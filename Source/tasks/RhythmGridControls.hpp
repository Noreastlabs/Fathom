#pragma once
#include "content/StrictJson.hpp"
#include <string>
namespace fathom::tasks::rhythm_grid_controls {
bool supports(const json::Value&);
json::Value construct(const std::string&,const json::Value&,const json::Value&,const json::Value&,const json::Value::Array&);
bool guard(const json::Value&,const json::Value&,const json::Value::Object&,const json::Value&,const json::Value::Object&);
bool policyBefore(const std::string&,const std::string&,const json::Value&,std::uint64_t,json::Value::Object&);
void policyAfter(const std::string&,const std::string&,const json::Value&,json::Value::Object&);
void policyReleased(json::Value::Object&);
bool policyComplete(const std::string&,const json::Value::Object&);
json::Value policyView(const std::string&,const json::Value::Object&);
std::size_t rowCount();
}
