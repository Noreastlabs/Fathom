#pragma once
#include "content/StrictJson.hpp"
#include <string>
namespace fathom::tasks::level068_source_controls {
bool supportsSchema(const std::string&);
bool supports(const json::Value& originalImplementation);
json::Value construct(const std::string& exactKey,const json::Value& originalImplementation);
bool guard(const json::Value&,const json::Value&,const json::Value::Object& saved);
std::size_t rowCount();
} // namespace fathom::tasks::level068_source_controls
