#include "progression/Recommendations.hpp"
#include "content/Canonical.hpp"
#include <algorithm>
#include <limits>
#include <numeric>
#include <set>

namespace fathom::progression {
namespace {
using A=Value::Array;using O=Value::Object;
void need(bool v,const std::string& s){if(!v)throw MetadataError(s);}
const Value& field(const Value& v,const std::string& k){auto p=v.find(k);need(p!=nullptr,"Missing recommendation field: "+k);return *p;}
bool nonempty(const Value& v){return v.isString()&&!v.string().empty();}
std::int64_t integer(const Value& v){std::int64_t n;need(v.integer(n),"Expected integer rule");return n;}
Value number(std::int64_t n){return Value::fromInteger(n);}
std::string hash(const Value& v){return content::sha256(storage::canonical(v));}
bool digest(const std::string& s){return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;}
A strings(std::vector<std::string> v){std::sort(v.begin(),v.end());A a;for(auto& x:v)a.emplace_back(x);return a;}
Rational divide(Rational x,std::size_t divisor){need(divisor>0&&divisor<=static_cast<std::size_t>(INT64_MAX),"Invalid domain count");auto d=static_cast<std::int64_t>(divisor),g=std::gcd(x.numerator(),d);auto remaining=d/g;need(x.denominator()<=INT64_MAX/remaining,"Coverage denominator overflow");return Rational(x.numerator()/g,x.denominator()*remaining);}
Rational subtract(Rational a,Rational b){need(!(a<b),"Negative remaining budget");auto g=std::gcd(a.denominator(),b.denominator());auto ad=b.denominator()/g,bd=a.denominator()/g;need(a.denominator()<=INT64_MAX/ad&&a.numerator()<=INT64_MAX/ad&&b.numerator()<=INT64_MAX/bd,"Remaining budget overflow");return Rational(a.numerator()*ad-b.numerator()*bd,a.denominator()*ad);}
void uniqueNonempty(const std::vector<std::string>& xs,const char* label,bool required){need(!required||!xs.empty(),std::string("Missing ")+label);std::set<std::string> found;for(auto& x:xs)need(!x.empty()&&found.insert(x).second,std::string("Empty/duplicate ")+label);}
void validate(const RecommendationCatalog& c){
    need(!c.version.empty()&&digest(c.contentManifestSha256),"Missing catalog version/content manifest identity");
    need(!c.items.empty()&&c.items.size()<=10000,"Catalog requires1..10000 explicit items");
    std::set<std::string> ids;
    for(auto& x:c.items){
        validateQuery(x.query);need(ids.insert(x.query.item).second,"Duplicate canonical item");
        uniqueNonempty(x.domains,"domain metadata",true);uniqueNonempty(x.guidance,"guidance",false);
        need(x.order>=0,"Negative canonical order");
        need(x.metadataProvenance.isObject()&&nonempty(field(x.metadataProvenance,"reference")),"Missing metadata provenance");
        // Ready is an explicit selected-task input assertion, not plan approval or
        // completion history. The actual producer is responsible for its truth.
        if(x.resourceReady){
            need(x.resourceEvidence.isObject(),"Ready resources lack evidence");
            need(nonempty(field(x.resourceEvidence,"reference")),"Missing readiness evidence reference");
            need(field(x.resourceEvidence,"query_sha256")==Value(hash(queryValue(x.query))),"Readiness belongs to another selected task");
            const auto& basis=field(x.resourceEvidence,"basis");
            need(basis==Value("no_required_resource")||basis==Value("explicit_access"),"Unsupported readiness basis");
            if(basis==Value("explicit_access")){
                need(field(x.resourceEvidence,"actual_access")==Value(true)&&nonempty(field(x.resourceEvidence,"who")),"Missing actual access assertion/issuer");
                const auto& role=field(x.resourceEvidence,"role");
                need(role==Value("learner")||role==Value("teacher")||role==Value("human_reviewer"),"Unsupported resource issuer role");
                need(nonempty(field(x.resourceEvidence,"work_ref")),"Missing actual resource reference");
                utcMicros(field(x.resourceEvidence,"at").string());
            }
        }
    }
    for(auto& x:c.items)for(auto& g:x.guidance)need(ids.count(g)!=0,"Unknown guidance identity");
}
struct Rank {
    int category=2;
    std::int64_t primary=0,secondary=0,order=0;
    Rational coverage;
    const RecommendationItem* item=nullptr;
    std::string reason;
};
bool less(const Rank& a,const Rank& b){
    if(a.category!=b.category)return a.category<b.category;
    if(a.primary!=b.primary)return a.primary<b.primary;
    if(a.secondary!=b.secondary)return a.secondary<b.secondary;
    if(!(a.coverage==b.coverage))return a.coverage<b.coverage;
    if(a.order!=b.order)return a.order<b.order;
    return a.item->query.item<b.item->query.item;
}
Value tuple(const Rank& r){A a{number(r.category),number(r.primary)};if(r.category==1)a.emplace_back(number(r.secondary));a.emplace_back(quantityValue(r.coverage));a.emplace_back(number(r.order));a.emplace_back(r.item->query.item);return a;}
void sortValues(A& a){std::sort(a.begin(),a.end(),[](const Value& x,const Value& y){return storage::canonical(x)<storage::canonical(y);});a.erase(std::unique(a.begin(),a.end()),a.end());}
}
Value recommendationCatalogValue(const RecommendationCatalog& c){
    A items;for(auto& x:c.items)items.emplace_back(O{{"query",queryValue(x.query)},{"domains",strings(x.domains)},{"guidance",strings(x.guidance)},{"order",number(x.order)},{"duration",x.duration?quantityValue(*x.duration):Value{}},{"overhead",x.overhead?quantityValue(*x.overhead):Value{}},{"resource_ready",x.resourceReady},{"metadata_provenance",x.metadataProvenance},{"resource_evidence",x.resourceEvidence}});
    std::sort(items.begin(),items.end(),[](const Value& a,const Value& b){return field(field(a,"query"),"item").string()<field(field(b,"query"),"item").string();});
    return O{{"version",c.version},{"content_manifest_sha256",c.contentManifestSha256},{"items",items}};
}
Value recommend(const std::vector<Evidence>& input,const RecommendationCatalog& catalog,std::int64_t budget,const std::string& asOf){
    need(budget>=1&&budget<=integer(field(initialRules(),"max_budget_seconds")),"Custom budget must be integer1..14400seconds");validate(catalog);
    const auto now=utcMicros(asOf);auto days=integer(field(initialRules(),"coverage_days"));constexpr std::int64_t day=86400000000LL;
    need(days>0&&days<=INT64_MAX/day&&now>=INT64_MIN+days*day,"Coverage cutoff overflow");auto cutoff=now-days*day;
    O projections,coverageValues;std::map<std::string,const RecommendationItem*> lookup;std::map<std::string,Rational> coverage;A notices,skipped;
    for(auto& x:catalog.items){lookup.emplace(x.query.item,&x);auto p=project(input,x.query,asOf);for(auto& n:field(p,"notices").array())notices.push_back(n);projections.emplace(x.query.item,std::move(p));}
    // Every original has already passed the accepted projection validator above.
    // Coverage is item-level, intentionally independent of selected comparability.
    std::map<std::string,const Evidence*> ordered;for(auto& r:input)ordered.emplace(r.key,&r);
    for(auto& pair:ordered){const auto& r=*pair.second;if(r.status!="committed"||r.kind!=Kind::Attempt||r.active.numerator()==0)continue;auto at=utcMicros(r.at);auto i=lookup.find(r.item);if(at<cutoff||at>now||i==lookup.end())continue;auto share=divide(r.active,i->second->domains.size());for(auto& domain:i->second->domains)coverage[domain]=coverage[domain]+share;}
    for(auto& kv:coverage)coverageValues.emplace(kv.first,quantityValue(kv.second));
    std::vector<Rank> ranked;
    for(auto& x:catalog.items){auto& p=projections.at(x.query.item);
        if(!x.duration||*x.duration<Rational(1,100000)||!x.overhead){skipped.emplace_back(A{x.query.item,"missing whole-task estimate/allowance"});continue;}
        if(!x.resourceReady){skipped.emplace_back(A{x.query.item,"required resource evidence unavailable"});continue;}
        Rank r;r.item=&x;r.order=x.order;auto domains=x.domains;std::sort(domains.begin(),domains.end());for(auto& d:domains){auto i=coverage.find(d);if(i!=coverage.end())r.coverage=r.coverage+i->second;}r.coverage=divide(r.coverage,x.domains.size());
        if(field(p,"review_due")==Value(true)){r.category=0;r.primary=utcMicros(field(p,"due_at").string());r.reason="due review: "+field(p,"due_at").string();}
        else if(!field(p,"weak").null()){r.category=1;r.primary=integer(field(field(initialRules(),"weak_rank"),field(p,"weak").string()));auto at=utcMicros(field(p,"weak_at").string());need(at!=INT64_MIN,"Weak rank timestamp overflow");r.secondary=-at;r.reason="recent self-report: "+field(p,"weak").string();}
        else if(field(p,"state")!=Value("Mastered")&&field(p,"source_complete")!=Value(true)){
            for(auto& g:x.guidance){auto& q=projections.at(g);if(field(q,"state")!=Value("Proficient")&&field(q,"state")!=Value("Mastered")&&field(q,"source_complete")!=Value(true))++r.primary;}
            r.reason="next progression: "+std::to_string(r.primary)+" unmet guidance prerequisites; access unrestricted";
        }else continue;
        ranked.push_back(r);
    }
    std::sort(ranked.begin(),ranked.end(),less);Rational remaining(budget);A selected;
    for(auto& r:ranked){auto cost=*r.item->duration+*r.item->overhead;if(!(remaining<cost)){selected.emplace_back(O{{"id",r.item->query.item},{"seconds",quantityValue(cost)},{"reason",r.reason},{"tuple",tuple(r)}});remaining=subtract(remaining,cost);}else skipped.emplace_back(A{r.item->query.item,"whole task does not fit remaining budget"});}
    sortValues(notices);sortValues(skipped);auto cv=recommendationCatalogValue(catalog);
    return O{{"recommendation_version",number(1)},{"selected",selected},{"remaining",quantityValue(remaining)},{"skipped",skipped},{"coverage",coverageValues},{"projections",projections},{"notices",notices},{"as_of",asOf},{"rules",field(initialRules(),"version")},{"rules_sha256",rulesIdentity()},{"source_rules_sha256",sourceRulesIdentity()},{"catalog",cv},{"catalog_sha256",hash(cv)},{"unrestricted_manual_access",true},{"no_fit",selected.empty()}};
}
Value recommendSnapshot(const storage::Reply& reply,const RecommendationCatalog& catalog,std::int64_t budget,const std::string& asOf){
    auto s=adaptSnapshot(reply);auto result=recommend(s.records,catalog,budget,asOf);auto& o=result.object();o.emplace("profile_id",s.profile);o.emplace("evidence_marker",number(s.marker));o.emplace("evidence_sha256",s.evidenceHash);o.emplace("snapshot_sha256",s.snapshotHash);o.emplace("adapter_notices",s.notices);o.emplace("original_history",s.originalHistory);o.emplace("historical_observations",s.historicalObservations);return result;
}
} // namespace fathom::progression
