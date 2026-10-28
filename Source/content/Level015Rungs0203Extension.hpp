#pragma once
// Two reviewed Level15 standalone cells, each with a separate explicit-Save Curriculum decision.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel015Rungs0203Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool yes,const char* why){if(!yes)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    constexpr const char* nativeRoot="Build/parallel-02/level015-r02-r03-canonical-native-r01/run-r01/combined/";
    constexpr const char* nativePackageSha="06664715e244183a3b8d76eff4c16705f9f9256815abe1ddc4a5d1304d15a9fd";
    constexpr const char* nativeProfileSha="0e14aea6009ab20a3c5703e307caece153d5533711d53226e5c8252668eb1f48";
    constexpr const char* nativeRegistrySha="3bea886d3bd11160f16eeea45f780f0c63d7249b84cbc523e2be7ca1990f9f92";
    constexpr const char* allocationSha="ee00c92cf7f5b488ce78396fcd96b0cdf27201609e792c3beb3d370b855601fd";
    constexpr const char* profileSha="da69d066f491b542aab085a594a20208f6e3db8bd10e3bef4c30fa451485b8a4";
    constexpr const char* adapterSha="eed6d3007f436de50a330eb35495ff50b457952140601f9a84dec850e4aa9af4";
    constexpr const char* decisionExpectedSha="5dfbfbf9f9d5da0b2f24a9f56071fb1ea9679f8741919f0fa9d1de13a44798a7";
    constexpr const char* adapterPath="Content/runtime/level015-rungs02-03-extension-v1/installed-resource-plan.json";
    need(decisionSha==decisionExpectedSha&&content::sha256(decisionBytes)==decisionSha,
         "Level15 Rungs02-03 exact decision hash differs");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level015-rungs02-03-triplet-curriculum-decision.1"&&
         at(decision,"status").string()=="ACCEPTED_FOR_INSTALLED_PRODUCER_CANDIDATE"&&
         at(decision,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner"&&
         at(decision,"source_review_sha256").string()=="621f0915913c8685c396c300998bbffe838cdf64d275e7d817c7d7d2b1bc7937"&&
         at(decision,"native_review_sha256").string()=="4b58ef6f3716790f1aa44d090476ea784aef2bcb5f07cd7b7b892eeb47e747ba"&&
         at(decision,"root_adoption_sha256").string()=="4e2cc0c22b70fdf3f9e50701fee0706f58c1af5cc37eaf842edebb68fa537ef6"&&
         at(decision,"manager_release_sha256").string()=="8014979875d114a744120e419440bdaf9d46eaaeda48e748ecec1c7a593775ad"&&
         at(decision,"locator_review_sha256").string()=="945f75e0b3d7c52b9da370c43491bb02f173bd0b48d0e0ad9d2e34011c3f8961"&&
         at(decision,"package_sha256").string()==nativePackageSha&&
         at(decision,"profile_sha256").string()==profileSha&&
         at(decision,"registry_sha256").string()==nativeRegistrySha&&
         at(decision,"resource_adapter_sha256").string()==adapterSha&&
         at(decision,"allocation_sha256").string()==allocationSha&&
         at(decision,"source_timing").string()=="source_defined_eighth_triplets_one_group_per_beat"&&
         at(decision,"resource_availability").string()=="required_unsupplied",
         "Level15 Rungs02-03 source/native/Curriculum authority differs");
    std::int64_t resourceCount{};
    need(at(decision,"resource_entries").integer(resourceCount)&&resourceCount==16&&
         at(decision,"supplied_resources")==J::fromInteger(0)&&
         !at(decision,"runtime_eligible_in_native_packet").boolean(),
         "Level15 Rungs02-03 unsupplied resource decision differs");
    const auto expectedCases=json::parse(R"([{"case":"rung02","decision_path":"rung02-agent-curriculum-decision.md","decision_sha256":"41859b28c4d2fde1f72b40552aa85ea078c7d7a737a56ae21e0c7ec32fe06586","item_id":"fg:item:001181","module_id":"fg:module:001181","variant_ids":["fg:variant:007702","fg:variant:007703"],"event_count":78,"source_row":"printed:l015:complete-tablature:rung-02-of-13-bb-major-root-on-low-e-fret-6-frame-5-8","pdf_physical_page_index":2,"txt_ref":"L15-TXT1-94-115","recorded_domain":"Technique/fretboard","explicit_save_only":true,"automatic_credit":false,"fixed_bpm":false,"whole_workbook":false},{"case":"rung03","decision_path":"rung03-agent-curriculum-decision.md","decision_sha256":"24c4b1a19f03c0feae8704c0867be36b05bd12cec34b58d7a822c6c5ce91e79c","item_id":"fg:item:001182","module_id":"fg:module:001182","variant_ids":["fg:variant:007704","fg:variant:007705"],"event_count":78,"source_row":"printed:l015:complete-tablature:rung-03-of-13-b-major-root-on-low-e-fret-7-frame-6-9","pdf_physical_page_index":3,"txt_ref":"L15-TXT1-118-139","recorded_domain":"Technique/fretboard","explicit_save_only":true,"automatic_credit":false,"fixed_bpm":false,"whole_workbook":false}])");
    need(at(decision,"cases")==expectedCases,"Level15 case-bound Curriculum decision differs");
    for(const auto& entry:at(decision,"cases").array()){
        const auto path=at(entry,"decision_path").string();
        content::verifyArchivedEvidence(input,path,at(entry,"decision_sha256").string());
    }
    need(content::sha256(input.package)==nativePackageSha&&content::sha256(input.registry)==nativeRegistrySha&&
         content::sha256(input.profile)==profileSha&&input.expectedProfileSha256==profileSha,
         "Level15 installed two-case packet differs");
    auto frozen=[&](const std::string& path,const char* hash){const auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==hash,"Level15 frozen asset differs");return json::parse(bytes);};
    const auto nativePackage=frozen(std::string(nativeRoot)+"package.json",nativePackageSha);
    const auto nativeProfile=frozen(std::string(nativeRoot)+"expected-profile.json",nativeProfileSha);
    const auto nativeRegistry=frozen(std::string(nativeRoot)+"identity-registry.json",nativeRegistrySha);
    const auto allocation=frozen(std::string(nativeRoot)+"candidate-allocation.json",allocationSha);
    const auto adapter=frozen(adapterPath,adapterSha);
    need(at(allocation,"records").object().size()==2&&
         at(allocation,"records").object().count("fg:item:001181")==1&&
         at(allocation,"records").object().count("fg:item:001182")==1&&
         at(adapter,"availability").string()=="required_unsupplied"&&
         at(adapter,"resources").array().empty()&&at(adapter,"entry_ids").array().size()==16&&
         at(adapter,"entry_ids")==at(at(nativeProfile,"resource_plan"),"entry_ids")&&
         at(adapter,"original_plan_sha256")==at(at(nativeProfile,"resource_plan"),"sha256"),
         "Level15 allocation or unsupplied resource truth differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    need(package==nativePackage&&registry==nativeRegistry&&
         at(package,"content_version").string()=="curriculum-v1-level015-rungs02-03-triplet-build-only.1"&&
         at(package,"sources").object().size()==7,
         "Level15 contacts, timing, identities or passages differ from reviewed reference");
    auto expectedProfile=nativeProfile;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"availability\":\"required_unsupplied\",\"entry_ids\":")+
        json::stringify(at(adapter,"entry_ids")) + ",\"path\":\""+adapterPath+"\",\"sha256\":\""+adapterSha+"\"}");
    need(profile==expectedProfile,"Level15 installed profile or source authority differs");
    const auto& records=at(package,"records").array();
    need(records.size()==2,"Level15 two separate selected records required");
    const std::array<const char*,2> items{"fg:item:001181","fg:item:001182"};
    const std::array<const char*,2> modules{"fg:module:001181","fg:module:001182"};
    const std::array<const char*,2> sourceRefs{"L15-TXT1-94-115","L15-TXT1-118-139"};
    for(std::size_t k=0;k<2;++k){
        const auto& rec=records[k];
        need(at(rec,"id").string()==items[k]&&at(rec,"module_id").string()==modules[k]&&
             at(rec,"workbook_id").string()=="fg:workbook:000015"&&
             at(at(rec,"timing"),"status").string()=="source_defined"&&
             !at(rec,"runtime_eligible").boolean()&&at(rec,"events").array().size()==78&&
             at(rec,"variants").array().size()==2,
             "Level15 case identity or source timing differs");
    }
    auto result=content::validate(input);
    if(!(result.validReference&&result.exitCode==2&&result.records.size()==2&&result.variants.size()==4))
        throw std::runtime_error("Level15 two-case native reference failed exit="+std::to_string(result.exitCode)+
            " valid="+std::to_string(result.validReference)+" records="+std::to_string(result.records.size())+
            " variants="+std::to_string(result.variants.size())+" issues="+json::stringify(at(result.report,"issues")).substr(0,1800));
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool r02=variant.itemId==items[0],r03=variant.itemId==items[1];
        const bool down=variant.id=="fg:variant:007702"||variant.id=="fg:variant:007704";
        need((r02||r03)&&seen.insert(variant.id).second&&variant.bindingsComplete&&
             variant.readiness.technicallyRenderable&&variant.validation.validReference(),
             "Level15 selected variant unavailable, foreign or duplicated");
        const std::size_t k=r02?0:1;
        need((r02&&(variant.id=="fg:variant:007702"||variant.id=="fg:variant:007703"))||
             (r03&&(variant.id=="fg:variant:007704"||variant.id=="fg:variant:007705")),
             "Level15 cross-case variant differs");
        auto& model=variant.source;
        need(model.events.size()==78&&model.measures.empty()&&
             model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
             "Level15 tuning or event model differs");
        for(std::size_t i=0;i<78;++i){auto& event=model.events[i];const auto& authored=at(records[k],"events").array()[i];
            std::int64_t string{},fret{},midi{},finger{};
            need(event.id==at(authored,"event_id").string()&&
                 event.span.onset==Rational{static_cast<std::int64_t>(i),3}&&
                 event.span.duration==Rational{1,3}&&event.tones.size()==1&&
                 event.sourceRef==sourceRefs[k]&&
                 at(authored,"string").integer(string)&&at(authored,"fret").integer(fret)&&
                 at(authored,"midi").integer(midi)&&at(authored,"finger").integer(finger)&&
                 event.tones.front().string==string&&event.tones.front().fret==fret&&
                 event.tones.front().midi==midi&&event.tones.front().finger==std::to_string(finger)&&
                 event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),
                 "Level15 printed contact, source or q-third differs");
            event.handDirection=(((i%2==0)==down)?"D":"U");
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference(),"Level15 D/U projected model invalid");
    }
    need(seen==std::set<std::string>{"fg:variant:007702","fg:variant:007703",
                                      "fg:variant:007704","fg:variant:007705"},
         "Level15 four D/U variants differ");
    return result;
}
} // namespace fathom::lesson
