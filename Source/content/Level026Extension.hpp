#pragma once
// Exact reviewed Level26 first rolling-four cell; separate runtime authority.
#include "content/Canonical.hpp"
#include <set>
#include <charconv>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel026Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* why){if(!ok)throw std::runtime_error(why);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level26 integer source field differs");return n;};
    auto rowNumber=[&](const J& value){
        require(value.isString(),"Level26 TSV numeric field is not a source string");
        const auto& text=value.string();std::int64_t result{};
        const auto parsed=std::from_chars(text.data(),text.data()+text.size(),result);
        require(parsed.ec==std::errc{}&&parsed.ptr==text.data()+text.size(),"Level26 TSV integer differs");
        return result;
    };
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level26 runtime decision hash differs from installed authority pin");
    const auto d=json::parse(disposition);
    require(at(d,"version").string()=="level026-first-cell-curriculum-decision.1"&&
            at(d,"status").string()=="ACCEPTED"&&
            at(d,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner",
        "Level26 exact case runtime decision absent");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted",
                         "one_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level26 source or runtime acceptance absent");
    require(at(d,"decision_sha256").string()=="2c6937c8bbdd143b56f003dc04fd47471b34b0612e381605ee5f88f4c22636c3"&&
            at(d,"source_producer_sha256").string()=="e2778ea5f8c52fb2efc481ee655e5ebca71230b28d91272e069292b9896ad2fc"&&
            at(d,"source_review_sha256").string()=="a3640fd5c396b93c7ca0aeade7bdda72ca5c4f1137284b105d6e5735be6b730c"&&
            at(d,"domain_review_sha256").string()=="2c6937c8bbdd143b56f003dc04fd47471b34b0612e381605ee5f88f4c22636c3",
        "Level26 Curriculum, independent source/native or domain authority differs");
    constexpr const char* packageSha="ab71d0310b5db248b83ae8f4b8bab15cc64ace9547d3eaca849145e4543d91bf";
    constexpr const char* sourceProfileSha="5fead19f8fbc8a64df051ef9859dabd61ef0adbfc89f2b42a38c82aa65239eb2";
    constexpr const char* registrySha="b792d3e89d0e6d7f3dab9308b5be6ec0cb52aa06930ff990bbf035e68ddf6792";
    constexpr const char* provenanceSha="8a687cfe61022f8cbc1ddadc2faad41354c021d30489f71187b5adb80fbb9e79";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level26 canonical package changed");
    require(content::sha256(input.profile)==at(d,"profile_sha256").string()&&
            input.expectedProfileSha256==at(d,"profile_sha256").string(),
        "Level26 installed profile changed");
    constexpr const char* sourceProfilePath=
        "Build/parallel-02/resumed-level026-r01/native-candidate-r01/packet/expected-profile.json";
    const auto sourceProfile=content::readBounded(input.sourceRoot/sourceProfilePath,1024*1024);
    require(content::sha256(sourceProfile)==sourceProfileSha&&
            at(d,"native_source_profile_sha256").string()==sourceProfileSha,
        "Level26 nonadmitted native source profile changed");
    auto installedProfile=json::parse(input.profile);
    const auto plan=json::parse(content::readBounded(input.sourceRoot/"installed-empty-resource-plan.json",1024*1024));
    require(plan==json::parse(R"({"resources":[]})")&&
            at(installedProfile,"resource_plan")==json::parse(R"({"availability":"required_unsupplied","entry_ids":[],"path":"installed-empty-resource-plan.json","sha256":"7a71deb04dd48a4d22456562ec2aa4e0ae794164ab80d3f5e0a4bc1c91d11908"})"),
        "Level26 empty installed resource adapter differs");
    installedProfile.object()["resource_plan"]=J{};
    require(installedProfile==json::parse(sourceProfile),
        "Level26 installed profile differs from nonadmitted source beyond empty adapter");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha&&
            content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level26 canonical identity or source/pick provenance changed");
    const auto scope=json::parse(R"({"automatic_credit":false,"case":{"events":96,"gap_after_event":0,"gap_duration_q":0,"item_id":"fg:item:001177","module_id":"fg:module:001177","span_q":24,"variant_ids":["fg:variant:007476","fg:variant:007477"]},"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"recorded_domain":"Technique/fretboard","rhythm_groove_inferred":false,"whole_workbook":false})");
    require(at(d,"scope")==scope,"Level26 exact first96/q24/no-credit decision scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level026-first-cell-build-only.1"&&
            at(package,"records").array().size()==1&&at(package,"sources").object().size()==3,
        "Level26 version, case count or three source keys differ");
    const auto refs=json::parse(R"(["L26-TXT-RULE-1-76","L26-TXT-RUNG01-79-100","L26-PDF-CARD01-P3"])");
    const auto& record=at(package,"records").array().front();
    require(at(record,"id").string()=="fg:item:001177"&&
            at(record,"module_id").string()=="fg:module:001177"&&
            at(record,"workbook_id").string()=="fg:workbook:000026"&&
            at(record,"content_revision")==J::fromInteger(1)&&
            at(record,"legacy_level")==J::fromInteger(26)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==refs&&at(record,"authored_text_refs")==refs&&
            at(record,"events").array().size()==96,
        "Level26 selected first96 nonadmitted source reference differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Level26 native nonadmitted source reference failed");
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==96&&at(sidecar,"variant_strokes").object().size()==2&&
            at(sidecar,"fixed_bpm").null()&&at(sidecar,"acoustic_gate").null()&&
            at(sidecar,"runtime_eligible").isBool()&&!at(sidecar,"runtime_eligible").boolean(),
        "Level26 source/pick sidecar or unsupplied acoustic limits differ");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        require(variant.itemId=="fg:item:001177"&&seen.insert(variant.id).second&&
                variant.bindingsComplete&&variant.readiness.technicallyRenderable&&
                variant.validation.validReference(),"Level26 variant unavailable, foreign or duplicated");
        const bool downStart=variant.id=="fg:variant:007476";
        require(downStart||variant.id=="fg:variant:007477","Level26 foreign variant");
        auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==96&&model.measures.empty()&&
                model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
            "Level26 event count or standard-tuning model differs");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==96,"Level26 pick provenance count differs");
        for(std::size_t i=0;i<96;++i){
            auto& event=model.events[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const auto& authored=at(record,"events").array()[i];
            const Rational onset{static_cast<std::int64_t>(i),4};
            require(at(authored,"event_id").string()==event.id&&
                    at(evidence,"onset_q")==at(authored,"onset_q")&&
                    at(evidence,"metric_duration_q")==at(authored,"duration_q")&&
                    event.kind==music::Kind::Note&&event.span.onset==onset&&
                    event.span.duration==Rational{1,4}&&event.tones.size()==1&&
                    event.sourceRef=="L26-TXT-RUNG01-79-100",
                "Level26 source contact, q1/4 timing or original reference differs");
            const auto& tone=event.tones.front();const auto& row=at(evidence,"source_row");
            require(rowNumber(at(row,"string"))==tone.string&&rowNumber(at(row,"fret"))==tone.fret&&
                    rowNumber(at(row,"midi"))==tone.midi&&
                    std::to_string(rowNumber(at(row,"finger")))==tone.finger&&
                    at(row,"spelling").string()==tone.spelling&&
                    tone.attack==music::Attack::Picked&&tone.tieFrom.empty()&&
                    number(at(evidence,"source_contact"))==static_cast<std::int64_t>(i+1)&&
                    number(at(evidence,"group"))==static_cast<std::int64_t>(i/4+1)&&
                    number(at(evidence,"slot"))==static_cast<std::int64_t>(i%4+1),
                "Level26 printed fret, finger, degree group or model MIDI differs");
            const auto& degrees=at(authored,"degree_contexts").object();
            require(degrees.size()==1&&at(degrees.begin()->second,"source_label")==at(row,"degree"),
                "Level26 natural-minor degree differs");
            require(at(evidence,"repeated_high_root_at_turn").boolean()==(i==47||i==48),
                "Level26 repeated octave-root turn differs");
            // Native per-note pick tokens are empty; the pinned sidecar supplies strokes.
            const char* stroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==stroke&&
                    at(at(evidence,"pick_strokes"),variant.id.c_str()).string()==stroke,
                "Level26 D/U stroke cycle resets or differs from source sidecar");
            event.handDirection=stroke;
        }
        const auto& a=model.events[47].tones.front();const auto& b=model.events[48].tones.front();
        require(a.string==6&&b.string==6&&a.fret==5&&b.fret==5&&a.midi==69&&b.midi==69&&
                model.events[47].id!=model.events[48].id,
            "Level26 contacts48/49 lost two separate high-e two-octave-root attacks");
        variant.validation=music::validate(model);
        require(variant.validation.validReference(),"Level26 sidecar stroke projection failed native validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007476","fg:variant:007477"},
        "Level26 exact D/U identities differ");
    return result;
}
} // namespace fathom::lesson
