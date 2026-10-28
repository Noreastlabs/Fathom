#pragma once

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <functional>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace fathom::navigation {

// Value snapshots for navigation, never runtime admission capabilities. Obtain
// these from a real Catalog::admit result; recheck it before each preparation.
struct AdmissionIdentity {
    std::string itemId, variantId, contentVersion, sourceBinding;
    bool complete() const {
        return !itemId.empty() && !variantId.empty() &&
               !contentVersion.empty() && !sourceBinding.empty();
    }
    bool operator==(const AdmissionIdentity& other) const {
        return itemId == other.itemId && variantId == other.variantId &&
               contentVersion == other.contentVersion && sourceBinding == other.sourceBinding;
    }
};

enum class ExerciseMappingExtent { Unavailable, ExactSourceUnit, LargerSourceCase, Ambiguous };

struct ExerciseEntry {
    std::string levelKey, sublevelKey, sourceExerciseKey;
    // Contiguous reviewed order WITHIN the sublevel, not printed exercise number,
    // title order, PDF page order, or an offset into musical events.
    std::uint32_t sourceOrder{};
    // Oracle level_ordinal detects disjoint recurrences of one parent path.
    std::uint32_t levelOrder{};
    std::string indexRevision, sourceRevision;
    ExerciseMappingExtent mappingExtent{ExerciseMappingExtent::Unavailable};
    std::optional<AdmissionIdentity> admission;
};

struct ExerciseSelection {
    std::string levelKey, sublevelKey, firstSourceKey, lastSourceKey;
};

class ExercisePlan;
ExercisePlan planExercises(const std::vector<ExerciseEntry>&, const ExerciseSelection&);

class ExercisePlan final {
public:
    bool valid() const noexcept { return error_.empty() && !items_.empty(); }
    const std::string& error() const noexcept { return error_; }
    const std::vector<ExerciseEntry>& items() const noexcept { return items_; }
private:
    friend ExercisePlan planExercises(const std::vector<ExerciseEntry>&, const ExerciseSelection&);
    std::vector<ExerciseEntry> items_;
    std::string error_;
};

inline ExercisePlan planExercises(const std::vector<ExerciseEntry>& entries,
                                  const ExerciseSelection& selection) {
    const auto refuse = [](std::string error) {
        ExercisePlan result;
        result.error_ = std::move(error);
        return result;
    };
    if (selection.levelKey.empty() || selection.sublevelKey.empty() ||
        selection.firstSourceKey.empty() || selection.lastSourceKey.empty())
        return refuse("Choose a level, source sublevel and both exercise endpoints.");

    std::map<std::string, std::size_t> keyCounts;
    const ExerciseEntry* first = nullptr;
    const ExerciseEntry* last = nullptr;
    for (const auto& entry : entries) {
        ++keyCounts[entry.sourceExerciseKey];
        if (entry.sourceExerciseKey == selection.firstSourceKey) first = &entry;
        if (entry.sourceExerciseKey == selection.lastSourceKey) last = &entry;
    }
    if (!first || !last) return refuse("A selected source exercise is missing from this index.");
    if (keyCounts[first->sourceExerciseKey] != 1 || keyCounts[last->sourceExerciseKey] != 1)
        return refuse("A selected source exercise key is duplicated in this index.");
    for (const auto* endpoint : {first, last})
        if (endpoint->levelKey != selection.levelKey || endpoint->sublevelKey != selection.sublevelKey)
            return refuse("Choose both exercises within the same source sublevel.");
    if (!first->sourceOrder || !last->sourceOrder || last->sourceOrder < first->sourceOrder)
        return refuse("Choose an inclusive range in source order; the end cannot precede the start.");
    if (first->indexRevision.empty() || first->sourceRevision.empty())
        return refuse("The selected source index or original source revision is unavailable.");

    ExercisePlan result;
    std::set<std::uint32_t> orders;
    std::set<std::string> itemIds;
    for (const auto& entry : entries) {
        if (entry.levelKey != selection.levelKey || entry.sublevelKey != selection.sublevelKey ||
            entry.sourceOrder < first->sourceOrder || entry.sourceOrder > last->sourceOrder) continue;
        if (entry.sourceExerciseKey.empty() || !entry.levelOrder || keyCounts[entry.sourceExerciseKey] != 1 ||
            !orders.insert(entry.sourceOrder).second)
            return refuse("The selected range contains a duplicate or ambiguous source exercise.");
        if (entry.indexRevision != first->indexRevision || entry.sourceRevision != first->sourceRevision)
            return refuse("The selected range mixes source index or original source revisions.");
        if (entry.mappingExtent == ExerciseMappingExtent::LargerSourceCase)
            return refuse("Source exercise " + entry.sourceExerciseKey + " is covered only by a larger admitted case; choose an exact exercise mapping.");
        if (entry.mappingExtent != ExerciseMappingExtent::ExactSourceUnit)
            return refuse("Source exercise " + entry.sourceExerciseKey + " has no reviewed exact-unit Practice mapping.");
        if (!entry.admission || !entry.admission->complete())
            return refuse("Source exercise " + entry.sourceExerciseKey + " is unavailable for Practice.");
        if (!itemIds.insert(entry.admission->itemId).second)
            return refuse("Different source exercises resolve to the same admitted item.");
        result.items_.push_back(entry);
    }
    const auto expected = std::uint64_t{last->sourceOrder} - first->sourceOrder + 1;
    if (result.items_.size() != expected)
        return refuse("The selected range contains a missing source exercise; no gap was skipped.");
    std::sort(result.items_.begin(), result.items_.end(), [](const auto& a, const auto& b) {
        return a.sourceOrder < b.sourceOrder;
    });
    for (std::size_t i = 1; i < result.items_.size(); ++i)
        if (std::uint64_t{result.items_[i - 1].levelOrder} + 1 != result.items_[i].levelOrder)
            return refuse("The selected range crosses separate source segments of this sublevel.");
    return result;
}

struct ExerciseLaunch {
    std::uint64_t ticket{}; // transient process-local correlation, never a Session/Attempt ID
    ExerciseEntry exercise;
    std::string sessionId; // actual distinct storage Session supplied by the trusted adapter
};

enum class ExerciseQueuePhase { Ready, Open, Resolved, Complete };
enum class ResultDisposition { Saved, SafelyDiscarded };
struct ExerciseResolution {
    std::uint64_t ticket{};
    AdmissionIdentity admission;
    ResultDisposition disposition{ResultDisposition::Saved};
    bool canLeave{}, outputCleared{};
    std::string sessionId, attemptId; // observed actual saved record IDs; never allocated here
};

// UI-thread-only transient coordinator. Does not persist, start sound, save,
// allocate a Session/Attempt, score, or grant credit. Practice remains authority
// for result resolution. Do not manufacture resolution from transport Stop.
class ExerciseQueue final {
public:
    using Resolver = std::function<std::optional<AdmissionIdentity>(const ExerciseEntry&)>;
    using Prepare = std::function<bool(const ExerciseLaunch&)>;

    explicit ExerciseQueue(ExercisePlan plan) : plan_(std::move(plan)) {
        if (!plan_.valid()) throw std::invalid_argument("An exercise queue requires a valid source plan.");
    }
    ExerciseQueue(const ExerciseQueue&) = delete;
    ExerciseQueue& operator=(const ExerciseQueue&) = delete;
    ExerciseQueue(ExerciseQueue&&) = delete;
    ExerciseQueue& operator=(ExerciseQueue&&) = delete;

    ExerciseQueuePhase phase() const noexcept { return phase_; }
    std::size_t position() const noexcept { return position_; }
    std::size_t size() const noexcept { return plan_.items().size(); }
    const ExerciseEntry* current() const noexcept {
        return phase_ == ExerciseQueuePhase::Complete ? nullptr : &plan_.items()[position_];
    }
    const ExerciseEntry* entryAt(std::size_t index) const noexcept { return index < size() ? &plan_.items()[index] : nullptr; }
    const std::optional<ExerciseLaunch>& activeLaunch() const noexcept { return launch_; }
    const std::optional<ExerciseResolution>& resolution() const noexcept { return resolution_; }

    // Call only from explicit "Open selected exercise". Resolver must use the
    // current Catalog, retain its actual immutable Admission, and Prepare must
    // pass that SAME object through the existing Home -> Practice boundary.
    // Neither callback may run Start or create an Attempt. Callbacks must not
    // reenter this coordinator. False/exception leaves the queue at Ready.
    bool openExplicitly(const std::string& sessionId, const Resolver& resolve,
                        const Prepare& prepare, std::string& error) {
        error.clear();
        if (phase_ != ExerciseQueuePhase::Ready || busy_)
            return fail(error, "Resolve the current exercise before opening another one.");
        if (sessionId.empty() || usedSessionIds_.count(sessionId))
            return fail(error, "Each queued exercise requires its own distinct Practice Session.");
        Busy guard(busy_);
        try {
            if (!resolve || !prepare) return fail(error, "Practice is not connected.");
            const auto resolved = resolve(*current());
            if (!resolved || !(*resolved == *current()->admission))
                return fail(error, "This exercise's admission changed or is unavailable; review its selection again.");
            ExerciseLaunch candidate{nextTicket(), *current(), sessionId};
            if (!prepare(candidate)) return fail(error, "Practice could not release or prepare this exercise; retain the current result.");
            usedSessionIds_.insert(sessionId);
            launch_ = std::move(candidate);
            phase_ = ExerciseQueuePhase::Open;
            return true;
        } catch (const std::exception& exception) {
            return fail(error, std::string{"Practice preparation refused: "} + exception.what());
        }
    }

    // Trusted adapter observation after successful saved/explicit-discard AND
    // cleanup. User-facing Next must not fabricate this receipt. A saved result
    // must retain its actual Session/Attempt IDs. SafelyDiscarded is only for
    // an existing safe cancellation path; this API performs no discard itself.
    bool noteResolved(const ExerciseResolution& receipt, std::string& error) {
        error.clear();
        if (busy_ || phase_ != ExerciseQueuePhase::Open || !launch_ ||
            receipt.ticket != launch_->ticket || receipt.sessionId != launch_->sessionId ||
            !(receipt.admission == *launch_->exercise.admission))
            return fail(error, "This result does not belong to the open exercise.");
        if (!receipt.canLeave || !receipt.outputCleared)
            return fail(error, "Save or safely discard the current result and finish audio cleanup first.");
        if (receipt.disposition != ResultDisposition::Saved && receipt.disposition != ResultDisposition::SafelyDiscarded)
            return fail(error, "The result disposition is invalid.");
        if (receipt.disposition == ResultDisposition::Saved && (receipt.sessionId.empty() || receipt.attemptId.empty()))
            return fail(error, "A saved result must retain its actual Session and Attempt identities.");
        resolution_ = receipt;
        phase_ = ExerciseQueuePhase::Resolved;
        return true;
    }

    // Call only from explicit Next. Does not open Practice or allocate anything.
    bool nextExplicitly(std::string& error) {
        error.clear();
        if (busy_ || phase_ != ExerciseQueuePhase::Resolved)
            return fail(error, "Resolve the current exercise before choosing Next.");
        ++position_;
        launch_.reset();
        resolution_.reset();
        phase_ = position_ == size() ? ExerciseQueuePhase::Complete : ExerciseQueuePhase::Ready;
        return true;
    }
private:
    struct Busy {
        bool& value;
        explicit Busy(bool& flag) : value(flag) { value = true; }
        ~Busy() { value = false; }
    };
    static bool fail(std::string& error, std::string reason) { error = std::move(reason); return false; }
    static std::uint64_t nextTicket() {
        static std::atomic<std::uint64_t> next{1};
        auto value = next.load();
        do {
            if (value == std::numeric_limits<std::uint64_t>::max())
                throw std::overflow_error("Exercise launch ticket capacity exhausted.");
        } while (!next.compare_exchange_weak(value, value + 1));
        return value;
    }
    ExercisePlan plan_;
    std::size_t position_{};
    ExerciseQueuePhase phase_{ExerciseQueuePhase::Ready};
    std::optional<ExerciseLaunch> launch_;
    std::optional<ExerciseResolution> resolution_;
    std::set<std::string> usedSessionIds_;
    bool busy_{};
};

} // namespace fathom::navigation
