#pragma once
#include "desktop/Appearance.hpp"
#include "desktop/ReadOnlyTextEditor.hpp"
#include <juce_gui_basics/juce_gui_basics.h>

namespace fathom::desktop {
// Retains Label's exact text API while making long permitted prose scrollable.
class ReadOnlyTextView final : public juce::Label {
public:
    ReadOnlyTextView() {
        // Native accessibility focuses the Label-compatible wrapper. Keep that
        // public identity, then forward reading keys to the embedded editor.
        setWantsKeyboardFocus(true);
        editor_.setMultiLine(true, true);
        editor_.setReadOnly(true);
        editor_.setScrollbarsShown(true);
        editor_.setCaretVisible(false);
        editor_.setColour(juce::TextEditor::backgroundColourId, appearance::colour(0xff10212c));
        editor_.setColour(juce::TextEditor::textColourId, appearance::colour(0xfff0f4f6));
        editor_.setColour(juce::TextEditor::outlineColourId, juce::Colours::transparentBlack);
        editor_.setWantsKeyboardFocus(true);
        addAndMakeVisible(editor_);
    }
    void setText(const juce::String& value, juce::NotificationType notification) {
        juce::Label::setText(value, notification);
        if (editor_.getText() != value) editor_.setText(value, false);
    }
    void textWasChanged() override { const auto value=juce::Label::getText();if(editor_.getText()!=value)editor_.setText(value,false); }
    void setFont(const juce::Font& font) { juce::Label::setFont(font); editor_.setFont(font); }
    void setTitle(const juce::String& title) {
        juce::Label::setTitle(title); editor_.setTitle(title);
        editor_.setDescription("Read-only complete text. Scroll to read more; no activity is started.");
    }
    void paint(juce::Graphics&) override {}
    void resized() override { editor_.setBounds(getLocalBounds()); }
    bool keyPressed(const juce::KeyPress& key) override {
        return editor_.keyPressed(key);
    }
private:
    ReadOnlyTextEditor editor_;
};
}
