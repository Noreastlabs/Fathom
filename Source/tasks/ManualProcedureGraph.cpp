#include "tasks/L97ListeningSixControls.hpp"
#include "tasks/ManualProcedureGraph.hpp"
#include <type_traits>
#include <chrono>
#include "tasks/ManualProcedureProtocolSupport.hpp"
#include "tasks/ManualProcedureAdvancedReports.hpp"
#include "tasks/ManualProcedureSourceContracts.hpp"
#include "tasks/ManualProcedureSourcePolicies.hpp"
#include "tasks/ManualProcedureCapstoneReports.hpp"
#include "tasks/ManualProcedureLearnerSchemas.hpp"
#include "tasks/C1661SourceOperators.hpp"
#include "tasks/C1661HiddenSourceSeven.hpp"
#include "tasks/BoundSourceUnits.hpp"
#include "tasks/HarmonizedTriadControls.hpp"
#include "tasks/Level68SourceControls.hpp"
#include "tasks/BeginnerSourceControls.hpp"
#include "tasks/SeventhFamilyControls.hpp"
#include "tasks/RhythmGridControls.hpp"
#include "tasks/SourcePhraseControls.hpp"
#include "tasks/DiagonalRouteControls.hpp"
#include "tasks/AnticipationGridControls.hpp"
#include "tasks/ProgressionCircleControls.hpp"
#include "tasks/AnticipationLadderControls.hpp"
#include "tasks/TimedChordChangeControls.hpp"
#include "tasks/CompiledChordSessionControls.hpp"
#include "tasks/WholeChordFormControls.hpp"
#include "tasks/PracticalTriadControls.hpp"
#include "tasks/MelodicFunctionControls.hpp"
#include "tasks/SourceMapControls.hpp"
#include "tasks/PhraseApplicationControls.hpp"
#include "tasks/IntervalRecoveryControls.hpp"
#include "tasks/SourceTaskControls.hpp"
#include "tasks/QualifiedSourceControls.hpp"
#include "tasks/DimContextControls.hpp"
#include "tasks/RootlessSeventhControls.hpp"
#include "tasks/TimedAssessmentControls.hpp"
#include "tasks/SourceFormControls.hpp"
#include "content/Canonical.hpp"
#include <GeneratedManualProcedureGraph.hpp>
#include <GeneratedExtraSource17Definitions.hpp>
#include <algorithm>
#include <atomic>
#include <functional>
#include <limits>
#include <map>
#include <regex>
#include <set>

