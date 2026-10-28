#include "desktop/ProgressPresentation.hpp"
#include "desktop/LessonSelectionLabel.hpp"
#include "desktop/DiagnosticText.hpp"
#include "progression/InstalledDomainCatalog.hpp"
#include "progression/SelectedCaseComparison.hpp"
#include <iomanip>
#include <cstdint>
#include <map>
#include <set>
#include <sstream>

namespace fathom::desktop {
namespace {
using V = json::Value;
const V& field(const V& v, const std::string& name) {
    const auto* p = v.find(name);
    if (!p) throw progression::HistoryError("Missing presentation field: " + name);
    return *p;
}
std::string safe(const std::string& text) { return diagnosticField(text, 2048); }
std::string decimal(const Rational& value) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(3)
        << static_cast<double>(value.numerator()) / static_cast<double>(value.denominator());
    return out.str();
}
std::string quantity(const V* value) {
    return !value || value->null() ? "not available" : decimal(progression::quantity(*value));
}
// Calendar arithmetic uses the validated envelope's local day, never its UTC instant.
std::int64_t civilDays(int year, int month, int day) {
    year -= month <= 2;
    const auto era = (year >= 0 ? year : year - 399) / 400;
    const auto yearOfEra = static_cast<unsigned>(year - era * 400);
    const auto dayOfYear = static_cast<unsigned>((153 * (month + (month > 2 ? -3 : 9)) + 2) / 5 + day - 1);
    const auto yearOfEraDay = yearOfEra * 365U + yearOfEra / 4U - yearOfEra / 100U + dayOfYear;
    return static_cast<std::int64_t>(era) * 146097 + static_cast<std::int64_t>(yearOfEraDay) - 719468;
}
std::string civilDate(std::int64_t days) {
    days += 719468;
    const auto era = (days >= 0 ? days : days - 146096) / 146097;
    const auto dayOfEra = static_cast<unsigned>(days - era * 146097);
    const auto yearOfEra = (dayOfEra - dayOfEra / 1460 + dayOfEra / 36524 - dayOfEra / 146096) / 365;
    auto year = static_cast<int>(yearOfEra) + static_cast<int>(era * 400);
    const auto dayOfYear = dayOfEra - (365 * yearOfEra + yearOfEra / 4 - yearOfEra / 100);
    const auto marchMonth = (5 * dayOfYear + 2) / 153;
    const auto day = dayOfYear - (153 * marchMonth + 2) / 5 + 1;
    const auto month = static_cast<int>(marchMonth) + (marchMonth < 10 ? 3 : -9);
    year += month <= 2;
    std::ostringstream out;
    out << std::setfill('0') << std::setw(4) << year << '-' << std::setw(2) << month << '-' << std::setw(2) << day;
    return out.str();
}
std::pair<std::string, std::string> localWeek(const std::string& day) {
    if (day.size() != 10 || day[4] != '-' || day[7] != '-')
        throw progression::HistoryError("Invalid saved local practice day.");
    const auto days = civilDays(std::stoi(day.substr(0, 4)), std::stoi(day.substr(5, 2)),
                                std::stoi(day.substr(8, 2)));
    // 1970-01-01 was Thursday, three days after Monday.
    const auto mondayOffset = (days % 7 + 10) % 7;
    return {civilDate(days - mondayOffset), civilDate(days - mondayOffset + 6)};
}
std::string sourceLabel(const V& context, const V& facts, const std::shared_ptr<const lesson::Catalog>& catalog) {
    const auto item = field(context, "item_id").string();
    const auto variant = field(context, "variant_id").string();
    if (catalog) try {
        const auto& config = field(context, "configuration");
        auto admission = catalog->admit(item, variant);
        if (const auto* selection = field(config, "runtime_admission").find("selection")) {
            std::int64_t ordinal{};
            if (field(*selection, "version") != V("lesson-transfer-cell.1")
                || !field(*selection, "ordinal").integer(ordinal) || ordinal < 1 || ordinal > 5)
                throw progression::HistoryError("Unsupported historical section selection.");
            admission = catalog->admitCell(item, variant, static_cast<std::uint32_t>(ordinal));
        }
        bool exactContext = admission != nullptr;
        if (admission) {
            for (const auto* key : {"item_id", "variant_id", "content_revision", "content_version", "source_manifest_sha256", "source_refs"})
                exactContext = exactContext && field(context, key) == field(admission->identity(), key);
            const auto span = admission->span();
            const auto begin = admission->sourceStart();
            const auto end = begin + span;
            const V expectedSpan = V::Object{{"start", V::Array{V::fromInteger(begin.numerator()), V::fromInteger(begin.denominator())}},
                {"end", V::Array{V::fromInteger(end.numerator()), V::fromInteger(end.denominator())}}};
            const auto& target = field(field(config, "values"), "target_cycles");
            std::int64_t passes{};
            exactContext = exactContext && target.integer(passes) && passes >= 1
                && passes <= static_cast<std::int64_t>(lesson::Admission::maximumScheduledPasses)
                && field(context, "span") == expectedSpan
                && field(field(config, "values"), "span") == V(V::Array{V::fromInteger(span.numerator()), V::fromInteger(span.denominator())})
                && field(context, "target") == V(V::Object{{"cycles", target}})
                && field(config, "source_hashes") == field(admission->identity(), "source_hashes")
                && field(field(facts, "content"), "source_hashes") == field(admission->identity(), "source_hashes");
        }
        if (exactContext && field(config, "runtime_admission") == admission->identity()
            && field(config, "source_binding") == V(admission->sourceBinding())) {
            const auto& lesson = catalog->lesson(item);
            auto label = "Level " + std::to_string(lesson.level) + " | "
                + safe(catalog->variant(item, variant).label)
                + " | Lesson: " + safe(field(lesson.record, "title").string());
            const auto section = lessonSelectionLabel(*admission);
            if (!section.empty()) label += " | " + section;
            const auto& record = catalog->lesson(item).record;
            label += " | Workbook identity: " + safe(field(record, "workbook_id").string())
                + " | Level: " + storage::canonical(field(record, "legacy_level"));
            label += " | " + safe(item) + " / " + safe(variant) + " | Source:";
            for (const auto& ref : field(context, "source_refs").array())
                label += " " + safe(ref.string());
            label += " | Content version: " + safe(field(context, "content_version").string());
            label += " | Content revision: " + storage::canonical(field(context, "content_revision"));
            if (const auto* session = context.find("session_id"); session && session->isString() && !session->string().empty())
                label += " | Guided Session: " + safe(session->string());
            return label;
        }
    } catch (const std::exception&) {
        // Historical source labels cannot be substituted from an unrelated version.
    }
    return "Saved source " + safe(item) + " / " + safe(variant) + "\n"
        + "Content " + safe(field(context, "content_version").string())
        + " (current lesson title not verified)";
}
std::string previewBoundary(const std::shared_ptr<const lesson::Catalog>& catalog) {
    if (!catalog) return {};
    std::set<std::string> workbooks;
    std::size_t variants{};
    for (const auto& lesson : catalog->lessons()) {
        workbooks.insert(field(lesson.record, "workbook_id").string());
        variants += lesson.variants.size();
    }
    const auto sources = catalog->sourceEntryCount();
    const auto remaining = workbooks.size() < 105 ? 105 - workbooks.size() : 0;
    const auto additional = workbooks.size() > 13 ? workbooks.size() - 13 : 0;
    return "Currently prepared verified scope: " + std::to_string(catalog->lessons().size()) + " selected cases | "
        + std::to_string(variants) + " variants | " + std::to_string(sources) + " retained source entries | "
        + std::to_string(workbooks.size()) + " of 105 approved workbook identities prepared | "
        + std::to_string(remaining) + " are outside this prepared scope and remain discoverable in Learn and Exercise library | Additional workbook identities represented by selected cases: " + std::to_string(additional)
        + " | Comparisons use this prepared scope; saved history is retained independently | Whole-workbook completion from these cases: 0 | Curriculum review: Pending";
}
void notices(std::ostringstream& out, const V::Array& values) {
    for (const auto& row : values) {
        out << "Notice: ";
        if (row.isArray() && row.array().size() == 2 && row.array()[1].isString())
            out << safe(row.array()[1].string()) << " [" << safe(row.array()[0].string()) << "]";
        else out << safe(storage::canonical(row));
        out << '\n';
    }
}
}

