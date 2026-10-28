#include "content/SelectedCatalogStore.hpp"
#include "content/InstalledExtensionRegistry.hpp"
#include "installed_catalog_fixture_access.hpp"
#include <chrono>
#include <fstream>
#include <iostream>

namespace {
namespace fs=std::filesystem;
using fathom::lesson::Catalog;
using fathom::lesson::SelectedCatalogStore;
using J=fathom::json::Value;
int checks=0;
void check(bool yes,const std::string& why){++checks;if(!yes)throw std::runtime_error(why);}
template<class F> void refused(F work,const std::string& why){bool no=false;try{work();}catch(const std::exception&){no=true;}check(no,why);}
std::vector<fs::path> paths(const fs::path& resources){
    std::vector<fs::path> result;
    for(const auto& name:Catalog::installedExtensionDirectoryNames())result.push_back(resources/name);
    return result;
}
void write(const fs::path& path,const std::string& bytes){
    std::ofstream out(path,std::ios::binary|std::ios::trunc);out.write(bytes.data(),static_cast<std::streamsize>(bytes.size()));
    if(!out)throw std::runtime_error("Cannot write owned test fixture");
}
struct Scratch {
    fs::path path;
    Scratch(){
        path=fs::canonical(fs::temp_directory_path())/("fathom-selected-catalog-tests-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
        if(!fs::create_directory(path))throw std::runtime_error("Test scratch directory already exists");
    }
    ~Scratch(){std::error_code ec;fs::remove_all(path,ec);}
};
void sameLesson(const Catalog& selected,const Catalog& reference,const std::string& item){
    const auto& actual=selected.lesson(item);const auto& expected=reference.lesson(item);
    check(actual.record==expected.record&&actual.id==expected.id&&actual.title==expected.title&&actual.level==expected.level,"Selected lesson preserves original record "+item);
    check(selected.contentVersion(item)==reference.contentVersion(item),"Selected content version "+item);
    check(actual.variants.size()==expected.variants.size(),"Selected variant coverage "+item);
    for(const auto& variant:expected.variants){
        const auto& loaded=selected.variant(item,variant.id);
        check(loaded.authored==variant.authored&&loaded.technicallyRenderable==variant.technicallyRenderable,"Selected authored variant/readiness "+variant.id);
        check(loaded.model&&variant.model&&loaded.model->source().itemId==variant.model->source().itemId&&loaded.model->source().events.size()==variant.model->source().events.size(),"Selected model owner/event count "+variant.id);
        // Instructions/details bind exact provenance, limitations and identity.
        check(selected.text(item,variant.id,fathom::lesson::Section::Instructions)==reference.text(item,variant.id,fathom::lesson::Section::Instructions),"Selected exact source instructions "+variant.id);
        check(selected.text(item,variant.id,fathom::lesson::Section::VariantDetails)==reference.text(item,variant.id,fathom::lesson::Section::VariantDetails),"Selected exact variant details "+variant.id);
    }
}
}
int main(int argc,char** argv){
    try{
        if(argc!=2)throw std::invalid_argument("Usage: selected_catalog_loading_tests ABSOLUTE_APP_RESOURCES");
        const auto resources=fs::canonical(fs::path(argv[1]));
        const auto base=resources/"representative-controls";
        const std::string baseHash="0ecd2b1466a7b16e10ca6221299b3b1b21c197ff13cd5df9f038e307673aea8b";
        const std::string levelOneHash="64c155482b5c3886de5a0669c661d3b38e4d0c9ce5dfa713bad362ffe4511082";
        const std::string rungHash="3cacd1c5c3dd2059a018c475192657ec0bb4e4c600074a5fbfb657ea611cefbc";
        const std::vector<SelectedCatalogStore::Request> levelOne{{"fg:item:000001",levelOneHash},{"fg:item:000002",baseHash}};
        SelectedCatalogStore store(base,paths(resources));
        check(store.requiredOwners(levelOne)==std::vector<std::string>({"representative-controls","level001-extension"}),"Finite exact owner resolution includes Level1 replacement");
        check(store.cachedOwnerNames().empty()&&store.preparedOwnerNames().empty(),"Construction performs no eager loading");
        auto badPaths=paths(resources);badPaths.pop_back();
        refused([&]{SelectedCatalogStore bad(base,badPaths);},"Partial prefix vector refused");
        badPaths=paths(resources);std::swap(badPaths[0],badPaths[1]);
        refused([&]{SelectedCatalogStore bad(base,badPaths);},"Reordered owner paths refused");
        refused([&]{store.requiredOwners({{"fg:item:000001",levelOneHash},{"fg:item:000001",baseHash}});},"Conflicting duplicate identity refused");
        refused([&]{store.requiredOwners({{"fg:item:000001","not-a-hash"}});},"Malformed package identity refused");
        const auto start=std::chrono::steady_clock::now();
        const auto selected=store.prepare(levelOne);
        const auto loadedSeconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        check(selected&&selected->lessons().size()==120,"Base plus complete108-case Level1 selected scope");
        check(store.lastPreparation().loadedOwners==2&&store.lastPreparation().memoryCacheHits==0,"Cold memory scope records two complete owner loads");
        check(store.preparedOwnerNames()==store.requiredOwners(levelOne),"Published owner names match requested subset");
        const auto reference=fathom::lesson::InstalledCatalogFixtureAccess::levelOneWithControls(resources);
        for(const auto& lesson:reference->lessons())sameLesson(*selected,*reference,lesson.id);
        check(selected->admit("fg:item:000001","fg:variant:007478")->identity()==reference->admit("fg:item:000001","fg:variant:007478")->identity(),"Full48 runtime admission identity unchanged");
        check(selected->admit("fg:item:000002","fg:variant:000006")->sourceBinding()==reference->admit("fg:item:000002","fg:variant:000006")->sourceBinding(),"Retained base runtime source binding unchanged");
        refused([&]{selected->admit("fg:item:000001","fg:variant:000001");},"Historical Level1 timing refusal retained");
        const auto beforeRevision=store.revision();const auto warmStart=std::chrono::steady_clock::now();
        const auto warm=store.prepare(levelOne);
        const auto warmSeconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-warmStart).count();
        check(warm==selected&&store.revision()==beforeRevision,"Warm request returns same immutable union after byte recheck");
        check(store.lastPreparation().loadedOwners==0&&store.lastPreparation().memoryCacheHits==2&&store.lastPreparation().recheckedAssets>0&&store.lastPreparation().recheckedBytes>0,"Warm memory hit explicitly includes fresh hash work");
        const auto rung=store.prepare({{"fg:item:001141",rungHash}});
        const auto rungReference=Catalog::load(base,resources/"rung02-extension");
        sameLesson(*rung,*rungReference,"fg:item:001141");
        check(rung->lessons().size()==14&&!rung->isInstalledExtension("fg:item:000001"),"New selected scope omits unrelated cached Level1 owner");
        check(rung->admit("fg:item:001141","fg:variant:007404")->identity()==rungReference->admit("fg:item:001141","fg:variant:007404")->identity(),"Selected narrow Rung02 admission identity unchanged");
        const auto both=store.prepare({{"fg:item:001141",rungHash},{"fg:item:000001",levelOneHash}});
        check(both->lessons().size()==121&&store.lastPreparation().loadedOwners==0&&store.lastPreparation().memoryCacheHits==3,"Visited owners combine without repeated model validation");
        refused([&]{store.prepare({{"fg:item:000001",baseHash}});},"Overlapping Level1 cannot substitute base package identity");
        refused([&]{store.prepare({{"fg:item:999999",baseHash}});},"Unknown item cannot be discovered from installed files");
        check(store.preparedOwnerNames().empty(),"Failed request leaves no current prepared scope");

        Scratch scratch;
        // Only two explicitly owned bundles are copied. All other compiled
        // paths intentionally remain absent: small volume loading needs no
        // unrelated catalog or gate files.
        fs::copy(base,scratch.path/"representative-controls",fs::copy_options::recursive);
        fs::copy(resources/"level001-extension",scratch.path/"level001-extension",fs::copy_options::recursive);
        SelectedCatalogStore privateStore(scratch.path/"representative-controls",paths(scratch.path));
        check(!privateStore.prepare(levelOne,[&]{return privateStore.cachedOwnerNames().size()==1;}),"Cancellation before selected owner preserves no publication");
        check(privateStore.cachedOwnerNames()==std::vector<std::string>({"representative-controls"})&&privateStore.preparedOwnerNames().empty(),"Canceled request retains only complete verified base snapshot");
        check(!privateStore.prepare(levelOne,[&]{return privateStore.cachedOwnerNames().size()==2;}),"Cancellation after owner load prevents stale union publication");
        check(privateStore.cachedOwnerNames().size()==2&&privateStore.preparedOwnerNames().empty(),"Completed private owner survives cancellation without a fake publication");
        const auto restored=privateStore.prepare(levelOne);
        check(restored&&privateStore.lastPreparation().loadedOwners==0&&privateStore.lastPreparation().memoryCacheHits==2,"Canceled complete work reuses verified models after fresh byte checks");
        const auto manifestPath=scratch.path/"level001-extension"/"manifest.json";
        const auto manifest=fathom::json::parse(fathom::content::readBounded(manifestPath,1024*1024));
        const auto planRelative=manifest.object().at("entries").object().at("empty_resource_plan").string();
        const auto planPath=scratch.path/"level001-extension"/planRelative;
        const auto original=fathom::content::readBounded(planPath,1024*1024);const auto originalTime=fs::last_write_time(planPath);
        auto mutation=original;mutation[0]=mutation[0]=='{'?'[':'{';write(planPath,mutation);fs::last_write_time(planPath,originalTime);
        refused([&]{privateStore.prepare(levelOne);},"Cached asset changed at same path/size/mtime is refused");
        check(privateStore.preparedOwnerNames().empty()&&privateStore.cachedOwnerNames()==std::vector<std::string>({"representative-controls"}),"Changed owner evicted; no failed cache or published scope remains");
        write(planPath,original);fs::last_write_time(planPath,originalTime);
        check(privateStore.prepare(levelOne)&&privateStore.lastPreparation().loadedOwners==1,"Restoring exact bytes recovers through complete validation, not cached failure");
        const auto oldManifest=fathom::content::readBounded(manifestPath,1024*1024);write(manifestPath,oldManifest+" ");
        refused([&]{privateStore.prepare(levelOne);},"Cached manifest drift refused");write(manifestPath,oldManifest);
        const auto held=scratch.path/"held-resource-plan.json";fs::rename(planPath,held);
        refused([&]{privateStore.prepare(levelOne);},"Missing requested asset refused");fs::rename(held,planPath);
        fs::rename(planPath,held);fs::create_symlink(held,planPath);
        refused([&]{privateStore.prepare(levelOne);},"Requested asset symlink refused");fs::remove(planPath);fs::rename(held,planPath);
        const auto extra=scratch.path/"level001-extension"/"unreviewed-extra.json";write(extra,"{}");
        refused([&]{privateStore.prepare(levelOne);},"Unexpected selected bundle file refused");fs::remove(extra);
        const auto escaped=scratch.path/"escape";fs::create_directory_symlink(resources,escaped);
        SelectedCatalogStore symlinkStore(escaped/"representative-controls",paths(escaped));
        refused([&]{symlinkStore.prepare({});},"Symlinked installed root refused");
        SelectedCatalogStore absent(scratch.path/"absent"/"representative-controls",paths(scratch.path/"absent"));
        check(!absent.prepare(levelOne,[]{return true;})&&absent.cachedOwnerNames().empty(),"Immediate cancellation touches no missing bundle");
        std::cout<<"PASS "<<checks<<" selected catalog checks; selected-load-seconds="<<loadedSeconds<<" memory-warm-rechecked-seconds="<<warmSeconds<<" (OS file cache uncontrolled)\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<'\n';return 1;}
}
