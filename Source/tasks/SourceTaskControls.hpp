#pragma once
#include "content/StrictJson.hpp"
#include <string>
namespace fathom::tasks::source_task_controls {
bool supports(const json::Value&);
json::Value construct(const std::string&,const json::Value&,const json::Value&,const json::Value&);
json::Value expectedReports(const std::string&,const std::string&,const json::Value&);
bool guard(const json::Value&,const json::Value&,const json::Value::Object&,const json::Value::Object&);
bool bodilyStop(const std::string&,const json::Value&);
void policyBefore(const std::string&,const std::string&,const json::Value&,json::Value::Object&);
void policyAfter(const std::string&,const std::string&,const json::Value&,json::Value::Object&);
void policyReleased(json::Value::Object&);
bool policyComplete(const std::string&,const json::Value::Object&);
std::string policyRetryEntry(const std::string&,const json::Value::Object&);
json::Value policyView(const std::string&,const json::Value::Object&);
std::size_t rowCount();
}
