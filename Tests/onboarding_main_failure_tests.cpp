// Exercise the actual anonymous Main owner. Only platform device leaves and the
// worker/fault/exit boundary seams are synthetic; no Desktop peer is created.
#ifndef FATHOM_MAIN_OWNER_TEST
#error This fixture requires the explicitly guarded Main owner test target.
#endif
#define main retained_main_owner_shared_audio_fixture_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include "../Source/desktop/Main.cpp"
#include <condition_variable>
#include <iterator>

namespace fathom::desktop {
struct OnboardingIntegrationTestAccess {
    static bool startStoppedFreeplay(HomeView& home) { return home.freeplayView.startFreeplay()&&home.freeplayView.stopFreeplay(); }
    static void tick(HomeView& home) { home.timerCallback(); }
    static bool opening(const HomeView& home) { return home.localProfileOpening_; }
    static bool setupBound(const HomeView& home) { return home.setupPreferences_.hasProfile(); }
    static bool presentationBound(const HomeView& home) { return home.presentation_.hasProfile(); }
    static bool setupReading(const HomeView& home) { return home.setupPreferences_.inFlight(); }
    static bool presentationReading(const HomeView& home) { return home.presentation_.inFlight(); }
    static void heldDiagnostics(const HomeView& h){
        const auto revision=[](const auto& p){return p.observedRevision().value_or(-1);};
        std::cout<<"QUIT_HELD_DIAGNOSTIC gate="<<h.presentationStoppedAndResolved()<<" page="<<static_cast<int>(h.page_)
          <<" restoreHeld="<<h.setupOwnerRestoreHeld_<<" restorePending="<<h.setupRestorePending_<<" opening="<<h.localProfileOpening_
          <<" learnQueue="<<bool(h.learnQueue_)<<" learnFuture="<<bool(h.learnFuture_)<<" learnMutation="<<static_cast<int>(h.learnMutation_)
          <<" progressBusy="<<h.progressView.busy()<<" freeplayResolved="<<h.freeplayView.presentationStoppedAndResolved()
          <<" guidedResolved="<<h.guidedView.presentationStoppedAndResolved()<<" practiceReleased="<<h.practiceView->audioCanRelease()
          <<" metronomeReleased="<<h.metronomeView.audioCanRelease()<<" referenceReleased="<<h.referenceView.audioCanRelease()
          <<" scheduleReleased="<<h.scheduleView.audioCanRelease()<<" metronomePrefsPending="<<h.metronomeView.preferencesPending()
          <<" manualClock="<<h.manualTaskView.clockActive()<<" manualPulse="<<h.manualTaskView.pulsePreparing()
          <<" setupState="<<static_cast<int>(h.setupPreferences_.state())<<" setupSupported="<<h.setupPreferences_.supported()
          <<" setupCanSaveIfStopped="<<h.setupPreferences_.canSave(true)<<" setupDirty="<<h.setupPreferences_.dirty()<<" setupInFlight="<<h.setupPreferences_.inFlight()<<" setupPending="<<h.setupPreferences_.pending()
          <<" setupRevision="<<revision(h.setupPreferences_)<<" setupSubmitted="<<h.quitSetupSubmitted_
          <<" presentationCanSaveIfStopped="<<h.presentation_.canSave(true)<<" presentationState="<<static_cast<int>(h.presentation_.state())<<" presentationDirty="<<h.presentation_.dirty()
          <<" presentationInFlight="<<h.presentation_.inFlight()<<" presentationPending="<<h.presentation_.pending()
          <<" presentationRevision="<<revision(h.presentation_)<<" presentationSubmitted="<<h.quitPresentationSubmitted_<<"\n"
          <<"QUIT_HELD_SETUP_MESSAGE "<<h.setupPreferences_.statusText()<<"\n"
          <<"QUIT_HELD_PRESENTATION_MESSAGE "<<h.presentation_.statusText()<<"\n";
    }
    static desktop::setup::Model chooseSaveDraft(HomeView& home) {
        auto model=home.setupPreferences_.model();model.appearance=desktop::setup::Appearance::Dark;model.experience=desktop::presentation::Level::Developer;
        home.setupPreferences_.choose(model);home.presentation_.chooseGlobal(model.experience);return model;
    }
};
}

