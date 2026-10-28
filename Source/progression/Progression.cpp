#include "progression/Progression.hpp"
#include "content/Canonical.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "ProgressionRules.generated.hpp"
#include <algorithm>
#include <charconv>
#include <ctime>
#include <iomanip>
#include <limits>
#include <set>
#include <sstream>

namespace fathom::progression {
namespace {
using A=Value::Array; using O=Value::Object;
void need(bool ok,const std::string& why){if(!ok)throw HistoryError(why);}
const Value& f(const Value& v,const std::string& k){auto p=v.find(k);need(p!=nullptr,"Missing "+k);return *p;}
Value opt(const Value& v,const std::string& k){auto p=v.find(k);return p?*p:Value{};}
std::string text(const Value& v){need(v.isString(),"Expected text");return v.string();}
std::int64_t integer(const Value& v,std::int64_t minimum=0){std::int64_t n;need(v.integer(n)&&n>=minimum,"Invalid integer");return n;}
bool yes(const Value& v){return v==Value(true);}
bool nonempty(const Value& v){return v.isString()&&!v.string().empty();}
std::int64_t component(const Value& v){if(!v.isString()){need(!v.isNumber()||std::get<json::Number>(v.data).token!="-0","Negative zero quantity");return integer(v);}auto& s=v.string();need(!s.empty()&&(s=="0"||s.front()!='0')&&s.find_first_not_of("0123456789")==std::string::npos,"Noncanonical quantity component");std::int64_t n=0;auto r=std::from_chars(s.data(),s.data()+s.size(),n);need(r.ec==std::errc{}&&r.ptr==s.data()+s.size()&&n>=0,"Invalid quantity component");return n;}
std::set<std::string> tokens(const A& a){std::set<std::string> s;for(auto& v:a){need(v.isString()||v.isNumber(),"Invalid cycle token");if(v.isString())need(!v.string().empty(),"Empty cycle token");else integer(v);need(s.insert(json::stringify(v)).second,"Duplicate completed traversal");}return s;}
Value rowValue(const Evidence& r){A segments;for(auto& s:r.segments)segments.emplace_back(O{{"tempo",quantityValue(s.tempo)},{"active",quantityValue(s.active)},{"whole",s.wholeTarget},{"cycles",s.cycles}});return O{{"kind",Value::fromInteger(static_cast<int>(r.kind))},{"key",r.key},{"original",r.originalBytes},{"status",r.status},{"item",r.item},{"session",r.session},{"at",r.at},{"timezone",r.timezone},{"day",r.day},{"condition",r.condition},{"scope",r.sourceScope},{"assessment",r.assessment},{"attestation",r.attestation},{"active",quantityValue(r.active)},{"complete",r.complete},{"cycles",r.completedCycles},{"segments",segments}};}
using Rows=std::vector<const Evidence*>;
bool before(const Evidence* a,const Evidence* b){auto ta=utcMicros(a->at),tb=utcMicros(b->at);return ta==tb?a->key<b->key:ta<tb;}
bool success(const Evidence* r){return r->complete&&(r->assessment==Value("Clean")||r->assessment==Value("Easy"));}
bool enough(const Rows& rows,const Value& rule){std::set<std::string> days,sessions;for(auto r:rows){days.insert(r->day);sessions.insert(r->session);}return rows.size()>=static_cast<std::size_t>(integer(f(rule,"attempts"),1))&&days.size()>=static_cast<std::size_t>(integer(f(rule,"days"),1))&&sessions.size()>=static_cast<std::size_t>(integer(f(rule,"sessions"),1));}
bool scoreValid(const Value& scores,const Value& rubric,const Value& total){if(!scores.isObject())return false;auto& ds=f(rubric,"dimensions").array();if(scores.object().size()!=ds.size())return false;std::int64_t sum=0;for(auto& d:ds){auto p=scores.find(text(f(d,"name")));std::int64_t n;if(!p||!p->integer(n)||n<0||n>=static_cast<std::int64_t>(f(d,"anchors").array().size()))return false;sum+=n;}std::int64_t n;return total.null()||(total.integer(n)&&n==sum);}
bool scorePass(const Value& scores,const Value& rubric,const Value& total){if(!scoreValid(scores,rubric,total))return false;std::int64_t sum=0;for(auto& kv:scores.object())sum+=integer(kv.second);if(sum<integer(f(rubric,"minimum_total")))return false;for(auto& k:f(rubric,"protected_nonzero").array())if(integer(f(scores,text(k)))==0)return false;return true;}
bool assertions(const Value& object,const Value& names){for(auto& n:names.array())if(!yes(opt(object,text(n))))return false;return true;}
Value sourcePass(const std::string& item,const Rows& rows){
    const Value* record=nullptr;for(auto& v:f(sourceRules(),"records").array())if(f(v,"id")==Value(item))record=&v;
    if(!record)return O{{"complete",false},{"applicable",false},{"passing",A{}},{"worked",A{}},{"reasons",A{}}};
    const auto& rubric=f(*record,"rubric");auto level=integer(f(*record,"legacy_level"));std::string rid=level==48?"R48":level==97?"R97C":level==105?"R105":"";
    const Value* resource=nullptr;for(auto& v:f(sourceRules(),"resources").array())if(f(v,"id")==Value(rid))resource=&v;
    Rows passing; A worked,reasons;
    for(auto r:rows){auto& a=r->attestation;if(a.null())continue;bool valid=yes(opt(a,"actual_work"));for(auto k:{"performer_ref","who","take","work_ref"})valid=valid&&nonempty(opt(a,k));auto role=opt(a,"role");valid=valid&&(role==Value("learner")||role==Value("human_reviewer"));auto scores=opt(a,"scores"),total=opt(a,"total");valid=valid&&(scores.null()||scoreValid(scores,rubric,total));auto access=opt(opt(a,"resources"),rid);
        if(!rid.empty())valid=valid&&yes(opt(access,"actual_access"))&&nonempty(opt(access,"work_ref"));
        if(valid)worked.emplace_back(r->key);
        bool ok=valid&&scorePass(scores,rubric,total)&&assertions(opt(a,"obligations"),f(rubric,"required_obligations"));
        if(resource)ok=ok&&assertions(opt(access,"constraints"),f(*resource,"selection_constraints"))&&assertions(opt(access,"outputs"),f(*resource,"required_outputs"));
        if(level==48)ok=ok&&nonempty(opt(a,"recording_ref"));
        if(level==97)ok=ok&&yes(opt(a,"unfamiliar"))&&nonempty(opt(a,"excerpt"))&&opt(a,"familiar_self_created")==Value(false);
        if(ok)passing.push_back(r);else reasons.emplace_back(A{r->key,"incomplete or invalid source attestation"});
    }
    std::set<std::string> takes,days,recordings,excerpts;A ids;
    for(auto r:passing)if(takes.insert(text(f(r->attestation,"take"))).second){ids.emplace_back(r->key);days.insert(r->day);if(level==48)recordings.insert(text(f(r->attestation,"recording_ref")));if(level==97)excerpts.insert(text(f(r->attestation,"excerpt")));}
    bool complete=level==97?excerpts.size()>=2:days.size()>=2;
    if(level==48)complete=complete&&recordings.size()>=2;
    if(level==105)for(auto r:passing){const auto& a=r->attestation;auto q=opt(a,"independent");complete=complete||(opt(q,"role")==Value("human_reviewer")&&yes(opt(q,"independent"))&&nonempty(opt(q,"who"))&&opt(q,"who")!=opt(a,"performer_ref")&&opt(q,"take")==opt(a,"take")&&scorePass(opt(q,"scores"),rubric,opt(q,"total")));}
    return O{{"complete",complete},{"applicable",true},{"passing",ids},{"worked",worked},{"reasons",reasons}};
}
std::int64_t addDays(std::int64_t at,std::int64_t days){constexpr std::int64_t day=86400000000LL;need(days>=0&&days<=std::numeric_limits<std::int64_t>::max()/day,"Review interval overflow");auto delta=days*day;need(at<=std::numeric_limits<std::int64_t>::max()-delta,"Review date overflow");return at+delta;}
}
const Value& initialRules(){static const auto v=json::parse(progressionInitialRules);return v;}
const Value& sourceRules(){static const auto v=json::parse(progressionSourceRules);return v;}
std::string rulesIdentity(){return content::sha256(progressionInitialRules);}
std::string sourceRulesIdentity(){return content::sha256(progressionSourceRules);}
Rational quantity(const Value& v){need(v.isArray()&&v.array().size()==2,"Expected exact quantity pair");auto n=component(v.array()[0]),d=component(v.array()[1]);need(d>0,"Zero quantity denominator");Rational r(n,d);need(r.numerator()==n&&r.denominator()==d,"Unreduced quantity");return r;}
Value quantityValue(const Rational& r){return A{std::to_string(r.numerator()),std::to_string(r.denominator())};}
std::int64_t utcMicros(const std::string& s){storage::validateUtc(s);std::tm t{};t.tm_year=std::stoi(s.substr(0,4))-1900;t.tm_mon=std::stoi(s.substr(5,2))-1;t.tm_mday=std::stoi(s.substr(8,2));t.tm_hour=std::stoi(s.substr(11,2));t.tm_min=std::stoi(s.substr(14,2));t.tm_sec=std::stoi(s.substr(17,2));auto original=t;auto seconds=timegm(&t);std::tm back{};need(gmtime_r(&seconds,&back)!=nullptr&&back.tm_year==original.tm_year&&back.tm_mon==original.tm_mon&&back.tm_mday==original.tm_mday&&back.tm_hour==original.tm_hour&&back.tm_min==original.tm_min&&back.tm_sec==original.tm_sec,"Unsupported UTC civil conversion");need(seconds>=std::numeric_limits<std::int64_t>::min()/1000000&&seconds<=std::numeric_limits<std::int64_t>::max()/1000000,"UTC overflow");std::int64_t micro=0;if(s.size()>20){auto digits=s.substr(20,s.size()-21);need(digits.size()<=6,"UTC precision exceeds microseconds");digits.append(6-digits.size(),'0');micro=std::stoll(digits);}need(seconds*1000000<=std::numeric_limits<std::int64_t>::max()-micro,"UTC overflow");return seconds*1000000+micro;}
std::string utcString(std::int64_t micros){auto seconds=micros/1000000,part=micros%1000000;if(part<0){--seconds;part+=1000000;}std::time_t t=seconds;std::tm tm{};need(gmtime_r(&t,&tm)!=nullptr,"UTC conversion failed");char out[32];need(std::strftime(out,sizeof(out),"%Y-%m-%dT%H:%M:%S",&tm)>0,"UTC formatting failed");std::ostringstream s;s<<out;if(part)s<<'.'<<std::setw(6)<<std::setfill('0')<<part;s<<'Z';storage::validateUtc(s.str());return s.str();}
void validateCondition(const Value& v){static const std::set<std::string> keys={"variant","revision","content_version","setup","span","beat_unit","grouping","technique","target"};need(v.isObject()&&v.object().size()==keys.size(),"Invalid comparability condition");for(auto& k:keys)need(v.find(k)&&!f(v,k).null(),"Missing comparability "+k);integer(f(v,"revision"),1);need(nonempty(f(v,"variant"))&&nonempty(f(v,"content_version"))&&f(v,"target").isObject(),"Invalid condition identity/target");if(auto p=f(v,"target").find("cycles"))integer(*p,1);}
Value queryValue(const Query& q){return O{{"item",q.item},{"condition",q.condition},{"source_scope",q.sourceScope}};}
Value project(const std::vector<Evidence>& input,const Query& query,const std::string& asOf,const Value& rules){
    if(query.condition.null())need(query.sourceScope.isObject(),"Source-only query requires exact source scope");else validateCondition(query.condition);need(query.item.rfind("fg:item:",0)==0,"Invalid canonical item");auto now=utcMicros(asOf);for(auto k:{"proficient","mastered","reliable"})for(auto n:{"attempts","days","sessions"})integer(f(f(rules,k),n),1);for(auto& kv:f(rules,"review_days").object())integer(kv.second,1);auto lookback=integer(f(rules,"weak_lookback_days"),1);need(nonempty(f(rules,"version")),"Missing rule version");
    std::map<std::string,std::string> seen;Rows data;A notices;
    for(auto& r:input){need(!r.key.empty()&&!r.originalBytes.empty(),"Missing original identity");auto payload=json::stringify(rowValue(r));auto old=seen.find(r.key);if(old!=seen.end()){need(old->second==payload,"Conflicting original identity");continue;}seen.emplace(r.key,payload);need(r.status=="committed"||r.status=="pending"||r.status=="uncertain","Invalid commit status");if(r.status!="committed"){notices.emplace_back(A{r.key,"unresolved save"});continue;}need(r.kind==Kind::Attempt||r.kind==Kind::Freeplay||r.kind==Kind::Acknowledgment||r.kind==Kind::Source,"Invalid evidence kind");auto at=utcMicros(r.at);if(r.kind!=Kind::Acknowledgment){need(storage::localDay(r.at,r.timezone)==r.day,"Invalid practice day");if(r.kind==Kind::Attempt||r.kind==Kind::Freeplay)need(!r.session.empty()||r.kind==Kind::Freeplay,"Missing Session");}if(r.kind!=Kind::Freeplay)need(r.item.rfind("fg:item:",0)==0,"Invalid canonical reference");need(r.assessment.null()||r.assessment==Value("Struggling")||r.assessment==Value("Developing")||r.assessment==Value("Clean")||r.assessment==Value("Easy"),"Invalid assessment");
        if(r.kind==Kind::Attempt){if(!r.condition.null())validateCondition(r.condition);auto cs=tokens(r.completedCycles);std::int64_t target=0;if(!r.condition.null())if(auto p=f(r.condition,"target").find("cycles"))target=integer(*p,1);if(r.complete)need(!r.condition.null()&&(target==0||cs.size()>=static_cast<std::size_t>(target)),"Complete target lacks confirmed traversals");for(auto& s:r.segments){need(s.tempo.numerator()>0,"Invalid tempo");auto seg=tokens(s.cycles);for(auto& c:seg)need(cs.count(c)>0,"Unconfirmed traversal");if(s.wholeTarget&&target>0)need(seg.size()>=static_cast<std::size_t>(target),"Whole target lacks traversals");}}
        if(at>now){notices.emplace_back(A{r.key,"future practice excluded"});continue;}data.push_back(&r);
    }
    std::sort(data.begin(),data.end(),before);std::sort(notices.begin(),notices.end(),[](const Value&a,const Value&b){return json::stringify(a)<json::stringify(b);});Rows rows,positive,successful,sourceRows;bool ack=false;Rational attempted;bool hasAttempted=false;
    for(auto r:data){if(r->item!=query.item)continue;if(r->kind==Kind::Acknowledgment)ack=true;if(r->kind==Kind::Attempt&&!query.condition.null()&&r->condition==query.condition){rows.push_back(r);if(r->active.numerator()>0){positive.push_back(r);if(success(r))successful.push_back(r);}sourceRows.push_back(r);for(auto& s:r->segments)if(s.active.numerator()>0&&(!hasAttempted||attempted<s.tempo)){attempted=s.tempo;hasAttempted=true;}}
        if(r->kind==Kind::Source&&!query.sourceScope.null()&&r->sourceScope==query.sourceScope)sourceRows.push_back(r);
    }
    std::sort(sourceRows.begin(),sourceRows.end(),before);auto src=sourcePass(query.item,sourceRows);std::string state=ack?"Introduced":"Not Started";if(!positive.empty()||!f(src,"worked").array().empty())state="Practicing";if(!yes(f(src,"applicable"))||yes(f(src,"complete"))){if(enough(successful,f(rules,"proficient")))state="Proficient";if(enough(successful,f(rules,"mastered")))state="Mastered";}
    std::vector<Rational> candidates;std::map<std::string,std::vector<Rational>> tempos;for(auto r:successful)for(auto& s:r->segments)if(s.wholeTarget&&s.active.numerator()>0&&!s.cycles.empty()){candidates.push_back(s.tempo);tempos[r->key].push_back(s.tempo);}std::sort(candidates.begin(),candidates.end(),[](const Rational&a,const Rational&b){return b<a;});candidates.erase(std::unique(candidates.begin(),candidates.end()),candidates.end());Value pb=candidates.empty()?Value{}:quantityValue(candidates.front()),reliable;
    for(auto& t:candidates){Rows supporting;for(auto r:successful)if(std::any_of(tempos[r->key].begin(),tempos[r->key].end(),[&](const Rational& v){return !(v<t);}))supporting.push_back(r);if(enough(supporting,f(rules,"reliable"))){reliable=quantityValue(t);break;}}
    Rows anchors=successful,work=positive;std::set<std::string> passIds,workIds;for(auto& v:f(src,"passing").array())passIds.insert(text(v));for(auto& v:f(src,"worked").array())workIds.insert(text(v));for(auto r:sourceRows){if(passIds.count(r->key))anchors.push_back(r);if(workIds.count(r->key))work.push_back(r);}std::optional<std::int64_t> anchor,due;if(!anchors.empty())anchor=utcMicros((*std::max_element(anchors.begin(),anchors.end(),before))->at);else if(!work.empty())anchor=utcMicros((*std::min_element(work.begin(),work.end(),before))->at);auto interval=opt(f(rules,"review_days"),state);if(interval.null()&&yes(f(src,"complete")))interval=f(f(rules,"review_days"),"Practicing");if(anchor&&!interval.null())due=addDays(*anchor,integer(interval,1));
    const Evidence* last=nullptr;auto delta=addDays(0,lookback);need(now>=std::numeric_limits<std::int64_t>::min()+delta,"Weak lookback overflow");auto cutoff=now-delta;for(auto r:positive)if(utcMicros(r->at)>=cutoff&&((r->assessment.isString()&&f(rules,"weak_rank").find(r->assessment.string()))||success(r)))last=r;const Evidence* weak=last&&last->assessment.isString()&&f(rules,"weak_rank").find(last->assessment.string())?last:nullptr;
    return O{{"state",state},{"source_complete",f(src,"complete")},{"source",src},{"pb",pb},{"reliable",reliable},{"attempted_maximum",hasAttempted?quantityValue(attempted):Value{}},{"due_at",due?Value(utcString(*due)):Value{}},{"review_due",due&&now>=*due},{"weak",weak?weak->assessment:Value{}},{"weak_at",weak?Value(weak->at):Value{}},{"positive_count",Value::fromInteger(static_cast<std::int64_t>(positive.size()))},{"success_count",Value::fromInteger(static_cast<std::int64_t>(successful.size()))},{"notices",notices},{"rules",f(rules,"version")},{"as_of",asOf}};
}
} // namespace fathom::progression
