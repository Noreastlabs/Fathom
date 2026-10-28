#pragma once
#include "tasks/RecipeTask.hpp"
#include <optional>

namespace fathom::tasks::manual_procedure_graph_support {
// Pure closed descriptor operations. These never own gestures or fabricate a
// report, source observation, release, recording, completion or credit.
json::Value expandSharedProgram(const json::Value& closedCatalog,
                               const std::string& program,
                               const json::Value& exactParameters);
const json::Value& boundedOriginalPath(const json::Value& original,
                                     const json::Value& literalPath);
std::optional<bool> advancedReportedGuard(const json::Value& descriptor,
                                         const json::Value& typedPayload,
                                         const json::Value::Object& saved,
                                         const json::Value& failed,
                                         const json::Value& domains);
} // namespace fathom::tasks::manual_procedure_graph_support
