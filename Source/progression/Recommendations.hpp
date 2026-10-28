#pragma once
#include "progression/ProgressionAdapter.hpp"
#include <optional>

namespace fathom::progression {
struct MetadataError:std::runtime_error { using std::runtime_error::runtime_error; };
// Transient input from a content/practice producer, not a stored record schema.
// Estimates, domains and resource facts are never inferred from an opaque ID.
struct RecommendationItem {
    Query query;
    std::vector<std::string> domains,guidance;
    std::int64_t order=0;
    std::optional<Rational> duration,overhead;
    bool resourceReady=false;
    Value metadataProvenance,resourceEvidence;
};
struct RecommendationCatalog {
    std::string version,contentManifestSha256;
    std::vector<RecommendationItem> items;
};
Value recommendationCatalogValue(const RecommendationCatalog&);
// Pure component seam. Evidence must retain its original ownership and is fully
// revalidated by the accepted progression projection. No cache/history mutation.
Value recommend(const std::vector<Evidence>&,const RecommendationCatalog&,
                std::int64_t budgetSeconds,const std::string& asOf);
// Production store boundary: validates the confirmed original snapshot and binds
// profile/evidence/observations. No store call or new profile/record identity.
Value recommendSnapshot(const storage::Reply&,const RecommendationCatalog&,
                        std::int64_t budgetSeconds,const std::string& asOf);
} // namespace fathom::progression
