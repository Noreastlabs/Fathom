#pragma once
#include "storage/StorageEnvelope.hpp"
#include <chrono>
#include <filesystem>
#include <functional>
#include <memory>

namespace fathom::storage {
struct RestoreApplyRequest {
    std::filesystem::path preview;
    Value previewFile; // Exact r06 {device,inode,bytes,sha256} receipt.
    std::string confirmationSha256;
    Value availableReferences=Value::Array{};
    bool explicitConfirmation=false,stopped=false,unresolvedWrites=true;
    std::chrono::milliseconds timeout{300000};
    std::function<bool()> cancelled;
};
namespace detail {
// Normal open must refuse a pending marker before touching SQLite. Recovery-only
// construction holds the normal lease but leaves SQLite closed until reconciliation.
void checkRestoreOpen(const std::filesystem::path& live,const std::string& recoveryOperation);
struct RestoreOwner {
    std::function<void()> checkLease;
    // Full authority/row counts, UUID/marker/schema; validates unsettled outcomes.
    std::function<Value()> currentBoundary;
    std::function<void()> checkpointAndClose;
    // Validate exact native inode and logical boundary BEFORE writer transition.
    std::function<void(const Value&,const Value&,bool allowLaterWrites)> reopen;
    std::function<void(const std::string&)> phase;
};
class RestoreApplier final {
public:
    RestoreApplier(std::string operation,RestoreApplyRequest,
                   std::filesystem::path live,RestoreOwner);
    ~RestoreApplier();
    RestoreApplier(const RestoreApplier&)=delete;
    RestoreApplier& operator=(const RestoreApplier&)=delete;
    Value apply();
    Value reconcile(); // Never issues a rename.
    bool uncertain()const noexcept;
    Value recoveryDetails()const;
private:
    struct Impl;std::unique_ptr<Impl> impl_;
};
}
} // namespace fathom::storage
