#include "tasks/InstalledPiecewiseContactTaskRegistry.hpp"
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
std::string sha256(const std::string& raw) {
    if (raw.size() > std::numeric_limits<CC_LONG>::max()) throw std::runtime_error("Hash size");
    std::array<unsigned char,CC_SHA256_DIGEST_LENGTH> bytes{};
    CC_SHA256(raw.data(),static_cast<CC_LONG>(raw.size()),bytes.data());
    std::ostringstream out; for (const auto byte:bytes) out<<std::hex<<std::setw(2)<<std::setfill('0')<<static_cast<int>(byte);
    return out.str();
}
std::string readBounded(const std::filesystem::path& path,std::size_t limit) {
    if (!std::filesystem::is_regular_file(path)) throw std::runtime_error("Regular file required");
    std::ifstream input(path,std::ios::binary); if (!input) throw std::runtime_error("File unavailable");
    std::string out; char buffer[65536];
    while (input) {
        input.read(buffer,sizeof(buffer)); const auto n=static_cast<std::size_t>(input.gcount());
        if (n>limit-out.size()) throw std::runtime_error("File exceeds bound"); out.append(buffer,n);
    }
    if (!input.eof()) throw std::runtime_error("Read failed"); return out;
}
}
namespace {
namespace fs=std::filesystem;namespace P=fathom::tasks::piecewise_contacts;namespace S=fathom::tasks::manual_contacts;namespace M=fathom::tasks::ordered_contacts::manual;
using Registry=P::InstalledPiecewiseContactTaskRegistry;using J=fathom::json::Value;
std::size_t checks=0,refusals=0;
void check(bool c,const char*why){++checks;if(!c)throw std::runtime_error(why);}
void write(const fs::path&p,const std::string&b){fs::create_directories(p.parent_path());std::ofstream o(p,std::ios::binary);o<<b;check(o.good(),"write fixture");}
void all(const Registry&r){check(r.size()==17&&r.error().empty()&&r.sourceFilesHashed()==4,"closed17 source verified");std::set<std::string>identities;
 for(const auto&key:P::keys()){const auto&d=P::definition(key);auto k=r.definitionForSourceKey(key),i=r.definitionForSourceIdentity(d.sourceIdentity());check(r.containsSourceKey(key)&&r.containsSourceIdentity(d.sourceIdentity())&&k&&i&&identities.insert(d.sourceIdentity()).second&&std::string(k->sourceRecordSha256())==d.sourceRecordSha256()&&std::string(i->sourceKey())==key,"all unique exact lookups");auto t=r.taskForSourceKey(key);check(t&&t->sourceHandle().family()==S::Family::PiecewiseContact&&std::string(t->sourceKey())==key&&t->sourcePolicy().level==d.level()&&t->sourcePolicy().family==S::Family::PiecewiseContact&&!t->view().reportedBpm&&!t->view().coverage.runtimeAdmitted,"all shared owner tagged policies");}
 check(!r.containsSourceKey("unknown")&&!r.definitionForSourceKey("unknown")&&!r.taskForSourceKey("unknown"),"unknown no route");
 for(const auto&key:fathom::tasks::ordered_contacts::keys())check(!r.containsSourceKey(key),"legacy scope excluded");for(const auto&key:fathom::tasks::physical_contacts::keys())check(!r.containsSourceKey(key),"physical scope excluded");
}
void negatives(const fs::path&root,const fs::path&package,const fs::path&assets){const auto out=root/"Build/manager-resume-r03/piecewise-contact-family-r01";const auto scratch=out/"guard-fixtures";const auto reset=[&]{fs::remove_all(scratch);fs::create_directories(scratch);for(const auto*name:{"manifest.json","definitions.jsonl","contexts.json"})fs::copy_file(package/name,scratch/name);};const auto reject=[&](const fs::path&p,const fs::path&a){auto r=Registry::load(p,a);check(r.size()==0&&!r.error().empty(),"bad package all zero");for(const auto&key:P::keys())check(!r.containsSourceKey(key)&&!r.definitionForSourceKey(key)&&!r.taskForSourceKey(key),"no partial grant");++refusals;return r;};
 const auto raw=fathom::content::readBounded(package/"manifest.json",65536);const auto original=fathom::json::parse(raw);
 for(const auto*name:{"runtime_admitted","practice_admitted","grants_credit"}){reset();auto m=original;m.object()[name]=J(true);write(scratch/"manifest.json",fathom::json::stringify(m));reject(scratch,assets);}
 reset();auto m=original;m.object()["definitions"].object()["path"]=J("../definitions.jsonl");write(scratch/"manifest.json",fathom::json::stringify(m));reject(scratch,assets);
 reset();m=original;m.object()["version_bindings"].object()["manual_owner_revision"]=J::fromInteger(999);write(scratch/"manifest.json",fathom::json::stringify(m));reject(scratch,assets);
 const auto rows=fathom::content::readBounded(package/"definitions.jsonl",1024*1024);for(const auto&b:{rows+rows.substr(0,rows.find('\n')+1),rows.substr(rows.find('\n')+1),std::string("{}\n")}){reset();write(scratch/"definitions.jsonl",b);reject(scratch,assets);}
 reset();write(scratch/"contexts.json","{}");reject(scratch,assets);
 reset();fs::remove(scratch/"contexts.json");reject(scratch,assets);
 reset();fs::remove(scratch/"definitions.jsonl");fs::create_symlink(package/"definitions.jsonl",scratch/"definitions.jsonl");reject(scratch,assets);
 reset();write(scratch/"extra.json","{}");reject(scratch,assets);reset();fs::create_directory(scratch/"extra");reject(scratch,assets);
 auto link=out/"root-link";fs::remove(link);fs::create_directory_symlink(package,link);reject(link,assets);fs::remove(link);
 const auto asset=original.object().at("source_assets").array().front();const auto path=asset.object().at("path").string();const auto source=out/"source-guard";fs::remove_all(source);fs::create_directories(source);auto bytes=fathom::content::readBounded(assets/path,1024*1024);bytes[0]^=1;write(source/path,bytes);auto bad=reject(package,source);check(bad.sourceFilesHashed()==1&&bad.error().find("bytes/hash")!=std::string::npos,"causal source byte hash refusal");fs::remove(source/path);fs::create_symlink(assets/path,source/path);bad=reject(package,source);check(bad.error().find("symlink")!=std::string::npos,"causal source symlink refusal");fs::remove_all(source);reject(package,source);fs::remove_all(scratch);
}
}
int main(int argc,char**argv){try{check(argc==4,"root/package/assets arguments");const fs::path root=argv[1],package=argv[2],assets=argv[3];auto r=Registry::load(package,assets);all(r);negatives(root,package,assets);std::cout<<"{\"result\":\"PASS\",\"rows\":17,\"source_assets\":4,\"assertions\":"<<checks<<",\"package_refusals\":"<<refusals<<",\"zero_partial_load\":true}\n";return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
