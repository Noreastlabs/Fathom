#pragma once
// One reviewed, nonadmitted source reference; exact agent decision grants only supplemental Practice.
#include "content/Canonical.hpp"
#include <array>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel080ModuleAPass1R02Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool value,const char* reason){if(!value)throw std::runtime_error(reason);};
    auto at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    auto replace=[](std::string text,const std::string& from,const std::string& to){
        std::size_t pos=0;while((pos=text.find(from,pos))!=std::string::npos){text.replace(pos,from.size(),to);pos+=to.size();}return text;};
    auto rebind=[&](const J& value){auto bytes=json::stringify(value);
        bytes=replace(bytes,"fg:module:080901","fg:module:001179");
        bytes=replace(bytes,"fg:item:080901","fg:item:001179");
        bytes=replace(bytes,"fg:variant:080901","fg:variant:007696");
        return json::parse(bytes);};
    constexpr const char* oldPackageSha="40f4ff84e334f9707346a6ae9f12c88f896b23bb66c254d01999960468136824";
    constexpr const char* oldProfileSha="ce11ee1035d6d92c49f4e6d12325bd24ef76790802a9e5fc3baf51962d1779e7";
    constexpr const char* oldRegistrySha="137259d3d03bb02f652a985bfb1a6002657ed7f1e4a8d7a927aa40f13d20d184";
    constexpr const char* packageSha="cf7b66d9bf1382cc18de099bdd4e404e2065ba0a4690e01f864b4efbfefd3106";
    constexpr const char* profileSha="08110660a28f8e1364dc64c79c6c4c25eed2cbc370b6d2de487c9448c9b725ef";
    constexpr const char* registrySha="276253e7763f6e039b1b29a2f7abae6de08858fd093873075cd7b99ee47e6a15";
    constexpr const char* allocationSha="b1bcc3700df026ebf985ac7526021eb69955081be543630381d7c6ccb5ce7465";
    constexpr const char* adapterSha="45d2df1954ce7b02c89c665677af9dad7b24fca21236c5a86a51565db01bbf95";
    constexpr const char* decisionExpectedSha="b02d10705866b62cbf1556cf9d416043db2e90d73b5ca356b042ed263f9b9581";
    constexpr const char* title="Supplemental Fathom example: Cmaj7 E–F–G–E melody only, four equal authored quarter-note slots; source timing unspecified.";
    constexpr const char* version="curriculum-v1-level080-module-a-pass1-r02-supplemental-build-only.1";
    constexpr const char* adapterPath="Content/runtime/level080-module-a-pass1-r02-extension-v1/installed-resource-plan.json";
    constexpr const char* allocationPath="Build/parallel-02/level080-r02-installed-r01/packet/candidate-allocation.json";
    need(decisionSha==decisionExpectedSha&&content::sha256(decisionBytes)==decisionSha,"Level80 exact decision hash differs");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level080-module-a-pass1-r02-supplemental-curriculum-decision.1"&&
         at(decision,"status").string()=="ACCEPTED"&&
         at(decision,"source_review_sha256").string()=="2dfaa0b58b044c2a6546ce0ea43d5ae8b229054a3254af3bae18c7123bc578ed"&&
         at(decision,"native_review_sha256").string()=="0670c940febacaec3ac79bc531243642021cdc6b1021767952cb469c87978d6f"&&
         at(decision,"package_sha256").string()==packageSha&&at(decision,"profile_sha256").string()==profileSha&&
         at(decision,"registry_sha256").string()==registrySha&&at(decision,"resource_adapter_sha256").string()==adapterSha&&
         at(decision,"original_package_sha256").string()==oldPackageSha&&
         at(decision,"original_profile_sha256").string()==oldProfileSha&&
         at(decision,"original_registry_sha256").string()==oldRegistrySha,
         "Level80 source/native/Curriculum authority differs");
    const auto expectedScope=json::parse(R"({"supplemental_worked_example":true,"source_row":"level080/modulea/p003-card01/cmaj7melodyefge","original_source_row_complete":false,"source_queue_exact":false,"source_timing":"unresolved","authored_timing":"four_equal_quarter_slots_q0_to_q4","fixed_authored_bpm":false,"authored_illustrative_bpm":72,"authored_meter":[4,4],"recorded_domain":"Technique/fretboard","item_id":"fg:item:001179","module_id":"fg:module:001179","variant_ids":["fg:variant:007696"],"events":4,"content_revision":1,"whole_workbook":false,"new_official_exercise":false,"automatic_credit":false,"source_task_completion":false,"accuracy_assessment":false,"mastery":false,"supplied_audio":false,"resource_entries":0})");
    need(at(decision,"scope")==expectedScope,"Level80 supplemental no-credit decision scope differs");
    need(content::sha256(input.package)==packageSha&&content::sha256(input.profile)==profileSha&&
         input.expectedProfileSha256==profileSha&&content::sha256(input.registry)==registrySha,
         "Level80 installed package/profile/registry changed");
    auto frozen=[&](const char* path,const char* expected){auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==expected,"Level80 frozen source asset differs");return json::parse(bytes);};
    const auto originalPackage=frozen("Build/guitar-virtuoso/level080/module-a-pass1-r02/native-package.json",oldPackageSha);
    const auto originalProfile=frozen("Build/guitar-virtuoso/level080/module-a-pass1-r02/native-profile.json",oldProfileSha);
    const auto originalRegistry=frozen("Build/guitar-virtuoso/level080/module-a-pass1-r01/identity-registry.json",oldRegistrySha);
    const auto allocation=frozen(allocationPath,allocationSha);
    const auto adapter=frozen(adapterPath,adapterSha);
    need(at(allocation,"records").object().size()==1&&
         at(allocation,"records").object().count("fg:item:001179")==1&&
         at(adapter,"availability").string()=="required_unsupplied"&&
         at(adapter,"resources").array().empty()&&at(adapter,"entry_ids").array().empty()&&
         at(adapter,"original_resource_plan").null(),"Level80 allocation or no-media resource adapter differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    auto expectedPackage=rebind(originalPackage);
    expectedPackage.object()["sources"]=at(originalPackage,"sources");
    expectedPackage.object()["content_version"]=version;
    auto& record=expectedPackage.object().at("records").array().front();record.object()["title"]=title;
    need(package==expectedPackage&&registry==rebind(originalRegistry),
         "Level80 installed source, authored grid, identity or title differs from reviewed R02");
    auto expectedProfile=rebind(originalProfile);
    expectedProfile.object()["reference_package"]=package;
    expectedProfile.object()["reference_registry"]=registry;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"availability\":\"required_unsupplied\",\"entry_ids\":[],\"path\":\"")+adapterPath+"\",\"sha256\":\""+adapterSha+"\"}");
    for(auto& artifact:expectedProfile.object().at("authority_artifacts").array())
        if(at(artifact,"role").string()=="candidate_identity_allocation"){
            artifact.object()["path"]=allocationPath;artifact.object()["sha256"]=allocationSha;
        }
    need(profile==expectedProfile,"Level80 installed profile or source authority differs");
    const auto& selected=at(package,"records").array().front();
    need(at(package,"records").array().size()==1&&at(package,"sources").object().size()==3&&
         at(selected,"id").string()=="fg:item:001179"&&at(selected,"module_id").string()=="fg:module:001179"&&
         at(selected,"workbook_id").string()=="fg:workbook:000080"&&
         at(selected,"timing").object().at("status").string()=="unresolved"&&
         !at(selected,"runtime_eligible").boolean()&&at(selected,"events").array().size()==4&&
         at(selected,"variants").array().size()==1&&
         at(at(selected,"variants").array().front(),"id").string()=="fg:variant:007696",
         "Level80 one-variant unresolved-timing source reference differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==1,
         "Level80 native source reference failed or became admitted");
    const auto& variant=result.variants.front();
    need(variant.id=="fg:variant:007696"&&variant.itemId=="fg:item:001179"&&
         variant.bindingsComplete&&variant.readiness.technicallyRenderable&&
         variant.validation.validReference()&&variant.source.events.size()==4,
         "Level80 single reference variant is foreign or unrenderable");
    const std::array<int,4> frets{0,1,3,0},midi{64,65,67,64};
    for(std::size_t i=0;i<4;++i){const auto& event=variant.source.events[i];
        need(event.id==at(at(selected,"events").array()[i],"event_id").string()&&
             event.span.onset==Rational{static_cast<std::int64_t>(i)}&&event.span.duration==Rational{1}&&
             event.tones.size()==1&&event.tones.front().string==6&&event.tones.front().fret==frets[i]&&
             event.tones.front().midi==midi[i]&&event.tones.front().attack==music::Attack::Picked,
             "Level80 Fathom-authored E-F-G-E contact or quarter slot differs");
    }
    return result;
}
} // namespace fathom::lesson
