#pragma once
#include "tasks/PhysicalContactFamily.hpp"

namespace fathom::tasks::piecewise_contacts {
using Start=physical_contacts::Start;
struct Cue final { physical_contacts::Cue source; std::string spelling; int degree; };
struct RouteCue final { std::string label; bool assignedFrameBefore,pressureReleaseBefore; };
// Closed cached A17 source handle. Saved MIDI is encoding, never audio authority.
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
    Cue contact(std::size_t exactOrdinal,Start) const;
    RouteCue routeCue(std::size_t exactOrdinal) const;
    void requireSourceParity(const Cue&,Start) const;
    std::string trustedMetadataJson() const;
    std::string trustedContextJson() const;
private:
    explicit Definition(std::size_t index):index_(index) {}
    std::size_t index_;
    friend const Definition& definition(const std::string&);
};
const std::vector<std::string>& keys();
const Definition& definition(const std::string& exactSourceKey);
const char* closureSha256();
} // namespace fathom::tasks::piecewise_contacts
