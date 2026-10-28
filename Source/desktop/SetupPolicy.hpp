#pragma once
#include "desktop/PresentationPolicy.hpp"
#include "core/AudioOutputLifecycle.hpp"
#include "core/GuitarSetup.hpp"
#include <limits>

namespace fathom::desktop::setup {
enum class Appearance { Default, Light, Dark };
enum class BoardMode { Basic = 0, Finger = 1, Note = 2 };
enum class NoteSpelling { Sharp = 0, Flat = 1 };
struct BoardDisplay {
    bool visible = false;
    BoardMode mode = BoardMode::Basic;
    NoteSpelling spelling = NoteSpelling::Sharp;
};
inline bool operator==(const BoardDisplay& a, const BoardDisplay& b) noexcept {
    return a.visible == b.visible && a.mode == b.mode && a.spelling == b.spelling;
}
inline bool operator!=(const BoardDisplay& a, const BoardDisplay& b) noexcept { return !(a == b); }
inline const char* boardModeName(BoardMode mode) {
    switch (mode) { case BoardMode::Basic: return "basic"; case BoardMode::Finger: return "finger"; case BoardMode::Note: return "note"; }
    throw std::invalid_argument("Unsupported fretboard display mode");
}
inline const char* noteSpellingName(NoteSpelling spelling) {
    switch (spelling) { case NoteSpelling::Sharp: return "sharp"; case NoteSpelling::Flat: return "flat"; }
    throw std::invalid_argument("Unsupported fretboard note spelling");
}
inline void validateBoardDisplay(const BoardDisplay& value) {
    (void)boardModeName(value.mode); (void)noteSpellingName(value.spelling);
}
enum class Step { Welcome, Experience, Appearance, Guitar, Audio, Summary };
inline constexpr const char* preferenceKey = "ui_setup";
inline constexpr std::int64_t namespaceVersion = 1;

// A resumable setup draft, never a device, transport, permission or identity.
// ui_presentation remains the authority for the applied experience disclosure.
struct Model {
    int defaultBpm = 60; // New explicit Learn drafts only; never an active queue or recorded tempo.
    Appearance appearance = Appearance::Default;
    guitar::Setup guitar;
    BoardDisplay boardDisplay; // presentation only; never a declared tuning or activity fact
    output::MixSettings audio;
    presentation::Level experience = presentation::Level::Beginner;
    Step step = Step::Welcome;
    bool completed = false, skipped = false;
};
inline const char* appearanceName(Appearance value) {
    switch (value) {
        case Appearance::Default: return "default";
        case Appearance::Light: return "light";
        case Appearance::Dark: return "dark";
    }
    throw std::invalid_argument("Unsupported setup appearance");
}
inline const char* stepName(Step value) {
    switch (value) {
        case Step::Welcome: return "welcome";
        case Step::Experience: return "experience";
        case Step::Appearance: return "appearance";
        case Step::Guitar: return "guitar";
        case Step::Audio: return "audio";
        case Step::Summary: return "summary";
    }
    throw std::invalid_argument("Unsupported setup step");
}
inline bool operator==(const Model& a, const Model& b) noexcept {
    return a.defaultBpm == b.defaultBpm && a.boardDisplay == b.boardDisplay && a.appearance == b.appearance && a.experience == b.experience && a.step == b.step &&
        a.completed == b.completed && a.skipped == b.skipped &&
        a.guitar.valueVersion == b.guitar.valueVersion && a.guitar.openMidi == b.guitar.openMidi &&
        a.guitar.capo == b.guitar.capo && a.guitar.fretCount == b.guitar.fretCount &&
        a.guitar.handedness == b.guitar.handedness && a.audio.bus == b.audio.bus &&
        a.audio.master == b.audio.master && a.audio.masterMute == b.audio.masterMute &&
        a.audio.muteMask == b.audio.muteMask && a.audio.soloAB == b.audio.soloAB;
}
inline bool operator!=(const Model& a, const Model& b) noexcept { return !(a == b); }
inline void validate(const Model& value) {
    if(value.defaultBpm<20||value.defaultBpm>300)throw std::invalid_argument("Default BPM must be a whole number from 20 to 300");
    validateBoardDisplay(value.boardDisplay);
    (void)appearanceName(value.appearance);
    (void)stepName(value.step);
    presentation::validateLevel(value.experience);
    if (!guitar::validate(value.guitar).empty()) throw std::invalid_argument("Unsupported setup guitar settings");
    if (!value.audio.valid()) throw std::invalid_argument("Unsupported setup audio mix settings");
}
inline json::Value encodePreferences(const Model& value) {
    validate(value);
    json::Value::Array pitches, buses;
    for (const auto pitch : value.guitar.openMidi) pitches.emplace_back(json::Value::fromInteger(pitch));
    for (const auto bus : value.audio.bus) buses.emplace_back(json::Value::fromInteger(bus));
    return json::Value::Object{
        {"default_bpm",json::Value::fromInteger(value.defaultBpm)}, {"version", "setup1"}, {"appearance", appearanceName(value.appearance)},
        {"experience", presentation::levelName(value.experience)}, {"step", stepName(value.step)},
        {"completed", value.completed}, {"skipped", value.skipped},
        {"board_display", json::Value::Object{{"visible", value.boardDisplay.visible},
            {"mode", boardModeName(value.boardDisplay.mode)}, {"spelling", noteSpellingName(value.boardDisplay.spelling)}}},
        {"guitar", json::Value::Object{{"version", value.guitar.valueVersion}, {"open_midi", std::move(pitches)},
            {"capo", json::Value::fromInteger(value.guitar.capo)}, {"fret_count", json::Value::fromInteger(value.guitar.fretCount)},
            {"handedness", value.guitar.handedness == guitar::Handedness::Right ? "right" : "left"}}},
        {"audio", json::Value::Object{{"bus", std::move(buses)}, {"master", json::Value::fromInteger(value.audio.master)},
            {"master_mute", value.audio.masterMute}, {"mute_mask", json::Value::fromInteger(value.audio.muteMask)},
            {"solo_ab", json::Value::fromInteger(value.audio.soloAB)}}}};
}
namespace detail {
inline const json::Value& field(const json::Value& value, const char* key) {
    const auto* result = value.find(key);
    if (!result) throw std::invalid_argument("Missing setup preference field");
    return *result;
}
inline void object(const json::Value& value, std::size_t fields) {
    if (!value.isObject() || value.object().size() != fields)
        throw std::invalid_argument("Exact setup preference object required");
}
inline std::string text(const json::Value& value) {
    if (!value.isString()) throw std::invalid_argument("Setup preference string required");
    return value.string();
}
inline bool boolean(const json::Value& value) {
    if (!value.isBool()) throw std::invalid_argument("Setup preference boolean required");
    return value.boolean();
}
inline int integer(const json::Value& value, int low, int high) {
    std::int64_t result;
    if (!value.integer(result) || result < low || result > high)
        throw std::invalid_argument("Setup preference integer outside supported range");
    return static_cast<int>(result);
}
}
// Read without migration. Saving this extended shape can make it unsupported
// by an older binary; keep existing profile/recovery files before downgrading.
inline Model decodePreferences(const json::Value& value) {
    // Accept the exact legacy shape without writing or migrating on read.
    // Recognized optional board_display and default_bpm fields extend the exact legacy shape.
    detail::object(value, 8+(value.find("board_display")?1:0)+(value.find("default_bpm")?1:0));
    if (detail::text(detail::field(value, "version")) != "setup1")
        throw std::invalid_argument("Unsupported setup preference version");
    Model result;
    if(const auto* bpm=value.find("default_bpm"))result.defaultBpm=static_cast<int>(detail::integer(*bpm,20,300));
    if (const auto* display = value.find("board_display")) {
        detail::object(*display, 3);
        result.boardDisplay.visible = detail::boolean(detail::field(*display, "visible"));
        const auto mode = detail::text(detail::field(*display, "mode"));
        if (mode == "basic") result.boardDisplay.mode = BoardMode::Basic;
        else if (mode == "finger") result.boardDisplay.mode = BoardMode::Finger;
        else if (mode == "note") result.boardDisplay.mode = BoardMode::Note;
        else throw std::invalid_argument("Unsupported fretboard display mode");
        const auto spelling = detail::text(detail::field(*display, "spelling"));
        if (spelling == "sharp") result.boardDisplay.spelling = NoteSpelling::Sharp;
        else if (spelling == "flat") result.boardDisplay.spelling = NoteSpelling::Flat;
        else throw std::invalid_argument("Unsupported fretboard note spelling");
    }
    const auto appearance = detail::text(detail::field(value, "appearance"));
    if (appearance == "default") result.appearance = Appearance::Default;
    else if (appearance == "light") result.appearance = Appearance::Light;
    else if (appearance == "dark") result.appearance = Appearance::Dark;
    else throw std::invalid_argument("Unsupported setup appearance");
    const auto experience = detail::text(detail::field(value, "experience"));
    if (experience == "beginner") result.experience = presentation::Level::Beginner;
    else if (experience == "advanced") result.experience = presentation::Level::Advanced;
    else if (experience == "developer") result.experience = presentation::Level::Developer;
    else throw std::invalid_argument("Unsupported setup experience draft");
    const auto step = detail::text(detail::field(value, "step"));
    if (step == "welcome") result.step = Step::Welcome;
    else if (step == "experience") result.step = Step::Experience;
    else if (step == "appearance") result.step = Step::Appearance;
    else if (step == "guitar") result.step = Step::Guitar;
    else if (step == "audio") result.step = Step::Audio;
    else if (step == "summary") result.step = Step::Summary;
    else throw std::invalid_argument("Unsupported setup step");
    result.completed = detail::boolean(detail::field(value, "completed"));
    result.skipped = detail::boolean(detail::field(value, "skipped"));
    const auto& guitarValue = detail::field(value, "guitar");
    detail::object(guitarValue, 5);
    result.guitar.valueVersion = detail::text(detail::field(guitarValue, "version"));
    const auto& pitches = detail::field(guitarValue, "open_midi");
    if (!pitches.isArray() || pitches.array().size() != 6) throw std::invalid_argument("Exactly six setup pitches required");
    for (std::size_t i = 0; i < 6; ++i) result.guitar.openMidi[i] = detail::integer(pitches.array()[i], 0, 127);
    result.guitar.fretCount = detail::integer(detail::field(guitarValue, "fret_count"), 0, 36);
    result.guitar.capo = detail::integer(detail::field(guitarValue, "capo"), 0, result.guitar.fretCount);
    const auto hand = detail::text(detail::field(guitarValue, "handedness"));
    if (hand == "right") result.guitar.handedness = guitar::Handedness::Right;
    else if (hand == "left") result.guitar.handedness = guitar::Handedness::Left;
    else throw std::invalid_argument("Unsupported setup handedness");
    const auto& audio = detail::field(value, "audio");
    detail::object(audio, 5);
    const auto& buses = detail::field(audio, "bus");
    if (!buses.isArray() || buses.array().size() != 4) throw std::invalid_argument("Exactly four setup mix buses required");
    for (std::size_t i = 0; i < 4; ++i) result.audio.bus[i] = detail::integer(buses.array()[i], 0, 100);
    result.audio.master = detail::integer(detail::field(audio, "master"), 0, 100);
    result.audio.masterMute = detail::boolean(detail::field(audio, "master_mute"));
    result.audio.muteMask = static_cast<std::uint8_t>(detail::integer(detail::field(audio, "mute_mask"), 0, 15));
    result.audio.soloAB = static_cast<std::uint8_t>(detail::integer(detail::field(audio, "solo_ab"), 0, 3));
    validate(result);
    return result;
}
inline bool preferenceValidator(const std::string& key, std::int64_t version, const json::Value& value) noexcept {
    if (key != preferenceKey || version != namespaceVersion) return false;
    try { (void)decodePreferences(value); return true; } catch (...) { return false; }
}
} // namespace fathom::desktop::setup
