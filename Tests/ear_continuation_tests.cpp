#include "tasks/ear234/Ear234.hpp"
#include "tasks/ear234/ClosedKernel.hpp"
#include "content/Canonical.hpp"
#include <iostream>
#include <set>
using namespace fathom;using J=json::Value;namespace E=tasks::ear234;
static int checks=0;void need(bool v,const char* m){if(!v)throw std::runtime_error(m);++checks;}
template<class F>void refuses(F f){bool no=false;try{f();}catch(const std::exception&){no=true;}need(no,"expected refusal");}
J availability(){return J::Object{{"provider_kind","external_human"},{"provider_reference","synthetic fixture, no actual source"},{"material_available",true},{"current_source_ready",true},{"prior_source_exposure",true},{"notes","synthetic declarations only"}};}
std::string envelope(J body){return json::stringify(J::Object{{"body",body},{"sha256",content::sha256(json::stringify(body))}});}
J sample(const J& schema){
 if(auto e=schema.find("enum"))return e->array().front();
 const auto& raw=*schema.find("type");auto type=raw.isArray()?raw.array().front().string():raw.string();
 if(type=="string")return "synthetic fixture, no actual performance";
 if(type=="boolean")return true;if(type=="null")return nullptr;
 if(type=="integer"||type=="number"){if(auto m=schema.find("minimum"))return *m;return J::fromInteger(0);}
 if(type=="object"){J::Object result;for(const auto& p:schema.find("properties")->object())result[p.first]=sample(p.second);return result;}
 if(type=="array"){std::int64_t n=0;if(auto m=schema.find("minItems"))m->integer(n);J::Array result;for(int i=0;i<n;++i)result.push_back(sample(*schema.find("items")));return result;}
 throw std::runtime_error("fixture unsupported schema");
}
int main(){try{
 std::set<std::string> families;std::string first;
 for(const auto& key:E::keys()){
  const auto& d=E::definition(key);if(!families.insert(d.family()).second)continue;if(first.empty())first=key;
  E::Owner original(d);auto old=original.capture("availability");auto bytes=original.continuation();auto restored=E::Owner::restoreContinuation(d,bytes);
  need(restored->learnerView()==original.learnerView(),"initial view differs");need(!restored->current(old),"old token survived");refuses([&]{restored->apply(old,availability());});
  original.apply(old,availability());auto active=original.continuation();restored=E::Owner::restoreContinuation(d,active);
  need(restored->learnerView()==original.learnerView(),"available view differs");need(restored->sourcePlayerView()==original.sourcePlayerView(),"private source choices differ");
  need(restored->history()==original.history(),"history differs");
  auto sourceView=original.sourcePlayerView();const auto& forms=sourceView.find("source_choice_forms")->object();
  if(!forms.empty()){const auto& choice=*forms.begin();original.apply(original.captureSourceChoices(choice.first),sample(choice.second));restored=E::Owner::restoreContinuation(d,original.continuation());need(restored->sourcePlayerView()==original.sourcePlayerView(),"private actual source choice lost");need(restored->history()==original.history(),"private source role history changed");need(restored->history().back().find("input")->null(),"private input leaked into learner history");}

  original.apply(original.capture("stop"),J::Object{{"reason","synthetic stop, no actual source"}});
  auto stopped=original.continuation();restored=E::Owner::restoreContinuation(d,stopped);need(restored->learnerView()==original.learnerView(),"stop state differs");
  need(original.fenceInactiveForNavigation(),"inactive fence refused");bytes=original.continuation();restored=E::Owner::restoreContinuation(d,bytes);need(restored->history()==original.history(),"fence missing");
  auto parsed=json::parse(bytes);J body=*parsed.find("body");body.object()["format"]="future";refuses([&]{E::Owner::restoreContinuation(d,envelope(body));});
  body=*json::parse(bytes).find("body");body.object()["catalogue_sha256"]="foreign";refuses([&]{E::Owner::restoreContinuation(d,envelope(body));});
  body=*json::parse(bytes).find("body");body.object()["state_sha256"]="wrong";refuses([&]{E::Owner::restoreContinuation(d,envelope(body));});
  std::cout<<"family "<<d.family()<<" passed\n"<<std::flush;
 }
 need(families.size()>10,"insufficient family breadth");
 // Every closed source binding must restore its own constructor data.
 std::size_t bindings=0;
 for(const auto& key:E::keys()){const auto& def=E::definition(key);E::Owner x(def);auto restored=E::Owner::restoreContinuation(def,x.continuation());need(restored->learnerView()==x.learnerView(),"source-specific initial state differs");++bindings;}
 std::cout<<"source bindings "<<bindings<<" passed\n";
 const auto& d=E::definition(first);E::Owner owner(d);auto bytes=owner.continuation();bytes.back()='x';refuses([&]{E::Owner::restoreContinuation(d,bytes);});
 // Active source/physical duties and explicit exit release must survive replay.
 for(const auto& key:E::keys())if(E::definition(key).family()=="tonic_card"){
  E::Owner active(E::definition(key));active.apply(active.capture("availability"),availability());
  active.apply(active.capture("report_source_performed"),J::Object{{"declaration","synthetic source declaration only"}});
  auto debt=E::Owner::restoreContinuation(active.retainedDefinition(),active.continuation());need(debt->learnerView()==active.learnerView(),"active debts changed");need(!debt->fenceInactiveForNavigation(),"debt bypassed by fence");
  active.apply(active.capture("stop"),J::Object{{"reason","synthetic exit while release owed"}});
  debt=E::Owner::restoreContinuation(active.retainedDefinition(),active.continuation());need(debt->learnerView()==active.learnerView(),"pending exit lost");
  auto unknown=J::Object{{"learner_released",false},{"source_stopped",false},{"notes","synthetic unknown release"}};refuses([&]{debt->apply(debt->capture("release"),unknown);});
  auto release=J::Object{{"learner_released",true},{"source_stopped",true},{"notes","synthetic released declaration"}};active.apply(active.capture("release"),release);debt->apply(debt->capture("release"),release);need(debt->continuation()==active.continuation(),"release continuation diverged");break;
 }
 // A clue records the peer's actual historical method, not its later edits.
 std::vector<std::unique_ptr<E::Owner>> methods;
 for(const auto& key:E::keys())if(E::definition(key).family()=="verification_method"){
  auto method=std::make_unique<E::Owner>(E::definition(key));method->apply(method->capture("availability"),availability());
  method->apply(method->capture("bind_candidate"),J::Object{{"candidate_reference","same synthetic candidate"},{"external_source_description","synthetic only"}});
  auto actions=method->learnerActions();method->apply(method->capture("submit_observations"),sample(*actions.find("submit_observations")));
  method->apply(method->capture("conclude"),J::Object{{"answer","uncertain"},{"explanation","synthetic uncertain conclusion; not app verified"}});
  methods.push_back(std::move(method));if(methods.size()==2)break;
 }
 need(methods.size()==2,"missing distinct method fixtures");methods[0]->addVerificationClue(methods[0]->capture("add_verification_clue"),*methods[1]);
 auto clues=methods[0]->continuation();std::set<std::string> resolved;
 auto joined=E::Owner::restoreContinuation(methods[0]->retainedDefinition(),clues,[&](const std::string& key)->const E::Definition&{resolved.insert(key);return E::definition(key);});
 need(resolved.count(methods[1]->retainedDefinition().sourceKey()),"nested dependency resolver skipped");need(joined->learnerView()==methods[0]->learnerView(),"owned clue lost");
 methods[1]->apply(methods[1]->capture("revise_observations"),J::Object{});need(joined->continuation()==clues,"historical clue followed later mutable peer");
 refuses([&]{E::Owner::restoreContinuation(methods[0]->retainedDefinition(),clues,[](const std::string&)->const E::Definition&{throw std::runtime_error("host source not admitted");});});
 auto convergence=J::Object{{"independent_clues",false},{"agreement",false},{"explanation","synthetic negative/uncertain methods remain unresolved"}};
 joined->apply(joined->capture("record_convergence"),convergence);auto uncertain=E::Owner::restoreContinuation(joined->retainedDefinition(),joined->continuation());need(uncertain->learnerView()==joined->learnerView(),"uncertain convergence debt lost");
 // Kernel comparison must distinguish typed keys, aliasing and callable data.
 auto binding=d.binding();auto kernel=E::closed::Kernel::fromPinnedSha(binding.find("kernel_sha256")->string());
 auto shared=E::closed::Value::sequence("list");auto a=E::closed::Value::sequence("list",{shared,shared});auto b=E::closed::Value::sequence("list",{E::closed::Value::sequence("list"),E::closed::Value::sequence("list")});
 need(kernel.continuationState(a)!=kernel.continuationState(b),"mutable aliases lost");need(kernel.continuationState(a)==kernel.continuationState(E::closed::clone(a)),"clone changes graph");
 auto cycle=E::closed::Value::sequence("list");cycle.p->values.push_back(cycle);need(!json::stringify(kernel.continuationState(cycle)).empty(),"cycle unsupported");cycle.p->values.clear();
 auto typed=E::closed::Value::dictionary();typed.put(E::closed::Value::integer(1),E::closed::Value::string("a"));typed.put(E::closed::Value::string("1"),E::closed::Value::string("b"));need(kernel.continuationState(typed).find("entries")->array().size()==2,"typed keys collapsed");
 auto executable=E::closed::Value::object("foreign");executable.p->closure=std::make_shared<E::closed::Environment>();refuses([&]{kernel.continuationState(executable);});
 std::cout<<"PASS "<<checks<<" checks across "<<families.size()<<" Ear families (synthetic only)\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<checks<<": "<<e.what()<<"\n";return 1;}}
