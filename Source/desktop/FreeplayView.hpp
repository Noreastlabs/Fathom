#pragma once

#include "desktop/ActionButton.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include "practice/PracticeSession.hpp"

#include <cstdint>
#include <functional>
#include <string>

namespace fathom::desktop {

struct SharedAudioViewTestAccess;

class FreeplayView final : public juce::Component, private juce::Timer {
public:
    FreeplayView();
    ~FreeplayView() override;

    std::function<void()> onBack;
    std::function<void()> onRhythmTools;
    std::function<void()> onProgress;
    std::function<void()> onAudioSettings;

    void setReturnDestination(std::string destination){returnDestination_=std::move(destination);refresh();}
    bool startFreeplay();
    bool pauseFreeplay();
    bool stopFreeplay();
    bool retryPersistence();
    enum class CloseState { Ready, Pending, Blocked };
    // Process exit must stop a paused timer and retain its original history save;
    // ordinary navigation can leave the paused view alive through canLeave().
    void cancelExit(){if(!capture_||capture_->canLeave(true))exitDiscard_=false;}
    bool requestExit(bool discard);
    void retryExitDiscard(){if(capture_)capture_->retryExitDiscard(monotonicMilliseconds());}
    bool requestClose();
    CloseState closeState() const;
    bool requestBack();
    bool requestRhythmTools();
    bool requestProgress();
    bool requestAudioSettings();
    bool configureStore(storage::ProfileStore&, std::function<std::string()> utcNow, std::string timezone);
    void servicePersistence();
    bool active() const noexcept { return running_; }
    bool canLeave() const noexcept { return !running_ && !persistencePending_ && !persistenceBlocked_; }
    bool presentationStoppedAndResolved() const { return canLeave()&&!paused_&&(!capture_||capture_->canLeave(true)); }
    bool persistencePending() const noexcept { return persistencePending_; }
    bool persistenceSaved() const noexcept { return persistenceSaved_; }
    bool persistenceConfigured() const noexcept { return store_ != nullptr && static_cast<bool>(utcNow_); }
    std::uint64_t activeNanoseconds() const noexcept;
    std::string statusText() const { return statusDetail_; }
    std::string timerText() const { return timer_.getText().toStdString(); }
    std::uint32_t historyWriteCount() const noexcept { return historyWrites_; }
    std::string persistenceStatus() const { return persistenceStatus_; }
    void setClockForTest(std::function<std::uint64_t()> clock);

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    friend struct SharedAudioViewTestAccess;

    void timerCallback() override;
    std::uint64_t nowNanoseconds() const noexcept;
    void refresh();
    void setStatus(juce::String detail, juce::NotificationType, juce::String visible = {});
    void handleBack();
    void handleRhythmTools();
    void handleProgress();
    void handleAudioSettings();
    void beginPersistence();
    bool retrySaveAvailable() const;
    std::uint64_t stoppedFrames() const;
    bool freeplayConfiguration(capture::StartRequest& request);
    practice::Progress freeplayProgress(std::uint64_t frames) const;
    static std::int64_t monotonicMilliseconds() noexcept;
    static std::string formatDuration(std::uint64_t nanoseconds);

    juce::Label heading;
    juce::Label explanation;
    juce::Label timerCaption;
    juce::Label timer_;
    juce::Label status_;
    juce::Label profileState_;
    ActionButton startButton{"Start freeplay"};
    ActionButton pauseButton{"Pause freeplay"};
    ActionButton stopButton{"Stop freeplay"};
    ActionButton retryButton{"Retry history save"};
    ActionButton rhythmButton{"Open rhythm tools"};
    ActionButton progressButton{"Open Progress"};
    ActionButton audioButton{"Audio settings"};
    ActionButton backButton{"Back"};

    std::string returnDestination_{"Home"};
    std::function<std::uint64_t()> clock_;
    storage::ProfileStore* store_{};
    std::function<std::string()> utcNow_;
    std::string timezone_;
    std::unique_ptr<capture::PracticeSession> capture_;
    practice::Coordinator coordinator_;
    std::uint64_t commandSequence_{};
    std::uint64_t persistedNanoseconds_{};
    std::uint64_t startedNanoseconds_{};
    std::uint64_t accumulatedNanoseconds_{};
    std::uint32_t historyWrites_{};
    bool exitDiscard_{};
    bool running_{}, paused_{}, stopped_{}, persistencePending_{}, persistenceSaved_{}, persistenceBlocked_{};
    std::string persistenceStatus_;
    std::string statusDetail_;
};

}
