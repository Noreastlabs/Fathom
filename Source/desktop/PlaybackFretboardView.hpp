#pragma once
#include "core/GuitarSetup.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include <memory>
#include <string>
#include <vector>
namespace fathom::desktop {
// Presentation only: no transport, audio, persistence, admission or assessment.
class PlaybackFretboardView final : public juce::Component {
public:
    enum class Mode { Basic, Finger, Note };
    enum class Spelling { Sharp, Flat };
    struct ActiveTone {
        std::string eventId;
        int internalString{}, relativeFret{};
        bool operator==(const ActiveTone& other) const noexcept { return eventId==other.eventId && internalString==other.internalString && relativeFret==other.relativeFret; }
    };
    struct Cell {
        int internalString{}, relativeFret{}, physicalFret{}, midi{};
        bool available{}, active{}, fingerUnknown{};
        std::string note, finger;
        std::vector<std::string> eventIds;
    };
    PlaybackFretboardView();
    void setSetup(const guitar::Setup&);
    void setMode(Mode);
    void setSpelling(Spelling);
    void setModel(std::shared_ptr<const music::ValidatedModel>);
    void setActiveEvents(const std::vector<std::string>&);
    // Exact accepted sounding gates, including pitched Contact member spans.
    void setActiveTones(const std::vector<ActiveTone>&);
    const std::vector<ActiveTone>& activeTones() const noexcept { return activeTones_; }
    void clear();
    const guitar::Setup& setup() const noexcept { return setup_; }
    Mode mode() const noexcept { return mode_; }
    Spelling spelling() const noexcept { return spelling_; }
    const std::vector<Cell>& projection() const noexcept { return cells_; }
    juce::Rectangle<float> cellBounds(int internalString, int relativeFret) const;
    void paint(juce::Graphics&) override;
private:
    void rebuild();
    guitar::Setup setup_;
    Mode mode_{Mode::Basic};
    Spelling spelling_{Spelling::Sharp};
    std::shared_ptr<const music::ValidatedModel> model_;
    std::vector<std::string> activeEvents_;
    std::vector<ActiveTone> activeTones_;
    bool exactTones_{};
    std::vector<Cell> cells_;
};
}
