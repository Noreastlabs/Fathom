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
#include <set>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>

namespace {
using namespace fathom::storage;namespace fs=std::filesystem;using O=Value::Object;using A=Value::Array;
fs::path root,fixtures;A checks,traces;std::string current;
const Value& at(const Value& v,const std::string& k){return v.object().at(k);}
std::string read(const fs::path& p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot read "+p.string());return {std::istreambuf_iterator<char>(f),{}};}
void writeNew(const fs::path& p,const std::string& bytes){if(fs::exists(p))throw std::runtime_error("No overwrite "+p.string());std::ofstream f(p,std::ios::binary);f<<bytes;f.close();if(!f||chmod(p.c_str(),0600)!=0)throw std::runtime_error("Write/protection failed");}
void directory(const fs::path& p){if(!fs::create_directory(p)||chmod(p.c_str(),0700)!=0)throw std::runtime_error("New private directory required");}
void copyFixture(const fs::path& from,const fs::path& to){if(!fs::copy_file(from,to)||chmod(to.c_str(),0600)!=0)throw std::runtime_error("Copy failed");}
void check(const std::string& n,bool ok){checks.emplace_back(O{{"case",current},{"name",n},{"pass",ok}});std::cout<<(ok?"PASS ":"FAIL ")<<current<<" "<<n<<'\n';if(!ok)throw std::runtime_error(n);}
std::string sha(const fs::path& p){return fathom::content::sha256(read(p));}
StoreOptions storeOptions(const fs::path& path){StoreOptions o;o.path=path;return o;}
Value replyValue(const Reply& r){return O{{"status",statusName(r.status)},{"operation",r.operation},{"owner",r.owner},{"code",r.code},{"message",r.message},{"data",r.data}};}
Reply observe(const std::string& name,ProfileStore::Future f,Status status,const std::string& code=""){
    auto r=f.get();traces.emplace_back(O{{"case",current},{"name",name},{"reply",replyValue(r)}});check(name+" status",r.status==status);if(!code.empty())check(name+" code",r.code==code);return r;
}
Value snapshot(ProfileStore& s,const std::string& suffix){auto r=s.snapshot(newUuid()).get();check(suffix+" snapshot confirmed",r.status==Status::Confirmed);writeNew(root/current/(suffix+".json"),canonical(r.data));return r.data;}
void unchanged(ProfileStore& s,const Value& before){auto after=snapshot(s,"after");check("source exact13table authority unchanged",at(after,"authoritative")==at(before,"authoritative"));check("source original profile retained",at(after,"profile_id")==at(before,"profile_id"));}
void setup(const std::string& name,const std::string& liveKind="empty",const std::string& incomingKind="rich"){
    current=name;directory(root/name);directory(root/name/"live");copyFixture(fixtures/liveKind/"profile.sqlite",root/name/"live/profile.sqlite");copyFixture(fixtures/incomingKind/"candidate.zip",root/name/"incoming.zip");
}
BackupSnapshotOptions options(){BackupSnapshotOptions o;o.destinationDirectory=root/current/"stage";o.stopped=true;o.unresolvedWrites=false;return o;}
RestorePreparationRequest request(){RestorePreparationRequest r;r.archive=root/current/"incoming.zip";return r;}
Value available(){auto m=parseCanonical(read(fixtures/"rich/manifest.json"));auto r=at(at(m,"snapshot"),"content_references").array().front();r.object().erase("reference_kind");return A{O{{"reference",r},{"provenance","Retained accepted control-examples.1 metadata; these examples do not establish runtime admission"}}};}
void reopened(const fs::path& source,const Value& expected,const std::string& name){
    auto dest=root/current/name;directory(dest);copyFixture(source,dest/"profile.sqlite");ProfileStore s(storeOptions(dest/"profile.sqlite"));auto r=s.snapshot(newUuid()).get();check(name+" native normal reopen",r.status==Status::Confirmed);writeNew(dest/"snapshot.json",canonical(r.data));
    check(name+" exact authority",at(r.data,"authoritative")==at(expected,"authoritative"));check(name+" original profile identity",at(r.data,"profile_id")==at(expected,"profile_id"));
}
Value fixtureSnapshot(const std::string& kind){auto dest=root/current/(kind+"-expected");directory(dest);copyFixture(fixtures/kind/"profile.sqlite",dest/"profile.sqlite");ProfileStore s(storeOptions(dest/"profile.sqlite"));auto r=s.snapshot(newUuid()).get();check("incoming expected native inspection",r.status==Status::Confirmed);writeNew(dest/"snapshot.json",canonical(r.data));return r.data;}
void successes(){
    for(const std::string mode:{"rich-to-empty","empty-to-rich"}){
        const bool rich=mode=="rich-to-empty";setup(mode,rich?"empty":"rich",rich?"rich":"empty");const auto path=root/current/"live/profile.sqlite";Value before;std::string archiveBefore=sha(root/current/"incoming.zip");
        {
            ProfileStore s(storeOptions(path));
            if(rich){observe("actual WAL acknowledgment",s.acknowledge(newUuid(),newUuid(),"fg:item:000003",1,"2026-09-13T02:00:00Z"),Status::Confirmed);
                check("actual committed WAL exists",fs::exists(path.string()+"-wal")&&fs::file_size(path.string()+"-wal")>0);}
            before=snapshot(s,"before");auto q=request();q.availableReferences=available();auto b=options();const auto op=newUuid();
            auto r=observe("prepare",s.prepareRestore(op,b,q),Status::Confirmed,"RESTORE_PREPARED");
            const auto& prep=at(r.data,"restore_preparation");const auto& record=at(prep,"record");const auto& body=at(record,"preview");
            check("exact confirmation digest",at(record,"confirmation_sha256")==Value(fathom::content::sha256(canonical(body))));
            check("saved preview exact",read(b.destinationDirectory/"restore-preview.json")==canonical(record));
            check("saved receipt identity",sha(b.destinationDirectory/"restore-preview.json")==at(at(prep,"file"),"sha256").string());
            check("explicit not applied/not confirmed",at(body,"restore_performed")==Value(false)&&at(body,"user_confirmed")==Value(false)&&at(body,"confirmation_required")==Value(true)&&at(prep,"prepared")==Value(true));
            check("stopped return",at(body,"required_resume_state")==Value("stopped"));check("original op/profile owner",r.operation==op&&Value(r.owner)==at(before,"profile_id")&&at(body,"operation")==Value(op));
            check("intended live path",at(body,"live_profile_path")==Value(path.string()));
            const auto& recovery=at(body,"recoverable_original");const auto& incoming=at(body,"incoming");
            check("live and incoming distinct",at(at(at(incoming,"manifest"),"snapshot"),"profile_id")!=at(before,"profile_id"));
            check("recovery exact live manifest",at(recovery,"manifest")==at(body,"live_boundary"));
            check("WAL/source marker retained",at(at(at(recovery,"manifest"),"snapshot"),"marker")==at(before,"committed_seq"));
            const auto& continuity=at(body,"content_compatibility");check("no admission inference",at(continuity,"runtime_admission")==Value("NOT ASSESSED")&&at(continuity,"latest_substitution")==Value(false));
            if(rich){const auto& refs=at(continuity,"references").array();check("three distinct historical reference forms",refs.size()==3);std::set<std::string> states;for(const auto& v:refs)states.insert(at(v,"status").string());check("exact missing partial distinct",states==std::set<std::string>{"exact_metadata_reference_present","historical_reference_unavailable","partial_original_identity"});}
            else check("empty history not invented",at(continuity,"references").array().empty());
            const auto expected=fixtureSnapshot(rich?"rich":"empty");
            reopened(b.destinationDirectory/"incoming/profile.sqlite",expected,"incoming-reopen");
            reopened(b.destinationDirectory/"recovery-readback/profile.sqlite",before,"original-reopen");
            unchanged(s,before);check("incoming archive unchanged",sha(q.archive)==archiveBefore);
            observe("repeat operation does not recreate preview",s.prepareRestore(op,b,q),Status::DefiniteFailure,"SNAPSHOT_DESTINATION_EXISTS");
        }
        ProfileStore s(storeOptions(path));auto after=snapshot(s,"normal-live-reopen");check("normal live reopen exact history",at(after,"authoritative")==at(before,"authoritative"));
    }
}
void sealedSourceMutation(){
    setup("sealed-source-mutation");
    const auto live=root/current/"live/profile.sqlite";
    const auto external=root/current/"incoming.zip";
    const auto originalSha=sha(external);
    const auto selectedRoot=root/current/".restore-selected-test";
    directory(selectedRoot);
    const auto selected=selectedRoot/"selected.zip";
    copyFixture(external,selected);
    auto identity=[&](const fs::path& path){struct stat state{};check("source identity stat",lstat(path.c_str(),&state)==0&&S_ISREG(state.st_mode));
        return Value(O{{"device",std::to_string(state.st_dev)},{"inode",std::to_string(state.st_ino)},
                       {"bytes",Value::fromInteger(state.st_size)},{"sha256",sha(path)}});};
    Value origin=O{{"format","Fathom.SealedArchiveSource"},{"version",Value::fromInteger(1)},
        {"source_archive_path",external.string()},{"source_archive_file",identity(external)},
        {"snapshot_archive_path",selected.string()},{"snapshot_archive_file",identity(selected)},
        {"copied_snapshot_semantics",true}};
    writeNew(selectedRoot/"origin.json",canonical(origin));
    bool changed=false;
    auto so=storeOptions(live);
    so.diagnosticHook=[&](const std::string& phase,const std::string&){
        if(phase=="backup_before_source_validation"){
            changed=true;
            int fd=open(external.c_str(),O_WRONLY|O_NOFOLLOW);
            if(fd<0||ftruncate(fd,fs::file_size(external)-1)!=0){if(fd>=0)close(fd);throw std::runtime_error("Cannot inject external archive mutation");}
            close(fd);
        }
    };
    Value sourceBefore;
    {
        ProfileStore store(so);
        sourceBefore=snapshot(store,"before");
        const auto rawBefore=sha(live);
        auto restore=request();restore.archive=selected;restore.availableReferences=available();
        auto backup=options();
        const auto prepared=observe("sealed snapshot prepare after external mutation",
            store.prepareRestore(newUuid(),backup,restore),Status::Confirmed,"RESTORE_PREPARED");
        check("external source mutation reached preparation",changed&&sha(external)!=originalSha);
        check("sealed archive bytes retain original source",sha(selected)==originalSha);
        check("preparation leaves raw live profile bytes intact",sha(live)==rawBefore);
        const auto& receipt=at(prepared.data,"restore_preparation");
        const auto& record=at(receipt,"record");
        const auto& body=at(record,"preview");
        check("preview binds original source path and sealed identity",
            at(at(at(body,"source_archive"),"record"),"source_archive_path")==Value(external.string())&&
            at(at(at(body,"source_archive"),"record"),"snapshot_archive_file")==identity(selected));
        RestoreApplyRequest apply;
        apply.preview=backup.destinationDirectory/"restore-preview.json";
        apply.previewFile=at(receipt,"file");
        apply.confirmationSha256=at(record,"confirmation_sha256").string();
        apply.availableReferences=restore.availableReferences;
        apply.explicitConfirmation=true;apply.stopped=true;apply.unresolvedWrites=false;
        const auto applied=observe("sealed snapshot apply despite external mutation",
            store.applyRestore(newUuid(),apply),Status::Confirmed,"RESTORE_APPLIED");
        check("apply installs incoming source identity",
            at(at(applied.data,"snapshot"),"profile_id")!=at(sourceBefore,"profile_id"));
    }
    ProfileStore reopenedStore(storeOptions(live));
    const auto reopenedState=snapshot(reopenedStore,"normal-reopen");
    check("sealed snapshot normal reopen preserves installed identity",
        at(reopenedState,"profile_id")!=at(sourceBefore,"profile_id"));
}
void changedContent(){
    setup("changed-content");ProfileStore s(storeOptions(root/current/"live/profile.sqlite"));auto before=snapshot(s,"before");auto q=request();q.availableReferences=available();
    q.availableReferences.array()[0].object().at("reference").object().at("content_revision")=Value::fromInteger(2);
    auto r=observe("changed version preview",s.prepareRestore(newUuid(),options(),q),Status::Confirmed,"RESTORE_PREPARED");
    const auto& body=at(at(at(r.data,"restore_preparation"),"record"),"preview");const auto& refs=at(at(body,"content_compatibility"),"references").array();
    std::size_t missing=0;for(const auto& ref:refs){if(at(ref,"status")==Value("historical_reference_unavailable"))++missing;
        check("no current version substituted",at(at(ref,"original_reference"),"content_revision")==Value::fromInteger(1));}
    check("same item with different revision stays unavailable",missing==2);
    check("changed selection has distinct exact identity",at(body,"available_metadata_sha256")==Value(fathom::content::sha256(canonical(q.availableReferences))));unchanged(s,before);
}
void refusals(){
    for(const std::string mode:{"running","unresolved","publication","duplicate-metadata","malformed-metadata","unknown-admission-metadata","unfinished","live-alias","stage-alias","invalid-operation"}){
        setup(mode);auto o=options();auto q=request();std::string code;Status status=Status::DefiniteFailure;auto op=newUuid();
        if(mode=="running"||mode=="unresolved"){o.stopped=mode!="running";o.unresolvedWrites=mode=="unresolved";status=Status::Busy;code="QUIESCENCE_REQUIRED";}
        if(mode=="publication"){BackupPublicationRequest p;p.destination=root/current/"out.zip";o.publication=p;code="RESTORE_OPTIONS";}
        if(mode=="duplicate-metadata"){q.availableReferences=available();q.availableReferences.array().push_back(q.availableReferences.array().front());code="RESTORE_CONTENT";}
        if(mode=="malformed-metadata"){q.availableReferences=available();q.availableReferences.array()[0].object().at("reference").object().at("variant_id")="wrong";code="RESTORE_CONTENT";}
        if(mode=="unknown-admission-metadata"){q.availableReferences=available();q.availableReferences.array()[0].object().emplace("runtime_admitted",true);code="RESTORE_CONTENT";}
        if(mode=="live-alias"){q.archive=root/current/"LIVE/profile.sqlite";code="PUBLICATION_PATH";}
        if(mode=="stage-alias"){o.destinationDirectory=root/current/"LIVE/stage";code="PUBLICATION_PATH";}
        if(mode=="invalid-operation"){op="not-an-original-uuid";code="INVALID_ENVELOPE";}
        ProfileStore s(storeOptions(root/current/"live/profile.sqlite"));
        if(mode=="unfinished"){
            // Existing immutable accepted fixture context; only the new disposable allocation is authored here.
            auto expected=fixtureSnapshot("rich");const auto& rows=at(at(expected,"authoritative"),"identity").array();const auto& row=rows.front().array();auto hex=at(row[4],"blob_hex").string();std::string bytes;
            for(std::size_t i=0;i<hex.size();i+=2)bytes.push_back(static_cast<char>(std::stoi(hex.substr(i,2),nullptr,16)));
            auto context=parseCanonical(bytes);const auto kind=row[1].string();
            if(kind=="Attempt"){auto session=observe("new synthetic session",s.createSession(newUuid(),"2026-09-13T02:00:00Z","UTC"),Status::Confirmed);context.object().at("session_id")=at(session.data,"session_id");}
            observe("actual unfinished allocation",s.allocate(newUuid(),kind,context,"2026-09-13T02:00:00Z"),Status::Confirmed);status=Status::Busy;code="RECOVERY_REQUIRED";
        }
        auto before=snapshot(s,"before");observe("refusal",s.prepareRestore(op,o,q),status,code);unchanged(s,before);check("no completed preview",!fs::exists(o.destinationDirectory/"restore-preview.json"));
        check("refused preparation leaves no owned stage",!fs::exists(o.destinationDirectory));
    }
}
void faultCases(){
    for(const std::string mode:{"cancel","deadline","input-replaced","stage-replaced","original-changed","candidate-changed","preview-changed"}){
        setup(mode);auto b=options();auto q=request();auto so=storeOptions(root/current/"live/profile.sqlite");bool reached=false;std::atomic<bool> canceled{false};A phases;
        b.cancelled=[&]{return canceled.load();};if(mode=="deadline")b.timeout=std::chrono::milliseconds(3000);
        so.diagnosticHook=[&](const std::string& phase,const std::string& operation){
            if(phase.rfind("restore_",0)==0)phases.emplace_back(O{{"phase",phase},{"operation",operation}});
            if(phase=="restore_incoming_extracted"&&(mode=="cancel"||mode=="deadline")){reached=true;if(mode=="cancel")canceled=true;else std::this_thread::sleep_for(std::chrono::milliseconds(3100));}
            if(phase=="restore_before_preview_write"){
                if(mode=="input-replaced"){reached=true;fs::rename(q.archive,root/current/"retained-input.zip");copyFixture(root/current/"retained-input.zip",q.archive);}
                if(mode=="stage-replaced"){reached=true;fs::rename(b.destinationDirectory,root/current/"retained-stage");directory(b.destinationDirectory);}
                if(mode=="original-changed"||mode=="candidate-changed"){
                    reached=true;auto path=mode=="original-changed"?b.destinationDirectory/"candidate.zip":b.destinationDirectory/"incoming/profile.sqlite";
                    auto retained=root/current/(mode+"-bytes");copyFixture(path,retained);int fd=open(path.c_str(),O_WRONLY|O_NOFOLLOW);if(fd<0||pwrite(fd,"X",1,0)!=1)throw std::runtime_error("Failed injection");close(fd);
                }
            }
            if(phase=="restore_before_acknowledgment"&&mode=="preview-changed"){
                reached=true;const auto path=b.destinationDirectory/"restore-preview.json";fs::rename(path,root/current/"retained-preview.json");copyFixture(root/current/"retained-preview.json",path);
            }
        };
        ProfileStore s(so);auto before=snapshot(s,"before");observe("injected boundary refusal",s.prepareRestore(newUuid(),b,q),Status::DefiniteFailure,
            mode=="cancel"?"SNAPSHOT_CANCELLED":mode=="deadline"?"SNAPSHOT_DEADLINE":mode=="stage-replaced"?"SNAPSHOT_CHANGED":"RESTORE_CHANGED");
        check("planned fault actually reached",reached);writeNew(root/current/"phases.json",canonical(phases));canceled=false;unchanged(s,before);
        if(mode=="stage-replaced")
            check("replacement stage is not cleaned as this operation's stage",fs::is_directory(b.destinationDirectory));
        else
            check("refused restore cleans its owned partial stage",!fs::exists(b.destinationDirectory));
    }
}
void sourceNamespace(){
    for(const std::string mode:{"live-name-replaced","held-lease-replaced"}){
        setup(mode);auto b=options();auto q=request();auto so=storeOptions(root/current/"live/profile.sqlite");bool reached=false;std::string originalHash;
        const auto path=mode=="live-name-replaced"?so.path:so.path.parent_path()/".profile.lock";const auto displaced=root/current/"original-held-file";
        so.diagnosticHook=[&](const std::string& phase,const std::string&){if(phase!="backup_snapshot_verified")return;
            reached=true;originalHash=sha(path);fs::rename(path,displaced);copyFixture(displaced,path);};
        ProfileStore s(so);auto before=snapshot(s,"before");auto r=observe("original namespace refused",s.prepareRestore(newUuid(),b,q),Status::Unresolved,"RESTORE_SOURCE_CHANGED");
        check("namespace injection reached",reached);check("original held bytes retained",sha(displaced)==originalHash);check("same-byte new path not adopted",sha(path)==originalHash);
        check("no completed preview",!fs::exists(b.destinationDirectory/"restore-preview.json"));
        observe("store blocks further work",s.snapshot(newUuid()),Status::Unresolved,"STORE_UNCERTAIN");
        reopened(b.destinationDirectory/"profile.sqlite",before,"verified-original-reopen");
        check("no false restored state",r.data.null());
    }
}
void reserveBound(){
    setup("reserve-bound");ArchiveReaderOptions o;o.archive=root/current/"incoming.zip";o.candidateDirectory=root/current/"candidate";o.additionalReserveBytes=17ULL*1024*1024*1024+1;
    const auto before=sha(o.archive);bool refused=false;
    try{previewProfileArchive(o);}catch(const EnvelopeError& e){refused=e.code=="ARCHIVE_OPTIONS";traces.emplace_back(O{{"case",current},{"code",e.code},{"message",e.what()}});}
    check("unrepresentable supported reserve refused before extraction",refused);check("no capacity fallback output",!fs::exists(o.candidateDirectory));check("input unchanged",sha(o.archive)==before);
}
void maintenance(){
    setup("maintenance-ack");auto b=options();auto q=request();auto so=storeOptions(root/current/"live/profile.sqlite");std::mutex mutex;std::condition_variable cv;bool entered=false,released=false;
    so.diagnosticHook=[&](const std::string& phase,const std::string&){if(phase!="restore_before_acknowledgment")return;std::unique_lock<std::mutex> lock(mutex);entered=true;cv.notify_all();if(!cv.wait_for(lock,std::chrono::seconds(8),[&]{return released;}))throw std::runtime_error("Held actor timeout");};
    ProfileStore s(so);auto before=snapshot(s,"before");const auto op=newUuid();auto f=s.prepareRestore(op,b,q);
    {std::unique_lock<std::mutex> lock(mutex);check("worker reached final acknowledgment",cv.wait_for(lock,std::chrono::seconds(5),[&]{return entered;}));}
    auto uncertain=ProfileStore::waitForAcknowledgment(f);traces.emplace_back(O{{"case",current},{"name","actual1sacktimeout"},{"reply",replyValue(uncertain)}});check("actual ACK_TIMEOUT",uncertain.status==Status::Unresolved&&uncertain.code=="ACK_TIMEOUT"&&uncertain.operation==op&&f.valid());
    observe("competing write deferred",s.acknowledge(newUuid(),newUuid(),"fg:item:000003",1,"2026-09-13T02:00:00Z"),Status::Busy,"QUEUE_REFUSED");
    {std::lock_guard<std::mutex> lock(mutex);released=true;cv.notify_all();}
    auto r=observe("original future retained",std::move(f),Status::Confirmed,"RESTORE_PREPARED");check("original operation only",r.operation==op);unchanged(s,before);
}
}
int main(int argc,char** argv){
    if(argc!=2){std::cerr<<"Explicit evidence directory required\n";return 2;}
    const fs::path evidence=fs::absolute(argv[1]);fixtures=evidence/"fixtures";root=evidence/"test-data/preparation01";
    bool ownsRunDirectory=false;
    try{directory(evidence/"test-data");directory(root);ownsRunDirectory=true;successes();sealedSourceMutation();changedContent();refusals();faultCases();sourceNamespace();reserveBound();maintenance();
        writeNew(root/"checks.json",canonical(O{{"status","PASS"},{"checks",checks},{"traces",traces},{"restore_performed",false}}));std::cout<<"ALL "<<checks.size()<<" CHECKS PASS\n";return 0;
    }catch(const std::exception& e){std::cerr<<"FAILED "<<current<<" "<<e.what()<<'\n';if(ownsRunDirectory)writeNew(root/"failed01.json",canonical(O{{"status","FAIL"},{"case",current},{"error",e.what()},{"checks",checks},{"traces",traces}}));return 1;}
}
