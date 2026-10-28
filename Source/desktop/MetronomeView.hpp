#pragma once
#include "desktop/SharedAudioSettings.hpp"
#include "desktop/PresentationPolicy.hpp"
#include "desktop/ReadOnlyTextEditor.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include "platform/MetronomePlayback.hpp"
#include "metronome/MetronomePreferences.hpp"
#include "storage/ProfileStore.hpp"

namespace fathom::desktop {
// Standalone sound-check consumer. No Session/Attempt/Freeplay records are made.
class MetronomeView final : public juce::Component, private juce::Timer, private juce::KeyListener {
public:
    struct Retained { platform::MetronomeProgress progress; output::Snapshot output; bool controlDisposition{}; bool cancelledBeforeSound{}; };
    struct ManualPulseStart { scheduler::Owner owner; std::uint64_t binding{}; std::uint32_t sampleRate{}; };
    MetronomeView();
    ~MetronomeView() override;
    bool applySettings(const metronome::Settings&);
    bool applyEditors();
    bool hasPendingPatternEdits() const;
    void setReturnLabel(juce::String label){back_.setButtonText(label);back_.setTitle(label+" after the sound check and original saved-settings operation are resolved.");}
    const metronome::Settings& settings() const noexcept { return settings_; }
    bool connectOutput(const platform::OutputCapability* expected=nullptr); bool enableOutput(); bool startSound();
    bool pauseSound(); bool resumeSound(); bool stopSound();
    bool finishSound(); bool resetSound(); bool requestClose();
    std::optional<ManualPulseStart> startManualPulse(int explicitQuarterBpm);
    bool resolveManualPulse();
    bool manualTempo(int); metronome::TapResult tap(std::uint64_t gestureNs);
    bool applyTap(); bool setMix(int master,int metronome,bool mute);
    bool configureStore(storage::ProfileStore&);
    bool prepareStoreReopen(); bool rebindStore(storage::ProfileStore&);
    void storeReopenFailed(const std::string&);
    bool saveLastUsed(); bool savePreset(std::string name,std::string replaceId={});
    bool restoreLastUsed(); bool restorePreset(const std::string&);
    bool reconcilePreferences(); bool retryOriginalPreferences(); bool keepStoredPreferences();
    bool preferencesReady() const noexcept;
    bool preferencesPending() const noexcept;
    bool preferenceInFlight() const noexcept { return future_.has_value(); }
    const metronome::Preferences& preferences() const noexcept { return preferences_; }
    const std::string& preferenceMessage() const noexcept { return preferenceMessage_; }
    const std::string& preferenceOperation() const noexcept { return pendingOperation_; }
    const std::string& preferencePayload() const noexcept { return pendingBytes_; }
    std::int64_t preferenceRevision() const noexcept { return revision_; }
    const std::string& error() const noexcept { return error_; }
    const platform::MetronomeProgress& progress() const noexcept { return shown_; }
    const std::vector<Retained>& retained() const noexcept { return retained_; }
    const std::vector<platform::MetronomeSegment>& segments() const noexcept { return segments_; }
    platform::OutputStatus outputStatus() const { return output_.status(); }
    bool soundPending() const noexcept { return started_; }
    // Disclosure only: this does not apply editors, change transport or write settings.
    void setPresentationLevel(presentation::Level);
    presentation::Level presentationLevel() const noexcept { return presentationLevel_; }
    void service(); void quiesceAndRetain();
    bool keyPressed(const juce::KeyPress&) override;
    bool keyStateChanged(bool) override;
    void paint(juce::Graphics&) override; void resized() override;
    std::function<void()> onBack;
    std::function<bool()> onReopenStore;
    std::function<void(const platform::NativeEvent&)> onNativeEvent;
    std::function<void(const scheduler::Fact&)> onFact;
    std::function<void(const platform::MetronomeProgress&)> onProgress;
    std::function<void(const platform::MetronomeSegment&)> onSegment;
    std::function<void(const platform::MetronomeReply&)> onReply;
    std::function<void()> onAudioSettings;
    void setAudioPolling(bool value) noexcept { audioPolling_=value; }
    bool applyCommonMix(const output::MixSettings&);
    bool audioCanRelease() const;
    bool audioCanPrepare() const { return !started_&&audioCanRelease(); }
    bool audioRelease();
    output::Snapshot audioSnapshot() const { return outputStatus().lifecycle; }
    std::string audioError() const { return error_; }
    std::function<void(const output::MixSettings&)> onMixSelected;
private:
    friend struct SharedAudioViewTestAccess;
    bool audioPolling_{true};
    juce::TextButton audioSettings_{"Audio settings"};
    output::MixSettings commonMix_;
    friend struct MetronomeViewTestAccess; // deterministic adapter/GUI integration checks
    bool keyPressed(const juce::KeyPress&,juce::Component*) override;
    bool keyStateChanged(bool,juce::Component*) override;
    bool spaceHeld_{};
    bool send(platform::OutputCommand,const scheduler::Owner&,scheduler::Owner next={});
    bool stoppedResolved() const;
    bool writePreferences(metronome::Preferences);
    void pollPreferences(); void drain(); void refresh(); void loadEditors();
    metronome::Settings editorSettings() const;
    void refreshDisclosure(); void refreshDetails();
    juce::String preferencePrimaryText() const;
    void timerCallback() override { service(); }
    std::unique_ptr<platform::MetronomePlayback> playback_;
    platform::AudioOutputMac output_;
    metronome::Settings settings_;
    metronome::Tap tap_; metronome::TapResult tapResult_;
    scheduler::Owner owner_, pendingResume_;
    platform::MetronomeProgress shown_;
    std::vector<platform::MetronomeProgress> pendingTerminal_;
    std::vector<Retained> retained_;
    std::vector<platform::MetronomeSegment> segments_;
    std::uint64_t sequence_{}, manualCount_{}, requestedStopNs_{};
    bool started_{}, terminalJoined_{}, resolveRequested_{}, stopRequested_{}, stopQueued_{}, pendingStart_{}, cancelledCommand_{};
    std::string error_, tempoMessage_;
    storage::ProfileStore* store_{};
    enum class PrefState { Detached, Reading, Ready, Writing, Reconciling, Conflict, Unsupported, Failed };
    PrefState prefState_{PrefState::Detached};
    std::optional<storage::ProfileStore::Future> future_;
    metronome::Preferences preferences_, proposed_;
    std::vector<std::string> presetIds_;
    std::int64_t revision_{}, expectedRevision_{};
    std::string pendingOperation_,pendingBytes_,preferenceMessage_{"Presets unavailable: no explicit test profile attached."};
    bool retryProven_{},reopenPending_{};
    juce::Label title_,description_,status_,facts_,tempoStatus_,prefStatus_,profileState_;
    presentation::Level presentationLevel_{presentation::Level::Beginner};
    bool showingDetails_{};
    juce::Label presentationBadge_,patternSummary_,advancedHeading_;
    juce::ToggleButton advancedControls_{"Advanced controls"};
    juce::TextButton detailsButton_{"Instructions and Details"};
    juce::Component advancedContent_;
    juce::Viewport advancedViewport_;
    ReadOnlyTextEditor instructions_,details_;
    juce::Rectangle<int> progressBarBounds_;
    juce::String fullFacts_,fullTempoStatus_;
    std::vector<std::unique_ptr<juce::Label>> captions_;
    juce::TextEditor tempo_,numerator_,step_,every_,target_,polyX_,polyY_,manual_,presetName_;
    juce::ComboBox meter_,denominator_,subdivision_,unit_,countIn_,ramp_,presetChoice_;
    std::array<juce::ComboBox,16> styles_;
    juce::ToggleButton enabled_{"Click enabled (stopped)"},polyrhythm_{"Polyrhythm layers (X:Y)"},mute_{"Master mute"},reducedMotion_{"Reduce motion"};
    class GainSlider final : public juce::Slider {
    public: std::function<void()> onInvalidText;
    private:
        double getValueFromText(const juce::String&) override;
        double snapValue(double value,DragMode) override { if(invalidText_){invalidText_=false;return getValue();}return std::clamp(std::round(value/5.0)*5.0,0.0,100.0); }
        bool invalidText_{};
    };
    GainSlider masterGain_,clickGain_;
    juce::TextButton apply_{"Apply pattern"},connect_{"Connect audio"},enable_{"Enable audio"},start_{"Start"},pause_{"Pause"},resume_{"Resume"},stop_{"Stop"},finish_{"Finish check"},reset_{"Reset"},back_{"Back"};
    juce::TextButton tapButton_{"Tap"},applyTap_{"Apply tap"},applyManual_{"Queue BPM"};
    juce::TextButton saveLast_{"Save last used"},restoreLast_{"Restore last"},savePreset_{"New preset"},replacePreset_{"Replace selected"},restorePreset_{"Restore selected"},reconcile_{"Inspect save"},retry_{"Retry original"},keepStored_{"Keep stored"},reopen_{"Reopen test profile"};
};
}
