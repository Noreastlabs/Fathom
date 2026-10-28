#include "progression/ProgressionAdapter.hpp"
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
Evidence unpack(const V& v){Evidence r;r.key=text(f(v,"key"));r.originalBytes=storage::canonical(v);r.status=text(f(v,"status"));if(r.status=="pending"||r.status=="uncertain")return r;r.session=text(f(v,"session"));r.at=utc(text(f(v,"at")));r.timezone=text(f(v,"timezone"));r.day=text(f(v,"day"));r.active=numeric(f(v,"active"));r.assessment=opt(v,"assessment");auto k=text(f(v,"kind"));if(k=="lesson")r.kind=Kind::Attempt;else if(k=="freeplay")r.kind=Kind::Freeplay;else if(k=="ack")r.kind=Kind::Acknowledgment;else throw HistoryError("Invalid kind");if(r.kind!=Kind::Freeplay)r.item=text(f(v,"item"));if(r.kind==Kind::Attempt){r.condition=f(v,"condition");if(!f(v,"complete").isBool())throw HistoryError("Invalid target completion");r.complete=f(v,"complete").boolean();r.completedCycles=f(v,"completed_cycles").array();r.attestation=opt(v,"attestation");for(auto& s:f(v,"segments").array()){if(!f(s,"whole_target").isBool())throw HistoryError("Invalid segment target flag");r.segments.push_back({numeric(f(s,"tempo")),numeric(f(s,"active")),f(s,"whole_target").boolean(),f(s,"cycles").array()});}}return r;}
V normalize(V v){v.object().erase("attempted_maximum");for(auto k:{"due_at","weak_at","as_of"})if(!f(v,k).null())v.object()[k]=std::to_string(utcMicros(utc(text(f(v,k)))));return v;}
V read(const char* path){std::ifstream in(path);if(!in)throw std::runtime_error("Oracle unavailable");return json::parse(std::string(std::istreambuf_iterator<char>(in),{}));}
int utcTests(){
    A cases;auto check=[&](bool ok,const char* name){cases.emplace_back(O{{"name",name},{"passed",ok}});};
    check(utcMicros("1969-12-31T23:59:59Z")==-1000000,"legitimate epoch minus one");
    check(utcMicros("2026-01-01T00:00:00Z")==1767225600000000LL,"exact current civil conversion");
    check(utcMicros("2026-01-01T00:00:00.123456Z")==1767225600123456LL,"exact fractional microseconds");
    check(utcString(-1)=="1969-12-31T23:59:59.999999Z","negative epoch microsecond roundtrip");
    bool rejected=false;try{utcMicros("0001-01-01T00:00:00Z");}catch(const std::exception&){rejected=true;}check(rejected,"unsupported native civil sentinel cannot become epoch minus one");
    check(utcMicros("1968-01-01T00:00:00Z")==-63158400000000LL,"supported earlier date exact");
    auto config=initialRules();config.object()["weak_lookback_days"]=V::fromInteger(INT64_MAX/86400000000LL);Query query{"fg:item:000001",O{{"variant","synthetic-control"},{"revision",V::fromInteger(1)},{"content_version","synthetic-UTC-only"},{"setup","synthetic"},{"span","whole"},{"beat_unit",A{V::fromInteger(1),V::fromInteger(1)}},{"grouping",A{V::fromInteger(1)}},{"technique","authored"},{"target",O{{"cycles",V::fromInteger(1)}}}},nullptr};
    rejected=false;try{project({},query,"1968-01-01T00:00:00Z",config);}catch(const HistoryError&){rejected=true;}check(rejected,"supported UTC cutoff rejects actual signed underflow");
    int passed=0;for(auto& c:cases)if(f(c,"passed").boolean())++passed;std::cout<<json::stringify(O{{"checks",cases},{"passed",V::fromInteger(passed)},{"count",V::fromInteger(static_cast<std::int64_t>(cases.size()))}})<<'\n';return passed==7?0:1;
}
}
int main(int argc,char** argv){try{if(argc!=2)throw std::runtime_error("Explicit complete101 oracle file or --utc required; no profile access");if(std::string(argv[1])=="--utc")return utcTests();auto oracle=read(argv[1]);A results;std::size_t passed=0;for(auto& c:f(oracle,"cases").array()){const auto& input=f(c,"input");bool expectedError=!f(c,"expected_error").null();V actual;std::string error;try{std::vector<Evidence> rows;for(auto& v:f(input,"records").array())rows.push_back(unpack(v));Query q{text(f(input,"item")),f(input,"condition"),{}};auto rules=opt(input,"config");actual=project(rows,q,utc(text(f(input,"asof"))),rules.null()?initialRules():rules);}catch(const std::exception& e){error=e.what();}bool ok=expectedError?!error.empty():error.empty()&&normalize(actual)==f(c,"normalized_comparison_output");passed+=ok?1:0;results.emplace_back(O{{"id",f(c,"id")},{"passed",ok},{"expected_error",expectedError},{"error",error},{"actual",actual},{"expected",f(c,"normalized_comparison_output")}});}std::cout<<json::stringify(O{{"classification","Synthetic contract comparison; not learner evidence"},{"cases",V::fromInteger(static_cast<std::int64_t>(results.size()))},{"passed",V::fromInteger(static_cast<std::int64_t>(passed))},{"results",results}})<<'\n';return passed==results.size()&&results.size()==101?0:1;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
