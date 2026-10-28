#include "desktop/Appearance.hpp"
#include "desktop/FretboardView.hpp"
#include "core/TabPresentation.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <sstream>
#include <stdexcept>

namespace fathom::desktop {
namespace {
constexpr auto background = 0xff10212c;
constexpr auto boardBackground = 0xff172e3b;
constexpr auto ink = 0xfff0f4f6;
constexpr auto muted = 0xffb7c9d2;
constexpr auto aqua = 0xff6bd5cb;
constexpr auto markerBackground = 0xff225b62;
constexpr int legacyLastFret = 12;

juce::String text(const std::string& value) {
    return juce::String::fromUTF8(value.c_str());
}

std::string fingerDescription(const std::string& finger) {
    return finger.empty() ? "unspecified" : finger == "O" ? "open" : finger;
}

class PositionMarker final : public juce::Component {
public:
    explicit PositionMarker(const FretboardToneMarker& marker)
        : pitch_(marker.authoredSpelling.empty() ? marker.pitchName : marker.authoredSpelling),
          finger_(fingerDescription(marker.finger)), degree_("Deg unspecified"),
          displayString_(marker.displayString), relativeFret_(marker.relativeFret) {
        if(!marker.degrees.empty()){degree_="Deg ";for(const auto& degree:marker.degrees){if(degree_!="Deg ")degree_+="/";degree_+=degree.sourceLabel;}}
        std::ostringstream label;
        label << "Source " << marker.sourceId << "; event " << marker.eventId
              << "; " << marker.chordSymbol << "; string " << marker.displayString
              << " (internal " << marker.internalString << "); relative fret " << marker.relativeFret
              << "; physical fret " << marker.physicalFret << "; " << marker.pitchName
              << " MIDI " << marker.midi << "; finger " << finger_
              << "; authored spelling " << (marker.authoredSpelling.empty() ? "unspecified" : marker.authoredSpelling);
        for(const auto& degree:marker.degrees)label << "; degree " << degree.sourceLabel << " [" << degree.context << "]";
        label << ".";
        setTitle(text(label.str()));
        setDescription(text(label.str()));
        setWantsKeyboardFocus(false);
    }

    int displayString() const noexcept { return displayString_; }
    int relativeFret() const noexcept { return relativeFret_; }

    void paint(juce::Graphics& graphics) override {
        auto bounds = getLocalBounds().toFloat().reduced(1.0f);
        graphics.setColour(appearance::colour(markerBackground));
        graphics.fillRoundedRectangle(bounds, 7.0f);
        graphics.setColour(appearance::colour(aqua));
        graphics.drawRoundedRectangle(bounds, 7.0f, 2.0f);
        graphics.setColour(appearance::colour(ink));
        graphics.setFont(juce::FontOptions{14.0f, juce::Font::bold});
        graphics.drawText(text(pitch_), 1, 1, getWidth() - 2, 19, juce::Justification::centred);
        graphics.setFont(juce::FontOptions{11.0f});
        const auto fingerLabel = finger_ == "open" ? std::string("Open") : "Fng " + finger_;
        graphics.drawText(text(fingerLabel), 1, 18, getWidth() - 2, 16,
                          juce::Justification::centred);
        graphics.setFont(juce::FontOptions{10.0f});
        graphics.drawText(text(degree_),1,33,getWidth()-2,14,juce::Justification::centred);
    }

private:
    std::string pitch_;
    std::string finger_;
    std::string degree_;
    int displayString_{};
    int relativeFret_{};
};
}

class FretboardView::Board final : public juce::Component {
public:
    Board() {
        setTitle("Fretboard: source event positions");
        setDescription("Six guitar strings, frets zero through twelve, derived from the selected source tuning.");
    }

