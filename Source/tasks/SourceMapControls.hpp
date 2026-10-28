#pragma once
#include "content/StrictJson.hpp"
#include <string>
namespace fathom::tasks::source_map_controls {
bool supports(const json::Value& original);
bool familyKey(const std::string& key);
json::Value construct(const std::string& key,const json::Value& original,const json::Value& context,const json::Value& contextRef,const json::Value& family);
json::Value expectedReports(const std::string& key,const std::string& stage,const json::Value& choices);
bool guard(const json::Value& op,const json::Value& payload,const json::Value::Object& saved,const json::Value::Object& policies);
bool bodilyStop(const std::string& key,const json::Value& payload);
void policyBefore(const std::string& key,const std::string& stage,const json::Value& payload,json::Value::Object& policies);
void policyAfter(const std::string& key,const std::string& stage,const json::Value& payload,json::Value::Object& policies);
void policyReleased(json::Value::Object& policies);
bool policyComplete(const std::string& key,const json::Value::Object& policies);
std::string policyRetryEntry(const std::string& key,const json::Value::Object& policies);
json::Value policyView(const std::string& key,const json::Value::Object& policies);
std::size_t rowCount();
}
