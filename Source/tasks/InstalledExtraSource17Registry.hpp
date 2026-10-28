#pragma once
#include "tasks/ManualProcedureGraph.hpp"
#include <filesystem>
#include <map>
#include <optional>
namespace fathom::tasks::extra_source17 {
// A separate closed package for existing extraSource identities, never a WBS
// child registry. It exposes either an exact qualified task or reference view.
class InstalledExtraSource17Registry final {
public:
    static InstalledExtraSource17Registry load(const std::filesystem::path& packageDirectory,
                                               const std::filesystem::path& hostSourceAssetsRoot);
    std::size_t size() const noexcept { return ready_ ? identities_.size() : 0; }
    bool containsSourceIdentity(const std::string&) const noexcept;
    std::optional<manual_procedure_graph::Definition> definitionForSourceIdentity(const std::string&) const;
    const std::string& error() const noexcept { return error_; }
private:
    bool ready_{false};
    std::map<std::string,std::string> identities_;
    std::string error_;
};
}
