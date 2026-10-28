#include "storage/BackupPublication.hpp"
#include "storage/ArchiveReader.hpp"
#include "content/Canonical.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <fcntl.h>
#include <regex>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/stdio.h>
#include <unistd.h>

namespace fathom::storage {
namespace {
namespace fs=std::filesystem;using O=Value::Object;using U=std::uint64_t;
constexpr U maxArchive=17ULL*1024*1024*1024;constexpr std::size_t chunk=1048576;
void require(bool ok,const std::string& message,const std::string& code="PUBLICATION_REFUSED"){
    if(!ok)throw EnvelopeError(code,message);
}
Value num(U n){require(n<=static_cast<U>(INT64_MAX),"Publication integer overflow");return Value::fromInteger(static_cast<std::int64_t>(n));}
const Value& field(const Value& v,const std::string& key){auto p=v.find(key);require(p!=nullptr,"Missing operation field: "+key);return *p;}
std::string text(const Value& v){require(v.isString(),"Operation text required");return v.string();}
U integer(const Value& v){std::int64_t n=0;require(v.integer(n)&&n>=0&&canonical(v)==std::to_string(n),"Operation integer required");return static_cast<U>(n);}
struct FD {int value;explicit FD(int v):value(v){require(v>=0,"Cannot open publication file","PUBLICATION_PATH");}~FD(){close(value);}FD(const FD&)=delete;FD& operator=(const FD&)=delete;};
bool stable(const struct stat& a,const struct stat& b){
    return a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_size==b.st_size&&a.st_mode==b.st_mode&&a.st_uid==b.st_uid&&a.st_nlink==b.st_nlink&&
        a.st_mtimespec.tv_sec==b.st_mtimespec.tv_sec&&a.st_mtimespec.tv_nsec==b.st_mtimespec.tv_nsec&&
        a.st_ctimespec.tv_sec==b.st_ctimespec.tv_sec&&a.st_ctimespec.tv_nsec==b.st_ctimespec.tv_nsec;
}
struct stat fileStat(int fd){struct stat s{};require(fstat(fd,&s)==0&&S_ISREG(s.st_mode)&&s.st_size>=0&&s.st_uid==getuid()&&s.st_nlink==1,"Publication file must remain regular, user-owned and unaliased","PUBLICATION_CHANGED");return s;}
void sameName(int fd,int directory,const std::string& name){
    auto a=fileStat(fd);struct stat b{};require(fstatat(directory,name.c_str(),&b,AT_SYMLINK_NOFOLLOW)==0&&S_ISREG(b.st_mode)&&stable(a,b),"Publication name changed","PUBLICATION_CHANGED");
}
void path(const fs::path& p){
    require(p.is_absolute()&&!p.filename().empty()&&p.string().find('\0')==std::string::npos,"Explicit absolute publication path required","PUBLICATION_PATH");
    (void)parseCanonical(canonical(Value(p.string())));
    fs::path at;for(const auto& component:p.parent_path()){
        require(component!="."&&component!="..","Publication traversal refused","PUBLICATION_PATH");at/=component;struct stat s{};
        require(lstat(at.c_str(),&s)==0&&S_ISDIR(s.st_mode),"Publication ancestors must exist without symlinks","PUBLICATION_PATH");
    }
    require(p.filename()!="."&&p.filename()!="..","Publication filename required","PUBLICATION_PATH");
}
void directoryBinding(int fd,const fs::path& p,bool privateDirectory){
    struct stat a{},b{};require(fstat(fd,&a)==0&&lstat(p.c_str(),&b)==0&&S_ISDIR(a.st_mode)&&S_ISDIR(b.st_mode)&&a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_uid==getuid()&&(!privateDirectory||(a.st_mode&077)==0),"Publication directory changed or is not permitted","PUBLICATION_CHANGED");
}
std::string digest(int fd,const std::function<void()>& check){
    auto before=fileStat(fd);require(static_cast<U>(before.st_size)<=maxArchive,"Publication file exceeds archive capacity");
    CC_SHA256_CTX ctx{};require(CC_SHA256_Init(&ctx)==1,"Digest initialization failed");std::vector<char> b(chunk);U at=0;
    while(at<static_cast<U>(before.st_size)){
        check();auto want=static_cast<std::size_t>(std::min<U>(chunk,static_cast<U>(before.st_size)-at));auto n=pread(fd,b.data(),want,static_cast<off_t>(at));
        if(n<0&&errno==EINTR)continue;
        require(n>0,"Publication read failed");require(CC_SHA256_Update(&ctx,b.data(),static_cast<CC_LONG>(n))==1,"Digest update failed");at+=static_cast<U>(n);
    }
    require(stable(before,fileStat(fd)),"Publication file changed during hashing","PUBLICATION_CHANGED");std::array<unsigned char,32> out{};require(CC_SHA256_Final(out.data(),&ctx)==1,"Digest finish failed");const char* h="0123456789abcdef";std::string s;for(auto v:out){s+=h[v>>4];s+=h[v&15];}return s;
}
Value identity(int fd,const std::function<void()>& check){auto s=fileStat(fd);auto sha=digest(fd,check);require(stable(s,fileStat(fd)),"Publication identity changed","PUBLICATION_CHANGED");return O{{"device",std::to_string(s.st_dev)},{"inode",std::to_string(s.st_ino)},{"bytes",num(static_cast<U>(s.st_size))},{"sha256",sha}};}
Value expected(const BackupPublicationRequest& request){
    if(!request.expected)return nullptr;
    const auto& e=*request.expected;require(std::regex_match(e.device,std::regex("[0-9]+"))&&std::regex_match(e.inode,std::regex("[0-9]+"))&&e.bytes>0&&e.bytes<=maxArchive&&std::regex_match(e.sha256,std::regex("[0-9a-f]{64}")),"Exact prior-file expectation required");
    return O{{"device",e.device},{"inode",e.inode},{"bytes",num(e.bytes)},{"sha256",e.sha256}};
}
bool exists(int dir,const std::string& name){struct stat s{};if(fstatat(dir,name.c_str(),&s,AT_SYMLINK_NOFOLLOW)==0)return true;require(errno==ENOENT,"Cannot inspect publication name");return false;}
std::string readRecord(int directory,const std::string& name){
    FD f(openat(directory,name.c_str(),O_RDONLY|O_NOFOLLOW|O_CLOEXEC));auto s=fileStat(f.value);require((s.st_mode&077)==0&&s.st_size>0&&s.st_size<=65536,"Private bounded operation record required");sameName(f.value,directory,name);
    std::string b(static_cast<std::size_t>(s.st_size),'\0');std::size_t at=0;while(at<b.size()){auto n=pread(f.value,b.data()+at,b.size()-at,static_cast<off_t>(at));if(n<0&&errno==EINTR)continue;require(n>0,"Operation record read failed");at+=static_cast<std::size_t>(n);}require(stable(s,fileStat(f.value)),"Operation record changed");sameName(f.value,directory,name);return b;
}
void writeRecord(int dir,const std::string& name,const Value& value){
    auto b=canonical(value);require(b.size()<=65536,"Operation record exceeds64KiB");FD f(openat(dir,name.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600));std::size_t at=0;
    while(at<b.size()){auto n=write(f.value,b.data()+at,b.size()-at);if(n<0&&errno==EINTR)continue;require(n>0,"Operation record write failed");at+=static_cast<std::size_t>(n);}require(fsync(f.value)==0,"Operation record sync failed");sameName(f.value,dir,name);
}
void syncDirectory(int fd){require(fsync(fd)==0,"Publication directory sync failed","PUBLICATION_SYNC");}
Value namedIdentity(int dir,const std::string& name,const std::function<void()>& check){
    if(!exists(dir,name))return nullptr;
    FD fd(openat(dir,name.c_str(),O_RDONLY|O_NOFOLLOW|O_CLOEXEC));
    sameName(fd.value,dir,name);auto id=identity(fd.value,check);sameName(fd.value,dir,name);return id;
}
Value resolution(const std::string& operation,const std::string& intentBytes,bool published){
    return O{{"format","Fathom.BackupPublicationResolution"},{"version",num(1)},
        {"operation",operation},{"intent_sha256",content::sha256(intentBytes)},
        {"archive_published",published}};
}
void retainedRecord(int dir,const std::string& name,const Value& v){
    if(exists(dir,name))require(readRecord(dir,name)==canonical(v),"Retained record conflicts","PUBLICATION_CONFLICT");
    else writeRecord(dir,name,v);
}
void validIdentity(const Value& v,bool nullable=false){
    if(nullable&&v.null())return;
    require(v.isObject()&&v.object().size()==4,"Exact archive identity required","PUBLICATION_CONFLICT");
    require(std::regex_match(text(field(v,"device")),std::regex("[0-9]+"))&&std::regex_match(text(field(v,"inode")),std::regex("[0-9]+"))&&
        integer(field(v,"bytes"))>0&&integer(field(v,"bytes"))<=maxArchive&&std::regex_match(text(field(v,"sha256")),std::regex("[0-9a-f]{64}")),"Invalid archive identity","PUBLICATION_CONFLICT");
}
Value attributes(const struct stat& s){return O{{"mode",num(s.st_mode)},{"uid",num(s.st_uid)},{"links",num(s.st_nlink)},
    {"mtime_seconds",Value::fromInteger(s.st_mtimespec.tv_sec)},{"mtime_nanoseconds",num(s.st_mtimespec.tv_nsec)}};}
Value namedAttributes(int directory,const std::string& name){
    if(!exists(directory,name))return nullptr;
    FD fd(openat(directory,name.c_str(),O_RDONLY|O_NOFOLLOW|O_CLOEXEC));sameName(fd.value,directory,name);return attributes(fileStat(fd.value));
}
void validAttributes(const Value& v,bool nullable){
    if(nullable&&v.null())return;
    require(v.isObject()&&v.object().size()==5,"Exact file attributes required","PUBLICATION_CONFLICT");
    (void)integer(field(v,"mode"));(void)integer(field(v,"uid"));
    std::int64_t seconds=0;require(field(v,"mtime_seconds").integer(seconds)&&integer(field(v,"links"))==1&&integer(field(v,"mtime_nanoseconds"))<1000000000,"Invalid retained file attributes","PUBLICATION_CONFLICT");
}
void validIntent(const Value& v){
    require(v.isObject()&&v.object().size()==10&&field(v,"format")==Value("Fathom.BackupPublicationIntent")&&field(v,"version")==num(1),"Unsupported operation intent","PUBLICATION_CONFLICT");
    validateUuid(text(field(v,"operation")));path(text(field(v,"destination")));path(text(field(v,"stage")));
    validIdentity(field(v,"new_archive"));validIdentity(field(v,"expected_old"),true);
    const auto& a=field(v,"attributes");require(a.isObject()&&a.object().size()==2,"Exact attribute pair required","PUBLICATION_CONFLICT");
    validAttributes(field(a,"new"),false);validAttributes(field(a,"old"),field(v,"expected_old").null());
    require(field(a,"old").null()==field(v,"expected_old").null(),"Old attribute presence differs","PUBLICATION_CONFLICT");
    require(field(v,"rename_mode")==Value(field(v,"expected_old").null()?"EXCL":"SWAP"),"Inconsistent rename mode","PUBLICATION_CONFLICT");
    const auto& s=field(v,"snapshot");require(s.isObject()&&s.object().size()==8,"Exact source tuple required","PUBLICATION_CONFLICT");
    validateUuid(text(field(s,"profile_id")));(void)integer(field(s,"committed_seq"));
    for(const char* key:{"authority_sha256","schema_sha256","profile_sha256","manifest_sha256"})
        require(std::regex_match(text(field(s,key)),std::regex("[0-9a-f]{64}")),"Invalid source digest","PUBLICATION_CONFLICT");
    require(integer(field(s,"profile_bytes"))>0&&integer(field(s,"profile_bytes"))<=16ULL*1024*1024*1024&&
        integer(field(s,"manifest_bytes"))>0&&integer(field(s,"manifest_bytes"))<=65536,"Invalid source byte counts","PUBLICATION_CONFLICT");
}
}
struct BackupPublisher::Impl {
    std::string operation,name,lockName,pointerName;BackupPublicationRequest request;fs::path stage;
    std::function<void()> check;std::function<void(const std::string&)> hook;
    FD parent,lock;Value oldExpected,intent,pendingOperation;std::string intentBytes;
    Impl(std::string op,BackupPublicationRequest r,fs::path s,std::function<void()> c,std::function<void(const std::string&)> h)
        :operation(std::move(op)),name(r.destination.filename().string()),
         lockName(".fathom-backup-publication.lock"),pointerName(".fathom-backup-publication.pending.json"),
         request(std::move(r)),stage(std::move(s)),check(std::move(c)),hook(std::move(h)),
         parent(openParent()),lock(openat(parent.value,lockName.c_str(),O_RDWR|O_CREAT|O_NOFOLLOW|O_CLOEXEC,0600)){
        require(flock(lock.value,LOCK_EX|LOCK_NB)==0,"Another publisher owns this target","PUBLICATION_TARGET_BUSY");
        auto st=fileStat(lock.value);require((st.st_mode&077)==0,"Publication lock must be private");oldExpected=expected(request);guard();
    }
    int openParent(){validateUuid(operation);path(request.destination);path(stage);
        auto folded=name;for(char& c:folded)if(c>='A'&&c<='Z')c=static_cast<char>(c-'A'+'a');
        require(folded.rfind(".fathom-backup-",0)!=0,"Reserved publication namespace","PUBLICATION_PATH");
        if(check)check();return open(request.destination.parent_path().c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);}
    void guard(){if(check)check();directoryBinding(parent.value,request.destination.parent_path(),false);sameName(lock.value,parent.value,lockName);
        struct stat target{},control{};
        if(fstatat(parent.value,name.c_str(),&target,AT_SYMLINK_NOFOLLOW)==0){
            for(const auto& controlName:{lockName,pointerName}){
                if(fstatat(parent.value,controlName.c_str(),&control,AT_SYMLINK_NOFOLLOW)==0)
                    require(target.st_dev!=control.st_dev||target.st_ino!=control.st_ino,"Target aliases publication control file","PUBLICATION_PATH");
                else require(errno==ENOENT,"Cannot inspect publication control file","PUBLICATION_PATH");
            }
        }else require(errno==ENOENT,"Cannot inspect publication target","PUBLICATION_PATH");
    }
    void phase(const std::string& p){if(hook)hook(p);}
    Value pointer()const{return O{{"format","Fathom.BackupPublicationPointer"},{"version",num(1)},{"operation",operation},{"stage",stage.string()},{"intent_sha256",content::sha256(intentBytes)}};}
    Value locations()const{return O{{"operation",operation},{"destination",request.destination.string()},{"stage",stage.string()},{"intent_path",(stage/"publication-intent.json").string()},{"pending_pointer",(request.destination.parent_path()/pointerName).string()},{"pending_operation",pendingOperation},{"intent",intent},{"required_resume_state","stopped"},{"restore_performed",false}};}
    BackupPublicationResult result(BackupPublicationState state,const std::string& code,const std::string& message){auto v=locations();v.object().emplace("archive_published",state==BackupPublicationState::Unresolved?Value(nullptr):Value(state==BackupPublicationState::Published));return {state,code,message,std::move(v)};}
    bool handoff(){
        if(!exists(parent.value,pointerName))return true;
        const auto bytes=readRecord(parent.value,pointerName);pendingOperation=parseCanonical(bytes);
        require(pendingOperation.isObject()&&pendingOperation.object().size()==5&&field(pendingOperation,"format")==Value("Fathom.BackupPublicationPointer")&&field(pendingOperation,"version")==num(1),"Invalid pending pointer","PUBLICATION_CONFLICT");
        const auto previous=text(field(pendingOperation,"operation"));validateUuid(previous);
        if(!request.reconciledPredecessor||*request.reconciledPredecessor!=previous)return false;
        require(previous!=operation,"A new publication cannot reuse the original operation","PUBLICATION_CONFLICT");
        fs::path oldStage=text(field(pendingOperation,"stage"));path(oldStage);
        FD oldDir(open(oldStage.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));directoryBinding(oldDir.value,oldStage,true);
        const auto oldBytes=readRecord(oldDir.value,"publication-intent.json");auto old=parseCanonical(oldBytes);
        validIntent(old);
        require(content::sha256(oldBytes)==text(field(pendingOperation,"intent_sha256"))&&field(old,"operation")==Value(previous)&&field(old,"stage")==Value(oldStage.string()),"Original handoff intent differs","PUBLICATION_CONFLICT");
        const fs::path oldDestination=text(field(old,"destination"));directoryBinding(parent.value,oldDestination.parent_path(),false);
        const auto oldName=oldDestination.filename().string();
        const auto marker=parseCanonical(readRecord(oldDir.value,"publication-resolved.json"));
        const bool published=field(marker,"archive_published")==Value(true);
        require(marker==resolution(previous,oldBytes,published),"Original resolution differs","PUBLICATION_CONFLICT");
        const auto target=published?field(old,"new_archive"):field(old,"expected_old");
        const auto staged=published?field(old,"expected_old"):field(old,"new_archive");
        const auto targetAttributes=field(field(old,"attributes"),published?"new":"old");
        const auto stageAttributes=field(field(old,"attributes"),published?"old":"new");
        auto verify=[&]{guard();directoryBinding(oldDir.value,oldStage,true);
            require(readRecord(parent.value,pointerName)==bytes&&readRecord(oldDir.value,"publication-intent.json")==oldBytes&&readRecord(oldDir.value,"publication-resolved.json")==canonical(marker),"Handoff records changed","PUBLICATION_CHANGED");
            directoryBinding(parent.value,oldDestination.parent_path(),false);
            require(namedIdentity(parent.value,oldName,[&]{guard();})==target&&namedIdentity(oldDir.value,"candidate.zip",[&]{guard();})==staged&&
                namedAttributes(parent.value,oldName)==targetAttributes&&namedAttributes(oldDir.value,"candidate.zip")==stageAttributes,"Original handoff names differ","PUBLICATION_CONFLICT");};
        verify();phase("publication_predecessor_sync");verify();
        syncDirectory(oldDir.value);syncDirectory(parent.value);verify();
        // Explicit same-original-operation handoff, before a new archive can move.
        // Preserve discoverability evidence before removing a resolved barrier.
        retainedRecord(oldDir.value,"publication-resolved-pointer.json",pendingOperation);syncDirectory(oldDir.value);verify();
        require(unlinkat(parent.value,pointerName.c_str(),0)==0,"Cannot retire resolved pointer","PUBLICATION_SYNC");syncDirectory(parent.value);
        pendingOperation=nullptr;return true;
    }
    void verifyRecord(){
        validIntent(intent);
        require(intent.isObject()&&intent.object().size()==10&&field(intent,"format")==Value("Fathom.BackupPublicationIntent")&&field(intent,"version")==num(1)&&
            field(intent,"operation")==Value(operation)&&field(intent,"destination")==Value(request.destination.string())&&field(intent,"stage")==Value(stage.string())&&field(intent,"expected_old")==oldExpected,
            "Original operation/payload differs from retained intent","PUBLICATION_CONFLICT");
        require(field(intent,"new_archive").isObject()&&field(intent,"new_archive").object().size()==4&&field(intent,"snapshot").isObject(),"Invalid retained operation identity");
        (void)integer(field(field(intent,"new_archive"),"bytes"));
        require(std::regex_match(text(field(field(intent,"new_archive"),"sha256")),std::regex("[0-9a-f]{64}")),"Invalid retained archive digest");
        require(field(intent,"rename_mode")==Value(oldExpected.null()?"EXCL":"SWAP"),"Original rename mode changed");
    }
};
BackupPublisher::BackupPublisher(std::string op,BackupPublicationRequest r,fs::path s,std::function<void()> c,std::function<void(const std::string&)> h)
    :impl_(std::make_unique<Impl>(std::move(op),std::move(r),std::move(s),std::move(c),std::move(h))){}
BackupPublisher::~BackupPublisher()=default;
BackupPublicationResult BackupPublisher::publish(int archive,const Value& file,const Value& snapshot){
    auto& p=*impl_;bool attempted=false;
    try{
        p.guard();
        if(!p.handoff())return p.result(BackupPublicationState::NotPublished,"PUBLICATION_PENDING","No new publication attempted; reconcile the retained pending_operation before another publication to this target");
        FD stage(open(p.stage.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));directoryBinding(stage.value,p.stage,true);
        struct stat sd{},td{};require(fstat(stage.value,&sd)==0&&fstat(p.parent.value,&td)==0&&sd.st_dev==td.st_dev,"Stage and target require the same filesystem","PUBLICATION_FILESYSTEM");
        sameName(archive,stage.value,"candidate.zip");auto before=fileStat(archive);
        auto incoming=identity(archive,[&]{p.guard();});
        require(field(incoming,"bytes")==field(file,"bytes")&&field(incoming,"sha256")==field(file,"sha256"),"Verified archive receipt changed","PUBLICATION_CHANGED");
        std::unique_ptr<FD> prior;std::optional<struct stat> priorBefore;
        if(p.oldExpected.null())require(!exists(p.parent.value,p.name),"Target exists; explicit exact replacement required","PUBLICATION_EXISTS");
        else{
            prior=std::make_unique<FD>(openat(p.parent.value,p.name.c_str(),O_RDONLY|O_NOFOLLOW|O_CLOEXEC));sameName(prior->value,p.parent.value,p.name);
            require(identity(prior->value,[&]{p.guard();})==p.oldExpected,"Selected prior backup changed","PUBLICATION_STALE");
            auto st=fileStat(prior->value);require(st.st_dev!=before.st_dev||st.st_ino!=before.st_ino,"Stage/target alias refused","PUBLICATION_CHANGED");
            priorBefore=st;
        }
        p.phase("publication_before_archive_validation");p.guard();
        ArchiveReaderOptions verification;verification.archive=p.stage/"candidate.zip";verification.candidateDirectory=p.stage/"publication-verification";
        verification.cancelled=[&]{p.guard();return false;};auto preview=previewProfileArchive(verification);
        require(field(preview,"archive")==incoming,"Archive verification identity disagrees","PUBLICATION_CHANGED");
        const auto& metadata=field(preview,"manifest");const auto& summary=field(metadata,"snapshot");
        require(snapshot.isObject()&&snapshot.object().size()==8&&
            field(summary,"profile_id")==field(snapshot,"profile_id")&&field(summary,"marker")==field(snapshot,"committed_seq")&&
            field(summary,"authority_sha256")==field(snapshot,"authority_sha256")&&field(summary,"schema_sha256")==field(snapshot,"schema_sha256")&&
            field(metadata,"profile_bytes")==field(snapshot,"profile_bytes")&&field(metadata,"profile_sha256")==field(snapshot,"profile_sha256")&&
            field(field(preview,"profile_file"),"sha256")==field(snapshot,"profile_sha256")&&field(field(preview,"profile_file"),"bytes")==field(snapshot,"profile_bytes")&&
            field(field(preview,"manifest_file"),"sha256")==field(snapshot,"manifest_sha256")&&field(field(preview,"manifest_file"),"bytes")==field(snapshot,"manifest_bytes")&&
            Value(content::sha256(canonical(metadata)))==field(snapshot,"manifest_sha256"),"Archive/source snapshot join differs","PUBLICATION_CHANGED");
        require(stable(before,fileStat(archive)),"Archive changed during independent validation","PUBLICATION_CHANGED");sameName(archive,stage.value,"candidate.zip");
        p.intent=O{{"format","Fathom.BackupPublicationIntent"},{"version",num(1)},{"operation",p.operation},{"destination",p.request.destination.string()},
            {"stage",p.stage.string()},{"expected_old",p.oldExpected},{"new_archive",incoming},{"snapshot",snapshot},{"rename_mode",p.oldExpected.null()?"EXCL":"SWAP"},
            {"attributes",O{{"new",attributes(before)},{"old",priorBefore?attributes(*priorBefore):Value(nullptr)}}}};
        p.intentBytes=canonical(p.intent);p.verifyRecord();
        writeRecord(stage.value,"publication-intent.json",p.intent);syncDirectory(stage.value);
        writeRecord(p.parent.value,p.pointerName,p.pointer());syncDirectory(p.parent.value);
        auto records=[&]{p.guard();directoryBinding(stage.value,p.stage,true);
            require(readRecord(stage.value,"publication-intent.json")==p.intentBytes&&readRecord(p.parent.value,p.pointerName)==canonical(p.pointer()),"Operation intent/pointer changed","PUBLICATION_CHANGED");};
        auto beforeCommit=[&]{records();
            require(identity(archive,[&]{p.guard();})==incoming&&stable(before,fileStat(archive)),"Archive changed before commit","PUBLICATION_CHANGED");sameName(archive,stage.value,"candidate.zip");
            if(prior){sameName(prior->value,p.parent.value,p.name);require(identity(prior->value,[&]{p.guard();})==p.oldExpected&&stable(*priorBefore,fileStat(prior->value)),"Prior backup changed before commit","PUBLICATION_STALE");}
            else require(!exists(p.parent.value,p.name),"Target appeared before commit","PUBLICATION_EXISTS");};
        p.phase("publication_intent_retained");beforeCommit();
        require(fsync(archive)==0,"Archive sync failed","PUBLICATION_SYNC");p.phase("publication_before_rename");beforeCommit();
        // After this boundary no error is reported as definite nonpublication.
        attempted=true;
        int rc=renameatx_np(stage.value,"candidate.zip",p.parent.value,p.name.c_str(),prior?RENAME_SWAP:RENAME_EXCL);
        if(rc!=0)throw EnvelopeError("PUBLICATION_RENAME_UNCERTAIN","Atomic publication syscall failed; inspect retained original names before retrying");
        const auto postNew=fileStat(archive);const auto postOld=prior?std::optional<struct stat>(fileStat(prior->value)):std::nullopt;
        require(attributes(postNew)==attributes(before)&&(!prior||attributes(*postOld)==attributes(*priorBefore)),"Rename changed protected file attributes","PUBLICATION_CHANGED");
        auto afterCommit=[&]{records();sameName(archive,p.parent.value,p.name);
            require(identity(archive,[&]{p.guard();})==incoming&&stable(postNew,fileStat(archive)),"Published archive differs","PUBLICATION_CHANGED");
            if(prior){sameName(prior->value,stage.value,"candidate.zip");require(identity(prior->value,[&]{p.guard();})==p.oldExpected&&stable(*postOld,fileStat(prior->value)),"Unexpected swapped prior file retained","PUBLICATION_CHANGED");}
            else require(!exists(stage.value,"candidate.zip"),"Unexpected stage entry after publication","PUBLICATION_CHANGED");};
        p.phase("publication_after_rename");afterCommit();
        p.phase("publication_before_directory_sync");afterCommit();syncDirectory(stage.value);syncDirectory(p.parent.value);
        auto success=p.result(BackupPublicationState::Published,"BACKUP_PUBLISHED","Verified backup published; previous replacement bytes retained in the private operation stage");
        writeRecord(stage.value,"publication-confirmed.json",success.evidence);syncDirectory(stage.value);
        p.phase("publication_before_acknowledgment");afterCommit();
        require(readRecord(stage.value,"publication-confirmed.json")==canonical(success.evidence),"Publication terminal changed","PUBLICATION_CHANGED");
        // The pointer remains until explicit original reconciliation and handoff.
        return success;
    }catch(const EnvelopeError& e){return p.result(attempted?BackupPublicationState::Unresolved:BackupPublicationState::NotPublished,e.code,e.what());}
    catch(const std::exception& e){return p.result(attempted?BackupPublicationState::Unresolved:BackupPublicationState::NotPublished,"PUBLICATION_EXCEPTION",e.what());}
}
BackupPublicationResult BackupPublisher::reconcile(const std::string& profileId,const std::string& schemaSha256){
    auto& p=*impl_;
    try{
        p.guard();FD stage(open(p.stage.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));directoryBinding(stage.value,p.stage,true);
        p.intentBytes=readRecord(stage.value,"publication-intent.json");p.intent=parseCanonical(p.intentBytes);p.verifyRecord();
        require(field(field(p.intent,"snapshot"),"profile_id")==Value(profileId)&&field(field(p.intent,"snapshot"),"schema_sha256")==Value(schemaSha256),"Original publication belongs to a different profile/schema","PUBLICATION_CONFLICT");
        const auto incoming=field(p.intent,"new_archive");
        if(exists(p.parent.value,p.pointerName))require(readRecord(p.parent.value,p.pointerName)==canonical(p.pointer()),"A different publication owns the target barrier","PUBLICATION_CONFLICT");
        auto named=[&](int dir,const std::string& name){return namedIdentity(dir,name,[&]{p.guard();});};
        auto destination=named(p.parent.value,p.name),retained=named(stage.value,"candidate.zip");
        bool published=destination==incoming&&retained==p.oldExpected;
        bool unchanged=destination==p.oldExpected&&retained==incoming;
        require(published||unchanged,"Original publication namespace conflicts; retain all files","PUBLICATION_CONFLICT");
        const auto destinationAttributes=field(field(p.intent,"attributes"),published?"new":"old");
        const auto retainedAttributes=field(field(p.intent,"attributes"),published?"old":"new");
        auto verify=[&]{p.guard();directoryBinding(stage.value,p.stage,true);
            require(readRecord(stage.value,"publication-intent.json")==p.intentBytes,"Reconcile intent changed","PUBLICATION_CHANGED");
            require(exists(p.parent.value,p.pointerName)&&readRecord(p.parent.value,p.pointerName)==canonical(p.pointer()),"Original pointer unavailable or changed","PUBLICATION_CONFLICT");
            require(named(p.parent.value,p.name)==destination&&named(stage.value,"candidate.zip")==retained&&
                namedAttributes(p.parent.value,p.name)==destinationAttributes&&namedAttributes(stage.value,"candidate.zip")==retainedAttributes,"Publication changed during reconciliation","PUBLICATION_CHANGED");};
        const auto marker=resolution(p.operation,p.intentBytes,published);
        if(exists(stage.value,"publication-resolved.json"))require(readRecord(stage.value,"publication-resolved.json")==canonical(marker),"Original resolution contradicts current namespace","PUBLICATION_CONFLICT");
        if(exists(stage.value,"publication-confirmed.json"))require(published,"Previously confirmed publication no longer matches","PUBLICATION_CONFLICT");
        p.phase("publication_reconcile_inspected");verify();
        syncDirectory(stage.value);syncDirectory(p.parent.value);
        auto result=p.result(published?BackupPublicationState::Published:BackupPublicationState::NotPublished,
            published?"BACKUP_PUBLISHED":"BACKUP_NOT_PUBLISHED",published?"Original publication verified and synchronized":"Original namespace unchanged; no publication retried");
        p.phase("publication_reconcile_before_acknowledgment");verify();
        if(exists(stage.value,"publication-confirmed.json"))require(readRecord(stage.value,"publication-confirmed.json")==canonical(result.evidence),"Original terminal bytes conflict","PUBLICATION_CONFLICT");
        retainedRecord(stage.value,"publication-resolved.json",marker);syncDirectory(stage.value);verify();
        require(readRecord(stage.value,"publication-resolved.json")==canonical(marker),"Original resolution changed","PUBLICATION_CHANGED");return result;
    }catch(const EnvelopeError& e){return p.result(BackupPublicationState::Unresolved,e.code,e.what());}
    catch(const std::exception& e){return p.result(BackupPublicationState::Unresolved,"PUBLICATION_RECONCILE_EXCEPTION",e.what());}
}
} // namespace fathom::storage
