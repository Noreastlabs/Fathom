#pragma once
#include "tasks/RecipeTask.hpp"
namespace fathom::tasks::manual_procedure_graph_support {
// Bind one complete finite contiguous source unit without adding intermediate
// UI/owner releases, rewriting the original contract or synthesizing a clock.
json::Value boundRetainedManualSourceUnit(const json::Value& originalContract,
                                         const json::Value& node);
}
