#pragma once
#include "core/Scheduler.hpp"
#include "core/PracticeTimeline.hpp"
#include <optional>
#include <string>
#include <vector>

namespace fathom::practice {
enum class Kind { Attempt, Freeplay };
enum class State { Stopped, CountIn, Running, Paused, Ended, Error };
enum class CountIn { AuthoredBar, Off };
struct Configuration final {
    Rational span{4};
    CountIn countIn{CountIn::AuthoredBar};
    std::optional<std::pair<int,int>> meter;
    bool sourceRequiresCountIn{}, faithfulWholeSpan{};
    std::uint32_t rate{44100};
    std::uint16_t bpm{120};
    scheduler::BeatUnit unit{scheduler::BeatUnit::Quarter};
    std::uint64_t targetCycles{2};
};
Rational countInSpan(const Configuration&); // throws actionable configuration errors
struct Progress final {
    scheduler::Owner owner;
    std::uint64_t sequence{}, clientAcceptedThrough{}, scheduledThrough{}, activeFrames{}, completedCycles{}, cursorFrames{},
        requestedStopNs{}, uncertainThrough{}, physicalConfirmedThrough{}, dispositionSequence{};
    State state{State::Stopped};
    bool hasPhysicalConfirmation{}, terminal{}, partial{}, fault{};
};
// Serialized control executor only. Callback Progress supplies all time/cycle facts.
// Original allocated ID and pinned canonical/context bytes come from the owning
// content/storage ports; this class invents neither a record nor a curriculum ID.
class Coordinator final {
public:
    void begin(scheduler::Owner,Kind,std::string pinnedContext,Configuration);
    bool command(std::uint64_t sequence,const scheduler::Owner&); // shared dedup for UI intents
    scheduler::Owner nextResumeOwner() const;
    bool stoppedAcknowledged(const scheduler::Owner&,State,std::uint64_t requestedNs); // explicit adapter/definite-submission-refusal port; adds no time
    scheduler::Owner resume(); // explicitly called only after retained Paused progress
    bool progress(const Progress&); // current or retained original generation; no wall clock
    bool progress(const Progress&,const Timeline& acceptedTimeline);
    const Timeline& timeline(const scheduler::Owner&) const;
    // Borrow only until the next control mutation. Null preserves legacy raw audit.
    const Timeline* lateTimeline(const Progress&) const noexcept;
    std::uint16_t currentTempo() const;
    std::string originalKey() const; // canonical UUID string of the allocated owner
    void seal(std::string originalKey,std::string immutablePayload);
    enum class Save { Unknown, Absent, Matching, Conflict };
    bool reconcile(const std::string& originalKey,const std::string& payload,Save);
    State state() const noexcept { return state_; }
    const scheduler::Owner& owner() const noexcept { return owner_; }
    const Configuration& configuration() const noexcept { return config_; }
    const std::string& context() const noexcept { return context_; }
    Kind kind() const noexcept { return kind_; }
    std::uint64_t activeFrames() const;
    std::uint64_t completedCycles() const;
    const std::vector<Progress>& generations() const noexcept { return generations_; }
    const std::vector<Progress>& lateEvidence() const noexcept { return late_; }
    bool pending() const noexcept { return state_!=State::Stopped; }
    bool sealed() const noexcept { return !key_.empty(); }
private:
    scheduler::Owner owner_;
    Configuration config_;
    Kind kind_{Kind::Attempt};
    State state_{State::Stopped};
    std::string context_,key_,payload_;
    std::uint64_t lastCommand_{},dispositionSequence_{};
    std::vector<Progress> generations_,retained_,late_;
    std::vector<Timeline> timelines_,retainedTimelines_;
    struct MappedLate { Progress fact; Timeline map; };
    std::vector<MappedLate> mappedLate_;
    void retainLate(const Progress&,const Progress& acceptedBase,const Timeline* supplied);
    bool progressChecked(const Progress&,const Timeline*);
};
const char* stateText(State) noexcept;
}
