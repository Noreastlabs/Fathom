#include "content/LessonCatalog.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=26)throw std::runtime_error("Expected base, twenty-two prior extensions, Level30 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[25];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=23;++i)prior.emplace_back(argv[i]);
    auto currentPaths=prior;currentPaths.emplace_back(argv[24]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,currentPaths);
    ck(old->lessons().size()==46&&current->lessons().size()==47&&
       old->sourceEntryCount()==172&&current->sourceEntryCount()==177,
       "one case and five unique source keys added");
    const auto order=lesson::Catalog::installedExtensionDirectoryNames();
    ck(order.size()==24&&order[22]=="level030-extension"&&order.back()=="level029-extension",
       "finite Level30 extension preserved before Level29");
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
    ck(priorVariants==115,"all prior variants accounted for");
    const std::string item="fg:item:001174";
    const std::array<std::string,2> variants{"fg:variant:007470","fg:variant:007471"};
    const auto& selected=current->lesson(item);
    ck(selected.title.find("12-note")!=std::string::npos&&
       current->admit(item,variants.front())->description().find("No neighboring-cell pause")!=std::string::npos,
       "Learn names isolated cell and absence of in-cell gap");
    const auto manifest=json::parse(content::readBounded(currentPaths.back()/"manifest.json",1024*1024));
    const auto package=json::parse(content::readBounded(currentPaths.back()/
       manifest.object().at("entries").object().at("package").string(),32*1024*1024));
    for(std::size_t pick=0;pick<2;++pick){
        const auto token=current->admit(item,variants[pick]);
        ck(token->practiceAllowed()&&token->span()==Rational{6}&&
           !token->identity().object().at("whole_task_completion").boolean(),
           "exact q6 span, permission and no whole-task credit");
        const auto& identity=token->identity().object();
        ck(identity.at("bundle_sha256")==json::Value("d43ea87a1e1663b42b38a9078d26e3c241b55c9924c5e1ef11efb72a0e7254e4")&&
           identity.at("package_sha256")==json::Value("bed49ebd54ea0192d36970ed24673950e147369c2550ee8ea3c00c29fd024a2b")&&
           identity.at("content_version")==json::Value("curriculum-v1-level030-first12-build-only.1")&&
           identity.at("source_refs")==json::parse(R"(["L30-TXT-RULE-14-30","L30-TXT-PRACTICE-40-46","L30-TXT-RUNG01-49-60","L30-PDF-P1","L30-PDF-P2"])")&&
           identity.at("source_hashes").object().at("L30-TXT-RULE-14-30")==json::Value("98e748f4dc9626eb2e4ad63888e503ae5599ea88c01494ebb231d4baa30fc9c9")&&
           identity.at("source_hashes").object().at("L30-PDF-P1")==json::Value("40a0ccb47e7fd9ec4c3f47653a309e05921505fdacabbe7646f19a2b687c8c7b"),
           "installed identity binds exact source/version/decision bundle");
        const auto& events=token->model()->source().events;
        ck(events.size()==12,"exact 12 picked contacts");
        for(std::size_t i=0;i<12;++i){
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
        ck(events[5].tones.front().string==3&&events[5].tones.front().fret==7&&
           events[5].tones.front().midi==57&&
           events[6].tones.front().string==3&&events[6].tones.front().fret==7&&
           events[6].tones.front().midi==57&&events[5].id!=events[6].id,
           "repeated D-string high root is two separate attacks");
    }
    ck(lesson::installedCaseOnset(Rational{1,2},11,0,Rational{0})==Rational{11,2}&&
       lesson::validInstalledGaps(12,0,0,1,0,0,1),"zero-gap q6 cell has no tail rest");
    refuses([&]{current->admit(item,"fg:variant:007469");},"foreign variant refused");
    refuses([&]{lesson::Catalog::loadInstalled(base,{currentPaths.back()});},"partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level030");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing Level30 bundle refused");
    const auto altered=out/"altered-level030";
    std::filesystem::copy(currentPaths.back(),altered,std::filesystem::copy_options::recursive);
    auto changed=prior;changed.push_back(altered);
    const auto packagePath=altered/manifest.object().at("entries").object().at("package").string();
    const auto originalBytes=content::readBounded(packagePath,32*1024*1024);
    for(const auto* fault:{"wrong-onset","wrong-identity","missing-event"}){
        auto candidate=json::parse(originalBytes);auto& record=candidate.object().at("records").array().front().object();
        auto& events=record.at("events").array();
        if(std::string(fault)=="wrong-onset")events[6].object()["onset_q"]=json::parse("[7,1]");
        else if(std::string(fault)=="wrong-identity")record["id"]="fg:item:009950";
        else events.pop_back();
        {std::ofstream write(packagePath,std::ios::binary);write<<json::stringify(candidate);}
        refuses([&]{lesson::Catalog::loadInstalled(base,changed);},std::string("changed ")+fault+" refused");
        {std::ofstream write(packagePath,std::ios::binary);write<<originalBytes;}
    }
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks
                                     <<",\"cases\":1,\"physical_listening\":false}\n";
    std::cout<<"PASS "<<checks<<" Level30 source-backed first-cell Catalog checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
