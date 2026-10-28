#pragma once
#include "content/StrictJson.hpp"
#include <string>
namespace fathom::tasks::anticipation_ladder_controls {
bool supports(const json::Value& original);
json::Value construct(const std::string& key,const json::Value& original,
                      const json::Value& context,const json::Value& contextRef,
                      const json::Value::Array& sourceFamily);
bool guard(const json::Value& op,const json::Value& payload,
           const json::Value::Object& saved);
std::size_t rowCount();
}
