#pragma once
// Exact rev1 Level4 Exercise007 second-pass adapter. The reference keeps
// all twelve historical variants; only two reviewed even-volume routes render.
#include "content/Canonical.hpp"
#include <algorithm>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline bool exactLevel004Ex007RetainedVariants(const json::Value& variants) {
    if(!variants.isArray()||variants.array().size()!=12)return false;
    std::set<std::string> expected,observed;
    for(int number=3346;number<=3357;++number){
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

inline content::Result validateLevel004Exercise007Extension(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    using J=json::Value;
    auto need=[](bool good,const char* why){if(!good)throw std::runtime_error(why);};
    auto at=[](const J& value,const char* key)->const J&{const auto* found=value.find(key);if(!found)throw std::runtime_error(std::string("Missing Level4 Ex007 field: ")+key);return *found;};
    constexpr const char* sourcePackageSha="a5f03dca721278b098e2d63bf10f39bf23ff7d8d8f5928fbbd43f02c5643a808";
    constexpr const char* sourceProfileSha="1b09e43ddf777e275e256fd2f949226ea24dcd2fb9fcaad63036ec20e1cd3b9b";
    constexpr const char* installedProfileSha="1b10b6ba1c082d4b0a78f00d19c8794bda08004d05cfff6eb4a1a1b12f210e1c";
    constexpr const char* registrySha="7d6659fd5fe9670ba37daf3b7273b1a642b8c07398e15d8db5039af138d9040d";
    constexpr const char* planSha="a2f2931850756d1f96cf54114c69f2ffa4ed3104098e4d78e9d4f48a320e974c";
    constexpr const char* decisionExpected="c0d5a8172b4273d7e116eedac09f96d0e3d29c373baf498a4308ec0a07b1abcc";
    constexpr const char* bodySha="32df144932bf5f2ec166c543a88920640e1b4e0684462efc87fe1525896e7fe8";
    need(decisionSha==decisionExpected&&content::sha256(decisionBytes)==decisionExpected,
         "Level4 Ex007 runtime decision changed");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level004-ex007-runtime-candidate.1"&&
         at(decision,"status").string()=="ACCEPTED_FOR_ONE_CASE_RUNTIME_CANDIDATE"&&
         at(decision,"manager_release_sha256").string()=="feda290bf6fcdec1dd9f6c9ea24ad1599c884c1fc234c939ce09c893d4e1354e"&&
         at(decision,"prospective_typed_decision_sha256").string()=="8c9b8bb2f45fe73c235aafbc668b385e26de897a41e2c50c6e4a75277780a15a"&&
         at(decision,"runtime_adoption_sha256").string()=="b28e391b158d3a61d8fdf16632127303be861f745bde030ccc87841ed5e84b04"&&
         at(decision,"curriculum_decision_sha256").string()=="d1da7685bfb4346ef6b56042cb610cfeb0db88f175e1e7167b07fea38a65ecfa"&&
         at(decision,"curriculum_adoption_sha256").string()=="f2c44c165451269b6a5e37251b33bc8e74d135b201acd11d949515cd66172882"&&
         at(decision,"source_package_sha256").string()==sourcePackageSha&&
         at(decision,"source_profile_sha256").string()==sourceProfileSha&&
         at(decision,"installed_profile_sha256").string()==installedProfileSha&&
         at(decision,"registry_sha256").string()==registrySha&&
         at(decision,"canonical_body_sha256").string()==bodySha&&
         at(decision,"empty_resource_plan_sha256").string()==planSha&&
         at(decision,"item_id").string()=="fg:item:000450"&&
         at(decision,"module_id").string()=="fg:module:000450"&&
         at(decision,"workbook_id").string()=="fg:workbook:000004"&&
         at(decision,"source_identity").string()=="printed:l004:set-1-of-9-exercises-001-012:exercise-007-1241"&&
         at(decision,"canonical_revision")==J::fromInteger(1)&&
         at(decision,"events")==J::fromInteger(32)&&
         at(decision,"selected_memberships")==J::fromInteger(64)&&
         at(decision,"metric_slot_q")==json::parse("[1,4]")&&
         at(decision,"fixed_bpm").null()&&at(decision,"acoustic_note_off").null()&&
         !at(decision,"automatic_credit").boolean()&&!at(decision,"whole_exercise_completion").boolean(),
         "Level4 Ex007 case/source/no-credit decision differs");
    const std::set<std::string> selected{"fg:variant:003347","fg:variant:003349"};
    const auto& allowed=at(decision,"runtime_allowed_variants").array();
    need(allowed.size()==2&&allowed[0].string()=="fg:variant:003347"&&allowed[1].string()=="fg:variant:003349",
         "Level4 Ex007 runtime allowlist differs");
    need(content::sha256(input.package)==sourcePackageSha&&
         content::sha256(input.registry)==registrySha&&
         content::sha256(input.profile)==installedProfileSha&&input.expectedProfileSha256==installedProfileSha,
         "Level4 Ex007 installed packet differs");
    auto frozen=[&](const char* path,const char* expected){const auto bytes=content::readBounded(input.sourceRoot/path,32*1024*1024);
        need(content::sha256(bytes)==expected,"Level4 Ex007 frozen authority changed");return json::parse(bytes);};
    const auto originalPackage=frozen("Build/parallel-02/level004-ex007-case-bound-r01/packet/package.json",sourcePackageSha);
    const auto originalProfile=frozen("Build/parallel-02/level004-ex007-case-bound-r01/packet/expected-profile.json",sourceProfileSha);
    const auto originalRegistry=frozen("Build/parallel-02/level004-ex007-case-bound-r01/packet/identity-registry.json",registrySha);
    const auto sourceMap=frozen("Build/parallel-02/level004-ex007-case-bound-r01/packet/selected-projection.json",
         "842589d7791ad64b01b4722483dc3ba7ec47ed1d7c048d88f94fae8eef5da0a0");
    const auto foundation=frozen("Content/controls/curriculum-v1/package.json",
         "766e7d07d91b3810e0c35ea0799b0afb7f34f25398cfa092de307167adeca255");
    const auto plan=frozen("installed-resource-plan.json",planSha);
    need(at(plan,"resources").array().empty()&&at(plan,"selected_case").string()=="fg:item:000450"&&
         at(plan,"selected_pass").string()=="second_even_volume_straight_sixteenths"&&
         at(plan,"source_profile_resource_plan").null()&&!at(plan,"automatic_credit").boolean(),
         "Level4 Ex007 empty resource plan differs");
    const auto package=json::parse(input.package),profile=json::parse(input.profile),registry=json::parse(input.registry);
    auto expectedProfile=originalProfile;
    expectedProfile.object()["resource_plan"]=json::parse(std::string("{\"path\":\"installed-resource-plan.json\",\"sha256\":\"")+planSha+"\",\"entry_ids\":[],\"availability\":\"required_unsupplied\"}");
    need(package==originalPackage&&profile==expectedProfile&&registry==originalRegistry,
         "Level4 Ex007 reviewed native reference or empty installed adapter changed");
    const auto& records=at(package,"records").array();
    need(records.size()==1,"Level4 Ex007 requires one exact case");
    const auto& record=records.front();
    need(content::sha256(json::stringify(record))==bodySha&&
         at(record,"id").string()=="fg:item:000450"&&at(record,"module_id").string()=="fg:module:000450"&&
         at(record,"workbook_id").string()=="fg:workbook:000004"&&
         at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(4)&&
         !at(record,"runtime_eligible").boolean()&&at(record,"events").array().size()==32&&
         at(record,"variants").array().size()==12&&at(record,"resource_requirements").array().empty()&&
         at(at(record,"timing"),"status").string()=="unresolved",
         "Level4 Ex007 exact rev1 identity/32-contact/12-variant record differs");
    std::set<std::string> retained,originalRetained;
    for(int i=3346;i<=3357;++i)originalRetained.insert("fg:variant:"+std::string(6-std::to_string(i).size(),'0')+std::to_string(i));
    for(const auto& authored:at(record,"variants").array()){
        const auto id=at(authored,"id").string();need(retained.insert(id).second&&at(authored,"event_ids").array().size()==32,
             "Level4 Ex007 duplicate or shortened historical variant");
    }
    need(retained==originalRetained&&exactLevel004Ex007RetainedVariants(at(record,"variants"))&&
         at(decision,"all_retained_variants").array().size()==12,
         "Level4 Ex007 all twelve retained identities differ");
    bool headFound=false;
    for(const auto& candidate:at(foundation,"records").array())
        if(at(candidate,"id").string()=="fg:item:000450"){
            need(!headFound&&candidate==record,"Level4 Ex007 current foundation head differs");headFound=true;
        }
    need(headFound,"Level4 Ex007 current foundation head absent");
    const auto& map=at(sourceMap,"selected").array();
    need(map.size()==2&&at(sourceMap,"source_identity").string()==at(decision,"source_identity").string()&&
         at(sourceMap,"record_sha256").string()==bodySha&&
         at(map[0],"variant_id").string()=="fg:variant:003347"&&
         at(map[1],"variant_id").string()=="fg:variant:003349"&&
         at(map[0],"event_ids").array().size()==32&&at(map[1],"event_ids").array().size()==32,
         "Level4 Ex007 source projection differs");
    auto result=content::validate(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==12,
         "Level4 Ex007 native nonadmitted reference failed");
    std::set<std::string> seen;
    for(auto& variant:result.variants){
        need(retained.count(variant.id)&&seen.insert(variant.id).second&&variant.itemId=="fg:item:000450",
             "Level4 Ex007 native variant identity differs");
        const bool chosen=selected.count(variant.id)!=0;
        need(variant.validation.validReference()&&variant.source.events.size()==32&&
             (chosen||!variant.readiness.technicallyRenderable),
             "Level4 Ex007 canonical reference variant changed or incomplete");
        if(!chosen){need(!variant.bindingsComplete,"Unselected Level4 variant unexpectedly bound");continue;}
        need(variant.bindingsComplete,"Selected Level4 source grouping unexpectedly unbound");
        const bool down=variant.id=="fg:variant:003347";
        const auto& selectedMap=map[down?0:1];
        need(at(selectedMap,"start").string()==(down?"D":"U")&&
             at(selectedMap,"metric_duration_q")==json::parse("[1,4]")&&
             at(selectedMap,"end_q")==json::parse("[8,1]")&&
             at(selectedMap,"metric_onsets_q").array().size()==32&&
             at(selectedMap,"source_reviewed_strokes").array().size()==32,
             "Level4 Ex007 reviewed metric/stroke projection differs");
        const auto& authored=*std::find_if(at(record,"variants").array().begin(),at(record,"variants").array().end(),
             [&](const J& value){return at(value,"id").string()==variant.id;});
        need(at(authored,"pick_start").string()==(down?"D":"U")&&
             at(authored,"pick_start_origin").string()=="source_authored"&&
             at(at(authored,"grouping"),"kind").string()=="even_subdivision"&&
             at(at(authored,"grouping"),"notes_per_beat")==J::fromInteger(4),
             "Level4 Ex007 selected second-pass D/U grouping differs");
        auto& model=variant.source;
        need(model.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&model.instrument.capo==0&&
             model.measures.empty(),"Level4 Ex007 instrument or measure scope differs");
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
                 "Level4 Ex007 original printed contact differs");
            need(at(contact,"onset_q").null()&&at(contact,"duration_q").null(),
                 "Level4 Ex007 original canonical timing was rewritten");
            event.span.onset=Rational{static_cast<std::int64_t>(i),4};
            event.span.duration=Rational{1,4};
            event.handDirection=(((i%2==0)==down)?"D":"U");
        }
        variant.validation=music::validate(model);
        need(variant.validation.validReference()&&variant.validation.model,
             "Level4 Ex007 selected 32-contact projection invalid");
        variant.readiness=music::assessReadiness(*variant.validation.model,
             {{music::Attack::Picked,music::Attack::HammerOn,music::Attack::PullOff,
               music::Attack::Held,music::Attack::SlideArrival,music::Attack::Bend},true,true,true});
        need(variant.readiness.technicallyRenderable,
             "Level4 Ex007 selected second-pass projection cannot render");
        variant.bindingsComplete=true; // Only this separately permitted selected route.
    }
    need(seen==retained,"Level4 Ex007 all historical variants not preserved");
    return result;
}
} // namespace fathom::lesson
