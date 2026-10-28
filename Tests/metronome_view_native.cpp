#include <CoreAudio/CoreAudio.h>
#include <array>
#include <atomic>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <filesystem>
#import <AppKit/AppKit.h>
namespace {
constexpr std::size_t captureLimit=192000*40*2;
std::array<float,captureLimit> captured{};std::size_t captureCount{};std::atomic<bool> captureOverflow{false};
struct CaptureBlock {std::uint64_t serial{},offset{};std::uint32_t epoch{},object{},frames{},buffer{},channels{},floats{};};
std::array<CaptureBlock,100000> captureBlocks{};std::size_t captureBlocksCount{};
void captureNative(int,const AudioBufferList*)noexcept;
}
#define FATHOM_TEST_NATIVE_CAPTURE captureNative
#include "../Source/platform/AudioOutputMac.mm"
#include "desktop/MetronomeView.hpp"
#include "platform/ProfileAccessMac.hpp"
#include <ctime>
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
std::string focusName(const juce::Component* component){
 if(!component)return "<none>";
 if(const auto* button=dynamic_cast<const juce::Button*>(component))return button->getButtonText().toStdString();
 if(component->getTitle().isNotEmpty())return component->getTitle().toStdString();
 return component->getName().toStdString();
}
juce::Component* focusControl(juce::Component& root,const char* name){
 for(auto* component:root.getChildren()){
  if(focusName(component)==name||component->getTitle()==name)return component;
  if(auto* result=focusControl(*component,name))return result;
 }
 return nullptr;
}
int focusProbe(const std::filesystem::path& root){
 if(!root.is_absolute()||std::filesystem::exists(root))return 2;
 std::filesystem::create_directories(root);
 std::ofstream trace(root/"focus-trace.tsv"),checks(root/"checks.tsv");
 trace<<"width\tstate\tfrom\tkey\texpected\tactual\tresult\n";
 int count=0,failures=0;
 auto check=[&](bool okay,const char* description){++count;failures+=!okay;checks<<description<<'\t'<<(okay?"PASS":"FAIL")<<'\n';};
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];juce::ScopedJuceInitialiser_GUI gui;
 for(int width:{640,920})for(bool recovery:{false,true}){
  desktop::MetronomeView view;view.setPresentationLevel(desktop::presentation::Level::Advanced);view.setSize(width,680);view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);view.setVisible(true);
  if(recovery){view.onReopenStore=[]{return true;};view.storeReopenFailed("controlled focus failure");view.service();}
  NSView* native=(__bridge NSView*)view.getPeer()->getNativeHandle();
  [native.window makeKeyAndOrderFront:nil];
  check(native&&native.window&&view.isShowing(),"native Metronome desktop peer visible");
  check(view.outputStatus().lifecycle.state==output::State::Closed&&!view.soundPending(),"focus probe retains closed output and no sound owner");
  juce::KeyboardFocusTraverser traverser;
  const auto all=traverser.getAllComponents(&view);
  auto contains=[&](const char* name){auto* target=focusControl(view,name);return target&&std::find(all.begin(),all.end(),target)!=all.end();};
  check(!contains("Start")&&!contains("Pause")&&!contains("Resume")&&!contains("Finish check")&&!contains("Retry original")&&!contains("Keep stored"),"disabled transport and recovery controls absent from expected traversal");
  check(contains("Reopen profile")==recovery,"Reopen enters traversal only after controlled failure");
  auto press=[&](bool reverse){
   auto* event=[NSEvent keyEventWithType:NSEventTypeKeyDown location:NSZeroPoint modifierFlags:reverse?NSEventModifierFlagShift:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:reverse?@"\x19":@"\t" charactersIgnoringModifiers:@"\t" isARepeat:NO keyCode:48];
   [NSApp sendEvent:event];
   auto* up=[NSEvent keyEventWithType:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:reverse?NSEventModifierFlagShift:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:reverse?@"\x19":@"\t" charactersIgnoringModifiers:@"\t" isARepeat:NO keyCode:48];
   [NSApp sendEvent:up];
  };
  auto step=[&](const char* start,bool reverse){
   auto* source=focusControl(view,start);
   check(source&&source->getWantsKeyboardFocus(),"starting control available for native focus step");
   if(!source)return;
   source->grabKeyboardFocus();
   auto* before=juce::Component::getCurrentlyFocusedComponent();
   auto* expected=reverse?traverser.getPreviousComponent(source):traverser.getNextComponent(source);
   press(reverse);
   auto* actual=juce::Component::getCurrentlyFocusedComponent();
   const bool passed=before==source&&expected&&actual==expected;
   trace<<width<<'\t'<<(recovery?"failed-store":"closed")<<'\t'<<focusName(source)<<'\t'<<(reverse?"Shift-Tab":"Tab")<<'\t'<<focusName(expected)<<'\t'<<focusName(actual)<<'\t'<<(passed?"PASS":"FAIL")<<'\n';
   check(passed,"injected AppKit key follows expected JUCE focus traversal");
  };
  step("Target BPM",false);step("Click enabled (stopped)",false);step("Apply pattern",true);
  step("Audio settings",false);step("Reset",false);step("Live BPM",true);
  step("Saved presets",true);
  if(recovery){step("Saved presets",false);step("Reopen profile",true);}
  check(!all.empty()&&all.front()==focusControl(view,"Back"),"constructed traversal begins with visible Back action");
  if(!all.empty()){
   all.front()->grabKeyboardFocus();
   check(juce::Component::getCurrentlyFocusedComponent()==all.front(),"native sweep begins at Back");
   for(std::size_t index=1;index<all.size();++index){
    auto* before=juce::Component::getCurrentlyFocusedComponent();press(false);
    auto* actual=juce::Component::getCurrentlyFocusedComponent();
    const bool passed=before==all[index-1]&&actual==all[index];
    trace<<width<<'\t'<<(recovery?"failed-store":"closed")<<'\t'<<focusName(all[index-1])<<"\tTab sweep\t"<<focusName(all[index])<<'\t'<<focusName(actual)<<'\t'<<(passed?"PASS":"FAIL")<<'\n';
    check(passed,"AppKit Tab sweep follows complete constructed focus sequence");
   }
   for(std::size_t index=all.size()-1;index>0;--index){
    auto* before=juce::Component::getCurrentlyFocusedComponent();press(true);
    auto* actual=juce::Component::getCurrentlyFocusedComponent();
    const bool passed=before==all[index]&&actual==all[index-1];
    trace<<width<<'\t'<<(recovery?"failed-store":"closed")<<'\t'<<focusName(all[index])<<"\tShift-Tab sweep\t"<<focusName(all[index-1])<<'\t'<<focusName(actual)<<'\t'<<(passed?"PASS":"FAIL")<<'\n';
    check(passed,"AppKit Shift-Tab sweep follows complete reverse focus sequence");
   }
  }
  auto* reducedMotion=dynamic_cast<juce::ToggleButton*>(focusControl(view,"Reduce motion"));
  check(reducedMotion&&!reducedMotion->getToggleState(),"reduced-motion control begins unchecked on the native peer");
  if(reducedMotion){
   reducedMotion->grabKeyboardFocus();
   auto* down=[NSEvent keyEventWithType:NSEventTypeKeyDown location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:@" " charactersIgnoringModifiers:@" " isARepeat:NO keyCode:49];
   auto* up=[NSEvent keyEventWithType:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:@" " charactersIgnoringModifiers:@" " isARepeat:NO keyCode:49];
   [NSApp sendEvent:down];[NSApp sendEvent:up];
   const auto until=[NSDate dateWithTimeIntervalSinceNow:0.1];while([until timeIntervalSinceNow]>0)CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);
   check(reducedMotion->getToggleState()&&view.outputStatus().lifecycle.state==output::State::Closed&&!view.soundPending(),"injected AppKit Space enables local reduced motion without starting audio");
  }
  view.removeFromDesktop();
 }
 trace.flush();checks.flush();
 const bool evidenceOkay=trace.good()&&checks.good();
 std::ofstream summary(root/"focus-summary.json");summary<<"{\"checks\":"<<count<<",\"failures\":"<<failures<<",\"evidenceFlushed\":"<<(evidenceOkay?"true":"false")<<",\"injectedAppKitEvents\":true,\"hardwareKeyboardRun\":false,\"screenReaderRun\":false,\"nativeAudioRun\":false}\n";
 std::cout<<(failures||!evidenceOkay?"FAIL ":"PASS ")<<count<<" injected AppKit Metronome focus checks; failures="<<failures<<'\n';
 return failures||!evidenceOkay?1:0;
}
class Run final:private juce::Timer {
public:
 explicit Run(std::filesystem::path root,platform::OutputCapability expected):expected_(std::move(expected)),root_(std::move(root)),events_(root_/"native-events.csv"),facts_(root_/"facts.csv"),progress_(root_/"progress.csv"),segments_(root_/"segments.csv"),commands_(root_/"commands.csv"),ui_(root_/"ui.csv"),replies_(root_/"tempo-replies.csv"){
  events_<<"ns,epoch,kind,serial,object,selector,scope,element,frames,flags,status,raw_host,sample_time,rate_scalar,peak,text_utf8_hex\n";
  facts_<<"observed_ns,uuid,generation,epoch,binding,frame,cycle,kind,event,role,action\n";
  progress_<<"observed_ns,uuid,generation,epoch,binding,sequence,phase,client_accepted,scheduled,active,total_active,completed,cursor,bar_frames,tempo,ramp,count,pending_manual,last_command,requested_stop_ns,uncertain,physical_confirmed,has_physical,terminal,partial,fault\n";
  segments_<<"observed_ns,uuid,generation,epoch,binding,from,through,tempo,count_in\n";
  commands_<<"ns,phase,action,accepted\n";ui_<<"ns,phase,owner,generation,state,active,cycles,cursor,bar,tempo,callback_sequence,callbacks,preferences_revision\n";replies_<<"ns,owner,generation,binding,sequence,tempo,accepted\n";
  std::filesystem::permissions(root_,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
  storage::StoreOptions options;options.path=root_/"profile.sqlite";options.create=true;options.createdUtc=utcNow();options.preferenceValidator=metronome::preferenceValidator;
  store_=std::make_unique<storage::ProfileStore>(options);view_=std::make_unique<desktop::MetronomeView>();if(!view_->configureStore(*store_))throw std::runtime_error("Explicit preference attachment refused");
  view_->setSize(920,680);view_->addToDesktop(juce::ComponentPeer::windowHasTitleBar);view_->setVisible(true);view_->grabKeyboardFocus();
  view_->onNativeEvent=[this](const platform::NativeEvent& e){events_<<e.ns<<','<<e.epoch<<','<<e.kind<<','<<e.serial<<','<<e.object<<','<<e.selector<<','<<e.scope<<','<<e.element<<','<<e.frames<<','<<e.flags<<','<<e.status<<','<<e.rawHost<<','<<std::setprecision(17)<<e.sampleTime<<','<<e.rateScalar<<','<<e.peak<<','<<hexText(e.text.data())<<'\n';};
  view_->onFact=[this](const scheduler::Fact& f){if(phase_>=16){if(f.role==scheduler::Role::LayerA)++polyLayerA_;if(f.role==scheduler::Role::LayerB)++polyLayerB_;}facts_<<platform::monotonicNs()<<','<<uuid(f.owner)<<','<<f.owner.generation<<','<<f.owner.epoch<<','<<f.binding<<','<<f.frame<<','<<f.cycle<<','<<int(f.kind)<<','<<f.sourceEvent<<','<<int(f.role)<<','<<int(f.action)<<'\n';};
  view_->onProgress=[this](const platform::MetronomeProgress& p){progress_<<platform::monotonicNs()<<','<<uuid(p.owner)<<','<<p.owner.generation<<','<<p.owner.epoch<<','<<p.binding<<','<<p.sequence<<','<<int(p.phase)<<','<<p.clientAcceptedThrough<<','<<p.scheduledThrough<<','<<p.activeFrames<<','<<p.totalActiveFrames<<','<<p.completedCycles<<','<<p.cursorFrames<<','<<p.barFrames<<','<<p.tempo.tempo<<','<<bool(p.tempo.ramp)<<','<<p.tempo.count<<','<<(p.tempo.pendingManual?*p.tempo.pendingManual:0)<<','<<p.tempo.lastCommand<<','<<p.requestedStopNs<<','<<p.uncertainThrough<<','<<p.physicalConfirmedThrough<<','<<p.hasPhysicalConfirmation<<','<<p.terminal<<','<<p.partial<<','<<p.fault<<'\n';};
  view_->onSegment=[this](const platform::MetronomeSegment& p){segments_<<platform::monotonicNs()<<','<<uuid(p.owner)<<','<<p.owner.generation<<','<<p.owner.epoch<<','<<p.binding<<','<<p.from<<','<<p.through<<','<<p.tempo<<','<<p.countIn<<'\n';};
  view_->onReply=[this](const platform::MetronomeReply& r){replies_<<platform::monotonicNs()<<','<<uuid(r.owner)<<','<<r.owner.generation<<','<<r.binding<<','<<r.sequence<<','<<r.tempo<<','<<r.accepted<<'\n';if(!r.accepted)replyRefused_=true;if(r.accepted&&r.tempo==tapCandidate_&&!tapCommand_&&phase_>=6&&phase_<=7)tapCommand_=r.sequence;if(r.accepted&&r.tempo==224&&tapCommand_&&r.sequence!=tapCommand_&&!manualCommand_&&phase_>=7&&phase_<=8)manualCommand_=r.sequence;};
  begin_=platform::monotonicNs();startTimer(20);
 }
 int result()const{return done_&&!failed_?0:1;}
private:
 void picture(const std::string& name){view_->service();auto image=view_->createComponentSnapshot(view_->getLocalBounds());juce::FileOutputStream out(juce::File((root_/name).string()));juce::PNGImageFormat png;imageFailed_|=!out.openedOk()||!png.writeImageToStream(image,out);out.flush();imageFailed_|=out.getStatus().failed();}
 bool action(const char* name,bool okay){commands_<<platform::monotonicNs()<<','<<phase_<<','<<name<<','<<okay<<'\n';if(!okay)finish(true,name);return okay;}
 void finish(bool failed,const char* reason){if(done_)return;done_=true;stopTimer();struct Exit{~Exit(){juce::MessageManager::getInstance()->stopDispatchLoop();}} exit;
  try{view_->quiesceAndRetain();const auto s=view_->outputStatus();picture("final.png");failed_=failed||imageFailed_||captureOverflow.load()||s.cleanupFailed||s.nativeSkips||platform::hub.dropped.load()||s.lifecycle.fault!=output::Fault::None||replyRefused_;
   std::ofstream raw(root_/"native-output-f32.raw",std::ios::binary);raw.write(reinterpret_cast<const char*>(captured.data()),static_cast<std::streamsize>(captureCount*sizeof(float)));raw.close();failed_|=!raw.good();
   std::ofstream map(root_/"capture-map.csv");map<<"serial,float_offset,epoch,object,frames,buffer,channels,float_count\n";for(std::size_t i=0;i<captureBlocksCount;++i){const auto& b=captureBlocks[i];map<<b.serial<<','<<b.offset<<','<<b.epoch<<','<<b.object<<','<<b.frames<<','<<b.buffer<<','<<b.channels<<','<<b.floats<<'\n';}map.close();failed_|=!map.good();
   std::ofstream retained(root_/"retained-generations.jsonl");using V=json::Value;using O=V::Object;using A=V::Array;auto n=[](auto x){return V::fromInteger(static_cast<std::int64_t>(x));};
   for(const auto& r:view_->retained()){const auto& p=r.progress;const auto& l=r.output;O value{{"owner",uuid(p.owner)},{"generation",n(p.owner.generation)},{"epoch",n(p.owner.epoch)},{"binding",n(p.binding)},{"sequence",n(p.sequence)},{"scheduled",n(p.scheduledThrough)},{"client_accepted",n(p.clientAcceptedThrough)},{"active",n(p.activeFrames)},{"total_active",n(p.totalActiveFrames)},{"completed",n(p.completedCycles)},{"cursor",n(p.cursorFrames)},{"bar",n(p.barFrames)},{"phase",n(int(p.phase))},{"tempo",n(p.tempo.tempo)},{"ramp",p.tempo.ramp?V(O{{"up",p.tempo.ramp->up},{"step",n(p.tempo.ramp->step)},{"every",n(p.tempo.ramp->every)},{"target",n(p.tempo.ramp->target)}}):V(nullptr)},{"ramp_count",n(p.tempo.count)},{"pending_manual",p.tempo.pendingManual?n(*p.tempo.pendingManual):V(nullptr)},{"completed_through",n(p.tempo.completedThrough)},{"last_command",n(p.tempo.lastCommand)},{"resumable",p.tempo.resumable},{"requested_stop_ns",n(p.requestedStopNs)},{"uncertain",n(p.uncertainThrough)},{"physical_confirmed",n(p.physicalConfirmedThrough)},{"has_physical",p.hasPhysicalConfirmation},{"terminal",p.terminal},{"partial",p.partial},{"fault",p.fault},{"control_disposition",r.controlDisposition},{"cancelled_before_sound",r.cancelledBeforeSound},{"output_owner",uuid(l.owner)},{"output_generation",n(l.owner.generation)},{"output_epoch",n(l.owner.epoch)},{"output_state",n(int(l.state))},{"output_submitted",n(l.submittedFrames)},{"output_requested_stop_ns",n(l.requestedStopNs)},{"output_uncertain",n(l.uncertainThrough)},{"output_stop_marker_ns",n(l.firstSilenceNs)},{"output_owns",l.ownsOutcome},{"output_pending",l.pendingOutcome}};retained<<storage::canonical(value)<<'\n';}retained.close();failed_|=!retained.good();
   const auto& l=s.lifecycle;const auto& o=l.observation;O final{{"state",n(int(l.state))},{"fault",n(int(l.fault))},{"request_epoch",n(l.request.epoch)},{"request_ns",n(l.request.stampNs)},{"requested_rate",n(l.request.format.rate)},{"requested_frames",n(l.request.format.frames)},{"selected_physical",n(l.request.selectedPhysical)},{"cached_epoch",n(l.cached.epoch)},{"cached_ns",n(l.cached.stampNs)},{"cached_rate",n(l.cached.format.rate)},{"cached_frames",n(l.cached.format.frames)},{"observed_epoch",n(o.epoch)},{"callback_sequence",n(o.callbackSequence)},{"callback_ns",n(o.callbackStampNs)},{"query_ns",n(o.queryStampNs)},{"queried_rate",n(o.queriedIO.rate)},{"queried_frames",n(o.queriedIO.frames)},{"callback_frames",n(o.callbackFrames)},{"io_object",n(o.nativeIOObject)},{"queried_io_object",n(o.queriedIOObject)},{"physical_object",n(o.physicalObject)},{"physical_rate",n(o.physicalRate)},{"physical_frames",n(o.physicalFrames)},{"physical_known",o.physicalKnown},{"io_known",o.ioKnown},{"route_known",o.routeKnown},{"full_route",o.selectedInFullRoute},{"active_route",o.selectedInActiveRoute},{"callbacks",n(s.callbacks)},{"rendered",n(s.renderedBlocks)},{"command_accepted",n(s.commandAccepted)},{"command_rejected",n(s.commandRejected)},{"native_skips",n(s.nativeSkips)},{"overloads",n(s.overloads)},{"event_drops",n(platform::hub.dropped.load())},{"cleanup_failed",s.cleanupFailed},{"first_silent_callback_ns",n(s.firstSilentCallbackNs)},{"physical_confirmed",n(l.confirmedFrames)},{"has_physical",l.hasConfirmation},{"owns_outcome",l.ownsOutcome},{"pending_outcome",l.pendingOutcome},{"mach_timebase_numer",n(platform::timebase.numer)},{"mach_timebase_denom",n(platform::timebase.denom)}};
   std::ofstream status(root_/"final-status.json");status<<storage::canonical(final)<<'\n';status.close();failed_|=!status.good();
   for(auto* stream:{&events_,&facts_,&progress_,&segments_,&commands_,&ui_,&replies_}){stream->flush();failed_|=!stream->good();}
   std::ofstream selected(root_/"final-settings.json");selected<<storage::canonical(metronome::encodeSettings(view_->settings()))<<'\n';selected.close();failed_|=!selected.good();
   const auto retainedCount=view_->retained().size();view_.reset();store_.reset();storage::StoreOptions reopen;reopen.path=root_/"profile.sqlite";reopen.preferenceValidator=metronome::preferenceValidator;{storage::ProfileStore store(reopen);const auto snapshot=store.snapshot(storage::newUuid()).get();failed_|=snapshot.status!=storage::Status::Confirmed;std::ofstream snap(root_/"reopened-snapshot.json");snap<<storage::canonical(snapshot.data)<<'\n';}
   std::ofstream result(root_/"run-result.json");result<<storage::canonical(O{{"failed",failed_},{"reason",reason},{"phase",n(phase_)},{"retained_generations",n(retainedCount)},{"captured_floats",n(captureCount)},{"capture_overflow",captureOverflow.load()},{"native_launches",n(1)},{"physical_measurement_run",false},{"human_listening_run",false}})<<'\n';std::cout<<(failed_?"FAIL ":"PASS ")<<reason<<std::endl;
  }catch(const std::exception& e){failed_=true;std::ofstream report(root_/"finalizer-error.txt");report<<e.what()<<'\n';std::cerr<<e.what()<<std::endl;}
 }
 void timerCallback()override{const auto now=platform::monotonicNs();const auto s=view_->outputStatus();const auto p=view_->progress();const auto state=s.lifecycle.state;const auto rate=s.lifecycle.request.format.rate;ui_<<now<<','<<phase_<<','<<uuid(p.owner)<<','<<p.owner.generation<<','<<int(state)<<','<<p.totalActiveFrames<<','<<p.completedCycles<<','<<p.cursorFrames<<','<<p.barFrames<<','<<p.tempo.tempo<<','<<s.lifecycle.observation.callbackSequence<<','<<s.callbacks<<','<<view_->preferenceRevision()<<'\n';
  if(now-begin_>35000000000ULL){finish(true,"35 second watchdog");return;}if(state==output::State::Fault||captureOverflow||replyRefused_){finish(true,"unexpected output/capture/tempo refusal");return;}
  switch(phase_){
   case 0:if(view_->preferencesReady()){metronome::Settings config;config.tempo=240;config.numerator=3;config.denominator=4;config.subdivision=2;config.styles={metronome::Style::Accent,metronome::Style::Normal,metronome::Style::Silent};config.ramp=metronome::Ramp{true,4,1,252};if(action("apply-3-4-sub2-silent-ramp",view_->applySettings(config))&&action("connect",view_->connectOutput(&expected_)))++phase_;}break;
   case 1:if(state==output::State::Observed){if(action("pre-ACK-start-refused",!view_->startSound())&&action("enable",view_->enableOutput()))++phase_;}break;
   case 2:if(state==output::State::Ready){picture("prepared.png");if(action("keyboard-start",view_->keyPressed(juce::KeyPress(juce::KeyPress::spaceKey)))&&action("duplicate-start-refused",!view_->startSound()))++phase_;}break;
   case 3:if(p.phase==metronome::Phase::Running&&p.activeFrames>=rate/2){picture("running.png");if(action("keyboard-pause",view_->keyPressed(juce::KeyPress(juce::KeyPress::spaceKey))))++phase_;}break;
   case 4:if(state==output::State::Paused&&!view_->retained().empty()){picture("paused.png");if(action("resume",view_->resumeSound()))++phase_;}break;
   case 5:if(p.owner.generation==2&&p.phase==metronome::Phase::Running){tapAt_=now;tapCount_=0;++phase_;}break;
   case 6:if(tapCount_<4&&now-tapAt_>=static_cast<std::uint64_t>(tapCount_)*500000000ULL){const auto t=view_->tap(now);++tapCount_;if(t.status==metronome::TapStatus::Candidate)tapCandidate_=t.bpm;commands_<<now<<','<<phase_<<",scripted-handler-tap-"<<tapCount_<<','<<(int(t.status))<<'\n';}if(tapCount_==4){if(action("apply-tap-resumed-original",view_->applyTap()))++phase_;}break;
   case 7:if(tapCommand_&&p.tempo.lastCommand==tapCommand_&&p.tempo.tempo==tapCandidate_&&!p.tempo.ramp&&!p.tempo.pendingManual){if(action("manual-224",view_->manualTempo(224)))++phase_;}break;
   case 8:if(manualCommand_&&p.tempo.lastCommand==manualCommand_&&p.tempo.tempo==224&&!p.tempo.pendingManual){picture("manual-applied.png");if(action("mute-gains",view_->setMix(55,45,true))){muteAt_=platform::monotonicNs();++phase_;}}break;
   case 9:if(now-muteAt_>=250000000ULL){if(action("unmute",view_->setMix(50,50,false))&&action("keyboard-stop",view_->keyPressed(juce::KeyPress(juce::KeyPress::escapeKey))))++phase_;}break;
   case 10:if(state==output::State::Unresolved&&p.terminal){picture("stopped.png");if(action("reset-before-finish-refused",!view_->resetSound())&&action("start-before-finish-refused",!view_->startSound())&&action("finish",view_->finishSound()))++phase_;}break;
   case 11:if(!view_->soundPending()){if(action("reset",view_->resetSound())&&action("save-preset",view_->savePreset("Three with silent beat")))++phase_;}break;
   case 12:if(view_->preferencesReady()){const auto id=view_->preferences().presets.at(0).id;if(action("restore-preset",view_->restorePreset(id))&&action("restore-no-auto-start",state==output::State::Ready&&!view_->soundPending())){picture("preset-restored.png");metronome::Settings next;next.tempo=240;next.numerator=7;next.denominator=8;next.subdivision=3;next.countIn=metronome::CountIn::Off;next.styles={metronome::Style::Accent,metronome::Style::Silent,metronome::Style::Normal,metronome::Style::Silent,metronome::Style::Accent,metronome::Style::Normal,metronome::Style::Silent};if(action("apply-7-8-sub3",view_->applySettings(next))&&action("second-explicit-start",view_->startSound()))++phase_;}}break;
   case 13:if(p.phase==metronome::Phase::Running&&p.activeFrames>=rate){picture("seven-eight.png");if(action("second-stop",view_->stopSound()))++phase_;}break;
   case 14:if(state==output::State::Unresolved&&p.terminal){if(action("second-finish",view_->finishSound()))++phase_;}break;
   case 15:if(!view_->soundPending()){if(action("reset-before-polyrhythm",view_->resetSound())){metronome::Settings poly;poly.tempo=120;poly.numerator=4;poly.denominator=4;poly.subdivision=2;poly.countIn=metronome::CountIn::Off;poly.polyrhythmEnabled=true;poly.x=5;poly.y=7;poly.styles={metronome::Style::Accent,metronome::Style::Normal,metronome::Style::Normal,metronome::Style::Normal};poly.ramp.reset();if(action("apply-polyrhythm-5-7",view_->applySettings(poly))&&action("polyrhythm-settings-retained",view_->settings().polyrhythmEnabled&&view_->settings().x==5&&view_->settings().y==7&&view_->settings().countIn==metronome::CountIn::Off&&!view_->settings().ramp&&!view_->soundPending())&&action("polyrhythm-explicit-start",view_->startSound()))++phase_;}}break;
   case 16:if(p.phase==metronome::Phase::Running&&p.activeFrames>=rate){picture("polyrhythm-5-7.png");if(action("polyrhythm-layer-facts",polyLayerA_>0&&polyLayerB_>0)&&action("polyrhythm-stop",view_->stopSound()))++phase_;}break;
   case 17:if(state==output::State::Unresolved&&p.terminal){if(action("polyrhythm-finish",view_->finishSound()))++phase_;}break;
   case 18:if(!view_->soundPending()){if(action("final-reset",view_->resetSound())&&action("safe-close",view_->requestClose())){++phase_;finish(false,"finite desktop metronome transport/tap/manual/mix/preset plus native 5-7 polyrhythm integration");}}break;
   default:finish(true,"invalid actor phase");
  }
 }
 platform::OutputCapability expected_;
 std::filesystem::path root_;std::ofstream events_,facts_,progress_,segments_,commands_,ui_,replies_;std::unique_ptr<storage::ProfileStore> store_;std::unique_ptr<desktop::MetronomeView> view_;std::uint64_t begin_{},tapAt_{},muteAt_{},tapCommand_{},manualCommand_{};std::size_t polyLayerA_{},polyLayerB_{};int phase_{},tapCount_{},tapCandidate_{};bool done_{},failed_{},imageFailed_{},replyRefused_{};
};
}
int main(int argc,char** argv){
 if(argc==3&&std::string(argv[1])=="--focus-probe")return focusProbe(argv[2]);
 if(argc==2&&std::string(argv[1])=="--preflight"){const auto c=platform::defaultOutputCapability();using V=json::Value;auto n=[](auto x){return V::fromInteger(x);};std::cout<<storage::canonical(V::Object{{"valid",c.valid},{"object",n(c.object)},{"uid",c.uid},{"name",c.name},{"rate",n(c.rate)},{"physicalFrames",n(c.physicalFrames)},{"minFrames",n(c.minFrames)},{"maxFrames",n(c.maxFrames)},{"outputChannels",n(c.outputChannels)},{"selectedClientFrames",n(c.valid?std::clamp(256U,c.minFrames,c.maxFrames):0U)}})<<'\n';return c.valid?0:1;}
 if(argc!=4||std::string(argv[1])!="--run")return 2;const std::filesystem::path root=argv[2];if(!root.is_absolute()||!std::filesystem::is_directory(root)||!std::filesystem::is_empty(root))return 2;
 try{std::ifstream input(argv[3]);const std::string bytes((std::istreambuf_iterator<char>(input)),{});const auto v=json::parse(bytes);platform::OutputCapability expected;auto n=[&](const char* key){std::int64_t x{};if(!v.object().at(key).integer(x)||x<0||x>UINT32_MAX)throw std::runtime_error("Invalid capability integer");return static_cast<std::uint32_t>(x);};expected.valid=v.object().at("valid").boolean();expected.object=n("object");expected.uid=v.object().at("uid").string();expected.name=v.object().at("name").string();expected.rate=n("rate");expected.physicalFrames=n("physicalFrames");expected.minFrames=n("minFrames");expected.maxFrames=n("maxFrames");expected.outputChannels=n("outputChannels");if(!expected.valid||n("selectedClientFrames")!=std::clamp(256U,expected.minFrames,expected.maxFrames))return 2;
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];juce::ScopedJuceInitialiser_GUI gui;Run run(root,expected);juce::MessageManager::getInstance()->runDispatchLoop();return run.result();
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 2;}
}
