#pragma once
#include "tasks/RecipeTask.hpp"
#include <optional>
namespace fathom::tasks::manual_procedure_graph_support {
// Exact twelve source units, using the existing opaque owner and typed reports.
// No performance observation, source clock, second owner or caller program.
std::optional<bool> c111CountryStudyReportedGuard(const json::Value& descriptor,
 const json::Value& payload,const json::Value& originalContract,
 const json::Value& frame,const json::Value::Object& saved,const json::Value& failed);
}
