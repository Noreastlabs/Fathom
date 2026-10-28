#pragma once
// Exact source-reviewed Level15 Rung04 Db-major 78-contact case; no automatic learner credit.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel015Rung04Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool yes,const char* why){if(!yes)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    constexpr const char* originalRoot="Build/parallel-02/level015-r04-native-candidate-r01/";
    constexpr const char* originalPackageSha="29677c3eba7a1667474bae5ee51d0d8ee9af80f429b62d05ae4468046e7c364c";
    constexpr const char* originalProfileSha="77b475ba5e8a9d73d891ae351894ad2e6ff3728ab04c81c7013b10e3dd983dd1";
    constexpr const char* originalRegistrySha="7bab6bf2aad67c49516e3df65c15a46aba8af8d290977ce65a6734753f205d6b";
    constexpr const char* packageSha="29677c3eba7a1667474bae5ee51d0d8ee9af80f429b62d05ae4468046e7c364c";
    constexpr const char* profileSha="e0ce76967f5b128a95f943b0413b943cc7fb337b951f1c2d5a725be1a5758913";
    constexpr const char* registrySha="7bab6bf2aad67c49516e3df65c15a46aba8af8d290977ce65a6734753f205d6b";
    constexpr const char* allocationSha="72b65a5dbf297fc4218851c7daf999eb9bd290a565245dab66e23420e6c46e83";
    constexpr const char* adapterSha="c171347a1dc5e39fc5013a2ba514e9c34e134b153bef1b49d2df2da685999d99";
    constexpr const char* decisionExpectedSha="09c4ab91fa98b90f07b330e6712d55497c4ca83495d89de9668e0f2930fc8246";
    constexpr const char* version="curriculum-v1-level015-rung04-triplet-build-only.1";
    constexpr const char* adapterPath="Content/runtime/level015-rung04-extension-v1/installed-resource-plan.json";
    constexpr const char* allocationPath="Build/parallel-02/level015-r04-native-candidate-r01/candidate-allocation.json";
    need(decisionSha==decisionExpectedSha&&content::sha256(decisionBytes)==decisionSha,
         "Level15 Rung04 exact agent decision hash differs");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level015-rung04-triplet-curriculum-decision.1"&&
         at(decision,"status").string()=="ACCEPTED"&&
         at(decision,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner"&&
         at(decision,"source_review_sha256").string()=="cbb2ec952199356c49f3e7fbc3aa15472f167f3e8783ec6032e207ca364c5619"&&
         at(decision,"native_review_sha256").string()=="7d8e8ecfabd72ecb2a01bff656537869ab2fa0be17d34feaaca8bf9049e63aff"&&
         at(decision,"native_adoption_sha256").string()=="84d39891ea3eed3538a7766017ebfb5ce75002f2febd8593d6792c38d1d5cc70"&&
         at(decision,"manager_release_sha256").string()=="214a0239968e86aa62a8f53b50c68a4f61fa1752a581f179031384af889116f4"&&
         at(decision,"package_sha256").string()==packageSha&&
         at(decision,"profile_sha256").string()==profileSha&&
         at(decision,"registry_sha256").string()==registrySha&&
         at(decision,"resource_adapter_sha256").string()==adapterSha&&
         at(decision,"allocation_sha256").string()==allocationSha&&
         at(decision,"original_package_sha256").string()==originalPackageSha&&
         at(decision,"original_profile_sha256").string()==originalProfileSha&&
         at(decision,"original_registry_sha256").string()==originalRegistrySha,
         "Level15 Rung04 source/native/Curriculum authority differs");
    const auto expectedScope=json::parse(R"fathom({"item_id":"fg:item:001186","module_id":"fg:module:001186","variant_ids":["fg:variant:007712","fg:variant:007713"],"event_ids":"fg:item:001186:event:0001..0078","events":78,"source_passages":5,"source_row":"printed:l015:complete-tablature:rung-04-of-13-c-major-root-on-low-e-fret-8-frame-7-10","content_revision":1,"recorded_domain":"Technique/fretboard","source_timing":"source_defined_attributed_quarter_triplets","authored_grid":"nominal_q0_to_q26_thirds","fixed_authored_bpm":false,"fixed_authored_meter":false,"intercell_pause_included":false,"tail_pause_included":false,"resource_availability":"required_unsupplied","resource_entries":16,"supplied_media":false,"automatic_credit":false,"accuracy_assessment":false,"rhythm_groove_inferred":false,"mastery":false,"whole_ladder":false,"whole_workbook":false})fathom");
    need(at(decision,"scope")==expectedScope,"Level15 Rung04 one-cell no-credit scope differs");
    need(content::sha256(input.package)==packageSha&&content::sha256(input.profile)==profileSha&&
         input.expectedProfileSha256==profileSha&&content::sha256(input.registry)==registrySha,
         "Level15 Rung04 installed packet differs");
    auto frozen=[&](const std::string& path,const char* hash){const auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==hash,"Level15 Rung04 frozen asset differs");return json::parse(bytes);};
    const auto originalPackage=frozen(std::string(originalRoot)+"package.json",originalPackageSha);
    const auto originalProfile=frozen(std::string(originalRoot)+"expected-profile.json",originalProfileSha);
    const auto originalRegistry=frozen(std::string(originalRoot)+"identity-registry.json",originalRegistrySha);
    const auto allocation=frozen(allocationPath,allocationSha);
    const auto adapter=frozen(adapterPath,adapterSha);
    need(at(allocation,"records").object().size()==1&&at(allocation,"records").object().count("fg:item:001186")==1&&
         at(adapter,"availability").string()=="required_unsupplied"&&
         at(adapter,"resources").array().empty()&&at(adapter,"entry_ids").array().size()==16&&
         at(adapter,"entry_ids")==at(at(originalProfile,"resource_plan"),"entry_ids")&&
         at(adapter,"original_plan_sha256")==at(at(originalProfile,"resource_plan"),"sha256"),
         "Level15 Rung04 exact allocation or unsupplied resource truth differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    need(package==originalPackage&&registry==originalRegistry,
         "Level15 Rung04 source notes, timing, identity or passages differ from reviewed reference");
    auto expectedProfile=originalProfile;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"availability\":\"required_unsupplied\",\"entry_ids\":")+
        json::stringify(at(adapter,"entry_ids")) + ",\"path\":\""+adapterPath+"\",\"sha256\":\""+adapterSha+"\"}");
    need(profile==expectedProfile,"Level15 Rung04 installed profile or source authority differs");
    const auto& record=at(package,"records").array().front();
    need(at(package,"records").array().size()==1&&at(package,"sources").object().size()==5&&
         at(record,"id").string()=="fg:item:001186"&&at(record,"module_id").string()=="fg:module:001186"&&
         at(record,"workbook_id").string()=="fg:workbook:000015"&&
         at(at(record,"timing"),"status").string()=="source_defined"&&
         !at(record,"runtime_eligible").boolean()&&at(record,"events").array().size()==78&&
         at(record,"variants").array().size()==2&&at(package,"content_version").string()==version,
         "Level15 Rung04 source scope differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
         "Level15 Rung04 native nonadmitted reference failed");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool down=variant.id=="fg:variant:007712";
        need((down||variant.id=="fg:variant:007713")&&seen.insert(variant.id).second&&
             variant.itemId=="fg:item:001186"&&variant.bindingsComplete&&
             variant.readiness.technicallyRenderable&&variant.validation.validReference(),
             "Level15 Rung04 foreign or unrenderable variant");
        auto& model=variant.source;
        need(model.events.size()==78&&model.measures.empty()&&
             model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
             "Level15 Rung04 tuning or event model differs");
        for(std::size_t i=0;i<78;++i){auto& event=model.events[i];const auto& authored=at(record,"events").array()[i];
            const auto q=Rational{static_cast<std::int64_t>(i),3};
            need(event.id==at(authored,"event_id").string()&&event.span.onset==q&&
                 event.span.duration==Rational{1,3}&&event.tones.size()==1&&
                 event.sourceRef=="L15-TXT1-142-163",
                 "Level15 Rung04 event order, nominal timing or source differs");
            event.handDirection=(((i%2==0)==down)?"D":"U");
            const auto& tone=event.tones.front();std::int64_t s{},f{},m{},finger{};
            need(at(authored,"string").integer(s)&&at(authored,"fret").integer(f)&&
                 at(authored,"midi").integer(m)&&at(authored,"finger").integer(finger)&&
                 tone.string==s&&tone.fret==f&&tone.midi==m&&tone.finger==std::to_string(finger)&&
                 tone.attack==music::Attack::Picked&&tone.tieFrom.empty(),
                 "Level15 Rung04 printed contact differs");
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference(),"Level15 Rung04 D/U model projection invalid");
    }
    need(seen==std::set<std::string>{"fg:variant:007712","fg:variant:007713"},
         "Level15 Rung04 D/U coverage differs");
    return result;
}
} // namespace fathom::lesson
