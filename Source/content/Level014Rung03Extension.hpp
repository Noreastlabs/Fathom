#pragma once
// One source-reviewed Level14 B-major Rung03 cell; a separate agent decision grants narrow runtime Practice.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel014Rung03Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool yes,const char* why){if(!yes)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    constexpr const char* nativeRoot="Build/parallel-02/level014-r03-canonical-native-r01/run-r01/";
    constexpr const char* nativePackageSha="d498dac23f30d0e5a5502bd44017b2af9bd21012890983c2ebc54375362c0841";
    constexpr const char* nativeProfileSha="46149c196a6b9b470585b3fa0abca881382a0b2ed9630e85dce5ba5e955e9915";
    constexpr const char* nativeRegistrySha="f19a21ced38907291550497b04c075a894f70a92ac67fd90bcb5875780fc37ed";
    constexpr const char* packageSha=nativePackageSha;
    constexpr const char* profileSha="311713a3503eec26e208e796d85d1e1c7b97fa37184915d33609ec8ae7a367d4";
    constexpr const char* registrySha=nativeRegistrySha;
    constexpr const char* allocationSha="2a4db1fe3d82e4deaea0859a622e849c2ae70951b1337547c147ceb677581e7a";
    constexpr const char* adapterSha="37f37a400a2ff9b019d3b787405b5bcce528fc3fcf0323c8544c0896ce9971ee";
    constexpr const char* decisionExpectedSha="970e4eed3b3d5a7959b277ca7ac3db99662d38ddc0d7e63d05e640508742ca6e";
    constexpr const char* version="curriculum-v1-level014-rung03-triplet-build-only.1";
    constexpr const char* adapterPath="Content/runtime/level014-rung03-extension-v1/installed-resource-plan.json";
    constexpr const char* allocationPath="Build/parallel-02/level014-r03-canonical-native-r01/run-r01/candidate-allocation.json";
    need(decisionSha==decisionExpectedSha&&content::sha256(decisionBytes)==decisionSha,
         "Level14 Rung03 exact agent decision hash differs");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level014-rung03-triplet-curriculum-decision.1"&&
         at(decision,"status").string()=="ACCEPTED"&&
         at(decision,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner"&&
         at(decision,"source_review_sha256").string()=="b511bd0b41d3bb7db8e48bc14a6a6d1c62e9a3f95ada5cc17483a115ace32bf2"&&
         at(decision,"native_review_sha256").string()=="e002b2da98a993c9a8a8f27cd50ac7b417362ac8039c034a9fe011cf100029c8"&&
         at(decision,"manager_release_sha256").string()=="a0e5125b12c91ec03afa5f03e479624e6ee90ef83b114f2854ab561eb78eea21"&&
         at(decision,"package_sha256").string()==packageSha&&
         at(decision,"profile_sha256").string()==profileSha&&
         at(decision,"registry_sha256").string()==registrySha&&
         at(decision,"resource_adapter_sha256").string()==adapterSha&&
         at(decision,"allocation_sha256").string()==allocationSha&&
         at(decision,"native_package_sha256").string()==nativePackageSha&&
         at(decision,"native_profile_sha256").string()==nativeProfileSha&&
         at(decision,"native_registry_sha256").string()==nativeRegistrySha,
         "Level14 Rung03 source/native/Curriculum authority differs");
    const auto expectedScope=json::parse(R"({"item_id":"fg:item:001180","module_id":"fg:module:001180","variant_ids":["fg:variant:007698","fg:variant:007699"],"event_ids":"fg:item:001180:event:0001..0036","events":36,"source_passages":13,"source_row":"printed:l014:complete-tablature:rung-03-of-13-b-major-root-on-low-e-fret-7-frame-6-9","content_revision":1,"recorded_domain":"Technique/fretboard","source_timing":"source_defined_eighth_triplets_one_group_per_beat","authored_grid":"nominal_q0_to_q12_triplets","fixed_authored_bpm":false,"fixed_authored_meter":false,"intercell_pause_included":false,"tail_pause_included":false,"resource_availability":"required_unsupplied","resource_entries":16,"supplied_media":false,"automatic_credit":false,"accuracy_assessment":false,"rhythm_groove_inferred":false,"mastery":false,"whole_ladder":false,"whole_workbook":false})");
    need(at(decision,"scope")==expectedScope,"Level14 Rung03 one-cell no-credit scope differs");
    need(content::sha256(input.package)==packageSha&&content::sha256(input.profile)==profileSha&&
         input.expectedProfileSha256==profileSha&&content::sha256(input.registry)==registrySha,
         "Level14 Rung03 installed packet differs");
    auto frozen=[&](const std::string& path,const char* hash){const auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==hash,"Level14 Rung03 frozen asset differs");return json::parse(bytes);};
    const auto nativePackage=frozen(std::string(nativeRoot)+"package.json",nativePackageSha);
    const auto nativeProfile=frozen(std::string(nativeRoot)+"expected-profile.json",nativeProfileSha);
    const auto nativeRegistry=frozen(std::string(nativeRoot)+"identity-registry.json",nativeRegistrySha);
    const auto allocation=frozen(allocationPath,allocationSha);
    const auto adapter=frozen(adapterPath,adapterSha);
    need(at(allocation,"records").object().size()==1&&at(allocation,"records").object().count("fg:item:001180")==1&&
         at(adapter,"availability").string()=="required_unsupplied"&&
         at(adapter,"resources").array().empty()&&at(adapter,"entry_ids").array().size()==16&&
         at(adapter,"entry_ids")==at(at(nativeProfile,"resource_plan"),"entry_ids")&&
         at(adapter,"original_plan_sha256")==at(at(nativeProfile,"resource_plan"),"sha256"),
         "Level14 Rung03 exact allocation or unsupplied resource truth differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    need(package==nativePackage&&registry==nativeRegistry&&at(package,"content_version").string()==version,
         "Level14 Rung03 source contacts, timing, identities or passages differ from reviewed native reference");
    auto expectedProfile=nativeProfile;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"availability\":\"required_unsupplied\",\"entry_ids\":")+
        json::stringify(at(adapter,"entry_ids")) + ",\"path\":\""+adapterPath+"\",\"sha256\":\""+adapterSha+"\"}");
    need(profile==expectedProfile,"Level14 Rung03 installed profile or source authority differs");
    const auto& record=at(package,"records").array().front();
    need(at(package,"records").array().size()==1&&at(package,"sources").object().size()==13&&
         at(record,"id").string()=="fg:item:001180"&&at(record,"module_id").string()=="fg:module:001180"&&
         at(record,"workbook_id").string()=="fg:workbook:000014"&&
         at(at(record,"timing"),"status").string()=="source_defined"&&
         !at(record,"runtime_eligible").boolean()&&at(record,"events").array().size()==36&&
         at(record,"variants").array().size()==2,
         "Level14 Rung03 source scope differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
         "Level14 Rung03 native nonadmitted reference failed");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool down=variant.id=="fg:variant:007698";
        need((down||variant.id=="fg:variant:007699")&&seen.insert(variant.id).second&&
             variant.itemId=="fg:item:001180"&&variant.bindingsComplete&&
             variant.readiness.technicallyRenderable&&variant.validation.validReference(),
             "Level14 Rung03 foreign or unrenderable variant");
        auto& model=variant.source;
        need(model.events.size()==36&&model.measures.empty()&&
             model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
             "Level14 Rung03 tuning or event model differs");
        for(std::size_t i=0;i<36;++i){auto& event=model.events[i];const auto& authored=at(record,"events").array()[i];
            const auto q=Rational{static_cast<std::int64_t>(i),3};
            need(event.id==at(authored,"event_id").string()&&event.span.onset==q&&
                 event.span.duration==Rational{1,3}&&event.tones.size()==1&&
                 event.sourceRef=="L14-TXT1-84-95",
                 "Level14 Rung03 event order, nominal timing or source differs");
            event.handDirection=(((i%2==0)==down)?"D":"U");
            const auto& tone=event.tones.front();std::int64_t s{},f{},m{},finger{};
            need(at(authored,"string").integer(s)&&at(authored,"fret").integer(f)&&
                 at(authored,"midi").integer(m)&&at(authored,"finger").integer(finger)&&
                 tone.string==s&&tone.fret==f&&tone.midi==m&&tone.finger==std::to_string(finger)&&
                 tone.attack==music::Attack::Picked&&tone.tieFrom.empty(),
                 "Level14 Rung03 printed contact differs");
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference(),"Level14 Rung03 D/U model projection invalid");
    }
    need(seen==std::set<std::string>{"fg:variant:007698","fg:variant:007699"},
         "Level14 Rung03 D/U coverage differs");
    return result;
}
} // namespace fathom::lesson
