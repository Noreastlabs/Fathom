#include "storage/RestoreApply.hpp"
#include "storage/RestorePreparation.hpp"
#include "storage/ArchiveReader.hpp"
#include "content/Canonical.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <fcntl.h>
#include <regex>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

namespace fathom::storage::detail {
namespace {
namespace fs=std::filesystem;using O=Value::Object;
constexpr const char* pendingName=".fathom-restore.pending.json";
void need(bool ok,const std::string& text,const std::string& code="RESTORE_CHANGED"){
    if(!ok)throw EnvelopeError(code,text);
}
const Value& at(const Value& v,const std::string& k){auto p=v.find(k);need(p!=nullptr,"Missing restore field "+k,"RESTORE_RECORD");return *p;}
std::string text(const Value& v){need(v.isString(),"Restore text field required","RESTORE_RECORD");return v.string();}
std::int64_t integer(const Value& v){std::int64_t n=0;need(v.integer(n)&&n>=0,"Restore integer required","RESTORE_RECORD");return n;}
Value n(std::int64_t x){return Value::fromInteger(x);}
void hashText(const std::string& s){need(std::regex_match(s,std::regex("[0-9a-f]{64}")),"Exact SHA256 required","RESTORE_RECORD");}
void validateAbsolutePath(const fs::path& p){
    need(p.is_absolute()&&p==p.lexically_normal()&&p.string().find('\0')==std::string::npos,"Normalized absolute restore path required","RESTORE_PATH");
    fs::path partial;for(const auto& c:p.parent_path()){
        partial/=c;if(partial=="/")continue;struct stat s{};
        need(lstat(partial.c_str(),&s)==0&&S_ISDIR(s.st_mode),"Restore path contains missing/non-directory/symlink parent","RESTORE_PATH");
    }
}
struct FD {int value=-1;explicit FD(int x):value(x){}~FD(){if(value>=0)close(value);}FD(const FD&)=delete;FD& operator=(const FD&)=delete;};
bool sameNode(const struct stat& a,const struct stat& b){return a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_mode==b.st_mode&&a.st_uid==b.st_uid&&a.st_nlink==b.st_nlink;}
bool sameFile(const struct stat& a,const struct stat& b){return sameNode(a,b)&&a.st_size==b.st_size&&
    a.st_mtimespec.tv_sec==b.st_mtimespec.tv_sec&&a.st_mtimespec.tv_nsec==b.st_mtimespec.tv_nsec&&
    a.st_ctimespec.tv_sec==b.st_ctimespec.tv_sec&&a.st_ctimespec.tv_nsec==b.st_ctimespec.tv_nsec;}
struct Pin {
    fs::path path;FD fd;struct stat initial{};bool directory;
    Pin(fs::path p,bool dir=false,bool privacy=true):path(std::move(p)),fd(-1),directory(dir){
        validateAbsolutePath(path);fd.value=::open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_CLOEXEC|(dir?O_DIRECTORY:O_NONBLOCK));
        need(fd.value>=0&&fstat(fd.value,&initial)==0,"Cannot pin restore path "+path.string());
        need(dir?S_ISDIR(initial.st_mode):S_ISREG(initial.st_mode),"Unexpected restore file type");
        if(privacy)need(initial.st_uid==getuid()&&(initial.st_mode&077)==0&&(dir||initial.st_nlink==1),"Restore files must remain private/user-owned");
        stable();
    }
    void stable()const{struct stat a{},b{};need(fstat(fd.value,&a)==0&&lstat(path.c_str(),&b)==0,"Restore path unavailable");
        need(directory?(initial.st_dev==a.st_dev&&initial.st_ino==a.st_ino&&initial.st_mode==a.st_mode&&initial.st_uid==a.st_uid&&a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_mode==b.st_mode&&a.st_uid==b.st_uid):(sameFile(initial,a)&&sameFile(a,b)),"Pinned restore path changed "+path.string());}
    Value node()const{return O{{"device",std::to_string(initial.st_dev)},{"inode",std::to_string(initial.st_ino)}};}
    Value identity(const std::function<void()>& check)const{
        need(!directory&&initial.st_size>=0&&initial.st_size<=17LL*1024*1024*1024,"Restore identity capacity exceeded","RESTORE_CAPACITY");
        CC_SHA256_CTX c;need(CC_SHA256_Init(&c)==1,"Cannot initialize SHA256");std::vector<unsigned char> buffer(1048576);off_t offset=0;
        while(offset<initial.st_size){check();stable();auto want=static_cast<std::size_t>(std::min<off_t>(initial.st_size-offset,static_cast<off_t>(buffer.size())));
            auto got=pread(fd.value,buffer.data(),want,offset);if(got<0&&errno==EINTR)continue;need(got>0,"Cannot read pinned restore file");
            need(CC_SHA256_Update(&c,buffer.data(),static_cast<CC_LONG>(got))==1,"Cannot update SHA256");offset+=got;
        }
        std::array<unsigned char,32> h{};need(CC_SHA256_Final(h.data(),&c)==1,"Cannot finish SHA256");const char* digits="0123456789abcdef";std::string sha;
        for(auto b:h){sha+=digits[b>>4];sha+=digits[b&15];}check();stable();auto out=node();out.object().emplace("bytes",n(initial.st_size));out.object().emplace("sha256",sha);return out;
    }
    std::string bytes(std::size_t limit)const{
        need(initial.st_size>=0&&static_cast<std::uint64_t>(initial.st_size)<=limit,"Restore record exceeds bounded size","RESTORE_CAPACITY");
        std::string out(static_cast<std::size_t>(initial.st_size),'\0');std::size_t offset=0;
        while(offset<out.size()){auto got=pread(fd.value,out.data()+offset,out.size()-offset,static_cast<off_t>(offset));if(got<0&&errno==EINTR)continue;need(got>0,"Restore record read failed");offset+=static_cast<std::size_t>(got);}stable();return out;
    }
};
bool restoreNameExists(const fs::path& p){struct stat s{};if(lstat(p.c_str(),&s)==0)return true;need(errno==ENOENT,"Cannot inspect restore name");return false;}
Value projectNode(const Value& v){return O{{"device",at(v,"device")},{"inode",at(v,"inode")}};}
Value fileIdentity(const Value& v){need(v.isObject()&&v.object().size()==4,"Exact preview file identity required","RESTORE_RECORD");
    need(!text(at(v,"device")).empty()&&!text(at(v,"inode")).empty()&&integer(at(v,"bytes"))>0,"Invalid file identity","RESTORE_RECORD");hashText(text(at(v,"sha256")));return v;}
Value boundary(const Value& snapshot){O out;for(const char* key:{"profile_id","marker","schema_sha256","authority_sha256","authoritative_row_counts"})out.emplace(key,at(snapshot,key));return out;}
void matchIdentity(const Value& actual,const Value& expected){
    for(const char* k:{"device","inode","bytes","sha256"})if(auto v=expected.find(k))need(at(actual,k)==*v,"Restore identity differs from retained receipt");
}
Value record(const Pin& p,std::size_t limit=4194304){return parseCanonical(p.bytes(limit));}
void noSidecars(const fs::path& p){for(const char* suffix:{"-wal","-shm","-journal"})need(!restoreNameExists(p.string()+suffix),"Restore requires verified standalone database; sidecar preserved","RESTORE_SIDECARS");}
fs::path operationDirectory(const fs::path& live,const std::string& op){validateUuid(op);return live.parent_path()/(".fathom-restore-"+op);}
Value requestValue(const RestoreApplyRequest& q){
    validateAbsolutePath(q.preview);fileIdentity(q.previewFile);hashText(q.confirmationSha256);
    const auto available=normalizedRestoreAvailability(q.availableReferences);
    return O{{"preview_path",q.preview.string()},{"preview_file",q.previewFile},{"confirmation_sha256",q.confirmationSha256},
        {"available_metadata_sha256",content::sha256(canonical(available))},{"explicit_confirmation",q.explicitConfirmation}};
}
void checkPointer(const Value& p,const fs::path& live,const std::string& op){
    need(p.isObject()&&p.object().size()==7&&at(p,"format")==Value("Fathom.RestorePending")&&at(p,"version")==n(1)&&
         at(p,"operation")==Value(op)&&at(p,"live_path")==Value(live.string())&&at(p,"directory")==Value(operationDirectory(live,op).string()),
         "Restore barrier is foreign/malformed; preserve it and reconcile its original operation","RESTORE_PENDING");
    hashText(text(at(p,"request_sha256")));fileIdentity(at(p,"intent_file"));
}
}
void checkRestoreOpen(const fs::path& live,const std::string& recoveryOperation){
    if(!recoveryOperation.empty())validateUuid(recoveryOperation);
    if(restoreNameExists(live.parent_path()/pendingName)){
        Pin pending(live.parent_path()/pendingName);auto p=record(pending);const auto op=text(at(p,"operation"));checkPointer(p,live,op);
        need(!recoveryOperation.empty()&&recoveryOperation==op,"Restore pending for operation "+op+"; use original-operation recovery before opening","RESTORE_PENDING");
    }else if(!recoveryOperation.empty()){
        Pin terminal(operationDirectory(live,recoveryOperation)/"resolved.json");auto r=record(terminal);
        need(at(r,"operation")==Value(recoveryOperation)&&at(r,"live_path")==Value(live.string()),"No matching terminal restore operation","RESTORE_PENDING");
    }
}
struct RestoreApplier::Impl {
    std::string op;RestoreApplyRequest q;fs::path live,stage;RestoreOwner owner;
    std::chrono::steady_clock::time_point end;bool uncertain=false;
    std::unique_ptr<Pin> parent,stagePin,pointer,activeLive;
    Value finalBoundary;
    std::vector<std::unique_ptr<Pin>> retained;std::vector<Value> retainedIdentities;
    Value request,preview,intent,intentIdentity;
    Impl(std::string id,RestoreApplyRequest r,fs::path path,RestoreOwner o):op(std::move(id)),q(std::move(r)),live(std::move(path)),stage(operationDirectory(live,op)),owner(std::move(o)){
        need(q.timeout.count()>0&&q.timeout<=std::chrono::seconds(300),"Restore timeout must be positive and at most300seconds","RESTORE_OPTIONS");
        end=std::chrono::steady_clock::now()+q.timeout;
        request=requestValue(q);parent=std::make_unique<Pin>(live.parent_path(),true);check();
    }
    void check(){owner.checkLease();parent->stable();if(stagePin)stagePin->stable();
        if(activeLive){struct stat held{},named{};need(fstat(activeLive->fd.value,&held)==0&&lstat(live.c_str(),&named)==0&&sameNode(activeLive->initial,held)&&sameNode(held,named),"Installed live namespace changed","RESTORE_CHANGED");}
        if(q.cancelled&&q.cancelled())throw EnvelopeError("RESTORE_CANCELLED","Restore cancelled; preserve original operation and data");
        need(std::chrono::steady_clock::now()<end,"Restore deadline reached; preserve original operation and data","RESTORE_DEADLINE");}
    void phase(const std::string& s){if(owner.phase)owner.phase(s);check();}
    Value bind(const fs::path& p,const Value& expected=Value(nullptr),bool privacy=true){
        auto file=std::make_unique<Pin>(p,false,privacy);auto identity=file->identity([&]{check();});if(!expected.null())matchIdentity(identity,expected);
        retained.push_back(std::move(file));retainedIdentities.push_back(identity);return identity;
    }
    Value save(Pin& directory,const std::string& name,const Value& body){
        const auto bytes=canonical(body);need(bytes.size()<=4194304,"Restore control record exceeds4MiB","RESTORE_CAPACITY");check();directory.stable();
        FD fd(openat(directory.fd.value,name.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600));need(fd.value>=0,"Cannot exclusively create restore record "+name,"RESTORE_RECORD_WRITE");
        std::size_t offset=0;while(offset<bytes.size()){check();auto wrote=write(fd.value,bytes.data()+offset,bytes.size()-offset);if(wrote<0&&errno==EINTR)continue;need(wrote>0,"Cannot write complete restore record","RESTORE_RECORD_WRITE");offset+=static_cast<std::size_t>(wrote);}
        need(fsync(fd.value)==0&&fsync(directory.fd.value)==0,"Cannot sync restore control record","RESTORE_SYNC");
        Pin saved(directory.path/name);struct stat held{};need(fstat(fd.value,&held)==0&&sameFile(held,saved.initial),"Created record name changed");return saved.identity([&]{check();});
    }
    Value getPreview(){
        auto id=bind(q.preview,q.previewFile);(void)id;auto r=record(*retained.back(),2097152);
        need(r.isObject()&&r.object().size()==2&&at(r,"confirmation_sha256")==Value(q.confirmationSha256),"Exact prepared confirmation required","RESTORE_CONFIRMATION");
        const auto body=at(r,"preview");
        need(content::sha256(canonical(body))==q.confirmationSha256&&at(body,"format")==Value("Fathom.RestorePreparation")&&at(body,"preparation_version")==n(1)&&
             at(body,"live_profile_path")==Value(live.string())&&at(body,"confirmation_required")==Value(true)&&at(body,"user_confirmed")==Value(false)&&
             at(body,"restore_performed")==Value(false)&&at(body,"required_resume_state")==Value("stopped"),"Unsupported or conflicting prepared preview","RESTORE_CONFIRMATION");
        validateUuid(text(at(body,"operation")));need(at(body,"operation")!=Value(op),"Apply uses its own UUID bound to preparation","RESTORE_OPERATION");
        auto available=normalizedRestoreAvailability(q.availableReferences);
        need(at(body,"available_metadata")==available&&at(body,"available_metadata_sha256")==at(request,"available_metadata_sha256"),"Current content selection differs; prepare a new explicit preview","RESTORE_CONTENT_STALE");
        need(at(body,"content_compatibility")==restoreContentComparison(at(at(body,"incoming"),"manifest"),available),"Preview compatibility differs from exact source identities","RESTORE_CONTENT_STALE");
        return body;
    }
    void preserveInputs(){
        const fs::path prep=q.preview.parent_path();
        need(q.preview.filename()=="restore-preview.json","Prepared record filename required","RESTORE_PATH");
        auto pinDir=[&](const fs::path& p){auto d=std::make_unique<Pin>(p,true);retainedIdentities.push_back(Value(nullptr));retained.push_back(std::move(d));};
        // Directories are checked separately; stable() deliberately handles their node identity.
        pinDir(prep);pinDir(prep/"incoming");pinDir(prep/"recovery-readback");pinDir(prep.parent_path());
        need(projectNode(at(preview,"live_parent"))==parent->node(),"Live parent differs from preview");
        Pin stageParent(prep.parent_path(),true);need(projectNode(at(preview,"stage_parent"))==stageParent.node()&&at(at(preview,"stage_parent"),"path")==Value(prep.parent_path().string()),"Prepared parent changed");
        bind(live.parent_path()/".profile.lock",at(preview,"live_lease_file"));
        const auto incoming=at(preview,"incoming"),original=at(preview,"recoverable_original");
        need(at(incoming,"candidate_directory")==Value((prep/"incoming").string())&&at(original,"candidate_directory")==Value((prep/"recovery-readback").string())&&
             at(preview,"recoverable_archive_path")==Value((prep/"candidate.zip").string()),"Prepared stage paths differ","RESTORE_PATH");
        if(preview.find("source_archive"))
            pinDir(fs::path(text(at(preview,"selected_archive_path"))).parent_path());
        bind(text(at(preview,"selected_archive_path")),at(incoming,"archive"),preview.find("source_archive")!=nullptr);
        if(const auto* source=preview.find("source_archive")){
            need(source->isObject()&&source->object().size()==3,
                 "Sealed source archive record is malformed","RESTORE_RECORD");
            const fs::path sourcePath=text(at(*source,"path"));
            need(sourcePath==fs::path(text(at(preview,"selected_archive_path"))).parent_path()/"origin.json",
                 "Sealed source archive record path differs","RESTORE_PATH");
            bind(sourcePath,at(*source,"file"));
            need(record(*retained.back(),4096)==at(*source,"record"),
                 "Sealed source archive origin changed","RESTORE_CHANGED");
            const auto& provenance=at(*source,"record");
            need(at(provenance,"format")==Value("Fathom.SealedArchiveSource")&&
                 at(provenance,"version")==n(1)&&
                 at(provenance,"copied_snapshot_semantics")==Value(true)&&
                 at(provenance,"snapshot_archive_path")==at(preview,"selected_archive_path")&&
                 at(provenance,"snapshot_archive_file")==at(incoming,"archive")&&
                 at(at(provenance,"source_archive_file"),"bytes")==at(at(incoming,"archive"),"bytes")&&
                 at(at(provenance,"source_archive_file"),"sha256")==at(at(incoming,"archive"),"sha256"),
                 "Sealed source archive does not bind the prepared snapshot","RESTORE_CHANGED");
        }
        bind(prep/"candidate.zip",at(original,"archive"));
        bind(prep/"profile.sqlite",O{{"bytes",at(at(preview,"live_boundary"),"profile_bytes")},{"sha256",at(at(preview,"live_boundary"),"profile_sha256")}});
        bind(prep/"manifest.json",O{{"bytes",at(at(original,"manifest_file"),"bytes")},{"sha256",at(at(original,"manifest_file"),"sha256")}});
        bind(prep/"incoming/manifest.json",at(incoming,"manifest_file"));
        bind(prep/"recovery-readback/manifest.json",at(original,"manifest_file"));
        // Original root manifest and readback are distinct files, sharing verified bytes.
        auto verify=[&](const fs::path& path,const Value& reader){
            bind(path,at(reader,"profile_file"));Pin file(path);auto actual=inspectArchiveCandidate(file.fd.value,path,[&]{check();file.stable();},{});
            need(actual==at(reader,"manifest"),"Prepared candidate metadata/authority changed");
        };
        verify(prep/"incoming/profile.sqlite",incoming);verify(prep/"recovery-readback/profile.sqlite",original);
        need(at(original,"manifest")==at(preview,"live_boundary"),"Recoverable original differs from preview");
    }
    void pinsStable(){check();if(pointer)pointer->stable();for(const auto& p:retained)p->stable();}
    void finalAuthority(){check();if(!finalBoundary.null())need(owner.currentBoundary()==finalBoundary,"Installed authority changed before final acknowledgment","RESTORE_SOURCE_STALE");check();}
    void allStable(){check();if(pointer)pointer->stable();for(std::size_t i=0;i<retained.size();++i){retained[i]->stable();if(!retained[i]->directory)need(retained[i]->identity([&]{check();})==retainedIdentities[i],"Retained restore artifact changed");}}
    void currentMatches(){Pin file(live);matchIdentity(file.identity([&]{check();}),at(preview,"live_file"));
        need(owner.currentBoundary()==boundary(at(at(preview,"live_boundary"),"snapshot")),"Live authority changed since preview; prepare a new preview","RESTORE_SOURCE_STALE");}
    void copyInstall(){
        const auto& in=at(at(preview,"incoming"),"profile_file");const auto bytes=integer(at(in,"bytes"));
        const auto space=fs::space(live.parent_path());need(space.available>=static_cast<std::uint64_t>(bytes)+64ULL*1024*1024,"Insufficient current space for separate install image plus64MiB; original already retained","RESTORE_SPACE");
        need(mkdirat(parent->fd.value,stage.filename().c_str(),0700)==0,"Restore operation directory exists or cannot be created; reconcile original operation","RESTORE_OPERATION_EXISTS");
        stagePin=std::make_unique<Pin>(stage,true);need(stagePin->initial.st_dev==parent->initial.st_dev,"Restore install must share live filesystem","RESTORE_PATH");
        Pin input(q.preview.parent_path()/"incoming/profile.sqlite");matchIdentity(input.identity([&]{check();}),in);
        FD output(openat(stagePin->fd.value,"profile.sqlite",O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600));need(output.value>=0,"Cannot create install image","RESTORE_COPY");
        std::vector<char> buffer(1048576);off_t offset=0;
        while(offset<bytes){pinsStable();input.stable();auto got=pread(input.fd.value,buffer.data(),static_cast<std::size_t>(std::min<off_t>(bytes-offset,static_cast<off_t>(buffer.size()))),offset);
            if(got<0&&errno==EINTR)continue;
            need(got>0,"Install source read failed","RESTORE_COPY");std::size_t done=0;
            while(done<static_cast<std::size_t>(got)){check();auto wrote=write(output.value,buffer.data()+done,static_cast<std::size_t>(got)-done);if(wrote<0&&errno==EINTR)continue;need(wrote>0,"Install copy write failed","RESTORE_COPY");done+=static_cast<std::size_t>(wrote);}offset+=got;
        }
        need(fsync(output.value)==0&&fsync(stagePin->fd.value)==0&&fsync(parent->fd.value)==0,"Install image sync failed","RESTORE_SYNC");
        Pin file(stage/"profile.sqlite");struct stat created{};need(fstat(output.value,&created)==0&&sameFile(created,file.initial),"Install copy name changed");
        auto manifest=inspectArchiveCandidate(file.fd.value,file.path,[&]{check();file.stable();},{});
        need(manifest==at(at(preview,"incoming"),"manifest"),"Install copy did not independently validate");
        intent=O{{"format","Fathom.RestoreIntent"},{"version",n(1)},{"operation",op},{"live_path",live.string()},{"request",request},
            {"preview",preview},{"install_file",file.identity([&]{check();})},{"live_parent",parent->node()},{"stage_node",stagePin->node()}};
        intentIdentity=save(*stagePin,"intent.json",intent);bind(stage/"intent.json",intentIdentity);
        phase("restore_apply_before_barrier");allStable();currentMatches();
        // Even a partial marker prevents ordinary open. After this point every error
        // is conservative Unresolved; reconciliation never performs another swap.
        uncertain=true;
        Value p=O{{"format","Fathom.RestorePending"},{"version",n(1)},{"operation",op},{"live_path",live.string()},{"directory",stage.string()},
            {"request_sha256",content::sha256(canonical(request))},{"intent_file",intentIdentity}};
        save(*parent,pendingName,p);pointer=std::make_unique<Pin>(live.parent_path()/pendingName);
        phase("restore_apply_barrier_retained");allStable();currentMatches();
    }
    Value resolutionValue(bool installed,const Value& named){
        return O{{"format","Fathom.RestoreResolution"},{"version",n(1)},{"operation",op},{"preparation_operation",at(preview,"operation")},
            {"live_path",live.string()},{"request",request},{"intent_file",intentIdentity},{"restore_performed",installed},{"installed_file_node",projectNode(named)},
            {"snapshot",at(installed?at(at(preview,"incoming"),"manifest"):at(preview,"live_boundary"),"snapshot")},
            {"recoverable_archive_path",at(preview,"recoverable_archive_path")},{"retained_swap_path",(stage/"profile.sqlite").string()},
            {"content_compatibility",restoreContentComparison(installed?at(at(preview,"incoming"),"manifest"):at(preview,"live_boundary"),normalizedRestoreAvailability(q.availableReferences))},{"required_resume_state","stopped"},{"invalidate_previous_consumers",true},
            {"confirmation_sha256",q.confirmationSha256},{"claim","Historical outcome at resolution; later legitimate writes are separate"}};
    }
    Value resolved(bool installed,const Value& named){
        const auto value=resolutionValue(installed,named);
        phase("restore_apply_before_resolution");allStable();finalAuthority();save(*stagePin,"resolved.json",value);bind(stage/"resolved.json");
        phase("restore_apply_resolution_retained");retire();return value;
    }
    void retire(){
        allStable();finalAuthority();if(pointer){need(unlinkat(parent->fd.value,pendingName,0)==0,"Cannot retire resolved restore barrier","RESTORE_SYNC");pointer.reset();}
        phase("restore_apply_barrier_retired");need(fsync(parent->fd.value)==0,"Restore barrier retirement sync uncertain","RESTORE_SYNC");check();finalAuthority();uncertain=false;
    }
    void load(){
        stagePin=std::make_unique<Pin>(stage,true);Pin input(stage/"intent.json");intent=record(input);intentIdentity=input.identity([&]{check();});
        need(intent.isObject()&&intent.object().size()==9&&at(intent,"format")==Value("Fathom.RestoreIntent")&&at(intent,"version")==n(1)&&
             at(intent,"operation")==Value(op)&&at(intent,"live_path")==Value(live.string())&&at(intent,"request")==request,"Original restore operation/payload conflict","RESTORE_CONFLICT");
        need(at(intent,"live_parent")==parent->node()&&at(intent,"stage_node")==stagePin->node(),"Restore operation directory changed");
        preview=at(intent,"preview");bind(stage/"intent.json",intentIdentity);
        if(restoreNameExists(live.parent_path()/pendingName)){
            pointer=std::make_unique<Pin>(live.parent_path()/pendingName);auto p=record(*pointer);checkPointer(p,live,op);
            need(at(p,"intent_file")==intentIdentity&&at(p,"request_sha256")==Value(content::sha256(canonical(request))),"Original restore barrier/payload conflict","RESTORE_CONFLICT");
        }
    }
    Value apply(){
        need(q.explicitConfirmation,"Explicit confirmation of this exact preview required","RESTORE_CONFIRMATION");
        need(!restoreNameExists(live.parent_path()/pendingName),"Resolve the original pending restore first","RESTORE_PENDING");
        preview=getPreview();preserveInputs();allStable();currentMatches();phase("restore_apply_preview_validated");copyInstall();
        phase("restore_apply_before_close");allStable();currentMatches();owner.checkpointAndClose();
        phase("restore_apply_after_close");allStable();noSidecars(live);
        Pin old(live);need(old.node()==projectNode(at(preview,"live_file")),"Closed original native identity changed");
        auto oldManifest=inspectArchiveCandidate(old.fd.value,live,[&]{check();old.stable();},{});
        need(at(oldManifest,"snapshot")==at(at(preview,"live_boundary"),"snapshot"),"Closed original lost committed authority");
        Pin incoming(stage/"profile.sqlite");const auto newIdentity=incoming.identity([&]{check();});need(newIdentity==at(intent,"install_file"),"Install image changed before swap");
        auto oldIdentity=old.identity([&]{check();});Value ready=O{{"operation",op},{"intent_file",intentIdentity},{"old_file",oldIdentity},{"new_file",newIdentity}};
        auto readyIdentity=save(*stagePin,"ready.json",ready);bind(stage/"ready.json",readyIdentity);
        phase("restore_apply_before_swap");allStable();old.stable();incoming.stable();noSidecars(live);noSidecars(incoming.path);
        need(old.identity([&]{check();})==oldIdentity&&incoming.identity([&]{check();})==newIdentity,"Pre-swap file changed");
        need(renameatx_np(parent->fd.value,live.filename().c_str(),stagePin->fd.value,"profile.sqlite",RENAME_SWAP)==0,
             "Restore swap outcome uncertain; reconcile the original operation","RESTORE_SWAP_UNCERTAIN");
        Pin installed(live),retainedOld(stage/"profile.sqlite");
        // Rename may update ctime; mode/owner/link count, bytes, mtime and actual
        // held old/new descriptors must continue to name the two installed files.
        struct stat oldHeld{},newHeld{};
        need(fstat(old.fd.value,&oldHeld)==0&&fstat(incoming.fd.value,&newHeld)==0&&sameNode(old.initial,oldHeld)&&sameNode(incoming.initial,newHeld)&&
             sameFile(oldHeld,retainedOld.initial)&&sameFile(newHeld,installed.initial)&&oldHeld.st_size==old.initial.st_size&&newHeld.st_size==incoming.initial.st_size&&
             oldHeld.st_mtimespec.tv_sec==old.initial.st_mtimespec.tv_sec&&oldHeld.st_mtimespec.tv_nsec==old.initial.st_mtimespec.tv_nsec&&
             newHeld.st_mtimespec.tv_sec==incoming.initial.st_mtimespec.tv_sec&&newHeld.st_mtimespec.tv_nsec==incoming.initial.st_mtimespec.tv_nsec,"Swap attributes/names changed");
        need(installed.identity([&]{check();})==newIdentity&&retainedOld.identity([&]{check();})==oldIdentity,"Post-swap names do not identify exact old/new images");
        bind(stage/"profile.sqlite",oldIdentity);activeLive=std::make_unique<Pin>(live);
        phase("restore_apply_after_swap");allStable();
        need(fsync(parent->fd.value)==0&&fsync(stagePin->fd.value)==0,"Post-swap directory sync uncertain","RESTORE_SYNC");phase("restore_apply_after_sync");
        save(*stagePin,"open-started.json",O{{"operation",op},{"intent_file",intentIdentity},{"installed",true}});
        phase("restore_apply_before_reopen");allStable();owner.reopen(boundary(at(at(at(preview,"incoming"),"manifest"),"snapshot")),newIdentity,false);
        finalBoundary=owner.currentBoundary();need(finalBoundary==boundary(at(at(at(preview,"incoming"),"manifest"),"snapshot")),"Reopened authority differs");
        phase("restore_apply_after_reopen");return resolved(true,newIdentity);
    }
    Value reconcile(){
        uncertain=restoreNameExists(live.parent_path()/pendingName);load();
        if(restoreNameExists(stage/"resolved.json")){
            bind(stage/"resolved.json");auto r=record(*retained.back());
            need(at(r,"format")==Value("Fathom.RestoreResolution")&&at(r,"version")==n(1)&&at(r,"operation")==Value(op)&&at(r,"request")==request&&at(r,"intent_file")==intentIdentity,
                 "Terminal restore record conflicts with original operation","RESTORE_CONFLICT");
            need(at(r,"restore_performed").isBool(),"Terminal outcome requires boolean","RESTORE_CONFLICT");
            const bool installed=at(r,"restore_performed").boolean();
            const auto native=installed?at(intent,"install_file"):at(preview,"live_file");
            need(r==resolutionValue(installed,native),"Terminal outcome differs from original intent","RESTORE_CONFLICT");
            allStable();activeLive=std::make_unique<Pin>(live);need(activeLive->node()==at(r,"installed_file_node"),"Terminal live native identity differs");
            owner.reopen(boundary(at(r,"snapshot")),at(r,"installed_file_node"),true);finalBoundary=owner.currentBoundary();retire();return r;
        }
        need(pointer!=nullptr,"No pending barrier or terminal resolution; preserve and inspect original restore artifacts","RESTORE_PENDING");
        // Inputs stay pinned to the original intent, including explicit original
        // metadata. Reconciliation does not obtain a new preview or swap again.
        need(at(preview,"available_metadata_sha256")==at(request,"available_metadata_sha256")&&
             content::sha256(canonical(preview))==q.confirmationSha256,"Retained preview/request conflict","RESTORE_CONFLICT");
        need(getPreview()==preview,"Prepared record differs from original intent","RESTORE_CONFLICT");
        preserveInputs();allStable();Pin named(live),other(stage/"profile.sqlite");const auto oldNode=projectNode(at(preview,"live_file")),newNode=projectNode(at(intent,"install_file"));
        bool installed=false;
        if(named.node()==oldNode&&other.node()==newNode){
            need(other.identity([&]{check();})==at(intent,"install_file"),"Uninstalled candidate changed");
            need(owner.currentBoundary()==boundary(at(at(preview,"live_boundary"),"snapshot")),"Retained old live authority differs","RESTORE_SOURCE_STALE");
        }else if(named.node()==newNode&&other.node()==oldNode){
            installed=true;bind(stage/"ready.json");auto ready=record(*retained.back());
            need(at(ready,"operation")==Value(op)&&at(ready,"intent_file")==intentIdentity&&at(ready,"new_file")==at(intent,"install_file"),"Missing/conflicting pre-swap identity record","RESTORE_CONFLICT");
            noSidecars(other.path);need(other.identity([&]{check();})==at(ready,"old_file"),"Retained closed original differs");
            if(!restoreNameExists(stage/"open-started.json")){noSidecars(live);need(named.identity([&]{check();})==at(intent,"install_file"),"Installed candidate bytes differ before open");}
            else{bind(stage/"open-started.json");const auto opened=record(*retained.back());need(at(opened,"operation")==Value(op)&&at(opened,"intent_file")==intentIdentity&&at(opened,"installed")==Value(true),"Conflicting normal-open marker","RESTORE_CONFLICT");}
            need(owner.currentBoundary()==boundary(at(at(at(preview,"incoming"),"manifest"),"snapshot")),"Installed logical authority differs","RESTORE_SOURCE_STALE");
        }else throw EnvelopeError("RESTORE_CHANGED","Cannot classify original restore names; no swap/retry performed");
        phase("restore_reconcile_classified");allStable();need(fsync(parent->fd.value)==0&&fsync(stagePin->fd.value)==0,"Reconciliation directory sync failed","RESTORE_SYNC");
        const auto expected=boundary(at(installed?at(at(preview,"incoming"),"manifest"):at(preview,"live_boundary"),"snapshot"));
        if(installed&&!restoreNameExists(stage/"open-started.json"))save(*stagePin,"open-started.json",O{{"operation",op},{"intent_file",intentIdentity},{"installed",true}});
        activeLive=std::make_unique<Pin>(live);
        owner.reopen(expected,named.node(),false);finalBoundary=owner.currentBoundary();need(finalBoundary==expected,"Reconciled authority differs");return resolved(installed,named.node());
    }
};
RestoreApplier::RestoreApplier(std::string o,RestoreApplyRequest r,fs::path p,RestoreOwner owner):impl_(std::make_unique<Impl>(std::move(o),std::move(r),std::move(p),std::move(owner))){}
RestoreApplier::~RestoreApplier()=default;
Value RestoreApplier::apply(){return impl_->apply();}
Value RestoreApplier::reconcile(){return impl_->reconcile();}
bool RestoreApplier::uncertain()const noexcept{return impl_->uncertain;}
Value RestoreApplier::recoveryDetails()const{return O{{"operation",impl_->op},{"live_path",impl_->live.string()},{"directory",impl_->stage.string()},
    {"pending_path",(impl_->live.parent_path()/pendingName).string()},{"request",impl_->request},{"required_resume_state","stopped"},{"instruction","Retain both sides; reconcile the original operation and exact immutable request. Do not retry installation."}};}
} // namespace fathom::storage::detail
