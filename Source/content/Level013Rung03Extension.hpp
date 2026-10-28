#pragma once
// Exact private-native B-major Rung03 cell; the separate agent decision grants only narrow runtime Practice.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel013Rung03Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool yes,const char* why){if(!yes)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    constexpr const char* originalRoot="Build/level-oracle/exercise-implementation-r01/level013-rung03-rational-r02/producer-r02/";
    constexpr const char* originalPackageSha="f61ca4a78a03f8e71c308f0c945e692b564b9ee443a6c56af294332bc32e9905";
    constexpr const char* originalProfileSha="b3a8edfebd1a10cb4ba9337adb4f1f715d516be105c5b672fba467ae80289b21";
    constexpr const char* originalRegistrySha="e6649e66247b7aab8732899cd8f7d0665c87e5ff751273af5b51ef00a02e2e73";
    constexpr const char* packageSha="dc4b229ea2c90bdfd0a09421c43d9b2a847bceb892afdb9d55a84e1271dc2231";
    constexpr const char* profileSha="3620b0053e77a5556cca28cabccbd948390b4fce06fbe2cd07ade9e71813815b";
    constexpr const char* registrySha=originalRegistrySha;
    constexpr const char* allocationSha="8a90232bab6438a4e427322d341c23a259aefaab4c16636b5559893562379ff6";
    constexpr const char* adapterSha="37f37a400a2ff9b019d3b787405b5bcce528fc3fcf0323c8544c0896ce9971ee";
    constexpr const char* decisionExpectedSha="3e2f57cd1ec20b8576e8e22dc67cb59568732f90d982108abd809d601d1d2bbf";
    constexpr const char* version="curriculum-v1-level013-rung03-neighboring-cell-build-only.1";
    constexpr const char* adapterPath="Content/runtime/level013-rung03-extension-v1/installed-resource-plan.json";
    constexpr const char* allocationPath="Build/parallel-02/level013-r03-installed-r01/packet/candidate-allocation.json";
    need(decisionSha==decisionExpectedSha&&content::sha256(decisionBytes)==decisionSha,
         "Level13 Rung03 exact agent decision hash differs");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level013-rung03-neighboring-cell-curriculum-decision.1"&&
         at(decision,"status").string()=="ACCEPTED"&&
         at(decision,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner"&&
         at(decision,"source_review_sha256").string()=="1500cee3d5467f1f2bc27b3667543922100ac836d2a4915a7ec7518f3eea029f"&&
         at(decision,"rational_contract_review_sha256").string()=="46c1741833a877e22f8365ad120ddd76a71d7e60004dc73d842dd5c1043dd1d6"&&
         at(decision,"native_review_sha256").string()=="27ca2fbd269deaf78b2b905188531e25a2f65eac8e69d4b15540f6b88d4accd2"&&
         at(decision,"package_sha256").string()==packageSha&&
         at(decision,"profile_sha256").string()==profileSha&&
         at(decision,"registry_sha256").string()==registrySha&&
         at(decision,"resource_adapter_sha256").string()==adapterSha&&
         at(decision,"allocation_sha256").string()==allocationSha&&
         at(decision,"original_package_sha256").string()==originalPackageSha&&
         at(decision,"original_profile_sha256").string()==originalProfileSha&&
         at(decision,"original_registry_sha256").string()==originalRegistrySha,
         "Level13 Rung03 source/native/Curriculum authority differs");
    const auto expectedScope=json::parse(R"({"item_id":"fg:item:001130","module_id":"fg:module:001130","variant_ids":["fg:variant:007382","fg:variant:007383"],"event_ids":"fg:item:001130:event:0001..0030","events":30,"source_passages":5,"source_row":"printed:l013:complete-tablature:rung-03-of-13-b-major-root-on-low-e-fret-7-frame-6-9","content_revision":1,"recorded_domain":"Technique/fretboard","source_timing":"source_defined_qualified_neighboring_even_eighths","authored_grid":"nominal_q0_to_q15_even_eighths","fixed_authored_bpm":false,"fixed_authored_meter":false,"intercell_pause_included":false,"tail_pause_included":false,"resource_availability":"required_unsupplied","resource_entries":16,"supplied_media":false,"automatic_credit":false,"accuracy_assessment":false,"rhythm_groove_inferred":false,"mastery":false,"whole_ladder":false,"whole_workbook":false})");
    need(at(decision,"scope")==expectedScope,"Level13 Rung03 one-cell no-credit scope differs");
    need(content::sha256(input.package)==packageSha&&content::sha256(input.profile)==profileSha&&
         input.expectedProfileSha256==profileSha&&content::sha256(input.registry)==registrySha,
         "Level13 Rung03 installed packet differs");
    auto frozen=[&](const std::string& path,const char* hash){const auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==hash,"Level13 Rung03 frozen asset differs");return json::parse(bytes);};
    const auto originalPackage=frozen(std::string(originalRoot)+"package.json",originalPackageSha);
    const auto originalProfile=frozen(std::string(originalRoot)+"expected-profile.json",originalProfileSha);
    const auto originalRegistry=frozen(std::string(originalRoot)+"identity-registry.json",originalRegistrySha);
    const auto allocation=frozen(allocationPath,allocationSha);
    const auto adapter=frozen(adapterPath,adapterSha);
    need(at(allocation,"records").object().size()==1&&at(allocation,"records").object().count("fg:item:001130")==1&&
         at(adapter,"availability").string()=="required_unsupplied"&&
         at(adapter,"resources").array().empty()&&at(adapter,"entry_ids").array().size()==16&&
         at(adapter,"entry_ids")==at(at(originalProfile,"resource_plan"),"entry_ids")&&
         at(adapter,"original_plan_sha256")==at(at(originalProfile,"resource_plan"),"sha256"),
         "Level13 Rung03 exact allocation or unsupplied resource truth differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    auto expectedPackage=originalPackage;expectedPackage.object()["content_version"]=version;
    need(package==expectedPackage&&registry==originalRegistry,
         "Level13 Rung03 source notes, timing, identity or passages differ from reviewed reference");
    auto expectedProfile=originalProfile;
    expectedProfile.object()["reference_package"]=package;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"availability\":\"required_unsupplied\",\"entry_ids\":")+
        json::stringify(at(adapter,"entry_ids")) + ",\"path\":\""+adapterPath+"\",\"sha256\":\""+adapterSha+"\"}");
    for(auto& artifact:expectedProfile.object().at("authority_artifacts").array())
        if(at(artifact,"role").string()=="candidate_identity_allocation"){
            artifact.object()["path"]=allocationPath;artifact.object()["sha256"]=allocationSha;}
    need(profile==expectedProfile,"Level13 Rung03 installed profile or source authority differs");
    const auto& record=at(package,"records").array().front();
    need(at(package,"records").array().size()==1&&at(package,"sources").object().size()==5&&
         at(record,"id").string()=="fg:item:001130"&&at(record,"module_id").string()=="fg:module:001130"&&
         at(record,"workbook_id").string()=="fg:workbook:000013"&&
         at(at(record,"timing"),"status").string()=="source_defined"&&
         !at(record,"runtime_eligible").boolean()&&at(record,"events").array().size()==30&&
         at(record,"variants").array().size()==2,
         "Level13 Rung03 source scope differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
         "Level13 Rung03 native nonadmitted reference failed");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool down=variant.id=="fg:variant:007382";
        need((down||variant.id=="fg:variant:007383")&&seen.insert(variant.id).second&&
             variant.itemId=="fg:item:001130"&&variant.bindingsComplete&&
             variant.readiness.technicallyRenderable&&variant.validation.validReference(),
             "Level13 Rung03 foreign or unrenderable variant");
        auto& model=variant.source;
        need(model.events.size()==30&&model.measures.empty()&&
             model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
             "Level13 Rung03 tuning or event model differs");
        for(std::size_t i=0;i<30;++i){auto& event=model.events[i];const auto& authored=at(record,"events").array()[i];
            const auto q=Rational{static_cast<std::int64_t>(i),2};
            need(event.id==at(authored,"event_id").string()&&event.span.onset==q&&
                 event.span.duration==Rational{1,2}&&event.tones.size()==1&&
                 event.sourceRef=="L13-TXT1-80-91",
                 "Level13 Rung03 event order, nominal timing or source differs");
            event.handDirection=(((i%2==0)==down)?"D":"U");
            const auto& tone=event.tones.front();std::int64_t s{},f{},m{},finger{};
            need(at(authored,"string").integer(s)&&at(authored,"fret").integer(f)&&
                 at(authored,"midi").integer(m)&&at(authored,"finger").integer(finger)&&
                 tone.string==s&&tone.fret==f&&tone.midi==m&&tone.finger==std::to_string(finger)&&
                 tone.attack==music::Attack::Picked&&tone.tieFrom.empty(),
                 "Level13 Rung03 printed contact differs");
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference(),"Level13 Rung03 D/U model projection invalid");
    }
    need(seen==std::set<std::string>{"fg:variant:007382","fg:variant:007383"},
         "Level13 Rung03 D/U coverage differs");
    return result;
}
} // namespace fathom::lesson
