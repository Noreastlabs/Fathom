#include "desktop/PortableRestoreWorkflow.hpp"

#include "content/Canonical.hpp"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <sys/stat.h>
#include <vector>

namespace {
namespace fs = std::filesystem;
using fathom::desktop::PortableRestoreRequest;
using fathom::desktop::PortableRestoreWorkflow;
using fathom::storage::ProfileStore;
using fathom::storage::Status;
using fathom::storage::StoreOptions;
using fathom::storage::Value;
using Object = Value::Object;
using Array = Value::Array;

void require(bool condition, const std::string& message) {
    if (!condition)
        throw std::runtime_error(message);
}

class BackupStepGate final {
public:
    void holdWorker() {
        std::unique_lock<std::mutex> lock(mutex_);
        entered_ = true;
        condition_.notify_all();
        if (!condition_.wait_for(lock, std::chrono::seconds(5), [this] { return released_; }))
            throw std::runtime_error("Bounded backup-step diagnostic gate timed out");
    }

    void waitForWorker() {
        std::unique_lock<std::mutex> lock(mutex_);
        require(condition_.wait_for(lock, std::chrono::seconds(5), [this] { return entered_; }),
                "Backup diagnostic hook did not reach backup_step");
    }

    void releaseWorker() {
        std::lock_guard<std::mutex> lock(mutex_);
        released_ = true;
        condition_.notify_all();
    }

