#pragma once

#include "progression/ProgressionAdapter.hpp"
#include <map>
#include <stdexcept>

namespace fathom::progression {

struct DomainCoverageError : std::runtime_error { using std::runtime_error::runtime_error; };

// Supplied by an approved content producer. This component never derives a
// domain from an item number, title, level, assessment or exam score.
struct DomainBinding {
    std::string item, variant, contentVersion, sourceManifestSha256;
    std::int64_t contentRevision{};
    std::vector<std::string> sourceRefs;
};
struct DomainMetadata {
    DomainBinding binding;
    std::vector<std::string> domains;
    std::string provenanceReference, provenanceSha256;
    std::string supportingReference{}, supportingSha256{};
    std::string vocabularyReference{}, vocabularySha256{};
};
struct DomainCatalog {
    std::string version, contentManifestSha256;
    std::vector<DomainMetadata> entries;
    // The installed bundle manifest and the source manifest in saved Attempts
    // are separate identities. Empty retains the r01 single-manifest contract.
    std::string sourceManifestSha256{};
};
struct MultiDomainCatalog {
    std::string version;
    std::vector<DomainCatalog> catalogs;
};
struct DomainActivity {
    std::size_t attempts{};
    Rational activeSeconds{};
};
struct UnmappedDomainAttempt {
    std::string originalOwner, reason;
};
struct DomainCoverage {
    std::string profile, evidenceSha256, snapshotSha256;
    std::int64_t evidenceMarker{};
    std::string catalogVersion, catalogSha256;
    std::size_t mappedAttempts{}, ignoredFreeplay{};
    std::map<std::string, DomainActivity> byDomain;
    std::vector<UnmappedDomainAttempt> unmapped;
    // Each explicitly mapped domain receives the full recorded activity. A
    // multi-domain attempt therefore appears in more than one domain row.
    bool overlappingDomainActivity = true;
};

// Pure projection seam for a SnapshotEvidence returned by adaptSnapshot().
// `expectedProfile` and `expectedManifest` must come from the current caller,
// not the saved records. The Reply overload enforces the confirmed-store
// adapter before this projection is used in production.
DomainCoverage projectDomainCoverage(const SnapshotEvidence&, const DomainCatalog&,
                                     const std::string& expectedProfile,
                                     const std::string& expectedManifest);
DomainCoverage projectDomainCoverage(const storage::Reply&, const DomainCatalog&,
                                     const std::string& expectedProfile,
                                     const std::string& expectedManifest);
// The caller supplies the complete finite set of installed bundle manifests.
// No saved Attempt or catalog entry can add a manifest to that set.
DomainCoverage projectDomainCoverage(const SnapshotEvidence&, const MultiDomainCatalog&,
                                     const std::string& expectedProfile,
                                     const std::vector<std::string>& expectedManifests);
DomainCoverage projectDomainCoverage(const storage::Reply&, const MultiDomainCatalog&,
                                     const std::string& expectedProfile,
                                     const std::vector<std::string>& expectedManifests);
} // namespace fathom::progression
