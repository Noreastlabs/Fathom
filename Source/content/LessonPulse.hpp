#pragma once
#include "content/StrictJson.hpp"
#include <stdexcept>

namespace fathom::lesson {
// Learner-selected accompaniment, separate from authored meter and task evidence.
inline json::Value pulseConfiguration(bool enabled) {
    return json::Value::Object{{"version",json::Value::fromInteger(1)},
        {"enabled",enabled},{"beat_unit","quarter"},{"accent","none"}};
}
inline bool pulseEnabled(const json::Value& configuration) {
    const auto* value=configuration.find("lesson_metronome");
    if(!value)return false; // Historical original records had no running click.
    if(*value==pulseConfiguration(false))return false;
    if(*value==pulseConfiguration(true))return true;
    throw std::invalid_argument("Unsupported lesson metronome configuration; retain the original outcome and choose supported settings for a new attempt.");
}
}
