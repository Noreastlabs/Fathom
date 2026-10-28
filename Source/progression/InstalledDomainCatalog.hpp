#pragma once

#include "progression/ProgressDomainCoverage.hpp"
#include "content/LessonCatalog.hpp"

namespace fathom::progression {

// Constructs the bounded proposal from the current installed Catalog's actual
// Practice admissions. Throws if any bundle, version, variant or source fact
// differs from the reviewed identities. P02 owns adoption and presentation.
MultiDomainCatalog installedDomainCatalog(const lesson::Catalog& installed);
std::vector<std::string> installedDomainManifests();

} // namespace fathom::progression
