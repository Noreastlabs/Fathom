#include "tasks/RecipeTask.hpp"
#include "content/Canonical.hpp"
#include <iostream>
using namespace fathom;using namespace tasks::recipes;using V=json::Value;using O=V::Object;
int checks=0;void ck(bool b,const char*m){++checks;if(!b)throw std::runtime_error(m);}template<class F>void no(F f){bool refused=false;try{f();}catch(const std::exception&){refused=true;}ck(refused,"expected refusal");}
void act(RecipeTask&t,Intent i,V p=O{}){t.apply(t.capture(i),p);}
std::unique_ptr<RecipeTask> round(RecipeTask&t){const auto bytes=t.continuation();auto r=RecipeTask::restoreContinuation(definition(t.capture(Intent::Choose).sourceKey),bytes);return r;}

int main(){try{for(const auto&key:keys()){
 const auto&d=definition(key);RecipeTask task(d);auto parity=[&]{auto r=round(task);ck(r->continuation()==task.continuation(),"exact private replay");ck(!r->view().observedPerformance&&!r->view().grantsCredit,"no observation/credit");const auto old=task.capture(Intent::Navigate);no([&]{r->apply(old,O{});});return r;};
 parity();ck(task.fenceInactiveForNavigation(),"idle fence");parity();
 V request=O{{"package_key",key},{"contract_sha256",d.contractSha256()},{"start_stroke","D"}};
 if(d.recipe()==Recipe::RecoveryPair){auto choices=allowedChoices(d);const auto origin=choices.object().at("source_contacts").array().front();auto targets=allowedChoices(d,origin);request.object().emplace("source_contact",origin);request.object().emplace("target_contact",targets.object().at("nearest_target_contacts").array().front());request.object().emplace("rest_of_bar_plan","Private test-only manual simplification and complete release.");}
 act(task,Intent::Choose,request);parity();
 while(task.view().phase==Phase::Steps){act(task,Intent::Report,task.expectedReport());parity();}
 auto release=parity();ck(release->view().needsManualRelease,"replay preserves actual release debt");no([&]{act(*release,Intent::Again);});act(task,Intent::Release,O{{"released_completely_reported",true}});parity();ck(task.fenceInactiveForNavigation(),"closed fence");parity();act(task,Intent::Again);parity();act(task,Intent::Choose,request);
 auto report=task.expectedReport();bool changed=false;for(auto&f:report.object())if(f.second.isBool()){f.second=false;changed=true;break;}ck(changed,"negative fixture");act(task,Intent::Report,report);auto negative=parity();ck(negative->diagnosis().has_value()&&negative->view().needsManualRelease,"negative diagnosis/debt retained");
 auto bytes=task.continuation();auto e=json::parse(bytes);e.object().at("body").object().at("revision")=V::fromInteger(999);no([&]{RecipeTask::restoreContinuation(d,json::stringify(e));});e.object().at("sha256")=content::sha256(json::stringify(e.object().at("body")));no([&]{RecipeTask::restoreContinuation(d,json::stringify(e));});
 auto changedSource=json::parse(bytes);changedSource.object().at("body").object().at("context_sha256")="foreign";changedSource.object().at("sha256")=content::sha256(json::stringify(changedSource.object().at("body")));no([&]{RecipeTask::restoreContinuation(d,json::stringify(changedSource));});
 auto extra=json::parse(bytes);extra.object().emplace("future",true);no([&]{RecipeTask::restoreContinuation(d,json::stringify(extra));});
 const auto&other=definition(keys()[key==keys().front()?1:0]);no([&]{RecipeTask::restoreContinuation(other,bytes);});ck(task.continuation()==bytes,"refusals preserve original");
 RecipeTask stopped(d);act(stopped,Intent::Choose,request);act(stopped,Intent::Stop,O{{"step",V::fromInteger(1)},{"response","stopped"}});auto held=round(stopped);ck(held->view().pendingOutcome==Outcome::Cancelled&&held->view().needsManualRelease,"stopped debt preserved");
 }
 std::cout<<"PASS "<<checks<<" private recipe continuation checks across "<<keys().size()<<" source keys; no app/audio/credit\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<" checks="<<checks<<'\n';return 1;}}
