#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include "desktop/SharedAudioSettings.hpp"
namespace fathom::desktop {
class AudioOutputView final : public juce::Component, private juce::Timer, private juce::KeyListener {
public:
    AudioOutputView();
    ~AudioOutputView() override;
    void bind(SharedAudioSettings& session) { session_=&session;timerCallback(); }
    void setReturnLabel(const juce::String& text) { back.setButtonText(text); }
    void resized() override;
    void paint(juce::Graphics&) override;
    std::function<void()> onBack;
private:
    friend struct SharedAudioViewTestAccess;
    using juce::Component::keyPressed;
    using juce::Component::keyStateChanged;
    bool keyPressed(const juce::KeyPress&,juce::Component*) override;
    bool keyStateChanged(bool,juce::Component*) override;
    void timerCallback() override;
    void applyMix();
    SharedAudioSettings* session_{};
    bool backSpaceHeld_{};
    output::MixSettings settings;
    juce::Label title,status,description,unboundState_;
    juce::TextButton connect{"Connect audio"},enable{"Enable audio"},disconnect{"Disconnect"},back{"Back"};
    class GainSlider final:public juce::Slider {
    public: std::function<void()> onInvalidText,onValidText;
    private:
        double getValueFromText(const juce::String&) override;
        double snapValue(double value,DragMode) override { if(invalid_){invalid_=false;return getValue();}return value; }
        bool invalid_{};
    };
    std::string validationMessage_;
    std::array<GainSlider,5> gains;
    std::array<juce::Label,5> labels;
    std::array<juce::ToggleButton,5> mutes;
    std::array<juce::ToggleButton,2> solos;
};
}
