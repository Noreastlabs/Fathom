#pragma once
#include "desktop/ActionButton.hpp"
#include "desktop/PreparedToolSound.hpp"
#include "desktop/SharedAudioSettings.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include "platform/ReferencePlayback.hpp"
#include "desktop/GuitarSetupView.hpp"
#include "desktop/ReferenceStatusView.hpp"

namespace fathom::desktop {
class ReferenceView final:public juce::Component,private juce::Timer {
public:
    ReferenceView();
    ~ReferenceView() override;
    ReferenceStatusView& toneStatusView() noexcept {return status_;}
    std::string displayedPitch()const{return pitch_.getText().toStdString();}
    output::Snapshot outputSnapshot()const{return output_.status().lifecycle;}
    void setSetup(const guitar::Setup&); // enter only after prior tool outcome acknowledged
    void paint(juce::Graphics&) override;
    void resized() override;
    std::function<void()> onBack;
    std::function<void(const platform::NativeEvent&)> onNativeEvent;
    std::function<void()> onAudioSettings;
    void setAudioPolling(bool value) noexcept { audioPolling_=value; }
    bool applyCommonMix(const output::MixSettings&);
    bool audioCanRelease() const;
    bool audioCanPrepare() const { return !started_&&audioCanRelease(); }
    bool audioRelease();
    bool requestClose(); // requests Stop once; retains the existing Done acknowledgment
    bool connectOutput(const platform::OutputCapability* expected=nullptr);
    bool enableOutput();
    output::Snapshot audioSnapshot() const { return outputSnapshot(); }
    std::string audioError() const { return localError_.empty()?output_.error():localError_; }
private:
    friend struct SharedAudioViewTestAccess;
    bool audioPolling_{true};
    ActionButton audioSettings_{"Audio settings"};
    output::MixSettings commonMix_;
    void timerCallback() override;
    void updatePitch();
    void refreshGuidance(const output::Snapshot&);
    bool command(platform::OutputCommand);
    void finishTool();
    void leaveIdle();
    bool closeUnowned(); // disconnect flush must precede provider destruction
    guitar::Setup setup_;
    std::unique_ptr<PreparedToolSound<platform::ReferencePlayback>> playback_;
    platform::OutputCapability preparedCapability_;
    platform::AudioOutputMac output_;
    scheduler::Owner owner_;
    output::Snapshot retained_;
    scheduler::StreamView view_;
    bool started_{}, resolving_{}, stopWhenRunning_{}, cancelledStart_{}, closeStopRequested_{};
    std::string localError_;
    std::uint64_t generation_{};
    juce::Label title_,description_,pitch_,facts_,idleState_;
    ReferenceStatusView status_;
    juce::ComboBox string_,target_,method_;
    SetupButton connect_{"Connect audio"},enable_{"Enable audio"},play_{"Play tone"},stop_{"Stop"},done_{"Finish tone"},back_{"Back"};
};
}