namespace {
using SetupOwnerAccess = desktop::OnboardingIntegrationTestAccess;
int ownerChecks{};
void checkOwner(bool passed, const char* label) {
    ++ownerChecks;
    std::cout << (passed ? "PASS " : "FAIL ") << label << '\n';
    if (!passed) throw std::runtime_error(label);
}

struct OwnerGate {
    std::atomic<bool> armed{false}, entered{false};
    std::mutex mutex;
    std::condition_variable cv;
    bool released{};
    void block() {
        if (!armed.exchange(false)) return;
        std::unique_lock<std::mutex> lock(mutex);
        entered = true;
        cv.notify_all();
        cv.wait(lock, [this] { return released; });
    }
    void await() {
        std::unique_lock<std::mutex> lock(mutex);
        if (!cv.wait_for(lock, std::chrono::seconds(3), [this] { return entered.load(); }))
            throw std::runtime_error("Main owner fixture latch watchdog");
    }
    void release() {
        std::lock_guard<std::mutex> lock(mutex);
        released = true;
        cv.notify_all();
    }
};

struct MainOpenContext {
    OwnerGate worker, reads, close;
    std::atomic<int> opens{}, closeAttempts{};
    std::atomic<bool> failClose{false};
    storage::ProfileStore* originalStore{};
    json::Value baseline;
    std::string profile, session;
    bool actualHelper{};
    desktop::LocalProfileOpen open(const std::filesystem::path& path, const std::string& zone) {
        ++opens;
        worker.block();
        if (actualHelper) return desktop::openLocalProfile(path, zone);
        storage::StoreOptions options;
        options.path = path;
        options.create = true;
        options.createdUtc = desktop::localProfileUtcNow();
        options.preferenceValidator = desktop::presentation::composedPreferenceValidator;
        options.diagnosticHook = [this](const auto& phase, const auto&) {
            if (phase == "before_operation") reads.block();
            if (phase == "before_shutdown_close") {
                ++closeAttempts;
                close.block();
                if (failClose.load()) throw std::runtime_error("Controlled Main fixture close exception before SQLite close");
            }
        };
        desktop::LocalProfileOpen opened;
        opened.path = path;
        opened.created = true;
        opened.timezone = zone;
        opened.store = std::make_unique<storage::ProfileStore>(options);
        auto identity = capture_fixture::confirmed(opened.store->snapshot(storage::newUuid()));
        opened.profileId = identity.data.object().at("profile_id").string();
        auto created = capture_fixture::confirmed(opened.store->createSession(storage::newUuid(),
            desktop::localProfileUtcNow(), zone, {}, json::Value::Object{{"version", "local-practice-session.1"}}));
        opened.sessionId = created.owner;
        baseline = capture_fixture::confirmed(opened.store->snapshot(storage::newUuid()))
            .data.object().at("authoritative");
        originalStore = opened.store.get();
        profile = opened.profileId;
        session = opened.sessionId;
        return opened;
    }
};
struct ReleaseOwnerGates {
    MainOpenContext& context;
    ~ReleaseOwnerGates() { context.worker.release(); context.reads.release(); context.close.release(); }
};

struct MainOwnerTestAccess {
    static Home& prepare(Application& app, const std::filesystem::path& path,
                         MainOpenContext& context, int& exits) {
        app.window = std::make_unique<Window>(false);
        app.window->onCancelQuit = [&app] { app.cancelQuit(); };
        app.window->onQuitChoice = [&app](bool discard) { app.chooseQuit(discard); };
        app.localProfileSelfTestPath = path;
        app.fixtureOpener = [&context](const auto& selected, const auto& zone) {
            return context.open(selected, zone);
        };
        app.fixtureExitReady = [&exits] { ++exits; };
        app.wireLocalProfile();
        app.window->home().beginInitialSetup();
        return app.window->home();
    }
    static void tick(Application& app) {
        app.pollLocalOpening();
        if (app.window) SetupOwnerAccess::tick(app.window->home());
        if (app.quitRequested && app.quitPhase != Application::QuitPhase::Exiting){
            const bool alreadyHeld=app.quitChoicePending;
            app.serviceQuit();
            if(!alreadyHeld&&app.quitChoicePending&&app.window&&app.window->home().closeState()==Home::CloseState::Held){
                std::cout<<"QUIT_DIAGNOSTIC_PHASE first_actual_held_after_serviceQuit\n";
                SetupOwnerAccess::heldDiagnostics(app.window->home());
            }
        }
    }
    static void clickRecovery(Application& app, bool keep) {
        auto& b=keep?app.window->closing.cancel:app.window->closing.discard;
        checkOwner(b.isVisible()&&b.isEnabled(),"Actual recovery button visible/enabled");
        checkOwner(app.window->closing.getLocalBounds().contains(b.getBounds()),"Recovery button contained at minimum bounds");
        b.triggerClick(); const auto end=std::chrono::steady_clock::now()+std::chrono::milliseconds(150); while(std::chrono::steady_clock::now()<end)pump();
    }
    static void raster(Application& app,const std::filesystem::path& root,const char* name) {
        auto image=app.window->createComponentSnapshot(app.window->getLocalBounds());
        juce::FileOutputStream stream(juce::File((root/name).string()));juce::PNGImageFormat png;
        checkOwner(stream.openedOk()&&png.writeImageToStream(image,stream),"Actual component raster saved");
    }
    static double quitElapsedMilliseconds(const Application& app){return std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-app.quitStarted).count();}
    static void commonChoices() {
        for (const bool discard : {false,true}) {
            Application app;int exits=0;app.window=std::make_unique<Window>(false);
            app.fixtureExitReady=[&]{++exits;};
            app.window->onCancelQuit=[&]{app.cancelQuit();};
            app.window->onQuitChoice=[&](bool value){app.chooseQuit(value);};
            app.window->showClosing("Preparing original close",true);
            const auto unchangedWindowBounds=app.window->getBounds();const auto unchangedPanelBounds=app.window->closing.getBounds();
            app.systemRequestedQuit();
            auto usableChoice=[&](const juce::Component& control){return control.isVisible()&&control.getWidth()>0&&control.getHeight()>0&&app.window->closing.getLocalBounds().contains(control.getBounds());};
            checkOwner(app.window->getBounds()==unchangedWindowBounds&&app.window->closing.getBounds()==unchangedPanelBounds&&usableChoice(app.window->closing.save)&&usableChoice(app.window->closing.discard)&&usableChoice(app.window->closing.cancel),"Quit choices have positive contained rectangles without window or panel resizing");
            checkOwner(!app.window->closing.save.getBounds().intersects(app.window->closing.discard.getBounds())&&!app.window->closing.discard.getBounds().intersects(app.window->closing.cancel.getBounds()),"Quit choices occupy separate usable rectangles before native resize");
            checkOwner(app.quitChoicePending&&!app.quitRequested&&exits==0,"Quit presents choice before any owner drain or exit");
            app.systemRequestedQuit();
            checkOwner(app.quitChoicePending&&app.quitPhase==Application::QuitPhase::None&&exits==0,"Repeated Quit retains one pending choice");
            app.window->closing.cancel.onClick();
            checkOwner(!app.quitChoicePending&&!app.quitRequested&&exits==0,"Cancel clears prompt without exit");
            app.window->showDiscardRecovery("Original cleanup remains held");
            checkOwner(app.window->getBounds()==unchangedWindowBounds&&app.window->closing.getBounds()==unchangedPanelBounds&&!app.window->closing.save.isVisible()&&usableChoice(app.window->closing.discard)&&usableChoice(app.window->closing.cancel)&&!app.window->closing.discard.getBounds().intersects(app.window->closing.cancel.getBounds()),"Recovery choices relayout at unchanged bounds with Save hidden");
            app.window->clearClosing();
            app.chooseQuit(discard);
            checkOwner(!app.quitRequested&&exits==0,"Stale choice after Cancel cannot exit");
            app.systemRequestedQuit();
            if(discard)app.window->closing.discard.onClick();else app.window->closing.save.onClick();
            checkOwner(!app.quitChoicePending&&app.quitDiscard==discard,"Save and Discard bind the actual chosen route");
            for(int i=0;i<4&&exits==0;++i)app.serviceQuit();
            checkOwner(exits==1,"Resolved ownerless choice exits normally once");
            app.systemRequestedQuit();app.chooseQuit(!discard);
            checkOwner(exits==1&&app.quitDiscard==discard,"Repeated Quit or changed choice after exit cannot apply twice");
        }
    }
    static void chooseDiscard(Application& app) { app.chooseQuit(true); }
    static void ageQuit(Application& app) { app.quitStarted=std::chrono::steady_clock::now()-std::chrono::seconds(16); }
    static bool discardOnlyPrompt(Application& app) { return app.quitChoicePending&&app.quitDiscardCommitted&&!app.quitRequested&&app.window->closing.discard.isVisible()&&!app.window->closing.save.isVisible()&&app.window->closing.cancel.isVisible()&&app.window->closing.cancel.isEnabled()&&app.window->closing.cancel.getButtonText()=="Keep App Open"; }
    static void chooseSave(Application& app) { app.chooseQuit(false); }
    static bool opening(const Application& app) { return app.localOpening.valid(); }
    static bool openingReady(Application& app) {
        return app.localOpening.valid()
            && app.localOpening.wait_for(std::chrono::milliseconds(0)) == std::future_status::ready;
    }
    static storage::ProfileStore* store(Application& app) { return app.store.get(); }
    static bool recoveryHeld(const Application& app) { return app.localRecoveryHeld; }
    static void cancel(Application& app) { app.cancelQuit(); }
    static void checkpoint(Application& app, std::function<void(const char*)> value) {
        app.fixtureCheckpoint = std::move(value);
    }
    static bool noNativePeer(const Application& app) {
        return app.window && !app.window->getPeer() && !app.window->home().getPeer();
    }
    static bool closingVisible(const Application& app) { return app.window->closing.isVisible(); }
    static bool cancelEnabled(const Application& app) { return app.window->closing.cancel.isEnabled(); }
    static bool waitingForConsumers(const Application& app) {
        return app.quitRequested && app.quitPhase == Application::QuitPhase::Consumers;
    }
    static bool waitingForStore(const Application& app) {
        return app.quitRequested && app.quitPhase == Application::QuitPhase::Store;
    }
    static bool storeErrorHeld(const Application& app) {
        return app.quitRequested && app.quitPhase == Application::QuitPhase::StoreError;
    }
    static bool timerRunning(const Application& app) { return app.isTimerRunning(); }
    static void heldDiagnostics(const Application& app){if(app.window)SetupOwnerAccess::heldDiagnostics(app.window->home());}
    static std::string closeMessage(const Application& app) {
        return app.window->closing.message.getText().toStdString();
    }
};

