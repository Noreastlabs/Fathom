#pragma once
// Exact private-native Db-major Rung05 cell; the separate agent decision grants only narrow runtime Practice.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel013Rung05Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool yes,const char* why){if(!yes)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    constexpr const char* originalRoot="Build/parallel-02/level013-r05-native-candidate-r01/packet/";
    constexpr const char* originalPackageSha="2ea419e516e8dafcb20d34cc2c1d8fe58577bd197ae9d3bc667a68a412f5b2ff";
    constexpr const char* originalProfileSha="d4a0d5589345f75c1be7b8d7ab576d9a18172d6b4921f736b636aa163c95505d";
    constexpr const char* originalRegistrySha="72b59febd7d5bb589af0328e0c67374a0e8df334a7f0480c295c100caa0d82f9";
    constexpr const char* packageSha="86373c0eff8d8e81d7b6c140906625ff9dea49c1d3640895defd537e23537c6f";
    constexpr const char* profileSha="11abf5603da5b13532d97c5b3a0abc6986eebaaa98e85e1990ee4042a8b7e4ce";
    constexpr const char* registrySha=originalRegistrySha;
    constexpr const char* allocationSha="419e93b4e3319d47b56cf7c5cd879c1c011748c024d6303d9dc350bd0bb52885";
    constexpr const char* adapterSha="37f37a400a2ff9b019d3b787405b5bcce528fc3fcf0323c8544c0896ce9971ee";
    constexpr const char* decisionExpectedSha="7a69ad7e4e1181ae40867b43b2e7caa22cf44aa1fde85b3018e7ad59f6b04de6";
    constexpr const char* version="curriculum-v1-level013-rung05-neighboring-cell-build-only.1";
    constexpr const char* adapterPath="Content/runtime/level013-rung05-extension-v1/installed-resource-plan.json";
    constexpr const char* allocationPath="Build/parallel-02/level013-r05-installed-r01/packet/candidate-allocation.json";
    need(decisionSha==decisionExpectedSha&&content::sha256(decisionBytes)==decisionSha,
         "Level13 Rung05 exact agent decision hash differs");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level013-rung05-neighboring-cell-curriculum-decision.1"&&
         at(decision,"status").string()=="ACCEPTED"&&
         at(decision,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner"&&
         at(decision,"source_review_sha256").string()=="d14bb9c8148e3793b3349a0222d02ae07893eebfc8019e411d62b7089140392e"&&
         at(decision,"native_review_sha256").string()=="9a3bf536eb985d0e098e98c2e07437794c21b6dc4743e0aa1eb917748d87b8a2"&&
         at(decision,"package_sha256").string()==packageSha&&
         at(decision,"profile_sha256").string()==profileSha&&
         at(decision,"registry_sha256").string()==registrySha&&
         at(decision,"resource_adapter_sha256").string()==adapterSha&&
         at(decision,"allocation_sha256").string()==allocationSha&&
         at(decision,"original_package_sha256").string()==originalPackageSha&&
         at(decision,"original_profile_sha256").string()==originalProfileSha&&
         at(decision,"original_registry_sha256").string()==originalRegistrySha,
         "Level13 Rung05 source/native/Curriculum authority differs");
    const auto expectedScope=json::parse(R"({"item_id":"fg:item:001184","module_id":"fg:module:001184","variant_ids":["fg:variant:007708","fg:variant:007709"],"event_ids":"fg:item:001184:event:0001..0030","events":30,"source_passages":5,"source_row":"printed:l013:complete-tablature:rung-05-of-13-db-major-root-on-low-e-fret-9-frame-8-11","content_revision":1,"recorded_domain":"Technique/fretboard","source_timing":"source_defined_qualified_neighboring_even_eighths","authored_grid":"nominal_q0_to_q15_even_eighths","fixed_authored_bpm":false,"fixed_authored_meter":false,"intercell_pause_included":false,"tail_pause_included":false,"resource_availability":"required_unsupplied","resource_entries":16,"supplied_media":false,"automatic_credit":false,"accuracy_assessment":false,"rhythm_groove_inferred":false,"mastery":false,"whole_ladder":false,"whole_workbook":false})");
    need(at(decision,"scope")==expectedScope,"Level13 Rung05 one-cell no-credit scope differs");
    need(content::sha256(input.package)==packageSha&&content::sha256(input.profile)==profileSha&&
         input.expectedProfileSha256==profileSha&&content::sha256(input.registry)==registrySha,
         "Level13 Rung05 installed packet differs");
    auto frozen=[&](const std::string& path,const char* hash){const auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==hash,"Level13 Rung05 frozen asset differs");return json::parse(bytes);};
    const auto originalPackage=frozen(std::string(originalRoot)+"package.json",originalPackageSha);
    const auto originalProfile=frozen(std::string(originalRoot)+"expected-profile.json",originalProfileSha);
    const auto originalRegistry=frozen(std::string(originalRoot)+"identity-registry.json",originalRegistrySha);
    const auto allocation=frozen(allocationPath,allocationSha);
    const auto adapter=frozen(adapterPath,adapterSha);
    need(at(allocation,"records").object().size()==1&&at(allocation,"records").object().count("fg:item:001184")==1&&
         at(adapter,"availability").string()=="required_unsupplied"&&
         at(adapter,"resources").array().empty()&&at(adapter,"entry_ids").array().size()==16&&
         at(adapter,"entry_ids")==at(at(originalProfile,"resource_plan"),"entry_ids")&&
         at(adapter,"original_plan_sha256")==at(at(originalProfile,"resource_plan"),"sha256"),
         "Level13 Rung05 exact allocation or unsupplied resource truth differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    auto expectedPackage=originalPackage;expectedPackage.object()["content_version"]=version;
    need(package==expectedPackage&&registry==originalRegistry,
         "Level13 Rung05 source notes, timing, identity or passages differ from reviewed reference");
    auto expectedProfile=originalProfile;
    expectedProfile.object()["reference_package"]=package;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"availability\":\"required_unsupplied\",\"entry_ids\":")+
        json::stringify(at(adapter,"entry_ids")) + ",\"path\":\""+adapterPath+"\",\"sha256\":\""+adapterSha+"\"}");
    for(auto& artifact:expectedProfile.object().at("authority_artifacts").array())
        if(at(artifact,"role").string()=="candidate_identity_allocation"){
            artifact.object()["path"]=allocationPath;artifact.object()["sha256"]=allocationSha;}
    need(profile==expectedProfile,"Level13 Rung05 installed profile or source authority differs");
    const auto& record=at(package,"records").array().front();
    need(at(package,"records").array().size()==1&&at(package,"sources").object().size()==5&&
         at(record,"id").string()=="fg:item:001184"&&at(record,"module_id").string()=="fg:module:001184"&&
         at(record,"workbook_id").string()=="fg:workbook:000013"&&
         at(at(record,"timing"),"status").string()=="source_defined"&&
         !at(record,"runtime_eligible").boolean()&&at(record,"events").array().size()==30&&
         at(record,"variants").array().size()==2,
         "Level13 Rung05 source scope differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
         "Level13 Rung05 native nonadmitted reference failed");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool down=variant.id=="fg:variant:007708";
        need((down||variant.id=="fg:variant:007709")&&seen.insert(variant.id).second&&
             variant.itemId=="fg:item:001184"&&variant.bindingsComplete&&
             variant.readiness.technicallyRenderable&&variant.validation.validReference(),
             "Level13 Rung05 foreign or unrenderable variant");
        auto& model=variant.source;
        need(model.events.size()==30&&model.measures.empty()&&
             model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
             "Level13 Rung05 tuning or event model differs");
        for(std::size_t i=0;i<30;++i){auto& event=model.events[i];const auto& authored=at(record,"events").array()[i];
            const auto q=Rational{static_cast<std::int64_t>(i),2};
            need(event.id==at(authored,"event_id").string()&&event.span.onset==q&&
                 event.span.duration==Rational{1,2}&&event.tones.size()==1&&
                 event.sourceRef=="L13-TXT1-108-119",
                 "Level13 Rung05 event order, nominal timing or source differs");
            event.handDirection=(((i%2==0)==down)?"D":"U");
            const auto& tone=event.tones.front();std::int64_t s{},f{},m{},finger{};
            need(at(authored,"string").integer(s)&&at(authored,"fret").integer(f)&&
                 at(authored,"midi").integer(m)&&at(authored,"finger").integer(finger)&&
                 tone.string==s&&tone.fret==f&&tone.midi==m&&tone.finger==std::to_string(finger)&&
                 tone.attack==music::Attack::Picked&&tone.tieFrom.empty(),
                 "Level13 Rung05 printed contact differs");
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference(),"Level13 Rung05 D/U model projection invalid");
    }
    need(seen==std::set<std::string>{"fg:variant:007708","fg:variant:007709"},
         "Level13 Rung05 D/U coverage differs");
    return result;
}
} // namespace fathom::lesson
