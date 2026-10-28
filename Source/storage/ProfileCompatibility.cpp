#include "storage/ProfileCompatibility.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "content/Canonical.hpp"
#include "sqlite3.h"
#include <CommonCrypto/CommonDigest.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <map>
#include <regex>
#include <set>
#include <sys/stat.h>
#include <unistd.h>

namespace fathom::storage {
namespace {
using A=Value::Array;using O=Value::Object;
struct Error:std::runtime_error{Status status;std::string code;Error(Status s,std::string c,std::string m):std::runtime_error(std::move(m)),status(s),code(std::move(c)) {}};
void need(bool ok,const std::string& why,const std::string& code="COMPATIBILITY_REFUSED"){if(!ok)throw Error(Status::DefiniteFailure,code,why);}
const Value& f(const Value& v,const std::string& k){auto p=v.find(k);need(p!=nullptr,"Missing field "+k);return *p;}
std::string text(const Value& v){need(v.isString(),"Expected text");return v.string();}
Value number(std::int64_t n){return Value::fromInteger(n);}
std::string hash(const Value& v){return content::sha256(canonical(v));}
bool digest(const std::string& s){return std::regex_match(s,std::regex("[0-9a-f]{64}"));}
struct FD {int n=-1;explicit FD(int fd):n(fd){}~FD(){if(n>=0)::close(n);}FD(const FD&)=delete;FD&operator=(const FD&)=delete;};
void regular(const struct stat& s){need(S_ISREG(s.st_mode)&&s.st_uid==getuid()&&s.st_nlink==1&&(s.st_mode&077)==0,"Expected private regular user-owned unlinked file");}
bool same(const struct stat& a,const struct stat& b){return a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_size==b.st_size&&a.st_mtimespec.tv_sec==b.st_mtimespec.tv_sec&&a.st_mtimespec.tv_nsec==b.st_mtimespec.tv_nsec&&a.st_ctimespec.tv_sec==b.st_ctimespec.tv_sec&&a.st_ctimespec.tv_nsec==b.st_ctimespec.tv_nsec;}
void deadline(std::chrono::steady_clock::time_point end){need(std::chrono::steady_clock::now()<end,"Inspection copy deadline reached; original retained","COPY_CAPACITY");}
Value file(const std::filesystem::path& source,const std::optional<std::filesystem::path>& destination,std::uint64_t limit,std::chrono::steady_clock::time_point end){
    struct stat pathState{};
    if(lstat(source.c_str(),&pathState)!=0){need(errno==ENOENT,"Cannot inspect image: "+std::string(strerror(errno)));return nullptr;}
    regular(pathState);need(pathState.st_size>=0&&static_cast<std::uint64_t>(pathState.st_size)<=limit,"Image exceeds inspection capacity; no history removed","COPY_CAPACITY");
    FD input(::open(source.c_str(),O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK));need(input.n>=0,"Cannot open image: "+std::string(strerror(errno)));struct stat opened{};need(fstat(input.n,&opened)==0&&same(pathState,opened),"Image changed before read");regular(opened);
    FD output(destination?::open(destination->c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600):-1);if(destination)need(output.n>=0,"Cannot exclusively create stage image: "+std::string(strerror(errno)),"STAGE_WRITE_FAILED");
    CC_SHA256_CTX ctx;need(CC_SHA256_Init(&ctx)==1,"Hash initialization failed");std::array<unsigned char,65536> buffer{};std::uint64_t total=0;
    for(;;){deadline(end);auto got=::read(input.n,buffer.data(),buffer.size());if(got<0&&errno==EINTR)continue;need(got>=0,"Image read failed");if(got==0)break;need(static_cast<std::uint64_t>(got)<=limit-total,"Image grew beyond inspection capacity","COPY_CAPACITY");total+=static_cast<std::uint64_t>(got);need(CC_SHA256_Update(&ctx,buffer.data(),static_cast<CC_LONG>(got))==1,"Hash update failed");if(destination){ssize_t at=0;while(at<got){auto written=::write(output.n,buffer.data()+at,static_cast<std::size_t>(got-at));if(written<0&&errno==EINTR)continue;need(written>0,"Stage write failed","STAGE_WRITE_FAILED");at+=written;}}}
    struct stat after{},named{};need(fstat(input.n,&after)==0&&lstat(source.c_str(),&named)==0&&same(opened,after)&&same(after,named)&&total==static_cast<std::uint64_t>(after.st_size),"Image changed during read");
    if(destination)need(fsync(output.n)==0,"Stage sync failed","STAGE_WRITE_FAILED");std::array<unsigned char,CC_SHA256_DIGEST_LENGTH> result{};need(CC_SHA256_Final(result.data(),&ctx)==1,"Hash finalization failed");const char* digits="0123456789abcdef";std::string hex;for(auto x:result){hex+=digits[x>>4];hex+=digits[x&15];}
    return O{{"bytes",number(static_cast<std::int64_t>(total))},{"sha256",hex}};
}
const std::array<const char*,4> suffixes={"","-wal","-shm","-journal"};
Value image(const std::filesystem::path& db,std::uint64_t limit,std::chrono::steady_clock::time_point end){O o;std::uint64_t total=0;for(auto suffix:suffixes){auto v=file(db.string()+suffix,{},limit,end);if(!v.null()){std::int64_t size;need(f(v,"bytes").integer(size),"Invalid image length");need(static_cast<std::uint64_t>(size)<=limit-total,"Combined image exceeds inspection capacity","COPY_CAPACITY");total+=static_cast<std::uint64_t>(size);}o.emplace(suffix,v);}return o;}
Value originalIdentities(const std::filesystem::path& db){O out;for(auto suffix:suffixes){auto p=std::filesystem::path(db.string()+suffix);struct stat st{};if(lstat(p.c_str(),&st)!=0){need(errno==ENOENT,"Cannot inspect original identity");out.emplace(suffix,nullptr);continue;}regular(st);out.emplace(suffix,O{{"device",std::to_string(st.st_dev)},{"inode",std::to_string(st.st_ino)},{"mtime_seconds",std::to_string(st.st_mtimespec.tv_sec)},{"mtime_nanoseconds",std::to_string(st.st_mtimespec.tv_nsec)},{"ctime_seconds",std::to_string(st.st_ctimespec.tv_sec)},{"ctime_nanoseconds",std::to_string(st.st_ctimespec.tv_nsec)}});}struct stat lock{};need(lstat((db.parent_path()/".profile.lock").c_str(),&lock)==0,"Original lease path disappeared");regular(lock);out.emplace("lease",O{{"device",std::to_string(lock.st_dev)},{"inode",std::to_string(lock.st_ino)}});return out;}
void privateDirectoryPath(const std::filesystem::path& p){need(p.is_absolute(),"Explicit absolute stage parent required");std::filesystem::path part;for(const auto& component:p){need(component!="."&&component!="..","Stage traversal refused");part/=component;struct stat s{};need(lstat(part.c_str(),&s)==0&&S_ISDIR(s.st_mode),"Stage parent must exist without symlinks");if(part==p)need(s.st_uid==getuid()&&(s.st_mode&077)==0,"Stage parent must be private and user-owned");}}
void makeDirectory(const std::filesystem::path& p){need(mkdir(p.c_str(),0700)==0,"New stage directory required: "+std::string(strerror(errno)),"STAGE_EXISTS_OR_UNAVAILABLE");}
struct Database {sqlite3* handle=nullptr;~Database(){if(handle)sqlite3_close_v2(handle);}};
std::int64_t pragma(sqlite3* db,const char* sql){sqlite3_stmt* statement=nullptr;need(sqlite3_prepare_v2(db,sql,-1,&statement,nullptr)==SQLITE_OK,"Candidate version read failed: "+std::string(sqlite3_errmsg(db)));struct Guard{sqlite3_stmt* p;~Guard(){sqlite3_finalize(p);}} guard{statement};need(sqlite3_step(statement)==SQLITE_ROW&&sqlite3_column_type(statement,0)==SQLITE_INTEGER,"Candidate version is unavailable");auto n=sqlite3_column_int64(statement,0);need(sqlite3_step(statement)==SQLITE_DONE,"Unexpected candidate version rows");return n;}
void candidateVersion(const std::filesystem::path& p){Database db;need(sqlite3_open_v2(p.c_str(),&db.handle,SQLITE_OPEN_READONLY|SQLITE_OPEN_NOMUTEX,nullptr)==SQLITE_OK,"Candidate database cannot be read");need(sqlite3_db_config(db.handle,SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE,1,nullptr)==SQLITE_OK,"Cannot preserve candidate WAL during inspection");need(pragma(db.handle,"PRAGMA application_id")==1178686536,"Not a Fathom application profile","WRONG_PROFILE_FORMAT");auto version=pragma(db.handle,"PRAGMA user_version");if(version!=1&&version!=2)throw Error(Status::Unsupported,"UNSUPPORTED_DATA_SCHEMA","Only exact schema1 and additive suite schema2 are supported; retain original and use its compatible application or a separately accepted migration handler (found "+std::to_string(version)+")");}
bool unfinished(const Value& authority){
    if(!f(authority,"pending").array().empty()||!f(authority,"checkpoint").array().empty())return true;
    std::set<std::string> finalized;for(auto& r:f(authority,"finalized").array())finalized.insert(text(r.array()[0]));for(auto& r:f(authority,"identity").array())if(!finalized.count(text(r.array()[0])))return true;return false;
}
std::string blob(const Value& v){auto s=text(f(v,"blob_hex"));need(s.size()%2==0&&s.find_first_not_of("0123456789abcdef")==std::string::npos,"Invalid retained blob");std::string out;for(std::size_t i=0;i<s.size();i+=2)out.push_back(static_cast<char>(std::stoi(s.substr(i,2),nullptr,16)));return out;}
Value reference(const Value& context){O out;for(auto key:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs"})out.emplace(key,f(context,key));need(std::regex_match(text(f(context,"item_id")),std::regex("fg:item:[0-9]{6}")),"Invalid historical item");need(std::regex_match(text(f(context,"variant_id")),std::regex("fg:variant:[0-9]{6}")),"Invalid historical variant");std::int64_t revision;need(f(context,"content_revision").integer(revision)&&revision>0&&!text(f(context,"content_version")).empty()&&digest(text(f(context,"source_manifest_sha256"))),"Invalid historical version/source");need(f(context,"source_refs").isArray()&&!f(context,"source_refs").array().empty(),"Invalid source reference list");std::set<std::string> refs;for(auto& v:f(context,"source_refs").array())need(!text(v).empty()&&refs.insert(text(v)).second,"Invalid duplicate source reference");return out;}
}
Reply inspectCompatibility(const CompatibilityOptions& o){
    Reply reply{Status::DefiniteFailure,o.operation,"","COMPATIBILITY_REFUSED","",nullptr};Value originalBefore,originalAfter,identitiesBefore,identitiesAfter;std::unique_ptr<ProfileLease> lease;
    std::chrono::steady_clock::time_point end;
    try{
        need(!o.operation.empty()&&!o.applicationVersion.empty()&&digest(o.applicationBuildSha256),"Explicit operation/application build/version required");
        if(o.targetDataSchema!=1&&o.targetDataSchema!=2)throw Error(Status::Unsupported,"NO_MIGRATION_HANDLER","No accepted transformation handler exists; no original data is changed. A real from/to migration requires verified pre-migration backup and accepted fixtures.");
        if(!o.stopped||o.unresolvedWrites)throw Error(Status::Busy,"QUIESCENCE_REQUIRED","Stop practice and reconcile original outstanding writes before maintenance");
        need(o.maxImageBytes>0&&o.maxImageBytes<=static_cast<std::uint64_t>(INT64_MAX)&&o.copyDeadline.count()>0&&o.copyDeadline<=std::chrono::hours(1),"Invalid inspection capacity/deadline");end=std::chrono::steady_clock::now()+o.copyDeadline;
        privateDirectoryPath(o.stage.parent_path());need(!o.stage.filename().empty()&&o.stage.filename()!="."&&o.stage.filename()!="..","Explicit new stage name required");
        auto relative=o.stage.lexically_relative(o.original.parent_path());need(relative.empty()||relative.is_absolute()||*relative.begin()=="..","Stage must be outside original profile directory");
        lease=std::make_unique<ProfileLease>(o.original,false);lease->validateFiles(true);identitiesBefore=originalIdentities(o.original);originalBefore=image(o.original,o.maxImageBytes,end);need(originalIdentities(o.original)==identitiesBefore,"Original identity changed during initial capture","PROFILE_CHANGED");
        need(f(originalBefore,"-journal").null()&&f(originalBefore,"-wal").null()==f(originalBefore,"-shm").null(),"Journal or incomplete WAL/SHM pair retained; use supported recovery before maintenance","RECOVERY_REQUIRED");
        std::uint64_t bytes=0;for(auto& kv:originalBefore.object())if(!kv.second.null()){std::int64_t n;f(kv.second,"bytes").integer(n);bytes+=static_cast<std::uint64_t>(n);}
        need(bytes<=(UINT64_MAX-64ULL*1024*1024)/2,"Stage space estimate overflow");auto space=std::filesystem::space(o.stage.parent_path());need(space.available>=2*bytes+64ULL*1024*1024,"Insufficient space for two images and staging allowance; original retained","STAGE_CAPACITY");
        makeDirectory(o.stage);auto raw=o.stage/"original-image",candidate=o.stage/"candidate";makeDirectory(raw);makeDirectory(candidate);
        for(auto suffix:suffixes)if(!f(originalBefore,suffix).null()){auto copied=file(o.original.string()+suffix,raw/(std::string("profile.sqlite")+suffix),o.maxImageBytes,end);need(copied==f(originalBefore,suffix),"Original changed before captured image","PROFILE_CHANGED");}
        need(image(raw/"profile.sqlite",o.maxImageBytes,end)==originalBefore&&image(o.original,o.maxImageBytes,end)==originalBefore&&originalIdentities(o.original)==identitiesBefore,"Raw image/original identity mismatch","PROFILE_CHANGED");
        if(o.diagnosticHook)o.diagnosticHook("raw-image-verified");
        // SHM bytes are a private candidate cache, never ownership of source locks.
        // Actual SQLite locks are acquired anew on the copied inode, with full
        // native schema/content validation and no SQL access to the original.
        for(auto suffix:suffixes)if(!f(originalBefore,suffix).null())need(file(raw/(std::string("profile.sqlite")+suffix),candidate/(std::string("profile.sqlite")+suffix),o.maxImageBytes,end)==f(originalBefore,suffix),"Candidate differs from retained image");
        candidateVersion(candidate/"profile.sqlite");StoreOptions options;options.path=candidate/"profile.sqlite";options.create=false;Reply snapshot;
        {ProfileStore store(options);snapshot=store.snapshot(o.operation+":candidate-snapshot").get();}
        need(snapshot.status==Status::Confirmed,"Candidate inspection failed: "+snapshot.code+" "+snapshot.message,"INVALID_CANDIDATE");
        if(unfinished(f(snapshot.data,"authoritative")))throw Error(Status::Busy,"RECOVERY_REQUIRED","Original pending/checkpoint/unfinished outcomes remain; reconcile them before maintenance. No original is discarded.");
        if(o.diagnosticHook)o.diagnosticHook("candidate-validated");
        lease->validateFiles(true);originalAfter=image(o.original,o.maxImageBytes,end);identitiesAfter=originalIdentities(o.original);need(originalAfter==originalBefore&&identitiesAfter==identitiesBefore,"Original changed during leased compatibility inspection","PROFILE_CHANGED");
        reply.status=Status::Confirmed;reply.code="COMPATIBLE_NO_DATA_MIGRATION";reply.message="Exact inspected schema1/2 is compatible with this application; original data and historical references remain unchanged. No transformed migration or publication occurred.";
        reply.data=O{{"application_version",o.applicationVersion},{"application_build_sha256",o.applicationBuildSha256},{"data_schema",f(snapshot.data,"authoritative").find("suite_fact")?number(2):number(1)},{"storage_envelope",number(1)},{"schema_sha256",f(snapshot.data,"schema_sha256")},{"original_before",originalBefore},{"original_after",originalAfter},{"original_identity_before",identitiesBefore},{"original_identity_after",identitiesAfter},{"original_preserved",true},{"snapshot",snapshot.data},{"stage",o.stage.string()},{"return_transport","stopped"},{"transformation_performed",false},{"runtime_content_admission","not assessed"},{"future_migration","suite schema1-to2 migration requires explicit beginSuite after verified retained backup; unsupported future versions refuse"}};
    }catch(const Error& e){reply.status=e.status;reply.code=e.code;reply.message=e.what();}
    catch(const std::exception& e){reply.message=e.what();}
    if(reply.status!=Status::Confirmed){bool preserved=false;if(lease&&!originalBefore.null())try{lease->validateFiles(true);originalAfter=image(o.original,o.maxImageBytes,std::chrono::steady_clock::now()+o.copyDeadline);identitiesAfter=originalIdentities(o.original);preserved=originalAfter==originalBefore&&identitiesAfter==identitiesBefore;}catch(const std::exception&){}reply.data=O{{"original_before",originalBefore},{"original_after",originalAfter},{"original_identity_before",identitiesBefore},{"original_identity_after",identitiesAfter},{"original_preserved",originalBefore.null()?Value{}:Value(preserved)},{"stage",o.stage.string()},{"return_transport",o.stopped?"stopped":"unchanged; explicit stop required"},{"transformation_performed",false}};}
    return reply;
}
Value historicalContentContinuity(const Reply& snapshot,const Value& available){
    need(snapshot.status==Status::Confirmed,"Historical lookup requires confirmed snapshot");auto& data=snapshot.data;auto authority=f(data,"authoritative");need(hash(authority)==text(f(data,"snapshot_sha256")),"Snapshot identity mismatch");auto evidence=authority;evidence.object().erase("rule_observation");need(hash(evidence)==text(f(data,"evidence_sha256"))&&(f(data,"schema_sha256")==Value(ProfileStore::schemaIdentity())||f(data,"schema_sha256")==Value(ProfileStore::legacySchemaIdentity())),"Evidence/schema identity mismatch");need(available.isArray(),"Available reference metadata must be an explicit array");
    std::map<std::string,Value> index;A normalized;for(auto& entry:available.array()){
        need(entry.isObject(),"Available metadata object required");for(auto& kv:entry.object())need(kv.first=="reference"||kv.first=="provenance"||kv.first=="title"||kv.first=="order","Unsupported availability/retirement/admission metadata field");
        const auto& supplied=f(entry,"reference");need(supplied.isObject()&&supplied.object().size()==6,"Available reference must have exactly six identity fields");auto ref=reference(supplied);
        need(!text(f(entry,"provenance")).empty(),"Availability metadata lacks provenance");if(auto title=entry.find("title"))text(*title);if(auto order=entry.find("order")){std::int64_t value;need(order->integer(value)&&value>=0,"Invalid display order");}
        auto key=canonical(ref);need(index.emplace(key,entry).second,"Duplicate or conflicting available historical reference");normalized.push_back(entry);
    }
    std::sort(normalized.begin(),normalized.end(),[](const Value& a,const Value& b){return canonical(f(a,"reference"))<canonical(f(b,"reference"));});
    A out;auto add=[&](const std::string& owner,const std::string& kind,const Value& context){auto ref=reference(context);auto hit=index.find(canonical(ref));out.emplace_back(O{{"owner",owner},{"kind",kind},{"reference",ref},{"original_context",context},{"status",hit==index.end()?"historical_reference_unavailable":"exact_metadata_reference_present"},{"available_metadata",hit==index.end()?Value{}:hit->second},{"runtime_admission","not assessed"},{"semantic_handler_support","not assessed"}});};
    auto profile=text(f(data,"profile_id"));validateUuid(profile);std::map<std::string,std::pair<std::string,Value>> allocations;
    for(auto& row:f(authority,"identity").array()){
        need(row.isArray()&&row.array().size()==5,"Invalid allocation row");auto& a=row.array();auto owner=text(a[0]),kind=text(a[1]);validateUuid(owner);auto context=parseCanonical(blob(a[4]));validateContext(context,kind);validateUtc(text(a[3]));
        need((kind=="Attempt"&&a[2]==f(context,"session_id"))||(kind=="FreeplayActivity"&&a[2].null()),"Allocation Session summary mismatch");need(allocations.emplace(owner,std::make_pair(kind,context)).second,"Duplicate allocation owner");if(kind=="Attempt")add(owner,"Attempt allocation",context);
    }
    std::set<std::string> finals;
    for(auto& row:f(authority,"finalized").array()){
        need(row.isArray()&&row.array().size()==11,"Invalid finalized row");auto& a=row.array();auto envelope=validateEnvelope(blob(a[1]));auto allocation=allocations.find(envelope.owner);
        need(envelope.owner==text(a[0])&&envelope.digest==text(a[2])&&finals.insert(envelope.owner).second&&allocation!=allocations.end()&&allocation->second.first==envelope.kind&&canonical(allocation->second.second)==envelope.contextBytes,"Finalized original/allocated context mismatch");
    }
    std::set<std::string> facts;
    for(auto& row:f(authority,"source_attestation").array()){
        need(row.isArray()&&row.array().size()==15,"Invalid source fact row");auto& a=row.array();auto bytes=blob(a[12]);auto value=parseCanonical(bytes);auto id=text(f(value,"fact_id"));need(facts.insert(id).second&&!allocations.count(id),"Duplicate source fact identity");std::optional<Value> linked;
        if(!f(value,"owner").null()){auto owner=allocations.find(text(f(value,"owner")));need(owner!=allocations.end()&&owner->second.first=="Attempt","Missing source original owner");linked=owner->second.second;}
        validateAttestation(value,profile,linked);
        need(content::sha256(bytes)==text(a[13])&&a[0]==f(value,"fact_id")&&a[1]==f(value,"owner")&&a[2]==f(value,"item_id")&&a[3]==f(value,"content_revision")&&blob(a[4])==canonical(f(value,"rubric_ref"))&&blob(a[5])==canonical(f(value,"context"))&&a[6]==f(value,"take_id")&&a[7]==f(value,"work_id")&&a[8]==f(value,"performer_ref")&&a[9]==f(value,"practice_utc")&&a[10]==f(value,"timezone")&&a[11]==f(value,"local_day"),"Source typed summary differs from original payload or owner");add(id,"Source attestation",f(value,"context"));
    }
    for(auto& row:f(authority,"acknowledgment").array()){need(row.isArray()&&row.array().size()==5,"Invalid acknowledgment row");auto& a=row.array();validateUuid(text(a[0]));need(!allocations.count(text(a[0]))&&facts.insert(text(a[0])).second,"Duplicate acknowledgment identity");need(std::regex_match(text(a[1]),std::regex("fg:item:[0-9]{6}")),"Invalid acknowledgment item");std::int64_t revision;need(a[2].integer(revision)&&revision>0,"Invalid acknowledgment revision");validateUtc(text(a[3]));out.emplace_back(O{{"owner",a[0]},{"kind","Acknowledgment"},{"reference",O{{"item_id",a[1]},{"content_revision",a[2]}}},{"status","item_revision_only; version/variant/provenance unavailable"},{"runtime_admission","not assessed"},{"progression_semantics","unchanged; acknowledgment remains original fact"}});}
    std::sort(out.begin(),out.end(),[](const Value& a,const Value& b){return canonical(a)<canonical(b);});
    return O{{"profile_id",f(data,"profile_id")},{"evidence_marker",f(data,"committed_seq")},{"snapshot_sha256",f(data,"snapshot_sha256")},{"evidence_sha256",f(data,"evidence_sha256")},{"references",out},{"available_metadata",normalized},{"available_metadata_sha256",hash(normalized)},{"original_authoritative",authority},{"history_rewritten",false},{"latest_substitution",false}};
}
} // namespace fathom::storage
