#include "content/LessonCatalog.hpp"
#include <filesystem>
#include <iostream>
using namespace fathom;
int main(int argc,char** argv){std::size_t checks=0;try{
    auto ck=[&](bool yes,const char* why){++checks;if(!yes)throw std::runtime_error(why);};
    if(argc!=2)throw std::runtime_error("Expected absolute Resources root");
    const std::filesystem::path resources=argv[1];ck(resources.is_absolute(),"absolute Resources root");
    std::vector<std::filesystem::path> extensions;
    for(const auto& name:lesson::Catalog::installedExtensionDirectoryNames())extensions.push_back(resources/name);
    const auto base=lesson::Catalog::load(resources/"representative-controls");
    const auto old=base->lesson("fg:item:000001");
    ck(old.variants.size()==4,"historical item001 has four original half routes");
    const auto installed=lesson::Catalog::loadInstalled(resources/"representative-controls",extensions);
    const auto& now=installed->lesson("fg:item:000001");
    ck(now.variants.size()==6&&now.record.object().at("content_revision")==json::Value::fromInteger(4),
        "one revision4 owner retains four historical plus two new choices");
    for(std::size_t k=0;k<4;++k)ck(now.variants[k].id==old.variants[k].id&&
        now.variants[k].authored==old.variants[k].authored,"old item001 variant identity and authored bytes unchanged");
    for(std::size_t k=4;k<6;++k){const auto admission=installed->admit(now.id,now.variants[k].id);
        ck(admission->identity().object().at("content_revision")==json::Value::fromInteger(4)&&
            admission->identity().object().at("item_id")==json::Value("fg:item:000001")&&
            !admission->identity().object().at("whole_task_completion").boolean(),
            "new item001 admission retains owner and no-credit identity");}
    ck(installed->lesson("fg:item:000002").id==base->lesson("fg:item:000002").id,
        "Guided default identity unchanged");
    std::cout<<"PASS "<<checks<<" historical item001 identities and new no-credit revision\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
