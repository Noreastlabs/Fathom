// Onboarding is presentation, not profile ownership. Draft edits and navigation
// callbacks request work from Main/Home; Finish is enabled only by their
// persistence/recovery gates. Back must preserve an unfinished original.
#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include "desktop/SetupPolicy.hpp"
#include "storage/ProfileNaming.hpp"
#include <array>

namespace fathom::desktop {
// Presentation only. The host owns navigation, settings pages, persistence and
// activity guards. No button in this component opens or starts an audio device.
class OnboardingView final : public juce::Component {
public:
    OnboardingView();
    void setModel(const setup::Model&);
    void setStatus(std::string);
    void setPersistenceState(bool busy, bool canFinish, std::string flags = {}, bool canReload = false, bool canOpenProfile = true, bool profileOpen = false, bool recoveryPending = false);
    setup::Step currentStep() const noexcept { return model_.step; }
    void paint(juce::Graphics&) override;
    void resized() override;

    std::function<void(setup::Model)> onModelChanged;
    std::function<void(std::string)> onProfileNameChanged;
    std::string profileName()const{return profileName_.getText().toStdString();}
    std::function<void()> onNext, onBack, onSkip, onFinish;
    std::function<void()> onOpenGuitar, onOpenAudio, onOpenLocalProfile, onResumeRecovery;
    std::function<void()> onReload;

private:
    class ActionButton final : public juce::TextButton {
    public:
        using juce::TextButton::TextButton;
        bool keyPressed(const juce::KeyPress&) override;
        bool keyStateChanged(bool) override;
    private:
        bool spaceHeld_{}, returnHeld_{};
    };
    class ChoiceButton final : public juce::ToggleButton {
    public:
        bool keyPressed(const juce::KeyPress&) override;
        bool keyStateChanged(bool) override;
    private:
        bool spaceHeld_{}, returnHeld_{};
    };
    void refresh();
    void chooseExperience(presentation::Level);
    void chooseAppearance(setup::Appearance);
    void chooseBoardDisplay();
    void invoke(const std::function<void()>&, const char* action);
    std::string guitarSummary() const;
    std::string audioSummary() const;

    setup::Model model_;
    bool profileOpen_{}, recoveryPending_{};
    bool busy_{}, canFinish_{true}, canReload_{}, canOpenProfile_{true};
    juce::TextEditor profileName_;juce::Label profileNameLabel_,profileNameHelp_;
    juce::Label progress_, title_, intro_, detail_, status_, persistence_;
    std::array<ChoiceButton, 3> choices_;
    std::array<juce::Label, 3> choiceDescriptions_;
    ChoiceButton boardVisible_;
    juce::ComboBox boardMode_, noteSpelling_;
    ActionButton back_{"Back"}, skip_{"Skip for now"}, next_{"Next"}, finish_{"Finish setup"};
    ActionButton guitar_{"Open guitar setup"}, audio_{"Open audio settings"};
    ActionButton profile_{"Open existing profile"};
    ActionButton reload_{"Reload / check save"};
};
} // namespace fathom::desktop
