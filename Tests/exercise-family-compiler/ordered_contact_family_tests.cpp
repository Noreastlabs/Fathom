#include "tasks/OrderedContactFamily.hpp"
#include "content/StrictJson.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>

namespace {
using J = fathom::json::Value;
using fathom::Rational;
namespace family = fathom::tasks::ordered_contacts;
std::size_t assertions = 0, refusals = 0;
void check(bool value, const char* reason) {
    ++assertions;
    if (!value) throw std::runtime_error(reason);
}
const J& at(const J& value, const std::string& key) {
    check(value.isObject() && value.find(key), "SOURCE_OBJECT_FIELD");
    return *value.find(key);
}
std::int64_t integer(const J& value) {
    std::int64_t number = 0;
    check(value.integer(number), "SOURCE_INTEGER_TYPE");
    return number;
}
Rational metric(const J& value) {
    if (value.isArray()) {
        check(value.array().size() == 2, "SOURCE_RATIONAL_PAIR");
        return Rational{integer(value.array()[0]), integer(value.array()[1])};
    }
    std::int64_t number = 0;
    if (value.integer(number)) return Rational{number};
    check(value.isNumber(), "SOURCE_METRIC_TYPE");
    auto token = std::get<fathom::json::Number>(value.data).token;
    const auto dot = token.find('.');
    check(dot != std::string::npos && token.find_first_not_of("0123456789.") == std::string::npos,
          "SOURCE_DECIMAL_METRIC");
    const auto decimals = token.size() - dot - 1;
    check(decimals <= 8, "SOURCE_DECIMAL_BOUND");
    token.erase(dot, 1);
    std::int64_t denominator = 1;
    for (std::size_t i = 0; i < decimals; ++i) denominator *= 10;
    return Rational{static_cast<std::int64_t>(std::stoll(token)), denominator};
}
std::string sha256(const std::string& bytes) {
    check(bytes.size() <= std::numeric_limits<CC_LONG>::max(), "SOURCE_HASH_SIZE");
    std::array<unsigned char, CC_SHA256_DIGEST_LENGTH> hash{};
    CC_SHA256(bytes.data(), static_cast<CC_LONG>(bytes.size()), hash.data());
    std::ostringstream out;
    for (const auto byte : hash) out << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(byte);
    return out.str();
}
struct SourceCache {
    std::filesystem::path root;
    std::map<std::string, std::vector<std::string>> packets;
    std::size_t bytes = 0;
    J record(const family::Definition& definition) {
        const std::string path = definition.packetPath();
        if (!packets.count(path)) {
            std::ifstream input(root / path, std::ios::binary);
            check(input.good(), "SOURCE_FILE_OPEN");
            std::ostringstream buffer; buffer << input.rdbuf();
            const auto raw = buffer.str();
            check(sha256(raw) == definition.packetSha256(), "SOURCE_FILE_SHA256");
            bytes += raw.size();
            std::istringstream stream(raw);
            std::string line;
            while (std::getline(stream, line)) packets[path].push_back(line);
        }
        const auto& lines = packets.at(path);
        check(definition.packetLine() > 0 && static_cast<std::size_t>(definition.packetLine()) <= lines.size(), "SOURCE_JSONL_LINE");
        return fathom::json::parse(lines[static_cast<std::size_t>(definition.packetLine() - 1)]);
    }
};
template<class Function> void refuses(Function&& action) {
    bool rejected = false;
    try { action(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "EXPECTED_SOURCE_REFUSAL"); ++refusals;
}
void metadataParity(const family::Definition& definition, const J& source) {
    const auto meta = fathom::json::parse(definition.retainedMetadataJson());
    const auto& context = at(meta, "source_context");
    const auto& payload = at(source, "source_payload");
    const auto& implementation = at(source, "implementation");
    check(at(source, "package_key").string() == definition.sourceKey()
          && at(source, "source_identity").string() == definition.sourceIdentity(), "ORIGINAL_SOURCE_IDENTITY");
    check(at(context, "source_schema") == at(source, "schema_version"), "ORIGINAL_SOURCE_SCHEMA");
    check(at(meta, "source_record_canonical_sha256").string() == definition.sourceRecordSha256(), "RETAINED_RECORD_FINGERPRINT");
    check(at(context, "timing_authority") == at(source, "timing_authority"), "WHOLE_SOURCE_TIMING_AUTHORITY");
    check(at(meta, "printed_label") == at(payload, "printed_label") && at(meta, "heading_path") == at(payload, "parent_path"), "SOURCE_HEADING_UNIT");
    check(at(meta, "unit_instruction_lines") == at(payload, "instruction_lines")
          && at(meta, "unit_direction_task_steps") == at(implementation, "task_steps"), "SOURCE_UNIT_DIRECTION_INSTRUCTIONS");
    check(at(context, "ordering_basis") == at(implementation, "ordering_basis"), "SOURCE_ORDERING_BASIS");
    check(!at(meta, "full_exercise_completed").boolean() && !at(meta, "runtime_admitted").boolean()
          && !at(meta, "official_accepted").boolean() && at(meta, "acoustic_sounding_span").null(), "SOURCE_SCOPE_BOUNDARY");
    const auto& sourceRefs = at(source, "source_refs").array();
    const auto& assets = at(context, "source_assets").array();
    const auto& locators = at(meta, "source_locators").array();
    check(sourceRefs.size() == assets.size() && assets.size() == locators.size(), "SOURCE_LOCATOR_CARDINALITY");
    for (std::size_t i = 0; i < sourceRefs.size(); ++i) {
        auto asset = sourceRefs[i];
        check(at(asset, "locator") == locators[i], "EXACT_ORIGINAL_LOCATOR");
        asset.object().erase("locator");
        check(asset == assets[i], "EXACT_ORIGINAL_SOURCE_ASSET_PIN");
    }
    const auto& originalVariants = at(implementation, "relative_variants").array();
    const auto& instructions = at(context, "variant_instructions").array();
    check(originalVariants.size() == instructions.size(), "SOURCE_VARIANT_API_CARDINALITY");
    for (std::size_t i = 0; i < originalVariants.size(); ++i) {
        auto instruction = originalVariants[i];
        instruction.object().erase("strokes"); instruction.object().erase("contact_ordinals");
        check(instruction == instructions[i], "EXACT_ORIGINAL_VARIANT_INSTRUCTIONS");
    }
}
void sourceParity(const family::Definition& definition, const J& source,
                  const fathom::music::Model& model, family::Start start) {
    const auto& impl = at(source, "implementation");
    const auto& contacts = at(impl, "ordered_contacts").array();
    const J* variant = nullptr;
    const std::string selected = start == family::Start::Down ? "D" : "U";
    for (const auto& candidate : at(impl, "relative_variants").array())
        if (at(candidate, "start_stroke").string() == selected) variant = &candidate;
    check(variant && model.events.size() == contacts.size(), "ORIGINAL_SOURCE_VARIANT");
    check(definition.metricEnd() == metric(at(at(source, "timing_authority"), "end_q"))
          && definition.metricEnd() == metric(at(*variant, "end_q")), "EXACT_SELECTED_TERMINAL");
    const auto& strokes = at(*variant, "strokes").array();
    const auto& ordinals = at(*variant, "contact_ordinals").array();
    check(strokes.size() == contacts.size() && ordinals.size() == contacts.size(), "ORIGINAL_VARIANT_ORDER_EXTENT");
    for (std::size_t index = 0; index < contacts.size(); ++index) {
        const auto& expected = contacts[index]; const auto& event = model.events[index];
        check(event.kind == fathom::music::Kind::Contact && event.contact == fathom::music::Contact::Pitched
              && event.tones.size() == 1, "PITCHED_CONTACT_KIND");
        const auto& tone = event.tones.front();
        check(integer(at(expected, "ordinal")) == static_cast<std::int64_t>(index + 1)
              && integer(ordinals[index]) == static_cast<std::int64_t>(index + 1), "ORIGINAL_CONTACT_ORDINAL");
        check(tone.string == integer(at(expected, "string_low_to_high")) && tone.fret == integer(at(expected, "fret"))
              && tone.midi == integer(at(expected, "midi")) && tone.finger == std::to_string(integer(at(expected, "finger"))), "ORIGINAL_PHYSICAL_PITCH_FINGER");
        const auto* spelling = expected.find("note_spelling");
        if (!spelling) spelling = expected.find("spelling");
        check(tone.spelling == (spelling && !spelling->null() ? spelling->string() : ""), "ORIGINAL_SPELLING_OR_UNSPECIFIED");
        check(event.span.onset && *event.span.onset == metric(at(expected, "onset_q"))
              && event.span.duration && *event.span.duration == metric(at(expected, "duration_q")), "ORIGINAL_RATIONAL_HAND_SPAN");
        check(event.handDirection == strokes[index].string() && tone.attack == fathom::music::Attack::Picked
              && !tone.soundingSpan, "ORIGINAL_PICK_AND_UNKNOWN_GATE");
        const auto locator = "#source-line=" + std::to_string(integer(at(expected, "source_line")))
            + "#column=" + std::to_string(integer(at(expected, "source_column_1based")));
        check(event.sourceRef.find(locator) != std::string::npos, "EXACT_CONTACT_LOCATOR");
    }
    check(!model.terminal && !model.events.empty() && model.events.back().span.onset
          && model.events.back().span.duration
          && *model.events.back().span.onset + *model.events.back().span.duration == definition.metricEnd(), "SOURCE_END_WITHOUT_INVENTED_REST");
}
}

int main(int argc, char** argv) {
    const auto begin = std::chrono::steady_clock::now();
    try {
        check(argc == 2, "SOURCE_ROOT_ARGUMENT");
        SourceCache sourceCache{std::filesystem::path(argv[1]), {}, 0};
        const auto& keys = family::keys();
        check(keys.size() == 1401 && std::set<std::string>(keys.begin(), keys.end()).size() == 1401, "CLOSED_NATIVE_KEYS");
        check(std::string(family::cohortSha256()) == "a6e3c5166d5fa4d2f1a282830cfca994ba93616088939704b0b5c18cb6e11dc0", "COHORT_SHA");
        std::size_t variants = 0, contacts = 0, unresolvedGates = 0, representatives = 0;
        std::set<int> representedLevels;
        for (const auto& key : keys) {
            const auto& definition = family::definition(key);
            const auto source = sourceCache.record(definition);
            metadataParity(definition, source);
            contacts += definition.contactCount();
            for (const auto start : {family::Start::Down, family::Start::Up}) {
                auto model = definition.reference(start);
                definition.requireSourceParity(model, start);
                sourceParity(definition, source, model, start);
                const auto validation = fathom::music::validate(model);
                check(validation.validReference(), "EXISTING_CORE_REFERENCE_VALIDATION");
                check(validation.issues.size() == definition.contactCount(), "EXACT_UNKNOWN_GATE_COUNT");
                for (const auto& issue : validation.issues) {
                    check(issue.severity == fathom::music::Severity::Unresolved && issue.code == "unresolved_gate", "NO_UNEXPECTED_NATIVE_ISSUE");
                    ++unresolvedGates;
                }
                ++variants;
                if (!representedLevels.count(definition.level())) {
                    const auto readiness = fathom::music::assessReadiness(*validation.model,
                        {{fathom::music::Attack::Picked}, false, false, false, false});
                    check(!readiness.technicallyRenderable && !readiness.curriculumPlaybackAuthorized, "UNKNOWN_GATE_AND_ADMISSION_BOUNDARY");
                    ++representatives;
                }
            }
            representedLevels.insert(definition.level());
        }
        check(variants == 2802 && contacts == 59528 && unresolvedGates == 119056, "ALL_ROW_VARIANT_CONTACT_COUNTS");
        const auto& first = family::definition(keys.front());
        refuses([&] { (void)family::definition("unknown-source-key"); });
        refuses([&] { (void)family::definition("proposed-printed-l004-set-1-of-9-exercises-001-012-exercise-006-1234"); });
        refuses([&] { (void)family::definition("proposed-printed-l002-set-1-of-9-exercises-001-012-exercise-002-1213"); });
        refuses([&] { (void)first.reference(static_cast<family::Start>(9)); });
        auto coherent = first.reference(family::Start::Down);
        ++coherent.events.front().tones.front().fret; ++coherent.events.front().tones.front().midi;
        check(fathom::music::validate(coherent).validReference(), "COHERENT_PITCH_MUTATION_CONTROL");
        refuses([&] { first.requireSourceParity(coherent, family::Start::Down); });
        auto wrongFinger = first.reference(family::Start::Down);
        wrongFinger.events.front().tones.front().finger = "8";
        check(!fathom::music::validate(wrongFinger).validReference(), "CORE_WRONG_FINGER_REFUSAL");
        refuses([&] { first.requireSourceParity(wrongFinger, family::Start::Down); });
        auto wrongMidi = first.reference(family::Start::Down);
        ++wrongMidi.events.front().tones.front().midi;
        check(!fathom::music::validate(wrongMidi).validReference(), "CORE_PITCH_POSITION_REFUSAL");
        refuses([&] { first.requireSourceParity(wrongMidi, family::Start::Down); });
        auto wrongClock = first.reference(family::Start::Down);
        wrongClock.events.front().span.duration = Rational{};
        check(!fathom::music::validate(wrongClock).validReference(), "CORE_ZERO_SPAN_REFUSAL");
        refuses([&] { first.requireSourceParity(wrongClock, family::Start::Down); });
        auto wrongOrder = first.reference(family::Start::Down);
        std::swap(wrongOrder.events[0], wrongOrder.events[1]);
        check(!fathom::music::validate(wrongOrder).validReference(), "CORE_REORDER_REFUSAL");
        refuses([&] { first.requireSourceParity(wrongOrder, family::Start::Down); });
        auto inventedGate = first.reference(family::Start::Down);
        inventedGate.events.front().tones.front().soundingSpan = inventedGate.events.front().span;
        refuses([&] { first.requireSourceParity(inventedGate, family::Start::Down); });
        auto inventedSilence = first.reference(family::Start::Down);
        inventedSilence.terminal = first.metricEnd();
        check(!fathom::music::validate(inventedSilence).validReference(), "CORE_SILENCE_TERMINAL_REFUSAL");
        refuses([&] { first.requireSourceParity(inventedSilence, family::Start::Down); });
        auto promoted = first.reference(family::Start::Down);
        promoted.proposalExample = false;
        refuses([&] { first.requireSourceParity(promoted, family::Start::Down); });
        auto wrongStart = first.reference(family::Start::Up);
        refuses([&] { first.requireSourceParity(wrongStart, family::Start::Down); });
        auto wrongMetadata = first.reference(family::Start::Down);
        wrongMetadata.preservedRecordJson = "{}";
        refuses([&] { first.requireSourceParity(wrongMetadata, family::Start::Down); });
        const auto seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - begin).count();
        std::cout << "{\"result\":\"PASS\",\"rows\":1401,\"saved_variants\":" << variants
            << ",\"contacts\":" << contacts << ",\"assertions\":" << assertions << ",\"source_parity_refusals\":" << refusals
            << ",\"unresolved_sounding_gates\":" << unresolvedGates << ",\"source_packets_SHA256_verified_once\":" << sourceCache.packets.size()
            << ",\"source_payload_bytes\":" << sourceCache.bytes << ",\"representative_readiness_cases\":" << representatives
            << ",\"shared_contexts\":" << family::sharedContextCount() << ",\"seconds\":" << seconds
            << ",\"core_valid_references\":2802,\"renderability_or_runtime_admission_claimed\":false,\"whole_exercise_children_closed\":0}" << '\n';
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
