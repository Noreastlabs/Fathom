#pragma once

#include "content/LoadCancellation.hpp"
#include <filesystem>
#include <string>
#include <vector>

namespace fathom::curriculum {
struct SourceWorkbook {
    std::string id;
    std::string label;
    int level = 0;
    std::filesystem::path txt;
    std::filesystem::path pdf;
    std::size_t txtBytes = 0;
    std::size_t pdfBytes = 0;
    std::string txtSha256;
    std::string pdfSha256;
    std::size_t lines = 0;
    std::size_t pages = 0;
};

// Exact original sources for browsing; deliberately has no Practice admission API.
class SourceLibrary final {
public:
    static SourceLibrary load(const std::filesystem::path& installedResources,
        const content::CancellationCheck& canceled = {});
    const std::vector<SourceWorkbook>& workbooks() const noexcept { return workbooks_; }
    std::string instructions(const SourceWorkbook& workbook) const;
    std::filesystem::path originalPdf(const SourceWorkbook& workbook) const;
private:
    std::filesystem::path root_;
    std::vector<SourceWorkbook> workbooks_;
};
} // namespace fathom::curriculum
