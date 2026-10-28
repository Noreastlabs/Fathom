#include "desktop/FretboardView.hpp"
#include "core/TabPresentation.hpp"
#include "reference_audio_fixtures.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

using namespace fathom;

namespace {
int checks = 0;
std::ofstream results;

void check(bool condition, const std::string& description) {
    ++checks;
    results << description << '\t' << (condition ? "PASS" : "FAIL") << '\n';
    results.flush();
    if (!condition)
        throw std::runtime_error(description);
}

struct ExpectedTone {
    int internalString;
    int displayString;
    int relativeFret;
    int physicalFret;
    int midi;
    const char* finger;
    const char* note;
};

const std::array<ExpectedTone, 6> eExpected{{
    {1, 6, 0, 0, 40, "O", "E2"},
    {2, 5, 2, 2, 47, "2", "B2"},
    {3, 4, 2, 2, 52, "3", "E3"},
    {4, 3, 1, 1, 56, "1", "G#3"},
    {5, 2, 0, 0, 59, "O", "B3"},
    {6, 1, 0, 0, 64, "O", "E4"},
}};

const std::array<ExpectedTone, 6> emExpected{{
    {1, 6, 0, 0, 40, "O", "E2"},
    {2, 5, 2, 2, 47, "2", "B2"},
    {3, 4, 2, 2, 52, "3", "E3"},
    {4, 3, 0, 0, 55, "O", "G3"},
    {5, 2, 0, 0, 59, "O", "B3"},
    {6, 1, 0, 0, 64, "O", "E4"},
}};

std::string juceText(const juce::String& value) {
    return value.toStdString();
}

juce::Component* findChildWithTitle(juce::Component& parent, const std::string& title) {
    for (auto* child : parent.getChildren())
        if (juceText(child->getTitle()) == title)
            return child;
    return nullptr;
}

void saveSnapshot(desktop::FretboardView& view, const std::filesystem::path& path,
                  const std::string& name) {
    const auto image = view.createComponentSnapshot(view.getLocalBounds());
    check(!image.isNull(), name + " component snapshot is nonempty");
    juce::FileOutputStream stream{juce::File{path.string()}};
    juce::PNGImageFormat png;
    check(stream.openedOk() && png.writeImageToStream(image, stream), name + " PNG is written");
    stream.flush();
    check(!stream.getStatus().failed(), name + " PNG flush succeeds");
    check(std::filesystem::file_size(path) > 0, name + " PNG has nonzero size");
}

void checkChord(const music::Model& source,
                const std::shared_ptr<const music::ValidatedModel>& validated,
                desktop::FretboardView& view,
                const std::filesystem::path& run,
                bool minor) {
    const auto& expected = minor ? emExpected : eExpected;
    const std::string symbol = minor ? "Em" : "E";
    const std::string eventId = std::string("fg:item:000008:event:") + (minor ? "0002" : "0001");
    const auto event = std::find_if(source.events.begin(), source.events.end(),
                                    [&](const auto& candidate) { return candidate.id == eventId; });
    check(event != source.events.end(), symbol + " source event identity exists");
    check(event->kind == music::Kind::Chord && event->chordSymbol == symbol &&
              event->sourceRef == "L49-TXT49-61" && event->tones.size() == expected.size(),
          symbol + " original source event retains chord identity and six members");
    check(!event->span.onset && !event->span.duration &&
              std::all_of(event->tones.begin(), event->tones.end(), [](const auto& tone) {
                  return tone.memberSpan && !tone.memberSpan->onset && !tone.memberSpan->duration;
              }),
          symbol + " original source remains untimed");

    tab::Document tabDocument(validated);
    check(!tabDocument.allTimed(), symbol + " TAB preserves the source untimed state");
    const auto detail = tabDocument.detail(eventId);
    check(detail.find("Source: L49-TXT49-61") != std::string::npos &&
              detail.find("onset unspecified; duration unspecified") != std::string::npos,
          symbol + " TAB detail preserves source reference and timing boundary");

    check(view.setEvent(validated, eventId), symbol + " view accepts the original validated event");
    check(view.selectedEventId() == eventId && view.markers().size() == expected.size(),
          symbol + " view retains event ID and six source markers");
    check(view.sourceSummary().find("fg:item:000008") != std::string::npos &&
              view.sourceSummary().find(eventId) != std::string::npos &&
              view.sourceSummary().find("L49-TXT49-61") != std::string::npos &&
              view.sourceSummary().find(symbol) != std::string::npos,
          symbol + " visible and accessible summary identifies source/event/reference/chord");
    check(view.timingSummary().find("timing unspecified") != std::string::npos &&
              view.timingSummary().find("no playback") != std::string::npos,
          symbol + " view states untimed display-only boundary");
    check(view.statusSummary().find("Proposal example") != std::string::npos &&
              view.statusSummary().find("not admitted") != std::string::npos,
          symbol + " view does not imply curriculum runtime admission");

    guitar::Setup setup;
    std::copy(source.instrument.openMidi.begin(), source.instrument.openMidi.end(), setup.openMidi.begin());
    setup.capo = source.instrument.capo;
    for (std::size_t index = 0; index < expected.size(); ++index) {
        const auto& want = expected[index];
        const auto& sourceTone = event->tones[index];
        const auto& marker = view.markers()[index];
        const auto position = guitar::position(setup, want.internalString, want.relativeFret);
        const std::string prefix = symbol + " member " + std::to_string(index + 1);

        check(sourceTone.string == want.internalString && sourceTone.fret == want.relativeFret &&
                  sourceTone.midi == want.midi && sourceTone.finger == want.finger,
              prefix + " exact source string/fret/MIDI/finger");
        check(position.available() && position.midi == want.midi &&
                  position.physicalFret == want.physicalFret,
              prefix + " independent guitar position agrees with expected physical fret and pitch");
        check(marker.sourceId == source.itemId && marker.sourceRef == event->sourceRef &&
                  marker.eventId == eventId && marker.chordSymbol == symbol &&
                  marker.internalString == want.internalString &&
                  marker.displayString == want.displayString &&
                  marker.relativeFret == want.relativeFret && marker.physicalFret == want.physicalFret &&
                  marker.midi == want.midi && marker.pitchName == want.note &&
                  marker.finger == want.finger,
              prefix + " view marker exactly projects source and position facts");
        check(tabDocument.displayString(want.internalString) == want.displayString,
              prefix + " conventional TAB display string agrees");

        const auto tabMember = "String " + std::to_string(want.displayString) +
            " (internal " + std::to_string(want.internalString) + "), fret " +
            std::to_string(want.relativeFret) + "; " + want.note +
            " (derived); MIDI " + std::to_string(want.midi) +
            "; authored spelling unspecified\nFng: " + want.finger + "; Deg: unspecified";
        check(detail.find(tabMember) != std::string::npos,
              prefix + " exact TAB member detail agrees with projection");
    }

    auto* board = findChildWithTitle(view, "Fretboard: source event positions");
    check(board != nullptr && board->getWidth() > 0 && board->getHeight() > 0,
          symbol + " real fretboard component is laid out");
    check(board != nullptr && board->getNumChildComponents() == 6,
          symbol + " creates one visible/accessibility marker for every chord tone");
    if (board != nullptr) {
        for (std::size_t index = 0; index < expected.size(); ++index) {
            juce::Component* markerView = nullptr;
            const auto token = "event " + eventId + "; " + symbol + "; string " +
                std::to_string(expected[index].displayString) + " (internal " +
                std::to_string(expected[index].internalString) + "); relative fret " +
                std::to_string(expected[index].relativeFret) + "; physical fret " +
                std::to_string(expected[index].physicalFret) + "; " + expected[index].note +
                " MIDI " + std::to_string(expected[index].midi) + "; finger " +
                (std::string(expected[index].finger) == "O" ? "open" : expected[index].finger) + "; authored spelling ";
            for (auto* candidate : board->getChildren())
                if (juceText(candidate->getTitle()).find(token) != std::string::npos)
                    markerView = candidate;
            check(markerView != nullptr, symbol + " member " + std::to_string(index + 1) +
                      " accessible marker names source/event/string/fret/pitch/finger");
            check(markerView != nullptr && markerView->getWidth() > 0 && markerView->getHeight() > 0 &&
                      board->getLocalBounds().contains(markerView->getBounds()),
                  symbol + " member " + std::to_string(index + 1) + " marker is visibly contained in the board");
        }
    }

    const auto synthetic = reference_fixtures::chord(minor);
    check(synthetic.itemId == source.itemId && synthetic.proposalExample && synthetic.syntheticFixture &&
              synthetic.sourceRefs == source.sourceRefs && synthetic.events.size() == 2 &&
              synthetic.events.front().id == eventId,
          symbol + " reference-audio comparison uses a separate source-linked synthetic QA copy");
    auto referenceValidation = music::validate(synthetic);
    check(referenceValidation.validReference(), symbol + " synthetic reference QA copy validates");
    const auto program = reference::compile(referenceValidation.model,
                                             reference_fixtures::config(Rational{5, 2}));
    check(program.voices().size() == expected.size(), symbol + " reference plan contains six voices");
    for (std::size_t index = 0; index < expected.size(); ++index) {
        const auto& voice = program.voices()[index];
        const auto& want = expected[index];
        check(voice.string == want.internalString && voice.midi == want.midi &&
                  voice.sourceEvents == std::vector<std::string>{eventId},
              symbol + " reference voice " + std::to_string(index + 1) +
                  " retains matching source/string/MIDI identity");
    }

    const auto png = run / (minor ? "l49-em-fretboard.png" : "l49-e-fretboard.png");
    saveSnapshot(view, png, symbol + " actual offscreen GUI");
    check(view.setEvent(validated, "fg:item:000008:event:missing") == false,
          symbol + " unknown source event refuses projection");
    check(view.selectedEventId().empty() && view.markers().empty() &&
              view.statusSummary().find("ID was not found") != std::string::npos,
          symbol + " refused event clears old markers and reports exact reason");
}

int markerCenter(juce::Component& board, int displayString, int fret) {
    const auto token = "; string " + std::to_string(displayString) +
        " (internal " + std::to_string(7 - displayString) + "); relative fret " +
        std::to_string(fret) + ";";
    for (auto* child : board.getChildren())
        if (juceText(child->getTitle()).find(token) != std::string::npos)
            return child->getBounds().getCentreX();
    throw std::runtime_error("Missing source marker for mirrored geometry");
}
}

