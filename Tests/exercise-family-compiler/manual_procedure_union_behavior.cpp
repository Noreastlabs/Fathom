#include "ManualProcedureGraphFixture.hpp"
#include <GeneratedManualProcedureGraph.hpp>
#include <iostream>
#include <set>
#include <functional>
using namespace fathom;using namespace tasks::manual_procedure_graph;
namespace X=tests::manual_procedure_fixture;using V=json::Value;using O=V::Object;using A=V::Array;
namespace {
std::size_t assertions{},refusals{},gestures{},paths{},stages{};std::string checkpoint;
void check(bool ok,const char* reason="CHECK"){++assertions;if(!ok)throw std::runtime_error(reason);}
const V& f(const V& v,const char* n){const auto* p=v.find(n);check(p!=nullptr,"FIELD");return *p;}
std::string state(const ManualProcedureGraph& t){return f(t.learnerView(),"state").string();}
void refuse(ManualProcedureGraph& t,const std::function<void()>& call){const auto v=t.learnerView();const auto h=t.history();bool no=false;try{call();}catch(const tasks::recipes::Error&){no=true;}check(no,"REFUSAL_EXPECTED");check(v==t.learnerView()&&h==t.history(),"REFUSAL_MUTATED");++refusals;}
void act(ManualProcedureGraph& t,const std::string& action,const V& p){const auto token=t.capture(action);check(t.current(token));t.apply(token,p);check(!t.current(token));++gestures;refuse(t,[&]{t.apply(token,p);});check(f(t.learnerView(),"observed_performance")==V(false)&&f(t.learnerView(),"grants_credit")==V(false));}
void advance(ManualProcedureGraph& t){const auto a=t.learnerActions();check(!a.array().empty());const auto action=f(a.array().front(),"action").string();checkpoint+=" ->"+action;if(t.learnerView().find("node"))checkpoint+="/"+f(t.learnerView(),"node").string();act(t,action,X::positiveFor(t));}
void finish(ManualProcedureGraph& t){for(int i=0;state(t)!="completed"&&state(t)!="cancelled"&&i<300;++i){check(state(t)!="needs_retry","POSITIVE_DIAGNOSED");advance(t);}check(state(t)=="completed"||state(t)=="cancelled","FINITE_PATH");++paths;}
bool nullField(V& report,const V& schema){for(const auto& field:f(schema,"properties").object()){const auto& types=f(field.second,"type");if(types.isArray()&&std::find(types.array().begin(),types.array().end(),V("null"))!=types.array().end()&&!field.second.find("const")){report.object()[field.first]=nullptr;return true;}}return false;}
}
int main(){try{
std::set<std::string> programs;std::size_t old{},fresh{};
for(const auto& row:tasks::manual_procedure_graph_generated::rows){const auto& d=definition(row.key);checkpoint=row.key;programs.insert(f(d.retainedProgram(),"name").string());stages+=d.retainedProgram().find("graph")?f(f(d.retainedProgram(),"graph"),"nodes").object().size():f(d.retainedProgram(),"steps").array().size();row.original?++fresh:++old;ManualProcedureGraph t(d),foreign(d);const auto idle=t.capture("begin");const auto v=t.learnerView();check(t.fenceInactiveForNavigation()&&v==t.learnerView()&&t.history().empty());refuse(t,[&]{t.apply(idle,O{{"original_workbook",true},{"own_instrument",true}});});refuse(t,[&]{t.apply(foreign.capture("begin"),O{{"original_workbook",true},{"own_instrument",true}});});advance(t);
const auto actions=t.learnerActions();auto malformed=X::positiveFor(t);if(malformed.isObject()&&!malformed.object().empty()){malformed.object().erase(malformed.object().begin());const auto token=t.capture(f(actions.array().front(),"action").string());refuse(t,[&]{t.apply(token,malformed);});check(t.current(token));}
finish(t);check(t.fenceInactiveForNavigation());
}
check(old==224&&fresh==225&&programs.size()==tasks::manual_procedure_graph_generated::programCount);
// One source-program unknown path, release and diagnosed restart. No automatic
// physical activity or sibling execution is inferred from the unknown report.
std::set<std::string> recovered;
for(const auto& row:tasks::manual_procedure_graph_generated::rows){if(!row.original)continue;const auto& d=definition(row.key);const auto program=f(d.retainedProgram(),"name").string();if(!recovered.insert(program).second)continue;checkpoint="unknown "+std::string(row.key);ManualProcedureGraph t(d);advance(t);bool found=false;
for(int i=0;i<100;++i){auto report=X::positiveFor(t);const auto a=t.learnerActions();if(f(a.array().front(),"action")==V("submit")&&nullField(report,f(a.array().front(),"schema"))){act(t,"submit",report);found=true;break;}advance(t);}
check(found);const auto rawHistory=t.history();if(state(t)=="await_release"){check(f(t.learnerView(),"release_reason")==V("physical_attempt"));for(V bad:{V(false),V(nullptr)})refuse(t,[&]{t.apply(t.capture("release"),O{{"learner_released",bad},{"external_source_stopped",true}});});advance(t);}check(state(t)=="needs_retry");act(t,"retry",X::positiveFor(t));check(state(t)=="await_release"&&f(t.learnerView(),"release_reason")==V("active_exit"));advance(t);check(state(t)=="active"&&t.history().size()>rawHistory.size());finish(t);
}
try{(void)definition("foreign");check(false,"FOREIGN_KEY");}catch(const tasks::recipes::Error&){++refusals;}
std::cout<<"{\"outcome\":\"PASS\",\"rows\":449,\"old_preserved\":224,\"new_children\":225,\"source_programs\":"<<programs.size()<<",\"source_stages\":"<<stages<<",\"paths\":"<<paths<<",\"gestures\":"<<gestures<<",\"assertions\":"<<assertions<<",\"refusals\":"<<refusals<<",\"new_program_recoveries\":"<<recovered.size()<<",\"synthetic_manual_declarations\":true,\"actual_performance\":false,\"credit\":false}\n";return 0;
}catch(const std::exception& e){std::cerr<<checkpoint<<": "<<e.what()<<" gestures="<<gestures<<"\n";return 1;}}
