#pragma once
// Exact P48/P50 source packet plus separate P02 case-bound runtime authority.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel014Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level14 whole-number source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level14 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=9;limits.values=180;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","decision_sha256","source_review_evidence","source_review_sha256",
        "domain_review_evidence","domain_review_sha256","package_sha256","profile_sha256",
        "registry_sha256","source_provenance_sha256","scope",
        "source_contacts_picking_timing_accepted","stable_identities_accepted","two_case_runtime_eligible"};
    std::set<std::string> actual;for(const auto& field:d.object())actual.insert(field.first);
    require(actual==fields,"Unsupported Level14 decision fields");
    require(at(d,"version").string()=="level014-rung01-a-and-a-bb-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level14 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence",
                         "source_review_evidence","domain_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level14 authority attribution missing");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted",
                         "two_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level14 exact two-case acceptance missing");
    require(at(d,"decision_sha256").string()=="262577639e2ebe2f0f4c53b02433c4cc975e90faae3da3f155d536350fde9683"&&
        at(d,"source_review_sha256").string()=="3cdc4d34bc39f45c3e927e41e5ad0fe1838dafd1c9eae64e8e0fcf8125b69939"&&
        at(d,"domain_review_sha256").string()=="5a2f7c55daf1ff4520eef9532fe588c4834171258b273512b985644d0f33620e",
        "Level14 source, Curriculum or domain authority differs");
    constexpr const char* packageSha="7ecd337c1f5a40b176d8a2bffe04f28bbc8132dbd2045bb27560d3e683fb34f1";
    constexpr const char* profileSha="c46097ec1eb49673474702af2c8c5f613ccdf7aa15b849073313b98688fb4b04";
    constexpr const char* registrySha="51d18e42a3f21e71d97943ddc414100cff2ba5d7dde712f50c29d18f58fe44e3";
    constexpr const char* provenanceSha="e5c775823fb22bd3d521d2ce454a72b4c9135241b2cbd9fb2e210ca6e4677baa";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level14 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level14 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level14 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level14 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false,"cases":[{"stage":"complete A-major first rolling-triplet cell; no shift or complete neck route","item_id":"fg:item:001155","module_id":"fg:module:001155","variant_ids":["fg:variant:007432","fg:variant:007433"],"events":36,"span_q":12,"gap_after_event":0,"gap_duration_q":0},{"stage":"A-major to Bb-major first two neighboring rolling-triplet cells; whole-frame one-fret move","item_id":"fg:item:001156","module_id":"fg:module:001156","variant_ids":["fg:variant:007434","fg:variant:007435"],"events":72,"span_q":25,"gap_after_event":36,"gap_duration_q":1}]})");
    require(at(d,"scope")==expectedScope,"Level14 decision case or pause scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level014-rung01-a-and-a-bb-triplet-build-only.1"&&
        at(package,"records").array().size()==2&&at(package,"sources").object().size()==6,
        "Level14 package version, case or unique source count differs");
    const auto refs=json::parse(R"(["L14-TXT-RULE-29-53","L14-PDF-GUIDANCE-P1","L14-TXT-RUNG01-56-67","L14-TXT-RUNG02-70-81","L14-PDF-CARDS-P3","L14-PDF-ROUTE-P2"])");
    const std::array<const char*,2> items{"fg:item:001155","fg:item:001156"};
    const std::array<const char*,2> modules{"fg:module:001155","fg:module:001156"};
    for(std::size_t i=0;i<2;++i){
        const auto& record=at(package,"records").array()[i];
        require(at(record,"id").string()==items[i]&&at(record,"module_id").string()==modules[i]&&
            at(record,"workbook_id").string()=="fg:workbook:000014"&&
            at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(14)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==refs,"Level14 candidate identity or original-source closure differs");
    }
    const auto& first=at(package,"records").array().front();
    require(at(first,"title").string().find("complete 36-note rolling-triplet cell")!=std::string::npos&&
        at(at(first,"context"),"route").string()=="A-major first complete rolling cell",
        "Level14 complete first-cell qualifier missing");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==2&&result.variants.size()==4,
        "Level14 native source validation failed");
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==108&&at(sidecar,"variant_strokes").object().size()==4,
        "Level14 event or pick provenance coverage differs");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool firstCase=variant.itemId==items[0],secondCase=variant.itemId==items[1];
        require((firstCase||secondCase)&&seen.insert(variant.id).second&&variant.bindingsComplete&&
            variant.readiness.technicallyRenderable&&variant.validation.validReference(),
            "Level14 selected variant unavailable, foreign or duplicated");
        const std::size_t count=firstCase?36:72;
        const auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==count&&model.measures.empty()&&
            model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
            "Level14 event count or standard setup differs");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==count,"Level14 pick provenance count differs");
        const bool downStart=variant.id=="fg:variant:007432"||variant.id=="fg:variant:007434";
        for(std::size_t i=0;i<count;++i){
            auto& event=variant.source.events[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const Rational onset=Rational{static_cast<std::int64_t>(i),3}+
                Rational{secondCase&&i>=36?1:0};
            require(event.kind==music::Kind::Note&&event.span.onset==onset&&
                event.span.duration==Rational{1,3}&&event.tones.size()==1&&
                event.sourceRef==at(evidence,"source_txt_ref").string()&&
                number(at(evidence,"string"))==event.tones.front().string&&
                number(at(evidence,"fret"))==event.tones.front().fret&&
                number(at(evidence,"midi"))==event.tones.front().midi&&
                std::to_string(number(at(evidence,"finger_digit")))==event.tones.front().finger&&
                at(evidence,"spelling").string()==event.tones.front().spelling&&
                event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),
                "Level14 source contact, articulation or exact nominal triplet/pause differs");
            const auto expectedStroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==expectedStroke,"Level14 D/U source cycle reset or changed");
            event.handDirection=expectedStroke;
        }
        variant.validation=music::validate(variant.source);
        require(variant.validation.validReference(),"Level14 stroke projection failed native validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007432","fg:variant:007433",
                                        "fg:variant:007434","fg:variant:007435"},
        "Level14 exact D/U variant identities differ");
    return result;
}
} // namespace fathom::lesson
