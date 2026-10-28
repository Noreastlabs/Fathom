#include "content/LessonCatalog.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=25)throw std::runtime_error("Expected base, twenty-one prior extensions, Level24 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[24];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=22;++i)prior.emplace_back(argv[i]);
    auto currentPaths=prior;currentPaths.emplace_back(argv[23]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,currentPaths);
    ck(old->lessons().size()==45&&current->lessons().size()==46&&
       old->sourceEntryCount()==167&&current->sourceEntryCount()==172,
       "one case and five unique source keys added");
    const auto order=lesson::Catalog::installedExtensionDirectoryNames();
    ck(order.size()==23&&order.at(21)=="level024-extension"&&order.back()=="level030-extension","finite Level24 extension installed last");
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
    ck(priorVariants==113,"all prior variants accounted for");
    const std::string item="fg:item:001173";
    const std::array<std::string,2> variants{"fg:variant:007468","fg:variant:007469"};
    const auto& selected=current->lesson(item);
    ck(selected.title.find("first linked 78-contact")!=std::string::npos&&
       current->admit(item,variants.front())->description().find("No intercell pause")!=std::string::npos,
       "Learn names isolated cell and absence of in-cell gap");
    const auto manifest=json::parse(content::readBounded(currentPaths.back()/"manifest.json",1024*1024));
    const auto package=json::parse(content::readBounded(currentPaths.back()/
       manifest.object().at("entries").object().at("package").string(),32*1024*1024));
    for(std::size_t pick=0;pick<2;++pick){
        const auto token=current->admit(item,variants[pick]);
        ck(token->practiceAllowed()&&token->span()==Rational{26}&&
           !token->identity().object().at("whole_task_completion").boolean(),
           "exact q26 span, permission and no whole-task credit");
        const auto& identity=token->identity().object();
        ck(identity.at("bundle_sha256")==json::Value("af0d6891254eb23b1e7fcd45dfb236e3f3a7b1982b96cb80bddad8891b110145")&&
           identity.at("package_sha256")==json::Value("ac54e5b11111ffa7dd2109fd93de9c93b2d6e2082929325acecc1e7a3c777e53")&&
           identity.at("content_version")==json::Value("curriculum-v1-level024-first-linked-cell-build-only.1")&&
           identity.at("source_refs")==json::parse(R"(["L24-TXT-RULE-1-70","L24-TXT-RUNG01-73-94","L24-PDF-TUNING-P2","L24-PDF-CARD01-P3","L24-PDF-PHASES-P10"])")&&
           identity.at("source_hashes").object().at("L24-TXT-RULE-1-70")==json::Value("2a91403130355b916d2d935a2df197cbe54a03d1d17cb32575ad6df73bee9988")&&
           identity.at("source_hashes").object().at("L24-PDF-CARD01-P3")==json::Value("6f447ad03a5a0b21cee9ea20ab2cb561e9fb25f5cd7c6a5e8a5121b7657697ad"),
           "installed identity binds exact source/version/decision bundle");
        const auto& events=token->model()->source().events;
        ck(events.size()==78,"exact 78 picked contacts");
        for(std::size_t i=0;i<78;++i){
            const auto& event=events[i];const auto& tone=event.tones.at(0);
            const auto& authored=package.object().at("records").array().front().object().at("events").array()[i].object();
            ck(event.kind==music::Kind::Note&&event.span.onset==Rational{static_cast<std::int64_t>(i),3}&&
               event.span.duration==Rational{1,3}&&event.tones.size()==1&&
               json::Value::fromInteger(tone.string)==authored.at("string")&&
               json::Value::fromInteger(tone.fret)==authored.at("fret")&&
               json::Value::fromInteger(tone.midi)==authored.at("midi")&&
               event.handDirection==(((i%2==0)==(pick==0))?"D":"U"),
               "exact original contact, q1/3 timing and continuous picking "+std::to_string(i+1));
        }
        ck(events[38].tones.front().string==6&&events[38].tones.front().fret==5&&
           events[38].tones.front().midi==69&&
           events[39].tones.front().string==6&&events[39].tones.front().fret==5&&
           events[39].tones.front().midi==69&&events[38].id!=events[39].id,
           "repeated high-e octave root is two separate attacks");
    }
    ck(lesson::installedCaseOnset(Rational{1,3},77,0,Rational{0})==Rational{77,3}&&
       lesson::validInstalledGaps(78,0,0,1,0,0,1),"zero-gap q26 cell has no tail rest");
    refuses([&]{current->admit(item,"fg:variant:007467");},"foreign variant refused");
    refuses([&]{lesson::Catalog::loadInstalled(base,{currentPaths.back()});},"partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level024");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing Level24 bundle refused");
    const auto altered=out/"altered-level024";
    std::filesystem::copy(currentPaths.back(),altered,std::filesystem::copy_options::recursive);
    auto changed=prior;changed.push_back(altered);
    const auto packagePath=altered/manifest.object().at("entries").object().at("package").string();
    const auto originalBytes=content::readBounded(packagePath,32*1024*1024);
    for(const auto* fault:{"wrong-onset","wrong-identity","missing-event"}){
        auto candidate=json::parse(originalBytes);auto& record=candidate.object().at("records").array().front().object();
        auto& events=record.at("events").array();
        if(std::string(fault)=="wrong-onset")events[39].object()["onset_q"]=json::parse("[7,1]");
        else if(std::string(fault)=="wrong-identity")record["id"]="fg:item:009950";
        else events.pop_back();
        {std::ofstream write(packagePath,std::ios::binary);write<<json::stringify(candidate);}
        refuses([&]{lesson::Catalog::loadInstalled(base,changed);},std::string("changed ")+fault+" refused");
        {std::ofstream write(packagePath,std::ios::binary);write<<originalBytes;}
    }
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks
                                     <<",\"cases\":1,\"physical_listening\":false}\n";
    std::cout<<"PASS "<<checks<<" Level24 source-backed first-cell Catalog checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
