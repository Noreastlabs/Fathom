#include "storage/StoredZip64.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <juce_core/zip/juce_zlib.h>
#include <algorithm>
#include <cerrno>
#include <regex>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

namespace fathom::storage {
namespace {
constexpr std::uint64_t profileLimit=16ULL*1024*1024*1024;
constexpr std::uint64_t archiveLimit=17ULL*1024*1024*1024;
constexpr std::size_t chunk=1048576;
const std::array<std::string,2> names{"manifest.json","profile.sqlite"};
void need(bool ok,const char* message,const char* code="ARCHIVE_CONTAINER_INVALID"){
    if(!ok)throw EnvelopeError(code,message);
}
void little(std::string& s,std::uint64_t n,unsigned bytes){
    for(unsigned i=0;i<bytes;++i){s+=static_cast<char>(n&255);n>>=8;}
    need(n==0,"ZIP field does not fit its declared width");
}
std::uint64_t plus(std::uint64_t a,std::uint64_t b){
    need(a<=archiveLimit&&b<=archiveLimit-a,"Archive exceeds accepted17GiB bound","ARCHIVE_CONTAINER_CAPACITY");
    return a+b;
}
void tick(const std::function<void()>& check){if(check)check();}
void event(const std::function<void(const std::string&)>& hook,const std::string& s){if(hook)hook(s);}
bool same(const struct stat& a,const struct stat& b){
    return a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_size==b.st_size&&a.st_mode==b.st_mode&&a.st_uid==b.st_uid&&a.st_nlink==b.st_nlink&&
        a.st_mtimespec.tv_sec==b.st_mtimespec.tv_sec&&a.st_mtimespec.tv_nsec==b.st_mtimespec.tv_nsec&&
        a.st_ctimespec.tv_sec==b.st_ctimespec.tv_sec&&a.st_ctimespec.tv_nsec==b.st_ctimespec.tv_nsec;
}
struct stat identity(int fd){
    struct stat st{};
    need(fd>=0&&fstat(fd,&st)==0&&S_ISREG(st.st_mode)&&st.st_uid==getuid()&&st.st_nlink==1&&(st.st_mode&077)==0&&st.st_size>=0,
         "Archive descriptors must remain private regular files","ARCHIVE_CONTAINER_CHANGED");
    return st;
}
bool aliases(const struct stat& a,const struct stat& b){return a.st_dev==b.st_dev&&a.st_ino==b.st_ino;}
class Hash {
    CC_SHA256_CTX context{};
public:
    Hash(){need(CC_SHA256_Init(&context)==1,"Cannot initialize archive digest");}
    void add(const char* p,std::size_t n){
        need(n<=chunk,"Archive digest chunk bound");
        need(CC_SHA256_Update(&context,p,static_cast<CC_LONG>(n))==1,"Cannot update archive digest");
    }
    std::string finish(){
        std::array<unsigned char,CC_SHA256_DIGEST_LENGTH> bytes{};
        need(CC_SHA256_Final(bytes.data(),&context)==1,"Cannot finish archive digest");
        const char* digits="0123456789abcdef";std::string s;
        for(auto b:bytes){s+=digits[b>>4];s+=digits[b&15];}return s;
    }
};
struct Sum {std::string sha;std::uint32_t crc=0;};
Sum scan(int fd,std::uint64_t size,const std::function<void()>& check,
         const std::function<void(const char*,std::size_t)>& consume={}){
    Hash hash;uLong crc=::crc32(0L,Z_NULL,0);std::vector<char> buffer(chunk);
    for(std::uint64_t at=0;at<size;){
        tick(check);auto wanted=static_cast<std::size_t>(std::min<std::uint64_t>(chunk,size-at));
        auto n=pread(fd,buffer.data(),wanted,static_cast<off_t>(at));
        if(n<0&&errno==EINTR)continue;
        need(n>0,"Archive input ended early or could not be read","ARCHIVE_CONTAINER_READ_FAILED");
        auto count=static_cast<std::size_t>(n);hash.add(buffer.data(),count);
        crc=::crc32(crc,reinterpret_cast<const Bytef*>(buffer.data()),static_cast<uInt>(count));
        if(consume)consume(buffer.data(),count);
        at+=count;
    }
    tick(check);return {hash.finish(),static_cast<std::uint32_t>(crc)};
}
}
StoredZip64Layout storedZip64Layout(const std::array<std::uint64_t,2>& sizes,
                                   const std::array<std::uint32_t,2>& crc){
    need(sizes[0]>0&&sizes[0]<=65536&&sizes[1]>0&&sizes[1]<=profileLimit,
         "Manifest/profile exceeds accepted archive capacity","ARCHIVE_CONTAINER_CAPACITY");
    StoredZip64Layout layout;std::array<std::uint64_t,2> offsets{};std::uint64_t pos=0;
    for(std::size_t i=0;i<2;++i){
        offsets[i]=pos;auto& h=layout.localHeaders[i];
        little(h,0x04034b50,4);little(h,45,2);little(h,0,2);little(h,0,2);
        little(h,0,2);little(h,33,2);little(h,crc[i],4);
        little(h,0xffffffff,4);little(h,0xffffffff,4);little(h,names[i].size(),2);little(h,20,2);h+=names[i];
        little(h,1,2);little(h,16,2);little(h,sizes[i],8);little(h,sizes[i],8);
        layout.dataOffsets[i]=plus(pos,h.size());pos=plus(layout.dataOffsets[i],sizes[i]);
    }
    layout.centralOffset=pos;
    for(std::size_t i=0;i<2;++i){
        auto& h=layout.centralHeaders[i];
        little(h,0x02014b50,4);little(h,(3U<<8)|45U,2);little(h,45,2);little(h,0,2);little(h,0,2);
        little(h,0,2);little(h,33,2);little(h,crc[i],4);little(h,0xffffffff,4);little(h,0xffffffff,4);
        little(h,names[i].size(),2);little(h,28,2);little(h,0,2);little(h,0,2);little(h,0,2);
        little(h,static_cast<std::uint64_t>(0100600)<<16,4);little(h,0xffffffff,4);h+=names[i];
        little(h,1,2);little(h,24,2);little(h,sizes[i],8);little(h,sizes[i],8);little(h,offsets[i],8);
        pos=plus(pos,h.size());
    }
    auto centralBytes=pos-layout.centralOffset;auto& t=layout.tail;
    little(t,0x06064b50,4);little(t,44,8);little(t,(3U<<8)|45U,2);little(t,45,2);
    little(t,0,4);little(t,0,4);little(t,2,8);little(t,2,8);little(t,centralBytes,8);little(t,layout.centralOffset,8);
    little(t,0x07064b50,4);little(t,0,4);little(t,pos,8);little(t,1,4);
    little(t,0x06054b50,4);little(t,0,2);little(t,0,2);little(t,0xffff,2);little(t,0xffff,2);
    little(t,0xffffffff,4);little(t,0xffffffff,4);little(t,0,2);
    layout.archiveBytes=plus(pos,t.size());return layout;
}
StoredZip64Result writeStoredZip64(int output,const std::array<StoredZip64Source,2>& sources,
                      const std::function<void()>& check,
                      const std::function<void(const std::string&)>& hook){
    tick(check);const auto originalOutput=identity(output);
    need(originalOutput.st_size==0,"Archive output must be exclusively created and empty","ARCHIVE_CONTAINER_OUTPUT_EXISTS");
    std::array<struct stat,2> originals{identity(sources[0].descriptor),identity(sources[1].descriptor)};
    need(!aliases(originalOutput,originals[0])&&!aliases(originalOutput,originals[1])&&!aliases(originals[0],originals[1]),"Archive descriptor alias refused");
    std::array<std::uint64_t,2> sizes{sources[0].bytes,sources[1].bytes};
    (void)storedZip64Layout(sizes,{0,0});
    std::array<Sum,2> sums;
    for(std::size_t i=0;i<2;++i){
        need(std::regex_match(sources[i].sha256,std::regex("[0-9a-f]{64}")),"Expected archive source SHA256 required");
        need(static_cast<std::uint64_t>(originals[i].st_size)==sizes[i],"Archive source size differs from receipt","ARCHIVE_CONTAINER_CHANGED");
        sums[i]=scan(sources[i].descriptor,sizes[i],check);
        need(sums[i].sha==sources[i].sha256&&same(originals[i],identity(sources[i].descriptor)),"Archive source differs from verified receipt","ARCHIVE_CONTAINER_CHANGED");
    }
    event(hook,"archive_sources_verified");tick(check);
    auto layout=storedZip64Layout(sizes,{sums[0].crc,sums[1].crc});Hash writtenHash;std::uint64_t position=0;
    auto write=[&](const char* data,std::size_t bytes){
        need(bytes<=chunk&&bytes<=layout.archiveBytes-position,"Archive write bound");
        for(std::size_t at=0;at<bytes;){
            tick(check);auto n=pwrite(output,data+at,bytes-at,static_cast<off_t>(position+at));
            if(n<0&&errno==EINTR)continue;
            need(n>0,"Archive write failed; candidate remains incomplete","ARCHIVE_CONTAINER_WRITE_FAILED");at+=static_cast<std::size_t>(n);
        }
        writtenHash.add(data,bytes);position+=bytes;
    };
    for(std::size_t i=0;i<2;++i){
        need(same(originals[i],identity(sources[i].descriptor)),"Archive source changed before copy","ARCHIVE_CONTAINER_CHANGED");
        const auto& h=layout.localHeaders[i];write(h.data(),h.size());
        auto actual=scan(sources[i].descriptor,sizes[i],check,[&](const char* b,std::size_t n){write(b,n);event(hook,"archive_data_chunk");});
        need(actual.sha==sums[i].sha&&actual.crc==sums[i].crc&&same(originals[i],identity(sources[i].descriptor)),"Archive source changed during copy","ARCHIVE_CONTAINER_CHANGED");
    }
    for(const auto& h:layout.centralHeaders)write(h.data(),h.size());
    write(layout.tail.data(),layout.tail.size());need(position==layout.archiveBytes,"Archive final length mismatch");
    auto expectedSha=writtenHash.finish();event(hook,"archive_before_sync");tick(check);
    need(fsync(output)==0,"Cannot sync archive candidate","ARCHIVE_CONTAINER_WRITE_FAILED");
    const auto written=identity(output);need(aliases(originalOutput,written)&&static_cast<std::uint64_t>(written.st_size)==position,"Archive output changed during write","ARCHIVE_CONTAINER_CHANGED");
    event(hook,"archive_written");tick(check);
    auto actual=scan(output,position,check);
    need(actual.sha==expectedSha&&same(written,identity(output)),"Archive candidate changed before readback completed","ARCHIVE_CONTAINER_CHANGED");
    for(std::size_t i=0;i<2;++i)need(same(originals[i],identity(sources[i].descriptor)),"Archive source changed before receipt","ARCHIVE_CONTAINER_CHANGED");
    event(hook,"archive_before_return");tick(check);
    Value receipt=Value::Object{{"bytes",Value::fromInteger(static_cast<std::int64_t>(position))},{"sha256",expectedSha},
        {"entries",Value::Array{Value::Object{{"name",names[0]},{"bytes",Value::fromInteger(static_cast<std::int64_t>(sizes[0]))},{"sha256",sums[0].sha},{"crc32",Value::fromInteger(sums[0].crc)}},
                                Value::Object{{"name",names[1]},{"bytes",Value::fromInteger(static_cast<std::int64_t>(sizes[1]))},{"sha256",sums[1].sha},{"crc32",Value::fromInteger(sums[1].crc)}}}},
        {"compression","STORED"},{"zip64",true},{"stream_chunk_bytes",Value::fromInteger(chunk)},
        {"self_generated_bytes_verified",true},{"external_import_validated",false}};
    return {std::move(receipt),written};
}
} // namespace fathom::storage
