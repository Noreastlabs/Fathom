#include "desktop/ProgressPresentation.hpp"
#include "desktop/LessonSetupNotice.hpp"
#include "platform/PracticePlayback.hpp"
#include "practice/LessonAttempt.hpp"
#include "progression/SelectedCaseComparison.hpp"
#include "practice_capture_fixtures.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <set>
#include <thread>

using namespace fathom;
namespace {
using V = json::Value;
int checks{};
void check(bool good, const char* label) {
    ++checks;
    if (!good) throw std::runtime_error(label);
}
const V& at(const V& value, const char* key) { return value.object().at(key); }
storage::Reply confirmed(storage::ProfileStore::Future future) {
    auto reply = future.get();
    if (reply.status != storage::Status::Confirmed) throw std::runtime_error(reply.code + ": " + reply.message);
    return reply;
}
template<class Predicate> void until(capture::PracticeSession& capture, const std::string& utc,
                                     Predicate predicate) {
    const auto end = capture_fixture::now() + 6000;
    while (!predicate()) {
        if (capture_fixture::now() > end) throw std::runtime_error("Six-second capture watchdog");
        capture.poll(capture_fixture::now(), utc);
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}
void drive(platform::PracticePlayback& player, practice::Coordinator& coordinator) {
    const auto owner = coordinator.owner();
    output::Snapshot output;
    output.owner = owner;
    output.request.epoch = owner.epoch;
    output.state = output::State::Running;
    auto buffers = std::make_unique<platform::Buses>();
    std::uint64_t submitted{};
    bool terminal{};
    for (int blocks = 0; blocks < 2000 && !terminal; ++blocks) {
        platform::PracticePlayback::observe(&player, output);
        practice::Progress progress;
        while (player.nextProgress(progress)) coordinator.progress(progress);
        scheduler::Fact fact;
        while (player.nextFact(fact)) {}
        *buffers = {};
        const auto rendered = platform::PracticePlayback::render(&player, owner,
            coordinator.configuration().rate, 256, *buffers);
        check(rendered.valid && (rendered.submittedFrames || rendered.terminal), "finite software playback");
        submitted += rendered.submittedFrames;
        output.submittedFrames = submitted;
        if (rendered.terminal) {
            terminal = true;
            output.state = output::State::Unresolved;
            output.uncertainThrough = submitted;
        }
        platform::PracticePlayback::observe(&player, output);
        while (player.nextProgress(progress)) coordinator.progress(progress);
        while (player.nextFact(fact)) {}
    }
    check(terminal, "software selected target terminated");
    practice::Progress retired;
    check(player.reclaim(retired), "terminal provider evidence retired");
}
void saveClean(storage::ProfileStore& store, const lesson::Admission& admission,
               const std::string& session, const std::string& utc, int bpm,
               const guitar::Setup& setup, std::vector<std::string>& originals) {
    const auto cfg = admission.practiceConfiguration(8000, static_cast<std::uint16_t>(bpm));
    auto request = capture::lessonStart(admission, cfg, session, utc, "UTC", 1);
    request.binding.context.object().at("configuration").object()["declared_instrument_setup"] =
        desktop::declaredSetupValue(setup);
    practice::Coordinator coordinator;
    capture::PracticeSession capture(store, coordinator);
    check(capture.start(std::move(request), 1, capture_fixture::now()), "typed Start allocated");
    until(capture, utc, [&] { return capture.phase() == capture::SessionPhase::Ready; });
    const auto owner = capture.takeStart(capture_fixture::now());
    check(owner.has_value(), "initial checkpoint acknowledged before sound");
    platform::PracticePlayback player;
    check(player.prepareLesson(admission,
        admission.referenceConfiguration(*owner, 1, cfg.rate, cfg.bpm), coordinator, 1),
        "typed current admission prepared");
    drive(player, coordinator);
    capture.poll(capture_fixture::now(), utc);
    check(capture.phase() == capture::SessionPhase::Review, "completed target reached Review");
    check(capture.save(V("Clean"), capture::Outcome::Natural, capture_fixture::now()),
          "explicit Clean self-report Save");
    until(capture, utc, [&] { return capture.phase() == capture::SessionPhase::Saved; });
    until(capture, utc, [&] { return capture.canLeave(true); });
    check(capture.original().has_value(), "finalized original retained");
    originals.push_back(capture.original()->bytes);
}
std::size_t rows(const V& projection) {
    std::size_t n{};
    for (const auto& group : at(projection, "groups").array()) n += at(group, "rows").array().size();
    return n;
}
V mutate(const V& source, const std::function<void(V&)>& edit) {
    auto copy = source;
    edit(copy);
    return copy;
}
}
int main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::runtime_error("Expected installed Resources and fresh absolute evidence root");
        const std::filesystem::path resources = argv[1], root = argv[2];
        check(root.is_absolute() && !std::filesystem::exists(root), "fresh private test root");
        std::filesystem::create_directories(root);
        std::filesystem::permissions(root, std::filesystem::perms::owner_all,
                                     std::filesystem::perm_options::replace);
        std::vector<std::filesystem::path> extensions;
        for (const auto& name : lesson::Catalog::installedExtensionDirectoryNames())
            extensions.push_back(resources / name);
        const auto catalog = lesson::Catalog::loadInstalled(resources / "representative-controls", extensions);
        check(catalog->lessons().size() == 50 && catalog->sourceEntryCount() == 188,
              "prior cases plus exact Level25 first cell installed");
        for(const char* variant : {"fg:variant:007474", "fg:variant:007475"}) {
            const auto level25 = catalog->admit("fg:item:001176", variant);
            check(level25 && level25->practiceAllowed()
                && level25->identity().object().at("whole_task_completion") == V(false),
                "Level25 D/U selected cell is admitted without whole-task credit");
        }
        const auto admission = catalog->admit("fg:item:001141", "fg:variant:007404");
        check(admission && admission->practiceAllowed(), "current Rung02 selected case admitted");
        storage::StoreOptions options;
        options.path = root / "profile.sqlite";
        options.create = true;
        options.createdUtc = "2026-09-20T00:00:00Z";
        auto store = std::make_unique<storage::ProfileStore>(options);
        const auto firstSession = confirmed(store->createSession("comparison-session-1",
            "2026-09-20T10:00:00Z", "UTC", {},
            V::Object{{"synthetic_fixture", true}, {"purpose", "disposable installed comparison proof"}})).owner;
        const auto secondSession = confirmed(store->createSession("comparison-session-2",
            "2026-09-21T10:00:00Z", "UTC", {},
            V::Object{{"synthetic_fixture", true}, {"purpose", "disposable installed comparison proof"}})).owner;
        const std::array<int, 4> tempos{80,84,84,84};
        const std::array<std::string, 4> stamps{"2026-09-20T10:00:00Z", "2026-09-20T11:00:00Z",
            "2026-09-21T10:00:00Z", "2026-09-21T11:00:00Z"};
        std::vector<std::string> originals;
        guitar::Setup standard;
        for (std::size_t i = 0; i < 4; ++i) {
            saveClean(*store, *admission, i < 2 ? firstSession : secondSession,
                stamps[i], tempos[i], standard, originals);
            const auto reply = confirmed(store->snapshot("comparison-snapshot-" + std::to_string(i)));
            const auto shown = desktop::presentProgress(reply, "2026-09-24T00:00:00Z", catalog);
            const auto& display = at(shown.projection, "selected_case_tempo_display");
            check(rows(display) == i + 1, "one more confirmed comparison row after Save");
            const auto& group = at(display, "groups").array().at(0);
            const auto& row = at(group, "rows").array().back();
            check(at(row, "clean_pb_bpm") == V::fromInteger(i == 0 ? 80 : 84),
                  "running saved Clean PB 80 to 84");
            const V expectedReliable = i < 2 ? V{} : V::fromInteger(i == 2 ? 80 : 84);
            check(at(row, "reliable_bpm") == expectedReliable,
                  "three-Attempt two-day two-Session reliability threshold");
            check(shown.text.find("No source-verified completed module") != std::string::npos
                && shown.text.find("Source-rule assessment unavailable") != std::string::npos,
                "visible source-rule/module boundary remains honest");
            check(at(reply.data, "authoritative") == at(confirmed(store->snapshot(
                "comparison-readonly-" + std::to_string(i))).data, "authoritative"),
                "Progress did not write authoritative Store tables");
        }
        const auto four = confirmed(store->snapshot("comparison-four"));
        const auto evidence = progression::adaptSnapshot(four);
        check(evidence.records.size() == 4 && at(at(four.data, "authoritative"),
            "source_attestation").array().empty(), "no source completion or fabricated attestation");
        std::multiset<std::string> actualOriginals;
        for (const auto& record : evidence.records) actualOriginals.insert(record.originalBytes);
        check(actualOriginals == std::multiset<std::string>(originals.begin(), originals.end()),
              "all four earlier finalized originals remain byte-identical after later Saves");
        for (std::size_t i = 0; i < originals.size(); ++i) {
            check(storage::validateEnvelope(originals[i]).kind == "Attempt",
                  "earlier finalized original remains valid");
        }
        const auto displayedFour = desktop::presentProgress(four, "2026-09-24T00:00:00Z", catalog);
        for (const auto& view : at(displayedFour.projection, "views").array()) {
            const auto& rule = at(view, "projection");
            check(at(rule, "source_complete") == V(false)
                && at(rule, "state") != V("Proficient") && at(rule, "state") != V("Mastered"),
                "selected-case comparison does not earn source or mastery credit");
        }
        auto extraKind = evidence;
        progression::Evidence freeplay;
        freeplay.kind = progression::Kind::Freeplay;
        freeplay.key = storage::newUuid();
        extraKind.records.push_back(freeplay);
        check(rows(progression::projectSelectedCaseComparison(extraKind, *catalog,
            "2026-09-24T00:00:00Z")) == 4, "Freeplay record cannot enter selected-case comparison");
        const auto& original = evidence.records.front();
        const auto originalEnvelope = storage::parseCanonical(original.originalBytes);
        auto reject = [&](const std::function<void(V&)>& edit, const char* label) {
            auto altered = evidence;
            auto changed = mutate(originalEnvelope, edit);
            altered.records.front().originalBytes = storage::canonical(changed);
            const auto projection = progression::projectSelectedCaseComparison(altered, *catalog,
                "2026-09-24T00:00:00Z");
            check(rows(projection) == 3 && !at(projection, "unavailable").array().empty(), label);
        };
        reject([](V& v) { auto& c = v.object().at("context").object().at("configuration").object();
            c.erase("declared_instrument_setup"); v.object().at("result").object()["configuration"] = c;
        }, "missing declaration refused");
        reject([](V& v) { auto& c = v.object().at("context").object().at("configuration").object();
            c.at("declared_instrument_setup").object()["physical_tuning_verified"] = true;
            v.object().at("result").object()["configuration"] = c;
        }, "unsupported physical verification refused");
        reject([](V& v) { auto& c = v.object().at("context").object().at("configuration").object();
            c.at("declared_instrument_setup").object()["value_version"] = "unknown-historical-version";
            v.object().at("result").object()["configuration"] = c;
        }, "unsupported historical setup version refused");
        reject([](V& v) { auto& c = v.object().at("context").object().at("configuration").object();
            c["lesson_tempo"] = V::Object{}; v.object().at("result").object()["configuration"] = c;
        }, "present initial ramp refused even if unadvanced");
        reject([](V& v) { v.object().at("result").object().at("tempo_segments").array()[0]
            .object()["tempo"] = V::Array{V::fromInteger(81),V::fromInteger(1)};
        }, "mixed tempo refused");
        reject([](V& v) { v.object().at("result").object().at("tempo_segments").array()[0]
            .object()["start_at"] = V::Array{V::fromInteger(1),V::fromInteger(1)};
        }, "gapped tempo refused");
        reject([](V& v) { v.object().at("result").object().at("completed_cycles").array().clear();
        }, "incomplete selected target refused");
        reject([](V& v) { v.object().at("result").object()["assessment"] = nullptr;
        }, "missing Clean/Easy self-report refused");
        reject([](V& v) { v.object().at("context").object()["content_version"] = "superseded";
        }, "changed admission version refused");
        reject([](V& v) { auto& c = v.object().at("context").object().at("configuration").object();
            c["source_hashes"] = V::Object{{"foreign", std::string(64, 'a')}};
            v.object().at("result").object()["configuration"] = c;
        }, "changed source hash refused");
        reject([](V& v) { auto& c = v.object().at("context").object().at("configuration").object();
            c.at("runtime_admission").object()["selection"] = V::Object{{"version", "lesson-transfer-cell.1"},
                {"ordinal", V::fromInteger(1)}};
            v.object().at("result").object()["configuration"] = c;
        }, "foreign selected-cell ordinal refused");
        reject([](V& v) { v.object().at("context").object().at("span").object()["end"] =
            V::Array{V::fromInteger(999),V::fromInteger(1)};
        }, "changed selected span refused");
        guitar::Setup drop = standard;
        drop.openMidi[0] = 38;
        saveClean(*store, *admission, secondSession, "2026-09-21T12:00:00Z", 90, drop, originals);
        const auto changed = confirmed(store->snapshot("comparison-drop-d"));
        const auto separate = progression::projectSelectedCaseComparison(
            progression::adaptSnapshot(changed), *catalog, "2026-09-24T00:00:00Z");
        check(at(separate, "groups").array().size() == 2 && rows(separate) == 5,
              "different declared tuning forms a separate comparison key");
        guitar::Setup capo = standard;
        capo.capo = 2;
        saveClean(*store, *admission, secondSession, "2026-09-21T13:00:00Z", 92, capo, originals);
        const auto capoSnapshot = confirmed(store->snapshot("comparison-capo"));
        const auto separatedCapo = progression::projectSelectedCaseComparison(
            progression::adaptSnapshot(capoSnapshot), *catalog, "2026-09-24T00:00:00Z");
        check(at(separatedCapo, "groups").array().size() == 3 && rows(separatedCapo) == 6,
              "different declared capo forms a separate comparison key");
        const auto pendingRoot = root / "uncommitted";
        std::filesystem::create_directories(pendingRoot);
        std::filesystem::permissions(pendingRoot, std::filesystem::perms::owner_all,
                                     std::filesystem::perm_options::replace);
        storage::StoreOptions pendingOptions = options;
        pendingOptions.path = pendingRoot / "profile.sqlite";
        storage::ProfileStore pendingStore(pendingOptions);
        const auto pendingSession = confirmed(pendingStore.createSession("comparison-pending-session",
            "2026-09-21T14:00:00Z", "UTC")).owner;
        const auto config = admission->practiceConfiguration(8000, 96);
        auto pending = capture::lessonStart(*admission, config, pendingSession,
            "2026-09-21T14:00:00Z", "UTC", 1);
        pending.binding.context.object().at("configuration").object()["declared_instrument_setup"] =
            desktop::declaredSetupValue(standard);
        confirmed(pendingStore.allocate("comparison-uncommitted", "Attempt", pending.binding.context,
            pending.binding.practiceUtc));
        const auto withPending = confirmed(pendingStore.snapshot("comparison-uncommitted-snapshot"));
        check(rows(progression::projectSelectedCaseComparison(progression::adaptSnapshot(withPending),
            *catalog, "2026-09-24T00:00:00Z")) == 0,
            "uncommitted allocation cannot enter selected-case comparison");
        const auto cleanBeforeReopen = confirmed(store->snapshot("comparison-clean-before-reopen"));
        store.reset(); options.create = false;
        store = std::make_unique<storage::ProfileStore>(options);
        const auto reopened = confirmed(store->snapshot("comparison-reopened"));
        check(at(reopened.data, "authoritative") == at(cleanBeforeReopen.data, "authoritative"),
              "reopen retains exactly the same authoritative data");
        std::ofstream(root / "projection.json") << storage::canonical(separatedCapo);
        std::ofstream(root / "presentation.txt") << desktop::presentProgress(capoSnapshot,
            "2026-09-24T00:00:00Z", catalog).text;
        std::cout << "PASS " << checks << " selected-case comparison checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << ": " << error.what() << '\n';
        return 1;
    }
}
