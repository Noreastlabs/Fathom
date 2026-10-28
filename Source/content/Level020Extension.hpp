#pragma once
// Exact P78/P82 source-bound Level20 packet and separate P02 runtime authority.
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel020Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J = json::Value;
    auto require = [](bool ok, const char* why) { if (!ok) throw std::runtime_error(why); };
    auto at = [](const J& value, const char* key) -> const J& { return value.object().at(key); };
    auto number = [&](const J& value) { std::int64_t n{};
        require(value.integer(n), "Level20 source integer differs"); return n; };
    require(expectedDispositionSha.size() == 64 &&
            content::sha256(disposition) == expectedDispositionSha,
            "Level20 decision hash differs from installed authority pin");
    json::Limits limits; limits.bytes = 16384; limits.depth = 10;
    limits.values = 260; limits.stringBytes = 4096;
    const auto d = json::parse(disposition, limits);
    const std::set<std::string> fields{
        "authority_name", "decision_evidence", "decision_sha256", "domain_review_evidence",
        "domain_review_sha256", "one_case_runtime_eligible", "package_sha256",
        "profile_sha256", "recorded_utc", "registry_sha256", "scope",
        "source_contacts_picking_timing_accepted", "source_provenance_sha256",
        "source_review_evidence", "source_review_sha256", "stable_identities_accepted",
        "status", "version"};
    std::set<std::string> actual;
    for (const auto& field : d.object()) actual.insert(field.first);
    require(actual == fields, "Unsupported Level20 decision fields");
    require(at(d, "version").string() == "level020-a-full-circuit-curriculum-decision.1" &&
            at(d, "status").string() == "ACCEPTED", "Level20 decision is not accepted");
    for (const char* key : {"authority_name", "recorded_utc", "decision_evidence",
                            "source_review_evidence", "domain_review_evidence"})
        require(at(d, key).isString() && !at(d, key).string().empty(),
                "Level20 authority attribution missing");
    for (const char* key : {"one_case_runtime_eligible", "stable_identities_accepted",
                            "source_contacts_picking_timing_accepted"})
        require(at(d, key).isBool() && at(d, key).boolean(),
                "Level20 selected-case runtime acceptance missing");
    require(at(d, "source_review_sha256").string() ==
                "3d9e3ea339e29190324b986beb1a6b2a1877dbf96174b4db34b3b666dd6f29fc" &&
            at(d, "domain_review_sha256").string() ==
                "08979d423e6c4a8fb428189371f7b4b00d7df1f17faeb8b4fd132143d358b920",
            "Level20 independent source or domain review differs");
    constexpr const char* packageSha = "29ae9ec9aef7b0655606643c9f15663d530a12124bdc0e3b3c476c96871ffb65";
    constexpr const char* profileSha = "1efdb60aa2b113ba388d1050db57440d115fdef122dd9dcc57da52ee79b60125";
    constexpr const char* registrySha = "a6efa13ec000e7a2901955514826f1df3ac7c89c861fcb8078b97a948ecd6896";
    constexpr const char* provenanceSha = "86c8a418db7046677fbaabb36b2449b52c2a5f48b3de81547c9ab77a4346c313";
    require(content::sha256(input.package) == packageSha &&
            at(d, "package_sha256").string() == packageSha,
            "Level20 canonical package changed");
    require(content::sha256(input.profile) == profileSha &&
            at(d, "profile_sha256").string() == profileSha &&
            input.expectedProfileSha256 == profileSha, "Level20 canonical profile changed");
    require(content::sha256(input.registry) == registrySha &&
            at(d, "registry_sha256").string() == registrySha,
            "Level20 canonical registry changed");
    require(content::sha256(provenance) == provenanceSha &&
            at(d, "source_provenance_sha256").string() == provenanceSha,
            "Level20 source-event provenance changed");
    require(at(d, "scope") == json::parse(R"fathom({"automatic_credit":false,"case":{"events":322,"item_id":"fg:item:001167","module_id":"fg:module:001167","span_q":322,"stage":"A-major complete five-module learning circuit only","variant_ids":["fg:variant:007456","fg:variant:007457"]},"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false})fathom"),
            "Level20 decision scope differs");
    const auto package = json::parse(input.package);
    require(at(package, "content_version").string() ==
                "curriculum-v1-level020-a-full-circuit-build-only.1" &&
            at(package, "records").array().size() == 1 &&
            at(package, "sources").object().size() == 10,
            "Level20 package version, selected case or source count differs");
    const auto& record = at(package, "records").array().front();
    const auto refs = json::parse(R"(["L20-TXT-GUIDANCE","L20-PDF-PROTOCOL","L20-PDF-ROUTE","L20-TXT-A-MODULE1","L20-TXT-A-MODULE2","L20-TXT-A-MODULE3","L20-TXT-A-MODULE4","L20-TXT-A-MODULE5","L20-PDF-A-MODULES1-3","L20-PDF-A-MODULES4-5"])");
    require(at(record, "id").string() == "fg:item:001167" &&
            at(record, "module_id").string() == "fg:module:001167" &&
            at(record, "workbook_id").string() == "fg:workbook:000020" &&
            at(record, "content_revision") == J::fromInteger(1) &&
            at(record, "legacy_level") == J::fromInteger(20) &&
            at(record, "runtime_eligible").isBool() &&
            !at(record, "runtime_eligible").boolean() &&
            at(record, "source_refs") == refs && at(record, "authored_text_refs") == refs,
            "Level20 selected source identity or original references differ");
    const auto result = content::validate(input);
    require(result.validReference && result.exitCode == 2 &&
            result.records.size() == 1 && result.variants.size() == 2,
            "Level20 native reference failed or admitted itself");
    auto projected = result;
    const auto sidecar = json::parse(provenance);
    require(at(sidecar, "events").object().size() == 322 &&
            at(sidecar, "variant_strokes").object().size() == 2,
            "Level20 source-event or pick provenance incomplete");
    std::set<std::string> seen;
    for (auto& variant : projected.variants) {
        const bool downStart = variant.id == "fg:variant:007456";
        require((downStart || variant.id == "fg:variant:007457") &&
                seen.insert(variant.id).second &&
                variant.itemId == "fg:item:001167" &&
                variant.bindingsComplete && variant.readiness.technicallyRenderable &&
                variant.validation.validReference(),
                "Level20 D/U or U/D variant missing, duplicated or foreign");
        auto& model = variant.source;
        require(!model.syntheticFixture && model.events.size() == 322 &&
                model.measures.empty() &&
                model.instrument.openMidi == std::vector<int>{40, 45, 50, 55, 59, 64} &&
                model.instrument.capo == 0,
                "Level20 event count, sequential source model or standard setup differs");
        const auto& strokes = at(at(sidecar, "variant_strokes"), variant.id.c_str()).array();
        require(strokes.size() == 322, "Level20 continuous pick provenance count differs");
        for (std::size_t i = 0; i < 322; ++i) {
            auto& event = model.events[i];
            const auto& evidence = at(at(sidecar, "events"), event.id.c_str());
            const auto& authored = at(record, "events").array()[i];
            require(at(authored, "event_id").string() == event.id &&
                    at(authored, "onset_q") == json::parse("[" + std::to_string(i) + ",1]") &&
                    at(authored, "duration_q") == json::parse("[1,1]") &&
                    at(evidence, "nominal_slot_q") == at(authored, "onset_q"),
                    "Level20 exact q1 learning grid or event identity differs");
            require(event.kind == music::Kind::Note &&
                    event.span.onset == Rational{static_cast<std::int64_t>(i)} &&
                    event.span.duration == Rational{1} && event.tones.size() == 1,
                    "Level20 picked note, onset, duration or terminal span differs");
            const auto& tone = event.tones.front();
            require(event.sourceRef == at(evidence, "source_txt_ref").string() &&
                    number(at(evidence, "source_circuit_contact")) == static_cast<std::int64_t>(i + 1) &&
                    number(at(evidence, "string")) == tone.string &&
                    number(at(evidence, "fret")) == tone.fret &&
                    number(at(evidence, "midi")) == tone.midi &&
                    std::to_string(number(at(evidence, "printed_finger"))) == tone.finger &&
                    at(evidence, "printed_note_spelling").string() == tone.spelling,
                    "Level20 source contact, pitch, finger or reference differs");
            const auto& degree = at(at(authored, "degree_contexts"), "A-major");
            require(number(at(degree, "ordinal")) == number(at(evidence, "printed_degree")) &&
                    at(degree, "source_label").string() ==
                        std::to_string(number(at(evidence, "printed_degree"))) &&
                    number(at(evidence, "scale_step")) == number(at(evidence, "p12_scale_step_ordinal")),
                    "Level20 printed degree or separate scale-step provenance differs");
            const bool seam = i == 30 || i == 108 || i == 204 || i == 256;
            require(at(evidence, "rearticulated_module_root").boolean() == seam &&
                    at(evidence, "selected_mode").string() == "one_sequential_note_per_click" &&
                    tone.attack == music::Attack::Picked && tone.tieFrom.empty(),
                    "Level20 module root re-articulation or selected learning mode differs");
            const char* stroke = ((i % 2 == 0) == downStart) ? "D" : "U";
            require(strokes[i].string() == stroke,
                    "Level20 continuous D/U source cycle or module transition differs");
            event.handDirection = stroke;
        }
        variant.validation = music::validate(model);
        require(variant.validation.validReference(),
                "Level20 picked stroke projection failed native validation");
    }
    require(seen == std::set<std::string>{"fg:variant:007456", "fg:variant:007457"},
            "Level20 exact variant identities differ");
    return projected;
}
} // namespace fathom::lesson
