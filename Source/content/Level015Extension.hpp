#pragma once
// Exact P55/P57 source packet plus separate P02 case-bound runtime authority.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel015Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level15 whole-number source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level15 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=9;limits.values=180;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","decision_sha256","source_review_evidence","source_review_sha256",
        "domain_review_evidence","domain_review_sha256","lineage_decision_sha256",
        "lineage_review_sha256","package_sha256","profile_sha256","registry_sha256",
        "source_provenance_sha256","scope","source_contacts_picking_timing_accepted",
        "stable_identities_accepted","one_case_runtime_eligible"};
    std::set<std::string> actual;for(const auto& field:d.object())actual.insert(field.first);
    require(actual==fields,"Unsupported Level15 decision fields");
    require(at(d,"version").string()=="level015-rung01-complete-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level15 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence",
                         "source_review_evidence","domain_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level15 authority attribution missing");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted",
                         "one_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level15 exact one-case acceptance missing");
    require(at(d,"decision_sha256").string()=="aa97708159d8bcde8c2246e15f7e9ffa07bbdb27c2c47d153f3579b101efe482"&&
        at(d,"source_review_sha256").string()=="c4d7f4ae1529c637bae45b89b00ea49e1df492e20d322c320d71495b1056e8c6"&&
        at(d,"domain_review_sha256").string()=="5e9ccfa2c95d7c7bdd334312bc34031f8d25d8376032cb3f57e4b090b788b4c4"&&
        at(d,"lineage_decision_sha256").string()=="d5a4174c9a3985c7b22940d477d0c440276eeed9fb5e3679a515fadcb983e213"&&
        at(d,"lineage_review_sha256").string()=="317d6a84c86a637e027121bc6da271b73a7f2981bd844421d8369e4555ba2ab0",
        "Level15 source, Curriculum, lineage or domain authority differs");
    constexpr const char* packageSha="f4344f9d3b90c2714acc5e6f31a10904491a0bcb37e4174cebc866b66825c0f0";
    constexpr const char* profileSha="aff47fff4350e0ef83a5d2e1b38401cc698ae43ad75076928edf1c04d60901f7";
    constexpr const char* registrySha="e0eb0da49e2a9444071437de5b86f9a5527c3ee76ec90c0ead2a5524981fe8f5";
    constexpr const char* provenanceSha="3c98c633d6000234009ee5e8ff92d7caec844b06c93ab9107ab7687e881a6aff";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level15 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level15 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level15 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level15 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false,"prior_item_000004_unchanged":true,"cases":[{"stage":"complete A-major Rung01 78-note rolling-triplet cell; no full neck route","item_id":"fg:item:001157","module_id":"fg:module:001157","variant_ids":["fg:variant:007436","fg:variant:007437"],"events":78,"span_q":26,"gap_after_event":0,"gap_duration_q":0}]})");
    require(at(d,"scope")==expectedScope,"Level15 decision case or lineage scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level015-rung01-complete-triplet-build-only.1"&&
        at(package,"records").array().size()==1&&at(package,"sources").object().size()==4,
        "Level15 package version, case or source-key count differs");
    const auto refs=json::parse(R"(["L15-TXT1-60-67","L15-TXT1-70-91","L15-PDF-GUIDANCE-P1","L15-PDF-CARD-P3"])");
    const auto& record=at(package,"records").array().front();
    require(at(record,"id").string()=="fg:item:001157"&&
        at(record,"module_id").string()=="fg:module:001157"&&
        at(record,"workbook_id").string()=="fg:workbook:000015"&&
        at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(15)&&
        at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
        at(record,"source_refs")==refs&&
        at(record,"title").string().find("complete 78-note two-octave rolling-triplet cell")!=std::string::npos&&
        at(at(record,"context"),"route").string()=="A-major Rung01 complete single cell",
        "Level15 complete-cell identity, source or qualifier differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Level15 native source validation failed");
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==78&&at(sidecar,"variant_strokes").object().size()==2,
        "Level15 event or pick provenance coverage differs");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        require(variant.itemId=="fg:item:001157"&&seen.insert(variant.id).second&&
            variant.bindingsComplete&&variant.readiness.technicallyRenderable&&
            variant.validation.validReference(),"Level15 selected variant unavailable, foreign or duplicated");
        const auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==78&&model.measures.empty()&&
            model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
            "Level15 event count or standard setup differs");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==78,"Level15 pick provenance count differs");
        const bool downStart=variant.id=="fg:variant:007436";
        for(std::size_t i=0;i<78;++i){
            auto& event=variant.source.events[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const Rational onset=Rational{static_cast<std::int64_t>(i),3};
            require(event.kind==music::Kind::Note&&event.span.onset==onset&&
                event.span.duration==Rational{1,3}&&event.tones.size()==1&&
                event.sourceRef==at(evidence,"source_txt_ref").string()&&
                number(at(evidence,"string"))==event.tones.front().string&&
                number(at(evidence,"fret"))==event.tones.front().fret&&
                number(at(evidence,"midi"))==event.tones.front().midi&&
                std::to_string(number(at(evidence,"finger_digit")))==event.tones.front().finger&&
                at(evidence,"spelling").string()==event.tones.front().spelling&&
                event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),
                "Level15 source contact, articulation or exact nominal triplet differs");
            const auto expectedStroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==expectedStroke,"Level15 D/U source cycle reset or changed");
            event.handDirection=expectedStroke;
        }
        require(at(at(sidecar,"events"),model.events[38].id.c_str()).object().at("high_root_turn_repeat").boolean()==true&&
                at(at(sidecar,"events"),model.events[39].id.c_str()).object().at("high_root_turn_repeat").boolean()==true&&
                model.events[38].tones.front().midi==model.events[39].tones.front().midi&&
                model.events[38].tones.front().string==model.events[39].tones.front().string&&
                model.events[38].tones.front().fret==model.events[39].tones.front().fret,
                "Level15 high-root turn lost its two separate attacks");
        variant.validation=music::validate(variant.source);
        require(variant.validation.validReference(),"Level15 stroke projection failed native validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007436","fg:variant:007437"},
        "Level15 exact D/U variant identities differ");
    return result;
}
} // namespace fathom::lesson
