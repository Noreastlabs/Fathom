#include "core/GuitarSetup.hpp"
#include <algorithm>
#include <cctype>
#include <limits>
#include <stdexcept>

namespace fathom::guitar {
std::array<int,6> tuning(Preset preset) {
    switch (preset) {
        case Preset::Standard: return {{40,45,50,55,59,64}};
        case Preset::EFlat: return {{39,44,49,54,58,63}};
        case Preset::DropD: return {{38,45,50,55,59,64}};
        case Preset::OpenE: return {{40,47,52,56,59,64}};
    }
    throw std::invalid_argument("Unknown guitar tuning preset");
}
std::vector<SettingIssue> validate(const Setup& setup) {
    std::vector<SettingIssue> issues;
    if (setup.valueVersion != "instrument-initial1")
        issues.push_back({"version", "Unsupported setup version; retain the stored value and current setup."});
    for (std::size_t i = 0; i < setup.openMidi.size(); ++i)
        if (setup.openMidi[i] < 0 || setup.openMidi[i] > 127)
            issues.push_back({"string" + std::to_string(6-i), "Choose a pitch from C-1 to G9 (MIDI0..127)."});
    if (setup.fretCount < 0 || setup.fretCount > 36)
        issues.push_back({"frets", "Enter a physical fret count from0 to36."});
    if (setup.capo < 0 || setup.capo > setup.fretCount)
        issues.push_back({"capo", "Place the full capo between0 and the configured last physical fret."});
    if (setup.handedness != Handedness::Right && setup.handedness != Handedness::Left)
        issues.push_back({"handedness", "Choose right-handed or left-handed orientation."});
    return issues;
}
int parseCount(const std::string& text) {
    if (text.empty() || text.size() > 3 || !std::all_of(text.begin(),text.end(),[](char c){ return c >= '0' && c <= '9'; }))
        throw std::invalid_argument("Enter a whole nonnegative number, without spaces or decimal points.");
    int value = 0;
    for (char c : text) value = value * 10 + c - '0';
    return value;
}
int parseNote(const std::string& text) {
    const auto fail = []() -> int { throw std::invalid_argument("Use a note and octave, e.g. E2, Eb2 or F#3; supported pitches C-1 through G9."); };
    if (text.size() < 2 || text.size() > 5) return fail();
    const char letter = static_cast<char>(std::toupper(static_cast<unsigned char>(text.front())));
    const std::string letters = "CDEFGAB";
    const int natural[] = {0,2,4,5,7,9,11};
    const auto index = letters.find(letter);
    if (index == std::string::npos) return fail();
    std::size_t i = 1;
    int accidental = 0;
    if (text[i] == 'b' || text[i] == '#') {
        const char marker = text[i++]; accidental = marker == 'b' ? -1 : 1;
        if (i < text.size() && text[i] == marker) { accidental *= 2; ++i; }
    } else if (text[i] == 'x') { accidental = 2; ++i; }
    bool negative = false;
    if (i < text.size() && text[i] == '-') { negative = true; ++i; }
    if (i + 1 != text.size() || text[i] < '0' || text[i] > '9') return fail();
    int octave = text[i] - '0';
    if (negative) { if (octave != 1) return fail(); octave = -1; }
    const int midi = (octave + 1) * 12 + natural[index] + accidental;
    if (midi < 0 || midi > 127) return fail();
    return midi;
}
std::string noteName(int midi) {
    if (midi < 0 || midi > 127) throw std::invalid_argument("Pitch outside MIDI representation");
    const char* names[] = {"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};
    return std::string(names[midi % 12]) + std::to_string(midi / 12 - 1);
}
int displayString(int internal) {
    if (internal < 1 || internal > 6) throw std::invalid_argument("Six-string product index required");
    return 7 - internal;
}
int fretColumn(int fret, int columns, Handedness hand) {
    if (columns < 1 || fret < 0 || fret >= columns || (hand != Handedness::Right && hand != Handedness::Left))
        throw std::invalid_argument("Invalid fretboard orientation position");
    return hand == Handedness::Right ? fret : columns - 1 - fret;
}
Position position(const Setup& setup, int internal, int fret) {
    if (!validate(setup).empty() || internal < 1 || internal > 6 || fret < 0)
        throw std::invalid_argument("Valid setup, string and nonnegative relative fret required");
    const auto physical = static_cast<std::int64_t>(setup.capo) + fret;
    const auto pitch = setup.openMidi[static_cast<std::size_t>(internal-1)] + physical;
    return {physical, pitch <= 127 ? std::optional<int>{static_cast<int>(pitch)} : std::nullopt, physical <= setup.fretCount};
}
Compatibility compare(const music::ValidatedModel& authored, const Setup& declared) {
    if (!validate(declared).empty()) throw std::invalid_argument("Validate draft before compatibility comparison");
    Compatibility result;
    const auto& model = authored.source();
    if (model.instrument.openMidi.empty()) return result;
    result.requirementStatus = RequirementStatus::Specified;
    if (model.instrument.openMidi.size() != 6) {
        result.requirementStatus = RequirementStatus::UnsupportedInstrument;
        result.warnings.push_back({"instrument", "", "This reference is not a six-string guitar setup; its source remains accessible.", 0});
        return result;
    }
    for (int string = 1; string <= 6; ++string)
        if (declared.openMidi[static_cast<std::size_t>(string-1)] != model.instrument.openMidi[static_cast<std::size_t>(string-1)])
            result.warnings.push_back({"tuning", "", "String " + std::to_string(displayString(string)) + " differs from the lesson tuning. Continue with lesson reference or explicitly update current setup.", string});
    if (declared.capo != model.instrument.capo)
        result.warnings.push_back({"capo", "", "Current capo differs from the lesson requirement. Continue with authored lesson reference or update current setup.", 0});
    for (const auto& event : model.events) for (const auto& tone : event.tones) {
        result.positionsAssessed = true;
        const auto actual = position(declared,tone.string,tone.fret);
        const auto requiredPhysical = static_cast<std::int64_t>(model.instrument.capo) + tone.fret;
        if (!actual.withinFrets || requiredPhysical > declared.fretCount)
            result.warnings.push_back({"unavailable_fret",event.id,"String " + std::to_string(displayString(tone.string)) + ", relative fret " + std::to_string(tone.fret) + " exceeds the configured neck in the current or required capo setup. Source remains accessible.",tone.string});
        if (!actual.midi)
            result.warnings.push_back({"pitch_range",event.id,"Current setup exceeds supported MIDI pitch at this position; no clamped or substituted tone.",tone.string});
        else if (tone.attack != music::Attack::Harmonic && *actual.midi != tone.midi)
            result.warnings.push_back({"pitch_mismatch",event.id,"Current setup would sound " + noteName(*actual.midi) + " here; lesson pitch remains " + noteName(tone.midi) + ". No automatic transposition.",tone.string});
    }
    return result;
}
std::vector<SettingIssue> ActiveSetup::apply(const Setup& draft, ApplyContext context) {
    auto issues = validate(draft);
    if (!context.stopped || !context.outcomeResolved)
        issues.push_back({"context", "Stop and resolve the current outcome before applying a setup change."});
    if (revision_ == std::numeric_limits<std::uint64_t>::max())
        issues.push_back({"revision", "Setup revision is exhausted; current setup retained."});
    if (issues.empty()) { value_ = draft; ++revision_; }
    return issues;
}
} // namespace fathom::guitar
