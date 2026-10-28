#pragma once
#include "platform/AudioOutputMac.hpp"
#include "metronome/Metronome.hpp"
#include "metronome/Polyrhythm.hpp"
#include <atomic>

namespace fathom::platform {
struct MetronomeProgress final {
    scheduler::Owner owner;
    std::uint64_t binding{}, sequence{}, scheduledThrough{}, clientAcceptedThrough{};
    std::uint64_t activeFrames{}, totalActiveFrames{}, completedCycles{}, cursorFrames{}, barFrames{};
    std::uint64_t requestedStopNs{}, uncertainThrough{}, physicalConfirmedThrough{};
    metronome::TempoState tempo;
    metronome::Phase phase{metronome::Phase::CountIn};
    bool hasPhysicalConfirmation{}, terminal{}, fault{}, partial{};
};
struct MetronomeSegment final {
    scheduler::Owner owner;
    std::uint64_t binding{}, from{}, through{};
    int tempo{};
    bool countIn{}; // successful client submission only; not physical presentation
};
struct MetronomeReply final { scheduler::Owner owner; std::uint64_t binding{}, sequence{}; int tempo{}; bool accepted{}; };
struct PolyrhythmLayerReply final { scheduler::Owner owner; std::uint64_t binding{}, sequence{}; polyrhythm::LayerGains gains; bool accepted{}; };

// One control producer and one audio/flush observer consumer. No transport, UUID,
// persistence or independent clock is created here. Keep alive through output flush.
class MetronomePlayback final {
public:
    MetronomePlayback();
    ~MetronomePlayback();
    bool prepare(const metronome::Settings&,const scheduler::Owner&,std::uint64_t binding,
                 std::string configurationBinding,std::uint32_t rate);
    // Requires the exact previously reclaimed Paused generation. Replays only its
    // incomplete whole bar, retains counters/tempo, and uses a fresh count-in.
    bool prepareResume(const scheduler::Owner& previous,const scheduler::Owner& next);
    bool manual(const scheduler::Owner&,std::uint64_t binding,std::uint64_t sequence,int bpm) noexcept;
    bool layerGains(const scheduler::Owner&,std::uint64_t binding,std::uint64_t sequence,
                    polyrhythm::LayerGains) noexcept;
    bool nextProgress(MetronomeProgress&) noexcept;
    bool nextFact(scheduler::Fact&) noexcept;
    bool nextSegment(MetronomeSegment&) noexcept; // also drains retired overflow fallback
    bool nextReply(MetronomeReply&) noexcept;
    bool nextLayerReply(PolyrhythmLayerReply&) noexcept;
    bool reclaim(MetronomeProgress&); // drain nextSegment first; refuses loss of accepted fallback
    static scheduler::BlockOutcome render(void*,const output::Owner&,std::uint32_t,std::uint32_t,Buses&) noexcept;
    static void observe(void*,const output::Snapshot&) noexcept;
private:
    struct Generation;
    struct History {scheduler::Owner owner;metronome::Settings settings;std::string key;std::uint32_t rate{};MetronomeProgress retained;bool reclaimed{};};
    enum SlotState { Free, Ready, Active, Retired };
    struct Slot {std::unique_ptr<Generation> value;std::atomic<int> state{Free};};
    bool install(const metronome::Settings&,const scheduler::Owner&,std::uint64_t,std::string,std::uint32_t,const History*);
    static bool collect(void*,const scheduler::Fact&) noexcept;
    static scheduler::BoundaryDecision boundary(void*,const scheduler::Fact&) noexcept;
    void update(const output::Snapshot&) noexcept;
    std::array<Slot,3> slots_;
    std::vector<History> history_; // control only; high water survives reclamation
    std::atomic<std::uint64_t> invalidatedThrough_{0};
    Generation* active_{};std::size_t activeSlot_{};
    scheduler::CommandQueue commands_;
    struct LayerCommand final {scheduler::Owner owner;std::uint64_t binding{},sequence{};polyrhythm::LayerGains gains;};
    scheduler::FixedQueue<LayerCommand,64> layerCommands_;
    scheduler::FixedQueue<MetronomeProgress,512> progress_;
    scheduler::FixedQueue<scheduler::Fact,4096> facts_;
    scheduler::FixedQueue<MetronomeSegment,2048> segments_;
    scheduler::FixedQueue<MetronomeReply,128> replies_;
    scheduler::FixedQueue<PolyrhythmLayerReply,128> layerReplies_;
    std::atomic<std::size_t> replyCapacity_{128}; // reserve before consuming/applying a command
    std::atomic<std::size_t> layerReplyCapacity_{128};
};
}
