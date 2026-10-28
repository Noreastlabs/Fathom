// Actual Home/Store/presentation; synthetic device leaf only. No native trials.
#include "practice/AttemptCapture.hpp"
#include "practice/LessonAttempt.hpp"
#define main retained_settings_campaign_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include "content/Canonical.hpp"
#include "read_only_text_peer_checks.hpp"

#include <map>
#include <set>
#include <iomanip>
#include <sstream>
#include <sys/stat.h>

namespace {
using V = json::Value;
using O = V::Object;
using Array = V::Array;
const std::string asOf = "2026-09-13T00:00:00Z";
const V& field(const V& value, const std::string& key) { return value.object().at(key); }
V& member(V& value, const std::string& key) { return value.object().at(key); }
std::string readFile(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("Missing input " + path.string());
    return std::string(std::istreambuf_iterator<char>(in), {});
}
V blob(const std::string& bytes) {
    constexpr char hex[] = "0123456789abcdef";
    std::string out;
    for (unsigned char c : bytes) { out += hex[c >> 4]; out += hex[c & 15]; }
    return O{{"blob_hex", out}};
}
void rehash(storage::Reply& reply) {
    auto authority = field(reply.data, "authoritative");
    member(reply.data, "snapshot_sha256") = content::sha256(storage::canonical(authority));
    authority.object().erase("rule_observation");
    member(reply.data, "evidence_sha256") = content::sha256(storage::canonical(authority));
}
// Coherently rebuild only synthetic in-memory snapshot rows, never original files.
void replaceOriginal(storage::Reply& reply, V original) {
    const auto owner = field(original, "owner");
    const auto bytes = storage::canonical(original);
    storage::validateEnvelope(bytes);
    auto& authority = member(reply.data, "authoritative");
    for (auto& row : member(authority, "identity").array())
        if (row.array()[0] == owner) row.array()[4] = blob(storage::canonical(field(original, "context")));
    for (auto& row : member(authority, "finalized").array())
        if (row.array()[0] == owner) { row.array()[1] = blob(bytes); row.array()[2] = content::sha256(bytes); }
    rehash(reply);
}
void choose(desktop::LessonView& view, int level) {
    const std::string item = level == 3 ? "fg:item:000002" : "fg:item:000003";
    const std::string variant = level == 3 ? "fg:variant:000006" : "fg:variant:000029";
    const auto& lessons = view.catalog()->lessons();
    auto lesson = std::find_if(lessons.begin(), lessons.end(), [&](const auto& x) { return x.id == item; });
    if (lesson == lessons.end()) throw std::runtime_error("Missing accepted lesson");
    auto* a = dynamic_cast<juce::ComboBox*>(view.findChildWithID("lessons"));
    auto* b = dynamic_cast<juce::ComboBox*>(view.findChildWithID("variants"));
    if (!a || !b) throw std::runtime_error("Missing lesson controls");
    a->setSelectedItemIndex(static_cast<int>(lesson - lessons.begin()), juce::sendNotificationSync);
    auto v = std::find_if(lesson->variants.begin(), lesson->variants.end(), [&](const auto& x) { return x.id == variant; });
    if (v == lesson->variants.end()) throw std::runtime_error("Missing accepted variant");
    b->setSelectedItemIndex(static_cast<int>(v - lesson->variants.begin()), juce::sendNotificationSync);
}
void ready(Harness& h) {
    click(h.practice(), "Audio settings"); h.tick();
    if (h.home->audioSettings().snapshot().state == output::State::Closed) {
        click(A::settings(*h.home), "Connect audio"); h.tick();
        click(A::settings(*h.home), "Enable audio"); h.blocks(1);
    }
    click(A::settings(*h.home), "Back to Practice"); h.tick(); h.tick();
}
void beginPartial(Harness& h) {
    click(h.practice(), "Start selected case");
    h.wait([&] { return h.practice().captureSession()->startTaken(); }, "source initial checkpoint");
    h.blocks(35); click(h.practice(), "Stop & review result"); h.blocks(2);
    h.wait([&] { return h.practice().captureSession()->phase() == capture::SessionPhase::Review; }, "source partial Review");
}
void finishSave(Harness& h) {
    h.wait([&] { return h.practice().captureSession()->phase() == capture::SessionPhase::Saved; }, "saved original");
    h.blocks(2); h.wait([&] { return h.practice().audioCanRelease(); }, "saved output release");
}
void refreshed(Harness& h) { h.wait([&] { return !A::progress(*h.home).busy(); }, "Progress read"); }
std::size_t views(const desktop::ProgressPresentation& p) { return field(p.projection, "views").array().size(); }
std::size_t originals(const desktop::ProgressPresentation& p) { return field(p.projection, "original_history").array().size(); }
void savePresentation(const std::filesystem::path& dir, const std::string& name, const desktop::ProgressPresentation& p) {
    capture_fixture::write(dir / (name + ".txt"), p.text);
    capture_fixture::write(dir / (name + ".json"), p.details);
}
scheduler::Owner ownerFor(const std::string& id) {
    storage::validateUuid(id);
    scheduler::Owner owner;
    std::string compact;
    for (const auto c : id) if (c != '-') compact += c;
    for (std::size_t i = 0; i < owner.id.size(); ++i)
        owner.id[i] = static_cast<std::uint8_t>(std::stoul(compact.substr(i * 2, 2), nullptr, 16));
    owner.generation = 1;
    owner.epoch = 1;
    return owner;
}
void beginAttempt(practice::Coordinator& coordinator, const capture::Binding& binding,
                  const practice::Configuration& configuration) {
    coordinator.begin(ownerFor(binding.owner), practice::Kind::Attempt,
                      storage::canonical(binding.context), configuration);
}
practice::Progress seededProgress(const practice::Coordinator& coordinator,
                                  std::uint64_t requestedCycles) {
    const auto& timeline = coordinator.timeline(coordinator.owner());
    const auto acceptedThrough = timeline.frame(requestedCycles);
    const auto introFrame = timeline.frame(0);
    const auto completedCycles = timeline.completed(acceptedThrough);
    const auto cycleAnchor = timeline.frame(completedCycles);
    practice::Progress progress;
    progress.owner = coordinator.owner();
    progress.sequence = 1;
    progress.clientAcceptedThrough = acceptedThrough;
    progress.scheduledThrough = acceptedThrough;
    progress.uncertainThrough = acceptedThrough;
    progress.activeFrames = acceptedThrough > introFrame ? acceptedThrough - introFrame : 0;
    progress.completedCycles = completedCycles;
    progress.cursorFrames = acceptedThrough > cycleAnchor ? acceptedThrough - cycleAnchor : 0;
    progress.requestedStopNs = 987654321;
    progress.state = practice::State::Ended;
    progress.terminal = true;
    progress.partial = progress.cursorFrames != 0;
    return progress;
}
std::string seedSession(storage::ProfileStore& store, const std::string& prefix,
                        const std::string& at) {
    const auto created = capture_fixture::confirmed(store.createSession(
        prefix + ".session-create", at, "America/New_York", 600,
        O{{"version", "seeded-progress.1"}, {"purpose", "deterministic Progress reconciliation"}}));
    return created.owner;
}
void seedAttempt(storage::ProfileStore& store, const std::string& prefix,
                 const std::string& at, int bpm, std::uint64_t completedCycles,
                 const std::string& assessment, const std::string& sessionEnd,
                 const std::string& item="fg:item:000001",const std::string& variant="fg:variant:000001") {
    const auto session = seedSession(store, prefix, at);
    auto request = capture_fixture::request(session);
    member(request.binding.context,"item_id")=item;
    member(request.binding.context,"variant_id")=variant;
    auto& sourceConfiguration=member(request.binding.context,"configuration");
    member(sourceConfiguration,"canonical_variant_id")=variant;
    member(member(sourceConfiguration,"progression_condition"),"variant")=variant;
    request.binding.practiceUtc = at;
    request.configuration.bpm = static_cast<std::uint16_t>(bpm);
    member(member(member(request.binding.context, "configuration"), "values"), "selected_bpm") = V::fromInteger(bpm);
    const auto allocation = capture_fixture::confirmed(store.allocate(
        prefix + ".attempt-allocate", request.binding.kind, request.binding.context, at));
    request.binding.owner = allocation.owner;
    practice::Coordinator coordinator;
    beginAttempt(coordinator, request.binding, request.configuration);
    const auto accepted = seededProgress(coordinator, completedCycles);
    if (!coordinator.progress(accepted)) throw std::runtime_error("Seeded Attempt progress was refused");
    const auto original = capture::makeEnvelope(coordinator, request.binding, V(assessment), capture::Outcome::Stop);
    capture_fixture::confirmed(store.seal(prefix + ".attempt-seal", original.owner, original.bytes));
    capture_fixture::confirmed(store.commit(prefix + ".attempt-commit", original.owner, original.bytes));
    capture_fixture::confirmed(store.closeSession(prefix + ".session-close", session, sessionEnd,
                                                   completedCycles == 2 ? "complete" : "partial"));
}
void seedFreeplay(storage::ProfileStore& store, const std::string& prefix,
                  const std::string& at, const std::string& sessionEnd) {
    (void)sessionEnd;
    auto request = capture_fixture::request("", true);
    request.binding.practiceUtc = at;
    const auto allocation = capture_fixture::confirmed(store.allocate(
        prefix + ".freeplay-allocate", request.binding.kind, request.binding.context, at));
    request.binding.owner = allocation.owner;
    practice::Coordinator coordinator;
    coordinator.begin(ownerFor(request.binding.owner), practice::Kind::Freeplay,
                      storage::canonical(request.binding.context), request.configuration);
    const auto accepted = seededProgress(coordinator, request.configuration.targetCycles);
    if (!coordinator.progress(accepted)) throw std::runtime_error("Seeded Freeplay progress was refused");
    const auto original = capture::makeEnvelope(coordinator, request.binding, V{}, capture::Outcome::Stop);
    capture_fixture::confirmed(store.seal(prefix + ".freeplay-seal", original.owner, original.bytes));
    capture_fixture::confirmed(store.commit(prefix + ".freeplay-commit", original.owner, original.bytes));
}
std::string displayedSeconds(const Rational& value) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(3) << value.displayValue();
    return out.str();
}
std::vector<std::string> sectionRows(const std::string& text, const std::string& heading,
                                     const std::string& nextHeading) {
    const auto start = text.find(heading);
    if (start == std::string::npos || text.find(heading, start + heading.size()) != std::string::npos)
        throw std::runtime_error("Missing or repeated Progress section: " + heading);
    const auto end = text.find(nextHeading, start + heading.size());
    if (end == std::string::npos) throw std::runtime_error("Missing Progress section boundary: " + nextHeading);
    std::istringstream in(text.substr(start + heading.size(), end - start - heading.size()));
    std::vector<std::string> rows;
    for (std::string line; std::getline(in, line); ) if (!line.empty()) rows.push_back(line);
    return rows;
}
}

