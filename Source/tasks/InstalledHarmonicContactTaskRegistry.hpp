#pragma once
#include "tasks/HarmonicContactFamily.hpp"
#include <filesystem>
#include <map>
namespace fathom::tasks::harmonic_contacts {
// Closed118 definition lookup. A package failure grants zero definitions.
class InstalledHarmonicContactTaskRegistry final {
public:
    static InstalledHarmonicContactTaskRegistry load(const std::filesystem::path& packageDirectory,
                                                     const std::filesystem::path& sourceLibraryAssetsRoot);
    std::size_t size()const noexcept{return ready_?keys_.size():0;}
    bool containsSourceKey(const std::string&)const noexcept;
    bool containsSourceIdentity(const std::string&)const noexcept;
    std::optional<Definition> definitionForSourceKey(const std::string&)const;
    std::optional<Definition> definitionForSourceIdentity(const std::string&)const;
    std::size_t sourceFilesHashed()const noexcept{return sourceFilesHashed_;}
    bool ownerBridgeReady()const noexcept{return ready_&&ownerBridgeReady_;}
    const std::string& error()const noexcept{return error_;}
private:
    bool ready_{false},ownerBridgeReady_{false};std::size_t sourceFilesHashed_{0};std::string error_;
    std::map<std::string,std::string> keys_,identities_;
};
}
