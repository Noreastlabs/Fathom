#include "tasks/InstalledExtraSource17Registry.hpp"
#include "content/Canonical.hpp"
#include "GeneratedExtraSource17PackageBinding.hpp"
#include <set>
#include <sstream>
namespace fathom::tasks::extra_source17 {
namespace {
using V=json::Value; namespace fs=std::filesystem;
void need(bool v,const char* why){if(!v)throw std::runtime_error(why);}
const V& f(const V& v,const char* k){need(v.find(k)!=nullptr,"EXTRA_PACKAGE_FIELDS");return *v.find(k);}
std::string str(const V& v,const char* k){need(f(v,k).isString(),"EXTRA_PACKAGE_TEXT");return f(v,k).string();}
fs::path root(const fs::path& p){const auto a=fs::absolute(p).lexically_normal();need(fs::is_directory(a)&&!fs::is_symlink(fs::symlink_status(a))&&fs::canonical(a)==a,"EXTRA_PACKAGE_REAL_ROOT");return a;}
fs::path file(const fs::path& p,const std::string& name){const fs::path relative(name);need(!name.empty()&&!relative.is_absolute()&&relative.generic_string()==name,"EXTRA_PACKAGE_RELATIVE_PATH");auto target=p;for(const auto& part:relative){need(part!="."&&part!=".."&&!part.empty(),"EXTRA_PACKAGE_COMPONENT");target/=part;need(!fs::is_symlink(fs::symlink_status(target)),"EXTRA_PACKAGE_SYMLINK");}need(fs::is_regular_file(target),"EXTRA_PACKAGE_REGULAR_FILE");return target;}
std::string read(const fs::path& p,const std::string& name,std::size_t limit){return content::readBounded(file(p,name),limit);}
void pin(const V& expected,const std::string& bytes){std::int64_t n{};need(f(expected,"bytes").integer(n)&&n>=0&&static_cast<std::size_t>(n)==bytes.size()&&str(expected,"sha256")==content::sha256(bytes),"EXTRA_PACKAGE_PIN");}
}
InstalledExtraSource17Registry InstalledExtraSource17Registry::load(const fs::path& package,const fs::path& host){
    InstalledExtraSource17Registry result;
    try {
        const auto p=root(package),h=root(host);
        const auto manifestBytes=read(p,"manifest.json",65536);need(content::sha256(manifestBytes)==extra_source17_package_binding::manifestSha,"EXACT_EXTRA_PACKAGE_MANIFEST");
        const auto manifest=json::parse(manifestBytes);
        need(str(manifest,"schema")=="fathom.extra-source17-manual-package.1"&&f(manifest,"rows")==V::fromInteger(17)&&f(manifest,"qualified")==V::fromInteger(13)&&f(manifest,"reference_only")==V::fromInteger(4)&&f(manifest,"official_children")==V::fromInteger(0),"EXACT_EXTRA_PACKAGE_SCOPE");
        const auto bulk=read(p,"definitions.jsonl",2*1024*1024),ctx=read(p,"contexts.json",2*1024*1024);
        need(content::sha256(bulk)==extra_source17_package_binding::definitionsSha&&content::sha256(ctx)==extra_source17_package_binding::contextsSha,"EXACT_EXTRA_PACKAGE_FILES");
        pin(f(manifest,"definitions"),bulk);pin(f(manifest,"contexts"),ctx);
        const auto contexts=json::parse(ctx);
        std::set<std::string> assets;
        for(const auto& asset:f(manifest,"source_assets").array()){const auto name=str(asset,"path");need(assets.insert(name).second,"EXACT_EXTRA_UNIQUE_ASSET");pin(asset,read(h,name,2*1024*1024));}
        need(assets.size()==16,"EXACT_EXTRA_ASSET_SCOPE");
        std::istringstream lines(bulk);std::string line;std::size_t index=0;std::map<std::string,std::string> identities;
        while(std::getline(lines,line)){
            need(!line.empty()&&index<17,"EXACT_EXTRA_BULK_COUNT");const auto row=json::parse(line);
            const auto key=str(row,"source_key");const auto& d=manual_procedure_graph::extraSourceDefinition(key);
            need(row==d.exportedDefinition()&&f(f(contexts,"original_records"),key.c_str())==d.retainedOriginalRecord()&&f(f(contexts,"source_contexts"),str(f(row,"context_ref"),"path").c_str())==d.retainedSourceContext(),"EXACT_EXTRA_NATIVE_SOURCE_JOIN");
            need(identities.emplace(d.sourceIdentity(),key).second,"EXACT_EXTRA_UNIQUE_IDENTITY");++index;
        }
        need(index==17&&identities.size()==17,"EXTRA_PACKAGE_ZERO_PARTIAL");std::set<std::string> files;
        for(const auto& entry:fs::directory_iterator(p)){need(!entry.is_symlink()&&entry.is_regular_file(),"EXTRA_PACKAGE_FLAT_FILES");files.insert(entry.path().filename().generic_string());}
        need(files==std::set<std::string>{"manifest.json","definitions.jsonl","contexts.json"},"EXTRA_PACKAGE_NO_EXTRA_FILES");
        result.identities_=std::move(identities);result.ready_=true;
    } catch(const std::exception& e){result.ready_=false;result.identities_.clear();result.error_=e.what();}
    return result;
}
bool InstalledExtraSource17Registry::containsSourceIdentity(const std::string& s)const noexcept{return ready_&&identities_.count(s)==1;}
std::optional<manual_procedure_graph::Definition> InstalledExtraSource17Registry::definitionForSourceIdentity(const std::string& s)const {if(!containsSourceIdentity(s))return {};return manual_procedure_graph::extraSourceDefinition(identities_.at(s));}
}
