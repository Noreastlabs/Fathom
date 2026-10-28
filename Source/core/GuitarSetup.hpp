#pragma once
#include "core/MusicModel.hpp"
#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace fathom::guitar {
enum class Handedness { Right, Left };
enum class Preset { Standard, EFlat, DropD, OpenE };
struct Setup {
    std::string valueVersion = "instrument-initial1";
    std::array<int, 6> openMidi{{40,45,50,55,59,64}}; // low to high
    int capo = 0, fretCount = 22;
    Handedness handedness = Handedness::Right;
};
struct SettingIssue { std::string field, message; };
std::array<int, 6> tuning(Preset);
std::vector<SettingIssue> validate(const Setup&);
int parseCount(const std::string&); // exact decimal integer text0..999, range checked by setup
int parseNote(const std::string&); // exact scientific pitch notation; throws invalid_argument
std::string noteName(int midi); // sharp display convention only; never edits authored spelling
int displayString(int internalString); // internal low1 -> conventional guitar6
int fretColumn(int relativeFret, int columnCount, Handedness);
struct Position {
    std::int64_t physicalFret;
    std::optional<int> midi;
    bool withinFrets;
    bool available() const { return withinFrets && midi.has_value(); }
};
Position position(const Setup&, int internalString, int relativeFret);
struct CompatibilityIssue {
    std::string code, eventId, message;
    int internalString = 0;
};
enum class RequirementStatus { Unspecified, Specified, UnsupportedInstrument };
struct Compatibility {
    RequirementStatus requirementStatus = RequirementStatus::Unspecified;
    bool positionsAssessed = false;
    bool accessAllowed = true;
    bool referenceUsesAuthoredSetup = true;
    std::vector<CompatibilityIssue> warnings;
};
Compatibility compare(const music::ValidatedModel& authored, const Setup& declared);
struct ApplyContext { bool stopped = false, outcomeResolved = false; };
class ActiveSetup final {
public:
    const Setup& current() const noexcept { return value_; }
    std::uint64_t revision() const noexcept { return revision_; }
    std::vector<SettingIssue> apply(const Setup&, ApplyContext);
private:
    Setup value_;
    std::uint64_t revision_ = 0; // session-local; persistent CAS revision belongs store
};
} // namespace fathom::guitar
