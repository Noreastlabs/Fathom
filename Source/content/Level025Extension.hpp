#pragma once
// Exact reviewed Level25 first rolling-four cell; separate runtime authority.
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel025Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* why){if(!ok)throw std::runtime_error(why);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level25 integer source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level25 runtime decision hash differs from installed authority pin");
    const auto d=json::parse(disposition);
    require(at(d,"version").string()=="level025-first-cell-curriculum-decision.1"&&
            at(d,"status").string()=="ACCEPTED"&&
            at(d,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner",
        "Level25 exact case runtime decision absent");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted",
                         "one_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level25 source or runtime acceptance absent");
    require(at(d,"decision_sha256").string()=="e9616ce544aa666eebc8c1c746e7fada7d7492865e47626738d1f5d8058e1d62"&&
            at(d,"source_producer_sha256").string()=="875893cd430306b6ffff3213e04e31270f3cf7874f7626c69efa1f644c663d08"&&
            at(d,"source_review_sha256").string()=="02245944a3cca206f42e5c1c99ceb3724d3b2435eb2d7d26b11527d0e64fcda8"&&
            at(d,"domain_review_sha256").string()=="1803c9c3d39cf9cd10eb3642a2b95b0ddeacd3038065507b78dae95dd677c2b2",
        "Level25 Curriculum, independent source/native or domain authority differs");
    constexpr const char* packageSha="9a9eff3df43f2ccf725a0dd9ab93b11323e42f66dfb53f484b314f0bc58e5948";
    constexpr const char* sourceProfileSha="cedac2ec9108434da0ad92fef867939cf5081db0d8b5bc6c54b7fe64a00b41a9";
    constexpr const char* registrySha="11ef6328333f2ae49af739f47fa8228ae5aa967a85d10b1a9d5b04a50f8f0a8c";
    constexpr const char* provenanceSha="6dba8d72d72d4571c6663bef3d6a9213865d7c799b64aef78da55daeee30f550";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level25 canonical package changed");
    require(content::sha256(input.profile)==at(d,"profile_sha256").string()&&
            input.expectedProfileSha256==at(d,"profile_sha256").string(),
        "Level25 installed profile changed");
    constexpr const char* sourceProfilePath=
        "Build/parallel-02/level025-first-cell-shared-r01/native-candidate-r01/packet/expected-profile.json";
    const auto sourceProfile=content::readBounded(input.sourceRoot/sourceProfilePath,1024*1024);
    require(content::sha256(sourceProfile)==sourceProfileSha&&
            at(d,"native_source_profile_sha256").string()==sourceProfileSha,
        "Level25 nonadmitted native source profile changed");
    auto installedProfile=json::parse(input.profile);
    const auto plan=json::parse(content::readBounded(input.sourceRoot/"installed-empty-resource-plan.json",1024*1024));
    require(plan==json::parse(R"({"resources":[]})")&&
            at(installedProfile,"resource_plan")==json::parse(R"({"availability":"required_unsupplied","entry_ids":[],"path":"installed-empty-resource-plan.json","sha256":"7a71deb04dd48a4d22456562ec2aa4e0ae794164ab80d3f5e0a4bc1c91d11908"})"),
        "Level25 empty installed resource adapter differs");
    installedProfile.object()["resource_plan"]=J{};
    require(installedProfile==json::parse(sourceProfile),
        "Level25 installed profile differs from nonadmitted source beyond empty adapter");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha&&
            content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level25 canonical identity or source/pick provenance changed");
    const auto scope=json::parse(R"({"automatic_credit":false,"case":{"events":40,"gap_after_event":0,"gap_duration_q":0,"item_id":"fg:item:001176","module_id":"fg:module:001176","span_q":10,"variant_ids":["fg:variant:007474","fg:variant:007475"]},"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"recorded_domain":"Technique/fretboard","rhythm_groove_inferred":false,"whole_workbook":false})");
    require(at(d,"scope")==scope,"Level25 exact first40/q10/no-credit decision scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level025-first-cell-build-only.1"&&
            at(package,"records").array().size()==1&&at(package,"sources").object().size()==4,
        "Level25 version, case count or four source keys differ");
    const auto refs=json::parse(R"(["L25-TXT-RULE-1-64","L25-TXT-RUNG01-67-78","L25-PDF-WORKED-P1","L25-PDF-CARD01-P3"])");
    const auto& record=at(package,"records").array().front();
    require(at(record,"id").string()=="fg:item:001176"&&
            at(record,"module_id").string()=="fg:module:001176"&&
            at(record,"workbook_id").string()=="fg:workbook:000025"&&
            at(record,"content_revision")==J::fromInteger(1)&&
            at(record,"legacy_level")==J::fromInteger(25)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==refs&&at(record,"authored_text_refs")==refs&&
            at(record,"events").array().size()==40,
        "Level25 selected first40 nonadmitted source reference differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Level25 native nonadmitted source reference failed");
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==40&&at(sidecar,"variant_strokes").object().size()==2&&
            at(sidecar,"fixed_bpm").null()&&at(sidecar,"acoustic_gate").null()&&
            at(sidecar,"runtime_eligible").isBool()&&!at(sidecar,"runtime_eligible").boolean(),
        "Level25 source/pick sidecar or unsupplied acoustic limits differ");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        require(variant.itemId=="fg:item:001176"&&seen.insert(variant.id).second&&
                variant.bindingsComplete&&variant.readiness.technicallyRenderable&&
                variant.validation.validReference(),"Level25 variant unavailable, foreign or duplicated");
        const bool downStart=variant.id=="fg:variant:007474";
        require(downStart||variant.id=="fg:variant:007475","Level25 foreign variant");
        auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==40&&model.measures.empty()&&
                model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
            "Level25 event count or standard-tuning model differs");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==40,"Level25 pick provenance count differs");
        for(std::size_t i=0;i<40;++i){
            auto& event=model.events[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const auto& authored=at(record,"events").array()[i];
            const Rational onset{static_cast<std::int64_t>(i),4};
            require(at(authored,"event_id").string()==event.id&&
                    at(evidence,"metric_onset_q")==at(authored,"onset_q")&&
                    at(evidence,"metric_duration_q")==at(authored,"duration_q")&&
                    event.kind==music::Kind::Note&&event.span.onset==onset&&
                    event.span.duration==Rational{1,4}&&event.tones.size()==1&&
                    event.sourceRef==at(evidence,"source_txt_ref").string(),
                "Level25 source contact, q1/4 timing or original reference differs");
            const auto& tone=event.tones.front();const auto& row=at(evidence,"source_row");
            require(number(at(row,"string"))==tone.string&&number(at(row,"fret"))==tone.fret&&
                    number(at(evidence,"derived_midi"))==tone.midi&&
                    std::to_string(number(at(row,"finger")))==tone.finger&&
                    at(row,"spelling").string()==tone.spelling&&
                    tone.attack==music::Attack::Picked&&tone.tieFrom.empty()&&
                    number(at(evidence,"source_contact"))==static_cast<std::int64_t>(i+1)&&
                    number(at(evidence,"source_group"))==static_cast<std::int64_t>(i/4+1)&&
                    number(at(evidence,"source_group_slot"))==static_cast<std::int64_t>(i%4+1),
                "Level25 printed fret, finger, degree group or model MIDI differs");
            const auto& degrees=at(authored,"degree_contexts").object();
            require(degrees.size()==1&&at(degrees.begin()->second,"source_label")==at(row,"degree"),
                "Level25 natural-minor degree differs");
            require(at(evidence,"repeated_high_root_at_turn").boolean()==(i==19||i==20),
                "Level25 repeated octave-root turn differs");
            // Native per-note pick tokens are empty; the pinned sidecar supplies strokes.
            const char* stroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==stroke&&
                    at(at(evidence,"pick_strokes"),variant.id.c_str()).string()==stroke,
                "Level25 D/U stroke cycle resets or differs from source sidecar");
            event.handDirection=stroke;
        }
        const auto& a=model.events[19].tones.front();const auto& b=model.events[20].tones.front();
        require(a.string==3&&b.string==3&&a.fret==7&&b.fret==7&&a.midi==57&&b.midi==57&&
                model.events[19].id!=model.events[20].id,
            "Level25 contacts20/21 lost two separate D-string octave-root attacks");
        variant.validation=music::validate(model);
        require(variant.validation.validReference(),"Level25 sidecar stroke projection failed native validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007474","fg:variant:007475"},
        "Level25 exact D/U identities differ");
    return result;
}
} // namespace fathom::lesson
