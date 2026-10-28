#include "desktop/PresentationPreferences.hpp"
#include <atomic>
#include <filesystem>
#include <fstream>
#include <future>
#include <iostream>
#include <thread>

using namespace fathom;
using namespace fathom::desktop::presentation;
namespace {
using V = json::Value;
using O = V::Object;
V::Array checks;
int failures = 0;
void check(const std::string& name, bool pass) {
    checks.emplace_back(O{{"case", name}, {"passed", pass}});
    if (!pass) ++failures;
    std::cout << (pass ? "PASS " : "FAIL ") << name << '\n';
}
template<class F> void rejects(const std::string& name, F action) {
    bool refused = false;
    try { action(); } catch (const std::exception&) { refused = true; }
    check(name, refused);
}
void settle(PreferencesController& controller) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    // An Unknown state retains debt but has no executing Future to wait for.
    while (controller.state() == PreferenceState::Reading ||
           controller.state() == PreferenceState::Saving) {
        controller.poll();
        if (std::chrono::steady_clock::now() >= deadline)
            throw std::runtime_error("Presentation preference acknowledgment timed out; original future retained");
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}
storage::Reply reply(storage::ProfileStore::Future future) { return future.get(); }
std::string storedBytes(storage::ProfileStore& store, const char* key = preferenceKey) {
    const auto result = reply(store.readPreferences(storage::newUuid(), key));
    if (result.status != storage::Status::Confirmed) throw std::runtime_error("Expected stored preference");
    return result.data.object().at("bytes").string();
}
storage::StoreOptions options(const std::filesystem::path& directory) {
    storage::StoreOptions result;
    result.path = directory / "profile.sqlite";
    result.create = true;
    result.createdUtc = "2026-10-04T15:10:09Z";
    result.preferenceValidator = composedPreferenceValidator;
    return result;
}
std::string profileIdentity(storage::ProfileStore& store) {
    const auto snapshot = reply(store.snapshot(storage::newUuid()));
    if (snapshot.status != storage::Status::Confirmed) throw std::runtime_error("Profile identity unavailable");
    return snapshot.data.object().at("profile_id").string();
}
}
int main(int argc, char** argv) {
    try {
        if (argc != 3 || !std::filesystem::path(argv[1]).is_absolute() ||
            !std::filesystem::path(argv[2]).is_absolute() ||
            std::filesystem::exists(argv[1]) || std::filesystem::exists(argv[2]))
            throw std::runtime_error("New absolute synthetic profile root and result JSON required");
        const auto root = std::filesystem::path(argv[1]);
        std::filesystem::create_directory(root);
        std::filesystem::permissions(root, std::filesystem::perms::owner_all);

        for (const auto level : {Level::Beginner, Level::Advanced, Level::Developer}) {
            check(std::string("strict level round trip: ") + levelName(level),
                  decodePreferences(encodePreferences(level)) == level &&
                  preferenceValidator(preferenceKey, 1, encodePreferences(level)));
        }
        auto invalid = encodePreferences(Level::Beginner);
        invalid.object()["permission"] = "administrator";
        rejects("extra field cannot create a role/permission", [&] { decodePreferences(invalid); });
        check("strict validator rejects extra field", !preferenceValidator(preferenceKey, 1, invalid));
        invalid = encodePreferences(Level::Beginner);
        invalid.object()["global_level"] = true;
        rejects("wrong level type refused", [&] { decodePreferences(invalid); });
        invalid.object()["global_level"] = "expert";
        rejects("unknown level not normalized", [&] { decodePreferences(invalid); });
        invalid = encodePreferences(Level::Beginner);
        invalid.object()["version"] = "presentation2";
        rejects("future value version refused", [&] { decodePreferences(invalid); });
        rejects("missing global field refused", [&] { decodePreferences(O{{"version", "presentation1"}}); });
        rejects("non-object refused", [&] { decodePreferences(nullptr); });
        rejects("invalid in-memory level refused", [&] { encodePreferences(static_cast<Level>(999)); });
        check("unknown namespace/version refused", !preferenceValidator("other", 1, encodePreferences(Level::Beginner)) &&
              !preferenceValidator(preferenceKey, 2, encodePreferences(Level::Beginner)));

        Model model;
        check("Beginner default inherited by both pages", model.effectiveLevel(Page::Learn) == Level::Beginner &&
              model.effectiveLevel(Page::Practice) == Level::Beginner);
        model.setPageOverride(Page::Learn, Level::Developer);
        model.setGlobalLevel(Level::Advanced);
        check("global change preserves independent session override", model.effectiveLevel(Page::Learn) == Level::Developer &&
              model.effectiveLevel(Page::Practice) == Level::Advanced);
        check("effective labels disclose inheritance and session scope",
              model.effectiveLabel(Page::Learn) == "Presentation: Developer (this page, session only)" &&
              model.effectiveLabel(Page::Practice) == "Presentation: Advanced (global)");
        model.resetPage(Page::Learn);
        check("page reset only clears its override", !model.pageOverride(Page::Learn) && model.globalLevel() == Level::Advanced);
        model.setPageOverride(Page::Practice, Level::Advanced);
        model.resetPresentation();
        check("reset all is Beginner and clears both overrides", model.globalLevel() == Level::Beginner &&
              !model.pageOverride(Page::Learn) && !model.pageOverride(Page::Practice));

        PreferencesController controller;
        controller.chooseGlobal(Level::Developer);
        controller.choosePage(Page::Practice, Level::Advanced);
        check("no-profile choices are session-only with no write", controller.state() == PreferenceState::NoProfile &&
              !controller.canSave(true) && !controller.save(true) && controller.canDetach() &&
              controller.statusText().find("for this session") != std::string::npos);
        auto config = options(root / "first");
        std::string firstIdentity;
        std::string timingBytes;
        {
            storage::ProfileStore store(config);
            firstIdentity = profileIdentity(store);
            check("explicit attach resets prior no-profile choices", controller.attach(store, firstIdentity) &&
                  controller.model().globalLevel() == Level::Beginner && !controller.model().pageOverride(Page::Practice));
            check("read in flight holds profile ownership", !controller.canDetach() && !controller.detach());
            settle(controller);
            check("missing preference is observed revision zero", controller.observedRevision() == 0 &&
                  controller.state() == PreferenceState::Ready && !controller.dirty());
            controller.chooseGlobal(Level::Advanced);
            check("choice alone does not dispatch storage", !controller.pending() &&
                  reply(store.readPreferences(storage::newUuid(), preferenceKey)).status == storage::Status::DefinitelyAbsent);
            const auto badFields = storage::canonical(O{{"version", "presentation1"}, {"global_level", "advanced"}, {"authority", true}});
            const auto unknownVersion = storage::canonical(O{{"version", "presentation2"}, {"global_level", "advanced"}});
            check("actual store refuses malformed extra fields", reply(store.compareExchangePreferences(storage::newUuid(), preferenceKey,
                  1, 0, badFields, true)).status == storage::Status::Unsupported);
            check("actual store refuses unknown version and leaves namespace missing", reply(store.compareExchangePreferences(storage::newUuid(),
                  preferenceKey, 1, 0, unknownVersion, true)).status == storage::Status::Unsupported &&
                  reply(store.readPreferences(storage::newUuid(), preferenceKey)).status == storage::Status::DefinitelyAbsent);
            check("active owner refuses save and remains dirty", !controller.save(false) &&
                  controller.state() == PreferenceState::StopRequired && controller.dirty() && !controller.pending());
            const auto directStop = reply(store.compareExchangePreferences(storage::newUuid(), preferenceKey, 1, 0,
                storage::canonical(encodePreferences(Level::Developer)), false));
            check("actual store enforces STOP_REQUIRED", directStop.status == storage::Status::DefiniteFailure &&
                  directStop.code == "STOP_REQUIRED");
            check("explicit stopped save dispatched", controller.canSave(true) && controller.save(true));
            const auto operation = controller.pendingOperationId();
            check("in-flight write retains operation and prohibits detach/write", !operation.empty() &&
                  !controller.canDetach() && !controller.save(true) && !controller.detach());
            settle(controller);
            check("confirmed save advances actual revision", controller.state() == PreferenceState::Ready &&
                  controller.observedRevision() == 1 && controller.pendingOperationId().empty() &&
                  storedBytes(store) == storage::canonical(encodePreferences(Level::Advanced)));
            controller.choosePage(Page::Learn, Level::Developer);
            check("page override never marks saved global dirty", !controller.dirty() && !controller.pending() &&
                  controller.model().effectiveLevel(Page::Learn) == Level::Developer);

            timingBytes = storage::canonical(metronome::encodePreferences(metronome::Preferences{}));
            const auto timing = reply(store.compareExchangePreferences(storage::newUuid(), "freeplay_timing", 1, 0, timingBytes, true));
            check("composed validator preserves existing timing owner", timing.status == storage::Status::Confirmed &&
                  composedPreferenceValidator("freeplay_timing", 1, metronome::encodePreferences(metronome::Preferences{})) &&
                  !composedPreferenceValidator("arbitrary", 1, encodePreferences(Level::Developer)));
            controller.chooseGlobal(Level::Developer);
            const auto elsewhere = reply(store.compareExchangePreferences(storage::newUuid(), preferenceKey, 1, 1,
                storage::canonical(encodePreferences(Level::Beginner)), true));
            check("independent actual writer changes revision", elsewhere.status == storage::Status::Confirmed);
            check("stale observed revision attempts guarded CAS", controller.save(true));
            settle(controller);
            check("CAS conflict preserves choice without overwrite/retry", controller.state() == PreferenceState::Conflict &&
                  controller.model().globalLevel() == Level::Developer && !controller.canSave(true) &&
                  controller.pendingOperationId().empty() && storedBytes(store) == storage::canonical(encodePreferences(Level::Beginner)));
            check("explicit reload accepted", controller.reload());
            settle(controller);
            check("reload adopts actual stored global and retains page override", controller.model().globalLevel() == Level::Beginner &&
                  controller.observedRevision() == 2 && controller.model().effectiveLevel(Page::Learn) == Level::Developer);
            controller.resetPresentation();
            check("reset clears session override without touching timing", !controller.model().pageOverride(Page::Learn) &&
                  !controller.model().pageOverride(Page::Practice) && storedBytes(store, "freeplay_timing") == timingBytes);
            controller.chooseGlobal(Level::Advanced);
            controller.save(true);
            settle(controller);
            controller.resetPresentation();
            check("reset remains dirty until explicit save", controller.dirty() && !controller.pending() &&
                  storedBytes(store) == storage::canonical(encodePreferences(Level::Advanced)));
            controller.save(true);
            settle(controller);
            check("explicit reset persisted only global, preserving timing bytes", storedBytes(store) == storage::canonical(encodePreferences(Level::Beginner)) &&
                  storedBytes(store, "freeplay_timing") == timingBytes);
            check("definite state releases profile", controller.detach());
        }
        config.create = false;
        {
            storage::ProfileStore reopened(config);
            controller.attach(reopened, firstIdentity);
            settle(controller);
            check("normal same-profile reopen loads persisted global", controller.model().globalLevel() == Level::Beginner &&
                  controller.observedRevision() == 4 && !controller.model().pageOverride(Page::Learn) &&
                  storedBytes(reopened, "freeplay_timing") == timingBytes);
            controller.chooseGlobal(Level::Developer);
            controller.save(true);
            settle(controller);
            controller.choosePage(Page::Practice, Level::Advanced);
            controller.detach();
        }
        {
            storage::ProfileStore other(options(root / "second"));
            const auto otherIdentity = profileIdentity(other);
            controller.attach(other, otherIdentity);
            settle(controller);
            check("profile isolation clears former global and page choice", otherIdentity != firstIdentity &&
                  controller.profileIdentity() == otherIdentity && controller.model().globalLevel() == Level::Beginner &&
                  !controller.model().pageOverride(Page::Practice) && controller.observedRevision() == 0);
            controller.detach();
        }
        check("detach clears profile disclosure and permits session choices", !controller.hasProfile() &&
              controller.model().globalLevel() == Level::Beginner && controller.state() == PreferenceState::NoProfile);

        // Hold one actual writer transaction so the read stays queued. A newer
        // explicit UI choice must survive an earlier Reload's acknowledgment.
        auto queuedConfig = options(root / "queued-read");
        std::atomic<bool> holdWriter{false};
        std::promise<void> releaseWriter;
        const auto writerRelease = releaseWriter.get_future().share();
        queuedConfig.diagnosticHook = [&](const std::string& phase, const std::string&) {
            if (phase == "before_commit" && holdWriter.load()) writerRelease.wait();
        };
        {
            storage::ProfileStore queued(queuedConfig);
            const auto identity = profileIdentity(queued);
            check("seed current choice before controlled queued read", reply(queued.compareExchangePreferences(storage::newUuid(), preferenceKey,
                  1, 0, storage::canonical(encodePreferences(Level::Beginner)), true)).status == storage::Status::Confirmed);
            controller.attach(queued, identity);
            settle(controller);
            holdWriter.store(true);
            auto ahead = queued.compareExchangePreferences(storage::newUuid(), "freeplay_timing", 1, 0, timingBytes, true);
            check("earlier reload queued before latest global choice", controller.reload());
            controller.chooseGlobal(Level::Developer);
            releaseWriter.set_value();
            check("controlled earlier transaction completes", reply(std::move(ahead)).status == storage::Status::Confirmed);
            settle(controller);
            check("late read cannot overwrite newer explicit global choice", controller.model().globalLevel() == Level::Developer &&
                  controller.dirty() && controller.observedRevision() == 1 &&
                  storedBytes(queued) == storage::canonical(encodePreferences(Level::Beginner)));
            controller.detach();
        }

        // Seed incompatible bytes through an explicitly synthetic semantic owner;
        // the production composed owner must preserve and refuse them on reopen.
        auto futureConfig = options(root / "unsupported");
        futureConfig.preferenceValidator = [](const auto& key, auto version, const auto&) {
            return key == preferenceKey && version == 2;
        };
        const auto futureBytes = storage::canonical(O{{"version", "presentation-future-synthetic"}, {"global_level", "developer"}});
        {
            storage::ProfileStore seed(futureConfig);
            check("isolated incompatible future seed", reply(seed.compareExchangePreferences(storage::newUuid(), preferenceKey, 2, 0,
                  futureBytes, true)).status == storage::Status::Confirmed);
        }
        futureConfig.create = false;
        futureConfig.preferenceValidator = composedPreferenceValidator;
        {
            storage::ProfileStore current(futureConfig);
            controller.attach(current, profileIdentity(current));
            settle(controller);
            controller.chooseGlobal(Level::Advanced);
            check("unsupported data retained and no overwrite offered", controller.state() == PreferenceState::Unsupported &&
                  !controller.canSave(true) && !controller.save(true) && storedBytes(current) == futureBytes);
            controller.detach();
        }

        // Controlled post-commit acknowledgment loss exercises real store debt.
        auto unknownConfig = options(root / "unknown");
        bool loseAcknowledgment = true;
        unknownConfig.diagnosticHook = [&](const std::string& phase, const std::string&) {
            if (phase == "after_commit" && loseAcknowledgment) {
                loseAcknowledgment = false;
                throw std::runtime_error("synthetic acknowledgment loss");
            }
        };
        {
            storage::ProfileStore uncertain(unknownConfig);
            controller.attach(uncertain, profileIdentity(uncertain));
            settle(controller);
            controller.chooseGlobal(Level::Advanced);
            controller.save(true);
            const auto originalOperation = controller.pendingOperationId();
            const auto originalBytes = controller.pendingBytes();
            settle(controller);
            check("unknown actual write retains original identity and exact bytes", controller.state() == PreferenceState::Unknown &&
                  controller.pendingOperationId() == originalOperation && controller.pendingBytes() == originalBytes &&
                  !controller.canDetach() && !controller.detach() && !controller.canSave(true) && !controller.save(true));
            controller.chooseGlobal(Level::Developer);
            check("new memory choice cannot replace unknown write debt", controller.pendingOperationId() == originalOperation &&
                  controller.pendingBytes() == originalBytes && !controller.canSave(true));
            check("explicit original inspection dispatches read", controller.reload());
            settle(controller);
            check("exact next-revision inspection resolves stored value without guessed write", controller.pendingOperationId().empty() &&
                  controller.observedRevision() == 1 && controller.model().globalLevel() == Level::Developer && controller.dirty() &&
                  controller.statusText().find("Which operation saved it is not established") != std::string::npos &&
                  storedBytes(uncertain) == originalBytes && controller.canDetach());
            controller.detach();
        }

        // If a subsequent writer moved past the unknown proposal, the store has
        // no operation journal with which to prove its original history. Keep the
        // same debt; do not invent a successful reconciliation or a retry route.
        auto differingConfig = options(root / "unknown-differing");
        bool loseDifferingAcknowledgment = true;
        differingConfig.diagnosticHook = [&](const std::string& phase, const std::string&) {
            if (phase == "after_commit" && loseDifferingAcknowledgment) {
                loseDifferingAcknowledgment = false;
                throw std::runtime_error("synthetic differing acknowledgment loss");
            }
        };
        {
            storage::ProfileStore uncertain(differingConfig);
            PreferencesController retained;
            retained.attach(uncertain, profileIdentity(uncertain));
            settle(retained);
            retained.chooseGlobal(Level::Advanced);
            retained.save(true);
            const auto originalOperation = retained.pendingOperationId();
            const auto originalBytes = retained.pendingBytes();
            settle(retained);
            check("isolated later writer advances past unknown proposal", reply(uncertain.compareExchangePreferences(storage::newUuid(),
                  preferenceKey, 1, 1, storage::canonical(encodePreferences(Level::Beginner)), true)).status == storage::Status::Confirmed);
            retained.reload();
            settle(retained);
            check("differing inspection preserves original debt and refuses guessed retry", retained.state() == PreferenceState::Unknown &&
                  retained.pendingOperationId() == originalOperation && retained.pendingBytes() == originalBytes &&
                  !retained.canDetach() && !retained.detach() && !retained.save(true));
        }

        std::ofstream output(argv[2]);
        output << storage::canonical(O{{"classification", "isolated synthetic presentation preferences; software-only, no GUI/listening/release claim"},
            {"checks", checks}, {"failures", V::fromInteger(failures)}}) << '\n';
        if (!output) throw std::runtime_error("Cannot write result JSON");
        return failures ? 1 : 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
