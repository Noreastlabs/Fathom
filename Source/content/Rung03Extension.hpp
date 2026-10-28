#pragma once
// Hash-bound extension validation. Only Catalog can issue a runtime capability.
// The caller must obtain the expected disposition hash from the compiled,
// independently reviewed installed manifest, never from the decision itself.
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateRung03Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha) {
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    using J=json::Value;
    auto at=[](const J& v,const char* k)->const J&{return v.object().at(k);};
    require(expectedDispositionSha.size()==64 && content::sha256(disposition)==expectedDispositionSha,
        "Rung03 decision hash differs from installed authority pin");
    json::Limits decisionLimits;decisionLimits.bytes=16384;decisionLimits.depth=8;
    decisionLimits.values=128;decisionLimits.stringBytes=4096;
    const auto d=json::parse(disposition,decisionLimits);
    const std::set<std::string> fields{"version","status","package_sha256","profile_sha256",
        "registry_sha256","scope","authority_name","recorded_utc","decision_evidence",
        "notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"};
    std::set<std::string> actual;for(const auto& p:d.object())actual.insert(p.first);
    require(actual==fields,"Unsupported Rung03 decision fields");
    require(at(d,"version").string()=="rung03-curriculum-decision.1" &&
        at(d,"status").string()=="ACCEPTED","Rung03 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Rung03 authority attribution missing");
    for(const char* key:{"notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Rung03 exact scope acceptance missing");
    const char* packageSha="56c711c70445904243207f9cecb7eaf125d9023af040b65d2dbfe16b2d892be5";
    const char* profileSha="9f424adf09dc434c41948f5240f9d32125e35e9d463925bfb30726e1e9193e55";
    const char* registrySha="fbebd891f157eaa47688364087860313450f88daef62aa9dc15bb05af50d1000";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Rung03 frozen package changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Rung03 frozen registry changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Rung03 frozen profile changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"cell":"Level12 Rung03 B major","content_revision":1,"events":16,"fixed_authored_bpm":false,"item_id":"fg:item:001142","mastery":false,"optional_inter_cell_pause":false,"timing":"connected even eighths","variant_ids":["fg:variant:007406","fg:variant:007407"],"whole_ladder":false})");
    require(at(d,"scope")==expectedScope,"Rung03 disposition scope differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Rung03 native source validation failed");
    require(result.records.front().id=="fg:item:001142"&&result.records.front().source.events.size()==16,
        "Rung03 selected cell differs");
    std::set<std::string> variants;
    for(const auto& v:result.variants){
        require(v.itemId=="fg:item:001142"&&v.bindingsComplete&&v.readiness.technicallyRenderable&&
            v.validation.validReference(),"Rung03 selected variant unavailable");
        variants.insert(v.id);
    }
    require(variants==std::set<std::string>{"fg:variant:007406","fg:variant:007407"},
        "Rung03 selected variant identities differ");
    return result; // Native technical result only: never a LessonAdmission.
}
}
