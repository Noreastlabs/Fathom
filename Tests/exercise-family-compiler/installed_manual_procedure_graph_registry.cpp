#include "tasks/InstalledManualProcedureGraphRegistry.hpp"
#include "content/StrictJson.hpp"
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <set>
using namespace fathom;using namespace fathom::tasks::manual_procedure_graph;
namespace fs=std::filesystem;using V=json::Value;
namespace {
std::size_t assertions{},mutants{};
void check(bool b,const char* why="CHECK") {++assertions;if(!b)throw std::runtime_error(why);}
const V& f(const V& v,const char* n) {const auto* p=v.find(n);check(p!=nullptr,"FIELD");return *p;}
std::string read(const fs::path& p) {std::ifstream in(p,std::ios::binary);check(in.good());return {std::istreambuf_iterator<char>(in),{}};}
void write(const fs::path& p,const std::string& bytes) {fs::create_directories(p.parent_path());std::ofstream out(p,std::ios::binary|std::ios::trunc);check(out.good());out<<bytes;check(out.good());}
void failClosed(const fs::path& package,const fs::path& assets) {
    const auto registry=InstalledManualProcedureGraphRegistry::load(package,assets);check(!registry.ready()&&registry.size()==0&&!registry.error().empty(),"MUTANT_ACCEPTED");
    for(const auto& key:keys())check(!registry.contains(key)&&!registry.definition(key)&&!registry.rowBinding(key)&&!registry.installedDefinitionPath(key)&&!registry.containsSourceIdentity(definition(key).sourceIdentity())&&!registry.definitionForSourceIdentity(definition(key).sourceIdentity()),"PARTIAL_ROUTE_EXPOSED");++mutants;
}
}
int main(int argc,char** argv) {try {
    check(argc==4,"ARGS package source-library-assets scratch");const auto package=fs::absolute(argv[1]),assets=fs::absolute(argv[2]),scratch=fs::absolute(argv[3]);check(!fs::exists(scratch));fs::create_directories(scratch);
    const auto registry=InstalledManualProcedureGraphRegistry::load(package,assets);check(registry.ready(),registry.error().c_str());check(registry.size()==224&&registry.sourceFilesHashed()==16);check(!registry.contains("foreign")&&!registry.definition("foreign")&&!registry.rowBinding("foreign"));
    std::size_t index=0;for(const auto& key:keys()) {
        const auto d=registry.definition(key);const auto binding=registry.rowBinding(key);check(d&&binding&&registry.contains(key));check(registry.containsSourceIdentity(d->sourceIdentity())&&registry.definitionForSourceIdentity(d->sourceIdentity())->sourceKey()==key);check(d->exportedDefinition()==definition(key).exportedDefinition());check(binding->bulkDefinitionsPath==package/"definitions.jsonl"&&binding->jsonlLine==++index&&binding->sourceKey==key&&binding->sourceIdentity==d->sourceIdentity()&&binding->contractSha256==d->contractSha256());check(binding->originalRowSha256==f(d->exportedDefinition(),"original_row_sha256").string());check(registry.installedDefinitionPath(key)==std::optional<fs::path>(package/"definitions.jsonl"));ManualProcedureGraph owner(*d);check(f(owner.learnerView(),"state")==V("select")&&!owner.learnerView().find("printed_self_check"));
    }
    const auto clone=scratch/"package";fs::copy(package,clone,fs::copy_options::recursive);const auto manifestBytes=read(package/"manifest.json"),bulk=read(package/"definitions.jsonl"),closure=read(package/"contexts.json");const auto manifest=json::parse(manifestBytes);
    auto mutatedManifest=[&](const std::function<void(V&)>& mutate){auto m=manifest;mutate(m);write(clone/"manifest.json",json::stringify(m));failClosed(clone,assets);write(clone/"manifest.json",manifestBytes);};
    mutatedManifest([](V& m){m.object()["schema"]="foreign";});mutatedManifest([](V& m){m.object()["family"]="foreign";});mutatedManifest([](V& m){m.object()["runtime_admitted"]=true;});mutatedManifest([](V& m){m.object()["practice_admitted"]=true;});mutatedManifest([](V& m){m.object()["official_accepted"]=true;});mutatedManifest([](V& m){m.object()["grants_credit"]=true;});mutatedManifest([](V& m){m.object()["source_clock"]=V::fromInteger(60);});
    mutatedManifest([](V& m){m.object()["source_keys"].array()[0]="foreign";});mutatedManifest([](V& m){m.object()["source_keys"].array()[1]=m.object()["source_keys"].array()[0];});mutatedManifest([](V& m){m.object()["source_keys"].array().pop_back();});mutatedManifest([](V& m){m.object()["bulk_definitions"].object()["path"]="../../escape";});mutatedManifest([](V& m){m.object()["source_assets"].array()[0].object()["path"]="/absolute";});mutatedManifest([](V& m){m.object()["version_bindings"].object()["native_engine_cpp_sha256"]=std::string(64,'0');});mutatedManifest([](V& m){m.object().erase("version_bindings");});
    write(clone/"manifest.json","{\"schema\":1,\"schema\":2}");failClosed(clone,assets);write(clone/"manifest.json",manifestBytes);
    for(const auto& file:{"manifest.json","definitions.jsonl","contexts.json"}) {const auto bytes=read(clone/file);fs::remove(clone/file);failClosed(clone,assets);write(clone/file,bytes);write(clone/file,bytes+"corrupt");failClosed(clone,assets);write(clone/file,bytes);}
    write(clone/"unexpected.json","{}");failClosed(clone,assets);fs::remove(clone/"unexpected.json");fs::create_directory(clone/"unexpected-directory");failClosed(clone,assets);fs::remove(clone/"unexpected-directory");
    fs::remove(clone/"definitions.jsonl");fs::create_symlink(package/"definitions.jsonl",clone/"definitions.jsonl");failClosed(clone,assets);fs::remove(clone/"definitions.jsonl");write(clone/"definitions.jsonl",bulk);
    const auto rootLink=scratch/"package-link";fs::create_directory_symlink(clone,rootLink);failClosed(rootLink,assets);
    const auto assetCopy=scratch/"source-assets";fs::create_directories(assetCopy);for(const auto& ref:f(manifest,"source_assets").array()){const auto p=f(ref,"path").string();write(assetCopy/p,read(assets/p));}
    check(InstalledManualProcedureGraphRegistry::load(clone,assetCopy).ready());const auto first=f(manifest,"source_assets").array()[0];const auto firstPath=f(first,"path").string(),original=read(assetCopy/firstPath);write(assetCopy/firstPath,original+"corrupt");failClosed(clone,assetCopy);write(assetCopy/firstPath,original);fs::remove(assetCopy/firstPath);failClosed(clone,assetCopy);fs::create_symlink(assets/firstPath,assetCopy/firstPath);failClosed(clone,assetCopy);fs::remove(assetCopy/firstPath);write(assetCopy/firstPath,original);
    const auto assetLink=scratch/"assets-link";fs::create_directory_symlink(assetCopy,assetLink);failClosed(clone,assetLink);
    check(read(package/"manifest.json")==manifestBytes&&read(package/"definitions.jsonl")==bulk&&read(package/"contexts.json")==closure);check(InstalledManualProcedureGraphRegistry::load(clone,assetCopy).ready());std::set<std::string> names;for(const auto& e:fs::directory_iterator(package)){check(e.is_regular_file()&&!e.is_symlink());names.insert(e.path().filename().string());}check(names==std::set<std::string>{"manifest.json","definitions.jsonl","contexts.json"});
    std::cout<<"{\"outcome\":\"PASS\",\"exact_rows\":224,\"closed_row_bindings\":224,\"package_files\":3,\"host_source_assets\":16,\"assets_hashed_once_per_snapshot\":16,\"negative_cases\":"<<mutants<<",\"assertions\":"<<assertions<<",\"mutant_snapshots_only\":true,\"runtime_admitted\":false,\"official_accepted\":false,\"grants_credit\":false}\n";return 0;
} catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;} }
