#pragma once
#include "core/Quantity.hpp"
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace fathom::music {
enum class Kind { Note, Chord, Rest, Contact };
enum class Contact { Pitched, Muted, Air, Release, Sustain };
enum class Attack { Picked, HammerOn, PullOff, SlideArrival, Bend, BlueThirdShade, Held, Harmonic, Vibrato };
enum class Severity { Contradiction, Unresolved, Unsupported, NotAdmitted };
struct Issue { Severity severity; std::string event, field, code, explanation; };
struct Span {
    std::optional<Rational> onset, duration;
    bool operator==(const Span& other) const { return onset == other.onset && duration == other.duration; }
};
struct Instrument { std::vector<int> openMidi; int capo = 0; };
struct Degree {
    std::string context, sourceLabel;
    int rootPitchClass = 0, ordinal = 1, alteration = 0;
    std::optional<int> rootMidi;
};
struct BendKnot { Rational q{}, offsetSemitones{}; };
enum class BendMode { RiseHoldRelease, PrebentRelease };
struct BendContour {
    Rational targetSemitones{};
    std::vector<BendKnot> knots; // absolute quarter positions, linear semitone offsets
    // Omitted mode preserves the existing base-at-attack rise/hold/release contract.
    std::optional<BendMode> mode;
    // Required only for a silent pre-bend: its first audible offset is explicit.
    std::optional<Rational> initialOffsetSemitones;
};
struct Tone {
    int string = 1, fret = 0, midi = 0;
    // Empty means source unspecified; otherwise 1..4 or O (open).
    std::string finger, spelling;
    std::vector<Degree> degrees;
    Attack attack = Attack::Picked;
    std::string tieFrom, authoredTechnique;
    std::optional<Rational> bendSemitones; // existing display field, must agree with typed contour
    std::optional<BendContour> bend;
    // Explicit duplicated member time, when supplied by a source chord record.
    std::optional<Span> memberSpan;
    // Pitched-contact hand slot is not a sounding gate. Binding must supply this.
    std::optional<Span> soundingSpan;
};
struct Event {
    std::string id, sourceRef, chordSymbol;
    Kind kind = Kind::Note;
    Span span;
    std::vector<Tone> tones;
    Contact contact = Contact::Air;
    std::string handDirection;
    // Rest/release/sustain scope is explicit; empty means unresolved, not global.
    std::vector<int> scopeStrings;
};
struct Measure {
    std::string id;
    Rational start;
    int numerator = 4, denominator = 4;
    std::vector<std::string> eventIds;
    bool requireCompleteCoverage = false;
};
// Technical backing is distinct from authored melodic events and has its own provenance.
struct BackingContact {
    std::string eventId;
    Rational onset{}, duration{};
    int string{}, fret{}, midi{};
};
struct BackingSection {
    Rational onset{}, duration{};
    int centerPitchClass{}, midi{};
};
struct BackingLane {
    std::string sourceRef, sourceSha256, eventDigestSha256, modelChoice;
    // Agent rendering default: sine A3/F#3, 8% backing with 92% melodic headroom,
    // each complete two-bar section gated at its exact quarter boundaries.
    int levelMilli{80};
    std::vector<BackingContact> contacts;
    std::vector<BackingSection> sections;
};
struct Model {
    std::string itemId, schemaVersion, contentVersion;
    int contentRevision = 1;
    std::vector<std::string> sourceRefs;
    Instrument instrument;
    std::vector<Event> events;
    std::optional<Rational> terminal; // Explicit finite end of a selected silence-bearing reference.
    std::vector<Measure> measures;
    std::optional<BackingLane> backing;
    // Authored tasks/tables/rubrics/normalization are preserved, never converted to notes.
    std::string preservedRecordJson;
    bool proposalExample = true, syntheticFixture = false;
};
struct ToneProjection {
    int string, fret, soundingMidi;
    std::string finger, spelling;
    std::vector<Degree> degrees;
    Attack attack;
    std::string tieFrom;
    Span soundingSpan;
    std::optional<BendContour> bend;
};
struct EventProjection {
    std::string eventId;
    Kind kind;
    Span span;
    std::vector<ToneProjection> tones;
    Contact contact;
    std::vector<int> scopeStrings;
    std::string handDirection;
};
struct Validation;
class ValidatedModel final {
public:
    const Model& source() const noexcept { return *source_; }
    const std::vector<EventProjection>& projections() const noexcept { return projections_; }
private:
    explicit ValidatedModel(Model source);
    std::shared_ptr<const Model> source_;
    std::vector<EventProjection> projections_;
    friend struct Validation;
    friend Validation validate(const Model&);
};
struct Validation {
    std::shared_ptr<const ValidatedModel> model;
    std::vector<Issue> issues;
    bool validReference() const noexcept { return model != nullptr; }
};
struct RendererCapabilities {
    std::vector<Attack> attacks;
    bool mutedContact = false, releaseContact = false, sustainContact = false;
    // A Held member linked to a multi-tone event needs a renderer that can
    // preserve polyphonic held voices; the reference renderer cannot.
    bool polyphonicHeldChains = false;
};
struct Readiness {
    bool technicallyRenderable = false;
    // This model package supplies no release/admission token or runtime loader.
    bool curriculumPlaybackAuthorized = false;
    std::vector<Issue> issues;
};
Validation validate(const Model& model);
Readiness assessReadiness(const ValidatedModel&, const RendererCapabilities&);
int pitchClass(const std::string& spelling); // A..G with b/bb/#/##/x; no inferred octave.
int intervalSemitones(int fromMidi, int toMidi);
std::vector<int> scalePitchClasses(int rootPitchClass, const std::vector<int>& ascendingIntervals);
} // namespace fathom::music
