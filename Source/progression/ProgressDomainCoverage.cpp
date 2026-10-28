#include "progression/ProgressDomainCoverage.hpp"
#include "content/Canonical.hpp"
#include <algorithm>
#include <regex>
#include <set>

namespace fathom::progression {
namespace {
using V = json::Value;
void require(bool condition, const std::string& message) {
    if (!condition) throw DomainCoverageError(message);
}
bool sha256(const std::string& value) {
    return value.size() == 64 && value.find_first_not_of("0123456789abcdef") == std::string::npos;
}
const V& field(const V& value, const char* key) {
    const auto* found = value.find(key);
    require(found != nullptr, std::string("Missing saved source field: ") + key);
    return *found;
}
std::string stringField(const V& value, const char* key) {
    const auto& found = field(value, key);
    require(found.isString(), std::string("Invalid saved source field: ") + key);
    return found.string();
}
V strings(const std::vector<std::string>& values) {
    V::Array out;
    for (const auto& value : values) out.emplace_back(value);
    return out;
}
V bindingValue(const DomainBinding& binding) {
    return V::Object{{"item_id", binding.item}, {"variant_id", binding.variant},
        {"content_revision", V::fromInteger(binding.contentRevision)},
        {"content_version", binding.contentVersion},
        {"source_manifest_sha256", binding.sourceManifestSha256},
        {"source_refs", strings(binding.sourceRefs)}};
}
V observedBinding(const Evidence& attempt) {
    require(attempt.sourceScope.isObject(), "Attempt lacks validated source scope");
    const auto& scope = attempt.sourceScope;
    const auto& revision = field(scope, "content_revision");
    std::int64_t number{};
    require(revision.integer(number) && number > 0, "Invalid saved content revision");
    const auto& refs = field(scope, "source_refs");
    require(refs.isArray() && !refs.array().empty(), "Invalid saved source references");
    for (const auto& ref : refs.array()) require(ref.isString() && !ref.string().empty(), "Invalid saved source reference");
    return V::Object{{"item_id", stringField(scope, "item_id")},
        {"variant_id", stringField(scope, "variant_id")},
        {"content_revision", revision},
        {"content_version", stringField(scope, "content_version")},
        {"source_manifest_sha256", stringField(scope, "source_manifest_sha256")},
        {"source_refs", refs}};
}
void uniqueNonempty(const std::vector<std::string>& values, const char* label) {
    require(!values.empty(), std::string("Missing ") + label);
    std::set<std::string> seen;
    for (const auto& value : values)
        require(!value.empty() && seen.insert(value).second, std::string("Empty/duplicate ") + label);
}
std::string validateCatalog(const DomainCatalog& catalog, const std::string& expectedManifest) {
    require(sha256(expectedManifest) && catalog.contentManifestSha256 == expectedManifest,
            "Domain catalog belongs to another content manifest");
    require(!catalog.version.empty() && !catalog.entries.empty(), "Missing domain catalog identity/entries");
    const auto& sourceManifest = catalog.sourceManifestSha256.empty()
        ? expectedManifest : catalog.sourceManifestSha256;
    require(sha256(sourceManifest), "Invalid domain source manifest");
    std::set<std::string> bindings;
    V::Array records;
    for (const auto& entry : catalog.entries) {
        const auto& binding = entry.binding;
        require(std::regex_match(binding.item, std::regex("fg:item:[0-9]{6}"))
                && std::regex_match(binding.variant, std::regex("fg:variant:[0-9]{6}")),
                "Invalid domain item/variant identity");
        require(binding.contentRevision > 0 && !binding.contentVersion.empty()
                && binding.sourceManifestSha256 == sourceManifest,
                "Invalid domain source version/manifest identity");
        uniqueNonempty(binding.sourceRefs, "domain source refs");
        uniqueNonempty(entry.domains, "domain labels");
        require(!entry.provenanceReference.empty() && sha256(entry.provenanceSha256),
                "Domain labels require explicit authority provenance");
        require(entry.vocabularyReference.empty() == entry.vocabularySha256.empty()
                && (entry.vocabularyReference.empty() || sha256(entry.vocabularySha256)),
                "Invalid domain vocabulary provenance");
        require(entry.supportingReference.empty() == entry.supportingSha256.empty()
                && (entry.supportingReference.empty() || sha256(entry.supportingSha256)),
                "Invalid supporting domain provenance");
        const auto value = bindingValue(binding);
        require(bindings.insert(storage::canonical(value)).second, "Duplicate domain source binding");
        V::Object record{{"binding", value}, {"domains", strings(entry.domains)},
            {"provenance_reference", entry.provenanceReference},
            {"provenance_sha256", entry.provenanceSha256}};
        if (!entry.vocabularyReference.empty()) {
            record.emplace("vocabulary_reference", entry.vocabularyReference);
            record.emplace("vocabulary_sha256", entry.vocabularySha256);
        }
        if (!entry.supportingReference.empty()) {
            record.emplace("supporting_reference", entry.supportingReference);
            record.emplace("supporting_sha256", entry.supportingSha256);
        }
        records.emplace_back(record);
    }
    V::Object identity{{"version", catalog.version},
        {"content_manifest_sha256", expectedManifest}, {"entries", records}};
    if (!catalog.sourceManifestSha256.empty())
        identity.emplace("source_manifest_sha256", sourceManifest);
    return content::sha256(storage::canonical(identity));
}
std::string mismatchReason(const V& observed, const DomainCatalog& catalog) {
    bool item = false, variant = false, revision = false, version = false, manifest = false;
    for (const auto& entry : catalog.entries) {
        const auto expected = bindingValue(entry.binding);
        if (field(expected, "item_id") != field(observed, "item_id")) continue;
        item = true;
        if (field(expected, "variant_id") != field(observed, "variant_id")) continue;
        variant = true;
        if (field(expected, "content_revision") != field(observed, "content_revision")) continue;
        revision = true;
        if (field(expected, "content_version") != field(observed, "content_version")) continue;
        version = true;
        if (field(expected, "source_manifest_sha256") != field(observed, "source_manifest_sha256")) continue;
        manifest = true;
    }
    if (!item) return "unknown_item";
    if (!variant) return "unknown_variant";
    if (!revision) return "content_revision_mismatch";
    if (!version) return "content_version_mismatch";
    if (!manifest) return "source_manifest_mismatch";
    return "source_refs_mismatch";
}
}

DomainCoverage projectDomainCoverage(const SnapshotEvidence& snapshot, const DomainCatalog& catalog,
                                     const std::string& expectedProfile,
                                     const std::string& expectedManifest) {
    require(!expectedProfile.empty() && snapshot.profile == expectedProfile,
            "Domain coverage cannot cross profile identity");
    require(sha256(snapshot.evidenceHash) && sha256(snapshot.snapshotHash) && snapshot.marker >= 0,
            "Domain coverage requires snapshot/evidence identity");
    DomainCoverage result;
    result.catalogSha256 = validateCatalog(catalog, expectedManifest);
    result.profile = snapshot.profile;
    result.evidenceSha256 = snapshot.evidenceHash;
    result.snapshotSha256 = snapshot.snapshotHash;
    result.evidenceMarker = snapshot.marker;
    result.catalogVersion = catalog.version;
    std::set<std::string> originalOwners;
    for (const auto& record : snapshot.records) {
        if (record.kind == Kind::Freeplay) { ++result.ignoredFreeplay; continue; }
        if (record.kind != Kind::Attempt) continue;
        require(!record.key.empty() && originalOwners.insert(record.key).second,
                "Duplicate/empty original Attempt owner");
        if (record.status != "committed" || record.active.numerator() <= 0) continue;
        const auto observed = observedBinding(record);
        const auto found = std::find_if(catalog.entries.begin(), catalog.entries.end(),
            [&](const DomainMetadata& entry) { return bindingValue(entry.binding) == observed; });
        if (found == catalog.entries.end()) {
            result.unmapped.push_back({record.key, mismatchReason(observed, catalog)});
            continue;
        }
        ++result.mappedAttempts;
        for (const auto& domain : found->domains) {
            auto& activity = result.byDomain[domain];
            ++activity.attempts;
            activity.activeSeconds = activity.activeSeconds + record.active;
        }
    }
    return result;
}

DomainCoverage projectDomainCoverage(const storage::Reply& reply, const DomainCatalog& catalog,
                                     const std::string& expectedProfile,
                                     const std::string& expectedManifest) {
    return projectDomainCoverage(adaptSnapshot(reply), catalog, expectedProfile, expectedManifest);
}

DomainCoverage projectDomainCoverage(const SnapshotEvidence& snapshot, const MultiDomainCatalog& catalog,
                                     const std::string& expectedProfile,
                                     const std::vector<std::string>& expectedManifests) {
    require(!expectedProfile.empty() && snapshot.profile == expectedProfile,
            "Domain coverage cannot cross profile identity");
    require(sha256(snapshot.evidenceHash) && sha256(snapshot.snapshotHash) && snapshot.marker >= 0,
            "Domain coverage requires snapshot/evidence identity");
    require(!catalog.version.empty() && !catalog.catalogs.empty() && !expectedManifests.empty()
            && catalog.catalogs.size() == expectedManifests.size(),
            "Missing or extra installed domain manifest");
    std::set<std::string> expected, included, owners, variantOwners;
    std::map<std::string, std::string> itemOwners;
    for (const auto& manifest : expectedManifests)
        require(sha256(manifest) && expected.insert(manifest).second,
                "Duplicate/invalid expected installed manifest");
    V::Array catalogIdentities;
    DomainCatalog lookup;
    for (const auto& member : catalog.catalogs) {
        require(expected.count(member.contentManifestSha256) != 0
                && included.insert(member.contentManifestSha256).second,
                "Unknown/duplicate installed domain manifest");
        require(!member.sourceManifestSha256.empty(),
                "Mixed catalog requires explicit source manifest identity");
        const auto digest = validateCatalog(member, member.contentManifestSha256);
        catalogIdentities.emplace_back(V::Object{{"manifest", member.contentManifestSha256},
            {"catalog_sha256", digest}});
        for (const auto& entry : member.entries) {
            // An item/variant may have one installed owner only, even when a
            // second package claims a different revision or source binding.
            require(owners.insert(entry.binding.item + "/" + entry.binding.variant).second,
                    "Mixed-version item/variant collision");
            const auto item = itemOwners.emplace(entry.binding.item, member.contentManifestSha256);
            require(item.second || item.first->second == member.contentManifestSha256,
                    "Mixed-version item collision");
            require(variantOwners.insert(entry.binding.variant).second,
                    "Duplicate installed variant owner");
            lookup.entries.push_back(entry);
        }
    }
    require(included == expected, "Incomplete installed domain manifest set");
    std::sort(catalogIdentities.begin(), catalogIdentities.end(), [](const V& a, const V& b) {
        return field(a, "manifest").string() < field(b, "manifest").string();
    });
    DomainCoverage result;
    result.profile = snapshot.profile;
    result.evidenceSha256 = snapshot.evidenceHash;
    result.snapshotSha256 = snapshot.snapshotHash;
    result.evidenceMarker = snapshot.marker;
    result.catalogVersion = catalog.version;
    result.catalogSha256 = content::sha256(storage::canonical(V::Object{
        {"version", catalog.version}, {"catalogs", catalogIdentities}}));
    std::set<std::string> originalOwners;
    for (const auto& record : snapshot.records) {
        if (record.kind == Kind::Freeplay) { ++result.ignoredFreeplay; continue; }
        if (record.kind != Kind::Attempt) continue;
        require(!record.key.empty() && originalOwners.insert(record.key).second,
                "Duplicate/empty original Attempt owner");
        if (record.status != "committed" || record.active.numerator() <= 0) continue;
        const auto observed = observedBinding(record);
        const auto found = std::find_if(lookup.entries.begin(), lookup.entries.end(),
            [&](const DomainMetadata& entry) { return bindingValue(entry.binding) == observed; });
        if (found == lookup.entries.end()) {
            result.unmapped.push_back({record.key, mismatchReason(observed, lookup)});
            continue;
        }
        ++result.mappedAttempts;
        for (const auto& domain : found->domains) {
            auto& activity = result.byDomain[domain];
            ++activity.attempts;
            activity.activeSeconds = activity.activeSeconds + record.active;
        }
    }
    return result;
}

DomainCoverage projectDomainCoverage(const storage::Reply& reply, const MultiDomainCatalog& catalog,
                                     const std::string& expectedProfile,
                                     const std::vector<std::string>& expectedManifests) {
    return projectDomainCoverage(adaptSnapshot(reply), catalog, expectedProfile, expectedManifests);
}
} // namespace fathom::progression
