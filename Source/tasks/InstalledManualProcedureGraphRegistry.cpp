#include "tasks/InstalledManualProcedureGraphRegistry.hpp"
#include <GeneratedCompiledPackageByteBounds.hpp>
#include <GeneratedHiddenSevenCarriers.hpp>
#include "content/Canonical.hpp"
#include <GeneratedManualProcedureGraphInstalledVersions.hpp>
#include <set>
#include <sstream>
#ifndef FATHOM_MANUAL_PROCEDURE_GRAPH_MANIFEST_SHA
#define FATHOM_MANUAL_PROCEDURE_GRAPH_MANIFEST_SHA manual_procedure_graph_installed_generated::manifestSha256
#endif
namespace fathom::tasks::manual_procedure_graph {
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
V versions() {return json::parse(manual_procedure_graph_installed_generated::versionsJson);}
V programCounts() {V::Object out;for(const auto& key:keys()){const auto n=str(manual_procedure_graph::definition(key).retainedProgram(),"name");auto& value=out[n];value=V::fromInteger(value.null()?1:static_cast<std::int64_t>(count(value)+1));}need(out.size()==manual_procedure_graph_installed_generated::programCount,"EXACT_PROGRAM_COUNT");return out;}
std::map<std::string,V> sourcePins() {
    std::map<std::string,V> out;
    for(const auto& key:keys())for(const auto& ref:f(manual_procedure_graph::definition(key).retainedOriginalRecord(),"source_refs").array()) {
        const auto p=str(ref,"path");if(p.rfind("Notes/",0)!=0)continue;V pin=V::Object{{"path",p},{"bytes",f(ref,"bytes")},{"sha256",f(ref,"sha256")}};
        const auto it=out.find(p);if(it==out.end())out.emplace(p,pin);else need(it->second==pin,"SOURCE_PIN_CONTRADICTION");
    }
    need(!out.empty(),"ORIGINALS_REQUIRED");return out;
}
}
InstalledManualProcedureGraphRegistry InstalledManualProcedureGraphRegistry::load(const fs::path& input,const fs::path& assetsInput) {
    InstalledManualProcedureGraphRegistry registry;
    try {
        const auto root=fs::absolute(input).lexically_normal();need(fs::is_directory(root)&&!fs::is_symlink(fs::symlink_status(root))&&fs::canonical(root)==root,"REAL_PACKAGE_ROOT");
        const auto assets=fs::absolute(assetsInput).lexically_normal();need(fs::is_directory(assets)&&!fs::is_symlink(fs::symlink_status(assets))&&fs::canonical(assets)==assets,"REAL_HOST_SOURCE_ASSETS_ROOT");
        std::set<std::string> expectedFiles{"manifest.json","definitions.jsonl","contexts.json"};const auto manifestBytes=read(root,"manifest.json",manual_procedure_graph_compiled_bounds::manifestBytes);need(content::sha256(manifestBytes)==FATHOM_MANUAL_PROCEDURE_GRAPH_MANIFEST_SHA&&std::string(FATHOM_MANUAL_PROCEDURE_GRAPH_MANIFEST_SHA)==manual_procedure_graph_installed_generated::manifestSha256,"COMPILED_MANIFEST_PIN");const auto manifest=json::parse(manifestBytes);
        shape(manifest,{"schema","family","scope","source_clock","source_tempo","runtime_candidate","runtime_admitted","practice_admitted","official_accepted","grants_credit","source_keys","program_counts","version_bindings","bulk_definitions","source_closure","package_files","source_assets","resource_layout"});
        need(str(manifest,"schema")=="fathom.compiled-recipe-family-package.1"&&str(manifest,"family")=="manual-procedure-graph"&&str(manifest,"scope")=="manual-guidance-candidate","PACKAGE_SCHEMA_SCOPE");
        need(f(manifest,"source_clock").null()&&f(manifest,"source_tempo").null()&&f(manifest,"runtime_candidate")==V(true)&&f(manifest,"runtime_admitted")==V(false)&&f(manifest,"practice_admitted")==V(false)&&f(manifest,"official_accepted")==V(false)&&f(manifest,"grants_credit")==V(false),"CANDIDATE_NO_ADMISSION");
        need(f(manifest,"resource_layout")==V(V::Object{{"package","compiled-recipe-families-v1/manual-procedure-graph"},{"source_assets","source-library/bundle/assets"}}),"HOST_RESOURCE_LAYOUT");
        const auto v=versions();need(f(manifest,"version_bindings")==v&&f(manifest,"program_counts")==programCounts(),"VERSION_OR_PROGRAM_DRIFT");
        const auto& k=keys();const auto& sourceKeys=f(manifest,"source_keys");const auto rowCount=manual_procedure_graph_installed_generated::rowCount;need(k.size()==rowCount&&sourceKeys.isArray()&&sourceKeys.array().size()==rowCount,"EXACT_COMPILED_SCOPE");for(std::size_t i=0;i<rowCount;++i)need(sourceKeys.array()[i]==V(k[i]),"EXACT_KEY_ORDER");
        const auto& bulkPin=f(manifest,"bulk_definitions");const auto& closurePin=f(manifest,"source_closure");need(str(bulkPin,"path")=="definitions.jsonl"&&str(closurePin,"path")=="contexts.json","FIXED_DATA_PATHS");
        const auto bulk=read(root,"definitions.jsonl",manual_procedure_graph_compiled_bounds::definitionsBytes);pinned(bulkPin,bulk);need(str(bulkPin,"sha256")==str(v,"definitions_sha256"),"BULK_VERSION");
        auto closureBytes=read(root,"contexts.json",manual_procedure_graph_compiled_bounds::contextsBytes);pinned(closurePin,closureBytes);need(str(closurePin,"sha256")==str(v,"contexts_sha256"),"CLOSURE_VERSION");
        json::Limits closureLimits;closureLimits.bytes=manual_procedure_graph_compiled_bounds::contextsBytes;closureLimits.values=manual_procedure_graph_compiled_bounds::contextsValues;const auto closure=json::parse(closureBytes,closureLimits);need(str(closure,"schema")=="fathom.manual-procedure-graph-contexts.1"&&f(closure,"bindings").array().size()==rowCount,"CLOSURE_SOURCE_SCOPE");
        const auto pins=sourcePins();const auto& originals=f(manifest,"source_assets");need(originals.isArray()&&originals.array().size()==pins.size(),"ORIGINAL_DENOMINATOR");std::set<std::string> seen;
        for(const auto& source:originals.array()) {
            shape(source,{"path","bytes","sha256"});const auto p=str(source,"path");need(pins.count(p)==1&&seen.insert(p).second&&source==pins.at(p),"ORIGINAL_SOURCE_PIN");const auto bytes=read(assets,p,512*1024);++registry.sourceFilesHashed_;need(bytes.size()==count(f(source,"bytes"))&&content::sha256(bytes)==str(source,"sha256"),"ORIGINAL_SOURCE_BYTES");
        }
        std::istringstream lines(bulk);std::string line;std::size_t n=0;
        while(std::getline(lines,line)) {
            need(!line.empty()&&n<rowCount,"BULK_DENOMINATOR");const auto row=json::parse(line);const auto& native=manual_procedure_graph::definition(k[n]);need(row==native.exportedDefinition(),"NATIVE_FULL_ROW_PARITY");
            const auto identity=str(row,"source_identity");const auto& reference=f(row,"context_ref");const auto contextRef=reference.isString()?reference.string():str(reference,"path");const auto* context=f(closure,"contexts").find(contextRef);need(context&&*context==native.retainedSourceContext(),"EXACT_CONTEXT_PARITY");
            need(str(row,"source_key")==k[n]&&str(row,"contract_sha256")==native.contractSha256()&&str(f(closure,"bindings").array()[n],"contract_sha256")==native.contractSha256()&&str(f(closure,"bindings").array()[n],"own_closure_sha256")==native.sourceClosureSha256()&&str(f(closure,"bindings").array()[n],"raw_export_sha256")==content::sha256(line),"EXACT_INSTALLED_CONTRACT");
            if(!row.find("original_record")){const auto& original=f(f(closure,"original_records"),k[n].c_str());need(original==native.retainedOriginalRecord(),"EXACT_REFERENCE_ORIGINAL_PARITY");}
            const auto& binding=f(closure,"bindings").array()[n];if(const auto* carrier=manual_procedure_graph_hidden_carriers::find(k[n])){need(binding==json::parse(carrier->binding)&&row==json::parse(carrier->row)&&native.retainedOriginalRecord()==json::parse(carrier->original),"EXACT_HIDDEN_SEVEN_SOURCE_CARRIER");}else need(!binding.find("source_protocol_carrier"),"CLOSED_SOURCE_CARRIER_SCOPE");
            need(registry.paths_.emplace(k[n],InstalledRowBinding{root/"definitions.jsonl",n+1,k[n],identity,str(row,"original_row_sha256"),native.contractSha256()}).second,"DUPLICATE_IDENTITY");need(registry.identities_.emplace(identity,k[n]).second,"DUPLICATE_SOURCE_IDENTITY");++n;
        }
        need(n==rowCount&&registry.paths_.size()==rowCount,"CLOSED_NATIVE_COMPILED_SCOPE");std::set<std::string> found;
        for(const auto& entry:fs::directory_iterator(root)){need(!entry.is_symlink()&&entry.is_regular_file(),"FLAT_PACKAGE_ONLY");need(found.insert(entry.path().filename().generic_string()).second,"DUPLICATE_FILE");}
        need(found==expectedFiles&&expectedFiles.size()==3&&f(manifest,"package_files")==V(V::Array{"manifest.json","definitions.jsonl","contexts.json"}),"EXACT_PACKAGE_FILE_SET");registry.ready_=true;
    } catch(const std::exception& e){registry.ready_=false;registry.paths_.clear();registry.identities_.clear();registry.error_=e.what();}
    return registry;
}
bool InstalledManualProcedureGraphRegistry::contains(const std::string& key) const noexcept {return ready_&&paths_.count(key)==1;}
std::optional<Definition> InstalledManualProcedureGraphRegistry::definition(const std::string& key) const {if(!contains(key))return std::nullopt;return manual_procedure_graph::definition(key);}
std::optional<fs::path> InstalledManualProcedureGraphRegistry::installedDefinitionPath(const std::string& key) const {if(!contains(key))return std::nullopt;return paths_.at(key).bulkDefinitionsPath;}
std::optional<InstalledRowBinding> InstalledManualProcedureGraphRegistry::rowBinding(const std::string& key) const {if(!contains(key))return std::nullopt;return paths_.at(key);}
bool InstalledManualProcedureGraphRegistry::containsSourceIdentity(const std::string& source) const noexcept{return ready_&&identities_.count(source)==1;}
std::optional<Definition> InstalledManualProcedureGraphRegistry::definitionForSourceIdentity(const std::string& source) const {if(!containsSourceIdentity(source))return std::nullopt;return definition(identities_.at(source));}
} // namespace fathom::tasks::manual_procedure_graph
