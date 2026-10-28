#include "content/LessonCatalog.hpp"
#include "content/Level006Extension.hpp"
#include "practice/LessonAttempt.hpp"
#include <fstream>
#include <iostream>
#include <set>
using namespace fathom;using J=json::Value;
int main(int argc,char** argv){int checks=0;try{
    if(argc!=7)throw std::runtime_error("Expected original bundle, extension, new evidence directory");
    const std::filesystem::path base=argv[1],prior=argv[2],prior3=argv[3],prior4=argv[4],ext=argv[5],out=argv[6];
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh absolute evidence required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");
    auto ck=[&](bool ok,const std::string& label){++checks;trace<<label<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(label);};
    auto refuse=[&](auto fn,const std::string& label){bool failed=false;try{fn();}catch(const std::exception&){failed=true;}ck(failed,label);};
    const auto original=lesson::Catalog::load(base),priorCatalog=lesson::Catalog::load(base,prior),prior3Catalog=lesson::Catalog::load(base,prior,prior3),prior4Catalog=lesson::Catalog::load(base,prior,prior3,prior4),catalog=lesson::Catalog::load(base,prior,prior3,prior4,ext);
    ck(original->lessons().size()==13&&priorCatalog->lessons().size()==14&&prior3Catalog->lessons().size()==15&&prior4Catalog->lessons().size()==16&&catalog->lessons().size()==17,"separate original13, prior14, prior15, prior16 and combined17");
    ck(catalog->package()==original->package()&&catalog->validationReport()==original->validationReport(),"original native package/report unchanged; no mixed schema");
    ck(original->sourceEntryCount()==47&&priorCatalog->sourceEntryCount()==54&&prior3Catalog->sourceEntryCount()==61&&prior4Catalog->sourceEntryCount()==68&&catalog->sourceEntryCount()==72,"source entries from independent packages");
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
    for(const auto& v:prior4Catalog->lesson("fg:item:001143").variants)ck(prior4Catalog->admit("fg:item:001143",v.id)->identity()==catalog->admit("fg:item:001143",v.id)->identity(),"Rung04 admission unchanged "+v.id);
    const std::string item="fg:item:001144";
    const std::vector<int> midi{45,46,45,56};
    for(const auto& id:{"fg:variant:007410","fg:variant:007411"}){
        const auto a=catalog->admit(item,id);ck(a->practiceAllowed()&&a->span()==Rational{1},"new exact one-quarter separated cell "+std::string(id));
        const auto& identity=a->identity().object();
        ck(identity.at("content_revision")==J::fromInteger(1)&&identity.at("package_sha256")==J("81a0acaded38ea742a0d8c1a5b0fbde79050c08252238c9e217e5bc145197778"),"new revision and frozen package bound");
        ck(identity.at("content_version").string()==catalog->contentVersion(item)&&identity.at("decision_sha256")!=original->admit("fg:item:000003","fg:variant:000029")->identity().object().at("decision_sha256"),"new version and decision separate from Rung01");
        ck(!identity.at("whole_task_completion").boolean(),"no source-task completion");
        const auto& events=a->model()->source().events;ck(events.size()==4,"four source events");
        const std::vector<int> strings{1,1,1,3},frets{5,6,5,6};
        const std::vector<std::string> fingers{"1","2","1","2"};
        for(std::size_t i=0;i<events.size();++i)ck(events[i].span.onset==Rational{static_cast<std::int64_t>(i),4}&&events[i].span.duration==Rational{1,4}&&events[i].tones.size()==1&&events[i].tones.front().midi==midi[i]&&events[i].tones.front().string==strings[i]&&events[i].tones.front().fret==frets[i]&&events[i].tones.front().finger==fingers[i]&&events[i].handDirection==(((i%2==0)==(std::string(id)=="fg:variant:007410"))?"D":"U"),"independent four-note E-D/string/fret/finger/pick/timing "+std::to_string(i));
        const auto cfg=a->practiceConfiguration(44100,120);const auto request=capture::lessonStart(*a,cfg,"00000000-0000-4000-8000-000000000001","2026-09-23T21:35:24Z","America/New_York",1);
        for(const auto* key:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs"})ck(request.binding.context.object().at(key)==identity.at(key),std::string("Attempt input identity ")+key);
        ck(request.binding.sourceHashes==identity.at("source_hashes"),"Attempt input exact source hashes");
        std::ofstream(out/(std::string(id)+"-admission.json"))<<json::stringify(a->identity());
        refuse([&]{catalog->admitCell(item,id,1);},"arbitrary transfer cell refused");
    }
    refuse([&]{catalog->admit("fg:item:000003","fg:variant:007410");},"wrong item ownership refused");
    refuse([&]{catalog->admit(item,"fg:variant:000029");},"wrong variant ownership refused");
    refuse([&]{catalog->admit("fg:item:000001","fg:variant:000001");},"unadmitted case stays refused");
    refuse([&]{lesson::Catalog::load(base,prior,prior3,prior4,out/"missing");},"missing extension fail closed");
    auto manifest=json::parse(content::readBounded(ext/"manifest.json",1024*1024));
    const auto mutableExt=out/"mutable-extension";std::filesystem::copy(ext,mutableExt,std::filesystem::copy_options::recursive);
    auto put=[](const std::filesystem::path& p,const std::string& b){std::ofstream s(p,std::ios::binary);s<<b;if(!s)throw std::runtime_error("write");};
    for(const char* key:{"package","registry","profile","decision"}){
        const auto rel=manifest.object().at("entries").object().at(key).string();const auto raw=content::readBounded(mutableExt/rel,32*1024*1024);put(mutableExt/rel,"{}");
        refuse([&]{lesson::Catalog::load(base,prior,prior3,prior4,mutableExt);},std::string("tampered extension ")+key);put(mutableExt/rel,raw);
    }
    const auto originalManifest=content::readBounded(mutableExt/"manifest.json",1024*1024);put(mutableExt/"manifest.json","{}");refuse([&]{lesson::Catalog::load(base,prior,prior3,prior4,mutableExt);},"tampered extension manifest");put(mutableExt/"manifest.json",originalManifest);
    std::string source;for(const auto& f:manifest.object().at("files").array())if(f.object().at("path").string().rfind("Notes/",0)==0){source=f.object().at("path").string();break;}
    const auto sourceBytes=content::readBounded(mutableExt/source,32*1024*1024);std::filesystem::remove(mutableExt/source);refuse([&]{lesson::Catalog::load(base,prior,prior3,prior4,mutableExt);},"missing source refused");put(mutableExt/source,sourceBytes);
    std::filesystem::remove(mutableExt/source);std::filesystem::create_symlink(ext/source,mutableExt/source);refuse([&]{lesson::Catalog::load(base,prior,prior3,prior4,mutableExt);},"source symlink refused");std::filesystem::remove(mutableExt/source);put(mutableExt/source,sourceBytes);
    auto readEntry=[&](const char* key){return content::readBounded(ext/manifest.object().at("entries").object().at(key).string(),32*1024*1024);};
    content::Input input{readEntry("package"),readEntry("registry"),readEntry("profile"),manifest.object().at("profile_sha256").string(),ext};
    const auto d=json::parse(readEntry("decision"));
    // Direct guard tests deliberately substitute a test trust pin. They cannot issue a Catalog capability.
    for(const auto* status:{"Pending","Rejected"}){auto bad=d;bad.object()["status"]=status;const auto bytes=json::stringify(bad);refuse([&]{lesson::validateLevel006Extension(input,bytes,content::sha256(bytes),readEntry("provenance"));},std::string("decision state refused ")+status);}
    for(const auto* key:{"package_sha256","profile_sha256","registry_sha256"}){auto bad=d;bad.object()[key]=std::string(64,'0');const auto bytes=json::stringify(bad);refuse([&]{lesson::validateLevel006Extension(input,bytes,content::sha256(bytes),readEntry("provenance"));},std::string("stale decision binding ")+key);}
    {auto bad=d;bad.object().at("scope").object()["whole_workbook"]=true;const auto bytes=json::stringify(bad);refuse([&]{lesson::validateLevel006Extension(input,bytes,content::sha256(bytes),readEntry("provenance"));},"expanded scope refused");}
    {auto bad=d;bad.object()["source_review_sha256"]=std::string(64,'0');const auto bytes=json::stringify(bad);refuse([&]{lesson::validateLevel006Extension(input,bytes,content::sha256(bytes),readEntry("provenance"));},"stale independent source review refused");}
    {auto bad=d;bad.object()["source_provenance_sha256"]=std::string(64,'0');const auto bytes=json::stringify(bad);refuse([&]{lesson::validateLevel006Extension(input,bytes,content::sha256(bytes),readEntry("provenance"));},"stale event provenance refused");}
    put(mutableExt/"unlisted.txt","expanded content");refuse([&]{lesson::Catalog::load(base,prior,prior3,prior4,mutableExt);},"unlisted extension content refused");std::filesystem::remove(mutableExt/"unlisted.txt");
    ck(lesson::Catalog::load(base,prior,prior3,prior4,mutableExt)->lessons().size()==17,"restored exact bundle loads17");
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"cases\":17,\"variants\":57,\"physical_listening\":false}\n";
    std::cout<<"PASS "<<checks<<" composite catalog/admission checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
