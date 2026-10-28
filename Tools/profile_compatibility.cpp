#include "storage/ProfileCompatibility.hpp"
#include "content/Canonical.hpp"
#include <mach-o/dyld.h>
#include <iostream>

int main(int argc,char** argv){
    try{
        if(argc!=5||std::string(argv[1])!="--stopped-and-reconciled")throw std::runtime_error("Usage: --stopped-and-reconciled /absolute/original/profile.sqlite /absolute/new-private-stage operation-id");
        std::uint32_t size=0;_NSGetExecutablePath(nullptr,&size);std::vector<char> name(size);if(_NSGetExecutablePath(name.data(),&size)!=0)throw std::runtime_error("Cannot identify executable");
        auto executable=std::filesystem::canonical(name.data());fathom::storage::CompatibilityOptions o;o.original=argv[2];o.stage=argv[3];o.operation=argv[4];o.applicationVersion=FATHOM_COMPATIBILITY_VERSION;o.applicationBuildSha256=fathom::content::sha256(fathom::content::readBounded(executable,64*1024*1024));o.stopped=true;o.unresolvedWrites=false;
        auto r=fathom::storage::inspectCompatibility(o);using V=fathom::json::Value;std::cout<<fathom::json::stringify(V::Object{{"status",fathom::storage::statusName(r.status)},{"operation",r.operation},{"code",r.code},{"message",r.message},{"data",r.data}})<<'\n';return r.status==fathom::storage::Status::Confirmed?0:1;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
