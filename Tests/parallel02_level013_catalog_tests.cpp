#include "content/LessonCatalog.hpp"
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=14)throw std::runtime_error("Expected base, ten prior extensions, Level13 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[13];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<'\n';if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=11;++i)prior.emplace_back(argv[i]);
    auto withNew=prior;withNew.emplace_back(argv[12]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,withNew);
    ck(old->lessons().size()==25&&current->lessons().size()==27&&
        old->sourceEntryCount()==99&&current->sourceEntryCount()==104,
        "two exact cases and five unique source entries counted once");
    const auto installed=lesson::Catalog::installedExtensionDirectoryNames();
    const std::vector<std::string> historical{
        "rung02-extension","rung03-extension","rung04-extension","level006-extension",
        "rung05-extension","level008-extension","level010-extension","level007-extension",
        "level009-extension","level011-extension","level013-extension","level014-extension","level015-extension","level016-extension"};
    const auto hasExactHistoricalPrefix=[&](const std::vector<std::string>& sequence){
        return sequence.size()>=historical.size()&&
            std::equal(historical.begin(),historical.end(),sequence.begin());
    };
    ck(hasExactHistoricalPrefix(installed),"finite historical installed extension prefix");
    auto omittedPrefix=installed;omittedPrefix.erase(omittedPrefix.begin()+1);
    ck(!hasExactHistoricalPrefix(omittedPrefix),"missing historical extension fails prefix");
    auto reorderedPrefix=installed;std::swap(reorderedPrefix[0],reorderedPrefix[1]);
    ck(!hasExactHistoricalPrefix(reorderedPrefix),"reordered historical extensions fail prefix");
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
    ck(priorVariants==73,"all prior variants accounted for");
    constexpr std::array<int,30> strings{1,1,2,2,2,3,3,3,4,4,4,5,5,6,6,6,6,5,5,4,4,4,3,3,3,2,2,2,1,1};
    constexpr std::array<int,30> frets{5,7,4,5,7,4,6,7,4,6,7,5,7,4,5,5,4,7,5,7,6,4,7,6,4,7,5,4,7,5};
    constexpr std::array<int,30> fingers{2,4,1,2,4,1,3,4,1,3,4,2,4,1,2,2,1,4,2,4,3,1,4,3,1,4,2,1,4,2};
    constexpr std::array<int,30> midi{45,47,49,50,52,54,56,57,59,61,62,64,66,68,69,69,68,66,64,62,61,59,57,56,54,52,50,49,47,45};
    const std::array<const char*,2> items{"fg:item:001153","fg:item:001154"};
    const std::array<std::array<const char*,2>,2> variants{{{{"fg:variant:007428","fg:variant:007429"}},
        {{"fg:variant:007430","fg:variant:007431"}}}};
    for(std::size_t caseIndex=0;caseIndex<2;++caseIndex){
        const auto& selectedLesson=current->lesson(items[caseIndex]);
        ck(selectedLesson.title.find(caseIndex==0?"excerpt of neighbor-stage":"A-major to Rung02 Bb-major")!=std::string::npos,
            "exact selected Learn title and Case A excerpt qualifier");
        for(std::size_t pick=0;pick<2;++pick){
            const auto admission=current->admit(items[caseIndex],variants[caseIndex][pick]);
            const std::size_t count=caseIndex==0?30:60;
            ck(admission->practiceAllowed()&&admission->span()==Rational{caseIndex==0?15:31}&&
                !admission->identity().object().at("whole_task_completion").boolean(),
                "exact Case A/B selected span, runtime permission and no whole-task credit");
            const auto& identity=admission->identity().object();
            ck(identity.at("bundle_sha256")==json::Value("e0edd51ab639c58b6421f3ad5cd14fd57585129d8377c10cdb9f6e8eca053b6b")&&
                identity.at("package_sha256")==json::Value("c8903cd600f8f9082f7e3471e1ef7ce23e103bfcb66c4a9a5e919d7b1b713df4")&&
                identity.at("content_version")==json::Value("curriculum-v1-level013-rung01-a-and-a-bb-timed-build-only.1")&&
                identity.at("source_refs")==json::parse(R"(["L13-TXT-RULE-29-49","L13-PDF-GUIDANCE-P1","L13-TXT-RUNG01-52-63","L13-TXT-RUNG02-66-77","L13-PDF-CARDS-P3"])")&&
                identity.at("source_hashes").object().at("L13-TXT-RULE-29-49")==json::Value("973b9c614546e432282dcc0ba415a21c0bc28858e61e7910ef2d0559329a0956")&&
                identity.at("source_hashes").object().at("L13-PDF-CARDS-P3")==json::Value("0730f903d6d7a992b1f366f0e4977c05ba59d6467666fde5a7ea15ff20ca040c"),
                "exact installed version, original source and decision bundle identity");
            const auto& events=admission->model()->source().events;
            ck(events.size()==count,"exact 30/60 note count");
            for(std::size_t i=0;i<count;++i){
                const auto& event=events[i];const auto& tone=event.tones.at(0);
                const bool secondCell=caseIndex==1&&i>=30;const auto sourceIndex=i%30;
                const auto expected=lesson::installedCaseOnset(Rational{1,2},i,caseIndex==1?30:0,
                    Rational{caseIndex==1?1:0});
                ck(event.kind==music::Kind::Note&&event.span.onset==expected&&
                    event.span.duration==Rational{1,2}&&event.tones.size()==1&&
                    tone.string==strings[sourceIndex]&&tone.fret==frets[sourceIndex]+(secondCell?1:0)&&
                    tone.midi==midi[sourceIndex]+(secondCell?1:0)&&
                    tone.finger==std::to_string(fingers[sourceIndex])&&
                    event.handDirection==(((i%2==0)==(pick==0))?"D":"U"),
                    "exact source contact, nominal onset and continuous D/U event "+std::to_string(i+1));
            }
        }
    }
    ck(lesson::validInstalledGap(60,30,1,1)&&
        lesson::installedCaseOnset(Rational{1,2},29,30,Rational{1})==Rational{29,2}&&
        lesson::installedCaseOnset(Rational{1,2},30,30,Rational{1})==Rational{16}&&
        lesson::installedCaseOnset(Rational{1,2},59,30,Rational{1})==Rational{61,2},
        "one beat only after event30, exact Bb boundary and final onset");
    ck(!lesson::validInstalledGap(60,0,1,1),"positive duration without boundary refused");
    ck(!lesson::validInstalledGap(60,30,0,1),"boundary without positive duration refused");
    ck(!lesson::validInstalledGap(60,60,1,1),"out-of-range boundary refused");
    ck(!lesson::validInstalledGap(60,30,1,0),"zero denominator refused");
    for(const auto wrongGap:{Rational{0},Rational{1,2},Rational{2}})
        ck(!(lesson::installedCaseOnset(Rational{1,2},30,30,wrongGap)==Rational{16}),
            "missing or wrong intercell pause differs from reviewed event31");
    refuses([&]{current->admit("fg:item:001153","fg:variant:007430");},"cross-case variant refused");
    refuses([&]{current->admit("fg:item:001154","fg:variant:007428");},"reverse cross-case variant refused");
    refuses([&]{lesson::Catalog::loadInstalled(base,std::vector<std::filesystem::path>{withNew.back()});},
        "out-of-order or partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level013");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing atomic Level13 bundle refused");
    const auto mutableBundle=out/"mutable-level013";
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
        if(std::string(fault)=="missing-pause")events[30].object()["onset_q"]=json::parse("[15,1]");
        else if(std::string(fault)=="short-pause")events[30].object()["onset_q"]=json::parse("[31,2]");
        else if(std::string(fault)=="long-pause")events[30].object()["onset_q"]=json::parse("[17,1]");
        else if(std::string(fault)=="shifted-pause")events[31].object()["onset_q"]=json::parse("[17,1]");
        else if(std::string(fault)=="extra-rest")events[30].object()["kind"]="rest";
        else events.pop_back();
        put(packagePath,json::stringify(packet));
        refuses([&]{lesson::Catalog::loadInstalled(base,altered);},
            std::string("changed ")+fault+" candidate refused by frozen manifest before timing guard");
        put(packagePath,originalPackage);
    }
    for(const auto* asset:{"Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_13_Major_Scale_Two_Octave_Six_String_Neck_Ladder.txt",
                           "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_13_Major_Scale_Two_Octave_Six_String_Neck_Ladder.pdf"}){
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
    ck(lesson::Catalog::loadInstalled(base,altered)->lessons().size()==27,
        "restored exact two-case bundle loads atomically");
    std::cout<<"PASS "<<checks<<" Level13 exact two-case Catalog checks\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