    void setProjection(const guitar::Setup& setup, const std::vector<FretboardToneMarker>& markers, int first, int last) {
        for (auto& marker : markerViews_)
            removeChildComponent(marker.get());
        markerViews_.clear();
        setup_ = setup;
        firstFret_=first;lastFret_=last;
        setDescription("Source-selected relative fret window " + juce::String(first) + " through " + juce::String(last) + "; authored tuning/capo, default instrument support.");
        for (const auto& marker : markers) {
            auto view = std::make_unique<PositionMarker>(marker);
            addAndMakeVisible(*view);
            markerViews_.push_back(std::move(view));
        }
        layoutMarkers();
        repaint();
    }

    void clearProjection() {
        for (auto& marker : markerViews_)
            removeChildComponent(marker.get());
        markerViews_.clear();
        repaint();
    }

    void setHandedness(guitar::Handedness handedness) {
        if (setup_.handedness == handedness)
            return;
        setup_.handedness = handedness;
        layoutMarkers();
        repaint();
    }

    juce::Rectangle<int> markerBounds() const {
        juce::Rectangle<int> bounds;
        for (const auto& marker : markerViews_)
            bounds = bounds.isEmpty() ? marker->getBounds() : bounds.getUnion(marker->getBounds());
        return bounds;
    }

    void paint(juce::Graphics& graphics) override {
        graphics.fillAll(appearance::colour(boardBackground));
        constexpr int left = 62;
        constexpr int right = 14;
        constexpr int top = 33;
        constexpr int rowHeight = 50;
        const int usable = std::max(1, getWidth() - left - right);
        const float cell = static_cast<float>(usable) / static_cast<float>(lastFret_-firstFret_+1);

        graphics.setFont(juce::FontOptions{12.0f, juce::Font::bold});
        for (int fret = firstFret_; fret <= lastFret_; ++fret) {
            const int column = guitar::fretColumn(fret-firstFret_, lastFret_-firstFret_+1, setup_.handedness);
            const float x = static_cast<float>(left) + (static_cast<float>(column) + 0.5f) * cell;
            graphics.setColour(appearance::colour(aqua));
            const auto fretLabel = fret == 0 ? juce::String{"Open"} : juce::String{fret};
            graphics.drawText(fretLabel,
                              static_cast<int>(x - cell * 0.5f), 5,
                              static_cast<int>(std::ceil(cell)), 20, juce::Justification::centred);
            graphics.setColour(appearance::colour(0xff38505e));
            graphics.drawVerticalLine(static_cast<int>(std::round(x)), 28.0f,
                                      static_cast<float>(top + rowHeight * 6 - 3));
        }

        graphics.setFont(juce::FontOptions{11.0f});
        for (int display = 1; display <= 6; ++display) {
            const int internal = 7 - display;
            const int y = top + (display - 1) * rowHeight;
            const int lineY = y + 18;
            graphics.setColour(appearance::colour(0xff617782));
            graphics.drawHorizontalLine(lineY, static_cast<float>(left - 4),
                                        static_cast<float>(getWidth() - right));
            graphics.setColour(appearance::colour(ink));
            graphics.setFont(juce::FontOptions{13.0f, juce::Font::bold});
            graphics.drawText("String " + juce::String(display), 4, y + 5, left - 11, 24,
                              juce::Justification::centredLeft);
            graphics.setFont(juce::FontOptions{10.0f});
            for (int fret = firstFret_; fret <= lastFret_; ++fret) {
                const int column = guitar::fretColumn(fret-firstFret_, lastFret_-firstFret_+1, setup_.handedness);
                const float x = static_cast<float>(left) + (static_cast<float>(column) + 0.5f) * cell;
                const auto position = guitar::position(setup_, internal, fret);
                const auto name = position.available() && position.midi
                    ? guitar::noteName(*position.midi)
                    : std::string("--");
                graphics.setColour(appearance::colour(muted));
                graphics.drawText(text(name), static_cast<int>(x - cell * 0.5f), y + 30,
                                  static_cast<int>(std::ceil(cell)), 17, juce::Justification::centred);
            }
        }
    }

