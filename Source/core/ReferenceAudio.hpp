#pragma once
#include "core/MusicModel.hpp"
#include "core/GuitarSetup.hpp"
#include "core/Scheduler.hpp"
#include <array>
#include <memory>

namespace fathom::reference {
enum class Method { Pluck, Sine };
struct Configuration {
    scheduler::Owner owner;
    std::uint64_t binding{};
    std::string sourceBinding;
    std::uint32_t rate{44100};
    std::uint16_t bpm{120};
    scheduler::BeatUnit unit{scheduler::BeatUnit::Quarter};
    Rational cycle{4}, intro{};
    Method method{Method::Pluck};
};
struct BendSampleKnot { std::uint64_t frame{}; double hz{}; };
struct PitchSegment {
    std::string sourceEvent;
    music::Attack attack{music::Attack::Picked};
    int midi{};
    double hz{};
    Rational onset{}, end{};
    scheduler::FrameRatio onsetFrames{}, endFrames{};
    std::vector<BendSampleKnot> bendKnots;
};
struct Voice {
    int string{}, midi{};
    double hz{};
    Rational onset{}, end{};
    scheduler::FrameRatio startFrames{}, endFrames{};
    std::vector<std::string> sourceEvents; // every original member, including nonpicked arrivals
    std::vector<PitchSegment> segments; // one excitation, ordered same-string pitch spans
    bool hasSlide{}; // compile-time flag; render callback performs no segment scan
};
struct Silence { std::string event; std::vector<int> strings; };
struct MutedVoice { std::string event; int string{}; Rational onset{}, end{}; scheduler::FrameRatio endFrames{}; };
struct BackingVoice {
    int midi{}, levelMilli{};
    double hz{};
    Rational onset{}, end{};
    scheduler::FrameRatio startFrames{}, endFrames{};
};
class Program final {
public:
    const scheduler::Plan& schedule() const noexcept { return schedule_; }
    const music::ValidatedModel& source() const noexcept { return *source_; }
    const std::vector<Voice>& voices() const noexcept { return voices_; }
    const std::vector<Silence>& silences() const noexcept { return silences_; }
    const std::vector<MutedVoice>& mutedVoices() const noexcept { return muted_; }
    const std::vector<BackingVoice>& backingVoices() const noexcept { return backing_; }
    Method method() const noexcept { return method_; }
    bool compatibleTempo(const Program&) const noexcept;
    // Deliberately no catalog/admission token: a Program is a technical projection.
private:
    friend Program compile(std::shared_ptr<const music::ValidatedModel>, const Configuration&);
    std::shared_ptr<const music::ValidatedModel> source_;
    scheduler::Plan schedule_;
    std::vector<Voice> voices_;
    std::vector<Silence> silences_;
    std::vector<MutedVoice> muted_;
    std::vector<BackingVoice> backing_;
    Method method_{};
};
// Control thread only; explicit validation/refusal exceptions, no partial publication.
Program compile(std::shared_ptr<const music::ValidatedModel>, const Configuration&);
enum class ToneTarget { OpenString, CapoPosition };
Program tuningTone(const guitar::Setup&, int internalString, ToneTarget,
                   const scheduler::Owner&, std::uint64_t binding, std::uint32_t rate,
                   Method = Method::Sine);
double frequency(int midi); // validated MIDI0..127; throws otherwise
// Accepted6.1 formula; no gate extension, cache or output gain hidden here.
double sample(Method, double hz, std::uint64_t age, std::uint64_t length, std::uint32_t rate) noexcept;

class Renderer final {
public:
    // Exactly once; caller retains immutable Program(s) through callback quiescence.
    bool bind(const Program&) noexcept;
    // Deliver all authoritative facts at nextFrame BEFORE sampleFrame(nextFrame).
    // Other buses remain caller-owned; this Program's schedule contains reference only.
    bool accept(const scheduler::Fact&) noexcept;
    // Only directly after accepted CycleCompleted, before next events/samples.
    bool selectTempo(const Program&) noexcept;
    bool sampleFrame(std::uint64_t absoluteFrame, float& mono) noexcept;
    void stop() noexcept; // immediate silence; cannot resume/rebind an interrupted owner
    bool failed() const noexcept { return failed_; }
    bool stopped() const noexcept { return stopped_; }
    std::uint64_t nextFrame() const noexcept { return nextFrame_; }
    scheduler::FramePosition anchor() const noexcept { return anchor_; }
private:
    struct Active {
        const Voice* voice{};
        std::uint64_t start{}, end{};
        std::uint32_t id{};
        std::size_t segment{};
        std::uint64_t segmentEnd{};
        double phase{};
        std::size_t bendIndex{};
    };
    bool fail() noexcept;
    bool refreshDue() noexcept;
    bool at(scheduler::FrameRatio offset, std::uint64_t&) const noexcept;
    const Program* program_{};
    std::array<Active,6> active_{};
    struct ActiveMute { const MutedVoice* voice{}; std::uint64_t start{}, end{}; std::uint32_t id{}; };
    std::array<ActiveMute,6> mutedActive_{};
    struct ActiveBacking { const BackingVoice* voice{}; std::uint64_t start{}, end{}; std::uint32_t id{}; };
    ActiveBacking backingActive_{};
    scheduler::FramePosition anchor_{};
    std::uint64_t nextFrame_{}, cycle_{}, due_{};
    std::size_t event_{};
    bool intro_{}, boundaryOpen_{}, failed_{}, stopped_{};
};
}
