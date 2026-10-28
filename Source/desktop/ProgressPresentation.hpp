#pragma once
#include "progression/ProgressionAdapter.hpp"
#include "content/LessonCatalog.hpp"

namespace fathom::desktop {
// Transient presentation of one confirmed snapshot; never a new history schema.
struct ProgressPresentation {
    json::Value projection;
    std::string text;
    std::string details;
};
ProgressPresentation presentProgress(const storage::Reply&, const std::string& asOf,
                                     std::shared_ptr<const lesson::Catalog> = {});
}
