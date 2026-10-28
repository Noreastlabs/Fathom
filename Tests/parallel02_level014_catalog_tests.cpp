#include "content/LessonCatalog.hpp"
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=15)throw std::runtime_error("Expected base, eleven prior extensions, Level14 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[14];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<'\n';if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=12;++i)prior.emplace_back(argv[i]);
    auto withNew=prior;withNew.emplace_back(argv[13]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,withNew);
    ck(old->lessons().size()==27&&current->lessons().size()==29&&
        old->sourceEntryCount()==104&&current->sourceEntryCount()==110,
        "two exact cases and six unique source entries counted once");
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
    ck(priorVariants==77,"all prior variants accounted for");
    constexpr std::array<int,36> strings{1,1,2,1,2,2,2,2,2,2,2,3,2,3,3,3,3,3,3,3,3,3,3,2,3,2,2,2,2,2,2,2,1,2,1,1};
    constexpr std::array<int,36> frets{5,7,4,7,4,5,4,5,7,5,7,4,7,4,6,4,6,7,7,6,4,6,4,7,4,7,5,7,5,4,5,4,7,4,7,5};
    constexpr std::array<int,36> fingers{2,4,1,4,1,2,1,2,4,2,4,1,4,1,3,1,3,4,4,3,1,3,1,4,1,4,2,4,2,1,2,1,4,1,4,2};
    constexpr std::array<int,36> midi{45,47,49,47,49,50,49,50,52,50,52,54,52,54,56,54,56,57,57,56,54,56,54,52,54,52,50,52,50,49,50,49,47,49,47,45};
    const std::array<const char*,2> items{"fg:item:001155","fg:item:001156"};
    const std::array<std::array<const char*,2>,2> variants{{{{"fg:variant:007432","fg:variant:007433"}},
        {{"fg:variant:007434","fg:variant:007435"}}}};
    for(std::size_t caseIndex=0;caseIndex<2;++caseIndex){
        const auto& selectedLesson=current->lesson(items[caseIndex]);
        ck(selectedLesson.title.find(caseIndex==0?"complete 36-note rolling-triplet cell":"A-major to Rung02 Bb-major")!=std::string::npos,
            "exact selected Learn title and Case A complete-cell qualifier");
        for(std::size_t pick=0;pick<2;++pick){
            const auto admission=current->admit(items[caseIndex],variants[caseIndex][pick]);
            const std::size_t count=caseIndex==0?36:72;
            ck(admission->practiceAllowed()&&admission->span()==Rational{caseIndex==0?12:25}&&
                !admission->identity().object().at("whole_task_completion").boolean(),
                "exact Case A/B selected span, runtime permission and no whole-task credit");
            const auto& identity=admission->identity().object();
            ck(identity.at("bundle_sha256")==json::Value("51851db9a08f16dbc8ffbd007aff5021bab42bc5404cca54c25c27144d82fc59")&&
                identity.at("package_sha256")==json::Value("7ecd337c1f5a40b176d8a2bffe04f28bbc8132dbd2045bb27560d3e683fb34f1")&&
                identity.at("content_version")==json::Value("curriculum-v1-level014-rung01-a-and-a-bb-triplet-build-only.1")&&
                identity.at("source_refs")==json::parse(R"(["L14-TXT-RULE-29-53","L14-PDF-GUIDANCE-P1","L14-TXT-RUNG01-56-67","L14-TXT-RUNG02-70-81","L14-PDF-CARDS-P3","L14-PDF-ROUTE-P2"])")&&
                identity.at("source_hashes").object().at("L14-TXT-RULE-29-53")==json::Value("301edb98b64daa90a015a3560b8c2219cfab13984d6a8c320765af48f444912b")&&
                identity.at("source_hashes").object().at("L14-PDF-CARDS-P3")==json::Value("c5ec5b0d1ed50c0c8af758a021f4488c886a1c6030c8a5a52cb755471ae7ed19"),
                "exact installed version, original source and decision bundle identity");
            const auto& events=admission->model()->source().events;
            ck(events.size()==count,"exact 36/72 note count");
            for(std::size_t i=0;i<count;++i){
                const auto& event=events[i];const auto& tone=event.tones.at(0);
                const bool secondCell=caseIndex==1&&i>=36;const auto sourceIndex=i%36;
                const auto expected=lesson::installedCaseOnset(Rational{1,3},i,caseIndex==1?36:0,
                    Rational{caseIndex==1?1:0});
                ck(event.kind==music::Kind::Note&&event.span.onset==expected&&
                    event.span.duration==Rational{1,3}&&event.tones.size()==1&&
                    tone.string==strings[sourceIndex]&&tone.fret==frets[sourceIndex]+(secondCell?1:0)&&
                    tone.midi==midi[sourceIndex]+(secondCell?1:0)&&
                    tone.finger==std::to_string(fingers[sourceIndex])&&
                    event.handDirection==(((i%2==0)==(pick==0))?"D":"U"),
                    "exact source contact, nominal onset and continuous D/U event "+std::to_string(i+1));
            }
        }
    }
    ck(lesson::validInstalledGap(72,36,1,1)&&
        lesson::installedCaseOnset(Rational{1,3},35,36,Rational{1})==Rational{35,3}&&
        lesson::installedCaseOnset(Rational{1,3},36,36,Rational{1})==Rational{13}&&
        lesson::installedCaseOnset(Rational{1,3},71,36,Rational{1})==Rational{74,3},
        "one beat only after event36, exact Bb boundary and final onset");
    ck(!lesson::validInstalledGap(72,0,1,1),"positive duration without boundary refused");
    ck(!lesson::validInstalledGap(72,36,0,1),"boundary without positive duration refused");
    ck(!lesson::validInstalledGap(72,72,1,1),"out-of-range boundary refused");
    ck(!lesson::validInstalledGap(72,36,1,0),"zero denominator refused");
    for(const auto wrongGap:{Rational{0},Rational{1,2},Rational{2}})
        ck(!(lesson::installedCaseOnset(Rational{1,3},36,36,wrongGap)==Rational{13}),
            "missing or wrong intercell pause differs from reviewed event37");
    refuses([&]{current->admit("fg:item:001155","fg:variant:007434");},"cross-case variant refused");
    refuses([&]{current->admit("fg:item:001156","fg:variant:007432");},"reverse cross-case variant refused");
    refuses([&]{lesson::Catalog::loadInstalled(base,std::vector<std::filesystem::path>{withNew.back()});},
        "out-of-order or partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level014");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing atomic Level14 bundle refused");
    const auto mutableBundle=out/"mutable-level014";
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
        if(std::string(fault)=="missing-pause")events[36].object()["onset_q"]=json::parse("[12,1]");
        else if(std::string(fault)=="short-pause")events[36].object()["onset_q"]=json::parse("[25,2]");
        else if(std::string(fault)=="long-pause")events[36].object()["onset_q"]=json::parse("[14,1]");
        else if(std::string(fault)=="shifted-pause")events[37].object()["onset_q"]=json::parse("[14,1]");
        else if(std::string(fault)=="extra-rest")events[36].object()["kind"]="rest";
        else events.pop_back();
        put(packagePath,json::stringify(packet));
        refuses([&]{lesson::Catalog::loadInstalled(base,altered);},
            std::string("changed ")+fault+" candidate refused by frozen manifest before timing guard");
        put(packagePath,originalPackage);
    }
    for(const auto* asset:{"Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_14_Major_Scale_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder.txt",
                           "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_14_Major_Scale_Three_Note_Rolling_Sequence_One_Octave_Neck_Ladder.pdf"}){
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
    ck(lesson::Catalog::loadInstalled(base,altered)->lessons().size()==29,
        "restored exact two-case bundle loads atomically");
    std::cout<<"PASS "<<checks<<" Level14 exact two-case Catalog checks\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
