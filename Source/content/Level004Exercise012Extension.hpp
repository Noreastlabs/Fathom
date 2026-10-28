#pragma once
// Exact rev1 Level4 Exercise012 second-pass adapter. The reference keeps
// all twelve historical variants; only two reviewed even-volume routes render.
#include "content/Canonical.hpp"
#include <algorithm>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline bool exactLevel004Ex012RetainedVariants(const json::Value& variants) {
    if(!variants.isArray()||variants.array().size()!=12)return false;
    std::set<std::string> expected,observed;
    for(int number=3406;number<=3417;++number){
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

inline content::Result validateLevel004Exercise012Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool good,const char* why){if(!good)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{const auto* found=value.find(key);if(!found)throw std::runtime_error(std::string("Missing Level4 Ex012 field: ")+key);return *found;};
    constexpr const char* sourcePackageSha="636aad73d4d37154530ec6f4fd9b1756176b15d5312fd079c307ae26c117b8cd";
    constexpr const char* sourceProfileSha="88c39787c4f1e088930bb642ecd581c5a59aa8d4d9b089e38ada0813707a692c";
    constexpr const char* installedProfileSha="11317bc23735412340ca2037906a3fdca2e11eca5216fa6506118bddd0f63a57";
    constexpr const char* registrySha="ffffde4e7bc899a3c1da051dbe07eb65c81f4af47bd7296bd2f2438bf319314d";
    constexpr const char* planSha="e1b880705cc938735d13f2a8c8b1b191f344335dbbbba79190a7496ef8327d1a";
    constexpr const char* decisionExpected="7d569c994c787d7302bb4a2abdeef39a1a74617a813e94e3f53e6d925caa4e52";
    constexpr const char* bodySha="19f8d982af8d81f84ced93b9f1ffb5837c9075c62270e19b626adaf3ba1d5cf2";
    need(decisionSha==decisionExpected&&content::sha256(decisionBytes)==decisionExpected,
         "Level4 Ex012 runtime decision changed");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level004-ex012-runtime-candidate.1"&&
         at(decision,"status").string()=="ACCEPTED_FOR_ONE_CASE_RUNTIME_CANDIDATE"&&
         at(decision,"manager_release_sha256").string()=="2032d6a6c4731d409d2c8b0a9f1066e059a48238776868ab5e47b67d96d8a6ee"&&
         at(decision,"prospective_typed_decision_sha256").string()=="54c724d63b616fae1a821c04be7a829e92a1cf52fd5ecfe3d6f0b2a9f5ff3f13"&&
         at(decision,"runtime_adoption_sha256").string()=="b19abbb74dcfc35fb92c79ac7e2ea5e07e0605ebe8d837b17006448b30823f05"&&
         at(decision,"curriculum_decision_sha256").string()=="4c429870ada16511f043bb7ca9515a36a4012f3f2449da3293945a5386ddda7b"&&
         at(decision,"curriculum_adoption_sha256").string()=="54e49ba0394c6f07349af5e2296fcd2160dc7b46733962068de7d191213150a0"&&
         at(decision,"source_package_sha256").string()==sourcePackageSha&&
         at(decision,"source_profile_sha256").string()==sourceProfileSha&&
         at(decision,"installed_profile_sha256").string()==installedProfileSha&&
         at(decision,"registry_sha256").string()==registrySha&&
         at(decision,"canonical_body_sha256").string()==bodySha&&
         at(decision,"empty_resource_plan_sha256").string()==planSha&&
         at(decision,"item_id").string()=="fg:item:000455"&&
         at(decision,"module_id").string()=="fg:module:000455"&&
         at(decision,"workbook_id").string()=="fg:workbook:000004"&&
         at(decision,"source_identity").string()=="printed:l004:set-1-of-9-exercises-001-012:exercise-012-1314"&&
         at(decision,"canonical_revision")==J::fromInteger(1)&&
         at(decision,"events")==J::fromInteger(32)&&
         at(decision,"selected_memberships")==J::fromInteger(64)&&
         at(decision,"metric_slot_q")==json::parse("[1,4]")&&
         at(decision,"fixed_bpm").null()&&at(decision,"acoustic_note_off").null()&&
         !at(decision,"automatic_credit").boolean()&&!at(decision,"whole_exercise_completion").boolean(),
         "Level4 Ex012 case/source/no-credit decision differs");
    const std::set<std::string> selected{"fg:variant:003407","fg:variant:003409"};
    const auto& allowed=at(decision,"runtime_allowed_variants").array();
    need(allowed.size()==2&&allowed[0].string()=="fg:variant:003407"&&allowed[1].string()=="fg:variant:003409",
         "Level4 Ex012 runtime allowlist differs");
    need(content::sha256(input.package)==sourcePackageSha&&
         content::sha256(input.registry)==registrySha&&
         content::sha256(input.profile)==installedProfileSha&&input.expectedProfileSha256==installedProfileSha,
         "Level4 Ex012 installed packet differs");
    auto frozen=[&](const char* path,const char* expected){const auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==expected,"Level4 Ex012 frozen authority changed");return json::parse(bytes);};
    const auto originalPackage=frozen("Build/parallel-02/level004-ex012-case-bound-r01/packet/package.json",sourcePackageSha);
    const auto originalProfile=frozen("Build/parallel-02/level004-ex012-case-bound-r01/packet/expected-profile.json",sourceProfileSha);
    const auto originalRegistry=frozen("Build/parallel-02/level004-ex012-case-bound-r01/packet/identity-registry.json",registrySha);
    const auto sourceMap=frozen("Build/parallel-02/level004-ex012-case-bound-r01/packet/selected-projection.json",
         "5aebadc225c7d1b84953b26fb917e3915db3833e09d89387dd03b28aed6e3b14");
    const auto foundation=frozen("Content/controls/curriculum-v1/package.json",
         "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255");
    const auto plan=frozen("installed-resource-plan.json",planSha);
    need(at(plan,"resources").array().empty()&&at(plan,"selected_case").string()=="fg:item:000455"&&
         at(plan,"selected_pass").string()=="second_even_volume_straight_sixteenths"&&
         at(plan,"source_profile_resource_plan").null()&&!at(plan,"automatic_credit").boolean(),
         "Level4 Ex012 empty resource plan differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    auto expectedProfile=originalProfile;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"path\":\"installed-resource-plan.json\",\"sha256\":\"")+planSha+"\",\"entry_ids\":[],\"availability\":\"required_unsupplied\"}");
    need(package==originalPackage&&profile==expectedProfile&&registry==originalRegistry,
         "Level4 Ex012 reviewed native reference or empty installed adapter changed");
    const auto& records=at(package,"records").array();
    need(records.size()==1,"Level4 Ex012 requires one exact case");
    const auto& record=records.front();
    need(content::sha256(json::stringify(record))==bodySha&&
         at(record,"id").string()=="fg:item:000455"&&at(record,"module_id").string()=="fg:module:000455"&&
         at(record,"workbook_id").string()=="fg:workbook:000004"&&
         at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(4)&&
         !at(record,"runtime_eligible").boolean()&&at(record,"events").array().size()==32&&
         at(record,"variants").array().size()==12&&at(record,"resource_requirements").array().empty()&&
         at(at(record,"timing"),"status").string()=="unresolved",
         "Level4 Ex012 exact rev1 identity/32-contact/12-variant record differs");
    std::set<std::string> retained,originalRetained;
    for(int i=3406;i<=3417;++i)originalRetained.insert("fg:variant:"+std::string(6-std::to_string(i).size(),'0')+std::to_string(i));
    for(const auto& authored:at(record,"variants").array()){
        const auto id=at(authored,"id").string();need(retained.insert(id).second&&at(authored,"event_ids").array().size()==32,
             "Level4 Ex012 duplicate or shortened historical variant");
    }
    need(retained==originalRetained&&exactLevel004Ex012RetainedVariants(at(record,"variants"))&&
         at(decision,"all_retained_variants").array().size()==12,
         "Level4 Ex012 all twelve retained identities differ");
    bool headFound=false;
    for(const auto& candidate:at(foundation,"records").array())
        if(at(candidate,"id").string()=="fg:item:000455"){
            need(!headFound&&candidate==record,"Level4 Ex012 current foundation head differs");headFound=true;
        }
    need(headFound,"Level4 Ex012 current foundation head absent");
    const auto& map=at(sourceMap,"selected").array();
    need(map.size()==2&&at(sourceMap,"source_identity").string()==at(decision,"source_identity").string()&&
         at(sourceMap,"record_sha256").string()==bodySha&&
         at(map[0],"variant_id").string()=="fg:variant:003407"&&
         at(map[1],"variant_id").string()=="fg:variant:003409"&&
         at(map[0],"event_ids").array().size()==32&&at(map[1],"event_ids").array().size()==32,
         "Level4 Ex012 source projection differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==12,
         "Level4 Ex012 native nonadmitted reference failed");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        need(retained.count(variant.id)&&seen.insert(variant.id).second&&variant.itemId=="fg:item:000455",
             "Level4 Ex012 native variant identity differs");
        const bool chosen=selected.count(variant.id)!=0;
        need(variant.validation.validReference()&&variant.source.events.size()==32&&
             (chosen||!variant.readiness.technicallyRenderable),
             "Level4 Ex012 canonical reference variant changed or incomplete");
        if(!chosen){need(!variant.bindingsComplete,"Unselected Level4 variant unexpectedly bound");continue;}
        need(variant.bindingsComplete,"Selected Level4 source grouping unexpectedly unbound");
        const bool down=variant.id=="fg:variant:003407";
        const auto& selectedMap=map[down?0:1];
        need(at(selectedMap,"start").string()==(down?"D":"U")&&
             at(selectedMap,"metric_duration_q")==json::parse("[1,4]")&&
             at(selectedMap,"end_q")==json::parse("[8,1]")&&
             at(selectedMap,"metric_onsets_q").array().size()==32&&
             at(selectedMap,"source_reviewed_strokes").array().size()==32,
             "Level4 Ex012 reviewed metric/stroke projection differs");
        const auto& authored=*std::find_if(at(record,"variants").array().begin(),at(record,"variants").array().end(),
             [&](const J& value){return at(value,"id").string()==variant.id;});
        need(at(authored,"pick_start").string()==(down?"D":"U")&&
             at(authored,"pick_start_origin").string()=="source_authored"&&
             at(at(authored,"grouping"),"kind").string()=="even_subdivision"&&
             at(at(authored,"grouping"),"notes_per_beat")==J::fromInteger(4),
             "Level4 Ex012 selected second-pass D/U grouping differs");
        auto& model=variant.source;
        need(model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0&&
             model.measures.empty(),"Level4 Ex012 instrument or measure scope differs");
        for(std::size_t i=0;i<32;++i){
            auto& event=model.events[i];const auto& contact=at(record,"events").array()[i];
            std::int64_t s{},f{},m{},finger{};
            need(at(contact,"string").integer(s)&&at(contact,"fret").integer(f)&&
                 at(contact,"midi").integer(m)&&at(contact,"finger").integer(finger)&&
                 event.id==at(contact,"event_id").string()&&
                 at(selectedMap,"event_ids").array()[i].string()==event.id&&
                 at(selectedMap,"metric_onsets_q").array()[i]==json::parse("["+std::to_string(i)+",4]")&&
                 at(selectedMap,"source_reviewed_strokes").array()[i].string()==(((i%2==0)==down)?"D":"U")&&
                 event.tones.size()==1&&event.tones.front().string==s&&event.tones.front().fret==f&&
                 event.tones.front().midi==m&&event.tones.front().finger==std::to_string(finger)&&
                 event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),
                 "Level4 Ex012 original printed contact differs");
            need(at(contact,"onset_q").null()&&at(contact,"duration_q").null(),
                 "Level4 Ex012 original canonical timing was rewritten");
            event.span.onset=Rational{static_cast<std::int64_t>(i),4};
            event.span.duration=Rational{1,4};
            event.handDirection=(((i%2==0)==down)?"D":"U");
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference()&&variant.validation.model,
             "Level4 Ex012 selected 32-contact projection invalid");
        variant.readiness=music::assessReadiness(*variant.validation.model,
             {{music::Attack::Picked,music::Attack::HammerOn,music::Attack::PullOff,
               music::Attack::Held,music::Attack::SlideArrival,music::Attack::Bend},true,true,true});
        need(variant.readiness.technicallyRenderable,
             "Level4 Ex012 selected second-pass projection cannot render");
        variant.bindingsComplete=true; // Only this separately permitted selected route.
    }
    need(seen==retained,"Level4 Ex012 all historical variants not preserved");
    return result;
}
} // namespace fathom::lesson
