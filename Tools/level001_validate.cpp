#include "content/Level001Extension.hpp"
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <unistd.h>

int main(int argc,char** argv) {
    const std::set<std::string> required{"--package","--registry","--profile","--profile-sha256","--source-root","--report"};
    std::map<std::string,std::string> options;
    for(int i=1;i<argc;i+=2) {
        if(i+1>=argc||(!required.count(argv[i])&&std::string(argv[i])!="--stroke-fault")||
            !options.emplace(argv[i],argv[i+1]).second) {
            std::cerr<<"Expected six unique named options and optional --stroke-fault variant:index:emitted\n";
            return 64;
        }
    }
    for(const auto& key:required)if(!options.count(key)){std::cerr<<"Missing "<<key<<'\n';return 64;}
    std::optional<fathom::lesson::Level001StrokeFault> fault;
    if(const auto found=options.find("--stroke-fault");found!=options.end()) {
        const auto& raw=found->second;const auto last=raw.rfind(':');
        const auto middle=last==std::string::npos?std::string::npos:raw.rfind(':',last-1);
        if(middle==std::string::npos||last==std::string::npos||middle==0||last+1>=raw.size()||
            (raw.substr(last+1)!="D"&&raw.substr(last+1)!="U")) {
            std::cerr<<"Invalid stroke fault syntax\n";return 64;
        }
        const auto index=raw.substr(middle+1,last-middle-1);
        if(index.empty()||index.find_first_not_of("0123456789")!=std::string::npos||index.size()>2||std::stoul(index)>=48) {
            std::cerr<<"Invalid stroke fault contact index\n";return 64;
        }
        fault=fathom::lesson::Level001StrokeFault{raw.substr(0,middle),std::stoul(index),raw.substr(last+1)};
    }
    try {
        fathom::content::Limits limits;limits.json.values=1100000;
        fathom::content::Input input{fathom::content::readBounded(options.at("--package"),limits.json.bytes),
            fathom::content::readBounded(options.at("--registry"),limits.json.bytes),
            fathom::content::readBounded(options.at("--profile"),limits.json.bytes),
            options.at("--profile-sha256"),options.at("--source-root")};
        auto result=fathom::lesson::validateLevel001Extension(input,fault,limits);
        const auto output=fathom::json::stringify(result.report)+"\n";
        const int fd=::open(options.at("--report").c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);
        if(fd<0){std::cerr<<"Cannot create new report: "<<std::strerror(errno)<<'\n';return 74;}
        std::size_t written=0;
        while(written<output.size()) {
            const auto n=::write(fd,output.data()+written,output.size()-written);
            if(n<0&&errno==EINTR)continue;
            if(n<=0){::close(fd);std::cerr<<"Report write failed; partial evidence retained\n";return 74;}
            written+=static_cast<std::size_t>(n);
        }
        if(::close(fd)!=0){std::cerr<<"Report close failed\n";return 74;}
        std::cout<<(result.validReference?"VALID LEVEL1 REFERENCE; runtime admission withheld":"INVALID LEVEL1 REFERENCE")
            <<"; "<<result.records.size()<<" mapped records; report "<<options.at("--report")<<'\n';
        return result.exitCode;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 74;}
}
