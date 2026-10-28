#pragma once
#include "content/StrictJson.hpp"
#include <string>
namespace fathom::tasks::seventh_family_controls {
bool supports(const json::Value& originalRecord);
json::Value construct(const std::string& exactKey,const json::Value& originalRecord,const json::Value& cachedContext,const json::Value& contextRef,const json::Value::Array& sourceFamily);
bool guard(const json::Value& op,const json::Value& payload,const json::Value::Object& saved);
std::size_t rowCount();
}
