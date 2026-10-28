#pragma once
#include "content/LessonCatalog.hpp"
#include <functional>
#include <mutex>

namespace fathom::lesson {
// One exact installed resource generation. Catalogs are immutable source
// snapshots; every requested owner is freshly hash-checked before publication.
// Preparation is serialized and cancellable between complete owner loads.
class SelectedCatalogStore final {
public:
    struct Request {
        std::string itemId, expectedPackageHash;
    };
    struct Preparation {
        std::vector<std::string> requiredOwners, preparedOwners;
        std::size_t loadedOwners{}, memoryCacheHits{};
        std::size_t recheckedAssets{}, recheckedBytes{};
        bool canceled=false;
        std::uint64_t revision{};
    };
    SelectedCatalogStore(std::filesystem::path base,
        std::vector<std::filesystem::path> exactInstalledExtensions);
    std::shared_ptr<const Catalog> prepare(const std::vector<Request>&,
        std::function<bool()> canceled = {});
    // Owner resolution is finite and compiled. Unknown IDs are checked against
    // the verified base during prepare, never discovered from dropped files.
    std::vector<std::string> requiredOwners(const std::vector<Request>&) const;
    std::vector<std::string> cachedOwnerNames() const;
    std::vector<std::string> preparedOwnerNames() const;
    Preparation lastPreparation() const;
    std::uint64_t revision() const;
private:
    std::filesystem::path base_;
    std::vector<std::filesystem::path> extensions_;
    std::map<std::string,std::size_t> itemOwners_;
    std::map<std::string,std::shared_ptr<const Catalog>> cache_;
    std::shared_ptr<const Catalog> prepared_;
    std::vector<std::string> preparedNames_;
    std::uint64_t revision_{};
    Preparation last_;
    mutable std::mutex stateMutex_;
    std::mutex preparationMutex_;
};
}
