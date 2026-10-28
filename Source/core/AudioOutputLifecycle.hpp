#pragma once
#include "core/Scheduler.hpp"
#include <array>
#include <cstdint>

namespace fathom::output {
using Owner = scheduler::Owner;
constexpr std::uint32_t maxOutputFrames = 8192;
struct Format final {
    std::uint32_t rate{}, frames{};
    bool valid() const noexcept;
    bool operator==(Format b) const noexcept { return rate == b.rate && frames == b.frames; }
};
// Monotonic nanoseconds are provenance, never musical time or DAC presentation.
struct Request final { std::uint64_t epoch{}, stampNs{}; Format format; std::uint32_t selectedPhysical{}; };
struct CachedAnnouncement final { std::uint64_t epoch{}, stampNs{}; Format format; };
struct Observation final {
    std::uint64_t epoch{}, callbackSequence{}, callbackStampNs{}, queryStampNs{};
    Format queriedIO;
    std::uint32_t callbackFrames{}, nativeIOObject{}, queriedIOObject{};
    std::uint32_t physicalObject{}, physicalRate{}, physicalFrames{};
    bool physicalKnown{}, ioKnown{}, routeKnown{}, selectedInFullRoute{}, selectedInActiveRoute{};
};
enum class State { Closed, Awaiting, Observed, Ready, Running, Paused, Unresolved, Fault };
enum class Fault { None, FormatMismatch, Restart, DeviceLost, Sleep, Clock, QueueOverflow, Backend, Render, InvalidObservation };
struct Snapshot final {
    State state{State::Closed};
    Request request;
    CachedAnnouncement cached;
    Observation observation;
    Owner owner;
    std::uint64_t observationToken{}, submittedFrames{}, confirmedFrames{}, uncertainThrough{}, requestedStopNs{}, firstSilenceNs{};
    std::uint32_t announcements{};
    bool ownsOutcome{}, hasConfirmation{}, pendingOutcome{}, stopRequested{};
    Fault fault{Fault::None};
};
// One callback writer after construction. Control/UI communicate through bounded ports.
class Lifecycle final {
public:
    bool configure(Request) noexcept;
    bool announce(CachedAnnouncement) noexcept;
    bool observe(Observation) noexcept;
    bool acknowledge(std::uint64_t epoch, std::uint64_t observationToken) noexcept;
    bool start(const Owner&) noexcept;
    bool pause(const Owner&, std::uint64_t requestedNs, std::uint64_t uncertainThrough) noexcept;
    // Caller retains the paused snapshot through its bounded fact port before acknowledging.
    bool acknowledgePause(const Owner&) noexcept;
    bool resume(const Owner& previous, const Owner& next) noexcept;
    bool stop(const Owner&, std::uint64_t requestedNs, std::uint64_t uncertainThrough) noexcept;
    bool invalidate(std::uint64_t epoch, Fault, std::uint64_t requestedNs, std::uint64_t uncertainThrough) noexcept;
    bool invalidateOwner(const Owner&, Fault, std::uint64_t requestedNs, std::uint64_t uncertainThrough) noexcept;
    bool submitted(const Owner&, std::uint64_t callbackSequence, std::uint32_t frames) noexcept;
    bool confirm(const Owner&, std::uint64_t through) noexcept;
    // Coordinator must have reconciled original identity+immutable outcome before this port.
    // Releasing audio ownership is separate from stopping output: persistence
    // reconciliation must complete before another activity can claim the port.
    bool resolveOutcome(const Owner&) noexcept;
    bool close() noexcept;
    bool renderAllowed() const noexcept { return s_.state == State::Running; }
    Snapshot snapshot() const noexcept { return s_; }
private:
    bool matches(const Owner& o) const noexcept { return s_.ownsOutcome && s_.owner == o; }
    bool current(std::uint64_t epoch) const noexcept { return s_.state != State::Closed && epoch == s_.request.epoch; }
    void retainStop(std::uint64_t stamp, std::uint64_t uncertain) noexcept;
    Snapshot s_;
    std::uint64_t lastEpoch_{}, lastSubmittedSequence_{};
    bool pauseRetained_{};
};
struct MixSettings final {
    std::array<int,4> bus{50,50,50,50};
    int master{50};
    bool masterMute{};
    std::uint8_t muteMask{}, soloAB{}; // bits reference/metronome/A/B; solo bits A/B
    bool valid() const noexcept;
};
class Mixer final {
public:
    bool apply(MixSettings) noexcept;
    MixSettings settings() const noexcept { return settings_; }
    std::array<float,4> gains() const noexcept;
    bool sample(const std::array<float,4>& buses, float& result) const noexcept;
private:
    MixSettings settings_;
};
const char* stateText(State) noexcept;
const char* faultText(Fault) noexcept;
} // namespace fathom::output
