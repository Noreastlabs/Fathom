#include "content/LessonCatalog.hpp"
#include "content/Level001Extension.hpp"
#include "content/LearnSourceAdmission.hpp"
#include "content/LearnSourceIndexPins.hpp"
#include "progression/InstalledDomainCatalog.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
using namespace fathom;
int main(int argc,char** argv){std::size_t checks=0;try{
    auto ck=[&](bool yes,const std::string& why){++checks;if(!yes)throw std::runtime_error(why);};
    auto refuses=[&](auto action,const std::string& why){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,why);};
    if(argc==3&&std::string(argv[1])=="--direct"){
        const std::filesystem::path root=argv[2];
        const auto manifest=json::parse(content::readBounded(root/"manifest.json",1024*1024));
        const auto& entries=manifest.object().at("entries").object();
        auto read=[&](const char* key){return content::readBounded(root/entries.at(key).string(),32*1024*1024);};
        const auto package=read("package"),registry=read("registry"),profile=read("profile"),decision=read("decision");
        auto validate=[&](const std::string& p,const std::string& r,const std::string& f){
            return lesson::validateLevel001Extension({p,r,f,manifest.object().at("profile_sha256").string(),root});};
        const auto result=validate(package,registry,profile);
        ck(result.validReference&&result.exitCode==2&&result.records.size()==108&&result.variants.size()==648,
            "108 finite source-valid nonadmitted records, six present variants each");
        std::size_t full=0,old=0;
        for(const auto& v:result.variants){
            if(v.id>="fg:variant:007478"&&v.id<="fg:variant:007693"){
                ++full;ck(v.source.events.size()==48&&v.validation.validReference()&&v.readiness.technicallyRenderable,
                    "full48 model complete");
                const auto suffix=std::stoi(v.id.substr(11));const bool down=suffix%2==0;
                for(std::size_t i=0;i<48;++i)ck(v.source.events[i].span.onset==Rational{static_cast<std::int64_t>(i)}&&
                    v.source.events[i].span.duration==Rational{1}&&
                    v.source.events[i].handDirection==(((i%2==0)==down)?"D":"U"),
                    "exact Fathom quarter grid and continuous D/U parity");
            }else{++old;ck(v.source.events.size()==24&&!v.readiness.technicallyRenderable,
                    "historical half-route retained/read-only");}
        }
        ck(full==216&&old==432,"216 full and 432 historical variants exhaustive");
        auto changed=json::parse(profile);changed.object()["resource_plan"]=json::parse(R"({"path":"unexpected.json"})");
        ck(!validate(package,registry,json::stringify(changed)).validReference,"frozen-null profile adapter mutation refused");
        changed=json::parse(decision);changed.object()["automatic_credit"]=true;
        ck(content::sha256(json::stringify(changed))!=manifest.object().at("decision_sha256").string(),"automatic-credit decision digest mutation refused");
        changed=json::parse(package);changed.object().at("records").array().front().object().at("variants").array()[4].object().at("event_ids").array().pop_back();
        ck(!validate(json::stringify(changed),registry,profile).validReference,"47-contact mutant refused");
        std::cout<<"PASS "<<checks<<" direct Level1 full48/half-route and refusals\n";return 0;
    }
    if(argc!=3)throw std::runtime_error("Expected --installed <absolute Resources directory>");
    const std::filesystem::path resources=argv[2];
    ck(resources.is_absolute(),"absolute installed Resources");
    std::vector<std::filesystem::path> paths;
    for(const auto& name:lesson::Catalog::installedExtensionDirectoryNames())paths.push_back(resources/name);
    ck(paths.size()==32&&paths.back().filename()=="level001-extension","finite extension directory order");
    const auto catalog=lesson::Catalog::loadInstalled(resources/"representative-controls",paths);
    ck(catalog->lessons().size()==163&&catalog->sourceEntryCount()==339,"one replaced base owner, 107 appended units and 116 source entries");
    ck(catalog->lessons().front().id=="fg:item:000002","Guided default item002 preserved");
    ck(std::count_if(catalog->lessons().begin(),catalog->lessons().end(),[](const auto& v){return v.id=="fg:item:000001";})==1,
        "one item001 historical/revision4 owner");
    std::size_t variants=0;for(const auto& item:catalog->lessons())variants+=item.variants.size();
    ck(variants==778,"134 prior minus four replaced plus 648 finite variants");
    const auto domain=progression::installedDomainCatalog(*catalog);
    ck(domain.catalogs.size()==33&&domain.catalogs.back().entries.size()==216,"216 recorded-only Level1 Technique/fretboard entries");
    const auto index=learn::SourceIndex::load(resources/"learn-source-index");
    const auto& level=index->level(1);std::size_t ordinal=0,withinRanges=0;
    ck(level.sublevels.size()==4,"four original starting-finger groups");
    for(const auto& group:level.sublevels){
        ck(group.exercises.size()==27,"27 original exercises per group");
        for(std::size_t a=0;a<27;++a){
            const auto& source=index->exercises()[group.exercises[a]];
            ++ordinal;
            ck(source.source.levelOrder==ordinal&&source.bindings.size()==1&&source.bindings.front().exact,
                "ordered exact Level1 source binding");
            const auto item=source.bindings.front().itemId;
            ck(catalog->lesson(item).variants.size()==6,"four historical plus two full48 choices");
            const auto choice=learn::choices(source,*catalog);
            ck(choice.size()==2,"only full48 D/U choices are source-queue admitted");
            for(const auto& pick:choice){const auto a=catalog->admit(item,pick.variantId);
                ck(a->practiceAllowed()&&a->span()==Rational{48}&&a->model()->source().events.size()==48&&
                    !a->identity().object().at("whole_task_completion").boolean(),"exact full48 recorded-only Practice admission");}
            for(std::size_t b=a;b<27;++b){
                const auto& last=index->exercises()[group.exercises[b]];
                ck(index->range(1,group.key,source.source.sourceExerciseKey,last.source.sourceExerciseKey).size()==b-a+1,
                    "within-group contiguous source range");++withinRanges;}
        }
    }
    ck(ordinal==108&&withinRanges==1512,"108 source units and 1512 within-group ranges");
    for(std::size_t g=0;g<3;++g){
        const auto& a=index->exercises()[level.sublevels[g].exercises.back()];
        const auto& b=index->exercises()[level.sublevels[g+1].exercises.front()];
        refuses([&]{index->range(1,level.sublevels[g].key,a.source.sourceExerciseKey,b.source.sourceExerciseKey);},
            "cross-group 27-to-28/54-to-55/81-to-82 range refused");}
    const auto& first=catalog->lesson("fg:item:000001");
    ck(first.record.object().at("content_revision")==json::Value::fromInteger(4),"item001 revision4 owner");
    for(std::size_t k=0;k<4;++k)refuses([&]{catalog->admit(first.id,first.variants[k].id);},"historical half-route Practice refused");
    refuses([&]{catalog->admit("fg:item:000002","fg:variant:007478");},"foreign full48 variant refused");
    std::cout<<"PASS "<<checks<<" installed Level1 Catalog/Domain/Learn exhaustive checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
