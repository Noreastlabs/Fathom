#pragma once
#include "storage/ProfileStore.hpp"

namespace fathom::storage {
struct CheckpointSnapshot {
    std::int64_t generation=0,sequence=0;
    std::string bytes;
};
struct CheckpointState {
    bool initialAcknowledged=false,inFlight=false,hasUnsaved=false,stopRequired=true;
    std::string code="INITIAL_CHECKPOINT_REQUIRED";
    std::optional<CheckpointSnapshot> acknowledged,inFlightSnapshot,unsaved;
    std::optional<Reply> lastReply;
};
// Single off-audio control owner. Caller time is monotonic milliseconds, never practice time.
class CheckpointCoordinator final {
public:
    CheckpointCoordinator(ProfileStore&,std::string owner,std::string kind,Value allocatedContext,std::string operationPrefix);
    void offer(CheckpointSnapshot,std::int64_t nowMs,bool force=false);
    void poll(std::int64_t nowMs);
    // Consumer explicitly remains stopped; clears only a resolved ACK timeout, never starts sound.
    bool resolveAcknowledgedWhileStopped();
    bool retryPendingForExit(std::int64_t nowMs);
    void quiesceForExit() noexcept { halted_=true; latest_.reset(); } // keep accepted future and persisted snapshots
    CheckpointState state(std::int64_t nowMs);
private:
    struct Captured {CheckpointSnapshot snapshot;std::int64_t capturedMs;bool forced;Value active;bool sealed;};
    ProfileStore& store_;
    std::string owner_,kind_,prefix_;
    Value context_;
    std::optional<Captured> latest_,pending_,acknowledged_,highWater_;
    std::optional<ProfileStore::Future> future_;
    std::optional<Reply> reply_;
    std::optional<std::int64_t> lastClock_,lastSubmit_;
    bool halted_=false,timeout_=false;
    void clock(std::int64_t);
    void submitIfDue(std::int64_t);
};
} // namespace fathom::storage
