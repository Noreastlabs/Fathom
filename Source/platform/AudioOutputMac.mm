#include "platform/AudioOutputMac.hpp"
#include <juce_audio_devices/juce_audio_devices.h>
#import <AppKit/AppKit.h>
#include <CoreAudio/CoreAudio.h>
#include <mach/mach_time.h>
#include "platform/NativeHooks.h"
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstring>
#include <limits>

namespace fathom::platform {
namespace {
// Bounded MPSC (sequence slots), one consumer. Failed publication is observable.
// No spinning on a held lock and no dynamically allocated queue nodes.
template<class T, std::size_t N> class MultiQueue final {
    struct Slot { std::atomic<std::size_t> sequence{}; T value{}; };
    std::array<Slot,N> slots_{};
    std::atomic<std::size_t> write_{0};
    std::size_t read_{};
public:
    MultiQueue() { for(std::size_t i=0;i<N;++i) slots_[i].sequence.store(i); }
    bool push(const T& x) noexcept {
        auto pos=write_.load(std::memory_order_relaxed);
        for(int attempt=0;attempt<8;++attempt) {
            auto& slot=slots_[pos%N];
            const auto seq=slot.sequence.load(std::memory_order_acquire);
            if(seq<pos) return false;
            if(seq==pos && write_.compare_exchange_weak(pos,pos+1,std::memory_order_relaxed)) {
                slot.value=x; slot.sequence.store(pos+1,std::memory_order_release); return true;
            }
            pos=write_.load(std::memory_order_relaxed);
        }
        return false;
    }
    bool pop(T& x) noexcept {
        auto& slot=slots_[read_%N];
        if(slot.sequence.load(std::memory_order_acquire)!=read_+1) return false;
        x=slot.value; slot.sequence.store(read_+N,std::memory_order_release); ++read_; return true;
    }
};
static_assert(std::atomic<std::uint64_t>::is_always_lock_free);
struct Hub final {
    MultiQueue<NativeEvent,4096> events;
    std::atomic<int> epoch{0};
    std::atomic<std::uint64_t> faultWord{0}, ioWord{0};
    std::atomic<std::uint32_t> expectedIO{0}, frames{0};
    std::atomic<bool> armed{false}, claimed{false};
    std::atomic<std::uint64_t> sequence{0}, dropped{0}, skips{0}, overloads{0};
};
Hub hub; // process-lifetime router; never points at reclaimable adapter memory
std::atomic<int> epochCounter{0};
thread_local std::uint64_t nativeSequence{};
thread_local int nativeEpoch{};
thread_local std::uint32_t nativeObject{}, nativeFrames{};
struct NativeClock final {int epoch{};std::uint32_t object{},frames{};bool haveSample{},haveHost{};double sample{};std::uint64_t host{};
    bool observe(int e,std::uint32_t obj,std::uint32_t n,const AudioTimeStamp* t,bool armed) noexcept {
        if(epoch!=e || object!=obj || !armed) {*this={};epoch=e;object=obj;}
        if(!t)return true;
        bool valid=true;
        if(t->mFlags & kAudioTimeStampSampleTimeValid) {
            valid=std::isfinite(t->mSampleTime) && (!haveSample || t->mSampleTime==sample+frames);
            sample=t->mSampleTime;frames=n;haveSample=true;
        } else haveSample=false;
        if(t->mFlags & kAudioTimeStampHostTimeValid) {valid&=!haveHost || t->mHostTime>host;host=t->mHostTime;haveHost=true;}
        else haveHost=false;
        return valid;
    }
};
NativeClock nativeClock; // serialized native I/O callbacks; stop flushes before a new device epoch
const mach_timebase_info_data_t timebase=[] {mach_timebase_info_data_t t{}; mach_timebase_info(&t); return t;}();
std::uint64_t tagged(int epoch,std::uint32_t value) noexcept {return (static_cast<std::uint64_t>(static_cast<std::uint32_t>(epoch))<<32)|value;}
output::Fault currentFault(int epoch) noexcept {const auto word=hub.faultWord.load();return (word>>32)==static_cast<std::uint32_t>(epoch)?static_cast<output::Fault>(static_cast<std::uint32_t>(word)):output::Fault::None;}
void fault(int epoch, output::Fault f) noexcept {
    if(epoch<=0 || f==output::Fault::None) return;
    auto expected=tagged(epoch,0);hub.faultWord.compare_exchange_strong(expected,tagged(epoch,static_cast<std::uint32_t>(f)));
}
void observedIO(int epoch,std::uint32_t object) noexcept {
    auto old=hub.ioWord.load();
    for(int i=0;i<8 && (old>>32)==static_cast<std::uint32_t>(epoch);++i)
        if(hub.ioWord.compare_exchange_weak(old,tagged(epoch,object)))return;
}
std::uint32_t currentIO(int epoch) noexcept {const auto v=hub.ioWord.load();return (v>>32)==static_cast<std::uint32_t>(epoch)?static_cast<std::uint32_t>(v):0;}
// At most one failed teardown is quarantined for the process; a new owner is refused.
// Blocks refer only to immutable epoch and permanent hub, so no dangling client pointer.
struct Quarantine {std::array<AudioObjectPropertyListenerBlock,3> blocks{};dispatch_queue_t queue{};};
Quarantine quarantine;
void emit(NativeEvent e) noexcept {
    e.ns=monotonicNs();
    if(!hub.events.push(e)) { ++hub.dropped; fault(static_cast<int>(e.epoch),output::Fault::QueueOverflow); }
}
void textEvent(std::uint32_t kind,int epoch,int status,const char* message) noexcept {
    NativeEvent e{}; e.kind=kind; e.epoch=static_cast<std::uint64_t>(std::max(0,epoch)); e.status=status;
    if(message) for(std::size_t i=0;i+1<e.text.size() && message[i];++i) e.text[i]=message[i];
    emit(e);
}
AudioObjectPropertyAddress address(AudioObjectPropertySelector s, AudioObjectPropertyScope scope=kAudioObjectPropertyScopeGlobal) {
    return {s,scope,kAudioObjectPropertyElementMain};
}
template<class T> bool get(AudioObjectID id,AudioObjectPropertySelector s,T& result,AudioObjectPropertyScope scope=kAudioObjectPropertyScopeGlobal) {
    T value{}; UInt32 n=sizeof(T); auto a=address(s,scope);
    const auto status=AudioObjectGetPropertyData(id,&a,0,nullptr,&n,&value);
    if(status!=noErr || n!=sizeof(T)) {
        NativeEvent e{};e.kind=40;e.epoch=static_cast<std::uint64_t>(std::max(0,hub.epoch.load()));e.object=id;e.selector=s;e.status=status ? status : kAudioHardwareBadPropertySizeError;emit(e);return false;
    }
    result=value; return true;
}
std::string cfString(CFStringRef s) {
    char bytes[1024]{};
    if(!s || CFGetTypeID(s)!=CFStringGetTypeID() || !CFStringGetCString(s,bytes,sizeof(bytes),kCFStringEncodingUTF8)) return {};
    return bytes;
}
std::string stringProperty(AudioObjectID id,AudioObjectPropertySelector s) {
    CFStringRef value=nullptr; if(!get(id,s,value)) return {};
    auto text=cfString(value); if(value) CFRelease(value);return text;
}
AudioDeviceID resolveUID(const std::string& uid) {
    auto value=CFStringCreateWithCString(kCFAllocatorDefault,uid.c_str(),kCFStringEncodingUTF8);
    if(!value) return kAudioObjectUnknown;
    AudioDeviceID id=kAudioObjectUnknown; UInt32 bytes=sizeof(id);auto a=address(kAudioHardwarePropertyTranslateUIDToDevice);
    const auto status=AudioObjectGetPropertyData(kAudioObjectSystemObject,&a,sizeof(value),&value,&bytes,&id);
    CFRelease(value); return status==noErr && bytes==sizeof(id)?id:kAudioObjectUnknown;
}
bool route(AudioObjectID io, AudioObjectID physical, const std::string& selected,bool& full,bool& active) {
    full=active=false;
    if(io==physical) {full=active=stringProperty(io,kAudioDevicePropertyDeviceUID)==selected;return full;}
    CFArrayRef list=nullptr;
    if(!get(io,kAudioAggregateDevicePropertyFullSubDeviceList,list)) return false;
    bool valid=list && CFGetTypeID(list)==CFArrayGetTypeID() && CFArrayGetCount(list)>0 && CFArrayGetCount(list)<=32;
    if(valid) for(CFIndex i=0;i<CFArrayGetCount(list);++i) {
        auto v=CFArrayGetValueAtIndex(list,i);
        if(CFGetTypeID(v)!=CFStringGetTypeID()) {valid=false;break;}
        const auto uid=cfString(static_cast<CFStringRef>(v)); if(uid.empty()) valid=false;
        full|=uid==selected;
    }
    if(list) CFRelease(list);
    std::array<AudioObjectID,32> ids{}; auto a=address(kAudioAggregateDevicePropertyActiveSubDeviceList);UInt32 bytes=0;
    if(AudioObjectGetPropertyDataSize(io,&a,0,nullptr,&bytes)!=noErr || !bytes || bytes>sizeof(ids) || bytes%sizeof(AudioObjectID)) return false;
    const auto expected=bytes;
    if(AudioObjectGetPropertyData(io,&a,0,nullptr,&bytes,ids.data())!=noErr || bytes!=expected) return false;
    for(std::size_t i=0;i<bytes/sizeof(AudioObjectID);++i) {
        const auto uid=stringProperty(ids[i],kAudioDevicePropertyDeviceUID); if(uid.empty()) valid=false;
        active|=uid==selected;
    }
    return valid;
}
}
std::uint64_t monotonicNs() noexcept {
    const auto ticks=mach_absolute_time();
    // Quotient/remainder avoids intermediate uint64 multiplication overflow.
    return (ticks/timebase.denom)*timebase.numer+(ticks%timebase.denom)*timebase.numer/timebase.denom;
}
OutputCapability defaultOutputCapability() {
    OutputCapability c;
    AudioDeviceID id{};UInt32 alive{},transport{};Float64 rate{};AudioValueRange bufferRange{};
    if(!get(kAudioObjectSystemObject,kAudioHardwarePropertyDefaultOutputDevice,id) || id==kAudioObjectUnknown) {c.error="No default output is available.";return c;}
    c.object=id;c.uid=stringProperty(id,kAudioDevicePropertyDeviceUID);c.name=stringProperty(id,kAudioObjectPropertyName);
    if(c.uid.empty() || c.name.empty() || !get(id,kAudioDevicePropertyDeviceIsAlive,alive) || !alive || !get(id,kAudioDevicePropertyTransportType,transport)
       || !get(id,kAudioDevicePropertyNominalSampleRate,rate) || !get(id,kAudioDevicePropertyBufferFrameSize,c.physicalFrames)
       || !get(id,kAudioDevicePropertyBufferFrameSizeRange,bufferRange)) {c.error="The output configuration could not be read. Choose an available output in macOS and retry.";return c;}
    if(transport==kAudioDeviceTransportTypeAggregate || transport==kAudioDeviceTransportTypeVirtual) {c.error="This preview requires a direct output device. Choose it in macOS Sound settings.";return c;}
    if(!std::isfinite(rate) || rate<8000 || rate>192000 || std::floor(rate)!=rate || !std::isfinite(bufferRange.mMinimum) || !std::isfinite(bufferRange.mMaximum) || bufferRange.mMinimum<1 || bufferRange.mMinimum>bufferRange.mMaximum || bufferRange.mMaximum>std::numeric_limits<std::uint32_t>::max()) {c.error="The selected output format is unsupported.";return c;}
    c.rate=static_cast<std::uint32_t>(rate);c.minFrames=static_cast<std::uint32_t>(std::ceil(bufferRange.mMinimum));c.maxFrames=static_cast<std::uint32_t>(std::floor(bufferRange.mMaximum));
    auto a=address(kAudioDevicePropertyStreamConfiguration,kAudioDevicePropertyScopeOutput);UInt32 bytes=0;
    if(AudioObjectGetPropertyDataSize(id,&a,0,nullptr,&bytes)!=noErr || bytes<sizeof(UInt32) || bytes>65536) {c.error="Output channels could not be read.";return c;}
    std::vector<std::uint64_t> storage((bytes+7)/8);const auto expected=bytes;
    if(AudioObjectGetPropertyData(id,&a,0,nullptr,&bytes,storage.data())!=noErr || bytes!=expected) {c.error="Output channels changed during inspection.";return c;}
    const auto* buffers=reinterpret_cast<const AudioBufferList*>(storage.data());
    if(buffers->mNumberBuffers>32 || offsetof(AudioBufferList,mBuffers)+buffers->mNumberBuffers*sizeof(AudioBuffer)>bytes) {c.error="Output channel list is unsupported.";return c;}
    for(UInt32 i=0;i<buffers->mNumberBuffers;++i) {const auto count=buffers->mBuffers[i].mNumberChannels;if(count>32 || c.outputChannels>32-count) {c.error="Output channel count is unsupported.";return c;}c.outputChannels+=count;}
    a=address(kAudioDevicePropertyAvailableNominalSampleRates);bytes=0;
    if(AudioObjectGetPropertyDataSize(id,&a,0,nullptr,&bytes)!=noErr || !bytes || bytes>32*sizeof(AudioValueRange) || bytes%sizeof(AudioValueRange)) {c.error="Supported output rates could not be read.";return c;}
    std::array<AudioValueRange,32> rates{};const auto requestedBytes=bytes;
    if(AudioObjectGetPropertyData(id,&a,0,nullptr,&bytes,rates.data())!=noErr || bytes!=requestedBytes) {c.error="Supported output rates changed during inspection.";return c;}
    for(std::size_t i=0;i<bytes/sizeof(AudioValueRange);++i) {const auto r=rates[i];if(!std::isfinite(r.mMinimum)||!std::isfinite(r.mMaximum)||r.mMinimum<=0||r.mMinimum>r.mMaximum) {c.error="Supported output rate data is invalid.";return c;}c.rates.push_back({r.mMinimum,r.mMaximum});}
    c.valid=c.outputChannels>=2 && c.minFrames<=c.maxFrames;
    if(!c.valid) c.error="A stereo output device is required by this preview.";
    return c;
}

struct AudioOutputMac::Impl final : juce::AudioIODeviceCallback {
    output::Lifecycle life;
    output::Mixer mixer;
    output::Observation latestQuery{};
    OutputStatus view{};
    scheduler::FixedQueue<Control,64> normal;
    scheduler::FixedQueue<Control,8> urgent;
    scheduler::FixedQueue<output::Observation,16> queries;
    scheduler::FixedQueue<OutputStatus,512> snapshots;
    MultiQueue<output::CachedAnnouncement,8> announcements;
    std::unique_ptr<juce::AudioIODeviceType> type;
    std::unique_ptr<juce::AudioIODevice> device;
    Buses buses{};
    RenderOutput render{};
    ScheduledRender scheduled{};
    OutputObserver observer{};
    void* context{};
    OutputCapability capability;
    output::Format requested{};
    std::string lastError;
    int epoch{};
    std::uint64_t callbacks{}, rendered{}, accepted{}, rejected{}, firstSilentCallbackNs{};
    output::Owner silenceOwner;
    dispatch_queue_t listenerQueue{};
    std::array<AudioObjectPropertyListenerBlock,3> listeners{};
    std::array<AudioObjectID,3> watched{};
    std::size_t watchCount{};
    id sleepToken=nil,wakeToken=nil;
    bool claimed{}, cleanupFailed{}, quiescent{true};
    std::atomic<bool> expectedStop{false};
    static void checkThread() {jassert(juce::MessageManager::getInstance()->isThisTheMessageThread());}
    void publish() noexcept {
        OutputStatus v{life.snapshot(),mixer.settings(),cleanupFailed,firstSilentCallbackNs,callbacks,rendered,accepted,rejected,hub.skips.load(),hub.overloads.load()};
        if(!snapshots.push(v)) {fault(epoch,output::Fault::QueueOverflow);life.invalidate(epoch,output::Fault::QueueOverflow,monotonicNs(),life.snapshot().submittedFrames);}
    }
    void command(Control c) noexcept {
        bool ok=false;
        if(c.epoch==static_cast<std::uint64_t>(epoch)) switch(c.op) {
            case OutputCommand::Acknowledge: ok=life.acknowledge(c.epoch,c.token);break;
            case OutputCommand::Start: ok=(render || scheduled) && life.start(c.owner);break;
            case OutputCommand::Pause: ok=life.pause(c.owner,c.requestedNs,life.snapshot().submittedFrames);break;
            case OutputCommand::PauseRetained: ok=life.acknowledgePause(c.owner);break;
            case OutputCommand::Resume: ok=life.resume(c.owner,c.nextOwner);break;
            case OutputCommand::Stop: ok=life.stop(c.owner,c.requestedNs,life.snapshot().submittedFrames);break;
            case OutputCommand::ResolveOutcome: ok=life.resolveOutcome(c.owner);break;
            case OutputCommand::Mix: ok=mixer.apply(c.mix);break;
        }
        ok?++accepted:++rejected;
        NativeEvent e{};e.kind=60;e.epoch=c.epoch;e.serial=c.owner.generation;e.selector=static_cast<std::uint32_t>(c.op);e.status=ok?0:1;e.rawHost=c.requestedNs;emit(e);
    }
    void audioDeviceAboutToStart(juce::AudioIODevice* d) override {
        const auto rate=d->getCurrentSampleRate();const auto frames=d->getCurrentBufferSizeSamples();
        if(!std::isfinite(rate) || rate<8000 || rate>192000 || std::floor(rate)!=rate || frames<1 || frames>static_cast<int>(output::maxOutputFrames)) {fault(epoch,output::Fault::FormatMismatch);return;}
        output::CachedAnnouncement a{static_cast<std::uint64_t>(epoch),monotonicNs(),{static_cast<std::uint32_t>(rate),static_cast<std::uint32_t>(frames)}};
        if(!announcements.push(a)) fault(epoch,output::Fault::QueueOverflow);
        NativeEvent e{};e.kind=61;e.epoch=epoch;e.frames=a.format.frames;e.sampleTime=rate;emit(e);
    }
    void audioDeviceStopped() override {textEvent(62,epoch,expectedStop.load()?0:1,"JUCE client stopped notification; status1 unexpected");if(!expectedStop.load())fault(epoch,output::Fault::Restart);}
    void audioDeviceError(const juce::String& error) override {textEvent(63,epoch,0,error.toRawUTF8());fault(epoch,output::Fault::Backend);}
    void audioDeviceIOCallbackWithContext(const float* const*,int,float* const* outputs,int channels,int n,const juce::AudioIODeviceCallbackContext& ctx) override {
        ++callbacks;
        for(int ch=0;ch<channels;++ch) if(outputs[ch] && n>0) std::fill_n(outputs[ch],n,0.0f);
        output::CachedAnnouncement a;for(int i=0;i<8 && announcements.pop(a);++i) life.announce(a);
        output::Observation q;for(int i=0;i<16 && queries.pop(q);++i) latestQuery=q;
        const auto stamp=monotonicNs();
        const auto f=currentFault(epoch);
        if(f!=output::Fault::None) life.invalidate(epoch,f,stamp,life.snapshot().submittedFrames);
        if(nativeEpoch!=epoch || n<=0 || n>static_cast<int>(output::maxOutputFrames) || nativeFrames!=static_cast<std::uint32_t>(n))
            life.invalidate(epoch,output::Fault::InvalidObservation,stamp,life.snapshot().submittedFrames);
        else if(latestQuery.epoch) {
            auto o=latestQuery;o.callbackSequence=nativeSequence;o.callbackStampNs=stamp;o.callbackFrames=static_cast<std::uint32_t>(n);o.nativeIOObject=nativeObject;
            life.observe(o);
        }
        if(life.snapshot().state==output::State::Observed && !hub.armed.load()) {hub.expectedIO.store(nativeObject);hub.armed.store(true);}
        // Urgent requests cancel matching pending Start/Resume in this same bounded batch.
        std::array<Control,8> stops{};std::size_t stopCount=0;Control c;
        for(int i=0;i<8 && urgent.pop(c);++i) {stops[stopCount++]=c;command(c);}
        for(int i=0;i<64 && normal.pop(c);++i) {
            bool cancelled=false;
            for(std::size_t j=0;j<stopCount;++j) cancelled|=stops[j].epoch==c.epoch
                && (c.op==OutputCommand::Start || c.op==OutputCommand::Resume)
                && (stops[j].owner==c.owner || (c.op==OutputCommand::Resume && stops[j].owner==c.nextOwner));
            if(cancelled) {
                // Stop of a recognized pending successor terminalizes its existing paused
                // predecessor. It never creates/rebinds output ownership to that successor.
                if(c.op==OutputCommand::Resume && life.snapshot().state==output::State::Paused && life.snapshot().owner==c.owner)
                    for(std::size_t j=0;j<stopCount;++j)
                        if(stops[j].op==OutputCommand::Stop && stops[j].epoch==c.epoch && stops[j].owner==c.nextOwner)
                            if(life.stop(c.owner,stops[j].requestedNs,life.snapshot().submittedFrames)) {
                                ++accepted;NativeEvent mapped{};mapped.kind=72;mapped.epoch=c.epoch;mapped.serial=c.owner.generation;mapped.rawHost=c.nextOwner.generation;
                                constexpr char hex[]="0123456789abcdef";for(std::size_t b=0;b<c.owner.id.size();++b){mapped.text[b*2]=hex[c.owner.id[b]>>4];mapped.text[b*2+1]=hex[c.owner.id[b]&15];}
                                emit(mapped); // retained UUID, predecessor generation, requested successor generation
                            }
                ++rejected;textEvent(71,epoch,1,"Pending start/resume cancelled by matching urgent command");
            }
            else command(c);
        }
        if(observer)observer(context,life.snapshot());
        std::uint32_t submittedThisBlock=0;
        if(life.renderAllowed()) {
            for(auto& bus:buses) for(auto& channel:bus) std::fill_n(channel.data(),n,0.0f);
            const auto owner=life.snapshot().owner;
            const auto progress=scheduled?scheduled(context,owner,requested.rate,static_cast<std::uint32_t>(n),buses)
                :scheduler::BlockOutcome{render && render(context,owner,requested.rate,static_cast<std::uint32_t>(n),buses),static_cast<std::uint32_t>(n),false};
            if(scheduled) {NativeEvent e{};e.kind=73;e.epoch=epoch;e.serial=nativeSequence;e.object=nativeObject;e.frames=progress.submittedFrames;
                e.flags=(progress.valid?1U:0U)|(progress.terminal?2U:0U);e.rawHost=owner.generation;emit(e);}
            bool valid=progress.valid && progress.submittedFrames<=static_cast<std::uint32_t>(n)
                && (progress.terminal || progress.submittedFrames==static_cast<std::uint32_t>(n));
            for(int ch=0;ch<channels && valid;++ch) for(int i=0;i<n;++i) {
                float value{};const auto cidx=static_cast<std::size_t>(ch%2);
                if(static_cast<std::uint32_t>(i)<progress.submittedFrames)
                    valid=mixer.sample({buses[0][cidx][i],buses[1][cidx][i],buses[2][cidx][i],buses[3][cidx][i]},value);
                if(!valid) break;
                if(outputs[ch]) outputs[ch][i]=value;
            }
            // A concurrent native invalidation must not leave this musical block in the buffer.
            if(!valid || currentFault(epoch)!=output::Fault::None
                || (progress.submittedFrames && !life.submitted(owner,nativeSequence,progress.submittedFrames))) {
                for(int ch=0;ch<channels;++ch) if(outputs[ch]) std::fill_n(outputs[ch],n,0.0f);
                life.invalidateOwner(owner,valid?(currentFault(epoch)!=output::Fault::None?currentFault(epoch):output::Fault::InvalidObservation):output::Fault::Render,stamp,life.snapshot().submittedFrames);
            } else {
                ++rendered;
                submittedThisBlock=progress.submittedFrames;
                if(progress.terminal)life.stop(owner,stamp,life.snapshot().submittedFrames);
            }
        }
        if(observer)observer(context,life.snapshot());
        const auto final=life.snapshot();
        if(!(silenceOwner==final.owner)) {silenceOwner=final.owner;firstSilentCallbackNs=0;}
        if(final.stopRequested && !life.renderAllowed() && !submittedThisBlock && !firstSilentCallbackNs)firstSilentCallbackNs=stamp;
        NativeEvent event{};event.kind=64;event.epoch=epoch;event.serial=nativeSequence;event.object=nativeObject;event.frames=static_cast<std::uint32_t>(std::max(n,0));event.selector=submittedThisBlock;event.rawHost=ctx.hostTimeNs?*ctx.hostTimeNs:0;event.flags=ctx.hostTimeNs?1U:0U;event.status=static_cast<int>(life.snapshot().state);emit(event);
        publish();
    }
    void watch(AudioObjectID object) {
        if(!object || watchCount>=watched.size() || std::find(watched.begin(),watched.begin()+static_cast<std::ptrdiff_t>(watchCount),object)!=watched.begin()+static_cast<std::ptrdiff_t>(watchCount)) return;
        auto a=AudioObjectPropertyAddress{kAudioObjectPropertySelectorWildcard,kAudioObjectPropertyScopeWildcard,kAudioObjectPropertyElementWildcard};
        const auto e=epoch;
        AudioObjectPropertyListenerBlock block=^(UInt32 n,const AudioObjectPropertyAddress* addresses) {for(UInt32 i=0;i<n;++i) fathom_property(e,object,addresses[i].mSelector,addresses[i].mScope,addresses[i].mElement,n);};
        const auto status=AudioObjectAddPropertyListenerBlock(object,&a,listenerQueue,block);
        if(status!=noErr) {textEvent(65,epoch,status,"Output listener registration failed");fault(epoch,output::Fault::Backend);return;}
        listeners[watchCount]=block;watched[watchCount++]=object;
    }
    void removeWatches() {
        auto a=AudioObjectPropertyAddress{kAudioObjectPropertySelectorWildcard,kAudioObjectPropertyScopeWildcard,kAudioObjectPropertyElementWildcard};
        for(std::size_t i=0;i<watchCount;++i) {
            const auto status=AudioObjectRemovePropertyListenerBlock(watched[i],&a,listenerQueue,listeners[i]);
            if(status!=noErr) {textEvent(66,epoch,status,"Output listener removal failed; process output quarantined");
                cleanupFailed=true;quarantine.blocks[i]=listeners[i];quarantine.queue=listenerQueue;
                lastError="Output could not be fully disconnected. Quit Fathom before reconnecting.";}
        }
        watchCount=0;
        if(listenerQueue) dispatch_sync(listenerQueue,^{});
        for(auto& block:listeners) block=nil;listenerQueue=nullptr;
        auto* center=[[NSWorkspace sharedWorkspace] notificationCenter];
        if(sleepToken) [center removeObserver:sleepToken];if(wakeToken) [center removeObserver:wakeToken];
        sleepToken=nil;wakeToken=nil;
    }
    void service() {
        checkThread();OutputStatus s;while(snapshots.pop(s)) view=s;
        if(!device) return;
        if(quiescent) return;
        const auto io=currentIO(epoch);
        if(io) {
            watch(io);
            output::Observation q{};q.epoch=epoch;q.queriedIOObject=io;q.physicalObject=capability.object;
            Float64 rate{},physicalRate{};UInt32 frames{},physicalFrames{},alive{};
            q.ioKnown=get(io,kAudioDevicePropertyNominalSampleRate,rate) && get(io,kAudioDevicePropertyBufferFrameSize,frames) && std::isfinite(rate) && rate>=8000 && rate<=192000 && std::floor(rate)==rate;
            q.physicalKnown=get(capability.object,kAudioDevicePropertyNominalSampleRate,physicalRate) && get(capability.object,kAudioDevicePropertyBufferFrameSize,physicalFrames) && get(capability.object,kAudioDevicePropertyDeviceIsAlive,alive) && alive && resolveUID(capability.uid)==capability.object;
            if(q.ioKnown) q.queriedIO={static_cast<std::uint32_t>(rate),frames};
            if(q.physicalKnown && std::isfinite(physicalRate) && physicalRate>=8000 && physicalRate<=192000 && std::floor(physicalRate)==physicalRate) {q.physicalRate=static_cast<std::uint32_t>(physicalRate);q.physicalFrames=physicalFrames;} else q.physicalKnown=false;
            q.routeKnown=route(io,capability.object,capability.uid,q.selectedInFullRoute,q.selectedInActiveRoute);q.queryStampNs=monotonicNs();
            queries.push(q); // A full query port retains earlier whole query; next service retries, no partial overwrite.
            NativeEvent e{};e.kind=67;e.epoch=epoch;e.object=io;e.frames=frames;e.sampleTime=rate;e.rateScalar=physicalRate;e.selector=physicalFrames;e.flags=(q.ioKnown?1U:0U)|(q.physicalKnown?2U:0U)|(q.routeKnown?4U:0U)|(q.selectedInFullRoute?8U:0U)|(q.selectedInActiveRoute?16U:0U);emit(e);
        }
        if(view.lifecycle.state==output::State::Observed && !hub.armed.load()) {
            hub.expectedIO.store(view.lifecycle.observation.nativeIOObject);hub.armed.store(true);
        }
        if(currentFault(epoch)!=output::Fault::None) {
            // Faults may stop callbacks entirely; flush before taking control-side ownership.
            expectedStop.store(true);device->stop();device->close();quiescent=true;
            OutputStatus pending;while(snapshots.pop(pending))view=pending;
            life.invalidate(epoch,currentFault(epoch),monotonicNs(),life.snapshot().submittedFrames);
            if(observer)observer(context,life.snapshot());
            view.lifecycle=life.snapshot();lastError=output::faultText(view.lifecycle.fault);
        }
        if(view.lifecycle.state==output::State::Fault) lastError=output::faultText(view.lifecycle.fault);
    }
    output::Snapshot shutdown() {
        checkThread();
        if(device) {hub.armed.store(false);expectedStop.store(true);device->stop();device->close();quiescent=true;}
        if(currentFault(epoch)!=output::Fault::None)life.invalidate(epoch,currentFault(epoch),monotonicNs(),life.snapshot().submittedFrames); // JUCE public stop flushes client callbacks.
        // Now callback is quiescent: ownership can move to this control thread.
        if(life.snapshot().ownsOutcome) life.stop(life.snapshot().owner,monotonicNs(),life.snapshot().submittedFrames);
        if(observer)observer(context,life.snapshot());
        observer=nullptr;render=nullptr;scheduled=nullptr;context=nullptr;
        OutputStatus pending;while(snapshots.pop(pending)) view=pending;
        view.lifecycle=life.snapshot();
        removeWatches();view.cleanupFailed=cleanupFailed;device.reset();type.reset();
        if(claimed && !cleanupFailed) {hub.epoch.store(0);hub.faultWord.store(0);hub.ioWord.store(0);hub.claimed.store(false);claimed=false;}
        return view.lifecycle;
    }
};
AudioOutputMac::AudioOutputMac():p_(std::make_unique<Impl>()) {}
AudioOutputMac::~AudioOutputMac() {p_->shutdown();}
bool AudioOutputMac::connect(const OutputCapability& selected,output::Format fmt,RenderOutput provider,void* context,
                            OutputObserver observer,ScheduledRender scheduled) {
    Impl::checkThread();auto& p=*p_;p.service();
    if(p.device || p.life.snapshot().ownsOutcome) {p.lastError="Stop and resolve the current activity before configuring output.";return false;}
    if(!selected.valid) {p.lastError=selected.error.empty()?"Choose an available output in macOS Sound settings, then connect again.":selected.error;return false;}
    if(!fmt.valid()) {p.lastError="Choose a supported output rate and buffer size, then connect again.";return false;}
    const auto current=defaultOutputCapability();
    bool supported=false;for(const auto& r:current.rates) supported|=fmt.rate>=r[0]&&fmt.rate<=r[1];
    if(!current.valid || current.uid!=selected.uid || current.object!=selected.object || !supported || fmt.rate!=current.rate || fmt.frames<current.minFrames || fmt.frames>current.maxFrames) {p.lastError="Output changed or requested format is unsupported. Refresh the selected output.";return false;}
    bool free=false;if(!hub.claimed.compare_exchange_strong(free,true)) {p.lastError="Another output owner is active.";return false;}
    p.claimed=true;
    if(epochCounter.load()==std::numeric_limits<int>::max()) {p.shutdown();p.lastError="Output generation capacity exhausted; reopen Fathom.";return false;}
    p.epoch=epochCounter.fetch_add(1)+1;
    if(p.epoch<=0) {p.shutdown();p.lastError="Output generation capacity exhausted; reopen Fathom.";return false;}
    hub.epoch.store(p.epoch);hub.armed.store(false);hub.faultWord.store(tagged(p.epoch,0));hub.ioWord.store(tagged(p.epoch,0));hub.expectedIO.store(0);hub.frames.store(fmt.frames);
    NativeEvent timebaseEvent{};timebaseEvent.kind=80;timebaseEvent.epoch=p.epoch;timebaseEvent.selector=timebase.numer;timebaseEvent.element=timebase.denom;emit(timebaseEvent);
    p.capability=current;p.requested=fmt;p.render=provider;p.scheduled=scheduled;p.observer=observer;p.context=context;p.latestQuery={};p.firstSilentCallbackNs=0;p.silenceOwner={};p.lastError.clear();p.expectedStop.store(false);
    output::Observation discard;while(p.queries.pop(discard)) {};
    output::CachedAnnouncement old;while(p.announcements.pop(old)) {};
    Control c;while(p.normal.pop(c)){}while(p.urgent.pop(c)){}
    if(!p.life.configure({static_cast<std::uint64_t>(p.epoch),monotonicNs(),fmt,current.object})) {p.shutdown();p.lastError="Output configuration is not ready for replacement.";return false;}
    const auto e=p.epoch;
    p.listenerQueue=dispatch_queue_create("local.fathom.output.properties",DISPATCH_QUEUE_SERIAL);
    p.watch(current.object);p.watch(kAudioObjectSystemObject);
    auto* center=[[NSWorkspace sharedWorkspace] notificationCenter];
    p.sleepToken=[center addObserverForName:NSWorkspaceWillSleepNotification object:nil queue:nil usingBlock:^(NSNotification*) {textEvent(68,e,0,"NSWorkspace will sleep");fault(e,output::Fault::Sleep);}];
    p.wakeToken=[center addObserverForName:NSWorkspaceDidWakeNotification object:nil queue:nil usingBlock:^(NSNotification*) {textEvent(69,e,0,"NSWorkspace did wake; explicit recovery remains required");}];
    p.type.reset(juce::AudioIODeviceType::createAudioIODeviceType_CoreAudio());p.type->scanForDevices();
    const auto names=p.type->getDeviceNames(false);const auto index=p.type->getDefaultDeviceIndex(false);
    if(index<0 || index>=names.size()) {p.shutdown();p.lastError="Default output could not be opened.";return false;}
    p.device.reset(p.type->createDevice(names[index],{}));
    if(!p.device) {p.shutdown();p.lastError="Output device creation failed.";return false;}
    juce::BigInteger input,output;output.setRange(0,2,true);
    const auto error=p.device->open(input,output,fmt.rate,static_cast<int>(fmt.frames));
    if(error.isNotEmpty()) {const auto detail=error.toStdString();p.shutdown();p.lastError="Output could not open: "+detail;return false;}
    const auto after=defaultOutputCapability();
    if(!after.valid || after.uid!=current.uid || after.rate!=fmt.rate) {p.shutdown();p.lastError="Output changed while opening. Refresh and reconnect.";return false;}
    p.view.lifecycle=p.life.snapshot();p.quiescent=false;p.device->start(&p);return true;
}
bool AudioOutputMac::send(Control c) {
    Impl::checkThread();if(!p_->device) return false;
    if(!c.requestedNs)c.requestedNs=monotonicNs();
    if(p_->quiescent) {p_->command(c);p_->view.lifecycle=p_->life.snapshot();p_->view.commandAccepted=p_->accepted;p_->view.commandRejected=p_->rejected;return true;}
    const auto urgent=c.op==OutputCommand::Stop || c.op==OutputCommand::Pause;
    const bool ok=urgent?p_->urgent.push(c):p_->normal.push(c);
    if(!ok) {fault(p_->epoch,output::Fault::QueueOverflow);p_->lastError="Output command capacity exceeded; playback stopped.";}
    return ok;
}
void AudioOutputMac::service(){p_->service();}
OutputStatus AudioOutputMac::status() const {Impl::checkThread();return p_->view;}
const std::string& AudioOutputMac::error() const {return p_->lastError;}
bool AudioOutputMac::nextEvent(NativeEvent& e){Impl::checkThread();return hub.events.pop(e);}
bool AudioOutputMac::disconnect() {
    p_->service();
    if(p_->view.lifecycle.ownsOutcome) {p_->lastError="Keep this activity open until its outcome is saved or reconciled.";return false;}
    p_->shutdown();const bool closed=p_->life.close();p_->view.lifecycle=p_->life.snapshot();if(closed&&!p_->cleanupFailed)p_->lastError.clear();return closed&&!p_->cleanupFailed;
}
output::Snapshot AudioOutputMac::shutdown(){return p_->shutdown();}
void AudioOutputMac::injectFault(output::Fault f){Impl::checkThread();textEvent(70,p_->epoch,static_cast<int>(f),"INJECTED failure; not an observed OS event");fault(p_->epoch,f);}
} // namespace fathom::platform

