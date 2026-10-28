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
// InstalledCatalogFixtureAccess is unused by this narrow fixture.

// Observe coordinator ownership and perturb returned receipts, never storage rows or capture facts.
namespace fathom::desktop {
struct GuidedSessionViewTestAccess {
    static bool hasNoPlan(const GuidedSessionView& view){return view.planValue_.null();}
};
struct LearnNavigationTestAccess {
    static std::string suite(const HomeView& h){return h.learnSuite_?h.learnSuite_->suiteId():"";}
    static bool clearSuitePending(const HomeView& h){return h.learnMutation_==HomeView::LearnMutation::ClearSuite&&h.learnFuture_.has_value();}
    static bool clearing(const HomeView& h){return h.clearQueueRequested_;}

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
    static bool settled(const HomeView& h){return !h.learnFuture_&&h.learnMutation_==HomeView::LearnMutation::None;}
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

int main(int argc,char**argv){int checks=0;try{
 if(argc!=3)throw std::runtime_error("fresh output and exact resources required");
 const std::filesystem::path out=argv[1],resources=argv[2];if(std::filesystem::exists(out))throw std::runtime_error("fresh root required");std::filesystem::create_directory(out);
 juce::ScopedJuceInitialiser_GUI gui;Harness h(out,"profile");auto& view=A::lessons(*h.home);
 auto ck=[&](bool x,const char* msg){if(!x)throw std::runtime_error(msg);++checks;std::cout<<"PASS "<<msg<<std::endl;};
 auto snapshot=[&]{return capture_fixture::confirmed(h.store->snapshot(storage::newUuid())).data.object().at("authoritative");};
 auto button=[&](const char* id)->juce::Button&{return control<juce::Button>(*h.home,id);};
 auto raster=[&](const char* file){auto image=h.home->createComponentSnapshot(h.home->getLocalBounds());juce::FileOutputStream stream(juce::File((out/file).string()));juce::PNGImageFormat png;ck(stream.openedOk()&&png.writeImageToStream(image,stream),"Component raster saved");};
 const std::vector<std::filesystem::path> extensions{resources/lesson::Catalog::installedExtensionDirectoryNames().at(0),resources/lesson::Catalog::installedExtensionDirectoryNames().at(1)};
 ck(view.load(resources/"representative-controls",extensions)&&view.loadSourceIndex(resources/"learn-source-index"),"Exact installed catalog and source index");L::indexLoaded(*h.home);
 auto prepare=[&](bool multi){h.home->navigate(H::Page::Learn);view.showSourceHierarchy();choose(view,"learn-source-level",12);pressName(view,"Open level");choose(view,"learn-source-sublevel",1);pressName(view,"Open sublevel");choose(view,"learn-source-selection-mode",multi?2:1);choose(view,"learn-source-start",2);if(multi)choose(view,"learn-source-stop",3);h.wait([&]{return !L::loading(*h.home)&&view.catalogReady()&&control<juce::Button>(view,"learn-source-preview").isEnabled();},"selected publication");pressId(view,"learn-source-preview");pressId(view,"learn-queue-confirm");pressId(view,"learn-queue-open");};
 prepare(true);const auto pendingOriginal=L::retained(*h.home);pressId(view,"learn-queue-clear");ck(!button("queue-clear-confirm").isEnabled(),"Pending original write blocks clear");pressId(*h.home,"queue-clear-cancel");ck(L::retained(*h.home)==pendingOriginal,"Cancel pending clear retains exact original request");h.wait([&]{return h.home->page()==H::Page::Practice&&L::settled(*h.home);},"real suite exercise preparation");const auto sid=L::suite(*h.home);ck(!sid.empty(),"Real durable multi-exercise queue created");
 const auto originalSession=h.practice().captureSessionId();const auto before=snapshot();std::string reason;
 ck(h.home->requestHome(reason),"Leave early to Home");ck(L::homeDetour(*h.home),"Home offers retained Resume");raster("home.png");L::resumeHomeDetour(*h.home);ck(h.home->page()==H::Page::Learn&&h.practice().captureSessionId()==originalSession&&snapshot()==before,"Resume preserves queue Session and all stored facts");
 pressId(view,"learn-queue-clear");ck(button("queue-clear-confirm").isEnabled(),"Unused preparation can be intentionally cleared");raster("confirm.png");const auto heldRequest=L::retained(*h.home);std::string blockedReason;ck(!view.onQueueNext(blockedReason),"Underlying stale Next cannot mutate confirmation");control<juce::Button>(view,"learn-queue-confirm").onClick();ck(L::retained(*h.home)==heldRequest,"Underlying stale confirm cannot replace queue");pressId(*h.home,"queue-clear-cancel");ck(L::owned(*h.home)&&snapshot()==before,"Cancel preserves exact queue and all tables");
 pressId(view,"learn-queue-clear");pressId(*h.home,"queue-clear-confirm");button("queue-clear-confirm").onClick();ck(L::clearing(*h.home),"Repeated confirm retains one original reset");h.wait([&]{return L::clearSuitePending(*h.home);},"original queue closure submission");
 auto realReply=L::takeReply(*h.home);const auto retainedReset=L::retained(*h.home);auto wrongReply=realReply;wrongReply.owner=storage::newUuid();L::deliver(*h.home,std::move(wrongReply));h.tick();ck(L::clearing(*h.home)&&!button("queue-clear-cancel").isEnabled()&&button("queue-clear-retry").isEnabled(),"Wrong owner receipt retains original and exposes visible safe Retry");
 ck(L::retained(*h.home)==retainedReset,"Uncertain reset retains operation timestamp and payload");pressId(*h.home,"queue-clear-retry");h.wait([&]{return !L::clearing(*h.home)&&L::settled(*h.home);},"same-original visible retry");ck(h.home->page()==H::Page::Learn&&!L::owned(*h.home)&&!L::sourceQueue(view)&&!L::homeDetour(*h.home),"Confirmed clear returns fresh selection without stale Resume");raster("fresh.png");
 auto closed=capture_fixture::confirmed(h.store->readSuite(storage::newUuid(),sid));ck(closed.data.object().at("closed")==json::Value(true)&&closed.data.object().at("review").object().at("score").null(),"Suite durably closed without invented assessment");
 ck(h.store->readSuite(storage::newUuid()).get().status==storage::Status::DefinitelyAbsent,"Cleared suite is absent from restart discovery");auto after=snapshot();for(const auto* key:{"identity","pending","checkpoint","finalized","source_attestation","rule_observation"})ck(after.object().at(key)==before.object().at(key),"Existing capture/history authority retained");
 ck(h.home->requestHome(reason)&&!L::homeDetour(*h.home),"Home after clear has no Resume detour");
 ck(h.home->detachForStoreReopen(),"Cleared queue safely detaches Store");h.store.reset();storage::StoreOptions opt;opt.path=h.dir/"profile.sqlite";opt.preferenceValidator=desktop::presentation::composedPreferenceValidator;h.store=std::make_unique<storage::ProfileStore>(opt);ck(snapshot()==after,"Close/reopen preserves exact reset facts");ck(h.home->configureCapture(*h.store,h.sessionId,"America/New_York"),"Reattach same original profile");h.wait([&]{return L::settled(*h.home)&&A::startupReadSettled(*h.home);},"restart discovery");ck(!L::owned(*h.home)&&L::suite(*h.home).empty(),"Reopen does not resurrect cleared queue");

 prepare(false);h.wait([&]{return h.home->page()==H::Page::Practice&&L::settled(*h.home);},"second singleton preparation");
 click(h.practice(),"Audio settings");h.tick();click(A::settings(*h.home),"Connect audio");h.wait([&]{return h.home->audioSettings().snapshot().state==output::State::Observed;},"output observation");click(A::settings(*h.home),"Enable audio");h.blocks(1);h.wait([&]{h.blocks(1);return h.home->audioSettings().snapshot().state==output::State::Ready;},"software ready");click(A::settings(*h.home),"Back to Practice");h.tick();
 ck(h.practice().startSample(),"Explicit software Start for unsaved-result protection");h.wait([&]{return h.practice().captureSession()->startTaken();},"Attempt Start");h.blocks(2);ck(h.practice().stopSample(),"Stop does not discard original");
 h.wait([&]{h.blocks(1);return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"original review");
 ck(!h.home->requestHome(reason),"Unsaved active result cannot escape to Home");
 // Invoke the actual queue reset callback as a stale-event probe while Practice owns unsaved work.
 view.onClearQueue();ck(!control<juce::Component>(*h.home,"clear-learn-queue-confirmation").isVisible(),"Stale reset from active Practice cannot change ownership");
 ck(h.home->navigate(H::Page::Learn),"Queue surface can retain unresolved original");pressId(view,"learn-queue-clear");ck(!button("queue-clear-confirm").isEnabled(),"Unsaved review explicitly blocks reset confirmation");raster("unsaved-held.png");const auto unsavedOwner=h.practice().captureSession()->binding().owner;pressId(*h.home,"queue-clear-return");ck(h.home->page()==H::Page::Practice&&h.practice().captureSession()->binding().owner==unsavedOwner,"Return preserves exact unsaved original");
 ck(h.practice().saveSample(),"Existing Save commits original result explicitly");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"saved original");h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"saved cleanup");
 const auto saved=snapshot();ck(saved.object().at("finalized").array().size()==1,"One real saved result exists before reset");
 ck(h.home->requestHome(reason),"Saved stopped result can return Home");L::resumeHomeDetour(*h.home);pressId(view,"learn-queue-clear");pressId(*h.home,"queue-clear-confirm");h.wait([&]{return !L::clearing(*h.home)&&L::settled(*h.home);},"saved singleton reset");
 const auto resetSaved=snapshot();for(const auto* key:{"identity","pending","checkpoint","finalized","source_attestation","rule_observation"})ck(saved.object().at(key)==resetSaved.object().at(key),"Saved history preserved after clear");
 ck(!L::sourceQueue(view)&&L::suite(*h.home).empty(),"Singleton reset also returns fresh selection");

 prepare(true);h.wait([&]{return h.home->page()==H::Page::Practice&&L::settled(*h.home);},"partial suite preparation");const auto partialSuite=L::suite(*h.home);
 ck(h.home->requestHome(reason),"Pause automatic continuation with real Home detour");L::resumeHomeDetour(*h.home);pressId(view,"learn-queue-open");h.wait([&]{return h.home->page()==H::Page::Practice;},"return current Practice");
 click(h.practice(),"Audio settings");h.tick();click(A::settings(*h.home),"Connect audio");h.wait([&]{return h.home->audioSettings().snapshot().state==output::State::Observed;},"partial suite output observation");click(A::settings(*h.home),"Enable audio");h.blocks(1);click(A::settings(*h.home),"Back to Practice");h.tick();
 ck(h.practice().startSample(),"Explicit Start for completed-member preservation");for(int i=0;i<2300&&h.practice().captureSession()->phase()!=capture::SessionPhase::Saved;++i)h.blocks(1);h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"natural suite saved");h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"natural cleanup");
 ck(h.practice().suiteNaturalCompleted(),"Actual naturally completed saved member retained");const auto natural=snapshot();ck(h.home->requestHome(reason),"Partial completed queue returns Home");L::resumeHomeDetour(*h.home);pressId(view,"learn-queue-clear");pressId(*h.home,"queue-clear-confirm");h.wait([&]{return !L::clearing(*h.home)&&L::settled(*h.home);},"partial suite closure");
 auto partial=capture_fixture::confirmed(h.store->readSuite(storage::newUuid(),partialSuite));ck(partial.data.object().at("closed")==json::Value(true)&&partial.data.object().at("members").array().size()==1&&partial.data.object().at("review").object().at("score").null(),"Clear retains completed suite member with no new score");ck(snapshot().object().at("finalized")==natural.object().at("finalized"),"Completed results remain byte-exact after clear");

 const auto durable=snapshot();h.home.reset();h.store.reset();h.store=std::make_unique<storage::ProfileStore>(opt);h.home=std::make_unique<H>();h.home->setVisible(true);h.home->setSize(920,680);A::halt(*h.home);ck(h.home->configureCapture(*h.store,h.sessionId,"America/New_York"),"Fresh Home instance reopens original profile");h.wait([&]{return L::settled(*h.home)&&A::startupReadSettled(*h.home);},"fresh-instance discovery");ck(L::suite(*h.home).empty()&&!L::owned(*h.home)&&snapshot()==durable,"New app instance retains history without resurrecting either cleared suite");
 ck(nativeOpens==0&&!h.home->getPeer(),"No native peer, device or sound");std::cout<<"PASS queue clear checks="<<checks<<std::endl;return 0;
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<std::endl;return 1;}}
