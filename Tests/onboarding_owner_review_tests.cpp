// Owner review regressions: real components and private own Stores, no native peer.
#define main retained_audio_tests_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include "desktop/LocalProfile.hpp"
#include "../Source/desktop/Main.cpp"
#include <atomic>
#include <condition_variable>
namespace fathom::desktop {
struct OnboardingIntegrationTestAccess {
 static void tick(HomeView& h){h.timerCallback();}
 static OnboardingView& view(HomeView& h){return h.onboarding_;}
 static OriginalActivityRecovery& recovery(HomeView& h){return h.originalRecovery_;}
 static bool finishing(const HomeView& h){return h.setupFinish_!=HomeView::SetupFinish::Idle;}
 static bool waiting(const HomeView& h){return h.setupPreferences_.inFlight()||h.presentation_.inFlight()||h.localProfileOpening_;}
};
}
namespace {
struct MainOwnerTestAccess {
 static Home& prepare(Application& a,const std::filesystem::path& p,int& exits){a.window=std::make_unique<Window>(false);a.localProfileSelfTestPath=p;a.fixtureExitReady=[&]{++exits;};a.wireLocalProfile();a.window->onCancelQuit=[&a]{a.cancelQuit();};a.window->onQuitChoice=[&a](bool discard){a.chooseQuit(discard);};a.window->home().beginInitialSetup();return a.window->home();}
 static void tick(Application& a){a.pollLocalOpening();desktop::OnboardingIntegrationTestAccess::tick(a.window->home());}
 static void discard(Application&a){a.chooseQuit(true);}
 static juce::Component& window(Application&a){return *a.window;}
 static std::string profile(const Application&a){return a.profileId;}
 static std::filesystem::path path(const Application&a){return a.profilePath;}
 static bool opened(const Application&a){return bool(a.store);}
 static storage::ProfileStore* store(Application&a){return a.store.get();}
};
}
using Access=desktop::OnboardingIntegrationTestAccess;
namespace {
int checks=0;void ck(bool b,const char* t){++checks;std::cout<<(b?"PASS ":"FAIL ")<<t<<std::endl;if(!b)throw std::runtime_error(t);}
juce::Button& control(juce::Component& c,const char* id){auto find=[&](auto&&self,juce::Component&root)->juce::Component*{if(root.getComponentID()==id)return &root;for(auto*child:root.getChildren())if(auto*found=self(self,*child))return found;return nullptr;};auto*b=dynamic_cast<juce::Button*>(find(find,c));if(!b)throw std::runtime_error(std::string("Missing ")+id);return *b;}
void press(juce::Component&c,const char*id){auto&b=control(c,id);ck(b.isVisible()&&b.isEnabled(),"Actual test control visible and enabled");activate(b);}
template<class F>void wait(Application&a,F f){auto until=std::chrono::steady_clock::now()+std::chrono::seconds(8);while(!f()){MainOwnerTestAccess::tick(a);pump();if(std::chrono::steady_clock::now()>until)throw std::runtime_error("8s watchdog");}}
json::Value authority(storage::ProfileStore&s){return capture_fixture::confirmed(s.snapshot(storage::newUuid())).data.object().at("authoritative");}
std::filesystem::path sub(const std::filesystem::path&r,const char*n){auto p=r/n;std::filesystem::create_directory(p);std::filesystem::permissions(p,std::filesystem::perms::owner_all);return p;}
void raster(juce::Component& c,const std::filesystem::path&p){auto img=c.createComponentSnapshot(c.getLocalBounds());juce::FileOutputStream out(juce::File(p.string()));ck(juce::PNGImageFormat().writeImageToStream(img,out),"Actual component raster saved");}
void close(Application&a,int&exits){a.systemRequestedQuit();MainOwnerTestAccess::discard(a);wait(a,[&]{return exits==1;});a.shutdown();}
}
int main(int argc,char**argv){try{if(argc!=2||std::filesystem::exists(argv[1]))throw std::runtime_error("Fresh output root required");std::filesystem::path root=argv[1];std::filesystem::create_directory(root);std::filesystem::permissions(root,std::filesystem::perms::owner_all);juce::ScopedJuceInitialiser_GUI gui;
{
 auto p=sub(root,"missing")/"profile.sqlite";bool refused=false;try{desktop::openLocalProfile(p,"Etc/UTC",desktop::LocalProfileIntent::ExistingOnly);}catch(const std::exception&){refused=true;}ck(refused&&!std::filesystem::exists(p),"Open existing refuses missing file without creating anything");
}
std::string namedId;std::filesystem::path namedFile;json::Value namedAuthority;
std::filesystem::path existing=sub(root,"existing")/"profile.sqlite";std::string profile,session;json::Value before;
{
 auto opened=desktop::openLocalProfile(existing,"Etc/UTC",desktop::LocalProfileIntent::CreateOnly);profile=opened.profileId;session=opened.sessionId;
 // One explicit synthetic unfinished original, like Joe's screenshot; no checkpoint/outcome invented.
 auto req=capture_fixture::request(session,true);auto owner=capture_fixture::confirmed(opened.store->allocate(storage::newUuid(),"FreeplayActivity",req.binding.context,"2026-10-25T00:00:00Z"));ck(!owner.owner.empty(),"Own synthetic retained original created for recovery fixture");before=authority(*opened.store);capture_fixture::write(root/"existing-before.json",storage::canonical(before));
}
{
 bool refused=false;try{desktop::openLocalProfile(existing,"Etc/UTC",desktop::LocalProfileIntent::CreateOnly);}catch(const std::exception&){refused=true;}ck(refused,"Create Profile refuses existing profile");auto o=desktop::openLocalProfile(existing,"Etc/UTC",desktop::LocalProfileIntent::ExistingOnly);ck(o.profileId==profile&&o.sessionId==session&&authority(*o.store)==before,"Existing-only open retains exact profile Session and all authority");
}
{
 auto p=sub(root,"empty-existing")/"profile.sqlite";storage::StoreOptions options;options.path=p;options.create=true;options.createdUtc="2026-10-25T00:00:00Z";json::Value snapshot;{storage::ProfileStore s(options);snapshot=authority(s);}bool refused=false;try{desktop::openLocalProfile(p,"Etc/UTC",desktop::LocalProfileIntent::ExistingOnly);}catch(const std::exception&){refused=true;}options.create=false;storage::ProfileStore s(options);ck(refused&&authority(s)==snapshot,"Existing-only empty profile refuses without adding fallback Session");
}
{
 auto p=sub(root,"new-flow")/"profile.sqlite";Application a;int exits=0;auto&h=MainOwnerTestAccess::prepare(a,p,exits);auto&v=Access::view(h);
 ck(!h.getPeer()&&!v.getPeer(),"Detached Main components have no native desktop peer");
 ck(control(v,"onboarding-next").getButtonText()=="Create Profile"&&control(v,"onboarding-open-local-profile").getButtonText()=="Open existing profile","Welcome actions distinguish creation and existing profile");auto* name=dynamic_cast<juce::TextEditor*>(v.findChildWithID("onboarding-profile-name"));ck(name&&!control(v,"onboarding-next").isEnabled(),"Profile name required before creation");name->setText(juce::String::fromUTF8("Joe review 🎸"));wait(a,[&]{return control(v,"onboarding-next").isEnabled();});raster(h,root/"welcome.png");
 press(v,"onboarding-open-local-profile");wait(a,[&]{return !Access::waiting(h);});ck(!std::filesystem::exists(p)&&h.setupModel().step==desktop::setup::Step::Welcome,"Missing existing-profile action returns recoverably to unchanged Welcome");
 press(v,"onboarding-next");ck(h.setupModel().step==desktop::setup::Step::Experience&&!MainOwnerTestAccess::opened(a)&&!std::filesystem::exists(p),"Create Profile begins wizard without touching storage");press(v,"onboarding-back");ck(h.setupModel().step==desktop::setup::Step::Welcome&&!std::filesystem::exists(p),"Cancel creation wizard with Back leaves no profile file");
 press(v,"onboarding-next");for(int i=0;i<4;++i)press(v,"onboarding-next");ck(h.setupModel().step==desktop::setup::Step::Summary&&!std::filesystem::exists(p),"New-profile choices remain draft until Finish");press(v,"onboarding-finish");control(v,"onboarding-finish").onClick();wait(a,[&]{return MainOwnerTestAccess::opened(a)&&!Access::waiting(h)&&!Access::finishing(h);});ck(h.setupModel().completed&&h.page()==H::Page::Home,"Actual Main CreateOnly route creates and finishes setup once");namedId=MainOwnerTestAccess::profile(a);namedFile=MainOwnerTestAccess::path(a);auto snap=authority(*MainOwnerTestAccess::store(a));namedAuthority=snap;ck(snap.object().at("session").array().size()==1&&snap.object().at("identity").array().empty(),"Repeated Finish creates one local Session and no activity");close(a,exits);ck(exits==1,"Fresh app closes normally once");
}
{
 Application reopened;int reexits=0;auto&rh=MainOwnerTestAccess::prepare(reopened,root/"new-flow/profile.sqlite",reexits);press(Access::view(rh),"onboarding-skip");press(rh,"home-user-profile");press(rh,"home-local-profile");wait(reopened,[&]{return MainOwnerTestAccess::opened(reopened)&&!Access::waiting(rh)&&!Access::recovery(rh).busy();});ck(MainOwnerTestAccess::profile(reopened)==namedId&&MainOwnerTestAccess::path(reopened)==namedFile&&authority(*MainOwnerTestAccess::store(reopened))==namedAuthority,"Restart Skip then User profile Open existing uses named active profile and exact history");close(reopened,reexits);
}
{
 Application a;int exits=0;auto&h=MainOwnerTestAccess::prepare(a,existing,exits);auto&v=Access::view(h);press(v,"onboarding-open-local-profile");control(v,"onboarding-open-local-profile").onClick();wait(a,[&]{return MainOwnerTestAccess::opened(a)&&!Access::waiting(h)&&!Access::recovery(h).busy();});auto&rec=Access::recovery(h);ck(rec.held()&&rec.isVisible()&&rec.originals().size()==1&&!rec.selectedOriginal(),"Existing profile displays original recovery without auto selection");raster(h,root/"recovery.png");auto model=h.setupModel();auto*store=MainOwnerTestAccess::store(a);ck(authority(*store)==before,"Actual Main opening route preserves all fourteen authority tables");
 press(rec,"recovery-back");ck(rec.held()&&rec.suspended()&&!rec.isVisible()&&h.setupModel()==model,"Recovery Back hides presentation only and preserves draft plus hold");for(int i=0;i<6;++i){MainOwnerTestAccess::tick(a);pump();}ck(!rec.isVisible()&&!h.navigate(H::Page::Practice)&&!h.canOpenLocalProfile(),"Polling does not reshow recovery or unlock new activity/profile");
 control(v,"onboarding-next").onClick();control(v,"onboarding-skip").onClick();control(v,"onboarding-finish").onClick();control(rec,"recovery-save").onClick();ck(h.setupModel()==model&&authority(*store)==before,"Stale hidden/blocked controls cannot change setup or save original");ck(control(v,"onboarding-open-local-profile").getButtonText()=="Resume profile recovery","Back leaves an explicit same-profile recovery return");raster(h,root/"back-to-setup.png");press(v,"onboarding-open-local-profile");ck(rec.isVisible()&&MainOwnerTestAccess::store(a)==store&&authority(*store)==before,"Resume reuses the same original component and Store without writes");
 ck(rec.selectOriginal(rec.originals()[0].binding.owner),"Select exact retained original read-only");ck(!rec.suspendPresentation(),"Back refused while original read is busy");wait(a,[&]{return !rec.busy();});auto selected=rec.selectedOriginal()->owner;press(rec,"recovery-keep");ck(rec.held()&&rec.selectedOriginal()->owner==selected&&authority(*store)==before,"Keep original/details preserves exact selected work without a write");press(rec,"recovery-back");press(v,"onboarding-open-local-profile");ck(rec.selectedOriginal()->owner==selected&&authority(*store)==before,"Back and re-entry preserve exact selected original and all stored facts");capture_fixture::write(root/"existing-after.json",storage::canonical(authority(*store)));close(a,exits);ck(exits==1,"Existing held original closes normally without saving or replacement");
}
{
 Application a;int exits=0;auto&h=MainOwnerTestAccess::prepare(a,existing,exits);auto&v=Access::view(h);auto summary=h.setupModel();summary.step=desktop::setup::Step::Summary;v.onModelChanged(summary);press(v,"onboarding-finish");wait(a,[&]{return MainOwnerTestAccess::opened(a)&&!Access::waiting(h)&&!Access::recovery(h).busy()&&!Access::finishing(h);});auto&rec=Access::recovery(h);ck(rec.held()&&rec.isVisible()&&authority(*MainOwnerTestAccess::store(a))==before,"Legacy Finish really opens existing unfinished profile; this is not an empty-reader timing hold");press(rec,"recovery-back");ck(!rec.isVisible()&&rec.held()&&h.setupModel().step==desktop::setup::Step::Summary&&!h.setupModel().completed,"Finish recovery has safe Back to the same incomplete Summary");a.systemRequestedQuit();press(MainOwnerTestAccess::window(a),"shutdown-cancel");ck(exits==0&&MainOwnerTestAccess::opened(a)&&authority(*MainOwnerTestAccess::store(a))==before,"Actual Cancel Quit keeps held original and profile exact");press(v,"onboarding-open-local-profile");ck(rec.isVisible(),"Summary can explicitly resume the same recovery");close(a,exits);ck(exits==1,"Legacy Finish recovery closes normally without discarding original records");auto retained=desktop::openLocalProfile(existing,"Etc/UTC",desktop::LocalProfileIntent::ExistingOnly);ck(authority(*retained.store)==before,"Normal close/reopen after legacy Finish keeps all14 original tables exact");
}
ck(nativeOpens==0&&connections==0,"No native peer/device/audio launch used");capture_fixture::write(root/"summary.json",storage::canonical(json::Value::Object{{"checks",json::Value::fromInteger(checks)},{"failures",json::Value::fromInteger(0)},{"native_ui",false},{"owner_acceptance",false}}));std::cout<<"PASS owner onboarding checks="<<checks<<std::endl;return 0;}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<std::endl;return 1;}}
