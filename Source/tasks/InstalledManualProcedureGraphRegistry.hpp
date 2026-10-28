#pragma once
#include "tasks/ManualProcedureGraph.hpp"
#include <filesystem>
#include <map>
namespace fathom::tasks::manual_procedure_graph {
struct InstalledRowBinding final {
    std::filesystem::path bulkDefinitionsPath;
    std::size_t jsonlLine{};
    std::string sourceKey, sourceIdentity, originalRowSha256, contractSha256;
};
// Entire exact224 family, contexts, originals and compiled versions verify
// before routing. Package JSON cannot construct a Definition or admit work.
class InstalledManualProcedureGraphRegistry final {
public:
    static InstalledManualProcedureGraphRegistry load(const std::filesystem::path& packageDirectory,
                                                 const std::filesystem::path& sourceLibraryAssetsRoot);
    bool ready() const noexcept {return ready_;}
    bool containsSourceIdentity(const std::string&) const noexcept;
    std::optional<Definition> definitionForSourceIdentity(const std::string&) const;
    bool contains(const std::string&) const noexcept;
    std::optional<Definition> definition(const std::string&) const;
    std::optional<std::filesystem::path> installedDefinitionPath(const std::string&) const;
    std::optional<InstalledRowBinding> rowBinding(const std::string&) const;
    std::size_t size() const noexcept {return ready_?paths_.size():0;}
    std::size_t sourceFilesHashed() const noexcept {return sourceFilesHashed_;}
    const std::string& error() const noexcept {return error_;}
private:
    bool ready_{};
    std::size_t sourceFilesHashed_{};
    std::map<std::string,InstalledRowBinding> paths_;
    std::string error_;
    std::map<std::string,std::string> identities_;
};
} // namespace fathom::tasks::manual_procedure_graph
