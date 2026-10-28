#pragma once
#include "content/StrictJson.hpp"
#include <memory>
#include <map>
namespace fathom::tasks::manual_procedure_graph_support {
// Trusted context metadata only. Parse each exact source reference once and
// retain immutable values independently of catalog/Definition lifetimes.
class SharedSourceContexts final {
public:
 explicit SharedSourceContexts(const std::vector<std::pair<std::string,std::string>>& closedSerializedContexts);
 std::shared_ptr<const json::Value> retain(const std::string& exactReference) const;
 std::size_t parsedCount() const noexcept{return contexts_.size();}
private:
 std::map<std::string,std::shared_ptr<const json::Value>> contexts_;
};
} // namespace fathom::tasks::manual_procedure_graph_support
