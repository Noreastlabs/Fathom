#include "tasks/SourceContactFamily.hpp"
#include "tasks/ManualProcedureDomainReports.hpp"
#include "tasks/SourceContactChoiceOperators.hpp"
#include "content/Canonical.hpp"
#include "GeneratedSourceContactFamilyData.hpp"
#include <algorithm>
#include <map>
#include <set>
#include <stdexcept>

namespace fathom::tasks::source_contacts {
namespace {
using J=json::Value;
void need(bool v,const char* why){if(!v)throw std::invalid_argument(why);}
const J& at(const J& v,const char* k){need(v.isObject()&&v.find(k),"SOURCE_CONTACT_REQUIRED_FIELD");return *v.find(k);}
std::size_t number(const J& v,std::size_t hi=1000000){std::int64_t n{};need(v.integer(n)&&n>=0&&static_cast<std::uint64_t>(n)<=hi,"SOURCE_CONTACT_INTEGER");return static_cast<std::size_t>(n);}
std::optional<int> optionalInt(const J& v,int hi=127){if(v.null())return {};return static_cast<int>(number(v,static_cast<std::size_t>(hi)));}
std::optional<bool> optionalBool(const J& v){if(v.null())return {};need(v.isBool(),"SOURCE_CONTACT_BOOLEAN");return v.boolean();}
std::string optionalText(const J& v){need(v.null()||v.isString(),"SOURCE_CONTACT_TEXT");return v.null()?std::string{}:v.string();}
Rational ratio(const J& v){need(v.isArray()&&v.array().size()==2,"SOURCE_CONTACT_RATIONAL");const auto den=number(v.array()[1]);need(den>0,"SOURCE_CONTACT_RATIONAL_DENOMINATOR");return Rational(static_cast<std::int64_t>(number(v.array()[0])),static_cast<std::int64_t>(den));}
std::optional<Rational> optionalRatio(const J& v){return v.null()?std::nullopt:std::optional<Rational>{ratio(v)};}
bool hash(const J& v){return v.isString()&&v.string().size()==64&&v.string().find_first_not_of("0123456789abcdef")==std::string::npos;}
bool date(const J& v){
 if(!v.isString())return false;const auto& s=v.string();if(s.size()!=10||s[4]!='-'||s[7]!='-')return false;
 for(std::size_t n=0;n<s.size();++n)if(n!=4&&n!=7&&(s[n]<'0'||s[n]>'9'))return false;
 const int y=std::stoi(s.substr(0,4)),m=std::stoi(s.substr(5,2)),d=std::stoi(s.substr(8));if(y==0||m<1||m>12)return false;
 const int days[]{31,28,31,30,31,30,31,31,30,31,30,31};return d>0&&d<=days[m-1]+(m==2&&y%4==0&&(y%100!=0||y%400==0));
}
bool type(const J& v,const std::string& t){if(t=="null")return v.null();if(t=="string")return v.isString();if(t=="boolean")return v.isBool();if(t=="integer"){std::int64_t n{};return v.integer(n);}if(t=="object")return v.isObject();if(t=="array")return v.isArray();return false;}
struct Table {
 J atoms=json::parse(compiled::atomsJson),contexts=json::parse(compiled::contextsJson);
 std::vector<J> rows;std::vector<std::string> keys;std::map<std::string,std::size_t> index;
 Table(){
  need(compiled::rows.size()==664&&atoms.isArray()&&contexts.isObject(),"SOURCE_CONTACT_CLOSED664");std::set<std::string> identities;
  for(const auto& a:atoms.array()){
   need(at(a,"acoustic_gate").null()&&hash(at(a,"raw_atom_sha256")),"SOURCE_CONTACT_NO_ACOUSTIC_DEFAULT");
   (void)optionalInt(at(a,"midi"));const auto finger=optionalInt(at(a,"finger"),4);need(!finger||*finger>=1,"SOURCE_CONTACT_PRINTED_FINGER");
   (void)optionalInt(at(a,"physical_fret"));(void)optionalInt(at(a,"sounding_fret"));(void)optionalInt(at(a,"reference_fret"));
   (void)optionalBool(at(a,"picked"));(void)optionalBool(at(a,"audible"));(void)optionalRatio(at(a,"onset"));const auto duration=optionalRatio(at(a,"hand_slot_duration"));need(!duration||Rational(0)<*duration,"SOURCE_CONTACT_RELATIVE_HAND_SLOT");
   if(at(a,"kind")==J("source_pitch_definition")||at(a,"kind")==J("nonaudible_reference"))need(at(a,"audible")==J(false),"SOURCE_CONTACT_REFERENCE_NOT_SOUNDING");
  }
  for(const auto& input:compiled::rows){
   auto r=json::parse(input.json);auto body=r;body.object().erase("compiled_definition_sha256");
   need(at(r,"schema")==J("fathom.compiled-source-contact-definition.1")&&at(r,"compiled_definition_sha256")==J(content::sha256(json::stringify(body))),"SOURCE_CONTACT_CLOSED_ROW_HASH");
   need(at(r,"source_key")==J(input.key)&&hash(at(r,"source_record_canonical_sha256"))&&hash(at(r,"contract_sha256"))&&index.emplace(input.key,rows.size()).second&&identities.insert(at(r,"source_identity").string()).second,"SOURCE_CONTACT_KEY_SOURCE_CONTRACT_BINDING");
   for(const auto* k:{"source_clock","source_acoustic_gates"})need(at(r,k).null(),"SOURCE_CONTACT_UNKNOWN_SOURCE_AUTHORITY");for(const auto* k:{"native_music_model","runtime_admitted","grants_credit"})need(at(r,k)==J(false),"SOURCE_CONTACT_NO_MODEL_OR_CREDIT");
   need(at(r,"routes").isArray()&&!at(r,"routes").array().empty(),"SOURCE_CONTACT_CLOSED_ROUTES");
   for(const auto& route:at(r,"routes").array()){
    const auto& indices=at(route,"atom_indices").array();const auto& units=at(route,"units").array();std::size_t next=0;
    for(const auto& i:indices)need(number(i)<atoms.array().size(),"SOURCE_CONTACT_ATOM_REFERENCE");
    J::Array boundAtoms;for(const auto& i:indices)boundAtoms.push_back(atoms.array()[number(i)]);need(at(route,"source_atoms_sha256")==J(content::sha256(json::stringify(J(boundAtoms)))),"SOURCE_CONTACT_ATOM_POOL_ROUTE_HASH");
    for(const auto& u:units){need(u.isArray()&&!u.array().empty(),"SOURCE_CONTACT_ATOMIC_GROUP");for(const auto& i:u.array())need(number(i)==next++&&number(i)<indices.size(),"SOURCE_CONTACT_NO_ATOM_LOSS_OR_REORDER");}
    need(next==indices.size(),"SOURCE_CONTACT_COMPLETE_ATOMIC_ROUTE");const auto& variants=at(route,"pick_variants").array();need(variants.empty()||variants.size()==2,"SOURCE_CONTACT_CLOSED_STARTS");
    for(std::size_t n=0;n<variants.size();++n){const auto& v=variants[n];need(at(v,"pick_start")==J(n?"U":"D")&&at(v,"strokes_by_contact").array().size()==indices.size(),"SOURCE_CONTACT_SAVED_VARIANT_SCOPE");for(const auto& s:at(v,"strokes_by_contact").array())need(s.null()||s==J("D")||s==J("U"),"SOURCE_CONTACT_TYPED_PICK");}
    const auto& p=at(route,"program");need(at(p,"schema")==J("fathom.source-contact-program.1")&&(at(p,"requires_both_saved_starts")==J(!variants.empty())||(p.find("requires_manual_authored_starts")&&at(p,"requires_manual_authored_starts")==J(true))),"SOURCE_CONTACT_PROGRAM_START_BINDING");
    need(at(p,"native_music_model")==J(false)&&at(p,"source_clock").null()&&at(p,"source_acoustic_gates").null()&&at(p,"inherits_physical_tempo_rule")==J(false)&&at(p,"inherits_physical_frame_or_pick_debt")==J(false),"SOURCE_CONTACT_SOURCE_POLICY_SEPARATION");
    std::size_t last=0;for(const auto& phase:at(p,"report_phases").array()){const auto after=number(at(phase,"after_source_ordinal"));need(after>=last&&after<=units.size()&&at(phase,"source_refs").isArray()&&!at(phase,"source_refs").array().empty(),"SOURCE_CONTACT_PHASE_SOURCE_BOUNDARY");last=after;need(at(at(phase,"report_schema"),"additionalProperties")==J(false),"SOURCE_CONTACT_CLOSED_REPORT_SCHEMA");}
    need(!at(p,"report_phases").array().empty()&&last==units.size(),"SOURCE_CONTACT_COMPLETE_SOURCE_EXTENT");
   }
   keys.push_back(input.key);rows.push_back(std::move(r));
  }
  need(rows.size()==664&&index.size()==664&&identities.size()==664,"SOURCE_CONTACT_ZERO_PARTIAL_TABLE");
 }
};
const Table& table(){static const Table t;return t;}
const J& row(std::size_t i){need(i<table().rows.size(),"SOURCE_CONTACT_CLOSED_INDEX");return table().rows[i];}
const J& route(std::size_t i,std::size_t r){const auto& routes=at(row(i),"routes").array();need(r<routes.size(),"SOURCE_CONTACT_EXACT_ROUTE");return routes[r];}
const char* string(const J& v,const char* k){return at(v,k).string().c_str();}
}
const char* Definition::sourceKey()const{return string(row(index_),"source_key");}
const char* Definition::sourceIdentity()const{return string(row(index_),"source_identity");}
const char* Definition::sourceRecordSha256()const{return string(row(index_),"source_record_canonical_sha256");}
const char* Definition::packetPath()const{return string(at(row(index_),"payload_ref"),"path");}
const char* Definition::packetSha256()const{return string(at(row(index_),"payload_ref"),"sha256");}
int Definition::packetLine()const{return static_cast<int>(number(at(at(row(index_),"payload_ref"),"jsonl_line")));}
int Definition::level()const{return static_cast<int>(number(at(row(index_),"level")));}
std::size_t Definition::contactCount(std::size_t r)const{return at(route(index_,r),"units").array().size();}
std::size_t Definition::routeCount()const{return at(row(index_),"routes").array().size();}
std::size_t Definition::sourceAtomCount()const{return at(route(index_,0),"atom_indices").array().size();}
std::vector<PickVariant> Definition::savedPickVariants(std::size_t r)const{return at(route(index_,r),"pick_variants").array().empty()?std::vector<PickVariant>{}:std::vector<PickVariant>{PickVariant::Down,PickVariant::Up};}
std::optional<Rational> Definition::selectedMetricEnd(std::size_t r)const{return optionalRatio(at(route(index_,r),"metric_end"));}
Cue Definition::contact(std::size_t ordinal,PickVariant start,std::size_t r)const{
 need(ordinal>0&&ordinal<=contactCount(r),"SOURCE_CONTACT_EXACT_ORDINAL");const auto& q=route(index_,r);const auto& variants=at(q,"pick_variants").array();
 need(variants.empty()?start==PickVariant::Unspecified:(start==PickVariant::Down||start==PickVariant::Up),"SOURCE_CONTACT_SAVED_OR_UNSPECIFIED_START");
 Cue c{sourceKey(),sourceIdentity(),sourceRecordSha256(),r,ordinal,{},false};const auto& unit=at(q,"units").array()[ordinal-1].array();c.simultaneous=unit.size()>1;
 for(const auto& pos:unit){const auto i=number(pos);const auto& a=table().atoms.array()[number(at(q,"atom_indices").array()[i])];std::optional<std::string> pick;
  if(!variants.empty()){const auto& s=at(variants[start==PickVariant::Down?0:1],"strokes_by_contact").array()[i];if(!s.null())pick=s.string();}
  c.atoms.push_back({number(at(a,"source_ordinal")),at(a,"string_label").string(),at(a,"kind").string(),optionalText(at(a,"spelling")),optionalText(at(a,"attack")),optionalText(at(a,"technique")),json::stringify(at(a,"annotations")),optionalInt(at(a,"string_low_to_high"),6),optionalInt(at(a,"physical_fret")),optionalInt(at(a,"sounding_fret")),optionalInt(at(a,"reference_fret")),optionalInt(at(a,"midi")),optionalInt(at(a,"finger"),4),optionalBool(at(a,"picked")),optionalBool(at(a,"audible")),optionalRatio(at(a,"onset")),optionalRatio(at(a,"hand_slot_duration")),pick,json::stringify(at(a,"source_facts"))});
 }
 return c;
}
void Definition::requireSourceParity(const Cue& c,PickVariant start)const{
 const auto e=contact(c.ordinal,start,c.routeIndex);need(c.sourceKey==e.sourceKey&&c.sourceIdentity==e.sourceIdentity&&c.sourceRecordSha256==e.sourceRecordSha256&&c.routeIndex==e.routeIndex&&c.ordinal==e.ordinal&&c.simultaneous==e.simultaneous&&c.atoms.size()==e.atoms.size(),"SOURCE_CONTACT_EXACT_CUE_BINDING");
 for(std::size_t n=0;n<c.atoms.size();++n){const auto& a=c.atoms[n];const auto& b=e.atoms[n];need(a.sourceOrdinal==b.sourceOrdinal&&a.stringLabel==b.stringLabel&&a.kind==b.kind&&a.spelling==b.spelling&&a.attack==b.attack&&a.technique==b.technique&&a.annotationsJson==b.annotationsJson&&a.stringLowToHigh==b.stringLowToHigh&&a.physicalFret==b.physicalFret&&a.soundingFret==b.soundingFret&&a.referenceFret==b.referenceFret&&a.midi==b.midi&&a.finger==b.finger&&a.picked==b.picked&&a.audible==b.audible&&a.onset==b.onset&&a.handSlotDuration==b.handSlotDuration&&a.pick==b.pick&&a.sourceFactsJson==b.sourceFactsJson,"SOURCE_CONTACT_EXACT_OPTIONAL_ATOM_PARITY");}
}
std::string Definition::trustedMetadataJson()const{return json::stringify(row(index_));}
std::string Definition::trustedContextJson()const{const auto& r=row(index_);const auto& ctx=at(table().contexts,at(r,"context_key").string().c_str());need(at(ctx,"context_ref")==at(r,"context_ref"),"SOURCE_CONTACT_CONTEXT_BINDING");return json::stringify(ctx);}
std::string Definition::sourceProgramJson(std::size_t r)const{return json::stringify(at(route(index_,r),"program"));}
std::string Definition::sourceAtomsJson(std::size_t r)const{J::Array atoms;for(const auto& i:at(route(index_,r),"atom_indices").array())atoms.push_back(table().atoms.array()[number(i)]);return json::stringify(J(std::move(atoms)));}
const std::vector<std::string>& keys(){return table().keys;}
const Definition& definition(const std::string& k){const auto p=table().index.find(k);need(p!=table().index.end(),"SOURCE_CONTACT_UNKNOWN_KEY");static const auto handles=[](){std::vector<Definition> v;v.reserve(664);for(std::size_t n=0;n<664;++n)v.push_back(Definition(n));return v;}();return handles[p->second];}
const char* closureSha256(){return compiled::closureSha;}
void validateReport(const J& s,const J& value){
 const auto& types=at(s,"type");bool good=false;if(types.isString())good=type(value,types.string());else {need(types.isArray(),"SOURCE_REPORT_TYPE_SCHEMA");for(const auto& t:types.array())good=good||type(value,t.string());}need(good,"SOURCE_REPORT_TYPE");
 if(const auto* e=s.find("enum"))need(std::find(e->array().begin(),e->array().end(),value)!=e->array().end(),"SOURCE_REPORT_ENUM");if(const auto* c=s.find("const"))need(value==*c,"SOURCE_REPORT_CONSTANT_BINDING");if(value.null())return;
 if(value.isObject()){const auto& props=at(s,"properties").object();need(at(s,"additionalProperties")==J(false),"SOURCE_REPORT_CLOSED_OBJECT");for(const auto& k:at(s,"required").array())(void)at(value,k.string().c_str());for(const auto& x:value.object()){need(props.count(x.first),"SOURCE_REPORT_UNKNOWN_FIELD");validateReport(props.at(x.first),x.second);}}
 if(value.isArray()){const auto n=value.array().size();need(n>=number(at(s,"minItems"))&&n<=number(at(s,"maxItems")),"SOURCE_REPORT_ARRAY_BOUND");for(const auto& x:value.array())validateReport(at(s,"items"),x);}
 if(value.isString()){if(const auto* max=s.find("maxLength"))need(manual_procedure_graph_support::utf8TextLength(value.string())<=number(*max),"SOURCE_REPORT_TEXT_BOUND");}
 std::int64_t n{};if(value.integer(n)){need(n>=0,"SOURCE_REPORT_NONNEGATIVE_INTEGER");if(const auto* lo=s.find("minimum"))need(n>=static_cast<std::int64_t>(number(*lo)),"SOURCE_REPORT_INTEGER_MINIMUM");if(const auto* hi=s.find("maximum"))need(n<=static_cast<std::int64_t>(number(*hi)),"SOURCE_REPORT_INTEGER_MAXIMUM");}
}
bool phaseReportResolved(const J& p,const J& report){
 validateReport(at(p,"report_schema"),report);bool resolved=true;
 for(const auto& g:at(p,"guards").array()){
  const auto& k=at(g,"kind").string();if(k=="saved_equal_literal")continue;
  if(const auto r=private_operators::reportGuard(g,report)){resolved=resolved&&*r;continue;}
  if(k=="tempo_reduction"||k=="reduction_or_source_isolation"){
   if(k=="reduction_or_source_isolation"&&at(report,at(g,"field").string().c_str())==J("isolate_one_source_unit")){resolved=resolved&&at(report,at(g,"isolation_report_field").string().c_str())==J("reported_met")&&at(report,at(g,"previous_field").string().c_str()).null()&&at(report,at(g,"new_field").string().c_str()).null()&&at(report,at(g,"drop_field").string().c_str()).null();continue;}
   const auto& old=at(report,at(g,"previous_field").string().c_str());const auto& now=at(report,at(g,"new_field").string().c_str());const auto& drop=at(report,at(g,"drop_field").string().c_str());resolved=resolved&&!old.null()&&!now.null()&&!drop.null()&&number(now)>0&&number(old)==number(now)+number(drop)&&number(drop)>=4&&number(drop)<=6;
   if(k=="reduction_or_source_isolation")resolved=resolved&&at(report,at(g,"field").string().c_str())==J("reduce_4_6");continue;
  }
  if(k=="source_tempo_progression"){
   const auto& choice=at(report,at(g,"field").string().c_str());const auto& old=at(report,at(g,"previous_field").string().c_str());const auto& now=at(report,at(g,"new_field").string().c_str());const auto& clean=at(report,at(g,"clean_field").string().c_str());
   resolved=resolved&&!old.null()&&!now.null()&&number(old)>0&&(choice==J("hold")?old==now:choice==J("increase_2")&&!clean.null()&&number(clean)>=3&&number(now)==number(old)+2);continue;
  }
  const auto& v=at(report,at(g,"field").string().c_str());
  if(k=="reported_met")resolved=resolved&&v==J("reported_met");
  else if(k=="nonempty_trimmed_text")resolved=resolved&&!v.null()&&manual_procedure_graph_support::nonemptyTrimmedText(v,1,4096);
  else if(k=="equal_literal")resolved=resolved&&v==at(g,"value");
  else if(k=="minimum")resolved=resolved&&!v.null()&&number(v)>=number(at(g,"value"));
  else if(k=="resolved_choice")resolved=resolved&&!v.null()&&v!=J("unknown");
  else if(k=="distinct_dates")resolved=resolved&&v.isArray()&&v.array().size()==2&&date(v.array()[0])&&date(v.array()[1])&&v.array()[0]!=v.array()[1];
  else need(false,"SOURCE_REPORT_UNKNOWN_GUARD");
 }
 return resolved;
}
}
