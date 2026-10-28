#include "desktop/Appearance.hpp"
#include "desktop/ProgressView.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "desktop/DiagnosticText.hpp"
#include <algorithm>

namespace fathom::desktop {
ProgressView::ProgressView() {
    setComponentID("progress");
    title_.setText(juce::String::fromUTF8("PROGRESS — SAVED LOCAL ACTIVITY"), juce::dontSendNotification);
    title_.setTitle("Read-only Progress: saved local activity and separate Freeplay history; no curriculum credit.");
    title_.setFont(juce::FontOptions{30.0f, juce::Font::bold});
    status_.setFont(juce::FontOptions{16.0f});
    status_.setComponentID("progress-status");
    status_.setTitle("Read-only Progress status and next action.");
    status_.setText("Opening Progress never creates activity. Attach a local profile to view saved practice. Progress is read-only and does not award curriculum credit. For a disposable Development Preview profile, launch with --capture-preview <new private directory> <IANA timezone>. Refresh reads finalized local activity; Freeplay history appears separately after its save is confirmed.", juce::dontSendNotification);
    emptyState_.setComponentID("progress-empty-state");
    emptyState_.setTitle("Progress empty-state heading.");
    emptyState_.setFont(juce::FontOptions{20.0f, juce::Font::bold});
    emptyState_.setText("No saved activity loaded yet", juce::dontSendNotification);
    emptyState_.setColour(juce::Label::textColourId, appearance::colour(0xffe1edf0));
    emptyNextAction_.setComponentID("progress-empty-next-action");
    emptyNextAction_.setTitle("Progress empty-state next action.");
    emptyNextAction_.setFont(juce::FontOptions{15.0f});
    emptyNextAction_.setText("Choose an admitted case in Learn, save a Practice result, then review it here.", juce::dontSendNotification);
    emptyNextAction_.setColour(juce::Label::textColourId, appearance::colour(0xffb7c9d2));
    body_.setMultiLine(true); body_.setReadOnly(true); body_.setScrollbarsShown(true);
    body_.setFont(juce::FontOptions{17.0f}); body_.setTitle("Read-only saved local activity, source identity and rule-comparison state.");
    body_.setComponentID("progress-body");
    body_.setColour(juce::TextEditor::backgroundColourId, appearance::colour(0xff142b38));
    body_.setColour(juce::TextEditor::textColourId, appearance::colour(0xffe1edf0));
    back_.setComponentID("progress-back"); refresh_.setComponentID("progress-refresh"); reopen_.setComponentID("progress-reopen"); learn_.setComponentID("progress-learn");
    audio_.setComponentID("progress-audio-settings"); details_.setComponentID("progress-details");
    for (auto* c : std::initializer_list<juce::Component*>{&title_, &status_, &emptyState_, &emptyNextAction_, &body_, &back_, &refresh_, &reopen_, &learn_, &audio_, &details_}) addAndMakeVisible(c);
    auto configureControl=[&](juce::Component& component,const char* title,int order){component.setTitle(title);component.setWantsKeyboardFocus(true);component.setExplicitFocusOrder(order);};
    configureControl(back_,"Return to Home without changing read-only Progress.",1);
    back_.setColour(juce::TextButton::buttonColourId, appearance::colour(0xff6bd5cb));
    back_.setColour(juce::TextButton::textColourOffId, appearance::colour(0xff10212c));
    back_.setColour(juce::TextButton::textColourOnId, appearance::colour(0xff10212c));
    configureControl(refresh_,"Read the current saved local snapshot without creating activity.",2);
    refresh_.setColour(juce::TextButton::buttonColourId, appearance::colour(0xff6bd5cb));
    refresh_.setColour(juce::TextButton::textColourOffId, appearance::colour(0xff10212c));
    refresh_.setColour(juce::TextButton::textColourOnId, appearance::colour(0xff10212c));
    configureControl(reopen_,"Reopen the same local profile without replacing saved history.",3);
    reopen_.setColour(juce::TextButton::buttonColourId, appearance::colour(0xff6bd5cb));
    reopen_.setColour(juce::TextButton::textColourOffId, appearance::colour(0xff10212c));
    reopen_.setColour(juce::TextButton::textColourOnId, appearance::colour(0xff10212c));
    configureControl(learn_,"Open Learn to choose an admitted source-backed case.",4);
    learn_.setColour(juce::TextButton::buttonColourId, appearance::colour(0xff6bd5cb));
    learn_.setColour(juce::TextButton::textColourOffId, appearance::colour(0xff10212c));
    learn_.setColour(juce::TextButton::textColourOnId, appearance::colour(0xff10212c));
    configureControl(audio_,"Open shared Audio settings without changing Progress.",5);
    audio_.setColour(juce::TextButton::buttonColourId, appearance::colour(0xff6bd5cb));
    audio_.setColour(juce::TextButton::textColourOffId, appearance::colour(0xff10212c));
    audio_.setColour(juce::TextButton::textColourOnId, appearance::colour(0xff10212c));
    configureControl(details_,"Show or hide retained read-only saved details.",6);
    details_.setColour(juce::TextButton::buttonColourId, appearance::colour(0xff6bd5cb));
    details_.setColour(juce::TextButton::textColourOffId, appearance::colour(0xff10212c));
    details_.setColour(juce::TextButton::textColourOnId, appearance::colour(0xff10212c));
    back_.onClick = [this] {
        if (onBack) { onBack(); return; }
        status_.setText("Back is unavailable from Progress until the existing Home navigation is connected. The current read-only Progress view remains here; no activity, Attempt or curriculum credit was changed. Next action: reconnect the existing Home navigation, then choose Back.", juce::dontSendNotification);
        updateControls();
    };
    learn_.onClick = [this] {
        if (onLearn) { onLearn(); return; }
        status_.setText("Learn is unavailable from Progress until the existing Learn navigation is connected. The current read-only Progress view remains here; no activity, Attempt or curriculum credit was changed. Next action: reconnect the existing Learn navigation, then choose practice in Learn.", juce::dontSendNotification);
        updateControls();
    };
    audio_.onClick = [this] {
        if (reopening_) return;
        if (onAudioSettings) { onAudioSettings(); return; }
        status_.setText("Audio settings are unavailable from Progress until the existing shared Audio destination is connected. The current read-only Progress view remains here; no activity, Attempt, sound or curriculum credit was changed. Next action: reconnect the existing shared Audio destination, then choose Audio settings.", juce::dontSendNotification);
        updateControls();
    };
    refresh_.onClick = [this] { refresh(); };
    reopen_.onClick = [this] {
        if (busy() || reopening_) return;
        const auto previous = statusText();
        if (!onReopen || !onReopen()) {
            if (statusText() == previous)
                status_.setText("Profile reopen could not begin. Finish the current read or activity, then retry." + olderSnapshot(), juce::dontSendNotification);
        }
    };
    details_.onClick = [this] { detailsShown_ = !detailsShown_; showBody(); };
    showBody(); updateControls(); startTimer(20);
}
ProgressView::~ProgressView() { stopTimer(); }
bool ProgressView::bind(storage::ProfileStore& store, Clock clock) {
    if (busy() || !clock) return false;
    ++generation_; store_ = &store; clock_ = std::move(clock); reopening_ = false;
    status_.setText("Progress is read-only; Refresh reads saved facts and does not create activity. Freeplay history appears separately after its save is confirmed. Next action: choose Refresh to load the current saved snapshot." + olderSnapshot(), juce::dontSendNotification);
    showBody(); updateControls(); return true;
}
bool ProgressView::detach() {
    if (busy() || reopening_) return false;
    ++generation_; store_ = nullptr; clock_ = {}; reopening_ = true;
    status_.setText("Profile is reopening. Saved history is not replaced." + olderSnapshot(), juce::dontSendNotification);
    showBody(); updateControls(); return true;
}
void ProgressView::unavailable(const std::string& error) {
    reopening_ = false;
    status_.setText("Profile unavailable: " + diagnosticField(error, 1024) + olderSnapshot()
                        + " Choose Reopen profile to retry attaching the same local profile.",
                    juce::dontSendNotification);
    updateControls();
}
bool ProgressView::refresh() {
    if (busy() || !store_ || !clock_) return false;
    try {
        const auto at = clock_(); progression::utcMicros(at);
        operation_ = "progress-view/" + storage::newUuid();
        // Submit only after the worker exists. A failed thread launch must not
        // leave an untracked Store operation behind on the message thread.
        auto* source = store_;
        const auto generation = generation_; const auto operation = operation_; const auto catalog = catalog_;
        const auto expectedProfile = expectedProfile_;
        future_ = std::async(std::launch::async, [source, generation, operation, at, catalog, expectedProfile]() {
            ReadResult result; result.generation = generation; result.operation = operation;
            try {
                const auto reply = source->snapshot(operation).get();
                if (reply.operation != operation) throw progression::HistoryError("Snapshot operation identity changed");
                result.data = presentProgress(reply, at, catalog);
                if (!expectedProfile.empty() && result.data.projection.find("profile_id")->string() != expectedProfile)
                    throw progression::HistoryError("The snapshot is not the original attached profile");
            } catch (const std::exception& error) { result.error = error.what(); }
            return result;
        });
        status_.setText(data_.projection.null() ? "Reading saved practice..." : "Refreshing. The previous snapshot remains below until this read completes.", juce::dontSendNotification);
        updateControls(); return true;
    } catch (const std::exception& error) { unavailable(error.what()); return false; }
}
void ProgressView::service() {
    if (!busy() || future_.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return;
    auto result = future_.get();
    if (result.generation != generation_ || result.operation != operation_) {
        unavailable("An old read was refused; refresh the attached profile."); return;
    }
    if (!result.error.empty()) {
        std::string message = "Could not refresh: " + diagnosticField(result.error, 1024);
        if (!data_.projection.null()) message += "\nShowing the previous snapshot from " + data_.projection.find("as_of")->string() + ".";
        message += " Choose Refresh to retry reading the attached profile.";
        status_.setText(message, juce::dontSendNotification);
    } else {
        data_ = std::move(result.data);
        expectedProfile_ = data_.projection.find("profile_id")->string();
        const auto asOf = data_.projection.find("as_of")->string();
        const bool emptySnapshot = data_.text.find("No finalized practice activity in this snapshot.") != std::string::npos;
        const auto status = emptySnapshot
            ? "Saved snapshot as of " + asOf + " contains no finalized practice activity in this snapshot. Progress remains read-only and does not award curriculum credit. Next action: choose an admitted source-backed case in Learn, complete explicit Practice, then use Save result to review a new local record here."
            : "Saved snapshot as of " + asOf + ". Refresh to include later changes. Finalized local activity remains read-only; this view does not award curriculum credit. Details expands the retained read-only view; Choose practice in Learn to create a new local record. Next action: choose Show saved details for the retained read-only view, or choose practice in Learn to create a new local record.";
        status_.setText(juce::String::fromUTF8(status.c_str()), juce::dontSendNotification);
        showBody();
    }
    updateControls();
}
void ProgressView::showBody() {
    const bool emptySnapshot = data_.projection.null()
        || data_.text.find("No finalized practice activity in this snapshot.") != std::string::npos;
    emptyState_.setVisible(emptySnapshot);
    emptyState_.setText(data_.projection.null() ? "No saved activity loaded yet" : "No saved activity yet", juce::dontSendNotification);
    emptyNextAction_.setVisible(emptySnapshot);
    emptyNextAction_.setText("Choose an admitted case in Learn, save a Practice result, then review it here.", juce::dontSendNotification);
    const auto content = data_.text.empty()
        ? std::string{"No Progress snapshot is loaded yet.\nChoose Refresh to read finalized local activity. To create a local record, choose an admitted source-backed case in Learn, complete the explicit Practice action and use Save result. Progress is read-only and does not create activity or curriculum credit."}
        : (detailsShown_ ? data_.details : data_.text);
    body_.setText(juce::String::fromUTF8(content.c_str()), false);
    details_.setButtonText(detailsShown_ ? "Hide saved details" : "Show saved details");
    details_.setTitle(data_.projection.null()
        ? "Saved details are unavailable until a Progress snapshot is loaded."
        : detailsShown_ ? "Hide retained read-only saved details."
                        : "Show retained read-only saved details.");
}
std::string ProgressView::olderSnapshot() const {
    return data_.projection.null() ? "" : "\nShowing the previous snapshot from " + data_.projection.find("as_of")->string() + ".";
}
void ProgressView::updateControls() {
    refresh_.setEnabled(store_ && !busy() && !reopening_);
    reopen_.setEnabled(bool(onReopen) && !busy() && !reopening_);
    audio_.setEnabled(!reopening_);
    details_.setEnabled(!data_.projection.null());
    back_.setTitle(data_.projection.null() ? "Return to Home without changing read-only Progress." : "Return to Home after reviewing saved local activity; Progress remains read-only.");
}
void ProgressView::paint(juce::Graphics& g) { g.fillAll(appearance::colour(0xff10212c)); }
void ProgressView::resized() {
    if (getWidth() < 800) {
        const auto width = std::max(1, getWidth() - 48);
        if (title_.getText().startsWith("PROGRESS")
            && title_.getText().contains("SAVED LOCAL ACTIVITY"))
            title_.setText(juce::String::fromUTF8("Progress — Saved local activity"), juce::dontSendNotification);
        title_.setBounds(24, 16, 430, 40); back_.setBounds(470, 18, 146, 34);
        status_.setBounds(24, 66, width, 112); emptyState_.setBounds(24, 184, width, 28); emptyNextAction_.setBounds(24, 214, width, 28); body_.setBounds(24, 248, width, 240);
        refresh_.setBounds(24, 504, 110, 34); reopen_.setBounds(146, 504, 132, 34);
        learn_.setBounds(290, 504, 150, 34); audio_.setBounds(452, 504, 140, 34); details_.setBounds(24, 548, 150, 34);
        return;
    }
    if (title_.getText().startsWith("Progress")
        && title_.getText().contains("Saved local activity"))
        title_.setText(juce::String::fromUTF8("PROGRESS — SAVED LOCAL ACTIVITY"), juce::dontSendNotification);
    title_.setBounds(28, 20, getWidth() - 170, 42); back_.setBounds(getWidth() - 128, 24, 100, 34);
    status_.setBounds(28, 72, getWidth() - 56, 116); emptyState_.setBounds(28, 194, getWidth() - 56, 28); emptyNextAction_.setBounds(28, 226, getWidth() - 56, 24); body_.setBounds(28, 256, getWidth() - 56, getHeight() - 334);
    refresh_.setBounds(28, getHeight() - 58, 100, 34); reopen_.setBounds(140, getHeight() - 58, 160, 34);
    learn_.setBounds(312, getHeight() - 58, 240, 34); audio_.setBounds(560, getHeight() - 58, 180, 34); details_.setBounds(getWidth() - 150, getHeight() - 58, 122, 34);
}
}
