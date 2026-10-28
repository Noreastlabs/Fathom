#pragma once

#include "content/LessonCatalog.hpp"
#include "desktop/ReadOnlyTextView.hpp"
#include "storage/ProfileStore.hpp"
#include <juce_gui_basics/juce_gui_basics.h>

#include <chrono>
#include <functional>
#include <optional>
#include <string>

namespace fathom::desktop {

class GuidedSessionView final : public juce::Component, private juce::Timer, private juce::KeyListener {
public:
    using Clock = std::function<std::string()>;

    GuidedSessionView();
    ~GuidedSessionView() override;

    std::function<void()> onBack;
    std::function<void()> onProgressPage;
    std::function<void()> onAudioSettings;
    std::function<bool(const std::string&, const std::string&)> onOpenLesson;

    void setNewSessionsEnabled(bool enabled){newSessionsEnabled_=enabled;refreshControls();}
    bool newSessionsEnabled()const noexcept{return newSessionsEnabled_;}
    bool configureStore(storage::ProfileStore&, Clock, std::string timezone);
    void setCatalog(std::shared_ptr<const lesson::Catalog>);
    void setCatalogLoading(bool,const std::string& message={});
    bool selectCase(const std::string& item, const std::string& variant);
    bool buildPlan();
    bool startSession();
    bool inspectOriginalStart();
    bool retryOriginalStart();
    bool stopSession();
    bool interruptSession();
    void noteSavedPracticeAttempt();
    bool requestBack();
    bool requestProgressPage();
    void service();

    bool busy() const noexcept { return future_.has_value(); }
    bool running() const noexcept { return running_; }
    bool holdsSessionOperation() const noexcept { return running_||unresolved_||closeUnresolved_||createUnresolved_||(busy()&&mutation_!=Mutation::LoadSummary); }
    bool canLeave() const noexcept { return !busy() && !running_ && !createUnresolved_ && !closeUnresolved_; }
    bool requestExit(bool discard){
        service();if(busy()||createUnresolved_)return false;
        if(discard){running_=false;if(!sessionId_.empty()&&!closed_)unresolved_=true;refreshControls();return true;} // existing Session remains open, no fabricated close
        if(running_){if(!exitStopAttempted_){exitStopAttempted_=true;stopSession();}return false;}
        return presentationStoppedAndResolved();
    }
    void cancelExit() noexcept { exitStopAttempted_=false; }
    bool canClose() const noexcept { return canLeave(); }
    bool createUnresolved() const noexcept { return createUnresolved_; }
    bool presentationStoppedAndResolved() const noexcept { return canLeave()&&!unresolved_&&!closeUnresolved_&&(sessionId_.empty()||closed_); }
    int selectedMinutes() const noexcept { return selectedMinutes_; }
    std::string statusText() const { return status_.getText().toStdString(); }
    std::string sessionSummaryText() const { return sessionSummary_.getText().toStdString(); }
    std::string planText() const { return plan_.getText().toStdString(); }
    std::string sessionId() const noexcept { return sessionId_; }

    void resized() override;
    void paint(juce::Graphics&) override;

private:
    friend struct GuidedSessionViewTestAccess;
    using juce::Component::keyPressed;
    using juce::Component::keyStateChanged;
    enum class Mutation { LoadSummary, RefreshAttempt, Create, InspectCreate, Close };
    struct CreateRequest {
        std::string operation, utc, timezone, owner, reservedOwner, errorCode, errorDetail;
        storage::Status status{storage::Status::Unresolved};
        std::int64_t seconds{};
        json::Value plan;
    };

    void timerCallback() override;
    bool keyPressed(const juce::KeyPress&,juce::Component*) override;
    bool keyStateChanged(bool,juce::Component*) override;
    bool readDuration(int& minutes, std::string& error) const;
    static std::string formatElapsed(std::chrono::steady_clock::duration);
    void refreshControls();
    void refreshStopLabel();
    void setError(const std::string&);
    std::string catalogLoadingFeedback() const;
    bool catalogFeedbackCanReplaceStatus() const;
    bool openFirstLesson();
    void adoptOriginalStart();

    bool newSessionsEnabled_{true};
    storage::ProfileStore* store_{};
    Clock utcNow_;
    std::string timezone_;
    std::shared_ptr<const lesson::Catalog> catalog_;
    bool catalogLoading_{};
    std::string catalogLoadingMessage_;
    std::optional<storage::ProfileStore::Future> future_;
    Mutation mutation_{Mutation::Create};
    std::optional<CreateRequest> originalCreate_;
    bool createUnresolved_{}, createRetryAllowed_{};
    json::Value planValue_;
    std::string sessionId_;
    std::string selectedItemId_, selectedVariantId_;
    std::string firstItemId_;
    std::string firstVariantId_;
    int selectedMinutes_{};
    std::int64_t plannedSeconds_{};
    std::int64_t lastElapsedSeconds_{};
    bool running_{}, closed_{};
    bool restoredOriginal_{};
    bool unresolved_{};
    bool closeUnresolved_{},exitStopAttempted_{};
    std::string originalCloseOperation_,originalCloseUtc_;
    bool summaryUnavailable_{};
    bool savedAttemptLinked_{};
    bool spaceHeld_{};
    std::string savedAttemptDetails_;
    std::chrono::steady_clock::time_point startedSteady_{};
    std::string outcome_;

    juce::Label heading_, explanation_, durationLabel_, customLabel_, elapsedLabel_, status_, summaryHeading_, summaryState_, planState_;
    ReadOnlyTextView sessionSummary_;
    juce::ComboBox duration_, custom_;
    juce::TextEditor plan_;
    juce::TextButton audio_{"Audio settings"}, build_{"Build plan"}, open_{"Open first practice-ready case in Learn"}, start_{"Start session"}, stop_{"Stop session"}, interrupt_{"Interrupt / leave"}, progress_{"Open Progress"}, back_{"Back"};
};

} // namespace fathom::desktop
