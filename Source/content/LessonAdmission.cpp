#include "content/LessonAdmission.hpp"
#include "content/Canonical.hpp"
#include "content/LessonPulse.hpp"
#include "content/LessonTempo.hpp"
#include <stdexcept>

namespace fathom::lesson {
Admission::Admission(std::shared_ptr<const music::ValidatedModel> model,json::Value identity,
                     Rational span,bool practice,std::string description,Rational sourceStart)
 :model_(std::move(model)),identity_(std::move(identity)),span_(span),sourceStart_(sourceStart),practice_(practice),description_(std::move(description)) {
    sourceBinding_="lesson-runtime.1:"+content::sha256(json::stringify(identity_));
}
void Admission::validateReference(const reference::Configuration& c) const {
    scheduler::FrameRatio frames;
    if(!c.owner.valid()||!c.binding||c.sourceBinding!=sourceBinding_||!(c.cycle==span_)||!(c.intro==Rational{})
        ||c.unit!=scheduler::BeatUnit::Quarter||c.bpm<20||c.bpm>300
        ||!scheduler::samples(span_,c.rate,c.bpm,c.unit,frames))
        throw std::invalid_argument("Use this admitted selection's complete span, explicit quarter-note tempo (20–300 BPM), supported rate and count-in Off; no substitute source or cutpoint.");
}
reference::Configuration Admission::referenceConfiguration(const scheduler::Owner& owner,std::uint64_t binding,
                                                           std::uint32_t rate,std::uint16_t bpm) const {
    reference::Configuration c;c.owner=owner;c.binding=binding;c.sourceBinding=sourceBinding_;
    c.rate=rate;c.bpm=bpm;c.unit=scheduler::BeatUnit::Quarter;c.cycle=span_;c.intro=Rational{};
    validateReference(c);return c;
}
void Admission::validatePractice(const practice::Configuration& c) const {
    if(!practice_)throw std::invalid_argument("This is an incomplete three-note illustration: reference projection only. Practice repeat/resume requires the authored complete rolling sequence; read its instructions.");
    if(!(c.span==span_)||(c.targetCycles<1||c.targetCycles>maximumScheduledPasses)||c.countIn!=practice::CountIn::Off||c.meter||c.sourceRequiresCountIn
        ||!c.faithfulWholeSpan||c.unit!=scheduler::BeatUnit::Quarter||c.bpm<20||c.bpm>300)
        throw std::invalid_argument("Choose 1–32 scheduled passes of the complete selected direction/cell, count-in Off and explicit quarter-note tempo. No partial cutpoints, invented meter or full-task credit.");
    (void)practice::countInSpan(c);
}
practice::Configuration Admission::practiceConfiguration(std::uint32_t rate,std::uint16_t bpm) const {
    practice::Configuration c;c.span=span_;c.targetCycles=1;c.countIn=practice::CountIn::Off;
    c.faithfulWholeSpan=practice_;c.rate=rate;c.bpm=bpm;c.unit=scheduler::BeatUnit::Quarter;
    validatePractice(c);return c;
}
void Admission::validateOriginal(const practice::Coordinator& coordinator) const {
    validatePractice(coordinator.configuration());
    if(coordinator.kind()!=practice::Kind::Attempt||!coordinator.pending()||coordinator.sealed())
        throw std::invalid_argument("Retain an active original lesson Attempt before preparing its music.");
    const auto context=json::parse(coordinator.context());const auto& cfg=context.object().at("configuration");
    (void)pulseEnabled(cfg);
    (void)tempoRamp(cfg,coordinator.configuration().bpm);
    if(cfg.object().at("runtime_admission")!=identity_||cfg.object().at("source_binding")!=json::Value(sourceBinding_)
        ||cfg.object().at("canonical_variant_id")!=identity_.object().at("variant_id"))
        throw std::invalid_argument("Playback selection differs from the original allocated lesson Attempt; finish its outcome before changing context.");
    for(const auto* key:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs"})
        if(context.object().at(key)!=identity_.object().at(key))throw std::invalid_argument("Original canonical lesson identity changed; retain and reconcile its outcome.");
    using V=json::Value;using O=V::Object;using A=V::Array;const auto& actual=coordinator.configuration();
    const auto n=[](std::int64_t value){return V::fromInteger(value);};
    const V span=A{n(span_.numerator()),n(span_.denominator())};
    const auto end=sourceStart_+span_;
    const V sourceSpan=O{{"start",A{n(sourceStart_.numerator()),n(sourceStart_.denominator())}},
        {"end",A{n(end.numerator()),n(end.denominator())}}};
    const V values=O{{"span",span},{"rate",n(actual.rate)},{"selected_bpm",n(actual.bpm)},{"beat_unit","quarter"},
        {"count_in","off"},{"meter",nullptr},{"target_cycles",n(static_cast<std::int64_t>(actual.targetCycles))},{"faithful_whole_span",true},{"source_requires_count_in",false}};
    if(cfg.object().at("values")!=values||cfg.object().at("source_hashes")!=identity_.object().at("source_hashes")
        ||cfg.object().at("beat_reference_q")!=V(A{n(1),n(1)})||cfg.object().at("synthetic_fixture")!=V(false)
        ||cfg.object().at("source_task_completion")!=V(false)||cfg.find("progression_condition")
        ||cfg.object().at("authored_tempo_ref")!=identity_.object().at("authored_practice_guidance")
        ||context.object().at("span")!=sourceSpan
        ||context.object().at("target")!=V(O{{"cycles",n(static_cast<std::int64_t>(actual.targetCycles))}}))
        throw std::invalid_argument("Original selected-span configuration differs from playback; preserve its recorded source and clock configuration.");
}
}
