// Real component/button/Store paths with software observations only. No device is opened.
#include "platform/AudioOutputMac.mm"
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
 static void settings(PracticeView& v){v.visitAudioSettings();}
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
int main(int argc,char**argv){try{
 if(argc<2||std::filesystem::exists(argv[1]))return 2;const std::filesystem::path dir=argv[1];std::filesystem::create_directory(dir);juce::ScopedJuceInitialiser_GUI gui;int checks=0;std::ofstream log(dir/"checks.tsv");auto ck=[&](bool b,const char*t){++checks;log<<(b?"PASS":"FAIL")<<'\t'<<t<<'\n';log.flush();if(!b)throw std::runtime_error(t);};
 {Harness h(dir,"saved-late-audit-return");h.start();h.end();ck(h.view->saveSample(nullptr),"explicit Save before return");h.wait([&]{return h.view->captureSession()->phase()==capture::SessionPhase::Saved&&Access::canLeave(*h.view);},"saved outcome");const auto bytes=h.view->captureSession()->original()->bytes;h.mode=5;Access::late(*h.view);h.tick();h.wait([&]{return h.hookEntered.load();},"actual pending late audit");h.click("Back");ck(h.returns==0&&!Access::canLeave(*h.view)&&Access::panel(*h.view),"pending accepted late audit holds requested return");h.wait([&]{return h.returns==1;},"single requested return after original late audit");ck(h.view->captureSession()->original()->bytes==bytes&&h.finals()==1,"late acknowledgment returns once and preserves exact original final");for(int i=0;i<10;++i){h.tick();pump();}ck(h.returns==1,"completed destination is not delivered twice");}
 if(argc==3&&std::string(argv[2])=="--reproduce")return 0;
 {Harness h(dir,"queued-cancel-and-original-caller");Access::attach(*h.view);Access::queue(*h.view);Access::stay(*h.view);dispatched();h.tick();ck(h.returns==0&&!Access::intent(*h.view)&&h.finals()==0,"Stay cancels already queued destination without a write");int replacement=0;Access::queue(*h.view);h.view->onBack=[&]{++replacement;};dispatched();h.tick();ck(h.returns==1&&replacement==0,"queued callback uses the explicitly requested original caller");}
 {Harness h(dir,"settings-cancels-original-caller");Access::attach(*h.view);Access::queue(*h.view);Access::settings(*h.view);int current=0;h.view->onBack=[&]{++current;};Access::queue(*h.view);dispatched();h.tick();ck(h.returns==0&&current==1,"settings cancellation clears old destination before a fresh explicit return");}
 for(int mode:{1,2,3}){Harness h(dir,"save-return-fault-"+std::to_string(mode));h.start();h.end();h.click("Back");ck(h.returns==0&&h.finals()==0,"Back does not save or leave an unsaved original");h.mode=mode;h.click("SaveBack");const auto bytes=h.view->captureSession()->original()->bytes;if(mode==3){h.wait([&]{return h.view->captureSession()->feedback().code=="ACK_TIMEOUT";},"actual save acknowledgment timeout");ck(h.returns==0&&!Access::canLeave(*h.view),"uncertain original cannot release destination");h.savedReturn();}else{h.wait([&]{return h.view->captureSession()->phase()==capture::SessionPhase::Failed;},"actual failed save");ck(h.returns==0,"failed original stays held");h.click("RetryBack");h.savedReturn();}ck(h.view->captureSession()->original()->bytes==bytes&&h.finals()==1&&h.hits==1,"explicit original retry/ack returns once with immutable payload");}
 {Harness h(dir,"conflict");h.start();h.end();auto alternate=capture::makeEnvelope(h.view->coordinator(),h.view->captureSession()->binding(),"Clean",Access::outcome(*h.view));confirmed(h.store->seal(storage::newUuid(),alternate.owner,alternate.bytes));h.click("Back");h.click("SaveBack");h.wait([&]{return h.view->captureSession()->phase()==capture::SessionPhase::Failed;},"actual pending conflict");auto bytes=h.view->captureSession()->original()->bytes;ck(h.view->captureSession()->feedback().status==storage::Status::Conflict&&h.returns==0&&h.finals()==0,"real stored conflict cannot navigate or overwrite");h.click("RetryBack");h.wait([&]{return h.view->captureSession()->phase()==capture::SessionPhase::Failed;},"same conflict retry");ck(h.returns==0&&h.view->captureSession()->original()->bytes==bytes,"conflict retry retains exact original and requested destination");h.click("Stay");ck(!Access::intent(*h.view),"Stay cancels conflicted destination without discarding original");}
 {Harness h(dir,"cancel-during-save");h.start();h.end();h.click("Back");h.mode=3;h.click("SaveBack");h.wait([&]{return h.hits.load()==1;},"live save");auto bytes=h.view->captureSession()->original()->bytes;h.click("Stay");h.wait([&]{return h.view->captureSession()->phase()==capture::SessionPhase::Saved&&Access::canLeave(*h.view);},"saved after cancel");ck(h.returns==0&&h.view->captureSession()->original()->bytes==bytes&&h.finals()==1,"Stay during accepted save preserves final but cancels destination");}
 {Harness h(dir,"cleanup-failure");Access::attach(*h.view);Access::cleanupFailure(*h.view,true);h.click("Back");h.wait([&]{return Access::failed(*h.view);},"cleanup refusal");const auto stops=stopped;for(int i=0;i<10;++i){h.tick();pump();}ck(h.returns==0&&stopped==stops&&!Access::posted(*h.view),"cleanup failure does not loop or navigate");Access::cleanupFailure(*h.view,false);h.click("RetryBack");h.savedReturn();ck(h.finals()==0,"explicit cleanup retry returns without invented Attempt");}
 {Harness h(dir,"cancel-before-allocation");h.prepareAudio();h.mode=4;h.click("Start");h.wait([&]{return h.hookEntered.load();},"allocation barrier");ck(h.view->captureSession()->binding().owner.empty()&&!h.view->captureSession()->startTaken(),"original allocation is genuinely pending before Back");h.click("Back");ck(!h.view->captureSession()->startTaken()&&h.returns==0,"Back before allocation cannot start sound or leave early");h.hookRelease=true;h.blocks(1);h.review();h.click("SaveBack");h.savedReturn();ck(h.view->captureSession()->original()->active==Rational{}&&h.finals()==1,"explicit zero-active Save resolves original pending allocation once");}
 {Harness h(dir,"destroy-on-return");h.view->onBack=[&]{++h.returns;h.view.reset();};Access::queue(*h.view);dispatched();ck(h.returns==1&&!h.view,"one confirmed return callback may safely destroy its view");}
 ck(opened==0,"software fixture never opens physical audio");std::cout<<"PASS "<<checks<<" requested-return boundary checks\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
