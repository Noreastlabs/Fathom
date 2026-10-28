#include "ordinary_recovery_test_harness.hpp"
#include "fixtures/recovery/TestSupport.hpp"
int main(int argc,char** argv){try{
 if(argc!=4)throw std::runtime_error("Installed source bundle, existing recovery evidence, fresh private/tmp fixture required");
 const std::filesystem::path bundle=argv[1],evidence=argv[2],dir=argv[3];
 if(!dir.is_absolute()||dir.parent_path()!=std::filesystem::path("/private/tmp")||std::filesystem::exists(dir)||std::filesystem::is_symlink(std::filesystem::symlink_status(dir)))throw std::runtime_error("Fresh private synthetic fixture required");
 std::filesystem::create_directory(dir);std::filesystem::permissions(dir,std::filesystem::perms::owner_all);
 auto local=desktop::openLocalProfile(dir/"profile.sqlite","Etc/UTC");
 // A genuinely persisted completed declaration must restore only after the
 // genuine recovered original is resolved; reads must never rewrite it.
 auto declaration=desktop::setup::Model{};declaration.completed=true;declaration.step=desktop::setup::Step::Summary;declaration.boardDisplay.visible=true;
 capture_fixture::confirmed(local.store->compareExchangePreferences(storage::newUuid(),desktop::setup::preferenceKey,1,0,storage::canonical(desktop::setup::encodePreferences(declaration)),true));
 capture_fixture::confirmed(local.store->compareExchangePreferences(storage::newUuid(),desktop::presentation::preferenceKey,1,0,storage::canonical(desktop::presentation::encodePreferences(desktop::presentation::Level::Beginner)),true));
 auto cp=recovery_test::load(recovery_test::oracle(evidence,"running-partial")/"checkpoint.json");
 auto context=cp.object().at("context");context.object()["session_id"]=local.sessionId;
 const auto allocated=capture_fixture::confirmed(local.store->allocate(storage::newUuid(),"Attempt",context,"2026-09-07T00:30:00Z"));
 cp=recovery_test::rebindCheckpoint(cp,allocated.owner,context);const auto checkpoint=recovery_test::snap(cp);
 capture_fixture::confirmed(local.store->checkpoint(storage::newUuid(),allocated.owner,checkpoint.generation,checkpoint.sequence,checkpoint.bytes));
 const auto baseline=capture_fixture::at(capture_fixture::confirmed(local.store->snapshot(storage::newUuid())).data,"authoritative");
 juce::ScopedJuceInitialiser_GUI gui;auto owner=std::make_unique<H>();auto& home=*owner;home.setVisible(true);home.setSize(920,680);home.beginInitialSetup();
 if(!home.configureCapture(*local.store,local.sessionId,local.timezone)||!home.attachPresentation(*local.store,local.profileId))throw std::runtime_error("Actual ordinary Home attachments");A::halt(home);
 auto tick=[&]{A::tick(home);pump();};
 auto facts=[&]{return A::navigationFacts(home)+" recoveryHeld="+std::to_string(A::originalRecovery(home).held())+" recoveryBusy="+std::to_string(A::originalRecovery(home).busy())+" restorePending="+std::to_string(A::setupRestorePending(home))+" restoreGatesReady="+std::to_string(A::setupRestoreGatesReady(home));};
 auto wait=[&](const char* stage,auto predicate){std::cout<<"RECOVERED_SETUP_WAIT_BEGIN "<<stage<<" "<<facts()<<std::endl;const auto deadline=capture_fixture::now()+7000;while(!predicate()){if(capture_fixture::now()>deadline)throw std::runtime_error(std::string("Home recovery fixture watchdog stage=")+stage+" "+facts());tick();}std::cout<<"RECOVERED_SETUP_WAIT_DONE "<<stage<<" "<<facts()<<std::endl;};
 wait("initial-owner-read-and-recovery-discovery",[&]{return A::setupReadersSettled(home)&&!A::originalRecovery(home).busy();});
 wait("setup-restore-gates-ready-while-original-held",[&]{return A::setupRestoreGatesReady(home);});
 // Exercise the real timer after both saved owners and release gates are ready.
 // Do not assert the asynchronous pending flag before recovery is resolved.
 tick();
 if(!A::originalRecovery(home).held()||home.navigate(H::Page::Learn)||A::practice(home).canStartNewCapture())throw std::runtime_error("Old original debt failed new activity gate");
 if(A::practice(home).startSample()||A::practice(home).captureSession()->startTaken()||connections||nativeOpens||home.getPeer())throw std::runtime_error("Discovery admitted new output/activity");
 auto authority=[&]{return capture_fixture::at(capture_fixture::confirmed(local.store->snapshot(storage::newUuid())).data,"authoritative");};
 if(authority()!=baseline)throw std::runtime_error("Home discovery changed original all14");
 std::cout<<"RECOVERED_SETUP_PRECONDITIONS heldOriginal=true all14Equal=true newActivityHeld=true outputNotOpened=true\n";
 if(home.page()!=H::Page::Onboarding)throw std::runtime_error("Recovery overlay lost original Setup underlay");
 std::string setupHomeReason;
 if(home.requestHome(setupHomeReason)||A::homeRouteStatus(home)!="Use Back or the existing setup action to retain your draft before Home.")throw std::runtime_error("Same-page setup Home refusal status lost");
 tick();if(A::homeRouteStatus(home)!=setupHomeReason)throw std::runtime_error("Same-page refresh erased held Home instruction");
 if(A::originalRecovery(home).selectedOriginal()||A::originalRecovery(home).saveOriginal())throw std::runtime_error("Original selected/saved without explicit owner choice");
 if(!A::originalRecovery(home).selectOriginal(allocated.owner))throw std::runtime_error("Exact original selection");
 wait("exact-selected-original-read",[&]{return !A::originalRecovery(home).busy();});
 click(A::originalRecovery(home),"Keep original and show details");tick();if(!A::originalRecovery(home).held()||authority()!=baseline)throw std::runtime_error("Keep original changed authority/gate");
 // Dispatch the actual visible explicit Save button; no direct storage finalization.
 click(A::originalRecovery(home),"Save original stopped activity");wait("genuine-original-save-confirmed-and-recovery-released",[&]{return !A::originalRecovery(home).busy()&&!A::originalRecovery(home).held();});
 const auto finalized=capture_fixture::confirmed(local.store->recoveryState(storage::newUuid(),allocated.owner));
 const auto envelope=storage::validateEnvelope(finalized.data.object().at("payload").string());
 if(envelope.owner!=allocated.owner||envelope.contextBytes!=storage::canonical(context)||envelope.value.object().at("result").object().at("active")!=cp.object().at("practice_snapshot").object().at("active"))throw std::runtime_error("Explicit original Save lost exact owner/context/active");
 std::cout<<"RECOVERED_SETUP_ORIGINAL_SAVE_VALIDATED owner="<<allocated.owner<<" exactContext=true exactActive=true"<<std::endl;
 wait("post-save-saved-owner-and-release-gates-ready",[&]{return A::setupRestoreGatesReady(home);});
 tick();
 // The timer has polled a genuinely resolved original and serviced ready setup
 // owners. Completed declarations require Home; no Reload/Finish/Skip fallback.
 if(home.page()==H::Page::Onboarding&&!A::setupRestorePending(home))throw std::runtime_error("Completed saved setup remained on Initial setup after original Save: restoration pending was consumed");
 if(home.page()!=H::Page::Home||A::setupRestorePending(home))throw std::runtime_error("Completed saved setup post-Save navigation did not settle: "+facts());
 if(!home.setupModel().completed||home.setupModel()!=declaration||home.audioSettings().snapshot().state!=output::State::Closed||nativeOpens||connections)throw std::runtime_error("Completed setup did not restore automatically after genuine original Save without output");
 const auto saved=authority();
 if(saved.object().at("preferences")!=baseline.object().at("preferences"))throw std::runtime_error("Recovery/setup restore rewrote original saved preferences");
 if(A::originalRecovery(home).saveOriginal()||authority()!=saved)throw std::runtime_error("Settled original duplicate changed authority");
 // Real page transitions must replace old Setup/held labels, while pure
 // Progress refresh stays authority-neutral. No source opening or selection.
 if(!home.navigate(H::Page::Progress)||A::homeRouteStatus(home)!="Fathom / Progress")throw std::runtime_error("Progress retained stale Setup breadcrumb");
 wait("read-only-progress-refresh",[&]{return !A::progress(home).busy();});
 std::string homeReason;if(!home.requestHome(homeReason)||home.page()!=H::Page::Home)throw std::runtime_error("Read-only Progress Home return");
 if(!home.navigate(H::Page::SourceLibrary)||A::homeRouteStatus(home)!="Fathom / Original workbooks")throw std::runtime_error("Source browser retained stale child breadcrumb");
 if(!home.requestHome(homeReason)||authority()!=saved)throw std::runtime_error("Read-only child route altered saved original authorities");
 auto& learn=A::lessons(home);if(!learn.load(bundle)||!home.navigate(H::Page::Learn))throw std::runtime_error("Fresh discovery failed normal Learn release");
 choose(learn,"fg:item:000002","fg:variant:000006");click(learn,"Practice selected case");auto& practice=A::practice(home);
 click(practice,"Audio settings");tick();click(A::settings(home),"Connect audio");tick();click(A::settings(home),"Enable audio");platform::OutputTestAccess::block(A::output(home));tick();click(A::settings(home),"Back to Practice");tick();
 click(practice,"Start selected case");wait("fresh-owner-start-accepted",[&]{return practice.captureSession()->startTaken();});
 if(practice.captureSession()->binding().owner.empty()||practice.captureSession()->binding().owner==allocated.owner)throw std::runtime_error("Released new Start reused old owner");
 platform::OutputTestAccess::block(A::output(home));tick();wait("fresh-owner-discard-output-closure",[&]{platform::OutputTestAccess::block(A::output(home));return practice.requestExit(true);});
 if(practice.audioSnapshot().state!=output::State::Closed)throw std::runtime_error("Actual new output shutdown incomplete");
 const auto finalAuthority=authority();if(finalAuthority.object().at("preferences")!=baseline.object().at("preferences"))throw std::runtime_error("Fresh owner activity rewrote original setup preferences");if(finalAuthority.object().at("finalized").array().size()!=saved.object().at("finalized").array().size())throw std::runtime_error("New discarded test capture invented final outcome");
 capture_fixture::write(dir/"authority-before.json",storage::canonical(baseline));capture_fixture::write(dir/"authority-original-saved.json",storage::canonical(saved));capture_fixture::write(dir/"authority-final.json",storage::canonical(finalAuthority));
 owner.reset();local.store->beginShutdown();const auto end=capture_fixture::now()+7000;while(!local.store->shutdownComplete()&&local.store->shutdownError().empty()){if(capture_fixture::now()>end)throw std::runtime_error("Writer shutdown watchdog");pump();}if(!local.store->shutdownComplete())throw std::runtime_error(local.store->shutdownError());local.store.reset();
 std::cout<<"PASS ordinary Home original recovery held/no writes; explicit Save once exact quantity; fresh discovery releases new Start; actual software/Store closure\n";return 0;
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
