// Native GUI audit capability, built ONLY by fathom_ui_audit_fixture.
// The actual desktop/store paths are used; device-open leaves and explicitly
// labeled failure receipts are synthetic. Nothing is injected into Fathom/Main.
#if !defined(FATHOM_UI_AUDIT_FIXTURE) || !defined(FATHOM_SOFTWARE_SETTINGS_IO)
#error This translation unit requires the separate software-only fixture target.
#endif
#include "ui_audit_audio_adapter.inc" // Build-owned, pinned fail-closed adapter.
#include "desktop/HomeView.hpp"
#include "ui_audit_fixture_faults.hpp"
#include <juce_cryptography/juce_cryptography.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <thread>
#include <unistd.h>

namespace fixture {
using namespace fathom;
using Fault = ui_fixture::Fault;
using Home = desktop::HomeView;
std::atomic<unsigned> forbiddenDeviceCalls{};
unsigned forbiddenCalls() noexcept {
    return forbiddenDeviceCalls.load()+platform::uiAuditForbiddenNativeConnectCalls.load();
}
ui_fixture::Faults* faults{}; // Lifetime is the JUCEApplication, longer than Home.
platform::OutputCapability capability() {
    return {true,87,44100,256,2,32,2048,"synthetic:ui-audit", "Silent software fixture; no OS device", "", {{44100,44100}}};
}
struct SoftwareDevice final : juce::AudioIODevice {
    SoftwareDevice() : AudioIODevice("Silent software fixture", "ui-audit-test-only") {}
    juce::StringArray getOutputChannelNames() override { return {"L","R"}; }
    juce::StringArray getInputChannelNames() override { return {}; }
    juce::Array<double> getAvailableSampleRates() override { return {44100}; }
    juce::Array<int> getAvailableBufferSizes() override { return {256}; }
    int getDefaultBufferSize() override { return 256; }
    juce::String open(const juce::BigInteger&, const juce::BigInteger&, double, int) override {
        ++forbiddenDeviceCalls; return "UI fixture refuses device open; no physical device exists";
    }
    void close() override {}
    bool isOpen() override { return true; }
    void start(juce::AudioIODeviceCallback*) override { ++forbiddenDeviceCalls; }
    void stop() override {}
    bool isPlaying() override { return false; }
    juce::String getLastError() override { return {}; }
    int getCurrentBufferSizeSamples() override { return 256; }
    double getCurrentSampleRate() override { return 44100; }
    int getCurrentBitDepth() override { return 32; }
    juce::BigInteger getActiveOutputChannels() const override {
        juce::BigInteger result; result.setRange(0,2,true); return result;
    }
    juce::BigInteger getActiveInputChannels() const override { return {}; }
    int getOutputLatencyInSamples() override { return 0; }
    int getInputLatencyInSamples() override { return 0; }
};
void require(bool value, const std::string& why) {
    if (!value) throw std::runtime_error(why);
}
json::Value integer(std::uint64_t value) { return json::Value::fromInteger(static_cast<std::int64_t>(value)); }
void write(const std::filesystem::path& path, const json::Value& value) {
    std::ofstream out(path, std::ios::binary); out << storage::canonical(value) << '\n'; out.close();
    require(bool(out), "Fixture evidence write failed: " + path.string());
}
// A worker may retain this sink after Application shutdown. It owns its stream
// and mutex independently and never dereferences Application or its members.
class EventLog final {
public:
    explicit EventLog(const std::filesystem::path& path) : stream_(path,std::ios::binary) {
        require(bool(stream_),"Fixture event log unavailable");
    }
    void append(const std::string& kind,json::Value detail) {
        std::lock_guard<std::mutex> lock(mutex_);
        stream_<<storage::canonical(json::Value::Object{{"utc",desktop::desktopUtcNow()},
            {"monotonic_ns",integer(platform::monotonicNs())},{"kind",kind},{"detail",std::move(detail)}})<<'\n';
        stream_.flush(); require(bool(stream_),"Fixture event log write failed");
    }
private:
    std::mutex mutex_; std::ofstream stream_;
};
json::Value verifyResources(const std::filesystem::path& resources,const std::string& expectedPin) {
    require(expectedPin.size()==64 && std::all_of(expectedPin.begin(),expectedPin.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}),"Explicit lowercase SHA256 resource pin required");
    const auto bytes=content::readBounded(resources/"ui-audit-resource-pin.json",16U*1024U*1024U);
    require(content::sha256(bytes)==expectedPin,"Selected resource manifest pin changed");
    const auto pin=json::parse(bytes);
    require(pin.object().at("version").string()=="fathom-ui-audit-resources-v1","Unsupported fixture resource manifest");
    const auto& files=pin.object().at("files").array();
    require(!files.empty() && files.size()<=10000,"Fixture resource inventory outside bounds");
    const auto until=platform::monotonicNs()+180000000000ULL;
    std::uint64_t bytesTotal{};
    for(const auto& row:files) {
        const auto relative=std::filesystem::path(row.object().at("path").string());
        require(!relative.empty() && !relative.is_absolute() && relative==relative.lexically_normal(),"Invalid pinned relative resource path");
        for(const auto& component:relative) require(component!="..","Resource path escapes fixture bundle");
        const auto path=resources/relative;
        require(!std::filesystem::is_symlink(path) && std::filesystem::is_regular_file(path),"Pinned fixture resource missing or symlinked");
        const auto size=std::filesystem::file_size(path); bytesTotal+=size;
        require(size<=256ULL*1024ULL*1024ULL && bytesTotal<=2ULL*1024ULL*1024ULL*1024ULL,"Fixture resource bytes outside bounds");
        require(std::to_string(size)==storage::canonical(row.object().at("bytes")),"Pinned fixture resource size changed");
        juce::FileInputStream stream(juce::File(path.string())); require(stream.openedOk(),"Fixture resource cannot be read");
        require(juce::SHA256(stream).toHexString().toStdString()==row.object().at("sha256").string(),"Pinned fixture resource hash changed: "+relative.string());
        require(platform::monotonicNs()<until,"180-second fixture resource integrity watchdog");
    }
    return pin;
}
} // namespace fixture

