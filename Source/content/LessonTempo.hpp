#pragma once
#include "content/StrictJson.hpp"
#include "metronome/Metronome.hpp"
#include <stdexcept>

namespace fathom::lesson {
// Initial learner choice only. Applied changes remain accepted transport facts.
inline metronome::Settings tempoSettings(int bpm,std::optional<metronome::Ramp> ramp) {
    metronome::Settings s;s.tempo=bpm;s.ramp=std::move(ramp);metronome::validate(s);return s;
}
inline json::Value tempoConfiguration(const metronome::Ramp& r,int selectedBpm) {
    (void)tempoSettings(selectedBpm,r);using V=json::Value;
    return V::Object{{"version",V::fromInteger(1)},{"ramp",V::Object{{"up",r.up},
        {"step",V::fromInteger(r.step)},{"every",V::fromInteger(r.every)},{"target",V::fromInteger(r.target)}}}};
}
inline std::optional<metronome::Ramp> tempoRamp(const json::Value& configuration,int selectedBpm) {
    const auto* value=configuration.find("lesson_tempo");
    if(!value)return {}; // Absence retains historical/default Off bytes.
    const char* error="Unsupported lesson tempo configuration; choose Off or a supported initial ramp for a new attempt.";
    if(!value->isObject()||value->object().size()!=2||!value->find("version")||!value->find("ramp")
        ||*value->find("version")!=json::Value::fromInteger(1))throw std::invalid_argument(error);
    const auto& r=*value->find("ramp");if(!r.isObject()||r.object().size()!=4||!r.find("up")||!r.find("up")->isBool())throw std::invalid_argument(error);
    auto number=[&](const char* key,int lo,int hi){std::int64_t n{};const auto* v=r.find(key);if(!v||!v->integer(n)||n<lo||n>hi)throw std::invalid_argument(error);return static_cast<int>(n);};
    metronome::Ramp result{r.find("up")->boolean(),number("step",1,20),number("every",1,32),number("target",20,300)};
    if(*value!=tempoConfiguration(result,selectedBpm))throw std::invalid_argument(error);return result;
}
}
