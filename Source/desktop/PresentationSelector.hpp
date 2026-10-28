#pragma once
#include "desktop/PresentationPolicy.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
namespace fathom::desktop {
class PresentationSelector final : public juce::ComboBox {
public:
    PresentationSelector() {
        addItem("Use global", 1); addItem("Beginner", 2);
        addItem("Advanced", 3); addItem("Developer", 4);
        setSelectedId(1, juce::dontSendNotification);
        setWantsKeyboardFocus(true);
        onChange = [this] {
            const auto id = getSelectedId();
            if (onChoice && id >= 1 && id <= 4)
                onChoice(id == 1 ? std::nullopt : std::optional<presentation::Level>{static_cast<presentation::Level>(id - 2)});
        };
    }
    void display(presentation::Level global, std::optional<presentation::Level> overrideLevel) {
        changeItemText(1, "Use global (" + juce::String(presentation::levelLabel(global)) + ")");
        setSelectedId(overrideLevel ? static_cast<int>(*overrideLevel) + 2 : 1, juce::dontSendNotification);
        const auto effective = overrideLevel.value_or(global);
        setTitle("Presentation: " + juce::String(presentation::levelLabel(effective)) +
                 (overrideLevel ? " (this page, session only)" : " (global)"));
        setTooltip(getTitle() + ". Use global clears this page override. Disclosure does not change the selected exercise, transport or permissions.");
    }
    std::function<void(std::optional<presentation::Level>)> onChoice;
};
}
