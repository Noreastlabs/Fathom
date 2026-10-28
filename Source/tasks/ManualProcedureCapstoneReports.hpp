#pragma once
#include "tasks/RecipeTask.hpp"
#include <optional>
namespace fathom::tasks::manual_procedure_graph_support {
// Exact reviewed one-key Curriculum companion; reports remain manual.
std::optional<bool> capstoneReportedGuard(const json::Value&,const json::Value&,const json::Value::Object&,const json::Value&);
}
