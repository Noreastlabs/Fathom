#pragma once
// Exact P59/P63 source packet plus separate P02 case-bound runtime authority.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel017Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level17 whole-number source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level17 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=9;limits.values=180;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","decision_sha256","source_review_evidence","source_review_sha256",
        "domain_review_evidence","domain_review_sha256","package_sha256","profile_sha256",
        "registry_sha256","source_provenance_sha256","scope",
        "source_contacts_picking_timing_accepted","stable_identities_accepted","two_case_runtime_eligible"};
    std::set<std::string> actual;for(const auto& field:d.object())actual.insert(field.first);
    require(actual==fields,"Unsupported Level17 decision fields");
    require(at(d,"version").string()=="level017-first-two-cases-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level17 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence",
                         "source_review_evidence","domain_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level17 authority attribution missing");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted",
                         "two_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level17 exact two-case acceptance missing");
    require(at(d,"decision_sha256").string()=="a1477b9dcde23563335bd563850120101d2bee650063b0eddc83177ce7f802f3"&&
        at(d,"source_review_sha256").string()=="30ca1b9c8251be00fd65a200cb84fb99dc219a2654cb2de21c6ada1de2426387"&&
        at(d,"domain_review_sha256").string()=="b92ba71103b2da13c5757165bd2d609247b8c5df9b66893669de8154b59e2d4e",
        "Level17 source, Curriculum or domain authority differs");
    constexpr const char* packageSha="bb30d460a3cef81b20ee5f162dfa5c0050effb05ade43dad63623a9c710176a2";
    constexpr const char* profileSha="0d5abb1dcbd72de19fe485486a985f95473ed843fb07caf1702f2612f878d6aa";
    constexpr const char* registrySha="c8ca8d2854851995e31f4325ecaf003f0979012bda72afb4cad17be2651eccd4";
    constexpr const char* provenanceSha="0809946d8dc0af6417d304eebf9c3d72883dcd31cfbef5707593bff7ec125a7e";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level17 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level17 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level17 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level17 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"cases":[{"events":96,"gap_after_event":0,"gap_duration_q":0,"item_id":"fg:item:001160","module_id":"fg:module:001160","span_q":24,"stage":"complete A-major first 96-contact rolling-four cell; no tail gap or full route","variant_ids":["fg:variant:007442","fg:variant:007443"]},{"events":192,"gap_after_event":96,"gap_duration_q":1,"item_id":"fg:item:001161","module_id":"fg:module:001161","span_q":49,"stage":"A-major to Bb-major first two 96-contact cells; one-beat released-pressure move","variant_ids":["fg:variant:007444","fg:variant:007445"]}],"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false})");
    require(at(d,"scope")==expectedScope,"Level17 decision case or pause scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level017-first-two-cases-build-only.1"&&
        at(package,"records").array().size()==2&&at(package,"sources").object().size()==6,
        "Level17 package version, case or unique source count differs");
    const auto refs=json::parse(R"(["L17-TXT-GUIDANCE","L17-PDF-GUIDANCE","L17-TXT-RUNG01","L17-TXT-RUNG02","L17-PDF-CARDS","L17-PDF-ROUTE"])");
    const std::array<const char*,2> items{"fg:item:001160","fg:item:001161"};
    const std::array<const char*,2> modules{"fg:module:001160","fg:module:001161"};
    for(std::size_t i=0;i<2;++i){
        const auto& record=at(package,"records").array()[i];
        require(at(record,"id").string()==items[i]&&at(record,"module_id").string()==modules[i]&&
            at(record,"workbook_id").string()=="fg:workbook:000017"&&
            at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(17)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==refs,"Level17 candidate identity or original-source closure differs");
    }
    const auto& first=at(package,"records").array().front();
    require(at(first,"title").string().find("complete 96-note rolling-four cell")!=std::string::npos&&
        at(at(first,"context"),"route").string()=="A-major first complete rolling cell",
        "Level17 complete first-cell qualifier missing");
    auto result=content::validate(input);
    if (!(result.validReference&&result.exitCode==2&&result.records.size()==2&&result.variants.size()==4))
        throw std::runtime_error("Level17 native source validation failed: "+
            json::stringify(result.report).substr(0,4096));
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==288&&at(sidecar,"variant_strokes").object().size()==4,
        "Level17 event or pick provenance coverage differs");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool firstCase=variant.itemId==items[0],secondCase=variant.itemId==items[1];
        require((firstCase||secondCase)&&seen.insert(variant.id).second&&variant.bindingsComplete&&
            variant.readiness.technicallyRenderable&&variant.validation.validReference(),
            "Level17 selected variant unavailable, foreign or duplicated");
        const std::size_t count=firstCase?96:192;
        const auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==count&&model.measures.empty()&&
            model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
            "Level17 event count or standard setup differs");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==count,"Level17 pick provenance count differs");
        const bool downStart=variant.id=="fg:variant:007442"||variant.id=="fg:variant:007444";
        for(std::size_t i=0;i<count;++i){
            auto& event=variant.source.events[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const Rational onset=Rational{static_cast<std::int64_t>(i),4}+
                Rational{secondCase&&i>=96?1:0};
            const auto& authored=at(package,"records").array()[secondCase?1:0].object().at("events").array()[i];
            const auto& slot=at(authored,"onset_q").array();
            const auto& duration=at(authored,"duration_q").array();
            require(at(authored,"event_id").string()==event.id&&slot.size()==2&&duration.size()==2&&
                at(evidence,"nominal_slot_q")==at(authored,"onset_q"),
                "Level17 authored event identity or source timing evidence differs");
            const Rational authoredOnset{number(slot[0]),number(slot[1])};
            const Rational authoredDuration{number(duration[0]),number(duration[1])};
            require(authoredOnset==onset&&authoredDuration==Rational{1,4},
                "Level17 source packet nominal sixteenth or intercell pause differs");
            // Corrected frozen source_event_time pair already carries q25.
            // Refuse any projected timing drift; do not repair at runtime.
            require(event.kind==music::Kind::Note&&event.span.onset==onset&&
                    event.span.duration==Rational{1,4}&&event.tones.size()==1,
                "Level17 source-event-time projection, duration or articulation differs");
            require(event.sourceRef==at(evidence,"source_txt_ref").string(),
                "Level17 source reference differs");
            require(number(at(evidence,"string"))==event.tones.front().string&&
                number(at(evidence,"fret"))==event.tones.front().fret&&
                number(at(evidence,"midi"))==event.tones.front().midi&&
                std::to_string(number(at(evidence,"finger_digit")))==event.tones.front().finger&&
                at(evidence,"spelling").string()==event.tones.front().spelling,
                "Level17 source contact differs");
            require(event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),
                "Level17 articulation differs");
            const auto expectedStroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==expectedStroke,"Level17 D/U source cycle reset or changed");
            event.handDirection=expectedStroke;
        }
        variant.validation=music::validate(variant.source);
        require(variant.validation.validReference(),"Level17 stroke projection failed native validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007442","fg:variant:007443",
                                        "fg:variant:007444","fg:variant:007445"},
        "Level17 exact D/U variant identities differ");
    return result;
}
} // namespace fathom::lesson
