#pragma once
// Exact P90/P91 Level22 source packet and separate P02 one-pair runtime authority.
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel022Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J = json::Value;
    auto require = [](bool ok, const char* reason) { if (!ok) throw std::runtime_error(reason); };
    auto at = [](const J& value, const char* key) -> const J& { return value.object().at(key); };
    auto number = [&](const J& value) { std::int64_t n{};
        require(value.integer(n), "Level22 integer source fact differs"); return n; };
    require(expectedDispositionSha.size() == 64 &&
            content::sha256(disposition) == expectedDispositionSha,
            "Level22 decision hash differs from installed authority pin");
    json::Limits limits; limits.bytes = 16384; limits.depth = 10;
    limits.values = 260; limits.stringBytes = 4096;
    const auto d = json::parse(disposition, limits);
    const std::set<std::string> fields{
        "authority_name", "conditional_decision_evidence", "conditional_decision_sha256",
        "decision_evidence", "decision_sha256", "domain_review_evidence", "domain_review_sha256",
        "one_pair_runtime_eligible", "package_sha256", "prior_installed_review_evidence",
        "prior_installed_review_sha256", "profile_sha256", "recorded_utc", "registry_sha256",
        "scope", "source_contacts_picking_timing_accepted", "source_provenance_sha256",
        "source_review_evidence", "source_review_sha256", "stable_identities_accepted",
        "status", "version"};
    std::set<std::string> actual;
    for (const auto& field : d.object()) actual.insert(field.first);
    require(actual == fields, "Unsupported Level22 decision fields");
    require(at(d, "version").string() == "level022-first-neighbor-pair-curriculum-decision.1" &&
            at(d, "status").string() == "ACCEPTED", "Level22 pair decision is not accepted");
    for (const char* key : {"authority_name", "recorded_utc", "decision_evidence",
                            "source_review_evidence", "domain_review_evidence",
                            "conditional_decision_evidence", "prior_installed_review_evidence"})
        require(at(d, key).isString() && !at(d, key).string().empty(),
                "Level22 authority attribution missing");
    for (const char* key : {"source_contacts_picking_timing_accepted",
                            "stable_identities_accepted", "one_pair_runtime_eligible"})
        require(at(d, key).isBool() && at(d, key).boolean(),
                "Level22 exact one-pair runtime acceptance missing");
    require(at(d, "source_review_sha256").string() ==
                "0bd68daf77c6b751108e12d41ec2588f692b39fefb45fe418b3092bf89479d7c" &&
            at(d, "domain_review_sha256").string() ==
                "2c88f9e0f4cbee96561e1c64706dd488b6aa6f608014302de82f776546da0553" &&
            at(d, "conditional_decision_sha256").string() ==
                "89b658d8d7b67084f0f9b8a6cc8757e46f98d668a354677a892a03b05c5aafd3" &&
            at(d, "prior_installed_review_sha256").string() ==
                "e01236b8f7d34282284cf8f30c9a1e33250e290a9bba9897ebc19b029de593c2",
            "Level22 independent source, domain, Curriculum or prior installed authority differs");
    constexpr const char* packageSha = "6d009fdbd4ac1e290ee121178a5d04648aa718822ba84a9c0ecad06bcd1f7be2";
    constexpr const char* profileSha = "e42869f72b4e83ca6efb001df38d66bb990dadebb7b228817a0286ea3cbd3ed5";
    constexpr const char* registrySha = "579c0929c21a199be5331aaf6f4d037a27d9157079a60bbf7c3c97f7d40b3a44";
    constexpr const char* provenanceSha = "c70347b3197a44e5302e0c3cb786a3ddff361257fd0de842b07e900d85bc0860";
    require(content::sha256(input.package) == packageSha &&
            at(d, "package_sha256").string() == packageSha, "Level22 canonical package changed");
    require(content::sha256(input.profile) == profileSha &&
            at(d, "profile_sha256").string() == profileSha &&
            input.expectedProfileSha256 == profileSha, "Level22 canonical profile changed");
    require(content::sha256(input.registry) == registrySha &&
            at(d, "registry_sha256").string() == registrySha, "Level22 canonical registry changed");
    require(content::sha256(provenance) == provenanceSha &&
            at(d, "source_provenance_sha256").string() == provenanceSha,
            "Level22 event provenance changed");
    const auto scope = json::parse(R"fathom({"automatic_credit":false,"case":{"events":60,"gap_after_event":30,"gap_duration_q":1,"item_id":"fg:item:001171","module_id":"fg:module:001171","span_q":31,"variant_ids":["fg:variant:007464","fg:variant:007465"]},"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false})fathom");
    require(at(d, "scope") == scope, "Level22 pair, pause or no-credit decision scope differs");
    const auto package = json::parse(input.package);
    require(at(package, "content_version").string() ==
                "curriculum-v1-level022-first-neighbor-pair-build-only.1" &&
            at(package, "records").array().size() == 1 &&
            at(package, "sources").object().size() == 6,
            "Level22 package version, case or original source count differs");
    const auto refs = json::parse(R"(["L22-TXT-GUIDANCE","L22-PDF-GUIDANCE","L22-PDF-ROUTE","L22-TXT-RUNG01","L22-TXT-RUNG02","L22-PDF-CARDS01-02"])");
    const auto& record = at(package, "records").array().front();
    require(at(record, "id").string() == "fg:item:001171" &&
            at(record, "module_id").string() == "fg:module:001171" &&
            at(record, "workbook_id").string() == "fg:workbook:000022" &&
            at(record, "content_revision") == J::fromInteger(1) &&
            at(record, "legacy_level") == J::fromInteger(22) &&
            at(record, "runtime_eligible").isBool() &&
            !at(record, "runtime_eligible").boolean() &&
            at(record, "source_refs") == refs && at(record, "authored_text_refs") == refs &&
            at(record, "events").array().size() == 60,
            "Level22 selected identity, nonadmission or source closure differs");
    auto result = content::validate(input);
    require(result.validReference && result.exitCode == 2 &&
            result.records.size() == 1 && result.variants.size() == 2,
            "Level22 native source reference failed or admitted itself");
    const auto sidecar = json::parse(provenance);
    require(at(sidecar, "events").object().size() == 60 &&
            at(sidecar, "variant_strokes").object().size() == 2,
            "Level22 source-event or pick provenance coverage differs");
    std::set<std::string> seen;
    for (auto& variant : result.variants) {
        require(variant.itemId == "fg:item:001171" && seen.insert(variant.id).second &&
                variant.bindingsComplete && variant.readiness.technicallyRenderable &&
                variant.validation.validReference(),
                "Level22 variant foreign, duplicate or unavailable");
        const bool downStart = variant.id == "fg:variant:007464";
        require(downStart || variant.id == "fg:variant:007465",
                "Level22 variant does not belong to selected source pair");
        auto& model = variant.source;
        require(!model.syntheticFixture && model.events.size() == 60 &&
                model.measures.empty() &&
                model.instrument.openMidi == std::vector<int>{40, 45, 50, 55, 59, 64} &&
                model.instrument.capo == 0, "Level22 event count or standard setup differs");
        const auto& strokes = at(at(sidecar, "variant_strokes"), variant.id.c_str()).array();
        require(strokes.size() == 60, "Level22 continuous pick provenance count differs");
        for (std::size_t i = 0; i < 60; ++i) {
            auto& event = model.events[i];
            const auto& evidence = at(at(sidecar, "events"), event.id.c_str());
            const auto& authored = at(record, "events").array()[i];
            const Rational onset = Rational{static_cast<std::int64_t>(i), 2} +
                Rational{i >= 30 ? 1 : 0};
            const auto& slot = at(authored, "onset_q").array();
            const auto& duration = at(authored, "duration_q").array();
            require(at(authored, "event_id").string() == event.id &&
                    slot.size() == 2 && duration.size() == 2 &&
                    at(evidence, "nominal_slot_q") == at(authored, "onset_q") &&
                    Rational{number(slot[0]), number(slot[1])} == onset &&
                    Rational{number(duration[0]), number(duration[1])} == Rational{1, 2},
                    "Level22 authored q1/2 timing, event or rest seam differs");
            require(event.kind == music::Kind::Note && event.span.onset == onset &&
                    event.span.duration == Rational{1, 2} && event.tones.size() == 1 &&
                    event.sourceRef == at(evidence, "source_txt_ref").string(),
                    "Level22 native note, onset, duration or source differs");
            const auto& tone = event.tones.front();
            require(number(at(evidence, "source_string")) == tone.string &&
                    number(at(evidence, "source_fret")) == tone.fret &&
                    number(at(evidence, "source_midi")) == tone.midi &&
                    std::to_string(number(at(evidence, "source_finger"))) == tone.finger &&
                    at(evidence, "source_pitch_spelling").string() == tone.spelling &&
                    tone.attack == music::Attack::Picked && tone.tieFrom.empty(),
                    "Level22 printed string, fret, finger, pitch or articulation differs");
            const auto& degrees = at(authored, "degree_contexts").object();
            require(degrees.size() == 1 &&
                    at(degrees.begin()->second, "source_label") == at(evidence, "source_degree"),
                    "Level22 printed natural-minor degree differs");
            require(number(at(evidence, "source_cell")) == static_cast<std::int64_t>(i / 30 + 1) &&
                    number(at(evidence, "source_contact")) == static_cast<std::int64_t>(i % 30 + 1) &&
                    at(evidence, "repeated_high_root_at_turn").boolean() ==
                        (i % 30 == 14 || i % 30 == 15),
                    "Level22 original cell, contact or repeated high root differs");
            const bool seam = i == 29;
            require(at(evidence, "one_beat_release_after_cell").boolean() == seam &&
                    number(at(evidence, "frame_move_frets")) == (seam ? 1 : 0),
                    "Level22 authored released-pressure whole-frame shift differs");
            const char* stroke = ((i % 2 == 0) == downStart) ? "D" : "U";
            require(strokes[i].string() == stroke,
                    "Level22 D/U cycle resets at root or shift");
            event.handDirection = stroke;
        }
        variant.validation = music::validate(model);
        require(variant.validation.validReference(),
                "Level22 picked-stroke projection failed native validation");
    }
    require(seen == std::set<std::string>{"fg:variant:007464", "fg:variant:007465"},
            "Level22 exact two variant identities differ");
    return result;
}
} // namespace fathom::lesson
