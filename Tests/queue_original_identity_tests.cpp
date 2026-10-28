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

int main(int argc,char**argv){try{
 if(argc!=3)throw std::runtime_error("fresh output and exact resources required");
 const std::filesystem::path out=argv[1],resources=argv[2];
 if(out.parent_path()!=std::filesystem::path("/private/tmp")||std::filesystem::exists(out))throw std::runtime_error("fresh private root only");
 std::filesystem::create_directory(out);std::filesystem::permissions(out,std::filesystem::perms::owner_all);
 juce::ScopedJuceInitialiser_GUI gui;Harness h(out,"profile");auto& view=A::lessons(*h.home);
 h.wait([&]{return !L::pending(*h.home);},"original initial discovery");
 const std::vector<std::filesystem::path> extensions{resources/lesson::Catalog::installedExtensionDirectoryNames().front()};
 if(!view.load(resources/"representative-controls",extensions)||!view.loadSourceIndex(resources/"learn-source-index"))throw std::runtime_error("exact catalog/index refused");L::indexLoaded(*h.home);
 h.home->navigate(H::Page::Learn);view.showSourceHierarchy();
 choose(view,"learn-source-level",12);pressName(view,"Open level");choose(view,"learn-source-sublevel",1);pressName(view,"Open sublevel");
 choose(view,"learn-source-selection-mode",1);choose(view,"learn-source-start",2);
 h.wait([&]{return !L::loading(*h.home)&&view.catalogReady()&&control<juce::Button>(view,"learn-source-preview").isEnabled();},"selected queue publication");
 const auto baseline=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));capture_fixture::write(out/"baseline.json",storage::canonical(baseline.data));
 pressId(view,"learn-source-preview");pressId(view,"learn-queue-confirm");pressId(view,"learn-queue-open");
 const auto retained=L::retained(*h.home);auto actual=L::takeReply(*h.home);const auto actualOperation=actual.operation;const auto request=json::parse(retained);const auto created=actual.data.object().at("session_id").string();storage::validateUuid(created);
 if(actual.status!=storage::Status::Confirmed||actual.operation!=request.object().at("operation").string()||actual.owner!=created)throw std::runtime_error("real confirmed original receipt mismatch");
 capture_fixture::write(out/"real-receipt.json",storage::canonical(json::Value::Object{{"status",storage::statusName(actual.status)},{"operation",actual.operation},{"owner",actual.owner},{"data",actual.data}}));auto wrongOwner=actual;wrongOwner.owner=storage::newUuid();L::deliver(*h.home,std::move(wrongOwner));if(h.home->page()!=H::Page::Learn||L::retained(*h.home)!=retained||L::pending(*h.home))throw std::runtime_error("Wrong owner receipt admitted or original changed");auto wrongSession=actual;wrongSession.data.object()["session_id"]=storage::newUuid();L::deliver(*h.home,std::move(wrongSession));if(h.home->page()!=H::Page::Learn||L::retained(*h.home)!=retained||L::pending(*h.home))throw std::runtime_error("Wrong Session receipt admitted or original changed");auto bad=actual;bad.operation="";L::deliver(*h.home,std::move(bad));
 if(L::retained(*h.home)!=retained||L::pending(*h.home)||!L::owned(*h.home))throw std::runtime_error("original operation lost");
 capture_fixture::write(out/"original.json",storage::canonical(json::Value::Object{{"retained",retained},{"actual_operation",actualOperation},{"actual_owner",actual.owner},{"synthetic_returned_receipt_corruption",true},{"physical_audio",false}}));
 if(h.home->getPeer()||h.practice().getPeer())throw std::runtime_error("Unexpected native peer");h.home->setSize(920,680);h.home->resized();
 auto raster=[&](const char* name){auto image=h.home->createComponentSnapshot(h.home->getLocalBounds());juce::FileOutputStream stream(juce::File((out/name).string()));juce::PNGImageFormat png;if(!stream.openedOk()||!png.writeImageToStream(image,stream))throw std::runtime_error("Raster failed");};
 auto* retryPtr=recursiveButton(view,"Check original exercise preparation");if(!retryPtr)throw std::runtime_error("Specific original retry caption absent");auto& retry=*retryPtr;
 if(!retry.isVisible()||!retry.isEnabled()||!view.getLocalBounds().contains(retry.getBounds()))throw std::runtime_error("Original retry button unusable");
 if(!retry.getTitle().contains("retained request identity and payload are unchanged"))throw std::runtime_error("Original retry contract missing");
 raster("queue-original.png");capture_fixture::write(out/"visible-retry.json",storage::canonical(json::Value::Object{{"label",retry.getButtonText().toStdString()},{"title",retry.getTitle().toStdString()}}));
 activate(retry);h.wait([&]{return h.home->page()==H::Page::Practice&&!L::pending(*h.home);},"actual Retry callback restores original");
 const auto current=json::parse(L::retained(*h.home));for(const auto* field:{"operation","at","plan","outcome"})if(storage::canonical(current.object().at(field))!=storage::canonical(request.object().at(field)))throw std::runtime_error("Retry replaced original request");
 capture_fixture::write(out/"recovered-identity.json",storage::canonical(json::Value::Object{{"created",created},{"capture",h.practice().captureSessionId()},{"retained",current}}));if(h.practice().captureSessionId()!=created||current.object().at("session").string()!=created)throw std::runtime_error("Retry replaced original Session");
 raster("queue-recovered.png");pressName(h.practice(),"Back to Learn");h.wait([&]{return h.home->page()==H::Page::Learn;},"actual Practice Back");
 auto& next=control<juce::Button>(view,"learn-queue-next");if(!next.isVisible()||!next.isEnabled()||next.getWidth()<=0||next.getHeight()<=0||!view.getLocalBounds().contains(next.getBounds()))throw std::runtime_error("Next control unusable");capture_fixture::write(out/"visible-next.json",storage::canonical(json::Value::Object{{"label",next.getButtonText().toStdString()}}));activate(next);h.wait([&]{return !L::owned(*h.home)&&!L::pending(*h.home);},"actual Next closes unused Session");
 bool closed=true;
 const auto after=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));capture_fixture::write(out/"after.json",storage::canonical(after.data));

 const auto& ba=baseline.data.object().at("authoritative").object();const auto& aa=after.data.object().at("authoritative").object();
 bool exactClose=false;for(const auto& row:aa.at("session_close").array())if(row.array()[0].string()==created)exactClose=row.array()[2].string()=="cancelled";
 if(aa.at("session").array().size()!=ba.at("session").array().size()+1||aa.at("session_close").array().size()!=ba.at("session_close").array().size()+1||!exactClose||!L::settled(*h.home))throw std::runtime_error("original unused Session close mismatch");
 for(const auto* name:{"identity","pending","finalized","source_attestation","rule_observation"})if(storage::canonical(aa.at(name))!=storage::canonical(ba.at(name)))throw std::runtime_error("unauthorized activity evidence");
 if(!closed||nativeOpens!=0||connections!=0)throw std::runtime_error("controlled component sequence incomplete; ordinary destructor cleanup only");
 std::cout<<"QUEUE_COMPONENT_SEQUENCE_COMPLETE no_audio=true native_fault_NOT_OBSERVED=true"<<std::endl;return 0;
 }catch(const std::exception&e){std::cerr<<"QUEUE_FIXTURE_FAIL "<<e.what()<<std::endl;return 1;}}
