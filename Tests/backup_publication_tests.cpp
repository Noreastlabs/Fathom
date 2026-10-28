#include "storage/ProfileStore.hpp"
#include "storage/ArchiveReader.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "content/Canonical.hpp"
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <mutex>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>

namespace {
using namespace fathom::storage;namespace fs=std::filesystem;using O=Value::Object;using A=Value::Array;
fs::path root,fixtures;A checks,traces,previews;int sequence=0;
const Value& at(const Value& v,const std::string& k){return v.object().at(k);}
Value num(std::int64_t n){return Value::fromInteger(n);}
std::string read(const fs::path& p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot read "+p.string());return {std::istreambuf_iterator<char>(f),{}};}
void writeNew(const fs::path& p,const std::string& bytes){if(fs::exists(p))throw std::runtime_error("Refuse overwrite "+p.string());std::ofstream f(p,std::ios::binary);f<<bytes;f.close();if(!f)throw std::runtime_error("Write failed");chmod(p.c_str(),0600);}
void directory(const fs::path& p){if(!fs::create_directory(p))throw std::runtime_error("Directory exists");if(chmod(p.c_str(),0700)!=0)throw std::runtime_error("Cannot set private fixture mode");}
void copyFixture(const fs::path& from,const fs::path& to){if(!fs::copy_file(from,to))throw std::runtime_error("Cannot copy fixture");if(chmod(to.c_str(),0600)!=0)throw std::runtime_error("Cannot protect copy");}
void check(const std::string& name,bool pass){checks.emplace_back(O{{"name",name},{"pass",pass}});std::cout<<(pass?"PASS ":"FAIL ")<<name<<'\n';if(!pass)throw std::runtime_error(name);}
std::string sha(const fs::path& p){return fathom::content::sha256(read(p));}
BackupPublicationIdentity identity(const fs::path& p){struct stat s{};if(lstat(p.c_str(),&s)!=0||!S_ISREG(s.st_mode))throw std::runtime_error("Bad identity fixture");return {std::to_string(s.st_dev),std::to_string(s.st_ino),sha(p),static_cast<std::uint64_t>(s.st_size)};}
fs::path profile(const std::string& name,const std::string& kind="rich"){
    auto d=root/(name+"-profile");directory(d);copyFixture(fixtures/kind/"profile.sqlite",d/"profile.sqlite");return d/"profile.sqlite";
}
fs::path targetPath(const std::string& name){auto d=root/(name+"-target");directory(d);return d/"Backup.zip";}
BackupSnapshotOptions options(const std::string& name,const fs::path& target){BackupSnapshotOptions b;b.destinationDirectory=root/(name+"-stage");b.stopped=true;b.unresolvedWrites=false;b.includeArchiveManifest=true;b.includeArchiveContainer=true;BackupPublicationRequest p;p.destination=target;b.publication=p;return b;}
StoreOptions storeOptions(const fs::path& p){StoreOptions o;o.path=p;return o;}
Reply reply(const std::string& name,ProfileStore::Future future,Status expected,const std::string& code=""){
    auto r=future.get();traces.emplace_back(O{{"case",name},{"operation",r.operation},{"owner",r.owner},{"status",statusName(r.status)},{"code",r.code},{"message",r.message},{"data",r.data}});
    check(name+" status",r.status==expected);if(!code.empty())check(name+" code",r.code==code);return r;
}
Value snapshot(ProfileStore& store,const std::string& name){return reply(name,store.snapshot(newUuid()),Status::Confirmed).data;}
void preserved(ProfileStore& store,const Value& before,const std::string& name){auto after=snapshot(store,name+" after");check(name+" full source authority unchanged",at(before,"authoritative")==at(after,"authoritative"));check(name+" source owner unchanged",at(before,"profile_id")==at(after,"profile_id"));}
fs::path pointer(const BackupSnapshotOptions& b){return b.publication->destination.parent_path()/".fathom-backup-publication.pending.json";}
void preview(const fs::path& archive,const std::string& name){ArchiveReaderOptions r;r.archive=archive;r.candidateDirectory=root/(name+"-preview-"+std::to_string(++sequence));auto v=previewProfileArchive(r);check(name+" archive independently readable",at(v,"candidate_validated")==Value(true)&&at(v,"restore_performed")==Value(false));previews.emplace_back(v);}
void successful(){
    auto target=targetPath("main");std::string firstOp=newUuid();
    {
        ProfileStore store(storeOptions(profile("first","empty")));auto before=snapshot(store,"first before");auto b=options("first",target);
        auto r=reply("EXCL first",store.prepareBackupSnapshot(firstOp,b),Status::Confirmed,"BACKUP_PUBLISHED");
        check("EXCL target matches receipt",sha(target)==at(at(at(r.data,"archive"),"file"),"sha256").string());
        check("EXCL moved stage and retained barrier",!fs::exists(b.destinationDirectory/"candidate.zip")&&fs::exists(pointer(b)));
        check("EXCL explicit stopped/no restore",at(r.data,"archive_published")==Value(true)&&at(r.data,"restore_performed")==Value(false)&&at(r.data,"required_resume_state")==Value("stopped"));
        auto blocked=options("first-blocked",target);blocked.publication->expected=identity(target);
        auto denied=reply("pending original blocks new attempt",store.prepareBackupSnapshot(newUuid(),blocked),Status::DefiniteFailure,"PUBLICATION_PENDING");
        check("pending original identity exposed",at(at(at(denied.data,"publication"),"pending_operation"),"operation")==Value(firstOp)&&at(denied.data,"archive_published")==Value(false));
        auto alias=options("case-alias-blocked",target.parent_path()/"backup.zip");alias.publication->expected=identity(target);
        const bool actualAlias=fs::exists(alias.publication->destination)&&fs::equivalent(target,alias.publication->destination);
        auto aliasDenied=reply("case variant uses directory barrier",store.prepareBackupSnapshot(newUuid(),alias),Status::DefiniteFailure,"PUBLICATION_PENDING");
        check("case variant retains original operation",at(at(at(aliasDenied.data,"publication"),"pending_operation"),"operation")==Value(firstOp));
        traces.emplace_back(O{{"case","filesystem name equivalence"},{"original",target.string()},{"case_variant",alias.publication->destination.string()},{"same_native_file",actualAlias},{"policy","Directory-wide barrier applies independently of case/Unicode normalization"}});
        auto reconciled=reply("EXCL original reconcile",store.reconcileBackupPublication(firstOp,b),Status::Confirmed,"BACKUP_PUBLISHED");
        check("original reconciliation ownership",reconciled.operation==firstOp&&Value(reconciled.owner)==at(before,"profile_id"));
        reply("EXCL repeat same original reconcile",store.reconcileBackupPublication(firstOp,b),Status::Confirmed,"BACKUP_PUBLISHED");
        check("resolved still discoverable",fs::exists(pointer(b))&&fs::exists(b.destinationDirectory/"publication-resolved.json"));
        preserved(store,before,"first");preview(target,"first");
    }
    const auto old=identity(target);
    {
        ProfileStore store(storeOptions(profile("replacement")));auto before=snapshot(store,"replacement before");auto b=options("replacement",target);
        b.publication->expected=old;b.publication->reconciledPredecessor=firstOp;const auto op=newUuid();
        auto r=reply("SWAP exact old",store.prepareBackupSnapshot(op,b),Status::Confirmed,"BACKUP_PUBLISHED");
        check("SWAP new rich archive differs",sha(target)!=old.sha256&&sha(target)==at(at(at(r.data,"archive"),"file"),"sha256").string());
        const auto retained=identity(b.destinationDirectory/"candidate.zip");
        check("SWAP old bytes and inode retained",retained.sha256==old.sha256&&retained.inode==old.inode&&retained.device==old.device);
        check("predecessor pointer retained before handoff",fs::exists(root/"first-stage"/"publication-resolved-pointer.json"));
        reply("SWAP same operation reconcile",store.reconcileBackupPublication(op,b),Status::Confirmed,"BACKUP_PUBLISHED");
        preserved(store,before,"replacement");preview(target,"replacement");preview(b.destinationDirectory/"candidate.zip","retained-old");
    }
}
void refusals(){
    for(const std::string mode:{"existing","stale","symlink","live-path","live-alias","stage-live-alias","reserved-alias","stage-path","missing-container","stopped","unresolved"}){
        auto source=profile(mode);ProfileStore store(storeOptions(source));auto before=snapshot(store,mode+" before");auto target=targetPath(mode);auto b=options(mode,target);
        std::string code;Status status=Status::DefiniteFailure;std::string old;
        if(mode=="existing"||mode=="stale"){copyFixture(fixtures/"empty"/"candidate.zip",target);old=sha(target);code=mode=="existing"?"PUBLICATION_EXISTS":"PUBLICATION_STALE";}
        if(mode=="stale"){b.publication->expected=identity(target);b.publication->expected->sha256=std::string(64,'0');}
        if(mode=="symlink"){auto victim=root/"symlink-victim.zip";copyFixture(fixtures/"empty"/"candidate.zip",victim);old=sha(victim);fs::create_symlink(victim,target);b.publication->expected=identity(victim);code="PUBLICATION_PATH";}
        if(mode=="live-path"){b.publication->destination=source;b.publication->expected=identity(source);code="PUBLICATION_PATH";}
        if(mode=="live-alias"){
            b.publication->destination=source.parent_path().parent_path()/"LIVE-ALIAS-PROFILE"/"profile.sqlite";b.publication->expected=identity(source);code="PUBLICATION_PATH";
            const bool actual=fs::exists(b.publication->destination)&&fs::equivalent(source,b.publication->destination);
            traces.emplace_back(O{{"case","protected native case alias"},{"actual_same_file",actual},{"source",source.string()},{"alias",b.publication->destination.string()}});
        }
        if(mode=="stage-live-alias"){b.destinationDirectory=source.parent_path().parent_path()/"STAGE-LIVE-ALIAS-PROFILE"/"backup-stage";code="PUBLICATION_PATH";}
        if(mode=="reserved-alias"){b.publication->destination=target.parent_path()/".FATHOM-BACKUP-PUBLICATION.LOCK";code="PUBLICATION_PATH";}
        if(mode=="stage-path"){b.publication->destination=b.destinationDirectory/"manifest.json";code="PUBLICATION_PATH";}
        if(mode=="missing-container"){b.includeArchiveContainer=false;code="PUBLICATION_CONTAINER_REQUIRED";}
        if(mode=="stopped"||mode=="unresolved"){b.stopped=mode!="stopped";b.unresolvedWrites=mode=="unresolved";status=Status::Busy;code="QUIESCENCE_REQUIRED";}
        reply(mode,store.prepareBackupSnapshot(newUuid(),b),status,code);
        if(!old.empty())check(mode+" selected/victim bytes retained",sha(mode=="symlink"?root/"symlink-victim.zip":target)==old);
        if(mode=="symlink")check("selected symlink retained",fs::is_symlink(target));
        if(mode!="existing"&&mode!="stale"&&mode!="symlink")check(mode+" refused before stage",!fs::exists(b.destinationDirectory));
        preserved(store,before,mode);
    }
}
void faults(){
    for(const std::string mode:{"corrupt-before","replace-before","prior-replace-before","stage-replace-before","cancel-before","deadline-before","sync-error","cancel-after","target-replace-at-ack","reconcile-replace-at-ack","wrong-profile","cancel-reconcile","target-lease","chmod-after"}){
        auto source=profile(mode);auto target=targetPath(mode);copyFixture(fixtures/"empty"/"candidate.zip",target);const auto old=identity(target);
        auto b=options(mode,target);b.publication->expected=old;const auto op=newUuid();auto o=storeOptions(source);
        bool reached=false,reconcilePhase=false,leaseRefused=false;std::atomic<bool> cancelled{false};A phases;
        if(mode=="deadline-before")b.timeout=std::chrono::milliseconds(5000);
        b.cancelled=[&]{return cancelled.load();};
        o.diagnosticHook=[&](const std::string& phase,const std::string& hookOp){
            if(phase.rfind("publication_",0)==0)phases.emplace_back(O{{"phase",phase},{"operation",hookOp}});
            const auto archive=b.destinationDirectory/"candidate.zip";
            if(mode=="chmod-after"&&phase=="publication_after_rename"){reached=true;if(chmod(target.c_str(),0644)!=0)throw std::runtime_error("Cannot inject mode change");}
            if(phase=="publication_before_rename"){
                if(mode=="corrupt-before"){reached=true;int fd=open(archive.c_str(),O_WRONLY|O_NOFOLLOW);if(fd<0||pwrite(fd,"X",1,0)!=1)throw std::runtime_error("Fault injection failed");close(fd);}
                if(mode=="replace-before"){reached=true;fs::rename(archive,b.destinationDirectory/"original-candidate.zip");copyFixture(b.destinationDirectory/"original-candidate.zip",archive);}
                if(mode=="prior-replace-before"){reached=true;fs::rename(target,root/(mode+"-original.zip"));copyFixture(root/(mode+"-original.zip"),target);}
                if(mode=="stage-replace-before"){reached=true;fs::rename(b.destinationDirectory,root/(mode+"-retained-stage"));directory(b.destinationDirectory);}
            }
            if(phase=="publication_intent_retained"){
                if(mode=="cancel-before"){reached=true;cancelled=true;}
                if(mode=="deadline-before"){reached=true;std::this_thread::sleep_for(std::chrono::milliseconds(5100));}
                if(mode=="target-lease"){
                    reached=true;try{auto request=*b.publication;request.destination=target.parent_path()/"backup.zip";BackupPublisher competing(newUuid(),request,root/"unused-stage",[]{});}
                    catch(const EnvelopeError& e){leaseRefused=e.code=="PUBLICATION_TARGET_BUSY";}
                }
            }
            if(phase=="publication_before_directory_sync"&&!reconcilePhase){
                if(mode=="sync-error"||mode=="reconcile-replace-at-ack"||mode=="wrong-profile"||mode=="cancel-reconcile"){reached=true;throw EnvelopeError("PUBLICATION_SYNC","Injected directory-sync failure before syscall; not a power-loss test");}
                if(mode=="cancel-after"){reached=true;cancelled=true;}
            }
            if((mode=="target-replace-at-ack"&&phase=="publication_before_acknowledgment")||
               (mode=="reconcile-replace-at-ack"&&phase=="publication_reconcile_before_acknowledgment")){
                reached=true;fs::rename(target,root/(mode+"-displaced-new.zip"));copyFixture(fixtures/"empty"/"candidate.zip",target);
            }
        };
        ProfileStore store(o);auto before=snapshot(store,mode+" before");
        const bool pre=mode=="corrupt-before"||mode=="replace-before"||mode=="prior-replace-before"||mode=="stage-replace-before"||mode=="cancel-before"||mode=="deadline-before";
        const bool success=mode=="target-lease";
        const auto expectedStatus=success?Status::Confirmed:pre?Status::DefiniteFailure:Status::Unresolved;
        const std::string expectedCode=success?"BACKUP_PUBLISHED":(mode=="cancel-before"||mode=="cancel-after")?"ARCHIVE_CANCELLED":mode=="deadline-before"?"ARCHIVE_DEADLINE":mode=="stage-replace-before"?"ARCHIVE_CHANGED":
            (mode=="sync-error"||mode=="reconcile-replace-at-ack"||mode=="wrong-profile"||mode=="cancel-reconcile")?"PUBLICATION_SYNC":"PUBLICATION_CHANGED";
        auto r=reply(mode,store.prepareBackupSnapshot(op,b),expectedStatus,expectedCode);
        check(mode+" fault actually reached",reached);
        check(mode+" publication truth",at(r.data,"archive_published")== (success?Value(true):pre?Value(false):Value(nullptr)));
        check(mode+" original operation retained",r.operation==op&&at(at(r.data,"publication"),"operation")==Value(op));
        if(!pre&&!success)check(mode+" unresolved barrier retained",fs::exists(pointer(b)));
        if(pre)check(mode+" old backup bytes unchanged by operation",sha(target)==old.sha256);
        else check(mode+" old backup retained",sha(b.destinationDirectory/"candidate.zip")==old.sha256);
        cancelled=false;reconcilePhase=true;b.timeout=std::chrono::milliseconds(300000);
        if(mode=="cancel-before"||mode=="deadline-before")reply(mode+" unchanged original reconcile",store.reconcileBackupPublication(op,b),Status::DefinitelyAbsent,"BACKUP_NOT_PUBLISHED");
        if(mode=="sync-error"||mode=="cancel-after"||mode=="target-lease"){
            if(mode=="sync-error"){
                reply("different operation cannot reconcile",store.reconcileBackupPublication(newUuid(),b),Status::Unresolved,"PUBLICATION_CONFLICT");
                auto conflict=b;conflict.publication->expected->sha256=std::string(64,'0');
                reply("conflicting original payload cannot reconcile",store.reconcileBackupPublication(op,conflict),Status::Unresolved,"PUBLICATION_CONFLICT");
                check("wrong key/payload preserve original unresolved barrier",fs::exists(pointer(b))&&!fs::exists(b.destinationDirectory/"publication-resolved.json"));
            }
            reply(mode+" original reconcile",store.reconcileBackupPublication(op,b),Status::Confirmed,"BACKUP_PUBLISHED");preview(target,mode);preview(b.destinationDirectory/"candidate.zip",mode+"-old");
        }
        if(mode=="target-lease")check("concurrent same-target native flock refusal",leaseRefused);
        if(mode=="chmod-after"){
            reply("changed permissions remain unresolved",store.reconcileBackupPublication(op,b),Status::Unresolved,"PUBLICATION_CHANGED");
            check("changed permissions keep original barrier",fs::exists(pointer(b))&&!fs::exists(b.destinationDirectory/"publication-resolved.json"));
        }
        if(mode=="target-replace-at-ack"||mode=="reconcile-replace-at-ack"){
            const auto code=mode=="target-replace-at-ack"?"PUBLICATION_CONFLICT":"PUBLICATION_CHANGED";
            reply(mode+" conflicting original reconcile",store.reconcileBackupPublication(op,b),Status::Unresolved,code);
            check(mode+" actual new/old/conflict files retained",fs::exists(root/(mode+"-displaced-new.zip"))&&fs::exists(pointer(b))&&!fs::exists(b.destinationDirectory/"publication-resolved.json"));
        }
        if(mode=="wrong-profile"){
            ProfileStore other(storeOptions(profile("wrong-owner","empty")));auto prior=snapshot(other,"wrong-owner before");
            reply("wrong owner original reconciliation",other.reconcileBackupPublication(op,b),Status::Unresolved,"PUBLICATION_CONFLICT");
            check("wrong owner cannot resolve original",!fs::exists(b.destinationDirectory/"publication-resolved.json"));preserved(other,prior,"wrong-owner");
            reply("right owner original reconciliation",store.reconcileBackupPublication(op,b),Status::Confirmed,"BACKUP_PUBLISHED");
        }
        if(mode=="cancel-reconcile"){
            cancelled=true;auto c=reply("cancel during reconciliation construction",store.reconcileBackupPublication(op,b),Status::Unresolved,"ARCHIVE_CANCELLED");
            check("constructor uncertainty retains paths",at(c.data,"archive_published").null()&&at(c.data,"operation")==Value(op)&&at(c.data,"destination")==Value(target.string()));
            cancelled=false;reply("original after cancelled reconciliation",store.reconcileBackupPublication(op,b),Status::Confirmed,"BACKUP_PUBLISHED");
        }
        preserved(store,before,mode);traces.emplace_back(O{{"case",mode},{"actual_phases",phases},{"original_operation",op}});
    }
}
void acknowledgment(){
    const std::string mode="ack-timeout";auto target=targetPath(mode);auto b=options(mode,target);auto o=storeOptions(profile(mode));const auto op=newUuid();
    std::mutex mutex;std::condition_variable cv;bool reached=false,released=false;A phases;
    o.diagnosticHook=[&](const std::string& phase,const std::string&){
        if(phase.rfind("publication_",0)==0)phases.emplace_back(phase);
        if(phase=="publication_before_acknowledgment"){
            std::unique_lock<std::mutex> lock(mutex);reached=true;cv.notify_all();
            if(!cv.wait_for(lock,std::chrono::seconds(10),[&]{return released;}))throw EnvelopeError("ACTOR_DEADLINE","Bounded acknowledgment gate expired");
        }
    };
    ProfileStore store(o);auto before=snapshot(store,"ack before");auto future=store.prepareBackupSnapshot(op,b);
    {std::unique_lock<std::mutex> lock(mutex);check("ack reached native postrename gate",cv.wait_for(lock,std::chrono::seconds(10),[&]{return reached;}));}
    const auto observed=ProfileStore::waitForAcknowledgment(future);
    check("actual acknowledgment timeout preserves original future",observed.status==Status::Unresolved&&observed.code=="ACK_TIMEOUT"&&observed.operation==op&&future.valid());
    auto blocked=store.snapshot(newUuid());
    auto busy=blocked.get();check("same-job maintenance excludes competing writer",busy.status==Status::Busy);
    {std::lock_guard<std::mutex> lock(mutex);released=true;cv.notify_all();}
    reply("original future after timeout",std::move(future),Status::Confirmed,"BACKUP_PUBLISHED");
    reply("same-key after timeout",store.reconcileBackupPublication(op,b),Status::Confirmed,"BACKUP_PUBLISHED");
    check("timeout did not allocate another archive",!fs::exists(b.destinationDirectory/"candidate.zip")&&fs::exists(pointer(b)));
    preserved(store,before,"ack");preview(target,"ack");traces.emplace_back(O{{"case",mode},{"actual_phases",phases},{"timeout_status",statusName(observed.status)},{"timeout_code",observed.code},{"operation",op}});
}
void historyAndVersion(){
    auto target=targetPath("history");auto b=options("history",target);ProfileStore store(storeOptions(profile("history","empty")));const auto op=newUuid();
    auto created=reply("history initial publication",store.prepareBackupSnapshot(op,b),Status::Confirmed,"BACKUP_PUBLISHED");const auto originalBytes=sha(target);
    reply("explicit synthetic later acknowledgment",store.acknowledge(newUuid(),newUuid(),"fg:item:000003",1,"2026-09-07T18:00:00Z"),Status::Confirmed);
    const auto current=snapshot(store,"history after explicit new fact");
    check("later marker differs from original backup",at(current,"committed_seq")!=at(created.data,"committed_seq"));
    reply("original reconciliation permits newer history",store.reconcileBackupPublication(op,b),Status::Confirmed,"BACKUP_PUBLISHED");
    preserved(store,current,"later-history reconcile");check("later history did not rewrite original archive",sha(target)==originalBytes);
    // New synthetic fault, never a modification to frozen evidence: all three
    // operation records are retained before a hash-consistent version mutation.
    for(const char* filename:{"publication-intent.json","publication-resolved.json"})
        fs::rename(b.destinationDirectory/filename,b.destinationDirectory/(std::string(filename)+".original"));
    auto intent=parseCanonical(read(b.destinationDirectory/"publication-intent.json.original"));intent.object().at("version")=num(2);const auto bytes=canonical(intent);
    writeNew(b.destinationDirectory/"publication-intent.json",bytes);
    const auto pp=pointer(b);fs::rename(pp,b.destinationDirectory/"target-pointer.original.json");
    auto pointerValue=parseCanonical(read(b.destinationDirectory/"target-pointer.original.json"));pointerValue.object().at("intent_sha256")=fathom::content::sha256(bytes);writeNew(pp,canonical(pointerValue));
    auto marker=parseCanonical(read(b.destinationDirectory/"publication-resolved.json.original"));marker.object().at("intent_sha256")=fathom::content::sha256(bytes);writeNew(b.destinationDirectory/"publication-resolved.json",canonical(marker));
    auto next=options("unsupported-predecessor",target);next.publication->expected=identity(target);next.publication->reconciledPredecessor=op;
    reply("hash-consistent unsupported predecessor refused",store.prepareBackupSnapshot(newUuid(),next),Status::DefiniteFailure,"PUBLICATION_CONFLICT");
    check("unsupported predecessor leaves barrier and target intact",fs::exists(pp)&&sha(target)==originalBytes);
    preserved(store,current,"unsupported-predecessor");
}
}
int main(int argc,char** argv){
    if(argc!=2){std::cerr<<"Usage: backup_publication_tests /absolute/E\n";return 64;}
    bool owned=false,passed=false;
    try{auto evidence=fs::canonical(argv[1]);fixtures=evidence/"fixtures";root=evidence/"test-data"/"publication01";
        if(fs::exists(root))throw std::runtime_error("No run overwrite");
        fs::create_directories(root.parent_path());chmod(root.parent_path().c_str(),0700);directory(root);owned=true;
        successful();refusals();faults();acknowledgment();historyAndVersion();passed=true;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(owned)writeNew(root/"failure.txt",e.what());}
    if(owned)writeNew(root/"checks.json",canonical(O{{"status",passed?"PASS":"FAIL"},{"synthetic",true},{"human_work",false},{"restore_performed",false},{"checks",checks},{"trace",traces},{"previews",previews},
        {"not_run",A{"Actual cross-volume publication: no second authorized writable filesystem within probe surfaces","Kernel/power-loss/disk-full failure: hooks establish exception boundaries only","UI, clean-install transfer and live restore"}}}));
    std::cout<<checks.size()<<" checks "<<(passed?"PASS":"FAIL")<<'\n';return passed?0:1;
}
