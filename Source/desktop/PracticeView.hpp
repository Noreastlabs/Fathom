#pragma once
#include "desktop/PresentationSelector.hpp"
#include "desktop/SharedAudioSettings.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include "platform/PracticePlayback.hpp"
#include "core/TabPlayback.hpp"
#include "desktop/TabView.hpp"
#include "desktop/PlaybackFretboardView.hpp"
#include "desktop/SetupPolicy.hpp"
#include "practice/PracticeSession.hpp"
#include "practice/LessonAttempt.hpp"
#include "desktop/LessonSetupNotice.hpp"
#include "desktop/PracticeCommands.hpp"
#include "desktop/PracticeKeyboardMac.hpp"
#include "desktop/PracticeStatusView.hpp"
#include "desktop/ReadOnlyTextView.hpp"

namespace fathom::desktop {
class PracticeView final : public juce::Component,private juce::Timer {
public:
    PracticeView();
    std::function<void(std::optional<presentation::Level>)> onPresentationChoice;
    void setPresentation(presentation::Level global,std::optional<presentation::Level> pageOverride){const auto level=pageOverride.value_or(global);presentation::validateLevel(level);presentationSelector_.display(global,pageOverride);presentationLevel_=level;refreshFocusFacts();}

    ~PracticeView() override;
    void setBoardDisplay(const setup::BoardDisplay&);
    const setup::BoardDisplay& boardDisplay() const noexcept { return boardDisplay_; }
    void setBoardDisplayStatus(const std::string&);
    std::function<void(const setup::BoardDisplay&)> onBoardDisplayChanged;
    PlaybackFretboardView& playbackFretboardView() noexcept { return playbackBoard_; }
    void visibilityChanged() override;
    static std::vector<PlaybackFretboardView::ActiveTone> soundingTonesAt(
        const music::ValidatedModel&,const practice::Timeline&,std::uint64_t cycle,std::uint64_t acceptedSample);
    std::vector<juce::Rectangle<int>> boardControlBounds() const { return {boardToggle_.getBounds(),boardMode_.getBounds(),boardSpelling_.getBounds(),boardDisplayStatus_.getBounds()}; }
    juce::Rectangle<int> boardBounds() const { return playbackBoard_.getBounds(); }
    void showTab(bool);
    void setFocusMode(bool);
    bool focusMode() const noexcept { return focusMode_; }
    bool performCommand(PracticeCommand);
    bool canPerformCommand(PracticeCommand) const;
    std::string commandFeedback() const { return commandFeedback_.getText().toStdString(); }
    PracticeStatusView& saveStatusView() noexcept { return captureStatus_; }
    std::string focusFacts() const { return focusFacts_.getText().toStdString(); }
    std::function<void(PracticeCommand,bool,const std::string&)> onPracticeCommand;
    std::function<void(const PracticeKeyObservation&)> onKeyObservation;
    bool tabVisible() const noexcept { return tabMode_; }
    TabView& tabView() noexcept { return tabView_; }
    const tab::PlaybackPosition& tabPosition() const noexcept { return tabPlayback_.position(); }
    std::function<void(const tab::PlaybackPosition&)> onTabProgress;
    bool connectOutput(const platform::OutputCapability* expected=nullptr);
    bool enableOutput();
    // Optional enclosing Session coordinator guard. Cleanup and internal Again
    // restoration remain available; an empty guard preserves existing callers.
    std::function<bool()> canStartNewCapture;
    bool startSample();
    bool pauseSample();
    bool resumeSample();
    bool stopSample();
    bool configureCapture(storage::ProfileStore&,std::string existingSession,
                          std::function<std::string()> utcNow,std::string timezone);
    bool rebindCaptureSession(std::string existingSession);
    const std::string& captureSessionId() const noexcept { return sessionId_; }
    bool configureLesson(std::shared_ptr<const lesson::Admission>,std::uint16_t selectedBpm,const guitar::Setup& declared=guitar::Setup{});
    bool updateDeclaredSetup(const guitar::Setup&);
    bool setLessonBeatClick(bool);
    bool setLessonScheduledPasses(std::uint64_t);
    bool setLessonRamp(std::optional<metronome::Ramp>);
    bool requestLessonTempo(int);
    const std::optional<metronome::Ramp>& lessonRamp() const noexcept { return initialRamp_; }
    std::string tempoFacts() const;
    std::function<void(const platform::PracticeTempoEvidence&)> onTempoProgress;
    std::function<void(const platform::PracticeTempoReply&)> onTempoReply;
    std::uint64_t lessonScheduledPasses() const noexcept { return config_.targetCycles; }
    bool lessonBeatClick() const noexcept {return beatClick_;}
    const std::shared_ptr<const lesson::Admission>& lessonAdmission() const noexcept { return lesson_; }
    void setSuiteMode(bool enabled) { suiteMode_=enabled; refreshDisplay(); }
    bool suiteMode() const noexcept { return suiteMode_; }
    bool suiteNaturalCompleted() const;
    bool saveSample(json::Value explicitAssessment = nullptr);
    bool chooseAssessment(json::Value);
    bool saveSelectedAssessment();
    bool retrySave();
    bool againSample();
    bool requestMetronome();
    bool requestProgressPage();
    void cancelExit(){if(!exitDiscard_)exitRequested_=false;}
    bool requestExit(bool discard);
    void retryExitDiscard(){if(capture_)capture_->retryExitDiscard(static_cast<std::int64_t>(platform::monotonicNs()/1000000));}
    bool requestClose(); // false retains the visible unresolved outcome
    const capture::PracticeSession* captureSession()const noexcept{return capture_.get();}
    void quiesceAndRetain(); // flush callback before final evidence inspection/destruction
    const practice::Coordinator& coordinator() const noexcept {return coordinator_;}
    platform::OutputStatus outputStatus() const {return output_.status();}
    const std::string& error() const noexcept {return error_;}
    void setReturnDestination(const std::string& destination){
        back_.setButtonText("Back to "+juce::String::fromUTF8(destination.c_str()));
        back_.setTitle("Return to "+juce::String::fromUTF8(destination.c_str())+" after the existing result-resolution gate; the original result is retained.");
        if(destination=="Guided")description_.setText(description_.getText().replace("Back returns to Learn to change the source case.","Back returns to the original Guided Session; source changes remain explicit."),juce::dontSendNotification);
    }
    void cancelReturnForNavigation(){if(returnAfterSave_||returnPosted_||requestedReturn_)stayHere();}
    std::function<void()> onBack;
    void setGuidedSummaryAction(std::function<void()> action) { onGuidedSummary = action; refreshDisplay(); }
    std::function<void()> onProgressPage;
    std::function<void()> onMetronome;
    std::function<void(const practice::Progress&)> onProgress;
    std::function<void(const platform::NativeEvent&)> onNativeEvent;
    std::function<void(const scheduler::Fact&)> onScheduledFact;
    bool keyPressed(const juce::KeyPress&) override;
    void paint(juce::Graphics&) override;
    void resized() override;
    std::function<void()> onAudioSettings;
    void setAudioPolling(bool value) noexcept { audioPolling_=value; }
    bool applyCommonMix(const output::MixSettings&);
    bool audioCanRelease() const;
    bool audioCanPrepare() const { return !started_&&audioCanRelease(); }
    bool audioRelease();
    void visitAudioSettings();
    std::function<void()> onAudioPreparation;
    output::Snapshot audioSnapshot() const { return outputStatus().lifecycle; }
    std::string audioError() const { return error_; }
private:
    PresentationSelector presentationSelector_;
    presentation::Level presentationLevel_{presentation::Level::Beginner};
    friend struct SharedAudioViewTestAccess;
    bool audioPolling_{true};
    juce::TextButton audioSettings_{"Audio settings"};
    output::MixSettings commonMix_;
    friend struct PracticeViewTestAccess;
    friend struct LessonTempoViewTestAccess;
    bool retainReturnRequest();
    void requestBack();
    void saveAndBack();
    void retryAndBack();
    void stayHere();
    void serviceReturn();
    void queueReturn();
    void presentReturn();
    void haltReturn();
    bool canReturn() const;
    bool returnPanel_{}, returnAfterSave_{}, returnPosted_{}, returnFailed_{};
    std::uint64_t returnGeneration_{};
    std::string audioDeviceName_;
    juce::Label returnStatus_, audioHelp_;
    juce::TextButton saveBack_{"Save & go back"}, retryBack_{"Retry & go back"}, stay_{"Stay"};
    bool send(platform::OutputCommand,const scheduler::Owner&,scheduler::Owner next={});
    void timerCallback() override;
    void drain();
    bool exitRequested_{},exitDiscard_{};
    void serviceCapture();
    bool outputCleared()const;
    void showCaptureStatus();
    void showSaveDetails();
    void refreshFocusFacts();
    void refreshLessonHeading();
    void applyFocusTextScale();
    void refreshDisplay();
    void showTempoControls(bool);
    void refreshTempoControls();
    bool canSelectTempo() const;
    bool canRequestTempo() const;
    void resetTempoEditors();
    void layoutTempoControls();
    void showSetupDetails(bool);
    bool hasCurrentAttempt()const;
    bool preparePlayback(const practice::Coordinator&,std::uint64_t remaining);
    std::unique_ptr<PracticeKeyboardMac> keyboard_;
    juce::Point<int> beforeFocusScroll_;
    bool focusMode_{},beforeFocusTab_{};
    juce::TextButton focus_{"Focus [F]"},clean_{"Clean [C]"};
    ReadOnlyTextView focusFacts_;
    juce::Label commandFeedback_,shortcutHelp_;
    void clearBoardHighlight();
    void refreshBoardVisibility();
    void layoutBoardOffControls();
    bool layoutBoardOn();
    setup::BoardDisplay boardDisplay_;
    PlaybackFretboardView playbackBoard_;
    juce::TextButton boardToggle_{"Fretboard: Off"};
    juce::ComboBox boardMode_, boardSpelling_;
    juce::Label boardDisplayStatus_;
    bool boardAcceptOutput_{},boardLayoutActive_{};
    TabView tabView_;
    tab::Playback tabPlayback_;
    bool tabMode_{};
    juce::TextButton tabModeButton_{"TAB"};
    platform::PracticePlayback playback_;
    platform::AudioOutputMac output_;
    practice::Coordinator coordinator_;
    std::unique_ptr<capture::PracticeSession> capture_;
    std::string sessionId_,timezone_;
    std::function<std::string()> utcNow_;
    std::shared_ptr<const music::ValidatedModel> model_;
    std::shared_ptr<const lesson::Admission> lesson_;
    std::string lessonLabel_,lessonCaption_;
    bool beatClick_{};
    juce::ComboBox scheduledPasses_;
    juce::TextButton beatClickButton_{"Beat click: Off"};
    static constexpr std::uint64_t lessonTempoBinding=1;
    std::optional<metronome::Ramp> initialRamp_;
    std::optional<platform::PracticeTempoEvidence> tempoEvidence_;
    std::optional<int> requestedTempo_;
    scheduler::Owner tempoRequestOwner_;
    std::uint64_t tempoRequestSequence_{};
    bool tempoAwaitingReply_{},tempoPanelOpen_{};
    juce::Component tempoPanel_;
    juce::TextButton tempoButton_{"Tempo"},applyRamp_{"Apply initial ramp"},applyTempo_{"At next span boundary"};
    juce::ComboBox rampDirection_,rampStep_,rampEvery_,rampTarget_,manualTempo_;
    juce::Label tempoHelp_;
    json::Value declaredSetup_;
    juce::Label setupSummary_;
    std::string setupPrimaryNotice_;
    juce::TextEditor setupDetails_;
    juce::TextButton setupButton_{"Setup details"};
    bool setupDetailsVisible_{};
    practice::Configuration config_;
    practice::Progress shown_;
    std::uint64_t sequence_{};
    bool started_{},stopRequested_{},resolveRequested_{};
    bool suiteMode_{};
    std::uint64_t lastStopRequestNs_{};
    std::string error_;
    std::optional<capture::Outcome> terminalOutcome_;
    juce::Label title_,emptySourceState_,status_,facts_;
    ReadOnlyTextView description_;
    juce::ComboBox assessment_;
    PracticeStatusView captureStatus_;
    juce::TextButton save_{"Save result"},retry_{"Retry original"},again_{"Again"};
    juce::TextButton connect_{"Connect audio"},enable_{"Enable audio"},start_{"Start sample"},pause_{"Pause"},resume_{"Resume"},stop_{"Stop"},back_{"Back"};
    juce::TextButton guidedSummary_{"Guided summary"};
    juce::TextButton openProgress_{"Open Progress"};
    juce::TextButton metronomeButton_{"Open metronome"};
    std::function<void()> onGuidedSummary;
    std::function<void()> requestedReturn_;
};
}
