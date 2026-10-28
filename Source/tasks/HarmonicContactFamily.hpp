#pragma once
#include "core/Quantity.hpp"
#include "content/StrictJson.hpp"
#include <cstddef>
#include <optional>
#include <string>
#include <vector>

namespace fathom::tasks::harmonic_contacts {
enum class PickVariant { Unspecified, Down, Up };
struct ManualSpan final { Rational onset, duration; };
struct Cue final {
    std::string sourceKey,sourceIdentity,sourceRecordSha256;
    std::size_t ordinal;
    int stringLowToHigh,fret,midi;
    std::optional<int> finger;
    std::string stringLabel,spelling,annotationsJson,attackAuthority;
    std::optional<std::string> pick;
    std::optional<ManualSpan> sourceMetricSpan,acousticSoundingSpan;
    int blockIndex,gridColumn,sourceLine,sourceColumn1Based;
};
// A value-owned index into one closed immutable source table. No music model.
class Definition final {
public:
    const char* sourceKey() const;
    const char* sourceIdentity() const;
    const char* sourceRecordSha256() const;
    const char* packetPath() const;
    const char* packetSha256() const;
    int packetLine() const;
    int level() const;
    std::size_t contactCount() const;
    std::vector<PickVariant> savedPickVariants() const;
    std::optional<Rational> selectedMetricEnd() const;
    Cue contact(std::size_t exactOrdinal,PickVariant) const;
    void requireSourceParity(const Cue&,PickVariant) const;
    std::string trustedMetadataJson() const;
    std::string trustedContextJson() const;
    std::string sourceProgramJson() const;
    std::string sourceAtomsJson() const;
    bool reportPhaseResolved(std::size_t exactPhase,const json::Value& manualReport) const;
private:
    explicit Definition(std::size_t index):index_(index) {}
    std::size_t index_;
    friend const Definition& definition(const std::string&);
};
const std::vector<std::string>& keys();
const Definition& definition(const std::string& exactSourceKey);
const char* closureSha256();
// Pure source-schema comparison. The shared owner retains raw reports/history.
// Negative/null/unknown outcomes return false; malformed objects throw.
bool phaseReportResolved(const json::Value& closedPhase,const json::Value& manualReport);
} // namespace fathom::tasks::harmonic_contacts