template<class Predicate>
void waitOwner(Application& app, Predicate predicate) {
    const auto end = std::chrono::steady_clock::now() + std::chrono::seconds(8);
    while (!predicate()) {
        MainOwnerTestAccess::tick(app);
        pump();
        if (std::chrono::steady_clock::now() >= end){
            std::cout<<"QUIT_DIAGNOSTIC_PHASE watchdog_after_original_read_release\n";MainOwnerTestAccess::heldDiagnostics(app);
            throw std::runtime_error("Actual Main owner eight-second watchdog");
        }
    }
}
template<class Predicate>
void waitWorker(Predicate predicate) {
    const auto end = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (!predicate()) {
        // Keep the message thread at this deliberate pre-publication boundary:
        // pumping its delayed Main poll here could consume the original future
        // before this fixture arms the first accepted-reader latch.
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
        if (std::chrono::steady_clock::now() >= end)
            throw std::runtime_error("Original opening worker five-second watchdog");
    }
}
void closeOwner(Application& app, int& exits, bool discard = false) {
    app.systemRequestedQuit();
    if(discard) MainOwnerTestAccess::chooseDiscard(app); else MainOwnerTestAccess::chooseSave(app);
    waitOwner(app, [&] { return exits == 1; });
    auto* store = MainOwnerTestAccess::store(app);
    checkOwner(!store || store->shutdownComplete(), "Exit readiness follows actual writer close publication");
    checkOwner(MainOwnerTestAccess::noNativePeer(app), "Actual Main coordination creates no native window peer");
    // Main's existing delayed polls capture this. Drain their no-op callbacks
    // while the same Application is alive, before fixture destruction.
    const auto until = std::chrono::steady_clock::now() + std::chrono::milliseconds(125);
    while (std::chrono::steady_clock::now() < until) pump();
    checkOwner(exits == 1, "Delayed and repeated close polls cannot request a second exit");
    app.shutdown();
}
json::Value reopenAuthority(const std::filesystem::path& path) {
    storage::StoreOptions options;
    options.path = path;
    options.preferenceValidator = desktop::presentation::composedPreferenceValidator;
    storage::ProfileStore reopened(options);
    return capture_fixture::confirmed(reopened.snapshot(storage::newUuid()))
        .data.object().at("authoritative");
}
void unchangedAuthority(const std::filesystem::path& path, const MainOpenContext& context) {
    const auto actual = reopenAuthority(path);
    checkOwner(actual.object().size() == 14 && actual == context.baseline,
        "All fourteen authoritative tables retain the original opening baseline, including preferences");
    checkOwner(actual.object().at("session").array().size() == 1
        && actual.object().at("session").array()[0].array()[0].string() == context.session
        && actual.object().at("session_close").array().empty()
        && actual.object().at("pending").array().empty()
        && actual.object().at("finalized").array().empty()
        && actual.object().at("source_attestation").array().empty()
        && actual.object().at("rule_observation").array().empty(),
        "Opening failure and normal cleanup retain one original Session without fabricated closes or credit");
}
void privateCase(const std::filesystem::path& path) {
    std::filesystem::create_directories(path.parent_path());
    std::filesystem::permissions(path.parent_path(), std::filesystem::perms::owner_all);
}
void chooseRetainedDraft(Home& home) {
    auto model = home.setupModel();
    model.appearance = desktop::setup::Appearance::Dark;
    model.experience = desktop::presentation::Level::Developer;
    model.guitar.capo = 3;
    model.audio.master = 43;
    home.resumeInitialSetup(model);
}
void genuinePreferenceSaveCase(const std::filesystem::path& root) {
    const auto path=root/"genuine-preference-save"/"profile.sqlite";privateCase(path);
    MainOpenContext context;int exits{};Application app;ReleaseOwnerGates release{context};
    auto& home=MainOwnerTestAccess::prepare(app,path,context,exits);
    checkOwner(home.onOpenLocalProfile(),"Genuine Save opens one actual original Store");
    waitWorker([&]{return MainOwnerTestAccess::openingReady(app);});
    context.reads.armed=true;MainOwnerTestAccess::tick(app);context.reads.await();
    checkOwner(SetupOwnerAccess::setupReading(home)||SetupOwnerAccess::presentationReading(home),"Genuine Save owns an actual blocked preference read");
    const auto draft=SetupOwnerAccess::chooseSaveDraft(home);
    const auto setupBytes=storage::canonical(desktop::setup::encodePreferences(draft));
    const auto presentationBytes=storage::canonical(desktop::presentation::encodePreferences(draft.experience));
    app.systemRequestedQuit();MainOwnerTestAccess::chooseSave(app);MainOwnerTestAccess::tick(app);
    checkOwner(home.closeState()==H::CloseState::Waiting&&exits==0&&MainOwnerTestAccess::store(app)==context.originalStore,"Save waits for actual accepted readers without a false unconfirmed-save failure");
    std::cout<<"QUIT_DIAGNOSTIC_PHASE before_original_read_release\n";MainOwnerTestAccess::heldDiagnostics(app);
    context.reads.release();closeOwner(app,exits);
    const auto actual=reopenAuthority(path);
    auto preserved=actual;auto baseline=context.baseline;preserved.object().erase("preferences");baseline.object().erase("preferences");
    checkOwner(actual.object().size()==14&&preserved==baseline,"Genuine preference Save preserves all other thirteen authorities including metadata including original Session and no activity/close facts");
    storage::StoreOptions options;options.path=path;options.preferenceValidator=desktop::presentation::composedPreferenceValidator;storage::ProfileStore reopened(options);
    for(const auto& entry:{std::pair<std::string,std::string>{desktop::setup::preferenceKey,setupBytes},{desktop::presentation::preferenceKey,presentationBytes}}){
        const auto result=capture_fixture::confirmed(reopened.readPreferences(storage::newUuid(),entry.first));std::int64_t version{},revision{};
        checkOwner(result.owner==entry.first&&result.data.object().at("namespace_version").integer(version)&&version==1&&result.data.object().at("revision").integer(revision)&&revision==1&&result.data.object().at("bytes").string()==entry.second,"Genuine Save retains each exact preference namespace/bytes once at revision one");
    }
    checkOwner(actual.object().at("preferences").array().size()==2&&nativeOpens==0&&connections==0,"Genuine Save creates exactly two preference facts without output/device activity");
}

