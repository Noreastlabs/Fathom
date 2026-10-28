#pragma once
#include "core/Quantity.hpp"
#include "content/StrictJson.hpp"
#include <cstddef>
#include <optional>
#include <string>
#include <vector>

namespace fathom::tasks::source_contacts {
enum class PickVariant { Unspecified, Down, Up };
struct Atom final {
    std::size_t sourceOrdinal;
    std::string stringLabel,kind,spelling,attack,technique,annotationsJson;
    std::optional<int> stringLowToHigh,physicalFret,soundingFret,referenceFret,midi,finger;
    std::optional<bool> picked,audible;
    std::optional<Rational> onset,handSlotDuration;
    std::optional<std::string> pick;
    std::string sourceFactsJson;
    // No acoustic sounding span is supplied by this family.
};
struct Cue final {
    std::string sourceKey,sourceIdentity,sourceRecordSha256;
    std::size_t routeIndex,ordinal;
    std::vector<Atom> atoms; // Atomic printed simultaneous groups stay together.
    bool simultaneous;
};
class Definition final {
public:
    const char* sourceKey() const;
    const char* sourceIdentity() const;
    const char* sourceRecordSha256() const;
    const char* packetPath() const;
    const char* packetSha256() const;
    int packetLine() const;
    int level() const;
    std::size_t contactCount() const { return contactCount(0); }
    std::size_t contactCount(std::size_t route) const;
    std::size_t sourceAtomCount() const;
    std::size_t routeCount() const;
    std::vector<PickVariant> savedPickVariants(std::size_t route=0) const;
    std::optional<Rational> selectedMetricEnd(std::size_t route=0) const;
    Cue contact(std::size_t exactOrdinal,PickVariant,std::size_t route=0) const;
    void requireSourceParity(const Cue&,PickVariant) const;
    std::string trustedMetadataJson() const;
    std::string trustedContextJson() const;
    std::string sourceProgramJson(std::size_t route=0) const;
    std::string sourceAtomsJson(std::size_t route=0) const;
private:
    explicit Definition(std::size_t index):index_(index) {}
    std::size_t index_;
    friend const Definition& definition(const std::string&);
};
const std::vector<std::string>& keys();
const Definition& definition(const std::string& exactSourceKey);
const char* closureSha256();
// Pure closed-schema/manual comparison. Null, negative, whitespace and failed
// literal criteria remain unresolved. The shared Task owns histories and debts.
bool phaseReportResolved(const json::Value& phase,const json::Value& report);
void validateReport(const json::Value& schema,const json::Value& report);
} // namespace fathom::tasks::source_contacts
