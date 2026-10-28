#include "core/Scheduler.hpp"
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <thread>
#include <vector>
using namespace fathom;
using namespace fathom::scheduler;
namespace {
int checks{};
void check(bool ok, const char* name) { ++checks; if (!ok) { std::cerr << "FAIL " << name << '\n'; std::exit(1); } }
template<class F> void rejects(F f, const char* name) { bool yes{}; try { f(); } catch (const std::exception&) { yes = true; } check(yes, name); }
Owner owner() { Owner o; o.id[6]=0x40; o.id[8]=0x80; o.id[15]=7; o.generation=1; o.epoch=1; return o; }
PlanSpec spec() { PlanSpec s; s.owner=owner(); s.binding=1; s.sourceBinding="synthetic:control1/version1"; s.events={{Rational{0},0,Role::Reference,Action::Attack}}; return s; }
struct Trace { std::array<Fact, 20000> facts{}; std::size_t n{}, capacity{20000}; };
bool sink(void* context, const Fact& f) noexcept { auto& t=*static_cast<Trace*>(context); if (t.n==t.capacity) return false; t.facts[t.n++]=f; return true; }
bool discard(void*, const Fact&) noexcept { return true; }
BoundaryDecision stopBoundary(void*, const Fact&) noexcept { return {BoundaryAction::Stop,nullptr}; }
BoundaryDecision invalidBoundary(void*, const Fact&) noexcept { return {static_cast<BoundaryAction>(99),nullptr}; }
BoundaryDecision tempoBoundary(void* p, const Fact&) noexcept { return {BoundaryAction::Tempo,static_cast<const Plan*>(p)}; }
void advance(Cursor& c, std::uint64_t frames, Trace& t, std::uint32_t block=256, BoundaryReducer r=nullptr, void* ctx=nullptr) {
    while(frames) { auto n=static_cast<std::uint32_t>(std::min<std::uint64_t>(frames,block)); if(!c.process(n,owner(),sink,&t,r,ctx)) break; frames-=n; }
}
std::uint64_t mapped(Rational q, int bpm=60, BeatUnit u=BeatUnit::Quarter, std::uint32_t rate=44100) {
    FrameRatio f; std::uint64_t n{}; check(samples(q,rate,static_cast<std::uint16_t>(bpm),u,f)&&round(f,n),"sample conversion"); return n;
}
void arithmetic() {
    const std::array<std::uint64_t,9> expected{0,19314,38628,57942,77255,96569,115883,135197,154511};
    for(int i=0;i<9;++i) check(mapped(Rational{i},137)==expected[static_cast<std::size_t>(i)],"independent137 oracle");
    check(mapped(Rational{1000},137)==19313869,"no accumulated loop rounding");
    check(mapped(Rational{1,264600},20)==1,"half sample rounds upward");
    check(mapped(Rational{1},60,BeatUnit::Eighth)==88200,"eighth BPM unit");
    check(mapped(Rational{1},60,BeatUnit::DottedQuarter)==29400,"dotted quarter BPM unit");
    check(mapped(Rational{1},60,BeatUnit::Half)==22050,"half BPM unit");
    FrameRatio out; std::uint64_t n{}; const auto m=std::numeric_limits<std::uint64_t>::max();
    check(!add({m,1},{1,1},out),"addition overflow refusal");
    check(!multiply({m,1},2,out),"multiplication overflow refusal");
    check(multiply({1,2},2,out)&&out.n==1&&out.d==1,"multiply cancellation");
    check(!round({1,0},n)&&!add({1,0},{0,1},out),"zero denominator refusal");
    check(round({m,m},n)&&n==1,"round avoids doubling overflow");
    check(!samples(Rational{1},7999,60,BeatUnit::Quarter,out),"rate lower bound");
    check(!samples(Rational{1},192001,60,BeatUnit::Quarter,out),"rate upper bound");
    check(!samples(Rational{1},44100,19,BeatUnit::Quarter,out),"BPM lower bound");
    check(!samples(Rational{1},44100,301,BeatUnit::Quarter,out),"BPM upper bound");
    check(!samples(Rational{1},44100,60,static_cast<BeatUnit>(99),out),"unknown BPM unit");
}
void validation() {
    auto s=spec(); check(compile(s).valid(),"valid plan");
    s.owner.epoch=0; rejects([&]{compile(s);},"missing epoch"); s=spec(); s.owner.id[6]=0x20; rejects([&]{compile(s);},"UUID version");
    s=spec(); s.binding=0; rejects([&]{compile(s);},"zero binding");
    s=spec(); s.sourceBinding.clear(); rejects([&]{compile(s);},"missing source binding");
    s=spec(); s.cycle=Rational{0}; rejects([&]{compile(s);},"zero loop");
    s=spec(); s.cycle=Rational{4097}; rejects([&]{compile(s);},"loop bound");
    s=spec(); s.cycle=Rational{1,10000000}; rejects([&]{compile(s);},"zero-sample loop");
    s=spec(); s.events[0].at=Rational{4}; rejects([&]{compile(s);},"half-open attack");
    s.events[0].action=Action::Release; check(compile(s).valid(),"end release before boundary");
    s.events[0].at=Rational{5}; rejects([&]{compile(s);},"beyond loop");
    s=spec(); s.events[0].role=Role::CountIn; rejects([&]{compile(s);},"phase mismatch");
    s=spec(); s.events[0].action=static_cast<Action>(99); rejects([&]{compile(s);},"unknown event action");
    s=spec(); s.events.push_back(s.events[0]); rejects([&]{compile(s);},"duplicate event identity");
    s=spec(); s.events.resize(maxPlanEvents+1); rejects([&]{compile(s);},"event capacity");
    s=spec(); s.intro=Rational{1}; s.countIn={{Rational{1},1,Role::CountIn,Action::Attack}}; rejects([&]{compile(s);},"count-in half-open");
}
void partitions() {
    auto s=spec(); s.bpm=137; s.cycle=Rational{1}; s.events.push_back({Rational{1,3},1,Role::LayerA,Action::Attack}); s.events.push_back({Rational{0},2,Role::LayerB,Action::Attack});
    auto p=compile(s); Cursor a,b; Trace ta,tb;
    check(a.start(p,owner(),1)&&b.start(p,owner(),1),"partition start");
    advance(a,19313870,ta,256); advance(b,19313870,tb,65536);
    check(ta.n==tb.n,"partition trace count");
    bool same=true; for(std::size_t i=0;i<ta.n;++i) { const auto& x=ta.facts[i]; const auto& y=tb.facts[i]; same &= x.frame==y.frame&&x.kind==y.kind&&x.sourceEvent==y.sourceEvent&&x.role==y.role&&x.cycle==y.cycle&&x.owner==y.owner; }
    check(same,"partition-independent exact trace");
    check(a.snapshot().completedCycles==1000&&b.snapshot().completedCycles==1000,"1000 exact loop completions");
    check(ta.facts[0].frame==ta.facts[1].frame&&ta.facts[0].role!=ta.facts[1].role,"simultaneous voices distinct");
    check(a.snapshot().processedThrough==19313870&&!a.snapshot().hasConfirmation,"callback cursor is not output confirmation");
    check(a.confirm(owner(),19313870),"explicit progress confirmation");
    check(!a.confirm(owner(),19313871)&&!a.confirm(owner(),1),"confirmation no future/regression");
    auto wrong=owner(); wrong.epoch++; check(!a.confirm(wrong,19313870),"stale confirmation");
}
void phasesAndStops() {
    auto s=spec(); s.intro=Rational{7,2}; s.countIn={{Rational{0},90,Role::CountIn,Action::Attack}};
    auto p=compile(s); Cursor c; Trace t; check(c.start(p,owner(),1),"count-in start"); advance(c,154350,t);
    check(c.snapshot().state==State::CountIn&&c.snapshot().completedCycles==0&&t.n==1,"count-in excluded endpoint/no cycle credit");
    check(c.process(1,owner(),sink,&t),"count-in endpoint callback");
    check(t.n==3&&t.facts[1].kind==FactKind::CountInEnded&&t.facts[2].frame==154350,"first practice event at count-in end");
    s=spec(); s.events.push_back({Rational{3},1,Role::Reference,Action::Silence}); s.events.push_back({Rational{4},2,Role::Reference,Action::Release});
    p=compile(s); Cursor d; Trace u; d.start(p,owner(),1); advance(d,176400,u);
    check(d.snapshot().completedCycles==0,"half-open cycle end pending");
    check(!d.process(1,owner(),sink,&u,stopBoundary),"boundary reducer stop");
    check(d.snapshot().completedCycles==1&&d.snapshot().state==State::Terminal,"last rest counts before Stop");
    check(u.n==4&&u.facts[2].action==Action::Release&&u.facts[3].kind==FactKind::CycleCompleted,"end release/boundary suppress next attack");
    check(!d.process(1,owner(),sink,&u)&&u.n==4,"no repeated terminal boundary");
    check(!d.start(p,owner(),1),"unresolved terminal cannot restart");
    auto wrong=owner();wrong.id[15]++;check(!d.acknowledge(wrong,1),"wrong outcome acknowledgement");
    check(d.acknowledge(owner(),1)&&d.start(p,owner(),1),"explicit matching acknowledgement before restart");
    Cursor partial;Trace v;partial.start(p,owner(),1);advance(partial,176399,v);check(partial.stop(owner(),1)&&partial.snapshot().completedCycles==0,"one sample before boundary partial");
    Cursor immediate;Trace w;immediate.start(p,owner(),1);advance(immediate,176400,w);
    check(immediate.stop(owner(),1)&&immediate.snapshot().completedCycles==1&&immediate.snapshot().boundaryFactPending,"immediate Stop exact boundary retains completion");
}
void tempo() {
    auto s=spec();s.cycle=Rational{1};s.bpm=137;auto p=compile(s);s.bpm=151;auto next=compile(s);
    check(p.compatibleTempo(next),"same structural cycle accepts a new precompiled tempo");
    Cursor c;Trace t;c.start(p,owner(),1);advance(c,71884,t,256,tempoBoundary,&next);
    const std::array<std::uint64_t,5> expected{0,19314,36837,54360,71883};
    std::size_t i{};for(std::size_t j=0;j<t.n;++j)if(t.facts[j].kind==FactKind::Event){check(i<expected.size()&&t.facts[j].frame==expected[i],"piecewise exact137/151 anchor");++i;}
    check(i==5,"tempo oracle coverage");
    s.bpm=22;auto slow=compile(s);Cursor d;Trace u;d.start(slow,owner(),1);advance(d,240546,u,1024,tempoBoundary,&slow);
    check(d.snapshot().completedCycles==2,"fractional22BPM anchor not rounded segments");
    auto units=spec();units.cycle=Rational{1};units.unit=BeatUnit::Half;check(!p.compatibleTempo(compile(units)),"live beat unit change refused");
    Cursor unknown;Trace ut;unknown.start(p,owner(),1);advance(unknown,19315,ut,256,invalidBoundary);check(unknown.snapshot().reason==StopReason::InvalidDecision&&ut.n==2,"unknown reducer action suppresses next attack");
    auto halfSpec=spec();halfSpec.bpm=20;halfSpec.cycle=Rational{1,264600};auto halfPlan=compile(halfSpec);Cursor hc;Trace ht;hc.start(halfPlan,owner(),1);advance(hc,2,ht,256,stopBoundary);check(hc.snapshot().completedCycles==1&&!hc.snapshot().boundaryFactPending,"same rounded endpoint cannot invent next cycle on Stop");
    s.sourceBinding="changed";auto bad=compile(s);Cursor e;Trace v;e.start(p,owner(),1);advance(e,19315,v,256,tempoBoundary,&bad);
    check(e.snapshot().reason==StopReason::InvalidTempo&&e.snapshot().completedCycles==1,"changed source cannot tempo swap");
    s=spec();s.cycle=Rational{1};s.owner.epoch++;auto stale=compile(s);check(!p.compatibleTempo(stale),"tempo epoch refusal");
    s=spec();s.cycle=Rational{1};s.events[0].sourceEvent++;auto changed=compile(s);check(!p.compatibleTempo(changed),"tempo source topology refusal");
    s=spec();s.cycle=Rational{1};s.binding=2;check(!p.compatibleTempo(compile(s)),"tempo binding change refused");
    s=spec();s.cycle=Rational{1};s.sampleRate=48000;check(!p.compatibleTempo(compile(s)),"tempo sample-rate change refused");
    s=spec();s.cycle=Rational{1};s.events.push_back({Rational{1,2},1,Role::LayerB,Action::Attack});check(!p.compatibleTempo(compile(s)),"tempo event-count change refused");
    s=spec();s.cycle=Rational{1};s.events[0].role=Role::LayerA;check(!p.compatibleTempo(compile(s)),"tempo event-role change refused");
    s=spec();s.cycle=Rational{1};s.events[0].action=Action::Release;check(!p.compatibleTempo(compile(s)),"tempo event-action change refused");
    s=spec();s.cycle=Rational{1};s.events[0].at=Rational{2,4};check(!p.compatibleTempo(compile(s)),"tempo normalized event-position change refused");
}
void failures() {
    const auto p=compile(spec());
    for(int i=0;i<3;++i) {Cursor c;Trace t;c.start(p,owner(),1);auto bad=owner();if(i==0)bad.id[15]++;if(i==1)bad.generation++;if(i==2)bad.epoch++;
        check(!c.stop(bad,1)&&c.snapshot().state==State::Running,"stale stop refuses");
        check(!c.process(256,bad,sink,&t)&&t.n==0&&c.snapshot().reason==StopReason::InvalidFormat,"format observation mismatch stops before render");}
    Cursor c;Trace t;t.capacity=0;c.start(p,owner(),1);check(!c.process(256,owner(),sink,&t),"fact overflow stops");
    const auto snap=c.snapshot();check(snap.owner==owner()&&snap.binding==1&&snap.uncertainThrough==256&&snap.reason==StopReason::FactOverflow,"overflow original owner and uncertain extent");
    check(!c.process(512,owner(),sink,&t)&&c.snapshot().uncertainThrough==256,"terminal cannot be overwritten");
    Cursor q;Trace u;q.start(p,owner(),1);advance(q,176400,u);u.capacity=u.n;
    check(!q.process(1,owner(),sink,&u)&&q.snapshot().completedCycles==1&&q.snapshot().boundaryFactPending&&q.snapshot().reason==StopReason::FactOverflow,"full fact queue retains prior completion independently");
    Cursor invalid;invalid.start(p,owner(),1);check(!invalid.process(0,owner(),discard,nullptr)&&invalid.snapshot().reason==StopReason::InvalidBlock,"zero block refused");
    Cursor oversized;oversized.start(p,owner(),1);check(!oversized.process(maxCallbackFrames+1,owner(),discard,nullptr),"block capacity refused");
    auto s=spec();s.cycle=Rational{1,44100};auto dense=compile(s);Cursor work;work.start(dense,owner(),1);
    check(!work.process(65536,owner(),discard,nullptr)&&work.snapshot().reason==StopReason::WorkLimit,"finite callback work budget");
}
void queuesAndPool() {
    CommandQueue q;Command cmd;cmd.owner=owner();for(std::uint64_t i=0;i<64;++i){cmd.sequence=i;check(q.push(cmd),"command capacity accepts");} check(!q.push(cmd),"command full refuses");
    UrgentStop urgent(owner(),1);urgent.request(owner(),1);auto p=compile(spec());Cursor c;c.start(p,owner(),1);check(!c.process(256,owner(),discard,nullptr,nullptr,nullptr,&urgent)&&c.snapshot().reason==StopReason::Requested,"urgent stop independent full queue");
    for(std::uint64_t i=0;i<64;++i){Command out;check(q.pop(out)&&out.sequence==i,"queue preserves original order on overflow");}check(!q.pop(cmd),"empty queue");
    auto changed=owner();changed.id[15]++;check(!urgent.request(changed,1),"stale owner urgent request refuses");
    changed=owner();changed.generation++;check(!urgent.request(changed,1),"stale generation urgent request refuses");
    changed=owner();changed.epoch++;check(!urgent.request(changed,1),"stale epoch urgent request refuses");
    urgent.request(owner(),1);check(!urgent.consume(changed,1)&&!urgent.consume(owner(),2)&&urgent.consume(owner(),1),"urgent exact identity consume");
    auto newSpec=spec();newSpec.owner=changed;auto newPlan=compile(newSpec);Cursor newOwner;newOwner.start(newPlan,changed,1);urgent.request(owner(),1);
    check(newOwner.process(1,changed,discard,nullptr,nullptr,nullptr,&urgent),"same key old owner channel cannot silence new owner");
    Cursor endpoint;Trace et;endpoint.start(p,owner(),1);advance(endpoint,176400,et);urgent.request(owner(),1);
    check(!endpoint.process(1,owner(),sink,&et,nullptr,nullptr,&urgent)&&endpoint.snapshot().completedCycles==1&&endpoint.snapshot().boundaryFactPending,"urgent endpoint retains preceding completion");
    Plan moved=compile(spec());Plan destination=std::move(moved);check(destination.valid()&&!moved.valid(),"move invalidates donor");PlanPool movePool;PlanToken mt;check(!movePool.prepare(std::move(moved),mt),"moved-from publication refuses");
    PlanPool pool;std::array<PlanToken,3> tokens;for(auto& token:tokens)check(pool.prepare(compile(spec()),token),"three pool publications");PlanToken spare;auto waiting=compile(spec());check(!pool.prepare(std::move(waiting),spare)&&waiting.valid(),"full pool preserves caller plan");
    const auto* active=pool.acquire(tokens[0]);check(active&&active->sourceBinding()=="synthetic:control1/version1","immutable published plan");
    check(!pool.acquire(tokens[0])&&!pool.reclaim(tokens[0]),"duplicate acquire/early reclaim refuses");
    check(pool.retire(tokens[0])&&!pool.retire(tokens[0]),"single callback retirement acknowledgement");
    check(!pool.prepare(std::move(waiting),spare),"retirement not automatic reclamation");
    check(pool.reclaim(tokens[0])&&pool.prepare(std::move(waiting),spare),"producer reclaim then republish");
    check(!pool.acquire(tokens[0])&&!pool.retire(tokens[0])&&!pool.reclaim(tokens[0]),"incarnation prevents ABA");check(pool.acquire(spare)!=nullptr,"new incarnation borrows");
}
void threaded() {
    constexpr std::uint64_t total=4000;PlanPool pool;FixedQueue<PlanToken,3> ready,retired;std::atomic<bool> okay{true};
    std::thread producer([&]{
        for(std::uint64_t i=1;i<=total;++i){auto s=spec();s.binding=i;s.sourceBinding="synthetic-thread-"+std::to_string(i);auto p=compile(s);PlanToken t;
            while(!pool.prepare(std::move(p),t)){PlanToken r;if(retired.pop(r)){if(!pool.reclaim(r))okay=false;}else std::this_thread::yield();}
            while(!ready.push(t))std::this_thread::yield();
            PlanToken r;while(retired.pop(r))if(!pool.reclaim(r))okay=false;
        }
    });
    std::thread consumer([&]{for(std::uint64_t i=1;i<=total;++i){PlanToken t;while(!ready.pop(t))std::this_thread::yield();const auto* p=pool.acquire(t);
        if(!p||p->binding()!=i||p->sourceBinding()!="synthetic-thread-"+std::to_string(i)||p->events().size()!=1)okay=false;
        if(!pool.retire(t))okay=false;while(!retired.push(t))std::this_thread::yield();}});
    producer.join();consumer.join();PlanToken r;while(retired.pop(r))if(!pool.reclaim(r))okay=false;
    check(okay.load(),"4000 synthetic publication/retirement interleavings");
    std::cout<<"SIZES Plan="<<sizeof(Plan)<<" TimedEvent="<<sizeof(TimedEvent)<<" Fact="<<sizeof(Fact)<<" Cursor="<<sizeof(Cursor)<<" PlanPool="<<sizeof(PlanPool)<<" CommandQueue="<<sizeof(CommandQueue)<<" FactQueue="<<sizeof(FactQueue)<<'\n';
}
}
int main(){arithmetic();validation();partitions();phasesAndStops();tempo();failures();queuesAndPool();threaded();std::cout<<"PASS "<<checks<<" scheduler checks; synthetic core only\n";}
