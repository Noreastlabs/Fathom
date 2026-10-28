#pragma once

// Fixture-only vocabulary and one-shot controller. Not included by Source/.
#include <cstdint>
#include <functional>
#include <mutex>
#include <stdexcept>
#include <string>

namespace fathom::ui_fixture {
enum class Fault {
    None, EmptyDevice, ConnectRefused, LoadFailed, CorruptLoad,
    PreferenceReadFailed, CorruptPreferenceReply, SettingsSaveFailed,
    SaveBeforeCommit, SaveLostReceipt
};
inline const char* name(Fault fault) noexcept {
    switch (fault) {
        case Fault::None: return "none";
        case Fault::EmptyDevice: return "empty-device";
        case Fault::ConnectRefused: return "connect-refused";
        case Fault::LoadFailed: return "load-failed";
        case Fault::CorruptLoad: return "corrupt-load";
        case Fault::PreferenceReadFailed: return "preference-read-failed";
        case Fault::CorruptPreferenceReply: return "corrupt-preference-reply";
        case Fault::SettingsSaveFailed: return "settings-receipt-failed";
        case Fault::SaveBeforeCommit: return "save-before-commit";
        case Fault::SaveLostReceipt: return "save-lost-receipt";
    }
    return "unknown";
}
struct Failure final : std::runtime_error {
    Fault type;
    explicit Failure(Fault fault)
        : std::runtime_error(std::string{"UI_FIXTURE_"} + name(fault) + ": controlled synthetic failure"), type(fault) {}
};
class Faults final {
public:
    using Observer = std::function<void(Fault, std::uint64_t, const std::string&)>;
    explicit Faults(Observer observer = {}) : observer_(std::move(observer)) {}
    bool arm(Fault fault, std::string operation = {}) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (armed_ != Fault::None || fault == Fault::None) return false;
        armed_ = fault; operation_ = std::move(operation); ++generation_;
        return true;
    }
    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        armed_ = Fault::None; operation_.clear();
    }
    Fault armed() const {
        std::lock_guard<std::mutex> lock(mutex_); return armed_;
    }
    bool take(Fault fault, const std::string& operation) {
        Observer observer; std::uint64_t generation{};
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (fault == Fault::None || armed_ != fault || (!operation_.empty() && operation_ != operation)) return false;
            armed_ = Fault::None; operation_.clear(); generation = generation_; observer = observer_;
        }
        if (observer) observer(fault, generation, operation);
        return true;
    }
    void hook(const std::string& phase, const std::string& operation) {
        // Existing capture controllers bind the original final-save operation.
        // A retry has a different suffix and does not receive an invented failure.
        constexpr const char* suffix = ".save.commit";
        const bool finalSave = operation.size() >= 12 && operation.compare(operation.size() - 12, 12, suffix) == 0;
        if (finalSave && phase == "before_commit" && take(Fault::SaveBeforeCommit, operation)) throw Failure(Fault::SaveBeforeCommit);
        if (finalSave && phase == "after_commit" && take(Fault::SaveLostReceipt, operation)) throw Failure(Fault::SaveLostReceipt);
        // Settings/inspection faults perturb only the owned returned receipt in
        // the fixture dispatcher. They never alter the committed database.
    }
private:
    mutable std::mutex mutex_;
    Fault armed_{Fault::None};
    std::string operation_;
    std::uint64_t generation_{};
    Observer observer_;
};
} // namespace fathom::ui_fixture
