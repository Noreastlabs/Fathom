#include "tasks/InstalledPiecewiseContactTaskRegistry.hpp"
#include "content/Canonical.hpp"
#include "GeneratedPiecewiseContactPackageBinding.hpp"
#include <fstream>
#include <set>
#include <sstream>

namespace fathom::tasks::piecewise_contacts {
namespace {
using J = json::Value;
namespace fs = std::filesystem;
void need(bool good, const char* message) { if (!good) throw std::runtime_error(message); }
const J& at(const J& obj, const char* name) {
    need(obj.isObject() && obj.find(name), "Piecewise contact package field required"); return *obj.find(name);
}
std::string text(const J& obj, const char* name) {
    const auto& v = at(obj, name); need(v.isString(), "Piecewise contact package string required"); return v.string();
}
std::int64_t integer(const J& v) {
    std::int64_t n = 0; need(v.integer(n) && n >= 0, "Piecewise contact package unsigned integer required"); return n;
}
void shape(const J& obj, std::initializer_list<const char*> fields) {
    need(obj.isObject() && obj.object().size() == fields.size(), "Piecewise contact package exact schema required");
    for (const auto* field : fields) (void)at(obj, field);
}
fs::path realDirectory(const fs::path& input) {
    const auto path = fs::absolute(input).lexically_normal();
    need(fs::is_directory(path) && !fs::is_symlink(fs::symlink_status(path)) && fs::canonical(path) == path,
         "Piecewise contact package root must be an exact real directory");
    return path;
}
fs::path safeFile(const fs::path& root, const std::string& relative) {
    const fs::path path(relative);
    need(!relative.empty() && !path.is_absolute() && path.generic_string() == relative, "Piecewise contact relative file required");
    fs::path cursor = root;
    for (const auto& component : path) {
        need(component != "." && component != ".." && !component.empty(), "Piecewise contact unsafe path component");
        cursor /= component;
        need(!fs::is_symlink(fs::symlink_status(cursor)), "Piecewise contact source/package symlink refused");
    }
    need(fs::is_regular_file(cursor), "Piecewise contact regular file required"); return cursor;
}
std::string read(const fs::path& root, const std::string& path, std::size_t limit) {
    return content::readBounded(safeFile(root, path), limit);
}
void pin(const J& p, const std::string& raw) {
    shape(p, {"path", "bytes", "sha256"});
    need(static_cast<std::size_t>(integer(at(p, "bytes"))) == raw.size() && text(p, "sha256") == content::sha256(raw),
         "Piecewise contact file bytes/hash differ");
}
J rational(Rational q) { return J::Array{J::fromInteger(q.numerator()), J::fromInteger(q.denominator())}; }
}

InstalledPiecewiseContactTaskRegistry InstalledPiecewiseContactTaskRegistry::load(const fs::path& input,const fs::path& assetsInput){
 InstalledPiecewiseContactTaskRegistry result;
 try{
  const auto directory=realDirectory(input),assets=realDirectory(assetsInput);
  const auto raw=read(directory,"manifest.json",65536);
  need(content::sha256(raw)==package_binding::manifestSha,"Piecewise installed manifest differs");const auto manifest=json::parse(raw);
  shape(manifest,{"schema","family","scope","rows","contacts","source_policy_groups","runtime_candidate","runtime_admitted","practice_admitted","official_accepted","grants_credit","fixed_bpm","source_acoustic_gates","retained_midi_encoding","native_music_model","package_files","definitions","contexts","source_assets","version_bindings","resource_layout"});
  need(text(manifest,"schema")=="fathom.piecewise-contact-manual-package.1"&&text(manifest,"family")=="piecewise-contact"&&text(manifest,"scope")=="manual-guidance-candidate"&&integer(at(manifest,"rows"))==17&&integer(at(manifest,"contacts"))==432&&integer(at(manifest,"source_policy_groups"))==2,"Piecewise closed package scope");
  for(const auto* flag:{"runtime_admitted","practice_admitted","official_accepted","grants_credit"})need(at(manifest,flag)==J(false),"Piecewise manual/noncredit boundary");
  need(at(manifest,"runtime_candidate")==J(true)&&at(manifest,"fixed_bpm").null()&&at(manifest,"source_acoustic_gates").null()&&at(manifest,"retained_midi_encoding")==J("frozen model encoding; no printed octave labels")&&at(manifest,"native_music_model")==J(false),"Piecewise saved encoding and unknown sounding/clock boundary");
  const auto& versions=at(manifest,"version_bindings");
  need(versions==json::parse(package_binding::versionsJson)&&text(versions,"native_row_closure_sha256")==closureSha256(),"Piecewise compiled versions differ");
  const auto& defsPin=at(manifest,"definitions");const auto& contextPin=at(manifest,"contexts");
  need(text(defsPin,"path")=="definitions.jsonl"&&text(contextPin,"path")=="contexts.json","Piecewise fixed paths");
  const auto bulk=read(directory,"definitions.jsonl",1024*1024),contextRaw=read(directory,"contexts.json",1024*1024);pin(defsPin,bulk);pin(contextPin,contextRaw);
  const auto contexts=json::parse(contextRaw);shape(contexts,{"schema","source_contexts","source_packets"});
  need(text(contexts,"schema")=="fathom.piecewise-contact-shared-contexts.1"&&at(contexts,"source_contexts").isObject()&&at(contexts,"source_contexts").object().size()==2&&at(contexts,"source_packets").isArray()&&at(contexts,"source_packets").array().size()==2,"Piecewise exact two context/packet groups");
  std::map<std::string,std::size_t>packets;
  for(std::size_t i=0;i<2;++i){const auto&p=at(contexts,"source_packets").array()[i];shape(p,{"path","bytes","sha256"});need(packets.emplace(text(p,"path"),i).second,"Piecewise duplicate packet");}
  std::map<std::string,J>expectedAssets;
  for(const auto&entry:at(contexts,"source_contexts").object())for(const auto*kind:{"txt","pdf"}){const auto& asset=at(at(at(entry.second,"source_context"),"originals"),kind);shape(asset,{"path","bytes","sha256"});need(expectedAssets.emplace(text(asset,"path"),asset).second,"Piecewise duplicate source asset");}
  need(expectedAssets.size()==4&&at(manifest,"source_assets").isArray()&&at(manifest,"source_assets").array().size()==4,"Piecewise 4 host source assets");
  std::set<std::string>seenAssets;
  for(const auto&asset:at(manifest,"source_assets").array()){const auto path=text(asset,"path");need(expectedAssets.count(path)&&expectedAssets.at(path)==asset&&seenAssets.insert(path).second,"Piecewise source asset context join");const auto bytes=read(assets,path,1024*1024);++result.sourceFilesHashed_;pin(asset,bytes);}
  std::map<std::string,std::string>identities,reverse;std::istringstream lines(bulk);std::string line;std::size_t index=0,offset=0;
  while(std::getline(lines,line)){
   need(!line.empty()&&index<keys().size(),"Piecewise exact bulk count");const auto row=json::parse(line);
   shape(row,{"source_key","source_identity","record_canonical_sha256","source_packet","packet_line","level","native_contact_offset","contact_count","metric_end_q","source_policy","metadata_sha256","contract_sha256"});
   const auto&d=definition(keys()[index]);const auto policy=static_cast<std::size_t>(d.level()-34);const auto meta=d.trustedMetadataJson();
   need(packets.count(d.packetPath())&&at(at(contexts,"source_contexts"),std::to_string(d.level()).c_str())==json::parse(d.trustedContextJson()),"Piecewise exact native source policy/packet join");
   const auto packet=packets.at(d.packetPath());need(text(at(contexts,"source_packets").array()[packet],"sha256")==d.packetSha256(),"Piecewise exact source packet pin");
   J expected(J::Object{{"source_key",d.sourceKey()},{"source_identity",d.sourceIdentity()},{"record_canonical_sha256",d.sourceRecordSha256()},{"source_packet",J::fromInteger(static_cast<std::int64_t>(packet))},{"packet_line",J::fromInteger(d.packetLine())},{"level",J::fromInteger(d.level())},{"native_contact_offset",J::fromInteger(static_cast<std::int64_t>(offset))},{"contact_count",J::fromInteger(static_cast<std::int64_t>(d.contactCount()))},{"metric_end_q",rational(d.selectedMetricEnd())},{"source_policy",J::fromInteger(static_cast<std::int64_t>(policy))},{"metadata_sha256",content::sha256(meta)}});
   expected.object().emplace("contract_sha256",content::sha256(json::stringify(J::Object{{"row",expected},{"context",at(versions,"contract_context")}})));
   need(row==expected&&identities.emplace(d.sourceKey(),d.sourceIdentity()).second&&reverse.emplace(d.sourceIdentity(),d.sourceKey()).second,"Piecewise exact row/native contract and unique identity");offset+=d.contactCount();++index;
  }
  need(index==17&&offset==432&&identities.size()==17&&reverse.size()==17,"Piecewise zero partial family load");
  std::set<std::string>files;for(const auto&f:fs::directory_iterator(directory)){need(!f.is_symlink()&&f.is_regular_file(),"Piecewise flat package special file/directory");files.insert(f.path().filename().generic_string());}
  need(files==std::set<std::string>{"manifest.json","definitions.jsonl","contexts.json"}&&at(manifest,"package_files")==J(J::Array{J("manifest.json"),J("definitions.jsonl"),J("contexts.json")}),"Piecewise missing/extra package files");
  result.identities_=std::move(identities);result.keysByIdentity_=std::move(reverse);result.ready_=true;
 }catch(const std::exception&e){result.ready_=false;result.identities_.clear();result.keysByIdentity_.clear();result.error_=e.what();}
 return result;
}
bool InstalledPiecewiseContactTaskRegistry::containsSourceKey(const std::string&key)const noexcept{return ready_&&identities_.count(key)==1;}
bool InstalledPiecewiseContactTaskRegistry::containsSourceIdentity(const std::string&id)const noexcept{return ready_&&keysByIdentity_.count(id)==1;}
std::optional<Definition>InstalledPiecewiseContactTaskRegistry::definitionForSourceKey(const std::string&key)const{if(!containsSourceKey(key))return std::nullopt;return definition(key);}
std::optional<Definition>InstalledPiecewiseContactTaskRegistry::definitionForSourceIdentity(const std::string&id)const{if(!containsSourceIdentity(id))return std::nullopt;return definition(keysByIdentity_.at(id));}
std::unique_ptr<ordered_contacts::manual::Task>InstalledPiecewiseContactTaskRegistry::taskForSourceKey(const std::string&key)const{if(!containsSourceKey(key))return {};return std::make_unique<ordered_contacts::manual::Task>(manual_contacts::SourceHandle::piecewise(definition(key)));}
}
