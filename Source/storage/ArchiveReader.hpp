#pragma once
#include "storage/StorageEnvelope.hpp"
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <functional>

namespace fathom::storage {
struct ArchiveReaderOptions {
    std::filesystem::path archive;
    std::filesystem::path candidateDirectory; // New absolute directory under a private parent.
    std::chrono::milliseconds timeout{300000};
    std::function<bool()> cancelled;
    // Space for a restore original/readback still to be materialized by caller.
    std::uint64_t additionalReserveBytes=0;
    bool reserveSecondCandidate=false; // Restore apply needs a separate incoming image.
    // Synchronous diagnostic phases, never audio or learner observations.
    std::function<void(const std::string&)> diagnosticHook;
};
// Extracts and verifies an isolated candidate. Never opens/replaces a live profile.
// Failure throws EnvelopeError and leaves any partial candidate explicitly incomplete.
Value previewProfileArchive(const ArchiveReaderOptions&);
namespace detail {
// Storage-layer inspection of a pinned private standalone candidate; no writer transition.
// check must validate the caller's held file/directory identities and deadline.
Value inspectArchiveCandidate(int descriptor,const std::filesystem::path&,
                              const std::function<void()>& check,
                              const std::function<void(const std::string&)>& hook);
}
} // namespace fathom::storage
