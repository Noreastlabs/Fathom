#include "content/LessonCatalog.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=22)throw std::runtime_error("Expected base, eighteen prior extensions, Level21 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[21];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<'\n';if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=19;++i)prior.emplace_back(argv[i]);
    auto withNew=prior;withNew.emplace_back(argv[20]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,withNew);
    ck(old->lessons().size()==40&&current->lessons().size()==43&&
       old->sourceEntryCount()==150&&current->sourceEntryCount()==157,
       "three exact cases and seven unique source entries counted once");
    const auto installedOrder=lesson::Catalog::installedExtensionDirectoryNames();
    ck(installedOrder.size()>=19 &&
       std::vector<std::string>(installedOrder.begin(),installedOrder.begin()+19)==std::vector<std::string>{
        "rung02-extension","rung03-extension","rung04-extension","level006-extension",
        "rung05-extension","level008-extension","level010-extension","level007-extension",
        "level009-extension","level011-extension","level013-extension","level014-extension",
        "level015-extension","level016-extension","level017-extension","level018-extension",
        "level019-extension","level020-extension","level021-extension"},"exact historical installed extension prefix");
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
                   a->span()==b->span(),"prior zero/one-gap runtime admission unchanged "+variant.id);
            }catch(const std::exception&){
                refuses([&]{current->admit(lesson.id,variant.id);},"prior refusal retained "+variant.id);
            }
        }
    }
    ck(priorVariants==103,"all one hundred three prior variants accounted for");
    const auto manifest=json::parse(content::readBounded(withNew.back()/"manifest.json",1024*1024));
    const auto packet=json::parse(content::readBounded(withNew.back()/manifest.object().at("entries").object().at("package").string(),32*1024*1024));
    const std::array<const char*,3> items{"fg:item:001168","fg:item:001169","fg:item:001170"};
    const std::array<std::array<const char*,2>,3> variants{{{{"fg:variant:007458","fg:variant:007459"}},
        {{"fg:variant:007460","fg:variant:007461"}},{{"fg:variant:007462","fg:variant:007463"}}}};
    const std::array<std::size_t,3> counts{16,32,48};
    const std::array<int,3> spans{8,17,26};
    for(std::size_t ci=0;ci<3;++ci){
        const auto& selected=current->lesson(items[ci]);
        ck(selected.title.find(ci==0?"16-contact":ci==1?"32-contact":"48-contact")!=std::string::npos,
            "exact selected Learn title and source case extent");
        for(std::size_t pick=0;pick<2;++pick){
            const auto token=current->admit(items[ci],variants[ci][pick]);
            ck(token->practiceAllowed()&&token->span()==Rational{spans[ci]}&&
               !token->identity().object().at("whole_task_completion").boolean(),
               "exact selected span, runtime permission and no whole-task credit");
            const auto& identity=token->identity().object();
            ck(identity.at("bundle_sha256")==json::Value("a728e8dc4665edcaa0097cd608457aa4da9a7d20784fe289d5e177582867572f")&&
               identity.at("package_sha256")==json::Value("6a9d7d2e8c642e60fa432fcf2dd8aa12bdafb4d583fbbfb431eeb7441ee68fe8")&&
               identity.at("content_version")==json::Value("curriculum-v1-level021-first-three-cases-build-only.1")&&
               identity.at("source_refs")==json::parse(R"(["L21-TXT-GUIDANCE","L21-PDF-GUIDANCE","L21-TXT-RUNG01","L21-TXT-RUNG02","L21-TXT-RUNG03","L21-PDF-CARDS01-03","L21-PDF-ROUTE"])")&&
               identity.at("source_hashes").object().at("L21-TXT-GUIDANCE")==json::Value("018db1d53df6b1b175c64d59f95809b3215d055f2c3361c90199ee8f3d75bf67")&&
               identity.at("source_hashes").object().at("L21-PDF-ROUTE")==json::Value("b8679699687ef8078f958563ce8f887e8e1083c486ef52d816a09c434d57d235"),
               "exact installed version, original source and decision bundle identity");
            const auto& events=token->model()->source().events;
            ck(events.size()==counts[ci],"exact 16/32/48 picked event count");
            for(std::size_t i=0;i<counts[ci];++i){
                const auto& e=events[i];const auto& tone=e.tones.at(0);
                const auto expected=lesson::installedCaseOnset(Rational{1,2},i,
                    ci>=1?16:0,Rational{ci>=1?1:0},ci==2?32:0,Rational{ci==2?1:0});
                const auto& original=packet.object().at("records").array()[ci].object().at("events").array()[i].object();
                ck(e.kind==music::Kind::Note&&e.span.onset==expected&&e.span.duration==Rational{1,2}&&
                   e.tones.size()==1&&json::Value::fromInteger(tone.string)==original.at("string")&&
                   json::Value::fromInteger(tone.fret)==original.at("fret")&&
                   json::Value::fromInteger(tone.midi)==original.at("midi")&&
                   e.handDirection==(((i%2==0)==(pick==0))?"D":"U"),
                   "exact source contact, two-gap onset and continuous D/U event "+std::to_string(i+1));
            }
        }
    }
    ck(lesson::installedCaseOnset(Rational{1,2},15,16,Rational{1},32,Rational{1})==Rational{15,2}&&
       lesson::installedCaseOnset(Rational{1,2},16,16,Rational{1},32,Rational{1})==Rational{9}&&
       lesson::installedCaseOnset(Rational{1,2},31,16,Rational{1},32,Rational{1})==Rational{33,2}&&
       lesson::installedCaseOnset(Rational{1,2},32,16,Rational{1},32,Rational{1})==Rational{18}&&
       lesson::installedCaseOnset(Rational{1,2},47,16,Rational{1},32,Rational{1})==Rational{51,2},
       "exact q8/q9/q17/q18/q26 seams and no tail rest");
    ck(lesson::validInstalledGaps(48,16,1,1,32,1,1)&&
       lesson::validInstalledGaps(32,16,1,1,0,0,1)&&
       lesson::validInstalledGaps(16,0,0,1,0,0,1),"zero, one and two gaps structurally valid");
    for(const auto& bad:std::array<std::array<std::int64_t,6>,12>{{
        {{0,0,1,32,1,1}},{{16,1,1,0,1,1}},{{16,1,1,0,0,0}},
        {{16,1,1,16,1,1}},{{32,1,1,16,1,1}},{{16,1,1,48,1,1}},
        {{16,1,1,32,0,1}},{{16,1,1,32,1,0}},{{16,1,1,32,-1,1}},
        {{0,1,1,0,0,1}},{{16,0,1,32,1,1}},{{16,1,0,32,1,1}}}})
        ck(!lesson::validInstalledGaps(48,static_cast<std::size_t>(bad[0]),bad[1],bad[2],
            static_cast<std::size_t>(bad[3]),bad[4],bad[5]),"malformed, unordered or out-of-range two-gap permission refused");
    for(const auto wrong:std::array<Rational,3>{Rational{0},Rational{1,2},Rational{2}})
        ck(!(lesson::installedCaseOnset(Rational{1,2},32,16,Rational{1},32,wrong)==Rational{18}),
            "missing/short/long second pause differs from reviewed B event33");
    refuses([&]{current->admit(items[0],variants[2][0]);},"foreign triple-case variant refused");
    refuses([&]{current->admit(items[2],variants[0][0]);},"reverse foreign variant refused");
    refuses([&]{lesson::Catalog::loadInstalled(base,std::vector<std::filesystem::path>{withNew.back()});},
            "out-of-order or partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level021");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing atomic Level21 bundle refused");
    const auto altered=out/"mutable-level021";
    std::filesystem::copy(withNew.back(),altered,std::filesystem::copy_options::recursive);
    auto changed=prior;changed.push_back(altered);
    const auto packagePath=altered/manifest.object().at("entries").object().at("package").string();
    const auto originalBytes=content::readBounded(packagePath,32*1024*1024);
    for(const auto* fault:{"missing-A-rest","missing-B-rest","short-B-rest","extra-rest","event-count"}){
        auto candidate=json::parse(originalBytes);auto& ev=candidate.object().at("records").array()[2].object().at("events").array();
        if(std::string(fault)=="missing-A-rest")ev[16].object()["onset_q"]=json::parse("[8,1]");
        else if(std::string(fault)=="missing-B-rest")ev[32].object()["onset_q"]=json::parse("[17,1]");
        else if(std::string(fault)=="short-B-rest")ev[32].object()["onset_q"]=json::parse("[35,2]");
        else if(std::string(fault)=="extra-rest")ev[32].object()["kind"]="rest";
        else ev.pop_back();
        {std::ofstream write(packagePath,std::ios::binary);write<<json::stringify(candidate);}
        refuses([&]{lesson::Catalog::loadInstalled(base,changed);},
            std::string("changed ")+fault+" refused by frozen manifest before timing guard");
        {std::ofstream write(packagePath,std::ios::binary);write<<originalBytes;}
    }
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"cases\":3,\"attempts\":0,\"physical_listening\":false}\n";
    std::cout<<"PASS "<<checks<<" Level21 three-case source-backed Catalog/two-gap checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
