#pragma once

#include "storage/ProfileStore.hpp"

#include <filesystem>
#include <functional>
#include <string>

namespace fathom::desktop {

struct PortableRestoreRequest {
    std::filesystem::path profile;
    std::filesystem::path archive;
    std::filesystem::path stage;
    std::filesystem::path availableMetadata;
};

struct PreparedPortableRestore {
    PortableRestoreRequest request;
    storage::Reply preparation;
    std::filesystem::path preview;
    storage::Value previewFile;
    storage::Value availableReferences;
    std::string confirmationSha256;
    std::string profileId;
};

struct AppliedPortableRestore {
    storage::Reply application;
    storage::Reply reopened;
};

// Application-facing orchestration only. Storage semantics and restore
// authority remain in ProfileStore; this service supplies explicit paths,
// availability metadata, confirmation, and normal reopen verification.
class PortableRestoreWorkflow final {
public:
    // Empty in production; permits deterministic fault injection after external
    // archive preflight and before the selected snapshot copy.
    static PreparedPortableRestore prepare(const PortableRestoreRequest&,
                                           const std::function<void()>& afterPreflight = {});
    static PreparedPortableRestore loadPrepared(const std::filesystem::path& profile,
                                                const std::filesystem::path& preview,
                                                const std::filesystem::path& availableMetadata,
                                                std::string confirmationSha256);
    static AppliedPortableRestore apply(const PreparedPortableRestore&);
};

} // namespace fathom::desktop
