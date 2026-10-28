#pragma once
// TEST ONLY. Trusted expected values produce synthetic declarations; no real
// audio/performance evidence, and never a production input/default provider.
#include "tasks/ManualProcedureGraph.hpp"
#include "tasks/ManualProcedureProtocolSupport.hpp"
#include "tasks/ManualProcedureSourcePolicies.hpp"
#include <algorithm>
#include <set>
namespace fathom::tests::manual_procedure_fixture {
using namespace tasks::manual_procedure_graph;using V=json::Value;using O=V::Object;using A=V::Array;
inline void check(bool b,const char* why="FIXTURE"){if(!b)throw std::runtime_error(why);}
inline const V& f(const V& v,const char* name){auto* p=v.find(name);if(!p)throw std::runtime_error(std::string("FIXTURE_FIELD_")+name);return *p;}
inline std::int64_t num(const V& v){std::int64_t n{};check(v.integer(n));return n;}
const std::map<std::string,int> tuning{{"E",40},{"A",45},{"D",50},{"G",55},{"B",59},{"e",64}};
const std::map<std::string,int> pitch{{"C",0},{"C#",1},{"Db",1},{"D",2},{"D#",3},{"Eb",3},{"E",4},{"E#",5},{"F",5},{"F#",6},{"G",7},{"G#",8},{"A",9},{"A#",10},{"Bb",10},{"B",11},{"B#",0}};
inline V schemaFixture(const V& schema) {
    if(const auto* c=schema.find("const"))return *c;if(const auto* e=schema.find("enum"))return e->array().front();
    const auto& types=f(schema,"type");const auto kind=types.isString()?types.string():types.array().front().string();
    if(kind=="object") {O p;for(const auto& field:f(schema,"properties").object())p.emplace(field.first,schemaFixture(field.second));return p;}
    if(kind=="array") {A a;for(std::int64_t i=0;i<num(f(schema,"minItems"));++i)a.push_back(schemaFixture(f(schema,"items")));return a;}
    if(kind=="boolean")return true;if(kind=="integer"||kind=="number")return schema.find("minimum")?f(schema,"minimum"):V::fromInteger(0);
    std::string value="Synthetic manual declaration; no actual performance observed.";
    if(const auto* maximum=schema.find("maxLength"))value.resize(std::min(value.size(),static_cast<std::size_t>(num(*maximum))));
    if(const auto* minimum=schema.find("minLength"))value.resize(std::max(value.size(),static_cast<std::size_t>(num(*minimum))),'x');
    return value;
}
inline const V& step(const ManualProcedureGraph& t) {return f(t.retainedDefinition().retainedProgram(),"steps").array()[static_cast<std::size_t>(num(f(t.learnerView(),"cursor")))];}
inline V contact(const std::string& s,int fret,const std::string& name) {return O{{"string",s},{"fret",V::fromInteger(fret)},{"named_pitch",name}};}
inline V linearPositive(const ManualProcedureGraph& t) {
    const auto name=f(t.learnerActions().array().front(),"action").string();auto p=schemaFixture(f(t.learnerActions().array().front(),"schema"));
    if(name=="begin"||name=="release"||name=="finish"||name=="retry"||name=="reopen")return p;
    const auto& s=step(t);for(const auto& expected:f(s,"expected").object())p.object()[expected.first]=expected.second;
    if(f(s,"name").string()=="written_response")return f(t.retainedDefinition().retainedProgram(),"hidden_self_check");
    for(const auto& c:f(s,"constraints").array()) {
        const auto k=f(c,"kind").string();
        if(k=="minimum")p.object()[f(c,"field").string()]=f(c,"value");
        else if(k=="distinct_dates") {p.object()[f(c,"fields").array()[0].string()]="2026-09-30";p.object()[f(c,"fields").array()[1].string()]="2026-10-01";}
        else if(k=="different") {const auto key=f(c,"fields").array()[1].string();p.object()[key]=f(f(f(s,"schema"),"properties"),key.c_str()).find("enum")->array()[1];}
        else if(k=="caged_formula") {
            const auto root=f(c,"root").string();const auto r=num(f(f(f(t.learnerView(),"learner_responses"),"root_region"),"root_fret"));A frets,roots;const std::vector<std::string> strings{"E","A","D","G","B","e"};
            const auto& offsets=f(c,"offsets").array();for(std::size_t i=0;i<6;++i) {if(offsets[i].null())frets.emplace_back(nullptr);else {const int fret=static_cast<int>(r+num(offsets[i]));frets.push_back(V::fromInteger(fret));if((tuning.at(strings[i])+fret)%12==pitch.at(root))roots.push_back(contact(strings[i],fret,root));}}
            p.object()["frets"]=frets;p.object()["root_contacts"]=roots;
        } else if(k=="caged_subset") {
            const auto root=f(f(t.retainedDefinition().retainedProgram(),"source_facts"),"root").string();const int rpc=pitch.at(root);const auto view=t.learnerView();const auto& frets=f(f(f(view,"learner_responses"),"form"),"frets").array();const std::vector<std::string> strings{"E","A","D","G","B","e"};A all;
            for(std::size_t i=0;i<6;++i)if(!frets[i].null()) {const int fret=static_cast<int>(num(frets[i])),pc=(tuning.at(strings[i])+fret)%12;const auto spelling=std::find_if(pitch.begin(),pitch.end(),[&](const auto& n){return n.second==pc;});check(spelling!=pitch.end());all.push_back(contact(strings[i],fret,spelling->first));}
            A chosen;if(num(f(c,"minimum"))==2)chosen={all[0],all[1]};else {for(int pc:{rpc,(rpc+4)%12,(rpc+7)%12}) {const auto it=std::find_if(all.begin(),all.end(),[&](const V& x){return pitch.at(f(x,"named_pitch").string())==pc;});check(it!=all.end());chosen.push_back(*it);}p.object()["inversion"]="root";p.object()["lowest_degree"]="1";}p.object()["contacts"]=chosen;
        } else if(k=="triad_names") {
            const int r=static_cast<int>(num(f(p,"bass_fret")));A names;for(std::size_t i=0;i<3;++i) {const int pc=(tuning.at(f(c,"strings").array()[i].string())+r+num(f(c,"offsets").array()[i]))%12;const auto& allowed=f(c,"allowed_notes").array();const auto it=std::find_if(allowed.begin(),allowed.end(),[&](const V& n){return pitch.at(n.string())==pc;});check(it!=allowed.end());names.push_back(*it);}p.object()["named_notes"]=names;
        }
    }
    return p;
}

inline V lookup(const V& ref,const V& view,const V& payload) {
 V result=f(ref,"scope")==V("saved")?f(view,"learner_responses"):f(ref,"scope")==V("failed")?f(view,"failed_source_pass"):payload;
 for(const auto& path:f(ref,"path").array()){V next=path.isString()?f(result,path.string().c_str()):result.array()[static_cast<std::size_t>(num(path))];result=std::move(next);}return result;
}
inline void setPath(V& value,const A& path,const V& report) {check(!path.empty());V* target=&value;for(const auto& part:path){if(part.isString())target=&target->object().at(part.string());else target=&target->array().at(static_cast<std::size_t>(num(part)));}*target=report;}
inline void setRef(V& payload,const V& reference,const V& report){check(f(reference,"scope")==V("payload"));setPath(payload,f(reference,"path").array(),report);}
inline V pathValue(V value,const A& path){for(const auto& part:path)value=part.isString()?f(value,part.string().c_str()):value.array().at(static_cast<std::size_t>(num(part)));return value;}
inline void futureGuards(const ManualProcedureGraph& task,const V& node,const V& graph,const V& view,V& payload){
 if(auto field=payload.object().find("reported_tension");field!=payload.object().end())field->second=false;
 if(auto field=payload.object().find("prior_manual_bpm");field!=payload.object().end())field->second=view.find("retained_reported_bpm_ceiling")&&!f(view,"retained_reported_bpm_ceiling").null()?f(view,"retained_reported_bpm_ceiling"):V::fromInteger(100);
 for(auto& field:payload.object())if(field.first.rfind("rating_",0)==0)field.second=V::fromInteger(2);
 for(const auto& c:f(node,"constraints").array()){
  const auto kind=f(c,"kind").string();
  if(kind=="minimum"||kind=="maximum"){auto& value=payload.object()[f(c,"field").string()];const auto bound=num(f(c,"value"));value=V::fromInteger(value.isNumber()?(kind=="minimum"?std::max(num(value),bound):std::min(num(value),bound)):bound);}
  if(kind=="distinct_dates"){const auto& names=f(c,"fields").array();payload.object()[names[0].string()]="2026-09-30";payload.object()[names[1].string()]="2026-10-01";}
  if(kind=="equal"){const auto& names=f(c,"fields").array();payload.object()[names[1].string()]=f(payload,names[0].string().c_str());}
  if(kind=="different"){const auto& names=f(c,"fields").array();payload.object()[names[0].string()]="Synthetic material one";payload.object()[names[1].string()]="Synthetic material two";}
  if(kind=="same_as_saved"){if(c.find("field"))payload.object()[f(c,"field").string()]=lookup(f(c,"saved_ref"),view,payload);else setRef(payload,f(c,"left"),lookup(f(c,"right"),view,payload));}
  if(kind=="same_as_failed_pass")setRef(payload,f(c,"payload_ref"),f(f(view,"failed_source_pass"),"pass_tag"));
  if(kind=="equals_literal")setRef(payload,f(c,"value_ref"),f(c,"literal"));
  if(kind=="reported_seconds_at_least"){
   const auto& lower=f(c,"lower_bound_ref");const auto value=f(lower,"scope")==V("contract")?pathValue(task.retainedDefinition().retainedOriginalContract(),f(lower,"path").array()):lookup(lower,view,payload);setRef(payload,f(c,"value_ref"),value);
  }
  if(kind=="domain_lookup"){
   const auto& first=f(f(graph,"domains"),f(c,"domain").string().c_str()).array().front();for(const auto& selection:f(c,"selection").object())if(f(selection.second,"scope")==V("payload"))setRef(payload,selection.second,f(f(first,"selection"),selection.first.c_str()));
  }
  if(kind=="source_policy_reported"){
   if(f(c,"policy")==V("reported_bpm_delta"))payload.object()[f(c,"after_field").string()]=V::fromInteger(num(f(payload,f(c,"before_field").string().c_str()))+num(f(c,"minimum_delta")));
   else if(f(c,"policy")==V("workload_route_tempo_choice"))payload.object()[f(c,"choice_field").string()]=f(view,"required_reported_tempo_reduction")==V(true)?V("reduce_route_to_one_tetrachord"):V("hold_current_tempo");
   else payload.object()[f(c,"choice_field").string()]=f(view,"required_reported_tempo_reduction")==V(true)?V("reduce_after_errors_or_tension"):V("hold");
  }
  if(kind=="readiness_next_day_reports"){payload.object()[f(c,"before_field").string()]="2026-09-30";payload.object()[f(c,"after_field").string()]="2026-10-01";}
  if(kind=="seventh_quality_permutation")payload.object()[f(c,"field").string()]=A{"maj7","7","m7","m7b5"};
  if(kind=="source_order_permutation")payload.object()[f(c,"field").string()]=f(c,"domain");
  if(kind=="source_adjacent_sets")payload.object()[f(c,"target_field").string()]="D_G_B";
  if(kind=="selected_source_literal"){const auto choice=lookup(f(c,"choice_ref"),view,payload);const auto& selected=f(f(f(graph,"domains"),f(c,"domain").string().c_str()),choice.string().c_str());for(const auto& report:f(c,"reports").object())payload.object()[report.first]=f(selected,report.second.string().c_str());}
  if(kind=="source_assignment_coverage"){A result;for(const auto& position:f(c,"positions").array())for(const auto& pattern:f(c,"patterns").array())result.emplace_back(O{{"position",position},{"pattern",pattern}});payload.object()[f(c,"field").string()]=result;}
  if(kind=="source_protocol_reported"){
   if(f(c,"policy")==V("timed_ladder")){payload.object()[f(c,"work_field").string()]=f(c,"source_work_targets");payload.object()[f(c,"rest_field").string()]=f(c,"source_work_targets");payload.object()[f(c,"clean_sets_field").string()]=f(c,"minimum_clean_sets");}
  }
 }
 // Populate equal groups after their minima, then reenter earlier ratings
 // before the separately entered synthetic sum declaration.
 for(int pass=0;pass<2;++pass)for(const auto& c:f(node,"constraints").array())if(f(c,"kind")==V("equal")){const auto& names=f(c,"fields").array();auto left=f(payload,names[0].string().c_str()),right=f(payload,names[1].string().c_str());if(left.isNumber()&&right.isNumber()){const auto value=V::fromInteger(std::max(num(left),num(right)));payload.object()[names[0].string()]=value;payload.object()[names[1].string()]=value;}else payload.object()[names[1].string()]=left;}
 for(const auto& c:f(node,"constraints").array())if(f(c,"kind")==V("reported_score_sum")){std::int64_t sum{};for(const auto& field:f(c,"fields").array())sum+=num(f(payload,field.string().c_str()));payload.object()[f(c,"total_field").string()]=V::fromInteger(sum);}
 for(const auto& c:f(node,"constraints").array())if(f(c,"kind")==V("same_as_saved")){if(c.find("field"))payload.object()[f(c,"field").string()]=lookup(f(c,"saved_ref"),view,payload);else setRef(payload,f(c,"left"),lookup(f(c,"right"),view,payload));}
 for(const auto& c:f(node,"constraints").array())if(f(c,"kind")==V("different")){const auto& fields=f(c,"fields").array();if(f(payload,fields[0].string().c_str())==f(payload,fields[1].string().c_str()))payload.object()[fields[1].string()]=f(payload,fields[0].string().c_str()).string()+" separately authored variant";}
}
inline V priorPositiveFor(const ManualProcedureGraph& task) {
 if(!task.retainedDefinition().retainedProgram().find("graph"))return linearPositive(task);
 const auto view=task.learnerView();const auto a=task.learnerActions();const auto action=f(a.array().front(),"action").string();auto payload=schemaFixture(f(a.array().front(),"schema"));
 if(action=="begin"||action=="release"||action=="retry"||action=="reopen"||action=="reveal_recorded_order"||action=="reveal_source_answer"||action=="close_reference")return payload;
 const auto& d=definition(f(view,"current_source_key").string());const auto& g=f(d.retainedProgram(),"graph");const auto node=f(view,"node").string();const auto& n=f(f(g,"nodes"),node.c_str());
 for(const auto& e:f(n,"expected").object())payload.object()[e.first]=e.second;
 futureGuards(task,n,g,view,payload);
 if(const auto* c=n.find("computed_expected")) {
  if(f(*c,"kind")==V("selected_direction_bindings")){A result;result.push_back(f(*c,"pass"));const auto dirs=lookup(f(*c,"directions_ref"),view,payload);result.insert(result.end(),dirs.array().begin(),dirs.array().end());payload.object()[f(*c,"report_field").string()]=result;}
  else if(f(*c,"kind")==V("source_order_P_directions")){const auto projected=tasks::manual_procedure_graph_support::projectSourceOrderedPDirections(*c,lookup(f(*c,"directions_ref"),view,payload));check(projected.resolved);for(const auto& field:projected.values.object())payload.object()[field.first]=field.second;}
  else {O select;for(const auto& x:f(*c,"selection").object())select[x.first]=lookup(x.second,view,payload);V domains;const auto name=f(*c,"domain").string();if(const auto* local=f(g,"domains").find(name))domains=*local;else {const auto& p=tasks::manual_procedure_graph::definition(select.at("source_key").string()).retainedProgram();domains=f(f(p,"graph"),"domains").object().at("failed_pass_pairs");}
   const auto it=std::find_if(domains.array().begin(),domains.array().end(),[&](const V& item){return f(item,"selection")==V(select);});check(it!=domains.array().end(),"FIXTURE_PAIR");for(const auto& field:f(*c,"fields").object()){A values;for(const auto& contact:f(*it,"contacts").array())values.push_back(f(contact,field.second.string().c_str()));payload.object()[field.first]=values;}
  }
 }
 if(node=="finish_choice")payload.object()["choice"]="complete_cell";
 if(node=="followup")payload.object()["choice"]="stop";
 if(node=="compare2")payload.object()["choice"]="clean_match_finish";
 if(node=="repair_choice"&&payload.find("failed_pass")){payload.object()["choice"]="retry_from_entry";payload.object()["failed_pass"]=nullptr;payload.object()["pair_start"]=nullptr;}
 if(node=="repair_after")payload.object()["choice"]="retry_from_entry";
 if(node=="family_repair_choice"){payload.object()["choice"]="resubmit_family_audit";payload.object()["case_key"]=nullptr;payload.object()["pass"]=nullptr;payload.object()["pair_start"]=nullptr;}
 if(node=="family_audit") {payload.object()["audit_result"]="consistent";const auto& cs=f(n,"constraints").array();const auto& keys=f(cs.front(),"expected_keys").array();auto& rows=payload.object()["submissions"].array();const auto tempo=f(f(f(view,"learner_responses"),"choice"),"tempo_label");for(std::size_t i=0;i<rows.size();++i){auto& item=rows[i].object();item["case_key"]=keys[i];item["tempo_label"]=tempo;for(auto& j:item["judgments"].object()){j.second.object()["result"]="consistent";j.second.object()["pair_start"]=nullptr;}for(auto& x:item["responses"].array())x="acknowledged";}}
 return payload;
}
inline V prior1287PositiveFor(const ManualProcedureGraph& task){
 auto payload=priorPositiveFor(task);const auto view=task.learnerView();if(!view.find("node")||f(view,"state")!=V("active"))return payload;const auto& g=f(task.retainedDefinition().retainedProgram(),"graph");const auto& node=f(f(g,"nodes"),f(view,"node").string().c_str());const auto& saved=f(view,"learner_responses").object();if(!node.find("constraints"))return payload;
 if(const auto* projection=node.find("schema_projection")){payload=tasks::manual_procedure_graph_support::derivedExpectedReports(*projection,saved,f(f(g,"domains"),"source_triad42"));return payload;}
 for(const auto& c:f(node,"constraints").array()){
  const auto kind=f(c,"kind").string();
  if(kind=="strictly_ascending_unique_integer_array")payload.object()[f(c,"field").string()]=A{f(c,"allowed_values").array().front()};
  if(kind=="complete_unique_choice_permutation")payload.object()[f(c,"field").string()]=f(c,"values");
  if(kind=="selected_source_pattern_reports"){const auto expected=tasks::manual_procedure_graph_support::futurePatternProjection(f(c,"projection"),saved,f(f(g,"domains"),"source_triad42"));for(const auto& field:expected.object())payload.object()[field.first]=field.second;}
  if(kind=="manual_source_safety_stop")for(const auto& field:f(c,"fields").array())payload.object()[field.string()]=false;
  if(kind=="c_fresh_recovery_scope")payload.object()[f(c,"field").string()]="Fresh complete same-source verification scope";
  if(kind=="c_distinct_registers")payload.object()[f(c,"field").string()]=A{"Explicit lower chosen register","Explicit upper chosen register"};
  if(kind=="c_manual_rubric"){auto& days=payload.object()["days"].array();for(std::size_t i=0;i<2;++i){days[i].object()["date"]=i==0?V("2026-09-30"):V("2026-10-01");days[i].object()["scores"]=A{V::fromInteger(2),V::fromInteger(2),V::fromInteger(2),V::fromInteger(2),V::fromInteger(2),V::fromInteger(2),V::fromInteger(2),V::fromInteger(2)};days[i].object()["reported_total"]=V::fromInteger(16);}}
  if(kind=="c_dynamic_arc_counts"){for(auto& pass:payload.object()["passes"].array()){A counts;const std::vector<int> minima={1,4,4,6,2,4,6,1};std::size_t section=0;for(const auto& row:f(c,"sections").array()){const auto bars=f(row,"Bars").string();auto dash=bars.find('-');auto first=std::stoi(bars.substr(0,dash)),last=std::stoi(bars.substr(dash+1));for(int bar=first;bar<=last;++bar)counts.push_back(V::fromInteger(minima[section]));++section;}counts[44]=V::fromInteger(4);counts[45]=V::fromInteger(3);counts[46]=V::fromInteger(2);counts[47]=V::fromInteger(1);pass.object()["contact_counts"]=counts;}}
 }
 if(auto* protocols=task.retainedDefinition().retainedProgram().find("source_state_protocols"))for(const auto& protocol:protocols->array()){
  const auto kind=f(protocol,"kind").string();if(kind=="source_reported_stop_condition"&&f(protocol,"node")==f(view,"node"))payload.object()[f(protocol,"field").string()]=false;
  if(kind=="manual_source_safety_stop"){if(const auto* fields=protocol.find("known_true_report_fields"))for(const auto& field:fields->array())if(payload.find(field.string()))payload.object()[field.string()]=false;}
 }
 if(f(view,"node")==V("choose_extensions")&&payload.find("selected_source_cells"))payload.object()["selected_source_cells"]=A{"F2","F3","F4","F5"};
 return payload;
}

inline V capstonePositiveFor(const ManualProcedureGraph& task) {
 const auto actions=task.learnerActions();auto payload=schemaFixture(f(actions.array().front(),"schema"));
 const auto view=task.learnerView();if(f(view,"state")!=V("active")||f(actions.array().front(),"action")!=V("submit"))return payload;
 const auto& graph=f(task.retainedDefinition().retainedProgram(),"graph");const auto& node=f(f(graph,"nodes"),f(view,"node").string().c_str());
 for(const auto& expected:f(node,"expected").object())payload.object()[expected.first]=expected.second;
 if(payload.find("selected_master_tempo_BPM"))payload.object()["selected_master_tempo_BPM"]=json::Number{"60.5"};
 if(payload.find("selected_master_tempo_BPM_reentered"))payload.object()["selected_master_tempo_BPM_reentered"]=json::Number{"60.50"};
 if(payload.find("eight_source_section_outcomes")) {
  auto& reports=payload.object()["eight_source_section_outcomes"].array();const auto& blocks=f(f(graph,"domains"),"reviewed_C89_source_blocks").array();
  const std::pair<const char*,const char*> names[]={{"reported_bars","Bars"},{"reported_harmony","Harmony"},{"reported_groove","Groove"},{"reported_primary_engine","Primary engine"},{"reported_dynamic","Dynamic"}};
  for(std::size_t i=0;i<8;++i)for(const auto& name:names)reports[i].object()[name.first]=f(f(blocks[i],"source_fields"),name.second);
 }
 return payload;
}
inline V positiveFor(const ManualProcedureGraph& task) {
 if(f(task.retainedDefinition().retainedProgram(),"name")==V("level089:reviewed_derived_six_full32bar_passes"))return capstonePositiveFor(task);
 return prior1287PositiveFor(task);
}

} // namespace fathom::tests::manual_procedure_fixture