namespace fathom::platform {
struct OutputTestAccess {
    static bool refuse(AudioOutputMac& output, const std::string& reason) {
        output.p_->lastError=reason; return false;
    }
    static bool attach(AudioOutputMac& output, const OutputCapability& selected, output::Format format,
                       void* context, OutputObserver observer, ScheduledRender render) {
        auto& p=*output.p_;
        if (!selected.valid) return refuse(output, selected.error);
        if (!format.valid() || format.rate!=44100 || format.frames!=256 || !context || !observer || !render)
            return refuse(output, "UI fixture requires its exact software format and owned provider");
        if (p.device || p.life.snapshot().ownsOutcome) return refuse(output, "Resolve the original fixture output first");
        bool free=false;
        if (!hub.claimed.compare_exchange_strong(free,true)) return refuse(output,"Another fixture output owns the software seam");
        output::Observation oldQuery; while(p.queries.pop(oldQuery)) {}
        output::CachedAnnouncement oldAnnouncement; while(p.announcements.pop(oldAnnouncement)) {}
        Control oldControl; while(p.normal.pop(oldControl)) {} while(p.urgent.pop(oldControl)) {}
        p.latestQuery={}; p.firstSilentCallbackNs=0; p.silenceOwner={}; p.lastError.clear(); p.expectedStop=false;
        p.claimed=true; p.epoch=epochCounter.fetch_add(1)+1; p.requested=format;
        // True: service() must never query CoreAudio/listeners. Callbacks below
        // are serialized on the GUI thread and send() consumes commands there.
        p.quiescent=true; p.device=std::make_unique<fixture::SoftwareDevice>();
        p.context=context; p.observer=observer; p.scheduled=render; p.capability=selected;
        nativeSequence=1; hub.epoch=p.epoch; hub.faultWord=tagged(p.epoch,0);
        hub.ioWord=tagged(p.epoch,selected.object); hub.expectedIO=0; hub.armed=false; hub.frames=format.frames;
        const auto stamp=monotonicNs();
        fixture::require(p.life.configure({static_cast<std::uint64_t>(p.epoch),stamp,format,selected.object}) &&
                         p.life.announce({static_cast<std::uint64_t>(p.epoch),stamp+1,format}), "Fixture lifecycle configuration");
        p.latestQuery={static_cast<std::uint64_t>(p.epoch),1,stamp+3,stamp+2,format,format.frames,
                      selected.object,selected.object,selected.object,selected.rate,selected.physicalFrames,
                      true,true,true,true,true};
        p.life.observe(p.latestQuery); p.view.lifecycle=p.life.snapshot(); return true;
    }
    static bool block(AudioOutputMac& output) {
        auto& p=*output.p_; if(!p.device) return false;
        nativeEpoch=p.epoch; nativeObject=p.capability.object; nativeFrames=p.requested.frames; ++nativeSequence;
        std::array<float,256> left{},right{}; float* channels[]{left.data(),right.data()};
        const juce::AudioIODeviceCallbackContext context{};
        p.audioDeviceIOCallbackWithContext(nullptr,0,channels,2,256,context);
        // PCM is deliberately discarded: no sink, physical output or hearing.
        return true;
    }
};
} // namespace fathom::platform

