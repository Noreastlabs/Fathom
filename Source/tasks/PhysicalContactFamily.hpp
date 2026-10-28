#pragma once
#include "core/Quantity.hpp"
#include <cstddef>
#include <optional>
#include <string>
#include <vector>

namespace fathom::tasks::physical_contacts {
enum class Start { Down, Up };
// Dispatch template, not a claim that source policies have identical behavior.
enum class WorkflowPattern { FourNoteRoll, ThreeNoteRoll, LinearEighth, DiatonicPairs,
    DiatonicTriads, FiveModuleCircuit, PentatonicOddGroups, PentatonicSkips };
struct ManualSpan final { Rational onset, duration; };
struct Cue final {
    std::string sourceKey, sourceIdentity, sourceRecordSha256;
    std::size_t ordinal;
    int stringLowToHigh, fret, finger;
    std::string stringLabel, pick, annotationsJson;
    int blockIndex, gridColumn, sourceLine, sourceColumn1Based;
    std::string attackAuthority;
    ManualSpan selectedRelativeHandSlot;
    std::optional<int> midi;
    std::optional<ManualSpan> acousticSoundingSpan;
};
// Closed immutable generated-row handle, inexpensive and safe to retain by value.
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
    Rational selectedMetricEnd() const;
    const char* selectedProjection() const;
    WorkflowPattern workflowPattern() const;
    Cue contact(std::size_t exactOrdinal, Start) const;
    void requireSourceParity(const Cue&, Start) const;
    std::string trustedMetadataJson() const;
    std::string trustedSourcePolicyJson() const;
private:
    explicit Definition(std::size_t index) : index_(index) {}
    std::size_t index_;
    friend const Definition& definition(const std::string&);
};
const std::vector<std::string>& keys();
const Definition& definition(const std::string& exactSourceKey);
const char* cohortSha256();
const char* closureSha256();
std::size_t sourcePolicyCount();
// No MusicModel, player, rendered pitch, clock, admission or completion API.
} // namespace fathom::tasks::physical_contacts
