// The test compiles the exact production adapter in this translation unit to inspect
// its private mechanics. The test capture seam is absent from production builds.
#include <CoreAudio/CoreAudio.h>
#include <array>
#include <atomic>
#include <cmath>
#include <fstream>
#include <filesystem>
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


#include "platform/ReferencePlayback.hpp"
#include "reference_audio_fixtures.hpp"
namespace {
using namespace fathom;
std::string uuid(const scheduler::Owner& o){std::ostringstream text;text<<std::hex<<std::setfill('0');for(auto b:o.id)text<<std::setw(2)<<static_cast<unsigned>(b);return text.str();}
struct Piece {std::string name;music::Model model;Rational offset,cycle;};
std::vector<Piece> pieces(){auto controls=controlExamples();return {{"l12",controls[2],Rational{},Rational{8}},{"l15",controls[3],Rational{17,2},Rational{1}},{"E",reference_fixtures::chord(false),Rational{10},Rational{5,2}},{"Em",reference_fixtures::chord(true),Rational{13},Rational{5,2}},{"held",reference_fixtures::held(),Rational{16},Rational{3,2}},{"repicked",reference_fixtures::held(true),Rational{18},Rational{3,2}},{"contacts",reference_fixtures::contacts(),Rational{20},Rational{9,2}}};}
music::Model compound(){
 auto model=reference_fixtures::synthetic("native-reference-compound");std::ostringstream records;records<<"{\"synthetic_native_compound\":true,\"source_records\":[";bool first=true;
 for(auto piece:pieces()) {
    if(!first)records<<',';first=false;records<<piece.model.preservedRecordJson;
    for(const auto& source:piece.model.sourceRefs)model.sourceRefs.push_back(source);
    for(auto event:piece.model.events){const auto original=event.id;event.id=piece.name+"/"+original;event.span.onset=*event.span.onset+piece.offset;
        for(auto& t:event.tones){if(!t.tieFrom.empty())t.tieFrom=piece.name+"/"+t.tieFrom;if(t.memberSpan && t.memberSpan->onset)t.memberSpan->onset=*t.memberSpan->onset+piece.offset;if(t.soundingSpan && t.soundingSpan->onset)t.soundingSpan->onset=*t.soundingSpan->onset+piece.offset;}
        model.events.push_back(std::move(event));
    }
    if(piece.name!="contacts")model.events.push_back(reference_fixtures::rest(piece.name+"/synthetic-gap",piece.offset+piece.cycle,Rational{1,2}));
 }
 records<<"],\"departures\":\"Exact retained core QA bindings; namespaced IDs/ties; six half-quarter inter-case rests. No runtime curriculum admission.\"}";model.preservedRecordJson=records.str();return model;
}
reference::Program program(int index,const scheduler::Owner& owner) {
 if(index==0){auto c=reference_fixtures::config(Rational{49,2});c.owner=owner;c.binding=1;c.sourceBinding="synthetic:native-reference-compound-v1";return reference::compile(reference_fixtures::checked(compound()),c);}
 guitar::Setup setup;setup.openMidi=guitar::tuning(guitar::Preset::DropD);setup.capo=2;
 return reference::tuningTone(setup,1,index==1?reference::ToneTarget::OpenString:reference::ToneTarget::CapoPosition,owner,static_cast<std::uint64_t>(index+1),44100,reference::Method::Sine);
}
void describe(const std::string& root) {
 std::filesystem::create_directories(root);
 std::ofstream map(root+"/source-map.csv");map<<"case,synthetic_event,source_event,source_ref,offset_q_n,offset_q_d\n";
 for(const auto& piece:pieces())for(const auto& event:piece.model.events)map<<piece.name<<','<<piece.name<<'/'<<event.id<<','<<event.id<<','<<event.sourceRef<<','<<piece.offset.numerator()<<','<<piece.offset.denominator()<<'\n';
 for(int index=0;index<3;++index){auto owner=reference_fixtures::owner();owner.generation=owner.epoch=static_cast<std::uint64_t>(index+1);auto p=program(index,owner);
    std::ofstream v(root+"/case-"+std::to_string(index+1)+"-voices.csv");v<<"id,string,midi,hz,start_n,start_d,end_n,end_d,source_events\n";std::size_t id=0;for(const auto& voice:p.voices()){v<<++id<<','<<voice.string<<','<<voice.midi<<','<<std::setprecision(17)<<voice.hz<<','<<voice.startFrames.n<<','<<voice.startFrames.d<<','<<voice.endFrames.n<<','<<voice.endFrames.d<<',';for(const auto& event:voice.sourceEvents)v<<event<<';';v<<'\n';}
    std::ofstream spec(root+"/case-"+std::to_string(index+1)+".json");spec<<"{\"case\":"<<index+1<<",\"rate\":44100,\"bpm\":"<<(index?60:120)<<",\"binding\":"<<index+1<<",\"method\":"<<int(p.method())<<",\"duration_n\":"<<p.schedule().duration().n<<",\"duration_d\":"<<p.schedule().duration().d<<",\"voices\":"<<p.voices().size()<<",\"events\":"<<p.schedule().events().size()<<",\"sourceBinding\":"<<std::quoted(p.schedule().sourceBinding())<<",\"sourceRecord\":"<<(p.source().source().preservedRecordJson.empty()?"null":p.source().source().preservedRecordJson);
    if(index)spec<<",\"setup\":{\"openMidi\":[38,45,50,55,59,64],\"capo\":2,\"internalString\":1,\"target\":"<<std::quoted(index==1?"OpenString":"CapoPosition")<<"}";
    spec<<"}\n";if(!v || !spec || !map)throw std::runtime_error("Cannot retain native source description");
 }
}
void snapshotJSON(std::ostream& out,const output::Snapshot& s,const scheduler::StreamView& v,std::uint64_t silent){out<<"{\"uuid\":\""<<uuid(s.owner)<<"\",\"generation\":"<<s.owner.generation<<",\"epoch\":"<<s.owner.epoch<<",\"state\":"<<int(s.state)<<",\"fault\":"<<int(s.fault)<<",\"submitted\":"<<s.submittedFrames<<",\"confirmed\":"<<s.confirmedFrames<<",\"hasConfirmation\":"<<(s.hasConfirmation?"true":"false")<<",\"uncertainThrough\":"<<s.uncertainThrough<<",\"pending\":"<<(s.pendingOutcome?"true":"false")<<",\"ownsOutcome\":"<<(s.ownsOutcome?"true":"false")<<",\"requestedStopNs\":"<<s.requestedStopNs<<",\"firstStopMarkerNs\":"<<s.firstSilenceNs<<",\"firstSilentCallbackNs\":"<<silent<<",\"cursorUUID\":\""<<uuid(v.cursor.owner)<<"\",\"cursorGeneration\":"<<v.cursor.owner.generation<<",\"cursorEpoch\":"<<v.cursor.owner.epoch<<",\"binding\":"<<v.cursor.binding<<",\"processed\":"<<v.cursor.processedThrough<<",\"cycles\":"<<v.cursor.completedCycles<<",\"cursorState\":"<<int(v.cursor.state)<<",\"cursorReason\":"<<int(v.cursor.reason)<<",\"cursorConfirmed\":"<<v.cursor.confirmedThrough<<",\"cursorHasConfirmation\":"<<(v.cursor.hasConfirmation?"true":"false")<<",\"cursorUncertain\":"<<v.cursor.uncertainThrough<<",\"boundaryFactPending\":"<<(v.cursor.boundaryFactPending?"true":"false")<<",\"streamFailed\":"<<(v.failed?"true":"false")<<"}";}
class Run final:private juce::Timer {
public:
 explicit Run(std::string root):root_(std::move(root)),events_(root_+"/events.csv"),facts_(root_+"/facts.csv"),views_(root_+"/views.csv"),states_(root_+"/states.csv"),commands_(root_+"/commands.csv") {
    events_<<"ns,epoch,kind,serial,object,selector,scope,element,frames,flags,status,sample_time,rate_scalar,peak,raw_host,text\n";
    facts_<<"case,kind,uuid,epoch,generation,binding,frame,cycle,event,role,action\n";
    views_<<"case,observed_ns,block,begin,prefix,state,processed,cycles,tempo,phase_origin,phase_n,phase_d,accepted,rejected,drops,failed\n";
    states_<<"ns,case,step,state,submitted,confirmed,uncertain,first_silent,callbacks,rendered\n";
    commands_<<"ns,case,op,uuid,generation,epoch,binding,token,requested_ns,queued\n";
    start_=platform::monotonicNs();startTimer(20);
 }
 int result()const{return done_&&!failed_&&completed_==3?0:1;}
private:
 void drain(){platform::NativeEvent e;while(output_.nextEvent(e)){std::string text=e.text.data();for(auto& c:text)if(c==','||c=='\n'||c=='\r')c=' ';events_<<e.ns<<','<<e.epoch<<','<<e.kind<<','<<e.serial<<','<<e.object<<','<<e.selector<<','<<e.scope<<','<<e.element<<','<<e.frames<<','<<e.flags<<','<<e.status<<','<<std::setprecision(17)<<e.sampleTime<<','<<e.rateScalar<<','<<e.peak<<','<<e.rawHost<<','<<text<<'\n';}
    if(playback_){scheduler::Fact f;while(playback_->stream().nextFact(f))facts_<<index_+1<<','<<int(f.kind)<<','<<uuid(f.owner)<<','<<f.owner.epoch<<','<<f.owner.generation<<','<<f.binding<<','<<f.frame<<','<<f.cycle<<','<<f.sourceEvent<<','<<int(f.role)<<','<<int(f.action)<<'\n';scheduler::StreamView v;while(playback_->stream().nextView(v)){latest_=v;views_<<index_+1<<','<<platform::monotonicNs()<<','<<v.block<<','<<v.blockBegin<<','<<v.prefix<<','<<int(v.cursor.state)<<','<<v.cursor.processedThrough<<','<<v.cursor.completedCycles<<','<<v.tempoIndex<<','<<v.phaseOrigin<<','<<v.phaseSpan.n<<','<<v.phaseSpan.d<<','<<v.acceptedCommands<<','<<v.rejectedCommands<<','<<v.displayDrops<<','<<v.failed<<'\n';}}
    auto s=output_.status();states_<<platform::monotonicNs()<<','<<index_+1<<','<<step_<<','<<int(s.lifecycle.state)<<','<<s.lifecycle.submittedFrames<<','<<s.lifecycle.confirmedFrames<<','<<s.lifecycle.uncertainThrough<<','<<s.firstSilentCallbackNs<<','<<s.callbacks<<','<<s.renderedBlocks<<'\n';
 }
 void finish(bool failed,const char* reason){if(done_)return;done_=true;stopTimer();auto final=output_.shutdown();drain();failed_=failed||captureOverflow||output_.status().cleanupFailed;
    std::ofstream raw(root_+"/native-output-f32.raw",std::ios::binary);raw.write(reinterpret_cast<const char*>(capture.data()),static_cast<std::streamsize>(captured*sizeof(float)));
    std::ofstream result(root_+"/run-result.json");result<<"{\"done\":true,\"failed\":"<<(failed_?"true":"false")<<",\"completed\":"<<completed_<<",\"case\":"<<index_+1<<",\"step\":"<<step_<<",\"capturedFloats\":"<<captured<<",\"overflow\":"<<(captureOverflow?"true":"false")<<",\"cleanupFailed\":"<<(output_.status().cleanupFailed?"true":"false")<<",\"finalState\":"<<int(final.state)<<",\"reason\":"<<std::quoted(reason)<<",\"outcomes\":[";
    for(int i=0;i<completed_;++i){if(i)result<<',';snapshotJSON(result,retained_[static_cast<std::size_t>(i)],retainedViews_[static_cast<std::size_t>(i)],silent_[static_cast<std::size_t>(i)]);}result<<"],\"lastSnapshot\":";snapshotJSON(result,final,playback_?playback_->stream().quiescentView():latest_,output_.status().firstSilentCallbackNs);result<<"}\n";
    std::cout<<(failed_?"FAIL ":"PASS ")<<reason<<std::endl;juce::MessageManager::getInstance()->stopDispatchLoop();
 }
 bool send(platform::OutputCommand op){platform::Control c;c.op=op;c.owner=owner_;const auto s=output_.status().lifecycle;c.epoch=s.request.epoch;c.token=s.observationToken;c.requestedNs=platform::monotonicNs();const bool ok=output_.send(c);commands_<<platform::monotonicNs()<<','<<index_+1<<','<<int(op)<<','<<uuid(c.owner)<<','<<c.owner.generation<<','<<c.epoch<<','<<index_+1<<','<<c.token<<','<<c.requestedNs<<','<<ok<<'\n';if(!ok)finish(true,"control queue refusal");return ok;}
 void timerCallback()override {
    output_.service();drain();const auto status=output_.status();const auto s=status.lifecycle;
    if(platform::monotonicNs()-start_>45000000000ULL){finish(true,"45 second watchdog");return;}
    if(s.state==output::State::Fault||captureOverflow){finish(true,"unexpected fault or capture overflow");return;}
    switch(step_){
     case 0:{const auto cap=platform::defaultOutputCapability();if(!cap.valid||cap.uid!="BuiltInSpeakerDevice"||cap.rate!=44100||cap.minFrames>256||cap.maxFrames<256){finish(true,"frozen output capability unavailable");return;}playback_=std::make_unique<platform::ReferencePlayback>();latest_={};if(!output_.connect(cap,{44100,256},nullptr,playback_.get(),platform::ReferencePlayback::observe,platform::ReferencePlayback::render)){finish(true,"connect failed");return;}++step_;break;}
     case 1:if(s.state==output::State::Observed){observed_=platform::monotonicNs();++step_;}break;
     case 2:if(platform::monotonicNs()-observed_>=250000000ULL){if(send(platform::OutputCommand::Acknowledge))++step_;}break;
     case 3:if(s.state==output::State::Ready){owner_=reference_fixtures::owner();owner_.id[1]=static_cast<std::uint8_t>(index_+1);owner_.generation=static_cast<std::uint64_t>(index_+1);owner_.epoch=s.request.epoch;playback_->prepare(program(index_,owner_));if(send(platform::OutputCommand::Start))++step_;}break;
     case 4:if(s.state==output::State::Unresolved){stopped_=platform::monotonicNs();++step_;}break;
     case 5:if(platform::monotonicNs()-stopped_>=200000000ULL){const auto expected=index_?132300ULL:540225ULL;if(!s.pendingOutcome||!s.ownsOutcome||s.submittedFrames!=expected||latest_.cursor.processedThrough!=expected||latest_.cursor.completedCycles!=1||latest_.failed){finish(true,"terminal reference facts incorrect");return;}
       retained_[static_cast<std::size_t>(index_)]=s;retainedViews_[static_cast<std::size_t>(index_)]=latest_;silent_[static_cast<std::size_t>(index_)]=status.firstSilentCallbackNs;
       std::ofstream outcome(root_+"/case-"+std::to_string(index_+1)+"-outcome-before-resolve.json");snapshotJSON(outcome,s,latest_,status.firstSilentCallbackNs);outcome<<'\n';outcome.close();if(send(platform::OutputCommand::ResolveOutcome))++step_;
     }break;
     case 6:if(!s.ownsOutcome&&s.state==output::State::Ready){if(!output_.disconnect()){finish(true,"disconnect failed");return;}drain();const auto final=playback_->stream().quiescentView();if(final.cursor.processedThrough!=retainedViews_[static_cast<std::size_t>(index_)].cursor.processedThrough||final.cursor.binding!=static_cast<std::uint64_t>(index_+1)){finish(true,"final cursor lineage changed");return;}++completed_;playback_.reset();if(completed_==3){finish(false,"three reference cases completed");return;}++index_;owner_={};step_=0;}break;
     default:finish(true,"invalid step");
    }
 }
 std::unique_ptr<platform::ReferencePlayback> playback_;platform::AudioOutputMac output_;scheduler::Owner owner_;scheduler::StreamView latest_;
 std::array<output::Snapshot,3> retained_{};std::array<scheduler::StreamView,3> retainedViews_{};std::array<std::uint64_t,3> silent_{};
 std::string root_;std::ofstream events_,facts_,views_,states_,commands_;std::uint64_t start_{},observed_{},stopped_{};int index_{},step_{},completed_{};bool done_{},failed_{};
};
}
int main(int argc,char**argv){
 if(argc==2&&std::string(argv[1])=="--preflight"){auto c=fathom::platform::defaultOutputCapability();std::cout<<"valid="<<c.valid<<" uid="<<c.uid<<" rate="<<c.rate<<" physicalFrames="<<c.physicalFrames<<" min="<<c.minFrames<<" max="<<c.maxFrames<<" channels="<<c.outputChannels<<'\n';return c.valid?0:1;}
 if(argc==3&&std::string(argv[1])=="--describe"){describe(argv[2]);return 0;}
 if(argc!=3||std::string(argv[1])!="--run")return 2;
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyProhibited];juce::ScopedJuceInitialiser_GUI gui;Run run(argv[2]);juce::MessageManager::getInstance()->runDispatchLoop();return run.result();
}
