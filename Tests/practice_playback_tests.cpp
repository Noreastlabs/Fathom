#include "practice_fixtures.hpp"
#include "platform/PracticePlayback.hpp"
#include <cmath>
#include <iostream>
using namespace fathom;using namespace practice_fixtures;
namespace {int n=0;void check(bool b,const char* s){++n;if(!b)throw std::runtime_error(s);std::cout<<"PASS "<<s<<'\n';}}
int main(){try{
 auto buses=std::make_unique<platform::Buses>();auto c=config();auto o=owner();
 for(auto cut: {1000U,18000U,24000U,28000U,32000U}) {
  platform::PracticePlayback p;check(p.prepare(model(),referenceConfig(c,o),c,2),"prepare fresh generation");
  output::Snapshot s;s.state=output::State::Running;s.owner=o;s.request.epoch=o.epoch;std::uint64_t through=0;double click=0,reference=0;practice::Progress last;
  while(through<cut){platform::PracticePlayback::observe(&p,s);*buses={};auto frames=std::min(256U,cut-static_cast<unsigned>(through));auto r=platform::PracticePlayback::render(&p,o,c.rate,frames,*buses);check(r.valid&&r.submittedFrames==frames,"native provider block exact prefix");
   for(unsigned i=0;i<frames;++i){if(through+i<16000){check((*buses)[0][0][i]==0,"count-in reference silent");click+=std::abs((*buses)[1][0][i]);}else reference+=std::abs((*buses)[0][0][i]);}
   through+=r.submittedFrames;s.submittedFrames=through;platform::PracticePlayback::observe(&p,s);while(p.nextProgress(last)){}scheduler::Fact f;while(p.nextFact(f)){}
  }
  s.state=output::State::Paused;s.requestedStopNs=123;s.uncertainThrough=through;platform::PracticePlayback::observe(&p,s);while(p.nextProgress(last)){}
  check(last.state==practice::State::Paused&&last.clientAcceptedThrough==cut&&last.activeFrames==(cut>16000?cut-16000:0),"paused accounting excludes count-in");check(!last.hasPhysicalConfirmation&&last.requestedStopNs==123,"request distinct from unavailable physical confirmation");check(last.completedCycles==(cut==32000?1:0),"exact final-rest boundary counts once");check(click>0,"audible count-in generated");if(cut>18000)check(reference>0,"reference frames generated after count-in");
  practice::Progress retired;check(p.reclaim(retired)&&retired.sequence==last.sequence,"callback retirement preserves terminal facts");auto next=o;++next.generation;check(p.prepare(model(),referenceConfig(c,next),c,2-last.completedCycles),"fresh renderer and program after pause");s={};s.state=output::State::Running;s.owner=next;s.request.epoch=next.epoch;through=0;bool done=false;
  while(!done){platform::PracticePlayback::observe(&p,s);*buses={};auto r=platform::PracticePlayback::render(&p,next,c.rate,256,*buses);check(r.valid,"resumed prefix valid");through+=r.submittedFrames;s.submittedFrames=through;if(r.terminal){s.state=output::State::Unresolved;done=true;}platform::PracticePlayback::observe(&p,s);while(p.nextProgress(last)){}scheduler::Fact f;while(p.nextFact(f)){}if(through>60000)throw std::runtime_error("target failed to stop");}
  check(last.state==practice::State::Ended&&last.completedCycles==(cut==32000?1:2),"resume full loop target no duplicate prior cycle");check(through==16000+(cut==32000?16000:32000),"fresh full count-in and exact target tail");check(p.reclaim(retired),"final coupled objects reclaimed off callback");
 }
 {platform::PracticePlayback p;p.prepare(model(),referenceConfig(c,o),c,2);output::Snapshot s;s.owner=o;s.request.epoch=o.epoch;s.state=output::State::Running;platform::PracticePlayback::observe(&p,s);auto r=platform::PracticePlayback::render(&p,o,c.rate,256,*buses);check(r.valid,"generated prefix before rejected output");s.state=output::State::Fault;s.uncertainThrough=256;platform::PracticePlayback::observe(&p,s);practice::Progress last;while(p.nextProgress(last)){}check(last.clientAcceptedThrough==0&&last.scheduledThrough==256&&last.activeFrames==0&&last.state==practice::State::Error,"rejected mixer/fault prefix gives zero credit");}
 std::cout<<"CHECKS "<<n<<" PASS\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<" checks "<<n<<'\n';return 1;}}
