#include "tasks/ManualCurriculumTask.hpp"
#include "GeneratedManualCurriculumFamily.hpp"
#include <algorithm>
#include <atomic>
#include <limits>
#include <map>
#include <regex>
#include <set>

namespace fathom::tasks::manual_curriculum {
namespace {
using V=json::Value;using O=V::Object;using A=V::Array;
void need(bool ok,const char* code) { if(!ok) throw recipes::Error(code); }
const V& f(const V& v,const char* name) { const auto* p=v.find(name);need(p!=nullptr,"FIELDS");return *p; }
std::string str(const V& v,const char* name) { const auto& p=f(v,name);need(p.isString(),"STRING_TYPE");return p.string(); }
std::int64_t num(const V& v) { std::int64_t n{};need(v.integer(n),"INTEGER_TYPE");return n; }
bool flag(const V& v,const char* name) { const auto& p=f(v,name);need(p.isBool(),"BOOLEAN_TYPE");return p.boolean(); }
bool hash(const std::string& s) { return s.size()==64 && std::all_of(s.begin(),s.end(),[](char c){return(c>='a'&&c<='f')||(c>='0'&&c<='9');}); }
bool nonblank(const std::string& s) { return std::any_of(s.begin(),s.end(),[](unsigned char c){return c>32;}); }
bool type(const V& v,const std::string& t) {
    if(t=="null")return v.null();if(t=="boolean")return v.isBool();if(t=="string")return v.isString();
    if(t=="object")return v.isObject();if(t=="array")return v.isArray();std::int64_t n{};return t=="integer"&&v.integer(n);
}
std::uint64_t instance() {
    static std::atomic<std::uint64_t> n{1};auto v=n.load();
    do {need(v!=std::numeric_limits<std::uint64_t>::max(),"INSTANCE_EXHAUSTED");} while(!n.compare_exchange_weak(v,v+1));return v;
}
const std::map<std::string,std::size_t> actions{{"begin",0},{"submit",1},{"release",2},{"reveal",3},{"compare",4},{"retry",5},{"cancel",6},{"navigate",7},{"stop",8},{"reopen",9},{"finish",10}};
recipes::Intent intent(const std::string& a) {
    if(a=="begin")return recipes::Intent::Choose;if(a=="release")return recipes::Intent::Release;if(a=="retry")return recipes::Intent::Retry;
    if(a=="cancel"||a=="stop")return recipes::Intent::Stop;if(a=="navigate")return recipes::Intent::Navigate;if(a=="reopen")return recipes::Intent::Reopen;return recipes::Intent::Report;
}
V boolSchema() {return O{{"type",A{"boolean","null"}},{"input_role","manual_report"}};}
V textSchema() {return O{{"type",A{"string","null"}},{"minLength",V::fromInteger(1)},{"maxLength",V::fromInteger(2000)},{"input_role","manual_report"}};}
V objectSchema(O properties) {A names;for(const auto& e:properties)names.emplace_back(e.first);return O{{"type","object"},{"properties",properties},{"required",names},{"additionalProperties",false}};}
V releaseSchema() {return objectSchema({{"learner_released",boolSchema()},{"external_source_stopped",boolSchema()}});}
int pc(const V& n) {
    if(!n.isString())return -1;static const auto p=json::parse(manual_curriculum_generated::pitchClassesJson);const auto* value=p.find(n.string());return value?static_cast<int>(num(*value)):-1;
}
int open(const std::string& s) {static const auto t=json::parse(manual_curriculum_generated::tuningJson);const auto* v=t.find(s);need(v!=nullptr,"STRING_NAME");return static_cast<int>(num(*v));}
std::string position(const V& c) {return str(c,"string")+":"+std::to_string(num(f(c,"fret")));}
bool contactNamed(const V& c) {const auto& fret=f(c,"fret");return !fret.null() && pc(f(c,"named_pitch"))==(open(str(c,"string"))+num(fret))%12;}
bool validDate(const V& v) {
    if(!v.isString()||!std::regex_match(v.string(),std::regex("[0-9]{4}-[0-9]{2}-[0-9]{2}")))return false;
    const int y=std::stoi(v.string().substr(0,4)),m=std::stoi(v.string().substr(5,2)),d=std::stoi(v.string().substr(8,2));
    static const int days[]={0,31,28,31,30,31,30,31,31,30,31,30,31};if(y<1||m<1||m>12)return false;
    return d>=1&&d<=days[m]+(m==2&&(y%400==0||(y%4==0&&y%100!=0)));
}
bool constraint(const V& c,const V& p,const O& saved,const V& program) {
    const auto kind=str(c,"kind");
    if(kind=="minimum") {const auto& x=f(p,str(c,"field").c_str());return !x.null()&&num(x)>=num(f(c,"value"));}
    if(kind=="equal"||kind=="different"||kind=="distinct_dates") {
        const auto& fields=f(c,"fields").array();const auto& a=f(p,fields[0].string().c_str());const auto& b=f(p,fields[1].string().c_str());
        if(kind=="distinct_dates")return validDate(a)&&validDate(b)&&a!=b;return kind=="equal"?a==b:a!=b;
    }
    if(kind=="written_comparison") {const auto it=saved.find("written_response");return it!=saved.end()&&it->second==f(program,"hidden_self_check");}
    if(kind=="caged_formula") {
        const auto it=saved.find("root_region");if(it==saved.end())return false;const auto& r=f(it->second,"root_fret");if(r.null())return false;
        const auto& frets=f(p,"frets").array();const auto& offsets=f(c,"offsets").array();std::set<std::string> expected,actual;
        static const char* strings[]={"E","A","D","G","B","e"};
        for(std::size_t i=0;i<6;++i) {
            const auto value=offsets[i].null()?V(nullptr):V::fromInteger(num(r)+num(offsets[i]));if(frets[i]!=value)return false;
            if(!value.null()&&(open(strings[i])+num(value))%12==pc(f(c,"root")))expected.emplace(std::string(strings[i])+":"+std::to_string(num(value)));
        }
        for(const auto& x:f(p,"root_contacts").array()) {if(!contactNamed(x)||pc(f(x,"named_pitch"))!=pc(f(c,"root"))||!actual.emplace(position(x)).second)return false;}
        return expected==actual;
    }
    if(kind=="caged_subset") {
        const auto it=saved.find("form");if(it==saved.end())return false;const auto& frets=f(it->second,"frets").array();static const std::vector<std::string> strings{"E","A","D","G","B","e"};std::set<std::string> contacts;std::set<int> pitches;int bass=1000;
        for(const auto& x:f(p,"contacts").array()) {
            const auto found=std::find(strings.begin(),strings.end(),str(x,"string"));if(found==strings.end()||f(x,"fret").null()||!contactNamed(x)||!contacts.emplace(position(x)).second)return false;
            if(frets[static_cast<std::size_t>(found-strings.begin())]!=f(x,"fret"))return false;const int midi=open(str(x,"string"))+static_cast<int>(num(f(x,"fret")));pitches.emplace(midi%12);bass=std::min(bass,midi);
        }
        if(num(f(c,"minimum"))==3) {
            const int root=pc(f(f(program,"source_facts"),"root"));if(pitches!=std::set<int>{root,(root+4)%12,(root+7)%12})return false;
            const auto inv=str(p,"inversion");const int offset=inv=="root"?0:inv=="first"?4:7;const auto& degree=f(p,"lowest_degree");
            return bass%12==(root+offset)%12&&degree.isString()&&degree.string()==(inv=="root"?"1":inv=="first"?"3":"5");
        }
        return true;
    }
    if(kind=="triad_names") {
        const auto& r=f(p,"bass_fret");if(r.null())return false;const auto& names=f(p,"named_notes").array();const auto& strings=f(c,"strings").array();const auto& offsets=f(c,"offsets").array();std::set<int> actual,expected;
        for(const auto& n:f(c,"allowed_notes").array())expected.emplace(pc(n));
        for(std::size_t i=0;i<3;++i) {const int n=pc(names[i]);if(n<0||n!=(open(strings[i].string())+num(r)+num(offsets[i]))%12)return false;actual.emplace(n);}
        return actual==expected;
    }
    throw recipes::Error("SOURCE_CONSTRAINT_KIND");
}
} // namespace

void validateInputSchema(const V& schema,const V& input) {
    need(schema.isObject()&&!schema.find("default"),"INPUT_SCHEMA");
    if(const auto* literal=schema.find("const")) {need(input==*literal,"SOURCE_PROTOCOL_BINDING");return;}
    const auto& kinds=f(schema,"type");bool typed=false;if(kinds.isString())typed=type(input,kinds.string());else {need(kinds.isArray(),"SCHEMA_TYPE");for(const auto& kind:kinds.array())typed=typed||type(input,kind.string());}need(typed,"INPUT_TYPE");
    if(const auto* values=schema.find("enum"))need(std::find(values->array().begin(),values->array().end(),input)!=values->array().end(),"INPUT_CHOICE_RANGE");
    if(input.null())return;
    if(input.isObject()) {
        const auto& props=f(schema,"properties");need(!flag(schema,"additionalProperties")&&input.object().size()==props.object().size()&&f(schema,"required").array().size()==props.object().size(),"EXACT_INPUT_FIELDS");
        for(const auto& prop:props.object())validateInputSchema(prop.second,f(input,prop.first.c_str()));
    }
    if(input.isArray()) {need(input.array().size()>=static_cast<std::size_t>(num(f(schema,"minItems")))&&input.array().size()<=static_cast<std::size_t>(num(f(schema,"maxItems"))),"ARRAY_RANGE");for(const auto& item:input.array())validateInputSchema(f(schema,"items"),item);}
    if(input.isString()) {need(nonblank(input.string()),"REPORTED_TEXT_RANGE");if(const auto* lo=schema.find("minLength"))need(input.string().size()>=static_cast<std::size_t>(num(*lo)),"REPORTED_TEXT_RANGE");if(const auto* hi=schema.find("maxLength"))need(input.string().size()<=static_cast<std::size_t>(num(*hi)),"REPORTED_TEXT_RANGE");}
    if(input.isNumber()) {const auto n=num(input);if(const auto* lo=schema.find("minimum"))need(n>=num(*lo),"INTEGER_RANGE");if(const auto* hi=schema.find("maximum"))need(n<=num(*hi),"INTEGER_RANGE");}
}

Definition::Definition(const char* row):exported_(json::parse(row)) {
    need(str(exported_,"schema")=="fathom.compiled-manual-curriculum-definition.1","DEFINITION_SCHEMA");key_=str(exported_,"source_key");identity_=str(exported_,"source_identity");contractSha_=str(exported_,"contract_sha256");closureSha_=manual_curriculum_generated::closureSha256;program_=f(exported_,"program");
    const auto& original=f(exported_,"original_record");need(str(original,"package_key")==key_&&str(original,"source_identity")==identity_&&str(f(original,"implementation"),"kind")=="manual_curriculum_task"&&!flag(f(original,"implementation"),"automated_assessment"),"EXACT_ORIGINAL_BINDING");
    need(hash(contractSha_)&&hash(closureSha_)&&hash(str(exported_,"original_row_sha256"))&&hash(str(exported_,"original_compact_sha256"))&&f(program_,"fixed_bpm").null()&&!flag(program_,"performance_observed")&&!flag(program_,"grants_credit")&&!flag(program_,"automatic_mastery"),"SOURCE_BOUNDARY");
    const auto path=str(exported_,"context_ref");bool found=false;for(const auto& c:manual_curriculum_generated::contexts)if(path==c.path){need(!found,"DUPLICATE_CONTEXT");context_=json::parse(c.value);found=true;}need(found,"MISSING_CONTEXT");
    need(!f(program_,"steps").array().empty(),"PROCEDURE_STEPS");for(const auto& s:f(program_,"steps").array())need(actions.count(str(s,"action"))&&!flag(f(s,"schema"),"additionalProperties")&&f(s,"expected").isObject(),"PROCEDURE_SCHEMA");
}
V Definition::sourcePlayerView() const {return O{{"source_key",key_},{"source_facts",f(program_,"source_facts")},{"hidden_self_check",f(program_,"hidden_self_check")},{"trusted_source_context_only",true},{"performance_observed",false},{"grants_credit",false}};}
const Definition& definition(const std::string& key) {
    static const std::map<std::string,Definition> all=[] {std::map<std::string,Definition> result;for(const auto& row:manual_curriculum_generated::rows){Definition d(row.value);need(d.sourceKey()==row.key&&result.emplace(row.key,d).second,"CLOSED_SOURCE_KEY");}need(result.size()==96,"CLOSED_NINETY_SIX");return result;}();const auto it=all.find(key);need(it!=all.end(),"EXACT_MANUAL_CURRICULUM_SCOPE");return it->second;
}
const std::vector<std::string>& keys() {static const auto result=[] {std::vector<std::string> out;for(const auto& r:manual_curriculum_generated::rows){(void)definition(r.key);out.emplace_back(r.key);}return out;}();return result;}
ManualCurriculumTask::ManualCurriculumTask(const Definition& d):definition_(d),instance_(instance()) {}
Token ManualCurriculumTask::captureImpl(const std::string& action) const {
    const auto it=actions.find(action);need(it!=actions.end(),"ACTION_KIND");const auto phase=state_.releaseDebt?recipes::Phase::Release:state_.phase=="select"?recipes::Phase::Select:(state_.phase=="completed"||state_.phase=="cancelled")?recipes::Phase::Closed:recipes::Phase::Steps;
    return {{instance_,state_.pass,state_.revision,definition_.sourceKey(),definition_.contractSha256(),definition_.sourceClosureSha256(),phase,it->second,intent(action)},action,state_.phase,state_.cursor};
}
Token ManualCurriculumTask::capture(const std::string& action) const {std::lock_guard<std::mutex> lock(mutex_);return captureImpl(action);}
V ManualCurriculumTask::viewImpl() const {
    O v{{"source_key",definition_.sourceKey()},{"program",f(definition_.retainedProgram(),"name")},{"state",state_.phase},{"cursor",V::fromInteger(static_cast<std::int64_t>(state_.cursor))},{"step_count",V::fromInteger(static_cast<std::int64_t>(f(definition_.retainedProgram(),"steps").array().size()))},{"needs_manual_release",state_.releaseDebt},{"self_check_visible",state_.selfCheckVisible},{"self_check_exposed_in_history",state_.revealedEver},{"diagnosis",state_.diagnosis},{"learner_responses",state_.saved},{"source_clock",nullptr},{"fixed_bpm",nullptr},{"observed_performance",false},{"grants_credit",false},{"automatic_mastery",false},{"user_reported_procedure_finished",state_.phase=="completed"}};
    if(state_.selfCheckVisible)v.emplace("printed_self_check",f(definition_.retainedProgram(),"hidden_self_check"));return v;
}
V ManualCurriculumTask::learnerView() const {std::lock_guard<std::mutex> lock(mutex_);return viewImpl();}
V ManualCurriculumTask::learnerInstructions() const {
    std::lock_guard<std::mutex> lock(mutex_);A text=f(definition_.retainedProgram(),"learner_instruction_context").array();text.emplace_back("Complete each source-specific action with your own report. Unknown or negative reports require diagnosis and retry. Manual reports do not establish heard/played performance, mastery, admission or credit.");
    if(state_.phase=="active"&&state_.cursor<f(definition_.retainedProgram(),"steps").array().size())text.push_back(f(f(definition_.retainedProgram(),"steps").array()[state_.cursor],"instruction"));
    if(state_.releaseDebt)text.emplace_back("Manually release and stop/mute the source before retry, navigation or completion.");
    return O{{"text",text},{"source_clock",nullptr},{"fixed_bpm",nullptr},{"actual_performance_verified",false}};
}
V ManualCurriculumTask::actionsImpl() const {
    A result;auto add=[&](const char* action,const V& schema){result.emplace_back(O{{"action",action},{"schema",schema},{"fresh_native_token_required",true}});};
    if(state_.releaseDebt) {add("release",releaseSchema());return result;}
    if(state_.phase=="select")add("begin",objectSchema({{"original_workbook",boolSchema()},{"own_instrument",boolSchema()}}));
    else if(state_.phase=="cancelled")add("reopen",objectSchema({}));
    else if(state_.phase=="completed")return result;
    else if(state_.phase=="needs_retry") {
        O fields{{"diagnosis",textSchema()}};if(state_.diagnosis.find("stop_condition")&&flag(state_.diagnosis,"stop_condition"))fields.emplace("stop_condition_resolved",boolSchema());add("retry",objectSchema(fields));
    } else if(state_.cursor==f(definition_.retainedProgram(),"steps").array().size())add("finish",objectSchema({}));
    else {const auto& s=f(definition_.retainedProgram(),"steps").array()[state_.cursor];const auto action=str(s,"action");add(action.c_str(),f(s,"schema"));}
    if(state_.phase!="select"&&state_.phase!="cancelled")for(const auto* a:{"cancel","navigate","stop"})add(a,objectSchema({}));return result;
}
V ManualCurriculumTask::learnerActions() const {std::lock_guard<std::mutex> lock(mutex_);return actionsImpl();}
void ManualCurriculumTask::apply(const Token& t,const V& payload) {
    std::lock_guard<std::mutex> lock(mutex_);const auto current=captureImpl(t.action);recipes::requireCurrentToken(t.owner,current.owner);need(t.state==current.state&&t.cursor==current.cursor&&t.action==current.action,"EXACT_ACTION_CURSOR_STATE");(void)json::parse(json::stringify(payload));
    const V* schema=nullptr;const auto available=actionsImpl();for(const auto& a:available.array())if(str(a,"action")==t.action)schema=&f(a,"schema");need(schema!=nullptr,"ACTION_NOT_CURRENT");validateInputSchema(*schema,payload);
    const auto before=viewImpl();State next=state_;need(next.revision!=std::numeric_limits<std::uint64_t>::max(),"REVISION_EXHAUSTED");
    auto positiveBool=[&](const char* n){const auto& v=f(payload,n);need(v.isBool()&&v.boolean(),"MANUAL_RELEASE_OR_PREREQUISITE_REQUIRED");};
    if(t.action=="begin") {positiveBool("original_workbook");const auto& stages=f(definition_.retainedProgram(),"steps").array();if(std::any_of(stages.begin(),stages.end(),[](const V& s){return flag(s,"activates_release");}))positiveBool("own_instrument");next.phase="active";}
    else if(t.action=="release") {
        positiveBool("learner_released");positiveBool("external_source_stopped");
        if(state_.releaseDebt) {next.releaseDebt=false;next.phase=next.afterRelease;next.afterRelease.clear();}
        else {need(str(f(definition_.retainedProgram(),"steps").array()[next.cursor],"action")=="release","SOURCE_RELEASE_STEP");++next.cursor;}
        // A physical source stage already advances its cursor to the mandatory
        // release stage. A successful owned release discharges that exact step.
        if(state_.releaseDebt&&next.phase=="active"&&next.cursor<f(definition_.retainedProgram(),"steps").array().size()&&str(f(definition_.retainedProgram(),"steps").array()[next.cursor],"action")=="release")++next.cursor;
    } else if(t.action=="cancel"||t.action=="navigate"||t.action=="stop") {next.releaseDebt=true;next.afterRelease="cancelled";next.phase="await_release";}
    else if(t.action=="reopen") {need(next.pass!=std::numeric_limits<std::uint64_t>::max(),"PASS_EXHAUSTED");++next.pass;next.phase="select";next.cursor=0;next.saved.clear();next.selfCheckVisible=false;next.diagnosis=nullptr;}
    else if(t.action=="retry") {
        need(f(payload,"diagnosis").isString()&&nonblank(str(payload,"diagnosis")),"DIAGNOSIS_REQUIRED");if(payload.find("stop_condition_resolved"))positiveBool("stop_condition_resolved");
        need(next.pass!=std::numeric_limits<std::uint64_t>::max(),"PASS_EXHAUSTED");++next.pass;next.cursor=next.retryTarget;next.phase="active";next.diagnosis=nullptr;
        if(next.cursor==0){next.saved.clear();next.selfCheckVisible=false;}
    } else if(t.action=="finish") {need(!next.releaseDebt,"RELEASE_DEBT");next.phase="completed";}
    else {
        const auto& s=f(definition_.retainedProgram(),"steps").array()[state_.cursor];bool good=true;A failures;
        for(const auto& name:f(s,"requires_known").array())if(f(payload,name.string().c_str()).null()){good=false;failures.push_back(name);}
        O booleanActual,booleanExpected;
        for(const auto& entry:f(s,"expected").object()) {const auto& actual=f(payload,entry.first.c_str());if(entry.second.isBool()&&actual.isBool()){booleanActual.emplace(entry.first,actual);booleanExpected.emplace(entry.first,entry.second);}else if(actual!=entry.second){good=false;failures.emplace_back(entry.first);}}
        for(const auto& negative:recipes::validateManualReport(booleanActual,booleanExpected)){good=false;failures.emplace_back(negative);}
        for(const auto& c:f(s,"constraints").array())if(!constraint(c,payload,next.saved,definition_.retainedProgram())){good=false;failures.emplace_back(str(c,"kind"));}
        const auto& save=f(s,"save_as");if(!save.null())next.saved[save.string()]=payload;
        if(!good) {
            const bool stopped=payload.find("no_stop_condition")&&f(payload,"no_stop_condition")!=V(true);
            next.retryTarget=t.action=="compare"||stopped?0:next.cursor;next.diagnosis=O{{"reported_fields",failures},{"reported",payload},{"stop_condition",stopped},{"observed_failure",false}};
            if(flag(s,"activates_release")) {next.releaseDebt=true;next.afterRelease="needs_retry";next.phase="await_release";}else next.phase="needs_retry";
        } else {
            if(t.action=="reveal") {next.selfCheckVisible=true;next.revealedEver=true;}
            ++next.cursor;if(flag(s,"activates_release")){next.releaseDebt=true;next.afterRelease="active";next.phase="await_release";}
        }
    }
    ++next.revision;state_=std::move(next);history_.emplace_back(O{{"action",t.action},{"reported",payload},{"before",before},{"after",viewImpl()},{"pass",V::fromInteger(static_cast<std::int64_t>(t.owner.pass))},{"revision",V::fromInteger(static_cast<std::int64_t>(t.owner.revision))},{"observed_performance",false},{"grants_credit",false}});
}
std::vector<V> ManualCurriculumTask::history() const {std::lock_guard<std::mutex> lock(mutex_);return history_;}
bool ManualCurriculumTask::fenceInactiveForNavigation() {
    std::lock_guard<std::mutex> lock(mutex_);if(state_.releaseDebt||(state_.phase!="select"&&state_.phase!="completed"&&state_.phase!="cancelled"))return false;
    need(state_.pass!=std::numeric_limits<std::uint64_t>::max()&&state_.revision!=std::numeric_limits<std::uint64_t>::max(),"OWNER_COUNTER_EXHAUSTED");++state_.pass;++state_.revision;return true;
}
} // namespace fathom::tasks::manual_curriculum
