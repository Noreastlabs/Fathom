#include "desktop/ReferenceView.hpp"
#include "desktop/SchedulerView.hpp"
#include "desktop/AudioOutputView.hpp"
#include "audio_preparation_software_leaves.hpp"
#include <filesystem>
#include <iostream>
#include <fstream>
#include <thread>
namespace fathom::desktop {
struct SharedAudioViewTestAccess {
 static void halt(AudioOutputView&v){v.stopTimer();}static std::string audioMessage(AudioOutputView&v){return v.status.getText().toStdString();}
 static void halt(ReferenceView&v){v.stopTimer();}static void halt(SchedulerView&v){v.stopTimer();}
 static void tick(ReferenceView&v){v.timerCallback();}static void tick(SchedulerView&v){v.timerCallback();}
 static platform::AudioOutputMac& output(ReferenceView&v){return v.output_;}static platform::AudioOutputMac& output(SchedulerView&v){return v.output;}
 static void* provider(ReferenceView&v){return v.playback_.get();}static void* provider(SchedulerView&v){return v.sound.get();}
 static output::Snapshot retained(ReferenceView&v){return v.retained_;}static output::Snapshot retained(SchedulerView&v){return v.retainedOutput;}
};
}
using namespace fathom;using A=desktop::SharedAudioViewTestAccess;
int checks=0;
static void ck(bool b,const std::string&m){++checks;if(!b)throw std::runtime_error(m);}
static juce::Button& ctl(juce::Component&v,const char*id){auto*p=dynamic_cast<juce::Button*>(v.findChildWithID(id));if(!p)throw std::runtime_error(id);return*p;}
static void press(juce::Component&v,const char*id){auto&b=ctl(v,id);ck(b.isEnabled(),std::string("enabled: ")+id);b.onClick();}
template<class V>void block(V&v,int n=1){for(int i=0;i<n;++i){platform::OutputTestAccess::block(A::output(v));A::tick(v);}}
template<class V>void snap(V&v,const std::filesystem::path&path){v.setSize(760,640);auto image=v.createComponentSnapshot(v.getLocalBounds());juce::FileOutputStream out(juce::File(path.string()));juce::PNGImageFormat png;ck(out.openedOk()&&png.writeImageToStream(image,out),"offscreen component image");}
template<class V>void run(const std::filesystem::path&root,bool reference){
 const char*begin=reference?"reference-play":"rhythm-start";const char*stop=reference?"reference-stop":"rhythm-stop";const char*finish=reference?"reference-done":"rhythm-finish";const char*back=reference?"reference-back":"rhythm-back";
 V v;A::halt(v);v.setSize(760,640);int backs=0;v.onBack=[&]{++backs;};const int opened=connections;
 ck(v.connectOutput(),"connect synthetic leaves only");ck(v.enableOutput(),"explicit Enable");block(v);ck(v.audioSnapshot().state==output::State::Ready,"Ready before explicit Start");const auto epoch=v.audioSnapshot().request.epoch;block(v,4);ck(!v.audioSnapshot().ownsOutcome,"preparation cannot allocate owner");
 output::Owner prior{};
 for(int repeat=0;repeat<3;++repeat){
  press(v,begin);block(v);auto running=v.audioSnapshot();ck(running.state==output::State::Running&&running.ownsOutcome,"explicit new run admitted");ck(!(running.owner==prior),"new owner identity each run");prior=running.owner;
  if(repeat==1){press(v,stop);block(v);}else{for(int n=0;n<2200&&!v.audioSnapshot().pendingOutcome;++n)block(v);}
  auto terminal=v.audioSnapshot();if(repeat!=1)ck(terminal.submittedFrames==(reference?132300U:432600U),"actual natural prefix has complete authored duration");ck(terminal.pendingOutcome&&terminal.ownsOutcome,"original outcome before Finish");ck(!v.audioCanRelease(),"no navigation before explicit original acknowledgment");ck(!ctl(v,begin).isEnabled(),"new Start disabled before Finish");ck(!v.connectOutput(),"cannot reconnect over pending original");
  press(v,finish);ck(!v.audioCanRelease(),"queued Finish is not cleanup proof");block(v,2);auto ready=v.audioSnapshot();ck(ready.state==output::State::Ready&&!ready.ownsOutcome&&!ready.pendingOutcome,"healthy ack retains Ready");ck(ready.request.epoch==epoch&&connections==opened+1,"no disconnect/reconnect for repeat");
  auto retained=A::retained(v);ck(retained.owner==terminal.owner&&retained.submittedFrames==terminal.submittedFrames&&retained.confirmedFrames==terminal.confirmedFrames,"original facts retained");ck(ctl(v,begin).isEnabled(),"another explicit Start enabled");const auto commands=A::output(v).status().commandAccepted;block(v,6);ck(v.audioSnapshot().state==output::State::Ready&&A::output(v).status().commandAccepted==commands,"idle ticks never enqueue another Start");
 }
 snap(v,root/(reference?"reference-ready.png":"rhythm-ready.png"));
 auto* originalProvider=A::provider(v);platform::OutputTestAccess::cleanupFailure(A::output(v),true);press(v,back);ck(backs==0&&A::provider(v)==originalProvider&&platform::hub.claimed,"failed synthetic cleanup retains provider and claim; no navigation");ck(!v.connectOutput()&&connections==opened+1&&A::provider(v)==originalProvider,"failed cleanup cannot replace provider or reopen device");
 // Test-only removal-listener failure leaf clears for bounded fixture cleanup;
 // no production recovery control or OS permission is changed.
 platform::OutputTestAccess::cleanupFailure(A::output(v),false);press(v,back);ck(backs==1&&v.audioSnapshot().state==output::State::Closed&&!platform::hub.claimed,"Back disconnects and releases provider claim");
 ck(v.connectOutput()&&v.enableOutput(),"fresh explicit Connect/Enable after Back");block(v);press(v,begin);block(v);platform::OutputTestAccess::faulted(A::output(v));A::tick(v);ck(v.audioSnapshot().state==output::State::Fault&&v.audioSnapshot().pendingOutcome,"fault keeps exact original outcome");ck(!ctl(v,begin).isEnabled(),"fault refuses Start");press(v,finish);block(v,2);ck(v.audioSnapshot().state==output::State::Closed&&!platform::hub.claimed,"fault acknowledgment closes instead of retaining Ready");ck(!ctl(v,begin).isEnabled(),"fault recovery requires new explicit preparation");
 ck(v.connectOutput()&&v.enableOutput(),"prepare capability-change boundary");block(v);const int count=connections;++capability.object;press(v,begin);ck(v.audioSnapshot().state==output::State::Closed&&connections==count&&!platform::hub.claimed,"changed device refuses Start and closes; no auto preparation");--capability.object;ck(v.requestClose(),"normal repeated close after no owner");
}
static void recoveryAdvice(const std::filesystem::path&root){
 using Session=desktop::SharedAudioSettings;using C=Session::Consumer;
 for(auto target:{C::Practice,C::Metronome,C::Reference,C::Rhythm}){
  Session session;bool allowed=true;int starts=0,opened=0,releases=0;output::Snapshot state;state.state=output::State::Closed;
  for(auto id:{C::Practice,C::Metronome,C::Reference,C::Rhythm}){
   std::string name=id==C::Practice?"Practice":id==C::Metronome?"Metronome":id==C::Reference?"Reference":"Rhythm";
   session.bind(id,{name,[]{return true;},[&]{return allowed;},[&]{return allowed;},[&]{++releases;return allowed;},[&]{++starts;return true;},[&](const platform::OutputCapability*){++opened;return true;},[](const output::MixSettings&){return true;},[&]{return state;},[]{return std::string{};},[](bool){}});
  }
  ck(session.activate(target),"activate exact stopped recovery owner");const auto before=releases;allowed=false;state.state=output::State::Unresolved;state.ownsOutcome=true;state.pendingOutcome=true;
  ck(!session.connect()&&!session.disconnect(),"recovery preserves original owner before Connect/Disconnect");const auto message=session.message();ck(message.find("Return to "+session.name()+".")!=std::string::npos&&message.find(output::stateText(state.state))!=std::string::npos,"recovery names actual activity and lifecycle blocker");
  ck(message.find(target==C::Practice?"Again":target==C::Reference?"Finish tone":"Finish check")!=std::string::npos,"recovery action belongs to actual activity");desktop::AudioOutputView screen;A::halt(screen);screen.setSize(760,640);screen.bind(session);const auto visible=A::audioMessage(screen);ck(visible.find(session.name())!=std::string::npos&&visible.find(target==C::Reference?"Finish tone":target==C::Practice?"Again":"Finish check")!=std::string::npos,"Audio visibly names exact original owner and recovery action");if(target==C::Reference)snap(screen,root/"reference-recovery-audio.png");
  ck(opened==0&&starts==0&&releases==before,"recovery advice never changes owner or enables output");
 }
}
int main(int argc,char**argv){try{ck(argc==2,"fresh fixture path");std::filesystem::path root=argv[1];ck(root.parent_path()==std::filesystem::path("/private/tmp")&&!std::filesystem::exists(root),"fresh private output only");std::filesystem::create_directory(root);juce::ScopedJuceInitialiser_GUI gui;recoveryAdvice(root);run<desktop::ReferenceView>(root,true);run<desktop::SchedulerView>(root,false);ck(nativeOpens==0&&maxClaims==1&&!platform::hub.claimed,"no native device open or competing claims");std::cout<<"PASS "<<checks<<" audio reuse checks; software callbacks only; nativeOpens="<<nativeOpens<<"\n";return 0;}catch(const std::exception&e){std::cerr<<"FAIL "<<checks<<": "<<e.what()<<"\n";return 1;}}
