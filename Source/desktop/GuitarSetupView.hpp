#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include "core/GuitarSetup.hpp"
#include "desktop/SetupPolicy.hpp"

namespace fathom::desktop {
class SetupButton final : public juce::TextButton {
public:
    using juce::TextButton::TextButton;
    bool keyPressed(const juce::KeyPress& key) override {
        if (key.getKeyCode() == juce::KeyPress::spaceKey || key.getKeyCode() == juce::KeyPress::returnKey) {
            triggerClick(); return true;
        }
        return juce::TextButton::keyPressed(key);
    }
};
class GuitarSetupView final : public juce::Component {
public:
    GuitarSetupView();
    const guitar::Setup& currentSetup() const noexcept { return active.current(); }
    // Draft/restore bridge only. Applying remains a guarded session-local action;
    // these methods never write preferences or claim a saved profile setting.
    bool setDraft(const guitar::Setup&);
    std::optional<guitar::Setup> draftSetup(std::string* error = nullptr) const;
    bool applySetup(const guitar::Setup&);
    void setBoardDisplay(const setup::BoardDisplay&);
    void setBoardDisplayStatus(const std::string&);
    std::function<void()> onUserApplied; // explicit Apply only; restore never arms persistence
    setup::BoardDisplay draftBoardDisplay() const;
    std::function<void(const setup::BoardDisplay&)> onBoardDisplayChanged;
    void paint(juce::Graphics&) override;
    void resized() override;
    std::function<void()> onBack, onApplied;
    std::function<bool()> canApply;
private:
    class Board final : public juce::Component {
    public:
        guitar::Setup setup;
        void paint(juce::Graphics&) override;
    } board;
    void selectPreset();
    void applyDraft();
    void acceptSetup(const guitar::Setup&, bool syncDraft);
    void showError(const std::string&);
    void refreshSummary();
    guitar::ActiveSetup active;
    juce::Label heading, explanation, tuningLabel, capoLabel, fretsLabel, handLabel, summary, status, footer;
    std::array<juce::Label,6> stringLabels;
    std::array<juce::TextEditor,6> notes;
    juce::ComboBox preset, hand, boardMode, noteSpelling;
    juce::ToggleButton boardVisible{"Show playback fretboard"};
    juce::TextEditor capo, frets;
    SetupButton apply{"Apply setup"}, back{"Back"};
};
} // namespace fathom::desktop
