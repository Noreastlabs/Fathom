#include "content/LessonCatalog.hpp"
#include "content/Level002Exercise002Extension.hpp"
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
    if(argc==3&&std::string(argv[1])=="--direct-ex002"){
        const std::filesystem::path root=argv[2];
        const auto manifest=json::parse(content::readBounded(root/"manifest.json",1024*1024));
        const auto& entries=manifest.object().at("entries").object();
        auto read=[&](const char* key){return content::readBounded(root/entries.at(key).string(),32*1024*1024);};
        const auto package=read("package"),registry=read("registry"),profile=read("profile"),decision=read("decision");
        auto validate=[&](const std::string& p,const std::string& r,const std::string& f,const std::string& d){
            return lesson::validateLevel002Exercise002Extension({p,r,f,manifest.object().at("profile_sha256").string(),root},
                d,manifest.object().at("decision_sha256").string(),{});};
        const auto result=validate(package,registry,profile,decision);
        ck(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
           "one source-valid but native-nonadmitted 40-contact case");
        for(const auto& v:result.variants){ck(v.validation.validReference()&&v.source.events.size()==40&&v.readiness.technicallyRenderable,
            "40 source-exact technically renderable contacts");
            for(std::size_t i=0;i<40;++i)ck(v.source.events[i].handDirection==(((i%2==0)==(v.id=="fg:variant:007716"))?"D":"U")&&
                v.source.events[i].span.onset==Rational{static_cast<std::int64_t>(i),4},
                "selected straight-sixteenth q grid and source D/U cycle "+std::to_string(i+1));}
        auto broken=json::parse(package);broken.object().at("records").array().front().object().at("events").array().front().object()["fret"]=json::Value::fromInteger(6);
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"wrong source fret refused");
        broken=json::parse(package);broken.object().at("records").array().front().object().at("events").array()[1].object()["onset_q"]=json::parse("[1,2]");
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"wrong onset refused");
        broken=json::parse(decision);broken.object()["status"]="PENDING";
        refuses([&]{validate(package,registry,profile,json::stringify(broken));},"unaccepted decision refused");
        broken=json::parse(registry);broken.object().at("entities").array().back().object()["parent"]="fg:item:009999";
        refuses([&]{validate(package,json::stringify(broken),profile,decision);},"foreign variant owner refused");
        broken=json::parse(profile);broken.object()["classification"]="unreviewed";
        refuses([&]{validate(package,registry,json::stringify(broken),decision);},"stale profile refused");
        std::cout<<"PASS "<<checks<<" direct Level2 Exercise002 source/no-credit and refusal checks\n";return 0;
    }
    if(argc!=41)throw std::runtime_error("Expected base, 38 finite extensions and fresh output");
    const std::filesystem::path base=argv[1],out=argv[40];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto check=[&](bool good,const std::string& why){ck(good,why);trace<<why<<'\t'<<(good?"PASS":"FAIL")<<'\n';};
    std::vector<std::filesystem::path> paths;for(int i=2;i<=39;++i)paths.emplace_back(argv[i]);
    const auto catalog=lesson::Catalog::loadInstalled(base,paths);
    const auto domain=progression::installedDomainCatalog(*catalog);
    check(domain.catalogs.size()==39&&progression::installedDomainManifests().size()==39&&
          domain.catalogs.back().entries.size()==2&&
          domain.catalogs.back().entries.front().binding.variant=="fg:variant:007716"&&
          domain.catalogs.back().entries.back().binding.variant=="fg:variant:007717",
          "exact two recorded-only Technique/fretboard domain entries appended");
    check(catalog->lessons().size()==169&&catalog->sourceEntryCount()==368,
          "accepted 168-case baseline plus one case and four source refs");
    check(lesson::Catalog::installedExtensionDirectoryNames().size()==38&&
          lesson::Catalog::installedExtensionDirectoryNames().back()=="level002-ex002-extension",
          "finite installed descriptor order and no discovery");
    std::size_t variants=0;for(const auto& item:catalog->lessons())variants+=item.variants.size();
    check(variants==790,"788 prior variants plus exact two Exercise002 variants");
    constexpr std::array<int,13> representativeLevels{1,3,12,15,29,39,48,49,58,74,83,97,105};
    for(std::size_t i=0;i<representativeLevels.size();++i){
        const auto digits=std::to_string(i+1);
        const auto id="fg:item:"+std::string(6-digits.size(),'0')+digits;
        check(catalog->lesson(id).level==representativeLevels[i],
              "original representative item and level retained "+id);
    }
    std::size_t level1Cases=0;
    for(const auto& item:catalog->lessons())if(item.level==1){
        ++level1Cases;
        check(item.variants.size()==6,"Level1 full-route and historical variants retained "+item.id);
    }
    check(level1Cases==108,"all 108 finite Level1 cases retained");
    const auto& selected=catalog->lesson("fg:item:001188");
    check(selected.level==2&&selected.variants.size()==2&&selected.title.find("Exercise002")!=std::string::npos,
          "one printed Exercise002 selection");
    for(const auto& id:std::array<const char*,2>{"fg:variant:007716","fg:variant:007717"}){
        const auto admission=catalog->admit("fg:item:001188",id);
        check(admission&&admission->practiceAllowed()&&admission->span()==Rational{10},
              "exact one-case q10 Practice admission");
        check(!admission->identity().object().at("whole_task_completion").boolean(),"no whole task credit");
        const auto& events=admission->model()->source().events;
        check(events.size()==40,"40 selected contacts");
        for(std::size_t i=0;i<40;++i)check(events[i].span.onset==Rational{static_cast<std::int64_t>(i),4}&&
            events[i].span.duration==Rational{1,4}&&
            events[i].handDirection==(((i%2==0)==(std::string(id)=="fg:variant:007716"))?"D":"U"),
            "selected relative grid and D/U stroke "+std::to_string(i+1));
    }
    refuses([&]{catalog->admit("fg:item:001188","fg:variant:007714");},"foreign variant cannot cross case");
    refuses([&]{catalog->admit("fg:item:000122","fg:variant:007716");},"historical detached item cannot enter Catalog");
    refuses([&]{catalog->admit("fg:item:009999","fg:variant:007716");},"foreign item cannot gain Exercise002 variant");
    const auto index=learn::SourceIndex::load(base.parent_path()/"learn-source-index");
    const auto& row=index->exercises()[index->level(2).sublevels.front().exercises[1]];
    check(row.source.sourceExerciseKey=="printed:l002:set-1-of-9-exercises-001-012:exercise-002-1213"&&
          row.bindings.size()==1&&row.bindings.front().exact&&learn::choices(row,*catalog).size()==2,
          "only exact printed Exercise002 source has two admitted choices");
    for(std::size_t neighbor:{std::size_t{0},std::size_t{2}}){
        const auto& other=index->exercises()[index->level(2).sublevels.front().exercises[neighbor]];
        check(learn::choices(other,*catalog).empty(),"unavailable adjacent Exercise001/003 refuses");}
    auto missing=paths;missing.back()=out/"missing-ex002";
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"declared Exercise002 bundle missing refuses");
    std::size_t playable=0;for(const auto& item:catalog->lessons())if(std::any_of(item.variants.begin(),item.variants.end(),[&](const auto& v){
        try{const auto a=catalog->admit(item.id,v.id);return a&&a->practiceAllowed();}catch(const std::exception&){return false;}}))++playable;
    check(playable==159,"158 prior playable cases plus one Exercise002 cell");
    std::cout<<"PASS "<<checks<<" installed Level2 Exercise002 Catalog/Domain/Learn checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
