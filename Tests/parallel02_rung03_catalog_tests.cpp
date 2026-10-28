#include "content/LessonCatalog.hpp"
#include "content/Rung03Extension.hpp"
#include "practice/LessonAttempt.hpp"
#include <fstream>
#include <iostream>
#include <set>
using namespace fathom;using J=json::Value;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=5)throw std::runtime_error("Expected original bundle, extension, new evidence directory");
    const std::filesystem::path base=argv[1],prior=argv[2],ext=argv[3],out=argv[4];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute evidence required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& label){++checks;trace<<label<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(label);};
    auto refuse=[&](auto fn,const std::string& label){bool failed=false;try{fn();}catch(const std::exception&){failed=true;}ck(failed,label);};
    const auto original=lesson::Catalog::load(base),priorCatalog=lesson::Catalog::load(base,prior),catalog=lesson::Catalog::load(base,prior,ext);
    ck(original->lessons().size()==13&&priorCatalog->lessons().size()==14&&catalog->lessons().size()==15,"separate original13, prior14 and combined15");
    ck(catalog->package()==original->package()&&catalog->validationReport()==original->validationReport(),"original native package/report unchanged; no mixed schema");
    ck(original->sourceEntryCount()==47&&priorCatalog->sourceEntryCount()==54&&catalog->sourceEntryCount()==61,"source entries from independent packages");
    int variants=0;
    for(const auto& l:original->lessons()){
        ck(catalog->lesson(l.id).record==l.record,"unchanged original record "+l.id);
        for(const auto& v:l.variants){++variants;ck(catalog->variant(l.id,v.id).authored==v.authored,"unchanged original variant "+v.id);
            try{const auto old=original->admit(l.id,v.id),now=catalog->admit(l.id,v.id);ck(old->identity()==now->identity()&&old->sourceBinding()==now->sourceBinding(),"unchanged original runtime identity "+v.id);}
            catch(const std::exception&){refuse([&]{catalog->admit(l.id,v.id);},"original refusal retained "+v.id);}
        }
    }
    ck(variants==49,"all49 original variants retained");
    for(const auto& v:priorCatalog->lesson("fg:item:001141").variants)ck(priorCatalog->admit("fg:item:001141",v.id)->identity()==catalog->admit("fg:item:001141",v.id)->identity(),"Rung02 admission unchanged "+v.id);
    const std::string item="fg:item:001142";
    const std::vector<int> midi{47,49,51,52,54,56,58,59,59,58,56,54,52,51,49,47};
    for(const auto& id:{"fg:variant:007406","fg:variant:007407"}){
        const auto a=catalog->admit(item,id);ck(a->practiceAllowed()&&a->span()==Rational{8},"new exact8-quarter single cell "+std::string(id));
        const auto& identity=a->identity().object();
        ck(identity.at("content_revision")==J::fromInteger(1)&&identity.at("package_sha256")==J("56c711c70445904243207f9cecb7eaf125d9023af040b65d2dbfe16b2d892be5"),"new revision and frozen package bound");
        ck(identity.at("content_version").string()==catalog->contentVersion(item)&&identity.at("decision_sha256")!=original->admit("fg:item:000003","fg:variant:000029")->identity().object().at("decision_sha256"),"new version and decision separate from Rung01");
        ck(!identity.at("whole_task_completion").boolean(),"no source-task completion");
        const auto& events=a->model()->source().events;ck(events.size()==16,"16 source events");
        for(std::size_t i=0;i<events.size();++i)ck(events[i].span.onset==Rational{static_cast<std::int64_t>(i),2}&&events[i].span.duration==Rational{1,2}&&events[i].tones.size()==1&&events[i].tones.front().midi==midi[i],"exact source note/order/eighth "+std::to_string(i));
        const auto cfg=a->practiceConfiguration(44100,120);const auto request=capture::lessonStart(*a,cfg,"00000000-0000-4000-8000-000000000001","2026-09-23T21:35:24Z","America/New_York",1);
        for(const auto* key:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs"})ck(request.binding.context.object().at(key)==identity.at(key),std::string("Attempt input identity ")+key);
        ck(request.binding.sourceHashes==identity.at("source_hashes"),"Attempt input exact source hashes");
        std::ofstream(out/(std::string(id)+"-admission.json"))<<json::stringify(a->identity());
        refuse([&]{catalog->admitCell(item,id,1);},"arbitrary transfer cell refused");
    }
    refuse([&]{catalog->admit("fg:item:000003","fg:variant:007406");},"wrong item ownership refused");
    refuse([&]{catalog->admit(item,"fg:variant:000029");},"wrong variant ownership refused");
    refuse([&]{catalog->admit("fg:item:000001","fg:variant:000001");},"unadmitted case stays refused");
    refuse([&]{lesson::Catalog::load(base,prior,out/"missing");},"missing extension fail closed");
    auto manifest=json::parse(content::readBounded(ext/"manifest.json",1024*1024));
    const auto mutableExt=out/"mutable-extension";std::filesystem::copy(ext,mutableExt,std::filesystem::copy_options::recursive);
    auto put=[](const std::filesystem::path& p,const std::string& b){std::ofstream s(p,std::ios::binary);s<<b;if(!s)throw std::runtime_error("write");};
    for(const char* key:{"package","registry","profile","decision"}){
        const auto rel=manifest.object().at("entries").object().at(key).string();const auto raw=content::readBounded(mutableExt/rel,32*1024*1024);put(mutableExt/rel,"{}");
        refuse([&]{lesson::Catalog::load(base,prior,mutableExt);},std::string("tampered extension ")+key);put(mutableExt/rel,raw);
    }
    const auto originalManifest=content::readBounded(mutableExt/"manifest.json",1024*1024);put(mutableExt/"manifest.json","{}");refuse([&]{lesson::Catalog::load(base,prior,mutableExt);},"tampered extension manifest");put(mutableExt/"manifest.json",originalManifest);
    std::string source;for(const auto& f:manifest.object().at("files").array())if(f.object().at("path").string().rfind("Notes/",0)==0){source=f.object().at("path").string();break;}
    const auto sourceBytes=content::readBounded(mutableExt/source,32*1024*1024);std::filesystem::remove(mutableExt/source);refuse([&]{lesson::Catalog::load(base,prior,mutableExt);},"missing source refused");put(mutableExt/source,sourceBytes);
    std::filesystem::remove(mutableExt/source);std::filesystem::create_symlink(ext/source,mutableExt/source);refuse([&]{lesson::Catalog::load(base,prior,mutableExt);},"source symlink refused");std::filesystem::remove(mutableExt/source);put(mutableExt/source,sourceBytes);
    auto readEntry=[&](const char* key){return content::readBounded(ext/manifest.object().at("entries").object().at(key).string(),32*1024*1024);};
    content::Input input{readEntry("package"),readEntry("registry"),readEntry("profile"),manifest.object().at("profile_sha256").string(),ext};
    const auto d=json::parse(readEntry("decision"));
    // Direct guard tests deliberately substitute a test trust pin. They cannot issue a Catalog capability.
    for(const auto* status:{"Pending","Rejected"}){auto bad=d;bad.object()["status"]=status;const auto bytes=json::stringify(bad);refuse([&]{lesson::validateRung03Extension(input,bytes,content::sha256(bytes));},std::string("decision state refused ")+status);}
    for(const auto* key:{"package_sha256","profile_sha256","registry_sha256"}){auto bad=d;bad.object()[key]=std::string(64,'0');const auto bytes=json::stringify(bad);refuse([&]{lesson::validateRung03Extension(input,bytes,content::sha256(bytes));},std::string("stale decision binding ")+key);}
    {auto bad=d;bad.object().at("scope").object()["whole_ladder"]=true;const auto bytes=json::stringify(bad);refuse([&]{lesson::validateRung03Extension(input,bytes,content::sha256(bytes));},"expanded scope refused");}
    ck(lesson::Catalog::load(base,prior,mutableExt)->lessons().size()==15,"restored exact bundle loads15");
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"cases\":15,\"variants\":53,\"physical_listening\":false}\n";
    std::cout<<"PASS "<<checks<<" composite catalog/admission checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
