#pragma once
#include "desktop/PresentationPolicy.hpp"
#include "desktop/SetupPolicy.hpp"
#include "metronome/MetronomePreferences.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "storage/ProfileStore.hpp"
#include "storage/ManualDraftStore.hpp"
#include "storage/ProfileNaming.hpp"
#include <chrono>
#include <limits>

namespace fathom::desktop::presentation {
// Route only named owners. This does not weaken the existing timing validator.
inline bool composedPreferenceValidator(const std::string& key, std::int64_t version,
                                        const json::Value& value) noexcept {
    if (key == storage::profile_names::key) return storage::profile_names::preferenceValidator(key,version,value);
    if (storage::manual_drafts::ownsKey(key)) return storage::manual_drafts::preferenceValidator(key, version, value);
    if (key == preferenceKey) return preferenceValidator(key, version, value);
    if (key == setup::preferenceKey) return setup::preferenceValidator(key, version, value);
    return metronome::preferenceValidator(key, version, value);
}
enum class PreferenceState {
    NoProfile, Reading, Ready, SessionOnly, StopRequired, Saving,
    Conflict, Unsupported, Failed, Unknown
};

// UI-thread-owned, nonblocking. The caller owns the store and must keep it alive
// until canDetach(). It supplies the actual stopped-and-resolved application gate.
// No destructor, poll or choice change initiates a write or a transport action.
class PreferencesController final {
public:
    const Model& model() const noexcept { return model_; }
    PreferenceState state() const noexcept { return state_; }
    const std::string& statusText() const noexcept { return message_; }
    const std::string& profileIdentity() const noexcept { return profileIdentity_; }
    const std::string& pendingOperationId() const noexcept { return pendingOperation_; }
    const std::string& pendingBytes() const noexcept { return pendingBytes_; }
    std::optional<std::int64_t> observedRevision() const noexcept {
        return loaded_ ? std::optional<std::int64_t>{revision_} : std::nullopt;
    }
    bool hasProfile() const noexcept { return store_ != nullptr; }
    bool dirty() const noexcept { return dirty_; }
    bool inFlight() const noexcept { return future_.has_value(); }
    bool pending() const noexcept { return future_.has_value() || !pendingOperation_.empty(); }
    bool canDetach() const noexcept { return !pending(); }
    bool canSave(bool stoppedAndResolved) const noexcept {
        return store_ && loaded_ && supported_ && dirty_ && stoppedAndResolved &&
               revision_ < std::numeric_limits<std::int64_t>::max() &&
               !pending() && state_ != PreferenceState::Conflict;
    }

    bool attach(storage::ProfileStore& store, std::string profileIdentity) {
        if (!canDetach() || profileIdentity.empty()) return false;
        resetBinding();
        store_ = &store;
        profileIdentity_ = std::move(profileIdentity);
        return startRead(false);
    }
    bool detach() {
        if (!canDetach()) return false;
        resetBinding();
        return true;
    }
    void chooseGlobal(Level level) {
        model_.setGlobalLevel(level);
        const bool duringRead = future_ && !writing_;
        dirty_ = duringRead || !loaded_ || !savedLevel_ || level != *savedLevel_;
        if (duringRead) reloadChoice_ = false; // A newer explicit choice wins over a pending read.
        updateChoiceMessage();
    }
    void choosePage(Page page, std::optional<Level> level) { model_.setPageOverride(page, level); }
    void resetPage(Page page) { model_.resetPage(page); }
    // Explicit reset changes disclosure only. Call save(actualGate) separately
    // to persist it; active transport and owner obligations are never touched.
    void resetPresentation() {
        model_.resetPresentation();
        const bool duringRead = future_ && !writing_;
        dirty_ = duringRead || !loaded_ || !savedLevel_ || *savedLevel_ != Level::Beginner;
        if (duringRead) reloadChoice_ = false;
        updateChoiceMessage();
    }
    bool save(bool stoppedAndResolved) {
        if (!canSave(stoppedAndResolved)) {
            if (store_ && loaded_ && supported_ && dirty_ && !pending() &&
                state_ != PreferenceState::Conflict && !stoppedAndResolved) {
                state_ = PreferenceState::StopRequired;
                message_ = "Presentation changed for this session. Stop and resolve the current activity before saving this setting.";
            }
            return false;
        }
        try {
            pendingBytes_ = storage::canonical(encodePreferences(model_.globalLevel()));
            pendingOperation_ = storage::newUuid();
            expectedRevision_ = revision_;
            proposedLevel_ = model_.globalLevel();
            activeOperation_ = pendingOperation_;
            future_.emplace(store_->compareExchangePreferences(pendingOperation_, preferenceKey,
                namespaceVersion, expectedRevision_, pendingBytes_, stoppedAndResolved));
            writing_ = true;
            state_ = PreferenceState::Saving;
            message_ = "Saving presentation setting…";
            return true;
        } catch (...) {
            // Submission exceptions do not establish absence. Keep the original
            // proposal and operation instead of issuing a replacement write.
            state_ = pendingOperation_.empty() ? PreferenceState::Failed : PreferenceState::Unknown;
            message_ = pendingOperation_.empty()
                ? "Presentation was not saved. Retry explicitly when stopped and resolved."
                : "Presentation save is not confirmed. Keep the profile open and check the original save.";
            return false;
        }
    }
    // Explicit Reload accepts the saved global choice after a definite conflict.
    // For an unknown write it inspects the original exact proposal instead.
    bool reload() { return store_ && !future_ && startRead(true); }

