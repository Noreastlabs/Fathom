#pragma once
#include "content/StrictJson.hpp"
#include <cstdint>
#include <mutex>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace fathom::tasks::recipes {
struct Error final : std::runtime_error {
    std::string code;
    explicit Error(std::string code);
};
enum class Recipe { CallAnswer, RecoveryPair };
enum class Phase { Select, Steps, Release, Closed };
enum class Outcome { None, UserReportedStepsFinished, RetryRequested, Cancelled };
enum class Intent { Choose, Report, Retry, Stop, Navigate, Release, Again, Reopen };

// The factory owns the generated/version-bound family. Caller-built definitions
// have no public constructor and cannot widen its17 exact source keys.
class Definition final {
public:
    Definition(const Definition&) = default;
    Definition& operator=(const Definition&) = default;
    const std::string& sourceKey() const noexcept { return sourceKey_; }
    const std::string& sourceIdentity() const noexcept { return sourceIdentity_; }
    const std::string& contractSha256() const noexcept { return contractSha256_; }
    const std::string& sourceClosureSha256() const noexcept { return closureSha256_; }
    Recipe recipe() const noexcept { return recipe_; }
    const json::Value& retainedContract() const noexcept { return contract_; }
    const json::Value& exportedDefinition() const noexcept { return exported_; }
    const std::vector<json::Value>& reports() const noexcept { return reports_; }
    const json::Value& reportBindings() const noexcept { return reportBindings_; }
    const json::Value& retainedSourceContext() const noexcept { return context_; }
private:
    Definition(const char* row, const char* reports, const char* bindings, const char* closure);
    std::string sourceKey_, sourceIdentity_, contractSha256_, closureSha256_;
    Recipe recipe_;
    json::Value contract_, exported_, reportBindings_, context_;
    std::vector<json::Value> reports_;
    friend const Definition& definition(const std::string& exactSourceKey);
};
const Definition& definition(const std::string& exactSourceKey);
const std::vector<std::string>& keys();

// Source menu/nearest policy is the frozen provisional MIDI-distance policy.
// These checks do not certify physical security or author printed positions.
json::Value allowedChoices(const Definition&, std::optional<json::Value> origin = std::nullopt);
json::Value select(const Definition&, const json::Value& exactRequest);

struct Token final {
    std::uint64_t instance{}, pass{}, revision{};
    std::string sourceKey, contractSha256, sourceClosureSha256;
    Phase phase{Phase::Select};
    std::optional<std::size_t> step;
    Intent intent{Intent::Choose};
};
// Small reusable primitives: family validators keep their own transitions and
// hidden/reveal/debt semantics. These helpers do not advance a workflow.
void requireCurrentToken(const Token& supplied, const Token& current);
std::vector<std::string> validateManualReport(const json::Value& supplied,
                                             const json::Value& expected);
struct View final {
    Phase phase{Phase::Select};
    Outcome outcome{Outcome::None}, pendingOutcome{Outcome::None};
    std::optional<std::size_t> step; // source report step, one-based
    bool needsManualRelease{}, observedPerformance{false}, grantsCredit{false};
};
struct HistoryEvent final {
    Token token;
    json::Value reported;
    View before, after;
    std::optional<json::Value> diagnosis;
    bool observedPerformance{false}, grantsCredit{false};
};

// Serialized in-memory recipe owner. No clock/audio/tempo, Attempt, persistence,
// runtime admission or credit operation. Every user gesture needs a fresh token.
class RecipeTask final {
public:
    explicit RecipeTask(const Definition&);
    RecipeTask(const RecipeTask&) = delete;
    RecipeTask& operator=(const RecipeTask&) = delete;
    RecipeTask(RecipeTask&&) = delete;
    RecipeTask& operator=(RecipeTask&&) = delete;
    const Definition& retainedDefinition() const noexcept { return definition_; }
    View view() const;
    std::uint64_t pass() const;
    std::uint64_t revision() const;
    Token capture(Intent) const;
    // Throws explicit Error on malformed/stale input before any state mutation.
    // Valid false boolean reports instead diagnose and require release/retry.
    void apply(const Token&, const json::Value& payload);
    json::Value expectedReport() const;
    std::optional<json::Value> selectedPlan() const;
    std::optional<json::Value> selectedRequest() const;
    std::optional<json::Value> currentStep() const;
    std::optional<json::Value> diagnosis() const;
    std::vector<HistoryEvent> history() const;
    // Preserve idle phase/choice/diagnosis and history while invalidating all
    // pending native tokens before a settings or host navigation detour.
    bool fenceInactiveForNavigation();
    // Private draft only: source-bound legal replay, fresh gesture instance.
    // Does not release manual duties, certify performance or grant credit.
    std::string continuation() const;
    static std::unique_ptr<RecipeTask> restoreContinuation(const Definition&, const std::string&);

private:
    Definition definition_;
    mutable std::mutex mutex_;
    struct State {
        std::uint64_t pass{1}, revision{1};
        Phase phase{Phase::Select};
        Outcome outcome{Outcome::None}, pending{Outcome::None};
        std::optional<std::size_t> step;
        std::optional<json::Value> request, plan, diagnosis;
    } state_;
    std::uint64_t instance_;
    std::vector<HistoryEvent> history_;
    json::Value continuationBody() const; // caller holds mutex
    static View viewImpl(const State&);
    Token captureImpl(Intent) const;
    json::Value expectedReportImpl() const;
    static void enterRelease(State&, Outcome, std::optional<json::Value> diagnosis);
};
} // namespace fathom::tasks::recipes
