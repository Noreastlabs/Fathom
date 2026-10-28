#include "tasks/InstalledAdvancedRecipeRegistry.hpp"
#include "content/Canonical.hpp"
#include "GeneratedAdvancedInstalledVersions.hpp"
#include <set>
#include <sstream>
#include <stdexcept>

#ifndef FATHOM_ADVANCED_RECIPE_MANIFEST_SHA
#error Advanced installed manifest must be bound by the integrating build
#endif

namespace fathom::tasks::advanced {
namespace {
using V=json::Value;namespace fs=std::filesystem;
void need(bool ok,const char* message) { if (!ok) throw std::runtime_error(message); }
const V& at(const V& value,const char* name) { need(value.isObject(),"Advanced object required");const auto* p=value.find(name);need(p!=nullptr,"Advanced field missing");return *p; }
std::string text(const V& value,const char* name) { const auto& v=at(value,name);need(v.isString(),"Advanced string required");return v.string(); }
void shape(const V& value,std::initializer_list<const char*> names) { need(value.isObject() && value.object().size()==names.size(),"Advanced exact schema required");for (auto name:names) (void)at(value,name); }
std::size_t count(const V& value) { std::int64_t n{};need(value.integer(n) && n>=0,"Advanced integer required");return static_cast<std::size_t>(n); }
fs::path safeFile(const fs::path& root,const std::string& relative) {
    const fs::path path{relative};need(!relative.empty() && !path.is_absolute() && path.generic_string()==relative,"Advanced relative path required");fs::path next=root;
    for (const auto& part:path) {need(part!="." && part!=".." && !part.empty(),"Advanced unsafe path component");next/=part;need(!fs::is_symlink(fs::symlink_status(next)),"Advanced symlink refused");}
    need(fs::is_regular_file(next),"Advanced regular file required");return next;
}
std::string read(const fs::path& root,const std::string& path,std::size_t limit) { return content::readBounded(safeFile(root,path),limit); }
void pin(const V& ref,const std::string& bytes) {shape(ref,{"path","bytes","sha256"});need(count(at(ref,"bytes"))==bytes.size() && text(ref,"sha256")==content::sha256(bytes),"Advanced bytes/hash differ");}
V versions() {return json::parse(advanced_installed_generated::versionsJson);}
V familyCounts() {return V::Object{{"chord_tone_transfer",V::fromInteger(14)},{"full_reconstruction",V::fromInteger(1)},{"fixed_top_reduction",V::fromInteger(41)}};}
}
InstalledAdvancedRecipeRegistry InstalledAdvancedRecipeRegistry::load(const fs::path& input) {
    InstalledAdvancedRecipeRegistry registry;
    try {
        const auto directory=fs::absolute(input).lexically_normal();need(fs::is_directory(directory) && !fs::is_symlink(fs::symlink_status(directory)) && fs::canonical(directory)==directory,"Advanced package root must be an exact real directory");
        std::set<std::string> expectedFiles{"manifest.json","definitions.jsonl","family-closure.json"};const auto manifestBytes=read(directory,"manifest.json",128*1024);
        need(content::sha256(manifestBytes)==FATHOM_ADVANCED_RECIPE_MANIFEST_SHA,"Advanced manifest differs from compiled installed version");const auto manifest=json::parse(manifestBytes);
        shape(manifest,{"schema","family","scope","source_clock","source_tempo","runtime_candidate","runtime_admitted","practice_admitted","official_accepted","grants_credit","source_keys","recipe_counts","version_bindings","bulk_definitions","source_closure","definitions","source_files"});
        need(text(manifest,"schema")=="fathom.compiled-recipe-family-package.1" && text(manifest,"family")=="advanced" && text(manifest,"scope")=="manual-guidance-candidate","Advanced package schema/family differs");
        need(at(manifest,"source_clock").null() && at(manifest,"source_tempo").null() && at(manifest,"runtime_candidate")==V(true) && at(manifest,"runtime_admitted")==V(false) && at(manifest,"practice_admitted")==V(false) && at(manifest,"official_accepted")==V(false) && at(manifest,"grants_credit")==V(false),"Advanced candidate/noncredit scope differs");
        const auto expectedVersions=versions();need(at(manifest,"version_bindings")==expectedVersions && at(manifest,"recipe_counts")==familyCounts(),"Advanced native/version/family denominator differs");
        const auto& keys=allKeys();const auto& sourceKeys=at(manifest,"source_keys");need(sourceKeys.isArray() && sourceKeys.array().size()==56 && keys.size()==56,"Advanced closed56 source keys required");for (std::size_t i=0;i<56;++i) need(sourceKeys.array()[i]==V(keys[i]),"Advanced source key/order differs");
        const auto& bulkPin=at(manifest,"bulk_definitions");const auto& closurePin=at(manifest,"source_closure");need(text(bulkPin,"path")=="definitions.jsonl" && text(closurePin,"path")=="family-closure.json","Advanced fixed data paths differ");
        const auto bulk=read(directory,"definitions.jsonl",512*1024);pin(bulkPin,bulk);need(text(bulkPin,"sha256")==text(expectedVersions,"definitions_sha256"),"Advanced definitions version differs");
        const auto closureBytes=read(directory,"family-closure.json",512*1024);pin(closurePin,closureBytes);need(text(closurePin,"sha256")==text(expectedVersions,"closure_sha256"),"Advanced source closure version differs");
        const auto closure=json::parse(closureBytes);need(text(closure,"schema")=="fathom.compiled-advanced-manual-closure.1" && count(at(closure,"rows"))==56 && at(closure,"recipe_counts")==familyCounts() && at(closure,"source_clock").null() && at(closure,"fixed_bpm").null() && at(closure,"actual_performance_observed")==V(false) && at(closure,"runtime_admitted")==V(false) && at(closure,"official_accepted")==V(false),"Advanced closure source/noncredit boundary differs");
        std::map<std::string,V> sourcePins;for (const auto& source:at(closure,"source_pins").array()) need(text(source,"path").rfind("Notes/",0)==0 && sourcePins.emplace(text(source,"path"),source).second,"Advanced source pin duplicate or foreign");
        const auto& sources=at(manifest,"source_files");need(sources.isArray() && sources.array().size()==4 && sourcePins.size()==4,"Advanced four original source files required");std::set<std::string> seenSources;
        for (const auto& source:sources.array()) {
            shape(source,{"path","original_path","bytes","sha256"});const auto original=text(source,"original_path"),path=text(source,"path");need(sourcePins.count(original)==1 && seenSources.insert(original).second && path=="assets/"+original,"Advanced source path/key differs");
            const auto& ref=sourcePins.at(original);need(at(source,"bytes")==at(ref,"bytes") && at(source,"sha256")==at(ref,"sha256"),"Advanced source version differs");const auto bytes=read(directory,path,256*1024);++registry.sourceFilesHashed_;
            need(bytes.size()==count(at(source,"bytes")) && content::sha256(bytes)==text(source,"sha256"),"Advanced original source bytes differ");expectedFiles.insert(path);
        }
        const auto& definitions=at(manifest,"definitions");need(definitions.isArray() && definitions.array().size()==56,"Advanced installed row count differs");std::istringstream lines(bulk);std::string line;std::size_t n=0;
        while (std::getline(lines,line)) {
            need(!line.empty() && n<56,"Advanced bulk denominator differs");const auto row=json::parse(line);const auto& trusted=advanced::definition(keys[n]);need(row==trusted.exportedDefinition() && trusted.sourceClosureSha256()==text(closurePin,"sha256"),"Advanced exact native retained contract differs");
            const auto contextRef=text(row,"context_ref"),identity=text(row,"source_identity");const auto* context=at(closure,"contexts").find(contextRef);need(context && *context==trusted.retainedSourceContext(),"Advanced shared operational context differs");
            const auto& item=definitions.array()[n];shape(item,{"source_key","source_identity","recipe","context_ref","contract_sha256","definition"});need(text(item,"source_key")==keys[n] && text(item,"source_identity")==identity && at(item,"recipe")==at(row,"recipe") && at(item,"context_ref")==at(row,"context_ref") && text(item,"contract_sha256")==trusted.contractSha256(),"Advanced row identity/model/context differs");
            const auto& ref=at(item,"definition");const auto path="definitions/"+identity+"/definition.json";need(text(ref,"path")==path,"Advanced exact installed identity path differs");const auto bytes=read(directory,path,65536);pin(ref,bytes);
            need(bytes==line+"\n" && json::parse(bytes)==trusted.exportedDefinition(),"Advanced installed row differs from complete native/bulk contract");expectedFiles.insert(path);need(registry.paths_.emplace(keys[n],directory/path).second,"Advanced duplicate identity");++n;
        }
        need(n==56 && registry.paths_.size()==56,"Advanced complete native56 family required");std::set<std::string> foundFiles;
        for (const auto& entry:fs::recursive_directory_iterator(directory)) {need(!entry.is_symlink(),"Advanced package symlink refused");if (entry.is_regular_file()) need(foundFiles.insert(entry.path().lexically_relative(directory).generic_string()).second,"Advanced duplicate file path");else need(entry.is_directory(),"Advanced special file refused");}
        need(foundFiles==expectedFiles,"Advanced package missing or unexpected files");registry.ready_=true;
    } catch (const std::exception& error) {registry.ready_=false;registry.paths_.clear();registry.error_=error.what();}
    return registry;
}
bool InstalledAdvancedRecipeRegistry::contains(const std::string& key) const noexcept {return ready_ && paths_.count(key)==1;}
std::optional<Definition> InstalledAdvancedRecipeRegistry::definition(const std::string& key) const {if (!contains(key)) return std::nullopt;return advanced::definition(key);}
std::optional<fs::path> InstalledAdvancedRecipeRegistry::installedDefinitionPath(const std::string& key) const {if (!contains(key)) return std::nullopt;return paths_.at(key);}
} // namespace fathom::tasks::advanced
