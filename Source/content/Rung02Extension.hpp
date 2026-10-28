#pragma once
// Hash-bound extension validation. Only Catalog can issue a runtime capability.
// The caller must obtain the expected disposition hash from the compiled,
// independently reviewed installed manifest, never from the decision itself.
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateRung02Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha) {
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    using J=json::Value;
    auto at=[](const J& v,const char* k)->const J&{return v.object().at(k);};
    require(expectedDispositionSha.size()==64 && content::sha256(disposition)==expectedDispositionSha,
        "Rung02 decision hash differs from installed authority pin");
    json::Limits decisionLimits;decisionLimits.bytes=16384;decisionLimits.depth=8;
    decisionLimits.values=128;decisionLimits.stringBytes=4096;
    const auto d=json::parse(disposition,decisionLimits);
    const std::set<std::string> fields{"version","status","package_sha256","profile_sha256",
        "registry_sha256","scope","authority_name","recorded_utc","decision_evidence",
        "notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"};
    std::set<std::string> actual;for(const auto& p:d.object())actual.insert(p.first);
    require(actual==fields,"Unsupported Rung02 decision fields");
    require(at(d,"version").string()=="rung02-curriculum-decision.1" &&
        at(d,"status").string()=="ACCEPTED","Rung02 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Rung02 authority attribution missing");
    for(const char* key:{"notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Rung02 exact scope acceptance missing");
    const char* packageSha="3cacd1c5c3dd2059a018c475192657ec0bb4e4c600074a5fbfb657ea611cefbc";
    const char* profileSha="346db033dac7bad2d601a8b782facd48ff9feac779a930102608c0bc065bb74c";
    const char* registrySha="1541b508787cf87d61a917da89e8933fdc85aedf5f0b38abbc8d85d6be70cf87";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Rung02 frozen package changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Rung02 frozen registry changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Rung02 frozen profile changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"cell":"Level12 Rung02 Bb major","content_revision":1,"events":16,"fixed_authored_bpm":false,"item_id":"fg:item:001141","mastery":false,"optional_inter_cell_pause":false,"timing":"connected even eighths","variant_ids":["fg:variant:007404","fg:variant:007405"],"whole_ladder":false})");
    require(at(d,"scope")==expectedScope,"Rung02 disposition scope differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Rung02 native source validation failed");
    require(result.records.front().id=="fg:item:001141"&&result.records.front().source.events.size()==16,
        "Rung02 selected cell differs");
    std::set<std::string> variants;
    for(const auto& v:result.variants){
        require(v.itemId=="fg:item:001141"&&v.bindingsComplete&&v.readiness.technicallyRenderable&&
            v.validation.validReference(),"Rung02 selected variant unavailable");
        variants.insert(v.id);
    }
    require(variants==std::set<std::string>{"fg:variant:007404","fg:variant:007405"},
        "Rung02 selected variant identities differ");
    return result; // Native technical result only: never a LessonAdmission.
}
}
