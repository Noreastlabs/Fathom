#pragma once
#include "content/StrictJson.hpp"
#include "content/LoadCancellation.hpp"
#include "core/MusicModel.hpp"
#include <filesystem>

namespace fathom::content {
class CleanRuntimeEnvelope;
struct Limits {
    json::Limits json;
    std::size_t records=10000, events=200000, sources=10000, entities=100000;
    std::size_t assetBytes=256*1024*1024, totalAssetBytes=1024*1024*1024;
};
struct Input {
    std::string package, registry, profile, expectedProfileSha256;
    std::filesystem::path sourceRoot;
    CancellationCheck canceled{};
    std::shared_ptr<const CleanRuntimeEnvelope> installedRuntime{};
};
struct RecordResult {
    std::string id;
    music::Model source;
    music::Validation validation;
    music::Readiness readiness;
};
struct VariantResult {
    std::string id, itemId;
    music::Model source;
    music::Validation validation;
    music::Readiness readiness;
    bool bindingsComplete=false;
};
struct Result {
    json::Value report;
    std::vector<RecordResult> records;
    std::vector<VariantResult> variants;
    bool validReference=false;
    int exitCode=1; // 1 invalid; 2 valid reference, never runtime admission in proposal or candidate schema.
};
std::string sha256(const std::string& bytes);
std::string readBounded(const std::filesystem::path&, std::size_t limit,
    const CancellationCheck& canceled = {});
// Integrity-only archival attestation; never supplies missing original bytes.
void verifyArchivedEvidence(const Input&,const std::string& logicalPath,const std::string& originalSha);
Result validate(const Input&, const Limits& = {});
} // namespace fathom::content
