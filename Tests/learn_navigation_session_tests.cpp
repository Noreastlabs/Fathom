// Real Home/Lesson/Practice/ProfileStore integration. Only output device I/O is substituted.
#define main retained_shared_audio_campaign_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include "content/LearnSourceIndex.hpp"
#include "content/LearnSourceAdmission.hpp"
#include "progression/ProgressionAdapter.hpp"
#include <cmath>
#include <set>
#include "desktop/CurriculumBrowseHierarchy.hpp"
#include "desktop/LessonSelectionLabel.hpp"
#include "installed_catalog_fixture_access.hpp"

// Observe coordinator ownership and perturb returned receipts, never storage rows or capture facts.
namespace fathom::desktop {
struct GuidedSessionViewTestAccess {
    static bool hasNoPlan(const GuidedSessionView& view){return view.planValue_.null();}
};
struct LearnNavigationTestAccess {
    static void resumeHomeDetour(HomeView& h){if(!h.learnButton.onClick)throw std::runtime_error("Resume Learn callback missing");h.learnButton.onClick();}
    static bool homeDetour(const HomeView& h){return h.homeLearnDetour_;}
    static const navigation::ExerciseQueue* ownedQueue(const HomeView& h){return h.learnQueue_;}
    static bool boardSetupReady(const HomeView& h){return h.setupPreferences_.hasProfile()&&h.setupPreferences_.ready()&&!h.setupRestorePending_&&h.presentationReadyForSetup();}
    static bool setupDirty(const HomeView& h){return h.setupPreferences_.dirty();}
    static bool boardDeferred(const HomeView& h){return h.boardSaveRequested_;}
    static bool boardPending(const HomeView& h){return h.setupPreferences_.inFlight();}
    static std::optional<std::int64_t> boardRevision(const HomeView& h){return h.setupPreferences_.observedRevision();}

