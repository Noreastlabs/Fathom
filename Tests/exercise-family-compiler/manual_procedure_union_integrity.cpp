#include "tasks/ManualProcedureGraph.hpp"
#include <GeneratedManualProcedureGraph.hpp>
#include <iostream>
#include <set>
using namespace fathom;using namespace tasks::manual_procedure_graph;
using V=json::Value;namespace G=tasks::manual_procedure_graph_generated;namespace recipes=tasks::recipes;
int main(){try{std::size_t assertions{};auto check=[&](bool b){++assertions;if(!b)throw std::runtime_error("ASSERT");};std::set<std::string> identities;std::set<const V*> contexts;
 for(const auto& row:G::rows){const auto& d=definition(row.key);check(d.exportedDefinition()==json::parse(row.value));check(d.sourceClosureSha256()==row.closure);check(d.sourceKey()==row.key);check(identities.insert(d.sourceIdentity()).second);check(d.retainedOriginalRecord().find("package_key")&&*d.retainedOriginalRecord().find("package_key")==V(row.key));contexts.insert(&d.retainedSourceContext());ManualProcedureGraph owner(d);const auto before=owner.learnerView();const auto token=owner.capture("begin");try{owner.apply(token,V::Object{{"original_workbook",false},{"own_instrument",false}});throw std::runtime_error("NO_REFUSAL");}catch(const recipes::Error&){}check(owner.history().empty()&&owner.current(token)&&owner.learnerView()==before);}
 check(keys().size()==G::rowCount&&contexts.size()==G::contexts.size());std::cout<<"{\"outcome\":\"PASS\",\"rows\":"<<keys().size()<<",\"shared_context_objects\":"<<contexts.size()<<",\"assertions\":"<<assertions<<",\"closed_initial_refusals\":"<<keys().size()<<",\"manual_reports\":0,\"owner_workflows\":0}\n";return 0;}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}
