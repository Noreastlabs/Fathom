#pragma once
#include "content/LoadCancellation.hpp"
#include "content/StrictJson.hpp"
#include <filesystem>
#include <memory>
#include <optional>
#include <string>

namespace fathom::content {
// Semantic data from an archived validator report, never its purported raw bytes.
struct SemanticPredecessorProjection {
    std::string validatorVersion;
    bool validReference{};
    json::Value records;
};
// A capability minted only after the compiled transport pin and closed physical
// layout validate. Logical package/decision identities remain unchanged.
class CleanRuntimeEnvelope final {
  public:
    static std::shared_ptr<const CleanRuntimeEnvelope>
    open(const std::filesystem::path &package, const std::string &logicalManifestSha,
         const std::string &logicalManifestName = "manifest.json",
         const CancellationCheck &canceled = {});
    const std::string &transportSha() const noexcept { return transportSha_; }
    const std::filesystem::path &packageRoot() const noexcept { return package_; }
    bool hasArchivedEvidence(const std::string &logicalPath) const;
    void verifyArchivedEvidence(const std::string &logicalPath, const std::string &originalSha,
                                std::optional<std::size_t> originalBytes = {}) const;
    SemanticPredecessorProjection readSemanticProjection(const std::string &logicalPath,
                                                         const std::string &originalSha) const;
    // Every physically consumed payload is checked against the new pinned tree,
    // in addition to the existing logical package/source hashes.
    void verifyPayload(const std::filesystem::path &resolved, const std::string &bytes) const;
    void verifyState() const;

  private:
    CleanRuntimeEnvelope(std::filesystem::path, std::filesystem::path, json::Value, std::string,
                         CancellationCheck);
    std::string archiveKey(const std::string &) const;
    std::string localKey(const std::string &) const;
    std::string retainedBytes(const std::string &) const;
    void verifyTransportPin() const;
    std::filesystem::path safePhysical(const std::string &) const;
    std::filesystem::path root_, package_;
    std::string prefix_, transportSha_;
    json::Value manifest_;
    CancellationCheck canceled_;
};
} // namespace fathom::content
