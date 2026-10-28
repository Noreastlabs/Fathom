#pragma once
#include "practice/PracticeSession.hpp"
#include "desktop/DiagnosticText.hpp"
#include <string_view>
#include <string>
#include <algorithm>

namespace fathom::desktop {
// A read-only projection. Command availability is supplied by the existing view;
// no guidance text or diagnostic receipt grants a transition.
struct PracticeGuidanceInput {
    bool attached{};
    capture::SessionPhase phase{capture::SessionPhase::Idle};
    storage::Status receipt{storage::Status::DefiniteFailure};
    bool stopRequired{}, hasOwner{}, hasOriginal{}, outputCleared{true};
    bool canLeave{}, canStart{}, canSave{}, canRetry{}, canAgain{}, canStop{};
    bool canConnect{}, canEnable{}, priorActivityBlocked{};
    std::string startPrerequisite; // Read-only actual output/admission projection; never a command.
};
struct PracticeGuidance {
    std::string status, next;
    std::string primary() const { return status + "\n" + next; }
};
inline PracticeGuidance practiceGuidance(const PracticeGuidanceInput& i) {
    using P=capture::SessionPhase;using S=storage::Status;
    const auto wait="Keep this preview open; the original operation is unresolved.";
    const auto retry=i.canRetry?"Retry original to reconcile; a pending operation may still need time.":wait;
    if(!i.attached)return {"No practice profile attached.","Choose Create / open local profile on Home. No Attempt, audio or curriculum credit."};
    // Saved is authoritative for the sealed result even when a later receipt is
    // unknown. Output resolution and late-evidence receipts are separate work.
    if(i.phase==P::Saved){
        if(i.canAgain)return {"Result saved.","Choose Again to prepare another attempt, then Start explicitly."};
        if(i.canLeave&&i.outputCleared&&i.receipt==S::Confirmed)return {"Result saved.","The original result is resolved. Use the available return controls."};
        if(i.receipt==S::Conflict)return {i.outputCleared?"Result saved; remaining evidence conflicts.":"Result saved; cleanup and conflicting evidence remain.",i.canRetry?"Retry original to reconcile; conflicting data cannot be overwritten.":"Keep this preview open; conflicting data cannot be overwritten."};
        if(!i.outputCleared)return {"Result saved; output cleanup is pending.",i.canRetry?"Retry original to finish output cleanup; do not save a new result.":wait};
        return {"Result saved; remaining evidence needs attention.",retry};
    }
    if(i.phase==P::Idle){
        if(!i.startPrerequisite.empty())return {i.canStart?"Ready for practice.":"Practice is stopped.","Next action: "+i.startPrerequisite};
        if(i.canStart)return {"Ready for practice.","Choose Start when you are ready; opening this page records no practice."};
        if(i.canConnect)return {"Practice is stopped.","Open Audio settings for your speakers or headphones before Start."};
        if(i.canEnable)return {"Practice is stopped.","Open Audio settings to enable the selected output before Start."};
        return {"Practice is stopped.","Wait for output readiness; Start stays explicit."};
    }
    if(i.phase==P::Failed && !i.hasOwner && i.canLeave && i.receipt==S::DefiniteFailure && i.priorActivityBlocked)
        return {"Practice did not start; an earlier activity needs recovery.","Return to Home. Keep this profile and its original recovery records; recover the earlier unfinished activity before another Start."};
    if(i.phase==P::Failed && !i.hasOwner && i.canLeave)
        return {"Practice did not start; no record was allocated.",i.canRetry?"Use Retry original to prepare another explicit Start.":"Keep the preview open and inspect Save details."};
    // Retry can enter Saving/Recovering while the last failed receipt remains.
    // The current operation's phase is not replaced by that stale receipt.
    if(i.phase==P::Recovering)return {"Checking the original interrupted result.",i.receipt==S::Conflict?"A receipt conflicts; wait for the original recovery without overwriting.":"Keep this preview open; recovery cannot start sound."};
    if(i.phase==P::Saving)return {"Save not yet confirmed.",i.receipt==S::Conflict?"A receipt conflicts; wait for the original save without overwriting.":"Wait for the original save; Again remains unavailable."};
    if(i.receipt==S::Conflict)
        return {"Stored data conflicts; no overwrite is allowed.",i.canRetry?"Retry original to reconcile the same result; keep this preview open.":wait};
    switch(i.phase){
        case P::Allocating:return {i.stopRequired?"Start cancelled; allocation is still unresolved.":"Preparing the original practice record.","Wait for its response; do not start another attempt."};
        case P::AllocationUnknown:return {"Allocation is unknown; no new attempt can start.",i.hasOwner&&i.canRetry?"Retry original to check this allocation; no new Start yet.":wait};
        case P::InitialCheckpoint:return {"Initial checkpoint is not yet confirmed.",i.stopRequired?wait:"Wait for the checkpoint before sound can start."};
        case P::Ready:return {"Initial checkpoint confirmed; preparing output.",i.canStop?"Wait for output, or use Stop to end this attempt.":"Wait for the current attempt; do not start another."};
        case P::Active:return i.stopRequired?PracticeGuidance{"Practice interrupted; saving needs attention.","Keep this preview open while output stops and facts are retained."}:PracticeGuidance{"Attempt in progress.","Only confirmed running output counts as active practice time."};
        case P::Review:
            if(i.stopRequired)return {"Result retained; checkpoint needs attention.",retry};
            return {"Attempt ended; review the actual result.",i.canSave?"Choose an optional self-assessment, then Save result.":"Wait for the ended result before saving; playback is not an assessment."};
        case P::SealedCheckpoint:return {"Result sealed; its checkpoint is not yet confirmed.",retry};
        case P::Saving:return {"Save not yet confirmed.","Wait for the original save; Again remains unavailable."};
        case P::Recovering:return {"Checking the original interrupted result.","Keep this preview open; recovery cannot start sound."};
        case P::Failed:return {i.hasOriginal?"Original result is retained; save is not confirmed.":"Practice needs recovery; saving is not confirmed.",retry};
        case P::Idle:case P::Saved:break;
    }
    return {"Practice state needs attention.",wait};
}

inline std::string practiceDiagnostics(const PracticeGuidanceInput& i,const storage::Reply& r,std::string_view localError={}){
    // 256 raw bytes per key and 1024 for message: <=7168 escaped bytes plus
    // fixed labels/context and <=4096 for an existing local error. Display-only limits, not storage retention policy.
    return std::string("Save details — read-only; no operation runs from this view.\n")+
      "Phase: "+capture::phaseText(i.phase)+"\n"+
      "Original result in memory: "+(i.hasOriginal?"yes":"no")+"\n"+
      "Output ownership cleared: "+(i.outputCleared?"yes":"no")+"\n"+
      "Operation: "+diagnosticField(r.operation,256)+"\n"+
      "Receipt owner: "+diagnosticField(r.owner,256)+"\n"+
      "Code: "+diagnosticField(r.code,256)+"\n"+
      "Message: "+diagnosticField(r.message,1024)+"\n"+
      "Local error: "+diagnosticField(localError,1024)+"\n"+
      "Long fields are shortened for display only. Original receipts stay unchanged.";
}
}
