#pragma once
// Exact P59/P63 source packet plus separate P02 case-bound runtime authority.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel016Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level16 whole-number source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level16 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=9;limits.values=180;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","decision_sha256","source_review_evidence","source_review_sha256",
        "domain_review_evidence","domain_review_sha256","package_sha256","profile_sha256",
        "registry_sha256","source_provenance_sha256","scope",
        "source_contacts_picking_timing_accepted","stable_identities_accepted","two_case_runtime_eligible"};
    std::set<std::string> actual;for(const auto& field:d.object())actual.insert(field.first);
    require(actual==fields,"Unsupported Level16 decision fields");
    require(at(d,"version").string()=="level016-first-two-cases-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level16 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence",
                         "source_review_evidence","domain_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level16 authority attribution missing");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted",
                         "two_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level16 exact two-case acceptance missing");
    require(at(d,"decision_sha256").string()=="96480faae17cd7a6ac62f6eea7c22c54bba1ad459e1369b6786e3813d69c1113"&&
        at(d,"source_review_sha256").string()=="16400c6e40d1d0aeb6fe63ed711d6fe851894595dacae440ffd0f2b57fee87bb"&&
        at(d,"domain_review_sha256").string()=="c308a59ee23f3ad5344e70fa86cc394d8e2e78bc4f8baefc794f8c3b64f6d356",
        "Level16 source, Curriculum or domain authority differs");
    constexpr const char* packageSha="a86ac46f1fba5c2135927ec52932f273d432bbfb3346f0ac0498f560bf2f81fa";
    constexpr const char* profileSha="ffb9314cd1cb2e1f7353c641f67d3184072a0cc73cebc8efa37629f29223203c";
    constexpr const char* registrySha="583e8062ffba4b2d0ffc8db334ba0c719ae9c89bed84295a9b5a9a33c40a6317";
    constexpr const char* provenanceSha="8b35400145640e533201879cb810bc8497e639f2033a254802718751524d21cb";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level16 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level16 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level16 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level16 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"cases":[{"events":40,"gap_after_event":0,"gap_duration_q":0,"item_id":"fg:item:001158","module_id":"fg:module:001158","span_q":10,"stage":"complete A-major first 40-contact rolling-four cell; no tail gap or full route","variant_ids":["fg:variant:007438","fg:variant:007439"]},{"events":80,"gap_after_event":40,"gap_duration_q":1,"item_id":"fg:item:001159","module_id":"fg:module:001159","span_q":21,"stage":"A-major to Bb-major first two 40-contact cells; one-beat released-pressure move","variant_ids":["fg:variant:007440","fg:variant:007441"]}],"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false})");
    require(at(d,"scope")==expectedScope,"Level16 decision case or pause scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level016-first-two-cases-build-only.1"&&
        at(package,"records").array().size()==2&&at(package,"sources").object().size()==6,
        "Level16 package version, case or unique source count differs");
    const auto refs=json::parse(R"(["L16-TXT-GUIDANCE","L16-PDF-GUIDANCE","L16-TXT-RUNG01","L16-TXT-RUNG02","L16-PDF-CARDS","L16-PDF-ROUTE"])");
    const std::array<const char*,2> items{"fg:item:001158","fg:item:001159"};
    const std::array<const char*,2> modules{"fg:module:001158","fg:module:001159"};
    for(std::size_t i=0;i<2;++i){
        const auto& record=at(package,"records").array()[i];
        require(at(record,"id").string()==items[i]&&at(record,"module_id").string()==modules[i]&&
            at(record,"workbook_id").string()=="fg:workbook:000016"&&
            at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(16)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==refs,"Level16 candidate identity or original-source closure differs");
    }
    const auto& first=at(package,"records").array().front();
    require(at(first,"title").string().find("complete 40-note rolling-four cell")!=std::string::npos&&
        at(at(first,"context"),"route").string()=="A-major first complete rolling cell",
        "Level16 complete first-cell qualifier missing");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==2&&result.variants.size()==4,
        "Level16 native source validation failed");
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==120&&at(sidecar,"variant_strokes").object().size()==4,
        "Level16 event or pick provenance coverage differs");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool firstCase=variant.itemId==items[0],secondCase=variant.itemId==items[1];
        require((firstCase||secondCase)&&seen.insert(variant.id).second&&variant.bindingsComplete&&
            variant.readiness.technicallyRenderable&&variant.validation.validReference(),
            "Level16 selected variant unavailable, foreign or duplicated");
        const std::size_t count=firstCase?40:80;
        const auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==count&&model.measures.empty()&&
            model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
            "Level16 event count or standard setup differs");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==count,"Level16 pick provenance count differs");
        const bool downStart=variant.id=="fg:variant:007438"||variant.id=="fg:variant:007440";
        for(std::size_t i=0;i<count;++i){
            auto& event=variant.source.events[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const Rational onset=Rational{static_cast<std::int64_t>(i),4}+
                Rational{secondCase&&i>=40?1:0};
            const auto& authored=at(package,"records").array()[secondCase?1:0].object().at("events").array()[i];
            const auto& slot=at(authored,"onset_q").array();
            const auto& duration=at(authored,"duration_q").array();
            require(at(authored,"event_id").string()==event.id&&slot.size()==2&&duration.size()==2&&
                at(evidence,"nominal_slot_q")==at(authored,"onset_q"),
                "Level16 authored event identity or source timing evidence differs");
            const Rational authoredOnset{number(slot[0]),number(slot[1])};
            const Rational authoredDuration{number(duration[0]),number(duration[1])};
            require(authoredOnset==onset&&authoredDuration==Rational{1,4},
                "Level16 source packet nominal sixteenth or intercell pause differs");
            // The frozen native even-subdivision projection rebases the pair's
            // second cell to q10. Restore only the exact reviewed source slot,
            // then revalidate before returning a runtime admission model.
            event.span={authoredOnset,authoredDuration};
            if (!(event.kind==music::Kind::Note&&event.span.onset==onset&&
                  event.span.duration==Rational{1,4}&&event.tones.size()==1))
                throw std::runtime_error("Level16 nominal slot differs in "+variant.id+
                    " event "+std::to_string(i+1)+" observed "+
                    std::to_string(event.span.onset->numerator())+"/"+
                    std::to_string(event.span.onset->denominator())+" expected "+
                    std::to_string(onset.numerator())+"/"+
                    std::to_string(onset.denominator()));
            require(event.sourceRef==at(evidence,"source_txt_ref").string(),
                "Level16 source reference differs");
            require(number(at(evidence,"string"))==event.tones.front().string&&
                number(at(evidence,"fret"))==event.tones.front().fret&&
                number(at(evidence,"midi"))==event.tones.front().midi&&
                std::to_string(number(at(evidence,"finger_digit")))==event.tones.front().finger&&
                at(evidence,"spelling").string()==event.tones.front().spelling,
                "Level16 source contact differs");
            require(event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),
                "Level16 articulation differs");
            const auto expectedStroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==expectedStroke,"Level16 D/U source cycle reset or changed");
            event.handDirection=expectedStroke;
        }
        variant.validation=music::validate(variant.source);
        require(variant.validation.validReference(),"Level16 stroke projection failed native validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007438","fg:variant:007439",
                                        "fg:variant:007440","fg:variant:007441"},
        "Level16 exact D/U variant identities differ");
    return result;
}
} // namespace fathom::lesson
