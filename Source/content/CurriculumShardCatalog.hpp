#pragma once

#include <cstddef>
#include <filesystem>

namespace fathom::curriculum {
// Discovery only. This deliberately exposes no lesson, Practice or Attempt admission.
struct ShardInventory {
    std::size_t shardCount = 0;
    std::size_t sourceRecords = 0;
};

ShardInventory discoverShards(const std::filesystem::path& installedResources);
} // namespace fathom::curriculum
