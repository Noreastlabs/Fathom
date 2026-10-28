#include "content/LessonCatalog.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=27)throw std::runtime_error("Expected base, twenty-three prior extensions, Level29 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[26];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=24;++i)prior.emplace_back(argv[i]);
    auto currentPaths=prior;currentPaths.emplace_back(argv[25]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,currentPaths);
    ck(old->lessons().size()==47&&current->lessons().size()==48&&
       old->sourceEntryCount()==177&&current->sourceEntryCount()==181,
       "one case and four unique source keys added");
    const auto order=lesson::Catalog::installedExtensionDirectoryNames();
    ck(order.size()==24&&order.back()=="level029-extension","finite Level29 extension installed last");
    std::size_t priorVariants=0;
    for(const auto& selected:old->lessons()){
        const auto& now=current->lesson(selected.id);
        ck(now.title==selected.title&&now.variants.size()==selected.variants.size()&&
           current->contentVersion(selected.id)==old->contentVersion(selected.id),
           "prior title, variants and version preserved "+selected.id);
        for(const auto& variant:selected.variants){++priorVariants;
            ck(variant.authored==current->variant(selected.id,variant.id).authored,
               "prior authored variant preserved "+variant.id);
            try{const auto a=old->admit(selected.id,variant.id),b=current->admit(selected.id,variant.id);
                ck(a->identity()==b->identity()&&a->sourceBinding()==b->sourceBinding()&&a->span()==b->span(),
                   "prior admission preserved "+variant.id);
            }catch(const std::exception&){refuses([&]{current->admit(selected.id,variant.id);},
                                                "prior refusal preserved "+variant.id);}
        }
    }
    ck(priorVariants==117,"all prior variants accounted for");
    const std::string item="fg:item:001175";
    const std::array<std::string,2> variants{"fg:variant:007472","fg:variant:007473"};
    const auto& selected=current->lesson(item);
    ck(selected.title.find("30 eighth-note")!=std::string::npos&&
       current->admit(item,variants.front())->description().find("No terminal rest")!=std::string::npos,
       "Learn names isolated cell and absence of in-cell gap");
    const auto manifest=json::parse(content::readBounded(currentPaths.back()/"manifest.json",1024*1024));
    const auto package=json::parse(content::readBounded(currentPaths.back()/
       manifest.object().at("entries").object().at("package").string(),32*1024*1024));
    for(std::size_t pick=0;pick<2;++pick){
        const auto token=current->admit(item,variants[pick]);
        ck(token->practiceAllowed()&&token->span()==Rational{15}&&
           !token->identity().object().at("whole_task_completion").boolean(),
           "exact q15 span, permission and no whole-task credit");
        const auto& identity=token->identity().object();
        ck(identity.at("bundle_sha256")==json::Value("e20e9f4a834e80257952e08d62a5befdd2ab96d76943495f2cb29148fc0c34f7")&&
           identity.at("package_sha256")==json::Value("e0773097a98923f139854769d8e97dbe70c5764bb84abd0eca98b1bc291dfdbc")&&
           identity.at("content_version")==json::Value("curriculum-v1-level029-module1-first30-build-only.1")&&
           identity.at("source_refs")==json::parse(R"(["L29-TXT-RULES-1-46","L29-TXT-RUNG01-80-95","L29-PDF-PULSE-P2","L29-PDF-CARD-P3"])")&&
           identity.at("source_hashes").object().at("L29-TXT-RULES-1-46")==json::Value("543d98fa9279f39d8975d6b00cd43e5f5aebbb94c5e59fe7771f63af8d8244e5")&&
           identity.at("source_hashes").object().at("L29-PDF-CARD-P3")==json::Value("2310fc942262081445d80d164ae6feab6335a879db283863db27f69bb75ef445"),
           "installed identity binds exact source/version/decision bundle");
        const auto& events=token->model()->source().events;
        ck(events.size()==30,"exact 30 picked contacts");
        for(std::size_t i=0;i<30;++i){
            const auto& event=events[i];const auto& tone=event.tones.at(0);
            const auto& authored=package.object().at("records").array().front().object().at("events").array()[i].object();
            ck(event.kind==music::Kind::Note&&event.span.onset==Rational{static_cast<std::int64_t>(i),2}&&
               event.span.duration==Rational{1,2}&&event.tones.size()==1&&
               json::Value::fromInteger(tone.string)==authored.at("string")&&
               json::Value::fromInteger(tone.fret)==authored.at("fret")&&
               json::Value::fromInteger(tone.midi)==authored.at("midi")&&
               event.handDirection==(((i%2==0)==(pick==0))?"D":"U"),
               "exact original contact, q1/2 timing and continuous picking "+std::to_string(i+1));
        }
        ck(events[14].tones.front().string==6&&events[14].tones.front().fret==5&&
           events[14].tones.front().midi==69&&
           events[15].tones.front().string==6&&events[15].tones.front().fret==5&&
           events[15].tones.front().midi==69&&events[14].id!=events[15].id,
           "repeated high-e root is two separate attacks");
    }
    ck(lesson::installedCaseOnset(Rational{1,2},29,0,Rational{0})==Rational{29,2}&&
       lesson::validInstalledGaps(30,0,0,1,0,0,1),"zero-gap q15 cell has no tail rest");
    refuses([&]{current->admit(item,"fg:variant:007471");},"foreign variant refused");
    refuses([&]{lesson::Catalog::loadInstalled(base,{currentPaths.back()});},"partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level029");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing Level29 bundle refused");
    const auto altered=out/"altered-level029";
    std::filesystem::copy(currentPaths.back(),altered,std::filesystem::copy_options::recursive);
    auto changed=prior;changed.push_back(altered);
    const auto packagePath=altered/manifest.object().at("entries").object().at("package").string();
    const auto originalBytes=content::readBounded(packagePath,32*1024*1024);
    for(const auto* fault:{"wrong-onset","wrong-identity","missing-event"}){
        auto candidate=json::parse(originalBytes);auto& record=candidate.object().at("records").array().front().object();
        auto& events=record.at("events").array();
        if(std::string(fault)=="wrong-onset")events[15].object()["onset_q"]=json::parse("[8,1]");
        else if(std::string(fault)=="wrong-identity")record["id"]="fg:item:009950";
        else events.pop_back();
        {std::ofstream write(packagePath,std::ios::binary);write<<json::stringify(candidate);}
        refuses([&]{lesson::Catalog::loadInstalled(base,changed);},std::string("changed ")+fault+" refused");
        {std::ofstream write(packagePath,std::ios::binary);write<<originalBytes;}
    }
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks
                                     <<",\"cases\":1,\"physical_listening\":false}\n";
    std::cout<<"PASS "<<checks<<" Level29 source-backed first-module Catalog checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
