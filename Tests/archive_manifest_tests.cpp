#include "storage/ArchiveManifest.hpp"
#include "storage/ProfileStore.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "content/Canonical.hpp"
#include <atomic>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <sstream>
#include <sys/stat.h>
#include <vector>

namespace {
using namespace fathom::storage;
namespace fs=std::filesystem;
using O=Value::Object;
using A=Value::Array;
fs::path root,fixtures;
A checks,trace;
const Value& at(const Value& v,const std::string& k){return v.object().at(k);}
Value& at(Value& v,const std::string& k){return v.object().at(k);}
Value num(std::int64_t v){return Value::fromInteger(v);}
std::int64_t integer(const Value& v){std::int64_t n;if(!v.integer(n))throw std::runtime_error("Fixture integer expected");return n;}
std::string read(const fs::path& p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot read "+p.string());return {std::istreambuf_iterator<char>(f),{}};}
void writeNew(const fs::path& p,const std::string& b){if(fs::exists(p))throw std::runtime_error("No evidence overwrite");std::ofstream f(p,std::ios::binary);f<<b;if(!f)throw std::runtime_error("Cannot write evidence");}
void check(const std::string& name,bool pass){checks.emplace_back(O{{"name",name},{"pass",pass}});std::cout<<(pass?"PASS ":"FAIL ")<<name<<'\n';if(!pass)throw std::runtime_error(name);}
template<class F> void rejects(const std::string& name,const std::string& code,F f){
    try{f();}catch(const EnvelopeError& e){check(name,e.code==code);return;}check(name,false);
}
Value counts(){O v;for(const char* k:{"acknowledgment","checkpoint","finalized","identity","late_evidence","metadata","pending","preferences","profile","rule_observation","session","session_close","source_attestation"})v.emplace(k,num(0));v["profile"]=num(1);v["metadata"]=num(2);return v;}
ArchiveManifestBuilder builder(const Value& c=counts()){
    return ArchiveManifestBuilder("fedcba98-7654-4321-89ab-0123456789ab",0,std::string(64,'a'),std::string(64,'b'),c);
}
Value finished(const ArchiveManifestBuilder& b){return b.manifest(4096,std::string(64,'c'));}
const Value& summary(const Value& m){return at(m,"snapshot");}
void pure(){
    auto b=builder();auto m=finished(b);
    check("exact six archive1 outer keys",m.object().size()==6&&at(m,"format")==Value("Fathom.ProfileArchive")&&at(m,"archive_version")==num(1)&&at(m,"data_schema_version")==num(1)&&m.find("snapshot")&&m.find("profile_bytes")&&m.find("profile_sha256"));
    check("empty nullable recorded range",at(summary(m),"practice_range_utc")==Value(O{{"first",nullptr},{"last",nullptr}}));
    check("empty reference list and zero result/source counts",at(summary(m),"content_references").array().empty()&&at(summary(m),"results")==num(0)&&at(summary(m),"attestations")==num(0));
    b.addAcknowledgment("fg:item:000002",1);b.addAcknowledgment("fg:item:000002",1);m=finished(b);
    auto ref=at(summary(m),"content_references").array().front();
    check("ack-only dedup retains missing metadata",at(summary(m),"content_references").array().size()==1&&at(ref,"reference_kind")==Value("item_revision_only")&&ref.find("variant_id")==nullptr&&ref.find("content_version")==nullptr&&ref.find("source_manifest_sha256")==nullptr);
    check("ack does not invent recorded practice date",at(summary(m),"practice_range_utc")==Value(O{{"first",nullptr},{"last",nullptr}}));
    auto context=parseCanonical(read(fixtures/"attempt-context.json"));b.addContext(context);b.addContext(context);m=finished(b);
    check("full same-item context never enriches or erases ack-only record",at(summary(m),"content_references").array().size()==2);
    for(const auto& r:at(summary(m),"content_references").array())if(at(r,"reference_kind")==Value("versioned_content"))
        for(const char* k:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs"})check(std::string("exact original full-reference field ")+k,at(r,k)==at(context,k));
    auto alternate=context;at(alternate,"variant_id")="fg:variant:999901";b.addContext(alternate);
    alternate=context;at(alternate,"source_manifest_sha256")=std::string(64,'d');b.addContext(alternate);
    alternate=context;at(alternate,"source_refs")=A{std::string("synthetic:distinct-source")};b.addContext(alternate);m=finished(b);
    check("distinct variant and provenance never merged",at(summary(m),"content_references").array().size()==5);
    auto standalone=parseCanonical(read(fixtures/"standalone-context.json"));b.addContext(standalone);b.addContext(standalone);m=finished(b);
    check("same-take standalone review dedups reference only",at(summary(m),"content_references").array().size()==6);
    check("old content is not substituted or admitted",at(summary(m),"content_compatibility").string().find("NOT ASSESSED")==0);
    auto chronological=builder();
    for(const char* t:{"2026-09-12T01:00:00Z","2026-09-12T01:00:00.1Z","2026-09-12T01:00:00.000000Z","2026-09-12T01:00:00.100000Z"})chronological.addRecordedTime(t);
    m=finished(chronological);check("fractional UTC chronology and deterministic equal-instant original spelling",at(summary(m),"practice_range_utc")==Value(O{{"first","2026-09-12T01:00:00.000000Z"},{"last","2026-09-12T01:00:00.1Z"}}));
    auto c=counts();at(c,"finalized")=num(1);at(c,"source_attestation")=num(2);auto records=builder(c);records.addRecordedTime("2026-09-12T02:00:00Z");m=finished(records);
    check("Freeplay/zero-active results remain recorded facts without lesson refs",at(summary(m),"results")==num(1)&&at(summary(m),"content_references").array().empty()&&at(summary(m),"practice_range_utc").find("first")!=nullptr);
    check("two source facts do not imply two performances",at(summary(m),"attestations")==num(2)&&at(summary(m),"count_meaning").string().find("not distinct performances")!=std::string::npos);
    rejects("boolean revision rejected","ARCHIVE_MANIFEST_INVALID",[&]{auto bad=context;at(bad,"content_revision")=true;auto q=builder();q.addContext(bad);});
    rejects("missing provenance rejected","ARCHIVE_MANIFEST_INVALID",[&]{auto bad=context;bad.object().erase("source_refs");auto q=builder();q.addContext(bad);});
    auto full=builder();bool capacitySeen=false;std::size_t inserted=0;
    for(int i=1;i<=1000;++i){
        auto changed=context;std::ostringstream id;id<<"fg:variant:"<<std::setw(6)<<std::setfill('0')<<i;at(changed,"variant_id")=id.str();
        try{full.addContext(changed);++inserted;(void)finished(full);}catch(const EnvelopeError& x){check("actual64KiB refusal is explicit capacity error",x.code=="ARCHIVE_MANIFEST_CAPACITY");capacitySeen=true;break;}
    }
    check("bounded distinct-reference accumulation refuses without pretending completion",capacitySeen&&inserted>0&&inserted<1000);
    trace.emplace_back(O{{"case","synthetic manifest capacity"},{"insertions_until_refusal",num(static_cast<std::int64_t>(inserted))},{"configured_limit",num(65536)}});
}
Reply observe(const std::string& name,ProfileStore::Future f,Status expected=Status::Confirmed){
    auto r=f.get();trace.emplace_back(O{{"name",name},{"status",statusName(r.status)},{"code",r.code},{"data",r.data}});check(name+" status",r.status==expected);return r;
}
fs::path profile(const std::string& name,bool copy){auto p=root/name;fs::create_directory(p);chmod(p.c_str(),0700);if(copy){fs::copy_file(fixtures/"settled/profile.sqlite",p/"profile.sqlite");chmod((p/"profile.sqlite").c_str(),0600);}return p/"profile.sqlite";}
StoreOptions options(const fs::path& p,bool create=false){StoreOptions o;o.path=p;o.create=create;o.createdUtc="2026-09-12T00:00:00Z";return o;}
BackupSnapshotOptions snapshot(const std::string& name){BackupSnapshotOptions b;b.destinationDirectory=root/name;b.stopped=true;b.unresolvedWrites=false;b.includeArchiveManifest=true;return b;}
void verifySaved(const Reply& r,const BackupSnapshotOptions& opt){
    const auto& m=at(r.data,"manifest");auto bytes=read(opt.destinationDirectory/"manifest.json");
    check("actual manifest bytes equal canonical receipt",bytes==canonical(at(m,"metadata"))&&parseCanonical(bytes)==at(m,"metadata"));
    check("actual manifest file hash and capacity bound",fathom::content::sha256(bytes)==at(at(m,"file"),"sha256").string()&&integer(at(at(m,"file"),"bytes"))==static_cast<std::int64_t>(bytes.size())&&bytes.size()<=65536);
    check("manifest binds actual closed database bytes/hash",at(at(m,"metadata"),"profile_bytes")==at(at(r.data,"file"),"bytes")&&at(at(m,"metadata"),"profile_sha256")==at(at(r.data,"file"),"sha256")&&fathom::content::sha256(read(opt.destinationDirectory/"profile.sqlite"))==at(at(r.data,"file"),"sha256").string());
    const auto& s=summary(at(m,"metadata"));
    check("manifest binds verified profile/marker/authority/schema",at(s,"profile_id")==at(r.data,"profile_id")&&at(s,"marker")==at(r.data,"committed_seq")&&at(s,"authority_sha256")==at(at(r.data,"authority"),"sha256")&&at(s,"schema_sha256")==at(r.data,"schema_sha256"));
    check("stage receipt never claims archive publication or restore",at(m,"staged")==Value(true)&&at(r.data,"archive_published")==Value(false)&&at(r.data,"restore_performed")==Value(false));
}
void native(){
    ProfileStore empty(options(profile("empty-profile",false),true));auto off=snapshot("snapshot-only");off.includeArchiveManifest=false;
    auto old=observe("unchanged snapshot-only default path",empty.prepareBackupSnapshot(newUuid(),off));check("snapshot-only has no manifest field/file",old.data.find("manifest")==nullptr&&!fs::exists(off.destinationDirectory/"manifest.json"));
    auto opt=snapshot("empty-stage");auto r=observe("native empty manifest",empty.prepareBackupSnapshot(newUuid(),opt));verifySaved(r,opt);
    check("native empty does not use profile creation time as practice",at(summary(at(at(r.data,"manifest"),"metadata")),"practice_range_utc")==Value(O{{"first",nullptr},{"last",nullptr}}));
    observe("actual synthetic acknowledgment",empty.acknowledge(newUuid(),newUuid(),"fg:item:000002",1,"2026-09-12T03:00:00Z"));
    opt=snapshot("ack-stage");r=observe("native acknowledgment-only manifest",empty.prepareBackupSnapshot(newUuid(),opt));verifySaved(r,opt);
    const auto& ack=summary(at(at(r.data,"manifest"),"metadata"));check("native ack retains only known reference and no practice date",at(ack,"content_references").array().size()==1&&at(at(ack,"content_references").array()[0],"reference_kind")==Value("item_revision_only")&&at(ack,"practice_range_utc")==Value(O{{"first",nullptr},{"last",nullptr}}));
    ProfileStore settled(options(profile("settled-profile",true)));auto before=observe("settled before manifest",settled.snapshot(newUuid()));
    opt=snapshot("settled-stage");r=observe("native settled rich manifest",settled.prepareBackupSnapshot(newUuid(),opt));verifySaved(r,opt);
    const auto& rich=summary(at(at(r.data,"manifest"),"metadata"));check("native distinct record types retained",at(rich,"results")==num(2)&&at(rich,"attestations")==num(4)&&at(rich,"sessions")==num(1)&&at(rich,"rule_observations")==num(1));
    check("native Attempt, standalone source and acknowledgment references distinct",at(rich,"content_references").array().size()==3);
    auto after=observe("settled after manifest",settled.snapshot(newUuid()));check("native full source authority unchanged",at(before.data,"authoritative")==at(after.data,"authoritative"));
    writeNew(root/"rich-manifest.json",canonical(at(at(r.data,"manifest"),"metadata")));
    for(const auto& mode:std::vector<std::string>{"cancel-before-manifest","replace-verified-manifest","change-db-after-manifest"}){
        auto o=options(profile(mode+"-profile",true));auto b=snapshot(mode+"-stage");std::atomic<bool> cancel{false};bool phaseReached=false;A phases;
        o.diagnosticHook=[&](const std::string& phase,const std::string&){
            phases.emplace_back(phase);
            if(mode=="cancel-before-manifest"&&phase=="backup_manifest_before_write"){phaseReached=true;cancel=true;}
            if(mode!="cancel-before-manifest"&&phase=="backup_manifest_verified"){
                phaseReached=true;
                auto path=b.destinationDirectory/(mode=="replace-verified-manifest"?"manifest.json":"profile.sqlite");
                if(mode=="replace-verified-manifest"){auto saved=path.parent_path()/"original-manifest.json";fs::rename(path,saved);fs::copy_file(saved,path);chmod(path.c_str(),0600);}
                else{std::ofstream f(path,std::ios::binary|std::ios::app);f.put('x');f.close();if(!f)throw std::runtime_error("Cannot apply declared DB mutation");}
            }
        };
        ProfileStore store(o);auto initial=observe(mode+" before",store.snapshot(newUuid()));b.cancelled=[&]{return cancel.load();};
        auto failure=observe(mode,store.prepareBackupSnapshot(newUuid(),b),Status::DefiniteFailure);
        check(mode+" actual phase and refusal code",phaseReached&&failure.code==(mode=="cancel-before-manifest"?"SNAPSHOT_CANCELLED":"SNAPSHOT_CHANGED")&&failure.data.null());
        trace.emplace_back(O{{"case",mode},{"actual_phases",phases}});cancel=false;
        auto current=observe(mode+" after",store.snapshot(newUuid()));check(mode+" source authority retained",at(initial.data,"authoritative")==at(current.data,"authoritative"));
    }
}
}
int main(int argc,char** argv){
    if(argc!=3){std::cerr<<"Usage: archive_manifest_tests /absolute/E /absolute/E/fixtures\n";return 64;}
    bool passed=false,ownsRunDirectory=false;
    try{
        auto evidence=fs::canonical(argv[1]);fixtures=fs::canonical(argv[2]);if(fixtures!=evidence/"fixtures")throw std::runtime_error("Only this lane copied fixtures allowed");
        root=evidence/"test-data"/"manifest01";if(fs::exists(root))throw std::runtime_error("No run overwrite");
        fs::create_directories(root.parent_path());chmod(root.parent_path().c_str(),0700);
        if(!fs::create_directory(root))throw std::runtime_error("No run overwrite");
        ownsRunDirectory=true;chmod(root.c_str(),0700);
        pure();native();passed=true;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(ownsRunDirectory)writeNew(root/"failure.txt",e.what());}
    if(ownsRunDirectory)writeNew(root/"checks.json",canonical(O{{"status",passed?"PASS":"FAIL"},{"synthetic",true},{"human_work",false},{"published_backup",false},{"restored_profile",false},{"checks",checks},{"trace",trace}}));
    std::cout<<checks.size()<<" checks, "<<(passed?"PASS":"FAIL")<<'\n';return passed?0:1;
}
