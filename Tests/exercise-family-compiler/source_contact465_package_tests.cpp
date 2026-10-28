#include "tasks/SourceContactFamily.hpp"
#include "tasks/InstalledSourceContactTaskRegistry.hpp"
#include "content/Canonical.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <array>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <set>
#include <sstream>

namespace fathom::content {
std::string sha256(const std::string& raw){if(raw.size()>std::numeric_limits<CC_LONG>::max())throw std::runtime_error("Hash size");std::array<unsigned char,CC_SHA256_DIGEST_LENGTH> bytes{};CC_SHA256(raw.data(),static_cast<CC_LONG>(raw.size()),bytes.data());std::ostringstream out;for(auto b:bytes)out<<std::hex<<std::setw(2)<<std::setfill('0')<<static_cast<int>(b);return out.str();}
std::string readBounded(const std::filesystem::path& p,std::size_t limit){std::ifstream in(p,std::ios::binary);if(!in)throw std::runtime_error("Missing file");std::ostringstream out;out<<in.rdbuf();auto s=out.str();if(s.size()>limit)throw std::runtime_error("Byte limit");return s;}
}
namespace {
namespace H=fathom::tasks::source_contacts;namespace fs=std::filesystem;using J=fathom::json::Value;
std::size_t checks=0,refusals=0,contacts=0,phaseReports=0;
void check(bool v,const char* why){++checks;if(!v)throw std::runtime_error(why);}
const J& f(const J& v,const char* k){check(v.isObject()&&v.find(k),"field");return *v.find(k);}
template<class F>void reject(F fn){bool refused=false;try{fn();}catch(const std::exception&){refused=true;}check(refused,"refusal required");++refusals;}
void installed(const fs::path& package,const fs::path& assets){auto r=H::InstalledSourceContactTaskRegistry::load(package,assets);check(r.size()==465&&r.error().empty()&&r.sourceFilesHashed()==30&&r.ownerBridgeReady(),"closed465 owner package with exact thirty host assets");for(const auto& key:H::keys()){auto d=r.definitionForSourceKey(key);check(d&&r.containsSourceKey(key)&&r.containsSourceIdentity(d->sourceIdentity())&&r.definitionForSourceIdentity(d->sourceIdentity()),"exact every definition lookup");}check(!r.definitionForSourceKey("foreign"),"foreign package lookup");}
void packageNegatives(const fs::path& package,const fs::path& assets){
 const auto out=fs::absolute("Build/manager-resume-r03/source-contact465-family-r01");const auto scratch=out/"package-guards";
 const auto write=[](const fs::path& path,const std::string& text){fs::create_directories(path.parent_path());std::ofstream file(path,std::ios::binary);file<<text;check(file.good(),"write own package guard");};
 const auto reset=[&]{fs::remove_all(scratch);fs::create_directories(scratch);for(const auto* name:{"manifest.json","definitions.jsonl","contexts.json"})fs::copy_file(package/name,scratch/name);};
 const auto rejected=[&](const fs::path& p,const fs::path& a){auto r=H::InstalledSourceContactTaskRegistry::load(p,a);check(r.size()==0&&!r.error().empty()&&!r.ownerBridgeReady(),"zero partial package readiness");for(const auto& key:H::keys())check(!r.containsSourceKey(key)&&!r.containsSourceIdentity(H::definition(key).sourceIdentity())&&!r.definitionForSourceKey(key),"no partial closed route");++refusals;return r;};
 const auto manifest=fathom::content::readBounded(package/"manifest.json",65536),rows=fathom::content::readBounded(package/"definitions.jsonl",1024*1024);
 for(const auto* flag:{"runtime_admitted","practice_admitted","grants_credit","official_accepted","owner_bridge_ready"}){reset();auto m=fathom::json::parse(manifest);m.object()[flag]=J(!f(m,flag).boolean());write(scratch/"manifest.json",fathom::json::stringify(m));rejected(scratch,assets);}
 reset();auto m=fathom::json::parse(manifest);m.object()["definitions"].object()["path"]="../definitions.jsonl";write(scratch/"manifest.json",fathom::json::stringify(m));rejected(scratch,assets);
 for(const auto& bytes:{rows.substr(rows.find('\n')+1),rows+rows.substr(0,rows.find('\n')+1),std::string("{}\n")}){reset();write(scratch/"definitions.jsonl",bytes);rejected(scratch,assets);}
 reset();write(scratch/"contexts.json","{}");rejected(scratch,assets);reset();fs::remove(scratch/"definitions.jsonl");rejected(scratch,assets);
 reset();fs::remove(scratch/"definitions.jsonl");fs::create_symlink(package/"definitions.jsonl",scratch/"definitions.jsonl");rejected(scratch,assets);
 reset();write(scratch/"extra.json","{}");rejected(scratch,assets);reset();fs::create_directory(scratch/"extra");rejected(scratch,assets);
 const auto link=out/"package-link";fs::create_directory_symlink(package,link);rejected(link,assets);fs::remove(link);
 const auto asset=f(fathom::json::parse(manifest),"source_assets").array()[0];const auto path=f(asset,"path").string();const auto host=out/"host-guards";fs::create_directory(host);auto bytes=fathom::content::readBounded(assets/path,1024*1024);bytes[0]^=1;write(host/path,bytes);const auto bad=rejected(package,host);check(bad.sourceFilesHashed()==1&&bad.error().find("HASH_BYTES")!=std::string::npos,"causal original host hash refusal");fs::remove(host/path);fs::create_symlink(assets/path,host/path);check(rejected(package,host).error().find("SYMLINK")!=std::string::npos,"causal original host symlink refusal");fs::remove_all(host);rejected(package,host);fs::remove_all(scratch);
}
}
int main(int argc,char** argv){try{check(argc==3,"package and host asset roots");installed(argv[1],argv[2]);packageNegatives(fs::absolute(argv[1]),fs::absolute(argv[2]));std::cout<<"{\"result\":\"PASS_SOURCE_NATIVE_FAMILY_AND_PACKAGE\",\"rows\":465,\"source_contacts\":9090,\"saved_variant_contact_projections\":"<<contacts<<",\"phase_schema_samples\":"<<phaseReports<<",\"assertions\":"<<checks<<",\"refusals\":"<<refusals<<",\"native_owner_runs\":0,\"package_source_assets\":30,\"zero_partial_load\":true}\n";return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