extern "C" int fathom_bind_epoch(){return fathom::platform::hub.epoch.load();}
extern "C" void fathom_property(int epoch,unsigned object,unsigned selector,unsigned scope,unsigned element,unsigned count){
    using namespace fathom::platform;NativeEvent e{};e.kind=20;e.epoch=static_cast<std::uint64_t>(std::max(0,epoch));e.object=object;e.selector=selector;e.scope=scope;e.element=element;e.frames=count;emit(e);
    if(epoch!=hub.epoch.load())return;
    if(selector==kAudioDeviceProcessorOverload)++hub.overloads;
    const bool changed=selector==kAudioDevicePropertyNominalSampleRate||selector==kAudioDevicePropertyBufferFrameSize||selector==kAudioDevicePropertyDeviceIsAlive||selector==kAudioHardwarePropertyDefaultOutputDevice||selector==kAudioHardwarePropertyDevices||selector==kAudioDevicePropertyDeviceUID||selector==kAudioDevicePropertyDeviceHasChanged||selector==kAudioAggregateDevicePropertyComposition||selector==kAudioAggregateDevicePropertyFullSubDeviceList||selector==kAudioAggregateDevicePropertyActiveSubDeviceList;
    if(changed && hub.armed.load()) fault(epoch,fathom::output::Fault::FormatMismatch);
}
extern "C" void fathom_native_block(int epoch,unsigned object,int frames,const AudioTimeStamp* now,const AudioTimeStamp* input,const AudioTimeStamp* output){
    using namespace fathom::platform;nativeEpoch=epoch;nativeSequence=hub.sequence.fetch_add(1)+1;nativeObject=object;nativeFrames=static_cast<std::uint32_t>(std::max(frames,0));
    if(epoch==hub.epoch.load()) {observedIO(epoch,object);if(hub.armed.load() && (object!=hub.expectedIO.load() || nativeFrames!=hub.frames.load()))fault(epoch,fathom::output::Fault::FormatMismatch);}
    if(!nativeClock.observe(epoch,object,nativeFrames,output,hub.armed.load()) && hub.armed.load()) fault(epoch,fathom::output::Fault::Clock);
    const AudioTimeStamp* ts[]{now,input,output};for(unsigned i=0;i<3;++i) {NativeEvent e{};e.kind=21+i;e.epoch=epoch;e.serial=nativeSequence;e.object=object;e.frames=nativeFrames;if(ts[i]) {e.rawHost=ts[i]->mHostTime;e.sampleTime=ts[i]->mSampleTime;e.rateScalar=ts[i]->mRateScalar;e.flags=ts[i]->mFlags;}emit(e);}
}
extern "C" void fathom_skip(int reason,int frames,int configured){
    using namespace fathom::platform;++hub.skips;NativeEvent e{};e.kind=24;e.epoch=nativeEpoch;e.serial=nativeSequence;e.status=reason;e.frames=static_cast<std::uint32_t>(std::max(0,frames));e.selector=static_cast<std::uint32_t>(std::max(0,configured));emit(e);
    if(reason==3 && hub.armed.load()) fault(nativeEpoch,fathom::output::Fault::FormatMismatch);
}
extern "C" void fathom_native_output(int epoch,const AudioBufferList* output){
    using namespace fathom::platform;if(!output)return;
    for(UInt32 b=0;b<output->mNumberBuffers;++b) {
        const auto& buffer=output->mBuffers[b];const auto* data=static_cast<const float*>(buffer.mData);NativeEvent e{};e.kind=26;e.epoch=epoch;e.serial=nativeSequence;e.object=b;e.frames=buffer.mDataByteSize/sizeof(float);e.selector=buffer.mNumberChannels;
        if(data && e.frames<=fathom::output::maxOutputFrames*32) for(UInt32 i=0;i<e.frames;++i) {if(!std::isfinite(data[i]))++e.status;else e.peak=std::max(e.peak,std::abs(static_cast<double>(data[i])));}
        else e.status=-1;
        if(e.status) fault(epoch,fathom::output::Fault::Render);
        emit(e);
    }
#ifdef FATHOM_TEST_NATIVE_CAPTURE
    FATHOM_TEST_NATIVE_CAPTURE(epoch,output);
#endif
}
extern "C" void fathom_backend_error(int epoch,int origin,int status,const char* message){
    using namespace fathom::platform;textEvent(27,epoch,status,message);NativeEvent e{};e.kind=28;e.epoch=epoch;e.status=origin;emit(e);
    if(origin==3||origin==4) fault(epoch,fathom::output::Fault::Backend);
}
