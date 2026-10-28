#pragma once
#include "tasks/RecipeTask.hpp"
#include <optional>
#include <set>
namespace fathom::tasks::manual_procedure_graph_support {
json::Value boundFutureSourceUnit(const json::Value&,const json::Value&);
std::optional<bool> futureReportedGuard(const json::Value&,const json::Value&,const json::Value::Object&,const json::Value&,const json::Value&);
std::optional<bool> futureSourcePhaseRepairGuard(const json::Value&,const json::Value&,const json::Value&,const json::Value::Object&);
std::optional<bool> futureBoundaryRepairGuard(const json::Value&,const json::Value&,const json::Value&,const json::Value&,const json::Value::Object&);
json::Value derivedReportSchema(const json::Value&,const json::Value::Object&,const json::Value&);
json::Value derivedExpectedReports(const json::Value&,const json::Value::Object&,const json::Value&);
json::Value futurePatternProjection(const json::Value&,const json::Value::Object&,const json::Value&);
bool futurePolicyKind(const std::string&);
bool futureSourceAllowsCompletedReopen(const json::Value&,const std::string&);
// All effects consume already schema-validated reports inside the owner's
// copied transactional state. No source, physical or release facts are made.
bool futurePolicyBefore(const json::Value&,const json::Value&,const std::string&,const std::string&,std::uint64_t,json::Value::Object&,bool& stop);
std::optional<json::Value> futureOwnedRepairFailure(const json::Value&,const std::string&,const json::Value&,const json::Value::Object&);
void futurePolicyAfter(const json::Value&,const std::string&,const std::string&,std::uint64_t,json::Value::Object&);
void futurePolicyReleased(json::Value::Object&);
json::Value futureReportedDebtView(const json::Value::Object&,const std::string&);
bool futurePolicyComplete(const json::Value&,const std::string&,std::uint64_t,const std::set<std::string>&,json::Value::Object&);
}
