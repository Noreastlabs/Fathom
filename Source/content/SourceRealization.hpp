#pragma once
#include "core/MusicModel.hpp"
#include <array>
#include <stdexcept>
#include <string>

namespace fathom::content::realization {
// A separately held active setup snapshot; a wire claim alone does not select it.
struct ActiveSetup final {
    std::array<int, 6> openMidi{{40,45,50,55,59,64}};
    int capo = 0;
    int fretCount = 22;
};

class SourceOnly final {
public:
    SourceOnly(const SourceOnly&) = default;
    const std::string& oracleId() const noexcept { return oracleId_; }
    int oracleVersion() const noexcept { return oracleVersion_; }
    const std::string& oracleSha256() const noexcept { return oracleSha256_; }
    const std::string& sourceSha256() const noexcept { return sourceSha256_; }
    // Deliberately no Tone, reference Program, Practice or Attempt surface.
private:
    SourceOnly(std::string oracleId, int oracleVersion,
               std::string oracleSha256, std::string sourceSha256);
    const std::string oracleId_, oracleSha256_, sourceSha256_;
    const int oracleVersion_;
    friend SourceOnly validateSource(const std::string& sourceJson);
};

class DeclaredRealization final {
public:
    DeclaredRealization(const DeclaredRealization&) = default;
    const SourceOnly source;
    const std::string choiceState; // always declared-unconfirmed; no learner-action attestation
    const std::string declaredSha256;
    const int selectedBpm;
    const int sampleRateHz;
    const std::string method;
    const music::Model candidate; // technical projection only; no Catalog permission or credit
private:
    DeclaredRealization(SourceOnly source, std::string choiceState,
                        std::string declaredSha256, int selectedBpm,
                        int sampleRateHz, std::string method, music::Model candidate);
    friend DeclaredRealization validateDeclaredChoice(const SourceOnly& source,
                                                       const std::string& choiceJson,
                                                       const ActiveSetup& activeSetup);
};

struct Error : std::runtime_error {
    std::string code;
    Error(std::string code, const std::string& message);
};

// The compiled oracle is the trust root, not an input. Exposed solely for
// independently checking its bytes against originals and review evidence.
const std::string& compiledOracleBytes();
SourceOnly validateSource(const std::string& sourceJson);
DeclaredRealization validateDeclaredChoice(const SourceOnly& source,
                                            const std::string& choiceJson,
                                            const ActiveSetup& activeSetup);
} // namespace fathom::content::realization
