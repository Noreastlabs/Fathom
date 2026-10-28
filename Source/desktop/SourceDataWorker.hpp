#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

namespace fathom::desktop {
// One shared data worker avoids concurrent closed-registry construction. Normal
// close guards count both queued and running jobs; completion uses owner tickets.
inline juce::ThreadPool& sourceDataPool() {
    static juce::ThreadPool pool{1};
    return pool;
}
}
