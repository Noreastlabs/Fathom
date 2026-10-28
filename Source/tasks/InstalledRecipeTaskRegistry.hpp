#pragma once
#include "tasks/RecipeTask.hpp"
#include <filesystem>
#include <map>

namespace fathom::tasks::recipes {
// All routes come from the compiled17-key factory after a complete version-bound
// installed snapshot passes. Package JSON never constructs a trusted Definition.
class InstalledRecipeTaskRegistry final {
public:
    static InstalledRecipeTaskRegistry load(const std::filesystem::path& level068Directory);
    bool contains(const std::string& exactSourceKey) const noexcept;
    std::optional<Definition> definition(const std::string& exactSourceKey) const;
    std::optional<std::filesystem::path> installedDefinitionPath(const std::string& exactSourceKey) const;
    std::size_t size() const noexcept { return ready_ ? paths_.size() : 0; }
    std::size_t sourceFilesHashed() const noexcept { return sourceFilesHashed_; }
    const std::string& error() const noexcept { return error_; }
private:
    bool ready_{};
    std::size_t sourceFilesHashed_{};
    std::map<std::string,std::filesystem::path> paths_;
    std::string error_;
};
} // namespace fathom::tasks::recipes
