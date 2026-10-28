#pragma once
#include "content/StrictJson.hpp"
#include <string>
namespace fathom::tasks::harmonized_triad_controls {
bool owns(const std::string&);
// Inputs come only from the closed BoundSourceUnits constructor, after raw
// source/coordinate/context pins have passed. No caller-built native factory.
json::Value construct(const std::string&,const json::Value& original,
                      const json::Value& context,const json::Value& contextRef,
                      const json::Value::Array& sevenSourceRows);
bool guard(const json::Value&,const json::Value&,const json::Value::Object& saved);
std::size_t profileCount();
} // namespace fathom::tasks::harmonized_triad_controls
