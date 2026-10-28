#pragma once
// Exact reviewed Level24 first linked cell plus a distinct, hash-bound runtime decision.
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel024Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    using J=json::Value;
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    auto at=[](const J& v,const char* key)->const J&{return v.object().at(key);};
    auto number=[&](const J& v){std::int64_t n{};require(v.integer(n),"Level24 integer source field differs");return n;};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level24 runtime decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=10;limits.values=300;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","decision_sha256","source_review_evidence","source_review_sha256",
        "native_review_evidence","native_review_sha256","domain_review_evidence","domain_review_sha256",
        "conditional_decision_evidence","conditional_decision_sha256",
        "prior_installed_review_evidence","prior_installed_review_sha256",
        "package_sha256","profile_sha256","native_source_profile_sha256","registry_sha256","source_provenance_sha256","scope",
        "source_contacts_picking_timing_accepted","stable_identities_accepted","one_case_runtime_eligible"};
    std::set<std::string> actual;for(const auto& field:d.object())actual.insert(field.first);
    require(actual==fields,"Unsupported Level24 runtime decision fields");
    require(at(d,"version").string()=="level024-first-linked-cell-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level24 runtime decision not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence","source_review_evidence",
                         "native_review_evidence","domain_review_evidence","conditional_decision_evidence",
                         "prior_installed_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level24 authority attribution missing");
    for(const char* key:{"source_contacts_picking_timing_accepted","stable_identities_accepted",
                         "one_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level24 exact one-case acceptance missing");
    require(at(d,"source_review_sha256").string()=="8d68eee93a7b39b6ffb56b1b587802af30e745067d7a170f4c3ab05a0655559c"&&
        at(d,"native_review_sha256").string()=="190b353c58f3b3a85bb6577909a808317c671904fab915fb38fdeebbdb656f2f"&&
        at(d,"domain_review_sha256").string()=="c19f3f297e194a0381a2920fe401baaa69ec1509ea18478db41c03a216f138e8"&&
        at(d,"conditional_decision_sha256").string()=="6a25ffc9c416f4ae06dc69717d8c614a88d388ef14f91c551ff5ed2fc1e5d372"&&
        at(d,"prior_installed_review_sha256").string()=="822663ed4b9cb3370a4e7b739082ed038764b0cab0b78f623613d1c82bdee9b7",
        "Level24 independent source, native, domain, Curriculum or prior installed authority differs");
    constexpr const char* packageSha="ac54e5b11111ffa7dd2109fd93de9c93b2d6e2082929325acecc1e7a3c777e53";
    constexpr const char* profileSha="1e2cd1af607b7e391c4b537d2ea8b7589e9dac101b928afb9c1e24f383c73db9";
    constexpr const char* nativeSourceProfileSha="c404c6d487b9ea8862e5684302e563aa722d923eccb93f003c5bad83960f790c";
    constexpr const char* registrySha="1b073b800355899dcf1b1fc200c661647cc061479f18a9e24a5adf8f8083b2da";
    constexpr const char* provenanceSha="0390dcbaa2b27aecc320b478d1bdf9994cca8992c58a84ece2c1d759caaf0260";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level24 canonical package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level24 canonical profile changed");
    constexpr const char* sourceProfilePath="Build/parallel-02/controlled-open-level024-first-linked-integration-r01/shared-r01/native-candidate-r01/packet/expected-profile.json";
    constexpr const char* planSha="7a71deb04dd48a4d22456562ec2aa4e0ae794164ab80d3f5e0a4bc1c91d11908";
    const auto sourceProfileBytes=content::readBounded(input.sourceRoot/sourceProfilePath,1024*1024);
    require(content::sha256(sourceProfileBytes)==nativeSourceProfileSha&&
        at(d,"native_source_profile_sha256").string()==nativeSourceProfileSha,
        "Level24 independently reviewed native source profile changed");
    auto installedProfile=json::parse(input.profile);
    const auto expectedPlan=json::parse(R"({"availability":"required_unsupplied","entry_ids":[],"path":"installed-empty-resource-plan.json","sha256":"7a71deb04dd48a4d22456562ec2aa4e0ae794164ab80d3f5e0a4bc1c91d11908"})");
    require(at(installedProfile,"resource_plan")==expectedPlan&&
        content::sha256(content::readBounded(input.sourceRoot/"installed-empty-resource-plan.json",1024*1024))==planSha&&
        json::parse(content::readBounded(input.sourceRoot/"installed-empty-resource-plan.json",1024*1024))==json::parse(R"({"resources":[]})"),
        "Level24 installed resource adapter differs from exact empty format requirement");
    installedProfile.object()["resource_plan"]=J{};
    require(installedProfile==json::parse(sourceProfileBytes),
        "Level24 installed profile differs from independently reviewed source beyond empty resource adapter");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level24 canonical registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level24 source/pick provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"case":{"events":78,"gap_after_event":0,"gap_duration_q":0,"item_id":"fg:item:001173","module_id":"fg:module:001173","span_q":26,"variant_ids":["fg:variant:007468","fg:variant:007469"]},"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"recorded_domain":"Technique/fretboard","rhythm_groove_inferred":false,"whole_workbook":false})");
    require(at(d,"scope")==expectedScope,"Level24 exact case, q26 span or no-credit scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level024-first-linked-cell-build-only.1"&&
        at(package,"records").array().size()==1&&at(package,"sources").object().size()==5,
        "Level24 package version, case or five original source keys differ");
    const auto refs=json::parse(R"(["L24-TXT-RULE-1-70","L24-TXT-RUNG01-73-94","L24-PDF-TUNING-P2","L24-PDF-CARD01-P3","L24-PDF-PHASES-P10"])");
    const auto& record=at(package,"records").array().front();
    require(at(record,"id").string()=="fg:item:001173"&&at(record,"module_id").string()=="fg:module:001173"&&
        at(record,"workbook_id").string()=="fg:workbook:000024"&&
        at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(24)&&
        at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
        at(record,"source_refs")==refs&&at(record,"authored_text_refs")==refs&&
        at(record,"events").array().size()==78&&
        at(record,"title").string().find("first linked 78-contact rolling-triplet cell")!=std::string::npos,
        "Level24 identity, nonadmitted source reference or first-cell qualifier differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Level24 native source reference failed or admitted itself");
    const auto sidecar=json::parse(provenance);
    require(at(sidecar,"events").object().size()==78&&at(sidecar,"variant_strokes").object().size()==2,
        "Level24 source or pick sidecar coverage differs");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        require(variant.itemId=="fg:item:001173"&&seen.insert(variant.id).second&&
            variant.bindingsComplete&&variant.readiness.technicallyRenderable&&
            variant.validation.validReference(),"Level24 variant unavailable, foreign or duplicated");
        const bool downStart=variant.id=="fg:variant:007468";
        require(downStart||variant.id=="fg:variant:007469","Level24 foreign variant");
        auto& model=variant.source;
        require(!model.syntheticFixture&&model.events.size()==78&&model.measures.empty()&&
            model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
            "Level24 event count or standard-tuning setup differs");
        const auto& strokes=at(at(sidecar,"variant_strokes"),variant.id.c_str()).array();
        require(strokes.size()==78,"Level24 provenance pick count differs");
        for(std::size_t i=0;i<78;++i){
            auto& event=model.events[i];
            const auto& evidence=at(at(sidecar,"events"),event.id.c_str());
            const auto& authored=at(record,"events").array()[i];
            const Rational onset{static_cast<std::int64_t>(i),3};
            require(at(authored,"event_id").string()==event.id&&
                at(evidence,"onset_q")==at(authored,"onset_q")&&
                at(evidence,"metric_duration_q")==at(authored,"duration_q")&&
                event.kind==music::Kind::Note&&event.span.onset==onset&&
                event.span.duration==Rational{1,3}&&event.tones.size()==1&&
                event.sourceRef==at(evidence,"source_txt_ref").string(),
                "Level24 source contact, q1/3 timing or original reference differs");
            const auto& tone=event.tones.front();
            require(number(at(evidence,"derived_string_index_low_to_high"))==tone.string&&
                number(at(evidence,"source_fret"))==tone.fret&&
                number(at(evidence,"derived_midi"))==tone.midi&&
                std::to_string(number(at(evidence,"source_finger")))==tone.finger&&
                at(evidence,"source_tone_lookup").string()==tone.spelling&&
                tone.attack==music::Attack::Picked&&tone.tieFrom.empty()&&
                number(at(evidence,"source_contact"))==static_cast<std::int64_t>(i+1)&&
                number(at(evidence,"source_group"))==static_cast<std::int64_t>(i/3+1)&&
                number(at(evidence,"source_group_slot"))==static_cast<std::int64_t>(i%3+1),
                "Level24 printed fret, finger, tone, contact, triplet or model-derived MIDI differs");
            const auto& degrees=at(authored,"degree_contexts").object();
            require(degrees.size()==1&&at(degrees.begin()->second,"source_label")==at(evidence,"source_degree_lookup"),
                "Level24 printed natural-minor degree differs");
            require(at(evidence,"repeated_high_root_at_turn").boolean()==(i==38||i==39),
                "Level24 repeated octave-root turn differs");
            // Native per-note pick tokens are empty; source-provenance is the explicit reviewed stroke authority.
            const char* stroke=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==stroke&&
                at(at(evidence,"pick_strokes"),variant.id.c_str()).string()==stroke,
                "Level24 D/U stroke cycle resets or differs from source sidecar");
            event.handDirection=stroke;
        }
        const auto& a=model.events[38].tones.front();const auto& b=model.events[39].tones.front();
        require(a.string==6&&b.string==6&&a.fret==5&&b.fret==5&&a.midi==69&&b.midi==69&&
                model.events[38].id!=model.events[39].id,
                "Level24 contacts39/40 lost two separate high-e fret5 octave-root attacks");
        variant.validation=music::validate(model);
        require(variant.validation.validReference(),"Level24 sidecar stroke projection failed native validation");
    }
    require(seen==std::set<std::string>{"fg:variant:007468","fg:variant:007469"},
        "Level24 exact D/U identities differ");
    return result;
}
} // namespace fathom::lesson
