#pragma once
#include "storage/ProfileStore.hpp"
#include <filesystem>

namespace fathom::storage {
struct HistoryCsv {
    std::string bytes;
    Value rows;
    Value report;
};
// null selects every finalized outcome and Session; [] explicitly selects none.
// An array names distinct finalized owners. Session totals cover selected children.
HistoryCsv historyCsv(const Reply& confirmedSnapshot,const Value& selectedOwners=nullptr);
// Exact accepted20-column typed representation; useful to consumers and pure tests.
Value historyCsvColumns();
std::string encodeHistoryRows(const Value& typedRows);
std::string historySeconds(const Rational& exact);
std::string historyTempo(const Rational& exact);
// Explicit .text-v2.csv path, exclusive atomic publication; never overwrites.
Value publishHistoryCsv(const std::filesystem::path& destination,const HistoryCsv&);
// CLI maintenance gate; pure committed-history projection may still exclude these.
bool historyMaintenanceQuiescent(const Reply& confirmedSnapshot);
} // namespace fathom::storage
