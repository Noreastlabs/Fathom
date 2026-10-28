#pragma once
#include "tasks/AdvancedRecipeTask.hpp"
#include <filesystem>
#include <map>

namespace fathom::tasks::advanced {
// Complete closed56 package verification precedes every native route. Installed
// JSON never constructs a trusted Definition or allocates a canonical identity.
class InstalledAdvancedRecipeRegistry final {
public:
    static InstalledAdvancedRecipeRegistry load(const std::filesystem::path& advancedDirectory);
    bool ready() const noexcept { return ready_; }
    bool contains(const std::string& exactSourceKey) const noexcept;
    std::optional<Definition> definition(const std::string& exactSourceKey) const;
    std::optional<std::filesystem::path> installedDefinitionPath(const std::string& exactSourceKey) const;
    std::size_t size() const noexcept { return ready_?paths_.size():0; }
    std::size_t sourceFilesHashed() const noexcept { return sourceFilesHashed_; }
    const std::string& error() const noexcept { return error_; }
private:
    bool ready_{};
    std::size_t sourceFilesHashed_{};
    std::map<std::string,std::filesystem::path> paths_;
    std::string error_;
};
} // namespace fathom::tasks::advanced
