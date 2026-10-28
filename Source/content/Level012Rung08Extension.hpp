#pragma once
// One exact source-reviewed Rung08 cell; native validity is separate from runtime admission.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel012Rung08Extension(const content::Input& input,
    const std::string& decisionBytes, const std::string& decisionSha,
    const std::string&) {
    using J = json::Value;
    auto need=[](bool yes,const char* why){if(!yes)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    auto number=[&](const J& value){std::int64_t n{};need(value.integer(n),"Rung08 integer differs");return n;};
    auto replace=[](std::string text,const std::string& from,const std::string& to){
        std::size_t pos=0;while((pos=text.find(from,pos))!=std::string::npos){text.replace(pos,from.size(),to);pos+=to.size();}return text;};
    auto rebound=[&](const J& value){auto bytes=json::stringify(value);
        bytes=replace(bytes,"fg:module:990008","fg:module:001178");
        bytes=replace(bytes,"fg:item:990008","fg:item:001178");
        bytes=replace(bytes,"fg:variant:9900081","fg:variant:007694");
        bytes=replace(bytes,"fg:variant:9900082","fg:variant:007695");
        return json::parse(bytes);};
    constexpr const char* sourcePackageSha="ba630bedbcec2755c62ef8666850ce2c19dc4cb2d7759a8edaa90f8eb177e123";
    constexpr const char* sourceProfileSha="477a9c58c1148f21d1d7864a6f0cfb5c068623fc09d0f79df04458cafff0192e";
    constexpr const char* sourceRegistrySha="fd4e905d0f436f2817689bd28dd83e5f64b77b0c2eb5b33e63633bff800cd6fe";
    constexpr const char* packageSha="ccc58d75f0eb0c7c5e2e556cdb6e13a9ddc835f10fc606ae740f56970ae9f8b2";
    constexpr const char* profileSha="02d5f00f9874014e56a670907331c51bb501973309452146480db0c6a5913f3d";
    constexpr const char* registrySha="c1d1a34a0eb27e5ef393001f3ef57e2fdd73fe7d1b6d7a7c6a4f2cae63ed04dd";
    constexpr const char* adapterSha="46c3eae8c870630ccc7e2d1bb522c08cf3b8daa4755994a7e64002913161f287";
    constexpr const char* sourceRoot="Build/level-oracle/exercise-implementation-r01/level012-rung08-portable-r01/producer-r01/";
    need(decisionSha.size()==64&&content::sha256(decisionBytes)==decisionSha,"Rung08 runtime decision hash differs");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level012-rung08-first-cell-curriculum-decision.1"&&
         at(decision,"status").string()=="ACCEPTED"&&
         at(decision,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner"&&
         at(decision,"source_review_sha256").string()=="5ee18730afaa8b8a0a8dc503c30296720e16bd4aea204e99ecc40395b8109b79"&&
         at(decision,"native_review_sha256").string()=="d29aeb28dae148fc50d0d5d26caa9b9b6c13e1edc7a3ae944fba7431ccdcb66d",
         "Rung08 exact agent/source/native decision authority differs");
    need(at(decision,"package_sha256").string()==packageSha&&
         at(decision,"profile_sha256").string()==profileSha&&
         at(decision,"registry_sha256").string()==registrySha&&
         at(decision,"resource_adapter_sha256").string()==adapterSha&&
         at(decision,"original_package_sha256").string()==sourcePackageSha&&
         at(decision,"original_profile_sha256").string()==sourceProfileSha&&
         at(decision,"original_registry_sha256").string()==sourceRegistrySha,
         "Rung08 decision packet or provenance differs");
    need(content::sha256(input.package)==packageSha&&content::sha256(input.profile)==profileSha&&
         input.expectedProfileSha256==profileSha&&content::sha256(input.registry)==registrySha,
         "Rung08 canonical package/profile/registry changed");
    const auto scope=json::parse(R"({"automatic_credit":false,"content_revision":1,"events":16,"fixed_authored_bpm":false,"intercell_pause_included":false,"item_id":"fg:item:001178","mastery":false,"module_id":"fg:module:001178","recorded_domain":"Technique/fretboard","required_unsupplied_resource_entry_count":16,"resource_availability":"required_unsupplied","rhythm_groove_inferred":false,"source_timing":"even_eighths","span_q":8,"variant_ids":["fg:variant:007694","fg:variant:007695"],"whole_ladder":false,"whole_workbook":false})");
    need(at(decision,"scope")==scope,"Rung08 one-case no-credit scope differs");
    auto sourceFile=[&](const char* name,const char* expectedSha){
        const auto bytes=content::readBounded(input.sourceRoot/(std::string(sourceRoot)+name),32*1024*1024);
        need(content::sha256(bytes)==expectedSha,"Rung08 frozen Oracle asset differs");return json::parse(bytes);};
    const auto originalPackage=sourceFile("package.json",sourcePackageSha);
    const auto originalProfile=sourceFile("expected-profile.json",sourceProfileSha);
    const auto originalRegistry=sourceFile("identity-registry.json",sourceRegistrySha);
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    auto expectedPackage=rebound(originalPackage);
    expectedPackage.object()["content_version"]="curriculum-v1-level012-rung08-first-cell-build-only.1";
    need(package==expectedPackage&&registry==rebound(originalRegistry),
         "Rung08 canonical notes, timing, source or identities differ from reviewed Oracle reference");
    need(at(profile,"reference_package")==package&&at(profile,"reference_registry")==registry&&
         at(profile,"event_sources")==at(rebound(originalProfile),"event_sources")&&
         at(profile,"degree_roots")==at(rebound(originalProfile),"degree_roots"),
         "Rung08 installed profile source projection differs");
    const auto adapterPath="Content/runtime/level012-rung08-extension-v1/installed-resource-plan.json";
    const auto adapterBytes=content::readBounded(input.sourceRoot/adapterPath,1024*1024);
    const auto adapter=json::parse(adapterBytes);
    need(content::sha256(adapterBytes)==adapterSha&&at(adapter,"availability").string()=="required_unsupplied"&&
         at(adapter,"resources").array().empty()&&at(adapter,"entry_ids")==at(at(originalProfile,"resource_plan"),"entry_ids")&&
         at(adapter,"entry_ids").array().size()==16&&
         at(adapter,"original_plan_sha256")==at(at(originalProfile,"resource_plan"),"sha256")&&
         at(profile,"resource_plan")==json::parse(std::string("{\"availability\":\"required_unsupplied\",\"entry_ids\":")+
             json::stringify(at(adapter,"entry_ids"))+",\"path\":\""+adapterPath+"\",\"sha256\":\""+adapterSha+"\"}"),
         "Rung08 unsupplied resource truth differs");
    const auto& record=at(package,"records").array().front();
    need(at(package,"records").array().size()==1&&at(package,"sources").object().size()==7&&
         at(record,"id").string()=="fg:item:001178"&&at(record,"module_id").string()=="fg:module:001178"&&
         at(record,"workbook_id").string()=="fg:workbook:000012"&&
         at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
         at(record,"events").array().size()==16&&at(record,"variants").array().size()==2,
         "Rung08 one-case source reference differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
         "Rung08 native nonadmitted reference failed");
    const std::array<int,16> strings{1,1,2,2,2,3,3,3,3,3,3,2,2,2,1,1};
    const std::array<int,16> frets{12,14,11,12,14,11,13,14,14,13,11,14,12,11,14,12};
    const std::array<int,16> fingers{2,4,1,2,4,1,3,4,4,3,1,4,2,1,4,2};
    const std::array<int,16> midi{52,54,56,57,59,61,63,64,64,63,61,59,57,56,54,52};
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool down=variant.id=="fg:variant:007694";
        need((down||variant.id=="fg:variant:007695")&&seen.insert(variant.id).second&&
             variant.itemId=="fg:item:001178"&&variant.bindingsComplete&&
             variant.readiness.technicallyRenderable&&variant.validation.validReference(),
             "Rung08 foreign or unavailable variant");
        auto& model=variant.source;
        need(model.events.size()==16&&model.measures.empty()&&model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&
             model.instrument.capo==0,"Rung08 model or standard tuning differs");
        for(std::size_t i=0;i<16;++i){auto& event=model.events[i];
            const auto& authored=at(record,"events").array()[i];
            need(event.id==at(authored,"event_id").string()&&event.kind==music::Kind::Note&&
                 event.span.onset==Rational{static_cast<std::int64_t>(i),2}&&
                 event.span.duration==Rational{1,2}&&event.tones.size()==1&&
                 event.sourceRef=="L12-TXT1-140-151", "Rung08 event identity, timing or source differs");
            const auto& tone=event.tones.front();
            need(tone.string==strings[i]&&tone.fret==frets[i]&&tone.midi==midi[i]&&
                 tone.finger==std::to_string(fingers[i])&&
                 tone.string==number(at(authored,"string"))&&tone.fret==number(at(authored,"fret"))&&
                 tone.midi==number(at(authored,"midi"))&&
                 tone.attack==music::Attack::Picked&&tone.tieFrom.empty(),
                 "Rung08 printed string/fret/finger/pitch/articulation differs");
            event.handDirection=((i%2==0)==down)?"D":"U";
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference(),"Rung08 D/U model projection invalid");
    }
    need(seen==std::set<std::string>{"fg:variant:007694","fg:variant:007695"},
         "Rung08 variant coverage differs");
    return result;
}
} // namespace fathom::lesson
