#pragma once
#include "content/StrictJson.hpp"
#include <string>
namespace fathom::tasks::progression_circle_controls {
bool supports(const json::Value& original);
json::Value construct(const std::string& key, const json::Value& original,
                      const json::Value& context, const json::Value& contextRef,
                      const json::Value::Array& sixCards,
                      const json::Value::Array& spellingRows);
bool guard(const json::Value& op, const json::Value& payload,
           const json::Value::Object& saved);
std::size_t rowCount();
std::size_t profileCount();
}
