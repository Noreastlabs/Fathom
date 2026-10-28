#pragma once
// Exact rev1 Level3 Mode B Exercise001 second-pass adapter. The reference keeps
// all twelve historical variants; only two reviewed even-volume routes render.
#include "content/Canonical.hpp"
#include <algorithm>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline bool exactLevel003ModeBRetainedVariants(const json::Value& variants) {
    if(!variants.isArray()||variants.array().size()!=12)return false;
    std::set<std::string> expected,observed;
    for(int number=826;number<=837;++number){
        const auto digits=std::to_string(number);
        expected.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
    }
    for(const auto& variant:variants.array()){
        const auto* id=variant.find("id");const auto* events=variant.find("event_ids");
        if(!id||!id->isString()||!events||!events->isArray()||events->array().size()!=40||
            !observed.insert(id->string()).second)return false;
    }
    return observed==expected;
}

inline content::Result validateLevel003ModeBExercise001Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool good,const char* why){if(!good)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    constexpr const char* sourcePackageSha="5d2ae1af6277907bf3644841ad18cf9c33bffc59190d66f554d9cd1baa08d5f1";
    constexpr const char* sourceProfileSha="186025ef4fecce249f7926a218b96c07e4d6256fa6569976530254051e0fc51e";
    constexpr const char* installedProfileSha="582e4d0392704cd3f6746614e3bbe88d8e8ec7f82ab04affccefaf5aed77e28c";
    constexpr const char* registrySha="b73a97f613162c6a93311ac9c234fe7a9e68058eacb5c58a4376063a49244574";
    constexpr const char* planSha="4353c4cf4a45d451e7a572f18ca483830228f13dc54d13e73b94044f11df7793";
    constexpr const char* decisionExpected="0adbc8ee7d80935f27abb74c7c52d45008b8e82e2f411e1ac852ecc499b78da9";
    constexpr const char* bodySha="de7b72f58de406164a7d03d6bfbf175d36a7e8c01b73ff8e48c08f276b877b50";
    need(decisionSha==decisionExpected&&content::sha256(decisionBytes)==decisionExpected,
         "Level3 ModeB001 runtime decision changed");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level003-modeb001-ex001-runtime-candidate.1"&&
         at(decision,"status").string()=="ACCEPTED_FOR_ONE_CASE_RUNTIME_CANDIDATE"&&
         at(decision,"manager_release_sha256").string()=="66eefe03662b75e968b7b30beefcabe2d2e6dd400515126ff263cf72f00ecd24"&&
         at(decision,"loader_addendum_sha256").string()=="eb5d0333bcafc5fead7019beef026afab969a532a4af2699c3ee841705e09d5a"&&
         at(decision,"prospective_runtime_decision_sha256").string()=="df44a2dbd0d7d6c28d30c436948f773e91ef22d33034f9b4123590e2a7556de0"&&
         at(decision,"source_package_sha256").string()==sourcePackageSha&&
         at(decision,"source_profile_sha256").string()==sourceProfileSha&&
         at(decision,"installed_profile_sha256").string()==installedProfileSha&&
         at(decision,"registry_sha256").string()==registrySha&&
         at(decision,"canonical_body_sha256").string()==bodySha&&
         at(decision,"empty_resource_plan_sha256").string()==planSha&&
         at(decision,"item_id").string()=="fg:item:000240"&&
         at(decision,"module_id").string()=="fg:module:000240"&&
         at(decision,"workbook_id").string()=="fg:workbook:000003"&&
         at(decision,"source_identity").string()=="printed:l003:set-1-of-9-exercises-001-012:mode-b-1-3-early-transfer:exercise-001-1212"&&
         at(decision,"canonical_revision")==J::fromInteger(1)&&
         at(decision,"events")==J::fromInteger(40)&&
         at(decision,"selected_memberships")==J::fromInteger(80)&&
         at(decision,"metric_slot_q")==json::parse("[1,4]")&&
         at(decision,"fixed_bpm").null()&&at(decision,"acoustic_note_off").null()&&
         !at(decision,"automatic_credit").boolean()&&!at(decision,"whole_exercise_completion").boolean(),
         "Level3 ModeB001 case/source/no-credit decision differs");
    const std::set<std::string> selected{"fg:variant:000827","fg:variant:000829"};
    const auto& allowed=at(decision,"runtime_allowed_variants").array();
    need(allowed.size()==2&&allowed[0].string()=="fg:variant:000827"&&allowed[1].string()=="fg:variant:000829",
         "Level3 ModeB001 runtime allowlist differs");
    need(content::sha256(input.package)==sourcePackageSha&&
         content::sha256(input.registry)==registrySha&&
         content::sha256(input.profile)==installedProfileSha&&input.expectedProfileSha256==installedProfileSha,
         "Level3 ModeB001 installed packet differs");
    auto frozen=[&](const char* path,const char* expected){const auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==expected,"Level3 ModeB001 frozen authority changed");return json::parse(bytes);};
    const auto originalPackage=frozen("Build/parallel-02/level003-modeb001-case-bound-r01/packet/package.json",sourcePackageSha);
    const auto originalProfile=frozen("Build/parallel-02/level003-modeb001-case-bound-r01/packet/expected-profile.json",sourceProfileSha);
    const auto originalRegistry=frozen("Build/parallel-02/level003-modeb001-case-bound-r01/packet/identity-registry.json",registrySha);
    const auto sourceMap=frozen("Results/parallel-02/level003-modeb001-case-bound-r01/source-to-event.json",
         "114866c6ee358794e3fa1f5be9dc8356461468a42efa02dc8d09b8acb09a9df4");
    const auto foundation=frozen("Content/controls/curriculum-v1/package.json",
         "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255");
    const auto plan=frozen("installed-resource-plan.json",planSha);
    need(at(plan,"resources").array().empty()&&at(plan,"selected_case").string()=="fg:item:000240"&&
         at(plan,"selected_pass").string()=="second_even_volume_straight_sixteenths"&&
         at(plan,"source_profile_resource_plan").null()&&!at(plan,"automatic_credit").boolean(),
         "Level3 ModeB001 empty resource plan differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    auto expectedProfile=originalProfile;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"path\":\"installed-resource-plan.json\",\"sha256\":\"")+planSha+"\",\"entry_ids\":[],\"availability\":\"required_unsupplied\"}");
    need(package==originalPackage&&profile==expectedProfile&&registry==originalRegistry,
         "Level3 ModeB001 reviewed native reference or empty installed adapter changed");
    const auto& records=at(package,"records").array();
    need(records.size()==1,"Level3 ModeB001 requires one exact case");
    const auto& record=records.front();
    need(content::sha256(json::stringify(record))==bodySha&&
         at(record,"id").string()=="fg:item:000240"&&at(record,"module_id").string()=="fg:module:000240"&&
         at(record,"workbook_id").string()=="fg:workbook:000003"&&
         at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(3)&&
         !at(record,"runtime_eligible").boolean()&&at(record,"events").array().size()==40&&
         at(record,"variants").array().size()==12&&at(record,"resource_requirements").array().empty()&&
         at(at(record,"timing"),"status").string()=="unresolved",
         "Level3 ModeB001 exact rev1 identity/40-contact/12-variant record differs");
    std::set<std::string> retained,originalRetained;
    for(int i=826;i<=837;++i)originalRetained.insert("fg:variant:"+std::string(6-std::to_string(i).size(),'0')+std::to_string(i));
    for(const auto& authored:at(record,"variants").array()){
        const auto id=at(authored,"id").string();need(retained.insert(id).second&&at(authored,"event_ids").array().size()==40,
             "Level3 ModeB001 duplicate or shortened historical variant");
    }
    need(retained==originalRetained&&exactLevel003ModeBRetainedVariants(at(record,"variants"))&&
         at(decision,"all_retained_variants").array().size()==12,
         "Level3 ModeB001 all twelve retained identities differ");
    bool headFound=false;
    for(const auto& candidate:at(foundation,"records").array())
        if(at(candidate,"id").string()=="fg:item:000240"){
            need(!headFound&&candidate==record,"Level3 ModeB001 current foundation head differs");headFound=true;
        }
    need(headFound,"Level3 ModeB001 current foundation head absent");
    const auto& map=at(sourceMap,"source_to_event").array();
    need(map.size()==40&&at(sourceMap,"selected_memberships")==J::fromInteger(80),
         "Level3 ModeB001 source projection differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==12,
         "Level3 ModeB001 native nonadmitted reference failed");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        need(retained.count(variant.id)&&seen.insert(variant.id).second&&variant.itemId=="fg:item:000240",
             "Level3 ModeB001 native variant identity differs");
        const bool chosen=selected.count(variant.id)!=0;
        need(variant.validation.validReference()&&variant.source.events.size()==40&&
             (chosen||!variant.readiness.technicallyRenderable),
             "Level3 ModeB001 canonical reference variant changed or incomplete");
        if(!chosen){need(!variant.bindingsComplete,"Unselected Level3 variant unexpectedly bound");continue;}
        need(variant.bindingsComplete,"Selected Level3 source grouping unexpectedly unbound");
        const bool down=variant.id=="fg:variant:000827";
        const auto& authored=*std::find_if(at(record,"variants").array().begin(),at(record,"variants").array().end(),
             [&](const J& value){return at(value,"id").string()==variant.id;});
        need(at(authored,"pick_start").string()==(down?"D":"U")&&
             at(authored,"pick_start_origin").string()=="source_authored"&&
             at(at(authored,"grouping"),"kind").string()=="even_subdivision"&&
             at(at(authored,"grouping"),"notes_per_beat")==J::fromInteger(4),
             "Level3 ModeB001 selected second-pass D/U grouping differs");
        auto& model=variant.source;
        need(model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0&&
             model.measures.empty(),"Level3 ModeB001 instrument or measure scope differs");
        for(std::size_t i=0;i<40;++i){
            auto& event=model.events[i];const auto& contact=at(record,"events").array()[i];const auto& mapping=map[i];
            std::int64_t s{},f{},m{},finger{};
            need(at(contact,"string").integer(s)&&at(contact,"fret").integer(f)&&
                 at(contact,"midi").integer(m)&&at(contact,"finger").integer(finger)&&
                 event.id==at(contact,"event_id").string()&&event.id==at(mapping,"event_id").string()&&
                 event.tones.size()==1&&event.tones.front().string==s&&event.tones.front().fret==f&&
                 event.tones.front().midi==m&&event.tones.front().finger==std::to_string(finger)&&
                 event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),
                 "Level3 ModeB001 original printed contact differs");
            need(at(contact,"onset_q").null()&&at(contact,"duration_q").null(),
                 "Level3 ModeB001 original canonical timing was rewritten");
            event.span.onset=Rational{static_cast<std::int64_t>(i),4};
            event.span.duration=Rational{1,4};
            event.handDirection=(((i%2==0)==down)?"D":"U");
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference()&&variant.validation.model,
             "Level3 ModeB001 selected 40-contact projection invalid");
        variant.readiness=music::assessReadiness(*variant.validation.model,
             {{music::Attack::Picked,music::Attack::HammerOn,music::Attack::PullOff,
               music::Attack::Held,music::Attack::SlideArrival,music::Attack::Bend},true,true,true});
        need(variant.readiness.technicallyRenderable,
             "Level3 ModeB001 selected second-pass projection cannot render");
        variant.bindingsComplete=true; // Only this separately permitted selected route.
    }
    need(seen==retained,"Level3 ModeB001 all historical variants not preserved");
    return result;
}
} // namespace fathom::lesson
