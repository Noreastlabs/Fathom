#pragma once

#include "core/GuitarSetup.hpp"
#include "core/MusicModel.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include <memory>
#include <functional>
#include <string>
#include <vector>

namespace fathom::desktop {

struct FretboardToneMarker {
    std::string sourceId;
    std::string sourceRef;
    std::string eventId;
    std::string chordSymbol;
    std::string pitchName;
    std::string finger;
    int internalString{};
    int displayString{};
    int relativeFret{};
    int physicalFret{};
    int midi{};
    std::string authoredSpelling{};
    std::vector<music::Degree> degrees{};
};

// Read-only source projection. It does not admit, schedule, or play an event.
class FretboardView final : public juce::Component {
public:
    FretboardView();
    ~FretboardView() override;

    bool setEvent(std::shared_ptr<const music::ValidatedModel>, const std::string& eventId);
    void setHandedness(guitar::Handedness);
    void setApprovedBookContext(const std::string&);
    std::function<void()> onRequestBookContext;
    std::string theorySummary() const { return theory_.getText().toStdString(); }
    int firstDisplayedFret() const noexcept { return firstDisplayedFret_; }
    int lastDisplayedFret() const noexcept { return lastDisplayedFret_; }
    std::string selectedEventId() const { return eventId_; }
    std::string sourceSummary() const { return sourceSummary_; }
    std::string timingSummary() const { return timingSummary_; }
    std::string statusSummary() const { return statusSummary_; }
    const std::vector<FretboardToneMarker>& markers() const noexcept { return markers_; }
    juce::Rectangle<int> markerBounds() const;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    class Board;
    std::shared_ptr<const music::ValidatedModel> model_;
    std::string eventId_;
    std::string sourceSummary_;
    std::string timingSummary_;
    std::string statusSummary_;
    std::vector<FretboardToneMarker> markers_;
    guitar::Handedness handedness_ = guitar::Handedness::Right;
    std::unique_ptr<Board> board_;
    juce::Label heading_;
    juce::Label source_;
    juce::Label timing_;
    juce::Label status_;
    juce::TextEditor theory_;
    juce::TextButton bookContext_{"Show approved book explanation"};
    std::string approvedBookContext_;
    int firstDisplayedFret_=0, lastDisplayedFret_=12;
    void refreshTheory();

    bool refuse(const std::string& reason);
};

} // namespace fathom::desktop
