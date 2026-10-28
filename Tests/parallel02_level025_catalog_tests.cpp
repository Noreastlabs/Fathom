#include "content/LessonCatalog.hpp"
#include "content/Level025Extension.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>
using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc==3&&std::string(argv[1])=="--direct-level025"){
        const std::filesystem::path root=argv[2];
        const auto manifest=json::parse(content::readBounded(root/"manifest.json",1024*1024));
        const auto& entries=manifest.object().at("entries").object();
        auto read=[&](const char* key){return content::readBounded(root/entries.at(key).string(),32*1024*1024);};
        const auto package=read("package"),registry=read("registry"),profile=read("profile"),
                   decision=read("decision"),provenance=read("provenance");
        auto validate=[&](const std::string& candidate,const std::string& disposition,
                          const std::string& sidecar){
            return lesson::validateLevel025Extension({candidate,registry,profile,
                manifest.object().at("profile_sha256").string(),root},disposition,
                manifest.object().at("decision_sha256").string(),sidecar);
        };
        auto ck=[&](bool ok,const char* name){++checks;if(!ok)throw std::runtime_error(name);};
        auto refusal=[&](const std::string& candidate,const std::string& disposition,
                         const std::string& sidecar,const char* name){
            bool denied=false;try{validate(candidate,disposition,sidecar);}catch(const std::exception&){denied=true;}
            ck(denied,name);
        };
        const auto result=validate(package,decision,provenance);
        ck(result.validReference&&result.exitCode==2&&result.records.size()==1&&result.variants.size()==2,
           "exact Level25 nonadmitted reference");
        for(const auto& variant:result.variants){
            ck(variant.source.events.size()==40&&variant.validation.validReference(),
               "forty validated Level25 contacts");
            ck(variant.source.events[19].id!=variant.source.events[20].id&&
               variant.source.events[19].tones.front().midi==57&&
               variant.source.events[20].tones.front().midi==57,
               "two separate D-string turn attacks");
        }
        auto altered=json::parse(package);
        altered.object().at("records").array().front().object().at("events").array()[20].object()["onset_q"]=json::parse("[6,1]");
        refusal(json::stringify(altered),decision,provenance,"changed onset refused");
        altered=json::parse(package);
        altered.object().at("records").array().front().object()["id"]="fg:item:009950";
        refusal(json::stringify(altered),decision,provenance,"foreign item refused");
        altered=json::parse(package);
        altered.object().at("records").array().front().object().at("events").array().pop_back();
        refusal(json::stringify(altered),decision,provenance,"missing contact refused");
        altered=json::parse(decision);altered.object()["status"]="PENDING";
        refusal(package,json::stringify(altered),provenance,"wrong decision refused");
        altered=json::parse(provenance);altered.object().at("variant_strokes").object().at("fg:variant:007474").array()[20]="U";
        refusal(package,decision,json::stringify(altered),"wrong pick provenance refused");
        std::cout<<"PASS "<<checks<<" direct Level25 validation/refusal checks\n";return 0;
    }
    if(argc!=28)throw std::runtime_error("Expected base, twenty-four prior extensions, Level25 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[27];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=25;++i)prior.emplace_back(argv[i]);
    auto currentPaths=prior;currentPaths.emplace_back(argv[26]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,currentPaths);
    ck(old->lessons().size()==48&&current->lessons().size()==49&&
       old->sourceEntryCount()==181&&current->sourceEntryCount()==185,
       "one case and four unique source keys added");
    const auto order=lesson::Catalog::installedExtensionDirectoryNames();
    ck(order.size()==25&&order.back()=="level025-extension","finite Level25 extension installed last");
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
    ck(priorVariants==119,"all prior variants accounted for");
    const std::string item="fg:item:001176";
    const std::array<std::string,2> variants{"fg:variant:007474","fg:variant:007475"};
    const auto& selected=current->lesson(item);
    ck(selected.title.find("40-contact rolling")!=std::string::npos&&
       current->admit(item,variants.front())->description().find("No shift pause")!=std::string::npos,
       "Learn names isolated cell and absence of in-cell gap");
    const auto manifest=json::parse(content::readBounded(currentPaths.back()/"manifest.json",1024*1024));
    const auto package=json::parse(content::readBounded(currentPaths.back()/
       manifest.object().at("entries").object().at("package").string(),32*1024*1024));
    for(std::size_t pick=0;pick<2;++pick){
        const auto token=current->admit(item,variants[pick]);
        ck(token->practiceAllowed()&&token->span()==Rational{10}&&
           !token->identity().object().at("whole_task_completion").boolean(),
           "exact q10 span, permission and no whole-task credit");
        const auto& identity=token->identity().object();
        ck(identity.at("bundle_sha256")==json::Value("1d04798658aec24e1bafe698e27a7eaec54f1714cd58ae02ce5efd6f057a5705")&&
           identity.at("package_sha256")==json::Value("9a9eff3df43f2ccf725a0dd9ab93b11323e42f66dfb53f484b314f0bc58e5948")&&
           identity.at("content_version")==json::Value("curriculum-v1-level025-first-cell-build-only.1")&&
           identity.at("source_refs")==json::parse(R"(["L25-TXT-RULE-1-64","L25-TXT-RUNG01-67-78","L25-PDF-WORKED-P1","L25-PDF-CARD01-P3"])")&&
           identity.at("source_hashes").object().at("L25-TXT-RULE-1-64")==json::Value("707c3edbfe942f703e94a7a7bd067215124e7ac4e5eb008c891e7c62102c30bb")&&
           identity.at("source_hashes").object().at("L25-PDF-CARD01-P3")==json::Value("7b0f5f718c79123a0515637dcbe01b6c3224ea1047e985f9e369a8618521aede"),
           "installed identity binds exact source/version/decision bundle");
        const auto& events=token->model()->source().events;
        ck(events.size()==40,"exact 40 picked contacts");
        for(std::size_t i=0;i<40;++i){
            const auto& event=events[i];const auto& tone=event.tones.at(0);
            const auto& authored=package.object().at("records").array().front().object().at("events").array()[i].object();
            ck(event.kind==music::Kind::Note&&event.span.onset==Rational{static_cast<std::int64_t>(i),4}&&
               event.span.duration==Rational{1,4}&&event.tones.size()==1&&
               json::Value::fromInteger(tone.string)==authored.at("string")&&
               json::Value::fromInteger(tone.fret)==authored.at("fret")&&
               json::Value::fromInteger(tone.midi)==authored.at("midi")&&
               event.handDirection==(((i%2==0)==(pick==0))?"D":"U"),
               "exact original contact, q1/4 timing and continuous picking "+std::to_string(i+1));
        }
        ck(events[19].tones.front().string==3&&events[19].tones.front().fret==7&&
           events[19].tones.front().midi==57&&
           events[20].tones.front().string==3&&events[20].tones.front().fret==7&&
           events[20].tones.front().midi==57&&events[19].id!=events[20].id,
           "repeated D-string octave root is two separate attacks");
    }
    ck(lesson::installedCaseOnset(Rational{1,4},39,0,Rational{0})==Rational{39,4}&&
       lesson::validInstalledGaps(40,0,0,1,0,0,1),"zero-gap q10 cell has no tail rest");
    refuses([&]{current->admit(item,"fg:variant:007473");},"foreign variant refused");
    refuses([&]{lesson::Catalog::loadInstalled(base,{currentPaths.back()});},"partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level025");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing Level25 bundle refused");
    const auto altered=out/"altered-level025";
    std::filesystem::copy(currentPaths.back(),altered,std::filesystem::copy_options::recursive);
    auto changed=prior;changed.push_back(altered);
    const auto packagePath=altered/manifest.object().at("entries").object().at("package").string();
    const auto originalBytes=content::readBounded(packagePath,32*1024*1024);
    for(const auto* fault:{"wrong-onset","wrong-identity","missing-event"}){
        auto candidate=json::parse(originalBytes);auto& record=candidate.object().at("records").array().front().object();
        auto& events=record.at("events").array();
        if(std::string(fault)=="wrong-onset")events[20].object()["onset_q"]=json::parse("[6,1]");
        else if(std::string(fault)=="wrong-identity")record["id"]="fg:item:009950";
        else events.pop_back();
        {std::ofstream write(packagePath,std::ios::binary);write<<json::stringify(candidate);}
        refuses([&]{lesson::Catalog::loadInstalled(base,changed);},std::string("changed ")+fault+" refused");
        {std::ofstream write(packagePath,std::ios::binary);write<<originalBytes;}
    }
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks
                                     <<",\"cases\":1,\"physical_listening\":false}\n";
    std::cout<<"PASS "<<checks<<" Level25 source-backed first-cell Catalog checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
