#include "content/LessonCatalog.hpp"
#include "content/Level009Extension.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace fathom;
int main(int argc,char** argv){
    int checks=0;
    try{
        if(argc!=12)throw std::runtime_error("Expected base, eight prior extensions, Level9 and fresh output");
        const std::filesystem::path base=argv[1],r02=argv[2],r03=argv[3],r04=argv[4],l06=argv[5],
            r05=argv[6],l08=argv[7],l10=argv[8],l07=argv[9],l09=argv[10],out=argv[11];
        if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
        std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
        auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<'\n';if(!ok)throw std::runtime_error(name);};
        auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
        const std::vector<std::filesystem::path> prior{r02,r03,r04,l06,r05,l08,l10,l07};
        auto withNew=prior;withNew.push_back(l09);
        const auto old=lesson::Catalog::loadInstalled(base,prior);
        const auto current=lesson::Catalog::loadInstalled(base,withNew);
        ck(old->lessons().size()==21&&current->lessons().size()==23&&
            old->sourceEntryCount()==91&&current->sourceEntryCount()==95,
            "two cases added and one shared four-passage source bundle counted once");
        ck(lesson::Catalog::installedExtensionDirectoryNames()==std::vector<std::string>{
            "rung02-extension","rung03-extension","rung04-extension","level006-extension",
            "rung05-extension","level008-extension","level010-extension","level007-extension","level009-extension","level011-extension","level013-extension","level014-extension","level015-extension","level016-extension"},
            "finite compiled installed-extension order");
        std::size_t variants{};
        for(const auto& priorCase:old->lessons()){
            ck(priorCase.record==current->lesson(priorCase.id).record&&
                old->contentVersion(priorCase.id)==current->contentVersion(priorCase.id),
                "prior record/version preserved "+priorCase.id);
            for(const auto& variant:priorCase.variants){
                ++variants;
                ck(variant.authored==current->variant(priorCase.id,variant.id).authored,
                    "prior authored variant preserved "+variant.id);
                try{const auto a=old->admit(priorCase.id,variant.id),b=current->admit(priorCase.id,variant.id);
                    ck(a->identity()==b->identity()&&a->sourceBinding()==b->sourceBinding(),
                        "prior runtime admission preserved "+variant.id);
                }catch(const std::exception&){
                    refuses([&]{current->admit(priorCase.id,variant.id);},"prior refusal retained "+variant.id);
                }
            }
        }
        ck(variants==65&&current->isInstalledExtension("fg:item:001149")&&
            current->isInstalledExtension("fg:item:001150"),"all prior variants plus two exact extension owners");
        const std::array<const char*,2> items{"fg:item:001149","fg:item:001150"};
        const std::array<std::array<const char*,2>,2> variantIds{{{{"fg:variant:007420","fg:variant:007421"}},
            {{"fg:variant:007422","fg:variant:007423"}}}};
        const std::array<std::array<int,4>,2> frets{{{{5,6,7,8}},{{7,8,5,6}}}};
        const std::array<std::array<int,4>,2> midi{{{{45,46,47,48}},{{71,72,69,70}}}};
        for(std::size_t caseIndex=0;caseIndex<2;++caseIndex){
            for(std::size_t pick=0;pick<2;++pick){
                const auto admission=current->admit(items[caseIndex],variantIds[caseIndex][pick]);
                const auto& identity=admission->identity().object();
                ck(admission->practiceAllowed()&&admission->span()==Rational{1}&&
                    !identity.at("whole_task_completion").boolean()&&
                    identity.at("item_id")==json::Value(items[caseIndex])&&
                    identity.at("variant_id")==json::Value(variantIds[caseIndex][pick]),
                    "per-item four-note runtime permission and no full-task credit");
                ck(identity.at("bundle_sha256")==json::Value("39e597135613e695285df0048ef3bc7babdbf13633b5af6e711268bd7025b313")&&
                    identity.at("package_sha256")==json::Value("0043283eba195ffc2d303b6b7acbac11deb0fbff152a74749f5111609c581209")&&
                    identity.at("source_refs")==json::parse(R"(["L9-TXT1-31-45","L9-PDF1-p2","L9-TXT1-1-25","L9-PDF1-p1"])"),
                    "same immutable bundle but exact case and ordered refs");
                const auto& hashes=identity.at("source_hashes").object();
                ck(hashes.at("L9-TXT1-31-45")==json::Value("3cb0983c95081771caea7a12e8263d780f58850154681a9cd85c1a1916956105")&&
                    hashes.at("L9-PDF1-p2")==json::Value("3564ed3c24d55df462dba49b81ef2aeaf9a716a5a5af993bfdbf3e774702b00f")&&
                    hashes.at("L9-PDF1-p1")==hashes.at("L9-PDF1-p2"),
                    "exact original TXT and both PDF source hashes");
                const auto& events=admission->model()->source().events;
                ck(events.size()==4,"one exact four-note case");
                for(std::size_t i=0;i<4;++i)
                    ck(events[i].span.onset==Rational{static_cast<std::int64_t>(i),4}&&
                        events[i].span.duration==Rational{1,4}&&events[i].tones.size()==1&&
                        events[i].tones.front().midi==midi[caseIndex][i]&&
                        events[i].tones.front().fret==frets[caseIndex][i]&&
                        events[i].tones.front().string==(caseIndex==0?1:6)&&
                        events[i].handDirection==((i%2==0)==(pick==0)?"D":"U"),
                        "exact pitch/fret/sixteenth/source stroke "+std::to_string(caseIndex)+"/"+std::to_string(i));
                std::ofstream(out/(std::string(variantIds[caseIndex][pick])+"-admission.json"))<<
                    json::stringify(admission->identity());
            }
            refuses([&]{current->admit(items[caseIndex],variantIds[1-caseIndex][0]);},
                "other Level9 item's D variant refused");
            refuses([&]{current->admit(items[caseIndex],variantIds[1-caseIndex][1]);},
                "other Level9 item's U variant refused");
        }
        refuses([&]{current->admit("fg:item:000001","fg:variant:000001");},"unadmitted original refused");
        auto missing=prior;missing.push_back(out/"missing");
        refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing atomic Level9 bundle refused");
        auto foreign=withNew;foreign.push_back(l09);
        refuses([&]{lesson::Catalog::loadInstalled(base,foreign);},"foreign tenth extension refused");
        const auto mutableBundle=out/"mutable-level009";
        std::filesystem::copy(l09,mutableBundle,std::filesystem::copy_options::recursive);
        auto put=[](const std::filesystem::path& path,const std::string& bytes){std::ofstream output(path,std::ios::binary);output<<bytes;};
        const auto manifest=json::parse(content::readBounded(l09/"manifest.json",1024*1024));
        for(const auto* key:{"package","registry","profile","provenance","decision"}){
            const auto path=manifest.object().at("entries").object().at(key).string();
            const auto original=content::readBounded(mutableBundle/path,32*1024*1024);
            put(mutableBundle/path,"{}");auto altered=prior;altered.push_back(mutableBundle);
            refuses([&]{lesson::Catalog::loadInstalled(base,altered);},std::string("changed ")+key+" asset refused atomically");
            put(mutableBundle/path,original);
        }
        for(const auto* asset:{"Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.txt",
                               "Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_9_Mid_Pattern_Position_Transfer.pdf"}){
            const auto original=content::readBounded(mutableBundle/asset,32*1024*1024);
            put(mutableBundle/asset,"changed source");auto altered=prior;altered.push_back(mutableBundle);
            refuses([&]{lesson::Catalog::loadInstalled(base,altered);},std::string("changed original ")+asset+" refused");
            put(mutableBundle/asset,original);std::filesystem::remove(mutableBundle/asset);
            refuses([&]{lesson::Catalog::loadInstalled(base,altered);},std::string("missing original ")+asset+" refused");
            put(mutableBundle/asset,original);
        }
        put(mutableBundle/"unreviewed-extra.txt","x");auto altered=prior;altered.push_back(mutableBundle);
        refuses([&]{lesson::Catalog::loadInstalled(base,altered);},"unlisted installed file refused");
        std::filesystem::remove(mutableBundle/"unreviewed-extra.txt");
        ck(lesson::Catalog::loadInstalled(base,altered)->lessons().size()==23,
            "restored exact two-case bundle loads atomically");
        std::cout<<"PASS "<<checks<<" Level9 two-case generic catalog checks\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<'\n';return 1;}
}
