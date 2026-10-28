// The test compiles the exact production adapter in this translation unit to inspect
// its private mechanics. The test capture seam is absent from production builds.
#include <CoreAudio/CoreAudio.h>
#include <array>
#include <atomic>
#include <cmath>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <thread>
#include <vector>
namespace {
constexpr std::size_t captureLimit=48000*45*2;
std::array<float,captureLimit> capture{};
std::size_t captured{};
bool captureOverflow{};
void captureNative(int,const AudioBufferList* data) noexcept {
    if(!data || data->mNumberBuffers==0)return;
    // Selected JUCE native float output; keep raw interleaving, not DAC samples.
    for(UInt32 b=0;b<data->mNumberBuffers;++b) {
        const auto& buf=data->mBuffers[b];const auto n=buf.mDataByteSize/sizeof(float);
        if(!buf.mData)continue;
        if(n>captureLimit-captured) {captureOverflow=true;return;}
        const auto* samples=static_cast<const float*>(buf.mData);
        for(UInt32 i=0;i<n;++i)capture[captured++]=samples[i];
    }
}
}
#define FATHOM_TEST_NATIVE_CAPTURE captureNative
#include "../Source/platform/AudioOutputMac.mm"

namespace fathom::platform {
struct OutputTestAccess {
    static int checks() {
        int checks=0,failures=0;
        auto check=[&](bool pass,const char* name){++checks;if(!pass)++failures;std::cout<<(pass?"PASS ":"FAIL ")<<name<<'\n';};
        {
            AudioOutputMac output;OutputCapability unavailable;unavailable.error="No default output is available.";
            check(!output.connect(unavailable,{44100,256})&&output.error()==unavailable.error,"unavailable output reports actual capability reason without invented activity");
            OutputCapability declared;declared.valid=true;
            check(!output.connect(declared,{0,0})&&output.error().find("supported output rate")!=std::string::npos,"invalid requested format gives actionable configuration message");
        }
        MultiQueue<std::uint64_t,64> q;std::atomic<int> done{0};std::atomic<std::uint64_t> written{0};
        std::array<std::thread,4> producers;
        for(std::size_t j=0;j<producers.size();++j) producers[j]=std::thread([&,j]{for(std::uint64_t i=0;i<5000;++i){const auto value=j*5000+i;while(!q.push(value))std::this_thread::yield();++written;}++done;});
        std::array<bool,20000> seen{};std::uint64_t count=0,x=0;bool unique=true;
        while(done.load()!=4 || count<written.load()) {if(q.pop(x)){unique&=x<seen.size()&&!seen[x];if(x<seen.size())seen[x]=true;++count;}else std::this_thread::yield();}
        for(auto& t:producers)t.join();while(q.pop(x)){unique&=x<seen.size()&&!seen[x];if(x<seen.size())seen[x]=true;++count;}
        check(unique&&count==20000,"four-producer publication retains 20000 unique values");
        hub.epoch.store(2);hub.faultWord.store(tagged(2,0));hub.ioWord.store(tagged(2,99));fault(1,output::Fault::Backend);observedIO(1,33);
        check(currentFault(2)==output::Fault::None&&currentIO(2)==99,"stale epoch cannot latch fault or IO object");
        fault(2,output::Fault::DeviceLost);check(currentFault(2)==output::Fault::DeviceLost,"matching epoch fault latches");fault(2,output::Fault::Backend);check(currentFault(2)==output::Fault::DeviceLost,"first fault retained");
        NativeClock clock;AudioTimeStamp ts{};ts.mFlags=kAudioTimeStampSampleTimeValid|kAudioTimeStampHostTimeValid;ts.mSampleTime=0;ts.mHostTime=100;
        check(clock.observe(1,2,256,&ts,true),"first valid native clock observation");ts.mSampleTime=256;ts.mHostTime=200;check(clock.observe(1,2,256,&ts,true),"contiguous native sample time");ts.mSampleTime=0;ts.mHostTime=300;check(!clock.observe(1,2,256,&ts,true),"sample time regression refuses");
        clock={};ts.mSampleTime=0;ts.mHostTime=100;clock.observe(1,2,256,&ts,true);ts.mSampleTime=512;ts.mHostTime=200;check(!clock.observe(1,2,256,&ts,true),"sample discontinuity refuses");
        clock={};ts.mSampleTime=0;ts.mHostTime=100;clock.observe(1,2,256,&ts,true);ts.mSampleTime=256;check(!clock.observe(1,2,256,&ts,true),"valid host time must advance");ts.mFlags=0;check(clock.observe(1,2,256,&ts,true),"unavailable timestamp fields not invented");
        // Real adapter callback with synthetic domain evidence; no native device opens.
        AudioOutputMac::Impl p;p.epoch=1;p.requested={44100,256};hub.epoch.store(1);hub.faultWord.store(tagged(1,0));hub.ioWord.store(tagged(1,87));hub.armed.store(false);
        p.life.configure({1,1,{44100,256},87});p.life.announce({1,2,{44100,256}});
        p.latestQuery={1,1,4,3,{44100,256},256,87,87,87,44100,512,true,true,true,true,true};
        p.life.observe(p.latestQuery);p.life.acknowledge(1,1);
        output::Owner owner;owner.id={1,2,3,4,5,6,0x47,8,0x89,10,11,12,13,14,15,16};owner.generation=1;owner.epoch=1;
        p.render=[](void*,const output::Owner&,std::uint32_t,std::uint32_t n,Buses& b)noexcept{for(auto& bus:b)for(auto& c:bus)std::fill_n(c.data(),n,0.1f);return true;};
        Control start;start.op=OutputCommand::Start;start.epoch=1;start.owner=owner;p.normal.push(start);Control stop=start;stop.op=OutputCommand::Stop;stop.requestedNs=5;p.urgent.push(stop);
        nativeEpoch=1;nativeObject=87;nativeFrames=256;nativeSequence=2;std::array<float,256> left{},right{};float* outs[]{left.data(),right.data()};juce::AudioIODeviceCallbackContext context{};
        p.audioDeviceIOCallbackWithContext(nullptr,0,outs,2,256,context);
        check(!p.life.renderAllowed()&&p.rendered==0&&left[0]==0,"same callback Stop cancels queued Start");
        p.normal.push(start);nativeSequence=3;p.audioDeviceIOCallbackWithContext(nullptr,0,outs,2,256,context);check(p.life.renderAllowed()&&p.rendered==1,"explicit later Start runs");
        const auto original=p.life.snapshot().owner;auto stale=owner;stale.generation=2;stop.owner=stale;p.urgent.push(stop);nativeSequence=4;p.audioDeviceIOCallbackWithContext(nullptr,0,outs,2,256,context);check(p.life.renderAllowed()&&p.life.snapshot().owner==original,"stale Stop does not repoint active outcome");
        p.life.pause(owner,7,p.life.snapshot().submittedFrames);p.life.acknowledgePause(owner);
        Control resume=start;resume.op=OutputCommand::Resume;resume.nextOwner=owner;++resume.nextOwner.generation;p.normal.push(resume);
        stop.owner=resume.nextOwner;p.urgent.push(stop);nativeSequence=5;p.audioDeviceIOCallbackWithContext(nullptr,0,outs,2,256,context);
        check(p.life.snapshot().state==output::State::Unresolved&&p.life.snapshot().pendingOutcome&&p.life.snapshot().owner==owner,"Stop of pending Resume successor retains predecessor terminal");
        p.expectedStop.store(false);p.audioDeviceStopped();check(currentFault(1)==output::Fault::Restart,"unexpected JUCE stop latches without next callback");
        hub.epoch.store(0);hub.faultWord.store(0);hub.ioWord.store(0);NativeEvent ev;bool mapped=false;
        while(hub.events.pop(ev))if(ev.kind==72)mapped=ev.epoch==1&&ev.serial==1&&ev.rawHost==2&&std::string(ev.text.data())=="0102030405064708890a0b0c0d0e0f10";
        check(mapped,"mapped successor Stop has explicit original-owner disposition event");captured=0;
        std::cout<<"checks="<<checks<<" failures="<<failures<<'\n';return failures?1:0;
    }
};
}
namespace {
using namespace fathom;
juce::var capabilityJson(const platform::OutputCapability& c) {
    juce::DynamicObject::Ptr o=new juce::DynamicObject();
    o->setProperty("valid",c.valid);o->setProperty("object",static_cast<int>(c.object));o->setProperty("uid",juce::String(c.uid));o->setProperty("name",juce::String(c.name));o->setProperty("rate",static_cast<int>(c.rate));o->setProperty("physicalFrames",static_cast<int>(c.physicalFrames));o->setProperty("outputChannels",static_cast<int>(c.outputChannels));o->setProperty("minFrames",static_cast<int>(c.minFrames));o->setProperty("maxFrames",static_cast<int>(c.maxFrames));o->setProperty("error",juce::String(c.error));
    juce::Array<juce::var> rates;for(const auto& r:c.rates) rates.add(juce::var{juce::Array<juce::var>{r[0],r[1]}});o->setProperty("rates",rates);return juce::var{o.get()};
}
struct Fixture {
    std::uint64_t frame{},generation{};
    static bool render(void* context,const output::Owner& owner,std::uint32_t rate,std::uint32_t n,platform::Buses& buses) noexcept {
        auto& f=*static_cast<Fixture*>(context);if(f.generation!=owner.generation){f.frame=0;f.generation=owner.generation;}
        const double freq[]{110,220,440,880};
        for(std::size_t b=0;b<4;++b)for(std::uint32_t i=0;i<n;++i){const auto t=static_cast<double>(f.frame+i)/rate;
            const auto v=static_cast<float>(0.12*std::sin(6.283185307179586*freq[b]*t));buses[b][0][i]=buses[b][1][i]=v;}
        f.frame+=n;return true;
    }
};
class Run final:private juce::Timer {
public:
    Run(std::string root,std::string uid,std::uint32_t rate,std::uint32_t frames):root_(std::move(root)),uid_(std::move(uid)),format_{rate,frames},events_(root_+"/events.csv"),states_(root_+"/states.csv"),outcomes_(root_+"/retained-outcomes.jsonl") {
        events_<<"ns,epoch,kind,serial,object,selector,scope,element,frames,flags,status,sample_time,rate_scalar,peak,raw_host,text\n";
        states_<<"ns,step,epoch,state,owner_uuid,owner_generation,owns,pending,submitted,confirmed,uncertain,request_ns,first_stop_marker_ns,first_silent_callback_ns,callbacks,rendered,accepted,rejected,fault\n";
        start_=platform::monotonicNs();phase_=start_;startTimer(20);
    }
    int result()const{return (!done_ || failed_)?1:0;}
private:
    static std::string uuid(const output::Owner& owner) {std::ostringstream out;out<<std::hex<<std::setfill('0');for(auto b:owner.id)out<<std::setw(2)<<static_cast<unsigned>(b);return out.str();}
    void retainOutcome(const char* kind,const output::Snapshot& s) {
        if(++retained_>8){finish(true,"retained outcome bound exceeded");return;}
        outcomes_<<"{\"kind\":\""<<kind<<"\",\"uuid\":\""<<uuid(s.owner)<<"\",\"generation\":"<<s.owner.generation<<",\"epoch\":"<<s.owner.epoch<<",\"state\":"<<static_cast<int>(s.state)<<",\"submitted\":"<<s.submittedFrames<<",\"confirmed\":"<<s.confirmedFrames<<",\"uncertain\":"<<s.uncertainThrough<<",\"pending\":"<<(s.pendingOutcome?"true":"false")<<",\"requestNs\":"<<s.requestedStopNs<<",\"retainedNs\":"<<platform::monotonicNs()<<"}\n";
    }
    void retain() {
        platform::NativeEvent e;for(int i=0;i<4096 && output_.nextEvent(e);++i){
            std::string msg=e.text.data();for(auto& c:msg)if(c==','||c=='\n'||c=='\r')c=' ';
            events_<<e.ns<<','<<e.epoch<<','<<e.kind<<','<<e.serial<<','<<e.object<<','<<e.selector<<','<<e.scope<<','<<e.element<<','<<e.frames<<','<<e.flags<<','<<e.status<<','<<std::setprecision(17)<<e.sampleTime<<','<<e.rateScalar<<','<<e.peak<<','<<e.rawHost<<','<<msg<<'\n';}
        const auto v=output_.status();const auto s=v.lifecycle;
        states_<<platform::monotonicNs()<<','<<step_<<','<<s.request.epoch<<','<<static_cast<int>(s.state)<<','<<uuid(s.owner)<<','<<s.owner.generation<<','<<s.ownsOutcome<<','<<s.pendingOutcome<<','<<s.submittedFrames<<','<<s.confirmedFrames<<','<<s.uncertainThrough<<','<<s.requestedStopNs<<','<<s.firstSilenceNs<<','<<v.firstSilentCallbackNs<<','<<v.callbacks<<','<<v.renderedBlocks<<','<<v.commandAccepted<<','<<v.commandRejected<<','<<static_cast<int>(s.fault)<<'\n';
    }
    void finish(bool failed,const std::string& message) {
        if(done_)return;done_=true;stopTimer();const auto terminal=output_.shutdown();failed|=output_.status().cleanupFailed;failed_=failed;retain();
        std::ofstream pcm(root_+"/native-output-f32.raw",std::ios::binary);pcm.write(reinterpret_cast<const char*>(capture.data()),static_cast<std::streamsize>(captured*sizeof(float)));
        std::ofstream result(root_+"/run-result.json");result<<"{\"failed\":"<<(failed?"true":"false")<<",\"lastStep\":"<<step_<<",\"capturedFloatSamples\":"<<captured<<",\"captureOverflow\":"<<(captureOverflow?"true":"false")<<",\"cleanupFailed\":"<<(output_.status().cleanupFailed?"true":"false")<<",\"pendingAtExit\":"<<(terminal.pendingOutcome?"true":"false")<<",\"message\": "<<juce::JSON::toString(juce::var{juce::String(message)})<<"}\n";
        std::cout<<(failed?"FAIL ":"PASS ")<<message<<std::endl;juce::MessageManager::getInstance()->stopDispatchLoop();
    }
    struct Abort {};
    void require(bool condition,const char* message) {if(!condition){finish(true,message);throw Abort{};}}
    void next(){++step_;phase_=platform::monotonicNs();std::cout<<"step="<<step_<<std::endl;}
    bool waitMs(unsigned ms)const{return platform::monotonicNs()-phase_>=static_cast<std::uint64_t>(ms)*1000000;}
    platform::Control control(platform::OutputCommand op)const {platform::Control c;c.op=op;c.epoch=output_.status().lifecycle.request.epoch;c.owner=owner_;return c;}
    void send(platform::OutputCommand op){require(output_.send(control(op)),"command queue refused");}
    void open(){auto cap=platform::defaultOutputCapability();require(cap.valid&&cap.uid==uid_&&cap.rate==format_.rate,"predeclared capability changed; abort");if(done_)return;require(output_.connect(cap,format_,Fixture::render,&fixture_),"native connect failed");}
    void timerCallback() override {
        output_.service();retain();
        if(platform::monotonicNs()-start_>120000000000ULL){finish(true,"120 second watchdog");return;}
        const auto s=output_.status().lifecycle;
        if(s.state==output::State::Fault && step_!=21 && step_!=22 && step_!=27 && step_!=28 && step_!=33 && step_!=34) {finish(true,std::string("unexpected fault: ")+output_.error());return;}
        if(captureOverflow){finish(true,"capture capacity exceeded");return;}
        try { switch(step_) {
            case 0:open();if(!done_)next();break;
            case 1:if(s.state==output::State::Observed){require(!s.ownsOutcome&&s.submittedFrames==0,"silent before ack");next();}else if(waitMs(8000))finish(true,"observation timeout");break;
            case 2:if(waitMs(250)){auto c=control(platform::OutputCommand::Acknowledge);c.token=s.observationToken;require(output_.send(c),"ack enqueue");next();}break;
            case 3:if(s.state==output::State::Ready){owner_.id={1,2,3,4,5,6,0x47,8,0x89,10,11,12,13,14,15,16};owner_.generation=1;owner_.epoch=s.request.epoch;send(platform::OutputCommand::Start);next();}else if(waitMs(2000))finish(true,"ack timeout");break;
            case 4:if(waitMs(500)){require(s.state==output::State::Running&&s.submittedFrames>0,"explicit Start rendered");mix_.masterMute=true;auto c=control(platform::OutputCommand::Mix);c.mix=mix_;output_.send(c);next();}break;
            case 5:if(waitMs(250)){mix_.masterMute=false;mix_.master=100;mix_.bus={100,100,100,100};mix_.muteMask=3;mix_.soloAB=1;auto c=control(platform::OutputCommand::Mix);c.mix=mix_;output_.send(c);next();}break;
            case 6:if(waitMs(250)){mix_.soloAB=2;auto c=control(platform::OutputCommand::Mix);c.mix=mix_;output_.send(c);next();}break;
            case 7:if(waitMs(250)){mix_.muteMask=15;auto c=control(platform::OutputCommand::Mix);c.mix=mix_;output_.send(c);next();}break;
            case 8:if(waitMs(250)){mix_={};auto c=control(platform::OutputCommand::Mix);c.mix=mix_;output_.send(c);send(platform::OutputCommand::Pause);next();}break;
            case 9:if(waitMs(250)){require(s.state==output::State::Paused&&s.ownsOutcome,"pause preserves owner");paused_=s;retainOutcome("pause-before-generation-handoff",s);send(platform::OutputCommand::PauseRetained);auto c=control(platform::OutputCommand::Resume);c.nextOwner=owner_;++c.nextOwner.generation;owner_=c.nextOwner;output_.send(c);next();}break;
            case 10:if(waitMs(500)){require(s.state==output::State::Running&&s.owner.generation==2,"fresh generation resume");auto c=control(platform::OutputCommand::Stop);c.owner.generation=1;output_.send(c);next();}break;
            case 11:if(waitMs(200)){require(s.state==output::State::Running,"stale Stop refused");send(platform::OutputCommand::Stop);send(platform::OutputCommand::Stop);next();}break;
            case 12:if(waitMs(250)){require(s.state==output::State::Unresolved&&s.pendingOutcome,"Stop preserves unresolved result");require(!output_.disconnect(),"disconnect refuses unresolved outcome");send(platform::OutputCommand::Start);next();}break;
            case 13:if(waitMs(150)){require(s.state==output::State::Unresolved,"Again before outcome resolution refused");terminal_=s;retainOutcome("terminal-before-original-owner-resolution",s);send(platform::OutputCommand::ResolveOutcome);next();}break;
            case 14:if(waitMs(150)){require(s.state==output::State::Ready&&!s.ownsOutcome,"test coordinator reconciled retained original outcome");require(output_.disconnect(),"explicit disconnect");next();}break;
            case 15:if(waitMs(250)){open();if(!done_)next();}break;
            case 16:if(s.state==output::State::Observed){require(!s.ownsOutcome&&s.submittedFrames==0,"reopen remains silent");next();}else if(waitMs(8000))finish(true,"reopen observation timeout");break;
            case 17:if(waitMs(250)){auto c=control(platform::OutputCommand::Acknowledge);c.token=s.observationToken;output_.send(c);next();}break;
            case 18:if(s.state==output::State::Ready){owner_.epoch=s.request.epoch;++owner_.generation;send(platform::OutputCommand::Start);next();}else if(waitMs(2000))finish(true,"reopen ack timeout");break;
            case 19:if(waitMs(350)){require(s.state==output::State::Running,"reopen explicit Start");next();}break;
            case 20:output_.injectFault(output::Fault::Sleep);next();break;
            case 21:if(waitMs(200)){require(s.state==output::State::Fault&&s.fault==output::Fault::Sleep&&s.pendingOutcome,"injected Sleep stopped with retained outcome");terminal_=s;retainOutcome("terminal-before-original-owner-resolution",s);send(platform::OutputCommand::ResolveOutcome);next();}break;
            case 22:if(waitMs(150)){require(!s.ownsOutcome,"fault outcome reconciled");require(output_.disconnect(),"sleep recovery disconnect");open();if(!done_)next();}break;
            case 23:if(s.state==output::State::Observed)next();else if(waitMs(8000))finish(true,"sleep recovery observation timeout");break;
            case 24:{auto c=control(platform::OutputCommand::Acknowledge);c.token=s.observationToken;output_.send(c);next();break;}
            case 25:if(s.state==output::State::Ready){owner_.epoch=s.request.epoch;++owner_.generation;send(platform::OutputCommand::Start);next();}else if(waitMs(2000))finish(true,"sleep recovery ack timeout");break;
            case 26:if(waitMs(350)){output_.injectFault(output::Fault::DeviceLost);next();}break;
            case 27:if(waitMs(200)){require(s.state==output::State::Fault&&s.fault==output::Fault::DeviceLost,"injected DeviceLost stopped");terminal_=s;retainOutcome("terminal-before-original-owner-resolution",s);send(platform::OutputCommand::ResolveOutcome);next();}break;
            case 28:if(waitMs(150)){require(!s.ownsOutcome,"device fault reconciled");require(output_.disconnect(),"device recovery disconnect");open();if(!done_)next();}break;
            case 29:if(s.state==output::State::Observed)next();else if(waitMs(8000))finish(true,"device recovery observation timeout");break;
            case 30:{auto c=control(platform::OutputCommand::Acknowledge);c.token=s.observationToken;output_.send(c);next();break;}
            case 31:if(s.state==output::State::Ready){owner_.epoch=s.request.epoch;++owner_.generation;send(platform::OutputCommand::Start);next();}else if(waitMs(2000))finish(true,"device recovery ack timeout");break;
            case 32:if(waitMs(350)){output_.injectFault(output::Fault::FormatMismatch);next();}break;
            case 33:if(waitMs(200)){require(s.state==output::State::Fault&&s.fault==output::Fault::FormatMismatch,"injected format change refused");terminal_=s;retainOutcome("terminal-before-original-owner-resolution",s);send(platform::OutputCommand::ResolveOutcome);next();}break;
            case 34:if(waitMs(150)){require(!s.ownsOutcome,"format fault reconciled");require(output_.disconnect(),"final disconnect");next();}break;
            case 35:if(waitMs(250))finish(false,"finite native lifecycle sequence completed");break;
            default:finish(true,"invalid step");
        }} catch(const Abort&) {}
    }
    platform::AudioOutputMac output_;Fixture fixture_;output::Owner owner_;output::MixSettings mix_;output::Snapshot paused_,terminal_;
    std::string root_,uid_;output::Format format_;std::ofstream events_,states_,outcomes_;std::size_t retained_{};std::uint64_t start_{},phase_{};int step_{};bool done_{},failed_{};
};
}
int main(int argc,char** argv) {
    if(argc==2&&std::string(argv[1])=="--preflight"){auto c=fathom::platform::defaultOutputCapability();std::cout<<juce::JSON::toString(capabilityJson(c))<<std::endl;return c.valid?0:1;}
    if(argc==2&&std::string(argv[1])=="--checks")return fathom::platform::OutputTestAccess::checks();
    if(argc==2&&std::string(argv[1])=="--loop-check") {
        const bool before=NSApp==nil;[NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyProhibited];
        juce::ScopedJuceInitialiser_GUI gui;bool dispatched=false;
        juce::Timer::callAfterDelay(100,[&]{dispatched=true;juce::MessageManager::getInstance()->stopDispatchLoop();});
        juce::MessageManager::getInstance()->runDispatchLoop();
        std::cout<<"NSApp_null_before="<<before<<" NSApp_present_after="<<(NSApp!=nil)<<" timer_dispatched="<<dispatched<<" audio_opened=0\n";
        return NSApp!=nil&&dispatched?0:1;
    }
    if(argc==6&&std::string(argv[1])=="--run") {[NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyProhibited];juce::ScopedJuceInitialiser_GUI gui;Run run(argv[2],argv[3],static_cast<std::uint32_t>(std::stoul(argv[4])),static_cast<std::uint32_t>(std::stoul(argv[5])));juce::MessageManager::getInstance()->runDispatchLoop();return run.result();}
    std::cerr<<"Usage: --preflight | --checks | --loop-check | --run EXISTING_EVIDENCE_DIR UID RATE FRAMES\n";return 2;
}
