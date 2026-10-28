#pragma once
#include "storage/StorageEnvelope.hpp"
#include <array>
#include <cstdint>
#include <functional>
#include <sys/stat.h>

namespace fathom::storage {
// Only the fixed Fathom archive entries. This is not an external ZIP importer.
struct StoredZip64Layout {
    std::array<std::string,2> localHeaders,centralHeaders;
    std::array<std::uint64_t,2> dataOffsets{};
    std::string tail;
    std::uint64_t centralOffset=0,archiveBytes=0;
};
StoredZip64Layout storedZip64Layout(const std::array<std::uint64_t,2>& sizes,
                                   const std::array<std::uint32_t,2>& crc);
struct StoredZip64Source {
    int descriptor=-1; // Borrowed, pinned verified candidate; never closed here.
    std::uint64_t bytes=0;
    std::string sha256;
};
struct StoredZip64Result {
    Value file;
    struct stat verifiedIdentity{}; // Exact descriptor stat bound to reread digest.
};
// output must be a new empty private regular file, held by the caller through
// receipt. Same maintenance deadline/check applies to prepass, write and reread.
StoredZip64Result writeStoredZip64(int output,const std::array<StoredZip64Source,2>&,
                      const std::function<void()>& check,
                      const std::function<void(const std::string&)>& hook={});
} // namespace fathom::storage
