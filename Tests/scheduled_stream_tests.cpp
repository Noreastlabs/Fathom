#include "core/ScheduledStream.hpp"
#include <iostream>
#include <memory>
#include <vector>
using namespace fathom;
using namespace fathom::scheduler;
namespace {
int checks{},failures{};
void check(bool v,const char* name){++checks;if(!v)++failures;std::cout<<(v?"PASS ":"FAIL ")<<name<<'\n';}
Owner owner(){Owner o;o.id={1,2,3,4,5,6,0x47,8,0x89,10,11,12,13,14,15,16};o.epoch=1;o.generation=1;return o;}
std::vector<Plan> plans(int initial=120){PlanSpec s;s.owner=owner();s.binding=1;s.sourceBinding="synthetic:stream-unit-v1";s.bpm=initial;s.events={{Rational{0},1,Role::Reference,Action::Attack},{Rational{1},2,Role::Metronome,Action::Attack},{Rational{4,3},3,Role::LayerA,Action::Attack},{Rational{2},4,Role::LayerB,Action::Attack},{Rational{4},1,Role::Reference,Action::Release}};std::vector<Plan> p;p.push_back(compile(s));s.bpm=126;p.push_back(compile(s));s.bpm=132;p.push_back(compile(s));return p;}
bool consume(void* ptr,std::uint64_t,std::uint32_t,const Fact* f,std::size_t n)noexcept{auto* v=static_cast<std::vector<Fact>*>(ptr);for(std::size_t i=0;i<n;++i)v->push_back(f[i]);return true;}
bool discard(void*,std::uint64_t,std::uint32_t,const Fact*,std::size_t)noexcept{return true;}
void drain(ScheduledStream& s){Fact f;StreamView v;while(s.nextFact(f)){}while(s.nextView(v)){}}
std::vector<Fact> run(std::uint32_t block){auto s=std::make_unique<ScheduledStream>();s->prepare(plans(),2);std::vector<Fact> facts;facts.reserve(100);BlockOutcome r;for(int i=0;i<10000;++i){r=s->process(owner(),44100,block,consume,&facts);drain(*s);if(r.terminal)break;}check(r.valid&&r.terminal,"finite completion valid");check(s->quiescentView().cursor.processedThrough==176400,"two exact cycles");return facts;}
}
int main(){
 auto a=run(256),b=run(137);check(a.size()==b.size(),"partition fact count");bool equal=a.size()==b.size();for(std::size_t i=0;i<a.size()&&i<b.size();++i)equal&=a[i].frame==b[i].frame&&a[i].kind==b[i].kind&&a[i].sourceEvent==b[i].sourceEvent&&a[i].cycle==b[i].cycle;check(equal,"partition exact fact identities");
 {auto s=std::make_unique<ScheduledStream>();s->prepare(plans(),1);BlockOutcome r;for(int i=0;i<345;++i){r=s->process(owner(),44100,256,discard,nullptr);drain(*s);}check(r.valid&&r.terminal&&r.submittedFrames==136,"normal midblock stop preserves136frame prefix");auto v=s->quiescentView();check(v.cursor.completedCycles==1&&v.cursor.processedThrough==88200&&!v.failed,"normal boundary retained without render failure");}
 {auto s=std::make_unique<ScheduledStream>();s->prepare(plans());auto wrong=owner();wrong.epoch=2;check(!s->process(wrong,44100,256,discard,nullptr).valid,"wrong epoch fails");check(!s->process(owner(),44100,256,discard,nullptr).valid&&s->quiescentView().failed,"initial failure latched no implicit restart");}
 {auto s=std::make_unique<ScheduledStream>();s->prepare(plans());s->process(owner(),44100,256,discard,nullptr);output::Snapshot o;o.request.epoch=1;o.state=output::State::Fault;s->observe(o);check(s->quiescentView().cursor.state==State::Terminal&&s->quiescentView().cursor.owner==owner(),"nonrendering lifecycle terminates originalowner");check(s->process(owner(),44100,256,discard,nullptr).submittedFrames==0,"stopped cursor never replays");}
 {auto s=std::make_unique<ScheduledStream>();s->prepare(plans(),2,1,1);s->tempo({owner(),1,1,2});s->tempo({owner(),1,1,1});auto wrong=owner();wrong.generation=2;s->tempo({wrong,1,2,1});for(int i=0;i<1000;++i){auto r=s->process(owner(),44100,256,discard,nullptr);drain(*s);if(r.terminal)break;}auto v=s->quiescentView();check(v.tempoIndex==2&&v.acceptedCommands==1&&v.rejectedCommands==2,"manual wins ramp duplicate stale rejected");check(v.cursor.processedThrough==168382,"absolute rational tempo boundary rounds once");}
 {auto s=std::make_unique<ScheduledStream>();s->prepare(plans());for(int i=1;i<=32;++i)check(s->tempo({owner(),1,static_cast<std::uint64_t>(i),1}),"bounded command admission");check(!s->tempo({owner(),1,33,1}),"full command queue explicit refusal");for(int i=0;i<600;++i)s->process(owner(),44100,256,discard,nullptr);check(s->quiescentView().displayDrops>0&&!s->quiescentView().failed,"full display queue dropscopies nottiming");output::Snapshot o;o.request.epoch=1;o.state=output::State::Unresolved;s->observe(o);check(s->quiescentView().cursor.state==State::Terminal,"terminalretention independent ofdisplayqueue");}
 std::cout<<"checks="<<checks<<" failures="<<failures<<'\n';return failures?1:0;
}
