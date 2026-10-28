#pragma once
#include "core/AudioOutputLifecycle.hpp"
#include "desktop/DiagnosticText.hpp"

namespace fathom::desktop {
struct ReferenceGuidanceInput {
    output::Snapshot output;
    bool started{},resolving{},stopWhenRunning{},ownerMatches{};
    bool canConnect{},canEnable{},canPlay{},canStop{},canDone{},canBack{};
};
struct ReferenceGuidance {
    std::string state,next;
    std::string primary()const{return state+"\n"+next;}
};
// Presentation never resolves output or allocates an owner. All capabilities
// come from the existing tool and its currently enabled controls.
inline ReferenceGuidance referenceGuidance(const ReferenceGuidanceInput& i){
    using S=output::State;const auto& s=i.output;
    if(i.resolving)return {"Acknowledging the original tone.","Wait for output cleanup; this tool records no practice."};
    if(s.pendingOutcome){
        if(!i.ownerMatches)return {"The original tone needs attention.","Keep this view open; its owner cannot be acknowledged here."};
        if(i.canDone)return {"Tone stopped; acknowledgment is still needed.","Choose Finish tone to release this outcome; another tone needs an explicit Play."};
        return {"Tone outcome is still pending.","Keep this view open while its acknowledgment becomes available."};
    }
    if(s.state==S::Fault&&!s.ownsOutcome)return {"Output is unavailable.",i.canBack?"Open Audio settings to reconnect, or Back to leave.":"Keep this view open and inspect Tone details."};
    if(i.stopWhenRunning||(s.stopRequested&&(s.ownsOutcome||i.started)))return {"A stop has been requested for this tone.","Wait for the stopped outcome, then use Finish tone when available."};
    if(s.ownsOutcome){
        if(s.state==S::Running&&i.canStop)return {"Reference tone is playing.","Use Stop to end it early; this tool records no practice."};
        return {"The original tone still owns the output.","Wait for its stopped outcome; no new tone can start yet."};
    }
    switch(s.state){
        case S::Closed:return {"Output is closed.",i.canConnect?"Open Audio settings, then Connect audio and Enable audio before Play tone.":"Wait for this tone to finish closing; do not reconnect yet."};
        case S::Awaiting:return {"Waiting for the selected output format.","Wait for Audio settings to observe the format; Play tone begins sound."};
        case S::Observed:return {"Selected output format observed.",i.canEnable?"Open Audio settings to enable audio, then Play tone when ready.":"Open Audio settings when the output is observed."};
        case S::Ready:return {i.started?"A tone start has been requested.":"Output is ready for a reference tone.",i.canPlay?"Choose Play tone explicitly; no practice will be recorded.":"Wait for the current request; do not start another tone."};
        case S::Fault:return {"Output is unavailable.",i.canBack?"Open Audio settings to reconnect, or Back to leave.":"Keep this view open and inspect Tone details."};
        case S::Running:case S::Paused:case S::Unresolved:return {"Output state needs attention.","Keep this view open and inspect Tone details."};
    }
    return {"Output state needs attention.","Keep this view open and inspect Tone details."};
}
inline std::string referenceDiagnostics(const ReferenceGuidanceInput& i,std::string_view localError,std::string_view backendError){
    const auto& s=i.output;std::string id;const char* hex="0123456789abcdef";
    for(const auto b:s.owner.id){id+=hex[b>>4];id+=hex[b&15];}
    return std::string("Tone details — read-only. Follow the current action above.\n")+
      "Output state: "+output::stateText(s.state)+"\n"+
      "Owns original tone: "+(s.ownsOutcome?"yes":"no")+"\n"+
      "Pending tone: "+(s.pendingOutcome?"yes":"no")+"; acknowledgment queued: "+(i.resolving?"yes":"no")+"\n"+
      "Output owner bytes (hex): "+id+"\n"+
      "Owner epoch / generation: "+std::to_string(s.owner.epoch)+" / "+std::to_string(s.owner.generation)+"\n"+
      "Matches this tool: "+(i.ownerMatches?"yes":"no")+"\n"+
      "Local feedback: "+diagnosticField(localError,1024)+"\n"+
      "Backend feedback: "+diagnosticField(backendError,1024)+"\n"+
      "Each feedback field is shortened for display only; no practice is recorded.";
}
}
