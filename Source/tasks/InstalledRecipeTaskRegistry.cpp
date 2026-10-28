#include "tasks/InstalledRecipeTaskRegistry.hpp"
#include "content/Canonical.hpp"
#include <fstream>
#include <set>
#include <sstream>
#include <stdexcept>

#ifndef FATHOM_LEVEL068_RECIPE_MANIFEST_SHA
#error Level68 installed recipe manifest must be bound by the integrating build
#endif

namespace fathom::tasks::recipes {
namespace {
using V=json::Value;
namespace fs=std::filesystem;
void need(bool good,const char* message){if(!good)throw std::runtime_error(message);}
const V& at(const V& value,const char* key){need(value.isObject(),"Recipe object required");const auto* p=value.find(key);need(p!=nullptr,"Recipe field missing");return *p;}
std::string text(const V& value,const char* key){const auto& v=at(value,key);need(v.isString(),"Recipe string required");return v.string();}
void shape(const V& value,std::initializer_list<const char*> names){need(value.isObject()&&value.object().size()==names.size(),"Recipe exact schema required");for(const auto* name:names)(void)at(value,name);}
std::size_t count(const V& value){std::int64_t n{};need(value.integer(n)&&n>=0,"Recipe integer required");return static_cast<std::size_t>(n);}
fs::path safeFile(const fs::path& root,const std::string& relative){
    const fs::path path{relative};need(!relative.empty()&&!path.is_absolute()&&path.generic_string()==relative,"Recipe relative path required");
    fs::path next=root;for(const auto& part:path){need(part!="."&&part!=".."&&!part.empty(),"Recipe unsafe path component");next/=part;need(!fs::is_symlink(fs::symlink_status(next)),"Recipe symlink refused");}
    need(fs::is_regular_file(next),"Recipe file required");return next;
}
std::string read(const fs::path& root,const std::string& relative,std::size_t limit){return content::readBounded(safeFile(root,relative),limit);}
void pin(const V& value,const std::string& bytes){shape(value,{"path","bytes","sha256"});need(count(at(value,"bytes"))==bytes.size()&&text(value,"sha256")==content::sha256(bytes),"Recipe file bytes/hash differ");}
V expectedVersions(){return V::Object{
    {"definitions_sha256","0dee1bf5ebebf361eafc9ad7b79e56ca6e7d3c4ad58a4fd6c53ab986d2d4efdf"},
    {"closure_sha256","e1ec9a40e149cb58c60af53b9f5bf63e0e23ecb9a6359046bdf93a2798dfb511"},
    {"native_family_header_sha256","def38b7c3ef4a0d1886f40c471cb68fc7dc5cbd00749216ca07a01dee31890a6"},
    {"native_context_header_sha256","64f7ea51572fa69d42f7b78f9f848dcb8167520fcf8f200f5685ad7af3f12abc"},
    {"native_engine_hpp_sha256","a188481ce1c08701bf07f84be9eb99991fd60e2c42a2b564c34bd97caa5b35bc"},
    {"native_engine_cpp_sha256","9120fb27756254cfe8914780aeb17d11c8f2c3ff14103879c2d71c6e05c647bb"},
    {"native_view_hpp_sha256","cbf79c03b3e8601f780be3dc9bf21fc214ed2d483c571c3a590090ac83fe2307"},
    {"native_view_cpp_sha256","389fcc7c97909dec1a8df188c97852bcda29abc081147d6acf604a04af954fe1"},
    {"compiler_sha256","b266b1aec875052116397688dcd29d54ad3cc68ad1dc27f817530714ac9b8b1a"}};}
}
InstalledRecipeTaskRegistry InstalledRecipeTaskRegistry::load(const fs::path& input){
    InstalledRecipeTaskRegistry registry;
    try{
        const auto directory=fs::absolute(input).lexically_normal();need(fs::is_directory(directory)&&!fs::is_symlink(fs::symlink_status(directory))&&fs::canonical(directory)==directory,"Recipe package root must be an exact real directory");
        std::set<std::string> expectedFiles{"manifest.json","definitions.jsonl","family-closure.json"};
        const auto manifestBytes=read(directory,"manifest.json",65536);
        need(content::sha256(manifestBytes)==FATHOM_LEVEL068_RECIPE_MANIFEST_SHA,"Recipe manifest differs from reviewed installed version");
        const auto manifest=json::parse(manifestBytes);
        shape(manifest,{"schema","family","scope","source_clock","source_tempo","runtime_candidate","runtime_admitted","practice_admitted","official_accepted","grants_credit","source_keys","recipe_counts","version_bindings","bulk_definitions","source_closure","definitions","source_files"});
        need(text(manifest,"schema")=="fathom.compiled-recipe-family-package.1"&&text(manifest,"family")=="level068"&&text(manifest,"scope")=="manual-guidance-candidate","Recipe package schema/family differs");
        need(at(manifest,"source_clock").null()&&at(manifest,"source_tempo").null()&&at(manifest,"runtime_candidate")==V(true)&&at(manifest,"runtime_admitted")==V(false)&&at(manifest,"practice_admitted")==V(false)&&at(manifest,"official_accepted")==V(false)&&at(manifest,"grants_credit")==V(false),"Recipe candidate/noncredit scope differs");
        need(at(manifest,"version_bindings")==expectedVersions(),"Recipe source/native/UI version binding differs");
        need(at(manifest,"recipe_counts")==V(V::Object{{"call_answer",V::fromInteger(5)},{"recovery_pair",V::fromInteger(12)}}),"Recipe family denominator differs");
        const auto& sourceKeys=at(manifest,"source_keys");need(sourceKeys.isArray()&&sourceKeys.array().size()==keys().size(),"Recipe source key denominator differs");
        for(std::size_t n=0;n<keys().size();++n)need(sourceKeys.array()[n]==V(keys()[n]),"Recipe source key/order differs");
        const auto& bulkPin=at(manifest,"bulk_definitions");const auto& closurePin=at(manifest,"source_closure");
        need(text(bulkPin,"path")=="definitions.jsonl"&&text(closurePin,"path")=="family-closure.json","Recipe fixed data paths differ");
        const auto bulk=read(directory,"definitions.jsonl",128*1024);pin(bulkPin,bulk);need(text(bulkPin,"sha256")==text(expectedVersions(),"definitions_sha256"),"Recipe definitions version differs");
        const auto closureBytes=read(directory,"family-closure.json",65536);pin(closurePin,closureBytes);need(text(closurePin,"sha256")==text(expectedVersions(),"closure_sha256"),"Recipe closure version differs");
        const auto closure=json::parse(closureBytes);need(text(closure,"schema")=="fathom.compiled-level068-closure.1"&&count(at(closure,"rows"))==17&&at(closure,"source_clock").null()&&at(closure,"fixed_bpm").null()&&at(closure,"source_acoustic_gates").null()&&at(closure,"runtime_admitted")==V(false)&&at(closure,"official_accepted")==V(false),"Recipe closure source/noncredit scope differs");
        std::map<std::string,V> sourcePins;
        for(const auto& source:at(closure,"source_pins").array())if(text(source,"path").rfind("Notes/",0)==0)need(sourcePins.emplace(text(source,"path"),source).second,"Recipe source pin duplicate");
        const auto& sources=at(manifest,"source_files");need(sources.isArray()&&sources.array().size()==2&&sourcePins.size()==2,"Recipe two source files required");
        std::set<std::string> seenSources;
        for(const auto& source:sources.array()){
            shape(source,{"path","original_path","bytes","sha256"});const auto original=text(source,"original_path"),path=text(source,"path");need(sourcePins.count(original)==1&&seenSources.insert(original).second&&path=="assets/"+original,"Recipe source path/key differs");
            const auto& originalPin=sourcePins.at(original);need(at(source,"bytes")==at(originalPin,"bytes")&&at(source,"sha256")==at(originalPin,"sha256"),"Recipe source version differs");
            const auto bytes=read(directory,path,128*1024);++registry.sourceFilesHashed_;need(bytes.size()==count(at(source,"bytes"))&&content::sha256(bytes)==text(source,"sha256"),"Recipe packaged source differs");expectedFiles.insert(path);
        }
        const auto& definitions=at(manifest,"definitions");need(definitions.isArray()&&definitions.array().size()==17,"Recipe installed definition count differs");
        std::istringstream lines(bulk);std::string line;std::size_t n=0;
        while(std::getline(lines,line)){
            need(!line.empty()&&n<keys().size(),"Recipe bulk line denominator differs");const auto row=json::parse(line);const auto& trusted=recipes::definition(keys()[n]);need(row==trusted.exportedDefinition()&&trusted.sourceClosureSha256()==text(closurePin,"sha256"),"Recipe complete retained contract/factory differs");
            const auto contextRef=text(row,"context_ref");need(at(closure,"contexts").find(contextRef)&&*at(closure,"contexts").find(contextRef)==trusted.retainedSourceContext(),"Recipe shared source context differs");
            const auto& item=definitions.array()[n];shape(item,{"source_key","source_identity","recipe","context_ref","contract_sha256","definition"});
            need(text(item,"source_key")==keys()[n]&&text(item,"source_identity")==trusted.sourceIdentity()&&at(item,"recipe")==at(row,"recipe")&&at(item,"context_ref")==at(row,"context_ref")&&text(item,"contract_sha256")==trusted.contractSha256(),"Recipe per-row identity/recipe/context differs");
            const auto& definitionPin=at(item,"definition");const auto path="definitions/"+trusted.sourceIdentity()+"/definition.json";need(text(definitionPin,"path")==path,"Recipe exact installed definition path differs");
            const auto bytes=read(directory,path,16384);pin(definitionPin,bytes);need(bytes==line+"\n"&&json::parse(bytes)==trusted.exportedDefinition(),"Recipe installed row differs from exact bulk/native contract");
            expectedFiles.insert(path);need(registry.paths_.emplace(keys()[n],directory/path).second,"Recipe duplicate installed identity");++n;
        }
        need(n==17&&registry.paths_.size()==17,"Recipe complete compiled family required");
        std::set<std::string> foundFiles;
        for(const auto& entry:fs::recursive_directory_iterator(directory)){
            need(!entry.is_symlink(),"Recipe package symlink refused");if(entry.is_regular_file())need(foundFiles.insert(entry.path().lexically_relative(directory).generic_string()).second,"Recipe duplicate file path");
            else need(entry.is_directory(),"Recipe package special file refused");
        }
        need(foundFiles==expectedFiles,"Recipe package has missing or unexpected files");registry.ready_=true;
    }catch(const std::exception& error){registry.ready_=false;registry.paths_.clear();registry.error_=error.what();}
    return registry;
}
bool InstalledRecipeTaskRegistry::contains(const std::string& key) const noexcept{return ready_&&paths_.find(key)!=paths_.end();}
std::optional<Definition> InstalledRecipeTaskRegistry::definition(const std::string& key) const {if(!contains(key))return std::nullopt;return recipes::definition(key);}
std::optional<fs::path> InstalledRecipeTaskRegistry::installedDefinitionPath(const std::string& key) const {if(!contains(key))return std::nullopt;return paths_.at(key);}
} // namespace fathom::tasks::recipes
