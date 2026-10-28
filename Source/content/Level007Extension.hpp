#pragma once
// The P04 Build-only reference remains nonadmitted. A separate exact, typed
// Curriculum decision supplies one installed Practice capability.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel007Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    using J=json::Value;
    auto at=[](const J& v,const char* k)->const J&{return v.object().at(k);};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level7 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=8;limits.values=128;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","source_review_evidence","source_review_sha256","package_sha256",
        "profile_sha256","registry_sha256","source_provenance_sha256","scope",
        "notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"};
    std::set<std::string> actual;for(const auto& p:d.object())actual.insert(p.first);
    require(actual==fields,"Unsupported Level7 decision fields");
    require(at(d,"version").string()=="level007-relay-pass2-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level7 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence","source_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level7 authority attribution missing");
    for(const char* key:{"notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level7 exact scope acceptance missing");
    require(at(d,"source_review_sha256").string()=="56fed78303c410cdfae837ca98ad1f16924dffabfa1df3b6466259bef3e834cb",
        "Level7 independent source review differs");
    constexpr const char* packageSha="30683b0b9a1206dbe68673d9f180a1c25714d842477b475bc311d74a4b289167";
    constexpr const char* profileSha="39d3508bbe35ab708e48367bbc0ab81f6b64051cf253dea93db53a17bc07366e";
    constexpr const char* registrySha="363b475e26f544d4d2475dbc67f9c65cb3ea24f87ee2ef3e66fdd97b44e80832";
    constexpr const char* provenanceSha="83b88e008cdd7ec72615e6b6c6fa9437ebddba829810a8cf87caecb90194ea98";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level7 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level7 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level7 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level7 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"cell":"Level7 Exercise001 code1212 connected Pass2 ASCEND-DESCEND relay","content_revision":1,"events":16,"fixed_authored_bpm":false,"item_id":"fg:item:001148","mastery":false,"module_id":"fg:module:001148","timing":"selected connected straight sixteenths","variant_ids":["fg:variant:007418","fg:variant:007419"],"whole_workbook":false,"per_note_strokes":"reviewed conservative agent interpretation"})");
    require(at(d,"scope")==expectedScope,"Level7 disposition scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level007-ex001-relay-pass2-build-only.1"&&
        at(package,"records").array().size()==1,"Level7 package/version differs");
    const auto& record=at(package,"records").array().front();
    require(at(record,"id").string()=="fg:item:001148"&&at(record,"module_id").string()=="fg:module:001148"&&
        at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(7)&&
        at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean(),
        "Level7 candidate eligibility or identity differs");
    const auto expectedRefs=json::parse(R"(["L7-TXT1-30-44","L7-PDF1-p2","L7-TXT1-1-24","L7-PDF1-p1"])");
    require(at(record,"source_refs")==expectedRefs,"Level7 ordered source refs differ");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Level7 native source validation failed");
    require(result.records.front().id=="fg:item:001148"&&result.records.front().source.events.size()==16,
        "Level7 selected cell differs");
    const std::array<int,16> strings{1,3,3,5,2,4,4,6,6,4,4,2,5,3,3,1};
    const std::array<int,16> frets{5,6,5,6,5,6,5,6,5,6,5,6,5,6,5,6};
    const std::array<int,16> midi{45,56,55,65,50,61,60,70,69,61,60,51,64,56,55,46};
    const std::array<const char*,16> fingers{"1","2","1","2","1","2","1","2","1","2","1","2","1","2","1","2"};
    std::set<std::string> variants;
    for(const auto& v:result.variants){
        require(v.itemId=="fg:item:001148"&&v.bindingsComplete&&v.readiness.technicallyRenderable&&
            v.validation.validReference(),"Level7 selected variant unavailable");
        variants.insert(v.id);
        const auto& source=v.source;
        require(!source.syntheticFixture&&source.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&
            source.instrument.capo==0&&source.measures.empty()&&source.events.size()==16,
            "Level7 setup or span differs");
        for(std::size_t i=0;i<16;++i){const auto& e=source.events[i];
            require(e.kind==music::Kind::Note&&e.span.onset==Rational{static_cast<std::int64_t>(i),4}&&
                e.span.duration==Rational{1,4}&&e.tones.size()==1&&e.sourceRef=="L7-TXT1-30-44",
                "Level7 event time or source reference differs");
            const auto& t=e.tones.front();
            require(t.string==strings[i]&&t.fret==frets[i]&&t.finger==fingers[i]&&t.midi==midi[i]&&
                t.attack==music::Attack::Picked&&t.tieFrom.empty()&&e.handDirection.empty(),
                "Level7 native note or unprojected stroke differs");
        }
    }
    require(variants==std::set<std::string>{"fg:variant:007418","fg:variant:007419"},
        "Level7 selected variant identities differ");
    // P35 reviewed the source's both-start alternate cycle across the connected relay as a conservative agent interpretation. The native packet
    // leaves note-level strokes blank; the hash-bound sidecar supplies them.
    const auto sidecar=json::parse(provenance);
    for(auto& v:result.variants){
        const auto& strokes=at(at(sidecar,"variant_strokes"),v.id.c_str()).array();
        require(strokes.size()==16,"Level7 stroke sequence differs");
        const bool down=v.id=="fg:variant:007418";
        for(std::size_t i=0;i<16;++i){
            const auto expected=((i%2==0)==down)?"D":"U";
            require(strokes[i].string()==expected,"Level7 sidecar alternate stroke differs");
            v.source.events[i].handDirection=expected;
        }
        v.validation=music::validate(v.source);
        require(v.validation.validReference(),"Level7 stroke projection failed musical validation");
    }
    return result; // Native reference validity alone is not runtime admission.
}
} // namespace fathom::lesson