    bool entered() {
        std::lock_guard<std::mutex> lock(mutex_);
        return entered_;
    }

private:
    std::mutex mutex_;
    std::condition_variable condition_;
    bool entered_ = false;
    bool released_ = false;
};

void directory(const fs::path& path) {
    require(fs::create_directory(path), "Directory already exists: " + path.string());
    require(chmod(path.c_str(), 0700) == 0, "Cannot protect directory: " + path.string());
}

std::string readFile(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    require(static_cast<bool>(input), "Cannot read " + path.string());
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

void writeNew(const fs::path& path, const std::string& bytes) {
    require(!fs::exists(path), "Evidence file already exists: " + path.string());
    std::ofstream output(path, std::ios::binary);
    require(static_cast<bool>(output), "Cannot write " + path.string());
    output << bytes;
    output.close();
    require(static_cast<bool>(output) && chmod(path.c_str(), 0600) == 0,
            "Cannot protect evidence file: " + path.string());
}

void copyPrivate(const fs::path& from, const fs::path& to) {
    require(fs::copy_file(from, to), "Cannot copy fixture " + from.string());
    require(chmod(to.c_str(), 0600) == 0, "Cannot protect fixture copy: " + to.string());
}

Value snapshot(const fs::path& profile, const std::string& operation) {
    StoreOptions options;
    options.path = profile;
    ProfileStore store(options);
    auto reply = store.snapshot(operation).get();
    require(reply.status == Status::Confirmed, "Snapshot failed: " + reply.code);
    return reply.data;
}

std::string sha256(const fs::path& path) {
    return fathom::content::sha256(readFile(path));
}

void writeReply(const fs::path& path, const fathom::storage::Reply& reply) {
    writeNew(path, fathom::storage::canonical(Object{
        {"status", fathom::storage::statusName(reply.status)},
        {"operation", reply.operation}, {"owner", reply.owner},
        {"code", reply.code}, {"message", reply.message}, {"data", reply.data}}));
}

fs::path prepareMetadata(const fs::path& evidence, const fs::path& fixtureRoot) {
    const auto manifest = fathom::storage::parseCanonical(readFile(fixtureRoot / "rich/manifest.json"));
    auto reference = manifest.object().at("snapshot").object().at("content_references").array().front();
    reference.object().erase("reference_kind");
    const Array available{Object{{"reference", reference},
                                {"provenance", "r10 retained synthetic control metadata"}}};
    const auto path = evidence / "available-metadata.json";
    writeNew(path, fathom::storage::canonical(available));
    return path;
}

std::vector<std::string> referenceIdentities(const Value& manifest) {
    std::vector<std::string> identities;
    const auto& references = manifest.object().at("snapshot").object()
                                 .at("content_references").array();
    for (const auto& reference : references)
        identities.push_back(fathom::storage::canonical(reference));
    std::sort(identities.begin(), identities.end());
    return identities;
}

PortableRestoreRequest setup(const fs::path& root, const fs::path& fixtureRoot,
                             const fs::path& metadata, const std::string& name) {
    const auto work = root / name;
    directory(work);
    directory(work / "live");
    copyPrivate(fixtureRoot / "rich/profile.sqlite", work / "live/profile.sqlite");
    copyPrivate(fixtureRoot / "rich/candidate.zip", work / "incoming.zip");
    return {work / "live/profile.sqlite", work / "incoming.zip", work / "stage", metadata};
}

void successCase(const fs::path& evidence, const fs::path& fixtureRoot,
                 const fs::path& metadata) {
    const auto request = setup(evidence / "workflow", fixtureRoot, metadata, "successful-apply");
    const auto beforeBytes = sha256(request.profile);
    const auto beforeState = snapshot(request.profile, "workflow-before-prepare");
    const auto prepared = PortableRestoreWorkflow::prepare(request);
    require(prepared.preparation.status == Status::Confirmed,
            "Prepare did not return Confirmed");
    require(prepared.preparation.code == "RESTORE_PREPARED",
            "Prepare did not return RESTORE_PREPARED");
    require(fs::is_regular_file(prepared.preview), "Prepared preview is missing");
    require(!prepared.confirmationSha256.empty(), "Prepared confirmation is missing");
    const auto afterPrepareBytes = sha256(request.profile);
    writeNew(evidence / "workflow/prepare-raw-byte-observation.json",
             fathom::storage::canonical(Object{{"raw_bytes_before", beforeBytes},
                                               {"raw_bytes_after", afterPrepareBytes},
                                               {"raw_bytes_changed", beforeBytes != afterPrepareBytes},
                                               {"raw_bytes_are_semantic_authority", false}}));
    const auto afterPrepareState = snapshot(request.profile, "workflow-after-prepare");
    writeNew(evidence / "workflow/prepare-before-state.json", fathom::storage::canonical(beforeState));
    writeNew(evidence / "workflow/prepare-after-state.json", fathom::storage::canonical(afterPrepareState));
    require(afterPrepareState.object().at("profile_id") == beforeState.object().at("profile_id") &&
                afterPrepareState.object().at("authoritative") == beforeState.object().at("authoritative"),
            "Prepare changed authoritative live profile state");
    writeReply(evidence / "workflow/success-prepare.json", prepared.preparation);

    const auto applied = PortableRestoreWorkflow::apply(prepared);
    require(applied.application.status == Status::Confirmed &&
                applied.application.code == "RESTORE_APPLIED",
            "Apply did not complete: " + applied.application.code);
    require(applied.reopened.status == Status::Confirmed,
            "Applied profile did not reopen normally");
    require(applied.reopened.data.object().at("profile_id") ==
                applied.application.data.object().at("snapshot").object().at("profile_id"),
            "Reopened profile identity differs from applied snapshot");
    writeReply(evidence / "workflow/success-apply.json", applied.application);
    writeReply(evidence / "workflow/success-reopen.json", applied.reopened);
}

void wrongConfirmationCase(const fs::path& evidence, const fs::path& fixtureRoot,
                           const fs::path& metadata) {
    const auto request = setup(evidence / "workflow", fixtureRoot, metadata, "wrong-confirmation");
    const auto beforeBytes = sha256(request.profile);
    const auto beforeState = snapshot(request.profile, "workflow-before-wrong-confirmation");
    auto prepared = PortableRestoreWorkflow::prepare(request);
    prepared.confirmationSha256 = std::string(64, '0');
    const auto refused = PortableRestoreWorkflow::apply(prepared);
    require(refused.application.status != Status::Confirmed,
            "Wrong confirmation was accepted");
    require(refused.application.code == "RESTORE_CONFIRMATION",
            "Wrong confirmation returned unexpected code: " + refused.application.code);
    const auto afterBytes = sha256(request.profile);
    const auto afterState = snapshot(request.profile, "workflow-after-wrong-confirmation");
    writeNew(evidence / "workflow/wrong-confirmation-raw-byte-observation.json",
             fathom::storage::canonical(Object{{"raw_bytes_before", beforeBytes},
                                               {"raw_bytes_after", afterBytes},
                                               {"raw_bytes_changed", beforeBytes != afterBytes},
                                               {"raw_bytes_are_semantic_authority", false}}));
    writeNew(evidence / "workflow/wrong-confirmation-before-state.json", fathom::storage::canonical(beforeState));
    writeNew(evidence / "workflow/wrong-confirmation-after-state.json", fathom::storage::canonical(afterState));
    require(afterState.object().at("profile_id") == beforeState.object().at("profile_id") &&
                afterState.object().at("authoritative") == beforeState.object().at("authoritative"),
            "Wrong confirmation changed authoritative live profile state");
    writeReply(evidence / "workflow/wrong-confirmation.json", refused.application);
}

void combinedParentWorkflowCase(const fs::path& evidence, const fs::path& fixtureRoot) {
    const auto work = evidence / "workflow/combined-parent-workflow";
    directory(work);
    const auto sourceDirectory = work / "source";
    directory(sourceDirectory);
    const auto sourceProfile = sourceDirectory / "profile.sqlite";
    copyPrivate(fixtureRoot / "rich/profile.sqlite", sourceProfile);

    const auto beforeInterruption = snapshot(sourceProfile, "combined-parent-before-interruption");
    const auto& beforeInterruptionData = beforeInterruption.object();
    const auto& beforeInterruptionAuthority = beforeInterruptionData.at("authoritative");
    std::int64_t initialCommittedSequence = 0;
    require(beforeInterruptionData.at("committed_seq").integer(initialCommittedSequence) &&
                initialCommittedSequence > 0,
            "Combined source fixture has no committed profile boundary");
    require(!beforeInterruptionAuthority.object().at("finalized").array().empty(),
            "Combined source fixture is missing committed history");
    require(!beforeInterruptionAuthority.object().at("preferences").array().empty(),
            "Combined source fixture is missing settings");

    const auto cancelledStage = work / "cancelled-during-write-stage";
    const auto cancelledArchive = work / "cancelled-during-write.zip";
    const std::string cancelledOperation = "11111111-1111-4111-8111-111111111111";
    const std::string replacementOperation = "88888888-8888-4888-8888-888888888888";
    auto gate = std::make_shared<BackupStepGate>();
    auto replacementGate = std::make_shared<BackupStepGate>();
    std::atomic<bool> cancelSnapshot{false};
    std::atomic<bool> cancelReplacement{false};
    fathom::storage::StoreOptions sourceOptions;
    sourceOptions.path = sourceProfile;
    sourceOptions.preferenceValidator = [](const std::string& key, std::int64_t version,
                                           const Value& value) {
        return key == "backup.test.r02" && version == 1 && value.isObject();
    };
    sourceOptions.diagnosticHook = [gate, cancelledOperation, replacementGate,
                                    replacementOperation](const std::string& phase,
                                                          const std::string& operation) {
        if (phase == "backup_step" && operation == cancelledOperation)
            gate->holdWorker();
        if (phase == "backup_step" && operation == replacementOperation)
            replacementGate->holdWorker();
    };
    fathom::storage::ProfileStore sourceStore(sourceOptions);
    fathom::storage::BackupSnapshotOptions cancelledOptions;
    cancelledOptions.destinationDirectory = cancelledStage;
    cancelledOptions.stopped = true;
    cancelledOptions.unresolvedWrites = false;
    cancelledOptions.includeArchiveManifest = true;
    cancelledOptions.includeArchiveContainer = true;
    fathom::storage::BackupPublicationRequest cancelledPublication;
    cancelledPublication.destination = cancelledArchive;
    cancelledOptions.publication = cancelledPublication;
    cancelledOptions.cancelled = [&cancelSnapshot] {
        return cancelSnapshot.load(std::memory_order_acquire);
    };
    auto cancelledFuture = sourceStore.prepareBackupSnapshot(cancelledOperation, cancelledOptions);
    gate->waitForWorker();
    const auto refusedHistory = sourceStore
        .acknowledge("22222222-2222-4222-8222-222222222222",
                     "33333333-3333-4333-8333-333333333333", "fg:item:000001", 1,
                     "2026-09-14T00:00:00Z")
        .get();
    const auto refusedSettings = sourceStore
        .compareExchangePreferences("44444444-4444-4444-8444-444444444444",
                                    "backup.test.r02", 1, 0, "{}", true)
        .get();
    cancelSnapshot.store(true, std::memory_order_release);
    gate->releaseWorker();
    const auto cancelled = cancelledFuture.get();

    require(gate->entered(), "Backup worker never entered its actual backup_step gate");
    require(refusedHistory.status == Status::Busy && refusedHistory.code == "QUEUE_REFUSED" &&
                refusedHistory.data.null(),
            "History write was not safely refused during the held snapshot");
    require(refusedSettings.status == Status::Busy && refusedSettings.code == "QUEUE_REFUSED" &&
                refusedSettings.data.null(),
            "Settings write was not safely refused during the held snapshot");
    require(cancelled.status == Status::DefiniteFailure && cancelled.code == "SNAPSHOT_CANCELLED" &&
                cancelled.data.null(),
            "Interrupted snapshot returned unexpected result: " + cancelled.code);
    require(fs::is_directory(cancelledStage) &&
                fs::is_regular_file(cancelledStage / "profile.sqlite"),
            "backup_step gate did not observe an allocated private snapshot stage");
    require(!fs::exists(cancelledStage / "manifest.json") &&
                !fs::exists(cancelledStage / "candidate.zip") && !fs::exists(cancelledArchive),
            "Interrupted snapshot created a successful manifest/archive artifact");
    const auto afterCancellation = sourceStore.snapshot("combined-parent-after-cancellation").get();
    require(afterCancellation.status == Status::Confirmed,
            "Source profile did not remain readable after interrupted backup cleanup");
    require(afterCancellation.data.object().at("profile_id") == beforeInterruptionData.at("profile_id") &&
                afterCancellation.data.object().at("committed_seq") ==
                    beforeInterruptionData.at("committed_seq") &&
                afterCancellation.data.object().at("authoritative") == beforeInterruptionAuthority,
            "Interrupted backup or deferred writes changed the original committed boundary");
    writeReply(work / "cancelled-backup.json", cancelled);
    writeReply(work / "during-backup-history-refused.json", refusedHistory);
    writeReply(work / "during-backup-settings-refused.json", refusedSettings);
    writeNew(work / "cancelled-boundary.json", fathom::storage::canonical(Object{
        {"before", beforeInterruption}, {"after", afterCancellation.data},
        {"hook_phase", "backup_step"}, {"hook_entered", gate->entered()},
        {"stage_directory_exists", fs::exists(cancelledStage)},
        {"partial_profile_bytes", Value::fromInteger(static_cast<std::int64_t>(
             fs::file_size(cancelledStage / "profile.sqlite")))},
        {"manifest_exists", fs::exists(cancelledStage / "manifest.json")},
        {"candidate_exists", fs::exists(cancelledStage / "candidate.zip")},
        {"published_archive_exists", fs::exists(cancelledArchive)}}));

    const auto acceptedHistory = sourceStore
        .acknowledge("55555555-5555-4555-8555-555555555555",
                     "66666666-6666-4666-8666-666666666666", "fg:item:000001", 1,
                     "2026-09-14T00:01:00Z")
        .get();
    const auto acceptedSettings = sourceStore
        .compareExchangePreferences("77777777-7777-4777-8777-777777777777",
                                    "backup.test.r02", 1, 0, "{}", true)
        .get();
    require(acceptedHistory.status == Status::Confirmed,
            "History write did not become usable after snapshot cleanup: " + acceptedHistory.code);
    require(acceptedSettings.status == Status::Confirmed,
            "Settings write did not become usable after snapshot cleanup: " + acceptedSettings.code);
    const auto afterCleanupWrites = sourceStore.snapshot("combined-parent-after-cleanup-writes").get();
    require(afterCleanupWrites.status == Status::Confirmed,
            "Committed boundary could not be read after cleanup writes");
    const auto& afterCleanupData = afterCleanupWrites.data.object();
    const auto& afterCleanupAuthority = afterCleanupData.at("authoritative");
    std::int64_t afterCleanupSequence = 0;
    require(afterCleanupData.at("committed_seq").integer(afterCleanupSequence) &&
                afterCleanupSequence == initialCommittedSequence + 1,
            "Post-cleanup history write did not advance the receipt marker exactly once");
    require(afterCleanupAuthority.object().at("acknowledgment").array().size() ==
                beforeInterruptionAuthority.object().at("acknowledgment").array().size() + 1 &&
                afterCleanupAuthority.object().at("preferences").array().size() ==
                beforeInterruptionAuthority.object().at("preferences").array().size() + 1,
            "Post-cleanup source boundary does not contain both successful writes");
    writeReply(work / "after-cleanup-history-accepted.json", acceptedHistory);
    writeReply(work / "after-cleanup-settings-accepted.json", acceptedSettings);
    writeReply(work / "after-cleanup-boundary.json", afterCleanupWrites);

    const Value before = afterCleanupWrites.data;
    const auto& beforeData = before.object();
    const auto& beforeAuthority = beforeData.at("authoritative");

    const auto successfulStage = work / "successful-stage";
    const auto publishedArchive = work / "portable-backup.zip";
    fathom::storage::BackupSnapshotOptions successfulOptions;
    successfulOptions.destinationDirectory = successfulStage;
    successfulOptions.stopped = true;
    successfulOptions.unresolvedWrites = false;
    successfulOptions.includeArchiveManifest = true;
    successfulOptions.includeArchiveContainer = true;
    fathom::storage::BackupPublicationRequest publication;
    publication.destination = publishedArchive;
    successfulOptions.publication = publication;
    const auto backup = sourceStore
        .prepareBackupSnapshot("22222222-2222-4222-8222-222222222222", successfulOptions)
        .get();
    require(backup.status == Status::Confirmed && backup.code == "BACKUP_PUBLISHED",
            "Portable backup publication failed: " + backup.code);
    require(fs::is_regular_file(publishedArchive) &&
                fs::is_regular_file(successfulStage / "manifest.json"),
            "Successful publication omitted its archive or verified manifest");
    require(backup.data.object().at("committed_seq") == beforeData.at("committed_seq") &&
                backup.data.object().at("authority").object().at("sha256") ==
                    beforeData.at("snapshot_sha256"),
            "Published backup receipt differs from the declared committed boundary");
    const auto afterBackup = sourceStore.snapshot("combined-parent-after-backup").get();
    require(afterBackup.status == Status::Confirmed &&
                afterBackup.data.object().at("profile_id") == beforeData.at("profile_id") &&
                afterBackup.data.object().at("committed_seq") == beforeData.at("committed_seq") &&
                afterBackup.data.object().at("authoritative") == beforeAuthority,
            "Successful backup changed the committed source boundary");
    writeReply(work / "published-backup.json", backup);
    writeReply(work / "source-after-backup.json", afterBackup);

    const auto originalReconciliation = sourceStore
        .reconcileBackupPublication("22222222-2222-4222-8222-222222222222", successfulOptions)
        .get();
    require(originalReconciliation.status == Status::Confirmed &&
                originalReconciliation.code == "BACKUP_PUBLISHED",
            "Original publication could not be explicitly reconciled: " +
                originalReconciliation.code);
    writeReply(work / "original-publication-reconciled.json", originalReconciliation);

    const std::string priorArchiveBytes = readFile(publishedArchive);
    const std::string priorArchiveSha = fathom::content::sha256(priorArchiveBytes);
    struct stat priorArchiveStat {};
    require(stat(publishedArchive.c_str(), &priorArchiveStat) == 0 &&
                S_ISREG(priorArchiveStat.st_mode) && priorArchiveStat.st_size >= 0,
            "Prior reconciled archive has no regular-file identity");
    fathom::storage::BackupPublicationIdentity priorIdentity{
        std::to_string(priorArchiveStat.st_dev), std::to_string(priorArchiveStat.st_ino),
        priorArchiveSha, static_cast<std::uint64_t>(priorArchiveStat.st_size)};
    writeNew(work / "prior-archive-source-boundary.json", fathom::storage::canonical(before));
    writeNew(work / "prior-archive-capture.json", fathom::storage::canonical(Object{
        {"archive_path", publishedArchive.string()}, {"sha256", priorArchiveSha},
        {"bytes", Value::fromInteger(static_cast<std::int64_t>(priorIdentity.bytes))},
        {"device", priorIdentity.device}, {"inode", priorIdentity.inode},
        {"profile_id", beforeData.at("profile_id")},
        {"committed_seq", beforeData.at("committed_seq")},
        {"authoritative_sha256", beforeData.at("snapshot_sha256")},
        {"original_operation_reconciled", true}}));

    const auto replacementStage = work / "cancelled-replacement-stage";
    fathom::storage::BackupSnapshotOptions replacementOptions;
    replacementOptions.destinationDirectory = replacementStage;
    replacementOptions.stopped = true;
    replacementOptions.unresolvedWrites = false;
    replacementOptions.includeArchiveManifest = true;
    replacementOptions.includeArchiveContainer = true;
    fathom::storage::BackupPublicationRequest replacementPublication;
    replacementPublication.destination = publishedArchive;
    replacementPublication.expected = priorIdentity;
    replacementPublication.reconciledPredecessor = "22222222-2222-4222-8222-222222222222";
    replacementOptions.publication = replacementPublication;
    replacementOptions.cancelled = [&cancelReplacement] {
        return cancelReplacement.load(std::memory_order_acquire);
    };
    auto replacementFuture = sourceStore.prepareBackupSnapshot(replacementOperation,
                                                               replacementOptions);
    replacementGate->waitForWorker();
    cancelReplacement.store(true, std::memory_order_release);
    replacementGate->releaseWorker();
    const auto replacementCancelled = replacementFuture.get();
    require(replacementGate->entered(),
            "Replacement worker never entered its exact backup_step gate");
    require(replacementCancelled.status == Status::DefiniteFailure &&
                replacementCancelled.code == "SNAPSHOT_CANCELLED" &&
                replacementCancelled.data.null(),
            "Replacement cancellation returned unexpected result: " +
                replacementCancelled.code);
    require(fs::is_directory(replacementStage) &&
                fs::is_regular_file(replacementStage / "profile.sqlite") &&
                !fs::exists(replacementStage / "manifest.json") &&
                !fs::exists(replacementStage / "candidate.zip"),
            "Cancelled replacement left a successful stage artifact");

    const std::string afterReplacementArchiveBytes = readFile(publishedArchive);
    struct stat afterReplacementArchiveStat {};
    require(stat(publishedArchive.c_str(), &afterReplacementArchiveStat) == 0 &&
                S_ISREG(afterReplacementArchiveStat.st_mode),
            "Prior archive disappeared or ceased to be a regular file after cancellation");
    const auto afterReplacementArchiveSha = fathom::content::sha256(afterReplacementArchiveBytes);
    require(afterReplacementArchiveBytes == priorArchiveBytes &&
                afterReplacementArchiveSha == priorArchiveSha &&
                static_cast<std::uint64_t>(afterReplacementArchiveStat.st_size) == priorIdentity.bytes &&
                std::to_string(afterReplacementArchiveStat.st_dev) == priorIdentity.device &&
                std::to_string(afterReplacementArchiveStat.st_ino) == priorIdentity.inode,
            "Cancelled replacement changed the prior archive bytes or native identity");
    const auto afterReplacementSource = sourceStore
        .snapshot("combined-parent-after-replacement-cancellation").get();
    require(afterReplacementSource.status == Status::Confirmed &&
                afterReplacementSource.data.object().at("profile_id") == beforeData.at("profile_id") &&
                afterReplacementSource.data.object().at("committed_seq") == beforeData.at("committed_seq") &&
                afterReplacementSource.data.object().at("authoritative") == beforeAuthority,
            "Cancelled replacement changed the prior archive's declared source authority");
    writeReply(work / "replacement-cancelled.json", replacementCancelled);
    writeReply(work / "source-after-replacement-cancellation.json", afterReplacementSource);
    writeNew(work / "replacement-cancellation.json", fathom::storage::canonical(Object{
        {"operation", replacementOperation}, {"hook_phase", "backup_step"},
        {"hook_entered", replacementGate->entered()}, {"result_code", replacementCancelled.code},
        {"prior_archive_bytes_equal", afterReplacementArchiveBytes == priorArchiveBytes},
        {"prior_archive_sha256_before", priorArchiveSha},
        {"prior_archive_sha256_after", afterReplacementArchiveSha},
        {"prior_archive_size_unchanged", true}, {"prior_archive_device_unchanged", true},
        {"prior_archive_inode_unchanged", true}, {"replacement_manifest_exists", false},
        {"replacement_candidate_exists", false}, {"source_profile_id_unchanged", true},
        {"source_committed_seq_unchanged", true}, {"source_authority_unchanged", true}}));

    const auto generatedManifest = fathom::storage::parseCanonical(
        readFile(successfulStage / "manifest.json"));
    const auto expectedManifest = fathom::storage::parseCanonical(
        readFile(fixtureRoot / "rich/manifest.json"));
    auto expectedReferences = referenceIdentities(expectedManifest);
    expectedReferences.push_back(fathom::storage::canonical(Object{
        {"content_revision", Value::fromInteger(1)}, {"item_id", "fg:item:000001"},
        {"metadata_status", "variant/version/provenance unavailable in original acknowledgment; never filled from current content"},
        {"reference_kind", "item_revision_only"}}));
    std::sort(expectedReferences.begin(), expectedReferences.end());
    require(referenceIdentities(generatedManifest) == expectedReferences,
            "Generated backup manifest did not preserve fixture references plus the accepted acknowledgment reference");

    Array available;
    const auto& references = generatedManifest.object().at("snapshot").object()
                                 .at("content_references").array();
    for (auto reference : references) {
        const auto kind = reference.object().at("reference_kind");
        if (kind == Value("versioned_content")) {
            reference.object().erase("reference_kind");
            available.emplace_back(Object{
                {"reference", reference},
                {"provenance", "Exact identity from the retained synthetic control manifest; availability only"}});
        }
    }
    require(!available.empty(), "Generated manifest had no exact versioned content references");
    const auto metadata = work / "available-metadata.json";
    writeNew(metadata, fathom::storage::canonical(available));

    // Treat this as an offline handoff: the valid published archive is copied
    // into a separately rooted transfer bundle, then consumed from that copy
    // by an independently located receiver profile. This is a same-host
    // filesystem-root simulation, not a second-machine qualification.
    const auto transferRoot = work / "offline-transfer-bundle";
    directory(transferRoot);
    const auto transferredArchive = transferRoot / "portable-backup.zip";
    copyPrivate(publishedArchive, transferredArchive);
    const auto transferredBytes = readFile(transferredArchive);
    struct stat publishedStat {};
    struct stat transferredStat {};
    require(stat(publishedArchive.c_str(), &publishedStat) == 0 &&
                stat(transferredArchive.c_str(), &transferredStat) == 0 &&
                S_ISREG(publishedStat.st_mode) && S_ISREG(transferredStat.st_mode),
            "Published and transferred archive identities are not regular files");
    const auto transferredSha = fathom::content::sha256(transferredBytes);
    require(transferredBytes == priorArchiveBytes && transferredSha == priorArchiveSha &&
                static_cast<std::uint64_t>(transferredStat.st_size) == priorIdentity.bytes &&
                std::to_string(transferredStat.st_dev) == priorIdentity.device &&
                transferredStat.st_ino != publishedStat.st_ino,
            "Offline transfer copy differs from the published archive or is not a distinct file");
    writeNew(work / "offline-transfer-copy-reconciliation.json",
             fathom::storage::canonical(Object{
                 {"source_archive_path", publishedArchive.string()},
                 {"source_archive_bytes", Value::fromInteger(publishedStat.st_size)},
                 {"source_archive_sha256", priorArchiveSha},
                 {"transfer_copy_path", transferredArchive.string()},
                 {"transfer_copy_bytes", Value::fromInteger(transferredStat.st_size)},
                 {"transfer_copy_sha256", transferredSha},
                 {"byte_identical", transferredBytes == priorArchiveBytes},
                 {"same_filesystem_device", publishedStat.st_dev == transferredStat.st_dev},
                 {"distinct_file_identity", publishedStat.st_ino != transferredStat.st_ino},
                 {"same_machine_simulation", true}}));

    const auto restoreRoot = work / "restore-target";
    directory(restoreRoot);
    const auto restoreLive = restoreRoot / "live";
    directory(restoreLive);
    const auto restoreProfile = restoreLive / "profile.sqlite";
    copyPrivate(fixtureRoot / "empty/profile.sqlite", restoreProfile);
    PortableRestoreRequest request{restoreProfile, transferredArchive,
                                   restoreRoot / "restore-stage", metadata};
    const auto prepared = PortableRestoreWorkflow::prepare(request);
    require(prepared.preparation.status == Status::Confirmed &&
                prepared.preparation.code == "RESTORE_PREPARED",
            "Combined workflow restore preparation failed: " + prepared.preparation.code);
    const auto applied = PortableRestoreWorkflow::apply(prepared);
    require(applied.application.status == Status::Confirmed &&
                applied.application.code == "RESTORE_APPLIED",
            "Combined workflow restore apply failed: " + applied.application.code);
    require(applied.reopened.status == Status::Confirmed,
            "Combined workflow restore did not reopen normally");
    const auto& reopened = applied.reopened.data.object();
    require(reopened.at("profile_id") == beforeData.at("profile_id") &&
                reopened.at("committed_seq") == beforeData.at("committed_seq") &&
                reopened.at("authoritative") == beforeAuthority,
            "Reopened isolated profile differs from the exact declared source boundary");
    const auto afterTransferSource = sourceStore
        .snapshot("combined-parent-after-transfer-restore").get();
    require(afterTransferSource.status == Status::Confirmed &&
                afterTransferSource.data.object().at("profile_id") == beforeData.at("profile_id") &&
                afterTransferSource.data.object().at("committed_seq") == beforeData.at("committed_seq") &&
                afterTransferSource.data.object().at("authoritative") == beforeAuthority,
            "Restoring the copied archive changed the sender profile boundary");

    // Exercise the invalid-copy path through the public workflow while the
    // receiver is populated by the successful transfer above. Corrupt only a
    // further disposable copy; retain both the published archive and valid
    // transfer copy exactly as they were.
    const auto invalidTransferRoot = work / "invalid-transfer-bundle";
    directory(invalidTransferRoot);
    const auto invalidTransferredArchive = invalidTransferRoot / "portable-backup.zip";
    copyPrivate(transferredArchive, invalidTransferredArchive);
    const std::string corruptArchiveBytes = "not a supported portable backup archive\n";
    {
        std::ofstream corrupt(invalidTransferredArchive, std::ios::binary | std::ios::trunc);
        require(static_cast<bool>(corrupt), "Cannot open disposable transfer copy for corruption");
        corrupt.write(corruptArchiveBytes.data(),
                      static_cast<std::streamsize>(corruptArchiveBytes.size()));
        corrupt.close();
        require(static_cast<bool>(corrupt) && chmod(invalidTransferredArchive.c_str(), 0600) == 0,
                "Cannot write/protect the disposable invalid transfer copy");
    }
    auto regularFileIdentity = [&](const fs::path& path) {
        struct stat info {};
        require(stat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode),
                "Expected a regular file while reconciling invalid-copy refusal: " + path.string());
        return Object{{"device", std::to_string(info.st_dev)},
                      {"inode", std::to_string(info.st_ino)},
                      {"bytes", Value::fromInteger(static_cast<std::int64_t>(info.st_size))},
                      {"sha256", sha256(path)}};
    };
    const auto publishedBeforeInvalid = regularFileIdentity(publishedArchive);
    const auto validTransferBeforeInvalid = regularFileIdentity(transferredArchive);
    const auto invalidTransferBefore = regularFileIdentity(invalidTransferredArchive);
    const auto receiverBeforeInvalid = snapshot(restoreProfile, "receiver-before-invalid-transfer-prepare");
    struct stat receiverFileBeforeInvalid {};
    require(stat(restoreProfile.c_str(), &receiverFileBeforeInvalid) == 0 &&
                S_ISREG(receiverFileBeforeInvalid.st_mode),
            "Populated receiver profile disappeared before invalid-copy preparation");
    const auto senderBeforeInvalid = sourceStore.snapshot("sender-before-invalid-transfer-prepare").get();
    require(senderBeforeInvalid.status == Status::Confirmed &&
                senderBeforeInvalid.data.object().at("profile_id") == beforeData.at("profile_id") &&
                senderBeforeInvalid.data.object().at("committed_seq") == beforeData.at("committed_seq") &&
                senderBeforeInvalid.data.object().at("authoritative") == beforeAuthority,
            "Sender boundary drifted before invalid-copy preparation");

    PortableRestoreRequest invalidRequest{restoreProfile, invalidTransferredArchive,
                                          restoreRoot / "corrupt-copy-stage", metadata};
    bool prepareRefused = false;
    bool applyInvoked = false;
    std::string prepareFailure;
    try {
        (void)PortableRestoreWorkflow::prepare(invalidRequest);
    } catch (const std::exception& error) {
        prepareRefused = true;
        prepareFailure = error.what();
    }
    require(prepareRefused,
            "Corrupt transferred archive unexpectedly passed restore preparation");
    const std::string refusalPrefix = "Restore preparation did not complete: ";
    const auto refusalAt = prepareFailure.find(refusalPrefix);
    require(refusalAt != std::string::npos,
            "Invalid-copy refusal omitted the workflow's typed preparation failure: " + prepareFailure);
    const auto codeAt = refusalAt + refusalPrefix.size();
    const auto codeEnd = prepareFailure.find(' ', codeAt);
    const auto prepareFailureCode = prepareFailure.substr(codeAt, codeEnd - codeAt);
    require(prepareFailureCode == "ARCHIVE_FORMAT",
            "Corrupt copy returned an unexpected preparation failure: " + prepareFailure);
    require(!applyInvoked, "Apply must never run after prepare refuses the invalid copy");
    require(!fs::exists(invalidRequest.stage / "restore-preview.json"),
            "Invalid copied archive unexpectedly produced a confirmation preview");

    const auto receiverAfterInvalid = snapshot(restoreProfile, "receiver-after-invalid-transfer-prepare");
    struct stat receiverFileAfterInvalid {};
    require(stat(restoreProfile.c_str(), &receiverFileAfterInvalid) == 0 &&
                S_ISREG(receiverFileAfterInvalid.st_mode) &&
                receiverFileAfterInvalid.st_dev == receiverFileBeforeInvalid.st_dev &&
                receiverFileAfterInvalid.st_ino == receiverFileBeforeInvalid.st_ino,
            "Invalid-copy prepare replaced the populated receiver database identity");
    require(receiverAfterInvalid.object().at("profile_id") ==
                receiverBeforeInvalid.object().at("profile_id") &&
                receiverAfterInvalid.object().at("committed_seq") ==
                receiverBeforeInvalid.object().at("committed_seq") &&
                receiverAfterInvalid.object().at("authoritative") ==
                receiverBeforeInvalid.object().at("authoritative"),
            "Invalid-copy prepare changed the populated receiver authoritative state");
    const auto senderAfterInvalid = sourceStore.snapshot("sender-after-invalid-transfer-prepare").get();
    require(senderAfterInvalid.status == Status::Confirmed &&
                senderAfterInvalid.data.object().at("profile_id") == beforeData.at("profile_id") &&
                senderAfterInvalid.data.object().at("committed_seq") == beforeData.at("committed_seq") &&
                senderAfterInvalid.data.object().at("authoritative") == beforeAuthority,
            "Invalid-copy prepare changed the sender profile boundary");
    const auto publishedAfterInvalid = regularFileIdentity(publishedArchive);
    const auto validTransferAfterInvalid = regularFileIdentity(transferredArchive);
    const auto invalidTransferAfter = regularFileIdentity(invalidTransferredArchive);
    require(publishedAfterInvalid == publishedBeforeInvalid &&
                validTransferAfterInvalid == validTransferBeforeInvalid &&
                invalidTransferAfter == invalidTransferBefore &&
                readFile(invalidTransferredArchive) == corruptArchiveBytes,
            "Invalid-copy preparation changed an archive or its captured identity");
    writeNew(work / "invalid-transfer-copy-refusal.json",
             fathom::storage::canonical(Object{
                 {"status", "PASS"}, {"prepare_refused", prepareRefused},
                 {"prepare_failure_code", prepareFailureCode}, {"prepare_failure", prepareFailure},
                 {"apply_invoked", applyInvoked}, {"confirmation_preview_created", false},
                 {"receiver_authoritative_state_unchanged", true},
                 {"receiver_database_native_identity_unchanged", true},
                 {"sender_authoritative_state_unchanged", true},
                 {"published_archive_identity_unchanged", true},
                 {"valid_transfer_copy_identity_unchanged", true},
                 {"invalid_transfer_copy_identity_unchanged", true},
                 {"invalid_copy_isolated_from_valid_copies", true},
                 {"receiver_before", Object{
                     {"profile_id", receiverBeforeInvalid.object().at("profile_id")},
                     {"committed_seq", receiverBeforeInvalid.object().at("committed_seq")},
                     {"authoritative_sha256", fathom::content::sha256(
                         fathom::storage::canonical(receiverBeforeInvalid.object().at("authoritative")))},
                     {"database_device", std::to_string(receiverFileBeforeInvalid.st_dev)},
                     {"database_inode", std::to_string(receiverFileBeforeInvalid.st_ino)}}},
                 {"receiver_after", Object{
                     {"profile_id", receiverAfterInvalid.object().at("profile_id")},
                     {"committed_seq", receiverAfterInvalid.object().at("committed_seq")},
                     {"authoritative_sha256", fathom::content::sha256(
                         fathom::storage::canonical(receiverAfterInvalid.object().at("authoritative")))},
                     {"database_device", std::to_string(receiverFileAfterInvalid.st_dev)},
                     {"database_inode", std::to_string(receiverFileAfterInvalid.st_ino)}}},
                 {"sender_before", Object{
                     {"profile_id", senderBeforeInvalid.data.object().at("profile_id")},
                     {"committed_seq", senderBeforeInvalid.data.object().at("committed_seq")},
                     {"authoritative_sha256", fathom::content::sha256(
                         fathom::storage::canonical(senderBeforeInvalid.data.object().at("authoritative")))}}},
                 {"sender_after", Object{
                     {"profile_id", senderAfterInvalid.data.object().at("profile_id")},
                     {"committed_seq", senderAfterInvalid.data.object().at("committed_seq")},
                     {"authoritative_sha256", fathom::content::sha256(
                         fathom::storage::canonical(senderAfterInvalid.data.object().at("authoritative")))}}},
                 {"published_archive_before", publishedBeforeInvalid},
                 {"published_archive_after", publishedAfterInvalid},
                 {"valid_transfer_copy_before", validTransferBeforeInvalid},
                 {"valid_transfer_copy_after", validTransferAfterInvalid},
                 {"invalid_transfer_copy_before", invalidTransferBefore},
                 {"invalid_transfer_copy_after", invalidTransferAfter},
                 {"physical_second_mac_transfer", false}}));

    // r06 keeps the archive container structurally intact and changes one byte
    // in its stored manifest payload. This exercises payload CRC refusal rather
    // than r05's unsupported/truncated-container refusal.
    const auto checksumCorruptRoot = work / "checksum-corrupt-transfer-bundle";
    directory(checksumCorruptRoot);
    const auto checksumCorruptArchive = checksumCorruptRoot / "portable-backup.zip";
    copyPrivate(transferredArchive, checksumCorruptArchive);
    auto checksumCorruptBytes = readFile(checksumCorruptArchive);
    const std::string manifestMarker = "Fathom.ProfileArchive";
    const auto markerAt = checksumCorruptBytes.find(manifestMarker);
    require(markerAt != std::string::npos &&
                checksumCorruptBytes.find(manifestMarker, markerAt + 1) == std::string::npos,
            "Valid transfer archive must contain exactly one stored manifest marker");
    require(checksumCorruptBytes.size() == transferredBytes.size(),
            "Copied transfer archive changed length before payload mutation");
    const auto originalMarkerByte = static_cast<unsigned char>(checksumCorruptBytes[markerAt]);
    checksumCorruptBytes[markerAt] = static_cast<char>(originalMarkerByte ^ 0x01u);
    std::size_t changedByteCount = 0;
    for (std::size_t index = 0; index < transferredBytes.size(); ++index)
        if (checksumCorruptBytes[index] != transferredBytes[index])
            ++changedByteCount;
    require(checksumCorruptBytes.size() == transferredBytes.size() && changedByteCount == 1 &&
                checksumCorruptBytes.size() >= 22 &&
                checksumCorruptBytes.compare(checksumCorruptBytes.size() - 22, 22,
                                             transferredBytes, transferredBytes.size() - 22, 22) == 0,
            "Checksum-corrupt copy must differ by one payload byte and retain its ZIP terminal record");
    {
        std::ofstream corrupt(checksumCorruptArchive, std::ios::binary | std::ios::trunc);
        require(static_cast<bool>(corrupt), "Cannot open checksum-corrupt transfer copy");
        corrupt.write(checksumCorruptBytes.data(),
                      static_cast<std::streamsize>(checksumCorruptBytes.size()));
        corrupt.close();
        require(static_cast<bool>(corrupt) && chmod(checksumCorruptArchive.c_str(), 0600) == 0,
                "Cannot write/protect checksum-corrupt transfer copy");
    }
    const auto checksumCorruptBefore = regularFileIdentity(checksumCorruptArchive);
    const auto publishedBeforeChecksum = regularFileIdentity(publishedArchive);
    const auto validTransferBeforeChecksum = regularFileIdentity(transferredArchive);
    const auto receiverBeforeChecksum = snapshot(restoreProfile, "receiver-before-checksum-corrupt-prepare");
    struct stat receiverFileBeforeChecksum {};
    require(stat(restoreProfile.c_str(), &receiverFileBeforeChecksum) == 0 &&
                S_ISREG(receiverFileBeforeChecksum.st_mode),
            "Populated receiver profile disappeared before checksum-corrupt preparation");
    const auto senderBeforeChecksum = sourceStore.snapshot("sender-before-checksum-corrupt-prepare").get();
    require(senderBeforeChecksum.status == Status::Confirmed &&
                senderBeforeChecksum.data.object().at("profile_id") == beforeData.at("profile_id") &&
                senderBeforeChecksum.data.object().at("committed_seq") == beforeData.at("committed_seq") &&
                senderBeforeChecksum.data.object().at("authoritative") == beforeAuthority,
            "Sender boundary drifted before checksum-corrupt preparation");

    PortableRestoreRequest checksumRequest{restoreProfile, checksumCorruptArchive,
                                           restoreRoot / "checksum-corrupt-stage", metadata};
    bool checksumPrepareRefused = false;
    bool checksumApplyInvoked = false;
    std::string checksumPrepareFailure;
    try {
        (void)PortableRestoreWorkflow::prepare(checksumRequest);
    } catch (const std::exception& error) {
        checksumPrepareRefused = true;
        checksumPrepareFailure = error.what();
    }
    require(checksumPrepareRefused,
            "Checksum-corrupt transfer archive unexpectedly passed restore preparation");
    const std::string checksumRefusalPrefix = "Restore preparation did not complete: ";
    const auto checksumRefusalAt = checksumPrepareFailure.find(checksumRefusalPrefix);
    require(checksumRefusalAt != std::string::npos,
            "Checksum refusal omitted the workflow's typed preparation failure: " + checksumPrepareFailure);
    const auto checksumCodeAt = checksumRefusalAt + checksumRefusalPrefix.size();
    const auto checksumCodeEnd = checksumPrepareFailure.find(' ', checksumCodeAt);
    const auto checksumPrepareFailureCode =
        checksumPrepareFailure.substr(checksumCodeAt, checksumCodeEnd - checksumCodeAt);
    require(checksumPrepareFailureCode == "ARCHIVE_CRC",
            "Checksum-corrupt copy returned an unexpected preparation failure: " + checksumPrepareFailure);
    require(!checksumApplyInvoked &&
                !fs::exists(checksumRequest.stage / "restore-preview.json"),
            "Checksum-corrupt prepare refusal must not apply or create a confirmation preview");

    const auto receiverAfterChecksum = snapshot(restoreProfile, "receiver-after-checksum-corrupt-prepare");
    struct stat receiverFileAfterChecksum {};
    require(stat(restoreProfile.c_str(), &receiverFileAfterChecksum) == 0 &&
                S_ISREG(receiverFileAfterChecksum.st_mode) &&
                receiverFileAfterChecksum.st_dev == receiverFileBeforeChecksum.st_dev &&
                receiverFileAfterChecksum.st_ino == receiverFileBeforeChecksum.st_ino,
            "Checksum-corrupt prepare changed populated receiver database identity");
    require(receiverAfterChecksum.object().at("profile_id") ==
                receiverBeforeChecksum.object().at("profile_id") &&
                receiverAfterChecksum.object().at("committed_seq") ==
                receiverBeforeChecksum.object().at("committed_seq") &&
                receiverAfterChecksum.object().at("authoritative") ==
                receiverBeforeChecksum.object().at("authoritative"),
            "Checksum-corrupt prepare changed populated receiver authority");
    const auto senderAfterChecksum = sourceStore.snapshot("sender-after-checksum-corrupt-prepare").get();
    require(senderAfterChecksum.status == Status::Confirmed &&
                senderAfterChecksum.data.object().at("profile_id") == beforeData.at("profile_id") &&
                senderAfterChecksum.data.object().at("committed_seq") == beforeData.at("committed_seq") &&
                senderAfterChecksum.data.object().at("authoritative") == beforeAuthority,
            "Checksum-corrupt prepare changed sender profile boundary");
    const auto checksumCorruptAfter = regularFileIdentity(checksumCorruptArchive);
    const auto publishedAfterChecksum = regularFileIdentity(publishedArchive);
    const auto validTransferAfterChecksum = regularFileIdentity(transferredArchive);
    require(checksumCorruptAfter == checksumCorruptBefore &&
                publishedAfterChecksum == publishedBeforeChecksum &&
                validTransferAfterChecksum == validTransferBeforeChecksum &&
                readFile(checksumCorruptArchive) == checksumCorruptBytes &&
                readFile(publishedArchive) == priorArchiveBytes &&
                readFile(transferredArchive) == transferredBytes,
            "Checksum-corrupt prepare changed an archive or its captured identity");
    writeNew(work / "checksum-corrupt-copy-refusal.json",
             fathom::storage::canonical(Object{
                 {"status", "PASS"}, {"prepare_refused", checksumPrepareRefused},
                 {"prepare_failure_code", checksumPrepareFailureCode},
                 {"prepare_failure", checksumPrepareFailure}, {"apply_invoked", checksumApplyInvoked},
                 {"confirmation_preview_created", false}, {"changed_payload_bytes", Value::fromInteger(1)},
                 {"changed_payload_offset", Value::fromInteger(static_cast<std::int64_t>(markerAt))},
                 {"original_payload_byte", Value::fromInteger(originalMarkerByte)},
                 {"mutated_payload_byte", Value::fromInteger(static_cast<unsigned char>(checksumCorruptBytes[markerAt]))},
                 {"zip_terminal_record_unchanged", true},
                 {"receiver_authoritative_state_unchanged", true},
                 {"receiver_database_native_identity_unchanged", true},
                 {"sender_authoritative_state_unchanged", true},
                 {"published_archive_identity_unchanged", true},
                 {"valid_transfer_copy_identity_unchanged", true},
                 {"checksum_corrupt_copy_identity_unchanged_after_prepare", true},
                 {"receiver_before", Object{
                     {"profile_id", receiverBeforeChecksum.object().at("profile_id")},
                     {"committed_seq", receiverBeforeChecksum.object().at("committed_seq")},
                     {"authoritative_sha256", fathom::content::sha256(
                         fathom::storage::canonical(receiverBeforeChecksum.object().at("authoritative")))},
                     {"database_device", std::to_string(receiverFileBeforeChecksum.st_dev)},
                     {"database_inode", std::to_string(receiverFileBeforeChecksum.st_ino)}}},
                 {"receiver_after", Object{
                     {"profile_id", receiverAfterChecksum.object().at("profile_id")},
                     {"committed_seq", receiverAfterChecksum.object().at("committed_seq")},
                     {"authoritative_sha256", fathom::content::sha256(
                         fathom::storage::canonical(receiverAfterChecksum.object().at("authoritative")))},
                     {"database_device", std::to_string(receiverFileAfterChecksum.st_dev)},
                     {"database_inode", std::to_string(receiverFileAfterChecksum.st_ino)}}},
                 {"sender_before", Object{
                     {"profile_id", senderBeforeChecksum.data.object().at("profile_id")},
                     {"committed_seq", senderBeforeChecksum.data.object().at("committed_seq")},
                     {"authoritative_sha256", fathom::content::sha256(
                         fathom::storage::canonical(senderBeforeChecksum.data.object().at("authoritative")))}}},
                 {"sender_after", Object{
                     {"profile_id", senderAfterChecksum.data.object().at("profile_id")},
                     {"committed_seq", senderAfterChecksum.data.object().at("committed_seq")},
                     {"authoritative_sha256", fathom::content::sha256(
                         fathom::storage::canonical(senderAfterChecksum.data.object().at("authoritative")))}}},
                 {"checksum_corrupt_copy_before", checksumCorruptBefore},
                 {"checksum_corrupt_copy_after", checksumCorruptAfter},
                 {"published_archive_before", publishedBeforeChecksum},
                 {"published_archive_after", publishedAfterChecksum},
                 {"valid_transfer_copy_before", validTransferBeforeChecksum},
                 {"valid_transfer_copy_after", validTransferAfterChecksum},
                 {"physical_second_mac_transfer", false}}));

    // Keep the copied backup's ZIP64 structure and payload intact while making
    // its first entry use a compression method that this format does not admit.
    // This is distinct from the truncated container and CRC damage above.
    const auto unsupportedRoot = work / "unsupported-method-transfer-bundle";
    directory(unsupportedRoot);
    const auto unsupportedArchive = unsupportedRoot / "portable-backup.zip";
    copyPrivate(transferredArchive, unsupportedArchive);
    auto unsupportedBytes = readFile(unsupportedArchive);
    const std::string zip64Signature("PK\x06\x06", 4);
    const auto zip64At = unsupportedBytes.rfind(zip64Signature);
    auto little64 = [&](std::size_t offset) {
        require(offset <= unsupportedBytes.size() && unsupportedBytes.size() - offset >= 8,
                "ZIP64 offset is outside the copied archive");
        std::uint64_t value = 0;
        for (int index = 7; index >= 0; --index)
            value = (value << 8) | static_cast<unsigned char>(unsupportedBytes[offset + index]);
        return value;
    };
    require(zip64At != std::string::npos && zip64At + 56 <= unsupportedBytes.size(),
            "Published backup lacks a bounded ZIP64 terminal record");
    const auto centralAt = static_cast<std::size_t>(little64(zip64At + 48));
    require(centralAt < unsupportedBytes.size() && unsupportedBytes.size() - centralAt >= 12 &&
                unsupportedBytes.compare(centralAt, 4, "PK\x01\x02", 4) == 0 &&
                unsupportedBytes.compare(0, 4, "PK\x03\x04", 4) == 0 &&
                unsupportedBytes[8] == 0 && unsupportedBytes[9] == 0 &&
                unsupportedBytes[centralAt + 10] == 0 && unsupportedBytes[centralAt + 11] == 0,
            "Published backup's first local/central entry is not a supported stored ZIP64 entry");
    unsupportedBytes[8] = 99;
    unsupportedBytes[centralAt + 10] = 99;
    require(unsupportedBytes.size() == transferredBytes.size() &&
                unsupportedBytes.compare(zip64At, unsupportedBytes.size() - zip64At,
                                         transferredBytes, zip64At,
                                         transferredBytes.size() - zip64At) == 0,
            "Unsupported-method copy changed the terminal ZIP64 record or length");
    {
        std::ofstream output(unsupportedArchive, std::ios::binary | std::ios::trunc);
        require(static_cast<bool>(output), "Cannot open unsupported-method transfer copy");
        output.write(unsupportedBytes.data(), static_cast<std::streamsize>(unsupportedBytes.size()));
        output.close();
        require(static_cast<bool>(output) && chmod(unsupportedArchive.c_str(), 0600) == 0,
                "Cannot write/protect unsupported-method transfer copy");
    }
    const auto unsupportedBefore = regularFileIdentity(unsupportedArchive);
    const auto validBeforeUnsupported = regularFileIdentity(transferredArchive);
    const auto publishedBeforeUnsupported = regularFileIdentity(publishedArchive);
    const auto receiverBeforeUnsupported = snapshot(restoreProfile, "receiver-before-unsupported-method");
    struct stat receiverFileBeforeUnsupported {};
    require(stat(restoreProfile.c_str(), &receiverFileBeforeUnsupported) == 0,
            "Cannot inspect receiver before unsupported-method refusal");
    PortableRestoreRequest unsupportedRequest{restoreProfile, unsupportedArchive,
                                              restoreRoot / "unsupported-method-stage", metadata};
    std::string unsupportedFailure;
    try {
        (void)PortableRestoreWorkflow::prepare(unsupportedRequest);
    } catch (const std::exception& error) {
        unsupportedFailure = error.what();
    }
    require(unsupportedFailure.find("Restore preparation did not complete: ARCHIVE_FORMAT ") !=
                std::string::npos &&
                unsupportedFailure.find("Unsupported ZIP flags/compression") != std::string::npos &&
                !fs::exists(unsupportedRequest.stage / "restore-preview.json"),
            "Unsupported compression method was not refused before apply: " + unsupportedFailure);
    const auto receiverAfterUnsupported = snapshot(restoreProfile, "receiver-after-unsupported-method");
    struct stat receiverFileAfterUnsupported {};
    require(stat(restoreProfile.c_str(), &receiverFileAfterUnsupported) == 0 &&
                receiverFileAfterUnsupported.st_dev == receiverFileBeforeUnsupported.st_dev &&
                receiverFileAfterUnsupported.st_ino == receiverFileBeforeUnsupported.st_ino &&
                receiverAfterUnsupported.object().at("profile_id") ==
                    receiverBeforeUnsupported.object().at("profile_id") &&
                receiverAfterUnsupported.object().at("committed_seq") ==
                    receiverBeforeUnsupported.object().at("committed_seq") &&
                receiverAfterUnsupported.object().at("authoritative") ==
                    receiverBeforeUnsupported.object().at("authoritative") &&
                regularFileIdentity(unsupportedArchive) == unsupportedBefore &&
                regularFileIdentity(transferredArchive) == validBeforeUnsupported &&
                regularFileIdentity(publishedArchive) == publishedBeforeUnsupported &&
                readFile(unsupportedArchive) == unsupportedBytes &&
                readFile(transferredArchive) == transferredBytes &&
                readFile(publishedArchive) == priorArchiveBytes,
            "Unsupported-method refusal changed receiver authority or archive identities");
    const auto senderAfterUnsupported = sourceStore.snapshot("sender-after-unsupported-method").get();
    require(senderAfterUnsupported.status == Status::Confirmed &&
                senderAfterUnsupported.data.object().at("profile_id") == beforeData.at("profile_id") &&
                senderAfterUnsupported.data.object().at("committed_seq") == beforeData.at("committed_seq") &&
                senderAfterUnsupported.data.object().at("authoritative") == beforeAuthority,
            "Unsupported-method refusal changed sender authority");
    writeNew(work / "unsupported-method-refusal.json", fathom::storage::canonical(Object{
        {"status", "PASS"}, {"prepare_failure", unsupportedFailure},
        {"expected_code", "ARCHIVE_FORMAT"}, {"apply_invoked", false},
        {"confirmation_preview_created", false}, {"zip64_terminal_unchanged", true},
        {"unsupported_method", Value::fromInteger(99)},
        {"receiver_authority_and_native_identity_unchanged", true},
        {"sender_authority_unchanged", true},
        {"valid_archives_unchanged", true},
        {"unsupported_copy_before", unsupportedBefore},
        {"unsupported_copy_after", regularFileIdentity(unsupportedArchive)}}));

    writeReply(work / "restore-prepare.json", prepared.preparation);
    writeReply(work / "restore-apply.json", applied.application);
    writeReply(work / "restore-reopen.json", applied.reopened);
    writeReply(work / "source-after-transfer-restore.json", afterTransferSource);
    writeNew(work / "combined-summary.json",
             fathom::storage::canonical(Object{
                 {"status", "PASS"}, {"backup_step_gate_entered", gate->entered()},
                 {"history_write_busy_during_backup", true},
                 {"settings_write_busy_during_backup", true},
                 {"cancelled_attempt_refused", true},
                 {"cancelled_attempt_preserved_committed_boundary", true},
                 {"original_publication_reconciled", true},
                 {"replacement_cancelled_at_backup_step", true},
                 {"prior_archive_sha256", priorArchiveSha},
                 {"prior_archive_bytes_hash_native_identity_unchanged", true},
                 {"replacement_success_artifacts_absent", true},
                 {"replacement_source_authority_unchanged", true},
                 {"post_cleanup_history_write_accepted", true},
                 {"post_cleanup_settings_write_accepted", true},
                 {"portable_backup_published", true}, {"restore_prepare_apply_reopen", true},
                 {"same_prior_archive_restored_after_cancelled_replacement", true},
                 {"published_archive_copied_to_separate_transfer_root", true},
                 {"transfer_copy_sha256", transferredSha},
                 {"transfer_copy_bytes", Value::fromInteger(transferredStat.st_size)},
                 {"transfer_copy_is_distinct_file", true},
                 {"sender_state_unchanged_after_transfer_restore", true},
                 {"unsupported_copy_refused_with_archive_format", true},
                 {"unsupported_zip_method_refused_with_archive_format", true},
                 {"checksum_corrupt_copy_refused_with_archive_crc", true},
                 {"checksum_corrupt_copy_had_one_payload_byte_change", true},
                 {"checksum_corrupt_copy_retained_zip_terminal_record", true},
                 {"checksum_corrupt_copy_refusal_preserved_receiver_sender_and_valid_archives", true},
                 {"physical_second_mac_transfer", false},
                 {"source_profile_id", beforeData.at("profile_id")},
                 {"committed_seq", beforeData.at("committed_seq")},
                 {"authoritative_sha256", beforeData.at("snapshot_sha256")},
                 {"content_reference_count", Value::fromInteger(
                     static_cast<std::int64_t>(references.size()))},
                 {"exact_authoritative_reconciliation", true},
                 {"exact_fixture_plus_post_cleanup_reference_reconciliation", true},
                 {"human_or_physical_acceptance", false}}));
}

void presealMutationCase(const fs::path& evidence, const fs::path& fixtureRoot,
                         const fs::path& metadata, bool replaceFile) {
    const auto name = replaceFile ? "preseal-replaced-inode" : "preseal-changed-bytes";
    const auto request = setup(evidence / "workflow", fixtureRoot, metadata, name);
    const auto work = request.archive.parent_path();
    const auto profileBefore = sha256(request.profile);
    const auto archiveBefore = sha256(request.archive);
    struct stat original{};
    require(stat(request.archive.c_str(), &original) == 0,
            "Cannot inspect archive before pre-seal mutation");
    bool injected = false;
    std::string refusal;
    try {
        PortableRestoreWorkflow::prepare(request, [&] {
            injected = true;
            if (replaceFile) {
                fs::rename(request.archive, work / "original.zip");
                copyPrivate(work / "original.zip", request.archive);
            } else {
                std::fstream archive(request.archive,
                                     std::ios::binary | std::ios::in | std::ios::out);
                require(static_cast<bool>(archive), "Cannot open archive for pre-seal mutation");
                char byte{};
                archive.read(&byte, 1);
                require(static_cast<bool>(archive), "Cannot read archive for pre-seal mutation");
                archive.seekp(0);
                byte ^= 0x01;
                archive.write(&byte, 1);
                archive.flush();
                require(static_cast<bool>(archive), "Cannot write archive pre-seal mutation");
            }
        });
    } catch (const std::exception& error) {
        refusal = error.what();
    }
    require(injected, "Actual workflow did not reach the post-preflight injection seam");
    require(refusal.find("ARCHIVE_CHANGED") != std::string::npos,
            "Pre-seal mutation did not refuse with ARCHIVE_CHANGED: " + refusal);
    struct stat changed{};
    require(stat(request.archive.c_str(), &changed) == 0,
            "Cannot inspect archive after pre-seal mutation");
    require(replaceFile ? changed.st_ino != original.st_ino
                        : sha256(request.archive) != archiveBefore,
            "Pre-seal mutation did not change the intended archive identity");
    require(sha256(request.profile) == profileBefore,
            "Pre-seal refusal changed live profile raw bytes");
    require(!fs::exists(request.stage) && !fs::exists(work / "restore-preview.json"),
            "Pre-seal refusal created restore stage or preview");
    require(!fs::exists(request.profile.string() + "-wal") &&
                !fs::exists(request.profile.string() + "-shm"),
            "Pre-seal refusal opened live SQLite before rejecting the archive");
    for (const auto& entry : fs::directory_iterator(work))
        require(entry.path().filename().string().rfind(".restore-selected-", 0) != 0,
                "Pre-seal refusal retained a private selected archive snapshot");
    writeNew(work / "refusal.json", fathom::storage::canonical(Object{
        {"status", "PASS"}, {"kind", replaceFile ? "replaced_inode" : "changed_bytes"},
        {"injection_after_actual_preflight", injected}, {"refusal", refusal},
        {"archive_sha256_before", archiveBefore},
        {"archive_sha256_after", sha256(request.archive)},
        {"archive_inode_before", Value::fromInteger(original.st_ino)},
        {"archive_inode_after", Value::fromInteger(changed.st_ino)},
        {"live_profile_sha256", profileBefore}, {"live_profile_raw_bytes_unchanged", true},
        {"live_sqlite_not_opened", true}, {"stage_and_selected_snapshot_absent", true}}));
}

} // namespace

