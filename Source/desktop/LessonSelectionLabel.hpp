#pragma once
#include "content/LessonAdmission.hpp"
#include <array>

namespace fathom::desktop {
// Only a typed, locally admitted selection supplies this label. Saved text is never trusted.
inline std::string lessonSelectionLabel(const lesson::Admission& admission) {
    const auto* selection = admission.identity().find("selection");
    if (!selection) return {};
    const auto& events = admission.model()->source().events;
    const auto& fields = selection->object();
    std::int64_t ordinal{};
    if (fields.at("version") != json::Value("lesson-transfer-cell.1")
        || !fields.at("ordinal").integer(ordinal) || ordinal < 1 || ordinal > 5
        || events.size() != 4 || events.front().tones.empty() || events.back().tones.empty())
        throw std::runtime_error("Unsupported admitted practice section.");
    const auto first = events.front().tones.front().string;
    const auto last = events.back().tones.front().string;
    constexpr std::array<const char*, 6> names{"low E", "A", "D", "G", "B", "high e"};
    if (first < 1 || first > 6 || last < 1 || last > 6)
        throw std::runtime_error("The admitted section has no supported string pair.");
    return "Cell " + std::to_string(ordinal) + " of 5: " + names[first - 1]
        + " → " + names[last - 1] + " (4 notes)";
}
}
