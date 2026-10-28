#pragma once
// A source-valid candidate gains a runtime capability only through this
// separately pinned, typed Curriculum disposition and the Catalog loader.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel006Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    using J=json::Value;
    auto at=[](const J& v,const char* k)->const J&{return v.object().at(k);};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level6 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=8;limits.values=128;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","source_review_evidence","source_review_sha256","package_sha256",
        "profile_sha256","registry_sha256","source_provenance_sha256","scope",
        "notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"};
    std::set<std::string> actual;for(const auto& p:d.object())actual.insert(p.first);
    require(actual==fields,"Unsupported Level6 decision fields");
    require(at(d,"version").string()=="level006-first-cell-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level6 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence","source_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level6 authority attribution missing");
    for(const char* key:{"notes_fingerings_picking_timing_accepted","stable_identities_accepted","single_cell_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level6 exact scope acceptance missing");
    require(at(d,"source_review_sha256").string()=="cddf0da9b5700e0a2f2d878fc9643dd3ac4f8ce3ea2cd4f8072d1477590b10e0",
        "Level6 independent review differs");
    constexpr const char* packageSha="81a0acaded38ea742a0d8c1a5b0fbde79050c08252238c9e217e5bc145197778";
    constexpr const char* profileSha="5cd11742b74acbf510e9f0afd27797182de5f91056b7b820a7d4bd1f66d31a7b";
    constexpr const char* registrySha="682bbcd95fb8826fbd9faa78517f7e0c7ddd529da90856f835a2afd77b0f5f73";
    constexpr const char* provenanceSha="64d616620b027c4d4b9f5c06b045245903a9ec018c71d112d2891539d8b82d37";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,"Level6 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&input.expectedProfileSha256==profileSha,"Level6 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,"Level6 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,"Level6 event provenance changed");
    const auto expectedScope=json::parse(R"({"accent_policy":"source_unspecified","automatic_credit":false,"cell":"Level6 Exercise001 ModeA first ascending separated E-D pair","content_revision":1,"events":4,"fixed_authored_bpm":false,"fixed_meter":false,"item_id":"fg:item:001144","mastery":false,"module_id":"fg:module:001144","timing":"TXT-only selected straight sixteenths","variant_ids":["fg:variant:007410","fg:variant:007411"],"whole_workbook":false})");
    require(at(d,"scope")==expectedScope,"Level6 disposition scope differs");
    const auto sourcePackage=json::parse(input.package);
    require(at(sourcePackage,"content_version").string()=="curriculum-v1-level006-ex001-first-cell-build-only.2"&&
        at(sourcePackage,"records").array().size()==1,"Level6 package/version differs");
    const auto& record=at(sourcePackage,"records").array().front();
    require(at(record,"id").string()=="fg:item:001144"&&at(record,"module_id").string()=="fg:module:001144"&&
        at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(6)&&
        at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean(),"Level6 candidate eligibility or identity differs");
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
        "Level6 native source validation failed");
    require(result.records.front().id=="fg:item:001144"&&result.records.front().source.events.size()==4,
        "Level6 selected cell differs");
    const std::array<int,4> strings{1,1,1,3},frets{5,6,5,6},midi{45,46,45,56};
    const std::array<const char*,4> fingers{"1","2","1","2"};
    std::set<std::string> variants;
    for(const auto& v:result.variants){
        require(v.itemId=="fg:item:001144"&&v.bindingsComplete&&v.readiness.technicallyRenderable&&v.validation.validReference(),
            "Level6 selected variant unavailable");
        variants.insert(v.id);
        const auto& source=v.source;
        require(!source.syntheticFixture&&source.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&
            source.instrument.capo==0&&source.measures.empty()&&source.events.size()==4,"Level6 setup or span differs");
        for(std::size_t i=0;i<4;++i){const auto& e=source.events[i];
            require(e.kind==music::Kind::Note&&e.span.onset==Rational{static_cast<std::int64_t>(i),4}&&
                e.span.duration==Rational{1,4}&&e.tones.size()==1&&e.sourceRef=="L6-TXT1-34-41",
                "Level6 event time or source reference differs");
            const auto& t=e.tones.front();
            require(t.string==strings[i]&&t.fret==frets[i]&&t.midi==midi[i]&&t.finger==fingers[i]&&
                t.attack==music::Attack::Picked&&t.tieFrom.empty()&&e.handDirection.empty(),
                "Level6 native event note or unprojected direction differs");
        }
    }
    require(variants==std::set<std::string>{"fg:variant:007410","fg:variant:007411"},
        "Level6 selected variant identities differ");
    // Native candidate projection preserves the notes but leaves note-level pick
    // direction blank. The reviewed sidecar supplies the bounded D/U cycle.
    const auto sidecar=json::parse(provenance);
    for(auto& v:result.variants){
        const auto& strokes=at(at(sidecar,"variant_strokes"),v.id.c_str()).array();
        require(strokes.size()==4,"Level6 stroke sequence differs");
        const bool down=v.id=="fg:variant:007410";
        for(std::size_t i=0;i<4;++i){
            const auto expected=((i%2==0)==down)?"D":"U";
            require(strokes[i].string()==expected,"Level6 sidecar alternate stroke differs");
            v.source.events[i].handDirection=expected;
        }
        v.validation=music::validate(v.source);
        require(v.validation.validReference(),"Level6 stroke projection failed musical validation");
    }
    return result; // Native reference validity is not itself a runtime permission.
}
}
