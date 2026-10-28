#pragma once
#include "storage/StorageEnvelope.hpp"
#include <vector>

namespace fathom::progression {
using Value=json::Value;
struct HistoryError:std::runtime_error { using std::runtime_error::runtime_error; };
enum class Kind { Attempt, Freeplay, Acknowledgment, Source };
struct Segment {
    Rational tempo,active;
    bool wholeTarget=false;
    Value::Array cycles;
};
// Transient facts. The store adapter supplies original identities and bindings;
// these are not a second persistent record schema or an audio-thread interface.
struct Evidence {
    Kind kind=Kind::Attempt;
    std::string key,originalBytes,status="committed",item,session,at,timezone,day;
    Value condition,sourceScope,assessment,attestation;
    Rational active;
    bool complete=false;
    Value::Array completedCycles;
    std::vector<Segment> segments;
};
struct Query { std::string item; Value condition,sourceScope; };
const Value& initialRules();
const Value& sourceRules();
std::string rulesIdentity();
std::string sourceRulesIdentity();
Rational quantity(const Value&);
Value quantityValue(const Rational&);
std::int64_t utcMicros(const std::string&);
std::string utcString(std::int64_t);
void validateCondition(const Value&);
Value queryValue(const Query&);
// Explicit rule argument supports isolated rule sensitivity tests. Production
// Repository registers only the embedded accepted initialRules definition.
Value project(const std::vector<Evidence>&,const Query&,const std::string& asOf,
              const Value& rules=initialRules());
} // namespace fathom::progression