void storeErrorCase(const std::filesystem::path& root) {
    const auto path = root / "injected-close-error" / "profile.sqlite";
    privateCase(path);
    MainOpenContext context;
    context.failClose = true;
    context.close.armed = true;
    int exits{};
    Application app;
    ReleaseOwnerGates release{context};
    auto& home = MainOwnerTestAccess::prepare(app, path, context, exits);
    chooseRetainedDraft(home);
    const auto draft = home.setupModel();
    auto* originalHome = &home;
    checkOwner(home.onOpenLocalProfile(), "StoreError fixture opens one actual detached Main owner");
    waitOwner(app, [&] { return !MainOwnerTestAccess::opening(app); });
    waitOwner(app, [&] { return home.requestClose(); });
    auto* store = MainOwnerTestAccess::store(app);
    checkOwner(store == context.originalStore && context.opens == 1
        && SetupOwnerAccess::setupBound(home) && SetupOwnerAccess::presentationBound(home)
        && home.setupModel() == draft && home.audioSettings().snapshot().state == output::State::Closed,
        "Original consumer attachment settles with exact retained draft and closed audio");
    const auto originalAuthority = context.baseline;
    const auto bytes = storage::canonical(desktop::setup::encodePreferences(draft));
    context.reads.armed = true;
    auto write = store->compareExchangePreferences("main/store-error/accepted-draft", desktop::setup::preferenceKey,
        1, 0, bytes, true);
    context.reads.await();
    auto read = store->readPreferences("main/store-error/accepted-exact-read", desktop::setup::preferenceKey);
    auto snapshot = store->snapshot("main/store-error/accepted-post-write-snapshot");
    app.systemRequestedQuit(); MainOwnerTestAccess::chooseDiscard(app);
    checkOwner(MainOwnerTestAccess::waitingForStore(app) && MainOwnerTestAccess::timerRunning(app)
        && exits == 0 && !store->shutdownComplete() && store->shutdownError().empty()
        && write.wait_for(std::chrono::milliseconds(0)) != std::future_status::ready,
        "Main begins nonblocking Store drain while the original accepted write stays gated");
    const auto refused = store->snapshot("main/store-error/forbidden-fresh-read").get();
    checkOwner(refused.status == storage::Status::Busy && refused.code == "QUEUE_REFUSED"
        && refused.operation == "main/store-error/forbidden-fresh-read",
        "Closing Store refuses new work without substituting for the original accepted jobs");
    app.systemRequestedQuit(); MainOwnerTestAccess::chooseDiscard(app);
    checkOwner(MainOwnerTestAccess::waitingForStore(app) && context.closeAttempts == 0
        && exits == 0 && MainOwnerTestAccess::store(app) == store,
        "Repeated Quit neither cancels the accepted write nor bypasses the writer drain");
    context.reads.release();
    checkOwner(write.wait_for(std::chrono::seconds(3)) == std::future_status::ready
        && read.wait_for(std::chrono::seconds(3)) == std::future_status::ready
        && snapshot.wait_for(std::chrono::seconds(3)) == std::future_status::ready,
        "Every accepted write and queued verification settles before the close barrier");
    const auto written = write.get();
    const auto inspected = read.get();
    const auto acceptedSnapshot = snapshot.get();
    std::int64_t writtenRevision{}, inspectedRevision{}, inspectedVersion{};
    checkOwner(written.status == storage::Status::Confirmed
        && written.operation == "main/store-error/accepted-draft"
        && written.data.object().at("revision").integer(writtenRevision) && writtenRevision == 1
        && inspected.status == storage::Status::Confirmed
        && inspected.operation == "main/store-error/accepted-exact-read"
        && inspected.data.object().at("revision").integer(inspectedRevision) && inspectedRevision == 1
        && inspected.data.object().at("namespace_version").integer(inspectedVersion) && inspectedVersion == 1
        && inspected.data.object().at("bytes").string() == bytes,
        "Original accepted CAS commits its exact namespace/version/bytes once before the injected close exception");
    checkOwner(acceptedSnapshot.status == storage::Status::Confirmed
        && acceptedSnapshot.operation == "main/store-error/accepted-post-write-snapshot",
        "Original queued snapshot confirms the exact authority boundary before close");
    context.baseline = acceptedSnapshot.data.object().at("authoritative");
    auto unchanged = context.baseline;
    auto originalWithoutPreferences = originalAuthority;
    unchanged.object().erase("preferences");
    originalWithoutPreferences.object().erase("preferences");
    checkOwner(context.baseline.object().size() == 14 && unchanged == originalWithoutPreferences
        && context.baseline.object().at("preferences").array().size() == 1,
        "Accepted configuration changes only its preference row and preserves the other thirteen authoritative tables");
    context.close.await();
    checkOwner(context.closeAttempts == 1 && !store->shutdownComplete() && store->shutdownError().empty()
        && MainOwnerTestAccess::waitingForStore(app) && exits == 0,
        "Actual writer reaches close only after accepted work drains and cannot publish completion while close is gated");
    context.close.release();
    waitOwner(app, [&] { return MainOwnerTestAccess::storeErrorHeld(app); });
    const std::string error = "Controlled Main fixture close exception before SQLite close";
    const auto message = MainOwnerTestAccess::closeMessage(app);
    checkOwner(!store->shutdownComplete() && store->shutdownError() == error && context.closeAttempts == 1,
        "Injected before-close exception reaches actual StoreError without a false SQLite-close success");
    checkOwner(MainOwnerTestAccess::store(app) == store && &home == originalHome && exits == 0
        && !MainOwnerTestAccess::timerRunning(app) && !home.isEnabled()
        && MainOwnerTestAccess::closingVisible(app) && !MainOwnerTestAccess::cancelEnabled(app)
        && message.find("Profile close failed; accepted results remain retained.") != std::string::npos
        && message.find(error) != std::string::npos,
        "Main holds the original failed Store with truthful error, stopped polling and disabled activity/Cancel");
    storage::StoreOptions duplicateOptions;
    duplicateOptions.path = path;
    duplicateOptions.preferenceValidator = desktop::presentation::composedPreferenceValidator;
    bool excluded{};
    try { storage::ProfileStore duplicate(duplicateOptions); }
    catch (const std::exception&) { excluded = true; }
    checkOwner(excluded, "StoreError retains the actual profile lease against a replacement owner");
    const auto afterError = store->snapshot("main/store-error/forbidden-after-error-read").get();
    checkOwner(afterError.status == storage::Status::Busy && afterError.code == "QUEUE_REFUSED"
        && afterError.operation == "main/store-error/forbidden-after-error-read",
        "Failed-close Store refuses later work while preserving its exact failure");
    for (int repeat = 0; repeat < 3; ++repeat) {
        app.systemRequestedQuit(); MainOwnerTestAccess::chooseDiscard(app);
        MainOwnerTestAccess::cancel(app);
    }
    // Drain already scheduled no-op opening callbacks with the same owner alive.
    // Do not invoke the private service method after its actual timer is stopped.
    const auto until = std::chrono::steady_clock::now() + std::chrono::milliseconds(125);
    while (std::chrono::steady_clock::now() < until) pump();
    checkOwner(MainOwnerTestAccess::storeErrorHeld(app) && MainOwnerTestAccess::store(app) == store
        && !MainOwnerTestAccess::timerRunning(app) && !home.isEnabled()
        && !MainOwnerTestAccess::cancelEnabled(app) && MainOwnerTestAccess::closeMessage(app) == message
        && !store->shutdownComplete() && store->shutdownError() == error
        && context.closeAttempts == 1 && exits == 0 && context.opens == 1,
        "Repeated Quit/Cancel and delayed callbacks cannot retry close, replace ownership or request exit from StoreError");
    checkOwner(MainOwnerTestAccess::noNativePeer(app) && nativeOpens == 0 && connections == 0,
        "StoreError proof remains detached with no native window peer or device connection");
    capture_fixture::write(root / "held-state.json", storage::canonical(json::Value::Object{
        {"actual_main_store_error", true}, {"shutdown_complete", false}, {"shutdown_error", error},
        {"exit_requests", json::Value::fromInteger(exits)}, {"close_attempts", json::Value::fromInteger(context.closeAttempts.load())},
        {"profile_id", context.profile}, {"original_session_id", context.session},
        {"injection", "Existing diagnostic hook before native SQLite close; not an actual SQLite fault"},
        {"cleanup", "Private fixture defensive destruction after hold proof; not production recovery or successful Quit"}}));
    // This private, fully drained fixture uses the existing defensive destructor
    // only after proving the production owner remains held. It does not publish
    // shutdownComplete, retry the close hook, release debt, or signal an App exit.
    std::cout << "STORE_ERROR_DEFENSIVE_FIXTURE_TEARDOWN_NOT_SUCCESSFUL_QUIT\n";
    app.shutdown();
    checkOwner(exits == 0 && !MainOwnerTestAccess::store(app) && context.closeAttempts == 1,
        "Defensive private fixture destruction releases resources without claiming an exit or retrying the failed close");
    const auto reopened = reopenAuthority(path);
    checkOwner(reopened.object().size() == 14 && reopened == context.baseline,
        "After defensive fixture destruction all fourteen tables exactly retain the accepted pre-close snapshot");
    const auto& preferenceRows = reopened.object().at("preferences").array();
    std::int64_t storedVersion{}, storedRevision{};
    checkOwner(preferenceRows.size() == 1 && preferenceRows[0].array().size() == 4
        && preferenceRows[0].array()[0].string() == desktop::setup::preferenceKey
        && preferenceRows[0].array()[1].integer(storedVersion) && storedVersion == 1
        && preferenceRows[0].array()[2].integer(storedRevision) && storedRevision == 1,
        "Exact original accepted preference survives close failure at revision one without duplicate commit");
    checkOwner(reopened.object().at("session").array().size() == 1
        && reopened.object().at("session").array()[0].array()[0].string() == context.session
        && reopened.object().at("session_close").array().empty()
        && reopened.object().at("pending").array().empty()
        && reopened.object().at("finalized").array().empty()
        && reopened.object().at("source_attestation").array().empty()
        && reopened.object().at("rule_observation").array().empty(),
        "Close-error handling and private cleanup fabricate no Session close, Attempt or learner credit");
}
}

