#include "tasks/OrderedContactTask.hpp"
#include "content/StrictJson.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <sstream>

namespace {
namespace F = fathom::tasks::ordered_contacts;
namespace M = F::manual;
using J = fathom::json::Value;
std::size_t checks = 0, refusals = 0, contactReports = 0, boundaryReports = 0, completed = 0;
std::size_t fullBranches = 0, restoredBranches = 0, untimedCues = 0, sourceSlotCues = 0;
void check(bool good, const char* code) { ++checks; if (!good) throw std::runtime_error(code); }
const J& at(const J& value, const std::string& key) {
    check(value.isObject() && value.find(key), "TEST_POLICY_FIELD"); return *value.find(key);
}
std::string sha256(const std::string& bytes) {
    check(bytes.size() <= std::numeric_limits<CC_LONG>::max(), "POLICY_HASH_SIZE");
    std::array<unsigned char, CC_SHA256_DIGEST_LENGTH> hash{};
    CC_SHA256(bytes.data(), static_cast<CC_LONG>(bytes.size()), hash.data());
    std::ostringstream out;
    for (const auto byte : hash) out << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(byte);
    return out.str();
}
template<class Function> void refuses(Function&& action, M::Task* task = nullptr) {
    const auto revision = task ? task->view().revision : 0;
    const auto history = task ? task->history().size() : 0;
    const auto before = task ? std::optional<M::View>(task->view()) : std::nullopt;
    bool rejected = false;
    try { action(); } catch (const M::Refusal&) { rejected = true; }
    check(rejected, "EXPECTED_ORDERED_TASK_REFUSAL"); ++refusals;
    if (task) {
        const auto after = task->view();
        check(after.revision == revision && task->history().size() == history
            && after.state == before->state && after.passIndex == before->passIndex && after.nextOrdinal == before->nextOrdinal
            && after.tempoReductionDue == before->tempoReductionDue && after.reportedBpm == before->reportedBpm,
            "REFUSAL_HAS_NO_STATE_MUTATION");
    }
}
M::SetupReport setup(const M::Task& task, std::optional<M::Rhythm> rhythm = std::nullopt) {
    M::SetupReport r{M::Branch::PrintedPassProgression,
        rhythm.value_or(task.sourcePolicy().passes.front().rhythms.front()), F::Start::Down};
    r.sourceSetupRead = r.onePrintedSetChosen = r.printedModeChosen = r.stableLandings = M::Claim::Yes;
    return r;
}
M::SessionReport external() {
    M::SessionReport r;
    r.priorPrintedPassesReported = r.fullPrintedSetClean = r.bothRoutesClean = r.bothStartsClean = r.bothModesClean = M::Claim::Yes;
    r.separateDayLabels = {"2026-09-29", "2026-09-30"}; return r;
}
std::size_t descriptors = 0;
void forms(const M::Task& task) {
    const auto actions = task.actionDescriptors();
    std::set<M::Action> unique;
    check(!actions.empty(), "EVERY_STATE_HAS_TYPED_LEARNER_ACTIONS");
    for (const auto& action : actions) {
        ++descriptors;
        check(unique.insert(action.action).second && !action.label.empty(), "UNIQUE_TYPED_ACTION_LABEL");
        (void)task.capture(action.action);
        const auto safe = [&task](const std::string& text) {
            check(text.find("sha256") == std::string::npos && text.find(task.definition().sourceRecordSha256()) == std::string::npos
                && text.find(task.definition().packetPath()) == std::string::npos
                && text.find("ORDERED_TASK_") == std::string::npos, "LEARNER_TEXT_EXCLUDES_TRUSTED_CUSTODY_AND_INTERNAL_CODES");
        };
        safe(action.label);
        for (const auto& text : action.instructions) safe(text);
        std::set<M::FieldId> fields;
        for (const auto& field : action.fields) {
            check(fields.insert(field.id).second && !field.label.empty(), "TYPED_FORM_FIELD_UNIQUE"); safe(field.label);
            if (field.kind == M::FieldKind::Choice) check(!field.choices.empty(), "TYPED_CHOICE_HAS_EXPLICIT_VALUES");
            if (field.kind == M::FieldKind::PositiveInteger) check(field.minimum == 1 && !field.maximum, "EXPLICIT_POSITIVE_INTEGER_NO_DEFAULT");
            for (const auto& choice : field.choices) safe(choice.label);
        }
        if (action.contact) check(action.action == M::Action::Contact && !action.contact->stringLabel.empty()
            && action.contact->ordinal == task.view().nextOrdinal, "LEARNER_CONTACT_IS_EXACT_CURRENT_DISPLAY");
    }
}
void sourcePolicies(const std::filesystem::path& root) {
    const std::map<int, std::vector<M::Pass>> expected{
        {2, {M::Pass::ConnectedEqual}}, {3, {M::Pass::LandingAccent, M::Pass::ConnectedEqual}},
        {4, {M::Pass::LandingAccent, M::Pass::ConnectedEqual}}, {5, {M::Pass::LandingAccent, M::Pass::ConnectedEqual}},
        {6, {M::Pass::SeparatedAccent, M::Pass::SeparatedEqual, M::Pass::ConnectedEqual}},
        {7, {M::Pass::SeparatedAccent, M::Pass::ConnectedEqual}},
        {8, {M::Pass::PausedEighthAccent, M::Pass::ConnectedEighthEqual, M::Pass::ConnectedSixteenth}},
        {9, {M::Pass::StoppedRelocation, M::Pass::ConnectedEighthAccent, M::Pass::ConnectedEighthEqual, M::Pass::ConnectedSixteenth}},
        {10, {M::Pass::PausedEighthAccent, M::Pass::ConnectedEighthEqual, M::Pass::ConnectedSixteenth}},
        {11, {M::Pass::PausedEighthAccent, M::Pass::ConnectedEighthAccent, M::Pass::ConnectedEighthEqual, M::Pass::ConnectedSixteenth}}};
    for (const auto& item : expected) {
        const auto& p = M::policy(item.first);
        check(p.passes.size() == item.second.size(), "SOURCE_PASS_COUNTS");
        for (std::size_t i = 0; i < item.second.size(); ++i) check(p.passes[i].pass == item.second[i], "SOURCE_PASS_ORDER_FIXTURE");
        std::ifstream input(root / p.contextPath, std::ios::binary);
        check(input.good(), "SAVED_CONTEXT_OPEN"); std::ostringstream buffer; buffer << input.rdbuf();
        const auto bytes = buffer.str(); check(sha256(bytes) == p.contextSha256, "SAVED_CONTEXT_PIN");
        const auto context = fathom::json::parse(bytes);
        const auto& lines = at(context, "guidance_lines").array();
        check(lines.size() == p.sourceLines.size(), "FULL_CONTEXT_LINE_CARDINALITY");
        for (std::size_t i = 0; i < lines.size(); ++i) {
            std::int64_t n = 0; check(at(lines[i], "line").integer(n), "SOURCE_LINE_INTEGER");
            check(n == p.sourceLines[i].line && at(lines[i], "text").string() == p.sourceLines[i].text, "EXACT_FULL_CONTEXT_LINES");
        }
        const auto& original = at(at(context, "originals"), "txt");
        check(at(original, "path").string() == p.sourceTextPath && at(original, "sha256").string() == p.sourceTextSha256, "SOURCE_ASSET_PIN");
        check(p.downStartFirst == (item.first >= 8) && p.oneModePerSession == (item.first == 3 || item.first == 6 || item.first == 10), "SOURCE_START_MODE_RULES");
        check(p.slowerOfTwoPreviousModes == (item.first == 7 || item.first == 11), "SOURCE_PREVIOUS_TEMPO_RULE");
    }
    refuses([] { (void)M::policy(1); });
}
void route(M::Task& task, M::Observation outcome = M::Observation::Clean, bool checkParity = true) {
    const auto source = task.definition().reference(task.view().start);
    const auto sourceKey = std::string(task.definition().sourceKey());
    while (task.view().state == M::State::Traversal || task.view().state == M::State::Boundary) {
        const auto cue = task.cue();
        if (task.view().state == M::State::Boundary) {
            check(cue.releaseAndRelocateBefore || cue.pauseBefore != M::Pause::None, "BOUNDARY_HAS_SOURCE_DUTY");
            task.reportBoundary(task.capture(M::Action::BoundaryReport), {M::Claim::Yes, M::Claim::Yes, M::Claim::Yes});
            ++boundaryReports;
        }
        if (checkParity) {
            const auto& event = source.events[cue.ordinal - 1]; const auto& tone = event.tones.front();
            check(cue.stringLowToHigh == tone.string && cue.fret == tone.fret && cue.finger == std::stoi(tone.finger)
                && cue.midi == tone.midi && cue.spelling == tone.spelling && cue.pick == event.handDirection
                && cue.sourceRef == event.sourceRef, "EVERY_CUE_EXACT_IMMUTABLE_SOURCE_CONTACT");
            check(cue.pick == ((cue.ordinal % 2 == 1) == (task.view().start == F::Start::Down) ? "D" : "U"), "CONTINUOUS_PICK_NO_BOUNDARY_RESET");
            check(!cue.acousticSoundingSpan, "EVERY_MANUAL_CUE_SOUNDING_GATE_UNKNOWN");
            if (cue.clockAuthority == M::ClockAuthority::ManualUntimed) {
                check(!cue.activeSourceMetricSpan, "UNSELECTED_PASS_CANNOT_INHERIT_SELECTED_GRID"); ++untimedCues;
            } else {
                check(cue.activeSourceMetricSpan && *cue.activeSourceMetricSpan == event.span, "SELECTED_SOURCE_SLOT_ONLY"); ++sourceSlotCues;
            }
            check(cue.route == task.sourceRoutes()[cue.ordinal <= source.events.size() / 2 ? 0 : 1], "EXACT_ROUTE_ORDER");
            const auto level = task.definition().level();
            const auto local = (cue.ordinal - 1) % (level == 8 ? 8 : 4) + 1;
            const auto pass = cue.pass;
            const bool accented = pass == M::Pass::LandingAccent || pass == M::Pass::SeparatedAccent
                || pass == M::Pass::PausedEighthAccent || pass == M::Pass::ConnectedEighthAccent;
            bool isLanding = false;
            if (level == 3 || level == 6 || level == 10) {
                const bool a = task.headingPath().back().rfind("MODE A", 0) == 0; isLanding = local == (a ? 4U : 2U);
            } else if (level == 4 || level == 7 || level == 11) isLanding = local == 2 || local == 4;
            else if (level == 5 || level == 9) isLanding = local == 3;
            else if (level == 8) isLanding = local == 5;
            check(cue.landingAccent == (accented && isLanding), "ALL_ROW_SOURCE_LANDING_ACCENT_SEMANTICS");
            if (pass == M::Pass::StoppedRelocation)
                check(cue.rhythm == M::Rhythm::Unspecified && cue.clockAuthority == M::ClockAuthority::ManualUntimed,
                      "LEVEL9_STOPPED_PASS_HAS_NO_INVENTED_EIGHTH_CLOCK");
            const bool selectedSlots = (level != 11 && cue.rhythm == M::Rhythm::StraightSixteenth
                && (pass == M::Pass::ConnectedEqual || pass == M::Pass::ConnectedSixteenth))
                || (level == 11 && pass == M::Pass::ConnectedEighthEqual && cue.rhythm == M::Rhythm::StraightEighth);
            check((cue.clockAuthority == M::ClockAuthority::SavedSelectedRelativeSlots) == selectedSlots,
                  "ONLY_ACTUAL_SAVED_GRID_HAS_RELATIVE_SLOT_AUTHORITY");
        }
        task.confirmContact(task.capture(M::Action::Contact), cue.ordinal, M::Claim::Yes); ++contactReports;
    }
    check(task.view().state == M::State::Release && task.view().needsManualRelease, "ALL_CONTACTS_REQUIRE_EXPLICIT_RELEASE");
    task.release(task.capture(M::Action::Release), M::Claim::Yes);
    task.reportLoop(task.capture(M::Action::LoopReport), {outcome, M::Claim::Yes});
    check(std::string(task.definition().sourceKey()) == sourceKey, "SOURCE_KEY_NEVER_CHANGES");
}
void normal(M::Task& task, M::SetupReport report) {
    task.begin(task.capture(M::Action::Begin), report);
    const auto startingPass = task.view().passIndex;
    for (std::size_t i = startingPass; i < task.sourcePolicy().passes.size(); ++i) {
        route(task);
        task.oppositeStart(task.capture(M::Action::OppositeStart)); route(task);
        if (i + 1 < task.sourcePolicy().passes.size()) {
            const auto& next = task.sourcePolicy().passes[i + 1];
            const auto rhythm = task.definition().level() >= 8 ? next.rhythms.front() : report.rhythm;
            task.advancePass(task.capture(M::Action::AdvancePass), next.pass, rhythm);
        } else task.finish(task.capture(M::Action::Finish));
    }
    const auto v = task.view();
    check(v.state == M::State::Finished && v.coverage.chosenBranchRequiredPassesAndBothStartsReported,
          "REQUIRED_SOURCE_BRANCH_PASSES_AND_STARTS_REPORTED");
    check(!v.coverage.wholeChildAccepted && !v.coverage.performanceObserved && !v.coverage.runtimeAdmitted
          && !v.coverage.remainingManualObligations.empty(), "MANUAL_SCOPE_NO_COMPLETION_PROMOTION");
    ++completed;
}
void allRows() {
    check(F::keys().size() == 1401 && F::sharedContextCount() == 11, "REUSED_SEALED_COHORT");
    std::map<int, std::size_t> counts;
    for (const auto& key : F::keys()) {
        const auto& d = F::definition(key); M::Task task(d); ++counts[d.level()];
        forms(task);
        check(task.sourcePolicy().level == d.level() && task.headingPath().front().rfind("SET ", 0) == 0, "EXACT_ROW_SET_LEVEL_POLICY_JOIN");
        const auto guidance = fathom::json::parse(task.fullSourceGuidanceJson());
        check(at(guidance, "manual_only").boolean() && at(guidance, "acoustic_sounding_span").null(), "FULL_GUIDANCE_MANUAL_BOUNDARY");
        check(at(at(guidance, "exact_unit"), "source_identity").string() == d.sourceIdentity()
            && at(at(guidance, "exact_unit"), "source_record_canonical_sha256").string() == d.sourceRecordSha256(), "FULL_GUIDANCE_ROW_PIN");
        normal(task, setup(task)); ++fullBranches;
        forms(task);
        // All keys retain the complete history/source identity; no per-key model logic.
        std::uint64_t revision = 0;
        for (const auto& history : task.history()) {
            check(history.sourceKey == key && history.revision == ++revision, "EVERY_ROW_IMMUTABLE_HISTORY_OWNER_IDENTITY");
            if (!history.manualReportJson.empty()) check(fathom::json::parse(history.manualReportJson).isObject(), "TYPED_REPORT_HISTORY_RETAINS_ACTUAL_FIELDS");
        }
        const auto& p = task.sourcePolicy();
        if (p.restoreAfterStable || p.restoreAfterAdvancement) {
            task.reportSession(task.capture(M::Action::SessionReport), external());
            for (const auto pulse : {M::Rhythm::Triplet, M::Rhythm::Quintuplet}) {
                task.restart(task.capture(M::Action::Restart));
                auto r = setup(task, pulse); r.branch = M::Branch::RestoredPulse;
                normal(task, r); ++restoredBranches;
                check(task.view().coverage.restoredPulseReported && task.view().coverage.printedPassProgressionReported,
                      "RESTORED_PULSE_DISTINCT_FROM_PRIOR_PRINTED_PASS_HISTORY");
            }
        }
    }
    const std::map<int, std::size_t> expected{{2,107},{3,216},{4,107},{5,108},{6,216},{7,107},{8,108},{9,108},{10,216},{11,108}};
    check(counts == expected, "ALL_LEVEL_SCOPE_DENOMINATORS");
}
void causal(int level, const F::Definition& definition) {
    M::Task task(definition), other(definition);
    auto r = setup(task);
    const auto begin = task.capture(M::Action::Begin);
    refuses([&] { other.begin(begin, setup(other)); }, &other);
    auto missing = r; missing.sourceSetupRead = M::Claim::Unknown;
    refuses([&] { task.begin(begin, missing); }, &task);
    if (level >= 8) {
        auto wrong = r; wrong.firstStart = F::Start::Up; refuses([&] { task.begin(begin, wrong); }, &task);
    }
    auto tempo = r; tempo.chosenBpm = 0; refuses([&] { task.begin(begin, tempo); }, &task);
    r.chosenBpm = 100;
    if (task.sourcePolicy().belowCleanMinimum) {
        r.previousCleanBpm = 100 + task.sourcePolicy().belowCleanMinimum;
        if (task.sourcePolicy().slowerOfTwoPreviousModes) r.otherPreviousModeCleanBpm = *r.previousCleanBpm + 4;
        auto wrong = r; wrong.chosenBpm = *r.previousCleanBpm;
        refuses([&] { task.begin(begin, wrong); }, &task);
    }
    task.begin(begin, r);
    refuses([&] { task.begin(begin, r); }, &task);
    const auto contact = task.capture(M::Action::Contact);
    refuses([&] { task.confirmContact(contact, 2, M::Claim::Yes); }, &task);
    refuses([&] { task.confirmContact(contact, 1, M::Claim::Unknown); }, &task);
    task.confirmContact(contact, 1, M::Claim::Yes); ++contactReports;
    refuses([&] { task.confirmContact(contact, 1, M::Claim::Yes); }, &task);
    refuses([&] { (void)task.capture(M::Action::Finish); }, &task);
    while (task.view().state == M::State::Traversal || task.view().state == M::State::Boundary) {
        if (task.view().state == M::State::Boundary) {
            const auto boundary = task.capture(M::Action::BoundaryReport);
            refuses([&] { task.reportBoundary(boundary, {}); }, &task);
            refuses([&] { (void)task.capture(M::Action::Contact); }, &task);
            task.reportBoundary(boundary, {M::Claim::Yes, M::Claim::Yes, M::Claim::Yes}); ++boundaryReports;
        }
        const auto cue = task.cue(); task.confirmContact(task.capture(M::Action::Contact), cue.ordinal, M::Claim::Yes); ++contactReports;
    }
    const auto release = task.capture(M::Action::Release);
    refuses([&] { task.release(release, M::Claim::No); }, &task);
    refuses([&] { (void)task.capture(M::Action::LoopReport); }, &task);
    task.release(release, M::Claim::Yes);
    const auto loop = task.capture(M::Action::LoopReport);
    refuses([&] { task.reportLoop(loop, {}); }, &task);
    check(task.view().state == M::State::Review, "UNKNOWN_REPORT_NOT_A_PERMANENT_TRAP");
    task.reportLoop(loop, {M::Observation::RisingTension, M::Claim::Yes});
    check(task.view().tempoReductionDue, "RISING_TENSION_IMMEDIATE_SOURCE_REDUCTION_DEBT");
    refuses([&] { (void)task.capture(M::Action::Retry); }, &task);
    task.cancel(task.capture(M::Action::Cancel));
    refuses([&] { (void)task.capture(M::Action::Restart); }, &task);
    task.release(task.capture(M::Action::Release), M::Claim::Yes);
    const auto historyCount = task.history().size();
    task.restart(task.capture(M::Action::Restart));
    check(task.view().tempoReductionDue && task.history().size() > historyCount, "CANCEL_RESTART_RETAINS_SAFETY_DEBT_AND_HISTORY");
    refuses([&] { (void)task.capture(M::Action::Begin); }, &task);
    const auto reduce = task.capture(M::Action::ReduceTempo);
    refuses([&] { task.reduceTempo(reduce, 3, M::Claim::Yes); }, &task);
    refuses([&] { task.reduceTempo(reduce, 4, M::Claim::Unknown); }, &task);
    task.reduceTempo(reduce, 4, M::Claim::Yes);
    check(task.view().reportedBpm == 96 && !task.view().tempoReductionDue, "ACTUAL_BOUNDED_REDUCTION_RECOVERY");
    auto replacement = setup(task); replacement.chosenBpm = 100;
    refuses([&] { task.begin(task.capture(M::Action::Begin), replacement); }, &task);
    replacement.chosenBpm = 96;
    normal(task, replacement);
    check(task.view().coverage.printedPassProgressionReported, "FULL_SAME_KEY_RECOVERY_THROUGH_ALL_SOURCE_PASSES");
    refuses([&] { (void)task.cue(); }, &task);
    auto days = external(); days.separateDayLabels = {"2026-09-30", "2026-09-30"};
    refuses([&] { task.reportSession(task.capture(M::Action::SessionReport), days); }, &task);
    days = external(); days.separateDayLabels = {"2026-02-30", "2026-09-30"};
    refuses([&] { task.reportSession(task.capture(M::Action::SessionReport), days); }, &task);
    task.reportSession(task.capture(M::Action::SessionReport), external());
    for (const auto extension : task.sourcePolicy().extensions) {
        const auto guidance = task.extensionGuidance(extension);
        check(!guidance.nativeAlternativeContactsSupplied && !guidance.sourceLines.empty()
             && !guidance.limitation.empty(), "ALTERNATIVE_GUIDANCE_HAS_NO_FAKE_REALIZATION");
        const auto token = task.capture(M::Action::ExtensionReport);
        refuses([&] { task.reportExtension(token, extension, M::Claim::Unknown); }, &task);
        if (extension == M::Extension::OtherPositionDistance) {
            refuses([&] { task.reportExtension(token, extension, M::Claim::Yes); }, &task);
            refuses([&] { task.reportDistanceExtension(token, {5, 5, 11}, M::Claim::Yes); }, &task);
            task.reportDistanceExtension(token, {5, 9, 13}, M::Claim::Yes);
        } else task.reportExtension(token, extension, M::Claim::Yes);
    }
}
void ownershipAndNavigation() {
    std::map<int, const F::Definition*> reps;
    for (const auto& key : F::keys()) reps.emplace(F::definition(key).level(), &F::definition(key));
    for (const auto& key : F::keys()) {
        const auto& original = F::definition(key);
        auto caller = original;
        M::Task task(caller);
        caller = *reps.at(original.level() == 2 ? 3 : 2);
        check(std::string(task.definition().sourceKey()) == key
            && task.definition().level() == original.level()
            && task.sourcePolicy().level == original.level()
            && std::string(task.definition().sourceRecordSha256()) == original.sourceRecordSha256(),
            "CALLER_ASSIGNMENT_CANNOT_REBIND_OWNED_SOURCE_OR_POLICY");
    }
    for (const auto& entry : reps) {
        std::unique_ptr<M::Task> retained;
        const auto key = std::string(entry.second->sourceKey());
        {
            auto caller = *entry.second;
            retained = std::make_unique<M::Task>(caller);
        }
        check(std::string(retained->definition().sourceKey()) == key
            && retained->definition().level() == entry.first
            && retained->sourcePolicy().level == entry.first, "CALLER_LIFETIME_DOES_NOT_OWN_TASK_SOURCE");
        retained->begin(retained->capture(M::Action::Begin), setup(*retained));
        check(retained->cue().ordinal == 1, "OWNED_SOURCE_USABLE_AFTER_CALLER_SCOPE");
        retained->cancel(retained->capture(M::Action::Cancel));
        retained->release(retained->capture(M::Action::Release), M::Claim::Yes);
    }
    const auto preserveFence = [](M::Task& task) {
        const auto old = task.view(); const auto history = task.history();
        const auto captured = task.capture(M::Action::SessionReport);
        task.deactivateForNavigation();
        const auto now = task.view();
        check(now.revision == old.revision + 1 && now.state == old.state
            && now.passIndex == old.passIndex && now.nextOrdinal == old.nextOrdinal
            && now.reportedBpm == old.reportedBpm && now.tempoReductionDue == old.tempoReductionDue
            && now.coverage.printedPassProgressionReported == old.coverage.printedPassProgressionReported
            && now.coverage.externalAdvancementConditionsReported == old.coverage.externalAdvancementConditionsReported
            && history.size() == task.history().size(), "INACTIVE_FENCE_PRESERVES_REPORTS_STATE_AND_DEBTS");
        for (std::size_t i = 0; i < history.size(); ++i) {
            const auto& a = history[i]; const auto& b = task.history()[i];
            check(a.revision == b.revision && a.action == b.action && a.sourceKey == b.sourceKey
                && a.detail == b.detail && a.passIndex == b.passIndex && a.start == b.start
                && a.observation == b.observation && a.manualReportJson == b.manualReportJson,
                "INACTIVE_FENCE_RETAINS_EXACT_HISTORY");
        }
        refuses([&] { task.reportSession(captured, external()); }, &task);
    };
    M::Task task(*reps.at(2));
    task.reportSession(task.capture(M::Action::SessionReport), external());
    preserveFence(task); // Setup with reports.
    task.begin(task.capture(M::Action::Begin), setup(task));
    refuses([&] { task.deactivateForNavigation(); }, &task); // Traversal.
    route(task);
    refuses([&] { task.deactivateForNavigation(); }, &task); // Review still active.
    task.oppositeStart(task.capture(M::Action::OppositeStart)); route(task);
    task.finish(task.capture(M::Action::Finish)); preserveFence(task);
    task.restart(task.capture(M::Action::Restart));
    task.begin(task.capture(M::Action::Begin), setup(task));
    route(task, M::Observation::RisingTension);
    task.cancel(task.capture(M::Action::Cancel));
    refuses([&] { task.deactivateForNavigation(); }, &task);
    refuses([&] { task.release(task.capture(M::Action::Release), M::Claim::Unknown); }, &task);
    task.release(task.capture(M::Action::Release), M::Claim::Yes);
    check(task.view().tempoReductionDue, "RELEASE_RETAINS_TEMPO_DEBT");
    preserveFence(task); // Cancelled, released, debt/history remain.
    M::Task boundary(*reps.at(9)); boundary.begin(boundary.capture(M::Action::Begin), setup(boundary));
    while (boundary.view().state == M::State::Traversal)
        boundary.confirmContact(boundary.capture(M::Action::Contact), boundary.cue().ordinal, M::Claim::Yes);
    check(boundary.view().state == M::State::Boundary, "BOUNDARY_NAVIGATION_FIXTURE");
    refuses([&] { boundary.deactivateForNavigation(); }, &boundary);
}
void representativeBranches() {
    std::map<int, const F::Definition*> reps;
    for (const auto& key : F::keys()) reps.emplace(F::definition(key).level(), &F::definition(key));
    for (const auto& entry : reps) {
        const auto level = entry.first; const auto& d = *entry.second;
        causal(level, d);
        if (M::policy(level).rotationAcrossSessions) {
            for (const auto pulse : {M::Rhythm::Triplet, M::Rhythm::Quintuplet}) {
                M::Task task(d); normal(task, setup(task, pulse));
                auto externalReport = external(); externalReport.nextSessionRhythm = M::Rhythm::StraightSixteenth;
                task.reportSession(task.capture(M::Action::SessionReport), externalReport);
                check(!task.view().reportedBpm, "NO_DEFAULT_BPM_ON_ROTATED_PULSE");
            }
        }
        if (M::policy(level).restoreAfterStable || M::policy(level).restoreAfterAdvancement) {
            M::Task task(d); auto r = setup(task, M::Rhythm::Triplet);
            refuses([&] { task.begin(task.capture(M::Action::Begin), r); }, &task);
            r.branch = M::Branch::RestoredPulse;
            refuses([&] { task.begin(task.capture(M::Action::Begin), r); }, &task);
        }
        // Source rule +2 next time is a reported plan; current BPM never changes.
        M::Task task(d); task.begin(task.capture(M::Action::Begin), setup(task));
        forms(task);
        route(task); task.oppositeStart(task.capture(M::Action::OppositeStart)); route(task);
        forms(task);
        refuses([&] { (void)task.capture(M::Action::PlanIncrease); }, &task);
        task.repeat(task.capture(M::Action::Repeat)); route(task);
        task.planIncreaseNextSession(task.capture(M::Action::PlanIncrease), M::Claim::Yes);
        check(!task.view().reportedBpm && !task.view().plannedNextSessionBpm, "UNKNOWN_TEMPO_PLUS_TWO_IS_NOT_FABRICATED_NUMBER");
        const auto retry = task.capture(M::Action::Retry); task.retry(retry); route(task);
        check(task.view().state == M::State::Review && !task.view().oppositeStartReported, "RETRY_REQUIRES_REPLACEMENT_ROUTE_START_AND_REPORTS");
        task.cancel(task.capture(M::Action::Cancel)); task.release(task.capture(M::Action::Release), M::Claim::Yes);
        check(task.view().state == M::State::Cancelled, "EXPLICIT_RELEASE_CLOSES_CANCEL");
    }
}
}
int main(int argc, char** argv) {
    try {
        check(argc == 2 || (argc == 3 && std::string(argv[2]) == "--ownership-only"), "REPO_ROOT_ARGUMENT");
        const auto start = std::chrono::steady_clock::now();
        ownershipAndNavigation();
        if (argc == 3) {
            std::cout << "{\"result\":\"PASS\",\"ownership_all_rows\":1401,\"caller_lifetime_policies\":10,"
                << "\"inactive_states\":3,\"assertions\":" << checks << ",\"refusals\":" << refusals
                << ",\"source_projection_matrix_replayed\":false}\n";
            return 0;
        }
        sourcePolicies(argv[1]); allRows(); representativeBranches();
        const auto seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        std::cout << "{\"result\":\"PASS\",\"all_rows\":1401,\"source_policy_groups\":10,\"full_printed_branch_flows\":" << fullBranches
            << ",\"restored_pulse_all_row_flows\":" << restoredBranches << ",\"completed_manual_test_flows\":" << completed
            << ",\"contact_reports\":" << contactReports << ",\"source_boundary_reports\":" << boundaryReports
            << ",\"manual_untimed_cues\":" << untimedCues << ",\"saved_selected_slot_cues\":" << sourceSlotCues
            << ",\"assertions\":" << checks << ",\"refusals\":" << refusals << ",\"seconds\":" << seconds
            << ",\"learner_action_descriptors_checked\":" << descriptors
            << ",\"source_original_rereads\":0,\"old_projection_proof_replayed\":false,\"whole_children_accepted\":0,\"runtime_admitted\":0}\n";
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
