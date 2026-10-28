#pragma once
#include "tasks/RecipeTask.hpp"
#include <mutex>
#include <optional>
#include <string>
#include <vector>

namespace fathom::tasks::advanced {
enum class State { Setup, Ready, Hearing, Singing, ChooseArrangements, SilentSetup,
    Attack, AwaitRelease, Reveal, Reporting, Reported, NeedsRetry, Completed,
    Cancelled, ReopenRelease };
enum class Action { SetPlan, Begin, Heard, SungName, ChooseArrangements, CannotRespond,
    SetupTarget, Attack, Release, Reveal, Report, NextSet, Retry, Finish, Cancel,
    Navigate, Reopen };
Action transferAction(const std::string& exactActionName);

class Definition final {
public:
    Definition(const Definition&) = default;
    Definition& operator=(const Definition&) = default;
    const std::string& sourceKey() const noexcept { return key_; }
    const std::string& contractSha256() const noexcept { return contractSha_; }
    const std::string& sourceClosureSha256() const noexcept { return closureSha_; }
    const std::string& recipe() const noexcept { return recipe_; }
    const json::Value& exportedDefinition() const noexcept { return exported_; }
    const json::Value& retainedContract() const noexcept { return contract_; }
    // Full cached operational context is trusted source-player metadata too.
    const json::Value& retainedSourceContext() const noexcept { return context_; }
    // Trusted source-player metadata; never a learner view.
    const json::Value& sourcePlayerView() const noexcept { return player_; }
private:
    Definition(const char* row, const char* learner, const char* player);
    std::string key_, contractSha_, closureSha_, recipe_;
    json::Value exported_, contract_, initialLearner_, player_, context_;
    friend const Definition& definition(const std::string&);
    friend class AdvancedRecipeTask;
    friend class AdvancedRecipeWorkflow;
};
const Definition& definition(const std::string& exactSourceKey);
// Existing transfer-only key enumeration remains compatible; allKeys is closed56.
const std::vector<std::string>& keys();
const std::vector<std::string>& allKeys();
json::Value allowedChoices(const Definition&, std::optional<std::string> chosenPitch = std::nullopt);
void validatePlan(const json::Value&);
void validateArrangements(const json::Value&);
void validateSourcePlan(const json::Value&);
void validateWritten(const std::string& pass, const json::Value& response);
void validateFixedTopChoice(const Definition&, const json::Value&);
void validateFixedVoicing(const Definition&, const json::Value& top, const json::Value& plan);
std::vector<json::Value> voicings(const Definition&, const json::Value& topChoice,
    const std::string& harmony, const std::string& stage, std::size_t limit=16);

struct AdvancedToken final {
    recipes::Token owner;
    Action action{Action::SetPlan};
    State state{State::Setup};
    std::size_t stringSet{}, cycle{};
};
struct HistoryEvent final {
    AdvancedToken token;
    json::Value reported;
    State before{State::Setup}, after{State::Setup};
    bool performanceObserved{false}, grantsCredit{false};
};

// Exact14 source-bound manual owner. No audio/clock/tempo, native admission,
// persistence, Attempt or credit path. Every action requires a fresh token.
class AdvancedRecipeTask final {
public:
    static std::unique_ptr<AdvancedRecipeTask> restoreContinuation(const Definition&,const std::string&);
    explicit AdvancedRecipeTask(const Definition&);
    AdvancedRecipeTask(const AdvancedRecipeTask&) = delete;
    AdvancedRecipeTask& operator=(const AdvancedRecipeTask&) = delete;
    AdvancedRecipeTask(AdvancedRecipeTask&&) = delete;
    AdvancedRecipeTask& operator=(AdvancedRecipeTask&&) = delete;
    AdvancedToken capture(Action) const;
    void apply(const AdvancedToken&, const json::Value& payload);
    json::Value learnerView() const;
    json::Value sourcePlayerView() const;
    std::optional<std::string> priorityGuidance() const;
    std::vector<HistoryEvent> history() const;
    json::Value learnerActions() const;
    json::Value learnerInstructions() const;
    bool fenceInactiveForNavigation();
    std::string continuation() const; // private draft, never learner export

