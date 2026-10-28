#pragma once
#include "core/PracticeTransport.hpp"
#include "core/ReferenceAudio.hpp"
#include "platform/AudioOutputMac.hpp"
#include "metronome/Metronome.hpp"
#include <atomic>

namespace fathom::lesson { class Admission; }

namespace fathom::platform {
struct PracticeTempoPoint final { std::uint64_t cycle{}; std::uint16_t bpm{}; };
// A complete callback snapshot, not independent progress/map queue fragments.
struct PracticeTempoEvidence final {
    practice::Progress progress;
    std::uint64_t binding{},reportedSubmittedThrough{}; // raw adapter report; not automatically accepted credit
    std::array<PracticeTempoPoint,32> points{};
    std::uint32_t pointCount{};
    metronome::TempoState tempo;
};
struct PracticeTempoReply final {
    scheduler::Owner owner;std::uint64_t binding{},sequence{};int bpm{};bool accepted{};
};
struct PracticeTempoPreparation final {
    std::size_t programs{},plans{},voices{},events{},generationBytes{};
};
// A three-slot immutable-generation handoff. UI/service prepares and reclaims;
// callback is the only writer of active renderer/cursor/progress. All slots and
// this context must outlive disconnect/shutdown's callback flush.
class PracticePlayback final {
public:
    PracticePlayback();
    ~PracticePlayback();
    bool prepare(std::shared_ptr<const music::ValidatedModel>,const reference::Configuration&,
                 const practice::Configuration&,std::uint64_t remainingCycles);
    bool prepareLesson(const lesson::Admission&,const reference::Configuration&,
                       const practice::Coordinator& original,std::uint64_t remainingCycles);
    bool prepareLessonTempo(const lesson::Admission&,const reference::Configuration&,
                            const practice::Coordinator& original,std::uint64_t remainingCycles);
    // Explicit synthetic technical entry, never a curriculum admission bypass.
    bool prepareTempo(std::shared_ptr<const music::ValidatedModel>,const reference::Configuration&,
                      const practice::Configuration&,std::uint64_t remainingCycles,
                      std::optional<metronome::Ramp> initialRamp={});
    bool manualTempo(const scheduler::Owner&,std::uint64_t binding,std::uint64_t sequence,int bpm) noexcept;
    bool nextTempoReply(PracticeTempoReply&) noexcept;
    bool nextTempoEvidence(PracticeTempoEvidence&) noexcept;
    bool reclaimTempoEvidence(PracticeTempoEvidence&);
    // Control-only: validates this provider's original binding before map/credit.
    bool applyTempoEvidence(const PracticeTempoEvidence&,practice::Coordinator&) const;
    PracticeTempoPreparation tempoPreparation() const noexcept { return preparation_; }
    bool nextProgress(practice::Progress&);
    bool nextFact(scheduler::Fact&);
    // Retired terminal facts are always retained even if the progress queue filled.
    // Drain nextProgress first; caller preserves returned original-owner facts.
    bool reclaim(practice::Progress&);
    static scheduler::BlockOutcome render(void*,const output::Owner&,std::uint32_t,std::uint32_t,Buses&) noexcept;
    static void observe(void*,const output::Snapshot&) noexcept;
private:
    bool prepareChecked(std::shared_ptr<const music::ValidatedModel>,const reference::Configuration&,
                        const practice::Configuration&,std::uint64_t remainingCycles,bool beatClick=false,
                        bool dynamic=false,std::optional<metronome::Ramp> initialRamp={},std::string pinnedContext={});
    struct Generation;
    enum SlotState { Free, Ready, Active, Retired };
    struct Slot { std::unique_ptr<Generation> value; std::atomic<int> state{Free}; };
    std::array<Slot,3> slots_;
    std::vector<scheduler::Owner> preparedOwners_; // control-only high-water marks, survive slot reclaim
    struct TempoHistory {
        scheduler::Owner owner;std::uint64_t binding{};std::string sourceBinding;
        practice::TimelineSpec spec;reference::Method method{};std::shared_ptr<const music::ValidatedModel> model;
        practice::Configuration configuration;bool beatClick{};
        std::optional<metronome::Ramp> initialRamp;std::string pinnedContext;
        PracticeTempoEvidence retained;bool reclaimed{};
    };
    std::vector<TempoHistory> tempoHistory_; // control only; original generation bases survive reclaim
    PracticeTempoPreparation preparation_;
    std::atomic<std::uint64_t> invalidatedThrough_{0};
    Generation* active_{};
    std::size_t activeSlot_{};
    scheduler::FixedQueue<practice::Progress,512> progress_;
    scheduler::FixedQueue<PracticeTempoEvidence,512> tempoProgress_;
    scheduler::CommandQueue tempoCommands_;
    scheduler::FixedQueue<PracticeTempoReply,128> tempoReplies_;
    std::atomic<std::size_t> replyCapacity_{128};
    scheduler::FixedQueue<scheduler::Fact,4096> facts_;
    static bool collect(void*,const scheduler::Fact&) noexcept;
    static scheduler::BoundaryDecision boundary(void*,const scheduler::Fact&) noexcept;
    void update(const output::Snapshot&) noexcept;
    void updateTempo(const output::Snapshot&) noexcept;
};
}
