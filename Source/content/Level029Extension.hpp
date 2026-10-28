#pragma once
// Exact Level29 Module1 first30 source cell; its native reference is nonadmitted.
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel029Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level29 integer source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level29 runtime decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=10;limits.values=300;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    require(at(d,"version").string()=="level029-module1-first30-curriculum-decision.1"&&
            at(d,"status").string()=="ACCEPTED"&&
            at(d,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner",
            "Level29 exact case runtime decision absent");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted","one_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level29 source or runtime acceptance absent");
    require(at(d,"source_review_sha256").string()=="f383ce43c1b9ab856770e344e537c6b9d901e17622d266b1709457e71f9072e3"&&
            at(d,"domain_review_sha256").string()=="e1169a04b1850ce1ac4767c6c6f31a834f283f5193f468dab3a7354eb44cb095"&&
            at(d,"conditional_decision_sha256").string()=="c1f574da8818b1e35b18f8d8f4ef417b28aa669663e2a37b5ceb7f459a3df543"&&
            at(d,"prior_installed_review_sha256").string()=="992db918f9096492b81b6c957f5ddb3b0327b7199fe6c8137e857c8cfc147ee1",
            "Level29 independent source, domain, Curriculum or prior installed authority differs");
    constexpr const char* packageSha="e0773097a98923f139854769d8e97dbe70c5764bb84abd0eca98b1bc291dfdbc";
    constexpr const char* sourceProfileSha="0978538928258e9a378310910e46ef0c18612005e21268f5d9ce7db306c6fd58";
    constexpr const char* registrySha="88aa41960b73f6c9a7b61f80c5fe0c9c98acc585772779857b1b5dd74182ca69";
    constexpr const char* provenanceSha="38ec4d8fc5fd7743c4d661a45f23c09c8763457e66c9f8c7f6e79ba6dde46ead";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level29 canonical package changed");
    require(content::sha256(input.profile)==at(d,"profile_sha256").string()&&
            input.expectedProfileSha256==at(d,"profile_sha256").string(),
        "Level29 installed profile changed");
    const auto sourceProfileBytes=content::readBounded(input.sourceRoot/
        "Build/parallel-02/controlled-open-level029-module1-first30-integration-r01/shared-r01/native-candidate-r01/packet/expected-profile.json",1024*1024);
    require(content::sha256(sourceProfileBytes)==sourceProfileSha&&
            at(d,"native_source_profile_sha256").string()==sourceProfileSha,
        "Level29 canonical native source profile changed");
    auto installedProfile=json::parse(input.profile);
    const auto plan=json::parse(content::readBounded(input.sourceRoot/"installed-empty-resource-plan.json",1024*1024));
    require(plan==json::parse(R"({"resources":[]})")&&
            at(installedProfile,"resource_plan")==json::parse(R"({"availability":"required_unsupplied","entry_ids":[],"path":"installed-empty-resource-plan.json","sha256":"7a71deb04dd48a4d22456562ec2aa4e0ae794164ab80d3f5e0a4bc1c91d11908"})"),
        "Level29 empty installed resource adapter differs");
    installedProfile.object()["resource_plan"]=J{};
    require(installedProfile==json::parse(sourceProfileBytes),
        "Level29 installed profile differs from nonadmitted source profile beyond empty adapter");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha&&
            content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level29 canonical identity or source/pick provenance changed");
    const auto scope=json::parse(R"({"automatic_credit":false,"case":{"events":30,"gap_after_event":0,"gap_duration_q":0,"item_id":"fg:item:001175","module_id":"fg:module:001175","span_q":15,"variant_ids":["fg:variant:007472","fg:variant:007473"]},"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"recorded_domain":"Technique/fretboard","rhythm_groove_inferred":false,"whole_workbook":false})");
    require(at(d,"scope")==scope,"Level29 exact first30/q15/no-credit decision scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level029-module1-first30-build-only.1"&&
            at(package,"records").array().size()==1&&at(package,"sources").object().size()==4,
        "Level29 version, case count or four source keys differ");
    const auto refs=json::parse(R"(["L29-TXT-RULES-1-46","L29-TXT-RUNG01-80-95","L29-PDF-PULSE-P2","L29-PDF-CARD-P3"])");
    const auto& record=at(package,"records").array().front();
    require(at(record,"id").string()=="fg:item:001175"&&
            at(record,"module_id").string()=="fg:module:001175"&&
            at(record,"workbook_id").string()=="fg:workbook:000029"&&
            at(record,"content_revision")==J::fromInteger(1)&&
            at(record,"legacy_level")==J::fromInteger(29)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==refs&&at(record,"authored_text_refs")==refs&&
            at(record,"events").array().size()==30,
        "Level29 selected first30 nonadmitted source reference differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Level29 native nonadmitted source reference failed");
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==30&&at(sidecar,"variant_strokes").object().size()==30&&
            at(sidecar,"fixed_bpm").null()&&at(sidecar,"acoustic_gate").null()&&
            at(sidecar,"runtime_eligible").isBool()&&!at(sidecar,"runtime_eligible").boolean(),
        "Level29 source/pick sidecar or unsupplied acoustic limits differ");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        require(variant.itemId=="fg:item:001175"&&seen.insert(variant.id).second&&
                variant.bindingsComplete&&variant.readiness.technicallyRenderable&&
                variant.validation.validReference(),"Level29 variant unavailable, foreign or duplicated");
        const bool downStart=variant.id=="fg:variant:007472";
        require(downStart||variant.id=="fg:variant:007473","Level29 foreign variant");
        auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==30&&model.measures.empty()&&
                model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
                "Level29 standard-tuning model or 30 events differ");
        for(std::size_t i=0;i<30;++i){
            auto& event=model.events[i];const auto& authored=at(record,"events").array()[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const auto& contact=at(evidence,"contact");
            const Rational onset{static_cast<std::int64_t>(i),2};
            require(at(authored,"event_id").string()==event.id&&
                    at(contact,"onset_q")==at(authored,"onset_q")&&
                    at(contact,"metric_duration_q")==at(authored,"duration_q")&&
                    event.kind==music::Kind::Note&&event.span.onset==onset&&
                    event.span.duration==Rational{1,2}&&event.tones.size()==1&&
                    event.sourceRef=="L29-TXT-RUNG01-80-95",
                "Level29 source contact or q1/2 grid differs");
            const auto& tone=event.tones.front();
            require(tone.string==number(at(contact,"model_string"))&&
                    tone.fret==number(at(contact,"source_fret"))&&
                    tone.midi==number(at(contact,"model_midi"))&&
                    tone.finger==std::to_string(number(at(contact,"source_finger")))&&
                    tone.spelling==at(contact,"source_tone").string()&&
                    tone.attack==music::Attack::Picked&&tone.tieFrom.empty()&&
                    number(at(contact,"contact"))==static_cast<std::int64_t>(i+1)&&
                    at(authored,"degree_contexts").object().at("A-natural-minor").object().at("source_label")==at(contact,"source_degree"),
                "Level29 printed degree/finger/string/fret or derived MIDI differs");
            const char* stroke=((i%2==0)==downStart)?"D":"U";
            require(at(at(evidence,"pick_strokes"),variant.id.c_str()).string()==stroke&&
                    at(at(at(sidecar,"variant_strokes"),event.id.c_str()),variant.id.c_str()).string()==stroke,
                "Level29 continuous alternate pick cycle differs from reviewed source sidecar");
            // Native pick tokens are empty. Keep reviewed stroke provenance distinct.
            event.handDirection=stroke;
        }
        require(model.events[14].id!=model.events[15].id&&
                model.events[14].tones.front().string==6&&model.events[15].tones.front().string==6&&
                model.events[14].tones.front().fret==5&&model.events[15].tones.front().fret==5,
            "Level29 high-e root contacts15/16 must be separate picked attacks");
        variant.validation=music::validate(model);
        require(variant.validation.validReference(),"Level29 stroke projection failed music validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007472","fg:variant:007473"},
        "Level29 exact D/U identities differ");
    return result;
}
} // namespace fathom::lesson