namespace fathom::tasks::manual_procedure_graph {
namespace {
using V=json::Value;using O=V::Object;using A=V::Array;
// Exact Python UTF8/sort_keys compact authority encoding. StrictJson's writer
// uses \u000a for LF; the retained source authority uses \n. Neither source
// object nor its hash is rewritten to hide that encoding distinction.
std::string extraSourceCanonical(const V& value) {
    if(value.isString()) {
        std::string out="\"";const char* hex="0123456789abcdef";
        for(unsigned char c:value.string()) {
            if(c=='"')out+="\\\"";else if(c=='\\')out+="\\\\";
            else if(c=='\n')out+="\\n";else if(c=='\r')out+="\\r";else if(c=='\t')out+="\\t";
            else if(c=='\b')out+="\\b";else if(c=='\f')out+="\\f";
            else if(c<32){out+="\\u00";out+=hex[c>>4];out+=hex[c&15];}else out+=static_cast<char>(c);
        }return out+'"';
    }
    if(value.isArray()){std::string out="[";bool first=true;for(const auto& child:value.array()){if(!first)out+=',';first=false;out+=extraSourceCanonical(child);}return out+"]";}
    if(value.isObject()){std::string out="{";bool first=true;for(const auto& child:value.object()){if(!first)out+=',';first=false;out+=extraSourceCanonical(V(child.first))+":"+extraSourceCanonical(child.second);}return out+"}";}
    return json::stringify(value);
}

bool extraSourceKey(const std::string& key){return extra_source17_current_generated::extraSourceKey(key);}


void need(bool ok,const char* code) { if(!ok) throw recipes::Error(code); }
const V& f(const V& v,const char* name) { const auto* p=v.find(name);if(!p)throw recipes::Error(std::string("FIELDS_")+name);return *p; }
std::string str(const V& v,const char* name) { const auto& p=f(v,name);if(!p.isString())throw recipes::Error(std::string("STRING_TYPE_")+name);return p.string(); }
std::int64_t num(const V& v) { std::int64_t n{};need(v.integer(n),"INTEGER_TYPE");return n; }
bool flag(const V& v,const char* name) { const auto& p=f(v,name);need(p.isBool(),"BOOLEAN_TYPE");return p.boolean(); }
bool hash(const std::string& s) { return s.size()==64 && std::all_of(s.begin(),s.end(),[](char c){return(c>='a'&&c<='f')||(c>='0'&&c<='9');}); }
bool nonblank(const std::string& s) { return std::any_of(s.begin(),s.end(),[](unsigned char c){return c>32;}); }
bool type(const V& v,const std::string& t) {
    if(t=="null")return v.null();if(t=="boolean")return v.isBool();if(t=="string")return v.isString();
    if(t=="object")return v.isObject();if(t=="array")return v.isArray();std::int64_t n{};return t=="integer"?v.integer(n):t=="number"&&v.isNumber();
}
std::uint64_t instance() {
    static std::atomic<std::uint64_t> n{1};auto v=n.load();
    do {need(v!=std::numeric_limits<std::uint64_t>::max(),"INSTANCE_EXHAUSTED");} while(!n.compare_exchange_weak(v,v+1));return v;
}
const std::map<std::string,std::size_t> actions{{"begin",0},{"submit",1},{"release",2},{"reveal",3},{"compare",4},{"retry",5},{"cancel",6},{"navigate",7},{"stop",8},{"reopen",9},{"finish",10},{"choose",11},{"reveal_recorded_order",12},{"reveal_source_answer",13},{"close_reference",14}};
recipes::Intent intent(const std::string& a) {
    if(a=="begin")return recipes::Intent::Choose;if(a=="release")return recipes::Intent::Release;if(a=="retry")return recipes::Intent::Retry;
    if(a=="cancel"||a=="stop")return recipes::Intent::Stop;if(a=="navigate")return recipes::Intent::Navigate;if(a=="reopen")return recipes::Intent::Reopen;return recipes::Intent::Report;
}
V boolSchema() {return O{{"type",A{"boolean","null"}},{"input_role","manual_report"}};}
V textSchema() {return O{{"type",A{"string","null"}},{"minLength",V::fromInteger(1)},{"maxLength",V::fromInteger(2000)},{"input_role","manual_report"}};}
V objectSchema(O properties) {A names;for(const auto& e:properties)names.emplace_back(e.first);return O{{"type","object"},{"properties",properties},{"required",names},{"additionalProperties",false}};}
V releaseSchema() {return objectSchema({{"learner_released",boolSchema()},{"external_source_stopped",boolSchema()}});}
int pc(const V& n) {
    if(!n.isString())return -1;static const auto p=json::parse(manual_procedure_graph_current_generated::pitchClassesJson);const auto* value=p.find(n.string());return value?static_cast<int>(num(*value)):-1;
}
int open(const std::string& s) {static const auto t=json::parse(manual_procedure_graph_current_generated::tuningJson);const auto* v=t.find(s);need(v!=nullptr,"STRING_NAME");return static_cast<int>(num(*v));}
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

namespace {
using GuardedTextPaths=std::set<std::string>;
void validateInputSchemaImpl(const V& schema,const V& input,const GuardedTextPaths& rawTextPaths,A path={}) {
    need(schema.isObject()&&!schema.find("default"),"INPUT_SCHEMA");
    if(const auto* literal=schema.find("const")) {need(input==*literal,"SOURCE_PROTOCOL_BINDING");return;}
    const auto& kinds=f(schema,"type");bool typed=false;if(kinds.isString())typed=type(input,kinds.string());else {need(kinds.isArray(),"SCHEMA_TYPE");for(const auto& kind:kinds.array())typed=typed||type(input,kind.string());}need(typed,"INPUT_TYPE");
    if(const auto* values=schema.find("enum"))need(std::find(values->array().begin(),values->array().end(),input)!=values->array().end(),"INPUT_CHOICE_RANGE");
    if(input.null())return;
    if(input.isObject()) {
        const auto& props=f(schema,"properties");need(!flag(schema,"additionalProperties")&&input.object().size()==props.object().size()&&f(schema,"required").array().size()==props.object().size(),"EXACT_INPUT_FIELDS");
        for(const auto& prop:props.object()){auto child=path;child.emplace_back(prop.first);validateInputSchemaImpl(prop.second,f(input,prop.first.c_str()),rawTextPaths,std::move(child));}
    }
    if(input.isArray()) {need(input.array().size()>=static_cast<std::size_t>(num(f(schema,"minItems"))),"ARRAY_RANGE");if(const auto* maximum=schema.find("maxItems"))need(input.array().size()<=static_cast<std::size_t>(num(*maximum)),"ARRAY_RANGE");for(std::size_t i=0;i<input.array().size();++i){auto child=path;child.push_back(V::fromInteger(static_cast<std::int64_t>(i)));validateInputSchemaImpl(f(schema,"items"),input.array()[i],rawTextPaths,std::move(child));}}
    if(input.isString()) {const bool raw=rawTextPaths.count(json::stringify(path))||(schema.find("retain_raw_for_guard")&&f(schema,"retain_raw_for_guard")==V(true));const auto length=raw?manual_procedure_graph_support::utf8TextLength(input.string()):input.string().size();if(!raw)need(nonblank(input.string()),"REPORTED_TEXT_RANGE");if(const auto* lo=schema.find("minLength"))need(raw||length>=static_cast<std::size_t>(num(*lo)),"REPORTED_TEXT_RANGE");if(const auto* hi=schema.find("maxLength"))need(length<=static_cast<std::size_t>(num(*hi)),"REPORTED_TEXT_RANGE");}
    if(input.isNumber()&&type(input,"integer")) {const auto n=num(input);if(const auto* lo=schema.find("minimum"))need(n>=num(*lo),"INTEGER_RANGE");if(const auto* hi=schema.find("maximum"))need(n<=num(*hi),"INTEGER_RANGE");}
}

GuardedTextPaths guardedTextPaths(const V& program){GuardedTextPaths result;if(const auto* graph=program.find("graph"))for(const auto& item:f(*graph,"nodes").object()){A guards;if(const auto* constraints=item.second.find("constraints"))guards=constraints->array();if(const auto* routes=item.second.find("routes"))for(const auto& route:routes->object())if(const auto* extra=route.second.find("guards"))guards.insert(guards.end(),extra->array().begin(),extra->array().end());for(const auto& guard:guards)if(str(guard,"kind")=="nonempty_trimmed_text"){if(const auto* field=guard.find("field")){need(field->isString(),"CLOSED_TEXT_FIELD");result.insert(json::stringify(A{*field}));}else{const auto& r=f(guard,"value_ref");need(str(r,"scope")=="payload"&&!f(r,"path").array().empty(),"CLOSED_TEXT_GUARD_REFERENCE");result.insert(json::stringify(f(r,"path")));}}}return result;}
const manual_procedure_graph_support::SharedSourceContexts& contextCatalog(){static const auto catalog=[] {std::vector<std::pair<std::string,std::string>> contexts;for(const auto& c:manual_procedure_graph_current_generated::contexts)contexts.emplace_back(c.path,c.value);return manual_procedure_graph_support::SharedSourceContexts(contexts);}();return catalog;}
const manual_procedure_graph_support::SharedSourceContexts& extraSourceContextCatalog(){static const auto catalog=[] {std::vector<std::pair<std::string,std::string>> contexts;for(const auto& c:extra_source17_current_generated::contexts)contexts.emplace_back(c.path,c.value);return manual_procedure_graph_support::SharedSourceContexts(contexts);}();return catalog;}
void sourceSpan(const V& original,const V& reference){
    const auto kind=str(reference,"kind");
    if(kind=="accepted_original_pdf_visual_clause"){need(reference.object().size()==5&&f(reference,"source_key")==f(original,"package_key")&&num(f(reference,"physical_page"))==14&&str(reference,"review_sha256")=="c64334730353503a598dbef5c41b428874d19fb7f099b51bfcf93849fa132790","CLOSED_SEVENTH_VISUAL_REVIEW");const auto key=str(reference,"source_key");const auto expected=key=="exercise-completeness-r01/level057/modulef/p014-supplement01/twostageiidrill"?"9683f85c73634848d2385002d9b8c43b1d99e8f6223cba298ac9645eafc1f0b2":key=="exercise-completeness-r01/level057/modulef/p014-supplement02/dominantresolutiondrill"?"61cd0b0f2083f89c39237273610b16a85ceefadfc2596ad8d73bb7d4e4b3ed72":"";need(!std::string(expected).empty()&&str(reference,"text_sha256")==expected,"EXACT_SEVENTH_VISUAL_CLAUSE");return;}
    if(kind=="original_record_literal"){need(reference.object().size()==3,"CLOSED_SOURCE_LITERAL");const auto& path=f(reference,"original_record_path");need(path.isArray()&&path.array().size()>=2&&path.array()[0]==V("implementation")&&std::none_of(path.array().begin(),path.array().end(),[](const V& part){return part==V("printed_answer");}),"CLOSED_INSTRUCTION_LITERAL_PATH");const auto& text=manual_procedure_graph_support::boundedOriginalPath(original,path);need(text.isString()&&content::sha256(text.string())==str(reference,"text_sha256"),"EXACT_SOURCE_LITERAL_HASH");return;}
    if(kind=="independently_reviewed_visual_clause"){need(reference.object().size()==2&&str(reference,"path")=="visually_read_fifth_row","CLOSED_VISUAL_CLAUSE");static const auto shared=json::parse(manual_procedure_graph_current_generated::sharedDomainsJson);need(f(shared,"reviewed_fifth_visual")==V(O{{"maj7","5-7-1-3"},{"7","5-b7-1-3"},{"m7","5-b7-1-b3"},{"m7b5","b5-b7-1-b3"}}),"REVIEWED_VISUAL_FORMULAS");return;}
    const auto& path=f(reference,"original_record_path");need(kind=="original_record_span"&&reference.object().size()==5&&(path==V(A{"implementation","source_scope","selected_source_text"})||path==V(A{"implementation","task","instructions"})),"CLOSED_SOURCE_SPAN");const auto start=num(f(reference,"start")),end=num(f(reference,"end"));need(start>=0&&end>start,"SOURCE_SPAN_RANGE");const auto& text=manual_procedure_graph_support::boundedOriginalPath(original,path);need(text.isString(),"SOURCE_SPAN_TEXT");const auto piece=manual_procedure_graph_support::utf8TextSlice(text.string(),static_cast<std::size_t>(start),static_cast<std::size_t>(end));need(content::sha256(piece)==str(reference,"text_sha256"),"EXACT_SOURCE_SPAN_HASH");
}
} // namespace
void validateInputSchema(const V& schema,const V& input){validateInputSchemaImpl(schema,input,{});}

Definition::Definition(const char* row,const char* ownClosure,const char* referenceOriginal):exported_(json::parse(row)) {
    // A closed companion for an existing extraSource identity. Its original
    // package_key remains null: this is never an official-child alias.
    if(str(exported_,"schema")=="fathom.manual-procedure-extra-source-definition.1") {
        need(referenceOriginal!=nullptr,"EXTRA_SOURCE_ORIGINAL_REQUIRED");
        referenceOriginal_=std::make_shared<const V>(json::parse(referenceOriginal));
        key_=str(exported_,"source_key");identity_=str(exported_,"source_identity");
        contractSha_=str(exported_,"contract_sha256");closureSha_=ownClosure;program_=f(exported_,"program");
        const auto& original=retainedOriginalRecord();const auto& authority=f(exported_,"authority");
        const auto& caseContract=f(exported_,"case_contract");
        need(extraSourceKey(key_)&&key_==identity_&&
             f(original,"package_key").null()&&str(original,"source_identity")==key_&&
             f(exported_,"official_child")==V(false)&&f(exported_,"runtime_admitted")==V(false),"EXACT_EXTRA_SOURCE_IDENTITY");
        need(str(f(authority,"root_decision"),"sha256")=="40968f48b7461c3ca46e2d3bf10b11485e309eb35bb382a4defa13be06d75600"&&
             str(f(authority,"distinct_source_review"),"sha256")=="b95abf3a1fdc1d6b54ba8ae7a40023a3fe0fc13d0dc5997d3ffeaddca4c183f3"&&
             str(authority,"case_version")=="extra-source17-r01:"+key_&&f(authority,"case_version")==f(caseContract,"case_version"),"EXACT_EXTRA_SOURCE_VERSION_AUTHORITY");
        need(hash(closureSha_)&&content::sha256(extraSourceCanonical(original))==str(exported_,"original_compact_sha256")&&
             f(exported_,"original_compact_sha256")==f(exported_,"original_row_sha256")&&
             content::sha256(extraSourceCanonical(program_))==contractSha_&&
             content::sha256(extraSourceCanonical(caseContract))==str(exported_,"case_contract_sha256"),"EXTRA_SOURCE_CANONICAL_BINDINGS");
        need(str(f(original,"implementation"),"kind")==str(program_,"source_kind")&&flag(program_,"original_kind_preserved")&&
             !flag(program_,"runtime_admitted")&&!flag(program_,"performance_observed")&&!flag(program_,"grants_credit")&&
             !flag(program_,"automatic_mastery")&&f(program_,"source_clock").null()&&f(program_,"fixed_bpm").null()&&f(program_,"sounding_span").null(),"EXTRA_SOURCE_MANUAL_BOUNDARY");
        need(f(exported_,"retained_contract_path")==V(A{"implementation"})&&f(program_,"source_facts")==f(caseContract,"whole_unit")&&
             f(program_,"faithful_original_full_task_available")==f(exported_,"faithful_original_full_task_available")&&
             flag(program_,"reference_only")!=flag(program_,"faithful_original_full_task_available"),"EXTRA_SOURCE_EXACT_SCOPE");
        const auto& contextRef=f(exported_,"context_ref");need(contextRef.object().size()==3&&hash(str(contextRef,"sha256")),"EXTRA_SOURCE_CONTEXT_PIN");
        context_=extraSourceContextCatalog().retain(str(contextRef,"path"));
        const auto& nodes=f(f(program_,"graph"),"nodes");need(!nodes.object().empty()&&f(program_,"steps").array().empty(),"EXTRA_SOURCE_CLOSED_GRAPH");
        for(const auto& entry:nodes.object()) {
            const auto& node=entry.second;const auto kind=str(node,"kind");
            if(flag(program_,"reference_only"))need(nodes.object().size()==2&&(kind=="end"||(kind=="source_reference_view"&&!flag(node,"physical"))),"REFERENCE_ONLY_NO_PHYSICAL_OR_COMPLETION");
            if(kind=="end"){need(!flag(node,"grants_credit"),"NO_EXTRA_SOURCE_CREDIT");continue;}
            need(actions.count(str(node,"action"))&&!flag(f(node,"schema"),"additionalProperties"),"EXTRA_SOURCE_ACTION_SCHEMA");
            need(nodes.find(str(node,"next"))!=nullptr,"EXTRA_SOURCE_CLOSED_EDGE");
        }
        return;
    }


    const auto schema=str(exported_,"schema");const bool shared=schema=="fathom.manual-procedure-shared-reference-definition.1";need(shared||schema=="fathom.compiled-manual-curriculum-definition.1"||schema=="fathom.manual-procedure-reference-definition.1","DEFINITION_SCHEMA");if(shared||schema=="fathom.manual-procedure-reference-definition.1"){need(referenceOriginal!=nullptr,"MISSING_REFERENCE_ORIGINAL");referenceOriginal_=std::make_shared<const V>(json::parse(referenceOriginal));}else need(referenceOriginal==nullptr,"OLD_EXPORT_UNCHANGED");key_=str(exported_,"source_key");identity_=str(exported_,"source_identity");contractSha_=str(exported_,"contract_sha256");closureSha_=ownClosure;if(shared){static const auto catalog=json::parse(manual_procedure_graph_current_generated::compositionSharedProgramsJson);program_=manual_procedure_graph_support::expandSharedProgram(catalog,str(exported_,"program_ref"),f(exported_,"parameters"));}else program_=f(exported_,"program");
    const auto& original=retainedOriginalRecord();need(str(original,"package_key")==key_&&str(original,"source_identity")==identity_&&manual_procedure_graph_current_generated::allowedKind(str(f(original,"implementation"),"kind"))&&(!f(original,"implementation").find("automated_assessment")||!flag(f(original,"implementation"),"automated_assessment")),"EXACT_ORIGINAL_BINDING");
    need(hash(contractSha_)&&hash(closureSha_)&&hash(str(exported_,"original_row_sha256"))&&hash(str(exported_,"original_compact_sha256"))&&f(program_,"fixed_bpm").null()&&!flag(program_,"performance_observed")&&!flag(program_,"grants_credit")&&(!program_.find("automatic_mastery")||(f(program_,"automatic_mastery")==V(false))),"SOURCE_BOUNDARY");
    const auto& contextRef=f(exported_,"context_ref");
    if(contextRef.isObject())need(contextRef.object().size()==3&&hash(str(contextRef,"sha256"))&&num(f(contextRef,"bytes"))>0,"CLOSED_CONTEXT_REFERENCE");
    context_=contextCatalog().retain(contextRef.isString()?contextRef.string():str(contextRef,"path"));
    if(referenceOriginal_){
        const auto& contract=retainedOriginalContract();
        if(hidden_seven::owns(key_)){
            need(f(exported_,"retained_contract_path")==V(A{"implementation","task","contract"})&&!flag(program_,"runtime_admitted")&&contractSha_==content::sha256(json::stringify(contract)),"CLOSED_HIDDEN_SEVEN_CONTRACT");
            hidden_seven::validate(key_,original,contract,program_);
        }else if(manual_procedure_graph_current_generated::candidateKey(key_)){
            const auto path=f(exported_,"retained_contract_path");need((path==V(A{"implementation"})||path==V(A{"implementation","manual_execution_contract"})||path==V(A{"implementation","task","contract"}))&&flag(program_,"original_kind_preserved")&&str(program_,"source_kind")==str(f(original,"implementation"),"kind")&&!flag(program_,"runtime_admitted"),"CLOSED_PRIVATE_FUTURE_SOURCE_CONTRACT");
        }else if(manual_procedure_graph_current_generated::derivedSourceKey(key_)){
            need(f(exported_,"retained_contract_path")==V(A{"implementation"})&&str(f(exported_,"approved_material_policy_ref"),"sha256")=="bdef7cce27f4e987cbca485413729a97f1646f6be3460ce468c9aa83ce5240a4"&&!flag(program_,"runtime_admitted"),"EXACT_REVIEWED_DERIVED_SOURCE_POLICY");
        }else if(manual_procedure_graph_current_generated::privateProtocolKey(key_)){
            need(f(exported_,"retained_contract_path")==V(A{"implementation","task","contract"})&&hash(str(exported_,"private_contract_sha256"))&&!flag(program_,"runtime_admitted"),"CLOSED_FUTURE_PRIVATE_SOURCE_CONTRACT");
        }else if(f(exported_,"retained_contract_path")==V(A{"implementation","table_task"})){
            need(str(f(original,"implementation"),"kind")=="manual_table_curriculum_task"&&contract.isObject()&&contract.object().size()==1&&f(contract,"printed_fields").array().size()==4,"CLOSED_SOURCE_TABLE");
            const auto& facts=f(program_,"source_facts");need(f(facts,"printed_fields")==f(contract,"printed_fields")&&f(facts,"printed_geometry").null()&&f(facts,"printed_strokes").null()&&f(facts,"source_clock").null(),"SOURCE_TABLE_BOUNDARY");
        }else if(f(exported_,"retained_contract_path")==V(A{"implementation","task_contract"})){
            need(str(f(original,"implementation"),"kind")=="source_defined_task"&&!flag(contract,"performance_observed")&&str(contract,"task_kind")==str(program_,"source_task_kind")&&f(contract,"ordered_source_instructions").isArray()&&!flag(program_,"runtime_admitted"),"SOURCE_ASSESSMENT_BOUNDARY");
        }else if(f(exported_,"retained_contract_path")==V(A{"implementation","task","contract"})){
            need(shared&&str(f(original,"implementation"),"kind")=="structured_source_prescription"&&str(program_,"source_kind")=="structured_source_prescription"&&!flag(program_,"runtime_admitted")&&f(exported_,"printed_components")==f(f(f(original,"implementation"),"task"),"printed_components"),"CLOSED_SOURCE_COMPOSITION");
        }else if(f(exported_,"retained_contract_path")==V(A{"implementation"})){
            need(str(f(original,"implementation"),"kind")=="manual_curriculum_task"&&flag(program_,"original_kind_preserved")&&str(program_,"source_kind")=="manual_curriculum_task"&&!flag(program_,"runtime_admitted"),"SOURCE_CURRICULUM_BOUNDARY");
        }else if(manual_procedure_graph_current_generated::manualSourceKey(key_)){
            need(f(exported_,"retained_contract_path")==V(A{"implementation","manual_execution_contract"})&&str(f(original,"implementation"),"kind")==str(program_,"source_kind")&&flag(program_,"original_kind_preserved")&&!flag(contract,"grants_credit")&&(!contract.find("runtime_admitted")||!flag(contract,"runtime_admitted"))&&(!contract.find("automated_assessment")||!flag(contract,"automated_assessment")),"CLOSED_RETAINED_MANUAL_SOURCE_CONTRACT");
            for(const auto* name:{"fixed_bpm","numeric_clock","source_clock"})if(const auto* clock=contract.find(name))need(clock->null(),"RETAINED_UNKNOWN_SOURCE_CLOCK");
            if(const auto* clock=contract.find("clock")){need(clock->isObject()&&clock->object().size()==4,"CLOSED_RETAINED_CLOCK");for(const auto* name:{"onset_q","duration_q","fixed_bpm","acoustic_gate_q"})need(f(*clock,name).null(),"RETAINED_UNKNOWN_SOURCE_CLOCK");}
        }else need(str(contract,"package_key")==key_&&f(contract,"fixed_bpm").null()&&!flag(contract,"grants_credit")&&!flag(contract,"runtime_admitted"),"REFERENCE_SOURCE_MANUAL_BOUNDARY");
        for(const auto& node:f(f(program_,"graph"),"nodes").object()){
            if(const auto* required=node.second.find("source_required_response_fields")){
                need(manual_procedure_graph_current_generated::candidateKey(key_)&&required->isArray(),"CLOSED_SOURCE_REQUIRED_REPORT_SCOPE");
                const auto& properties=f(f(node.second,"schema"),"properties");std::set<std::string> names;
                for(const auto& name:required->array())need(name.isString()&&properties.find(name.string())&&names.insert(name.string()).second,"CLOSED_SOURCE_REQUIRED_REPORT_FIELD");
                const auto* delegated=node.second.find("constraints");
                const bool closedTimedDelegation=names.empty()&&timed_assessment_controls::supports(original)&&delegated&&delegated->isArray()&&delegated->array().size()==1&&delegated->array().front().isObject()&&delegated->array().front().object().size()==3&&f(delegated->array().front(),"kind")==V("b_timed_assessment_controls")&&f(delegated->array().front(),"source_key")==V(key_)&&f(delegated->array().front(),"stage")==V(node.first)&&!properties.object().empty();
                const bool closedTimedEligibility=closedTimedDelegation&&str(node.second,"kind")=="choice"&&node.first=="quarter_eligibility"&&str(node.second,"action")=="choose";
                need(str(node.second,"kind")=="report"||closedTimedEligibility,"CLOSED_SOURCE_REQUIRED_REPORT_SCOPE");
                need(!names.empty()||closedTimedDelegation,"SOURCE_REQUIRED_REPORT_DUTIES");
                for(const auto& expected:f(node.second,"expected").object())need(names.count(expected.first)||(closedTimedDelegation&&properties.find(expected.first)),"SOURCE_EXPECTED_REPORT_REQUIRED");
            }
            if(const auto* refs=node.second.find("source_action_refs")){if(!refs->array().empty()){if(manual_procedure_graph_current_generated::candidateKey(key_))(void)manual_procedure_graph_support::boundFutureSourceUnit(contract,node.second);else if(f(exported_,"retained_contract_path")==V(A{"implementation","task_contract"}))(void)manual_procedure_graph_support::boundAssessmentSourceInstructions(contract,node.second);else if(manual_procedure_graph_current_generated::manualSourceKey(key_))(void)manual_procedure_graph_support::boundRetainedManualSourceUnit(contract,node.second);else(void)manual_procedure_graph_support::boundSourceUnit(contract,node.second);}}
            if(manual_procedure_graph_current_generated::candidateKey(key_)){if(node.second.find("source_action_ref")||node.second.find("release_source_action_ref"))(void)manual_procedure_graph_support::boundFutureSourceUnit(contract,node.second);}else for(const auto* field:{"source_action_ref","release_source_action_ref"})if(const auto* r=node.second.find(field))(void)manual_procedure_graph_support::boundProtocolSourceAction(contract,*r);
            if(node.second.find("source_record_refs"))(void)manual_procedure_graph_support::boundTableSourceRecords(original,node.second);
            if(const auto* refs=node.second.find("source_span_refs"))for(const auto& reference:refs->array())sourceSpan(original,reference);
        }
    }
    if(const auto* prerequisites=program_.find("source_begin_prerequisites")){need((manual_procedure_graph_current_generated::candidateKey(key_)||hidden_seven::owns(key_))&&prerequisites->isArray()&&prerequisites->array().size()<=2,"CLOSED_SOURCE_BEGIN_SCOPE");std::set<std::string> names;for(const auto& name:prerequisites->array())need(name.isString()&&(name==V("original_workbook")||name==V("own_instrument"))&&names.insert(name.string()).second,"CLOSED_SOURCE_BEGIN_PREREQUISITE");}
    need(program_.find("graph")||!f(program_,"steps").array().empty(),"PROCEDURE_STEPS");for(const auto& s:f(program_,"steps").array())need(actions.count(str(s,"action"))&&!flag(f(s,"schema"),"additionalProperties")&&f(s,"expected").isObject(),"PROCEDURE_SCHEMA");
}
const V& Definition::retainedOriginalContract() const {if(bound_source_units::coordinateOverrideKey(key_))return bound_source_units::operativeImplementation(key_);const V* value=&retainedOriginalRecord();if(referenceOriginal_){for(const auto& part:f(exported_,"retained_contract_path").array()){need(part.isString(),"ORIGINAL_CONTRACT_PATH");value=&f(*value,part.string().c_str());}}else {const auto& implementation=f(*value,"implementation");value=implementation.find("manual_execution_contract");if(!value)value=&f(implementation,"task");}return *value;}
V Definition::learnerInstructionContext() const {
    if(const auto* literal=program_.find("learner_instruction_context")){
        if(!manual_procedure_graph_current_generated::addedCKey(key_)&&key_!="exercise-completeness-r01/level084/modulej/p015-u001/modulejsectionxicompletionaudit")return *literal;
        need(literal->isArray(),"CLOSED_LEARNER_INSTRUCTION_ARRAY");A text;
        for(const auto& line:literal->array()){need(line.isString(),"CLOSED_LEARNER_INSTRUCTION_TEXT");
            if(line==V("Closed immutable set matrix authority: exercise-completeness-r01/level099/modulea/p003-u001/moduleasetselectionmatrix"))text.emplace_back("Use the printed Module A set-selection matrix for each declared set.");else if(key_=="exercise-completeness-r01/level084/modulej/p015-u001/modulejsectionxicompletionaudit"&&line==V("Source arrangement reference: exercise-completeness-r01/level084/modulei/p013-u001/moduleithirtytwobarcompletesologuitarcapstone"))text.emplace_back("Source arrangement reference: Module I thirty-two-bar complete solo-guitar capstone.");else text.push_back(line);}
        return text;
    }
    if(str(f(retainedOriginalRecord(),"implementation"),"kind")=="structured_source_prescription"){
        A text;const auto& task=f(f(retainedOriginalRecord(),"implementation"),"task");need(f(task,"label").isString(),"COMPOSITION_LABEL");text.push_back(f(task,"label"));for(const auto& line:f(task,"instructions").array()){need(f(line,"text").isString(),"COMPOSITION_INSTRUCTION");text.push_back(f(line,"text"));}static const auto instructionContext=json::parse(manual_procedure_graph_current_generated::compositionInstructionContextsJson);for(const auto& page:f(exported_,"learner_instruction_pages").array()){const auto number=num(page);const V* source=nullptr;for(const auto& cached:f(retainedSourceContext(),"pages").array())if(num(f(cached,"physical_page"))==number)source=&f(cached,"text");need(source&&source->isString(),"COMPOSITION_CONTEXT_PAGE");for(const auto& span:f(f(instructionContext,"learner_instruction_spans"),std::to_string(number).c_str()).array()){const auto piece=manual_procedure_graph_support::utf8TextSlice(source->string(),static_cast<std::size_t>(num(f(span,"start"))),static_cast<std::size_t>(num(f(span,"end"))));need(content::sha256(piece)==str(span,"text_sha256")&&f(span,"text")==V(piece),"COMPOSITION_INSTRUCTION_PIN");text.emplace_back(piece);}}return text;
    }
    if(str(f(retainedOriginalRecord(),"implementation"),"kind")=="manual_curriculum_task"){
        A text;for(const auto& witness:f(f(program_,"source_literal_ref"),"source_span_witnesses").array()){sourceSpan(retainedOriginalRecord(),f(witness,"witness"));need(f(witness,"text").isString(),"LEARNER_SOURCE_SPAN_TEXT");text.push_back(f(witness,"text"));}return text;
    }
    if(str(f(retainedOriginalRecord(),"implementation"),"kind")=="source_defined_task"){
        A text;const auto& original=retainedOriginalRecord();const auto& metadata=f(original,"source_payload");if(const auto* label=metadata.find("printed_label")){need(label->isString(),"LEARNER_LABEL_TYPE");text.push_back(*label);}for(const auto& line:f(retainedOriginalContract(),"ordered_source_instructions").array()){need(f(line,"text").isString(),"LEARNER_INSTRUCTION_TYPE");text.push_back(f(line,"text"));}return text;
    }
    // Reference definitions retain trusted source objects. Project only the
    // closed instruction paths authored for these programs, never serialize a
    // contract, player view, source locator, report default or cached page.
    const auto& reference=f(program_,"learner_instruction_context_ref");
    A text;auto add=[&](const V& value){need(value.isString()&&nonblank(value.string()),"LEARNER_INSTRUCTION_TEXT");if(std::find(text.begin(),text.end(),value)==text.end())text.push_back(value);};
    auto at=[&](const V& base,const V& path)->const V& {const V* value=&base;need(path.isArray(),"INSTRUCTION_REFERENCE_PATH");for(const auto& part:path.array()){need(part.isString(),"INSTRUCTION_REFERENCE_PATH");value=&f(*value,part.string().c_str());}return *value;};
    for(const auto& path:f(reference,"original_record_paths").array()){
        if(path==V(A{"source_payload","label"})||path==V(A{"implementation","source_scope","selected_source_text"}))add(at(retainedOriginalRecord(),path));
        else {need(path==V(A{"implementation","context_tasks"}),"CLOSED_LEARNER_RECORD_PATH");for(const auto& task:at(retainedOriginalRecord(),path).array())add(f(task,"instruction"));}
    }
    if(const auto* paths=reference.find("original_contract_paths"))for(const auto& path:paths->array()){
        const auto& value=at(retainedOriginalContract(),path);
        if(path==V(A{"physical_boundary","exact_text"})||path==V(A{"source_required_practice_duty","exact_text"}))add(value);
        else if(path==V(A{"source_rules"})){for(const auto& rule:value.object()){need(rule.first=="session"||rule.first=="local"||rule.first=="picking"||rule.first=="shift"||rule.first=="recovery","CLOSED_LEARNER_SOURCE_RULE");if(rule.first=="shift")for(const auto& step:f(rule.second,"exact_steps").array())add(step);else add(f(rule.second,"exact_text"));}}
        else if(path==V(A{"source_session_duties"})||path==V(A{"tempo_advance_gate"}))add(f(value,"exact_text"));
        else if(path==V(A{"source_required_practice_duty"}))add(f(value,"full_gate_text"));
        else if(path==V(A{"source_rule"})){if(value.isString())add(value);else add(f(value,"exact_text"));}
        else {need(path==V(A{"source_fatigue_repairs"}),"CLOSED_LEARNER_CONTRACT_PATH");for(const auto& repair:f(value,"instructions").object()){need(repair.second.isString(),"LEARNER_REPAIR_TEXT");auto label=repair.first;std::replace(label.begin(),label.end(),'_',' ');add(label+": "+repair.second.string());}}
    }
    if(const auto* pages=reference.find("cached_context_pages")){
        need(str(f(retainedOriginalRecord(),"implementation"),"kind")=="manual_table_curriculum_task"&&*pages==V(A{V::fromInteger(1),V::fromInteger(16)}),"CLOSED_LEARNER_CONTEXT_PAGES");
        // These pages also contain other cards' note arrays and table answers.
        // Only the explicitly named governing prose belongs to this surface.
        auto page=[&](std::int64_t number)->std::string {for(const auto& p:f(retainedSourceContext(),"pdf_pages").array())if(num(f(p,"physical_page"))==number)return str(p,"text");throw recipes::Error("LEARNER_CONTEXT_PAGE");};
        auto excerpt=[&](const std::string& source,const char* begin,const char* end){const auto start=source.find(begin);need(start!=std::string::npos,"LEARNER_CONTEXT_START");const auto stop=source.find(end,start);need(stop!=std::string::npos&&stop>start,"LEARNER_CONTEXT_END");add(source.substr(start,stop-start));};
        const auto first=page(1);excerpt(first,"1. Name the destination","Core phrase grammar Written workload");excerpt(first,"Session protocol","Standard tuning.");
        excerpt(page(16),"Module H - motif development and nearest-target recovery","Six eight-note motif transformations");
    }
    need(!text.empty(),"LEARNER_INSTRUCTION_CONTEXT_EMPTY");return text;
}
V Definition::sourcePlayerView() const {const auto* facts=program_.find("source_facts");if(!facts)facts=program_.find("source_metadata");const auto* hidden=program_.find("hidden_self_check");return O{{"source_key",key_},{"source_facts",facts?*facts:retainedOriginalContract()},{"hidden_self_check",hidden?*hidden:V(nullptr)},{"trusted_source_context_only",true},{"performance_observed",false},{"grants_credit",false}};}
const Definition& definition(const std::string& key) {
    static const std::map<std::string,Definition> all=[] {std::map<std::string,Definition> result;for(const auto& row:manual_procedure_graph_current_generated::rows){Definition d(row.value,row.closure,row.original);need(d.sourceKey()==row.key&&result.emplace(row.key,d).second,"CLOSED_SOURCE_KEY");}need(result.size()==manual_procedure_graph_current_generated::rowCount,"CLOSED_COMPILED_UNION");return result;}();const auto it=all.find(key);need(it!=all.end(),"EXACT_MANUAL_CURRICULUM_SCOPE");return it->second;
}
const std::vector<std::string>& keys() {static const auto result=[] {std::vector<std::string> out;for(const auto& r:manual_procedure_graph_current_generated::rows){(void)definition(r.key);out.emplace_back(r.key);}return out;}();return result;}
const Definition& extraSourceDefinition(const std::string& key) {
    static const std::map<std::string,Definition> all=[] {std::map<std::string,Definition> result;for(const auto& row:extra_source17_current_generated::rows){Definition d(row.value,row.closure,row.original);need(d.sourceKey()==row.key&&result.emplace(row.key,d).second,"CLOSED_EXTRA_SOURCE_KEY");}need(result.size()==17,"CLOSED_EXTRA_SOURCE17_SCOPE");return result;}();const auto it=all.find(key);need(it!=all.end(),"EXACT_EXTRA_SOURCE17_SCOPE");return it->second;
}
const std::vector<std::string>& extraSourceKeys(){static const auto result=[] {std::vector<std::string> out;for(const auto& row:extra_source17_current_generated::rows)out.emplace_back(row.key);return out;}();return result;}
ManualProcedureGraph::ManualProcedureGraph(const Definition& d):definition_(d),instance_(instance()) {}
Token ManualProcedureGraph::captureImpl(const std::string& action) const {
    const auto it=actions.find(action);need(it!=actions.end(),"ACTION_KIND");const auto phase=state_.releaseDebt?recipes::Phase::Release:state_.phase=="select"?recipes::Phase::Select:(state_.phase=="completed"||state_.phase=="cancelled")?recipes::Phase::Closed:recipes::Phase::Steps;
    const auto& d=graphMode()?frameDefinition(state_):definition_;
    return {{instance_,state_.pass,state_.revision,d.sourceKey(),d.contractSha256(),d.sourceClosureSha256(),phase,it->second,intent(action)},action,state_.phase,state_.cursor,state_.frames.empty()?0:state_.frames.back().serial,state_.frames.empty()?"":state_.frames.back().node};
}
Token ManualProcedureGraph::capture(const std::string& action) const {std::lock_guard<std::mutex> lock(mutex_);const auto available=hidden_seven::owns(definition_.sourceKey())?hidden_seven::actions(definition_.sourceKey(),viewImpl(),actionsImpl(),false):actionsImpl();need(std::any_of(available.array().begin(),available.array().end(),[&](const V& a){return str(a,"action")==action;}),"ACTION_NOT_CURRENT");return captureImpl(action);}
// capture() checks current availability before issuing this opaque Token.
// Its constructor/fields are private, and every owner mutation/navigation fence
// advances revision. Under the mutex, exact ownership/revision/phase/cursor/frame
// equality therefore preserves that issued action's validity. Rebuilding every
// action schema here made each large-form field edit reconstruct the full report.
// apply() still performs its complete availability and input-schema validation.
bool ManualProcedureGraph::current(const Token& t) const noexcept {try{std::lock_guard<std::mutex> lock(mutex_);const auto now=captureImpl(t.action);recipes::requireCurrentToken(t.owner,now.owner);return t.action==now.action&&t.state==now.state&&t.cursor==now.cursor&&t.frame==now.frame&&t.node==now.node;}catch(...){return false;}}
V ManualProcedureGraph::viewImpl() const {
    if(graphMode())return graphView();
    O v{{"source_key",definition_.sourceKey()},{"program",f(definition_.retainedProgram(),"name")},{"state",state_.phase},{"cursor",V::fromInteger(static_cast<std::int64_t>(state_.cursor))},{"step_count",V::fromInteger(static_cast<std::int64_t>(f(definition_.retainedProgram(),"steps").array().size()))},{"needs_manual_release",state_.releaseDebt},{"self_check_visible",state_.selfCheckVisible},{"self_check_exposed_in_history",state_.revealedEver},{"diagnosis",state_.diagnosis},{"learner_responses",state_.saved},{"source_clock",nullptr},{"fixed_bpm",nullptr},{"observed_performance",false},{"grants_credit",false},{"automatic_mastery",false},{"user_reported_procedure_finished",state_.phase=="completed"}};
    if(state_.selfCheckVisible)v.emplace("printed_self_check",f(definition_.retainedProgram(),"hidden_self_check"));return v;
}
V ManualProcedureGraph::learnerView() const {std::lock_guard<std::mutex> lock(mutex_);const auto raw=viewImpl();return hidden_seven::owns(definition_.sourceKey())?hidden_seven::learnerView(definition_.sourceKey(),raw):raw;}
V ManualProcedureGraph::learnerInstructions() const {
    std::lock_guard<std::mutex> lock(mutex_);const auto& d=graphMode()?frameDefinition(state_):definition_;A text=d.learnerInstructionContext().array();text.emplace_back("Complete each source-specific action with your own report. Unknown or negative reports require diagnosis and retry. Manual reports do not establish heard/played performance, mastery, admission or credit.");
    if(graphMode()&&state_.phase=="active"){const auto& node=graphNode(state_);if(hidden_seven::owns(d.sourceKey())&&hidden_seven::motif(d.sourceKey())&&(state_.frames.back().node=="setup"||state_.frames.back().node=="whole_pair"))text.emplace_back("Await the trusted source player. Provider choices, performance reports and scripts are not learner inputs.");else if(const auto* instruction=node.find("instruction"))text.push_back(*instruction);else if(str(node,"kind")=="source_reference_view")text.push_back(f(node,"qualification"));else text.emplace_back("Your preceding response is committed. Choose the explicit reveal to inspect the retained source self-check; no answer is entered for you.");}
    if(!graphMode()&&state_.phase=="active"&&state_.cursor<f(definition_.retainedProgram(),"steps").array().size())text.push_back(f(f(definition_.retainedProgram(),"steps").array()[state_.cursor],"instruction"));
    if(manual_procedure_graph_current_generated::candidateKey(d.sourceKey())){const auto debts=manual_procedure_graph_support::futureReportedDebtView(state_.sourcePolicyState,d.sourceKey());for(const auto& debt:debts.array())if(flag(debt,"remains_due"))text.emplace_back(str(debt,"duty")+" remains due from your report. Restart, navigation and later clean fields do not erase it.");}
    if(state_.releaseDebt)text.emplace_back("Manually release and stop/mute the source before retry, navigation or completion.");
    for(const auto& policy:state_.sourcePolicyState){if(flag(policy.second,"reduction_required")){const auto* kind=policy.second.find("debt_kind");if(!kind)text.emplace_back("Your tempo reports retain a required 4–6 BPM reduction. Restart, cancellation and navigation preserve this duty; hold or increase cannot clear it.");else if(*kind==V("source_workload_route_reduction_debt"))text.emplace_back("Your source route reduction to one tetrachord remains due. Retry, cancellation and navigation retain this duty; holding tempo cannot clear it.");else if(*kind==V("source_color_pair_repair_debt"))text.emplace_back("The color-pair source duty remains unresolved. A known unintentional change requires the printed repair and owned release. Unknown verification requires a complete fresh known-positive source retry; one later clean field cannot clear either duty.");else text.emplace_back("The source interval-equality report is still required before speed permission. No speed increase or clock is supplied.");}const auto& ceiling=f(policy.second,"reported_bpm_ceiling");if(!ceiling.null())text.emplace_back("Retained ceiling from your validated manual tempo report: "+std::to_string(num(ceiling))+" BPM. A later increase requires the source clean-trip reports. This owner supplies no clock.");}
    return O{{"text",text},{"source_clock",nullptr},{"fixed_bpm",nullptr},{"actual_performance_verified",false}};
}
V ManualProcedureGraph::actionsImpl() const {
    if(graphMode())return graphActions();
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
V ManualProcedureGraph::learnerActions() const {std::lock_guard<std::mutex> lock(mutex_);return hidden_seven::owns(definition_.sourceKey())?hidden_seven::actions(definition_.sourceKey(),viewImpl(),actionsImpl(),false):actionsImpl();}
void ManualProcedureGraph::apply(const Token& t,const V& payload) {std::lock_guard<std::mutex> lock(mutex_);V entry=O{{"kind","apply"},{"role","learner"},{"action",t.action},{"input",payload}};prepareJournalSlot();applyImpl(t,payload,false);continuationJournal_.push_back(std::move(entry));}
void ManualProcedureGraph::applyImpl(const Token& t,const V& payload,bool sourceRole) {
    const auto current=captureImpl(t.action);recipes::requireCurrentToken(t.owner,current.owner);need(t.state==current.state&&t.cursor==current.cursor&&t.action==current.action&&t.frame==current.frame&&t.node==current.node,"EXACT_ACTION_CURSOR_STATE");(void)json::parse(json::stringify(payload));
    const V* schema=nullptr;const auto available=hidden_seven::owns(definition_.sourceKey())?hidden_seven::actions(definition_.sourceKey(),viewImpl(),actionsImpl(),sourceRole):actionsImpl();need(!sourceRole||hidden_seven::owns(definition_.sourceKey()),"CLOSED_SOURCE_ROLE_SCOPE");for(const auto& a:available.array())if(str(a,"action")==t.action)schema=&f(a,"schema");need(schema!=nullptr,"ACTION_NOT_CURRENT");if(graphMode())validateInputSchemaImpl(*schema,payload,guardedTextPaths(frameDefinition(state_).retainedProgram()));else validateInputSchema(*schema,payload);
    if(graphMode()){graphApply(t,payload);return;}
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
        if(next.phase=="terminal_retry_entry"){need(next.pass!=std::numeric_limits<std::uint64_t>::max(),"PASS_EXHAUSTED");++next.pass;next.cursor=0;next.phase="active";next.saved.clear();next.selfCheckVisible=false;next.diagnosis=nullptr;}
    } else if(t.action=="cancel"||t.action=="navigate"||t.action=="stop") {next.releaseDebt=true;next.afterRelease="cancelled";next.phase="await_release";}
    else if(t.action=="reopen") {need(next.pass!=std::numeric_limits<std::uint64_t>::max(),"PASS_EXHAUSTED");++next.pass;next.phase="select";next.cursor=0;next.saved.clear();next.selfCheckVisible=false;next.diagnosis=nullptr;}
    else if(t.action=="retry") {
        need(f(payload,"diagnosis").isString()&&nonblank(str(payload,"diagnosis")),"DIAGNOSIS_REQUIRED");if(payload.find("stop_condition_resolved"))positiveBool("stop_condition_resolved");
        if(definition_.retainedProgram().find("manual_response_failure_policy")){next.releaseDebt=true;next.afterRelease="terminal_retry_entry";next.phase="await_release";}else{need(next.pass!=std::numeric_limits<std::uint64_t>::max(),"PASS_EXHAUSTED");++next.pass;next.cursor=next.retryTarget;next.phase="active";next.diagnosis=nullptr;
        if(next.cursor==0){next.saved.clear();next.selfCheckVisible=false;}}
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
            const auto* terminal=definition_.retainedProgram().find("manual_response_failure_policy");
            next.retryTarget=terminal||t.action=="compare"||stopped?0:next.cursor;next.diagnosis=O{{"reported_fields",failures},{"reported",payload},{"stop_condition",stopped},{"observed_failure",false}};
            if(flag(s,"activates_release")) {next.releaseDebt=true;next.afterRelease="needs_retry";next.phase="await_release";}else next.phase="needs_retry";
        } else {
            if(t.action=="reveal") {next.selfCheckVisible=true;next.revealedEver=true;}
            ++next.cursor;if(flag(s,"activates_release")){next.releaseDebt=true;next.afterRelease="active";next.phase="await_release";}
        }
    }
    ++next.revision;state_=std::move(next);history_.emplace_back(O{{"action",t.action},{"reported",payload},{"before",before},{"after",viewImpl()},{"pass",V::fromInteger(static_cast<std::int64_t>(t.owner.pass))},{"revision",V::fromInteger(static_cast<std::int64_t>(t.owner.revision))},{"observed_performance",false},{"grants_credit",false}});
}
namespace {
const V& ref(const V& r,const V& payload,const O& saved,const V& failed,const V& frame) {
    const auto scope=str(r,"scope");const V savedValue(saved);const V* value=scope=="payload"?&payload:scope=="saved"?&savedValue:scope=="failed"?&failed:scope=="frame"?&frame:nullptr;
    need(value!=nullptr,"REF_SCOPE");for(const auto& item:f(r,"path").array()) {
        if(item.isString()){need(value->isObject(),"REF_OBJECT");value=&f(*value,item.string().c_str());}
        else {const auto index=num(item);need(value->isArray()&&index>=0&&static_cast<std::size_t>(index)<value->array().size(),"REF_INDEX");value=&value->array()[static_cast<std::size_t>(index)];}
    }
    // savedValue is local: references into it need an owned stable source.
    if(scope=="saved") {
        const auto& path=f(r,"path").array();need(!path.empty()&&path.front().isString(),"SAVED_REF");auto it=saved.find(path.front().string());need(it!=saved.end(),"SAVED_REF");value=&it->second;
        for(std::size_t i=1;i<path.size();++i)if(path[i].isString())value=&f(*value,path[i].string().c_str());else value=&value->array()[static_cast<std::size_t>(num(path[i]))];
    }
    return *value;
}
const V& domain(const V& graph,const std::string& name) {
    if(const auto* d=f(graph,"domains").find(name))return *d;
    static const V shared=json::parse(manual_procedure_graph_current_generated::sharedDomainsJson);return f(shared,name.c_str());
}
const V* selected(const V& graph,const V& spec,const V& payload,const O& saved,const V& failed,const V& frame) {
    O choice;for(const auto& e:f(spec,"selection").object()){const auto& value=ref(e.second,payload,saved,failed,frame);if(value.null())return nullptr;choice.emplace(e.first,value);}
    const V* result=nullptr;for(const auto& entry:domain(graph,str(spec,"domain")).array())if(f(entry,"selection")==V(choice)){need(!result,"DUPLICATE_DOMAIN");result=&entry;}
    need(result!=nullptr,"CLOSED_SOURCE_PAIR_BINDING");return result;
}
std::string trimmed(const V& value) {need(value.isString(),"TEMPO_LABEL_TYPE");auto s=value.string();auto start=s.find_first_not_of(" \t\r\n");need(start!=std::string::npos,"TEMPO_LABEL_BLANK");return s.substr(start,s.find_last_not_of(" \t\r\n")-start+1);}
bool guard(const V& c,const V& graph,const V& payload,const O& saved,const V& failed,const V& frame,const V& originalContract,const O& policyState) {
    auto get=[&](const char* name)->const V&{const auto& r=f(c,name);if(str(r,"scope")=="contract"){need(r.object().size()==2&&str(c,"kind")=="reported_seconds_at_least"&&std::string(name)=="lower_bound_ref","CLOSED_CONTRACT_REFERENCE");const auto& path=f(r,"path").array();need(path.size()==3&&path[0]==V("steps")&&path[2]==V("target_seconds"),"CLOSED_TARGET_SECONDS");const auto index=num(path[1]);const auto& steps=f(originalContract,"steps").array();need(index>=0&&static_cast<std::size_t>(index)<steps.size(),"SOURCE_TARGET_RANGE");return f(steps[static_cast<std::size_t>(index)],"target_seconds");}return ref(r,payload,saved,failed,frame);};const auto kind=str(c,"kind");
    if(kind=="hidden_seven_source_unit") {need(c.object().size()==2&&hidden_seven::owns(str(frame,"source_key")),"CLOSED_HIDDEN_SEVEN_GUARD");return hidden_seven::reportedUnit(str(c,"unit"),payload,saved,originalContract);}
    const auto* localDomains=graph.find("domains");
    if(const auto phase=manual_procedure_graph_support::futureSourcePhaseRepairGuard(c,originalContract,frame,policyState))return *phase;
    if(const auto boundary=manual_procedure_graph_support::futureBoundaryRepairGuard(c,payload,originalContract,frame,policyState))return *boundary;
    if(const auto capstone=manual_procedure_graph_support::capstoneReportedGuard(c,payload,saved,localDomains?*localDomains:V(O{})))return *capstone;
    if(str(c,"kind")=="b_melodic_function_controls")return melodic_function_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_source_map_controls")return source_map_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_phrase_application_controls")return phrase_application_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_source_form_controls")return source_form_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_timed_assessment_controls")return timed_assessment_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_rootless_seventh_controls")return rootless_seventh_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_dim_context_controls")return dim_context_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_qualified_source_controls")return qualified_source_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_source_task_controls")return source_task_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_interval_recovery_controls")return interval_recovery_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_practical_triad_CAGED_controls")return practical_triad_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_whole_chord_form_controls")return whole_chord_form_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_compiled_chord_session_controls")return compiled_chord_session_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_timed_chord_change_controls")return timed_chord_change_controls::guard(c,payload,saved,policyState);
    if(str(c,"kind")=="b_progression_circle_controls")return progression_circle_controls::guard(c,payload,saved);
    if(str(c,"kind")=="b_anticipation_ladder_controls")return anticipation_ladder_controls::guard(c,payload,saved);
    if(str(c,"kind")=="b_anticipation_grid_controls")return anticipation_grid_controls::guard(c,payload,saved);
    if(str(c,"kind")=="b_diagonal_route_controls")return diagonal_route_controls::guard(c,payload,saved);
    if(str(c,"kind")=="b_source_phrase_controls")return source_phrase_controls::guard(c,payload,saved,failed,policyState);
    if(str(c,"kind")=="b_rhythm_grid_controls")return rhythm_grid_controls::guard(c,payload,saved,failed,policyState);
    if(str(c,"kind")=="b_seventh_family_controls")return seventh_family_controls::guard(c,payload,saved);
    if(str(c,"kind")=="b_beginner_source_controls")return beginner_source_controls::guard(c,payload,saved,failed,policyState);
    if(str(c,"kind")=="b_l068_source_controls")return level068_source_controls::guard(c,payload,saved);
    if(str(c,"kind").rfind("b_harmonized_",0)==0)return harmonized_triad_controls::guard(c,payload,saved);
    if(str(c,"kind")=="b_source_atom_unit"||str(c,"kind")=="b_source_choices_known"||str(c,"kind")=="b_triad_silent_landing")return bound_source_units::atomReportGuard(c,payload,saved);
    if(const auto future=manual_procedure_graph_support::futureReportedGuard(c,payload,saved,failed,localDomains?*localDomains:V(O{})))return *future;
    if(const auto source=manual_procedure_graph_support::c1661ReportedGuard(c,payload,originalContract,frame,saved,failed))return *source;
    if(kind=="c_voice_ready"){need(c.object().size()==1,"CLOSED_VOICE_READY");const auto found=policyState.find(str(frame,"source_key"));if(found==policyState.end())return true;const auto* future=found->second.find("future_debts");if(!future)return true;const auto* d=future->find("c_source_voice_reduction");const auto reported=saved.find("voice_report");if(reported==saved.end()||f(reported->second,"uncertain_voice_count").null()||num(f(reported->second,"uncertain_voice_count"))>1)return false;return !d||!flag(*d,"known_negative")||flag(*d,"repair_completed");}
    if(const auto advanced=manual_procedure_graph_support::advancedReportedGuard(c,payload,saved,failed,localDomains?*localDomains:V(O{})))return *advanced;
    if(kind=="nonempty_trimmed_text"){need(c.object().size()==4,"TEXT_GUARD_FIELDS");const auto lo=num(f(c,"minimum")),hi=num(f(c,"maximum"));need(lo>=1&&hi>=lo&&hi<=8192,"TEXT_GUARD_BOUNDS");const auto& value=c.find("field")?f(payload,str(c,"field").c_str()):get("value_ref");return !value.null()&&manual_procedure_graph_support::nonemptyTrimmedText(value,static_cast<std::size_t>(lo),static_cast<std::size_t>(hi));}
    if(kind=="trimmed_text_exact"){need(c.object().size()==2,"TEXT_GUARD_FIELDS");const auto& value=get("value_ref");return !value.null()&&manual_procedure_graph_support::trimmedTextExact(value);}
    if(kind=="equals_literal"){need(c.object().size()==3,"LITERAL_GUARD_FIELDS");const auto& value=get("value_ref");return !value.null()&&value==f(c,"literal");}
    if(kind=="reported_seconds_at_least"){need(c.object().size()==3,"SECONDS_GUARD_FIELDS");return manual_procedure_graph_support::reportedSecondsAtLeast(get("value_ref"),get("lower_bound_ref"));}
    if(kind=="failed_node_is"){need(c.object().size()==2,"FAILED_NODE_GUARD_FIELDS");return !failed.null()&&f(failed,"node")==f(c,"node")&&f(failed,"source_key")==f(frame,"source_key");}
    if(kind=="minimum"||kind=="equal"||kind=="different"||kind=="distinct_dates")return constraint(c,payload,saved,V(O{}));
    if(kind=="maximum"){need(c.object().size()==3,"MAXIMUM_GUARD_FIELDS");const auto& value=f(payload,str(c,"field").c_str());return !value.null()&&num(value)<=num(f(c,"value"));}
    if(kind=="reported_score_sum"){need(c.object().size()==3,"SCORE_GUARD_FIELDS");std::int64_t sum{};for(const auto& name:f(c,"fields").array()){const auto& rating=f(payload,name.string().c_str());if(rating.null())return false;const auto n=num(rating);need(n>=0&&n<=2&&sum<=16,"SOURCE_RUBRIC_RANGE");sum+=n;}const auto& total=f(payload,str(c,"total_field").c_str());return !total.null()&&sum==num(total);}
    if(kind=="source_policy_reported"){
        const auto policy=str(c,"policy");
        if(policy=="workload_route_tempo_choice"){need(c.object().size()==7&&num(f(c,"error_threshold"))==2&&num(f(c,"increase_requires_clean_repetitions"))==3,"CLOSED_WORKLOAD_TEMPO_POLICY");const auto& errors=f(payload,str(c,"error_count_field").c_str());const auto& clean=f(payload,str(c,"clean_count_field").c_str());if(errors.null()||clean.null())return false;const auto found=policyState.find(str(frame,"source_key"));const bool owed=found!=policyState.end()&&flag(found->second,"reduction_required");const auto choice=str(payload,str(c,"choice_field").c_str());if(num(errors)>=2||owed)return choice=="reduce_route_to_one_tetrachord";return choice=="hold_current_tempo"||(choice=="increase_after_three_clean_repetitions"&&num(clean)>=3);}
        if(policy=="reported_bpm_delta"){need(c.object().size()==6,"BPM_DELTA_FIELDS");const auto& a=f(payload,str(c,"before_field").c_str());const auto& b=f(payload,str(c,"after_field").c_str());if(a.null()||b.null())return false;const auto before=num(a),after=num(b);return before>0&&after>0&&after-before>=num(f(c,"minimum_delta"))&&after-before<=num(f(c,"maximum_delta"));}
        need(policy=="tempo_choice_trigger"&&c.object().size()==6,"TEMPO_TRIGGER_FIELDS");const auto& count=f(payload,str(c,"error_count_field").c_str());const auto& tension=f(payload,str(c,"tension_field").c_str());if(count.null()||tension.null())return false;need(tension.isBool(),"TEMPO_TENSION_TYPE");const auto retained=policyState.find(str(frame,"source_key"));const bool owed=retained!=policyState.end()&&flag(retained->second,"reduction_required");const bool reduce=num(count)>=num(f(c,"error_threshold"))||tension.boolean()||owed;const auto choice=str(payload,str(c,"choice_field").c_str());return reduce?choice=="reduce_after_errors_or_tension":choice=="hold"||choice=="increase_after_three_clean_trips";
    }
    if(kind=="source_material_reuse"){need(c.object().size()==4&&str(c,"catalog")=="level063_modules_a_i"&&flag(c,"no_new_printed_notes"),"CLOSED_SOURCE_MATERIAL_CATALOG");const auto& value=f(payload,str(c,"field").c_str());if(value.null())return false;need(value.isString(),"SOURCE_MATERIAL_TYPE");for(const auto& item:domain(graph,str(c,"catalog")).array())if(f(item,"key")==value)return true;return false;}
    if(kind=="source_protocol_reported"){
        const auto policy=str(c,"policy");
        if(policy=="four_bar_system_ceiling"){need(c.object().size()==5&&num(f(c,"block_width"))==4&&num(f(c,"maximum_distinct"))==2,"SOURCE_SYSTEM_CEILING");const auto& systems=f(payload,str(c,"systems_field").c_str());need(systems.isArray()&&systems.array().size()==16,"SOURCE_BAR_COUNT");for(std::size_t start=0;start<16;start+=4){std::set<std::string> choices;for(std::size_t i=start;i<start+4;++i){const auto& value=systems.array()[i];if(value.null())return false;need(value.isString(),"REPORTED_SYSTEM_TYPE");choices.insert(value.string());}if(choices.size()>2)return false;}return true;}
        need(policy=="timed_ladder"&&c.object().size()==8&&flag(c,"final_set_count_is_private_minimum"),"SOURCE_TIMED_LADDER");const auto& work=f(payload,str(c,"work_field").c_str());const auto& rest=f(payload,str(c,"rest_field").c_str());const auto& sets=f(payload,str(c,"clean_sets_field").c_str());const auto& targets=f(c,"source_work_targets");const auto& floors=f(c,"minimum_clean_sets");need(work.isArray()&&rest.isArray()&&sets.isArray()&&work.array().size()==9&&rest.array().size()==9&&sets.array().size()==5&&targets==V(A{V::fromInteger(15),V::fromInteger(15),V::fromInteger(15),V::fromInteger(15),V::fromInteger(30),V::fromInteger(30),V::fromInteger(45),V::fromInteger(45),V::fromInteger(60)})&&floors==V(A{V::fromInteger(1),V::fromInteger(3),V::fromInteger(2),V::fromInteger(2),V::fromInteger(1)}),"EXACT_REPORTED_LADDER_COUNTS");bool good=true;for(std::size_t i=0;i<9;++i){good=manual_procedure_graph_support::reportedSecondsAtLeast(work.array()[i],targets.array()[i])&&good;good=manual_procedure_graph_support::reportedSecondsAtLeast(rest.array()[i],work.array()[i])&&good;}for(std::size_t i=0;i<5;++i)if(sets.array()[i].null()||num(sets.array()[i])<num(floors.array()[i]))good=false;return good;
    }
    if(kind=="all_true"||kind=="known_boolean_reports") {bool good=true;for(const auto& r:f(c,"refs").array()){const auto& x=ref(r,payload,saved,failed,frame);need(x.null()||x.isBool(),"BOOLEAN_GUARD_TYPE");if(x.null()||(kind=="all_true"&&!x.boolean()))good=false;}return good;}
    if(kind=="same_as_saved") {const auto& a=get("left");const auto& b=get("right");return !a.null()&&!b.null()&&a==b;}
    if(kind=="same_as_failed_pass") {const auto& x=get("payload_ref");const auto& p=f(failed,"pass_tag");need(!p.null(),"NO_FAILED_PICK_PASS");return !x.null()&&x==p;}
    if(kind=="domain_lookup")return selected(graph,c,payload,saved,failed,frame)!=nullptr;
    if(kind=="exact_unique_case_set") {std::set<std::string> actual,expected;for(const auto& k:f(c,"expected_keys").array())expected.insert(k.string());for(const auto& row:get("array_ref").array()){need(actual.insert(str(row,str(c,"key_field").c_str())).second,"DUPLICATE_AUDIT_CASE");}need(actual==expected,"CLOSED_AUDIT_CASE_SET");return true;}
    if(kind=="complete_source_response_prefix") {bool good=true;for(const auto& row:get("array_ref").array()){const auto& a=f(row,str(c,"response_field").c_str()).array();need(a.size()==static_cast<std::size_t>(num(f(c,"steps"))),"SOURCE_RESPONSE_COUNT");for(const auto& x:a)if(x!=V("acknowledged"))good=false;}return good;}
    if(kind=="same_family_tempo") {const auto expected=trimmed(get("saved_ref"));bool good=true;for(const auto& row:get("array_ref").array())if(trimmed(f(row,str(c,"tempo_field").c_str()))!=expected)good=false;return good;}
    if(kind=="conditional_pair") {bool good=true;for(const auto& row:get("array_ref").array())for(const auto& pass:f(c,"passes").array()) {
        const auto& j=f(f(row,str(c,"judgments_field").c_str()),pass.string().c_str());const auto& result=f(j,"result");const auto& pair=f(j,"pair_start");
        if(result.null()){good=false;continue;}if(result==V("consistent")){need(pair.null(),"CONSISTENT_PAIR_MUST_BE_NULL");continue;}
        need(result==V("louder")||result==V("later"),"JUDGMENT_RANGE");if(pair.null()){good=false;continue;}
        O selection{{"source_key",f(row,str(c,"case_field").c_str())},{"pass",pass},{"pair_start",pair}};bool found=false;for(const auto& item:domain(graph,str(c,"domain")).array())if(f(item,"selection")==V(selection)){need(!found,"DUPLICATE_DOMAIN");found=true;}need(found,"CLOSED_AUDIT_PAIR_BINDING");
    }
        return good;
    }
    if(kind=="audit_outcome") {bool issue=false,unknown=false;for(const auto& row:get("array_ref").array())for(const auto& pass:f(c,"passes").array()) {const auto& r=f(f(f(row,str(c,"judgments_field").c_str()),pass.string().c_str()),"result");unknown=unknown||r.null();issue=issue||r==V("louder")||r==V("later");}return !unknown&&(str(c,"value")=="repair_required"?issue:!issue);}
    if(kind=="reported_issue_binding") {const auto& key=get("case_ref");const auto& pass=get("pass_ref");const auto& pair=get("pair_ref");if(key.null()||pass.null()||pair.null())return false;need(pass.isString(),"PAIR_PASS_TYPE");bool match=false;for(const auto& row:get("saved_ref").array())if(f(row,"case_key")==key){const auto& j=f(f(row,"judgments"),pass.string().c_str());match=(f(j,"result")==V("louder")||f(j,"result")==V("later"))&&f(j,"pair_start")==pair;}need(match,"REPORTED_ISSUE_BINDING");return true;}
    throw recipes::Error("FINITE_GUARD_KIND");
}
O computed(const V& c,const V& graph,const V& payload,const O& saved,const V& failed,const V& frame,bool& resolved) {
    O result;const auto kind=str(c,"kind");if(kind=="selected_pair_reports") {const auto* item=selected(graph,c,payload,saved,failed,frame);need(item!=nullptr,"UNRESOLVED_SELECTED_PAIR");for(const auto& field:f(c,"fields").object()){A values;for(const auto& contact:f(*item,"contacts").array())values.push_back(f(contact,field.second.string().c_str()));result[field.first]=values;}}
    else if(kind=="selected_direction_bindings") {const auto& dirs=ref(f(c,"directions_ref"),payload,saved,failed,frame).array();A values;bool first=true;std::size_t index{};for(const auto& contact:f(c,"source_contacts").array())if(f(contact,"pick")==V("P")){if(first){values.emplace_back(str(c,"pass"));first=false;}else {need(index<dirs.size(),"P_DIRECTION_COUNT");values.push_back(dirs[index++]);}}need(index==dirs.size(),"P_DIRECTION_COUNT");result[str(c,"report_field")]=values;}
    else if(kind=="selected_domain_reports"){O selection;for(const auto& item:f(c,"selection").object())selection.emplace(item.first,ref(item.second,payload,saved,failed,frame));const auto value=manual_procedure_graph_support::projectClosedDomainReports(c,selection,domain(graph,str(c,"domain")));resolved=value.resolved;if(resolved)result=value.values.object();}
    else if(kind=="source_order_P_directions"){const auto value=manual_procedure_graph_support::projectSourceOrderedPDirections(c,ref(f(c,"directions_ref"),payload,saved,failed,frame));resolved=value.resolved;if(resolved)result=value.values.object();}
    else throw recipes::Error("FINITE_COMPUTED_KIND");return result;
}
bool mentionsFutureField(const V& value,const std::string& field){
    if(value.isString())return value.string()==field;
    if(value.isObject()){for(const auto& item:value.object())if(mentionsFutureField(item.second,field))return true;}
    else if(value.isArray()){for(const auto& item:value.array())if(mentionsFutureField(item,field))return true;}
    return false;
}
bool nongatingFutureObservation(const V& node,const V& program,const O& expected,const std::string& field){
    if(field!="optional_observation"||expected.count(field))return false;
    const auto& property=f(f(f(node,"schema"),"properties"),field.c_str());
    if(f(property,"type")!=V(A{"string","null"})||!property.find("input_role")||f(property,"input_role")!=V("manual_report"))return false;
    if(const auto* title=property.find("title");title&&*title!=V("optional observation"))return false;
    if(mentionsFutureField(f(node,"constraints"),field))return false;
    if(const auto* protocols=program.find("source_state_protocols");protocols&&mentionsFutureField(*protocols,field))return false;
    return true;
}
bool knownFutureReport(const V& value){if(value.null())return false;if(value.isObject()){for(const auto& field:value.object())if(!knownFutureReport(field.second))return false;}else if(value.isArray()){for(const auto& item:value.array())if(!knownFutureReport(item))return false;}return true;}
bool knownReport(const V& value) {if(value.null())return false;if(value.isArray()){for(const auto& v:value.array())if(!knownReport(v))return false;}return true;}
void advancedPolicyBefore(const V& program,const V& payload,const std::string& key,const std::string& node,std::uint64_t pass,O& policies,bool& good){
    const auto* protocols=program.find("source_state_protocols");if(!protocols||protocols->array().empty())return;
    for(const auto& protocol:protocols->array()){
        const auto kind=str(protocol,"kind");if(kind=="source_continuous_unit"||manual_procedure_graph_support::futurePolicyKind(kind))continue;
        auto& retained=policies[key];if(retained.null())retained=O{{"reduction_required",kind=="source_tempo_permission_only"},{"trigger_unresolved",false},{"reported_bpm_ceiling",nullptr},{"debt_kind",kind},{"clear_after_owned_release",false}};
        if(kind=="source_color_pair_repair_debt"&&!retained.find("known_negative")){retained.object()["known_negative"]=false;retained.object()["repair_completed"]=false;retained.object()["activation_pass"]=V::fromInteger(0);}
        need(str(retained,"debt_kind")==kind,"SOURCE_POLICY_COLLISION");
        if(kind=="source_workload_route_reduction_debt"){
            if(node==str(protocol,"activate_node")){const auto& count=f(payload,str(protocol,"error_count_field").c_str());if(count.null()){retained.object()["reduction_required"]=true;retained.object()["trigger_unresolved"]=true;}else if(num(count)>=num(f(protocol,"error_threshold"))){retained.object()["reduction_required"]=true;retained.object()["trigger_unresolved"]=false;}}
            if(node=="tempo_increase"&&flag(retained,"reduction_required"))good=false;
        }else if(kind=="source_color_pair_repair_debt"){
            if(const auto* color=payload.find(str(protocol,"failure_field"))){need(color->null()||color->isBool(),"SOURCE_COLOR_REPORT_TYPE");if(color->null()||*color!=V(true)){if(!flag(retained,"reduction_required"))retained.object()["activation_pass"]=V::fromInteger(static_cast<std::int64_t>(pass));retained.object()["reduction_required"]=true;retained.object()["trigger_unresolved"]=color->null();if(*color==V(false)){retained.object()["known_negative"]=true;retained.object()["repair_completed"]=false;}}else if(flag(retained,"known_negative")&&!flag(retained,"repair_completed"))good=false;}
        }else need(kind=="source_tempo_permission_only","CLOSED_ADVANCED_SOURCE_POLICY");
    }
}
void advancedPolicyAfter(const V& program,const std::string& key,const std::string& node,O& policies){
    const auto* protocols=program.find("source_state_protocols");if(!protocols)return;
    for(const auto& protocol:protocols->array()){
        const auto kind=str(protocol,"kind");if(kind=="source_continuous_unit"||manual_procedure_graph_support::futurePolicyKind(kind))continue;
        auto found=policies.find(key);need(found!=policies.end(),"SOURCE_POLICY_RETAINED");bool clears=false;
        if(kind=="source_workload_route_reduction_debt")clears=node==str(protocol,"required_route_repair_node");
        else if(kind=="source_color_pair_repair_debt")clears=node==str(protocol,"repair_node");
        else if(kind=="source_tempo_permission_only")clears=node==str(protocol,"required_node");
        if(clears)found->second.object()["clear_after_owned_release"]=true;
    }
}
void dischargeAdvancedPolicyAfterOwnedRelease(O& policies){for(auto& item:policies)if(const auto* pending=item.second.find("clear_after_owned_release")){if(*pending==V(true)){if(str(item.second,"debt_kind")=="source_color_pair_repair_debt")item.second.object()["repair_completed"]=true;else{item.second.object()["reduction_required"]=false;item.second.object()["trigger_unresolved"]=false;}item.second.object()["clear_after_owned_release"]=false;}}}
V hideSavedChoiceFields(const V& value,const V& program,bool revealed){
    if(revealed)return value;const auto* hidden=program.find("learner_hidden_saved_choices");if(!hidden||hidden->array().empty())return value;
    std::set<std::string> names;for(const auto& item:hidden->array()){const auto& path=f(item,"path").array();need(!path.empty()&&path.back().isString(),"HIDDEN_CHOICE_PATH");names.insert(path.back().string());}
    std::function<V(const V&)> redact=[&](const V& source)->V{if(source.isObject()){O output;for(const auto& item:source.object())if(!names.count(item.first))output.emplace(item.first,redact(item.second));return output;}if(source.isArray()){A output;for(const auto& item:source.array())output.push_back(redact(item));return output;}return source;};return redact(value);
}
bool reportedPolicyBefore(const V& graph,const V& payload,const std::string& key,const std::string& node,O& state){
    const auto* protocols=graph.find("source_state_protocols");if(!protocols)return true;bool good=true;
    for(const auto& protocol:protocols->array()){
        need(str(protocol,"kind")=="source_tempo_reduction_debt","SOURCE_STATE_POLICY_KIND");auto& retained=state[key];if(retained.null())retained=O{{"reduction_required",false},{"trigger_unresolved",false},{"reported_bpm_ceiling",nullptr}};
        const auto& activation=f(protocol,"activate");const auto& nodes=f(activation,"nodes").array();
        if(std::find(nodes.begin(),nodes.end(),V(node))!=nodes.end()){
            const auto& count=f(payload,str(activation,"error_count_field").c_str());const auto& tension=f(payload,str(activation,"tension_field").c_str());
            if(count.null()||tension.null()){retained.object()["reduction_required"]=true;retained.object()["trigger_unresolved"]=true;}
            else {need(tension.isBool(),"SOURCE_TRIGGER_BOOLEAN");const bool trigger=num(count)>=num(f(activation,"source_reported_error_threshold"))||tension.boolean();if(trigger)retained.object()["reduction_required"]=true;retained.object()["trigger_unresolved"]=false;}
        }
        if(const auto* prior=payload.find("prior_manual_bpm")){const auto& ceiling=f(retained,"reported_bpm_ceiling");if(!prior->null()&&!ceiling.null()&&num(*prior)>num(ceiling))good=false;}
        if(node==str(protocol,"increase_node")&&flag(retained,"reduction_required"))good=false;
    }return good;
}
void reportedPolicyAfter(const V& graph,const V& payload,const std::string& key,const std::string& node,O& state){
    const auto* protocols=graph.find("source_state_protocols");if(!protocols)return;
    for(const auto& protocol:protocols->array()){
        auto& retained=state.at(key);
        if(node==str(protocol,"reduction_node")){retained.object()["reduction_required"]=false;retained.object()["trigger_unresolved"]=false;retained.object()["reported_bpm_ceiling"]=f(payload,"new_manual_bpm");}
        if(node==str(protocol,"increase_node")){need(!flag(retained,"reduction_required")&&num(f(payload,"reported_clean_complete_trips"))>=num(f(protocol,"required_clean_complete_trips")),"SOURCE_INCREASE_DUTY");retained.object()["reported_bpm_ceiling"]=f(payload,"new_manual_bpm");}
    }
}
bool reductionOwed(const O& policies){for(const auto& entry:policies)if(flag(entry.second,"reduction_required"))return true;return false;}
} // namespace
bool ManualProcedureGraph::graphMode() const noexcept{return definition_.retainedProgram().find("graph")!=nullptr;}
const Definition& ManualProcedureGraph::frameDefinition(const State& s) const{return s.frames.empty()?definition_:extraSourceKey(s.frames.back().key)?extraSourceDefinition(s.frames.back().key):definition(s.frames.back().key);}
const V& ManualProcedureGraph::graphNode(const State& s) const{need(!s.frames.empty(),"MISSING_GRAPH_FRAME");return f(f(f(frameDefinition(s).retainedProgram(),"graph"),"nodes"),s.frames.back().node.c_str());}
void ManualProcedureGraph::graphContinue(State& s,bool reportCommitted) const {
    if(reportCommitted&&!s.frames.back().exit.empty()&&s.frames.back().node==s.frames.back().exit) {
        need(s.frames.size()==2,"CALL_DEPTH");s.frames.pop_back();auto& parent=s.frames.back();
        if(!parent.calls.empty()){const auto call=parent.calls.front();parent.calls.erase(parent.calls.begin());need(s.frameSerial!=std::numeric_limits<std::uint64_t>::max(),"FRAME_EXHAUSTED");s.frames.push_back({str(call,"source_key"),str(call,"entry"),str(call,"exit"),++s.frameSerial,{},{},{}});}
        return;
    }
    if(str(graphNode(s),"kind")=="end") {need(s.frames.size()==1,"CALL_EXIT_SKIPPED");const auto& terminal=graphNode(s);const auto* failure=terminal.find("terminal_failure");
        auto retained=s.sourcePolicyState.find(s.frames.back().key);if(!failure&&retained!=s.sourcePolicyState.end()&&retained->second.find("debt_kind")&&str(retained->second,"debt_kind")=="source_color_pair_repair_debt"&&flag(retained->second,"reduction_required")&&s.pass>static_cast<std::uint64_t>(num(f(retained->second,"activation_pass")))&&(!flag(retained->second,"known_negative")||flag(retained->second,"repair_completed"))){bool complete=true;const auto& program=frameDefinition(s).retainedProgram();for(const auto& protocol:f(program,"source_state_protocols").array())if(str(protocol,"kind")=="source_color_pair_repair_debt")for(const auto& node:f(f(program,"graph"),"nodes").object())if(const auto* expected=node.second.find("expected"))if(expected->find(str(protocol,"failure_field")))complete=complete&&s.frames.back().committedNodes.count(node.first)==1;if(complete){retained->second.object()["reduction_required"]=false;retained->second.object()["trigger_unresolved"]=false;retained->second.object()["known_negative"]=false;retained->second.object()["repair_completed"]=false;}}
        const bool futureReady=manual_procedure_graph_support::futurePolicyComplete(frameDefinition(s).retainedProgram(),s.frames.back().key,s.pass,s.frames.back().committedNodes,s.sourcePolicyState);
        if(failure||reductionOwed(s.sourcePolicyState)||!futureReady||!practical_triad_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!melodic_function_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!source_map_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!phrase_application_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!source_form_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!timed_assessment_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!rootless_seventh_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!dim_context_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!qualified_source_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!source_task_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!interval_recovery_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!whole_chord_form_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!compiled_chord_session_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!timed_chord_change_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!source_phrase_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!rhythm_grid_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)||!beginner_source_controls::policyComplete(s.frames.back().key,s.sourcePolicyState)){if(failure)need(*failure==V(true)&&str(terminal,"status")=="needs_retry","CLOSED_TERMINAL_FAILURE");s.phase="needs_retry";s.failed=O{{"source_key",s.frames.back().key},{"pass_tag",nullptr},{"node",s.frames.back().node}};s.diagnosis=O{{"source_terminal_failure",true},{"observed_failure",false},{"reported_source_status",reductionOwed(s.sourcePolicyState)?V("required manual reduction remains"):f(terminal,"status")}};}else s.phase="completed";}
}
V ManualProcedureGraph::graphView() const {
    const auto& d=frameDefinition(state_);O v{{"source_key",definition_.sourceKey()},{"program",f(d.retainedProgram(),"name")},{"state",state_.phase},{"cursor",V::fromInteger(0)},{"step_count",V::fromInteger(static_cast<std::int64_t>(f(f(d.retainedProgram(),"graph"),"nodes").object().size()))},{"needs_manual_release",state_.releaseDebt},{"release_reason",state_.releaseReason},{"self_check_visible",false},{"self_check_exposed_in_history",state_.revealedEver},{"diagnosis",state_.diagnosis},{"learner_responses",state_.frames.empty()?V(O{}):V(state_.frames.back().saved)},{"reported_readiness",state_.readiness},{"failed_source_pass",state_.failed},{"family_audit_unperformed_or_unresolved",state_.auditDebt},{"whole_session_unverified",true},{"source_clock",nullptr},{"fixed_bpm",nullptr},{"observed_performance",false},{"grants_credit",false},{"automatic_mastery",false},{"user_reported_procedure_finished",state_.phase=="completed"},{"call_depth",V::fromInteger(static_cast<std::int64_t>(state_.frames.size()))}};
    if(const auto* referenceOnly=d.retainedProgram().find("source_reference_navigation_only")){need(*referenceOnly==V(true),"CLOSED_REFERENCE_NAVIGATION_METADATA");v["user_reported_procedure_finished"]=false;v["source_reference_navigation_closed"]=state_.phase=="completed";}
    v["required_reported_tempo_reduction"]=reductionOwed(state_.sourcePolicyState);if(source_form_controls::supports(definition_.retainedOriginalRecord()))v["source_form_policy"]=source_form_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(timed_assessment_controls::supports(definition_.retainedOriginalRecord()))v["timed_assessment_policy"]=timed_assessment_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(rootless_seventh_controls::supports(definition_.retainedOriginalRecord()))v["rootless_seventh_policy"]=rootless_seventh_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(dim_context_controls::supports(definition_.retainedOriginalRecord()))v["dim_context_policy"]=dim_context_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(qualified_source_controls::supports(definition_.retainedOriginalRecord()))v["qualified_source_policy"]=qualified_source_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(source_task_controls::supports(definition_.retainedOriginalRecord()))v["source_task_policy"]=source_task_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(manual_procedure_graph_current_generated::melodicKey(definition_.sourceKey()))v["melodic_function_controls_source_policy"]=melodic_function_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(manual_procedure_graph_current_generated::sourceMapKey(definition_.sourceKey()))v["source_map_controls_source_policy"]=source_map_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(manual_procedure_graph_current_generated::phraseApplicationKey(definition_.sourceKey()))v["phrase_application_controls_source_policy"]=phrase_application_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(manual_procedure_graph_current_generated::intervalRecoveryKey(definition_.sourceKey()))v["interval_recovery_controls_source_policy"]=interval_recovery_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(manual_procedure_graph_current_generated::practicalKey(definition_.sourceKey()))v["practical_triad_source_policy"]=practical_triad_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(manual_procedure_graph_current_generated::wholeFormKey(definition_.sourceKey()))v["whole_source_form_policy"]=whole_chord_form_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(manual_procedure_graph_current_generated::sessionKey(definition_.sourceKey()))v["compiled_source_session_policy"]=compiled_chord_session_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(manual_procedure_graph_current_generated::timedKey(definition_.sourceKey()))v["timed_source_policy"]=timed_chord_change_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(manual_procedure_graph_current_generated::sourcePhraseKey(definition_.sourceKey()))v["source_phrase_root_map_debt"]=source_phrase_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(manual_procedure_graph_preserved2174_generated::addedBKey(definition_.sourceKey()))v["rhythm_grid_muting_debt"]=rhythm_grid_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(beginner_source_controls::rowCount()>0&&manual_procedure_graph_preserved1965_generated::addedBKey(definition_.sourceKey()))v["beginner_source_audit_debt"]=beginner_source_controls::policyView(definition_.sourceKey(),state_.sourcePolicyState);if(!state_.frames.empty()){v["node"]=state_.frames.back().node;v["current_source_key"]=state_.frames.back().key;const auto policy=state_.sourcePolicyState.find(state_.frames.back().key);if(policy!=state_.sourcePolicyState.end()){v["reported_tempo_trigger_unresolved"]=f(policy->second,"trigger_unresolved");v["retained_reported_bpm_ceiling"]=f(policy->second,"reported_bpm_ceiling");if(policy->second.find("debt_kind")){v["source_repair_due"]=f(policy->second,"reduction_required");v["retained_source_debt_kind"]=f(policy->second,"debt_kind");}}}
    if(manual_procedure_graph_current_generated::candidateKey(d.sourceKey()))v["source_manual_debts"]=manual_procedure_graph_support::futureReportedDebtView(state_.sourcePolicyState,d.sourceKey());
    if(!state_.frames.empty()){const auto& program=d.retainedProgram();if(const auto* facts=program.find("source_facts"))if(const auto* version=facts->find("additive_curriculum_version"))if(f(*version,"version")==V("l080-six-literal-role-cells-open-realization-r01")){const auto saved=state_.frames.back().saved.find("setup");if(saved!=state_.frames.back().saved.end())v["declared_source_role_projection"]=manual_procedure_graph_support::c1661RoleProjection(d.retainedOriginalContract(),saved->second,O{{"source_key",d.sourceKey()}});}}
    const bool choiceRevealed=state_.currentPassReveals.count(d.sourceKey())!=0;v["learner_responses"]=hideSavedChoiceFields(v["learner_responses"],d.retainedProgram(),choiceRevealed);v["diagnosis"]=hideSavedChoiceFields(v["diagnosis"],d.retainedProgram(),choiceRevealed);v["failed_source_pass"]=hideSavedChoiceFields(v["failed_source_pass"],d.retainedProgram(),choiceRevealed);if(const auto shown=state_.retainedPrintedReveals.find(d.sourceKey());shown!=state_.retainedPrintedReveals.end())v["printed_self_check"]=shown->second;
    if(extraSourceKey(d.sourceKey())){const bool reference=flag(d.retainedProgram(),"reference_only");v["extra_source_identity"]=true;v["official_child"]=false;v["faithful_original_full_task_available"]=flag(d.retainedProgram(),"faithful_original_full_task_available");v["reference_only"]=reference;v["reference_closed"]=reference&&state_.phase=="completed";if(reference)v["user_reported_procedure_finished"]=false;if(state_.currentPassReveals.count(d.sourceKey())==0)v.erase("printed_self_check");}
    if(str(f(d.retainedOriginalRecord(),"implementation"),"kind")=="structured_source_prescription"){v["source_family_audit_unverified"]=true;v["selected_card_does_not_complete_family"]=true;}return v;
}
namespace {
// Learner presentation only; the retained source schema/guard/export is unchanged.
V progressionReportMenu(V schema,const V& program,const V& node,const std::string& key) {
    need(str(program,"name")=="retained_full_six_key_progression_circle_controls","CLOSED_PROGRESSION_PRESENTATION");
    const auto& constraints=f(node,"constraints");need(constraints.isArray()&&constraints.array().size()==1,"CLOSED_PROGRESSION_PRESENTATION_GUARD");
    const auto& op=constraints.array().front();need(op==V(O{{"kind","b_progression_circle_controls"},{"source_key",key},{"stage",f(node,"pass_tag")}}),"CLOSED_PROGRESSION_PRESENTATION_OWNER");
    const auto& profile=f(program,"source_profile");const auto& keys=f(profile,"ordered_source_rows").array();const auto& names=f(profile,"complete_key_order").array();need(keys.size()==6&&names.size()==6,"COMPLETE_SIX_KEY_MENU");
    A choices,labels;std::set<std::string> unique;
    for(std::size_t i=0;i<6;++i){const auto& source=f(keys[i],"source_key");need(source.isString()&&unique.insert(source.string()).second&&names[i].isString()&&!names[i].string().empty(),"EXACT_SOURCE_KEY_MENU");choices.push_back(source);labels.push_back(names[i]);}
    choices.emplace_back(nullptr);labels.emplace_back("Unknown circle key");
    std::function<void(V&)> project=[&](V& field) {
        if(!field.isObject())return;
        if(auto properties=field.object().find("properties");properties!=field.object().end()) {
            for(auto& item:properties->second.object()) {
                if(item.first=="reported_source_key") {
                    need(f(item.second,"type")==V(A{"string","null"})&&f(item.second,"input_role")==V("manual_report")&&!item.second.find("const")&&!item.second.find("default"),"MANUAL_KEY_REPORT_STAYS_BLANK");
                    item.second.object()["enum"]=choices;item.second.object()["enumLabels"]=labels;item.second.object()["label"]="Reported circle key";
                }else project(item.second);
            }
        }
        if(auto items=field.object().find("items");items!=field.object().end())project(items->second);
    };
    project(schema);return schema;
}
}
V ManualProcedureGraph::graphActions() const {
    A result;auto add=[&](const char* a,const V& sourceSchema){auto schema=sourceSchema;if(std::string(a)=="submit"&&!state_.frames.empty()&&manual_procedure_graph_current_generated::progressionKey(frameDefinition(state_).sourceKey()))schema=progressionReportMenu(std::move(schema),frameDefinition(state_).retainedProgram(),graphNode(state_),frameDefinition(state_).sourceKey());if(manual_procedure_graph_current_generated::candidateKey(frameDefinition(state_).sourceKey()))schema=manual_procedure_graph_support::candidateLearnerSchema(schema,frameDefinition(state_).retainedProgram(),state_.frames.empty()?std::string{}:state_.frames.back().node,state_.frames.empty()?O{}:state_.frames.back().saved);if(auto* props=schema.isObject()?&schema.object()["properties"]:nullptr){if(props->isObject())if(auto found=props->object().find("reused_source_material_key");found!=props->object().end()){auto& field=found->second;A labels;for(const auto& choice:f(field,"enum").array()){if(choice.null()){labels.emplace_back("Unknown source material");continue;}const auto& record=definition(choice.string()).retainedOriginalRecord();const auto& metadata=f(record,"source_payload");std::string label=str(metadata,"label");if(const auto* parents=metadata.find("parent_path"))if(parents->isArray()&&parents->array().size()>1&&parents->array()[1].isString())label=parents->array()[1].string()+" · "+label;labels.emplace_back(label);}field.object()["enumLabels"]=labels;field.object()["label"]="Previously printed source material";}}result.emplace_back(O{{"action",a},{"schema",schema},{"fresh_native_token_required",true}});};
    if(state_.releaseDebt){add("release",releaseSchema());return result;}
    if(state_.phase=="select"){if(extraSourceKey(definition_.sourceKey())&&flag(definition_.retainedProgram(),"reference_only"))add("begin",objectSchema({{"original_workbook",boolSchema()}}));else if(const auto* prerequisites=definition_.retainedProgram().find("source_begin_prerequisites")){O props;for(const auto& name:prerequisites->array())props.emplace(name.string(),boolSchema());add("begin",objectSchema(props));}else add("begin",objectSchema({{"original_workbook",boolSchema()},{"own_instrument",boolSchema()}}));}
    else if(state_.phase=="cancelled")add("reopen",objectSchema({}));else if(state_.phase=="completed"){
        const auto* protocols=f(definition_.retainedProgram(),"graph").find("source_state_protocols");
        if((protocols&&!protocols->array().empty())||bound_source_units::exactKey(definition_.sourceKey())||hidden_seven::owns(definition_.sourceKey())||manual_procedure_graph_support::futureSourceAllowsCompletedReopen(definition_.retainedProgram(),definition_.sourceKey()))add("reopen",objectSchema({}));
        return result;
    }
    else if(state_.phase=="needs_retry")add("retry",objectSchema({{"diagnosis",textSchema()}}));
    else {const auto& n=graphNode(state_);const auto* projection=n.find("schema_projection");const auto schema=projection?manual_procedure_graph_support::derivedReportSchema(*projection,state_.frames.back().saved,f(f(frameDefinition(state_).retainedProgram(),"graph"),"domains").object().at("source_triad42")):f(n,"schema");add(str(n,"action").c_str(),schema);}
    if(state_.phase!="select"&&state_.phase!="cancelled")for(const auto* a:{"cancel","navigate","stop"})add(a,objectSchema({}));return result;
}
V ManualProcedureGraph::sourcePlayerView() const {std::lock_guard<std::mutex> lock(mutex_);auto view=(graphMode()?frameDefinition(state_):definition_).sourcePlayerView();if(hidden_seven::owns(definition_.sourceKey())){view.object()["current_trusted_source_reports"]=viewImpl();view.object()["trusted_role_is_authentication"]=false;}return view;}
void ManualProcedureGraph::graphApply(const Token& t,const V& payload) {
    const auto before=viewImpl();State next=state_;need(next.revision!=std::numeric_limits<std::uint64_t>::max(),"REVISION_EXHAUSTED");
    auto yes=[&](const char* field){need(f(payload,field)==V(true),"MANUAL_RELEASE_OR_PREREQUISITE_REQUIRED");};
    auto start=[&](const std::string& node){need(next.pass!=std::numeric_limits<std::uint64_t>::max()&&next.frameSerial!=std::numeric_limits<std::uint64_t>::max(),"GRAPH_COUNTER_EXHAUSTED");++next.pass;next.frames.clear();next.frames.push_back({definition_.sourceKey(),node,"",++next.frameSerial,{},{},{}});next.currentPassReveals.clear();next.phase="active";next.diagnosis=nullptr;};
    auto exit=[&](const char* after){next.releaseDebt=true;next.releaseReason="active_exit";next.afterRelease=after;next.phase="await_release";};
    if(t.action=="begin") {if(const auto* prerequisites=definition_.retainedProgram().find("source_begin_prerequisites")){for(const auto& name:prerequisites->array())yes(name.string().c_str());}else {yes("original_workbook");if(!extraSourceKey(definition_.sourceKey())||!flag(definition_.retainedProgram(),"reference_only"))yes("own_instrument");}start(str(f(definition_.retainedProgram(),"graph"),"entry"));}
    else if(t.action=="reopen") {if(hidden_seven::owns(definition_.sourceKey())&&state_.phase=="cancelled"&&!next.frames.empty()){if(!next.diagnosis.null())next.phase="needs_retry";else {next.phase="active";graphContinue(next,false);}}else {next.phase="select";next.frames.clear();next.diagnosis=nullptr;}}
    else if(t.action=="release") {yes("learner_released");yes("external_source_stopped");dischargeAdvancedPolicyAfterOwnedRelease(next.sourcePolicyState);manual_procedure_graph_support::futurePolicyReleased(next.sourcePolicyState);beginner_source_controls::policyReleased(next.sourcePolicyState);rhythm_grid_controls::policyReleased(next.sourcePolicyState);source_phrase_controls::policyReleased(next.sourcePolicyState);timed_chord_change_controls::policyReleased(next.sourcePolicyState);compiled_chord_session_controls::policyReleased(next.sourcePolicyState);whole_chord_form_controls::policyReleased(next.sourcePolicyState);practical_triad_controls::policyReleased(next.sourcePolicyState);melodic_function_controls::policyReleased(next.sourcePolicyState);source_map_controls::policyReleased(next.sourcePolicyState);phrase_application_controls::policyReleased(next.sourcePolicyState);interval_recovery_controls::policyReleased(next.sourcePolicyState);source_task_controls::policyReleased(next.sourcePolicyState);qualified_source_controls::policyReleased(next.sourcePolicyState);dim_context_controls::policyReleased(next.sourcePolicyState);rootless_seventh_controls::policyReleased(next.sourcePolicyState);timed_assessment_controls::policyReleased(next.sourcePolicyState);source_form_controls::policyReleased(next.sourcePolicyState);next.releaseDebt=false;next.releaseReason.clear();next.phase=next.afterRelease;next.afterRelease.clear();
        if(next.phase=="graph_restart")start(str(f(definition_.retainedProgram(),"graph"),"entry"));
        else if(next.phase=="graph_repair") {need(!next.retryEntry.empty(),"REPAIR_ENTRY_REQUIRED");const auto entry=next.retryEntry;next.retryEntry.clear();start(entry);}
        else if(next.phase=="graph_commit_exit"){next.phase="active";graphContinue(next,true);}
        else if(next.phase=="active")graphContinue(next,false);
    } else if(t.action=="retry") {need(f(payload,"diagnosis").isString()&&(hidden_seven::owns(definition_.sourceKey())?hidden_seven::requiredTextVisible(f(payload,"diagnosis")):manual_procedure_graph_support::l97ListeningOwns(definition_.sourceKey())?manual_procedure_graph_support::l97ListeningRetryTextVisible(f(payload,"diagnosis")):nonblank(str(payload,"diagnosis")))&&timed_assessment_controls::visibleDiagnosis(definition_.sourceKey(),payload),"DIAGNOSIS_REQUIRED");const auto& policy=f(f(definition_.retainedProgram(),"graph"),"failure_policy");const auto* repairEntry=policy.find("failed_pass_repair_entry");bool repair=repairEntry&&repairEntry->isString()&&!next.failed.null()&&!f(next.failed,"pass_tag").null()&&f(next.failed,"source_key")==V(definition_.sourceKey());next.retryEntry=repair?repairEntry->string():"";if(const auto* nodes=policy.find("failed_node_repair_entry")){need(nodes->isObject(),"CLOSED_REPAIR_NODE_MAP");if(!next.failed.null()&&f(next.failed,"source_key")==V(definition_.sourceKey()))if(const auto* entry=nodes->find(str(next.failed,"node"))){need(entry->isString()&&f(f(definition_.retainedProgram(),"graph"),"nodes").find(entry->string()),"CLOSED_REPAIR_ENTRY");repair=true;next.retryEntry=entry->string();}}const auto timedRepair=timed_chord_change_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto sessionRepair=compiled_chord_session_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto wholeRepair=whole_chord_form_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto practicalRepair=practical_triad_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto newRepair0=melodic_function_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto newRepair1=source_map_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto newRepair2=phrase_application_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto newRepair3=interval_recovery_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto sourceTaskRepair=source_task_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto qualifiedSourceRepair=qualified_source_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto dimContextRepair=dim_context_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto rootlessRepair=rootless_seventh_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto timedAssessmentRepair=timed_assessment_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto sourceFormRepair=source_form_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState);const auto retainedRepair=!sourceFormRepair.empty()?sourceFormRepair:!timedAssessmentRepair.empty()?timedAssessmentRepair:!rootlessRepair.empty()?rootlessRepair:!dimContextRepair.empty()?dimContextRepair:!qualifiedSourceRepair.empty()?qualifiedSourceRepair:!sourceTaskRepair.empty()?sourceTaskRepair:!newRepair0.empty()?newRepair0:!newRepair1.empty()?newRepair1:!newRepair2.empty()?newRepair2:!newRepair3.empty()?newRepair3:!practicalRepair.empty()?practicalRepair:!wholeRepair.empty()?wholeRepair:!sessionRepair.empty()?sessionRepair:(timedRepair.empty()?source_phrase_controls::policyRetryEntry(definition_.sourceKey(),next.sourcePolicyState):timedRepair);if(!retainedRepair.empty()){need(f(f(definition_.retainedProgram(),"graph"),"nodes").find(retainedRepair),"CLOSED_RETAINED_DEBT_REPAIR_ENTRY");repair=true;next.retryEntry=retainedRepair;}exit(repair?"graph_repair":"graph_restart");}
    else if(t.action=="cancel"||t.action=="navigate"||t.action=="stop")exit("cancelled");
    else if(t.action=="reveal_recorded_order"||t.action=="reveal_source_answer"||t.action=="close_reference"){
        auto& frame=next.frames.back();const auto& d=frameDefinition(next);const auto& n=graphNode(next);const auto kind=str(n,"kind");
        if(t.action=="close_reference")need(kind=="source_reference_view"&&!flag(n,"physical"),"SOURCE_REFERENCE_ONLY");
        else {need(frame.committedNodes.count(str(n,"requires_committed_node"))==1,"REVEAL_AFTER_COMMITTED_REPORT");if(t.action=="reveal_recorded_order"){need(kind=="owned_saved_choice_reveal","CLOSED_SAVED_REVEAL");const V frameIdentity=O{{"source_key",frame.key}};const auto& shown=ref(f(n,"saved_choice_ref"),payload,frame.saved,next.failed,frameIdentity);next.currentPassReveals.insert(d.sourceKey());next.retainedPrintedReveals[d.sourceKey()]=shown;}else {if(kind=="owned_hidden_seven_reference_reveal"){need(hidden_seven::owns(d.sourceKey()),"CLOSED_HIDDEN_SEVEN_REVEAL");next.retainedPrintedReveals[d.sourceKey()]=hidden_seven::reveal(d.sourceKey(),d.retainedOriginalContract(),frame.saved);next.currentPassReveals.insert(d.sourceKey());}else if(kind=="owned_private_source_answer_reveal"){need(manual_procedure_graph_current_generated::privateProtocolKey(d.sourceKey())||extraSourceKey(d.sourceKey()),"EXACT_PRIVATE_SOURCE_REVEAL");next.retainedPrintedReveals[d.sourceKey()]=f(n,"answer");if(extraSourceKey(d.sourceKey()))next.currentPassReveals.insert(d.sourceKey());}else {need(kind=="owned_source_answer_reveal"&&f(f(n,"source_answer_ref"),"original_record_path")==V(A{"implementation","task","printed_answer"}),"CLOSED_SOURCE_ANSWER_REVEAL");next.retainedPrintedReveals[d.sourceKey()]=manual_procedure_graph_support::boundedOriginalPath(d.retainedOriginalRecord(),f(f(n,"source_answer_ref"),"original_record_path"));}}next.revealedEver=true;}
        frame.committedNodes.insert(frame.node);frame.node=str(n,"next");graphContinue(next,false);
    }else {
        const auto& d=frameDefinition(state_);const auto& g=f(d.retainedProgram(),"graph");const auto& n=graphNode(state_);auto& frame=next.frames.back();const V frameIdentity=O{{"source_key",frame.key},{"node",frame.node},{"pass",V::fromInteger(static_cast<std::int64_t>(next.pass))}};bool good=true;A failures;
        bool sourceStop=hidden_seven::owns(d.sourceKey())&&payload.find("no_stop_condition")&&f(payload,"no_stop_condition")==V(false);source_form_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(source_form_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}timed_assessment_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(timed_assessment_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}rootless_seventh_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(rootless_seventh_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}dim_context_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(dim_context_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}qualified_source_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(qualified_source_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}source_task_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(source_task_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}melodic_function_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(melodic_function_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}source_map_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(source_map_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}phrase_application_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(phrase_application_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}interval_recovery_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(interval_recovery_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}practical_triad_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(practical_triad_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}whole_chord_form_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(whole_chord_form_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}compiled_chord_session_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(compiled_chord_session_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}timed_chord_change_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState);if(timed_chord_change_controls::bodilyStop(frame.key,payload)){sourceStop=true;good=false;}if(!source_phrase_controls::policyBefore(frame.key,frame.node,payload,next.sourcePolicyState))good=false;if(!rhythm_grid_controls::policyBefore(frame.key,frame.node,payload,next.pass,next.sourcePolicyState))good=false;if(!manual_procedure_graph_support::futurePolicyBefore(d.retainedProgram(),payload,frame.key,frame.node,next.pass,next.sourcePolicyState,sourceStop))good=false;if(!beginner_source_controls::policyBefore(frame.key,frame.node,payload,next.pass,next.sourcePolicyState))good=false;if(bound_source_units::exactKey(frame.key)&&bound_source_units::bodilyStopReported(payload)){sourceStop=true;good=false;}
        advancedPolicyBefore(d.retainedProgram(),payload,frame.key,frame.node,next.pass,next.sourcePolicyState,good);if(!reportedPolicyBefore(g,payload,frame.key,frame.node,next.sourcePolicyState)){good=false;failures.emplace_back("retained_reported_bpm_ceiling");}
        O expected=f(n,"expected").object();if(const auto* c=n.find("computed_expected")){bool resolved=true;const auto values=computed(*c,g,payload,frame.saved,next.failed,frameIdentity,resolved);if(!resolved){good=false;failures.emplace_back("unresolved_source_selection");}expected.insert(values.begin(),values.end());}
        for(const auto& field:expected)if(f(payload,field.first.c_str())!=field.second){good=false;failures.emplace_back(field.first);}
        if(str(n,"kind")=="report"&&!manual_procedure_graph_current_generated::wholeFormKey(d.sourceKey())&&!manual_procedure_graph_current_generated::practicalKey(d.sourceKey())&&!manual_procedure_graph_current_generated::melodicKey(d.sourceKey())&&!source_task_controls::supports(d.retainedOriginalRecord())&&!timed_assessment_controls::supports(d.retainedOriginalRecord())&&!source_form_controls::supports(d.retainedOriginalRecord()))for(const auto& field:payload.object()){
            const auto* required=n.find("source_required_response_fields");
            const bool gates=required?std::find(required->array().begin(),required->array().end(),V(field.first))!=required->array().end():field.first!="limitations_note"&&!(manual_procedure_graph_current_generated::candidateKey(d.sourceKey())&&nongatingFutureObservation(n,d.retainedProgram(),expected,field.first));
            if(gates&&(!(manual_procedure_graph_current_generated::candidateKey(d.sourceKey())?knownFutureReport(field.second):knownReport(field.second))||(hidden_seven::owns(d.sourceKey())&&!hidden_seven::requiredTextVisible(field.second)))){good=false;failures.emplace_back(field.first);}
        }
        for(const auto& c:f(n,"constraints").array())if(!guard(c,g,payload,frame.saved,next.failed,frameIdentity,d.retainedOriginalContract(),next.sourcePolicyState)){good=false;failures.emplace_back(str(c,"kind"));}
        const V* route=nullptr;if(str(n,"kind")=="choice") {route=&f(f(n,"routes"),str(payload,str(n,"route_field").c_str()).c_str());if(const auto* guards=route->find("guards"))for(const auto& c:guards->array())if(!guard(c,g,payload,frame.saved,next.failed,frameIdentity,d.retainedOriginalContract(),next.sourcePolicyState)){good=false;failures.emplace_back(str(c,"kind"));}
            if(const auto* c=route->find("guard")){need((manual_procedure_graph_current_generated::newKey(d.sourceKey())||extraSourceKey(d.sourceKey()))&&(str(*route,"guard_phase")=="after_owned_release_before_new_repair_activation"||(manual_procedure_graph_current_generated::candidateKey(d.sourceKey())&&str(*route,"guard_phase")=="after_owned_release_before_repair")),"CLOSED_SOURCE_REPAIR_GUARD");const auto ownedRepair=manual_procedure_graph_current_generated::candidateKey(d.sourceKey())?manual_procedure_graph_support::futureOwnedRepairFailure(d.retainedProgram(),frame.key,*route,next.sourcePolicyState):std::nullopt;
                const auto& repairFailure=ownedRepair?*ownedRepair:next.failed;
                need(!repairFailure.null()&&f(repairFailure,"source_key")==V(frame.key)&&guard(*c,g,payload,frame.saved,repairFailure,frameIdentity,d.retainedOriginalContract(),next.sourcePolicyState)&&(!route->find("failed_node")||f(*route,"failed_node")==f(repairFailure,"node")),"SOURCE_REPAIR_REQUIRES_REPORTED_FAILURE");}
        }
        if(!good) {
            if(!n.find("computed_expected")||f(*n.find("computed_expected"),"kind")!=V("selected_pair_reports")||next.failed.null()){next.failed=O{{"source_key",d.sourceKey()},{"pass_tag",f(n,"kind")==V("report")?f(n,"pass_tag"):V(nullptr)},{"node",frame.node}};if(manual_procedure_graph_current_generated::newKey(d.sourceKey())||extraSourceKey(d.sourceKey())){next.failed.object()["payload"]=payload;if(f(next.failed,"pass_tag").null())next.failed.object()["pass_tag"]=frame.node;}}next.diagnosis=O{{"reported_fields",failures},{"reported",payload},{"observed_failure",false}};for(auto& x:next.frames)x.calls.clear();
            if(sourceStop){next.diagnosis.object()["stop_condition"]=true;if(bound_source_units::exactKey(frame.key)||flag(n,"physical"))exit("cancelled");else next.phase="cancelled";}else if(flag(n,"physical")){next.releaseDebt=true;next.releaseReason="physical_attempt";next.afterRelease="needs_retry";next.phase="await_release";}else next.phase="needs_retry";
        } else {
            beginner_source_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);rhythm_grid_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);source_phrase_controls::policyAfter(frame.key,frame.node,next.sourcePolicyState);timed_chord_change_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);compiled_chord_session_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);whole_chord_form_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);practical_triad_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);melodic_function_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);source_map_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);phrase_application_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);interval_recovery_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);source_task_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);qualified_source_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);dim_context_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);rootless_seventh_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);timed_assessment_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);source_form_controls::policyAfter(frame.key,frame.node,payload,next.sourcePolicyState);manual_procedure_graph_support::futurePolicyAfter(d.retainedProgram(),frame.key,frame.node,next.pass,next.sourcePolicyState);advancedPolicyAfter(d.retainedProgram(),frame.key,frame.node,next.sourcePolicyState);reportedPolicyAfter(g,payload,frame.key,frame.node,next.sourcePolicyState);frame.committedNodes.insert(frame.node);
            const auto& save=f(n,"save_as");if(!save.null())frame.saved[save.string()]=payload;
            for(const auto& effect:f(n,"completion_effects").array()){need(str(effect,"kind")=="write_readiness"&&flag(effect,"report_only"),"READINESS_EFFECT");const auto& value=ref(f(effect,"report_ref"),payload,frame.saved,next.failed,frameIdentity);need(value.isBool(),"READINESS_REPORT_TYPE");next.readiness[str(effect,"source_key")]=O{{"reported_ready",value},{"origin_source_key",frame.key},{"pass",V::fromInteger(static_cast<std::int64_t>(next.pass))},{"frame",V::fromInteger(static_cast<std::int64_t>(frame.serial))},{"observed",false}};}
            if(frame.node=="family_audit")next.auditDebt=str(payload,"audit_result")!="consistent";
            if(route&&route->find("native_protocol")) {const auto protocol=str(*route,"native_protocol");need(protocol=="stop"||protocol=="retry_from_entry","NATIVE_ROUTE");exit(protocol=="stop"?"cancelled":"graph_restart");}
            else {
                const bool callExit=!frame.exit.empty()&&frame.node==frame.exit;
                if(!callExit)frame.node=str(route?*route:n,"next");
                if(route&&route->find("calls")){need(next.frames.size()==1,"FINITE_CALL_DEPTH");frame.calls=f(*route,"calls").array();need(!frame.calls.empty()&&frame.calls.size()<=2,"FINITE_CALL_COUNT");const auto call=frame.calls.front();frame.calls.erase(frame.calls.begin());need(next.frameSerial!=std::numeric_limits<std::uint64_t>::max(),"FRAME_EXHAUSTED");next.frames.push_back({str(call,"source_key"),str(call,"entry"),str(call,"exit"),++next.frameSerial,{},{},{}});}
                if(flag(n,"physical")){next.releaseDebt=true;next.releaseReason="physical_attempt";next.afterRelease=callExit?"graph_commit_exit":"active";next.phase="await_release";}
                else graphContinue(next,callExit);
            }
        }
    }
    ++next.revision;state_=std::move(next);history_.emplace_back(O{{"action",t.action},{"reported",payload},{"before",before},{"after",viewImpl()},{"source_key",t.owner.sourceKey},{"contract_sha256",t.owner.contractSha256},{"own_closure_sha256",t.owner.sourceClosureSha256},{"frame",V::fromInteger(static_cast<std::int64_t>(t.frame))},{"node",t.node},{"pass",V::fromInteger(static_cast<std::int64_t>(t.owner.pass))},{"revision",V::fromInteger(static_cast<std::int64_t>(t.owner.revision))},{"observed_performance",false},{"grants_credit",false}});
}

