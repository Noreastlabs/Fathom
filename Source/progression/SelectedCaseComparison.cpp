#include "progression/SelectedCaseComparison.hpp"
#include "content/Canonical.hpp"
#include "core/GuitarSetup.hpp"
#include <algorithm>
#include <map>
#include <set>
#include <stdexcept>
#include <tuple>

namespace fathom::progression {
namespace {
using V = json::Value;
using A = V::Array;
using O = V::Object;
void need(bool ok, const char* reason) { if (!ok) throw HistoryError(reason); }
const V& at(const V& value, const char* key) {
    const auto* found = value.find(key);
    need(found != nullptr, "Missing selected-case comparison field");
    return *found;
}
std::int64_t integer(const V& value) {
    std::int64_t result{};
    need(value.integer(result), "Invalid selected-case comparison integer");
    return result;
}
V q(const Rational& value) {
    return A{V::fromInteger(value.numerator()), V::fromInteger(value.denominator())};
}
void validateSetup(const V& value) {
    need(value.isObject() && value.object().size() == 6, "Declared setup unavailable or unsupported");
    need(at(value, "value_version") == V("instrument-initial1"), "Declared setup version unavailable");
    const auto& pitches = at(value, "open_midi");
    need(pitches.isArray() && pitches.array().size() == 6, "Declared tuning unavailable");
    guitar::Setup setup;
    for (std::size_t i = 0; i < 6; ++i) {
        const auto n = integer(pitches.array()[i]);
        need(n >= 0 && n <= 127, "Declared tuning out of range");
        setup.openMidi[i] = static_cast<int>(n);
    }
    const auto capo = integer(at(value, "capo"));
    const auto frets = integer(at(value, "fret_count"));
    need(capo >= 0 && capo <= 36 && frets >= 0 && frets <= 36, "Declared setup out of range");
    setup.capo = static_cast<int>(capo);
    setup.fretCount = static_cast<int>(frets);
    const auto& hand = at(value, "handedness");
    need(hand.isString() && (hand == V("left") || hand == V("right")), "Declared handedness unavailable");
    setup.handedness = hand == V("left") ? guitar::Handedness::Left : guitar::Handedness::Right;
    need(at(value, "physical_tuning_verified") == V(false), "Physical tuning claim unsupported");
    need(guitar::validate(setup).empty(), "Declared setup invalid");
    // The exact production shape is part of the comparison contract.
    need(value.object().count("value_version") && value.object().count("open_midi") &&
         value.object().count("capo") && value.object().count("fret_count") &&
         value.object().count("handedness") && value.object().count("physical_tuning_verified"),
         "Declared setup fields unavailable");
}
struct Qualified {
    std::string owner, utc, day, session, item, variant, beatUnit, contentVersion;
    std::int64_t bpm{};
    V span, identity, setup;
};
struct Group { std::vector<Qualified> rows; };
std::pair<std::string, Qualified> qualify(const Evidence& evidence, const lesson::Catalog& catalog,
                                          const std::string& asOfUtc) {
    const auto envelope = storage::validateEnvelope(evidence.originalBytes);
    need(envelope.kind == "Attempt" && evidence.kind == Kind::Attempt && envelope.owner == evidence.key,
         "Not a finalized Attempt");
    need(utcMicros(envelope.practiceUtc) <= utcMicros(asOfUtc), "Practice date follows projection time");
    const auto& context = at(envelope.value, "context");
    const auto& config = at(context, "configuration");
    const auto& values = at(config, "values");
    const auto& result = at(envelope.value, "result");
    need(config.isObject() && values.isObject() && result.isObject(), "Comparison configuration unavailable");
    need(config.find("lesson_tempo") == nullptr, "Initial tempo ramp selected");
    need(config.find("progression_condition") == nullptr && at(config, "source_task_completion") == V(false)
         && at(config, "synthetic_fixture") == V(false), "Unsupported source-credit or synthetic context");
    need(at(result, "configuration") == config, "Result configuration differs from allocation");
    validateSetup(at(config, "declared_instrument_setup"));
    need(envelope.assessment && (*envelope.assessment == "Clean" || *envelope.assessment == "Easy"),
         "No Clean/Easy self-report");
    need(envelope.active.numerator() > 0 && (at(result, "outcome") == V("natural")
         || at(result, "outcome") == V("stop")),
         "Selected target not positively ended");
    const auto& item = at(context, "item_id");
    const auto& variant = at(context, "variant_id");
    need(item.isString() && variant.isString(), "Selected identity unavailable");
    std::shared_ptr<const lesson::Admission> admission;
    const auto& runtime = at(config, "runtime_admission");
    if (const auto* selection = runtime.find("selection")) {
        need(at(*selection, "version") == V("lesson-transfer-cell.1"), "Unsupported selected cell");
        const auto ordinal = integer(at(*selection, "ordinal"));
        need(ordinal >= 1 && ordinal <= 5, "Selected cell ordinal unavailable");
        admission = catalog.admitCell(item.string(), variant.string(), static_cast<std::uint32_t>(ordinal));
    } else admission = catalog.admit(item.string(), variant.string());
    need(admission != nullptr, "Current runtime admission unavailable");
    const auto& identity = admission->identity();
    need(runtime == identity && at(config, "source_binding") == V(admission->sourceBinding())
         && at(config, "source_hashes") == at(identity, "source_hashes")
         && at(at(result, "content"), "source_hashes") == at(identity, "source_hashes"),
         "Admission or source binding changed");
    for (const auto* field : {"item_id", "variant_id", "content_revision", "content_version",
                               "source_manifest_sha256", "source_refs"})
        need(at(context, field) == at(identity, field), "Selected source identity changed");
    const auto begin = admission->sourceStart();
    const auto span = admission->span();
    const V expectedSpan = O{{"start", q(begin)}, {"end", q(begin + span)}};
    need(at(context, "span") == expectedSpan && at(values, "span") == q(span),
         "Selected source span changed");
    const auto target = integer(at(values, "target_cycles"));
    need(target > 0 && target <= static_cast<std::int64_t>(lesson::Admission::maximumScheduledPasses)
         && at(context, "target") == V(O{{"cycles", V::fromInteger(target)}}),
         "Selected target changed");
    const auto bpm = integer(at(values, "selected_bpm"));
    need(bpm > 0 && bpm <= 300 && at(result, "selected_tempo") == q(Rational(bpm)),
         "Selected scalar tempo unavailable");
    need(at(config, "beat_reference_q") == q(Rational(1)) && at(config, "lesson_metronome").isObject(),
         "Beat reference or metronome unavailable");
    const auto& cycles = at(result, "completed_cycles");
    const auto& traversals = at(result, "traversals");
    need(cycles.isArray() && traversals.isArray(), "Selected target proof unavailable");
    std::set<std::string> completed, full;
    for (const auto& cycle : cycles.array())
        need(completed.insert(storage::canonical(cycle)).second, "Duplicate completed cycle");
    need(completed.size() >= static_cast<std::size_t>(target), "Selected target incomplete");
    for (const auto& traversal : traversals.array()) {
        if (at(traversal, "status") != V("complete")) continue;
        const auto token = storage::canonical(at(traversal, "cycle"));
        need(completed.count(token) && full.insert(token).second, "Conflicting complete traversal");
        need(at(traversal, "start") == at(expectedSpan, "start")
             && at(traversal, "end") == at(expectedSpan, "end"), "Traversal differs from selected span");
    }
    need(full == completed, "Full selected-span traversal unavailable");
    const auto& segments = at(result, "tempo_segments");
    need(segments.isArray() && !segments.array().empty(), "Confirmed tempo segments unavailable");
    Rational cursor;
    for (const auto& segment : segments.array()) {
        const auto start = quantity(at(segment, "start_at"));
        const auto end = quantity(at(segment, "end_at"));
        const auto duration = quantity(at(segment, "confirmed_duration"));
        need(duration.numerator() > 0 && start == cursor && start + duration == end
             && quantity(at(segment, "tempo")) == Rational(bpm),
             "Mixed, gapped, or unconfirmed tempo segments");
        cursor = end;
    }
    need(cursor == envelope.active, "Tempo coverage differs from confirmed active time");
    auto keyValues = values;
    keyValues.object().erase("selected_bpm");
    const V key = O{{"admission", identity}, {"source_hashes", at(config, "source_hashes")},
        {"span", expectedSpan}, {"target", at(context, "target")},
        {"values_except_selected_bpm", keyValues},
        {"beat_reference_q", at(config, "beat_reference_q")},
        {"lesson_metronome", at(config, "lesson_metronome")},
        {"declared_instrument_setup", at(config, "declared_instrument_setup")}};
    const auto hash = content::sha256(storage::canonical(key));
    const auto& beat = at(values, "beat_unit");
    need(beat.isString(), "Beat unit unavailable");
    return {hash, Qualified{evidence.key, envelope.practiceUtc, envelope.day,
        at(context, "session_id").string(), item.string(), variant.string(), beat.string(),
        at(context, "content_version").string(), bpm, expectedSpan, identity,
        at(config, "declared_instrument_setup")}};
}
}

Value projectSelectedCaseComparison(const SnapshotEvidence& snapshot, const lesson::Catalog& catalog,
                                    const std::string& asOfUtc) {
    utcMicros(asOfUtc);
    const auto& acceptedRule = initialRules();
    const auto& reliability = at(acceptedRule, "reliable");
    need(at(acceptedRule, "version") == V("progress-initial1")
         && at(reliability, "attempts") == V::fromInteger(3)
         && at(reliability, "days") == V::fromInteger(2)
         && at(reliability, "sessions") == V::fromInteger(2),
         "Accepted saved-practice reliability rule changed");
    std::map<std::string, Group> groups;
    A unavailable;
    std::map<std::string, std::size_t> owners;
    for (const auto& evidence : snapshot.records)
        if (evidence.kind == Kind::Attempt) ++owners[evidence.key];
    for (const auto& evidence : snapshot.records) {
        if (evidence.kind != Kind::Attempt) continue;
        if (owners[evidence.key] != 1) {
            unavailable.emplace_back(O{{"original_owner", evidence.key}, {"reason", "Duplicate original owner"}});
            continue;
        }
        try {
            auto [hash, row] = qualify(evidence, catalog, asOfUtc);
            groups[hash].rows.push_back(std::move(row));
        } catch (const std::exception& error) {
            unavailable.emplace_back(O{{"original_owner", evidence.key}, {"reason", error.what()}});
        }
    }
    A projectedGroups;
    for (auto& [hash, group] : groups) {
        auto& rows = group.rows;
        std::sort(rows.begin(), rows.end(), [](const Qualified& left, const Qualified& right) {
            return std::tie(left.utc, left.owner) < std::tie(right.utc, right.owner);
        });
        A projectedRows;
        std::int64_t pb = 0;
        for (std::size_t i = 0; i < rows.size(); ++i) {
            const auto& row = rows[i];
            const auto prior = pb;
            pb = std::max(pb, row.bpm);
            std::int64_t reliable = 0;
            for (std::size_t candidate = 0; candidate <= i; ++candidate) {
                const auto threshold = rows[candidate].bpm;
                std::set<std::string> days, sessions, distinct;
                for (std::size_t j = 0; j <= i; ++j) if (rows[j].bpm >= threshold) {
                    days.insert(rows[j].day);
                    sessions.insert(rows[j].session);
                    distinct.insert(rows[j].owner);
                }
                if (distinct.size() >= 3 && days.size() >= 2 && sessions.size() >= 2)
                    reliable = std::max(reliable, threshold);
            }
            projectedRows.emplace_back(O{{"original_owner", row.owner}, {"practice_utc", row.utc},
                {"local_day", row.day}, {"session_id", row.session},
                {"selected_bpm", V::fromInteger(row.bpm)}, {"beat_unit", row.beatUnit},
                {"prior_clean_pb_bpm", prior ? V::fromInteger(prior) : V{}},
                {"clean_pb_bpm", V::fromInteger(pb)},
                {"reliable_bpm", reliable ? V::fromInteger(reliable) : V{}},
                {"reliable_reason", reliable ? "" : "Fewer than 3 qualifying Attempts across 2 local days and 2 Sessions"}});
        }
        const auto& first = rows.front();
        projectedGroups.emplace_back(O{{"comparison_key_sha256", hash},
            {"item_id", first.item}, {"variant_id", first.variant},
            {"content_version", first.contentVersion}, {"selected_span", first.span},
            {"admission", first.identity}, {"declared_instrument_setup", first.setup},
            {"rows", projectedRows}});
    }
    return O{{"version", "selected_case_tempo_display.1"}, {"profile_id", snapshot.profile},
        {"evidence_sha256", snapshot.evidenceHash}, {"snapshot_sha256", snapshot.snapshotHash},
        {"evidence_marker", V::fromInteger(snapshot.marker)}, {"as_of_utc", asOfUtc},
        {"rule_version", "progress-initial1"}, {"rule_sha256", rulesIdentity()},
        {"groups", projectedGroups}, {"unavailable", unavailable},
        {"source_rule_assessment", "unavailable for bounded selected cases"},
        {"completed_module", "No source-verified completed module is available from these bounded selected cases."}};
}
} // namespace fathom::progression
