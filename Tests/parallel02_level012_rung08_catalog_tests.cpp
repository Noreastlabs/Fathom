#include "content/LessonCatalog.hpp"
#include "content/Level012Rung08Extension.hpp"
#include "progression/InstalledDomainCatalog.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>

using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    auto ck=[&](bool yes,const std::string& name){++checks;if(!yes)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    if(argc==3&&std::string(argv[1])=="--direct-r08"){
        const std::filesystem::path root=argv[2];
        const auto manifest=json::parse(content::readBounded(root/"manifest.json",1024*1024));
        const auto& entries=manifest.object().at("entries").object();
        auto read=[&](const char* key){return content::readBounded(root/entries.at(key).string(),32*1024*1024);};
        const auto package=read("package"),registry=read("registry"),profile=read("profile"),decision=read("decision");
        auto validate=[&](const std::string& p,const std::string& r,const std::string& f,const std::string& d){
            return lesson::validateLevel012Rung08Extension({p,r,f,manifest.object().at("profile_sha256").string(),root},
                d,manifest.object().at("decision_sha256").string(),{});};
        const auto result=validate(package,registry,profile,decision);
        ck(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
           "canonical source reference valid but nonadmitted");
        for(const auto& v:result.variants){ck(v.validation.validReference()&&v.source.events.size()==16,
            "16 source-exact native events");for(std::size_t i=0;i<16;++i)ck(v.source.events[i].handDirection==(((i%2==0)==(v.id=="fg:variant:007694"))?"D":"U"),
            "source D/U pick cycle at contact "+std::to_string(i+1));}
        auto broken=json::parse(package);broken.object().at("records").array().front().object().at("events").array().front().object()["fret"]=json::Value::fromInteger(13);
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"wrong fret12-to-13 refuses installed decision pin");
        broken=json::parse(decision);broken.object()["status"]="PENDING";
        refuses([&]{validate(package,registry,profile,json::stringify(broken));},"nonaccepted decision refused");
        broken=json::parse(registry);broken.object().at("entities").array().back().object()["parent"]="fg:item:009999";
        refuses([&]{validate(package,json::stringify(broken),profile,decision);},"cross-case registry refused");
        broken=json::parse(profile);broken.object()["classification"]="unreviewed";
        refuses([&]{validate(package,registry,json::stringify(broken),decision);},"stale or altered profile refused");
        std::cout<<"PASS "<<checks<<" direct Rung08 source/refusal checks\n";return 0;
    }
    if(argc!=30)throw std::runtime_error("Expected base, 27 finite extensions and fresh output");
    const std::filesystem::path base=argv[1],out=argv[29];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto check=[&](bool yes,const std::string& name){ck(yes,name);trace<<name<<'\t'<<(yes?"PASS":"FAIL")<<'\n';};
    std::vector<std::filesystem::path> paths;for(int i=2;i<=28;++i)paths.emplace_back(argv[i]);
    const auto catalog=lesson::Catalog::loadInstalled(base,paths);
    const auto domain=progression::installedDomainCatalog(*catalog);
    check(domain.catalogs.size()==28&&progression::installedDomainManifests().size()==28&&
          domain.catalogs.back().entries.size()==2&&
          domain.catalogs.back().entries[0].binding.variant=="fg:variant:007694"&&
          domain.catalogs.back().entries[1].binding.variant=="fg:variant:007695",
          "one exact Rung08 Technique/fretboard domain pair added");
    check(catalog->lessons().size()==51&&catalog->sourceEntryCount()==195,
          "fifty prior cases plus one Rung08 and seven source keys");
    check(lesson::Catalog::installedExtensionDirectoryNames().size()==27&&
          lesson::Catalog::installedExtensionDirectoryNames().back()=="level012-rung08-extension",
          "finite Rung08 descriptor is last");
    std::size_t variants=0;for(const auto& l:catalog->lessons())variants+=l.variants.size();
    check(variants==125,"123 prior variants plus two Rung08 variants");
    for(int i=1;i<=13;++i)check(catalog->lesson("fg:item:"+std::string(6-std::to_string(i).size(),'0')+std::to_string(i)).id.size()>0,
        "original admitted case preserved "+std::to_string(i));
    const auto& selected=catalog->lesson("fg:item:001178");
    check(selected.level==12&&selected.variants.size()==2&&selected.title.find("Rung 08")!=std::string::npos,
          "one printed Rung08 selection");
    const std::array<const char*,2> ids{"fg:variant:007694","fg:variant:007695"};
    for(std::size_t pick=0;pick<2;++pick){const auto token=catalog->admit("fg:item:001178",ids[pick]);
        check(token&&token->practiceAllowed()&&token->span()==Rational{8},"exact q8 Practice admission");
        check(token->identity().object().at("whole_task_completion").isBool()&&
              !token->identity().object().at("whole_task_completion").boolean(),"no whole task credit");
        const auto& events=token->model()->source().events;
        check(events.size()==16,"sixteen selected contacts");
        for(std::size_t i=0;i<events.size();++i)check(events[i].span.onset==Rational{static_cast<std::int64_t>(i),2}&&
            events[i].span.duration==Rational{1,2}&&
            events[i].handDirection==(((i%2==0)==(pick==0))?"D":"U"),
            "exact even eighth and D/U source stroke "+std::to_string(i+1));
    }
    refuses([&]{catalog->admit("fg:item:001178","fg:variant:007693");},"reserved Level1 variant cannot cross case");
    refuses([&]{catalog->admit("fg:item:990008","fg:variant:9900081");},"Oracle placeholder cannot enter Catalog");
    refuses([&]{catalog->admit("fg:item:000001","fg:variant:000001");},"historical unadmitted case remains refused");
    auto missing=paths;missing.back()=out/"missing-r08";
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"declared Rung08 bundle missing refuses");
    std::cout<<"PASS "<<checks<<" installed Rung08 catalog checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
