#pragma once
// P37's two-case native reference is nonadmitted. This validator checks its
// immutable source packet and a separate exact agent runtime disposition.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel009Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    using J=json::Value;
    auto at=[](const J& v,const char* k)->const J&{return v.object().at(k);};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level9 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=9;limits.values=160;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","source_review_evidence","source_review_sha256",
        "domain_review_evidence","domain_review_sha256","package_sha256",
        "profile_sha256","registry_sha256","source_provenance_sha256","scope",
        "notes_fingerings_picking_timing_accepted","stable_identities_accepted","two_case_runtime_eligible"};
    std::set<std::string> actual;for(const auto& p:d.object())actual.insert(p.first);
    require(actual==fields,"Unsupported Level9 decision fields");
    require(at(d,"version").string()=="level009-first-up-down-pass2-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level9 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence","source_review_evidence",
                         "domain_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level9 authority attribution missing");
    for(const char* key:{"notes_fingerings_picking_timing_accepted","stable_identities_accepted",
                         "two_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level9 exact two-case acceptance missing");
    require(at(d,"source_review_sha256").string()=="750dcfbe975a0fdc30172adb747699c414124b0b5f516c4ec898faf7551435d5"&&
        at(d,"domain_review_sha256").string()=="2d6de9e1da24541c3491636358f94a95048b60b9167dcadcae7370ebf7e98524",
        "Level9 independent source or domain review differs");
    constexpr const char* packageSha="0043283eba195ffc2d303b6b7acbac11deb0fbff152a74749f5111609c581209";
    constexpr const char* profileSha="7fd4f3bb8a85e6ddc886aeda4dc611656dc5f818f78675631450d280fd4b0bf1";
    constexpr const char* registrySha="beb6ff70ef05799887dfdf8c151c9556dc1f90c2b42fdecc3c6aaccf1b8c1695";
    constexpr const char* provenanceSha="2bec8ccb38bf8fea21db747e828821c38d7f69d53e72022dcfa7f1e8d7565c0c";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level9 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level9 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level9 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level9 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false,"cases":[{"cell":"Level9 Exercise001 first low-E SHIFT UP P5-P7 Pass2","item_id":"fg:item:001149","module_id":"fg:module:001149","variant_ids":["fg:variant:007420","fg:variant:007421"],"events":4,"timing":"selected no-stop unaccented straight sixteenths","shift_after_note":2},{"cell":"Level9 Exercise001 first high-e SHIFT DOWN P7-P5 Pass2","item_id":"fg:item:001150","module_id":"fg:module:001150","variant_ids":["fg:variant:007422","fg:variant:007423"],"events":4,"timing":"selected no-stop unaccented straight sixteenths","shift_after_note":2}]})");
    require(at(d,"scope")==expectedScope,"Level9 decision case scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level009-ex001-first-up-down-pass2-build-only.1"&&
        at(package,"records").array().size()==2,"Level9 package/version differs");
    const auto expectedRefs=json::parse(R"(["L9-TXT1-31-45","L9-PDF1-p2","L9-TXT1-1-25","L9-PDF1-p1"])");
    const std::array<const char*,2> items{"fg:item:001149","fg:item:001150"};
    const std::array<const char*,2> modules{"fg:module:001149","fg:module:001150"};
    for(std::size_t i=0;i<items.size();++i){
        const auto& record=at(package,"records").array()[i];
        require(at(record,"id").string()==items[i]&&at(record,"module_id").string()==modules[i]&&
            at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(9)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==expectedRefs,"Level9 candidate case eligibility or identity differs");
    }
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==2&&result.variants.size()==4,
        "Level9 native source validation failed");
    const std::array<std::array<int,4>,2> frets{{{{5,6,7,8}},{{7,8,5,6}}}};
    const std::array<std::array<int,4>,2> midi{{{{45,46,47,48}},{{71,72,69,70}}}};
    const std::array<const char*,4> fingers{"1","2","1","2"};
    for(std::size_t caseIndex=0;caseIndex<2;++caseIndex){
        require(result.records[caseIndex].id==items[caseIndex]&&
            result.records[caseIndex].source.events.size()==4,"Level9 selected native case differs");
    }
    std::set<std::string> variants;
    for(auto& v:result.variants){
        const bool up=v.itemId==items[0],down=v.itemId==items[1];
        require((up||down)&&v.bindingsComplete&&v.readiness.technicallyRenderable&&
            v.validation.validReference()&&variants.insert(v.id).second,
            "Level9 selected variant unavailable or duplicated");
        const std::size_t caseIndex=up?0:1;
        const auto& source=v.source;
        require(!source.syntheticFixture&&source.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&
            source.instrument.capo==0&&source.measures.empty()&&source.events.size()==4,
            "Level9 setup or span differs");
        for(std::size_t i=0;i<4;++i){const auto& e=source.events[i];
            require(e.kind==music::Kind::Note&&e.span.onset==Rational{static_cast<std::int64_t>(i),4}&&
                e.span.duration==Rational{1,4}&&e.tones.size()==1&&e.sourceRef=="L9-TXT1-31-45",
                "Level9 event time or source reference differs");
            const auto& t=e.tones.front();
            require(t.string==(up?1:6)&&t.fret==frets[caseIndex][i]&&t.finger==fingers[i]&&
                t.midi==midi[caseIndex][i]&&t.attack==music::Attack::Picked&&
                t.tieFrom.empty()&&e.handDirection.empty(),
                "Level9 native note or unprojected stroke differs");
        }
    }
    require(variants==std::set<std::string>{"fg:variant:007420","fg:variant:007421",
                                            "fg:variant:007422","fg:variant:007423"},
        "Level9 selected variant identities differ");
    const auto sidecar=json::parse(provenance);
    for(auto& v:result.variants){
        const auto& strokes=at(at(sidecar,"variant_strokes"),v.id.c_str()).array();
        require(strokes.size()==4,"Level9 stroke sequence differs");
        const bool downStart=v.id=="fg:variant:007420"||v.id=="fg:variant:007422";
        for(std::size_t i=0;i<4;++i){
            const auto expected=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==expected,"Level9 source-authored D/U stroke differs");
            v.source.events[i].handDirection=expected;
        }
        v.validation=music::validate(v.source);
        require(v.validation.validReference(),"Level9 stroke projection failed musical validation");
    }
    return result; // Exact source reference remains separate from runtime permission.
}
} // namespace fathom::lesson
