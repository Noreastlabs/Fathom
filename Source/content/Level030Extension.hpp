#pragma once
// Exact Level30 first12 source cell; native reference remains nonadmitted.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel030Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level30 integer source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level30 runtime decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=10;limits.values=300;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    require(at(d,"version").string()=="level030-first12-curriculum-decision.1"&&
            at(d,"status").string()=="ACCEPTED"&&
            at(d,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner",
            "Level30 exact case runtime decision absent");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted","one_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level30 source or runtime acceptance absent");
    require(at(d,"source_review_sha256").string()=="0c967cd48b12f081d05c5b3a37077945820e5894738b186cfb477353884bf7d3"&&
            at(d,"domain_review_sha256").string()=="312f90b79db1be37d1269a4e43c745452d362c0231e2ce896018bcd0f5f02e99"&&
            at(d,"conditional_decision_sha256").string()=="ce3b2f666756534bb8c23fee2104ad087c78756f18391472f70a394d83720380"&&
            at(d,"prior_installed_review_sha256").string()=="2f2ea23fe9985e1dc75692e0899fc373a23736beddc988bdf556704201abda3d",
            "Level30 independent source, domain, Curriculum or prior installed authority differs");
    constexpr const char* packageSha="bed49ebd54ea0192d36970ed24673950e147369c2550ee8ea3c00c29fd024a2b";
    constexpr const char* sourceProfileSha="e07825e8ee1b03864c900369778080051455d51fc2a77c48056f3d7412def36d";
    constexpr const char* registrySha="890164fe0f60a4c49253ed8ac24984e170240878989055511043cc96a1d83b46";
    constexpr const char* provenanceSha="3afd16d58558bf8efdc737a38141f1e6927c4f4a3d65ac0f84a8469c9f7b801f";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level30 canonical package changed");
    require(content::sha256(input.profile)==at(d,"profile_sha256").string()&&
            input.expectedProfileSha256==at(d,"profile_sha256").string(),
        "Level30 installed profile changed");
    const auto sourceProfileBytes=content::readBounded(input.sourceRoot/
        "Build/parallel-02/controlled-open-level030-first12-integration-r01/shared-r01/native-candidate-r01/packet/expected-profile.json",1024*1024);
    require(content::sha256(sourceProfileBytes)==sourceProfileSha&&
            at(d,"native_source_profile_sha256").string()==sourceProfileSha,
        "Level30 canonical native source profile changed");
    auto installedProfile=json::parse(input.profile);
    const auto plan=json::parse(content::readBounded(input.sourceRoot/"installed-empty-resource-plan.json",1024*1024));
    require(plan==json::parse(R"({"resources":[]})")&&
            at(installedProfile,"resource_plan")==json::parse(R"({"availability":"required_unsupplied","entry_ids":[],"path":"installed-empty-resource-plan.json","sha256":"7a71deb04dd48a4d22456562ec2aa4e0ae794164ab80d3f5e0a4bc1c91d11908"})"),
        "Level30 empty installed resource adapter differs");
    installedProfile.object()["resource_plan"]=J{};
    require(installedProfile==json::parse(sourceProfileBytes),
        "Level30 installed profile differs from nonadmitted source profile beyond empty adapter");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha&&
            content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level30 canonical identity or source/pick provenance changed");
    const auto scope=json::parse(R"({"automatic_credit":false,"case":{"events":12,"gap_after_event":0,"gap_duration_q":0,"item_id":"fg:item:001174","module_id":"fg:module:001174","span_q":6,"variant_ids":["fg:variant:007470","fg:variant:007471"]},"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"recorded_domain":"Technique/fretboard","rhythm_groove_inferred":false,"whole_workbook":false})");
    require(at(d,"scope")==scope,"Level30 exact first12/q6/no-credit decision scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level030-first12-build-only.1"&&
            at(package,"records").array().size()==1&&at(package,"sources").object().size()==5,
        "Level30 version, case count or source key count differs");
    const auto refs=json::parse(R"(["L30-TXT-RULE-14-30","L30-TXT-PRACTICE-40-46","L30-TXT-RUNG01-49-60","L30-PDF-P1","L30-PDF-P2"])");
    const auto& record=at(package,"records").array().front();
    require(at(record,"id").string()=="fg:item:001174"&&
            at(record,"module_id").string()=="fg:module:001174"&&
            at(record,"workbook_id").string()=="fg:workbook:000030"&&
            at(record,"content_revision")==J::fromInteger(1)&&
            at(record,"legacy_level")==J::fromInteger(30)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==refs&&at(record,"authored_text_refs")==refs&&
            at(record,"events").array().size()==12,
        "Level30 selected first12 nonadmitted source reference differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Level30 native nonadmitted source reference failed");
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==12&&at(sidecar,"variant_strokes").object().size()==2&&
            at(sidecar,"authored_neighbor_pause_beats")==json::parse("[1,1]")&&
            at(sidecar,"isolated_cell_tail_pause").null(),
        "Level30 source/pick sidecar or excluded neighboring pause differs");
    constexpr std::array<int,12> strings{1,1,2,2,3,3,3,3,2,2,1,1};
    constexpr std::array<int,12> frets{5,7,4,7,4,7,7,4,7,4,7,5};
    constexpr std::array<int,12> fingers{2,4,1,4,1,4,4,1,4,1,4,2};
    constexpr std::array<int,12> degrees{1,2,3,5,6,8,8,6,5,3,2,1};
    constexpr std::array<int,12> midis{45,47,49,52,54,57,57,54,52,49,47,45};
    constexpr std::array<const char*,12> tones{"A","B","C#","E","F#","A","A","F#","E","C#","B","A"};
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        require(variant.itemId=="fg:item:001174"&&seen.insert(variant.id).second&&
                variant.bindingsComplete&&variant.readiness.technicallyRenderable&&
                variant.validation.validReference(),"Level30 variant unavailable, foreign or duplicated");
        const bool downStart=variant.id=="fg:variant:007470";
        require(downStart||variant.id=="fg:variant:007471","Level30 foreign variant");
        auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==12&&model.measures.empty()&&
                model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
                "Level30 standard-tuning model or 12 events differ");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==12,"Level30 source stroke count differs");
        for(std::size_t i=0;i<12;++i){
            auto& event=model.events[i];const auto& authored=at(record,"events").array()[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const Rational onset{static_cast<std::int64_t>(i),2};
            require(at(authored,"event_id").string()==event.id&&
                    at(evidence,"metric_onset_q")==at(authored,"onset_q")&&
                    at(evidence,"metric_duration_q")==at(authored,"duration_q")&&
                    event.kind==music::Kind::Note&&event.span.onset==onset&&
                    event.span.duration==Rational{1,2}&&event.tones.size()==1&&
                    event.sourceRef=="L30-TXT-RUNG01-49-60",
                "Level30 source contact or q1/2 grid differs");
            const auto& tone=event.tones.front();
            require(tone.string==strings[i]&&tone.fret==frets[i]&&tone.midi==midis[i]&&
                    tone.finger==std::to_string(fingers[i])&&tone.spelling==tones[i]&&
                    tone.attack==music::Attack::Picked&&tone.tieFrom.empty()&&
                    number(at(evidence,"source_contact"))==static_cast<std::int64_t>(i+1)&&
                    number(at(evidence,"source_fret"))==frets[i]&&
                    number(at(evidence,"source_finger"))==fingers[i]&&
                    number(at(evidence,"derived_midi"))==midis[i]&&
                    at(evidence,"source_degree").string()==std::to_string(degrees[i]),
                "Level30 printed degree/finger/fret/tone or derived MIDI differs");
            const auto& degree=at(authored,"degree_contexts").object().at("A-major-pentatonic");
            require(at(degree,"source_label").string()==std::to_string(degrees[i]),
                "Level30 major-pentatonic degree differs");
            const char* stroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==stroke&&
                    at(at(evidence,"pick_strokes"),variant.id.c_str()).string()==stroke,
                "Level30 alternate pick cycle differs from reviewed source sidecar");
            // Native per-note pick tokens are empty; preserve separate reviewed sidecar authority.
            event.handDirection=stroke;
        }
        require(model.events[5].id!=model.events[6].id&&
                model.events[5].tones.front().string==3&&model.events[6].tones.front().string==3&&
                model.events[5].tones.front().fret==7&&model.events[6].tones.front().fret==7,
            "Level30 D7 high root must be two picked attacks");
        variant.validation=music::validate(model);
        require(variant.validation.validReference(),"Level30 stroke projection failed music validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007470","fg:variant:007471"},
        "Level30 exact D/U identities differ");
    return result;
}
} // namespace fathom::lesson
