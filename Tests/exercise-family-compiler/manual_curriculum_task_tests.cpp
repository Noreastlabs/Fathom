#include "tasks/ManualCurriculumTask.hpp"
#include <algorithm>
#include <fstream>
#include <functional>
#include <iostream>
#include <set>
using namespace fathom;using namespace fathom::tasks::manual_curriculum;
namespace recipes=fathom::tasks::recipes;
using V=json::Value;using O=V::Object;using A=V::Array;
namespace {
std::size_t assertions{},refusals{},actions{},paths{};
std::string checkpoint;
void check(bool b,const char* why="CHECK") {++assertions;if(!b)throw std::runtime_error(why);}
const V& f(const V& v,const char* n) {const auto* p=v.find(n);check(p!=nullptr,"FIELD");return *p;}
std::int64_t num(const V& v) {std::int64_t n{};check(v.integer(n),"INTEGER");return n;}
std::string state(ManualCurriculumTask& t) {return f(t.learnerView(),"state").string();}
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
const V& step(ManualCurriculumTask& t) {return f(t.retainedDefinition().retainedProgram(),"steps").array()[static_cast<std::size_t>(num(f(t.learnerView(),"cursor")))];}
V contact(const std::string& s,int fret,const std::string& name) {return O{{"string",s},{"fret",V::fromInteger(fret)},{"named_pitch",name}};}
V positive(ManualCurriculumTask& t) {
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
void refused(ManualCurriculumTask& t,const std::function<void()>& call) {
    const auto before=t.learnerView();const auto h=t.history().size();const auto own=t.capture("submit");try {call();}catch(const recipes::Error&) {++refusals;check(t.learnerView()==before&&t.history().size()==h,"REFUSAL_MUTATED");const auto now=t.capture("submit");check(own.owner.instance==now.owner.instance&&own.owner.pass==now.owner.pass&&own.owner.revision==now.owner.revision,"REFUSAL_OWNER_MUTATED");return;}throw std::runtime_error("EXPECTED_REFUSAL");
}
void doAction(ManualCurriculumTask& t,const std::string& a,const V& p) {const auto token=t.capture(a);t.apply(token,p);++actions;check(!f(t.learnerView(),"observed_performance").boolean()&&!f(t.learnerView(),"grants_credit").boolean()&&!f(t.learnerView(),"automatic_mastery").boolean());refused(t,[&]{t.apply(token,p);});}
void advance(ManualCurriculumTask& t,bool mutants=false) {
    const auto descriptors=t.learnerActions();check(descriptors.isArray()&&!descriptors.array().empty());const auto a=f(descriptors.array().front(),"action").string();auto p=positive(t);validateInputSchema(f(descriptors.array().front(),"schema"),p);
    if(mutants) {
        const auto original=t.capture(a);
        for(int i=0;i<10;++i) {auto token=original;switch(i){case 0:++token.owner.instance;break;case 1:++token.owner.pass;break;case 2:++token.owner.revision;break;case 3:token.owner.sourceKey="foreign";break;case 4:token.owner.contractSha256=std::string(64,'0');break;case 5:token.owner.sourceClosureSha256=std::string(64,'0');break;case 6:token.owner.step=99;break;case 7:token.cursor+=1;break;case 8:token.state="foreign";break;case 9:token.action=a=="finish"?"submit":"finish";break;}refused(t,[&]{t.apply(token,p);});}
        auto missing=p;if(!p.object().empty()){missing.object().erase(missing.object().begin());refused(t,[&]{t.apply(original,missing);});}
        auto extra=p;extra.object()["foreign_field"]=true;refused(t,[&]{t.apply(original,extra);});
    }
    doAction(t,a,p);
}
void finish(ManualCurriculumTask& t,bool mutants=false) {for(int i=0;state(t)!="completed"&&i<300;++i) {check(state(t)!="needs_retry","UNEXPECTED_DIAGNOSIS");advance(t,mutants);}check(state(t)=="completed","UNFINISHED");}
void begin(ManualCurriculumTask& t) {advance(t);check(state(t)=="active");}
void releaseRecovery(ManualCurriculumTask& t) {
    if(f(t.learnerView(),"needs_manual_release").boolean()) {
        const auto tok=t.capture("release");for(V bad:{V(false),V(nullptr)})refused(t,[&]{t.apply(tok,O{{"learner_released",bad},{"external_source_stopped",true}});});
        refused(t,[&]{t.apply(t.capture("retry"),O{{"diagnosis","Synthetic premature retry."}});});advance(t);
    }
    check(state(t)=="needs_retry");refused(t,[&]{t.apply(t.capture("finish"),O{});});advance(t);check(state(t)=="active");
}
std::vector<V> read(const char* p) {std::ifstream in(p);check(in.good());std::vector<V> out;std::string line;while(std::getline(in,line))out.push_back(json::parse(line));return out;}
}
int main(int argc,char** argv) {try {
    check(argc==2,"ARGS definitions.jsonl");const auto rows=read(argv[1]);check(rows.size()==96&&keys().size()==96);std::set<std::string> programs;
    for(const auto& row:rows) {
        const auto key=f(row,"source_key").string();checkpoint="positive "+key;const auto& d=definition(key);check(d.exportedDefinition()==row,"EXACT_NATIVE_ROUNDTRIP");check(!d.retainedSourceContext().null());programs.emplace(f(d.retainedProgram(),"name").string());
        ManualCurriculumTask t(d);const auto idle=t.capture("begin");const auto initial=t.learnerView();check(t.fenceInactiveForNavigation()&&t.learnerView()==initial&&t.history().empty());refused(t,[&]{t.apply(idle,O{{"original_workbook",true},{"own_instrument",true}});});
        check(!t.learnerView().find("printed_self_check")&&!t.learnerView().find("original_record")&&!t.learnerInstructions().find("source_context")&&!t.learnerInstructions().find("contract"));
        begin(t);const auto active=t.learnerView();check(!t.fenceInactiveForNavigation()&&t.learnerView()==active);
        finish(t,true);check(t.history().size()==f(d.retainedProgram(),"steps").array().size()+2,"COMPLETE_SOURCE_STEP_COUNT");
        const auto complete=t.learnerView();const auto h=t.history().size();check(t.fenceInactiveForNavigation()&&t.learnerView()==complete&&t.history().size()==h);check(t.learnerActions().array().empty());++paths;
    }
    check(programs.size()==18);try{(void)definition("foreign");throw std::runtime_error("FOREIGN_SCOPE");}catch(const recipes::Error&){++refusals;}
    // Every genuine source program gets a nullable/negative causal report,
    // release if physical, diagnosed retry, and full reachable completion.
    for(const auto& name:programs) {
        checkpoint="unknown "+name;const auto row=std::find_if(rows.begin(),rows.end(),[&](const V& r){return f(f(r,"program"),"name").string()==name;});ManualCurriculumTask t(definition(f(*row,"source_key").string()));begin(t);
        bool tested=false;for(int j=0;j<150&&!tested;++j) {
            auto p=positive(t);const auto& s=step(t);const auto& props=f(f(s,"schema"),"properties");
            for(const auto& field:f(s,"requires_known").array()) {const auto n=field.string();const auto& schema=f(props,n.c_str());const auto* types=schema.find("type");if(types&&types->isArray()&&std::find(types->array().begin(),types->array().end(),V("null"))!=types->array().end()) {p.object()[n]=nullptr;doAction(t,f(s,"action").string(),p);check(state(t)=="needs_retry"||state(t)=="await_release");releaseRecovery(t);tested=true;break;}}
            if(!tested)advance(t);
        }
        check(tested,"MISSING_NULLABLE_PROGRAM_PATH");finish(t);++paths;
    }
    // Written answers must stay hidden until response and explicit reveal;
    // wrong committed answers diagnose after reveal, and retry preserves exposure.
    for(int level:{55,56}) {
        const auto row=std::find_if(rows.begin(),rows.end(),[&](const V& r){return f(f(r,"program"),"name").string()==("l0"+std::to_string(level)+"_written_analysis");});ManualCurriculumTask t(definition(f(*row,"source_key").string()));begin(t);refused(t,[&]{t.apply(t.capture("reveal"),O{{"reveal_requested",true}});});
        auto response=positive(t);response.object()["key"]="Wrong manual key";doAction(t,"submit",response);check(!t.learnerView().find("printed_self_check"));advance(t);check(t.learnerView().find("printed_self_check")!=nullptr);advance(t);check(state(t)=="needs_retry");advance(t);check(f(t.learnerView(),"self_check_exposed_in_history").boolean()&&!f(t.learnerView(),"self_check_visible").boolean());finish(t);++paths;
    }
    // Mandatory release survives cancel/navigation; false/null releases retain
    // cursor, complete history and owner revision across repeated refusal.
    const auto first=std::find_if(rows.begin(),rows.end(),[](const V& r){return f(f(r,"program"),"name").string()=="l054_root_form_command";});ManualCurriculumTask nav(definition(f(*first,"source_key").string()));begin(nav);advance(nav);const auto old=nav.capture("submit");doAction(nav,"navigate",O{});check(f(nav.learnerView(),"needs_manual_release").boolean());refused(nav,[&]{nav.apply(nav.capture("reopen"),O{});});for(int i=0;i<3;++i)refused(nav,[&]{nav.apply(nav.capture("release"),O{{"learner_released",false},{"external_source_stopped",true}});});advance(nav);check(state(nav)=="cancelled");const auto cancelled=nav.learnerView();const auto nh=nav.history().size();check(nav.fenceInactiveForNavigation()&&nav.learnerView()==cancelled&&nav.history().size()==nh);advance(nav);refused(nav,[&]{nav.apply(old,O{});});finish(nav);++paths;
    // Source-specific integrity: root contacts complete, partial/triad only
    // inside the chosen form, pitch roles correct, and inversion declared.
    ManualCurriculumTask form(definition(f(*first,"source_key").string()));begin(form);advance(form);auto calc=positive(form);calc.object()["root_contacts"].array().pop_back();doAction(form,"submit",calc);releaseRecovery(form);advance(form);advance(form);advance(form);auto partial=positive(form);partial.object()["contacts"].array()[0].object()["fret"]=V::fromInteger(24);doAction(form,"submit",partial);releaseRecovery(form);finish(form);++paths;
    // Printed audit dates/thresholds remain actual manual fields, not one
    // completion checkbox. Same dates and below30 counts diagnose and recover.
    for(const auto* program:{"l054_progression_mastery_audit","l055_progression_mastery_audit"}) {
        const auto row=std::find_if(rows.begin(),rows.end(),[&](const V& r){return f(f(r,"program"),"name").string()==program;});ManualCurriculumTask t(definition(f(*row,"source_key").string()));begin(t);bool tested=false;
        for(int i=0;i<30&&!tested;++i) {auto p=positive(t);if(p.find("first_attempt_successes")){p.object()["first_attempt_successes"]=V::fromInteger(29);tested=true;}else if(p.find("date_1")){p.object()["date_2"]=f(p,"date_1");tested=true;}if(tested){doAction(t,"submit",p);releaseRecovery(t);}else advance(t);}check(tested);finish(t);++paths;
    }
    // Mechanics stop-condition reports end the current set through owned
    // release; retry requires explicit resolved-condition report and new set.
    const auto mechanics=std::find_if(rows.begin(),rows.end(),[](const V& r){return f(f(r,"program"),"name").string()=="l063_technique_mechanics";});ManualCurriculumTask stop(definition(f(*mechanics,"source_key").string()));begin(stop);advance(stop);auto p=positive(stop);p.object()["no_stop_condition"]=false;doAction(stop,"submit",p);check(state(stop)=="await_release");advance(stop);check(state(stop)=="needs_retry");refused(stop,[&]{stop.apply(stop.capture("retry"),O{{"diagnosis","Synthetic stop condition; unresolved."},{"stop_condition_resolved",false}});});advance(stop);check(num(f(stop.learnerView(),"cursor"))==0);finish(stop);++paths;
    // Unknown tempo is retained without inventing a BPM; no fabricated clock
    // or observation blocks a source-supported relative/manual hearing loop.
    const auto ear=std::find_if(rows.begin(),rows.end(),[](const V& r){return f(f(r,"program"),"name").string()=="l055_functional_hearing";});ManualCurriculumTask tempo(definition(f(*ear,"source_key").string()));begin(tempo);auto e=positive(tempo);e.object()["bpm"]=nullptr;doAction(tempo,"submit",e);check(state(tempo)=="active"&&f(f(f(tempo.learnerView(),"learner_responses"),"ear_key"),"bpm").null());finish(tempo);++paths;
    std::size_t sourceSteps{};for(const auto& row:rows)sourceSteps+=f(f(row,"program"),"steps").array().size();std::cout<<"{\"outcome\":\"PASS\",\"exact_rows\":96,\"source_programs\":18,\"source_steps\":"<<sourceSteps<<",\"paths\":"<<paths<<",\"actions\":"<<actions<<",\"assertions\":"<<assertions<<",\"refusals\":"<<refusals<<",\"synthetic_only\":true,\"actual_performance_observed\":false,\"runtime_acceptance_increment\":0}\n";return 0;
} catch(const std::exception& e){std::cerr<<checkpoint<<": "<<e.what()<<" actions="<<actions<<" paths="<<paths<<"\n";return 1;} }
