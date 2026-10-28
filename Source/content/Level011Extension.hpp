#pragma once
// P41's two-case native reference is nonadmitted. This validator checks its
// immutable source packet and a separate exact agent runtime disposition.
#include "content/Canonical.hpp"
#include <array>
#include <set>
#include <stdexcept>

namespace fathom::lesson {
inline content::Result validateLevel011Extension(const content::Input& input,
    const std::string& disposition, const std::string& expectedDispositionSha,
    const std::string& provenance) {
    auto require=[](bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);};
    using J=json::Value;
    auto at=[](const J& v,const char* k)->const J&{return v.object().at(k);};
    require(expectedDispositionSha.size()==64&&content::sha256(disposition)==expectedDispositionSha,
        "Level11 decision hash differs from installed authority pin");
    json::Limits limits;limits.bytes=16384;limits.depth=9;limits.values=160;limits.stringBytes=4096;
    const auto d=json::parse(disposition,limits);
    const std::set<std::string> fields{"version","status","authority_name","recorded_utc",
        "decision_evidence","source_review_evidence","source_review_sha256",
        "domain_review_evidence","domain_review_sha256","package_sha256",
        "profile_sha256","registry_sha256","source_provenance_sha256","scope",
        "notes_fingerings_picking_timing_accepted","stable_identities_accepted","two_case_runtime_eligible"};
    std::set<std::string> actual;for(const auto& p:d.object())actual.insert(p.first);
    require(actual==fields,"Unsupported Level11 decision fields");
    require(at(d,"version").string()=="level011-first-up-down-pass2-curriculum-decision.1"&&
        at(d,"status").string()=="ACCEPTED","Level11 Curriculum disposition is not accepted");
    for(const char* key:{"authority_name","recorded_utc","decision_evidence","source_review_evidence",
                         "domain_review_evidence"})
        require(at(d,key).isString()&&!at(d,key).string().empty(),"Level11 authority attribution missing");
    for(const char* key:{"notes_fingerings_picking_timing_accepted","stable_identities_accepted",
                         "two_case_runtime_eligible"})
        require(at(d,key).isBool()&&at(d,key).boolean(),"Level11 exact two-case acceptance missing");
    require(at(d,"source_review_sha256").string()=="fdf27f842a5cfd3bc47204b9bcd17e8838f0fd965a90607a488cafb4fd41ece4"&&
        at(d,"domain_review_sha256").string()=="1bbe91745972298e6be200a02b53d0290c9f798944760731257385f0e5cd78db",
        "Level11 independent source or domain review differs");
    constexpr const char* packageSha="d818d20afb8d15e0bfa53c91284be18ebdc1f09d300acc7f63136f78f8a3f91a";
    constexpr const char* profileSha="6539ff768be135afcabf4c6b17e58cf07ae3b7ad5eae5f4ff757788ceffe1ac5";
    constexpr const char* registrySha="826c5cf5078084fb12b726c6561a5e0c96fb6f06ddb081a03881a825d6d8ef7c";
    constexpr const char* provenanceSha="9e36ea049875e8fea6afb2aca3ce6fd2375a965b3c749006ea5f6f80ca0e52fa";
    require(content::sha256(input.package)==packageSha&&at(d,"package_sha256").string()==packageSha,
        "Level11 frozen package changed");
    require(content::sha256(input.profile)==profileSha&&at(d,"profile_sha256").string()==profileSha&&
        input.expectedProfileSha256==profileSha,"Level11 frozen profile changed");
    require(content::sha256(input.registry)==registrySha&&at(d,"registry_sha256").string()==registrySha,
        "Level11 frozen registry changed");
    require(content::sha256(provenance)==provenanceSha&&at(d,"source_provenance_sha256").string()==provenanceSha,
        "Level11 event provenance changed");
    const auto expectedScope=json::parse(R"({"automatic_credit":false,"content_revision":1,"fixed_authored_bpm":false,"mastery":false,"whole_workbook":false,"cases":[{"cell":"Level11 Exercise001 first low-E SHIFT UP P5-P7-P9 Pass2","item_id":"fg:item:001151","module_id":"fg:module:001151","variant_ids":["fg:variant:007424","fg:variant:007425"],"events":4,"timing":"selected connected unaccented straight sixteenths","shift_after_notes":[1,3]},{"cell":"Level11 Exercise001 first high-e SHIFT DOWN P9-P7-P5 Pass2","item_id":"fg:item:001152","module_id":"fg:module:001152","variant_ids":["fg:variant:007426","fg:variant:007427"],"events":4,"timing":"selected connected unaccented straight sixteenths","shift_after_notes":[1,3]}]})");
    require(at(d,"scope")==expectedScope,"Level11 decision case scope differs");
    const auto package=json::parse(input.package);
    require(at(package,"content_version").string()=="curriculum-v1-level011-ex001-first-up-down-pass2-build-only.1"&&
        at(package,"records").array().size()==2,"Level11 package/version differs");
    const auto expectedRefs=json::parse(R"(["L11-TXT1-51-57","L11-PDF1-p2","L11-TXT1-1-41","L11-PDF1-p1"])");
    const std::array<const char*,2> items{"fg:item:001151","fg:item:001152"};
    const std::array<const char*,2> modules{"fg:module:001151","fg:module:001152"};
    for(std::size_t i=0;i<items.size();++i){
        const auto& record=at(package,"records").array()[i];
        require(at(record,"id").string()==items[i]&&at(record,"module_id").string()==modules[i]&&
            at(record,"content_revision")==J::fromInteger(1)&&at(record,"legacy_level")==J::fromInteger(11)&&
            at(record,"runtime_eligible").isBool()&&!at(record,"runtime_eligible").boolean()&&
            at(record,"source_refs")==expectedRefs,"Level11 candidate case eligibility or identity differs");
    }
    auto result=content::validate(input);
    require(result.validReference&&result.exitCode==2&&result.records.size()==2&&result.variants.size()==4,
        "Level11 native source validation failed");
    const std::array<std::array<int,4>,2> frets{{{{5,8,7,10}},{{9,8,7,6}}}};
    const std::array<std::array<int,4>,2> midi{{{{45,48,47,50}},{{73,72,71,70}}}};
    const std::array<const char*,4> fingers{"1","2","1","2"};
    for(std::size_t caseIndex=0;caseIndex<2;++caseIndex){
        require(result.records[caseIndex].id==items[caseIndex]&&
            result.records[caseIndex].source.events.size()==4,"Level11 selected native case differs");
    }
    std::set<std::string> variants;
    for(auto& v:result.variants){
        const bool up=v.itemId==items[0],down=v.itemId==items[1];
        require((up||down)&&v.bindingsComplete&&v.readiness.technicallyRenderable&&
            v.validation.validReference()&&variants.insert(v.id).second,
            "Level11 selected variant unavailable or duplicated");
        const std::size_t caseIndex=up?0:1;
        const auto& source=v.source;
        require(!source.syntheticFixture&&source.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&
            source.instrument.capo==0&&source.measures.empty()&&source.events.size()==4,
            "Level11 setup or span differs");
        for(std::size_t i=0;i<4;++i){const auto& e=source.events[i];
            require(e.kind==music::Kind::Note&&e.span.onset==Rational{static_cast<std::int64_t>(i),4}&&
                e.span.duration==Rational{1,4}&&e.tones.size()==1&&e.sourceRef=="L11-TXT1-51-57",
                "Level11 event time or source reference differs");
            const auto& t=e.tones.front();
            require(t.string==(up?1:6)&&t.fret==frets[caseIndex][i]&&t.finger==fingers[i]&&
                t.midi==midi[caseIndex][i]&&t.attack==music::Attack::Picked&&
                t.tieFrom.empty()&&e.handDirection.empty(),
                "Level11 native note or unprojected stroke differs");
        }
    }
    require(variants==std::set<std::string>{"fg:variant:007424","fg:variant:007425",
                                            "fg:variant:007426","fg:variant:007427"},
        "Level11 selected variant identities differ");
    const auto sidecar=json::parse(provenance);
    const std::array<std::array<const char*,4>,2> frames{{{{"P5","P7","P7","P9"}},
        {{"P9","P7","P7","P5"}}}};
    for(std::size_t caseIndex=0;caseIndex<2;++caseIndex)
        for(std::size_t i=0;i<4;++i){
            const auto key=std::string(items[caseIndex])+":event:000"+std::to_string(i+1);
            const auto& evidence=at(at(sidecar,"events"),key.c_str());
            require(at(evidence,"frame").string()==frames[caseIndex][i]&&
                at(evidence,"landing_note").isBool()&&
                at(evidence,"landing_note").boolean()==(i==1||i==3)&&
                at(evidence,"shift_boundary_after_notes")==json::parse("[1,3]")&&
                at(evidence,"source_txt_ref").string()=="L11-TXT1-51-57"&&
                at(evidence,"source_pdf_ref").string()=="L11-PDF1-p2"&&
                at(evidence,"timing_ref").string()=="L11-TXT1-1-41",
                "Level11 source frame, landing, shift or timing provenance differs");
        }
    for(auto& v:result.variants){
        const auto& strokes=at(at(sidecar,"variant_strokes"),v.id.c_str()).array();
        require(strokes.size()==4,"Level11 stroke sequence differs");
        const bool downStart=v.id=="fg:variant:007424"||v.id=="fg:variant:007426";
        for(std::size_t i=0;i<4;++i){
            const auto expected=((i%2==0)==downStart)?"D":"U";
            require(strokes[i].string()==expected,"Level11 source-authored D/U stroke differs");
            v.source.events[i].handDirection=expected;
        }
        v.validation=music::validate(v.source);
        require(v.validation.validReference(),"Level11 stroke projection failed musical validation");
    }
    return result; // Exact source reference remains separate from runtime permission.
}
} // namespace fathom::lesson
