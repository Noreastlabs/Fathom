#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

namespace fathom::desktop {
// Pinned JUCE rejects navigation keys in read-only TextEditors. Allow only
// unmodified reading keys; editable input, Copy/Select All and Tab keep JUCE's
// existing dispatch. No text, listener callback or task action is written here.
class ReadOnlyTextEditor final : public juce::TextEditor {
public:
    using juce::TextEditor::TextEditor;
    bool keyPressed(const juce::KeyPress& key) override {
        if (isReadOnly() && key.getModifiers().isAnyModifierKeyDown() == false) {
            // JUCE scrollUp increments the scrollbar; scrollDown decrements it.
            if (key.isKeyCode(juce::KeyPress::downKey)) return scrollUp();
            if (key.isKeyCode(juce::KeyPress::upKey)) return scrollDown();
            if (key.isKeyCode(juce::KeyPress::pageDownKey)) return pageDown(false);
            if (key.isKeyCode(juce::KeyPress::pageUpKey)) return pageUp(false);
            if (key.isKeyCode(juce::KeyPress::homeKey)) {
                moveCaretToTop(false);
                // Moving to the same caret index is a JUCE no-op. Reveal it
                // again after independent arrow/scrollbar scrolling.
                scrollToMakeSureCursorIsVisible();
                return true;
            }
            if (key.isKeyCode(juce::KeyPress::endKey)) {
                moveCaretToEnd(false);
                scrollToMakeSureCursorIsVisible();
                return true;
            }
        }
        return juce::TextEditor::keyPressed(key);
    }
};
} // namespace fathom::desktop
