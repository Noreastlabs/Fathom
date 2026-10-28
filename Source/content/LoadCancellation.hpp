#pragma once
#include <functional>
#include <stdexcept>

namespace fathom::content {
using CancellationCheck = std::function<bool()>;

// Cancellation abandons private construction. It is not a validation refusal
// and must never produce a partially checked Result or Catalog.
class LoadCanceled final : public std::runtime_error {
public:
    LoadCanceled() : std::runtime_error("Source loading canceled") {}
};
inline void checkLoadCanceled(const CancellationCheck& canceled) {
    if(canceled&&canceled())throw LoadCanceled{};
}
}
