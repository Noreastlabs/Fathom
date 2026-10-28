#pragma once
#include "core/Quantity.hpp"
#include <cstddef>
#include <optional>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

namespace fathom::tasks {
struct Error final : std::runtime_error {
    std::string code;
    Error(std::string code, const std::string& detail);
};

// These are written source contacts for display, not sounding Tone/Model objects.
struct Contact final {
    int sourceString; // high e = 1, low E = 6
    int fret;
    int writtenStandardTuningMidi;
};
struct Action final {
    std::string label;
    std::vector<Contact> contacts;
    Rational authoredCueOnset;
};

class Definition final {
public:
    Definition(const Definition&) = default;
    Definition& operator=(const Definition&) = default;
    const std::string& sourceKey() const noexcept { return sourceKey_; }
    const std::string& label() const noexcept { return label_; }
    const std::string& policySha256() const noexcept { return policySha256_; }
    const std::string& provenanceJson() const noexcept { return provenanceJson_; }
    const std::vector<std::string>& setupInstructions() const noexcept { return setup_; }
    const std::vector<std::string>& retainedSourceContext() const noexcept { return context_; }
    const std::string& releaseInstruction() const noexcept { return release_; }
    const std::string& pacedChoiceExplanation() const noexcept { return pacedExplanation_; }
    const std::vector<Action>& actions() const noexcept { return actions_; }
    Rational cueEnd() const noexcept { return cueEnd_; }
    // No conversion to MusicModel, audio Program, Practice, Session or Attempt.
private:
    Definition(std::string sourceKey, std::string label, std::string policySha256,
               std::string provenanceJson, std::vector<std::string> setup,
               std::vector<std::string> context, std::string release,
               std::string pacedExplanation, std::vector<Action> actions,
               Rational cueEnd);
    std::string sourceKey_, label_, policySha256_, provenanceJson_;
    std::vector<std::string> setup_, context_;
    std::string release_, pacedExplanation_;
    std::vector<Action> actions_;
    Rational cueEnd_;
    friend const Definition& representativeDefinition(const std::string&);
};

// The only trusted definition in this private preparatory build. New source
// families require a reviewed generator/input closure, not caller-built JSON.
const Definition& representativeDefinition(const std::string& exactSourceKey);

enum class Mode { Unselected, SourceOrder, FathomEvenPulse };
enum class Phase { Choose, Setup, ManualSteps, Cues, Release, Closed };
enum class Outcome { None, UserReportedStepsFinished, Cancelled, RetryRequested, Interrupted };
enum class Response { Acknowledged, NeedsRetry, Stopped };

// Supplied by the actual host clock capability, never inferred from a source.
// The integration must supply its current range again at Ready.
struct TempoRange final { int minimumBpm; int maximumBpm; };

struct View final {
    Mode mode;
    Phase phase;
    Outcome outcome; // cue completion alone never reports performed steps
    std::optional<int> selectedBpm;
    std::optional<std::size_t> actionIndex;
    bool needsManualRelease;
    bool requiresSetup;
};

// In-memory UI state only. This object is not an activity/history record and
// deliberately has no save/import/profile, assessment or credit operation.
class Task final {
public:
    explicit Task(const Definition& definition);
    const Definition& definition() const noexcept { return definition_; }
    View view() const noexcept;
    void chooseSourceOrder();
    void chooseEvenPulse(int selectedBpm, TempoRange currentHostRange);
    template<class T, std::enable_if_t<!std::is_same_v<T, int>, int> = 0>
    void chooseEvenPulse(T, TempoRange) = delete;
    // Explicit source setup/Ready action. This acknowledges the instruction;
    // the software cannot observe fingers, muting, sound or physical release.
    void ready(TempoRange currentHostRange);
    // Source-order acknowledgments advance only one currently displayed action.
    void respond(Response response);
    // Supplied by the existing shared clock, in relative quarter coordinates.
    // Updates the current visual cue; it neither schedules nor emits sound.
    void followCuePosition(QuarterTime position);
    void cancel();
    void requestRetry();
    void acknowledgeRelease();
    void beginAnotherPass();
    void reopen();
private:
    Definition definition_; // own immutable copy; no borrowed lifetime hazard
    Mode mode_{Mode::Unselected};
    Phase phase_{Phase::Choose};
    Outcome outcome_{Outcome::None}, pendingOutcome_{Outcome::None};
    std::optional<int> bpm_;
    std::optional<std::size_t> action_;
    std::optional<Rational> lastCuePosition_;
    bool manuallyAcknowledgedAll_{false};
    void requireSelectable() const;
    void enterRelease(Outcome pending);
    static void validateTempo(int bpm, TempoRange range);
};
} // namespace fathom::tasks
