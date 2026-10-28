#include "storage/ProfileStore.hpp"
#include "platform/ProfileAccessMac.hpp"
#include <iostream>
int main(int argc,char** argv){
    if(argc!=4)return 64;
    try{
        const auto root=std::filesystem::canonical(argv[1]);
        const auto database=std::filesystem::absolute(argv[3]).lexically_normal();
        const auto relative=database.lexically_relative(root/"test-data");
        if(relative.empty()||relative.is_absolute()||*relative.begin()=="..")throw std::runtime_error("Test profile must be below explicit evidence/test-data");
        const std::string mode=argv[2];
        if(mode=="lease"){
            fathom::storage::ProfileLease lease(database,false);
            std::cout<<"LEASE_ACQUIRED\n";return 0;
        }
        if(mode!="snapshot")return 64;
        fathom::storage::StoreOptions options;options.path=database;
        fathom::storage::ProfileStore store(options);
        auto reply=store.snapshot("separate-process-reopen").get();
        std::cout<<fathom::storage::canonical(fathom::storage::Value::Object{
            {"status",fathom::storage::statusName(reply.status)},
            {"operation",reply.operation},{"owner",reply.owner},{"data",reply.data}})<<'\n';
        return reply.status==fathom::storage::Status::Confirmed?0:3;
    }catch(const std::exception& e){std::cout<<"REFUSED: "<<e.what()<<'\n';return 2;}
}
