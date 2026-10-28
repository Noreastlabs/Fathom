#include "progression/ProgressionAdapter.hpp"
#include "storage/SuiteReview.hpp"
#include "content/Canonical.hpp"
#include <regex>
#include <set>

namespace fathom::progression {
namespace {
using A=Value::Array;using O=Value::Object;
void need(bool b,const std::string& why){if(!b)throw HistoryError(why);}
const Value& f(const Value& v,const std::string& k){auto p=v.find(k);need(p!=nullptr,"Missing "+k);return *p;}
std::string text(const Value& v){need(v.isString(),"Expected text");return v.string();}
std::int64_t integer(const Value& v,std::int64_t min=0){std::int64_t n;need(v.integer(n)&&n>=min,"Invalid integer");return n;}
std::string bytes(const Value& v){auto s=text(f(v,"blob_hex"));need(s.size()%2==0,"Invalid blob length");std::string out;auto nibble=[](char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;throw HistoryError("Invalid blob hex");};for(std::size_t i=0;i<s.size();i+=2)out.push_back(static_cast<char>(nibble(s[i])*16+nibble(s[i+1])));return out;}
const A& row(const Value& v,std::size_t n){need(v.isArray()&&v.array().size()==n,"Invalid snapshot row shape");return v.array();}
const A& table(const Value& a,const std::string& name){const auto& v=f(a,name);need(v.isArray(),"Invalid snapshot table");return v.array();}
std::string hash(const Value& v){return content::sha256(storage::canonical(v));}
void exactFields(const Value& v,std::initializer_list<const char*> ks){need(v.isObject()&&v.object().size()==ks.size(),"Unsupported coverage/ledger fields");for(auto k:ks)f(v,k);}
std::set<std::string> tokenSet(const A& a){std::set<std::string> out;for(auto& v:a){need(v.isString()||v.isNumber(),"Invalid cycle token");if(v.isString())need(!v.string().empty(),"Empty cycle token");else integer(v);need(out.insert(storage::canonical(v)).second,"Duplicate cycle token");}return out;}
bool positive(const Rational& q){return q.numerator()>0;}
Value originalCondition(const Value& c){const auto& config=f(c,"configuration");auto p=config.find("progression_condition");if(!p)return {};validateCondition(*p);for(auto pair:{std::pair{"variant","variant_id"},{"revision","content_revision"},{"content_version","content_version"},{"span","span"},{"target","target"}})need(f(*p,pair.first)==f(c,pair.second),"Original comparability context conflict");return *p;}
void parseAttempt(Evidence& out,const storage::Envelope& e,const Value* coverage,A& notices){
    const auto& c=f(e.value,"context");const auto& raw=f(e.value,"result");out.item=text(f(c,"item_id"));out.session=text(f(c,"session_id"));out.condition=originalCondition(c);out.sourceScope=sourceScope(c);out.assessment=f(raw,"assessment");out.completedCycles=f(raw,"completed_cycles").array();auto cycles=tokenSet(out.completedCycles);const auto& traversals=f(raw,"traversals").array();std::set<std::string> full;
    const auto& span=f(c,"span");auto spanStart=span.find("start"),spanEnd=span.find("end");need((spanStart==nullptr)==(spanEnd==nullptr),"Incomplete original span extent");bool extentKnown=spanStart&&spanEnd;if(extentKnown)need(quantity(*spanStart)<quantity(*spanEnd),"Invalid original span extent");
    for(auto& v:traversals){exactFields(v,{"cycle","start","end","status"});auto start=quantity(f(v,"start")),end=quantity(f(v,"end"));need(!(end<start),"Traversal end precedes start");auto status=text(f(v,"status"));need(status=="complete"||status=="partial_suffix"||status=="partial_interrupted"||status=="partial_ended"||status=="partial_recovered","Unsupported finalized traversal status");tokenSet(A{f(v,"cycle")});auto id=storage::canonical(f(v,"cycle"));if(status=="complete"){need(full.insert(id).second&&cycles.count(id),"Conflicting or unconfirmed complete traversal");if(auto p=f(c,"span").find("start")){auto q=f(c,"span").find("end");need(q&&start==quantity(*p)&&end==quantity(*q),"Complete traversal differs from original span");}} // Earlier partial traversal of this cycle remains partial when a later full replay completes it.
    }
    bool traversalProof=extentKnown&&full==cycles&&(!cycles.empty()||traversals.empty());if(!traversalProof)notices.emplace_back(A{out.key,"Missing complete traversal proof; no whole-target credit"});
    std::int64_t target=0;if(auto p=f(c,"target").find("cycles"))target=integer(*p,1);auto outcome=text(f(raw,"outcome"));out.complete=!out.condition.null()&&positive(out.active)&&target>0&&cycles.size()>=static_cast<std::size_t>(target)&&traversalProof&&(outcome=="natural"||outcome=="stop");
    const auto& rawSegments=f(raw,"tempo_segments").array();Rational total;bool uniform=true;std::optional<Rational> tempo;
    for(auto& v:rawSegments){exactFields(v,{"tempo","start_at","end_at","confirmed_duration"});Segment s{quantity(f(v,"tempo")),quantity(f(v,"confirmed_duration")),false,{}};need(positive(s.tempo),"Nonpositive segment tempo");auto start=quantity(f(v,"start_at")),end=quantity(f(v,"end_at"));need(start+s.active==end,"Segment duration mismatch");total=total+s.active;if(positive(s.active)){if(tempo&&!(s.tempo==*tempo))uniform=false;tempo=s.tempo;}out.segments.push_back(s);}
    bool segmentProof=total==out.active;if(!segmentProof){need(rawSegments.empty(),"Segment total differs from confirmed active time");notices.emplace_back(A{out.key,"Missing confirmed tempo segments; no tempo credit"});}
    if(out.condition.null())notices.emplace_back(A{out.key,"Original comparability metadata unavailable; history remains unbound"});
    if(coverage){
        exactFields(*coverage,{"kind","version","original_owner","generation","envelope_sha256","condition_sha256","segments"});need(integer(f(*coverage,"version"),1)==1,"Unsupported tempo coverage version");need(text(f(*coverage,"original_owner"))==out.key&&text(f(*coverage,"envelope_sha256"))==e.digest,"Coverage original envelope mismatch");need(!out.condition.null()&&text(f(*coverage,"condition_sha256"))==hash(out.condition),"Coverage original condition mismatch");auto generation=integer(f(*coverage,"generation"));const auto& intervals=f(raw,"intervals").array();std::set<std::int64_t> indices;std::set<std::string> covered;
        for(auto& v:f(*coverage,"segments").array()){exactFields(v,{"index","intervals","cycles"});auto index=integer(f(v,"index"));need(static_cast<std::size_t>(index)<out.segments.size()&&indices.insert(index).second,"Invalid/duplicate covered segment");auto& s=out.segments[static_cast<std::size_t>(index)];need(positive(s.active)&&segmentProof&&traversalProof,"Coverage lacks confirmed segment/traversals");std::set<std::int64_t> intervalIndices;Rational duration;for(auto& iv:f(v,"intervals").array()){auto i=integer(iv);need(static_cast<std::size_t>(i)<intervals.size()&&intervalIndices.insert(i).second,"Invalid/duplicate coverage interval");auto& interval=intervals[static_cast<std::size_t>(i)];need(integer(f(interval,"generation"))==generation,"Coverage interval generation mismatch");auto start=quantity(f(interval,"start")),end=quantity(f(interval,"end"));need(start<end,"Coverage interval must be positive");if(auto d=interval.find("duration"))duration=duration+quantity(*d);else{ // Exact subtraction through checked rational components, with no float inference.
                    auto n1=end.numerator(),n2=start.numerator(),d1=end.denominator(),d2=start.denominator();
                    __int128 n=static_cast<__int128>(n1)*d2-static_cast<__int128>(n2)*d1,denominator=static_cast<__int128>(d1)*d2;
                    need(n>=0&&n<=INT64_MAX&&denominator<=INT64_MAX,"Coverage interval arithmetic overflow");duration=duration+Rational(static_cast<std::int64_t>(n),static_cast<std::int64_t>(denominator));
                }}need(!intervalIndices.empty()&&!(duration<s.active),"Coverage interval duration insufficient");s.cycles=f(v,"cycles").array();auto ids=tokenSet(s.cycles);need(!ids.empty(),"Empty covered cycles");for(auto& id:ids)need(cycles.count(id)&&covered.insert(id).second,"Unconfirmed/repeated covered cycle");s.wholeTarget=target>0&&ids.size()>=static_cast<std::size_t>(target);
        }
    }else if(out.complete&&uniform&&tempo&&segmentProof){ // Same exact tempo over the entire confirmed target; no mixed-tempo join inferred.
        Segment whole{*tempo,out.active,true,out.completedCycles};out.segments.push_back(std::move(whole));
    }else if(!uniform&&positive(out.active))notices.emplace_back(A{out.key,"Mixed-tempo cycle coverage unavailable; attempted tempo only"});
}
}
Value sourceScope(const Value& c){O out;for(auto k:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs","span","target"})out.emplace(k,f(c,k));return out;}
bool supportsSourceFact(const Value& v){try{
    const auto& ref=f(v,"rubric_ref");const auto& c=f(v,"context");
    if(text(f(ref,"source_rules_version"))!="sha256:"+sourceRulesIdentity())return false;
    // Registered accepted historical source definition. This does not admit
    // executable curriculum or assert equivalence for a later content version.
    if(f(c,"content_revision")!=Value::fromInteger(1)||f(c,"content_version")!=Value("control-examples.1")||
       f(c,"source_manifest_sha256")!=Value("e856ef05e610b9be51f33aac661a900301f747a9259bfcbd951b756a247504fe"))return false;
    for(auto& r:f(sourceRules(),"records").array())if(f(r,"id")==f(v,"item_id")){
        auto refs=f(r,"source_refs");
        return text(f(ref,"rubric_sha256"))==hash(f(r,"rubric"))&&f(c,"source_refs")==refs&&
            f(c,"span")==Value(O{{"kind","source_task"},{"source_refs",refs}})&&
            f(c,"target")==Value(O{{"kind","source_attestation"},{"rubric_item_id",f(r,"id")}});
    }
    return false;
}catch(const std::exception&){return false;}}
SnapshotEvidence adaptSnapshot(const storage::Reply& reply){
    need(reply.status==storage::Status::Confirmed,"Projection requires confirmed authoritative snapshot: "+reply.code);const auto& d=reply.data;const auto& authority=f(d,"authoritative");SnapshotEvidence out;out.profile=text(f(d,"profile_id"));out.marker=integer(f(d,"committed_seq"));out.evidenceHash=text(f(d,"evidence_sha256"));out.snapshotHash=text(f(d,"snapshot_sha256"));need(hash(authority)==out.snapshotHash,"Snapshot identity mismatch");auto evidence=authority;evidence.object().erase("rule_observation");need(hash(evidence)==out.evidenceHash,"Evidence identity mismatch");need((text(f(d,"schema_sha256"))==storage::ProfileStore::schemaIdentity()||text(f(d,"schema_sha256"))==storage::ProfileStore::legacySchemaIdentity()),"Unsupported profile schema");
    std::map<std::string,std::pair<std::string,Value>> allocations;for(auto& v:table(authority,"identity")){auto& r=row(v,5);auto owner=text(r[0]);storage::validateUuid(owner);auto kind=text(r[1]);auto context=storage::parseCanonical(bytes(r[4]));storage::validateContext(context,kind);need(allocations.emplace(owner,std::make_pair(kind,context)).second,"Duplicate allocated owner");}
    auto suiteProjection=storage::suite::projection(authority);auto& deferred=f(suiteProjection,"assessments");
    std::map<std::string,Value> coverage;for(auto& v:table(authority,"late_evidence")){auto& r=row(v,5);auto b=bytes(r[3]);need(content::sha256(b)==text(r[4]),"Late evidence digest mismatch");auto value=storage::parseCanonical(b);need(f(value,"original_owner")==r[1],"Late owner mismatch");out.originalHistory.emplace_back(O{{"kind","LateEvidence"},{"owner",r[1]},{"fact_id",r[0]},{"received_utc",r[2]},{"bytes",b},{"sha256",r[4]}});auto k=value.find("kind");if(k&&*k==Value("progression_tempo_coverage")){auto owner=text(r[1]);auto old=coverage.find(owner);need(old==coverage.end()||old->second==value,"Conflicting original tempo coverage");coverage[owner]=value;}}
    std::set<std::string> finalized;for(auto& v:table(authority,"finalized")){auto& r=row(v,11);auto b=bytes(r[1]);auto e=storage::validateEnvelope(b);need(e.owner==text(r[0])&&e.digest==text(r[2])&&finalized.insert(e.owner).second,"Finalized owner/digest conflict");auto a=allocations.find(e.owner);need(a!=allocations.end()&&a->second.first==e.kind&&storage::canonical(a->second.second)==e.contextBytes,"Finalized allocated context mismatch");Evidence item;item.kind=e.kind=="Attempt"?Kind::Attempt:Kind::Freeplay;item.key=e.owner;item.originalBytes=b;item.at=e.practiceUtc;item.timezone=e.timezone;item.day=e.day;item.active=e.active;
        if(item.kind==Kind::Attempt){auto c=coverage.find(e.owner);parseAttempt(item,e,c==coverage.end()?nullptr:&c->second,out.notices);if(auto review=deferred.find(e.owner)){item.assessment=f(*review,"score");out.notices.emplace_back(A{e.owner,"Deferred suite self-assessment; original capture unchanged"});}}out.originalHistory.emplace_back(O{{"kind",e.kind},{"owner",e.owner},{"bytes",b},{"sha256",e.digest}});out.records.push_back(std::move(item));
    }
    for(auto& kv:allocations)if(!finalized.count(kv.first))out.notices.emplace_back(A{kv.first,"unresolved save"});
    for(auto& v:table(authority,"acknowledgment")){auto& r=row(v,5);Evidence item;item.kind=Kind::Acknowledgment;item.key=text(r[0]);storage::validateUuid(item.key);item.item=text(r[1]);integer(r[2],1);item.at=text(r[3]);item.originalBytes=storage::canonical(v);out.records.push_back(std::move(item));}
    for(auto& v:table(authority,"source_attestation")){auto& r=row(v,15);auto b=bytes(r[12]);auto value=storage::parseCanonical(b);need(content::sha256(b)==text(r[13])&&f(value,"fact_id")==r[0],"Source original digest mismatch");std::optional<Value> linked;if(!f(value,"owner").null()){auto a=allocations.find(text(f(value,"owner")));need(a!=allocations.end()&&a->second.first=="Attempt","Source owner unavailable");linked=a->second.second;}storage::validateAttestation(value,out.profile,linked);out.originalHistory.emplace_back(O{{"kind","Source"},{"owner",f(value,"fact_id")},{"bytes",b},{"sha256",r[13]}});if(!supportsSourceFact(value)){out.notices.emplace_back(A{f(value,"fact_id"),"Unsupported exact source rubric/version; fact preserved without completion credit"});continue;}Evidence item;item.kind=Kind::Source;item.key=text(f(value,"fact_id"));item.originalBytes=b;item.item=text(f(value,"item_id"));item.at=text(f(value,"practice_utc"));item.timezone=text(f(value,"timezone"));item.day=text(f(value,"local_day"));item.sourceScope=sourceScope(f(value,"context"));item.attestation=f(value,"attestation");out.records.push_back(std::move(item));}
    if(auto facts=authority.find("suite_fact"))for(auto& row: facts->array())out.originalHistory.emplace_back(O{{"kind","SuiteReviewFact"},{"owner",row.array()[0]},{"bytes",bytes(row.array()[5])},{"sha256",row.array()[6]}});
    out.historicalObservations=table(authority,"rule_observation");return out;
}
void validateQuery(const Query& q){
    need(std::regex_match(q.item,std::regex("fg:item:[0-9]{6}")),"Invalid canonical query item");
    if(!q.condition.null()){
        validateCondition(q.condition);
        need(std::regex_match(text(f(q.condition,"variant")),std::regex("fg:variant:[0-9]{6}")),"Invalid canonical query variant");
    }else need(q.sourceScope.isObject(),"Source-only query requires exact source scope");
    if(!q.sourceScope.null()){
        exactFields(q.sourceScope,{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs","span","target"});
        need(f(q.sourceScope,"item_id")==Value(q.item),"Selected source item mismatch");
        need(std::regex_match(text(f(q.sourceScope,"variant_id")),std::regex("fg:variant:[0-9]{6}")),"Invalid source variant");
        integer(f(q.sourceScope,"content_revision"),1);
        need(!text(f(q.sourceScope,"content_version")).empty()&&std::regex_match(text(f(q.sourceScope,"source_manifest_sha256")),std::regex("[0-9a-f]{64}")),"Invalid source version/manifest");
        need(f(q.sourceScope,"source_refs").isArray()&&!f(q.sourceScope,"source_refs").array().empty()&&f(q.sourceScope,"span").isObject()&&f(q.sourceScope,"target").isObject(),"Invalid source scope");
        for(auto& ref:f(q.sourceScope,"source_refs").array())need(!text(ref).empty(),"Empty source ref");
        if(!q.condition.null())for(auto pair:{std::pair{"variant_id","variant"},{"content_revision","revision"},{"content_version","content_version"},{"span","span"},{"target","target"}})need(f(q.sourceScope,pair.first)==f(q.condition,pair.second),"Selected source scope mismatch");
    }
}
Value projectSnapshot(const SnapshotEvidence& snapshot,const std::vector<Query>& queries,const std::string& asOf){
    A selection,views;std::set<std::string> keys;for(auto& q:queries){validateQuery(q);auto qv=queryValue(q);need(keys.insert(storage::canonical(qv)).second,"Duplicate selected condition");selection.emplace_back(qv);views.emplace_back(O{{"query",qv},{"projection",project(snapshot.records,q,asOf)}});}
    return O{{"projection_version",Value::fromInteger(1)},{"profile_id",snapshot.profile},{"evidence_marker",Value::fromInteger(snapshot.marker)},{"evidence_sha256",snapshot.evidenceHash},{"snapshot_sha256",snapshot.snapshotHash},{"selection",selection},{"selection_sha256",hash(selection)},{"rules",initialRules()},{"rules_sha256",rulesIdentity()},{"source_rules_sha256",sourceRulesIdentity()},{"as_of",asOf},{"views",views},{"notices",snapshot.notices},{"original_history",snapshot.originalHistory},{"historical_observations",snapshot.historicalObservations}};
}
} // namespace fathom::progression
