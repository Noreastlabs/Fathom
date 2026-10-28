// Real component/button/Store paths with software observations only. No device is opened.
#include "../Source/platform/AudioOutputMac.mm"
#include "desktop/PracticeView.hpp"
#include "desktop/SchedulerView.hpp"
#include "desktop/AudioOutputView.hpp"
#include "practice_capture_fixtures.hpp"
#include <iostream>
#include <atomic>
#include <mutex>
using namespace fathom;
namespace {
int opened=0, stopped=0;
struct SoftwareDevice final:juce::AudioIODevice {
 SoftwareDevice():AudioIODevice("Synthetic software output — not hardware","test-only"){}
 juce::StringArray getOutputChannelNames()override{return {"L","R"};}juce::StringArray getInputChannelNames()override{return {};}
 juce::Array<double> getAvailableSampleRates()override{return {44100.0};}juce::Array<int> getAvailableBufferSizes()override{return {256};}
 int getDefaultBufferSize()override{return 256;}
 juce::String open(const juce::BigInteger&,const juce::BigInteger&,double,int)override{++opened;return "Test forbids open";}
 void close()override{}bool isOpen()override{return false;}void start(juce::AudioIODeviceCallback*)override{++opened;}
 void stop()override{++stopped;}bool isPlaying()override{return false;}juce::String getLastError()override{return {};}
 int getCurrentBufferSizeSamples()override{return 256;}double getCurrentSampleRate()override{return 44100;}int getCurrentBitDepth()override{return 32;}
 juce::BigInteger getActiveOutputChannels()const override{juce::BigInteger b;b.setRange(0,2,true);return b;}juce::BigInteger getActiveInputChannels()const override{return {};}
 int getOutputLatencyInSamples()override{return 0;}int getInputLatencyInSamples()override{return 0;}
};
void pump(){@autoreleasepool {CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.001,true);if(auto* e=[NSApp nextEventMatchingMask:NSEventMaskAny untilDate:[NSDate dateWithTimeIntervalSinceNow:0.001] inMode:NSDefaultRunLoopMode dequeue:YES])[NSApp sendEvent:e];}}
void activate(juce::Button& button){struct Listener final:juce::Button::Listener{bool delivered=false;void buttonClicked(juce::Button*)override{delivered=true;}} listener;button.addListener(&listener);button.triggerClick();const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(2);while(!listener.delivered&&std::chrono::steady_clock::now()<end)pump();button.removeListener(&listener);if(!listener.delivered)throw std::runtime_error("JUCE button delivery watchdog");}
void dispatched(){bool done=false;juce::MessageManager::callAsync([&]{done=true;});const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(2);while(!done&&std::chrono::steady_clock::now()<end)pump();if(!done)throw std::runtime_error("async marker watchdog");}
std::string utc(){return "2026-09-08T14:30:00Z";}
}
namespace fathom::platform {
struct OutputTestAccess {
 static void attach(AudioOutputMac& o,PracticePlayback& playback){auto& p=*o.p_;p.epoch=1;p.requested={44100,256};p.quiescent=true;p.device=std::make_unique<SoftwareDevice>();p.context=&playback;p.observer=PracticePlayback::observe;p.scheduled=PracticePlayback::render;
  nativeSequence=1;hub.epoch.store(1);hub.faultWord.store(tagged(1,0));hub.ioWord.store(tagged(1,87));hub.armed.store(false);hub.frames.store(256);
  if(!p.life.configure({1,1,{44100,256},87})||!p.life.announce({1,2,{44100,256}}))throw std::runtime_error("software configuration");
  p.latestQuery={1,1,4,3,{44100,256},256,87,87,87,44100,512,true,true,true,true,true};
  p.life.observe(p.latestQuery);p.view.lifecycle=p.life.snapshot();
 }
 static void block(AudioOutputMac& o){auto& p=*o.p_;if(!p.device)return;nativeEpoch=1;nativeObject=87;nativeFrames=256;++nativeSequence;std::array<float,256> l{},r{};float* outputs[]{l.data(),r.data()};juce::AudioIODeviceCallbackContext ctx{};p.audioDeviceIOCallbackWithContext(nullptr,0,outputs,2,256,ctx);}
 static void queued(AudioOutputMac& o,bool value){o.p_->quiescent=!value;}
 static void cleanupFailure(AudioOutputMac& o,bool fail){o.p_->cleanupFailed=fail;o.p_->view.cleanupFailed=fail;o.p_->lastError=fail?"Synthetic teardown fault (no OS call)":"";}
};
}
namespace fathom::desktop {
struct PracticeViewTestAccess {
 static bool boardLatch(const PracticeView& v){return v.boardAcceptOutput_;}
 static std::vector<PlaybackFretboardView::ActiveTone> acceptedBoardTones(const PracticeView& v){
  const auto& p=v.tabPlayback_.position();const auto live=v.output_.status().lifecycle;
  if(!v.model_||!v.boardAcceptOutput_||v.stopRequested_||!p.hasMusicalSample||v.coordinator_.state()!=practice::State::Running||live.state!=output::State::Running||!(live.owner==v.coordinator_.owner())||!(p.progress.owner==v.coordinator_.owner()))return {};
  return PracticeView::soundingTonesAt(*v.model_,v.coordinator_.timeline(v.coordinator_.owner()),p.cycle,p.sample);
 }
 static void haltTimer(PracticeView& v){v.stopTimer();}
 static void tick(PracticeView& v){v.timerCallback();}
 static void attach(PracticeView& v){platform::OutputTestAccess::attach(v.output_,v.playback_);v.refreshDisplay();}
 static void block(PracticeView& v){platform::OutputTestAccess::block(v.output_);v.timerCallback();}
 static void queued(PracticeView& v,bool value){platform::OutputTestAccess::queued(v.output_,value);}
 static void late(PracticeView& v){auto p=v.coordinator_.generations().back();p.sequence+=100;p.dispositionSequence=0;v.coordinator_.progress(p);}
 static void cleanupFailure(PracticeView& v,bool fail){platform::OutputTestAccess::cleanupFailure(v.output_,fail);}
 static juce::TextButton& button(PracticeView& v,const std::string& id){if(id=="Back")return v.back_;if(id=="SaveBack")return v.saveBack_;if(id=="RetryBack")return v.retryBack_;if(id=="Stay")return v.stay_;if(id=="Start")return v.start_;if(id=="Audio settings")return v.audioSettings_;if(id=="Pause")return v.pause_;if(id=="Stop")return v.stop_;if(id=="Again")return v.again_;throw std::runtime_error("unknown button");}
 static bool enableFromSharedSettings(PracticeView& v){return v.enableOutput();}
 static bool panel(const PracticeView& v){return v.returnPanel_;}static bool intent(const PracticeView& v){return v.returnAfterSave_;}static bool posted(const PracticeView& v){return v.returnPosted_;}static bool failed(const PracticeView& v){return v.returnFailed_;}
 static std::uint64_t stopStamp(const PracticeView& v){return v.lastStopRequestNs_;}
 static void queue(PracticeView& v){v.requestBack();} // queue race seam only; ordinary cases use triggerClick
 static void stay(PracticeView& v){v.stayHere();}
 static capture::Outcome outcome(const PracticeView& v){return *v.terminalOutcome_;}
 static bool terminal(const PracticeView& v){return v.terminalOutcome_.has_value();}
 static std::string returnText(const PracticeView& v){return v.returnStatus_.getText().toStdString();}
 static bool canLeave(const PracticeView& v){return v.canReturn();}
};
}
using Access=desktop::PracticeViewTestAccess;
using namespace capture_fixture;
struct Harness {
 std::filesystem::path dir;std::atomic<int> mode{0},hits{0};std::atomic<bool> hookEntered{false},hookRelease{false};std::mutex mutex;std::ofstream hooks;int audioSettingsVisits{};
 std::unique_ptr<storage::ProfileStore> store;std::unique_ptr<desktop::PracticeView> view;int returns{};
 Harness(const std::filesystem::path& base,const std::string& name):dir(base/name){std::filesystem::create_directory(dir);std::filesystem::permissions(dir,std::filesystem::perms::owner_all);hooks.open(dir/"store-hooks.tsv");storage::StoreOptions options;options.path=dir/"profile.sqlite";options.create=true;options.createdUtc=utc();
  options.diagnosticHook=[this](const std::string& phase,const std::string& op){std::lock_guard<std::mutex> lock(mutex);hooks<<phase<<'\t'<<op<<'\n';hooks.flush();const auto final=op.size()>=12&&op.compare(op.size()-12,12,".save.commit")==0;const auto current=mode.load();if(current==4&&phase=="before_operation"&&op.find(".allocate")!=std::string::npos){mode=0;hookEntered=true;const auto deadline=now()+6000;while(!hookRelease){if(now()>deadline)throw std::runtime_error("allocation barrier watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}}if(current==5&&phase=="before_operation"&&op.find(".late")!=std::string::npos){mode=0;++hits;hookEntered=true;std::this_thread::sleep_for(std::chrono::milliseconds(1300));}if(final&&((current==1&&phase=="before_commit")||(current==2&&phase=="after_commit")||(current==3&&phase=="before_commit"))){mode=0;++hits;if(current==3)std::this_thread::sleep_for(std::chrono::milliseconds(1300));else throw std::runtime_error(current==1?"TEST definite precommit failure":"TEST lost aftercommit acknowledgment");}};
  store=std::make_unique<storage::ProfileStore>(options);auto session=confirmed(store->createSession(storage::newUuid(),utc(),"America/New_York",{},O{{"synthetic_fixture",true}}));
  view=std::make_unique<desktop::PracticeView>();Access::haltTimer(*view);view->setSize(920,680);view->setVisible(true);view->showTab(true);view->configureCapture(*store,session.owner,utc,"America/New_York");view->onBack=[this]{++returns;};view->onAudioSettings=[this]{++audioSettingsVisits;};
 }
 ~Harness(){hookRelease=true;view.reset();store.reset();}
 void tick(){Access::tick(*view);}
 template<class F>void wait(F predicate,const std::string& label){const auto end=now()+7000;while(!predicate()){if(now()>end)throw std::runtime_error(label+" watchdog; phase="+capture::phaseText(view->captureSession()->phase())+" feedback="+view->captureSession()->feedback().code+" error="+view->error());tick();pump();}}
 void click(const std::string& name){tick();auto& b=Access::button(*view,name);if(!b.isVisible()||!b.isEnabled()||!view->getLocalBounds().contains(b.getBounds()))throw std::runtime_error(name+" not visible/enabled/in bounds");activate(b);tick();}
 void clickSaveDetails(){tick();auto& b=view->saveStatusView().detailsButton();if(!b.isVisible()||!b.isEnabled()||!view->getLocalBounds().contains(b.getBounds()))throw std::runtime_error("Save details not visible/enabled/in bounds");activate(b);tick();}
 void prepareAudio(){Access::attach(*view);click("Audio settings");if(audioSettingsVisits!=1)throw std::runtime_error("Practice did not hand off to shared Audio settings");if(!Access::enableFromSharedSettings(*view))throw std::runtime_error("synthetic shared Audio Enable acknowledgment");}
 void start(){prepareAudio();click("Start");wait([&]{return view->captureSession()->startTaken();},"start");}
 void blocks(int count){for(int i=0;i<count;++i)Access::block(*view);}
 void review(){wait([&]{return view->captureSession()->phase()==capture::SessionPhase::Review&&Access::terminal(*view);},"review");}
 void end(){blocks(1100);review();}
 void savedReturn(){wait([&]{return returns==1;},"save return");}
 std::size_t finals(){auto s=confirmed(store->snapshot(storage::newUuid()));write(dir/"snapshot.json",storage::canonical(s.data));return at(at(s.data,"authoritative"),"finalized").array().size();}
 void image(const std::string& label){tick();for(auto size:{std::pair{920,680},std::pair{1280,800}}){view->setSize(size.first,size.second);for(auto* c:view->getChildren())if(c->isVisible()&&dynamic_cast<juce::Button*>(c)&&!view->getLocalBounds().contains(c->getBounds()))throw std::runtime_error("visible button outside snapshot bounds");auto image=view->createComponentSnapshot(view->getLocalBounds());juce::FileOutputStream out(juce::File((dir/(label+"-"+std::to_string(size.first)+".png")).string()));juce::PNGImageFormat png;if(!out.openedOk()||!png.writeImageToStream(image,out))throw std::runtime_error("PNG");out.flush();}view->setSize(920,680);}
};
int main(int argc,char** argv){int checks=0;std::ofstream log;try{
 const bool supplemental=argc==3&&std::string(argv[2])=="--supplemental";if((argc!=2&&!supplemental)||!std::filesystem::path(argv[1]).is_absolute()||std::filesystem::exists(argv[1]))throw std::runtime_error("New absolute evidence directory required");const std::filesystem::path dir=argv[1];std::filesystem::create_directories(dir);log.open(dir/"checks.tsv");
 const auto ck=[&](bool b,const std::string& text){++checks;log<<text<<'\t'<<(b?"PASS":"FAIL")<<'\n';log.flush();if(!b)throw std::runtime_error(text);};
 const auto hasText=[](const std::string& text,const std::string& part){return text.find(part)!=std::string::npos;};
 const auto checkSeparateDetails=[&](Harness& h,const std::string& primary,const std::string& label){
  auto& status=h.view->saveStatusView();h.clickSaveDetails();const auto details=status.detailsView().getText().toStdString();
  ck(status.detailsVisible()&&status.detailsView().isVisible()&&status.detailsView().isReadOnly()&&details.rfind("Save details — read-only; no operation runs from this view.\n",0)==0,label+" opens separate read-only diagnostics");
  ck(details.size()<=16384&&details.find("\nPhase: ")!=std::string::npos&&details.find("\nCode: ")!=std::string::npos&&details.find("\nMessage: ")!=std::string::npos&&primary.find("Code: ")==std::string::npos&&primary.find("Message: ")==std::string::npos&&primary.find("TEST ")==std::string::npos,label+" diagnostic fields remain bounded and outside primary guidance");
  h.clickSaveDetails();
 };
 juce::ScopedJuceInitialiser_GUI gui;
 if(supplemental)goto deferred_checks;
 {Harness h(dir,"idle");h.image("audio-setup");h.click("Back");h.wait([&]{return h.returns==1;},"idle return");ck(h.finals()==0,"idle Back creates no practice");}
 {Harness h(dir,"natural");h.start();h.end();ck(h.view->coordinator().completedCycles()==2,"natural two cycles");h.click("Back");ck(h.returns==0&&Access::panel(*h.view)&&h.finals()==0,"Back reveals Save; never implicitly saves");h.image("tab-return");h.view->setFocusMode(true);h.image("focus-return");h.click("SaveBack");h.savedReturn();const auto& e=*h.view->captureSession()->original();write(h.dir/"original.json",e.bytes);ck(!e.assessment&&e.active==Rational{4}&&h.finals()==1,"natural exact facts default null assessment final once");ck(h.view->outputStatus().lifecycle.state==output::State::Closed,"return disconnects without restart");h.view->setFocusMode(false);h.view->showTab(true);h.click("Again");ck(h.view->captureSession()->phase()==capture::SessionPhase::Idle&&h.finals()==1,"reentry explicit Again; original not duplicated");ck(!h.view->canPerformCommand(desktop::PracticeCommand::Start),"reentry requires explicit audio setup no autoplay");}
 for(const auto& name:{"manual-note","count-in","paused","stay","repeat-back"}){Harness h(dir,name);h.start();h.blocks(std::string(name)=="count-in"?10:400);if(std::string(name)=="manual-note")h.image("playing-low-E");if(std::string(name)=="paused"){h.click("Pause");h.blocks(1);}
  if(std::string(name)=="manual-note")ck(!h.view->requestClose()&&Access::panel(*h.view),"external close reveals unresolved result controls");h.click("Back");const auto stamp=Access::stopStamp(*h.view);h.click("Back");ck(Access::stopStamp(*h.view)==stamp,"repeated Back retains first Stop "+std::string(name));h.blocks(1);h.review();
  ck(h.returns==0&&!h.view->canPerformCommand(desktop::PracticeCommand::Start)&&!h.view->canPerformCommand(desktop::PracticeCommand::Again),"unresolved outcome blocks new work "+std::string(name));
  if(std::string(name)=="stay"){const auto owner=h.view->captureSession()->binding().owner;h.click("Stay");ck(!Access::intent(*h.view)&&!Access::panel(*h.view)&&h.view->captureSession()->binding().owner==owner,"Stay keeps original and cancels only navigation");h.click("Back");}
  if(std::string(name)=="stay")ck(h.view->chooseAssessment("Clean"),"explicit assessment choice");h.click("SaveBack");h.savedReturn();const auto& e=*h.view->captureSession()->original();write(h.dir/"original.json",e.bytes);ck((std::string(name)=="stay"?e.assessment==std::optional<std::string>{"Clean"}:!e.assessment)&&h.finals()==1&&h.view->coordinator().completedCycles()==0,"partial facts stay partial "+std::string(name));ck(std::string(name)=="count-in"?e.active==Rational{}:e.active.numerator()>0,"count-in excluded / running retained "+std::string(name));
 }
 for(int mode=1;mode<=3;++mode){Harness h(dir,"save-"+std::to_string(mode));h.start();h.end();h.click("Back");h.mode=mode;h.click("SaveBack");const auto bytes=h.view->captureSession()->original()->bytes;
  if(mode==3){h.wait([&]{return h.view->captureSession()->feedback().code=="ACK_TIMEOUT";},"timeout");const auto primary=h.view->saveStatusView().primaryText();const auto& save=Access::button(*h.view,"SaveBack");const auto& retry=Access::button(*h.view,"RetryBack");const auto& stay=Access::button(*h.view,"Stay");
   ck(h.returns==0&&!save.isEnabled()&&!retry.isEnabled()&&stay.isVisible()&&stay.isEnabled()&&!Access::canLeave(*h.view)&&!h.view->canPerformCommand(desktop::PracticeCommand::Again),"timeout retains future; only Stay is available while original save is unresolved");
   ck(hasText(primary,"Save not yet confirmed.")&&hasText(primary,"Wait for the original save")&&!hasText(primary,"Result saved")&&!hasText(primary,"Attempt is saved")&&h.view->captureSession()->original()&&h.view->captureSession()->original()->bytes==bytes,"timeout primary guidance waits without claiming save and retains exact original");
   ck(hasText(Access::returnText(*h.view),"Stay")&&!hasText(Access::returnText(*h.view),"Result resolved."),"timeout return guidance does not claim navigation readiness");checkSeparateDetails(h,primary,"timeout");h.savedReturn();}
  else {h.wait([&]{return h.view->captureSession()->phase()==capture::SessionPhase::Failed;},"failed save");const auto primary=h.view->saveStatusView().primaryText();const auto& save=Access::button(*h.view,"SaveBack");const auto& retry=Access::button(*h.view,"RetryBack");const auto& stay=Access::button(*h.view,"Stay");
   ck(h.returns==0&&h.hits==1,"failed/unknown save cannot navigate "+std::to_string(mode));
   ck(hasText(primary,"Original result is retained; save is not confirmed.")&&hasText(primary,"Retry original to reconcile")&&!hasText(primary,"Result saved")&&!hasText(primary,"Attempt is saved")&&h.view->captureSession()->original()&&h.view->captureSession()->original()->bytes==bytes,"failed save primary guidance retains original without fabricated success "+std::to_string(mode));
   ck(!save.isEnabled()&&retry.isVisible()&&retry.isEnabled()&&stay.isVisible()&&stay.isEnabled()&&!h.view->canPerformCommand(desktop::PracticeCommand::Again)&&hasText(Access::returnText(*h.view),"Stay")&&!hasText(Access::returnText(*h.view),"Result resolved."),"failed save Retry/Stay controls align; Save/Again remain unavailable "+std::to_string(mode));
   checkSeparateDetails(h,primary,"failed save "+std::to_string(mode));h.image("retry-tab");h.view->setFocusMode(true);h.image("retry-focus");h.click("RetryBack");h.savedReturn();}
  ck(h.hits==1&&h.view->captureSession()->original()->bytes==bytes&&h.finals()==1,"original immutable; one actual final receipt "+std::to_string(mode));write(h.dir/"original.json",bytes);
 }
 {Harness h(dir,"conflict");h.start();h.end();const auto alternate=capture::makeEnvelope(h.view->coordinator(),h.view->captureSession()->binding(),"Clean",Access::outcome(*h.view));confirmed(h.store->seal(storage::newUuid(),alternate.owner,alternate.bytes));h.click("Back");h.click("SaveBack");h.wait([&]{return h.view->captureSession()->phase()==capture::SessionPhase::Failed;},"conflict");const auto original=h.view->captureSession()->original()->bytes;const auto primary=h.view->saveStatusView().primaryText();const auto& save=Access::button(*h.view,"SaveBack");const auto& retry=Access::button(*h.view,"RetryBack");const auto& stay=Access::button(*h.view,"Stay");
  ck(h.view->captureSession()->feedback().status==storage::Status::Conflict&&h.returns==0&&h.finals()==0,"actual pending conflict refuses navigation/final");
  ck(hasText(primary,"Stored data conflicts; no overwrite is allowed.")&&hasText(primary,"Retry original to reconcile the same result")&&hasText(primary,"keep this preview open")&&!hasText(primary,"Result saved")&&!h.view->canPerformCommand(desktop::PracticeCommand::Again)&&h.view->captureSession()->original()->bytes==original,"conflict guidance forbids overwrite and retains exact original result");
  ck(!save.isEnabled()&&retry.isVisible()&&retry.isEnabled()&&stay.isVisible()&&stay.isEnabled()&&hasText(Access::returnText(*h.view),"Stay")&&!hasText(Access::returnText(*h.view),"Result resolved."),"conflict exposes Retry/Stay and no Save or resolved navigation");
  checkSeparateDetails(h,primary,"conflict");write(h.dir/"ui-original.json",original);write(h.dir/"pending-alternate.json",alternate.bytes);h.click("RetryBack");h.wait([&]{return h.view->captureSession()->phase()==capture::SessionPhase::Failed;},"repeat conflict");ck(h.returns==0&&h.view->captureSession()->original()->bytes==original,"retry cannot replace conflicting original");h.click("Stay");}
 {Harness h(dir,"cancel-before-allocation");h.prepareAudio();h.mode=4;h.click("Start");h.wait([&]{return h.hookEntered.load();},"allocation barrier");ck(h.view->captureSession()->binding().owner.empty()&&!h.view->captureSession()->startTaken(),"actual allocation pending at Back");h.click("Back");ck(!h.view->captureSession()->startTaken()&&h.returns==0,"pending allocation cancelled without sound/leave");h.hookRelease=true;h.blocks(1);h.review();h.click("SaveBack");h.savedReturn();ck(h.view->captureSession()->original()->active==Rational{}&&h.finals()==1,"pending-allocation cancellation has zero active facts");}
 {Harness h(dir,"queued-stop");h.start();h.blocks(400);Access::queued(*h.view,true);activate(Access::button(*h.view,"Back"));const auto stamp=Access::stopStamp(*h.view);ck(stamp>0&&h.view->outputStatus().lifecycle.state==output::State::Running,"first Back queues Stop while still Running");activate(Access::button(*h.view,"Back"));ck(Access::stopStamp(*h.view)==stamp,"second Back before callback preserves first request");Access::queued(*h.view,false);h.blocks(1);h.review();h.click("SaveBack");h.savedReturn();ck(h.finals()==1,"queued Stop saved once");}
 {Harness h(dir,"stay-during-save-and-late-audit");h.start();h.end();h.click("Back");h.mode=3;h.click("SaveBack");h.wait([&]{return h.hits.load()==1;},"live save");const auto bytes=h.view->captureSession()->original()->bytes;h.click("Stay");h.wait([&]{return h.view->captureSession()->phase()==capture::SessionPhase::Saved&&Access::canLeave(*h.view);},"saved after Stay");ck(h.returns==0&&h.view->captureSession()->original()->bytes==bytes,"Stay while save future lives retains final but cancels return");h.mode=5;Access::late(*h.view);h.tick();h.wait([&]{return h.hookEntered.load();},"late audit");h.click("Back");ck(h.returns==0&&!Access::canLeave(*h.view)&&Access::panel(*h.view),"Saved receipt cannot bypass actual pending late audit");h.wait([&]{return Access::canLeave(*h.view);},"late audit acknowledgment");h.click("Back");h.savedReturn();ck(h.view->captureSession()->original()->bytes==bytes&&h.finals()==1,"late audit acknowledged separately; original immutable");}

 deferred_checks:
 {Harness h(dir,"queued-stay");h.prepareAudio();Access::queue(*h.view);ck(Access::posted(*h.view)&&!h.view->canPerformCommand(desktop::PracticeCommand::Start),"queued Back blocks Start before dispatch");Access::stay(*h.view);dispatched();h.tick();ck(h.returns==0&&!Access::intent(*h.view)&&h.finals()==0,"Stay invalidates already queued return");}
 {Harness h(dir,"cleanup-failure");Access::attach(*h.view);Access::cleanupFailure(*h.view,true);h.click("Back");h.wait([&]{return Access::failed(*h.view);},"cleanup failure");const auto stopCount=stopped;for(int i=0;i<20;++i){h.tick();pump();}ck(stopped==stopCount&&h.returns==0&&!Access::intent(*h.view)&&!Access::posted(*h.view)&&Access::panel(*h.view),"teardown failure never schedules automatic retries; persistent panel");h.image("cleanup-failure");ck(Access::button(*h.view,"Stay").isVisible()&&Access::button(*h.view,"RetryBack").isEnabled(),"explicit cleanup Retry and Stay reachable");Access::cleanupFailure(*h.view,false);h.click("RetryBack");h.savedReturn();ck(h.finals()==0,"explicit cleanup retry only; no fabricated attempt");}
 {Harness h(dir,"destroy-on-return");h.view->onBack=[&]{++h.returns;h.view.reset();};Access::button(*h.view,"Back").triggerClick();const auto end=now()+2000;while(h.view&&now()<end)pump();ck(h.returns==1&&!h.view,"deferred callback may destroy view safely");}
 {Harness h(dir,"destroy-before-return");Access::queue(*h.view);h.view.reset();dispatched();ck(h.returns==0,"destroyed view invalidates queued callback");}
 {desktop::SchedulerView rhythm;desktop::AudioOutputView audio;for(auto* view:std::initializer_list<juce::Component*>{&rhythm,&audio})for(auto size:{std::pair{920,680},std::pair{1280,800}}){view->setSize(size.first,size.second);view->setVisible(true);const auto id=std::string(view==&rhythm?"rhythm-copy-":"audio-copy-")+std::to_string(size.first);for(auto* c:view->getChildren())if(c->isVisible()&&dynamic_cast<juce::Button*>(c))ck(view->getLocalBounds().contains(c->getBounds()),id+" visible button bounds");auto image=view->createComponentSnapshot(view->getLocalBounds());juce::FileOutputStream out(juce::File((dir/(id+".png")).string()));juce::PNGImageFormat png;ck(out.openedOk()&&png.writeImageToStream(image,out),id+" image");out.flush();}}
 ck(opened==0,"zero native device opens/starts in entire sequence");std::cout<<"PASS "<<checks<<" navigation checks; real Store/component, software callbacks only\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
