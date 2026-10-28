#include "content/Canonical.hpp"
#include "content/BookContextSourceCatalog.hpp"
#include "content/LearnSourceIndex.hpp"
#include "content/LearnSourceIndexPins.hpp"
#include "content/SelectedCatalogStore.hpp"
#include <fstream>
#include <iostream>

namespace {
namespace fs=std::filesystem;
using namespace fathom;
using J=json::Value;
using lesson::Catalog;
using lesson::SelectedCatalogStore;
int checks=0;
std::ofstream trace;
void check(bool okay,const char* label){
    ++checks;trace<<(okay?"PASS":"FAIL")<<'\t'<<label<<std::endl;
    if(!okay)throw std::runtime_error(label);
}
template<class F> void canceled(F operation,const char* label){
    bool stopped=false;try{operation();}catch(const content::LoadCanceled&){stopped=true;}
    check(stopped,label);
}
template<class F> std::string refusal(F operation){
    try{operation();}catch(const content::LoadCanceled&){throw;}
    catch(const std::exception& error){return error.what();}
    throw std::runtime_error("Expected the unchanged source refusal");
}
const J& at(const J& value,const char* name){return value.object().at(name);}
std::vector<fs::path> installedPaths(const fs::path& resources){
    std::vector<fs::path> result;
    for(const auto& name:Catalog::installedExtensionDirectoryNames())result.push_back(resources/name);
    return result;
}
bool sameIndex(const learn::SourceIndex& a,const learn::SourceIndex& b){
    if(a.levels().size()!=b.levels().size()||a.exercises().size()!=b.exercises().size())return false;
    for(std::size_t i=0;i<a.levels().size();++i){
        const auto& x=a.levels()[i];const auto& y=b.levels()[i];
        if(x.number!=y.number||x.title!=y.title||x.sublevels.size()!=y.sublevels.size())return false;
        for(std::size_t j=0;j<x.sublevels.size();++j){
            const auto& u=x.sublevels[j];const auto& v=y.sublevels[j];
            if(u.key!=v.key||u.label!=v.label||u.exercises!=v.exercises)return false;
        }
    }
    for(std::size_t i=0;i<a.exercises().size();++i){
        const auto& x=a.exercises()[i];const auto& y=b.exercises()[i];
        const auto& u=x.source;const auto& v=y.source;
        if(u.levelKey!=v.levelKey||u.sublevelKey!=v.sublevelKey||u.sourceExerciseKey!=v.sourceExerciseKey||
           u.sourceOrder!=v.sourceOrder||u.levelOrder!=v.levelOrder||u.indexRevision!=v.indexRevision||
           u.sourceRevision!=v.sourceRevision||u.mappingExtent!=v.mappingExtent||!(u.admission==v.admission)||
           x.label!=y.label||x.auditStatus!=y.auditStatus||x.locator!=y.locator||x.bindings.size()!=y.bindings.size())return false;
        for(std::size_t j=0;j<x.bindings.size();++j){
            const auto& p=x.bindings[j];const auto& q=y.bindings[j];
            if(p.itemId!=q.itemId||p.packageHash!=q.packageHash||p.variants!=q.variants||
               p.exact!=q.exact||p.supplemental!=q.supplemental)return false;
        }
    }
    return true;
}
bool sameLibrary(const curriculum::SourceLibrary& a,const curriculum::SourceLibrary& b){
    if(a.workbooks().size()!=b.workbooks().size())return false;
    for(std::size_t i=0;i<a.workbooks().size();++i){
        const auto& x=a.workbooks()[i];const auto& y=b.workbooks()[i];
        if(x.id!=y.id||x.label!=y.label||x.level!=y.level||x.txt!=y.txt||x.pdf!=y.pdf||
           x.txtBytes!=y.txtBytes||x.pdfBytes!=y.pdfBytes||x.txtSha256!=y.txtSha256||x.pdfSha256!=y.pdfSha256||
           x.lines!=y.lines||x.pages!=y.pages)return false;
    }
    return true;
}
bool sameContext(const curriculum::BookContextSourceCatalog& a,const curriculum::BookContextSourceCatalog& b){
    if(a.books().size()!=b.books().size())return false;
    for(std::size_t i=0;i<a.books().size();++i){
        const auto& x=a.books()[i];const auto& y=b.books()[i];
        if(x.workbookId!=y.workbookId||x.title!=y.title||x.level!=y.level||x.txtLines!=y.txtLines||
           x.pdfPages!=y.pdfPages||x.sourceUnits!=y.sourceUnits||x.snapshotAcceptedChildren!=y.snapshotAcceptedChildren||
           x.snapshotPendingChildren!=y.snapshotPendingChildren||x.sourceOnlyUnits!=y.sourceOnlyUnits||
           x.publicCardIds!=y.publicCardIds||x.sourceTasks.size()!=y.sourceTasks.size()||
           x.contextLocations.size()!=y.contextLocations.size()||x.compositeContinuations.size()!=y.compositeContinuations.size()||
           x.sourceQualifications.size()!=y.sourceQualifications.size()||a.publicInstructions(x)!=b.publicInstructions(y))return false;
        for(std::size_t j=0;j<x.sourceTasks.size();++j){
            const auto& u=x.sourceTasks[j];const auto& v=y.sourceTasks[j];
            if(u.sourceUnitOrdinal!=v.sourceUnitOrdinal||u.firstTxtLine!=v.firstTxtLine||u.lastTxtLine!=v.lastTxtLine||
               u.physicalPages!=v.physicalPages||u.qualification!=v.qualification||
               a.sourceIdentity(x,u)!=b.sourceIdentity(y,v)||a.sourceTaskLabel(x,u)!=b.sourceTaskLabel(y,v))return false;
        }
        for(std::size_t j=0;j<x.contextLocations.size();++j){
            const auto& u=x.contextLocations[j];const auto& v=y.contextLocations[j];
            if(u.kind!=v.kind||u.firstLine!=v.firstLine||u.lastLine!=v.lastLine||u.physicalPages!=v.physicalPages)return false;
        }
        for(std::size_t j=0;j<x.compositeContinuations.size();++j){
            const auto& u=x.compositeContinuations[j];const auto& v=y.compositeContinuations[j];
            if(u.physicalPage!=v.physicalPage||u.completeSourceUnits!=v.completeSourceUnits)return false;
        }
        for(std::size_t j=0;j<x.sourceQualifications.size();++j){
            const auto& u=x.sourceQualifications[j];const auto& v=y.sourceQualifications[j];
            if(u.sourceUnitOrdinal!=v.sourceUnitOrdinal||u.qualifiedFullWorkflow!=v.qualifiedFullWorkflow||
               u.physicalPages!=v.physicalPages||u.notice!=v.notice)return false;
        }
    }
    return true;
}
void sameCatalog(const Catalog& a,const Catalog& b){
    check(a.package()==b.package()&&a.validationReport()==b.validationReport()&&
          a.resourcePlan()==b.resourcePlan()&&a.contentVersion()==b.contentVersion(),
          "Uncanceled catalog preserves exact package/report/resource hashes and diagnostics");
    bool same=a.lessons().size()==b.lessons().size();
    for(std::size_t i=0;same&&i<a.lessons().size();++i){
        const auto& x=a.lessons()[i];const auto& y=b.lessons()[i];
        same=x.id==y.id&&x.title==y.title&&x.level==y.level&&x.record==y.record&&
             x.resources==y.resources&&x.variants.size()==y.variants.size();
        for(std::size_t j=0;same&&j<x.variants.size();++j){
            const auto& u=x.variants[j];const auto& v=y.variants[j];
            same=u.id==v.id&&u.label==v.label&&u.authored==v.authored&&
                 u.technicallyRenderable==v.technicallyRenderable&&u.limitations==v.limitations&&u.model&&v.model&&
                 u.model->source().preservedRecordJson==v.model->source().preservedRecordJson;
        }
    }
    check(same,"Uncanceled catalog preserves exact ordered lessons/authored variants/model records/refusals");
}
}
int main(int argc,char** argv){
    try{
        if(argc!=3)throw std::invalid_argument("Usage: source_load_cancellation_tests ABSOLUTE_APP_RESOURCES NEW_ABSOLUTE_OUTPUT");
        const fs::path resources{argv[1]},output{argv[2]};
        if(!resources.is_absolute()||!output.is_absolute()||fs::exists(output))
            throw std::invalid_argument("Resources/output must be absolute; output must be absent");
        if(!fs::create_directory(output))throw std::runtime_error("Cannot create fresh cancellation evidence directory");
        trace.open(output/"checks.tsv");if(!trace)throw std::runtime_error("Cannot retain cancellation checks");
        const auto never=[] {return false;};
        const auto missing=output/"absent";
        canceled([&]{Catalog::load(missing,[]{return true;});},"Immediate Catalog cancellation precedes missing-bundle IO");
        canceled([&]{learn::SourceIndex::load(missing,[]{return true;});},"Immediate SourceIndex cancellation precedes missing-index IO");
        canceled([&]{content::readBounded(missing,1,[]{return true;});},"Immediate bounded-reader cancellation precedes missing-file IO");

        const auto basePath=resources/"representative-controls";
        const auto plain=Catalog::load(basePath);
        std::size_t catalogCalls=0;
        const auto observed=Catalog::load(basePath,[&]{++catalogCalls;return false;});
        sameCatalog(*observed,*plain);
        check(catalogCalls>20,"Catalog load exposes checkpoints inside verified construction");
        check(observed->admit("fg:item:000002","fg:variant:000006")->identity()==
              plain->admit("fg:item:000002","fg:variant:000006")->identity(),"Uncanceled admission/source identity unchanged");
        check(refusal([&]{observed->admit("fg:item:000007","fg:variant:000040");})==
              refusal([&]{plain->admit("fg:item:000007","fg:variant:000040");}),"Uncanceled historical SlideArrival refusal unchanged");
        std::size_t installedCalls=0;
        canceled([&]{Catalog::loadInstalled(basePath,{missing},[&]{return ++installedCalls>=catalogCalls+3;});},
                 "Installed load cancels between complete base and absent next owner");
        check(installedCalls==catalogCalls+3,"Installed cancellation reached the owner boundary without inspecting next bundle");

        const auto manifest=json::parse(content::readBounded(basePath/"manifest.json",1024*1024));
        const auto& entries=at(manifest,"entries");
        const auto readEntry=[&](const char* name){return content::readBounded(basePath/at(entries,name).string(),32*1024*1024);};
        const auto decision=json::parse(readEntry("decision"));
        content::Input input{readEntry("package"),readEntry("registry"),readEntry("profile"),
            at(decision,"expectedProfile").string(),basePath};
        std::size_t validatorCalls=0;input.canceled=[&]{++validatorCalls;return false;};
        const auto report=content::validate(input);
        check(report.validReference&&report.exitCode==2&&report.report==plain->validationReport(),
              "Explicit never-canceled validator preserves complete original report, hashes and refusals");
        check(validatorCalls>20,"Validator cancellation is propagated through nested guard checkpoints");
        for(const auto point:{std::size_t{2},validatorCalls/2}){
            std::size_t calls=0;bool returned=false;input.canceled=[&]{return ++calls>=point;};
            canceled([&]{const auto partial=content::validate(input);(void)partial;returned=true;},
                     "Canceled validator escapes nested diagnostics without returning partial Result");
            check(!returned&&calls==point,"Cancellation never becomes INPUT_FAILURE or fabricated validation completion");
        }
        input.canceled={};input.expectedProfileSha256=std::string(64,'0');
        const auto refusedDefault=content::validate(input);input.canceled=never;
        const auto refusedObserved=content::validate(input);
        check(!refusedDefault.validReference&&refusedDefault.exitCode==1&&refusedDefault.report==refusedObserved.report,
              "Never-canceled invalid-input refusal/report is byte-equivalent to default validation");

        const std::string baseHash="0ecd2b1466a7b16e10ca6221299b3b1b21c197ff13cd5df9f038e307673aea8b";
        const std::string rungHash="3cacd1c5c3dd2059a018c475192657ec0bb4e4c600074a5fbfb657ea611cefbc";
        const std::vector<SelectedCatalogStore::Request> baseRequest{{"fg:item:000002",baseHash}};
        const std::vector<SelectedCatalogStore::Request> rungRequest{{"fg:item:001141",rungHash}};
        SelectedCatalogStore cold(basePath,installedPaths(resources));std::size_t coldCalls=0;
        check(!cold.prepare(baseRequest,[&]{return ++coldCalls>=20;}),"Canceled cold selected load publishes no catalog");
        check(cold.lastPreparation().canceled&&cold.cachedOwnerNames().empty()&&cold.preparedOwnerNames().empty()&&cold.revision()==0,
              "Interrupted owner is never cached or counted as a prepared revision");
        const auto original=cold.prepare(baseRequest);const auto revision=cold.revision();const auto owners=cold.preparedOwnerNames();
        sameCatalog(*original,*plain);
        std::size_t warmCalls=0;
        check(!cold.prepare(baseRequest,[&]{return ++warmCalls>=5;}),"Cancellation inside fresh cache verification returns no scope");
        check(cold.lastPreparation().canceled&&cold.preparedOwnerNames()==owners&&cold.revision()==revision&&
              cold.cachedOwnerNames()==std::vector<std::string>{"representative-controls"},
              "Canceled verification retains existing prepared owner/revision and complete cache");
        check(cold.prepare(baseRequest)==original,"Original prepared pointer survives cancel and full fresh recheck");
        check(!cold.prepare(rungRequest,[&]{return cold.cachedOwnerNames().size()==2;}),
              "Cancellation after new owner validates prevents union publication");
        check(cold.lastPreparation().canceled&&cold.cachedOwnerNames().size()==2&&
              cold.preparedOwnerNames()==owners&&cold.revision()==revision,
              "Only complete new owner is retained; prior prepared scope/revision unchanged");
        const auto recovered=cold.prepare(rungRequest);
        check(recovered&&recovered->lessons().size()==14&&cold.lastPreparation().loadedOwners==0&&
              cold.lastPreparation().memoryCacheHits==2&&cold.lastPreparation().recheckedAssets>0,
              "Recovery rechecks current bytes and reuses validated owners before publishing new scope");
        const auto reference=Catalog::load(basePath,resources/"rung02-extension");
        check(recovered->lesson("fg:item:001141").record==reference->lesson("fg:item:001141").record&&
              recovered->variant("fg:item:001141","fg:variant:007404").authored==reference->variant("fg:item:001141","fg:variant:007404").authored&&
              recovered->admit("fg:item:001141","fg:variant:007404")->identity()==reference->admit("fg:item:001141","fg:variant:007404")->identity(),
              "Recovered selected extension preserves exact record/authored/admission provenance");

        const auto indexPath=resources/"learn-source-index";
        const auto indexBytes=content::readBounded(indexPath/"index.json",4*1024*1024);
        const auto exerciseBytes=content::readBounded(indexPath/"exercises.jsonl",32*1024*1024);
        const auto overlayBytes=content::readBounded(indexPath/"accepted-overlay.json",1024*1024);
        const auto index=learn::SourceIndex::parse(indexBytes,exerciseBytes,overlayBytes,learn::installedSourceIndexPins);
        std::size_t indexCalls=0;
        const auto counted=learn::SourceIndex::parse(indexBytes,exerciseBytes,overlayBytes,learn::installedSourceIndexPins,
            [&]{++indexCalls;return false;});
        check(indexCalls>index.exercises().size()&&sameIndex(counted,index),
              "Never-canceled SourceIndex preserves every ordered source/provenance/binding field");
        for(const auto point:{std::size_t{109},indexCalls/2,indexCalls}){
            std::size_t calls=0;bool returned=false;
            canceled([&]{const auto partial=learn::SourceIndex::parse(indexBytes,exerciseBytes,overlayBytes,learn::installedSourceIndexPins,
                [&]{return ++calls>=point;});(void)partial;returned=true;},"Cancellation before row/during rows/before publication returns no SourceIndex");
            check(!returned&&calls==point,"SourceIndex cancellation stops at deterministic checkpoint without partial completion");
        }
        check(refusal([&]{learn::SourceIndex::parse(indexBytes+" ",exerciseBytes,overlayBytes,learn::installedSourceIndexPins);})==
              refusal([&]{learn::SourceIndex::parse(indexBytes+" ",exerciseBytes,overlayBytes,learn::installedSourceIndexPins,never);}),
              "Never-canceled SourceIndex retains exact source-hash drift refusal");
        canceled([&]{curriculum::SourceLibrary::load(missing,[]{return true;});},
                 "Immediate SourceLibrary cancellation precedes missing-library IO");
        const auto library=curriculum::SourceLibrary::load(resources/"source-library");
        std::size_t libraryCalls=0;
        const auto libraryObserved=curriculum::SourceLibrary::load(resources/"source-library",[&]{++libraryCalls;return false;});
        check(libraryCalls>210&&sameLibrary(libraryObserved,library),
              "Never-canceled library preserves all105 ordered original TXT/PDF pairs and hash/locator fields");
        check(library.instructions(library.workbooks().front())==libraryObserved.instructions(libraryObserved.workbooks().front())&&
              library.instructions(library.workbooks().back())==libraryObserved.instructions(libraryObserved.workbooks().back()),
              "Original source text remains exact and owned after cancellable construction");
        for(const auto point:{std::size_t{20},libraryCalls/2,libraryCalls}){
            std::size_t calls=0;bool returned=false;
            canceled([&]{const auto partial=curriculum::SourceLibrary::load(resources/"source-library",
                [&]{return ++calls>=point;});(void)partial;returned=true;},
                "Canceled asset/file-set/book construction never returns partial SourceLibrary");
            check(!returned&&calls==point,"SourceLibrary cancellation acknowledges exact checkpoint before publication");
        }
        canceled([&]{curriculum::BookContextSourceCatalog::load(missing,library,[]{return true;});},
                 "Immediate BookContext cancellation precedes missing-context IO");
        const auto context=curriculum::BookContextSourceCatalog::load(resources/"book-context105",library);
        std::size_t contextCalls=0;
        const auto contextObserved=curriculum::BookContextSourceCatalog::load(resources/"book-context105",libraryObserved,
            [&]{++contextCalls;return false;});
        check(contextCalls>7321&&sameContext(contextObserved,context),
              "Never-canceled context preserves105 books, all7321 task identities/locators and public instructions");
        for(const auto point:{std::size_t{10},contextCalls/2,contextCalls}){
            std::size_t calls=0;bool returned=false;
            canceled([&]{const auto partial=curriculum::BookContextSourceCatalog::load(resources/"book-context105",library,
                [&]{return ++calls>=point;});(void)partial;returned=true;},
                "Canceled context file/task/book construction never returns partial BookContext");
            check(!returned&&calls==point,"BookContext cancellation acknowledges exact checkpoint before publication");
        }
        check(refusal([&]{curriculum::SourceLibrary::load(missing);})==
              refusal([&]{curriculum::SourceLibrary::load(missing,never);})&&
              refusal([&]{curriculum::BookContextSourceCatalog::load(missing,library);})==
              refusal([&]{curriculum::BookContextSourceCatalog::load(missing,library,never);}),
              "Never-canceled source readers preserve missing-resource refusal boundaries");
        const auto summary=J::Object{{"status","PASS"},{"checks",J::fromInteger(checks)},
            {"catalog_checkpoints",J::fromInteger(static_cast<std::int64_t>(catalogCalls))},
            {"validator_checkpoints",J::fromInteger(static_cast<std::int64_t>(validatorCalls))},
            {"index_checkpoints",J::fromInteger(static_cast<std::int64_t>(indexCalls))},
            {"library_checkpoints",J::fromInteger(static_cast<std::int64_t>(libraryCalls))},
            {"context_checkpoints",J::fromInteger(static_cast<std::int64_t>(contextCalls))},
            {"source_rows_compared",J::fromInteger(static_cast<std::int64_t>(index.exercises().size()))},
            {"gui_launches",J::fromInteger(0)},{"acceptance_increment",J::fromInteger(0)}};
        std::ofstream saved(output/"summary.json");saved<<json::stringify(summary)<<'\n';if(!saved)throw std::runtime_error("Cannot retain cancellation summary");
        std::cout<<"PASS "<<checks<<" source-load cancellation/parity checks; no GUI or acceptance change\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<'\n';return 1;}
}
