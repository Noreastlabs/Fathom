#pragma once
#include <array>
#include <string>
namespace fathom::desktop {
// Presentation only. Exact source identity remains callback-only metadata;
// deliberate Original TXT/PDF browsing is still available and may reveal keys.
inline std::size_t hiddenSevenMotifOrdinal(const std::string& sourceIdentity){
    static constexpr std::array<const char*,6> exact{{
        "level073/modulee/p010-card01/cmajorgmajor",
        "level073/modulee/p010-card02/cmajoremajor",
        "level073/modulee/p010-card03/fmajoramajor",
        "level073/modulee/p011-card01/aminoreminor",
        "level073/modulee/p011-card02/aminorc#minor",
        "level073/modulee/p011-card03/dminorf#minor"}};
    for(std::size_t i=0;i<exact.size();++i)if(sourceIdentity==exact[i])return i+1;
    return 0;
}
inline std::string hiddenSevenLearnerLabel(const std::string& sourceIdentity,const std::string& retainedLabel){
    const auto ordinal=hiddenSevenMotifOrdinal(sourceIdentity);
    return ordinal?"Motif listening comparison "+std::to_string(ordinal):retainedLabel;
}
inline std::string hiddenSevenLearnerLocator(const std::string& sourceIdentity,const std::string& retainedLocator){
    return hiddenSevenMotifOrdinal(sourceIdentity)?
        "Original Level 73 Module E source remains available through deliberate Original TXT/PDF controls. That browsing can disclose the reference; no fresh unseen listening is claimed.":retainedLocator;
}
} // namespace
