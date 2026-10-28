#pragma once
#include "storage/StorageEnvelope.hpp"
#include "storage/BackupSnapshot.hpp"
#include "storage/RestoreApply.hpp"
#include <filesystem>
#include <functional>
#include <future>
#include <memory>

namespace fathom::storage {
// Status is part of the persistence contract: an unresolved reply is not proof
// that a write failed. Keep the original owner, operation and payload until
// reconciliation establishes Confirmed or DefinitelyAbsent.
enum class Status { Confirmed, DefinitelyAbsent, Unresolved, Conflict, DefiniteFailure, Unsupported, Busy };
const char* statusName(Status) noexcept;
struct Reply {
    Status status=Status::DefiniteFailure;
    std::string operation,owner,code,message;
    Value data;
};
struct StoreOptions {
    std::filesystem::path path;
    bool create=false;
    // Explicit original operation only; no ordinary jobs until reconciliation.
    std::string restoreRecoveryOperation;
    std::string createdUtc;
    // Semantic owners validate supported values; absence never means acceptance.
    std::function<bool(const std::string&,std::int64_t,const Value&)> preferenceValidator;
    std::function<bool(const Value&)> sourceValidator;
    // Controlled fault/queue evidence only. Empty in application use. Invoked on writer.
    std::function<void(const std::string& phase,const std::string& operation)> diagnosticHook;
};
class ProfileStore final {
public:
    explicit ProfileStore(StoreOptions);
    ~ProfileStore();
    ProfileStore(const ProfileStore&)=delete;
    ProfileStore& operator=(const ProfileStore&)=delete;
    // Call only after the consumer close/detach gates pass. Stop accepting work
    // without waiting for the writer; accepted jobs retain their original
    // futures and drain normally. Nothing is cancelled or acknowledged here.
    void beginShutdown();
    // True only after accepted work has drained and SQLite closed on the writer.
    // The profile lease remains held until this Store is destroyed. The caller
    // must keep consumers/Store alive until their own close gates are satisfied.
    bool shutdownComplete() const noexcept;
    // A nonempty value means writer-side close failed: retain this Store/lease
    // and show the failure. It never converts failed cleanup into completion.
    std::string shutdownError() const;
    class Future final {
    public:
        Future(std::future<Reply> future,std::string operation,std::string owner)
          :future_(std::move(future)),operation_(std::move(operation)),owner_(std::move(owner)){}
        Future(Future&&) noexcept=default;
        Future& operator=(Future&&) noexcept=default;
        Reply get(){return future_.get();}
        bool valid()const noexcept{return future_.valid();}
        template<class Rep,class Period> std::future_status wait_for(const std::chrono::duration<Rep,Period>& delay){return future_.wait_for(delay);}
        const std::string& operationId()const noexcept{return operation_;}
        const std::string& ownerId()const noexcept{return owner_;}
    private:
        std::future<Reply> future_;
        std::string operation_,owner_;
    };
    Future createSession(std::string operation,std::string startedUtc,std::string timezone,
                         std::optional<std::int64_t> plannedSeconds={},Value plan=nullptr);
    // Retain the original operation and Session identity before submission.
    // The plan binds both; exact replay is read-only, conflicting reuse fails.
    Future createSessionWithIdentity(std::string operation,std::string session,
                         std::string startedUtc,std::string timezone,
                         std::int64_t plannedSeconds,Value boundPlan);
    Future createSessionWithIdentity(std::string operation,std::string session,
                         std::string startedUtc,std::string timezone,
                         std::optional<std::int64_t> plannedSeconds,Value boundPlan);
    Future closeSession(std::string operation,std::string session,std::string endedUtc,std::string outcome);
    Future allocate(std::string operation,std::string kind,Value context,std::string allocationUtc);
    Future seal(std::string operation,std::string owner,std::string originalBytes);
    Future commit(std::string operation,std::string owner,std::string originalBytes);
    Future reconcile(std::string operation,std::string owner,std::string originalBytes);
    Future checkpoint(std::string operation,std::string owner,std::int64_t generation,
                      std::int64_t sequence,std::string originalBytes);
    Future recoveryState(std::string operation,std::string owner);
    // Explicit suite admission migrates schema1 only after a retained verified
    // SQLite snapshot; ordinary opening never silently migrates old profiles.
    Future beginSuite(std::string operation,std::string suiteId,std::string createdUtc,Value frozenPlan);
    Future appendSuiteMember(std::string operation,std::string suiteId,std::string attemptId,std::string completedUtc);
    Future readSuite(std::string operation,std::string suiteId={});
    Future submitSuiteReview(std::string operation,std::string suiteId,std::string reviewedUtc,Value score);
    static std::string legacySchemaIdentity();
    Future appendLate(std::string operation,std::string owner,std::string eventId,
                      std::string receivedUtc,std::string originalBytes);
    Future acknowledge(std::string operation,std::string factId,std::string item,
                       std::int64_t contentRevision,std::string acknowledgedUtc);
    Future attest(std::string operation,std::string originalBytes);
    // Cheap identity read for profile-bound draft repositories; no snapshot or write.
    Future readProfileIdentity(std::string operation);
    // Bounded key-only discovery; cursor belongs to the exact prefix.
    Future readPreferenceKeys(std::string operation,std::string prefix,std::string afterKey={},std::int64_t limit=64);
    Future readPreferences(std::string operation,std::string key);
    Future compareExchangePreferences(std::string operation,std::string key,std::int64_t namespaceVersion,
                                      std::int64_t expectedRevision,std::string bytes,bool applicationStopped);
    Future writeCache(std::string operation,std::string key,std::int64_t evidenceMarker,
                      std::string evidenceHash,std::string contentHash,std::string ruleVersion,
                      std::string asOfUtc,std::string bytes);
    Future readCache(std::string operation,std::string key,std::string contentHash,
                     std::string ruleVersion,std::string asOfUtc);
    Future observeRule(std::string operation,std::string factId,Value config,Value contentSelection,
                       Value displayedState,std::string asOfUtc);
    Future snapshot(std::string operation);
    // Requires an idle writer and stopped/reconciled caller. Conflicting work is
    // deferred until the snapshot stage finishes; the existing lease is retained.
    Future prepareBackupSnapshot(std::string operation, BackupSnapshotOptions);
    // Concrete original-preserving preview; explicit later apply remains separate.
    Future prepareRestore(std::string operation, BackupSnapshotOptions, RestorePreparationRequest);
    Future applyRestore(std::string operation, RestoreApplyRequest);
    Future reconcileRestore(std::string operation, RestoreApplyRequest);
    // Reconcile an original backup operation without generating a new snapshot.
    Future reconcileBackupPublication(std::string operation, BackupSnapshotOptions);
    // A timeout is an observation, not cancellation. The original future remains valid.
    static Reply waitForAcknowledgment(Future&);
    static std::string schemaIdentity();
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
} // namespace fathom::storage
