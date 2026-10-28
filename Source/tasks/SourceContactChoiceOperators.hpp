#pragma once
#include "content/StrictJson.hpp"
#include <map>
#include <optional>
namespace fathom::tasks::source_contacts::private_operators {
// Optional means the guard is not owned by this finite private extension.
std::optional<bool> reportGuard(const json::Value&,const json::Value&);
bool ownedGuard(const json::Value&,const json::Value&,const std::map<std::string,json::Value>&);
}
