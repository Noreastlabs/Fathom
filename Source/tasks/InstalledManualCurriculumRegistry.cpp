#include "tasks/InstalledManualCurriculumRegistry.hpp"
#include "content/Canonical.hpp"
#include "GeneratedManualCurriculumInstalledVersions.hpp"
#include <set>
#include <sstream>
#ifndef FATHOM_MANUAL_CURRICULUM_MANIFEST_SHA
#error Manual curriculum installed manifest must be pinned by the integrating build
#endif
namespace fathom::tasks::manual_curriculum {
namespace {
using V=json::Value;namespace fs=std::filesystem;
void need(bool ok,const char* code) {if(!ok)throw std::runtime_error(code);}
const V& f(const V& v,const char* n) {need(v.isObject(),"OBJECT");const auto* p=v.find(n);need(p!=nullptr,"FIELDS");return *p;}
std::string str(const V& v,const char* n) {const auto& x=f(v,n);need(x.isString(),"STRING");return x.string();}
std::size_t count(const V& v) {std::int64_t n{};need(v.integer(n)&&n>=0,"COUNT");return static_cast<std::size_t>(n);}
void shape(const V& v,std::initializer_list<const char*> names) {need(v.isObject()&&v.object().size()==names.size(),"EXACT_SCHEMA");for(const auto* n:names)(void)f(v,n);}
fs::path safe(const fs::path& root,const std::string& relative) {
    const fs::path p{relative};need(!relative.empty()&&!p.is_absolute()&&p.generic_string()==relative,"RELATIVE_PATH");auto next=root;
    for(const auto& part:p){need(part!="."&&part!=".."&&!part.empty(),"UNSAFE_COMPONENT");next/=part;need(!fs::is_symlink(fs::symlink_status(next)),"SYMLINK_REFUSED");}need(fs::is_regular_file(next),"REGULAR_FILE_REQUIRED");return next;
}
std::string read(const fs::path& root,const std::string& p,std::size_t limit) {return content::readBounded(safe(root,p),limit);}
void pinned(const V& ref,const std::string& bytes) {shape(ref,{"path","bytes","sha256"});need(count(f(ref,"bytes"))==bytes.size()&&str(ref,"sha256")==content::sha256(bytes),"HASH_OR_SIZE_DRIFT");}
V versions() {return json::parse(manual_curriculum_installed_generated::versionsJson);}
V programCounts() {V::Object out;for(const auto& key:keys()){const auto n=str(manual_curriculum::definition(key).retainedProgram(),"name");auto& value=out[n];value=V::fromInteger(value.null()?1:static_cast<std::int64_t>(count(value)+1));}need(out.size()==18,"EXACT_PROGRAM_COUNT");return out;}
std::map<std::string,V> sourcePins() {
    std::map<std::string,V> out;
    for(const auto& key:keys())for(const auto& ref:f(f(manual_curriculum::definition(key).exportedDefinition(),"original_record"),"source_refs").array()) {
        const auto p=str(ref,"path");if(p.rfind("Notes/",0)!=0)continue;V pin=V::Object{{"path",p},{"bytes",f(ref,"bytes")},{"sha256",f(ref,"sha256")}};
        const auto it=out.find(p);if(it==out.end())out.emplace(p,pin);else need(it->second==pin,"SOURCE_PIN_CONTRADICTION");
    }
    need(out.size()==12,"TWELVE_ORIGINALS");return out;
}
}
InstalledManualCurriculumRegistry InstalledManualCurriculumRegistry::load(const fs::path& input,const fs::path& assetsInput) {
    InstalledManualCurriculumRegistry registry;
    try {
        const auto root=fs::absolute(input).lexically_normal();need(fs::is_directory(root)&&!fs::is_symlink(fs::symlink_status(root))&&fs::canonical(root)==root,"REAL_PACKAGE_ROOT");
        const auto assets=fs::absolute(assetsInput).lexically_normal();need(fs::is_directory(assets)&&!fs::is_symlink(fs::symlink_status(assets))&&fs::canonical(assets)==assets,"REAL_HOST_SOURCE_ASSETS_ROOT");
        std::set<std::string> expectedFiles{"manifest.json","definitions.jsonl","family-closure.json"};const auto manifestBytes=read(root,"manifest.json",256*1024);need(content::sha256(manifestBytes)==FATHOM_MANUAL_CURRICULUM_MANIFEST_SHA,"COMPILED_MANIFEST_PIN");const auto manifest=json::parse(manifestBytes);
        shape(manifest,{"schema","family","scope","source_clock","source_tempo","runtime_candidate","runtime_admitted","practice_admitted","official_accepted","grants_credit","source_keys","program_counts","version_bindings","bulk_definitions","source_closure","package_files","source_assets","resource_layout"});
        need(str(manifest,"schema")=="fathom.compiled-recipe-family-package.1"&&str(manifest,"family")=="curriculum"&&str(manifest,"scope")=="manual-guidance-candidate","PACKAGE_SCHEMA_SCOPE");
        need(f(manifest,"source_clock").null()&&f(manifest,"source_tempo").null()&&f(manifest,"runtime_candidate")==V(true)&&f(manifest,"runtime_admitted")==V(false)&&f(manifest,"practice_admitted")==V(false)&&f(manifest,"official_accepted")==V(false)&&f(manifest,"grants_credit")==V(false),"CANDIDATE_NO_ADMISSION");
        need(f(manifest,"resource_layout")==V(V::Object{{"package","compiled-recipe-families-v1/curriculum"},{"source_assets","source-library/bundle/assets"}}),"HOST_RESOURCE_LAYOUT");
        const auto v=versions();need(f(manifest,"version_bindings")==v&&f(manifest,"program_counts")==programCounts(),"VERSION_OR_PROGRAM_DRIFT");
        const auto& k=keys();const auto& sourceKeys=f(manifest,"source_keys");need(k.size()==96&&sourceKeys.isArray()&&sourceKeys.array().size()==96,"EXACT_96");for(std::size_t i=0;i<96;++i)need(sourceKeys.array()[i]==V(k[i]),"EXACT_KEY_ORDER");
        const auto& bulkPin=f(manifest,"bulk_definitions");const auto& closurePin=f(manifest,"source_closure");need(str(bulkPin,"path")=="definitions.jsonl"&&str(closurePin,"path")=="family-closure.json","FIXED_DATA_PATHS");
        const auto bulk=read(root,"definitions.jsonl",4*1024*1024);pinned(bulkPin,bulk);need(str(bulkPin,"sha256")==str(v,"definitions_sha256"),"BULK_VERSION");
        auto closureBytes=read(root,"family-closure.json",1024*1024);pinned(closurePin,closureBytes);need(str(closurePin,"sha256")==str(v,"closure_sha256"),"CLOSURE_VERSION");
        need(!closureBytes.empty()&&closureBytes.back()=='\n',"CLOSURE_RECORD_NEWLINE");closureBytes.pop_back();need(content::sha256(closureBytes)==str(v,"native_closure_record_sha256"),"NATIVE_CLOSURE_RECORD");
        const auto closure=json::parse(closureBytes);need(str(closure,"schema")=="fathom.compiled-manual-curriculum-closure.1"&&f(closure,"keys")==sourceKeys&&f(closure,"program_counts")==programCounts()&&f(closure,"runtime_admitted")==V(false)&&f(closure,"grants_credit")==V(false)&&f(closure,"new_source_extraction")==V(false),"CLOSURE_SOURCE_SCOPE");
        const auto pins=sourcePins();const auto& originals=f(manifest,"source_assets");need(originals.isArray()&&originals.array().size()==12,"ORIGINAL_DENOMINATOR");std::set<std::string> seen;
        for(const auto& source:originals.array()) {
            shape(source,{"path","bytes","sha256"});const auto p=str(source,"path");need(pins.count(p)==1&&seen.insert(p).second&&source==pins.at(p),"ORIGINAL_SOURCE_PIN");const auto bytes=read(assets,p,512*1024);++registry.sourceFilesHashed_;need(bytes.size()==count(f(source,"bytes"))&&content::sha256(bytes)==str(source,"sha256"),"ORIGINAL_SOURCE_BYTES");
        }
        std::istringstream lines(bulk);std::string line;std::size_t n=0;
        while(std::getline(lines,line)) {
            need(!line.empty()&&n<96,"BULK_DENOMINATOR");const auto row=json::parse(line);const auto& native=manual_curriculum::definition(k[n]);need(row==native.exportedDefinition()&&native.sourceClosureSha256()==str(v,"native_closure_record_sha256"),"NATIVE_FULL_ROW_PARITY");
            const auto identity=str(row,"source_identity"),contextRef=str(row,"context_ref");const auto* context=f(closure,"contexts").find(contextRef);need(context&&*context==native.retainedSourceContext(),"EXACT_CONTEXT_PARITY");
            need(str(row,"source_key")==k[n]&&str(row,"contract_sha256")==native.contractSha256()&&f(f(closure,"contracts"),k[n].c_str())==V(native.contractSha256()),"EXACT_INSTALLED_CONTRACT");
            need(registry.paths_.emplace(k[n],InstalledRowBinding{root/"definitions.jsonl",n+1,k[n],identity,str(row,"original_row_sha256"),native.contractSha256()}).second,"DUPLICATE_IDENTITY");++n;
        }
        need(n==96&&registry.paths_.size()==96,"CLOSED_NATIVE_96");std::set<std::string> found;
        for(const auto& entry:fs::directory_iterator(root)){need(!entry.is_symlink()&&entry.is_regular_file(),"FLAT_PACKAGE_ONLY");need(found.insert(entry.path().filename().generic_string()).second,"DUPLICATE_FILE");}
        need(found==expectedFiles&&expectedFiles.size()==3&&f(manifest,"package_files")==V(V::Array{"manifest.json","definitions.jsonl","family-closure.json"}),"EXACT_PACKAGE_FILE_SET");registry.ready_=true;
    } catch(const std::exception& e){registry.ready_=false;registry.paths_.clear();registry.error_=e.what();}
    return registry;
}
bool InstalledManualCurriculumRegistry::contains(const std::string& key) const noexcept {return ready_&&paths_.count(key)==1;}
std::optional<Definition> InstalledManualCurriculumRegistry::definition(const std::string& key) const {if(!contains(key))return std::nullopt;return manual_curriculum::definition(key);}
std::optional<fs::path> InstalledManualCurriculumRegistry::installedDefinitionPath(const std::string& key) const {if(!contains(key))return std::nullopt;return paths_.at(key).bulkDefinitionsPath;}
std::optional<InstalledRowBinding> InstalledManualCurriculumRegistry::rowBinding(const std::string& key) const {if(!contains(key))return std::nullopt;return paths_.at(key);}
} // namespace fathom::tasks::manual_curriculum
