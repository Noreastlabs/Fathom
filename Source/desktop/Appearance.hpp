#pragma once
#include "desktop/SetupPolicy.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include <array>
#include <cstdint>
#include <stdexcept>

namespace fathom::desktop::appearance {
// Appearance is presentation only. Default preserves the existing Fathom
// palette; Dark is an explicit choice of that same palette, not an OS setting.
// Call set/apply on the message thread. This owner never changes content,
// control values, transport, admission, profile data or window geometry.
inline setup::Appearance selected = setup::Appearance::Default;
inline setup::Appearance current() noexcept { return selected; }
inline void set(setup::Appearance value) {
    if (value != setup::Appearance::Default && value != setup::Appearance::Light &&
        value != setup::Appearance::Dark) throw std::invalid_argument("Unsupported appearance");
    selected = value;
}

namespace detail {
struct Pair { std::uint32_t legacy, light; };
// Named existing dark UI palette only. Already-light manual form/procedure
// surfaces (fff6f4ef/fff3f6f7/white), their dark ink (ff182b33/ff586b73),
// unknown colours and transparent values are preserved rather than inverted.
// Teal selection and amber playback/warnings keep their semantic hue/order.
inline constexpr std::array<Pair, 28> palette{{
    {0xff10212c, 0xfff7fafb}, {0xff172e3b, 0xffeef3f6},
    {0xff142b38, 0xffedf3f5}, {0xff172f3c, 0xffeaf1f3},
    {0xff142833, 0xfff0f5f7}, {0xff162d39, 0xffe9f1f5},
    {0xff225b62, 0xffd4e8e5}, {0xff254a59, 0xffd7e9e6},
    {0xff29404d, 0xff6c8291}, {0xff38505e, 0xff718896},
    {0xff617782, 0xff667e8b}, {0xfff0f4f6, 0xff203441},
    {0xffe4edf1, 0xff233744}, {0xffe1edf0, 0xff243845},
    {0xffd8e7eb, 0xff273b48}, {0xffeaf4f4, 0xff203b3d},
    {0xfff2f7f8, 0xff273c47}, {0xffffffff, 0xff20323d},
    {0xffdce8ed, 0xff223947}, {0xffb7c9d2, 0xff405765},
    {0xffa9bbc5, 0xff425a68}, {0xff8aa0ad, 0xff475f6d},
    {0xff6bd5cb, 0xff00665f}, {0xffffd479, 0xff865200},
    {0xffffcb77, 0xff8a5100}, {0xffffc857, 0xff895000},
    {0xffffc17d, 0xff8b4b00}, {0xff203f50, 0xffdfebf1} // Main's existing closing panel
}};
inline std::uint32_t legacy(std::uint32_t value) noexcept {
    // Light targets are distinct, and disjoint from all legacy palette values.
    // This recovers a constructor/status colour created while Light is active.
    for (const auto& pair : palette)
        if ((value & 0x00ffffffU) == (pair.light & 0x00ffffffU))
            return (value & 0xff000000U) | (pair.legacy & 0x00ffffffU);
    return value;
}
}
inline juce::Colour colour(std::uint32_t legacyARGB) noexcept {
    if (selected == setup::Appearance::Light && (legacyARGB & 0xff000000U) != 0)
        for (const auto& pair : detail::palette)
            if ((legacyARGB & 0x00ffffffU) == (pair.legacy & 0x00ffffffU))
                return juce::Colour{(legacyARGB & 0xff000000U) | (pair.light & 0x00ffffffU)};
    return juce::Colour{legacyARGB};
}
inline juce::Colour colour(juce::Colour legacyColour) noexcept {
    return colour(static_cast<std::uint32_t>(legacyColour.getARGB()));
}

namespace detail {
class LookAndFeel final : public juce::LookAndFeel_V4 {
public:
    juce::PopupMenu::Options getOptionsForComboBoxPopupMenu(juce::ComboBox& box,
                                                         juce::Label& label) override {
        auto options = juce::LookAndFeel_V4::getOptionsForComboBoxPopupMenu(box, label);
        // Compact menus fit as a whole. Aligning the selected row over a control
        // near the display edge can shrink JUCE's viewport to one row plus scroll.
        // Retain the selected highlight, but let normal above/below placement act.
        if (box.getNumItems() <= 4)
            options = options.withItemThatMustBeVisible(0);
        // Keep the menu inside the owning native window, including its fullscreen
        // space. Use the root rather than the control/viewport to avoid clipping.
        if (auto* root = box.getTopLevelComponent();
            root != &box && root->isShowing() && root->getPeer() != nullptr)
            return options.withParentComponent(root);
        return options;
    }
};
inline juce::LookAndFeel_V4& lookAndFeel() {
    static LookAndFeel owner;
    return owner;
}
inline void configureLookAndFeel() {
    auto& owner = lookAndFeel();
    if (selected != setup::Appearance::Light) {
        owner.setColourScheme(juce::LookAndFeel_V4::getDarkColourScheme());
        return;
    }
    auto scheme = juce::LookAndFeel_V4::getLightColourScheme();
    using Scheme = juce::LookAndFeel_V4::ColourScheme;
    scheme.setUIColour(Scheme::windowBackground, colour(0xff10212c));
    scheme.setUIColour(Scheme::widgetBackground, colour(0xff142b38));
    scheme.setUIColour(Scheme::outline, colour(0xff617782));
    scheme.setUIColour(Scheme::defaultText, colour(0xfff0f4f6));
    scheme.setUIColour(Scheme::defaultFill, colour(0xff6bd5cb));
    scheme.setUIColour(Scheme::highlightedText, colour(0xff10212c));
    scheme.setUIColour(Scheme::highlightedFill, colour(0xff6bd5cb));
    scheme.setUIColour(Scheme::menuText, colour(0xfff0f4f6));
    owner.setColourScheme(scheme);
    // Filled buttons need light text; the scheme's default text also serves
    // unfilled labels/editors and must stay dark in Light.
    owner.setColour(juce::TextButton::buttonColourId, colour(0xff6bd5cb));
    owner.setColour(juce::TextButton::buttonOnColourId, colour(0xff6bd5cb));
    owner.setColour(juce::TextButton::textColourOffId, colour(0xff10212c));
    owner.setColour(juce::TextButton::textColourOnId, colour(0xff10212c));
    owner.setColour(juce::ToggleButton::textColourId, colour(0xfff0f4f6));
    owner.setColour(juce::ToggleButton::tickColourId, colour(0xff6bd5cb));
    owner.setColour(juce::TextEditor::highlightedTextColourId, colour(0xff10212c));
    owner.setColour(juce::TextEditor::highlightColourId, colour(0xff6bd5cb));
    owner.setColour(juce::Slider::textBoxHighlightColourId, colour(0xff6bd5cb));
}
inline bool backgroundId(int id) noexcept {
    return id == juce::TextEditor::backgroundColourId || id == juce::Label::backgroundColourId ||
        id == juce::Label::backgroundWhenEditingColourId || id == juce::ComboBox::backgroundColourId ||
        id == juce::ListBox::backgroundColourId || id == juce::Slider::textBoxBackgroundColourId;
}
inline void explicitColour(juce::Component& component, int id) {
    if (!component.isColourSpecified(id)) return;
    auto& properties = component.getProperties();
    const juce::Identifier originalKey{"fathomAppearanceOriginal" + juce::String(id)};
    const juce::Identifier lastKey{"fathomAppearanceLast" + juce::String(id)};
    const auto observed = static_cast<std::uint32_t>(component.findColour(id).getARGB());
    if (!properties.contains(originalKey) ||
        observed != static_cast<std::uint32_t>(static_cast<juce::int64>(properties[lastKey]))) {
        // A status renderer may replace an explicit colour after an earlier
        // application. Keep that new original, rather than restoring stale ink.
        properties.set(originalKey, static_cast<juce::int64>(legacy(observed)));
    }
    const auto original = static_cast<std::uint32_t>(static_cast<juce::int64>(properties[originalKey]));
    // White editor/form backgrounds already have a light surface role. A raw
    // white foreground can be mapped, but a white background is never inverted.
    const auto mapped = backgroundId(id) && original == 0xffffffffU
        ? juce::Colour{original} : colour(original);
    if (component.findColour(id) != mapped) component.setColour(id, mapped);
    properties.set(lastKey, static_cast<juce::int64>(mapped.getARGB()));
}
inline void walk(juce::Component& component) {
    // A bounded whitelist of existing framework paint IDs, not arbitrary
    // component properties or authored/model colours.
    const int ids[]{
        juce::Label::textColourId, juce::Label::backgroundColourId, juce::Label::outlineColourId,
        juce::Label::textWhenEditingColourId, juce::Label::backgroundWhenEditingColourId,
        juce::TextEditor::backgroundColourId, juce::TextEditor::textColourId,
        juce::TextEditor::highlightColourId, juce::TextEditor::highlightedTextColourId,
        juce::TextEditor::outlineColourId, juce::TextEditor::focusedOutlineColourId,
        juce::TextButton::buttonColourId, juce::TextButton::buttonOnColourId,
        juce::TextButton::textColourOffId, juce::TextButton::textColourOnId,
        juce::ToggleButton::textColourId, juce::ToggleButton::tickColourId,
        juce::ToggleButton::tickDisabledColourId, juce::ComboBox::backgroundColourId,
        juce::ComboBox::textColourId, juce::ComboBox::outlineColourId,
        juce::ComboBox::arrowColourId, juce::ComboBox::focusedOutlineColourId,
        juce::Slider::backgroundColourId, juce::Slider::thumbColourId,
        juce::Slider::trackColourId, juce::Slider::textBoxTextColourId,
        juce::Slider::textBoxBackgroundColourId, juce::Slider::textBoxHighlightColourId,
        juce::Slider::textBoxOutlineColourId, juce::ListBox::backgroundColourId,
        juce::ListBox::textColourId, juce::ListBox::outlineColourId,
        juce::ScrollBar::backgroundColourId, juce::ScrollBar::thumbColourId
    };
    for (const int id : ids) explicitColour(component, id);
    if (auto* editor = dynamic_cast<juce::TextEditor*>(&component))
        editor->applyColourToAllText(editor->findColour(juce::TextEditor::textColourId), false);
    for (int index = 0; index < component.getNumChildComponents(); ++index)
        if (auto* child = component.getChildComponent(index)) walk(*child);
    component.repaint();
}
}
inline void apply(juce::Component& root) {
    detail::configureLookAndFeel();
    root.setLookAndFeel(&detail::lookAndFeel());
    detail::walk(root);
    root.sendLookAndFeelChange();
    root.repaint();
}
} // namespace fathom::desktop::appearance
