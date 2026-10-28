#include "content/Canonical.hpp"
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <map>
#include <set>
#include <unistd.h>

int main(int argc,char** argv) {
    const std::set<std::string> allowed{"--package","--registry","--profile","--profile-sha256","--source-root","--report"};
    std::map<std::string,std::string> options;
    for(int i=1;i<argc;i+=2) {
        if(i+1>=argc||!allowed.count(argv[i])||!options.emplace(argv[i],argv[i+1]).second) { std::cerr<<"Expected each of --package --registry --profile --profile-sha256 --source-root --report once, with a value\n"; return 64; }
    }
    if(options.size()!=allowed.size()) { std::cerr<<"All six named options are required\n";return 64; }
    try {
        const auto limits=[] {
            fathom::content::Limits value;
            // Offline CLI budget for monolithic reference documents. Keep the
            // shared parser/API defaults and all other finite limits unchanged.
            value.json.values=1100000;
            return value;
        }();
        fathom::content::Input input{fathom::content::readBounded(options.at("--package"),limits.json.bytes),fathom::content::readBounded(options.at("--registry"),limits.json.bytes),fathom::content::readBounded(options.at("--profile"),limits.json.bytes),options.at("--profile-sha256"),options.at("--source-root")};
        auto result=fathom::content::validate(input,limits);
        const std::string output=fathom::json::stringify(result.report)+"\n";
        const int fd=::open(options.at("--report").c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);
        if(fd<0) {std::cerr<<"Cannot create new report: "<<std::strerror(errno)<<'\n';return 74;}
        std::size_t written=0;
        while(written<output.size()) {
            const auto n=::write(fd,output.data()+written,output.size()-written);
            if(n<0&&errno==EINTR)continue;
            if(n<=0) {::close(fd);std::cerr<<"Report write failed; partial evidence retained\n";return 74;}
            written+=static_cast<std::size_t>(n);
        }
        if(::close(fd)!=0) {std::cerr<<"Report close failed\n";return 74;}
        std::cout<<(result.validReference?"VALID REFERENCE; runtime admission withheld":"INVALID")<<"; "<<result.records.size()<<" mapped records; report "<<options.at("--report")<<'\n';
        return result.exitCode;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 74;}
}
