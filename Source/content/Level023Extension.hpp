#pragma once
// Exact reviewed Level23 Rung01 source packet plus separate P02 runtime authority.
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel023Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level23 integer source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level23 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=10;limits.values=260;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","decision_sha256","source_review_evidence","source_review_sha256",
        "domain_review_evidence","domain_review_sha256","conditional_decision_evidence",
        "conditional_decision_sha256","prior_installed_review_evidence","prior_installed_review_sha256",
        "package_sha256","profile_sha256","registry_sha256","source_provenance_sha256","scope",
        "source_contacts_picking_timing_accepted","stable_identities_accepted","one_case_runtime_eligible"};
    std::set<std::string> actual;for(const auto& field:d.object())actual.insert(field.first);
    require(actual==fields,"Unsupported Level23 decision fields");
    require(at(d,"version").string()=="level023-first-rolling-cell-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level23 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence","source_review_evidence",
                         "domain_review_evidence","conditional_decision_evidence","prior_installed_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level23 authority attribution missing");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted",
                         "one_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level23 exact one-case acceptance missing");
    require(at(d,"source_review_sha256").string()=="a43d728690ca0937bd88c61250375a00456020c8967254baae9be37bb9827f5d"&&
        at(d,"domain_review_sha256").string()=="c6f41e6638fa491c98f8aa310d0f1f6f0c179d34e40e6afd441dc0b97d3817c2"&&
        at(d,"conditional_decision_sha256").string()=="d4f61b5398c1e25a1940886035871bab99deeaf11613ca6ccdf86f76a4e91611"&&
        at(d,"prior_installed_review_sha256").string()=="0ce5c8c090a40fc702be7e1bbbdb1205fa799058e158960e60c914ea89383fe1",
        "Level23 source, domain, Curriculum or prior installed authority differs");
    constexpr const char* packageSha="b0a362abf9701afea62ccd66201dd923cafb40d51dc5f283d45daaa799ff4e2c";
    constexpr const char* profileSha="a155b3963e0277a5d80c33cee46896c0358bd5cd6defea3364858462c6035b11";
    constexpr const char* registrySha="470f60403e10d8c453ca56d91cbb7085c0fa6df23b720ef84738b5a63ee59681";
    constexpr const char* provenanceSha="b0176d3779b109a2dc2876e47cd640fdcf447eada0eeea9794b2313feb71bb1e";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level23 canonical package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level23 canonical profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level23 canonical registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level23 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"case":{"events":36,"gap_after_event":0,"gap_duration_q":0,"item_id":"fg:item:001172","module_id":"fg:module:001172","span_q":12,"variant_ids":["fg:variant:007466","fg:variant:007467"]},"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false,"recorded_domain":"Technique/fretboard"})");
    require(at(d,"scope")==expectedScope,"Level23 decision case, span or no-credit scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level023-first-rolling-cell-build-only.1"&&
        at(package,"records").array().size()==1&&at(package,"sources").object().size()==4,
        "Level23 package version, case or original source count differs");
    const auto refs=json::parse(R"(["L23-TXT-RULE-1-60","L23-PDF-GUIDANCE-P1","L23-TXT-RUNG01-62-73","L23-PDF-CARD01-P3"])");
    const auto& record=at(package,"records").array().front();
    require(at(record,"id").string()=="fg:item:001172"&&at(record,"module_id").string()=="fg:module:001172"&&
        at(record,"workbook_id").string()=="fg:workbook:000023"&&
        at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(23)&&
        at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
        at(record,"source_refs")==refs&&at(record,"authored_text_refs")==refs&&
        at(record,"events").array().size()==36&&
        at(record,"title").string().find("isolated 36-contact rolling-triplet cell")!=std::string::npos,
        "Level23 identity, nonadmission, source closure or isolated-cell qualifier differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Level23 native source reference failed or admitted itself");
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==36&&at(sidecar,"variant_strokes").object().size()==2,
        "Level23 event or pick provenance coverage differs");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        require(variant.itemId=="fg:item:001172"&&seen.insert(variant.id).second&&
            variant.bindingsComplete&&variant.readiness.technicallyRenderable&&
            variant.validation.validReference(),"Level23 variant unavailable, foreign or duplicated");
        const bool downStart=variant.id=="fg:variant:007466";
        require(downStart||variant.id=="fg:variant:007467","Level23 foreign variant");
        auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==36&&model.measures.empty()&&
            model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
            "Level23 event count or standard setup differs");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==36,"Level23 pick provenance count differs");
        for(std::size_t i=0;i<36;++i){
            auto& event=model.events[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const auto& authored=at(record,"events").array()[i];
            const Rational onset{static_cast<std::int64_t>(i),3};
            require(at(authored,"event_id").string()==event.id&&
                at(evidence,"nominal_slot_q")==at(authored,"onset_q")&&
                at(evidence,"duration_q")==at(authored,"duration_q")&&
                event.kind==music::Kind::Note&&event.span.onset==onset&&
                event.span.duration==Rational{1,3}&&event.tones.size()==1&&
                event.sourceRef==at(evidence,"source_txt_ref").string(),
                "Level23 authored q1/3 timing, note or original source differs");
            const auto& tone=event.tones.front();
            require(number(at(evidence,"source_string"))==tone.string&&
                number(at(evidence,"source_fret"))==tone.fret&&
                number(at(evidence,"source_midi"))==tone.midi&&
                std::to_string(number(at(evidence,"source_finger")))==tone.finger&&
                at(evidence,"source_pitch_spelling").string()==tone.spelling&&
                tone.attack==music::Attack::Picked&&tone.tieFrom.empty()&&
                number(at(evidence,"source_contact"))==static_cast<std::int64_t>(i+1)&&
                number(at(evidence,"source_group"))==static_cast<std::int64_t>(i/3+1),
                "Level23 printed string, fret, finger, pitch, contact or articulation differs");
            const auto& degrees=at(authored,"degree_contexts").object();
            require(degrees.size()==1&&at(degrees.begin()->second,"source_label")==at(evidence,"source_degree"),
                "Level23 printed natural-minor degree differs");
            require(at(evidence,"repeated_high_root_at_turn").boolean()==(i==17||i==18),
                "Level23 repeated octave-root contacts differ");
            const char* stroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==stroke&&
                at(at(evidence,"pick_strokes"),variant.id.c_str()).string()==stroke,
                "Level23 D/U cycle resets at triplet or root turn");
            event.handDirection=stroke;
        }
        const auto& a=model.events[17].tones.front();const auto& b=model.events[18].tones.front();
        require(a.string==b.string&&a.fret==b.fret&&a.midi==b.midi&&
            a.string==3&&a.fret==7&&a.midi==57,
            "Level23 repeated D-string fret7 root lost separate attacks");
        variant.validation=music::validate(model);
        require(variant.validation.validReference(),"Level23 stroke projection failed native validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007466","fg:variant:007467"},
        "Level23 exact D/U identities differ");
    return result;
}
} // namespace fathom::lesson
