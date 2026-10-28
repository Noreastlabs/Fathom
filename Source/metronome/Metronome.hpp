#pragma once
#include "core/Scheduler.hpp"
#include <optional>

namespace fathom::metronome {
enum class Style { Accent, Normal, Silent };
enum class CountIn { ConfiguredBar, AuthoredBar, Off };
enum class Reference { A, B, Cycle };
struct Ramp { bool up{true}; int step{1}, every{1}, target{120}; };
struct Settings {
    int tempo{60}, numerator{4}, denominator{4}, subdivision{1};
    scheduler::BeatUnit unit{scheduler::BeatUnit::Quarter};
    std::vector<Style> styles{Style::Accent,Style::Normal,Style::Normal,Style::Normal};
    bool metronomeEnabled{true}, polyrhythmEnabled{}, masterMute{};
    int x{3}, y{2}, masterVolume{50};
    Reference reference{Reference::B};
    CountIn countIn{CountIn::ConfiguredBar};
    std::optional<Ramp> ramp;
    // Reference, metronome, A, B: accepted four-bus ordering.
    std::array<int,4> volumes{50,50,50,50};
    std::array<bool,2> mute{}, solo{};
};
void validate(const Settings&); // control thread; actionable refusal, never clamps
Rational barSpan(const Settings&);
const std::array<std::pair<int,int>,8>& commonMeters() noexcept;
const char* beatUnitLabel(scheduler::BeatUnit) noexcept;
struct Cue { Rational at; std::uint32_t id{}; Style style{Style::Normal}; int beat{}, part{}; };
std::vector<Cue> events(const Settings&); // half-open bar; silent beat has no events

// Immutable control-built schedule bank, borrowed until callback quiescence.
// All musical time is still owned by the accepted scheduler::Cursor.
class PlanBank final {
public:
    PlanBank(const Settings&,const scheduler::Owner&,std::uint64_t binding,
             std::string configurationBinding,std::uint32_t rate);
    const scheduler::Plan& initial() const noexcept { return initial_; }
    const scheduler::Plan* tempo(int bpm) const noexcept;
    const std::vector<Cue>& cues() const noexcept { return cues_; }
    const std::vector<Cue>& countInCues() const noexcept { return countIn_; }
    std::size_t retainedEventCount() const noexcept;
private:
    scheduler::Plan initial_;
    std::array<scheduler::Plan,281> tempos_;
    std::vector<Cue> cues_,countIn_;
};

enum class TapStatus { Rejected, Insufficient, Unstable, Candidate };
struct TapResult { TapStatus status{TapStatus::Insufficient}; int bpm{}; };
// A Candidate is a gesture estimate, not a tempo command. The current activity
// owner must explicitly submit/apply it through its normal tempo policy.
class Tap final {
public:
    // Monotonic command sequence is process-local, not a persisted record identity.
    // Nanoseconds are input gesture time only, never the musical clock.
    TapResult add(std::uint64_t sequence,std::uint64_t monotonicNs) noexcept;
    void reset() noexcept { count_=0; } // retains sequence/time high water marks
    std::size_t retained() const noexcept { return count_; }
private:
    std::array<std::uint64_t,6> points_{};
    std::size_t count_{};
    std::uint64_t sequence_{},lastNs_{};
};

// Small callback-owned policy, not a second transport or result owner. Caller
// supplies authoritative phase, confirmed complete bar and simultaneous intent.
enum class Phase { CountIn, Running, Paused, Terminal };
enum class Intent { Continue, Pause, Stop, Context, Error };
struct TempoState {
    int tempo{60}; std::optional<Ramp> ramp; int count{};
    std::uint64_t completedThrough{}, lastCommand{};
    std::optional<int> pendingManual;
    bool resumable{}; // set only by an accepted Pause disposition
};
struct Decision { bool accepted{}, nextAttack{}; int tempo{}; Intent intent{Intent::Continue}; };
class TempoPolicy final {
public:
    TempoPolicy(const scheduler::Owner&,std::uint64_t binding,const Settings&);
    // Only a genuine same-original resume uses this handoff. The practice owner
    // supplies the new generation; no automatic restart or identity allocation.
    TempoPolicy(const scheduler::Owner& previous,const scheduler::Owner& resumed,
                std::uint64_t binding,TempoState handoff);
    bool manual(const scheduler::Owner&,std::uint64_t binding,std::uint64_t command,
                int bpm,Phase) noexcept;
    Decision boundary(const scheduler::Owner&,std::uint64_t binding,
                      std::uint64_t logicalBar,bool confirmed,bool complete,
                      Intent) noexcept;
    TempoState handoff() const noexcept { return state_; }
    bool halted() const noexcept { return halted_; }
private:
    scheduler::Owner owner_;
    std::uint64_t binding_{};
    TempoState state_;
    bool halted_{};
};
}
