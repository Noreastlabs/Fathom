#include "content/LessonCatalog.hpp"
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=18)throw std::runtime_error("Expected base, fourteen prior extensions, Level17 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[17];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<'\n';if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=15;++i)prior.emplace_back(argv[i]);
    auto withNew=prior;withNew.emplace_back(argv[16]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,withNew);
    ck(old->lessons().size()==32&&current->lessons().size()==34&&
        old->sourceEntryCount()==120&&current->sourceEntryCount()==126,
        "two exact cases and six unique source entries counted once");
    const auto installed=lesson::Catalog::installedExtensionDirectoryNames();
    const std::vector<std::string> historical{
        "rung02-extension","rung03-extension","rung04-extension","level006-extension",
        "rung05-extension","level008-extension","level010-extension","level007-extension",
        "level009-extension","level011-extension","level013-extension","level014-extension","level015-extension","level016-extension","level017-extension"};
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
    ck(priorVariants==87,"all prior variants accounted for");
    const auto newManifest=json::parse(content::readBounded(withNew.back()/"manifest.json",1024*1024));
    const auto packet=json::parse(content::readBounded(withNew.back()/newManifest.object().at("entries").object().at("package").string(),32*1024*1024));
    const std::array<const char*,2> items{"fg:item:001160","fg:item:001161"};
    const std::array<std::array<const char*,2>,2> variants{{{{"fg:variant:007442","fg:variant:007443"}},
        {{"fg:variant:007444","fg:variant:007445"}}}};
    for(std::size_t caseIndex=0;caseIndex<2;++caseIndex){
        const auto& selectedLesson=current->lesson(items[caseIndex]);
        ck(selectedLesson.title.find(caseIndex==0?"complete 96-note rolling-four cell":"A-major to Rung02 Bb-major")!=std::string::npos,
            "exact selected Learn title and Case A complete-cell qualifier");
        for(std::size_t pick=0;pick<2;++pick){
            const auto admission=current->admit(items[caseIndex],variants[caseIndex][pick]);
            const std::size_t count=caseIndex==0?96:192;
            ck(admission->practiceAllowed()&&admission->span()==Rational{caseIndex==0?24:49}&&
                !admission->identity().object().at("whole_task_completion").boolean(),
                "exact Case A/B selected span, runtime permission and no whole-task credit");
            const auto& identity=admission->identity().object();
            ck(identity.at("bundle_sha256")==json::Value("fc741a0a849f4d0d68476e5b6c439e8bc0fa1560fbe6c9ff2595ae6356935f41")&&
                identity.at("package_sha256")==json::Value("bb30d460a3cef81b20ee5f162dfa5c0050effb05ade43dad63623a9c710176a2")&&
                identity.at("content_version")==json::Value("curriculum-v1-level017-first-two-cases-build-only.1")&&
                identity.at("source_refs")==json::parse(R"(["L17-TXT-GUIDANCE","L17-PDF-GUIDANCE","L17-TXT-RUNG01","L17-TXT-RUNG02","L17-PDF-CARDS","L17-PDF-ROUTE"])")&&
                identity.at("source_hashes").object().at("L17-TXT-GUIDANCE")==json::Value("e742548015d297941c9972ddb7cfcaeb0a66375b164864698e72d3e0b6bed511")&&
                identity.at("source_hashes").object().at("L17-PDF-CARDS")==json::Value("fc60d519a880c3d6a8a4984d99dd07030fcb56d09f1e2ea9ad951da271349d6d"),
                "exact installed version, original source and decision bundle identity");
            const auto& events=admission->model()->source().events;
            ck(events.size()==count,"exact 96/192 note count");
            for(std::size_t i=0;i<count;++i){
                const auto& event=events[i];const auto& tone=event.tones.at(0);
                                const auto expected=lesson::installedCaseOnset(Rational{1,4},i,caseIndex==1?96:0,
                    Rational{caseIndex==1?1:0});
                ck(event.kind==music::Kind::Note&&event.span.onset==expected&&
                    event.span.duration==Rational{1,4}&&event.tones.size()==1&&
                    json::Value::fromInteger(tone.string)==packet.object().at("records").array()[caseIndex].object().at("events").array()[i].object().at("string")&&
                    json::Value::fromInteger(tone.fret)==packet.object().at("records").array()[caseIndex].object().at("events").array()[i].object().at("fret")&&
                    json::Value::fromInteger(tone.midi)==packet.object().at("records").array()[caseIndex].object().at("events").array()[i].object().at("midi")&&
                    event.handDirection==(((i%2==0)==(pick==0))?"D":"U"),
                    "exact source contact, nominal onset and continuous D/U event "+std::to_string(i+1));
            }
        }
    }
    ck(lesson::validInstalledGap(192,96,1,1)&&
        lesson::installedCaseOnset(Rational{1,4},95,96,Rational{1})==Rational{95,4}&&
        lesson::installedCaseOnset(Rational{1,4},96,96,Rational{1})==Rational{25}&&
        lesson::installedCaseOnset(Rational{1,4},191,96,Rational{1})==Rational{195,4},
        "one beat only after event96, exact Bb boundary and final onset");
    ck(!lesson::validInstalledGap(192,0,1,1),"positive duration without boundary refused");
    ck(!lesson::validInstalledGap(192,96,0,1),"boundary without positive duration refused");
    ck(!lesson::validInstalledGap(192,192,1,1),"out-of-range boundary refused");
    ck(!lesson::validInstalledGap(192,96,1,0),"zero denominator refused");
    for(const auto wrongGap:{Rational{0},Rational{1,2},Rational{2}})
        ck(!(lesson::installedCaseOnset(Rational{1,4},96,96,wrongGap)==Rational{25}),
            "missing or wrong intercell pause differs from reviewed event97");
    refuses([&]{current->admit("fg:item:001160","fg:variant:007444");},"cross-case variant refused");
    refuses([&]{current->admit("fg:item:001161","fg:variant:007442");},"reverse cross-case variant refused");
    refuses([&]{lesson::Catalog::loadInstalled(base,std::vector<std::filesystem::path>{withNew.back()});},
        "out-of-order or partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level017");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing atomic Level17 bundle refused");
    const auto mutableBundle=out/"mutable-level017";
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
        if(std::string(fault)=="missing-pause")events[96].object()["onset_q"]=json::parse("[24,1]");
        else if(std::string(fault)=="short-pause")events[96].object()["onset_q"]=json::parse("[49,2]");
        else if(std::string(fault)=="long-pause")events[96].object()["onset_q"]=json::parse("[26,1]");
        else if(std::string(fault)=="shifted-pause")events[97].object()["onset_q"]=json::parse("[26,1]");
        else if(std::string(fault)=="extra-rest")events[96].object()["kind"]="rest";
        else events.pop_back();
        put(packagePath,json::stringify(packet));
        refuses([&]{lesson::Catalog::loadInstalled(base,altered);},
            std::string("changed ")+fault+" candidate refused by frozen manifest before timing guard");
        put(packagePath,originalPackage);
    }
    for(const auto* asset:{"Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_17_Major_Scale_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt",
                           "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_17_Major_Scale_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.pdf"}){
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
    ck(lesson::Catalog::loadInstalled(base,altered)->lessons().size()==34,
        "restored exact two-case bundle loads atomically");
    std::cout<<"PASS "<<checks<<" Level17 exact two-case Catalog checks\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
