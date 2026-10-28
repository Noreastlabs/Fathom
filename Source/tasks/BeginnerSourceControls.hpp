#pragma once
#include "content/StrictJson.hpp"
#include <string>
namespace fathom::tasks::beginner_source_controls {
bool supports(const json::Value& originalRecord);
json::Value construct(const std::string& exactKey,const json::Value& originalRecord,const json::Value& cachedContext,const json::Value& contextRef,const json::Value::Array& sourceFamily);
bool guard(const json::Value& op,const json::Value& payload,const json::Value::Object& saved,const json::Value& failed,const json::Value::Object& policyState);
bool policyBefore(const std::string&,const std::string&,const json::Value&,std::uint64_t,json::Value::Object&);
void policyAfter(const std::string&,const std::string&,const json::Value&,json::Value::Object&);
void policyReleased(json::Value::Object&);
bool policyComplete(const std::string&,const json::Value::Object&);
json::Value policyView(const std::string&,const json::Value::Object&);
std::size_t rowCount();
}
