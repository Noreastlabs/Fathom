#include "content/CurriculumShardCatalog.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
bool refused(const std::filesystem::path& root){
    try{(void)fathom::curriculum::discoverShards(root);return false;}
    catch(const std::exception&){return true;}
}
}

int main(int argc,char** argv){
    try{
        require(argc==2,"Pass the absolute installed curriculum-shards resource path");
        const std::filesystem::path installed{argv[1]};
        const auto found=fathom::curriculum::discoverShards(installed);
        require(found.shardCount==4&&found.sourceRecords==432,"Four nonadmitted shards were not discovered");
        const auto scratch=installed.parent_path()/"curriculum-shard-negative-check";
        require(!std::filesystem::exists(scratch),"Choose a fresh negative-check path");
        std::filesystem::create_directories(scratch/"bundle");
        require(refused(scratch),"Missing handoff was accepted");
        {
            std::ifstream in(installed/"handoff.json",std::ios::binary);
            std::ofstream out(scratch/"handoff.json",std::ios::binary);
            out<<in.rdbuf()<<"corrupt";
        }
        require(refused(scratch),"Changed handoff was accepted");
        std::filesystem::copy_file(installed/"handoff.json",scratch/"handoff.json",
                                   std::filesystem::copy_options::overwrite_existing);
        for(const auto& entry:std::filesystem::recursive_directory_iterator(installed/"bundle")){
            const auto destination=scratch/"bundle"/entry.path().lexically_relative(installed/"bundle");
            if(entry.is_directory())std::filesystem::create_directories(destination);
            else std::filesystem::create_hard_link(entry.path(),destination);
        }
        require(fathom::curriculum::discoverShards(scratch).sourceRecords==432,"Isolated installed copy was not discovered");
        const auto summary=scratch/"bundle/Build/parallel-02/four-real-shard-manifest-r01/summary.json";
        std::filesystem::remove(summary); // Unlink this hard link without changing the installed original.
        {std::ofstream out(summary,std::ios::binary);out<<"changed summary";}
        require(refused(scratch),"Changed shard asset was accepted");
        std::filesystem::remove_all(scratch);
        std::cout<<"Four sealed source shards discovered; missing handoff and changed handoff/asset refused; no runtime admission\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
