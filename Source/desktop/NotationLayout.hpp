#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include <algorithm>
#include <vector>

namespace fathom::desktop::notation_layout {
// Shared allocation only: no event, source, transport or preference state.
inline constexpr int gap = 8;
inline constexpr int controlHeight = 34;
inline void row(juce::Rectangle<int> area,
                const std::vector<std::pair<juce::Component*,int>>& controls) {
    int count=0,total=0;
    for (const auto& [control,width] : controls)
        if (control->isVisible()) { ++count; total+=width; }
    if (!count) return;
    const int available=std::max(1,area.getWidth()-gap*(count-1));
    int remaining=available,weight=total,index=0;
    for (const auto& [control,width] : controls) {
        if (!control->isVisible()) { control->setBounds({}); continue; }
        const int extent=++index==count?remaining:std::max(1,remaining*width/std::max(1,weight));
        control->setBounds(area.removeFromLeft(extent));
        area.removeFromLeft(gap); remaining-=extent; weight-=width;
    }
}
inline juce::Rectangle<int> workspace(juce::Rectangle<int> bounds, int top, int bottom) {
    return {bounds.getX()+8,bounds.getY()+top,std::max(1,bounds.getWidth()-16),
            std::max(1,bounds.getHeight()-top-bottom)};
}
} // namespace fathom::desktop::notation_layout
