#include "tasks/InstalledSourceContactTaskRegistry.hpp"
#include "content/Canonical.hpp"
#include "GeneratedSourceContactPackageBinding.hpp"
#include <set>
#include <sstream>
#include <stdexcept>

namespace fathom::tasks::source_contacts {
namespace {
using J=json::Value;namespace fs=std::filesystem;
void need(bool value,const char* why){if(!value)throw std::runtime_error(why);}
const J& at(const J& value,const char* key){need(value.isObject()&&value.find(key),"SOURCE_CONTACT_PACKAGE_FIELD");return *value.find(key);}
std::string string(const J& value,const char* key){const auto& x=at(value,key);need(x.isString(),"SOURCE_CONTACT_PACKAGE_STRING");return x.string();}
std::size_t number(const J& value){std::int64_t n{};need(value.integer(n)&&n>=0,"SOURCE_CONTACT_PACKAGE_INTEGER");return static_cast<std::size_t>(n);}
void shape(const J& value,std::initializer_list<const char*> fields){need(value.isObject()&&value.object().size()==fields.size(),"SOURCE_CONTACT_PACKAGE_SCHEMA");for(const auto* key:fields)(void)at(value,key);}
fs::path directory(const fs::path& path){const auto exact=fs::absolute(path).lexically_normal();need(fs::is_directory(exact)&&!fs::is_symlink(fs::symlink_status(exact))&&fs::canonical(exact)==exact,"SOURCE_CONTACT_PACKAGE_REAL_ROOT");return exact;}
fs::path file(const fs::path& root,const std::string& name){const fs::path relative(name);need(!name.empty()&&!relative.is_absolute()&&relative.generic_string()==name,"SOURCE_CONTACT_PACKAGE_RELATIVE_PATH");auto cursor=root;for(const auto& part:relative){need(!part.empty()&&part!="."&&part!="..","SOURCE_CONTACT_PACKAGE_PATH_COMPONENT");cursor/=part;need(!fs::is_symlink(fs::symlink_status(cursor)),"SOURCE_CONTACT_PACKAGE_SYMLINK");}need(fs::is_regular_file(cursor),"SOURCE_CONTACT_PACKAGE_REGULAR_FILE");return cursor;}
std::string read(const fs::path& root,const std::string& name,std::size_t limit){return content::readBounded(file(root,name),limit);}
void pin(const J& pin,const std::string& bytes){shape(pin,{"path","bytes","sha256"});need(number(at(pin,"bytes"))==bytes.size()&&string(pin,"sha256")==content::sha256(bytes),"SOURCE_CONTACT_PACKAGE_FILE_HASH_BYTES");}
}
InstalledSourceContactTaskRegistry InstalledSourceContactTaskRegistry::load(const fs::path& package,const fs::path& host){
 InstalledSourceContactTaskRegistry result;
 try{
  const auto root=directory(package),assets=directory(host);const auto manifestRaw=read(root,"manifest.json",65536);need(content::sha256(manifestRaw)==package_binding::manifestSha,"SOURCE_CONTACT_PACKAGE_MANIFEST_PIN");const auto manifest=json::parse(manifestRaw);
  shape(manifest,{"schema","family","rows","contacts","source_contexts","owner_bridge_ready","runtime_admitted","practice_admitted","official_accepted","grants_credit","source_clock","source_acoustic_gates","native_music_model","definitions","contexts","source_assets","versions","package_files","resource_layout"});
  need(string(manifest,"schema")=="fathom.source-contact-manual-package.1"&&string(manifest,"family")=="source-contact-private664"&&number(at(manifest,"rows"))==664&&number(at(manifest,"contacts"))==package_binding::originalAtoms&&number(at(manifest,"source_contexts"))==package_binding::sourceContexts,"SOURCE_CONTACT_PACKAGE_CLOSED664");
  for(const auto* flag:{"runtime_admitted","practice_admitted","official_accepted","grants_credit","native_music_model"})need(at(manifest,flag)==J(false),"SOURCE_CONTACT_PACKAGE_NO_ADMISSION");need(at(manifest,"source_clock").null()&&at(manifest,"source_acoustic_gates").null(),"SOURCE_CONTACT_PACKAGE_UNKNOWN_CLOCK_GATE");
  need(at(manifest,"versions")==json::parse(package_binding::versionsJson)&&string(at(manifest,"versions"),"native_row_closure_sha256")==closureSha256(),"SOURCE_CONTACT_PACKAGE_CODE_SOURCE_VERSION");
  need(string(at(manifest,"definitions"),"path")=="definitions.jsonl"&&string(at(manifest,"contexts"),"path")=="contexts.json","SOURCE_CONTACT_PACKAGE_CLOSED_PATHS");
  const auto bulk=read(root,"definitions.jsonl",4*1024*1024),contextsRaw=read(root,"contexts.json",2*1024*1024);pin(at(manifest,"definitions"),bulk);pin(at(manifest,"contexts"),contextsRaw);const auto contexts=json::parse(contextsRaw);
  shape(contexts,{"schema","source_contexts","source_packets"});need(at(contexts,"schema")==J("fathom.source-contact-package-contexts.1")&&at(contexts,"source_contexts").isObject()&&at(contexts,"source_contexts").object().size()==package_binding::sourceContexts,"SOURCE_CONTACT_PACKAGE_THREE_CONTEXTS");
  std::map<std::string,J> sourceAssets;std::map<std::string,std::size_t> packets;
  const auto collectAssets=[&](const auto& self,const J& value)->void{
   if(value.isObject()){if(value.object().size()==3&&value.find("path")&&value.find("bytes")&&value.find("sha256")){
    const auto path=string(value,"path");if(path.size()>4&&(path.substr(path.size()-4)==".pdf"||path.substr(path.size()-4)==".txt")){const auto prior=sourceAssets.find(path);need(prior==sourceAssets.end()||prior->second==value,"SOURCE_CONTACT_PACKAGE_ASSET_CONFLICT");sourceAssets.emplace(path,value);}}
    else for(const auto& child:value.object())self(self,child.second);
   }else if(value.isArray())for(const auto& child:value.array())self(self,child);
  };collectAssets(collectAssets,at(contexts,"source_contexts"));
  const auto& packetList=at(contexts,"source_packets").array();need(packetList.size()==package_binding::sourcePackets&&sourceAssets.size()==package_binding::sourceAssets,"SOURCE_CONTACT_PACKAGE_EXACT_SOURCE_CUSTODY");for(std::size_t n=0;n<packetList.size();++n){shape(packetList[n],{"path","bytes","sha256"});need(packets.emplace(string(packetList[n],"path"),n).second,"SOURCE_CONTACT_PACKAGE_UNIQUE_PACKET");}
  std::set<std::string> assetSeen;need(at(manifest,"source_assets").isArray()&&at(manifest,"source_assets").array().size()==package_binding::sourceAssets,"SOURCE_CONTACT_PACKAGE_EXACT_SOURCE_ASSETS");
  for(const auto& asset:at(manifest,"source_assets").array()){const auto path=string(asset,"path");need(sourceAssets.count(path)&&sourceAssets.at(path)==asset&&assetSeen.insert(path).second,"SOURCE_CONTACT_PACKAGE_SOURCE_CONTEXT_JOIN");const auto bytes=read(assets,path,1024*1024);++result.sourceFilesHashed_;pin(asset,bytes);}
  std::map<std::string,std::string> byKey,byIdentity;std::istringstream lines(bulk);std::string line;std::size_t index=0,offset=0;
  while(std::getline(lines,line)){
   need(!line.empty()&&index<keys().size(),"SOURCE_CONTACT_PACKAGE_BULK_COUNT");const auto actual=json::parse(line);const auto& definition=source_contacts::definition(keys()[index]);const auto meta=json::parse(definition.trustedMetadataJson());
   need(packets.count(definition.packetPath())&&at(at(contexts,"source_contexts"),string(meta,"context_key").c_str())==json::parse(definition.trustedContextJson()),"SOURCE_CONTACT_PACKAGE_NATIVE_CONTEXT_JOIN");
   const auto packetIndex=packets.at(definition.packetPath());need(string(packetList[packetIndex],"sha256")==definition.packetSha256(),"SOURCE_CONTACT_PACKAGE_PACKET_PIN");
   J::Array routeContracts;for(std::size_t r=0;r<definition.routeCount();++r){const auto& route=at(meta,"routes").array()[r];routeContracts.emplace_back(J::Object{{"id",at(route,"id")},{"contact_count",J::fromInteger(static_cast<std::int64_t>(definition.contactCount(r)))},{"atom_count",J::fromInteger(static_cast<std::int64_t>(at(route,"atom_indices").array().size()))},{"program_sha256",content::sha256(definition.sourceProgramJson(r))}});}
   J expected=J::Object{{"source_key",definition.sourceKey()},{"source_identity",definition.sourceIdentity()},{"existing_parent_id",at(meta,"existing_parent_id")},{"source_record_sha256",definition.sourceRecordSha256()},{"source_packet",J::fromInteger(static_cast<std::int64_t>(packetIndex))},{"packet_line",J::fromInteger(definition.packetLine())},{"level",J::fromInteger(definition.level())},{"contact_offset",J::fromInteger(static_cast<std::int64_t>(offset))},{"contact_count",J::fromInteger(static_cast<std::int64_t>(definition.sourceAtomCount()))},{"compiled_definition_sha256",at(meta,"compiled_definition_sha256")},{"route_contracts",routeContracts},{"contract_sha256",at(meta,"contract_sha256")}};
   expected.object().emplace("package_binding_sha256",content::sha256(json::stringify(J::Object{{"row",expected},{"versions",at(manifest,"versions")}})));
   need(actual==expected&&byKey.emplace(definition.sourceKey(),definition.sourceIdentity()).second&&byIdentity.emplace(definition.sourceIdentity(),definition.sourceKey()).second,"SOURCE_CONTACT_PACKAGE_EXACT_DEFINITION_CONTRACT");++index;offset+=definition.sourceAtomCount();
  }
  need(index==664&&offset==package_binding::originalAtoms&&byKey.size()==664&&byIdentity.size()==664,"SOURCE_CONTACT_PACKAGE_ZERO_PARTIAL_LOAD");std::set<std::string> files;
  for(const auto& entry:fs::directory_iterator(root)){need(!entry.is_symlink()&&entry.is_regular_file(),"SOURCE_CONTACT_PACKAGE_FLAT_REGULAR_FILES");files.insert(entry.path().filename().generic_string());}
  need(files==std::set<std::string>{"manifest.json","definitions.jsonl","contexts.json"}&&at(manifest,"package_files")==J(J::Array{"manifest.json","definitions.jsonl","contexts.json"}),"SOURCE_CONTACT_PACKAGE_NO_EXTRA_FILES");
  need(at(manifest,"owner_bridge_ready").isBool(),"SOURCE_CONTACT_PACKAGE_OWNER_READY_TYPE");result.ownerBridgeReady_=at(manifest,"owner_bridge_ready").boolean();result.keys_=std::move(byKey);result.identities_=std::move(byIdentity);result.ready_=true;
 }catch(const std::exception& error){result.ready_=false;result.ownerBridgeReady_=false;result.keys_.clear();result.identities_.clear();result.error_=error.what();}
 return result;
}
bool InstalledSourceContactTaskRegistry::containsSourceKey(const std::string& key)const noexcept{return ready_&&keys_.count(key)==1;}
bool InstalledSourceContactTaskRegistry::containsSourceIdentity(const std::string& identity)const noexcept{return ready_&&identities_.count(identity)==1;}
std::optional<Definition> InstalledSourceContactTaskRegistry::definitionForSourceKey(const std::string& key)const{if(!containsSourceKey(key))return {};return definition(key);}
std::optional<Definition> InstalledSourceContactTaskRegistry::definitionForSourceIdentity(const std::string& identity)const{if(!containsSourceIdentity(identity))return {};return definition(identities_.at(identity));}
}
