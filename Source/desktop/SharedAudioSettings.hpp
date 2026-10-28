#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include "platform/AudioOutputMac.hpp"

namespace fathom::desktop {
// Message-thread settings only. The original consumer owns its provider, clock,
// outcome and event polling. Queue admission is not physical output evidence.
#if defined(FATHOM_SOFTWARE_SETTINGS_IO)
platform::OutputCapability settingsOutputCapability();
bool connectSettingsOutput(platform::AudioOutputMac&,const platform::OutputCapability&,output::Format,void*,platform::OutputObserver,platform::ScheduledRender);
#else
inline platform::OutputCapability settingsOutputCapability(){return platform::defaultOutputCapability();}
inline bool connectSettingsOutput(platform::AudioOutputMac& output,const platform::OutputCapability& cap,output::Format format,void* context,platform::OutputObserver observer,platform::ScheduledRender render){return output.connect(cap,format,nullptr,context,observer,render);}
#endif
inline bool sameAudioCapability(const platform::OutputCapability& a,const platform::OutputCapability& b) {
    return a.valid&&b.valid&&a.uid==b.uid&&a.object==b.object&&a.rate==b.rate
        &&a.physicalFrames==b.physicalFrames&&a.outputChannels==b.outputChannels
        &&a.minFrames==b.minFrames&&a.maxFrames==b.maxFrames;
}
inline bool queueAudioMix(platform::AudioOutputMac& output,const output::MixSettings& mix) {
    if(mix.master<0||mix.master>100||mix.muteMask>15||mix.soloAB>3)return false;
    for(auto gain:mix.bus)if(gain<0||gain>100)return false;
    const auto s=output.status().lifecycle;
    if(s.state==output::State::Closed||s.state==output::State::Fault)return true;
    platform::Control c;c.op=platform::OutputCommand::Mix;c.epoch=s.request.epoch;
    c.requestedNs=platform::monotonicNs();c.mix=mix;return output.send(c);
}
struct AudioEndpoint {
    std::string name;
    std::function<bool()> valid,canRelease,canPrepare,release,enable;
    std::function<bool(const platform::OutputCapability*)> connect;
    std::function<bool(const output::MixSettings&)> mix;
    std::function<output::Snapshot()> snapshot;
    std::function<std::string()> error;
    std::function<void(bool)> polling;
};
template<class View> AudioEndpoint audioEndpoint(View& view,std::string name) {
    const juce::Component::SafePointer<View> p(&view);
    return {std::move(name),[p]{return bool(p);},[p]{return p&&p->audioCanRelease();},[p]{return p&&p->audioCanPrepare();},
        [p]{return p&&p->audioRelease();},[p]{return p&&p->enableOutput();},
        [p](const platform::OutputCapability* c){return p&&p->connectOutput(c);},
        [p](const output::MixSettings& m){return p&&p->applyCommonMix(m);},
        [p]{return p?p->audioSnapshot():output::Snapshot{};},
        [p]{return p?p->audioError():std::string{"Playback view is no longer available."};},
        [p](bool active){if(p)p->setAudioPolling(active);}};
}
class SharedAudioSettings final {
public:
    enum class Consumer:std::size_t { Practice,Metronome,Reference,Rhythm,Count };
    void bind(Consumer id,AudioEndpoint endpoint) {
        endpoints_[index(id)]=std::move(endpoint);
        endpoints_[index(id)].polling(id==active_);
        if(id==active_){enableIntent_=false;pendingAck_=false;capability_.reset();}
    }
    void invalidatePreparation(){enableIntent_=false;pendingAck_=false;capability_.reset();message_="Audio preparation cleared. Reconnect explicitly after recovery.";}
    std::string deviceName()const{return capability_?capability_->name:"No output selected";}
    Consumer active()const noexcept{return active_;}
    const output::MixSettings& selected()const noexcept{return mix_;}
    const std::string& message()const noexcept{return message_;}
    std::string name()const{return endpoints_[index(active_)].name;}
    output::Snapshot snapshot()const {const auto& e=endpoint();return e.valid&&e.valid()?e.snapshot():output::Snapshot{};}
    std::string recoveryMessage()const{return recoveryInstruction();}
    bool canConnect()const {const auto& e=endpoint();return canRelease()&&e.canPrepare();}
    bool canRelease()const {const auto& e=endpoint();return e.valid&&e.valid()&&e.canRelease();}
    bool activate(Consumer id) {
        if(id==active_){
            if(!endpoint().valid||!endpoint().valid()){message_="Playback view is unavailable.";return false;}
            prepareAuthorized();return true;
        }
        auto& old=endpoint();auto& next=endpoints_[index(id)];
        if(!next.valid||!next.valid()){message_="Playback view unavailable; return to the original activity.";return false;}
        if(!next.canRelease()){message_="Resolve the pending settings or activity in "+next.name+" before changing playback sections.";return false;}
        const bool faulted=old.snapshot().state==output::State::Fault;
        if(!canRelease()||!old.release()){message_="Return to "+old.name+" and finish its original result or sound check before changing playback sections.";return false;}
        if(faulted)enableIntent_=false;
        old.polling(false);active_=id;next.polling(true);pendingAck_=false;
        // Activation is committed after the old endpoint released. A connection
        // failure belongs to this new caller; do not leave a mismatched old page.
        if(!next.mix(mix_)){message_="Resolve the pending settings save before changing audio.";return true;}
        message_.clear();prepareAuthorized();return true;
    }

