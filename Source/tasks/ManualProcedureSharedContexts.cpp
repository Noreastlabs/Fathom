#include "tasks/ManualProcedureSharedContexts.hpp"
#include <stdexcept>
namespace fathom::tasks::manual_procedure_graph_support {
SharedSourceContexts::SharedSourceContexts(const std::vector<std::pair<std::string,std::string>>& bindings) {
 if(bindings.empty())throw std::runtime_error("CONTEXTS_REQUIRED");
 for(const auto& binding:bindings){if(binding.first.empty()||contexts_.count(binding.first))throw std::runtime_error("EXACT_UNIQUE_CONTEXT_REFERENCE");const auto value=json::parse(binding.second);if(!value.isObject())throw std::runtime_error("CONTEXT_OBJECT");contexts_.emplace(binding.first,std::make_shared<const json::Value>(value));}
}
std::shared_ptr<const json::Value> SharedSourceContexts::retain(const std::string& reference) const {const auto i=contexts_.find(reference);if(i==contexts_.end())throw std::runtime_error("CLOSED_CONTEXT_REFERENCE");return i->second;}
} // namespace fathom::tasks::manual_procedure_graph_support
