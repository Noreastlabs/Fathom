#pragma once
#include <string>

namespace fathom::learn {
enum class QueueCapturePhase { Other, Idle, Saved };
enum class QueueCaptureResult { Unresolved, Saved, UnusedPreparation };
// PracticeSession retains its immutable original envelope when Saved -> Again
// changes the phase to Idle. A subsequent Start clears that original. This
// projection requires the same Session/Attempt and exact original context.
struct QueueCaptureEvidence {
    QueueCapturePhase phase{QueueCapturePhase::Other};
    bool canLeave{}, originalContextMatches{};
    std::string expectedSession, currentSession, owner, baselineOwner;
    std::string originalOwner, originalSession, originalKind;
};
inline QueueCaptureResult queueCaptureResult(const QueueCaptureEvidence& e) {
    if (!e.canLeave || e.expectedSession.empty() || e.currentSession != e.expectedSession)
        return QueueCaptureResult::Unresolved;
    if (e.phase != QueueCapturePhase::Idle && e.phase != QueueCapturePhase::Saved)
        return QueueCaptureResult::Unresolved;
    const bool saved = e.originalContextMatches && !e.owner.empty() &&
        e.originalOwner == e.owner && e.originalSession == e.expectedSession &&
        e.originalKind == "Attempt";
    if (saved) return QueueCaptureResult::Saved;
    // A retained envelope for this Session must never become unused cancellation.
    if (e.phase == QueueCapturePhase::Idle && e.owner == e.baselineOwner &&
        e.originalSession != e.expectedSession)
        return QueueCaptureResult::UnusedPreparation;
    return QueueCaptureResult::Unresolved;
}
} // namespace fathom::learn