    bool connect() {
        auto& e=endpoint();
        if(!canConnect()){message_=recoveryInstruction();return false;}
        if(!e.release()){message_=e.error();return false;}
        enableIntent_=false;pendingAck_=false;capability_.reset();
        const auto cap=settingsOutputCapability();
        if(!e.mix(mix_)||!e.connect(&cap)){message_=e.error();return false;}
        capability_=cap;message_.clear();return true;
    }
    bool enable() {
        auto& e=endpoint();const auto s=snapshot();
        if(!approvedObservation(s)||!e.mix(mix_)||!e.enable()){
            message_="Audio is not observed and ready to enable. Connect explicitly after resolving any current activity.";return false;
        }
        enableIntent_=true;pendingAck_=false;message_.clear();return true;
    }
    bool disconnect() {
        if(!canRelease()){message_=recoveryInstruction();return false;}
        if(!endpoint().release()){message_=endpoint().error();return false;}
        enableIntent_=false;pendingAck_=false;capability_.reset();message_.clear();return true;
    }
    bool selectMix(const output::MixSettings& value) {
        auto& e=endpoint();if(!e.valid||!e.valid()||!e.mix(value)){message_="Audio change refused. Resolve any pending settings save; prior values remain selected.";return false;}
        mix_=value;message_.clear();return true;
    }
    void selectedByConsumer(Consumer id,const output::MixSettings& value) {
        if(id==active_){mix_=value;message_.clear();}
    }
    // No service()/nextEvent() here: each active consumer alone polls its adapter.
    void observe() {
        const auto s=snapshot();
        if(s.state==output::State::Fault){pendingAck_=false;enableIntent_=false;message_=endpoint().error();return;}
        if(!pendingAck_)return;
        if(s.request.epoch!=pendingEpoch_){pendingAck_=false;enableIntent_=false;message_="Output epoch changed. Reconnect explicitly in Audio settings.";return;}
        if(s.state==output::State::Observed){
            pendingAck_=false;
            if(!approvedObservation(s)||!endpoint().mix(mix_)||!endpoint().enable()){enableIntent_=false;message_="Audio handoff could not enable. Reconnect explicitly; no sound started.";}
        }
    }
private:
    std::string recoveryInstruction()const{
        const auto& e=endpoint();const auto s=e.snapshot();
        const auto duty=active_==Consumer::Practice?"Resolve the original result, then Again.":
            active_==Consumer::Metronome?"Stop, wait for confirmation, then Finish check.":
            active_==Consumer::Reference?"Stop if needed, then Finish tone.":
            "Stop if needed, then Finish check.";
        return "Return to "+e.name+". "+duty+" Output: "+output::stateText(s.state)+". Then return to Audio to reconnect. Start stays explicit.";
    }
    bool approvedObservation(const output::Snapshot& s)const{
        if(!capability_||s.state!=output::State::Observed||!sameAudioCapability(settingsOutputCapability(),*capability_))return false;
        const auto& c=*capability_;const auto& o=s.observation;
        return s.request.selectedPhysical==c.object&&s.request.format.rate==c.rate
            &&s.request.format.frames==std::clamp(256U,c.minFrames,c.maxFrames)
            &&o.epoch==s.request.epoch&&o.physicalKnown&&o.ioKnown&&o.routeKnown
            &&o.selectedInFullRoute&&o.selectedInActiveRoute&&o.physicalObject==c.object
            &&o.physicalRate==c.rate&&o.physicalFrames==c.physicalFrames
            &&o.queriedIO==s.request.format&&o.callbackFrames==s.request.format.frames;
    }
    void prepareAuthorized(){
        auto& e=endpoint();
        if(!enableIntent_||!capability_||e.snapshot().state!=output::State::Closed)return;
        if(!e.canPrepare()){message_=recoveryInstruction();return;}
        if(!e.connect(&*capability_)){enableIntent_=false;message_=e.error().empty()?"Output changed or could not connect. Open Audio settings and reconnect explicitly.":e.error();return;}
        pendingAck_=true;pendingEpoch_=e.snapshot().request.epoch;
    }
    static constexpr std::size_t index(Consumer id){return static_cast<std::size_t>(id);}
    AudioEndpoint& endpoint(){return endpoints_[index(active_)];}
    const AudioEndpoint& endpoint()const{return endpoints_[index(active_)];}
    std::array<AudioEndpoint,static_cast<std::size_t>(Consumer::Count)> endpoints_;
    Consumer active_{Consumer::Practice};
    output::MixSettings mix_;
    std::optional<platform::OutputCapability> capability_;
    bool enableIntent_{},pendingAck_{};
    std::uint64_t pendingEpoch_{};
    std::string message_;
};
}
