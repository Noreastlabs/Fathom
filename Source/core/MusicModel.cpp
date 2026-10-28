#include "core/MusicModel.hpp"
#include <algorithm>
#include <cstdint>
#include <map>
#include <set>
#include <stdexcept>

namespace fathom::music {
namespace {
int mod12(std::int64_t n) { return static_cast<int>((n % 12 + 12) % 12); }
bool midiValid(int n) { return n >= 0 && n <= 127; }
bool resolved(const Span& span) { return span.onset && span.duration; }
bool overlap(const Span& a, const Span& b) {
    return resolved(a) && resolved(b) && *a.onset < *b.onset + *b.duration && *b.onset < *a.onset + *a.duration;
}
bool contains(const std::vector<int>& values, int value) { return std::find(values.begin(), values.end(), value) != values.end(); }
Span soundingSpan(const Event& e, const Tone& t) {
    return e.kind == Kind::Contact ? t.soundingSpan.value_or(Span{}) : e.span;
}
bool cancels(const Event& event, int string) {
    return event.kind == Kind::Contact && (event.contact == Contact::Release || event.contact == Contact::Muted) && contains(event.scopeStrings, string);
}
bool contradictory(const std::vector<Issue>& issues) {
    return std::any_of(issues.begin(), issues.end(), [](const Issue& i) { return i.severity == Severity::Contradiction; });
}
const Tone* matchingTone(const Event& event, const Tone& tone) {
    for (const auto& previous : event.tones)
        if (previous.string == tone.string && previous.fret == tone.fret && previous.midi == tone.midi) return &previous;
    return nullptr;
}
}

int pitchClass(const std::string& spelling) {
    if (spelling.empty()) throw std::invalid_argument("Empty authored spelling");
    const std::string letters = "CDEFGAB";
    const int pitches[] = {0, 2, 4, 5, 7, 9, 11};
    const auto index = letters.find(spelling[0]);
    if (index == std::string::npos) throw std::invalid_argument("Spelling requires uppercase A..G");
    const auto accidental = spelling.substr(1);
    int offset = 0;
    if (accidental == "#") offset = 1;
    else if (accidental == "##" || accidental == "x") offset = 2;
    else if (accidental == "b") offset = -1;
    else if (accidental == "bb") offset = -2;
    else if (!accidental.empty()) throw std::invalid_argument("Unsupported spelling; octave must be represented explicitly");
    return mod12(pitches[index] + offset);
}
int intervalSemitones(int fromMidi, int toMidi) {
    if (!midiValid(fromMidi) || !midiValid(toMidi)) throw std::invalid_argument("MIDI outside 0..127");
    return toMidi - fromMidi;
}
std::vector<int> scalePitchClasses(int root, const std::vector<int>& intervals) {
    if (root < 0 || root > 11 || intervals.empty() || intervals.front() != 0)
        throw std::invalid_argument("Scale requires root pitch class and explicit root-first intervals");
    std::vector<int> result;
    int previous = -1;
    for (int n : intervals) {
        if (n <= previous || n > 11) throw std::invalid_argument("Scale intervals must increase within octave");
        result.push_back(mod12(root + n)); previous = n;
    }
    return result;
}

ValidatedModel::ValidatedModel(Model source) : source_(std::make_shared<const Model>(std::move(source))) {
    for (const auto& e : source_->events) {
        EventProjection projection{e.id, e.kind, e.span, {}, e.contact, e.scopeStrings, e.handDirection};
        for (const auto& t : e.tones)
            projection.tones.push_back({t.string, t.fret, t.midi, t.finger, t.spelling, t.degrees, t.attack, t.tieFrom, soundingSpan(e,t), t.bend});
        projections_.push_back(std::move(projection));
    }
}

Validation validate(const Model& source) {
    Validation result;
    auto issue = [&](Severity severity, const std::string& id, const std::string& field, const std::string& code, const std::string& message) {
        result.issues.push_back({severity, id, field, code, message});
    };
    auto invalid = [&](const std::string& id, const std::string& field, const std::string& code, const std::string& message) {
        issue(Severity::Contradiction, id, field, code, message);
    };
    auto unresolved = [&](const std::string& id, const std::string& field, const std::string& code, const std::string& message) {
        issue(Severity::Unresolved, id, field, code, message);
    };
    if (source.itemId.empty() || source.contentRevision <= 0 || source.schemaVersion.empty() || source.contentVersion.empty())
        invalid("", "identity", "identity", "Item and independent schema/content/revision required");
    if (!source.syntheticFixture && source.sourceRefs.empty()) invalid("", "sourceRefs", "provenance", "Reference model needs source provenance");
    if (source.instrument.capo < 0) invalid("", "capo", "capo", "Capo cannot be negative");
    for (int pitch : source.instrument.openMidi) if (!midiValid(pitch)) invalid("", "tuning", "tuning", "Open MIDI outside representation range0..127");
    if (source.backing) {
        const auto& lane=*source.backing;
        const auto hex=[](const std::string& h) {
            return h.size()==64 && h.find_first_not_of("0123456789abcdef")==std::string::npos;
        };
        if (lane.sourceRef.empty() || std::find(source.sourceRefs.begin(),source.sourceRefs.end(),lane.sourceRef)==source.sourceRefs.end()
            || !hex(lane.sourceSha256) || !hex(lane.eventDigestSha256))
            invalid("","backing","backing_provenance","Backing source and two SHA-256 bindings must be declared");
        if (lane.modelChoice!="agent:l39-v1-sine-a3-fsharp3-full-section-gate-80permille" || lane.levelMilli!=80)
            invalid("","backing","backing_default","Unsupported or unattributed backing render defaults");
        if (lane.contacts.size()!=source.events.size() || lane.contacts.empty())
            invalid("","backing","backing_contacts","Backing binding must cover each unchanged melodic contact exactly once");
        else for (std::size_t i=0;i<lane.contacts.size();++i) {
            const auto& c=lane.contacts[i];const auto& e=source.events[i];
            if (e.kind!=Kind::Note || e.tones.size()!=1 || c.eventId!=e.id || !e.span.onset || !e.span.duration
                || !(c.onset==*e.span.onset) || !(c.duration==*e.span.duration)
                || c.string!=e.tones[0].string || c.fret!=e.tones[0].fret || c.midi!=e.tones[0].midi)
                invalid(e.id,"backing.contacts","backing_contact_drift","Melodic contact differs from the bound Version 1 source grid");
        }
        if (lane.sections.size()!=4) invalid("","backing","backing_section_count","Version 1 requires exactly four two-bar backing sections");
        else {
            const int expectedPc[]={9,6,9,6};const int expectedMidi[]={57,54,57,54};
            for (std::size_t i=0;i<4;++i) {
                const auto& s=lane.sections[i];
                if (!(s.onset==Rational{static_cast<std::int64_t>(8*i)}) || !(s.duration==Rational{8})
                    || s.centerPitchClass!=expectedPc[i] || s.midi!=expectedMidi[i] || mod12(s.midi)!=s.centerPitchClass)
                    invalid("","backing.sections","backing_center","Wrong/swapped center, pitch class, model octave, or two-bar gate");
            }
            if (source.events.size()!=32 || !source.events.back().span.onset || !source.events.back().span.duration
                || !(*source.events.back().span.onset+*source.events.back().span.duration==Rational{32}))
                invalid("","backing","backing_extent","Backing and 32-contact metric extent differ");
        }
    }
    std::map<std::string, const Event*> earlier;
    std::map<int, const Event*> lastOnString;
    // Conservatively reserve the full declared muted hand span on its strings.
    // Its shorter synthetic attack never licenses another incompatible action.
    std::map<int, Rational> mutedEnds, restEnds, releaseEnds, sustainEnds, pitchedEnds, releasePoints;
    std::optional<Rational> lastOnset;
    try {
        for (const auto& e : source.events) {
            if (e.kind != Kind::Note && e.kind != Kind::Chord && e.kind != Kind::Rest && e.kind != Kind::Contact)
                invalid(e.id, "kind", "event_kind", "Unknown required event kind");
            if (e.kind == Kind::Contact && e.contact != Contact::Pitched && e.contact != Contact::Muted && e.contact != Contact::Air && e.contact != Contact::Release && e.contact != Contact::Sustain)
                invalid(e.id, "contact", "contact_kind", "Unknown required contact operation");
            if (e.id.empty() || earlier.count(e.id)) invalid(e.id, "id", "duplicate_identity", "Event identity must be nonempty and unique");
            if (!resolved(e.span)) unresolved(e.id, "span", "unresolved_time", "No duration or onset inferred for reference material");
            if (resolved(e.span)) (void)(*e.span.onset + *e.span.duration);
            if (e.span.duration && *e.span.duration == Rational{} && !(e.kind == Kind::Contact && e.contact == Contact::Release))
                invalid(e.id, "duration", "zero_duration", "Sound/rest/hand span must have positive duration");
            if (e.span.onset) {
                if (lastOnset && *e.span.onset < *lastOnset) invalid(e.id, "onset", "event_order", "Resolved event sequence must be time ordered");
                lastOnset = e.span.onset;
            }
            if (e.kind == Kind::Note && e.tones.size() != 1) invalid(e.id, "tones", "note_cardinality", "A note contains exactly one tone");
            if (e.kind == Kind::Note && !e.handDirection.empty()) {
                if (e.handDirection != "D" && e.handDirection != "U") invalid(e.id, "handDirection", "direction", "An explicit pitched note stroke must be D or U");
                if (e.tones.size() == 1 && (e.tones[0].attack != Attack::Picked || !e.tones[0].tieFrom.empty()))
                    invalid(e.id, "handDirection", "pick_attack", "An explicit pitched note stroke requires its own picked attack");
            }
            if (e.kind == Kind::Chord && e.tones.empty()) unresolved(e.id, "tones", "unresolved_voicing", "Chord symbol alone supplies no voicing");
            if (e.kind == Kind::Chord && !e.handDirection.empty()) {
                if (e.handDirection != "D" && e.handDirection != "U") invalid(e.id, "handDirection", "direction", "An explicit chord stroke must be D or U");
                for (const auto& tone : e.tones)
                    if (tone.attack != Attack::Picked || !tone.tieFrom.empty())
                        invalid(e.id, "handDirection", "pick_attack", "An explicit chord stroke requires every member to be picked without a held link");
            }
            if (e.kind == Kind::Rest && !e.tones.empty()) invalid(e.id, "tones", "pitched_rest", "Rest contains no pitches");
            if (e.kind == Kind::Contact) {
                if (e.contact == Contact::Air && !e.scopeStrings.empty()) invalid(e.id,"scopeStrings","air_scope","Air movement has no string contact");
                if (e.contact == Contact::Muted && e.scopeStrings.empty()) unresolved(e.id,"scopeStrings","unresolved_scope","Muted contact needs a string identity");
                if (e.contact == Contact::Pitched && e.tones.empty()) unresolved(e.id, "tones", "unresolved_binding", "Pitched contact requires explicit note/chord binding");
                if (e.contact != Contact::Pitched && !e.tones.empty()) invalid(e.id, "tones", "nonpitched_contact", "Air/muted/release/sustain cannot acquire new pitches");
                if (!e.handDirection.empty() && e.handDirection != "D" && e.handDirection != "U") invalid(e.id, "handDirection", "direction", "Supported authored hand directions are D/U or unspecified");
            }
            if ((e.kind == Kind::Rest || (e.kind == Kind::Contact && (e.contact == Contact::Release || e.contact == Contact::Sustain))) && e.scopeStrings.empty())
                unresolved(e.id, "scopeStrings", "unresolved_scope", "Silence/sustain scope must be explicit before playback; empty is not global");
            std::set<int> scope;
            for (int string : e.scopeStrings)
                if (string < 1 || static_cast<std::size_t>(string) > source.instrument.openMidi.size() || !scope.insert(string).second)
                    invalid(e.id, "scopeStrings", "scope", "Scope strings must be distinct and present in the instrument");
            if (resolved(e.span) && (e.kind == Kind::Rest || (e.kind == Kind::Contact &&
                    (e.contact == Contact::Muted || e.contact == Contact::Release || e.contact == Contact::Sustain)))) {
                const auto onset = *e.span.onset, end = onset + *e.span.duration;
                for (int string : scope) {
                    if (e.kind == Kind::Rest) {
                        const auto mute = mutedEnds.find(string);
                        if (mute != mutedEnds.end() && onset < mute->second)
                            invalid(e.id, "scopeStrings", "rest_muted_overlap", "Scoped rest cannot overlap a muted attack on the same string");
                        auto& prior = restEnds[string];
                        if (prior < end) prior = end;
                    } else if (e.contact == Contact::Muted) {
                        const auto mute = mutedEnds.find(string), rest = restEnds.find(string),
                            release = releaseEnds.find(string), sustain = sustainEnds.find(string),
                            pitched = pitchedEnds.find(string), releasePoint = releasePoints.find(string);
                        if (mute != mutedEnds.end() && onset < mute->second)
                            invalid(e.id, "scopeStrings", "muted_overlap", "Muted attacks on one string cannot overlap");
                        if (rest != restEnds.end() && onset < rest->second)
                            invalid(e.id, "scopeStrings", "rest_muted_overlap", "Muted attack cannot sound inside a scoped rest on the same string");
                        if ((release != releaseEnds.end() && onset < release->second) ||
                            (releasePoint != releasePoints.end() && onset == releasePoint->second))
                            invalid(e.id, "scopeStrings", "release_muted_overlap", "Muted attack cannot coincide with a scoped release on the same string");
                        if (sustain != sustainEnds.end() && onset < sustain->second)
                            invalid(e.id, "scopeStrings", "sustain_muted_overlap", "Muted attack cannot coincide with sustain on the same string");
                        if (pitched != pitchedEnds.end() && onset < pitched->second)
                            invalid(e.id, "scopeStrings", "pitched_muted_overlap", "Muted attack cannot overlap a sounding gate on the same string");
                        auto& prior = mutedEnds[string];
                        if (prior < end) prior = end;
                    } else if (e.contact == Contact::Release) {
                        const auto mute = mutedEnds.find(string);
                        if (mute != mutedEnds.end() && onset < mute->second)
                            invalid(e.id, "scopeStrings", "release_muted_overlap", "Scoped release cannot occur inside a muted contact on the same string");
                        auto& prior = releaseEnds[string];
                        if (prior < end) prior = end;
                        releasePoints[string] = onset;
                    } else if (e.contact == Contact::Sustain) {
                        const auto mute = mutedEnds.find(string);
                        if (mute != mutedEnds.end() && onset < mute->second)
                            invalid(e.id, "scopeStrings", "sustain_muted_overlap", "Sustain cannot coincide with a muted contact on the same string");
                        auto& prior = sustainEnds[string];
                        if (prior < end) prior = end;
                    }
                }
            }
            std::set<int> strings;
            for (const auto& t : e.tones) {
                const auto gate = soundingSpan(e,t);
                if (resolved(gate)) {
                    const auto end = *gate.onset + *gate.duration;
                    if (*gate.duration == Rational{}) invalid(e.id,"soundingSpan","zero_gate","Sounding gate must have positive duration");
                    const auto mute = mutedEnds.find(t.string);
                    if (mute != mutedEnds.end() && *gate.onset < mute->second)
                        invalid(e.id,"soundingSpan","pitched_muted_overlap","Sounding gate cannot enter a muted contact on the same string");
                    auto& prior = pitchedEnds[t.string];
                    if (prior < end) prior = end;
                    for (const auto& cancellation : source.events)
                        if (cancels(cancellation,t.string) && cancellation.span.onset && !(*cancellation.span.onset < *gate.onset) && *cancellation.span.onset < end)
                            invalid(cancellation.id,"scopeStrings","release_gate","Authored release/mute cannot contradict an explicit longer sounding gate; bind its end explicitly");
                }
                if (e.kind == Kind::Contact) {
                    if (!resolved(gate)) unresolved(e.id,"soundingSpan","unresolved_gate","Pitched contact needs its own explicit sounding gate; hand-slot duration supplies none");
                    if (gate.onset && e.span.onset && !(*gate.onset == *e.span.onset)) invalid(e.id,"soundingSpan","contact_gate_onset","Sounding gate must start at the pitched contact");
                    if (t.attack != Attack::Picked) invalid(e.id,"attack","contact_attack","Pitched hand contact cannot silently become a held/legato arrival");
                } else if (t.soundingSpan && !(*t.soundingSpan == e.span)) invalid(e.id,"soundingSpan","conflicting_gate","Note/chord event span is its authoritative sounding gate");
                if (t.attack != Attack::Picked && t.attack != Attack::HammerOn && t.attack != Attack::PullOff && t.attack != Attack::SlideArrival && t.attack != Attack::Bend && t.attack != Attack::BlueThirdShade && t.attack != Attack::Held && t.attack != Attack::Harmonic && t.attack != Attack::Vibrato)
                    invalid(e.id, "attack", "attack_kind", "Unknown required attack kind");
                const bool positionValid = t.string >= 1 && static_cast<std::size_t>(t.string) <= source.instrument.openMidi.size() && t.fret >= 0 && source.instrument.capo >= 0;
                if (!positionValid) invalid(e.id, "position", "position", "Explicit string/fret/capo cannot address a missing or negative position");
                if (!midiValid(t.midi)) invalid(e.id, "midi", "midi", "Sounding MIDI outside0..127");
                if (positionValid) {
                    const auto computed = static_cast<std::int64_t>(source.instrument.openMidi[static_cast<std::size_t>(t.string - 1)]) + source.instrument.capo + t.fret;
                    if (t.attack == Attack::Harmonic)
                        unresolved(e.id, "harmonic", "harmonic_binding", "Preserve harmonic pitch/position; a faithful harmonic relation needs its explicit source binding");
                    else if (computed != t.midi) invalid(e.id, "midi", "pitch_position", "Sounding MIDI contradicts tuning + capo + fret");
                }
                if (!strings.insert(t.string).second) invalid(e.id, "tones", "duplicate_string", "Simultaneous chord tones cannot occupy the same string twice");
                if (!t.finger.empty() && t.finger != "O" && t.finger != "1" && t.finger != "2" && t.finger != "3" && t.finger != "4")
                    invalid(e.id, "finger", "finger", "Finger is1..4/O/unspecified, never degree8/15");
                if (t.finger == "O" && t.fret != 0) invalid(e.id, "finger", "open_finger", "Open finger requires open fret");
                if (!t.spelling.empty()) {
                    try { if (pitchClass(t.spelling) != mod12(t.midi)) invalid(e.id, "spelling", "spelling_pitch", "Authored enharmonic spelling contradicts pitch class"); }
                    catch (const std::invalid_argument& error) { invalid(e.id, "spelling", "spelling", error.what()); }
                }
                for (const auto& degree : t.degrees) {
                    if (degree.ordinal <= 0 || degree.rootPitchClass < 0 || degree.rootPitchClass > 11 || degree.context.empty() || degree.sourceLabel.empty()) {
                        invalid(e.id, "degree", "degree", "Degree needs ordinal, tonal root/context and source label"); continue;
                    }
                    const int lattice[] = {0,2,4,5,7,9,11};
                    const auto ordinal = static_cast<std::int64_t>(degree.ordinal) - 1;
                    const auto semitones = 12 * (ordinal / 7) + lattice[ordinal % 7] + degree.alteration;
                    if (degree.alteration >= -2 && degree.alteration <= 2) {
                        const std::string prefixes[] = {"bb", "b", "", "#", "##"};
                        const auto expected = prefixes[degree.alteration + 2] + std::to_string(degree.ordinal);
                        if (degree.sourceLabel != expected && !(degree.alteration == 2 && degree.sourceLabel == "x" + std::to_string(degree.ordinal)))
                            invalid(e.id, "degree", "degree_label", "Authored degree label disagrees with ordinal/alteration metadata");
                    } else unresolved(e.id, "degree", "degree_notation", "Preserved degree alteration needs an explicitly supported notation rule");
                    if (mod12(degree.rootPitchClass + semitones) != mod12(t.midi)) invalid(e.id, "degree", "degree_pitch", "Degree alteration uses major/perfect lattice, not a second alteration of a minor scale");
                    if (degree.rootMidi && (!midiValid(*degree.rootMidi) || mod12(*degree.rootMidi) != degree.rootPitchClass || static_cast<std::int64_t>(*degree.rootMidi) + semitones != t.midi))
                        invalid(e.id, "degree", "degree_register", "Explicit root register contradicts octave degree/pitch");
                }
                if (t.memberSpan && !(*t.memberSpan == e.span)) invalid(e.id, "memberSpan", "chord_time", "Duplicated chord member timing must equal parent event timing");
                if (t.attack == Attack::Held || !t.tieFrom.empty()) {
                    const auto previous = earlier.find(t.tieFrom);
                    if (t.attack != Attack::Held || t.tieFrom.empty() || previous == earlier.end() || !matchingTone(*previous->second, t))
                        invalid(e.id, "tieFrom", "tie_identity", "Held link must be backward and retain string/fret/pitch without repicking");
                    else {
                        const auto previousGate = soundingSpan(*previous->second,*matchingTone(*previous->second,t));
                        if (!resolved(gate) || !resolved(previousGate)) unresolved(e.id, "tieFrom", "tie_time", "Held continuity needs explicit structural gates");
                        else {
                            if (!(*previousGate.onset + *previousGate.duration == *gate.onset)) invalid(e.id,"tieFrom","tie_continuity","Held segments must touch exactly");
                            for (const auto& cancellation:source.events)
                                if (cancels(cancellation,t.string) && cancellation.span.onset && !(*cancellation.span.onset < *previousGate.onset) && !(*gate.onset < *cancellation.span.onset))
                                    invalid(e.id,"tieFrom","tie_cancelled","Release/muted contact breaks the held chain, including at its boundary");
                        }
                    }
                }
                if (t.attack == Attack::HammerOn || t.attack == Attack::PullOff || t.attack == Attack::SlideArrival) {
                    const auto previous = lastOnString.find(t.string);
                    if (previous == lastOnString.end()) unresolved(e.id, "attack", "legato_context", "Excerpt lacks preceding same-string technique context");
                    else {
                        const auto& prior = *previous->second;
                        const auto tone = std::find_if(prior.tones.begin(), prior.tones.end(), [&](const Tone& p) { return p.string == t.string; });
                        const auto previousGate = tone == prior.tones.end() ? Span{} : soundingSpan(prior,*tone);
                        if (resolved(previousGate) && resolved(gate)) {
                            if (!(*previousGate.onset + *previousGate.duration == *gate.onset)) invalid(e.id,"attack","legato_gap","Technique transition cannot bridge an unarticulated gap");
                            for(const auto& cancellation:source.events)
                                if(cancels(cancellation,t.string) && cancellation.span.onset && !(*cancellation.span.onset < *previousGate.onset) && !(*gate.onset < *cancellation.span.onset))
                                    invalid(e.id,"attack","legato_cancelled","Release/muted contact interrupts this legato transition");
                        } else unresolved(e.id,"attack","legato_time","Technique continuity needs explicit sounding gates");
                        if (tone != prior.tones.end() && ((t.attack == Attack::HammerOn && t.fret <= tone->fret) || (t.attack == Attack::PullOff && t.fret >= tone->fret) || (t.attack == Attack::SlideArrival && t.fret == tone->fret)))
                            invalid(e.id, "attack", "legato_direction", "Technique arrival contradicts the preceding fret direction");
                    }
                }
                if (t.attack == Attack::Bend) {
                    if (!t.bend) unresolved(e.id,"bend","bend_binding","Bend needs a typed target and timed contour");
                    else if (!resolved(gate)) unresolved(e.id,"bend","bend_gate","Bend contour needs a finite sounding gate");
                    else {
                        const auto& b=*t.bend;
                        if(t.bendSemitones && !(*t.bendSemitones==b.targetSemitones))
                            invalid(e.id,"bend","bend_target_mismatch","Display bend amount must match typed contour target");
                        const auto& knots=b.knots;
                        const bool prebent=b.mode==BendMode::PrebentRelease;
                        if(prebent && !b.initialOffsetSemitones)
                            invalid(e.id,"bend","bend_initial_state","Pre-bent release requires an explicit silent initial offset");
                        if(!prebent && b.initialOffsetSemitones)
                            invalid(e.id,"bend","bend_initial_mode","An initial pre-bend offset requires pre-bent release mode");
                        if (!(Rational{}<b.targetSemitones) || knots.size()<4 || knots.size()>64)
                            invalid(e.id,"bend","bend_shape","Bend needs a positive target and a finite four-knot contour");
                        else {
                            const auto end=*gate.onset+*gate.duration;
                            if (!(knots.front().q==*gate.onset) || !(knots.back().q==end)
                                || !(knots.front().offsetSemitones==(prebent?b.targetSemitones:Rational{}))
                                || !(knots.back().offsetSemitones==Rational{}))
                                invalid(e.id,"bend","bend_endpoint",prebent?
                                    "Pre-bent contour must begin at target on attack and end at base at the exact gate end":
                                    "Contour must start at base and return to base at exact gate end");
                            if(prebent && b.initialOffsetSemitones && !(*b.initialOffsetSemitones==b.targetSemitones))
                                invalid(e.id,"bend","bend_initial_state","Silent pre-bend offset must equal the positive target");
                            bool plateau=false, rising=false, falling=false, sequenceBroken=false;
                            enum class BendPhase { Rise, Hold, Release };
                            auto phase=BendPhase::Rise;
                            for (std::size_t k=0;k<knots.size();++k) {
                                const auto& point=knots[k];
                                if (b.targetSemitones<point.offsetSemitones || point.q<*gate.onset || end<point.q)
                                    invalid(e.id,"bend","bend_range","Contour knot exceeds target or sounding gate");
                                if (k) {
                                    const auto& prior=knots[k-1];
                                    if (!(prior.q<point.q)) invalid(e.id,"bend","bend_time","Contour knots must increase strictly");
                                    if (prior.offsetSemitones<point.offsetSemitones) rising=true;
                                    if (point.offsetSemitones<prior.offsetSemitones) falling=true;
                                    if (prior.offsetSemitones==b.targetSemitones && point.offsetSemitones==b.targetSemitones) plateau=true;
                                    if(prebent) {
                                        if(prior.offsetSemitones<point.offsetSemitones) sequenceBroken=true;
                                        if(point.offsetSemitones<prior.offsetSemitones && !plateau) sequenceBroken=true;
                                    } else {
                                        if (phase==BendPhase::Rise) {
                                            if (point.offsetSemitones<prior.offsetSemitones) sequenceBroken=true;
                                            if (prior.offsetSemitones==b.targetSemitones) {
                                                if (point.offsetSemitones==b.targetSemitones) phase=BendPhase::Hold;
                                                else sequenceBroken=true; // no target hold before release
                                            }
                                        } else if (phase==BendPhase::Hold) {
                                            if (point.offsetSemitones<b.targetSemitones) phase=BendPhase::Release;
                                        } else if (prior.offsetSemitones<point.offsetSemitones) sequenceBroken=true;
                                    }
                                }
                            }
                            if ((prebent && (!plateau || !falling)) || (!prebent && (!rising || !plateau || !falling)))
                                invalid(e.id,"bend","bend_motion",prebent?
                                    "Pre-bent release must hold the target audibly, then descend to base without repick":
                                    "Bend must rise to target, hold, and release without repick");
                            if (sequenceBroken)
                                invalid(e.id,"bend","bend_sequence",prebent?
                                    "Pre-bent release must hold target before a monotonic descent without rebound":
                                    "Bend must rise monotonically, hold target, then release monotonically");
                        }
                    }
                } else if (t.bend) invalid(e.id,"bend","bend_attack","Only Bend attack may carry a bend contour");
                if (t.attack == Attack::BlueThirdShade)
                    unresolved(e.id,"bend","bend_binding","Blue-third shade still needs its own explicit capability");
            }
            for (const auto& entry : earlier) {
                const auto& previous = *entry.second;
                for (const auto& t : e.tones) {
                    for(const auto& p:previous.tones)
                        if(p.string==t.string && overlap(soundingSpan(previous,p),soundingSpan(e,t))) invalid(e.id,"span","string_overlap","Two sounding gates overlap on the same string");
                    if (previous.kind == Kind::Rest && contains(previous.scopeStrings,t.string) && overlap(previous.span,soundingSpan(e,t))) invalid(e.id,"span","rest_overlap","Explicit scoped rest overlaps a sounding gate on that string");
                }
                if (e.kind == Kind::Rest)
                    for(const auto& p:previous.tones) if(contains(e.scopeStrings,p.string) && overlap(e.span,soundingSpan(previous,p))) invalid(e.id,"span","rest_overlap","Explicit scoped rest overlaps a sounding gate on that string");
            }
            if(e.kind==Kind::Contact && e.contact==Contact::Sustain && resolved(e.span)) {
                for(int string:e.scopeStrings) {
                    bool supported=false;
                    for(const auto& entry:earlier) for(const auto& t:entry.second->tones) {
                        const auto gate=soundingSpan(*entry.second,t);
                        if(t.string==string && resolved(gate) && !(*e.span.onset < *gate.onset) && !(*gate.onset + *gate.duration < *e.span.onset + *e.span.duration)) supported=true;
                    }
                    if(!supported) unresolved(e.id,"scopeStrings","sustain_binding","Sustain needs a previously declared active gate covering its span; no extension invented");
                }
            }
            earlier.emplace(e.id, &e);
            for (const auto& t : e.tones) lastOnString[t.string] = &e;
        }
        if(source.terminal) {
            if(! (Rational{} < *source.terminal))
                invalid("","terminal","terminal_nonpositive","Terminal endpoint must be positive");
            bool terminalRest=false;
            std::map<int,Rational> latestSoundEnd;
            std::set<int> unresolvedSoundStrings;
            std::optional<Rational> terminalTailStart;
            for(const auto& event:source.events) {
                if(resolved(event.span)) {
                    const auto end=*event.span.onset+*event.span.duration;
                    if(*source.terminal<end)
                        invalid(event.id,"terminal","terminal_early","Event extends beyond declared terminal endpoint");
                    if(event.kind==Kind::Rest && end==*source.terminal && !event.scopeStrings.empty())terminalRest=true;
                    // A scoped muted contact is an audible percussive gate, not silence.
                    // Its resolved end moves the terminal tail start on each contacted string.
                    if(event.kind==Kind::Contact && event.contact==Contact::Muted) {
                        for(const int string:event.scopeStrings) {
                            const auto found=latestSoundEnd.find(string);
                            if(found==latestSoundEnd.end() || found->second<end)
                                latestSoundEnd.insert_or_assign(string,end);
                        }
                        if(!event.scopeStrings.empty() && (!terminalTailStart || *terminalTailStart<end))
                            terminalTailStart=end;
                    }
                }
                for(const auto& tone:event.tones) {
                    const auto gate=soundingSpan(event,tone);
                    if(!resolved(gate)) {unresolvedSoundStrings.insert(tone.string);continue;}
                    const auto end=*gate.onset+*gate.duration;
                    if(*source.terminal<end)
                        invalid(event.id,"terminal","terminal_early","Sounding gate extends beyond declared terminal endpoint");
                    const auto found=latestSoundEnd.find(tone.string);
                    if(found==latestSoundEnd.end() || found->second<end)latestSoundEnd.insert_or_assign(tone.string,end);
                    if(!terminalTailStart || *terminalTailStart<end)terminalTailStart=end;
                }
            }
            if(!terminalRest)
                invalid("","terminal","terminal_rest","Terminal endpoint requires an explicit scoped rest ending exactly there");
            for(const int string:unresolvedSoundStrings)
                unresolved("","terminal","terminal_gate_unresolved","Terminal coverage needs an explicit sounding gate on string " + std::to_string(string));
            for(const auto& [string, gateEnd]:latestSoundEnd) {
                // The terminal silence begins after the last sounding gate anywhere in the
                // selected model. Earlier notes on other strings are still part of the music.
                const auto tailStart=terminalTailStart && gateEnd<*terminalTailStart?*terminalTailStart:gateEnd;
                if(!(tailStart<*source.terminal)) {
                    if(tailStart==*source.terminal)
                        invalid("","terminal","terminal_scope","A sounded string reaches terminal without a following scoped rest");
                    continue;
                }
                auto cursor=tailStart;
                std::vector<Span> rests;
                for(const auto& event:source.events)
                    if(event.kind==Kind::Rest && contains(event.scopeStrings,string) && resolved(event.span))
                        rests.push_back(event.span);
                if(rests.empty()) {
                    invalid("","terminal","terminal_scope","Terminal coverage lacks a scoped rest for a sounded string");
                    continue;
                }
                std::sort(rests.begin(),rests.end(),[](const Span& a,const Span& b) {
                    return *a.onset<*b.onset || (*a.onset==*b.onset && *b.duration<*a.duration);
                });
                for(const auto& rest:rests) {
                    const auto end=*rest.onset+*rest.duration;
                    if(!(cursor<end))continue;
                    if(cursor<*rest.onset)break;
                    cursor=end;
                    if(cursor==*source.terminal)break;
                }
                if(cursor<*source.terminal)
                    invalid("","terminal","terminal_rest_gap","Every sounded string needs continuous scoped rest coverage from its latest gate end to terminal");
            }
        }
        for (const auto& measure : source.measures) {
            if (measure.numerator <= 0 || measure.denominator <= 0) { invalid(measure.id, "meter", "meter", "Meter components must be positive"); continue; }
            const Rational length{static_cast<std::int64_t>(measure.numerator) * 4, measure.denominator};
            const auto end = measure.start + length;
            std::vector<Span> spans;
            bool unresolvedCoverage = false;
            std::set<std::string> seen;
            for (const auto& id : measure.eventIds) {
                const auto found = earlier.find(id);
                if (found == earlier.end() || !seen.insert(id).second) { invalid(measure.id, "eventIds", "measure_identity", "Measure references must resolve uniquely"); continue; }
                const auto& span = found->second->span;
                if (!resolved(span)) { unresolvedCoverage = true; unresolved(id, "span", "measure_time", "Cannot prove measure coverage from unresolved times"); continue; }
                if (*span.onset < measure.start || end < *span.onset + *span.duration) invalid(id, "span", "measure_bounds", "Event exceeds declared measure boundary");
                spans.push_back(span);
            }
            if (measure.requireCompleteCoverage && !unresolvedCoverage) {
                std::sort(spans.begin(), spans.end(), [](const Span& a, const Span& b) { return *a.onset < *b.onset; });
                auto cursor = measure.start;
                for (const auto& span : spans) {
                    if (!(*span.onset == cursor)) invalid(measure.id, "coverage", "measure_gap_overlap", "Declared single-stream coverage must include exact notes/rests without gaps/overlap");
                    cursor = *span.onset + *span.duration;
                }
                if (!(cursor == end)) invalid(measure.id, "coverage", "measure_total", "Declared complete measure does not reach its exact end");
            }
        }
    } catch (const std::overflow_error& error) { invalid("", "rational", "arithmetic_range", error.what()); }
    if (!contradictory(result.issues)) result.model = std::shared_ptr<const ValidatedModel>(new ValidatedModel(source));
    return result;
}

Readiness assessReadiness(const ValidatedModel& model, const RendererCapabilities& capabilities) {
    Readiness result;
    result.issues = validate(model.source()).issues;
    if (model.source().events.empty()) result.issues.push_back({Severity::Unresolved,"","events","no_events","Reference/task material has no invented event stream"});
    for (const auto& e : model.source().events) {
        bool unsupportedHeldChord = false;
        for (const auto& tone : e.tones) {
            if (std::find(capabilities.attacks.begin(), capabilities.attacks.end(), tone.attack) == capabilities.attacks.end())
                result.issues.push_back({Severity::Unsupported,e.id,"attack","unsupported_technique","Renderer cannot faithfully present this authored technique"});
            if (tone.attack == Attack::Held && !capabilities.polyphonicHeldChains) {
                const auto origin = std::find_if(model.source().events.begin(), model.source().events.end(),
                    [&](const Event& previous) { return previous.id == tone.tieFrom; });
                if (e.tones.size() != 1 || origin == model.source().events.end() || origin->tones.size() != 1)
                    unsupportedHeldChord = true;
            }
        }
        if (unsupportedHeldChord)
            result.issues.push_back({Severity::Unsupported,e.id,"tieFrom","unsupported_held_chord",
                "Renderer cannot continue a Held chain with a multi-tone event or origin"});
        if (e.kind == Kind::Contact && ((e.contact == Contact::Muted && !capabilities.mutedContact) || (e.contact == Contact::Release && !capabilities.releaseContact) || (e.contact == Contact::Sustain && !capabilities.sustainContact)))
            result.issues.push_back({Severity::Unsupported,e.id,"contact","unsupported_contact","Renderer lacks the declared contact operation"});
    }
    result.technicallyRenderable = result.issues.empty();
    result.issues.push_back({Severity::NotAdmitted,"","admission","not_admitted","Model validation is not catalog/release/Curriculum admission; no runtime authorization supplied here"});
    return result;
}
} // namespace fathom::music
