#include "content/LessonCatalog.hpp"
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=16)throw std::runtime_error("Expected base, twelve prior extensions, Level15 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[15];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<'\n';if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=13;++i)prior.emplace_back(argv[i]);
    auto withNew=prior;withNew.emplace_back(argv[14]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,withNew);
    ck(old->lessons().size()==29&&current->lessons().size()==30&&
        old->sourceEntryCount()==110&&current->sourceEntryCount()==114,
        "one exact case and four declared source keys counted once");
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
    ck(priorVariants==81,"all prior variants accounted for");
    const auto& selectedLesson=current->lesson("fg:item:001157");
    ck(selectedLesson.title.find("complete 78-note two-octave rolling-triplet cell")!=std::string::npos,
        "exact selected Learn title and complete-cell qualifier");
    for(std::size_t pick=0;pick<2;++pick){
        const std::string variant=pick==0?"fg:variant:007436":"fg:variant:007437";
        const auto admission=current->admit("fg:item:001157",variant);
        ck(admission->practiceAllowed()&&admission->span()==Rational{26}&&
            !admission->identity().object().at("whole_task_completion").boolean(),
            "exact selected span26, runtime permission and no whole-task credit");
        const auto& identity=admission->identity().object();
        ck(identity.at("bundle_sha256")==json::Value("e132f1c3117df3515457adb53058227f1878e2032c9ea6684d301af7cb2c4ccc")&&
            identity.at("package_sha256")==json::Value("f4344f9d3b90c2714acc5e6f31a10904491a0bcb37e4174cebc866b66825c0f0")&&
            identity.at("content_version")==json::Value("curriculum-v1-level015-rung01-complete-triplet-build-only.1")&&
            identity.at("source_refs")==json::parse(R"(["L15-TXT1-60-67","L15-TXT1-70-91","L15-PDF-GUIDANCE-P1","L15-PDF-CARD-P3"])")&&
            identity.at("source_hashes").object().at("L15-TXT1-70-91")==json::Value("896937c0d5040c8e7590364433e141bbe7f6da419e063a8ed2590666d5a2c514")&&
            identity.at("source_hashes").object().at("L15-PDF-CARD-P3")==json::Value("9c3e2b980079fb3a4eca7affe9bc948a2e58cab15f256766976451ac08d53a5e"),
            "exact installed version, original source and decision bundle identity");
        const auto& events=admission->model()->source().events;
        ck(events.size()==78,"exact 78-contact single cell");
        for(std::size_t i=0;i<78;++i){
            const auto& event=events[i];
            ck(event.kind==music::Kind::Note&&
                event.span.onset==Rational{static_cast<std::int64_t>(i),3}&&
                event.span.duration==Rational{1,3}&&event.tones.size()==1&&
                event.handDirection==(((i%2==0)==(pick==0))?"D":"U"),
                "exact nominal triplet onset and unreset D/U event "+std::to_string(i+1));
        }
        ck(events[38].tones.front().midi==events[39].tones.front().midi&&
            events[38].tones.front().string==events[39].tones.front().string&&
            events[38].tones.front().fret==events[39].tones.front().fret&&
            events[38].id!=events[39].id&&events[38].handDirection!=events[39].handDirection,
            "two separate high-root attacks with opposite consecutive strokes");
    }
    refuses([&]{current->admit("fg:item:000004","fg:variant:007436");},
        "old Level15 selected illustration cannot gain new triplet variant");
    refuses([&]{current->admit("fg:item:001157","fg:variant:000033");},
        "new full cell cannot gain old illustration variant");
    refuses([&]{lesson::Catalog::loadInstalled(base,std::vector<std::filesystem::path>{withNew.back()});},
        "out-of-order or partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level015");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing atomic Level15 bundle refused");
    const auto mutableBundle=out/"mutable-level015";
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
    for(const auto* fault:{"wrong-triplet","shifted-turn","extra-rest","event-count","foreign-item"}){
        auto packet=json::parse(originalPackage);
        auto& record=packet.object().at("records").array()[0];
        auto& events=record.object().at("events").array();
        if(std::string(fault)=="wrong-triplet")events[39].object()["onset_q"]=json::parse("[40,3]");
        else if(std::string(fault)=="shifted-turn")events[38].object()["onset_q"]=json::parse("[13,1]");
        else if(std::string(fault)=="extra-rest")events[39].object()["kind"]="rest";
        else if(std::string(fault)=="foreign-item")record.object()["id"]="fg:item:000004";
        else events.pop_back();
        put(packagePath,json::stringify(packet));
        refuses([&]{lesson::Catalog::loadInstalled(base,altered);},
            std::string("changed ")+fault+" candidate refused by frozen manifest before grid guard");
        put(packagePath,originalPackage);
    }
    for(const auto* asset:{"Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_15_Major_Scale_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt",
                           "Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_15_Major_Scale_Three_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.pdf"}){
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
    ck(lesson::Catalog::loadInstalled(base,altered)->lessons().size()==30,
        "restored exact one-case bundle loads atomically");
    std::cout<<"PASS "<<checks<<" Level15 exact one-case Catalog checks\n";
    return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
