#include "content/LessonCatalog.hpp"
#include "content/Level010Extension.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
using namespace fathom;
int main(int argc,char** argv){
    int checks=0;
    try{
        if(argc!=10)throw std::runtime_error("Expected base, six prior extensions, Level10 and fresh output");
        const std::filesystem::path base=argv[1],r02=argv[2],r03=argv[3],r04=argv[4],l06=argv[5],r05=argv[6],l08=argv[7],l10=argv[8],out=argv[9];
        if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
        std::filesystem::create_directories(out);
        std::ofstream trace(out/"checks.tsv");
        auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<'\n';if(!ok)throw std::runtime_error(name);};
        auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
        const auto old=lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,l08});
        const auto current=lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,l08,l10});
        ck(old->lessons().size()==19&&current->lessons().size()==20&&old->sourceEntryCount()==83&&current->sourceEntryCount()==87,
            "one new selected case and four retained source entries");
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
        ck(variants==61&&current->isInstalledExtension("fg:item:001147")&&
            !current->isInstalledExtension("fg:item:000003"),"all prior variants and exact extension ownership");
        const std::array<int,4> midi{45,46,45,48},frets{5,6,5,8};
        for(const auto* id:{"fg:variant:007416","fg:variant:007417"}){
            const auto admission=current->admit("fg:item:001147",id);
            const auto& identity=admission->identity().object();
            ck(admission->practiceAllowed()&&admission->span()==Rational{1}&&
                !identity.at("whole_task_completion").boolean()&&
                identity.at("package_sha256")==json::Value("b37a9a1194ba183522d45075388010f08bbb923c8975bb67401e26917eaa2b83"),
                "Level10 typed one-cell permission and no full-task credit");
            ck(identity.at("bundle_sha256")==json::Value("acd3277998a19da2db8ed2cdbde84c39f29ad725fae56fbcda5c8673a9c6b35e")&&
                identity.at("source_manifest_sha256")==json::Value("e856ef05e610b9be51f33aac661a900301f747a9259bfcbd951b756a247504fe")&&
                identity.at("source_refs")==json::parse(R"(["L10-TXT1-39-53","L10-PDF1-p2","L10-TXT1-1-33","L10-PDF1-p1"])"),
                "Level10 exact installed bundle, original source manifest and ordered refs");
            const auto& events=admission->model()->source().events;
            ck(events.size()==4,"Level10 four source events");
            for(std::size_t i=0;i<events.size();++i)
                ck(events[i].span.onset==Rational{static_cast<std::int64_t>(i),4}&&
                    events[i].span.duration==Rational{1,4}&&events[i].tones.size()==1&&
                    events[i].tones.front().midi==midi[i]&&events[i].tones.front().string==1&&
                    events[i].tones.front().fret==frets[i]&&
                    events[i].handDirection==((i%2==0)==(std::string(id)=="fg:variant:007416")?"D":"U"),
                    "Level10 exact pitch/fret/sixteenth/stroke "+std::to_string(i));
            std::ofstream(out/(std::string(id)+"-admission.json"))<<json::stringify(admission->identity());
        }
        refuses([&]{current->admit("fg:item:001147","fg:variant:007415");},"foreign Level8 variant refused");
        refuses([&]{current->admit("fg:item:000001","fg:variant:000001");},"unadmitted original refused");
        refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,l08,out/"missing"});},"missing Level10 refused");
        refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,l08,l10,l10});},"unknown eighth extension refused");
        const auto mutableBundle=out/"mutable-level010";
        std::filesystem::copy(l10,mutableBundle,std::filesystem::copy_options::recursive);
        auto put=[](const std::filesystem::path& path,const std::string& bytes){std::ofstream output(path,std::ios::binary);output<<bytes;};
        const auto manifest=json::parse(content::readBounded(l10/"manifest.json",1024*1024));
        for(const auto* key:{"package","registry","profile","provenance","decision"}){
            const auto path=manifest.object().at("entries").object().at(key).string();
            const auto original=content::readBounded(mutableBundle/path,32*1024*1024);
            put(mutableBundle/path,"{}");
            refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,l08,mutableBundle});},
                std::string("changed ")+key+" asset refused");
            put(mutableBundle/path,original);
        }
        for(const auto* asset:{"Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.txt",
                               "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_10_Odd_Count_Position_Transfer.pdf"}){
            const auto original=content::readBounded(mutableBundle/asset,32*1024*1024);
            put(mutableBundle/asset,"changed original source");
            refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,l08,mutableBundle});},
                std::string("changed original ")+asset+" refused");
            put(mutableBundle/asset,original);
            std::filesystem::remove(mutableBundle/asset);
            refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,l08,mutableBundle});},
                std::string("missing original ")+asset+" refused");
            put(mutableBundle/asset,original);
        }
        put(mutableBundle/"unreviewed-extra.txt","x");
        refuses([&]{lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,l08,mutableBundle});},
            "unlisted installed file refused");
        std::filesystem::remove(mutableBundle/"unreviewed-extra.txt");
        ck(lesson::Catalog::loadInstalled(base,{r02,r03,r04,l06,r05,l08,mutableBundle})->lessons().size()==20,
            "restored exact bundle loads through generic descriptor");
        std::cout<<"PASS "<<checks<<" Level10 generic catalog checks\n";
        return 0;
    }catch(const std::exception& error){
        std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<'\n';
        return 1;
    }
}
