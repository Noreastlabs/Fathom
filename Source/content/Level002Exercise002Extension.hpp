#pragma once
// Exact source-reviewed Level2 Exercise002 1213, one 40-contact case; no learner credit.
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel002Exercise002Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool good,const char* why){if(!good)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    constexpr const char* packageSha="41cf4ebfd29792872813dbcdc1342e40d6e0a020b1eeebd80942cff8622facd0";
    constexpr const char* profileSha="1d78e2e7445e3b4736124ac876e69c07b0adfa1f220287a5fd0f5cd6e21e4b03";
    constexpr const char* originalProfileSha="776d41cdcb9ff6db87d56fd29e0523bbbf222408060d2564f5869d4d25395aa6";
    constexpr const char* planSha="a9f56e56b925499e5a367dde4476312f3a42bcd250e5c87b336d85247cd57d1a";
    constexpr const char* registrySha="adea111e58fc2aec5bb49ee38372ff64ebae8c57430320ad8b7ab6d9f6c49d6f";
    constexpr const char* allocationSha="ea105220fbac6589dd95a64427d185436a4f882b392c97a875b044fe3af389f1";
    constexpr const char* expectedDecision="e840455c908cb099fbba9ed6cf67912346a7ea23a275dfdf3f4dff8b16ddbf70";
    constexpr const char* version="curriculum-v1-level002-ex002-1213-straight16-private.1";
    need(decisionSha==expectedDecision&&content::sha256(decisionBytes)==expectedDecision,
         "Level2 Exercise002 exact Curriculum decision changed");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level002-ex002-1213-curriculum-runtime-decision.1"&&
         at(decision,"status").string()=="ACCEPTED_FOR_ONE_CASE_RUNTIME_CANDIDATE"&&
         at(decision,"authority_name").string()=="P02 interim agent Curriculum/Product runtime decision owner"&&
         at(decision,"manager_release_sha256").string()=="cbe0aebf8e9230af327ee059625cf6cd72d927534fa598d30ff6e8492bb44ff6"&&
         at(decision,"source_review_sha256").string()=="a946aa7a4c89502d86af334c9f857fd43beb4b9324b3af3ac9dce74c2d7e70f8"&&
         at(decision,"native_review_sha256").string()=="bc46d1c9fa5f381629b7fdcaf098bb200fd20a2896b0a8f9860d80fe80156261"&&
         at(decision,"native_adoption_sha256").string()=="69784a1e9722875e842e64568937ba60de02f61e562ff457fd773a5671c27769"&&
         at(decision,"package_sha256").string()==packageSha&&
         at(decision,"original_profile_sha256").string()==originalProfileSha&&
         at(decision,"installed_profile_sha256").string()==profileSha&&
         at(decision,"installed_empty_resource_plan_sha256").string()==planSha&&
         at(decision,"registry_sha256").string()==registrySha&&at(decision,"allocation_sha256").string()==allocationSha,
         "Level2 Exercise002 source/native/Curriculum authority differs");
    const auto expectedScope=json::parse(R"fathom({"item_id":"fg:item:001188","module_id":"fg:module:001188","variants":["fg:variant:007716","fg:variant:007717"],"source_identity":"printed:l002:set-1-of-9-exercises-001-012:exercise-002-1213","source_extent_kind":"exact_single_printed_unit_candidate","events":40,"selected_grouping":"straight_sixteenths","selected_relative_grid":"q=i/4; duration=1/4; endq=10","source_authored_starts":["D","U"],"continuous_alternation_no_turn_reset":"bounded_interpretation","fixed_bpm":null,"fixed_meter":null,"acoustic_sustain":null,"performance_assessment":false,"automatic_credit":false,"whole_workbook":false,"resource_requirements":[]})fathom");
    need(at(decision,"scope")==expectedScope,"Level2 Exercise002 one-case/no-credit scope differs");
    need(content::sha256(input.package)==packageSha&&content::sha256(input.profile)==profileSha&&
         input.expectedProfileSha256==profileSha&&content::sha256(input.registry)==registrySha,
         "Level2 Exercise002 installed packet differs");
    auto frozen=[&](const char* path,const char* sha){const auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==sha,"Level2 Exercise002 frozen authority differs");return json::parse(bytes);};
    const auto originalPackage=frozen("Build/parallel-02/level002-ex002-native-r01/r02/package.json",packageSha);
    const auto originalProfile=frozen("Build/parallel-02/level002-ex002-native-r01/r02/expected-profile.json",originalProfileSha);
    const auto plan=frozen("installed-resource-plan.json",planSha);
    need(at(plan,"resources").array().empty()&&at(plan,"selected_case").string()=="fg:item:001188"&&
         at(plan,"selected_grouping").string()=="straight_sixteenths"&&
         at(plan,"source_profile_resource_plan").null()&&!at(plan,"automatic_credit").boolean(),
         "Level2 Exercise002 empty resource adapter differs");
    const auto originalRegistry=frozen("Build/parallel-02/level002-ex002-native-r01/identity-registry.json",registrySha);
    const auto allocation=frozen("Build/parallel-02/level002-ex002-native-r01/candidate-allocation.json",allocationSha);
    need(at(allocation,"records").object().size()==1&&at(allocation,"records").object().count("fg:item:001188")==1,
         "Level2 Exercise002 case-bound allocation differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    auto expectedProfile=originalProfile;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"path\":\"installed-resource-plan.json\",\"sha256\":\"")+planSha+"\",\"entry_ids\":[],\"availability\":\"required_unsupplied\"}");
    need(package==originalPackage&&profile==expectedProfile&&registry==originalRegistry,
         "Level2 Exercise002 reviewed native packet or exact empty adapter differs");
    const auto& record=at(package,"records").array().front();
    need(at(package,"records").array().size()==1&&at(package,"sources").object().size()==4&&
         at(record,"id").string()=="fg:item:001188"&&at(record,"module_id").string()=="fg:module:001188"&&
         at(record,"workbook_id").string()=="fg:workbook:000002"&&
         at(record,"events").array().size()==40&&at(record,"variants").array().size()==2&&
         at(record,"resource_requirements").array().empty()&&
         at(record,"timing").object().at("status").string()=="source_defined"&&
         !at(record,"runtime_eligible").boolean()&&at(package,"content_version").string()==version,
         "Level2 Exercise002 source extent, timing or resource truth differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
         "Level2 Exercise002 native nonadmitted reference failed");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        const bool down=variant.id=="fg:variant:007716";
        need((down||variant.id=="fg:variant:007717")&&seen.insert(variant.id).second&&
             variant.itemId=="fg:item:001188"&&!variant.bindingsComplete&&
             !variant.readiness.technicallyRenderable&&variant.validation.validReference(),
             "Level2 Exercise002 frozen native unresolved state differs");
        const auto& authoredVariant=at(record,"variants").array()[down?0:1];
        need(at(authoredVariant,"id").string()==variant.id&&at(authoredVariant,"pick_start").string()==(down?"D":"U")&&
             at(authoredVariant,"pick_start_origin").string()=="source_authored"&&
             at(at(authoredVariant,"grouping"),"kind").string()=="even_subdivision"&&
             at(at(authoredVariant,"grouping"),"notes_per_beat")==json::Value::fromInteger(4)&&
             at(authoredVariant,"unresolved").array().size()==1,
             "Level2 Exercise002 selected straight-sixteenth D/U policy differs");
        auto& model=variant.source;
        need(model.events.size()==40&&model.measures.empty()&&
             model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0,
             "Level2 Exercise002 tuning or event model differs");
        for(std::size_t i=0;i<40;++i){auto& event=model.events[i];const auto& authored=at(record,"events").array()[i];
            need(event.id==at(authored,"event_id").string()&&event.span.onset==Rational{static_cast<std::int64_t>(i),4}&&
                 event.span.duration==Rational{1,4}&&event.tones.size()==1,
                 "Level2 Exercise002 event identity, selected onset or duration differs");
            event.handDirection=(((i%2==0)==down)?"D":"U");
            const auto& tone=event.tones.front();std::int64_t s{},f{},m{},finger{};
            need(at(authored,"string").integer(s)&&at(authored,"fret").integer(f)&&
                 at(authored,"midi").integer(m)&&at(authored,"finger").integer(finger)&&
                 tone.string==s&&tone.fret==f&&tone.midi==m&&tone.finger==std::to_string(finger)&&
                 tone.attack==music::Attack::Picked&&tone.tieFrom.empty(),
                 "Level2 Exercise002 original 1213 contact differs");
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference()&&variant.validation.model,
             "Level2 Exercise002 selected D/U model projection invalid");
        variant.readiness=music::assessReadiness(*variant.validation.model,
             {{music::Attack::Picked,music::Attack::HammerOn,music::Attack::PullOff,
               music::Attack::Held,music::Attack::SlideArrival,music::Attack::Bend},true,true,true});
        need(variant.readiness.technicallyRenderable,
             "Level2 Exercise002 selected 40-contact route is not renderable");
        variant.bindingsComplete=true; // resolves only the chosen straight-sixteenth/D-U route.
    }
    need(seen==std::set<std::string>{"fg:variant:007716","fg:variant:007717"},
         "Level2 Exercise002 D/U coverage differs");
    return result;
}
} // namespace fathom::lesson
