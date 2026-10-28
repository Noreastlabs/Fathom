#pragma once
#include "content/StrictJson.hpp"
#include <string>
namespace fathom::tasks::diagonal_route_controls {
bool supports(const json::Value& original);
json::Value construct(const std::string& key,const json::Value& original,const json::Value& context,const json::Value& contextRef);
bool guard(const json::Value& op,const json::Value& payload,const json::Value::Object& saved);
std::size_t rowCount();
}
