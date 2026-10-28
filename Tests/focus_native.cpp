#if defined(FATHOM_APP_WIRED_FOCUS)

// Compile the existing Home/Store/software-device harness into a separate
// native Focus executable. The retained campaign main is never called here.
#define main retained_shared_audio_campaign_main
#include "shared_audio_settings_tests.cpp"
#undef main

#include <algorithm>
#include <fstream>
#include <vector>

int main(int argc, char** argv) {
 int checks=0;
 try {
  if(argc!=4 || std::string(argv[1])!="--app-wired-focus")
   throw std::runtime_error("Usage: fathom_focus_app_native --app-wired-focus <absolute bundle> <new absolute output>");
  const std::filesystem::path bundle=argv[2],root=argv[3];
  if(!bundle.is_absolute()||!root.is_absolute()||std::filesystem::exists(root)||!std::filesystem::is_directory(bundle))
   throw std::runtime_error("Absolute bundle and fresh absolute output directory required");
  std::filesystem::create_directory(root);
  std::filesystem::permissions(root,std::filesystem::perms::owner_all);
  std::ofstream checksFile(root/"checks.tsv"),keys(root/"keys.tsv"),factsFile(root/"visible-facts.txt");
  auto ck=[&](bool okay,const std::string& label){++checks;checksFile<<label<<'\t'<<(okay?"PASS":"FAIL")<<'\n';checksFile.flush();if(!okay)throw std::runtime_error(label);};
  [NSApplication sharedApplication];
  [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
  juce::ScopedJuceInitialiser_GUI gui;
  Harness h(root,"app-wired");
  h.home->setSize(920,680);
  h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);
  h.home->setVisible(true);
  ck(A::lessons(*h.home).load(bundle),"retained representative bundle loads in actual Home/Learn view");
  click(*h.home,"Learn");
  auto& learn=A::lessons(*h.home);
  ck(h.home->page()==H::Page::Learn&&learn.catalog(),"Home Learn button opens loaded Learn page");
  const auto& lessons=learn.catalog()->lessons();
  const auto lesson=std::find_if(lessons.begin(),lessons.end(),[](const auto& item){return item.id=="fg:item:000002";});
  ck(lesson!=lessons.end(),"admitted L3 case exists in retained catalog");
  auto* lessonCombo=dynamic_cast<juce::ComboBox*>(learn.findChildWithID("lessons"));
  auto* variantCombo=dynamic_cast<juce::ComboBox*>(learn.findChildWithID("variants"));
  ck(lessonCombo&&variantCombo,"Learn exposes actual case and variant selection controls");
  lessonCombo->setSelectedItemIndex(static_cast<int>(lesson-lessons.begin()),juce::sendNotificationSync);
  const auto variant=std::find_if(lesson->variants.begin(),lesson->variants.end(),[](const auto& item){return item.id=="fg:variant:000006";});
  ck(variant!=lesson->variants.end(),"admitted L3 variant exists in retained catalog");
  variantCombo->setSelectedItemIndex(static_cast<int>(variant-lesson->variants.begin()),juce::sendNotificationSync);
  const auto admission=learn.catalog()->admit("fg:item:000002","fg:variant:000006");
  ck(admission&&admission->practiceAllowed()&&learn.selectedLesson()=="fg:item:000002"&&learn.selectedVariant()=="fg:variant:000006",
     "Learn selected case has original admitted L3 practice identity");
  const auto& identity=admission->identity().object();
  ck(identity.at("content_version").string()=="representative-controls.1"&&
     storage::canonical(identity.at("content_revision"))=="2"&&
     admission->model()->source().sourceRefs==std::vector<std::string>{"L3-TXT5-21","L3-TXT28-46"},
     "admitted L3 retains exact source references and content version");
  const auto before=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
  const auto beforeAuthority=storage::canonical(*before.data.find("authoritative"));
  const auto beforeNative=nativeOpens;
  click(learn,"Practice selected case");
  h.wait([&]{return h.home->page()==H::Page::Practice;},"Learn-to-Practice app route");
  auto& practice=h.practice();
  ck(practice.lessonAdmission()&&
     storage::canonical(practice.lessonAdmission()->identity())==storage::canonical(admission->identity())&&
     practice.captureSessionId()==h.sessionId&&practice.captureSession()&&
     practice.captureSession()->phase()==capture::SessionPhase::Idle,
     "app Practice callback preserves exact L3 admission and original Session");
  ck(practice.tabVisible()&&practice.tabView().isVisible()&&practice.tabView().document()&&
     practice.tabView().document()->source().events.size()==admission->model()->source().events.size(),
     "authored TAB is visible in app Practice before Focus");
  ck(practice.outputStatus().lifecycle.state==output::State::Closed&&!practice.captureSession()->startTaken(),
     "app route begins stopped with no Attempt or native output");
  auto* peer=practice.getPeer();NSView* native=peer?(__bridge NSView*)peer->getNativeHandle():nil;
  ck(native&&native.window&&practice.isShowing(),"Practice has a visible native window");
  [NSApp activateIgnoringOtherApps:YES];[native.window makeKeyAndOrderFront:nil];practice.grabKeyboardFocus();
  const auto focusDeadline=capture_fixture::now()+2000;
  while((![NSApp isActive]||!native.window.isKeyWindow||!practice.hasKeyboardFocus(false))&&capture_fixture::now()<focusDeadline)pump();
  ck([NSApp isActive]&&native.window.isKeyWindow&&practice.hasKeyboardFocus(false),
     "foreground app, key window and Practice keyboard focus are active");
  std::vector<desktop::PracticeKeyObservation> observed;
  int invocations=0;keys<<"key\thardware\tdown\trepeat\tmatched\tvisible\tconsumed\tinvoked\n";
  practice.onKeyObservation=[&](const desktop::PracticeKeyObservation& event){
   observed.push_back(event);invocations+=event.invoked;
   keys<<event.key<<'\t'<<event.hardwareKey<<'\t'<<event.down<<'\t'<<event.repeat<<'\t'
       <<event.matchedWindow<<'\t'<<event.visible<<'\t'<<event.consumed<<'\t'<<event.invoked<<'\n';
  };
  const auto send=[&](NSString* value,unsigned short code,bool down){
   auto* event=[NSEvent keyEventWithType:down?NSEventTypeKeyDown:NSEventTypeKeyUp location:NSZeroPoint
      modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber
      context:nil characters:value charactersIgnoringModifiers:value isARepeat:NO keyCode:code];
   [NSApp sendEvent:event];
  };
  const auto tap=[&](NSString* value,unsigned short code){send(value,code,true);send(value,code,false);};
  tap(@"f",3);
  ck(practice.focusMode()&&practice.tabVisible()&&invocations==1&&observed.size()==2,
     "foreground constructed F enters app-wired Focus once");
  const auto focusFacts=practice.focusFacts();
  factsFile<<focusFacts<<'\n';
  ck(focusFacts.find("Selected: 60 BPM")!=std::string::npos&&
     focusFacts.find("Current: 60 BPM")!=std::string::npos&&
     focusFacts.find("Target:")!=std::string::npos&&focusFacts.find("Scheduled:")!=std::string::npos&&
     focusFacts.find("Practice owner Session: "+h.sessionId)!=std::string::npos,
     "visible Focus facts include current/selected BPM, loop target/schedule and original Session");
  ck(practice.tabView().isVisible()&&practice.tabView().document()&&
     practice.tabView().document()->source().events.size()==admission->model()->source().events.size(),
     "Focus keeps the actual authored TAB visible");
  h.image("foreground-focus");
  tap(@" ",49);
  ck(invocations==2&&practice.outputStatus().lifecycle.state==output::State::Closed&&
     !practice.commandFeedback().empty(),"foreground Space visibly refuses Start while output is Closed");
  tap(@"c",8);
  ck(invocations==3&&practice.commandFeedback().find("Clean requires an ended result")!=std::string::npos,
     "foreground Clean visibly refuses before Review");
  tap(@"a",0);
  ck(invocations==4&&practice.commandFeedback().find("Again requires confirmed persistence")!=std::string::npos,
     "foreground Again visibly refuses before a saved result");
  h.image("refused-focus");
  ck(practice.captureSession()->phase()==capture::SessionPhase::Idle&&
     !practice.captureSession()->startTaken()&&practice.coordinator().completedCycles()==0&&
     practice.captureSessionId()==h.sessionId,"refused commands leave zero Attempt/cycle and original Session");
  tap(@"f",3);
  ck(!practice.focusMode()&&invocations==5&&observed.size()==10,
     "second foreground F exits Focus without duplicate invocation");
  for(const auto& key:observed)
   ck(key.matchedWindow&&key.visible&&key.invoked==key.down,
      "each constructed key matches the foreground Practice window and invokes only on key down");
  click(practice,"Back");
  h.wait([&]{return h.home->page()==H::Page::Learn;},"Focus Back to Learn");
  ck(learn.selectedLesson()=="fg:item:000002"&&learn.selectedVariant()=="fg:variant:000006"&&
     practice.captureSessionId()==h.sessionId,"Back returns to original Learn source and Session");
  const auto after=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
  ck(storage::canonical(*after.data.find("authoritative"))==beforeAuthority&&
     after.data.find("authoritative")->find("finalized")->array().empty()&&
     nativeOpens==beforeNative&&h.finals()==0,
     "Focus keyboard route leaves Store authority unchanged, zero finalized Attempts and zero native opens");
  ck(h.home->requestClose(),"app route closes cleanly");
  checksFile.flush();keys.flush();factsFile.flush();
  ck(checksFile.good()&&keys.good()&&factsFile.good(),"Focus evidence flushed");
  std::ofstream(root/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks
      <<",\"source\":\"fg:item:000002/fg:variant:000006\",\"session\":\""<<h.sessionId
      <<"\",\"appWiredHomeLesson\":true,\"foregroundActiveKeyWindow\":true,\"constructedKeyEvents\":true,"
      <<"\"physicalUserKeyDelivery\":\"NOT RUN\",\"attemptCreated\":false,\"nativeOpens\":0}\n";
  std::cout<<"PASS "<<checks<<" app-wired foreground Focus checks; constructed keys, physical guitar-held input NOT RUN\n";
  return 0;
 } catch(const std::exception& error) {
  std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<'\n';return 1;
 }
}

#else

#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CoreFoundation.h>
#include <array>
#include <atomic>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <filesystem>
#include <set>
#include <chrono>
#include <typeinfo>
namespace {
constexpr std::size_t captureLimit=192000*50*2;
std::array<float,captureLimit> captured{};std::size_t captureCount{};std::atomic<bool> captureOverflow{false};
struct CaptureBlock {std::uint64_t serial{},offset{};std::uint32_t epoch{},object{},frames{},buffer{},channels{},floats{};};
std::array<CaptureBlock,100000> captureBlocks{};std::size_t captureBlocksCount{};
void captureNative(int,const AudioBufferList*)noexcept;
}
#define FATHOM_TEST_NATIVE_CAPTURE captureNative
#include "../Source/platform/AudioOutputMac.mm"
#include "desktop/PracticeView.hpp"
#include "desktop/PracticeKeyboardMac.hpp"
#include "practice_capture_fixtures.hpp"
#include <ctime>
#include <vector>
using namespace fathom;
namespace {
void captureNative(int epoch,const AudioBufferList* data)noexcept {
 if(!data)return;
 for(UInt32 b=0;b<data->mNumberBuffers;++b){const auto& x=data->mBuffers[b];if(!x.mData)continue;const auto n=x.mDataByteSize/sizeof(float);
  if(n>captureLimit-captureCount || captureBlocksCount==captureBlocks.size()){captureOverflow.store(true);return;}
  captureBlocks[captureBlocksCount++]={platform::nativeSequence,captureCount,static_cast<std::uint32_t>(epoch),platform::nativeObject,platform::nativeFrames,b,x.mNumberChannels,static_cast<std::uint32_t>(n)};
  const auto* samples=static_cast<const float*>(x.mData);for(UInt32 i=0;i<n;++i)captured[captureCount++]=samples[i];
 }
}
std::string hexText(const char* p){constexpr char h[]="0123456789abcdef";std::string s;for(std::size_t i=0;i<160&&p[i];++i){const auto b=static_cast<unsigned char>(p[i]);s+=h[b>>4];s+=h[b&15];}return s;}
std::string uuid(const scheduler::Owner& o){constexpr char h[]="0123456789abcdef";std::string s;for(auto b:o.id){s+=h[b>>4];s+=h[b&15];}return s;}
std::string utcNow(){const auto n=std::time(nullptr);std::tm t{};gmtime_r(&n,&t);char s[32]{};std::strftime(s,sizeof(s),"%Y-%m-%dT%H:%M:%SZ",&t);return s;}
struct Expected {std::string uid;std::uint32_t rate,physical,min,max,channels;};
bool matches(const Expected& e,const platform::OutputCapability& c){return c.valid&&c.uid==e.uid&&c.rate==e.rate&&c.physicalFrames==e.physical&&c.minFrames==e.min&&c.maxFrames==e.max&&c.outputChannels==e.channels&&e.min<=256&&e.max>=256;}
bool matches(const Expected& e){return matches(e,platform::defaultOutputCapability());}
class Run final:private juce::Timer {
public:
 explicit Run(std::filesystem::path root,Expected expected):expected_(std::move(expected)),root_(std::move(root)),events_(root_/"native-events.csv"),facts_(root_/"scheduled-facts.csv"),progress_(root_/"progress.csv"),commands_(root_/"commands.csv"),ui_(root_/"ui.csv"),storeLog_(root_/"store-operations.csv"),tabLog_(root_/"tab-progress.csv"),keyLog_(root_/"key-observations.csv"),inputLog_(root_/"input-intents.csv"){
  keyLog_<<"observed_ns,event_seconds,key,hardware,down,repeat,modified,matched,visible,consumed,invoked\n";inputLog_<<"ns,type,key,hardware,repeat,flags\n";
  tabLog_<<"observed_ns,uuid,generation,epoch,sequence,state,through,sample,cycle,has_sample,events,selected\n";
  events_<<"ns,epoch,kind,serial,object,selector,scope,element,frames,flags,status,raw_host,sample_time,rate_scalar,peak,text_utf8_hex\n";facts_<<"observed_ns,uuid,generation,epoch,binding,frame,cycle,kind,event,role,action\n";
  progress_<<"observed_ns,uuid,generation,epoch,sequence,state,client_accepted,scheduled,active,completed,cursor,requested_stop_ns,uncertain,physical_confirmed,has_physical,terminal,partial,fault\n";
  commands_<<"ns,phase,action,accepted\n";ui_<<"ns,phase,state,active,cycles,output_state,callbacks,capture_phase,initial_ack,checkpoint_seq,start_taken,owner\n";
  storeLog_<<"ns,phase,operation\n";
  std::filesystem::permissions(root_,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
  storage::StoreOptions options;options.path=root_/"profile.sqlite";options.create=true;options.createdUtc=utcNow();
  options.diagnosticHook=[this](const std::string& phase,const std::string& op){storeLog_<<platform::monotonicNs()<<','<<phase<<','<<op<<'\n';};
  store_=std::make_unique<storage::ProfileStore>(options);const auto session=capture_fixture::confirmed(store_->createSession(storage::newUuid(),utcNow(),"America/New_York",{},json::Value::Object{{"synthetic_fixture",true}}));
  view_=std::make_unique<desktop::PracticeView>();
  if(!view_->configureCapture(*store_,session.owner,utcNow,"America/New_York"))throw std::runtime_error("Capture attachment refused");view_->setSize(1280,800);view_->showTab(true);view_->tabView().selectEvent("picked-E");view_->addToDesktop(juce::ComponentPeer::windowHasTitleBar);view_->setVisible(true);view_->setFocusMode(true);view_->grabKeyboardFocus();NSView* native=(__bridge NSView*)view_->getPeer()->getNativeHandle();[native.window makeKeyAndOrderFront:nil];
  view_->onNativeEvent=[this](const platform::NativeEvent& e){events_<<e.ns<<','<<e.epoch<<','<<e.kind<<','<<e.serial<<','<<e.object<<','<<e.selector<<','<<e.scope<<','<<e.element<<','<<e.frames<<','<<e.flags<<','<<e.status<<','<<e.rawHost<<','<<std::setprecision(17)<<e.sampleTime<<','<<e.rateScalar<<','<<e.peak<<','<<hexText(e.text.data())<<'\n';};
  view_->onScheduledFact=[this](const scheduler::Fact& f){facts_<<platform::monotonicNs()<<','<<uuid(f.owner)<<','<<f.owner.generation<<','<<f.owner.epoch<<','<<f.binding<<','<<f.frame<<','<<f.cycle<<','<<int(f.kind)<<','<<f.sourceEvent<<','<<int(f.role)<<','<<int(f.action)<<'\n';};
  view_->onProgress=[this](const practice::Progress& p){progress_<<platform::monotonicNs()<<','<<uuid(p.owner)<<','<<p.owner.generation<<','<<p.owner.epoch<<','<<p.sequence<<','<<int(p.state)<<','<<p.clientAcceptedThrough<<','<<p.scheduledThrough<<','<<p.activeFrames<<','<<p.completedCycles<<','<<p.cursorFrames<<','<<p.requestedStopNs<<','<<p.uncertainThrough<<','<<p.physicalConfirmedThrough<<','<<p.hasPhysicalConfirmation<<','<<p.terminal<<','<<p.partial<<','<<p.fault<<'\n';};
  view_->onTabProgress=[this](const tab::PlaybackPosition& position){const auto& p=position.progress;tabLog_<<platform::monotonicNs()<<','<<uuid(p.owner)<<','<<p.owner.generation<<','<<p.owner.epoch<<','<<p.sequence<<','<<int(p.state)<<','<<p.clientAcceptedThrough<<','<<position.sample<<','<<position.cycle<<','<<position.hasMusicalSample<<',';for(const auto& id:position.events)tabLog_<<id<<';';tabLog_<<','<<view_->tabView().selectedEvent()<<'\n';

  };
  view_->onPracticeCommand=[this](desktop::PracticeCommand command,bool accepted,const std::string&){++commandCalls_;lastAccepted_=accepted;commands_<<platform::monotonicNs()<<','<<phase_<<",intent-"<<int(command)<<','<<accepted<<'\n';};
  view_->onKeyObservation=[this](const desktop::PracticeKeyObservation& k){++keyObservations_;keyLog_<<platform::monotonicNs()<<','<<std::setprecision(17)<<k.timestamp<<','<<k.key<<','<<k.hardwareKey<<','<<k.down<<','<<k.repeat<<','<<k.modified<<','<<k.matchedWindow<<','<<k.visible<<','<<k.consumed<<','<<k.invoked<<'\n';};
  begin_=platform::monotonicNs();startTimer(20);
 }
 int result()const{return done_&&!failed_?0:1;}
private:
 void key(NSString* text,unsigned short code,bool down,bool repeat=false,NSEventModifierFlags flags=0){
  NSView* native=(__bridge NSView*)view_->getPeer()->getNativeHandle();inputLog_<<platform::monotonicNs()<<','<<(down?"down":"up")<<','<<int([text characterAtIndex:0])<<','<<code<<','<<repeat<<','<<flags<<'\n';
  auto* e=[NSEvent keyEventWithType:down?NSEventTypeKeyDown:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:flags timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:text charactersIgnoringModifiers:text isARepeat:repeat keyCode:code];[NSApp sendEvent:e];
 }
 bool tap(const char* name,NSString* text,unsigned short code,bool expected){const auto calls=commandCalls_;const auto seen=keyObservations_;key(text,code,true);key(text,code,false);return action(name,commandCalls_==calls+1&&lastAccepted_==expected&&keyObservations_>=seen+2);}
 bool action(const char* name,bool ok){commands_<<platform::monotonicNs()<<','<<phase_<<','<<name<<','<<ok<<'\n';if(!ok)finish(true,"control refused");return ok;}
 void picture(const std::string& name){auto image=view_->createComponentSnapshot(view_->getLocalBounds());juce::FileOutputStream out(juce::File((root_/name).string()));juce::PNGImageFormat png;const bool wrote=out.openedOk() && png.writeImageToStream(image,out);out.flush();imageFailed_|=!wrote || out.getStatus().failed();}
 void finish(bool failed,const char* reason){if(done_)return;done_=true;stopTimer();
  struct DispatchExit {~DispatchExit(){juce::MessageManager::getInstance()->stopDispatchLoop();}} exit;
  try {view_->quiesceAndRetain();failed_=failed||captureOverflow.load();picture("final-view.png");failed_|=imageFailed_;const auto c=view_->coordinator();const auto s=view_->outputStatus();
  failed_=failed_ || s.cleanupFailed || s.nativeSkips || platform::hub.dropped.load() || s.lifecycle.fault!=output::Fault::None || !view_->error().empty();
  for(auto* stream:{&events_,&facts_,&progress_,&commands_,&ui_,&tabLog_,&keyLog_,&inputLog_}){stream->flush();failed_|=!stream->good();}
  std::ofstream raw(root_/"native-output-f32.raw",std::ios::binary);raw.write(reinterpret_cast<const char*>(captured.data()),static_cast<std::streamsize>(captureCount*sizeof(float)));raw.close();failed_|=!raw.good();
  std::ofstream map(root_/"capture-map.csv");map<<"serial,float_offset,epoch,object,frames,buffer,channels,float_count\n";
  for(std::size_t i=0;i<captureBlocksCount;++i){const auto& b=captureBlocks[i];map<<b.serial<<','<<b.offset<<','<<b.epoch<<','<<b.object<<','<<b.frames<<','<<b.buffer<<','<<b.channels<<','<<b.floats<<'\n';}map.close();failed_|=!map.good();
  std::ofstream state(root_/"final-status.json");const auto& l=s.lifecycle;const auto& o=l.observation;
  state<<"{\"owner\":"<<std::quoted(uuid(l.owner))<<",\"generation\":"<<l.owner.generation<<",\"epoch\":"<<l.owner.epoch;
  auto field=[&](const char* key,auto value){state<<','<<std::quoted(key)<<':'<<value;};
  field("request_epoch",l.request.epoch);field("request_ns",l.request.stampNs);field("request_rate",l.request.format.rate);field("request_frames",l.request.format.frames);field("selected_physical",l.request.selectedPhysical);
  field("cached_epoch",l.cached.epoch);field("cached_ns",l.cached.stampNs);field("cached_rate",l.cached.format.rate);field("cached_frames",l.cached.format.frames);
  field("observed_epoch",o.epoch);field("callback_sequence",o.callbackSequence);field("callback_ns",o.callbackStampNs);field("query_ns",o.queryStampNs);field("queried_rate",o.queriedIO.rate);field("queried_frames",o.queriedIO.frames);field("callback_frames",o.callbackFrames);field("native_object",o.nativeIOObject);field("queried_object",o.queriedIOObject);field("physical_object",o.physicalObject);field("physical_rate",o.physicalRate);field("physical_frames",o.physicalFrames);field("physical_known",o.physicalKnown);field("io_known",o.ioKnown);field("route_known",o.routeKnown);field("full_route",o.selectedInFullRoute);field("active_route",o.selectedInActiveRoute);
  field("state",int(l.state));field("fault",int(l.fault));field("token",l.observationToken);field("submitted",l.submittedFrames);field("confirmed",l.confirmedFrames);field("has_confirmation",l.hasConfirmation);field("uncertain",l.uncertainThrough);field("requested_stop_ns",l.requestedStopNs);field("first_stop_marker_ns",l.firstSilenceNs);field("announcements",l.announcements);field("owns_outcome",l.ownsOutcome);field("pending",l.pendingOutcome);field("stop_requested",l.stopRequested);
  field("first_silent_callback_ns",s.firstSilentCallbackNs);field("callbacks",s.callbacks);field("rendered_blocks",s.renderedBlocks);field("commands_accepted",s.commandAccepted);field("commands_rejected",s.commandRejected);field("native_skips",s.nativeSkips);field("overloads",s.overloads);field("cleanup_failed",s.cleanupFailed);field("event_drops",platform::hub.dropped.load());field("mach_timebase_numer",platform::timebase.numer);field("mach_timebase_denom",platform::timebase.denom);
  field("master_volume",s.mix.master);field("reference_volume",s.mix.bus[0]);field("count_in_volume",s.mix.bus[1]);state<<"}\n";state.close();failed_|=!state.good();

  // Synthetic Store results retain exact originals. This is no learner performance or musical acceptance.
  view_.reset();store_.reset();storeLog_.close();failed_|=!storeLog_.good();
  storage::StoreOptions reopen;reopen.path=root_/"profile.sqlite";{storage::ProfileStore store(reopen);capture_fixture::write(root_/"reopened-snapshot.json",storage::canonical(capture_fixture::confirmed(store.snapshot(storage::newUuid())).data));}
  std::ofstream result(root_/"run-result.json");result<<"{\"failed\":"<<(failed_?"true":"false")<<",\"reason\":"<<std::quoted(reason)<<",\"phase\":"<<phase_<<",\"activeFrames\":"<<c.activeFrames()<<",\"cycles\":"<<c.completedCycles()<<",\"generations\":"<<c.generations().size()<<",\"rate\":"<<s.lifecycle.request.format.rate<<",\"frames\":"<<s.lifecycle.request.format.frames<<",\"state\":"<<int(c.state())<<",\"pendingOriginalOutcome\":"<<(c.pending()?"true":"false")<<",\"capturedFloats\":"<<captureCount<<",\"captureOverflow\":"<<(captureOverflow?"true":"false")<<",\"callbacks\":"<<s.callbacks<<",\"physicalConfirmationAvailable\":"<<(s.lifecycle.hasConfirmation?"true":"false")<<"}\n";result.close();failed_|=!result.good();
  std::cout<<(failed_?"FAIL ":"PASS ")<<reason<<std::endl;juce::MessageManager::getInstance()->stopDispatchLoop();
  }catch(const std::exception& e){failed_=true;std::cerr<<"FAIL finalizer: "<<e.what()<<std::endl;
   std::ofstream report(root_/"run-result.json");report<<"{\"failed\":true,\"reason\":"<<std::quoted(std::string("finalizer: ")+e.what())<<",\"phase\":"<<phase_<<"}\n";
  }
 }
 void timerCallback()override{try{step();}catch(const std::exception& e){finish(true,e.what());}catch(...){finish(true,"unknown actor exception");}}
 void step(){
  const auto s=view_->outputStatus();const auto& c=view_->coordinator();const auto now=platform::monotonicNs();ui_<<now<<','<<phase_<<','<<int(c.state())<<','<<c.activeFrames()<<','<<c.completedCycles()<<','<<int(s.lifecycle.state)<<','<<s.callbacks;
  auto* capture=const_cast<capture::PracticeSession*>(view_->captureSession());const auto cp=capture->checkpointState(static_cast<std::int64_t>(now/1000000));
  ui_<<','<<int(capture->phase())<<','<<cp.initialAcknowledged<<','<<(cp.acknowledged?cp.acknowledged->sequence:-1)<<','<<capture->startTaken()<<','<<capture->binding().owner<<'\n';
  if(now-begin_>45000000000ULL){finish(true,"45 second watchdog");return;}
  if(s.lifecycle.state==output::State::Fault || !view_->error().empty() || captureOverflow){finish(true,"unexpected output/transport error");return;}
  const auto rate=s.lifecycle.request.format.rate;const auto& gens=c.generations();const auto* last=gens.empty()?nullptr:&gens.back();
  switch(phase_){
   case 0:if(!matches(expected_)){finish(true,"default capability changed from declared preflight; no connect");return;}if(action("connect",view_->performCommand(desktop::PracticeCommand::Connect)))++phase_;break;
   case 1:if(s.lifecycle.state==output::State::Observed){if(action("acknowledge",view_->performCommand(desktop::PracticeCommand::Enable)))++phase_;}break;
   case 2:if(s.lifecycle.state==output::State::Ready){const auto actual=platform::defaultOutputCapability();if(!matches(expected_,actual)||s.lifecycle.request.selectedPhysical!=actual.object||s.lifecycle.observation.physicalObject!=actual.object||s.lifecycle.request.format.rate!=expected_.rate||s.lifecycle.request.format.frames!=256||!s.lifecycle.observation.physicalKnown||s.lifecycle.observation.physicalRate!=expected_.rate||s.lifecycle.observation.physicalFrames!=expected_.physical){finish(true,"requested/observed configuration differs from declared case; no Start");return;}
    const auto calls=commandCalls_;key(@" ",49,true);if(action("AppKit-Space-start",commandCalls_==calls+1&&lastAccepted_))++phase_;}break;
   case 3:if(last&&last->clientAcceptedThrough>=rate/4&&last->state==practice::State::CountIn){
    picture("count-in-focus.png");const auto calls=commandCalls_;key(@" ",49,true,true);
    NSView* native=(__bridge NSView*)view_->getPeer()->getNativeHandle();auto* flags=[NSEvent keyEventWithType:NSEventTypeFlagsChanged location:NSZeroPoint modifierFlags:NSEventModifierFlagShift timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:@"" charactersIgnoringModifiers:@"" isARepeat:NO keyCode:56];inputLog_<<platform::monotonicNs()<<",flags,0,56,0,"<<NSEventModifierFlagShift<<'\n';[NSApp sendEvent:flags];
    if(!action("actual-JUCE-Shift-state",juce::ModifierKeys::getCurrentModifiers().isShiftDown()))return;
    view_->tabView().showDetail(true);juce::TextEditor* intended=nullptr;for(auto* child:view_->tabView().getChildren())if(auto* editor=dynamic_cast<juce::TextEditor*>(child)){intended=editor;editor->grabKeyboardFocus();}
    if(!action("actual-readonly-descendant-focus",intended&&intended->isShowing()&&intended->hasKeyboardFocus(false)))return;key(@" ",49,true,true);key(@" ",49,false);view_->tabView().showDetail(false);
    if(!action("held-Space-modifier-focus-repeat-suppressed",commandCalls_==calls&&c.generations().size()==1))return;
    if(tap("Clean-midrun-refused",@"c",8,false)&&tap("Save-midrun-refused",@"s",1,false)&&tap("Again-midrun-refused",@"a",0,false)&&action("no-implicit-assessment-or-save",!capture->original().has_value()))++phase_;
   }break;
   case 4:if(view_->tabPosition().events==std::vector<std::string>{"held-E"}&&view_->tabPosition().cycle==0&&last&&last->state==practice::State::Running){const auto calls=commandCalls_;key(@" ",49,true);if(action("AppKit-Space-pause-held",commandCalls_==calls+1&&lastAccepted_))++phase_;}break;
   case 5:if(c.state()==practice::State::Paused&&s.lifecycle.state==output::State::Paused){picture("paused-held-focus.png");const auto calls=commandCalls_;key(@" ",49,true,true);
    if(!action("held-Pause-repeat-no-Resume",commandCalls_==calls&&c.generations().size()==1))return;key(@" ",49,false);
    const auto owner=c.owner();const auto active=c.activeFrames();const auto selected=view_->tabView().selectedEvent();
    if(!tap("exit-Focus-paused",@"f",3,true)||!tap("restore-Focus-paused",@"f",3,true))return;
    if(!action("Focus-preserves-paused-owner-facts-selection",c.owner()==owner&&c.activeFrames()==active&&view_->tabView().selectedEvent()==selected))return;
    if(tap("fresh-Space-resume",@" ",49,true)&&action("fresh-countin-no-old-highlight",view_->tabView().playingEvents().empty()))++phase_;
   }break;
   case 6:if(c.generations().size()==2&&last&&view_->tabPosition().events==std::vector<std::string>{"full-rest"}&&last->state==practice::State::Running){picture("running-rest-focus.png");
    if(tap("Esc-stop-rest",[NSString stringWithFormat:@"%C",(unichar)27],53,true)&&tap("Space-after-requested-Stop-refused",@" ",49,false)&&action("PauseResume-disabled-after-Stop",!view_->canPerformCommand(desktop::PracticeCommand::Pause)&&!view_->canPerformCommand(desktop::PracticeCommand::Resume)))++phase_;
   }break;
   case 7:if(capture->phase()==capture::SessionPhase::Review){picture("partial-review-focus.png");const auto owner=c.owner();const auto active=c.activeFrames();const auto cycles=c.completedCycles();
    if(!tap("Again-before-Save-refused",@"a",0,false)||!tap("Clean-explicit-review-selection",@"c",8,true))return;
    if(!action("Clean-no-save-time-cycle-target-change",!capture->original()&&c.owner()==owner&&c.activeFrames()==active&&c.completedCycles()==cycles&&cycles<2))return;
    picture("Clean-selected-focus.png");
    if(tap("Save-explicit-Clean-original",@"s",1,true)&&tap("Again-during-save-refused",@"a",0,false)&&tap("Clean-after-seal-refused",@"c",8,false))++phase_;
   }break;
   case 8:if(capture->phase()==capture::SessionPhase::Saved&&capture->canLeave(!s.lifecycle.ownsOutcome&&!s.lifecycle.pendingOutcome)){
    capture_fixture::write(root_/"original.json",capture->original()->bytes);picture("saved-focus.png");const auto owner=c.owner();const auto calls=commandCalls_;
    if(!tap("Again-confirmed-rearms-stopped",@"a",0,true))return;key(@"a",0,true,true);key(@"a",0,false);
    if(!action("orphan-Again-repeat-no-second-command",commandCalls_==calls+1))return;
    if(!action("Again-no-new-allocation-or-autoplay",capture->phase()==capture::SessionPhase::Idle&&c.owner()==owner&&!c.pending()&&s.lifecycle.state!=output::State::Running))return;
    snapshot_.emplace(store_->snapshot(storage::newUuid()));++phase_;
   }break;
   case 9:if(snapshot_->wait_for(std::chrono::milliseconds(0))==std::future_status::ready){auto r=snapshot_->get();snapshot_.reset();if(r.status!=storage::Status::Confirmed){finish(true,"snapshot failure");return;}
    capture_fixture::write(root_/"snapshot.json",storage::canonical(r.data));picture("Again-ready-stopped.png");if(action("confirmed-close",view_->requestClose())){++phase_;finish(false,"native Focus/AppKit command input; explicit partial Clean/Save; confirmed Again stopped; normal original reopen");}
   }break;
   default:finish(true,"invalid phase");
  }

 }
 Expected expected_;std::filesystem::path root_;std::ofstream events_,facts_,progress_,commands_,ui_,storeLog_,tabLog_,keyLog_,inputLog_;std::set<std::string> images_;std::unique_ptr<storage::ProfileStore> store_;std::optional<storage::ProfileStore::Future> snapshot_;std::unique_ptr<desktop::PracticeView> view_;std::uint64_t begin_{};int phase_{};std::uint64_t commandCalls_{},keyObservations_{};bool lastAccepted_{};bool done_{},failed_{},imageFailed_{};
};
}
int main(int argc,char** argv){try{
 if(argc==2&&std::string(argv[1])=="--focused-button-space-self-test"){
  [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];juce::ScopedJuceInitialiser_GUI gui;
  juce::Component host;host.setSize(360,180);host.setWantsKeyboardFocus(true);juce::TextButton button{"Focused Space target"};button.setWantsKeyboardFocus(true);button.setClickingTogglesState(false);host.addAndMakeVisible(button);button.setBounds(24,24,220,42);
  int clicks=0,dispatches=0,toggles=0;std::vector<desktop::PracticeKeyObservation> observations;button.onClick=[&]{++clicks;};
  desktop::PracticeKeyboardMac keyboard(host,[&](desktop::PracticeCommand command){++dispatches;if(command==desktop::PracticeCommand::ToggleTransport)++toggles;});
  keyboard.onObservation=[&](const desktop::PracticeKeyObservation& o){observations.push_back(o);};
  host.addToDesktop(juce::ComponentPeer::windowHasTitleBar);host.setVisible(true);NSView* native=(__bridge NSView*)host.getPeer()->getNativeHandle();if(!native||!native.window)throw std::runtime_error("native host window unavailable");
  int checks=0;const auto ck=[&](bool okay,const char* label){++checks;if(!okay)throw std::runtime_error(label);};
  button.grabKeyboardFocus();id initialResponder=native.window.firstResponder;auto* initialFocus=juce::Component::getCurrentlyFocusedComponent();
  std::cout<<"DIAGNOSTIC pre-space nativeUserKeyDelivery=NOT_RUN appActive="<<[NSApp isActive]<<" keyWindow="<<native.window.isKeyWindow
           <<" firstResponderClass="<<(initialResponder?NSStringFromClass([initialResponder class]).UTF8String:"nil")<<" firstResponder="<<(__bridge const void*)initialResponder
           <<" firstResponderIsNative="<<(initialResponder==native)<<" focusedComponent="<<static_cast<const void*>(initialFocus)
           <<" focusedClass="<<(initialFocus?typeid(*initialFocus).name():"nil")<<" focusedIsButton="<<(initialFocus==&button)
           <<" buttonHasKeyboardFocus="<<button.hasKeyboardFocus(false)<<'\n';
  ck(initialResponder==native,"JUCE peer view is the AppKit first responder before focused-button events");
  ck(initialFocus==&button&&button.hasKeyboardFocus(false),"focused TextButton owns JUCE keyboard focus before Space");
  const auto sendSpace=[&](bool down){auto* e=[NSEvent keyEventWithType:down?NSEventTypeKeyDown:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:@" " charactersIgnoringModifiers:@" " isARepeat:NO keyCode:49];[NSApp sendEvent:e];};
  sendSpace(true);sendSpace(false);
  id firstResponder=native.window.firstResponder;auto* focused=juce::Component::getCurrentlyFocusedComponent();
  std::cout<<"DIAGNOSTIC focused-button nativeUserKeyDelivery=NOT_RUN clicks="<<clicks<<" dispatches="<<dispatches<<" appActive="<<[NSApp isActive]<<" keyWindow="<<native.window.isKeyWindow
           <<" firstResponderClass="<<(firstResponder?NSStringFromClass([firstResponder class]).UTF8String:"nil")<<" firstResponder="<<(__bridge const void*)firstResponder
           <<" firstResponderIsNative="<<(firstResponder==native)<<" focusedComponent="<<static_cast<const void*>(focused)
           <<" focusedClass="<<(focused?typeid(*focused).name():"nil")<<" focusedIsButton="<<(focused==&button)<<" focusedIsHost="<<(focused==&host)
           <<" buttonHasKeyboardFocus="<<button.hasKeyboardFocus(false)<<" observationCount="<<observations.size()<<'\n';
  for(std::size_t i=0;i<observations.size();++i){const auto& o=observations[i];std::cout<<"DIAGNOSTIC observation["<<i<<"] timestamp="<<std::setprecision(17)<<o.timestamp
       <<" key="<<o.key<<" hardwareKey="<<o.hardwareKey<<" down="<<o.down<<" repeat="<<o.repeat<<" modified="<<o.modified
       <<" matchedWindow="<<o.matchedWindow<<" visible="<<o.visible<<" consumed="<<o.consumed<<" invoked="<<o.invoked<<'\n';}
  const auto clickDeadline=std::chrono::steady_clock::now()+std::chrono::seconds(2);
  while(clicks<1&&std::chrono::steady_clock::now()<clickDeadline){@autoreleasepool {CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);}}
  ck(clicks==1,"Space activates the focused JUCE button exactly once");ck(dispatches==0&&toggles==0,"focused-button Space does not dispatch Practice ToggleTransport");
  ck(observations.size()==2&&observations[0].key==' '&&observations[0].hardwareKey==49&&observations[0].down&&!observations[0].repeat&&!observations[0].modified&&observations[0].matchedWindow&&observations[0].visible,"focused-button Space keydown is observed for the visible matching host");
  ck(observations[1].key==' '&&observations[1].hardwareKey==49&&!observations[1].down&&observations[1].matchedWindow&&observations[1].visible,"focused-button Space keyup is observed for the visible matching host");
  ck(!observations[0].consumed&&!observations[0].invoked&&!observations[1].consumed&&!observations[1].invoked,"focused-button Space events pass through without adapter consumption");
  host.grabKeyboardFocus();ck(host.hasKeyboardFocus(false),"Practice host regains keyboard focus");sendSpace(true);sendSpace(false);
  ck(clicks==1&&dispatches==1&&toggles==1,"host-focused Space dispatches ToggleTransport once without activating the button");
  ck(observations.size()==4&&observations[2].key==' '&&observations[2].hardwareKey==49&&observations[2].down&&observations[2].matchedWindow&&observations[2].visible&&observations[2].consumed&&observations[2].invoked&&!observations[3].down&&observations[3].matchedWindow&&observations[3].visible&&!observations[3].consumed&&!observations[3].invoked,"host-focused command consumes only the initial matching Space down");
  host.removeFromDesktop();std::cout<<"PASS "<<checks<<" focused-button Space arbitration checks; no PracticeView, audio, profile, or Store constructed\n";return 0;
 }
 if(argc==2&&std::string(argv[1])=="--preflight"){const auto c=platform::defaultOutputCapability();std::cout<<"valid="<<c.valid<<" uid="<<c.uid<<" name="<<std::quoted(c.name)<<" rate="<<c.rate<<" physicalFrames="<<c.physicalFrames<<" min="<<c.minFrames<<" max="<<c.maxFrames<<" channels="<<c.outputChannels<<'\n';return c.valid?0:1;}
 if(argc!=9||std::string(argv[1])!="--run")return 2;const std::filesystem::path root=argv[2];if(!root.is_absolute()||!std::filesystem::is_directory(root)||!std::filesystem::is_empty(root))return 2;
 auto number=[](const char* text){std::size_t used=0;const auto n=std::stoull(text,&used);if(used!=std::string(text).size()||n>UINT32_MAX)throw std::invalid_argument("Invalid declared capability");return static_cast<std::uint32_t>(n);};
 Expected expected{argv[3],number(argv[4]),number(argv[5]),number(argv[6]),number(argv[7]),number(argv[8])};if(!matches(expected))throw std::invalid_argument("Declared capability differs; native sequence not started");
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];juce::ScopedJuceInitialiser_GUI gui;Run run(root,expected);juce::MessageManager::getInstance()->runDispatchLoop();return run.result();
}catch(const std::exception& e){std::cerr<<"FAIL entry: "<<e.what()<<'\n';return 1;}}

#endif
