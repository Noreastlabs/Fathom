// Actual desktop/Store/adapter paths; only capability and device-open leaves are synthetic.
#include "../Source/platform/AudioOutputMac.mm"
#include "shared_audio_test_access.hpp"
#include "practice_capture_fixtures.hpp"
#include <atomic>
#include <mutex>
#include <iostream>
#include <sstream>
#include <array>
#include <iomanip>
using namespace fathom;
using H=desktop::HomeView;
using A=desktop::SharedAudioViewTestAccess;
using P=desktop::PracticeViewTestAccess;
namespace {
int nativeOpens{},connections{},maxClaims{};std::vector<std::string> ioLog;
platform::OutputCapability capability{true,87,44100,512,2,32,2048,"synthetic:direct","Software fixture; not hardware","",{{44100,44100}}};
struct SoftwareDevice final:juce::AudioIODevice {
 SoftwareDevice():AudioIODevice("Software fixture","test"){}
 juce::StringArray getOutputChannelNames()override{return {"L","R"};}juce::StringArray getInputChannelNames()override{return {};}
 juce::Array<double> getAvailableSampleRates()override{return {44100};}juce::Array<int> getAvailableBufferSizes()override{return {256};}
 int getDefaultBufferSize()override{return 256;}juce::String open(const juce::BigInteger&,const juce::BigInteger&,double,int)override{++nativeOpens;return "Forbidden";}
 void close()override{ioLog.push_back("close");}bool isOpen()override{return true;}void start(juce::AudioIODeviceCallback*)override{++nativeOpens;}void stop()override{ioLog.push_back("stop");}bool isPlaying()override{return false;}juce::String getLastError()override{return {};}
 int getCurrentBufferSizeSamples()override{return 256;}double getCurrentSampleRate()override{return 44100;}int getCurrentBitDepth()override{return 32;}
 juce::BigInteger getActiveOutputChannels()const override{juce::BigInteger b;b.setRange(0,2,true);return b;}juce::BigInteger getActiveInputChannels()const override{return {};}
 int getOutputLatencyInSamples()override{return 0;}int getInputLatencyInSamples()override{return 0;}
 };
void pump(){@autoreleasepool {CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.001,true);if(auto* e=[NSApp nextEventMatchingMask:NSEventMaskAny untilDate:[NSDate dateWithTimeIntervalSinceNow:0.001] inMode:NSDefaultRunLoopMode dequeue:YES])[NSApp sendEvent:e];}}
void activate(juce::Button& button){struct Listener final:juce::Button::Listener{bool delivered{};void buttonClicked(juce::Button*)override{delivered=true;}} listener;button.addListener(&listener);button.triggerClick();const auto until=capture_fixture::now()+2000;while(!listener.delivered&&capture_fixture::now()<until)pump();button.removeListener(&listener);if(!listener.delivered)throw std::runtime_error("button dispatch watchdog");}
void marker(){bool reached=false;juce::MessageManager::callAsync([&]{reached=true;});const auto until=capture_fixture::now()+2000;while(!reached&&capture_fixture::now()<until)pump();if(!reached)throw std::runtime_error("marker watchdog");}
juce::Button& button(juce::Component& c,const std::string& name){for(auto* child:c.getChildren()){if(auto* b=dynamic_cast<juce::Button*>(child);b&&b->getButtonText().toStdString()==name)return *b;}throw std::runtime_error("Missing button "+name);}
// Historical campaigns request these route names; assertions below test the
// current visible controls. A removed duplicate is never dispatched directly.
void click(juce::Component& c,const std::string& name){
 auto actual=name;
 if(dynamic_cast<desktop::HomeView*>(&c)){
  if(name=="Start learning"||name=="Continue selected case"||name=="Practice (choose in Learn)")actual="Learn";
  else if(name=="Review selected case")actual="Exercise details";
 }
 if(name=="Back"&&dynamic_cast<desktop::LessonView*>(&c)){
  // The retained case Back now names its destination; hidden case controls
  // must never substitute for the visible source-hierarchy Back.
  if(auto* back=dynamic_cast<juce::Button*>(c.findChildWithID("back"));back&&back->isVisible())actual=back->getButtonText().toStdString();
 }
 const auto visibleButton=[&](auto&& self,juce::Component& root)->juce::Button*{
  if(auto* candidate=dynamic_cast<juce::Button*>(&root);candidate&&candidate->isVisible()&&candidate->getButtonText().toStdString()==actual)return candidate;
  for(auto* child:root.getChildren())if(child->isVisible())if(auto* found=self(self,*child))return found;
  return nullptr;
 };
 auto* b=visibleButton(visibleButton,c);if(!b||!b->isEnabled()||!c.getLocalBounds().contains(b->getBounds()))throw std::runtime_error("Button not usable "+actual);activate(*b);
}

