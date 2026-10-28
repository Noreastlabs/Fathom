#pragma once
#include "desktop/PracticeCommands.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include <functional>
#include <memory>

namespace fathom::desktop {
// AppKit event time/key codes are input provenance, never musical time.
struct PracticeKeyObservation {
    double timestamp{};
    int key{},hardwareKey{};
    bool down{},repeat{},modified{},matchedWindow{},visible{},consumed{},invoked{};
};
class PracticeKeyboardMac final {
public:
    PracticeKeyboardMac(juce::Component&,std::function<void(PracticeCommand)>);
    ~PracticeKeyboardMac();
    std::function<void(const PracticeKeyObservation&)> onObservation;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
}
