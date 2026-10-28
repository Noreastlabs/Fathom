#pragma once
#include "core/Quantity.hpp"
#include "core/FramePosition.hpp"
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>
#include <type_traits>
#include <vector>

namespace fathom::scheduler {
constexpr std::size_t maxPlanEvents = 4096, maxCallbackEvents = 8192;
constexpr std::uint32_t maxCallbackFrames = 65536;
struct Owner final {
    std::array<std::uint8_t, 16> id{};
    std::uint64_t generation{}, epoch{};
    bool valid() const noexcept;
    bool operator==(const Owner&) const noexcept;
};
// Exact unsigned sample coordinate. Invalid/overflow returns false, never wraps.
struct FrameRatio final { std::uint64_t n{}, d{1}; };
bool add(FrameRatio, FrameRatio, FrameRatio&) noexcept;
bool multiply(FrameRatio, std::uint64_t, FrameRatio&) noexcept;
bool round(FrameRatio, std::uint64_t&) noexcept;
enum class BeatUnit { Eighth, Quarter, DottedQuarter, Half };
bool samples(const Rational& quarters, std::uint32_t rate, std::uint16_t bpm,
             BeatUnit, FrameRatio&) noexcept;
enum class Role : std::uint8_t { Reference, Metronome, LayerA, LayerB, CountIn };
enum class Action : std::uint8_t { Attack, Release, Silence };
struct EventSpec final {
    Rational at{};
    std::uint32_t sourceEvent{};
    Role role{Role::Reference};
    Action action{Action::Attack};
};
struct PlanSpec final {
    Owner owner;
    std::uint64_t binding{}; // monotonic process-local binding, not a record ID
    std::string sourceBinding; // control-owned canonical version/admission ledger key
    std::uint32_t sampleRate{44100};
    std::uint16_t bpm{60};
    BeatUnit unit{BeatUnit::Quarter};
    Rational cycle{4}, intro{};
    std::vector<EventSpec> events, countIn;
};
struct TimedEvent final {
    Rational structural{};
    FrameRatio offset;
    std::uint32_t sourceEvent{};
    Role role{};
    Action action{};
};
class Plan final {
public:
    Plan() = default;
    Plan(const Plan&) = default;
    Plan& operator=(const Plan&) = default;
    Plan(Plan&&) noexcept;
    Plan& operator=(Plan&&) noexcept;
    bool valid() const noexcept { return valid_; }
    const Owner& owner() const noexcept { return owner_; }
    std::uint64_t binding() const noexcept { return binding_; }
    const std::string& sourceBinding() const noexcept { return source_; }
    std::uint32_t sampleRate() const noexcept { return rate_; }
    FrameRatio duration() const noexcept { return duration_; }
    FrameRatio introDuration() const noexcept { return introDuration_; }
    const std::vector<TimedEvent>& events() const noexcept { return events_; }
    const std::vector<TimedEvent>& countIn() const noexcept { return countIn_; }
    bool compatibleTempo(const Plan&) const noexcept;
private:
    friend Plan compile(const PlanSpec&); // off callback; throws invalid/range errors
    bool valid_{};
    Owner owner_;
    std::uint64_t binding_{};
    std::string source_;
    std::uint32_t rate_{};
    BeatUnit unit_{BeatUnit::Quarter};
    Rational cycle_{};
    FrameRatio duration_, introDuration_;
    std::vector<TimedEvent> events_, countIn_;
};
Plan compile(const PlanSpec&);

// Single producer / single consumer: push and pop each have one owning thread.
// Release/acquire publishes whole slots; atomics do not serialize extra callers.
// A false push requires explicit overflow handling, never silent fact loss.
template<class T, std::size_t Capacity> class FixedQueue final {
    static_assert(Capacity > 0 && std::is_trivially_copyable_v<T>);
    static_assert(std::atomic<std::size_t>::is_always_lock_free);
public:
    bool push(const T& value) noexcept {
        const auto w = write_.load(std::memory_order_relaxed), next = (w + 1) % (Capacity + 1);
        if (next == read_.load(std::memory_order_acquire)) return false;
        values_[w] = value; write_.store(next, std::memory_order_release); return true;
    }
    bool pop(T& value) noexcept {
        const auto r = read_.load(std::memory_order_relaxed);
        if (r == write_.load(std::memory_order_acquire)) return false;
        value = values_[r]; read_.store((r + 1) % (Capacity + 1), std::memory_order_release); return true;
    }
private:
    std::array<T, Capacity + 1> values_{};
    alignas(64) std::atomic<std::size_t> read_{0}, write_{0};
};
// One immutable channel per owner binding. Publish/lifetime follows the plan lease.
class UrgentStop final {
    static_assert(std::atomic<bool>::is_always_lock_free);
public:
    UrgentStop(Owner owner, std::uint64_t binding) noexcept : owner_(owner), binding_(binding) {}
    bool request(const Owner&, std::uint64_t binding) noexcept;
    bool consume(const Owner&, std::uint64_t binding) noexcept;
private:
    const Owner owner_;
    const std::uint64_t binding_;
    std::atomic<bool> requested_{false};
};
struct PlanToken final { std::uint8_t slot{255}; std::uint64_t incarnation{}; };
// Single producer prepares/reclaims; single consumer acquires/retires. No implicit reclamation.
class PlanPool final {
public:
    bool prepare(Plan&&, PlanToken&); // producer only; moves allocation off callback
    const Plan* acquire(PlanToken) noexcept;
    bool retire(PlanToken) noexcept; // consumer: must no longer borrow the pointer
    bool reclaim(PlanToken); // producer only; destroys vectors off callback
private:
    enum State : std::uint64_t { Free, Ready, Active, Retired };
    struct Slot { Plan plan; std::atomic<std::uint64_t> word{0}; };
    static std::uint64_t word(PlanToken t, State s) noexcept { return t.incarnation * 4 + s; }
    std::array<Slot, 3> slots_;
    std::uint64_t next_{1};
};
enum class FactKind : std::uint8_t { Event, CycleCompleted, CountInEnded };
struct Fact final {
    FactKind kind{};
    Owner owner;
    std::uint64_t binding{}, frame{}, cycle{};
    std::uint32_t sourceEvent{};
    Role role{};
    Action action{};
};
using FactQueue = FixedQueue<Fact, 256>;
struct Command final { Owner owner; std::uint64_t binding{}, sequence{}, value{}; std::uint32_t kind{}; };
using CommandQueue = FixedQueue<Command, 64>;
using Sink = bool (*)(void*, const Fact&) noexcept;
enum class BoundaryAction { Continue, Stop, Tempo };
struct BoundaryDecision final { BoundaryAction action{BoundaryAction::Continue}; const Plan* tempo{}; };
using BoundaryReducer = BoundaryDecision (*)(void*, const Fact&) noexcept;
enum class State { Idle, CountIn, Running, Terminal };
enum class StopReason { Requested, InvalidFormat, FactOverflow, Arithmetic, WorkLimit, InvalidTempo, InvalidBlock, InvalidDecision };
struct Snapshot final {
    State state{State::Idle};
    Owner owner;
    std::uint64_t binding{}, processedThrough{}, completedCycles{}, confirmedThrough{}, uncertainThrough{};
    bool hasConfirmation{}, boundaryFactPending{};
    StopReason reason{StopReason::Requested};
};
class Cursor final {
public:
    // All methods single callback owner. Never expose this object directly to UI.
    bool start(const Plan&, const Owner&, std::uint64_t binding) noexcept;
    bool process(std::uint32_t frames, const Owner& observed, Sink, void*,
                 BoundaryReducer = nullptr, void* reducerContext = nullptr,
                 UrgentStop* = nullptr) noexcept;
    bool stop(const Owner&, std::uint64_t binding) noexcept;
    bool confirm(const Owner&, std::uint64_t through) noexcept;
    bool acknowledge(const Owner&, std::uint64_t binding) noexcept;
    Snapshot snapshot() const noexcept { return status_; }
private:
    bool fail(StopReason, std::uint64_t uncertain) noexcept;
    void retainEndpointCompletion() noexcept;
    const Plan* plan_{};
    Snapshot status_;
    FramePosition anchor_{};
    std::size_t event_{};
    bool consumedBoundary_{};
};
} // namespace fathom::scheduler
