#include "content/LessonCatalog.hpp"
#include "core/TabPresentation.hpp"
#include <array>
#include <fstream>
#include <functional>
#include <iostream>
#include <set>
using namespace fathom;
using J=json::Value;
namespace {const J& at(const J& j,const std::string& k){return j.object().at(k);}void write(const std::filesystem::path& p,const std::string& s){std::ofstream o(p,std::ios::binary);o<<s;if(!o)throw std::runtime_error("Cannot retain output");}}
int main(int argc,char** argv){
    int checks=0;std::ofstream trace;
    auto check=[&](bool good,const std::string& name){++checks;trace<<name<<'\t'<<(good?"PASS":"FAIL")<<std::endl;if(!good)throw std::runtime_error(name);};
    try{
        if(argc!=3)throw std::invalid_argument("Expected absolute bundle and new evidence directory");
        const std::filesystem::path bundle(argv[1]),out(argv[2]);if(!out.is_absolute()||std::filesystem::exists(out))throw std::invalid_argument("Output must be new and absolute");std::filesystem::create_directories(out);trace.open(out/"checks.tsv");
        auto catalog=lesson::Catalog::load(bundle);check(catalog->lessons().size()==13,"13 accepted selected cases");check(catalog->contentVersion()=="representative-controls.1","independent content version");
        check(at(catalog->package(),"sources").object().size()==47,"47 full source passages");
        std::set<int> levels;std::size_t variants=0,renderable=0;std::set<std::string> seenPassages;
        for(const auto& l:catalog->lessons()){
            levels.insert(l.level);check(!at(at(l.record,"control_scope"),"whole_workbook_complete").boolean(),l.id+" bounded selected case");
            const auto instructions=catalog->text(l.id,l.variants.front().id,lesson::Section::Instructions);write(out/("L"+std::to_string(l.level)+"-instructions.txt"),instructions);
            for(const auto* refs:{&at(l.record,"authored_text_refs"),&at(at(l.record,"control_scope"),"basis_refs")})for(const auto& ref:refs->array()){
                const auto& source=at(at(catalog->package(),"sources"),ref.string());check(instructions.find(at(source,"text").string())!=std::string::npos,l.id+" exact passage "+ref.string());seenPassages.insert(ref.string());
            }
            for(const auto& v:l.variants){write(out/(v.id+"-details.txt"),catalog->text(l.id,v.id,lesson::Section::VariantDetails));++variants;renderable+=v.technicallyRenderable?1:0;check(v.model&&!v.model->source().syntheticFixture&&v.model->source().itemId==l.id,"actual source variant model "+v.id);auto document=std::make_shared<const tab::Document>(v.model);check(document->source().events.size()==v.model->source().events.size(),"same immutable TAB model "+v.id);}
            for(auto s:{lesson::Section::Context,lesson::Section::Assessment,lesson::Section::Resources,lesson::Section::VariantDetails}){const auto text=catalog->text(l.id,l.variants.front().id,s);check(!text.empty(),l.id+" accessible section "+std::to_string(static_cast<int>(s)));if(s!=lesson::Section::VariantDetails)write(out/("L"+std::to_string(l.level)+"-section"+std::to_string(static_cast<int>(s))+".txt"),text);}
            for(const auto& resource:l.resources)check(at(resource,"availability").string()=="required_unsupplied"&&at(resource,"supplied_asset").null(),"actual unsupplied resource "+at(resource,"id").string());
        }
        check(levels==std::set<int>({1,3,12,15,29,39,48,49,58,74,83,97,105}),"source ordering covers exact accepted levels");check(variants==49&&renderable==10,"49 readable and only10 structurally renderable");check(seenPassages.size()==47,"all source passages reachable");
        const auto& baseReport=catalog->validationReport();
        std::set<std::string> reportedVariants;
        const J* slideReport=nullptr;
        for(const auto& row:at(baseReport,"variants").array()){
            const auto id=at(row,"variant_id").string();
            check(reportedVariants.insert(id).second,"unique representative validator variant "+id);
            if(id=="fg:variant:000040")slideReport=&row;
        }
        check(reportedVariants.size()==49&&slideReport&&
            at(*slideReport,"item_id").string()=="fg:item:000007"&&
            !at(*slideReport,"technically_renderable").boolean()&&
            !at(*slideReport,"curriculum_playback_authorized").boolean()&&
            !catalog->variant("fg:item:000007","fg:variant:000040").technicallyRenderable&&
            !at(baseReport,"curriculum_playback_authorized").boolean(),
            "exact historical SlideArrival variant remains unrenderable and unauthorized");
        const auto& slideIssues=at(*slideReport,"issues").array();
        check(slideIssues.size()==5,"only five current ordered SlideArrival variant diagnostics");
        const std::array<const char*,4> scopeEvents{{"fg:item:000007:event:0003",
            "fg:item:000007:event:0008","fg:item:000007:event:0011","fg:item:000007:event:0016"}};
        for(std::size_t i=0;i<scopeEvents.size();++i)
            check(at(slideIssues[i],"code").string()=="unresolved_scope"&&
                at(slideIssues[i],"event").string()==scopeEvents[i]&&
                at(slideIssues[i],"field").string()=="scopeStrings",
                "exact surviving scope refusal "+std::to_string(i));
        check(at(slideIssues[4],"code").string()=="not_admitted"&&
            at(slideIssues[4],"field").string()=="admission",
            "admission refusal remains last");
        bool slideDenied=false;
        try{catalog->admit("fg:item:000007","fg:variant:000040");}
        catch(const std::exception&){slideDenied=true;}
        check(slideDenied,"SlideArrival base admission refused");
        const auto item=[](int n){return "fg:item:"+std::string(6-std::to_string(n).size(),'0')+std::to_string(n);};
        auto section=[&](int n,lesson::Section s){auto id=item(n);return catalog->text(id,catalog->lesson(id).variants.front().id,s);};
        check(catalog->lesson(item(6)).resources.size()==1&&catalog->lesson(item(13)).resources.size()==1,"L39/L105 join plan despite empty local resource arrays");
        check(catalog->lesson(item(12)).resources.size()==3,"L97 groove harmony and capstone resources distinct");
        check(section(11,lesson::Section::Context).find("bar6 Chord A7 and Top C#")!=std::string::npos,"C3 approved melody exception preserved");
        for(auto pair:{std::pair<int,int>{7,13},{11,14},{12,14},{13,24}}){const auto& rubric=at(catalog->lesson(item(pair.first)).record,"rubric");check(at(rubric,"minimum_total")==J::fromInteger(pair.second),"distinct source rubric total "+std::to_string(pair.first));}
        check(section(7,lesson::Section::Assessment).find("0 = absent")!=std::string::npos&&section(7,lesson::Section::Assessment).find("2 = controlled")!=std::string::npos,"source score-anchor associations explicit");
        check(section(13,lesson::Section::Instructions).find("L105-PDF28")!=std::string::npos&&section(12,lesson::Section::Instructions).find("L97-PDF18")!=std::string::npos,"late PDF exam/reflection/capstone passages accessible");
        for(int n:{5,10,11,12,13})check(catalog->lesson(item(n)).variants.front().model->source().events.empty(),"no fabricated note events "+std::to_string(n));
        check(lesson::readinessText(catalog->variant(item(2),"fg:variant:000005")).find("accent operation")!=std::string::npos,"unsupported crossing accent explained");
        check(lesson::readinessText(catalog->variant(item(3),"fg:variant:000031")).find("tail pause")!=std::string::npos,"unsupported tail pause operation explained");
        const auto& original=catalog->variant(item(2),"fg:variant:000006");auto document=std::make_shared<const tab::Document>(original.model);catalog.reset();check(document->source().itemId==item(2)&&document->source().events.size()==20,"immutable model lifetime outlives catalog");
        auto mutableBundle=out/"mutable-bundle";std::filesystem::copy(bundle,mutableBundle,std::filesystem::copy_options::recursive);const auto manifest=json::parse(content::readBounded(bundle/"manifest.json",1024*1024));
        int mutation=0;auto refuse=[&](const std::filesystem::path& path,const std::string& expected){std::optional<std::string> failure;try{auto rejected=lesson::Catalog::load(path);(void)rejected;}catch(const std::exception& ex){failure=ex.what();}check(failure.has_value(),"must refuse "+expected);check(failure->find(expected)!=std::string::npos,"refusal boundary "+expected);write(out/("refusal-"+std::to_string(++mutation)+".txt"),*failure);};
        auto corrupt=[&](const std::string& rel,const std::string& replacement,const std::string& reason){const auto originalBytes=content::readBounded(mutableBundle/rel,32*1024*1024);write(out/("mutation-"+std::to_string(mutation+1)+".bin"),replacement);write(mutableBundle/rel,replacement);refuse(mutableBundle,reason);write(mutableBundle/rel,originalBytes);};
        for(const auto* key:{"package","registry","profile","decision"})corrupt(at(at(manifest,"entries"),key).string(),"{}","lesson asset");
        const auto decisionPath=at(at(manifest,"entries"),"decision").string();
        auto changedDecision=json::parse(content::readBounded(bundle/decisionPath,1024*1024));
        for(auto& row:changedDecision.object().at("variants").array())if(at(row,"variantId").string()=="fg:variant:000040"){
            row.object().at("issueCodes").array().erase(row.object().at("issueCodes").array().begin()+4);
            break;
        }
        corrupt(decisionPath,json::stringify(changedDecision),"lesson asset");
        corrupt("manifest.json","{\"version\":\"future\"}","manifest");corrupt("manifest.json","{\"x\":1,\"x\":2}","manifest");corrupt("manifest.json",std::string(1024*1024+1,'x'),"limit");
        std::string source,authority,resource;
        for(const auto& f:at(manifest,"files").array()){const auto p=at(f,"path").string();if(source.empty()&&p.rfind("Notes/",0)==0)source=p;if(authority.empty()&&p.find("identity-manifest.json")!=std::string::npos)authority=p;if(p.find("-evidence/plan.json")!=std::string::npos)resource=p;}
        for(const auto& rel:{source,authority,resource}){corrupt(rel,"truncated","lesson asset");auto old=content::readBounded(mutableBundle/rel,32*1024*1024);std::filesystem::remove(mutableBundle/rel);refuse(mutableBundle,"Missing local lesson asset");write(mutableBundle/rel,old);}
        const auto external=out/"outside-source.bin";const auto sourceBytes=content::readBounded(mutableBundle/source,32*1024*1024);write(external,sourceBytes);std::filesystem::remove(mutableBundle/source);std::filesystem::create_symlink(external,mutableBundle/source);refuse(mutableBundle,"symlinks");std::filesystem::remove(mutableBundle/source);write(mutableBundle/source,sourceBytes);
        refuse(mutableBundle/".","Dot paths");refuse(out/"absent","missing");
        auto after=lesson::Catalog::load(mutableBundle);check(after->lessons().size()==13,"original restored bundle remains readable");
        try{after->variant(item(1),"fg:variant:000006");check(false,"cross-owner refused");}catch(const std::out_of_range&){check(true,"cross-owner variant selection refused");}
        try{after->lesson("missing");check(false,"missing ID refused");}catch(const std::out_of_range&){check(true,"missing identity refused");}
        write(out/"validation-report.json",json::stringify(after->validationReport()));write(out/"summary.json",json::stringify(J::Object{{"checks",J::fromInteger(checks)},{"native_audio",false},{"progress_mutation",false},{"scope","Trusted-bundle mutations refuse at hash boundary; not proof of unreachable inner parser branches"}}));
        std::cout<<"PASS "<<checks<<" lesson catalog checks\n";return 0;
    }catch(const std::exception& ex){std::cerr<<"FAIL after "<<checks<<": "<<ex.what()<<'\n';return 1;}
}
