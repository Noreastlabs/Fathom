#pragma once
#include "storage/BackupPublication.hpp"
#include "storage/RestorePreparation.hpp"
#include <chrono>
#include <filesystem>
#include <functional>

namespace fathom::storage {
// A private, standalone snapshot stage. This is not a published backup archive.
struct BackupSnapshotOptions {
    std::filesystem::path destinationDirectory;
    bool stopped = false;
    bool unresolvedWrites = true;
    // Opt-in staged archive1 metadata; still no ZIP publication or restore.
    bool includeArchiveManifest = false;
    // Requires includeArchiveManifest; an unpublished verified candidate.zip only.
    bool includeArchiveContainer = false;
    // Opt-in publication remains inside this same maintenance job.
    std::optional<BackupPublicationRequest> publication;
    // Mutually exclusive with publication; keeps the same maintenance reservation.
    std::optional<RestorePreparationRequest> restorePreparation;
    std::chrono::milliseconds timeout{300000};
    // Called on the writer; the caller must provide a thread-safe, bounded query.
    std::function<bool()> cancelled;
};
} // namespace fathom::storage
