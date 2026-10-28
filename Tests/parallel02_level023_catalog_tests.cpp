#include "content/LessonCatalog.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=24)throw std::runtime_error("Expected base, twenty prior extensions, Level23 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[23];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=21;++i)prior.emplace_back(argv[i]);
    auto currentPaths=prior;currentPaths.emplace_back(argv[22]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,currentPaths);
    ck(old->lessons().size()==44&&current->lessons().size()==45&&
       old->sourceEntryCount()==163&&current->sourceEntryCount()==167,
       "one case and four unique source keys added");
    const auto order=lesson::Catalog::installedExtensionDirectoryNames();
    ck(order.size()==22&&order[20]=="level023-extension"&&order.back()=="level024-extension",
       "finite Level23 extension retains its installed position");
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
    ck(priorVariants==111,"all prior variants accounted for");
    const std::string item="fg:item:001172";
    const std::array<std::string,2> variants{"fg:variant:007466","fg:variant:007467"};
    const auto& selected=current->lesson(item);
    ck(selected.title.find("isolated 36-contact")!=std::string::npos&&
       current->admit(item,variants.front())->description().find("No intercell pause")!=std::string::npos,
       "Learn names isolated cell and absence of in-cell gap");
    const auto manifest=json::parse(content::readBounded(currentPaths.back()/"manifest.json",1024*1024));
    const auto package=json::parse(content::readBounded(currentPaths.back()/
       manifest.object().at("entries").object().at("package").string(),32*1024*1024));
    for(std::size_t pick=0;pick<2;++pick){
        const auto token=current->admit(item,variants[pick]);
        ck(token->practiceAllowed()&&token->span()==Rational{12}&&
           !token->identity().object().at("whole_task_completion").boolean(),
           "exact q12 span, permission and no whole-task credit");
        const auto& identity=token->identity().object();
        ck(identity.at("bundle_sha256")==json::Value("4d0fea8ad4971ea9ef8155e63fad4b72c176ee9c2f5f1b93689f99d634adce41")&&
           identity.at("package_sha256")==json::Value("b0a362abf9701afea62ccd66201dd923cafb40d51dc5f283d45daaa799ff4e2c")&&
           identity.at("content_version")==json::Value("curriculum-v1-level023-first-rolling-cell-build-only.1")&&
           identity.at("source_refs")==json::parse(R"(["L23-TXT-RULE-1-60","L23-PDF-GUIDANCE-P1","L23-TXT-RUNG01-62-73","L23-PDF-CARD01-P3"])")&&
           identity.at("source_hashes").object().at("L23-TXT-RULE-1-60")==json::Value("c8c01c4a4ad95e1aed5323d485b359a1bd4d057f46fd2b3ffe8277324b0032f7")&&
           identity.at("source_hashes").object().at("L23-PDF-CARD01-P3")==json::Value("5601a14c406f3b33e455e96d4539ade22160ed0ac95aa782b36a2ef9d960dd43"),
           "installed identity binds exact source/version/decision bundle");
        const auto& events=token->model()->source().events;
        ck(events.size()==36,"exact 36 picked contacts");
        for(std::size_t i=0;i<36;++i){
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
        ck(events[17].tones.front().string==3&&events[17].tones.front().fret==7&&
           events[17].tones.front().midi==57&&
           events[18].tones.front().string==3&&events[18].tones.front().fret==7&&
           events[18].tones.front().midi==57&&events[17].id!=events[18].id,
           "repeated octave root is two separate attacks");
    }
    ck(lesson::installedCaseOnset(Rational{1,3},35,0,Rational{0})==Rational{35,3}&&
       lesson::validInstalledGaps(36,0,0,1,0,0,1),"zero-gap q12 cell has no tail rest");
    refuses([&]{current->admit(item,"fg:variant:007465");},"foreign variant refused");
    refuses([&]{lesson::Catalog::loadInstalled(base,{currentPaths.back()});},"partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level023");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing Level23 bundle refused");
    const auto altered=out/"altered-level023";
    std::filesystem::copy(currentPaths.back(),altered,std::filesystem::copy_options::recursive);
    auto changed=prior;changed.push_back(altered);
    const auto packagePath=altered/manifest.object().at("entries").object().at("package").string();
    const auto originalBytes=content::readBounded(packagePath,32*1024*1024);
    for(const auto* fault:{"wrong-onset","wrong-identity","missing-event"}){
        auto candidate=json::parse(originalBytes);auto& record=candidate.object().at("records").array().front().object();
        auto& events=record.at("events").array();
        if(std::string(fault)=="wrong-onset")events[18].object()["onset_q"]=json::parse("[7,1]");
        else if(std::string(fault)=="wrong-identity")record["id"]="fg:item:009950";
        else events.pop_back();
        {std::ofstream write(packagePath,std::ios::binary);write<<json::stringify(candidate);}
        refuses([&]{lesson::Catalog::loadInstalled(base,changed);},std::string("changed ")+fault+" refused");
        {std::ofstream write(packagePath,std::ios::binary);write<<originalBytes;}
    }
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks
                                     <<",\"cases\":1,\"physical_listening\":false}\n";
    std::cout<<"PASS "<<checks<<" Level23 source-backed first-cell Catalog checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
