#pragma once
// Exact P75/P76 Level19 source packet plus separate P02 case-bound runtime authority.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel019Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level19 whole-number source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level19 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=10;limits.values=260;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","decision_sha256","source_review_evidence","source_review_sha256",
        "domain_review_evidence","domain_review_sha256","technical_review_evidence","technical_review_sha256",
        "package_sha256","profile_sha256","registry_sha256","source_provenance_sha256","scope",
        "source_contacts_picking_timing_accepted","stable_identities_accepted","three_case_runtime_eligible"};
    std::set<std::string> actual;for(const auto& field:d.object())actual.insert(field.first);
    require(actual==fields,"Unsupported Level19 decision fields");
    require(at(d,"version").string()=="level019-first-three-cases-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level19 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence",
                         "source_review_evidence","domain_review_evidence","technical_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level19 authority attribution missing");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted",
                         "three_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level19 exact three-case acceptance missing");
    require(at(d,"decision_sha256").string()=="651040c7e9143a0d80722ee6e865c24b694aa331aa42c62b49a4828b2aeeb9e2"&&
        at(d,"source_review_sha256").string()=="a9628de092fd8039c9c3265ba85d778ddf5ed50e10ed2bec6ec61169fa1676f4"&&
        at(d,"domain_review_sha256").string()=="1ddabd1c8c0dd8da6c2ef475658e85df728d63fda4e0e930aa45927941ff80bb"&&
        at(d,"technical_review_sha256").string()=="0f00de0b6d8e6194e4dad5412b4fb572993e2794478da852c8206f8368971492",
        "Level19 source, Curriculum, domain or technical authority differs");
    constexpr const char* packageSha="3c29479b9f2ad3726972c52bdb82917021a314a675370e13d3d22281c855ae44";
    constexpr const char* profileSha="5d27dbc504e17ac637e5ab0030c5400639de7e14b5ae7dff46378bfe3bcfb5a5";
    constexpr const char* registrySha="4a0f79322fb661b8a5137586dbf6b10317529268286911dddc4735b94a6f3453";
    constexpr const char* provenanceSha="08c601f953574a0c95d60885cc7ac3f3eddf2d0c9383feefb3f8ae173edf9d19";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level19 canonical package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level19 canonical profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level19 canonical registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level19 event provenance changed");
    require(at(d,"scope")==json::parse(R"fathom({"automatic_credit":false,"cases":[{"events":66,"gap_after_event":0,"gap_duration_q":0,"item_id":"fg:item:001164","module_id":"fg:module:001164","second_gap_after_event":0,"second_gap_duration_q":0,"span_q":22,"stage":"complete A-major first 66-contact sequential broken-triad cell; no tail gap or full route","variant_ids":["fg:variant:007450","fg:variant:007451"]},{"events":132,"gap_after_event":66,"gap_duration_q":1,"item_id":"fg:item:001165","module_id":"fg:module:001165","second_gap_after_event":0,"second_gap_duration_q":0,"span_q":45,"stage":"A-major to Bb-major first two 66-contact cells; one-beat released-pressure move","variant_ids":["fg:variant:007452","fg:variant:007453"]},{"events":198,"gap_after_event":66,"gap_duration_q":1,"item_id":"fg:item:001166","module_id":"fg:module:001166","second_gap_after_event":132,"second_gap_duration_q":1,"span_q":68,"stage":"A-major through B-major first three 66-contact cells; two one-beat released-pressure moves","variant_ids":["fg:variant:007454","fg:variant:007455"]}],"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false})fathom"),
        "Level19 decision case or two-pause scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level019-first-three-cases-build-only.1"&&
        at(package,"records").array().size()==3&&at(package,"sources").object().size()==8,
        "Level19 package version, case or unique source count differs");
    const auto refs=json::parse(R"(["L19-TXT-GUIDANCE","L19-PDF-GUIDANCE","L19-TXT-RUNG01","L19-TXT-RUNG02","L19-TXT-RUNG03","L19-PDF-CARDS01-02","L19-PDF-CARD03","L19-PDF-ROUTE"])");
    const std::array<const char*,3> items{"fg:item:001164","fg:item:001165","fg:item:001166"};
    const std::array<const char*,3> modules{"fg:module:001164","fg:module:001165","fg:module:001166"};
    const std::array<std::array<const char*,2>,3> variants{{{{"fg:variant:007450","fg:variant:007451"}},
        {{"fg:variant:007452","fg:variant:007453"}},{{"fg:variant:007454","fg:variant:007455"}}}};
    for(std::size_t i=0;i<3;++i){
        const auto& record=at(package,"records").array()[i];
        require(at(record,"id").string()==items[i]&&at(record,"module_id").string()==modules[i]&&
            at(record,"workbook_id").string()=="fg:workbook:000019"&&
            at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(19)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==refs,"Level19 candidate identity or original-source closure differs");
        require(at(record,"title").string().find(i==0?"66-contact":i==1?"132-contact":"198-contact")!=std::string::npos,
            "Level19 exact selected-case qualifier missing");
    }
    auto result=content::validate(input);
    if (!(result.validReference&&result.exitCode==2&&result.records.size()==3&&result.variants.size()==6))
        throw std::runtime_error("Level19 native source validation failed: "+
            json::stringify(result.report).substr(0,4096));
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==396&&at(sidecar,"variant_strokes").object().size()==6,
        "Level19 event or pick provenance coverage differs");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        std::size_t ci=3;
        for(std::size_t j=0;j<3;++j)if(variant.itemId==items[j])ci=j;
        require(ci<3&&seen.insert(variant.id).second&&variant.bindingsComplete&&
            variant.readiness.technicallyRenderable&&variant.validation.validReference(),
            "Level19 selected variant unavailable, foreign or duplicated");
        const bool downStart=variant.id==variants[ci][0];
        require(downStart||variant.id==variants[ci][1],"Level19 variant does not belong to source case");
        const std::size_t count=66*(ci+1);
        const auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==count&&model.measures.empty()&&
            model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
            "Level19 event count or standard setup differs");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==count,"Level19 pick provenance count differs");
        for(std::size_t i=0;i<count;++i){
            auto& event=variant.source.events[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const Rational onset=Rational{static_cast<std::int64_t>(i),3}+
                Rational{i>=66?1:0}+Rational{i>=132?1:0};
            const auto& authored=at(package,"records").array()[ci].object().at("events").array()[i];
            const auto& slot=at(authored,"onset_q").array();
            const auto& duration=at(authored,"duration_q").array();
            require(at(authored,"event_id").string()==event.id&&slot.size()==2&&duration.size()==2&&
                at(evidence,"nominal_slot_q")==at(authored,"onset_q"),
                "Level19 authored event identity or source timing evidence differs");
            require(Rational{number(slot[0]),number(slot[1])}==onset&&
                Rational{number(duration[0]),number(duration[1])}==Rational{1,3},
                "Level19 source packet nominal triplet or intercell pause differs");
            require(event.kind==music::Kind::Note&&event.span.onset==onset&&
                event.span.duration==Rational{1,3}&&event.tones.size()==1,
                "Level19 source-event-time projection, duration or articulation differs");
            require(event.sourceRef==at(evidence,"source_txt_ref").string(),
                "Level19 source reference differs");
            require(number(at(evidence,"string"))==event.tones.front().string&&
                number(at(evidence,"fret"))==event.tones.front().fret&&
                number(at(evidence,"midi"))==event.tones.front().midi&&
                std::to_string(number(at(evidence,"finger_digit")))==event.tones.front().finger&&
                at(evidence,"spelling").string()==event.tones.front().spelling,
                "Level19 source contact differs");
            const auto& degreeContexts=at(authored,"degree_contexts").object();
            require(degreeContexts.size()==1&&number(at(degreeContexts.begin()->second,"ordinal"))==
                    number(at(evidence,"degree")),"Level19 printed degree differs");
            const auto quality=at(evidence,"triad_quality").string();
            require(quality=="major"||quality=="minor"||quality=="diminished",
                "Level19 printed triad quality differs");
            const auto role=at(evidence,"source_note_role").string();
            const auto rungNote=i%66;
            const auto expectedRole=rungNote<33?
                (i%3==0?"root":i%3==1?"third":"fifth"):
                (i%3==0?"fifth":i%3==1?"third":"root");
            require(role==expectedRole&&
                number(at(evidence,"source_triad_slot"))==static_cast<std::int64_t>(i%3+1)&&
                number(at(evidence,"source_rung"))==static_cast<std::int64_t>(i/66+1),
                "Level19 sequential triad role or rung differs");
            if(i%3!=0){
                const auto& previous=at(at(sidecar,"events"),model.events[i-1].id.c_str());
                require(at(previous,"triad_quality")==at(evidence,"triad_quality")&&
                    at(previous,"harmonic_function")==at(evidence,"harmonic_function"),
                    "Level19 neighboring triad quality or function differs");
            }
            const bool seam=(i==65||i==131)&&i+1<count;
            require(at(evidence,"one_beat_release_after_cell").boolean()==seam&&
                number(at(evidence,"frame_move_frets"))==(seam?1:0),
                "Level19 source-authored released-pressure seam differs");
            require(event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),
                "Level19 articulation differs");
            const auto expectedStroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==expectedStroke,"Level19 D/U source cycle reset or changed");
            event.handDirection=expectedStroke;
        }
        variant.validation=music::validate(variant.source);
        require(variant.validation.validReference(),"Level19 stroke projection failed native validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007450","fg:variant:007451","fg:variant:007452",
                                        "fg:variant:007453","fg:variant:007454","fg:variant:007455"},
        "Level19 exact D/U variant identities differ");
    return result;
}
} // namespace fathom::lesson