bool equal(const output::MixSettings& a,const output::MixSettings& b){return a.master==b.master&&a.bus==b.bus&&a.masterMute==b.masterMute&&a.muteMask==b.muteMask&&a.soloAB==b.soloAB;}
// Measure the actual caption through its drawing font and text insets, independently
// of the production row's weights or target pixel widths.
bool stopCaptionFits(desktop::PracticeView& view){
 auto* stop=dynamic_cast<juce::TextButton*>(view.findChildWithID("practice-stop"));
 if(!stop||!stop->isVisible()||!stop->isEnabled()||stop->getButtonText()!="Stop & review result")return false;
 const auto font=stop->getLookAndFeel().getTextButtonFont(*stop,stop->getHeight());
 const int corner=std::min(stop->getHeight(),stop->getWidth())/2;
 const int fontInset=juce::roundToInt(font.getHeight()*0.6f);
 const int left=std::min(fontInset,2+corner/(stop->isConnectedOnLeft()?4:2));
 const int right=std::min(fontInset,2+corner/(stop->isConnectedOnRight()?4:2));
 return juce::GlyphArrangement::getStringWidth(font,stop->getButtonText())<=stop->getWidth()-left-right;
}
bool transportContainedAndSeparate(desktop::PracticeView& view){
 std::vector<juce::Component*> controls;
 for(const auto* id:{"practice-audio-settings","practice-start","practice-pause","practice-resume","practice-stop","lesson-tempo","scheduled-passes"}){
  auto* control=view.findChildWithID(id);if(!control)return false;
  if(control->isVisible())controls.push_back(control);
 }
 for(auto* child:view.getChildren())if(auto* setup=dynamic_cast<juce::TextButton*>(child);setup&&setup->isVisible()&&(setup->getButtonText()=="Show setup details"||setup->getButtonText()=="Hide setup details"))controls.push_back(setup);
 for(std::size_t i=0;i<controls.size();++i){
  const auto bounds=controls[i]->getBounds();if(bounds.isEmpty()||!view.getLocalBounds().contains(bounds))return false;
  for(std::size_t j=0;j<i;++j)if(bounds.intersects(controls[j]->getBounds()))return false;
 }
 return !controls.empty();
}
}
namespace fathom::platform {
struct OutputTestAccess {
 inline static bool deferObservation=false; // Exercise asynchronous native handoff timing with software I/O only.
 static bool attach(AudioOutputMac& o,const OutputCapability& c,output::Format format,void* context,OutputObserver observer,ScheduledRender render){
  auto& p=*o.p_;bool free=false;if(!hub.claimed.compare_exchange_strong(free,true))return false;
  output::Observation discard;while(p.queries.pop(discard)){} output::CachedAnnouncement old;while(p.announcements.pop(old)){} Control command;while(p.normal.pop(command)){}while(p.urgent.pop(command)){} p.latestQuery={};p.firstSilentCallbackNs=0;p.silenceOwner={};p.lastError.clear();p.expectedStop.store(false);hub.expectedIO.store(0);
  p.claimed=true;p.epoch=epochCounter.fetch_add(1)+1;p.requested=format;p.quiescent=true;p.device=std::make_unique<SoftwareDevice>();p.context=context;p.observer=observer;p.scheduled=render;p.capability=c;
  nativeSequence=1;hub.epoch.store(p.epoch);hub.faultWord.store(tagged(p.epoch,0));hub.ioWord.store(tagged(p.epoch,c.object));hub.armed.store(false);hub.frames.store(format.frames);
  if(!p.life.configure({static_cast<std::uint64_t>(p.epoch),1,format,c.object})||!p.life.announce({static_cast<std::uint64_t>(p.epoch),2,format}))throw std::runtime_error("Synthetic configure");
  p.latestQuery={static_cast<std::uint64_t>(p.epoch),1,4,3,format,format.frames,c.object,c.object,c.object,c.rate,c.physicalFrames,true,true,true,true,true};
  if(!deferObservation)p.life.observe(p.latestQuery);p.view.lifecycle=p.life.snapshot();++connections;maxClaims=std::max(maxClaims,int(hub.claimed));ioLog.push_back("connect:"+std::to_string(p.epoch)+":"+(context?"provider":"NULL"));return context&&observer&&render;
 }
 static float block(AudioOutputMac& o){auto& p=*o.p_;if(!p.device)return 0;nativeEpoch=p.epoch;nativeObject=p.capability.object;nativeFrames=p.requested.frames;++nativeSequence;std::array<float,256> l{},r{};float* channels[]{l.data(),r.data()};juce::AudioIODeviceCallbackContext context{};p.audioDeviceIOCallbackWithContext(nullptr,0,channels,2,256,context);float peak{};for(auto f:l)peak=std::max(peak,std::abs(f));return peak;}
 static void queued(AudioOutputMac& o,bool queued){o.p_->quiescent=!queued;}
 static void observedFrames(AudioOutputMac& o,std::uint32_t frames){o.p_->view.lifecycle.observation.physicalFrames=frames;}
 static void event(NativeEvent e){emit(e);}
 static bool consume(NativeEvent& e){return hub.events.pop(e);}
 static void faulted(AudioOutputMac& o){o.p_->life.invalidate(o.p_->epoch,output::Fault::Backend,10,0);o.p_->view.lifecycle=o.p_->life.snapshot();}
};
}
namespace fathom::desktop {
platform::OutputCapability settingsOutputCapability(){return capability;}
bool connectSettingsOutput(platform::AudioOutputMac& output,const platform::OutputCapability& cap,output::Format format,void* context,platform::OutputObserver observer,platform::ScheduledRender render){return platform::OutputTestAccess::attach(output,cap,format,context,observer,render);}
}
struct Harness {
 std::filesystem::path dir;std::atomic<int> mode{0};std::atomic<bool> entered{false},release{false},startupEntered{false},startupReleased{false};bool startupGate{},startupWaitObserved{};std::ofstream hooks;
 std::unique_ptr<storage::ProfileStore> store;std::unique_ptr<H> home;std::string sessionId;
 Harness(const std::filesystem::path& base,const std::string& name,bool gateStartup=false):dir(base/name),startupGate(gateStartup){std::filesystem::create_directory(dir);std::filesystem::permissions(dir,std::filesystem::perms::owner_all);hooks.open(dir/"hooks.tsv");storage::StoreOptions options;options.path=dir/"profile.sqlite";options.create=true;options.createdUtc="2026-09-08T16:00:00Z";options.preferenceValidator=desktop::presentation::composedPreferenceValidator;
  options.diagnosticHook=[this](const std::string& phase,const std::string& op){if(startupGate&&phase=="before_operation"&&op.rfind("learn-suite/discover/",0)==0){startupEntered=true;const auto end=capture_fixture::now()+8000;while(!startupReleased){if(capture_fixture::now()>end)throw std::runtime_error("startup read barrier watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}}
  hooks<<phase<<'\t'<<op<<'\n';hooks.flush();const int m=mode.load();const bool final=op.size()>=12&&op.compare(op.size()-12,12,".save.commit")==0;
   if(m==4&&phase=="before_operation"){mode=0;entered=true;const auto end=capture_fixture::now()+8000;while(!release){if(capture_fixture::now()>end)throw std::runtime_error("barrier watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}}
   if(final&&((m==1&&phase=="before_commit")||(m==2&&phase=="after_commit")||(m==3&&phase=="before_commit"))){mode=0;entered=true;if(m==3){const auto end=capture_fixture::now()+8000;while(!release){if(capture_fixture::now()>end)throw std::runtime_error("save barrier watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}}else throw std::runtime_error(m==1?"Synthetic precommit failure":"Synthetic lost receipt");}};
  store=std::make_unique<storage::ProfileStore>(options);const auto session=capture_fixture::confirmed(store->createSession(storage::newUuid(),options.createdUtc,"America/New_York",{},json::Value::Object{{"synthetic_fixture",true}}));sessionId=session.owner;home=std::make_unique<H>();home->setVisible(true);home->setSize(920,680);if(!home->configureCapture(*store,session.owner,"America/New_York"))throw std::runtime_error("configure capture");A::halt(*home);std::cout<<"HARNESS_STARTUP_INITIAL "<<A::navigationFacts(*home)<<"\n";
  wait([&]{if(startupGate&&startupEntered&&!startupReleased){if(A::startupReadSettled(*home))throw std::runtime_error("blocked original discovery falsely settled");startupWaitObserved=true;startupReleased=true;}return A::metronome(*home).preferencesReady()&&A::startupReadSettled(*home);},"preferences and original suite discovery");
  if(startupGate&&(!startupEntered||!startupWaitObserved||nativeOpens!=0))throw std::runtime_error("original startup barrier/device contract");
  std::cout<<"HARNESS_STARTUP_FINAL "<<A::navigationFacts(*home)<<" blockedOriginalReadWitness="<<startupWaitObserved<<"\n";
 }
 ~Harness(){startupReleased=true;release=true;home.reset();store.reset();}
 desktop::PracticeView& practice(){return A::practice(*home);}void tick(){A::tick(*home);}
 template<class F>void wait(F p,const std::string& label){const auto end=capture_fixture::now()+7000;while(!p()){if(capture_fixture::now()>end)throw std::runtime_error(label+" watchdog "+home->audioSettings().message());tick();pump();}}
 void blocks(int n){for(int i=0;i<n;++i){platform::OutputTestAccess::block(A::output(*home));tick();}}
 void setup(){click(*home,"Audio settings");tick();click(A::settings(*home),"Connect audio");tick();click(A::settings(*home),"Enable audio");blocks(1);click(A::settings(*home),"Back to Home");home->navigate(H::Page::Practice);practice().showTab(true);tick();}
 void start(){click(practice(),"Start sample");wait([&]{return practice().captureSession()->startTaken();},"start");blocks(1);}
 void end(){blocks(1100);wait([&]{return practice().captureSession()->phase()==capture::SessionPhase::Review;},"review");}
 void detour(){tick();click(practice(),"Audio settings");tick();click(A::settings(*home),"Back to Practice");tick();}
 std::size_t finals(){auto s=capture_fixture::confirmed(store->snapshot(storage::newUuid()));capture_fixture::write(dir/"snapshot.json",storage::canonical(s.data));return s.data.find("authoritative")->find("finalized")->array().size();}
 void image(const std::string& name){for(auto size:{std::pair{920,680},std::pair{1280,800}}){home->setSize(size.first,size.second);tick();auto image=home->createComponentSnapshot(home->getLocalBounds());juce::FileOutputStream out(juce::File((dir/(name+"-"+std::to_string(size.first)+".png")).string()));juce::PNGImageFormat png;if(!out.openedOk()||!png.writeImageToStream(image,out))throw std::runtime_error("image");out.flush();}home->setSize(920,680);}
};
int main(int argc,char** argv){int checks{};std::ofstream out;try{
 const bool shutdownTools=argc==3&&std::string(argv[2])=="--shutdown-tools";
 if(shutdownTools)argc=2;
 const bool remainingAfterTransport=argc==3&&std::string(argv[2])=="--remaining-after-transport";
 const bool lessonRhythmActiveContext=argc==3&&std::string(argv[2])=="--lesson-rhythm-active-context";
 if(lessonRhythmActiveContext)argc=2; // The existing validator still checks the absolute, absent evidence directory.
 const bool tail=argc==3&&std::string(argv[2])=="--tail";const bool remainder=argc==3&&(std::string(argv[2])=="--remaining"||remainingAfterTransport);const bool freeplayContext=argc==3&&std::string(argv[2])=="--freeplay-context";const bool homeNavigationSmoke=argc==3&&std::string(argv[2])=="--home-navigation-smoke";const bool homeStartLearningAttempt=argc==3&&std::string(argv[2])=="--home-start-learning-attempt";const bool homeStartLearningSearchRoute=argc==3&&std::string(argv[2])=="--home-start-learning-search-route";const bool homePracticeEntry=argc==3&&std::string(argv[2])=="--home-practice-entry";const bool homeAudioEntry=argc==3&&std::string(argv[2])=="--home-audio-entry";const bool homeReferenceEntry=argc==3&&std::string(argv[2])=="--home-reference-entry";const bool homeProgressEntry=argc==3&&std::string(argv[2])=="--home-progress-entry";const bool homeFreeplayEntry=argc==3&&std::string(argv[2])=="--home-freeplay-entry";const bool homeMetronomeEntry=argc==3&&std::string(argv[2])=="--home-metronome-entry";const bool restoredPreferencesStopped=argc==3&&std::string(argv[2])=="--restored-preferences-stopped";const bool homeRhythmEntry=argc==3&&std::string(argv[2])=="--home-rhythm-entry";const bool homeProfileBoundary=argc==3&&std::string(argv[2])=="--home-profile-boundary";const bool homeAboutSurface=argc==3&&std::string(argv[2])=="--home-about-surface";const bool homeGuitarSetupSurface=argc==3&&std::string(argv[2])=="--home-guitar-setup-surface";const bool homeGuitarSetupApply=argc==3&&std::string(argv[2])=="--home-guitar-setup-apply";const bool homeGuitarSetupInvalidRecovery=argc==3&&std::string(argv[2])=="--home-guitar-setup-invalid-recovery";const bool homeGuitarSetupOrientationApply=argc==3&&std::string(argv[2])=="--home-guitar-setup-orientation-apply";const bool homeGuitarSetupCustomApply=argc==3&&std::string(argv[2])=="--home-guitar-setup-custom-apply";const bool homeProgressEmpty=argc==3&&std::string(argv[2])=="--home-progress-empty";const bool homeProgressAttachedEmpty=argc==3&&std::string(argv[2])=="--home-progress-attached-empty";const bool homeProgressLearnHandoff=argc==3&&std::string(argv[2])=="--home-progress-learn-handoff";const bool homeProgressLearnPracticeHandoff=argc==3&&std::string(argv[2])=="--home-progress-learn-practice-handoff";const bool homeProgressLearnPracticeProvenance=argc==3&&std::string(argv[2])=="--home-progress-learn-practice-provenance";const bool homeProgressLearnPracticeTabToggle=argc==3&&std::string(argv[2])=="--home-progress-learn-practice-tab-toggle";const bool homeProgressLearnPracticeAudioSave=argc==3&&std::string(argv[2])=="--home-progress-learn-practice-audio-save";const bool practiceSaveProgressReview=argc==3&&std::string(argv[2])=="--practice-save-progress-review";const bool savedProgressLearnReturn=argc==3&&std::string(argv[2])=="--saved-progress-learn-return";const bool savedProgressRefreshReview=argc==3&&std::string(argv[2])=="--saved-progress-refresh-review";const bool homeSurfaceOnly=argc==3&&(std::string(argv[2])=="--home-surface"||std::string(argv[2])=="--presentation-stop-gates");const bool freeplaySurfaceOnly=argc==3&&std::string(argv[2])=="--freeplay-surface";const bool audioSurfaceOnly=argc==3&&std::string(argv[2])=="--audio-surface";const bool audioKeyboardPeer=argc==3&&std::string(argv[2])=="--audio-keyboard-peer";const bool audioResponsiveOnly=argc==3&&std::string(argv[2])=="--audio-responsive-layout";const bool rhythmResponsiveOnly=argc==3&&std::string(argv[2])=="--rhythm-responsive-layout";const bool referenceResponsiveOnly=argc==3&&std::string(argv[2])=="--reference-responsive-layout";const bool rhythmSurfaceOnly=argc==3&&std::string(argv[2])=="--rhythm-surface";const bool rhythmLayerControlsOnly=argc==3&&std::string(argv[2])=="--rhythm-layer-controls";const bool rhythmRatioSelectionOnly=argc==3&&std::string(argv[2])=="--rhythm-ratio-selection";const bool rhythmLayerVolumesOnly=argc==3&&std::string(argv[2])=="--rhythm-layer-volumes";const bool rhythmRatioLayerRoutingOnly=argc==3&&std::string(argv[2])=="--rhythm-ratio-layer-routing";const bool rhythmSharedCycleOnly=argc==3&&(std::string(argv[2])=="--rhythm-shared-cycle"||std::string(argv[2])=="--rhythm-playhead-cycle"||rhythmLayerControlsOnly||rhythmRatioSelectionOnly||rhythmLayerVolumesOnly||rhythmRatioLayerRoutingOnly);const bool learnRefusedPracticeTitle=argc==3&&std::string(argv[2])=="--learn-refused-practice-title";if((argc!=2&&!remainder&&!tail&&!freeplayContext&&!homeNavigationSmoke&&!homeStartLearningAttempt&&!homeStartLearningSearchRoute&&!homePracticeEntry&&!homeAudioEntry&&!homeReferenceEntry&&!homeProgressEntry&&!homeFreeplayEntry&&!homeMetronomeEntry&&!restoredPreferencesStopped&&!homeRhythmEntry&&!homeProfileBoundary&&!homeAboutSurface&&!homeGuitarSetupSurface&&!homeGuitarSetupApply&&!homeGuitarSetupInvalidRecovery&&!homeGuitarSetupOrientationApply&&!homeGuitarSetupCustomApply&&!homeProgressEmpty&&!homeProgressAttachedEmpty&&!homeProgressLearnHandoff&&!homeProgressLearnPracticeHandoff&&!homeProgressLearnPracticeProvenance&&!homeProgressLearnPracticeTabToggle&&!homeProgressLearnPracticeAudioSave&&!practiceSaveProgressReview&&!savedProgressLearnReturn&&!savedProgressRefreshReview&&!homeSurfaceOnly&&!freeplaySurfaceOnly&&!audioSurfaceOnly&&!audioKeyboardPeer&&!audioResponsiveOnly&&!rhythmResponsiveOnly&&!referenceResponsiveOnly&&!rhythmSurfaceOnly&&!rhythmSharedCycleOnly&&!learnRefusedPracticeTitle)||!std::filesystem::path(argv[1]).is_absolute()||std::filesystem::exists(argv[1]))throw std::runtime_error("New absolute evidence path required");const std::filesystem::path dir=argv[1];std::filesystem::create_directories(dir);out.open(dir/"checks.tsv");juce::ScopedJuceInitialiser_GUI gui;
 auto ck=[&](bool okay,const std::string& text){++checks;out<<text<<'\t'<<(okay?"PASS":"FAIL")<<'\n';out.flush();if(!okay)throw std::runtime_error(text);};
 if(shutdownTools){
  for(const bool reference:{true,false})for(const bool pendingStart:{false,true})for(const bool manualStop:{false,true}){
   if(pendingStart&&manualStop)continue;
   const auto label=std::string(reference?"Reference":"Rhythm")+(pendingStart?" pending Start":" running")+(manualStop?" manual Stop":"");
   Harness h(dir,(reference?"reference":"rhythm")+std::string(pendingStart?"-quit-pending":"-quit-running")+(manualStop?"-manual-stop":""),reference&&!pendingStart&&!manualStop);
   auto& tone=A::reference(*h.home);auto& rhythm=A::rhythm(*h.home);
   const auto requestClose=[&]{return reference?tone.requestClose():rhythm.requestClose();};
   ck(requestClose()&&requestClose(),label+" idle repeated Quit is safe without opening audio");
   const bool opened=h.home->navigate(reference?H::Page::Reference:H::Page::Rhythm);
   if(!opened)std::cout<<"SHUTDOWN_TOOL_NAVIGATION_REFUSED "<<A::navigationFacts(*h.home)<<"\n";
   ck(opened,label+" opens its existing tool");
   ck(reference?tone.connectOutput():rhythm.connectOutput(),label+" synthetic output connects");
   ck(reference?tone.enableOutput():rhythm.enableOutput(),label+" output enables explicitly");
   h.blocks(1);auto& output=A::output(*h.home);
   auto& component=reference?static_cast<juce::Component&>(tone):static_cast<juce::Component&>(rhythm);
   if(pendingStart)platform::OutputTestAccess::queued(output,true);
   click(component,reference?"Play tone":"Start preview");
   if(!pendingStart)h.blocks(2);
   const auto original=output.status().lifecycle;
   const auto acceptedBefore=output.status().commandAccepted;
   const auto before=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
   platform::OutputTestAccess::queued(output,true);
   if(manualStop)click(component,"Stop");
   for(int quit=0;quit<12;++quit)ck(!requestClose(),label+" repeated Quit retains its original check "+std::to_string(quit));
   platform::OutputTestAccess::block(output);platform::OutputTestAccess::queued(output,false);h.tick();
   auto stopped=output.status().lifecycle;
   if(pendingStart){
    ck(stopped.state==output::State::Closed&&!stopped.ownsOutcome&&!stopped.pendingOutcome
       &&stopped.submittedFrames==0&&requestClose(),label+" cancels before sound and closes without inventing output");
   }else{
    ck(stopped.state==output::State::Unresolved&&stopped.ownsOutcome&&stopped.pendingOutcome
       &&stopped.owner==original.owner&&stopped.submittedFrames==original.submittedFrames
       &&output.status().commandAccepted==acceptedBefore+1,label+" requests exactly one Stop and retains exact terminal ownership/frames");
    const auto terminal=stopped;const auto accepted=output.status().commandAccepted;
    ck(!requestClose()&&!requestClose(),label+" terminal check still requires its existing explicit acknowledgment");
    h.blocks(1);stopped=output.status().lifecycle;
    ck(stopped.owner==terminal.owner&&stopped.requestedStopNs==terminal.requestedStopNs
       &&stopped.submittedFrames==terminal.submittedFrames&&output.status().commandAccepted==accepted,
       label+" repeated terminal Quit preserves Stop provenance and does not resolve the outcome");
    click(component,reference?"Finish tone":"Finish check");h.tick();
    ck(requestClose()&&requestClose()&&output.status().lifecycle.state==output::State::Closed,
       label+" explicit acknowledgment releases the original check before Quit becomes ready");
    if(!reference)ck(A::rhythmOutput(*h.home).owner==terminal.owner
       &&A::rhythmOutput(*h.home).submittedFrames==terminal.submittedFrames,label+" retains the original Rhythm outcome after release");
   }
   const auto after=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
   ck(after.data.find("authoritative")&&before.data.find("authoritative")
      &&*after.data.find("authoritative")==*before.data.find("authoritative"),label+" Quit creates no learner history or curriculum authority");
  }
  for(const bool reference:{true,false}){
   Harness h(dir,reference?"reference-quit-rejected":"rhythm-quit-rejected");auto& tone=A::reference(*h.home);auto& rhythm=A::rhythm(*h.home);
   ck(h.home->navigate(reference?H::Page::Reference:H::Page::Rhythm),"queue rejection fixture opens its original tool");
   ck(reference?tone.connectOutput():rhythm.connectOutput(),"queue rejection fixture connects synthetic output");
   ck(reference?tone.enableOutput():rhythm.enableOutput(),"queue rejection fixture enables explicitly");h.blocks(1);
   auto& component=reference?static_cast<juce::Component&>(tone):static_cast<juce::Component&>(rhythm);
   click(component,reference?"Play tone":"Start preview");h.blocks(2);auto& output=A::output(*h.home);const auto original=output.status().lifecycle;
   platform::OutputTestAccess::queued(output,true);platform::Control stop;stop.op=platform::OutputCommand::Stop;stop.epoch=original.request.epoch;stop.owner=original.owner;
   for(int queued=0;queued<8;++queued)ck(output.send(stop),"queue rejection fixture fills the bounded urgent queue");
   ck(!(reference?tone.requestClose():rhythm.requestClose()),"rejected Quit Stop retains the original tool");
   platform::OutputTestAccess::block(output);platform::OutputTestAccess::queued(output,false);h.tick();const auto fault=output.status().lifecycle;
   ck(fault.state==output::State::Fault&&fault.fault==output::Fault::QueueOverflow&&fault.owner==original.owner
      &&fault.ownsOutcome&&fault.pendingOutcome&&fault.submittedFrames==original.submittedFrames,
      "rejected Stop uses the existing output fault path and retains exact original ownership/frames");
   ck(!(reference?tone.requestClose():rhythm.requestClose()),"queue fault remains held for the existing acknowledgment");
   click(component,reference?"Finish tone":"Finish check");h.tick();
   ck(reference?tone.requestClose():rhythm.requestClose(),"explicit acknowledgment safely releases the queue-fault original");
  }
  {
   Harness h(dir,"paused-freeplay-reopen");auto& freeplay=A::freeplay(*h.home);std::uint64_t now{};
   freeplay.setClockForTest([&]{return now;});ck(h.home->navigate(H::Page::Freeplay)&&freeplay.startFreeplay(),"paused reopen fixture starts Freeplay");
   now=2'000'000'000ULL;ck(freeplay.pauseFreeplay()&&freeplay.canLeave(),"paused Freeplay navigation retains its current interval");
   const auto* practice=&h.practice();const auto before=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
   ck(!h.home->detachForStoreReopen()&& &h.practice()==practice&&freeplay.activeNanoseconds()==2'000'000'000ULL
      &&!freeplay.persistencePending()&&!freeplay.persistenceSaved()&&freeplay.historyWriteCount()==0,
      "Home refuses profile reopen while Freeplay is paused without replacing views or stopping/saving its retained interval");
   const auto after=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
   ck(*before.data.find("authoritative")==*after.data.find("authoritative"),"refused paused Freeplay reopen leaves exact profile authority unchanged");
  }
  ck(nativeOpens==0,"shutdown tool checks open no native audio");
  std::cout<<"PASS "<<checks<<" software shutdown-tool checks\n";return 0;
 }
 if(audioKeyboardPeer){
  std::ofstream keys(dir/"focus-keys.tsv");keys<<"width\tfrom\tkey\texpected\tactual\tresult\n";int failures=0;
  const auto peerCheck=[&](bool okay,const std::string& text){++checks;failures+=!okay;out<<text<<'\t'<<(okay?"PASS":"FAIL")<<'\n';out.flush();};
  for(const int width:{640,920}){
   desktop::AudioOutputView view;view.setSize(width,680);int returned=0;view.onBack=[&]{++returned;};view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);view.setVisible(true);
   auto* peer=view.getPeer();juce::KeyboardFocusTraverser traverser;const auto order=traverser.getAllComponents(&view);
   const auto named=[&](const juce::Component* component){for(auto* current=component;current&&current!=&view;current=current->getParentComponent())if(current->getComponentID().isNotEmpty())return current->getComponentID().toStdString()+(current==component?"":":text");return std::string{"<none>"};};
   std::vector<std::string> ids;for(auto* component:order)ids.push_back(named(component));
   peerCheck(peer&&view.isShowing()&&!order.empty(),"detached Audio has visible desktop peer and focus controls at "+std::to_string(width));
   bool valid=true;for(auto* component:order)valid=valid&&component->isShowing()&&component->isEnabled()&&component->getWantsKeyboardFocus()&&component->getWidth()>0&&component->getHeight()>0&&view.getLocalBounds().contains(view.getLocalArea(component,component->getLocalBounds()));
   peerCheck(valid,"detached Audio focus controls are enabled, visible and contained at "+std::to_string(width));
   const auto image=view.createComponentSnapshot(view.getLocalBounds());juce::FileOutputStream imageOut(juce::File((dir/("audio-keyboard-"+std::to_string(width)+".png")).string()));juce::PNGImageFormat png;const bool saved=imageOut.openedOk()&&png.writeImageToStream(image,imageOut);imageOut.flush();peerCheck(saved&&!imageOut.getStatus().failed(),"detached Audio desktop screenshot saved at "+std::to_string(width));
   if(peer&&!order.empty()){
    order.front()->grabKeyboardFocus();peerCheck(juce::Component::getCurrentlyFocusedComponent()==order.front(),"detached Audio focus begins at first control at "+std::to_string(width));
    for(std::size_t i=1;i<order.size();++i){const auto before=named(juce::Component::getCurrentlyFocusedComponent());peer->handleKeyPress(juce::KeyPress(juce::KeyPress::tabKey));const auto actual=named(juce::Component::getCurrentlyFocusedComponent());const bool okay=before==ids[i-1]&&actual==ids[i];keys<<width<<'\t'<<before<<"\tTab\t"<<ids[i]<<'\t'<<actual<<'\t'<<(okay?"PASS":"FAIL")<<'\n';peerCheck(okay,"detached Audio Tab follows focus order at "+std::to_string(width));}
    for(std::size_t i=order.size()-1;i>0;--i){const auto before=named(juce::Component::getCurrentlyFocusedComponent());peer->handleKeyPress(juce::KeyPress(juce::KeyPress::tabKey,juce::ModifierKeys::shiftModifier,'\t'));const auto actual=named(juce::Component::getCurrentlyFocusedComponent());const bool okay=before==ids[i]&&actual==ids[i-1];keys<<width<<'\t'<<before<<"\tShift-Tab\t"<<ids[i-1]<<'\t'<<actual<<'\t'<<(okay?"PASS":"FAIL")<<'\n';peerCheck(okay,"detached Audio Shift-Tab follows reverse focus order at "+std::to_string(width));}
    auto* back=dynamic_cast<juce::TextButton*>(view.findChildWithID("audio-back"));peerCheck(back&&back->isShowing()&&back->isEnabled(),"detached Audio Back is safe and enabled at "+std::to_string(width));
    if(back){back->grabKeyboardFocus();peer->handleKeyPress(juce::KeyPress(juce::KeyPress::returnKey));for(int i=0;i<20;++i)pump();peerCheck(returned==1,"focused Return activates Audio Back at "+std::to_string(width));peer->handleKeyPress(juce::KeyPress(juce::KeyPress::spaceKey));peer->handleKeyPress(juce::KeyPress(juce::KeyPress::spaceKey));for(int i=0;i<20;++i)pump();peerCheck(returned==2,"focused held Space activates Audio Back once at "+std::to_string(width));peer->handleKeyUpOrDown(false);peer->handleKeyPress(juce::KeyPress(juce::KeyPress::spaceKey));for(int i=0;i<20;++i)pump();peerCheck(returned==3,"focused Space rearms after release at "+std::to_string(width));}
   }
   peerCheck(nativeOpens==0&&connections==0,"detached Audio peer keys create no output connection at "+std::to_string(width));view.removeFromDesktop();
  }
  keys.flush();out.flush();peerCheck(keys.good()&&out.good(),"detached Audio peer evidence flushed");std::ofstream(dir/"summary.json")<<"{\"checks\":"<<checks<<",\"failures\":"<<failures<<",\"peerInjectedKeys\":true,\"nativeOpens\":"<<nativeOpens<<",\"connections\":"<<connections<<",\"profileWrites\":false}\n";
  std::cout<<(failures?"FAIL ":"PASS ")<<checks<<" Audio peer keyboard checks; failures="<<failures<<'\n';return failures?1:0;
 }
 if(homeSurfaceOnly&&std::string(argv[2])=="--presentation-stop-gates"){
  Harness h(dir,"presentation-stopped-profile");
  const auto before=h.store->snapshot(storage::newUuid()).get();
  ck(before.status==storage::Status::Confirmed&&h.home->attachPresentation(*h.store,before.data.object().at("profile_id").string()),"Presentation attaches only the confirmed exact synthetic profile");
  auto* choice=dynamic_cast<juce::ComboBox*>(h.home->findChildWithID("presentation-global"));
  h.wait([&]{return h.home->presentationStoppedAndResolved();},"initial read-only profile and timing inspections settle");
  ck(choice&&h.home->presentationStoppedAndResolved(),"Initial Home has stopped and resolved activity gates");
  choice->setSelectedId(2,juce::sendNotification);
  A::tick(*h.home);
  ck(choice->getSelectedId()==2,"A timer refresh preserves the queued explicit disclosure selection before notification");
  h.wait([&]{return h.home->presentationModel().globalLevel()==desktop::presentation::Level::Advanced;},"explicit Advanced disclosure choice");
  auto& freeplay=A::freeplay(*h.home);
  ck(h.home->navigate(H::Page::Freeplay)&&freeplay.startFreeplay(),"New isolated Freeplay explicitly starts");
  h.wait([&]{freeplay.servicePersistence();return !freeplay.persistencePending();},"original Freeplay allocation settles");
  ck(freeplay.pauseFreeplay()&&freeplay.canLeave()&&!freeplay.presentationStoppedAndResolved(),"Paused Freeplay retains its owner while safe Back is permitted");
  ck(h.home->navigate(H::Page::Home)&&!h.home->presentationStoppedAndResolved(),"Paused Freeplay owner keeps Home setting save STOP_REQUIRED");
  juce::TextButton* save=nullptr;
  for(auto* child:h.home->getChildren())if(auto* b=dynamic_cast<juce::TextButton*>(child);b&&b->getButtonText()=="Save setting")save=b;
  A::tick(*h.home);ck(save&&!save->isEnabled(),"Save setting is disabled while the original Freeplay remains paused");
  if(save)save->onClick();
  const auto preference=h.store->readPreferences(storage::newUuid(),desktop::presentation::preferenceKey).get();
  ck(preference.status==storage::Status::DefinitelyAbsent,"Even direct activation while paused creates no presentation preference write");
  ck(h.home->presentationModel().globalLevel()==desktop::presentation::Level::Advanced&&!freeplay.active(),"Refused persistence retains in-memory disclosure and paused transport");
  ck(freeplay.stopFreeplay(),"Original paused Freeplay stops explicitly");
  h.wait([&]{freeplay.servicePersistence();return freeplay.persistenceSaved();},"original Freeplay save settles");
  A::tick(*h.home);ck(h.home->presentationStoppedAndResolved()&&save->isEnabled(),"Only explicit stopped resolved owner enables global preference Save");
  save->onClick();
  h.wait([&]{return h.store->readPreferences(storage::newUuid(),desktop::presentation::preferenceKey).get().status==storage::Status::Confirmed;},"explicit presentation Save");
  ck(h.home->presentationModel().globalLevel()==desktop::presentation::Level::Advanced,"Saving presentation preserves selected disclosure");
  {
   Harness q(dir,"presentation-notification-ordering");
   const auto initial=capture_fixture::confirmed(q.store->snapshot(storage::newUuid()));
   ck(q.home->attachPresentation(*q.store,initial.data.object().at("profile_id").string()),"Ordering fixture attaches its exact independent synthetic profile");
   auto* selector=dynamic_cast<juce::ComboBox*>(q.home->findChildWithID("presentation-global"));
   auto button=[&](const char* name){for(auto* child:q.home->getChildren())if(auto* b=dynamic_cast<juce::TextButton*>(child);b&&b->getButtonText()==name)return b;return static_cast<juce::TextButton*>(nullptr);};
   auto* reset=button("Reset presentation");auto* reload=button("Reload / check save");
   ck(selector&&reset&&reload,"Actual ordering fixture exposes selector, explicit Reset and Reload");
   q.wait([&]{return reload->isEnabled()&&q.home->presentationStoppedAndResolved();},"ordering initial inspections settle");
   selector->setSelectedId(2,juce::sendNotification);reset->onClick();q.tick();pump();q.tick();
   ck(selector->getSelectedId()==1&&q.home->presentationModel().globalLevel()==desktop::presentation::Level::Beginner,"Explicit Reset already at Beginner discards an older queued Advanced choice");
   const auto savedBytes=storage::canonical(desktop::presentation::encodePreferences(desktop::presentation::Level::Advanced));
   const auto seed=q.store->compareExchangePreferences(storage::newUuid(),desktop::presentation::preferenceKey,desktop::presentation::namespaceVersion,0,savedBytes,true).get();
   ck(seed.status==storage::Status::Confirmed,"Ordering fixture explicitly seeds a different saved Advanced setting through Store");
   const auto seeded=capture_fixture::confirmed(q.store->snapshot(storage::newUuid()));
   auto originalActivity=initial.data.object().at("authoritative").object();auto seededActivity=seeded.data.object().at("authoritative").object();
   ck(originalActivity.erase("preferences")==1&&seededActivity.erase("preferences")==1&&originalActivity==seededActivity,"Explicit seed changes only its preference authority; all twelve activity authorities remain identical");
   q.mode=4;q.entered=false;q.release=false;reload->onClick();
   q.wait([&]{return q.entered.load();},"hold actual pending preference read");
   selector->setSelectedId(3,juce::sendNotification);q.tick();
   ck(q.home->presentationModel().globalLevel()==desktop::presentation::Level::Developer&&selector->getSelectedId()==3,"Timer consumes newer explicit Developer before polling the held saved Advanced read");
   q.release=true;q.wait([&]{return reload->isEnabled();},"release actual saved preference read");pump();q.tick();
   ck(q.home->presentationModel().globalLevel()==desktop::presentation::Level::Developer&&selector->getSelectedId()==3,"Different saved read and delayed notification retain the newer explicit Developer choice");
   selector->setSelectedId(1,juce::sendNotification);reload->onClick();q.tick();pump();
   q.wait([&]{return reload->isEnabled();},"explicit Reload supersedes older queued choice");
   ck(q.home->presentationModel().globalLevel()==desktop::presentation::Level::Advanced&&selector->getSelectedId()==2,"Explicit Reload discards older queued Beginner and loads exact saved Advanced");
   q.mode=4;q.entered=false;q.release=false;reload->onClick();
   q.wait([&]{return q.entered.load();},"hold second actual preference reload");
   selector->setSelectedId(1,juce::sendNotification);q.tick();q.release=true;
   q.wait([&]{return reload->isEnabled();},"newer choice during Reload settles");pump();q.tick();
   ck(q.home->presentationModel().globalLevel()==desktop::presentation::Level::Beginner&&selector->getSelectedId()==1,"A newer explicit Beginner during Reload wins without an implicit save");
   const auto stored=q.store->readPreferences(storage::newUuid(),desktop::presentation::preferenceKey).get();
   ck(stored.status==storage::Status::Confirmed&&stored.data.object().at("bytes").string()==savedBytes,"Choice ordering leaves the exact persisted Advanced proposal unchanged");
   const auto after=capture_fixture::confirmed(q.store->snapshot(storage::newUuid()));
   ck(*seeded.data.find("authoritative")==*after.data.find("authoritative")&&nativeOpens==0&&connections==0,"Ordering controls leave all thirteen seeded authority tables and closed physical/software output unchanged");
  }
  out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home presentation stop-gate checks; synthetic only; no device opens\n";return 0;
 }
 if(homeSurfaceOnly){
  H home;home.setSize(920,680);home.setVisible(true);
  auto* guidance=dynamic_cast<juce::Label*>(home.findChildWithID("home-guidance"));
  auto* inventory=dynamic_cast<juce::Label*>(home.findChildWithID("home-preview-inventory"));
  auto* detail=dynamic_cast<juce::Label*>(home.findChildWithID("home-preview-inventory"));
  auto* freeplay=dynamic_cast<juce::TextButton*>(home.findChildWithID("home-freeplay"));
  auto* guided=dynamic_cast<juce::TextButton*>(home.findChildWithID("home-guided"));
  auto* audio=dynamic_cast<juce::TextButton*>(home.findChildWithID("home-audio-output"));
  auto* learn=dynamic_cast<juce::TextButton*>(home.findChildWithID("home-learn"));
  auto* startLearning=dynamic_cast<juce::TextButton*>(home.findChildWithID("home-start-learning"));
  auto* progress=dynamic_cast<juce::TextButton*>(home.findChildWithID("home-progress"));
  auto* practice=dynamic_cast<juce::TextButton*>(home.findChildWithID("home-practice"));
  ck(guidance&&guidance->getTitle().toStdString()=="Read-only Home navigation guidance and product boundary.","Home guidance exposes a stable truthful navigation title");
  bool previewIdentity=false;for(auto* child:home.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))previewIdentity=previewIdentity||label->getText().toStdString()=="OFFLINE MACOS DEVELOPMENT PREVIEW";
  ck(previewIdentity,"Home identifies the delivered candidate as an offline macOS Development Preview");
  const auto guidanceText=guidance?guidance->getText().toStdString():std::string{};
  ck(guidance&&guidance->isVisible()&&guidanceText.find("Choose a level and exercise in Learn, then open it in Practice.")!=std::string::npos&&guidanceText.find("Progress shows saved activity, not exercise completion.")!=std::string::npos&&guidanceText.find("Freeplay is independent practice.")!=std::string::npos,"Home guidance preserves the exact Learn-first, no-credit and shared-Audio boundary");
  ck(inventory&&inventory->getTitle().toStdString()=="Read-only Development Preview inventory and shared Audio scope.","Home inventory exposes a stable truthful preview title");
  const auto inventoryText=inventory?inventory->getText().toStdString():std::string{};
  auto* disclosure=dynamic_cast<juce::TextButton*>(home.findChildWithID("home-preview-details"));
  ck(inventory&&!inventory->isVisible()&&inventoryText.find("all 105 original workbooks")!=std::string::npos&&inventoryText.find("105 read-only text/PDF pairs")!=std::string::npos&&inventoryText.find("Curriculum review Pending")!=std::string::npos&&inventoryText.find("Audio settings are shared across activities")!=std::string::npos,"Home keeps complete current preview/source/no-credit scope retained behind explicit disclosure");
  ck(disclosure&&disclosure->isVisible()&&disclosure->isEnabled(),"Home offers explicit Preview details");
  disclosure->onClick();
  ck(inventory->isVisible()&&!startLearning->isVisible()&&inventory->getNumChildComponents()==1&&dynamic_cast<juce::TextEditor*>(inventory->getChildComponent(0))!=nullptr,"Home details opens complete scrollable prose without overlaying navigation");
  disclosure->onClick();

  auto* about=dynamic_cast<juce::TextButton*>(home.findChildWithID("home-about-preview"));
  ck(detail&&detail->getHeight()>=64&&home.getLocalBounds().contains(detail->getBounds())&&startLearning&&about&&detail->getText().toStdString().find("\n")!=std::string::npos&&detail->getText().toStdString().find("Visible MVP paths: Home → Learn → admitted Practice → Save result → Progress; Home → Guided → Learn → admitted Practice → Save result → Guided summary → Progress.")!=std::string::npos,"Home retains full qualified MVP paths in its explicitly opened scrollable Details region");
  for(const auto size:{std::pair{921,680},std::pair{1400,680},std::pair{1400,928}}){
   home.setSize(size.first,size.second);
   bool contained=true,disjoint=true;
   for(auto* a:home.getChildren())if(a->isVisible()&&a->getWidth()>0&&a->getHeight()>0){
    contained=contained&&home.getLocalBounds().contains(a->getBounds());
    for(auto* b:home.getChildren())if(a!=b&&b->isVisible()&&b->getWidth()>0&&b->getHeight()>0)disjoint=disjoint&&!a->getBounds().intersects(b->getBounds());
   }
   ck(contained&&disjoint,"Home visible primary prose, navigation, presentation setting and footer bounds are contained and disjoint at "+std::to_string(size.first)+"x"+std::to_string(size.second));
  }

  ck(learn&&learn->getButtonText().toStdString()=="Learn"&&learn->getTitle().toStdString()=="Choose a level and exercise. Practice starts only when you choose Start in Practice."&&learn->isEnabled()&&learn->getExplicitFocusOrder()==9,"Home Learn keeps its visible label and exposes the source-backed/explicit-Practice/no-credit boundary");
  ck(startLearning&&!startLearning->isVisible()&&!startLearning->isEnabled()&&!startLearning->getWantsKeyboardFocus(),"duplicate Start learning is absent from visible and keyboard Home navigation");
  ck(progress&&progress->getButtonText().toStdString()=="Progress"&&progress->getTitle().toStdString()=="Open read-only Progress for saved local activity; no curriculum credit is inferred."&&progress->isEnabled()&&progress->getExplicitFocusOrder()==11,"Home Progress keeps its visible label and exposes the read-only local-activity/no-credit boundary");
  ck(practice&&practice->getButtonText()=="Exercise details"&&!practice->isEnabled()&&practice->getExplicitFocusOrder()==7,"stable secondary Exercise details waits for a prepared catalog; it does not alias Learn before readiness");
  ck(freeplay&&freeplay->getButtonText().toStdString()=="Freeplay"&&freeplay->getTitle().toStdString()=="Open separate Freeplay; active time and history stay outside curriculum progress."&&freeplay->isEnabled()&&freeplay->getExplicitFocusOrder()==12,"Home Freeplay keeps its visible label and exposes the separate non-curriculum boundary");
  ck(guided&&guided->getButtonText().toStdString()=="Guided sessions"&&guided->getTitle().toStdString()=="Open Guided sessions with a local timed plan; linked Practice stays explicit and no curriculum credit is inferred."&&guided->isEnabled()&&guided->getExplicitFocusOrder()==13,"Home Guided keeps its visible label and exposes the local timed-plan/no-credit boundary");
  ck(audio&&audio->getButtonText().toStdString()=="Audio settings"&&audio->getTitle().toStdString()=="Open shared Audio settings for local activities; opening settings does not start audio or practice activity."&&audio->isEnabled()&&audio->getExplicitFocusOrder()==4,"Home Audio keeps its visible label and exposes the shared-settings/no-activity boundary");
  ck(guidance&&inventory&&home.getLocalBounds().contains(guidance->getBounds())&&home.getLocalBounds().contains(inventory->getBounds())&&home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed,"Home surface remains contained, initial and closed without profile access");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home guidance surface checks\n";return 0;
 }
 if(homeProfileBoundary){
  H home;home.setSize(920,680);home.setVisible(true);
  auto* guidance=dynamic_cast<juce::Label*>(home.findChildWithID("home-guidance"));
  const auto before=guidance?guidance->getText().toStdString():std::string{};
  ck(home.page()==H::Page::Home&&guidance&&before.find("Browse without a profile.")!=std::string::npos&&before.find("Create / open local profile to use Practice or Guided sessions.")!=std::string::npos&&button(home,"Create / open local profile").isEnabled(),"Home without a profile exposes the read-only boundary and actual explicit local-profile action");
 ck(home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"profile-free Home remains closed without native output or activity");
  std::filesystem::permissions(dir,std::filesystem::perms::owner_all);
  storage::StoreOptions options;options.path=dir/"profile.sqlite";options.create=true;options.createdUtc="2026-09-08T16:00:00Z";options.preferenceValidator=desktop::presentation::composedPreferenceValidator;
  storage::ProfileStore store(options);const auto session=capture_fixture::confirmed(store.createSession(storage::newUuid(),options.createdUtc,"America/New_York",{},json::Value::Object{{"synthetic_fixture",true}}));
  ck(home.configureCapture(store,session.owner,"America/New_York"),"Home binds one disposable local preview profile through the existing Store path");
  ck(home.navigate(H::Page::Home),"Home refreshes its visible profile boundary after attachment");
  guidance=dynamic_cast<juce::Label*>(home.findChildWithID("home-guidance"));const auto after=guidance?guidance->getText().toStdString():std::string{};
  ck(after.find("Local profile ready.")!=std::string::npos&&after.find("Practice and Guided Start stay explicit; save your result before leaving an active exercise.")!=std::string::npos&&after.find("Browse without a profile.")==std::string::npos,"attached Home replaces the no-profile wording with the explicit local-profile boundary");
  ck(home.page()==H::Page::Home&&A::practice(home).captureSession()!=nullptr&&!A::practice(home).captureSession()->startTaken()&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"attached profile remains at Home with no Attempt start, native output or audio connection");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home profile boundary checks\n";return 0;
 }
 if(homeAboutSurface){
  H home;home.setSize(920,680);home.setVisible(true);
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed,"fresh About fixture starts at Home with closed output");
  bool homeHeading=false;for(auto* child:home.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText()=="Fathom")homeHeading=true;ck(homeHeading,"Home retains the Fathom heading before About opens");
  click(home,"About this preview");
  auto* guidance=dynamic_cast<juce::Label*>(home.findChildWithID("home-guidance"));const auto text=guidance?guidance->getText().toStdString():std::string{};
  ck(home.page()==H::Page::About&&A::visiblePages(home)==0,"About opens as the visible Home root with child destinations hidden");
  bool aboutHeading=false;for(auto* child:home.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText()=="About Fathom")aboutHeading=true;ck(aboutHeading,"About exposes an explicit About Fathom heading");
  ck(guidance&&text.find("A quiet place to build your guitar practice.")!=std::string::npos&&text.find("Choose a level and exercise in Learn.")!=std::string::npos&&text.find("Progress shows saved local activity.")!=std::string::npos&&text.find("Opening pages does not start Practice or create completion credit.")!=std::string::npos&&text.find("offline macOS Development Preview")!=std::string::npos&&text.find("PDF")==std::string::npos,"About explains learner destinations and preview scope without authoring jargon");
  ck(text.find("Curriculum acceptance")==std::string::npos&&text.find("runtime eligible")==std::string::npos&&text.find("released course")==std::string::npos,"About does not claim curriculum acceptance, runtime eligibility or release");
  ck(home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"About inspection creates no audio connection or native output");
  click(home,"Back");
  homeHeading=false;for(auto* child:home.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText()=="Fathom")homeHeading=true;ck(home.page()==H::Page::Home&&homeHeading&&A::visiblePages(home)==0&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"About Back returns Home safely with the Fathom heading and closed output");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home About surface checks\n";return 0;
 }
 if(homeGuitarSetupSurface){
  H home;home.setSize(920,680);home.setVisible(true);
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed,"fresh Guitar setup fixture starts at Home with closed output");
  ck(home.navigate(H::Page::Setup),"Home opens Guitar setup without starting activity");
  desktop::GuitarSetupView* setup=nullptr;for(auto* child:home.getChildren())if(auto* candidate=dynamic_cast<desktop::GuitarSetupView*>(child))setup=candidate;
  std::string labels;std::vector<std::string> buttons;std::vector<std::string> combos;int editors=0;int capoEditors=0;int fretEditors=0;
  if(setup){for(auto* child:setup->getChildren()){if(auto* label=dynamic_cast<juce::Label*>(child))labels+=label->getText().toStdString()+"\n";if(auto* button=dynamic_cast<juce::Button*>(child))buttons.push_back(button->getButtonText().toStdString());if(auto* combo=dynamic_cast<juce::ComboBox*>(child)){combos.push_back(combo->getTitle().toStdString());for(int i=1;i<=combo->getNumItems();++i)combos.push_back(combo->getItemText(i).toStdString());}if(auto* editor=dynamic_cast<juce::TextEditor*>(child)){++editors;const auto title=editor->getTitle().toStdString();if(title=="Capo physical fret")++capoEditors;if(title=="Physical fret count")++fretEditors;}}}
  ck(home.page()==H::Page::Setup&&setup&&setup->isVisible(),"Guitar setup is the visible Home destination");
  ck(labels.find("Guitar setup")!=std::string::npos&&labels.find("Describe your guitar. This does not detect its physical tuning. Applying setup changes local configuration only; authored lesson tuning remains unchanged.")!=std::string::npos&&labels.find("Open tuning - low to high")!=std::string::npos&&labels.find("Capo (physical fret)")!=std::string::npos&&labels.find("Physical fret count")!=std::string::npos&&labels.find("Fretboard orientation")!=std::string::npos,"Guitar setup exposes truthful local configuration and physical-tuning boundaries");
  bool tuningChoices=false;for(const auto& item:{std::string("Standard"),std::string("E-flat Standard"),std::string("Drop D"),std::string("Custom")})tuningChoices=tuningChoices||std::find(combos.begin(),combos.end(),item)!=combos.end();ck(tuningChoices&&std::find(combos.begin(),combos.end(),"Fretboard orientation")!=combos.end(),"Guitar setup exposes tuning presets and handedness selection");
  ck(editors==8&&capoEditors==1&&fretEditors==1&&std::find(buttons.begin(),buttons.end(),"Apply setup")!=buttons.end()&&std::find(buttons.begin(),buttons.end(),"Back")!=buttons.end(),"Guitar setup exposes six string notes, capo, fret count, Apply setup and Back");
  ck(labels.find("Right-handed: capo/open at left; frets increase right.")!=std::string::npos&&labels.find("String1 is high/top; string6 low/bottom. Preview: relative frets 0-12. Sharp note names; -- means unavailable.")!=std::string::npos&&labels.find("Changes are kept for this app session. Lesson notes keep their authored tuning.")!=std::string::npos,"Guitar setup exposes the default orientation summary, fret preview and authored-tuning footer");
  ck(home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"Guitar setup inspection creates no audio connection or native output");
  click(*setup,"Back");
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"Guitar setup Back returns Home safely with closed output");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home Guitar setup surface checks\n";return 0;
 }
 if(homeGuitarSetupApply){
  H home;home.setSize(920,680);home.setVisible(true);
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed,"fresh Guitar setup Apply fixture starts at Home with closed output");
  ck(home.navigate(H::Page::Setup),"Home opens Guitar setup for Apply");
  desktop::GuitarSetupView* setup=nullptr;for(auto* child:home.getChildren())if(auto* candidate=dynamic_cast<desktop::GuitarSetupView*>(child))setup=candidate;
  juce::ComboBox* preset=nullptr;std::vector<juce::TextEditor*> editors;
  if(setup)for(auto* child:setup->getChildren()){if(auto* combo=dynamic_cast<juce::ComboBox*>(child);combo&&combo->getTitle().toStdString()=="Tuning preset")preset=combo;if(auto* editor=dynamic_cast<juce::TextEditor*>(child))editors.push_back(editor);}
  ck(setup&&setup->isVisible()&&preset&&preset->getSelectedId()==1,"Guitar setup Apply finds the visible Tuning preset at Standard");
  preset->setSelectedId(3,juce::sendNotificationSync);
  std::string notes;for(auto* editor:editors)if(editor->getTitle().toStdString().find("open note")!=std::string::npos)notes+=editor->getText().toStdString()+" ";
  ck(preset->getSelectedId()==3&&notes.find("D2")!=std::string::npos&&notes.find("A2")!=std::string::npos&&notes.find("D3")!=std::string::npos&&notes.find("G3")!=std::string::npos&&notes.find("B3")!=std::string::npos&&notes.find("E4")!=std::string::npos,"Drop D selects the existing source-derived D2 A2 D3 G3 B3 E4 draft");
  click(*setup,"Apply setup");
  std::string labels;for(auto* child:setup->getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))labels+=label->getText().toStdString()+"\n";
  ck(labels.find("Setup applied. Open fret0 is at the capo; numbered frets are relative to it.")!=std::string::npos,"Apply reports the exact existing session-only setup status");
  ck(labels.find("Right-handed: capo/open at left; frets increase right.")!=std::string::npos&&labels.find("Changes are kept for this app session. Lesson notes keep their authored tuning.")!=std::string::npos,"Apply preserves orientation and authored lesson tuning boundaries");
  ck(home.page()==H::Page::Setup&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"applied setup remains on the setup surface without audio or native output");
  click(*setup,"Back");
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"applied Guitar setup Back returns Home safely");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home Guitar setup Apply checks\n";return 0;
 }
 if(homeGuitarSetupInvalidRecovery){
  H home;home.setSize(920,680);home.setVisible(true);
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed,"fresh Guitar setup recovery fixture starts at Home with closed output");
  ck(home.navigate(H::Page::Setup),"Home opens Guitar setup for recovery");
  desktop::GuitarSetupView* setup=nullptr;for(auto* child:home.getChildren())if(auto* candidate=dynamic_cast<desktop::GuitarSetupView*>(child))setup=candidate;
  juce::TextEditor* capo=nullptr;juce::TextButton* apply=nullptr;
  if(setup)for(auto* child:setup->getChildren()){if(auto* editor=dynamic_cast<juce::TextEditor*>(child);editor&&editor->getTitle().toStdString()=="Capo physical fret")capo=editor;if(auto* button=dynamic_cast<juce::TextButton*>(child);button&&button->getButtonText().toStdString()=="Apply setup")apply=button;}
  ck(setup&&setup->isVisible()&&capo&&apply,"Guitar setup recovery finds the existing capo editor and Apply control");
  capo->setText("23");activate(*apply);
  std::string refused;for(auto* child:setup->getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))refused+=label->getText().toStdString()+"\n";
  ck(refused.find("Place the full capo between0 and the configured last physical fret.")!=std::string::npos&&refused.find("Current setup unchanged.")!=std::string::npos,"invalid capo Apply refuses with exact recoverable validation guidance");
  ck(home.page()==H::Page::Setup&&refused.find("Right-handed: capo/open at left; frets increase right.")!=std::string::npos&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"invalid Apply keeps Setup usable with summary and no audio or native output");
  capo->setText("0");activate(*apply);
  std::string corrected;for(auto* child:setup->getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))corrected+=label->getText().toStdString()+"\n";
  ck(corrected.find("Setup applied. Open fret0 is at the capo; numbered frets are relative to it.")!=std::string::npos&&corrected.find("Changes are kept for this app session. Lesson notes keep their authored tuning.")!=std::string::npos,"corrected capo Apply succeeds and retains the session-only authored-tuning boundary");
  click(*setup,"Back");
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"recovered Guitar setup Back returns Home safely");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home Guitar setup invalid recovery checks\n";return 0;
 }
 if(homeGuitarSetupOrientationApply){
  H home;home.setSize(920,680);home.setVisible(true);
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed,"fresh Guitar setup orientation fixture starts at Home with closed output");
  ck(home.navigate(H::Page::Setup),"Home opens Guitar setup for orientation Apply");
  desktop::GuitarSetupView* setup=nullptr;for(auto* child:home.getChildren())if(auto* candidate=dynamic_cast<desktop::GuitarSetupView*>(child))setup=candidate;
  juce::ComboBox* preset=nullptr;juce::ComboBox* hand=nullptr;std::vector<juce::TextEditor*> editors;
  if(setup)for(auto* child:setup->getChildren()){if(auto* combo=dynamic_cast<juce::ComboBox*>(child)){if(combo->getTitle().toStdString()=="Tuning preset")preset=combo;if(combo->getTitle().toStdString()=="Fretboard orientation")hand=combo;}if(auto* editor=dynamic_cast<juce::TextEditor*>(child))editors.push_back(editor);}
  ck(setup&&setup->isVisible()&&preset&&hand&&preset->getSelectedId()==1&&hand->getSelectedId()==1,"Guitar setup orientation finds Standard and Right-handed controls");
  preset->setSelectedId(2,juce::sendNotificationSync);hand->setSelectedId(2,juce::sendNotificationSync);
  std::string notes;for(auto* editor:editors)if(editor->getTitle().toStdString().find("open note")!=std::string::npos)notes+=editor->getText().toStdString()+" ";
  ck(preset->getSelectedId()==2&&hand->getSelectedId()==2&&notes.find("D#2")!=std::string::npos&&notes.find("G#2")!=std::string::npos&&notes.find("C#3")!=std::string::npos&&notes.find("F#3")!=std::string::npos&&notes.find("A#3")!=std::string::npos&&notes.find("D#4")!=std::string::npos,"E-flat Standard exposes the source-derived D#2 G#2 C#3 F#3 A#3 D#4 draft");
  click(*setup,"Apply setup");
  std::string labels;for(auto* child:setup->getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))labels+=label->getText().toStdString()+"\n";
  ck(labels.find("Setup applied. Open fret0 is at the capo; numbered frets are relative to it.")!=std::string::npos&&labels.find("Left-handed: capo/open at right; frets increase left.")!=std::string::npos,"E-flat left-handed Apply reports exact status and orientation summary");
  ck(labels.find("String1 is high/top; string6 low/bottom. Preview: relative frets 0-12. Sharp note names; -- means unavailable.")!=std::string::npos&&labels.find("Changes are kept for this app session. Lesson notes keep their authored tuning.")!=std::string::npos&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"left-handed preview and authored-tuning boundary remain visible without audio or native output");
  click(*setup,"Back");
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"orientation Apply Back returns Home safely");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home Guitar setup orientation Apply checks\n";return 0;
 }
 if(homeGuitarSetupCustomApply){
  H home;home.setSize(920,680);home.setVisible(true);
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed,"fresh Guitar setup Custom fixture starts at Home with closed output");
  ck(home.navigate(H::Page::Setup),"Home opens Guitar setup for Custom Apply");
  desktop::GuitarSetupView* setup=nullptr;for(auto* child:home.getChildren())if(auto* candidate=dynamic_cast<desktop::GuitarSetupView*>(child))setup=candidate;
  juce::ComboBox* preset=nullptr;juce::TextEditor* string6=nullptr;juce::TextButton* apply=nullptr;
  if(setup)for(auto* child:setup->getChildren()){if(auto* combo=dynamic_cast<juce::ComboBox*>(child);combo&&combo->getTitle().toStdString()=="Tuning preset")preset=combo;if(auto* editor=dynamic_cast<juce::TextEditor*>(child)){if(editor->getTitle().toStdString()=="String 6 open note")string6=editor;}if(auto* button=dynamic_cast<juce::TextButton*>(child);button&&button->getButtonText().toStdString()=="Apply setup")apply=button;}
  ck(setup&&setup->isVisible()&&preset&&string6&&apply&&preset->getSelectedId()==1,"Guitar setup Custom finds the String 6 editor, preset and Apply controls");
  string6->setText("F2",true);if(string6->onTextChange)string6->onTextChange();pump();
  ck(preset->getSelectedId()==4&&string6->getText().toStdString()=="F2","editing String 6 changes the visible preset to Custom and retains F2");
  activate(*apply);
  std::string labels;for(auto* child:setup->getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))labels+=label->getText().toStdString()+"\n";
  ck(labels.find("Setup applied. Open fret0 is at the capo; frets are relative to it.")==std::string::npos&&labels.find("Setup applied. Open fret0 is at the capo; numbered frets are relative to it.")!=std::string::npos,"Custom Apply reports the exact existing success status");
  ck(labels.find("Right-handed: capo/open at left; frets increase right.")!=std::string::npos&&labels.find("Changes are kept for this app session. Lesson notes keep their authored tuning.")!=std::string::npos&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"Custom Apply preserves orientation and authored-tuning boundaries without audio or native output");
  click(*setup,"Back");
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"Custom Apply Back returns Home safely");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home Guitar setup Custom Apply checks\n";return 0;
 }
 if(homeProgressEmpty){
  H home;home.setSize(920,680);home.setVisible(true);
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed,"fresh Home Progress fixture starts at Home with closed output");
  ck(home.navigate(H::Page::Progress),"Home opens read-only Progress without a profile");
  auto* progress=dynamic_cast<desktop::ProgressView*>(home.findChildWithID("progress"));juce::Label* title=nullptr;if(progress)for(auto* child:progress->getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText().toStdString()=="PROGRESS — SAVED LOCAL ACTIVITY")title=label;auto* status=progress?dynamic_cast<juce::Label*>(progress->findChildWithID("progress-status")):nullptr;auto* body=progress?dynamic_cast<juce::TextEditor*>(progress->findChildWithID("progress-body")):nullptr;auto* back=progress?dynamic_cast<juce::TextButton*>(progress->findChildWithID("progress-back")):nullptr;auto* refresh=progress?dynamic_cast<juce::TextButton*>(progress->findChildWithID("progress-refresh")):nullptr;auto* reopen=progress?dynamic_cast<juce::TextButton*>(progress->findChildWithID("progress-reopen")):nullptr;auto* learn=progress?dynamic_cast<juce::TextButton*>(progress->findChildWithID("progress-learn")):nullptr;auto* audio=progress?dynamic_cast<juce::TextButton*>(progress->findChildWithID("progress-audio-settings")):nullptr;auto* details=progress?dynamic_cast<juce::TextButton*>(progress->findChildWithID("progress-details")):nullptr;
  ck(home.page()==H::Page::Progress&&title&&title->getText().toStdString()=="PROGRESS — SAVED LOCAL ACTIVITY"&&status&&body,"Progress exposes its visible title, status and body");
  const auto statusText=status->getText().toStdString();const auto bodyText=body->getText().toStdString();
  ck(statusText.find("Opening Progress never creates activity.")!=std::string::npos&&statusText.find("Attach a local profile to view saved practice.")!=std::string::npos&&statusText.find("Progress is read-only and does not award curriculum credit.")!=std::string::npos&&statusText.find("--capture-preview <new private directory>")!=std::string::npos,"empty Progress status names the profile, read-only, no-credit and disposable-preview boundaries");
  ck(bodyText.find("No Progress snapshot is loaded yet.")!=std::string::npos&&bodyText.find("Choose Refresh to read finalized local activity.")!=std::string::npos&&bodyText.find("admitted source-backed case in Learn")!=std::string::npos&&bodyText.find("does not create activity or curriculum credit")!=std::string::npos&&bodyText.find("Synthetic") == std::string::npos,"empty Progress body gives a truthful next action without fabricated activity");
  ck(refresh&&!refresh->isEnabled()&&reopen&&!reopen->isEnabled()&&details&&!details->isEnabled()&&learn&&learn->isEnabled()&&audio&&audio->isEnabled()&&back&&back->isEnabled(),"profile-free Progress controls expose only safe read-only actions");
  ck(home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"empty Progress creates no profile, audio connection or native output");
  click(*progress,"Back");
  ck(home.page()==H::Page::Home&&home.audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"Progress Back returns Home safely");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home Progress empty checks\n";return 0;
 }
 if(homeProgressAttachedEmpty){
  Harness h(dir,"progress-attached-empty");
  ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&h.finals()==0,"attached Progress fixture starts Home with closed output and no finalized activity");
  ck(h.home->navigate(H::Page::Progress),"attached profile opens Progress");
  auto& progress=A::progress(*h.home);h.wait([&]{return !progress.busy();},"attached Progress empty read settles");
  const auto statusText=progress.statusText();const auto bodyText=progress.presentation().text;const auto projection=progress.presentation().projection;
  ck(!progress.busy()&&!projection.null(),"attached Progress produces a confirmed snapshot presentation");
  ck(statusText.find("Saved snapshot as of")!=std::string::npos&&statusText.find("contains no finalized practice activity in this snapshot")!=std::string::npos&&statusText.find("read-only")!=std::string::npos&&statusText.find("does not award curriculum credit")!=std::string::npos,"attached empty Progress status identifies no finalized activity and no-credit read-only state");
  ck(bodyText.find("No finalized practice activity in this snapshot.")!=std::string::npos&&bodyText.find("curriculum credit")!=std::string::npos&&bodyText.find("mastery") == std::string::npos&&bodyText.find("completed") == std::string::npos,"attached empty Progress body contains truthful empty snapshot facts without fabricated completion");
  ck(h.finals()==0&&!h.practice().captureSession()->startTaken()&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"attached Progress refresh creates no Attempt, finalization, audio connection or native output");
  click(progress,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"attached Progress Back returns Home");
  ck(h.home->page()==H::Page::Home&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"attached Progress Back returns safely without activity or output mutation");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home Progress attached empty checks\n";return 0;
 }
 if(homeProgressLearnHandoff){
  Harness h(dir,"progress-learn-handoff");
  ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&h.finals()==0,"Progress Learn handoff starts Home with closed output and no finalized activity");
  ck(h.home->navigate(H::Page::Progress),"attached Progress opens for Learn handoff");
  auto& progress=A::progress(*h.home);h.wait([&]{return !progress.busy();},"Progress Learn handoff read settles");
  ck(!progress.busy()&&!progress.presentation().projection.null(),"attached Progress is settled before Learn handoff");
  click(progress,"Choose practice in Learn");h.wait([&]{return h.home->page()==H::Page::Learn;},"Progress Choose practice in Learn handoff");
  auto& learn=A::lessons(*h.home);ck(h.home->page()==H::Page::Learn&&learn.catalog()&&learn.catalog()->lessons().size()==13,"Progress handoff loads the retained 13-case Learn catalog");
  ck(h.finals()==0&&!h.practice().captureSession()->startTaken()&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"Progress handoff creates no Attempt, finalization, audio connection or native output");
  click(learn,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Learn Back returns Home after Progress handoff");
  ck(h.home->page()==H::Page::Home&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"Progress Learn handoff returns Home safely");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Home Progress Learn handoff checks\n";return 0;
 }
 if(homeProgressLearnPracticeHandoff){
  Harness h(dir,"progress-learn-practice-handoff");
  ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&h.finals()==0,"Progress Learn Practice handoff starts Home with closed output and no finalized activity");
  ck(h.home->navigate(H::Page::Progress),"attached Progress opens for Learn Practice handoff");
  auto& progress=A::progress(*h.home);h.wait([&]{return !progress.busy();},"Progress Learn Practice handoff read settles");
  ck(!progress.busy()&&!progress.presentation().projection.null(),"attached Progress is settled before Learn Practice handoff");
  click(progress,"Choose practice in Learn");h.wait([&]{return h.home->page()==H::Page::Learn;},"Progress Choose practice enters Learn for Practice handoff");
  auto& learn=A::lessons(*h.home);ck(h.home->page()==H::Page::Learn&&learn.catalog()&&learn.catalog()->lessons().size()==13,"Progress-origin Learn exposes the retained 13-case catalog");
  ck(learn.selectLesson("fg:item:000002")&&learn.selectVariant("fg:variant:000006"),"Progress-origin Learn selects the retained admitted source case");
  auto* practiceAction=dynamic_cast<juce::TextButton*>(learn.findChildWithID("practice-selection"));
  ck(practiceAction&&practiceAction->isEnabled()&&practiceAction->getTitle().toStdString().find("fg:item:000002 / fg:variant:000006")!=std::string::npos,"Progress-origin admitted Practice action is enabled with exact source identity");
  click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"Progress-origin admitted case enters Practice");
  ck(h.practice().lessonAdmission()!=nullptr&&h.practice().lessonAdmission()->identity().object().at("item_id").string()=="fg:item:000002"&&h.practice().lessonAdmission()->identity().object().at("variant_id").string()=="fg:variant:000006"&&h.practice().captureSession()!=nullptr&&h.practice().captureSession()->phase()==capture::SessionPhase::Idle&&!h.practice().captureSession()->startTaken()&&h.finals()==0,"Progress-origin Practice preserves admitted identity with explicit Start and no activity");
  ck(h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"Progress-origin Practice remains closed with no native audio activity");
  click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"Progress-origin Practice Back returns Learn");
  ck(learn.selectedLesson()=="fg:item:000002"&&learn.selectedVariant()=="fg:variant:000006"&&h.finals()==0,"Progress-origin Practice Back preserves the exact selected source identity without activity");
  click(learn,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Progress-origin Learn Back returns Home");
  ck(h.home->page()==H::Page::Home&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"Progress-origin handoff returns Home safely without activity or output mutation");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Progress Learn Practice handoff checks\n";return 0;
 }
 if(homeProgressLearnPracticeProvenance){
  Harness h(dir,"progress-learn-practice-provenance");
  ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&h.finals()==0,"Progress-origin provenance starts Home with closed output and no finalized activity");
  ck(h.home->navigate(H::Page::Progress),"attached Progress opens for provenance handoff");
  auto& progress=A::progress(*h.home);h.wait([&]{return !progress.busy();},"Progress provenance read settles");click(progress,"Choose practice in Learn");h.wait([&]{return h.home->page()==H::Page::Learn;},"Progress provenance enters Learn");
  auto& learn=A::lessons(*h.home);ck(learn.catalog()&&learn.catalog()->lessons().size()==13&&learn.selectLesson("fg:item:000002")&&learn.selectVariant("fg:variant:000006"),"Progress-origin provenance selects the retained admitted case");
  const auto& selected=learn.catalog()->variant("fg:item:000002","fg:variant:000006");click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"Progress-origin provenance enters Practice");
  auto* authored=dynamic_cast<juce::Label*>(h.practice().findChildWithID("practice-authored-source"));auto* statusLabel=dynamic_cast<juce::Label*>(h.practice().findChildWithID("practice-status"));const auto authoredText=authored?authored->getText().toStdString():std::string{};const auto statusText=statusLabel?statusLabel->getText().toStdString():std::string{};const auto revision=storage::canonical(h.practice().lessonAdmission()->identity().object().at("content_revision"));
  ck(authored&&statusLabel&&authoredText.rfind("AUTHORED SOURCE INSTRUCTIONS\n",0)==0&&authoredText.find(h.practice().lessonAdmission()->description())!=std::string::npos&&authoredText.find("SOURCE PROVENANCE")!=std::string::npos,"Progress-origin Practice preserves the authored instruction marker and exact description");
  ck(authoredText.find("Lesson title: ModeA Exercise001 full selected directions")!=std::string::npos&&authoredText.find("Variant label: sixteenths-ascending-D-even")!=std::string::npos&&authoredText.find("Workbook identity: fg:workbook:000003 | Level: 3")!=std::string::npos&&authoredText.find("Source case: fg:item:000002 / fg:variant:000006")!=std::string::npos&&authoredText.find("Source references: L3-TXT5-21, L3-TXT28-46")!=std::string::npos,"Progress-origin Practice preserves exact authored lesson, variant, workbook, source case and source references");
  ck(authoredText.find("Content version: representative-controls.1")!=std::string::npos&&authoredText.find("Content revision: "+revision)!=std::string::npos,"Progress-origin Practice preserves the admitted content version and revision");
  ck(statusText.find("Output closed")!=std::string::npos&&statusText.find("Selected source: fg:item:000002 / fg:variant:000006")!=std::string::npos&&statusText.find("Next action: choose Start selected case.")!=std::string::npos&&statusText.find("Explicit Start begins one local Practice Attempt; Save result is required before a local record is finalized.")!=std::string::npos,"Progress-origin Practice status preserves exact source identity and explicit Start/Save boundary");
  ck(h.practice().tabView().document()&&&h.practice().tabView().document()->source()==&selected.model->source(),"Progress-origin Practice TAB uses the same admitted source model");
  ck(h.practice().lessonAdmission()&&h.practice().captureSession()!=nullptr&&h.practice().captureSession()->phase()==capture::SessionPhase::Idle&&!h.practice().captureSession()->startTaken()&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"Progress-origin provenance remains stopped with no Attempt, finalization, credit or output");
  click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"Provenance Practice Back returns Learn");ck(learn.selectedLesson()=="fg:item:000002"&&learn.selectedVariant()=="fg:variant:000006"&&h.finals()==0,"Practice Back preserves provenance selection without activity");click(learn,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Provenance Learn Back returns Home");ck(h.home->page()==H::Page::Home&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"Provenance handoff returns Home safely");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Progress-origin Practice provenance checks\n";return 0;
 }
 if(homeProgressLearnPracticeTabToggle){
  Harness h(dir,"progress-learn-practice-tab-toggle");ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&h.finals()==0,"Progress-origin TAB toggle starts Home with closed output and no finalized activity");ck(h.home->navigate(H::Page::Progress),"attached Progress opens for TAB toggle");auto& progress=A::progress(*h.home);h.wait([&]{return !progress.busy();},"Progress TAB toggle read settles");click(progress,"Choose practice in Learn");h.wait([&]{return h.home->page()==H::Page::Learn;},"Progress TAB toggle enters Learn");auto& learn=A::lessons(*h.home);ck(learn.selectLesson("fg:item:000002")&&learn.selectVariant("fg:variant:000006"),"Progress-origin TAB toggle selects the retained admitted case");const auto& selected=learn.catalog()->variant("fg:item:000002","fg:variant:000006");click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"Progress-origin TAB toggle enters Practice");auto& tabButton=button(h.practice(),"Show Results / transport");ck(h.practice().tabView().isVisible()&&tabButton.isVisible()&&tabButton.isEnabled()&&h.practice().tabView().document()&&&h.practice().tabView().document()->source()==&selected.model->source(),"Progress-origin Practice starts with the authored TAB visible and exact source model");click(h.practice(),"Show Results / transport");h.tick();ck(!h.practice().tabView().isVisible()&&button(h.practice(),"Show TAB").isVisible()&&h.practice().captureSession()->phase()==capture::SessionPhase::Idle&&!h.practice().captureSession()->startTaken()&&h.finals()==0,"TAB disclosure hides the view without starting Practice activity");click(h.practice(),"Show TAB");h.tick();ck(h.practice().tabView().isVisible()&&button(h.practice(),"Show Results / transport").isVisible()&&h.practice().tabView().document()&&&h.practice().tabView().document()->source()==&selected.model->source()&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"TAB disclosure restores the same source model with stopped closed output");click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"TAB toggle Practice Back returns Learn");ck(learn.selectedLesson()=="fg:item:000002"&&learn.selectedVariant()=="fg:variant:000006"&&h.finals()==0,"TAB toggle Practice Back preserves the selected source identity");click(learn,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"TAB toggle Learn Back returns Home");ck(h.home->page()==H::Page::Home&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"TAB toggle returns Home safely without activity or output mutation");out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Progress-origin Practice TAB toggle checks\n";return 0;
 }
 if(homeProgressLearnPracticeAudioSave){
  Harness h(dir,"progress-learn-practice-audio-save");ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&h.finals()==0,"Progress-origin audio save starts Home with closed output and no finalized activity");ck(h.home->navigate(H::Page::Progress),"attached Progress opens for audio save");auto& progress=A::progress(*h.home);h.wait([&]{return !progress.busy();},"Progress audio save read settles");click(progress,"Choose practice in Learn");h.wait([&]{return h.home->page()==H::Page::Learn;},"Progress audio save enters Learn");auto& learn=A::lessons(*h.home);ck(learn.selectLesson("fg:item:000002")&&learn.selectVariant("fg:variant:000006"),"Progress-origin audio save selects the retained admitted case");click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"Progress-origin audio save enters Practice");ck(h.practice().captureSession()!=nullptr&&!h.practice().captureSession()->startTaken()&&h.practice().outputStatus().lifecycle.state==output::State::Closed&&h.finals()==0,"Practice audio save starts stopped with explicit Start and no finalization");click(h.practice(),"Audio settings");h.wait([&]{return h.home->page()==H::Page::Audio;},"Practice opens shared Audio");auto& audio=A::settings(*h.home);ck(h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"opening shared Audio does not start output");click(audio,"Connect audio");h.tick();click(audio,"Enable audio");h.blocks(1);h.wait([&]{return h.home->audioSettings().snapshot().state==output::State::Ready;},"shared Audio becomes Ready");ck(h.home->audioSettings().snapshot().state==output::State::Ready&&connections==1&&nativeOpens==0,"explicit Connect then Enable opens one synthetic shared output");click(audio,"Back to Practice");h.wait([&]{return h.home->page()==H::Page::Practice;},"shared Audio Back returns Practice");ck(h.practice().lessonAdmission()!=nullptr&&h.practice().captureSession()->phase()==capture::SessionPhase::Idle&&!h.practice().captureSession()->startTaken()&&h.practice().outputStatus().lifecycle.state==output::State::Ready&&h.finals()==0,"Practice retains the admitted case and explicit Start after audio setup");click(h.practice(),"Start selected case");h.wait([&]{return h.practice().captureSession()->startTaken();},"Progress-origin Practice Start");h.blocks(1);ck(h.practice().coordinator().state()==practice::State::Running&&h.finals()==0,"explicit Start begins one unfinalized local Attempt");click(h.practice(),"Stop & review result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"Progress-origin Practice Review");ck(h.practice().captureSession()->phase()==capture::SessionPhase::Review&&h.finals()==0,"Stop creates Review without finalization before Save");click(h.practice(),"Save result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"Progress-origin Practice Save");h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"Progress-origin Practice audio cleanup");ck(h.practice().captureSession()->phase()==capture::SessionPhase::Saved&&h.practice().audioCanRelease()&&h.finals()==1&&h.practice().lessonAdmission()->identity().object().at("item_id").string()=="fg:item:000002"&&h.practice().lessonAdmission()->identity().object().at("variant_id").string()=="fg:variant:000006","Save settles one disposable Attempt with exact source identity");click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"saved audio Practice Back returns Learn");ck(learn.selectedLesson()=="fg:item:000002"&&learn.selectedVariant()=="fg:variant:000006"&&h.finals()==1&&h.home->audioSettings().snapshot().state==output::State::Closed,"saved Back preserves selection after audio cleanup");click(learn,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"saved audio Learn Back returns Home");ck(h.home->page()==H::Page::Home&&h.finals()==1&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==1,"Progress-origin audio save returns Home with closed output and one synthetic connection");out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Progress-origin Practice audio save checks\n";return 0;
 }
 if(practiceSaveProgressReview){
  Harness h(dir,"practice-save-progress-review");
  ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&h.finals()==0,"Practice Save Progress review starts Home with closed output and no finalized activity");
  ck(h.home->navigate(H::Page::Progress),"attached Progress opens before Practice Save review");
  auto& initialProgress=A::progress(*h.home);h.wait([&]{return !initialProgress.busy();},"Practice Save Progress initial read settles");
  click(initialProgress,"Choose practice in Learn");h.wait([&]{return h.home->page()==H::Page::Learn;},"Progress enters Learn for Practice Save review");
  auto& learn=A::lessons(*h.home);ck(learn.selectLesson("fg:item:000002")&&learn.selectVariant("fg:variant:000006"),"Practice Save review selects the retained admitted case");
  click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"Practice Save review enters Practice");
  ck(h.practice().captureSession()!=nullptr&&!h.practice().captureSession()->startTaken()&&h.practice().outputStatus().lifecycle.state==output::State::Closed&&h.finals()==0,"Practice Save review starts stopped with explicit Start and no finalization");
  click(h.practice(),"Audio settings");h.wait([&]{return h.home->page()==H::Page::Audio;},"Practice Save review opens shared Audio");
  auto& audio=A::settings(*h.home);click(audio,"Connect audio");h.tick();click(audio,"Enable audio");h.blocks(1);h.wait([&]{return h.home->audioSettings().snapshot().state==output::State::Ready;},"Practice Save review audio becomes Ready");
  click(audio,"Back to Practice");h.wait([&]{return h.home->page()==H::Page::Practice;},"Practice Save review returns from Audio");click(h.practice(),"Start selected case");h.wait([&]{return h.practice().captureSession()->startTaken();},"Practice Save review starts explicit Attempt");h.blocks(1);
  ck(h.practice().coordinator().state()==practice::State::Running&&h.finals()==0,"Practice Save review has one unfinalized running Attempt");click(h.practice(),"Stop & review result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"Practice Save review enters Review");click(h.practice(),"Save result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"Practice Save review reaches Saved");h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"Practice Save review audio cleanup settles");
  ck(h.finals()==1&&h.practice().captureSession()->phase()==capture::SessionPhase::Saved&&h.practice().audioCanRelease()&&h.practice().lessonAdmission()->identity().object().at("item_id").string()=="fg:item:000002"&&h.practice().lessonAdmission()->identity().object().at("variant_id").string()=="fg:variant:000006","Practice Save review finalizes exactly one Attempt with exact source identity");
  click(h.practice(),"Open Progress");h.wait([&]{return h.home->page()==H::Page::Progress;},"saved Practice opens Progress");
  auto& progress=A::progress(*h.home);h.wait([&]{return !progress.busy()&&!progress.presentation().projection.null();},"saved Practice Progress refresh settles");const auto body=progress.presentation().text;
  ck(h.home->page()==H::Page::Progress&&A::visiblePages(*h.home)==1&&body.find("SAVED PRACTICE")!=std::string::npos&&body.find("Finalized local activity records in this snapshot: 1")!=std::string::npos&&progress.statusText().find("Finalized local activity remains read-only")!=std::string::npos&&progress.statusText().find("does not award curriculum credit")!=std::string::npos,"Progress exposes one saved read-only Practice record and no-credit guidance");
  ck(body.find("fg:item:000002 / fg:variant:000006")!=std::string::npos&&body.find("Source: L3-TXT5-21 L3-TXT28-46")!=std::string::npos&&body.find("Content version: representative-controls.1")!=std::string::npos&&body.find("Content revision: 2")!=std::string::npos&&body.find("Workbook identity: fg:workbook:000003 | Level: 3")!=std::string::npos&&body.find("Source-task completion credited: no")!=std::string::npos,"Progress retains exact saved source identity and refuses completion inference");
  const auto firstDetails=progress.presentation().details;click(progress,"Show saved details");h.tick();auto* bodyEditor=dynamic_cast<juce::TextEditor*>(progress.findChildWithID("progress-body"));ck(bodyEditor&&bodyEditor->getText().toStdString()==firstDetails&&h.finals()==1,"Progress Show saved details is read-only and creates no duplicate Attempt");click(progress,"Hide saved details");h.tick();bodyEditor=dynamic_cast<juce::TextEditor*>(progress.findChildWithID("progress-body"));ck(bodyEditor&&bodyEditor->getText().toStdString()==progress.presentation().text&&h.finals()==1,"Progress Hide saved details restores the concise read-only view");
  click(progress,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Progress Back returns Home");ck(h.home->page()==H::Page::Home&&h.finals()==1&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0,"Progress Back preserves one saved Attempt and closed audio without native activity");
  out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Practice Save Progress review checks\n";return 0;
 }
 if(savedProgressLearnReturn){
  Harness h(dir,"saved-progress-learn-return");
  ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&h.finals()==0,"saved Progress Learn return starts Home with closed output and no finalized activity");
  ck(h.home->navigate(H::Page::Progress),"attached Progress opens for saved Learn return setup");auto& initialProgress=A::progress(*h.home);h.wait([&]{return !initialProgress.busy();},"saved Learn return initial Progress settles");click(initialProgress,"Choose practice in Learn");h.wait([&]{return h.home->page()==H::Page::Learn;},"saved Learn return enters Learn for Practice setup");
  auto& learn=A::lessons(*h.home);ck(learn.catalog()&&learn.catalog()->lessons().size()==13&&learn.selectLesson("fg:item:000002")&&learn.selectVariant("fg:variant:000006"),"saved Learn return selects the retained admitted case");click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"saved Learn return enters Practice");
  click(h.practice(),"Audio settings");h.wait([&]{return h.home->page()==H::Page::Audio;},"saved Learn return opens shared Audio");auto& audio=A::settings(*h.home);click(audio,"Connect audio");h.tick();click(audio,"Enable audio");h.blocks(1);h.wait([&]{return h.home->audioSettings().snapshot().state==output::State::Ready;},"saved Learn return audio becomes Ready");click(audio,"Back to Practice");h.wait([&]{return h.home->page()==H::Page::Practice;},"saved Learn return returns from Audio");
  click(h.practice(),"Start selected case");h.wait([&]{return h.practice().captureSession()->startTaken();},"saved Learn return starts explicit Attempt");h.blocks(1);click(h.practice(),"Stop & review result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"saved Learn return enters Review");click(h.practice(),"Save result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"saved Learn return reaches Saved");h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"saved Learn return audio cleanup settles");ck(h.finals()==1&&h.practice().captureSession()->phase()==capture::SessionPhase::Saved&&h.practice().audioCanRelease(),"saved Learn return has exactly one finalized Attempt before Progress");
  click(h.practice(),"Open Progress");h.wait([&]{return h.home->page()==H::Page::Progress;},"saved Practice opens read-only Progress for Learn return");auto& progress=A::progress(*h.home);h.wait([&]{return !progress.busy()&&!progress.presentation().projection.null();},"saved Progress refresh settles before Learn return");ck(progress.presentation().text.find("fg:item:000002 / fg:variant:000006")!=std::string::npos&&progress.statusText().find("read-only")!=std::string::npos&&h.finals()==1&&h.home->audioSettings().snapshot().state==output::State::Closed,"saved Progress retains the finalized source-backed record without new activity");
  click(progress,"Choose practice in Learn");h.wait([&]{return h.home->page()==H::Page::Learn;},"saved Progress Choose practice enters Learn");auto& returnedLearn=A::lessons(*h.home);ck(h.home->page()==H::Page::Learn&&returnedLearn.catalog()&&returnedLearn.catalog()->lessons().size()==13,"saved Progress Learn return exposes the retained 13-case catalog");ck(returnedLearn.selectedLesson()=="fg:item:000002"&&returnedLearn.selectedVariant()=="fg:variant:000006"&&h.finals()==1&&h.practice().captureSession()->phase()==capture::SessionPhase::Saved&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0,"saved Progress Learn return preserves selection, one saved Attempt, closed output and zero native opens");click(returnedLearn,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"saved Progress Learn Back returns Home");ck(h.home->page()==H::Page::Home&&h.finals()==1&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0,"saved Progress Learn Back returns Home without changing saved activity");
  out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" saved Progress Learn return checks\n";return 0;
 }
 if(savedProgressRefreshReview){
  Harness h(dir,"saved-progress-refresh-review");
  ck(h.home->navigate(H::Page::Progress),"attached Progress opens for saved refresh setup");auto& initialProgress=A::progress(*h.home);h.wait([&]{return !initialProgress.busy();},"saved refresh initial Progress settles");click(initialProgress,"Choose practice in Learn");h.wait([&]{return h.home->page()==H::Page::Learn;},"saved refresh enters Learn for Practice setup");auto& learn=A::lessons(*h.home);ck(learn.catalog()&&learn.catalog()->lessons().size()==13&&learn.selectLesson("fg:item:000002")&&learn.selectVariant("fg:variant:000006"),"saved refresh selects the retained admitted case");click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"saved refresh enters Practice");click(h.practice(),"Audio settings");h.wait([&]{return h.home->page()==H::Page::Audio;},"saved refresh opens shared Audio");auto& audio=A::settings(*h.home);click(audio,"Connect audio");h.tick();click(audio,"Enable audio");h.blocks(1);h.wait([&]{return h.home->audioSettings().snapshot().state==output::State::Ready;},"saved refresh audio becomes Ready");click(audio,"Back to Practice");h.wait([&]{return h.home->page()==H::Page::Practice;},"saved refresh returns from Audio");click(h.practice(),"Start selected case");h.wait([&]{return h.practice().captureSession()->startTaken();},"saved refresh starts explicit Attempt");h.blocks(1);click(h.practice(),"Stop & review result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"saved refresh enters Review");click(h.practice(),"Save result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"saved refresh reaches Saved");h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"saved refresh audio cleanup settles");click(h.practice(),"Open Progress");h.wait([&]{return h.home->page()==H::Page::Progress;},"saved refresh opens Progress");auto& progress=A::progress(*h.home);h.wait([&]{return !progress.busy()&&!progress.presentation().projection.null();},"saved refresh first read settles");const auto firstText=progress.presentation().text;const auto firstDetails=progress.presentation().details;ck(h.finals()==1&&firstText.find("fg:item:000002 / fg:variant:000006")!=std::string::npos&&progress.statusText().find("read-only")!=std::string::npos&&h.home->audioSettings().snapshot().state==output::State::Closed,"saved Progress first read retains one exact read-only record");click(progress,"Refresh");h.wait([&]{return !progress.busy();},"saved Progress explicit Refresh settles");ck(h.finals()==1&&progress.presentation().text==firstText&&progress.presentation().details==firstDetails&&progress.presentation().projection.find("profile_id")&&progress.presentation().projection.find("profile_id")->isString()&&progress.statusText().find("does not award curriculum credit")!=std::string::npos,"Refresh re-reads the same profile and preserves exact saved presentation without duplicate activity");click(progress,"Show saved details");h.tick();auto* bodyEditor=dynamic_cast<juce::TextEditor*>(progress.findChildWithID("progress-body"));ck(bodyEditor&&bodyEditor->getText().toStdString()==firstDetails&&h.finals()==1&&nativeOpens==0,"saved details remains read-only after Refresh");click(progress,"Hide saved details");h.tick();bodyEditor=dynamic_cast<juce::TextEditor*>(progress.findChildWithID("progress-body"));ck(bodyEditor&&bodyEditor->getText().toStdString()==firstText&&h.finals()==1&&h.home->audioSettings().snapshot().state==output::State::Closed,"hiding details restores the refreshed concise view");click(progress,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"saved refresh Progress Back returns Home");ck(h.finals()==1&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0,"saved refresh returns Home with one saved Attempt and closed audio");out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" saved Progress refresh checks\n";return 0;
 }
 if(freeplaySurfaceOnly){
  desktop::FreeplayView view;view.setSize(920,680);view.setVisible(true);
  juce::Label* heading = nullptr;
  for(auto* child:view.getChildren())
   if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText().toStdString()=="FREEPLAY — SEPARATE LOCAL ACTIVITY"){heading=label;break;}
  ck(heading&&heading->getText().toStdString()=="FREEPLAY — SEPARATE LOCAL ACTIVITY","Freeplay heading identifies separate local activity");
  auto* explanation=dynamic_cast<juce::Label*>(view.findChildWithID("freeplay-explanation"));
  auto* status=dynamic_cast<juce::Label*>(view.findChildWithID("freeplay-status"));
  ck(explanation&&explanation->isVisible()&&explanation->getTitle().toStdString()=="Read-only Freeplay entry: separate active time/history, shared Audio and no curriculum credit."&&explanation->getText().toStdString().find("Stopped Freeplay activity is saved locally as separate history and never grants curriculum progress.")!=std::string::npos,"Freeplay explanation exposes the separate-history/shared-Audio/no-credit boundary");
  ck(explanation&&explanation->getHeight()>=104&&view.getLocalBounds().contains(explanation->getBounds())&&explanation->getBottom()<=view.findChildWithID("freeplay-status")->getY(),"Freeplay explanation reserves readable contained space above the lifecycle status");
  ck(status&&status->getTitle().toStdString()=="Read-only Freeplay lifecycle, active time, save boundary and next action.","Freeplay status exposes a stable truthful lifecycle title");
  const auto statusText=status?status->getText().toStdString():std::string{};
  ck(status&&status->isVisible()&&statusText.find("Freeplay is stopped")!=std::string::npos&&statusText.find("Opening Freeplay does not start sound.")!=std::string::npos&&statusText.find("Stop saves one separate local Freeplay history entry when a local profile is configured")!=std::string::npos,"Freeplay status preserves the no-sound-on-entry, stopped and separate-history boundary");
  ck(status&&statusText.find("Next action: choose Start freeplay to begin active-time capture")!=std::string::npos,"Freeplay status preserves the exact initial Start next action");
  ck(status&&status->getHeight()>=50&&view.getLocalBounds().contains(status->getBounds()),"Freeplay status remains readable and contained in the 920x680 layout");
  ck(!view.active()&&view.canLeave()&&!view.persistenceConfigured()&&view.historyWriteCount()==0,"Freeplay status inspection creates no profile access, active time or history");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Freeplay status surface checks\n";return 0;
 }
 if(audioSurfaceOnly){
  desktop::AudioOutputView view;view.setSize(920,680);view.setVisible(true);
  auto* description=dynamic_cast<juce::Label*>(view.findChildWithID("shared-audio-description"));
  auto* unbound=dynamic_cast<juce::Label*>(view.findChildWithID("audio-unbound-state"));
  ck(unbound&&unbound->isVisible()&&unbound->getText().toStdString()=="Shared Audio settings are waiting for the calling activity."&&unbound->getTitle().toStdString()=="Shared Audio unbound state marker."&&view.getLocalBounds().contains(unbound->getBounds()),"detached shared Audio exposes a contained unbound state marker");
  ck(description&&description->getTitle().toStdString()=="Read-only shared Audio: Connect/Enable is explicit; activity controls begin sound across local tools.","shared Audio explanation exposes the stable explicit-start title");
  const auto descriptionText=description?description->getText().toStdString():std::string{};
  ck(description&&descriptionText.find("Connect your macOS speakers or headphones, then Enable audio.")!=std::string::npos&&descriptionText.find("Opening Audio settings never starts sound.")!=std::string::npos&&descriptionText.find("These shared settings apply across Learn, Practice, Freeplay and rhythm tools.")!=std::string::npos&&descriptionText.find("Disconnect is enabled only when the current activity can be released safely.")!=std::string::npos,"shared Audio explanation retains explicit-start, authored scope and safe-release text");
  auto* status=dynamic_cast<juce::Label*>(view.findChildWithID("shared-audio-status"));
  ck(status&&status->getTitle().toStdString()=="Read-only shared Audio lifecycle, output state, next action and safe release boundary.","shared Audio status exposes a stable truthful lifecycle title");
  const auto statusText=status?status->getText().toStdString():std::string{};
  ck(status&&status->isVisible()&&statusText.find("Audio settings awaits its playback view.")!=std::string::npos,"shared Audio status preserves the detached no-playback guidance");
  auto* connect=dynamic_cast<juce::TextButton*>(view.findChildWithID("audio-connect"));auto* enable=dynamic_cast<juce::TextButton*>(view.findChildWithID("audio-enable"));auto* disconnect=dynamic_cast<juce::TextButton*>(view.findChildWithID("audio-disconnect"));auto* firstGain=dynamic_cast<juce::Slider*>(view.findChildWithID("audio-master-volume"));auto* lastGain=dynamic_cast<juce::Slider*>(view.findChildWithID("audio-rhythm-b-volume"));auto* back=dynamic_cast<juce::TextButton*>(view.findChildWithID("audio-back"));
  ck(description&&description->getHeight()>=72&&view.getLocalBounds().contains(description->getBounds())&&description->getBottom()<=unbound->getY()&&unbound->getBottom()<=status->getY(),"shared Audio explanation, unbound state and lifecycle status remain ordered");
  ck(status&&status->getHeight()>=72&&view.getLocalBounds().contains(status->getBounds())&&connect&&enable&&disconnect&&firstGain&&lastGain&&back&&view.getLocalBounds().contains(connect->getBounds())&&view.getLocalBounds().contains(enable->getBounds())&&view.getLocalBounds().contains(disconnect->getBounds())&&view.getLocalBounds().contains(firstGain->getBounds())&&view.getLocalBounds().contains(lastGain->getBounds())&&view.getLocalBounds().contains(back->getBounds())&&status->getBottom()<=connect->getY()&&disconnect->getBottom()<=firstGain->getY()&&lastGain->getBottom()<=back->getY(),"shared Audio status, controls and mix rows remain readable, ordered and contained in the 920x680 layout");
  ck(nativeOpens==0&&connections==0,"detached shared Audio status inspection creates no native output claim");
 out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" shared Audio status surface checks\n";return 0;
 }
 if(audioResponsiveOnly){
  desktop::AudioOutputView view;view.setSize(640,680);view.setVisible(true);
  const auto bounds=view.getLocalBounds();
  const char* visibleIds[]={"shared-audio-description","shared-audio-status","audio-connect","audio-enable","audio-disconnect","audio-master-volume","audio-reference-volume","audio-metronome-volume","audio-rhythm-a-volume","audio-rhythm-b-volume","audio-master-mute","audio-reference-mute","audio-metronome-mute","audio-rhythm-a-mute","audio-rhythm-b-mute","audio-rhythm-a-solo","audio-rhythm-b-solo","audio-back"};
  for(const auto* id:visibleIds){auto* component=view.findChildWithID(id);ck(component&&component->isVisible()&&bounds.contains(component->getBounds())&&component->getWidth()>0&&component->getHeight()>0,std::string("Compact Audio surface remains visible and contained: ")+id);}
  const char* actions[]={"audio-connect","audio-enable","audio-disconnect","audio-back"};
  for(std::size_t leftIndex=0;leftIndex<std::size(actions);++leftIndex)for(std::size_t rightIndex=leftIndex+1;rightIndex<std::size(actions);++rightIndex){const auto* left=view.findChildWithID(actions[leftIndex]);const auto* right=view.findChildWithID(actions[rightIndex]);ck(left&&right&&!left->getBounds().intersects(right->getBounds()),std::string("Compact Audio actions do not overlap: ")+actions[leftIndex]+"/"+actions[rightIndex]);}
  const char* gains[]={"audio-master-volume","audio-reference-volume","audio-metronome-volume","audio-rhythm-a-volume","audio-rhythm-b-volume"};
  const char* mutes[]={"audio-master-mute","audio-reference-mute","audio-metronome-mute","audio-rhythm-a-mute","audio-rhythm-b-mute"};
  const char* solos[]={"audio-rhythm-a-solo","audio-rhythm-b-solo"};
  for(std::size_t i=0;i<std::size(gains);++i){const auto* gain=view.findChildWithID(gains[i]);const auto* mute=view.findChildWithID(mutes[i]);ck(gain&&mute&&!gain->getBounds().intersects(mute->getBounds()),std::string("Compact Audio mix row does not overlap: ")+gains[i]+"/"+mutes[i]);if(i>=3){const auto* solo=view.findChildWithID(solos[i-3]);ck(solo&&mute&&!mute->getBounds().intersects(solo->getBounds())&&gain&&!gain->getBounds().intersects(solo->getBounds()),std::string("Compact Audio rhythm row does not overlap: ")+solos[i-3]);}}
  auto* description=dynamic_cast<juce::Label*>(view.findChildWithID("shared-audio-description"));auto* status=dynamic_cast<juce::Label*>(view.findChildWithID("shared-audio-status"));
  const auto* compactTitle=dynamic_cast<const juce::Label*>(view.getChildComponent(0));ck(compactTitle&&compactTitle->getText()==juce::String::fromUTF8("Audio — Shared output settings"),"Compact Audio renders the exact shared-output heading with an em dash");
  auto* connect=dynamic_cast<juce::TextButton*>(view.findChildWithID("audio-connect"));auto* enable=dynamic_cast<juce::TextButton*>(view.findChildWithID("audio-enable"));auto* disconnect=dynamic_cast<juce::TextButton*>(view.findChildWithID("audio-disconnect"));auto* back=dynamic_cast<juce::TextButton*>(view.findChildWithID("audio-back"));
  ck(connect&&connect->getButtonText().toStdString()=="Connect audio"&&enable&&enable->getButtonText().toStdString()=="Enable audio"&&disconnect&&disconnect->getButtonText().toStdString()=="Disconnect"&&back&&back->getButtonText().toStdString()=="Back","Compact Audio preserves lifecycle labels");
  ck(description&&status&&description->getBottom()<=status->getY()&&status->getBottom()<=connect->getY()&&view.getLocalBounds().contains(description->getBounds())&&view.getLocalBounds().contains(status->getBounds()),"Compact Audio preserves readable guidance order");
  ck(status&&status->getText().toStdString().find("Audio settings awaits its playback view.")!=std::string::npos&&nativeOpens==0&&connections==0,"Compact Audio remains detached, closed and honest without native output");
  desktop::AudioOutputView standard;standard.setSize(920,680);standard.setVisible(true);standard.resized();
  const auto* standardTitle=dynamic_cast<const juce::Label*>(standard.getChildComponent(0));ck(standardTitle&&standardTitle->getText()==juce::String::fromUTF8("AUDIO — SHARED OUTPUT SETTINGS"),"Standard Audio restores the exact authored heading");
  ck(standard.findChildWithID("audio-connect")->getBounds().getX()==40&&standard.findChildWithID("audio-connect")->getBounds().getY()==278&&standard.findChildWithID("audio-back")->getBounds().getY()==608,"Standard Audio geometry remains unchanged at 920x680");
  out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Compact Audio responsive layout checks\n";return 0;
 }
 if(rhythmSharedCycleOnly){
  desktop::SchedulerView view;view.setSize(920,680);view.setVisible(true);view.resized();
  scheduler::Owner planOwner{};planOwner.id[6]=0x40;planOwner.id[8]=0x80;planOwner.generation=1;planOwner.epoch=1;
  const auto plans=desktop::previewPlans(planOwner,44100);const auto& events=plans.front().events();
  std::vector<Rational> layerA,layerB;for(const auto& event:events)if(event.action==scheduler::Action::Attack){if(event.role==scheduler::Role::LayerA)layerA.push_back(event.structural);if(event.role==scheduler::Role::LayerB)layerB.push_back(event.structural);}
  ck(plans.size()==3&&plans.front().valid()&&layerA.size()==3&&layerB.size()==2,"shared-cycle test reads the three current compiled preview plans and their Layer A/B attack facts");
  ck(layerA==std::vector<Rational>{Rational{0},Rational{4,3},Rational{8,3}}&&layerB==std::vector<Rational>{Rational{0},Rational{2}},"compiled scheduler facts place three A hits and two B hits on one synchronized 4-quarter 3:2 cycle");
  auto* cycle=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-shared-cycle"));auto* a=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-layer-a"));auto* b=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-layer-b"));
  ck(cycle&&cycle->isVisible()&&cycle->getText().toStdString().find("Shared cycle")!=std::string::npos&&cycle->getTitle().toStdString().find("four quarter beats")!=std::string::npos&&cycle->getTitle().toStdString().find("begin together at phase 0")!=std::string::npos,"visible shared-cycle heading exposes common length and synchronized start accessibly");
  ck(a&&a->isVisible()&&a->getText().toStdString().find("Layer A")!=std::string::npos&&a->getText().toStdString().find("3 hits")!=std::string::npos&&a->getTitle().toStdString().find("0, 4/3, 8/3")!=std::string::npos&&a->getTitle().toStdString().find("first hit aligns with Layer B")!=std::string::npos,"Layer A row exposes its name, hit count and exact scheduled phases accessibly");
  ck(b&&b->isVisible()&&b->getText().toStdString().find("Layer B")!=std::string::npos&&b->getText().toStdString().find("2 hits")!=std::string::npos&&b->getTitle().toStdString().find("0, 2")!=std::string::npos&&b->getTitle().toStdString().find("first hit aligns with Layer A")!=std::string::npos,"Layer B row exposes its name, hit count and exact scheduled phases accessibly");
  juce::Image image(juce::Image::RGB,920,680,true);juce::Graphics graphics(image);view.paint(graphics);
  const int cycleLeft=190,cycleWidth=920-24-cycleLeft,layerAY=396,layerBY=420;bool aMarkers=true,bMarkers=true;
  for(const auto phase:{0.0,1.0/3.0,2.0/3.0})aMarkers=aMarkers&&image.getPixelAt(cycleLeft+static_cast<int>(cycleWidth*phase),layerAY)==juce::Colour{0xff6bd5cb};
  for(const auto phase:{0.0,0.5})bMarkers=bMarkers&&image.getPixelAt(cycleLeft+static_cast<int>(cycleWidth*phase),layerBY)==juce::Colour{0xffffc857};
  ck(aMarkers&&bMarkers,"software-rendered shared cycle draws teal triangle hits for A and amber circle hits for B");
  const auto standardBounds=view.getLocalBounds();const char* standardIds[]={"rhythm-shared-cycle","rhythm-layer-a","rhythm-layer-b"};bool standardContained=true;for(const auto* id:standardIds){const auto* item=view.findChildWithID(id);standardContained=standardContained&&item&&item->isVisible()&&item->getWidth()>0&&item->getHeight()>0&&standardBounds.contains(item->getBounds());}
  const char* actions[]={"rhythm-audio-settings","rhythm-start","rhythm-stop","rhythm-finish","rhythm-back"};for(const auto* id:actions){const auto* action=view.findChildWithID(id);for(const auto* layer:standardIds){const auto* row=view.findChildWithID(layer);standardContained=standardContained&&action&&row&&!action->getBounds().intersects(row->getBounds());}}
  ck(standardContained,"standard shared-cycle information and existing Rhythm controls remain visible, contained and non-overlapping");
  desktop::SchedulerView compact;compact.setSize(640,680);compact.setVisible(true);compact.resized();const auto compactBounds=compact.getLocalBounds();bool compactContained=true;for(const auto* id:standardIds){const auto* item=compact.findChildWithID(id);compactContained=compactContained&&item&&item->isVisible()&&item->getWidth()>0&&item->getHeight()>0&&compactBounds.contains(item->getBounds());}for(const auto* id:actions){const auto* action=compact.findChildWithID(id);for(const auto* layer:standardIds){const auto* row=compact.findChildWithID(layer);compactContained=compactContained&&action&&row&&!action->getBounds().intersects(row->getBounds());}}
  ck(compactContained,"compact shared-cycle information and existing Rhythm controls remain visible, contained and non-overlapping");
  const auto snapshot=view.audioSnapshot();ck(snapshot.state==output::State::Closed&&view.audioCanRelease()&&!snapshot.owner.valid()&&!snapshot.ownsOutcome&&!snapshot.pendingOutcome&&nativeOpens==0&&connections==0,"cycle visualization is inspectable before explicit Start with Closed output, no owner or native connection");
  if(rhythmRatioSelectionOnly){
   using polyrhythm::Ratio;
   const std::array<Ratio,8> presets{{{2,3},{3,2},{3,4},{4,3},{4,5},{5,4},{5,7},{7,5}}};
   auto* preset=dynamic_cast<juce::ComboBox*>(view.findChildWithID("rhythm-ratio-preset"));
   auto* customX=dynamic_cast<juce::TextEditor*>(view.findChildWithID("rhythm-ratio-x"));
   auto* customY=dynamic_cast<juce::TextEditor*>(view.findChildWithID("rhythm-ratio-y"));
   auto* apply=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-ratio-apply"));
   auto* message=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-ratio-message"));
   ck(preset&&preset->isVisible()&&preset->getNumItems()==9&&preset->getSelectedId()==2&&customX&&customY&&apply&&message,"ratio controls expose eight contract presets plus custom entry, with 3:2 initially selected before Start");
   bool exactPresetList=preset!=nullptr;
   for(std::size_t i=0;i<presets.size()&&preset;++i){
    const auto expected=std::to_string(presets[i].x)+":"+std::to_string(presets[i].y);
    exactPresetList=exactPresetList&&preset->getItemText(static_cast<int>(i)).toStdString()==expected;
   }
   exactPresetList=exactPresetList&&preset&&preset->getItemText(8).toStdString().find("Custom")!=std::string::npos&&preset->getTitle().toStdString().find("Layer A")!=std::string::npos&&preset->getTitle().toStdString().find("Layer B")!=std::string::npos;
   ck(exactPresetList,"preset control names exactly the accepted 5.1 X:Y ratios and documents Layer A/B assignment accessibly");
   auto phaseList=[](const std::vector<Rational>& phases){std::ostringstream text;for(std::size_t i=0;i<phases.size();++i){if(i)text<<", ";text<<phases[i].numerator();if(phases[i].denominator()!=1)text<<"/"<<phases[i].denominator();}return text.str();};
   auto exactPlan=[&](const scheduler::Plan& plan,Ratio ratio,bool hasCountIn){
    std::vector<Rational> a,b,expectedA,expectedB;
    for(const auto& event:plan.events())if(event.action==scheduler::Action::Attack){if(event.role==scheduler::Role::LayerA)a.push_back(event.structural);if(event.role==scheduler::Role::LayerB)b.push_back(event.structural);}
    for(int i=0;i<ratio.x;++i)expectedA.emplace_back(4*i,ratio.x);
    for(int i=0;i<ratio.y;++i)expectedB.emplace_back(4*i,ratio.y);
    return plan.valid()&&plan.countIn().size()==(hasCountIn?4U:0U)&&a==expectedA&&b==expectedB;
   };
   auto allPlans=[&](Ratio ratio){const auto plans=desktop::previewPlans(planOwner,44100,ratio);return plans.size()==3&&exactPlan(plans[0],ratio,true)&&exactPlan(plans[1],ratio,false)&&exactPlan(plans[2],ratio,false);};
   auto visibleRatio=[&](desktop::SchedulerView& target,Ratio ratio){
    auto* heading=dynamic_cast<juce::Label*>(target.findChildWithID("rhythm-shared-cycle"));
    auto* a=dynamic_cast<juce::Label*>(target.findChildWithID("rhythm-layer-a"));auto* b=dynamic_cast<juce::Label*>(target.findChildWithID("rhythm-layer-b"));
    const auto ratioText=std::to_string(ratio.x)+":"+std::to_string(ratio.y);
    if(!heading||!a||!b)return false;
    return heading->getText().toStdString().find(ratioText)!=std::string::npos&&
      a->getText().toStdString().find(std::to_string(ratio.x)+" hits")!=std::string::npos&&
      b->getText().toStdString().find(std::to_string(ratio.y)+" hits")!=std::string::npos&&
      a->getTitle().toStdString().find(phaseList([&]{std::vector<Rational> v;for(int i=0;i<ratio.x;++i)v.emplace_back(4*i,ratio.x);return v;}()))!=std::string::npos&&
      b->getTitle().toStdString().find(phaseList([&]{std::vector<Rational> v;for(int i=0;i<ratio.y;++i)v.emplace_back(4*i,ratio.y);return v;}()))!=std::string::npos;
   };
   auto visibleMarkers=[&](Ratio ratio){
    auto* a=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-layer-a"));auto* b=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-layer-b"));if(!a||!b)return false;
    juce::Image frame(juce::Image::RGB,view.getWidth(),view.getHeight(),true);juce::Graphics graphics(frame);view.paint(graphics);
    const int left=190,width=view.getWidth()-24-left,ay=a->getBounds().getCentreY(),by=b->getBounds().getCentreY();
    for(int i=0;i<ratio.x;++i){const int x=left+static_cast<int>(width*static_cast<double>(i)/ratio.x);if(frame.getPixelAt(x,ay)!=juce::Colour{0xff6bd5cb})return false;}
    for(int i=0;i<ratio.y;++i){const int x=left+static_cast<int>(width*static_cast<double>(i)/ratio.y);if(frame.getPixelAt(x,by)!=juce::Colour{0xffffc857})return false;}
    return true;
   };
   auto markerDiagnostic=[&](Ratio ratio){
    std::ostringstream detail;bool okay=true;
    auto* a=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-layer-a"));auto* b=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-layer-b"));
    if(!a||!b)return std::pair{false,std::string{"missing layer label"}};
    juce::Image frame(juce::Image::RGB,view.getWidth(),view.getHeight(),true);juce::Graphics graphics(frame);view.paint(graphics);
    const int left=190,width=view.getWidth()-24-left,ay=a->getBounds().getCentreY(),by=b->getBounds().getCentreY();
    for(int i=0;i<ratio.x;++i){const int x=left+static_cast<int>(width*static_cast<double>(i)/ratio.x);const bool match=frame.getPixelAt(x,ay)==juce::Colour{0xff6bd5cb};okay=okay&&match;detail<<"A"<<i<<"@"<<x<<","<<ay<<"="<<(match?"PASS":"FAIL")<<";";}
    for(int i=0;i<ratio.y;++i){const int x=left+static_cast<int>(width*static_cast<double>(i)/ratio.y);const bool match=frame.getPixelAt(x,by)==juce::Colour{0xffffc857};okay=okay&&match;detail<<"B"<<i<<"@"<<x<<","<<by<<"="<<(match?"PASS":"FAIL")<<";";}
    return std::pair{okay,detail.str()};
   };
   bool allPresetViews=true;
   for(std::size_t i=0;i<presets.size();++i){
    preset->setSelectedId(static_cast<int>(i)+1,juce::sendNotificationSync);pump();
    const bool viewOkay=visibleRatio(view,presets[i]);const bool plansOkay=allPlans(presets[i]);const bool markersOkay=visibleMarkers(presets[i]);
    const auto plans=desktop::previewPlans(planOwner,44100,presets[i]);const bool p0=plans.size()==3&&exactPlan(plans[0],presets[i],true);const bool p1=plans.size()==3&&exactPlan(plans[1],presets[i],false);const bool p2=plans.size()==3&&exactPlan(plans[2],presets[i],false);
    const auto markerFacts=markerDiagnostic(presets[i]);
    auto* heading=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-shared-cycle"));auto* a=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-layer-a"));auto* b=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-layer-b"));
    out<<"preset-diagnostic\t"<<std::to_string(presets[i].x)+":"+std::to_string(presets[i].y)<<"\tview="<<(viewOkay?"PASS":"FAIL")<<"\tplans="<<(plansOkay?"PASS":"FAIL")<<"\tp0="<<(p0?"PASS":"FAIL")<<"\tp1="<<(p1?"PASS":"FAIL")<<"\tp2="<<(p2?"PASS":"FAIL")<<"\tmarkers="<<(markersOkay?"PASS":"FAIL")<<"\tcycle="<<(heading?heading->getText().toStdString():"<missing>")<<"\tA="<<(a?a->getText().toStdString()+" | "+a->getTitle().toStdString():"<missing>")<<"\tB="<<(b?b->getText().toStdString()+" | "+b->getTitle().toStdString():"<missing>")<<"\tpixels="<<markerFacts.second<<"\n";out.flush();
    allPresetViews=allPresetViews&&viewOkay&&plansOkay&&markersOkay;
   }
   ck(allPresetViews,"all eight selectable presets drive exact X/Y counts, compiled count-in plus both tempo plans, accessible phases and correctly colored event markers");
   auto applyCustom=[&](const std::string& x,const std::string& y){preset->setSelectedId(9,juce::sendNotificationSync);customX->setText(x);customY->setText(y);activate(*apply);pump();};
   applyCustom("8","12");
   ck(visibleRatio(view,{8,12})&&allPlans({8,12})&&visibleMarkers({8,12})&&message->getText().isEmpty(),"valid reducible custom 8:12 remains literal in displayed counts, markers and all scheduler plans");
   applyCustom("1","16");
   ck(visibleRatio(view,{1,16})&&allPlans({1,16})&&visibleMarkers({1,16})&&message->getText().isEmpty(),"custom ratio accepts validator boundary counts 1 and 16 without reducing literal hit counts");
   bool invalidRefused=true;
   for(const auto& input:std::array<std::pair<std::string,std::string>,4>{{{"bad","3"},{"0","3"},{"17","3"},{"4","4"}}}){
    applyCustom(input.first,input.second);invalidRefused=invalidRefused&&visibleRatio(view,{1,16})&&allPlans({1,16})&&!message->getText().isEmpty();
   }
   ck(invalidRefused,"malformed, below-range, above-range and equal-count custom ratios are explained and refused without substituting or mutating the last valid 1:16 plan");

   Harness h(dir,"live-rhythm-ratio-selection");h.setup();click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Practice Back to Home");
   click(*h.home,"Rhythm preview");auto& live=A::rhythm(*h.home);auto* livePreset=dynamic_cast<juce::ComboBox*>(live.findChildWithID("rhythm-ratio-preset"));
   ck(livePreset&&livePreset->isEnabled(),"new independent Rhythm preview exposes ratio selection before output setup");
   livePreset->setSelectedId(7,juce::sendNotificationSync);pump();
   click(live,"Audio settings");h.tick();auto& settings=A::settings(*h.home);click(settings,"Connect audio");h.tick();click(settings,"Enable audio");h.blocks(1);click(settings,"Back to Rhythm preview");h.tick();
   scheduler::Owner expectedOwner{};expectedOwner.id[6]=0x40;expectedOwner.id[8]=0x80;expectedOwner.generation=1;expectedOwner.epoch=live.audioSnapshot().request.epoch;
   scheduler::ScheduledStream expected;expected.prepare(desktop::previewPlans(expectedOwner,44100,{5,7}),4,2,1);
   const auto discard=[](void*,std::uint64_t,std::uint32_t,const scheduler::Fact*,std::size_t) noexcept{return true;};
   int callbackBlocks{},oracleBlocks{};auto advance=[&]{if(++callbackBlocks>1400)throw std::runtime_error("ratio selection walkthrough callback watchdog");auto& output=A::output(*h.home);platform::OutputTestAccess::block(output);h.tick();if(output.status().lifecycle.state==output::State::Running){const auto outcome=expected.process(expectedOwner,44100,256,discard,nullptr);if(!outcome.valid)throw std::runtime_error("ratio selection oracle failed to process callback");scheduler::Fact fact;while(expected.nextFact(fact)){}scheduler::StreamView copied;while(expected.nextView(copied)){}++oracleBlocks;}};
   auto matchesCursor=[&]{auto* a=dynamic_cast<juce::Label*>(live.findChildWithID("rhythm-layer-a"));auto* b=dynamic_cast<juce::Label*>(live.findChildWithID("rhythm-layer-b"));if(!a||!b)return false;juce::Image frame(juce::Image::RGB,live.getWidth(),live.getHeight(),true);juce::Graphics graphics(frame);live.paint(graphics);const int y=(a->getBounds().getCentreY()+b->getBounds().getCentreY())/2;std::vector<int> xs;for(int x=190;x<live.getWidth()-24;++x){const auto pixel=frame.getPixelAt(x,y);if(pixel.getRed()>220&&pixel.getGreen()>230&&pixel.getBlue()>230)xs.push_back(x);}if(xs.empty())return false;const auto facts=expected.quiescentView();const long double span=static_cast<long double>(facts.phaseSpan.n)/facts.phaseSpan.d;const auto elapsed=facts.cursor.processedThrough>=facts.phaseOrigin?facts.cursor.processedThrough-facts.phaseOrigin:0;const double phase=span>0?std::clamp(static_cast<double>(static_cast<long double>(elapsed)/span),0.0,1.0):0.0;const int target=190+static_cast<int>((live.getWidth()-24-190)*phase);return std::abs((xs.front()+xs.back())/2-target)<=2;};
   click(live,"Start preview");advance();
   ck(live.audioSnapshot().state==output::State::Running&&expected.quiescentView().cursor.state==scheduler::State::CountIn&&nativeOpens==0,"selected 5:7 starts on the existing one-stream count-in path with native output closed");
   auto* liveX=dynamic_cast<juce::TextEditor*>(live.findChildWithID("rhythm-ratio-x"));auto* liveY=dynamic_cast<juce::TextEditor*>(live.findChildWithID("rhythm-ratio-y"));auto* liveApply=dynamic_cast<juce::TextButton*>(live.findChildWithID("rhythm-ratio-apply"));
   const bool locked=livePreset&&!livePreset->isEnabled()&&liveX&&!liveX->isEnabled()&&liveY&&!liveY->isEnabled()&&liveApply&&!liveApply->isEnabled();
   if(livePreset)livePreset->setSelectedId(2,juce::sendNotificationSync);pump();
   ck(locked&&livePreset&&livePreset->getSelectedId()==7&&visibleRatio(live,{5,7}),"ratio controls are locked after Start and cannot mutate the active 5:7 scheduler plan");
   while(expected.quiescentView().cursor.state!=scheduler::State::Running)advance();
   auto facts=expected.quiescentView();ck(facts.cursor.completedCycles==0&&matchesCursor(),"count-in boundary enters the first 5:7 shared cycle and visible playhead follows its scheduler cursor");
   while(expected.quiescentView().cursor.completedCycles<1)advance();facts=expected.quiescentView();
   ck(facts.cursor.completedCycles==1&&matchesCursor(),"the selected 5:7 event pattern repeats across the first common-cycle boundary without a second cursor");
   while(expected.quiescentView().tempoIndex<1)advance();facts=expected.quiescentView();
   ck(facts.cursor.completedCycles==2&&facts.tempoIndex==1&&matchesCursor()&&oracleBlocks>1000,"selected 5:7 relation and visible playhead persist through the scheduled 126 BPM variant on the same callback oracle");
   ck(nativeOpens==0&&A::practice(*h.home).captureSession()&&!A::practice(*h.home).captureSession()->startTaken(),"live ratio walkthrough uses synthetic output only and creates no Practice Attempt");
   click(live,"Stop");h.blocks(1);h.wait([&]{return button(live,"Finish check").isEnabled();},"Rhythm stop outcome");click(live,"Finish check");h.blocks(1);
   ck(live.audioSnapshot().state==output::State::Closed&&nativeOpens==0&&h.finals()==0,"selected-ratio synthetic outcome resolves without native output or finalized Practice history");
  }
  if(std::string(argv[2])=="--rhythm-playhead-cycle"){
   Harness h(dir,"live-rhythm-playhead");h.setup();click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Practice Back to Home");
   click(*h.home,"Rhythm preview");auto& live=A::rhythm(*h.home);click(live,"Audio settings");h.tick();click(A::settings(*h.home),"Connect audio");h.tick();click(A::settings(*h.home),"Enable audio");h.blocks(1);click(A::settings(*h.home),"Back to Rhythm preview");h.tick();
   ck(live.audioSnapshot().state==output::State::Ready&&nativeOpens==0,"synthetic Rhythm output is Ready before explicit Start without opening or starting a native device");
   scheduler::Owner expectedOwner{};expectedOwner.id[6]=0x40;expectedOwner.id[8]=0x80;expectedOwner.generation=1;expectedOwner.epoch=1;
   scheduler::ScheduledStream expected;expected.prepare(desktop::previewPlans(expectedOwner,44100),4,2,1);
   const auto discard=[](void*,std::uint64_t,std::uint32_t,const scheduler::Fact*,std::size_t) noexcept{return true;};
   int oracleBlocks{},callbackBlocks{};auto advance=[&]{if(++callbackBlocks>1600)throw std::runtime_error("playhead walkthrough callback watchdog");auto& output=A::output(*h.home);platform::OutputTestAccess::block(output);h.tick();const auto state=output.status().lifecycle.state;if(state==output::State::Running){const auto outcome=expected.process(expectedOwner,44100,256,discard,nullptr);if(!outcome.valid)throw std::runtime_error("playhead oracle failed to process the synthetic callback");scheduler::Fact fact;while(expected.nextFact(fact)){}scheduler::StreamView copied;while(expected.nextView(copied)){}++oracleBlocks;}};
   const auto renderedXs=[&]{juce::Image frame(juce::Image::RGB,live.getWidth(),live.getHeight(),true);juce::Graphics graphics(frame);live.paint(graphics);std::vector<int> xs;for(int x=190;x<live.getWidth()-24;++x){const auto pixel=frame.getPixelAt(x,410);if(pixel.getRed()>220&&pixel.getGreen()>230&&pixel.getBlue()>230)xs.push_back(x);}return xs;};
   const auto cursorX=[&]{const auto facts=expected.quiescentView();const long double span=static_cast<long double>(facts.phaseSpan.n)/facts.phaseSpan.d;const auto elapsed=facts.cursor.processedThrough>=facts.phaseOrigin?facts.cursor.processedThrough-facts.phaseOrigin:0;const auto phase=span>0?std::clamp(static_cast<double>(static_cast<long double>(elapsed)/span),0.0,1.0):0.0;return 190+static_cast<int>((live.getWidth()-24-190)*phase);};
   const auto matchesCursor=[&]{const auto xs=renderedXs();if(xs.empty())return false;const int observed=(xs.front()+xs.back())/2;return std::abs(observed-cursorX())<=2;};
   click(live,"Start preview");
   advance();while(expected.quiescentView().cursor.processedThrough<44100)advance();
   auto facts=expected.quiescentView();ck(facts.cursor.state==scheduler::State::CountIn&&facts.cursor.completedCycles==0&&facts.phaseSpan.n>0&&oracleBlocks>100,"current scheduler oracle is halfway through the intro count-in before the first running cycle");
   ck(matchesCursor()&&cursorX()>190+(live.getWidth()-24-190)/4,"rendered playhead advances during count-in according to the current scheduler phase");
   while(expected.quiescentView().cursor.state!=scheduler::State::Running)advance();facts=expected.quiescentView();
   ck(facts.cursor.completedCycles==0&&facts.phaseOrigin==88200&&facts.tempoIndex==0&&matchesCursor(),"CountInEnded resets the visible playhead to the first shared cycle using the scheduler boundary fact");
   while(expected.quiescentView().cursor.completedCycles<1)advance();facts=expected.quiescentView();
   ck(facts.cursor.completedCycles==1&&facts.phaseOrigin==176400&&facts.tempoIndex==0&&matchesCursor(),"first cycle boundary resets the visible playhead from the shared scheduler cursor");
   while(expected.quiescentView().tempoIndex<1)advance();facts=expected.quiescentView();std::string progressText;for(auto* child:live.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText().toStdString().find("126 BPM")!=std::string::npos)progressText=label->getText().toStdString();
   ck(facts.cursor.completedCycles==2&&facts.tempoIndex==1&&progressText.find("126 BPM")!=std::string::npos&&matchesCursor(),"second cycle boundary selects and visibly identifies the scheduled 126 BPM variant");
   const long double variantSpan=static_cast<long double>(facts.phaseSpan.n)/facts.phaseSpan.d;while(static_cast<long double>(expected.quiescentView().cursor.processedThrough-expected.quiescentView().phaseOrigin)<variantSpan/2)advance();facts=expected.quiescentView();
   ck(facts.cursor.state==scheduler::State::Running&&facts.tempoIndex==1&&matchesCursor()&&cursorX()>190+(live.getWidth()-24-190)/3,"playhead advances within the accepted tempo variant using its updated scheduler phase span");
   ck(nativeOpens==0&&A::practice(*h.home).captureSession()&&!A::practice(*h.home).captureSession()->startTaken(),"playhead walkthrough remains synthetic with no native device or Practice Attempt start");
   click(live,"Stop");h.blocks(1);h.wait([&]{return button(live,"Finish check").isEnabled();},"Rhythm stop outcome");click(live,"Finish check");h.blocks(1);
   ck(live.audioSnapshot().state==output::State::Closed&&nativeOpens==0&&h.finals()==0,"synthetic outcome releases cleanly without native sound or finalized Practice history");
  }
  if(rhythmLayerControlsOnly){
   Harness h(dir,"live-rhythm-layer-controls");h.setup();click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Practice Back to Home");
   click(*h.home,"Rhythm preview");auto& live=A::rhythm(*h.home);h.tick();
   auto baseline=h.home->audioSettings().selected();baseline.master=100;baseline.masterMute=false;baseline.bus={0,0,100,100};baseline.muteMask=3;baseline.soloAB=0;
   ck(h.home->audioSettings().selectMix(baseline),"shared test mix isolates audible A/B layers and mutes Reference/Metronome without changing the scheduler");
   click(live,"Audio settings");h.tick();auto& settings=A::settings(*h.home);click(settings,"Connect audio");h.tick();click(settings,"Enable audio");h.blocks(1);
   ck(live.audioSnapshot().state==output::State::Ready&&equal(A::output(*h.home).status().mix,baseline)&&nativeOpens==0,"synthetic Rhythm output is Ready with the isolated common mix and no native open/start");
   auto clickId=[&](const std::string& id){auto* b=dynamic_cast<juce::Button*>(settings.findChildWithID(id));if(!b||!b->isVisible()||!b->isEnabled()||!settings.getLocalBounds().contains(b->getBounds()))throw std::runtime_error("Layer control is not usable: "+id);activate(*b);};
   clickId("audio-rhythm-a-mute");auto selected=h.home->audioSettings().selected();selected.muteMask=static_cast<std::uint8_t>(selected.muteMask|4U);
   ck(h.home->audioSettings().selected().muteMask==7&&h.home->audioSettings().selected().soloAB==0,"actual Layer A mute control changes only A while B remains enabled");
   h.blocks(1);ck(equal(A::output(*h.home).status().mix,selected),"A mute reaches the active Rhythm output mix before Start");
   click(settings,"Back to Rhythm preview");h.tick();
   scheduler::Owner expectedOwner{};expectedOwner.id[6]=0x40;expectedOwner.id[8]=0x80;expectedOwner.generation=1;expectedOwner.epoch=1;
   scheduler::ScheduledStream expected;expected.prepare(desktop::previewPlans(expectedOwner,44100),4,2,1);
   const auto discard=[](void*,std::uint64_t,std::uint32_t,const scheduler::Fact*,std::size_t) noexcept{return true;};
   int callbackBlocks{},oracleBlocks{};auto advance=[&]{if(++callbackBlocks>1800)throw std::runtime_error("layer control walkthrough callback watchdog");auto& output=A::output(*h.home);const float peak=platform::OutputTestAccess::block(output);h.tick();if(output.status().lifecycle.state==output::State::Running){const auto outcome=expected.process(expectedOwner,44100,256,discard,nullptr);if(!outcome.valid)throw std::runtime_error("layer control oracle failed to process the synthetic callback");scheduler::Fact fact;while(expected.nextFact(fact)){}scheduler::StreamView copied;while(expected.nextView(copied)){}++oracleBlocks;}return peak;};
   const auto renderedXs=[&]{juce::Image frame(juce::Image::RGB,live.getWidth(),live.getHeight(),true);juce::Graphics graphics(frame);live.paint(graphics);std::vector<int> xs;for(int x=190;x<live.getWidth()-24;++x){const auto pixel=frame.getPixelAt(x,410);if(pixel.getRed()>220&&pixel.getGreen()>230&&pixel.getBlue()>230)xs.push_back(x);}return xs;};
   const auto cursorX=[&]{const auto facts=expected.quiescentView();const long double span=static_cast<long double>(facts.phaseSpan.n)/facts.phaseSpan.d;const auto elapsed=facts.cursor.processedThrough>=facts.phaseOrigin?facts.cursor.processedThrough-facts.phaseOrigin:0;const auto phase=span>0?std::clamp(static_cast<double>(static_cast<long double>(elapsed)/span),0.0,1.0):0.0;return 190+static_cast<int>((live.getWidth()-24-190)*phase);};
   const auto matchesCursor=[&]{const auto xs=renderedXs();if(xs.empty())return false;return std::abs((xs.front()+xs.back())/2-cursorX())<=2;};
   const auto peakAt=[&](std::uint64_t frame){float peak{};while(expected.quiescentView().cursor.processedThrough<frame){const auto callbackPeak=advance();if(expected.quiescentView().cursor.processedThrough>=frame)peak=callbackPeak;}for(int i=0;i<6;++i)peak=std::max(peak,advance());return peak;};
   click(live,"Start preview");advance();
   ck(live.audioSnapshot().state==output::State::Running&&expected.quiescentView().cursor.state==scheduler::State::CountIn&&nativeOpens==0,"explicit Start begins one software scheduler stream with native output still closed");
   auto requireRouting=[&](std::uint64_t frame,bool audible,const std::string& label){const float peak=peakAt(frame);ck(audible?peak>0.01f:peak==0.0f,label+" (peak="+std::to_string(peak)+")");};
   requireRouting(117600,false,"A-only phase is silent while actual Layer A mute is on");
   requireRouting(132300,true,"B-only phase remains audible while Layer A alone is muted");
   auto toggle=[&](const std::string& id,std::uint8_t expectedMute,std::uint8_t expectedSolo,const std::string& label){
    const auto before=expected.quiescentView();click(live,"Audio settings");h.tick();clickId(id);
    const auto selectedNow=h.home->audioSettings().selected();ck(selectedNow.muteMask==expectedMute&&selectedNow.soloAB==expectedSolo,label+" updates only the selected A/B control in shared settings");
    const auto peak=advance();(void)peak;const auto outputMix=A::output(*h.home).status().mix;const auto after=expected.quiescentView();
    ck(outputMix.muteMask==expectedMute&&outputMix.soloAB==expectedSolo,label+" is applied to the active output callback");
    ck(after.cursor.processedThrough==before.cursor.processedThrough+256&&after.cursor.completedCycles==before.cursor.completedCycles&&after.phaseOrigin==before.phaseOrigin&&after.tempoIndex==before.tempoIndex,label+" advances exactly one shared callback without resetting cycle/tempo phase");
    click(settings,"Back to Rhythm preview");h.tick();ck(matchesCursor(),label+" leaves the visible shared playhead aligned with the same scheduler cursor");
   };
   toggle("audio-rhythm-a-mute",3,0,"Layer A unmute");toggle("audio-rhythm-b-mute",11,0,"Layer B mute");
   requireRouting(205800,true,"A-only phase remains audible while actual Layer B mute is on");
   requireRouting(220500,false,"B-only phase is silent while actual Layer B mute is on");
   toggle("audio-rhythm-b-mute",3,0,"Layer B unmute");toggle("audio-rhythm-a-solo",3,1,"Layer A solo");
   requireRouting(292600,true,"A-only phase remains audible under actual Layer A solo at scheduled 126 BPM");
   requireRouting(306600,false,"B-only phase is silent under actual Layer A solo at scheduled 126 BPM");
   toggle("audio-rhythm-a-solo",3,0,"Layer A unsolo");toggle("audio-rhythm-b-solo",3,2,"Layer B solo");
   requireRouting(376600,false,"A-only phase is silent under actual Layer B solo");
   requireRouting(390600,true,"B-only phase remains audible under actual Layer B solo");
   const auto finalFacts=expected.quiescentView();ck(finalFacts.cursor.completedCycles==3&&finalFacts.tempoIndex==1&&oracleBlocks>1400&&callbackBlocks==oracleBlocks,"one shared stream crossed count-in, three cycle boundaries and its scheduled tempo change through one callback path");
   ck(nativeOpens==0&&A::practice(*h.home).captureSession()&&!A::practice(*h.home).captureSession()->startTaken(),"layer control walk remained synthetic and created no Practice Attempt");
   click(live,"Stop");h.blocks(1);h.wait([&]{return button(live,"Finish check").isEnabled();},"Rhythm stop outcome");click(live,"Finish check");h.blocks(1);
   ck(live.audioSnapshot().state==output::State::Closed&&nativeOpens==0&&h.finals()==0,"synthetic result releases with no native output or finalized Practice history");
  }
  if(rhythmRatioLayerRoutingOnly){
   struct Hit{std::uint64_t cycle{},frame{};scheduler::Role role{};float callbackPeak{};};
   Harness h(dir,"live-rhythm-ratio-layer-routing");h.setup();click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Practice Back to Home");
   click(*h.home,"Rhythm preview");auto& live=A::rhythm(*h.home);
   auto* livePreset=dynamic_cast<juce::ComboBox*>(live.findChildWithID("rhythm-ratio-preset"));ck(livePreset&&livePreset->isEnabled(),"live Rhythm exposes its pre-start X:Y preset control");
   if(livePreset){livePreset->setSelectedId(7,juce::sendNotificationSync);pump();}
   auto* sharedCycle=dynamic_cast<juce::Label*>(live.findChildWithID("rhythm-shared-cycle"));
   ck(livePreset&&livePreset->getSelectedId()==7&&sharedCycle&&sharedCycle->getText().toStdString().find("5:7")!=std::string::npos,"the actual live preview selects the accepted 5:7 shared-cycle preset");
   auto baseline=h.home->audioSettings().selected();baseline.master=100;baseline.masterMute=false;baseline.bus={0,0,100,100};baseline.muteMask=3;baseline.soloAB=0;
   ck(h.home->audioSettings().selectMix(baseline),"shared Audio baseline keeps A/B audible and isolates Reference/Metronome before the run");
   click(live,"Audio settings");h.tick();auto& settings=A::settings(*h.home);
   click(settings,"Connect audio");h.tick();click(settings,"Enable audio");h.blocks(1);
   auto clickId=[&](const std::string& id){auto* b=dynamic_cast<juce::Button*>(settings.findChildWithID(id));if(!b||!b->isVisible()||!b->isEnabled()||!settings.getLocalBounds().contains(b->getBounds()))throw std::runtime_error("Layer routing control is not usable: "+id);activate(*b);};
   const auto beforeInitialMute=h.home->audioSettings().selected();clickId("audio-rhythm-a-mute");auto initiallyMuted=beforeInitialMute;initiallyMuted.muteMask=static_cast<std::uint8_t>(initiallyMuted.muteMask^4U);
   ck(equal(h.home->audioSettings().selected(),initiallyMuted),"actual Layer A mute changes only its shared Audio mute bit before Start");h.blocks(1);
   ck(equal(A::output(*h.home).status().mix,initiallyMuted)&&live.audioSnapshot().state==output::State::Ready&&nativeOpens==0,"synthetic output applies the initial A-only mute while Ready without opening native output");
   click(settings,"Back to Rhythm preview");h.tick();
   scheduler::Owner owner{};owner.id[6]=0x40;owner.id[8]=0x80;owner.generation=1;owner.epoch=live.audioSnapshot().request.epoch;
   scheduler::ScheduledStream expected;expected.prepare(desktop::previewPlans(owner,44100,{5,7}),4,2,1);
   const auto discard=[](void*,std::uint64_t,std::uint32_t,const scheduler::Fact*,std::size_t) noexcept{return true;};
   int callbackBlocks{},oracleBlocks{};float callbackPeak{};std::vector<Hit> hits;
   auto advance=[&]{if(++callbackBlocks>1900)throw std::runtime_error("5:7 layer-routing callback watchdog");auto& output=A::output(*h.home);callbackPeak=platform::OutputTestAccess::block(output);h.tick();if(output.status().lifecycle.state==output::State::Running){const auto result=expected.process(owner,44100,256,discard,nullptr);if(!result.valid)throw std::runtime_error("5:7 shared scheduler oracle rejected a synthetic callback");scheduler::Fact fact;while(expected.nextFact(fact))if(fact.kind==scheduler::FactKind::Event&&fact.action==scheduler::Action::Attack&&(fact.role==scheduler::Role::LayerA||fact.role==scheduler::Role::LayerB))hits.push_back({fact.cycle,fact.frame,fact.role,callbackPeak});scheduler::StreamView copied;while(expected.nextView(copied)){}++oracleBlocks;}return callbackPeak;};
   auto uniqueHit=[&](scheduler::Role role,std::uint64_t cycle,std::size_t fresh){for(;;){for(std::size_t i=fresh;i<hits.size();++i){const auto& candidate=hits[i];if(candidate.cycle!=cycle||candidate.role!=role)continue;const bool peerAtSameFrame=std::any_of(hits.begin(),hits.end(),[&](const Hit& other){return other.frame==candidate.frame&&other.role!=candidate.role;});if(!peerAtSameFrame)return candidate;}if(expected.quiescentView().cursor.completedCycles>cycle+1)throw std::runtime_error("5:7 scheduler passed the requested common-cycle event");advance();}};
   auto peakWindow=[&](const Hit& hit){float peak=hit.callbackPeak;for(int i=0;i<6;++i)peak=std::max(peak,advance());return peak;};
   std::ofstream routingLog(h.dir/"ratio-layer-routing.tsv");routingLog<<"cycle\trole\tframe\tpeak_after_shared_mixer\tstate\n";
   auto requireHit=[&](scheduler::Role role,std::uint64_t cycle,std::size_t fresh,bool audible,const std::string& label){const auto hit=uniqueHit(role,cycle,fresh);const float peak=peakWindow(hit);routingLog<<cycle<<'\t'<<(role==scheduler::Role::LayerA?"A":"B")<<'\t'<<hit.frame<<'\t'<<std::setprecision(9)<<peak<<'\t'<<(audible?"audible":"silent")<<'\n';routingLog.flush();const bool okay=audible?peak>0.01f:peak==0.0f;ck(okay,label+" (peak="+std::to_string(peak)+")");return hits.size();};
   const auto cursorX=[&]{const auto facts=expected.quiescentView();const long double span=static_cast<long double>(facts.phaseSpan.n)/facts.phaseSpan.d;const auto elapsed=facts.cursor.processedThrough>=facts.phaseOrigin?facts.cursor.processedThrough-facts.phaseOrigin:0;const double phase=span>0?std::clamp(static_cast<double>(static_cast<long double>(elapsed)/span),0.0,1.0):0.0;return 190+static_cast<int>((live.getWidth()-24-190)*phase);};
   const auto matchesCursor=[&]{juce::Image frame(juce::Image::RGB,live.getWidth(),live.getHeight(),true);juce::Graphics graphics(frame);live.paint(graphics);std::vector<int> xs;for(int x=190;x<live.getWidth()-24;++x){const auto pixel=frame.getPixelAt(x,410);if(pixel.getRed()>220&&pixel.getGreen()>230&&pixel.getBlue()>230)xs.push_back(x);}return !xs.empty()&&std::abs((xs.front()+xs.back())/2-cursorX())<=2;};
   auto toggle=[&](const std::string& id,std::uint8_t bit,bool solo,const std::string& label){const auto before=expected.quiescentView();const auto selectedBefore=h.home->audioSettings().selected();auto desired=selectedBefore;if(solo)desired.soloAB=static_cast<std::uint8_t>(desired.soloAB^bit);else desired.muteMask=static_cast<std::uint8_t>(desired.muteMask^bit);click(live,"Audio settings");h.tick();clickId(id);const auto selectedAfter=h.home->audioSettings().selected();ck(equal(selectedAfter,desired),label+" changes exactly its intended shared Audio control bit");advance();const auto applied=A::output(*h.home).status().mix;const auto after=expected.quiescentView();ck(equal(applied,desired),label+" is applied to the active post-mixer snapshot on its next callback");ck(after.cursor.processedThrough==before.cursor.processedThrough+256&&after.cursor.completedCycles==before.cursor.completedCycles&&after.phaseOrigin==before.phaseOrigin&&after.tempoIndex==before.tempoIndex,label+" advances one 256-frame callback without resetting the single shared cursor, cycle or tempo");click(settings,"Back to Rhythm preview");h.tick();ck(matchesCursor(),label+" leaves the visible playhead aligned to that same scheduler cursor");};
   click(live,"Start preview");advance();
   ck(live.audioSnapshot().state==output::State::Running&&expected.quiescentView().cursor.state==scheduler::State::CountIn&&nativeOpens==0,"explicit Start begins one synthetic 5:7 scheduler count-in with native output closed");
   std::size_t fresh=hits.size();fresh=requireHit(scheduler::Role::LayerB,0,fresh,true,"Layer B attack routes audibly under actual Layer A mute in common cycle 0");fresh=requireHit(scheduler::Role::LayerA,0,fresh,false,"Layer A attack is exactly silent under its actual mute in common cycle 0");
   toggle("audio-rhythm-a-mute",4,false,"Layer A unmute");fresh=hits.size();fresh=requireHit(scheduler::Role::LayerA,0,fresh,true,"Layer A attack becomes audible after its actual unmute in common cycle 0");fresh=requireHit(scheduler::Role::LayerB,0,fresh,true,"Layer B remains independently audible after Layer A unmute in common cycle 0");
   toggle("audio-rhythm-b-mute",8,false,"Layer B mute");fresh=hits.size();fresh=requireHit(scheduler::Role::LayerB,0,fresh,false,"Layer B attack becomes exactly silent under its actual mute in common cycle 0");fresh=requireHit(scheduler::Role::LayerA,0,fresh,true,"Layer A remains audible while Layer B is muted in common cycle 0");
   toggle("audio-rhythm-b-mute",8,false,"Layer B unmute");toggle("audio-rhythm-a-solo",1,true,"Layer A solo");
   fresh=hits.size();fresh=requireHit(scheduler::Role::LayerA,1,fresh,true,"Layer A remains audible under actual Layer A solo in common cycle 1");fresh=requireHit(scheduler::Role::LayerB,1,fresh,false,"Layer B is exactly silent under actual Layer A solo in common cycle 1");
   const auto cycle1=expected.quiescentView();const long double cycle1Span=static_cast<long double>(cycle1.phaseSpan.n)/cycle1.phaseSpan.d;
   ck(cycle1.cursor.completedCycles==1&&cycle1.tempoIndex==0&&std::abs(static_cast<double>(cycle1Span)-88200.0)<0.5,"the first full 5:7 common cycle uses its 120 BPM scheduler span");
   toggle("audio-rhythm-a-solo",1,true,"Layer A unsolo");toggle("audio-rhythm-b-solo",2,true,"Layer B solo");
   fresh=hits.size();fresh=requireHit(scheduler::Role::LayerA,1,fresh,false,"Layer A is exactly silent under actual Layer B solo in common cycle 1");fresh=requireHit(scheduler::Role::LayerB,1,fresh,true,"Layer B remains audible under actual Layer B solo in common cycle 1");
   while(expected.quiescentView().cursor.completedCycles<2)advance();const auto cycle2Start=expected.quiescentView();const long double cycle2Span=static_cast<long double>(cycle2Start.phaseSpan.n)/cycle2Start.phaseSpan.d;
   ck(cycle2Start.cursor.completedCycles==2&&cycle2Start.tempoIndex==1&&std::abs(static_cast<double>(cycle2Span)-84000.0)<0.5,"the next common cycle applies the accepted 126 BPM scheduler variant without replacing the cursor");
   fresh=hits.size();fresh=requireHit(scheduler::Role::LayerA,2,fresh,false,"Layer A remains exactly silent under actual Layer B solo in the 126 BPM common cycle 2");fresh=requireHit(scheduler::Role::LayerB,2,fresh,true,"Layer B remains audible under actual Layer B solo in the 126 BPM common cycle 2");
   while(expected.quiescentView().cursor.completedCycles<3)advance();const auto finalFacts=expected.quiescentView();
   const auto attacksIn=[&](std::uint64_t cycle,scheduler::Role role){return static_cast<int>(std::count_if(hits.begin(),hits.end(),[&](const Hit& hit){return hit.cycle==cycle&&hit.role==role;}));};
   for(const auto cycle:{1U,2U}){const int a=attacksIn(cycle,scheduler::Role::LayerA),b=attacksIn(cycle,scheduler::Role::LayerB);routingLog<<"cycle-count\t"<<cycle<<"\tA="<<a<<"\tB="<<b<<"\n";routingLog.flush();ck(a==5&&b==7,"scheduler reports exactly five Layer A and seven Layer B attacks in complete 5:7 common cycle "+std::to_string(cycle));}
   ck(finalFacts.cursor.completedCycles==3&&finalFacts.tempoIndex==1&&oracleBlocks>1200&&callbackBlocks==oracleBlocks,"one scheduler cursor completed two measured 5:7 cycles and their tempo transition through the same synthetic callback path");
   ck(nativeOpens==0&&A::practice(*h.home).captureSession()&&!A::practice(*h.home).captureSession()->startTaken(),"5:7 live routing trace uses no native output and creates no Practice Attempt");
   click(live,"Stop");h.blocks(1);h.wait([&]{return button(live,"Finish check").isEnabled();},"Rhythm stop outcome");click(live,"Finish check");h.blocks(1);
   ck(live.audioSnapshot().state==output::State::Closed&&nativeOpens==0&&h.finals()==0,"synthetic 5:7 result resolves closed without native output or finalized Practice history");
  }
  if(rhythmLayerVolumesOnly){
   Harness h(dir,"live-rhythm-layer-volumes");h.setup();click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Practice Back to Home");
   click(*h.home,"Rhythm preview");auto& live=A::rhythm(*h.home);h.tick();
   auto setupMix=h.home->audioSettings().selected();setupMix.master=100;setupMix.masterMute=false;setupMix.muteMask=3;setupMix.soloAB=0;
   ck(h.home->audioSettings().selectMix(setupMix),"shared test mix sets master and isolates only Reference/Metronome before the synthetic Rhythm run");
   click(live,"Audio settings");h.tick();auto& settings=A::settings(*h.home);
   auto* gainA=dynamic_cast<juce::Slider*>(settings.findChildWithID("audio-rhythm-a-volume"));auto* gainB=dynamic_cast<juce::Slider*>(settings.findChildWithID("audio-rhythm-b-volume"));
   ck(gainA&&gainB&&gainA->isVisible()&&gainB->isVisible()&&gainA->getMinimum()==0.0&&gainA->getMaximum()==100.0&&gainB->getMinimum()==0.0&&gainB->getMaximum()==100.0,"existing shared Audio A/B volume sliders expose the current 0–100 controls");
   const auto initialPeerA=h.home->audioSettings().selected().bus[2];const auto initialPeerB=h.home->audioSettings().selected().bus[3];
   if(gainA){gainA->setValue(25,juce::sendNotificationSync);h.tick();}
   const auto afterAChoice=h.home->audioSettings().selected();
   ck(afterAChoice.bus[2]==25&&afterAChoice.bus[3]==initialPeerB&&initialPeerA!=afterAChoice.bus[2],"actual Layer A slider changes A while retaining the selected Layer B gain");
   if(gainB){gainB->setValue(50,juce::sendNotificationSync);h.tick();}
   const auto initialMix=h.home->audioSettings().selected();
   ck(initialMix.bus[2]==25&&initialMix.bus[3]==50&&initialMix.bus[2]==afterAChoice.bus[2],"actual Layer B slider changes B while retaining the selected Layer A gain");
   click(settings,"Connect audio");h.tick();click(settings,"Enable audio");h.blocks(1);
   ck(live.audioSnapshot().state==output::State::Ready&&equal(A::output(*h.home).status().mix,initialMix)&&nativeOpens==0,"synthetic Rhythm output applies the independently selected 25/50 bus gains with native output closed");
   click(settings,"Back to Rhythm preview");h.tick();
   scheduler::Owner expectedOwner{};expectedOwner.id[6]=0x40;expectedOwner.id[8]=0x80;expectedOwner.generation=1;expectedOwner.epoch=live.audioSnapshot().request.epoch;
   scheduler::ScheduledStream expected;expected.prepare(desktop::previewPlans(expectedOwner,44100),4,2,1);
   const auto discard=[](void*,std::uint64_t,std::uint32_t,const scheduler::Fact*,std::size_t) noexcept{return true;};
   std::vector<std::pair<scheduler::Role,std::uint64_t>> attacks;int callbackBlocks{},oracleBlocks{};float lastCallbackPeak{};
   auto advance=[&]{if(++callbackBlocks>1500)throw std::runtime_error("layer volume walkthrough callback watchdog");auto& output=A::output(*h.home);lastCallbackPeak=platform::OutputTestAccess::block(output);h.tick();if(output.status().lifecycle.state==output::State::Running){const auto outcome=expected.process(expectedOwner,44100,256,discard,nullptr);if(!outcome.valid)throw std::runtime_error("layer volume oracle failed to process the synthetic callback");scheduler::Fact fact;while(expected.nextFact(fact)){if(fact.kind==scheduler::FactKind::Event&&fact.action==scheduler::Action::Attack&&(fact.role==scheduler::Role::LayerA||fact.role==scheduler::Role::LayerB))attacks.emplace_back(fact.role,fact.frame);}scheduler::StreamView copied;while(expected.nextView(copied)){}++oracleBlocks;}return lastCallbackPeak;};
   auto occurrenceCount=[&](scheduler::Role role){return static_cast<std::size_t>(std::count_if(attacks.begin(),attacks.end(),[&](const auto& event){return event.first==role;}));};
   auto hitFrame=[&](scheduler::Role role,std::size_t occurrence){while(occurrenceCount(role)<=occurrence)advance();std::size_t seen{};for(const auto& event:attacks)if(event.first==role){if(seen++==occurrence)return event.second;}throw std::runtime_error("scheduler attack fact disappeared");};
   std::ofstream peakLog(h.dir/"layer-volume-peaks.tsv");peakLog<<"role\toccurrence\tframe\tpeak_after_mixer\n";
   auto measureHit=[&](scheduler::Role role,std::size_t occurrence){const auto frame=hitFrame(role,occurrence);float peak=lastCallbackPeak;for(int i=0;i<6;++i)peak=std::max(peak,advance());peakLog<<(role==scheduler::Role::LayerA?"A":"B")<<'\t'<<occurrence<<'\t'<<frame<<'\t'<<std::setprecision(9)<<peak<<'\n';peakLog.flush();return std::pair{frame,peak};};
   const auto renderedXs=[&]{juce::Image frame(juce::Image::RGB,live.getWidth(),live.getHeight(),true);juce::Graphics graphics(frame);live.paint(graphics);std::vector<int> xs;for(int x=190;x<live.getWidth()-24;++x){const auto pixel=frame.getPixelAt(x,410);if(pixel.getRed()>220&&pixel.getGreen()>230&&pixel.getBlue()>230)xs.push_back(x);}return xs;};
   const auto cursorX=[&]{const auto facts=expected.quiescentView();const long double span=static_cast<long double>(facts.phaseSpan.n)/facts.phaseSpan.d;const auto elapsed=facts.cursor.processedThrough>=facts.phaseOrigin?facts.cursor.processedThrough-facts.phaseOrigin:0;const double phase=span>0?std::clamp(static_cast<double>(static_cast<long double>(elapsed)/span),0.0,1.0):0.0;return 190+static_cast<int>((live.getWidth()-24-190)*phase);};
   const auto matchesCursor=[&]{const auto xs=renderedXs();return !xs.empty()&&std::abs((xs.front()+xs.back())/2-cursorX())<=2;};
   click(live,"Start preview");advance();
   ck(live.audioSnapshot().state==output::State::Running&&expected.quiescentView().cursor.state==scheduler::State::CountIn&&nativeOpens==0,"explicit Start uses one synthetic scheduler stream with native output closed");
   const auto a25=measureHit(scheduler::Role::LayerA,1);const auto b50=measureHit(scheduler::Role::LayerB,1);
   ck(a25.first==117600&&b50.first==132300,"scheduler attack facts derive the isolated first-cycle A and B measurement frames");
   while(expected.quiescentView().cursor.processedThrough<150000)advance();
   auto changeGain=[&](const std::string& id,int value,int ownBus,int peerBus,int expectedPeer,std::uint64_t expectedCycle,const std::string& label){
    const auto before=expected.quiescentView();ck(before.cursor.state==scheduler::State::Running&&before.cursor.processedThrough<before.phaseOrigin+before.phaseSpan.n/before.phaseSpan.d&&before.cursor.completedCycles==expectedCycle,label+" begins inside its current shared cycle");
    click(live,"Audio settings");h.tick();auto* slider=dynamic_cast<juce::Slider*>(settings.findChildWithID(id));
    ck(slider&&slider->isEnabled(),label+" adjusts the existing Shared Audio slider during playback");
    if(slider)slider->setValue(value,juce::sendNotificationSync);h.tick();
    const auto selected=h.home->audioSettings().selected();ck(selected.bus[static_cast<std::size_t>(ownBus)]==value&&selected.bus[static_cast<std::size_t>(peerBus)]==expectedPeer,label+" updates only its selected bus gain");
    advance();const auto after=expected.quiescentView();const auto applied=A::output(*h.home).status().mix;
    ck(equal(applied,selected),label+" reaches the active post-mixer settings snapshot on the next callback");
    ck(after.cursor.processedThrough==before.cursor.processedThrough+256&&after.cursor.completedCycles==before.cursor.completedCycles&&after.phaseOrigin==before.phaseOrigin&&after.tempoIndex==before.tempoIndex,label+" advances exactly one 256-frame callback without resetting shared phase, cycle or tempo");
    click(settings,"Back to Rhythm preview");h.tick();ck(matchesCursor(),label+" preserves the rendered playhead-to-oracle position");
   };
   auto midA=expected.quiescentView();ck(midA.phaseOrigin==88200&&midA.cursor.completedCycles==0&&midA.tempoIndex==0,"first gain change is scheduled after count-in and before the first cycle boundary");
   changeGain("audio-rhythm-a-volume",50,2,3,50,0,"Layer A 25-to-50 volume change");
   const auto a50=measureHit(scheduler::Role::LayerA,4);const auto b50AfterA=measureHit(scheduler::Role::LayerB,3);const auto a50BeforeB=measureHit(scheduler::Role::LayerA,5);
   ck(a50.first==205800&&b50AfterA.first==220500&&a50BeforeB.first==235200,"next same-phase scheduler facts confirm A/B post-change and pre-B-change measurements");
   auto midB=expected.quiescentView();while(midB.cursor.processedThrough<245000){advance();midB=expected.quiescentView();}
   ck(midB.phaseOrigin==176400&&midB.cursor.completedCycles==1&&midB.tempoIndex==0&&midB.cursor.processedThrough<264600,"second gain change remains inside the following 120 BPM cycle before its boundary");
   changeGain("audio-rhythm-b-volume",25,3,2,50,1,"Layer B 50-to-25 volume change");
   const auto a50AfterB=measureHit(scheduler::Role::LayerA,7);const auto b25=measureHit(scheduler::Role::LayerB,5);
   ck(a50AfterB.first==292600&&b25.first==306600,"126 BPM scheduler facts provide matching post-change A/B attack windows");
   const auto near=[](float actual,float target){return std::abs(actual-target)<=std::abs(target)*0.001f+1.0e-7f;};
   ck(a25.second>0.0f&&near(a50.second,2.0f*a25.second),"Layer A 25-to-50 shared Audio slider doubles its synthesized post-mixer event peak");
   ck(b50.second>0.0f&&near(b50AfterA.second,b50.second),"Layer A volume change leaves the Layer B synthesized event peak unchanged");
   ck(near(a50AfterB.second,a50.second),"Layer B volume change leaves the Layer A synthesized event peak unchanged");
   ck(near(b25.second,0.5f*b50.second),"Layer B 50-to-25 shared Audio slider halves its synthesized post-mixer event peak");
   const auto finalFacts=expected.quiescentView();ck(finalFacts.cursor.completedCycles>=2&&finalFacts.tempoIndex==1&&oracleBlocks>1100&&callbackBlocks==oracleBlocks,"one scheduler cursor crosses count-in, cycle boundaries and the accepted 126 BPM variant through the same software callback");
   ck(nativeOpens==0&&A::practice(*h.home).captureSession()&&!A::practice(*h.home).captureSession()->startTaken(),"volume walkthrough remains synthetic and starts no Practice Attempt");
   click(live,"Stop");h.blocks(1);h.wait([&]{return button(live,"Finish check").isEnabled();},"Rhythm stop outcome");click(live,"Finish check");h.blocks(1);
   ck(live.audioSnapshot().state==output::State::Closed&&nativeOpens==0&&h.finals()==0,"synthetic Rhythm outcome resolves closed with no native output or finalized Practice history");
  }
  out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<(rhythmRatioLayerRoutingOnly?" Rhythm ratio-layer-routing checks\n":rhythmRatioSelectionOnly?" Rhythm ratio-selection checks\n":rhythmLayerControlsOnly?" Rhythm layer-control checks\n":rhythmLayerVolumesOnly?" Rhythm layer-volume checks\n":" Rhythm shared-cycle checks\n");return 0;
 }
 if(rhythmSurfaceOnly){
  desktop::SchedulerView view;view.setSize(920,680);view.setVisible(true);
  auto* title=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-title"));
  auto* description=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-description"));
  auto* status=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-status"));
  ck(title&&title->isVisible()&&title->getText().toStdString()=="RHYTHM — SYNTHETIC SOUND-CHECK PREVIEW"&&title->getTitle().toStdString()=="Read-only Rhythm preview: synthetic sound-check only; no practice recording or curriculum credit.","Rhythm heading identifies the synthetic sound-check contract");
  const auto descriptionText=description?description->getText().toStdString():std::string{};
  ck(description&&description->isVisible()&&description->getTitle().toStdString()=="Read-only Rhythm preview: shared Audio settings, explicit Start and no practice recording."&&descriptionText.find("These shared settings apply across the other activities;")!=std::string::npos&&descriptionText.find("Start begins sound.")!=std::string::npos&&descriptionText.find("This preview does not record practice.")!=std::string::npos&&descriptionText.find("Back returns Home after the Rhythm preview is safely stopped.")!=std::string::npos,"Rhythm explanation preserves authored guidance and exposes shared-Audio/explicit-Start/safe-Back scope");
  ck(status&&status->isVisible()&&status->getTitle().toStdString()=="Read-only Rhythm preview lifecycle, output state, next action and safe release boundary."&&status->getText().toStdString().find("Output closed")!=std::string::npos,"Rhythm status exposes its lifecycle title and truthful initial closed guidance");
  auto* audio=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-audio-settings"));auto* start=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-start"));auto* stop=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-stop"));auto* tempo=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-tempo"));auto* finish=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-finish"));auto* back=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-back"));
  ck(audio&&start&&stop&&tempo&&finish&&back&&view.getLocalBounds().contains(title->getBounds())&&view.getLocalBounds().contains(description->getBounds())&&view.getLocalBounds().contains(status->getBounds()),"Rhythm primary controls and labels expose stable IDs and remain contained in the detached layout");
  const char* rhythmActionIds[]={"rhythm-audio-settings","rhythm-start","rhythm-stop","rhythm-tempo","rhythm-finish","rhythm-back"};bool rhythmPresentation=true;int rhythmActions=0;for(const auto* id:rhythmActionIds){auto* button=dynamic_cast<juce::TextButton*>(view.findChildWithID(id));rhythmPresentation=rhythmPresentation&&button&&button->findColour(juce::TextButton::buttonColourId)==juce::Colour{0xff6bd5cb}&&button->findColour(juce::TextButton::textColourOffId)==juce::Colour{0xff10212c}&&button->findColour(juce::TextButton::textColourOnId)==juce::Colour{0xff10212c};++rhythmActions;}for(auto* child:view.getChildren())if(auto* button=dynamic_cast<juce::TextButton*>(child))if(button->getButtonText().toStdString()=="Connect audio"||button->getButtonText().toStdString()=="Enable audio"){rhythmPresentation=rhythmPresentation&&button->findColour(juce::TextButton::buttonColourId)==juce::Colour{0xff6bd5cb}&&button->findColour(juce::TextButton::textColourOffId)==juce::Colour{0xff10212c}&&button->findColour(juce::TextButton::textColourOnId)==juce::Colour{0xff10212c};++rhythmActions;}ck(rhythmPresentation&&rhythmActions==8,"Rhythm action buttons use the primary presentation while preserving the existing control contract");
  ck(audio->getTitle().toStdString()=="Open shared Audio settings before starting the Rhythm preview."&&start->getTitle().toStdString()=="Start Rhythm preview synthetic sound; no practice recording is created."&&stop->getTitle().toStdString()=="Stop Rhythm preview and retain the sound-check outcome until Finish check."&&tempo->getTitle().toStdString()=="Change the Rhythm preview tempo for its next cycle."&&finish->getTitle().toStdString()=="Finish the Rhythm preview check and release its retained output safely."&&back->getTitle().toStdString()=="Return Home after the Rhythm preview is safely stopped.","Rhythm primary controls expose truthful non-behavioral action titles");
  const auto snapshot=view.audioSnapshot();ck(snapshot.state==output::State::Closed&&view.audioCanRelease()&&!snapshot.ownsOutcome&&!snapshot.pendingOutcome&&nativeOpens==0&&connections==0,"detached Rhythm surface inspection creates no output owner, pending outcome, native open or connection");
  out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Rhythm surface contract checks\n";return 0;
 }
 if(rhythmResponsiveOnly){
  desktop::SchedulerView view;view.setSize(640,680);view.setVisible(true);view.resized();
  const auto bounds=view.getLocalBounds();
  const char* visibleIds[]={"rhythm-title","rhythm-description","rhythm-status","rhythm-audio-settings","rhythm-start","rhythm-stop","rhythm-finish","rhythm-back"};
  for(const auto* id:visibleIds){auto* component=view.findChildWithID(id);ck(component&&component->isVisible()&&bounds.contains(component->getBounds())&&component->getWidth()>0&&component->getHeight()>0,std::string("Compact Rhythm surface remains visible and contained: ")+id);}
  const auto* tempoLayout=view.findChildWithID("rhythm-tempo");ck(tempoLayout&&bounds.contains(tempoLayout->getBounds())&&tempoLayout->getWidth()>0&&tempoLayout->getHeight()>0&&!tempoLayout->isVisible(),"Compact Rhythm tempo keeps a contained bound while remaining hidden until running");
  const auto* compactTitle=dynamic_cast<const juce::Label*>(view.findChildWithID("rhythm-title"));ck(compactTitle&&compactTitle->getText().startsWith("Rhythm")&&compactTitle->getText().contains("Synthetic sound-check preview"),"Compact Rhythm uses a readable synthetic-preview identity heading");
  const char* actions[]={"rhythm-audio-settings","rhythm-start","rhythm-stop","rhythm-tempo","rhythm-finish","rhythm-back"};
  for(std::size_t leftIndex=0;leftIndex<std::size(actions);++leftIndex)for(std::size_t rightIndex=leftIndex+1;rightIndex<std::size(actions);++rightIndex){const auto* left=view.findChildWithID(actions[leftIndex]);const auto* right=view.findChildWithID(actions[rightIndex]);ck(left&&right&&!left->getBounds().intersects(right->getBounds()),std::string("Compact Rhythm actions do not overlap: ")+actions[leftIndex]+"/"+actions[rightIndex]);}
  auto* audio=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-audio-settings"));auto* start=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-start"));auto* stop=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-stop"));auto* tempo=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-tempo"));auto* done=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-finish"));auto* back=dynamic_cast<juce::TextButton*>(view.findChildWithID("rhythm-back"));auto* status=dynamic_cast<juce::Label*>(view.findChildWithID("rhythm-status"));
  ck(audio&&audio->getTitle().toStdString()=="Open shared Audio settings before starting the Rhythm preview."&&start&&start->getTitle().toStdString()=="Start Rhythm preview synthetic sound; no practice recording is created."&&stop&&stop->getTitle().toStdString()=="Stop Rhythm preview and retain the sound-check outcome until Finish check."&&tempo&&tempo->getTitle().toStdString()=="Change the Rhythm preview tempo for its next cycle."&&done&&done->getTitle().toStdString()=="Finish the Rhythm preview check and release its retained output safely."&&back&&back->getTitle().toStdString()=="Return Home after the Rhythm preview is safely stopped.","Compact Rhythm preserves explicit lifecycle titles");
  ck(status&&status->getText().toStdString().find("Closed")!=std::string::npos&&view.audioSnapshot().state==output::State::Closed&&view.audioCanRelease()&&nativeOpens==0&&connections==0,"Compact Rhythm remains closed, releasable and without native output");
  desktop::SchedulerView standard;standard.setSize(920,680);standard.setVisible(true);standard.resized();
  const auto* standardTitle=dynamic_cast<const juce::Label*>(standard.findChildWithID("rhythm-title"));ck(standardTitle&&standardTitle->getText().startsWith("RHYTHM")&&standardTitle->getText().contains("SYNTHETIC SOUND-CHECK PREVIEW"),"Standard Rhythm restores the authored identity heading");
  ck(standard.findChildWithID("rhythm-audio-settings")->getBounds().getX()==40&&standard.findChildWithID("rhythm-audio-settings")->getBounds().getY()==282&&standard.findChildWithID("rhythm-back")->getBounds().getY()==608,"Standard Rhythm geometry remains unchanged at 920x680");
  out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Compact Rhythm responsive layout checks\n";return 0;
 }
 if(referenceResponsiveOnly){
  desktop::ReferenceView view;view.setSize(640,680);view.setVisible(true);view.resized();
  const auto bounds=view.getLocalBounds();
  const char* visibleIds[]={"reference-string","reference-target","reference-sound","reference-audio-settings","reference-play","reference-stop","reference-done","reference-back"};
  for(const auto* id:visibleIds){auto* component=view.findChildWithID(id);ck(component&&component->isVisible()&&bounds.contains(component->getBounds())&&component->getWidth()>0&&component->getHeight()>0,std::string("Compact Reference surface remains visible and contained: ")+id);}
  const auto statusBounds=view.toneStatusView().getBounds();const auto detailsBounds=view.toneStatusView().detailsView().getBounds();ck(bounds.contains(statusBounds)&&statusBounds.getWidth()>0&&statusBounds.getHeight()>0&&bounds.contains(detailsBounds)&&detailsBounds.getWidth()>0&&detailsBounds.getHeight()>0,"Compact Reference status and read-only details remain contained");
  const char* actions[]={"reference-audio-settings","reference-play","reference-stop","reference-done","reference-back"};
  for(std::size_t leftIndex=0;leftIndex<std::size(actions);++leftIndex)for(std::size_t rightIndex=leftIndex+1;rightIndex<std::size(actions);++rightIndex){const auto* left=view.findChildWithID(actions[leftIndex]);const auto* right=view.findChildWithID(actions[rightIndex]);ck(left&&right&&!left->getBounds().intersects(right->getBounds()),std::string("Compact Reference actions do not overlap: ")+actions[leftIndex]+"/"+actions[rightIndex]);}
  const auto* compactTitle=dynamic_cast<const juce::Label*>(view.getChildComponent(0));ck(compactTitle&&compactTitle->getText().startsWith("Reference")&&compactTitle->getText().contains("Local tone comparison"),"Compact Reference uses a readable local-comparison identity heading");
  auto* audio=dynamic_cast<juce::TextButton*>(view.findChildWithID("reference-audio-settings"));auto* play=dynamic_cast<juce::TextButton*>(view.findChildWithID("reference-play"));auto* stop=dynamic_cast<juce::TextButton*>(view.findChildWithID("reference-stop"));auto* done=dynamic_cast<juce::TextButton*>(view.findChildWithID("reference-done"));auto* back=dynamic_cast<juce::TextButton*>(view.findChildWithID("reference-back"));
  ck(audio&&audio->getTitle().toStdString()=="Open shared Audio settings before playing a reference tone."&&play&&play->getTitle().toStdString()=="Play the selected reference tone."&&stop&&stop->getTitle().toStdString()=="Stop the reference tone and review the output state."&&done&&done->getTitle().toStdString()=="Acknowledge the stopped reference output and return to idle."&&back&&back->getTitle().toStdString()=="Return to Home after the reference output is idle.","Compact Reference preserves explicit lifecycle titles");
  ck(!view.displayedPitch().empty()&&view.toneStatusView().detailsButton().getButtonText().toStdString()=="Tone details"&&view.audioSnapshot().state==output::State::Closed&&view.audioCanRelease()&&nativeOpens==0&&connections==0,"Compact Reference remains truthful, closed, releasable and without native output");
  desktop::ReferenceView standard;standard.setSize(920,680);standard.setVisible(true);standard.resized();
  const auto* standardTitle=dynamic_cast<const juce::Label*>(standard.getChildComponent(0));ck(standardTitle&&standardTitle->getText().startsWith("REFERENCE")&&standardTitle->getText().contains("LOCAL TONE COMPARISON"),"Standard Reference restores the authored identity heading");
  ck(standard.findChildWithID("reference-string")->getBounds().getX()==40&&standard.findChildWithID("reference-string")->getBounds().getY()==220&&standard.findChildWithID("reference-audio-settings")->getBounds().getY()==530&&standard.findChildWithID("reference-back")->getBounds().getY()==608,"Standard Reference geometry remains unchanged at 920x680");
  out<<"summary\tPASS\tchecks="<<checks<<"\n";std::cout<<"PASS "<<checks<<" Compact Reference responsive layout checks\n";return 0;
 }
 if(tail)goto tail_cases;
 if(remainingAfterTransport)goto remaining_after_transport;
 if(remainder)goto remaining;
 if(lessonRhythmActiveContext){
  Harness h(dir,"lesson-rhythm-active-context");
  const auto bundle=std::filesystem::current_path()/"Build/parallel-03/9.4-app-smoke-r01/Fathom_artefacts/Release/Fathom.app/Contents/Resources/representative-controls";
  ck(std::filesystem::is_directory(bundle)&&A::lessons(*h.home).load(bundle.string()),"current packaged representative catalog loads for selected active-context route");
  click(*h.home,"Start learning");h.wait([&]{return h.home->page()==H::Page::Learn;},"Learn opens");
  auto& learn=A::lessons(*h.home);
  ck(learn.selectLesson("fg:item:000002")&&learn.selectVariant("fg:variant:000006"),"source-backed item and variant selected before rhythm handoff");
  click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"selected Practice opens");
  auto& practice=h.practice();const auto* capture=practice.captureSession();
  ck(capture&&capture->phase()==capture::SessionPhase::Idle&&!capture->startTaken()&&practice.lessonAdmission()!=nullptr&&h.finals()==0,"selected Practice remains idle and owns no finalized Attempt");
  const auto fixtureSession=h.sessionId;
  ck(practice.requestMetronome()&&h.home->page()==H::Page::Metronome&&A::visiblePages(*h.home)==1,"stopped selected Practice opens the shared rhythm tool");
  auto& rhythm=A::metronome(*h.home);auto selected=rhythm.settings();selected.tempo=97;selected.polyrhythmEnabled=true;selected.countIn=metronome::CountIn::Off;selected.ramp.reset();selected.x=5;selected.y=7;
  ck(rhythm.applySettings(selected)&&rhythm.settings().tempo==97&&rhythm.settings().x==5&&rhythm.settings().y==7&&rhythm.settings().polyrhythmEnabled,"stopped selected lesson configures shared 97 BPM 5:7 rhythm");
  click(rhythm,"Back");h.wait([&]{return h.home->page()==H::Page::Practice;},"rhythm returns selected Practice");
  ck(learn.selectedLesson()=="fg:item:000002"&&learn.selectedVariant()=="fg:variant:000006"&&h.sessionId==fixtureSession&&h.finals()==0,"stopped rhythm visit preserves selected source and Session without history");
  click(practice,"Audio settings");h.tick();click(A::settings(*h.home),"Connect audio");h.tick();click(A::settings(*h.home),"Enable audio");h.blocks(1);click(A::settings(*h.home),"Back to Practice");h.tick();
  const int preparedConnections=connections;
  ck(h.home->audioSettings().active()==desktop::SharedAudioSettings::Consumer::Practice&&maxClaims==1&&nativeOpens==0&&A::visiblePages(*h.home)==1,"selected Practice has the sole software audio owner before Start");
  click(practice,"Start selected case");h.wait([&]{return capture->startTaken();},"selected Practice Start");
  int callbacksToActive=0;
  while(practice.coordinator().activeFrames()==0&&callbacksToActive<1100&&capture->phase()!=capture::SessionPhase::Review&&capture->phase()!=capture::SessionPhase::Saved){h.blocks(1);++callbacksToActive;}
  const auto activeFrames=practice.coordinator().activeFrames();
  const auto attemptOwner=capture->binding().owner;
  out<<"diagnostic\tcallbacks_to_active="<<callbacksToActive<<"\tphase="<<static_cast<int>(capture->phase())<<"\tactive_frames="<<activeFrames<<"\n";out.flush();
  ck(!attemptOwner.empty()&&h.sessionId==fixtureSession&&capture->phase()==capture::SessionPhase::Active&&capture->startTaken()&&activeFrames>0&&h.finals()==0,"selected Practice schedules active frames for one unfinalized Attempt");
  ck(!practice.requestMetronome()&&h.home->page()==H::Page::Practice&&h.home->audioSettings().active()==desktop::SharedAudioSettings::Consumer::Practice&&connections==preparedConnections&&maxClaims==1,"active selected Practice refuses second rhythm owner and connection");
  const auto beforeGuardedCallback=practice.coordinator().activeFrames();h.blocks(1);
  ck(practice.coordinator().activeFrames()==beforeGuardedCallback+256&&connections==preparedConnections&&maxClaims==1,"guarded handoff advances exactly one 256-frame Practice callback without a second sound schedule");
  click(practice,"Back");h.tick();
  ck(h.home->page()==H::Page::Practice&&A::visiblePages(*h.home)==1&&capture->binding().owner==attemptOwner&&h.sessionId==fixtureSession&&capture->startTaken()&&h.finals()==0,"active Practice Back cannot replace Session or leak into Freeplay");
  h.blocks(2);h.wait([&]{return capture->phase()==capture::SessionPhase::Review;},"active Back stops the selected Practice into Review");
  ck(capture->binding().owner==attemptOwner&&h.sessionId==fixtureSession&&h.finals()==0,"return panel retains the original unfinalized Attempt and Session");
  click(practice,"Stay");h.tick();
  click(practice,"Save result");h.wait([&]{return capture->phase()==capture::SessionPhase::Saved&&practice.audioCanRelease();},"selected Practice save and audio cleanup");
  ck(h.finals()==1&&capture->binding().owner==attemptOwner&&h.sessionId==fixtureSession&&maxClaims==1,"exactly one selected Practice Attempt is finalized under original Session");
  click(practice,"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"saved Practice returns Learn");click(learn,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Learn returns Home");
  click(*h.home,"Freeplay");h.wait([&]{return h.home->page()==H::Page::Freeplay;},"independent Freeplay opens");auto& freeplay=A::freeplay(*h.home);
  ck(!freeplay.active()&&h.finals()==1&&learn.selectedLesson()=="fg:item:000002"&&learn.selectedVariant()=="fg:variant:000006","Freeplay starts separately while saved lesson source and Attempt remain intact");
  click(freeplay,"Start freeplay");ck(freeplay.active()&&!freeplay.requestRhythmTools()&&h.home->page()==H::Page::Freeplay&&h.finals()==1,"active Freeplay refuses rhythm handoff without duplicating Practice Attempt");
  click(freeplay,"Stop freeplay");h.wait([&]{return freeplay.persistenceSaved();},"separate Freeplay save");
  auto saved=capture_fixture::confirmed(h.store->snapshot("lesson-rhythm-after-freeplay"));capture_fixture::write(h.dir/"final-snapshot.json",storage::canonical(saved.data));
  ck(saved.data.find("authoritative")->find("finalized")->array().size()==2&&h.finals()==2,"one Practice Attempt and one separate Freeplay activity finalize without duplication");
  ck(freeplay.requestRhythmTools()&&h.home->page()==H::Page::Metronome&&A::visiblePages(*h.home)==1,"stopped Freeplay reaches the existing shared rhythm tool");
  ck(rhythm.settings().tempo==97&&rhythm.settings().x==5&&rhythm.settings().y==7&&rhythm.settings().polyrhythmEnabled&&maxClaims==1&&nativeOpens==0,"shared 97 BPM 5:7 state persists with at most one software output claim");
  std::ofstream summary(h.dir/"summary.json");summary<<"{\"checks\":"<<checks<<",\"selectedItem\":\"fg:item:000002\",\"selectedVariant\":\"fg:variant:000006\",\"tempo\":97,\"ratio\":[5,7],\"practiceActiveFrames\":"<<activeFrames<<",\"finalizedRows\":2,\"connections\":"<<connections<<",\"maxClaims\":"<<maxClaims<<",\"nativeOpens\":"<<nativeOpens<<"}\n";
  std::cout<<"PASS "<<checks<<" selected lesson and Freeplay active-context checks\n";return 0;
 }
 if(homeStartLearningAttempt){
  Harness h(dir,"home-start-learning-attempt");h.setup();click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Home before Start learning Attempt");
  const auto testBundle=juce::File::getCurrentWorkingDirectory().getChildFile("Build/development/Fathom_artefacts/Release/Fathom.app/Contents/Resources/representative-controls").getFullPathName().toStdString();
  ck(A::lessons(*h.home).load(testBundle),"Start learning Attempt smoke loads the retained representative bundle");click(*h.home,"Start learning");h.wait([&]{return h.home->page()==H::Page::Learn;},"Start learning Attempt enters Learn");
  ck(A::lessons(*h.home).selectLesson("fg:item:000002")&&A::lessons(*h.home).selectVariant("fg:variant:000006"),"Start learning Attempt selects the retained admitted item and variant");auto* practiceAction=dynamic_cast<juce::TextButton*>(A::lessons(*h.home).findChildWithID("practice-selection"));ck(practiceAction&&practiceAction->findColour(juce::TextButton::buttonColourId).getARGB()==0xff6bd5cbU&&practiceAction->findColour(juce::TextButton::textColourOffId).getARGB()==0xff10212cU&&practiceAction->findColour(juce::TextButton::textColourOnId).getARGB()==0xff10212cU,"Learn admitted Practice action is visibly emphasized without changing its source-backed action");click(A::lessons(*h.home),"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"admitted case enters Practice");
  ck(h.practice().lessonAdmission()!=nullptr&&h.practice().captureSession()!=nullptr&&h.practice().captureSession()->phase()==capture::SessionPhase::Idle&&!h.practice().captureSession()->startTaken()&&h.finals()==0,"selected Practice starts stopped with no Attempt");
  auto* idleStart=dynamic_cast<juce::TextButton*>(h.practice().findChildWithID("practice-start"));auto* idlePause=dynamic_cast<juce::TextButton*>(h.practice().findChildWithID("practice-pause"));
  ck(idleStart&&idlePause,"Practice idle action components are present");
  out<<"diagnostic\\tidle_start_title="<<(idleStart?idleStart->getTitle().toStdString():"<missing>")<<"\\tidle_pause_title="<<(idlePause?idlePause->getTitle().toStdString():"<missing>")<<"\\n";out.flush();
  ck(idleStart&&idleStart->getTitle().toStdString()=="Start the selected Practice sample for fg:item:000002 / fg:variant:000006; it will remain owned by the active Guided Session and creates no curriculum credit.","Practice idle Start title exposes the selected source identity, Guided owner and explicit no-credit boundary");
  ck(idlePause&&idlePause->getTitle().toStdString().find("fg:item:000002 / fg:variant:000006")!=std::string::npos,"Practice idle Pause title exposes the selected source identity");
  click(h.practice(),"Audio settings");h.tick();click(A::settings(*h.home),"Connect audio");h.tick();click(A::settings(*h.home),"Enable audio");h.blocks(1);click(A::settings(*h.home),"Back to Practice");h.tick();ck(h.home->page()==H::Page::Practice&&h.practice().audioCanRelease(),"Practice Audio preparation settles before explicit Start");
  click(h.practice(),"Start selected case");h.wait([&]{return h.practice().captureSession()->startTaken();},"explicit Practice Start");h.blocks(1);ck(h.practice().captureSession()->startTaken()&&h.finals()==0,"explicit Practice Start begins one unfinalized Attempt");
  auto* pauseAction=dynamic_cast<juce::TextButton*>(h.practice().findChildWithID("practice-pause"));auto* resumeAction=dynamic_cast<juce::TextButton*>(h.practice().findChildWithID("practice-resume"));auto* stopAction=dynamic_cast<juce::TextButton*>(h.practice().findChildWithID("practice-stop"));ck(pauseAction&&resumeAction&&stopAction&&pauseAction->getTitle().toStdString().find("fg:item:000002 / fg:variant:000006")!=std::string::npos&&resumeAction->getTitle().toStdString().find("active time remains retained")!=std::string::npos&&stopAction->getTitle().toStdString().find("Save result is a separate explicit action")!=std::string::npos,"Practice running actions expose source identity and separate Pause/Resume/Stop boundaries");
  h.end();auto* saveAction=dynamic_cast<juce::TextButton*>(h.practice().findChildWithID("practice-save"));auto* retryAction=dynamic_cast<juce::TextButton*>(h.practice().findChildWithID("practice-retry"));auto* againAction=dynamic_cast<juce::TextButton*>(h.practice().findChildWithID("practice-again"));ck(h.practice().captureSession()->phase()==capture::SessionPhase::Review&&saveAction&&retryAction&&againAction&&saveAction->getTitle().toStdString().find("one local Attempt")!=std::string::npos&&retryAction->getTitle().toStdString().find("no duplicate Attempt")!=std::string::npos&&againAction->getTitle().toStdString().find("without saving a curriculum result")!=std::string::npos&&h.finals()==0,"Practice review actions expose explicit Save, Retry and Again boundaries without finalization");click(h.practice(),"Save result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"Practice Save result");h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"Practice audio cleanup");
  saveAction=dynamic_cast<juce::TextButton*>(h.practice().findChildWithID("practice-save"));retryAction=dynamic_cast<juce::TextButton*>(h.practice().findChildWithID("practice-retry"));ck(h.practice().captureSession()->phase()==capture::SessionPhase::Saved&&saveAction&&retryAction&&saveAction->getTitle().toStdString().find("already saved")!=std::string::npos&&retryAction->getTitle().toStdString().find("will not create another Attempt")!=std::string::npos&&h.practice().audioCanRelease()&&h.finals()==1,"Practice saved state makes duplicate Save and Retry consequences explicit");click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"saved Practice Back returns Learn");ck(A::lessons(*h.home).selectedLesson()=="fg:item:000002"&&A::lessons(*h.home).selectedVariant()=="fg:variant:000006"&&h.finals()==1,"saved Practice Back preserves exact source identity without duplicate finalization");click(A::lessons(*h.home),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Learn Back returns Home");ck(h.home->page()==H::Page::Home&&h.finals()==1,"Learn Back returns Home after one saved Attempt");std::cout<<"PASS "<<checks<<" Start Learning Practice Attempt save checks\n";return 0;
 }
 if(learnRefusedPracticeTitle){
  Harness h(dir,"learn-refused-practice-title");h.setup();click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Learn refused title starts from Home");
  const auto testBundle=juce::File::getCurrentWorkingDirectory().getChildFile("Build/development/Fathom_artefacts/Release/Fathom.app/Contents/Resources/representative-controls").getFullPathName().toStdString();
  ck(A::lessons(*h.home).load(testBundle),"Learn refused title loads the retained representative bundle");click(*h.home,"Start learning");h.wait([&]{return h.home->page()==H::Page::Learn;},"Learn refused title enters Learn");
  auto& learn=A::lessons(*h.home);ck(learn.selectLesson("fg:item:000001")&&learn.selectVariant("fg:variant:000001"),"Learn refused title selects the retained refused source case");auto* refused=dynamic_cast<juce::TextButton*>(learn.findChildWithID("practice-selection"));const auto refusedTitle=refused?refused->getTitle().toStdString():std::string{};ck(refused&&!refused->isEnabled()&&refusedTitle.find("fg:item:000001 / fg:variant:000001")!=std::string::npos&&refusedTitle.find("runtime admission refused")!=std::string::npos&&refusedTitle.find("no Practice, Attempt or curriculum credit")!=std::string::npos&&refusedTitle.find("Choose another retained case in Learn")!=std::string::npos,"Learn refused Practice action stays disabled and exposes its source-specific no-activity boundary");ck(h.home->page()==H::Page::Learn&&h.finals()==0&&!h.practice().captureSession()->startTaken(),"refused Practice selection remains in Learn with no Attempt or finalized activity");
  ck(learn.selectLesson("fg:item:000002")&&learn.selectVariant("fg:variant:000006"),"Learn refused title returns to the retained admitted source case");auto* admitted=dynamic_cast<juce::TextButton*>(learn.findChildWithID("practice-selection"));ck(admitted&&admitted->isEnabled()&&admitted->getTitle().toStdString().find("Open admitted fg:item:000002 / fg:variant:000006 in Practice")!=std::string::npos,"Learn admitted Practice action remains enabled with its existing source-backed title");std::cout<<"PASS "<<checks<<" Learn refused Practice title checks\n";return 0;
 }
 if(homeStartLearningSearchRoute){
  Harness h(dir,"home-start-learning-search-route");const auto testBundle=juce::File::getCurrentWorkingDirectory().getChildFile("Build/development/Fathom_artefacts/Release/Fathom.app/Contents/Resources/representative-controls").getFullPathName().toStdString();ck(A::lessons(*h.home).load(testBundle),"Start learning search route loads the retained representative bundle");click(*h.home,"Start learning");h.wait([&]{return h.home->page()==H::Page::Learn;},"Start learning search route enters Learn");auto& learn=A::lessons(*h.home);auto* search=dynamic_cast<juce::TextEditor*>(learn.findChildWithID("lesson-search"));auto* clear=dynamic_cast<juce::TextButton*>(learn.findChildWithID("lesson-search-clear"));auto* rows=dynamic_cast<juce::ComboBox*>(learn.findChildWithID("lessons"));auto* searchStatus=dynamic_cast<juce::Label*>(learn.findChildWithID("lesson-search-status"));ck(search&&clear&&rows&&searchStatus&&rows->getNumItems()==13,"Start learning search route exposes the retained 13-case catalog and search controls");search->setText("fg:item:000002",false);if(search->onTextChange)search->onTextChange();h.tick();ck(rows->getNumItems()==1&&rows->getItemText(0).toStdString().find("fg:item:000002")!=std::string::npos,"Start learning search filters to the exact retained source-backed item");ck(searchStatus->getText().toStdString().find("1 matching retained case")!=std::string::npos&&searchStatus->getText().toStdString().find("outside this filter")!=std::string::npos,"Start learning search reports one exact match without replacing selection");ck(learn.selectLesson("fg:item:000002")&&learn.selectVariant("fg:variant:000006")&&learn.practiceSelected(),"filtered Start learning case remains admitted for explicit Practice handoff");click(learn,"Clear search");if(search->onTextChange)search->onTextChange();h.tick();ck(rows->getNumItems()==13&&learn.selectedLesson()=="fg:item:000002"&&learn.selectedVariant()=="fg:variant:000006"&&search->getText().isEmpty(),"Clear search restores all retained cases and preserves exact source identity");click(learn,"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"filtered admitted case enters Practice");ck(h.practice().lessonAdmission()!=nullptr&&h.practice().captureSession()!=nullptr&&h.practice().captureSession()->phase()==capture::SessionPhase::Idle&&!h.practice().captureSession()->startTaken()&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed,"search route enters stopped Practice with explicit Start required and no Attempt, curriculum activity or audio connection");click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"search route Practice Back returns Learn");ck(learn.selectedLesson()=="fg:item:000002"&&learn.selectedVariant()=="fg:variant:000006"&&h.finals()==0,"search route Back preserves exact selected identity without activity");click(learn,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"search route Learn Back returns Home");std::cout<<"PASS "<<checks<<" Start Learning search route checks\n";return 0;
 }
 if(homePracticeEntry){
  {Harness route(dir,"home-practice-route");const auto testBundle=juce::File::getCurrentWorkingDirectory().getChildFile("Build/development/Fathom_artefacts/Release/Fathom.app/Contents/Resources/representative-controls").getFullPathName().toStdString();ck(A::lessons(*route.home).load(testBundle),"Home Practice route loads the retained representative bundle");click(*route.home,"Practice (choose in Learn)");route.wait([&]{return route.home->page()==H::Page::Learn;},"Home Practice route enters Learn");ck(route.home->page()==H::Page::Learn&&A::lessons(*route.home).catalog()&&A::lessons(*route.home).catalog()->lessons().size()==13&&route.finals()==0&&route.home->audioSettings().snapshot().state==output::State::Closed,"Home Practice route exposes the retained 13-case Learn catalog without activity or audio");click(A::lessons(*route.home),"Back");route.wait([&]{return route.home->page()==H::Page::Home;},"Home Practice route Learn Back returns Home");ck(route.home->page()==H::Page::Home&&route.finals()==0&&route.home->audioSettings().snapshot().state==output::State::Closed,"Home Practice route returns safely to Home without activity or audio");}
  Harness h(dir,"home-practice-entry");ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed,"fresh Home Practice entry fixture starts at Home with closed output");h.home->navigate(H::Page::Practice);auto* status=dynamic_cast<juce::Label*>(h.practice().findChildWithID("practice-status"));auto* authored=dynamic_cast<juce::Label*>(h.practice().findChildWithID("practice-authored-source"));ck(h.home->page()==H::Page::Practice&&status&&status->isVisible(),"actual Home Practice click opens one visible Practice page with status");const auto text=status?status->getText().toStdString():std::string{};const auto authoredText=authored?authored->getText().toStdString():std::string{};ck(h.practice().lessonAdmission()==nullptr&&h.practice().captureSession()!=nullptr&&h.practice().captureSession()->phase()==capture::SessionPhase::Idle&&!h.practice().captureSession()->startTaken()&&h.finals()==0,"direct Home Practice entry has no selected case, Attempt or finalization");ck(text.find("Practice opens from Learn")!=std::string::npos&&text.find("Choose an admitted source-backed case before Start")!=std::string::npos&&text.find("no Attempt or curriculum credit exists yet")!=std::string::npos,"direct Home Practice entry exposes the truthful Learn-first/no-credit empty state");ck(authored&&authored->isVisible()&&authoredText.find("Choose an admitted source-backed case in Learn before Practice.")!=std::string::npos&&authoredText.find("No authored lesson instructions or TAB are loaded in this empty Practice view.")!=std::string::npos&&authoredText.find("No Attempt or curriculum credit exists yet.")!=std::string::npos&&authoredText.find("Synthetic sample:")==std::string::npos,"direct Home Practice authored-source surface is truthful and contains no synthetic lesson claim");ck(text.find("Open Audio settings to connect and enable the shared output before Start")!=std::string::npos&&h.home->audioSettings().snapshot().state==output::State::Closed,"direct Home Practice empty state points to shared Audio without starting output");click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Home Practice Back returns Home");ck(h.home->page()==H::Page::Home&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed,"direct Home Practice Back returns safely with no activity or audio connection");std::cout<<"PASS "<<checks<<" Home Practice entry checks\n";return 0;
 }
 if(homeAudioEntry){
  Harness h(dir,"home-audio-entry");ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"fresh Home Audio entry fixture starts at Home with closed output and no native activity");click(*h.home,"Audio settings");h.wait([&]{return h.home->page()==H::Page::Audio;},"Home Audio entry opens Audio");auto& audio=A::settings(*h.home);auto* description=dynamic_cast<juce::Label*>(audio.findChildWithID("shared-audio-description"));auto* status=dynamic_cast<juce::Label*>(audio.findChildWithID("shared-audio-status"));auto* connect=dynamic_cast<juce::TextButton*>(audio.findChildWithID("audio-connect"));auto* enable=dynamic_cast<juce::TextButton*>(audio.findChildWithID("audio-enable"));ck(A::visiblePages(*h.home)==1&&description&&status&&description->isVisible()&&status->isVisible()&&connect&&enable&&connect->isVisible()&&enable->isVisible(),"actual Home Audio click opens one visible shared Audio page with explicit Connect and Enable controls");const auto descriptionText=description?description->getText().toStdString():std::string{};const auto statusText=status?status->getText().toStdString():std::string{};ck(descriptionText.find("Connect your macOS speakers or headphones, then Enable audio.")!=std::string::npos&&descriptionText.find("These shared settings apply across Learn, Practice, Freeplay and rhythm tools.")!=std::string::npos&&statusText.find("Next action: choose Connect audio, then choose Enable audio")!=std::string::npos,"direct Home Audio entry preserves the shared-scope and explicit-next-action guidance");ck(h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0&&h.finals()==0,"direct Home Audio entry does not connect output, open native audio or create activity");click(audio,"Back to Home");h.wait([&]{return h.home->page()==H::Page::Home;},"Home Audio Back returns Home");ck(h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0&&h.finals()==0,"direct Home Audio Back returns safely with closed output and no activity");std::cout<<"PASS "<<checks<<" Home Audio entry checks\n";return 0;
 }
 if(homeReferenceEntry){
  Harness h(dir,"home-reference-entry");ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"fresh Home Reference entry fixture starts at Home with closed output and no native activity");click(*h.home,"Reference tones");h.wait([&]{return h.home->page()==H::Page::Reference;},"Home Reference entry opens Reference");auto& reference=A::reference(*h.home);juce::Label* heading=nullptr;for(auto* child:reference.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText().toStdString()=="REFERENCE — LOCAL TONE COMPARISON"){heading=label;break;}ck(heading&&heading->getText().toStdString()=="REFERENCE — LOCAL TONE COMPARISON","Reference heading identifies local tone comparison");ck(A::visiblePages(*h.home)==1&&reference.audioCanRelease()&&reference.outputSnapshot().state==output::State::Closed,"actual Home Reference click opens one visible stopped Reference page with closed output");const auto guidance=reference.toneStatusView().primaryText();ck(guidance.find("Output is closed.")!=std::string::npos&&guidance.find("Open Audio settings")!=std::string::npos&&guidance.find("Play tone begins sound")!=std::string::npos,"direct Home Reference entry exposes truthful stopped shared-Audio guidance");ck(!reference.outputSnapshot().ownsOutcome&&nativeOpens==0&&connections==0&&h.finals()==0,"direct Home Reference entry creates no native output, tone outcome, Attempt or finalization");click(reference,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Home Reference Back returns Home");ck(h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0&&reference.audioCanRelease()&&reference.outputSnapshot().state==output::State::Closed&&nativeOpens==0&&connections==0&&h.finals()==0,"direct Home Reference Back returns safely with closed output and no activity");std::cout<<"PASS "<<checks<<" Home Reference entry checks\n";return 0;
 }
 if(homeProgressEntry){
  Harness h(dir,"home-progress-entry");ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0&&h.finals()==0,"fresh Home Progress entry fixture starts at Home with closed output and zero finalized activity");click(*h.home,"Progress");h.wait([&]{return h.home->page()==H::Page::Progress;},"Home Progress entry opens Progress");auto& progress=A::progress(*h.home);ck(A::visiblePages(*h.home)==1,"actual Home Progress click opens one visible Progress page");auto* learnAction=dynamic_cast<juce::TextButton*>(progress.findChildWithID("progress-learn"));auto* detailsAction=dynamic_cast<juce::TextButton*>(progress.findChildWithID("progress-details"));ck(learnAction&&learnAction->findColour(juce::TextButton::buttonColourId).getARGB()==0xff6bd5cbU&&learnAction->findColour(juce::TextButton::textColourOffId).getARGB()==0xff10212cU&&learnAction->findColour(juce::TextButton::textColourOnId).getARGB()==0xff10212cU,"Progress keeps its existing Choose practice in Learn action visibly primary without changing read-only behavior");h.wait([&]{return !progress.busy();},"Home Progress read-only refresh settles");const auto statusText=progress.statusText();ck(!statusText.empty()&&statusText.find("Saved snapshot")!=std::string::npos&&statusText.find("read-only")!=std::string::npos&&statusText.find("does not award curriculum credit")!=std::string::npos&&!progress.presentation().text.empty(),"Progress entry settles with a saved read-only snapshot and explicit no-credit guidance");ck(detailsAction&&detailsAction->getButtonText().toStdString()=="Show saved details"&&detailsAction->getTitle().toStdString()=="Show retained read-only saved details.","Progress saved-details control exposes its truthful Show state");click(progress,"Show saved details");h.tick();ck(detailsAction&&detailsAction->getButtonText().toStdString()=="Hide saved details"&&detailsAction->getTitle().toStdString()=="Hide retained read-only saved details.","Progress saved-details control exposes its truthful Hide state without changing the read-only snapshot");ck(h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"read-only Progress refresh and details disclosure create no Attempt, finalization, audio connection or native output");click(progress,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Home Progress Back returns Home");ck(h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed,"direct Home Progress Back returns safely without activity or output mutation");std::cout<<"PASS "<<checks<<" Home Progress entry checks\n";return 0;
 }
 if(homeFreeplayEntry){
  Harness h(dir,"home-freeplay-entry");auto& freeplay=A::freeplay(*h.home);ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0&&h.finals()==0&&!freeplay.active(),"fresh Home Freeplay entry fixture starts at Home with closed output, stopped timer and zero finalized activity");click(*h.home,"Freeplay");h.wait([&]{return h.home->page()==H::Page::Freeplay;},"Home Freeplay entry opens Freeplay");auto* explanation=dynamic_cast<juce::Label*>(freeplay.findChildWithID("freeplay-explanation"));auto* status=dynamic_cast<juce::Label*>(freeplay.findChildWithID("freeplay-status"));ck(A::visiblePages(*h.home)==1&&explanation&&status&&explanation->isVisible()&&status->isVisible()&&!freeplay.active()&&freeplay.canLeave()&&freeplay.persistenceConfigured(),"actual Home Freeplay click opens one visible stopped/profile-bound Freeplay page");const auto explanationText=explanation?explanation->getText().toStdString():std::string{};const auto statusText=status?status->getText().toStdString():std::string{};ck(explanationText.find("Stopped Freeplay activity is saved locally as separate history and never grants curriculum progress.")!=std::string::npos&&explanationText.find("Use Audio settings for shared speakers and headphones")!=std::string::npos&&statusText.find("Freeplay is stopped")!=std::string::npos&&statusText.find("Next action: choose Start freeplay to begin active-time capture")!=std::string::npos,"direct Home Freeplay entry preserves separate-history/shared-Audio/no-credit guidance and the explicit Start next action");ck(!freeplay.active()&&freeplay.historyWriteCount()==0&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"direct Home Freeplay entry creates no active time, history, finalized activity, audio connection or native output");click(freeplay,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Home Freeplay Back returns Home");ck(h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0&&!freeplay.active()&&freeplay.historyWriteCount()==0&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"direct Home Freeplay Back returns safely with stopped timer, no history, no activity and closed output");std::cout<<"PASS "<<checks<<" Home Freeplay entry checks\n";return 0;
 }
 if(homeMetronomeEntry){
  Harness h(dir,"home-metronome-entry");auto& metronome=A::metronome(*h.home);ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0&&h.finals()==0&&!metronome.soundPending(),"fresh Home Metronome entry fixture starts at Home with closed output, stopped sound check and zero finalized activity");click(*h.home,"Metronome");h.wait([&]{return h.home->page()==H::Page::Metronome;},"Home Metronome entry opens Metronome");h.wait([&]{return metronome.preferencesReady();},"Home Metronome preference read settles");std::string surfaceText;for(auto* child:metronome.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))surfaceText+=label->getText().toStdString()+"\n";const auto statusText=desktop::MetronomeViewTestAccess::statusText(metronome);ck(A::visiblePages(*h.home)==1&&metronome.preferencesReady()&&!metronome.soundPending()&&metronome.audioCanRelease()&&metronome.audioSnapshot().state==output::State::Closed&&surfaceText.find("Audio settings are shared across Learn, Practice, Freeplay and Rhythm; Start begins sound.")!=std::string::npos&&surfaceText.find("Settings only; no practice result.")!=std::string::npos&&surfaceText.find("METRONOME — TIMED SOUND-CHECK PREVIEW")!=std::string::npos,"actual Home Metronome click opens one visible settled stopped page with explicit shared-Audio/start/no-result/heading guidance");const auto metronomeOutput=metronome.audioSnapshot();const auto sharedOutput=h.home->audioSettings().snapshot();out<<"diagnostic\\tmetronome_state="<<static_cast<int>(metronomeOutput.state)<<"\\tshared_state="<<static_cast<int>(sharedOutput.state)<<"\\tretained="<<metronome.retained().size()<<"\\tfinals="<<h.finals()<<"\\tnativeOpens="<<nativeOpens<<"\\tconnections="<<connections<<"\\n";out<<"metronome-status\\t"<<statusText<<"\\n";out.flush();ck(statusText.find("Closed · no unresolved check")!=std::string::npos,"direct Home Metronome status retains the Closed no-unresolved-check cue");ck(metronome.retained().empty(),"direct Home Metronome entry retains no sound-check generation");ck(h.finals()==0,"direct Home Metronome entry creates no finalized activity");ck(h.home->audioSettings().snapshot().state==output::State::Closed,"direct Home Metronome entry leaves shared Audio Closed");ck(nativeOpens==0&&connections==0,"direct Home Metronome entry opens no native output or connection");click(metronome,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Home Metronome Back returns Home");ck(h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0&&!metronome.soundPending()&&metronome.audioCanRelease()&&metronome.audioSnapshot().state==output::State::Closed&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"direct Home Metronome Back returns safely with stopped check, no activity and closed output");std::cout<<"PASS "<<checks<<" Home Metronome entry checks\n";return 0;
 }
 if(restoredPreferencesStopped){
  Harness h(dir,"restored-preferences-stopped");
  const int nativeOpensBefore=nativeOpens,connectionsBefore=connections;
  const auto isCustom=[](const metronome::Settings& value){return value.tempo==97&&value.numerator==4&&value.denominator==4&&value.polyrhythmEnabled&&value.x==5&&value.y==7&&value.countIn==metronome::CountIn::Off;};
  const auto noPracticeActivity=[&](){
   auto* capture=h.practice().captureSession();auto& freeplay=A::freeplay(*h.home);
   return h.home->audioSettings().snapshot().state==output::State::Closed&&!freeplay.active()&&freeplay.activeNanoseconds()==0&&freeplay.historyWriteCount()==0&&capture&&capture->phase()==capture::SessionPhase::Idle&&!capture->startTaken()&&h.practice().lessonAdmission()==nullptr&&A::lessons(*h.home).selectedLesson().empty()&&h.finals()==0;
  };
  auto& initial=A::metronome(*h.home);
  ck(h.home->page()==H::Page::Home&&initial.preferencesReady()&&!initial.soundPending()&&initial.audioSnapshot().state==output::State::Closed&&noPracticeActivity()&&nativeOpens==nativeOpensBefore&&connections==connectionsBefore,"fresh profile starts Home with settled preferences, closed output, stopped Freeplay and no lesson activity");
  auto custom=initial.settings();custom.tempo=97;custom.polyrhythmEnabled=true;custom.x=5;custom.y=7;custom.countIn=metronome::CountIn::Off;
  ck(initial.applySettings(custom)&&isCustom(initial.settings()),"non-default 97 BPM, 5:7 rhythm and count-in-off settings apply while stopped");
  ck(!initial.soundPending()&&initial.audioSnapshot().state==output::State::Closed&&initial.audioCanRelease()&&nativeOpens==nativeOpensBefore&&connections==connectionsBefore&&noPracticeActivity(),"custom settings application starts no sound, Freeplay timer, history or lesson activity");
  ck(initial.savePreset("P04 restored 5:7"),"custom last-used rhythm preference persists through the real Store API");
  h.wait([&]{return initial.preferencesReady();},"custom preference write confirmation");
  ck(isCustom(initial.preferences().lastUsed)&&initial.preferences().presets.size()==1&&isCustom(initial.preferences().presets.front().settings)&&initial.audioSnapshot().state==output::State::Closed&&!initial.soundPending()&&noPracticeActivity(),"stored non-default preference is acknowledged without output or activity");
  click(initial,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"return Home before same-profile context recreation");
  ck(noPracticeActivity()&&nativeOpens==nativeOpensBefore&&connections==connectionsBefore,"first context closes with zero Freeplay and lesson activity");
  h.home.reset();h.store.reset();
  storage::StoreOptions reopen;reopen.path=h.dir/"profile.sqlite";reopen.preferenceValidator=metronome::preferenceValidator;
  h.store=std::make_unique<storage::ProfileStore>(reopen);
  h.home=std::make_unique<H>();h.home->setVisible(true);h.home->setSize(920,680);
  ck(h.home->configureCapture(*h.store,h.sessionId,"America/New_York"),"same local profile and fixture Session bind after Home/Store recreation");
  A::halt(*h.home);
  auto& restored=A::metronome(*h.home);
  h.wait([&]{return restored.preferencesReady();},"reopened Metronome preference read settles");
  ck(h.home->page()==H::Page::Home&&restored.preferencesReady()&&isCustom(restored.preferences().lastUsed)&&restored.preferences().presets.size()==1&&isCustom(restored.preferences().presets.front().settings)&&restored.settings().tempo==60&&!restored.settings().polyrhythmEnabled&&!restored.soundPending()&&restored.audioCanRelease()&&restored.audioSnapshot().state==output::State::Closed&&nativeOpens==nativeOpensBefore&&connections==connectionsBefore&&noPracticeActivity(),"same-profile reload decodes custom preference but does not auto-restore, start output, timer or activity");
  click(*h.home,"Metronome");h.wait([&]{return h.home->page()==H::Page::Metronome&&restored.preferencesReady();},"reopened Metronome becomes visible with preferences ready");
  click(restored,"Restore last");h.tick();
  ck(isCustom(restored.settings())&&!restored.soundPending()&&restored.audioCanRelease()&&restored.audioSnapshot().state==output::State::Closed&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==nativeOpensBefore&&connections==connectionsBefore&&noPracticeActivity(),"explicit Restore last applies the saved 97 BPM and 5:7 rhythm while remaining stopped");
  click(restored,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"restored stopped preference returns Home");
  ck(noPracticeActivity()&&!restored.soundPending()&&restored.audioSnapshot().state==output::State::Closed&&nativeOpens==nativeOpensBefore&&connections==connectionsBefore,"restored preference leaves no timer, audio output, history or lesson activity");
  std::ofstream summary(dir/"summary.json");summary<<"{\"checks\":"<<checks<<",\"status\":\"PASS\",\"restoredTempo\":97,\"polyrhythm\":[5,7],\"countInOff\":true,\"output\":\"Closed\",\"freeplayActive\":false,\"finalizedActivity\":0}\n";
  std::cout<<"PASS "<<checks<<" restored custom preference stopped checks\n";return 0;
 }
  if(homeRhythmEntry){
  Harness h(dir,"home-rhythm-entry");auto& rhythm=A::rhythm(*h.home);ck(h.home->page()==H::Page::Home&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0&&h.finals()==0&&rhythm.audioSnapshot().state==output::State::Closed,"fresh Home Rhythm entry fixture starts at Home with closed output, stopped preview and zero finalized activity");click(*h.home,"Rhythm preview");h.wait([&]{return h.home->page()==H::Page::Rhythm;},"Home Rhythm entry opens Rhythm preview");std::string surfaceText;for(auto* child:rhythm.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))surfaceText+=label->getText().toStdString()+"\n";ck(A::visiblePages(*h.home)==1&&rhythm.audioCanRelease()&&rhythm.audioSnapshot().state==output::State::Closed&&surfaceText.find("Use Audio settings for speakers, headphones and volume. These shared settings apply across the other activities; Start begins sound.")!=std::string::npos&&surfaceText.find("This preview does not record practice.")!=std::string::npos,"actual Home Rhythm click opens one visible stopped page with explicit shared-Audio/start/no-practice-record guidance");const auto rhythmOutput=rhythm.audioSnapshot();const auto sharedOutput=h.home->audioSettings().snapshot();out<<"diagnostic\\trhythm_state="<<static_cast<int>(rhythmOutput.state)<<"\\tshared_state="<<static_cast<int>(sharedOutput.state)<<"\\tclosed_text="<<(surfaceText.find("Closed")!=std::string::npos)<<"\\towns="<<rhythmOutput.ownsOutcome<<"\\tpending="<<rhythmOutput.pendingOutcome<<"\\tfinals="<<h.finals()<<"\\tnativeOpens="<<nativeOpens<<"\\tconnections="<<connections<<"\\n";out.flush();ck(surfaceText.find("Closed")!=std::string::npos&&rhythmOutput.state==output::State::Closed&&!rhythmOutput.ownsOutcome&&!rhythmOutput.pendingOutcome&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"direct Home Rhythm entry creates no sound owner, output connection, native activity, retained outcome or finalized activity");click(rhythm,"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Home Rhythm Back returns Home");ck(h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0&&rhythm.audioCanRelease()&&rhythm.audioSnapshot().state==output::State::Closed&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,"direct Home Rhythm Back returns safely with stopped preview, no activity and closed output");std::cout<<"PASS "<<checks<<" Home Rhythm entry checks\n";return 0;
 }
 if(homeNavigationSmoke){
  Harness h(dir,"home-navigation-smoke");h.setup();const auto testBundle=juce::File::getCurrentWorkingDirectory().getChildFile("Build/development/Fathom_artefacts/Release/Fathom.app/Contents/Resources/representative-controls").getFullPathName().toStdString();A::lessons(*h.home).load(testBundle);click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Home after Practice");
  ck(h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0,"Home is the single visible root after idle Practice");
  click(*h.home,"Start learning");h.wait([&]{return h.home->page()==H::Page::Learn;},"Start learning enters Learn");
  ck(h.home->page()==H::Page::Learn&&A::visiblePages(*h.home)==1&&A::lessons(*h.home).catalog()&&A::lessons(*h.home).catalog()->lessons().size()==13,"Start learning opens one visible Learn page with the retained 13-case catalog");
  ck(!h.practice().captureSession()->startTaken()&&h.finals()==0&&h.home->audioSettings().snapshot().state==output::State::Closed,"Start learning creates no Practice Attempt, curriculum activity or audio connection");
  ck(A::lessons(*h.home).selectLesson("fg:item:000002")&&A::lessons(*h.home).selectVariant("fg:variant:000006"),"Start learning selects the retained admitted item and variant");
  click(A::lessons(*h.home),"Practice selected case");h.wait([&]{return h.home->page()==H::Page::Practice;},"admitted Start learning case enters Practice");
  ck(A::lessons(*h.home).selectedLesson()=="fg:item:000002"&&A::lessons(*h.home).selectedVariant()=="fg:variant:000006"&&h.practice().lessonAdmission()!=nullptr&&h.practice().captureSession()!=nullptr&&h.practice().captureSession()->phase()==capture::SessionPhase::Idle&&!h.practice().captureSession()->startTaken()&&h.finals()==0,"admitted Practice entry preserves exact identity and requires explicit Start");
  click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"Practice Back after Start learning selection");
  ck(A::lessons(*h.home).selectedLesson()=="fg:item:000002"&&A::lessons(*h.home).selectedVariant()=="fg:variant:000006"&&h.finals()==0,"Practice Back preserves the selected source identity without an Attempt");
  click(A::lessons(*h.home),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Learn Back after Start learning");
  ck(h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0,"Start learning Learn Back returns to the single visible Home destination");
  auto* returnedHomeInventory=dynamic_cast<juce::Label*>(h.home->findChildWithID("home-preview-inventory"));ck(returnedHomeInventory&&returnedHomeInventory->getText().toStdString().find("Current Learn selection: fg:item:000002 / fg:variant:000006. Practice remains explicit; selection creates no Attempt or curriculum credit.")!=std::string::npos,"Home retains the exact selected Learn identity without inferring Practice or curriculum credit");
  ck(returnedHomeInventory&&returnedHomeInventory->getText().toStdString().find("Source refs: L3-TXT5-21, L3-TXT28-46")!=std::string::npos&&returnedHomeInventory->getText().toStdString().find("Content version: representative-controls.1 | Content revision: 2 | Workbook identity: fg:workbook:000003 | Level: 3")!=std::string::npos,"Home retains exact selected source provenance without invoking admission or fabricating completion");
  ck(returnedHomeInventory&&returnedHomeInventory->getText().toStdString().find("Lesson title: ModeA Exercise001 full selected directions")!=std::string::npos,"Home shows the exact selected lesson title from the loaded Catalog record");
  ck(returnedHomeInventory&&returnedHomeInventory->getText().toStdString().find("Selected variant: sixteenths-ascending-D-even")!=std::string::npos,"Home shows the exact selected variant label from the loaded Catalog record");
  ck(h.home->navigate(H::Page::Learn)&&h.home->page()==H::Page::Learn&&A::visiblePages(*h.home)==1,"Home opens the visible Learn destination");
  ck(h.home->navigate(H::Page::Home)&&h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0,"Learn returns to the single visible Home destination");
  ck(h.home->navigate(H::Page::Practice)&&h.home->page()==H::Page::Practice&&A::visiblePages(*h.home)==1,"Home opens the visible Practice destination");
  ck(h.home->navigate(H::Page::Home)&&h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0,"Practice returns to the single visible Home destination");
  ck(h.home->navigate(H::Page::Freeplay)&&h.home->page()==H::Page::Freeplay&&A::visiblePages(*h.home)==1&&!A::freeplay(*h.home).active(),"Home opens stopped Freeplay without starting its clock");
  ck(h.home->navigate(H::Page::Home)&&h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0,"Freeplay returns to the single visible Home destination");
  ck(h.home->navigate(H::Page::Progress)&&h.home->page()==H::Page::Progress&&A::visiblePages(*h.home)==1,"Home opens the visible read-only Progress destination");
  h.wait([&]{return !A::progress(*h.home).busy();},"Progress read-only settles");
  ck(!A::progress(*h.home).busy(),"Home opens read-only Progress without a pending read");
  ck(h.home->navigate(H::Page::Home)&&h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0,"Progress returns to the single visible Home destination");
  ck(h.home->navigate(H::Page::Reference)&&h.home->page()==H::Page::Reference&&A::visiblePages(*h.home)==1,"Home opens the visible Reference destination");
  ck(h.home->navigate(H::Page::Home)&&h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0,"Reference returns to the single visible Home destination");
  h.home->openAudioSettings();ck(h.home->page()==H::Page::Audio&&h.home->settingsCaller()==H::Page::Home&&A::visiblePages(*h.home)==1,"Home opens one shared Audio settings surface");
  h.home->returnFromAudioSettings();ck(h.home->page()==H::Page::Home&&A::visiblePages(*h.home)==0,"shared Audio settings returns to its Home caller");
  ck(h.finals()==0&&!h.practice().captureSession()->startTaken()&&!A::freeplay(*h.home).active(),"route smoke creates no Practice or Freeplay activity");
  std::cout<<"PASS "<<checks<<" Home navigation smoke checks\n";return 0;
 }
 {Harness h(dir,"home-guidance");bool found=false;for(auto* child:h.home->getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))found=found||label->getText().toStdString().find("Start with Learn to browse the retained catalog and open an admitted case in Practice.")!=std::string::npos;ck(found,"Home states the current Learn-first admitted-case boundary");}
 if(freeplayContext)goto freeplay_context_only;
 freeplay_context_only:
 {Harness h(dir,"freeplay-context");h.setup();click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Freeplay route starts from Home");
  const auto ownerBeforeFreeplay=h.home->audioSettings().active();const int connectionsBeforeFreeplay=connections;
  ck(h.home->navigate(H::Page::Freeplay)&&h.home->page()==H::Page::Freeplay&&A::visiblePages(*h.home)==1,"standalone Freeplay route has one visible page");
  ck(h.home->audioSettings().active()==ownerBeforeFreeplay&&connections==connectionsBeforeFreeplay&&!A::freeplay(*h.home).active(),"Freeplay entry does not activate audio or timer");
  ck(A::freeplay(*h.home).persistenceConfigured(),"Home binds Freeplay to the existing local Store");
  auto* progressAction=dynamic_cast<juce::TextButton*>(A::freeplay(*h.home).findChildWithID("freeplay-open-progress"));
  ck(progressAction&&progressAction->getButtonText().toStdString()=="Open Progress"&&progressAction->getTitle().toStdString()=="Open read-only Progress; Freeplay history is not saved until Stop completes.","fresh Freeplay Progress action identifies the unsaved read-only boundary");
  auto beforeFreeplayPause=capture_fixture::confirmed(h.store->snapshot("freeplay-before-pause"));
  click(A::freeplay(*h.home),"Start freeplay");click(A::freeplay(*h.home),"Pause freeplay");
  auto afterFreeplayPause=capture_fixture::confirmed(h.store->snapshot("freeplay-after-pause"));
  ck(afterFreeplayPause.data.find("authoritative")->find("identity")->array().empty()
         && beforeFreeplayPause.data.find("authoritative")->find("identity")->array().empty(),"Freeplay entry and Pause do not write history");
  auto* resumeAction=dynamic_cast<juce::TextButton*>(A::freeplay(*h.home).findChildWithID("freeplay-start"));
  ck(resumeAction&&resumeAction->getButtonText().toStdString()=="Resume freeplay"&&resumeAction->getTitle().toStdString()=="Resume Freeplay and continue active-time capture without saving history","paused Freeplay keeps its visible Resume label and accessibility title aligned");
  progressAction=dynamic_cast<juce::TextButton*>(A::freeplay(*h.home).findChildWithID("freeplay-open-progress"));
  ck(progressAction&&progressAction->getTitle().toStdString()=="Open read-only Progress; Freeplay history is not saved until Stop completes.","paused Freeplay Progress action keeps the unsaved read-only boundary");
  click(A::freeplay(*h.home),"Resume freeplay");click(A::freeplay(*h.home),"Back");
  ck(h.home->page()==H::Page::Freeplay&&A::freeplay(*h.home).active(),"active Freeplay Back remains guarded");
  click(A::freeplay(*h.home),"Stop freeplay");
  ck(A::freeplay(*h.home).persistencePending(),"explicit Stop enters pending Freeplay save: "+A::freeplay(*h.home).persistenceStatus());
  ck(!h.home->requestClose()&&h.home->page()==H::Page::Freeplay,"pending Freeplay history save guards close");
  h.wait([&]{return A::freeplay(*h.home).persistenceSaved();},"Freeplay history save");
  progressAction=dynamic_cast<juce::TextButton*>(A::freeplay(*h.home).findChildWithID("freeplay-open-progress"));
  ck(progressAction&&progressAction->getButtonText().toStdString()=="Review Progress (read-only)"&&progressAction->getTitle().toStdString()=="Review saved Freeplay history in read-only Progress; no new activity or history is created.","saved Freeplay Progress action identifies finalized-history review");
  auto afterFreeplayStop=capture_fixture::confirmed(h.store->snapshot("freeplay-after-stop"));
  ck(afterFreeplayStop.data.find("authoritative")->find("identity")->array().size()==1
         && afterFreeplayStop.data.find("authoritative")->find("finalized")->array().size()==1,"explicit Stop finalizes one FreeplayActivity");
  ck(h.home->navigate(H::Page::Progress),"saved Freeplay opens existing Progress");h.wait([&]{return !A::progress(*h.home).busy();},"Freeplay Progress refresh");
  ck(A::progress(*h.home).presentation().text.find("Freeplay activity")!=std::string::npos,"Progress shows saved Freeplay distinctly");
  click(A::progress(*h.home),"Back");
  click(*h.home,"Freeplay");click(A::freeplay(*h.home),"Open rhythm tools");h.tick();
  ck(h.home->page()==H::Page::Metronome&&A::visiblePages(*h.home)==1&&!A::metronome(*h.home).soundPending()&&A::metronome(*h.home).audioSnapshot().state!=output::State::Running,"explicit rhythm route reuses stopped Metronome");
  const auto connectionsBeforeFreeplayPolyrhythm=connections;
  const auto beforeFreeplayPolyrhythm=capture_fixture::confirmed(h.store->snapshot("freeplay-before-polyrhythm"));
  auto freeplayPolyrhythm=A::metronome(*h.home).settings();
  freeplayPolyrhythm.polyrhythmEnabled=true;freeplayPolyrhythm.countIn=metronome::CountIn::Off;freeplayPolyrhythm.ramp.reset();freeplayPolyrhythm.x=5;freeplayPolyrhythm.y=7;
  ck(A::metronome(*h.home).applySettings(freeplayPolyrhythm)&&A::metronome(*h.home).settings().polyrhythmEnabled
         &&A::metronome(*h.home).settings().x==5&&A::metronome(*h.home).settings().y==7,"Freeplay route accepts existing stopped 5:7 polyrhythm host");
  const auto afterFreeplayPolyrhythm=capture_fixture::confirmed(h.store->snapshot("freeplay-after-polyrhythm"));
  const auto& beforeFreeplayHistory=beforeFreeplayPolyrhythm.data.object().at("authoritative");
  const auto& afterFreeplayHistory=afterFreeplayPolyrhythm.data.object().at("authoritative");
  bool sameFreeplayHistory=true;for(const auto* key:{"identity","finalized","pending","session","session_close"})
    sameFreeplayHistory=sameFreeplayHistory&&beforeFreeplayHistory.object().at(key)==afterFreeplayHistory.object().at(key);
  ck(connections==connectionsBeforeFreeplayPolyrhythm&&!A::metronome(*h.home).soundPending()
         &&A::metronome(*h.home).audioSnapshot().state!=output::State::Running
         &&sameFreeplayHistory,"Freeplay polyrhythm configuration adds no audio or Store history side effect");
  click(A::metronome(*h.home),"Back");
  ck(h.home->page()==H::Page::Freeplay&&A::visiblePages(*h.home)==1,"Metronome returns exactly to Freeplay");
  click(A::freeplay(*h.home),"Back");ck(h.home->page()==H::Page::Home,"stopped Freeplay returns Home");}
 if(freeplayContext)goto completed;
 {Harness h(dir,"practice-metronome-handoff");h.setup();
  const auto connectionsBeforePracticeMetronome=connections;
  const auto beforePracticeMetronome=capture_fixture::confirmed(h.store->snapshot("practice-before-metronome"));
  ck(h.practice().requestMetronome()&&h.home->page()==H::Page::Metronome&&A::visiblePages(*h.home)==1,"stopped Practice opens shared Metronome");
  auto practicePolyrhythm=A::metronome(*h.home).settings();practicePolyrhythm.polyrhythmEnabled=true;practicePolyrhythm.countIn=metronome::CountIn::Off;practicePolyrhythm.ramp.reset();practicePolyrhythm.x=5;practicePolyrhythm.y=7;
  ck(A::metronome(*h.home).applySettings(practicePolyrhythm)&&A::metronome(*h.home).settings().x==5&&A::metronome(*h.home).settings().y==7,"Practice handoff accepts existing stopped 5:7 polyrhythm host");
  const auto afterPracticeMetronome=capture_fixture::confirmed(h.store->snapshot("practice-after-metronome"));
  const auto& beforePracticeHistory=beforePracticeMetronome.data.object().at("authoritative");const auto& afterPracticeHistory=afterPracticeMetronome.data.object().at("authoritative");
  bool samePracticeHistory=true;for(const auto* key:{"identity","finalized","pending","session","session_close"})samePracticeHistory=samePracticeHistory&&beforePracticeHistory.object().at(key)==afterPracticeHistory.object().at(key);
  ck(connections==connectionsBeforePracticeMetronome+1&&maxClaims==1&&!A::metronome(*h.home).soundPending()&&A::metronome(*h.home).audioSnapshot().state!=output::State::Running&&samePracticeHistory,"Practice handoff keeps one stopped owner with no Store history");
  click(A::metronome(*h.home),"Back");ck(h.home->page()==H::Page::Practice&&A::visiblePages(*h.home)==1,"Metronome returns exactly to Practice");h.blocks(2);
  h.start();ck(!h.practice().requestMetronome()&&h.home->page()==H::Page::Practice&&h.practice().captureSession()->startTaken(),"active Practice refuses shared Metronome handoff");
  click(h.practice(),"Stop");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"active handoff guard cleanup");}
 {Harness h(dir,"home-and-links");const int before=connections;h.setup();ck(connections==before+1&&h.practice().outputStatus().lifecycle.state==output::State::Ready,"Home setup prepares actual Practice without duplicate connect");ck(!h.practice().captureSession()->startTaken()&&h.finals()==0,"setup no music or result");
  click(h.practice(),"Audio settings");h.tick();auto& settings=A::settings(*h.home);juce::Slider* master=nullptr;
  auto* sharedDescription=dynamic_cast<juce::Label*>(settings.findChildWithID("shared-audio-description"));
  ck(sharedDescription&&sharedDescription->getText().toStdString().find("shared settings apply across Learn, Practice, Freeplay and rhythm tools")!=std::string::npos
       && sharedDescription->getText().toStdString().find("Disconnect is enabled only when the current activity can be released safely.")!=std::string::npos,
     "Audio settings identify the shared scope and safe Disconnect boundary");
  for(auto* child:settings.getChildren())if(auto* slider=dynamic_cast<juce::Slider*>(child);slider&&slider->getTitle()=="Master volume")master=slider;
  ck(master!=nullptr,"actual common Master editor found");juce::Label* valueBox=nullptr;for(auto* child:master->getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))valueBox=label;ck(valueBox!=nullptr,"actual Slider value label");
  const auto enter=[&](const juce::String& text){valueBox->showEditor();auto* editor=valueBox->getCurrentTextEditor();if(!editor)throw std::runtime_error("value editor unavailable");editor->setText(text);valueBox->hideEditor(false);h.tick();};
  for(const auto* text:{"63junk","","101","-1","1.5","junk"}){enter(text);ck(master->getValue()==50&&h.home->audioSettings().selected().master==50,"invalid common volume retains prior: "+std::string(text));}
  enter("63");ck(master->getValue()==63&&h.home->audioSettings().selected().master==63,"next valid volume applies exactly");
  for(const auto title:{"Master mute","Reference mute","Metronome mute","Rhythm A mute","Rhythm B mute","Rhythm A solo","Rhythm B solo"}){juce::Button* control=nullptr;for(auto* child:settings.getChildren())if(auto* b=dynamic_cast<juce::Button*>(child);b&&b->getTitle()==title)control=b;ck(control!=nullptr,"actual common control "+std::string(title));activate(*control);h.blocks(1);ck(equal(h.practice().outputStatus().mix,h.home->audioSettings().selected()),"actual mute/solo callback join "+std::string(title));activate(*control);h.blocks(1);}
  click(settings,"Back to Practice");auto mix=h.home->audioSettings().selected();mix.master=37;mix.bus={13,27,41,89};mix.muteMask=3;mix.soloAB=2;ck(h.home->audioSettings().selectMix(mix),"distinct common mix accepted");h.blocks(1);ck(equal(h.practice().outputStatus().mix,mix),"actual callback publishes complete mix");h.image("practice-tab");h.detour();ck(h.home->page()==H::Page::Practice&&A::visiblePages(*h.home)==1,"Practice same caller one page");h.practice().setFocusMode(true);h.image("practice-focus");click(h.practice(),"Audio settings");h.tick();h.image("settings");ck(!h.practice().isShowing()&&h.home->settingsCaller()==H::Page::Practice,"settings hides original Focus");click(A::settings(*h.home),"Back to Practice");ck(h.practice().focusMode(),"Focus retained");h.practice().setFocusMode(false);click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"idle Back");
  for(auto entry:{std::pair{H::Page::Reference,"Reference tones"},std::pair{H::Page::Metronome,"Metronome"},std::pair{H::Page::Rhythm,"Rhythm preview"}}){click(*h.home,entry.second);h.blocks(2);h.tick();ck(h.home->page()==entry.first&&A::pollers(*h.home)&&h.home->audioSettings().snapshot().state==output::State::Ready,"handoff fresh Ready one drainer "+std::string(entry.second));ck(equal(A::output(*h.home).status().mix,mix),"common mix survives handoff "+std::string(entry.second));juce::Component* c=entry.first==H::Page::Reference?static_cast<juce::Component*>(&A::reference(*h.home)):entry.first==H::Page::Metronome?static_cast<juce::Component*>(&A::metronome(*h.home)):static_cast<juce::Component*>(&A::rhythm(*h.home));h.image(entry.second);click(*c,"Audio settings");h.tick();ck(A::visiblePages(*h.home)==1,"single settings surface "+std::string(entry.second));click(A::settings(*h.home),"Back to "+std::string(entry.second));ck(h.home->page()==entry.first,"exact return "+std::string(entry.second));click(*c,"Back");h.tick();ck(h.home->page()==H::Page::Home,"resolved activity Back "+std::string(entry.second));}
  ck(h.home->navigate(H::Page::Learn),"Learn route unchanged");h.home->openAudioSettings();h.home->openAudioSettings();click(A::settings(*h.home),"Back to Learn");ck(h.home->page()==H::Page::Learn,"repeated settings preserves Learn caller");
 }
 for(const auto& stage:{"idle","count-in","running","paused","review","after-save"}){Harness h(dir,std::string("detour-")+stage);h.setup();if(std::string(stage)!="idle"){h.start();h.blocks(std::string(stage)=="count-in"?10:400);if(std::string(stage)=="paused"){click(h.practice(),"Pause");h.blocks(1);}if(std::string(stage)=="review"||std::string(stage)=="after-save"){h.end();if(std::string(stage)=="after-save"){click(h.practice(),"Save result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"saved");}}}
  auto* object=&h.practice();const auto* capture=object->captureSession();const auto owner=capture->binding().owner;const auto phase=capture->phase();const auto state=object->outputStatus().lifecycle.state;const auto active=object->coordinator().activeFrames();const auto cycles=object->coordinator().completedCycles();const auto stamp=P::stopStamp(*object);const auto assessment=P::assessment(*object);const auto document=object->tabView().document();object->setFocusMode(true);const auto scroll=object->tabView().scrollPosition();
  if(stage!=std::string("idle")&&stage!=std::string("after-save")){click(h.practice(),"Audio settings");h.tick();const auto before=connections;ck(!h.home->audioSettings().connect()&&!h.home->audioSettings().disconnect()&&connections==before,"active/unresolved device changes refused "+std::string(stage));click(A::settings(*h.home),"Back to Practice");}
  h.detour();
  ck(&h.practice()==object&&object->captureSession()==capture&&capture->binding().owner==owner&&capture->phase()==phase,"same object original phase/identity "+std::string(stage));ck(object->outputStatus().lifecycle.state==state&&object->coordinator().activeFrames()==active&&object->coordinator().completedCycles()==cycles&&P::stopStamp(*object)==stamp,"detour emits no transport/facts "+std::string(stage));ck(object->focusMode()&&object->tabView().document()==document&&object->tabView().scrollPosition()==scroll&&P::assessment(*object)==assessment,"mode source scroll assessment preserved "+std::string(stage));if(std::string(stage)=="review")h.image("review-focus");
 }
 for(int mode=1;mode<=3;++mode){Harness h(dir,"save-detour-"+std::to_string(mode));h.setup();h.start();h.end();ck(h.practice().chooseAssessment("Clean"),"explicit Clean selected for save fixture");click(h.practice(),"Back");h.mode=mode;click(h.practice(),"Save & go back");h.wait([&]{return h.entered.load();},"save hook");if(mode<3)h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Failed;},"failure");const auto original=h.practice().captureSession()->original()->bytes;const auto owner=h.practice().captureSession()->binding().owner;if(mode==3){click(h.practice(),"Audio settings");h.tick();h.release=true;h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"save completes on settings");marker();ck(h.home->page()==H::Page::Audio,"live save completion cannot leave settings");click(A::settings(*h.home),"Back to Practice");h.tick();}else h.detour();marker();ck(h.home->page()==H::Page::Practice&&!P::intent(h.practice())&&!P::posted(h.practice()),"detour cancels queued return only "+std::to_string(mode));ck(h.practice().captureSession()->original()->bytes==original&&h.practice().captureSession()->binding().owner==owner,"immutable pending save "+std::to_string(mode));h.image("pending-save");if(mode==3){h.release=true;h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"saved after detour");ck(h.home->page()==H::Page::Practice,"completed save stays at original caller");click(h.practice(),"Go back");}else click(h.practice(),"Retry & go back");h.wait([&]{return h.home->page()==H::Page::Home;},"real Back after detour");ck(h.finals()==1&&h.practice().captureSession()->original()->bytes==original,"real Retry/Back original once "+std::to_string(mode));}
 remaining:
 {Harness h(dir,"observed-guidance");click(*h.home,"Audio settings");h.tick();auto& settings=A::settings(*h.home);auto* status=dynamic_cast<juce::Label*>(settings.findChildWithID("shared-audio-status"));ck(status!=nullptr,"Audio settings exposes its lifecycle status label");ck(h.home->audioSettings().snapshot().state==output::State::Closed&&status->getText().toStdString().find("Next action: choose Connect audio, then choose Enable audio; Start or Play in the current activity begins sound.")!=std::string::npos,"Closed Audio output state gives the exact Connect and Enable next actions");click(settings,"Connect audio");h.tick();ck(h.home->audioSettings().snapshot().state==output::State::Observed&&status->getText().toStdString().find("Output is connected and observed. Choose Enable audio to prepare; Start or Play in the current activity begins sound.")!=std::string::npos,"Observed Audio output state gives the explicit Enable preparation guidance");click(settings,"Back to Home");}
 {desktop::PracticeGuidanceInput i;i.attached=true;i.phase=capture::SessionPhase::Saved;i.canAgain=false;i.canLeave=true;i.outputCleared=true;i.receipt=storage::Status::Confirmed;ck(desktop::practiceGuidance(i).next.find("resolved")!=std::string::npos,"confirmed Saved return does not require Again eligibility");i.receipt=storage::Status::Unresolved;ck(desktop::practiceGuidance(i).next.find("unresolved")!=std::string::npos,"unknown late receipt still outstanding");i.receipt=storage::Status::Conflict;ck(desktop::practiceGuidance(i).next.find("overwritten")!=std::string::npos,"conflicting late receipt still protected");i.receipt=storage::Status::Confirmed;i.outputCleared=false;ck(desktop::practiceGuidance(i).status.find("cleanup")!=std::string::npos,"Saved result does not bypass output cleanup");}
 {Harness h(dir,"saved-return-guidance");h.setup();h.start();h.blocks(400);
  auto& practice=h.practice();const auto owner=practice.captureSession()->binding().owner;const auto session=practice.captureSessionId();const auto model=practice.tabView().document();
  const auto checkTransport=[&](const std::string& state){
   ck(stopCaptionFits(practice),state+" Stop caption fits immediately after the actual state transition");
   for(auto size:{std::pair{920,680},std::pair{1280,800}}){h.home->setSize(size.first,size.second);h.tick();ck(practice.tabVisible()&&stopCaptionFits(practice)&&transportContainedAndSeparate(practice),state+" TAB transport text and separate contained controls at "+std::to_string(size.first));}
   h.home->setSize(920,680);h.tick();
  };
  ck(practice.outputStatus().lifecycle.state==output::State::Running&&practice.canPerformCommand(desktop::PracticeCommand::Pause),"synthetic layout fixture reaches actual running transport");checkTransport("Running");
  click(practice,"Pause");h.blocks(1);h.wait([&]{return practice.outputStatus().lifecycle.state==output::State::Paused&&practice.canPerformCommand(desktop::PracticeCommand::Resume);},"software pause confirmed");checkTransport("Paused");
  ck(practice.captureSession()->binding().owner==owner&&practice.captureSessionId()==session&&practice.tabView().document()==model&&h.finals()==0,"running and paused layout retain the original Attempt Session and source without a save");
  click(practice,"Resume selected span");h.blocks(1);h.wait([&]{return practice.outputStatus().lifecycle.state==output::State::Running;},"software resume confirmed");
  ck(practice.captureSession()->binding().owner==owner&&practice.captureSessionId()==session&&practice.tabView().document()==model,"explicit Resume preserves the same software Attempt Session and source after layout checks");
  h.end();click(h.practice(),"Back");h.mode=3;click(h.practice(),"Save & go back");h.wait([&]{return h.entered.load();},"save barrier");click(h.practice(),"Audio settings");h.release=true;h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved&&h.practice().audioCanRelease();},"saved and cleanup while settings");marker();ck(h.home->page()==H::Page::Audio,"saved correction keeps settings caller");click(A::settings(*h.home),"Back to Practice");h.tick();ck(h.practice().saveStatusView().primaryText().find("original result is resolved")!=std::string::npos,"actual saved return panel guidance agrees with guard");h.image("resolved-return");click(h.practice(),"Go back");h.wait([&]{return h.home->page()==H::Page::Home;},"actual resolved return");ck(h.finals()==1,"resolved message does not create duplicate result");}
 remaining_after_transport:
 {Harness h(dir,"posted-return");h.setup();P::queueReturn(h.practice());ck(P::posted(h.practice()),"actual deferred return posted");h.home->openAudioSettings();marker();h.tick();ck(h.home->page()==H::Page::Audio&&!P::posted(h.practice())&&!P::intent(h.practice()),"old callback cannot send settings Home");h.home->returnFromAudioSettings();ck(h.home->page()==H::Page::Practice&&h.finals()==0,"posted idle return no inferred save");h.mode=4;ck(A::metronome(*h.home).savePreset("Pending target"),"pending target preference request");h.wait([&]{return h.entered.load();},"target preference barrier");P::queueReturn(h.practice());ck(!h.home->navigate(H::Page::Metronome),"pending target rejects before release");marker();ck(h.home->page()==H::Page::Audio&&!P::posted(h.practice()),"refused target uses same detour cancellation");h.release=true;h.wait([&]{return A::metronome(*h.home).preferencesReady();},"target preference settled");h.home->returnFromAudioSettings();
   const auto detachCheckpoint=[&](const std::string& stage){
    auto& guided=A::guided(*h.home);
    capture_fixture::write(h.dir/("detach-"+stage+".json"),storage::canonical(json::Value::Object{
     {"guided_busy",guided.busy()},{"guided_can_leave",guided.canLeave()},{"guided_running",guided.running()},
     {"guided_holds_session_operation",guided.holdsSessionOperation()},{"guided_session_id",guided.sessionId()},
     {"progress_busy",A::progress(*h.home).busy()},{"freeplay_can_leave",A::freeplay(*h.home).canLeave()},
     {"practice_audio_can_release",h.practice().audioCanRelease()},{"audio_can_release",h.home->audioSettings().canRelease()},
     {"metronome_preferences_ready",A::metronome(*h.home).preferencesReady()}}));
   };
   detachCheckpoint("before-guided-service");
   ck(!A::guided(*h.home).running()&&!A::guided(*h.home).holdsSessionOperation()&&A::guided(*h.home).sessionId().empty(),"detach fixture Guided reader owns no Session or musical operation");
   h.wait([&]{A::guided(*h.home).service();return A::guided(*h.home).canLeave();},"Guided summary settled before Store detach");
   detachCheckpoint("after-guided-service");
   ck(A::guided(*h.home).canLeave()&&!A::guided(*h.home).holdsSessionOperation(),"existing Guided summary read settles before detach without relaxing its guard");
   const auto old=A::practiceEndpoint(*h.home);ck(h.home->detachForStoreReopen(),"actual Store detach recreates Practice");ck(!old.valid()&&!old.release(),"borrowed old endpoint invalidated safely");ck(!h.home->navigate(H::Page::Metronome)&&h.home->audioSettings().snapshot().state==output::State::Closed,"pending reopen keeps output Closed and guards handoff");h.store.reset();storage::StoreOptions reopen;reopen.path=h.dir/"profile.sqlite";reopen.preferenceValidator=metronome::preferenceValidator;h.store=std::make_unique<storage::ProfileStore>(reopen);ck(h.home->configureCapture(*h.store,h.sessionId,"America/New_York"),"actual same-profile Store reopen and Home rebind");h.wait([&]{return A::metronome(*h.home).preferencesReady();},"reopened preference reconciliation");ck(h.home->navigate(H::Page::Metronome)&&h.home->audioSettings().snapshot().state==output::State::Closed,"reconciled reopen does not reuse prior enable intent");}
 {Harness h(dir,"metronome-mix-presets");h.setup();click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Back");click(*h.home,"Metronome");h.blocks(2);auto& v=A::metronome(*h.home);auto mix=h.home->audioSettings().selected();mix.master=37;mix.bus={13,27,41,89};mix.muteMask=15;mix.soloAB=2;ck(h.home->audioSettings().selectMix(mix),"metronome all bus mix selected");h.blocks(1);ck(v.settings().volumes==mix.bus&&v.settings().masterVolume==37,"metronome selected model joins common mix");h.mode=4;ck(v.savePreset("Mix Ω"),"public preset immutable write");h.wait([&]{return h.entered.load();},"preset barrier");const auto op=v.preferenceOperation(),bytes=v.preferencePayload();auto rejected=mix;rejected.master=63;ck(!h.home->audioSettings().selectMix(rejected)&&v.preferenceOperation()==op&&v.preferencePayload()==bytes&&equal(h.home->audioSettings().selected(),mix),"pending preferences blocks common change without payload mutation");h.release=true;h.wait([&]{return v.preferencesReady();},"preset done");ck(h.home->audioSettings().selectMix(rejected),"common change after confirmation");ck(v.restorePreset(v.preferences().presets.at(0).id),"explicit restore");h.blocks(1);ck(equal(h.home->audioSettings().selected(),mix)&&equal(v.outputStatus().mix,mix),"restore joins common values preserving Reference/Metronome mute bits");click(v,"Start");h.blocks(400);ck(equal(v.outputStatus().mix,mix),"Start preserves common gain and all mute bits");click(v,"Audio settings");h.tick();ck(!v.keyPressed(juce::KeyPress(juce::KeyPress::spaceKey))&&!v.keyPressed(juce::KeyPress(juce::KeyPress::escapeKey)),"hidden metronome cannot transport");click(A::settings(*h.home),"Back to Metronome");click(v,"Stop");h.blocks(1);h.wait([&]{return button(v,"Finish check").isEnabled();},"terminal");click(v,"Finish check");h.blocks(1);ck(v.audioCanRelease(),"metronome actual finish remains usable");}
 tail_cases:
 {Harness h(dir,"rhythm-cancel-finish");h.setup();click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Home;},"Back");click(*h.home,"Rhythm preview");h.blocks(2);auto& v=A::rhythm(*h.home);auto& output=A::output(*h.home);platform::OutputTestAccess::queued(output,true);click(v,"Start preview");click(v,"Back");platform::OutputTestAccess::block(output);A::inactiveFirst(*h.home);h.tick();ck(v.audioCanRelease()&&v.audioSnapshot().state==output::State::Closed,"inactive timers preserve actual kind71 canceled Start proof");ck(!A::rhythmOutput(*h.home).ownsOutcome,"cancel has no musical owner or practice");click(v,"Audio settings");h.tick();click(A::settings(*h.home),"Connect audio");h.tick();click(A::settings(*h.home),"Enable audio");h.blocks(1);click(A::settings(*h.home),"Back to Rhythm preview");click(v,"Start preview");h.blocks(1800);h.wait([&]{return button(v,"Finish check").isEnabled();},"rhythm terminal");const auto submitted=v.audioSnapshot().submittedFrames;click(v,"Finish check");h.blocks(1);ck(v.audioCanRelease()&&v.audioSnapshot().state==output::State::Closed,"Rhythm Finish resolves then closes");std::ofstream facts(h.dir/"retained-facts.tsv");facts<<"terminal_submitted\tretained_submitted\tcycles\tprocessed\treason\tfailed\n"<<submitted<<'\t'<<A::rhythmOutput(*h.home).submittedFrames<<'\t'<<A::rhythmFinal(*h.home).cursor.completedCycles<<'\t'<<A::rhythmFinal(*h.home).cursor.processedThrough<<'\t'<<int(A::rhythmFinal(*h.home).cursor.reason)<<'\t'<<A::rhythmFinal(*h.home).failed<<'\n';facts.close();ck(A::rhythmOutput(*h.home).submittedFrames==submitted,"Rhythm original submitted frames retained");ck(A::rhythmFinal(*h.home).cursor.completedCycles==4&&!A::rhythmFinal(*h.home).failed,"Rhythm final quiescent four completed cycles retained");}
 {Harness h(dir,"observed-refusal");click(*h.home,"Audio settings");h.tick();click(A::settings(*h.home),"Connect audio");h.tick();platform::OutputTestAccess::observedFrames(A::output(*h.home),1024);ck(!h.home->audioSettings().enable()&&h.home->audioSettings().snapshot().state==output::State::Observed,"unapproved actual physical buffer refuses ACK");}
 for(int field=0;field<7;++field){Harness h(dir,"route-change-"+std::to_string(field));h.setup();const auto old=capability;if(field==0)capability.uid+="changed";if(field==1)++capability.object;if(field==2)capability.rate=48000;if(field==3)capability.physicalFrames=1024;if(field==4)capability.outputChannels=4;if(field==5)++capability.minFrames;if(field==6)--capability.maxFrames;const int before=connections;ck(h.home->navigate(H::Page::Reference),"committed changed-route caller coherent");ck(h.home->page()==H::Page::Reference&&h.home->audioSettings().active()==desktop::SharedAudioSettings::Consumer::Reference&&connections==before&&!h.home->audioSettings().message().empty(),"changed descriptor refused no fallback "+std::to_string(field));capability=old;}
 {Harness h(dir,"fault-before-observe");h.setup();platform::OutputTestAccess::faulted(A::output(*h.home));ck(h.home->navigate(H::Page::Reference),"fault route can leave resolved original");ck(h.home->audioSettings().snapshot().state==output::State::Closed,"fault before controller observe never carries enable intent");}
 {Harness h(dir,"real-peer-keys");h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);h.home->setVisible(true);h.home->navigate(H::Page::Practice);auto& v=h.practice();v.grabKeyboardFocus();NSView* native=(__bridge NSView*)h.home->getPeer()->getNativeHandle();[native.window makeKeyAndOrderFront:nil];int invoked=0;v.onPracticeCommand=[&](desktop::PracticeCommand,bool,const std::string&){++invoked;};auto key=[&](NSString* text,unsigned short code,bool down){auto* e=[NSEvent keyEventWithType:down?NSEventTypeKeyDown:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:text charactersIgnoringModifiers:text isARepeat:NO keyCode:code];[NSApp sendEvent:e];};ck(v.isShowing(),"real peer Practice visible positive");key(@"f",3,true);key(@"f",3,false);ck(invoked==1&&v.focusMode(),"visible actual AppKit Focus command invoked");click(v,"Audio settings");key(@"f",3,true);key(@"f",3,false);key(@" ",49,true);key(@" ",49,false);key(@"\x1b",53,true);key(@"\x1b",53,false);ck(invoked==1&&!v.isShowing()&&v.focusMode(),"hidden Practice AppKit cannot transport/toggle");click(A::settings(*h.home),"Back to Practice");ck(v.isShowing()&&v.focusMode(),"caller visible and focused mode returns");h.home->removeFromDesktop();}
 completed:
 ck(nativeOpens==0&&maxClaims==1,"zero native opens; maximum one software claim");std::ofstream log(dir/"io-order.txt");for(const auto& s:ioLog)log<<s<<'\n';std::ofstream summary(dir/"summary.json");summary<<"{\"checks\":"<<checks<<",\"connections\":"<<connections<<",\"nativeOpens\":"<<nativeOpens<<",\"status\":\"PASS\"}\n";std::cout<<"PASS "<<checks<<" shared audio checks\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
