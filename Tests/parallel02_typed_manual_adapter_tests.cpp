#include "tasks/InstalledManualTaskRegistry.hpp"
#include "tasks/ManualTaskAdapter.hpp"
#include "content/Canonical.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace fathom;
namespace {
void check(bool okay,const char* message){if(!okay)throw std::runtime_error(message);}
scheduler::Owner owner(std::uint8_t id,std::uint64_t generation){scheduler::Owner o;o.id[0]=id;o.id[6]=0x40;o.id[8]=0x80;o.epoch=1;o.generation=generation;return o;}
platform::MetronomeProgress progress(scheduler::Owner o,std::uint64_t binding,std::uint64_t sequence,std::uint64_t frames){
 platform::MetronomeProgress p;p.owner=o;p.binding=binding;p.sequence=sequence;p.totalActiveFrames=frames;p.clientAcceptedThrough=frames+1;p.phase=metronome::Phase::Running;p.tempo.tempo=60;return p;
}
}
int main(int argc,char** argv){
 try{
  check(argc==2,"usage: test <typed-task-resource-directory>");
  const auto directory=std::filesystem::path{argv[1]};
  const auto registry=tasks::InstalledManualTaskRegistry::load(directory);
  check(registry.error().empty(),"reviewed manifest/definition must load");
  const auto mutantRoot=std::filesystem::temp_directory_path()/"fathom-typed-manual-mutant-r01";
  const auto mutant=mutantRoot/"typed-manual-tasks-v1";
  std::filesystem::remove_all(mutantRoot);
  std::filesystem::create_directories(mutant/"level053-moduleb-cmajrp");
  const auto sourceStem="Guitar_Exercises_Section_VI_Level_53_Major_and_Minor_Triads_Across_Four_Adjacent_Three_String_Sets";
  const auto sourceDir=std::filesystem::path{"source-library/bundle/assets/Notes/music/guitar project"};
  const auto txt=sourceDir/"TXT version"/(std::string{sourceStem}+".txt");
  const auto pdf=sourceDir/"PDF version"/(std::string{sourceStem}+".pdf");
  for(const auto& path:{txt,pdf}){
   std::filesystem::create_directories((mutantRoot/path).parent_path());
   std::filesystem::copy_file(directory.parent_path()/path,mutantRoot/path);
  }
  std::filesystem::copy_file(directory/"manifest.json",mutant/"manifest.json");
  std::filesystem::copy_file(directory/"level053-moduleb-cmajrp/task-definition.json",mutant/"level053-moduleb-cmajrp/task-definition.json");
  {
   auto bytes=content::readBounded(mutantRoot/txt,65536);bytes[0]=bytes[0]=='G'?'H':'G';
   std::ofstream changed(mutantRoot/txt,std::ios::binary|std::ios::trunc);changed<<bytes;
  }
  check(!tasks::InstalledManualTaskRegistry::load(mutant).error().empty(),"altered packaged TXT must refuse");
  std::filesystem::copy_file(directory.parent_path()/txt,mutantRoot/txt,std::filesystem::copy_options::overwrite_existing);
  {
   auto bytes=content::readBounded(mutantRoot/pdf,131072);bytes[0]=bytes[0]=='%'?'!':'%';
   std::ofstream changed(mutantRoot/pdf,std::ios::binary|std::ios::trunc);changed<<bytes;
  }
  check(!tasks::InstalledManualTaskRegistry::load(mutant).error().empty(),"altered packaged PDF must refuse");
  std::filesystem::copy_file(directory.parent_path()/pdf,mutantRoot/pdf,std::filesystem::copy_options::overwrite_existing);
  {
   auto bytes=content::readBounded(mutant/"level053-moduleb-cmajrp/task-definition.json",65536);
   bytes[0]=bytes[0]=='{'?'[':'{';
   std::ofstream changed(mutant/"level053-moduleb-cmajrp/task-definition.json",std::ios::binary|std::ios::trunc);changed<<bytes;
  }
  check(!tasks::InstalledManualTaskRegistry::load(mutant).error().empty(),"altered definition must refuse");
  std::filesystem::copy_file(directory/"level053-moduleb-cmajrp/task-definition.json",mutant/"level053-moduleb-cmajrp/task-definition.json",std::filesystem::copy_options::overwrite_existing);
  {
   auto bytes=content::readBounded(mutant/"manifest.json",65536);
   bytes[0]=bytes[0]=='{'?'[':'{';
   std::ofstream changed(mutant/"manifest.json",std::ios::binary|std::ios::trunc);changed<<bytes;
  }
  check(!tasks::InstalledManualTaskRegistry::load(mutant).error().empty(),"altered manifest must refuse");
  std::filesystem::remove_all(mutantRoot);
  const std::string row="level053/moduleb/p003-t1-r1-c2/cmajrp";
  check(registry.contains(row)&&registry.contains("level053/moduleb/p003-t1-r1-c3/cmaj1st")&&!registry.contains("level053/moduleb/foreign"),"legacy and exact compiled rows may route");
  auto definition=registry.definition(row);check(definition.has_value(),"trusted definition missing");
  tasks::ManualTaskAdapter a(*definition);
  auto oldChoose=a.capture(tasks::IntentKind::SourceOrder);
  check(a.apply(oldChoose,std::nullopt,{20,300}),"choose source order");
  check(!a.apply(oldChoose,std::nullopt,{20,300}),"duplicate mode refused");
  check(a.apply(a.capture(tasks::IntentKind::Ready),std::nullopt,{20,300}),"source Ready");
  check(!a.clockArmed(),"source-order must not use clock");
  for(int i=0;i<4;++i){
   auto token=a.capture(tasks::IntentKind::Acknowledge);
   check(a.apply(token,std::nullopt,{20,300}),"ack current action");
   check(!a.apply(token,std::nullopt,{20,300}),"duplicate old action refused");
  }
  check(a.view().phase==tasks::Phase::Release&&a.view().outcome==tasks::Outcome::None,"manual steps require release");
  check(a.apply(a.capture(tasks::IntentKind::Release),std::nullopt,{20,300}),"release ack");
  check(a.view().outcome==tasks::Outcome::UserReportedStepsFinished,"completion is user report only");
  check(a.apply(a.capture(tasks::IntentKind::Again),std::nullopt,{20,300}),"again");
  check(!a.apply(a.capture(tasks::IntentKind::EvenPulse),60,{61,300}),"current host range refusal");
  check(!a.apply(a.capture(tasks::IntentKind::EvenPulse),std::nullopt,{20,300}),"missing bpm refusal");
  check(a.apply(a.capture(tasks::IntentKind::EvenPulse),60,{20,300}),"explicit bpm choice");
  const auto setupRevision=a.revision(),setupPass=a.pass();
  check(!a.apply(a.capture(tasks::IntentKind::Ready),std::nullopt,{20,300}),"paced Ready requires current BPM");
  check(!a.apply(a.capture(tasks::IntentKind::Ready),120,{20,300}),"changed visible BPM requires reselect");
  check(!a.apply(a.capture(tasks::IntentKind::Ready),301,{20,300}),"out-of-range current BPM refused");
  check(!a.apply(a.capture(tasks::IntentKind::Ready),60,{61,300}),"Ready revalidates host range");
  check(a.view().phase==tasks::Phase::Setup&&a.view().selectedBpm==60&&a.revision()==setupRevision&&a.pass()==setupPass&&!a.clockArmed(),"Ready refusals preserve selected Setup without clock or credit");
  check(a.apply(a.capture(tasks::IntentKind::Ready),60,{20,300}),"same-value paced Ready");
  const auto firstOwner=owner(1,1);
  check(a.armClock(firstOwner,1,48000),"arm exact shared clock");
  check(!a.progress(progress(owner(2,1),1,1,0)),"foreign owner refused");
  check(!a.progress(progress(firstOwner,2,1,0)),"wrong binding refused");
  check(a.progress(progress(firstOwner,1,1,0)),"pass origin observed");
  check(!a.progress(progress(firstOwner,1,1,100)),"duplicate sequence refused");
  auto acceptedPartial=progress(firstOwner,1,2,48000);acceptedPartial.partial=true;
  check(a.progress(acceptedPartial),"callback-accepted partial running progress advances q1");
  check(a.view().actionIndex==1,"q1 shows low step");
  auto oldQ4=progress(firstOwner,1,3,192000);
  check(a.apply(a.capture(tasks::IntentKind::Retry),std::nullopt,{20,300}),"retry invalidates pass");
  check(!a.progress(oldQ4),"late q4 refused");
  check(a.apply(a.capture(tasks::IntentKind::Release),std::nullopt,{20,300}),"release retry");
  check(a.apply(a.capture(tasks::IntentKind::Again),std::nullopt,{20,300}),"fresh pass");
  check(a.apply(a.capture(tasks::IntentKind::EvenPulse),60,{20,300}),"fresh bpm choice");
  check(a.apply(a.capture(tasks::IntentKind::Ready),60,{20,300}),"fresh Ready");
  check(a.armClock(owner(1,2),2,48000),"fresh generation");
  check(!a.progress(oldQ4),"old q4 cannot finish new pass");
  check(a.progress(progress(owner(1,2),2,1,0)),"new pass origin");
  check(a.progress(progress(owner(1,2),2,2,192000)),"new q4");
  check(a.view().phase==tasks::Phase::Release&&a.view().outcome==tasks::Outcome::None,"numeric cue never credits");
  check(a.apply(a.capture(tasks::IntentKind::Release),std::nullopt,{20,300}),"paced release");
  check(a.view().outcome==tasks::Outcome::None,"paced outcome remains none");
  a.invalidateForNavigation();check(!a.progress(progress(owner(1,2),2,3,192001)),"navigation invalidates clock");
  std::cout<<"PASS typed manual adapter source, stale-intent, tempo, clock and no-credit checks\n";
  return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}
