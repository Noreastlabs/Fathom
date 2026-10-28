#include "tasks/ManualProcedureProtocolSupport.hpp"
#include "GeneratedManualProcedureProtocols.hpp"
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <set>
#include <sstream>

using namespace fathom;using namespace tasks::manual_procedure_graph_support;
using V=json::Value;namespace G=tasks::manual_procedure_protocols_generated;
namespace {
std::size_t assertions{},refusals{},projections{},bindings{},durationGuards{},sourceAliases{};
void check(bool yes){++assertions;if(!yes)throw std::runtime_error("ASSERT");}
const V& f(const V& v,const char* name){const auto* p=v.find(name);check(p!=nullptr);return *p;}
void refuse(const std::function<void()>& fn){try{fn();}catch(const std::exception&){++refusals;return;}throw std::runtime_error("NO_REFUSAL");}
std::map<std::string,std::vector<V>> cache;
V original(const std::filesystem::path& root,const V& row){const auto& r=f(row,"payload_ref");const auto path=f(r,"path").string();if(!cache.count(path)){std::ifstream stream(root/path);check(stream.good());std::string line;std::vector<V> values;while(std::getline(stream,line))values.push_back(json::parse(line));cache.emplace(path,std::move(values));}std::int64_t line{};check(f(r,"jsonl_line").integer(line)&&line>0);check(static_cast<std::size_t>(line)<=cache.at(path).size());return cache.at(path).at(static_cast<std::size_t>(line-1));}
const V& retainedContract(const V& record,const V& row){const V* c=&record;for(const auto& part:f(row,"retained_contract_path").array())c=&f(*c,part.string().c_str());return *c;}
const V& path(const V& value,const V& parts){const V* current=&value;for(const auto& part:parts.array()){if(part.isString())current=&f(*current,part.string().c_str());else{std::int64_t index{};check(part.integer(index)&&index>=0&&current->isArray()&&static_cast<std::size_t>(index)<current->array().size());current=&current->array()[static_cast<std::size_t>(index)];}}return *current;}
}
int main(int argc,char** argv){try{
 check(argc==2);std::set<std::string> keys,programs;
 for(const auto& entry:G::rows){const auto row=json::parse(entry.value),record=original(argv[1],row);check(f(row,"source_key")==V(entry.key)&&f(record,"package_key")==V(entry.key)&&f(row,"source_identity")==f(record,"source_identity"));check(keys.insert(entry.key).second);const auto& p=f(row,"program");programs.insert(f(p,"name").string());const auto& g=f(p,"graph");const auto& c=retainedContract(record,row);
  for(const auto& named:f(g,"nodes").object()){const auto& node=named.second;
   for(const auto* field:{"source_action_ref","release_source_action_ref"})if(const auto* ref=node.find(field)){const auto& bound=boundProtocolSourceAction(c,*ref);check(bound==path(c,f(*ref,"original_contract_path")));++bindings;if(f(*ref,"original_contract_path").array()[0]==V("actions")){++sourceAliases;auto foreign=*ref;foreign.object()["original_contract_path"]=V::Array{"actions","made_up_release"};refuse([&]{(void)boundProtocolSourceAction(c,foreign);});}}
   if(const auto* op=node.find("computed_expected")){
    if(f(*op,"kind")==V("source_order_P_directions")){const auto& orders=f(*op,"source_P_orders").array();const auto count=orders.size()-(f(*op,"include_first").boolean()?0:1);
     for(const auto* direction:{"D","U"}){V::Array choices(count,V(direction));if(f(*op,"include_first").boolean())choices.front()=f(*op,"protocol_start");V input=f(*op,"directions_value_kind")==V("one_scalar")?choices.front():V(choices);const auto before=input;const auto result=projectSourceOrderedPDirections(*op,input);check(result.resolved&&input==before);const auto& actual=f(result.values,"P_directions").array();check(actual.size()==orders.size()&&actual.front()==f(*op,"protocol_start"));for(std::size_t i=1;i<actual.size();++i)check(actual[i]==V(direction));++projections;}
     check(!projectSourceOrderedPDirections(*op,nullptr).resolved);V::Array unknown(count,nullptr);check(!projectSourceOrderedPDirections(*op,f(*op,"directions_value_kind")==V("one_scalar")?V(nullptr):V(unknown)).resolved);
     refuse([&]{(void)projectSourceOrderedPDirections(*op,V(true));});auto broken=*op;broken.object()["source_P_orders"]=V::Array{V::fromInteger(999)};refuse([&]{(void)projectSourceOrderedPDirections(broken,nullptr);});broken=*op;broken.object()["extra"]=false;refuse([&]{(void)projectSourceOrderedPDirections(broken,nullptr);});
    }else if(f(*op,"kind")==V("selected_domain_reports")){for(const auto& item:f(f(g,"domains"),f(*op,"domain").string().c_str()).array()){check(projectClosedDomainReports(*op,f(item,"selection"),f(f(g,"domains"),f(*op,"domain").string().c_str())).resolved);++projections;}}
   }
   if(const auto* constraints=node.find("constraints"))for(const auto& guard:constraints->array())if(f(guard,"kind")==V("reported_seconds_at_least")){++durationGuards;const auto& r=f(guard,"lower_bound_ref");if(f(r,"scope")==V("contract")){const auto& lower=path(c,f(r,"path"));check(reportedSecondsAtLeast(lower,lower));check(!reportedSecondsAtLeast(V::fromInteger(0),lower));check(!reportedSecondsAtLeast(nullptr,lower));}}
  }
 }
 for(const auto& pair:std::vector<std::pair<std::string,std::string>>{{"0","0"},{"30","3e1"},{"30.00000000000000000001","30"},{"9007199254740993","9007199254740992"},{"0.1000000000000000000001","0.1"}})check(reportedSecondsAtLeast(json::parse(pair.first),json::parse(pair.second)));
 for(const auto& pair:std::vector<std::pair<std::string,std::string>>{{"29.99999999999999999999","30"},{"9007199254740992","9007199254740993"},{"0.0999999999999999999999","0.1"}})check(!reportedSecondsAtLeast(json::parse(pair.first),json::parse(pair.second)));
 for(const auto& wrong:V::Array{true,"30",json::parse("-0.00001"),V(json::Number{"1e309"})})refuse([&]{(void)reportedSecondsAtLeast(wrong,V::fromInteger(30));});refuse([&]{(void)reportedSecondsAtLeast(nullptr,true);});
 check(!reportedSecondsAtLeast(nullptr,V::fromInteger(30))&&!reportedSecondsAtLeast(V::fromInteger(30),nullptr));check(trimmedTextExact("label")&&!trimmedTextExact(" label ")&&!trimmedTextExact("\u3000label\u00a0")&&!trimmedTextExact(""));refuse([&]{(void)trimmedTextExact(true);});
 check(keys.size()==44&&programs.size()==10&&cache.size()==4);std::cout<<"{\"outcome\":\"PASS\",\"rows\":44,\"programs\":10,\"cached_payload_files\":4,\"projections\":"<<projections<<",\"source_bindings\":"<<bindings<<",\"source_action_aliases\":"<<sourceAliases<<",\"duration_guards\":"<<durationGuards<<",\"assertions\":"<<assertions<<",\"refusals\":"<<refusals<<",\"owner_execution\":false,\"current224_mutated\":false}\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
