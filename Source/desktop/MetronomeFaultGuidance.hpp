#pragma once
#include <string>
namespace fathom::desktop {
// Fault-only presentation. Capabilities are existing consumer guards; this
// projection cannot acknowledge output, change preferences, or start sound.
struct MetronomeFaultInput {
    bool started{},terminalJoined{},resolving{},ownsOutcome{},pendingOutcome{},preferencesPending{};
    bool canFinish{},canConnect{},canBack{};
};
inline std::string metronomeFaultGuidance(const MetronomeFaultInput& i){
    if(i.resolving)return "Acknowledging the original sound check. Wait for cleanup.";
    if(i.preferencesPending)return "Output unavailable. Follow the pending settings status below.";
    if(i.started&&i.terminalJoined&&i.canFinish)return "Output unavailable. Choose Finish check for the retained original.";
    if(i.started||i.ownsOutcome||i.pendingOutcome)return "Output unavailable. Waiting for the original check's stopped evidence.";
    if(i.canConnect&&i.canBack)return "Output unavailable. Open Audio settings, then choose Connect audio; or choose Back to leave.";
    if(i.canConnect)return "Output unavailable. Open Audio settings to reconnect.";
    if(i.canBack)return "Output unavailable. Choose Back to leave.";
    return "Output unavailable. Keep this view open; no recovery action is ready.";
}
}
