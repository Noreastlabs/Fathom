#include "tasks/InstalledAdvancedRecipeRegistry.hpp"
#include "content/Canonical.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
using namespace fathom;using namespace fathom::tasks::advanced;
namespace {
namespace fs=std::filesystem;using V=json::Value;std::size_t assertions{},refusals{};
void need(bool v,const char* message) {++assertions;if (!v) throw std::runtime_error(message);}
const V& f(const V& value,const char* name) {const auto* p=value.find(name);need(p!=nullptr,"FIELD");return *p;}
void write(const fs::path& path,const std::string& bytes) {std::ofstream stream(path,std::ios::binary|std::ios::trunc);stream<<bytes;need(stream.good(),"MUTANT_WRITE");}
void mutate(const fs::path& path) {auto bytes=content::readBounded(path,512*1024);need(!bytes.empty(),"NONEMPTY_MUTANT");bytes.front()^=1;write(path,bytes);}
void refuse(const fs::path& path) {
    const auto registry=InstalledAdvancedRecipeRegistry::load(path);need(!registry.ready() && registry.size()==0 && !registry.error().empty(),"CORRUPT_SNAPSHOT_PARTIALLY_ADMITTED");
    for (const auto& key:allKeys()) need(!registry.contains(key) && !registry.definition(key) && !registry.installedDefinitionPath(key),"CORRUPT_SNAPSHOT_LEAKED_ROUTE");need(registry.sourceFilesHashed()<=4,"SOURCE_HASH_REPEATED_PER_ROW");++refusals;
}
void verify(const fs::path& path) {
    const auto registry=InstalledAdvancedRecipeRegistry::load(path);need(registry.ready() && registry.size()==56 && registry.error().empty(),"EXACT_CLOSED56_PACKAGE_REFUSED");need(registry.sourceFilesHashed()==4,"FOUR_SOURCE_HASHES_PER_SNAPSHOT");
    need(!registry.contains("foreign") && !registry.definition("foreign") && !registry.installedDefinitionPath("foreign"),"FOREIGN_ROUTE");std::set<std::string> files;
    for (const auto& key:allKeys()) {
        auto installed=registry.definition(key);auto file=registry.installedDefinitionPath(key);const auto& trusted=definition(key);
        need(installed && file && registry.contains(key) && fs::is_regular_file(*file) && files.insert(file->generic_string()).second,"EXACT_SOURCE_IDENTITY_PATH_ROUTE");
        need(installed->exportedDefinition()==trusted.exportedDefinition() && installed->retainedSourceContext()==trusted.retainedSourceContext() && installed->retainedContract()==trusted.retainedContract(),"COMPLETE_NATIVE_CONTEXT_CONTRACT_MISMATCH");
        need(json::parse(content::readBounded(*file,65536))==trusted.exportedDefinition(),"INSTALLED_ROW_BYTES_DIFFER");const auto identity=f(trusted.exportedDefinition(),"source_identity").string();need(!registry.contains(identity),"UNPREFIXED_ALIAS_SCOPE_WIDENED");
        if (trusted.recipe()=="chord_tone_transfer") {AdvancedRecipeTask task(*installed);need(!task.learnerView().find("reference_pitch"),"HIDDEN_TRANSFER_REFERENCE_LEAK");}
        else {AdvancedRecipeWorkflow task(*installed);need(!task.learnerView().find("source_reference") && !f(task.snapshot(),"runtime_admitted").boolean(),"HIDDEN_REFERENCE_OR_RUNTIME_CLAIM");}
    }need(files.size()==56 && registry.sourceFilesHashed()==4,"EXACT_PATH_DENOMINATOR");
}
}
int main(int argc,char** argv) {try {
    need(argc==3,"ARGS: advanced-package fresh-mutant-directory");const auto package=fs::absolute(argv[1]).lexically_normal(),mutant=fs::absolute(argv[2]).lexically_normal();need(!fs::exists(mutant),"FRESH_MUTANT_REQUIRED");verify(package);fs::copy(package,mutant,fs::copy_options::recursive);
    const auto manifest=json::parse(content::readBounded(package/"manifest.json",128*1024));const auto& rows=f(manifest,"definitions").array();const auto first=f(f(rows.front(),"definition"),"path").string(),middle=f(f(rows[14],"definition"),"path").string(),last=f(f(rows.back(),"definition"),"path").string();
    auto restore=[&](const std::string& relative) {fs::remove(mutant/relative);fs::copy_file(package/relative,mutant/relative);};
    std::vector<std::string> changed{"manifest.json","definitions.jsonl","family-closure.json",first,middle,last};for (const auto& source:f(manifest,"source_files").array()) changed.push_back(f(source,"path").string());
    for (const auto& path:changed) {mutate(mutant/path);refuse(mutant);restore(path);}
    for (const auto& path:{std::string("manifest.json"),first,middle,last}) {fs::remove(mutant/path);refuse(mutant);restore(path);}
    const auto source=f(f(manifest,"source_files").array().front(),"path").string();for (const auto& path:{first,source}) {fs::remove(mutant/path);fs::create_symlink(package/path,mutant/path);refuse(mutant);restore(path);}
    write(mutant/"foreign-extra.json","{}\n");refuse(mutant);fs::remove(mutant/"foreign-extra.json");const auto alias=mutant.parent_path()/(mutant.filename().string()+"-symlink");need(!fs::exists(alias),"FRESH_ALIAS");fs::create_directory_symlink(package,alias);refuse(alias);fs::remove(alias);
    for (const std::string field:{"schema","source_keys","bulk_definitions","version_bindings","definitions","grants_credit","runtime_admitted"}) {
        auto bad=manifest;
        if (field=="schema") bad.object().at(field)="foreign";
        else if (field=="source_keys") bad.object().at(field).array().push_back("foreign/new/key");
        else if (field=="bulk_definitions") bad.object().at(field).object().at("path")="../definitions.jsonl";
        else if (field=="version_bindings") bad.object().at(field).object().erase("native_engine_cpp_sha256");
        else if (field=="definitions") bad.object().at(field).array().back()=bad.object().at(field).array().front();
        else bad.object().at(field)=true;
        write(mutant/"manifest.json",json::stringify(bad)+"\n");refuse(mutant);restore("manifest.json");
    }
    verify(mutant);verify(package);need(refusals==25,"EXACT_PACKAGE_MUTANT_DENOMINATOR");
    std::cout<<"{\"outcome\":\"PASS\",\"source_rows\":56,\"installed_definition_paths\":56,\"package_files\":63,\"source_files_hashed_once_per_snapshot\":4,\"negative_package_cases\":"<<refusals<<",\"assertions\":"<<assertions<<",\"runtime_candidate\":true,\"runtime_admitted\":false,\"official_accepted\":false,\"grants_credit\":false}\n";return 0;
}catch(const std::exception& error){std::cerr<<error.what()<<"\n";return 1;} }
