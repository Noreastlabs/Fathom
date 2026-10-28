#include "tasks/HarmonicContactFamily.hpp"
#include "tasks/InstalledHarmonicContactTaskRegistry.hpp"
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
namespace H=fathom::tasks::harmonic_contacts;namespace fs=std::filesystem;using J=fathom::json::Value;
std::size_t checks=0,refusals=0,contacts=0,phaseReports=0;
void check(bool v,const char* why){++checks;if(!v)throw std::runtime_error(why);}
const J& f(const J& v,const char* k){check(v.isObject()&&v.find(k),"field");return *v.find(k);}
int number(const J& v){std::int64_t n{};check(v.integer(n),"integer");return static_cast<int>(n);}
template<class F>void reject(F fn){bool refused=false;try{fn();}catch(const std::exception&){refused=true;}check(refused,"refusal required");++refusals;}
J positive(const J& phase){J::Object r;for(const auto& prop:f(f(phase,"report_schema"),"properties").object())r.emplace(prop.first,prop.first=="evidence"?J("Synthetic manual source evidence"):prop.second.find("minimum")?J::fromInteger(number(f(prop.second,"minimum"))):J("reported_met"));return r;}
void sourceFamily(){
 check(H::keys().size()==118,"closed118");std::set<std::string> identities;std::size_t unknown=0,savedStarts=0,metric=0,roots=0,later=0,unspecifiedRows=0;
 for(const auto& key:H::keys()){
  const auto& d=H::definition(key);check(key==d.sourceKey()&&identities.insert(d.sourceIdentity()).second,"exact key/identity");const auto meta=fathom::json::parse(d.trustedMetadataJson());const auto atoms=fathom::json::parse(d.sourceAtomsJson());const auto program=fathom::json::parse(d.sourceProgramJson());
  check(d.contactCount()==atoms.array().size()&&f(meta,"source_record_canonical_sha256")==J(d.sourceRecordSha256()),"source record/count");check(f(program,"inherits_physical_tempo_rule")==J(false)&&f(program,"inherits_physical_frame_or_pick_debt")==J(false),"no old physical policies");
  auto starts=d.savedPickVariants();if(starts.empty()){starts={H::PickVariant::Unspecified};++unspecifiedRows;reject([&]{d.contact(1,H::PickVariant::Down);});reject([&]{d.contact(1,H::PickVariant::Up);});}else{savedStarts+=starts.size();reject([&]{d.contact(1,H::PickVariant::Unspecified);});}
  for(auto start:starts)for(std::size_t n=1;n<=d.contactCount();++n){const auto cue=d.contact(n,start);const auto& atom=atoms.array()[n-1];d.requireSourceParity(cue,start);++contacts;
   check(cue.ordinal==n&&cue.fret==number(f(atom,"fret"))&&cue.midi==number(f(atom,"midi"))&&cue.stringLowToHigh==number(f(atom,"string_low_to_high")),"all source physical/pitch fields");check(cue.stringLabel==f(atom,"string_label").string()&&cue.spelling==f(atom,"note_spelling").string()&&cue.annotationsJson==fathom::json::stringify(f(atom,"annotations")),"all saved spelling/annotation fields");
   check(!cue.acousticSoundingSpan,"all sounding unknown");check(bool(cue.finger)==!f(atom,"finger").null(),"optional printed finger");if(cue.finger)check(*cue.finger==number(f(atom,"finger")),"source finger");
   check(bool(cue.sourceMetricSpan)==!f(atom,"onset_q").null(),"source metric null parity");check(bool(cue.pick)==(start!=H::PickVariant::Unspecified),"absent pick remains absent");
   check(cue.blockIndex==number(f(atom,"block_index"))&&cue.gridColumn==number(f(atom,"grid_column"))&&cue.sourceLine==number(f(atom,"source_line"))&&cue.sourceColumn1Based==number(f(atom,"source_column_1based")),"all source locators");
   if(start==starts[0]){unknown+=!cue.finger;metric+=bool(cue.sourceMetricSpan);roots+=f(atom,"harmonic_role")==J("R");}
  }
  reject([&]{d.contact(0,starts[0]);});reject([&]{d.contact(d.contactCount()+1,starts[0]);});auto cue=d.contact(1,starts[0]);cue.finger=0;reject([&]{d.requireSourceParity(cue,starts[0]);});cue=d.contact(1,starts[0]);cue.acousticSoundingSpan=H::ManualSpan{fathom::Rational(0),fathom::Rational(1)};reject([&]{d.requireSourceParity(cue,starts[0]);});
  const auto& phases=f(program,"report_phases").array();for(std::size_t p=0;p<phases.size();++p){const auto& phase=phases[p];auto report=positive(phase);check(d.reportPhaseResolved(p,report),"source phase positive schema");++phaseReports;later+=f(phase,"id")==J("later_manual_slide_pass");
   for(const auto& prop:f(f(phase,"report_schema"),"properties").object()){
    auto bad=report;bad.object()[prop.first]=J(nullptr);check(!d.reportPhaseResolved(p,bad),"null report unresolved");if(prop.first!="evidence"){bad.object()[prop.first]=J("unknown");check(!d.reportPhaseResolved(p,bad),"unknown report unresolved");bad.object()[prop.first]=J("reported_not_met");check(!d.reportPhaseResolved(p,bad),"negative report unresolved");bad.object()[prop.first]=J(true);reject([&]{d.reportPhaseResolved(p,bad);});}
   }
   auto bad=report;bad.object()["evidence"]=J(" \t\r\n");check(!d.reportPhaseResolved(p,bad),"whitespace unresolved");bad.object()["evidence"]=J("\xc2\xa0\xe2\x80\x83");check(!d.reportPhaseResolved(p,bad),"Unicode whitespace unresolved via shared helper");bad.object()["foreign"]=J(true);reject([&]{d.reportPhaseResolved(p,bad);});
  }
  reject([&]{d.reportPhaseResolved(phases.size(),J::Object{});});
 }
 check(contacts==2044&&savedStarts==70&&unknown==1070&&metric==48&&roots==276&&later==3&&unspecifiedRows==83,"exact source/variant/unknown totals");reject([]{H::definition("foreign");});
 auto copy=H::definition(H::keys()[0]);const auto originalKey=std::string(copy.sourceKey());copy=H::definition(H::keys()[69]);check(std::string(copy.sourceKey())!=originalKey,"cheap handles own assigned value");
 const auto lifetime=[](){auto temporary=H::definition(H::keys()[0]);return temporary;}();check(std::string(lifetime.sourceKey())==H::keys()[0],"caller lifetime safe");
}
void installed(const fs::path& package,const fs::path& assets){auto r=H::InstalledHarmonicContactTaskRegistry::load(package,assets);check(r.size()==118&&r.error().empty()&&r.sourceFilesHashed()==6&&r.ownerBridgeReady(),"closed118 owner package with exact six host assets");for(const auto& key:H::keys()){auto d=r.definitionForSourceKey(key);check(d&&r.containsSourceKey(key)&&r.containsSourceIdentity(d->sourceIdentity())&&r.definitionForSourceIdentity(d->sourceIdentity()),"exact every definition lookup");}check(!r.definitionForSourceKey("foreign"),"foreign package lookup");}
void packageNegatives(const fs::path& package,const fs::path& assets){
 const auto out=fs::absolute("Build/manager-resume-r03/harmonic-contact-family118-r01");const auto scratch=out/"package-guards";
 const auto write=[](const fs::path& path,const std::string& text){fs::create_directories(path.parent_path());std::ofstream file(path,std::ios::binary);file<<text;check(file.good(),"write own package guard");};
 const auto reset=[&]{fs::remove_all(scratch);fs::create_directories(scratch);for(const auto* name:{"manifest.json","definitions.jsonl","contexts.json"})fs::copy_file(package/name,scratch/name);};
 const auto rejected=[&](const fs::path& p,const fs::path& a){auto r=H::InstalledHarmonicContactTaskRegistry::load(p,a);check(r.size()==0&&!r.error().empty()&&!r.ownerBridgeReady(),"zero partial package readiness");for(const auto& key:H::keys())check(!r.containsSourceKey(key)&&!r.containsSourceIdentity(H::definition(key).sourceIdentity())&&!r.definitionForSourceKey(key),"no partial closed route");++refusals;return r;};
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
int main(int argc,char** argv){try{check(argc==3,"package and host asset roots");sourceFamily();installed(argv[1],argv[2]);packageNegatives(fs::absolute(argv[1]),fs::absolute(argv[2]));std::cout<<"{\"result\":\"PASS_SOURCE_NATIVE_FAMILY_AND_PACKAGE\",\"rows\":118,\"source_contacts\":1510,\"saved_variant_contact_projections\":"<<contacts<<",\"phase_schema_samples\":"<<phaseReports<<",\"assertions\":"<<checks<<",\"refusals\":"<<refusals<<",\"native_owner_runs\":0,\"package_source_assets\":6,\"zero_partial_load\":true}\n";return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
