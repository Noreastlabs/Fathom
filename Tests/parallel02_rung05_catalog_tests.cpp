#include "content/LessonCatalog.hpp"
#include "content/Rung05Extension.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
using namespace fathom;
int main(int argc,char** argv){
    int checks=0;
    try{
        if(argc!=8)throw std::runtime_error("Expected base, four prior extensions, Rung05 and fresh output");
        const std::filesystem::path base=argv[1],r02=argv[2],r03=argv[3],r04=argv[4],l06=argv[5],r05=argv[6],out=argv[7];
        if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
        std::filesystem::create_directories(out);
        std::ofstream trace(out/"checks.tsv");
        auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<'\n';if(!ok)throw std::runtime_error(name);};
        auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
        const auto old=lesson::Catalog::load(base,r02,r03,r04,l06);
        const auto current=lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05});
        ck(old->lessons().size()==17&&current->lessons().size()==18&&old->sourceEntryCount()==72&&current->sourceEntryCount()==79,
            "one new selected case and seven retained source entries");
        ck(lesson::Catalog::installedExtensionDirectoryNames()==std::vector<std::string>{"rung02-extension","rung03-extension","rung04-extension","level006-extension","rung05-extension","level008-extension","level010-extension","level007-extension","level009-extension","level011-extension","level013-extension","level014-extension","level015-extension","level016-extension"},
            "finite compiled installed-extension order");
        std::size_t variants{};
        for(const auto& prior:old->lessons()){
            ck(prior.record==current->lesson(prior.id).record&&old->contentVersion(prior.id)==current->contentVersion(prior.id),
                "prior record and content version preserved "+prior.id);
            for(const auto& variant:prior.variants){
                ++variants;
                ck(variant.authored==current->variant(prior.id,variant.id).authored,"prior authored variant preserved "+variant.id);
                try{
                    const auto a=old->admit(prior.id,variant.id),b=current->admit(prior.id,variant.id);
                    ck(a->identity()==b->identity()&&a->sourceBinding()==b->sourceBinding(),
                        "prior runtime identity preserved "+variant.id);
                }catch(const std::exception&){
                    refuses([&]{current->admit(prior.id,variant.id);},"prior refusal retained "+variant.id);
                }
            }
        }
        ck(variants==57&&current->isInstalledExtension("fg:item:001145")&&
            !current->isInstalledExtension("fg:item:000003"),"all prior variants and exact extension ownership");
        const std::array<int,16> midi{49,51,53,54,56,58,60,61,61,60,58,56,54,53,51,49};
        for(const auto* id:{"fg:variant:007412","fg:variant:007413"}){
            const auto admission=current->admit("fg:item:001145",id);
            const auto& identity=admission->identity().object();
            ck(admission->practiceAllowed()&&admission->span()==Rational{8}&&
                !identity.at("whole_task_completion").boolean()&&
                identity.at("package_sha256")==json::Value("7163016180690f4c6432caf5586a59c2fe07815681da554c6f8d7f1c4ed64ced"),
                "Rung05 typed one-cell permission and no full-task credit");
            const auto& events=admission->model()->source().events;
            ck(events.size()==16,"Rung05 sixteen source events");
            for(std::size_t i=0;i<events.size();++i)
                ck(events[i].span.onset==Rational{static_cast<std::int64_t>(i),2}&&
                    events[i].span.duration==Rational{1,2}&&events[i].tones.size()==1&&
                    events[i].tones.front().midi==midi[i],"Rung05 exact pitch/eighth "+std::to_string(i));
            std::ofstream(out/(std::string(id)+"-admission.json"))<<json::stringify(admission->identity());
        }
        refuses([&]{current->admit("fg:item:001145","fg:variant:007411");},"foreign Level6 variant refused");
        refuses([&]{current->admit("fg:item:000001","fg:variant:000001");},"unadmitted original refused");
        refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,out/"missing"});},"missing Rung05 refused");
        refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,r05});},"unknown sixth extension refused");
        const auto mutableBundle=out/"mutable-rung05";
        std::filesystem::copy(r05,mutableBundle,std::filesystem::copy_options::recursive);
        auto put=[](const std::filesystem::path& path,const std::string& bytes){std::ofstream output(path,std::ios::binary);output<<bytes;};
        const auto manifest=json::parse(content::readBounded(r05/"manifest.json",1024*1024));
        for(const auto* key:{"package","registry","profile","decision"}){
            const auto path=manifest.object().at("entries").object().at(key).string();
            const auto original=content::readBounded(mutableBundle/path,32*1024*1024);
            put(mutableBundle/path,"{}");
            refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,mutableBundle});},
                std::string("changed ")+key+" asset refused");
            put(mutableBundle/path,original);
        }
        put(mutableBundle/"unreviewed-extra.txt","x");
        refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,mutableBundle});},
            "unlisted installed file refused");
        std::filesystem::remove(mutableBundle/"unreviewed-extra.txt");
        ck(lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,mutableBundle})->lessons().size()==18,
            "restored exact bundle loads through generic descriptor");
        std::cout<<"PASS "<<checks<<" Rung05 generic catalog checks\n";
        return 0;
    }catch(const std::exception& error){
        std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<'\n';
        return 1;
    }
}
