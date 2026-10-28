#include "desktop/PreviewResume.hpp"
#include "content/Canonical.hpp"
#include "platform/ProfileAccessMac.hpp"
#include <fstream>
#include <iostream>

namespace {
using namespace fathom;
using V=json::Value;using O=V::Object;using A=V::Array;namespace fs=std::filesystem;
std::string read(const fs::path& p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Missing input "+p.string());return std::string(std::istreambuf_iterator<char>(f),{});}
void write(const fs::path& p,const std::string& s){std::ofstream f(p,std::ios::binary);f<<s;f.close();if(!f)throw std::runtime_error("Evidence write failed");}
const V& field(const V& v,const std::string& k){return v.object().at(k);}V& m(V& v,const std::string& k){return v.object().at(k);}
void hashes(storage::Reply& r){auto a=field(r.data,"authoritative");m(r.data,"snapshot_sha256")=content::sha256(storage::canonical(a));a.object().erase("rule_observation");m(r.data,"evidence_sha256")=content::sha256(storage::canonical(a));}
void directory(const fs::path& p){if(fs::exists(p))throw std::runtime_error("Refuse existing test path");fs::create_directories(p);fs::permissions(p,fs::perms::owner_all);}
storage::Reply snapshot(const fs::path& p){storage::StoreOptions o;o.path=p/"profile.sqlite";storage::ProfileStore store(o);auto r=store.snapshot("preview-inspection").get();if(r.status!=storage::Status::Confirmed)throw std::runtime_error(r.code+":"+r.message);return r;}
}
int main(int argc,char** argv){int count=0;std::ofstream log;try{
 if(argc==3&&std::string(argv[1])=="--snapshot"){std::cout<<storage::canonical(snapshot(fs::path(argv[2])).data)<<'\n';return 0;}
 if(argc!=3)throw std::runtime_error("Frozen native input directory and new absolute evidence directory required");
 const fs::path input=argv[1],out=argv[2];if(!input.is_absolute()||!out.is_absolute())throw std::runtime_error("Absolute paths required");directory(out);log.open(out/"checks.tsv");
 auto ck=[&](bool ok,const std::string& name){log<<++count<<'\t'<<name<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(name);};
 auto refuse=[&](auto fn,const std::string& name){std::string error;try{fn();}catch(const std::exception& e){error=e.what();}ck(!error.empty(),name);write(out/("refusal-"+std::to_string(count)+".txt"),error);};
 auto copy=[&](const std::string& name){auto p=out/name;directory(p);fs::copy_file(input/"profile.sqlite",p/"profile.sqlite");return p;};
 auto dir=copy("valid");auto original=snapshot(dir);const auto& sessions=field(field(original.data,"authoritative"),"session").array();ck(sessions.size()==1,"retained single original Session input");
 desktop::PreviewResumeRequest request{dir,field(original.data,"profile_id").string(),sessions[0].array()[0].string(),sessions[0].array()[2].string()};
 write(out/"request.json",storage::canonical(O{{"directory",dir.string()},{"profile",request.profile},{"session",request.session},{"timezone",request.timezone}}));write(out/"before.json",storage::canonical(original.data));
 {auto opened=desktop::openPreviewResume(request);ck(opened.snapshot.data==original.data,"actual helper reopens exact profile and authoritative snapshot");}
 ck(snapshot(dir).data==original.data,"helper writes no Session history acknowledgment or time");
 auto wrong=request;wrong.profile="00000000-0000-4000-8000-000000000001";
 refuse([&]{desktop::openPreviewResume(wrong);},"wrong explicit profile refuses");
 wrong=request;wrong.session="00000000-0000-4000-8000-000000000002";refuse([&]{desktop::openPreviewResume(wrong);},"missing explicit original Session refuses");
 wrong=request;wrong.timezone="UTC";refuse([&]{desktop::openPreviewResume(wrong);},"changed Session timezone refuses");
 wrong=request;wrong.timezone="Invalid/Missing";refuse([&]{desktop::openPreviewResume(wrong);},"invalid IANA zone refuses");
 wrong=request;wrong.directory=out/"missing";refuse([&]{desktop::openPreviewResume(wrong);},"missing directory refuses without creation");ck(!fs::exists(wrong.directory),"missing directory remains missing");
 wrong=request;wrong.directory="relative";refuse([&]{desktop::openPreviewResume(wrong);},"relative path refuses");
 wrong=request;wrong.directory=out/"linked";fs::create_directory_symlink(dir,wrong.directory);refuse([&]{desktop::openPreviewResume(wrong);},"symlink directory refuses");
 wrong=request;wrong.directory=out/"linked-database";directory(wrong.directory);fs::create_symlink(dir/"profile.sqlite",wrong.directory/"profile.sqlite");refuse([&]{desktop::openPreviewResume(wrong);},"symlink database refuses");
 for(const auto& mode:{"closed","nonfixture","bad-hash","malformed-session"}){
  auto changed=original;auto& a=m(changed.data,"authoritative");
  if(mode==std::string("closed"))m(a,"session_close").array().emplace_back(A{request.session,"2026-09-09T00:00:00Z","synthetic-close"});
  if(mode==std::string("nonfixture"))m(a,"session").array()[0].array()[4]=nullptr;
  if(mode==std::string("malformed-session"))m(a,"session").array()[0]=A{};
  hashes(changed);if(mode==std::string("bad-hash"))m(changed.data,"snapshot_sha256")=std::string(64,'0');
  refuse([&]{desktop::validatePreviewResumeSnapshot(changed,request);},std::string("synthetic snapshot refusal ")+mode);
  write(out/(std::string("synthetic-")+mode+".json"),storage::canonical(changed.data));
 }
 const auto guided=copy("guided");std::string guidedSession;
 {
  storage::StoreOptions o;o.path=guided/"profile.sqlite";storage::ProfileStore store(o);
  const auto plan=O{{"version","guided-session-plan.1"},{"duration_minutes",V::fromInteger(10)},
                    {"planned_seconds",V::fromInteger(600)},{"content_version","development-preview-v1"},
                    {"items",A{}}};
  const auto created=store.createSession("guided-resume-session","2026-09-14T11:56:20Z","America/New_York",600,plan).get();
  ck(created.status==storage::Status::Confirmed&&!created.owner.empty(),"actual planned Guided Session created through ProfileStore");
  guidedSession=created.owner;
 }
 const auto guidedBefore=snapshot(guided);bool guidedRowFound=false;std::int64_t guidedPlanned{};
 for(const auto& row:field(field(guidedBefore.data,"authoritative"),"session").array()){
  const auto& cells=row.array();if(cells.size()==5&&cells[0]==V(guidedSession)){guidedRowFound=true;ck(cells[2]==V("America/New_York"),"planned Guided Session retains its source timezone");ck(cells[3].integer(guidedPlanned)&&guidedPlanned==600,"planned Guided Session retains 600 planned seconds");}
 }
 ck(guidedRowFound,"planned Guided Session is present in the authoritative snapshot");
 const desktop::PreviewResumeRequest guidedRequest{guided,field(guidedBefore.data,"profile_id").string(),guidedSession,"America/New_York"};
 write(out/"guided-request.json",storage::canonical(O{{"directory",guided.string()},{"profile",guidedRequest.profile},{"session",guidedRequest.session},{"timezone",guidedRequest.timezone}}));
 {auto opened=desktop::openPreviewResume(guidedRequest);ck(opened.snapshot.data==guidedBefore.data,"actual helper reopens a planned Guided Session without mutation");}
 ck(snapshot(guided).data==guidedBefore.data,"planned Guided resume creates no Session history or outcome");
 auto mismatched=guidedBefore;auto& mismatchRows=m(m(mismatched.data,"authoritative"),"session").array();
 for(auto& row:mismatchRows)if(row.array().at(0)==V(guidedSession))row.array().at(3)=V::fromInteger(1200);
 hashes(mismatched);refuse([&]{desktop::validatePreviewResumeSnapshot(mismatched,guidedRequest);},"planned Guided duration mismatch refuses");
 write(out/"guided-duration-mismatch.json",storage::canonical(mismatched.data));
 const auto unresolved=copy("unresolved");{
  storage::StoreOptions o;o.path=unresolved/"profile.sqlite";storage::ProfileStore store(o);const auto envelope=storage::validateEnvelope(read(input/"L3-original.json"));
  auto r=store.allocate("synthetic-unfinished","Attempt",field(envelope.value,"context"),"2026-09-12T09:00:00Z").get();ck(r.status==storage::Status::Confirmed,"actual isolated unfinished allocation created");
 }
 wrong=request;wrong.directory=unresolved;auto unresolvedBefore=snapshot(unresolved);refuse([&]{desktop::openPreviewResume(wrong);},"unresolved original refuses new-session resume");ck(snapshot(unresolved).data==unresolvedBefore.data,"unresolved original identity and bytes retained after refusal");write(out/"unresolved.json",storage::canonical(unresolvedBefore.data));
 const auto corrupt=copy("corrupt");const auto digest=field(field(original.data,"authoritative"),"finalized").array()[0].array()[2].string();
 auto bytes=read(corrupt/"profile.sqlite");const auto at=bytes.find(digest);ck(at!=std::string::npos&&bytes.find(digest,at+1)==std::string::npos,"unique isolated digest corruption target");
 fs::copy_file(corrupt/"profile.sqlite",corrupt/"valid-before.sqlite");bytes[at]=bytes[at]=='0'?'1':'0';write(corrupt/"profile.sqlite",bytes);const auto corruptHash=content::sha256(bytes);
 wrong=request;wrong.directory=corrupt;refuse([&]{desktop::openPreviewResume(wrong);},"corrupt authoritative original refuses without reset");ck(content::sha256(read(corrupt/"profile.sqlite"))==corruptHash,"corrupt bytes preserved on refusal");
 ck(snapshot(dir).data==original.data,"all valid-profile refusal cases preserve authoritative snapshot");write(out/"after.json",storage::canonical(snapshot(dir).data));
 write(out/"summary.json",storage::canonical(O{{"status","PASS"},{"checks",V::fromInteger(count)},{"classification","Actual Store/helper and explicit synthetic negative fixtures; no new human/native evidence"}}));std::cout<<"PASS "<<count<<" preview resume checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<count<<": "<<e.what()<<'\n';return 1;}}
