#pragma once
// Only this compiled, finite set can become an installed runtime extension.
// Native validators remain case-specific and hash-bound; the Catalog asset,
// identity and permission path is common. There is no filesystem discovery.
#include "content/Rung02Extension.hpp"
#include "content/Rung03Extension.hpp"
#include "content/Rung04Extension.hpp"
#include "content/Level006Extension.hpp"
#include "content/Rung05Extension.hpp"
#include "content/Level008Extension.hpp"
#include "content/Level010Extension.hpp"
#include "content/Level007Extension.hpp"
#include "content/Level009Extension.hpp"
#include "content/Level011Extension.hpp"
#include "content/Level013Extension.hpp"
#include "content/Level014Extension.hpp"
#include "content/Level015Extension.hpp"
#include "content/Level016Extension.hpp"
#include "content/Level015Rungs0203Extension.hpp"
#include "content/Level017Extension.hpp"
#include "content/Level018Extension.hpp"
#include "content/Level019Extension.hpp"
#include "content/Level020Extension.hpp"
#include "content/Level021Extension.hpp"
#include "content/Level022Extension.hpp"
#include "content/Level023Extension.hpp"
#include "content/Level024Extension.hpp"
#include "content/Level030Extension.hpp"
#include "content/Level029Extension.hpp"
#include "content/Level025Extension.hpp"
#include "content/Level026Extension.hpp"
#include "content/Level012Rung08Extension.hpp"
#include "content/Level013Rung03Extension.hpp"
#include "content/Level013Rung04Extension.hpp"
#include "content/Level013Rung05Extension.hpp"
#include "content/Level015Rung05Extension.hpp"
#include "content/Level015Rung04Extension.hpp"
#include "content/Level015Rung06Extension.hpp"
#include "content/Level002Exercise002Extension.hpp"
#include "content/Level003ModeBExercise001Extension.hpp"
#include "content/Level004Exercise002Extension.hpp"
#include "content/Level004Exercise003Extension.hpp"
#include "content/Level004Exercise004Extension.hpp"
#include "content/Level004Exercise005Extension.hpp"
#include "content/Level004Exercise006Extension.hpp"
#include "content/Level004Exercise007Extension.hpp"
#include "content/Level004Exercise008Extension.hpp"
#include "content/Level004Exercise009Extension.hpp"
#include "content/Level004Exercise010Extension.hpp"
#include "content/Level004Exercise011Extension.hpp"
#include "content/Level004Exercise012Extension.hpp"
#include "content/Level004Exercise013Extension.hpp"
#include "content/Level004Exercise014Extension.hpp"
#include "content/Level004Exercise015Extension.hpp"
#include "content/Level014Rung03Extension.hpp"
#include "content/Level080ModuleAPass1R02Extension.hpp"
#include "content/Level001Extension.hpp"
#include <array>
#include <vector>

