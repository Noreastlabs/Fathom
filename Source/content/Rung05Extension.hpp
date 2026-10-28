#pragma once
// The Build-only source candidate remains nonadmitted. Catalog uses this
// separately pinned decision and exact native projection to issue one cell.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateRung05Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha) {
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    using J=json::Value;
    auto at=[](const J& v,const char* k)->const J&{return v.object().at(k);};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Rung05 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=8;limits.values=128;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","package_sha256","profile_sha256",
        "registry_sha256","scope","authority_name","recorded_utc","decision_evidence",
        "notes_fingerings_picking_timing_accepted","stable_identities_accepted",
        "single_cell_runtime_eligible","source_review_evidence","source_review_sha256"};
    std::set<std::string> actual;for(const auto& p:d.object())actual.insert(p.first);
    require(actual==fields,"Unsupported Rung05 decision fields");
    require(at(d,"version").string()=="rung05-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Rung05 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence","source_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Rung05 authority attribution missing");
    for(const char* key:{"notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Rung05 exact scope acceptance missing");
    require(at(d,"source_review_sha256").string()=="13961516b857c34cfc0d9c9827c3de7d39de1b9f43d6773e2358cecea10a7185",
        "Rung05 independent review differs");
    constexpr const char* packageSha="7163016180690f4c6432caf5586a59c2fe07815681da554c6f8d7f1c4ed64ced";
    constexpr const char* profileSha="dacdea4825000f6195b7348863f79904a5ecc78109120408aebf1d8b6df9fd62";
    constexpr const char* registrySha="07eb0fd632561ad862da5b350d0f2c81b85863aae4ada33f8530e5a5a4c67ac1";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Rung05 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Rung05 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Rung05 frozen registry changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"cell":"Level12 Rung05 Db major","content_revision":1,"events":16,"fixed_authored_bpm":false,"item_id":"fg:item:001145","mastery":false,"module_id":"fg:module:001145","optional_inter_cell_pause":false,"timing":"connected even eighths","variant_ids":["fg:variant:007412","fg:variant:007413"],"whole_ladder":false})");
    require(at(d,"scope")==expectedScope,"Rung05 disposition scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level012-rung05-local-build-only.1"&&
        at(package,"records").array().size()==1,"Rung05 package/version differs");
    const auto& record=at(package,"records").array().front();
    require(at(record,"id").string()=="fg:item:001145"&&
        at(record,"module_id").string()=="fg:module:001145"&&
        at(record,"content_revision")==J::fromInteger(1)&&
        at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean(),
        "Rung05 candidate eligibility or identity differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Rung05 native source validation failed");
    require(result.records.front().id=="fg:item:001145"&&result.records.front().source.events.size()==16,
        "Rung05 selected cell differs");
    const std::array<int,16> midi{49,51,53,54,56,58,60,61,61,60,58,56,54,53,51,49};
    std::set<std::string> variants;
    for(const auto& v:result.variants){
        require(v.itemId=="fg:item:001145"&&v.bindingsComplete&&v.readiness.technicallyRenderable&&
            v.validation.validReference(),"Rung05 selected variant unavailable");
        variants.insert(v.id);
        const auto& source=v.source;
        require(!source.syntheticFixture&&source.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&
            source.instrument.capo==0&&source.measures.empty()&&source.events.size()==16,
            "Rung05 setup or span differs");
        for(std::size_t i=0;i<16;++i){const auto& e=source.events[i];
            require(e.kind==music::Kind::Note&&e.span.onset==Rational{static_cast<std::int64_t>(i),2}&&
                e.span.duration==Rational{1,2}&&e.tones.size()==1&&
                e.sourceRef=="L12-TXT1-98-109","Rung05 event time or source reference differs");
            const auto& t=e.tones.front();
            require(t.midi==midi[i]&&t.attack==music::Attack::Picked&&t.tieFrom.empty(),
                "Rung05 event pitch or articulation differs");
        }
    }
    require(variants==std::set<std::string>{"fg:variant:007412","fg:variant:007413"},
        "Rung05 selected variant identities differ");
    return result; // Native reference validity alone is never runtime admission.
}
} // namespace fathom::lesson
