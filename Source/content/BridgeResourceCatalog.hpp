#pragma once

#include <filesystem>
#include <string>
#include <vector>

namespace fathom::content {

struct BridgeSourceLink {
    std::string passageId;
    std::string path;
    std::string sourceSha256;
    std::string passageSha256;
    std::vector<int> lines;
    int page = 0;
};

struct BridgePassage {
    std::string id;
    std::string format;
    std::string path;
    std::string sourceSha256;
    std::string textSha256;
    std::string text;
    int level = 0;
    int page = 0;
    int firstLine = 0;
    int lastLine = 0;
};

struct BridgeCard {
    std::string id;
    std::string kind;
    std::string title;
    std::string summary;
    std::string availability;
    std::string approvedRequirementJson;
    std::string proposedPreviewJson;
    int legacyLevel = 0;
    std::vector<int> appliesToLevels;
    std::vector<std::string> sourceRefs;
    std::vector<std::string> publicSourceRefs;
    std::vector<std::string> tags;
    std::vector<std::string> searchTerms;
    std::vector<std::string> prerequisiteLinks;
    std::vector<std::string> requiredOutputs;
    std::vector<std::string> selectionConstraints;
    std::vector<BridgeSourceLink> sourceLinks;
    bool runtimeAdmitted = false;
    bool hasSuppliedAsset = false;
    bool hasProposedPreview = false;
    bool runtimeNetwork = false;
    bool inAppImport = false;
    bool inAppRecorder = false;
    bool newWordingCurriculumAccepted = false;
};

struct BridgeSourceBinding {
    std::string path;
    std::string sha256;
};

// Read-only access to the sealed offline bridge/resource bundle. This catalog
// exposes no lesson, recording, playback, Attempt, or admission operation.
class BridgeResourceCatalog final {
public:
    static BridgeResourceCatalog load(const std::filesystem::path& bundleRoot,
                                      const std::filesystem::path& sourceRoot);

    const std::vector<BridgeCard>& cards() const noexcept { return cards_; }
    const std::vector<BridgePassage>& passages() const noexcept { return passages_; }
    const std::vector<BridgeSourceBinding>& sourceBindings() const noexcept { return sourceBindings_; }
    std::size_t verifiedPassageCount() const noexcept { return verifiedPassageCount_; }
    const BridgeCard* find(const std::string& id) const noexcept;
    const BridgePassage* findPassage(const std::string& id) const noexcept;
    std::vector<std::string> search(const std::string& query) const;
    bool offline() const noexcept { return offline_; }
    bool runtimeAdmitted() const noexcept { return runtimeAdmitted_; }

private:
    std::vector<BridgeCard> cards_;
    std::vector<BridgePassage> passages_;
    std::vector<BridgeSourceBinding> sourceBindings_;
    std::size_t verifiedPassageCount_ = 0;
    bool offline_ = false;
    bool runtimeAdmitted_ = true;
};

} // namespace fathom::content