namespace fathom::desktop {
platform::OutputCapability settingsOutputCapability() {
    if (fixture::faults && fixture::faults->take(ui_fixture::Fault::EmptyDevice,"settings-output-capability")) {
        auto result=fixture::capability(); result.valid=false;
        result.error="UI_FIXTURE_empty-device: no software output available; clear fixture and Connect again";
        return result;
    }
    return fixture::capability();
}
bool connectSettingsOutput(platform::AudioOutputMac& output,const platform::OutputCapability& selected,
                           output::Format format,void* context,platform::OutputObserver observer,platform::ScheduledRender render) {
    if (fixture::faults && fixture::faults->take(ui_fixture::Fault::ConnectRefused,"settings-output-connect"))
        return platform::OutputTestAccess::refuse(output,"UI_FIXTURE_connect-refused: controlled synthetic connection failure");
    return platform::OutputTestAccess::attach(output,selected,format,context,observer,render);
}
// Existing friend seams, defined privately for this target. No Source headers
// or the shared regression campaign are modified to add fixture dispatch.
struct SharedAudioViewTestAccess {
    static PracticeView& practice(HomeView& home) { return *home.practiceView; }
    static FreeplayView& freeplay(HomeView& home) { return home.freeplayView; }
    static GuidedSessionView& guided(HomeView& home) { return home.guidedView; }
    static MetronomeView& metronome(HomeView& home) { return home.metronomeView; }
    static platform::AudioOutputMac& output(HomeView& home) {
        switch(home.audio_.active()) {
            case SharedAudioSettings::Consumer::Practice: return home.practiceView->output_;
            case SharedAudioSettings::Consumer::Metronome: return home.metronomeView.output_;
            case SharedAudioSettings::Consumer::Reference: return home.referenceView.output_;
            case SharedAudioSettings::Consumer::Rhythm: return home.scheduleView.output;
            case SharedAudioSettings::Consumer::Count: break;
        }
        throw std::runtime_error("Invalid fixture consumer");
    }
    static void halt(HomeView& home) {
        home.stopTimer(); home.progressView.stopTimer(); home.outputView.stopTimer();
        home.practiceView->stopTimer(); home.metronomeView.stopTimer();
        home.referenceView.stopTimer(); home.scheduleView.stopTimer(); home.freeplayView.stopTimer();
    }
    static void tick(HomeView& home) {
        home.progressView.service(); home.metronomeView.service(); home.referenceView.timerCallback();
        home.scheduleView.timerCallback(); home.practiceView->timerCallback(); home.freeplayView.timerCallback();
        home.guidedView.service(); home.timerCallback(); home.outputView.timerCallback();
    }
};
struct LearnNavigationTestAccess {
    static bool loading(const HomeView& home) { return home.learnLoadTicket_!=nullptr; }
    static bool injectLoad(HomeView& home,const std::filesystem::path& resources,std::shared_ptr<ui_fixture::Faults> faults,
                           ui_fixture::Fault type) {
        if(home.learnLoadTicket_ || home.lessonView.catalog()) return false;
        std::vector<std::filesystem::path> extensions;
        for(const auto& name:lesson::Catalog::installedExtensionDirectoryNames()) extensions.push_back(resources/name);
        return home.beginGuidedLoading(resources,extensions,[faults=std::move(faults),type]{
            if(faults->take(type,"learn-before-catalog")) {
                if(type==ui_fixture::Fault::CorruptLoad) {
                    // Corrupt *returned loader data*, never installed input files.
                    try { storage::parseCanonical("{\"synthetic\":"); }
                    catch(const std::exception&) { throw ui_fixture::Failure(type); }
                }
                throw ui_fixture::Failure(type);
            }
        });
    }
};
struct MetronomeViewTestAccess {
    static bool inspect(MetronomeView& view) { return view.reconcilePreferences(); }
    static bool perturb(MetronomeView& view,ui_fixture::Faults& faults,
                        std::function<void(const storage::Reply&)> observed={}) {
        if(!view.future_ || view.future_->wait_for(std::chrono::milliseconds(0))!=std::future_status::ready) return false;
        const bool writing=view.prefState_==MetronomeView::PrefState::Writing;
        const auto type=writing?ui_fixture::Fault::SettingsSaveFailed:faults.armed();
        if((writing && faults.armed()!=type) || (!writing && type!=ui_fixture::Fault::PreferenceReadFailed && type!=ui_fixture::Fault::CorruptPreferenceReply)) return false;
        const auto operation=view.future_->operationId();
        const auto owner=view.future_->ownerId();
        if(!faults.take(type,operation)) return false;
        // Consume and retain the actual owned reply before substituting a test
        // response with the SAME operation/owner. Committed rows are untouched.
        auto reply=view.future_->get(); view.future_.reset();
        if(observed) observed(reply);
        if(type==ui_fixture::Fault::CorruptPreferenceReply) {
            reply.status=storage::Status::Confirmed;
            reply.data=json::Value::Object{{"revision",json::Value::fromInteger(1)},
                {"namespace_version",json::Value::fromInteger(1)},{"applicable",true},{"bytes","{synthetic malformed preference}"}};
        } else {
            reply.status=storage::Status::DefiniteFailure; reply.code=std::string{"UI_FIXTURE_"}+ui_fixture::name(type);
            reply.message="Controlled returned-receipt failure; inspect actual stored value; no database mutation";
        }
        std::promise<storage::Reply> promise; auto future=promise.get_future(); promise.set_value(std::move(reply));
        view.future_.emplace(std::move(future),operation,owner); return true;
    }
};
} // namespace fathom::desktop

