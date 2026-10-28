#include "progression/Recommendations.hpp"
#include "content/Canonical.hpp"
#include <algorithm>
#include <set>
#include <fstream>
#include <iostream>
#include <numeric>

namespace {
using namespace fathom;using namespace fathom::progression;using V=json::Value;using A=V::Array;using O=V::Object;
const V& f(const V& v,const std::string& k){auto p=v.find(k);if(!p)throw HistoryError("Fixture missing "+k);return *p;}
std::string text(const V& v){if(!v.isString())throw HistoryError("Fixture expected string");return v.string();}
V opt(const V& v,const std::string& k){auto p=v.find(k);return p?*p:V{};}
std::string utc(std::string s){if(s.size()>=6&&s.substr(s.size()-6)=="+00:00")s.replace(s.size()-6,6,"Z");return s;}
// Test-only compact numeric bridge. Decimal spelling is exact; no double coercion.
Rational numeric(const V& v){if(!v.isNumber())throw HistoryError("Invalid synthetic numeric quantity");auto token=std::get<json::Number>(v.data).token;auto point=token.find('.');if(token.find_first_of("eE")!=std::string::npos)throw HistoryError("Unsupported synthetic exponent");std::int64_t d=1;if(point!=std::string::npos){auto digits=token.size()-point-1;if(digits>9)throw HistoryError("Synthetic decimal exceeds fixture bridge");for(std::size_t i=0;i<digits;++i)d*=10;token.erase(point,1);}std::size_t end=0;auto n=std::stoll(token,&end);if(end!=token.size()||n<0)throw HistoryError("Invalid synthetic confirmed quantity");return Rational(n,d);}
Evidence unpack(const V& v){Evidence r;r.key=text(f(v,"key"));r.originalBytes=storage::canonical(v);r.status=text(f(v,"status"));if(r.status=="pending"||r.status=="uncertain")return r;r.session=text(f(v,"session"));r.at=utc(text(f(v,"at")));r.timezone=text(f(v,"timezone"));r.day=text(f(v,"day"));r.active=numeric(f(v,"active"));r.assessment=opt(v,"assessment");auto k=text(f(v,"kind"));if(k=="lesson")r.kind=Kind::Attempt;else if(k=="freeplay")r.kind=Kind::Freeplay;else if(k=="ack")r.kind=Kind::Acknowledgment;else throw HistoryError("Invalid kind");if(r.kind!=Kind::Freeplay)r.item=text(f(v,"item"));if(r.kind==Kind::Attempt){r.condition=f(v,"condition");if(f(r.condition,"variant")==V("synthetic-control"))r.condition.object()["variant"]="fg:variant:999999";if(!f(v,"complete").isBool())throw HistoryError("Invalid target completion");r.complete=f(v,"complete").boolean();r.completedCycles=f(v,"completed_cycles").array();r.attestation=opt(v,"attestation");for(auto& s:f(v,"segments").array()){if(!f(s,"whole_target").isBool())throw HistoryError("Invalid segment target flag");r.segments.push_back({numeric(f(s,"tempo")),numeric(f(s,"active")),f(s,"whole_target").boolean(),f(s,"cycles").array()});}}return r;}
V read(const char* p){std::ifstream in(p);if(!in)throw std::runtime_error("Explicit fixture unavailable");return json::parse(std::string(std::istreambuf_iterator<char>(in),{}));}
std::int64_t n(const V& v){std::int64_t x;if(!v.integer(x))throw MetadataError("Fixture expected integer");return x;}
void ready(RecommendationItem& i){i.resourceReady=true;i.resourceEvidence=O{{"basis","no_required_resource"},{"reference","synthetic explicit task metadata; not real availability"},{"query_sha256",content::sha256(storage::canonical(queryValue(i.query)))}};}
RecommendationCatalog catalog(const V& c){RecommendationCatalog out{"synthetic-recommendation-catalog.1",std::string(64,'a'),{}};for(auto& v:f(c,"items").array()){RecommendationItem x;x.query={text(f(v,"id")),f(v,"condition"),nullptr};if(f(x.query.condition,"variant")==V("synthetic-control"))x.query.condition.object()["variant"]="fg:variant:999999";for(auto& d:f(v,"domains").array())x.domains.push_back(text(d));for(auto& g:f(v,"guidance").array())x.guidance.push_back(text(g));x.order=n(f(v,"order"));if(!opt(v,"duration").null())x.duration=numeric(f(v,"duration"));if(!opt(v,"overhead").null())x.overhead=numeric(f(v,"overhead"));x.metadataProvenance=O{{"reference","frozen7.1 synthetic fixture metadata"}};if(opt(v,"resource_ready")==V(true))ready(x);out.items.push_back(x);}return out;}
std::vector<Evidence> records(const V& c){std::vector<Evidence> rows;for(auto& r:f(c,"records").array())rows.push_back(unpack(r));return rows;}
const V& findCase(const V& all,const std::string& prefix){for(auto& c:f(all,"cases").array())if(text(f(c,"id")).rfind(prefix,0)==0)return c;throw std::runtime_error("Missing frozen case");}
V reference(const V& all){A out;for(auto& c:f(all,"cases").array()){auto op=text(f(c,"op"));if(op!="recommend"&&op!="permutation")continue;O result{{"id",f(c,"id")},{"classification","synthetic contract input; original raw retained"}};try{auto cat=catalog(c);auto rows=records(c);auto value=recommend(rows,cat,n(f(c,"budget")),utc(text(f(c,"asof"))));result.emplace("result",value);if(op=="permutation"){int count=0;std::sort(cat.items.begin(),cat.items.end(),[](const auto& a,const auto& b){return a.query.item<b.query.item;});do{auto candidate=cat;for(auto& i:candidate.items){std::reverse(i.domains.begin(),i.domains.end());std::reverse(i.guidance.begin(),i.guidance.end());}std::reverse(rows.begin(),rows.end());if(recommend(rows,candidate,n(f(c,"budget")),utc(text(f(c,"asof"))))!=value)throw std::runtime_error("Full permutation mismatch");++count;}while(std::next_permutation(cat.items.begin(),cat.items.end(),[](const auto& a,const auto& b){return a.query.item<b.query.item;}));result.emplace("permutations",V::fromInteger(count));}}catch(const MetadataError& e){result.emplace("error","MetadataError");result.emplace("message",e.what());}catch(const HistoryError& e){result.emplace("error","HistoryError");result.emplace("message",e.what());}out.emplace_back(result);}return O{{"cases",out}};}
V counterexamples(const V& all,const V& phase){
 A checks;auto check=[&](bool pass,const char* name){checks.emplace_back(O{{"name",name},{"passed",pass}});};
 auto error=[&](auto fn,const char* name){bool hit=false;try{fn();}catch(const std::exception&){hit=true;}check(hit,name);};
 const auto& first=findCase(all,"R27-");auto cat=catalog(first);auto asof=utc(text(f(first,"asof")));auto baseRows=records(findCase(all,"R28-"));auto out=recommend({},cat,65,asof);
 check(f(out,"unrestricted_manual_access")==V(true),"Manual access remains unrestricted");
 auto c=cat;c.items[0].duration=Rational(1,100001);check(f(recommend({},c,65,asof),"skipped").array().size()==1,"Below accepted1/100000estimate minimum skips");
 c=cat;c.items[0].duration=Rational(1,100000);check(!f(recommend({},c,65,asof),"selected").array().empty(),"Exact accepted duration minimum supported");
 c=cat;c.items[0].overhead.reset();check(f(recommend({},c,65,asof),"skipped").array().size()==1,"Missing explicit overhead skips");
 c=cat;c.items.push_back(c.items[0]);error([&]{recommend({},c,65,asof);},"Duplicate item refuses");
 c=cat;c.items[0].guidance={"fg:item:888888"};error([&]{recommend({},c,65,asof);},"Unknown guidance refuses");
 c=cat;c.items[0].domains={"a","a"};error([&]{recommend({},c,65,asof);},"Duplicate domains refuse");
 c=cat;c.items[0].metadataProvenance=nullptr;error([&]{recommend({},c,65,asof);},"Missing metadata provenance refuses");
 c=cat;c.items[0].resourceEvidence=nullptr;error([&]{recommend({},c,65,asof);},"Ready without evidence refuses");
 c=cat;c.items[0].resourceEvidence.object()["query_sha256"]=std::string(64,'b');error([&]{recommend({},c,65,asof);},"Resource evidence cannot transfer to another task");
 c=cat;c.items[0].resourceEvidence=O{{"basis","plan_approved"},{"reference","synthetic"},{"query_sha256",content::sha256(storage::canonical(queryValue(c.items[0].query)))}};error([&]{recommend({},c,65,asof);},"Plan approval is not resource access");
 c=cat;c.items[0].resourceEvidence.object()["basis"]="explicit_access";error([&]{recommend({},c,65,asof);},"Explicit access missing issuer/work refuses");
 error([&]{recommend({},cat,0,asof);},"Zero budget refuses");error([&]{recommend({},cat,14401,asof);},"Overlarge budget refuses");
 check(!f(recommend({},cat,14400,asof),"no_fit").boolean(),"Maximum custom budget supported");
 c=cat;c.items[0].duration=Rational(INT64_MAX);c.items[0].overhead=Rational(1);error([&]{recommend({},c,65,asof);},"Wholecost overflow refuses");
 auto r=baseRows.front();r.kind=Kind::Attempt;r.item=cat.items[0].query.item;r.condition=cat.items[0].query.condition;r.at=asof;r.day=asof.substr(0,10);r.timezone="UTC";r.active=Rational(5);r.complete=false;r.completedCycles.clear();r.segments.clear();r.assessment=nullptr;r.attestation=nullptr;r.session="synthetic-session";
 auto a=recommend({r,r},cat,65,asof),b=recommend({r},cat,65,asof);check(a==b,"Duplicate history counted once including coverage");
 auto conflicting=r;conflicting.originalBytes+=" ";error([&]{recommend({r,conflicting},cat,65,asof);},"Conflicting original identity refuses");
 auto unresolved=r;unresolved.key="pending-original";unresolved.status="uncertain";a=recommend({r,unresolved},cat,65,asof);check(f(a,"coverage")==f(b,"coverage")&&!f(a,"notices").array().empty(),"Uncertain save excluded with visible notice");
 auto free=r;free.key="free-original";free.kind=Kind::Freeplay;free.item="";a=recommend({r,free},cat,65,asof);check(f(a,"coverage")==f(b,"coverage"),"Freeplay excluded from domain coverage");
 auto changed=r;changed.condition.object()["setup"]="different-synthetic-setup";a=recommend({changed},cat,65,asof);check(f(a,"coverage")==f(b,"coverage")&&f(f(f(a,"projections"),r.item),"state")==V("Not Started"),"Item coverage across setups differs from comparable achievement");
 auto future=r;future.at="2026-10-01T00:00:00Z";future.day="2026-10-01";a=recommend({future},cat,65,asof);check(f(a,"coverage").object().empty()&&!f(a,"notices").array().empty(),"Future practice excluded with notice");
 auto boundary=r;boundary.at=utcString(utcMicros(asof)-14LL*86400000000LL);boundary.day=boundary.at.substr(0,10);a=recommend({boundary},cat,65,asof);check(f(a,"coverage")==f(b,"coverage"),"Inclusive14day coverage boundary");boundary.at=utcString(utcMicros(boundary.at)-1);boundary.day=boundary.at.substr(0,10);check(f(recommend({boundary},cat,65,asof),"coverage").object().empty(),"Older than cutoff excluded");
 auto x=r,y=r,z=r;x.key="a";y.key="b";z.key="c";x.active=Rational(1,4000000007LL);y.active=Rational(4000000006LL,4000000007LL);z.active=Rational(1,4000000009LL);a=recommend({x,y,z},cat,65,asof);b=recommend({x,z,y},cat,65,asof);check(a==b,"Canonical arithmetic order survives valid largefraction permutation");
 c=cat;c.items[0].domains={"z","a"};a=recommend({x,y,z},c,65,asof);std::reverse(c.items[0].domains.begin(),c.items[0].domains.end());check(a==recommend({z,y,x},c,65,asof),"Domain/hash/arithmetic permutations identical");
 storage::Reply reply;reply.status=storage::Status::Confirmed;reply.code="CONFIRMED";reply.data=f(phase,"after_commit_snapshot");auto q=f(phase,"query");RecommendationItem item;item.query={text(f(q,"item")),f(q,"condition"),f(q,"source_scope")};item.domains={"synthetic technique"};item.duration=Rational(60);item.overhead=Rational(5);item.metadataProvenance=O{{"reference","synthetic explicit metadata over retained7.2 native snapshot"}};ready(item);RecommendationCatalog native{"synthetic-native.1",std::string(64,'c'),{item}};
 auto raw=storage::canonical(reply.data);a=recommendSnapshot(reply,native,65,text(f(phase,"asof")));auto projected=adaptSnapshot(reply);
 check(f(a,"evidence_sha256")==f(reply.data,"evidence_sha256")&&f(a,"snapshot_sha256")==f(reply.data,"snapshot_sha256"),"Native snapshot exact identities retained");
 check(f(a,"original_history")==V(projected.originalHistory)&&f(a,"historical_observations")==V(projected.historicalObservations),"Original history and observations unchanged");
 check(f(f(f(a,"projections"),item.query.item),"state")==V("Proficient")&&f(f(f(a,"projections"),item.query.item),"pb")==quantityValue(Rational(60)),"Actual retained2Attempt native facts project ProficientPB60");
 check(f(a,"coverage")==V(O{{"synthetic technique",quantityValue(Rational(8))}}),"Native coverage8Attemptseconds excludes3Freeplayseconds");
 check(f(a,"selected").array().size()==1&&f(f(a,"selected").array()[0],"reason")==V("due review: 2026-09-09T10:00:00Z"),"Actual native due recommendation reason exact");
 check(storage::canonical(reply.data)==raw,"Recommendation never mutates snapshot authority");
 reply.status=storage::Status::Unresolved;error([&]{recommendSnapshot(reply,native,65,text(f(phase,"asof")));},"Unconfirmed snapshot refuses");reply.status=storage::Status::Confirmed;
 reply.data.object()["evidence_sha256"]=std::string(64,'f');error([&]{recommendSnapshot(reply,native,65,text(f(phase,"asof")));},"Corrupt evidence identity refuses");
 int passed=0;for(auto& t:checks)if(f(t,"passed")==V(true))++passed;
 return O{{"checks",checks},{"passed",V::fromInteger(passed)},{"total",V::fromInteger(static_cast<std::int64_t>(checks.size()))}};
}
V boundaryCases(const V& all){
 A checks;auto check=[&](bool pass,const char* name){checks.emplace_back(O{{"name",name},{"passed",pass}});};
 const auto& fixture=findCase(all,"R27-");auto c=catalog(fixture);c.items.resize(1);auto asof=text(f(fixture,"asof"));auto id=c.items[0].query.item;
 c.items[0].duration=Rational(1,100001);auto r=recommend({},c,65,asof);
 check(f(r,"selected").array().empty()&&f(r,"skipped")==V(A{A{id,"missing whole-task estimate/allowance"}}),"Single-item below minimum exact skip reason");
 c.items[0].duration=Rational(1,100000);r=recommend({},c,65,asof);
 check(f(r,"selected").array().size()==1&&f(f(r,"selected").array()[0],"id")==V(id)&&f(f(r,"selected").array()[0],"seconds")==quantityValue(Rational(500001,100000))&&f(r,"remaining")==quantityValue(Rational(5999999,100000)),"Single-item exact minimum exact identity cost remaining");
 c.items[0].overhead.reset();r=recommend({},c,65,asof);
 check(f(r,"selected").array().empty()&&f(r,"skipped")==V(A{A{id,"missing whole-task estimate/allowance"}}),"Single-item missing explicit overhead exact skip");
 int passed=0;for(auto& t:checks)if(f(t,"passed")==V(true))++passed;return O{{"checks",checks},{"passed",V::fromInteger(passed)},{"total",V::fromInteger(static_cast<std::int64_t>(checks.size()))}};
}
V sourceCases(const V& all){
 A checks;auto check=[&](bool pass,const char* name){checks.emplace_back(O{{"name",name},{"passed",pass}});};
 const auto& fixture=findCase(all,"R45-");auto c=catalog(fixture);auto rows=records(fixture);auto asof=text(f(fixture,"asof"));auto& item=c.items[0];
 V refs=f(f(sourceRules(),"records").array().back(),"source_refs");
 V scope=O{{"item_id",item.query.item},{"variant_id","fg:variant:999999"},{"content_revision",V::fromInteger(1)},{"content_version","control-examples.1"},{"source_manifest_sha256","e856ef05e610b9be51f33aac661a900301f747a9259bfcbd951b756a247504fe"},{"source_refs",refs},{"span",O{{"kind","source_task"},{"source_refs",refs}}},{"target",O{{"kind","source_attestation"},{"rubric_item_id",item.query.item}}}};
 item.query.condition=nullptr;item.query.sourceScope=scope;ready(item);
 for(auto& r:rows){r.kind=Kind::Source;r.condition=nullptr;r.sourceScope=scope;r.session.clear();r.segments.clear();r.completedCycles.clear();r.active=Rational();r.originalBytes=storage::canonical(O{{"classification","synthetic standalone source fixture from accepted R45 attestation"},{"key",r.key},{"scope",scope},{"at",r.at},{"attestation",r.attestation}});}
 auto result=recommend(rows,c,65,asof);auto& p=f(f(result,"projections"),item.query.item);
 check(f(p,"source_complete")==V(true)&&f(p,"positive_count")==V::fromInteger(0),"Standalone105 independent same-take source completion has no generic Attempt");
 check(f(result,"coverage").object().empty(),"Standalone source contributes no domain time");
 check(f(result,"selected").array().size()==1&&f(f(result,"selected").array()[0],"id")==V("fg:item:000001")&&f(f(result,"selected").array()[0],"reason")==V("next progression: 0 unmet guidance prerequisites; access unrestricted"),"SourceComplete satisfies advisory guidance without perpetual automatic next");
 auto later=utcString(utcMicros(asof)+3LL*86400000000LL);item.resourceReady=false;
 result=recommend(rows,c,65,later);bool skipped=false;for(auto& x:f(result,"skipped").array())if(x==V(A{item.query.item,"required resource evidence unavailable"}))skipped=true;
 check(skipped&&f(f(f(result,"projections"),item.query.item),"source_complete")==V(true),"Historical SourceComplete cannot supply current missing resource");
 check(f(result,"unrestricted_manual_access")==V(true),"Missing source resource retains manual browsing access");
 auto changed=c;changed.items[0].query.sourceScope.object()["content_version"]="explicit-synthetic-other-version";changed.items[0].resourceReady=false;
 result=recommend(rows,changed,65,asof);check(f(f(f(result,"projections"),item.query.item),"source_complete")==V(false),"Changed source scope does not inherit completion");
 auto partial=rows;partial[0].attestation.object()["independent"]=nullptr;partial[0].originalBytes+=" synthetic missing independent branch";
 result=recommend(partial,c,65,asof);check(f(f(f(result,"projections"),item.query.item),"source_complete")==V(false),"One passing105take without repeat or independent branch incomplete");
 auto missing=rows;missing[0].attestation.object()["resources"]=O{};missing[0].originalBytes+=" synthetic missing R105";
 result=recommend(missing,c,65,asof);check(f(f(f(result,"projections"),item.query.item),"source_complete")==V(false),"R105 missing actual access does not qualify source completion");
 int passed=0;for(auto& t:checks)if(f(t,"passed")==V(true))++passed;return O{{"checks",checks},{"passed",V::fromInteger(passed)},{"total",V::fromInteger(static_cast<std::int64_t>(checks.size()))}};
}
}
int main(int argc,char** argv){try{if(argc!=3&&argc!=4)throw std::runtime_error("Usage --reference/--source fixtures OR --checks fixtures native-phase");V out;if(std::string(argv[1])=="--reference"&&argc==3)out=reference(read(argv[2]));else if(std::string(argv[1])=="--bounds"&&argc==3)out=boundaryCases(read(argv[2]));else if(std::string(argv[1])=="--source"&&argc==3)out=sourceCases(read(argv[2]));else if(std::string(argv[1])=="--checks"&&argc==4)out=counterexamples(read(argv[2]),read(argv[3]));else throw std::runtime_error("Explicit mode required");std::cout<<json::stringify(out)<<'\n';return out.find("total")&&f(out,"total")!=f(out,"passed")?1:0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
