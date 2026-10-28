#include "tasks/ManualProcedureGraph.hpp"
#include "tasks/ManualCurriculumTask.hpp"
#include "ManualProcedureGraphFixture.hpp"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <set>
using namespace fathom;using namespace fathom::tasks::manual_procedure_graph;
namespace C=fathom::tasks::manual_curriculum;using V=json::Value;using O=V::Object;using A=V::Array;
namespace {
std::size_t assertions{},refusals{},actions{},paths{};std::string checkpoint;
void check(bool good,const char* why="CHECK"){++assertions;if(!good)throw std::runtime_error(why);}
const V& f(const V& value,const char* key){auto* p=value.find(key);check(p!=nullptr,"FIELD");return *p;}
std::int64_t num(const V& v){std::int64_t n{};check(v.integer(n),"INTEGER");return n;}
std::string state(ManualProcedureGraph& t){return f(t.learnerView(),"state").string();}
const std::map<std::string,int> tuning{{"E",40},{"A",45},{"D",50},{"G",55},{"B",59},{"e",64}};
const std::map<std::string,int> pitch{{"C",0},{"C#",1},{"Db",1},{"D",2},{"D#",3},{"Eb",3},{"E",4},{"E#",5},{"F",5},{"F#",6},{"G",7},{"G#",8},{"A",9},{"A#",10},{"Bb",10},{"B",11},{"B#",0}};
V schemaFixture(const V& schema) {
    if(const auto* c=schema.find("const"))return *c;if(const auto* e=schema.find("enum"))return e->array().front();
    const auto& types=f(schema,"type");const auto kind=types.isString()?types.string():types.array().front().string();
    if(kind=="object") {O p;for(const auto& field:f(schema,"properties").object())p.emplace(field.first,schemaFixture(field.second));return p;}
    if(kind=="array") {A a;for(std::int64_t i=0;i<num(f(schema,"minItems"));++i)a.push_back(schemaFixture(f(schema,"items")));return a;}
    if(kind=="boolean")return true;if(kind=="integer")return schema.find("minimum")?f(schema,"minimum"):V::fromInteger(0);
    return "Synthetic manual declaration; no actual performance observed.";
}
const V& step(ManualProcedureGraph& t) {return f(t.retainedDefinition().retainedProgram(),"steps").array()[static_cast<std::size_t>(num(f(t.learnerView(),"cursor")))];}
V contact(const std::string& s,int fret,const std::string& name) {return O{{"string",s},{"fret",V::fromInteger(fret)},{"named_pitch",name}};}
V positive(ManualProcedureGraph& t) {
    if(t.retainedDefinition().retainedProgram().find("graph"))return fathom::tests::manual_procedure_fixture::positiveFor(t);
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

void refused(ManualProcedureGraph& t,const std::function<void()>& call){const auto before=t.learnerView();const auto n=t.history().size();bool no=false;try{call();}catch(const tasks::recipes::Error&){no=true;}check(no,"EXPECTED_REFUSAL");check(before==t.learnerView()&&n==t.history().size(),"REFUSAL_MUTATED");++refusals;}
void action(ManualProcedureGraph& t,const std::string& a,const V& p){const auto token=t.capture(a);check(t.current(token));t.apply(token,p);check(!t.current(token));++actions;refused(t,[&]{t.apply(token,p);});check(!f(t.learnerView(),"observed_performance").boolean()&&!f(t.learnerView(),"grants_credit").boolean());}
void advance(ManualProcedureGraph& t){const auto a=t.learnerActions();const auto name=f(a.array().front(),"action").string();action(t,name,positive(t));}
void finish(ManualProcedureGraph& t){for(int i=0;state(t)!="completed"&&state(t)!="cancelled"&&i<200;++i){check(state(t)!="needs_retry","POSITIVE_DIAGNOSED");advance(t);}check(state(t)=="completed"||state(t)=="cancelled");++paths;}
std::vector<V> read(const char* path){std::ifstream in(path);check(in.good());std::vector<V> rows;std::string line;while(std::getline(in,line))rows.push_back(json::parse(line));return rows;}
}
int main(int argc,char** argv){try{check(argc==2);const auto rows=read(argv[1]);check(rows.size()==224&&keys().size()==224);std::set<std::string> programs;std::size_t legacy{},newRows{},stages{};for(const auto& row:rows){const auto key=f(row,"source_key").string();checkpoint=key;const auto& d=definition(key);check(d.exportedDefinition()==row,"EXACT_RAW_EXPORT");const auto& original=f(row,"original_record");const auto kind=f(f(original,"implementation"),"kind").string();const auto name=f(d.retainedProgram(),"name").string();programs.insert(name);stages+=d.retainedProgram().find("graph")?f(f(d.retainedProgram(),"graph"),"nodes").object().size():f(d.retainedProgram(),"steps").array().size();if(kind=="manual_curriculum_task"){check(C::definition(key).exportedDefinition()==row);check(C::definition(key).sourceClosureSha256()==d.sourceClosureSha256(),"OLD_CLOSURE_DRIFT");++legacy;}else ++newRows;ManualProcedureGraph t(d),other(d);const auto idle=t.capture("begin");const auto view=t.learnerView();check(t.fenceInactiveForNavigation()&&t.learnerView()==view&&t.history().empty());refused(t,[&]{t.apply(idle,O{{"original_workbook",true},{"own_instrument",true}});});refused(t,[&]{t.apply(other.capture("begin"),O{{"original_workbook",true},{"own_instrument",true}});});advance(t);finish(t);if(!d.retainedProgram().find("graph"))check(t.history().size()==f(d.retainedProgram(),"steps").array().size()+2);check(t.fenceInactiveForNavigation());}check(legacy==96&&newRows==128&&programs.size()==26&&stages==2253);
 // Every new program: a nonphysical unknown ends the pass. Diagnosis alone
 // cannot expose a later source stage; owned active-exit release precedes entry0.
 std::set<std::string> tested;for(const auto& row:rows){const auto& p=f(row,"program");if(!p.find("manual_response_failure_policy"))continue;const auto name=f(p,"name").string();if(!tested.insert(name).second)continue;checkpoint="terminal unknown "+name;ManualProcedureGraph t(definition(f(row,"source_key").string()));advance(t);auto report=positive(t);const auto& stage=step(t);const auto field=f(stage,"requires_known").array().front().string();report.object()[field]=nullptr;action(t,"submit",report);check(state(t)=="needs_retry"&&!f(t.learnerView(),"needs_manual_release").boolean());const auto failed=t.history();action(t,"retry",positive(t));check(state(t)=="await_release");refused(t,[&]{t.apply(t.capture("submit"),positive(t));});for(V bad:{V(false),V(nullptr)})refused(t,[&]{t.apply(t.capture("release"),O{{"learner_released",bad},{"external_source_stopped",true}});});advance(t);check(state(t)=="active"&&num(f(t.learnerView(),"cursor"))==0&&t.history().size()>failed.size());finish(t);
 // Physical unknown retains its exact failed source node through physical
 // release, then diagnosis + a distinct active-exit release before fresh entry.
 ManualProcedureGraph physical(t.retainedDefinition());advance(physical);for(int i=0;i<80&&!f(step(physical),"activates_release").boolean();++i)advance(physical);auto negative=positive(physical);for(const auto& known:f(step(physical),"requires_known").array()){const auto& schema=f(f(f(step(physical),"schema"),"properties"),known.string().c_str());if(const auto* type=schema.find("type");type&&type->isArray()&&std::find(type->array().begin(),type->array().end(),V("null"))!=type->array().end()){negative.object()[known.string()]=nullptr;break;}}action(physical,"submit",negative);check(state(physical)=="await_release");advance(physical);check(state(physical)=="needs_retry");auto diagnosis=positive(physical);action(physical,"retry",diagnosis);check(state(physical)=="await_release");advance(physical);check(state(physical)=="active"&&num(f(physical.learnerView(),"cursor"))==0);finish(physical);
 }check(tested.size()==3);
 // One causal unknown/release/restart recovery for each genuine graph program.
 std::set<std::string> graphPrograms;for(const auto& row:rows){const auto& p=f(row,"program");if(!p.find("graph")||!graphPrograms.insert(f(p,"name").string()).second)continue;checkpoint="graph recovery "+f(p,"name").string();ManualProcedureGraph t(definition(f(row,"source_key").string()));advance(t);
 for(int i=0;i<20;++i){const auto view=t.learnerView();const auto& n=f(f(f(p,"graph"),"nodes"),f(view,"node").string().c_str());if(n.find("physical")&&f(n,"physical").boolean())break;advance(t);}
 auto report=positive(t);report.object()["no_stop_condition"]=nullptr;action(t,"submit",report);check(state(t)=="await_release"&&f(t.learnerView(),"release_reason")==V("physical_attempt"));advance(t);check(state(t)=="needs_retry");action(t,"retry",positive(t));check(state(t)=="await_release"&&f(t.learnerView(),"release_reason")==V("active_exit"));advance(t);
 if(f(t.learnerView(),"node")==V("repair_choice")){advance(t);check(state(t)=="await_release");advance(t);}finish(t);
 }check(graphPrograms.size()==5);
 try{(void)definition("foreign");check(false,"FOREIGN_ACCEPTED");}catch(const tasks::recipes::Error&){++refusals;}std::cout<<"{\"outcome\":\"PASS\",\"rows\":224,\"legacy_preserved\":96,\"new_rows\":128,\"source_programs\":26,\"source_stages\":"<<stages<<",\"paths\":"<<paths<<",\"actions\":"<<actions<<",\"assertions\":"<<assertions<<",\"refusals\":"<<refusals<<",\"graph48_admitted\":48,\"credit\":false}\n";return 0;}catch(const std::exception& e){std::cerr<<checkpoint<<": "<<e.what()<<" actions="<<actions<<"\n";return 1;}}