void discardTimeoutCase(const std::filesystem::path& root){
 const auto path=root/"discard-timeout"/"profile.sqlite";privateCase(path);MainOpenContext context;int exits{};Application app;ReleaseOwnerGates release{context};auto& home=MainOwnerTestAccess::prepare(app,path,context,exits);
 chooseRetainedDraft(home);checkOwner(home.onOpenLocalProfile(),"Actual isolated profile opens");waitOwner(app,[&]{return !MainOwnerTestAccess::opening(app);});waitOwner(app,[&]{return home.requestClose();});
 checkOwner(MainOwnerTestAccess::noNativePeer(app)&&home.audioSettings().snapshot().state==output::State::Closed,"No native peer and output Closed");capture_fixture::write(root/"baseline-authority.json",storage::canonical(context.baseline));context.reads.armed=true;checkOwner(SetupOwnerAccess::startStoppedFreeplay(home),"Actual Freeplay Stop admits original persistence job without audio");context.reads.await();auto* store=MainOwnerTestAccess::store(app);
 app.systemRequestedQuit();MainOwnerTestAccess::clickRecovery(app,false);checkOwner(MainOwnerTestAccess::waitingForConsumers(app)&&exits==0,"Actual Discard callback retains blocked consumer");
 const auto start=std::chrono::steady_clock::now();
 while(!MainOwnerTestAccess::discardOnlyPrompt(app)&&std::chrono::steady_clock::now()-start<std::chrono::seconds(20)){MainOwnerTestAccess::tick(app);pump();}
 const auto elapsed=MainOwnerTestAccess::quitElapsedMilliseconds(app);
 checkOwner(elapsed>=15000&&MainOwnerTestAccess::discardOnlyPrompt(app)&&MainOwnerTestAccess::store(app)==store&&exits==0,"Real fifteen-second timeout holds original Store with recovery-only controls");
 MainOwnerTestAccess::raster(app,root,"held.png");
 MainOwnerTestAccess::clickRecovery(app,true);checkOwner(!MainOwnerTestAccess::waitingForConsumers(app)&&!MainOwnerTestAccess::choicePending(app)&&MainOwnerTestAccess::store(app)==store&&exits==0&&context.opens==1,"Actual Keep App Open cancels only quit intent; same accepted owner retained");
 app.systemRequestedQuit();checkOwner(MainOwnerTestAccess::discardOnlyPrompt(app)&&MainOwnerTestAccess::store(app)==store&&context.opens==1,"New Quit exposes only Continue, never restores discarded changes");MainOwnerTestAccess::raster(app,root,"continued-choice.png");
 MainOwnerTestAccess::clickRecovery(app,false);checkOwner(MainOwnerTestAccess::waitingForConsumers(app)&&exits==0&&MainOwnerTestAccess::store(app)==store,"Actual Continue callback retries original ownership barrier");context.reads.release();waitOwner(app,[&]{return exits==1;});checkOwner(context.opens==1&&context.closeAttempts==1,"Original Store drains and closes once");app.shutdown();
 const auto reopened=reopenAuthority(path);capture_fixture::write(root/"reopened-authority.json",storage::canonical(reopened));
 checkOwner(reopened.object().at("session")==context.baseline.object().at("session")&&reopened.object().at("session_close")==context.baseline.object().at("session_close"),"No new Session or Session close from stopped Freeplay");
 checkOwner(reopened.object().at("identity").array().size()==context.baseline.object().at("identity").array().size()+1&&reopened.object().at("finalized")==context.baseline.object().at("finalized")&&reopened.object().at("pending").array().empty(),"Exactly one retained Freeplay identity, no finalized result or pending work");checkOwner(reopened.object().at("identity").array().back().array()[1].string()=="FreeplayActivity","Retained identity is Freeplay, never PracticeAttempt");checkOwner(reopened.object().at("source_attestation")==context.baseline.object().at("source_attestation")&&reopened.object().at("rule_observation")==context.baseline.object().at("rule_observation"),"No new source or progression credit");capture_fixture::write(root/"equivalence.json",storage::canonical(json::Value::Object{{"elapsed_ms_string",std::to_string(elapsed)},{"opens",json::Value::fromInteger(context.opens.load())},{"close_attempts",json::Value::fromInteger(context.closeAttempts.load())},{"exits",json::Value::fromInteger(exits)},{"native_peer",false},{"real_timeout",true},{"actual_button_callbacks",true},{"scope","Actual Main/Home/Store component workflow, not native Q16 input"}}));
}

