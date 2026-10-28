#include "tasks/OrderedContactFamily.hpp"
#include "content/StrictJson.hpp"
#include "GeneratedOrderedContactData.hpp"
#include <algorithm>
#include <iterator>
#include <map>
#include <set>
#include <stdexcept>

namespace fathom::tasks::ordered_contacts {
namespace {
using J = json::Value;
using compiled::StoredRow;
void need(bool condition, const char* reason) {
    if (!condition) throw std::invalid_argument(reason);
}
bool hex(const std::string& value) {
    return value.size() == 64 && value.find_first_not_of("0123456789abcdef") == std::string::npos;
}
const J& at(const J& value, const char* key) {
    need(value.isObject(), "ORDERED_CONTACT_METADATA_TYPE");
    const auto* found = value.find(key);
    need(found != nullptr, "ORDERED_CONTACT_METADATA_FIELD");
    return *found;
}
std::string stroke(Start start) {
    need(start == Start::Down || start == Start::Up, "ORDERED_CONTACT_UNKNOWN_START");
    return start == Start::Down ? "D" : "U";
}
std::string packetRef(const StoredRow& row) {
    return std::string(row.packetPath) + "#sha256=" + row.packetSha + "#jsonl=" + std::to_string(row.packetLine)
        + "#record=" + row.recordSha;
}
std::string eventId(const StoredRow& row, const std::string& selected, int ordinal) {
    return std::string(row.key) + "/selected-" + selected + "/contact-" + std::to_string(ordinal);
}
std::string eventRef(const StoredRow& row, const compiled::StoredContact& contact) {
    return packetRef(row) + "#source-line=" + std::to_string(contact.line) + "#column=" + std::to_string(contact.column);
}
struct Registry {
    std::vector<std::string> keys;
    std::map<std::string, std::size_t> indices;
    std::vector<J> contexts;
    Registry() {
        need(std::size(compiled::rows) == 1401 && std::size(compiled::contacts) == 59528,
             "ORDERED_CONTACT_CLOSED_DENOMINATOR");
        need(hex(compiled::cohortSha) && hex(compiled::closureSha), "ORDERED_CONTACT_CLOSURE_HASH");
        for (const auto* encoded : compiled::contexts) contexts.push_back(json::parse(encoded));
        std::set<std::string> identities;
        std::size_t next = 0;
        for (std::size_t index = 0; index < std::size(compiled::rows); ++index) {
            const auto& row = compiled::rows[index];
            need(indices.emplace(row.key, index).second && identities.insert(row.identity).second,
                 "ORDERED_CONTACT_DUPLICATE_IDENTITY");
            need(hex(row.recordSha) && hex(row.packetSha) && row.packetLine > 0 && row.level >= 2 && row.level <= 11,
                 "ORDERED_CONTACT_ROW_BINDING");
            need(row.begin == next && row.count > 0 && row.count <= std::size(compiled::contacts) - next
                 && row.context < contexts.size(), "ORDERED_CONTACT_ROW_RANGE");
            const auto unit = json::parse(row.preserved);
            need(at(unit, "source_key").string() == row.key && at(unit, "source_identity").string() == row.identity
                 && at(unit, "source_record_canonical_sha256").string() == row.recordSha,
                 "ORDERED_CONTACT_METADATA_IDENTITY");
            need(at(unit, "projection_scope").string() == "selected_traversal_only"
                 && !at(unit, "full_exercise_completed").boolean()
                 && !at(unit, "runtime_admitted").boolean() && !at(unit, "official_accepted").boolean()
                 && at(unit, "acoustic_sounding_span").null(), "ORDERED_CONTACT_SCOPE_BOUNDARY");
            const auto& ctx = contexts[row.context];
            need(at(ctx, "source_schema").string() == "fathom-private-source-implementation.1",
                 "ORDERED_CONTACT_SOURCE_SCHEMA");
            const auto& projection = at(at(ctx, "timing_authority"), "selected_projection").string();
            need(projection == "straight_sixteenth" || projection == "straight_eighth_connected",
                 "ORDERED_CONTACT_TIMING_SCOPE");
            const std::string down = row.down, up = row.up;
            need(down.size() == row.count && up.size() == row.count, "ORDERED_CONTACT_VARIANT_EXTENT");
            Rational cursor;
            for (std::size_t ordinal = 0; ordinal < row.count; ++ordinal) {
                const auto& contact = compiled::contacts[row.begin + ordinal];
                const Rational onset{contact.onsetN, contact.onsetD}, duration{contact.durationN, contact.durationD};
                need(contact.ordinal == static_cast<int>(ordinal + 1) && onset == cursor && Rational{} < duration,
                     "ORDERED_CONTACT_METRIC_ORDER");
                need(contact.string >= 1 && contact.string <= 6 && contact.fret >= 0 && contact.finger >= 1
                     && contact.finger <= 4 && contact.midi >= 0 && contact.midi <= 127
                     && contact.line > 0 && contact.column > 0, "ORDERED_CONTACT_TYPED_FIELDS");
                const int tuning[] = {40, 45, 50, 55, 59, 64};
                need(tuning[contact.string - 1] + contact.fret == contact.midi, "ORDERED_CONTACT_PITCH_POSITION");
                need(down[ordinal] == (ordinal % 2 == 0 ? 'D' : 'U')
                     && up[ordinal] == (ordinal % 2 == 0 ? 'U' : 'D'), "ORDERED_CONTACT_PICK_PARITY");
                cursor = onset + duration;
            }
            need(cursor == Rational{row.endN, row.endD}, "ORDERED_CONTACT_SELECTED_TERMINAL");
            keys.emplace_back(row.key);
            next += row.count;
        }
        need(next == std::size(compiled::contacts), "ORDERED_CONTACT_UNUSED_OR_OVERLAPPING_DATA");
    }
};
const Registry& registry() { static const Registry instance; return instance; }
}

const std::vector<std::string>& keys() { return registry().keys; }
const Definition& definition(const std::string& key) {
    const auto& table = registry();
    need(table.indices.count(key) == 1, "ORDERED_CONTACT_UNKNOWN_OR_EXCLUDED_KEY");
    static const auto definitions = [] {
        std::map<std::string, Definition> out;
        for (const auto& entry : registry().indices) out.emplace(entry.first, Definition(entry.second));
        return out;
    }();
    return definitions.at(key);
}
const char* cohortSha256() { (void)registry(); return compiled::cohortSha; }
const char* closureSha256() { (void)registry(); return compiled::closureSha; }
std::size_t sharedContextCount() { return registry().contexts.size(); }
const char* Definition::sourceKey() const { return compiled::rows[index_].key; }
const char* Definition::sourceIdentity() const { return compiled::rows[index_].identity; }
const char* Definition::sourceRecordSha256() const { return compiled::rows[index_].recordSha; }
const char* Definition::packetPath() const { return compiled::rows[index_].packetPath; }
const char* Definition::packetSha256() const { return compiled::rows[index_].packetSha; }
int Definition::packetLine() const { return compiled::rows[index_].packetLine; }
int Definition::level() const { return compiled::rows[index_].level; }
std::size_t Definition::contactCount() const { return compiled::rows[index_].count; }
Rational Definition::metricEnd() const { const auto& row = compiled::rows[index_]; return Rational{row.endN, row.endD}; }
std::string Definition::retainedMetadataJson() const {
    const auto& row = compiled::rows[index_];
    auto metadata = json::parse(row.preserved);
    metadata.object().emplace("source_context", registry().contexts[row.context]);
    return json::stringify(metadata);
}
music::Model Definition::reference(Start start) const {
    const auto& row = compiled::rows[index_];
    const auto selected = stroke(start);
    const char* directions = start == Start::Down ? row.down : row.up;
    music::Model model;
    model.itemId = std::string("private-source-projection:") + row.key + "#" + selected;
    model.schemaVersion = "fathom.music-selected-contact-reference.1";
    model.contentVersion = std::string(compiled::contentVersion) + "/" + compiled::closureSha + "/" + selected;
    model.contentRevision = 1;
    model.sourceRefs = {packetRef(row), std::string("source-identity:") + row.identity};
    model.instrument.openMidi = {40, 45, 50, 55, 59, 64};
    model.preservedRecordJson = retainedMetadataJson();
    for (std::size_t ordinal = 0; ordinal < row.count; ++ordinal) {
        const auto& contact = compiled::contacts[row.begin + ordinal];
        music::Event event;
        event.id = eventId(row, selected, contact.ordinal);
        event.sourceRef = eventRef(row, contact);
        event.kind = music::Kind::Contact;
        event.contact = music::Contact::Pitched;
        event.span = {Rational{contact.onsetN, contact.onsetD}, Rational{contact.durationN, contact.durationD}};
        event.handDirection = std::string(1, directions[ordinal]);
        music::Tone tone;
        tone.string = contact.string; tone.fret = contact.fret; tone.midi = contact.midi;
        tone.finger = std::to_string(contact.finger); tone.spelling = contact.spelling;
        // Deliberately unassigned: the metric hand slot is not a sounding gate.
        event.tones.push_back(std::move(tone));
        model.events.push_back(std::move(event));
    }
    // Model::terminal asserts ending scoped silence. metricEnd() retains the
    // source traversal endpoint without adding a rest or acoustic observation.
    return model;
}
void Definition::requireSourceParity(const music::Model& model, Start start) const {
    const auto& row = compiled::rows[index_];
    const auto selected = stroke(start);
    const std::string directions = start == Start::Down ? row.down : row.up;
    const std::vector<std::string> expectedRefs{packetRef(row), std::string("source-identity:") + row.identity};
    need(model.itemId == std::string("private-source-projection:") + row.key + "#" + selected
         && model.schemaVersion == "fathom.music-selected-contact-reference.1"
         && model.contentVersion == std::string(compiled::contentVersion) + "/" + compiled::closureSha + "/" + selected
         && model.contentRevision == 1 && model.sourceRefs == expectedRefs
         && model.preservedRecordJson == retainedMetadataJson()
         && model.instrument.openMidi == std::vector<int>({40, 45, 50, 55, 59, 64}) && model.instrument.capo == 0
         && model.proposalExample && !model.syntheticFixture && !model.terminal && model.measures.empty()
         && !model.backing && model.events.size() == row.count, "ORDERED_CONTACT_REFERENCE_SCOPE_PARITY");
    for (std::size_t index = 0; index < model.events.size(); ++index) {
        const auto& a = model.events[index]; const auto& contact = compiled::contacts[row.begin + index];
        const music::Span span{Rational{contact.onsetN, contact.onsetD}, Rational{contact.durationN, contact.durationD}};
        need(a.id == eventId(row, selected, contact.ordinal) && a.sourceRef == eventRef(row, contact)
             && a.kind == music::Kind::Contact && a.contact == music::Contact::Pitched
             && a.span == span && a.handDirection == std::string(1, directions[index]) && a.scopeStrings.empty()
             && a.chordSymbol.empty() && a.tones.size() == 1, "ORDERED_CONTACT_EVENT_SOURCE_PARITY");
        const auto& x = a.tones.front();
        need(x.string == contact.string && x.fret == contact.fret && x.midi == contact.midi
             && x.finger == std::to_string(contact.finger) && x.spelling == contact.spelling
             && x.attack == music::Attack::Picked && x.degrees.empty()
             && x.tieFrom.empty() && x.authoredTechnique.empty() && !x.bendSemitones && !x.bend
             && !x.memberSpan && !x.soundingSpan, "ORDERED_CONTACT_TONE_SOURCE_PARITY");
    }
}
} // namespace fathom::tasks::ordered_contacts
