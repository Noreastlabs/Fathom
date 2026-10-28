#pragma once
#include "core/MusicModel.hpp"
#include <cstddef>
#include <string>
#include <vector>

namespace fathom::tasks::ordered_contacts {
enum class Start { Down, Up, Unspecified };

// A closed generated source-data family. No caller-built definitions, runtime
// loader, release token, physical observation, or full-exercise completion API.
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
    Rational metricEnd() const; // Selected hand-slot endpoint; not ending silence.
    std::string retainedMetadataJson() const;
    music::Model reference(Start) const;
    // Checks the whole reference against its trusted frozen source data. A
    // coherent but altered pitch can pass music::validate and still refuse here.
    void requireSourceParity(const music::Model&, Start) const;
private:
    explicit Definition(std::size_t index) : index_(index) {}
    std::size_t index_;
    friend const Definition& definition(const std::string&);
};

const std::vector<std::string>& keys();
const Definition& definition(const std::string& exactSourceKey);
const char* cohortSha256();
const char* closureSha256();
std::size_t sharedContextCount();
} // namespace fathom::tasks::ordered_contacts
