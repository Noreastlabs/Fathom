#include "tasks/ManualProcedureDomainReports.hpp"
#include "GeneratedManualProcedureReference79.hpp"
#include <iostream>
#include <set>
#include <functional>
using namespace fathom;using namespace tasks::manual_procedure_graph_support;using V=json::Value;namespace G=tasks::manual_procedure_reference79_generated;
namespace {std::size_t assertions{},refusals{},profiles{},units{},bindings{};
void check(bool b){++assertions;if(!b)throw std::runtime_error("ASSERT");}
const V& f(const V& v,const char* key){const auto* p=v.find(key);check(p!=nullptr);return *p;}
const V& contract(const V& original,const V& row){const V* c=&original;for(const auto& path:f(row,"retained_contract_path").array())c=&f(*c,path.string().c_str());return *c;}
void refuse(const std::function<void()>& fn){try{fn();}catch(const std::runtime_error&){++refusals;return;}throw std::runtime_error("NO_REFUSAL");}
}
int main(){try{std::set<std::string> keys,identities,programs;for(const auto& entry:G::rows){const auto row=json::parse(entry.value),original=json::parse(entry.original);check(f(row,"source_key")==V(entry.key));check(f(original,"package_key")==V(entry.key)&&f(original,"source_identity")==f(row,"source_identity"));check(keys.insert(entry.key).second&&identities.insert(f(row,"source_identity").string()).second);const auto& p=f(row,"program");programs.insert(f(p,"name").string());const auto& g=f(p,"graph");const auto& c=contract(original,row);
 for(const auto& node:f(g,"nodes").object()){
  const auto unit=boundSourceUnit(c,node.second);const auto& actions=f(unit,"source_actions").array();bindings+=actions.size();if(actions.size()==2){check(f(node.second,"physical")==V(true));check(actions[0]==f(c,"steps").array()[3]&&actions[1]==f(c,"steps").array()[4]);check(f(unit,"inserts_release_between_actions")==V(false)&&f(unit,"execution_observed")==V(false));++units;auto malformed=node.second;std::reverse(malformed.object()["source_action_refs"].array().begin(),malformed.object()["source_action_refs"].array().end());refuse([&]{(void)boundSourceUnit(c,malformed);});}
  if(node.second.find("release_source_action_ref")){check(!f(unit,"separate_release_witness").null());++bindings;}
  if(const auto* op=node.second.find("computed_expected")){const auto& domain=f(f(g,"domains"),f(*op,"domain").string().c_str());for(const auto& record:domain.array()){const auto result=projectClosedDomainReports(*op,f(record,"selection"),domain);check(result.resolved);for(const auto& field:f(*op,"fields").object()){const auto& values=f(result.values,field.first.c_str()).array();const auto& contacts=f(record,"contacts").array();check(values.size()==contacts.size());for(std::size_t i=0;i<values.size();++i)check(values[i]==f(contacts[i],field.second.string().c_str()));}++profiles;}
   auto unknown=f(domain.array().front(),"selection");for(auto& x:unknown.object())x.second=nullptr;const auto unresolved=projectClosedDomainReports(*op,unknown,domain);check(!unresolved.resolved&&unresolved.values.object().empty());auto foreign=unknown;for(auto& x:foreign.object())x.second=true;refuse([&]{(void)projectClosedDomainReports(*op,foreign,domain);});auto dup=domain;dup.array().push_back(domain.array().front());refuse([&]{(void)projectClosedDomainReports(*op,f(domain.array().front(),"selection"),dup);});}
 }
 }
 for(const auto& value:V::Array{"x"," x ","\u3000é\u00a0"}){const auto before=value;check(nonemptyTrimmedText(value,1,512));check(before==value);}
 for(const auto& value:V::Array{""," \t\n","\u3000\u00a0\u0085","\u001c\u001d\u001e\u001f"})check(!nonemptyTrimmedText(value,1,512));
 std::string unicode;for(int i=0;i<512;++i)unicode+="😀";check(utf8TextLength(unicode)==512&&nonemptyTrimmedText(unicode,1,512));unicode+="😀";check(!nonemptyTrimmedText(unicode,1,512));
 for(const auto& value:V::Array{nullptr,true,V::fromInteger(1)})refuse([&]{(void)nonemptyTrimmedText(value,1,512);});refuse([&]{(void)nonemptyTrimmedText("plan",0,512);});refuse([&]{(void)utf8TextLength(std::string("\xc0\xaf",2));});
 check(keys.size()==79&&programs.size()==15&&profiles==188&&units==12&&bindings==431);std::cout<<"{\"outcome\":\"PASS\",\"rows\":79,\"programs\":15,\"profiles\":"<<profiles<<",\"uninterrupted_units\":"<<units<<",\"source_bindings\":"<<bindings<<",\"assertions\":"<<assertions<<",\"refusals\":"<<refusals<<",\"owner_execution\":false,\"current224_mutated\":false}\n";return 0;}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
