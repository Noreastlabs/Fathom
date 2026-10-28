#pragma once
#include "core/Scheduler.hpp"

namespace fathom::practice {
// Control-side accepted-evidence map. It neither schedules output nor decides a
// ramp. A provider must supply changes only after successful client submission.
struct TimelineSpec final {
    scheduler::Owner owner;
    Rational span{4}, intro{};
    std::uint32_t rate{44100};
    std::uint16_t initialBpm{120};
    scheduler::BeatUnit unit{scheduler::BeatUnit::Quarter};
    std::uint64_t cycles{1};
};
struct TempoPoint final {
    std::uint64_t cycle{}; // zero-based cycle starting at this exact anchor
    std::uint16_t bpm{};
    scheduler::FramePosition anchor;
};
struct TempoSlice final { std::uint16_t bpm{}; std::uint64_t begin{}, end{}; };
class Timeline final {
public:
    explicit Timeline(TimelineSpec);
    Timeline changed(std::uint64_t cycle, std::uint16_t bpm) const;
    const TimelineSpec& spec() const noexcept { return spec_; }
    const std::vector<TempoPoint>& points() const noexcept { return points_; }
    scheduler::FramePosition coordinate(std::uint64_t cycle, const Rational& offset = Rational{}) const;
    std::uint64_t frame(std::uint64_t cycle, const Rational& offset = Rational{}) const;
    std::uint64_t completed(std::uint64_t acceptedThrough) const;
    std::uint16_t tempo(std::uint64_t cycle) const;
    std::uint16_t acceptedTempo(std::uint64_t acceptedThrough) const;
    std::vector<TempoSlice> slices(std::uint64_t acceptedThrough) const;
    bool extends(const Timeline& previous, std::uint64_t previousThrough, std::uint64_t acceptedThrough) const;
private:
    TimelineSpec spec_;
    std::vector<TempoPoint> points_;
};
}
