#pragma once

#include "core/Scheduler.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace fathom::polyrhythm {

struct Ratio {
    int x{};
    int y{};
};

struct Event {
    int layer{};
    int index{};
    int tick{};
    Rational position;
};

inline bool operator==(const Event& left, const Event& right) noexcept {
    return left.layer == right.layer && left.index == right.index && left.tick == right.tick &&
           left.position == right.position;
}

struct Cycle {
    int ticks{};
    std::vector<Event> events;
};

void validate(const Ratio&);
int commonCycleTicks(const Ratio&);
Cycle makeCycle(const Ratio&);
scheduler::Plan compilePlan(const Ratio&, const scheduler::Owner&, std::uint64_t binding,
                            std::string sourceBinding, std::uint32_t sampleRate,
                            std::uint16_t bpm, scheduler::BeatUnit);

// Control-thread-owned immutable plan bank. Runtime code may select a precompiled
// tempo plan, but the scheduler::Cursor remains the sole musical clock owner.
class PlanBank final {
public:
    PlanBank(const Ratio&, const scheduler::Owner&, std::uint64_t binding,
             std::string sourceBinding, std::uint32_t sampleRate,
             scheduler::BeatUnit, std::uint16_t initialBpm = 60);
    const scheduler::Plan& initial() const noexcept { return tempos_[initialBpm_ - 20]; }
    const scheduler::Plan* tempo(int bpm) const noexcept;
    std::size_t retainedEventCount() const noexcept;

private:
    std::array<scheduler::Plan, 281> tempos_;
    std::uint16_t initialBpm_{60};
};

struct LayerControls final {
    int volumeA{100};
    int volumeB{100};
    bool muteA{};
    bool muteB{};
    bool soloA{};
    bool soloB{};
};

struct LayerGains final {
    int a{};
    int b{};
};

void validateLayerControls(const LayerControls&);
LayerGains resolveLayerGains(const LayerControls&);

struct LayerFrame final {
    float a{};
    float b{};
};

class Renderer final {
public:
    bool bind(const scheduler::Plan&, LayerGains) noexcept;
    bool accept(const scheduler::Fact&) noexcept;
    // Only directly after accepting CycleCompleted. The replacement must be the
    // same structural cycle compiled at another tempo.
    bool selectTempo(const scheduler::Plan&) noexcept;
    bool setGains(LayerGains) noexcept;
    bool sampleFrame(std::uint64_t, LayerFrame&) noexcept;
    void stop() noexcept;
    bool failed() const noexcept { return failed_; }
    bool stopped() const noexcept { return stopped_; }

private:
    bool fail() noexcept;
    const scheduler::Plan* plan_{};
    LayerGains gains_{};
    scheduler::FramePosition anchor_{};
    std::array<std::uint64_t, 2> starts_{};
    std::array<bool, 2> active_{};
    std::uint64_t nextFrame_{}, due_{}, cycle_{};
    std::size_t event_{};
    bool boundaryOpen_{}, failed_{}, stopped_{};
};

} // namespace fathom::polyrhythm
