#include <CoreAudio/CoreAudio.h>
#include <array>
#include <atomic>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <filesystem>
namespace {
constexpr std::size_t captureLimit=44100*45*2;
std::array<float,captureLimit> captured{};std::size_t captureCount{};std::atomic<bool> captureOverflow{false};
struct CaptureBlock {std::uint64_t serial{},offset{};std::uint32_t epoch{},object{},frames{},buffer{},channels{},floats{};};
std::array<CaptureBlock,100000> captureBlocks{};std::size_t captureBlocksCount{};
void captureNative(int,const AudioBufferList*)noexcept;
}
#define FATHOM_TEST_NATIVE_CAPTURE captureNative
#include "../Source/platform/AudioOutputMac.mm"
#include "platform/MetronomePlayback.hpp"
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
class Run final:private juce::Timer {
public:
 explicit Run(std::filesystem::path root):root_(std::move(root)),events_(root_/"native-events.csv"),facts_(root_/"facts.csv"),progress_(root_/"progress.csv"),segments_(root_/"segments.csv"),commands_(root_/"commands.csv"),states_(root_/"states.csv"),replies_(root_/"tempo-replies.csv"),retainedFile_(root_/"retained-generations.jsonl"){
  events_<<"ns,epoch,kind,serial,object,selector,scope,element,frames,flags,status,raw_host,sample_time,rate_scalar,peak,text_utf8_hex\n";
  facts_<<"ns,uuid,generation,epoch,binding,frame,cycle,kind,event,role,action\n";
  progress_<<"ns,uuid,generation,epoch,sequence,scheduled,accepted,active,total_active,cycles,cursor,bar_frames,tempo,pending_manual,ramp_target,ramp_count,phase,terminal,partial,fault,requested_stop_ns,uncertain,physical_confirmed,has_physical\n";
  segments_<<"ns,uuid,generation,epoch,binding,from,through,tempo,count_in\n";commands_<<"ns,phase,action,queue_admitted_or_assertion_passed\n";
  states_<<"ns,phase,output_state,callbacks,rendered,submitted,owner,generation,epoch,mute\n";replies_<<"ns,uuid,generation,binding,sequence,tempo,accepted\n";
  cap_=platform::defaultOutputCapability();if(!cap_.valid||cap_.uid!="BuiltInSpeakerDevice"||cap_.rate!=44100||cap_.physicalFrames!=512||cap_.minFrames!=14||cap_.maxFrames!=4096||cap_.outputChannels!=2)throw std::runtime_error("Frozen capability changed; no native connect");
  owner_.id[6]=0x40;owner_.id[8]=0x80;owner_.id[15]=1;owner_.generation=1;
  begin_=platform::monotonicNs();startTimer(10);
 }
 int result()const{return done_&&!failed_?0:1;}
private:
 bool action(const char* name,bool okay){commands_<<platform::monotonicNs()<<','<<phase_<<','<<name<<','<<okay<<'\n';commands_.flush();if(!okay)finish(true,name);return okay;}
 bool send(platform::OutputCommand op,const char* name,output::Owner next={}){const auto l=output_.status().lifecycle;platform::Control c;c.op=op;c.owner=owner_;c.nextOwner=next;c.epoch=l.request.epoch;c.token=l.observationToken;c.requestedNs=platform::monotonicNs();return action(name,output_.send(c));}
 void drain(){platform::NativeEvent e;while(output_.nextEvent(e))events_<<e.ns<<','<<e.epoch<<','<<e.kind<<','<<e.serial<<','<<e.object<<','<<e.selector<<','<<e.scope<<','<<e.element<<','<<e.frames<<','<<e.flags<<','<<e.status<<','<<e.rawHost<<','<<std::setprecision(17)<<e.sampleTime<<','<<e.rateScalar<<','<<e.peak<<','<<hexText(e.text.data())<<'\n';
  scheduler::Fact f;while(player_.nextFact(f))facts_<<platform::monotonicNs()<<','<<uuid(f.owner)<<','<<f.owner.generation<<','<<f.owner.epoch<<','<<f.binding<<','<<f.frame<<','<<f.cycle<<','<<int(f.kind)<<','<<f.sourceEvent<<','<<int(f.role)<<','<<int(f.action)<<'\n';
  platform::MetronomeProgress p;while(player_.nextProgress(p)){p_=p;progress_<<platform::monotonicNs()<<','<<uuid(p.owner)<<','<<p.owner.generation<<','<<p.owner.epoch<<','<<p.sequence<<','<<p.scheduledThrough<<','<<p.clientAcceptedThrough<<','<<p.activeFrames<<','<<p.totalActiveFrames<<','<<p.completedCycles<<','<<p.cursorFrames<<','<<p.barFrames<<','<<p.tempo.tempo<<','<<p.tempo.pendingManual.value_or(0)<<','<<(p.tempo.ramp?p.tempo.ramp->target:0)<<','<<p.tempo.count<<','<<int(p.phase)<<','<<p.terminal<<','<<p.partial<<','<<p.fault<<','<<p.requestedStopNs<<','<<p.uncertainThrough<<','<<p.physicalConfirmedThrough<<','<<p.hasPhysicalConfirmation<<'\n';}
  platform::MetronomeSegment seg;while(player_.nextSegment(seg))segments_<<platform::monotonicNs()<<','<<uuid(seg.owner)<<','<<seg.owner.generation<<','<<seg.owner.epoch<<','<<seg.binding<<','<<seg.from<<','<<seg.through<<','<<seg.tempo<<','<<seg.countIn<<'\n';
  while(player_.reclaim(p)){p_=p;pendingRetained_.push_back(p);}
  const auto joined=output_.status();
  for(auto it=pendingRetained_.begin();it!=pendingRetained_.end();){const auto& l=joined.lifecycle;
   if(l.owner==it->owner && l.request.epoch==it->owner.epoch && l.submittedFrames==it->clientAcceptedThrough && l.state==(it->fault?output::State::Fault:it->phase==metronome::Phase::Paused?output::State::Paused:output::State::Unresolved)){retain(*it,joined,true);retained_.push_back(*it);it=pendingRetained_.erase(it);}else ++it;
  }
  platform::MetronomeReply reply;while(player_.nextReply(reply))replies_<<platform::monotonicNs()<<','<<uuid(reply.owner)<<','<<reply.owner.generation<<','<<reply.binding<<','<<reply.sequence<<','<<reply.tempo<<','<<reply.accepted<<'\n';
 }
 void retain(const platform::MetronomeProgress& p,const platform::OutputStatus& status,bool joined){
  retainedFile_<<"{\"retained_ns\":"<<platform::monotonicNs()<<",\"uuid\":"<<std::quoted(uuid(p.owner));
  auto field=[&](const char* k,auto v){retainedFile_<<','<<std::quoted(k)<<':'<<v;};
  field("generation",p.owner.generation);field("epoch",p.owner.epoch);field("binding",p.binding);field("sequence",p.sequence);field("scheduled",p.scheduledThrough);field("accepted",p.clientAcceptedThrough);field("active",p.activeFrames);field("total_active",p.totalActiveFrames);field("completed_cycles",p.completedCycles);field("cursor",p.cursorFrames);field("bar_frames",p.barFrames);field("requested_stop_ns",p.requestedStopNs);field("uncertain",p.uncertainThrough);field("physical_confirmed",p.physicalConfirmedThrough);field("has_physical",p.hasPhysicalConfirmation);field("phase",int(p.phase));field("terminal",p.terminal);field("fault",p.fault);field("partial",p.partial);
  const auto& t=p.tempo;field("tempo",t.tempo);field("ramp_present",bool(t.ramp));field("ramp_up",t.ramp?t.ramp->up:false);field("ramp_step",t.ramp?t.ramp->step:0);field("ramp_every",t.ramp?t.ramp->every:0);field("ramp_target",t.ramp?t.ramp->target:0);field("ramp_count",t.count);field("completed_through",t.completedThrough);field("last_command",t.lastCommand);field("pending_manual_present",bool(t.pendingManual));field("pending_manual",t.pendingManual.value_or(0));field("resumable",t.resumable);
  field("output_joined",joined);const auto& l=status.lifecycle;retainedFile_<<",\"output_owner\":"<<std::quoted(uuid(l.owner));field("output_generation",l.owner.generation);field("output_epoch",l.owner.epoch);field("output_state",int(l.state));field("output_fault",int(l.fault));field("output_submitted",l.submittedFrames);field("output_confirmed",l.confirmedFrames);field("output_uncertain",l.uncertainThrough);field("output_has_confirmation",l.hasConfirmation);field("output_requested_stop_ns",l.requestedStopNs);field("output_first_stop_marker_ns",l.firstSilenceNs);field("output_first_silent_callback_ns",status.firstSilentCallbackNs);field("output_pending",l.pendingOutcome);field("output_owns_outcome",l.ownsOutcome);retainedFile_<<"}\n";retainedFile_.flush();if(!retainedFile_.good())throw std::runtime_error("Terminal diagnostic record write failed; do not resolve output");
 }
 bool mix(bool muted){auto c=platform::Control{};c.op=platform::OutputCommand::Mix;c.epoch=output_.status().lifecycle.request.epoch;c.mix.masterMute=muted;return action(muted?"master-mute":"master-unmute",output_.send(c));}
 void finish(bool failed,const char* reason){if(done_)return;done_=true;stopTimer();failed_=failed;
  struct Exit {~Exit(){juce::MessageManager::getInstance()->stopDispatchLoop();}} exit;
  try{output_.shutdown();drain();const auto s=output_.status();for(const auto& pending:pendingRetained_)retain(pending,s,false);failed_|=!pendingRetained_.empty();failed_|=s.cleanupFailed||s.nativeSkips||platform::hub.dropped.load()||captureOverflow||s.lifecycle.fault!=output::Fault::None||!output_.error().empty();
   for(auto* f:{&events_,&facts_,&progress_,&segments_,&commands_,&states_,&replies_,&retainedFile_}){f->flush();failed_|=!f->good();}
   std::ofstream raw(root_/"native-output-f32.raw",std::ios::binary);raw.write(reinterpret_cast<const char*>(captured.data()),static_cast<std::streamsize>(captureCount*sizeof(float)));raw.close();failed_|=!raw.good();
   std::ofstream map(root_/"capture-map.csv");map<<"serial,float_offset,epoch,object,frames,buffer,channels,float_count\n";for(std::size_t i=0;i<captureBlocksCount;++i){const auto& b=captureBlocks[i];map<<b.serial<<','<<b.offset<<','<<b.epoch<<','<<b.object<<','<<b.frames<<','<<b.buffer<<','<<b.channels<<','<<b.floats<<'\n';}map.close();failed_|=!map.good();
   std::ofstream final(root_/"final.json");final<<"{\"failed\":"<<(failed_?"true":"false")<<",\"reason\":"<<std::quoted(reason)<<",\"phase\":"<<phase_<<",\"callbacks\":"<<s.callbacks<<",\"rendered\":"<<s.renderedBlocks<<",\"retained_generations\":"<<retained_.size()<<",\"capture_floats\":"<<captureCount<<",\"capture_overflow\":"<<captureOverflow<<",\"event_drops\":"<<platform::hub.dropped.load()<<",\"native_skips\":"<<s.nativeSkips<<",\"overloads\":"<<s.overloads<<",\"cleanup_failed\":"<<s.cleanupFailed<<",\"fault\":"<<int(s.lifecycle.fault)<<",\"pending\":"<<s.lifecycle.pendingOutcome<<",\"owns_outcome\":"<<s.lifecycle.ownsOutcome;
   const auto& l=s.lifecycle;const auto& o=l.observation;auto field=[&](const char* k,auto v){final<<','<<std::quoted(k)<<':'<<v;};
   final<<",\"owner\":"<<std::quoted(uuid(l.owner));field("generation",l.owner.generation);field("epoch",l.owner.epoch);field("submitted",l.submittedFrames);field("confirmed",l.confirmedFrames);field("uncertain",l.uncertainThrough);field("requested_stop_ns",l.requestedStopNs);field("first_stop_marker_ns",l.firstSilenceNs);field("first_silent_callback_ns",s.firstSilentCallbackNs);field("request_epoch",l.request.epoch);field("request_ns",l.request.stampNs);field("request_rate",l.request.format.rate);field("request_frames",l.request.format.frames);field("cached_epoch",l.cached.epoch);field("cached_ns",l.cached.stampNs);field("cached_rate",l.cached.format.rate);field("cached_frames",l.cached.format.frames);field("observed_epoch",o.epoch);field("observed_rate",o.queriedIO.rate);field("observed_frames",o.queriedIO.frames);field("observed_callback_frames",o.callbackFrames);field("physical_object",o.physicalObject);field("physical_rate",o.physicalRate);field("physical_frames",o.physicalFrames);field("io_object",o.queriedIOObject);field("native_object",o.nativeIOObject);field("has_physical_confirmation",l.hasConfirmation);field("mach_timebase_numer",platform::timebase.numer);field("mach_timebase_denom",platform::timebase.denom);final<<"}\n";final.close();failed_|=!final.good();std::cout<<(failed_?"FAIL ":"PASS ")<<reason<<'\n';
  }catch(const std::exception& e){failed_=true;std::cerr<<e.what()<<'\n';}
 }
 void timerCallback()override {try{output_.service();drain();const auto s=output_.status();const auto now=platform::monotonicNs();states_<<now<<','<<phase_<<','<<int(s.lifecycle.state)<<','<<s.callbacks<<','<<s.renderedBlocks<<','<<s.lifecycle.submittedFrames<<','<<uuid(s.lifecycle.owner)<<','<<s.lifecycle.owner.generation<<','<<s.lifecycle.owner.epoch<<','<<s.mix.masterMute<<'\n';
  if(now-begin_>40000000000ULL){finish(true,"40 second total watchdog");return;}if(s.lifecycle.state==output::State::Fault||p_.fault||captureOverflow){finish(true,"native/provider/capture failure; no retry");return;}
  switch(phase_){
   case 0:if(action("connect-44100-256",output_.connect(cap_,{44100,256},nullptr,&player_,platform::MetronomePlayback::observe,platform::MetronomePlayback::render)))++phase_;break;
   case 1:if(s.lifecycle.state==output::State::Observed && s.callbacks>=20){owner_.epoch=s.lifecycle.request.epoch;if(action("enqueue-preack-start-negative",output_.send({platform::OutputCommand::Start,owner_.epoch,0,now,owner_,{}, {}})))++phase_;}break;
   case 2:if(s.commandRejected==1 && s.lifecycle.state==output::State::Observed){if(action("preack-start-refused-without-render",s.renderedBlocks==0)&&send(platform::OutputCommand::Acknowledge,"explicit-format-ack"))++phase_;}break;
   case 3:if(s.lifecycle.state==output::State::Ready){metronome::Settings c;c.tempo=240;c.numerator=7;c.denominator=8;c.subdivision=2;c.styles={metronome::Style::Accent,metronome::Style::Normal,metronome::Style::Silent,metronome::Style::Normal,metronome::Style::Normal,metronome::Style::Accent,metronome::Style::Normal};c.ramp=metronome::Ramp{true,20,1,280};if(action("prepare-odd-ramp",player_.prepare(c,owner_,1,"native-technical-7-8",44100))&&send(platform::OutputCommand::Start,"start-odd-ramp"))++phase_;}break;
   case 4:if(p_.owner==owner_ && p_.completedCycles>=2&&p_.tempo.tempo==280){if(action("queue-manual236",player_.manual(owner_,1,1,236)))++phase_;}break;
   case 5:if(p_.completedCycles>=4&&p_.tempo.tempo==236&&p_.cursorFrames>4410){if(send(platform::OutputCommand::Pause,"pause-partial-bar"))++phase_;}break;
   case 6:if(p_.terminal&&p_.phase==metronome::Phase::Paused&&retained_.size()==1){auto next=owner_;++next.generation;if(action("prepare-fresh-countin-resume",player_.prepareResume(owner_,next))&&send(platform::OutputCommand::PauseRetained,"paused-facts-retained")&&send(platform::OutputCommand::Resume,"explicit-resume",next)){owner_=next;++phase_;}}break;
   case 7:if(p_.owner==owner_&&p_.completedCycles>=5&&p_.cursorFrames>4410){mark_=p_.activeFrames;if(mix(true))++phase_;}break;
   case 8:if(p_.activeFrames>=mark_+8820){if(mix(false))++phase_;}break;
   case 9:if(p_.completedCycles>=6&&p_.cursorFrames>4410){if(send(platform::OutputCommand::Stop,"stop-original"))++phase_;}break;
   case 10:if(p_.terminal&&s.lifecycle.state==output::State::Unresolved&&retained_.size()==2){if(action("original-terminal-retained",retained_.size()==2)&&send(platform::OutputCommand::ResolveOutcome,"resolve-diagnostic-original"))++phase_;}break;
   case 11:if(s.lifecycle.state==output::State::Ready){owner_.id[15]=2;owner_.generation=1;metronome::Settings c;c.tempo=300;c.numerator=1;c.denominator=16;c.unit=scheduler::BeatUnit::Half;c.subdivision=7;c.styles={metronome::Style::Accent};c.countIn=metronome::CountIn::Off;if(action("prepare-max-density",player_.prepare(c,owner_,2,"native-technical-density",44100))&&send(platform::OutputCommand::Start,"start-max-density"))++phase_;}break;
   case 12:if(p_.owner==owner_&&p_.activeFrames>=13230){if(send(platform::OutputCommand::Stop,"stop-max-density"))++phase_;}break;
   case 13:if(p_.terminal&&s.lifecycle.state==output::State::Unresolved&&retained_.size()==3){if(action("dense-terminal-retained",retained_.size()==3)&&send(platform::OutputCommand::ResolveOutcome,"resolve-diagnostic-density"))++phase_;}break;
   case 14:if(s.lifecycle.state==output::State::Ready){owner_.id[15]=3;metronome::Settings c;c.tempo=240;c.numerator=3;c.styles={metronome::Style::Silent,metronome::Style::Silent,metronome::Style::Silent};c.subdivision=2;if(action("prepare-silent-with-countin",player_.prepare(c,owner_,3,"native-technical-silent",44100))&&send(platform::OutputCommand::Start,"start-countin-cancellation"))++phase_;}break;
   case 15:if(p_.owner==owner_&&p_.clientAcceptedThrough>=11025&&p_.phase==metronome::Phase::CountIn){if(send(platform::OutputCommand::Stop,"stop-countin"))++phase_;}break;
   case 16:if(p_.terminal&&s.lifecycle.state==output::State::Unresolved&&retained_.size()==4){if(action("countin-zero-active-retained",retained_.size()==4&&p_.activeFrames==0&&p_.completedCycles==0)&&send(platform::OutputCommand::ResolveOutcome,"resolve-diagnostic-countin"))++phase_;}break;
   case 17:if(s.lifecycle.state==output::State::Ready){if(action("disconnect-resolved",output_.disconnect())){++phase_;finish(false,"one fixed-format metronome sequence completed");}}break;
   default:finish(true,"invalid sequence phase");
  }
 }catch(const std::exception& e){finish(true,e.what());}}
 std::filesystem::path root_;std::ofstream events_,facts_,progress_,segments_,commands_,states_,replies_,retainedFile_;platform::MetronomePlayback player_;platform::AudioOutputMac output_;platform::OutputCapability cap_;output::Owner owner_;platform::MetronomeProgress p_;std::vector<platform::MetronomeProgress> retained_,pendingRetained_;std::uint64_t begin_{},mark_{};int phase_{};bool done_{},failed_{};
};
}
int main(int argc,char** argv){
 if(argc==2&&std::string(argv[1])=="--preflight"){const auto c=platform::defaultOutputCapability();std::cout<<"valid="<<c.valid<<" uid="<<c.uid<<" name="<<std::quoted(c.name)<<" rate="<<c.rate<<" physicalFrames="<<c.physicalFrames<<" min="<<c.minFrames<<" max="<<c.maxFrames<<" channels="<<c.outputChannels<<'\n';return c.valid?0:1;}
 if(argc!=3||std::string(argv[1])!="--run")return 2;const std::filesystem::path root=argv[2];if(!root.is_absolute()||!std::filesystem::is_directory(root)||!std::filesystem::is_empty(root))return 2;
 [NSApplication sharedApplication];juce::ScopedJuceInitialiser_GUI gui;try{Run run(root);juce::MessageManager::getInstance()->runDispatchLoop();return run.result();}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
