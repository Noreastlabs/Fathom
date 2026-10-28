#pragma once
#include "SetupPolicy.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "storage/ProfileStore.hpp"
#include <chrono>
#include <limits>
#include <optional>

namespace fathom::desktop::setup {
enum class PreferenceState {
    NoProfile, Reading, Ready, SessionOnly, StopRequired, Saving,
    Conflict, Unsupported, Failed, Unknown
};

// UI-thread-owned draft persistence only. The caller keeps Store alive until
// canDetach(), supplies its real stopped/resolved gate, and separately confirms
// ui_presentation before marking setup complete. The two namespaces are not atomic.
class PreferencesController final {
public:
    const Model& model() const noexcept { return model_; }
    PreferenceState state() const noexcept { return state_; }
    const std::string& statusText() const noexcept { return message_; }
    const std::string& profileIdentity() const noexcept { return profileIdentity_; }
    const std::string& pendingBytes() const noexcept { return pendingBytes_; }
    const std::string& pendingOperationId() const noexcept { return pendingOperation_; }
    std::optional<std::int64_t> observedRevision() const noexcept {
        return loaded_ ? std::optional<std::int64_t>{revision_} : std::nullopt;
    }
    bool hasProfile() const noexcept { return store_ != nullptr; }
    bool dirty() const noexcept { return dirty_; }
    bool inFlight() const noexcept { return future_.has_value(); }
    bool pending() const noexcept { return inFlight() || !pendingOperation_.empty(); }
    bool canDetach() const noexcept { return !pending(); }
    bool supported() const noexcept { return loaded_ && supported_; }
    bool ready() const noexcept {
        return supported() && !pending() && state_ != PreferenceState::Conflict;
    }
    bool canSave(bool stoppedAndResolved) const noexcept {
        return store_ && supported() && dirty_ && stoppedAndResolved && !pending() &&
            revision_ < std::numeric_limits<std::int64_t>::max() && state_ != PreferenceState::Conflict;
    }
    bool attach(storage::ProfileStore& store, std::string profileIdentity) {
        if (!canDetach() || profileIdentity.empty()) return false;
        // Preserve unbound explicit choices through the initial read. Rebinding
        // an attached controller to another profile clears the old profile draft.
        const auto choice = model_;
        const bool retainChoice = !store_;
        const bool wasDirty = dirty_;
        resetBinding();
        if (retainChoice) { model_ = choice; dirty_ = wasDirty; }
        store_ = &store;
        profileIdentity_ = std::move(profileIdentity);
        return startRead(false);
    }
    bool detach() {
        if (!canDetach()) return false;
        resetBinding();
        return true;
    }
    void choose(Model choice) {
        validate(choice); // Invalid drafts never partially replace the current model.
        model_ = std::move(choice);
        const bool duringRead = future_ && !writing_;
        dirty_ = duringRead || !loaded_ || !savedModel_ || model_ != *savedModel_;
        if (duringRead) reloadChoice_ = false;
        updateChoiceMessage();
    }
    bool save(bool stoppedAndResolved) {
        if (!canSave(stoppedAndResolved)) {
            if (store_ && supported() && dirty_ && !pending() &&
                state_ != PreferenceState::Conflict && !stoppedAndResolved) {
                state_ = PreferenceState::StopRequired;
                message_ = "Setup changed for this session. Stop and resolve the current activity before saving.";
            }
            return false;
        }
        try {
            pendingBytes_ = storage::canonical(encodePreferences(model_));
            pendingOperation_ = storage::newUuid();
            expectedRevision_ = revision_;
            proposedModel_ = model_;
            activeOperation_ = pendingOperation_;
            future_.emplace(store_->compareExchangePreferences(pendingOperation_, preferenceKey,
                namespaceVersion, expectedRevision_, pendingBytes_, stoppedAndResolved));
            writing_ = true;
            state_ = PreferenceState::Saving;
            message_ = "Saving setup draft…";
            return true;
        } catch (...) {
            state_ = pendingOperation_.empty() ? PreferenceState::Failed : PreferenceState::Unknown;
            message_ = pendingOperation_.empty() ? "Setup was not saved. Retry explicitly when stopped and resolved."
                : "Setup save is not confirmed. Keep the profile open and inspect the original save.";
            return false;
        }
    }
    // Conflict: explicitly accept saved draft. Unknown: inspect only the exact
    // original proposal; a read never submits a replacement write or starts audio.
    bool reload() { return store_ && !future_ && startRead(true); }
    bool poll() {
        if (!future_ || future_->wait_for(std::chrono::milliseconds(0)) != std::future_status::ready) return false;
        const bool wasWriting = writing_;
        try {
            const auto reply = future_->get();
            future_.reset();
            writing_ = false;
            if (reply.operation != activeOperation_ || reply.owner != preferenceKey)
                throw std::runtime_error("Setup response identity mismatch");
            if (wasWriting) applyWrite(reply); else applyRead(reply);
        } catch (...) {
            future_.reset();
            writing_ = false;
            state_ = pendingOperation_.empty() ? PreferenceState::Failed : PreferenceState::Unknown;
            if (pendingOperation_.empty()) loaded_ = false;
            message_ = pendingOperation_.empty() ? "Saved setup could not be read. Reload before saving; stored bytes are unchanged."
                : "Setup save is not confirmed. Keep the profile open and inspect the original save.";
        }
        return true;
    }
private:
    static std::int64_t integer(const json::Value& value, const char* key) {
        const auto* field = value.find(key);
        std::int64_t result;
        if (!field || !field->integer(result) || result < 0) throw std::runtime_error("Invalid setup revision/version response");
        return result;
    }
    bool startRead(bool explicitReload) {
        try {
            activeOperation_ = storage::newUuid();
            future_.emplace(store_->readPreferences(activeOperation_, preferenceKey));
            writing_ = false;
            reloadChoice_ = explicitReload && pendingOperation_.empty();
            state_ = PreferenceState::Reading;
            message_ = pendingOperation_.empty() ? "Reading saved setup…"
                : "Inspecting the original setup save; no new write is being made.";
            return true;
        } catch (...) {
            state_ = pendingOperation_.empty() ? PreferenceState::Failed : PreferenceState::Unknown;
            if (pendingOperation_.empty()) loaded_ = false;
            message_ = "Saved setup could not be read. Any original save remains unresolved.";
            return false;
        }
    }
    void applyWrite(const storage::Reply& reply) {
        if (reply.status == storage::Status::Confirmed) {
            if (expectedRevision_ == std::numeric_limits<std::int64_t>::max() ||
                integer(reply.data, "revision") != expectedRevision_ + 1 ||
                integer(reply.data, "namespace_version") != namespaceVersion)
                throw std::runtime_error("Setup acknowledgment does not match the proposal");
            revision_ = expectedRevision_ + 1;
            savedModel_ = proposedModel_;
            loaded_ = supported_ = true;
            clearProposal();
            dirty_ = model_ != *savedModel_;
            state_ = dirty_ ? PreferenceState::SessionOnly : PreferenceState::Ready;
            message_ = dirty_ ? "Earlier setup draft saved. Your latest choice remains for this session; save it explicitly."
                : "Setup draft saved.";
            return;
        }
        if (reply.status == storage::Status::Unresolved || reply.status == storage::Status::DefinitelyAbsent) {
            state_ = PreferenceState::Unknown;
            message_ = "Setup save is not confirmed. Keep the profile open and inspect the original save.";
            return;
        }
        clearProposal(); // A definite no-write response alone releases the proposal.
        dirty_ = true;
        if (reply.status == storage::Status::Conflict) {
            state_ = PreferenceState::Conflict;
            message_ = "Saved setup changed elsewhere. Reload before saving again.";
        } else if (reply.status == storage::Status::Unsupported) {
            supported_ = false;
            state_ = PreferenceState::Unsupported;
            message_ = "Saved setup is unsupported. Your session draft and stored bytes are unchanged.";
        } else {
            state_ = reply.code == "STOP_REQUIRED" ? PreferenceState::StopRequired : PreferenceState::Failed;
            message_ = "Setup was not saved. This draft remains for this session; retry explicitly when stopped and resolved.";
        }
    }
    void applyRead(const storage::Reply& reply) {
        if (reply.status != storage::Status::Confirmed && reply.status != storage::Status::DefinitelyAbsent) {
            state_ = pendingOperation_.empty() ? PreferenceState::Failed : PreferenceState::Unknown;
            if (pendingOperation_.empty()) loaded_ = false;
            message_ = "Saved setup could not be read. Keep any original save and reload explicitly; stored bytes are unchanged.";
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
                throw std::runtime_error("Invalid setup read response");
            bytes = raw->string();
            applicable = applies->boolean();
        }
        if (!pendingOperation_.empty()) {
            // No preference operation journal exists. Exact next revision/bytes
            // establishes current value only, never who committed it.
            if (applicable && version == namespaceVersion &&
                expectedRevision_ < std::numeric_limits<std::int64_t>::max() &&
                revision == expectedRevision_ + 1 && bytes == pendingBytes_) {
                revision_ = revision;
                savedModel_ = proposedModel_;
                clearProposal();
                loaded_ = supported_ = true;
                dirty_ = model_ != *savedModel_;
                state_ = dirty_ ? PreferenceState::SessionOnly : PreferenceState::Ready;
                message_ = "Exact setup value confirmed at the expected next revision. Which operation saved it is not established.";
            } else {
                state_ = PreferenceState::Unknown;
                message_ = "Original setup save remains unresolved. Stored value differs or is unsupported; keep the profile open. No retry or overwrite is available.";
            }
            return;
        }
        // Decode before adopting revision/model so a malformed reply cannot
        // partially publish a supposedly ready persisted draft.
        std::optional<Model> saved;
        if (!absent && applicable && version == namespaceVersion)
            saved = decodePreferences(storage::parseCanonical(bytes));
        loaded_ = true;
        revision_ = revision;
        supported_ = applicable && version == namespaceVersion;
        savedModel_ = std::move(saved);
        if (!supported_) {
            state_ = PreferenceState::Unsupported;
            message_ = "Saved setup is unsupported. Using your current session draft; saved bytes are unchanged.";
            return;
        }
        // An absent namespace always retains current defaults/session choices,
        // including an explicit Reload. Reads never create a completion record.
        if (savedModel_ && (reloadChoice_ || !dirty_)) model_ = *savedModel_;
        dirty_ = savedModel_ ? model_ != *savedModel_ : dirty_;
        state_ = dirty_ ? PreferenceState::SessionOnly : PreferenceState::Ready;
        message_ = absent ? "No saved setup. Your current draft is for this session; save it explicitly."
            : dirty_ ? "Setup changed for this session. Save this draft explicitly." : "Saved setup draft loaded.";
    }
    void updateChoiceMessage() {
        if (!store_) { state_ = PreferenceState::NoProfile; message_ = noProfileMessage(); return; }
        if (state_ == PreferenceState::Unsupported && !pending()) {
            message_ = "Saved setup is unsupported. Using your current session draft; saved bytes are unchanged.";
            return;
        }
        if (pending() || state_ == PreferenceState::Conflict || !loaded_) return;
        state_ = dirty_ ? PreferenceState::SessionOnly : PreferenceState::Ready;
        message_ = dirty_ ? "Setup changed for this session. Save this draft explicitly." : "Setup matches the saved draft.";
    }
    static const char* noProfileMessage() noexcept {
        return "Setup choices are for this session. Open a local profile to save them.";
    }
    void clearProposal() { pendingOperation_.clear(); pendingBytes_.clear(); }
    void resetBinding() {
        store_ = nullptr;
        profileIdentity_.clear();
        model_ = Model{};
        state_ = PreferenceState::NoProfile;
        message_ = noProfileMessage();
        loaded_ = supported_ = dirty_ = writing_ = reloadChoice_ = false;
        revision_ = expectedRevision_ = 0;
        savedModel_.reset();
        clearProposal();
        activeOperation_.clear();
    }
    Model model_, proposedModel_;
    storage::ProfileStore* store_ = nullptr;
    PreferenceState state_ = PreferenceState::NoProfile;
    std::optional<storage::ProfileStore::Future> future_;
    std::optional<Model> savedModel_;
    std::string profileIdentity_, pendingOperation_, pendingBytes_, activeOperation_;
    std::string message_ = noProfileMessage();
    std::int64_t revision_ = 0, expectedRevision_ = 0;
    bool loaded_ = false, supported_ = false, dirty_ = false, writing_ = false, reloadChoice_ = false;
};
} // namespace fathom::desktop::setup
