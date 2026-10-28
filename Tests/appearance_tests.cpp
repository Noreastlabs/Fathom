#include "desktop/Appearance.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {
using namespace fathom::desktop;
double luminance(juce::Colour colour) {
    const auto channel = [](double value) {
        value /= 255.0;
        return value <= 0.04045 ? value / 12.92 : std::pow((value + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * channel(colour.getRed()) + 0.7152 * channel(colour.getGreen()) +
        0.0722 * channel(colour.getBlue());
}
double contrast(juce::Colour a, juce::Colour b) {
    const auto first = luminance(a), second = luminance(b);
    return (std::max(first, second) + 0.05) / (std::min(first, second) + 0.05);
}
class Surface final : public juce::Component {
    void paint(juce::Graphics& graphics) override {
        graphics.fillAll(appearance::colour(0xff10212c));
    }
};
}
int main() {
    int checks = 0;
    const auto check = [&](bool condition, const char* message) {
        ++checks;
        if (!condition) throw std::runtime_error(message);
        std::cout << "PASS\t" << message << '\n';
    };
    try {
        juce::ScopedJuceInitialiser_GUI initialise;
        using Appearance = setup::Appearance;
        for (const auto mode : {Appearance::Default, Appearance::Dark, Appearance::Light}) {
            appearance::set(mode);
            const auto surface = appearance::colour(0xff10212c);
            check(contrast(appearance::colour(0xfff0f4f6), surface) >= 4.5,
                  "primary text contrast meets 4.5 on the application surface");
            check(contrast(appearance::colour(0xffa9bbc5), surface) >= 4.5,
                  "secondary text contrast meets 4.5 on the application surface");
            check(contrast(appearance::colour(0xff6bd5cb), surface) >= 4.5,
                  "teal headings retain readable contrast and semantic hue");
            check(contrast(appearance::colour(0xffffcb77), surface) >= 4.5,
                  "amber warning and playback text retain readable contrast");
            check(contrast(appearance::colour(0xff10212c), appearance::colour(0xff6bd5cb)) >= 4.5,
                  "filled teal button text contrast meets 4.5");
            check(contrast(appearance::colour(0xff617782), surface) >= 3.0,
                  "control outline contrast meets 3 on the application surface");
            check(contrast(appearance::colour(0xfff0f4f6), appearance::colour(0xff225b62)) >= 4.5,
                  "fretboard marker text remains readable on its mapped marker surface");
            check(appearance::colour(0xff7135a8) == juce::Colour{0xff7135a8},
                  "unknown semantic colours are preserved");
            check(appearance::colour(0x0010212c) == juce::Colour{0x0010212c},
                  "fully transparent colour remains transparent and unchanged");
            check(appearance::colour(juce::Colour{0xfff6f4ef}) == juce::Colour{0xfff6f4ef} &&
                  appearance::colour(0xff182b33) == juce::Colour{0xff182b33},
                  "existing light manual panel surface and dark ink remain explicit exceptions");
        }
        for (const auto& first : appearance::detail::palette)
            for (const auto& second : appearance::detail::palette) {
                if (&first != &second && first.light == second.light)
                    throw std::runtime_error("Ambiguous Light palette reverse mapping");
                if (first.light == second.legacy)
                    throw std::runtime_error("Light palette collides with an existing legacy colour");
            }
        check(true, "all named Light targets are unique and disjoint from the original palette");

        appearance::set(Appearance::Default);
        Surface root;
        root.setSize(480, 260);
        juce::Label source;
        juce::TextButton button{"Next"};
        juce::TextButton inheritedButton{"Back"};
        juce::TextEditor editor;
        root.addAndMakeVisible(source);root.addAndMakeVisible(button);root.addAndMakeVisible(inheritedButton);root.addAndMakeVisible(editor);
        source.setBounds(20, 30, 380, 24);button.setBounds(20, 70, 120, 32);editor.setBounds(20, 120, 400, 90);
        inheritedButton.setBounds(160, 70, 120, 32);
        source.setText("Source case fg:item:000002 / exact retained instructions", juce::dontSendNotification);
        source.setColour(juce::Label::textColourId, juce::Colour{0xfff0f4f6});
        button.setColour(juce::TextButton::buttonColourId, juce::Colour{0xff6bd5cb});
        button.setColour(juce::TextButton::textColourOffId, juce::Colour{0xff10212c});
        editor.setMultiLine(true);editor.setText("Exact source spelling,\nTAB positions and original timing remain unchanged.", false);
        editor.setColour(juce::TextEditor::backgroundColourId, juce::Colour{0xff142b38});
        editor.setColour(juce::TextEditor::textColourId, juce::Colour{0xffe1edf0});
        editor.setHighlightedRegion({2, 7});
        const auto text = editor.getText();const auto selection = editor.getHighlightedRegion();
        const auto sourceBounds = source.getBounds(), buttonBounds = button.getBounds(), editorBounds = editor.getBounds();
        int actions = 0;button.onClick = [&]{++actions;};editor.onTextChange = [&]{++actions;};
        for (const auto mode : {Appearance::Default, Appearance::Light, Appearance::Light,
                                Appearance::Dark, Appearance::Default, Appearance::Light, Appearance::Default}) {
            appearance::set(mode);appearance::apply(root);
            const bool light = mode == Appearance::Light;
            check(source.findColour(juce::Label::textColourId) ==
                  (light ? juce::Colour{0xff203441} : juce::Colour{0xfff0f4f6}),
                  "existing explicit source-label ink toggles reversibly without cumulative conversion");
            check(editor.getText() == text && editor.getHighlightedRegion() == selection,
                  "mode changes preserve editor bytes and selected source range");
            check(source.getBounds() == sourceBounds && button.getBounds() == buttonBounds && editor.getBounds() == editorBounds,
                  "mode changes preserve all control geometry");
            check(actions == 0 && button.isEnabled(),
                  "mode changes invoke no user actions and preserve control eligibility");
            check(contrast(button.findColour(juce::TextButton::textColourOffId),
                           button.findColour(juce::TextButton::buttonColourId)) >= 4.5,
                  "actual existing filled-button colour IDs retain text contrast");
            check(contrast(inheritedButton.findColour(juce::TextButton::textColourOffId),
                           inheritedButton.findColour(juce::TextButton::buttonColourId)) >= 4.5,
                  "buttons without explicit colours inherit a readable current theme pair");
            juce::Image frame{juce::Image::ARGB, 480, 260, true};juce::Graphics graphics(frame);
            root.paintEntireComponent(graphics, true);
            check(frame.getPixelAt(2, 2) == (light ? juce::Colour{0xfff7fafb} : juce::Colour{0xff10212c}),
                  "actual custom paint resolves the current surface rather than a static startup colour");
        }

        appearance::set(Appearance::Light);
        juce::Label createdInLight;
        createdInLight.setColour(juce::Label::textColourId, appearance::colour(0xffd8e7eb));
        root.addAndMakeVisible(createdInLight);appearance::apply(root);
        source.setColour(juce::Label::textColourId, appearance::colour(0xffffcb77));appearance::apply(root);
        check(source.findColour(juce::Label::textColourId) == juce::Colour{0xff8a5100},
              "later warning colour replaces the original rather than restoring stale ordinary ink");
        appearance::set(Appearance::Dark);appearance::apply(root);
        check(createdInLight.findColour(juce::Label::textColourId) == juce::Colour{0xffd8e7eb},
              "a control created during Light recovers its exact legacy colour in Dark");
        check(source.findColour(juce::Label::textColourId) == juce::Colour{0xffffcb77},
              "later warning colour restores its own exact legacy value");
        juce::TextEditor whitePanel;
        whitePanel.setColour(juce::TextEditor::backgroundColourId, juce::Colours::white);
        whitePanel.setColour(juce::TextEditor::textColourId, juce::Colour{0xff182b33});
        root.addAndMakeVisible(whitePanel);appearance::set(Appearance::Light);appearance::apply(root);
        check(whitePanel.findColour(juce::TextEditor::backgroundColourId) == juce::Colours::white &&
              whitePanel.findColour(juce::TextEditor::textColourId) == juce::Colour{0xff182b33},
              "already-light manual editor white surface is never mistaken for white foreground ink");
        bool refused = false;
        try { appearance::set(static_cast<Appearance>(999)); } catch (const std::invalid_argument&) { refused = true; }
        check(refused && appearance::current() == Appearance::Light,
              "invalid appearance selection refuses without replacing the current mode");
        appearance::set(Appearance::Default);appearance::apply(root);
        std::cout << "PASS " << checks << " appearance checks; native windows=0 profiles=0 audio=0\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " appearance checks: " << error.what() << '\n';
        return 1;
    }
}
