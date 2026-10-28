#include "tasks/c43/C43.hpp"
#include "content/Canonical.hpp"
#include <iostream>
#include <fstream>
#include <sstream>
#include <set>
using namespace fathom;using J=json::Value;namespace C=tasks::c43;
static int checks=0;void need(bool v,const char*m){if(!v)throw std::runtime_error(m);++checks;}
template<class F>void refuses(F f){bool no=false;try{f();}catch(const std::exception&){no=true;}need(no,"expected refusal");}
J sample(const J& schema){if(auto e=schema.find("enum"))return e->array().front();const auto&raw=*schema.find("type");const auto type=raw.isArray()?raw.array().front().string():raw.string();if(type=="string")return "synthetic fixture";if(type=="boolean")return true;if(type=="null")return nullptr;if(type=="integer"||type=="number"){if(auto m=schema.find("minimum"))return*m;return J::fromInteger(0);}if(type=="object"){J::Object r;for(auto&p:schema.find("properties")->object())r[p.first]=sample(p.second);return r;}if(type=="array"){std::int64_t n=0;if(auto m=schema.find("minItems"))m->integer(n);J::Array r;for(int i=0;i<n;++i)r.push_back(sample(*schema.find("items")));return r;}throw std::runtime_error("fixture schema");}
std::string envelope(J b){return json::stringify(J::Object{{"body",b},{"sha256",content::sha256(json::stringify(b))}});}
int main(int argc,char**argv){try{std::set<std::string>groups;std::size_t bindings=0;
 for(auto&key:C::keys()){const auto&def=C::definition(key);C::Owner owner(def);auto old=owner.capture("availability");auto bytes=owner.continuation();auto restored=C::Owner::restoreContinuation(def,bytes);need(restored.owner->learnerView()==owner.learnerView(),"initial view differs");need(!restored.owner->current(old),"old token survived");need(!restored.context,"phantom context");++bindings;
 if(!groups.insert(def.group()).second)continue;
 auto actions=owner.learnerActions();auto available=sample(*actions.find("availability"));owner.apply(old,available);restored=C::Owner::restoreContinuation(def,owner.continuation());need(restored.owner->learnerView()==owner.learnerView(),"availability differs");need(restored.owner->history()==owner.history(),"history differs");
 auto source=owner.sourcePlayerView();auto forms=source.find("source_choice_forms");if(auto prepare=forms->find("prepare_source")){auto input=sample(*prepare);input.object()["reference"]="synthetic fixture";auto before=owner.continuation();try{owner.apply(owner.captureSourceChoices("prepare_source"),input);}catch(const std::exception&){need(owner.continuation()==before,"refused source fixture mutated state");}restored=C::Owner::restoreContinuation(def,owner.continuation());need(restored.owner->sourcePlayerView()==owner.sourcePlayerView(),"private source choices differ");need(restored.owner->history()==owner.history(),"private role history differs");}
 owner.apply(owner.capture("stop"),J::Object{{"reason","synthetic stop"}});restored=C::Owner::restoreContinuation(def,owner.continuation());need(restored.owner->learnerView()==owner.learnerView(),"stop differs");need(owner.fenceInactiveForNavigation(),"inactive refused");bytes=owner.continuation();restored=C::Owner::restoreContinuation(def,bytes);need(restored.owner->history()==owner.history(),"fence differs");
 auto parsed=json::parse(bytes);auto body=*parsed.find("body");body.object()["state_sha256"]="wrong";refuses([&]{C::Owner::restoreContinuation(def,envelope(body));});body=*parsed.find("body");body.object()["current_context"]="forged";refuses([&]{C::Owner::restoreContinuation(def,envelope(body));});
 std::cout<<"group "<<def.group()<<" passed\n"<<std::flush;
 }
 // Complete the real guarded 18-subpass Ear protocol using synthetic reports.
 need(argc==2,"exact fixture path required");std::ifstream input(argv[1]);std::stringstream buffer;buffer<<input.rdbuf();auto fixture=json::parse(buffer.str());
 const auto&earDef=tasks::ear234::definition(fixture.find("source_key")->string());auto context=std::make_shared<tasks::ear234::Owner>(earDef);
 for(const auto&c:fixture.find("commands")->array()){try{context->apply(context->capture(c.find("action")->string()),*c.find("input"));}catch(const std::exception&e){throw std::runtime_error("context action "+c.find("action")->string()+": "+e.what());}}
 auto completeActions=context->learnerActions();need(completeActions.find("complete"),"full context not ready for completion");auto review=sample(*completeActions.find("complete"));review.object()["remaining_debt"]="no";context->apply(context->capture("complete"),review);need(context->learnerView().find("state")->string()=="completed","context not completed");
 for(const auto&key:C::keys())if(C::definition(key).group()=="legacy_Am7_guide_row"){
  const auto&def=C::definition(key);C::Owner owner(def);auto actions=owner.learnerActions();owner.apply(owner.capture("availability"),sample(*actions.find("availability")));auto src=owner.sourcePlayerView();auto report=sample(*src.find("source_choice_forms")->find("prepare_source"));report.object()["reference"]="synthetic fixture";owner.apply(owner.captureSourceChoices("prepare_source"),report);
  auto current=owner.learnerActions();auto sung=sample(*current.find("commit_sung_guides"));sung.object()["source_key"]=key;sung.object()["guide_notes"]=J::Array{"C","G"};sung.object()["chosen_sung_registers"]=J::Array{J::fromInteger(60),J::fromInteger(67)};owner.apply(owner.capture("commit_sung_guides"),sung);
  current=owner.learnerActions();auto played=sample(*current.find("play_selected_shell"));played.object()["source_key"]=key;played.object()["selected_contacts"]=J::Array{J::Object{{"string",J::fromInteger(2)},{"fret",J::fromInteger(1)},{"midi",J::fromInteger(60)}},J::Object{{"string",J::fromInteger(1)},{"fret",J::fromInteger(3)},{"midi",J::fromInteger(67)}}};played.object()["actual_attack_count"]=J::fromInteger(2);owner.apply(owner.capture("play_selected_shell"),played);
  auto debt=C::Owner::restoreContinuation(def,owner.continuation());need(debt.owner->learnerView()==owner.learnerView(),"physical release debts lost");need(!debt.owner->fenceInactiveForNavigation(),"physical debt fence bypass");
  current=owner.learnerActions();auto release=sample(*current.find("release"));if(release.find("source_key"))release.object()["source_key"]=key;owner.apply(owner.capture("release"),release);
  auto before=owner.continuation();auto incomplete=std::make_shared<tasks::ear234::Owner>(earDef);refuses([&]{owner.attachContextCompletion(owner.capture("attach_complete_context"),incomplete);});need(owner.continuation()==before,"refused attachment mutated original");
  owner.attachContextCompletion(owner.capture("attach_complete_context"),context);need(owner.learnerView().find("context_complete_and_current")->boolean(),"valid context missing");
  auto joined=C::Owner::restoreContinuation(def,owner.continuation());need(joined.context&&joined.owner->learnerView().find("context_complete_and_current")->boolean(),"restored context missing");
  joined.context->apply(joined.context->capture("stop"),J::Object{{"reason","synthetic later context edit"}});need(!joined.owner->learnerView().find("context_complete_and_current")->boolean(),"C43 detached from actual mutable dependency");
  // Replay must use the dependency at the time of each later C43 action.
  auto advance=[&](C::Owner&target,const std::string&action){auto a=target.learnerActions();auto r=sample(*a.find(action));if(r.find("source_key"))r.object()["source_key"]=key;target.apply(target.capture(action),r);};
  advance(*joined.owner,"explicit_reveal");advance(*joined.owner,"compare_complete_unit");need(joined.owner->learnerView().find("state")->string()=="source_duty_debt","stale dependency did not retain failed comparison");
  advance(owner,"explicit_reveal");advance(owner,"compare_complete_unit");advance(owner,"complete_full_unit");need(owner.learnerView().find("state")->string()=="completed","valid dependent workflow did not complete");auto full=C::Owner::restoreContinuation(def,owner.continuation());need(full.owner->learnerView()==owner.learnerView(),"completed dependent workflow differs");
  auto stale=joined.owner->continuation();auto reopened=C::Owner::restoreContinuation(def,stale);need(!reopened.owner->learnerView().find("context_complete_and_current")->boolean(),"stale context resurrected");need(reopened.context->learnerView()==joined.context->learnerView(),"dependency current state lost");need(reopened.owner->learnerView()==joined.owner->learnerView(),"stale context action outcome changed during replay");
  std::set<std::string>resolved;auto qualified=C::Owner::restoreContinuation(def,stale,[&](const std::string&k)->const tasks::ear234::Definition&{resolved.insert(k);return tasks::ear234::definition(k);});need(resolved.count(earDef.sourceKey()),"host dependency resolver bypassed");
  refuses([&]{C::Owner::restoreContinuation(def,stale,[](const std::string&)->const tasks::ear234::Definition&{throw std::runtime_error("host refuses source");});});
  break;
 }
 std::cout<<"PASS "<<checks<<" checks; "<<bindings<<" C43 bindings / "<<groups.size()<<" groups; synthetic only\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<checks<<": "<<e.what()<<"\n";return 1;}}
