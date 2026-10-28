#include "storage/ProfileCompatibility.hpp"
#include "content/Canonical.hpp"
#include <fcntl.h>
#include <unistd.h>
#include <iostream>
#include <filesystem>

int main(int argc,char** argv){try{
    if(argc!=6)throw std::runtime_error("Usage: phase original/profile.sqlite new-stage phase-file binary-sha256");
    std::string phase=argv[1];if(phase!="raw-image-verified"&&phase!="candidate-validated")throw std::runtime_error("Unsupported interruption phase");
    fathom::storage::CompatibilityOptions o;o.original=argv[2];o.stage=argv[3];o.operation="synthetic-owned-interruption";o.applicationVersion="0.1.0-native-compatibility-evidence";o.applicationBuildSha256=argv[5];o.stopped=true;o.unresolvedWrites=false;
    o.diagnosticHook=[&](const std::string& reached){if(reached!=phase)return;using V=fathom::json::Value;auto bytes=fathom::json::stringify(V::Object{{"phase",reached},{"pid",V::fromInteger(getpid())},{"original",o.original.string()},{"stage",o.stage.string()},{"classification","owned synthetic profile interruption; no original SQL writer"}});auto partial=std::string(argv[4])+".partial";int fd=::open(partial.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);if(fd<0)throw std::runtime_error("Cannot exclusively create phase record");auto n=::write(fd,bytes.data(),bytes.size());int synced=fsync(fd);int closed=::close(fd);if(n!=static_cast<ssize_t>(bytes.size())||synced!=0||closed!=0)throw std::runtime_error("Phase record incomplete");if(::renamex_np(partial.c_str(),argv[4],RENAME_EXCL)!=0)throw std::runtime_error("Phase publication failed");for(;;)::pause();};
    auto r=fathom::storage::inspectCompatibility(o);std::cout<<r.code<<": "<<r.message<<'\n';return r.status==fathom::storage::Status::Confirmed?0:1;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
