#pragma once
#include "tasks/TaskContract.hpp"
#include <filesystem>
#include <optional>
#include <string>

namespace fathom::tasks {
// Exact source identities are loaded only from version-bound compiled closures.
class InstalledManualTaskRegistry final {
public:
    static InstalledManualTaskRegistry load(const std::filesystem::path& directory);
    bool contains(const std::string& sourceIdentity) const noexcept;
    std::optional<Definition> definition(const std::string& sourceIdentity) const;
    const std::string& error() const noexcept { return error_; }
private:
    bool ready_{};
    bool familyReady_{};
    std::string error_;
};
}
