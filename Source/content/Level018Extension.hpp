#pragma once
// Exact P59/P63 source packet plus separate P02 case-bound runtime authority.
#include "content/Canonical.hpp"
#include <array>
#include <cstdlib>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel018Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level18 whole-number source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level18 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=9;limits.values=180;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","decision_sha256","source_review_evidence","source_review_sha256",
        "domain_review_evidence","domain_review_sha256","package_sha256","profile_sha256",
        "registry_sha256","source_provenance_sha256","scope",
        "source_contacts_picking_timing_accepted","stable_identities_accepted","two_case_runtime_eligible"};
    std::set<std::string> actual;for(const auto& field:d.object())actual.insert(field.first);
    require(actual==fields,"Unsupported Level18 decision fields");
    require(at(d,"version").string()=="level018-first-two-cases-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level18 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence",
                         "source_review_evidence","domain_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level18 authority attribution missing");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted",
                         "two_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level18 exact two-case acceptance missing");
    require(at(d,"decision_sha256").string()=="3dfe66e3b5fb40a3441b2d86ec9b6c8600a419c920a38ea994c09e1bcea86390"&&
        at(d,"source_review_sha256").string()=="3004c080f517e5af8c73fd5417124cdb81159afbafec7155c5861150ff5edd89"&&
        at(d,"domain_review_sha256").string()=="224bd5272af5ea375510fc91f3d08f9f2e1648d5522e17b0a1db223177afd3e2",
        "Level18 source, Curriculum or domain authority differs");
    constexpr const char* packageSha="09c3c9b3ae501fedcffdf01a9b309f587b571fdf7557232c0a20623f3147c538";
    constexpr const char* profileSha="d0210d17f65277e9b92babc035a30d5465b82ff08e34df7e75e5f044d2050e0e";
    constexpr const char* registrySha="32f0d3bebdaff95de06621c7c0219ff170c615d940b3731e2ac3913644b4d506";
    constexpr const char* provenanceSha="f892e5869a23b1ee1cd0bcdd07d1e4481720d3ac1bd0e8d24575e859c2361f38";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level18 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level18 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level18 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level18 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"cases":[{"events":52,"gap_after_event":0,"gap_duration_q":0,"item_id":"fg:item:001162","module_id":"fg:module:001162","span_q":26,"stage":"complete A-major first 52-contact diatonic-thirds cell; no tail gap or full route","variant_ids":["fg:variant:007446","fg:variant:007447"]},{"events":104,"gap_after_event":52,"gap_duration_q":1,"item_id":"fg:item:001163","module_id":"fg:module:001163","span_q":53,"stage":"A-major to Bb-major first two 52-contact cells; one-beat released-pressure move","variant_ids":["fg:variant:007448","fg:variant:007449"]}],"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false})");
    require(at(d,"scope")==expectedScope,"Level18 decision case or pause scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level018-first-two-cases-build-only.1"&&
        at(package,"records").array().size()==2&&at(package,"sources").object().size()==6,
        "Level18 package version, case or unique source count differs");
    const auto refs=json::parse(R"(["L18-TXT-GUIDANCE","L18-PDF-GUIDANCE","L18-TXT-RUNG01","L18-TXT-RUNG02","L18-PDF-CARDS","L18-PDF-ROUTE"])");
    const std::array<const char*,2> items{"fg:item:001162","fg:item:001163"};
    const std::array<const char*,2> modules{"fg:module:001162","fg:module:001163"};
    for(std::size_t i=0;i<2;++i){
        const auto& record=at(package,"records").array()[i];
        require(at(record,"id").string()==items[i]&&at(record,"module_id").string()==modules[i]&&
            at(record,"workbook_id").string()=="fg:workbook:000018"&&
            at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(18)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==refs,"Level18 candidate identity or original-source closure differs");
    }
    const auto& first=at(package,"records").array().front();
    require(at(first,"title").string().find("complete 52-contact diatonic-thirds cell")!=std::string::npos&&
        at(at(first,"context"),"route").string()=="A-major first complete thirds cell",
        "Level18 complete first-cell qualifier missing");
    auto result=content::validate(input);
    if (!(result.validReference&&result.exitCode==2&&result.records.size()==2&&result.variants.size()==4))
        throw std::runtime_error("Level18 native source validation failed: "+
            json::stringify(result.report).substr(0,4096));
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==156&&at(sidecar,"variant_strokes").object().size()==4,
        "Level18 event or pick provenance coverage differs");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool firstCase=variant.itemId==items[0],secondCase=variant.itemId==items[1];
        require((firstCase||secondCase)&&seen.insert(variant.id).second&&variant.bindingsComplete&&
            variant.readiness.technicallyRenderable&&variant.validation.validReference(),
            "Level18 selected variant unavailable, foreign or duplicated");
        const std::size_t count=firstCase?52:104;
        const auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==count&&model.measures.empty()&&
            model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
            "Level18 event count or standard setup differs");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==count,"Level18 pick provenance count differs");
        const bool downStart=variant.id=="fg:variant:007446"||variant.id=="fg:variant:007448";
        for(std::size_t i=0;i<count;++i){
            auto& event=variant.source.events[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const Rational onset=Rational{static_cast<std::int64_t>(i),2}+
                Rational{secondCase&&i>=52?1:0};
            const auto& authored=at(package,"records").array()[secondCase?1:0].object().at("events").array()[i];
            const auto& slot=at(authored,"onset_q").array();
            const auto& duration=at(authored,"duration_q").array();
            require(at(authored,"event_id").string()==event.id&&slot.size()==2&&duration.size()==2&&
                at(evidence,"nominal_slot_q")==at(authored,"onset_q"),
                "Level18 authored event identity or source timing evidence differs");
            const Rational authoredOnset{number(slot[0]),number(slot[1])};
            const Rational authoredDuration{number(duration[0]),number(duration[1])};
            require(authoredOnset==onset&&authoredDuration==Rational{1,2},
                "Level18 source packet nominal eighth or intercell pause differs");
            // Frozen source_event_time pair already carries q27.
            // Refuse any projected timing drift; do not repair at runtime.
            require(event.kind==music::Kind::Note&&event.span.onset==onset&&
                    event.span.duration==Rational{1,2}&&event.tones.size()==1,
                "Level18 source-event-time projection, duration or articulation differs");
            require(event.sourceRef==at(evidence,"source_txt_ref").string(),
                "Level18 source reference differs");
            require(number(at(evidence,"string"))==event.tones.front().string&&
                number(at(evidence,"fret"))==event.tones.front().fret&&
                number(at(evidence,"midi"))==event.tones.front().midi&&
                std::to_string(number(at(evidence,"finger_digit")))==event.tones.front().finger&&
                at(evidence,"spelling").string()==event.tones.front().spelling,
                "Level18 source contact differs");
            const auto& degreeContexts=at(authored,"degree_contexts").object();
            require(degreeContexts.size()==1&&number(at(degreeContexts.begin()->second,"ordinal"))==
                    number(at(evidence,"degree")),"Level18 printed degree differs");
            const auto quality=at(evidence,"pair_quality").string();
            const auto semitones=number(at(evidence,"pair_semitones"));
            require((quality=="M3"&&semitones==4)||(quality=="m3"&&semitones==3),
                "Level18 printed interval quality or semitone relation differs");
            require(number(at(evidence,"source_pair_slot"))==static_cast<std::int64_t>(i%2+1),
                "Level18 source pair slot differs");
            if(i%2==1){
                const auto& previous=at(at(sidecar,"events"),model.events[i-1].id.c_str());
                require(at(previous,"pair_quality")==at(evidence,"pair_quality")&&
                        at(previous,"pair_semitones")==at(evidence,"pair_semitones")&&
                        std::abs(event.tones.front().midi-model.events[i-1].tones.front().midi)==semitones,
                    "Level18 adjacent picked pair differs from printed third quality");
            }
            require(event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),
                "Level18 articulation differs");
            const auto expectedStroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==expectedStroke,"Level18 D/U source cycle reset or changed");
            event.handDirection=expectedStroke;
        }
        variant.validation=music::validate(variant.source);
        require(variant.validation.validReference(),"Level18 stroke projection failed native validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007446","fg:variant:007447",
                                        "fg:variant:007448","fg:variant:007449"},
        "Level18 exact D/U variant identities differ");
    return result;
}
} // namespace fathom::lesson
