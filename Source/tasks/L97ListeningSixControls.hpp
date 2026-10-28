#pragma once
#include "tasks/RecipeTask.hpp"
#include <optional>
#include <set>
namespace fathom::tasks::manual_procedure_graph_support {
std::optional<bool> l97ListeningSixGuard(const json::Value& descriptor,
    const json::Value& payload,const json::Value& originalContract,
    const json::Value& frame,const json::Value::Object& saved);
bool l97ListeningOwns(const std::string& key);
bool l97ListeningRetryTextVisible(const json::Value& value);
std::optional<bool> l97ListeningPolicyBefore(const json::Value& program,const json::Value& payload,
    const std::string& key,const std::string& node,std::uint64_t pass,json::Value::Object& policies);
bool l97ListeningPolicyAfter(const json::Value& program,const std::string& key,
    const std::string& node,std::uint64_t pass,json::Value::Object& policies);
void l97ListeningPolicyReleased(json::Value::Object& policies);
json::Value l97ListeningDebtView(const json::Value::Object& policies,const std::string& key);
std::optional<bool> l97ListeningPolicyComplete(const json::Value& program,const std::string& key,
    std::uint64_t pass,const std::set<std::string>& committed,json::Value::Object& policies);
}
