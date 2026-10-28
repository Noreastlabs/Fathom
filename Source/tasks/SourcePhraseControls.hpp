#pragma once
#include "content/StrictJson.hpp"
#include <string>
#include <cstdint>
namespace fathom::tasks::source_phrase_controls {
bool supports(const json::Value& original);
json::Value construct(const std::string& key,const json::Value& original,const json::Value& context,const json::Value& contextRef,const json::Value::Array& family);
bool guard(const json::Value& op,const json::Value& payload,const json::Value::Object& saved,const json::Value& failed,const json::Value::Object& policies);
bool policyBefore(const std::string&,const std::string&,const json::Value&,json::Value::Object&);
void policyAfter(const std::string&,const std::string&,json::Value::Object&);
void policyReleased(json::Value::Object&);
bool policyComplete(const std::string&,const json::Value::Object&);
std::string policyRetryEntry(const std::string&,const json::Value::Object&);
json::Value policyView(const std::string&,const json::Value::Object&);
std::size_t rowCount();
}
