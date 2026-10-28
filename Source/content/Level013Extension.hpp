#pragma once
// Exact P44/P47 Level13 source packet plus a separate P02 typed runtime decision.
// The frozen reference itself remains nonadmitted until the finite descriptor
// and Catalog permission both accept its two selected cases.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel013Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level13 whole-number source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level13 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=9;limits.values=180;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","decision_sha256","source_review_evidence","source_review_sha256",
        "domain_review_evidence","domain_review_sha256","package_sha256","profile_sha256",
        "registry_sha256","source_provenance_sha256","scope",
        "source_contacts_picking_timing_accepted","stable_identities_accepted","two_case_runtime_eligible"};
    std::set<std::string> actual;for(const auto& field:d.object())actual.insert(field.first);
    require(actual==fields,"Unsupported Level13 decision fields");
    require(at(d,"version").string()=="level013-rung01-a-and-a-bb-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level13 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence",
                         "source_review_evidence","domain_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level13 authority attribution missing");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted",
                         "two_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level13 exact two-case acceptance missing");
    require(at(d,"decision_sha256").string()=="27b3324286a7377bef16c4285073464c0bd6c1914340e80fee270c0a870f0c33"&&
        at(d,"source_review_sha256").string()=="4fce4a1722d0ea6b227677a566c54e6619dc7945bc22ea09f1412ce05d8146fa"&&
        at(d,"domain_review_sha256").string()=="e95bee69855b818ed83d65a8bcf53e7cb58725cacad0a171bd48d019a4128217",
        "Level13 source, Curriculum or domain authority differs");
    constexpr const char* packageSha="c8903cd600f8f9082f7e3471e1ef7ce23e103bfcb66c4a9a5e919d7b1b713df4";
    constexpr const char* profileSha="d8867e2459a34f9ab85520343aba3b7e9cea3dd05874ef77c2718696cc8dd36a";
    constexpr const char* registrySha="9d9c883ac519540e8ca3280df993c32142ca779b9ea07b45d3c992d8e4d6bf6a";
    constexpr const char* provenanceSha="9961b847c81bba1d3cb7cd6170ab0b5584a051d10681d28b8cda978d03c8f4df";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level13 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level13 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level13 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level13 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false,"cases":[{"stage":"neighboring-rung even-eighth first-cell excerpt, not earlier isolated first-mastery rhythm","item_id":"fg:item:001153","module_id":"fg:module:001153","variant_ids":["fg:variant:007428","fg:variant:007429"],"events":30,"span_q":15,"gap_after_event":0,"gap_duration_q":0},{"stage":"A-major to Bb-major two-neighbor even-eighth stage, whole-frame one-fret move","item_id":"fg:item:001154","module_id":"fg:module:001154","variant_ids":["fg:variant:007430","fg:variant:007431"],"events":60,"span_q":31,"gap_after_event":30,"gap_duration_q":1}]})");
    require(at(d,"scope")==expectedScope,"Level13 decision case or pause scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level013-rung01-a-and-a-bb-timed-build-only.1"&&
        at(package,"records").array().size()==2&&at(package,"sources").object().size()==5,
        "Level13 package version, case or unique source count differs");
    const auto refs=json::parse(R"(["L13-TXT-RULE-29-49","L13-PDF-GUIDANCE-P1","L13-TXT-RUNG01-52-63","L13-TXT-RUNG02-66-77","L13-PDF-CARDS-P3"])");
    const std::array<const char*,2> items{"fg:item:001153","fg:item:001154"};
    const std::array<const char*,2> modules{"fg:module:001153","fg:module:001154"};
    for(std::size_t i=0;i<2;++i){
        const auto& record=at(package,"records").array()[i];
        require(at(record,"id").string()==items[i]&&at(record,"module_id").string()==modules[i]&&
            at(record,"workbook_id").string()=="fg:workbook:000013"&&
            at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(13)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==refs,"Level13 candidate identity or original-source closure differs");
    }
    const auto& first=at(package,"records").array().front();
    require(at(first,"title").string().find("excerpt of neighbor-stage even-eighth cell")!=std::string::npos&&
        at(at(first,"context"),"route").string().find("neighbor-stage excerpt")!=std::string::npos,
        "Level13 first-cell neighboring-stage excerpt qualifier missing");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==2&&result.variants.size()==4,
        "Level13 native source validation failed");
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==90&&at(sidecar,"variant_strokes").object().size()==4,
        "Level13 event or pick provenance coverage differs");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool firstCase=variant.itemId==items[0],secondCase=variant.itemId==items[1];
        require((firstCase||secondCase)&&seen.insert(variant.id).second&&variant.bindingsComplete&&
            variant.readiness.technicallyRenderable&&variant.validation.validReference(),
            "Level13 selected variant unavailable, foreign or duplicated");
        const std::size_t count=firstCase?30:60;
        const auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==count&&model.measures.empty()&&
            model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
            "Level13 event count or standard setup differs");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==count,"Level13 pick provenance count differs");
        const bool downStart=variant.id=="fg:variant:007428"||variant.id=="fg:variant:007430";
        for(std::size_t i=0;i<count;++i){
            auto& event=variant.source.events[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const Rational onset=Rational{static_cast<std::int64_t>(i),2}+
                Rational{secondCase&&i>=30?1:0};
            require(event.kind==music::Kind::Note&&event.span.onset==onset&&
                event.span.duration==Rational{1,2}&&event.tones.size()==1&&
                event.sourceRef==at(evidence,"source_txt_ref").string()&&
                number(at(evidence,"string"))==event.tones.front().string&&
                number(at(evidence,"fret"))==event.tones.front().fret&&
                number(at(evidence,"midi"))==event.tones.front().midi&&
                std::to_string(number(at(evidence,"finger_digit")))==event.tones.front().finger&&
                at(evidence,"spelling").string()==event.tones.front().spelling&&
                event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),
                "Level13 source contact, articulation or exact nominal pause differs");
            const auto expectedStroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==expectedStroke,"Level13 D/U source cycle reset or changed");
            event.handDirection=expectedStroke;
        }
        variant.validation=music::validate(variant.source);
        require(variant.validation.validReference(),"Level13 stroke projection failed native validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007428","fg:variant:007429",
                                        "fg:variant:007430","fg:variant:007431"},
        "Level13 exact D/U variant identities differ");
    return result;
}
} // namespace fathom::lesson
