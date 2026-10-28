#pragma once
#include "core/PracticeTransport.hpp"
#include "storage/CheckpointCoordinator.hpp"

namespace fathom::capture {
using Value = json::Value;
// Caller retains these exact allocation inputs. No lookup of current content,
// allocation, audio work or filesystem access occurs while building a capture.
struct Binding final {
    std::string owner, kind;
    Value context, sourceHashes;
    std::string practiceUtc, timezone;
};
enum class Outcome { Stop, Natural, InterruptedError };
Value configurationValues(const practice::Configuration&);
// Same binding rules as capture, before an identity is allocated. No UUID is
// fabricated for preflight; source hashes must cover the exact pinned references.
void validateContext(const Binding&, const practice::Configuration&);
storage::Envelope makeEnvelope(const practice::Coordinator&, const Binding&,
                               Value explicitAssessment, Outcome);
storage::CheckpointSnapshot makeCheckpoint(const practice::Coordinator&, const Binding&,
    std::int64_t sequence, Value explicitAssessment = nullptr,
    std::optional<Outcome> = {}, const storage::Envelope* sealed = nullptr,
    bool saveUncertain = false);
// Audit only; does not change an envelope, interval, cycle or progression credit.
Value lateEvidence(const practice::Progress&);
Value lateEvidence(const practice::Progress&,const practice::Timeline&);

// One off-audio control operation owns one immutable original envelope. The
// Store must outlive this operation. Timeouts do not cancel its original future.
class SaveOperation final {
public:
    SaveOperation(storage::ProfileStore&, practice::Coordinator&, Binding,
                  Value assessment, Outcome, std::string operationPrefix, std::int64_t nowMs);
    // Explicit retry/reconcile of already sealed bytes, including a previously
    // natural/stop outcome followed by a later save error. Never reconstruct it.
    SaveOperation(storage::ProfileStore&, practice::Coordinator&, const storage::Envelope& original,
                  std::string operationPrefix, std::int64_t nowMs);
    bool poll(std::int64_t nowMs); // nonblocking; at most one stage per call
    bool finished() const noexcept { return finished_; }
    bool saved() const noexcept { return saved_; }
    const storage::Reply& feedback() const noexcept { return feedback_; }
    const storage::Envelope& original() const noexcept { return envelope_; }
    bool release(practice::Coordinator&) const; // confirmation only; never starts
private:
    enum class Stage { Reconcile, Seal, Commit };
    void submit(Stage, std::int64_t);
    void finish(storage::Reply, bool saved = false);
    storage::ProfileStore& store_;
    storage::Envelope envelope_;
    std::string prefix_;
    Stage stage_{Stage::Reconcile};
    std::optional<storage::ProfileStore::Future> future_;
    storage::Reply feedback_;
    std::int64_t submittedMs_{}, lastMs_{};
    bool finished_{}, saved_{};
};
} // namespace fathom::capture