ProgressPresentation presentProgress(const storage::Reply& reply, const std::string& asOf,
                                     std::shared_ptr<const lesson::Catalog> catalog) {
    const auto snapshot = progression::adaptSnapshot(reply);
    std::map<std::string, progression::Query> selected;
    for (const auto& record : snapshot.records) {
        if (record.kind != progression::Kind::Attempt && record.kind != progression::Kind::Source) continue;
        progression::Query query{record.item, record.condition, record.sourceScope};
        progression::validateQuery(query);
        selected.emplace(storage::canonical(progression::queryValue(query)), std::move(query));
    }
    std::vector<progression::Query> queries;
    for (const auto& entry : selected) queries.push_back(entry.second);
    ProgressPresentation result;
    result.projection = progression::projectSnapshot(snapshot, queries, asOf);
    std::size_t activities = 0, additional = 0;
    struct DayTotals { std::size_t attempts{}, freeplay{}; Rational attemptActive{}, freeplayActive{}; };
    std::map<std::string, DayTotals> byLocalDay;
    std::set<std::string> sessions;
    std::size_t attempts = 0, freeplay = 0;
    Rational attemptActive{}, freeplayActive{};
    std::ostringstream comparisonOut;
    if (catalog) {
        try {
            const auto comparison = progression::projectSelectedCaseComparison(snapshot, *catalog, asOf);
            result.projection.object()["selected_case_tempo_display"] = comparison;
            comparisonOut << "SELECTED-CASE PRACTICE COMPARISON (saved self-report; no mastery or module credit)\n";
            for (const auto& group : field(comparison, "groups").array()) {
                comparisonOut << safe(field(group, "item_id").string()) << " / "
                    << safe(field(group, "variant_id").string()) << " | version "
                    << safe(field(group, "content_version").string()) << " | selected span "
                    << safe(storage::canonical(field(group, "selected_span"))) << '\n';
                for (const auto& row : field(group, "rows").array()) {
                    comparisonOut << safe(field(row, "local_day").string()) << " | Session "
                        << safe(field(row, "session_id").string()) << " | Selected "
                        << storage::canonical(field(row, "selected_bpm")) << " BPM ("
                        << safe(field(row, "beat_unit").string()) << " beat) | self-reported Clean PB "
                        << storage::canonical(field(row, "clean_pb_bpm")) << " BPM";
                    if (!field(row, "prior_clean_pb_bpm").null())
                        comparisonOut << " (prior " << storage::canonical(field(row, "prior_clean_pb_bpm")) << " BPM)";
                    std::int64_t currentPb{}, previousPb{};
                    if (!field(row, "prior_clean_pb_bpm").null() &&
                        field(row, "clean_pb_bpm").integer(currentPb) &&
                        field(row, "prior_clean_pb_bpm").integer(previousPb) && currentPb > previousPb)
                        comparisonOut << " | self-reported clean PB improved from "
                            << storage::canonical(field(row, "prior_clean_pb_bpm")) << " to "
                            << storage::canonical(field(row, "clean_pb_bpm")) << " BPM";
                    comparisonOut << " | reliable saved-practice tempo ";
                    if (field(row, "reliable_bpm").null())
                        comparisonOut << "unavailable: " << safe(field(row, "reliable_reason").string());
                    else comparisonOut << storage::canonical(field(row, "reliable_bpm")) << " BPM";
                    comparisonOut << '\n';
                }
            }
            for (const auto& row : field(comparison, "unavailable").array())
                comparisonOut << "Comparison unavailable for saved Attempt " << safe(field(row, "original_owner").string())
                    << ": " << safe(field(row, "reason").string()) << " (history retained).\n";
            comparisonOut << "No source-verified completed module is available from these bounded selected cases.\n\n";
        } catch (const std::exception& error) {
            result.projection.object()["selected_case_tempo_display"] = V::Object{{"status", "unavailable"},
                {"reason", safe(error.what())}};
            comparisonOut << "Selected-case comparison unavailable: " << safe(error.what())
                << ". Saved history remains visible.\n\n";
        }
    }
    for (const auto& original : snapshot.originalHistory) {
        const auto kind = field(original, "kind").string();
        if (kind == "Attempt" || kind == "FreeplayActivity") ++activities;
        else ++additional;
        if (kind == "Attempt" || kind == "FreeplayActivity") {
            const auto envelope = storage::validateEnvelope(field(original, "bytes").string());
            auto& day = byLocalDay[envelope.day];
            if (kind == "Attempt") {
                ++attempts;
                ++day.attempts;
                attemptActive = attemptActive + envelope.active;
                day.attemptActive = day.attemptActive + envelope.active;
                const auto& context = field(envelope.value, "context");
                if (const auto* session = context.find("session_id"); session && session->isString())
                    sessions.insert(session->string());
            } else {
                ++freeplay;
                ++day.freeplay;
                freeplayActive = freeplayActive + envelope.active;
                day.freeplayActive = day.freeplayActive + envelope.active;
            }
        }
    }
    struct WeekTotals { std::size_t dates{}, attempts{}, freeplay{}; std::string end; };
    std::map<std::string, WeekTotals> byLocalWeek;
    for (const auto& [day, totals] : byLocalDay) {
        const auto [start, end] = localWeek(day);
        auto& week = byLocalWeek[start];
        week.end = end;
        ++week.dates;
        week.attempts += totals.attempts;
        week.freeplay += totals.freeplay;
    }
    std::ostringstream out;
    out << "SAVED PRACTICE\nRecorded facts from this profile. Opening Progress records no practice.\n"
        << "Finalized local records are shown read-only below; Progress does not recalculate or award curriculum credit.\n"
        << "Finalized local activity records in this snapshot: " << activities << "\n\n";
    out << "RECORDED HISTORY SUMMARY\n"
        << "Attempts: " << attempts << " in " << sessions.size() << " recorded Session(s) | active time: " << decimal(attemptActive) << " s\n"
        << "Freeplay activities: " << freeplay << " | active time: " << decimal(freeplayActive) << " s (kept separate from curriculum Attempts)\n"
        << "Practice dates: " << byLocalDay.size() << " distinct local dates with finalized records; this is history, not a score or streak.\n"
        << "Activity by local practice day:\n";
    if (byLocalDay.empty()) out << "No finalized local practice dates.\n";
    for (const auto& entry : byLocalDay)
        out << entry.first << " | Attempts: " << entry.second.attempts << " (" << decimal(entry.second.attemptActive)
            << " s) | Freeplay: " << entry.second.freeplay << " (" << decimal(entry.second.freeplayActive) << " s)\n";
    out << "Weekly recorded activity (local Monday-Sunday; finalized records only; not mastery, a score, streak or curriculum credit):\n";
    if (byLocalWeek.empty()) out << "No finalized local practice weeks.\n";
    for (const auto& [start, week] : byLocalWeek)
        out << start << " to " << week.end << " | Practice dates: " << week.dates
            << " | Attempts: " << week.attempts << " | Freeplay: " << week.freeplay << '\n';
    if (catalog) {
        try {
            const auto approved = progression::installedDomainCatalog(*catalog);
            const auto coverage = progression::projectDomainCoverage(
                snapshot, approved, snapshot.profile, progression::installedDomainManifests());
            V::Array unmapped;
            for (const auto& attempt : coverage.unmapped)
                unmapped.emplace_back(V::Object{{"original_owner", attempt.originalOwner}, {"reason", attempt.reason}});
            V::Array domains;
            for (const auto& [label, activity] : coverage.byDomain)
                domains.emplace_back(V::Object{{"label", label},
                    {"recorded_attempts", V::fromInteger(static_cast<std::int64_t>(activity.attempts))},
                    {"active_seconds", V::Array{V::fromInteger(activity.activeSeconds.numerator()),
                        V::fromInteger(activity.activeSeconds.denominator())}}});
            result.projection.object()["domain_coverage"] = V::Object{
                {"status", "mapped_recorded_activity"}, {"profile_id", coverage.profile},
                {"evidence_sha256", coverage.evidenceSha256}, {"snapshot_sha256", coverage.snapshotSha256},
                {"evidence_marker", V::fromInteger(coverage.evidenceMarker)},
                {"catalog_version", coverage.catalogVersion}, {"catalog_sha256", coverage.catalogSha256},
                {"mapped_attempts", V::fromInteger(static_cast<std::int64_t>(coverage.mappedAttempts))},
                {"separate_freeplay", V::fromInteger(static_cast<std::int64_t>(coverage.ignoredFreeplay))},
                {"domains", domains}, {"unmapped", unmapped}};
            out << "Domain coverage: source-verified recorded activity only; no technique quality, mastery, curriculum credit or whole-workbook completion is inferred.\n"
                << "Mapped Attempts: " << coverage.mappedAttempts << " | Freeplay kept separate: "
                << coverage.ignoredFreeplay << " | Unmapped Attempts: " << coverage.unmapped.size() << '\n';
            for (const auto& [label, activity] : coverage.byDomain)
                out << safe(label) << " | recorded Attempts: " << activity.attempts
                    << " | active time: " << decimal(activity.activeSeconds) << " s\n";
            for (const auto& attempt : coverage.unmapped)
                out << "Unmapped saved Attempt " << safe(attempt.originalOwner) << " | "
                    << safe(attempt.reason) << " (history retained; no domain inferred)\n";
            out << '\n';
        } catch (const std::exception& error) {
            result.projection.object()["domain_coverage"] = V::Object{{"status", "mapping_unavailable"},
                {"reason", safe(error.what())}};
            out << "Domain coverage: not computed; mapping unavailable for this installed catalog ("
                << safe(error.what()) << "). Saved history remains visible; no domain is inferred.\n\n";
        }
    } else {
        result.projection.object()["domain_coverage"] = V::Object{{"status", "mapping_unavailable"},
            {"reason", "No installed catalog was supplied"}};
        out << "Domain coverage: not computed; mapping unavailable without the installed catalog. Saved history remains visible; no domain is inferred.\n\n";
    }
    out << comparisonOut.str();
    for (const auto& original : snapshot.originalHistory) {
        const auto kind = field(original, "kind").string();
        if (kind != "Attempt" && kind != "FreeplayActivity") continue;
        const auto envelope = storage::validateEnvelope(field(original, "bytes").string());
        const auto& context = field(envelope.value, "context");
        const auto& facts = field(envelope.value, "result");
        out << (kind == "Attempt" ? sourceLabel(context, facts, catalog) : "Freeplay activity") << '\n';
        out << safe(envelope.practiceUtc) << " | " << safe(envelope.day) << " " << safe(envelope.timezone) << '\n';
        out << "Recorded active time: " << decimal(envelope.active) << " s\n";
        out << "Duration fact: recorded active time only; wall-clock duration is not inferred.\n";
        if (kind == "Attempt") {
            out << "Selected tempo: " << quantity(facts.find("selected_tempo"));
            const auto& config = field(context, "configuration");
            const auto* values = config.find("values");
            const auto* unit = values ? values->find("beat_unit") : nullptr;
            out << (unit && unit->isString() ? " BPM (" + safe(unit->string()) + " beat)" : " (beat unit not recorded)") << '\n';
            out << "Completed selected passes: " << field(facts, "completed_cycles").array().size() << '\n';
            std::size_t partial = 0;
            for (const auto& traversal : field(facts, "traversals").array())
                if (field(traversal, "status") != V("complete")) ++partial;
            out << "Earlier/ended partial traversals retained: " << partial << '\n';
            if (const auto* scope = config.find("selected_scope_notice"); scope && scope->isString())
                out << safe(scope->string()) << '\n';
            out << "Selected passes do not establish source-task completion.\n";
        } else out << "Freeplay is separate from curriculum progression.\n";
        out << "Self-assessment: " << (envelope.assessment ? safe(*envelope.assessment) + " (self-report)" : "not provided")
            << "\nOutcome: " << safe(envelope.outcome) << "\nOriginal: " << envelope.owner << "\n\n";
    }
    if (!activities) {
        const auto boundary = previewBoundary(catalog);
        if (!boundary.empty()) out << boundary << '\n';
        out << "No finalized practice activity in this snapshot.\n";
        out << "Progress is read-only here: it shows finalized local activity only and does not create, estimate or award curriculum progress.\n";
        out << "Start with Learn: choose an admitted source-backed case, complete the explicit Practice action, use Save result, then return here to review the recorded facts.\n";
        out << "Freeplay activity is recorded separately.\n\n";
    }
    if (additional) out << additional << " additional original evidence records retained in Details.\n\n";
    notices(out, snapshot.notices);
    out << "\nRULE / COMPARISON STATE\nThis classification is separate from the saved practice above.\n";
    for (const auto& view : field(result.projection, "views").array()) {
        const auto& query = field(view, "query");
        const auto& projection = field(view, "projection");
        out << '\n' << safe(field(query, "item").string());
        const auto& scope = field(query, "source_scope");
        out << " / " << safe(field(scope, "variant_id").string()) << '\n';
        out << "Rule state: " << safe(field(projection, "state").string()) << '\n';
        if (field(query, "condition").null())
            out << "Source-rule assessment unavailable for this bounded case. Saved practice remains visible; no source mastery or credit is inferred.\n";
        out << "Attempted maximum (including incomplete attempt evidence): " << quantity(projection.find("attempted_maximum"))
            << " BPM; this is separate from a clean personal best.\n"
            << "Evidence in this comparison: " << storage::canonical(field(projection, "positive_count")) << " positive Attempt(s), "
            << storage::canonical(field(projection, "success_count")) << " complete Clean/Easy Attempt(s).\n";
        out << "Clean PB: " << quantity(projection.find("pb"))
            << " | Reliable tempo: " << quantity(projection.find("reliable")) << '\n';
        out << "Source-task completion credited: " << (field(projection, "source_complete").boolean() ? "yes" : "no")
            << " | Review due: " << (field(projection, "review_due").boolean() ? "yes" : "no") << '\n';
        const auto& dueAt = field(projection, "due_at");
        if (dueAt.isString()) {
            out << "Review date: " << safe(dueAt.string()) << " | "
                << (field(projection, "review_due").boolean()
                    ? "due as of this snapshot; choose an explicit Practice session to add new evidence."
                    : "not yet due as of this snapshot.") << '\n';
        } else out << "Review date: not scheduled by the current rule state.\n";
        const auto& weak = field(projection, "weak");
        if (weak.isString()) {
            const auto& weakAt = field(projection, "weak_at");
            out << "Recent lower self-report: " << safe(weak.string()) << " (self-report)"
                << (weakAt.isString() ? " on " + safe(weakAt.string()) : std::string{})
                << "; this is not an instrument-derived score.\n";
        }
        notices(out, field(projection, "notices").array());
    }
    if (queries.empty()) out << "No exact curriculum query is available in this snapshot.\n";
    result.text = out.str();
    result.details = storage::canonical(result.projection);
    return result;
}
}
