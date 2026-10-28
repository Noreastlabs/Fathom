#include "tasks/OrderedContactTask.hpp"
#include "tasks/OrderedContactTaskFormAdapter.hpp"
#include "content/StrictJson.hpp"
#include <iostream>
#include <map>
#include <set>
#include <memory>
#include <functional>
#include <algorithm>
namespace F=fathom::tasks::ordered_contacts;
namespace P=fathom::tasks::physical_contacts;
namespace S=fathom::tasks::manual_contacts;
namespace M=F::manual;
using J=fathom::json::Value;
namespace {
std::size_t checks=0,refusals=0,reports=0,boundaries=0,flows=0,legacyFlows=0,formChecks=0;
void check(bool c,const char* why){++checks;if(!c)throw std::runtime_error(why);}
template<class Fn>void refuse(M::Task& t,Fn f){const auto v=t.view();const auto n=t.history().size();bool no=false;try{f();}catch(const std::invalid_argument&){no=true;}check(no,"expected refusal");++refusals;const auto w=t.view();check(v.revision==w.revision&&v.state==w.state&&v.nextOrdinal==w.nextOrdinal&&v.tempoReductionDue==w.tempoReductionDue&&v.reportedBpm==w.reportedBpm&&n==t.history().size(),"refusal atomic");}
M::SetupReport setup(const M::Task&t){M::SetupReport r{M::Branch::PrintedPassProgression,t.sourcePolicy().passes.front().rhythms.front(),F::Start::Down};r.sourceSetupRead=r.onePrintedSetChosen=r.printedModeChosen=r.stableLandings=M::Claim::Yes;return r;}
void traversal(M::Task&t,M::Observation observation=M::Observation::Clean,bool geometryNeg=false){
 const auto& src=t.sourceHandle();std::size_t n=0;bool boundaryNegative=false;
 while(t.view().state==M::State::Traversal||t.view().state==M::State::Boundary){
  if(t.view().state==M::State::Boundary){auto tok=t.capture(M::Action::BoundaryReport);if(geometryNeg&&!boundaryNegative){refuse(t,[&]{t.reportBoundary(tok,{});});boundaryNegative=true;}t.reportBoundary(tok,{M::Claim::Yes,M::Claim::Yes,M::Claim::Yes});++boundaries;}
  const auto cue=t.cue();const auto expected=src.contact(cue.ordinal,t.view().start==F::Start::Down?S::Start::Down:S::Start::Up);
  check(cue.ordinal==++n&&cue.stringLowToHigh==expected.stringLowToHigh&&cue.fret==expected.fret&&cue.finger==expected.finger&&cue.pick==expected.pick&&cue.midi==expected.midi&&!cue.acousticSoundingSpan,"exact transport contact and unknown gate");
  if(src.family()==S::Family::PhysicalContact)check(!cue.midi&&!cue.activeSourceMetricSpan&&cue.clockAuthority==M::ClockAuthority::ManualUntimed,"physical never clock/pitch fallback");
  t.confirmContact(t.capture(M::Action::Contact),cue.ordinal,M::Claim::Yes);++reports;
 }
 check(n==src.contactCount()&&t.view().state==M::State::Release,"exact traversal terminal release");
 auto release=t.capture(M::Action::Release);refuse(t,[&]{t.release(release,M::Claim::Unknown);});t.release(release,M::Claim::Yes);
 auto loop=t.capture(M::Action::LoopReport);refuse(t,[&]{t.reportLoop(loop,{});});t.reportLoop(loop,{observation,M::Claim::Yes});
}
void pair(M::Task&t,bool negative=false){traversal(t,M::Observation::Clean,negative);t.oppositeStart(t.capture(M::Action::OppositeStart));traversal(t);}
void full(M::Task&t){t.begin(t.capture(M::Action::Begin),setup(t));for(std::size_t i=0;i<t.sourcePolicy().passes.size();++i){pair(t,i==0);if(i+1<t.sourcePolicy().passes.size()){const auto&p=t.sourcePolicy().passes[i+1];t.advancePass(t.capture(M::Action::AdvancePass),p.pass,p.rhythms.front());}}t.finish(t.capture(M::Action::Finish));check(t.view().coverage.chosenBranchRequiredPassesAndBothStartsReported&&!t.view().coverage.wholeChildAccepted&&!t.view().coverage.runtimeAdmitted,"honest cell closure");++flows;}
void learner(const M::Task&t){for(const auto& d:t.actionDescriptors()){check(!d.label.empty(),"learner label");for(const auto& line:d.instructions)check(line.find(t.sourceHandle().sourceRecordSha256())==std::string::npos&&line.find(t.sourceHandle().packetPath())==std::string::npos&&line.find("TASK_")==std::string::npos,"no custody in learner instructions");for(const auto& f:d.fields)check(!f.label.empty(),"typed learner field");}}
void physicalRows(){std::set<int>levels;std::map<int,std::string>representatives;const auto before=S::legacyProjectionBuildCount();
 for(const auto& key:P::keys()){
  auto caller=P::definition(key);M::Task t(S::SourceHandle::physical(caller));const auto level=caller.level();levels.insert(level);representatives.emplace(level,key);
  caller=P::definition(P::keys().back());check(t.sourceHandle().level()==level&&t.sourcePolicy().level==level&&t.sourcePolicy().family==S::Family::PhysicalContact&&std::string(t.sourceKey())==key,"value-owned physical source policy");
  refuse(t,[&]{(void)t.definition();});learner(t);auto begin=t.capture(M::Action::Begin);auto bad=setup(t);bad.sourceSetupRead=M::Claim::Unknown;refuse(t,[&]{t.begin(begin,bad);});
  refuse(t,[&]{auto r=setup(t);r.rhythm=static_cast<M::Rhythm>(999);t.begin(begin,r);});
  full(t);check(!t.sourceHandle().projection(S::Start::Down)->legacyMusicModelUsed&&!t.sourceHandle().projection(S::Start::Up)->legacyMusicModelUsed,"physical no MusicModel path");
  for(const auto& duty:t.sourcePolicy().sourceDuties){auto token=t.capture(M::Action::SourcePracticeReport);refuse(t,[&]{t.reportSourcePractice(token,duty.duty,M::Claim::Unknown,{});});if(duty.needsRelease)refuse(t,[&]{t.reportSourcePractice(token,duty.duty,M::Claim::Yes,{});});t.reportSourcePractice(token,duty.duty,M::Claim::Yes,{M::Claim::Yes,M::Claim::Yes,M::Claim::Yes});}
  const auto h=t.history().size();const auto tok=t.capture(M::Action::Restart);t.deactivateForNavigation();check(t.history().size()==h,"navigation history retained");refuse(t,[&]{t.restart(tok);});
 }
 check(levels.size()==18&&P::keys().size()==339&&S::legacyProjectionBuildCount()==before,"339/18 physical no legacy construction");
 for(const auto& e:representatives){const auto level=e.first;auto owner=[](const std::string&k){auto d=P::definition(k);return std::make_unique<M::Task>(S::SourceHandle::physical(d));}(e.second);M::Task&t=*owner;auto r=setup(t);
  if(t.sourcePolicy().belowCleanMinimum){r.previousCleanBpm=80;r.chosenBpm=80-t.sourcePolicy().belowCleanMinimum;auto bad=r;bad.chosenBpm=80-t.sourcePolicy().belowCleanMinimum+1;refuse(t,[&]{t.begin(t.capture(M::Action::Begin),bad);});}
  auto foreign=std::make_unique<M::Task>(S::SourceHandle::physicalKey(e.second));const auto badOwner=foreign->capture(M::Action::Begin);refuse(t,[&]{t.begin(badOwner,r);});
  t.begin(t.capture(M::Action::Begin),r);auto stale=t.capture(M::Action::Contact);refuse(t,[&]{t.confirmContact(stale,2,M::Claim::Yes);});refuse(t,[&]{t.confirmContact(stale,1,M::Claim::Unknown);});refuse(t,[&]{t.deactivateForNavigation();});refuse(t,[&]{(void)t.capture(M::Action::Finish);});
  t.cancel(t.capture(M::Action::Cancel));refuse(t,[&]{(void)t.capture(M::Action::Restart);});refuse(t,[&]{t.release(t.capture(M::Action::Release),M::Claim::No);});t.release(t.capture(M::Action::Release),M::Claim::Yes);t.restart(t.capture(M::Action::Restart));t.begin(t.capture(M::Action::Begin),r);refuse(t,[&]{t.confirmContact(stale,1,M::Claim::Yes);});
  traversal(t,M::Observation::RisingTension);check(t.view().tempoReductionDue==t.sourcePolicy().sourceTempoRule,"exact source tempo debt scope");
  if(t.sourcePolicy().sourceTempoRule){refuse(t,[&]{(void)t.capture(M::Action::Retry);});t.cancel(t.capture(M::Action::Cancel));t.release(t.capture(M::Action::Release),M::Claim::Yes);t.restart(t.capture(M::Action::Restart));check(t.view().tempoReductionDue,"debt survives restart");refuse(t,[&]{(void)t.capture(M::Action::Begin);});auto reduce=t.capture(M::Action::ReduceTempo);refuse(t,[&]{t.reduceTempo(reduce,3,M::Claim::Yes);});refuse(t,[&]{t.reduceTempo(reduce,4,M::Claim::Unknown);});t.reduceTempo(reduce,4,M::Claim::Yes);if(r.chosenBpm){refuse(t,[&]{t.begin(t.capture(M::Action::Begin),r);});r.chosenBpm=t.view().reportedBpm;}t.begin(t.capture(M::Action::Begin),r);}else{refuse(t,[&]{(void)t.capture(M::Action::ReduceTempo);});t.retry(t.capture(M::Action::Retry));}
  traversal(t);t.oppositeStart(t.capture(M::Action::OppositeStart));traversal(t);
  while(t.view().passIndex+1<t.sourcePolicy().passes.size()){const auto&p=t.sourcePolicy().passes[t.view().passIndex+1];auto advance=t.capture(M::Action::AdvancePass);refuse(t,[&]{t.advancePass(advance,static_cast<M::Pass>(999),p.rhythms.front());});t.advancePass(advance,p.pass,p.rhythms.front());pair(t);}t.finish(t.capture(M::Action::Finish));
  refuse(t,[&]{t.reportSourcePractice(t.capture(M::Action::SourcePracticeReport),static_cast<M::SourceDuty>(999),M::Claim::Yes,{});});
  if(t.sourcePolicy().groupedBeforeDisplacement){t.restart(t.capture(M::Action::Restart));auto v=setup(t);v.branch=M::Branch::DisplacementVariation;v.rhythm=M::Rhythm::StraightSixteenth;refuse(t,[&]{t.begin(t.capture(M::Action::Begin),v);});t.reportSourcePractice(t.capture(M::Action::SourcePracticeReport),M::SourceDuty::GroupedSecure,M::Claim::Yes,{});t.begin(t.capture(M::Action::Begin),v);pair(t);t.finish(t.capture(M::Action::Finish));}
  if(t.sourcePolicy().sourceTempoRule){refuse(t,[&]{(void)t.capture(M::Action::PlanIncrease);});t.reportSourcePractice(t.capture(M::Action::SourcePracticeReport),M::SourceDuty::ThreeCleanRoundTrips,M::Claim::Yes,{});t.planIncreaseNextSession(t.capture(M::Action::PlanIncrease),M::Claim::Yes);}else refuse(t,[&]{(void)t.capture(M::Action::PlanIncrease);});
  check(!t.history().empty()&&!t.view().coverage.performanceObserved,"reports not performance");learner(t);(void)level;
 }
}
void legacy(){std::map<int,std::string> reps;for(const auto&k:F::keys()){auto d=F::definition(k);M::Task t(d);reps.emplace(d.level(),k);check(std::string(t.sourceKey())==k&&t.definition().level()==d.level()&&t.sourcePolicy().family==S::Family::OrderedContact&&t.sourcePolicy().contextSha256==M::policy(d.level()).contextSha256&&t.sourcePolicy().passes.size()==M::policy(d.level()).passes.size(),"all1401 legacy bindings unchanged");refuse(t,[&]{(void)t.capture(M::Action::SourcePracticeReport);});}
 for(const auto&e:reps){auto d=F::definition(e.second);M::Task t(d);full(t);++legacyFlows;learner(t);}
 check(reps.size()==10,"ten legacy policies");
}
void form(){for(int level=16;level<=33;++level){const auto found=std::find_if(P::keys().begin(),P::keys().end(),[level](const auto&k){return P::definition(k).level()==level;});check(found!=P::keys().end(),"form level");M::Task t(S::SourceHandle::physicalKey(*found));M::OrderedContactTaskFormAdapter adapter(t);auto begin=adapter.open(M::Action::Begin);const auto&props=begin.schema.object().at("properties");check(props.find("rhythm")&&props.find("one_set")&&!props.find("midi")&&!props.find("source_key"),"learner form no pitch or custody");J::Object payload;for(const auto&key:begin.schema.object().at("required").array()){const auto&field=props.object().at(key.string());auto value=field.object().at("enum").array().front();if(key.string()=="setup_read"||key.string()=="one_set")value=J::fromInteger(static_cast<int>(M::Claim::Yes));payload.emplace(key.string(),value);}refuse(t,[&]{adapter.apply(begin.token,J::Object{});});adapter.apply(begin.token,J(payload));refuse(t,[&]{adapter.apply(begin.token,J(payload));});auto contact=adapter.open(M::Action::Contact);adapter.apply(contact.token,J::Object{{"contact_reported",J::fromInteger(static_cast<int>(M::Claim::Yes))}});++formChecks;
 t.cancel(t.capture(M::Action::Cancel));t.release(t.capture(M::Action::Release),M::Claim::Yes);auto external=adapter.open(M::Action::SourcePracticeReport);const auto&d=t.sourcePolicy().sourceDuties.back();J report(J::Object{{"source_duty",J::fromInteger(static_cast<int>(d.duty))},{"source_practice_reported",J::fromInteger(static_cast<int>(M::Claim::Yes))},{"source_release_reported",J::fromInteger(static_cast<int>(M::Claim::Yes))},{"frame_relocated",J::fromInteger(static_cast<int>(M::Claim::Yes))},{"pause_reported",J::fromInteger(static_cast<int>(M::Claim::Yes))}});adapter.apply(external.token,report);++formChecks;}
}
}
int main(){try{physicalRows();legacy();form();std::cout<<"{\"result\":\"PASS\",\"physical_rows\":339,\"physical_policies\":18,\"legacy_rows\":1401,\"legacy_material_flows\":"<<legacyFlows<<",\"cell_flows\":"<<flows<<",\"contact_reports\":"<<reports<<",\"boundary_reports\":"<<boundaries<<",\"form_flows\":"<<formChecks<<",\"assertions\":"<<checks<<",\"refusals\":"<<refusals<<"}\n";return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
