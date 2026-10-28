#include <CoreAudio/CoreAudio.h>
#include <array>
#include <atomic>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <filesystem>
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
#include "practice_capture_fixtures.hpp"
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
class Run final:private juce::Timer {
public:
 explicit Run(std::filesystem::path root):root_(std::move(root)),events_(root_/"native-events.csv"),facts_(root_/"scheduled-facts.csv"),progress_(root_/"progress.csv"),commands_(root_/"commands.csv"),ui_(root_/"ui.csv"),storeLog_(root_/"store-operations.csv"){
  events_<<"ns,epoch,kind,serial,object,selector,scope,element,frames,flags,status,raw_host,sample_time,rate_scalar,peak,text_utf8_hex\n";facts_<<"observed_ns,uuid,generation,epoch,binding,frame,cycle,kind,event,role,action\n";
  progress_<<"observed_ns,uuid,generation,epoch,sequence,state,client_accepted,scheduled,active,completed,cursor,requested_stop_ns,uncertain,physical_confirmed,has_physical,terminal,partial,fault\n";
  commands_<<"ns,phase,action,accepted\n";ui_<<"ns,phase,state,active,cycles,output_state,callbacks,capture_phase,initial_ack,checkpoint_seq,start_taken,owner\n";
  storeLog_<<"ns,phase,operation\n";
  std::filesystem::permissions(root_,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
  storage::StoreOptions options;options.path=root_/"profile.sqlite";options.create=true;options.createdUtc=utcNow();
  options.diagnosticHook=[this](const std::string& phase,const std::string& op){storeLog_<<platform::monotonicNs()<<','<<phase<<','<<op<<'\n';};
  store_=std::make_unique<storage::ProfileStore>(options);const auto session=capture_fixture::confirmed(store_->createSession(storage::newUuid(),utcNow(),"America/New_York",{},json::Value::Object{{"synthetic_fixture",true}}));
  view_=std::make_unique<desktop::PracticeView>();
  if(!view_->configureCapture(*store_,session.owner,utcNow,"America/New_York"))throw std::runtime_error("Capture attachment refused");view_->setSize(920,660);view_->addToDesktop(juce::ComponentPeer::windowHasTitleBar);view_->setVisible(true);
  view_->onNativeEvent=[this](const platform::NativeEvent& e){events_<<e.ns<<','<<e.epoch<<','<<e.kind<<','<<e.serial<<','<<e.object<<','<<e.selector<<','<<e.scope<<','<<e.element<<','<<e.frames<<','<<e.flags<<','<<e.status<<','<<e.rawHost<<','<<std::setprecision(17)<<e.sampleTime<<','<<e.rateScalar<<','<<e.peak<<','<<hexText(e.text.data())<<'\n';};
  view_->onScheduledFact=[this](const scheduler::Fact& f){facts_<<platform::monotonicNs()<<','<<uuid(f.owner)<<','<<f.owner.generation<<','<<f.owner.epoch<<','<<f.binding<<','<<f.frame<<','<<f.cycle<<','<<int(f.kind)<<','<<f.sourceEvent<<','<<int(f.role)<<','<<int(f.action)<<'\n';};
  view_->onProgress=[this](const practice::Progress& p){progress_<<platform::monotonicNs()<<','<<uuid(p.owner)<<','<<p.owner.generation<<','<<p.owner.epoch<<','<<p.sequence<<','<<int(p.state)<<','<<p.clientAcceptedThrough<<','<<p.scheduledThrough<<','<<p.activeFrames<<','<<p.completedCycles<<','<<p.cursorFrames<<','<<p.requestedStopNs<<','<<p.uncertainThrough<<','<<p.physicalConfirmedThrough<<','<<p.hasPhysicalConfirmation<<','<<p.terminal<<','<<p.partial<<','<<p.fault<<'\n';};
  begin_=platform::monotonicNs();startTimer(20);
 }
 int result()const{return done_&&!failed_?0:1;}
private:
 bool action(const char* name,bool ok){commands_<<platform::monotonicNs()<<','<<phase_<<','<<name<<','<<ok<<'\n';if(!ok)finish(true,"control refused");return ok;}
 void picture(const std::string& name){auto image=view_->createComponentSnapshot(view_->getLocalBounds());juce::FileOutputStream out(juce::File((root_/name).string()));juce::PNGImageFormat png;const bool wrote=out.openedOk() && png.writeImageToStream(image,out);out.flush();imageFailed_|=!wrote || out.getStatus().failed();}
 void finish(bool failed,const char* reason){if(done_)return;done_=true;stopTimer();
  struct DispatchExit {~DispatchExit(){juce::MessageManager::getInstance()->stopDispatchLoop();}} exit;
  try {view_->quiesceAndRetain();failed_=failed||captureOverflow.load();picture("final-view.png");failed_|=imageFailed_;const auto c=view_->coordinator();const auto s=view_->outputStatus();
  failed_=failed_ || s.cleanupFailed || s.nativeSkips || platform::hub.dropped.load() || s.lifecycle.fault!=output::Fault::None || !view_->error().empty();
  for(auto* stream:{&events_,&facts_,&progress_,&commands_,&ui_}){stream->flush();failed_|=!stream->good();}
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
 void timerCallback()override{
  const auto s=view_->outputStatus();const auto& c=view_->coordinator();const auto now=platform::monotonicNs();ui_<<now<<','<<phase_<<','<<int(c.state())<<','<<c.activeFrames()<<','<<c.completedCycles()<<','<<int(s.lifecycle.state)<<','<<s.callbacks;
  auto* capture=const_cast<capture::PracticeSession*>(view_->captureSession());const auto cp=capture->checkpointState(static_cast<std::int64_t>(now/1000000));
  ui_<<','<<int(capture->phase())<<','<<cp.initialAcknowledged<<','<<(cp.acknowledged?cp.acknowledged->sequence:-1)<<','<<capture->startTaken()<<','<<capture->binding().owner<<'\n';
  if(now-begin_>45000000000ULL){finish(true,"45 second watchdog");return;}
  if(s.lifecycle.state==output::State::Fault || !view_->error().empty() || captureOverflow){finish(true,"unexpected output/transport error");return;}
  const auto rate=s.lifecycle.request.format.rate;const auto& gens=c.generations();const auto* last=gens.empty()?nullptr:&gens.back();
  switch(phase_){
   case 0:if(action("connect",view_->connectOutput()))++phase_;break;
   case 1:if(s.lifecycle.state==output::State::Observed){if(action("acknowledge",view_->enableOutput()))++phase_;}break;
   case 2:if(s.lifecycle.state==output::State::Ready){if(action("start-first",view_->startSample())&&action("duplicate-start-refused",!view_->startSample()))++phase_;}break;
   case 3:if(last&&last->clientAcceptedThrough>=rate/4&&last->state==practice::State::CountIn){if(action("pause-count-in",view_->pauseSample()))++phase_;}break;
   case 4:if(c.state()==practice::State::Paused){if(action("keyboard-resume",view_->keyPressed(juce::KeyPress(juce::KeyPress::spaceKey))))++phase_;}break;
   case 5:if(last&&last->activeFrames>=rate*3/2&&last->state==practice::State::Running){picture("partial-running.png");if(action("keyboard-stop-rest",view_->keyPressed(juce::KeyPress(juce::KeyPress::escapeKey))))++phase_;}break;
   case 6:if(capture->phase()==capture::SessionPhase::Review){if(action("choose-Clean",view_->chooseAssessment("Clean"))){picture("assessment.png");if(action("close-before-save-refused",!view_->requestClose())&&action("save-selected-partial-Clean",view_->saveSelectedAssessment())&&action("sealed-Easy-change-refused",!view_->chooseAssessment("Easy"))&&action("repeated-save-refused",!view_->saveSample("Easy"))&&action("Again-pending-refused",!view_->againSample()))++phase_;}}break;
   case 7:if(capture->phase()==capture::SessionPhase::Saved&&capture->canLeave(!s.lifecycle.ownsOutcome&&!s.lifecycle.pendingOutcome)){picture("saved-first.png");capture_fixture::write(root_/"first-original.json",capture->original()->bytes);snapshot_.emplace(store_->snapshot(storage::newUuid()));++phase_;}break;
   case 8:if(snapshot_->wait_for(std::chrono::milliseconds(0))==std::future_status::ready){auto r=snapshot_->get();snapshot_.reset();if(r.status!=storage::Status::Confirmed){finish(true,"snapshot failure");return;}capture_fixture::write(root_/"first-snapshot.json",storage::canonical(r.data));if(action("deliberate-Again",view_->againSample())&&action("Again-does-not-autoplay",view_->coordinator().state()==practice::State::Stopped))++phase_;}break;
   case 9:if(action("explicit-second-Start",view_->startSample()))++phase_;break;
   case 10:if(last&&last->clientAcceptedThrough>=rate/4&&last->state==practice::State::CountIn){if(action("cancel-second-count-in",view_->stopSample()))++phase_;}break;
   case 11:if(capture->phase()==capture::SessionPhase::Review){if(action("choose-no-assessment",view_->chooseAssessment(nullptr))&&action("save-zero-no-assessment",view_->saveSelectedAssessment()))++phase_;}break;
   case 12:if(capture->phase()==capture::SessionPhase::Saved&&capture->canLeave(!s.lifecycle.ownsOutcome&&!s.lifecycle.pendingOutcome)){capture_fixture::write(root_/"second-original.json",capture->original()->bytes);++phase_;}break;
   case 13:if(view_->requestClose()){snapshot_.emplace(store_->snapshot(storage::newUuid()));++phase_;}break;
   case 14:if(snapshot_->wait_for(std::chrono::milliseconds(0))==std::future_status::ready){auto r=snapshot_->get();snapshot_.reset();if(r.status!=storage::Status::Confirmed){finish(true,"finalsnapshot failure");return;}capture_fixture::write(root_/"snapshot.json",storage::canonical(r.data));++phase_;finish(false,"native original allocation/checkpoint, partial self-report, confirmed save, deliberateAgain and zero count-in cancellation");}break;
   default:finish(true,"invalid phase");
  }
 }
 std::filesystem::path root_;std::ofstream events_,facts_,progress_,commands_,ui_,storeLog_;std::unique_ptr<storage::ProfileStore> store_;std::optional<storage::ProfileStore::Future> snapshot_;std::unique_ptr<desktop::PracticeView> view_;std::uint64_t begin_{};int phase_{};bool done_{},failed_{},imageFailed_{};
};
}
int main(int argc,char** argv){
 if(argc==2&&std::string(argv[1])=="--preflight"){const auto c=platform::defaultOutputCapability();std::cout<<"valid="<<c.valid<<" uid="<<c.uid<<" name="<<std::quoted(c.name)<<" rate="<<c.rate<<" physicalFrames="<<c.physicalFrames<<" min="<<c.minFrames<<" max="<<c.maxFrames<<" channels="<<c.outputChannels<<'\n';return c.valid?0:1;}
 if(argc!=3||std::string(argv[1])!="--run")return 2;const std::filesystem::path root=argv[2];if(!root.is_absolute()||!std::filesystem::is_directory(root)||!std::filesystem::is_empty(root))return 2;
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];juce::ScopedJuceInitialiser_GUI gui;Run run(root);juce::MessageManager::getInstance()->runDispatchLoop();return run.result();
}
