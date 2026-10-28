#pragma once
// The P04 Build-only reference remains nonadmitted. A separate exact, typed
// Curriculum decision supplies one installed Practice capability.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel008Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    using J=json::Value;
    auto at=[](const J& v,const char* k)->const J&{return v.object().at(k);};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level8 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=8;limits.values=128;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","source_review_evidence","source_review_sha256","package_sha256",
        "profile_sha256","registry_sha256","source_provenance_sha256","scope",
        "notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"};
    std::set<std::string> actual;for(const auto& p:d.object())actual.insert(p.first);
    require(actual==fields,"Unsupported Level8 decision fields");
    require(at(d,"version").string()=="level008-first-shift-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level8 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence","source_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level8 authority attribution missing");
    for(const char* key:{"notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level8 exact scope acceptance missing");
    require(at(d,"source_review_sha256").string()=="732cc285a34b7cf560bf92d8268d57555bff97a33a2141eb7da7caec64460698",
        "Level8 independent source review differs");
    constexpr const char* packageSha="0d1fc7cdf70aa0fd75a40b3d952f935adc46cb6d9ad6e6abd168499a9a91c420";
    constexpr const char* profileSha="aa45e342f0880e4a479c27907ed919bd075ddaa142743c08f0dd3dca53965b3a";
    constexpr const char* registrySha="e47fb4d4904c80e641d9ffc7f9289bb6f3e1c32198fd683cbc3c630e3259e2e7";
    constexpr const char* provenanceSha="a1a48ad858efa603245f542532d3126f9a71e8a57b764730e1ff166b16c19db2";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level8 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level8 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level8 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level8 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"cell":"Level8 Exercise001 first low-E P5-P7 SHIFT UP PASS2","content_revision":1,"events":8,"fixed_authored_bpm":false,"item_id":"fg:item:001146","mastery":false,"module_id":"fg:module:001146","timing":"connected straight sixteenths","variant_ids":["fg:variant:007414","fg:variant:007415"],"whole_workbook":false})");
    require(at(d,"scope")==expectedScope,"Level8 disposition scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level008-ex001-first-shift-build-only.1"&&
        at(package,"records").array().size()==1,"Level8 package/version differs");
    const auto& record=at(package,"records").array().front();
    require(at(record,"id").string()=="fg:item:001146"&&at(record,"module_id").string()=="fg:module:001146"&&
        at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(8)&&
        at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean(),
        "Level8 candidate eligibility or identity differs");
    const auto expectedRefs=json::parse(R"(["L8-TXT1-31-38","L8-PDF1-p2","L8-TXT1-1-25","L8-PDF1-p1"])");
    require(at(record,"source_refs")==expectedRefs,"Level8 ordered source refs differ");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Level8 native source validation failed");
    require(result.records.front().id=="fg:item:001146"&&result.records.front().source.events.size()==8,
        "Level8 selected cell differs");
    const std::array<int,8> frets{5,6,5,6,7,8,7,8},midi{45,46,45,46,47,48,47,48};
    const std::array<const char*,8> fingers{"1","2","1","2","1","2","1","2"};
    std::set<std::string> variants;
    for(const auto& v:result.variants){
        require(v.itemId=="fg:item:001146"&&v.bindingsComplete&&v.readiness.technicallyRenderable&&
            v.validation.validReference(),"Level8 selected variant unavailable");
        variants.insert(v.id);
        const auto& source=v.source;
        require(!source.syntheticFixture&&source.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&
            source.instrument.capo==0&&source.measures.empty()&&source.events.size()==8,
            "Level8 setup or span differs");
        for(std::size_t i=0;i<8;++i){const auto& e=source.events[i];
            require(e.kind==music::Kind::Note&&e.span.onset==Rational{static_cast<std::int64_t>(i),4}&&
                e.span.duration==Rational{1,4}&&e.tones.size()==1&&e.sourceRef=="L8-TXT1-31-38",
                "Level8 event time or source reference differs");
            const auto& t=e.tones.front();
            require(t.string==1&&t.fret==frets[i]&&t.finger==fingers[i]&&t.midi==midi[i]&&
                t.attack==music::Attack::Picked&&t.tieFrom.empty()&&e.handDirection.empty(),
                "Level8 native note or unprojected stroke differs");
        }
    }
    require(variants==std::set<std::string>{"fg:variant:007414","fg:variant:007415"},
        "Level8 selected variant identities differ");
    // P05 reviewed the source's both-start alternate cycle. The native packet
    // leaves note-level strokes blank; the hash-bound sidecar supplies them.
    const auto sidecar=json::parse(provenance);
    for(auto& v:result.variants){
        const auto& strokes=at(at(sidecar,"variant_strokes"),v.id.c_str()).array();
        require(strokes.size()==8,"Level8 stroke sequence differs");
        const bool down=v.id=="fg:variant:007414";
        for(std::size_t i=0;i<8;++i){
            const auto expected=((i%2==0)==down)?"D":"U";
            require(strokes[i].string()==expected,"Level8 sidecar alternate stroke differs");
            v.source.events[i].handDirection=expected;
        }
        v.validation=music::validate(v.source);
        require(v.validation.validReference(),"Level8 stroke projection failed musical validation");
    }
    return result; // Native reference validity alone is not runtime admission.
}
} // namespace fathom::lesson
