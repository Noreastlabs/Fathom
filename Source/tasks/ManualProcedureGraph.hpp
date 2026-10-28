#pragma once
#include "tasks/RecipeTask.hpp"
#include <mutex>
#include <set>
#include <memory>
#include "tasks/ManualProcedureSharedContexts.hpp"

namespace fathom::tasks::manual_procedure_graph {
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
    const json::Value& retainedSourceContext() const noexcept { return *context_; }
    const json::Value& retainedOriginalRecord() const noexcept { return referenceOriginal_ ? *referenceOriginal_ : *exported_.find("original_record"); }
    const json::Value& retainedOriginalContract() const;
    json::Value learnerInstructionContext() const;
    json::Value sourcePlayerView() const;
private:
    explicit Definition(const char* row,const char* ownClosure,const char* referenceOriginal);
    std::string key_, identity_, contractSha_, closureSha_;
    json::Value exported_, program_;
    std::shared_ptr<const json::Value> context_, referenceOriginal_;
    friend const Definition& definition(const std::string& exactSourceKey);
    friend const Definition& extraSourceDefinition(const std::string& exactSourceKey);
};
const Definition& definition(const std::string& exactSourceKey);
const std::vector<std::string>& keys();
// Separate existing-source catalog; no WBS admission.
const Definition& extraSourceDefinition(const std::string& exactSourceKey);
const std::vector<std::string>& extraSourceKeys();
// A token binds the shared owner primitive plus exact action and procedure
// cursor. Revision is monotonic, including navigation/retry/reveal/release.
class Token final {
public:
    Token(const Token&) = default;
private:
    Token(recipes::Token owned,std::string a,std::string s,std::size_t c,std::uint64_t fr,std::string nd):owner(std::move(owned)),action(std::move(a)),state(std::move(s)),cursor(c),frame(fr),node(std::move(nd)) {}
    recipes::Token owner;
    std::string action, state;
    std::size_t cursor{};
    std::uint64_t frame{};
    std::string node;
    friend class ManualProcedureGraph;
};
// Explicit trusted caller boundary, not authentication. This wrapper cannot be
// passed to learner apply() or unwrapped by a caller.
class SourceRoleAction final {
public:
    SourceRoleAction(const SourceRoleAction&) = default;
private:
    explicit SourceRoleAction(Token t):token_(std::move(t)) {}
    Token token_;
    friend class ManualProcedureGraph;
};
// Immutable same-owner save proposal. The watermark belongs to these exact
// bytes, not a later read of a live owner. It carries no profile authorization.
class PrivateContinuation final {
public:
    const std::string& bytes()const noexcept{return bytes_;}
    std::size_t watermark()const noexcept{return watermark_;}
private:
    PrivateContinuation(std::string bytes,std::size_t watermark):bytes_(std::move(bytes)),watermark_(watermark){}
    std::string bytes_;std::size_t watermark_{};
    friend class ManualProcedureGraph;
};
class ManualProcedureGraph final {
public:
    explicit ManualProcedureGraph(const Definition&);
    ManualProcedureGraph(const ManualProcedureGraph&) = delete;
    ManualProcedureGraph& operator=(const ManualProcedureGraph&) = delete;
    const Definition& retainedDefinition() const noexcept { return definition_; }
    Token capture(const std::string& action) const;
    bool current(const Token&) const noexcept;
    // Malformed input refuses without mutation; well-formed unknown/negative
    // reports are retained, diagnosed and require release/retry as appropriate.
    void apply(const Token&, const json::Value& payload);
    json::Value learnerView() const;
    json::Value learnerInstructions() const;
    json::Value learnerActions() const;
    json::Value sourcePlayerView() const;
    std::vector<json::Value> history() const;
    std::size_t historyCount() const;
    json::Value sourcePlayerActions() const;
    SourceRoleAction captureSourceAction(const std::string&) const;
    bool current(const SourceRoleAction&) const noexcept;
    void applySourceAction(const SourceRoleAction&,const json::Value&);
    std::vector<json::Value> sourcePlayerHistory() const;
    // Only Select/Completed/Cancelled, without release debt. Preserve history,
    // exposure and phase while invalidating input owned before a host detour.
    bool fenceInactiveForNavigation();
    // Private same-profile continuity data, not a learner history export.
    // Exact source/version and full native replay are checked on restoration.
    // New instance fences old tokens; reports, dates, retries and release debt
    // remain historical manual declarations, never observed performance.
    std::string continuation() const;
    PrivateContinuation captureContinuation() const;
    std::size_t continuationWatermark() const;
    static std::unique_ptr<ManualProcedureGraph> restoreContinuation(
        const Definition& expectedSource,const std::string& privateBytes);
    void recordSourcePresentation();
    bool sourcePresentationSeen() const;

private:
    Definition definition_;
    mutable std::mutex mutex_;
    std::uint64_t instance_;
    struct Frame {
        std::string key,node,exit;
        std::uint64_t serial{};
        json::Value::Object saved;
        json::Value::Array calls;
        std::set<std::string> committedNodes;
    };
    struct State {
        std::uint64_t pass{1}, revision{1};
        std::string phase{"select"};
        std::size_t cursor{}, retryTarget{};
        bool releaseDebt{}, revealedEver{}, selfCheckVisible{};
        std::string afterRelease;
        json::Value diagnosis;
        json::Value::Object saved;
        std::vector<Frame> frames;
        std::uint64_t frameSerial{};
        json::Value failed;
        json::Value::Object readiness;
        bool auditDebt{true};
        std::string releaseReason, retryEntry;
        json::Value::Object sourcePolicyState;
        std::set<std::string> currentPassReveals;
        json::Value::Object retainedPrintedReveals;
    } state_;
    std::vector<json::Value> history_;
    std::vector<json::Value> continuationJournal_;
    bool sourcePresentationSeen_{};
    void prepareJournalSlot();
    std::string continuationStateDigest(const State&) const;

    void applyImpl(const Token&,const json::Value&,bool sourceRole);
    bool graphMode() const noexcept;
    const Definition& frameDefinition(const State&) const;
    const json::Value& graphNode(const State&) const;
    void graphContinue(State&,bool reportCommitted) const;
    void graphApply(const Token&,const json::Value&);
    json::Value graphView() const;
    json::Value graphActions() const;
    Token captureImpl(const std::string&) const;
    json::Value viewImpl() const;
    json::Value actionsImpl() const;
};
// Validate the public typed schema without choosing, completing or reporting
// anything. Empty/default input is never synthesized by this API.
void validateInputSchema(const json::Value& schema, const json::Value& input);
} // namespace fathom::tasks::manual_procedure_graph
