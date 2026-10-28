#include "tasks/ManualProcedureSourceContracts.hpp"
#include "tasks/ManualProcedureDomainReports.hpp"
namespace fathom::tasks::manual_procedure_graph_support {
namespace {using V=json::Value;void need(bool ok,const char* why){if(!ok)throw recipes::Error(why);}const V& f(const V& v,const char* name){const auto* p=v.find(name);need(p!=nullptr,"SOURCE_REFERENCE_FIELD");return *p;}}
V boundRetainedManualSourceUnit(const V& contract,const V& node){
 need(node.isObject()&&!node.find("source_action_ref"),"SOURCE_BINDING_FORM");const auto& refs=f(node,"source_action_refs");need(refs.isArray()&&!refs.array().empty()&&refs.array().size()<=256,"FINITE_RETAINED_SOURCE_UNIT");
 V::Array result;std::int64_t previous=-1;
 for(const auto& reference:refs.array()){
  const auto& value=boundSourceAction(contract,reference);const auto& path=f(reference,"original_contract_path");std::int64_t index{};need(path.array()[1].integer(index)&&(previous<0||index==previous+1),"ORDERED_CONTIGUOUS_SOURCE_UNIT");previous=index;result.push_back(value);
 }
 if(result.size()>1)need(f(node,"physical")==V(true),"PHYSICAL_COMPLETE_SOURCE_UNIT");
 return V::Object{{"source_actions",result},{"inserts_release_between_actions",false},{"execution_observed",false},{"clock_synthesized",false}};
}
}
