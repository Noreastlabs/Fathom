#pragma once
#include "content/ExerciseQueue.hpp"

namespace fathom::navigation {
// Membership only. Storage validates immutable completed envelopes and records
// the explicit review durably; this class never writes or grants performance.
struct SuiteCompletedAttempt {
    std::string sessionId, attemptId, sourceExerciseKey;
    AdmissionIdentity admission;
    bool operator==(const SuiteCompletedAttempt& other) const {
        return sessionId == other.sessionId && attemptId == other.attemptId &&
            sourceExerciseKey == other.sourceExerciseKey && admission == other.admission;
    }
};
class ExerciseSuiteReview final {
public:
    explicit ExerciseSuiteReview(std::string suiteId) : suiteId_(std::move(suiteId)) {
        if (suiteId_.empty()) throw std::invalid_argument("A suite review requires its durable suite identity.");
    }
    const std::string& suiteId() const noexcept { return suiteId_; }
    const std::vector<SuiteCompletedAttempt>& completed() const noexcept { return completed_; }
    bool frozen() const noexcept { return frozen_; }
    bool record(const ExerciseLaunch& launch, const ExerciseResolution& receipt,
                bool naturalTargetCompleted, std::string& reason) {
        reason.clear();
        if (!naturalTargetCompleted) return true; // saved Stop/abort is not completed membership
        if (receipt.disposition != ResultDisposition::Saved || !receipt.canLeave || !receipt.outputCleared ||
            receipt.ticket != launch.ticket || receipt.sessionId != launch.sessionId ||
            receipt.attemptId.empty() || !launch.exercise.admission ||
            !(receipt.admission == *launch.exercise.admission))
            return fail(reason, "The completed result does not belong to this exercise.");
        const SuiteCompletedAttempt value{receipt.sessionId,receipt.attemptId,launch.exercise.sourceExerciseKey,receipt.admission};
        for (const auto& prior : completed_)
            if (prior.attemptId == value.attemptId) return prior == value ? true : fail(reason,"Attempt identity changed during suite reconciliation.");
        if (frozen_) return fail(reason, "The final review membership is already fixed.");
        completed_.push_back(value);return true;
    }
    void freeze() noexcept { frozen_ = true; }
private:
    static bool fail(std::string& reason, const char* message) {reason=message;return false;}
    std::string suiteId_;
    std::vector<SuiteCompletedAttempt> completed_;
    bool frozen_{};
};
}
