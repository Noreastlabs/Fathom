#pragma once
#include "storage/StorageEnvelope.hpp"
#include <chrono>
#include <filesystem>
#include <functional>

namespace fathom::storage {
struct RestorePreparationRequest {
    std::filesystem::path archive;
    // Exact historical-reference metadata from the caller's available selection.
    // Entries: {reference: six canonical identity fields, provenance: nonempty text}.
    // This is availability metadata, never curriculum acceptance/runtime admission.
    Value availableReferences = Value::Array{};
};
namespace detail {
Value normalizedRestoreAvailability(const Value&);
Value restoreContentComparison(const Value& manifest,const Value& normalizedAvailable);
// Requires one held ProfileStore maintenance owner and an independently verified
// original snapshot/container receipt. The check closure retains source ownership.
// Writes only inside that newly created private stage. Never replaces live data.
Value prepareRestore(const std::string& operation,const RestorePreparationRequest&,
                     const std::filesystem::path& live,const Value& original,
                     std::chrono::steady_clock::time_point deadline,
                     const std::function<void()>& check,
                     const std::function<void()>& validateFinalAuthority,
                     const std::function<void(const std::string&)>& hook);
}
} // namespace fathom::storage