namespace fathom::lesson {
struct InstalledExtensionCase {
    const char* item;
    const char* firstVariant;
    const char* secondVariant;
    int level;
    std::int64_t stepNumerator, stepDenominator;
    std::size_t eventCount;
    const char* description;
    // Zero-initialized for every existing contiguous case. An explicit
    // source-reviewed case can insert one pause before this event index.
    std::size_t gapAfterEvent{};
    std::int64_t gapNumerator{};
    std::int64_t gapDenominator{1};
    // A second reviewed intercell pause; old aggregate initializers default absent.
    std::size_t secondGapAfterEvent{};
    std::int64_t secondGapNumerator{};
    std::int64_t secondGapDenominator{1};
};
struct InstalledExtensionDescriptor {
    const char* directory;
    const char* bundleVersion;
    const char* manifestSha256;
    const char* item;
    const char* firstVariant;
    const char* secondVariant;
    int level;
    std::int64_t stepNumerator, stepDenominator;
    std::size_t eventCount;
    const char* description;
    bool hasProvenance;
    content::Result (*validate)(const content::Input&, const std::string&,
                                const std::string&, const std::string&);
    // Existing one-case descriptors leave this empty. A reviewed multi-case
    // bundle declares every further item explicitly in this finite list.
    std::vector<InstalledExtensionCase> additionalCases{};
    // A source-reviewed single-case selection may contain an intercell pause.
    // Existing descriptor aggregates default to contiguous, zero-gap timing.
    std::size_t baseGapAfterEvent{};
    std::int64_t baseGapNumerator{};
    std::int64_t baseGapDenominator{1};
    // Only a reviewed descriptor may opt in; every existing extension still
    // requires two distinct finite variants.
    bool singleVariant{};
};

inline content::Result validateInstalledRung02(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string&) {
    return validateRung02Extension(input, decision, sha);
}
inline content::Result validateInstalledRung03(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string&) {
    return validateRung03Extension(input, decision, sha);
}
inline content::Result validateInstalledRung04(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string&) {
    return validateRung04Extension(input, decision, sha);
}
inline content::Result validateInstalledLevel006(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel006Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledRung05(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string&) {
    return validateRung05Extension(input, decision, sha);
}
inline content::Result validateInstalledLevel008(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel008Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel010(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel010Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel007(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel007Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel009(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel009Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel011(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel011Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel013(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel013Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel014(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel014Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel015(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel015Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel015Rungs0203(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel015Rungs0203Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel016(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel016Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel017(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel017Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel018(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel018Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel019(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel019Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel020(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel020Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel021(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel021Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel022(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel022Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel023(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel023Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel024(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel024Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel030(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel030Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel029(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel029Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel025(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel025Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel026(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel026Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel012Rung08(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel012Rung08Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel080ModuleAPass1R02(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel080ModuleAPass1R02Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel013Rung03(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel013Rung03Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel013Rung04(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel013Rung04Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel013Rung05(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel013Rung05Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel015Rung05(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel015Rung05Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel015Rung04(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel015Rung04Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel015Rung06(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel015Rung06Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel002Exercise002(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel002Exercise002Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel003ModeBExercise001(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel003ModeBExercise001Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel004Exercise002(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise002Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel004Exercise003(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise003Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel004Exercise004(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise004Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel004Exercise005(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise005Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel004Exercise006(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise006Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel004Exercise007(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise007Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel004Exercise008(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise008Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel004Exercise009(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise009Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel004Exercise010(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise010Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel004Exercise011(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise011Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel004Exercise012(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise012Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel004Exercise013(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise013Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel004Exercise014(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise014Extension(input, decision, sha, provenance);
}
inline content::Result validateInstalledLevel004Exercise015(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel004Exercise015Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel014Rung03(const content::Input& input,
    const std::string& decision, const std::string& sha, const std::string& provenance) {
    return validateLevel014Rung03Extension(input, decision, sha, provenance);
}

inline content::Result validateInstalledLevel001(const content::Input& input,
    const std::string& decisionBytes,const std::string& decisionSha,const std::string&) {
    const auto need=[](bool yes,const char* message){if(!yes)throw std::runtime_error(message);};
    const auto& at=[](const json::Value& value,const char* key)->const json::Value&{return value.object().at(key);};
    constexpr const char* expectedDecision="17a1f80cd4cfc775626d31da9358dc42b060df3b1cb92e103bb4c83aad313036";
    constexpr const char* expectedPlan="bdf0f2424df0f72e0a8b32a225d8e42a07b5005baa0a7fa8f023ca62c9c5fbd4";
    need(decisionSha==expectedDecision&&content::sha256(decisionBytes)==expectedDecision,
        "Level1 installed Curriculum decision differs");
    const auto decision=json::parse(decisionBytes);
    need(at(decision,"version").string()=="level001-full48-curriculum-runtime-decision.1"&&
        at(decision,"status").string()=="ACCEPTED_FOR_INSTALLED_PRODUCER_CANDIDATE"&&
        at(decision,"manager_release_sha256").string()=="55bcdefd6f555dba1c8ac33c8b32091af1330e37859970045c962ff42fea681f"&&
        at(decision,"source_review_sha256").string()=="5b4db66cf148fe864532c63aa5537d5f22df0133fd392fe2806f5f69b3c6d17f"&&
        at(decision,"native_review_sha256").string()=="9df2599e4766837ee5355e151147b3781f305310a8442740b9f909dbcbdd9461"&&
        at(decision,"contract_sha256").string()=="cea318ba4a1c8e54371eccb40c29729e1104d163e922a41665317319055f9646"&&
        at(decision,"package_sha256").string()=="64c155482b5c3886de5a0669c661d3b38e4d0c9ce5dfa713bad362ffe4511082"&&
        at(decision,"profile_sha256").string()=="b76c298763c8c88e211fb5517f950ffca09b22a58c9d767e7616fe43759ee3ba"&&
        at(decision,"registry_sha256").string()=="07c7e371d7a7900fbfb98bc28ec33810f3428db8e7a1f77dd1c80b7f202b397f"&&
        at(decision,"empty_resource_plan_sha256").string()==expectedPlan&&
        at(decision,"source_timing").string()=="unresolved"&&
        at(decision,"recorded_domain").string()=="Technique/fretboard"&&
        at(decision,"explicit_save_only").boolean()&&
        !at(decision,"automatic_credit").boolean()&&
        !at(decision,"mastery").boolean()&&
        !at(decision,"whole_workbook_accepted").boolean(),
        "Level1 installed authority or no-credit decision differs");
    const auto planBytes=content::readBounded(input.sourceRoot/"installed-empty-resource-plan.json",16*1024);
    need(content::sha256(planBytes)==expectedPlan,"Level1 empty resource-plan pin differs");
    const auto plan=json::parse(planBytes);
    need(at(plan,"version").string()=="level001-installed-empty-resource-plan.1"&&
        at(plan,"resources").array().empty()&&at(plan,"source_profile_resource_plan").null()&&
        at(plan,"availability").string()=="none_supplied",
        "Level1 empty resource-plan meaning differs");
    need(content::sha256(input.package)==at(decision,"package_sha256").string()&&
        content::sha256(input.profile)==at(decision,"profile_sha256").string()&&
        content::sha256(input.registry)==at(decision,"registry_sha256").string()&&
        input.expectedProfileSha256==at(decision,"profile_sha256").string(),
        "Level1 installed packet differs from reviewed authority");
    auto result=validateLevel001Extension(input);
    need(result.validReference&&result.exitCode==2&&result.records.size()==108&&result.variants.size()==648,
        "Level1 finite 108-unit native projection refused");
    return result;
}

inline const std::array<InstalledExtensionDescriptor, 53>& installedExtensionDescriptors() {
    static const std::array<InstalledExtensionDescriptor, 53> descriptors{{
        {"rung02-extension", "rung02-extension-bundle.1", FATHOM_RUNG02_MANIFEST_SHA,
         "fg:item:001141", "fg:variant:007404", "fg:variant:007405", 12, 1, 2, 16,
         "One connected 16-note cell. This is not the moving ladder or its complete round trip.",
         false, validateInstalledRung02},
        {"rung03-extension", "rung03-extension-bundle.1", FATHOM_RUNG03_MANIFEST_SHA,
         "fg:item:001142", "fg:variant:007406", "fg:variant:007407", 12, 1, 2, 16,
         "One connected 16-note cell. This is not the moving ladder or its complete round trip.",
         false, validateInstalledRung03},
        {"rung04-extension", "rung04-extension-bundle.1", FATHOM_RUNG04_MANIFEST_SHA,
         "fg:item:001143", "fg:variant:007408", "fg:variant:007409", 12, 1, 2, 16,
         "One connected 16-note cell. This is not the moving ladder or its complete round trip.",
         false, validateInstalledRung04},
        {"level006-extension", "level006-extension-bundle.1", FATHOM_LEVEL006_MANIFEST_SHA,
         "fg:item:001144", "fg:variant:007410", "fg:variant:007411", 6, 1, 4, 4,
         "One separated four-note ascending E-to-D cell. Straight sixteenths are a TXT-only selected option. This does not complete Exercise 001 or Level 6.",
         true, validateInstalledLevel006},
        {"rung05-extension", "rung05-extension-bundle.1", FATHOM_RUNG05_MANIFEST_SHA,
         "fg:item:001145", "fg:variant:007412", "fg:variant:007413", 12, 1, 2, 16,
         "One connected 16-note Db-major cell. This is not the moving ladder, optional inter-cell pause, or its complete round trip.",
         false, validateInstalledRung05},
        {"level008-extension", "level008-extension-bundle.1", FATHOM_LEVEL008_MANIFEST_SHA,
         "fg:item:001146", "fg:variant:007414", "fg:variant:007415", 8, 1, 4, 8,
         "One connected eight-note first low-E P5-to-P7 SHIFT UP cell. This is not Exercise 001 or the complete two-position ladder.",
         true, validateInstalledLevel008},
        {"level010-extension", "level010-extension-bundle.1", FATHOM_LEVEL010_MANIFEST_SHA,
         "fg:item:001147", "fg:variant:007416", "fg:variant:007417", 10, 1, 4, 4,
         "One connected four-note Mode A first low-E P5-to-P7 SHIFT UP Pass2 cell. This is not Exercise 001 or Level 10.",
         true, validateInstalledLevel010},
        {"level007-extension", "level007-extension-bundle.1", FATHOM_LEVEL007_MANIFEST_SHA,
         "fg:item:001148", "fg:variant:007418", "fg:variant:007419", 7, 1, 4, 16,
         "One connected 16-note Exercise 001 Pass2 ASCEND-to-DESCEND relay. Per-note alternating strokes are a reviewed agent interpretation, not individually printed. This is not Level 7.",
         true, validateInstalledLevel007},
        {"level009-extension", "level009-extension-bundle.1", FATHOM_LEVEL009_MANIFEST_SHA,
         "fg:item:001149", "fg:variant:007420", "fg:variant:007421", 9, 1, 4, 4,
         "One selected four-note first low-E SHIFT UP Pass2 cell. The hand frame changes after note 2; this is not the full route or Level 9.",
         true, validateInstalledLevel009,
         {{"fg:item:001150", "fg:variant:007422", "fg:variant:007423", 9, 1, 4, 4,
           "One selected four-note first high-e SHIFT DOWN Pass2 cell. The hand frame changes after note 2; this is not the full route or Level 9."}}},
        {"level011-extension", "level011-extension-bundle.1", FATHOM_LEVEL011_MANIFEST_SHA,
         "fg:item:001151", "fg:variant:007424", "fg:variant:007425", 11, 1, 4, 4,
         "One selected four-note first low-E SHIFT UP Pass2 cell. The hand frame changes after notes 1 and 3; this is not Exercise 001 or Level 11.",
         true, validateInstalledLevel011,
         {{"fg:item:001152", "fg:variant:007426", "fg:variant:007427", 11, 1, 4, 4,
           "One selected four-note first high-e SHIFT DOWN Pass2 cell. The hand frame changes after notes 1 and 3; this is not Exercise 001 or Level 11."}}},
        {"level013-extension", "level013-extension-bundle.1", FATHOM_LEVEL013_MANIFEST_SHA,
         "fg:item:001153", "fg:variant:007428", "fg:variant:007429", 13, 1, 2, 30,
         "One A-major Rung01 first-cell excerpt of the neighboring-rung even-eighth stage. This is not the earlier isolated first-mastery rhythm or the full ladder.",
         true, validateInstalledLevel013,
         {{"fg:item:001154", "fg:variant:007430", "fg:variant:007431", 13, 1, 2, 60,
           "Two neighboring A-major to Bb-major 30-note cells, with one beat of intercell pause for the one-fret whole-frame move. This is not the full ladder.",
           30, 1, 1}}},
        {"level014-extension", "level014-extension-bundle.1", FATHOM_LEVEL014_MANIFEST_SHA,
         "fg:item:001155", "fg:variant:007432", "fg:variant:007433", 14, 1, 3, 36,
         "One complete A-major 36-note rolling-triplet cell. There is no one-fret shift in this selected case; this is not the full neck route.",
         true, validateInstalledLevel014,
         {{"fg:item:001156", "fg:variant:007434", "fg:variant:007435", 14, 1, 3, 72,
           "Two neighboring A-major to Bb-major 36-note rolling-triplet cells, with one beat of intercell pause for the one-fret whole-frame move. This is not the full neck route.",
           36, 1, 1}}},
        {"level015-extension", "level015-extension-bundle.1", FATHOM_LEVEL015_MANIFEST_SHA,
         "fg:item:001157", "fg:variant:007436", "fg:variant:007437", 15, 1, 3, 78,
         "One complete A-major Rung01 78-note two-octave rolling-triplet cell. This is not the full neck route or Level 15 workbook.",
         true, validateInstalledLevel015},
        {"level016-extension", "level016-extension-bundle.1", FATHOM_LEVEL016_MANIFEST_SHA,
         "fg:item:001158", "fg:variant:007438", "fg:variant:007439", 16, 1, 4, 40,
         "One complete A-major first 40-contact rolling-four cell. No tail gap; not the full neck route or Level 16 workbook.",
         true, validateInstalledLevel016,
         {{"fg:item:001159", "fg:variant:007440", "fg:variant:007441", 16, 1, 4, 80,
           "First A-major to Bb-major neighboring 40-contact cells with one-beat released-pressure frame move. Not the full neck route or Level 16 workbook.",
           40, 1, 1}}},
        {"level017-extension", "level017-extension-bundle.1", FATHOM_LEVEL017_MANIFEST_SHA,
         "fg:item:001160", "fg:variant:007442", "fg:variant:007443", 17, 1, 4, 96,
         "One complete A-major first 96-contact rolling-four cell. No tail gap; not the full neck route or Level 17 workbook.",
         true, validateInstalledLevel017,
         {{"fg:item:001161", "fg:variant:007444", "fg:variant:007445", 17, 1, 4, 192,
           "First A-major to Bb-major neighboring 96-contact cells with one-beat released-pressure frame move. Not the full neck route or Level 17 workbook.",
           96, 1, 1}}},
        {"level018-extension", "level018-extension-bundle.1", FATHOM_LEVEL018_MANIFEST_SHA,
         "fg:item:001162", "fg:variant:007446", "fg:variant:007447", 18, 1, 2, 52,
         "One complete A-major first 52-contact diatonic-thirds cell. No tail gap; not the full neck route or Level 18 workbook.",
         true, validateInstalledLevel018,
         {{"fg:item:001163", "fg:variant:007448", "fg:variant:007449", 18, 1, 2, 104,
           "First A-major to Bb-major neighboring 52-contact cells with one-beat released-pressure frame move. Not the full neck route or Level 18 workbook.",
           52, 1, 1}}},
        {"level019-extension", "level019-extension-bundle.1", FATHOM_LEVEL019_MANIFEST_SHA,
         "fg:item:001164", "fg:variant:007450", "fg:variant:007451", 19, 1, 3, 66,
         "One complete A-major first 66-contact sequential broken-triad cell at the authored learning pulse. No tail gap; not the full route or Level 19 workbook.",
         true, validateInstalledLevel019,
         {{"fg:item:001165", "fg:variant:007452", "fg:variant:007453", 19, 1, 3, 132,
           "First A-major to Bb-major neighboring 66-contact triad cells, with one-beat released-pressure rest after event66. Not the full route or Level 19 workbook.",
           66, 1, 1},
          {"fg:item:001166", "fg:variant:007454", "fg:variant:007455", 19, 1, 3, 198,
           "First A-major through B-major neighboring 66-contact triad cells, with one-beat released-pressure rests after events66 and132. Not the full route or Level 19 workbook.",
           66, 1, 1, 132, 1, 1}}},
        {"level020-extension", "level020-extension-bundle.1", FATHOM_LEVEL020_MANIFEST_SHA,
         "fg:item:001167", "fg:variant:007456", "fg:variant:007457", 20, 1, 1, 322,
         "One complete A-major 322-contact five-module learning circuit, one picked note per click with continuous alternating strokes and no boundary pause. This is not the full 25-circuit route or Level 20 workbook.",
         true, validateInstalledLevel020},
        {"level021-extension", "level021-extension-bundle.1", FATHOM_LEVEL021_MANIFEST_SHA,
         "fg:item:001168", "fg:variant:007458", "fg:variant:007459", 21, 1, 2, 16,
         "One complete A-natural-minor 16-contact even-eighth cell with repeated octave root and continuous alternate picking. No tail pause or whole Level21 route.",
         true, validateInstalledLevel021,
         {{"fg:item:001169", "fg:variant:007460", "fg:variant:007461", 21, 1, 2, 32,
           "A to Bb natural-minor neighboring 16-contact cells, with one-beat released-pressure frame move after event16. Not the whole route.",
           16, 1, 1},
          {"fg:item:001170", "fg:variant:007462", "fg:variant:007463", 21, 1, 2, 48,
           "A through B natural-minor neighboring 16-contact cells, with released-pressure rests after events16 and32. Not the whole route.",
           16, 1, 1, 32, 1, 1}}},
        {"level022-extension", "level022-extension-bundle.1", FATHOM_LEVEL022_MANIFEST_SHA,
         "fg:item:001171", "fg:variant:007464", "fg:variant:007465", 22, 1, 2, 60,
         "One A to Bb natural-minor two-octave 60-contact neighboring-pair selection, with a one-beat released-pressure frame move after contact30. Not a standalone A case or full Level22 route.",
         true, validateInstalledLevel022, {}, 30, 1, 1},
        {"level023-extension", "level023-extension-bundle.1", FATHOM_LEVEL023_MANIFEST_SHA,
         "fg:item:001172", "fg:variant:007466", "fg:variant:007467", 23, 1, 3, 36,
         "One isolated A-natural-minor Rung01 36-contact rolling-triplet cell with two separate octave-root attacks. No intercell pause, full route, or whole Level23 workbook.",
         true, validateInstalledLevel023},
        {"level024-extension", "level024-extension-bundle.1", FATHOM_LEVEL024_MANIFEST_SHA,
         "fg:item:001173", "fg:variant:007468", "fg:variant:007469", 24, 1, 3, 78,
         "One first linked A-natural-minor Rung01 78-contact rolling-triplet cell with two separate high-e octave-root attacks. No intercell pause, full route, or whole Level24 workbook.",
         true, validateInstalledLevel024},
        {"level030-extension", "level030-extension-bundle.1", FATHOM_LEVEL030_MANIFEST_SHA,
         "fg:item:001174", "fg:variant:007470", "fg:variant:007471", 30, 1, 2, 12,
         "One isolated A-major-pentatonic Rung01 first12 cell with two separately picked D-string high-root attacks. No neighboring-cell pause, full route or whole Level30 workbook.",
         true, validateInstalledLevel030},
        {"level029-extension", "level029-extension-bundle.1", FATHOM_LEVEL029_MANIFEST_SHA,
         "fg:item:001175", "fg:variant:007472", "fg:variant:007473", 29, 1, 2, 30,
         "One isolated A-natural-minor Rung01 Module1 30-note scale cell with two separately picked high-e root attacks. No terminal rest, Module2 attack or whole Level29 workbook.",
         true, validateInstalledLevel029},
        {"level025-extension", "level025-extension-bundle.1", FATHOM_LEVEL025_MANIFEST_SHA,
         "fg:item:001176", "fg:variant:007474", "fg:variant:007475", 25, 1, 4, 40,
         "One isolated A-natural-minor Rung01 40-contact rolling-four cell with two separate D-string octave-root attacks. No shift pause, full neck route, or whole Level25 workbook.",
         true, validateInstalledLevel025},
        {"level026-extension", "level026-extension-bundle.1", FATHOM_LEVEL026_MANIFEST_SHA,
         "fg:item:001177", "fg:variant:007476", "fg:variant:007477", 26, 1, 4, 96,
         "One isolated A-natural-minor Rung01 96-contact rolling-four cell with two separate high-e two-octave-root attacks. No shift pause, full neck route, or whole Level26 workbook.",
         true, validateInstalledLevel026},
        {"level012-rung08-extension", "level012-rung08-extension-bundle.1", FATHOM_LEVEL012_R08_MANIFEST_SHA,
         "fg:item:001178", "fg:variant:007694", "fg:variant:007695", 12, 1, 2, 16,
         "One isolated E-major Rung08 16-note even-eighth cell with repeated octave root and D/U starts. No tail pause, next-rung shift, full ladder, or whole Level12 workbook.",
         false, validateInstalledLevel012Rung08},
        {"level080-module-a-pass1-r02-extension", "level080-module-a-pass1-r02-extension-bundle.1", FATHOM_LEVEL080_R02_MANIFEST_SHA,
         "fg:item:001179", "fg:variant:007696", "", 80, 1, 1, 4,
         "Supplemental Fathom example: Cmaj7 E–F–G–E melody only, four equal authored quarter-note slots; source timing unspecified. Original exercise remains incomplete.",
         false, validateInstalledLevel080ModuleAPass1R02, {}, 0, 0, 1, true},
        {"level013-rung03-extension", "level013-rung03-extension-bundle.1", FATHOM_LEVEL013_R03_MANIFEST_SHA,
         "fg:item:001130", "fg:variant:007382", "fg:variant:007383", 13, 1, 2, 30,
         "One B-major Rung03 neighboring-stage nominal 30-contact cell, D/U starts, source-guided even eighths on a Fathom-authored q0-to-q15 grid. No fixed printed BPM, meter, tail pause, full ladder or whole Level13 workbook.",
         false, validateInstalledLevel013Rung03},
        {"level014-rung03-extension", "level014-rung03-extension-bundle.1", FATHOM_LEVEL014_R03_MANIFEST_SHA,
         "fg:item:001180", "fg:variant:007698", "fg:variant:007699", 14, 1, 3, 36,
         "One B-major Rung03 36-contact rolling-triplet cell, D/U starts, one group per beat on a nominal q0-to-q12 grid. No fixed printed BPM, tail pause, full ladder or whole Level14 workbook.",
         false, validateInstalledLevel014Rung03},
        {"level015-rungs02-03-extension", "level015-rungs02-03-extension-bundle.1", FATHOM_LEVEL015_R0203_MANIFEST_SHA,
         "fg:item:001181", "fg:variant:007702", "fg:variant:007703", 15, 1, 3, 78,
         "One standalone Bb-major Rung02 78-contact rolling-triplet cell, source-defined q0-to-q26 grid, D/U starts, no fixed BPM, tail pause or whole Level15 workbook.",
         false, validateInstalledLevel015Rungs0203,
         {{"fg:item:001182", "fg:variant:007704", "fg:variant:007705", 15, 1, 3, 78,
           "One separate B-major Rung03 78-contact rolling-triplet cell, source-defined q0-to-q26 grid, D/U starts, no fixed BPM, tail pause or whole Level15 workbook.",
           0, 0, 1}}},
        {"level001-extension", "level001-extension-bundle.1", FATHOM_LEVEL001_MANIFEST_SHA,
         "fg:item:000001", "fg:variant:007478", "fg:variant:007479", 1, 1, 1, 48,
         "One complete original Level1 Exercise 001 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion.",
         false, validateInstalledLevel001,
         {          {"fg:item:000014", "fg:variant:007480", "fg:variant:007481", 1, 1, 1, 48,
           "One complete original Level1 Exercise 002 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000015", "fg:variant:007482", "fg:variant:007483", 1, 1, 1, 48,
           "One complete original Level1 Exercise 003 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000016", "fg:variant:007484", "fg:variant:007485", 1, 1, 1, 48,
           "One complete original Level1 Exercise 004 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000017", "fg:variant:007486", "fg:variant:007487", 1, 1, 1, 48,
           "One complete original Level1 Exercise 005 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000018", "fg:variant:007488", "fg:variant:007489", 1, 1, 1, 48,
           "One complete original Level1 Exercise 006 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000019", "fg:variant:007490", "fg:variant:007491", 1, 1, 1, 48,
           "One complete original Level1 Exercise 007 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000020", "fg:variant:007492", "fg:variant:007493", 1, 1, 1, 48,
           "One complete original Level1 Exercise 008 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000021", "fg:variant:007494", "fg:variant:007495", 1, 1, 1, 48,
           "One complete original Level1 Exercise 009 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000022", "fg:variant:007496", "fg:variant:007497", 1, 1, 1, 48,
           "One complete original Level1 Exercise 010 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000023", "fg:variant:007498", "fg:variant:007499", 1, 1, 1, 48,
           "One complete original Level1 Exercise 011 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000024", "fg:variant:007500", "fg:variant:007501", 1, 1, 1, 48,
           "One complete original Level1 Exercise 012 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000025", "fg:variant:007502", "fg:variant:007503", 1, 1, 1, 48,
           "One complete original Level1 Exercise 013 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000026", "fg:variant:007504", "fg:variant:007505", 1, 1, 1, 48,
           "One complete original Level1 Exercise 014 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000027", "fg:variant:007506", "fg:variant:007507", 1, 1, 1, 48,
           "One complete original Level1 Exercise 015 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000028", "fg:variant:007508", "fg:variant:007509", 1, 1, 1, 48,
           "One complete original Level1 Exercise 016 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000029", "fg:variant:007510", "fg:variant:007511", 1, 1, 1, 48,
           "One complete original Level1 Exercise 017 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000030", "fg:variant:007512", "fg:variant:007513", 1, 1, 1, 48,
           "One complete original Level1 Exercise 018 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000031", "fg:variant:007514", "fg:variant:007515", 1, 1, 1, 48,
           "One complete original Level1 Exercise 019 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000032", "fg:variant:007516", "fg:variant:007517", 1, 1, 1, 48,
           "One complete original Level1 Exercise 020 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000033", "fg:variant:007518", "fg:variant:007519", 1, 1, 1, 48,
           "One complete original Level1 Exercise 021 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000034", "fg:variant:007520", "fg:variant:007521", 1, 1, 1, 48,
           "One complete original Level1 Exercise 022 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000035", "fg:variant:007522", "fg:variant:007523", 1, 1, 1, 48,
           "One complete original Level1 Exercise 023 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000036", "fg:variant:007524", "fg:variant:007525", 1, 1, 1, 48,
           "One complete original Level1 Exercise 024 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000037", "fg:variant:007526", "fg:variant:007527", 1, 1, 1, 48,
           "One complete original Level1 Exercise 025 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000038", "fg:variant:007528", "fg:variant:007529", 1, 1, 1, 48,
           "One complete original Level1 Exercise 026 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000039", "fg:variant:007530", "fg:variant:007531", 1, 1, 1, 48,
           "One complete original Level1 Exercise 027 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000040", "fg:variant:007532", "fg:variant:007533", 1, 1, 1, 48,
           "One complete original Level1 Exercise 028 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000041", "fg:variant:007534", "fg:variant:007535", 1, 1, 1, 48,
           "One complete original Level1 Exercise 029 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000042", "fg:variant:007536", "fg:variant:007537", 1, 1, 1, 48,
           "One complete original Level1 Exercise 030 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000043", "fg:variant:007538", "fg:variant:007539", 1, 1, 1, 48,
           "One complete original Level1 Exercise 031 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000044", "fg:variant:007540", "fg:variant:007541", 1, 1, 1, 48,
           "One complete original Level1 Exercise 032 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000045", "fg:variant:007542", "fg:variant:007543", 1, 1, 1, 48,
           "One complete original Level1 Exercise 033 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000046", "fg:variant:007544", "fg:variant:007545", 1, 1, 1, 48,
           "One complete original Level1 Exercise 034 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000047", "fg:variant:007546", "fg:variant:007547", 1, 1, 1, 48,
           "One complete original Level1 Exercise 035 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000048", "fg:variant:007548", "fg:variant:007549", 1, 1, 1, 48,
           "One complete original Level1 Exercise 036 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000049", "fg:variant:007550", "fg:variant:007551", 1, 1, 1, 48,
           "One complete original Level1 Exercise 037 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000050", "fg:variant:007552", "fg:variant:007553", 1, 1, 1, 48,
           "One complete original Level1 Exercise 038 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000051", "fg:variant:007554", "fg:variant:007555", 1, 1, 1, 48,
           "One complete original Level1 Exercise 039 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000052", "fg:variant:007556", "fg:variant:007557", 1, 1, 1, 48,
           "One complete original Level1 Exercise 040 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000053", "fg:variant:007558", "fg:variant:007559", 1, 1, 1, 48,
           "One complete original Level1 Exercise 041 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000054", "fg:variant:007560", "fg:variant:007561", 1, 1, 1, 48,
           "One complete original Level1 Exercise 042 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000055", "fg:variant:007562", "fg:variant:007563", 1, 1, 1, 48,
           "One complete original Level1 Exercise 043 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000056", "fg:variant:007564", "fg:variant:007565", 1, 1, 1, 48,
           "One complete original Level1 Exercise 044 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000057", "fg:variant:007566", "fg:variant:007567", 1, 1, 1, 48,
           "One complete original Level1 Exercise 045 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000058", "fg:variant:007568", "fg:variant:007569", 1, 1, 1, 48,
           "One complete original Level1 Exercise 046 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000059", "fg:variant:007570", "fg:variant:007571", 1, 1, 1, 48,
           "One complete original Level1 Exercise 047 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000060", "fg:variant:007572", "fg:variant:007573", 1, 1, 1, 48,
           "One complete original Level1 Exercise 048 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000061", "fg:variant:007574", "fg:variant:007575", 1, 1, 1, 48,
           "One complete original Level1 Exercise 049 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000062", "fg:variant:007576", "fg:variant:007577", 1, 1, 1, 48,
           "One complete original Level1 Exercise 050 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000063", "fg:variant:007578", "fg:variant:007579", 1, 1, 1, 48,
           "One complete original Level1 Exercise 051 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000064", "fg:variant:007580", "fg:variant:007581", 1, 1, 1, 48,
           "One complete original Level1 Exercise 052 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000065", "fg:variant:007582", "fg:variant:007583", 1, 1, 1, 48,
           "One complete original Level1 Exercise 053 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000066", "fg:variant:007584", "fg:variant:007585", 1, 1, 1, 48,
           "One complete original Level1 Exercise 054 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000067", "fg:variant:007586", "fg:variant:007587", 1, 1, 1, 48,
           "One complete original Level1 Exercise 055 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000068", "fg:variant:007588", "fg:variant:007589", 1, 1, 1, 48,
           "One complete original Level1 Exercise 056 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000069", "fg:variant:007590", "fg:variant:007591", 1, 1, 1, 48,
           "One complete original Level1 Exercise 057 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000070", "fg:variant:007592", "fg:variant:007593", 1, 1, 1, 48,
           "One complete original Level1 Exercise 058 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000071", "fg:variant:007594", "fg:variant:007595", 1, 1, 1, 48,
           "One complete original Level1 Exercise 059 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000072", "fg:variant:007596", "fg:variant:007597", 1, 1, 1, 48,
           "One complete original Level1 Exercise 060 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000073", "fg:variant:007598", "fg:variant:007599", 1, 1, 1, 48,
           "One complete original Level1 Exercise 061 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000074", "fg:variant:007600", "fg:variant:007601", 1, 1, 1, 48,
           "One complete original Level1 Exercise 062 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000075", "fg:variant:007602", "fg:variant:007603", 1, 1, 1, 48,
           "One complete original Level1 Exercise 063 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000076", "fg:variant:007604", "fg:variant:007605", 1, 1, 1, 48,
           "One complete original Level1 Exercise 064 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000077", "fg:variant:007606", "fg:variant:007607", 1, 1, 1, 48,
           "One complete original Level1 Exercise 065 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000078", "fg:variant:007608", "fg:variant:007609", 1, 1, 1, 48,
           "One complete original Level1 Exercise 066 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000079", "fg:variant:007610", "fg:variant:007611", 1, 1, 1, 48,
           "One complete original Level1 Exercise 067 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000080", "fg:variant:007612", "fg:variant:007613", 1, 1, 1, 48,
           "One complete original Level1 Exercise 068 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000081", "fg:variant:007614", "fg:variant:007615", 1, 1, 1, 48,
           "One complete original Level1 Exercise 069 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000082", "fg:variant:007616", "fg:variant:007617", 1, 1, 1, 48,
           "One complete original Level1 Exercise 070 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000083", "fg:variant:007618", "fg:variant:007619", 1, 1, 1, 48,
           "One complete original Level1 Exercise 071 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000084", "fg:variant:007620", "fg:variant:007621", 1, 1, 1, 48,
           "One complete original Level1 Exercise 072 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000085", "fg:variant:007622", "fg:variant:007623", 1, 1, 1, 48,
           "One complete original Level1 Exercise 073 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000086", "fg:variant:007624", "fg:variant:007625", 1, 1, 1, 48,
           "One complete original Level1 Exercise 074 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000087", "fg:variant:007626", "fg:variant:007627", 1, 1, 1, 48,
           "One complete original Level1 Exercise 075 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000088", "fg:variant:007628", "fg:variant:007629", 1, 1, 1, 48,
           "One complete original Level1 Exercise 076 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000089", "fg:variant:007630", "fg:variant:007631", 1, 1, 1, 48,
           "One complete original Level1 Exercise 077 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000090", "fg:variant:007632", "fg:variant:007633", 1, 1, 1, 48,
           "One complete original Level1 Exercise 078 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000091", "fg:variant:007634", "fg:variant:007635", 1, 1, 1, 48,
           "One complete original Level1 Exercise 079 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000092", "fg:variant:007636", "fg:variant:007637", 1, 1, 1, 48,
           "One complete original Level1 Exercise 080 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000093", "fg:variant:007638", "fg:variant:007639", 1, 1, 1, 48,
           "One complete original Level1 Exercise 081 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000094", "fg:variant:007640", "fg:variant:007641", 1, 1, 1, 48,
           "One complete original Level1 Exercise 082 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000095", "fg:variant:007642", "fg:variant:007643", 1, 1, 1, 48,
           "One complete original Level1 Exercise 083 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000096", "fg:variant:007644", "fg:variant:007645", 1, 1, 1, 48,
           "One complete original Level1 Exercise 084 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000097", "fg:variant:007646", "fg:variant:007647", 1, 1, 1, 48,
           "One complete original Level1 Exercise 085 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000098", "fg:variant:007648", "fg:variant:007649", 1, 1, 1, 48,
           "One complete original Level1 Exercise 086 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000099", "fg:variant:007650", "fg:variant:007651", 1, 1, 1, 48,
           "One complete original Level1 Exercise 087 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000100", "fg:variant:007652", "fg:variant:007653", 1, 1, 1, 48,
           "One complete original Level1 Exercise 088 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000101", "fg:variant:007654", "fg:variant:007655", 1, 1, 1, 48,
           "One complete original Level1 Exercise 089 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000102", "fg:variant:007656", "fg:variant:007657", 1, 1, 1, 48,
           "One complete original Level1 Exercise 090 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000103", "fg:variant:007658", "fg:variant:007659", 1, 1, 1, 48,
           "One complete original Level1 Exercise 091 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000104", "fg:variant:007660", "fg:variant:007661", 1, 1, 1, 48,
           "One complete original Level1 Exercise 092 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000105", "fg:variant:007662", "fg:variant:007663", 1, 1, 1, 48,
           "One complete original Level1 Exercise 093 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000106", "fg:variant:007664", "fg:variant:007665", 1, 1, 1, 48,
           "One complete original Level1 Exercise 094 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000107", "fg:variant:007666", "fg:variant:007667", 1, 1, 1, 48,
           "One complete original Level1 Exercise 095 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000108", "fg:variant:007668", "fg:variant:007669", 1, 1, 1, 48,
           "One complete original Level1 Exercise 096 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000109", "fg:variant:007670", "fg:variant:007671", 1, 1, 1, 48,
           "One complete original Level1 Exercise 097 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000110", "fg:variant:007672", "fg:variant:007673", 1, 1, 1, 48,
           "One complete original Level1 Exercise 098 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000111", "fg:variant:007674", "fg:variant:007675", 1, 1, 1, 48,
           "One complete original Level1 Exercise 099 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000112", "fg:variant:007676", "fg:variant:007677", 1, 1, 1, 48,
           "One complete original Level1 Exercise 100 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000113", "fg:variant:007678", "fg:variant:007679", 1, 1, 1, 48,
           "One complete original Level1 Exercise 101 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000114", "fg:variant:007680", "fg:variant:007681", 1, 1, 1, 48,
           "One complete original Level1 Exercise 102 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000115", "fg:variant:007682", "fg:variant:007683", 1, 1, 1, 48,
           "One complete original Level1 Exercise 103 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000116", "fg:variant:007684", "fg:variant:007685", 1, 1, 1, 48,
           "One complete original Level1 Exercise 104 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000117", "fg:variant:007686", "fg:variant:007687", 1, 1, 1, 48,
           "One complete original Level1 Exercise 105 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000118", "fg:variant:007688", "fg:variant:007689", 1, 1, 1, 48,
           "One complete original Level1 Exercise 106 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000119", "fg:variant:007690", "fg:variant:007691", 1, 1, 1, 48,
           "One complete original Level1 Exercise 107 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."},
          {"fg:item:000120", "fg:variant:007692", "fg:variant:007693", 1, 1, 1, 48,
           "One complete original Level1 Exercise 108 full48 selected D/U route on a Fathom-authored quarter grid; source timing unresolved. Explicit Save records activity, not credit or whole-workbook completion."}}},
        {"level013-rung04-extension", "level013-rung04-extension-bundle.1", FATHOM_LEVEL013_R04_MANIFEST_SHA,
         "fg:item:001183", "fg:variant:007706", "fg:variant:007707", 13, 1, 2, 30,
         "One C-major Rung04 neighboring-stage nominal 30-contact cell, D/U starts, source-guided even eighths on a Fathom-authored q0-to-q15 grid. No fixed printed BPM, meter, tail pause, full ladder or whole Level13 workbook.",
         false, validateInstalledLevel013Rung04},
        {"level013-rung05-extension", "level013-rung05-extension-bundle.1", FATHOM_LEVEL013_R05_MANIFEST_SHA,
         "fg:item:001184", "fg:variant:007708", "fg:variant:007709", 13, 1, 2, 30,
         "One Db-major Rung05 neighboring-stage nominal 30-contact cell, D/U starts, source-guided even eighths on a Fathom-authored q0-to-q15 grid. No fixed printed BPM, meter, tail pause, full ladder or whole Level13 workbook.",
         false, validateInstalledLevel013Rung05},
        {"level015-rung05-extension", "level015-rung05-extension-bundle.1", FATHOM_LEVEL015_R05_MANIFEST_SHA,
         "fg:item:001185", "fg:variant:007710", "fg:variant:007711", 15, 1, 3, 78,
         "One Db-major Rung05 78-contact cell with D/U starts on attributed quarter-triplet q0-to-q26 grid. Source-defined relative timing; no fixed BPM, meter, tail pause, full ladder or whole Level15 workbook.",
         false, validateInstalledLevel015Rung05},
        {"level015-rung04-extension", "level015-rung04-extension-bundle.1", FATHOM_LEVEL015_R04_MANIFEST_SHA,
         "fg:item:001186", "fg:variant:007712", "fg:variant:007713", 15, 1, 3, 78,
         "One C-major Rung04 78-contact cell with D/U starts on attributed quarter-triplet q0-to-q26 grid. Source-defined relative timing; no fixed BPM, meter, tail pause, full ladder or whole Level15 workbook.",
         false, validateInstalledLevel015Rung04},
        {"level015-rung06-extension", "level015-rung06-extension-bundle.1", FATHOM_LEVEL015_R06_MANIFEST_SHA,
         "fg:item:001187", "fg:variant:007714", "fg:variant:007715", 15, 1, 3, 78,
         "One D-major Rung06 78-contact cell with D/U starts on attributed quarter-triplet q0-to-q26 grid. Source-defined relative timing; no fixed BPM, meter, tail pause, full ladder or whole Level15 workbook.",
         false, validateInstalledLevel015Rung06},
        {"level002-ex002-extension", "level002-ex002-extension-bundle.1", FATHOM_LEVEL002_EX002_MANIFEST_SHA,
         "fg:item:001188", "fg:variant:007716", "fg:variant:007717", 2, 1, 4, 40,
         "One printed Level2 Exercise002 1213 complete40-contact adjacent-string cell with source-authored D/U starts on selected straight-sixteenth q0-to-q10 grid. No fixed BPM, meter, triplet/quintuplet selection, whole Level2 or learner credit.",
         false, validateInstalledLevel002Exercise002},
        {"level003-modeb001-extension", "level003-modeb001-extension-bundle.1", FATHOM_LEVEL003_MODEB001_MANIFEST_SHA,
         "fg:item:000240", "fg:variant:000827", "fg:variant:000829", 3, 1, 4, 40,
         "Only the printed Level3 Mode B Exercise001 1212 second even-volume straight-sixteenth D/U pass, q0-to-q10 metric slots. The first accent pass, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise001 completion or learner credit.",
         false, validateInstalledLevel003ModeBExercise001},
        {"level004-ex002-extension", "level004-ex002-extension-bundle.1", FATHOM_LEVEL004_EX002_MANIFEST_SHA,
         "fg:item:000445", "fg:variant:003287", "fg:variant:003289", 4, 1, 4, 32,
         "Only printed Level4 Exercise002 1213 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise002 completion or learner credit.",
         false, validateInstalledLevel004Exercise002},
        {"level004-ex003-extension", "level004-ex003-extension-bundle.1", FATHOM_LEVEL004_EX003_MANIFEST_SHA,
         "fg:item:000446", "fg:variant:003299", "fg:variant:003301", 4, 1, 4, 32,
         "Only printed Level4 Exercise003 1214 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise003 completion or learner credit.",
         false, validateInstalledLevel004Exercise003},
        {"level004-ex004-extension", "level004-ex004-extension-bundle.1", FATHOM_LEVEL004_EX004_MANIFEST_SHA,
         "fg:item:000447", "fg:variant:003311", "fg:variant:003313", 4, 1, 4, 32,
         "Only printed Level4 Exercise004 1231 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise004 completion or learner credit.",
         false, validateInstalledLevel004Exercise004},
        {"level004-ex005-extension", "level004-ex005-extension-bundle.1", FATHOM_LEVEL004_EX005_MANIFEST_SHA,
         "fg:item:000448", "fg:variant:003323", "fg:variant:003325", 4, 1, 4, 32,
         "Only printed Level4 Exercise005 1232 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise005 completion or learner credit.",
         false, validateInstalledLevel004Exercise005},
        {"level004-ex006-extension", "level004-ex006-extension-bundle.1", FATHOM_LEVEL004_EX006_MANIFEST_SHA,
         "fg:item:000449", "fg:variant:003335", "fg:variant:003337", 4, 1, 4, 32,
         "Only printed Level4 Exercise006 1234 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise006 completion or learner credit.",
         false, validateInstalledLevel004Exercise006},
        {"level004-ex007-extension", "level004-ex007-extension-bundle.1", FATHOM_LEVEL004_EX007_MANIFEST_SHA,
         "fg:item:000450", "fg:variant:003347", "fg:variant:003349", 4, 1, 4, 32,
         "Only printed Level4 Exercise007 1241 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise007 completion or learner credit.",
         false, validateInstalledLevel004Exercise007},
        {"level004-ex008-extension", "level004-ex008-extension-bundle.1", FATHOM_LEVEL004_EX008_MANIFEST_SHA,
         "fg:item:000451", "fg:variant:003359", "fg:variant:003361", 4, 1, 4, 32,
         "Only printed Level4 Exercise008 1242 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise008 completion or learner credit.",
         false, validateInstalledLevel004Exercise008},
        {"level004-ex009-extension", "level004-ex009-extension-bundle.1", FATHOM_LEVEL004_EX009_MANIFEST_SHA,
         "fg:item:000452", "fg:variant:003371", "fg:variant:003373", 4, 1, 4, 32,
         "Only printed Level4 Exercise009 1243 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise009 completion or learner credit.",
         false, validateInstalledLevel004Exercise009},
        {"level004-ex010-extension", "level004-ex010-extension-bundle.1", FATHOM_LEVEL004_EX010_MANIFEST_SHA,
         "fg:item:000453", "fg:variant:003383", "fg:variant:003385", 4, 1, 4, 32,
         "Only printed Level4 Exercise010 1312 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise010 completion or learner credit.",
         false, validateInstalledLevel004Exercise010},
        {"level004-ex011-extension", "level004-ex011-extension-bundle.1", FATHOM_LEVEL004_EX011_MANIFEST_SHA,
         "fg:item:000454", "fg:variant:003395", "fg:variant:003397", 4, 1, 4, 32,
         "Only printed Level4 Exercise011 1313 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise011 completion or learner credit.",
         false, validateInstalledLevel004Exercise011},
        {"level004-ex012-extension", "level004-ex012-extension-bundle.1", FATHOM_LEVEL004_EX012_MANIFEST_SHA,
         "fg:item:000455", "fg:variant:003407", "fg:variant:003409", 4, 1, 4, 32,
         "Only printed Level4 Exercise012 1314 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise012 completion or learner credit.",
         false, validateInstalledLevel004Exercise012},
        {"level004-ex013-extension", "level004-ex013-extension-bundle.1", FATHOM_LEVEL004_EX013_MANIFEST_SHA,
         "fg:item:000456", "fg:variant:003419", "fg:variant:003421", 4, 1, 4, 32,
         "Only printed Level4 Exercise013 1321 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise013 completion or learner credit.",
         false, validateInstalledLevel004Exercise013},
        {"level004-ex014-extension", "level004-ex014-extension-bundle.1", FATHOM_LEVEL004_EX014_MANIFEST_SHA,
         "fg:item:000457", "fg:variant:003431", "fg:variant:003433", 4, 1, 4, 32,
         "Only printed Level4 Exercise014 1323 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise014 completion or learner credit.",
         false, validateInstalledLevel004Exercise014},
        {"level004-ex015-extension", "level004-ex015-extension-bundle.1", FATHOM_LEVEL004_EX015_MANIFEST_SHA,
         "fg:item:000458", "fg:variant:003443", "fg:variant:003445", 4, 1, 4, 32,
         "Only printed Level4 Exercise015 1324 second even-volume straight-sixteenth D/U pass, q0-to-q8 metric slots. First accent pass, opposite-start repeat, other rhythms and ten historical variants remain unavailable; no fixed BPM, acoustic note-off, whole Exercise015 completion or learner credit.",
         false, validateInstalledLevel004Exercise015},
    }};
    return descriptors;
}
} // namespace fathom::lesson
