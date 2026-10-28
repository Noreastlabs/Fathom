#pragma once
#include "desktop/ActionButton.hpp"
#include "desktop/PreparedToolSound.hpp"
#include "desktop/SharedAudioSettings.hpp"
#include "metronome/Polyrhythm.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include "platform/AudioOutputMac.hpp"
#include <vector>

namespace fathom::desktop {
// Explicit synthetic sound-check material, never a runtime curriculum record.
std::vector<scheduler::Plan> previewPlans(scheduler::Owner, std::uint32_t rate,
                                          polyrhythm::Ratio ratio = {3, 2});
struct PreviewSound final {
    scheduler::ScheduledStream stream;
    struct Voice { std::uint64_t attack{}; bool active{}; };
    std::array<Voice,4> voices{};
    platform::Buses* buses{};
    std::uint32_t rate{};
    static scheduler::BlockOutcome render(void*,const output::Owner&,std::uint32_t,std::uint32_t,platform::Buses&) noexcept;
    static void observe(void*,const output::Snapshot&) noexcept;
    static bool consume(void*,std::uint64_t,std::uint32_t,const scheduler::Fact*,std::size_t) noexcept;
};
class SchedulerView final : public juce::Component, private juce::Timer {
public:
    SchedulerView();
    ~SchedulerView() override;
    void resized() override;
    void paint(juce::Graphics&) override;
    std::function<void()> onBack;
    void setReturnLabel(juce::String label){back.setButtonText(label);back.setTitle(label+" after Stop and Finish check release the retained preview.");updateReturnDescription();}
    std::function<void(const platform::NativeEvent&)> onNativeEvent;
    std::function<void()> onAudioSettings;
    void setAudioPolling(bool value) noexcept { audioPolling_=value; }
    bool applyCommonMix(const output::MixSettings&);
    bool audioCanRelease() const;
    bool audioCanPrepare() const { return !started&&audioCanRelease(); }
    bool audioRelease();
    bool requestClose(); // requests Stop once; retains the existing Finish check acknowledgment
    bool connectOutput(const platform::OutputCapability* expected=nullptr);
    bool enableOutput();
    bool finishCheck();
    output::Snapshot audioSnapshot() const { return output.status().lifecycle; }
    std::string audioError() const { return localError_.empty()?output.error():localError_; }
private:
    friend struct SharedAudioViewTestAccess;
    bool audioPolling_{true};
    ActionButton audioSettings_{"Audio settings"};
    juce::ComboBox ratioPreset_;
    juce::Label ratioXLabel_,ratioYLabel_;
    juce::TextEditor ratioX_,ratioY_;
    ActionButton ratioApply_{"Apply ratio"};
    juce::Label ratioMessage_;
    polyrhythm::Ratio selectedRatio_{3,2};
    int selectedRatioChoice_{2};
    output::MixSettings commonMix_;
    void timerCallback() override;
    bool send(platform::OutputCommand);
    void updateRatioDisplay();
    void updateReturnDescription();
    void stopAndRetain();
    std::unique_ptr<PreparedToolSound<PreviewSound>> sound;
    platform::OutputCapability preparedCapability_;
    std::string localError_;
    platform::AudioOutputMac output;
    scheduler::Owner owner;
    scheduler::StreamView view;
    output::Snapshot retainedOutput;
    scheduler::StreamView retainedTimeline;
    bool started{},retained{},resolving{},cancelledStart{},stopRequested{};
    ActionButton done{"Finish check"};
    juce::Label title,description,status,progress,cycleHeading,layerALabel,layerBLabel;
    std::vector<double> layerAPhases,layerBPhases;
    ActionButton connect{"Connect audio"},enable{"Enable audio"},start{"Start preview"},stop{"Stop"},tempo{"132 BPM next cycle"},back{"Back to Home"};
};
}
