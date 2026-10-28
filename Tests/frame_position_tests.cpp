// Requirement-derived arithmetic/consumer execution. All controls are synthetic;
// the included existing reference actor supplies unchanged validated specimens.
#define main retained_reference_campaign_main
#include "reference_audio_tests.cpp"
#undef main
#include "core/PracticeTimeline.hpp"
#include "platform/MetronomePlayback.hpp"
#include "content/StrictJson.hpp"
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <new>

namespace {
std::atomic<bool> counting{false};
std::atomic<std::uint64_t> allocations{0};
}
void* operator new(std::size_t n) {if(counting.load(std::memory_order_relaxed))allocations.fetch_add(1,std::memory_order_relaxed);if(auto* p=std::malloc(n?n:1))return p;throw std::bad_alloc();}
void* operator new[](std::size_t n) {return ::operator new(n);}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete[](void* p) noexcept {std::free(p);}
namespace {
using J=json::Value;
const J& field(const J& v,const std::string& key){const auto* p=v.find(key);if(!p)throw std::runtime_error("Missing oracle "+key);return *p;}
std::uint64_t number(const J& v){if(v.isString())return std::stoull(v.string());std::int64_t n{};if(!v.integer(n)||n<0)throw std::runtime_error("Expected unsigned integer");return static_cast<std::uint64_t>(n);}
Rational quantity(const J& v){return Rational{static_cast<std::int64_t>(number(v.array()[0])),static_cast<std::int64_t>(number(v.array()[1]))};}
scheduler::FrameRatio ratio(const J& v){return {number(v.array()[0]),number(v.array()[1])};}
std::array<std::string,2> pair(const J& v){return {v.array()[0].string(),v.array()[1].string()};}
J readJson(const char* p){std::ifstream in(p);if(!in)throw std::runtime_error("Missing oracle file");return json::parse(std::string(std::istreambuf_iterator<char>(in),{}));}
scheduler::BeatUnit unit(const J& v){const auto& s=v.string();if(s=="quarter")return scheduler::BeatUnit::Quarter;if(s=="eighth")return scheduler::BeatUnit::Eighth;if(s=="half")return scheduler::BeatUnit::Half;if(s=="dotted_quarter")return scheduler::BeatUnit::DottedQuarter;throw std::runtime_error("Unknown oracle unit");}
struct DynamicCollector {
    std::array<scheduler::Fact,128> facts{};std::size_t count{};
    const std::vector<reference::Program>* programs{};
    static bool sink(void* p,const scheduler::Fact& f) noexcept {auto& c=*static_cast<DynamicCollector*>(p);if(c.count==c.facts.size())return false;c.facts[c.count++]=f;return true;}
    static scheduler::BoundaryDecision boundary(void* p,const scheduler::Fact& f) noexcept {
        auto& c=*static_cast<DynamicCollector*>(p);if(f.cycle>=c.programs->size())return {scheduler::BoundaryAction::Stop,nullptr};
        return {scheduler::BoundaryAction::Tempo,&(*c.programs)[static_cast<std::size_t>(f.cycle)].schedule()};
    }
};
struct PulseHarness {
    platform::MetronomePlayback player;platform::Buses buses{};output::Snapshot state;platform::MetronomeProgress progress;
    std::vector<scheduler::Fact> facts;std::vector<platform::MetronomeSegment> segments;
    PulseHarness(std::uint32_t rate,bool intro){metronome::Settings settings;settings.tempo=137;settings.numerator=1;settings.styles={metronome::Style::Accent};settings.countIn=intro?metronome::CountIn::ConfiguredBar:metronome::CountIn::Off;settings.ramp=metronome::Ramp{true,2,1,199};state.owner=reference_fixtures::owner();state.request.epoch=1;state.request.format={rate,256};state.state=output::State::Running;
        player.prepare(settings,state.owner,1,"synthetic-wide-anchor",rate);platform::MetronomePlayback::observe(&player,state);drain();facts.reserve(1024);segments.reserve(8192);}
    void drain(){platform::MetronomeProgress p;while(player.nextProgress(p))progress=p;scheduler::Fact f;while(player.nextFact(f))facts.push_back(f);platform::MetronomeSegment s;while(player.nextSegment(s))segments.push_back(s);platform::MetronomeReply r;while(player.nextReply(r)){};}
    bool block(std::uint32_t frames,bool accept=true){platform::MetronomePlayback::observe(&player,state);drain();buses={};const auto b=platform::MetronomePlayback::render(&player,state.owner,state.request.format.rate,frames,buses);if(b.valid&&accept)state.submittedFrames+=b.submittedFrames;if(!b.valid||!accept)state.state=output::State::Fault;platform::MetronomePlayback::observe(&player,state);drain();return b.valid;}
    bool through(std::uint64_t end){while(state.submittedFrames<end)if(!block(static_cast<std::uint32_t>(std::min<std::uint64_t>(256,end-state.submittedFrames))))return false;return true;}
    void stop(){state.state=output::State::Unresolved;state.requestedStopNs=123;platform::MetronomePlayback::observe(&player,state);drain();player.reclaim(progress);}
};
}
int main(int argc,char** argv){try{
    if(argc!=5)throw std::runtime_error("Expected independent arithmetic oracle, independent edge/program oracle, width/cancellation oracle, new absolute output directory");
    const std::filesystem::path out(argv[4]);if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("New absolute output directory required");std::filesystem::create_directories(out);
    const auto oracle=readJson(argv[1]), edges=readJson(argv[2]);std::ofstream trace(out/"positions.tsv");trace<<"case\tcycle\tnumerator\tdenominator\trounded\n";
    for(const auto& c:field(edges,"kernel").array()){
        scheduler::FramePosition a,result;expect(scheduler::position(ratio(field(c,"initial")),a),"edge initial "+field(c,"name").string());const auto before=a;result=a;
        const auto valid=scheduler::addRepeated(a,ratio(field(c,"input")),number(field(c,"count")),result);
        expect(valid==field(c,"representable_whole").boolean(),"edge representability");
        auto alias=a;expect(scheduler::addRepeated(alias,ratio(field(c,"input")),number(field(c,"count")),alias)==valid&&alias==result,"alias output matches atomic operation");
        if(valid){const auto& expected=field(c,"expected");expect(result.exact()==pair(field(expected,"exact")),"edge exact canonical fraction");std::uint64_t rounded=42;const bool ok=scheduler::round(result,rounded);expect(ok!=field(expected,"round_refused").boolean(),"edge rounding refusal");expect(ok?rounded==number(field(expected,"round_half_up")):rounded==42,"rounding output atomic and exact");}
        else expect(result==before,"overflow leaves caller output unchanged");
        expect(!scheduler::addRepeated(a,{1,0},0,result)&&result==(valid?alias:before),"invalid denominator even zero count leaves output unchanged");
    }
    const auto widthOracle=readJson(argv[3]);scheduler::FramePosition widePosition;
    for(const auto& step:field(widthOracle,"accumulate_reciprocals").array()){
        const auto before=widePosition;const bool fit=field(step,"capacity_fits").boolean();
        expect(scheduler::add(widePosition,ratio(field(step,"input")),widePosition)==fit,"fixed-width unrelated prime accumulation explicitly bounded");
        expect(fit?widePosition.exact()==pair(field(field(step,"expected"),"exact")):widePosition==before,"wide success exact or refusal atomic");
    }
    for(const auto& step:field(widthOracle,"cancellations").array()){
        expect(scheduler::add(widePosition,ratio(field(step,"input")),widePosition)&&widePosition.exact()==pair(field(field(step,"expected"),"exact")),"full uint64 divisor/gcd/carry cancels canonical denominator exactly");
    }
    expect(widePosition.exact()==std::array<std::string,2>{"10","1"},"complete fraction cancellation normalizes zero to denominator1");
    for(const auto& c:field(oracle,"cases").array()){
        const auto& tempos=field(c,"bpms").array();const auto span=quantity(field(c,"span")),intro=quantity(field(c,"intro"));const auto rate=static_cast<std::uint32_t>(number(field(c,"rate")));const auto beat=unit(field(c,"unit"));
        scheduler::FrameRatio interval; scheduler::FramePosition position;
        expect(scheduler::samples(intro,rate,static_cast<std::uint16_t>(number(tempos[0])),beat,interval)&&scheduler::position(interval,position),"initial exact position");
        std::optional<practice::Timeline> timeline;
        if(tempos.size()<=32){timeline.emplace(practice::TimelineSpec{reference_fixtures::owner(),span,intro,rate,static_cast<std::uint16_t>(number(tempos[0])),beat,tempos.size()});for(std::size_t i=1;i<tempos.size();++i)if(tempos[i]!=tempos[i-1])*timeline=timeline->changed(i,static_cast<std::uint16_t>(number(tempos[i])));}
        for(std::size_t i=0;i<=tempos.size();++i){std::uint64_t rounded{};expect(position.exact()==pair(field(c,"anchors").array()[i])&&scheduler::round(position,rounded)&&rounded==number(field(c,"rounded").array()[i]),"independent exact anchor and half-up frame");
            if(timeline)expect(timeline->coordinate(i)==position&&timeline->frame(i)==rounded,"actual Timeline shares full exact position");
            const auto exact=position.exact();trace<<field(c,"name").string()<<'\t'<<i<<'\t'<<exact[0]<<'\t'<<exact[1]<<'\t'<<rounded<<'\n';
            if(i<tempos.size())expect(scheduler::samples(span,rate,static_cast<std::uint16_t>(number(tempos[i])),beat,interval)&&scheduler::add(position,interval,position),"accepted interval exact accumulation");
        }
    }
    {practice::Timeline many({reference_fixtures::owner(),Rational{1},Rational{},44100,60,scheduler::BeatUnit::Quarter,1000000});expect(many.frame(1000000)==44100000000ULL,"closed million-cycle interval multiplication");}
    allocations=0;void* (*volatile measuredNew)(std::size_t)=&::operator new;
    counting=true;void* allocationControl=measuredNew(8);counting=false;::operator delete(allocationControl);
    expect(allocations.load()==1,"positive control observes one unaligned operator-new allocation");
    std::ofstream workloads(out/"workloads.tsv");workloads<<"case\tframes\tblocks\tcallback_allocations\telapsed_ns\n";
    for(const auto& profile:field(edges,"programs").array()){
        const auto rate=static_cast<std::uint32_t>(number(field(profile,"rate")));const auto intro=Rational{static_cast<std::int64_t>(number(field(profile,"synthetic_intro_quarters")))};const auto& cycles=field(profile,"cycles").array();
        auto m=synthetic("wide-position-two-notes-rests");m.events={note("first",Rational{},Rational{1,4}),rest("rest1",Rational{1,4},Rational{1,4}),note("second",Rational{1,2},Rational{1,4}),rest("rest2",Rational{3,4},Rational{1,4})};const auto model=checked(m);
        std::vector<reference::Program> programs;programs.reserve(cycles.size());
        for(std::size_t i=0;i<cycles.size();++i){auto c=config(Rational{1},rate,static_cast<std::uint16_t>(number(field(cycles[i],"bpm"))));c.intro=i?Rational{}:intro;programs.push_back(reference::compile(model,c));}
        scheduler::Cursor cursor;reference::Renderer renderer;DynamicCollector collector;collector.programs=&programs;
        expect(cursor.start(programs[0].schedule(),programs[0].schedule().owner(),programs[0].schedule().binding())&&renderer.bind(programs[0]),"dynamic actual scheduler/renderer bind");
        const auto total=number(field(field(profile,"target"),"round_half_up"));std::vector<float> pcm(static_cast<std::size_t>(total));std::vector<scheduler::Fact> all;all.reserve(2048);bool ok=true;std::uint64_t blocks{};allocations=0;const auto beginTime=std::chrono::steady_clock::now();counting=true;
        while(cursor.snapshot().state!=scheduler::State::Terminal&&blocks<10000){++blocks;const auto begin=cursor.snapshot().processedThrough;collector.count=0;cursor.process(256,programs[0].schedule().owner(),DynamicCollector::sink,&collector,DynamicCollector::boundary,&collector);const auto end=cursor.snapshot().processedThrough;std::size_t next{};
            for(auto frame=begin;frame<end&&ok;++frame){while(next<collector.count&&collector.facts[next].frame==frame){const auto& f=collector.facts[next++];ok=renderer.accept(f)&&ok;if(f.kind==scheduler::FactKind::CycleCompleted&&f.cycle<programs.size())ok=renderer.selectTempo(programs[static_cast<std::size_t>(f.cycle)])&&ok;}
                if(frame>=pcm.size()){ok=false;break;}ok=renderer.sampleFrame(frame,pcm[static_cast<std::size_t>(frame)])&&ok;}
            while(next<collector.count){const auto& f=collector.facts[next++];ok=f.frame==end&&renderer.accept(f)&&ok;}
            for(std::size_t i=0;i<collector.count;++i)all.push_back(collector.facts[i]);if(!ok)break;
        }
        counting=false;const auto elapsed=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-beginTime).count();const auto allocationCount=allocations.load();
        expect(ok&&cursor.snapshot().reason==scheduler::StopReason::Requested&&cursor.snapshot().processedThrough==total&&!renderer.failed(),"full32 dynamic scheduler/renderer completes without arithmetic fault");expect(allocationCount==0,"measured callback-shaped region has zero operator-new allocations");
        std::size_t boundaries{};for(const auto& f:all){if(f.kind==scheduler::FactKind::CycleCompleted){++boundaries;const auto& expected=f.cycle==cycles.size()?field(profile,"target"):field(cycles[static_cast<std::size_t>(f.cycle)],"start");expect(f.frame==number(field(expected,"round_half_up")),"dynamic endpoint matches independent Fraction");}
            if(f.kind==scheduler::FactKind::Event){const auto offsetIndex=f.action==scheduler::Action::Silence?(f.sourceEvent==3?1:3):(f.sourceEvent==1?(f.action==scheduler::Action::Attack?0:1):(f.action==scheduler::Action::Attack?2:3));const auto& expected=field(cycles[static_cast<std::size_t>(f.cycle)],"quarter_offsets").array()[static_cast<std::size_t>(offsetIndex)];expect(f.frame==number(field(expected,"round_half_up")),"dynamic note/release/rest matches independent Fraction");}}
        expect(boundaries==32&&renderer.anchor().exact()==pair(field(field(profile,"target"),"exact")),"renderer final exact anchor agrees with32 unique cycles");
        const auto name=std::to_string(rate)+(intro.numerator()?"-intro":"-off");Trace retained;retained.pcm=std::move(pcm);retained.facts=std::move(all);dump(out,name,programs[0],retained);workloads<<name<<'\t'<<total<<'\t'<<blocks<<'\t'<<allocationCount<<'\t'<<elapsed<<'\n';
        PulseHarness pulse(rate,intro.numerator()!=0);
        for(std::size_t i=0;i<cycles.size();++i){const auto endpoint=i+1==cycles.size()?number(field(field(profile,"target"),"round_half_up")):number(field(field(cycles[i+1],"start"),"round_half_up"));expect(pulse.through(endpoint)&&pulse.progress.completedCycles==i+1&&pulse.progress.tempo.tempo==static_cast<int>(number(field(cycles[i],"bpm"))),"actual metronome exact endpoint keeps preceding accepted tempo");if(i+1<cycles.size())expect(pulse.block(1)&&pulse.progress.tempo.tempo==static_cast<int>(number(field(cycles[i+1],"bpm"))),"actual metronome boundary new sample commits next tempo");}
        expect(!pulse.progress.fault&&pulse.progress.activeFrames==total-number(field(field(cycles[0],"start"),"round_half_up")),"metronome excludes intro and retains exact confirmed total");pulse.stop();
        std::ofstream facts(out/(name+"-metronome.csv"));facts<<"kind,frame,cycle\n";for(const auto& f:pulse.facts)facts<<int(f.kind)<<','<<f.frame<<','<<f.cycle<<'\n';
        PulseHarness rejected(rate,intro.numerator()!=0);const auto first=number(field(field(cycles[1],"start"),"round_half_up"));expect(rejected.through(first),"rejection setup at first endpoint");const auto prior=rejected.progress;expect(rejected.block(1,false)&&rejected.progress.fault&&rejected.progress.clientAcceptedThrough==prior.clientAcceptedThrough&&rejected.progress.tempo.tempo==137&&rejected.progress.completedCycles==1,"rejected boundary output never commits draft anchor/tempo/extra cycle");
    }
    std::ofstream summary(out/"summary.json");summary<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"classification\":\"actual software consumers; synthetic input; no native or physical qualification\"}\n";std::cout<<"PASS "<<checks<<" exact position checks\n";return 0;
}catch(const std::exception& e){counting=false;std::cerr<<"FAIL "<<e.what()<<" after "<<checks<<" checks\n";return 1;}}
