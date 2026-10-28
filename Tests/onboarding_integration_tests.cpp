// Actual Home and Store owners; reuse the established software-only device leaves.
#define main retained_setup_shared_audio_fixture_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include <condition_variable>
namespace fathom::desktop {
struct OnboardingIntegrationTestAccess {
    static void tick(HomeView& h){h.timerCallback();}
    static OnboardingView& view(HomeView& h){return h.onboarding_;}
    static setup::PreferencesController& preferences(HomeView& h){return h.setupPreferences_;}
    static presentation::PreferencesController& presentation(HomeView& h){return h.presentation_;}
    static GuitarSetupView& guitar(HomeView& h){return h.setup;}
    static bool finishing(const HomeView& h){return h.setupFinish_!=HomeView::SetupFinish::Idle;}
    static bool restoring(const HomeView& h){return h.setupRestorePending_;}
    static void stopTimer(HomeView& h){h.stopTimer();}
    static void serviceRestore(HomeView& h){h.serviceSetup(false);}
};
}
namespace {
using SetupAccess=desktop::OnboardingIntegrationTestAccess;
int setupChecks=0;
void verifySetup(bool pass,const char* label){++setupChecks;std::cout<<(pass?"PASS ":"FAIL ")<<label<<'\n';if(!pass)throw std::runtime_error(label);}
void settleSetup(H& h){const auto until=std::chrono::steady_clock::now()+std::chrono::seconds(8);do{SetupAccess::tick(h);pump();if(std::chrono::steady_clock::now()>until)throw std::runtime_error("Original setup owner watchdog");}while(SetupAccess::preferences(h).inFlight()||SetupAccess::presentation(h).inFlight()||SetupAccess::finishing(h));}
std::string setupIdentity(storage::ProfileStore& store){return store.snapshot(storage::newUuid()).get().data.object().at("profile_id").string();}
storage::StoreOptions setupOptions(const std::filesystem::path& root){storage::StoreOptions o;o.path=root/"profile.sqlite";o.create=true;o.createdUtc="2026-10-07T13:40:00Z";o.preferenceValidator=desktop::presentation::composedPreferenceValidator;return o;}
json::Value setupHistory(storage::ProfileStore& store){auto a=store.snapshot(storage::newUuid()).get().data.object().at("authoritative");a.object().erase("preferences");return a;}
desktop::setup::Model savedSetup(storage::ProfileStore& store){const auto r=store.readPreferences(storage::newUuid(),desktop::setup::preferenceKey).get();if(r.status!=storage::Status::Confirmed)throw std::runtime_error("Expected actual saved setup");return desktop::setup::decodePreferences(storage::parseCanonical(r.data.object().at("bytes").string()));}
std::int64_t setupRevision(storage::ProfileStore& store){std::int64_t revision{};const auto r=store.readPreferences(storage::newUuid(),desktop::setup::preferenceKey).get();if(r.status!=storage::Status::Confirmed||!r.data.object().at("revision").integer(revision))throw std::runtime_error("Expected actual setup revision");return revision;}
struct SetupGate{std::atomic<bool> armed{false},entered{false};std::mutex m;std::condition_variable cv;bool released=false;void wait(){if(!armed.exchange(false))return;std::unique_lock<std::mutex> l(m);entered=true;cv.notify_all();cv.wait(l,[this]{return released;});}void release(){std::lock_guard<std::mutex> l(m);released=true;cv.notify_all();}void await(){std::unique_lock<std::mutex> l(m);if(!cv.wait_for(l,std::chrono::seconds(3),[this]{return entered.load();}))throw std::runtime_error("Setup fixture latch watchdog");}};
struct SetupRelease{SetupGate& g;~SetupRelease(){g.release();}};
}
int main(int argc,char** argv){try{
 if(argc!=2||!std::filesystem::path(argv[1]).is_absolute()||std::filesystem::exists(argv[1]))throw std::runtime_error("Fresh absolute isolated evidence root required");
 const std::filesystem::path root(argv[1]);std::filesystem::create_directories(root);std::filesystem::permissions(root,std::filesystem::perms::owner_all);
 juce::ScopedJuceInitialiser_GUI gui;
 {
  H h;h.beginInitialSetup();verifySetup(h.page()==H::Page::Onboarding&&h.audioSettings().snapshot().state==output::State::Closed,"Initial setup precedes Home with closed audio and no profile access");
  auto m=h.setupModel();m.experience=desktop::presentation::Level::Advanced;m.appearance=desktop::setup::Appearance::Light;
  SetupAccess::view(h).onModelChanged(m);verifySetup(h.presentationModel().globalLevel()==m.experience&&desktop::appearance::current()==m.appearance,"Wizard experience and appearance apply for the current session");
  SetupAccess::view(h).onSkip();verifySetup(h.page()==H::Page::Home&&!h.setupModel().completed&&h.setupModel().skipped&&!SetupAccess::preferences(h).hasProfile(),"No-profile Skip preserves explicit choices without claiming saved completion");
  verifySetup(h.openSetupWizard()&&h.setupModel().appearance==m.appearance&&h.presentationModel().globalLevel()==m.experience,"Later setup resumes session choices");
  int opens=0;h.onOpenLocalProfile=[&]{++opens;h.localProfileFailed("controlled open failure");return false;};
  SetupAccess::view(h).onFinish();verifySetup(opens==1&&!SetupAccess::finishing(h)&&!h.setupModel().completed&&h.page()==H::Page::Onboarding,"Failed explicit profile open leaves incomplete draft and recoverable wizard");
  verifySetup(h.requestClose(),"No-profile incomplete draft does not fabricate a write during Quit");
  H recovered;auto retained=h.setupModel();retained.guitar.capo=3;retained.audio.master=43;recovered.resumeInitialSetup(retained);SetupAccess::view(recovered).onNext();
  verifySetup(recovered.setupModel().guitar.capo==3&&recovered.setupModel().audio.master==43&&SetupAccess::guitar(recovered).currentSetup().capo==3&&recovered.audioSettings().selected().master==43&&recovered.audioSettings().snapshot().state==output::State::Closed,"Fresh-Home rollback resumes the actual custom guitar/audio owners without sound or profile writes");recovered.requestClose();
  H paused;verifySetup(paused.navigate(H::Page::Freeplay)&&A::freeplay(paused).startFreeplay(),"No-profile Freeplay can retain active time");
  verifySetup(A::freeplay(paused).pauseFreeplay()&&paused.navigate(H::Page::Home)&&!paused.canOpenLocalProfile()&&!paused.openSetupWizard(),"Paused activity refuses profile/setup replacement while retaining duration");
  A::freeplay(paused).stopFreeplay();paused.requestClose();
 }
 desktop::appearance::set(desktop::setup::Appearance::Default);
 {
  storage::ProfileStore store(setupOptions(root/"profile-button"));H h;h.beginInitialSetup();
  auto m=h.setupModel();m.experience=desktop::presentation::Level::Developer;SetupAccess::view(h).onModelChanged(m);
  int opens=0;h.onOpenExistingLocalProfile=[&]{++opens;return h.attachPresentation(store,setupIdentity(store));};
  SetupAccess::view(h).onOpenLocalProfile();settleSetup(h);
  verifySetup(opens==1&&h.presentationModel().globalLevel()==m.experience&&h.setupModel().experience==m.experience,"Explicit experience survives the profile button's queued preference attachment");
  verifySetup(store.readPreferences(storage::newUuid(),desktop::presentation::preferenceKey).get().status==storage::Status::DefinitelyAbsent,"Profile attachment alone never saves the explicit experience choice");h.requestClose();h.detachForStoreReopen();
 }
 {
  auto o=setupOptions(root/"unknown-finish");bool loseReceipt=false;
  o.diagnosticHook=[&](const auto& phase,const auto&){if(phase=="after_commit"&&loseReceipt){loseReceipt=false;throw std::runtime_error("controlled receipt loss");}};
  storage::ProfileStore store(o);H h;h.beginInitialSetup();h.attachPresentation(store,setupIdentity(store));settleSetup(h);
  auto m=h.setupModel();m.step=desktop::setup::Step::Summary;SetupAccess::view(h).onModelChanged(m);loseReceipt=true;SetupAccess::view(h).onFinish();settleSetup(h);
  const auto setupOp=SetupAccess::preferences(h).pendingOperationId(),setupBytes=SetupAccess::preferences(h).pendingBytes();
  const auto levelOp=SetupAccess::presentation(h).pendingOperationId(),levelBytes=SetupAccess::presentation(h).pendingBytes();
  verifySetup((!setupOp.empty()||!levelOp.empty())&&!SetupAccess::finishing(h)&&!savedSetup(store).completed,"Unknown acknowledgment in either namespace holds its original proposal and cannot mark setup complete");
  SetupAccess::view(h).onFinish();SetupAccess::tick(h);
  verifySetup(SetupAccess::preferences(h).pendingOperationId()==setupOp&&SetupAccess::preferences(h).pendingBytes()==setupBytes&&SetupAccess::presentation(h).pendingOperationId()==levelOp&&SetupAccess::presentation(h).pendingBytes()==levelBytes&&!h.requestClose()&&h.closeState()==H::CloseState::Held,"Repeated Finish/Quit retain both namespace proposals without replacement writes");
  SetupAccess::view(h).onReload();settleSetup(h);verifySetup(SetupAccess::preferences(h).pendingOperationId().empty()&&SetupAccess::presentation(h).pendingOperationId().empty()&&!savedSetup(store).completed,"Read-only inspection confirms the exact original values without inventing completion");
  SetupAccess::view(h).onFinish();settleSetup(h);verifySetup(savedSetup(store).completed&&h.page()==H::Page::Home,"Explicit retry completes after original reconciliation");h.requestClose();h.detachForStoreReopen();
 }
 std::string identity;
 {
  storage::ProfileStore store(setupOptions(root/"saved"));identity=setupIdentity(store);const auto history=setupHistory(store);
  H h;h.beginInitialSetup();verifySetup(h.attachPresentation(store,identity),"Attach both named setup/presentation owners to the exact profile");settleSetup(h);
  auto m=h.setupModel();m.experience=desktop::presentation::Level::Developer;m.appearance=desktop::setup::Appearance::Light;m.step=desktop::setup::Step::Guitar;SetupAccess::view(h).onModelChanged(m);
  SetupAccess::view(h).onOpenGuitar();verifySetup(h.page()==H::Page::Setup,"Wizard borrows the existing guitar owner");
  auto guitar=m.guitar;guitar.capo=2;guitar.handedness=guitar::Handedness::Left;
  verifySetup(SetupAccess::guitar(h).applySetup(guitar),"Existing stopped/resolved guitar Apply remains authoritative");SetupAccess::guitar(h).onBack();settleSetup(h);
  verifySetup(h.page()==H::Page::Onboarding&&savedSetup(store).guitar.capo==2&&!savedSetup(store).completed,"Guitar Back saves a resumable draft without completion");
  m=h.setupModel();m.step=desktop::setup::Step::Audio;SetupAccess::view(h).onModelChanged(m);SetupAccess::view(h).onOpenAudio();
  auto mix=h.audioSettings().selected();mix.master=37;mix.masterMute=true;verifySetup(h.audioSettings().selectMix(mix),"Existing shared audio mix selection remains configuration only");
  h.returnFromAudioSettings();settleSetup(h);verifySetup(h.page()==H::Page::Onboarding&&savedSetup(store).audio.master==37&&savedSetup(store).audio.masterMute&&h.audioSettings().snapshot().state==output::State::Closed,"Audio Back confirms draft after return without connecting or enabling");
  m=h.setupModel();m.step=desktop::setup::Step::Summary;SetupAccess::view(h).onModelChanged(m);SetupAccess::view(h).onFinish();SetupAccess::view(h).onFinish();settleSetup(h);
  verifySetup(h.page()==H::Page::Home&&savedSetup(store).completed&&!savedSetup(store).skipped,"Repeated Finish confirms both namespaces before the completion marker");
  const auto r=store.readPreferences(storage::newUuid(),desktop::presentation::preferenceKey).get();verifySetup(desktop::presentation::decodePreferences(storage::parseCanonical(r.data.object().at("bytes").string()))==m.experience,"Canonical experience is saved independently before completion");
  const auto revision=setupRevision(store);for(int i=0;i<4;++i)SetupAccess::tick(h);verifySetup(setupRevision(store)==revision&&setupHistory(store)==history,"Repeated polling cannot add setup revisions, Sessions, attempts, closes or credit");
  verifySetup(h.requestClose()&&h.detachForStoreReopen(),"Confirmed setup permits existing normal close and safe Store detach");
 }
 desktop::appearance::set(desktop::setup::Appearance::Default);
 {
  auto o=setupOptions(root/"saved");o.create=false;storage::ProfileStore store(o);H h;h.beginInitialSetup();verifySetup(h.attachPresentation(store,identity),"Restart attaches the original saved profile");settleSetup(h);
  verifySetup(h.page()==H::Page::Home&&h.setupModel().completed&&h.setupModel().appearance==desktop::setup::Appearance::Light&&h.audioSettings().selected().master==37&&h.audioSettings().snapshot().state==output::State::Closed&&SetupAccess::guitar(h).currentSetup().capo==2,"Restart restores completed configuration with audio closed and original guitar");
  verifySetup(h.presentationModel().globalLevel()==desktop::presentation::Level::Developer,"Restart retains canonical experience authority");h.requestClose();h.detachForStoreReopen();
 }
 {
  SetupGate gate;auto o=setupOptions(root/"quit-in-flight");o.diagnosticHook=[&](const auto& phase,const auto&){if(phase=="before_operation")gate.wait();};storage::ProfileStore store(o);SetupRelease release{gate};H h;h.beginInitialSetup();h.attachPresentation(store,setupIdentity(store));settleSetup(h);
  auto m=h.setupModel();m.step=desktop::setup::Step::Summary;m.experience=desktop::presentation::Level::Advanced;SetupAccess::view(h).onModelChanged(m);SetupAccess::view(h).onFinish();gate.armed=true;SetupAccess::tick(h);gate.await();
  verifySetup(!h.requestClose()&&h.closeState()==H::CloseState::Waiting&&!SetupAccess::finishing(h),"Quit cancels future completion-chain intent before waiting for original writes");gate.release();settleSetup(h);
  verifySetup(!savedSetup(store).completed&&h.requestClose(),"Original draft settles for normal Quit without a newly enqueued completion marker");h.detachForStoreReopen();
 }
 {
  auto o=setupOptions(root/"restore-while-away");storage::ProfileStore store(o);auto m=desktop::setup::Model{};m.step=desktop::setup::Step::Audio;m.appearance=desktop::setup::Appearance::Dark;
  const auto seeded=store.compareExchangePreferences(storage::newUuid(),desktop::setup::preferenceKey,1,0,storage::canonical(desktop::setup::encodePreferences(m)),true).get();verifySetup(seeded.status==storage::Status::Confirmed,"Seed incomplete saved draft without session activity");
  H h;h.attachPresentation(store,setupIdentity(store));verifySetup(h.navigate(H::Page::Freeplay),"User may navigate while saved setup is being read");settleSetup(h);
  verifySetup(h.page()==H::Page::Freeplay&&SetupAccess::restoring(h),"Delayed initial setup read cannot steal an activity page");verifySetup(h.navigate(H::Page::Home),"Return through original safe activity navigation");settleSetup(h);
  verifySetup(h.page()==H::Page::Onboarding&&h.setupModel().step==desktop::setup::Step::Audio&&!SetupAccess::restoring(h),"Incomplete draft resumes only after the stopped/resolved gate");h.requestClose();h.detachForStoreReopen();
 }
 {
  SetupGate gate;auto o=setupOptions(root/"queued-experience");o.diagnosticHook=[&](const auto& phase,const auto&){if(phase=="before_operation")gate.wait();};storage::ProfileStore store(o);SetupRelease release{gate};
  auto m=desktop::setup::Model{};m.step=desktop::setup::Step::Audio;
  store.compareExchangePreferences(storage::newUuid(),desktop::setup::preferenceKey,1,0,storage::canonical(desktop::setup::encodePreferences(m)),true).get();
  H h;const auto id=setupIdentity(store);gate.armed=true;h.attachPresentation(store,id);gate.await();
  SetupAccess::presentation(h).chooseGlobal(desktop::presentation::Level::Developer);gate.release();settleSetup(h);
  verifySetup(h.presentationModel().globalLevel()==desktop::presentation::Level::Developer&&h.setupModel().experience==desktop::presentation::Level::Developer,"Incomplete setup restoration preserves a newer explicit experience choice during queued reads");
  verifySetup(savedSetup(store).experience==desktop::presentation::Level::Beginner&&setupRevision(store)==1,"Mirrored newer session experience does not silently rewrite saved draft");h.requestClose();h.detachForStoreReopen();
 }

 // Canonical presentation and an older unfinished setup may finish reading in
 // either order. Exercise actual owners without relying on scheduler timing.
 for(const bool skipped:{false,true})for(const bool setupFirst:{false,true}){
  const auto name=std::string{"canonical-vs-draft-"}+(skipped?"skipped-":"unfinished-")+(setupFirst?"setup-first":"presentation-first");
  storage::ProfileStore store(setupOptions(root/name));auto draft=desktop::setup::Model{};draft.skipped=skipped;
  verifySetup(store.compareExchangePreferences(storage::newUuid(),desktop::setup::preferenceKey,1,0,storage::canonical(desktop::setup::encodePreferences(draft)),true).get().status==storage::Status::Confirmed,"Seed older Beginner setup draft");
  verifySetup(store.compareExchangePreferences(storage::newUuid(),desktop::presentation::preferenceKey,1,0,storage::canonical(desktop::presentation::encodePreferences(desktop::presentation::Level::Advanced)),true).get().status==storage::Status::Confirmed,"Seed independent canonical Advanced presentation");
  const auto before=store.snapshot(storage::newUuid()).get().data.object().at("authoritative");
  H h;SetupAccess::stopTimer(h);h.beginInitialSetup();verifySetup(h.attachPresentation(store,setupIdentity(store)),"Attach canonical presentation plus older draft");
  const auto pollOwner=[&](bool setupOwner){const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(8);while(setupOwner?SetupAccess::preferences(h).inFlight():SetupAccess::presentation(h).inFlight()){
   if(std::chrono::steady_clock::now()>end)throw std::runtime_error("Independent restore owner watchdog");
   if(setupOwner)SetupAccess::preferences(h).poll();else SetupAccess::presentation(h).poll();pump();
  }};
  pollOwner(setupFirst);SetupAccess::serviceRestore(h);
  verifySetup(SetupAccess::restoring(h),"One settled namespace cannot restore before the other owner settles");
  pollOwner(!setupFirst);SetupAccess::serviceRestore(h);SetupAccess::tick(h);
  verifySetup(!SetupAccess::restoring(h)&&h.presentationModel().globalLevel()==desktop::presentation::Level::Advanced&&!SetupAccess::presentation(h).dirty(),"Saved Advanced wins over older Beginner draft in both read orders");
  verifySetup(h.setupModel().experience==desktop::presentation::Level::Beginner&&h.page()==(skipped?H::Page::Home:H::Page::Onboarding),"Original draft experience and skipped/unfinished navigation are retained");
  verifySetup(h.audioSettings().snapshot().state==output::State::Closed&&store.snapshot(storage::newUuid()).get().data.object().at("authoritative")==before,"Restoration changes no stored preference or history and starts no audio");
  verifySetup(h.requestClose()&&h.detachForStoreReopen(),"Restored canonical choice permits normal closure without a save");
 }
 verifySetup(nativeOpens==0&&connections==0,"Setup construction never opens a real or synthetic device or starts audio");
 capture_fixture::write(root/"summary.json",storage::canonical(json::Value::Object{{"checks",json::Value::fromInteger(setupChecks)},{"failures",json::Value::fromInteger(0)},{"scope","software-only actual Home/Store; no hardware or acceptance increment"}}));std::cout<<"SETUP_INTEGRATION_PASS checks="<<setupChecks<<'\n';return 0;
 }catch(const std::exception& e){std::cerr<<"SETUP_INTEGRATION_FAILURE "<<e.what()<<'\n';return 1;}}
