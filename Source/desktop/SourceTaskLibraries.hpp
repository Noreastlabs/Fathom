#pragma once
#include "tasks/InstalledExtraSource17Registry.hpp"
#include "tasks/InstalledManualTaskRegistry.hpp"
#include "tasks/InstalledRecipeTaskRegistry.hpp"
#include "tasks/InstalledAdvancedRecipeRegistry.hpp"
#include "tasks/InstalledOrderedContactTaskRegistry.hpp"
#include "tasks/InstalledManualProcedureGraphRegistry.hpp"
#include "tasks/InstalledPhysicalContactTaskRegistry.hpp"
#include "tasks/InstalledPiecewiseContactTaskRegistry.hpp"
#include "tasks/InstalledHarmonicContactTaskRegistry.hpp"
#include "tasks/InstalledSourceContactTaskRegistry.hpp"
#include "tasks/ear234/ClosedPackage.hpp"
#include "tasks/c43/ClosedPackage.hpp"
#include "content/Canonical.hpp"
#include <map>
#include <optional>
#include <atomic>
#include <memory>
#include <vector>
#include "desktop/GeneratedSourceTaskRoutes.hpp"

namespace fathom::desktop {
// Data-only installed gates. Construct on a worker; publish only on the UI thread.
struct SourceTaskLibraries {
    inline static std::atomic<unsigned> activeLoads{0};
    struct ActiveLoad {
        ActiveLoad(){++activeLoads;}
        ~ActiveLoad(){--activeLoads;}
    };
    std::optional<tasks::InstalledManualTaskRegistry> manualTaskRegistry_;
    std::optional<tasks::recipes::InstalledRecipeTaskRegistry> recipeTaskRegistry_;
    std::optional<tasks::advanced::InstalledAdvancedRecipeRegistry> advancedRecipeTaskRegistry_;
    std::optional<tasks::ordered_contacts::InstalledOrderedContactTaskRegistry> orderedContactTaskRegistry_;
    std::optional<tasks::manual_procedure_graph::InstalledManualProcedureGraphRegistry> manualCurriculumRegistry_;
    std::optional<tasks::extra_source17::InstalledExtraSource17Registry> extraSource17Registry_;
    std::optional<tasks::physical_contacts::InstalledPhysicalContactTaskRegistry> physicalContactTaskRegistry_;
    std::optional<tasks::piecewise_contacts::InstalledPiecewiseContactTaskRegistry> piecewiseContactTaskRegistry_;
    std::optional<tasks::harmonic_contacts::InstalledHarmonicContactTaskRegistry> harmonicContactTaskRegistry_;
    std::optional<tasks::source_contacts::InstalledSourceContactTaskRegistry> sourceContactTaskRegistry_;
    std::optional<tasks::ear234::package::ClosedPackage> ear234Package_;
    std::map<std::string,std::string> ear234SourceKeys_;
    std::optional<tasks::c43::package::ClosedPackage> c43Package_;
    std::map<std::string,std::string> c43SourceKeys_;
    std::vector<source_routes::Family> missingFamilies()const {
        using F=source_routes::Family;std::vector<F> missing;
        if(!manualTaskRegistry_)missing.push_back(F::Manual);
        if(!recipeTaskRegistry_)missing.push_back(F::Recipe);
        if(!advancedRecipeTaskRegistry_)missing.push_back(F::Advanced);
        if(!orderedContactTaskRegistry_)missing.push_back(F::Ordered);
        if(!manualCurriculumRegistry_)missing.push_back(F::Graph);
        if(!extraSource17Registry_)missing.push_back(F::Extra);
        if(!physicalContactTaskRegistry_)missing.push_back(F::Physical);
        if(!piecewiseContactTaskRegistry_)missing.push_back(F::Piecewise);
        if(!harmonicContactTaskRegistry_)missing.push_back(F::Harmonic);
        if(!sourceContactTaskRegistry_)missing.push_back(F::Source);
        if(!ear234Package_)missing.push_back(F::Ear);
        if(!c43Package_)missing.push_back(F::C43);
        return missing;
    }
    void loadMissing(const std::filesystem::path& familyResources,
                     const std::shared_ptr<std::atomic<bool>>& canceled={},
                     source_routes::Family family=source_routes::Family::All) {
        const ActiveLoad active;
        const auto wanted=[&](source_routes::Family value){return family==source_routes::Family::All||family==value;};
        const auto checkpoint=[&]{if(canceled&&canceled->load())throw std::runtime_error("Activity loading canceled");};
        checkpoint();
            if(wanted(source_routes::Family::Manual)&&!manualTaskRegistry_)manualTaskRegistry_=tasks::InstalledManualTaskRegistry::load(
                familyResources/"typed-manual-tasks-v1");
            checkpoint();
            if(wanted(source_routes::Family::Recipe)&&!recipeTaskRegistry_)recipeTaskRegistry_=tasks::recipes::InstalledRecipeTaskRegistry::load(
                familyResources/"compiled-recipe-families-v1/level068");
            checkpoint();
            if(wanted(source_routes::Family::Advanced)&&!advancedRecipeTaskRegistry_)advancedRecipeTaskRegistry_=tasks::advanced::InstalledAdvancedRecipeRegistry::load(
                familyResources/"compiled-recipe-families-v1/advanced");
            const auto sourceAssets=familyResources/"source-library/bundle/assets";
            checkpoint();
            if(wanted(source_routes::Family::Ordered)&&!orderedContactTaskRegistry_)orderedContactTaskRegistry_=tasks::ordered_contacts::InstalledOrderedContactTaskRegistry::load(familyResources/"compiled-manual-families-v1/ordered-contact",sourceAssets);
            checkpoint();
            if(wanted(source_routes::Family::Graph)&&!manualCurriculumRegistry_)manualCurriculumRegistry_=tasks::manual_procedure_graph::InstalledManualProcedureGraphRegistry::load(familyResources/"compiled-recipe-families-v1/manual-procedure-graph",sourceAssets);
            checkpoint();
            if(wanted(source_routes::Family::Extra)&&!extraSource17Registry_)extraSource17Registry_=tasks::extra_source17::InstalledExtraSource17Registry::load(familyResources/"compiled-extra-source17",sourceAssets);
            checkpoint();
            if(wanted(source_routes::Family::Physical)&&!physicalContactTaskRegistry_)physicalContactTaskRegistry_=tasks::physical_contacts::InstalledPhysicalContactTaskRegistry::load(familyResources/"compiled-manual-families-v1/physical-contact",sourceAssets);
            checkpoint();
            if(wanted(source_routes::Family::Piecewise)&&!piecewiseContactTaskRegistry_)piecewiseContactTaskRegistry_=tasks::piecewise_contacts::InstalledPiecewiseContactTaskRegistry::load(familyResources/"compiled-manual-families-v1/piecewise-contact",sourceAssets);
            checkpoint();
            if(wanted(source_routes::Family::Harmonic)&&!harmonicContactTaskRegistry_)harmonicContactTaskRegistry_=tasks::harmonic_contacts::InstalledHarmonicContactTaskRegistry::load(familyResources/"compiled-manual-families-v1/harmonic-contact",sourceAssets);
            checkpoint();
            if(wanted(source_routes::Family::Source)&&!sourceContactTaskRegistry_)sourceContactTaskRegistry_=tasks::source_contacts::InstalledSourceContactTaskRegistry::load(familyResources/"compiled-manual-families-v1/source-contact",sourceAssets);
            checkpoint();
            if((wanted(source_routes::Family::Ear)||wanted(source_routes::Family::C43))&&!ear234Package_){
                auto package=tasks::ear234::package::ClosedPackage::load(
                    content::readBounded(familyResources/"compiled-manual-families-v1/ear234/closed-package.json",512*1024),
                    content::readBounded(familyResources/"learn-source-index/exercises.jsonl",32*1024*1024));
                std::map<std::string,std::string> identities;
                for(const auto& row:package.authority().object().at("rows").array()){
                    const auto identity=row.object().at("source_identity").string();
                    const auto key=row.object().at("source_key").string();
                    package.lookup(key,identity);
                    checkpoint();
            if(!identities.emplace(identity,key).second)throw std::runtime_error("duplicate Ear source identity");
                }
                if(identities.size()!=234)throw std::runtime_error("Ear source identity extent");
                ear234SourceKeys_=std::move(identities);ear234Package_=std::move(package);
            }
            checkpoint();
            if(wanted(source_routes::Family::C43)&&!c43Package_){
                auto package=tasks::c43::package::ClosedPackage::load(
                    content::readBounded(familyResources/"compiled-manual-families-v1/c43/closed-package.json",512*1024),
                    content::readBounded(familyResources/"learn-source-index/exercises.jsonl",32*1024*1024));
                std::map<std::string,std::string> identities;
                for(const auto& row:package.authority().object().at("rows").array()){
                    const auto identity=row.object().at("source_identity").string();
                    const auto key=row.object().at("source_key").string();
                    package.lookup(key,identity);
                    checkpoint();
            if(!identities.emplace(identity,key).second)throw std::runtime_error("duplicate C43 source identity");
                }
                if(identities.size()!=43)throw std::runtime_error("C43 source identity extent");
                c43SourceKeys_=std::move(identities);c43Package_=std::move(package);
            }
    }
    void merge(SourceTaskLibraries&& other) {
        // A prepared family adds its exact gate without replacing unrelated gates.
        #define FATHOM_MERGE_GATE(member) if(other.member)member=std::move(other.member)
        FATHOM_MERGE_GATE(manualTaskRegistry_);FATHOM_MERGE_GATE(recipeTaskRegistry_);
        FATHOM_MERGE_GATE(advancedRecipeTaskRegistry_);FATHOM_MERGE_GATE(orderedContactTaskRegistry_);
        FATHOM_MERGE_GATE(manualCurriculumRegistry_);FATHOM_MERGE_GATE(extraSource17Registry_);
        FATHOM_MERGE_GATE(physicalContactTaskRegistry_);FATHOM_MERGE_GATE(piecewiseContactTaskRegistry_);
        FATHOM_MERGE_GATE(harmonicContactTaskRegistry_);FATHOM_MERGE_GATE(sourceContactTaskRegistry_);
        if(other.ear234Package_){ear234Package_=std::move(other.ear234Package_);ear234SourceKeys_=std::move(other.ear234SourceKeys_);}
        if(other.c43Package_){c43Package_=std::move(other.c43Package_);c43SourceKeys_=std::move(other.c43SourceKeys_);}
        #undef FATHOM_MERGE_GATE
    }
    void loadSelected(const std::filesystem::path& resources,
                      const std::shared_ptr<std::atomic<bool>>& canceled,const std::string& source){
        const auto family=source_routes::familyFor(source);
        if(family==source_routes::Family::None)return;
        loadMissing(resources,canceled,family);
        // Preserve the pre-existing legacy fallback for this sole overlap.
        if(source=="level053/moduleb/p003-t1-r1-c2/cmajrp"&&
           (!manualCurriculumRegistry_||!manualCurriculumRegistry_->containsSourceIdentity(source)))
            loadMissing(resources,canceled,source_routes::Family::Manual);
    }
};
}
