#pragma once
#include "practice/AttemptCapture.hpp"
#include "storage/Recovery.hpp"
#include <deque>

namespace fathom::capture {
struct StartRequest {
    Binding binding; // owner empty until actual allocation
    practice::Configuration configuration;
    std::uint64_t epoch{};
};
enum class SessionPhase { Idle, Allocating, AllocationUnknown, InitialCheckpoint,
    Ready, Active, Review, SealedCheckpoint, Saving, Saved, Recovering, Failed };
const char* phaseText(SessionPhase) noexcept;

// Serialized off-audio owner. Store and Coordinator must outlive this object.
// The view retains the object through close, all futures and output resolution.
class PracticeSession final {
public:
    PracticeSession(storage::ProfileStore&,practice::Coordinator&);
    bool start(StartRequest,std::uint64_t commandSequence,std::int64_t nowMs);
    void cancelBeforeSound(std::uint64_t requestedNs);
    void poll(std::int64_t nowMs,const std::string& receivedUtc);
    std::optional<scheduler::Owner> takeStart(std::int64_t nowMs);
    bool save(Value explicitAssessment,Outcome,std::int64_t nowMs);
    bool retry(std::int64_t nowMs); // explicit; retains original checkpoint/envelope
    bool inspectAllocation(std::int64_t nowMs); // uncertain returned UUID only
    bool recover(storage::RecoveryBinding); // explicit stopped reopen
    bool again(bool outputOwnershipCleared); // arms another explicit Start only
    bool canLeave(bool outputOwnershipCleared) const;
    void requestExitDiscard() noexcept;
    void retryExitDiscard(std::int64_t now);
    bool canLeaveForExit(bool outputOwnershipCleared,std::int64_t nowMs);
    bool stopRequired() const noexcept { return stopRequired_; }
    SessionPhase phase() const noexcept { return phase_; }
    const storage::Reply& feedback() const noexcept { return feedback_; }
    std::string displayText()const;
    const Binding& binding() const noexcept { return request_.binding; }
    const std::optional<storage::Envelope>& original() const noexcept { return original_; }
    const std::optional<storage::CheckpointSnapshot>& latestCheckpoint() const noexcept {return latest_;}
    storage::CheckpointState checkpointState(std::int64_t nowMs);
    bool startTaken()const noexcept{return startTaken_;}
private:
    struct Audit {std::string owner,id,received,bytes;std::optional<storage::ProfileStore::Future> future;bool failed=false;std::int64_t submitted=0;};
    void clock(std::int64_t);
    void beginAllocated(std::int64_t);
    void offer(std::int64_t,bool force,const std::string* observedUtc=nullptr);
    void setFeedback(storage::Status,const char*,const char*);
    void collectAudit(const std::string&);
    void serviceAudit(std::int64_t,bool explicitRetry=false);
    storage::ProfileStore& store_;
    practice::Coordinator& coordinator_;
    StartRequest request_;
    SessionPhase phase_{SessionPhase::Idle};
    storage::Reply feedback_;
    std::string prefix_;
    std::optional<storage::ProfileStore::Future> allocation_,inspection_;
    std::unique_ptr<storage::CheckpointCoordinator> checkpoint_;
    std::unique_ptr<SaveOperation> save_;
    std::unique_ptr<storage::RecoveryOperation> recovery_;
    std::optional<storage::RecoveryBinding> recoveryBinding_;
    std::optional<storage::CheckpointSnapshot> latest_,sealedCheckpoint_;
    std::optional<storage::Envelope> original_;
    Value assessment_;
    std::optional<Outcome> outcome_;
    std::deque<Audit> audit_;
    std::size_t auditIndex_{};
    std::uint64_t commandSequence_{},cancelNs_{};
    std::uint64_t endpointActive_{};
    std::int64_t now_{},submitted_{},checkpointSequence_{-1};
    std::string observed_;
    bool exitDiscard_{};
    bool cancelled_{},startTaken_{},stopRequired_{},clockSet_{},allocationAbsent_{},allocationRecovery_{},terminalObserved_{};
};
} // namespace fathom::capture
