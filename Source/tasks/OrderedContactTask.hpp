#pragma once
#include "tasks/OrderedContactFamily.hpp"
#include "tasks/ManualContactSourceHandle.hpp"
#include <cstdint>
#include <optional>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
#include <variant>

namespace fathom::tasks::ordered_contacts::manual {
// Choices and reports describe manual guidance. They are not measurements,
// clocks, sounding gates, assessment, admission, or credit.
enum class Rhythm { Unspecified, StraightEighth, StraightSixteenth, Triplet, Quintuplet, SixteenthTriplet, OneNotePerClick, SourceMetric };
enum class Branch { PrintedPassProgression, RestoredPulse, DisplacementVariation };
enum class Pass { ConnectedEqual, LandingAccent, SeparatedAccent, SeparatedEqual,
                  PausedEighthAccent, StoppedRelocation, ConnectedEighthAccent,
                  ConnectedEighthEqual, ConnectedSixteenth, SourceAccent, SourceEqual, SourcePerformance, SourceDisplacement };
enum class Claim { Unknown, No, Yes };
enum class Observation { Unknown, Clean, Error, RisingTension, NoisyGap,
                         LateLanding, Slide, Squeak, UnevenPulse, DraggedShiftNoise, CrossingAccent, GeometryError,
                         LostKeyCenter, WrongPosition, EarlyShift, PickReset };
enum class Pause { None, SeparateCell, StopAndRelocate, OneSubdivisionAtShift };
enum class ClockAuthority { ManualUntimed, SavedSelectedRelativeSlots };
enum class State { Setup, Traversal, Boundary, Release, Review, Finished, Cancelled, SourcePhase };
enum class Action { Begin, Contact, BoundaryReport, Release, LoopReport, OppositeStart, Repeat,
                    AdvancePass, Finish, Retry, Cancel, Restart, SessionReport,
                    ReduceTempo, PlanIncrease, ExtensionReport, SourcePracticeReport, SourceIssueReport,
                    SourcePhaseReport, SourceRepairReport };
enum class Extension { AlternatingModes, DistanceP5P8P11, DistanceP5P7P10, OtherPositionDistance };
struct Refusal final : std::invalid_argument { using std::invalid_argument::invalid_argument; };

struct SourceLine { int line; std::string text; };
struct PassOption {
    Pass pass;
    std::vector<Rhythm> rhythms;
    std::vector<int> sourceLines;
    bool needsReportedStableLandings{false};
};
enum class SourceDuty { ScaleComparison, EarNaming, FirstOctave, AscendingHalf, DescendingHalf, AdjacentModules,
    PausedCircuit, AccentedCircuit, EqualCircuit, GroupedSecure, LinkedModules, NeighboringRungs, FullRoute, ThreeCleanRoundTrips,
    SourceMapNaming, UnselectedSourceBranches, RootAccentThenRemove, ShortenedRouteRepair, NoisePressureThumbRepair,
    LostKeyRootRepair, WrongPositionNamingRepair, EarlyShiftAnchorRepair, ExactCountAirPickingRepair };
struct SourceDutyOption { SourceDuty duty; std::string label; std::vector<int> sourceLines; bool needsRelease; };
struct Policy {
    int level;
    std::string contextPath, contextSha256, sourceTextPath, sourceTextSha256;
    std::vector<SourceLine> sourceLines;
    std::vector<PassOption> passes;
    int previousLevel{0}, belowCleanMinimum{0}, belowCleanMaximum{0};
    bool slowerOfTwoPreviousModes{false}, oneModePerSession{false};
    bool downStartFirst{false}, rotationAcrossSessions{false}, restoreAfterStable{false};
    bool restoreAfterAdvancement{false};
    bool advancementNeedsTwoDays{false}, advancementNeedsBothModes{false};
    bool advancementNeedsBothStarts{false}, advancementNeedsBothRoutes{false};
    std::vector<Extension> extensions;
    manual_contacts::Family family{manual_contacts::Family::OrderedContact};
    std::vector<int> safeInstructionLines;
    std::vector<SourceDutyOption> sourceDuties;
    bool sourceTempoRule{true}, approximateThreeQuarters{false}, groupedBeforeDisplacement{false};
    bool minorGeometryRelease{false}, upperGeometryRebuild{false}, sourceGeometryObservation{false};
    std::vector<std::string> sourceInstructionBlocks;
};
const Policy& policy(int exactLevel);
const char* policyClosureSha256();
const char* physicalPolicyClosureSha256();
Policy physicalPolicy(const manual_contacts::SourceHandle&);
Policy piecewisePolicy(const manual_contacts::SourceHandle&);
Policy harmonicPolicy(const manual_contacts::SourceHandle&);

struct SetupReport {
    Branch branch;
    Rhythm rhythm;
    Start firstStart;
    Claim sourceSetupRead{Claim::Unknown};
    Claim onePrintedSetChosen{Claim::Unknown};
    Claim printedModeChosen{Claim::Unknown}; // Used only by the three two-mode levels.
    Claim stableLandings{Claim::Unknown};
    std::optional<int> chosenBpm{}, previousCleanBpm{}, otherPreviousModeCleanBpm{};
};
struct LoopReport {
    Observation observation{Observation::Unknown};
    Claim landingsStable{Claim::Unknown};
};
struct BoundaryReport {
    Claim pressureReleased{Claim::Unknown};
    Claim wholeFrameRelocated{Claim::Unknown};
    Claim sourcePauseOrSeparationReported{Claim::Unknown};
};
struct SessionReport {
    Claim priorPrintedPassesReported{Claim::Unknown};
    Claim fullPrintedSetClean{Claim::Unknown};
    Claim bothRoutesClean{Claim::Unknown};
    Claim bothStartsClean{Claim::Unknown};
    Claim bothModesClean{Claim::Unknown};
    std::vector<std::string> separateDayLabels; // Explicit learner reports, not dated observations.
    std::optional<Rhythm> nextSessionRhythm;
};
struct Cue {
    std::size_t ordinal;
    int stringLowToHigh, fret, finger;
    std::optional<int> midi;
    std::string spelling, pick, route, sourceRef;
    Pass pass;
    Rhythm rhythm;
    bool landingAccent;
    bool releaseAndRelocateBefore;
    Pause pauseBefore;
    ClockAuthority clockAuthority;
    std::optional<music::Span> activeSourceMetricSpan;
    // The source model's selected slots are never promoted to another pass.
    std::optional<music::Span> acousticSoundingSpan;
    bool rebuildAssignedFingeringBefore{false};
};
struct ExtensionGuidance {
    Extension extension;
    std::vector<int> positionFrames;
    std::vector<SourceLine> sourceLines;
    bool nativeAlternativeContactsSupplied{false};
    std::string limitation;
};
// Learner-facing descriptors contain source instructions and typed report
// choices. Hashes, packet refs, owner tokens and source custody stay in the
// separate trusted metadata/history APIs. A shared renderer needs no row logic.
enum class FieldId { Branch, Rhythm, FirstStart, SetupRead, OneSet, PrintedMode, StableLandings,
    ChosenBpm, PreviousCleanBpm, OtherModeCleanBpm, ContactReported, PressureReleased,
    FrameRelocated, PauseReported, HandReleaseReported, Observation, NextPass,
    PriorPrintedPasses, FullSetClean, BothRoutesClean, BothStartsClean, BothModesClean,
    SeparateDays, NextSessionRhythm, TempoDrop, AppliedReduction, PlannedIncrease,
    ExtensionChoice, MasteryReported, PositionOne, PositionTwo, PositionThree,
    SourceDutyChoice, SourcePracticeReported, SourceReleaseReported };
enum class FieldKind { Choice, PositiveInteger, DateList };
using ChoiceValue = std::variant<Claim, Rhythm, Branch, Start, Observation, Pass, Extension, SourceDuty, int>;
struct ChoiceDescriptor { ChoiceValue value; std::string label; };
struct FieldDescriptor {
    FieldId id;
    FieldKind kind;
    std::string label;
    bool required;
    std::vector<ChoiceDescriptor> choices;
    std::optional<int> minimum, maximum;
    std::optional<Extension> onlyForExtension;
};
struct ContactDescriptor {
    std::size_t ordinal;
    std::string stringLabel, pick, route;
    int fret;
    std::optional<int> finger;
    bool lightlyAccent;
    std::string timingInstruction;
    // New SourceContact atoms may be references, muted tokens or atomic
    // simultaneous groups. The legacy fret above is never their fallback.
    bool sourceAtomDescriptor{false};
    std::optional<int> sourcePhysicalFret{},sourceSoundingFret{},sourceReferenceFret{};
    std::string sourceAtomKind{};
    std::optional<bool> sourceAudible{},sourcePickAttack{};
    std::optional<int> sourceMidi{};
};
struct ActionDescriptor {
    Action action;
    std::string label;
    std::vector<std::string> instructions;
    std::vector<FieldDescriptor> fields;
    std::optional<ContactDescriptor> contact;
    std::optional<json::Value> typedReportSchema{};
};
struct HistoryEntry {
    std::uint64_t revision;
    Action action;
    std::string sourceKey, detail;
    std::size_t passIndex;
    Start start;
    std::optional<Observation> observation;
    std::string manualReportJson;
};
struct Coverage {
    bool chosenBranchRequiredPassesAndBothStartsReported{false};
    bool printedPassProgressionReported{false}, restoredPulseReported{false};
    bool externalAdvancementConditionsReported{false};
    bool allSourceGuidanceAvailable{true};
    bool wholeChildAccepted{false}, performanceObserved{false}, runtimeAdmitted{false};
    std::vector<std::string> remainingManualObligations;
};
struct View {
    State state;
    std::uint64_t revision;
    std::size_t passIndex, nextOrdinal;
    Branch branch;
    Rhythm rhythm;
    Start start;
    bool needsManualRelease, needsBoundaryReport, tempoReductionDue, oppositeStartReported;
    std::size_t reportedCleanLoops, reportedErrors;
    std::optional<int> reportedBpm;
    std::optional<int> plannedNextSessionBpm;
    Coverage coverage;
    std::size_t sourcePhaseIndex{0};
    bool sourcePhaseUnresolved{false};
    std::optional<std::string> sourceRepairDue{};
};

class Task;
// Opaque task/revision capability. Tokens cannot be manufactured by a caller.
class Token final {
public:
    Token(const Token&) = default;
private:
    Token(std::uint64_t owner, std::uint64_t revision, Action action)
        : owner_(owner), revision_(revision), action_(action) {}
    std::uint64_t owner_, revision_;
    Action action_;
    friend class Task;
};

class Task final {
public:
    explicit Task(const Definition&);
    explicit Task(const manual_contacts::SourceHandle&);
    Task(const Task&) = delete;
    Task& operator=(const Task&) = delete;
    Task(Task&&) = delete;
    Task& operator=(Task&&) = delete;
    const Definition& definition() const; // Legacy-only: physical handles are never coerced.
    const manual_contacts::SourceHandle& sourceHandle() const noexcept { return source_; }
    const char* sourceKey() const { return source_.sourceKey(); }
    const Policy& sourcePolicy() const noexcept { return policy_; }
    const std::vector<std::string>& sourceRoutes() const noexcept { return routes_; }
    const std::vector<std::string>& headingPath() const noexcept { return headings_; }
    const std::vector<HistoryEntry>& history() const noexcept { return history_; }
    std::string fullSourceGuidanceJson() const;
    // Read-only private continuation checks. No state setter or permission is
    // exposed. Caller must hold exclusive owner access during capture/replay.
    std::string continuationSourceSha256() const;
    std::string continuationStateSha256() const;
    void reportSourceIssue(const Token&, Observation);
    std::vector<ActionDescriptor> actionDescriptors() const;
    View view() const;
    Cue cue() const;
    harmonic_contacts::Cue harmonicCue() const;
    source_contacts::Cue sourceAtomCue() const;
    void reportSourcePhase(const Token&,const json::Value&);
    void reportHarmonicSourceIssue(const Token&,const std::string& exactRepairId,const json::Value& rawEvidence);
    void reportSourceRepair(const Token&,const json::Value&);
    ExtensionGuidance extensionGuidance(Extension) const;
    Token capture(Action) const;
    void begin(const Token&, const SetupReport&);
    void confirmContact(const Token&, std::size_t exactOrdinal, Claim manualAcknowledgment);
    void reportBoundary(const Token&, const BoundaryReport&);
    void release(const Token&, Claim completeHandReleaseReported);
    void reportLoop(const Token&, const LoopReport&);
    void oppositeStart(const Token&);
    void repeat(const Token&);
    void retry(const Token&);
    void advancePass(const Token&, Pass explicitPass, Rhythm explicitRhythm);
    void advanceSourceRoute(const Token&,std::size_t exactRoute,Start explicitlyChosenStart);
    void finish(const Token&);
    void cancel(const Token&);
    void restart(const Token&);
    // Host lifecycle fence: only inactive, fully released owners may leave.
    // Invalidates captured tokens without changing reports, history or debts.
    void deactivateForNavigation();
    void reportSession(const Token&, const SessionReport&);
    void reportSourcePractice(const Token&, SourceDuty, Claim performedReported, const BoundaryReport& sourceBoundary);
    void reduceTempo(const Token&, int explicitDropBpm, Claim appliedReported);
    void planIncreaseNextSession(const Token&, Claim plannedReported);
    void reportExtension(const Token&, Extension, Claim sourceMasteryReported);
    void reportDistanceExtension(const Token&, const std::vector<int>& threeAscendingFrames,
                                 Claim sourceMasteryReported);
private:
    const manual_contacts::SourceHandle source_;
    const std::optional<Definition> legacyDefinition_;
    const Policy policy_;
    const std::uint64_t owner_;
    State state_{State::Setup};
    std::uint64_t revision_{0};
    std::size_t passIndex_{0}, nextOrdinal_{1}, cleanLoops_{0}, errors_{0};
    Start firstStart_{Start::Down}, start_{Start::Down};
    Rhythm rhythm_{Rhythm::StraightSixteenth}; // Inactive until explicit Begin.
    Branch branch_{Branch::PrintedPassProgression};
    bool setupDone_{false}, cancelledRelease_{false}, stable_{false}, reductionDue_{false};
    bool sourceNoiseRepairDue_{false}, sourceNarrowingRepairDue_{false};
    std::optional<SourceDuty> sourceIssueRepairDue_{};
    bool firstReported_{false}, oppositeReported_{false};
    bool chosenSessionComplete_{false};
    bool baseProgressionReported_{false};
    bool pendingLoopReport_{false};
    bool initialTempoOffsetReported_{false};
    std::optional<int> bpm_, plannedBpm_;
    std::optional<int> reductionCeilingBpm_;
    std::optional<SessionReport> sessionReport_;
    std::vector<std::string> routes_, headings_;
    std::vector<HistoryEntry> history_;
    std::shared_ptr<const manual_contacts::Projection> selectedReference_;
    std::vector<SourceDuty> sourcePracticeReports_;
    json::Value harmonicProgram_;
    json::Value harmonicSourceAtoms_;
    json::Value harmonicSourceContracts_;
    std::size_t harmonicPhaseIndex_{0};
    bool harmonicPhaseUnresolved_{false},harmonicRepairClearsAfterRelease_{false};
    std::optional<std::string> harmonicRepairDue_{};
    std::optional<State> harmonicAfterRelease_{};
    std::map<std::string,json::Value> sourcePassReports_;
    std::vector<bool> sourceCompletedRoutes_;
    std::vector<source_contacts::Cue> sourceOwnedContacts_;
    json::Value sourceOwnedChoice_;
    bool sourceBendHeld_{false};
    std::optional<int> sourceExcitationGroup_,sourceLastEvent_;
    bool sourceTempoRepairDebt_{false};
    std::optional<int> sourceReportedBpm_,sourceRetainedTempoCeiling_;
    std::vector<ActionDescriptor> sourceContactActionDescriptors() const;
    std::size_t activeSourceContactCount() const;
    bool allRequiredSourceRoutesReported() const;
    State sourceStateAfterPhase() const;
    std::vector<ActionDescriptor> harmonicActionDescriptors() const;
    void harmonicNextPhaseState();
    void fence(const Token&, Action) const;
    void requireAllowed(Action) const;
    void record(Action, const std::string&, std::optional<Observation> = std::nullopt,
                const std::string& manualReportJson = {});
    void startTraversal();
    void sourceIssueDebt(Observation);
    void requireRhythm(const PassOption&, Rhythm) const;
    bool advancementReported() const;
};
} // namespace fathom::tasks::ordered_contacts::manual
