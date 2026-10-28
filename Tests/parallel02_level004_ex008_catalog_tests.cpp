#include "content/LessonCatalog.hpp"
#include "content/Level004Exercise008Extension.hpp"
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
    if(argc==3&&std::string(argv[1])=="--direct-ex008"){
        const std::filesystem::path root=argv[2];
        const auto manifest=json::parse(content::readBounded(root/"manifest.json",1024*1024));
        const auto& entries=manifest.object().at("entries").object();
        auto read=[&](const char* key){return content::readBounded(root/entries.at(key).string(),32*1024*1024);};
        const auto package=read("package"),registry=read("registry"),profile=read("profile"),decision=read("decision");
        auto validate=[&](const std::string& p,const std::string& r,const std::string& f,const std::string& d){
            return lesson::validateLevel004Exercise008Extension({p,r,f,manifest.object().at("profile_sha256").string(),root},
                d,manifest.object().at("decision_sha256").string(),{});};
        const auto result=validate(package,registry,profile,decision);
        ck(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==12,
           "exact nonadmitted rev1 reference retains all12 variants");
        const auto record=json::parse(package).object().at("records").array().front();
        ck(lesson::exactLevel004Ex008RetainedVariants(record.object().at("variants")),"all12 exact identities/memberships retained");
        for(const auto& v:result.variants){
            const bool selected=v.id=="fg:variant:003359"||v.id=="fg:variant:003361";
            ck(v.source.events.size()==32&&v.readiness.technicallyRenderable==selected,
               "only selected second-pass D/U route renders");
            if(selected)for(std::size_t i=0;i<32;++i)
                ck(v.source.events[i].span.onset==Rational{static_cast<std::int64_t>(i),4}&&
                   v.source.events[i].span.duration==Rational{1,4}&&
                   v.source.events[i].handDirection==(((i%2==0)==(v.id=="fg:variant:003359"))?"D":"U"),
                   "exact q-grid and pick parity");
        }
        auto missing=record.object().at("variants");missing.array().pop_back();
        ck(!lesson::exactLevel004Ex008RetainedVariants(missing),"missing historical variant refuses");
        auto extra=record.object().at("variants");extra.array().push_back(extra.array().back());
        ck(!lesson::exactLevel004Ex008RetainedVariants(extra),"extra historical variant refuses");
        auto duplicate=record.object().at("variants");duplicate.array().back().object()["id"]="fg:variant:003358";
        ck(!lesson::exactLevel004Ex008RetainedVariants(duplicate),"duplicate historical variant refuses");
        auto bad=json::parse(package);bad.object().at("records").array().front().object().at("events").array().front().object()["fret"]=json::Value::fromInteger(99);
        refuses([&]{validate(json::stringify(bad),registry,profile,decision);},"wrong printed fret refuses");
        bad=json::parse(decision);bad.object()["status"]="PENDING";
        refuses([&]{validate(package,registry,profile,json::stringify(bad));},"absent prospective decision refuses");
        bad=json::parse(profile);bad.object()["classification"]="changed";
        refuses([&]{validate(package,registry,json::stringify(bad),decision);},"stale profile refuses");
        bad=json::parse(registry);bad.object().at("entities").array().back().object()["parent"]="fg:item:009999";
        refuses([&]{validate(package,json::stringify(bad),profile,decision);},"foreign variant owner refuses");
        std::cout<<"PASS "<<checks<<" direct Level4 Exercise008 all12/two-selected/refusal checks\n";return 0;
    }
    if(argc!=49)throw std::runtime_error("Expected base, 46 finite extensions and fresh output");
    const std::filesystem::path base=argv[1],out=argv[48];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute evidence directory required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto check=[&](bool good,const std::string& why){ck(good,why);trace<<why<<'\t'<<(good?"PASS":"FAIL")<<'\n';};
    std::vector<std::filesystem::path> paths;for(int i=2;i<=47;++i)paths.emplace_back(argv[i]);
    const auto catalog=lesson::Catalog::loadInstalled(base,paths);
    const auto domain=progression::installedDomainCatalog(*catalog);
    check(catalog->lessons().size()==177&&catalog->sourceEntryCount()==401,
          "prior176 cases/397 sources plus exact one Level4 case/four source passages");
    std::size_t variants=0;for(const auto& item:catalog->lessons())variants+=item.variants.size();
    check(variants==886,"prior874 retained variants plus all12 historically allocated Level4 variants");
    check(domain.catalogs.size()==47&&domain.catalogs.back().entries.size()==2,
          "exact two selected Level4 domain entries, 47 catalogs total");
    const auto& selected=catalog->lesson("fg:item:000451");
    check(selected.level==4&&selected.variants.size()==12&&selected.record.object().at("content_revision")==json::Value::fromInteger(1),
          "existing rev1 item and all12 variants retained");
    for(int number=3358;number<=3369;++number){const auto digits=std::to_string(number);
        const auto id="fg:variant:"+std::string(6-digits.size(),'0')+digits;
        if(number==3359||number==3361){const auto admission=catalog->admit("fg:item:000451",id);
            check(admission&&admission->practiceAllowed()&&admission->span()==Rational{8},"selected q8 D/U Practice route");
        }else refuses([&]{catalog->admit("fg:item:000451",id);},"ten unselected historical siblings refuse Practice");}
    std::size_t level1=0;for(const auto& item:catalog->lessons())if(item.level==1){++level1;check(item.variants.size()==6,"Level1 case retained");}
    check(level1==108,"all 108 Level1 cases retained");
    const auto index=learn::SourceIndex::load(base.parent_path()/"learn-source-index");
    const auto it=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& row){
        return row.source.sourceExerciseKey=="printed:l004:set-1-of-9-exercises-001-012:exercise-008-1242";});
    check(it!=index->exercises().end()&&it->bindings.size()==1&&it->bindings.front().exact&&
          it->bindings.front().itemId=="fg:item:000451"&&
          it->bindings.front().variants==std::vector<std::string>{"fg:variant:003359","fg:variant:003361"}&&
          learn::choices(*it,*catalog).size()==2,"only exact printed Ex008 source row offers two admitted variants");
    check(index->exercises()[std::distance(index->exercises().begin(),it)+1].bindings.empty(),
          "neighboring Exercise009 remains unavailable");
    std::size_t playable=0;for(const auto& item:catalog->lessons())if(std::any_of(item.variants.begin(),item.variants.end(),[&](const auto& v){
        try{const auto a=catalog->admit(item.id,v.id);return a&&a->practiceAllowed();}catch(const std::exception&){return false;}}))++playable;
    check(playable==167,"166 prior playable cases plus one bounded Level4 second pass");
    auto missing=paths;missing.back()=out/"missing-ex008";
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing declared Level4 bundle refuses");
    std::cout<<"PASS "<<checks<<" installed Level4 Exercise008 Catalog/Domain/Learn checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
