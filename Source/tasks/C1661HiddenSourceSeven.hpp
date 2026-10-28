#pragma once
#include "content/StrictJson.hpp"
#include <string>
#include <vector>
namespace fathom::tasks::manual_procedure_graph::hidden_seven {
bool owns(const std::string&) noexcept;
bool motif(const std::string&);
bool requiredTextVisible(const json::Value&);
void validate(const std::string&,const json::Value& original,const json::Value& contract,const json::Value& program);
bool reportedUnit(const std::string&,const json::Value& payload,const json::Value::Object& saved,const json::Value& contract);
json::Value actions(const std::string&,const json::Value& rawView,const json::Value& rawActions,bool sourceRole);
json::Value learnerView(const std::string&,const json::Value& rawView);
std::vector<json::Value> learnerHistory(const std::string&,const std::vector<json::Value>& raw);
json::Value reveal(const std::string&,const json::Value& contract,const json::Value::Object& saved);
} // namespace
