#include "tasks/InstalledManualTaskRegistry.hpp"
#include "tasks/ManualTaskAdapter.hpp"
#include "content/Canonical.hpp"
#include "content/LearnSourceIndex.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
using namespace fathom;
namespace {
std::size_t assertions=0;
void check(bool value,const char* message){++assertions;if(!value)throw std::runtime_error(message);}
void change(const std::filesystem::path& path){auto bytes=content::readBounded(path,2*1024*1024);bytes[0]^=1;std::ofstream f(path,std::ios::binary|std::ios::trunc);f<<bytes;}
}
int main(int argc,char** argv){try{
 check(argc==3,"usage: registry-check <resources> <fresh-mutation-directory>");
 const std::filesystem::path resources{argv[1]},mutant{argv[2]};
 auto registry=tasks::InstalledManualTaskRegistry::load(resources/"typed-manual-tasks-v1");
 check(registry.error().empty(),"version-bound family and legacy must load");
 check(registry.contains("level053/moduleb/p003-t1-r1-c2/cmajrp"),"legacy route preserved");
 check(!registry.contains("exercise-completeness-r01/level053/moduleb/p003-t1-r1-c3/cmaj1st"),"prefixed identity must refuse");
 check(!registry.contains("level053/moduleb/foreign"),"unknown identity must refuse");
 std::set<std::string> identities;
 for(const auto& key:tasks::compiledFamilyKeys()){
  auto identity=key.substr(std::string{"exercise-completeness-r01/"}.size());
  check(identities.insert(identity).second,"duplicate source identity");
  check(registry.contains(identity),"every exact compiled identity must route");
  auto definition=registry.definition(identity);check(bool(definition),"trusted definition required");
  check(definition->sourceKey()==key&&bool(definition->reportContract()),"source/report binding required");
  auto reports=*definition->reportContract();tasks::ManualTaskAdapter a(*definition);
  check(a.apply(a.capture(tasks::IntentKind::SourceOrder),std::nullopt,{20,300}),"source choice");
  check(a.apply(a.capture(tasks::IntentKind::Ready),std::nullopt,{20,300},reports.setup),"explicit setup");
  for(const auto& report:reports.actions)check(a.apply(a.capture(tasks::IntentKind::Acknowledge),std::nullopt,{20,300},report),"exact action");
  check(a.view().phase==tasks::Phase::Release,"physical release boundary required");
  check(a.apply(a.capture(tasks::IntentKind::Release),std::nullopt,{20,300},reports.release),"explicit release");
  check(a.view().phase==tasks::Phase::Closed&&a.view().outcome==tasks::Outcome::UserReportedStepsFinished,"user report close");
  check(a.history().size()==7,"all explicit reports retained");
  for(const auto& event:a.history())check(!event.observedPerformance&&!event.grantsCredit,"no observed-performance or credit claim");
 }
 check(identities.size()==167,"exact family denominator");
 auto index=learn::SourceIndex::load(resources/"learn-source-index");
 std::map<std::string,std::size_t> sourceCounts;
 for(const auto& exercise:index->exercises())if(identities.count(exercise.source.sourceExerciseKey))++sourceCounts[exercise.source.sourceExerciseKey];
 check(sourceCounts.size()==identities.size(),"every compiled identity must exist in installed Learn index");
 for(const auto& identity:identities)check(sourceCounts.at(identity)==1,"exact unique installed Learn identity");
 check(!std::filesystem::exists(mutant),"mutation directory must be fresh");
 for(const auto& path:{"typed-manual-tasks-v1/manifest.json","typed-manual-tasks-v1/level053-moduleb-cmajrp/task-definition.json","compiled-manual-families-v1/manifest.json","compiled-manual-families-v1/definitions.jsonl","compiled-manual-families-v1/family-closure.json"}){
  std::filesystem::create_directories((mutant/path).parent_path());std::filesystem::copy_file(resources/path,mutant/path);
 }
 const auto stem="Guitar_Exercises_Section_VI_Level_53_Major_and_Minor_Triads_Across_Four_Adjacent_Three_String_Sets";
 for(const auto& extension:{"txt","pdf"}){
  auto path=std::filesystem::path{"source-library/bundle/assets/Notes/music/guitar project"}/(std::string{extension}=="txt"?"TXT version":"PDF version")/(std::string{stem}+"."+extension);
  std::filesystem::create_directories((mutant/path).parent_path());std::filesystem::copy_file(resources/path,mutant/path);
 }
 for(const auto& name:{"manifest.json","definitions.jsonl","family-closure.json"}){
  auto path=mutant/"compiled-manual-families-v1"/name;change(path);
  auto bad=tasks::InstalledManualTaskRegistry::load(mutant/"typed-manual-tasks-v1");
  check(!bad.error().empty(),"changed family bytes refuse");
  check(!bad.contains(*identities.begin()),"corrupt family grants no identity");
  check(bad.contains("level053/moduleb/p003-t1-r1-c2/cmajrp"),"family corruption preserves separate legacy");
  std::filesystem::copy_file(resources/"compiled-manual-families-v1"/name,path,std::filesystem::copy_options::overwrite_existing);
 }
 for(const auto& extension:{"txt","pdf"}){
  auto path=std::filesystem::path{"source-library/bundle/assets/Notes/music/guitar project"}/(std::string{extension}=="txt"?"TXT version":"PDF version")/(std::string{stem}+"."+extension);
  change(mutant/path);auto bad=tasks::InstalledManualTaskRegistry::load(mutant/"typed-manual-tasks-v1");
  check(!bad.contains(*identities.begin())&&!bad.contains("level053/moduleb/p003-t1-r1-c2/cmajrp"),"source tamper blocks all dependent routes");
  std::filesystem::copy_file(resources/path,mutant/path,std::filesystem::copy_options::overwrite_existing);
 }
 check(tasks::InstalledManualTaskRegistry::load(mutant/"typed-manual-tasks-v1").error().empty(),"restored bytes recover exact routes");
 std::cout<<"{\"result\":\"PASS\",\"rows\":167,\"assertions\":"<<assertions<<",\"installed_resource_registry\":true,\"practice_admitted\":false,\"official_accepted\":false}\n";
 return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