namespace fixture {
using Access=desktop::SharedAudioViewTestAccess;
class Surface final : public juce::Component {
public:
    Surface(Home& home,std::function<void(Fault)> action,std::function<void()> snapshot) : home_(home) {
        addAndMakeVisible(home_); addAndMakeVisible(banner_); addAndMakeVisible(choice_);
        addAndMakeVisible(inject_); addAndMakeVisible(clear_); addAndMakeVisible(snapshot_);
        banner_.setText(juce::String::fromUTF8("SYNTHETIC / SILENT — no guitar performance, hearing or curriculum credit claim"),juce::dontSendNotification);
        banner_.setColour(juce::Label::textColourId,juce::Colours::white);
        int id=1; for(auto fault:{Fault::EmptyDevice,Fault::ConnectRefused,Fault::LoadFailed,Fault::CorruptLoad,
            Fault::PreferenceReadFailed,Fault::CorruptPreferenceReply,Fault::SettingsSaveFailed,Fault::SaveBeforeCommit,Fault::SaveLostReceipt})
            choice_.addItem(ui_fixture::name(fault),id++);
        choice_.setSelectedId(1); choice_.setTitle("Fixture-only typed failure; one owned boundary");
        inject_.onClick=[this,action]{ action(static_cast<Fault>(choice_.getSelectedId())); };
        clear_.onClick=[action]{ action(Fault::None); }; snapshot_.onClick=std::move(snapshot);
        inject_.setTitle("Arm one synthetic boundary failure; never change production admission or storage rows");
    }
    void resized() override {
        banner_.setBounds(10,0,getWidth()-20,24); choice_.setBounds(10,27,250,30);
        inject_.setBounds(270,27,155,30); clear_.setBounds(435,27,115,30); snapshot_.setBounds(560,27,180,30);
        home_.setBounds(0,68,getWidth(),std::max(0,getHeight()-68));
    }
    void paint(juce::Graphics& graphics) override { graphics.fillAll(juce::Colour{0xff4b2039}); }
private:
    Home& home_; juce::Label banner_; juce::ComboBox choice_;
    juce::TextButton inject_{"Arm / inject once"},clear_{"Clear fixture"},snapshot_{"Record owned snapshot"};
};
class Window final : public juce::DocumentWindow {
public:
    explicit Window(Surface& surface) : DocumentWindow(juce::String::fromUTF8("Fathom UI Audit Fixture — SYNTHETIC / SILENT"),juce::Colour{0xff10212c},allButtons) {
        setUsingNativeTitleBar(true); setContentNonOwned(&surface,true); setResizable(true,false);
        // These are the full surface's dimensions. The recorded Home client is
        // exactly 920x680 at minimum after the separate 68-point fixture bar.
        setResizeLimits(920,748,1600,1200); centreWithSize(920,748); setVisible(true);
    }
    void closeButtonPressed() override { juce::JUCEApplication::getInstance()->systemRequestedQuit(); }
};
class Application final : public juce::JUCEApplication, private juce::Timer {
public:
    const juce::String getApplicationName() override { return "Fathom UI Audit Fixture"; }
    const juce::String getApplicationVersion() override { return "1.0.0"; }
    bool moreThanOneInstanceAllowed() override { return false; }
    void anotherInstanceStarted(const juce::String&) override {
        // Never forward a second launch's path/argv into the current owner.
        std::cerr<<"FIXTURE_SECOND_INSTANCE_REFUSED; existing lease unchanged\n";
    }
    void initialise(const juce::String& commandLine) override {
        try {
            const auto args=juce::StringArray::fromTokens(commandLine,true);
            require((args.size()==8 || args.size()==9) && args[0]=="--ui-audit-fixture" && args[4]=="--resource-pin-sha256" && args[6]=="--max-seconds" &&
                    (args.size()!=9 || args[8]=="--self-test"),
                    "Use --ui-audit-fixture <new absolute directory> <IANA timezone> <lease UUID> --resource-pin-sha256 <SHA256> --max-seconds <whole seconds> [--self-test]; GUI: 60..14400; --self-test: 60..900");
            directory_=std::filesystem::path(args[1].unquoted().toStdString()); zone_=args[2].unquoted().toStdString();
            lease_=args[3].unquoted().toStdString(); storage::validateUuid(lease_);
            resourcePin_=args[5].unquoted().toStdString();
            const auto maxText=args[7].toStdString(); std::size_t parsed{}; const auto limit=std::stoul(maxText,&parsed);
            require(parsed==maxText.size() && limit>=60 && limit<=(args.size()==9?900UL:14400UL),
                    args.size()==9?"Capability self-test deadline must be 60..900 whole seconds":"GUI fixture deadline must be 60..14400 whole seconds");
            require(directory_.is_absolute() && directory_==directory_.lexically_normal() && !std::filesystem::exists(directory_),
                    "Fixture refuses existing, relative or non-normalized directories");
            require(directory_.parent_path()==std::filesystem::canonical(directory_.parent_path()),
                    "Fixture parent must already exist and cannot redirect through symlinks");
            storage::localDay(desktop::desktopUtcNow(),zone_);
            const auto application=juce::File::getSpecialLocation(juce::File::currentApplicationFile);
            const auto direct=application.getChildFile("Contents/Resources");
            const auto adjacent=application.getParentDirectory().getParentDirectory().getChildFile("Resources");
            resources_=std::filesystem::path((direct.isDirectory()?direct:adjacent).getFullPathName().toStdString());
            require(std::filesystem::is_regular_file(resources_/"ui-audit-resource-pin.json") &&
                    std::filesystem::is_directory(resources_/"representative-controls") &&
                    std::filesystem::is_directory(resources_/"learn-source-index"),"Root-frozen fixture bundle resources and pin are required; no working-tree fallback");
            const auto resourceInventory=verifyResources(resources_,resourcePin_);
            require(std::filesystem::create_directory(directory_),"Fixture did not create its new directory");
            created_=true; std::filesystem::permissions(directory_,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
            log_=std::make_shared<EventLog>(directory_/"fixture-events.jsonl");
            faults_=std::make_shared<ui_fixture::Faults>([log=log_](Fault type,std::uint64_t generation,const std::string& operation){
                log->append("injected",json::Value::Object{{"type",ui_fixture::name(type)},{"generation",integer(generation)},{"operation",operation}});
            }); fixture::faults=faults_.get();
            storage::StoreOptions options; options.path=directory_/"profile.sqlite"; options.create=true;
            options.createdUtc=desktop::desktopUtcNow(); options.preferenceValidator=desktop::presentation::composedPreferenceValidator;
            options.diagnosticHook=[controller=faults_](const std::string& phase,const std::string& operation){controller->hook(phase,operation);};
            store_=std::make_unique<storage::ProfileStore>(options);
            const auto session=store_->createSession(storage::newUuid(),options.createdUtc,zone_,{},
                json::Value::Object{{"synthetic_fixture",true},{"ui_audit_fixture",true},{"lease",lease_}}).get();
            require(session.status==storage::Status::Confirmed,"Fixture Session creation not confirmed; retain original directory"); session_=session.owner;
            const auto snapshot=store_->snapshot(storage::newUuid()).get(); require(snapshot.status==storage::Status::Confirmed,"Fixture profile identity unavailable");
            profile_=snapshot.data.object().at("profile_id").string();
            home_=std::make_unique<Home>(); require(home_->configureCapture(*store_,session_,zone_),"Fixture Home attachment refused");
            require(home_->attachPresentation(*store_,profile_),"Fixture presentation profile attachment refused");
            Access::halt(*home_); // One fixture timer serializes callbacks/receipts.
            // Profile UI launch callbacks remain empty: this target can never open
            // a real profile. Reopen is the SAME test-created store only.
            home_->onReopenStore=[this]{return reopen();};
            surface_=std::make_unique<Surface>(*home_,[this](Fault type){inject(type);},[this]{retain("operator-snapshot");});
            window_=std::make_unique<Window>(*surface_);
            const auto started=platform::monotonicNs(); deadline_=started+limit*1000000000ULL; lastBlocks_=started;
            selfTest_=args.size()==9;
            event("owned-launch",json::Value::Object{{"pid",integer(static_cast<std::uint64_t>(getpid()))},
                {"application",application.getFullPathName().toStdString()},{"command_line",commandLine.toStdString()},
                {"resources",resources_.string()},{"resource_pin_sha256",resourcePin_},
                {"resource_source_executable_sha256",resourceInventory.object().at("source_executable_sha256")},
                {"directory",directory_.string()},{"profile_id",profile_},
                {"session_id",session_},{"timezone",zone_},{"lease",lease_},{"max_seconds",integer(limit)},
                {"software_only",true},{"physical_or_human_review",false}});
            retain("attached"); write(directory_/"ownership.json",ownership("active"));
            startTimer(10);
        } catch(const std::exception& error) {
            std::cerr<<"FIXTURE_REFUSED "<<error.what()<<std::endl; setApplicationReturnValue(2);
            if(created_) event("startup-refused",json::Value::Object{{"reason",error.what()}}); quit();
        }
    }
    void systemRequestedQuit() override {
        if(!home_ || home_->requestClose()) { closingReason_="normal-guarded-quit"; quit(); }
        else { event("quit-held",json::Value::Object{{"reason","Actual Home guard retains original unsaved or active ownership"}}); }
    }
    void shutdown() override {
        stopTimer();
        if(home_) {
            try { retain("before-shutdown"); } catch(const std::exception& error) { std::cerr<<error.what()<<'\n'; setApplicationReturnValue(1); }
        }
        window_.reset(); surface_.reset(); home_.reset();
        if(store_) {
            // Do not manufacture a Session close. The snapshot explicitly records
            // any unresolved preview/Guided/activity debt for later inspection.
            try { const auto snapshot=store_->snapshot(storage::newUuid()).get();
                if(snapshot.status==storage::Status::Confirmed) write(directory_/"shutdown-snapshot.json",snapshot.data);
                else event("shutdown-snapshot-unavailable",json::Value::Object{{"status",storage::statusName(snapshot.status)}});
            } catch(const std::exception& error) { std::cerr<<error.what()<<'\n'; setApplicationReturnValue(1); }
        }
        store_.reset(); fixture::faults=nullptr; faults_.reset();
        if(created_) {
            try { write(directory_/"ownership.json",ownership("released"));
                event("shutdown",json::Value::Object{{"reason",closingReason_},{"forbidden_device_open_start_calls",integer(forbiddenCalls())},
                    {"real_performance_or_listening",false},{"session_close_fabricated",false}});
            } catch(const std::exception& error) { std::cerr<<error.what()<<'\n'; setApplicationReturnValue(1); }
        }
        if(forbiddenCalls()) setApplicationReturnValue(1);
        std::cout<<"FIXTURE_SHUTDOWN forbidden_device_calls="<<forbiddenCalls()<<std::endl;
    }
private:
    void event(const std::string& kind,json::Value detail) {
        if(log_) log_->append(kind,std::move(detail));
    }
    json::Value ownership(const std::string& state) const {
        return json::Value::Object{{"state",state},{"pid",integer(static_cast<std::uint64_t>(getpid()))},{"lease",lease_},
            {"profile_id",profile_},{"session_id",session_},{"profile_path",(directory_/"profile.sqlite").string()},
            {"timezone",zone_},{"actual_process_closure_requires_external_verification",true},
            {"synthetic",true},{"gui_foreground_lease_granted_by_root",false}};
    }
    void retain(const std::string& label) {
        if(!home_) return;
        const auto& p=Access::practice(*home_); const auto output=Access::output(*home_).status();
        event(label,json::Value::Object{{"page",integer(static_cast<unsigned>(home_->page()))},
            {"home_client_width",integer(static_cast<std::uint64_t>(home_->getWidth()))},
            {"home_client_height",integer(static_cast<std::uint64_t>(home_->getHeight()))},
            {"practice_session",p.captureSessionId()},
            {"practice_phase",integer(p.captureSession()?static_cast<unsigned>(p.captureSession()->phase()):0)},
            {"guided_session",Access::guided(*home_).sessionId()},{"guided_running",Access::guided(*home_).running()},
            {"freeplay_saved",Access::freeplay(*home_).persistenceSaved()},
            {"freeplay_active_nanoseconds",integer(Access::freeplay(*home_).activeNanoseconds())},
            {"freeplay_history_writes",integer(Access::freeplay(*home_).historyWriteCount())},
            {"output_epoch",integer(output.lifecycle.request.epoch)},{"output_state",integer(static_cast<unsigned>(output.lifecycle.state))},
            {"output_callbacks",integer(output.callbacks)},{"software_blocks",integer(softwareBlocks_)},
            {"forbidden_device_open_start_calls",integer(forbiddenCalls())},
            {"fault_armed",faults_?ui_fixture::name(faults_->armed()):"none"}});
    }
    void inject(Fault type) {
        bool newlyArmed=false;
        try {
            if(type==Fault::None) { faults_->clear(); event("cleared",nullptr); return; }
            require(faults_->arm(type),"Clear the prior armed fixture before replacing it");
            newlyArmed=true;
            event("armed",json::Value::Object{{"type",ui_fixture::name(type)}});
            if(type==Fault::LoadFailed || type==Fault::CorruptLoad) {
                require(desktop::LearnNavigationTestAccess::injectLoad(*home_,resources_,faults_,type),
                        "Load fault requires a fresh Home before a catalog/background load; use a fresh fixture invocation");
            } else if(type==Fault::PreferenceReadFailed || type==Fault::CorruptPreferenceReply) {
                require(desktop::MetronomeViewTestAccess::inspect(Access::metronome(*home_)),
                        "Settings inspection refused by actual activity/operation ownership; finish current work first");
            }
            // Device faults wait for explicit Connect. Save faults wait for the
            // original .save.commit; settings-receipt failure waits for Save.
        } catch(const std::exception& error) {
            if(newlyArmed) faults_->clear();
            event("injection-refused",json::Value::Object{{"reason",error.what()},{"existing_injection_preserved",!newlyArmed}});
        }
    }
    bool reopen() {
        if(!home_->detachForStoreReopen()) return false;
        Access::halt(*home_); store_.reset();
        try {
            storage::StoreOptions options; options.path=directory_/"profile.sqlite"; options.create=false;
            options.preferenceValidator=desktop::presentation::composedPreferenceValidator;
            options.diagnosticHook=[controller=faults_](const std::string& phase,const std::string& operation){controller->hook(phase,operation);};
            store_=std::make_unique<storage::ProfileStore>(options);
            require(home_->configureCapture(*store_,session_,zone_),"Owned fixture reattach refused"); Access::halt(*home_);
            require(home_->attachPresentation(*store_,profile_),"Owned fixture presentation reattach refused");
            retain("same-profile-reopened"); return true;
        } catch(const std::exception& error) { home_->storeReopenFailed(error.what()); event("reopen-failed",json::Value::Object{{"reason",error.what()}}); return false; }
    }
    bool perturbPreferences() {
        return desktop::MetronomeViewTestAccess::perturb(Access::metronome(*home_),*faults_,[this](const storage::Reply& actual){
            event("actual-receipt-before-substitution",json::Value::Object{{"operation",actual.operation},{"owner",actual.owner},
                {"status",storage::statusName(actual.status)},{"code",actual.code},{"data_sha256",content::sha256(storage::canonical(actual.data))}});
        });
    }
    void selfTest() {
        unsigned checks{}; auto check=[&](bool okay,const std::string& why){++checks; require(okay,why); event("self-check",json::Value::Object{{"name",why},{"pass",true}});};
        ui_fixture::Faults controller;
        for(auto type:{Fault::EmptyDevice,Fault::ConnectRefused,Fault::LoadFailed,Fault::CorruptLoad,
            Fault::PreferenceReadFailed,Fault::CorruptPreferenceReply,Fault::SettingsSaveFailed,Fault::SaveBeforeCommit,Fault::SaveLostReceipt}) {
            check(controller.arm(type,"owned-operation"),std::string(ui_fixture::name(type))+" arms");
            check(!controller.take(type,"foreign-operation"),"Foreign operation does not consume owned injection");
            check(controller.take(type,"owned-operation") && !controller.take(type,"owned-operation"),"One exact operation consumes injection once");
        }
        inject(Fault::SaveBeforeCommit);
        check(faults_->armed()==Fault::SaveBeforeCommit,"Actual toolbar arms original save failure");
        inject(Fault::EmptyDevice);
        check(faults_->armed()==Fault::SaveBeforeCommit,"Actual rejected toolbar replacement preserves original armed failure");
        inject(Fault::None);
        check(faults_->armed()==Fault::None,"Explicit toolbar Clear releases original armed failure");
        check(home_->audioSettings().connect(),"Actual shared settings connects software seam");
        Access::tick(*home_); check(home_->audioSettings().enable(),"Actual observed software output enables explicitly");
        check(platform::OutputTestAccess::block(Access::output(*home_)),"Software callback is manually owned"); ++softwareBlocks_; Access::tick(*home_);
        check(Access::output(*home_).status().callbacks>0,"Actual adapter consumes software callback");
        check(home_->audioSettings().disconnect(),"Idle software output disconnects through actual guard");
        for(auto type:{Fault::EmptyDevice,Fault::ConnectRefused}) {
            check(faults_->arm(type),"Device failure arms at seam");
            check(!home_->audioSettings().connect(),"Controlled software connection refuses");
            check(faults_->armed()==Fault::None,"Device failure is consumed once");
            check(home_->audioSettings().connect(),"Explicit reconnect recovers software seam");
            check(home_->audioSettings().disconnect(),"Recovered idle software seam releases");
        }
        for(auto type:{Fault::SaveBeforeCommit,Fault::SaveLostReceipt}) {
            const auto session=store_->createSession(storage::newUuid(),desktop::desktopUtcNow(),zone_,{},json::Value::Object{{"synthetic_fixture",true},{"capability_self_test",true}}).get();
            check(session.status==storage::Status::Confirmed,"Fault probe owns separate synthetic Session");
            const auto operation=storage::newUuid()+".save.commit"; const auto ended=desktop::desktopUtcNow();
            check(faults_->arm(type,operation),"Store fault binds exact operation before submission");
            const auto reply=store_->closeSession(operation,session.owner,ended,"interrupted").get();
            check(reply.status==(type==Fault::SaveLostReceipt?storage::Status::Unresolved:storage::Status::DefiniteFailure),"Actual store returns correct precommit versus lost-receipt status");
            check(faults_->armed()==Fault::None,"Store failure is consumed once");
            check(store_->closeSession(operation,session.owner,ended,"interrupted").get().status==storage::Status::Confirmed,"Exact original store operation recovers without row tampering");
        }
        for(auto type:{Fault::PreferenceReadFailed,Fault::CorruptPreferenceReply}) {
            auto& metronome=Access::metronome(*home_);
            check(faults_->arm(type),"Typed read-receipt failure arms");
            check(desktop::MetronomeViewTestAccess::inspect(metronome),"Actual preference inspection begins");
            const auto until=platform::monotonicNs()+3000000000ULL;
            while(!perturbPreferences()) {
                require(platform::monotonicNs()<until,"Owned preference-receipt watchdog"); std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
            metronome.service(); check(!metronome.preferencesReady(),"Actual preference view refuses failed/malformed returned data");
            check(metronome.reconcilePreferences(),"Actual explicit preference reinspection remains available");
            const auto recover=platform::monotonicNs()+3000000000ULL;
            while(!metronome.preferencesReady()) { metronome.service(); require(platform::monotonicNs()<recover,"Preference recovery watchdog"); std::this_thread::sleep_for(std::chrono::milliseconds(1)); }
            check(metronome.preferencesReady(),"Actual unchanged stored preferences recover");
        }
        check(faults_->arm(Fault::SettingsSaveFailed),"Settings receipt failure arms");
        auto& metronome=Access::metronome(*home_);
        check(metronome.saveLastUsed(),"Actual settings proposal starts");
        const auto receiptEnd=platform::monotonicNs()+3000000000ULL;
        while(!perturbPreferences()) { require(platform::monotonicNs()<receiptEnd,"Settings receipt watchdog"); std::this_thread::sleep_for(std::chrono::milliseconds(1)); }
        const auto recover=platform::monotonicNs()+3000000000ULL;
        while(!metronome.preferencesReady()) { metronome.service(); require(platform::monotonicNs()<recover,"Settings stored-value recovery watchdog"); std::this_thread::sleep_for(std::chrono::milliseconds(1)); }
        check(metronome.preferencesReady(),"Actual settings inspects committed proposal despite synthetic failed receipt");
        check(forbiddenCalls()==0,"Forbidden device open/start count is zero");
        check(store_->snapshot(storage::newUuid()).get().status==storage::Status::Confirmed,"Profile remains readable after all capability injections");
        // Remaining two capability checks use the real background loader and
        // its actual Guided failure publication, without constructing a catalog.
        // The normal JUCE event loop delivers callbacks between timer ticks.
        selfTest_=false; selfTestChecks_=checks; beginSelfTestLoad(Fault::LoadFailed);
    }
    void beginSelfTestLoad(Fault type) {
        require(faults_->arm(type),"Real loader failure self-test could not arm");
        require(desktop::LearnNavigationTestAccess::injectLoad(*home_,resources_,faults_,type),"Real Guided loader injection was refused");
        selfTestLoad_=type; selfTestLoadDeadline_=platform::monotonicNs()+30000000000ULL;
    }
    void observeSelfTestLoad() {
        require(platform::monotonicNs()<selfTestLoadDeadline_,"30-second actual loader-failure publication watchdog");
        if(desktop::LearnNavigationTestAccess::loading(*home_)) return;
        require(faults_->armed()==Fault::None,"Actual loader did not consume its controlled boundary failure");
        const auto* loadState=dynamic_cast<juce::Label*>(Access::guided(*home_).findChildWithID("guided-plan-state"));
        require(loadState && loadState->isVisible() && loadState->getText().toStdString().find(ui_fixture::name(selfTestLoad_))!=std::string::npos,
                "Actual Guided loader UI did not retain the typed failure reason");
        ++selfTestChecks_; event("self-check",json::Value::Object{{"name",std::string("Actual loader publishes ")+ui_fixture::name(selfTestLoad_)},{"pass",true}});
        if(selfTestLoad_==Fault::LoadFailed) { beginSelfTestLoad(Fault::CorruptLoad); return; }
        selfTestLoad_=Fault::None;
        require(forbiddenCalls()==0,"Unexpected native/device call during actual loader self-tests");
        write(directory_/"self-test-summary.json",json::Value::Object{{"status","PASS"},{"checks",integer(selfTestChecks_)},
            {"forbidden_device_open_start_calls",integer(forbiddenCalls())},
            {"integrated_active_gui_flows_proven",false},{"actual_listening_or_performance",false}});
        closingReason_="capability-self-test-complete"; quit();
    }
    void timerCallback() override {
        try {
            perturbPreferences();
            const auto now=platform::monotonicNs();
            // Wall-paced software frames, bounded catch-up. This is functional
            // exercise-state evidence, never real-device latency/timing evidence.
            constexpr std::uint64_t blockNs=256ULL*1000000000ULL/44100ULL;
            unsigned burst{};
            while(now>=lastBlocks_+blockNs && burst++<8) {
                if(platform::OutputTestAccess::block(Access::output(*home_))) ++softwareBlocks_;
                lastBlocks_+=blockNs;
            }
            if(burst>8) { event("software-scheduling-gap",json::Value::Object{{"unserved_ns",integer(now-lastBlocks_)}}); lastBlocks_=now; }
            Access::tick(*home_);
            if(selfTest_ && Access::metronome(*home_).preferencesReady()) { selfTest(); return; }
            if(selfTestLoad_!=Fault::None) { observeSelfTestLoad(); if(selfTestLoad_==Fault::None) return; }
            require(forbiddenCalls()==0,"Forbidden fixture device-open/start invocation");
            if(now>=deadline_) {
                const bool clean=home_->requestClose(); retain(clean?"deadline-guard-clear":"deadline-unresolved-original-retained");
                closingReason_=clean?"bounded-deadline-guard-clear":"bounded-deadline-interrupted-with-retained-debt";
                if(!clean) setApplicationReturnValue(3); quit();
            }
        } catch(const std::exception& error) {
            event("fixture-failure",json::Value::Object{{"reason",error.what()}}); closingReason_="fixture-failure";
            setApplicationReturnValue(1); quit();
        }
    }
    std::filesystem::path directory_,resources_; std::string zone_,lease_,profile_,session_,resourcePin_,closingReason_{"startup-refused"};
    std::shared_ptr<EventLog> log_; std::shared_ptr<ui_fixture::Faults> faults_;
    std::unique_ptr<storage::ProfileStore> store_; std::unique_ptr<Home> home_;
    std::unique_ptr<Surface> surface_; std::unique_ptr<Window> window_;
    std::uint64_t deadline_{},lastBlocks_{},softwareBlocks_{},selfTestLoadDeadline_{}; bool created_{},selfTest_{};
    Fault selfTestLoad_{Fault::None}; unsigned selfTestChecks_{};
};
} // namespace fixture
START_JUCE_APPLICATION(fixture::Application)
