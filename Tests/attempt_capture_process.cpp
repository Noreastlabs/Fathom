#include "storage/ProfileStore.hpp"
#include "platform/ProfileAccessMac.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
int main(int argc,char** argv){try{
    if(argc!=3)throw std::runtime_error("Explicit existing synthetic profile and new output required");
    const auto path=std::filesystem::absolute(argv[1]).lexically_normal();
    const auto out=std::filesystem::absolute(argv[2]).lexically_normal();
    const std::string root="/Results/20260908T031111Z-3.4.1.1.1-r01-evidence/test-data/";
    if(path.string().find(root)==std::string::npos||out.string().find(root)==std::string::npos||std::filesystem::exists(out))throw std::runtime_error("Paths must be explicit isolated evidence; no overwrite");
    fathom::storage::StoreOptions o;o.path=path;
    fathom::storage::ProfileStore store(o);auto r=store.snapshot(fathom::storage::newUuid()).get();
    if(r.status!=fathom::storage::Status::Confirmed)throw std::runtime_error(r.code+": "+r.message);
    std::ofstream f(out,std::ios::binary);f<<fathom::storage::canonical(r.data);f.flush();if(!f)throw std::runtime_error("Snapshot write failed");
    std::cout<<"Normal separate-process snapshot; no playback or extra outcome\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
