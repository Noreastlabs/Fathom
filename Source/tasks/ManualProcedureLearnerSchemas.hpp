#pragma once
#include "tasks/RecipeTask.hpp"
namespace fathom::tasks::manual_procedure_graph_support {
json::Value candidateLearnerSchema(const json::Value& schema,const json::Value& program,const std::string& node,const json::Value::Object& saved);
}
