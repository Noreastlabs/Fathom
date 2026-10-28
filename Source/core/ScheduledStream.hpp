#pragma once
#include "core/Scheduler.hpp"
#include "core/AudioOutputLifecycle.hpp"

namespace fathom::scheduler {
struct BlockOutcome final { bool valid{}; std::uint32_t submittedFrames{}; bool terminal{}; };
// The consumer renders only this prefix, using these exact absolute-frame facts.
// The caller has zeroed the complete output block. No allocation/locks/I/O here.
using BlockConsumer = bool (*)(void*, std::uint64_t begin, std::uint32_t prefix,
                              const Fact*, std::size_t) noexcept;
struct StreamView final {
    Snapshot cursor;
    std::uint64_t block{}, blockBegin{}, displayDrops{}, acceptedCommands{}, rejectedCommands{};
    std::uint32_t prefix{}, tempoIndex{};
    std::uint64_t phaseOrigin{};
    FrameRatio phaseSpan;
    bool failed{};
};
struct TempoCommand final { Owner owner; std::uint64_t binding{}, sequence{}; std::uint32_t index{}; };
class ScheduledStream final {
public:
    // Exactly once, off callback. Configuration and plan pointers live through disconnect.
    // Plan[0] includes count-in; all others must be compatible, intro-free tempo variants.
    void prepare(std::vector<Plan>, std::uint64_t stopAfterCycles = 0,
                 std::uint32_t rampEveryCycles = 0, std::uint32_t rampIndex = 0);
    bool tempo(TempoCommand) noexcept; // single control producer; false is explicit refusal
    BlockOutcome process(const Owner&, std::uint32_t rate, std::uint32_t frames,
                         BlockConsumer, void*) noexcept;
    // Only audio callback, or control thread AFTER the output callback has been flushed.
    void observe(const output::Snapshot&) noexcept;
    bool nextView(StreamView&) noexcept; // single control consumer
    bool nextFact(Fact&) noexcept;
    StreamView quiescentView() const noexcept { return view_; } // only after flush
private:
    static bool collect(void*, const Fact&) noexcept;
    static BoundaryDecision boundary(void*, const Fact&) noexcept;
    void publish() noexcept;
    std::vector<Plan> plans_;
    Cursor cursor_;
    std::atomic<bool> prepared_{false};
    std::uint64_t stopAfter_{}, lastSequence_{};
    std::uint32_t rampEvery_{}, rampIndex_{}, tempoIndex_{};
    bool rampArmed_{}, manualPending_{}, failed_{};
    std::uint32_t pendingIndex_{};
    std::array<Fact,maxCallbackEvents> blockFacts_{};
    std::size_t count_{};
    FixedQueue<TempoCommand,32> commands_;
    FixedQueue<Fact,4096> facts_;
    FixedQueue<StreamView,512> views_;
    StreamView view_;
};
}
