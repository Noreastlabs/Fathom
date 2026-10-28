#include "content/LessonCatalog.hpp"
#include "content/Level008Extension.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
using namespace fathom;
int main(int argc,char** argv){
    int checks=0;
    try{
        if(argc!=9)throw std::runtime_error("Expected base, five prior extensions, Level8 and fresh output");
        const std::filesystem::path base=argv[1],r02=argv[2],r03=argv[3],r04=argv[4],l06=argv[5],r05=argv[6],l08=argv[7],out=argv[8];
        if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
        std::filesystem::create_directories(out);
        std::ofstream trace(out/"checks.tsv");
        auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<'\n';if(!ok)throw std::runtime_error(name);};
        auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
        const auto old=lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05});
        const auto current=lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,l08});
        ck(old->lessons().size()==18&&current->lessons().size()==19&&old->sourceEntryCount()==79&&current->sourceEntryCount()==83,
            "one new selected case and four retained source entries");
        ck(lesson::Catalog::installedExtensionDirectoryNames()==std::vector<std::string>{"rung02-extension","rung03-extension","rung04-extension","level006-extension","rung05-extension","level008-extension"},
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
        ck(variants==59&&current->isInstalledExtension("fg:item:001146")&&
            !current->isInstalledExtension("fg:item:000003"),"all prior variants and exact extension ownership");
        const std::array<int,8> midi{45,46,45,46,47,48,47,48},frets{5,6,5,6,7,8,7,8};
        for(const auto* id:{"fg:variant:007414","fg:variant:007415"}){
            const auto admission=current->admit("fg:item:001146",id);
            const auto& identity=admission->identity().object();
            ck(admission->practiceAllowed()&&admission->span()==Rational{2}&&
                !identity.at("whole_task_completion").boolean()&&
                identity.at("package_sha256")==json::Value("0d1fc7cdf70aa0fd75a40b3d952f935adc46cb6d9ad6e6abd168499a9a91c420"),
                "Level8 typed one-cell permission and no full-task credit");
            ck(identity.at("bundle_sha256")==json::Value("d4c44f1b6745a710b702b5a1fd21e97bb11365699ae5a0795ba5dba5a64ea225")&&
                identity.at("source_manifest_sha256")==json::Value("e856ef05e610b9be51f33aac661a900301f747a9259bfcbd951b756a247504fe")&&
                identity.at("source_refs")==json::parse(R"(["L8-TXT1-31-38","L8-PDF1-p2","L8-TXT1-1-25","L8-PDF1-p1"])"),
                "Level8 exact installed bundle, original source manifest and ordered refs");
            const auto& events=admission->model()->source().events;
            ck(events.size()==8,"Level8 eight source events");
            for(std::size_t i=0;i<events.size();++i)
                ck(events[i].span.onset==Rational{static_cast<std::int64_t>(i),4}&&
                    events[i].span.duration==Rational{1,4}&&events[i].tones.size()==1&&
                    events[i].tones.front().midi==midi[i]&&events[i].tones.front().string==1&&
                    events[i].tones.front().fret==frets[i]&&
                    events[i].handDirection==((i%2==0)==(std::string(id)=="fg:variant:007414")?"D":"U"),
                    "Level8 exact pitch/fret/sixteenth/stroke "+std::to_string(i));
            std::ofstream(out/(std::string(id)+"-admission.json"))<<json::stringify(admission->identity());
        }
        refuses([&]{current->admit("fg:item:001146","fg:variant:007413");},"foreign Rung05 variant refused");
        refuses([&]{current->admit("fg:item:000001","fg:variant:000001");},"unadmitted original refused");
        refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,out/"missing"});},"missing Level8 refused");
        refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,l08,l08});},"unknown seventh extension refused");
        const auto mutableBundle=out/"mutable-level008";
        std::filesystem::copy(l08,mutableBundle,std::filesystem::copy_options::recursive);
        auto put=[](const std::filesystem::path& path,const std::string& bytes){std::ofstream output(path,std::ios::binary);output<<bytes;};
        const auto manifest=json::parse(content::readBounded(l08/"manifest.json",1024*1024));
        for(const auto* key:{"package","registry","profile","provenance","decision"}){
            const auto path=manifest.object().at("entries").object().at(key).string();
            const auto original=content::readBounded(mutableBundle/path,32*1024*1024);
            put(mutableBundle/path,"{}");
            refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,mutableBundle});},
                std::string("changed ")+key+" asset refused");
            put(mutableBundle/path,original);
        }
        put(mutableBundle/"unreviewed-extra.txt","x");
        refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,mutableBundle});},
            "unlisted installed file refused");
        std::filesystem::remove(mutableBundle/"unreviewed-extra.txt");
        ck(lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,mutableBundle})->lessons().size()==19,
            "restored exact bundle loads through generic descriptor");
        std::cout<<"PASS "<<checks<<" Level8 generic catalog checks\n";
        return 0;
    }catch(const std::exception& error){
        std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<'\n';
        return 1;
    }
}
