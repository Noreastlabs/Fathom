#pragma once
#include "desktop/ActionButton.hpp"
#include "core/TabPresentation.hpp"
#include <juce_gui_basics/juce_gui_basics.h>

namespace fathom::desktop {
struct TabOverlays { bool fingers=true, picking=true, notes=false, degrees=false; };
class TabView final : public juce::Component {
public:
    static constexpr std::size_t upcomingPanelLimit=32;
    TabView();
    ~TabView() override;
    void setDocument(std::shared_ptr<const tab::Document>);
    // Presentation only: future documents never receive selection or playback.
    void setUpcomingDocuments(std::vector<std::shared_ptr<const tab::Document>>);
    const std::vector<std::shared_ptr<const tab::Document>>& upcomingDocuments() const noexcept { return upcoming_; }
    bool setPlayback(std::vector<std::string>, std::string status);
    const std::vector<std::string>& playingEvents() const noexcept { return playing_; }
    void setCompact(bool);
    void showDetail(bool);
    bool detailVisible() const noexcept { return showDetail_; }
    bool selectEvent(const std::string&);
    // Accept any finite 10–200% scale; controls use bounded stops and Reset 100%.
    bool setZoom(double);
    void setOverlays(TabOverlays);
    TabOverlays overlays() const noexcept { return overlays_; }
    double zoom() const noexcept { return zoom_; }
    juce::Point<int> scrollPosition() const { return viewport_.getViewPosition(); }
    // JUCE clamps to the current canvas extent; this changes no musical state.
    void restoreScrollPosition(juce::Point<int> position) { viewport_.setViewPosition(position); }
    std::string selectedEvent() const { return selected_; }
    std::string visibleDetail() const { return detail_.getText().toStdString(); }
    void showSource();
    void resized() override;
    void paint(juce::Graphics&) override;
    bool keyPressed(const juce::KeyPress&) override;
    std::function<void(const std::string&)> onSelection;
    std::shared_ptr<const tab::Document> document() const { return document_; }
private:
    class Canvas;
    std::unique_ptr<Canvas> canvas_;
    std::shared_ptr<const tab::Document> document_;
    std::vector<std::shared_ptr<const tab::Document>> upcoming_;
    TabOverlays overlays_;
    double zoom_=1.0;
    std::string selected_;
    std::vector<std::string> playing_;
    bool compact_{},showDetail_{};
    juce::Label playbackStatus_;
    ActionButton detailButton_{"Detail"};
    juce::Label title_,summary_;
    juce::ToggleButton fingers_{"Fng"},picking_{"Picking"},notes_{"Note names"},degrees_{"Deg + context"};
    juce::Label zoomValue_;
    ActionButton smaller_{"Zoom -"},larger_{"Zoom +"},resetZoom_{"Reset 100%"},source_{"Source / instructions"};
    juce::Viewport viewport_;
    juce::TextEditor detail_;
    void refresh();
};
} // namespace fathom::desktop
