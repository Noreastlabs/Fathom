#pragma once
#include "storage/StorageEnvelope.hpp"
#include <cstdint>
#include <filesystem>
#include <functional>
#include <memory>
#include <optional>

namespace fathom::storage {
struct BackupPublicationIdentity {
    std::string device,inode,sha256;
    std::uint64_t bytes=0;
};
struct BackupPublicationRequest {
    std::filesystem::path destination;
    // Empty means expect absent. Replacement binds the exact selected old file.
    std::optional<BackupPublicationIdentity> expected;
    // Explicit original-operation handoff after reconcile. Its retained pointer
    // and resolution are revalidated/synchronized before starting a new backup.
    std::optional<std::string> reconciledPredecessor;
};
enum class BackupPublicationState { Published, NotPublished, Unresolved };
struct BackupPublicationResult {
    BackupPublicationState state=BackupPublicationState::NotPublished;
    std::string code,message;
    Value evidence;
};
// Held by one existing ProfileStore maintenance job. No second queued writer job.
// The same-target lease serializes cooperating Fathom publishers only.
class BackupPublisher final {
public:
    BackupPublisher(std::string operation,BackupPublicationRequest,
                    std::filesystem::path privateStage,
                    std::function<void()> check,
                    std::function<void(const std::string&)> diagnosticHook={});
    ~BackupPublisher();
    BackupPublisher(const BackupPublisher&)=delete;
    BackupPublisher& operator=(const BackupPublisher&)=delete;
    // snapshot is original profile/marker/authority metadata; file is the already
    // verified archive bytes/SHA receipt. Input descriptor remains caller-owned.
    BackupPublicationResult publish(int archiveDescriptor,const Value& file,const Value& snapshot);
    // Inspect the original operation; never issues another rename. Explicit sync
    // may finish its unconfirmed directory flush after identities are rechecked.
    BackupPublicationResult reconcile(const std::string& profileId,const std::string& schemaSha256);
private:
    struct Impl;std::unique_ptr<Impl> impl_;
};
} // namespace fathom::storage
