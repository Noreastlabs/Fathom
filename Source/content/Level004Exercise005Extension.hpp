#pragma once
// Exact rev1 Level4 Exercise005 second-pass adapter. The reference keeps
// all twelve historical variants; only two reviewed even-volume routes render.
#include "content/Canonical.hpp"
#include <algorithm>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline bool exactLevel004Ex005RetainedVariants(const json::Value& variants) {
    if(!variants.isArray()||variants.array().size()!=12)return false;
    std::set<std::string> expected,observed;
    for(int number=3322;number<=3333;++number){
        const auto digits=std::to_string(number);
        expected.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
    }
    for(const auto& variant:variants.array()){
        const auto* id=variant.find("id");const auto* events=variant.find("event_ids");
        if(!id||!id->isString()||!events||!events->isArray()||events->array().size()!=32||
            !observed.insert(id->string()).second)return false;
    }
    return observed==expected;
}

inline content::Result validateLevel004Exercise005Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool good,const char* why){if(!good)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    constexpr const char* sourcePackageSha="b7a18e588d2d22f02aab0e6a73098063f8c925fe898105652ddcf29cf5a6c796";
    constexpr const char* sourceProfileSha="473c7e28456de79e7af62f4331fbc51e644ae409f1d9a1276667bb7067ecc5dd";
    constexpr const char* installedProfileSha="f26f6ed3a6a48e725b2e8f230db3cf8d60c060832ee58749f5a240b5254e2661";
    constexpr const char* registrySha="6b21e32ae5ef6d4fe9e557495855d77de9769bb3246b69aacdf6a795d351f1e1";
    constexpr const char* planSha="3c6909976463bfacfae26c41fee8c9fa965320393036f39196c9c62e25e99cf2";
    constexpr const char* decisionExpected="dc745f6116e7ce713603d5ca16eeb19147e0c39055d6da9f780c3fc207341881";
    constexpr const char* bodySha="808449598a007108168bc47eb19a1b6a4e33d79d7c9c792afdada07b15c5ec0f";
    need(decisionSha==decisionExpected&&content::sha256(decisionBytes)==decisionExpected,
         "Level4 Ex005 runtime decision changed");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level004-ex005-runtime-candidate.1"&&
         at(decision,"status").string()=="ACCEPTED_FOR_ONE_CASE_RUNTIME_CANDIDATE"&&
         at(decision,"manager_release_sha256").string()=="c5aad7a21ca3a34dd79931741bab6b4e5171559bce99106afd8a1f3fdecbdaf4"&&
         at(decision,"prospective_typed_decision_sha256").string()=="52d555c8c0e82ac31707fa67f4780c272fb1686e9936534ed1f305561a9b3f50"&&
         at(decision,"runtime_adoption_sha256").string()=="c5e17b41dcf22d0c5fa9ec00ea7725b39fcbab907865fbb7a66cd1facaab0d1e"&&
         at(decision,"curriculum_decision_sha256").string()=="16066135f3af8b718f03d75cf184fd29f77e78f14f278d1944674acb83ae5b25"&&
         at(decision,"curriculum_adoption_sha256").string()=="4b6fb94dab3f221b56e3020e66f6a84abb1a14c62d77de38486b5a79122cf21f"&&
         at(decision,"source_package_sha256").string()==sourcePackageSha&&
         at(decision,"source_profile_sha256").string()==sourceProfileSha&&
         at(decision,"installed_profile_sha256").string()==installedProfileSha&&
         at(decision,"registry_sha256").string()==registrySha&&
         at(decision,"canonical_body_sha256").string()==bodySha&&
         at(decision,"empty_resource_plan_sha256").string()==planSha&&
         at(decision,"item_id").string()=="fg:item:000448"&&
         at(decision,"module_id").string()=="fg:module:000448"&&
         at(decision,"workbook_id").string()=="fg:workbook:000004"&&
         at(decision,"source_identity").string()=="printed:l004:set-1-of-9-exercises-001-012:exercise-005-1232"&&
         at(decision,"canonical_revision")==J::fromInteger(1)&&
         at(decision,"events")==J::fromInteger(32)&&
         at(decision,"selected_memberships")==J::fromInteger(64)&&
         at(decision,"metric_slot_q")==json::parse("[1,4]")&&
         at(decision,"fixed_bpm").null()&&at(decision,"acoustic_note_off").null()&&
         !at(decision,"automatic_credit").boolean()&&!at(decision,"whole_exercise_completion").boolean(),
         "Level4 Ex005 case/source/no-credit decision differs");
    const std::set<std::string> selected{"fg:variant:003323","fg:variant:003325"};
    const auto& allowed=at(decision,"runtime_allowed_variants").array();
    need(allowed.size()==2&&allowed[0].string()=="fg:variant:003323"&&allowed[1].string()=="fg:variant:003325",
         "Level4 Ex005 runtime allowlist differs");
    need(content::sha256(input.package)==sourcePackageSha&&
         content::sha256(input.registry)==registrySha&&
         content::sha256(input.profile)==installedProfileSha&&input.expectedProfileSha256==installedProfileSha,
         "Level4 Ex005 installed packet differs");
    auto frozen=[&](const char* path,const char* expected){const auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==expected,"Level4 Ex005 frozen authority changed");return json::parse(bytes);};
    const auto originalPackage=frozen("Build/parallel-02/level004-ex005-case-bound-r01/packet/package.json",sourcePackageSha);
    const auto originalProfile=frozen("Build/parallel-02/level004-ex005-case-bound-r01/packet/expected-profile.json",sourceProfileSha);
    const auto originalRegistry=frozen("Build/parallel-02/level004-ex005-case-bound-r01/packet/identity-registry.json",registrySha);
    const auto sourceMap=frozen("Build/parallel-02/level004-ex005-case-bound-r01/packet/selected-projection.json",
         "e700389164258814b2188781699f0f7094ef47ec72b3fd389e66ed540d1d4d72");
    const auto foundation=frozen("Content/controls/curriculum-v1/package.json",
         "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255");
    const auto plan=frozen("installed-resource-plan.json",planSha);
    need(at(plan,"resources").array().empty()&&at(plan,"selected_case").string()=="fg:item:000448"&&
         at(plan,"selected_pass").string()=="second_even_volume_straight_sixteenths"&&
         at(plan,"source_profile_resource_plan").null()&&!at(plan,"automatic_credit").boolean(),
         "Level4 Ex005 empty resource plan differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    auto expectedProfile=originalProfile;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"path\":\"installed-resource-plan.json\",\"sha256\":\"")+planSha+"\",\"entry_ids\":[],\"availability\":\"required_unsupplied\"}");
    need(package==originalPackage&&profile==expectedProfile&&registry==originalRegistry,
         "Level4 Ex005 reviewed native reference or empty installed adapter changed");
    const auto& records=at(package,"records").array();
    need(records.size()==1,"Level4 Ex005 requires one exact case");
    const auto& record=records.front();
    need(content::sha256(json::stringify(record))==bodySha&&
         at(record,"id").string()=="fg:item:000448"&&at(record,"module_id").string()=="fg:module:000448"&&
         at(record,"workbook_id").string()=="fg:workbook:000004"&&
         at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(4)&&
         !at(record,"runtime_eligible").boolean()&&at(record,"events").array().size()==32&&
         at(record,"variants").array().size()==12&&at(record,"resource_requirements").array().empty()&&
         at(at(record,"timing"),"status").string()=="unresolved",
         "Level4 Ex005 exact rev1 identity/32-contact/12-variant record differs");
    std::set<std::string> retained,originalRetained;
    for(int i=3322;i<=3333;++i)originalRetained.insert("fg:variant:"+std::string(6-std::to_string(i).size(),'0')+std::to_string(i));
    for(const auto& authored:at(record,"variants").array()){
        const auto id=at(authored,"id").string();need(retained.insert(id).second&&at(authored,"event_ids").array().size()==32,
             "Level4 Ex005 duplicate or shortened historical variant");
    }
    need(retained==originalRetained&&exactLevel004Ex005RetainedVariants(at(record,"variants"))&&
         at(decision,"all_retained_variants").array().size()==12,
         "Level4 Ex005 all twelve retained identities differ");
    bool headFound=false;
    for(const auto& candidate:at(foundation,"records").array())
        if(at(candidate,"id").string()=="fg:item:000448"){
            need(!headFound&&candidate==record,"Level4 Ex005 current foundation head differs");headFound=true;
        }
    need(headFound,"Level4 Ex005 current foundation head absent");
    const auto& map=at(sourceMap,"selected").array();
    need(map.size()==2&&at(sourceMap,"source_identity").string()==at(decision,"source_identity").string()&&
         at(sourceMap,"record_sha256").string()==bodySha&&
         at(map[0],"variant_id").string()=="fg:variant:003323"&&
         at(map[1],"variant_id").string()=="fg:variant:003325"&&
         at(map[0],"event_ids").array().size()==32&&at(map[1],"event_ids").array().size()==32,
         "Level4 Ex005 source projection differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==12,
         "Level4 Ex005 native nonadmitted reference failed");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        need(retained.count(variant.id)&&seen.insert(variant.id).second&&variant.itemId=="fg:item:000448",
             "Level4 Ex005 native variant identity differs");
        const bool chosen=selected.count(variant.id)!=0;
        need(variant.validation.validReference()&&variant.source.events.size()==32&&
             (chosen||!variant.readiness.technicallyRenderable),
             "Level4 Ex005 canonical reference variant changed or incomplete");
        if(!chosen){need(!variant.bindingsComplete,"Unselected Level4 variant unexpectedly bound");continue;}
        need(variant.bindingsComplete,"Selected Level4 source grouping unexpectedly unbound");
        const bool down=variant.id=="fg:variant:003323";
        const auto& selectedMap=map[down?0:1];
        need(at(selectedMap,"start").string()==(down?"D":"U")&&
             at(selectedMap,"metric_duration_q")==json::parse("[1,4]")&&
             at(selectedMap,"end_q")==json::parse("[8,1]")&&
             at(selectedMap,"metric_onsets_q").array().size()==32&&
             at(selectedMap,"source_export_strokes").array().size()==32,
             "Level4 Ex005 reviewed metric/stroke projection differs");
        const auto& authored=*std::find_if(at(record,"variants").array().begin(),at(record,"variants").array().end(),
             [&](const J& value){return at(value,"id").string()==variant.id;});
        need(at(authored,"pick_start").string()==(down?"D":"U")&&
             at(authored,"pick_start_origin").string()=="source_authored"&&
             at(at(authored,"grouping"),"kind").string()=="even_subdivision"&&
             at(at(authored,"grouping"),"notes_per_beat")==J::fromInteger(4),
             "Level4 Ex005 selected second-pass D/U grouping differs");
        auto& model=variant.source;
        need(model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0&&
             model.measures.empty(),"Level4 Ex005 instrument or measure scope differs");
        for(std::size_t i=0;i<32;++i){
            auto& event=model.events[i];const auto& contact=at(record,"events").array()[i];
            std::int64_t s{},f{},m{},finger{};
            need(at(contact,"string").integer(s)&&at(contact,"fret").integer(f)&&
                 at(contact,"midi").integer(m)&&at(contact,"finger").integer(finger)&&
                 event.id==at(contact,"event_id").string()&&
                 at(selectedMap,"event_ids").array()[i].string()==event.id&&
                 at(selectedMap,"metric_onsets_q").array()[i]==json::parse("["+std::to_string(i)+",4]")&&
                 at(selectedMap,"source_export_strokes").array()[i].string()==(((i%2==0)==down)?"D":"U")&&
                 event.tones.size()==1&&event.tones.front().string==s&&event.tones.front().fret==f&&
                 event.tones.front().midi==m&&event.tones.front().finger==std::to_string(finger)&&
                 event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),
                 "Level4 Ex005 original printed contact differs");
            need(at(contact,"onset_q").null()&&at(contact,"duration_q").null(),
                 "Level4 Ex005 original canonical timing was rewritten");
            event.span.onset=Rational{static_cast<std::int64_t>(i),4};
            event.span.duration=Rational{1,4};
            event.handDirection=(((i%2==0)==down)?"D":"U");
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference()&&variant.validation.model,
             "Level4 Ex005 selected 32-contact projection invalid");
        variant.readiness=music::assessReadiness(*variant.validation.model,
             {{music::Attack::Picked,music::Attack::HammerOn,music::Attack::PullOff,
               music::Attack::Held,music::Attack::SlideArrival,music::Attack::Bend},true,true,true});
        need(variant.readiness.technicallyRenderable,
             "Level4 Ex005 selected second-pass projection cannot render");
        variant.bindingsComplete=true; // Only this separately permitted selected route.
    }
    need(seen==retained,"Level4 Ex005 all historical variants not preserved");
    return result;
}
} // namespace fathom::lesson
