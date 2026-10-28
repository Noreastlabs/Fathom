#include "storage/ProfileStore.hpp"
#include "storage/RestorePreparation.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "content/Canonical.hpp"
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <fstream>
#include <iostream>
#include <limits>
#include <mutex>
#include <set>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>

namespace {
using namespace fathom::storage;namespace fs=std::filesystem;using O=Value::Object;using A=Value::Array;
fs::path root,fixtures;std::string current;A checks,traces,phases;bool ownsRunDirectory=false;
const Value& at(const Value& v,const std::string& k){return v.object().at(k);}
std::string read(const fs::path& p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot read "+p.string());return {std::istreambuf_iterator<char>(f),{}};}
void writeNew(const fs::path& p,const std::string& text){if(fs::exists(p))throw std::runtime_error("No overwrite "+p.string());std::ofstream f(p,std::ios::binary);f<<text;f.close();if(!f||chmod(p.c_str(),0600)!=0)throw std::runtime_error("Cannot retain "+p.string());}
void directory(const fs::path& p){if(!fs::create_directory(p)||chmod(p.c_str(),0700)!=0)throw std::runtime_error("New private directory required "+p.string());}
void copyFixture(const fs::path& from,const fs::path& to){if(!fs::copy_file(from,to)||chmod(to.c_str(),0600)!=0)throw std::runtime_error("Copy failed");}
std::string sha(const fs::path& p){return fathom::content::sha256(read(p));}
Value native(const fs::path& p){struct stat s{};if(lstat(p.c_str(),&s)!=0)throw std::runtime_error("Cannot stat "+p.string());return O{{"device",std::to_string(s.st_dev)},{"inode",std::to_string(s.st_ino)},{"bytes",Value::fromInteger(s.st_size)},{"sha256",sha(p)}};}
void check(const std::string& name,bool okay){checks.emplace_back(O{{"case",current},{"name",name},{"pass",okay}});std::cout<<(okay?"PASS ":"FAIL ")<<current<<" "<<name<<'\n';if(!okay)throw std::runtime_error(name);}
fs::path live(){return root/current/"live/profile.sqlite";}
fs::path barrier(){return live().parent_path()/".fathom-restore.pending.json";}
fs::path operationDir(const std::string& op){return live().parent_path()/(".fathom-restore-"+op);}
void phase(const std::string& p,const std::string& op){if(p.rfind("restore_apply_",0)==0||p.rfind("restore_reconcile_",0)==0)phases.emplace_back(O{{"case",current},{"phase",p},{"operation",op}});}
StoreOptions options(){StoreOptions o;o.path=live();o.diagnosticHook=phase;return o;}
Value replyValue(const Reply& r){return O{{"status",statusName(r.status)},{"operation",r.operation},{"owner",r.owner},{"code",r.code},{"message",r.message},{"data",r.data}};}
Reply observe(const std::string& name,ProfileStore::Future f,Status expected,const std::string& code=""){
    auto r=f.get();traces.emplace_back(O{{"case",current},{"name",name},{"reply",replyValue(r)}});check(name+" status",r.status==expected);if(!code.empty())check(name+" code",r.code==code);return r;
}
Value snapshot(ProfileStore& s,const std::string& name){auto r=observe(name,s.snapshot(newUuid()),Status::Confirmed);writeNew(root/current/(name+".json"),canonical(r.data));return r.data;}
void matches(const Value& value,const Value& expected,const std::string& name){check(name+" exact13table authority",at(value,"authoritative")==at(expected,"authoritative"));check(name+" profile identity",at(value,"profile_id")==at(expected,"profile_id"));check(name+" marker",at(value,"committed_seq")==at(expected,"committed_seq"));}
void setup(const std::string& name,const std::string& kind="empty",const std::string& incoming="rich"){
    current=name;directory(root/name);directory(root/name/"live");if(kind!="create")copyFixture(fixtures/kind/"profile.sqlite",live());copyFixture(fixtures/incoming/"candidate.zip",root/name/"incoming.zip");
}
Value available(){auto m=parseCanonical(read(fixtures/"rich/manifest.json"));auto r=at(at(m,"snapshot"),"content_references").array().front();r.object().erase("reference_kind");return A{O{{"reference",r},{"provenance","Retained exact control-example metadata; not runtime/source acceptance"}}};}
RestoreApplyRequest prepare(ProfileStore& s){
    BackupSnapshotOptions b;b.destinationDirectory=root/current/"prepared";b.stopped=true;b.unresolvedWrites=false;
    RestorePreparationRequest q;q.archive=root/current/"incoming.zip";q.availableReferences=available();
    auto r=observe("prepare",s.prepareRestore(newUuid(),b,q),Status::Confirmed,"RESTORE_PREPARED");const auto& prepared=at(r.data,"restore_preparation");
    RestoreApplyRequest a;a.preview=at(prepared,"path").string();a.previewFile=at(prepared,"file");a.confirmationSha256=at(at(prepared,"record"),"confirmation_sha256").string();a.availableReferences=q.availableReferences;a.explicitConfirmation=true;a.stopped=true;a.unresolvedWrites=false;return a;
}
Value expected(const std::string& kind){auto dir=root/current/(kind+"-expected");directory(dir);copyFixture(fixtures/kind/"profile.sqlite",dir/"profile.sqlite");StoreOptions o;o.path=dir/"profile.sqlite";ProfileStore s(o);auto r=observe("expected incoming",s.snapshot(newUuid()),Status::Confirmed);writeNew(dir/"snapshot.json",canonical(r.data));return r.data;}
void retainedOriginal(const Value& before,const std::string& op,bool swapped){
    auto path=swapped?operationDir(op)/"profile.sqlite":root/current/"prepared/recovery-readback/profile.sqlite";
    auto dir=root/current/"original-reopen";directory(dir);copyFixture(path,dir/"profile.sqlite");StoreOptions o;o.path=dir/"profile.sqlite";ProfileStore original(o);
    auto r=observe("retained original normal open",original.snapshot(newUuid()),Status::Confirmed);matches(r.data,before,"original");writeNew(dir/"snapshot.json",canonical(r.data));
}
std::size_t swaps(const std::string& op){std::size_t count=0;for(const auto& p:phases)if(at(p,"operation")==Value(op)&&at(p,"phase")==Value("restore_apply_after_swap"))++count;return count;}
void recordOutcome(const Reply& r,const RestoreApplyRequest& q,const Value& expectedSnapshot,bool installed){
    check("receipt stopped",at(r.data,"required_resume_state")==Value("stopped"));check("receipt explicit outcome",at(r.data,"restore_performed")==Value(installed));
    check("invalidate old consumer context",at(r.data,"invalidate_previous_consumers")==Value(true));check("receipt exact confirmation",at(r.data,"confirmation_sha256")==Value(q.confirmationSha256));
    const auto& snap=at(r.data,"snapshot");check("receipt snapshot owner",at(snap,"profile_id")==at(expectedSnapshot,"profile_id"));check("receipt original marker",at(snap,"marker")==at(expectedSnapshot,"committed_seq"));
    auto manifest=parseCanonical(read(root/current/(installed?"prepared/incoming/manifest.json":"prepared/manifest.json")));
    check("outcome reference compatibility belongs to outcome",at(r.data,"content_compatibility")==detail::restoreContentComparison(manifest,detail::normalizedRestoreAvailability(q.availableReferences)));
    check("no inferred source/runtime admission",at(at(r.data,"content_compatibility"),"runtime_admission")==Value("NOT ASSESSED"));
}
void successes(){
    for(const std::string mode:{"rich-to-empty","empty-to-rich","created-to-rich"}){
        const bool reverse=mode=="empty-to-rich",created=mode=="created-to-rich";setup(mode,created?"create":reverse?"rich":"empty",reverse?"empty":"rich");
        const auto incoming=expected(reverse?"empty":"rich");Value before,afterWrite;std::string op=newUuid(),originalArchiveHash;RestoreApplyRequest q;
        {
            auto o=options();o.create=created;if(created)o.createdUtc="2026-09-13T02:45:52Z";ProfileStore s(o);
            if(!reverse){observe("actual WAL acknowledgment",s.acknowledge(newUuid(),newUuid(),"fg:item:000003",1,"2026-09-13T02:45:52Z"),Status::Confirmed);check("committed WAL exists",fs::exists(live().string()+"-wal")&&fs::file_size(live().string()+"-wal")>0);}
            before=snapshot(s,"before");q=prepare(s);originalArchiveHash=sha(root/current/"prepared/candidate.zip");
            auto r=observe("apply",s.applyRestore(op,q),Status::Confirmed,"RESTORE_APPLIED");check("same apply UUID",r.operation==op);recordOutcome(r,q,incoming,true);
            matches(snapshot(s,"after"),incoming,"incoming installed");check("one actual swap",swaps(op)==1);check("barrier retired only after resolution",!fs::exists(barrier())&&fs::exists(operationDir(op)/"resolved.json"));
            check("preserved original archive",sha(root/current/"prepared/candidate.zip")==originalArchiveHash);retainedOriginal(before,op,true);
            auto duplicate=observe("same original reconciliation",s.reconcileRestore(op,q),Status::Confirmed,"RESTORE_APPLIED");check("immutable original resolution",duplicate.data==r.data&&swaps(op)==1);
            observe("later legitimate acknowledgment",s.acknowledge(newUuid(),newUuid(),"fg:item:000003",1,"2026-09-13T03:00:00Z"),Status::Confirmed);afterWrite=snapshot(s,"after-legitimate-write");
            auto old=observe("reconcile after later write",s.reconcileRestore(op,q),Status::Confirmed,"RESTORE_APPLIED");check("historical receipt not rewritten by later activity",old.data==r.data&&at(afterWrite,"committed_seq")!=at(at(old.data,"snapshot"),"marker"));
            matches(snapshot(s,"after-reconciliation"),afterWrite,"later history preserved");
        }
        ProfileStore reopened(options());matches(snapshot(reopened,"normal-reopen"),afterWrite,"normal reopened incoming");check("still one swap",swaps(op)==1);
    }
}
void mutatePreference(ProfileStore& s){observe("real preference change without receipt marker",s.compareExchangePreferences(newUuid(),"restore.actor",1,0,canonical(O{{"value","synthetic"}}),true),Status::Confirmed);}
void allocateUnfinished(ProfileStore& s){
    const auto fixture=expected("rich");const auto& row=at(at(fixture,"authoritative"),"identity").array().front().array();const auto hex=at(row[4],"blob_hex").string();std::string bytes;
    for(std::size_t i=0;i<hex.size();i+=2)bytes.push_back(static_cast<char>(std::stoi(hex.substr(i,2),nullptr,16)));
    auto context=parseCanonical(bytes);const auto kind=row[1].string();
    if(kind=="Attempt"){auto session=observe("new disposable Session",s.createSession(newUuid(),"2026-09-13T02:45:52Z","UTC"),Status::Confirmed);context.object().at("session_id")=at(session.data,"session_id");}
    observe("actual unfinished allocation",s.allocate(newUuid(),kind,context,"2026-09-13T02:45:52Z"),Status::Confirmed);
}
void refusals(){
    for(const std::string mode:{"no-confirmation","wrong-digest","running","unresolved-writes","changed-content","stale-preference","stale-acknowledgment","unfinished","replaced-preview","invalid-operation","invalid-timeout","unknown-reconciliation"}){
        setup(mode);auto o=options();o.preferenceValidator=[](const std::string& k,std::int64_t v,const Value& value){return k=="restore.actor"&&v==1&&value==Value(O{{"value","synthetic"}});};ProfileStore s(o);
        const auto original=snapshot(s,"original");auto q=prepare(s);std::string op=newUuid(),code;Status wanted=Status::DefiniteFailure;
        if(mode=="no-confirmation"){q.explicitConfirmation=false;code="RESTORE_CONFIRMATION";}
        if(mode=="wrong-digest"){q.confirmationSha256=std::string(64,'1');code="RESTORE_CONFIRMATION";}
        if(mode=="running"||mode=="unresolved-writes"){q.stopped=mode!="running";q.unresolvedWrites=mode=="unresolved-writes";wanted=Status::Busy;code="QUIESCENCE_REQUIRED";}
        if(mode=="changed-content"){q.availableReferences.array()[0].object().at("reference").object().at("content_revision")=Value::fromInteger(2);code="RESTORE_CONTENT_STALE";}
        if(mode=="stale-preference"){mutatePreference(s);code="RESTORE_SOURCE_STALE";}
        if(mode=="stale-acknowledgment"){observe("new real acknowledgment",s.acknowledge(newUuid(),newUuid(),"fg:item:000003",1,"2026-09-13T03:00:00Z"),Status::Confirmed);code="RESTORE_SOURCE_STALE";}
        if(mode=="unfinished"){allocateUnfinished(s);code="RESTORE_RECOVERY_REQUIRED";}
        if(mode=="replaced-preview"){fs::rename(q.preview,root/current/"retained-preview.json");copyFixture(root/current/"retained-preview.json",q.preview);code="RESTORE_CHANGED";}
        if(mode=="invalid-operation"){op="invalid-uuid";code="INVALID_ENVELOPE";}
        if(mode=="invalid-timeout"){q.timeout=std::chrono::milliseconds::max();code="RESTORE_OPTIONS";}
        if(mode=="unknown-reconciliation")code="RESTORE_CHANGED";
        auto before=snapshot(s,"before");if(mode=="stale-preference")check("preference changed full authority without marker",at(before,"committed_seq")==at(original,"committed_seq")&&at(before,"authoritative")!=at(original,"authoritative"));
        observe("refusal",mode=="unknown-reconciliation"?s.reconcileRestore(op,q):s.applyRestore(op,q),wanted,code);
        matches(snapshot(s,"after"),before,"refused current source");check("no pending barrier or swap",!fs::exists(barrier())&&swaps(op)==0);
    }
}
void ordinaryOpen(const std::string& name,bool shouldOpen){
    auto before=native(live());bool opened=false,snapshotOkay=false;std::string message;
    try{ProfileStore s(options());opened=true;auto r=s.snapshot(newUuid()).get();snapshotOkay=r.status==Status::Confirmed;}catch(const std::exception& e){message=e.what();}
    if(opened)check(name+" opened snapshot",snapshotOkay);
    check(name+" expected open state",opened==shouldOpen);if(!shouldOpen){check(name+" explicit original restore message",message.find("Restore pending for operation")!=std::string::npos);check(name+" refuses before DB mutation",native(live())==before);}
    writeNew(root/current/(name+".json"),canonical(O{{"opened",opened},{"message",message}}));
}
void interruptionCases(){
    const std::vector<std::string> points={"before_barrier","barrier_retained","before_close","after_checkpoint","after_close","before_swap","after_swap","after_sync","before_reopen","after_reopen","before_resolution","resolution_retained","barrier_retired","nonstandard_after_swap","cancel_before_close","deadline_before_close"};
    for(const auto& point:points){
        setup("interrupt-"+point);const auto incoming=expected("rich");const auto op=newUuid();RestoreApplyRequest q;Value before;bool reached=false;std::atomic<bool> cancelled{false};
        const bool installed=point=="after_swap"||point=="after_sync"||point=="before_reopen"||point=="after_reopen"||point=="before_resolution"||point=="resolution_retained"||point=="barrier_retired"||point=="nonstandard_after_swap";
        const bool uncertain=point!="before_barrier";
        {
            auto o=options();o.diagnosticHook=[&](const std::string& p,const std::string& id){phase(p,id);
                const auto target=point=="nonstandard_after_swap"?std::string("after_swap"):(point=="cancel_before_close"||point=="deadline_before_close")?std::string("before_close"):point;
                if(!reached&&p=="restore_apply_"+target){
                    reached=true;
                    if(point=="cancel_before_close"){cancelled=true;return;}
                    if(point=="deadline_before_close"){std::this_thread::sleep_for(std::chrono::milliseconds(2100));return;}
                    if(point=="nonstandard_after_swap")throw 7;
                    throw std::runtime_error("Declared reached interruption "+point);
                }};
            ProfileStore s(o);observe("WAL source fact",s.acknowledge(newUuid(),newUuid(),"fg:item:000003",1,"2026-09-13T02:45:52Z"),Status::Confirmed);before=snapshot(s,"before");q=prepare(s);
            if(point=="cancel_before_close")q.cancelled=[&]{return cancelled.load();};
            if(point=="deadline_before_close")q.timeout=std::chrono::milliseconds(2000);
            const auto code=point=="cancel_before_close"?"RESTORE_CANCELLED":point=="deadline_before_close"?"RESTORE_DEADLINE":"RESTORE_EXCEPTION";
            auto r=observe("interrupted apply",s.applyRestore(op,q),uncertain?Status::Unresolved:Status::DefiniteFailure,code);check("declared phase reached",reached);check("original operation preserved",r.operation==op&&at(r.data,"operation")==Value(op));
            if(uncertain){
                const auto allocationOp=newUuid();
                // Deliberately invalid payload proves the quarantined allocation job body
                // (including validation/INSERT) is never invoked, not merely rolled back.
                const auto refused=observe("new allocation not admitted before worker execution",s.allocate(allocationOp,"Attempt",Value(nullptr),"2026-09-13T02:45:52Z"),Status::DefiniteFailure,"ALLOCATION_REFUSED_STORE_UNCERTAIN");
                check("preworker refusal exact new operation provenance",refused.operation==allocationOp&&refused.owner.empty()&&at(refused.data,"version")==Value("allocation-refusal.1")&&at(refused.data,"new_allocation")==Value("not_admitted")&&at(refused.data,"job_executed")==Value(false)&&at(refused.data,"store_quarantined")==Value(true));
                observe("ordinary jobs fenced",s.snapshot(newUuid()),Status::Unresolved,"STORE_UNCERTAIN");observe("wrong recovery identity fenced",s.reconcileRestore(newUuid(),q),Status::Unresolved,"STORE_UNCERTAIN");}
            else matches(snapshot(s,"before-recovery"),before,"prebarrier unchanged");
        }
        q.cancelled={};q.timeout=std::chrono::milliseconds(300000);
        ordinaryOpen("fresh-ordinary-open",!uncertain||point=="barrier_retired");
        if(!uncertain){retainedOriginal(before,op,false);check("no swap before barrier",swaps(op)==0);continue;}
        {
            auto o=options();o.restoreRecoveryOperation=op;ProfileStore recovery(o);
            observe("recovery-only ordinary call fenced",recovery.readPreferences(newUuid(),"anything"),Status::Unresolved,"STORE_UNCERTAIN");
            auto wrong=q;wrong.confirmationSha256=std::string(64,'2');observe("conflicting original payload",recovery.reconcileRestore(op,wrong),Status::Unresolved,"RESTORE_CONFLICT");
            auto r=observe("same original native reconcile",recovery.reconcileRestore(op,q),installed?Status::Confirmed:Status::DefinitelyAbsent,installed?"RESTORE_APPLIED":"RESTORE_NOT_APPLIED");
            recordOutcome(r,q,installed?incoming:before,installed);matches(snapshot(recovery,"after"),installed?incoming:before,"reconciled exact state");
            check("reconciliation never swaps",swaps(op)==(installed?1u:0u));check("terminal written/barrier retired",fs::exists(operationDir(op)/"resolved.json")&&!fs::exists(barrier()));
            auto again=observe("repeat terminal reconciliation",recovery.reconcileRestore(op,q),installed?Status::Confirmed:Status::DefinitelyAbsent);check("terminal payload unchanged",again.data==r.data);
        }
        retainedOriginal(before,op,installed);ProfileStore normal(options());matches(snapshot(normal,"normal-after-reconciliation"),installed?incoming:before,"recovered normal reopen");
    }
}
void replacementCases(){
    for(const std::string mode:{"selected-input","install-image","pending-marker","live-after-reopen","retained-original","late-sidecar"}){
        setup("replace-"+mode);const auto op=newUuid();Value before;RestoreApplyRequest q;bool reached=false;
        {
            auto o=options();o.diagnosticHook=[&](const std::string& p,const std::string& id){phase(p,id);
                const auto target=mode=="selected-input"?"restore_apply_before_barrier":mode=="live-after-reopen"?"restore_apply_after_reopen":"restore_apply_before_swap";
                if(!reached&&p==target){reached=true;fs::path file;
                    if(mode=="selected-input")file=root/current/"incoming.zip";
                    if(mode=="install-image"||mode=="retained-original")file=mode=="install-image"?operationDir(op)/"profile.sqlite":root/current/"prepared/candidate.zip";
                    if(mode=="pending-marker")file=barrier();
                    if(mode=="live-after-reopen")file=live();
                    if(mode=="late-sidecar")writeNew(live().string()+"-journal","synthetic unsupported sidecar; never an actual rollback journal");
                    else{auto retained=root/current/"retained-replaced-file";fs::rename(file,retained);copyFixture(retained,file);}
                }};
            ProfileStore s(o);before=snapshot(s,"before");q=prepare(s);auto r=observe("changed namespace refused",s.applyRestore(op,q),mode=="selected-input"?Status::DefiniteFailure:Status::Unresolved,mode=="late-sidecar"?"RESTORE_SIDECARS":"RESTORE_CHANGED");
            check("replacement hook reached",reached);check("not reported applied",r.code!="RESTORE_APPLIED");
            if(mode=="selected-input")matches(snapshot(s,"after-refusal"),before,"selected input refusal");else observe("changed source remains fenced",s.snapshot(newUuid()),Status::Unresolved,"STORE_UNCERTAIN");
        }
        // Changed namespace and synthetic sidecar are retained, never reset to make a pass.
        retainedOriginal(before,op,false);check("no misleading terminal resolution",!fs::exists(operationDir(op)/"resolved.json"));
        writeNew(root/current/"disposition.json",canonical(O{{"status","Unresolved artifacts retained; no automatic retry/rollback"},{"physical_crash","NOT RUN"},{"injected_replacement",mode}}));
    }
}
void acknowledgment(){
    setup("acknowledgment");auto op=newUuid();std::mutex m;std::condition_variable cv;bool entered=false,released=false;
    auto o=options();o.diagnosticHook=[&](const std::string& p,const std::string& id){phase(p,id);if(p=="restore_apply_before_reopen"){std::unique_lock<std::mutex> lock(m);entered=true;cv.notify_one();cv.wait(lock,[&]{return released;});}};
    ProfileStore s(o);auto q=prepare(s);auto future=s.applyRestore(op,q);
    {
        std::unique_lock<std::mutex> lock(m);if(!cv.wait_for(lock,std::chrono::seconds(20),[&]{return entered;})){released=true;cv.notify_one();throw std::runtime_error("Native worker failed to reach declared acknowledgment phase");}
    }
    // Release the worker even when a test assertion throws; no orphaned wait.
    struct Release {std::mutex& m;std::condition_variable& cv;bool& released;~Release(){std::lock_guard<std::mutex> lock(m);released=true;cv.notify_one();}} release{m,cv,released};
    bool competingOwnerOpened=false;std::string leaseRefusal;
    try{ProfileStore competing(options());competingOwnerOpened=true;}
    catch(const std::exception& e){leaseRefusal=e.what();}
    check("continuous ProfileStore lease fences competing owner before restore reopen",
          !competingOwnerOpened&&leaseRefusal.find("already leased by this process")!=std::string::npos);
    traces.emplace_back(O{{"case",current},{"name","competing owner at held restore reopen"},
                          {"opened",competingOwnerOpened},{"refusal",leaseRefusal}});
    auto timeout=ProfileStore::waitForAcknowledgment(future);traces.emplace_back(O{{"case",current},{"name","actual acknowledgment timeout"},{"reply",replyValue(timeout)}});
    check("real ACK_TIMEOUT original future valid",timeout.status==Status::Unresolved&&timeout.code=="ACK_TIMEOUT"&&timeout.operation==op&&future.valid());
    observe("competing write Busy",s.acknowledge(newUuid(),newUuid(),"fg:item:000003",1,"2026-09-13T03:00:00Z"),Status::Busy,"QUEUE_REFUSED");
    {std::lock_guard<std::mutex> lock(m);released=true;cv.notify_one();}
    auto r=observe("original future completion",std::move(future),Status::Confirmed,"RESTORE_APPLIED");check("original operation completion identity",r.operation==op&&swaps(op)==1);
    observe("same operation reconcile after timeout",s.reconcileRestore(op,q),Status::Confirmed,"RESTORE_APPLIED");check("no repeated swap after timeout",swaps(op)==1);
}
}
int main(int argc,char** argv){
    std::string error;try{
        if(argc!=2)throw std::runtime_error("Explicit new lane evidence root required");
        const fs::path evidence=fs::absolute(argv[1]);fixtures=evidence/"fixtures";
        const auto data=evidence/"test-data";directory(data);root=data/"apply01";directory(root);ownsRunDirectory=true;
        successes();refusals();interruptionCases();replacementCases();acknowledgment();
    }catch(const std::exception& e){error=e.what();std::cerr<<"STOP "<<current<<" "<<error<<'\n';}
    catch(...){error="Unexpected non-standard actor exception";std::cerr<<"STOP "<<current<<" "<<error<<'\n';}
    try{if(ownsRunDirectory){
        std::set<std::string> cases;for(const auto& c:checks)cases.insert(at(c,"case").string());
        Value result=O{{"status",error.empty()?"PASS":"FAIL"},{"error",error},{"checks",checks},{"traces",traces},{"phases",phases},
            {"cases",Value::fromInteger(static_cast<std::int64_t>(cases.size()))},{"check_count",Value::fromInteger(static_cast<std::int64_t>(checks.size()))},
            {"measurement_limits","Actual local native API/SQLite/rename/ordinary/fresh-owner opens with synthetic fault hooks; not abrupt process/power loss, actual diskfull, GUI or clean-machine transfer"}};
        writeNew(root/"checks.json",canonical(result));std::cout<<(error.empty()?"PASS ":"FAIL ")<<checks.size()<<" checks / "<<cases.size()<<" cases\n";
    }}catch(const std::exception& e){std::cerr<<"Evidence retention error: "<<e.what()<<'\n';return 2;}
    return error.empty()?0:1;
}
