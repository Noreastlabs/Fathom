#include "storage/StoredZip64.hpp"
#include "storage/ProfileStore.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "content/Canonical.hpp"
#include <atomic>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

namespace {
using namespace fathom::storage;
namespace fs=std::filesystem;
using O=Value::Object;using A=Value::Array;
fs::path root,fixtures;A checks,trace,archives,headers;
Value num(std::int64_t n){return Value::fromInteger(n);}
const Value& at(const Value& v,const std::string& k){return v.object().at(k);}
std::string read(const fs::path& p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot read "+p.string());return {std::istreambuf_iterator<char>(f),{}};}
void writeNew(const fs::path& p,const std::string& bytes){if(fs::exists(p))throw std::runtime_error("No overwrite");std::ofstream f(p,std::ios::binary);f<<bytes;f.close();if(!f)throw std::runtime_error("Write failed");chmod(p.c_str(),0600);}
void check(const std::string& name,bool pass){checks.emplace_back(O{{"name",name},{"pass",pass}});std::cout<<(pass?"PASS ":"FAIL ")<<name<<'\n';if(!pass)throw std::runtime_error(name);}
struct FD {int v;explicit FD(int fd):v(fd){if(v<0)throw std::runtime_error("Fixture open failed");}~FD(){close(v);}FD(const FD&)=delete;};
StoredZip64Source source(int fd,const fs::path& p){auto s=read(p);return {fd,s.size(),fathom::content::sha256(s)};}
template<class F> void rejects(const std::string& name,const std::string& code,F f){
    try{f();}catch(const EnvelopeError& e){check(name,e.code==code);return;}check(name,false);
}
std::string hex(const std::string& s){std::string out;const char* d="0123456789abcdef";for(unsigned char c:s){out+=d[c>>4];out+=d[c&15];}return out;}
void pure(){
    for(std::uint64_t size:{0xffffffffULL,0x100000000ULL,16ULL*1024*1024*1024}){
        const auto layout=storedZip64Layout({65536,size},{0,0});
        check("64bit layout capacity and final size "+std::to_string(size),layout.archiveBytes==size+65536+400&&layout.dataOffsets[0]==63&&layout.centralOffset==size+65536+127);
        headers.emplace_back(O{{"manifest_bytes",num(65536)},{"profile_bytes",num(static_cast<std::int64_t>(size))},{"archive_bytes",num(static_cast<std::int64_t>(layout.archiveBytes))},
            {"local",A{hex(layout.localHeaders[0]),hex(layout.localHeaders[1])}},{"central",A{hex(layout.centralHeaders[0]),hex(layout.centralHeaders[1])}},{"tail",hex(layout.tail)}});
    }
    rejects("manifest zero refused","ARCHIVE_CONTAINER_CAPACITY",[]{(void)storedZip64Layout({0,1},{0,0});});
    rejects("manifest over64KiB refused","ARCHIVE_CONTAINER_CAPACITY",[]{(void)storedZip64Layout({65537,1},{0,0});});
    rejects("profile over16GiB refused","ARCHIVE_CONTAINER_CAPACITY",[]{(void)storedZip64Layout({1,16ULL*1024*1024*1024+1},{0,0});});
    rejects("overflow size refused before arithmetic","ARCHIVE_CONTAINER_CAPACITY",[]{(void)storedZip64Layout({1,UINT64_MAX},{0,0});});
    auto m=root/"crc-manifest.bin",p=root/"crc-profile.bin";writeNew(m,"123456789");writeNew(p,"123456789");
    FD mf(open(m.c_str(),O_RDONLY|O_NOFOLLOW)),pf(open(p.c_str(),O_RDONLY|O_NOFOLLOW));
    std::array<StoredZip64Source,2> inputs{source(mf.v,m),source(pf.v,p)};
    auto path=root/"crc-stage.zip";FD output(open(path.c_str(),O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW,0600));
    check("fixture source seek",lseek(mf.v,3,SEEK_SET)==3&&lseek(pf.v,5,SEEK_SET)==5);
    auto result=writeStoredZip64(output.v,inputs,[]{}).file;
    check("CRC32 knownvector actualentry0",at(at(result,"entries").array()[0],"crc32")==num(3421780262LL));
    check("CRC32 knownvector actualentry1",at(at(result,"entries").array()[1],"crc32")==num(3421780262LL));
    check("borrowed source positions preserved",lseek(mf.v,0,SEEK_CUR)==3&&lseek(pf.v,0,SEEK_CUR)==5);
    archives.emplace_back(O{{"path",path.string()},{"manifest",m.string()},{"profile",p.string()},{"receipt",result},{"classification","synthetic raw CRC helper input, not a validated profile"}});
    rejects("existing output not overwritten","ARCHIVE_CONTAINER_OUTPUT_EXISTS",[&]{(void)writeStoredZip64(output.v,inputs,[]{});});
    auto fresh=[&](const std::string& name,const std::array<StoredZip64Source,2>& in,const std::string& code){
        auto dest=root/(name+".zip");FD out(open(dest.c_str(),O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW,0600));
        rejects(name,code,[&]{(void)writeStoredZip64(out.v,in,[]{});});
        check(name+" refused before writing",fs::file_size(dest)==0);
    };
    auto bad=inputs;bad[0].sha256=std::string(64,'0');fresh("wrongsourcehash",bad,"ARCHIVE_CONTAINER_CHANGED");
    bad=inputs;bad[0].bytes=8;fresh("wrongsourcesize",bad,"ARCHIVE_CONTAINER_CHANGED");
    bad=inputs;bad[1]=bad[0];fresh("sourcealias",bad,"ARCHIVE_CONTAINER_INVALID");
    check("descriptor refusal sources retained",read(m)=="123456789"&&read(p)=="123456789");
}
Reply observe(const std::string& name,ProfileStore::Future future,Status expected=Status::Confirmed){
    auto r=future.get();trace.emplace_back(O{{"name",name},{"status",statusName(r.status)},{"code",r.code},{"data",r.data}});check(name+" status",r.status==expected);return r;
}
fs::path profile(const std::string& name,const std::string& fixture="settled-stage"){
    auto p=root/name;fs::create_directory(p);chmod(p.c_str(),0700);fs::copy_file(fixtures/fixture/"profile.sqlite",p/"profile.sqlite");chmod((p/"profile.sqlite").c_str(),0600);return p/"profile.sqlite";
}
StoreOptions storeOptions(const fs::path& p){StoreOptions o;o.path=p;return o;}
BackupSnapshotOptions options(const std::string& name){BackupSnapshotOptions b;b.destinationDirectory=root/name;b.stopped=true;b.unresolvedWrites=false;b.includeArchiveManifest=true;b.includeArchiveContainer=true;return b;}
void success(const std::string& which){
    ProfileStore store(storeOptions(profile(which+"-profile",which)));
    auto before=observe(which+" before",store.snapshot(newUuid()));auto b=options(which+"-archive");
    auto r=observe(which+" container",store.prepareBackupSnapshot(newUuid(),b));
    const auto& container=at(r.data,"archive");const auto& receipt=at(container,"file");
    check(which+" staged only",at(container,"staged")==Value(true)&&at(container,"published")==Value(false)&&at(r.data,"archive_published")==Value(false)&&at(r.data,"restore_performed")==Value(false));
    check(which+" native exact container bytes",fathom::content::sha256(read(b.destinationDirectory/"candidate.zip"))==at(receipt,"sha256").string());
    const auto& entries=at(receipt,"entries").array();
    check(which+" native manifest receipt binding",at(entries[0],"sha256")==at(at(at(r.data,"manifest"),"file"),"sha256")&&at(entries[0],"bytes")==at(at(at(r.data,"manifest"),"file"),"bytes"));
    check(which+" native database receipt binding",at(entries[1],"sha256")==at(at(r.data,"file"),"sha256")&&at(entries[1],"bytes")==at(at(r.data,"file"),"bytes"));
    auto after=observe(which+" after",store.snapshot(newUuid()));check(which+" complete source authority unchanged",at(before.data,"authoritative")==at(after.data,"authoritative"));
    archives.emplace_back(O{{"path",(b.destinationDirectory/"candidate.zip").string()},{"manifest",(b.destinationDirectory/"manifest.json").string()},
        {"profile",(b.destinationDirectory/"profile.sqlite").string()},{"receipt",receipt},{"classification","native verified standalone profile archive stage; not published/restored"}});
}
void native(){
    success("empty-stage");success("settled-stage");
    {
        ProfileStore store(storeOptions(profile("option-profile","empty-stage")));auto b=options("manifest-only-stage");b.includeArchiveContainer=false;
        auto r=observe("manifest-only default container off",store.prepareBackupSnapshot(newUuid(),b));check("container absent when disabled",r.data.find("archive")==nullptr&&!fs::exists(b.destinationDirectory/"candidate.zip"));
        b=options("invalid-options-stage");b.includeArchiveManifest=false;
        auto bad=observe("container without manifest",store.prepareBackupSnapshot(newUuid(),b),Status::DefiniteFailure);
        check("missingmanifest explicit refusal before creation",bad.code=="ARCHIVE_MANIFEST_REQUIRED"&&!fs::exists(b.destinationDirectory));
    }
    const std::vector<std::string> modes{"cancel-stream","source-after-prepass","corrupt-written","handoff-change","replace-verified","existing-output","symlink-output"};
    for(const auto& mode:modes){
        auto o=storeOptions(profile(mode+"-profile"));auto b=options(mode+"-stage");
        bool reached=false;std::atomic<bool> cancel{false};A phases;
        const auto victim=root/(mode+"-victim.txt");if(mode=="symlink-output")writeNew(victim,"Preserve previous usable file");
        o.diagnosticHook=[&](const std::string& phase,const std::string&){
            phases.emplace_back(phase);
            if(mode=="cancel-stream"&&phase=="archive_data_chunk"){reached=true;cancel=true;}
            if(mode=="source-after-prepass"&&phase=="archive_sources_verified"){
                reached=true;std::ofstream f(b.destinationDirectory/"profile.sqlite",std::ios::binary|std::ios::app);f.put('x');f.close();if(!f)throw std::runtime_error("Mutation write failed");
            }
            if(mode=="corrupt-written"&&phase=="archive_written"){
                reached=true;FD fd(open((b.destinationDirectory/"candidate.zip").c_str(),O_WRONLY|O_NOFOLLOW));if(pwrite(fd.v,"X",1,0)!=1)throw std::runtime_error("Corruption write failed");
            }
            if(mode=="handoff-change"&&phase=="archive_before_return"){
                reached=true;std::ofstream f(b.destinationDirectory/"candidate.zip",std::ios::binary|std::ios::app);f.put('x');f.close();if(!f)throw std::runtime_error("Handoff mutation failed");
            }
            if(mode=="replace-verified"&&phase=="backup_archive_verified"){
                reached=true;auto p=b.destinationDirectory/"candidate.zip";fs::rename(p,b.destinationDirectory/"original-candidate.zip");fs::copy_file(b.destinationDirectory/"original-candidate.zip",p);chmod(p.c_str(),0600);
            }
            if((mode=="existing-output"||mode=="symlink-output")&&phase=="backup_archive_before_create"){
                reached=true;auto p=b.destinationDirectory/"candidate.zip";
                if(mode=="existing-output")writeNew(p,"Preserve prior candidate");else fs::create_symlink(victim,p);
            }
        };
        ProfileStore store(o);auto before=observe(mode+" before",store.snapshot(newUuid()));b.cancelled=[&]{return cancel.load();};
        auto r=observe(mode,store.prepareBackupSnapshot(newUuid(),b),Status::DefiniteFailure);
        const std::string code=mode=="cancel-stream"?"SNAPSHOT_CANCELLED":(mode=="replace-verified"||mode=="handoff-change")?"SNAPSHOT_CHANGED":
            (mode=="existing-output"||mode=="symlink-output")?"ARCHIVE_CONTAINER_OUTPUT_EXISTS":"ARCHIVE_CONTAINER_CHANGED";
        check(mode+" actualphase exactcode no receipt",reached&&r.code==code&&r.data.null());cancel=false;
        auto after=observe(mode+" after",store.snapshot(newUuid()));check(mode+" source authority retained",at(before.data,"authoritative")==at(after.data,"authoritative"));
        if(mode=="existing-output")check("prior candidate bytes preserved",read(b.destinationDirectory/"candidate.zip")=="Preserve prior candidate");
        if(mode=="symlink-output")check("symlink target untouched",fs::is_symlink(b.destinationDirectory/"candidate.zip")&&read(victim)=="Preserve previous usable file");
        trace.emplace_back(O{{"case",mode},{"actual_phases",phases}});
    }
}
}
int main(int argc,char** argv){
    if(argc!=3){std::cerr<<"Usage: archive_container_tests /absolute/E /absolute/E/fixtures\n";return 64;}
    bool owned=false,passed=false;
    try{
        auto evidence=fs::canonical(argv[1]);fixtures=fs::canonical(argv[2]);if(fixtures!=evidence/"fixtures")throw std::runtime_error("Only copied lane fixtures allowed");
        root=evidence/"test-data"/"container01";if(fs::exists(root))throw std::runtime_error("No run overwrite");
        fs::create_directories(root.parent_path());chmod(root.parent_path().c_str(),0700);
        if(!fs::create_directory(root))throw std::runtime_error("Run directory exists");
        owned=true;chmod(root.c_str(),0700);
        pure();native();passed=true;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';if(owned)writeNew(root/"failure.txt",e.what());}
    if(owned){writeNew(root/"checks.json",canonical(O{{"status",passed?"PASS":"FAIL"},{"synthetic",true},{"human_work",false},{"archive_published",false},{"restore_performed",false},{"checks",checks},{"trace",trace},{"successful_archives",archives},{"synthetic_headers",headers}}));}
    std::cout<<checks.size()<<" checks, "<<(passed?"PASS":"FAIL")<<'\n';return passed?0:1;
}