    static const navigation::ExerciseQueue* sourceQueue(const LessonView& view){return view.exerciseQueue_.get();}
    static std::string catalogLoadState(const LessonView& v){return " diagnostic="+v.diagnostic_+" catalog="+(v.catalog_?"present":"absent")+" retainedPlan="+(v.hasRetainedSourcePlan()?"yes":"no")+" activeQueue="+(v.sourceQueueActive()?"yes":"no");}
    static juce::String sourceBreadcrumb(const LessonView& view){return view.sourceBreadcrumb_.getText();}
    static bool beginFastLearn(HomeView& h,const std::filesystem::path& resources,const std::vector<std::filesystem::path>& extensions){return h.beginLearnIndexLoading(resources,extensions);}
    static std::shared_ptr<lesson::SelectedCatalogStore> selectedStore(const HomeView& h){return h.selectedCatalogStore_;}
    static void configureFiniteSelectedFixture(HomeView& h,const std::filesystem::path& resources){
        std::vector<std::filesystem::path> exactExtensions;
        for(const auto& name:lesson::Catalog::installedExtensionDirectoryNames())exactExtensions.push_back(resources/name);
        h.selectedCatalogStore_=std::make_shared<lesson::SelectedCatalogStore>(resources/"representative-controls",std::move(exactExtensions));
    }
    static bool beginSelected(HomeView& h,const std::vector<lesson::SelectedCatalogStore::Request>& requests,std::uint64_t group){return h.beginSelectedCatalogLoading(requests,group);}
    static bool beginSelectedGuided(HomeView& h,const std::filesystem::path& resources,const std::vector<std::filesystem::path>& extensions){return h.beginGuidedSelectionLoading(resources,extensions);}
    static bool selectedActivity(HomeView& h,const std::string& source){return h.beginLearnActivityLoading(source);}
    static bool beginLearn(HomeView& h,const std::filesystem::path& resources,
                           const std::vector<std::filesystem::path>& extensions,
                           const std::vector<source_routes::Family>& families,std::function<void()> beforeCatalog={}){
        return h.beginLearnLoading(resources,extensions,families,std::move(beforeCatalog));
    }
    static bool loading(const HomeView& h){return h.learnLoadTicket_!=nullptr;}
    static bool presentationReady(const HomeView& h){return h.presentation_.hasProfile()&&h.presentation_.state()==presentation::PreferenceState::Ready;}
    static GuidedSessionView& guided(HomeView& h){return h.guidedView;}
    static bool beginGuided(HomeView& h,const std::filesystem::path& resources,const std::vector<std::filesystem::path>& extensions,std::function<void()> beforeCatalog={}){
        return h.beginGuidedLoading(resources,extensions,std::move(beforeCatalog));
    }
    static bool beginBook(HomeView& h,const std::filesystem::path& resources,const std::vector<std::filesystem::path>& extensions,const std::string& book,std::function<void()> beforeCatalog={}){
        return h.beginWorkbookLoading(resources,extensions,book,std::move(beforeCatalog));
    }
    static std::size_t recipes(const HomeView& h){return h.recipeTaskRegistry_?h.recipeTaskRegistry_->size():0;}
    static bool manual(const HomeView& h,const std::string& source){return h.manualTaskRegistry_&&h.manualTaskRegistry_->contains(source);}
    static SourceLibraryView& browser(HomeView& h){return h.sourceLibraryView;}
    static void browse(HomeView& h,const std::filesystem::path& resources){
        if(!h.navigate(HomeView::Page::SourceLibrary))throw std::runtime_error("Browse navigation refused");
        h.sourceLibraryView.beginBrowse(resources/"source-library");
    }
    static void prepare(HomeView& h,const std::filesystem::path& resources,const std::string& source){
        const juce::Component::SafePointer<HomeView> owner{&h};
        h.sourceLibraryView.prepareActivity(source,[owner,resources,source](const SourceLibraryView::LoadTicket& ticket){
            auto gates=std::make_shared<SourceTaskLibraries>();gates->loadSelected(resources,ticket,source);
            return [owner,gates]{if(owner)owner->SourceTaskLibraries::merge(std::move(*gates));};
        },[]{return false;}); // Verify the production gate without beginning a task.
    }
    static void indexLoaded(HomeView& h) { h.learnIndexLoaded_=true; }
    static bool owned(const HomeView& h) { return h.learnQueue_!=nullptr; }
    static bool pending(const HomeView& h) { return h.learnFuture_.has_value(); }
    static bool pendingLearnEntry(const HomeView& h) { return h.pendingLearnEntry_; }
    static std::size_t position(const HomeView& h) { return h.learnQueue_?h.learnQueue_->position():999; }
    static std::string retained(const HomeView& h) {
        return storage::canonical(json::Value::Object{{"operation",h.learnOperation_},{"at",h.learnAt_},
            {"session",h.learnSession_},{"outcome",h.learnOutcome_},{"plan",h.learnPlan_}});
    }
    static bool retry(HomeView& h,std::string& reason) { return h.retryLearnQueue(reason); }
    static bool next(HomeView& h,std::string& reason) { return h.advanceLearnQueue(reason); }
    static storage::Reply takeReply(HomeView& h) {
        if(!h.learnFuture_||h.learnFuture_->wait_for(std::chrono::seconds(7))!=std::future_status::ready)
            throw std::runtime_error("Learn original reply watchdog");
        auto result=h.learnFuture_->get();h.learnFuture_.reset();return result;
    }
    static void deliver(HomeView& h,storage::Reply reply) {
        std::promise<storage::Reply> promise;auto future=promise.get_future();promise.set_value(std::move(reply));
        h.learnFuture_.emplace(std::move(future),h.learnOperation_,h.learnSession_);h.serviceLearnQueue();
    }
};
struct SourceBrowseTestAccess {
    static std::string firstIdentity(const SourceLibraryView& v,int level){const auto& book=v.context_->book(level);return v.context_->sourceIdentity(book,book.sourceTasks.front());}
    static int recipeRow(const SourceLibraryView& v){
        for(std::size_t i=0;i<v.taskRows_.size();++i){const auto& row=v.taskRows_[i];const auto& book=v.context_->book(row.level);
            if(source_routes::familyFor(v.context_->sourceIdentity(book,book.sourceTasks[row.task]))==source_routes::Family::Recipe)return static_cast<int>(i);}
        return -1;
    }
    static std::string selectedIdentity(const SourceLibraryView& v){
        const auto* task=v.selectedSourceTask();const auto* book=v.selectedWorkbook();
        return task&&book&&v.context_?v.context_->sourceIdentity(v.context_->book(book->level),*task):std::string{};
    }
    static bool theoryAttempted(const SourceLibraryView& v){return v.theoryInitializationAttempted_;}
    static std::size_t available(const SourceLibraryView& v){
        std::size_t count=0;
        if(v.context_&&v.onManualTaskAvailable)for(const auto& book:v.context_->books())for(const auto& task:book.sourceTasks)
            if(v.onManualTaskAvailable(v.context_->sourceIdentity(book,task)))++count;
        return count;
    }
};
}
using L=desktop::LearnNavigationTestAccess;
namespace {
juce::Component* recursiveId(juce::Component& root,const std::string& id) {
    if(root.getComponentID().toStdString()==id)return &root;
    for(auto* c:root.getChildren())if(auto* found=recursiveId(*c,id))return found;
    return nullptr;
}
juce::Button* recursiveButton(juce::Component& root,const std::string& name) {
    if(auto* b=dynamic_cast<juce::Button*>(&root);b&&b->getButtonText().toStdString()==name&&b->isVisible())return b;
    for(auto* c:root.getChildren())if(c->isVisible())if(auto* found=recursiveButton(*c,name))return found;
    return nullptr;
}
template<class T>T& control(juce::Component& root,const std::string& id) {
    auto* p=dynamic_cast<T*>(recursiveId(root,id));if(!p)throw std::runtime_error("Missing control "+id);return *p;
}
void pressId(juce::Component& root,const std::string& id) {
    auto& b=control<juce::Button>(root,id);if(!b.isVisible()||!b.isEnabled())throw std::runtime_error("Unusable control "+id);activate(b);
}
void pressName(juce::Component& root,const std::string& name) {
    auto* b=recursiveButton(root,name);if(!b||!b->isEnabled())throw std::runtime_error("Unusable button "+name);activate(*b);
}
void choose(juce::Component& root,const std::string& id,int choice) {
    auto& c=control<juce::ComboBox>(root,id);if(!c.isVisible()||!c.isEnabled()||c.indexOfItemId(choice)<0)throw std::runtime_error("Unavailable choice "+id);c.setSelectedId(choice,juce::sendNotificationSync);
}
std::string decodeBlob(const json::Value& value) {
    const auto hex=value.object().at("blob_hex").string();std::string bytes;
    for(std::size_t i=0;i<hex.size();i+=2)bytes+=static_cast<char>(std::stoul(hex.substr(i,2),nullptr,16));return bytes;
}
}
int main(int argc,char** argv) { int checks=0;try {
    const bool singletonSaveQuit=argc==4&&std::string(argv[3])=="--singleton-board-savequit-regression";
    const bool suiteOnly=argc==4&&std::string(argv[3])=="--suite-auto-regression";
    const bool shutdownOnly=argc==4&&std::string(argv[3])=="--shutdown-prepared-regression";
    const bool shutdownActiveOnly=argc==4&&(std::string(argv[3])=="--shutdown-active-regression"||singletonSaveQuit);
    const bool quitOnly=argc==4&&(std::string(argv[3])=="--quit-regression"||shutdownActiveOnly);
    const bool focusOnly=argc==4&&std::string(argv[3])=="--focus-regression";
    const bool shortcutOnly=argc==4&&std::string(argv[3])=="--shortcut-regression";
    const bool entryOnly=argc==4&&std::string(argv[3])=="--focus-entry-regression";
    const bool nextFocusOnly=argc==4&&std::string(argv[3])=="--queue-next-focus-regression";
    const bool browseOnly=argc==4&&std::string(argv[3])=="--browse-regression";
    const bool learnLoadingOnly=argc==4&&std::string(argv[3])=="--learn-loading-regression";
    const bool readinessOnly=argc==4&&std::string(argv[3])=="--learn-readiness-regression";
    const bool inspectorWordingOnly=argc==4&&std::string(argv[3])=="--inspector-wording-regression";
    const bool preparationTimingOnly=argc==4&&std::string(argv[3])=="--preparation-timing";
    const bool phaseFailureRetryOnly=argc==4&&std::string(argv[3])=="--learn-phase-failure-retry-regression";
    const bool exactSelectionOnly=argc==4&&std::string(argv[3])=="--exact-selection-regression";
    const bool selectedLoadingVisual=argc==4&&std::string(argv[3])=="--selected-loading-visual-regression";
    const bool selectedLoadingOnly=argc==4&&(std::string(argv[3])=="--selected-loading-regression"||selectedLoadingVisual);
    const bool guidedBackSummaryOnly=argc==4&&std::string(argv[3])=="--guided-back-summary-regression";
    if(argc!=3&&!suiteOnly&&!shutdownOnly&&!quitOnly&&!focusOnly&&!shortcutOnly&&!entryOnly&&!nextFocusOnly&&!browseOnly&&!learnLoadingOnly&&!readinessOnly&&!exactSelectionOnly&&!guidedBackSummaryOnly&&!inspectorWordingOnly&&!preparationTimingOnly&&!phaseFailureRetryOnly&&!selectedLoadingOnly)throw std::runtime_error("Expected installed resource directory and new absolute evidence directory [regression mode]");
    const std::filesystem::path resources=argv[1],out=argv[2];
    if(!resources.is_absolute()||!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Absolute resource path and absent evidence directory required");
    std::filesystem::create_directories(out);
    if(preparationTimingOnly){
        // One direct-API measurement, before any GUI, profile, Harness or peer.
        // Each stage includes its required I/O, hashes, parsing and validation;
        // neither cold-disk latency nor UI publication is claimed.
        json::Value::Object stages;
        auto measured=[&](const char* name,auto operation){
            std::cout<<"PREPARATION stage="<<name<<" outcome=started"<<std::endl;
            const auto begin=std::chrono::steady_clock::now();
            auto value=operation();
            const auto microseconds=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-begin).count();
            stages.emplace(name,json::Value::fromInteger(microseconds));
            std::cout<<"PREPARATION stage="<<name<<" elapsed_microseconds="<<microseconds<<std::endl;
            return value;
        };
        const auto index=measured("SourceIndex",[&]{return learn::SourceIndex::load(resources/"learn-source-index");});
        const auto names=lesson::Catalog::installedExtensionDirectoryNames();
        std::vector<std::filesystem::path> extensions;
        for(const auto& name:names)extensions.push_back(resources/name);
        const auto catalog=measured("Catalog",[&]{return lesson::Catalog::loadInstalled(resources/"representative-controls",extensions);});
        // Compare one mixed selective scope with the full catalog already loaded.
        // Public source/projection fields are compared directly: no extra full
        // load, GUI, profile, device action or private model serializer is used.
        json::Value::Array selectiveChecks;
        const auto parityCheck=[&](bool ok,const std::string& name){
            ++checks;
            selectiveChecks.emplace_back(json::Value::Object{{"check",name},{"pass",ok}});
            std::cout<<"SELECTIVE_FULL check="<<name<<" outcome="<<(ok?"PASS":"FAIL")<<std::endl;
            if(!ok)throw std::runtime_error("Selective/full parity: "+name);
        };
        const std::vector<std::pair<std::string,std::string>> mixedChoices{
            {"fg:item:000002","fg:variant:000006"},
            {"fg:item:000014","fg:variant:007480"},
            {"fg:item:000445","fg:variant:003287"}};
        std::vector<lesson::SelectedCatalogStore::Request> mixedRequests;
        for(const auto& choice:mixedChoices){
            const auto admitted=catalog->admit(choice.first,choice.second);
            mixedRequests.push_back({choice.first,admitted->identity().object().at("package_sha256").string()});
        }
        lesson::SelectedCatalogStore selectedStore(resources/"representative-controls",extensions);
        const std::vector<std::string> expectedOwners{
            "representative-controls","level001-extension","level004-ex002-extension"};
        parityCheck(selectedStore.requiredOwners(mixedRequests)==expectedOwners,"exact mixed compiled owners include secondary Level1 item and late Level4 owner");
        const auto selected=measured("SelectedMixedScope",[&]{return selectedStore.prepare(mixedRequests);});
        parityCheck(selected&&selectedStore.preparedOwnerNames()==expectedOwners,"mixed scope publishes only required owners");
        std::set<std::string> expectedItems;
        for(const auto& item:catalog->lessons())if(!catalog->isInstalledExtension(item.id))expectedItems.insert(item.id);
        const auto& descriptors=lesson::installedExtensionDescriptors();
        for(const auto owner:{"level001-extension","level004-ex002-extension"}){
            const auto descriptor=std::find_if(descriptors.begin(),descriptors.end(),[&](const auto& value){return std::string(value.directory)==owner;});
            if(descriptor==descriptors.end())throw std::runtime_error("Expected mixed owner is absent from compiled registry");
            expectedItems.insert(descriptor->item);
            for(const auto& item:descriptor->additionalCases)expectedItems.insert(item.item);
        }
        std::vector<std::string> actualOrder,expectedOrder;
        for(const auto& item:selected->lessons())actualOrder.push_back(item.id);
        for(const auto& item:catalog->lessons())if(expectedItems.count(item.id))expectedOrder.push_back(item.id);
        parityCheck(actualOrder==expectedOrder&&actualOrder.size()==expectedItems.size(),"selected membership and order match full catalog with unrelated owners omitted");
        parityCheck(selected->isInstalledExtension("fg:item:000001")&&selected->isInstalledExtension("fg:item:000014")&&!selected->isInstalledExtension("fg:item:000002"),"Level1 replaces exactly its base item while retained base ownership remains");
        const auto sameDegrees=[](const std::vector<music::Degree>& a,const std::vector<music::Degree>& b){
            if(a.size()!=b.size())return false;
            for(std::size_t i=0;i<a.size();++i)
                if(a[i].context!=b[i].context||a[i].sourceLabel!=b[i].sourceLabel||a[i].rootPitchClass!=b[i].rootPitchClass||a[i].ordinal!=b[i].ordinal||a[i].alteration!=b[i].alteration||a[i].rootMidi!=b[i].rootMidi)return false;
            return true;
        };
        const auto samePublicModel=[&](const music::ValidatedModel& a,const music::ValidatedModel& b){
            const auto& x=a.source();const auto& y=b.source();
            // This comparison is bounded to the three reviewed picked-note
            // fixtures and their retained historical variants, without backing.
            if(x.itemId!=y.itemId||x.schemaVersion!=y.schemaVersion||x.contentVersion!=y.contentVersion||x.contentRevision!=y.contentRevision||x.sourceRefs!=y.sourceRefs||x.instrument.openMidi!=y.instrument.openMidi||x.instrument.capo!=y.instrument.capo||!(x.terminal==y.terminal)||x.preservedRecordJson!=y.preservedRecordJson||x.proposalExample!=y.proposalExample||x.syntheticFixture!=y.syntheticFixture||!x.measures.empty()||!y.measures.empty()||x.backing||y.backing||x.events.size()!=y.events.size())return false;
            for(std::size_t i=0;i<x.events.size();++i){
                const auto& e=x.events[i];const auto& f=y.events[i];
                if(e.id!=f.id||e.sourceRef!=f.sourceRef||e.chordSymbol!=f.chordSymbol||e.kind!=f.kind||!(e.span==f.span)||e.contact!=f.contact||e.handDirection!=f.handDirection||e.scopeStrings!=f.scopeStrings||e.tones.size()!=f.tones.size())return false;
                for(std::size_t j=0;j<e.tones.size();++j){
                    const auto& t=e.tones[j];const auto& u=f.tones[j];
                    if(t.string!=u.string||t.fret!=u.fret||t.midi!=u.midi||t.finger!=u.finger||t.spelling!=u.spelling||!sameDegrees(t.degrees,u.degrees)||t.attack!=u.attack||t.tieFrom!=u.tieFrom||t.authoredTechnique!=u.authoredTechnique||!(t.bendSemitones==u.bendSemitones)||t.bend||u.bend||!(t.memberSpan==u.memberSpan)||!(t.soundingSpan==u.soundingSpan))return false;
                }
            }
            const auto& xp=a.projections();const auto& yp=b.projections();
            if(xp.size()!=yp.size())return false;
            for(std::size_t i=0;i<xp.size();++i){
                const auto& e=xp[i];const auto& f=yp[i];
                if(e.eventId!=f.eventId||e.kind!=f.kind||!(e.span==f.span)||e.contact!=f.contact||e.scopeStrings!=f.scopeStrings||e.handDirection!=f.handDirection||e.tones.size()!=f.tones.size())return false;
                for(std::size_t j=0;j<e.tones.size();++j){
                    const auto& t=e.tones[j];const auto& u=f.tones[j];
                    if(t.string!=u.string||t.fret!=u.fret||t.soundingMidi!=u.soundingMidi||t.finger!=u.finger||t.spelling!=u.spelling||!sameDegrees(t.degrees,u.degrees)||t.attack!=u.attack||t.tieFrom!=u.tieFrom||!(t.soundingSpan==u.soundingSpan)||t.bend||u.bend)return false;
                }
            }
            return true;
        };
        std::size_t comparedVariants=0;
        for(const auto& choice:mixedChoices){
            const auto& item=selected->lesson(choice.first);const auto& reference=catalog->lesson(choice.first);
            parityCheck(item.id==reference.id&&item.title==reference.title&&item.level==reference.level&&item.record==reference.record&&item.resources==reference.resources&&selected->contentVersion(item.id)==catalog->contentVersion(item.id)&&item.variants.size()==reference.variants.size(),"exact record content resources and variant coverage "+item.id);
            bool authoredEqual=true,modelsEqual=true,textEqual=true,admissionEqual=true;
            for(const auto& original:reference.variants){
                ++comparedVariants;
                const auto& variant=selected->variant(item.id,original.id);
                authoredEqual=authoredEqual&&variant.id==original.id&&variant.label==original.label&&variant.authored==original.authored&&variant.technicallyRenderable==original.technicallyRenderable&&variant.limitations==original.limitations;
                modelsEqual=modelsEqual&&variant.model&&original.model&&samePublicModel(*variant.model,*original.model);
                for(const auto section:{lesson::Section::Instructions,lesson::Section::Context,lesson::Section::Assessment,lesson::Section::Resources,lesson::Section::VariantDetails})
                    textEqual=textEqual&&selected->text(item.id,original.id,section)==catalog->text(item.id,original.id,section);
                std::shared_ptr<const lesson::Admission> actualAdmission,referenceAdmission;
                try{actualAdmission=selected->admit(item.id,original.id);}catch(const std::exception&){}
                try{referenceAdmission=catalog->admit(item.id,original.id);}catch(const std::exception&){}
                admissionEqual=admissionEqual&&(static_cast<bool>(actualAdmission)==static_cast<bool>(referenceAdmission));
                if(actualAdmission&&referenceAdmission)
                    admissionEqual=admissionEqual&&actualAdmission->identity()==referenceAdmission->identity()&&actualAdmission->sourceBinding()==referenceAdmission->sourceBinding()&&actualAdmission->span()==referenceAdmission->span()&&actualAdmission->sourceStart()==referenceAdmission->sourceStart()&&actualAdmission->practiceAllowed()==referenceAdmission->practiceAllowed()&&actualAdmission->description()==referenceAdmission->description();
            }
            parityCheck(authoredEqual,"exact authored variant readiness and limitations "+item.id);
            parityCheck(modelsEqual,"exact public model source projections timing and picking "+item.id);
            parityCheck(textEqual,"exact instructions context assessment resources and details "+item.id);
            parityCheck(admissionEqual,"exact admission refusal and source identities "+item.id);
        }
        const auto rejects=[](const lesson::Catalog& scope,const std::string& item,const std::string& variant){
            try{scope.admit(item,variant);return false;}catch(const std::exception&){return true;}
        };
        const auto oldLevelOne=catalog->lesson("fg:item:000014").variants.front().id;
        parityCheck(rejects(*selected,"fg:item:000014",oldLevelOne)&&rejects(*catalog,"fg:item:000014",oldLevelOne),"secondary Level1 historical timing remains refused");
        parityCheck(rejects(*selected,"fg:item:000445","fg:variant:003286")&&rejects(*catalog,"fg:item:000445","fg:variant:003286"),"late Level4 historical accent variant remains refused");
        const auto library=measured("SourceLibrary",[&]{return curriculum::SourceLibrary::load(resources/"source-library");});
        const auto context=measured("BookContext",[&]{return curriculum::BookContextSourceCatalog::load(resources/"book-context105",library);});
        std::size_t variants=0;
        for(const auto& lesson:catalog->lessons())variants+=lesson.variants.size();
        const auto count=[](std::size_t n){return json::Value::fromInteger(static_cast<std::int64_t>(n));};
        const json::Value summary=json::Value::Object{
            {"schema","fathom.preparation-stage-timing.1"},{"stage_microseconds",stages},
            {"source_levels",count(index->levels().size())},{"source_rows",count(index->exercises().size())},
            {"registered_extensions",count(extensions.size())},{"lessons",count(catalog->lessons().size())},{"variants",count(variants)},
            {"selective_full_check_count",count(static_cast<std::size_t>(checks))},{"selective_full_checks",std::move(selectiveChecks)},
            {"selective_compared_items",count(mixedChoices.size())},{"selective_compared_variants",count(comparedVariants)},
            {"selective_scope_lessons",count(selected->lessons().size())},{"selective_scope_owners",json::Value::Array{"representative-controls","level001-extension","level004-ex002-extension"}},
            {"original_workbooks",count(library.workbooks().size())},{"context_books",count(context.books().size())},
            {"profile_actions",count(0)},{"GUI_actions",count(0)},{"physical_audio",false},{"acceptance_increment",count(0)},
            {"scope","One end-to-end call per public loader; current compiled extent; file cache state uncontrolled; not UI-ready/cold-start or curriculum acceptance evidence"}};
        std::ofstream summaryFile(out/"summary.json");
        if(!summaryFile)throw std::runtime_error("Preparation timing summary could not be opened");
        summaryFile<<storage::canonical(summary)<<'\n';summaryFile.close();
        if(!summaryFile)throw std::runtime_error("Preparation timing summary could not be written completely");
        return 0;
    }
    std::ofstream trace(out/"checks.tsv");juce::ScopedJuceInitialiser_GUI gui;
    auto ck=[&](bool ok,const std::string& text){++checks;trace<<text<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(text);};
    Harness h(out,"profile");auto& view=A::lessons(*h.home);
    if(singletonSaveQuit){
        const auto initial=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        ck(h.home->attachPresentation(*h.store,initial.data.object().at("profile_id").string()),"attach original synthetic profile controllers");
        h.wait([&]{return L::boardSetupReady(*h.home);},"setup restore ready before singleton queue");
    }

    h.wait([&]{return !L::pending(*h.home);},"fresh profile suite discovery completes before navigation");
    if(suiteOnly){
        std::vector<std::filesystem::path> finiteExtensions;
        const auto installed=lesson::Catalog::installedExtensionDirectoryNames();
        ck(installed.size()>=2,"two exact Level12 fixture extension owners available");
        finiteExtensions={resources/installed[0],resources/installed[1]};
        const auto prepare=[&](Harness& fixture){
            fixture.wait([&]{return !L::pending(*fixture.home);},"fresh profile suite discovery");
            const auto ownProfile=capture_fixture::confirmed(fixture.store->snapshot(storage::newUuid())).data.object().at("profile_id").string();
            ck(fixture.home->attachPresentation(*fixture.store,ownProfile),"board suite attaches its exact original synthetic profile and setup controller");
            fixture.wait([&]{return L::boardSetupReady(*fixture.home);},"actual setup and presentation reads restore before Learn");
            auto& lesson=A::lessons(*fixture.home);const bool loaded=lesson.load(resources/"representative-controls",finiteExtensions);ck(loaded,"load only representative base plus two Level12 admitted rung owners"+L::catalogLoadState(lesson));
            ck(lesson.loadSourceIndex(resources/"learn-source-index"),"load exact installed reviewed source index");L::indexLoaded(*fixture.home);
            ck(fixture.home->navigate(H::Page::Learn),"enter Learn without audio or Attempt");lesson.showSourceHierarchy();
            choose(lesson,"learn-source-level",12);pressName(lesson,"Open level");choose(lesson,"learn-source-sublevel",1);pressName(lesson,"Open sublevel");
            choose(lesson,"learn-source-selection-mode",2);choose(lesson,"learn-source-start",2);choose(lesson,"learn-source-stop",3);pressId(lesson,"learn-source-preview");
            pressId(lesson,"learn-queue-confirm");control<juce::TextEditor>(lesson,"learn-source-bpm").setText("300",false);pressId(lesson,"learn-queue-open");
            auto originalDefinition=L::takeReply(*fixture.home);auto foreignOwner=originalDefinition;foreignOwner.owner=storage::newUuid();
            L::deliver(*fixture.home,std::move(foreignOwner));
            ck(!fixture.practice().captureSession()->startTaken()&&fixture.practice().captureSessionId()==fixture.sessionId,"foreign confirmed suite owner cannot prepare or Start an exercise");
            std::string definitionRetry;ck(L::retry(*fixture.home,definitionRetry),"original durable suite definition retries its exact operation after foreign receipt");
            fixture.wait([&]{return fixture.home->page()==H::Page::Practice&&!L::pending(*fixture.home);},"first suite preparation after durable definition");
            ck(fixture.practice().suiteMode()&&!fixture.practice().captureSession()->startTaken(),"one confirmed suite is prepared; first Start remains explicit");
            auto& tab=fixture.practice().tabView();
            const auto active=tab.document();const auto future=tab.upcomingDocuments();
            ck(active&&active->source().itemId=="fg:item:001141"&&future.size()==1&&future.front()&&future.front()->source().itemId=="fg:item:001142", "stacked queue binds actual next admitted TAB after current admission matches");
            const auto immutableBefore=capture_fixture::confirmed(fixture.store->snapshot(storage::newUuid()));
            const auto selected=tab.selectedEvent();const auto playing=tab.playingEvents();const auto scroll=tab.scrollPosition();
            const auto originalSize=juce::Point<int>{fixture.home->getWidth(),fixture.home->getHeight()};
            for(const auto size:{juce::Point<int>{920,680},juce::Point<int>{1400,1000},originalSize})fixture.home->setSize(size.x,size.y);
            ck(tab.document()==active&&tab.upcomingDocuments()==future&&tab.selectedEvent()==selected&&tab.playingEvents()==playing, "resize preserves active and future immutable TAB pointers, selection and playback binding");
            tab.restoreScrollPosition(scroll);
            const auto immutableAfter=capture_fixture::confirmed(fixture.store->snapshot(storage::newUuid()));
            ck(immutableAfter.data.object().at("authoritative")==immutableBefore.data.object().at("authoritative"), "future presentation and resize allocate no Attempt, Session, suite member or score");
        };
        const auto startFirst=[&](Harness& fixture){
            click(fixture.practice(),"Audio settings");fixture.tick();
            if(fixture.home->audioSettings().snapshot().state==output::State::Closed){click(A::settings(*fixture.home),"Connect audio");fixture.tick();click(A::settings(*fixture.home),"Enable audio");fixture.blocks(1);}
            click(A::settings(*fixture.home),"Back to Practice");fixture.tick();click(fixture.practice(),"Start selected case");
            fixture.wait([&]{return fixture.practice().captureSession()->startTaken();},"explicit first suite Start");
        };
        bool sawAwaitingHandoff=false;
        std::set<std::string> boardItemsObserved;
        const auto inspectBoard=[&](Harness& fixture){
            auto& practice=fixture.practice();const auto admission=practice.lessonAdmission();
            if(practice.isShowing()||std::any_of(practice.playbackFretboardView().projection().begin(),practice.playbackFretboardView().projection().end(),[](const auto& c){return c.active;}))throw std::runtime_error("headless accepted output must not paint native-only board highlights");
            const auto& position=practice.tabPosition();
            if(admission&&position.hasMusicalSample&&position.progress.owner==practice.coordinator().owner()&&practice.coordinator().state()==practice::State::Running){
                const auto tones=desktop::PracticeView::soundingTonesAt(*admission->model(),practice.coordinator().timeline(practice.coordinator().owner()),position.cycle,position.sample);
                for(const auto& tone:tones){
                    if(!std::any_of(admission->model()->source().events.begin(),admission->model()->source().events.end(),[&](const auto& e){return e.id==tone.eventId;}))throw std::runtime_error("accepted sounding tone IDs must belong to current suite model, never prior item");
                    boardItemsObserved.insert(admission->model()->source().itemId);
                }
            }
        };
        const auto completeUntil=[&](Harness& fixture,auto predicate,const std::string& label){
            for(int block=0;block<16000&&!predicate();++block){platform::OutputTestAccess::block(A::output(*fixture.home));fixture.tick();inspectBoard(fixture);if(fixture.home->audioSettings().snapshot().state==output::State::Awaiting)sawAwaitingHandoff=true;if(block%16==0)pump();}
            fixture.wait(predicate,label);
        };
        for(const auto& mode:{std::string{"automatic"},std::string{"delayed-automatic"},std::string{"stopped-second-reopen"},std::string{"unused-first"}}){
            Harness fixture(out,"suite-"+mode);prepare(fixture);boardItemsObserved.clear();
            fixture.practice().setBoardDisplay({true,desktop::setup::BoardMode::Basic,desktop::setup::NoteSpelling::Sharp});
            ck(std::none_of(fixture.practice().playbackFretboardView().projection().begin(),fixture.practice().playbackFretboardView().projection().end(),[](const auto& c){return c.active;}),"prepared suite board has no premature highlights");
            const auto firstSession=fixture.practice().captureSessionId();
            if(mode=="unused-first"){
                const auto beforeHome=capture_fixture::confirmed(fixture.store->snapshot(storage::newUuid()));
                const auto retainedQueue=L::ownedQueue(*fixture.home);const auto retainedSource=fixture.practice().lessonAdmission();
                std::string homeReason;ck(fixture.home->requestHome(homeReason)&&fixture.home->page()==H::Page::Home,"safe prepared suite reaches Home without cancelling its Session");
                for(int tick=0;tick<20;++tick)fixture.tick();
                ck(L::homeDetour(*fixture.home)&&L::ownedQueue(*fixture.home)==retainedQueue&&fixture.practice().captureSessionId()==firstSession&&fixture.practice().lessonAdmission()==retainedSource&&!fixture.practice().captureSession()->startTaken(),"Home detour preserves exact queue/source/Session and never automatically Starts");
                const auto atHome=capture_fixture::confirmed(fixture.store->snapshot(storage::newUuid()));
                ck(atHome.data.object().at("authoritative")==beforeHome.data.object().at("authoritative"),"Home detour preserves all14 authority tables before Learn resume");
                L::resumeHomeDetour(*fixture.home);fixture.tick();
                ck(fixture.home->page()==H::Page::Learn&&!L::homeDetour(*fixture.home)&&L::ownedQueue(*fixture.home)==retainedQueue&&fixture.practice().captureSessionId()==firstSession&&fixture.practice().lessonAdmission()==retainedSource,"Resume Learn reuses retained selection and original Session instead of catalog replacement");
                const auto afterResume=capture_fixture::confirmed(fixture.store->snapshot(storage::newUuid()));
                ck(afterResume.data.object().at("authoritative")==beforeHome.data.object().at("authoritative"),"Learn resume adds no cancellation, Attempt, suite member, score or source mutation");

                ck(fixture.home->navigate(H::Page::Learn),"unused preparation returns to its exact queue");pressId(A::lessons(*fixture.home),"learn-queue-next");fixture.wait([&]{return !L::owned(*fixture.home)&&!L::pending(*fixture.home);},"unused Session closes without score");
                pressId(A::lessons(*fixture.home),"learn-queue-open");fixture.wait([&]{return fixture.home->page()==H::Page::Practice&&!L::pending(*fixture.home);},"next item explicitly prepared after unused skip");
                ck(!fixture.practice().captureSession()->startTaken(),"unused skip does not fabricate Start or active time");
            }
            startFirst(fixture);
            const auto activeQueue=L::ownedQueue(*fixture.home);const auto activeSource=fixture.practice().lessonAdmission();const auto activeSession=fixture.practice().captureSessionId();
            std::string activeHomeReason;ck(!fixture.home->requestHome(activeHomeReason)&&fixture.home->page()==H::Page::Practice&&!activeHomeReason.empty(),"active admitted suite refuses Home without stopping or discarding its result");
            ck(L::ownedQueue(*fixture.home)==activeQueue&&fixture.practice().lessonAdmission()==activeSource&&fixture.practice().captureSessionId()==activeSession&&fixture.practice().captureSession()->startTaken(),"Home refusal retains actual active source, queue, Session and original Start");

            const auto boardRevisionBefore=L::boardRevision(*fixture.home);
            choose(fixture.practice(),"practice-board-mode",3);
            ck(L::boardDeferred(*fixture.home)&&L::boardRevision(*fixture.home)==boardRevisionBefore&&!L::boardPending(*fixture.home),"explicit board choice deferred during active suite, no CAS dispatched");
            sawAwaitingHandoff=false;platform::OutputTestAccess::deferObservation=mode=="delayed-automatic";
            if(mode=="stopped-second-reopen"){
                const auto firstAttempt=fixture.practice().captureSession()->binding().owner;
                completeUntil(fixture,[&]{const auto* current=fixture.practice().captureSession();return fixture.practice().captureSessionId()!=firstSession&&current->phase()==capture::SessionPhase::Active&&current->startTaken()&&!current->binding().owner.empty()&&current->binding().owner!=firstAttempt&&fixture.practice().canPerformCommand(desktop::PracticeCommand::Stop);},"second exercise automatically Starts without between-item assessment");
                ck(fixture.practice().tabView().document()->source().itemId=="fg:item:001142"&&fixture.practice().tabView().upcomingDocuments().empty(), "automatic advancement promotes the real next TAB and removes it from future panels");
                ck(fixture.practice().stopSample(),"explicit Stop interrupts the actual second exercise");
                fixture.wait([&]{return fixture.practice().captureSession()->phase()==capture::SessionPhase::Review;},"stopped second result remains unsaved for explicit decision");
                ck(!fixture.practice().suiteNaturalCompleted()&&!fixture.practice().chooseAssessment("Clean"),"interrupted second result cannot be marked completed or receive intermediate score");
                ck(fixture.practice().saveSample(nullptr),"retain truthful interrupted capture without self-assessment");fixture.wait([&]{return fixture.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"explicit interrupted save");fixture.blocks(2);fixture.wait([&]{return fixture.practice().audioCanRelease();},"interrupted output cleanup");
                click(fixture.practice(),"Back");fixture.wait([&]{return fixture.home->page()==H::Page::Learn;},"Back retains original suite and stops automatic continuation");
                const auto owner=fixture.practice().captureSession()->binding().owner;for(int repeat=0;repeat<20;++repeat)fixture.tick();ck(fixture.practice().captureSession()->binding().owner==owner,"Back/repeated ticks create no replacement Attempt");
                pressId(A::lessons(*fixture.home),"learn-queue-next");fixture.wait([&]{return fixture.home->page()==H::Page::SuiteReview;},"suite ends with only first exercise eligible");
            }else completeUntil(fixture,[&]{return fixture.home->page()==H::Page::SuiteReview;},"suite naturally finishes with automatic save and next playback");
            platform::OutputTestAccess::deferObservation=false;
            ck(std::none_of(fixture.practice().playbackFretboardView().projection().begin(),fixture.practice().playbackFretboardView().projection().end(),[](const auto& c){return c.active;}),"suite terminal/navigation leaves no stale highlights");
            if(mode=="automatic"||mode=="delayed-automatic")ck(boardItemsObserved.count("fg:item:001141")&&boardItemsObserved.count("fg:item:001142"),"actual accepted frames select sounding tones for both suite source models; native paint remains gated");
            if(mode=="delayed-automatic")ck(sawAwaitingHandoff,"asynchronous handoff remains Awaiting before callback observation and still completes both exercises");
            const auto before=capture_fixture::confirmed(fixture.store->snapshot(storage::newUuid()));const auto originalFinalized=before.data.object().at("authoritative").object().at("finalized");
            const auto discovered=capture_fixture::confirmed(fixture.store->readSuite(storage::newUuid(),""));const auto suiteId=discovered.data.object().at("suite_id").string();
            const std::size_t expected=(mode=="automatic"||mode=="delayed-automatic")?2:1;
            ck(discovered.data.object().at("members").array().size()==expected,"suite includes exactly actually naturally completed exercises; no stopped or unused member");
            ck(discovered.data.object().at("review").null(),"no user self-assessment exists before final explicit review");
            for(const auto& row:originalFinalized.array()){const auto envelope=storage::validateEnvelope(decodeBlob(row.array()[1]));ck(envelope.value.object().at("result").object().at("assessment").null(),"each original immutable capture remains unassessed");}
            if(mode=="stopped-second-reopen"){
                ck(fixture.home->detachForStoreReopen(),"stopped suite can detach after all original capture/output cleanup");fixture.store.reset();storage::StoreOptions options;options.path=fixture.dir/"profile.sqlite";options.preferenceValidator=desktop::presentation::composedPreferenceValidator;fixture.store=std::make_unique<storage::ProfileStore>(options);
                ck(fixture.home->configureCapture(*fixture.store,fixture.sessionId,"America/New_York"),"reopen attaches original preview Session");fixture.wait([&]{return fixture.home->page()==H::Page::SuiteReview&&!L::pending(*fixture.home);},"durable pending suite restores final review only");
                ck(!fixture.practice().captureSession()->startTaken()&&fixture.home->audioSettings().snapshot().state==output::State::Closed,"reopen never automatically plays or scores unplayed work");
            }
            choose(*fixture.home,"suite-review-score",3);pressId(*fixture.home,"suite-review-submit");fixture.wait([&]{return control<juce::Button>(*fixture.home,"suite-review-back").isEnabled();},"one explicit final Developing review confirmed");
            const auto reviewed=capture_fixture::confirmed(fixture.store->readSuite(storage::newUuid(),suiteId));const auto& review=reviewed.data.object().at("review");
            ck(review.object().at("score")==json::Value("Developing")&&review.object().at("members").array().size()==expected,"final user score applies to exactly frozen completed membership");
            const auto reviewSnapshot=capture_fixture::confirmed(fixture.store->snapshot(storage::newUuid()));
            const auto suiteFacts=reviewSnapshot.data.object().at("authoritative").object().at("suite_fact");
            std::string reviewOperation;std::size_t reviewFacts=0;
            for(const auto& row:suiteFacts.array())if(row.array()[1]==json::Value(suiteId)&&row.array()[2]==json::Value("review")){reviewOperation=row.array()[3].string();++reviewFacts;}
            ck(reviewFacts==1&&!reviewOperation.empty(),"one authoritative final review retains its original operation identity");
            const auto replay=capture_fixture::confirmed(fixture.store->submitSuiteReview(reviewOperation,suiteId,review.object().at("reviewed_utc").string(),"Developing"));
            ck(replay.data.object().at("replayed").boolean(),"unchanged final review operation replays once without double application");
            const auto after=capture_fixture::confirmed(fixture.store->snapshot(storage::newUuid()));ck(after.data.object().at("authoritative").object().at("finalized")==originalFinalized,"final user report and reopen preserve individual immutable original Attempt envelopes");
            ck(after.data.object().at("authoritative").object().at("suite_fact")==suiteFacts,"unchanged review replay preserves every suite fact and creates no duplicate");
            ck(after.data.object().at("authoritative").object().at("source_attestation").array().empty(),"no learner performance, source task completion or automatic mastery credit inferred");
            if(mode!="stopped-second-reopen"){
                pressId(*fixture.home,"suite-review-back");fixture.wait([&]{return fixture.home->page()==H::Page::Home&&!L::boardPending(*fixture.home)&&!L::boardDeferred(*fixture.home);},"deferred board choice commits only stopped resolved Home");
                ck(L::boardRevision(*fixture.home)==boardRevisionBefore.value_or(0)+1,"one deferred choice commits exactly one CAS revision");
                const auto stable=L::boardRevision(*fixture.home);for(int repeat=0;repeat<20;++repeat)fixture.tick();ck(L::boardRevision(*fixture.home)==stable&&!L::boardDeferred(*fixture.home),"repeated ticks do not repeat display save");
            }else ck(!L::boardDeferred(*fixture.home)&&bool(fixture.practice().onBoardDisplayChanged),"detach/recreated Practice restores callback and cancels prior deferred request");
            capture_fixture::write(out/(mode+"-suite.json"),storage::canonical(reviewed.data));capture_fixture::write(out/(mode+"-snapshot.json"),storage::canonical(after.data));
            ck(fixture.home->getPeer()==nullptr,"suite campaign uses software-only output with no native App peer");
        }
        ck(nativeOpens==0,"suite campaign never opens a physical output device");
        capture_fixture::write(out/"summary.json",storage::canonical(json::Value::Object{{"status","PASS"},{"checks",json::Value::fromInteger(checks)},{"mode","--suite-auto-regression"},{"native_gui",false},{"physical_audio",false},{"acceptance_increment",json::Value::fromInteger(0)}}));
        std::cout<<"PASS "<<checks<<" real Home/Store suite automatic/final-review/skip/Stop/reopen/idempotence checks; software output only\n";return 0;
    }

    if(selectedLoadingOnly){
        // Actual Home/Lesson coordinators, no desktop peer, input injection or
        // audio connection. Only the fresh Harness profile is used.
        std::vector<std::filesystem::path> extensions;
        for(const auto& name:lesson::Catalog::installedExtensionDirectoryNames())extensions.push_back(resources/name);
        const auto wait=[&](auto predicate,const std::string& label,int seconds=35){
            const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(seconds);
            while(!predicate()){if(std::chrono::steady_clock::now()>end)throw std::runtime_error(label+" watchdog");h.tick();pump();}
        };
        if(selectedLoadingVisual){
            const auto ownProfile=capture_fixture::confirmed(h.store->snapshot(storage::newUuid())).data.object().at("profile_id").string();
            ck(h.home->attachPresentation(*h.store,ownProfile),"synthetic Home binds the same presentation path as production preview");
            wait([&]{return L::presentationReady(*h.home);},"owned synthetic presentation read",5);
            h.image("home-before-selective-learn");
        }
        const auto start=std::chrono::steady_clock::now();
        ck(L::beginFastLearn(*h.home,resources,extensions),"production metadata-only Learn accepts the exact installed resource extent");
        wait([&]{return view.preparedSourceIndex()&&!L::loading(*h.home);},"complete initial exercise browsing",8);
        const auto browseUs=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-start).count();
        const auto index=view.preparedSourceIndex();const auto store=L::selectedStore(*h.home);
        std::size_t sublevels=0;for(const auto& level:index->levels())sublevels+=level.sublevels.size();
        ck(index->levels().size()==105&&index->exercises().size()==7321&&sublevels==1389,"initial browsing retains all105 levels1389 source sublevels7321 rows");
        ck(!view.catalog()&&store&&store->cachedOwnerNames().empty(),"initial browsing constructs zero Practice package models");
        ck(control<juce::Button>(view,"learn-source-preview").isEnabled()==false&&control<juce::ComboBox>(view,"learn-source-level").isEnabled(),"complete hierarchy is usable without pretending Practice is prepared");
        const auto warmBrowse=std::chrono::steady_clock::now();
        ck(L::beginFastLearn(*h.home,resources,extensions)&&view.preparedSourceIndex()==index&&!L::loading(*h.home),"warm navigation reuses the same immutable complete index without a worker");
        const auto warmBrowseUs=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-warmBrowse).count();
        wait([&]{return !L::guided(*h.home).busy();},"initial read-only Guided summary",5);
        const auto noNewGuidedPlan=[&]{
            auto& guided=L::guided(*h.home);
            return desktop::GuidedSessionViewTestAccess::hasNoPlan(guided)&&guided.selectedMinutes()==0
                &&!control<juce::Button>(guided,"start").isEnabled()
                &&!control<juce::Button>(guided,"build").isEnabled()
                &&!control<juce::Button>(guided,"open-first").isEnabled()
                &&guided.planText().find("Choose an admitted whole exercise explicitly in Learn")!=std::string::npos
                &&guided.planText().find("rebuild this preview")==std::string::npos
                &&control<juce::Label>(guided,"guided-plan-state").getText().contains("Choose an admitted whole exercise explicitly in Learn");
        };
        ck(L::beginSelectedGuided(*h.home,resources,extensions)&&h.home->page()==H::Page::Guided&&!L::loading(*h.home)&&noNewGuidedPlan()&&store->cachedOwnerNames().empty(),"fresh Guided is responsive and requires an explicit Learn choice without loading all packages");
        if(selectedLoadingVisual)h.image("guided-explicit-choice-required");
        std::cout<<"Initial complete browsing_us="<<browseUs<<" warm_browsing_us="<<warmBrowseUs<<std::endl;
        ck(L::beginFastLearn(*h.home,resources,extensions),"return to complete Learn index");
        constexpr const char* sourceKey="printed:l001:starting-finger-1-index:exercise-001-1212";
        int subChoice=0,rowChoice=0;const learn::Exercise* row=nullptr;
        const auto& level=index->level(1);
        for(std::size_t a=0;a<level.sublevels.size();++a)for(std::size_t b=0;b<level.sublevels[a].exercises.size();++b){
            const auto& candidate=index->exercises().at(level.sublevels[a].exercises[b]);
            if(candidate.source.sourceExerciseKey==sourceKey){row=&candidate;subChoice=static_cast<int>(a+1);rowChoice=static_cast<int>(b+1);}
        }
        ck(row&&subChoice>0&&rowChoice>0,"real source-bound full48 Level1 row retained");
        choose(view,"learn-source-level",1);pressName(view,"Open level");choose(view,"learn-source-sublevel",subChoice);
        const auto selectedStart=std::chrono::steady_clock::now();pressName(view,"Open sublevel");
        const auto group=view.sourceGroupRevision();choose(view,"learn-source-start",rowChoice);choose(view,"learn-source-selection-mode",2);choose(view,"learn-source-stop",rowChoice);
        ck(view.sourceGroupRevision()==group,"moving inclusive endpoints preserves selected package generation");
        ck(!control<juce::Button>(view,"learn-source-preview").isEnabled(),"pending selected preparation does not enable stale catalog Preview");
        wait([&]{return !L::loading(*h.home)&&view.catalogReady();},"selected sublevel verified publication");
        const auto selectedUs=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-selectedStart).count();
        const auto catalog=view.catalog();const auto expected=learn::choices(*row,*catalog).at(0);
        ck(store->preparedOwnerNames()==std::vector<std::string>({"representative-controls","level001-extension"}),"non-prefix Level1 preparation loads only base and exact selected owner");
        ck(control<juce::ComboBox>(view,"learn-source-start").getSelectedId()==rowChoice&&control<juce::ComboBox>(view,"learn-source-stop").getSelectedId()==rowChoice,"verified publication retains endpoint intent");
        ck(control<juce::ComboBox>(view,"learn-source-start").getText().contains("Available for exact exercise Practice")&&control<juce::Button>(view,"learn-source-preview").isEnabled(),"selected availability and Preview agree with exact admission");
        if(selectedLoadingVisual)h.image("learn-selected-sublevel-ready");
        pressName(view,"Preview selection");const auto initialPreview=view.catalog();
        if(selectedLoadingVisual)h.image("learn-explicit-source-preview");
        const auto other=store->prepare({{"fg:item:001141","3cacd1c5c3dd2059a018c475192657ec0bb4e4c600074a5fbfb657ea611cefbc"}});
        ck(!view.installPreparedCatalog(other,resources,true,true)&&view.catalog()==initialPreview,"background publication refuses to replace retained Preview owner");
        pressName(view,"Confirm queue");
        ck(view.hasRetainedSourcePlan()&&!view.sourceQueueActive()&&!view.installPreparedCatalog(other,resources,true,true)&&view.catalog()==initialPreview,"confirmed Ready queue retains its original catalog before any Session exists");
        ck(!L::beginSelected(*h.home,{{"fg:item:001141","3cacd1c5c3dd2059a018c475192657ec0bb4e4c600074a5fbfb657ea611cefbc"}},view.sourceGroupRevision()),"Root cannot dispatch a new owner underneath Ready queue");
        {
            const auto* ready=L::sourceQueue(view);
            ck(ready&&ready->phase()==navigation::ExerciseQueuePhase::Ready&&ready->current()&&ready->current()->admission,"Browse fixture observes the confirmed unopened Ready queue");
            const auto readyAdmission=*ready->current()->admission;const auto readySource=ready->current()->sourceExerciseKey;
            const auto readyPosition=ready->position(),readySize=ready->size();
            const auto ownerNames=store->cachedOwnerNames();const auto groupBefore=view.sourceGroupRevision(),selectionBefore=view.sourceSelectionRevision();
            ck(view.selectLesson(expected.itemId)&&view.selectVariant(expected.variantId),"Ready queue permits read-only inspection of its exact admitted case");
            pressName(view,"Browse levels");auto& levels=control<juce::ComboBox>(view,"learn-source-level");
            ck(levels.isVisible()&&levels.getParentComponent()->isVisible()&&levels.getNumItems()==105&&!control<juce::Button>(view,"learn-queue-confirm").isVisible(),"explicit Browse levels from a Ready case opens all105 levels rather than Queue or Preview");
            ck(L::sourceBreadcrumb(view)=="105 levels","Levels breadcrumb omits the retained Ready queue's previous sublevel");
            const auto levelsHelp=control<juce::TextEditor>(view,"learn-source-details").getText();
            ck(levelsHelp.contains("Choose a level, sublevel and exercise")&&!levelsHelp.contains("Queue confirmed")&&!levelsHelp.contains("Review the displayed initial variant"),"Levels help describes the visible level-list step rather than the retained Ready workflow");
            ck(L::sourceQueue(view)==ready&&ready->phase()==navigation::ExerciseQueuePhase::Ready&&ready->position()==readyPosition&&ready->size()==readySize&&ready->current()->sourceExerciseKey==readySource&&*ready->current()->admission==readyAdmission&&view.catalog()==initialPreview&&view.preparedSourceIndex()==index&&store->cachedOwnerNames()==ownerNames&&view.sourceGroupRevision()==groupBefore&&view.sourceSelectionRevision()==selectionBefore&&view.selectedLesson()==expected.itemId&&view.selectedVariant()==expected.variantId,"Browse levels preserves the same Ready queue, exact admission, selection and verified caches without a new preparation");
        }
        ck(view.showSourceLevel(1),"explicit source-level choice resets only never-opened selection");choose(view,"learn-source-sublevel",subChoice);
        const auto warmStart=std::chrono::steady_clock::now();pressName(view,"Open sublevel");choose(view,"learn-source-start",rowChoice);
        wait([&]{return !L::loading(*h.home)&&view.catalogReady();},"visited owner rechecked publication");
        const auto warmSelectedUs=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-warmStart).count();
        ck(control<juce::ComboBox>(view,"learn-source-start").getText().contains("Available for exact exercise Practice"),"warm visited-owner publication refreshes dropdown availability");
        const auto sameScope=view.catalog();pressName(view,"Back");pressName(view,"Open sublevel");choose(view,"learn-source-start",rowChoice);
        wait([&]{return !L::loading(*h.home)&&view.catalogReady();},"same immutable scope byte recheck",3);
        ck(view.catalog()==sameScope&&store->lastPreparation().memoryCacheHits==2&&control<juce::ComboBox>(view,"learn-source-start").getText().contains("Available for exact exercise Practice"),"same-pointer warm publication preserves endpoint identity and refreshes exact availability after byte recheck");
        pressName(view,"Preview selection");pressName(view,"Exercise details");
        ck(view.hasExplicitSelection()&&view.selectedLesson()==expected.itemId&&view.selectedVariant()==expected.variantId,"details uses the explicit admitted source Preview identity");
        ck(control<juce::Label>(view,"lesson-search-status").getText().contains("currently prepared cases")&&control<juce::Label>(view,"lesson-search-status").getText().contains("complete exercise list"),"inspector search describes its prepared scope and full browsing route");
        if(selectedLoadingVisual){
            pressName(view,"Show TAB");
            desktop::TabView* actualTab=nullptr;
            for(auto* child:view.getChildren())if(auto* candidate=dynamic_cast<desktop::TabView*>(child))actualTab=candidate;
            ck(actualTab&&actualTab->isVisible()&&actualTab->document()&&actualTab->document()->source().events.size()==48&&view.getPeer()==nullptr,
               "component visuals expose TAB with the exact selected full48 source document without a native peer");
            const auto document=actualTab->document();const auto first=document->source().events.front().id,last=document->source().events.back().id;
            for(const double zoom:{0.10,0.75,1.0,2.0}){
                ck(actualTab->setZoom(zoom)&&actualTab->selectEvent(last)&&actualTab->document()==document,"actual full48 final event survives supported zoom");
                h.image("learn-actual48-final-zoom-"+std::to_string(static_cast<int>(std::lround(zoom*100))));
            }
            ck(actualTab->setZoom(1.0)&&actualTab->selectEvent(first),"component capture restores100% and exact first event before Guided");
            h.image("learn-actual48-first-zoom-100");
        }
        {
            const auto previewCatalog=view.catalog();const auto previewIndex=view.preparedSourceIndex();const auto groupBefore=view.sourceGroupRevision(),selectionBefore=view.sourceSelectionRevision();const auto ownerNames=store->cachedOwnerNames();
            view.showSourceHierarchy(false);
            ck(control<juce::Button>(view,"learn-queue-confirm").isVisible()&&!control<juce::ComboBox>(view,"learn-source-level").isVisible(),"generic source hierarchy entry still resumes the retained Preview");
            ck(control<juce::TextEditor>(view,"learn-source-details").getText().contains("Review the displayed initial variant for every item"),"generic Preview resume retains its original variant-review guidance");
            pressName(view,"Exercise details");pressName(view,"Browse levels");auto& levels=control<juce::ComboBox>(view,"learn-source-level");
            ck(levels.isVisible()&&levels.getParentComponent()->isVisible()&&levels.getNumItems()==105&&!control<juce::Button>(view,"learn-queue-confirm").isVisible(),"explicit Browse levels from Preview details opens the complete level list");
            ck(L::sourceBreadcrumb(view)=="105 levels","Levels breadcrumb omits the retained Preview's previous sublevel");
            const auto levelsHelp=control<juce::TextEditor>(view,"learn-source-details").getText();
            ck(levelsHelp.contains("Choose a level, sublevel and exercise")&&!levelsHelp.contains("Review the displayed initial variant")&&!levelsHelp.contains("Inclusive selection"),"Levels help omits Preview-only confirmation instructions without clearing the Preview");
            ck(view.hasRetainedSourcePlan()&&!L::sourceQueue(view)&&view.catalog()==previewCatalog&&view.preparedSourceIndex()==previewIndex&&store->cachedOwnerNames()==ownerNames&&view.sourceGroupRevision()==groupBefore&&view.sourceSelectionRevision()==selectionBefore&&view.selectedLesson()==expected.itemId&&view.selectedVariant()==expected.variantId&&navigation::snapshotAdmission(*view.catalog()->admit(expected.itemId,expected.variantId))==expected,"Browse levels retains Preview admission, explicit selection and immutable caches without creating a queue");
        }
        ck(L::beginSelectedGuided(*h.home,resources,extensions),"explicit selected Guided owner verification dispatched");
        wait([&]{return !L::loading(*h.home);},"Guided exact source recheck");
        ck(L::guided(*h.home).planText().find("Selected single source-backed case:")!=std::string::npos&&L::guided(*h.home).planText().find(expected.itemId)!=std::string::npos,"Guided plan preserves explicit exact source identity without an implicit case fallback");
        if(selectedLoadingVisual)h.image("guided-exact-selected-plan");
        ck(h.home->navigate(H::Page::Home),"return Home before cancellation fixture");
        if(selectedLoadingVisual)h.image("home-after-selected-guided");
        ck(L::beginFastLearn(*h.home,resources,extensions)&&view.showSourceLevel(1),"explicit new selection clears only never-opened plan");choose(view,"learn-source-sublevel",subChoice);
        auto entered=std::make_shared<std::atomic<bool>>(false),released=std::make_shared<std::atomic<bool>>(false);
        struct Release { std::shared_ptr<std::atomic<bool>> flag;~Release(){flag->store(true);} } release{released};
        desktop::sourceDataPool().addJob([entered,released]{entered->store(true);const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(8);while(!released->load()){if(std::chrono::steady_clock::now()>end)throw std::runtime_error("cancellation barrier watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}});
        wait([&]{return entered->load();},"owned cancellation barrier",2);pressName(view,"Open sublevel");
        const auto prior=view.catalog();ck(h.home->navigate(H::Page::Setup),"Back/navigation cancels queued selected-owner preparation");released->store(true);
        wait([]{return !desktop::SourceLibraryView::hasBackgroundWork();},"canceled selected work drain",8);
        ck(h.home->page()==H::Page::Setup&&view.catalog()==prior&&!L::loading(*h.home)&&!view.catalogReady(),"canceled completion cannot redirect Setup or authorize old catalog for a new selection");
        ck(h.home->navigate(H::Page::Learn),"return Learn for explicit refusal guard");view.catalogRefused("synthetic byte verification refusal");
        ck(!view.practiceSelected()&&!control<juce::Button>(view,"practice-selection").isEnabled(),"refused cached owner cannot create direct Practice through old Case controls");
        ck(L::beginSelectedGuided(*h.home,resources,extensions)&&noNewGuidedPlan()&&!L::loading(*h.home),"refused owner cannot implicitly enter a fresh Guided plan");
        const auto snapshot=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));const auto& authority=snapshot.data.object().at("authoritative").object();
        ck(authority.at("session").array().size()==1&&authority.at("pending").array().empty()&&authority.at("finalized").array().empty()&&authority.at("session_close").array().empty()&&authority.at("source_attestation").array().empty()&&authority.at("rule_observation").array().empty(),"browsing, verification, Preview/Ready and refusal create no Attempt or curriculum credit");
        ck(nativeOpens==0&&connections==0&&h.home->audioSettings().snapshot().state==output::State::Closed,"all navigation uses closed Audio and zero physical device opens");
        capture_fixture::write(out/"summary.json",storage::canonical(json::Value::Object{{"status","PASS"},{"mode",selectedLoadingVisual?"--selected-loading-visual-regression":"--selected-loading-regression"},{"checks",json::Value::fromInteger(checks)},{"initial_browse_microseconds",json::Value::fromInteger(browseUs)},{"warm_browse_microseconds",json::Value::fromInteger(warmBrowseUs)},{"selected_sublevel_microseconds",json::Value::fromInteger(selectedUs)},{"visited_sublevel_microseconds",json::Value::fromInteger(warmSelectedUs)},{"initial_browse_target_met",browseUs<=3000000},{"visited_target_met",warmSelectedUs<=3000000},{"OS_cache_controlled",false},{"native_GUI",false},{"component_snapshots",selectedLoadingVisual},{"physical_listening",false},{"curriculum_credit",false}}));
        std::cout<<"PASS "<<checks<<" selective Learn UI checks; browsing_us="<<browseUs<<" visited_us="<<warmSelectedUs<<"\n";return 0;
    }
    if(phaseFailureRetryOnly){
        // One Home/profile/index owner; no desktop peer or source/resource edits.
        // Faults use the existing post-index/pre-catalog hook, before catalog I/O.
        const std::vector<std::filesystem::path> finite{resources/lesson::Catalog::installedExtensionDirectoryNames().front()};
        const auto before=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        const auto authorityBefore=storage::canonical(before.data.object().at("authoritative"));
        const auto* capture=h.practice().captureSession();
        if(!capture)throw std::runtime_error("Missing original synthetic capture");
        const auto captureOwner=capture->binding().owner;
        const auto captureContext=capture->binding().context;
        auto& guided=L::guided(*h.home);
        h.wait([&]{return !guided.busy();},"initial read-only Guided summary");
        auto entered=std::make_shared<std::atomic<bool>>(false);
        auto release=std::make_shared<std::atomic<bool>>(false);
        struct ReleaseOnExit {
            std::shared_ptr<std::atomic<bool>> value;
            ~ReleaseOnExit(){value->store(true);}
        } releaseOnExit{release};
        const auto arm=[&]{entered->store(false);release->store(false);};
        const auto fault=[entered,release](const std::string& message){
            return [entered,release,message]{
                entered->store(true);
                const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(8);
                while(!release->load()){
                    if(std::chrono::steady_clock::now()>end)throw std::runtime_error("phase-failure barrier watchdog");
                    std::this_thread::sleep_for(std::chrono::milliseconds(1));
                }
                throw std::runtime_error(message);
            };
        };
        const auto closedCapture=[&](const std::string& phase){
            ck(h.practice().captureSession()==capture&&h.practice().captureSessionId()==h.sessionId&&
               capture->binding().owner==captureOwner&&capture->binding().context==captureContext&&
               capture->phase()==capture::SessionPhase::Idle&&!capture->startTaken()&&
               !L::owned(*h.home)&&!L::pending(*h.home)&&!view.sourceQueueActive()&&
               !guided.running()&&h.home->audioSettings().snapshot().state==output::State::Closed&&
               nativeOpens==0&&connections==0,
               phase+": original idle capture retained, no queue/Guided Session or audio connection");
        };
        const auto sourceText=[&]{return control<juce::TextEditor>(view,"learn-source-details").getText();};
        const auto finishWorker=[&](const std::string& phase){
            h.wait([&]{return !L::loading(*h.home);},phase+" result publication");
            h.wait([]{return !desktop::SourceLibraryView::hasBackgroundWork();},phase+" worker boundary");
        };
        const std::string learnError="controlled Learn post-index fault";
        arm();
        ck(L::beginLearn(*h.home,resources,finite,{},fault(learnError)),"Learn starts finite post-index failure fixture");
        h.wait([&]{return entered->load()&&view.preparedSourceIndex();},"verified index and Learn fault barrier");
        const auto index=view.preparedSourceIndex();
        ck(h.home->page()==H::Page::Learn&&L::loading(*h.home)&&!view.catalog()&&
           control<juce::ComboBox>(view,"learn-source-level").getNumItems()==105,
           "real verified index publishes before the controlled Learn fault, with catalog still absent");
        choose(view,"learn-source-level",12);pressName(view,"Open level");
        choose(view,"learn-source-sublevel",1);pressName(view,"Open sublevel");
        choose(view,"learn-source-start",2);
        ck(sourceText().contains("Preparing Practice")&&
           control<juce::ComboBox>(view,"learn-source-start").getText().contains("Preparing Practice")&&
           !control<juce::Button>(view,"learn-source-preview").isEnabled(),
           "post-index pending state is visibly preparing and cannot preview unverified Practice");
        release->store(true);finishWorker("Learn fault");
        ck(view.preparedSourceIndex()==index&&!view.catalog()&&h.home->page()==H::Page::Learn,
           "Learn phase failure retains the exact verified index and current page without installing a catalog");
        ck(sourceText().contains(juce::String::fromUTF8(("Could not prepare exercises: "+learnError).c_str()))&&
           !sourceText().contains("Preparing Practice")&&
           !sourceText().contains("Preparing exercises and Practice"),
           "Learn post-index failure is visibly explicit and no longer claims preparation");
        const auto* sourceDetailsButton=recursiveButton(view,"Exercise details");
        ck(control<juce::ComboBox>(view,"learn-source-start").getText().contains("Practice not ready")&&
           !control<juce::ComboBox>(view,"learn-source-start").getText().contains("Preparing Practice")&&
           !control<juce::Button>(view,"learn-source-preview").isEnabled()&&
           sourceDetailsButton&&!sourceDetailsButton->isEnabled(),
           "failed catalog refreshes the retained row to not ready and keeps Preview/details gated");
        closedCapture("Learn fault");
        pressName(view,"Back");pressName(view,"Back");pressName(view,"Back");
        ck(h.home->page()==H::Page::Home&&!L::loading(*h.home)&&view.preparedSourceIndex()==index,
           "actual hierarchy Back remains available after failure and retains the verified index");

        // A canceled late exception must neither redirect a newer page nor publish its error.
        const std::string canceledError="controlled canceled post-index fault";
        arm();
        ck(L::beginLearn(*h.home,resources,finite,{},fault(canceledError)),"same-package retry owns one cancellable post-index job");
        h.wait([&]{return entered->load();},"canceled Learn fault barrier");
        ck(view.preparedSourceIndex()==index&&!view.catalog()&&L::loading(*h.home),
           "cancellable retry reuses the same verified index owner before catalog construction");
        pressName(view,"Back");
        ck(h.home->page()==H::Page::Home&&!L::loading(*h.home),"actual Back cancels only the pending retry intent");
        click(*h.home,"Guitar setup");
        ck(h.home->page()==H::Page::Setup,"newer ordinary Setup destination is established before releasing the canceled fault");
        release->store(true);
        h.wait([]{return !desktop::SourceLibraryView::hasBackgroundWork();},"canceled exception worker boundary");
        // The job posts its exception before leaving the pool; pump its queued callback.
        for(int i=0;i<8;++i){h.tick();pump();}
        ck(h.home->page()==H::Page::Setup&&!L::loading(*h.home)&&!view.catalog()&&
           view.preparedSourceIndex()==index&&!sourceText().contains(juce::String::fromUTF8(canceledError.c_str())),
           "late canceled exception cannot redirect Setup, replace the index or publish stale failure text");
        closedCapture("Canceled late fault");
        click(*h.home,"Back");
        ck(h.home->page()==H::Page::Home,"normal Setup Back returns Home after canceled worker closure");

        const std::string guidedError="controlled Guided post-index fault";
        arm();
        ck(L::beginGuided(*h.home,resources,finite,fault(guidedError)),"same Home/index owner starts controlled Guided failure");
        h.wait([&]{return entered->load();},"Guided fault barrier");
        auto& planState=control<juce::Label>(guided,"guided-plan-state");
        ck(h.home->page()==H::Page::Guided&&view.preparedSourceIndex()==index&&!view.catalog()&&
           planState.isVisible()&&planState.getText().contains("Preparing the verified")&&
           !control<juce::Button>(guided,"build").isEnabled()&&!control<juce::Button>(guided,"start").isEnabled(),
           "Guided retry retains the exact index, shows preparation and gates premature actions");
        release->store(true);finishWorker("Guided fault");
        ck(h.home->page()==H::Page::Guided&&view.preparedSourceIndex()==index&&!view.catalog()&&
           planState.isVisible()&&planState.getText().contains(juce::String::fromUTF8(("Could not prepare exercises: "+guidedError).c_str()))&&
           !planState.getText().contains("Preparing the verified"),
           "Guided post-index failure replaces preparing feedback with the exact visible failure");
        ck(!control<juce::Button>(guided,"build").isEnabled()&&!control<juce::Button>(guided,"start").isEnabled()&&
           !guided.buildPlan()&&!guided.startSession(),
           "visible and direct Guided Build/Start remain gated after catalog failure");
        closedCapture("Guided fault");
        ck(guided.requestBack()&&h.home->page()==H::Page::Home&&!L::loading(*h.home),
           "Guided Back remains available after post-index failure");

        // Only this successful retry reaches catalog construction; no second index parse is requested.
        ck(L::beginGuided(*h.home,resources,finite),"same-package Guided retry resumes normal verified construction");
        finishWorker("successful Guided retry");
        ck(h.home->page()==H::Page::Guided&&view.preparedSourceIndex()==index&&view.catalog(),
           "successful retry publishes finite catalog while retaining the original index owner and Guided destination");
        ck(!guided.planText().empty()&&control<juce::Button>(guided,"build").isEnabled()&&
           control<juce::Button>(guided,"start").isEnabled()&&
           !planState.getText().contains(juce::String::fromUTF8(guidedError.c_str()))&&
           !planState.getText().contains("Preparing the verified"),
           "successful Guided retry clears the failure fence and restores original plan actions without starting them");
        const auto catalog=view.catalog();
        closedCapture("Successful Guided retry");
        ck(guided.requestBack()&&h.home->page()==H::Page::Home,"successful unstarted Guided plan returns Home without a Session");
        ck(L::beginLearn(*h.home,resources,finite,{})&&!L::loading(*h.home)&&view.catalog()==catalog&&view.preparedSourceIndex()==index,
           "eventual Learn retry reuses the same verified index/catalog without another job");
        pressName(view,"Open level");pressName(view,"Open sublevel");
        ck(control<juce::ComboBox>(view,"learn-source-level").getSelectedId()==12&&
           control<juce::ComboBox>(view,"learn-source-start").getSelectedId()==2&&
           control<juce::ComboBox>(view,"learn-source-stop").getSelectedId()==2,
           "failure/cancel/Guided detours preserve the original source level and exact endpoints");
        ck(control<juce::Button>(view,"learn-source-preview").isVisible()&&
           control<juce::Button>(view,"learn-source-preview").isEnabled()&&
           !control<juce::ComboBox>(view,"learn-source-start").getText().contains("Preparing Practice")&&
           !sourceText().contains(juce::String::fromUTF8(learnError.c_str()))&&
           !sourceText().contains(juce::String::fromUTF8(guidedError.c_str()))&&
           !sourceText().contains(juce::String::fromUTF8(canceledError.c_str())),
           "eventual Learn retry enables verified Preview and removes stale preparing/failure feedback");
        const auto after=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        ck(storage::canonical(after.data.object().at("authoritative"))==authorityBefore,
           "all authoritative tables remain byte-equivalent across faults, cancel and retry: no Session, Attempt, attestation or credit");
        closedCapture("Final phase-failure/retry state");
        trace.flush();if(!trace)throw std::runtime_error("Phase-failure checks could not be flushed");
        capture_fixture::write(out/"summary.json",storage::canonical(json::Value::Object{
            {"schema","fathom.learn-phase-failure-retry.1"},{"status","PASS"},
            {"checks",json::Value::fromInteger(checks)},{"mode","--learn-phase-failure-retry-regression"},
            {"one_home_owner",true},{"verified_index_owner_reused",true},{"finite_catalog",true},
            {"post_index_failures_observed",json::Value::fromInteger(2)},
            {"late_canceled_fault",true},{"authoritative_unchanged",true},
            {"native_gui",false},{"native_opens",json::Value::fromInteger(nativeOpens)},
            {"software_connections",json::Value::fromInteger(connections)},
            {"physical_listening",false},{"curriculum_credit",false},{"acceptance_increment",json::Value::fromInteger(0)}}));
        std::cout<<"PASS "<<checks<<" finite Learn/Guided post-index failure and retry checks; no foreground/audio\n";
        return 0;
    }
    if(inspectorWordingOnly){
        // No desktop peer, foreground interaction, audio connection or Practice Start.
        const auto before=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        const auto authorityBefore=storage::canonical(before.data.object().at("authoritative"));
        const auto* capture=h.practice().captureSession();
        ck(view.installPreparedCatalog(lesson::InstalledCatalogFixtureAccess::levelOneWithControls(resources),resources,false),"install only the hash-bound Level1 extension and representative controls");
        ck(view.loadSourceIndex(resources/"learn-source-index"),"load the verified source hierarchy");L::indexLoaded(*h.home);
        const auto catalog=view.catalog();const auto index=view.preparedSourceIndex();
        const learn::Exercise* row=nullptr;int sublevel=0,exercise=0;
        const auto& level=index->level(1);
        for(std::size_t sub=0;sub<level.sublevels.size();++sub)for(std::size_t ex=0;ex<level.sublevels[sub].exercises.size();++ex){
            const auto& candidate=index->exercises().at(level.sublevels[sub].exercises[ex]);
            if(candidate.source.sourceExerciseKey=="printed:l001:starting-finger-1-index:exercise-001-1212"){
                ck(!row,"printed source identity is unique");row=&candidate;sublevel=static_cast<int>(sub+1);exercise=static_cast<int>(ex+1);
            }
        }
        ck(row&&learn::choices(*row,*catalog).size()==2,"real printed exercise retains its two reviewed exact choices");
        const auto expected=learn::choices(*row,*catalog).front();
        const auto identityBefore=navigation::snapshotAdmission(*catalog->admit(expected.itemId,expected.variantId));
        const auto models=[&]{json::Value::Object records;for(const auto& variant:catalog->lesson(expected.itemId).variants)records.emplace(variant.id,content::sha256(variant.model->source().preservedRecordJson));return storage::canonical(records);};
        const auto modelsBefore=models();
        ck(h.home->navigate(H::Page::Learn),"open retained Learn without dispatching the full catalog loader");view.showSourceHierarchy(false);
        choose(view,"learn-source-level",1);pressName(view,"Open level");choose(view,"learn-source-sublevel",sublevel);pressName(view,"Open sublevel");choose(view,"learn-source-selection-mode",1);choose(view,"learn-source-start",exercise);
        pressName(view,"Exercise details");
        auto& back=control<juce::Button>(view,"back");auto& inventory=control<juce::Label>(view,"inventory");auto& summary=control<juce::Label>(view,"summary");auto& practice=control<juce::Button>(view,"practice-selection");
        ck(back.getButtonText()=="Exercises"&&back.getTitle()=="Return to Exercises with the original source selection retained.","source inspection names its actual Exercises caller in visible and accessible text");
        ck(view.selectedLesson()==expected.itemId&&view.selectedVariant()==expected.variantId&&practice.isEnabled(),"inspection still chooses the exact admitted variant");
        const auto textFits=[&](int width,int height){
            h.home->setSize(width,height);
            const auto font=back.getLookAndFeel().getTextButtonFont(dynamic_cast<juce::TextButton&>(back),back.getHeight());
            juce::GlyphArrangement glyphs;glyphs.addLineOfText(font,back.getButtonText(),0,0);
            ck(back.getWidth()==90&&view.getLocalBounds().contains(back.getBounds())&&glyphs.getBoundingBox(0,-1,true).getWidth()<=back.getWidth()-12,"destination label fits the unchanged 90-pixel control at "+std::to_string(width)+"x"+std::to_string(height));
        };
        textFits(920,680);textFits(1400,819);textFits(640,680);
        auto& cases=control<juce::ComboBox>(view,"lessons");std::string caseText;
        for(int i=0;i<cases.getNumItems();++i)if(cases.getItemText(i).contains("[fg:item:000001]"))caseText=cases.getItemText(i).toStdString();
        ck(caseText.find("| Case variants: some available")!=std::string::npos&&caseText.find("| Practice admission: available")==std::string::npos,"mixed case availability is explicitly scoped to some variants");
        for(const auto mode:{desktop::presentation::Level::Beginner,desktop::presentation::Level::Advanced,desktop::presentation::Level::Developer}){
            view.setPresentation(mode,std::nullopt);
            ck(view.selectVariant("fg:variant:000001"),"retain authored refused variant for presentation mode "+std::to_string(static_cast<int>(mode)));
            ck(!practice.isEnabled()&&summary.getText().contains("Selected variant unavailable for Practice"),"refused variant stays disabled and primary wording does not refuse the entire mixed case");
            ck(practice.getTitle().contains("selected variant")||practice.getTitle().contains("Selected variant"),"accessible refusal names the selected variant");
            ck(summary.getText().contains("another variant or case"),"refused selection offers another variant or case");
            ck(!view.practiceSelected(),"explicit refused entry remains rejected by the unchanged Practice gate");
            ck(view.selectVariant(expected.variantId)&&practice.isEnabled()&&summary.getText().contains("Selected variant available for Practice"),"available variant restores exact availability without starting Practice");
            ck(navigation::snapshotAdmission(*catalog->admit(view.selectedLesson(),view.selectedVariant()))==identityBefore,"presentation changes preserve the complete admitted identity");
            if(mode!=desktop::presentation::Level::Developer){
                ck(!inventory.getText().contains("variants /")&&!inventory.getDescription().contains("105")&&!inventory.getDescription().contains("cases |"),"Beginner and Advanced inventory omit Developer catalog totals including accessible descriptions");
            }else{
                std::size_t variants=0;for(const auto& record:catalog->lessons())variants+=record.variants.size();
                ck(inventory.getText().contains("Retained preview catalog: "+juce::String(static_cast<int>(catalog->lessons().size()))+" cases / "+juce::String(static_cast<int>(variants))+" variants")&&inventory.getDescription().contains("105 approved workbook identities represented")&&inventory.getDescription().contains("do not measure exercise engineering acceptance, whole-workbook completion or learner credit"),"Developer counts report the actual finite retained catalog and exclude engineering acceptance, workbook completion and credit");
            }
        }
        view.setPresentation(desktop::presentation::Level::Advanced,std::nullopt);h.home->setSize(920,680);
        h.image("inspector-Exercises-admitted-component");
        pressId(view,"back");
        ck(control<juce::ComboBox>(view,"learn-source-start").isVisible()&&control<juce::ComboBox>(view,"learn-source-start").getSelectedId()==exercise&&control<juce::ComboBox>(view,"learn-source-sublevel").getSelectedId()==sublevel,"Exercises Back actually restores the original hierarchy selection");
        pressName(view,"Preview selection");pressName(view,"Exercise details");
        ck(back.getButtonText()=="Preview"&&back.getTitle().contains("Return to Preview"),"Preview inspector names its retained Preview caller");pressId(view,"back");
        ck(control<juce::ComboBox>(view,"learn-preview-item").isVisible(),"Preview Back actually restores source preview");
        ck(h.home->navigate(H::Page::Home),"return Home with exact explicit selection retained");click(*h.home,"Exercise details");
        ck(h.home->page()==H::Page::Learn&&back.getButtonText()=="Home"&&back.getTitle()=="Return to Home without changing the selected Learn case.","Home Exercise details names its real Home caller");
        textFits(920,680);textFits(1400,819);
        ck(view.selectVariant("fg:variant:000001")&&!practice.isEnabled(),"Home inspector retains the same selected-variant refusal");h.image("inspector-Home-refused-component");pressId(view,"back");
        ck(h.home->page()==H::Page::Home,"Home Back returns Home through the unchanged callback");
        const auto after=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        ck(storage::canonical(after.data.object().at("authoritative"))==authorityBefore,"all authoritative storage rows remain exactly unchanged");
        ck(models()==modelsBefore&&navigation::snapshotAdmission(*catalog->admit(expected.itemId,expected.variantId))==identityBefore,"source models and full admission identity remain unchanged");
        ck(h.practice().captureSession()==capture&&h.practice().captureSessionId()==h.sessionId&&capture->phase()==capture::SessionPhase::Idle&&!capture->startTaken()&&!L::owned(*h.home)&&!L::pending(*h.home)&&!view.sourceQueueActive(),"original idle capture ownership retained without a queue or Attempt");
        ck(h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0&&h.finals()==0,"zero physical opens, audio connections, finalized results or learner credit");
        std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"native_gui\":false,\"physical_audio\":false,\"foreground_actions\":0,\"acceptance_change\":0}\n";
        std::cout<<"PASS "<<checks<<" inspector caller and variant wording checks\n";return 0;
    }
    if(guidedBackSummaryOnly){
        // Exercise the shared Home callbacks; never manually notify Guided of a save.
        h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);h.home->toFront(true);marker();
        ck(view.installPreparedCatalog(lesson::InstalledCatalogFixtureAccess::levelOneWithControls(resources),resources,false),"install the existing hash-bound Level1 descriptor and representative controls");
        ck(view.selectLesson("fg:item:000001")&&view.selectVariant("fg:variant:007478"),"select the existing admitted exact case before Guided planning");
        const std::vector<std::filesystem::path> finite{resources/"level001-extension"};
        ck(L::beginGuided(*h.home,resources,finite),"ordinary Guided entry starts the existing finite catalog preparation");
        h.wait([&]{return !L::loading(*h.home);},"finite Guided catalog ready");
        auto& guided=L::guided(*h.home);
        h.wait([&]{return !guided.busy();},"initial Guided summary resolved");
        ck(view.catalog()&&guided.buildPlan(),"real Home has the verified catalog and a Guided plan");
        ck(guided.startSession(),"explicit Guided Start creates its original Session");
        h.wait([&]{return !guided.busy();},"Guided Session confirmed");
        const auto session=guided.sessionId();
        ck(guided.running()&&!session.empty(),"Guided owns the confirmed active Session");
        auto& explanation=control<juce::Label>(guided,"guided-explanation");
        const auto unlinkedExplanationBounds=explanation.getBounds();
        const auto claimsSavedLink=[&]{return explanation.getText().contains("Saved Practice Attempt belongs to this Guided Session");};
        ck(!claimsSavedLink(),"fresh Guided explanation does not claim a saved Attempt");
        const auto admission=view.catalog()->admit("fg:item:000001","fg:variant:007478");
        ck(admission&&admission->practiceAllowed(),"retained exact Level1 case is admitted without policy changes");
        ck(guided.onOpenLesson&&guided.onOpenLesson("fg:item:000001","fg:variant:007478"),"ordinary Guided Open in Learn preserves its return origin");
        std::string reason;
        ck(view.onPractice&&view.onPractice(admission,60,reason),"ordinary Learn callback prepares Guided-owned Practice");
        ck(h.practice().captureSessionId()==session&&!h.practice().captureSession()->startTaken(),"preparation binds the same Session without starting an Attempt");
        click(h.practice(),"Back");
        h.wait([&]{return h.home->page()==H::Page::Learn;},"unused preparation returns through ordinary Back");
        ck(guided.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session")==std::string::npos&&h.finals()==0,"unused Back does not invent a saved link or Attempt");
        ck(view.onPractice(admission,60,reason),"same exact case can be prepared again through the original callback");
        click(h.practice(),"Audio settings");
        h.wait([&]{return h.home->page()==H::Page::Audio;},"prepared Practice opens its ordinary shared Audio route");
        auto& audio=A::settings(*h.home);
        click(audio,"Connect audio");h.tick();click(audio,"Enable audio");h.blocks(1);
        h.wait([&]{return h.home->audioSettings().snapshot().state==output::State::Ready;},"explicit software Connect and Enable reaches Ready");
        click(audio,"Back to Practice");
        h.wait([&]{return h.home->page()==H::Page::Practice;},"Audio returns to the original prepared Practice");
        ck(nativeOpens==0&&connections==1&&h.practice().captureSessionId()==session&&!h.practice().captureSession()->startTaken(),"ordinary Audio setup preserves the Guided owner without physical I/O or an implicit Start");
        click(h.practice(),"Start selected case");
        h.wait([&]{return h.practice().captureSession()->startTaken();},"explicit Guided-owned Practice Start");
        h.blocks(2);click(h.practice(),"Stop & review result");
        h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"explicitly stopped original result reaches Review");
        const auto owner=h.practice().captureSession()->binding().owner;
        ck(!owner.empty()&&h.practice().captureSession()->binding().context.object().at("session_id").string()==session,"original Attempt context belongs to this Guided Session");
        ck(h.practice().saveSample(),"explicit Save submits the original result");
        h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"original result confirmed Saved");
        h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"saved output cleanup resolved");
        const auto retainedBack=h.practice().onBack;
        click(h.practice(),"Back");
        h.wait([&]{return h.home->page()==H::Page::Learn;},"saved result returns through ordinary Back");
        h.wait([&]{return !guided.busy();},"ordinary Back summary refresh settled");
        ck(guided.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session")!=std::string::npos,"ordinary Back exposes the real saved Attempt without the dedicated summary button");
        ck(guided.sessionSummaryText().find(session)!=std::string::npos&&guided.sessionSummaryText().find("fg:item:000001 / fg:variant:007478")!=std::string::npos,"linked summary retains exact Session and source identity");
        ck(claimsSavedLink()&&explanation.getBounds()!=unlinkedExplanationBounds,"real linked Attempt updates explanation and its layout without a test resize");
        ck(view.onBack!=nullptr,"Learn has its original Guided return callback");view.onBack();
        ck(h.home->page()==H::Page::Guided&&guided.stopSession(),"ordinary Learn Back permits explicit Guided Stop and save");
        h.wait([&]{return !guided.busy();},"linked Guided close confirmed");
        ck(!guided.running()&&guided.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session")!=std::string::npos,"normal closed summary retains the linked saved result");
        ck(guided.requestProgressPage()&&h.home->page()==H::Page::Progress&&h.finals()==1,"read-only Progress creates no duplicate Attempt");
        ck(guided.startSession(),"a new explicit Guided Session can follow the closed one");
        h.wait([&]{return !guided.busy();},"new Guided Session confirmed");
        const auto nextSession=guided.sessionId();
        ck(nextSession!=session&&guided.running(),"new Guided owner is distinct from retained old Practice");
        ck(!claimsSavedLink()&&explanation.getBounds()==unlinkedExplanationBounds,"confirmed new Guided Session clears prior saved-link text and restores unlinked layout without a test resize");
        retainedBack();
        ck(!guided.busy()&&guided.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session")==std::string::npos,"stale old Back callback cannot link its saved Attempt to a new Guided owner");
        ck(h.practice().captureSessionId()==session&&h.practice().captureSession()->binding().owner==owner&&h.finals()==1,"stale return preserves original capture identity and finalized count");
        ck(!claimsSavedLink(),"stale old Back callback cannot restore an explanation link for the new Guided owner");
        ck(guided.stopSession(),"explicit Stop settles the new unused synthetic Guided Session");
        h.wait([&]{return !guided.busy();},"new Guided close confirmed");
        ck(!claimsSavedLink(),"closed unused Guided Session still does not claim a saved Attempt");
        ck(guided.startSession(),"explicit Start creates a separate synthetic Session for the interruption regression");
        h.wait([&]{return !guided.busy();},"interruptible Guided Session confirmed");
        const auto interruptedSession=guided.sessionId();
        ck(interruptedSession!=session&&interruptedSession!=nextSession&&guided.running()&&!claimsSavedLink(),"third confirmed owner is distinct and has no saved-link explanation");
        ck(guided.interruptSession(),"explicit interruption leaves the new original Session unresolved");
        ck(!guided.running()&&guided.canLeave()&&!claimsSavedLink()&&explanation.getBounds()==unlinkedExplanationBounds&&guided.sessionSummaryText().find(interruptedSession)!=std::string::npos&&guided.sessionSummaryText().find("No saved outcome is claimed.")!=std::string::npos&&guided.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session")==std::string::npos,"interrupted owner retains truthful no-saved-outcome guidance and unlinked layout without a test resize");
        const auto snapshot=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        const auto& authoritative=snapshot.data.object().at("authoritative").object();
        ck(authoritative.at("pending").array().empty()&&authoritative.at("finalized").array().size()==1,"one original Attempt remains finalized with no pending save");
        bool interruptedCreated=false,interruptedClosed=false,interruptedLinked=false;
        for(const auto& row:authoritative.at("session").array())interruptedCreated=interruptedCreated||row.array().at(0).string()==interruptedSession;
        for(const auto& row:authoritative.at("session_close").array())interruptedClosed=interruptedClosed||row.array().at(0).string()==interruptedSession;
        for(const auto& row:authoritative.at("identity").array())if(row.array().at(1).string()=="Attempt"&&!row.array().at(2).null())interruptedLinked=interruptedLinked||row.array().at(2).string()==interruptedSession;
        ck(interruptedCreated&&!interruptedClosed&&!interruptedLinked,"interruption preserves its created Session with no close or linked Attempt while original saved history remains authoritative");
        ck(authoritative.at("source_attestation").array().empty()&&authoritative.at("rule_observation").array().empty(),"navigation and summary notification create no attestation or curriculum observation");
        ck(nativeOpens==0,"all device I/O remains substituted and no physical device opens");
        capture_fixture::write(out/"summary.json",storage::canonical(json::Value::Object{{"status","PASS"},{"checks",json::Value::fromInteger(checks)},{"mode","--guided-back-summary-regression"},{"actual_home",true},{"actual_store",true},{"original_session",session},{"original_owner",owner},{"new_session",nextSession},{"interrupted_session",interruptedSession},{"intentional_unresolved_session_debt",true},{"finalized_attempts",json::Value::fromInteger(1)},{"native_opens",json::Value::fromInteger(nativeOpens)},{"physical_listening",false},{"curriculum_credit",false}}));
        std::cout<<"PASS "<<checks<<" ordinary Guided Back summary checks\n";return 0;
    }
    if(exactSelectionOnly){
        h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);h.home->toFront(true);marker();
        // This branch must return before the retained all-extension campaign below.
        // The fixed test-only helper selects the existing compiled Level1 descriptor.
        const std::vector<std::filesystem::path> finite{resources/"level001-extension"};
        const std::vector<std::filesystem::path> pinnedFiles{
            resources/"representative-controls"/"manifest.json",finite.front()/"manifest.json",
            resources/"learn-source-index"/"index.json",resources/"learn-source-index"/"exercises.jsonl",
            resources/"learn-source-index"/"accepted-overlay.json"};
        auto resourcePins=[&]{json::Value::Object result;for(const auto& path:pinnedFiles){
            result.emplace(path.lexically_relative(resources).generic_string(),content::sha256(content::readBounded(path,32*1024*1024)));}return json::Value(std::move(result));};
        auto snapshot=[&](const std::string& name){auto reply=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));capture_fixture::write(out/(name+".json"),storage::canonical(reply.data));return reply;};
        const auto before=snapshot("exact-selection-before");const auto pinsBefore=resourcePins();
        auto* const originalCapture=h.practice().captureSession();
        ck(originalCapture&&h.practice().captureSessionId()==h.sessionId,"fresh Home capture belongs to its one named synthetic Session");
        const auto originalOwner=originalCapture->binding().owner;const auto originalContext=originalCapture->binding().context;
        const auto& authoritativeBefore=before.data.object().at("authoritative").object();
        const std::set<std::string> expectedSnapshotKeys{"acknowledgment","checkpoint","finalized","identity","late_evidence","metadata","pending","preferences","profile","rule_observation","session","session_close","source_attestation"};
        std::set<std::string> actualSnapshotKeys;for(const auto& table:authoritativeBefore)actualSnapshotKeys.insert(table.first);
        ck(actualSnapshotKeys==expectedSnapshotKeys&&authoritativeBefore.size()==13&&authoritativeBefore.at("identity").array().empty()&&authoritativeBefore.at("session").array().size()==1&&authoritativeBefore.at("finalized").array().empty()&&authoritativeBefore.at("source_attestation").array().empty(),"fresh fixture has exactly the 13 snapshot authority keys, one Session and no Attempt, result or source credit");
        ck(std::filesystem::canonical(h.dir)==std::filesystem::canonical(out)/"profile"&&std::filesystem::is_regular_file(h.dir/"profile.sqlite"),"ProfileStore is confined to the newly created evidence profile");
        const auto stopped=[&](const std::string& stage){
            ck(h.practice().captureSession()==originalCapture&&h.practice().captureSessionId()==h.sessionId&&originalCapture->binding().owner==originalOwner&&originalCapture->binding().context==originalContext&&originalCapture->phase()==capture::SessionPhase::Idle&&!originalCapture->startTaken()&&!L::owned(*h.home)&&!L::pending(*h.home)&&!view.sourceQueueActive(),stage+": original owner/context retained, no queue Session or Attempt started");
            ck(h.home->audioSettings().snapshot().state==output::State::Closed&&nativeOpens==0&&connections==0,stage+": output remains closed with zero software connections and physical opens");
        };
        stopped("initial");
        ck(view.installPreparedCatalog(lesson::InstalledCatalogFixtureAccess::levelOneWithControls(resources),resources,false),"install verified representative controls and only the compiled pinned Level1 extension");
        ck(view.loadSourceIndex(resources/"learn-source-index"),"load the packaged hash-verified source hierarchy");L::indexLoaded(*h.home);
        const auto index=view.preparedSourceIndex();const auto catalog=view.catalog();
        ck(index&&catalog&&catalog->isInstalledExtension("fg:item:000001"),"finite catalog installs the exact Level1 replacement owner");
        constexpr const char* sourceKey="printed:l001:starting-finger-1-index:exercise-001-1212";
        const learn::Exercise* row=nullptr;int sublevelChoice=0,exerciseChoice=0;
        const auto& level=index->level(1);
        for(std::size_t sub=0;sub<level.sublevels.size();++sub)for(std::size_t exercise=0;exercise<level.sublevels[sub].exercises.size();++exercise){
            const auto& candidate=index->exercises().at(level.sublevels[sub].exercises[exercise]);
            if(candidate.source.sourceExerciseKey==sourceKey){ck(!row,"exact Level1 source identity occurs once in its hierarchy");row=&candidate;sublevelChoice=static_cast<int>(sub+1);exerciseChoice=static_cast<int>(exercise+1);}
        }
        ck(row&&row->source.levelKey=="1"&&row->label=="Exercise 001: 1212","use the real printed Level1 Exercise001:1212 row, not a forged substitute");
        const auto choices=learn::choices(*row,*catalog);
        ck(choices.size()==2&&choices[0].itemId=="fg:item:000001"&&choices[0].variantId=="fg:variant:007478"&&choices[1].variantId=="fg:variant:007479","source binding offers exactly the two admitted full-route variants in reviewed order");
        const auto expected=choices.at(0);const auto alternate=choices.at(1);
        const auto fullAdmission=catalog->admit(expected.itemId,expected.variantId);
        ck(fullAdmission->practiceAllowed()&&navigation::snapshotAdmission(*fullAdmission)==expected&&fullAdmission->model()->source().events.size()==48,"exact007478 is admitted with its complete content/source binding and48 authored contacts");
        const auto& refusedVariant=catalog->variant(expected.itemId,"fg:variant:000001");
        const auto expectedRefusal="Reference unavailable for this variant. "+lesson::readinessText(refusedVariant);
        std::shared_ptr<const lesson::Admission> refusedAdmission;bool refusedByContract=false;
        try{refusedAdmission=catalog->admit(expected.itemId,"fg:variant:000001");}
        catch(const std::runtime_error& error){refusedByContract=std::string(error.what())==expectedRefusal;}
        ck(!refusedVariant.technicallyRenderable&&refusedByContract&&!refusedAdmission,"retained authored000001 is nonrenderable and raises its exact reference-refusal contract without an Admission");
        const auto sourceModels=[&]{json::Value::Object result;for(const auto& selected:std::vector<std::pair<std::string,std::string>>{{expected.itemId,expected.variantId},{alternate.itemId,alternate.variantId},{expected.itemId,"fg:variant:000001"},{"fg:item:000002","fg:variant:000006"}}){
            result.emplace(selected.first+"/"+selected.second,content::sha256(catalog->variant(selected.first,selected.second).model->source().preservedRecordJson));}return json::Value(std::move(result));};
        const auto modelsBefore=sourceModels();
        const auto rowBytes=[&]{json::Value::Array bindings;for(const auto& binding:row->bindings){json::Value::Array variants;for(const auto& variant:binding.variants)variants.emplace_back(variant);bindings.emplace_back(json::Value::Object{{"item",binding.itemId},{"package_sha256",binding.packageHash},{"variants",std::move(variants)},{"exact",binding.exact},{"supplemental",binding.supplemental}});}return storage::canonical(json::Value::Object{{"source",row->source.sourceExerciseKey},{"index_revision",row->source.indexRevision},{"source_revision",row->source.sourceRevision},{"bindings",std::move(bindings)}});};
        const auto originalRow=rowBytes();
        ck(learn::availability(*row,*catalog)=="Available for exact exercise Practice","availability agrees with exact admitted source choices");
        ck(h.home->navigate(H::Page::Learn),"real Home opens Learn without launching an asynchronous all-extension loader");view.showSourceHierarchy(false);
        choose(view,"learn-source-level",1);pressName(view,"Open level");choose(view,"learn-source-sublevel",sublevelChoice);pressName(view,"Open sublevel");choose(view,"learn-source-selection-mode",1);choose(view,"learn-source-start",exerciseChoice);
        ck(control<juce::TextEditor>(view,"learn-source-details").getText().contains("Available for exact exercise Practice"),"actual selected source hierarchy row advertises exact Practice availability");
        pressName(view,"Exercise details");
        const auto selectedIdentity=[&]{return navigation::snapshotAdmission(*catalog->admit(view.selectedLesson(),view.selectedVariant()));};
        ck(selectedIdentity()==expected&&view.selectedPracticeCell()==0&&control<juce::Button>(view,"practice-selection").isEnabled(),"Exercises Inspect chooses exact admitted007478 instead of refused first authored000001");
        auto& diagnostics=control<juce::TextEditor>(view,"diagnostics");
        auto& inspectedTab=control<desktop::TabView>(view,"tab");
        ck(!diagnostics.isVisible(),"first source Inspect keeps the optional Details footer closed");
        pressId(view,"mode");
        const auto closedTabBounds=inspectedTab.getBounds();
        ck(inspectedTab.isVisible()&&inspectedTab.document()->source().events.size()==48&&inspectedTab.zoom()==1.0,"actual full48 source enters default TAB without revealing optional Details");
        pressId(view,"details");
        ck(diagnostics.isVisible()&&inspectedTab.getHeight()<closedTabBounds.getHeight(),"explicit Details alone opens the optional footer");
        pressId(view,"back");
        ck(!diagnostics.isVisible(),"source hierarchy hides the footer while retaining its explicit choice");
        pressName(view,"Exercise details");pressId(view,"mode");
        ck(diagnostics.isVisible()&&selectedIdentity()==expected,"return through the source hierarchy preserves open Details and exact admission");
        pressId(view,"details");
        ck(!diagnostics.isVisible()&&inspectedTab.getBounds()==closedTabBounds,"closing Details restores the original default notation allocation");
        pressId(view,"back");pressName(view,"Exercise details");
        ck(!diagnostics.isVisible()&&selectedIdentity()==expected,"a later Inspect preserves the explicit closed choice and original exact source");
        stopped("Exercises inspection");
        pressId(view,"back");pressId(view,"learn-source-preview");
        auto& variants=control<juce::ComboBox>(view,"learn-preview-variant");
        ck(variants.getNumItems()==2&&variants.getSelectedId()==1&&variants.getText().toStdString()==catalog->variant(expected.itemId,expected.variantId).label,"normal source Preview defaults to the same exact admitted007478");
        choose(view,"learn-preview-variant",2);pressName(view,"Exercise details");
        ck(selectedIdentity()==alternate,"Inspect preserves explicitly selected non-first Preview variant007479 with its full source binding");
        pressId(view,"back");
        ck(variants.isVisible()&&variants.getSelectedId()==2&&variants.getText().toStdString()==catalog->variant(alternate.itemId,alternate.variantId).label,"Back to Preview preserves the exact explicit alternative, without resetting to first");
        choose(view,"learn-preview-variant",1);pressName(view,"Exercise details");
        ck(selectedIdentity()==expected,"Preview Inspect parity retains selected007478 with unchanged content version/source binding");
        pressId(view,"practice-selection");
        ck(h.home->page()==H::Page::Practice&&h.practice().lessonAdmission()&&navigation::snapshotAdmission(*h.practice().lessonAdmission())==expected,"real Home Practice callback prepares the exact Preview/Inspect007478 admission");
        const auto primaryCaption=[](desktop::PracticeView& practice)->juce::Label&{
            for(auto* child:practice.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))
                if(label->isVisible()&&(label->getText().startsWith("Practice | Level ")||label->getText().startsWith("Focus | Level ")))return *label;
            throw std::runtime_error("Missing readable admitted Practice caption");
        };
        for(const auto presentation:{desktop::presentation::Level::Beginner,desktop::presentation::Level::Advanced,desktop::presentation::Level::Developer}){
            h.practice().setPresentation(presentation,{});
            auto& wholeCaption=primaryCaption(h.practice());
            ck(wholeCaption.getText()=="Practice | Level 1 | Whole case"&&!wholeCaption.getText().contains("\n")&&wholeCaption.getTooltip().contains(expected.itemId+" / "+expected.variantId)&&wholeCaption.getTooltip().contains("Workbook identity:")&&navigation::snapshotAdmission(*h.practice().lessonAdmission())==expected&&h.practice().tabView().document()->source().events.size()==48,"actual full48 Practice has one-line whole-case scope and complete original source identity at presentation level"+std::to_string(static_cast<int>(presentation)));
        }
        auto* independentStart=h.practice().findChildWithID("practice-start");
        ck(independentStart&&!independentStart->getTitle().contains("active Guided Session"),"independent Learn Practice does not claim Guided ownership from its ordinary Session UUID");
        stopped("prepared exact Practice");click(h.practice(),"Back");
        ck(h.home->page()==H::Page::Learn&&selectedIdentity()==expected,"prepared Practice Back returns to the same exact Learn selection");pressId(view,"back");
        ck(variants.isVisible()&&variants.getSelectedId()==1,"return from prepared Practice retains the normal Preview choice");pressName(view,"Exercise details");
        auto prepared=h.practice().lessonAdmission();
        const auto document=control<desktop::TabView>(view,"tab").document();
        ck(!view.selectVariant("fg:variant:000006")&&selectedIdentity()==expected&&control<desktop::TabView>(view,"tab").document()==document,"foreign variant is refused without replacing the exact source/TAB selection");
        ck(!view.selectLesson("synthetic:missing:exact-selection")&&selectedIdentity()==expected,"missing or stale lesson ID cannot replace the selected admission");
        auto& search=control<juce::TextEditor>(view,"lesson-search");search.setText("synthetic-no-match-exact-selection-regression",true);marker();
        const auto status=control<juce::Label>(view,"lesson-search-status").getText();
        ck(control<juce::ComboBox>(view,"lessons").getNumItems()==0&&selectedIdentity()==expected&&status.contains("No source-backed lesson cases match")&&status.contains("fg:item:000001 / fg:variant:007478 remains selected")&&status.contains("not a search match"),"zero-result search explicitly retains the exact prior selection and its recovery boundary");
        ck(control<juce::Button>(view,"practice-selection").isEnabled(),"empty search results do not fabricate unavailability for the retained admitted selection");
        pressId(view,"practice-selection");ck(h.home->page()==H::Page::Practice&&navigation::snapshotAdmission(*h.practice().lessonAdmission())==expected,"enabled Practice under an empty search prepares only the explicitly retained identity");prepared=h.practice().lessonAdmission();stopped("empty search Practice");click(h.practice(),"Back");
        pressId(view,"lesson-search-clear");marker();
        ck(search.getText().isEmpty()&&control<juce::ComboBox>(view,"lessons").getNumItems()==static_cast<int>(catalog->lessons().size())&&selectedIdentity()==expected,"Clear Search restores the finite catalog while preserving exact selection");
        ck(view.selectVariant("fg:variant:000001")&&!control<juce::Button>(view,"practice-selection").isEnabled()&&control<juce::Button>(view,"practice-selection").getTitle().contains("runtime admission refused fg:item:000001 / fg:variant:000001"),"authored000001 remains inspectable with explicit disabled Practice refusal");
        ck(!view.practiceSelected()&&h.home->page()==H::Page::Learn&&h.practice().lessonAdmission()==prepared,"refused Practice call leaves previously prepared exact admission untouched");
        ck(view.selectVariant(expected.variantId)&&selectedIdentity()==expected,"explicit valid selection restores exact007478 after refused inspection");
        for(const auto& fault:std::vector<std::string>{"foreign","refused","stale"}){
            auto copy=*row;for(auto& binding:copy.bindings){if(fault=="stale")binding.packageHash=std::string(64,'0');else binding.variants={fault=="foreign"?"fg:variant:000006":"fg:variant:000001"};}
            ck(learn::choices(copy,*catalog).empty(),fault+" source-choice value copy fails closed through the existing admission helper");
            ck(selectedIdentity()==expected&&rowBytes()==originalRow&&h.practice().lessonAdmission()==prepared,fault+" helper rejection does not mutate real source, selected case or Practice owner");
        }
        auto staleEntry=row->source;staleEntry.mappingExtent=navigation::ExerciseMappingExtent::ExactSourceUnit;staleEntry.admission=expected;staleEntry.admission->sourceBinding+="/synthetic-stale";bool staleRefused=false;
        try{navigation::resolveExerciseAdmission(*catalog,staleEntry);}catch(const std::invalid_argument&){staleRefused=true;}
        ck(staleRefused&&selectedIdentity()==expected,"stale complete admission snapshot cannot resolve against the real catalog");stopped("selection rejection checks");
        ck(view.selectLesson("fg:item:000002")&&view.selectVariant("fg:variant:000006"),"select the retained representative L3 direction for authored cell qualification");
        const auto whole=catalog->admit(view.selectedLesson(),view.selectedVariant());const auto wholeIdentity=whole->identity();const auto wholeSource=whole->model()->source().preservedRecordJson;
        for(const auto ordinal:{1u,5u}){
            choose(view,"practice-span",static_cast<int>(ordinal+1));const auto cell=catalog->admitCell(view.selectedLesson(),view.selectedVariant(),ordinal);const auto cellIdentity=cell->identity();const auto label=desktop::lessonSelectionLabel(*cell);
            ck(view.selectedPracticeCell()==ordinal&&cell->practiceAllowed()&&cell->model()->source().events.size()==4&&cell->model()->source().preservedRecordJson==wholeSource,"listed source cell"+std::to_string(ordinal)+" preserves the original authored record with its bounded four-contact selection");
            for(const auto presentation:{desktop::presentation::Level::Beginner,desktop::presentation::Level::Advanced,desktop::presentation::Level::Developer}){
                view.setPresentation(presentation,{});const auto summary=control<juce::Label>(view,"summary").getText();
                ck(summary.contains(label)&&summary.contains("This cell is not a full direction or source task.")&&summary.contains("Attempt")&&summary.contains("credit"),"cell"+std::to_string(ordinal)+" qualification and no-credit boundary survive presentation level"+std::to_string(static_cast<int>(presentation)));
                ck(view.selectedPracticeCell()==ordinal&&catalog->admitCell(view.selectedLesson(),view.selectedVariant(),ordinal)->identity()==cellIdentity&&whole->identity()==wholeIdentity,"presentation disclosure preserves exact cell and whole-direction identities");
                ck(h.practice().configureLesson(cell,60),"typed admitted cell prepares its stopped Practice caption without Start");
                h.practice().setPresentation(presentation,{});
                auto& caption=primaryCaption(h.practice());
                ck(caption.getText()==juce::String("Practice | Level 3 | Cell ")+juce::String(ordinal)+" of 5 (partial)"&&caption.getTooltip().contains(label)&&h.practice().lessonAdmission()->identity()==cellIdentity,"cell"+std::to_string(ordinal)+" partial scope stays primary at presentation level"+std::to_string(static_cast<int>(presentation))+" with unchanged admitted identity and full qualifier");
            }
        }
        ck(!view.selectPracticeCell(6)&&view.selectedPracticeCell()==5,"unsupported arbitrary cell cutpoint refuses while retaining the exact listed cell");choose(view,"practice-span",1);
        ck(view.selectedPracticeCell()==0&&catalog->admit(view.selectedLesson(),view.selectedVariant())->identity()==wholeIdentity,"Whole selected direction restores the unchanged admitted whole identity");
        ck(h.practice().configureLesson(whole,60)&&primaryCaption(h.practice()).getText()=="Practice | Level 3 | Whole case","whole-case restoration clears only the primary partial-caption qualification");
        stopped("cell disclosure checks");
        ck(resourcePins()==pinsBefore&&sourceModels()==modelsBefore&&rowBytes()==originalRow&&view.preparedSourceIndex()==index&&view.catalog()==catalog,"source resource pins, all four selected authored records, exact source row and catalog/index owners remain unchanged");
        const auto after=snapshot("exact-selection-after");
        ck(after.data.object().at("authoritative")==before.data.object().at("authoritative"),"inspection, preparation, search, fail-closed helpers and disclosure preserve all 13 authoritative Store tables byte-for-byte");
        capture_fixture::write(out/"resource-pins.json",storage::canonical(pinsBefore));
        capture_fixture::write(out/"source-model-pins.json",storage::canonical(modelsBefore));
        capture_fixture::write(out/"exact-source-row.json",originalRow);
        capture_fixture::write(out/"exact-admission.json",storage::canonical(fullAdmission->identity()));
        capture_fixture::write(out/"summary.json",storage::canonical(json::Value::Object{{"status","PASS"},{"checks",json::Value::fromInteger(checks)},{"mode","--exact-selection-regression"},{"resources",resources.string()},{"extension","level001-extension"},{"actual_home",true},{"actual_store",true},{"profile_path",(h.dir/"profile.sqlite").string()},{"session_owner",h.sessionId},{"admitted_item",expected.itemId},{"admitted_variant",expected.variantId},{"explicit_alternate",alternate.variantId},{"source_identity",sourceKey},{"sessions",json::Value::fromInteger(1)},{"attempts",json::Value::fromInteger(0)},{"finalized",json::Value::fromInteger(0)},{"native_opens",json::Value::fromInteger(nativeOpens)},{"software_connections",json::Value::fromInteger(connections)},{"installed_gui",false},{"physical_listening",false},{"curriculum_credit",false}}));
        std::cout<<"PASS "<<checks<<" finite exact source Preview/Inspect/Practice selection checks; no Start, queue, audio or credit\n";return 0;
    }
    if(quitOnly&&!shutdownActiveOnly){h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);h.home->toFront(true);marker();}
    if(learnLoadingOnly||readinessOnly){
        if(learnLoadingOnly){h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);h.home->toFront(true);}marker();
        const std::vector<std::filesystem::path> finite{resources/lesson::Catalog::installedExtensionDirectoryNames().front()};
        using F=desktop::source_routes::Family;
        const auto before=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        auto entered=std::make_shared<std::atomic<bool>>(false),release=std::make_shared<std::atomic<bool>>(false);
        struct ReleaseBarrierOnExit { std::shared_ptr<std::atomic<bool>> release; ~ReleaseBarrierOnExit(){release->store(true);} } releaseBarrierOnExit{release};
        const auto barrier=[entered,release]{
            *entered=true;const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(8);
            while(!release->load()){if(std::chrono::steady_clock::now()>end)throw std::runtime_error("finite Learn barrier watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}
        };
        const auto begin=std::chrono::steady_clock::now();
        ck(L::beginLearn(*h.home,resources,finite,{F::Recipe},barrier),"finite Learn entry accepted without synchronous source/catalog/gate construction");
        ck(std::chrono::steady_clock::now()-begin<std::chrono::milliseconds(100),"Learn entry returns within100ms while worker verifies");
        ck(h.home->page()==H::Page::Learn&&(readinessOnly?view.isVisible():view.isShowing())&&L::loading(*h.home),"Learn is visible with pending worker");
        ck(control<juce::TextEditor>(view,"learn-source-details").getText().contains("Preparing exercises and Practice"),"loading status is visible before verified data");
        ck(L::beginLearn(*h.home,resources,finite,{F::Recipe})&&desktop::sourceDataPool().getNumJobs()==1,"repeat same-package entry retains exactly one job");
        h.wait([&]{return entered->load();},"verified index phase");marker();
        ck(view.preparedSourceIndex()&&control<juce::ComboBox>(view,"learn-source-level").getNumItems()==105&&!view.catalog(),"all105 verified source levels publish before catalog completion");
        ck(!control<juce::Button>(view,"learn-source-preview").isEnabled(),"unverified catalog cannot enable Practice preview");
        choose(view,"learn-source-level",12);pressName(view,"Open level");choose(view,"learn-source-sublevel",1);pressName(view,"Open sublevel");choose(view,"learn-source-start",2);
        ck(!control<juce::ComboBox>(view,"learn-source-start").getText().isEmpty(),"verified source metadata remains usable during catalog loading");
        ck(!L::loading(*h.home)&&!view.catalog()&&control<juce::ComboBox>(view,"learn-source-start").getText().contains("Choose this sublevel to verify Practice")&&!control<juce::Button>(view,"learn-source-preview").isEnabled(),"group change cancels the old full-load ticket and truthfully leaves the new group unverified");
        const auto selectedIndex=view.preparedSourceIndex();
        const auto& selectedRow=selectedIndex->exercises().at(selectedIndex->level(12).sublevels.front().exercises.at(1));
        std::vector<lesson::SelectedCatalogStore::Request> selectedRequests;
        for(const auto& binding:selectedRow.bindings)selectedRequests.push_back({binding.itemId,binding.packageHash});
        // The selected Store uses the complete compiled path registry, but this
        // fixture prepares only the exact row above; full reentry stays finite.
        L::configureFiniteSelectedFixture(*h.home,resources);
        ck(!selectedRequests.empty()&&L::beginSelected(*h.home,selectedRequests,view.sourceGroupRevision())&&L::loading(*h.home),"exact selected row queues a new current preparation behind the canceled full-load barrier");
        const auto sourceSelection=control<juce::ComboBox>(view,"learn-source-start").getText();
        const auto pendingText=control<juce::TextEditor>(view,"learn-source-details").getText();
        ck(sourceSelection.contains("Preparing selected exercise Practice")&&pendingText.contains("Preparing selected exercise Practice")&&!pendingText.contains("Practice unavailable")&&!pendingText.contains("Practice catalog unavailable"),"index-ready catalog-pending rows say preparing instead of permanent unavailability");
        ck(!control<juce::Button>(view,"learn-source-preview").isEnabled(),"preparing wording does not enable unverified Practice");
        view.setPresentation(desktop::presentation::Level::Beginner,{});
        ck(!control<juce::TextEditor>(view,"learn-source-details").getText().contains("PDF")&&!control<juce::TextEditor>(view,"learn-source-details").getText().contains("TXT"),"ordinary Beginner omits authoring locators");
        view.setPresentation(desktop::presentation::Level::Advanced,{});
        ck(!control<juce::TextEditor>(view,"learn-source-details").getText().contains("PDF")&&!control<juce::TextEditor>(view,"learn-source-details").getText().contains("TXT"),"Advanced omits authoring locators without replacing the exercise");
        view.setPresentation(desktop::presentation::Level::Developer,{});
        ck(control<juce::TextEditor>(view,"learn-source-details").getText().contains("PDF")&&control<juce::ComboBox>(view,"learn-source-start").getSelectedId()==2,"Developer retains provenance and exact selected endpoint");
        view.setPresentation(desktop::presentation::Level::Beginner,{});

        const auto back=std::chrono::steady_clock::now();
        if(readinessOnly){
            pressName(view,"Back");pressName(view,"Back");pressName(view,"Back");
            ck(h.home->page()==H::Page::Home&&!L::loading(*h.home)&&std::chrono::steady_clock::now()-back<std::chrono::milliseconds(100),"actual hierarchy Back cancels pending catalog intent promptly on returning Home");
            ck(control<juce::Button>(*h.home,"home-learn").getButtonText()=="Learn"&&!control<juce::Button>(*h.home,"home-start-learning").isVisible(),"canceled partial preparation keeps the stable sole Home Learn entry");
        }else{
            h.home->openAudioSettings();
            ck(h.home->page()==H::Page::Audio&&!L::loading(*h.home)&&std::chrono::steady_clock::now()-back<std::chrono::milliseconds(100),"Audio cancels Learn publication promptly while verification waits");
        }
        *release=true;h.wait([]{return !desktop::SourceLibraryView::hasBackgroundWork();},"canceled Learn worker boundary");marker();
        ck(h.home->page()==(readinessOnly?H::Page::Home:H::Page::Audio)&&!view.catalog(),"canceled catalog publication cannot redirect or populate a newer page");
        const auto ready=std::chrono::steady_clock::now();
        ck(L::beginLearn(*h.home,resources,finite,{F::Recipe}),"reentry reuses verified index and prepares finite catalog plus Recipe gate");
        h.wait([&]{return !L::loading(*h.home);},"finite Learn ready");
        if(readinessOnly){
            pressName(view,"Open level");pressName(view,"Open sublevel");
            ck(control<juce::ComboBox>(view,"learn-source-start").getSelectedId()==2&&control<juce::ComboBox>(view,"learn-source-stop").getSelectedId()==2,"real Back and same-level reentry retain prior exercise endpoints");
        }
        ck(!control<juce::ComboBox>(view,"learn-source-start").getText().contains("Preparing selected exercise Practice")&&!control<juce::ComboBox>(view,"learn-source-start").getText().contains("Practice catalog unavailable"),"verified catalog refreshes existing endpoint labels without retaining a loading diagnosis");

        trace<<"finite_ready_ms\t"<<std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-ready).count()<<'\n';
        ck(view.catalog()&&L::recipes(*h.home)==17,"finite catalog and exact17 Recipe routes publish after closed gates");
        ck(!view.hasExplicitSelection(),"background catalog publication keeps its default separate from explicit learner choice");
        if(readinessOnly){
            int probeLevel=0;
            for(const auto& level:view.preparedSourceIndex()->levels())if(level.sublevels.size()>1&&level.sublevels[1].exercises.size()>1){probeLevel=level.number;break;}
            ck(probeLevel>0,"verified fixture has a non-first sublevel with non-first endpoint for reentry coverage");
            pressName(view,"Back");pressName(view,"Back");
            choose(view,"learn-source-level",probeLevel);pressName(view,"Open level");choose(view,"learn-source-sublevel",2);pressName(view,"Open sublevel");choose(view,"learn-source-start",2);
            pressName(view,"Back");pressName(view,"Back");pressName(view,"Back");
            ck(h.home->page()==H::Page::Home&&!control<juce::Button>(*h.home,"home-practice").isEnabled(),"default catalog and hierarchy choices do not silently select an inspected case on Home");
            ck(L::beginLearn(*h.home,resources,finite,{})&&!L::loading(*h.home),"same-package non-first selection revisit reuses verified data without a job");
            pressName(view,"Open level");
            ck(control<juce::ComboBox>(view,"learn-source-level").getSelectedId()==probeLevel&&control<juce::ComboBox>(view,"learn-source-sublevel").getSelectedId()==2,"Back and reentry retain a non-first sublevel key");
            pressName(view,"Open sublevel");
            ck(control<juce::ComboBox>(view,"learn-source-start").getSelectedId()==2,"non-first sublevel also retains its own non-first endpoint");
            pressName(view,"Back");pressName(view,"Back");choose(view,"learn-source-level",12);pressName(view,"Open level");choose(view,"learn-source-sublevel",1);pressName(view,"Open sublevel");
            ck(control<juce::ComboBox>(view,"learn-source-start").getSelectedId()==1,"explicit different-group selection resets endpoints to its first exercise");
            choose(view,"learn-source-start",2);
        }

        ck(h.home->page()==H::Page::Learn&&control<juce::ComboBox>(view,"learn-source-level").getSelectedId()==12&&control<juce::ComboBox>(view,"learn-source-start").getSelectedId()==2,"catalog publication preserves current source level and endpoint stage");
        ck((readinessOnly?control<juce::Button>(view,"learn-source-preview").isVisible():control<juce::Button>(view,"learn-source-preview").isShowing())&&control<juce::Button>(view,"learn-source-preview").isEnabled(),"verified catalog enables preview in the existing source stage");
        const auto catalog=view.catalog();const auto index=view.preparedSourceIndex();
        ck(!L::beginLearn(*h.home,resources,{},{}),"different extension extent is refused before cached catalog reuse");
        ck(!L::beginLearn(*h.home,resources/"foreign-root",finite,{}),"different resource root is refused before cached index/gate reuse");
        ck(view.catalog()==catalog&&view.preparedSourceIndex()==index&&!L::loading(*h.home),"differing-package refusal leaves original owned prepared data intact");
        std::string manualSource;for(const auto& row:index->exercises())if(desktop::source_routes::familyFor(row.source.sourceExerciseKey)==F::Manual){manualSource=row.source.sourceExerciseKey;break;}
        ck(!manualSource.empty()&&L::beginLearn(*h.home,resources,finite,{F::Manual}),"later same-package Manual family preparation starts");
        h.wait([&]{return !L::loading(*h.home);},"finite incremental Manual gate");
        ck(L::manual(*h.home,manualSource)&&L::recipes(*h.home)==17,"published Manual gate retains all17 earlier Recipe routes after consumed private cache");
        ck(view.catalog()==catalog&&view.preparedSourceIndex()==index,"incremental family construction reuses immutable verified catalog and index");
        pressId(view,"learn-source-preview");
        const auto indexCopy=std::make_shared<const learn::SourceIndex>(*index);
        ck(!view.installPreparedSourceIndex(indexCopy)&&view.preparedSourceIndex()==index,"staged Preview refuses replacement of its owned row pointers");
        ck(view.installPreparedSourceIndex(index),"Preview reuses its already-owned exact index safely");
        pressId(view,"learn-queue-confirm");
        ck(!view.installPreparedSourceIndex(indexCopy)&&(readinessOnly?control<juce::Button>(view,"learn-queue-open").isVisible():control<juce::Button>(view,"learn-queue-open").isShowing()),"Ready queue also refuses index replacement while original row remains usable");
        ck(L::beginLearn(*h.home,resources,finite,{})&&!L::loading(*h.home),"complete same-package revisit requires no duplicate verification job");
        entered->store(false);release->store(false);
        ck(L::beginLearn(*h.home,resources,finite,{},barrier)&&!L::loading(*h.home),"fully prepared revisit avoids even an unnecessary queued barrier");
        ck(L::beginLearn(*h.home,resources,finite,{F::Manual},barrier),"controlled repeat prepares owned worker for close accounting");
        h.wait([&]{return entered->load();},"Learn close barrier");
        const auto quit=std::chrono::steady_clock::now();
        ck(!h.home->requestClose()&&h.home->closeState()==H::CloseState::Waiting&&!L::loading(*h.home)&&std::chrono::steady_clock::now()-quit<std::chrono::milliseconds(100),"Quit cancels Learn intent and promptly refuses until shared worker boundary");
        *release=true;h.wait([]{return !desktop::SourceLibraryView::hasBackgroundWork();},"Learn close worker boundary");marker();
        ck(h.home->requestClose(),"normal guarded Quit succeeds after Learn worker completes");
        const auto after=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        ck(*before.data.find("authoritative")==*after.data.find("authoritative"),"loading/index/preview/cancel creates no Practice Session, Attempt, attestation or credit");
        ck(nativeOpens==0&&connections==0,"Learn construction performs no audio device connection");
        {
            Harness missing(out,"missing-profile");if(learnLoadingOnly){missing.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);missing.home->toFront(true);}auto& missingView=A::lessons(*missing.home);
            ck(L::beginLearn(*missing.home,resources/"absent-package",{},{}),"missing package enters responsive loading state");
            missing.wait([&]{return !L::loading(*missing.home);},"missing Learn package response");
            ck(!missingView.catalog()&&control<juce::TextEditor>(missingView,"learn-source-details").getText().contains("Could not prepare exercises:"),"missing package fails closed with explicit visible error");
            ck(missing.home->navigate(H::Page::Home),"Back remains available after verification failure");
        }
        {
            Harness guided(out,"guided-profile");if(learnLoadingOnly){guided.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);guided.home->toFront(true);}
            auto& guidedView=L::guided(*guided.home);auto& guidedLessons=A::lessons(*guided.home);
            guided.wait([&]{return !guidedView.busy();},"Guided initial summary");
            const auto guidedBefore=capture_fixture::confirmed(guided.store->snapshot(storage::newUuid()));
            entered->store(false);release->store(false);const auto guidedBegin=std::chrono::steady_clock::now();
            ck(L::beginGuided(*guided.home,resources,finite,barrier)&&guided.home->page()==H::Page::Guided&&std::chrono::steady_clock::now()-guidedBegin<std::chrono::milliseconds(100),"first Guided entry is visible and immediate before catalog verification");
            guided.wait([&]{return entered->load();},"Guided source index phase");
            ck(control<juce::Label>(guidedView,"guided-plan-state").getText().contains("Preparing the verified")&&!control<juce::Button>(guidedView,"build").isEnabled()&&!control<juce::Button>(guidedView,"start").isEnabled(),"Guided shows catalog preparation and disables premature plan/session actions");
            ck(!guidedView.buildPlan()&&!guidedView.startSession(),"direct Guided actions also refuse while catalog is unverified");
            ck(guidedView.requestBack()&&guided.home->page()==H::Page::Home&&!L::loading(*guided.home),"Guided Back cancels pending catalog intent");
            *release=true;guided.wait([]{return !desktop::SourceLibraryView::hasBackgroundWork();},"canceled Guided worker boundary");marker();
            ck(!guidedLessons.catalog()&&guided.home->page()==H::Page::Home,"late canceled Guided catalog does not redirect Home");
            ck(L::beginGuided(*guided.home,resources,finite),"Guided retry reuses verified private index");
            guided.wait([&]{return !L::loading(*guided.home);},"finite Guided catalog ready");
            ck(guidedLessons.catalog()&&!guidedView.planText().empty()&&control<juce::Button>(guidedView,"build").isEnabled(),"verified finite catalog enables original Guided planning controls");
            const auto plan=guidedView.planText();const auto selected=guidedLessons.selectedLesson();
            ck(L::beginGuided(*guided.home,resources,finite)&&!L::loading(*guided.home)&&guidedLessons.selectedLesson()==selected&&guidedView.planText()==plan,"cached Guided revisit preserves original selected case and plan without another worker");
            const auto guidedAfter=capture_fixture::confirmed(guided.store->snapshot(storage::newUuid()));
            ck(*guidedBefore.data.find("authoritative")==*guidedAfter.data.find("authoritative"),"Guided preparation and cancel create no Session, Attempt or credit");
        }
        {
            Harness workbook(out,"workbook-profile");if(learnLoadingOnly){workbook.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);workbook.home->toFront(true);}auto& bookView=A::lessons(*workbook.home);
            entered->store(false);release->store(false);const auto bookBegin=std::chrono::steady_clock::now();
            ck(L::beginBook(*workbook.home,resources,finite,"fg:workbook:000012",barrier)&&std::chrono::steady_clock::now()-bookBegin<std::chrono::milliseconds(100),"workbook entry starts one asynchronous verified catalog instead of two synchronous loads");
            workbook.wait([&]{return entered->load();},"workbook metadata phase");marker();
            choose(bookView,"learn-source-level",12);pressName(bookView,"Open level");choose(bookView,"learn-source-sublevel",1);pressName(bookView,"Open sublevel");choose(bookView,"learn-source-start",2);
            *release=true;workbook.wait([&]{return !L::loading(*workbook.home);},"workbook catalog ready");
            ck((readinessOnly?control<juce::Button>(bookView,"learn-source-preview").isVisible():control<juce::Button>(bookView,"learn-source-preview").isShowing())&&control<juce::ComboBox>(bookView,"learn-source-start").getSelectedId()==2,"newer source selection wins over pending workbook case intent");
            workbook.wait([]{return !desktop::SourceLibraryView::hasBackgroundWork();},"canceled workbook worker boundary");marker();
            ck(!bookView.catalog(),"source group change cancels the original workbook load without publishing a stale catalog");
            ck(L::beginBook(*workbook.home,resources,finite,"fg:workbook:000012"),"explicit workbook reentry starts fresh preparation after canceled publication");
            workbook.wait([&]{return !L::loading(*workbook.home);},"explicit workbook reentry ready");
            ck(bookView.catalog()&&bookView.catalog()->lesson(bookView.selectedLesson()).record.object().at("workbook_id").string()=="fg:workbook:000012","fresh workbook reentry selects only the exact requested owned workbook");
            ck(L::beginBook(*workbook.home,resources,finite,"fg:workbook:000012")&&!L::loading(*workbook.home)&&bookView.catalog()->lesson(bookView.selectedLesson()).record.object().at("workbook_id").string()=="fg:workbook:000012","cached workbook entry selects only the exact requested owned workbook");
            ck(L::beginBook(*workbook.home,resources,finite,"foreign-workbook")&&control<juce::TextEditor>(bookView,"learn-source-details").getText().contains("No installed admitted case"),"unknown workbook retains explicit source-view refusal instead of substituting a case");
            ck(workbook.home->navigate(H::Page::SourceLibrary),"workbook Back destination remains original source library");
        }
        h.wait([]{return !desktop::SourceLibraryView::hasBackgroundWork();},"final Learn worker boundary");
        std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"status\":\"PASS\",\"native_gui\":"<<(readinessOnly?"false":"true")<<",\"finite_catalog\":true,\"curriculum_credit\":false}\n";
        std::cout<<"PASS "<<checks<<(readinessOnly?" component Learn readiness checks; no foreground or real audio":" scoped native Learn loading checks; finite catalog prefix and Recipe/Manual only")<<"\n";return 0;
    }
    if(browseOnly){
        h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);h.home->toFront(true);
        auto& browser=L::browser(*h.home);
        const auto snapshotBefore=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        const auto begin=std::chrono::steady_clock::now();L::browse(*h.home,resources);
        ck(std::chrono::steady_clock::now()-begin<std::chrono::milliseconds(100),"Browse enters immediately without synchronous source/runtime verification");
        ck(h.home->page()==H::Page::SourceLibrary&&browser.isVisible()&&browser.isLoading(),"loading browser is visible before data is ready");
        L::browse(*h.home,resources);ck(browser.isLoading(),"repeated Browse retains one pending load");
        pressId(browser,"source-library-back");ck(h.home->page()==H::Page::Home&&!browser.isLoading(),"Back cancels loading and returns to Home immediately");
        ck(!desktop::SourceBrowseTestAccess::theoryAttempted(browser),"cancel before publication leaves theory initialization retryable");
        const auto verifiedBegin=std::chrono::steady_clock::now();
        L::browse(*h.home,resources);
        const auto watchdog=std::chrono::steady_clock::now()+std::chrono::seconds(120);int ticks=0;
        while(browser.isLoading()){
            if(std::chrono::steady_clock::now()>watchdog)throw std::runtime_error("Browse verification watchdog");
            h.tick();pump();++ticks;
        }
        trace<<"responsive_message_pumps\t"<<ticks<<'\n';
        trace<<"source_context_ready_ms\t"<<std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-verifiedBegin).count()<<'\n';
        ck(browser.workbookCount()==105&&browser.bookContextAvailable(),"full closed source210 and Book105 context verified on worker");
        ck(!view.catalog(),"Browse does not initialize or navigate to the Learn catalog");
        auto& books=control<juce::ComboBox>(browser,"source-library-workbooks");
        auto& sections=control<juce::ComboBox>(browser,"source-library-section");
        auto& volumes=control<juce::ComboBox>(browser,"source-library-volume");
        auto& tasks=control<juce::ListBox>(browser,"source-library-source-tasks");
        ck(volumes.getNumItems()==3&&sections.getNumItems()==5&&books.getNumItems()==11&&books.getSelectedId()==1,"default Volume1 SectionI owns exactly levels1–11");
        std::set<int> visited;std::size_t allTasks=0;
        for(int v=1;v<=3;++v){choose(browser,"source-library-volume",v);
            for(std::size_t i=0;i<desktop::browseSections.size();++i){const auto& s=desktop::browseSections[i];if(s.volume!=v)continue;
                choose(browser,"source-library-section",static_cast<int>(i)+1);
                ck(books.getNumItems()==s.last-s.first+1,"section workbook extent "+std::string{s.name});
                for(int level=s.first;level<=s.last;++level)ck(books.indexOfItemId(level)>=0&&visited.insert(level).second,"exact unique authored section level "+std::to_string(level));
                allTasks+=static_cast<std::size_t>(tasks.getListBoxModel()->getNumRows());
            }
        }
        ck(visited.size()==105&&allTasks==7321,"all105 levels and all7321 distinct source rows reachable across16 authored sections");
        ck(sections.getText()=="Section Final"&&books.getSelectedId()==105,"Final remains authored Final rather than invented SectionXVI");
        choose(browser,"source-library-volume",1);choose(browser,"source-library-section",1);
        ck(tasks.getListBoxModel()->getNumRows()>108,"SectionI lists exercises across its workbooks rather than only Level1");
        tasks.selectRow(108);pump();ck(books.getSelectedId()==2,"section exercise selection re-resolves its exact workbook");
        ck(desktop::SourceBrowseTestAccess::selectedIdentity(browser)==desktop::SourceBrowseTestAccess::firstIdentity(browser,2),"cross-workbook row retains exact owned Level2 first-source identity");
        ck(desktop::SourceBrowseTestAccess::available(browser)==0,"initial Browse grants zero runtime routes and performs no bulk activity preparation");
        ck(desktop::source_routes::familyFor("foreign/caller/key")==desktop::source_routes::Family::None,"foreign source has no family preparation route");
        ck(desktop::source_routes::familyFor("level053/moduleb/p003-t1-r1-c2/cmajrp")==desktop::source_routes::Family::Graph,"reviewed legacy duplicate follows existing Graph priority");
        auto& search=control<juce::TextEditor>(browser,"source-library-search");search.setText("graduation",true);marker();
        ck(books.getNumItems()==0,"Original-only graduation term is excluded from approved public metadata search");
        search.setText("G01",true);marker();
        ck(books.getNumItems()==1&&books.getSelectedId()==12&&sections.getText()=="Section II","global approved G01 metadata search preserves exact Level12 and authored section");
        search.setText("Level 105",true);marker();ck(books.getSelectedId()==105&&volumes.getSelectedId()==3,"global exact level search reaches Final across volumes");
        search.setText("Level 68",true);marker();
        const auto recipeRow=desktop::SourceBrowseTestAccess::recipeRow(browser);ck(recipeRow>=0,"trusted Level68 recipe route is reachable");
        tasks.selectRow(recipeRow);pump();const auto recipeSource=desktop::SourceBrowseTestAccess::selectedIdentity(browser);
        L::prepare(*h.home,resources,recipeSource);ck(browser.isPreparingActivity(),"explicit source choice starts family verification asynchronously");
        h.wait([&]{return !browser.isPreparingActivity();},"selected recipe family verification");
        ck(browser.onManualTaskAvailable&&browser.onManualTaskAvailable(recipeSource),"selected existing Recipe family passes unchanged closed installed gate");
        ck(desktop::SourceBrowseTestAccess::available(browser)==17,"preparing Recipe initializes exactly its17 source routes rather than every family");
        pressId(browser,"source-library-back");L::browse(*h.home,resources);
        ck(!browser.isLoading()&&browser.workbookCount()==105,"repeat visit reuses verified current payload");
        auto& status=control<juce::Label>(browser,"source-library-status");
        ck(!status.getText().containsIgnoreCase("verification failed"),"installed runtime preparation does not report an exception");
        const auto snapshotAfter=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
        ck(snapshotBefore.data.find("authoritative")&&*snapshotBefore.data.find("authoritative")==*snapshotAfter.data.find("authoritative"),"browse/search/cancel create no Attempt or Session changes, attestation or credit");
        ck(nativeOpens==0&&connections==0,"Browse opens no real or substituted audio device");
        {
            desktop::SourceLibraryView canceledTheory;
            canceledTheory.beginBrowse(resources/"source-library");canceledTheory.cancelLoading();
            ck(canceledTheory.ensureTheoryContext(resources/"source-library"),"cancel then same-root Learn theory call performs successful existing exact verification");
        }
        auto entered=std::make_shared<std::atomic<bool>>(false),release=std::make_shared<std::atomic<bool>>(false);
        browser.prepareActivity(recipeSource,[entered,release](const desktop::SourceLibraryView::LoadTicket&){
            const desktop::SourceTaskLibraries::ActiveLoad active;
            *entered=true;const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(3);
            while(!release->load()&&std::chrono::steady_clock::now()<end)std::this_thread::sleep_for(std::chrono::milliseconds(1));
            return []{};
        },[]{return false;});
        h.wait([&]{return entered->load();},"controlled in-flight family");pressId(browser,"source-library-back");
        const auto closeClick=std::chrono::steady_clock::now();
        ck(!h.home->requestClose()&&std::chrono::steady_clock::now()-closeClick<std::chrono::milliseconds(100),"Quit cancels and refuses promptly while read-only source preparation finishes");
        const auto learnClick=std::chrono::steady_clock::now();pressId(*h.home,"home-learn");
        ck(std::chrono::steady_clock::now()-learnClick<std::chrono::milliseconds(100)&&h.home->page()==H::Page::Home,"cancelled in-flight family never blocks Learn click on worker initialization");
        ck(control<juce::Label>(*h.home,"home-guidance").getText().contains("Finishing the earlier"),"deferred Learn entry shows explicit responsive Home status");
        ck(!h.home->requestClose()&&!L::pendingLearnEntry(*h.home),"Quit cancels previously deferred Learn intent before refusing background destruction");
        h.home->openAudioSettings();ck(h.home->page()==H::Page::Audio,"direct Audio helper cancels deferred Learn intent");*release=true;
        h.wait([&]{return desktop::SourceTaskLibraries::activeLoads.load()==0;},"controlled family release");
        h.home->returnFromAudioSettings();for(int i=0;i<20;++i){h.tick();pump();}
        ck(h.home->page()==H::Page::Home,"Audio return cancels queued Learn and stale activity completion cannot redirect");
        h.wait([]{return !desktop::SourceLibraryView::hasBackgroundWork();},"source worker boundary");
        ck(h.home->requestClose(),"normal guarded Quit succeeds after source worker boundary");
        browser.beginBrowse(resources/"absent-source-library");
        h.wait([&]{return !browser.isLoading();},"missing library response");
        ck(browser.workbookCount()==0&&status.getText().startsWith("Library unavailable:"),"missing source fails closed with explicit error and Back available");
        auto doomed=std::make_unique<desktop::SourceLibraryView>();doomed->beginBrowse(resources/"absent-source-library");doomed.reset();for(int i=0;i<30;++i)pump();
        ck(true,"destroying an in-flight browser safely discards its completion");
        std::cout<<"PASS "<<checks<<" scoped native Browse checks; workbooks105 sourceRows7321; VM qualification deferred\n";return 0;
    }
    std::vector<std::filesystem::path> extensions;for(const auto& directory:lesson::Catalog::installedExtensionDirectoryNames())extensions.push_back(resources/directory);
    if(quitOnly||shutdownOnly)extensions.resize(1); // Exact closed prefix: the one Level12 Rung02 used by the Quit capture.
    ck(view.load(resources/"representative-controls",extensions),(quitOnly||shutdownOnly)?"load exact finite Level12 Rung02 queue fixture and representative base":"load actual finite catalog and all installed extensions");
    ck(view.loadSourceIndex(resources/"learn-source-index"),"load bundled hash-pinned source index");L::indexLoaded(*h.home);
    const auto index=learn::SourceIndex::load(resources/"learn-source-index");
    auto snapshot=[&](const std::string& name){auto r=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));capture_fixture::write(out/(name+".json"),storage::canonical(r.data));return r;};
    auto counts=[&](const storage::Reply& r,std::size_t attempts,std::size_t sessions){const auto& a=r.data.object().at("authoritative").object();ck(a.at("identity").array().size()==attempts&&a.at("session").array().size()==sessions&&a.at("source_attestation").array().empty(),"exact Attempt/Session counts; no source credit");};
    auto enterQueueLearn=[&]{
        // The console default owns argv resources, not the ordinary App resource
        // locator (which may find an unrelated development bundle). Native Home
        // entry campaigns retain their existing actual button dispatch.
        if(argc==3){
            if(!L::beginFastLearn(*h.home,resources,extensions))throw std::runtime_error("Pinned Home Learn coordinator refused default queue fixture resources");
        }else if(quitOnly||shutdownOnly){h.home->navigate(H::Page::Learn);view.showSourceHierarchy();}
        else click(*h.home,"Learn");
    };
    auto loadRange=[&](int level,int first,int last){
        enterQueueLearn();
        choose(view,"learn-source-level",level);pressName(view,"Open level");
        choose(view,"learn-source-sublevel",1);pressName(view,"Open sublevel");
        choose(view,"learn-source-selection-mode",2);choose(view,"learn-source-start",first);choose(view,"learn-source-stop",last);
        const auto group=view.sourceGroupRevision(),selection=view.sourceSelectionRevision();
        auto& preview=control<juce::Button>(view,"learn-source-preview");
        h.wait([&]{return !L::loading(*h.home)&&view.catalogReady()&&preview.isVisible()&&preview.isEnabled();},"exact selected queue Practice publication");
        ck(view.sourceGroupRevision()==group&&view.sourceSelectionRevision()==selection&&
           control<juce::ComboBox>(view,"learn-source-level").getSelectedId()==level&&
           control<juce::ComboBox>(view,"learn-source-sublevel").getSelectedId()==1&&
           control<juce::ComboBox>(view,"learn-source-selection-mode").getSelectedId()==2&&
           control<juce::ComboBox>(view,"learn-source-start").getSelectedId()==first&&
           control<juce::ComboBox>(view,"learn-source-stop").getSelectedId()==last,
           "verified selected publication preserves exact queue source group and endpoint intent");
        pressId(view,"learn-source-preview");
    };
    if(nextFocusOnly){
        h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);h.home->toFront(true);marker();
        ck(h.home->getPeer()!=nullptr&&h.home->isShowing(),"Queue Next focus fixture owns a showing native peer");
        loadRange(12,2,3);pressId(view,"learn-queue-confirm");
        pressId(view,"learn-queue-open");h.wait([&]{return h.home->page()==H::Page::Practice&&!L::pending(*h.home);},"first queued Practice open");
        click(h.practice(),"Audio settings");click(A::settings(*h.home),"Connect audio");h.tick();click(A::settings(*h.home),"Enable audio");h.blocks(1);click(A::settings(*h.home),"Back to Practice");
        click(h.practice(),"Start selected case");h.wait([&]{return h.practice().captureSession()->startTaken();},"first explicit Start");
        h.blocks(6000);h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"first Practice review");
        ck(h.practice().saveSample(),"first original result explicitly saved");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"first result Saved");
        h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"first output cleanup");
        if(P::panel(h.practice()))pressName(h.practice(),"Go back");else click(h.practice(),"Back");
        h.tick();ck(h.home->page()==H::Page::Learn,"saved result returns to owned queue");
        auto& next=control<juce::Button>(view,"learn-queue-next");auto& open=control<juce::Button>(view,"learn-queue-open");
        ck(next.isShowing()&&next.isEnabled(),"Next is visible and enabled after Save and cleanup");
        next.grabKeyboardFocus();ck(juce::Component::getCurrentlyFocusedComponent()==&next,"real native focus is on Next before activation");
        pressId(view,"learn-queue-next");h.wait([&]{return !L::owned(*h.home)&&!L::pending(*h.home);},"first Session close and queue advance");
        ck(h.home->page()==H::Page::Learn&&open.isShowing()&&open.isEnabled(),"next source item is ready with visible Open");
        auto* focused=juce::Component::getCurrentlyFocusedComponent();
        ck(focused&&view.isParentOf(focused)&&focused->isShowing()&&focused->isEnabled()&&focused->getWantsKeyboardFocus(),"async Next completion preserves an eligible Learn keyboard destination");
        auto traversal=view.createKeyboardFocusTraverser();
        auto* openDestination=focused==&open?focused:traversal->getNextComponent(focused);
        ck(openDestination==&open,"normal traversal reaches next-item Open after async close");
        openDestination->grabKeyboardFocus();
        ck(juce::Component::getCurrentlyFocusedComponent()==&open,"next-item Open receives real native focus");
        for(int i=0;i<50;++i)h.tick();ck(juce::Component::getCurrentlyFocusedComponent()==&open,"next-item Open focus survives unchanged timer updates");
        std::cout<<"PASS "<<checks<<" real native-peer Queue Next focus checks; actual keyboard proof remains separate installed GUI\n";return 0;
    }
    if(entryOnly){
        h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);h.home->toFront(true);marker();
        ck(h.home->getPeer()!=nullptr&&h.home->isShowing(),"focus-entry fixture owns a real showing native peer");
        const auto valid=[&]{auto* focused=juce::Component::getCurrentlyFocusedComponent();return focused&&view.isParentOf(focused)&&focused->isShowing()&&focused->isEnabled()&&focused->getWantsKeyboardFocus();};
        click(*h.home,"Learn");ck(valid(),"generic Learn enters final source hierarchy with an eligible native focus");pressName(view,"Back");
        loadRange(12,2,2);auto& confirm=control<juce::Button>(view,"learn-queue-confirm");confirm.grabKeyboardFocus();
        ck(juce::Component::getCurrentlyFocusedComponent()==&confirm,"native Preview confirmation begins with focused Confirm");pressId(view,"learn-queue-confirm");
        ck(valid(),"Preview to Queue preserves a legitimate keyboard entry when Confirm hides");
        auto& open=control<juce::Button>(view,"learn-queue-open");auto& next=control<juce::Button>(view,"learn-queue-next");
        open.grabKeyboardFocus();ck(juce::Component::getCurrentlyFocusedComponent()==&open,"native fixture establishes real JUCE queue focus");
        pressId(view,"learn-queue-open");h.wait([&]{return h.home->page()==H::Page::Practice&&!L::pending(*h.home);},"focus-entry Practice open");
        ck(h.practice().hasKeyboardFocus(true),"Practice owns real keyboard focus before Back");
        const auto before=snapshot("entry-open-before-back");click(h.practice(),"Back");h.tick();
        ck(h.home->page()==H::Page::Learn&&valid(),"Practice Back seeds an eligible visible Learn descendant after hiding Practice");
        ck(juce::Component::getCurrentlyFocusedComponent()==&open,"owned queue default traversal skips disabled Back and tempo");
        for(int i=0;i<50;++i)h.tick();ck(juce::Component::getCurrentlyFocusedComponent()==&open,"return focus survives unchanged real Home timer refreshes");
        ck(snapshot("entry-open-after-back").data.object().at("authoritative")==before.data.object().at("authoritative"),"focus return preserves all14 tables before Start");
        pressId(view,"learn-queue-open");click(h.practice(),"Audio settings");click(A::settings(*h.home),"Connect audio");h.tick();click(A::settings(*h.home),"Enable audio");h.blocks(1);click(A::settings(*h.home),"Back to Practice");
        click(h.practice(),"Start selected case");h.wait([&]{return h.practice().captureSession()->startTaken();},"focus-entry Start");
        h.blocks(6000);h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"focus-entry review");
        ck(h.practice().saveSample(),"focus-entry explicit Save accepts original result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"focus-entry Saved");h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"focus-entry cleanup");
        ck(h.practice().requestProgressPage(),"saved queued result opens actual Progress");h.tick();auto& progress=A::progress(*h.home);progress.grabKeyboardFocus();
        ck(progress.hasKeyboardFocus(true),"Progress owns native focus before its Back");const auto saved=snapshot("entry-saved-before-return");
        click(progress,"Back");h.tick();ck(h.home->page()==H::Page::Learn&&valid(),"Progress Back seeds an eligible visible owned-queue control");
        ck(next.isEnabled()&&next.isShowing(),"saved queue Next is now a legitimate keyboard destination");
        auto traversal=view.createKeyboardFocusTraverser();auto* successor=traversal->getNextComponent(juce::Component::getCurrentlyFocusedComponent());
        ck(successor==&next,"normal queue traversal reaches Next after default Open");successor->grabKeyboardFocus();
        ck(juce::Component::getCurrentlyFocusedComponent()==&next,"native Next receives focus through normal traversal");
        ck(h.home->navigate(H::Page::Learn)&&juce::Component::getCurrentlyFocusedComponent()==&next,"same-page update preserves an existing valid Learn focus");
        for(int i=0;i<50;++i)h.tick();ck(juce::Component::getCurrentlyFocusedComponent()==&next,"saved Next focus survives repeated timer refreshes");
        ck(snapshot("entry-saved-after-return").data.object().at("authoritative")==saved.data.object().at("authoritative"),"focus entry and traversal preserve all14 saved authoritative tables");
        std::cout<<"PASS "<<checks<<" real native-peer Learn focus-entry checks; actual keyboard proof remains separate CUA\n";return 0;
    }
    if(focusOnly){
        struct VisibilityProbe final:juce::ComponentListener {
            explicit VisibilityProbe(juce::Component& c):component(c){component.addComponentListener(this);}
            ~VisibilityProbe()override{component.removeComponentListener(this);}
            void componentVisibilityChanged(juce::Component& c)override{++changes;if(!c.isVisible())++hidden;}
            juce::Component& component;int changes{},hidden{};
        };
        loadRange(12,2,2);pressId(view,"learn-queue-confirm");
        auto& open=control<juce::Button>(view,"learn-queue-open");auto& next=control<juce::Button>(view,"learn-queue-next");
        auto& bpm=control<juce::TextEditor>(view,"learn-source-bpm");auto* panel=open.getParentComponent();
        ck(panel&&panel->isVisible()&&open.isVisible()&&open.isEnabled()&&bpm.isVisible(),"focus probes begin on visible enabled queue controls and panel");
        VisibilityProbe openProbe(open),panelProbe(*panel),bpmProbe(bpm);
        const auto before=snapshot("focus-before");
        for(int i=0;i<50;++i)h.tick();
        ck(openProbe.changes==0&&bpmProbe.changes==0&&panelProbe.changes==0,"unchanged real Home timer must not hide and reshow queue controls");
        for(int i=0;i<20;++i)view.queueStatus("Stable queue message");
        ck(openProbe.changes==0&&bpmProbe.changes==0&&panelProbe.changes==0,"unchanged queueStatus must not hide and reshow its parent panel");
        view.queueStatus("Pending original Session operation",true);
        ck(!open.isEnabled()&&!next.isEnabled()&&!bpm.isEnabled(),"pending operation still updates Open Next and tempo fences");
        view.queueStatus("Original operation resolved",false);
        ck(open.isEnabled()&&!next.isEnabled()&&bpm.isEnabled(),"resolved ready state refresh restores only permitted controls");
        pressName(view,"Back");
        ck(openProbe.hidden==1&&!open.isVisible()&&panelProbe.hidden==0,"real Queue to Exercises transition hides old control once without pulsing parent");
        auto& first=control<juce::ComboBox>(view,"learn-source-start");auto& last=control<juce::ComboBox>(view,"learn-source-stop");
        ck(first.isVisible()&&last.isVisible(),"endpoint probes begin on visible exercise controls");VisibilityProbe firstProbe(first),lastProbe(last);
        choose(view,"learn-source-selection-mode",2);choose(view,"learn-source-start",3);choose(view,"learn-source-stop",4);
        ck(firstProbe.changes==0&&lastProbe.changes==0&&last.isEnabled(),"endpoint selection updates preserve still-visible controls");
        choose(view,"learn-source-selection-mode",1);
        ck(!last.isEnabled()&&last.getSelectedId()==first.getSelectedId()&&firstProbe.changes==0,"single exercise mode changes enabled fence without visibility churn");
        pressId(view,"learn-source-preview");
        ck(firstProbe.hidden==1&&lastProbe.hidden==1,"Exercises to Preview legitimately hides both endpoint controls");
        auto& variant=control<juce::ComboBox>(view,"learn-preview-variant");auto& confirm=control<juce::Button>(view,"learn-queue-confirm");
        ck(variant.isVisible()&&confirm.isVisible()&&confirm.isEnabled(),"preview probes begin on visible admitted variant and Confirm");VisibilityProbe variantProbe(variant),confirmProbe(confirm);
        choose(view,"learn-preview-variant",2);
        ck(variantProbe.changes==0&&confirmProbe.changes==0&&variant.getSelectedId()==2,"variant selection preserves visible variant and Confirm controls");
        ck(snapshot("focus-after").data.object().at("authoritative")==before.data.object().at("authoritative"),"focus visibility and state refreshes preserve all14 authoritative tables");
        std::cout<<"PASS "<<checks<<" causal source visibility checks; actual keyboard proof is separate CUA\n";return 0;
    }
    if(shortcutOnly){
        ck(view.selectLesson("fg:item:000002")&&view.selectVariant("fg:variant:000008"),"choose exact retained non-first variant before Home shortcut");
        const auto selected=navigation::snapshotAdmission(*view.catalog()->admit(view.selectedLesson(),view.selectedVariant()));
        ck(h.home->navigate(H::Page::Home),"return Home with retained exact case");const auto before=snapshot("shortcut-before");
        pressId(*h.home,"home-practice");marker();
        ck(h.home->page()==H::Page::Learn,"Home shortcut dispatch reaches Learn before testing its destination");
        auto& levels=control<juce::ComboBox>(view,"learn-source-level");
        ck(h.home->page()==H::Page::Learn&&!levels.getParentComponent()->isVisible(),"Home Review selected case opens Case rather than source hierarchy");
        ck(view.selectedLesson()==selected.itemId&&view.selectedVariant()==selected.variantId&&navigation::snapshotAdmission(*view.catalog()->admit(view.selectedLesson(),view.selectedVariant()))==selected,"Home Review preserves exact item non-first variant version and source binding");
        pressName(view,"Back");ck(h.home->page()==H::Page::Home,"direct selected case Back returns Home");
        click(*h.home,"Learn");ck(levels.getParentComponent()->isVisible()&&levels.isVisible(),"generic Learn still opens source levels");pressName(view,"Back");
        auto& duplicate=control<juce::Button>(*h.home,"home-start-learning");
        ck(!duplicate.isVisible()&&!duplicate.isEnabled()&&!duplicate.getWantsKeyboardFocus(),"duplicate Start learning stays unavailable after selection");
        click(*h.home,"Learn");
        ck(levels.getParentComponent()->isVisible()&&levels.isVisible()&&view.selectedVariant()==selected.variantId,"stable Learn opens hierarchy without replacing retained case");pressName(view,"Back");
        for(int width:{920,1280}){h.home->setSize(width,680);for(const auto* expected:{"LEARN & PRACTICE","ACTIVITIES","AUDIO & TOOLS"}){bool found=false;for(auto* child:h.home->getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText()==juce::String::fromUTF8(expected))found=true;ck(found,"Home heading is explicitly decoded UTF8 at width "+std::to_string(width));}}
        ck(snapshot("shortcut-after").data.object().at("authoritative")==before.data.object().at("authoritative"),"Home shortcut and hierarchy browsing preserve all14 authoritative tables");
        ck(!h.practice().captureSession()->startTaken()&&h.home->audioSettings().snapshot().state==output::State::Closed,"Home case review neither starts an Attempt nor opens output");
        std::cout<<"PASS "<<checks<<" exact Home shortcut checks\n";return 0;
    }
    counts(snapshot("initial"),0,1);
    enterQueueLearn();
    ck(control<juce::ComboBox>(view,"learn-source-level").getNumItems()==105,quitOnly?"preloaded Learn source hierarchy exposes all105 original source levels":"pinned Home Learn coordinator exposes all 105 original source levels");
    pressName(view,"Back");ck(h.home->page()==H::Page::Home,"source hierarchy Back returns Home without activity");
    loadRange(12,2,2);
    const auto& sub=index->level(12).sublevels.front();std::vector<navigation::AdmissionIdentity> expected;
    for(std::size_t i=0;i<1;++i){
        if(i==0){choose(view,"learn-preview-item",1);choose(view,"learn-preview-variant",1);}
        const auto choices=learn::choices(index->exercises().at(sub.exercises.at(i+1)),*view.catalog());
        ck(choices.size()==2,"each Level12 rung has exactly two admitted variants");expected.push_back(choices.at(i%2));
    }
    counts(snapshot("preview-no-activity"),0,1);pressId(view,"learn-queue-confirm");counts(snapshot("confirmed-no-activity"),0,1);
    const auto sourceDescription=[&]{return control<juce::TextEditor>(view,"learn-source-details").getDescription();};
    const auto checkUnavailableHomeShortcut=[&](const std::string& context){
        auto& shortcut=control<juce::Button>(*h.home,"home-practice");
        ck(!shortcut.isVisible()&&!shortcut.isEnabled()&&static_cast<bool>(shortcut.onClick),
           context+": hidden Home details is disabled without an explicit case; its guarded callback remains installed");
        // This is a direct adversarial callback test, not a user/UI activation.
        // JUCE correctly suppresses triggerClick for this disabled control.
        shortcut.onClick();marker();
    };
    ck(sourceDescription().isEmpty(),"confirmed unopened queue has no active Session accessibility annotation");
    control<juce::TextEditor>(view,"learn-source-bpm").setText("300",false);
    ck(!control<juce::Button>(view,"learn-queue-next").isEnabled(),"Confirm cannot advance or auto-open a queue item");
    std::set<std::string> sessions,owners;std::vector<std::string> originalBytes;
    for(std::size_t item=0;item<((quitOnly||shutdownOnly)?1u:4u);++item){
        if(item>0){view.showSourceHierarchy(true,true);loadRange(12,static_cast<int>(item)+2,static_cast<int>(item)+2);const auto currentChoices=learn::choices(index->exercises().at(sub.exercises.at(item+1)),*view.catalog());ck(currentChoices.size()==2,"current single exercise retains two exact admitted variants");expected.push_back(currentChoices.at(item%2));choose(view,"learn-preview-variant",static_cast<int>(item%2+1));pressId(view,"learn-queue-confirm");control<juce::TextEditor>(view,"learn-source-bpm").setText("300",false);}
        if(item==0){h.mode=4;h.entered=false;h.release=false;}
        pressId(view,"learn-queue-open");
        if(item==0){
            h.wait([&]{return h.entered.load();},"pending create barrier");const auto retained=L::retained(*h.home);std::string reason;
            ck(L::pending(*h.home)&&L::owned(*h.home)&&!L::retry(*h.home,reason),"pending create retains sole original future; retry cannot duplicate it");
            ck(!h.home->detachForStoreReopen()&&!h.home->navigate(H::Page::Guided),"pending create blocks profile detach and another activity");
            ck(L::retained(*h.home)==retained&&!h.practice().captureSession()->startTaken(),"pending navigation preserves operation/time/payload without Attempt");
            view.showSourceHierarchy(false,true);
            ck(!control<juce::ComboBox>(view,"learn-source-level").isVisible()&&control<juce::Button>(view,"learn-queue-open").isVisible()&&L::pending(*h.home)&&L::owned(*h.home)&&L::retained(*h.home)==retained,"explicit Browse levels request during pending create stays at the original owned queue");
            const auto retainedItem=view.selectedLesson(),retainedVariant=view.selectedVariant();const auto retainedPosition=L::position(*h.home);
            checkUnavailableHomeShortcut("Pending queue create");
            ck(L::pending(*h.home)&&L::owned(*h.home)&&L::position(*h.home)==retainedPosition&&L::retained(*h.home)==retained&&view.selectedLesson()==retainedItem&&view.selectedVariant()==retainedVariant,"queued Home shortcut preserves pending original operation owner position and selection");
            h.release=true;
        }
        h.wait([&]{return h.home->page()==H::Page::Practice&&!L::pending(*h.home);},"explicit queued Practice open");
        const auto session=h.practice().captureSessionId();const auto admission=h.practice().lessonAdmission();
        const auto expectedDescription=juce::String::fromUTF8(("Session "+session+"; source "+index->exercises().at(sub.exercises.at(item+1)).source.sourceExerciseKey).c_str());
        ck(sourceDescription()==expectedDescription,"each fresh queue launch exposes its exact current Session and source annotation");
        ck(session!=h.sessionId&&sessions.insert(session).second,"each explicit queue Open creates a distinct Session");
        ck(admission&&navigation::snapshotAdmission(*admission)==expected[item],"Practice retains exact per-item variant and source binding");
        ck(h.practice().captureSession()->phase()==capture::SessionPhase::Idle,"Open prepares Practice without starting an Attempt");counts(snapshot("opened-"+std::to_string(item)),item,item+2);
        if(shutdownOnly){
            snapshot("prepared-before-quit");
            h.mode=4;h.entered=false;h.release=false;
            const auto before=std::chrono::steady_clock::now();
            ck(!h.home->requestClose()&&h.home->closeState()==H::CloseState::Waiting&&
                std::chrono::steady_clock::now()-before<std::chrono::milliseconds(100),
               "Quit submits the original unused Session close without blocking");
            h.wait([&]{return h.entered.load();},"pending original quit close barrier");
            const auto retained=L::retained(*h.home);
            ck(L::pending(*h.home)&&L::owned(*h.home)&&!h.practice().captureSession()->startTaken(),
               "prepared Quit retains one close future and creates no Attempt");
            ck(!h.home->requestClose()&&h.home->closeState()==H::CloseState::Waiting&&L::retained(*h.home)==retained,
               "repeated Quit keeps the exact original close operation/time/owner/payload");
            h.release=true;h.wait([&]{return !L::pending(*h.home)&&!L::owned(*h.home);},"original quit close confirmed");
            ck(h.home->requestClose()&&h.home->closeState()==H::CloseState::Ready,
               "prepared Quit becomes ready after original close and ownership restoration");
            const auto after=snapshot("prepared-after-quit");
            const auto& authority=after.data.object().at("authoritative").object();
            const auto& rows=authority.at("session").array();bool closed=false;
            for(const auto& row:authority.at("session_close").array())if(row.array()[0].string()==session)
                closed=row.array()[1].isString()&&!row.array()[1].string().empty()&&row.array()[2].string()=="cancelled";
            ck(closed,"the actual unused Session is durably closed as cancelled");
            ck(authority.at("identity").array().empty()&&authority.at("finalized").array().empty()&&rows.size()==2,
               "prepared Quit makes no Attempt, result, or replacement Session");
            ck(h.practice().captureSessionId()==h.sessionId&&h.home->audioSettings().snapshot().state==output::State::Closed,
               "prepared Quit restores original capture owner and leaves real devices closed");
            ck(h.home->getPeer()==nullptr&&nativeOpens==0&&connections==0,
               "prepared close test creates no native peer or physical/software device connection");
            capture_fixture::write(out/"summary.json",storage::canonical(json::Value::Object{
                {"schema","fathom.shutdown-prepared.1"},{"status","PASS"},{"checks",json::Value::fromInteger(checks)},
                {"native_gui",false},{"physical_listening",false},{"acceptance_increment",json::Value::fromInteger(0)}}));
            std::cout<<"PASS "<<checks<<" prepared Session Quit checks; no foreground/audio\n";return 0;
        }
        click(h.practice(),"Audio settings");h.tick();if(h.home->audioSettings().snapshot().state==output::State::Closed){click(A::settings(*h.home),"Connect audio");h.tick();click(A::settings(*h.home),"Enable audio");h.blocks(1);}click(A::settings(*h.home),"Back to Practice");h.tick();
        click(h.practice(),"Start selected case");h.wait([&]{return h.practice().captureSession()->startTaken();},"explicit queued Start");h.blocks(2);
        const auto owner=h.practice().captureSession()->binding().owner;ck(!owner.empty()&&owners.insert(owner).second,"each explicit Start creates a distinct Attempt owner");
        const auto context=h.practice().captureSession()->binding().context;
        ck(context.object().at("session_id").string()==session,"Attempt belongs to its exact queue Session");
        for(const auto* key:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs"})ck(context.object().at(key)==admission->identity().object().at(key),std::string("Attempt retains exact ")+key);
        if(quitOnly||item==2){
            std::shared_ptr<std::atomic<bool>> sourceRelease;
            if(quitOnly){
                auto& browser=L::browser(*h.home);
                ck(browser.ensureTheoryContext(resources/"source-library"),"Quit overlap uses verified existing source context");
                const auto entered=std::make_shared<std::atomic<bool>>(false);sourceRelease=std::make_shared<std::atomic<bool>>(false);
                browser.prepareActivity(desktop::SourceBrowseTestAccess::firstIdentity(browser,1),[entered,sourceRelease](const desktop::SourceLibraryView::LoadTicket&){
                    const desktop::SourceTaskLibraries::ActiveLoad active;
                    *entered=true;const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(3);
                    while(!sourceRelease->load()&&std::chrono::steady_clock::now()<end)std::this_thread::sleep_for(std::chrono::milliseconds(1));
                    return []{};
                },[]{return false;});
                h.wait([&]{return entered->load();},"active capture and source worker overlap");
                ck(desktop::SourceLibraryView::hasBackgroundWork(),"Quit regression overlaps real Active capture with queued/running source work");
            }
            ck(h.practice().canPerformCommand(desktop::PracticeCommand::Stop),"Quit regression begins during a stoppable Active queued Attempt");
            ck(!h.home->requestClose()&&h.home->closeState()==H::CloseState::Held,"normal Quit holds destruction of the owned unsaved queue and capture");
            ck(h.home->page()==H::Page::Practice&&P::panel(h.practice())&&P::stopStamp(h.practice())!=0,"normal Quit requests Stop and retains visible Practice review instead of hiding running audio");
            ck(L::owned(*h.home)&&h.practice().captureSession()->binding().owner==owner&&h.practice().captureSessionId()==session,"Quit preserves the original Attempt and original queue Session");
            if(sourceRelease){*sourceRelease=true;h.wait([]{return !desktop::SourceLibraryView::hasBackgroundWork();},"Quit overlap worker release");}
        }
        float peak=0;for(int block=0;block<2300&&h.practice().captureSession()->phase()!=capture::SessionPhase::Review;++block){peak=std::max(peak,platform::OutputTestAccess::block(A::output(*h.home)));h.tick();}
        h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"queued review");
        if(!quitOnly&&item!=2)ck(peak>0,"actual software callback produces selected reference PCM");
        std::string reason;ck(!L::next(*h.home,reason)&&h.practice().captureSession()->binding().owner==owner,"Stopped unsaved result cannot advance or discard its original Attempt");
        ck(h.practice().saveSample(),"explicit Save accepts the original queued Attempt");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"saved queued result");h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"queued output cleanup");
        const auto original=h.practice().captureSession()->original();ck(original&&!original->assessment,"Save keeps unassessed result without inferred Clean");originalBytes.push_back(original->bytes);
        capture_fixture::write(out/("original-"+std::to_string(item)+".json"),original->bytes);
        if(item==0&&!quitOnly){ck(h.practice().requestProgressPage(),"Saved queue item opens Progress");h.tick();ck(h.home->page()==H::Page::Progress,"Progress is visible");click(A::progress(*h.home),"Back");h.tick();ck(h.home->page()==H::Page::Learn,"Progress Back returns to owned queue");}
        else {if(item==1){ck(h.practice().performCommand(desktop::PracticeCommand::Again),"user Again returns Saved item to Idle");ck(h.practice().captureSession()->original()->bytes==originalBytes.back(),"Again retains the saved original");}if(P::panel(h.practice()))pressName(h.practice(),"Go back");else click(h.practice(),"Back");h.wait([&]{return h.home->page()==H::Page::Learn;},"return to the current owned queue");ck(!P::panel(h.practice()),"actual Back resolves its return panel before queue Session cleanup");}
        view.refreshQueueControls();ck(control<juce::Button>(view,"learn-queue-next").isEnabled()&&control<juce::Button>(view,"learn-queue-next").getButtonText()=="Next after Save and cleanup","Saved and Saved-then-Again keep saved disposition for Next");
        if(singletonSaveQuit){
            const auto before=snapshot("saved-before-home");const auto original=h.practice().captureSession()->original()->bytes;
            const auto revision=L::boardRevision(*h.home);choose(h.practice(),"practice-board-mode",3);
            ck(L::setupDirty(*h.home)&&L::boardDeferred(*h.home)&&!L::boardPending(*h.home),"board choice deferred while singleton child remains owned");
            std::string reason;ck(h.home->requestHome(reason)&&h.home->page()==H::Page::Home&&L::owned(*h.home),"stopped Home detour preserves original singleton Learn owner");
            ck(!h.home->presentationStoppedAndResolved(),"retained child blocks normal preference save gate");
            h.wait([&]{return h.home->requestExit(false);},"SaveQuit closes original child then confirms one setup CAS");
            const auto after=snapshot("savequit-resolved");const auto& aa=after.data.object().at("authoritative").object();const auto& bb=before.data.object().at("authoritative").object();
            ck(!L::owned(*h.home)&&!L::pending(*h.home)&&!L::setupDirty(*h.home),"original queue and setup operation resolved");
            ck(L::boardRevision(*h.home)==revision.value_or(0)+1,"explicit deferred board choice commits once");
            ck(aa.at("identity")==bb.at("identity")&&aa.at("finalized")==bb.at("finalized")&&aa.at("session")==bb.at("session"),"SaveQuit creates no new Attempt/Session and preserves original finalized bytes");
            ck(aa.at("session_close").array().size()==1&&aa.at("session_close").array()[0].array()[0].string()==session&&aa.at("session_close").array()[0].array()[2].string()=="partial","exact singleton child closes as partial activity not source completion");
            for(const auto& [name,rows]:bb)if(name!="session_close"&&name!="preferences")ck(aa.at(name)==rows,"SaveQuit preserves each unrelated authoritative table exactly");
            ck(aa.at("pending").array().empty()&&aa.at("checkpoint").array().empty()&&aa.at("suite_fact").array().empty()&&aa.at("source_attestation").array().empty(),"no capture debt suite or source-credit fabrication");
            ck(h.home->requestExit(false),"repeated resolved SaveQuit succeeds");ck(snapshot("savequit-repeat").data.object().at("authoritative")==after.data.object().at("authoritative"),"repeated SaveQuit all14 stable");
            ck(nativeOpens==0&&!h.home->getPeer(),"software device only no native peer");
            (void)original;std::cout<<"PASS "<<checks<<" singleton dirty board SaveQuit ordering checks\n";return 0;
        }
        pressId(view,"learn-queue-next");
        if(item==1&&!quitOnly){
            const auto retained=L::retained(*h.home);const auto position=L::position(*h.home);const auto real=L::takeReply(*h.home);
            for(int fault=0;fault<3;++fault){auto bad=real;if(fault==0)bad.operation.clear();if(fault==1)bad.operation="foreign-operation";if(fault==2)bad.data.object()["session_id"]=h.sessionId;
                L::deliver(*h.home,std::move(bad));ck(L::retained(*h.home)==retained&&L::position(*h.home)==position&&L::owned(*h.home),"empty/foreign operation or foreign Session receipt cannot advance original close");
                ck(sourceDescription()==expectedDescription,"unresolved mismatched close retains the original active Session accessibility annotation");
                view.showSourceHierarchy(false,true);
                ck(!control<juce::ComboBox>(view,"learn-source-level").isVisible()&&control<juce::Button>(view,"learn-queue-open").isVisible()&&L::owned(*h.home)&&L::retained(*h.home)==retained&&L::position(*h.home)==position,"explicit Browse levels request during unresolved close keeps the original queue owner and operation");
                ck(h.home->navigate(H::Page::Practice)&&!h.practice().startSample()&&!h.practice().performCommand(desktop::PracticeCommand::Again),"retained close keeps cleanup reachable while new Start and user Again are refused");
                ck(h.home->navigate(H::Page::Learn),"retained close returns to its retry screen");
                const auto retainedItem=view.selectedLesson(),retainedVariant=view.selectedVariant();checkUnavailableHomeShortcut("Unresolved queue close");
                ck(L::retained(*h.home)==retained&&L::position(*h.home)==position&&L::owned(*h.home)&&view.selectedLesson()==retainedItem&&view.selectedVariant()==retainedVariant,"Home shortcut cannot replace a retained failed-close queue or selected source");
            }
            ck(L::retry(*h.home,reason)&&L::retained(*h.home)==retained,"retry submits exact original close operation/time/Session/outcome/payload");
        }
        h.wait([&]{return !L::owned(*h.home)&&!L::pending(*h.home);},"explicit Next closes original Session");
        ck(sourceDescription().isEmpty(),"confirmed close and explicit Next clear the retired Session annotation before another Open");
        ck(h.practice().captureSessionId()==h.sessionId&&h.practice().captureSession()->phase()==capture::SessionPhase::Idle,"Next restores preview owner without starting next Attempt");counts(snapshot("next-"+std::to_string(item)),item+1,item+2);
    }
    if(quitOnly){
        if(shutdownActiveOnly){
            const auto last=snapshot("shutdown-active-end");const auto& authority=last.data.object().at("authoritative").object();
            ck(h.home->getPeer()==nullptr&&nativeOpens==0&&connections>0,
               "active close test uses software output with no native peer or forbidden physical open");
            ck(authority.at("session_close").array().size()==1&&authority.at("session_close").array()[0].array()[2].string()=="partial"&&
               authority.at("finalized").array().size()==1&&authority.at("finalized").array()[0].array()[0].string()==*owners.begin()&&
               authority.at("source_attestation").array().empty(),
               "active Quit preserves one exact original saved Attempt and partial Session close without source credit");
        }
        capture_fixture::write(out/"summary.json",storage::canonical(json::Value::Object{
            {"status","PASS"},{"checks",json::Value::fromInteger(checks)},
            {"mode",shutdownActiveOnly?"--shutdown-active-regression":"--quit-regression"},
            {"native_gui",!shutdownActiveOnly},{"physical_audio",false},{"acceptance_increment",json::Value::fromInteger(0)}}));
        std::cout<<"PASS "<<checks<<" active queued Quit checks; software device only\n";return 0;
    }
    const auto completed=snapshot("four-complete");const auto& rows=completed.data.object().at("authoritative").object().at("session").array();std::size_t exactPlans=0;
    for(const auto& row:rows)if(sessions.count(row.array()[0].string())){const auto plan=json::parse(decodeBlob(row.array()[4]));ck(plan.object().at("version").string()=="learn-exercise-session.1"&&!plan.object().at("source_task_completion").boolean(),"queue Session stores exact index source plan without completion claim");++exactPlans;}
    std::size_t partialCloses=0;for(const auto& close:completed.data.object().at("authoritative").object().at("session_close").array())if(sessions.count(close.array()[0].string())){ck(close.array()[2].string()=="partial","saved queue Session closes as recorded partial activity");++partialCloses;}
    ck(partialCloses==4&&exactPlans==4&&owners.size()==4&&sessions.size()==4,"four separately selected single exercises retain distinct manual-flow Sessions and Attempts");
    pressName(view,"Back");pressName(view,"Back");pressName(view,"Back");pressName(view,"Back");ck(h.home->page()==H::Page::Home,"completed hierarchy unwinds to Home");
    ck(sourceDescription().isEmpty(),"completed queue annotation remains absent through source hierarchy navigation");
    loadRange(12,2,2);pressId(view,"learn-queue-confirm");pressId(view,"learn-queue-open");h.wait([&]{return h.home->page()==H::Page::Practice;},"unused preparation");const auto unused=h.practice().captureSessionId();
    ck(sourceDescription()==juce::String::fromUTF8(("Session "+unused+"; source "+index->exercises().at(sub.exercises.at(1)).source.sourceExerciseKey).c_str()),"new unused preparation exposes its own Session rather than a retired launch annotation");
    ck(h.home->navigate(H::Page::Learn),"unused preparation returns to queue");view.refreshQueueControls();ck(control<juce::Button>(view,"learn-queue-next").getButtonText()=="Cancel unused preparation & Next","never-started preparation exposes explicit cancellation");pressId(view,"learn-queue-next");h.wait([&]{return !L::owned(*h.home);},"unused cancellation");const auto final=snapshot("final");counts(final,4,6);
    bool cancelled=false;for(const auto& row:final.data.object().at("authoritative").object().at("session_close").array())if(row.array()[0].string()==unused)cancelled=row.array()[2].string()=="cancelled";ck(cancelled,"unused Session cancelled without an Attempt");
    ck(sourceDescription().isEmpty(),"confirmed unused-preparation cancellation clears the retired Session annotation without an Attempt");
    const auto adapted=progression::adaptSnapshot(final);ck(adapted.records.size()==4,"history contains exactly the four explicit saved Attempts");for(const auto& r:adapted.records)ck(!r.complete&&r.condition.null()&&r.assessment.null(),"history infers no completion, comparable condition or assessment");
    ck(view.selectLesson(expected.front().itemId),"direct admitted case in the prepared source scope remains selectable");const auto direct=view.selectedVariant();
    const auto invalid=out/"invalid-index";std::filesystem::create_directory(invalid);ck(!view.loadSourceIndex(invalid)&&view.selectedVariant()==direct,"missing index refuses hierarchy without replacing direct selected case");
    for(int pass=0;pass<2;++pass){ck(h.home->detachForStoreReopen(),"resolved queue permits safe Store detach");h.store.reset();storage::StoreOptions options;options.path=h.dir/"profile.sqlite";options.preferenceValidator=metronome::preferenceValidator;h.store=std::make_unique<storage::ProfileStore>(options);const auto reopened=snapshot("reopen-"+std::to_string(pass));ck(reopened.data.object().at("authoritative")==final.data.object().at("authoritative"),"read-only Store restart preserves every authoritative table byte-for-byte");ck(h.home->configureCapture(*h.store,h.sessionId,"America/New_York")&&!h.practice().captureSession()->startTaken()&&!L::owned(*h.home),"restart reattaches original preview Session without queue or auto-Start");h.wait([&]{return !L::pending(*h.home)&&A::metronome(*h.home).preferencesReady()&&!A::progress(*h.home).busy()&&!A::guided(*h.home).busy();},"read-only reattach preferences and suite discovery ready");}
    ck(nativeOpens==0,"no physical audio device was opened by the software test");
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"actual_home\":true,\"actual_store\":true,\"software_device\":true,\"installed_gui\":false,\"physical_listening\":false,\"attempts\":4,\"credit\":false}\n";
    std::cout<<"PASS "<<checks<<" Learn real Home/Store navigation checks; software device only\n";return 0;
}catch(const std::exception& error){std::cerr<<"FAIL after "<<checks<<": "<<error.what()<<'\n';return 1;}}
