#pragma once
#include <cstddef>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

namespace fathom::json {
struct Number { std::string token; bool operator==(const Number& n) const { return token == n.token; } };
struct Value {
    using Array = std::vector<Value>;
    using Object = std::map<std::string, Value>;
    std::variant<std::nullptr_t, bool, Number, std::string, Array, Object> data = nullptr;
    Value() = default;
    Value(std::nullptr_t) : data(nullptr) {}
    Value(bool b) : data(b) {}
    Value(Number n) : data(std::move(n)) {}
    Value(std::string s) : data(std::move(s)) {}
    Value(const char* s) : data(std::string(s)) {}
    Value(Array a) : data(std::move(a)) {}
    Value(Object o) : data(std::move(o)) {}
    static Value fromInteger(std::int64_t n);
    bool null() const { return std::holds_alternative<std::nullptr_t>(data); }
    bool isBool() const { return std::holds_alternative<bool>(data); }
    bool isNumber() const { return std::holds_alternative<Number>(data); }
    bool isString() const { return std::holds_alternative<std::string>(data); }
    bool isArray() const { return std::holds_alternative<Array>(data); }
    bool isObject() const { return std::holds_alternative<Object>(data); }
    const std::string& string() const { return std::get<std::string>(data); }
    const Array& array() const { return std::get<Array>(data); }
    Array& array() { return std::get<Array>(data); }
    const Object& object() const { return std::get<Object>(data); }
    Object& object() { return std::get<Object>(data); }
    bool boolean() const { return std::get<bool>(data); }
    bool integer(std::int64_t& n) const noexcept;
    const Value* find(const std::string& key) const;
    bool operator==(const Value& v) const { return data == v.data; }
    bool operator!=(const Value& v) const { return !(*this == v); }
};
struct Limits {
    std::size_t bytes = 32 * 1024 * 1024, depth = 64, stringBytes = 1024 * 1024;
    std::size_t values = 1000000, numberBytes = 128;
};
struct Error : std::runtime_error {
    std::string code;
    std::size_t offset;
    Error(std::string code, std::size_t offset, const std::string& message);
};
Value parse(const std::string&, const Limits& = {});
std::string stringify(const Value&);
} // namespace fathom::json
