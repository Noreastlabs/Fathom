#include "content/LessonCatalog.hpp"
#include "content/Level015Rungs0203Extension.hpp"
#include "content/LearnSourceAdmission.hpp"
#include "content/LearnSourceIndexPins.hpp"
#include "progression/InstalledDomainCatalog.hpp"
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    auto ck=[&](bool good,const std::string& why){++checks;if(!good)throw std::runtime_error(why);};
    auto refuses=[&](auto action,const std::string& why){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,why);};
    if(argc==3&&std::string(argv[1])=="--direct-r0203"){
        const std::filesystem::path root=argv[2];
        const auto manifest=json::parse(content::readBounded(root/"manifest.json",1024*1024));
        const auto& entries=manifest.object().at("entries").object();
        auto read=[&](const char* key){return content::readBounded(root/entries.at(key).string(),32*1024*1024);};
        const auto package=read("package"),registry=read("registry"),profile=read("profile"),decision=read("decision");
        auto validate=[&](const std::string& p,const std::string& r,const std::string& f,const std::string& d){
            return lesson::validateLevel015Rungs0203Extension({p,r,f,manifest.object().at("profile_sha256").string(),root},
                d,manifest.object().at("decision_sha256").string(),{});};
        const auto result=validate(package,registry,profile,decision);
        ck(result.validReference&&result.exitCode==2&&result.records.size()==2&&result.variants.size()==4,
           "two source-valid native-nonadmitted 78-contact cells");
        std::set<std::string> seen;
        for(const auto& v:result.variants){
            ck(v.validation.validReference()&&v.source.events.size()==78&&v.readiness.technicallyRenderable&&seen.insert(v.id).second,
               "78 source-exact renderable contacts and four distinct variants");
            const bool down=v.id=="fg:variant:007702"||v.id=="fg:variant:007704";
            for(std::size_t i=0;i<78;++i)ck(v.source.events[i].handDirection==(((i%2==0)==down)?"D":"U"),
                "continuous D/U cycle contact "+std::to_string(i+1));
        }
        auto broken=json::parse(package);broken.object().at("records").array().front().object().at("events").array().front().object()["fret"]=json::Value::fromInteger(99);
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"wrong printed fret refused");
        broken=json::parse(package);broken.object().at("records").array()[1].object().at("events").array().front().object()["onset_q"]=json::parse("[1,2]");
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"off-triplet onset refused");
        broken=json::parse(package);broken.object().at("records").array()[1].object().at("variants").array().front().object()["id"]="fg:variant:007702";
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"cross-case variant refused");
        broken=json::parse(package);broken.object().at("records").array().pop_back();
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"partial one-record bundle refused");
        broken=json::parse(decision);broken.object()["status"]="PENDING";
        refuses([&]{validate(package,registry,profile,json::stringify(broken));},"unaccepted decision refused");
        broken=json::parse(profile);broken.object()["classification"]="unreviewed";
        refuses([&]{validate(package,registry,json::stringify(broken),decision);},"changed profile refused");
        broken=json::parse(registry);broken.object().at("entities").array().back().object()["parent"]="fg:item:009999";
        refuses([&]{validate(package,json::stringify(broken),profile,decision);},"foreign registry owner refused");
        std::cout<<"PASS "<<checks<<" direct Level15 Rungs02-03 source and refusals\n";return 0;
    }
    if(argc!=34)throw std::runtime_error("Expected base, 31 finite extensions and fresh output");
    const std::filesystem::path base=argv[1],out=argv[33];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto check=[&](bool good,const std::string& why){ck(good,why);trace<<why<<'\t'<<(good?"PASS":"FAIL")<<'\n';};
    std::vector<std::filesystem::path> paths;for(int i=2;i<=32;++i)paths.emplace_back(argv[i]);
    const auto catalog=lesson::Catalog::loadInstalled(base,paths);
    const auto domain=progression::installedDomainCatalog(*catalog);
    check(domain.catalogs.size()==32&&progression::installedDomainManifests().size()==32&&
          domain.catalogs.back().entries.size()==4,"four separate recorded-only Technique/fretboard entries");
    check(catalog->lessons().size()==56&&catalog->sourceEntryCount()==223,
          "accepted 54-case baseline plus two cells and seven deduplicated refs");
    check(lesson::Catalog::installedExtensionDirectoryNames().size()==31&&
          lesson::Catalog::installedExtensionDirectoryNames().back()=="level015-rungs02-03-extension",
          "finite two-case descriptor and no discovery");
    std::size_t variants=0;for(const auto& l:catalog->lessons())variants+=l.variants.size();
    check(variants==134,"130 prior variants plus four exact new variants");
    check(catalog->lesson("fg:item:001157").level==15&&catalog->lesson("fg:item:001157").variants.size()==2,
          "Level15 Rung01 retained");
    const std::array<const char*,2> items{"fg:item:001181","fg:item:001182"};
    const std::array<std::array<const char*,2>,2> ids{{{"fg:variant:007702","fg:variant:007703"},{"fg:variant:007704","fg:variant:007705"}}};
    for(std::size_t k=0;k<2;++k){
        const auto& selected=catalog->lesson(items[k]);
        check(selected.level==15&&selected.variants.size()==2,"separate Level15 printed Rung selection");
        for(const auto* id:ids[k]){
            const auto admission=catalog->admit(items[k],id);
            check(admission&&admission->practiceAllowed()&&admission->span()==Rational{26},
                  "exact q26 standalone cell Practice admission");
            check(!admission->identity().object().at("whole_task_completion").boolean(),"no whole-task credit");
            const auto& events=admission->model()->source().events;
            check(events.size()==78,"78 source contacts in selected case");
            const bool down=std::string(id)==ids[k][0];
            for(std::size_t i=0;i<78;++i)check(events[i].span.onset==Rational{static_cast<std::int64_t>(i),3}&&
                events[i].span.duration==Rational{1,3}&&events[i].handDirection==(((i%2==0)==down)?"D":"U"),
                "source q-third and D/U stroke contact "+std::to_string(i+1));
        }
        refuses([&]{catalog->admit(items[k],ids[1-k][0]);},"cross-case variant cannot enter");
    }
    const auto index=learn::SourceIndex::load(base.parent_path()/"learn-source-index");
    const auto& l15=index->level(15).sublevels.front().exercises;
    for(std::size_t k=0;k<2;++k){const auto& rung=index->exercises()[l15[k+1]];
        check(rung.bindings.size()==1&&rung.bindings.front().exact&&rung.bindings.front().itemId==items[k]&&
              learn::choices(rung,*catalog).size()==2&&
              rung.locator.find(k==0?"PDF pages [2]":"PDF pages [3]")!=std::string::npos,
              "exact printed source row and PDF locator binds two D/U choices");}
    check(learn::choices(index->exercises()[l15[3]],*catalog).empty(),"Rung04 still unavailable");
    auto missing=paths;missing.back()=out/"missing-r0203";
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"declared two-case bundle missing refuses");
    std::size_t playable=0;for(const auto& item:catalog->lessons())if(std::any_of(item.variants.begin(),item.variants.end(),[&](const auto& variant){
        try{const auto a=catalog->admit(item.id,variant.id);return a&&a->practiceAllowed();}catch(const std::exception&){return false;}}))++playable;
    check(playable==45,"43 prior playable cases plus two exact cells");
    std::cout<<"PASS "<<checks<<" installed Level15 Rungs02-03 Catalog/Domain/Learn checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
