#include "content/CleanRuntimeEnvelope.hpp"
#include "content/CurriculumShardCatalog.hpp"
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>

namespace fathom::curriculum {
namespace {
using J=json::Value;
const J& at(const J& j,const std::string& key){return j.object().at(key);}
void require(bool condition,const std::string& message){if(!condition)throw std::runtime_error(message);}
std::int64_t integer(const J& j){std::int64_t value=0;require(j.integer(value),"Invalid shard count or size");return value;}
std::filesystem::path safeFile(const std::filesystem::path& root,const std::string& name){
    require(!name.empty()&&name.find('\\')==std::string::npos&&name.find('\0')==std::string::npos,"Unsafe shard asset name");
    const std::filesystem::path rel{name};require(!rel.is_absolute()&&!rel.has_root_name(),"Shard asset path must be relative");
    auto file=root;
    for(const auto& part:rel){
        require(part!="."&&part!=".."&&part!="","Unsafe shard asset component");
        file/=part;require(!std::filesystem::is_symlink(std::filesystem::symlink_status(file)),"Shard asset symlink refused");
    }
    require(std::filesystem::is_regular_file(file),"Missing shard asset: "+name);return file;
}
std::string exact(const std::filesystem::path& root,const std::string& name,std::int64_t size,const std::string& hash){
    require(size>=0&&size<=32*1024*1024,"Shard asset exceeds supported size");
    const auto bytes=content::readBounded(safeFile(root,name),static_cast<std::size_t>(size));
    require(bytes.size()==static_cast<std::size_t>(size)&&content::sha256(bytes)==hash,"Changed shard asset: "+name);
    return bytes;
}
} // namespace

ShardInventory discoverShards(const std::filesystem::path& installedResources){
    require(installedResources.is_absolute(),"Shard resources path must be absolute");
    auto current=std::filesystem::path{};
    for(const auto& part:installedResources){current/=part;require(!std::filesystem::is_symlink(std::filesystem::symlink_status(current)),"Shard resources root symlink refused");}
    require(std::filesystem::is_directory(installedResources),"Shard resources missing");
    const auto root=std::filesystem::canonical(installedResources);
    const auto transport=content::CleanRuntimeEnvelope::open(root,FATHOM_SHARD_HANDOFF_SHA,"handoff.json");
    const auto handoffBytes=content::readBounded(safeFile(root,"handoff.json"),1024*1024);
    require(content::sha256(handoffBytes)==FATHOM_SHARD_HANDOFF_SHA,"Unsupported or changed shard handoff");
    const auto handoff=json::parse(handoffBytes);
    require(at(handoff,"schema").string()=="fathom-four-shard-reader-handoff.1","Unsupported shard handoff version");
    require(at(handoff,"bundle_root").string()=="bundle","Unexpected shard bundle directory");
    require(at(at(handoff,"path_policy"),"external_references_remaining").array().empty(),"External shard reference refused");
    const auto bundle=root/"bundle";
    require(std::filesystem::is_directory(bundle)&&!std::filesystem::is_symlink(std::filesystem::symlink_status(bundle)),"Shard bundle missing or linked");
    const auto inventoryRef=at(handoff,"inventory");
    const auto inventoryBytes=exact(bundle,at(inventoryRef,"path").string(),
        static_cast<std::int64_t>(std::filesystem::file_size(safeFile(bundle,at(inventoryRef,"path").string()))),at(inventoryRef,"sha256").string());
    require(content::sha256(inventoryBytes)==FATHOM_SHARD_INVENTORY_SHA,"Unsupported shard inventory");
    const auto inventory=json::parse(inventoryBytes);
    require(at(inventory,"schema").string()=="fathom-four-shard-source-bundle.1"&&!at(inventory,"admitted").boolean()
        &&!at(inventory,"aggregate_complete").boolean()&&!at(inventory,"runtime_admission").boolean(),"Shard inventory exceeds discovery scope");
    const auto& files=at(inventory,"files").object();require(files.size()==65,"Unexpected shard file count");
    std::set<std::string> declared{"bundle-inventory.json"};
    for(const auto& [name,descriptor]:files){
        if(transport->hasArchivedEvidence("bundle/"+name)){
            const auto bytes=integer(at(descriptor,"bytes"));require(bytes>=0,"Archived shard byte identity invalid");
            transport->verifyArchivedEvidence("bundle/"+name,at(descriptor,"sha256").string(),static_cast<std::size_t>(bytes));
        }else{
            require(declared.insert(name).second,"Duplicate shard path");
            exact(bundle,name,integer(at(descriptor,"bytes")),at(descriptor,"sha256").string());
        }
    }
    std::set<std::string> actual;
    for(const auto& entry:std::filesystem::recursive_directory_iterator(bundle)){
        require(!entry.is_symlink(),"Shard bundle symlink refused");
        if(entry.is_regular_file())actual.insert(entry.path().lexically_relative(bundle).generic_string());
        else require(entry.is_directory(),"Unexpected shard bundle entry");
    }
    require(actual==declared,"Shard bundle file set differs from sealed inventory");
    const auto& manifestRef=at(handoff,"manifest");
    const auto manifestBytes=exact(bundle,at(manifestRef,"path").string(),integer(at(manifestRef,"bytes")),at(manifestRef,"sha256").string());
    require(content::sha256(manifestBytes)==FATHOM_SHARD_MANIFEST_SHA,"Unsupported shard manifest");
    const auto manifest=json::parse(manifestBytes);
    require(at(manifest,"schema").string()=="global-curriculum-shard-manifest.1"&&!at(manifest,"admitted").boolean()
        &&!at(manifest,"aggregate_complete").boolean(),"Shard manifest exceeds discovery scope");
    const auto& shards=at(handoff,"shards").array();require(shards.size()==4&&at(manifest,"shards").array().size()==4,"Expected exactly four source shards");
    std::set<std::int64_t> levels;
    for(const auto& shard:shards){
        const auto level=integer(at(shard,"legacy_level"));require(levels.insert(level).second,"Duplicate shard level");
        const auto& artifacts=at(shard,"artifacts");
        for(const auto* key:{"package","registry","profile","native_report"}){
            const auto& ref=at(artifacts,key);const auto& name=at(ref,"path").string();
            require(at(files.at(name),"sha256").string()==at(ref,"sha256").string(),"Shard handoff and inventory differ");
        }
        // Historical native-report identity is retained in compiled-pinned
        // archived metadata; its omitted report body is not claimed to be read.
    }
    require(levels==std::set<std::int64_t>{7,8,10,11},"Unexpected source shard levels");
    const auto summary=json::parse(content::readBounded(safeFile(bundle,"Build/parallel-02/four-real-shard-manifest-r01/summary.json"),1024*1024));
    require(!at(summary,"admitted").boolean()&&!at(summary,"aggregate_complete").boolean()&&!at(summary,"runtime_admission").boolean()
        &&integer(at(summary,"shard_count"))==4&&integer(at(at(summary,"new_counts"),"records"))==432,"Source shard summary changed");
    return {4,432};
}
} // namespace fathom::curriculum
