#pragma once
// The P04 Build-only reference remains nonadmitted. A separate exact, typed
// Curriculum decision supplies one installed Practice capability.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel010Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    using J=json::Value;
    auto at=[](const J& v,const char* k)->const J&{return v.object().at(k);};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level10 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=8;limits.values=128;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","source_review_evidence","source_review_sha256","package_sha256",
        "profile_sha256","registry_sha256","source_provenance_sha256","scope",
        "notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"};
    std::set<std::string> actual;for(const auto& p:d.object())actual.insert(p.first);
    require(actual==fields,"Unsupported Level10 decision fields");
    require(at(d,"version").string()=="level010-first-odd-shift-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level10 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence","source_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level10 authority attribution missing");
    for(const char* key:{"notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level10 exact scope acceptance missing");
    require(at(d,"source_review_sha256").string()=="2c6ce143a9fad6b721866895aadd912c4b4ce41be78b485bc8a83c3f0d6f6150",
        "Level10 independent source review differs");
    constexpr const char* packageSha="b37a9a1194ba183522d45075388010f08bbb923c8975bb67401e26917eaa2b83";
    constexpr const char* profileSha="605985e9d97c97fa0bda3399c960eb92d28752c5cf19e10c0cb4b0855abbfead";
    constexpr const char* registrySha="88f8d5c394fd04cb0868b2356f451c3fb414013c8eb81abbb2e12d6ab1690c6b";
    constexpr const char* provenanceSha="4de5fead1c2591de82b06ad1a4a52c462481accf1c597bb9e8562f7705c2793b";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level10 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level10 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level10 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level10 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"cell":"Level10 Exercise001 Mode A first low-E P5-P7 SHIFT UP PASS2","content_revision":1,"events":4,"fixed_authored_bpm":false,"item_id":"fg:item:001147","mastery":false,"module_id":"fg:module:001147","timing":"connected straight sixteenths","variant_ids":["fg:variant:007416","fg:variant:007417"],"whole_workbook":false})");
    require(at(d,"scope")==expectedScope,"Level10 disposition scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level010-ex001-first-odd-shift-build-only.1"&&
        at(package,"records").array().size()==1,"Level10 package/version differs");
    const auto& record=at(package,"records").array().front();
    require(at(record,"id").string()=="fg:item:001147"&&at(record,"module_id").string()=="fg:module:001147"&&
        at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(10)&&
        at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean(),
        "Level10 candidate eligibility or identity differs");
    const auto expectedRefs=json::parse(R"(["L10-TXT1-39-53","L10-PDF1-p2","L10-TXT1-1-33","L10-PDF1-p1"])");
    require(at(record,"source_refs")==expectedRefs,"Level10 ordered source refs differ");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Level10 native source validation failed");
    require(result.records.front().id=="fg:item:001147"&&result.records.front().source.events.size()==4,
        "Level10 selected cell differs");
    const std::array<int,4> frets{5,6,5,8},midi{45,46,45,48};
    const std::array<const char*,4> fingers{"1","2","1","2"};
    std::set<std::string> variants;
    for(const auto& v:result.variants){
        require(v.itemId=="fg:item:001147"&&v.bindingsComplete&&v.readiness.technicallyRenderable&&
            v.validation.validReference(),"Level10 selected variant unavailable");
        variants.insert(v.id);
        const auto& source=v.source;
        require(!source.syntheticFixture&&source.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&
            source.instrument.capo==0&&source.measures.empty()&&source.events.size()==4,
            "Level10 setup or span differs");
        for(std::size_t i=0;i<4;++i){const auto& e=source.events[i];
            require(e.kind==music::Kind::Note&&e.span.onset==Rational{static_cast<std::int64_t>(i),4}&&
                e.span.duration==Rational{1,4}&&e.tones.size()==1&&e.sourceRef=="L10-TXT1-39-53",
                "Level10 event time or source reference differs");
            const auto& t=e.tones.front();
            require(t.string==1&&t.fret==frets[i]&&t.finger==fingers[i]&&t.midi==midi[i]&&
                t.attack==music::Attack::Picked&&t.tieFrom.empty()&&e.handDirection.empty(),
                "Level10 native note or unprojected stroke differs");
        }
    }
    require(variants==std::set<std::string>{"fg:variant:007416","fg:variant:007417"},
        "Level10 selected variant identities differ");
    // P25 reviewed the source's both-start alternate cycle across the late shift. The native packet
    // leaves note-level strokes blank; the hash-bound sidecar supplies them.
    const auto sidecar=json::parse(provenance);
    for(auto& v:result.variants){
        const auto& strokes=at(at(sidecar,"variant_strokes"),v.id.c_str()).array();
        require(strokes.size()==4,"Level10 stroke sequence differs");
        const bool down=v.id=="fg:variant:007416";
        for(std::size_t i=0;i<4;++i){
            const auto expected=((i%2==0)==down)?"D":"U";
            require(strokes[i].string()==expected,"Level10 sidecar alternate stroke differs");
            v.source.events[i].handDirection=expected;
        }
        v.validation=music::validate(v.source);
        require(v.validation.validReference(),"Level10 stroke projection failed musical validation");
    }
    return result; // Native reference validity alone is not runtime admission.
}
} // namespace fathom::lesson
