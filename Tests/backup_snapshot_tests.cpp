#include "storage/ProfileStore.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "content/Canonical.hpp"
#include "fixtures/profile_store/SyntheticL105Handler.hpp"
#include <atomic>
#include <condition_variable>
#include <fstream>
#include <iostream>
#include <mutex>
#include <sys/stat.h>
#include <thread>
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
std::string str(const Value& v,const std::string& k){return at(v,k).string();}
std::int64_t integer(const Value& v){std::int64_t n;if(!v.integer(n))throw std::runtime_error("Integer fixture expected");return n;}
std::string read(const fs::path& p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot read "+p.string());return {std::istreambuf_iterator<char>(f),{}};}
void write(const fs::path& p,const std::string& bytes){std::ofstream f(p,std::ios::binary);f<<bytes;if(!f)throw std::runtime_error("Cannot retain "+p.string());}
void check(const std::string& name,bool pass){checks.emplace_back(O{{"name",name},{"pass",pass}});std::cout<<(pass?"PASS ":"FAIL ")<<name<<'\n';if(!pass)throw std::runtime_error(name);}
Value replyValue(const Reply& r){return O{{"status",statusName(r.status)},{"operation",r.operation},{"owner",r.owner},{"code",r.code},{"message",r.message},{"data",r.data}};}
Reply observe(const std::string& name,ProfileStore::Future future,Status expected=Status::Confirmed){
    auto r=future.get();trace.emplace_back(O{{"name",name},{"reply",replyValue(r)}});
    check(name+" status "+statusName(expected),r.status==expected);return r;
}
fs::path copyProfile(const std::string& source,const std::string& name){
    auto dir=root/name;
    check(name+" new copied fixture directory",!fs::exists(dir));fs::create_directory(dir);chmod(dir.c_str(),0700);
    for(const char* suffix:{"","-wal","-shm","-journal"}){
        auto from=fixtures/source/(std::string("profile.sqlite")+suffix);
        if(fs::exists(from)){auto to=dir/from.filename();fs::copy_file(from,to);chmod(to.c_str(),0600);}
    }
    return dir/"profile.sqlite";
}
StoreOptions storeOptions(const fs::path& path){StoreOptions o;o.path=path;o.create=false;o.preferenceValidator=[](const std::string& key,std::int64_t version,const Value& value){return key=="backup.fixture"&&version==1&&value.isObject();};return o;}
BackupSnapshotOptions backupOptions(const std::string& name){BackupSnapshotOptions o;o.destinationDirectory=root/name;o.stopped=true;o.unresolvedWrites=false;return o;}
void unchanged(ProfileStore& store,const Reply& before,const std::string& label){
    auto after=observe(label+" inspect source",store.snapshot(newUuid()));
    check(label+" authoritative rows/BLOBs unchanged",at(after.data,"authoritative")==at(before.data,"authoritative"));
}
struct Gate {
    std::mutex mutex;
    std::condition_variable cv;
    std::string phase,operation;
    bool entered=false,released=false;
    void hook(const std::string& p,const std::string& op){
        if(p!=phase||op!=operation)return;
        std::unique_lock<std::mutex> lock(mutex);entered=true;cv.notify_all();
        if(!cv.wait_for(lock,std::chrono::seconds(5),[&]{return released;}))throw std::runtime_error("Bounded fixture gate timed out");
    }
    void wait(){std::unique_lock<std::mutex> lock(mutex);check("actual worker entered "+phase,cv.wait_for(lock,std::chrono::seconds(5),[&]{return entered;}));}
    void release(){std::lock_guard<std::mutex> lock(mutex);released=true;cv.notify_all();}
};
void success(){
    auto path=copyProfile("normal","settled-source");
    auto o=storeOptions(path);
    auto source=fixtures/"source";
    auto context=parseCanonical(read(source/"standalone-context.json"));
    o.sourceValidator=reviewer::synthetic::L105SourceHandler(read(source/"historical-l105-authority.json"),context);
    ProfileStore store(o);
    auto initial=observe("copied settled normal",store.snapshot(newUuid()));
    for(const char* name:{"standalone-learner.json","standalone-same-take-review.json","standalone-incomplete-work.json","standalone-protected-zero.json"}){
        auto v=parseCanonical(read(source/name));
        at(v,"performer_ref")=initial.owner;at(at(v,"attestation"),"performer_ref")=initial.owner;
        if(str(at(v,"attestation"),"role")=="learner")at(at(v,"attestation"),"who")=initial.owner;
        observe(std::string("append labelled synthetic source fixture ")+name,store.attest(newUuid(),canonical(v)));
    }
    O large{{"synthetic",true},{"chunks",A{std::string(400000,'a'),std::string(400000,'b'),std::string(400000,'c')}}};
    observe("committed WAL setting spans multiple backup steps",store.compareExchangePreferences(newUuid(),"backup.fixture",1,0,canonical(large),true));
    auto before=observe("settled boundary with all evidence types",store.snapshot(newUuid()));
    write(root/"settled-before.json",canonical(before.data));
    for(const char* table:{"session","session_close","identity","finalized","late_evidence","acknowledgment","source_attestation","preferences","rule_observation"})
        check(std::string("successful boundary covers ")+table,!at(at(before.data,"authoritative"),table).array().empty());
    check("source contains committed WAL",fs::file_size(path.string()+"-wal")>0);
    auto options=backupOptions("settled-snapshot");
    auto r=observe("native standalone snapshot",store.prepareBackupSnapshot("snapshot-normal",options));
    write(root/"settled-receipt.json",canonical(replyValue(r)));
    check("streamed digest equals existing snapshot identity",str(at(r.data,"authority"),"sha256")==str(before.data,"snapshot_sha256"));
    check("same profile and receipt marker",at(r.data,"profile_id")==at(before.data,"profile_id")&&at(r.data,"committed_seq")==at(before.data,"committed_seq"));
    check("multiple native backup steps exercised",integer(at(r.data,"backup_steps"))>=2);
    check("snapshot never claims archive or restore",at(r.data,"archive_published")==Value(false)&&at(r.data,"restore_performed")==Value(false));
    auto destination=options.destinationDirectory/"profile.sqlite";
    check("closed-file hash and size bound",str(at(r.data,"file"),"sha256")==fathom::content::sha256(read(destination))&&integer(at(at(r.data,"file"),"bytes"))==static_cast<std::int64_t>(fs::file_size(destination)));
    for(const char* suffix:{"-wal","-shm","-journal"})check(std::string("no required snapshot sidecar ")+suffix,!fs::exists(destination.string()+suffix));
    unchanged(store,before,"successful snapshot");
    auto moved=root/"independent-profile";fs::create_directory(moved);chmod(moved.c_str(),0700);
    fs::copy_file(destination,moved/"profile.sqlite");chmod((moved/"profile.sqlite").c_str(),0600);
    {ProfileStore restored(storeOptions(moved/"profile.sqlite"));auto fresh=observe("isolated normal native reopen using only DB",restored.snapshot(newUuid()));check("all authoritative rows and original BLOBs reconcile",at(fresh.data,"authoritative")==at(before.data,"authoritative"));write(root/"isolated-reopen.json",canonical(fresh.data));}
    auto defaults=backupOptions("default-refusal");defaults.stopped=false;
    auto refused=observe("active transport attestation refused",store.prepareBackupSnapshot(newUuid(),defaults),Status::Busy);
    check("active refusal actionable",refused.code=="QUIESCENCE_REQUIRED"&&!fs::exists(defaults.destinationDirectory));
    defaults=backupOptions("unresolved-flag");defaults.unresolvedWrites=true;
    observe("uncertain acknowledgment caller refuses backup",store.prepareBackupSnapshot(newUuid(),defaults),Status::Busy);
    check("unresolved flag creates no stage",!fs::exists(defaults.destinationDirectory));
    auto oldHash=fathom::content::sha256(read(destination));
    refused=observe("existing snapshot refused intact",store.prepareBackupSnapshot(newUuid(),options),Status::DefiniteFailure);
    check("existing destination retained",refused.code=="SNAPSHOT_DESTINATION_EXISTS"&&fathom::content::sha256(read(destination))==oldHash);
    auto alias=backupOptions("alias");fs::create_directory_symlink(options.destinationDirectory,alias.destinationDirectory);
    observe("symlink destination refused",store.prepareBackupSnapshot(newUuid(),alias),Status::DefiniteFailure);
    check("symlink target unchanged",fathom::content::sha256(read(destination))==oldHash);
    auto within=options;within.destinationDirectory=path.parent_path()/"nested-snapshot";
    observe("stage inside live profile refused",store.prepareBackupSnapshot(newUuid(),within),Status::DefiniteFailure);
    check("no nested live stage",!fs::exists(within.destinationDirectory));
    auto cancelled=backupOptions("cancel-before");cancelled.cancelled=[](){return true;};
    refused=observe("cancel before snapshot",store.prepareBackupSnapshot(newUuid(),cancelled),Status::DefiniteFailure);
    check("cancel before entry has no stage",refused.code=="SNAPSHOT_CANCELLED"&&!fs::exists(cancelled.destinationDirectory));
    int cancelCalls=0;cancelled=backupOptions("cancel-after-begin");cancelled.cancelled=[&](){return ++cancelCalls==3;};
    refused=observe("cancel at post-BEGIN progress check",store.prepareBackupSnapshot(newUuid(),cancelled),Status::DefiniteFailure);
    check("post-BEGIN cancellation exercised",cancelCalls==3&&refused.code=="SNAPSHOT_CANCELLED");
    unchanged(store,before,"all entry refusals and cancellation");
    auto written=observe("writer transaction usable after post-BEGIN cancellation",store.compareExchangePreferences(newUuid(),"backup.fixture",1,1,canonical(large),true));
    check("explicit subsequent write increments preference revision",integer(at(written.data,"revision"))==2);
}
void walAndUnresolved(){
    auto path=copyProfile("wal","wal-source");ProfileStore store(storeOptions(path));
    auto before=observe("retained committed-WAL input",store.snapshot(newUuid()));
    auto r=observe("retained WAL native snapshot",store.prepareBackupSnapshot(newUuid(),backupOptions("wal-snapshot")));
    check("WAL boundary retains all three finalized outcomes",at(at(before.data,"authoritative"),"finalized").array().size()==3&&str(at(r.data,"authority"),"sha256")==str(before.data,"snapshot_sha256"));
    unchanged(store,before,"WAL snapshot");
    auto unresolved=copyProfile("unresolved","unresolved-source");ProfileStore pending(storeOptions(unresolved));
    auto prior=observe("actual unfinalized source profile",pending.snapshot(newUuid()));
    auto refusal=observe("actual DB unfinished owner refuses false-clear caller",pending.prepareBackupSnapshot(newUuid(),backupOptions("unfinished-refused")),Status::Busy);
    check("actual DB refusal actionable and no stage",refusal.code=="RECOVERY_REQUIRED"&&!fs::exists(root/"unfinished-refused"));
    unchanged(pending,prior,"unfinished refusal");
}
void fence(){
    auto path=copyProfile("normal","fenced-source");auto gate=std::make_shared<Gate>();gate->phase="backup_boundary_captured";gate->operation="held-backup";
    auto o=storeOptions(path);o.diagnosticHook=[gate](const std::string& phase,const std::string& op){gate->hook(phase,op);};
    ProfileStore store(o);auto before=observe("fence initial boundary",store.snapshot(newUuid()));
    auto future=store.prepareBackupSnapshot("held-backup",backupOptions("fenced-snapshot"));gate->wait();
    observe("competing settings deferred",store.compareExchangePreferences(newUuid(),"backup.fixture",1,0,"{}",true),Status::Busy);
    observe("competing history deferred",store.acknowledge(newUuid(),newUuid(),"fg:item:000001",1,"2026-09-12T00:00:00Z"),Status::Busy);
    observe("competing snapshot deferred",store.prepareBackupSnapshot(newUuid(),backupOptions("competing-snapshot")),Status::Busy);
    check("existing native profile lease never released",[&]{try{ProfileLease second(path,false);return false;}catch(...){return true;}}());
    gate->release();observe("held snapshot finishes",std::move(future));unchanged(store,before,"maintenance fence");
    observe("new settings accepted after fence cleanup",store.compareExchangePreferences(newUuid(),"backup.fixture",1,0,"{}",true));
    auto secondGate=std::make_shared<Gate>();secondGate->phase="before_operation";secondGate->operation="held-read";
    auto q=storeOptions(copyProfile("normal","inflight-source"));q.diagnosticHook=[secondGate](const std::string& phase,const std::string& op){secondGate->hook(phase,op);};
    ProfileStore active(q);auto readFuture=active.snapshot("held-read");secondGate->wait();
    observe("empty queue with running job refuses maintenance",active.prepareBackupSnapshot(newUuid(),backupOptions("inflight-refused")),Status::Busy);
    auto queued=active.readPreferences("queued-read","missing");
    observe("queued prior work refuses maintenance",active.prepareBackupSnapshot(newUuid(),backupOptions("queued-refused")),Status::Busy);
    secondGate->release();observe("running read retained",std::move(readFuture));observe("queued read retained",std::move(queued),Status::DefinitelyAbsent);
    observe("backup proceeds only after prior work settles",active.prepareBackupSnapshot(newUuid(),backupOptions("after-idle")));
}
void identityChanges(){
    for(const auto& mode:std::vector<std::string>{"replace-before-hash","modify-before-hash","modify-before-receipt"}){
        auto path=copyProfile("normal",mode+"-source");auto o=storeOptions(path);
        auto options=backupOptions(mode+"-stage");auto destination=options.destinationDirectory/"profile.sqlite";
        bool exercised=false;
        o.diagnosticHook=[&](const std::string& phase,const std::string&){
            const std::string wanted=mode=="modify-before-receipt"?"backup_snapshot_verified":"backup_before_file_hash";
            if(phase!=wanted)return;
            exercised=true;
            if(mode=="replace-before-hash"){
                // Byte-identical replacement still must not be joined to the validated inode.
                fs::rename(destination,options.destinationDirectory/"original-validated.sqlite");
                fs::copy_file(options.destinationDirectory/"original-validated.sqlite",destination);chmod(destination.c_str(),0600);
            }else{
                // In-place append after validation/hash changes identity without touching source.
                std::ofstream changed(destination,std::ios::binary|std::ios::app);changed.put('x');changed.close();
                if(!changed)throw std::runtime_error("Cannot create declared candidate mutation");
            }
        };
        ProfileStore store(o);auto before=observe(mode+" before",store.snapshot(newUuid()));
        auto r=observe(mode,store.prepareBackupSnapshot(newUuid(),options),Status::DefiniteFailure);
        check(mode+" exact boundary rejects changed candidate",exercised&&r.code=="SNAPSHOT_CHANGED"&&r.data.null());
        unchanged(store,before,mode);
        if(mode=="replace-before-hash")check("replaced validated original preserved",fs::exists(options.destinationDirectory/"original-validated.sqlite"));
        observe(mode+" writer usable after refusal",store.compareExchangePreferences(newUuid(),"backup.fixture",1,0,"{}",true));
    }
}
void phaseFailures(){
    for(const auto& mode:std::vector<std::string>{"cancel-during-copy","deadline-during-validation","write-phase-failure","cancel-during-hash"}){
        auto path=copyProfile("normal",mode+"-source");auto o=storeOptions(path);std::atomic<bool> cancel{false};bool targetPhaseReached=false;A phases;
        o.diagnosticHook=[&](const std::string& phase,const std::string&){
            phases.emplace_back(phase);
            if(mode=="cancel-during-copy"&&phase=="backup_step"){targetPhaseReached=true;cancel=true;}
            if(mode=="deadline-during-validation"&&phase=="backup_before_source_validation"){
                targetPhaseReached=true;std::this_thread::sleep_for(std::chrono::milliseconds(1250));
            }
            if(mode=="write-phase-failure"&&phase=="backup_after_copy"){
                targetPhaseReached=true;throw std::runtime_error("Declared snapshot-stage write/finalization exception; no physical disk-failure claim");
            }
            if(mode=="cancel-during-hash"&&phase=="backup_before_file_hash"){targetPhaseReached=true;cancel=true;}
        };
        ProfileStore store(o);auto before=observe(mode+" before",store.snapshot(newUuid()));auto options=backupOptions(mode+"-stage");
        options.cancelled=[&]{return cancel.load();};if(mode=="deadline-during-validation")options.timeout=std::chrono::milliseconds(1000);
        auto r=observe(mode,store.prepareBackupSnapshot(newUuid(),options),Status::DefiniteFailure);
        trace.emplace_back(O{{"name",mode+" actual reached phases"},{"phases",phases}});
        check(mode+" intended phase was actually reached",targetPhaseReached);
        check(mode+" expected failure classification",r.code==(mode=="deadline-during-validation"?"SNAPSHOT_DEADLINE":mode=="write-phase-failure"?"EXCEPTION":"SNAPSHOT_CANCELLED"));
        check(mode+" never successful stage receipt",r.data.null());cancel=false;unchanged(store,before,mode);
        observe(mode+" writer usable after cleanup",store.compareExchangePreferences(newUuid(),"backup.fixture",1,0,"{}",true));
    }
}
} // namespace
int main(int argc,char** argv){
    if(argc!=3){std::cerr<<"Usage: backup_snapshot_tests /absolute/evidence /absolute/evidence/fixtures\n";return 64;}
    fs::path evidence;bool successFlag=false;
    try{
        evidence=fs::canonical(argv[1]);fixtures=fs::canonical(argv[2]);
        if(fixtures!=evidence/"fixtures")throw std::runtime_error("Only copied fixtures under this evidence root are allowed");
        root=evidence/"test-data"/"snapshot01";if(fs::exists(root))throw std::runtime_error("Never overwrite a native run");fs::create_directories(root);chmod(root.parent_path().c_str(),0700);chmod(root.c_str(),0700);
        success();walAndUnresolved();fence();identityChanges();phaseFailures();successFlag=true;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(!root.empty()&&fs::exists(root))write(root/"failure.txt",e.what());}
    if(!root.empty()&&fs::exists(root))write(root/"checks.json",canonical(O{{"synthetic",true},{"actual_human_work",false},{"production_snapshot",true},{"archive_or_restore",false},{"status",successFlag?"PASS":"FAIL"},{"checks",checks},{"trace",trace}}));
    std::cout<<checks.size()<<" checks, "<<(successFlag?"PASS":"FAIL")<<'\n';return successFlag?0:1;
}
