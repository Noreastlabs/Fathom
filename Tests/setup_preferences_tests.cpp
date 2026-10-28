#include "desktop/SetupPreferences.hpp"
#include "desktop/PresentationPreferences.hpp"
#include <atomic>
#include <condition_variable>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <thread>

using namespace fathom;
namespace setup = fathom::desktop::setup;
namespace presentation = fathom::desktop::presentation;
namespace {
using V = json::Value;
using O = V::Object;
V::Array checks;
int failures = 0;
void check(const std::string& name, bool pass) {
    checks.emplace_back(O{{"case", name}, {"passed", pass}});
    std::cout << (pass ? "PASS " : "FAIL ") << name << '\n';
    if (!pass) ++failures;
}
template<class F> void rejects(const std::string& name, F action) {
    bool refused = false;
    try { action(); } catch (const std::exception&) { refused = true; }
    check(name, refused);
}
storage::Reply reply(storage::ProfileStore::Future future) {
    if (future.wait_for(std::chrono::seconds(5)) != std::future_status::ready)
        throw std::runtime_error("Fixture Store acknowledgment timed out; no retry submitted");
    return future.get();
}
void settle(setup::PreferencesController& controller) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (controller.inFlight()) {
        controller.poll();
        if (std::chrono::steady_clock::now() >= deadline)
            throw std::runtime_error("Setup acknowledgment timed out; original future retained");
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}
storage::StoreOptions options(const std::filesystem::path& directory) {
    storage::StoreOptions value;
    value.path = directory / "profile.sqlite";
    value.create = true;
    value.createdUtc = "2026-10-07T13:20:00Z";
    value.preferenceValidator = presentation::composedPreferenceValidator;
    return value;
}
std::string profileIdentity(storage::ProfileStore& store) {
    const auto value = reply(store.snapshot(storage::newUuid()));
    if (value.status != storage::Status::Confirmed) throw std::runtime_error("Fixture profile identity unavailable");
    return value.data.object().at("profile_id").string();
}
std::string storedBytes(storage::ProfileStore& store, const char* key = setup::preferenceKey) {
    const auto value = reply(store.readPreferences(storage::newUuid(), key));
    if (value.status != storage::Status::Confirmed) throw std::runtime_error("Expected stored fixture namespace");
    return value.data.object().at("bytes").string();
}
V protectedHistory(storage::ProfileStore& store) {
    const auto value = reply(store.snapshot(storage::newUuid()));
    if (value.status != storage::Status::Confirmed) throw std::runtime_error("Fixture snapshot unavailable");
    auto authority = value.data.object().at("authoritative");
    authority.object().erase("preferences");
    return authority;
}
// The real writer waits before one operation. Release-on-exit is declared after
// Store so a failed oracle cannot strand its destructor behind the test latch.
struct Gate {
    std::atomic<bool> armed{false}, entered{false};
    std::mutex mutex;
    std::condition_variable cv;
    bool released = false;
    void arm() {
        std::lock_guard<std::mutex> lock(mutex);
        released = false;
        entered.store(false);
        armed.store(true);
    }
    void holdIfArmed() {
        if (!armed.exchange(false)) return;
        std::unique_lock<std::mutex> lock(mutex);
        entered.store(true);
        cv.notify_all();
        cv.wait(lock, [&] { return released; });
    }
    void awaitEntered() {
        std::unique_lock<std::mutex> lock(mutex);
        if (!cv.wait_for(lock, std::chrono::seconds(5), [&] { return entered.load(); }))
            throw std::runtime_error("Controlled setup writer gate not entered");
    }
    void release() {
        { std::lock_guard<std::mutex> lock(mutex); released = true; }
        cv.notify_all();
    }
};
struct ReleaseOnExit { Gate& gate; ~ReleaseOnExit() { gate.release(); } };

void policyCases() {
    const setup::Model defaults;
    check("setup defaults preserve existing guitar and closed-output mix defaults",
          defaults.appearance == setup::Appearance::Default && defaults.experience == presentation::Level::Beginner &&
          defaults.step == setup::Step::Welcome && !defaults.completed && !defaults.skipped &&
          defaults.guitar.openMidi == guitar::Setup{}.openMidi && defaults.audio.bus == output::MixSettings{}.bus);
    for (const auto appearance : {setup::Appearance::Default, setup::Appearance::Light, setup::Appearance::Dark}) {
        auto value = defaults; value.appearance = appearance;
        check(std::string("appearance round trip: ") + setup::appearanceName(appearance),
              setup::decodePreferences(setup::encodePreferences(value)) == value);
    }
    for (const auto step : {setup::Step::Welcome, setup::Step::Experience, setup::Step::Appearance,
                           setup::Step::Guitar, setup::Step::Audio, setup::Step::Summary}) {
        auto value = defaults; value.step = step;
        check(std::string("resume step round trip: ") + setup::stepName(step),
              setup::decodePreferences(setup::encodePreferences(value)) == value);
    }
    auto boundary = defaults;
    boundary.guitar.openMidi = {{0,127,0,127,0,127}};
    boundary.guitar.capo = boundary.guitar.fretCount = 36;
    boundary.guitar.handedness = guitar::Handedness::Left;
    boundary.audio.bus = {{0,100,0,100}};
    boundary.audio.master = 100; boundary.audio.masterMute = true;
    boundary.audio.muteMask = 15; boundary.audio.soloAB = 3;
    boundary.experience = presentation::Level::Developer;
    boundary.step = setup::Step::Summary; boundary.completed = true; boundary.skipped = true;
    check("valid guitar mix flags and draft enums round trip without narrowing",
          setup::decodePreferences(setup::encodePreferences(boundary)) == boundary);
    auto invalid = setup::encodePreferences(defaults);
    for (const auto key : {"device_id", "permission", "identity", "running"}) {
        auto extra = invalid; extra.object()[key] = true;
        check(std::string("authority and transport field refused: ") + key,
              !setup::preferenceValidator(setup::preferenceKey, 1, extra));
    }
    auto mutate = [&](const std::string& name, auto edit) {
        auto value = setup::encodePreferences(defaults); edit(value);
        check(name, !setup::preferenceValidator(setup::preferenceKey, 1, value));
    };
    mutate("future setup value version refused", [](V& v) { v.object()["version"] = "setup2"; });
    mutate("unknown appearance refused", [](V& v) { v.object()["appearance"] = "automatic-device"; });
    mutate("unknown experience refused", [](V& v) { v.object()["experience"] = "administrator"; });
    mutate("unknown resume step refused", [](V& v) { v.object()["step"] = "transport"; });
    mutate("completion integer cannot become boolean", [](V& v) { v.object()["completed"] = V::fromInteger(1); });
    mutate("missing exact outer field refused", [](V& v) { v.object().erase("skipped"); });
    mutate("future instrument version refused", [](V& v) { v.object()["guitar"].object()["version"] = "instrument2"; });
    mutate("unknown hand refused", [](V& v) { v.object()["guitar"].object()["handedness"] = "either"; });
    mutate("six pitch count enforced", [](V& v) { v.object()["guitar"].object()["open_midi"].array().pop_back(); });
    mutate("out of MIDI range refused", [](V& v) { v.object()["guitar"].object()["open_midi"].array()[0] = V::fromInteger(128); });
    mutate("capo past physical neck refused", [](V& v) { v.object()["guitar"].object()["capo"] = V::fromInteger(23); });
    mutate("too many physical frets refused", [](V& v) { v.object()["guitar"].object()["fret_count"] = V::fromInteger(37); });
    mutate("unknown guitar field refused", [](V& v) { v.object()["guitar"].object()["device"] = "none"; });
    mutate("exact four mix buses enforced", [](V& v) { v.object()["audio"].object()["bus"].array().pop_back(); });
    mutate("mix gain above100 refused", [](V& v) { v.object()["audio"].object()["bus"].array()[0] = V::fromInteger(101); });
    mutate("fractional mix gain refused", [](V& v) { v.object()["audio"].object()["master"] = json::Number{"50.5"}; });
    mutate("negative mix gain refused", [](V& v) { v.object()["audio"].object()["master"] = V::fromInteger(-1); });
    mutate("mix mute requires boolean", [](V& v) { v.object()["audio"].object()["master_mute"] = "false"; });
    mutate("mute mask rejects overflow before uint8 conversion", [](V& v) { v.object()["audio"].object()["mute_mask"] = V::fromInteger(256); });
    mutate("solo mask unknown bit refused", [](V& v) { v.object()["audio"].object()["solo_ab"] = V::fromInteger(4); });
    rejects("invalid in-memory appearance cannot be encoded", [&] { auto v = defaults; v.appearance = static_cast<setup::Appearance>(999); setup::encodePreferences(v); });
    check("composed validator routes only supported named owners",
          presentation::composedPreferenceValidator(setup::preferenceKey, 1, setup::encodePreferences(defaults)) &&
          presentation::composedPreferenceValidator(presentation::preferenceKey, 1, presentation::encodePreferences(presentation::Level::Advanced)) &&
          presentation::composedPreferenceValidator("freeplay_timing", 1, metronome::encodePreferences(metronome::Preferences{})) &&
          !presentation::composedPreferenceValidator("arbitrary", 1, setup::encodePreferences(defaults)) &&
          !setup::preferenceValidator(setup::preferenceKey, 2, setup::encodePreferences(defaults)));
}

void durableCases(const std::filesystem::path& root) {
    auto config = options(root / "durable");
    setup::PreferencesController controller;
    setup::Model chosen;
    chosen.appearance = setup::Appearance::Dark; chosen.experience = presentation::Level::Advanced;
    chosen.step = setup::Step::Guitar; chosen.guitar.openMidi[0] = 38;
    chosen.audio.master = 67; chosen.audio.muteMask = 4;
    controller.choose(chosen);
    check("unbound choices have no Store write or transport", !controller.hasProfile() && controller.dirty() &&
          !controller.pending() && !controller.ready() && !controller.save(true) && controller.canDetach());
    std::string identity, finalBytes, canonicalPresentation;
    V history;
    {
        storage::ProfileStore store(config);
        identity = profileIdentity(store);
        const auto session = reply(store.createSession(storage::newUuid(), "2026-10-07T13:20:01Z", "America/New_York"));
        check("seed actual retained Session history", session.status == storage::Status::Confirmed &&
              reply(store.closeSession(storage::newUuid(), session.owner, "2026-10-07T13:20:02Z", "cancelled")).status == storage::Status::Confirmed);
        check("seed independent saved acknowledgment history", reply(store.acknowledge(storage::newUuid(), storage::newUuid(),
              "fg:item:000001", 1, "2026-10-07T13:20:03Z")).status == storage::Status::Confirmed);
        canonicalPresentation = storage::canonical(presentation::encodePreferences(presentation::Level::Advanced));
        check("canonical presentation independently confirmed before completion",
              reply(store.compareExchangePreferences(storage::newUuid(), presentation::preferenceKey, 1, 0, canonicalPresentation, true)).status == storage::Status::Confirmed);
        history = protectedHistory(store);
        check("attach starts only read and holds Store lifetime", controller.attach(store, identity) &&
              controller.inFlight() && !controller.canDetach() && !controller.detach());
        settle(controller);
        check("absent namespace preserves existing-profile session draft without completion",
              controller.model() == chosen && controller.observedRevision() == 0 && controller.dirty() &&
              controller.supported() && controller.ready() && !controller.model().completed &&
              reply(store.readPreferences(storage::newUuid(), setup::preferenceKey)).status == storage::Status::DefinitelyAbsent);
        check("explicit absent reload starts only a read", controller.reload()); settle(controller);
        check("absent reload retains the current draft without fabricating saved completion", controller.model() == chosen &&
              controller.dirty() && controller.observedRevision() == 0 && !controller.model().completed &&
              reply(store.readPreferences(storage::newUuid(), setup::preferenceKey)).status == storage::Status::DefinitelyAbsent);
        auto malformed = setup::encodePreferences(chosen);
        malformed.object()["audio"].object()["mute_mask"] = V::fromInteger(256);
        check("actual Store refuses invalid setup semantics without creating namespace",
              reply(store.compareExchangePreferences(storage::newUuid(), setup::preferenceKey, 1, 0,
                  storage::canonical(malformed), true)).status == storage::Status::Unsupported &&
              reply(store.readPreferences(storage::newUuid(), setup::preferenceKey)).status == storage::Status::DefinitelyAbsent);
        check("actual Store refuses unknown setup namespace version", reply(store.compareExchangePreferences(storage::newUuid(),
              setup::preferenceKey, 2, 0, storage::canonical(setup::encodePreferences(chosen)), true)).status == storage::Status::Unsupported);
        check("invalid chosen guitar cannot partially change controller model", [&] {
            auto bad = chosen; bad.guitar.capo = 100;
            try { controller.choose(bad); } catch (const std::invalid_argument&) { return controller.model() == chosen; }
            return false;
        }());
        check("stopped-resolved gate required before original save", !controller.save(false) &&
              controller.state() == setup::PreferenceState::StopRequired && !controller.pending() && controller.dirty());
        const auto directStop = reply(store.compareExchangePreferences(storage::newUuid(), setup::preferenceKey, 1, 0,
            storage::canonical(setup::encodePreferences(chosen)), false));
        check("actual Store independently enforces stopped application gate", directStop.status == storage::Status::DefiniteFailure &&
              directStop.code == "STOP_REQUIRED");
        check("explicit draft save submits guarded CAS", controller.save(true));
        const auto operation = controller.pendingOperationId();
        const auto proposal = controller.pendingBytes();
        check("in-flight save retains exact original proposal", !operation.empty() && !proposal.empty() &&
              controller.inFlight() && !controller.canDetach() && !controller.save(true) && !controller.detach());
        settle(controller);
        check("draft save confirmed at revision1 exact bytes", controller.observedRevision() == 1 && !controller.dirty() &&
              controller.ready() && storedBytes(store) == storage::canonical(setup::encodePreferences(chosen)));
        chosen.step = setup::Step::Summary; chosen.completed = true;
        controller.choose(chosen);
        check("explicit completion is saved only after confirmed canonical experience", storedBytes(store, presentation::preferenceKey) == canonicalPresentation && controller.save(true));
        settle(controller);
        check("completion round trip confirmed at revision2", controller.observedRevision() == 2 && !controller.dirty() &&
              setup::decodePreferences(storage::parseCanonical(storedBytes(store))).completed);
        controller.choose(chosen);
        check("same completed model is idempotent without replacement write", !controller.dirty() && !controller.save(true) &&
              !controller.poll() && !controller.poll() && controller.observedRevision() == 2);
        auto latest = chosen; latest.appearance = setup::Appearance::Light;
        controller.choose(latest);
        const setup::Model elsewhere;
        check("independent writer changes actual setup revision", reply(store.compareExchangePreferences(storage::newUuid(), setup::preferenceKey,
              1, 2, storage::canonical(setup::encodePreferences(elsewhere)), true)).status == storage::Status::Confirmed);
        check("stale controller submits original expected revision", controller.save(true));
        settle(controller);
        check("conflict preserves latest draft and refuses overwrite", controller.state() == setup::PreferenceState::Conflict &&
              controller.model() == latest && !controller.canSave(true) && !controller.ready() && !controller.pending() &&
              storedBytes(store) == storage::canonical(setup::encodePreferences(elsewhere)));
        check("explicit conflict reload submitted", controller.reload()); settle(controller);
        check("explicit reload accepts saved draft without inventing completion", controller.model() == elsewhere &&
              controller.observedRevision() == 3 && !controller.dirty() && controller.ready() && !controller.model().completed);
        controller.choose(chosen); check("explicit resave after conflict", controller.save(true)); settle(controller);
        finalBytes = storedBytes(store);
        check("setup writes preserve all12 non-preference authoritative tables", protectedHistory(store) == history);
        check("setup experience draft cannot overwrite canonical presentation", storedBytes(store, presentation::preferenceKey) == canonicalPresentation);
        check("confirmed controller detaches", controller.detach() && !controller.hasProfile());
    }
    config.create = false;
    {
        storage::ProfileStore reopened(config);
        controller.attach(reopened, identity); settle(controller);
        check("normal restart restores full setup and completion exact revision", controller.model() == chosen &&
              controller.observedRevision() == 4 && !controller.dirty() && storedBytes(reopened) == finalBytes);
        check("normal restart preserves prior history and canonical presentation", protectedHistory(reopened) == history &&
              storedBytes(reopened, presentation::preferenceKey) == canonicalPresentation);
        controller.detach();
    }
    {
        storage::ProfileStore other(options(root / "other-profile"));
        const auto otherId = profileIdentity(other);
        controller.attach(other, otherId); settle(controller);
        check("different absent profile receives defaults without inheriting completion", otherId != identity &&
              controller.profileIdentity() == otherId && controller.model() == setup::Model{} &&
              controller.observedRevision() == 0 && !controller.dirty() && !controller.model().completed);
        controller.detach();
    }
}

void interleavingCases(const std::filesystem::path& root) {
    Gate gate;
    auto config = options(root / "interleaved");
    config.diagnosticHook = [&](const std::string& phase, const std::string&) { if (phase == "before_operation") gate.holdIfArmed(); };
    storage::ProfileStore store(config);
    ReleaseOnExit release{gate};
    const auto identity = profileIdentity(store);
    setup::Model saved; saved.appearance = setup::Appearance::Light; saved.step = setup::Step::Experience;
    check("seed real setup before queued read", reply(store.compareExchangePreferences(storage::newUuid(), setup::preferenceKey,
          1, 0, storage::canonical(setup::encodePreferences(saved)), true)).status == storage::Status::Confirmed);
    setup::PreferencesController controller;
    gate.arm(); controller.attach(store, identity); gate.awaitEntered();
    auto newer = saved; newer.appearance = setup::Appearance::Dark; newer.step = setup::Step::Audio;
    controller.choose(newer);
    check("initial queued read blocks detach but not newer explicit draft", controller.inFlight() && !controller.canDetach() && controller.model() == newer);
    gate.release(); settle(controller);
    check("initial late read preserves newer draft and actual observed revision", controller.model() == newer && controller.dirty() &&
          controller.observedRevision() == 1 && storedBytes(store) == storage::canonical(setup::encodePreferences(saved)));
    gate.arm(); controller.reload(); gate.awaitEntered();
    newer.audio.master = 72; controller.choose(newer); gate.release(); settle(controller);
    check("choice after explicit Reload still wins against its queued acknowledgment", controller.model() == newer && controller.dirty() && controller.observedRevision() == 1);
    gate.arm(); check("interleaved actual write submitted", controller.save(true)); gate.awaitEntered();
    const auto originalBytes = controller.pendingBytes(); const auto originalOp = controller.pendingOperationId();
    auto latest = newer; latest.step = setup::Step::Summary; latest.completed = true; controller.choose(latest);
    check("choice while writing cannot replace original proposed bytes or operation", controller.pendingBytes() == originalBytes &&
          controller.pendingOperationId() == originalOp && !controller.save(true));
    gate.release(); settle(controller);
    check("confirmed earlier write leaves newer completion dirty and unsaved", controller.model() == latest && controller.dirty() &&
          controller.observedRevision() == 2 && storedBytes(store) == originalBytes &&
          !setup::decodePreferences(storage::parseCanonical(storedBytes(store))).completed);
    check("repeated poll cannot write newer completion or advance revision", !controller.poll() && !controller.poll() &&
          controller.observedRevision() == 2 && storedBytes(store) == originalBytes);
    controller.detach();
}

void unsupportedCases(const std::filesystem::path& root) {
    for (const auto future : {false, true}) {
        auto config = options(root / (future ? "future" : "malformed"));
        auto value = setup::encodePreferences(setup::Model{});
        if (future) value.object()["version"] = "setup-future-synthetic";
        else value.object()["audio"].object()["master"] = "invalid-gain";
        const auto version = future ? 2 : 1;
        const auto original = storage::canonical(value);
        config.preferenceValidator = [](const auto& key, auto, const auto&) { return key == setup::preferenceKey; };
        {
            storage::ProfileStore seed(config);
            check(future ? "synthetic future seed accepted by isolated owner" : "synthetic malformed-semantic seed accepted by isolated owner",
                  reply(seed.compareExchangePreferences(storage::newUuid(), setup::preferenceKey, version, 0, original, true)).status == storage::Status::Confirmed);
        }
        config.create = false; config.preferenceValidator = presentation::composedPreferenceValidator;
        storage::ProfileStore current(config);
        setup::PreferencesController controller;
        auto chosen = setup::Model{}; chosen.appearance = setup::Appearance::Dark; chosen.step = setup::Step::Guitar;
        controller.choose(chosen); controller.attach(current, profileIdentity(current)); settle(controller);
        check(future ? "future read preserves exact bytes and session choice" : "malformed read preserves exact bytes and session choice",
              controller.state() == setup::PreferenceState::Unsupported && controller.model() == chosen &&
              !controller.supported() && !controller.ready() && !controller.canSave(true) && !controller.save(true) && storedBytes(current) == original);
        controller.reload(); settle(controller);
        check(future ? "future explicit reload is not a reset/migration" : "malformed explicit reload is not a reset/rewrite",
              controller.model() == chosen && !controller.poll() && storedBytes(current) == original && controller.canDetach());
        controller.detach();
    }
}

void unknownCases(const std::filesystem::path& root) {
    for (const auto differing : {false, true}) {
        auto config = options(root / (differing ? "unknown-differing" : "unknown-exact"));
        bool loseReceipt = true;
        config.diagnosticHook = [&](const std::string& phase, const std::string&) {
            if (phase == "after_commit" && loseReceipt) { loseReceipt = false; throw std::runtime_error("controlled setup receipt loss"); }
        };
        storage::ProfileStore store(config);
        setup::PreferencesController controller;
        controller.attach(store, profileIdentity(store)); settle(controller);
        setup::Model proposed; proposed.appearance = setup::Appearance::Dark; proposed.step = setup::Step::Summary; proposed.completed = true;
        controller.choose(proposed); check("receipt-loss original write submitted", controller.save(true));
        const auto op = controller.pendingOperationId(); const auto bytes = controller.pendingBytes();
        settle(controller);
        check("lost receipt preserves original unknown debt without retry/detach", controller.state() == setup::PreferenceState::Unknown &&
              controller.pendingOperationId() == op && controller.pendingBytes() == bytes && !controller.inFlight() &&
              !controller.canDetach() && !controller.detach() && !controller.canSave(true) && !controller.save(true));
        auto latest = proposed; latest.appearance = setup::Appearance::Light; latest.completed = false; controller.choose(latest);
        check("new choice cannot replace unknown completion proposal", controller.model() == latest && controller.pendingOperationId() == op && controller.pendingBytes() == bytes);
        if (differing) {
            check("later actual writer moves beyond unknown original proposal", reply(store.compareExchangePreferences(storage::newUuid(), setup::preferenceKey,
                  1, 1, storage::canonical(setup::encodePreferences(setup::Model{})), true)).status == storage::Status::Confirmed);
        }
        check("unknown inspection explicitly submitted with no new write", controller.reload()); settle(controller);
        if (!differing) {
            check("exact next-revision value resolves only stored value preserving latest choice", controller.pendingOperationId().empty() &&
                  controller.pendingBytes().empty() && controller.observedRevision() == 1 && controller.model() == latest && controller.dirty() &&
                  controller.canDetach() && storedBytes(store) == bytes && controller.statusText().find("Which operation saved it is not established") != std::string::npos);
            check("repeated resolved poll cannot save latest completion flag", !controller.poll() && !controller.poll() &&
                  controller.observedRevision() == 1 && storedBytes(store) == bytes);
            controller.detach();
        } else {
            check("different later value cannot fabricate original outcome or permit overwrite", controller.state() == setup::PreferenceState::Unknown &&
                  controller.pendingOperationId() == op && controller.pendingBytes() == bytes && controller.model() == latest &&
                  !controller.canDetach() && !controller.detach() && !controller.save(true) && !controller.poll());
            // Fixture-only teardown retains the unsupported production debt. No
            // detach, replacement operation, fabricated receipt or history write.
        }
    }
}
}
int main(int argc, char** argv) {
    try {
        if (argc != 3 || !std::filesystem::path(argv[1]).is_absolute() || !std::filesystem::path(argv[2]).is_absolute() ||
            std::filesystem::exists(argv[1]) || std::filesystem::exists(argv[2]))
            throw std::runtime_error("New absolute synthetic profile root and result JSON required");
        const auto root = std::filesystem::path(argv[1]);
        if (!std::filesystem::create_directory(root)) throw std::runtime_error("Cannot reserve fresh fixture root");
        std::filesystem::permissions(root, std::filesystem::perms::owner_all, std::filesystem::perm_options::replace);
        policyCases(); durableCases(root); interleavingCases(root); unsupportedCases(root); unknownCases(root);
        std::ofstream output(argv[2]);
        output << storage::canonical(O{{"classification", "isolated setup preferences and real Store CAS; software-only, no GUI/device/credit/release claim"},
            {"checks", checks}, {"failures", V::fromInteger(failures)}}) << '\n';
        if (!output) throw std::runtime_error("Cannot persist setup preference fixture summary");
        return failures ? 1 : 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 2; }
}
