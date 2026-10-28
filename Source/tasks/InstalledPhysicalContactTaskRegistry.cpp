#include "tasks/InstalledPhysicalContactTaskRegistry.hpp"
#include "content/Canonical.hpp"
#include "GeneratedPhysicalContactPackageBinding.hpp"
#include <fstream>
#include <set>
#include <sstream>

namespace fathom::tasks::physical_contacts {
namespace {
using J = json::Value;
namespace fs = std::filesystem;
void need(bool good, const char* message) { if (!good) throw std::runtime_error(message); }
const J& at(const J& obj, const char* name) {
    need(obj.isObject() && obj.find(name), "Physical contact package field required"); return *obj.find(name);
}
std::string text(const J& obj, const char* name) {
    const auto& v = at(obj, name); need(v.isString(), "Physical contact package string required"); return v.string();
}
std::int64_t integer(const J& v) {
    std::int64_t n = 0; need(v.integer(n) && n >= 0, "Physical contact package unsigned integer required"); return n;
}
void shape(const J& obj, std::initializer_list<const char*> fields) {
    need(obj.isObject() && obj.object().size() == fields.size(), "Physical contact package exact schema required");
    for (const auto* field : fields) (void)at(obj, field);
}
fs::path realDirectory(const fs::path& input) {
    const auto path = fs::absolute(input).lexically_normal();
    need(fs::is_directory(path) && !fs::is_symlink(fs::symlink_status(path)) && fs::canonical(path) == path,
         "Physical contact package root must be an exact real directory");
    return path;
}
fs::path safeFile(const fs::path& root, const std::string& relative) {
    const fs::path path(relative);
    need(!relative.empty() && !path.is_absolute() && path.generic_string() == relative, "Physical contact relative file required");
    fs::path cursor = root;
    for (const auto& component : path) {
        need(component != "." && component != ".." && !component.empty(), "Physical contact unsafe path component");
        cursor /= component;
        need(!fs::is_symlink(fs::symlink_status(cursor)), "Physical contact source/package symlink refused");
    }
    need(fs::is_regular_file(cursor), "Physical contact regular file required"); return cursor;
}
std::string read(const fs::path& root, const std::string& path, std::size_t limit) {
    return content::readBounded(safeFile(root, path), limit);
}
void pin(const J& p, const std::string& raw) {
    shape(p, {"path", "bytes", "sha256"});
    need(static_cast<std::size_t>(integer(at(p, "bytes"))) == raw.size() && text(p, "sha256") == content::sha256(raw),
         "Physical contact file bytes/hash differ");
}
J rational(Rational q) { return J::Array{J::fromInteger(q.numerator()), J::fromInteger(q.denominator())}; }
}

InstalledPhysicalContactTaskRegistry InstalledPhysicalContactTaskRegistry::load(const fs::path& input,const fs::path& assetsInput){
 InstalledPhysicalContactTaskRegistry result;
 try{
  const auto directory=realDirectory(input),assets=realDirectory(assetsInput);
  const auto raw=read(directory,"manifest.json",65536);
  need(content::sha256(raw)==package_binding::manifestSha,"Physical installed manifest differs");const auto manifest=json::parse(raw);
  shape(manifest,{"schema","family","scope","rows","contacts","source_policy_groups","runtime_candidate","runtime_admitted","practice_admitted","official_accepted","grants_credit","fixed_bpm","source_acoustic_gates","physical_pitch","package_files","definitions","contexts","source_assets","version_bindings","resource_layout"});
  need(text(manifest,"schema")=="fathom.physical-contact-manual-package.1"&&text(manifest,"family")=="physical-contact"&&text(manifest,"scope")=="manual-guidance-candidate"&&integer(at(manifest,"rows"))==339&&integer(at(manifest,"contacts"))==18906&&integer(at(manifest,"source_policy_groups"))==18,"Physical closed package scope");
  for(const auto* flag:{"runtime_admitted","practice_admitted","official_accepted","grants_credit"})need(at(manifest,flag)==J(false),"Physical manual/noncredit boundary");
  need(at(manifest,"runtime_candidate")==J(true)&&at(manifest,"fixed_bpm").null()&&at(manifest,"source_acoustic_gates").null()&&at(manifest,"physical_pitch").null(),"Physical unknown pitch/sounding/clock boundary");
  const auto& versions=at(manifest,"version_bindings");
  need(versions==json::parse(package_binding::versionsJson)&&text(versions,"native_row_closure_sha256")==closureSha256()&&text(versions,"cohort_sha256")==cohortSha256()&&text(versions,"manual_policy_closure_sha256")==ordered_contacts::manual::physicalPolicyClosureSha256(),"Physical compiled versions differ");
  const auto& defsPin=at(manifest,"definitions");const auto& contextPin=at(manifest,"contexts");
  need(text(defsPin,"path")=="definitions.jsonl"&&text(contextPin,"path")=="contexts.json","Physical fixed paths");
  const auto bulk=read(directory,"definitions.jsonl",1024*1024),contextRaw=read(directory,"contexts.json",1024*1024);pin(defsPin,bulk);pin(contextPin,contextRaw);
  const auto contexts=json::parse(contextRaw);shape(contexts,{"schema","source_policies","owner_policies","source_packets"});
  need(text(contexts,"schema")=="fathom.physical-contact-shared-contexts.1"&&at(contexts,"source_policies").isArray()&&at(contexts,"source_policies").array().size()==18&&at(contexts,"owner_policies").isArray()&&at(contexts,"owner_policies").array().size()==18&&at(contexts,"source_packets").isArray()&&at(contexts,"source_packets").array().size()==18,"Physical exact shared policy/packet groups");
  need(content::sha256(json::stringify(at(contexts,"owner_policies")))==ordered_contacts::manual::physicalPolicyClosureSha256(),"Physical complete compiled owner policies differ");
  std::map<std::string,std::size_t>packets;
  for(std::size_t i=0;i<18;++i){const auto&p=at(contexts,"source_packets").array()[i];shape(p,{"path","bytes","sha256"});need(packets.emplace(text(p,"path"),i).second,"Physical duplicate packet");}
  std::map<std::string,J>expectedAssets;
  for(const auto&p:at(contexts,"source_policies").array())for(const auto*kind:{"txt","pdf"}){const auto& asset=at(at(at(p,"source_context"),"originals"),kind);shape(asset,{"path","bytes","sha256"});need(expectedAssets.emplace(text(asset,"path"),asset).second,"Physical duplicate source asset");}
  need(expectedAssets.size()==36&&at(manifest,"source_assets").isArray()&&at(manifest,"source_assets").array().size()==36,"Physical 36 host source assets");
  std::set<std::string>seenAssets;
  for(const auto&asset:at(manifest,"source_assets").array()){const auto path=text(asset,"path");need(expectedAssets.count(path)&&expectedAssets.at(path)==asset&&seenAssets.insert(path).second,"Physical source asset context join");const auto bytes=read(assets,path,1024*1024);++result.sourceFilesHashed_;pin(asset,bytes);}
  std::map<std::string,std::string>identities,reverse;std::istringstream lines(bulk);std::string line;std::size_t index=0,offset=0;
  while(std::getline(lines,line)){
   need(!line.empty()&&index<keys().size(),"Physical exact bulk count");const auto row=json::parse(line);
   shape(row,{"source_key","source_identity","record_canonical_sha256","source_packet","packet_line","level","native_contact_offset","contact_count","metric_end_q","source_policy","metadata_sha256","contract_sha256"});
   const auto&d=definition(keys()[index]);const auto policy=static_cast<std::size_t>(d.level()-16);const auto meta=d.trustedMetadataJson();
   need(packets.count(d.packetPath())&&at(contexts,"source_policies").array()[policy]==json::parse(d.trustedSourcePolicyJson()),"Physical exact native source policy/packet join");
   const auto packet=packets.at(d.packetPath());need(text(at(contexts,"source_packets").array()[packet],"sha256")==d.packetSha256(),"Physical exact source packet pin");
   J expected(J::Object{{"source_key",d.sourceKey()},{"source_identity",d.sourceIdentity()},{"record_canonical_sha256",d.sourceRecordSha256()},{"source_packet",J::fromInteger(static_cast<std::int64_t>(packet))},{"packet_line",J::fromInteger(d.packetLine())},{"level",J::fromInteger(d.level())},{"native_contact_offset",J::fromInteger(static_cast<std::int64_t>(offset))},{"contact_count",J::fromInteger(static_cast<std::int64_t>(d.contactCount()))},{"metric_end_q",rational(d.selectedMetricEnd())},{"source_policy",J::fromInteger(static_cast<std::int64_t>(policy))},{"metadata_sha256",content::sha256(meta)}});
   expected.object().emplace("contract_sha256",content::sha256(json::stringify(J::Object{{"row",expected},{"context",at(versions,"contract_context")}})));
   need(row==expected&&identities.emplace(d.sourceKey(),d.sourceIdentity()).second&&reverse.emplace(d.sourceIdentity(),d.sourceKey()).second,"Physical exact row/native contract and unique identity");offset+=d.contactCount();++index;
  }
  need(index==339&&offset==18906&&identities.size()==339&&reverse.size()==339,"Physical zero partial family load");
  std::set<std::string>files;for(const auto&f:fs::directory_iterator(directory)){need(!f.is_symlink()&&f.is_regular_file(),"Physical flat package special file/directory");files.insert(f.path().filename().generic_string());}
  need(files==std::set<std::string>{"manifest.json","definitions.jsonl","contexts.json"}&&at(manifest,"package_files")==J(J::Array{J("manifest.json"),J("definitions.jsonl"),J("contexts.json")}),"Physical missing/extra package files");
  result.identities_=std::move(identities);result.keysByIdentity_=std::move(reverse);result.ready_=true;
 }catch(const std::exception&e){result.ready_=false;result.identities_.clear();result.keysByIdentity_.clear();result.error_=e.what();}
 return result;
}
bool InstalledPhysicalContactTaskRegistry::containsSourceKey(const std::string&key)const noexcept{return ready_&&identities_.count(key)==1;}
bool InstalledPhysicalContactTaskRegistry::containsSourceIdentity(const std::string&id)const noexcept{return ready_&&keysByIdentity_.count(id)==1;}
std::optional<Definition>InstalledPhysicalContactTaskRegistry::definitionForSourceKey(const std::string&key)const{if(!containsSourceKey(key))return std::nullopt;return definition(key);}
std::optional<Definition>InstalledPhysicalContactTaskRegistry::definitionForSourceIdentity(const std::string&id)const{if(!containsSourceIdentity(id))return std::nullopt;return definition(keysByIdentity_.at(id));}
std::unique_ptr<ordered_contacts::manual::Task>InstalledPhysicalContactTaskRegistry::taskForSourceKey(const std::string&key)const{if(!containsSourceKey(key))return {};return std::make_unique<ordered_contacts::manual::Task>(manual_contacts::SourceHandle::physical(definition(key)));}
}
