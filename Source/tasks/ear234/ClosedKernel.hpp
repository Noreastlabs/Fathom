#pragma once
#include "content/StrictJson.hpp"
#include <map>
#include <memory>
#include <string>
#include <vector>

namespace fathom::tasks::ear234::closed {
// Only the generated, pinned27-kernel catalogue can supply code. Learner JSON
// is always data; no runtime import, evaluation, file access or source clock.
struct Node;
struct Value {
    std::shared_ptr<Node> p;
    Value();
    explicit Value(std::shared_ptr<Node>);
    static Value none();
    static Value boolean(bool);
    static Value integer(std::int64_t);
    static Value string(std::string);
    static Value sequence(std::string,const std::vector<Value>& = {});
    static Value dictionary();
    static Value object(std::string);
    static Value unknown();
    bool truth() const;
    std::string kind() const;
    std::string text() const;
    std::int64_t number() const;
    Value get(const Value&) const;
    Value get(const std::string&) const;
    Value getOr(const std::string&,Value = none()) const;
    void put(Value,Value);
    void attribute(std::string,Value);
    Value attribute(const std::string&) const;
    std::vector<Value> items() const;
    bool has(const Value&) const;
    bool operator==(const Value&) const;
    bool operator!=(const Value& v) const { return !(*this==v); }
};
struct NeedInput final {};
struct Return final { Value value; };
using Environment = std::map<std::string,Value>;
struct Node {
    std::string kind{"none"}, text;
    std::int64_t number{}, denominator{1};
    std::vector<Value> values;
    std::vector<std::pair<Value,Value>> entries;
    std::map<std::string,Value> attributes;
    json::Value code;
    Value* unused{};
    std::shared_ptr<Environment> closure;
    std::shared_ptr<Node> bound;
};
Value fromJson(const json::Value&);
json::Value toJson(const Value&);
Value clone(const Value&);
std::string unicodeStrip(const std::string&);

class Kernel final {
public:
    static Kernel fromPinnedSha(const std::string& exactCatalogueSha256);
    Value construct(const std::string& exactClass,const std::vector<Value>& arguments);
    Value invoke(Value self,const std::string& method,const std::vector<Value>& arguments = {});
    // Private replay comparison only; never a learner export or state setter.
    json::Value continuationState(const Value&) const;
    bool hasMethod(const Value&,const std::string&) const;
    bool enabled(const Value&,const std::string&,std::size_t argumentCount,bool internalToken);
    void permitExplicitLearnerReference(bool permitted) noexcept { explicitReference_=permitted; }
private:
    explicit Kernel(const json::Value& frozenModule);
    Value evaluate(const json::Value&,Environment&);
    void statements(const json::Value::Array&,Environment&);
    Environment globals_;
    std::map<std::string,json::Value> classes_;
    std::size_t fuel_{250000};
    std::string instance_;
    bool explicitReference_{};
    Value call(Value,const std::vector<Value>&,const std::map<std::string,Value>& = {});
    Value function(const json::Value&,std::vector<Value>,const std::map<std::string,Value>&,const std::shared_ptr<Environment>& = {});
    Value attribute(Value,const std::string&);
    void assign(const json::Value&,Value,Environment&);
    void comprehension(const json::Value&,Environment&,std::size_t,std::vector<Value>&,std::vector<std::pair<Value,Value>>* = nullptr);
    void consume();
};
} // namespace fathom::tasks::ear234::closed