int main(int argc, char** argv) {
    try {
        const bool discardTimeoutOnly=argc==3&&std::string(argv[2])=="--discard-timeout-regression";
        if(discardTimeoutOnly)argc=2;
        const bool commonChoiceOnly=argc==3&&std::string(argv[2])=="--common-quit-choice-regression";
        if(commonChoiceOnly)argc=2;
        const bool storeErrorOnly = argc == 3 && std::string(argv[2]) == "--store-error-regression";
        if (storeErrorOnly) argc = 2;
        if (argc != 2 || !std::filesystem::path(argv[1]).is_absolute()
            || std::filesystem::exists(argv[1]))
            throw std::runtime_error("Fresh absolute owned evidence root required");
        const std::filesystem::path root(argv[1]);
        std::filesystem::create_directories(root);
        std::filesystem::permissions(root, std::filesystem::perms::owner_all);
        juce::ScopedJuceInitialiser_GUI gui;
        if(discardTimeoutOnly) discardTimeoutCase(root);
        else if(commonChoiceOnly) MainOwnerTestAccess::commonChoices();
        else if (storeErrorOnly) storeErrorCase(root);
        else {
        genuinePreferenceSaveCase(root);
        for (const bool cancelBeforeException : {false, true}) {
            const auto path = root / (cancelBeforeException ? "worker-exception-cancel" : "worker-exception-quit") / "profile.sqlite";
            privateCase(path);
            const std::string original = "Controlled unsupported profile; must not be replaced.\n";
            capture_fixture::write(path, original);
            std::filesystem::permissions(path, std::filesystem::perms::owner_read | std::filesystem::perms::owner_write);
            MainOpenContext context;
            context.actualHelper = true;
            context.worker.armed = true;
            int exits{};
            Application app;
            ReleaseOwnerGates release{context};
            auto& home = MainOwnerTestAccess::prepare(app, path, context, exits);
            chooseRetainedDraft(home);
            const auto draft = home.setupModel();
            checkOwner(home.onOpenLocalProfile(), "Explicit Main action returns while the original opening worker is gated");
            context.worker.await();
            checkOwner(MainOwnerTestAccess::opening(app) && SetupOwnerAccess::opening(home) && !home.isEnabled(),
                "Pending original future owns the opening UI and prevents activity");
            checkOwner(!home.onOpenLocalProfile() && context.opens == 1 && MainOwnerTestAccess::opening(app),
                "Repeated open refuses without replacing the original worker");
            app.systemRequestedQuit(); MainOwnerTestAccess::chooseSave(app);
            checkOwner(exits == 0 && MainOwnerTestAccess::closingVisible(app) && MainOwnerTestAccess::cancelEnabled(app),
                "Quit waits for the original opening future instead of destroying it");
            if (cancelBeforeException) {
                MainOwnerTestAccess::cancel(app);
                checkOwner(MainOwnerTestAccess::opening(app) && !home.isEnabled(),
                    "Cancel Quit retains the opening future and keeps activity disabled");
            }
            context.worker.release();
            waitOwner(app, [&] { return !MainOwnerTestAccess::opening(app); });
            checkOwner(!MainOwnerTestAccess::store(app) && !MainOwnerTestAccess::recoveryHeld(app)
                && !SetupOwnerAccess::opening(home) && home.setupModel() == draft,
                "Worker exception before adoption retains every session draft choice without a Store owner");
            if (cancelBeforeException)
                checkOwner(home.isEnabled() && exits == 0,
                    "Cancelled Quit plus worker exception restores actionable Home without an exit request");
            else
                checkOwner(!home.isEnabled() && MainOwnerTestAccess::closingVisible(app),
                    "Original pending Quit remains on the normal close path after the worker exception");
            std::ifstream input(path, std::ios::binary);
            checkOwner(std::string(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()) == original,
                "Actual opening helper leaves the unsupported original profile bytes unchanged");
            closeOwner(app, exits);
        }
        for (const bool cancelBeforeCompletion : {false, true}) {
            const auto path = root / (cancelBeforeCompletion ? "cancel-then-success" : "quit-before-attach") / "profile.sqlite";
            privateCase(path);
            MainOpenContext context;
            context.worker.armed = true;
            int exits{}, attached{};
            Application app;
            ReleaseOwnerGates release{context};
            auto& home = MainOwnerTestAccess::prepare(app, path, context, exits);
            chooseRetainedDraft(home);
            const auto draft = home.setupModel();
            MainOwnerTestAccess::checkpoint(app, [&](const char*) { ++attached; });
            checkOwner(home.onOpenLocalProfile(), "Main starts exactly one controlled actual-Store opening worker");
            context.worker.await();
            app.systemRequestedQuit(); MainOwnerTestAccess::chooseSave(app);
            app.systemRequestedQuit(); MainOwnerTestAccess::chooseSave(app);
            checkOwner(context.opens == 1 && exits == 0 && !home.isEnabled(),
                "Repeated Quit retains the gated original opening identity without a second worker");
            if (cancelBeforeCompletion) MainOwnerTestAccess::cancel(app);
            context.worker.release();
            waitOwner(app, [&] { return !MainOwnerTestAccess::opening(app); });
            checkOwner(MainOwnerTestAccess::store(app) == context.originalStore,
                "Ready future publishes the exact original Store owner once");
            if (cancelBeforeCompletion) {
                waitOwner(app, [&] { return !SetupOwnerAccess::setupReading(home)
                    && !SetupOwnerAccess::presentationReading(home); });
                checkOwner(attached == 2 && home.isEnabled() && SetupOwnerAccess::setupBound(home)
                    && SetupOwnerAccess::presentationBound(home) && !MainOwnerTestAccess::recoveryHeld(app),
                    "Cancelled Quit allows original worker completion to attach the actual consumers and preferences");
                checkOwner(home.setupModel() == draft
                    && home.presentationModel().globalLevel() == draft.experience
                    && home.audioSettings().snapshot().state == output::State::Closed,
                    "Completed attachment preserves explicit unbound draft and canonical experience choice without audio");
            } else {
                checkOwner(attached == 0 && !SetupOwnerAccess::setupBound(home)
                    && !SetupOwnerAccess::presentationBound(home),
                    "Quit before ready publication adopts the Store for drain but queues no consumer attachment");
            }
            // This fixture retains an explicitly unsaved draft and asserts no preference writes.
            closeOwner(app, exits, cancelBeforeCompletion);
            unchangedAuthority(path, context);
        }
        for (const auto* phaseName : {"after_configure", "after_presentation"}) {
            const std::string point(phaseName);
            const auto path = root / point / "profile.sqlite";
            privateCase(path);
            MainOpenContext context;
            int exits{};
            Application app;
            ReleaseOwnerGates release{context};
            auto& home = MainOwnerTestAccess::prepare(app, path, context, exits);
            chooseRetainedDraft(home);
            const auto draft = home.setupModel();
            auto* originalHome = &home;
            MainOwnerTestAccess::checkpoint(app, [&](const char* phase) {
                if (point == phase) throw std::runtime_error("Controlled partial attachment at " + point);
            });
            checkOwner(home.onOpenLocalProfile(), "Partial attachment case begins one actual Main opening operation");
            waitWorker([&] { return MainOwnerTestAccess::openingReady(app); });
            context.reads.armed = true;
            MainOwnerTestAccess::tick(app);
            context.reads.await();
            checkOwner(MainOwnerTestAccess::store(app) == context.originalStore && &home == originalHome
                && MainOwnerTestAccess::recoveryHeld(app) && !home.isEnabled(),
                "Partial attachment retains the original Home, Store lease and accepted reader owners in place");
            checkOwner(home.setupModel() == draft && home.audioSettings().selected().master == draft.audio.master
                && home.audioSettings().snapshot().state == output::State::Closed,
                "Partial attachment never rolls back guitar, audio, experience or appearance choices");
            if (point == "after_presentation")
                checkOwner(SetupOwnerAccess::setupBound(home) && SetupOwnerAccess::presentationBound(home)
                    && SetupOwnerAccess::setupReading(home) && SetupOwnerAccess::presentationReading(home),
                    "Fault after presentation keeps both exact accepted preference reads queued");
            else
                checkOwner(!SetupOwnerAccess::setupBound(home) && !SetupOwnerAccess::presentationBound(home),
                    "Fault after configure preserves consumer ownership before any setup/presentation attachment");
            checkOwner(!home.onOpenLocalProfile() && context.opens == 1
                && MainOwnerTestAccess::store(app) == context.originalStore,
                "Recovery cannot silently create a replacement worker, Store or Session");
            app.systemRequestedQuit(); MainOwnerTestAccess::chooseSave(app);
            checkOwner(exits == 0 && MainOwnerTestAccess::store(app) == context.originalStore
                && MainOwnerTestAccess::waitingForConsumers(app)
                && home.closeState() == H::CloseState::Waiting && MainOwnerTestAccess::cancelEnabled(app),
                "Normal Quit waits for accepted partial-attachment reads before Store shutdown");
            MainOwnerTestAccess::cancel(app);
            checkOwner(!home.isEnabled() && MainOwnerTestAccess::recoveryHeld(app),
                "Cancel Quit never re-enables activity against partial profile recovery");
            app.systemRequestedQuit(); MainOwnerTestAccess::chooseDiscard(app);
            context.reads.release();
            // Discard drains accepted readers while retaining the unsaved recovery draft.
            closeOwner(app, exits, true);
            unchangedAuthority(path, context);
        }
        }
        checkOwner(nativeOpens == 0 && connections == 0,
            "Actual Main failure paths open no physical or synthetic device and start no audio");
        capture_fixture::write(root / "summary.json", storage::canonical(json::Value::Object{
            {"checks", json::Value::fromInteger(ownerChecks)}, {"failures", json::Value::fromInteger(0)},
            {"scope", storeErrorOnly ? "Actual Main StoreError hold from injected before-close exception; defensive fixture teardown is not successful Quit; no native GUI or acceptance"
                : "Actual Main owner with detached Window, real Store and gated worker/fault seams; no native GUI or acceptance"}}));
        std::cout << "MAIN_OWNER_FAILURE_PASS checks=" << ownerChecks << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "MAIN_OWNER_FAILURE_FAIL " << error.what() << '\n';
        return 1;
    }
}
