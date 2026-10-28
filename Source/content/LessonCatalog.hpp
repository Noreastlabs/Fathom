#pragma once
#include "content/Canonical.hpp"
#include "content/LessonAdmission.hpp"
#include <map>
#include <memory>
#include <set>

namespace fathom::lesson {
inline bool validInstalledGap(std::size_t eventCount,std::size_t gapAfterEvent,
                             std::int64_t numerator,std::int64_t denominator) {
    return (gapAfterEvent==0&&numerator==0&&denominator==1)||
        (gapAfterEvent>0&&gapAfterEvent<eventCount&&numerator>0&&denominator>0);
}
inline bool validInstalledGaps(std::size_t eventCount,std::size_t firstAfter,
                              std::int64_t firstNumerator,std::int64_t firstDenominator,
                              std::size_t secondAfter,std::int64_t secondNumerator,
                              std::int64_t secondDenominator) {
    if (!validInstalledGap(eventCount,firstAfter,firstNumerator,firstDenominator)) return false;
    if (secondAfter==0) return secondNumerator==0&&secondDenominator==1;
    return firstAfter!=0&&secondAfter>firstAfter&&secondAfter<eventCount&&
        secondNumerator>0&&secondDenominator>0;
}
inline Rational installedCaseOnset(Rational step,std::size_t index,
                                   std::size_t gapAfterEvent,Rational gapDuration) {
    const Rational base{step.numerator()*static_cast<std::int64_t>(index),step.denominator()};
    return base+(gapAfterEvent!=0&&index>=gapAfterEvent?gapDuration:Rational{0});
}
inline Rational installedCaseOnset(Rational step,std::size_t index,
                                   std::size_t firstAfter,Rational firstDuration,
                                   std::size_t secondAfter,Rational secondDuration) {
    return installedCaseOnset(step,index,firstAfter,firstDuration)+
        (secondAfter!=0&&index>=secondAfter?secondDuration:Rational{0});
}
struct Variant {
    std::string id, label;
    json::Value authored;
    std::shared_ptr<const music::ValidatedModel> model;
    bool technicallyRenderable=false;
    std::vector<std::string> limitations;
};
struct Lesson {
    std::string id, title;
    int level=0;
    json::Value record;
    std::vector<Variant> variants;
    std::vector<json::Value> resources;
};
enum class Section { Instructions, Context, Assessment, Resources, VariantDetails };
struct InstalledExtensionDescriptor;
class Catalog final {
public:
    static std::shared_ptr<const Catalog> load(const std::filesystem::path& bundle,
        const content::CancellationCheck& canceled = {});
    // Explicit compiled descriptor order; no arbitrary dropped-file discovery.
    static std::vector<std::string> installedExtensionDirectoryNames();
    static std::shared_ptr<const Catalog> loadInstalled(const std::filesystem::path& bundle,
        const std::vector<std::filesystem::path>& installedExtensions,
        const content::CancellationCheck& canceled = {});
    // Retained call signatures for existing focused tests and older consumers.
    static std::shared_ptr<const Catalog> load(const std::filesystem::path& bundle,
                                               const std::filesystem::path& extension);
    static std::shared_ptr<const Catalog> load(const std::filesystem::path& bundle,
                                               const std::filesystem::path& rung02,
                                               const std::filesystem::path& rung03);
    static std::shared_ptr<const Catalog> load(const std::filesystem::path& bundle,
                                               const std::filesystem::path& rung02,
                                               const std::filesystem::path& rung03,
                                               const std::filesystem::path& rung04);
    static std::shared_ptr<const Catalog> load(const std::filesystem::path& bundle,
                                               const std::filesystem::path& rung02,
                                               const std::filesystem::path& rung03,
                                               const std::filesystem::path& rung04,
                                               const std::filesystem::path& level006);
    const std::vector<Lesson>& lessons() const noexcept { return lessons_; }
    bool isInstalledExtension(const std::string& item) const { return extensions_.count(item)!=0; }
    const json::Value& package() const noexcept { return package_; }
    const json::Value& validationReport() const noexcept { return validation_; }
    const json::Value& resourcePlan() const noexcept { return resources_; }
    const std::string& contentVersion() const noexcept { return contentVersion_; }
    const std::string& contentVersion(const std::string& item) const;
    std::size_t sourceEntryCount() const;
    const Lesson& lesson(const std::string& id) const;
    const Variant& variant(const std::string& item,const std::string& id) const;
    std::string text(const std::string& item,const std::string& variant,Section) const;
    std::shared_ptr<const Admission> admit(const std::string& item,const std::string& variant) const;
    // Source-defined four-note transfer cell, ordinal1–5 in the selected L3 direction.
    // No arbitrary cursor cuts or new curriculum identity are introduced.
    std::shared_ptr<const Admission> admitCell(const std::string& item,const std::string& variant,
                                             std::uint32_t ordinal) const;
private:
    // Defined only by the fixed registered-extension QA helper, never production.
    friend struct InstalledCatalogFixtureAccess;
    friend class SelectedCatalogStore;
    Catalog()=default;
    static std::shared_ptr<const Catalog> loadExtension(const std::filesystem::path&,
        const InstalledExtensionDescriptor&, const content::CancellationCheck& canceled = {});
    struct BundleIdentity {
        std::string manifestHash, packageHash, transportHash;
        std::size_t assetCount{}, assetBytes{};
    };
    // A memory cache may reuse models only after rechecking the complete pinned
    // bundle at its current path. No filesystem timestamp grants authority.
    static BundleIdentity reverifyBundle(const std::filesystem::path&,
        const InstalledExtensionDescriptor*, const json::Value& validation,
        const content::CancellationCheck& canceled = {});
    struct ExtensionPermission {
        std::set<std::string> variants;
        Rational step;
        std::size_t eventCount;
        std::string description;
        std::size_t gapAfterEvent{};
        Rational gapDuration{0};
        std::size_t secondGapAfterEvent{};
        Rational secondGapDuration{0};
    };
    std::map<std::string, std::shared_ptr<const Catalog>> extensions_;
    std::map<std::string, ExtensionPermission> extensionPermissions_;
    std::vector<Lesson> lessons_;
    json::Value package_, validation_, resources_;
    std::string contentVersion_;
    std::string manifestHash_,decisionHash_,packageHash_,transportHash_;
};
// Structured-reference readability is deliberately not a playback token.
std::string readinessText(const Variant&);
}
