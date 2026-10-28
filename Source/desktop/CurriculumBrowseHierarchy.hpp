#pragma once
#include <array>

namespace fathom::desktop {
// Navigation aliases for the three approved WBS curriculum groups. Section
// names/ranges join all105 levels to the approved source inventory, SHA256
// bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6.
// These labels do not assert that the original sources have Volume metadata.
struct BrowseSection { int volume,first,last; const char* name; };
inline constexpr std::array<BrowseSection,16> browseSections{{
    {1,1,11,"I"},{1,12,20,"II"},{1,21,29,"III"},{1,30,38,"IV"},{1,39,48,"V"},
    {2,49,58,"VI"},{2,59,64,"VII"},{2,65,68,"VIII"},{2,69,72,"IX"},
    {3,73,79,"X"},{3,80,84,"XI"},{3,85,90,"XII"},{3,91,94,"XIII"},
    {3,95,99,"XIV"},{3,100,104,"XV"},{3,105,105,"Final"}
}};
inline constexpr int browseSectionForLevel(int level) {
    for(std::size_t i=0;i<browseSections.size();++i)
        if(level>=browseSections[i].first&&level<=browseSections[i].last)return static_cast<int>(i)+1;
    return 0;
}
}
