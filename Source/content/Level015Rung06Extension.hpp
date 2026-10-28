#pragma once
// Exact source-reviewed Level15 Rung06 Db-major 78-contact case; no automatic learner credit.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel015Rung06Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool yes,const char* why){if(!yes)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    constexpr const char* originalRoot="Build/parallel-02/level015-r06-native-candidate-r01/r02/";
    constexpr const char* originalPackageSha="52de80e7680a3bda6845cc5739785cbee22f4d3b6b6dd07b7a7d01e784508cfa";
    constexpr const char* originalProfileSha="ccf82540eb90ae71e5d18fe78ce98374130f50224a7491c6229eb3d3a91a7e33";
    constexpr const char* originalRegistrySha="1b5ccc9024aa02cd61fdfa796ae18b3ae524b5c9349fd19756ae4015f777863e";
    constexpr const char* packageSha="52de80e7680a3bda6845cc5739785cbee22f4d3b6b6dd07b7a7d01e784508cfa";
    constexpr const char* profileSha="1e25757b7958613dbb8487ffa5df15e4d2526641b80f6c4921032134ff1b9347";
    constexpr const char* registrySha="1b5ccc9024aa02cd61fdfa796ae18b3ae524b5c9349fd19756ae4015f777863e";
    constexpr const char* allocationSha="6ec05184700ed72b0ffed5fae87099f563d1139d329f5c7fa53997e5ef104b13";
    constexpr const char* adapterSha="c171347a1dc5e39fc5013a2ba514e9c34e134b153bef1b49d2df2da685999d99";
    constexpr const char* decisionExpectedSha="945a0dbff35b57934be609a74b61d950569190d1667d939fe895154d708667f7";
    constexpr const char* version="curriculum-v1-level015-rung06-triplet-build-only.1";
    constexpr const char* adapterPath="Content/runtime/level015-rung06-extension-v1/installed-resource-plan.json";
    constexpr const char* allocationPath="Build/parallel-02/level015-r06-native-candidate-r01/candidate-allocation.json";
    need(decisionSha==decisionExpectedSha&&content::sha256(decisionBytes)==decisionSha,
         "Level15 Rung06 exact agent decision hash differs");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level015-rung06-triplet-curriculum-decision.1"&&
         at(decision,"status").string()=="ACCEPTED"&&
         at(decision,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner"&&
         at(decision,"source_review_sha256").string()=="7535aae004e0e34cfc5dc83a21829564bcb2f010c2a6f7b696bdf02317c6fc86"&&
         at(decision,"native_review_sha256").string()=="08692d82eb39b5becb4a3c96d5d882e299281829c0c0c862efbe1b87cf144f99"&&
         at(decision,"native_adoption_sha256").string()=="c663d4ca2608f1fdd3bfb04c62954fd8cf8c6698425f71a51b55bdf821762fb8"&&
         at(decision,"manager_release_sha256").string()=="ddf02e15ee8316e25bf1b129a5e51f79b6039d92a7f1ab9abff56d7f2d023f74"&&
         at(decision,"package_sha256").string()==packageSha&&
         at(decision,"profile_sha256").string()==profileSha&&
         at(decision,"registry_sha256").string()==registrySha&&
         at(decision,"resource_adapter_sha256").string()==adapterSha&&
         at(decision,"allocation_sha256").string()==allocationSha&&
         at(decision,"original_package_sha256").string()==originalPackageSha&&
         at(decision,"original_profile_sha256").string()==originalProfileSha&&
         at(decision,"original_registry_sha256").string()==originalRegistrySha,
         "Level15 Rung06 source/native/Curriculum authority differs");
    const auto expectedScope=json::parse(R"fathom({"item_id":"fg:item:001187","module_id":"fg:module:001187","variant_ids":["fg:variant:007714","fg:variant:007715"],"event_ids":"fg:item:001187:event:0001..0078","events":78,"source_passages":5,"source_row":"printed:l015:complete-tablature:rung-06-of-13-d-major-root-on-low-e-fret-10-frame-9-12","content_revision":1,"recorded_domain":"Technique/fretboard","source_timing":"source_defined_attributed_quarter_triplets","authored_grid":"nominal_q0_to_q26_thirds","fixed_authored_bpm":false,"fixed_authored_meter":false,"intercell_pause_included":false,"tail_pause_included":false,"resource_availability":"required_unsupplied","resource_entries":16,"supplied_media":false,"automatic_credit":false,"accuracy_assessment":false,"rhythm_groove_inferred":false,"mastery":false,"whole_ladder":false,"whole_workbook":false})fathom");
    need(at(decision,"scope")==expectedScope,"Level15 Rung06 one-cell no-credit scope differs");
    need(content::sha256(input.package)==packageSha&&content::sha256(input.profile)==profileSha&&
         input.expectedProfileSha256==profileSha&&content::sha256(input.registry)==registrySha,
         "Level15 Rung06 installed packet differs");
    auto frozen=[&](const std::string& path,const char* hash){const auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==hash,"Level15 Rung06 frozen asset differs");return json::parse(bytes);};
    const auto originalPackage=frozen(std::string(originalRoot)+"package.json",originalPackageSha);
    const auto originalProfile=frozen(std::string(originalRoot)+"expected-profile.json",originalProfileSha);
    const auto originalRegistry=frozen("Build/parallel-02/level015-r06-native-candidate-r01/identity-registry.json",originalRegistrySha);
    const auto allocation=frozen(allocationPath,allocationSha);
    const auto adapter=frozen(adapterPath,adapterSha);
    need(at(allocation,"records").object().size()==1&&at(allocation,"records").object().count("fg:item:001187")==1&&
         at(adapter,"availability").string()=="required_unsupplied"&&
         at(adapter,"resources").array().empty()&&at(adapter,"entry_ids").array().size()==16&&
         at(adapter,"entry_ids")==at(at(originalProfile,"resource_plan"),"entry_ids")&&
         at(adapter,"original_plan_sha256")==at(at(originalProfile,"resource_plan"),"sha256"),
         "Level15 Rung06 exact allocation or unsupplied resource truth differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    need(package==originalPackage&&registry==originalRegistry,
         "Level15 Rung06 source notes, timing, identity or passages differ from reviewed reference");
    auto expectedProfile=originalProfile;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"availability\":\"required_unsupplied\",\"entry_ids\":")+
        json::stringify(at(adapter,"entry_ids")) + ",\"path\":\""+adapterPath+"\",\"sha256\":\""+adapterSha+"\"}");
    need(profile==expectedProfile,"Level15 Rung06 installed profile or source authority differs");
    const auto& record=at(package,"records").array().front();
    need(at(package,"records").array().size()==1&&at(package,"sources").object().size()==5&&
         at(record,"id").string()=="fg:item:001187"&&at(record,"module_id").string()=="fg:module:001187"&&
         at(record,"workbook_id").string()=="fg:workbook:000015"&&
         at(at(record,"timing"),"status").string()=="source_defined"&&
         !at(record,"runtime_eligible").boolean()&&at(record,"events").array().size()==78&&
         at(record,"variants").array().size()==2&&at(package,"content_version").string()==version,
         "Level15 Rung06 source scope differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
         "Level15 Rung06 native nonadmitted reference failed");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool down=variant.id=="fg:variant:007714";
        need((down||variant.id=="fg:variant:007715")&&seen.insert(variant.id).second&&
             variant.itemId=="fg:item:001187"&&variant.bindingsComplete&&
             variant.readiness.technicallyRenderable&&variant.validation.validReference(),
             "Level15 Rung06 foreign or unrenderable variant");
        auto& model=variant.source;
        need(model.events.size()==78&&model.measures.empty()&&
             model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
             "Level15 Rung06 tuning or event model differs");
        for(std::size_t i=0;i<78;++i){auto& event=model.events[i];const auto& authored=at(record,"events").array()[i];
            const auto q=Rational{static_cast<std::int64_t>(i),3};
            need(event.id==at(authored,"event_id").string()&&event.span.onset==q&&
                 event.span.duration==Rational{1,3}&&event.tones.size()==1&&
                 event.sourceRef=="L15-TXT1-190-211",
                 "Level15 Rung06 event order, nominal timing or source differs");
            event.handDirection=(((i%2==0)==down)?"D":"U");
            const auto& tone=event.tones.front();std::int64_t s{},f{},m{},finger{};
            need(at(authored,"string").integer(s)&&at(authored,"fret").integer(f)&&
                 at(authored,"midi").integer(m)&&at(authored,"finger").integer(finger)&&
                 tone.string==s&&tone.fret==f&&tone.midi==m&&tone.finger==std::to_string(finger)&&
                 tone.attack==music::Attack::Picked&&tone.tieFrom.empty(),
                 "Level15 Rung06 printed contact differs");
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference(),"Level15 Rung06 D/U model projection invalid");
    }
    need(seen==std::set<std::string>{"fg:variant:007714","fg:variant:007715"},
         "Level15 Rung06 D/U coverage differs");
    return result;
}
} // namespace fathom::lesson