    bool poll() {
        if (!future_ || future_->wait_for(std::chrono::milliseconds(0)) != std::future_status::ready)
            return false;
        const bool wasWriting = writing_;
        try {
            const auto reply = future_->get();
            future_.reset();
            writing_ = false;
            if (reply.operation != activeOperation_ || reply.owner != preferenceKey)
                throw std::runtime_error("Presentation response identity mismatch");
            if (wasWriting) applyWrite(reply); else applyRead(reply);
        } catch (...) {
            future_.reset();
            writing_ = false;
            state_ = pendingOperation_.empty() ? PreferenceState::Failed : PreferenceState::Unknown;
            message_ = pendingOperation_.empty()
                ? "Saved presentation setting could not be read. Reload it before saving."
                : "Presentation save is not confirmed. Keep the profile open and check the original save.";
            if (pendingOperation_.empty()) loaded_ = false;
        }
        return true;
    }

private:
    static std::int64_t integer(const json::Value& data, const char* key) {
        const auto* value = data.find(key);
        std::int64_t result = 0;
        if (!value || !value->integer(result) || result < 0)
            throw std::runtime_error("Invalid presentation revision/version response");
        return result;
    }
    bool startRead(bool explicitReload) {
        try {
            activeOperation_ = storage::newUuid();
            future_.emplace(store_->readPreferences(activeOperation_, preferenceKey));
            writing_ = false;
            reloadChoice_ = explicitReload && pendingOperation_.empty();
            state_ = PreferenceState::Reading;
            message_ = pendingOperation_.empty() ? "Reading saved presentation setting…"
                : "Checking the original presentation save; no new write is being made.";
            return true;
        } catch (...) {
            state_ = pendingOperation_.empty() ? PreferenceState::Failed : PreferenceState::Unknown;
            message_ = "Saved presentation setting could not be read. Original save, if any, remains unresolved.";
            return false;
        }
    }
    void applyWrite(const storage::Reply& reply) {
        if (reply.status == storage::Status::Confirmed) {
            if (expectedRevision_ == std::numeric_limits<std::int64_t>::max() ||
                integer(reply.data, "revision") != expectedRevision_ + 1 ||
                integer(reply.data, "namespace_version") != namespaceVersion)
                throw std::runtime_error("Presentation write acknowledgment does not match the proposal");
            revision_ = expectedRevision_ + 1;
            savedLevel_ = proposedLevel_;
            clearProposal();
            dirty_ = model_.globalLevel() != *savedLevel_;
            state_ = dirty_ ? PreferenceState::SessionOnly : PreferenceState::Ready;
            message_ = dirty_ ? "Earlier presentation choice saved. Your latest choice is for this session; save it explicitly."
                             : "Presentation setting saved.";
            return;
        }
        if (reply.status == storage::Status::Unresolved || reply.status == storage::Status::DefinitelyAbsent) {
            state_ = PreferenceState::Unknown;
            message_ = "Presentation save is not confirmed. Keep the profile open and check the original save.";
            return;
        }
        clearProposal(); // Only definite no-write replies release the proposal.
        dirty_ = true;
        if (reply.status == storage::Status::Conflict) {
            state_ = PreferenceState::Conflict;
            message_ = "Saved presentation setting changed elsewhere. Reload it before saving again.";
        } else if (reply.status == storage::Status::Unsupported) {
            state_ = PreferenceState::Unsupported;
            supported_ = false;
            message_ = "Saved presentation setting is not supported. Using this session choice; saved settings are unchanged.";
        } else {
            state_ = reply.code == "STOP_REQUIRED" ? PreferenceState::StopRequired : PreferenceState::Failed;
            message_ = "Presentation was not saved. This choice is for this session; retry explicitly when stopped and resolved.";
        }
    }
    void applyRead(const storage::Reply& reply) {
        if (reply.status != storage::Status::Confirmed && reply.status != storage::Status::DefinitelyAbsent) {
            state_ = pendingOperation_.empty() ? PreferenceState::Failed : PreferenceState::Unknown;
            if (pendingOperation_.empty()) loaded_ = false;
            message_ = "Saved presentation setting could not be read. Keep any original save and reload explicitly.";
            return;
        }
        const bool absent = reply.status == storage::Status::DefinitelyAbsent;
        const auto revision = absent ? 0 : integer(reply.data, "revision");
        const auto version = absent ? namespaceVersion : integer(reply.data, "namespace_version");
        std::string bytes;
        bool applicable = absent;
        if (!absent) {
            const auto* raw = reply.data.find("bytes");
            const auto* applies = reply.data.find("applicable");
            if (!raw || !raw->isString() || !applies || !applies->isBool() || revision == 0)
                throw std::runtime_error("Invalid presentation read response");
            bytes = raw->string();
            applicable = applies->boolean();
        }
        // The preference API has no operation journal. Exact next revision and
        // bytes can establish current stored value, not which operation wrote it.
        if (!pendingOperation_.empty()) {
            if (applicable && version == namespaceVersion &&
                expectedRevision_ < std::numeric_limits<std::int64_t>::max() &&
                revision == expectedRevision_ + 1 && bytes == pendingBytes_) {
                revision_ = revision;
                savedLevel_ = proposedLevel_;
                clearProposal();
                loaded_ = supported_ = true;
                dirty_ = model_.globalLevel() != *savedLevel_;
                state_ = dirty_ ? PreferenceState::SessionOnly : PreferenceState::Ready;
                message_ = "Exact presentation value confirmed stored at the expected next revision. Which operation saved it is not established.";
            } else {
                state_ = PreferenceState::Unknown;
                message_ = "The original presentation save is still unresolved. Stored value differs or is unsupported; keep the profile open. No retry or overwrite is available.";
            }
            return;
        }
        loaded_ = true;
        revision_ = revision;
        supported_ = applicable && version == namespaceVersion;
        if (!supported_) {
            savedLevel_.reset();
            if (reloadChoice_ || !dirty_) model_.setGlobalLevel(Level::Beginner);
            dirty_ = true;
            state_ = PreferenceState::Unsupported;
            message_ = "Saved presentation setting is not supported. Using Beginner for this session; saved settings are unchanged.";
            if (model_.globalLevel() != Level::Beginner)
                message_ = "Saved presentation setting is not supported. Using this session choice; saved settings are unchanged.";
            return;
        }
        savedLevel_ = absent ? std::optional<Level>{} : decodePreferences(storage::parseCanonical(bytes));
        if (reloadChoice_ || !dirty_) model_.setGlobalLevel(savedLevel_.value_or(Level::Beginner));
        dirty_ = savedLevel_ ? model_.globalLevel() != *savedLevel_ : dirty_;
        state_ = dirty_ ? PreferenceState::SessionOnly : PreferenceState::Ready;
        message_ = absent ? "No saved presentation setting. Beginner is the default; save a choice explicitly."
                          : dirty_ ? "Presentation changed for this session. Save this choice explicitly."
                                   : "Saved presentation setting loaded.";
    }
    void updateChoiceMessage() {
        if (!store_) { state_ = PreferenceState::NoProfile; message_ = noProfileMessage(); return; }
        if (state_ == PreferenceState::Unsupported && !pending()) {
            message_ = model_.globalLevel() == Level::Beginner
                ? "Saved presentation setting is not supported. Using Beginner for this session; saved settings are unchanged."
                : "Saved presentation setting is not supported. Using this session choice; saved settings are unchanged.";
            return;
        }
        if (pending() || state_ == PreferenceState::Conflict || !loaded_)
            return;
        state_ = dirty_ ? PreferenceState::SessionOnly : PreferenceState::Ready;
        message_ = dirty_ ? "Presentation changed for this session. Save this choice explicitly."
                         : "Presentation matches the saved setting.";
    }
    static const char* noProfileMessage() noexcept {
        return "Presentation changes are for this session. Open a local profile on Home to save them.";
    }
    void clearProposal() { pendingOperation_.clear(); pendingBytes_.clear(); }
    void resetBinding() {
        store_ = nullptr;
        profileIdentity_.clear();
        model_.resetForProfile();
        state_ = PreferenceState::NoProfile;
        message_ = noProfileMessage();
        loaded_ = supported_ = dirty_ = writing_ = reloadChoice_ = false;
        revision_ = expectedRevision_ = 0;
        savedLevel_.reset();
        clearProposal();
        activeOperation_.clear();
    }
    Model model_;
    storage::ProfileStore* store_ = nullptr;
    std::string profileIdentity_, pendingOperation_, pendingBytes_, activeOperation_;
    PreferenceState state_ = PreferenceState::NoProfile;
    std::string message_ = noProfileMessage();
    std::optional<storage::ProfileStore::Future> future_;
    std::optional<Level> savedLevel_;
    Level proposedLevel_ = Level::Beginner;
    std::int64_t revision_ = 0, expectedRevision_ = 0;
    bool loaded_ = false, supported_ = false, dirty_ = false, writing_ = false, reloadChoice_ = false;
};
} // namespace fathom::desktop::presentation
