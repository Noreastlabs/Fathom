#include "ManualProcedureGraphFixture.hpp"
#include <GeneratedManualProcedureGraph.hpp>
#include <iostream>
#include <functional>
using namespace fathom;using namespace tasks::manual_procedure_graph;
namespace X=tests::manual_procedure_fixture;namespace S=tasks::manual_procedure_graph_support;using V=json::Value;using O=V::Object;using A=V::Array;
namespace {std::size_t assertions{},refusals{},cases{},gestures{};std::string checkpoint;
void check(bool b,const char* why="CHECK"){++assertions;if(!b)throw std::runtime_error(why);}
const V& f(const V& v,const char* n){const auto* p=v.find(n);check(p,"FIELD");return *p;}
std::string state(const ManualProcedureGraph& t){return f(t.learnerView(),"state").string();}
void act(ManualProcedureGraph& t,const std::string& a,const V& p){const auto token=t.capture(a);t.apply(token,p);check(!t.current(token));++gestures;}
void advance(ManualProcedureGraph& t){const auto a=t.learnerActions();act(t,f(a.array().front(),"action").string(),X::positiveFor(t));}
void seek(ManualProcedureGraph& t,const std::string& name){for(int i=0;i<200;++i){const auto v=t.learnerView();if(state(t)=="active"&&f(v,"node")==V(name))return;check(state(t)!="needs_retry"&&state(t)!="completed"&&state(t)!="cancelled","TARGET_NOT_REACHED");advance(t);}check(false,"TARGET_FINITE");}
void refuse(ManualProcedureGraph& t,const std::function<void()>& call){const auto v=t.learnerView(),h=V(t.history());bool no=false;try{call();}catch(const std::exception&){no=true;}check(no&&v==t.learnerView()&&h==V(t.history()),"REFUSAL_MUTATED_OR_MISSING");++refusals;}
bool debt(const ManualProcedureGraph& t){return f(t.learnerView(),"required_reported_tempo_reduction")==V(true);}
void diagnosed(ManualProcedureGraph& t){if(state(t)=="await_release")advance(t);check(state(t)=="needs_retry");}
void restart(ManualProcedureGraph& t){act(t,"retry",O{{"diagnosis","Synthetic diagnosis; no actual performance"}});check(state(t)=="await_release"&&f(t.learnerView(),"release_reason")==V("active_exit"));advance(t);}
std::string matching(const std::string& text){for(const auto& key:keys())if(key.find(text)!=std::string::npos)return key;throw std::runtime_error("KEY_NOT_FOUND");}
}
int main(){try{
// Persistent reduction and validated-ceiling semantics for all three exact
// source programs, through cancellation, unknown, release, reopen and restart.
std::size_t policies{};
for(const auto& key:keys()){const auto& d=definition(key);const auto* graph=d.retainedProgram().find("graph");if(!graph)continue;const auto* policy=graph->find("source_state_protocols");if(!policy||policy->array().empty())continue;++policies;checkpoint="tempo "+key;
 ManualProcedureGraph t(d);advance(t);auto source=X::positiveFor(t);source.object()["reported_error_count"]=V::fromInteger(2);act(t,"submit",source);check(debt(t)&&f(t.learnerView(),"reported_tempo_trigger_unresolved")==V(false));act(t,"cancel",O{});check(debt(t)&&state(t)=="await_release");refuse(t,[&]{t.apply(t.capture("reopen"),O{});});advance(t);const auto saved=t.history();check(state(t)=="cancelled"&&debt(t)&&t.fenceInactiveForNavigation()&&saved==t.history());act(t,"reopen",O{});check(state(t)=="select"&&debt(t));advance(t);advance(t);seek(t,"criterion_007_choose");auto bad=X::positiveFor(t);bad.object()["tempo_decision"]="hold";act(t,"choose",bad);check(state(t)=="needs_retry"&&debt(t));restart(t);seek(t,"criterion_007_choose");auto choice=X::positiveFor(t);choice.object()["prior_manual_bpm"]=V::fromInteger(100);act(t,"choose",choice);check(f(t.learnerView(),"node")==V("criterion_008"));auto reduction=X::positiveFor(t);reduction.object()["new_manual_bpm"]=V::fromInteger(95);act(t,"submit",reduction);check(state(t)=="completed"&&!debt(t)&&f(t.learnerView(),"retained_reported_bpm_ceiling")==V::fromInteger(95));const auto before=t.history();const auto old=t.capture("reopen");check(t.fenceInactiveForNavigation()&&before==t.history());refuse(t,[&]{t.apply(old,O{});});act(t,"reopen",O{});check(!debt(t));advance(t);advance(t);seek(t,"criterion_007_choose");bad=X::positiveFor(t);bad.object()["prior_manual_bpm"]=V::fromInteger(100);act(t,"choose",bad);check(state(t)=="needs_retry"&&f(t.learnerView(),"retained_reported_bpm_ceiling")==V::fromInteger(95));restart(t);seek(t,"criterion_007_choose");advance(t);check(state(t)=="completed"&&!debt(t));++cases;
 ManualProcedureGraph unknown(d);advance(unknown);source=X::positiveFor(unknown);source.object()["reported_error_count"]=nullptr;act(unknown,"submit",source);check(debt(unknown)&&f(unknown.learnerView(),"reported_tempo_trigger_unresolved")==V(true));check(f(f(unknown.history().back(),"reported"),"reported_error_count").null()&&f(f(unknown.learnerView(),"diagnosis"),"observed_failure")==V(false));diagnosed(unknown);restart(unknown);seek(unknown,"criterion_007_choose");bad=X::positiveFor(unknown);bad.object()["tempo_decision"]="increase_after_three_clean_trips";act(unknown,"choose",bad);check(state(unknown)=="needs_retry"&&debt(unknown));++cases;
}
check(policies==3);
// Every preserved completed224 graph keeps its prior empty action surface.
for(const auto& row:tasks::manual_procedure_graph_generated::rows)if(!row.original){check(definition(row.key).exportedDefinition()==json::parse(row.value));}
// Manual criterion evidence, valid unknown and malformed integer separation.
const auto criterionKey=matching("l038-module-d-space-and-density-density-test");
for(V evidence:{V("   "),V("\xc2\xa0\xc2\xa0"),V(nullptr)}){checkpoint="trimmed evidence";ManualProcedureGraph t(definition(criterionKey));advance(t);seek(t,"criterion_001");auto p=X::positiveFor(t);p.object()["manual_evidence"]=evidence;act(t,"submit",p);check(state(t)=="needs_retry"&&f(f(t.history().back(),"reported"),"manual_evidence")==evidence);++cases;}
{ManualProcedureGraph t(definition(criterionKey));advance(t);seek(t,"criterion_001");auto p=X::positiveFor(t);p.object()["reported_bpm_1"]=true;const auto token=t.capture("submit");refuse(t,[&]{t.apply(token,p);});check(t.current(token));++cases;}
// Literal Gregorian dates and saved score bindings. Two independent rubric
// shapes remain source-specific, with no override of earlier typed ratings.
for(const auto& key:keys()){const auto& p=definition(key).retainedProgram();const auto* graph=p.find("graph");if(!graph)continue;std::string target;for(const auto& n:f(*graph,"nodes").object())if(n.second.find("constraints"))for(const auto& c:f(n.second,"constraints").array())if(f(c,"kind")==V("reported_score_sum"))target=n.first;if(target.empty())continue;checkpoint="rubric "+key;
 for(const auto& badDate:{"2026-02-29","2026-09-30"}){ManualProcedureGraph t(definition(key));advance(t);seek(t,target);auto report=X::positiveFor(t);report.object()["date_2"]=badDate;act(t,"submit",report);check(state(t)=="needs_retry");++cases;}
 {ManualProcedureGraph t(definition(key));advance(t);seek(t,target);auto report=X::positiveFor(t);report.object()["reported_score_1"]=V::fromInteger(1);act(t,"submit",report);check(state(t)=="needs_retry");++cases;}
 {ManualProcedureGraph t(definition(key));advance(t);seek(t,target);auto report=X::positiveFor(t);const auto& n=f(f(*graph,"nodes"),target.c_str());const auto& guard=*std::find_if(f(n,"constraints").array().begin(),f(n,"constraints").array().end(),[](const V& c){return X::f(c,"kind")==V("reported_score_sum");});report.object()[f(guard,"fields").array()[0].string()]=V::fromInteger(1);act(t,"submit",report);check(state(t)=="needs_retry");++cases;}
}
// Every authored table choice is checked against the pinned signed source
// movement, including the whole-tone D->E row; no semitone-only assumption.
std::size_t pairs{};for(const auto& key:keys()){const auto& p=definition(key).retainedProgram();if(f(p,"name")!=V("l061_table_nearest_target_recovery"))continue;const auto& graph=f(p,"graph"),n=f(f(graph,"nodes"),"recover"),op=f(n,"computed_expected"),domain=f(f(graph,"domains"),"chosen_pair");for(const auto& row:domain.array()){auto result=S::projectClosedDomainReports(op,f(row,"selection"),domain);check(result.resolved&&result.values.object().size()==4);++pairs;}auto mutant=domain;mutant.array()[0].object()["source_clock"]=V::fromInteger(60);bool refused=false;try{(void)S::projectClosedDomainReports(op,f(domain.array()[0],"selection"),mutant);}catch(const std::exception&){refused=true;}check(refused);++refusals;}
check(pairs==576);++cases;
// Unicode source spans are codepoint slices, not UTF8 byte offsets.
check(S::utf8TextSlice("α → ‘quoted’ é",2,3)=="→");check(S::utf8TextSlice("α → ‘quoted’ é",4,12)=="‘quoted’");check(S::utf8TextLength("α → ‘quoted’ é")==14);bool no=false;try{(void)S::utf8TextSlice("α → ‘quoted’ é",0,15);}catch(const std::exception&){no=true;}check(no);++refusals;++cases;
// Exact decimal comparisons preserve reported values and reject bool clocks.
check(S::reportedSecondsAtLeast(json::parse("30.000000000000000001"),json::parse("30")));check(!S::reportedSecondsAtLeast(json::parse("29.999999999999999999"),json::parse("30")));check(!S::reportedSecondsAtLeast(V(nullptr),json::parse("30")));no=false;try{(void)S::reportedSecondsAtLeast(V(true),json::parse("30"));}catch(const std::exception&){no=true;}check(no);++refusals;++cases;
std::cout<<"{\"outcome\":\"PASS\",\"tempo_source_policies\":3,\"source_table_choices\":"<<pairs<<",\"material_cases\":"<<cases<<",\"gestures\":"<<gestures<<",\"assertions\":"<<assertions<<",\"refusals\":"<<refusals<<",\"synthetic_manual_reports\":true,\"actual_performance\":false,\"credit\":false}\n";return 0;
}catch(const std::exception& e){std::cerr<<checkpoint<<": "<<e.what()<<" gestures="<<gestures<<"\n";return 1;}}
