#pragma once
#include "tasks/RecipeTask.hpp"
#include <mutex>

namespace fathom::tasks::manual_curriculum {
// Closed cached source definitions. Original records/context/expected values
// are trusted metadata, never a learner UI boundary.
class Definition final {
public:
    Definition(const Definition&) = default;
    const std::string& sourceKey() const noexcept { return key_; }
    const std::string& sourceIdentity() const noexcept { return identity_; }
    const std::string& contractSha256() const noexcept { return contractSha_; }
    const std::string& sourceClosureSha256() const noexcept { return closureSha_; }
    const json::Value& exportedDefinition() const noexcept { return exported_; }
    const json::Value& retainedProgram() const noexcept { return program_; }
    const json::Value& retainedSourceContext() const noexcept { return context_; }
    json::Value sourcePlayerView() const;
private:
    explicit Definition(const char* row);
    std::string key_, identity_, contractSha_, closureSha_;
    json::Value exported_, program_, context_;
    friend const Definition& definition(const std::string& exactSourceKey);
};
const Definition& definition(const std::string& exactSourceKey);
const std::vector<std::string>& keys();
// A token binds the shared owner primitive plus exact action and procedure
// cursor. Revision is monotonic, including navigation/retry/reveal/release.
struct Token final {
    recipes::Token owner;
    std::string action, state;
    std::size_t cursor{};
};
class ManualCurriculumTask final {
public:
    explicit ManualCurriculumTask(const Definition&);
    ManualCurriculumTask(const ManualCurriculumTask&) = delete;
    ManualCurriculumTask& operator=(const ManualCurriculumTask&) = delete;
    const Definition& retainedDefinition() const noexcept { return definition_; }
    Token capture(const std::string& action) const;
    // Malformed input refuses without mutation; well-formed unknown/negative
    // reports are retained, diagnosed and require release/retry as appropriate.
    void apply(const Token&, const json::Value& payload);
    json::Value learnerView() const;
    json::Value learnerInstructions() const;
    json::Value learnerActions() const;
    json::Value sourcePlayerView() const { return definition_.sourcePlayerView(); }
    std::vector<json::Value> history() const;
    // Only Select/Completed/Cancelled, without release debt. Preserve history,
    // exposure and phase while invalidating input owned before a host detour.
    bool fenceInactiveForNavigation();
private:
    Definition definition_;
    mutable std::mutex mutex_;
    std::uint64_t instance_;
    struct State {
        std::uint64_t pass{1}, revision{1};
        std::string phase{"select"};
        std::size_t cursor{}, retryTarget{};
        bool releaseDebt{}, revealedEver{}, selfCheckVisible{};
        std::string afterRelease;
        json::Value diagnosis;
        json::Value::Object saved;
    } state_;
    std::vector<json::Value> history_;
    Token captureImpl(const std::string&) const;
    json::Value viewImpl() const;
    json::Value actionsImpl() const;
};
// Validate the public typed schema without choosing, completing or reporting
// anything. Empty/default input is never synthesized by this API.
void validateInputSchema(const json::Value& schema, const json::Value& input);
} // namespace fathom::tasks::manual_curriculum
