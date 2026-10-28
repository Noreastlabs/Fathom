#include "content/LessonCatalog.hpp"
#include "content/Level015Rung06Extension.hpp"
#include "content/LearnSourceAdmission.hpp"
#include "content/LearnSourceIndexPins.hpp"
#include "progression/InstalledDomainCatalog.hpp"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    auto ck=[&](bool good,const std::string& why){++checks;if(!good)throw std::runtime_error(why);};
    auto refuses=[&](auto action,const std::string& why){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,why);};
    if(argc==3&&std::string(argv[1])=="--direct-r06"){
        const std::filesystem::path root=argv[2];
        const auto manifest=json::parse(content::readBounded(root/"manifest.json",1024*1024));
        const auto& entries=manifest.object().at("entries").object();
        auto read=[&](const char* key){return content::readBounded(root/entries.at(key).string(),32*1024*1024);};
        const auto package=read("package"),registry=read("registry"),profile=read("profile"),decision=read("decision");
        auto validate=[&](const std::string& p,const std::string& r,const std::string& f,const std::string& d){
            return lesson::validateLevel015Rung06Extension({p,r,f,manifest.object().at("profile_sha256").string(),root},
                d,manifest.object().at("decision_sha256").string(),{});};
        const auto result=validate(package,registry,profile,decision);
        ck(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
           "one source-valid but native-nonadmitted 78-contact C-major cell");
        for(const auto& v:result.variants){ck(v.validation.validReference()&&v.source.events.size()==78&&v.readiness.technicallyRenderable,
            "78 source-exact technically renderable contacts");
            for(std::size_t i=0;i<78;++i)ck(v.source.events[i].handDirection==(((i%2==0)==(v.id=="fg:variant:007714"))?"D":"U"),
                "source D/U pick cycle "+std::to_string(i+1));}
        auto broken=json::parse(package);broken.object().at("records").array().front().object().at("events").array().front().object()["finger"]=json::Value::fromInteger(99);
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"source finger 2-to-3 drift refused");
        broken=json::parse(package);broken.object().at("records").array().front().object().at("events").array()[1].object()["onset_q"]=json::parse("[1,2]");
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"source half-quarter onset drift refused");
        broken=json::parse(package);broken.object().at("records").array().front().object().at("events").array().front().object()["fret"]=json::Value::fromInteger(10);
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"source wrong fret refused");
        broken=json::parse(decision);broken.object()["status"]="PENDING";
        refuses([&]{validate(package,registry,profile,json::stringify(broken));},"unaccepted decision refused");
        broken=json::parse(registry);broken.object().at("entities").array().back().object()["parent"]="fg:item:009999";
        refuses([&]{validate(package,json::stringify(broken),profile,decision);},"foreign variant owner refused");
        broken=json::parse(profile);broken.object()["classification"]="unreviewed";
        refuses([&]{validate(package,registry,json::stringify(broken),decision);},"stale profile refused");
        std::cout<<"PASS "<<checks<<" direct Level15 Rung06 source/no-credit and refusal checks\n";return 0;
    }
    if(argc!=40)throw std::runtime_error("Expected base, 37 finite extensions and fresh output");
    const std::filesystem::path base=argv[1],out=argv[39];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto check=[&](bool good,const std::string& why){ck(good,why);trace<<why<<'\t'<<(good?"PASS":"FAIL")<<'\n';};
    std::vector<std::filesystem::path> paths;for(int i=2;i<=38;++i)paths.emplace_back(argv[i]);
    const auto catalog=lesson::Catalog::loadInstalled(base,paths);
    const auto domain=progression::installedDomainCatalog(*catalog);
    check(domain.catalogs.size()==38&&progression::installedDomainManifests().size()==38&&
          domain.catalogs.back().entries.size()==2&&
          domain.catalogs.back().entries.front().binding.variant=="fg:variant:007714"&&
          domain.catalogs.back().entries.back().binding.variant=="fg:variant:007715",
          "exact two recorded-only Technique/fretboard domain entries appended");
    check(catalog->lessons().size()==168&&catalog->sourceEntryCount()==364,
          "accepted 167-case baseline plus one 78-contact, five-passage case");
    check(lesson::Catalog::installedExtensionDirectoryNames().size()==37&&
          lesson::Catalog::installedExtensionDirectoryNames().back()=="level015-rung06-extension",
          "finite installed descriptor order and no discovery");
    std::size_t variants=0;for(const auto& lesson:catalog->lessons())variants+=lesson.variants.size();
    check(variants==788,"786 prior variants plus exact two Rung06 variants");
    for(int i=1;i<=13;++i)check(catalog->lesson("fg:item:"+std::string(6-std::to_string(i).size(),'0')+std::to_string(i)).id.size()>0,
         "original admitted case preserved "+std::to_string(i));
    check(catalog->lesson("fg:item:001153").level==13&&catalog->lesson("fg:item:001154").level==13,
          "previous Level13 Rung01/Rung02 cases retained");
    const auto& selected=catalog->lesson("fg:item:001187");
    check(selected.level==15&&selected.variants.size()==2&&selected.title.find("Rung06")!=std::string::npos,
          "one printed Rung06 selection");
    for(const auto& id:std::array<const char*,2>{"fg:variant:007714","fg:variant:007715"}){
        const auto admission=catalog->admit("fg:item:001187",id);
        check(admission&&admission->practiceAllowed()&&admission->span()==Rational{26},
              "exact one-cell q26 Practice admission");
        check(!admission->identity().object().at("whole_task_completion").boolean(),
              "no whole task credit");
        const auto& events=admission->model()->source().events;
        check(events.size()==78,"78 selected contacts");
        for(std::size_t i=0;i<78;++i)check(events[i].span.onset==Rational{static_cast<std::int64_t>(i),3}&&
            events[i].span.duration==Rational{1,3}&&
            events[i].handDirection==(((i%2==0)==(std::string(id)=="fg:variant:007714"))?"D":"U"),
            "exact attributed triplet and source D/U stroke "+std::to_string(i+1));
    }
    refuses([&]{catalog->admit("fg:item:001187","fg:variant:007705");},"foreign variant cannot cross case");
    refuses([&]{catalog->admit("fg:item:001187","fg:variant:007709");},"historical provisional variant cannot enter Catalog");
    refuses([&]{catalog->admit("fg:item:009999","fg:variant:007714");},"foreign item cannot gain Rung06 variant");
    const auto index=learn::SourceIndex::load(base.parent_path()/"learn-source-index");
    const auto& rung=index->exercises()[index->level(15).sublevels.front().exercises[5]];
    check(rung.source.sourceExerciseKey=="printed:l015:complete-tablature:rung-06-of-13-d-major-root-on-low-e-fret-10-frame-9-12"&&
          rung.bindings.size()==1&&rung.bindings.front().exact&&learn::choices(rung,*catalog).size()==2,
          "only exact printed Rung06 source Queue has two admitted choices");
    const auto& next=index->exercises()[index->level(15).sublevels.front().exercises[6]];
    check(learn::choices(next,*catalog).empty(),"unavailable Level15 Rung07 still refuses");
    auto missing=paths;missing.back()=out/"missing-r06";
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"declared Rung06 bundle missing refuses");
    std::size_t playable=0;for(const auto& item:catalog->lessons()){
        if(std::any_of(item.variants.begin(),item.variants.end(),[&](const auto& variant){
            try{const auto a=catalog->admit(item.id,variant.id);return a&&a->practiceAllowed();}
            catch(const std::exception&){return false;}}))++playable;
    }
    check(playable==158,"157 prior playable cases plus one Rung06 cell");
    std::cout<<"PASS "<<checks<<" installed Level15 Rung06 catalog/Domain/Learn checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
