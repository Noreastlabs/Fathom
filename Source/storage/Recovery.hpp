#pragma once
#include "storage/ProfileStore.hpp"

namespace fathom::storage {
struct RecoveryBinding {
    std::string owner, kind;
    Value context;
    // Only exact original bound metadata, never inferred from current content.
    std::optional<Value> originalAuthoredTempoRef;
    std::optional<std::string> originalSealedBytes;
    std::int64_t currentGeneration=0, currentSerial=0;
};
enum class RecoveryKind { Final, Original, Interrupted, NeedsInitialCheckpoint };
struct RecoveryPlan {
    RecoveryKind kind=RecoveryKind::NeedsInitialCheckpoint;
    std::string owner, bytes, digest;
    Value stoppedSnapshot;
    // Absent means no fresh transport generation; original sealed/final reconciliation still works.
    std::optional<std::int64_t> nextGeneration;
    std::int64_t serial=0;
};
// After the accepted outer checkpoint validation: verify only unsealed ledgers we may close.
Rational confirmedRecoveryQuantity(const Value&);
void validateUnsealedRecoverySnapshot(const Value& practiceSnapshot);
// Input is the actual validated store recovery reply. Throws on mismatched/corrupt facts.
RecoveryPlan planRecovery(const Reply&,const RecoveryBinding&);
// Off-audio, single control-thread owner. Poll never waits. No automatic retry on error.
class RecoveryOperation final {
public:
    RecoveryOperation(ProfileStore&,RecoveryBinding,std::string operationPrefix);
    bool poll(); // true only when terminal; a nonterminal call advances at most one stage
    bool finished()const noexcept{return finished_;}
    bool confirmed()const noexcept{return finished_&&reply_.status==Status::Confirmed;}
    bool canRetry()const noexcept;
    bool retry(); // explicit reconciliation of the same owner/bytes/operation prefix
    const std::string& operationPrefix()const noexcept{return prefix_;}
    const Reply& reply()const noexcept{return reply_;}
    const std::optional<RecoveryPlan>& plan()const noexcept{return plan_;}
private:
    enum class Stage { Read, Reconcile, Seal, Commit };
    ProfileStore& store_;
    RecoveryBinding binding_;
    std::string prefix_;
    std::optional<ProfileStore::Future> future_;
    std::optional<RecoveryPlan> plan_;
    Stage stage_=Stage::Read;
    bool finished_=false;
    Reply reply_;
    void finish(Reply);
};
} // namespace fathom::storage
