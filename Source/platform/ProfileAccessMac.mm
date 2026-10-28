#include "platform/ProfileAccessMac.hpp"
#include "storage/ProfileNaming.hpp"
#import <Foundation/Foundation.h>
#include <array>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <iomanip>
#include <fstream>
#include <mutex>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>

namespace fathom::storage {
namespace {
std::mutex leaseMutex;
std::set<std::string> processLeases;
[[noreturn]] void fail(const std::string& text){throw std::runtime_error(text);}
NSString* ns(const std::string& text){
    NSString* value=[[NSString alloc] initWithBytes:text.data() length:text.size() encoding:NSUTF8StringEncoding];
    if(value==nil)fail("Invalid UTF8 platform value");return value;
}
NSDate* date(const std::string& utc){
    static const std::regex format(R"(^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$)");
    if(!std::regex_match(utc,format))fail("Expected normalized RFC3339 UTC timestamp");
    NSISO8601DateFormatter* parser=[[NSISO8601DateFormatter alloc] init];
    parser.formatOptions=NSISO8601DateFormatWithInternetDateTime | (utc.find('.')==std::string::npos?0:NSISO8601DateFormatWithFractionalSeconds);
    NSDate* value=[parser dateFromString:ns(utc)];if(value==nil)fail("Invalid UTC calendar date");
    NSDateFormatter* roundtrip=[[NSDateFormatter alloc] init];roundtrip.locale=[[NSLocale alloc] initWithLocaleIdentifier:@"en_US_POSIX"];roundtrip.timeZone=[NSTimeZone timeZoneForSecondsFromGMT:0];roundtrip.dateFormat=@"yyyy-MM-dd'T'HH:mm:ss";
    if(std::string([[roundtrip stringFromDate:value] UTF8String])!=utc.substr(0,19))fail("UTC date normalized to a different calendar value");
    return value;
}
void inspectFile(const std::filesystem::path& path,bool required){
    struct stat st{};
    if(lstat(path.c_str(),&st)!=0){if(errno==ENOENT&&!required)return;fail("Cannot inspect profile file: "+path.string()+": "+strerror(errno));}
    if(!S_ISREG(st.st_mode)||st.st_uid!=getuid()||st.st_nlink!=1)fail("Profile files must be regular, user-owned and not hard-linked: "+path.string());
    if((st.st_mode&077)!=0)fail("Profile file permissions must be user-only: "+path.string());
}
void directoryPath(const std::filesystem::path& directory,bool create){
    std::filesystem::path path;
    for(const auto& component:directory){
        path/=component;if(path=="/")continue;
        struct stat st{};
        if(lstat(path.c_str(),&st)!=0){
            if(errno!=ENOENT||!create)fail("Profile directory is unavailable: "+path.string());
            if(mkdir(path.c_str(),0700)!=0)fail("Cannot create profile directory: "+std::string(strerror(errno)));
            if(lstat(path.c_str(),&st)!=0)fail("Cannot inspect created profile directory");
        }
        if(!S_ISDIR(st.st_mode))fail("Profile directory path contains a symlink or non-directory: "+path.string());
        if(path==directory&&(st.st_uid!=getuid()||(st.st_mode&077)!=0))fail("Profile directory must be user-owned with user-only permissions");
    }
}
} // namespace
std::filesystem::path defaultProfilePath(){@autoreleasepool{
    NSURL* url=[[[NSFileManager defaultManager] URLsForDirectory:NSApplicationSupportDirectory inDomains:NSUserDomainMask] firstObject];
    if(url==nil||![url isFileURL])fail("User Application Support directory unavailable");
    return std::filesystem::path([[url path] fileSystemRepresentation])/"Fathom"/"profile.sqlite";
}}
std::string systemIanaTimezone(){@autoreleasepool{
    NSTimeZone* zone=[NSTimeZone localTimeZone];
    if(zone==nil||zone.name==nil)fail("Native local timezone unavailable");
    const auto name=std::string([[zone name] UTF8String]);
    localDay("2026-09-01T00:00:00Z",name);
    return name;
}}
void validateUtc(const std::string& utc){@autoreleasepool{(void)date(utc);}}
bool utcBefore(const std::string& lhs,const std::string& rhs){
    validateUtc(lhs);validateUtc(rhs);
    if(lhs.substr(0,19)!=rhs.substr(0,19))return lhs.substr(0,19)<rhs.substr(0,19);
    const auto fraction=[](const std::string& value){auto result=value[19]=='.'?value.substr(20,value.size()-21):std::string{};result.resize(6,'0');return result;};
    return fraction(lhs)<fraction(rhs);
}
std::string localDay(const std::string& utc,const std::string& zone){@autoreleasepool{
    NSString* name=ns(zone);
    if(zone!="UTC"){
        if(zone.empty()||zone.find('\0')!=std::string::npos)fail("Invalid IANA timezone identifier");
        std::filesystem::path relative(zone);if(relative.is_absolute())fail("IANA timezone must be relative");
        for(const auto& component:relative)if(component.empty()||component=="."||component=="..")fail("Invalid IANA timezone component");
        if(zone.find("//")!=std::string::npos||zone.back()=='/')fail("Invalid IANA timezone separator");
        std::error_code ec;auto root=std::filesystem::canonical("/usr/share/zoneinfo",ec);if(ec)fail("Native timezone data unavailable");
        auto file=std::filesystem::canonical(root/relative,ec);if(ec)fail("Unknown native IANA timezone");
        auto inside=file.lexically_relative(root);if(inside.empty()||inside.is_absolute()||*inside.begin()==".."||!std::filesystem::is_regular_file(file))fail("Timezone outside native database");
        std::ifstream input(file,std::ios::binary);char magic[4]{};input.read(magic,4);if(input.gcount()!=4||std::string(magic,4)!="TZif")fail("Invalid native timezone data");
    }
    NSTimeZone* timezone=zone=="UTC"?[NSTimeZone timeZoneForSecondsFromGMT:0]:[NSTimeZone timeZoneWithName:name];if(timezone==nil)fail("Unknown timezone");
    NSDateFormatter* formatter=[[NSDateFormatter alloc] init];formatter.locale=[[NSLocale alloc] initWithLocaleIdentifier:@"en_US_POSIX"];formatter.timeZone=timezone;formatter.dateFormat=@"yyyy-MM-dd";
    return [[formatter stringFromDate:date(utc)] UTF8String];
}}
std::string newUuid(){
    std::array<unsigned char,16> bytes{};arc4random_buf(bytes.data(),bytes.size());bytes[6]=(bytes[6]&0x0f)|0x40;bytes[8]=(bytes[8]&0x3f)|0x80;
    std::ostringstream out;out<<std::hex<<std::setfill('0');for(std::size_t i=0;i<bytes.size();++i){if(i==4||i==6||i==8||i==10)out<<'-';out<<std::setw(2)<<static_cast<unsigned int>(bytes[i]);}return out.str();
}
struct ProfileLease::Impl {
    std::filesystem::path database;
    std::string key;
    int fd=-1;
    bool registered=false;
    ~Impl(){
        if(fd>=0){flock(fd,LOCK_UN);close(fd);}
        if(registered){std::lock_guard<std::mutex> guard(leaseMutex);processLeases.erase(key);}
    }
};
ProfileLease::ProfileLease(std::filesystem::path database,bool createDirectories){
    auto state=std::make_unique<Impl>();
    if(!database.is_absolute()||!profile_names::databaseName(database.filename().string()))fail("Explicit absolute profile.sqlite path required");
    for(const auto& component:database)if(component=="."||component=="..")fail("Profile path cannot contain dot traversal");
    directoryPath(database.parent_path(),createDirectories);state->database=database;state->key=database.string();
    {std::lock_guard<std::mutex> guard(leaseMutex);if(!processLeases.insert(state->key).second)fail("Profile is already leased by this process");state->registered=true;}
    const auto lock=database.parent_path()/".profile.lock";
    inspectFile(lock,false);
    state->fd=open(lock.c_str(),O_RDWR|O_CREAT|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK,0600);
    if(state->fd<0)fail("Cannot open profile lease: "+std::string(strerror(errno)));
    struct stat st{};if(fstat(state->fd,&st)!=0||!S_ISREG(st.st_mode)||st.st_uid!=getuid()||st.st_nlink!=1||(st.st_mode&077)!=0)fail("Unsafe profile lease file");
    if(flock(state->fd,LOCK_EX|LOCK_NB)!=0)fail("Profile is already open in another process; close that instance first");
    impl_=std::move(state);validateFiles(false);
}
ProfileLease::~ProfileLease()=default;
ProfileLease::ProfileLease(ProfileLease&&) noexcept=default;
ProfileLease& ProfileLease::operator=(ProfileLease&&) noexcept=default;
const std::filesystem::path& ProfileLease::path() const{return impl_->database;}
void ProfileLease::validateLeaseIdentity() const{
    struct stat held{},named{};const auto path=impl_->database.parent_path()/".profile.lock";
    if(fstat(impl_->fd,&held)!=0||lstat(path.c_str(),&named)!=0||!S_ISREG(held.st_mode)||!S_ISREG(named.st_mode)||
       held.st_dev!=named.st_dev||held.st_ino!=named.st_ino||held.st_uid!=getuid()||held.st_nlink!=1||
       (held.st_mode&077)!=0||held.st_mode!=named.st_mode||held.st_uid!=named.st_uid||held.st_nlink!=named.st_nlink)
        fail("Held profile lease no longer matches its named private file");
}
void ProfileLease::validateFiles(bool required) const{
    inspectFile(impl_->database,required);
    for(const char* suffix:{"-wal","-shm","-journal"})inspectFile(impl_->database.string()+suffix,false);
}
} // namespace fathom::storage
