#include "content/LearnSourceIndex.hpp"
#include "content/LearnSourceIndexPins.hpp"
#include "content/Canonical.hpp"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <sstream>
// Linked against actual fathom_content IO/hash and fathom_lessons loader.
using namespace fathom;
int main(int argc,char** argv){
 try{
  if(argc!=2)throw std::runtime_error("resource directory required");
  int checks=0;const auto check=[&](bool okay,const char* message){++checks;if(!okay)throw std::runtime_error(message);};
  const auto index=learn::SourceIndex::load(argv[1]);check(index->levels().size()==105,"105 levels");check(index->exercises().size()==7321,"7321 source rows");
  check(index->exercises()[index->level(12).sublevels.back().exercises.front()].locator.find("TXT locator unavailable")!=std::string::npos,"PDF-only source row retains explicit unavailable TXT locator");
  const auto& set=index->level(2).sublevels.front();check(set.exercises.size()==12,"Level2 first SET has12 exercises");
  const auto& first=index->exercises()[set.exercises[4]];const auto& stop=index->exercises()[set.exercises[11]];
  check(index->range(2,set.key,first.source.sourceExerciseKey,stop.source.sourceExerciseKey).size()==8,"Level2 within-sublevel5to12 inclusive");
  check(first.bindings.empty(),"Level2 source exercise5 remains unavailable");
  const auto& next=index->level(2).sublevels[1];const auto& cross=index->exercises()[next.exercises[1]];
  bool refused=false;try{index->range(2,set.key,first.source.sourceExerciseKey,cross.source.sourceExerciseKey);}catch(const std::exception&){refused=true;}check(refused,"Level2 source5to14 crosses SET and refuses");
  const auto& ladder=index->level(12).sublevels.front();const auto range=index->range(12,ladder.key,index->exercises()[ladder.exercises[1]].source.sourceExerciseKey,index->exercises()[ladder.exercises[4]].source.sourceExerciseKey);
  check(range.size()==4,"Level12rung2through5 exact range");std::set<std::string> items;
  for(const auto* row:range){check(row->bindings.size()==1&&row->bindings.front().exact,"Level12 whole-unit exact binding");check(items.insert(row->bindings.front().itemId).second,"Level12 unique item per rung");}
  const auto& rung13=index->exercises()[index->level(13).sublevels.front().exercises[1]];
  check(std::none_of(rung13.bindings.begin(),rung13.bindings.end(),[](const auto& b){return b.exact;}),"Level13rung2 composite coverage is not exact launch");
  const auto& rung13three=index->exercises()[index->level(13).sublevels.front().exercises[2]];
  check(rung13three.source.sourceExerciseKey=="printed:l013:complete-tablature:rung-03-of-13-b-major-root-on-low-e-fret-7-frame-6-9"&&
        rung13three.bindings.size()==1&&rung13three.bindings.front().exact&&
        rung13three.bindings.front().itemId=="fg:item:001130"&&
        rung13three.bindings.front().variants==std::vector<std::string>{"fg:variant:007382","fg:variant:007383"},
        "Level13 Rung03 only printed exact row binds one case and two D/U variants");
  const auto& rung13four=index->exercises()[index->level(13).sublevels.front().exercises[3]];
  check(rung13four.source.sourceExerciseKey=="printed:l013:complete-tablature:rung-04-of-13-c-major-root-on-low-e-fret-8-frame-7-10"&&
        rung13four.locator.find("PDF pages [3]")!=std::string::npos&&
        rung13four.bindings.size()==1&&rung13four.bindings.front().exact&&
        rung13four.bindings.front().itemId=="fg:item:001183"&&
        rung13four.bindings.front().variants==std::vector<std::string>{"fg:variant:007706","fg:variant:007707"},
        "Level13 Rung04 corrected physical page4 exact row binds one C-major D/U case");
  const auto& rung13five=index->exercises()[index->level(13).sublevels.front().exercises[4]];
  check(rung13five.source.sourceExerciseKey=="printed:l013:complete-tablature:rung-05-of-13-db-major-root-on-low-e-fret-9-frame-8-11"&&
        rung13five.locator.find("PDF pages [3]")!=std::string::npos&&
        rung13five.bindings.size()==1&&rung13five.bindings.front().exact&&
        rung13five.bindings.front().itemId=="fg:item:001184"&&
        rung13five.bindings.front().variants==std::vector<std::string>{"fg:variant:007708","fg:variant:007709"},
        "Level13 Rung05 corrected physical page4 exact row binds one Db-major D/U case");
  const auto& rung13six=index->exercises()[index->level(13).sublevels.front().exercises[5]];
  check(rung13six.source.sourceExerciseKey=="printed:l013:complete-tablature:rung-06-of-13-d-major-root-on-low-e-fret-10-frame-9-12"&&
        rung13six.locator.find("PDF pages [3]")!=std::string::npos&&
        rung13six.auditStatus.find("missing")!=std::string::npos&&rung13six.bindings.empty(),
        "Level13 Rung06 PDF physical page4 locator corrected; case remains unavailable");
  const auto& rung13seven=index->exercises()[index->level(13).sublevels.front().exercises[6]];
  check(rung13seven.source.sourceExerciseKey=="printed:l013:complete-tablature:rung-07-of-13-eb-major-root-on-low-e-fret-11-frame-10-13"&&
        rung13seven.locator.find("PDF pages [4]")!=std::string::npos&&
        rung13seven.auditStatus.find("missing")!=std::string::npos&&rung13seven.bindings.empty(),
        "Level13 Rung07 physical page5 locator corrected; case remains unavailable");
  const auto& rung13eight=index->exercises()[index->level(13).sublevels.front().exercises[7]];
  check(rung13eight.source.sourceExerciseKey=="printed:l013:complete-tablature:rung-08-of-13-e-major-root-on-low-e-fret-12-frame-11-14"&&
        rung13eight.locator.find("PDF pages [4]")!=std::string::npos&&
        rung13eight.auditStatus.find("missing")!=std::string::npos&&rung13eight.bindings.empty(),
        "Level13 Rung08 physical page5 locator corrected; case remains unavailable");
  const auto& rung14three=index->exercises()[index->level(14).sublevels.front().exercises[2]];
  check(rung14three.source.sourceExerciseKey=="printed:l014:complete-tablature:rung-03-of-13-b-major-root-on-low-e-fret-7-frame-6-9"&&
        rung14three.bindings.size()==1&&rung14three.bindings.front().exact&&
        rung14three.bindings.front().itemId=="fg:item:001180"&&
        rung14three.bindings.front().variants==std::vector<std::string>{"fg:variant:007698","fg:variant:007699"},
        "Level14 Rung03 exact one-cell source row binds two D/U variants");
  const auto& rung14four=index->exercises()[index->level(14).sublevels.front().exercises[3]];
  check(rung14four.source.sourceExerciseKey=="printed:l014:complete-tablature:rung-04-of-13-c-major-root-on-low-e-fret-8-frame-7-10"&&
        rung14four.locator.find("PDF pages [3]")!=std::string::npos&&
        rung14four.auditStatus.find("missing")!=std::string::npos&&rung14four.bindings.empty(),
        "Level14 Rung04 physical page4 locator corrected; case remains unavailable");
  const auto& l15=index->level(15).sublevels.front().exercises;
  const auto& rung15one=index->exercises()[l15[0]];
  const auto& rung15two=index->exercises()[l15[1]];
  const auto& rung15three=index->exercises()[l15[2]];
  const auto& rung15four=index->exercises()[l15[3]];
  const auto& rung15five=index->exercises()[l15[4]];

  check(rung15one.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-01-of-13-a-major-root-on-low-e-fret-5-frame-4-7"&&
        rung15one.locator.find("PDF pages [2]")!=std::string::npos&&rung15one.bindings.size()==2&&
        !rung15one.bindings.front().exact&&rung15one.bindings.back().exact&&
        rung15one.bindings.back().itemId=="fg:item:001157",
        "Level15 Rung01 source row and existing Learn binding state unchanged");
  check(rung15two.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-02-of-13-bb-major-root-on-low-e-fret-6-frame-5-8"&&
        rung15two.locator.find("PDF pages [2]")!=std::string::npos&&
        rung15two.bindings.size()==1&&rung15two.bindings.front().exact&&
        rung15two.bindings.front().itemId=="fg:item:001181"&&
        rung15two.bindings.front().variants==std::vector<std::string>{"fg:variant:007702","fg:variant:007703"},
        "Level15 Rung02 printed page3 exact two D/U choices");
  check(rung15three.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-03-of-13-b-major-root-on-low-e-fret-7-frame-6-9"&&
        rung15three.locator.find("PDF pages [3]")!=std::string::npos&&
        rung15three.bindings.size()==1&&rung15three.bindings.front().exact&&
        rung15three.bindings.front().itemId=="fg:item:001182"&&
        rung15three.bindings.front().variants==std::vector<std::string>{"fg:variant:007704","fg:variant:007705"},
        "Level15 Rung03 corrected printed page4 exact two D/U choices");
  check(rung15four.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-04-of-13-c-major-root-on-low-e-fret-8-frame-7-10"&&
        rung15four.locator.find("PDF pages [3]")!=std::string::npos&&
        rung15four.bindings.size()==1&&rung15four.bindings.front().exact&&
        rung15four.bindings.front().itemId=="fg:item:001186"&&
        rung15four.bindings.front().variants==std::vector<std::string>{"fg:variant:007712","fg:variant:007713"},
        "Level15 Rung04 physical page4 exact C-major D/U candidate binding");
  check(rung15five.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-05-of-13-db-major-root-on-low-e-fret-9-frame-8-11"&&
        rung15five.locator.find("PDF pages [4]")!=std::string::npos&&
        rung15five.bindings.size()==1&&rung15five.bindings.front().exact&&
        rung15five.bindings.front().itemId=="fg:item:001185"&&
        rung15five.bindings.front().variants==std::vector<std::string>{"fg:variant:007710","fg:variant:007711"},
        "Level15 Rung05 physical page5 exact candidate binding");
  const auto& rung15six=index->exercises()[l15[5]];
  check(rung15six.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-06-of-13-d-major-root-on-low-e-fret-10-frame-9-12"&&
        rung15six.locator.find("PDF pages [4]")!=std::string::npos&&
        rung15six.bindings.size()==1&&rung15six.bindings.front().exact&&
        rung15six.bindings.front().itemId=="fg:item:001187"&&
        rung15six.bindings.front().variants==std::vector<std::string>{"fg:variant:007714","fg:variant:007715"},
        "Level15 Rung06 physical page5 exact D-major D/U candidate binding");
  const auto& rung15seven=index->exercises()[l15[6]];
  check(rung15seven.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-07-of-13-eb-major-root-on-low-e-fret-11-frame-10-13"&&
        rung15seven.locator.find("PDF pages [5]")!=std::string::npos&&
        rung15seven.auditStatus.find("missing")!=std::string::npos&&rung15seven.bindings.empty(),
        "Level15 Rung07 physical page6 corrected; remains unavailable and empty-bound");
  const auto& rung15eight=index->exercises()[l15[7]];
  const auto& rung15nine=index->exercises()[l15[8]];
  check(rung15eight.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-08-of-13-e-major-root-on-low-e-fret-12-frame-11-14"&&
        rung15eight.locator.find("PDF pages [5]")!=std::string::npos&&
        rung15eight.auditStatus.find("missing")!=std::string::npos&&rung15eight.bindings.empty(),
        "Level15 Rung08 points to physical PDF page6 and remains unavailable");
  check(rung15nine.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-09-of-13-f-major-root-on-low-e-fret-13-frame-12-15"&&
        rung15nine.locator.find("PDF pages [6]")!=std::string::npos&&
        rung15nine.auditStatus.find("missing")!=std::string::npos&&rung15nine.bindings.empty(),
        "Level15 Rung09 points to physical PDF page7 and remains unavailable");
  const auto& rung15ten=index->exercises()[l15[9]];
  check(rung15ten.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16"&&
        rung15ten.locator.find("PDF pages [6]")!=std::string::npos&&
        rung15ten.auditStatus.find("missing")!=std::string::npos&&rung15ten.bindings.empty(),
        "Level15 Rung10 corrected physical PDF page7 remains unavailable");
  const auto& rung15eleven=index->exercises()[l15[10]];
  check(rung15eleven.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-11-of-13-g-major-root-on-low-e-fret-15-frame-14-17"&&
        rung15eleven.locator.find("PDF pages [7]")!=std::string::npos&&
        rung15eleven.auditStatus.find("missing")!=std::string::npos&&rung15eleven.bindings.empty(),
        "Level15 Rung11 corrected physical PDF page8 remains unavailable");
  const auto& rung15twelve=index->exercises()[l15[11]];
  check(rung15twelve.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-12-of-13-ab-major-root-on-low-e-fret-16-frame-15-18"&&
        rung15twelve.locator.find("PDF pages [7]")!=std::string::npos&&
        rung15twelve.auditStatus.find("missing")!=std::string::npos&&rung15twelve.bindings.empty(),
        "Level15 Rung12 corrected physical PDF page8 remains unavailable");
  const auto& rung16ten=index->exercises()[index->level(16).sublevels.front().exercises[9]];
  check(rung16ten.source.sourceExerciseKey=="printed:l016:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16"&&
        rung16ten.locator.find("PDF pages [5]")!=std::string::npos&&
        rung16ten.auditStatus.find("missing")!=std::string::npos&&rung16ten.bindings.empty(),
        "Level16 Rung10 corrected physical PDF page6 remains unavailable");
  const auto& rung16eleven=index->exercises()[index->level(16).sublevels.front().exercises[10]];
  const auto& rung16twelve=index->exercises()[index->level(16).sublevels.front().exercises[11]];
  check(rung16eleven.source.sourceExerciseKey=="printed:l016:complete-tablature:rung-11-of-13-g-major-root-on-low-e-fret-15-frame-14-17"&&
        rung16eleven.locator.find("PDF pages [5]")!=std::string::npos&&
        rung16eleven.auditStatus.find("missing")!=std::string::npos&&rung16eleven.bindings.empty(),
        "Level16 Rung11 corrected physical PDF page6 remains unavailable");
  check(rung16twelve.source.sourceExerciseKey=="printed:l016:complete-tablature:rung-12-of-13-ab-major-root-on-low-e-fret-16-frame-15-18"&&
        rung16twelve.locator.find("PDF pages [5]")!=std::string::npos&&
        rung16twelve.auditStatus.find("missing")!=std::string::npos&&rung16twelve.bindings.empty(),
        "Level16 Rung12 corrected physical PDF page6 remains unavailable");
  const auto& rung17ten=index->exercises()[index->level(17).sublevels.front().exercises[9]];
  check(rung17ten.source.sourceExerciseKey=="printed:l017:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16"&&
        rung17ten.locator.find("PDF pages [6]")!=std::string::npos&&
        rung17ten.auditStatus.find("missing")!=std::string::npos&&rung17ten.bindings.empty(),
        "Level17 Rung10 corrected physical PDF page7 remains unavailable");
  const auto& rung18ten=index->exercises()[index->level(18).sublevels.front().exercises[9]];
  check(rung18ten.source.sourceExerciseKey=="printed:l018:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16"&&
        rung18ten.locator.find("PDF pages [6]")!=std::string::npos&&
        rung18ten.auditStatus.find("missing")!=std::string::npos&&rung18ten.bindings.empty(),
        "Level18 Rung10 corrected physical PDF page7 remains unavailable");
  const auto& rung19ten=index->exercises()[index->level(19).sublevels.front().exercises[9]];
  check(rung19ten.source.sourceExerciseKey=="printed:l019:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16"&&
        rung19ten.locator.find("PDF pages [6]")!=std::string::npos&&
        rung19ten.auditStatus.find("missing")!=std::string::npos&&rung19ten.bindings.empty(),
        "Level19 Rung10 corrected physical PDF page7 remains unavailable");
  const auto l20m1=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
    return row.source.sourceExerciseKey=="printed:l020:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16:module-1-linear-scale-30-notes";});
  const auto l20m2=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
    return row.source.sourceExerciseKey=="printed:l020:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16:module-2-three-note-roll-78-notes";});
  check(l20m1!=index->exercises().end()&&l20m1->locator.find("PDF pages [20]")!=std::string::npos&&
        l20m1->auditStatus.find("missing")!=std::string::npos&&l20m1->bindings.empty(),
        "Level20 Rung10 Module1 physical PDF page21 remains unavailable");
  check(l20m2!=index->exercises().end()&&l20m2->locator.find("PDF pages [20]")!=std::string::npos&&
        l20m2->auditStatus.find("missing")!=std::string::npos&&l20m2->bindings.empty(),
        "Level20 Rung10 Module2 physical PDF page21 remains unavailable");
  const auto l20m3=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
    return row.source.sourceExerciseKey=="printed:l020:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16:module-3-four-note-roll-96-notes";});
  check(l20m3!=index->exercises().end()&&l20m3->locator.find("PDF pages [20]")!=std::string::npos&&
        l20m3->auditStatus.find("missing")!=std::string::npos&&l20m3->bindings.empty(),
        "Level20 Rung10 Module3 physical PDF page21 remains unavailable");
  for(const auto& fixture:std::vector<std::pair<std::string,std::string>>{
      {"printed:l031:complete-tablature:rung-10-of-13-gb-major-pentatonic-root-on-low-e-fret-14-frame-13-16","PDF pages [5]"},
      {"printed:l032:rung-10-of-13-gb-major-pentatonic-root-on-low-e-fret-14-frame-13-16:module-a-three-note-roll","PDF pages [11]"}}){
    const auto it=std::find_if(index->exercises().begin(),index->exercises().end(),[&](const auto& row){return row.source.sourceExerciseKey==fixture.first;});
    check(it!=index->exercises().end()&&it->locator.find(fixture.second)!=std::string::npos&&
          it->auditStatus.find("missing")!=std::string::npos&&it->bindings.empty(),
          "Level31/32 Rung10 reviewed PDF locator remains unavailable");
  }
  const auto& rung25=index->exercises()[index->level(25).sublevels.front().exercises.front()];
  check(rung25.bindings.size()==1&&rung25.bindings.front().exact&&rung25.bindings.front().itemId=="fg:item:001176","Accepted49 Level25 explicit overlay");
  const auto& rung08=index->exercises()[index->level(12).sublevels.front().exercises[7]];
  check(rung08.source.sourceExerciseKey=="printed:l012:complete-tablature:rung-08-of-13-e-major-root-on-low-e-fret-12-frame-11-14"&&
        rung08.locator.find("PDF pages [3]")!=std::string::npos&&
        rung08.bindings.size()==1&&rung08.bindings.front().exact&&
        rung08.bindings.front().itemId=="fg:item:001178"&&
        rung08.bindings.front().variants==std::vector<std::string>{"fg:variant:007694","fg:variant:007695"},
        "Rung08 printed exact source row binds the one canonical case and D/U variants");
  const auto& ex002=index->exercises()[index->level(2).sublevels.front().exercises[1]];
  check(ex002.source.sourceExerciseKey=="printed:l002:set-1-of-9-exercises-001-012:exercise-002-1213"&&
        ex002.bindings.size()==1&&ex002.bindings.front().exact&&
        ex002.bindings.front().itemId=="fg:item:001188"&&
        ex002.bindings.front().variants==std::vector<std::string>{"fg:variant:007716","fg:variant:007717"}&&
        ex002.auditStatus.find("prepared_only")!=std::string::npos,
        "Level2 Exercise002 exact candidate binding preserves base prepared-only status");
  for(std::size_t neighbor:{std::size_t{0},std::size_t{2}}){
    const auto& other=index->exercises()[index->level(2).sublevels.front().exercises[neighbor]];
    check(other.bindings.empty()&&other.auditStatus.find("prepared_only")!=std::string::npos,
          "Level2 Exercise001/003 remain unavailable and empty-bound");}
  const auto modeB001=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l003:set-1-of-9-exercises-001-012:mode-b-1-3-early-transfer:exercise-001-1212";});
  check(modeB001!=index->exercises().end()&&modeB001->bindings.size()==1&&
        modeB001->bindings.front().exact&&modeB001->bindings.front().itemId=="fg:item:000240"&&
        modeB001->bindings.front().variants==std::vector<std::string>{"fg:variant:000827","fg:variant:000829"}&&
        modeB001->auditStatus.find("prepared_only")!=std::string::npos,
        "Level3 ModeB001 exact second-pass candidate binds only source-authored D/U variants");
  const auto modeB002=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l003:set-1-of-9-exercises-001-012:mode-b-1-3-early-transfer:exercise-002-1213";});
  check(modeB002!=index->exercises().end()&&modeB002->bindings.empty(),
        "Neighboring Level3 ModeB002 remains unavailable");
  const auto level4ex002=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-002-1213";});
  check(level4ex002!=index->exercises().end()&&level4ex002->bindings.size()==1&&
        level4ex002->bindings.front().exact&&level4ex002->bindings.front().itemId=="fg:item:000445"&&
        level4ex002->bindings.front().variants==std::vector<std::string>{"fg:variant:003287","fg:variant:003289"}&&
        level4ex002->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise002 selected second-pass source row binds only D/U");
  const auto level4ex003=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-003-1214";});
  check(level4ex003!=index->exercises().end()&&level4ex003->bindings.size()==1&&
        level4ex003->bindings.front().exact&&level4ex003->bindings.front().itemId=="fg:item:000446"&&
        level4ex003->bindings.front().variants==std::vector<std::string>{"fg:variant:003299","fg:variant:003301"}&&
        level4ex003->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise003 selected second-pass source row binds only D/U");
  const auto level4ex004=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-004-1231";});
  check(level4ex004!=index->exercises().end()&&level4ex004->bindings.size()==1&&
        level4ex004->bindings.front().exact&&level4ex004->bindings.front().itemId=="fg:item:000447"&&
        level4ex004->bindings.front().variants==std::vector<std::string>{"fg:variant:003311","fg:variant:003313"}&&
        level4ex004->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise004 selected second-pass source row binds only D/U");
  const auto level4ex005=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-005-1232";});
  check(level4ex005!=index->exercises().end()&&level4ex005->bindings.size()==1&&
        level4ex005->bindings.front().exact&&level4ex005->bindings.front().itemId=="fg:item:000448"&&
        level4ex005->bindings.front().variants==std::vector<std::string>{"fg:variant:003323","fg:variant:003325"}&&
        level4ex005->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise005 selected second-pass source row binds only D/U");
  const auto level4ex006=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-006-1234";});
  check(level4ex006!=index->exercises().end()&&level4ex006->bindings.size()==1&&
        level4ex006->bindings.front().exact&&level4ex006->bindings.front().itemId=="fg:item:000449"&&
        level4ex006->bindings.front().variants==std::vector<std::string>{"fg:variant:003335","fg:variant:003337"}&&
        level4ex006->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise006 selected second-pass source row binds only D/U");
  const auto level4ex007=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-007-1241";});
  check(level4ex007!=index->exercises().end()&&level4ex007->bindings.size()==1&&
        level4ex007->bindings.front().exact&&level4ex007->bindings.front().itemId=="fg:item:000450"&&
        level4ex007->bindings.front().variants==std::vector<std::string>{"fg:variant:003347","fg:variant:003349"}&&
        level4ex007->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise007 selected second-pass source row binds only D/U");
  const auto level4ex008=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-008-1242";});
  check(level4ex008!=index->exercises().end()&&level4ex008->bindings.size()==1&&
        level4ex008->bindings.front().exact&&level4ex008->bindings.front().itemId=="fg:item:000451"&&
        level4ex008->bindings.front().variants==std::vector<std::string>{"fg:variant:003359","fg:variant:003361"}&&
        level4ex008->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise008 selected second-pass source row binds only D/U");
  const auto level4ex009=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-009-1243";});
  check(level4ex009!=index->exercises().end()&&level4ex009->bindings.size()==1&&
        level4ex009->bindings.front().exact&&level4ex009->bindings.front().itemId=="fg:item:000452"&&
        level4ex009->bindings.front().variants==std::vector<std::string>{"fg:variant:003371","fg:variant:003373"}&&
        level4ex009->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise009 selected second-pass source row binds only D/U");
  const auto level4ex010=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-010-1312";});
  check(level4ex010!=index->exercises().end()&&level4ex010->bindings.size()==1&&
        level4ex010->bindings.front().exact&&level4ex010->bindings.front().itemId=="fg:item:000453"&&
        level4ex010->bindings.front().variants==std::vector<std::string>{"fg:variant:003383","fg:variant:003385"}&&
        level4ex010->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise010 selected second-pass source row binds only D/U");
  const auto level4ex011=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-011-1313";});
  check(level4ex011!=index->exercises().end()&&level4ex011->bindings.size()==1&&
        level4ex011->bindings.front().exact&&level4ex011->bindings.front().itemId=="fg:item:000454"&&
        level4ex011->bindings.front().variants==std::vector<std::string>{"fg:variant:003395","fg:variant:003397"}&&
        level4ex011->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise011 selected second-pass source row binds only D/U");
  const auto level4ex012=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-012-1314";});
  check(level4ex012!=index->exercises().end()&&level4ex012->bindings.size()==1&&
        level4ex012->bindings.front().exact&&level4ex012->bindings.front().itemId=="fg:item:000455"&&
        level4ex012->bindings.front().variants==std::vector<std::string>{"fg:variant:003407","fg:variant:003409"}&&
        level4ex012->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise012 selected second-pass source row binds only D/U");
  const auto level4ex013=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-2-of-9-exercises-013-024:exercise-013-1321";});
  check(level4ex013!=index->exercises().end()&&level4ex013->bindings.size()==1&&
        level4ex013->bindings.front().exact&&level4ex013->bindings.front().itemId=="fg:item:000456"&&
        level4ex013->bindings.front().variants==std::vector<std::string>{"fg:variant:003419","fg:variant:003421"}&&
        level4ex013->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise013 selected second-pass source row binds only D/U");
  const auto level4ex014=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-2-of-9-exercises-013-024:exercise-014-1323";});
  check(level4ex014!=index->exercises().end()&&level4ex014->bindings.size()==1&&
        level4ex014->bindings.front().exact&&level4ex014->bindings.front().itemId=="fg:item:000457"&&
        level4ex014->bindings.front().variants==std::vector<std::string>{"fg:variant:003431","fg:variant:003433"}&&
        level4ex014->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise014 selected second-pass source row binds only D/U");
  const auto level4ex015=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-2-of-9-exercises-013-024:exercise-015-1324";});
  check(level4ex015!=index->exercises().end()&&level4ex015->bindings.size()==1&&
        level4ex015->bindings.front().exact&&level4ex015->bindings.front().itemId=="fg:item:000458"&&
        level4ex015->bindings.front().variants==std::vector<std::string>{"fg:variant:003443","fg:variant:003445"}&&
        level4ex015->auditStatus.find("prepared_only")!=std::string::npos,
        "Level4 Exercise015 selected second-pass source row binds only D/U");
  for(const auto neighbor:{"printed:l004:set-1-of-9-exercises-001-012:exercise-001-1212",
                           "printed:l004:set-2-of-9-exercises-013-024:exercise-016-1341"}){
    const auto it=std::find_if(index->exercises().begin(),index->exercises().end(),[&](const auto& row){
        return row.source.sourceExerciseKey==neighbor;});
    check(it!=index->exercises().end()&&it->bindings.empty(),"Level4 neighboring exercise remains unavailable");
  }
  const auto supplemental=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="level080/modulea/p003-card01/cmaj7melodyefge";});
  check(supplemental!=index->exercises().end()&&supplemental->bindings.size()==1&&
        supplemental->bindings.front().supplemental&&!supplemental->bindings.front().exact&&
        supplemental->bindings.front().itemId=="fg:item:001179"&&
        supplemental->bindings.front().variants==std::vector<std::string>{"fg:variant:007696"}&&
        supplemental->auditStatus.find("missing")!=std::string::npos,
        "Level80 source row remains missing with one non-exact supplemental example");
  std::size_t exact=0;for(const auto& row:index->exercises())for(const auto& binding:row.bindings)if(binding.exact)++exact;check(exact==153,"Level4 Exercise015 adds one exact binding while preserving prior cases");
  auto bytes=content::readBounded(std::filesystem::path(argv[1])/"index.json",4*1024*1024);const auto rows=content::readBounded(std::filesystem::path(argv[1])/"exercises.jsonl",32*1024*1024),overlay=content::readBounded(std::filesystem::path(argv[1])/"accepted-overlay.json",1024*1024);
  check(overlay.find("accepted184 cases/970 retained variants/429 retained source entries/174 Practice-playable")!=std::string::npos&&
        overlay.find("manager-adopted official children121/7271")!=std::string::npos&&
        overlay.find("Level4 Exercise005, Exercise006, Exercise007, Exercise008 and Exercise009 second-pass D/U are manager-adopted installed accepted")!=std::string::npos&&
        overlay.find("Level4 Exercise010 second-pass D/U is manager-adopted installed accepted")!=std::string::npos&&
        overlay.find("Level4 Exercise011 second-pass D/U is manager-adopted installed accepted")!=std::string::npos&&
        overlay.find("Level4 Exercise012 second-pass D/U is manager-adopted installed accepted")!=std::string::npos&&
        overlay.find("Level4 Exercise013 second-pass D/U is manager-adopted installed accepted")!=std::string::npos&&
        overlay.find("Level4 Exercise014 second-pass D/U is manager-adopted installed accepted")!=std::string::npos&&
        overlay.find("Level4 Exercise015 second-pass D/U is manager-adopted installed accepted")!=std::string::npos&&
        overlay.find("Level4 Exercise015 second-pass D/U is an installed candidate pending different review")==std::string::npos&&
        overlay.find("Level4 Exercise015 remains nonadmitted and unavailable")==std::string::npos&&
        overlay.find("accepted177 cases/886 retained variants/401 retained source entries/167 Practice-playable")==std::string::npos&&
        overlay.find("accepted176 cases/874 retained variants/397 retained source entries/166 Practice-playable")==std::string::npos&&
        overlay.find("accepted175 cases/862 retained variants/393 retained source entries/165 Practice-playable")==std::string::npos&&
        overlay.find("technical parents40/58")!=std::string::npos&&
        overlay.find("accepted174 cases/850 retained variants/389 retained source entries/164 Practice-playable")==std::string::npos&&
        overlay.find("accepted173 cases/838 retained variants/385 retained source entries/163 Practice-playable")==std::string::npos&&
        overlay.find("children120/7271") == std::string::npos&&
        overlay.find("accepted170 cases/802 retained variants/373 retained source entries/160 Practice-playable")==std::string::npos,
        "Accepted cutoff describes adopted Catalog, official children and parent baseline");
  const auto level35LowE=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l035:module-a-six-silent-shift-horizontal-lanes:low-e-string-12-note-up-down-cell";});
  check(level35LowE!=index->exercises().end()&&level35LowE->locator.find("PDF pages [2]")!=std::string::npos&&
        level35LowE->auditStatus.find("prepared_only")!=std::string::npos&&level35LowE->bindings.empty(),
        "Level35 low-E reviewed PDF locator remains unavailable");
  auto level35WrongPage=rows;const auto level35Start=level35WrongPage.find("printed:l035:module-a-six-silent-shift-horizontal-lanes:low-e-string-12-note-up-down-cell");
  check(level35Start!=std::string::npos,"Level35 low-E source identity exists for wrong-page refusal");
  const auto level35End=level35WrongPage.find('\n',level35Start);const auto level35Tag=std::string{"\"physical_pages\":[2]"};
  const auto level35Page=level35WrongPage.find(level35Tag,level35Start);
  check(level35Page!=std::string::npos&&level35Page<level35End,"Level35 corrected page exists for reversion");
  level35WrongPage[level35Page+std::string{"\"physical_pages\":["}.size()]='3';
  auto level35StalePins=learn::installedSourceIndexPins;level35StalePins.exercises=content::sha256(level35WrongPage);
  refused=false;try{learn::SourceIndex::parse(bytes,level35WrongPage,overlay,level35StalePins);}catch(const std::exception&){refused=true;}
  check(refused,"Level35 wrong PDF page refuses against current overlay base");
  auto preLevel35BasePins=learn::installedSourceIndexPins;
  preLevel35BasePins.exercises="5b21fd17067220b8f3c1e78aac6ff9e54c203c51a960d18e0f627ff38b67c358";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preLevel35BasePins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level35 base index pin refuses");
  auto preEX012CutoffPins=learn::installedSourceIndexPins;
  preEX012CutoffPins.overlay="bfe58d546ee7e3cff7d348f95014e4a8a1792b38e2ae5386763eef22dc0983a7";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preEX012CutoffPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-EX012 accepted cutoff overlay pin refuses");
  const auto rung10Gb=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l013:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16";});
  check(rung10Gb!=index->exercises().end()&&rung10Gb->locator.find("PDF pages [5]")!=std::string::npos&&
        rung10Gb->auditStatus.find("missing")!=std::string::npos&&rung10Gb->bindings.empty(),
        "Level13 Rung10 reviewed PDF locator remains unavailable");
  auto rung10WrongPage=rows;const auto rung10Start=rung10WrongPage.find("printed:l013:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16");
  check(rung10Start!=std::string::npos,"Level13 Rung10 source identity exists for wrong-page refusal");
  const auto rung10End=rung10WrongPage.find('\n',rung10Start);const auto rung10Tag=std::string{"\"physical_pages\":[5]"};
  const auto rung10Page=rung10WrongPage.find(rung10Tag,rung10Start);
  check(rung10Page!=std::string::npos&&rung10Page<rung10End,"Level13 Rung10 corrected page exists for reversion");
  rung10WrongPage[rung10Page+std::string{"\"physical_pages\":["}.size()]='2';
  auto rung10StalePins=learn::installedSourceIndexPins;rung10StalePins.exercises=content::sha256(rung10WrongPage);
  refused=false;try{learn::SourceIndex::parse(bytes,rung10WrongPage,overlay,rung10StalePins);}catch(const std::exception&){refused=true;}
  check(refused,"Level13 Rung10 wrong PDF page refuses against current overlay base");
  auto preRung10BasePins=learn::installedSourceIndexPins;
  preRung10BasePins.exercises="3d70e63c7fccff81deacc559db2330ba0c77c54bc74a4c38612362f5c7dea2cc";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preRung10BasePins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level13 Rung10 base index pin refuses");
  auto preRung10OverlayPins=learn::installedSourceIndexPins;
  preRung10OverlayPins.overlay="64d5fc0040b3fa074b6a7b39bcea73278e45cbd77451d732b75ffb9bea6031d1";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preRung10OverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level13 Rung10 overlay pin refuses");
  const auto l37CommonTone=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l037:section-iv:level-37:module-b-voice-leading:p1-root-frame-frets-4-7:common-tone-a-e5-r-a-e5-5-b-e7-5-a-e5-r";});
  check(l37CommonTone!=index->exercises().end()&&l37CommonTone->locator.find("PDF pages [7]")!=std::string::npos&&
        l37CommonTone->auditStatus.find("prepared_only")!=std::string::npos&&l37CommonTone->bindings.empty(),
        "Level37 common-tone corrected PDF locator remains unavailable");
  auto l37WrongPage=rows;const auto l37Start=l37WrongPage.find("printed:l037:section-iv:level-37:module-b-voice-leading:p1-root-frame-frets-4-7:common-tone-a-e5-r-a-e5-5-b-e7-5-a-e5-r");
  check(l37Start!=std::string::npos,"Level37 common-tone source identity exists for wrong-page refusal");
  const auto l37End=l37WrongPage.find('\n',l37Start);const auto l37Tag=std::string{"\"physical_pages\":[7]"};
  const auto l37Page=l37WrongPage.find(l37Tag,l37Start);
  check(l37Page!=std::string::npos&&l37Page<l37End,"Level37 common-tone corrected page exists for reversion");
  l37WrongPage[l37Page+std::string{"\"physical_pages\":["}.size()]='8';
  auto l37WrongPins=learn::installedSourceIndexPins;l37WrongPins.exercises=content::sha256(l37WrongPage);
  refused=false;try{learn::SourceIndex::parse(bytes,l37WrongPage,overlay,l37WrongPins);}catch(const std::exception&){refused=true;}
  check(refused,"Level37 common-tone wrong PDF page refuses against current overlay base");
  auto l37OldBasePins=learn::installedSourceIndexPins;
  l37OldBasePins.exercises="1ab345c37029fa61961d2f3ecad9ae38a85392c85fd153272e90deb177dd276c";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,l37OldBasePins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level37 common-tone base index pin refuses");
  auto l37OldOverlayPins=learn::installedSourceIndexPins;
  l37OldOverlayPins.overlay="3cc3adb0731e54f545f380c6d90c7faedc6ccf631317012fc4fbf03c2d057a1b";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,l37OldOverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level37 common-tone overlay pin refuses");
  const auto l36Position1=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l036:module-a-five-position-legato-cells:position-1-root-frame-frets-4-7-roots-e5-d7-e5";});
  check(l36Position1!=index->exercises().end()&&l36Position1->locator.find("PDF pages [2]")!=std::string::npos&&
        l36Position1->auditStatus.find("prepared_only")!=std::string::npos&&l36Position1->bindings.empty(),
        "Level36 Position1 corrected PDF locator remains unavailable");
  auto l36WrongPage=rows;const auto l36Start=l36WrongPage.find("printed:l036:module-a-five-position-legato-cells:position-1-root-frame-frets-4-7-roots-e5-d7-e5");
  check(l36Start!=std::string::npos,"Level36 Position1 source identity exists for wrong-page refusal");
  const auto l36End=l36WrongPage.find('\n',l36Start);const auto l36Tag=std::string{"\"physical_pages\":[2]"};
  const auto l36Page=l36WrongPage.find(l36Tag,l36Start);
  check(l36Page!=std::string::npos&&l36Page<l36End,"Level36 Position1 corrected page exists for reversion");
  l36WrongPage[l36Page+std::string{"\"physical_pages\":["}.size()]='3';
  auto l36WrongPins=learn::installedSourceIndexPins;l36WrongPins.exercises=content::sha256(l36WrongPage);
  refused=false;try{learn::SourceIndex::parse(bytes,l36WrongPage,overlay,l36WrongPins);}catch(const std::exception&){refused=true;}
  check(refused,"Level36 Position1 wrong page refuses against current overlay base");
  auto l36OldBasePins=learn::installedSourceIndexPins;
  l36OldBasePins.exercises="d6a2a541a11629a2c45a8a0e5d21e026e180aaaae360c82ce2a390eca2f18ab2";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,l36OldBasePins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level36 Position1 base index pin refuses");
  auto l36OldOverlayPins=learn::installedSourceIndexPins;
  l36OldOverlayPins.overlay="a72399ea53f3ffabff43419e18a45c97bbcfe1448b5396240c1cc34ca401537e";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,l36OldOverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-EX013 accepted cutoff overlay pin refuses");
  const auto l38P1=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l038:section-iv:level-38:module-a-local-pairs:p1-root-frame-frets-4-7";});
  check(l38P1!=index->exercises().end()&&l38P1->locator.find("PDF pages [2]")!=std::string::npos&&
        l38P1->auditStatus.find("missing")!=std::string::npos&&l38P1->bindings.empty(),
        "Level38 P1 corrected PDF locator retains missing/unavailable status");
  auto l38WrongPage=rows;const auto l38Start=l38WrongPage.find("printed:l038:section-iv:level-38:module-a-local-pairs:p1-root-frame-frets-4-7");
  check(l38Start!=std::string::npos,"Level38 P1 source identity exists for wrong-page refusal");
  const auto l38End=l38WrongPage.find('\n',l38Start);
  const auto l38Tag=std::string{"\"physical_pages\":[2]"};
  const auto l38Page=l38WrongPage.find(l38Tag,l38Start);
  check(l38Page!=std::string::npos&&l38Page<l38End,"Level38 P1 corrected page exists for reversion");
  l38WrongPage[l38Page+std::string{"\"physical_pages\":["}.size()]='3';
  auto l38WrongPins=learn::installedSourceIndexPins;l38WrongPins.exercises=content::sha256(l38WrongPage);
  refused=false;try{learn::SourceIndex::parse(bytes,l38WrongPage,overlay,l38WrongPins);}catch(const std::exception&){refused=true;}
  check(refused,"Level38 P1 wrong page refuses against current overlay base");
  auto l38OldBasePins=learn::installedSourceIndexPins;
  l38OldBasePins.exercises="cd20579a39ca16cb83d095e122a0194644732b5a884528c4a347133a4d585ce6";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,l38OldBasePins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level38 P1 base index pin refuses");
  auto l38OldOverlayPins=learn::installedSourceIndexPins;
  l38OldOverlayPins.overlay="d53a30c5bb391fd346908af1361589e9ba461289affb3d1bb33b7718d15bf072";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,l38OldOverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-EX014 accepted cutoff overlay pin refuses");
  const auto l39P1=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l039:section-v:level-39:module-a-drone-comparison:p1-drone-comparison-phrase";});
  check(l39P1!=index->exercises().end()&&l39P1->locator.find("PDF pages [2]")!=std::string::npos&&
        l39P1->auditStatus.find("prepared_only")!=std::string::npos&&l39P1->bindings.empty(),
        "Level39 Module A P1 corrected PDF locator retains prepared/unavailable status");
  auto l39WrongPage=rows;const auto l39Start=l39WrongPage.find("printed:l039:section-v:level-39:module-a-drone-comparison:p1-drone-comparison-phrase");
  check(l39Start!=std::string::npos,"Level39 Module A P1 source identity exists for wrong-page refusal");
  const auto l39End=l39WrongPage.find('\n',l39Start);
  const auto l39Tag=std::string{"\"physical_pages\":[2]"};
  const auto l39Page=l39WrongPage.find(l39Tag,l39Start);
  check(l39Page!=std::string::npos&&l39Page<l39End,"Level39 Module A P1 corrected page exists for reversion");
  l39WrongPage[l39Page+std::string{"\"physical_pages\":["}.size()]='3';
  auto l39WrongPins=learn::installedSourceIndexPins;l39WrongPins.exercises=content::sha256(l39WrongPage);
  refused=false;try{learn::SourceIndex::parse(bytes,l39WrongPage,overlay,l39WrongPins);}catch(const std::exception&){refused=true;}
  check(refused,"Level39 Module A P1 wrong page refuses against current overlay base");
  auto l39OldBasePins=learn::installedSourceIndexPins;
  l39OldBasePins.exercises="a9b6baaac7873d903d1ca1ce01f83566f95f6d47d89d6a118cbf2a5a02b039e0";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,l39OldBasePins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level39 Module A P1 base index pin refuses");
  auto l39OldOverlayPins=learn::installedSourceIndexPins;
  l39OldOverlayPins.overlay="2fc8e1fc00a806be963ac8bcd565e6a23c7db06b40eae36641702091dc8cdafc";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,l39OldOverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-EX015 accepted cutoff overlay pin refuses");
  const auto ex016=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l004:set-2-of-9-exercises-013-024:exercise-016-1341";});
  check(ex016!=index->exercises().end()&&ex016->locator.find("PDF pages [2]")!=std::string::npos&&
        ex016->auditStatus.find("prepared_only")!=std::string::npos&&ex016->bindings.empty(),
        "Level4 EX016 corrected PDF locator retains prepared/unavailable status");
  auto ex016WrongPage=rows;const auto ex016Start=ex016WrongPage.find("printed:l004:set-2-of-9-exercises-013-024:exercise-016-1341");
  check(ex016Start!=std::string::npos,"Level4 EX016 source identity exists for wrong-page refusal");
  const auto ex016End=ex016WrongPage.find('\n',ex016Start);
  const auto ex016Tag=std::string{"\"physical_pages\":[2]"};
  const auto ex016Page=ex016WrongPage.find(ex016Tag,ex016Start);
  check(ex016Page!=std::string::npos&&ex016Page<ex016End,"Level4 EX016 corrected page exists for reversion");
  ex016WrongPage[ex016Page+std::string{"\"physical_pages\":["}.size()]='3';
  auto ex016WrongPins=learn::installedSourceIndexPins;ex016WrongPins.exercises=content::sha256(ex016WrongPage);
  refused=false;try{learn::SourceIndex::parse(bytes,ex016WrongPage,overlay,ex016WrongPins);}catch(const std::exception&){refused=true;}
  check(refused,"Level4 EX016 wrong page refuses against current overlay base");
  auto ex016OldBasePins=learn::installedSourceIndexPins;
  ex016OldBasePins.exercises="ce449c9ff646d47fe8f7f8d70fe60ddb7db600ae639d79d1ec9cc2fb52529949";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,ex016OldBasePins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level4 EX016 base index pin refuses");
  auto ex016OldOverlayPins=learn::installedSourceIndexPins;
  ex016OldOverlayPins.overlay="ea57bd39e3feba21bcfb61548140207d19faae84a2fd5ca3386adf3478921055";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,ex016OldOverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level4 EX016 overlay pin refuses");
  const auto l40P1=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
      return row.source.sourceExerciseKey=="printed:l040:section-v:level-40:module-a-chord-target-cells:p1-established-a-root-frame-frets-4-7:f-m-14-note-target-cell";});
  check(l40P1!=index->exercises().end()&&l40P1->locator.find("PDF pages [2]")!=std::string::npos&&
        l40P1->auditStatus.find("missing")!=std::string::npos&&l40P1->bindings.empty(),
        "Level40 Module A P1 corrected PDF locator retains missing/unavailable status");
  auto l40P1WrongPage=rows;const auto l40P1Start=l40P1WrongPage.find("printed:l040:section-v:level-40:module-a-chord-target-cells:p1-established-a-root-frame-frets-4-7:f-m-14-note-target-cell");
  check(l40P1Start!=std::string::npos,"Level40 Module A P1 source identity exists for wrong-page refusal");
  const auto l40P1End=l40P1WrongPage.find('\n',l40P1Start);
  const auto l40P1Tag=std::string{"\"physical_pages\":[2]"};
  const auto l40P1Page=l40P1WrongPage.find(l40P1Tag,l40P1Start);
  check(l40P1Page!=std::string::npos&&l40P1Page<l40P1End,"Level40 Module A P1 corrected page exists for reversion");
  l40P1WrongPage[l40P1Page+std::string{"\"physical_pages\":["}.size()]='3';
  auto l40P1WrongPins=learn::installedSourceIndexPins;l40P1WrongPins.exercises=content::sha256(l40P1WrongPage);
  refused=false;try{learn::SourceIndex::parse(bytes,l40P1WrongPage,overlay,l40P1WrongPins);}catch(const std::exception&){refused=true;}
  check(refused,"Level40 Module A P1 wrong page refuses against current overlay base");
  auto l40P1OldBasePins=learn::installedSourceIndexPins;
  l40P1OldBasePins.exercises="1fdf7e38706548d2e807065afca562c0937e95d5baaec5a4744f07373a00a11e";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,l40P1OldBasePins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level40 Module A P1 base index pin refuses");
  auto l40P1OldOverlayPins=learn::installedSourceIndexPins;
  l40P1OldOverlayPins.overlay="b8a55f1cd614206284877c01a5f543c97c8ebbe002ecf27ad044b4c358db2a1a";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,l40P1OldOverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level40 Module A P1 overlay pin refuses");
  refused=false;try{learn::SourceIndex::parse(bytes+" ",rows,overlay,learn::installedSourceIndexPins);}catch(const std::exception&){refused=true;}check(refused,"Source resource hash tamper refuses");
  for(const auto& fixture:std::vector<std::pair<std::string,std::string>>{
      {"printed:l031:complete-tablature:rung-10-of-13-gb-major-pentatonic-root-on-low-e-fret-14-frame-13-16","\"physical_pages\":[5]"},
      {"printed:l032:rung-10-of-13-gb-major-pentatonic-root-on-low-e-fret-14-frame-13-16:module-a-three-note-roll","\"physical_pages\":[11]"}}){
    auto reverted=rows;const auto start=reverted.find(fixture.first);
    check(start!=std::string::npos,"Level31/32 corrected source identity exists");
    const auto end=reverted.find('\n',start);const auto page=reverted.find(fixture.second,start);
    check(page!=std::string::npos&&page<end,"Level31/32 corrected page exists for reversion");
    reverted[page+fixture.second.size()-2]=fixture.first.find("l031")!=std::string::npos?'6':'2';
    auto stalePins=learn::installedSourceIndexPins;stalePins.exercises=content::sha256(reverted);
    refused=false;try{learn::SourceIndex::parse(bytes,reverted,overlay,stalePins);}catch(const std::exception&){refused=true;}
    check(refused,"Level31/32 stale page refuses against current overlay base");
  }
  for(const auto& fixture:std::vector<std::string>{
      "printed:l033:rung-10-of-13-gb-major-pentatonic-root-on-low-e-fret-14-frame-13-16:module-a-skip-one-pairs",
      "printed:l033:rung-10-of-13-gb-major-pentatonic-root-on-low-e-fret-14-frame-13-16:module-b-wide-leap-resolve"}){
    const auto it=std::find_if(index->exercises().begin(),index->exercises().end(),[&](const auto& row){return row.source.sourceExerciseKey==fixture;});
    check(it!=index->exercises().end()&&it->locator.find("PDF pages [11]")!=std::string::npos&&
          it->auditStatus.find("missing")!=std::string::npos&&it->bindings.empty(),
          "Level33 Rung10 reviewed PDF locator remains unavailable");
    auto reverted=rows;const auto start=reverted.find(fixture);
    check(start!=std::string::npos,"Level33 corrected source identity exists for reversion");
    const auto end=reverted.find('\n',start);const auto tag=std::string{"\"physical_pages\":[11]"};
    const auto page=reverted.find(tag,start);
    check(page!=std::string::npos&&page<end,"Level33 corrected page exists for reversion");
    reverted[page+std::string{"\"physical_pages\":[1"}.size()]='2';
    auto stalePins=learn::installedSourceIndexPins;stalePins.exercises=content::sha256(reverted);
    refused=false;try{learn::SourceIndex::parse(bytes,reverted,overlay,stalePins);}catch(const std::exception&){refused=true;}
    check(refused,"Level33 stale page refuses against current overlay base");
  }
  auto preLevel33SourcePins=learn::installedSourceIndexPins;
  preLevel33SourcePins.exercises="8de0006d21ac6823586d8761f9b4cb75c59da8bb645e1bd3d2de6ea86efe3535";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preLevel33SourcePins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level33 exercises pin refuses");
  auto preEx011CutoffPins=learn::installedSourceIndexPins;
  preEx011CutoffPins.overlay="775e4096ea5a0d6c4c0264f4a2bd584bb01796eab261112c7a0de51852d5964d";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preEx011CutoffPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-EX011 accepted cutoff overlay pin refuses");
  for(const auto& fixture:std::vector<std::tuple<std::string,char,char,std::string>>{
      {"printed:l013:complete-tablature:rung-09-of-13-f-major-root-on-low-e-fret-13-frame-12-15",'4','2',"missing"},
      {"printed:l034:five-vertical-position-cells:position-1-root-frame-frets-4-7",'2','3',"prepared_only"}}){
    const auto& key=std::get<0>(fixture);const auto pageDigit=std::get<1>(fixture);
    const auto it=std::find_if(index->exercises().begin(),index->exercises().end(),[&](const auto& row){return row.source.sourceExerciseKey==key;});
    check(it!=index->exercises().end()&&it->locator.find(std::string{"PDF pages ["}+pageDigit+"]")!=std::string::npos&&
          it->auditStatus.find(std::get<3>(fixture))!=std::string::npos&&it->bindings.empty(),
          "Level13/34 reviewed PDF locator remains unavailable");
    auto reverted=rows;const auto start=reverted.find(key);check(start!=std::string::npos,"Level13/34 identity exists for reversion");
    const auto end=reverted.find('\n',start);const auto tag=std::string{"\"physical_pages\":["}+pageDigit+"]";
    const auto page=reverted.find(tag,start);check(page!=std::string::npos&&page<end,"Level13/34 corrected page exists for reversion");
    reverted[page+std::string{"\"physical_pages\":["}.size()]=std::get<2>(fixture);
    auto stalePins=learn::installedSourceIndexPins;stalePins.exercises=content::sha256(reverted);
    refused=false;try{learn::SourceIndex::parse(bytes,reverted,overlay,stalePins);}catch(const std::exception&){refused=true;}
    check(refused,"Level13/34 stale page refuses with recomputed index pin");
  }
  auto preLevel13R09Level34P1Pins=learn::installedSourceIndexPins;
  preLevel13R09Level34P1Pins.exercises="42efa3705728e28215c2f2a43265691704bf326ae6187d61a2c654d9deec3092";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preLevel13R09Level34P1Pins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level13/34 index pin refuses");
  auto preLevel13R09Level34P1OverlayPins=learn::installedSourceIndexPins;
  preLevel13R09Level34P1OverlayPins.overlay="a61e5d85fc3ee12465c1c2797d309e01f7d80ea1f9369a041e0379dcf87c5728";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preLevel13R09Level34P1OverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level13/34 overlay pin refuses");
  auto oldSourcePins=learn::installedSourceIndexPins;
  oldSourcePins.exercises="9bf90ac85b0e0f0d7fade1dc3f497d8a32d8b0167efc6f31d69ba89ab4b48d55";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,oldSourcePins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level31/32 source hash refuses");
  auto oldOverlayPins=learn::installedSourceIndexPins;
  oldOverlayPins.overlay="53fb2a4ee26b6bd2f320042ddb21a2832a103a3f40e38d51e2e86f39c2ece795";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,oldOverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-EX010 accepted cutoff overlay hash refuses");
  auto preFourLocatorIndexPins=learn::installedSourceIndexPins;
  preFourLocatorIndexPins.exercises="00e893b0f3c94f8b15405ff76a8e61bf56cddc74f95ddf195be699dd23b021ab";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preFourLocatorIndexPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-four-locator exercises pin refuses");
  auto preFourLocatorOverlayPins=learn::installedSourceIndexPins;
  preFourLocatorOverlayPins.overlay="65250167620af3144afe4653e41a2f6efcf1ebfe72d7fbcd91bc54194c4d0a92";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preFourLocatorOverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Stale pre-accepted174 overlay pin refuses");
  for(const auto& fixture:std::vector<std::pair<std::string,char>>{
      {"printed:l015:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16",'6'},
      {"printed:l015:complete-tablature:rung-11-of-13-g-major-root-on-low-e-fret-15-frame-14-17",'7'},
      {"printed:l015:complete-tablature:rung-12-of-13-ab-major-root-on-low-e-fret-16-frame-15-18",'7'},
      {"printed:l016:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16",'5'}}){
    auto reverted=rows;const auto start=reverted.find(fixture.first);
    check(start!=std::string::npos,"Four-locator source identity exists for reversion");
    const auto end=reverted.find('\n',start);
    const auto tag=std::string{"\"physical_pages\":["}+fixture.second+"]";
    const auto page=reverted.find(tag,start);
    check(page!=std::string::npos&&page<end,"Four-locator corrected page exists for reversion");
    reverted[page+std::string{"\"physical_pages\":["}.size()]='2';
    auto revertedPins=learn::installedSourceIndexPins;revertedPins.exercises=content::sha256(reverted);
    refused=false;try{learn::SourceIndex::parse(bytes,reverted,overlay,revertedPins);}catch(const std::exception&){refused=true;}
    check(refused,"Single old PDF pointer refuses even with recomputed exercises pin");
  }
  for(const auto& source:std::vector<std::string>{
      "printed:l016:complete-tablature:rung-11-of-13-g-major-root-on-low-e-fret-15-frame-14-17",
      "printed:l016:complete-tablature:rung-12-of-13-ab-major-root-on-low-e-fret-16-frame-15-18"}){
    auto reverted=rows;const auto start=reverted.find(source);
    check(start!=std::string::npos,"Level16 reviewed source identity exists for reversion");
    const auto end=reverted.find('\n',start);
    const auto page=reverted.find("\"physical_pages\":[5]",start);
    check(page!=std::string::npos&&page<end,"Level16 reviewed page exists for reversion");
    reverted[page+std::string{"\"physical_pages\":["}.size()]='2';
    auto revertedPins=learn::installedSourceIndexPins;revertedPins.exercises=content::sha256(reverted);
    refused=false;try{learn::SourceIndex::parse(bytes,reverted,overlay,revertedPins);}catch(const std::exception&){refused=true;}
    check(refused,"Level16 stale page refuses even with recomputed exercises pin");
  }
  auto preLevel17Rung10Pins=learn::installedSourceIndexPins;
  preLevel17Rung10Pins.exercises="be8035e9baad7fde8a10e5e59063d8af77d30778f4f3c250a3f18a97662f4cbe";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preLevel17Rung10Pins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level17 Rung10 exercises pin refuses");
  auto preLevel17Rung10OverlayPins=learn::installedSourceIndexPins;
  preLevel17Rung10OverlayPins.overlay="1368d3627bd34db65a9ecb30bfb649bdb3db08d3c17948624b2c246093f0a5cf";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preLevel17Rung10OverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level17 Rung10 overlay pin refuses");
  auto revertedLevel17Rung10Rows=rows;
  const auto l17r10key=std::string{"printed:l017:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16"};
  const auto l17r10start=revertedLevel17Rung10Rows.find(l17r10key);
  check(l17r10start!=std::string::npos,"Level17 Rung10 source key exists for refusal");
  const auto l17r10end=revertedLevel17Rung10Rows.find('\n',l17r10start);
  const auto l17r10tag=revertedLevel17Rung10Rows.find("\"physical_pages\":[6]",l17r10start);
  check(l17r10tag!=std::string::npos&&l17r10tag<l17r10end,"Level17 corrected page exists for refusal");
  revertedLevel17Rung10Rows[l17r10tag+std::string{"\"physical_pages\":["}.size()]='2';
  auto l17r10pins=learn::installedSourceIndexPins;l17r10pins.exercises=content::sha256(revertedLevel17Rung10Rows);
  refused=false;try{learn::SourceIndex::parse(bytes,revertedLevel17Rung10Rows,overlay,l17r10pins);}catch(const std::exception&){refused=true;}
  check(refused,"Level17 Rung10 old PDF page refuses with recomputed exercises pin");
  auto preLevel18Rung10Pins=learn::installedSourceIndexPins;
  preLevel18Rung10Pins.exercises="2f56ffbb1ced176057109d656fa4d05ee30dfdfad34a8708133ee404d9da6241";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preLevel18Rung10Pins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level18 Rung10 exercises pin refuses");
  auto preLevel18Rung10OverlayPins=learn::installedSourceIndexPins;
  preLevel18Rung10OverlayPins.overlay="cc0a5921e88c6fc99c7342bf011a4af5d27f1f7221dd4a942bd499d284669b4b";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preLevel18Rung10OverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level18 Rung10 overlay pin refuses");
  auto revertedLevel18Rung10Rows=rows;
  const auto l18r10key=std::string{"printed:l018:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16"};
  const auto l18r10start=revertedLevel18Rung10Rows.find(l18r10key);
  check(l18r10start!=std::string::npos,"Level18 Rung10 source key exists for refusal");
  const auto l18r10end=revertedLevel18Rung10Rows.find('\n',l18r10start);
  const auto l18r10tag=revertedLevel18Rung10Rows.find("\"physical_pages\":[6]",l18r10start);
  check(l18r10tag!=std::string::npos&&l18r10tag<l18r10end,"Level18 corrected page exists for refusal");
  revertedLevel18Rung10Rows[l18r10tag+std::string{"\"physical_pages\":["}.size()]='2';
  auto l18r10pins=learn::installedSourceIndexPins;l18r10pins.exercises=content::sha256(revertedLevel18Rung10Rows);
  refused=false;try{learn::SourceIndex::parse(bytes,revertedLevel18Rung10Rows,overlay,l18r10pins);}catch(const std::exception&){refused=true;}
  check(refused,"Level18 Rung10 old PDF page refuses with recomputed exercises pin");
  auto oldL19Pin=learn::installedSourceIndexPins;
  oldL19Pin.exercises="5f2b90411c4bcf539455270c488033b472eec182f36c5bfac532e16118cea6bf";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,oldL19Pin);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level19 Rung10 exercises pin refuses");
  auto oldL19OverlayPin=learn::installedSourceIndexPins;
  oldL19OverlayPin.overlay="49da4ff3192cd3dc98623912d3af14fdc96843a1186c769849905b567e9a5746";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,oldL19OverlayPin);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level19/EX007 overlay pin refuses");
  auto revertedL19Rows=rows;
  const auto l19key=std::string{"printed:l019:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16"};
  const auto l19start=revertedL19Rows.find(l19key);
  check(l19start!=std::string::npos,"Level19 Rung10 source key exists for refusal");
  const auto l19end=revertedL19Rows.find('\n',l19start);
  const auto l19tag=revertedL19Rows.find("\"physical_pages\":[6]",l19start);
  check(l19tag!=std::string::npos&&l19tag<l19end,"Level19 corrected page exists for refusal");
  revertedL19Rows[l19tag+std::string{"\"physical_pages\":["}.size()]='2';
  auto l19pin=learn::installedSourceIndexPins;l19pin.exercises=content::sha256(revertedL19Rows);
  refused=false;try{learn::SourceIndex::parse(bytes,revertedL19Rows,overlay,l19pin);}catch(const std::exception&){refused=true;}
  check(refused,"Level19 Rung10 old PDF page refuses with recomputed exercises pin");
  auto oldL20Pin=learn::installedSourceIndexPins;
  oldL20Pin.exercises="657e10f91b70e898965191a2cc0c4c51a9291c361808860b411e7b6f8ea12f2d";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,oldL20Pin);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level20 two-pointer exercises pin refuses");
  auto oldL20OverlayPin=learn::installedSourceIndexPins;
  oldL20OverlayPin.overlay="163bfc4a9f9f47423cca0e479590bdefec1dc11d5507377e7ae6eaa54c407005";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,oldL20OverlayPin);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level20/EX008 overlay pin refuses");
  for(const auto& key:std::vector<std::string>{
      "printed:l020:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16:module-1-linear-scale-30-notes",
      "printed:l020:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16:module-2-three-note-roll-78-notes"}){
    auto reverted=rows;
    const auto start=reverted.find(key);check(start!=std::string::npos,"Level20 source key exists for refusal");
    const auto end=reverted.find('\n',start);
    const auto tag=reverted.find("\"physical_pages\":[20]",start);
    check(tag!=std::string::npos&&tag<end,"Level20 corrected page exists for refusal");
    reverted.erase(tag+std::string{"\"physical_pages\":[2"}.size(),1);
    auto pin=learn::installedSourceIndexPins;pin.exercises=content::sha256(reverted);
    refused=false;try{learn::SourceIndex::parse(bytes,reverted,overlay,pin);}catch(const std::exception&){refused=true;}
    check(refused,"Level20 old PDF page refuses with recomputed exercises pin");
  }
  auto preL20m3Pin=learn::installedSourceIndexPins;
  preL20m3Pin.exercises="5463011f7805104da50204cc64d528cc14f16b28d0e4f3de9c09334f34e5e69b";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preL20m3Pin);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Level20 Module3 exercises pin refuses");
  auto preL20m3Overlay=learn::installedSourceIndexPins;
  preL20m3Overlay.overlay="32034c06c05005eca19d792e69cfd4e24b1215cc0a04efa27f8f98444a4ce053";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preL20m3Overlay);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-EX009 accepted cutoff overlay pin refuses");
  auto revertedL20m3=rows;
  const auto l20m3start=revertedL20m3.find("printed:l020:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16:module-3-four-note-roll-96-notes");
  check(l20m3start!=std::string::npos,"Level20 Module3 source key exists for refusal");
  const auto l20m3end=revertedL20m3.find('\n',l20m3start);
  const auto l20m3tag=revertedL20m3.find("\"physical_pages\":[20]",l20m3start);
  check(l20m3tag!=std::string::npos&&l20m3tag<l20m3end,"Level20 Module3 corrected page exists for refusal");
  revertedL20m3.erase(l20m3tag+std::string{"\"physical_pages\":[2"}.size(),1);
  auto l20m3pin=learn::installedSourceIndexPins;l20m3pin.exercises=content::sha256(revertedL20m3);
  refused=false;try{learn::SourceIndex::parse(bytes,revertedL20m3,overlay,l20m3pin);}catch(const std::exception&){refused=true;}
  check(refused,"Level20 Module3 old PDF page refuses with recomputed exercises pin");
  auto preRung08Rung09IndexPins=learn::installedSourceIndexPins;
  preRung08Rung09IndexPins.exercises="eaf79125997d119cb462b7d4c0eb37c03711ca8862141b16629e830dfcac2bc4";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preRung08Rung09IndexPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Rung08/Rung09 exercises pin refuses");
  auto preExercise005OverlayPins=learn::installedSourceIndexPins;
  preExercise005OverlayPins.overlay="a4061d760943c401673f3acd7af8eb17e9701b628e973b9df8d08511bca7f036";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preExercise005OverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Exercise005 overlay pin refuses");
  auto preExercise004OverlayPins=learn::installedSourceIndexPins;
  preExercise004OverlayPins.overlay="8075fededaf54ecd168fe4c34214e076e9e06ffd95cfcff89d66f547b1bd89c5";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preExercise004OverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Exercise004 overlay pin refuses after exact one-row binding");
  auto preRung08Rung09OverlayPins=learn::installedSourceIndexPins;
  preRung08Rung09OverlayPins.overlay="05d729502ee33f8cfdd4321a719e702324e7cbb0927cb8365604abf9e4fe4b60";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preRung08Rung09OverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Rung08/Rung09 overlay pin refuses");
  for(const auto& fixture:std::vector<std::pair<std::string,char>>{
      {"printed:l015:complete-tablature:rung-08-of-13-e-major-root-on-low-e-fret-12-frame-11-14",'5'},
      {"printed:l015:complete-tablature:rung-09-of-13-f-major-root-on-low-e-fret-13-frame-12-15",'6'}}){
    auto reverted=rows;const auto start=reverted.find(fixture.first);
    check(start!=std::string::npos,"Level15 corrected row exists for old-page refusal");
    const auto end=reverted.find('\n',start);
    const auto tag=std::string{"\"physical_pages\":["}+fixture.second+"]";
    const auto page=reverted.find(tag,start);
    check(page!=std::string::npos&&page<end,"Level15 corrected page exists for old-page refusal");
    reverted[page+std::string{"\"physical_pages\":["}.size()]='2';
    auto revertedPins=learn::installedSourceIndexPins;revertedPins.exercises=content::sha256(reverted);
    refused=false;try{learn::SourceIndex::parse(bytes,reverted,overlay,revertedPins);}catch(const std::exception&){refused=true;}
    check(refused,"Original Level15 card locator refuses even with recomputed exercises pin");
  }
  auto revertedLevel12Rung08Rows=rows;
  const auto l12r08source=std::string{"printed:l012:complete-tablature:rung-08-of-13-e-major-root-on-low-e-fret-12-frame-11-14"};
  const auto l12r08start=revertedLevel12Rung08Rows.find(l12r08source);
  check(l12r08start!=std::string::npos,"Level12 Rung08 source exists for old-page refusal");
  const auto l12r08end=revertedLevel12Rung08Rows.find('\n',l12r08start);
  const auto l12r08page=revertedLevel12Rung08Rows.find("\"physical_pages\":[3]",l12r08start);
  check(l12r08page!=std::string::npos&&l12r08page<l12r08end,"Corrected Level12 Rung08 page exists");
  revertedLevel12Rung08Rows[l12r08page+std::string{"\"physical_pages\":["}.size()]='2';
  auto l12r08pins=learn::installedSourceIndexPins;l12r08pins.exercises=content::sha256(revertedLevel12Rung08Rows);
  refused=false;try{learn::SourceIndex::parse(bytes,revertedLevel12Rung08Rows,overlay,l12r08pins);}catch(const std::exception&){refused=true;}
  check(refused,"Old Level12 Rung08 page refuses with recomputed exercises pin and current overlay");
  auto preRung08IndexPins=learn::installedSourceIndexPins;
  preRung08IndexPins.exercises="da48e887d7157855e8fe314ca076e6862e4916549a7720b45c0637faa0f7feaf";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preRung08IndexPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Rung08 index pin refuses");
  auto revertedRung08Rows=rows;
  const auto r08identity=std::string{"printed:l013:complete-tablature:rung-08-of-13-e-major-root-on-low-e-fret-12-frame-11-14"};
  const auto r08start=revertedRung08Rows.find(r08identity);check(r08start!=std::string::npos,"Rung08 source identity exists for reversion");
  const auto r08end=revertedRung08Rows.find('\n',r08start),r08page=revertedRung08Rows.find("\"physical_pages\":[4]",r08start);
  check(r08page!=std::string::npos&&r08page<r08end,"Corrected Rung08 locator exists for reversion");
  revertedRung08Rows[r08page+std::string{"\"physical_pages\":["}.size()]='2';
  auto r08pins=learn::installedSourceIndexPins;r08pins.exercises=content::sha256(revertedRung08Rows);
  refused=false;try{learn::SourceIndex::parse(bytes,revertedRung08Rows,overlay,r08pins);}catch(const std::exception&){refused=true;}
  check(refused,"Reverted Rung08 locator refuses with recomputed exercises pin and current overlay");
  auto preRung08OverlayPins=learn::installedSourceIndexPins;
  preRung08OverlayPins.overlay="108846d8685edbfa8b5a138d334471b21abe338d32bff0baed009cff2137c529";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preRung08OverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Rung08 factual overlay pin refuses");
  auto immediateOldIndexPins=learn::installedSourceIndexPins;
  immediateOldIndexPins.exercises="b3ae40be2942023840b52d4b776092e34b33a0d9bdb116f98c2669cebbd513e8";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,immediateOldIndexPins);}catch(const std::exception&){refused=true;}
  check(refused,"Immediate pre-Rung06 index pin refuses");
  auto twoPointerOldIndexPins=learn::installedSourceIndexPins;
  twoPointerOldIndexPins.exercises="f709a5d075890643d8ae160a81449c9ff0fc7580ec3a3398534c78556b65d560";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,twoPointerOldIndexPins);}catch(const std::exception&){refused=true;}
  check(refused,"Immediate pre-two-pointer index pin refuses");
  for(const auto& fixture:std::vector<std::pair<std::string,char>>{
      {"printed:l013:complete-tablature:rung-07-of-13-eb-major-root-on-low-e-fret-11-frame-10-13",'4'},
      {"printed:l014:complete-tablature:rung-04-of-13-c-major-root-on-low-e-fret-8-frame-7-10",'3'}}){
    auto reverted=rows;const auto start=reverted.find(fixture.first);
    check(start!=std::string::npos,"Two-pointer row identity exists for reversion");
    const auto end=reverted.find('\n',start);
    const auto tag=std::string{"\"physical_pages\":["}+fixture.second+"]";
    const auto page=reverted.find(tag,start);
    check(page!=std::string::npos&&page<end,"Two-pointer corrected locator exists for reversion");
    reverted[page+std::string{"\"physical_pages\":["}.size()]='2';
    auto revertedPins=learn::installedSourceIndexPins;revertedPins.exercises=content::sha256(reverted);
    refused=false;try{learn::SourceIndex::parse(bytes,reverted,overlay,revertedPins);}catch(const std::exception&){refused=true;}
    check(refused,"Single corrected pointer reversion refuses with recomputed exercises pin");
  }
  auto revertedRung06Rows=rows;
  const auto r15identity=std::string{"printed:l015:complete-tablature:rung-06-of-13-d-major-root-on-low-e-fret-10-frame-9-12"};
  const auto r15start=revertedRung06Rows.find(r15identity);check(r15start!=std::string::npos,"Rung06 source identity exists for locator refusal");
  const auto r15end=revertedRung06Rows.find('\n',r15start),r15page=revertedRung06Rows.find("\"physical_pages\":[4]",r15start);
  check(r15page!=std::string::npos&&r15page<r15end,"Corrected Rung06 locator exists for refusal");
  revertedRung06Rows[r15page+std::string{"\"physical_pages\":["}.size()]='2';
  auto r15pins=learn::installedSourceIndexPins;r15pins.exercises=content::sha256(revertedRung06Rows);
  refused=false;try{learn::SourceIndex::parse(bytes,revertedRung06Rows,overlay,r15pins);}catch(const std::exception&){refused=true;}
  check(refused,"Reverted Rung06 locator refuses even with recomputed exercises pin");
  auto revertedRung07Rows=rows;
  const auto r07identity=std::string{"printed:l015:complete-tablature:rung-07-of-13-eb-major-root-on-low-e-fret-11-frame-10-13"};
  const auto r07start=revertedRung07Rows.find(r07identity);
  const auto r07end=revertedRung07Rows.find('\n',r07start),r07page=revertedRung07Rows.find("\"physical_pages\":[5]",r07start);
  if(r07start==std::string::npos||r07page==std::string::npos||r07page>=r07end)throw std::runtime_error("missing corrected Rung07 locator fixture");
  revertedRung07Rows[r07page+std::string{"\"physical_pages\":["}.size()]='2';
  auto r07pins=learn::installedSourceIndexPins;r07pins.exercises=content::sha256(revertedRung07Rows);
  refused=false;try{learn::SourceIndex::parse(bytes,revertedRung07Rows,overlay,r07pins);}catch(const std::exception&){refused=true;}
  if(!refused)throw std::runtime_error("reverted Rung07 locator accepted with recomputed exercises pin");
  auto preRung06OverlayPins=learn::installedSourceIndexPins;
  preRung06OverlayPins.overlay="1ffd3a230ab4a28ae893bb08b125186e880f46de0ff5a703ecfb715db1b84d1a";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preRung06OverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Rung06 overlay pin refuses");
  auto preRung04OverlayPins=learn::installedSourceIndexPins;
  preRung04OverlayPins.overlay="b54047252fecb7a947672354be17456fc855da4adafd6862715217b71b00444f";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,preRung04OverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Rung04 overlay pin refuses");
  auto immediateOldOverlayPins=learn::installedSourceIndexPins;
  immediateOldOverlayPins.overlay="2fa942134668e4c2ca519093af758c0175b93f63bd1b1881e4e3e32befe08f24";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,immediateOldOverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Immediate pre-adoption overlay pin refuses");
  auto twoPointerOldOverlayPins=learn::installedSourceIndexPins;
  twoPointerOldOverlayPins.overlay="3d9561f34a2d6a294894ea3d8a40985c4f33a40744ae54c6b437a82baa83acba";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,twoPointerOldOverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Immediate pre-two-pointer overlay pin refuses");
  auto staleOverlayPins=learn::installedSourceIndexPins;
  staleOverlayPins.overlay="168fd0029e9f8c2f752f74b528da762041db66cfdb06741090d0947ae93c49f9";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,staleOverlayPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre-Rung05 accepted overlay pin refuses");
  auto pins=learn::installedSourceIndexPins;
  pins.exercises="cb85b24dcfafe0ec96ded09623240f6b925c6f5d67564925d4ca69591130e078";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,pins);}catch(const std::exception&){refused=true;}check(refused,"Stale pre-correction exercises pin refuses");
  pins=learn::installedSourceIndexPins;pins.exercises="98e189dcd5ffb6dc551d82dd97bd9ee84342b1494cef8246a49eac5b3372e021";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,pins);}catch(const std::exception&){refused=true;}check(refused,"Stale pre-Rung06 exercises pin refuses");
  for(const auto& identity:{std::string{"printed:l013:complete-tablature:rung-04-of-13-c-major-root-on-low-e-fret-8-frame-7-10"},std::string{"printed:l013:complete-tablature:rung-05-of-13-db-major-root-on-low-e-fret-9-frame-8-11"},std::string{"printed:l013:complete-tablature:rung-06-of-13-d-major-root-on-low-e-fret-10-frame-9-12"}}){
    auto badLocatorRows=rows;const auto start=badLocatorRows.find(identity);check(start!=std::string::npos,"Level13 locator identity exists for tamper fixture");
    const auto rowEnd=badLocatorRows.find('\n',start),pageTag=badLocatorRows.find("\"physical_pages\":[3]",start);
    check(pageTag!=std::string::npos&&pageTag<rowEnd,"Level13 corrected page locator exists for tamper fixture");
    badLocatorRows[pageTag+std::string{"\"physical_pages\":["}.size()]='2';
    pins=learn::installedSourceIndexPins;pins.exercises=content::sha256(badLocatorRows);
    refused=false;try{learn::SourceIndex::parse(bytes,badLocatorRows,overlay,pins);}catch(const std::exception&){refused=true;}
    check(refused,"Single Level13 row locator tamper refuses with recomputed exercises pin");
  }
  auto staleBaseOverlay=json::parse(overlay);staleBaseOverlay.object()["base_exercises_sha256"]="98e189dcd5ffb6dc551d82dd97bd9ee84342b1494cef8246a49eac5b3372e021";
  const auto staleBase=json::stringify(staleBaseOverlay);pins=learn::installedSourceIndexPins;pins.overlay=content::sha256(staleBase);
  refused=false;try{learn::SourceIndex::parse(bytes,rows,staleBase,pins);}catch(const std::exception&){refused=true;}check(refused,"Stale overlay base exercises digest refuses with recomputed overlay pin");
  auto badRows=rows+rows.substr(0,rows.find('\n')+1);pins=learn::installedSourceIndexPins;pins.exercises=content::sha256(badRows);refused=false;try{learn::SourceIndex::parse(bytes,badRows,overlay,pins);}catch(const std::exception&){refused=true;}check(refused,"Duplicate source row refuses with recomputed test pin");
  auto badOverlay=json::parse(overlay);badOverlay.object().at("entries").array().front().object().at("source_identity")="fixture:absent";const auto changed=json::stringify(badOverlay);pins=learn::installedSourceIndexPins;pins.overlay=content::sha256(changed);refused=false;try{learn::SourceIndex::parse(bytes,rows,changed,pins);}catch(const std::exception&){refused=true;}check(refused,"Overlay to nonexistent source unit refuses");
  badOverlay=json::parse(overlay);auto& supplementalOverlay=badOverlay.object().at("entries").array();
  const auto supplementalIt=std::find_if(supplementalOverlay.begin(),supplementalOverlay.end(),[](const auto& entry){return entry.object().at("source_identity").string()=="level080/modulea/p003-card01/cmaj7melodyefge";});
  if(supplementalIt==supplementalOverlay.end())throw std::runtime_error("missing Level80 supplemental overlay");
  supplementalIt->object().at("binding").object()["source_extent_kind"]="exact_single_printed_unit_candidate";
  const auto falseExact=json::stringify(badOverlay);pins=learn::installedSourceIndexPins;pins.overlay=content::sha256(falseExact);refused=false;try{learn::SourceIndex::parse(bytes,rows,falseExact,pins);}catch(const std::exception&){refused=true;}check(refused,"Level80 supplemental example cannot be laundered into exact source Queue");
  //33 independently reviewed exact-key metadata postimages; no generic locator alias.
  for(const auto& fixture:std::vector<std::pair<std::string,std::string>>{
      {"printed:l012:complete-tablature:rung-06-of-13-d-major-root-on-low-e-fret-10-frame-9-12","PDF pages [3]"},
      {"printed:l012:complete-tablature:rung-07-of-13-eb-major-root-on-low-e-fret-11-frame-10-13","PDF pages [3]"},
      {"printed:l012:complete-tablature:rung-09-of-13-f-major-root-on-low-e-fret-13-frame-12-15","PDF pages [4]"},
      {"printed:l012:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16","PDF pages [4]"},
      {"printed:l012:complete-tablature:rung-11-of-13-g-major-root-on-low-e-fret-15-frame-14-17","PDF pages [4]"},
      {"printed:l012:complete-tablature:rung-12-of-13-ab-major-root-on-low-e-fret-16-frame-15-18","PDF pages [4]"},
      {"printed:l012:complete-tablature:rung-13-of-13-a-major-octave-root-on-low-e-fret-17-frame-16-19","PDF pages [5]"},
      {"printed:l012:consolidation:full-round-trip-challenge","PDF pages [5]"},
      {"printed:l012:pdf-consolidation:mastery-gate-before-the-next-scale-level","PDF pages [1]"},
      {"printed:l013:complete-tablature:rung-11-of-13-g-major-root-on-low-e-fret-15-frame-14-17","PDF pages [5]"},
      {"printed:l013:complete-tablature:rung-12-of-13-ab-major-root-on-low-e-fret-16-frame-15-18","PDF pages [5]"},
      {"printed:l013:complete-tablature:rung-13-of-13-a-major-octave-root-on-low-e-fret-17-frame-16-19","PDF pages [6]"},
      {"printed:l013:consolidation:full-round-trip-challenge","PDF pages [6]"},
      {"printed:l013:pdf-consolidation:mastery-gate-before-the-next-scale-level","PDF pages [1]"},
      {"printed:l014:complete-tablature:rung-05-of-13-db-major-root-on-low-e-fret-9-frame-8-11","PDF pages [3]"},
      {"printed:l014:complete-tablature:rung-06-of-13-d-major-root-on-low-e-fret-10-frame-9-12","PDF pages [3]"},
      {"printed:l014:complete-tablature:rung-07-of-13-eb-major-root-on-low-e-fret-11-frame-10-13","PDF pages [4]"},
      {"printed:l014:complete-tablature:rung-08-of-13-e-major-root-on-low-e-fret-12-frame-11-14","PDF pages [4]"},
      {"printed:l014:complete-tablature:rung-09-of-13-f-major-root-on-low-e-fret-13-frame-12-15","PDF pages [4]"},
      {"printed:l014:complete-tablature:rung-10-of-13-gb-major-root-on-low-e-fret-14-frame-13-16","PDF pages [5]"},
      {"printed:l014:complete-tablature:rung-11-of-13-g-major-root-on-low-e-fret-15-frame-14-17","PDF pages [5]"},
      {"printed:l014:complete-tablature:rung-12-of-13-ab-major-root-on-low-e-fret-16-frame-15-18","PDF pages [5]"},
      {"printed:l014:complete-tablature:rung-13-of-13-a-major-octave-root-on-low-e-fret-17-frame-16-19","PDF pages [6]"},
      {"printed:l014:consolidation:full-round-trip-challenge","PDF pages [6]"},
      {"printed:l014:pdf-consolidation:mastery-gate","PDF pages [1]"},
      {"printed:l015:complete-tablature:rung-13-of-13-a-major-octave-root-on-low-e-fret-17-frame-16-19","PDF pages [8]"},
      {"printed:l015:consolidation:full-round-trip-challenge","PDF pages [8]"},
      {"printed:l015:consolidation:mastery-gate-before-level-16","PDF pages [1,9]"},
      {"printed:l037:section-iv:level-37:module-c-target-phrases:p1-root-frame-frets-4-7-32-eighth-notes","PDF pages [8]"},
      {"printed:l037:section-iv:level-37:module-c-target-phrases:p2-second-degree-frame-frets-6-10-32-eighth-notes","PDF pages [8]"},
      {"printed:l037:section-iv:level-37:module-c-target-phrases:p3-third-degree-frame-frets-9-12-32-eighth-notes","PDF pages [9]"},
      {"printed:l037:section-iv:level-37:module-c-target-phrases:p4-fifth-degree-frame-frets-11-14-32-eighth-notes","PDF pages [9]"},
      {"printed:l037:section-iv:level-37:module-c-target-phrases:p5-sixth-degree-frame-frets-14-17-32-eighth-notes","PDF pages [10]"}}){
    const auto found=std::find_if(index->exercises().begin(),index->exercises().end(),[&](const auto& e){return e.source.sourceExerciseKey==fixture.first;});
    check(found!=index->exercises().end(),"Reviewed metadata source identity exists");
    check(found->locator.find(fixture.second)!=std::string::npos,"Reviewed exact PDF page array is visible through native loader");
  }
  auto locator33OldPins=learn::installedSourceIndexPins;locator33OldPins.exercises="39996dd0b7087df4d1c8e8a1aa5a32ba11479389229b70d3cbb71d5bf79722d7";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,locator33OldPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre33 metadata exercises pin refuses");
  //277 exact postimages compose two distinct accepted source reviews.
  for(const auto& fixture:std::vector<std::pair<std::string,std::string>>{
      {"level076/modulea/p003-t1-r1/1","PDF pages [2]"},
      {"level076/modulea/p003-t1-r10/10","PDF pages [2]"},
      {"level076/modulea/p003-t1-r11/11","PDF pages [2]"},
      {"level076/modulea/p003-t1-r12/12","PDF pages [2]"},
      {"level076/modulea/p003-t1-r2/2","PDF pages [2]"},
      {"level076/modulea/p003-t1-r3/3","PDF pages [2]"},
      {"level076/modulea/p003-t1-r4/4","PDF pages [2]"},
      {"level076/modulea/p003-t1-r5/5","PDF pages [2]"},
      {"level076/modulea/p003-t1-r6/6","PDF pages [2]"},
      {"level076/modulea/p003-t1-r7/7","PDF pages [2]"},
      {"level076/modulea/p003-t1-r8/8","PDF pages [2]"},
      {"level076/modulea/p003-t1-r9/9","PDF pages [2]"},
      {"level076/moduleb/p004-t1-r1/cmajor","PDF pages [3]"},
      {"level076/moduleb/p004-t1-r10/cmajor","PDF pages [3]"},
      {"level076/moduleb/p004-t1-r11/gmajor","PDF pages [3]"},
      {"level076/moduleb/p004-t1-r12/emajor","PDF pages [3]"},
      {"level076/moduleb/p004-t1-r2/cmajor","PDF pages [3]"},
      {"level076/moduleb/p004-t1-r3/gmajor","PDF pages [3]"},
      {"level076/moduleb/p004-t1-r4/dmajor","PDF pages [3]"},
      {"level076/moduleb/p004-t1-r5/amajor","PDF pages [3]"},
      {"level076/moduleb/p004-t1-r6/aminor","PDF pages [3]"},
      {"level076/moduleb/p004-t1-r7/eminor","PDF pages [3]"},
      {"level076/moduleb/p004-t1-r8/dminor","PDF pages [3]"},
      {"level076/moduleb/p004-t1-r9/fmajor","PDF pages [3]"},
      {"level076/modulec/p005-t1-r1/1","PDF pages [4]"},
      {"level076/modulec/p005-t1-r10/10","PDF pages [4]"},
      {"level076/modulec/p005-t1-r11/11","PDF pages [4]"},
      {"level076/modulec/p005-t1-r12/12","PDF pages [4]"},
      {"level076/modulec/p005-t1-r13/13","PDF pages [4]"},
      {"level076/modulec/p005-t1-r14/14","PDF pages [4]"},
      {"level076/modulec/p005-t1-r15/15","PDF pages [4]"},
      {"level076/modulec/p005-t1-r16/16","PDF pages [4]"},
      {"level076/modulec/p005-t1-r2/2","PDF pages [4]"},
      {"level076/modulec/p005-t1-r3/3","PDF pages [4]"},
      {"level076/modulec/p005-t1-r4/4","PDF pages [4]"},
      {"level076/modulec/p005-t1-r5/5","PDF pages [4]"},
      {"level076/modulec/p005-t1-r9/9","PDF pages [4]"},
      {"level076/modulec/p006-card01/card2tonalframegmajor","PDF pages [5]"},
      {"level076/modulec/p006-card02/card6tonalframefmajor","PDF pages [5]"},
      {"level076/modulec/p006-card03/card3tonalframedmajor","PDF pages [5]"},
      {"level076/modulec/p006-card04/card7tonalframecmajorg","PDF pages [5]"},
      {"level076/modulec/p006-card05/card4tonalframeaminor","PDF pages [5]"},
      {"level076/modulec/p006-card06/card8tonalframeaminorc","PDF pages [5]"},
      {"level076/modulec/p006-supplement01/card1tonalframecmajor","PDF pages [5]"},
      {"level076/modulec/p006-supplement02/card5tonalframeeminor","PDF pages [5]"},
      {"level076/moduled/p007-t1-r1/quarter","PDF pages [6]"},
      {"level076/moduled/p007-t1-r10/tiebar","PDF pages [6]"},
      {"level076/moduled/p007-t1-r11/stoptime","PDF pages [6]"},
      {"level076/moduled/p007-t1-r12/shuffle","PDF pages [6]"},
      {"level076/moduled/p007-t1-r13/quintuplet","PDF pages [6]"},
      {"level076/moduled/p007-t1-r14/septuplet","PDF pages [6]"},
      {"level076/moduled/p007-t1-r15/5432","PDF pages [6]"},
      {"level076/moduled/p007-t1-r16/78223","PDF pages [6]"},
      {"level076/moduled/p007-t1-r2/eighths","PDF pages [6]"},
      {"level076/moduled/p007-t1-r3/backbeat","PDF pages [6]"},
      {"level076/moduled/p007-t1-r4/332","PDF pages [6]"},
      {"level076/moduled/p007-t1-r5/push4","PDF pages [6]"},
      {"level076/moduled/p007-t1-r6/latea4","PDF pages [6]"},
      {"level076/moduled/p007-t1-r7/16thstab","PDF pages [6]"},
      {"level076/moduled/p007-t1-r8/funk1","PDF pages [6]"},
      {"level076/moduled/p007-t1-r9/tie2","PDF pages [6]"},
      {"level076/moduled/p008-card01/dictation1","PDF pages [7]"},
      {"level076/moduled/p008-card02/dictation2","PDF pages [7]"},
      {"level076/moduled/p008-card03/dictation3","PDF pages [7]"},
      {"level076/moduled/p008-card04/dictation4","PDF pages [7]"},
      {"level076/moduled/p008-card05/dictation5","PDF pages [7]"},
      {"level076/moduled/p008-card06/dictation6","PDF pages [7]"},
      {"level076/moduled/p008-card07/dictation7","PDF pages [7]"},
      {"level076/moduled/p008-card08/dictation8","PDF pages [7]"},
      {"level076/moduled/p008-card09/dictation9","PDF pages [7]"},
      {"level076/moduled/p008-card11/dictation11","PDF pages [7]"},
      {"level076/moduled/p008-card12/dictation12","PDF pages [7]"},
      {"level076/moduled/p008-card13/dictation13","PDF pages [7]"},
      {"level076/moduled/p008-card14/dictation14","PDF pages [7]"},
      {"level076/moduled/p008-card15/dictation15","PDF pages [7]"},
      {"level076/modulee/p009-t1-r1/cmajor","PDF pages [8]"},
      {"level076/modulee/p009-t1-r10/amelodicminor","PDF pages [8]"},
      {"level076/modulee/p009-t1-r11/cmajor","PDF pages [8]"},
      {"level076/modulee/p009-t1-r12/g7","PDF pages [8]"},
      {"level076/modulee/p009-t1-r2/cmajor","PDF pages [8]"},
      {"level076/modulee/p009-t1-r3/gmajor","PDF pages [8]"},
      {"level076/modulee/p009-t1-r4/dmajor","PDF pages [8]"},
      {"level076/modulee/p009-t1-r5/aminor","PDF pages [8]"},
      {"level076/modulee/p009-t1-r6/aminor","PDF pages [8]"},
      {"level076/modulee/p009-t1-r7/eminor","PDF pages [8]"},
      {"level076/modulee/p009-t1-r8/dminor","PDF pages [8]"},
      {"level076/modulee/p009-t1-r9/aharmonicminor","PDF pages [8]"},
      {"level076/modulee/p010-t1-r1/cmaj7","PDF pages [9]"},
      {"level076/modulee/p010-t1-r10/d7#11","PDF pages [9]"},
      {"level076/modulee/p010-t1-r11/e7b13","PDF pages [9]"},
      {"level076/modulee/p010-t1-r12/g#7alt","PDF pages [9]"},
      {"level076/modulee/p010-t1-r2/g7","PDF pages [9]"},
      {"level076/modulee/p010-t1-r3/am7","PDF pages [9]"},
      {"level076/modulee/p010-t1-r4/dm7","PDF pages [9]"},
      {"level076/modulee/p010-t1-r5/e7","PDF pages [9]"},
      {"level076/modulee/p010-t1-r6/a7","PDF pages [9]"},
      {"level076/modulee/p010-t1-r7/cmaj7","PDF pages [9]"},
      {"level076/modulee/p010-t1-r8/gmaj7","PDF pages [9]"},
      {"level076/modulee/p010-t1-r9/bm7b5","PDF pages [9]"},
      {"level076/modulef/p011-t1-r1/a","PDF pages [10]"},
      {"level076/modulef/p011-t1-r2/b","PDF pages [10]"},
      {"level076/modulef/p011-t1-r3/c","PDF pages [10]"},
      {"level076/modulef/p011-t1-r4/d","PDF pages [10]"},
      {"level076/modulef/p011-t1-r5/e","PDF pages [10]"},
      {"level076/modulef/p011-t1-r6/f","PDF pages [10]"},
      {"level076/modulef/p011-t1-r7/g","PDF pages [10]"},
      {"level076/modulef/p011-t1-r8/h","PDF pages [10]"},
      {"level076/moduleg/p013-u001/moduleglayeredsixteenbartranscriptionlab","PDF pages [12,13,14]"},
      {"level076/moduleh/p012-t1-r1/1","PDF pages [11]"},
      {"level076/moduleh/p012-t1-r2/2","PDF pages [11]"},
      {"level076/moduleh/p012-t1-r3/3","PDF pages [11]"},
      {"level076/moduleh/p012-t1-r4/4","PDF pages [11]"},
      {"level076/moduleh/p012-t1-r5/5","PDF pages [11]"},
      {"level076/moduleh/p012-t1-r6/6","PDF pages [11]"},
      {"level076/moduleh/p012-t1-r7/7","PDF pages [11]"},
      {"level076/moduleh/p012-t1-r8/8","PDF pages [11]"},
      {"level076/modulei/p016-card01/singback","PDF pages [15]"},
      {"level076/modulei/p016-card02/rootonlyplayback","PDF pages [15]"},
      {"level076/modulei/p016-card03/guidetoneplayback","PDF pages [15]"},
      {"level076/modulei/p016-card04/mutedrhythmpass","PDF pages [15]"},
      {"level076/modulei/p016-card05/slowplayback","PDF pages [15]"},
      {"level076/modulei/p016-card06/octavecheck","PDF pages [15]"},
      {"level076/modulei/p016-card07/neighbortest","PDF pages [15]"},
      {"level076/modulei/p016-card08/sectioncomparison","PDF pages [15]"},
      {"level076/modulei/p016-card09/basschordsplit","PDF pages [15]"},
      {"level076/modulei/p016-card10/completereconstruction","PDF pages [15]"},
      {"level076/workbookfoundations/p002-u001/thetranscriptionworkflowanduncertaintynotation","PDF pages [1]"},
      {"level077/modulea/p002-t1-r1/m2","PDF pages [1]"},
      {"level077/modulea/p002-t1-r10/m7","PDF pages [1]"},
      {"level077/modulea/p002-t1-r11/m7","PDF pages [1]"},
      {"level077/modulea/p002-t1-r12/p8","PDF pages [1]"},
      {"level077/modulea/p002-t1-r2/m2","PDF pages [1]"},
      {"level077/modulea/p002-t1-r3/m3","PDF pages [1]"},
      {"level077/modulea/p002-t1-r4/m3","PDF pages [1]"},
      {"level077/modulea/p002-t1-r5/p4","PDF pages [1]"},
      {"level077/modulea/p002-t1-r6/tt","PDF pages [1]"},
      {"level077/modulea/p002-t1-r7/p5","PDF pages [1]"},
      {"level077/modulea/p002-t1-r8/m6","PDF pages [1]"},
      {"level077/modulea/p002-t1-r9/m6","PDF pages [1]"},
      {"level077/modulea/p003-t1-r1/1","PDF pages [2]"},
      {"level077/modulea/p003-t1-r10/10","PDF pages [2]"},
      {"level077/modulea/p003-t1-r11/11","PDF pages [2]"},
      {"level077/modulea/p003-t1-r12/12","PDF pages [2]"},
      {"level077/modulea/p003-t1-r13/13","PDF pages [2]"},
      {"level077/modulea/p003-t1-r14/14","PDF pages [2]"},
      {"level077/modulea/p003-t1-r15/15","PDF pages [2]"},
      {"level077/modulea/p003-t1-r16/16","PDF pages [2]"},
      {"level077/modulea/p003-t1-r17/17","PDF pages [2]"},
      {"level077/modulea/p003-t1-r18/18","PDF pages [2]"},
      {"level077/modulea/p003-t1-r19/19","PDF pages [2]"},
      {"level077/modulea/p003-t1-r2/2","PDF pages [2]"},
      {"level077/modulea/p003-t1-r21/21","PDF pages [2]"},
      {"level077/modulea/p003-t1-r25/24","PDF pages [2]"},
      {"level077/modulea/p003-t1-r3/3","PDF pages [2]"},
      {"level077/modulea/p003-t1-r4/4","PDF pages [2]"},
      {"level077/modulea/p003-t1-r5/5","PDF pages [2]"},
      {"level077/modulea/p003-t1-r6/6","PDF pages [2]"},
      {"level077/modulea/p003-t1-r7/7","PDF pages [2]"},
      {"level077/modulea/p003-t1-r8/8","PDF pages [2]"},
      {"level077/modulea/p003-t1-r9/9","PDF pages [2]"},
      {"level077/modulea/p004-t1-r1/1","PDF pages [3]"},
      {"level077/modulea/p004-t1-r10/10","PDF pages [3]"},
      {"level077/modulea/p004-t1-r11/11","PDF pages [3]"},
      {"level077/modulea/p004-t1-r12/12","PDF pages [3]"},
      {"level077/modulea/p004-t1-r2/2","PDF pages [3]"},
      {"level077/modulea/p004-t1-r3/3","PDF pages [3]"},
      {"level077/modulea/p004-t1-r4/4","PDF pages [3]"},
      {"level077/modulea/p004-t1-r5/5","PDF pages [3]"},
      {"level077/modulea/p004-t1-r6/6","PDF pages [3]"},
      {"level077/modulea/p004-t1-r7/7","PDF pages [3]"},
      {"level077/modulea/p004-t1-r8/8","PDF pages [3]"},
      {"level077/modulea/p004-t1-r9/9","PDF pages [3]"},
      {"level077/moduleb/p005-supplement01/blindtest","PDF pages [4]"},
      {"level077/moduleb/p005-t1-r1/i","PDF pages [4]"},
      {"level077/moduleb/p005-t1-r2/ii","PDF pages [4]"},
      {"level077/moduleb/p005-t1-r3/iii","PDF pages [4]"},
      {"level077/moduleb/p005-t1-r4/iv","PDF pages [4]"},
      {"level077/moduleb/p005-t1-r5/v","PDF pages [4]"},
      {"level077/moduleb/p005-t1-r6/vi","PDF pages [4]"},
      {"level077/moduleb/p005-t1-r8/viidim","PDF pages [4]"},
      {"level077/moduleb/p006-t1-r1/c","PDF pages [5]"},
      {"level077/moduleb/p006-t1-r2/g","PDF pages [5]"},
      {"level077/moduleb/p006-t1-r3/d","PDF pages [5]"},
      {"level077/moduleb/p006-t1-r8/g","PDF pages [5]"},
      {"level077/modulec/p007-supplement01/majoriivivoiceleading","PDF pages [6]"},
      {"level077/modulec/p007-t1-r1/cmaj7","PDF pages [6]"},
      {"level077/modulec/p007-t1-r2/dm7","PDF pages [6]"},
      {"level077/modulec/p007-t1-r3/g7","PDF pages [6]"},
      {"level077/modulec/p007-t1-r6/fmaj7","PDF pages [6]"},
      {"level077/modulec/p008-supplement01/minoriivivoiceleading","PDF pages [7]"},
      {"level077/modulec/p008-t1-r1/ammaj7","PDF pages [7]"},
      {"level077/modulec/p008-t1-r2/bm7b5","PDF pages [7]"},
      {"level077/modulec/p008-t1-r3/e7","PDF pages [7]"},
      {"level077/modulec/p008-t1-r6/dm7","PDF pages [7]"},
      {"level077/moduled/p009-t1-r1/cmajor","PDF pages [8]"},
      {"level077/moduled/p009-t1-r2/cmajor","PDF pages [8]"},
      {"level077/moduled/p009-t1-r3/gmajor","PDF pages [8]"},
      {"level077/moduled/p009-t1-r4/dmajor","PDF pages [8]"},
      {"level077/moduled/p009-t1-r5/aminor","PDF pages [8]"},
      {"level077/moduled/p009-t1-r6/eminor","PDF pages [8]"},
      {"level077/moduled/p009-t1-r7/aharmonicminor","PDF pages [8]"},
      {"level077/moduled/p009-t1-r8/amelodicminor","PDF pages [8]"},
      {"level077/moduled/p010-t1-r1/1","PDF pages [9]"},
      {"level077/moduled/p010-t1-r2/2","PDF pages [9]"},
      {"level077/moduled/p010-t1-r3/3","PDF pages [9]"},
      {"level077/modulee/p011-t1-r1/cmaj7","PDF pages [10]"},
      {"level077/modulee/p011-t1-r2/dm7","PDF pages [10]"},
      {"level077/modulee/p011-t1-r3/g7","PDF pages [10]"},
      {"level077/modulee/p011-t1-r4/am7","PDF pages [10]"},
      {"level077/modulee/p011-t1-r5/fmaj7","PDF pages [10]"},
      {"level077/modulee/p011-t1-r6/bm7b5","PDF pages [10]"},
      {"level077/modulee/p011-t1-r7/e7","PDF pages [10]"},
      {"level077/modulee/p011-t1-r8/ammaj7","PDF pages [10]"},
      {"level077/modulee/p012-t1-r1/1","PDF pages [11]"},
      {"level077/modulee/p012-t1-r2/2","PDF pages [11]"},
      {"level077/modulee/p012-t1-r3/3","PDF pages [11]"},
      {"level077/modulee/p012-t1-r4/4","PDF pages [11]"},
      {"level077/modulee/p012-t1-r5/5","PDF pages [11]"},
      {"level077/modulee/p012-t1-r7/7","PDF pages [11]"},
      {"level077/modulee/p012-t1-r8/8","PDF pages [11]"},
      {"level077/modulef/p013-t1-r1/cmajor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r10/eminor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r11/dminor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r12/aharmonicminor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r13/amelodicminor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r15/amelodicminor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r2/cmajor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r3/gmajor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r4/dmajor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r5/amajor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r6/emajor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r7/fmajor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r8/aminor","PDF pages [12]"},
      {"level077/modulef/p013-t1-r9/aminor","PDF pages [12]"},
      {"level076/modulec/p005-t1-r6/6","PDF pages [4]"},
      {"level076/modulec/p005-t1-r7/7","PDF pages [4]"},
      {"level076/modulec/p005-t1-r8/8","PDF pages [4]"},
      {"level077/modulea/p003-t1-r20/20","PDF pages [2]"},
      {"level077/moduleb/p006-t1-r10/a","PDF pages [5]"},
      {"level077/moduleb/p006-t1-r11/e","PDF pages [5]"},
      {"level077/moduleb/p006-t1-r12/f","PDF pages [5]"},
      {"level077/moduleb/p006-t1-r4/a","PDF pages [5]"},
      {"level077/moduleb/p006-t1-r5/e","PDF pages [5]"},
      {"level077/moduleb/p006-t1-r6/f","PDF pages [5]"},
      {"level077/moduleb/p006-t1-r7/c","PDF pages [5]"},
      {"level077/moduleb/p006-t1-r9/d","PDF pages [5]"},
      {"level077/modulec/p007-t1-r5/fmaj7","PDF pages [6]"},
      {"level077/modulec/p008-t1-r5/dm7","PDF pages [7]"},
      {"level077/moduled/p010-t1-r4/4","PDF pages [9]"},
      {"level077/moduled/p010-t1-r5/5","PDF pages [9]"},
      {"level077/moduled/p010-t1-r6/6","PDF pages [9]"},
      {"level077/moduled/p010-t1-r7/7","PDF pages [9]"},
      {"level077/moduled/p010-t1-r8/8","PDF pages [9]"},
      {"level077/modulee/p012-t1-r6/6","PDF pages [11]"},
      {"level077/moduleg/p016-card16/16singvirootsina","PDF pages [15]"},
      {"level077/moduleg/p016-card17/17sing37ofcmaj7","PDF pages [15]"},
      {"level077/moduleg/p016-card18/18singb73ofg7","PDF pages [15]"},
      {"level077/moduleh/p019-u001/level77capstoneunfamiliar16bareartohandreconstruction","PDF pages [18]"},
      {"level076/modulej/p017-u001/modulejthirtytwobarearledcapstone","PDF pages [16,17,18]"},
      {"level076/modulej/p020-u001/level76masterygatetranscriptionlogandsectionxdirection","PDF pages [19]"},
      {"level077/moduleg/p015-u001/modulegtimedreactionladder","PDF pages [14]"},
      {"level077/moduleg/p016-card01/1cm3","PDF pages [15]"},
      {"level077/moduleg/p016-card02/2f#m3","PDF pages [15]"},
      {"level077/moduleg/p016-card03/3bbp5","PDF pages [15]"},
      {"level077/moduleg/p016-card04/4em6","PDF pages [15]"},
      {"level077/moduleg/p016-card05/5cmajordegree7","PDF pages [15]"},
      {"level077/moduleg/p016-card06/6gmajordegree3","PDF pages [15]"},
      {"level077/moduleg/p016-card07/7aminordegreeb6","PDF pages [15]"},
      {"level077/moduleg/p016-card08/8aharmonicminordegree7","PDF pages [15]"},
      {"level077/moduleg/p016-card09/9cmaj7third","PDF pages [15]"},
      {"level077/moduleg/p016-card10/10g7b7","PDF pages [15]"},
      {"level077/moduleg/p016-card11/11dm7b3","PDF pages [15]"},
      {"level077/moduleg/p016-card12/12bm7b5b5","PDF pages [15]"},
      {"level077/moduleg/p016-card13/13functionofvind","PDF pages [15]"},
      {"level077/moduleg/p016-card14/14functionofiiing","PDF pages [15]"},
      {"level077/moduleg/p016-card15/15functionofviinc","PDF pages [15]"},
      {"level077/moduleh/p020-u001/practiceprogressionmasterygateandsectionxdirection","PDF pages [19]"}}){
    const auto found=std::find_if(index->exercises().begin(),index->exercises().end(),[&](const auto& e){return e.source.sourceExerciseKey==fixture.first;});
    check(found!=index->exercises().end(),"Reviewed metadata source identity exists");
    check(found->locator.find(fixture.second)!=std::string::npos,"Reviewed exact PDF page array visible through native loader");
  }
  auto metadata277OldPins=learn::installedSourceIndexPins;metadata277OldPins.exercises="2d05ea79ae4213e89c7f797fb7d1ede226f3eb2671a6ffd70e7fcf852db58abf";
  refused=false;try{learn::SourceIndex::parse(bytes,rows,overlay,metadata277OldPins);}catch(const std::exception&){refused=true;}
  check(refused,"Pre277 metadata exercises pin refuses");
  std::cout<<"PASS "<<checks<<" loader/source contract checks on frozen7321 index plus 108 Level1 exact bindings, Level15 Rung02/Rung03 and non-exact Level80 supplemental overlay\n";
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}
