#include "content/LessonCatalog.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=20)throw std::runtime_error("Expected base, sixteen prior extensions, Level19 and fresh output");
    const std::filesystem::path base=argv[1],out=argv[19];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute output required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& name){++checks;trace<<name<<'\t'<<(ok?"PASS":"FAIL")<<'\n';if(!ok)throw std::runtime_error(name);};
    auto refuses=[&](auto action,const std::string& name){bool denied=false;try{action();}catch(const std::exception&){denied=true;}ck(denied,name);};
    std::vector<std::filesystem::path> prior;for(int i=2;i<=17;++i)prior.emplace_back(argv[i]);
    auto withNew=prior;withNew.emplace_back(argv[18]);
    const auto old=lesson::Catalog::loadInstalled(base,prior);
    const auto current=lesson::Catalog::loadInstalled(base,withNew);
    ck(old->lessons().size()==36&&current->lessons().size()==39&&
       old->sourceEntryCount()==132&&current->sourceEntryCount()==140,
       "three exact cases and eight unique source entries counted once");
    const auto installedOrder=lesson::Catalog::installedExtensionDirectoryNames();
    ck(installedOrder.size()>=17 &&
       std::vector<std::string>(installedOrder.begin(),installedOrder.begin()+17)==std::vector<std::string>{
        "rung02-extension","rung03-extension","rung04-extension","level006-extension",
        "rung05-extension","level008-extension","level010-extension","level007-extension",
        "level009-extension","level011-extension","level013-extension","level014-extension",
        "level015-extension","level016-extension","level017-extension","level018-extension",
        "level019-extension"},"exact historical installed extension prefix");
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
    ck(priorVariants==95,"all ninety-five prior variants accounted for");
    const auto manifest=json::parse(content::readBounded(withNew.back()/"manifest.json",1024*1024));
    const auto packet=json::parse(content::readBounded(withNew.back()/manifest.object().at("entries").object().at("package").string(),32*1024*1024));
    const std::array<const char*,3> items{"fg:item:001164","fg:item:001165","fg:item:001166"};
    const std::array<std::array<const char*,2>,3> variants{{{{"fg:variant:007450","fg:variant:007451"}},
        {{"fg:variant:007452","fg:variant:007453"}},{{"fg:variant:007454","fg:variant:007455"}}}};
    const std::array<std::size_t,3> counts{66,132,198};
    const std::array<int,3> spans{22,45,68};
    for(std::size_t ci=0;ci<3;++ci){
        const auto& selected=current->lesson(items[ci]);
        ck(selected.title.find(ci==0?"66-contact":ci==1?"132-contact":"198-contact")!=std::string::npos,
            "exact selected Learn title and source case extent");
        for(std::size_t pick=0;pick<2;++pick){
            const auto token=current->admit(items[ci],variants[ci][pick]);
            ck(token->practiceAllowed()&&token->span()==Rational{spans[ci]}&&
               !token->identity().object().at("whole_task_completion").boolean(),
               "exact selected span, runtime permission and no whole-task credit");
            const auto& identity=token->identity().object();
            ck(identity.at("bundle_sha256")==json::Value("13e4bffc017d0356252c7a89ed49715232a11f2107dc90b9a336fae2c2ef491c")&&
               identity.at("package_sha256")==json::Value("3c29479b9f2ad3726972c52bdb82917021a314a675370e13d3d22281c855ae44")&&
               identity.at("content_version")==json::Value("curriculum-v1-level019-first-three-cases-build-only.1")&&
               identity.at("source_refs")==json::parse(R"(["L19-TXT-GUIDANCE","L19-PDF-GUIDANCE","L19-TXT-RUNG01","L19-TXT-RUNG02","L19-TXT-RUNG03","L19-PDF-CARDS01-02","L19-PDF-CARD03","L19-PDF-ROUTE"])")&&
               identity.at("source_hashes").object().at("L19-TXT-GUIDANCE")==json::Value("d4d0bebee8d9d2b6899bde448a0f5017070eef7936c2ccd6ffa03e7b95a4ce26")&&
               identity.at("source_hashes").object().at("L19-PDF-CARD03")==json::Value("107bfaecd5daa15adc1117440d01feead623f831e720837de5d18662375166e6"),
               "exact installed version, original source and decision bundle identity");
            const auto& events=token->model()->source().events;
            ck(events.size()==counts[ci],"exact 66/132/198 picked event count");
            for(std::size_t i=0;i<counts[ci];++i){
                const auto& e=events[i];const auto& tone=e.tones.at(0);
                const auto expected=lesson::installedCaseOnset(Rational{1,3},i,
                    ci>=1?66:0,Rational{ci>=1?1:0},ci==2?132:0,Rational{ci==2?1:0});
                const auto& original=packet.object().at("records").array()[ci].object().at("events").array()[i].object();
                ck(e.kind==music::Kind::Note&&e.span.onset==expected&&e.span.duration==Rational{1,3}&&
                   e.tones.size()==1&&json::Value::fromInteger(tone.string)==original.at("string")&&
                   json::Value::fromInteger(tone.fret)==original.at("fret")&&
                   json::Value::fromInteger(tone.midi)==original.at("midi")&&
                   e.handDirection==(((i%2==0)==(pick==0))?"D":"U"),
                   "exact source contact, two-gap onset and continuous D/U event "+std::to_string(i+1));
            }
        }
    }
    ck(lesson::installedCaseOnset(Rational{1,3},65,66,Rational{1},132,Rational{1})==Rational{65,3}&&
       lesson::installedCaseOnset(Rational{1,3},66,66,Rational{1},132,Rational{1})==Rational{23}&&
       lesson::installedCaseOnset(Rational{1,3},131,66,Rational{1},132,Rational{1})==Rational{134,3}&&
       lesson::installedCaseOnset(Rational{1,3},132,66,Rational{1},132,Rational{1})==Rational{46}&&
       lesson::installedCaseOnset(Rational{1,3},197,66,Rational{1},132,Rational{1})==Rational{203,3},
       "exact q22/q23/q45/q46/q68 seams and no tail rest");
    ck(lesson::validInstalledGaps(198,66,1,1,132,1,1)&&
       lesson::validInstalledGaps(132,66,1,1,0,0,1)&&
       lesson::validInstalledGaps(66,0,0,1,0,0,1),"zero, one and two gaps structurally valid");
    for(const auto& bad:std::array<std::array<std::int64_t,6>,12>{{
        {{0,0,1,132,1,1}},{{66,1,1,0,1,1}},{{66,1,1,0,0,0}},
        {{66,1,1,66,1,1}},{{132,1,1,66,1,1}},{{66,1,1,198,1,1}},
        {{66,1,1,132,0,1}},{{66,1,1,132,1,0}},{{66,1,1,132,-1,1}},
        {{0,1,1,0,0,1}},{{66,0,1,132,1,1}},{{66,1,0,132,1,1}}}})
        ck(!lesson::validInstalledGaps(198,static_cast<std::size_t>(bad[0]),bad[1],bad[2],
            static_cast<std::size_t>(bad[3]),bad[4],bad[5]),"malformed, unordered or out-of-range two-gap permission refused");
    for(const auto wrong:std::array<Rational,3>{Rational{0},Rational{1,2},Rational{2}})
        ck(!(lesson::installedCaseOnset(Rational{1,3},132,66,Rational{1},132,wrong)==Rational{46}),
            "missing/short/long second pause differs from reviewed B event133");
    refuses([&]{current->admit(items[0],variants[2][0]);},"foreign triple-case variant refused");
    refuses([&]{current->admit(items[2],variants[0][0]);},"reverse foreign variant refused");
    refuses([&]{lesson::Catalog::loadInstalled(base,std::vector<std::filesystem::path>{withNew.back()});},
            "out-of-order or partial extension set refused");
    auto missing=prior;missing.push_back(out/"missing-level019");
    refuses([&]{lesson::Catalog::loadInstalled(base,missing);},"missing atomic Level19 bundle refused");
    const auto altered=out/"mutable-level019";
    std::filesystem::copy(withNew.back(),altered,std::filesystem::copy_options::recursive);
    auto changed=prior;changed.push_back(altered);
    const auto packagePath=altered/manifest.object().at("entries").object().at("package").string();
    const auto originalBytes=content::readBounded(packagePath,32*1024*1024);
    for(const auto* fault:{"missing-A-rest","missing-B-rest","short-B-rest","extra-rest","event-count"}){
        auto candidate=json::parse(originalBytes);auto& ev=candidate.object().at("records").array()[2].object().at("events").array();
        if(std::string(fault)=="missing-A-rest")ev[66].object()["onset_q"]=json::parse("[22,1]");
        else if(std::string(fault)=="missing-B-rest")ev[132].object()["onset_q"]=json::parse("[45,1]");
        else if(std::string(fault)=="short-B-rest")ev[132].object()["onset_q"]=json::parse("[91,2]");
        else if(std::string(fault)=="extra-rest")ev[132].object()["kind"]="rest";
        else ev.pop_back();
        {std::ofstream write(packagePath,std::ios::binary);write<<json::stringify(candidate);}
        refuses([&]{lesson::Catalog::loadInstalled(base,changed);},
            std::string("changed ")+fault+" refused by frozen manifest before timing guard");
        {std::ofstream write(packagePath,std::ios::binary);write<<originalBytes;}
    }
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"cases\":3,\"attempts\":0,\"physical_listening\":false}\n";
    std::cout<<"PASS "<<checks<<" Level19 three-case source-backed Catalog/two-gap checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
