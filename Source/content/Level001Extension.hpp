#pragma once
// Finite, nonadmitting Level 1 realization guard. Generic Canonical remains workbook-neutral.
#include "content/Canonical.hpp"
#include <algorithm>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>

namespace fathom::lesson {
struct Level001StrokeFault {
    std::string variantId;
    std::size_t contactIndex{}; // zero-based projected contact; diagnostic CLI input only
    std::string emitted;
};

inline content::Result validateLevel001Extension(const content::Input& input,
    const std::optional<Level001StrokeFault>& strokeFault = std::nullopt,
    content::Limits limits = {}) {
    using J=json::Value;
    using O=J::Object;
    using A=J::Array;
    limits.json.values=1100000; // Same bounded monolithic-reference budget as content_validate.
    auto result=content::validate(input,limits);
    auto& report=result.report.object();
    if(!result.validReference) {
        report["finite_level001"]=O{{"status","generic_refusal"},{"contract_checked",false}};
        return result;
    }
    constexpr const char* packageSha="64c155482b5c3886de5a0669c661d3b38e4d0c9ce5dfa713bad362ffe4511082";
    constexpr const char* profileSha="b76c298763c8c88e211fb5517f950ffca09b22a58c9d767e7616fe43759ee3ba";
    constexpr const char* registrySha="07c7e371d7a7900fbfb98bc28ec33810f3428db8e7a1f77dd1c80b7f202b397f";
    constexpr const char* contractSha="cea318ba4a1c8e54371eccb40c29729e1104d163e922a41665317319055f9646";
    const auto readPinned=[&](const char* path,const char* expected){
        const auto bytes=content::readBounded(input.sourceRoot/path,limits.json.bytes);
        if(content::sha256(bytes)!=expected)throw std::runtime_error(std::string("Level1 frozen authority drift: ")+path);
        return bytes;
    };
    const auto authorityPackageBytes=readPinned("Build/manager-resume-r01/level001-whole-candidate-r01/candidate-r01/package.json",packageSha);
    const auto authorityProfileBytes=readPinned("Build/manager-resume-r01/level001-final-profile-r01/expected-profile.final.json",profileSha);
    readPinned("Build/manager-resume-r01/level001-whole-candidate-r01/candidate-r01/identity-registry.json",registrySha);
    content::verifyArchivedEvidence(input,"Results/manager-resume-r01/level001-whole-contract/realization-contract.md",contractSha);
    const auto& at=[](const J& value,const char* key)->const J&{return value.object().at(key);};
    const auto authority=json::parse(authorityPackageBytes,limits.json);
    const auto authorityProfile=json::parse(authorityProfileBytes,limits.json);
    const auto package=json::parse(input.package,limits.json);
    const auto profile=json::parse(input.profile,limits.json);
    std::size_t finiteIssues=0;
    const auto issue=[&](const std::string& code,const std::string& item,
        const std::string& variant,const std::string& event,const std::string& field,const std::string& message){
        ++finiteIssues;
        report.at("issues").array().emplace_back(O{{"code",code},{"event",event},{"field",field},
            {"message",message},{"record",item},{"severity","contradiction"},{"source",variant}});
    };
    const auto& authorityRecords=at(authority,"records").array();
    const auto& records=at(package,"records").array();
    if(records.size()!=108||authorityRecords.size()!=108||result.records.size()!=108||result.variants.size()!=648)
        issue("LEVEL001_COVERAGE","","","","/records","Finite Level1 requires 108 records and 648 variants");
    // Only the two explicitly new variants' membership and quarter-unit field may differ
    // from the reviewed bytes. This lets causal mutants reach semantic guards while
    // pinning every old event, four old variants, source reference, identity and rubric.
    J normalized=package;
    if(records.size()==authorityRecords.size()) {
        for(std::size_t ri=0;ri<records.size();++ri) {
            auto& candidateVariants=normalized.object().at("records").array()[ri].object().at("variants").array();
            const auto& pinnedVariants=at(authorityRecords[ri],"variants").array();
            if(candidateVariants.size()!=6||pinnedVariants.size()!=6)continue;
            for(std::size_t vi=4;vi<6;++vi) {
                candidateVariants[vi].object().at("event_ids")=at(pinnedVariants[vi],"event_ids");
                candidateVariants[vi].object().at("grouping").object().at("beat_unit_q")=
                    at(at(pinnedVariants[vi],"grouping"),"beat_unit_q");
            }
        }
    }
    if(normalized!=authority)
        issue("LEVEL001_PACKAGE_AUTHORITY","","","","/package",
            "Candidate differs outside finite new-variant membership or beat-unit fields");
    J normalizedProfile=profile;
    normalizedProfile.object().at("reference_package")=at(authorityProfile,"reference_package");
    if(normalizedProfile!=authorityProfile)
        issue("LEVEL001_PROFILE_AUTHORITY","","","","/profile",
            "Profile differs outside its rebound reference_package");
    if(content::sha256(input.registry)!=registrySha)
        issue("LEVEL001_REGISTRY_AUTHORITY","","","","/registry","Finite registry differs from reviewed bytes");
    if(at(profile,"reference_package")!=package)
        issue("LEVEL001_PROFILE_REBOUND","","","","/profile/reference_package",
            "Profile does not bind exact candidate package");
    std::size_t checkedNew=0,checkedOld=0,projectedContacts=0;
    bool faultApplied=false;
    for(std::size_t ri=0;ri<std::min(records.size(),authorityRecords.size());++ri) {
        const auto& record=records[ri];const auto& sourceEvents=at(record,"events").array();
        const auto& variants=at(record,"variants").array();
        const auto item=at(record,"id").string();
        if(sourceEvents.size()!=48||variants.size()!=6) {
            issue("LEVEL001_RECORD_SHAPE",item,"","","/records","Each Level1 item requires 48 original contacts and six variants");
            continue;
        }
        if(at(record,"runtime_eligible")!=J(false))
            issue("LEVEL001_NOT_ADMITTED",item,"","","/runtime_eligible","Candidate must remain runtime-ineligible");
        for(const auto& sourceEvent:sourceEvents)
            if(!at(sourceEvent,"onset_q").null()||!at(sourceEvent,"duration_q").null())
                issue("LEVEL001_SOURCE_TIME",item,"",at(sourceEvent,"event_id").string(),"/events",
                    "Original source time must remain unresolved; quarter grid is Fathom-authored");
        for(std::size_t vi=0;vi<6;++vi) {
            const auto id=at(variants[vi],"id").string();
            auto native=std::find_if(result.variants.begin(),result.variants.end(),
                [&](const content::VariantResult& value){return value.id==id;});
            auto& reportVariants=report.at("variants").array();
            auto reported=std::find_if(reportVariants.begin(),reportVariants.end(),
                [&](const J& value){return at(value,"variant_id").string()==id;});
            if(native==result.variants.end()||reported==reportVariants.end()) {
                issue("LEVEL001_VARIANT_COVERAGE",item,id,"","/variants","Variant missing from native projection");
                continue;
            }
            if(vi<4) {
                ++checkedOld;
                if(at(variants[vi],"event_ids").array().size()!=24||native->source.events.size()!=24||
                    native->readiness.technicallyRenderable)
                    issue("LEVEL001_OLD_ROUTE",item,id,"","/variants","Historical half-route must remain 24 unresolved contacts");
                continue;
            }
            ++checkedNew;
            const auto variantIssuesBefore=finiteIssues;
            const auto& variant=variants[vi];const auto& selected=at(variant,"event_ids").array();
            const auto start=at(variant,"pick_start").string();
            if(start!=(vi==4?"D":"U")||at(variant,"pick_start_origin").string()!="learner_configuration")
                issue("LEVEL001_PICK_ORIGIN",item,id,"","/pick_start","Both explicit learner D/U starts are required");
            if(selected.size()!=48||native->source.events.size()!=48) {
                issue("LEVEL001_MEMBERSHIP",item,id,"","/event_ids","Full-route variant must select all 48 original contacts");
            }
            for(std::size_t i=0;i<std::min(selected.size(),sourceEvents.size());++i)
                if(selected[i]!=at(sourceEvents[i],"event_id"))
                    issue("LEVEL001_MEMBERSHIP",item,id,"","/event_ids","Variant occurrence order differs from original source array");
            const auto& group=at(variant,"grouping");
            if(at(group,"beat_unit_q")!=J(A{J::fromInteger(1),J::fromInteger(1)}))
                issue("LEVEL001_QUARTER_GRID",item,id,"","/grouping/beat_unit_q",
                    "One Fathom-authored quarter per source contact is required");
            if(!native->readiness.technicallyRenderable||!native->validation.validReference())
                issue("LEVEL001_MODEL",item,id,"","/model","Full-route model must be technically renderable");
            auto& modelEvents=reported->object().at("model").object().at("events").array();
            for(std::size_t i=0;i<native->source.events.size();++i) {
                auto& event=native->source.events[i];
                const auto expected=((i%2==0)==(start=="D"))?"D":"U";
                event.handDirection=expected; // the finite realization emits onto copied new models only
                if(strokeFault&&strokeFault->variantId==id&&strokeFault->contactIndex==i) {
                    event.handDirection=strokeFault->emitted;faultApplied=true;
                }
                if(event.handDirection!=expected)
                    issue("LEVEL001_PICK_PARITY",item,id,event.id,"/model/events/pick",
                        "Emitted stroke differs from continuous chosen-start alternation");
                if(i>=48||!event.span.onset||!(*event.span.onset==Rational{static_cast<std::int64_t>(i),1})||
                    !event.span.duration||!(*event.span.duration==Rational{1,1}))
                    issue("LEVEL001_QUARTER_GRID",item,id,event.id,"/model/events/span",
                        "Projected contact must start at i quarters and last one quarter");
                if(i<modelEvents.size())modelEvents[i].object().at("pick")=event.handDirection;
                ++projectedContacts;
            }
            if(native->source.events.size()!=48||!native->source.events.back().span.onset||
                !(*native->source.events.back().span.onset==Rational{47,1})||
                !native->source.events.back().span.duration||
                !(*native->source.events.back().span.duration==Rational{1,1}))
                issue("LEVEL001_QUARTER_GRID",item,id,"","/model/end","Full route must end at quarter 48");
            native->validation=music::validate(native->source);
            if(!native->validation.validReference())
                issue("LEVEL001_PROJECTED_MODEL",item,id,"","/model","Projected D/U model failed native music validation");
            reported->object()["finite_contract_valid_reference"]=finiteIssues==variantIssuesBefore;
        }
    }
    if(checkedNew!=216||checkedOld!=432||projectedContacts!=10368)
        issue("LEVEL001_EXHAUSTIVE_COVERAGE","","","","/finite_level001",
            "Finite projection must exhaust 216 new, 432 old and 10368 projected contacts");
    if(strokeFault&&!faultApplied)
        issue("LEVEL001_STROKE_FAULT_TARGET","",strokeFault->variantId,"","/stroke_fault",
            "Diagnostic stroke fault target did not name a projected contact");
    result.validReference=finiteIssues==0;
    result.exitCode=result.validReference?2:1;
    report["valid_reference"]=result.validReference;
    report["exit_code"]=J::fromInteger(result.exitCode);
    report["curriculum_playback_authorized"]=false;
    report["finite_level001"]=O{{"status",result.validReference?"valid_nonadmitted":"contract_refusal"},
        {"contract_checked",true},{"authority_package_sha256",packageSha},{"authority_profile_sha256",profileSha},
        {"authority_registry_sha256",registrySha},{"authority_contract_sha256",contractSha},
        {"candidate_package_sha256",content::sha256(input.package)},
        {"candidate_profile_sha256",content::sha256(input.profile)},
        {"candidate_registry_sha256",content::sha256(input.registry)},
        {"fathom_authored_quarter_realization",true},{"source_time_unresolved",true},
        {"old_variants_checked",J::fromInteger(static_cast<std::int64_t>(checkedOld))},
        {"new_variants_checked",J::fromInteger(static_cast<std::int64_t>(checkedNew))},
        {"emitted_contacts",J::fromInteger(static_cast<std::int64_t>(projectedContacts))},
        {"finite_issue_count",J::fromInteger(static_cast<std::int64_t>(finiteIssues))},
        {"stroke_fault_applied",faultApplied},{"runtime_admitted",false}};
    return result;
}
} // namespace fathom::lesson
