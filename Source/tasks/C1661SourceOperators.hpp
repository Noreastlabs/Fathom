#pragma once
#include "tasks/RecipeTask.hpp"
#include <optional>
namespace fathom::tasks::manual_procedure_graph_support {
// Closed source-specific declarations. This helper neither generates music
// nor observes performance; the existing opaque owner retains all actions.
std::optional<bool> c1661ReportedGuard(const json::Value& descriptor,const json::Value& payload,const json::Value& originalContract,const json::Value& frame,const json::Value::Object& saved,const json::Value& failed);
json::Value c1661RoleProjection(const json::Value& originalContract,const json::Value& setupPayload,const json::Value& frame);
}
