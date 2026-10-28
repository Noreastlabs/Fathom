#pragma once

#include <juce_gui_basics/juce_gui_basics.h>

namespace fathom::desktop {

// Use the existing button click path for focused desktop keyboard activation.
class ActionButton final : public juce::TextButton {
public:
    using juce::TextButton::TextButton;

    bool keyPressed(const juce::KeyPress& key) override {
        if (key.getKeyCode() == juce::KeyPress::spaceKey || key.getKeyCode() == juce::KeyPress::returnKey) {
            if (isEnabled()) internalClickCallback(juce::ModifierKeys::getCurrentModifiersRealtime());
            return true;
        }
        return juce::TextButton::keyPressed(key);
    }
};

} // namespace fathom::desktop