std::size_t ManualProcedureGraph::historyCount() const {std::lock_guard<std::mutex> lock(mutex_);return history_.size();}
std::vector<V> ManualProcedureGraph::history() const {std::lock_guard<std::mutex> lock(mutex_);return hidden_seven::owns(definition_.sourceKey())?hidden_seven::learnerHistory(definition_.sourceKey(),history_):history_;}
std::vector<V> ManualProcedureGraph::sourcePlayerHistory() const {std::lock_guard<std::mutex> lock(mutex_);need(hidden_seven::owns(definition_.sourceKey()),"CLOSED_SOURCE_ROLE_SCOPE");return history_;}
V ManualProcedureGraph::sourcePlayerActions() const {std::lock_guard<std::mutex> lock(mutex_);need(hidden_seven::owns(definition_.sourceKey()),"CLOSED_SOURCE_ROLE_SCOPE");return hidden_seven::actions(definition_.sourceKey(),viewImpl(),actionsImpl(),true);}
SourceRoleAction ManualProcedureGraph::captureSourceAction(const std::string& action) const {std::lock_guard<std::mutex> lock(mutex_);need(hidden_seven::owns(definition_.sourceKey()),"CLOSED_SOURCE_ROLE_SCOPE");const auto available=hidden_seven::actions(definition_.sourceKey(),viewImpl(),actionsImpl(),true);need(std::any_of(available.array().begin(),available.array().end(),[&](const V& a){return str(a,"action")==action;}),"SOURCE_ACTION_NOT_CURRENT");return SourceRoleAction(captureImpl(action));}
bool ManualProcedureGraph::current(const SourceRoleAction& wrapped) const noexcept {try{std::lock_guard<std::mutex> lock(mutex_);if(!hidden_seven::owns(definition_.sourceKey()))return false;const auto& t=wrapped.token_;const auto now=captureImpl(t.action);recipes::requireCurrentToken(t.owner,now.owner);const auto available=hidden_seven::actions(definition_.sourceKey(),viewImpl(),actionsImpl(),true);return t.state==now.state&&t.cursor==now.cursor&&t.frame==now.frame&&t.node==now.node&&std::any_of(available.array().begin(),available.array().end(),[&](const V& a){return str(a,"action")==t.action;});}catch(...){return false;}}
void ManualProcedureGraph::applySourceAction(const SourceRoleAction& token,const V& payload){std::lock_guard<std::mutex> lock(mutex_);need(hidden_seven::owns(definition_.sourceKey()),"CLOSED_SOURCE_ROLE_SCOPE");V entry=O{{"kind","apply"},{"role","trusted_source_player"},{"action",token.token_.action},{"input",payload}};prepareJournalSlot();applyImpl(token.token_,payload,true);sourcePresentationSeen_=true;continuationJournal_.push_back(std::move(entry));}
bool ManualProcedureGraph::fenceInactiveForNavigation() {
    std::lock_guard<std::mutex> lock(mutex_);if(state_.releaseDebt||(state_.phase!="select"&&state_.phase!="completed"&&state_.phase!="cancelled"))return false;
    need(state_.pass!=std::numeric_limits<std::uint64_t>::max()&&state_.revision!=std::numeric_limits<std::uint64_t>::max(),"OWNER_COUNTER_EXHAUSTED");V entry=O{{"kind","inactive_fence"}};prepareJournalSlot();++state_.pass;++state_.revision;continuationJournal_.push_back(std::move(entry));return true;
}
void ManualProcedureGraph::prepareJournalSlot(){
    need(continuationJournal_.size()<continuationJournal_.max_size(),"CONTINUATION_JOURNAL_STORAGE_EXHAUSTED_ORIGINAL_RETAINED");
    static_assert(std::is_nothrow_move_constructible<V>::value,"Journal publication must not add an allocation failure after a native commit");
    if(continuationJournal_.size()==continuationJournal_.capacity()){
        const auto cap=continuationJournal_.capacity(),limit=continuationJournal_.max_size();
        continuationJournal_.reserve(cap>limit/2?limit:std::max<std::size_t>(8,cap*2));
    }
}
void ManualProcedureGraph::recordSourcePresentation(){
    std::lock_guard<std::mutex> lock(mutex_);need(hidden_seven::owns(definition_.sourceKey()),"CLOSED_SOURCE_ROLE_SCOPE");
    if(sourcePresentationSeen_)return;V entry=O{{"kind","intentional_source_presentation"}};prepareJournalSlot();sourcePresentationSeen_=true;continuationJournal_.push_back(std::move(entry));
}
bool ManualProcedureGraph::sourcePresentationSeen()const{std::lock_guard<std::mutex> lock(mutex_);return sourcePresentationSeen_;}
namespace {
json::Limits continuationLimits(){json::Limits l;l.bytes=64*1024*1024;l.depth=96;l.stringBytes=4*1024*1024;l.values=2000000;return l;}
V continuationBinding(const Definition&d){return O{{"source_key",d.sourceKey()},{"source_identity",d.sourceIdentity()},{"contract_sha256",d.contractSha256()},{"own_closure_sha256",d.sourceClosureSha256()}};}
void continuationShape(const V&v,std::initializer_list<const char*> names){need(v.isObject()&&v.object().size()==names.size(),"CONTINUATION_SHAPE");for(const auto*name:names)(void)f(v,name);}
}
std::string ManualProcedureGraph::continuationStateDigest(const State&snapshot)const{
    auto names=[](const std::set<std::string>&values){A out;for(const auto&v:values)out.emplace_back(v);return out;};
    auto bound=[&](const std::string&key){const auto&d=key==definition_.sourceKey()?definition_:(extraSourceKey(key)?extraSourceDefinition(key):definition(key));return O{{"source_key",d.sourceKey()},{"source_identity",d.sourceIdentity()},{"contract_sha256",d.contractSha256()},{"own_closure_sha256",d.sourceClosureSha256()}};};
    A frames;for(const auto&x:snapshot.frames){A pending;for(const auto&call:x.calls)pending.emplace_back(bound(str(call,"source_key")));frames.emplace_back(O{{"key",x.key},{"binding",bound(x.key)},{"node",x.node},{"exit",x.exit},{"serial",std::to_string(x.serial)},{"saved",x.saved},{"calls",x.calls},{"pending_call_bindings",pending},{"committed_nodes",names(x.committedNodes)}});}
    return content::sha256(json::stringify(O{{"pass",std::to_string(snapshot.pass)},{"revision",std::to_string(snapshot.revision)},{"phase",snapshot.phase},{"cursor",std::to_string(snapshot.cursor)},{"retry_target",std::to_string(snapshot.retryTarget)},{"release_debt",snapshot.releaseDebt},{"revealed_ever",snapshot.revealedEver},{"self_check_visible",snapshot.selfCheckVisible},{"after_release",snapshot.afterRelease},{"diagnosis",snapshot.diagnosis},{"saved",snapshot.saved},{"frames",frames},{"frame_serial",std::to_string(snapshot.frameSerial)},{"failed",snapshot.failed},{"readiness",snapshot.readiness},{"audit_debt",snapshot.auditDebt},{"release_reason",snapshot.releaseReason},{"retry_entry",snapshot.retryEntry},{"source_policy_state",snapshot.sourcePolicyState},{"current_pass_reveals",names(snapshot.currentPassReveals)},{"retained_printed_reveals",snapshot.retainedPrintedReveals}}));
}
PrivateContinuation ManualProcedureGraph::captureContinuation()const{
    A journal,history;State snapshot;bool seen{};
    {std::lock_guard<std::mutex> lock(mutex_);need(continuationJournal_.size()<=100000,"CONTINUATION_SAVE_LIMIT_ORIGINAL_RETAINED");journal=continuationJournal_;history=history_;snapshot=state_;seen=sourcePresentationSeen_;}
    // Hashing and bounded encoding run on an immutable copy, not under the
    // live input-owner lock. A later commit changes the journal watermark;
    // the profile controller must not call this older proposal latest-Saved.
    const auto watermark=journal.size();
    const V body=O{{"format","fathom-manual-continuation-v1"},{"binding",continuationBinding(definition_)},{"journal",std::move(journal)},{"history_sha256",content::sha256(json::stringify(std::move(history)))},{"final_state_sha256",continuationStateDigest(snapshot)},{"source_presentation_seen",seen}};
    const auto bytes=json::stringify(O{{"body",body},{"sha256",content::sha256(json::stringify(body))}});
    // Enforce the same bounded decoding contract before offering a save. A
    // refused oversized save never changes the live owner or its work limits.
    (void)json::parse(bytes,continuationLimits());return PrivateContinuation(bytes,watermark);
}
std::string ManualProcedureGraph::continuation()const{auto captured=captureContinuation();return std::move(captured.bytes_);}
std::size_t ManualProcedureGraph::continuationWatermark()const{std::lock_guard<std::mutex> lock(mutex_);return continuationJournal_.size();}
std::unique_ptr<ManualProcedureGraph> ManualProcedureGraph::restoreContinuation(const Definition& expected,const std::string& bytes){
    const auto envelope=json::parse(bytes,continuationLimits());continuationShape(envelope,{"body","sha256"});const auto&body=f(envelope,"body");
    continuationShape(body,{"format","binding","journal","history_sha256","final_state_sha256","source_presentation_seen"});
    need(f(body,"format")==V("fathom-manual-continuation-v1")&&f(envelope,"sha256")==V(content::sha256(json::stringify(body))),"CONTINUATION_FORMAT_OR_DIGEST");
    need(f(body,"binding")==continuationBinding(expected),"CONTINUATION_EXACT_SOURCE_VERSION_REQUIRED");const auto&journal=f(body,"journal");
    need(journal.isArray()&&journal.array().size()<=100000&&f(body,"source_presentation_seen").isBool(),"CONTINUATION_JOURNAL");
    auto restored=std::make_unique<ManualProcedureGraph>(expected);const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(10);
    for(const auto&entry:journal.array()){
        need(std::chrono::steady_clock::now()<deadline,"CONTINUATION_REPLAY_BUDGET_ORIGINAL_RETAINED");const auto&kind=f(entry,"kind");
        if(kind==V("apply")){continuationShape(entry,{"kind","role","action","input"});need(f(entry,"action").isString(),"CONTINUATION_ACTION");const auto action=f(entry,"action").string();
            if(f(entry,"role")==V("learner"))restored->apply(restored->capture(action),f(entry,"input"));
            else {need(f(entry,"role")==V("trusted_source_player"),"CONTINUATION_ROLE");restored->applySourceAction(restored->captureSourceAction(action),f(entry,"input"));}}
        else if(kind==V("inactive_fence")){continuationShape(entry,{"kind"});need(restored->fenceInactiveForNavigation(),"CONTINUATION_FENCE_NOT_ELIGIBLE");}
        else {continuationShape(entry,{"kind"});need(kind==V("intentional_source_presentation"),"CONTINUATION_RECORD_KIND");restored->recordSourcePresentation();}
    }
    need(restored->continuationJournal_==journal.array()&&restored->sourcePresentationSeen_==f(body,"source_presentation_seen").boolean(),"CONTINUATION_ORIGINAL_JOURNAL_REQUIRED");
    need(f(body,"history_sha256")==V(content::sha256(json::stringify(A(restored->history_))))&&f(body,"final_state_sha256")==V(restored->continuationStateDigest(restored->state_)),"CONTINUATION_HISTORY_OR_STATE_MISMATCH");
    return restored;
}
} // namespace fathom::tasks::manual_procedure_graph
