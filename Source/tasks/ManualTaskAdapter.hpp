#pragma once
#include "tasks/TaskContract.hpp"
#include "platform/MetronomePlayback.hpp"
#include <cstdint>
#include <optional>
#include <memory>
#include <functional>
#include <string>

namespace fathom::tasks {
enum class IntentKind { SourceOrder, EvenPulse, Ready, Acknowledge, Retry, Cancel, Release, Again, Reopen, Unknown };
struct IntentToken final {
    std::uint64_t instance{},pass{},revision{};
    std::string sourceKey,policySha256;
    Phase phase{Phase::Choose};
    std::optional<std::size_t> actionIndex;
    IntentKind kind{IntentKind::SourceOrder};
};
struct ReportHistoryEvent final {
    IntentToken token;
    json::Value reported;
    View before, after;
    std::optional<json::Value> diagnosis;
    bool observedPerformance{false}, grantsCredit{false};
};
class ManualTaskAdapter final {
public:
    explicit ManualTaskAdapter(const Definition& definition);
    ManualTaskAdapter(const ManualTaskAdapter&) = delete;
    ManualTaskAdapter& operator=(const ManualTaskAdapter&) = delete;
    ManualTaskAdapter(ManualTaskAdapter&&) = delete;
    ManualTaskAdapter& operator=(ManualTaskAdapter&&) = delete;
    const Definition& definition() const noexcept {return task_.definition();}
    View view() const noexcept {return task_.view();}
    std::uint64_t pass() const noexcept {return pass_;}
    std::uint64_t revision() const noexcept {return revision_;}
    IntentToken capture(IntentKind kind) const;
    bool apply(const IntentToken&,std::optional<int> bpm,TempoRange currentHostRange,
               std::optional<json::Value> report=std::nullopt);
    const std::vector<ReportHistoryEvent>& history() const noexcept {return history_;}
    const std::optional<json::Value>& diagnosis() const noexcept {return task_.diagnosis();}
    // Arm only with the clock generation actually started by the shared owner.
    bool armClock(const scheduler::Owner&,std::uint64_t binding,std::uint32_t sampleRate);
    bool progress(const platform::MetronomeProgress&);
    void invalidateForNavigation();
    // Choose has no active physical duty; Closed has already released. Fence
    // delayed host input while preserving their phase, definition and history.
    bool fenceInactiveForNavigation();
    const std::string& error() const noexcept {return error_;}
    bool clockArmed() const noexcept {return clockArmed_;}
    // Host must freeze edits and resolve the actual output before capture.
    // A live bound clock is refused; restore never starts or resumes audio.
    std::string continuation() const;
    static std::unique_ptr<ManualTaskAdapter> restoreContinuation(const Definition&,const std::string&);

private:
    bool same(const IntentToken&) const noexcept;
    bool record(json::Value,const std::function<bool()>&);
    bool applyImpl(const IntentToken&,std::optional<int>,TempoRange,std::optional<json::Value>);
    bool armClockImpl(const scheduler::Owner&,std::uint64_t,std::uint32_t);
    bool progressImpl(const platform::MetronomeProgress&);
    void invalidateForNavigationImpl();
    bool fenceInactiveForNavigationImpl();

    void invalidateClock() noexcept;
    static std::uint64_t nextInstance() noexcept;
    json::Value continuationBody() const;
    json::Value::Array journal_;
    Task task_;
    std::uint64_t instance_,pass_{1},revision_{1};
    bool clockArmed_{},originSet_{};
    scheduler::Owner clockOwner_{};
    std::uint64_t clockBinding_{},lastSequence_{},originFrames_{};
    std::uint32_t sampleRate_{};
    std::string error_;
    std::vector<ReportHistoryEvent> history_;
};
}
