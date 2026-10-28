#include "content/LessonCatalog.hpp"
#include "content/Rung04Extension.hpp"
#include "practice/LessonAttempt.hpp"
#include <fstream>
#include <iostream>
#include <set>
using namespace fathom;using J=json::Value;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=6)throw std::runtime_error("Expected original bundle, extension, new evidence directory");
    const std::filesystem::path base=argv[1],prior=argv[2],prior3=argv[3],ext=argv[4],out=argv[5];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute evidence required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& label){++checks;trace<<label<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(label);};
    auto refuse=[&](auto fn,const std::string& label){bool failed=false;try{fn();}catch(const std::exception&){failed=true;}ck(failed,label);};
    const auto original=lesson::Catalog::load(base),priorCatalog=lesson::Catalog::load(base,prior),prior3Catalog=lesson::Catalog::load(base,prior,prior3),catalog=lesson::Catalog::load(base,prior,prior3,ext);
    ck(original->lessons().size()==13&&priorCatalog->lessons().size()==14&&prior3Catalog->lessons().size()==15&&catalog->lessons().size()==16,"separate original13, prior14 and combined16");
    ck(catalog->package()==original->package()&&catalog->validationReport()==original->validationReport(),"original native package/report unchanged; no mixed schema");
    ck(original->sourceEntryCount()==47&&priorCatalog->sourceEntryCount()==54&&prior3Catalog->sourceEntryCount()==61&&catalog->sourceEntryCount()==68,"source entries from independent packages");
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
    for(const auto& v:prior3Catalog->lesson("fg:item:001142").variants)ck(prior3Catalog->admit("fg:item:001142",v.id)->identity()==catalog->admit("fg:item:001142",v.id)->identity(),"Rung03 admission unchanged "+v.id);
    const std::string item="fg:item:001143";
    const std::vector<int> midi{48,50,52,53,55,57,59,60,60,59,57,55,53,52,50,48};
    for(const auto& id:{"fg:variant:007408","fg:variant:007409"}){
        const auto a=catalog->admit(item,id);ck(a->practiceAllowed()&&a->span()==Rational{8},"new exact8-quarter single cell "+std::string(id));
        const auto& identity=a->identity().object();
        ck(identity.at("content_revision")==J::fromInteger(1)&&identity.at("package_sha256")==J("a3ac97896f9fffbcbcf2d25dc1e757252cecd0737cae680caaf1a36c037f4f8a"),"new revision and frozen package bound");
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
    refuse([&]{catalog->admit("fg:item:000003","fg:variant:007408");},"wrong item ownership refused");
    refuse([&]{catalog->admit(item,"fg:variant:000029");},"wrong variant ownership refused");
    refuse([&]{catalog->admit("fg:item:000001","fg:variant:000001");},"unadmitted case stays refused");
    refuse([&]{lesson::Catalog::load(base,prior,prior3,out/"missing");},"missing extension fail closed");
    auto manifest=json::parse(content::readBounded(ext/"manifest.json",1024*1024));
    const auto mutableExt=out/"mutable-extension";std::filesystem::copy(ext,mutableExt,std::filesystem::copy_options::recursive);
    auto put=[](const std::filesystem::path& p,const std::string& b){std::ofstream s(p,std::ios::binary);s<<b;if(!s)throw std::runtime_error("write");};
    for(const char* key:{"package","registry","profile","decision"}){
        const auto rel=manifest.object().at("entries").object().at(key).string();const auto raw=content::readBounded(mutableExt/rel,32*1024*1024);put(mutableExt/rel,"{}");
        refuse([&]{lesson::Catalog::load(base,prior,prior3,mutableExt);},std::string("tampered extension ")+key);put(mutableExt/rel,raw);
    }
    const auto originalManifest=content::readBounded(mutableExt/"manifest.json",1024*1024);put(mutableExt/"manifest.json","{}");refuse([&]{lesson::Catalog::load(base,prior,prior3,mutableExt);},"tampered extension manifest");put(mutableExt/"manifest.json",originalManifest);
    std::string source;for(const auto& f:manifest.object().at("files").array())if(f.object().at("path").string().rfind("Notes/",0)==0){source=f.object().at("path").string();break;}
    const auto sourceBytes=content::readBounded(mutableExt/source,32*1024*1024);std::filesystem::remove(mutableExt/source);refuse([&]{lesson::Catalog::load(base,prior,prior3,mutableExt);},"missing source refused");put(mutableExt/source,sourceBytes);
    std::filesystem::remove(mutableExt/source);std::filesystem::create_symlink(ext/source,mutableExt/source);refuse([&]{lesson::Catalog::load(base,prior,prior3,mutableExt);},"source symlink refused");std::filesystem::remove(mutableExt/source);put(mutableExt/source,sourceBytes);
    auto readEntry=[&](const char* key){return content::readBounded(ext/manifest.object().at("entries").object().at(key).string(),32*1024*1024);};
    content::Input input{readEntry("package"),readEntry("registry"),readEntry("profile"),manifest.object().at("profile_sha256").string(),ext};
    const auto d=json::parse(readEntry("decision"));
    // Direct guard tests deliberately substitute a test trust pin. They cannot issue a Catalog capability.
    for(const auto* status:{"Pending","Rejected"}){auto bad=d;bad.object()["status"]=status;const auto bytes=json::stringify(bad);refuse([&]{lesson::validateRung04Extension(input,bytes,content::sha256(bytes));},std::string("decision state refused ")+status);}
    for(const auto* key:{"package_sha256","profile_sha256","registry_sha256"}){auto bad=d;bad.object()[key]=std::string(64,'0');const auto bytes=json::stringify(bad);refuse([&]{lesson::validateRung04Extension(input,bytes,content::sha256(bytes));},std::string("stale decision binding ")+key);}
    {auto bad=d;bad.object().at("scope").object()["whole_ladder"]=true;const auto bytes=json::stringify(bad);refuse([&]{lesson::validateRung04Extension(input,bytes,content::sha256(bytes));},"expanded scope refused");}
    {auto bad=d;bad.object()["source_review_sha256"]=std::string(64,'0');const auto bytes=json::stringify(bad);refuse([&]{lesson::validateRung04Extension(input,bytes,content::sha256(bytes));},"stale independent source review refused");}
    ck(lesson::Catalog::load(base,prior,prior3,mutableExt)->lessons().size()==16,"restored exact bundle loads16");
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"cases\":16,\"variants\":55,\"physical_listening\":false}\n";
    std::cout<<"PASS "<<checks<<" composite catalog/admission checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
