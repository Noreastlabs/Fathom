#include "storage/ArchiveReader.hpp"
#include "juce_core/zip/juce_zlib.h"
#include <CommonCrypto/CommonDigest.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <fcntl.h>
#include <limits>
#include <memory>
#include <set>
#include <sys/stat.h>
#include <unistd.h>

namespace fathom::storage {
namespace {
using U=std::uint64_t;using O=Value::Object;using A=Value::Array;
constexpr U archiveLimit=17ULL*1024*1024*1024,profileLimit=16ULL*1024*1024*1024;
constexpr std::size_t chunk=1048576;
void need(bool yes,const std::string& message,const std::string& code="ARCHIVE_FORMAT"){
    if(!yes)throw EnvelopeError(code,message);
}
Value num(U n){need(n<=static_cast<U>(INT64_MAX),"Unrepresentable receipt number");return Value::fromInteger(static_cast<std::int64_t>(n));}
struct FD {int v;explicit FD(int x):v(x){need(v>=0,"Cannot open selected or private candidate file","ARCHIVE_PATH");}~FD(){close(v);}FD(const FD&)=delete;FD& operator=(const FD&)=delete;};
bool same(const struct stat& a,const struct stat& b){
    return a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_size==b.st_size&&a.st_mode==b.st_mode&&
        a.st_uid==b.st_uid&&a.st_nlink==b.st_nlink&&
        a.st_mtimespec.tv_sec==b.st_mtimespec.tv_sec&&a.st_mtimespec.tv_nsec==b.st_mtimespec.tv_nsec&&
        a.st_ctimespec.tv_sec==b.st_ctimespec.tv_sec&&a.st_ctimespec.tv_nsec==b.st_ctimespec.tv_nsec;
}
struct stat pinned(int fd,const std::filesystem::path& path,bool privateFile){
    struct stat a{},b{};
    need(fstat(fd,&a)==0&&lstat(path.c_str(),&b)==0&&S_ISREG(a.st_mode)&&a.st_size>=0&&same(a,b),"Selected file changed or is not regular","ARCHIVE_CHANGED");
    if(privateFile)need(a.st_uid==getuid()&&(a.st_mode&077)==0&&a.st_nlink==1,"Candidate must remain private and unaliased","ARCHIVE_CHANGED");
    return a;
}
void ancestors(const std::filesystem::path& path){
    need(path.is_absolute()&&!path.filename().empty(),"Explicit absolute path required","ARCHIVE_PATH");
    std::filesystem::path p;
    for(const auto& part:path.parent_path()){
        need(part!="."&&part!="..","Path traversal refused","ARCHIVE_PATH");p/=part;
        struct stat s{};need(lstat(p.c_str(),&s)==0&&S_ISDIR(s.st_mode),"Parent must exist without symlinks","ARCHIVE_PATH");
    }
    need(path.filename()!="."&&path.filename()!="..","Path traversal refused","ARCHIVE_PATH");
}
U add(U a,U b){need(b<=UINT64_MAX-a,"ZIP offset overflow");return a+b;}
std::string bytes(int fd,U offset,std::size_t count,U bound,const std::function<void()>& check){
    need(offset<=bound&&count<=bound-offset&&offset<=static_cast<U>(INT64_MAX),"ZIP range outside selected file");
    std::string out(count,'\0');std::size_t at=0;
    while(at<count){check();auto n=pread(fd,out.data()+at,count-at,static_cast<off_t>(offset+at));if(n<0&&errno==EINTR)continue;need(n>0,"Selected archive read failed","ARCHIVE_IO");at+=static_cast<std::size_t>(n);}
    return out;
}
U le(const std::string& b,std::size_t at,std::size_t width){
    need(width<=8&&at<=b.size()&&width<=b.size()-at,"Truncated ZIP field");U n=0;for(std::size_t i=0;i<width;++i)n|=static_cast<U>(static_cast<unsigned char>(b[at+i]))<<(8*i);return n;
}
std::string zip64Extra(const std::string& extra,std::size_t expected){
    std::string out;bool seen=false;
    for(std::size_t at=0;at<extra.size();){
        auto id=le(extra,at,2),size=le(extra,at+2,2);at+=4;
        need(size<=extra.size()-at,"Truncated ZIP extra field");
        if(id==1){need(!seen&&size==expected,"Duplicate or malformed ZIP64 extra field");seen=true;out=extra.substr(at,static_cast<std::size_t>(size));}
        at+=static_cast<std::size_t>(size);
    }
    need(expected==0||seen,"Missing ZIP64 sizes/offset");return out;
}
struct Entry {std::string name;U method=0,flags=0,crc=0,size=0,compressed=0,offset=0,data=0,end=0,alternateEnd=0;bool wide=false;};
std::array<Entry,2> directory(int fd,U size,const std::function<void()>& check){
    need(size>=22&&size<=archiveLimit,"Archive outside accepted capacity","ARCHIVE_CAPACITY");
    auto tailSize=static_cast<std::size_t>(std::min<U>(size,65557));auto tail=bytes(fd,size-tailSize,tailSize,size,check);
    std::optional<std::size_t> position;
    for(std::size_t i=0;i+22<=tail.size();++i)if(le(tail,i,4)==0x06054b50&&i+22+le(tail,i+20,2)==tail.size()){
        need(!position,"Ambiguous terminal ZIP record");position=i;
    }
    need(position.has_value(),"Missing terminal ZIP record");auto e=tail.substr(*position,22);U end=size-tailSize+*position;
    need((le(e,4,2)==0||le(e,4,2)==65535)&&(le(e,6,2)==0||le(e,6,2)==65535),"Multi-disk ZIP refused");
    U count=le(e,10,2),centralBytes=le(e,12,4),central=le(e,16,4),terminal=end;
    bool wide=count==65535||le(e,8,2)==65535||centralBytes==0xffffffffULL||central==0xffffffffULL||le(e,4,2)==65535||le(e,6,2)==65535;
    if(!wide&&end>=20&&!(central<=end&&centralBytes==end-central))
        wide=le(bytes(fd,end-20,4,size,check),0,4)==0x07064b50;
    if(wide){
        need(end>=20,"Missing ZIP64 locator");auto locator=bytes(fd,end-20,20,size,check);
        need(le(locator,0,4)==0x07064b50&&le(locator,4,4)==0&&le(locator,16,4)==1,"Invalid ZIP64 locator");
        U zpos=le(locator,8,8);auto z=bytes(fd,zpos,56,size,check);
        need(le(z,0,4)==0x06064b50&&le(z,4,8)==44&&add(zpos,56)==end-20,"Unsupported ZIP64 terminal record");
        need(le(z,14,2)==45&&le(z,16,4)==0&&le(z,20,4)==0&&le(z,24,8)==2&&le(z,32,8)==2,"Unsupported ZIP64 disks/count/version");
        count=2;centralBytes=le(z,40,8);central=le(z,48,8);terminal=zpos;
        need((le(e,8,2)==65535||le(e,8,2)==2)&&(le(e,10,2)==65535||le(e,10,2)==2)&&
             (le(e,12,4)==0xffffffffULL||le(e,12,4)==centralBytes)&&
             (le(e,16,4)==0xffffffffULL||le(e,16,4)==central),"ZIP32/64 terminal mismatch");
    }else need(le(e,8,2)==count,"ZIP entry counts disagree");
    need(count==2&&centralBytes<=2ULL*(46+65535*3)&&add(central,centralBytes)==terminal,"Exactly two bounded contiguous central entries required");
    auto c=bytes(fd,central,static_cast<std::size_t>(centralBytes),size,check);
    std::array<Entry,2> out;std::set<std::string> names;std::size_t at=0;
    for(auto& entry:out){
        need(le(c,at,4)==0x02014b50,"Invalid central signature");
        auto version=le(c,at+6,2),creator=le(c,at+4,2)>>8,nameSize=le(c,at+28,2),extraSize=le(c,at+30,2),comment=le(c,at+32,2);
        U endAt=add(at,add(46,add(nameSize,add(extraSize,comment))));need(endAt<=c.size(),"Central entry exceeds directory");
        entry.flags=le(c,at+8,2);entry.method=le(c,at+10,2);entry.crc=le(c,at+16,4);
        entry.compressed=le(c,at+20,4);entry.size=le(c,at+24,4);entry.offset=le(c,at+42,4);
        U disk=le(c,at+34,2);const bool d64=disk==65535;
        entry.name=c.substr(at+46,static_cast<std::size_t>(nameSize));
        need((entry.name=="manifest.json"||entry.name=="profile.sqlite")&&names.insert(entry.name).second,"Exact unique archive entry names required");
        need((entry.flags&~0x080eULL)==0&&(entry.method==0||entry.method==8)&&(entry.method==8||(entry.flags&6)==0),"Unsupported ZIP flags/compression");
        auto attributes=le(c,at+38,4),type=(attributes>>16)&0170000;
        need((attributes&0x10)==0&&(creator!=3||type==0||type==0100000),"Directory/symlink/special entry refused");
        const bool s64=entry.size==0xffffffffULL,c64=entry.compressed==0xffffffffULL,o64=entry.offset==0xffffffffULL;
        entry.wide=s64||c64||o64||d64;
        auto x=zip64Extra(c.substr(at+46+static_cast<std::size_t>(nameSize),static_cast<std::size_t>(extraSize)),8u*(s64+c64+o64)+4u*d64);std::size_t xat=0;
        if(s64){entry.size=le(x,xat,8);xat+=8;}if(c64){entry.compressed=le(x,xat,8);xat+=8;}if(o64){entry.offset=le(x,xat,8);xat+=8;}if(d64)disk=le(x,xat,4);
        need(disk==0,"Entry on another disk");
        need(version>=(entry.method==8?20u:10u)&&version<=45&&(!(s64||c64||o64||d64)||version==45),"Unsupported entry version");
        U limit=entry.name=="manifest.json"?65536:profileLimit;
        need(entry.size>0&&entry.size<=limit&&entry.compressed>0&&entry.compressed<=archiveLimit,"Entry outside accepted capacity","ARCHIVE_CAPACITY");
        need(entry.method!=0||entry.size==entry.compressed,"Stored size mismatch");
        auto local=bytes(fd,entry.offset,30,size,check);
        need(le(local,0,4)==0x04034b50&&le(local,6,2)==entry.flags&&le(local,8,2)==entry.method&&
             le(local,4,2)>=(entry.method==8?20u:10u)&&le(local,4,2)<=45,"Local and central header mismatch");
        auto ln=le(local,26,2),lx=le(local,28,2);auto variable=bytes(fd,add(entry.offset,30),static_cast<std::size_t>(ln+lx),size,check);
        need(variable.substr(0,static_cast<std::size_t>(ln))==entry.name,"Local name mismatch");
        U ls=le(local,22,4),lc=le(local,18,4);bool ls64=ls==0xffffffffULL,lc64=lc==0xffffffffULL;
        need(ls64==lc64,"Local ZIP64 requires both size fields");
        auto localExtra=zip64Extra(variable.substr(static_cast<std::size_t>(ln)),8u*(ls64+lc64));xat=0;
        if(ls64){ls=le(localExtra,xat,8);xat+=8;}if(lc64)lc=le(localExtra,xat,8);
        need(!(ls64||lc64)||le(local,4,2)==45,"ZIP64 local version required");
        entry.wide=entry.wide||ls64||lc64;
        bool descriptor=(entry.flags&8)!=0;
        if(descriptor)need((le(local,14,4)==0||le(local,14,4)==entry.crc)&&(ls==0||ls==entry.size)&&(lc==0||lc==entry.compressed),"Descriptor local values mismatch");
        else need(le(local,14,4)==entry.crc&&ls==entry.size&&lc==entry.compressed,"Local CRC/size mismatch");
        entry.data=add(entry.offset,add(30,ln+lx));entry.end=add(entry.data,entry.compressed);
        if(descriptor){
            // CRC may itself equal the optional descriptor signature. Match the complete
            // forms against central values and resolve their exact next boundary below. No data scan.
            const auto plainSize=static_cast<std::size_t>(4+(entry.wide?16:8));
            auto dd=bytes(fd,entry.end,plainSize,size,check);
            auto matches=[&](const std::string& b,std::size_t d){
                return le(b,d,4)==entry.crc&&le(b,d+4,entry.wide?8:4)==entry.compressed&&
                       le(b,d+4+(entry.wide?8:4),entry.wide?8:4)==entry.size;
            };
            const bool plainMatches=matches(dd,0);
            bool signedMatches=false;
            if(le(dd,0,4)==0x08074b50&&entry.end<=size&&plainSize+4<=size-entry.end){
                auto signedBytes=bytes(fd,entry.end,plainSize+4,size,check);signedMatches=matches(signedBytes,4);
            }
            need(plainMatches||signedMatches,"Data descriptor mismatch");
            if(plainMatches&&signedMatches)entry.alternateEnd=add(entry.end,plainSize+4);
            entry.end=add(entry.end,plainSize+(plainMatches?0:4));
        }
        need(entry.end<=central,"Entry overlaps directory");at=static_cast<std::size_t>(endAt);
    }
    need(at==c.size(),"Additional central entry/bytes refused");
    auto first=out[0].offset<out[1].offset?0u:1u;auto second=1u-first;
    for(auto i:{first,second}){
        const auto boundary=i==first?out[second].offset:central;
        if(out[i].end!=boundary&&out[i].alternateEnd==boundary)out[i].end=out[i].alternateEnd;
    }
    need(out[first].offset==0&&out[first].end==out[second].offset&&out[second].end==central,"Overlapping or unaccounted ZIP ranges");
    return out;
}
class Hash {
    CC_SHA256_CTX c{};
public:
    Hash(){need(CC_SHA256_Init(&c)==1,"SHA initialization failed","ARCHIVE_IO");}
    void addBytes(const char* p,std::size_t n){need(n<=chunk&&CC_SHA256_Update(&c,p,static_cast<CC_LONG>(n))==1,"SHA update failed","ARCHIVE_IO");}
    std::string finish(){std::array<unsigned char,32> b{};need(CC_SHA256_Final(b.data(),&c)==1,"SHA finish failed","ARCHIVE_IO");const char* h="0123456789abcdef";std::string s;for(auto v:b){s+=h[v>>4];s+=h[v&15];}return s;}
};
std::string fileHash(int fd,U size,const std::function<void()>& check){Hash h;for(U at=0;at<size;){auto b=bytes(fd,at,static_cast<std::size_t>(std::min<U>(chunk,size-at)),size,check);h.addBytes(b.data(),b.size());at+=b.size();}check();return h.finish();}
struct Inflate {z_stream stream{};bool initialized=false;~Inflate(){if(initialized)inflateEnd(&stream);}};
std::string extract(int input,U archiveSize,int output,const Entry& e,const std::function<void()>& check,
                    const std::function<void(const std::string&)>& hook){
    Hash h;uLong crc=crc32(0L,Z_NULL,0);U expanded=0,consumed=0;Inflate z;
    if(e.method==8){need(inflateInit2(&z.stream,-MAX_WBITS)==Z_OK,"Cannot initialize raw DEFLATE","ARCHIVE_DEFLATE");z.initialized=true;}
    std::vector<char> out(chunk);bool ended=false;
    auto emit=[&](const char* data,std::size_t size){
        need(size<=e.size-expanded,"Expanded entry exceeds declared size","ARCHIVE_DEFLATE");
        h.addBytes(data,size);crc=crc32(crc,reinterpret_cast<const Bytef*>(data),static_cast<uInt>(size));
        std::size_t done=0;while(done<size){check();auto n=write(output,data+done,size-done);if(n<0&&errno==EINTR)continue;need(n>0,"Candidate write failed","ARCHIVE_IO");done+=static_cast<std::size_t>(n);}
        expanded+=size;if(hook)hook("extract_chunk");check();
    };
    while(consumed<e.compressed){
        check();auto b=bytes(input,add(e.data,consumed),static_cast<std::size_t>(std::min<U>(chunk,e.compressed-consumed)),archiveSize,check);consumed+=b.size();
        if(e.method==0){emit(b.data(),b.size());continue;}
        z.stream.next_in=reinterpret_cast<const Bytef*>(b.data());z.stream.avail_in=static_cast<uInt>(b.size());
        do{
            check();auto before=z.stream.avail_in;z.stream.next_out=reinterpret_cast<Bytef*>(out.data());z.stream.avail_out=static_cast<uInt>(out.size());
            int rc=inflate(&z.stream,Z_NO_FLUSH);auto produced=out.size()-z.stream.avail_out;
            if(rc==Z_BUF_ERROR&&before==0&&produced==0&&consumed<e.compressed)break;
            need(rc==Z_OK||rc==Z_STREAM_END,"Invalid or truncated raw DEFLATE","ARCHIVE_DEFLATE");emit(out.data(),produced);
            if(rc==Z_STREAM_END){need(z.stream.avail_in==0&&consumed==e.compressed,"Trailing DEFLATE stream/bytes","ARCHIVE_DEFLATE");ended=true;break;}
            need(produced!=0||z.stream.avail_in<before,"DEFLATE made no progress","ARCHIVE_DEFLATE");
        }while(z.stream.avail_in>0||z.stream.avail_out==0);
        if(ended)break;
    }
    need((e.method==0||ended)&&expanded==e.size,"Incomplete compressed entry","ARCHIVE_DEFLATE");
    need(static_cast<U>(crc)==e.crc,"ZIP CRC mismatch","ARCHIVE_CRC");
    need(fsync(output)==0,"Candidate sync failed","ARCHIVE_IO");return h.finish();
}
Value identity(const struct stat& s,const std::string& sha){return O{{"device",std::to_string(s.st_dev)},{"inode",std::to_string(s.st_ino)},{"bytes",num(static_cast<U>(s.st_size))},{"sha256",sha}};}
}
Value previewProfileArchive(const ArchiveReaderOptions& options){
    const auto started=std::chrono::steady_clock::now();
    need(options.timeout.count()>0&&options.timeout<=std::chrono::seconds(300),"Archive deadline outside policy","ARCHIVE_OPTIONS");
    auto deadline=started+options.timeout;
    auto timed=[&]{if(options.cancelled&&options.cancelled())throw EnvelopeError("ARCHIVE_CANCELLED","Preview cancelled; no live profile changed");
        need(std::chrono::steady_clock::now()<deadline,"Archive preview deadline reached","ARCHIVE_DEADLINE");};
    need(options.additionalReserveBytes<=17ULL*1024*1024*1024,"Restore reserve exceeds accepted bound","ARCHIVE_OPTIONS");
    timed();ancestors(options.archive);ancestors(options.candidateDirectory);
    FD input(open(options.archive.c_str(),O_RDONLY|O_NOFOLLOW|O_CLOEXEC));auto initial=pinned(input.v,options.archive,false);
    need(static_cast<U>(initial.st_size)<=archiveLimit,"Selected archive exceeds17GiB","ARCHIVE_CAPACITY");
    auto checkInput=[&]{timed();need(same(initial,pinned(input.v,options.archive,false)),"Selected archive changed","ARCHIVE_CHANGED");};
    auto entries=directory(input.v,static_cast<U>(initial.st_size),checkInput);
    auto archiveSha=fileHash(input.v,static_cast<U>(initial.st_size),checkInput);
    FD parent(open(options.candidateDirectory.parent_path().c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));struct stat parentStat{};
    need(fstat(parent.v,&parentStat)==0&&parentStat.st_uid==getuid()&&(parentStat.st_mode&077)==0,"Candidate parent must be private user-owned directory","ARCHIVE_PATH");
    U expanded=0;for(const auto& e:entries)expanded=add(expanded,e.size);
    need(std::filesystem::space(options.candidateDirectory.parent_path()).available>=expanded*(options.reserveSecondCandidate?2:1)+options.additionalReserveBytes+64ULL*1024*1024,"Insufficient isolated candidate space","ARCHIVE_CAPACITY");
    checkInput();need(mkdirat(parent.v,options.candidateDirectory.filename().c_str(),0700)==0,"Candidate directory already exists or cannot be created","ARCHIVE_DESTINATION_EXISTS");
    FD dir(openat(parent.v,options.candidateDirectory.filename().c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));struct stat dirStat{};need(fstat(dir.v,&dirStat)==0,"Cannot bind candidate directory","ARCHIVE_PATH");
    auto checkDirectory=[&]{checkInput();struct stat a{},b{};need(fstat(dir.v,&a)==0&&lstat(options.candidateDirectory.c_str(),&b)==0&&S_ISDIR(a.st_mode)&&S_ISDIR(b.st_mode)&&a.st_dev==dirStat.st_dev&&a.st_ino==dirStat.st_ino&&a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_uid==getuid()&&(a.st_mode&077)==0,"Candidate directory changed","ARCHIVE_CHANGED");};
    std::array<std::unique_ptr<FD>,2> outputs;std::array<struct stat,2> states{};std::array<std::string,2> hashes;
    for(std::size_t i=0;i<2;++i){
        checkDirectory();const auto& e=entries[i];outputs[i]=std::make_unique<FD>(openat(dir.v,e.name.c_str(),O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600));
        hashes[i]=extract(input.v,static_cast<U>(initial.st_size),outputs[i]->v,e,checkDirectory,options.diagnosticHook);
        states[i]=pinned(outputs[i]->v,options.candidateDirectory/e.name,true);
        need(static_cast<U>(states[i].st_size)==e.size&&fileHash(outputs[i]->v,e.size,checkDirectory)==hashes[i],"Extracted candidate reread mismatch","ARCHIVE_CHANGED");
    }
    auto checkAll=[&]{checkDirectory();for(std::size_t i=0;i<2;++i)need(same(states[i],pinned(outputs[i]->v,options.candidateDirectory/entries[i].name,true)),"Candidate changed after extraction","ARCHIVE_CHANGED");};
    if(options.diagnosticHook)options.diagnosticHook("extracted");
    checkAll();
    const auto mi=entries[0].name=="manifest.json"?0u:1u,di=1u-mi;
    auto text=bytes(outputs[mi]->v,0,static_cast<std::size_t>(entries[mi].size),entries[mi].size,checkAll);
    Value manifest;
    try{json::Limits limits;limits.bytes=65536;manifest=json::parse(text,limits);need(canonical(manifest)==text,"Manifest must use exact canonical storage JSON","ARCHIVE_MANIFEST");}
    catch(const json::Error& e){throw EnvelopeError("ARCHIVE_MANIFEST",e.what());}
    need(manifest.isObject()&&manifest.object().size()==6&&manifest.find("format")&&*manifest.find("format")==Value("Fathom.ProfileArchive")&&
         manifest.find("archive_version")&&*manifest.find("archive_version")==num(1)&&manifest.find("data_schema_version")&&(*manifest.find("data_schema_version")==num(1)||*manifest.find("data_schema_version")==num(2))&&
         manifest.find("snapshot")&&manifest.find("profile_bytes")&&*manifest.find("profile_bytes")==num(entries[di].size)&&
         manifest.find("profile_sha256")&&*manifest.find("profile_sha256")==Value(hashes[di]),"Unsupported or mismatched archive manifest","ARCHIVE_MANIFEST");
    if(options.diagnosticHook)options.diagnosticHook("before_sql");
    checkAll();
    auto projected=detail::inspectArchiveCandidate(outputs[di]->v,options.candidateDirectory/"profile.sqlite",checkAll,options.diagnosticHook);
    need(projected==manifest,"Manifest summary does not match verified original profile","ARCHIVE_MANIFEST");
    if(options.diagnosticHook)options.diagnosticHook("before_receipt");
    checkAll();
    // Rebind the entire selected input after all extraction/SQL work; no mutation or publication.
    need(fileHash(input.v,static_cast<U>(initial.st_size),checkAll)==archiveSha,"Archive changed before preview receipt","ARCHIVE_CHANGED");checkAll();
    return O{{"format","Fathom.ArchiveCandidatePreview"},{"preview_version",num(1)},{"archive",identity(initial,archiveSha)},
        {"candidate_directory",options.candidateDirectory.string()},{"manifest_file",identity(states[mi],hashes[mi])},{"profile_file",identity(states[di],hashes[di])},
        {"manifest",manifest},{"candidate_validated",true},{"restore_performed",false},{"archive_published",false},{"required_resume_state","stopped"},
        {"content_compatibility","NOT ASSESSED: original references retained; preview does not admit current playback"},
        {"elapsed_ms",num(static_cast<U>(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count()))}};
}
} // namespace fathom::storage
