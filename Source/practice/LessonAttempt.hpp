#pragma once
#include "content/LessonAdmission.hpp"
#include "content/LessonTempo.hpp"
#include "practice/PracticeSession.hpp"

namespace fathom::capture {
// Pure preallocation binding. ProfileStore remains the sole result-ID allocator.
StartRequest lessonStart(const lesson::Admission&,const practice::Configuration&,
                         std::string session,std::string practiceUtc,std::string timezone,std::uint64_t epoch,
                         bool beatClick=false,std::optional<metronome::Ramp> initialRamp={});
}
