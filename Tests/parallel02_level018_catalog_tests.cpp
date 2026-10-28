#include "content/LessonCatalog.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=19)throw std::runtime_error("Expected base, fifteen prior extensions, Level18 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[18];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<'\n';if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=16;++i)prior.emplace_back(argv[i]);
    auto withNew=prior;withNew.emplace_back(argv[17]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,withNew);
    ck(old->lessons().size()==34&&current->lessons().size()==36&&
        old->sourceEntryCount()==126&&current->sourceEntryCount()==132,
        "two exact cases and six unique source entries counted once");
    const auto installedOrder=lesson::Catalog::installedExtensionDirectoryNames();
    ck(installedOrder.size()>=16&&
       std::vector<std::string>(installedOrder.begin(),installedOrder.begin()+16)==std::vector<std::string>{
        "rung02-extension","rung03-extension","rung04-extension","level006-extension",
        "rung05-extension","level008-extension","level010-extension","level007-extension",
        "level009-extension","level011-extension","level013-extension","level014-extension","level015-extension","level016-extension","level017-extension","level018-extension"},"exact historical installed extension prefix");
    std::size_t priorVariants{};
    for(const auto& lesson:old->lessons()){
        ck(lesson.record==current->lesson(lesson.id).record&&
            old->contentVersion(lesson.id)==current->contentVersion(lesson.id),
            "prior record and owning version preserved "+lesson.id);
        for(const auto& variant:lesson.variants){
            ++priorVariants;
            ck(variant.authored==current->variant(lesson.id,variant.id).authored,
                "prior authored variant preserved "+variant.id);
            try{const auto a=old->admit(lesson.id,variant.id),b=current->admit(lesson.id,variant.id);
                ck(a->identity()==b->identity()&&a->sourceBinding()==b->sourceBinding()&&
                    a->span()==b->span(),"prior zero-gap runtime admission unchanged "+variant.id);
            }catch(const std::exception&){
                refuses([&]{current->admit(lesson.id,variant.id);},"prior refusal retained "+variant.id);
            }
        }
    }
    ck(priorVariants==91,"all prior variants accounted for");
    const auto newManifest=json::parse(content::readBounded(withNew.back()/"manifest.json",1024*1024));
    const auto packet=json::parse(content::readBounded(withNew.back()/newManifest.object().at("entries").object().at("package").string(),32*1024*1024));
    const std::array<const char*,2> items{"fg:item:001162","fg:item:001163"};
    const std::array<std::array<const char*,2>,2> variants{{{{"fg:variant:007446","fg:variant:007447"}},
        {{"fg:variant:007448","fg:variant:007449"}}}};
    for(std::size_t caseIndex=0;caseIndex<2;++caseIndex){
        const auto& selectedLesson=current->lesson(items[caseIndex]);
        ck(selectedLesson.title.find(caseIndex==0?"complete 52-contact diatonic-thirds cell":"A-major to Rung02 Bb-major")!=std::string::npos,
            "exact selected Learn title and Case A complete-cell qualifier");
        for(std::size_t pick=0;pick<2;++pick){
            const auto admission=current->admit(items[caseIndex],variants[caseIndex][pick]);
            const std::size_t count=caseIndex==0?52:104;
            ck(admission->practiceAllowed()&&admission->span()==Rational{caseIndex==0?26:53}&&
                !admission->identity().object().at("whole_task_completion").boolean(),
                "exact Case A/B selected span, runtime permission and no whole-task credit");
            const auto& identity=admission->identity().object();
            ck(identity.at("bundle_sha256")==json::Value("03adee5e7d46bbb1ed4815044c6b9f6db8137c3215fc1e3db427461707210c69")&&
                identity.at("package_sha256")==json::Value("09c3c9b3ae501fedcffdf01a9b309f587b571fdf7557232c0a20623f3147c538")&&
                identity.at("content_version")==json::Value("curriculum-v1-level018-first-two-cases-build-only.1")&&
                identity.at("source_refs")==json::parse(R"(["L18-TXT-GUIDANCE","L18-PDF-GUIDANCE","L18-TXT-RUNG01","L18-TXT-RUNG02","L18-PDF-CARDS","L18-PDF-ROUTE"])")&&
                identity.at("source_hashes").object().at("L18-TXT-GUIDANCE")==json::Value("a4faf2579a2d3546e2dc021640eeb3764ec7de9d858975a66f29f9611e2ad3a8")&&
                identity.at("source_hashes").object().at("L18-PDF-CARDS")==json::Value("a79374066ff017c148c11ec75791b02ba930560123dde1a6fcc933fe17821536"),
                "exact installed version, original source and decision bundle identity");
            const auto& events=admission->model()->source().events;
            ck(events.size()==count,"exact 52/104 note count");
            for(std::size_t i=0;i<count;++i){
                const auto& event=events[i];const auto& tone=event.tones.at(0);
                                const auto expected=lesson::installedCaseOnset(Rational{1,2},i,caseIndex==1?52:0,
                    Rational{caseIndex==1?1:0});
                ck(event.kind==music::Kind::Note&&event.span.onset==expected&&
                    event.span.duration==Rational{1,2}&&event.tones.size()==1&&
                    json::Value::fromInteger(tone.string)==packet.object().at("records").array()[caseIndex].object().at("events").array()[i].object().at("string")&&
                    json::Value::fromInteger(tone.fret)==packet.object().at("records").array()[caseIndex].object().at("events").array()[i].object().at("fret")&&
                    json::Value::fromInteger(tone.midi)==packet.object().at("records").array()[caseIndex].object().at("events").array()[i].object().at("midi")&&
                    event.handDirection==(((i%2==0)==(pick==0))?"D":"U"),
                    "exact source contact, nominal onset and continuous D/U event "+std::to_string(i+1));
            }
        }
    }
    ck(lesson::validInstalledGap(104,52,1,1)&&
        lesson::installedCaseOnset(Rational{1,2},51,52,Rational{1})==Rational{51,2}&&
        lesson::installedCaseOnset(Rational{1,2},52,52,Rational{1})==Rational{27}&&
        lesson::installedCaseOnset(Rational{1,2},103,52,Rational{1})==Rational{105,2},
        "one beat only after event52, exact Bb boundary and final onset");
    ck(!lesson::validInstalledGap(104,0,1,1),"positive duration without boundary refused");
    ck(!lesson::validInstalledGap(104,52,0,1),"boundary without positive duration refused");
    ck(!lesson::validInstalledGap(104,104,1,1),"out-of-range boundary refused");
    ck(!lesson::validInstalledGap(104,52,1,0),"zero denominator refused");
    for(const auto wrongGap:{Rational{0},Rational{1,2},Rational{2}})
        ck(!(lesson::installedCaseOnset(Rational{1,2},52,52,wrongGap)==Rational{27}),
            "missing or wrong intercell pause differs from reviewed event53");
    refuses([&]{current->admit("fg:item:001162","fg:variant:007448");},"cross-case variant refused");
    refuses([&]{current->admit("fg:item:001163","fg:variant:007446");},"reverse cross-case variant refused");
    refuses([&]{lesson::Catalog::loadInstalled(base,std::vector<std::filesystem::path>{withNew.back()});},
        "out-of-order or partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level018");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing atomic Level18 bundle refused");
    const auto mutableBundle=out/"mutable-level018";
    std::filesystem::copy(withNew.back(),mutableBundle,std::filesystem::copy_options::recursive);
    auto put=[](const std::filesystem::path& path,const std::string& bytes){std::ofstream output(path,std::ios::binary);output<<bytes;};
    const auto manifest=json::parse(content::readBounded(withNew.back()/"manifest.json",1024*1024));
    auto altered=prior;altered.push_back(mutableBundle);
    for(const auto* key:{"package","registry","profile","provenance","decision"}){
        const auto path=manifest.object().at("entries").object().at(key).string();
        const auto original=content::readBounded(mutableBundle/path,32*1024*1024);
        put(mutableBundle/path,"{}");
        refuses([&]{lesson::Catalog::loadInstalled(base,altered);},
            std::string("changed ")+key+" asset refused by immutable manifest");
        put(mutableBundle/path,original);
    }
    const auto packagePath=mutableBundle/manifest.object().at("entries").object().at("package").string();
    const auto originalPackage=content::readBounded(packagePath,32*1024*1024);
    for(const auto* fault:{"missing-pause","short-pause","long-pause","shifted-pause","extra-rest","event-count"}){
        auto packet=json::parse(originalPackage);
        auto& events=packet.object().at("records").array()[1].object().at("events").array();
        if(std::string(fault)=="missing-pause")events[52].object()["onset_q"]=json::parse("[26,1]");
        else if(std::string(fault)=="short-pause")events[52].object()["onset_q"]=json::parse("[53,2]");
        else if(std::string(fault)=="long-pause")events[52].object()["onset_q"]=json::parse("[28,1]");
        else if(std::string(fault)=="shifted-pause")events[53].object()["onset_q"]=json::parse("[28,1]");
        else if(std::string(fault)=="extra-rest")events[52].object()["kind"]="rest";
        else events.pop_back();
        put(packagePath,json::stringify(packet));
        refuses([&]{lesson::Catalog::loadInstalled(base,altered);},
            std::string("changed ")+fault+" candidate refused by frozen manifest before timing guard");
        put(packagePath,originalPackage);
    }
    for(const auto* asset:{"Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_18_Major_Scale_Diatonic_Thirds_Two_Octave_Six_String_Neck_Ladder.txt",
                           "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_18_Major_Scale_Diatonic_Thirds_Two_Octave_Six_String_Neck_Ladder.pdf"}){
        const auto original=content::readBounded(mutableBundle/asset,32*1024*1024);
        put(mutableBundle/asset,"changed original source");
        refuses([&]{lesson::Catalog::loadInstalled(base,altered);},"changed original TXT/PDF refused");
        put(mutableBundle/asset,original);std::filesystem::remove(mutableBundle/asset);
        refuses([&]{lesson::Catalog::loadInstalled(base,altered);},"missing original TXT/PDF refused");
        put(mutableBundle/asset,original);
    }
    put(mutableBundle/"unreviewed-extra.txt","x");
    refuses([&]{lesson::Catalog::loadInstalled(base,altered);},"unlisted installed file refused");
    std::filesystem::remove(mutableBundle/"unreviewed-extra.txt");
    ck(lesson::Catalog::loadInstalled(base,altered)->lessons().size()==36,
        "restored exact two-case bundle loads atomically");
    std::cout<<"PASS "<<checks<<" Level18 exact two-case Catalog checks\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
