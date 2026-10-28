#include "practice/LessonAttempt.hpp"
#include "content/LessonPulse.hpp"
#include <stdexcept>

namespace fathom::capture {
StartRequest lessonStart(const lesson::Admission& admission,const practice::Configuration& cfg,
                         std::string session,std::string utc,std::string zone,std::uint64_t epoch,bool beatClick,std::optional<metronome::Ramp> initialRamp) {
    admission.validatePractice(cfg);
    if(!epoch)throw std::invalid_argument("Explicit acknowledged output epoch is required before allocating a lesson attempt.");
    const auto& id=admission.identity();using V=json::Value;using O=V::Object;using A=V::Array;
    auto n=[](std::int64_t x){return V::fromInteger(x);};
    const auto sourceStart=admission.sourceStart(),sourceEnd=sourceStart+cfg.span;
    const auto& hashes=id.object().at("source_hashes");
    V configuration=O{{"canonical_variant_id",id.object().at("variant_id")},{"values",configurationValues(cfg)},{"synthetic_fixture",false},{"authored_tempo_ref",id.object().at("authored_practice_guidance")},
        {"beat_reference_q",A{n(1),n(1)}},{"source_hashes",hashes},{"runtime_admission",id},{"source_binding",admission.sourceBinding()},
        {"selected_scope_notice",admission.description()},{"source_task_completion",false},
        {"lesson_metronome",lesson::pulseConfiguration(beatClick)}};
    if(initialRamp)configuration.object()["lesson_tempo"]=lesson::tempoConfiguration(*initialRamp,cfg.bpm);
    O context{{"session_id",std::move(session)},{"configuration_version",n(1)},{"configuration",std::move(configuration)},
        {"span",O{{"start",A{n(sourceStart.numerator()),n(sourceStart.denominator())}},{"end",A{n(sourceEnd.numerator()),n(sourceEnd.denominator())}}}},{"target",O{{"cycles",n(static_cast<std::int64_t>(cfg.targetCycles))}}}};
    for(const auto* key:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs"})context.emplace(key,id.object().at(key));
    Binding binding{"","Attempt",context,hashes,std::move(utc),std::move(zone)};
    validateContext(binding,cfg);return {std::move(binding),cfg,epoch};
}
}
