#include "ManualProcedureGraphFixture.hpp"
#include <GeneratedManualProcedureGraph.hpp>
#include <iostream>
#include <set>
using namespace fathom;using namespace tasks::manual_procedure_graph;
namespace X=tests::manual_procedure_fixture;using V=json::Value;using O=V::Object;using A=V::Array;
namespace {
std::size_t assertions{},initial{},states{},nodes{},gestures{},recoveries{},frames{};std::string checkpoint;
void check(bool ok,const char* reason){++assertions;if(!ok)throw std::runtime_error(reason);}
const V& f(const V& value,const char* name){const auto* p=value.find(name);check(p!=nullptr,"FIELD");return *p;}
void safeText(const V& value,const Definition& d){check(value.isString()&&!value.string().empty(),"TEXT_TYPE");for(const auto* forbidden:{"Build/","Results/","Prompts/","source_key","source_identity","contract_sha256","original_row_sha256","trusted_source_context_only"})check(value.string().find(forbidden)==std::string::npos,"TRUSTED_METADATA_EXPOSED");check(value.string().find(d.sourceKey())==std::string::npos&&value.string().find(d.contractSha256())==std::string::npos,"SOURCE_AUTHORITY_EXPOSED");}
void projection(ManualProcedureGraph& task){const auto before=task.learnerView();const auto history=task.history();const auto instructions=task.learnerInstructions();check(instructions.isObject()&&instructions.object().size()==4,"INSTRUCTION_SHAPE");check(f(instructions,"source_clock").null()&&f(instructions,"fixed_bpm").null()&&f(instructions,"actual_performance_verified")==V(false),"PERFORMANCE_CLAIM");const auto& text=f(instructions,"text");check(text.isArray()&&!text.array().empty(),"INSTRUCTIONS_EMPTY");const auto& d=before.find("current_source_key")?definition(f(before,"current_source_key").string()):task.retainedDefinition();const auto context=d.learnerInstructionContext();check(context.isArray(),"CONTEXT_TYPE");for(const auto& line:context.array()){safeText(line,d);check(std::find(text.array().begin(),text.array().end(),line)!=text.array().end(),"SOURCE_CONTEXT_LOST");}for(const auto& line:text.array())safeText(line,d);check(before==task.learnerView()&&history==task.history(),"PROJECTION_MUTATED");++states;if(d.sourceKey()!=task.retainedDefinition().sourceKey())++frames;
if(d.exportedDefinition().find("retained_contract_path")&&f(d.exportedDefinition(),"retained_contract_path")==V(A{"implementation","table_task"})){const auto rendered=json::stringify(context);check(rendered.find("Session protocol")!=std::string::npos&&rendered.find("ASTERISK RULE")!=std::string::npos&&rendered.find("an unstable note.")!=std::string::npos,"TABLE_GOVERNING_PROSE_LOST");check(rendered.find("H1 Seed statement Nte|")==std::string::npos&&rendered.find("Twelve two-note recovery cards")==std::string::npos,"TABLE_OTHER_ANSWERS_EXPOSED");}
}
std::string state(const ManualProcedureGraph& t){return f(t.learnerView(),"state").string();}
void advance(ManualProcedureGraph& task){projection(task);const auto actions=task.learnerActions();check(!actions.array().empty(),"NO_ACTION");const auto action=f(actions.array().front(),"action").string();checkpoint+=" ->"+action;if(task.learnerView().find("node"))checkpoint+="/"+f(task.learnerView(),"node").string();task.apply(task.capture(action),X::positiveFor(task));++gestures;}
void finish(ManualProcedureGraph& task){for(int i=0;state(task)!="completed"&&state(task)!="cancelled"&&i<300;++i){check(state(task)!="needs_retry","POSITIVE_DIAGNOSED");advance(task);}check(state(task)=="completed"||state(task)=="cancelled","FINITE_PATH");projection(task);}
bool unknown(V& report,const V& schema){for(const auto& field:f(schema,"properties").object()){const auto& kinds=f(field.second,"type");if(kinds.isArray()&&std::find(kinds.array().begin(),kinds.array().end(),V("null"))!=kinds.array().end()&&!field.second.find("const")){report.object()[field.first]=nullptr;return true;}}return false;}
}
int main(){try{
std::set<std::string> programs;
for(const auto& row:tasks::manual_procedure_graph_generated::rows){checkpoint=row.key;const auto& d=definition(row.key);ManualProcedureGraph task(d);projection(task);++initial;
const auto context=d.learnerInstructionContext();for(const auto& line:context.array())safeText(line,d);
// The active projection adds only the current node's literal instruction to
// this same closed context. Check every node, including repair-only branches,
// without manufacturing reports to enter unreachable or guarded routes.
if(const auto* graph=d.retainedProgram().find("graph")){for(const auto& node:f(*graph,"nodes").object()){if(const auto* instruction=node.second.find("instruction"))safeText(*instruction,d);++nodes;}}
else for(const auto& step:f(d.retainedProgram(),"steps").array()){safeText(f(step,"instruction"),d);++nodes;}
finish(task);check(task.fenceInactiveForNavigation(),"IDLE_FENCE");projection(task);
}
for(const auto& row:tasks::manual_procedure_graph_generated::rows){if(!row.original)continue;const auto& d=definition(row.key);const auto program=f(d.retainedProgram(),"name").string();if(!programs.insert(program).second)continue;checkpoint="unknown "+std::string(row.key);ManualProcedureGraph task(d);advance(task);bool found=false;
for(int i=0;i<100;++i){projection(task);const auto actions=task.learnerActions();auto report=X::positiveFor(task);if(f(actions.array().front(),"action")==V("submit")&&unknown(report,f(actions.array().front(),"schema"))){task.apply(task.capture("submit"),report);++gestures;found=true;break;}advance(task);}
check(found,"UNKNOWN_CASE");projection(task);if(state(task)=="await_release")advance(task);check(state(task)=="needs_retry","UNKNOWN_NOT_DIAGNOSED");advance(task);check(state(task)=="await_release","RETRY_RELEASE");advance(task);finish(task);++recoveries;
}
// Execute a guarded peer-call route from every enclosure source row so the
// projection must follow the current frame rather than the retained root.
std::size_t callRows{};
for(const auto& row:tasks::manual_procedure_graph_generated::rows){const auto& d=definition(row.key);if(f(d.retainedProgram(),"name")!=V("l061_paired_enclosure_choice_routes"))continue;checkpoint="callee "+std::string(row.key);ManualProcedureGraph task(d);advance(task);
auto toFollowup=[&](){for(int i=0;i<100&&f(task.learnerView(),"node")!=V("followup");++i)advance(task);check(f(task.learnerView(),"node")==V("followup"),"FOLLOWUP_ROUTE");projection(task);};toFollowup();
auto choose=[&](const char* choice){projection(task);task.apply(task.capture("choose"),O{{"choice",choice},{"current_separate",true},{"other_separate",true}});++gestures;projection(task);};
choose("practice_other_order");check(f(task.learnerView(),"call_depth")==V::fromInteger(2),"CALLEE_NOT_ENTERED");toFollowup();choose("alternate_one_pair");toFollowup();choose("stop");if(state(task)=="await_release")advance(task);projection(task);check(state(task)=="cancelled","STOP_ROUTE");++callRows;
}
check(initial==449&&nodes>=4000&&callRows==16&&frames>0,"EXACT_SCOPE");std::cout<<"{\"outcome\":\"PASS\",\"initial_rows\":"<<initial<<",\"closed_node_or_stage_instructions\":"<<nodes<<",\"reachable_state_projections\":"<<states<<",\"synthetic_gestures\":"<<gestures<<",\"new_program_unknown_recoveries\":"<<recoveries<<",\"callee_rows\":"<<callRows<<",\"callee_state_projections\":"<<frames<<",\"assertions\":"<<assertions<<",\"manual_reports_are_synthetic\":true,\"actual_performance\":false,\"credit\":false}\n";return 0;
}catch(const std::exception& e){std::cerr<<checkpoint<<": "<<e.what()<<" states="<<states<<"\n";return 1;}}
