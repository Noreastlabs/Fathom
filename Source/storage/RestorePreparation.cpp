#include "storage/RestorePreparation.hpp"
#include "storage/ArchiveReader.hpp"
#include "content/Canonical.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <fcntl.h>
#include <fstream>
#include <iterator>
#include <map>
#include <memory>
#include <optional>
#include <regex>
#include <set>
#include <sys/stat.h>
#include <vector>
#include <unistd.h>

namespace fathom::storage::detail {
namespace {
using O=Value::Object;using A=Value::Array;namespace fs=std::filesystem;
void need(bool ok,const std::string& text,const std::string& code="RESTORE_PREVIEW_REFUSED"){
    if(!ok)throw EnvelopeError(code,text);
}
const Value& field(const Value& v,const std::string& key){auto p=v.find(key);need(p!=nullptr,"Missing restore field "+key);return *p;}
std::int64_t integer(const Value& v){std::int64_t n=0;need(v.integer(n),"Expected exact integer");return n;}
Value number(std::int64_t n){return Value::fromInteger(n);}
bool same(const struct stat& a,const struct stat& b){
    return a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_size==b.st_size&&a.st_uid==b.st_uid&&a.st_mode==b.st_mode&&a.st_nlink==b.st_nlink&&
        a.st_mtimespec.tv_sec==b.st_mtimespec.tv_sec&&a.st_mtimespec.tv_nsec==b.st_mtimespec.tv_nsec&&
        a.st_ctimespec.tv_sec==b.st_ctimespec.tv_sec&&a.st_ctimespec.tv_nsec==b.st_ctimespec.tv_nsec;
}
struct Pin {
    fs::path path;int fd=-1;struct stat state{};bool directory=false;
    Pin(fs::path p,bool dir,bool privacy,int held=-1):path(std::move(p)),directory(dir){
        fd=held>=0?fcntl(held,F_DUPFD_CLOEXEC,0):open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_CLOEXEC|(dir?O_DIRECTORY:O_NONBLOCK));
        try{
            need(fd>=0&&fstat(fd,&state)==0,"Cannot pin restore input","RESTORE_CHANGED");
            need(dir?S_ISDIR(state.st_mode):S_ISREG(state.st_mode),"Unexpected restore file type","RESTORE_CHANGED");
            if(privacy)need(state.st_uid==getuid()&&(state.st_mode&077)==0&&(dir||state.st_nlink==1),"Restore stage must remain private","RESTORE_CHANGED");
            validate();
        }catch(...){if(fd>=0)close(fd);fd=-1;throw;}
    }
    ~Pin(){if(fd>=0)close(fd);}Pin(const Pin&)=delete;Pin& operator=(const Pin&)=delete;
    void validate()const{
        struct stat a{},b{};
        need(fstat(fd,&a)==0&&lstat(path.c_str(),&b)==0,"Pinned restore path unavailable","RESTORE_CHANGED");
        if(directory)need(S_ISDIR(a.st_mode)&&S_ISDIR(b.st_mode)&&a.st_dev==state.st_dev&&a.st_ino==state.st_ino&&a.st_mode==state.st_mode&&a.st_uid==state.st_uid&&a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_mode==b.st_mode&&a.st_uid==b.st_uid,"Restore directory changed","RESTORE_CHANGED");
        else need(same(state,a)&&same(a,b),"Restore file changed","RESTORE_CHANGED");
    }
    Value identity(const std::function<void()>& check)const{
        need(!directory&&state.st_size>=0&&static_cast<std::uint64_t>(state.st_size)<=17ULL*1024*1024*1024,"Restore file exceeds bound","RESTORE_CAPACITY");
        CC_SHA256_CTX c;need(CC_SHA256_Init(&c)==1,"Hash initialization failed");std::vector<unsigned char> bytes(1048576);
        off_t offset=0;
        while(offset<state.st_size){check();validate();const auto wanted=static_cast<std::size_t>(std::min<off_t>(state.st_size-offset,static_cast<off_t>(bytes.size())));
            auto n=pread(fd,bytes.data(),wanted,offset);if(n<0&&errno==EINTR)continue;
            need(n>0,"Restore hash read failed","RESTORE_CHANGED");need(CC_SHA256_Update(&c,bytes.data(),static_cast<CC_LONG>(n))==1,"Hash update failed");offset+=n;
        }
        check();validate();std::array<unsigned char,32> h{};need(CC_SHA256_Final(h.data(),&c)==1,"Hash finalization failed");
        const char* digits="0123456789abcdef";std::string sha;for(auto x:h){sha+=digits[x>>4];sha+=digits[x&15];}
        return O{{"device",std::to_string(state.st_dev)},{"inode",std::to_string(state.st_ino)},{"bytes",number(state.st_size)},{"sha256",sha}};
    }
};
void reference(const Value& r){
    need(r.isObject()&&r.object().size()==6,"Availability reference requires exactly six original identity fields","RESTORE_CONTENT");
    const auto str=[&](const std::string& k)->std::string{const auto& v=field(r,k);need(v.isString(),"Reference requires text","RESTORE_CONTENT");return v.string();};
    need(std::regex_match(str("item_id"),std::regex("fg:item:[0-9]{6}"))&&std::regex_match(str("variant_id"),std::regex("fg:variant:[0-9]{6}"))&&
         integer(field(r,"content_revision"))>0&&!str("content_version").empty()&&std::regex_match(str("source_manifest_sha256"),std::regex("[0-9a-f]{64}")),"Invalid original content identity","RESTORE_CONTENT");
    const auto& refs=field(r,"source_refs");need(refs.isArray()&&!refs.array().empty(),"Missing original source refs","RESTORE_CONTENT");std::set<std::string> unique;
    for(const auto& x:refs.array())need(x.isString()&&!x.string().empty()&&unique.insert(x.string()).second,"Invalid/duplicate source refs","RESTORE_CONTENT");
}
Value availability(const Value& requested){
    need(requested.isArray()&&canonical(requested).size()<=1048576,"Availability metadata must be an explicit array at most1MiB; select relevant exact references","RESTORE_CONTENT");
    std::map<std::string,Value> sorted;
    for(const auto& e:requested.array()){
        need(e.isObject()&&e.object().size()==2,"Availability entry must contain only reference/provenance","RESTORE_CONTENT");
        const auto& r=field(e,"reference");reference(r);const auto& p=field(e,"provenance");need(p.isString()&&!p.string().empty(),"Availability provenance required","RESTORE_CONTENT");
        need(sorted.emplace(canonical(r),e).second,"Duplicate/conflicting availability identity","RESTORE_CONTENT");
    }
    A out;for(const auto& e:sorted)out.push_back(e.second);return out;
}
Value compare(const Value& manifest,const Value& available){
    std::map<std::string,Value> index;for(const auto& e:available.array())index.emplace(canonical(field(e,"reference")),e);
    A out;for(const auto& r:field(field(manifest,"snapshot"),"content_references").array()){
        const auto kind=field(r,"reference_kind");
        if(kind==Value("item_revision_only"))out.emplace_back(O{{"original_reference",r},{"status","partial_original_identity"},{"available_metadata",nullptr}});
        else{
            need(kind==Value("versioned_content"),"Unsupported historical reference","RESTORE_CONTENT");auto key=r;key.object().erase("reference_kind");reference(key);auto i=index.find(canonical(key));
            out.emplace_back(O{{"original_reference",r},{"status",i==index.end()?"historical_reference_unavailable":"exact_metadata_reference_present"},{"available_metadata",i==index.end()?Value(nullptr):i->second}});
        }
    }
    return O{{"references",out},{"lookup_scope","Exact supplied metadata only; caller must supply its current available selection"},
        {"runtime_admission","NOT ASSESSED"},{"source_acceptance","NOT ESTABLISHED by availability"},{"missing_policy","Preserve history; unavailable for playback until exact supported content is supplied"},
        {"partial_policy","Preserve item/revision-only acknowledgment; never infer variant/version/provenance"},{"latest_substitution",false},{"history_rewritten",false}};
}
}
Value normalizedRestoreAvailability(const Value& v){return availability(v);}
Value restoreContentComparison(const Value& m,const Value& a){return compare(m,a);}
Value prepareRestore(const std::string& operation,const RestorePreparationRequest& request,
        const fs::path& live,const Value& original,std::chrono::steady_clock::time_point end,
        const std::function<void()>& check,const std::function<void()>& validateFinalAuthority,
        const std::function<void(const std::string&)>& hook){
    validateUuid(operation);check();const auto available=availability(request.availableReferences);
    const fs::path stage=fs::path(field(original,"destination").string()).parent_path();
    std::vector<std::unique_ptr<Pin>> dirs,files;std::vector<Value> identities;
    auto pinDirectory=[&](const fs::path& p){dirs.push_back(std::make_unique<Pin>(p,true,true));};
    pinDirectory(stage);pinDirectory(live.parent_path());pinDirectory(stage.parent_path());
    const auto stable=[&]{check();for(const auto& p:dirs)p->validate();for(const auto& p:files)p->validate();};
    auto bind=[&](const fs::path& path,const Value& expected,bool privacy,int held=-1){
        auto p=std::make_unique<Pin>(path,false,privacy,held);auto identity=p->identity(stable);
        if(!expected.null()){
            need(field(identity,"bytes")==field(expected,"bytes")&&field(identity,"sha256")==field(expected,"sha256"),
                 "Restore input bytes differ from verified receipt","RESTORE_CHANGED");
            for(const char* key:{"device","inode"})if(auto value=expected.find(key))
                need(field(identity,key)==*value,"Restore input native identity differs from verified receipt","RESTORE_CHANGED");
        }
        files.push_back(std::move(p));identities.push_back(identity);return identity;
    };
    bind(live,Value(nullptr),true);
    bind(live.parent_path()/".profile.lock",Value(nullptr),true);
    bind(stage/"profile.sqlite",field(original,"file"),true);
    bind(stage/"manifest.json",field(field(original,"manifest"),"file"),true);
    bind(stage/"candidate.zip",field(field(original,"archive"),"file"),true);
    const auto selectedParent=request.archive.parent_path().filename().string();
    const bool sealed=request.archive.filename()=="selected.zip"&&selectedParent.rfind(".restore-selected-",0)==0;
    if(sealed)pinDirectory(request.archive.parent_path());
    const auto selected=bind(request.archive,Value(nullptr),sealed);
    std::optional<Value> sourceArchive;
    if(sealed){
        const auto originPath=request.archive.parent_path()/"origin.json";
        const auto originIdentity=bind(originPath,Value(nullptr),true);
        std::ifstream input(originPath,std::ios::binary);
        need(static_cast<bool>(input),"Cannot read selected archive origin","RESTORE_CHANGED");
        const std::string bytes{std::istreambuf_iterator<char>(input),std::istreambuf_iterator<char>()};
        need(bytes.size()<=4096&&content::sha256(bytes)==field(originIdentity,"sha256").string(),
             "Selected archive origin changed","RESTORE_CHANGED");
        const auto record=parseCanonical(bytes);
        need(record.isObject()&&record.object().size()==7&&
             field(record,"format")==Value("Fathom.SealedArchiveSource")&&
             field(record,"version")==number(1)&&
             field(record,"snapshot_archive_path")==Value(request.archive.string())&&
             field(record,"snapshot_archive_file")==selected&&
             field(record,"copied_snapshot_semantics")==Value(true)&&
             field(field(record,"source_archive_file"),"bytes")==field(selected,"bytes")&&
             field(field(record,"source_archive_file"),"sha256")==field(selected,"sha256"),
             "Selected archive origin does not bind the validated snapshot","RESTORE_CHANGED");
        sourceArchive=O{{"path",originPath.string()},{"file",originIdentity},{"record",record}};
    }
    const auto reader=[&](const fs::path& archive,const fs::path& target,const std::string& prefix,std::uint64_t reserve){
        stable();auto remaining=std::chrono::duration_cast<std::chrono::milliseconds>(end-std::chrono::steady_clock::now());need(remaining.count()>0,"Restore deadline reached","RESTORE_DEADLINE");
        ArchiveReaderOptions o;o.archive=archive;o.candidateDirectory=target;o.timeout=remaining;o.additionalReserveBytes=reserve;o.reserveSecondCandidate=prefix=="restore_incoming_";
        o.cancelled=[&]{stable();return false;};o.diagnosticHook=[&](const std::string& phase){if(hook)hook(prefix+phase);stable();};
        auto v=previewProfileArchive(o);pinDirectory(target);
        bind(target/"profile.sqlite",field(v,"profile_file"),true);bind(target/"manifest.json",field(v,"manifest_file"),true);return v;
    };
    const auto originalBytes=integer(field(field(original,"file"),"bytes"));need(originalBytes>0,"Missing recoverable original size");
    auto incoming=reader(request.archive,stage/"incoming","restore_incoming_",static_cast<std::uint64_t>(originalBytes)+65536);
    need(field(incoming,"archive")==selected,"Incoming archive changed from selected identity","RESTORE_CHANGED");
    auto recovery=reader(stage/"candidate.zip",stage/"recovery-readback","restore_recovery_",0);
    need(field(recovery,"manifest")==field(field(original,"manifest"),"metadata"),"Recoverable original does not match live boundary","RESTORE_CHANGED");
    const auto& incomingManifest=field(incoming,"manifest");
    Value body=O{{"format","Fathom.RestorePreparation"},{"preparation_version",number(1)},{"operation",operation},
        {"live_profile_path",live.string()},{"live_file",identities.front()},
        {"live_parent",O{{"device",std::to_string(dirs[1]->state.st_dev)},{"inode",std::to_string(dirs[1]->state.st_ino)}}},
        {"live_lease_file",identities[1]},
        {"stage_parent",O{{"path",stage.parent_path().string()},{"device",std::to_string(dirs[2]->state.st_dev)},{"inode",std::to_string(dirs[2]->state.st_ino)}}},{"live_boundary",field(field(original,"manifest"),"metadata")},
        {"selected_archive_path",request.archive.string()},{"incoming",incoming},{"recoverable_original",recovery},
        {"recoverable_archive_path",(stage/"candidate.zip").string()},{"available_metadata",available},
        {"available_metadata_sha256",content::sha256(canonical(available))},{"content_compatibility",compare(incomingManifest,available)},
        {"space_policy",O{{"incoming_expanded_bytes",field(incomingManifest,"profile_bytes")},
            {"incoming_manifest_bytes",field(field(incoming,"manifest_file"),"bytes")},{"additional_original_readback_bytes",number(originalBytes+65536)},
            {"check","Before incoming extraction: available >= 2*(incoming profile+manifest) + original profile+65536 +64MiB. Existing original DB/ZIP already consume disk; future apply must recheck current space."}}},
        {"confirmation_required",true},{"user_confirmed",false},{"restore_performed",false},{"required_resume_state","stopped"},
        {"apply_policy","Separate explicit apply must revalidate this exact preview, live boundary, available selection, all files and source quiescence. No apply implemented by preparation."}};
    if(sourceArchive)body.object().emplace("source_archive",*sourceArchive);
    Value receipt=O{{"preview",body},{"confirmation_sha256",content::sha256(canonical(body))}};
    const auto bytes=canonical(receipt);need(bytes.size()<=2097152,"Restore preview exceeds2MiB; no restore performed","RESTORE_CAPACITY");
    if(hook)hook("restore_before_preview_write");stable();
    const auto path=stage/"restore-preview.json";
    struct OutputFD {int value;~OutputFD(){if(value>=0)close(value);}};
    OutputFD output{open(path.c_str(),O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600)};
    need(output.value>=0,"Cannot exclusively create restore preview","RESTORE_PREVIEW_WRITE");
    std::size_t at=0;
    while(at<bytes.size()){
        stable();auto n=write(output.value,bytes.data()+at,bytes.size()-at);
        if(n<0&&errno==EINTR)continue;
        need(n>0,"Cannot write complete preview","RESTORE_PREVIEW_WRITE");at+=static_cast<std::size_t>(n);
    }
    need(fsync(output.value)==0,"Cannot sync preview","RESTORE_PREVIEW_WRITE");
    // Keep the original exclusively-created descriptor RAII-owned while the Pin
    // duplicates it. Allocation/duplication/validation exceptions cannot leak it.
    const auto saved=bind(path,O{{"bytes",number(static_cast<std::int64_t>(bytes.size()))},{"sha256",content::sha256(bytes)}},true,output.value);
    if(hook)hook("restore_before_acknowledgment");stable();
    validateFinalAuthority();stable();
    for(std::size_t i=0;i<files.size();++i)need(files[i]->identity(stable)==identities[i],"Restore file digest changed before acknowledgment","RESTORE_CHANGED");
    for(std::size_t i=3;i<dirs.size();++i){need(fsync(dirs[i]->fd)==0,"Cannot sync restore child directory","RESTORE_PREVIEW_WRITE");}
    need(fsync(dirs[0]->fd)==0&&fsync(dirs[2]->fd)==0,"Cannot sync restore stage and its parent","RESTORE_PREVIEW_WRITE");
    stable();
    return O{{"record",receipt},{"path",path.string()},{"file",saved},{"prepared",true},{"restore_performed",false},{"required_resume_state","stopped"}};
}
} // namespace fathom::storage::detail
