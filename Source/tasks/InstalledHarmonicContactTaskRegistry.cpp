#include "tasks/InstalledHarmonicContactTaskRegistry.hpp"
#include "content/Canonical.hpp"
#include "GeneratedHarmonicContactPackageBinding.hpp"
#include <set>
#include <sstream>
#include <stdexcept>

namespace fathom::tasks::harmonic_contacts {
namespace {
using J=json::Value;namespace fs=std::filesystem;
void need(bool value,const char* why){if(!value)throw std::runtime_error(why);}
const J& at(const J& value,const char* key){need(value.isObject()&&value.find(key),"HARMONIC_PACKAGE_FIELD");return *value.find(key);}
std::string string(const J& value,const char* key){const auto& x=at(value,key);need(x.isString(),"HARMONIC_PACKAGE_STRING");return x.string();}
std::size_t number(const J& value){std::int64_t n{};need(value.integer(n)&&n>=0,"HARMONIC_PACKAGE_INTEGER");return static_cast<std::size_t>(n);}
void shape(const J& value,std::initializer_list<const char*> fields){need(value.isObject()&&value.object().size()==fields.size(),"HARMONIC_PACKAGE_SCHEMA");for(const auto* key:fields)(void)at(value,key);}
fs::path directory(const fs::path& path){const auto exact=fs::absolute(path).lexically_normal();need(fs::is_directory(exact)&&!fs::is_symlink(fs::symlink_status(exact))&&fs::canonical(exact)==exact,"HARMONIC_PACKAGE_REAL_ROOT");return exact;}
fs::path file(const fs::path& root,const std::string& name){const fs::path relative(name);need(!name.empty()&&!relative.is_absolute()&&relative.generic_string()==name,"HARMONIC_PACKAGE_RELATIVE_PATH");auto cursor=root;for(const auto& part:relative){need(!part.empty()&&part!="."&&part!="..","HARMONIC_PACKAGE_PATH_COMPONENT");cursor/=part;need(!fs::is_symlink(fs::symlink_status(cursor)),"HARMONIC_PACKAGE_SYMLINK");}need(fs::is_regular_file(cursor),"HARMONIC_PACKAGE_REGULAR_FILE");return cursor;}
std::string read(const fs::path& root,const std::string& name,std::size_t limit){return content::readBounded(file(root,name),limit);}
void pin(const J& pin,const std::string& bytes){shape(pin,{"path","bytes","sha256"});need(number(at(pin,"bytes"))==bytes.size()&&string(pin,"sha256")==content::sha256(bytes),"HARMONIC_PACKAGE_FILE_HASH_BYTES");}
}
InstalledHarmonicContactTaskRegistry InstalledHarmonicContactTaskRegistry::load(const fs::path& package,const fs::path& host){
 InstalledHarmonicContactTaskRegistry result;
 try{
  const auto root=directory(package),assets=directory(host);const auto manifestRaw=read(root,"manifest.json",65536);need(content::sha256(manifestRaw)==package_binding::manifestSha,"HARMONIC_PACKAGE_MANIFEST_PIN");const auto manifest=json::parse(manifestRaw);
  shape(manifest,{"schema","family","rows","contacts","source_contexts","owner_bridge_ready","runtime_admitted","practice_admitted","official_accepted","grants_credit","source_clock","source_acoustic_gates","native_music_model","definitions","contexts","source_assets","versions","package_files","resource_layout"});
  need(string(manifest,"schema")=="fathom.harmonic-contact-manual-package.1"&&string(manifest,"family")=="harmonic-contact"&&number(at(manifest,"rows"))==118&&number(at(manifest,"contacts"))==1510&&number(at(manifest,"source_contexts"))==3,"HARMONIC_PACKAGE_CLOSED118");
  for(const auto* flag:{"runtime_admitted","practice_admitted","official_accepted","grants_credit","native_music_model"})need(at(manifest,flag)==J(false),"HARMONIC_PACKAGE_NO_ADMISSION");need(at(manifest,"source_clock").null()&&at(manifest,"source_acoustic_gates").null(),"HARMONIC_PACKAGE_UNKNOWN_CLOCK_GATE");
  need(at(manifest,"versions")==json::parse(package_binding::versionsJson)&&string(at(manifest,"versions"),"native_row_closure_sha256")==closureSha256(),"HARMONIC_PACKAGE_CODE_SOURCE_VERSION");
  need(string(at(manifest,"definitions"),"path")=="definitions.jsonl"&&string(at(manifest,"contexts"),"path")=="contexts.json","HARMONIC_PACKAGE_CLOSED_PATHS");
  const auto bulk=read(root,"definitions.jsonl",1024*1024),contextsRaw=read(root,"contexts.json",1024*1024);pin(at(manifest,"definitions"),bulk);pin(at(manifest,"contexts"),contextsRaw);const auto contexts=json::parse(contextsRaw);
  shape(contexts,{"schema","source_contexts","source_packets"});need(at(contexts,"schema")==J("fathom.harmonic-contact-package-contexts.1")&&at(contexts,"source_contexts").isObject()&&at(contexts,"source_contexts").object().size()==3,"HARMONIC_PACKAGE_THREE_CONTEXTS");
  std::map<std::string,J> sourceAssets;std::map<std::string,std::size_t> packets;
  for(const auto& context:at(contexts,"source_contexts").object())for(const auto* kind:{"pdf","txt"}){const auto& asset=at(at(at(context.second,"source_context"),"originals"),kind);shape(asset,{"path","bytes","sha256"});need(sourceAssets.emplace(string(asset,"path"),asset).second,"HARMONIC_PACKAGE_UNIQUE_SOURCE_ASSET");}
  const auto& packetList=at(contexts,"source_packets").array();need(packetList.size()==3&&sourceAssets.size()==6,"HARMONIC_PACKAGE_CLOSED_SIX_ASSETS_THREE_PACKETS");for(std::size_t n=0;n<packetList.size();++n){shape(packetList[n],{"path","bytes","sha256"});need(packets.emplace(string(packetList[n],"path"),n).second,"HARMONIC_PACKAGE_UNIQUE_PACKET");}
  std::set<std::string> assetSeen;need(at(manifest,"source_assets").isArray()&&at(manifest,"source_assets").array().size()==6,"HARMONIC_PACKAGE_EXACT_SOURCE_ASSETS");
  for(const auto& asset:at(manifest,"source_assets").array()){const auto path=string(asset,"path");need(sourceAssets.count(path)&&sourceAssets.at(path)==asset&&assetSeen.insert(path).second,"HARMONIC_PACKAGE_SOURCE_CONTEXT_JOIN");const auto bytes=read(assets,path,1024*1024);++result.sourceFilesHashed_;pin(asset,bytes);}
  std::map<std::string,std::string> byKey,byIdentity;std::istringstream lines(bulk);std::string line;std::size_t index=0,offset=0;
  while(std::getline(lines,line)){
   need(!line.empty()&&index<keys().size(),"HARMONIC_PACKAGE_BULK_COUNT");const auto actual=json::parse(line);const auto& definition=harmonic_contacts::definition(keys()[index]);const auto meta=json::parse(definition.trustedMetadataJson());
   need(packets.count(definition.packetPath())&&at(at(contexts,"source_contexts"),std::to_string(definition.level()).c_str())==json::parse(definition.trustedContextJson()),"HARMONIC_PACKAGE_NATIVE_CONTEXT_JOIN");
   const auto packetIndex=packets.at(definition.packetPath());need(string(packetList[packetIndex],"sha256")==definition.packetSha256(),"HARMONIC_PACKAGE_PACKET_PIN");
   J expected=J::Object{{"source_key",definition.sourceKey()},{"source_identity",definition.sourceIdentity()},{"source_record_sha256",definition.sourceRecordSha256()},{"source_packet",J::fromInteger(static_cast<std::int64_t>(packetIndex))},{"packet_line",J::fromInteger(definition.packetLine())},{"level",J::fromInteger(definition.level())},{"contact_offset",J::fromInteger(static_cast<std::int64_t>(offset))},{"contact_count",J::fromInteger(static_cast<std::int64_t>(definition.contactCount()))},{"compiled_definition_sha256",at(meta,"compiled_definition_sha256")},{"source_program_sha256",content::sha256(definition.sourceProgramJson())},{"contract_sha256",at(meta,"contract_sha256")}};
   expected.object().emplace("package_binding_sha256",content::sha256(json::stringify(J::Object{{"row",expected},{"versions",at(manifest,"versions")}})));
   need(actual==expected&&byKey.emplace(definition.sourceKey(),definition.sourceIdentity()).second&&byIdentity.emplace(definition.sourceIdentity(),definition.sourceKey()).second,"HARMONIC_PACKAGE_EXACT_DEFINITION_CONTRACT");++index;offset+=definition.contactCount();
  }
  need(index==118&&offset==1510&&byKey.size()==118&&byIdentity.size()==118,"HARMONIC_PACKAGE_ZERO_PARTIAL_LOAD");std::set<std::string> files;
  for(const auto& entry:fs::directory_iterator(root)){need(!entry.is_symlink()&&entry.is_regular_file(),"HARMONIC_PACKAGE_FLAT_REGULAR_FILES");files.insert(entry.path().filename().generic_string());}
  need(files==std::set<std::string>{"manifest.json","definitions.jsonl","contexts.json"}&&at(manifest,"package_files")==J(J::Array{"manifest.json","definitions.jsonl","contexts.json"}),"HARMONIC_PACKAGE_NO_EXTRA_FILES");
  need(at(manifest,"owner_bridge_ready").isBool(),"HARMONIC_PACKAGE_OWNER_READY_TYPE");result.ownerBridgeReady_=at(manifest,"owner_bridge_ready").boolean();result.keys_=std::move(byKey);result.identities_=std::move(byIdentity);result.ready_=true;
 }catch(const std::exception& error){result.ready_=false;result.ownerBridgeReady_=false;result.keys_.clear();result.identities_.clear();result.error_=error.what();}
 return result;
}
bool InstalledHarmonicContactTaskRegistry::containsSourceKey(const std::string& key)const noexcept{return ready_&&keys_.count(key)==1;}
bool InstalledHarmonicContactTaskRegistry::containsSourceIdentity(const std::string& identity)const noexcept{return ready_&&identities_.count(identity)==1;}
std::optional<Definition> InstalledHarmonicContactTaskRegistry::definitionForSourceKey(const std::string& key)const{if(!containsSourceKey(key))return {};return definition(key);}
std::optional<Definition> InstalledHarmonicContactTaskRegistry::definitionForSourceIdentity(const std::string& identity)const{if(!containsSourceIdentity(identity))return {};return definition(identities_.at(identity));}
}
