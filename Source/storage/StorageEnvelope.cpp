#include "storage/StorageEnvelope.hpp"
#include "content/Canonical.hpp"
#include "platform/ProfileAccessMac.hpp"
#include <charconv>
#include <limits>
#include <numeric>
#include <regex>
#include <set>

namespace fathom::storage {
EnvelopeError::EnvelopeError(std::string c,std::string m):std::runtime_error(std::move(m)),code(std::move(c)){}
namespace {
void require(bool ok,const std::string& message){if(!ok)throw EnvelopeError("INVALID_ENVELOPE",message);}
const Value& at(const Value& v,const std::string& key){auto p=v.find(key);require(p!=nullptr,"Missing field: "+key);return *p;}
std::string text(const Value& v){require(v.isString(),"Expected string");return v.string();}
std::string str(const Value& v,const std::string& k){return text(at(v,k));}
void nonempty(const std::string& s){require(!s.empty()&&s.find_first_not_of(" \t\r\n")!=std::string::npos,"Expected nonempty text");}
void fields(const Value& v,std::initializer_list<const char*> names){require(v.isObject(),"Expected object");std::set<std::string> want;for(auto n:names)want.insert(n);std::set<std::string> got;for(const auto& p:v.object())got.insert(p.first);require(want==got,"Unexpected or missing fields");}
std::int64_t integer(const Value& v,std::int64_t minimum=0){std::int64_t n=0;require(v.integer(n)&&n>=minimum&&json::stringify(v)==std::to_string(n),"Expected bounded canonical integer");return n;}
void hash(const std::string& v){require(std::regex_match(v,std::regex("[0-9a-f]{64}")),"Expected SHA256");}
void namespaceId(const std::string& v,const std::string& prefix){require(std::regex_match(v,std::regex(prefix+"[0-9]{6}")),"Expected canonical stable identity");}
std::int64_t component(const Value& v,bool strings){if(!strings&&v.isNumber())return integer(v);auto s=text(v);require(std::regex_match(s,std::regex("0|[1-9][0-9]*")),"Noncanonical rational component");std::int64_t n=0;auto r=std::from_chars(s.data(),s.data()+s.size(),n);require(r.ec==std::errc{}&&r.ptr==s.data()+s.size(),"Rational component outside int64");return n;}
Rational rational(const Value& v,bool strings=false){require(v.isArray()&&v.array().size()==2,"Expected rational pair");auto n=component(v.array()[0],strings),d=component(v.array()[1],strings);require(d>0&&std::gcd(n,d)==1,"Expected reduced rational");return Rational(n,d);}
Rational difference(const Rational& b,const Rational& a){require(!(b<a),"Negative interval");auto g=std::gcd(a.denominator(),b.denominator());std::int64_t x=0,y=0,d=0;require(!__builtin_mul_overflow(b.numerator(),a.denominator()/g,&x)&&!__builtin_mul_overflow(a.numerator(),b.denominator()/g,&y)&&!__builtin_mul_overflow(b.denominator(),a.denominator()/g,&d),"Interval arithmetic outside int64");return Rational(x-y,d);}
Rational intervals(const Value& list){require(list.isArray(),"Expected interval array");Rational total;std::map<std::int64_t,Rational> ends;std::set<std::pair<std::int64_t,std::string>> ids;
 for(const auto& v:list.array()){
  const bool id=v.find("id")!=nullptr,duration=v.find("duration")!=nullptr;
  if(id)fields(v,{"id","generation","start","end"});else if(duration)fields(v,{"event","generation","start","end","duration"});else fields(v,{"event","generation","start","end"});
  auto token=str(v,id?"id":"event");nonempty(token);auto gen=integer(at(v,"generation"));require(ids.emplace(gen,token).second,"Duplicate confirmed interval");auto a=rational(at(v,"start")),b=rational(at(v,"end"));require(!(a<ends[gen]),"Overlapping confirmed interval");auto delta=difference(b,a);if(duration)require(rational(at(v,"duration"))==delta,"Duration mismatch");ends[gen]=b;total=total+delta;
 }return total;
}
void dates(const Value& v){auto utc=str(v,"practice_utc"),zone=str(v,"timezone");require(localDay(utc,zone)==str(v,"local_day"),"Practice local day mismatch");}
void assessment(const Value& v){if(v.null())return;auto s=text(v);require(s=="Struggling"||s=="Developing"||s=="Clean"||s=="Easy","Unknown self-assessment");}
void cycles(const Value& v){require(v.isArray(),"Expected completed cycle identities");std::set<std::string> seen;for(const auto& item:v.array()){if(item.isString())nonempty(item.string());else integer(item);require(seen.insert(canonical(item)).second,"Duplicate completed cycle identity");}}
void binding(const Value& raw,const Value& c){require(raw.isObject(),"Missing original canonical binding");require(str(raw,"id")==str(c,"item_id"),"Content owner mismatch");for(auto k:{"content_revision","content_version","source_manifest_sha256","source_refs"})require(at(raw,k)==at(c,k),"Pinned content mismatch");const auto& hashes=at(raw,"source_hashes");require(hashes.isObject(),"Expected source hash ledger");std::set<std::string> refs;for(const auto& r:at(c,"source_refs").array())refs.insert(text(r));require(refs.size()==hashes.object().size(),"Source hash coverage mismatch");for(const auto& p:hashes.object()){require(refs.count(p.first)==1,"Unknown source hash reference");hash(text(p.second));}}
std::string unhex(const std::string& s){require(s.size()%2==0,"Odd byte hex");std::string out;out.reserve(s.size()/2);for(std::size_t i=0;i<s.size();i+=2){auto digit=[](char c){return c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:-1;};auto a=digit(s[i]),b=digit(s[i+1]);require(a>=0&&b>=0,"Expected lowercase hex");out.push_back(static_cast<char>(a*16+b));}return out;}
}
std::string canonical(const Value& v){return json::stringify(v);}
Value parseCanonical(const std::string& bytes){auto v=json::parse(bytes);require(canonical(v)==bytes,"Expected exact storage-json.1 bytes; serialize before first seal");return v;}
void validateUuid(const std::string& v){require(std::regex_match(v,std::regex("[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")),"Expected lowercase UUIDv4");}
void validateContext(const Value& c,const std::string& kind,bool standalone){
 (void)parseCanonical(canonical(c));
 require(kind=="Attempt"||kind=="FreeplayActivity","Unknown activity kind");
 if(kind=="FreeplayActivity"){require(!standalone,"Freeplay cannot own source evidence");fields(c,{"configuration_version","configuration"});}
 else if(standalone)fields(c,{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs","configuration_version","configuration","span","target"});
 else{fields(c,{"session_id","item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs","configuration_version","configuration","span","target"});validateUuid(str(c,"session_id"));}
 integer(at(c,"configuration_version"),1);require(at(c,"configuration").isObject(),"Expected pinned configuration object");
 if(kind=="Attempt"){
  namespaceId(str(c,"item_id"),"fg:item:");namespaceId(str(c,"variant_id"),"fg:variant:");integer(at(c,"content_revision"),1);nonempty(str(c,"content_version"));hash(str(c,"source_manifest_sha256"));
  const auto& refs=at(c,"source_refs");require(refs.isArray()&&!refs.array().empty(),"Missing source references");std::set<std::string> seen;for(const auto& r:refs.array()){nonempty(text(r));require(seen.insert(text(r)).second,"Duplicate source reference");}
  require(at(c,"span").isObject()&&at(c,"target").isObject(),"Expected span and target objects");
  if(auto p=at(c,"target").find("cycles"))integer(*p,1);
 }
}
Envelope validateEnvelope(const std::string& bytes){
 Envelope e;e.value=parseCanonical(bytes);e.bytes=bytes;const auto& v=e.value;
 fields(v,{"storage_envelope_version","owner","kind","context","practice","result"});require(integer(at(v,"storage_envelope_version"),1)==1,"Unsupported storage envelope version");e.owner=str(v,"owner");validateUuid(e.owner);e.kind=str(v,"kind");const auto& c=at(v,"context");validateContext(c,e.kind);e.contextBytes=canonical(c);
 const auto& p=at(v,"practice");fields(p,{"practice_utc","timezone","local_day","active_seconds"});dates(p);e.practiceUtc=str(p,"practice_utc");e.timezone=str(p,"timezone");e.day=str(p,"local_day");e.active=rational(at(p,"active_seconds"),true);
 const auto& r=at(v,"result");fields(r,{"key","kind","content","configuration","active","completed_cycles","traversals","interruptions","intervals","selected_tempo","authored_tempo_ref","tempo_segments","assessment","outcome"});require(str(r,"key")==e.owner&&str(r,"kind")==e.kind,"Result original owner mismatch");require(rational(at(r,"active"))==e.active,"Active summary mismatch");require(at(r,"configuration")==at(c,"configuration"),"Configuration binding mismatch");
 if(e.kind=="Attempt"){binding(at(r,"content"),c);require(at(at(r,"configuration"),"canonical_variant_id")==at(c,"variant_id"),"Variant binding mismatch");}else require(at(r,"content").null(),"Freeplay cannot carry curriculum content");
 const auto resultOutcome=str(r,"outcome");require(resultOutcome=="stop"||resultOutcome=="natural"||resultOutcome=="interrupted_error"||resultOutcome=="interrupted_reopen","Unknown outcome");assessment(at(r,"assessment"));if(!at(r,"assessment").null())e.assessment=text(at(r,"assessment"));cycles(at(r,"completed_cycles"));for(auto k:{"traversals","interruptions","tempo_segments"})require(at(r,k).isArray(),"Expected practice ledger");require(intervals(at(r,"intervals"))==e.active,"Confirmed intervals do not equal active time");rational(at(r,"selected_tempo"));
 const auto* target=e.kind=="Attempt"?at(c,"target").find("cycles"):nullptr;
 if(target&&at(r,"completed_cycles").array().size()>=static_cast<std::uint64_t>(integer(*target,1)))e.outcome="complete";
 else if(resultOutcome=="interrupted_error"||resultOutcome=="interrupted_reopen")e.outcome="interrupted";
 else e.outcome=e.active.numerator()>0?"partial":"cancelled";
 e.digest=content::sha256(bytes);return e;
}
void validateCheckpoint(const std::string& owner,std::int64_t gen,std::int64_t seq,const std::string& bytes,const std::string& kind,const Value& c){
 validateUuid(owner);require(gen>=0&&seq>=0,"Invalid checkpoint position");auto v=parseCanonical(bytes);fields(v,{"owner","context","sequence","stopped_on_reopen","practice_snapshot","snapshot_practice","sealed_envelope"});require(str(v,"owner")==owner&&at(v,"context")==c&&integer(at(v,"sequence"))==seq&&at(v,"stopped_on_reopen")==Value(true),"Checkpoint binding mismatch");validateContext(c,kind);
 const auto& q=at(v,"practice_snapshot");fields(q,{"binding","config","context","attempt","generation","serial","cursor","attempt_config","active","intervals","completed","cycle","traversals","traversal","interruptions","segments","segment","tempo","selected_tempo","assessment","state","confirmed_at","pending","outcome","uncertain"});
 require(str(q,"attempt")==owner&&integer(at(q,"generation"))==gen,"Snapshot owner/generation mismatch");integer(at(q,"serial"));integer(at(q,"cycle"),1);require(str(q,"context")== (kind=="Attempt"?"lesson":"freeplay"),"Snapshot mode mismatch");require(at(q,"config").isObject()&&at(q,"attempt_config")==at(at(c,"configuration"),"values"),"Snapshot configuration mismatch");
 if(kind=="Attempt")binding(at(q,"binding"),c);else require(at(q,"binding").null(),"Freeplay snapshot content");
 auto active=rational(at(q,"active"));require(intervals(at(q,"intervals"))==active,"Snapshot active mismatch");cycles(at(q,"completed"));for(auto k:{"traversals","interruptions","segments"})require(at(q,k).isArray(),"Snapshot ledger required");for(auto k:{"cursor","tempo","selected_tempo"})rational(at(q,k));if(!at(q,"confirmed_at").null())rational(at(q,"confirmed_at"));assessment(at(q,"assessment"));auto state=str(q,"state");require(std::set<std::string>{"STOPPED","COUNT_IN","RUNNING","PAUSED","ENDED","ERROR"}.count(state)==1&&at(q,"uncertain").isBool(),"Snapshot state");
 const auto& p=at(v,"snapshot_practice");fields(p,{"practice_utc","timezone","local_day","active_seconds"});dates(p);require(rational(at(p,"active_seconds"),true)==active,"Snapshot date/active mismatch");
 if(!at(q,"pending").null()){
  const auto& sealed=at(v,"sealed_envelope");fields(sealed,{"bytes_hex","sha256"});auto data=unhex(str(sealed,"bytes_hex"));require(content::sha256(data)==str(sealed,"sha256"),"Sealed checkpoint digest");auto e=validateEnvelope(data);require(e.owner==owner&&e.contextBytes==canonical(c),"Sealed checkpoint context");const auto& r=at(e.value,"result");for(auto pair:{std::pair{"active","active"},{"intervals","intervals"},{"completed_cycles","completed"},{"traversals","traversals"},{"interruptions","interruptions"},{"tempo_segments","segments"}})require(at(r,pair.first)==at(q,pair.second),"Sealed checkpoint facts mismatch");
  const auto& pending=at(q,"pending");fields(pending,{"key","payload","digest"});auto raw=str(pending,"payload");require(str(pending,"key")==owner&&content::sha256(raw)==str(pending,"digest")&&json::parse(raw)==r,"Original raw pending mismatch");
 }else require(at(v,"sealed_envelope").null(),"Unbound sealed checkpoint");
}
void validateAttestation(const Value& v,const std::string& profileId,const std::optional<Value>& linked){
 fields(v,{"fact_id","item_id","content_revision","rubric_ref","take_id","work_id","performer_ref","practice_utc","timezone","local_day","attestation","context","owner"});validateUuid(str(v,"fact_id"));validateUuid(str(v,"performer_ref"));require(str(v,"performer_ref")==profileId,"Wrong local performer");dates(v);integer(at(v,"content_revision"),1);nonempty(str(v,"take_id"));nonempty(str(v,"work_id"));const auto& c=at(v,"context");validateContext(c,"Attempt",true);
 if(!at(v,"owner").null()){validateUuid(text(at(v,"owner")));require(linked.has_value(),"Missing linked Attempt");auto without=*linked;require(without.isObject(),"Missing linked context");without.object().erase("session_id");require(without==c,"Source fact context differs from original Attempt");}else require(!linked.has_value(),"Unexpected linked owner");
 require(at(v,"item_id")==at(c,"item_id")&&at(v,"content_revision")==at(c,"content_revision"),"Source fact content mismatch");const auto& ref=at(v,"rubric_ref");fields(ref,{"item_id","content_revision","content_version","source_rules_version","rubric_sha256"});for(auto k:{"item_id","content_revision","content_version"})require(at(ref,k)==at(c,k),"Rubric binding mismatch");nonempty(str(ref,"source_rules_version"));hash(str(ref,"rubric_sha256"));
 const auto& a=at(v,"attestation");require(a.isObject(),"Expected source attestation object");require(at(a,"performer_ref")==at(v,"performer_ref")&&at(a,"take")==at(v,"take_id")&&at(a,"work_ref")==at(v,"work_id"),"Source work/take/performer mismatch");require(at(a,"actual_work")==Value(true),"Explicit actual-work attestation required");auto role=str(a,"role"),who=str(a,"who");nonempty(who);require(role=="learner"||role=="human_reviewer","Attestation role");if(role=="learner")require(who==profileId,"Learner actor mismatch");
 if(auto q=a.find("independent");q&&!q->null()&&*q!=Value(false)){require(q->isObject(),"Independent review object required");auto reviewer=str(*q,"who");nonempty(reviewer);require(reviewer!=profileId&&str(*q,"take")==str(v,"take_id")&&str(*q,"role")=="human_reviewer"&&at(*q,"independent")==Value(true),"Independent same-take reviewer mismatch");}
}
void validateRuleObservation(const Value& v){
 fields(v,{"fact_id","rule_version","rule_config","rule_config_sha256","evidence_marker","evidence_sha256","content_selection","content_selection_sha256","as_of_utc","displayed_state","displayed_state_sha256"});validateUuid(str(v,"fact_id"));nonempty(str(v,"rule_version"));integer(at(v,"evidence_marker"));validateUtc(str(v,"as_of_utc"));hash(str(v,"evidence_sha256"));
 for(auto pair:{std::pair{"rule_config","rule_config_sha256"},{"content_selection","content_selection_sha256"},{"displayed_state","displayed_state_sha256"}}){auto b=str(v,pair.first);auto object=parseCanonical(b);require(object.isObject(),"Rule observation object required");require(content::sha256(b)==str(v,pair.second),"Rule observation digest mismatch");}
 require(str(parseCanonical(str(v,"rule_config")),"version")==str(v,"rule_version"),"Rule version mismatch");
}
} // namespace fathom::storage
