#include "content/LessonCatalog.hpp"
#include "content/Level080ModuleAPass1R02Extension.hpp"
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
    if(argc==3&&std::string(argv[1])=="--direct-l80"){
        const std::filesystem::path root=argv[2];
        const auto manifest=json::parse(content::readBounded(root/"manifest.json",1024*1024));
        const auto& entries=manifest.object().at("entries").object();
        auto read=[&](const char* key){return content::readBounded(root/entries.at(key).string(),32*1024*1024);};
        const auto package=read("package"),registry=read("registry"),profile=read("profile"),decision=read("decision");
        auto validate=[&](const std::string& p,const std::string& r,const std::string& f,const std::string& d){
            return lesson::validateLevel080ModuleAPass1R02Extension({p,r,f,manifest.object().at("profile_sha256").string(),root},
                d,manifest.object().at("decision_sha256").string(),{});};
        const auto result=validate(package,registry,profile,decision);
        ck(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==1,
           "single valid but native-nonadmitted supplemental reference");
        ck(result.variants.front().id=="fg:variant:007696"&&result.variants.front().source.events.size()==4&&
           result.variants.front().readiness.technicallyRenderable,"one technically renderable four-note variant");
        const auto value=json::parse(package);const auto& record=value.object().at("records").array().front();
        ck(record.object().at("timing").object().at("status").string()=="unresolved"&&
           record.object().at("title").string().find("source timing unspecified")!=std::string::npos,
           "source timing unresolved and supplemental label explicit");
        auto broken=value;broken.object().at("records").array().front().object().at("events").array()[1].object()["spelling"]="F#";
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"printed F-to-F# drift refused");
        broken=value;broken.object().at("records").array().front().object().at("timing").object()["status"]="source_defined";
        refuses([&]{validate(json::stringify(broken),registry,profile,decision);},"false source-defined timing refused");
        broken=json::parse(decision);broken.object()["status"]="PENDING";
        refuses([&]{validate(package,registry,profile,json::stringify(broken));},"unaccepted decision refused");
        broken=json::parse(registry);broken.object().at("entities").array().back().object()["parent"]="fg:item:009999";
        refuses([&]{validate(package,json::stringify(broken),profile,decision);},"foreign variant owner refused");
        broken=json::parse(profile);broken.object()["classification"]="unreviewed";
        refuses([&]{validate(package,registry,json::stringify(broken),decision);},"stale profile refused");
        std::cout<<"PASS "<<checks<<" direct Level80 source, one-variant and refusal checks\n";return 0;
    }
    if(argc!=31)throw std::runtime_error("Expected base, 28 finite extensions and fresh output");
    const std::filesystem::path base=argv[1],out=argv[30];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto check=[&](bool good,const std::string& why){ck(good,why);trace<<why<<'\t'<<(good?"PASS":"FAIL")<<'\n';};
    std::vector<std::filesystem::path> paths;for(int i=2;i<=29;++i)paths.emplace_back(argv[i]);
    const auto catalog=lesson::Catalog::loadInstalled(base,paths);
    const auto domain=progression::installedDomainCatalog(*catalog);
    check(domain.catalogs.size()==29&&progression::installedDomainManifests().size()==29&&
          domain.catalogs.back().entries.size()==1&&
          domain.catalogs.back().entries.front().binding.variant=="fg:variant:007696",
          "one recorded-only Level80 domain entry appended");
    check(catalog->lessons().size()==52&&catalog->sourceEntryCount()==198,
          "Rung08 accepted baseline plus one case and three declared sources");
    check(lesson::Catalog::installedExtensionDirectoryNames().size()==28&&
          lesson::Catalog::installedExtensionDirectoryNames().back()=="level080-module-a-pass1-r02-extension",
          "finite installed descriptor order and no discovery");
    const auto& selected=catalog->lesson("fg:item:001179");
    check(selected.variants.size()==1&&selected.variants.front().id=="fg:variant:007696"&&
          selected.title.find("Supplemental Fathom example")!=std::string::npos&&
          selected.title.find("source timing unspecified")!=std::string::npos,
          "single supplemental variant and honest installed label");
    const auto admission=catalog->admit("fg:item:001179","fg:variant:007696");
    check(admission&&admission->practiceAllowed()&&admission->span()==Rational{4},
          "exact one-variant q4 Practice admission");
    refuses([&]{(void)catalog->variant("fg:item:001179","fg:variant:007697");},"unallocated second variant unavailable");
    const auto index=learn::SourceIndex::load(base.parent_path()/"learn-source-index");
    const auto row=std::find_if(index->exercises().begin(),index->exercises().end(),[](const auto& v){
        return v.source.sourceExerciseKey=="level080/modulea/p003-card01/cmaj7melodyefge";});
    check(row!=index->exercises().end()&&row->bindings.size()==1&&row->bindings.front().supplemental&&
          !row->bindings.front().exact&&row->auditStatus.find("missing")!=std::string::npos,
          "original Level80 row remains missing and non-exact");
    check(learn::choices(*row,*catalog).empty()&&
          learn::availability(*row,*catalog).find("original source exercise remains incomplete")!=std::string::npos,
          "exact source Queue refuses but supplemental inspect is available");
    std::size_t playable=0;for(const auto& item:catalog->lessons()){
        if(std::any_of(item.variants.begin(),item.variants.end(),[&](const auto& variant){
            try {const auto a=catalog->admit(item.id,variant.id);return a&&a->practiceAllowed();}
            catch(const std::exception&) {return false;}}))++playable;
    }
    check(playable==41,"forty historical playable cases plus one supplemental case");
    std::cout<<"PASS "<<checks<<" installed Level80 supplemental catalog/Domain/Learn checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
