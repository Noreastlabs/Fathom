#pragma once
// Exact P86/P87 Level21 source packet and separate P02 three-case runtime authority.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel021Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J = json::Value;
    auto require = [](bool ok, const char* reason) { if (!ok) throw std::runtime_error(reason); };
    auto at = [](const J& value, const char* key) -> const J& { return value.object().at(key); };
    auto number = [&](const J& value) { std::int64_t n{};
        require(value.integer(n), "Level21 integer source fact differs"); return n; };
    require(expectedDispositionSha.size() == 64 &&
            content::sha256(disposition) == expectedDispositionSha,
            "Level21 decision hash differs from installed authority pin");
    json::Limits limits; limits.bytes = 16384; limits.depth = 10;
    limits.values = 260; limits.stringBytes = 4096;
    const auto d = json::parse(disposition, limits);
    const std::set<std::string> fields{
        "authority_name", "conditional_decision_evidence", "conditional_decision_sha256",
        "decision_evidence", "decision_sha256", "domain_review_evidence", "domain_review_sha256",
        "package_sha256", "prior_installed_review_evidence", "prior_installed_review_sha256",
        "profile_sha256", "recorded_utc", "registry_sha256", "scope",
        "source_contacts_picking_timing_accepted", "source_provenance_sha256",
        "source_review_evidence", "source_review_sha256", "stable_identities_accepted",
        "status", "three_case_runtime_eligible", "version"};
    std::set<std::string> actual;
    for (const auto& field : d.object()) actual.insert(field.first);
    require(actual == fields, "Unsupported Level21 decision fields");
    require(at(d, "version").string() == "level021-first-three-curriculum-decision.1" &&
            at(d, "status").string() == "ACCEPTED", "Level21 case decision is not accepted");
    for (const char* key : {"authority_name", "recorded_utc", "decision_evidence",
                            "source_review_evidence", "domain_review_evidence",
                            "conditional_decision_evidence", "prior_installed_review_evidence"})
        require(at(d, key).isString() && !at(d, key).string().empty(),
                "Level21 authority attribution missing");
    for (const char* key : {"source_contacts_picking_timing_accepted",
                            "stable_identities_accepted", "three_case_runtime_eligible"})
        require(at(d, key).isBool() && at(d, key).boolean(),
                "Level21 exact three-case runtime acceptance missing");
    require(at(d, "source_review_sha256").string() ==
                "af2d9f0ee0bf032144c94f0e59d331dd490271bf1131aafea492668451b9d803" &&
            at(d, "domain_review_sha256").string() ==
                "c7d328dd6eab1a013dfb234f67a549722e2ab1cc66db6a9acd9b376cdf15d4d4" &&
            at(d, "conditional_decision_sha256").string() ==
                "01287db70a20a52bda8eceb923e6579b33421ea112faf0bd2f6087c672679f20" &&
            at(d, "prior_installed_review_sha256").string() ==
                "974874a1b5d793cd2895ffce90301d77df7d755570a6eb8f18f3e86f18d78764",
            "Level21 independent source, domain, Curriculum or prior installed authority differs");
    constexpr const char* packageSha = "6a9d7d2e8c642e60fa432fcf2dd8aa12bdafb4d583fbbfb431eeb7441ee68fe8";
    constexpr const char* profileSha = "9bf94b5aec6eb3624720d7c29d8ae04334e92e1900456c7e14d946530711d4de";
    constexpr const char* registrySha = "33a3c82a30e13f46a407520635a5002e2c39dbcc933654359de9a3883f6f548e";
    constexpr const char* provenanceSha = "2c94ab8520e8401cc7db4c00d5b351dd62d5528f0f6013f836835bd5adc82a1a";
    require(content::sha256(input.package) == packageSha &&
            at(d, "package_sha256").string() == packageSha, "Level21 canonical package changed");
    require(content::sha256(input.profile) == profileSha &&
            at(d, "profile_sha256").string() == profileSha &&
            input.expectedProfileSha256 == profileSha, "Level21 canonical profile changed");
    require(content::sha256(input.registry) == registrySha &&
            at(d, "registry_sha256").string() == registrySha, "Level21 canonical registry changed");
    require(content::sha256(provenance) == provenanceSha &&
            at(d, "source_provenance_sha256").string() == provenanceSha,
            "Level21 event provenance changed");
    const auto scope = json::parse(R"fathom({"automatic_credit":false,"cases":[{"events":16,"gap_after_event":0,"gap_duration_q":0,"item_id":"fg:item:001168","module_id":"fg:module:001168","second_gap_after_event":0,"second_gap_duration_q":0,"span_q":8,"variant_ids":["fg:variant:007458","fg:variant:007459"]},{"events":32,"gap_after_event":16,"gap_duration_q":1,"item_id":"fg:item:001169","module_id":"fg:module:001169","second_gap_after_event":0,"second_gap_duration_q":0,"span_q":17,"variant_ids":["fg:variant:007460","fg:variant:007461"]},{"events":48,"gap_after_event":16,"gap_duration_q":1,"item_id":"fg:item:001170","module_id":"fg:module:001170","second_gap_after_event":32,"second_gap_duration_q":1,"span_q":26,"variant_ids":["fg:variant:007462","fg:variant:007463"]}],"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false})fathom");
    require(at(d, "scope") == scope, "Level21 case, pause or no-credit decision scope differs");
    const auto package = json::parse(input.package);
    require(at(package, "content_version").string() ==
                "curriculum-v1-level021-first-three-cases-build-only.1" &&
            at(package, "records").array().size() == 3 &&
            at(package, "sources").object().size() == 7,
            "Level21 package version, cases or original source count differs");
    const auto refs = json::parse(R"(["L21-TXT-GUIDANCE","L21-PDF-GUIDANCE","L21-TXT-RUNG01","L21-TXT-RUNG02","L21-TXT-RUNG03","L21-PDF-CARDS01-03","L21-PDF-ROUTE"])");
    const std::array<const char*, 3> items{
        "fg:item:001168", "fg:item:001169", "fg:item:001170"};
    const std::array<const char*, 3> modules{
        "fg:module:001168", "fg:module:001169", "fg:module:001170"};
    const std::array<std::array<const char*, 2>, 3> variants{{
        {{"fg:variant:007458", "fg:variant:007459"}},
        {{"fg:variant:007460", "fg:variant:007461"}},
        {{"fg:variant:007462", "fg:variant:007463"}}}};
    for (std::size_t i = 0; i < 3; ++i) {
        const auto& record = at(package, "records").array()[i];
        require(at(record, "id").string() == items[i] &&
                at(record, "module_id").string() == modules[i] &&
                at(record, "workbook_id").string() == "fg:workbook:000021" &&
                at(record, "content_revision") == J::fromInteger(1) &&
                at(record, "legacy_level") == J::fromInteger(21) &&
                at(record, "runtime_eligible").isBool() &&
                !at(record, "runtime_eligible").boolean() &&
                at(record, "source_refs") == refs && at(record, "authored_text_refs") == refs &&
                at(record, "events").array().size() == (i + 1) * 16,
                "Level21 selected identity, nonadmission or source closure differs");
    }
    auto result = content::validate(input);
    require(result.validReference && result.exitCode == 2 &&
            result.records.size() == 3 && result.variants.size() == 6,
            "Level21 native source reference failed or admitted itself");
    const auto sidecar = json::parse(provenance);
    require(at(sidecar, "events").object().size() == 96 &&
            at(sidecar, "variant_strokes").object().size() == 6,
            "Level21 source-event or pick provenance coverage differs");
    std::set<std::string> seen;
    for (auto& variant : result.variants) {
        std::size_t ci = 3;
        for (std::size_t i = 0; i < 3; ++i) if (variant.itemId == items[i]) ci = i;
        require(ci < 3 && seen.insert(variant.id).second &&
                variant.bindingsComplete && variant.readiness.technicallyRenderable &&
                variant.validation.validReference(),
                "Level21 variant foreign, duplicate or unavailable");
        const bool downStart = variant.id == variants[ci][0];
        require(downStart || variant.id == variants[ci][1],
                "Level21 variant does not belong to selected source case");
        const std::size_t count = (ci + 1) * 16;
        auto& model = variant.source;
        require(!model.syntheticFixture && model.events.size() == count &&
                model.measures.empty() &&
                model.instrument.openMidi == std::vector<int>{40, 45, 50, 55, 59, 64} &&
                model.instrument.capo == 0, "Level21 event count or standard setup differs");
        const auto& strokes = at(at(sidecar, "variant_strokes"), variant.id.c_str()).array();
        require(strokes.size() == count, "Level21 continuous pick provenance count differs");
        for (std::size_t i = 0; i < count; ++i) {
            auto& event = model.events[i];
            const auto& evidence = at(at(sidecar, "events"), event.id.c_str());
            const auto& authored = at(package, "records").array()[ci].object().at("events").array()[i];
            const Rational onset = Rational{static_cast<std::int64_t>(i), 2} +
                Rational{i >= 16 ? 1 : 0} + Rational{i >= 32 ? 1 : 0};
            const auto& slot = at(authored, "onset_q").array();
            const auto& duration = at(authored, "duration_q").array();
            require(at(authored, "event_id").string() == event.id &&
                    slot.size() == 2 && duration.size() == 2 &&
                    at(evidence, "nominal_slot_q") == at(authored, "onset_q") &&
                    Rational{number(slot[0]), number(slot[1])} == onset &&
                    Rational{number(duration[0]), number(duration[1])} == Rational{1, 2},
                    "Level21 authored q1/2 timing, event or rest seam differs");
            require(event.kind == music::Kind::Note && event.span.onset == onset &&
                    event.span.duration == Rational{1, 2} && event.tones.size() == 1 &&
                    event.sourceRef == at(evidence, "source_txt_ref").string(),
                    "Level21 native note, onset, duration or source differs");
            const auto& tone = event.tones.front();
            require(number(at(evidence, "source_string")) == tone.string &&
                    number(at(evidence, "source_fret")) == tone.fret &&
                    number(at(evidence, "source_midi")) == tone.midi &&
                    std::to_string(number(at(evidence, "source_finger"))) == tone.finger &&
                    at(evidence, "source_pitch_spelling").string() == tone.spelling &&
                    tone.attack == music::Attack::Picked && tone.tieFrom.empty(),
                    "Level21 printed string, fret, finger, pitch or articulation differs");
            const auto& degrees = at(authored, "degree_contexts").object();
            require(degrees.size() == 1 &&
                    at(degrees.begin()->second, "source_label") == at(evidence, "source_degree"),
                    "Level21 printed natural-minor degree differs");
            require(number(at(evidence, "source_rung")) == static_cast<std::int64_t>(i / 16 + 1) &&
                    number(at(evidence, "source_contact")) == static_cast<std::int64_t>(i % 16 + 1) &&
                    at(evidence, "repeated_high_root_at_turn").boolean() ==
                        (i % 16 == 7 || i % 16 == 8),
                    "Level21 original rung, contact or repeated octave root differs");
            const bool seam = (i == 15 || i == 31) && i + 1 < count;
            require(at(evidence, "one_beat_release_after_cell").boolean() == seam &&
                    number(at(evidence, "frame_move_frets")) == (seam ? 1 : 0),
                    "Level21 authored released-pressure whole-frame shift differs");
            const char* stroke = ((i % 2 == 0) == downStart) ? "D" : "U";
            require(strokes[i].string() == stroke,
                    "Level21 D/U cycle resets at root or shift");
            event.handDirection = stroke;
        }
        variant.validation = music::validate(model);
        require(variant.validation.validReference(),
                "Level21 picked-stroke projection failed native validation");
    }
    require(seen == std::set<std::string>{"fg:variant:007458", "fg:variant:007459",
                                          "fg:variant:007460", "fg:variant:007461",
                                          "fg:variant:007462", "fg:variant:007463"},
            "Level21 exact six variant identities differ");
    return result;
}
} // namespace fathom::lesson
