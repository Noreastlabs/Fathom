#pragma once
#include "progression/Progression.hpp"
#include "storage/ProfileStore.hpp"

namespace fathom::progression {
struct SnapshotEvidence {
    std::vector<Evidence> records;
    Value::Array notices,originalHistory,historicalObservations;
    std::string profile,evidenceHash,snapshotHash;
    std::int64_t marker=0;
};
Value sourceScope(const Value& allocatedContext);
void validateQuery(const Query&);
bool supportsSourceFact(const Value&);
// Caller supplies only the original confirmed store snapshot. Hash/decoded
// binding checks supplement the store's full authoritative inspection.
SnapshotEvidence adaptSnapshot(const storage::Reply&);
Value projectSnapshot(const SnapshotEvidence&,const std::vector<Query>&,
                      const std::string& asOf);
} // namespace fathom::progression