    void resized() override { layoutMarkers(); }

private:
    guitar::Setup setup_;
    int firstFret_=0,lastFret_=legacyLastFret;
    std::vector<std::unique_ptr<PositionMarker>> markerViews_;

    void layoutMarkers() {
        constexpr int left = 62;
        constexpr int right = 14;
        constexpr int top = 33;
        constexpr int rowHeight = 50;
        const int usable = std::max(1, getWidth() - left - right);
        const float cell = static_cast<float>(usable) / static_cast<float>(lastFret_-firstFret_+1);
        for (auto& marker : markerViews_) {
            const int display = marker->displayString();
            const int fret = marker->relativeFret();
            if (display < 1 || display > 6 || fret < firstFret_ || fret > lastFret_)
                continue;
            const int column = guitar::fretColumn(fret-firstFret_, lastFret_-firstFret_+1, setup_.handedness);
            const float centerX = static_cast<float>(left) + (static_cast<float>(column) + 0.5f) * cell;
            const int y = top + (display - 1) * rowHeight + 2;
            const int markerWidth = std::max(1, static_cast<int>(std::floor(cell)) - 2);
            marker->setBounds(static_cast<int>(std::round(centerX - static_cast<float>(markerWidth) * 0.5f)),
                              y, markerWidth, 48);
        }
    }
};

FretboardView::FretboardView() : board_(std::make_unique<Board>()) {
    setTitle("Read-only guitar fretboard projection");
    setDescription("A view of validated source event positions. It does not play sound or infer event timing.");
    heading_.setText("Fretboard source projection", juce::dontSendNotification);
    heading_.setFont(juce::FontOptions{22.0f, juce::Font::bold});
    heading_.setColour(juce::Label::textColourId, appearance::colour(ink));
    heading_.setTitle("Fretboard view heading");
    source_.setFont(juce::FontOptions{14.0f});
    source_.setColour(juce::Label::textColourId, appearance::colour(ink));
    source_.setTitle("Source and selected event identity");
    timing_.setFont(juce::FontOptions{13.0f});
    timing_.setColour(juce::Label::textColourId, appearance::colour(muted));
    timing_.setTitle("Authored source timing boundary");
    status_.setFont(juce::FontOptions{13.0f});
    status_.setColour(juce::Label::textColourId, appearance::colour(aqua));
    status_.setTitle("Projection and admission status");
    for (auto* label : {&heading_, &source_, &timing_, &status_})
        addAndMakeVisible(*label);
    addAndMakeVisible(*board_);
    statusSummary_ = "No source event selected.";
    timingSummary_ = "No source timing shown.";
    status_.setText(text(statusSummary_), juce::dontSendNotification);
    timing_.setText(text(timingSummary_), juce::dontSendNotification);
    theory_.setComponentID("fretboard-theory-details");
    theory_.setTitle("Selected source tone degrees and approved book explanation; separate contexts");
    theory_.setMultiLine(true);theory_.setReadOnly(true);theory_.setScrollbarsShown(true);theory_.setCaretVisible(false);
    theory_.setFont(juce::FontOptions{14.0f});
    bookContext_.setComponentID("fretboard-approved-book-context");
    bookContext_.setTitle("Read the selected original workbook's approved explanation; no Practice or credit");
    bookContext_.onClick=[this]{if(onRequestBookContext)onRequestBookContext();};
    bookContext_.setEnabled(false);
    addAndMakeVisible(bookContext_);addAndMakeVisible(theory_);
    refreshTheory();
    setSize(1000, 760);
}

FretboardView::~FretboardView() = default;

void FretboardView::setHandedness(guitar::Handedness handedness) {
    handedness_ = handedness;
    board_->setHandedness(handedness);
}

juce::Rectangle<int> FretboardView::markerBounds() const {
    return board_->markerBounds().translated(board_->getX(), board_->getY());
}

bool FretboardView::refuse(const std::string& reason) {
    model_.reset();
    eventId_.clear();
    markers_.clear();
    sourceSummary_ = "No source event selected.";
    timingSummary_ = "No source timing shown.";
    statusSummary_ = "Projection refused: " + reason;
    source_.setText(text(sourceSummary_), juce::dontSendNotification);
    timing_.setText(text(timingSummary_), juce::dontSendNotification);
    status_.setText(text(statusSummary_), juce::dontSendNotification);
    board_->clearProjection();
    approvedBookContext_.clear();bookContext_.setEnabled(false);
    firstDisplayedFret_=0;lastDisplayedFret_=legacyLastFret;refreshTheory();
    return false;
}

bool FretboardView::setEvent(std::shared_ptr<const music::ValidatedModel> model,
                             const std::string& eventId) {
    if (!model)
        return refuse("no validated source model was supplied.");

    const auto& source = model->source();
    if (source.instrument.openMidi.size() != 6)
        return refuse("source instrument does not define exactly six strings.");

    const auto event = std::find_if(source.events.begin(), source.events.end(),
                                    [&](const auto& candidate) { return candidate.id == eventId; });
    if (event == source.events.end())
        return refuse("source event ID was not found.");
    if (event->kind != music::Kind::Note && event->kind != music::Kind::Chord)
        return refuse("selected source event is not a note or chord.");
    if (event->tones.empty())
        return refuse("selected source event has no pitched positions.");

    guitar::Setup setup;
    std::copy(source.instrument.openMidi.begin(), source.instrument.openMidi.end(), setup.openMidi.begin());
    setup.capo = source.instrument.capo;
    setup.handedness = handedness_;
    if (!guitar::validate(setup).empty())
        return refuse("source tuning or capo cannot produce a valid six-string fretboard.");

    std::vector<FretboardToneMarker> markers;
    markers.reserve(event->tones.size());
    for (const auto& tone : event->tones) {
        if(tone.fret<0)
            return refuse("a selected source fret is negative.");
        guitar::Position position{};
        try {
            position = guitar::position(setup, tone.string, tone.fret);
        } catch (const std::exception&) {
            return refuse("a selected source string/fret is invalid for the source tuning.");
        }
        if (!position.available() || !position.midi)
            return refuse("a selected source position is unavailable on the displayed instrument.");
        if (*position.midi != tone.midi)
            return refuse("source sounding MIDI contradicts its tuning/capo/fret position.");

        markers.push_back({source.itemId, event->sourceRef, event->id, event->chordSymbol,
                           guitar::noteName(*position.midi), tone.finger, tone.string,
                           guitar::displayString(tone.string), tone.fret,
                           static_cast<int>(position.physicalFret), tone.midi, tone.spelling, tone.degrees});
    }

    const auto bounds=std::minmax_element(markers.begin(),markers.end(),[](const auto& a,const auto& b){return a.relativeFret<b.relativeFret;});
    const int support=setup.fretCount-setup.capo;
    lastDisplayedFret_=std::min(support,std::max(legacyLastFret,bounds.second->relativeFret));
    firstDisplayedFret_=std::min(bounds.first->relativeFret,std::max(0,lastDisplayedFret_-legacyLastFret));
    approvedBookContext_.clear();
    model_ = std::move(model);
    eventId_ = event->id;
    markers_ = std::move(markers);
    sourceSummary_ = "Source " + source.itemId + " / event " + event->id +
                     " / " + (event->sourceRef.empty() ? std::string("source reference unspecified") : event->sourceRef) +
                     (event->chordSymbol.empty() ? std::string{} : " / " + event->chordSymbol);
    if (!event->span.onset && !event->span.duration)
        timingSummary_ = "Source timing unspecified; display only; no playback or timing inference.";
    else
        timingSummary_ = "Authored source timing retained; display only; no playback.";
    if (source.syntheticFixture)
        statusSummary_ = "Synthetic QA source; no curriculum runtime admission. Positions are read-only.";
    else if (source.proposalExample)
        statusSummary_ = "Proposal example; not admitted to curriculum runtime. Positions are read-only.";
    else
        statusSummary_ = "Validated source projection only. This view does not confer runtime admission.";

    source_.setText(text(sourceSummary_), juce::dontSendNotification);
    timing_.setText(text(timingSummary_), juce::dontSendNotification);
    status_.setText(text(statusSummary_), juce::dontSendNotification);
    statusSummary_ += " Relative fret window " + std::to_string(firstDisplayedFret_) + "–" + std::to_string(lastDisplayedFret_) +
                      "; physical " + std::to_string(setup.capo+firstDisplayedFret_) + "–" + std::to_string(setup.capo+lastDisplayedFret_) + ".";
    status_.setText(text(statusSummary_),juce::dontSendNotification);
    board_->setProjection(setup, markers_,firstDisplayedFret_,lastDisplayedFret_);
    bookContext_.setEnabled(static_cast<bool>(onRequestBookContext));
    refreshTheory();
    return true;
}

void FretboardView::setApprovedBookContext(const std::string& context) {
    approvedBookContext_=context;refreshTheory();
}

void FretboardView::refreshTheory() {
    std::ostringstream out;
    out << source_.getText().toStdString() << "\n" << timingSummary_ << "\n" << statusSummary_ << "\n\n";
    out << "Selected source tones — these degree contexts do not infer a global key.\n";
    if(markers_.empty())out << "No pitched source event selected.\n";
    for(const auto& marker:markers_) {
        out << "String " << marker.displayString << "; relative fret " << marker.relativeFret << "; physical fret " << marker.physicalFret
            << "; MIDI " << marker.midi << "; derived pitch " << marker.pitchName << "; authored spelling "
            << (marker.authoredSpelling.empty()?"unspecified":marker.authoredSpelling) << "; finger " << fingerDescription(marker.finger) << "\n";
        if(marker.degrees.empty())out << "Degree context unspecified; root register and interval unspecified.\n";
        for(const auto& degree:marker.degrees) {
            out << "Degree " << degree.sourceLabel << " [" << degree.context << "]; root pitch class " << degree.rootPitchClass
                << "; ordinal " << degree.ordinal << "; alteration " << degree.alteration;
            if(degree.rootMidi)out << "; supplied root MIDI " << *degree.rootMidi << "; signed interval " << music::intervalSemitones(*degree.rootMidi,marker.midi) << " semitones.\n";
            else out << "; root register unspecified; signed root interval unspecified.\n";
        }
    }
    out << "\nApproved original workbook explanation — separate from selected tone projection:\n";
    out << (approvedBookContext_.empty()?"Choose Show approved book explanation to read verified offline context. No root octave, source timing, drone or Practice authority is inferred.":approvedBookContext_);
    theory_.setText(text(out.str()),false);
}

void FretboardView::paint(juce::Graphics& graphics) {
    graphics.fillAll(appearance::colour(background));
}

void FretboardView::resized() {
    if(getHeight()<600){
        auto area=getLocalBounds().reduced(8);
        heading_.setVisible(false);source_.setVisible(false);timing_.setVisible(false);
        status_.setBounds(area.removeFromTop(26));area.removeFromTop(4);
        board_->setBounds(area.removeFromTop(335));area.removeFromTop(4);
        bookContext_.setBounds(area.removeFromTop(30));area.removeFromTop(4);theory_.setBounds(area);
        return;
    }
    heading_.setVisible(true);source_.setVisible(true);timing_.setVisible(true);
    auto area = getLocalBounds().reduced(16);
    heading_.setBounds(area.removeFromTop(30));
    source_.setBounds(area.removeFromTop(36));
    timing_.setBounds(area.removeFromTop(25));
    status_.setBounds(area.removeFromTop(24));
    area.removeFromTop(8);
    board_->setBounds(area.removeFromTop(335));
    area.removeFromTop(8);bookContext_.setBounds(area.removeFromTop(30));
    area.removeFromTop(8);theory_.setBounds(area);
}

} // namespace fathom::desktop
