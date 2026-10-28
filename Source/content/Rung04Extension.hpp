#pragma once
// Hash-bound extension validation. Only Catalog can issue a runtime capability.
// The caller must obtain the expected disposition hash from the compiled,
// independently reviewed installed manifest, never from the decision itself.
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateRung04Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha) {
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    using J=json::Value;
    auto at=[](const J& v,const char* k)->const J&{return v.object().at(k);};
    require(expectedDispositionSha.size()==64 && content::sha256(disposition)==expectedDispositionSha,
        "Rung04 decision hash differs from installed authority pin");
    json::Limits decisionLimits;decisionLimits.bytes=16384;decisionLimits.depth=8;
    decisionLimits.values=128;decisionLimits.stringBytes=4096;
    const auto d=json::parse(disposition,decisionLimits);
    const std::set<std::string> fields{"version","status","package_sha256","profile_sha256",
        "registry_sha256","scope","authority_name","recorded_utc","decision_evidence",
        "notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible","source_review_evidence","source_review_sha256"};
    std::set<std::string> actual;for(const auto& p:d.object())actual.insert(p.first);
    require(actual==fields,"Unsupported Rung04 decision fields");
    require(at(d,"version").string()=="rung04-curriculum-decision.1" &&
        at(d,"status").string()=="ACCEPTED","Rung04 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence","source_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Rung04 authority attribution missing");
    for(const char* key:{"notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Rung04 exact scope acceptance missing");
    require(at(d,"source_review_sha256").string()=="a717661851a45e6c3cb09b6d207e0f7b8bf079817297536b250739645ce75bce", "Rung04 independent review differs");
    const char* packageSha="a3ac97896f9fffbcbcf2d25dc1e757252cecd0737cae680caaf1a36c037f4f8a";
    const char* profileSha="045f3d99d9aae36b60d44e2539dcb1fb160ba2ef46173a49e47a175408f9a151";
    const char* registrySha="6765fa345f4178b046d4f00b67affbe881299034dc19b78d03c51bfe480eca06";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Rung04 frozen package changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Rung04 frozen registry changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Rung04 frozen profile changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"cell":"Level12 Rung04 C major","content_revision":1,"events":16,"fixed_authored_bpm":false,"item_id":"fg:item:001143","mastery":false,"optional_inter_cell_pause":false,"timing":"connected even eighths","variant_ids":["fg:variant:007408","fg:variant:007409"],"whole_ladder":false})");
    require(at(d,"scope")==expectedScope,"Rung04 disposition scope differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Rung04 native source validation failed");
    require(result.records.front().id=="fg:item:001143"&&result.records.front().source.events.size()==16,
        "Rung04 selected cell differs");
    std::set<std::string> variants;
    for(const auto& v:result.variants){
        require(v.itemId=="fg:item:001143"&&v.bindingsComplete&&v.readiness.technicallyRenderable&&
            v.validation.validReference(),"Rung04 selected variant unavailable");
        variants.insert(v.id);
    }
    require(variants==std::set<std::string>{"fg:variant:007408","fg:variant:007409"},
        "Rung04 selected variant identities differ");
    return result; // Native technical result only: never a LessonAdmission.
}
}