    const Definition& retainedDefinition() const noexcept { return definition_; }
private:
    Definition definition_;
    mutable std::mutex mutex_;
    struct Data {
        std::uint64_t pass{1}, revision{1};
        State state{State::Setup};
        std::size_t stage{}, cycle{};
        std::optional<State> resume;
        std::optional<json::Value> plan, arrangements, cueReport;
        json::Value namedPitch{nullptr};
        bool firstReported{}, currentRevealed{}, everRevealed{};
    } data_;
    json::Value continuationBody() const; // mutex held
    json::Value::Array journal_;
    std::uint64_t instance_;
    std::vector<HistoryEvent> history_;
    AdvancedToken captureImpl(Action) const;
    json::Value learnerViewImpl() const;
    static void clearInitial(Data&);
};

struct FamilyToken final {
    recipes::Token owner;
    std::string action, state;
    std::size_t writtenPass{}, bar{}, registerIndex{}, harmony{}, texture{};
    bool recovery{};
};
struct FamilyHistoryEvent final {
    FamilyToken token;
    json::Value reported;
    std::string before, after;
    bool performanceObserved{false}, grantsCredit{false};
};

// The two remaining source systems share ownership/report primitives but retain
// their exact distinct workflow states. This owner accepts only the closed42.
class AdvancedRecipeWorkflow final {
public:
    static std::unique_ptr<AdvancedRecipeWorkflow> restoreContinuation(const Definition&,const std::string&);
    explicit AdvancedRecipeWorkflow(const Definition&);
    AdvancedRecipeWorkflow(const AdvancedRecipeWorkflow&) = delete;
    AdvancedRecipeWorkflow& operator=(const AdvancedRecipeWorkflow&) = delete;
    AdvancedRecipeWorkflow(AdvancedRecipeWorkflow&&) = delete;
    AdvancedRecipeWorkflow& operator=(AdvancedRecipeWorkflow&&) = delete;
    FamilyToken capture(const std::string& action) const;
    void apply(const FamilyToken&, const json::Value& payload);
    json::Value learnerView() const;
    json::Value sourcePlayerView() const;
    json::Value currentTarget() const;
    json::Value snapshot() const;
    std::vector<FamilyHistoryEvent> history() const;
    json::Value learnerActions() const;
    json::Value learnerInstructions() const;
    bool fenceInactiveForNavigation();
    std::string continuation() const; // private draft, never learner export

    const Definition& retainedDefinition() const noexcept { return definition_; }
private:
    Definition definition_;
    mutable std::mutex mutex_;
    struct Data {
        std::uint64_t pass{1}, revision{1};
        std::string state{"setup"}, resume, retryTarget;
        std::size_t writtenPass{}, bar{}, registerIndex{}, harmony{}, texture{};
        bool revealed{}, hasPitchMatches{}, pitchMatches{}, recovery{},
            reductionRequired{}, restartAfterReduction{};
        json::Value sourcePlan{nullptr}, position{nullptr}, contacts{nullptr},
            firstContacts{nullptr}, responses{json::Value::Object{}},
            hearingReports{json::Value::Object{}}, scores{nullptr}, top{nullptr},
            plan{nullptr}, roleResponse{nullptr}, auditAnswers{nullptr},
            harmonies{json::Value::Array{}};
    } data_;
    json::Value continuationBody() const; // mutex held
    json::Value::Array journal_;
    std::uint64_t instance_;
    std::vector<FamilyHistoryEvent> history_;
    FamilyToken captureImpl(const std::string&) const;
    json::Value learnerViewImpl() const;
    json::Value currentFixed(const Data&) const;
    json::Value target(const Data&) const;
    void applyReconstruction(Data&, const std::string&, const json::Value&);
    void applyFixedTop(Data&, const std::string&, const json::Value&);
};
} // namespace fathom::tasks::advanced
