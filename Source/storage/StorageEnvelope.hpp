#pragma once
#include "content/StrictJson.hpp"
#include "core/Quantity.hpp"
#include <optional>
#include <string>

namespace fathom::storage {
using Value=json::Value;
struct EnvelopeError:std::runtime_error{
    std::string code;
    EnvelopeError(std::string code,std::string message);
};
struct Envelope {
    Value value;
    std::string bytes,owner,kind,contextBytes,digest,practiceUtc,timezone,day,outcome;
    std::optional<std::string> assessment;
    Rational active;
};
// Reject noncanonical first-seal input. This never replaces an existing sealed payload.
std::string canonical(const Value&);
Value parseCanonical(const std::string&);
void validateUuid(const std::string&);
void validateContext(const Value&,const std::string& kind,bool standalone=false);
Envelope validateEnvelope(const std::string& bytes);
void validateCheckpoint(const std::string& owner,std::int64_t generation,std::int64_t sequence,
                        const std::string& bytes,const std::string& kind,const Value& allocatedContext);
void validateAttestation(const Value&,const std::string& profileId,
                         const std::optional<Value>& linkedAttemptContext);
void validateRuleObservation(const Value&);
} // namespace fathom::storage
