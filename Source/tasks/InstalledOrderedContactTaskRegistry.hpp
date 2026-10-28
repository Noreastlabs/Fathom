#pragma once
#include "tasks/OrderedContactTask.hpp"
#include <filesystem>
#include <map>
#include <memory>

namespace fathom::tasks::ordered_contacts {
// Closed, version-bound manual guidance candidates. The JSON table cannot
// create a trusted source definition or authorize Practice, sound or credit.
class InstalledOrderedContactTaskRegistry final {
public:
    static InstalledOrderedContactTaskRegistry load(const std::filesystem::path& packageDirectory,
                                                   const std::filesystem::path& sourceLibraryAssetsRoot);
    std::size_t size() const noexcept { return ready_ ? identities_.size() : 0; }
    bool containsSourceKey(const std::string&) const noexcept;
    bool containsSourceIdentity(const std::string&) const noexcept;
    std::optional<Definition> definitionForSourceKey(const std::string&) const;
    std::optional<Definition> definitionForSourceIdentity(const std::string&) const;
    std::unique_ptr<manual::Task> taskForSourceKey(const std::string&) const;
    std::size_t sourceFilesHashed() const noexcept { return sourceFilesHashed_; }
    const std::string& error() const noexcept { return error_; }
private:
    bool ready_{false};
    std::size_t sourceFilesHashed_{0};
    std::string error_;
    std::map<std::string, std::string> identities_, keysByIdentity_;
};
} // namespace fathom::tasks::ordered_contacts
