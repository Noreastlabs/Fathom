#pragma once
#include "storage/ProfileStore.hpp"
#include <chrono>

namespace fathom::storage {
struct CompatibilityOptions {
    std::filesystem::path original,stage;
    std::string operation,applicationVersion,applicationBuildSha256;
    std::int64_t targetDataSchema=2;
    bool stopped=false,unresolvedWrites=true;
    // Inspection capacity, never a history retention/deletion limit.
    std::uint64_t maxImageBytes=1024ULL*1024*1024;
    std::chrono::milliseconds copyDeadline{30000};
    // Empty in application use. Bounded evidence hooks execute off audio.
    std::function<void(const std::string&)> diagnosticHook;
};
// No SQL opens/writes on original. Owns its profile lease while capturing and
// validating an isolated candidate. No transformed migration or publication.
Reply inspectCompatibility(const CompatibilityOptions&);
// Exact historical content lookup on an original confirmed snapshot. Available
// entries are explicit metadata references, not content/runtime admission.
Value historicalContentContinuity(const Reply&,const Value& availableEntries);
} // namespace fathom::storage