int main(int argc, char** argv) {
    int count = 0; std::ofstream log;
    try {
        const bool uxOnly = argc == 5 && std::string(argv[4]) == "--ux";
        const bool refreshGuidanceOnly = argc == 5 && std::string(argv[4]) == "--refresh-guidance-only";
        const bool backGuidanceOnly = argc == 5 && std::string(argv[4]) == "--back-guidance-only";
        const bool learnGuidanceOnly = argc == 5 && std::string(argv[4]) == "--learn-guidance-only";
        const bool audioGuidanceOnly = argc == 5 && std::string(argv[4]) == "--audio-guidance-only";
        const bool controlContractOnly = argc == 5 && std::string(argv[4]) == "--control-contract";
        const bool audioControlOnly = argc == 5 && std::string(argv[4]) == "--audio-control-contract";
        const bool readOnlySurfaceOnly = argc == 5 && std::string(argv[4]) == "--read-only-surface";
        const bool progressResponsiveOnly = argc == 5 && std::string(argv[4]) == "--progress-responsive-layout";
        const bool guidedProvenanceOnly = argc == 5 && std::string(argv[4]) == "--guided-progress-provenance";
        const bool savedBackIdentityOnly = argc == 5 && std::string(argv[4]) == "--saved-back-identity";
        const bool seededHistoryOnly = argc == 5 && std::string(argv[4]) == "--seeded-history-reconciliation";
        const bool weeklyActivityOnly = argc == 5 && std::string(argv[4]) == "--weekly-activity";
        const bool selectedScopeHistoryOnly = argc == 5 && std::string(argv[4]) == "--selected-scope-history";
        if (argc != 4 && !uxOnly && !refreshGuidanceOnly && !backGuidanceOnly && !learnGuidanceOnly && !audioGuidanceOnly && !controlContractOnly && !audioControlOnly && !readOnlySurfaceOnly && !progressResponsiveOnly && !guidedProvenanceOnly && !savedBackIdentityOnly && !seededHistoryOnly && !weeklyActivityOnly && !selectedScopeHistoryOnly) throw std::runtime_error("Absolute accepted bundle, frozen native directory and new evidence directory required");
        const std::filesystem::path bundle = argv[1], native = argv[2], dir = argv[3];
        if (!bundle.is_absolute() || !native.is_absolute() || !dir.is_absolute() || std::filesystem::exists(dir))
            throw std::runtime_error("New absolute output directory required");
        std::filesystem::create_directories(dir); std::filesystem::permissions(dir, std::filesystem::perms::owner_all, std::filesystem::perm_options::replace); ::chmod(dir.c_str(), 0700); log.open(dir / "checks.tsv");
        juce::ScopedJuceInitialiser_GUI gui;
        const auto catalog = lesson::Catalog::load(bundle);
        auto ck = [&](bool okay, const std::string& name) {
            log << ++count << '\t' << name << '\t' << (okay ? "PASS" : "FAIL") << std::endl;
            if (!okay) throw std::runtime_error(name);
        };
        auto rejected = [&](auto fn, const std::string& name) {
            bool threw = false; try { fn(); } catch (const std::exception&) { threw = true; }
            ck(threw, name);
        };
        if(selectedScopeHistoryOnly){
            // Fresh synthetic Store plus detached Progress component only.
            // The native-history argument is deliberately never read in this mode.
            storage::StoreOptions options;options.path=dir/"profile.sqlite";options.create=true;
            options.createdUtc="2026-08-17T00:00:00Z";options.preferenceValidator=metronome::preferenceValidator;
            storage::ProfileStore store(options);
            ck(std::none_of(catalog->lessons().begin(),catalog->lessons().end(),[](const auto& item){return item.id=="fg:item:001141";}),
               "prepared catalog explicitly lacks the saved extension owner used by this fixture");
            const auto empty=capture_fixture::confirmed(store.snapshot("selected-scope-empty"));
            const auto emptyView=desktop::presentProgress(empty,asOf,catalog);
            ck(emptyView.text.find("Currently prepared verified scope:")!=std::string::npos
               &&emptyView.text.find("remain discoverable in Learn")!=std::string::npos,
               "empty Progress labels only its prepared scope and preserves full-library discovery");
            seedAttempt(store,"selected-scope-outside-owner","2026-09-01T16:00:00Z",120,2,"Clean","2026-09-01T16:10:00Z","fg:item:001141","fg:variant:007404");
            seedFreeplay(store,"selected-scope-freeplay","2026-09-02T16:00:00Z","2026-09-02T16:10:00Z");
            const auto before=capture_fixture::confirmed(store.snapshot("selected-scope-before"));
            const auto withScope=desktop::presentProgress(before,asOf,catalog);
            const auto withoutScope=desktop::presentProgress(before,asOf);
            ck(originals(withScope)==2&&field(withScope.projection,"original_history")==field(withoutScope.projection,"original_history"),
               "saved Attempt and Freeplay originals survive a catalog that lacks the saved owner");
            ck(withScope.text.find("Saved source fg:item:001141 / fg:variant:007404")!=std::string::npos
               &&withScope.text.find("current lesson title not verified")!=std::string::npos,
               "unprepared saved owner retains exact historical IDs without borrowing a current title");
            ck(withScope.text.find("Freeplay activity")!=std::string::npos
               &&withScope.text.find("Selected passes do not establish source-task completion.")!=std::string::npos,
               "partial prepared scope retains separate Freeplay and no-completion boundaries");
            desktop::ProgressView view;view.setSize(920,680);view.setVisible(true);view.setCatalog(catalog);
            ck(view.getPeer()==nullptr&&view.bind(store,[]{return asOf;})&&view.refresh(),"detached Progress reads only the owned synthetic Store");
            const auto wait=[&]{const auto end=capture_fixture::now()+7000;while(view.busy()){view.service();pump();if(capture_fixture::now()>end)throw std::runtime_error("selected-scope Progress read watchdog");}};
            wait();ck(view.presentation().text==withScope.text&&view.presentation().details==withScope.details,"visible scoped Progress agrees with confirmed historical facts");
            view.setCatalog({});ck(view.refresh(),"clear optional current catalog without changing history");wait();
            ck(originals(view.presentation())==2&&view.presentation().text.find("fg:item:001141 / fg:variant:007404")!=std::string::npos,
               "removing current models leaves both saved originals visible");
            const auto after=capture_fixture::confirmed(store.snapshot("selected-scope-after"));
            ck(field(before.data,"authoritative")==field(after.data,"authoritative"),"Progress reads create no new Session, Attempt, Freeplay or credit facts");
            ck(view.getPeer()==nullptr&&nativeOpens==0&&connections==0&&view.detach(),"component QA uses no desktop peer, audio connection or native output");
            savePresentation(dir,"prepared-scope-history",withScope);
            capture_fixture::write(dir/"summary.json",storage::canonical(O{{"status","PASS"},{"checks",V::fromInteger(count)},{"mode","--selected-scope-history"},{"synthetic_fixtures_only",true},{"saved_originals",V::fromInteger(2)},{"native_GUI",false},{"physical_listening",false},{"learner_credit",false}}));
            std::cout<<"PASS "<<count<<" selected-scope history checks\n";return 0;
        }
        if (weeklyActivityOnly) {
            storage::StoreOptions options;
            options.path = dir / "profile.sqlite";
            options.create = true;
            options.createdUtc = "2025-12-30T00:00:00Z";
            options.preferenceValidator = metronome::preferenceValidator;
            auto store = std::make_unique<storage::ProfileStore>(options);
            const auto empty = capture_fixture::confirmed(store->snapshot("weekly-empty"));
            const auto emptyView = desktop::presentProgress(empty, asOf, catalog);
            ck(originals(emptyView) == 0
                   && emptyView.text.find("No finalized local practice weeks.") != std::string::npos
                   && emptyView.text.find("Weekly recorded activity (local Monday-Sunday; finalized records only; not mastery, a score, streak or curriculum credit):") != std::string::npos,
               "Empty profile has no invented weekly activity or success claim");

            seedAttempt(*store, "weekly-dec31", "2025-12-31T16:00:00Z", 120, 2, "Clean", "2025-12-31T16:10:00Z");
            seedAttempt(*store, "weekly-jan01-a", "2026-01-01T16:00:00Z", 120, 2, "Clean", "2026-01-01T16:10:00Z");
            seedAttempt(*store, "weekly-jan01-b", "2026-01-01T18:00:00Z", 120, 2, "Clean", "2026-01-01T18:10:00Z");
            seedFreeplay(*store, "weekly-jan01-freeplay", "2026-01-01T20:00:00Z", "2026-01-01T20:10:00Z");
            seedFreeplay(*store, "weekly-jan05-freeplay", "2026-01-05T16:00:00Z", "2026-01-05T16:10:00Z");
            const auto before = capture_fixture::confirmed(store->snapshot("weekly-seeded-before-view"));
            const auto expected = desktop::presentProgress(before, asOf, catalog);
            ck(originals(expected) == 5
                   && field(field(before.data, "authoritative"), "session").array().size() == 3
                   && field(field(before.data, "authoritative"), "finalized").array().size() == 5,
               "Three saved Attempts and two separate Freeplay originals are authoritative");
            ck(expected.text.find("2025-12-29 to 2026-01-04 | Practice dates: 2 | Attempts: 3 | Freeplay: 1") != std::string::npos
                   && expected.text.find("2026-01-05 to 2026-01-11 | Practice dates: 1 | Attempts: 0 | Freeplay: 1") != std::string::npos,
               "Local Monday-Sunday buckets cross the year boundary and separate Attempt and Freeplay counts");
            ck(expected.text.find("2026-01-01 | Attempts: 2") != std::string::npos
                   && expected.text.find("2026-01-01 | Attempts: 2 (", expected.text.find("Activity by local practice day:")) != std::string::npos
                   && expected.text.find("Practice dates: 3 distinct local dates") != std::string::npos,
               "Repeated same-day Attempt and mixed Freeplay activity count as one local practice date");
            ck(expected.text.find("not mastery, a score, streak or curriculum credit") != std::string::npos
                   && expected.text.find("Domain coverage: not computed") != std::string::npos
                   && expected.text.find("Freeplay is separate from curriculum progression.") != std::string::npos,
               "Weekly facts do not infer mastery, domain coverage, module completion or curriculum credit");
            savePresentation(dir, "weekly-seeded", expected);

            desktop::ProgressView view;
            view.setSize(920, 680); view.setVisible(true); view.setCatalog(catalog);
            ck(view.bind(*store, [] { return asOf; }) && view.refresh(), "Progress reads the seeded weekly profile");
            const auto readDeadline = capture_fixture::now() + 7000;
            while (view.busy()) {
                view.service(); pump();
                if (capture_fixture::now() > readDeadline) throw std::runtime_error("weekly Progress read watchdog");
            }
            ck(view.presentation().text == expected.text && view.presentation().details == expected.details,
               "Visible Progress agrees with the confirmed Store projection");
            const auto after = capture_fixture::confirmed(store->snapshot("weekly-seeded-after-view"));
            ck(field(before.data, "authoritative") == field(after.data, "authoritative"),
               "Weekly presentation writes no Session, Attempt or Freeplay facts");
            ck(view.detach(), "Progress detaches before ordinary same-profile reopen");
            store.reset(); options.create = false; store = std::make_unique<storage::ProfileStore>(options);
            ck(view.bind(*store, [] { return asOf; }) && view.refresh(), "Progress reattaches to the same profile after reopen");
            const auto reopenDeadline = capture_fixture::now() + 7000;
            while (view.busy()) {
                view.service(); pump();
                if (capture_fixture::now() > reopenDeadline) throw std::runtime_error("weekly reopen watchdog");
            }
            const auto reopened = capture_fixture::confirmed(store->snapshot("weekly-after-reopen"));
            ck(field(before.data, "authoritative") == field(reopened.data, "authoritative")
                   && view.presentation().text == expected.text && view.presentation().details == expected.details,
               "Same-profile reopen retains exact weekly facts and authoritative originals");
            savePresentation(dir, "weekly-reopened", view.presentation());
            capture_fixture::write(dir / "summary.json", storage::canonical(O{
                {"status", "PASS"}, {"checks", V::fromInteger(count)}, {"as_of", asOf},
                {"attempts", V::fromInteger(3)}, {"freeplay_activities", V::fromInteger(2)},
                {"distinct_local_dates", V::fromInteger(3)}, {"calendar_weeks", V::fromInteger(2)},
                {"domain_coverage", "not computed"}}));
            std::cout << "PASS " << count << " factual weekly Progress checks\n";
            return 0;
        }
        if (seededHistoryOnly) {
            storage::StoreOptions options;
            options.path = dir / "profile.sqlite";
            options.create = true;
            options.createdUtc = "2026-08-17T00:00:00Z";
            options.preferenceValidator = metronome::preferenceValidator;
            auto store = std::make_unique<storage::ProfileStore>(options);
            seedFreeplay(*store, "seed-0818-freeplay", "2026-08-18T16:00:00Z", "2026-08-18T16:10:00Z");
            seedFreeplay(*store, "seed-0827-freeplay", "2026-08-27T16:00:00Z", "2026-08-27T16:10:00Z");
            seedAttempt(*store, "seed-0901", "2026-09-01T16:00:00Z", 120, 2, "Clean", "2026-09-01T16:10:00Z");
            seedAttempt(*store, "seed-0904", "2026-09-04T16:00:00Z", 120, 2, "Clean", "2026-09-04T16:10:00Z");
            seedAttempt(*store, "seed-0905", "2026-09-05T16:00:00Z", 120, 2, "Clean", "2026-09-05T16:10:00Z");
            seedAttempt(*store, "seed-0909", "2026-09-09T16:00:00Z", 140, 1, "Developing", "2026-09-09T16:10:00Z");
            seedFreeplay(*store, "seed-0910-freeplay", "2026-09-10T16:00:00Z", "2026-09-10T16:10:00Z");

            const auto before = capture_fixture::confirmed(store->snapshot("seeded-history-before-view"));
            const auto expected = desktop::presentProgress(before, asOf, catalog);
            const auto& authority = field(before.data, "authoritative");
            ck(field(authority, "session").array().size() == 4
                   && field(authority, "finalized").array().size() == 7
                   && originals(expected) == 7 && views(expected) == 1,
               "Seeded authoritative profile has four Sessions, four Attempts, three distinct FreeplayActivity records and one exact query");
            const auto& rule = field(field(expected.projection, "views").array()[0], "projection");
            std::int64_t positiveCount{}, successCount{};
            ck(field(rule, "positive_count").integer(positiveCount) && positiveCount == 4
                   && field(rule, "success_count").integer(successCount) && successCount == 3
                   && field(rule, "state") == V("Proficient")
                   && progression::quantity(field(rule, "attempted_maximum")) == Rational{140}
                   && progression::quantity(field(rule, "pb")) == Rational{120}
                   && progression::quantity(field(rule, "reliable")) == Rational{120}
                   && field(rule, "review_due") == V(true)
                   && field(rule, "due_at").string().find("2026-09-12") == 0,
               "Repeated same-condition evidence reconciles Proficient, attempted maximum 140, clean PB/reliable tempo 120 and due review");
            ck(expected.text.find("Attempts: 4 in 4 recorded Session(s) | active time: 13.714 s") != std::string::npos
                   && expected.text.find("Freeplay activities: 3 | active time: 12.000 s") != std::string::npos
                   && expected.text.find("Practice dates: 7 distinct local dates") != std::string::npos
                   && expected.text.find("2026-09-09 | Attempts: 1") != std::string::npos
                   && expected.text.find("2026-09-10 | Attempts: 0") != std::string::npos,
               "Visible totals and local-day history reconcile to stored Attempt and separate Freeplay active time");
            const std::map<std::string, std::pair<std::string, Rational>> exactActive{
                {"2026-08-18", {"FreeplayActivity", Rational{4}}},
                {"2026-08-27", {"FreeplayActivity", Rational{4}}},
                {"2026-09-01", {"Attempt", Rational{4}}},
                {"2026-09-04", {"Attempt", Rational{4}}},
                {"2026-09-05", {"Attempt", Rational{4}}},
                // At 8 kHz the accepted end minus the rounded intro frame is 13,715 frames.
                {"2026-09-09", {"Attempt", Rational{13715, 8000}}},
                {"2026-09-10", {"FreeplayActivity", Rational{4}}},
            };
            std::set<std::string> observedDays;
            for (const auto& original : progression::adaptSnapshot(before).originalHistory) {
                const auto envelope = storage::validateEnvelope(field(original, "bytes").string());
                const auto expectedDay = exactActive.find(envelope.day);
                ck(expectedDay != exactActive.end() && observedDays.insert(envelope.day).second
                       && field(original, "kind") == V(expectedDay->second.first)
                       && envelope.active == expectedDay->second.second,
                   "Confirmed original has the seeded local day, kind and rational active duration: " + envelope.day);
            }
            ck(observedDays.size() == exactActive.size(), "All seven expected local days occur exactly once in the confirmed snapshot");
            const std::vector<std::string> exactDays{
                "2026-08-18 | Attempts: 0 (0.000 s) | Freeplay: 1 (" + displayedSeconds(Rational{4}) + " s)",
                "2026-08-27 | Attempts: 0 (0.000 s) | Freeplay: 1 (" + displayedSeconds(Rational{4}) + " s)",
                "2026-09-01 | Attempts: 1 (" + displayedSeconds(Rational{4}) + " s) | Freeplay: 0 (0.000 s)",
                "2026-09-04 | Attempts: 1 (" + displayedSeconds(Rational{4}) + " s) | Freeplay: 0 (0.000 s)",
                "2026-09-05 | Attempts: 1 (" + displayedSeconds(Rational{4}) + " s) | Freeplay: 0 (0.000 s)",
                "2026-09-09 | Attempts: 1 (" + displayedSeconds(Rational{13715, 8000}) + " s) | Freeplay: 0 (0.000 s)",
                "2026-09-10 | Attempts: 0 (0.000 s) | Freeplay: 1 (" + displayedSeconds(Rational{4}) + " s)",
            };
            const std::vector<std::string> exactWeeks{
                "2026-08-17 to 2026-08-23 | Practice dates: 1 | Attempts: 0 | Freeplay: 1",
                "2026-08-24 to 2026-08-30 | Practice dates: 1 | Attempts: 0 | Freeplay: 1",
                "2026-08-31 to 2026-09-06 | Practice dates: 3 | Attempts: 3 | Freeplay: 0",
                "2026-09-07 to 2026-09-13 | Practice dates: 2 | Attempts: 1 | Freeplay: 1",
            };
            const auto dayRows = [&](const std::string& text) {
                return sectionRows(text, "Activity by local practice day:\n", "Weekly recorded activity (");
            };
            const auto weekRows = [&](const std::string& text) {
                const auto rows = sectionRows(text, "Weekly recorded activity (local Monday-Sunday; finalized records only; not mastery, a score, streak or curriculum credit):\n", "Domain coverage:");
                return rows;
            };
            ck(dayRows(expected.text) == exactDays, "All seven exact local-day rows reconcile counts and rational-derived displayed seconds");
            ck(weekRows(expected.text) == exactWeeks && exactWeeks.size() == 4,
               "All four exact local Monday-Sunday week rows reconcile distinct dates and activity counts");
            auto mismatchedDays = exactDays;
            mismatchedDays[5].replace(mismatchedDays[5].find("1.714 s"), 7, "1.715 s");
            ck(dayRows(expected.text) != mismatchedDays, "Exact-row oracle detects a deliberately mismatched 140-BPM duration");
            ck(expected.text.find("Attempted maximum (including incomplete attempt evidence): 140.000 BPM") != std::string::npos
                   && expected.text.find("Clean PB: 120.000 | Reliable tempo: 120.000") != std::string::npos
                   && expected.text.find("Review date: 2026-09-12T16:00:00Z | due as of this snapshot") != std::string::npos
                   && expected.text.find("Recent lower self-report: Developing (self-report)") != std::string::npos
                   && expected.text.find("Self-assessment: Clean (self-report)") != std::string::npos
                   && expected.text.find("Domain coverage: not computed") != std::string::npos
                   && expected.text.find("Freeplay is separate from curriculum progression.") != std::string::npos,
               "Progress explains PB versus attempted maximum, review date, labeled self-report and uncomputed domain boundary");
            savePresentation(dir, "seeded-history", expected);

            desktop::ProgressView view;
            view.setSize(920, 680); view.setVisible(true); view.setCatalog(catalog);
            ck(view.bind(*store, [] { return asOf; }) && view.refresh(), "Progress attaches to the seeded local profile and reads the fixed as-of snapshot");
            const auto readDeadline = capture_fixture::now() + 7000;
            while (view.busy()) {
                view.service(); pump();
                if (capture_fixture::now() > readDeadline) throw std::runtime_error("seeded Progress read watchdog");
            }
            ck(view.presentation().details == expected.details && view.presentation().text == expected.text,
               "Visible ProgressView matches independently presented confirmed seeded snapshot");
            ck(dayRows(view.presentation().text) == exactDays && weekRows(view.presentation().text) == exactWeeks,
               "Visible ProgressView renders every exact seeded day and week row");
            {
                fathom::test::ReadingPeerScope peer(view);view.toFront(true);pump();
                auto* body=dynamic_cast<juce::TextEditor*>(view.findChildWithID("progress-body"));
                auto* details=dynamic_cast<juce::TextButton*>(view.findChildWithID("progress-details"));
                ck(view.getPeer()!=nullptr&&view.isShowing()&&body&&details&&details->isEnabled(),
                   "Confirmed populated Progress has a visible peer, body and enabled details control");
                const auto savedStatus=view.statusText();
                details->grabKeyboardFocus();
                ck(juce::Component::getCurrentlyFocusedComponent()==details
                   &&view.getPeer()->handleKeyPress(juce::KeyPress{juce::KeyPress::tabKey})
                   &&juce::Component::getCurrentlyFocusedComponent()==body,
                   "Peer Tab reaches the populated Progress body from Details without opening details");
                fathom::test::readingKeys(view,*body,expected.text,ck);
                ck(!view.busy()&&view.statusText()==savedStatus&&view.presentation().text==expected.text
                   &&view.presentation().details==expected.details,
                   "Reading saved Progress changes no projection, status, disclosure state or pending read");
            }
            const auto afterReading=capture_fixture::confirmed(store->snapshot("seeded-after-reading-keys"));
            ck(field(before.data,"authoritative")==field(afterReading.data,"authoritative")
               &&field(before.data,"profile_id")==field(afterReading.data,"profile_id")
               &&field(before.data,"snapshot_sha256")==field(afterReading.data,"snapshot_sha256")
               &&field(before.data,"evidence_sha256")==field(afterReading.data,"evidence_sha256"),
               "Populated Progress reading keys create no authoritative Session, Attempt, Freeplay or profile change");
            const auto beforeDetails = capture_fixture::confirmed(store->snapshot("seeded-before-details"));
            click(view, "Show saved details");
            auto* body = dynamic_cast<juce::TextEditor*>(view.findChildWithID("progress-body"));
            ck(body && body->isReadOnly() && body->getText().toStdString() == expected.details,
               "Expanded Progress details show retained projection JSON in a read-only editor");
            const auto afterDetails = capture_fixture::confirmed(store->snapshot("seeded-after-details"));
            ck(field(beforeDetails.data, "authoritative") == field(afterDetails.data, "authoritative"),
               "Expanding saved history changes no authoritative Session, Attempt or Freeplay facts");
            click(view, "Hide saved details");
            ck(body->getText().toStdString() == expected.text,
               "Collapsing saved details returns to the factual Progress history view");

            ck(view.detach(), "Progress detaches before ordinary same-profile Store reopen");
            store.reset(); options.create = false;
            store = std::make_unique<storage::ProfileStore>(options);
            ck(view.bind(*store, [] { return asOf; }) && view.refresh(), "Progress reattaches to the same profile after Store reopen");
            const auto reopenDeadline = capture_fixture::now() + 7000;
            while (view.busy()) {
                view.service(); pump();
                if (capture_fixture::now() > reopenDeadline) throw std::runtime_error("same-profile reopen watchdog");
            }
            const auto reopened = capture_fixture::confirmed(store->snapshot("seeded-after-reopen"));
            ck(field(before.data, "authoritative") == field(reopened.data, "authoritative")
                   && field(before.data, "profile_id") == field(reopened.data, "profile_id")
                   && field(before.data, "snapshot_sha256") == field(reopened.data, "snapshot_sha256")
                   && field(before.data, "evidence_sha256") == field(reopened.data, "evidence_sha256")
                   && view.presentation().details == expected.details
                   && view.presentation().text == expected.text
                   && dayRows(view.presentation().text) == exactDays
                   && weekRows(view.presentation().text) == exactWeeks,
               "Fresh same-profile Store reopen preserves exact authoritative history and computed projection");
            savePresentation(dir, "seeded-history-reopened", view.presentation());

            const auto foreignDir = dir / "foreign-empty";
            std::filesystem::create_directories(foreignDir);
            std::filesystem::permissions(foreignDir, std::filesystem::perms::owner_all,
                                         std::filesystem::perm_options::replace);
            if (::chmod(foreignDir.c_str(), 0700) != 0)
                throw std::runtime_error("Could not enforce user-only foreign profile directory permissions");
            storage::StoreOptions foreignOptions;
            foreignOptions.path = foreignDir / "profile.sqlite";
            foreignOptions.create = true;
            foreignOptions.createdUtc = "2026-09-13T00:00:00Z";
            foreignOptions.preferenceValidator = metronome::preferenceValidator;
            auto foreign = std::make_unique<storage::ProfileStore>(foreignOptions);
            const auto foreignSnapshot = capture_fixture::confirmed(foreign->snapshot("foreign-empty-snapshot"));
            const auto foreignPresentation = desktop::presentProgress(foreignSnapshot, asOf, catalog);
            ck(field(field(foreignSnapshot.data, "authoritative"), "session").array().empty()
                   && field(field(foreignSnapshot.data, "authoritative"), "finalized").array().empty()
                   && originals(foreignPresentation) == 0
                   && foreignPresentation.text.find("No finalized practice activity in this snapshot.") != std::string::npos
                   && foreignPresentation.text.find("seed-0901") == std::string::npos,
               "Separate empty profile presents no borrowed Session, Attempt or Freeplay history");
            ck(view.bind(*foreign, [] { return asOf; }) && view.refresh(), "Existing Progress view probes a foreign empty profile");
            const auto foreignDeadline = capture_fixture::now() + 7000;
            while (view.busy()) {
                view.service(); pump();
                if (capture_fixture::now() > foreignDeadline) throw std::runtime_error("foreign-profile guard watchdog");
            }
            ck(view.presentation().details == expected.details
                   && view.statusText().find("not the original attached profile") != std::string::npos,
               "Foreign profile identity is refused while the dated original snapshot remains attached");
            ck(view.bind(*store, [] { return asOf; }) && view.refresh(), "Progress restores the original local-profile attachment");
            const auto restoreDeadline = capture_fixture::now() + 7000;
            while (view.busy()) {
                view.service(); pump();
                if (capture_fixture::now() > restoreDeadline) throw std::runtime_error("original-profile restore watchdog");
            }
            const auto finalSnapshot = capture_fixture::confirmed(store->snapshot("seeded-after-foreign-probe"));
            ck(field(before.data, "authoritative") == field(finalSnapshot.data, "authoritative")
                   && field(before.data, "profile_id") == field(finalSnapshot.data, "profile_id")
                   && field(before.data, "snapshot_sha256") == field(finalSnapshot.data, "snapshot_sha256")
                   && field(before.data, "evidence_sha256") == field(finalSnapshot.data, "evidence_sha256")
                   && view.presentation().details == expected.details
                   && view.presentation().text == expected.text,
               "Foreign-profile refusal and original-profile restore leave the seeded authoritative snapshot unchanged");
            capture_fixture::write(dir / "summary.json", storage::canonical(O{
                {"status", "PASS"}, {"checks", V::fromInteger(count)}, {"as_of", asOf},
                {"sessions", V::fromInteger(4)}, {"attempts", V::fromInteger(4)},
                {"freeplay_activities", V::fromInteger(3)}, {"distinct_local_dates", V::fromInteger(7)},
                {"calendar_weeks", V::fromInteger(4)}, {"attempted_maximum_bpm", V::fromInteger(140)},
                {"clean_pb_bpm", V::fromInteger(120)}, {"reliable_bpm", V::fromInteger(120)},
                {"profile_id", field(before.data, "profile_id")},
                {"snapshot_sha256", field(before.data, "snapshot_sha256")},
                {"evidence_sha256", field(before.data, "evidence_sha256")},
                {"review_due", true}, {"domain_coverage", "not computed; no accepted Progress mapping"}}));
            std::cout << "PASS " << count << " seeded Progress history reconciliation checks\n";
            return 0;
        }
        if (progressResponsiveOnly) {
            desktop::ProgressView compact; compact.setSize(640, 680); compact.setVisible(true); compact.resized();
            const auto bounds = compact.getLocalBounds();
            const char* visibleIds[] = {"progress-status", "progress-empty-state", "progress-empty-next-action", "progress-body", "progress-back", "progress-refresh", "progress-reopen", "progress-learn", "progress-audio-settings", "progress-details"};
            for (const auto* id : visibleIds) {
                auto* component = compact.findChildWithID(id);
                ck(component && component->isVisible() && bounds.contains(component->getBounds()) && component->getWidth() > 0 && component->getHeight() > 0,
                   std::string("Compact Progress surface remains visible and contained: ") + id);
            }
            const char* actions[] = {"progress-back", "progress-refresh", "progress-reopen", "progress-learn", "progress-audio-settings", "progress-details"};
            for (std::size_t leftIndex = 0; leftIndex < std::size(actions); ++leftIndex)
                for (std::size_t rightIndex = leftIndex + 1; rightIndex < std::size(actions); ++rightIndex) {
                    const auto* left = compact.findChildWithID(actions[leftIndex]);
                    const auto* right = compact.findChildWithID(actions[rightIndex]);
                    ck(left && right && !left->getBounds().intersects(right->getBounds()),
                       std::string("Compact Progress actions do not overlap: ") + actions[leftIndex] + "/" + actions[rightIndex]);
                }
            const std::pair<const char*, const char*> labels[] = {{"progress-back", "Back"}, {"progress-refresh", "Refresh"}, {"progress-reopen", "Reopen profile"}, {"progress-learn", "Choose practice in Learn"}, {"progress-audio-settings", "Audio settings"}, {"progress-details", "Show saved details"}};
            for (const auto& expected : labels) {
                const auto* button = dynamic_cast<const juce::TextButton*>(compact.findChildWithID(expected.first));
                ck(button && button->getButtonText().toStdString() == expected.second,
                   std::string("Compact Progress preserves label: ") + expected.first);
            }
            const auto* status = dynamic_cast<const juce::Label*>(compact.findChildWithID("progress-status"));
            const auto* emptyState = dynamic_cast<const juce::Label*>(compact.findChildWithID("progress-empty-state"));
            const auto* body = dynamic_cast<const juce::TextEditor*>(compact.findChildWithID("progress-body"));
            const auto* compactTitle = dynamic_cast<const juce::Label*>(compact.getChildComponent(0));
            const auto compactCaption = juce::String::fromUTF8("Progress — Saved local activity");
            const auto standardCaption = juce::String::fromUTF8("PROGRESS — SAVED LOCAL ACTIVITY");
            ck(compactTitle && compactTitle->getText() == compactCaption,
               "Compact Progress preserves the exact Unicode saved-activity heading");
            compact.setSize(799, 680); compact.resized();
            ck(compactTitle && compactTitle->getText() == compactCaption,
               "Progress preserves the exact compact Unicode heading below the 800px boundary");
            compact.setSize(800, 680); compact.resized();
            ck(compactTitle && compactTitle->getText() == standardCaption,
               "Progress restores the exact standard Unicode heading at the 800px boundary");
            compact.setSize(799, 680); compact.resized();
            ck(compactTitle && compactTitle->getText() == compactCaption,
               "Progress restores the exact compact Unicode heading after crossing back below 800px");
            ck(compact.presentation().projection.null() && !compact.busy(),
               "Progress heading boundary changes leave the snapshot empty without a pending read");
            compact.setSize(640, 680); compact.resized();
            ck(compact.presentation().projection.null() && !compact.busy() && status && body
                   && status->getText().toStdString().find("Opening Progress never creates activity.") != std::string::npos
                   && body->getText().toStdString().find("No Progress snapshot is loaded yet.") != std::string::npos
                   && body->getText().toStdString().find("Progress is read-only and does not create activity or curriculum credit.") != std::string::npos,
               "Compact Progress opens with an honest empty read-only snapshot and no pending read");
            ck(emptyState && emptyState->getText().toStdString() == "No saved activity loaded yet"
                   && emptyState->getTitle().toStdString() == "Progress empty-state heading."
                   && emptyState->getBounds().getBottom() <= body->getY(),
               "Compact Progress exposes a contained empty-state heading without changing the read-only body");
            const auto* emptyNextAction = dynamic_cast<const juce::Label*>(compact.findChildWithID("progress-empty-next-action"));
            ck(emptyNextAction && emptyNextAction->isVisible()
                   && emptyNextAction->getText().toStdString() == "Choose an admitted case in Learn, save a Practice result, then review it here."
                   && emptyNextAction->getTitle().toStdString() == "Progress empty-state next action."
                   && emptyState->getBounds().getBottom() <= emptyNextAction->getY()
                   && emptyNextAction->getBounds().getBottom() <= body->getY(),
               "Compact Progress gives the empty read-only state a contained Learn-to-Save next action");
            desktop::ProgressView standard; standard.setSize(920, 680); standard.setVisible(true); standard.resized();
            const auto* standardTitle = dynamic_cast<const juce::Label*>(standard.getChildComponent(0));
            ck(standardTitle && standardTitle->getText() == standardCaption,
               "Standard Progress restores the exact Unicode saved-activity heading");
            ck(standard.findChildWithID("progress-back")->getBounds().getX() == 792
                   && standard.findChildWithID("progress-back")->getBounds().getWidth() == 100
                   && standard.findChildWithID("progress-refresh")->getBounds().getX() == 28,
               "Standard Progress geometry remains unchanged at 920x680");
            std::ofstream(dir / "summary.json") << "{\"checks\":" << count << ",\"status\":\"PASS\",\"projectionEmpty\":true,\"profileRead\":false,\"activityCreated\":false}\n";
            std::cout << "PASS " << count << " Compact Progress responsive layout checks\n";
            return 0;
        }
        if (audioControlOnly) {
            desktop::AudioOutputView detached; detached.setSize(920, 680); detached.setVisible(true);
            juce::Label* title = nullptr;
            for (auto* child : detached.getChildren())
                if (auto* label = dynamic_cast<juce::Label*>(child); label && label->getText().toStdString() == "AUDIO — SHARED OUTPUT SETTINGS") { title = label; break; }
            ck(title && title->getText().toStdString() == "AUDIO — SHARED OUTPUT SETTINGS", "Audio heading identifies shared output settings");
            auto* connectColor = dynamic_cast<juce::TextButton*>(detached.findChildWithID("audio-connect"));
            ck(connectColor && connectColor->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                   && connectColor->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                   && connectColor->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c},
               "Audio Connect uses the primary teal presentation while preserving the existing control contract");
            auto* enableColor = dynamic_cast<juce::TextButton*>(detached.findChildWithID("audio-enable"));
            ck(enableColor && enableColor->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                   && enableColor->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                   && enableColor->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c},
               "Audio Enable uses the primary teal presentation while preserving the existing control contract");
            auto* disconnectColor = dynamic_cast<juce::TextButton*>(detached.findChildWithID("audio-disconnect"));
            ck(disconnectColor && disconnectColor->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                   && disconnectColor->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                   && disconnectColor->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c},
               "Audio Disconnect uses the primary teal presentation while preserving the existing control contract");
            auto* backColor = dynamic_cast<juce::TextButton*>(detached.findChildWithID("audio-back"));
            ck(backColor && backColor->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                   && backColor->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                   && backColor->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c},
               "Audio Back uses the primary teal presentation while preserving the existing control contract");
            const char* muteIds[] = {"audio-master-mute", "audio-reference-mute", "audio-metronome-mute", "audio-rhythm-a-mute", "audio-rhythm-b-mute"};
            bool mutePresentation = true;
            for (const auto* id : muteIds) {
                auto* mute = dynamic_cast<juce::Button*>(detached.findChildWithID(id));
                mutePresentation = mutePresentation && mute
                    && mute->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                    && mute->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                    && mute->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c};
            }
            ck(mutePresentation, "Audio mute controls use the primary teal presentation while preserving the existing control contract");
            const char* soloIds[] = {"audio-rhythm-a-solo", "audio-rhythm-b-solo"};
            bool soloPresentation = true;
            for (const auto* id : soloIds) {
                auto* solo = dynamic_cast<juce::Button*>(detached.findChildWithID(id));
                soloPresentation = soloPresentation && solo
                    && solo->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                    && solo->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                    && solo->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c};
            }
            ck(soloPresentation, "Audio Rhythm solo controls use the primary teal presentation while preserving the existing control contract");
            const char* gainIds[] = {"audio-master-volume", "audio-reference-volume", "audio-metronome-volume", "audio-rhythm-a-volume", "audio-rhythm-b-volume"};
            bool gainPresentation = true;
            for (const auto* id : gainIds) {
                auto* gain = dynamic_cast<juce::Slider*>(detached.findChildWithID(id));
                gainPresentation = gainPresentation && gain
                    && gain->findColour(juce::Slider::thumbColourId) == juce::Colour{0xff6bd5cb}
                    && gain->findColour(juce::Slider::trackColourId) == juce::Colour{0xff6bd5cb}
                    && gain->findColour(juce::Slider::backgroundColourId) == juce::Colour{0xff10212c};
            }
            ck(gainPresentation, "Audio gain sliders use the primary presentation while preserving the existing control contract");
            struct ControlContract { const char* id; const char* label; const char* title; int order; bool button; };
            const ControlContract controls[] = {
                {"audio-connect", "Connect audio", "Connect shared macOS audio output.", 1, true},
                {"audio-enable", "Enable audio", "Enable observed shared macOS audio output.", 2, true},
                {"audio-disconnect", "Disconnect", "Disconnect shared audio when current activity is safely releasable.", 3, true},
                {"audio-master-volume", "", "Master volume", 4, false},
                {"audio-master-mute", "Mute", "Master mute", 5, true},
                {"audio-reference-volume", "", "Reference volume", 6, false},
                {"audio-reference-mute", "Mute", "Reference mute", 7, true},
                {"audio-metronome-volume", "", "Metronome volume", 8, false},
                {"audio-metronome-mute", "Mute", "Metronome mute", 9, true},
                {"audio-rhythm-a-volume", "", "Rhythm A volume", 10, false},
                {"audio-rhythm-a-mute", "Mute", "Rhythm A mute", 11, true},
                {"audio-rhythm-a-solo", "Solo", "Rhythm A solo", 12, true},
                {"audio-rhythm-b-volume", "", "Rhythm B volume", 13, false},
                {"audio-rhythm-b-mute", "Mute", "Rhythm B mute", 14, true},
                {"audio-rhythm-b-solo", "Solo", "Rhythm B solo", 15, true},
                {"audio-back", "Back", "Return to the calling activity without changing shared Audio settings.", 16, true}
            };
            for (const auto& contract : controls) {
                auto* component = detached.findChildWithID(contract.id);
                ck(component != nullptr, std::string("Audio control exists: ") + contract.id);
                if (!component) continue;
                ck(component->getTitle().toStdString() == contract.title, std::string("Audio control title: ") + contract.id);
                ck(component->getExplicitFocusOrder() == contract.order, std::string("Audio control focus order: ") + contract.id);
                ck(component->getWantsKeyboardFocus() == component->isEnabled(), std::string("Audio control focusability preserves enabled-state boundary: ") + contract.id);
                if (contract.button) {
                    auto* button = dynamic_cast<juce::Button*>(component);
                    ck(button && button->getButtonText().toStdString() == contract.label, std::string("Audio button label preserved: ") + contract.id);
                } else {
                    ck(dynamic_cast<juce::Slider*>(component) != nullptr, std::string("Audio gain control type preserved: ") + contract.id);
                }
            }
            auto* status = dynamic_cast<juce::Label*>(detached.findChildWithID("shared-audio-status"));
            ck(status && status->getText().toStdString() == "Audio settings awaits its playback view.", "detached Audio status states the missing playback view without fabricating output");
            std::cout << "PASS " << count << " Audio control checks; no native output or Store\n";
            return 0;
        }
        if (readOnlySurfaceOnly) {
            desktop::ProgressView detached; detached.setSize(920, 680); detached.setVisible(true);
            juce::Label* title = nullptr;
            for (auto* child : detached.getChildren())
                if (auto* label = dynamic_cast<juce::Label*>(child); label && label->getTitle().toStdString() == "Read-only Progress: saved local activity and separate Freeplay history; no curriculum credit.") { title = label; break; }
            auto* status = dynamic_cast<juce::Label*>(detached.findChildWithID("progress-status"));
            auto* body = dynamic_cast<juce::TextEditor*>(detached.findChildWithID("progress-body"));
            ck(title && title->getText().toStdString() == "PROGRESS — SAVED LOCAL ACTIVITY"
                   && title->getTitle().toStdString() == "Read-only Progress: saved local activity and separate Freeplay history; no curriculum credit."
                   && title->isVisible() && detached.getLocalBounds().contains(title->getBounds()),
               "Progress heading exposes its visible label, stable boundary title and contained layout");
            ck(status && status->getTitle().toStdString() == "Read-only Progress status and next action."
                   && status->getText().toStdString().find("Opening Progress never creates activity.") != std::string::npos
                   && status->getText().toStdString().find("Attach a local profile to view saved practice.") != std::string::npos,
               "Progress exposes a stable truthful read-only status identity and initial guidance");
            ck(body && body->getTitle().toStdString() == "Read-only saved local activity, source identity and rule-comparison state."
                   && body->isReadOnly() && body->areScrollbarsShown(),
               "Progress body identifies retained saved activity and remains read-only and scrollable");
            ck(status && body && status->getHeight() >= 96 && status->getBottom() <= body->getY()
                   && detached.getLocalBounds().contains(status->getBounds()) && detached.getLocalBounds().contains(body->getBounds()),
               "Progress status reserves readable space and remains ordered above the contained scrollable body");
            const auto text = body ? body->getText().toStdString() : std::string{};
            capture_fixture::write(dir / "body-text.txt", text);
            ck(text.find("No Progress snapshot is loaded yet.") != std::string::npos,
               "Progress empty state names that no snapshot is loaded");
            ck(text.find("Choose Refresh to read finalized local activity.") != std::string::npos,
               "Progress empty state names the Refresh action");
            ck(text.find("To create a local record, choose an admitted source-backed case in Learn, complete the explicit Practice action and use Save result.") != std::string::npos,
               "Progress empty state preserves the exact Learn-to-Save next action");
            ck(text.find("Progress is read-only and does not create activity or curriculum credit.") != std::string::npos,
               "Progress empty state preserves the exact no-activity and no-credit boundary");
            ck(detached.presentation().projection.null() && !detached.busy(),
               "read-only Progress surface creates no snapshot read, profile mutation or pending operation");
            std::ofstream(dir / "summary.json") << "{\"checks\":" << count << ",\"status\":\"PASS\",\"profileRead\":false,\"mutation\":false}\n";
            std::cout << "PASS " << count << " Progress read-only surface checks\n";
            return 0;
        }
        if (guidedProvenanceOnly) {
            storage::StoreOptions options;
            options.path = dir / "profile.sqlite";
            options.create = true;
            options.createdUtc = "2026-09-19T12:48:34Z";
            storage::ProfileStore store(options);
            const auto session = store.createSession("guided-progress-provenance-session", "2026-09-19T12:48:35Z",
                                                     "America/New_York", 600,
                                                     V::Object{{"version", "guided-session-plan.1"}, {"purpose", "progress-provenance-smoke"}}).get();
            ck(session.status == storage::Status::Confirmed && !session.owner.empty(), "isolated Guided Session is created and owns the fixture Attempt");
            const auto activeSessionId = session.owner;
            const auto admitted = catalog->admit("fg:item:000002", "fg:variant:000006");
            ck(admitted && admitted->practiceAllowed(), "retained source-backed case remains admitted by the existing runtime gate");
            const auto configuration = admitted->practiceConfiguration(8000, 120);
            auto request = capture::lessonStart(*admitted, configuration, activeSessionId,
                                                "2026-09-19T12:48:36Z", "America/New_York", 1, false);
            const auto allocation = store.allocate("guided-progress-provenance-allocate", request.binding.kind,
                                                   request.binding.context, request.binding.practiceUtc).get();
            ck(allocation.status == storage::Status::Confirmed && !allocation.owner.empty(), "Attempt allocation preserves the Guided Session owner");
            request.binding.owner = allocation.owner;
            practice::Coordinator coordinator;
            beginAttempt(coordinator, request.binding, configuration);
            ck(coordinator.progress(capture_fixture::progress(coordinator, 16000, practice::State::Ended)),
               "isolated Guided-owned Attempt reaches a stopped result");
            const auto envelope = capture::makeEnvelope(coordinator, request.binding, nullptr, capture::Outcome::Stop);
            const auto sealed = store.seal("guided-progress-provenance-seal", envelope.owner, envelope.bytes).get();
            const auto committed = store.commit("guided-progress-provenance-commit", envelope.owner, envelope.bytes).get();
            ck(sealed.status == storage::Status::Confirmed && committed.status == storage::Status::Confirmed,
               "Guided-owned Attempt seals and commits through the existing transactional path");
            const auto snapshot = capture_fixture::confirmed(store.snapshot("guided-progress-provenance-snapshot"));
            const auto presentation = desktop::presentProgress(snapshot, asOf, catalog);
            const auto identity = std::string("fg:item:000002 / fg:variant:000006 | Source: L3-TXT5-21 L3-TXT28-46 | Content version: representative-controls.1 | Content revision: 2");
            ck(presentation.text.find("Lesson: ModeA Exercise001 full selected directions") != std::string::npos,
               "Progress presents the exact Catalog lesson title beside the retained source identity");
            ck(presentation.text.find("Finalized local activity records in this snapshot: 1") != std::string::npos,
               "Progress presents the exact finalized local activity count before details");
            ck(presentation.text.find("Duration fact: recorded active time only; wall-clock duration is not inferred.") != std::string::npos,
               "read-only Progress labels recorded active duration without inferring wall-clock time");
            ck(presentation.text.find("Guided Session: " + activeSessionId) != std::string::npos,
               "read-only Progress presents the exact persisted Guided Session ID");
            ck(presentation.text.find(identity) != std::string::npos
                   && presentation.text.find("Selected passes do not establish source-task completion.") != std::string::npos
                   && presentation.text.find("Progress does not recalculate or award curriculum credit.") != std::string::npos,
               "Progress preserves exact source facts and no-credit wording beside Guided provenance");
            savePresentation(dir, "guided-progress", presentation);
            const auto fallback = desktop::presentProgress(snapshot, asOf);
            ck(fallback.text.find("current lesson title not verified") != std::string::npos
                   && fallback.text.find("Guided Session:") == std::string::npos,
               "unverified historical fallback omits borrowed Guided provenance");
            savePresentation(dir, "guided-progress-fallback", fallback);
            capture_fixture::write(dir / "summary.json", storage::canonical(O{{"status", "PASS"}, {"checks", V::fromInteger(count)},
                {"session_id", activeSessionId}, {"case", "fg:item:000002/fg:variant:000006"}, {"finalized_attempts", V::fromInteger(1)}}));
            std::cout << "PASS " << count << " Guided Progress provenance checks\n";
            return 0;
        }
        if (controlContractOnly) {
            desktop::ProgressView detached; detached.setSize(920, 680); detached.setVisible(true);
            struct ControlContract { const char* id; const char* label; const char* title; int order; };
            const ControlContract controls[] = {
                {"progress-back", "Back", "Return to Home without changing read-only Progress.", 1},
                {"progress-refresh", "Refresh", "Read the current saved local snapshot without creating activity.", 2},
                {"progress-reopen", "Reopen profile", "Reopen the same local profile without replacing saved history.", 3},
                {"progress-learn", "Choose practice in Learn", "Open Learn to choose an admitted source-backed case.", 4},
                {"progress-audio-settings", "Audio settings", "Open shared Audio settings without changing Progress.", 5},
                {"progress-details", "Show saved details", "Saved details are unavailable until a Progress snapshot is loaded.", 6}
            };
            auto* backColor = dynamic_cast<juce::TextButton*>(detached.findChildWithID("progress-back"));
            ck(backColor && backColor->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                   && backColor->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                   && backColor->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c},
               "Progress Back uses the primary teal presentation while preserving the existing control contract");
            auto* refreshColor = dynamic_cast<juce::TextButton*>(detached.findChildWithID("progress-refresh"));
            ck(refreshColor && refreshColor->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                   && refreshColor->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                   && refreshColor->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c},
               "Progress Refresh uses the primary teal presentation while preserving the existing control contract");
            auto* reopenColor = dynamic_cast<juce::TextButton*>(detached.findChildWithID("progress-reopen"));
            ck(reopenColor && reopenColor->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                   && reopenColor->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                   && reopenColor->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c},
               "Progress Reopen uses the primary teal presentation while preserving the existing control contract");
            auto* audioColor = dynamic_cast<juce::TextButton*>(detached.findChildWithID("progress-audio-settings"));
            ck(audioColor && audioColor->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                   && audioColor->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                   && audioColor->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c},
               "Progress Audio settings uses the primary teal presentation while preserving the existing control contract");
            auto* detailsColor = dynamic_cast<juce::TextButton*>(detached.findChildWithID("progress-details"));
            ck(detailsColor && detailsColor->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                   && detailsColor->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                   && detailsColor->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c},
               "Progress saved details uses the primary teal presentation while preserving the existing control contract");
            for (const auto& contract : controls) {
                auto* component = detached.findChildWithID(contract.id);
                ck(component != nullptr, std::string("Progress control exists: ") + contract.id);
                if (!component) continue;
                ck(component->getTitle().toStdString() == contract.title, std::string("Progress control title: ") + contract.id);
                ck(component->getExplicitFocusOrder() == contract.order, std::string("Progress control focus order: ") + contract.id);
                ck(component->getWantsKeyboardFocus() == component->isEnabled(), std::string("Progress control focusability preserves enabled-state boundary: ") + contract.id);
                auto* button = dynamic_cast<juce::Button*>(component);
                ck(button && button->getButtonText().toStdString() == contract.label, std::string("Progress control label preserved: ") + contract.id);
            }
            ck(detached.presentation().projection.null() && !detached.busy(), "control inspection creates no Progress snapshot or pending read");
            std::cout << "PASS " << count << " Progress control checks\n";
            return 0;
        }
        if (refreshGuidanceOnly) {
            Harness h(dir, "refresh-guidance"); auto& progress = A::progress(*h.home);
            ck(A::lessons(*h.home).load(bundle), "accepted source bundle loads for Refresh guidance");
            ck(progress.bind(*h.store, [] { return asOf; }), "initial Progress bind succeeds without a snapshot read");
            ck(progress.presentation().projection.null()
                   && progress.statusText().find("Next action: choose Refresh to load the current saved snapshot.") != std::string::npos
                   && progress.statusText().find("Refresh reads saved facts and does not create activity.") != std::string::npos,
               "initial Progress status names the exact Refresh next action and read-only boundary");
            std::cout << "PASS " << count << " focused Progress refresh-guidance checks\n"; return 0;
        }
        if (backGuidanceOnly) {
            Harness h(dir, "back-guidance");
            ck(A::lessons(*h.home).load(bundle), "accepted source bundle loads for Back guidance");
            desktop::ProgressView detached;
            detached.setSize(920, 680); detached.setVisible(true);
            click(detached, "Back");
            ck(detached.presentation().projection.null()
                   && detached.presentation().text.empty()
                   && detached.presentation().details.empty()
                   && detached.statusText() == "Back is unavailable from Progress until the existing Home navigation is connected. The current read-only Progress view remains here; no activity, Attempt or curriculum credit was changed. Next action: reconnect the existing Home navigation, then choose Back.",
               "disconnected Progress Back preserves the read-only view and names Home reconnection as the next action");
            int backCalls{};
            detached.onBack = [&] { ++backCalls; };
            click(detached, "Back");
            ck(backCalls == 1, "connected Progress Back callback remains exactly once");
            std::cout << "PASS " << count << " focused Progress Back-guidance checks\n"; return 0;
        }
        if (savedBackIdentityOnly) {
            Harness h(dir, "saved-back-identity"); auto& progress = A::progress(*h.home);
            ck(A::lessons(*h.home).load(bundle), "accepted source bundle loads for saved Progress Back identity");
            ck(progress.findChildWithID("progress-back")->getTitle().toStdString() == "Return to Home without changing read-only Progress.", "initial Progress Back retains the generic read-only title");
            click(*h.home, "Progress"); refreshed(h);
            auto* back = dynamic_cast<juce::TextButton*>(progress.findChildWithID("progress-back"));
            ck(back && !progress.presentation().projection.null() && back->getTitle().toStdString() == "Return to Home after reviewing saved local activity; Progress remains read-only.", "loaded Progress Back exposes the saved read-only Home destination without changing the Back label or behavior");
            ck(progress.presentation().text.find("Progress is read-only here") != std::string::npos && h.finals() == 0, "loaded Progress Back identity preserves read-only facts and no Practice finalization");
            std::cout << "PASS " << count << " focused Progress saved-back identity checks\n"; return 0;
        }
        if (learnGuidanceOnly) {
            Harness h(dir, "learn-guidance");
            ck(A::lessons(*h.home).load(bundle), "accepted source bundle loads for Learn guidance");
            desktop::ProgressView detached;
            detached.setSize(920, 680); detached.setVisible(true);
            click(detached, "Choose practice in Learn");
            ck(detached.presentation().projection.null()
                   && detached.presentation().text.empty()
                   && detached.presentation().details.empty()
                   && detached.statusText() == "Learn is unavailable from Progress until the existing Learn navigation is connected. The current read-only Progress view remains here; no activity, Attempt or curriculum credit was changed. Next action: reconnect the existing Learn navigation, then choose practice in Learn.",
               "disconnected Progress Learn preserves the read-only view and names Learn reconnection as the next action");
            int learnCalls{};
            detached.onLearn = [&] { ++learnCalls; };
            click(detached, "Choose practice in Learn");
            ck(learnCalls == 1, "connected Progress Learn callback remains exactly once");
            std::cout << "PASS " << count << " focused Progress Learn-guidance checks\n"; return 0;
        }
        if (audioGuidanceOnly) {
            Harness h(dir, "audio-guidance");
            ck(A::lessons(*h.home).load(bundle), "accepted source bundle loads for Audio guidance");
            desktop::ProgressView detached;
            detached.setSize(920, 680); detached.setVisible(true);
            click(detached, "Audio settings");
            ck(detached.presentation().projection.null()
                   && detached.presentation().text.empty()
                   && detached.presentation().details.empty()
                   && detached.statusText() == "Audio settings are unavailable from Progress until the existing shared Audio destination is connected. The current read-only Progress view remains here; no activity, Attempt, sound or curriculum credit was changed. Next action: reconnect the existing shared Audio destination, then choose Audio settings.",
               "disconnected Progress Audio preserves the read-only view and names shared Audio reconnection as the next action");
            int audioCalls{};
            detached.onAudioSettings = [&] { ++audioCalls; };
            click(detached, "Audio settings");
            ck(audioCalls == 1, "connected Progress Audio callback remains exactly once");
            std::cout << "PASS " << count << " focused Progress Audio-guidance checks\n"; return 0;
        }
        if (!uxOnly) {
        {
            Harness h(dir, "actual-lessons"); auto& progress = A::progress(*h.home);
            ck(A::lessons(*h.home).load(bundle), "accepted source bundle loads locally");
            ck(progress.bind(*h.store, [] { return asOf; }), "explicit stable projection as-of");
            auto* body = dynamic_cast<juce::TextEditor*>(progress.findChildWithID("progress-body"));
            ck(body && body->getText().toStdString().find("No Progress snapshot is loaded yet.") != std::string::npos
                && body->getText().toStdString().find("Choose Refresh to read finalized local activity.") != std::string::npos
                && body->getText().toStdString().find("Progress is read-only and does not create activity or curriculum credit.") != std::string::npos,
               "pre-refresh Progress shows an honest next action without inventing saved activity");
            click(*h.home, "Progress"); refreshed(h);
            ck(views(progress.presentation()) == 0 && originals(progress.presentation()) == 0
                && progress.presentation().text.find("Currently prepared verified scope: 13 selected cases | 49 variants | 47 retained source entries | 13 of 105 approved workbook identities prepared | 92 are outside this prepared scope and remain discoverable in Learn and Exercise library | Additional workbook identities represented by selected cases: 0 | Comparisons use this prepared scope; saved history is retained independently | Whole-workbook completion from these cases: 0 | Curriculum review: Pending") != std::string::npos
                && progress.presentation().text.find("No finalized practice activity in this snapshot.") != std::string::npos
                && progress.presentation().text.find("Progress is read-only here: it shows finalized local activity only and does not create, estimate or award curriculum progress.") != std::string::npos
                && progress.presentation().text.find("Start with Learn: choose an admitted source-backed case, complete the explicit Practice action, use Save result, then return here to review the recorded facts.") != std::string::npos
                && progress.presentation().text.find("Freeplay activity is recorded separately.") != std::string::npos, "empty Progress gives an honest next action without fabricated practice");
            const auto beforeAudioRoute = capture_fixture::confirmed(h.store->snapshot("progress-audio-before"));
            click(progress, "Audio settings"); h.tick();
            ck(h.home->page() == H::Page::Audio && h.home->settingsCaller() == H::Page::Progress
                && button(A::settings(*h.home), "Back to Progress").isVisible(), "Progress opens shared Audio settings with Progress caller");
            click(A::settings(*h.home), "Back to Progress"); h.tick();
            const auto afterAudioRoute = capture_fixture::confirmed(h.store->snapshot("progress-audio-after"));
            ck(h.home->page() == H::Page::Progress && beforeAudioRoute.data == afterAudioRoute.data
                && h.home->audioSettings().snapshot().state == output::State::Closed, "Audio detour returns to read-only Progress without audio or profile mutation");
            h.image("empty");
            const auto empty = capture_fixture::confirmed(h.store->snapshot("empty-before"));
            ck(progress.refresh(), "explicit read refresh"); refreshed(h);
            ck(progress.statusText().find("Progress remains read-only and does not award curriculum credit.") != std::string::npos
                && progress.statusText().find("contains no finalized practice activity in this snapshot.") != std::string::npos
                && progress.statusText().find("Next action: choose an admitted source-backed case in Learn, complete explicit Practice, then use Save result to review a new local record here.") != std::string::npos,
               "successful empty Progress refresh states the no-activity fact, read-only boundary and Learn-to-Save next action");
            const auto emptyAfter = capture_fixture::confirmed(h.store->snapshot("empty-after"));
            ck(field(empty.data, "authoritative") == field(emptyAfter.data, "authoritative"), "viewing writes no history preferences cache or acknowledgment");
            click(progress, "Choose practice in Learn"); choose(A::lessons(*h.home), 3);
            click(A::lessons(*h.home), "Practice selected case"); ready(h); beginPartial(h);
            h.mode = 3; h.entered = false; h.release = false;
            click(h.practice(), "Save result"); h.wait([&] { return h.entered.load(); }, "Save barrier");
            const auto original = h.practice().captureSession()->original()->bytes;
            ck(!h.home->navigate(H::Page::Progress) && !h.home->detachForStoreReopen()
                && h.practice().captureSession()->original()->bytes == original, "pending save cannot be replaced or abandoned by Progress/reopen");
            h.release = true; finishSave(h);
            ck(h.home->navigate(H::Page::Progress), "resolved original opens Progress"); refreshed(h);
            ck(originals(progress.presentation()) == 1 && views(progress.presentation()) == 1, "one saved original produces one exact query");
            ck(progress.presentation().text.find("Level 3") != std::string::npos
                && progress.presentation().text.find("Completed selected passes: 0") != std::string::npos
                && progress.presentation().text.find("Self-assessment: not provided") != std::string::npos, "partial source facts and nullable self-report displayed accurately");
            ck(field(field(progress.presentation().projection, "views").array()[0], "query").find("condition")->null(), "missing comparison condition stays null");
            h.image("partial-original"); savePresentation(h.dir, "first-progress", progress.presentation());
            click(progress, "Choose practice in Learn"); choose(A::lessons(*h.home), 3);
            click(A::lessons(*h.home), "Practice selected case"); ready(h); beginPartial(h);
            click(h.practice(), "Save result"); finishSave(h);
            ck(h.home->navigate(H::Page::Progress), "second saved original opens Progress"); refreshed(h);
            ck(originals(progress.presentation()) == 2 && views(progress.presentation()) == 1, "two saves retain two originals and one canonical query");
            click(progress, "Choose practice in Learn"); choose(A::lessons(*h.home), 12);
            click(A::lessons(*h.home), "Practice selected case"); ready(h); beginPartial(h);
            click(h.practice(), "Save result"); finishSave(h);
            ck(h.home->navigate(H::Page::Progress), "different source opens Progress"); refreshed(h);
            ck(originals(progress.presentation()) == 3 && views(progress.presentation()) == 2, "different source variant remains a distinct exact query");
            auto older = progress.presentation();
            h.mode = 4; h.entered = false; h.release = false;
            ck(progress.refresh(), "start delayed snapshot read"); h.wait([&] { return h.entered.load(); }, "snapshot barrier");
            ck(!progress.refresh() && !progress.bind(*h.store, [] { return asOf; }) && !progress.detach()
                && !h.home->detachForStoreReopen() && !h.home->requestClose(), "pending read refuses duplicate refresh rebind detach and close");
            ck(progress.presentation().details == older.details && progress.statusText().find("previous snapshot") != std::string::npos, "delayed read visibly preserves older coherent snapshot");
            h.release = true; refreshed(h);
            ck(progress.bind(*h.store, [] { return "invalid-time"; }) && !progress.refresh(), "invalid refresh clock is an explicit failure");
            ck(progress.presentation().details == older.details && progress.statusText().find(asOf) != std::string::npos, "refresh failure retains dated older snapshot");
            ck(progress.bind(*h.store, [] { return asOf; }), "restore valid consumer clock");
            const auto before = capture_fixture::confirmed(h.store->snapshot("before-reopen"));
            int reopenRequests = 0;
            h.home->onReopenStore = [&] { ++reopenRequests; return h.home->detachForStoreReopen(); };
            ck(progress.refresh(), "refresh controls after attaching actual reopen callback"); refreshed(h);
            click(progress, "Reopen profile");
            ck(reopenRequests == 1 && !button(progress, "Reopen profile").isEnabled()
                && progress.presentation().details == older.details, "reopen retains dated snapshot while preventing overlap");
            h.home->storeReopenFailed("Synthetic unavailable path; no real profile removed");
            ck(button(progress, "Reopen profile").isEnabled() && progress.statusText().find(asOf) != std::string::npos
                   && progress.statusText().find("Choose Reopen profile to retry attaching the same local profile.") != std::string::npos,
               "failed detached reopen retains the old date and names the Reopen profile retry");
            h.image("failed-reopen"); click(progress, "Reopen profile");
            ck(reopenRequests == 2, "retry routes through existing guarded Home reopen");
            h.store.reset(); storage::StoreOptions options; options.path = h.dir / "profile.sqlite";
            options.preferenceValidator = metronome::preferenceValidator;
            h.store = std::make_unique<storage::ProfileStore>(options);
            ck(h.home->configureCapture(*h.store, h.sessionId, "America/New_York"), "ordinary same-profile Store reopen and consumer attachment");
            refreshed(h); h.wait([&] { return A::metronome(*h.home).preferencesReady(); }, "reopened preferences");
            ck(progress.bind(*h.store, [] { return asOf; }) && progress.refresh(), "stable as-of after reopen"); refreshed(h);
            const auto after = capture_fixture::confirmed(h.store->snapshot("after-reopen"));
            ck(field(before.data, "authoritative") == field(after.data, "authoritative")
                && progress.presentation().details == older.details, "ordinary reopen preserves exact original tables and projection at declared as-of");
            ck(h.home->audioSettings().snapshot().state == output::State::Closed, "reopen creates no output or elapsed practice");
            h.image("reopened-history"); click(progress, "Show saved details"); h.image("details"); click(progress, "Hide saved details");
            savePresentation(h.dir, "final-progress", progress.presentation());
            capture_fixture::write(h.dir / "snapshot-before.json", storage::canonical(before.data));
            capture_fixture::write(h.dir / "snapshot-after.json", storage::canonical(after.data));
            // New private foreign profile is never admitted as the old one.
            Harness other(dir, "foreign-profile");
            ck(progress.bind(*other.store, [] { return asOf; }) && progress.refresh(), "exercise explicit foreign snapshot rejection"); refreshed(h);
            ck(progress.presentation().details == older.details && progress.statusText().find("not the original") != std::string::npos, "foreign profile cannot overwrite original displayed snapshot");
            ck(progress.bind(*h.store, [] { return asOf; }), "restore original attachment before foreign fixture destruction");
        }
        {
            const auto copied = dir / "native-profile-copy"; std::filesystem::create_directory(copied);
            std::filesystem::permissions(copied, std::filesystem::perms::owner_all);
            std::filesystem::copy_file(native / "profile.sqlite", copied / "profile.sqlite");
            storage::StoreOptions options; options.path = copied / "profile.sqlite"; options.preferenceValidator = metronome::preferenceValidator;
            storage::ProfileStore store(options); const auto snapshot = capture_fixture::confirmed(store.snapshot("retained-native-copy"));
            const auto p = desktop::presentProgress(snapshot, asOf, catalog);
            ck(originals(p) == 2 && views(p) == 2, "copied native history retains both actual original owners");
            ck(p.text.find("6.039 s") != std::string::npos && p.text.find("8.000 s") != std::string::npos
                && p.text.find("Earlier/ended partial traversals retained: 1") != std::string::npos
                && p.text.find("Workbook identity: fg:workbook:000003 | Level: 3") != std::string::npos
                && p.text.find("fg:item:000002 / fg:variant:000006 | Source: L3-TXT5-21 L3-TXT28-46 | Content version: representative-controls.1 | Content revision: 2") != std::string::npos,
               "retained native L3 replay/partial, exact source identity/content version and L12 duration facts remain visible");
            for (const auto& view : field(p.projection, "views").array()) {
                const auto& rule = field(view, "projection");
                ck(field(field(view, "query"), "condition").null() && field(rule, "pb").null()
                    && !field(rule, "source_complete").boolean(), "native selected passes invent no comparison or source credit");
            }
            savePresentation(copied, "native-progress", p);
            desktop::ProgressView view; view.setSize(920, 680); view.setVisible(true); view.setCatalog(catalog);
            ck(view.bind(store, [] { return asOf; }) && view.refresh(), "native-copy actual Progress view read");
            const auto deadline = capture_fixture::now() + 7000;
            while (view.busy()) { view.service(); pump(); if (capture_fixture::now() > deadline) throw std::runtime_error("native-copy presentation watchdog"); }
            for (auto size : {juce::Point<int>{920,680}, juce::Point<int>{1280,800}}) {
                view.setSize(size.x, size.y); auto image = view.createComponentSnapshot(view.getLocalBounds());
                juce::FileOutputStream out(juce::File((copied / (std::to_string(size.x) + ".png")).string()));
                ck(juce::PNGImageFormat().writeImageToStream(image, out), "native-copy readable component screenshot " + std::to_string(size.x));
            }
            auto wrong = snapshot; member(wrong.data, "snapshot_sha256") = std::string(64, '0');
            rejected([&] { desktop::presentProgress(wrong, asOf, catalog); }, "hash mismatch rejected without empty-success fallback");
            wrong = snapshot; member(member(wrong.data, "authoritative"), "finalized").array()[0] = Array{}; rehash(wrong);
            rejected([&] { desktop::presentProgress(wrong, asOf, catalog); }, "malformed authoritative row refused");
            const auto unlabelled = desktop::presentProgress(snapshot, asOf);
            ck(unlabelled.text.find("current lesson title not verified") != std::string::npos && originals(unlabelled) == 2, "missing current metadata retains raw source IDs and original facts");
            auto altered = json::parse(readFile(native / "L3-original.json"));
            member(member(altered, "context"), "content_version") = "synthetic-historical-version";
            member(member(member(altered, "result"), "content"), "content_version") = "synthetic-historical-version";
            auto changed = snapshot; replaceOriginal(changed, altered);
            const auto historical = desktop::presentProgress(changed, asOf, catalog);
            ck(historical.text.find("synthetic-historical-version (current lesson title not verified)") != std::string::npos
                && historical.text.find("Level 3 |") == std::string::npos, "stale optional runtime metadata cannot label changed authoritative context as current source");
            savePresentation(copied, "synthetic-changed-context", historical);
            auto hashChanged = json::parse(readFile(native / "L3-original.json"));
            auto& hashes = member(member(member(hashChanged,"result"),"content"),"source_hashes");
            hashes.object().begin()->second = std::string(64,'c');
            auto hashSnapshot = snapshot; replaceOriginal(hashSnapshot, hashChanged);
            const auto historicalHash = desktop::presentProgress(hashSnapshot, asOf, catalog);
            ck(historicalHash.text.find("Level 3 |") == std::string::npos && historicalHash.text.find("current lesson title not verified") != std::string::npos,
               "changed original source hash cannot borrow current title through stale optional runtime metadata");
            savePresentation(copied,"synthetic-changed-hash",historicalHash);
            const auto future = desktop::presentProgress(snapshot, "2026-09-08T00:00:00Z", catalog);
            ck(originals(future) == 2 && future.details.find("future") != std::string::npos, "future relative to as-of evidence remains original with explicit rule notice");
        }
        {
            Harness h(dir, "synthetic-freeplay-ack");
            const auto ack = h.store->acknowledge("explicit-ack", storage::newUuid(), "fg:item:000002", 2, "2026-09-08T16:01:00Z").get();
            ck(ack.status == storage::Status::Confirmed, "synthetic explicit acknowledgment stored");
            const auto ackOnly = desktop::presentProgress(capture_fixture::confirmed(h.store->snapshot("ack-only")), asOf, catalog);
            ck(views(ackOnly) == 0 && originals(ackOnly) == 0, "acknowledgment alone cannot invent exact curriculum query or practice");
            practice::Coordinator coordinator;
            capture::PracticeSession session(*h.store, coordinator); auto request = capture_fixture::request(h.sessionId, true);
            ck(session.start(request, 1, capture_fixture::now()), "synthetic Freeplay allocation through actual capture session");
            capture_fixture::until(session, [&] { return session.phase() == capture::SessionPhase::Ready; });
            ck(session.takeStart(capture_fixture::now()).has_value(), "synthetic Freeplay initial checkpoint confirmed");
            coordinator.progress(capture_fixture::progress(coordinator, 24000, practice::State::Ended));
            session.poll(capture_fixture::now(), "2026-09-08T16:01:02Z");
            capture_fixture::until(session, [&] { return session.phase() == capture::SessionPhase::Review; });
            ck(session.save(nullptr, capture::Outcome::Stop, capture_fixture::now()), "synthetic Freeplay save requested");
            capture_fixture::until(session, [&] { return session.phase() == capture::SessionPhase::Saved; });
            const auto freeplay = desktop::presentProgress(capture_fixture::confirmed(h.store->snapshot("freeplay")), asOf, catalog);
            ck(views(freeplay) == 0 && originals(freeplay) == 1
                && freeplay.text.find("Freeplay activity") != std::string::npos
                && freeplay.text.find("Finalized local records are shown read-only below; Progress does not recalculate or award curriculum credit.") != std::string::npos,
               "actual FreeplayActivity original is displayed read-only without curriculum query");
            savePresentation(h.dir, "freeplay-ack-progress", freeplay);
        }
        {
            const auto d = dir / "synthetic-source-attestations";
            std::filesystem::create_directory(d); std::filesystem::permissions(d, std::filesystem::perms::owner_all);
            storage::StoreOptions options; options.path = d / "profile.sqlite"; options.create = true;
            options.createdUtc = "2026-09-01T00:00:00Z";
            options.sourceValidator = [](const V&) { return true; }; // Isolated historical-definition fixtures, no production admission.
            storage::ProfileStore store(options);
            const auto initial = capture_fixture::confirmed(store.snapshot("source-profile"));
            const auto inputs = native.parent_path().parent_path() / "20260907T230134Z-7.2.1.1.1-r01-evidence/fixture-inputs";
            auto source = [&](const std::string& name) {
                auto value = json::parse(readFile(inputs / name));
                member(value, "performer_ref") = field(initial.data, "profile_id");
                member(member(value, "attestation"), "performer_ref") = field(initial.data, "profile_id");
                if (field(field(value, "attestation"), "role") == V("learner"))
                    member(member(value, "attestation"), "who") = field(initial.data, "profile_id");
                member(value, "fact_id") = storage::newUuid(); return value;
            };
            auto learner = source("source-learner.json");
            capture_fixture::confirmed(store.attest("synthetic-learner", storage::canonical(learner)));
            auto p = desktop::presentProgress(capture_fixture::confirmed(store.snapshot("one-source")), asOf, catalog);
            ck(views(p) == 1 && originals(p) == 1 && !field(field(field(p.projection,"views").array()[0],"projection"),"source_complete").boolean(),
               "supported one-take source fact gives exact query without completion");
            capture_fixture::confirmed(store.attest("synthetic-review", storage::canonical(source("source-review.json"))));
            p = desktop::presentProgress(capture_fixture::confirmed(store.snapshot("source-review")), asOf, catalog);
            ck(views(p) == 1 && originals(p) == 2 && field(field(field(p.projection,"views").array()[0],"projection"),"source_complete").boolean()
               && field(field(field(p.projection,"views").array()[0],"projection"),"pb").null(), "synthetic accepted-definition independent branch credits source only, no PB");
            member(learner,"fact_id") = storage::newUuid();
            member(member(learner,"context"),"content_version") = "synthetic-unregistered.2";
            member(member(learner,"rubric_ref"),"content_version") = "synthetic-unregistered.2";
            capture_fixture::confirmed(store.attest("synthetic-unsupported", storage::canonical(learner)));
            p = desktop::presentProgress(capture_fixture::confirmed(store.snapshot("unsupported-source")), asOf, catalog);
            ck(views(p) == 1 && originals(p) == 3 && p.text.find("Unsupported exact source rubric/version") != std::string::npos,
               "unsupported source fact retained with notice and no invented query");
            savePresentation(d,"source-progress",p);
        }
        {
            const auto d = dir / "snapshot-error"; std::filesystem::create_directory(d);
            std::filesystem::permissions(d, std::filesystem::perms::owner_all);
            std::atomic<bool> failRead{false}; storage::StoreOptions options; options.path = d / "profile.sqlite";
            options.create = true; options.createdUtc = "2026-09-01T00:00:00Z";
            options.diagnosticHook = [&](const std::string& phase, const std::string& operation) {
                if (phase == "before_operation" && operation.find("progress-view/") == 0 && failRead.exchange(false))
                    throw std::runtime_error("Synthetic read failure; authoritative bytes unchanged");
            };
            storage::ProfileStore store(options); desktop::ProgressView view; view.setSize(920,680);
            auto drain = [&] { const auto until=capture_fixture::now()+7000; while(view.busy()) { view.service();pump();if(capture_fixture::now()>until)throw std::runtime_error("read failure watchdog"); } };
            ck(view.bind(store, [] { return asOf; }) && view.refresh(), "initial coherent snapshot before worker failure"); drain();
            const auto old = view.presentation().details; failRead = true;
            ck(view.refresh(), "submit actual Store snapshot fault"); drain();
            ck(view.presentation().details == old && view.statusText().find("Could not refresh") != std::string::npos
               && view.statusText().find(asOf) != std::string::npos
               && view.statusText().find("Choose Refresh to retry reading the attached profile.") != std::string::npos,
               "actual worker read failure retains the older snapshot date and names Refresh retry");
            capture_fixture::write(d/"failure-status.txt",view.statusText());
        }
        }
        if (uxOnly) {
            {
                desktop::ProgressView detached;
                detached.setSize(920, 680); detached.setVisible(true);
                click(detached, "Back");
                ck(detached.presentation().projection.null()
                       && detached.presentation().text.empty()
                       && detached.presentation().details.empty()
                       && detached.statusText() == "Back is unavailable from Progress until the existing Home navigation is connected. The current read-only Progress view remains here; no activity, Attempt or curriculum credit was changed.",
                   "disconnected Progress Back preserves the initial read-only view with exact recovery guidance");
                int backCalls{};
                detached.onBack = [&] { ++backCalls; };
                click(detached, "Back");
                ck(backCalls == 1, "connected Progress Back callback is delivered exactly once");
            }
            {
                desktop::ProgressView detached;
                detached.setSize(920, 680); detached.setVisible(true);
                click(detached, "Choose practice in Learn");
                ck(detached.presentation().projection.null()
                       && detached.presentation().text.empty()
                       && detached.presentation().details.empty()
                       && detached.statusText() == "Learn is unavailable from Progress until the existing Learn navigation is connected. The current read-only Progress view remains here; no activity, Attempt or curriculum credit was changed.",
                   "disconnected Progress Learn handoff preserves the initial read-only view with exact recovery guidance");
                int learnCalls{};
                detached.onLearn = [&] { ++learnCalls; };
                click(detached, "Choose practice in Learn");
                ck(learnCalls == 1, "connected Progress Learn callback is delivered exactly once");
            }
            {
                desktop::ProgressView detached;
                detached.setSize(920, 680); detached.setVisible(true);
                click(detached, "Audio settings");
                ck(detached.presentation().projection.null()
                       && detached.presentation().text.empty()
                       && detached.presentation().details.empty()
                       && detached.statusText() == "Audio settings are unavailable from Progress until the existing shared Audio destination is connected. The current read-only Progress view remains here; no activity, Attempt, sound or curriculum credit was changed.",
                   "disconnected Progress Audio handoff preserves the initial read-only view with exact recovery guidance");
                int audioCalls{};
                detached.onAudioSettings = [&] { ++audioCalls; };
                click(detached, "Audio settings");
                ck(audioCalls == 1, "connected Progress Audio callback is delivered exactly once");
            }
            {
                desktop::AudioOutputView detached;
                detached.setSize(920, 680); detached.setVisible(true);
                juce::Button* back = nullptr;
                for(auto* child : detached.getChildren())
                    if(auto* candidate=dynamic_cast<juce::Button*>(child);candidate&&candidate->getButtonText()=="Back") back=candidate;
                auto* status=dynamic_cast<juce::Label*>(detached.findChildWithID("shared-audio-status"));
                ck(back&&status, "shared Audio Back and status controls are present");
                back->onClick();
                ck(status->getText().toStdString()=="Back is unavailable from Audio settings until the existing caller navigation is connected. The shared Audio state remains here; no output, activity or curriculum credit was changed.",
                   "disconnected shared Audio Back exposes exact recovery guidance without callback");
                int backCalls{};
                detached.onBack=[&]{++backCalls;};
                back->onClick();
                ck(backCalls==1, "connected shared Audio Back callback is delivered exactly once");
            }
            Harness h(dir, "keyboard-home");
            ck(A::lessons(*h.home).load(bundle), "accepted bundle for keyboard navigation");
            h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar); h.home->setVisible(true);
            NSView* nativeView = (__bridge NSView*)h.home->getPeer()->getNativeHandle();
            [nativeView.window makeKeyAndOrderFront:nil];
            auto key = [&](NSString* text, unsigned short code) {
                for (bool down : {true,false}) {
                    auto* event = [NSEvent keyEventWithType:down?NSEventTypeKeyDown:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:nativeView.window.windowNumber context:nil characters:text charactersIgnoringModifiers:text isARepeat:NO keyCode:code];
                    [NSApp sendEvent:event];
                }
                pump(); marker(); h.tick();
            };
            button(*h.home,"Progress").grabKeyboardFocus(); key(@"\r",36); refreshed(h);
            ck(h.home->page()==H::Page::Progress && A::progress(*h.home).isShowing(), "focused Return opens actual Home Progress destination");
            auto& progress=A::progress(*h.home);
            ck(progress.statusText().find("Saved snapshot as of") != std::string::npos
                && progress.statusText().find("Finalized local activity remains read-only; this view does not award curriculum credit.") != std::string::npos,
               "Progress settled status states read-only refresh/no-activity");
            button(progress,"Back").grabKeyboardFocus(); key(@"\t",48);
            ck(button(progress,"Refresh").hasKeyboardFocus(true), "actual Tab moves Back to Refresh");
            button(progress,"Show saved details").grabKeyboardFocus(); key(@"\r",36);
            ck(button(progress,"Hide saved details").isVisible(), "focused Return toggles exact saved details");
            h.image("keyboard-details");
            button(progress,"Choose practice in Learn").grabKeyboardFocus(); key(@"\r",36);
            ck(h.home->page()==H::Page::Learn && h.finals()==0, "keyboard return to Learn records no practice and starts no audio");
            h.home->removeFromDesktop();
            const auto d=dir/"scroll-native-copy"; std::filesystem::create_directory(d); std::filesystem::permissions(d,std::filesystem::perms::owner_all);
            std::filesystem::copy_file(native/"profile.sqlite",d/"profile.sqlite");
            storage::StoreOptions options;options.path=d/"profile.sqlite";options.preferenceValidator=metronome::preferenceValidator;
            storage::ProfileStore store(options);desktop::ProgressView view;view.setCatalog(catalog);view.setSize(920,680);view.setVisible(true);
            ck(view.bind(store,[]{return asOf;})&&view.refresh(), "scrollable retained original view starts one read");
            const auto until=capture_fixture::now()+7000;while(view.busy()){view.service();pump();if(capture_fixture::now()>until)throw std::runtime_error("scroll view watchdog");}
            juce::TextEditor* editor=nullptr;
            for(auto* child:view.getChildren())if(auto* candidate=dynamic_cast<juce::TextEditor*>(child))editor=candidate;
            ck(editor&&editor->isReadOnly()&&editor->isMultiLine(), "history is a read-only multiline editor");
            editor->moveCaretToEnd(false);editor->scrollEditorToPositionCaret(0,0);
            for(auto size:{juce::Point<int>{920,680},juce::Point<int>{1280,800}}){
                view.setSize(size.x,size.y);editor->moveCaretToEnd(false);editor->scrollEditorToPositionCaret(0,0);
                auto image=view.createComponentSnapshot(view.getLocalBounds());juce::FileOutputStream out(juce::File((d/(std::to_string(size.x)+"-bottom.png")).string()));
                ck(juce::PNGImageFormat().writeImageToStream(image,out),"scrolled rule/comparison screenshot "+std::to_string(size.x));
            }
            ck(editor->getText().toStdString()==view.presentation().text && originals(view.presentation())==2,
               "scrolling retains complete original text and both immutable records");
        }
        ck(nativeOpens == 0 && maxClaims <= 1, "zero native opens and at most one synthetic output owner");
        capture_fixture::write(dir / "summary.json", storage::canonical(O{{"status","PASS"},{"checks",V::fromInteger(count)},
            {"native_opens",V::fromInteger(nativeOpens)},{"classification","Actual desktop/Store, synthetic device and labelled fixture records; retained native profile is a copy"}}));
        std::cout << "PASS " << count << " M1 Progress checks\n"; return 0;
    } catch (const std::exception& error) { std::cerr << "FAIL after " << count << ": " << error.what() << '\n'; return 1; }
}