int main(int argc, char** argv) {
    const bool presealOnly = argc == 4 && std::string(argv[3]) == "--preseal-mutation";
    if (argc != 3 && !presealOnly) {
        std::cerr << "Usage: fathom_portable_restore_workflow_tests <scratch-test-root> <r10-evidence-root> [--preseal-mutation]\n";
        return 2;
    }
    try {
        const fs::path evidence = fs::absolute(argv[1]);
        const fs::path r10 = fs::absolute(argv[2]);
        require(fs::is_directory(evidence), "Current lane scratch test root must already exist");
        require(fs::is_directory(r10 / "fixtures/rich"), "r10 rich fixture root is missing");
        const auto workflow = evidence / "workflow";
        directory(workflow);
        const auto metadata = prepareMetadata(workflow, r10 / "fixtures");
        if (presealOnly) {
            presealMutationCase(evidence, r10 / "fixtures", metadata, false);
            presealMutationCase(evidence, r10 / "fixtures", metadata, true);
            std::cout << "PASS portable restore workflow: two actual preflight-to-copy mutations refused before live open\n";
            return 0;
        }
        successCase(evidence, r10 / "fixtures", metadata);
        wrongConfirmationCase(evidence, r10 / "fixtures", metadata);
        combinedParentWorkflowCase(evidence, r10 / "fixtures");
        writeNew(evidence / "workflow/summary.json",
                 fathom::storage::canonical(Object{{"status", "PASS"},
                                                   {"successful_apply_reopen", true},
                                                   {"wrong_confirmation_refused", true},
                                                   {"combined_parent_workflow", true},
                                                   {"real_learner_profile", false}}));
        std::cout << "PASS portable restore workflow: prepare/apply/reopen, wrong-confirmation refusal, "
                     "and combined backup/publication/restore boundary reconciliation\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL portable restore workflow: " << error.what() << '\n';
        return 1;
    }
}
