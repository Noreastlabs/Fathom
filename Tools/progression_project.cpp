#include "progression/ProgressionRepository.hpp"
#include <fstream>
#include <iostream>
#include <thread>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cerrno>

namespace {
std::string queryFile(const char* path){
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_NONBLOCK);
    if(fd<0)throw std::runtime_error("Query must be an accessible regular file");
    struct Guard{int fd;~Guard(){close(fd);}} guard{fd};
    struct stat st{};constexpr std::size_t limit=1024*1024;
    if(fstat(fd,&st)!=0||!S_ISREG(st.st_mode)||st.st_size<0||static_cast<std::uint64_t>(st.st_size)>limit)
        throw std::runtime_error("Query must be a regular file of at most 1MiB");
    std::string out;char buffer[4096];
    for(;;){auto n=read(fd,buffer,sizeof(buffer));if(n<0){if(errno==EINTR)continue;throw std::runtime_error("Query read failed");}if(n==0)break;if(static_cast<std::size_t>(n)>limit-out.size())throw std::runtime_error("Query exceeded 1MiB while reading");out.append(buffer,static_cast<std::size_t>(n));}
    return out;
}
}

int main(int argc,char** argv){
    try{
        if(argc!=4)throw std::runtime_error("Usage: fathom_progression_project <explicit profile path> <query JSON file> <as-of UTC>; writes disposable projection cache only");
        auto value=fathom::json::parse(queryFile(argv[2]));std::vector<fathom::progression::Query> queries;
        for(auto& q:value.array()){auto item=q.find("item"),condition=q.find("condition"),scope=q.find("source_scope");if(!item||!condition||!scope||!item->isString())throw std::runtime_error("Query requires item/condition/source_scope");queries.push_back({item->string(),*condition,*scope});}
        for(auto& q:queries)fathom::progression::validateQuery(q);
        fathom::progression::utcMicros(argv[3]);
        fathom::storage::StoreOptions options;options.path=argv[1];fathom::storage::ProfileStore store(options);fathom::progression::ProgressionRepository repository(store,queries,argv[3],"explicit-cli-projection");
        while(!repository.finished()){repository.poll();std::this_thread::sleep_for(std::chrono::milliseconds(1));}
        auto& reply=repository.reply();std::cout<<fathom::json::stringify(fathom::json::Value::Object{{"status",fathom::storage::statusName(reply.status)},{"code",reply.code},{"message",reply.message},{"data",reply.data}})<<'\n';return reply.status==fathom::storage::Status::Confirmed?0:1;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
