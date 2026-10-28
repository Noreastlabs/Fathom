#pragma once
#include "progression/ProgressionAdapter.hpp"
#include "content/LessonCatalog.hpp"

namespace fathom::progression {
// Display-only projection. It never writes history or feeds Progression::project.
Value projectSelectedCaseComparison(const SnapshotEvidence&, const lesson::Catalog&,
                                    const std::string& asOfUtc);
}
