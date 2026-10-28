#pragma once
#include "tasks/OrderedContactFamily.hpp"
#include "tasks/PhysicalContactFamily.hpp"
#include "tasks/PiecewiseContactFamily.hpp"
#include "tasks/HarmonicContactFamily.hpp"
#include "tasks/SourceContactFamily.hpp"
#include <memory>
#include <variant>

namespace fathom::tasks::manual_contacts {
enum class Family { OrderedContact, PhysicalContact, PiecewiseContact, HarmonicContact, SourceContact };
enum class Start { Down, Up, Unspecified };
struct OrderedPolicyTag { int level; };
struct PhysicalPolicyTag { int level; };
struct PiecewisePolicyTag { int level; };
struct HarmonicPolicyTag { int level; };
struct SourceContactPolicyTag { int level; };
using PolicyTag=std::variant<OrderedPolicyTag,PhysicalPolicyTag,PiecewisePolicyTag,HarmonicPolicyTag,SourceContactPolicyTag>;
struct RelativeHandSlot { Rational onset,duration; };
// Trusted source projection fields. A learner renderer consumes an owner's
// whitelisted descriptor, never custody, expected annotations or this struct.
struct Contact final {
    std::size_t ordinal;
    int stringLowToHigh,fret,finger;
    std::string stringLabel,pick;
    std::optional<int> midi;
    std::string spelling;
    RelativeHandSlot selectedRelativeHandSlot;
    std::optional<RelativeHandSlot> acousticSoundingSpan;
    std::string sourceRef,annotationsJson,attackAuthority;
    std::optional<int> blockIndex,gridColumn,sourceLine,sourceColumn1Based;
    std::optional<int> degree{};
};
struct Projection final {
    Family family;
    Start start;
    std::string sourceKey,sourceIdentity,sourceRecordSha256;
    int level;
    Rational selectedMetricEnd;
    std::vector<Contact> contacts;
    bool legacyMusicModelUsed;
    // Every projection is source-relative hand data only; no clock/sound claim.
};
class SourceHandle final {
public:
    static SourceHandle ordered(const ordered_contacts::Definition&);
    static SourceHandle physical(const physical_contacts::Definition&);
    static SourceHandle piecewise(const piecewise_contacts::Definition&);
    static SourceHandle harmonic(const harmonic_contacts::Definition&);
    static SourceHandle sourceContact(const source_contacts::Definition&);
    static SourceHandle orderedKey(const std::string& exactKey);
    static SourceHandle physicalKey(const std::string& exactKey);
    static SourceHandle piecewiseKey(const std::string& exactKey);
    static SourceHandle harmonicKey(const std::string& exactKey);
    static SourceHandle sourceContactKey(const std::string& exactKey);
    SourceHandle(const SourceHandle&)=default;
    SourceHandle& operator=(const SourceHandle&)=delete;
    Family family() const noexcept;
    const char* sourceKey() const;
    const char* sourceIdentity() const;
    const char* sourceRecordSha256() const;
    const char* packetPath() const;
    const char* packetSha256() const;
    int packetLine() const;
    int level() const;
    std::size_t contactCount() const;
    Rational selectedMetricEnd() const;
    PolicyTag policyTag() const;
    std::string trustedMetadataJson() const;
    // Returned immutable data owns its lifetime independently of this handle.
    std::shared_ptr<const Projection> projection(Start) const;
    Contact contact(std::size_t exactOrdinal,Start) const;
    void requireSourceParity(const Projection&,Start) const;
    // Optional source fields never pass through the legacy mandatory projection.
    harmonic_contacts::Cue harmonicContact(std::size_t exactOrdinal,Start) const;
    std::optional<Rational> harmonicMetricEnd() const;
    std::string harmonicProgramJson() const;
    std::string harmonicContextJson() const;
    source_contacts::Cue sourceAtomContact(std::size_t exactOrdinal,Start,std::size_t route=0) const;
    std::string phaseProgramJson(std::size_t route=0) const;
    std::string phaseContextJson() const;
    std::string phaseAtomsJson(std::size_t route=0) const;
    std::optional<Rational> phaseMetricEnd(std::size_t route=0) const;
    std::size_t sourceRouteCount() const;
    std::size_t sourceRouteContactCount(std::size_t route) const;
private:
    using ClosedDefinition=std::variant<ordered_contacts::Definition,physical_contacts::Definition,piecewise_contacts::Definition,harmonic_contacts::Definition,source_contacts::Definition>;
    explicit SourceHandle(ClosedDefinition);
    const ClosedDefinition definition_;
    struct Cache;
    std::shared_ptr<Cache> cache_;
};
// Proof instrumentation counts the actual legacy-only construction branch.
std::size_t legacyProjectionBuildCount() noexcept;
} // namespace fathom::tasks::manual_contacts