int main(int argc, char** argv) {
    try {
        if (argc != 2 || std::filesystem::exists(argv[1]))
            throw std::runtime_error("A new run directory argument is required");
        const std::filesystem::path run{argv[1]};
        std::filesystem::create_directories(run);
        results.open(run / "checks.tsv");
        if (!results)
            throw std::runtime_error("Could not create checks.tsv");

        juce::ScopedJuceInitialiser_GUI gui;
        const auto controls = controlExamples();
        const auto source = std::find_if(controls.begin(), controls.end(), [](const auto& model) {
            return model.itemId == "fg:item:000008";
        });
        check(source != controls.end(), "accepted L49 E/Em source example exists");
        check(source->proposalExample && !source->syntheticFixture &&
                  source->sourceRefs == std::vector<std::string>{"L49-TXT49-61"} &&
                  source->instrument.openMidi == std::vector<int>({40, 45, 50, 55, 59, 64}) &&
                  source->instrument.capo == 0,
              "L49 source identity and standard tuning remain unchanged");

        const auto validation = music::validate(*source);
        check(validation.validReference(), "original L49 source validates without timing edits");
        const auto validated = validation.model;
        tab::Document sourceTab(validated);
        check(!sourceTab.allTimed(), "original L49 source remains untimed for TAB");

        bool sourceReferenceRefused = false;
        try {
            (void)reference::compile(validated, reference_fixtures::config(Rational{8}));
        } catch (const std::invalid_argument&) {
            sourceReferenceRefused = true;
        }
        check(sourceReferenceRefused, "original untimed source remains refused for reference playback compilation");

        desktop::FretboardView view;
        view.setBounds(0, 0, 1024, 560);
        view.setVisible(true);
        checkChord(*source, validated, view, run, false);
        checkChord(*source, validated, view, run, true);

        const std::string eEvent = "fg:item:000008:event:0001";
        check(view.setEvent(validated, eEvent), "right-handed presentation reselects exact E source event");
        auto* board = findChildWithTitle(view, "Fretboard: source event positions");
        check(board != nullptr, "mirrored presentation uses the actual visible board");
        const int rightOpen = markerCenter(*board, 6, 0);
        const int rightFretTwo = markerCenter(*board, 5, 2);
        const auto beforeMarkers = view.markers();
        const auto beforeSource = view.sourceSummary();
        const auto beforeTiming = view.timingSummary();
        const auto beforeStatus = view.statusSummary();
        saveSnapshot(view, run / "l49-e-right-handed.png", "right-handed E source projection");
        view.setHandedness(guitar::Handedness::Left);
        const int leftOpen = markerCenter(*board, 6, 0);
        const int leftFretTwo = markerCenter(*board, 5, 2);
        check(rightOpen < leftOpen && rightFretTwo < leftFretTwo &&
                  std::abs((rightOpen + leftOpen) - (rightFretTwo + leftFretTwo)) <= 2,
              "left-handed setup mirrors open and fretted source marker columns around one board axis");
        bool sameMarkers = view.markers().size() == beforeMarkers.size();
        for (std::size_t i = 0; sameMarkers && i < beforeMarkers.size(); ++i) {
            const auto& a = beforeMarkers[i];
            const auto& b = view.markers()[i];
            sameMarkers = a.sourceId == b.sourceId && a.sourceRef == b.sourceRef &&
                a.eventId == b.eventId && a.chordSymbol == b.chordSymbol &&
                a.pitchName == b.pitchName && a.finger == b.finger &&
                a.internalString == b.internalString && a.displayString == b.displayString &&
                a.relativeFret == b.relativeFret && a.physicalFret == b.physicalFret && a.midi == b.midi;
        }
        check(sameMarkers && view.selectedEventId() == eEvent &&
                  view.sourceSummary() == beforeSource && view.timingSummary() == beforeTiming &&
                  view.statusSummary() == beforeStatus,
              "handedness refresh retains all validated source, pitch, fret, timing and status facts");
        saveSnapshot(view, run / "l49-e-left-handed.png", "left-handed E source projection");
        view.setHandedness(guitar::Handedness::Right);
        check(markerCenter(*board, 6, 0) == rightOpen &&
                  markerCenter(*board, 5, 2) == rightFretTwo,
              "returning to right-handed setup restores original marker columns");

        auto outsideRegion = *source;
        auto outsideEvent = std::find_if(outsideRegion.events.begin(), outsideRegion.events.end(),
                                         [](const auto& event) {
                                             return event.id == "fg:item:000008:event:0001";
                                         });
        outsideEvent->tones.at(1).fret = 23;
        outsideEvent->tones.at(1).midi = 68;
        const auto outsideValidation = music::validate(outsideRegion);
        check(outsideValidation.validReference(), "out-of-region test source remains a valid position-model case");
        check(!view.setEvent(outsideValidation.model, outsideEvent->id),
              "source event beyond the bounded fretboard region is explicitly refused");
        check(view.selectedEventId().empty() && view.markers().empty() &&
                  view.statusSummary().find("a selected source position is unavailable on the displayed instrument") != std::string::npos,
              "out-of-region refusal clears prior projection without clipping or substitution");
        view.setHandedness(guitar::Handedness::Left);
        check(view.selectedEventId().empty() && view.markers().empty() && board->getNumChildComponents() == 0,
              "handedness change cannot resurrect a refused source event");

        check(!source->events.front().span.onset && !source->events.front().span.duration,
              "source event timing remains untouched after all view selections and refusals");
        results.flush();
        check(results.good(), "all fretboard checks flush to checks.tsv");
        std::cout << "PASS " << checks << " source-backed fretboard projection checks; "
                  << "four PNG snapshots; no native playback, app integration, or runtime admission\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << ": " << error.what() << '\n';
        return 1;
    }
}
