#include "tasks/InstalledRecipeTaskRegistry.hpp"
#include "content/Canonical.hpp"
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <set>

using namespace fathom;
using namespace fathom::tasks::recipes;
namespace {
namespace fs=std::filesystem;
std::size_t checks{}, refusals{};
void check(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
void change(const fs::path& path){auto bytes=content::readBounded(path,128*1024);check(!bytes.empty(),"nonempty mutation input");bytes.front()^=1;std::ofstream out(path,std::ios::binary|std::ios::trunc);out<<bytes;check(out.good(),"mutation write");}
void refuse(const fs::path& path){auto bad=InstalledRecipeTaskRegistry::load(path);check(!bad.error().empty()&&bad.size()==0,"corrupt package must fail closed");for(const auto& key:keys())check(!bad.contains(key)&&!bad.definition(key)&&!bad.installedDefinitionPath(key),"corrupt package granted a partial key/path");check(bad.sourceFilesHashed()<=2,"source hashes repeated per key");++refusals;}
void verify(const fs::path& package){
 auto registry=InstalledRecipeTaskRegistry::load(package);check(registry.error().empty()&&registry.size()==17,"full reviewed package must load");check(registry.sourceFilesHashed()==2,"packaged sources must be read/hashed once each");std::set<std::string> paths;
 check(!registry.contains("foreign")&&!registry.definition("foreign")&&!registry.installedDefinitionPath("foreign"),"untrusted identity route");
 for(const auto& key:keys()){
  check(registry.contains(key),"every compiled exact key must route");auto d=registry.definition(key);check(bool(d)&&d->exportedDefinition()==definition(key).exportedDefinition()&&d->retainedSourceContext()==definition(key).retainedSourceContext(),"installed definition differs from exact trusted factory/context");
  const auto identity=d->sourceIdentity();check(!registry.contains(identity),"unprefixed key must not broaden this exact-key factory");auto path=registry.installedDefinitionPath(key);check(bool(path)&&fs::is_regular_file(*path)&&paths.insert(path->string()).second,"every exact installed path must exist and be unique");
  check(json::parse(content::readBounded(*path,16384))==d->exportedDefinition(),"installed path full retained contract differs");
  RecipeTask task(*d);json::Value::Object choice{{"package_key",key},{"contract_sha256",d->contractSha256()},{"start_stroke","D"}};
  if(d->recipe()==Recipe::RecoveryPair){auto origin=allowedChoices(*d).find("source_contacts")->array().front();auto target=allowedChoices(*d,origin).find("nearest_target_contacts")->array().front();choice.emplace("source_contact",origin);choice.emplace("target_contact",target);choice.emplace("rest_of_bar_plan","Explicit installed-test fixture only: sustain the secure target, then release. Never a default user plan.");}
  task.apply(task.capture(Intent::Choose),choice);
  for(std::size_t n=0;n<d->reports().size();++n){task.apply(task.capture(Intent::Report),task.expectedReport());check(!task.view().observedPerformance&&!task.view().grantsCredit,"manual pass claimed performance/credit");}
  check(task.view().phase==Phase::Release&&task.view().pendingOutcome==Outcome::UserReportedStepsFinished,"positive manual path must still await release");
  task.apply(task.capture(Intent::Release),json::Value::Object{{"released_completely_reported",true}});check(task.view().phase==Phase::Closed&&task.view().outcome==Outcome::UserReportedStepsFinished,"installed task explicit release close");
  for(const auto& event:task.history())check(!event.observedPerformance&&!event.grantsCredit,"history claimed performance/credit");
 }
 check(paths.size()==17&&registry.sourceFilesHashed()==2,"complete path denominator and cached source hashes");
}
}
int main(int argc,char** argv){try{
 check(argc==3,"usage: installed-recipe-registry <level068-package> <fresh-mutant-directory>");const fs::path package=fs::absolute(argv[1]).lexically_normal(),mutant=fs::absolute(argv[2]).lexically_normal();check(!fs::exists(mutant),"mutant directory must be fresh");verify(package);
 fs::copy(package,mutant,fs::copy_options::recursive);const auto manifest=json::parse(content::readBounded(package/"manifest.json",65536));const auto& rows=manifest.find("definitions")->array();
 const auto first=rows.front().find("definition")->find("path")->string(),last=rows.back().find("definition")->find("path")->string();
 std::vector<std::string> changed{"manifest.json","definitions.jsonl","family-closure.json",first,last};for(const auto& source:manifest.find("source_files")->array())changed.push_back(source.find("path")->string());
 for(const auto& relative:changed){change(mutant/relative);refuse(mutant);fs::remove(mutant/relative);fs::copy_file(package/relative,mutant/relative);}
 for(const auto& relative:{std::string{"manifest.json"},first,last}){fs::remove(mutant/relative);refuse(mutant);fs::copy_file(package/relative,mutant/relative);}
 // Unchanged bytes through symlinks must still refuse, including the package root.
 const auto sourcePath=manifest.find("source_files")->array().front().find("path")->string();
 for(const auto& relative:{first,sourcePath}){fs::remove(mutant/relative);fs::create_symlink(package/relative,mutant/relative);refuse(mutant);fs::remove(mutant/relative);fs::copy_file(package/relative,mutant/relative);}
 {std::ofstream extra(mutant/"unreviewed.json");extra<<"{}\n";}refuse(mutant);fs::remove(mutant/"unreviewed.json");
 const auto alias=mutant.parent_path()/(mutant.filename().string()+"-symlink");check(!fs::exists(alias),"alias must be fresh");fs::create_directory_symlink(package,alias);refuse(alias);fs::remove(alias);
 // Signed metadata cannot be replaced by a changed schema, widened key or path.
 for(const auto& field:{"schema","source_keys","bulk_definitions"}){auto bad=manifest;if(std::string{field}=="schema")bad.object().at(field)="untrusted";else if(std::string{field}=="source_keys")bad.object().at(field).array().push_back("foreign");else bad.object().at(field).object().at("path")="../definitions.jsonl";
  {std::ofstream out(mutant/"manifest.json",std::ios::binary|std::ios::trunc);out<<json::stringify(bad)<<'\n';}refuse(mutant);fs::remove(mutant/"manifest.json");fs::copy_file(package/"manifest.json",mutant/"manifest.json");}
 verify(mutant);verify(package);
 std::cout<<"{\"result\":\"PASS\",\"rows\":17,\"installed_definition_paths\":17,\"packaged_source_files_hashed_once\":2,\"negative_package_cases\":"<<refusals<<",\"assertions\":"<<checks<<",\"runtime_candidate\":true,\"runtime_admitted\":false,\"official_accepted\":false,\"grants_credit\":false}\n";return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
