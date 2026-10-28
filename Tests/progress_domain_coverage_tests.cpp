#include "progression/ProgressDomainCoverage.hpp"
#include <iostream>
#include <stdexcept>

using namespace fathom;
using namespace fathom::progression;
namespace {
int checks = 0;
void check(bool ok, const char* label) {
    ++checks;
    if (!ok) throw std::runtime_error(label);
}
template<class F> void refuses(F&& action, const char* label) {
    bool rejected = false;
    try { action(); } catch (const DomainCoverageError&) { rejected = true; }
    check(rejected, label);
}
std::string digest(char c) { return std::string(64, c); }
constexpr const char* profile = "00000000-0000-4000-8000-000000000014";
json::Value scope(const DomainBinding& b) {
    json::Value::Array refs;
    for (const auto& ref : b.sourceRefs) refs.emplace_back(ref);
    return json::Value::Object{{"item_id", b.item}, {"variant_id", b.variant},
        {"content_revision", json::Value::fromInteger(b.contentRevision)},
        {"content_version", b.contentVersion}, {"source_manifest_sha256", b.sourceManifestSha256},
        {"source_refs", refs}, {"span", json::Value::Object{}}, {"target", json::Value::Object{}}};
}
Evidence attempt(std::string owner, const DomainBinding& b, Rational active = Rational(5, 2)) {
    Evidence e;
    e.kind = Kind::Attempt;
    e.key = std::move(owner);
    e.item = b.item;
    e.sourceScope = scope(b);
    e.active = active;
    e.originalBytes = "unchanged original bytes";
    return e;
}
SnapshotEvidence snapshot() {
    SnapshotEvidence s;
    s.profile = profile;
    s.evidenceHash = digest('a');
    s.snapshotHash = digest('b');
    s.marker = 4;
    return s;
}
DomainCatalog catalog() {
    DomainCatalog c;
    c.version = "p14-test-explicit-map.1";
    c.contentManifestSha256 = digest('c');
    c.entries.push_back({{"fg:item:000001", "fg:variant:000001", "representative-test.1", digest('c'), 3,
        {"L1-TXT2-15"}}, {"Technique/fretboard", "Rhythm/groove"}, "fixture:approved-map-entry-1", digest('d')});
    c.entries.push_back({{"fg:item:000002", "fg:variant:000006", "representative-test.1", digest('c'), 2,
        {"L3-TXT5-21", "L3-TXT28-46"}}, {"Technique/fretboard"}, "fixture:approved-map-entry-2", digest('e')});
    return c;
}
}
int main() {
    try {
        auto c = catalog();
        auto s = snapshot();
        const auto original = attempt("first", c.entries[0].binding);
        s.records.push_back(original);
        s.records.push_back(attempt("second", c.entries[1].binding, Rational(3)));
        auto older = attempt("old", c.entries[0].binding);
        older.sourceScope.object()["content_revision"] = json::Value::fromInteger(2);
        s.records.push_back(older);
        auto unknown = attempt("unknown", c.entries[0].binding);
        unknown.sourceScope.object()["item_id"] = "fg:item:000099";
        s.records.push_back(unknown);
        auto otherVariant = attempt("variant", c.entries[0].binding);
        otherVariant.sourceScope.object()["variant_id"] = "fg:variant:000099";
        s.records.push_back(otherVariant);
        auto oldVersion = attempt("version", c.entries[0].binding);
        oldVersion.sourceScope.object()["content_version"] = "historical.1";
        s.records.push_back(oldVersion);
        auto oldManifest = attempt("manifest", c.entries[0].binding);
        oldManifest.sourceScope.object()["source_manifest_sha256"] = digest('f');
        s.records.push_back(oldManifest);
        auto changedRefs = attempt("refs", c.entries[0].binding);
        changedRefs.sourceScope.object()["source_refs"] = json::Value::Array{"other-source"};
        s.records.push_back(changedRefs);
        auto freeplay = attempt("freeplay", c.entries[0].binding);
        freeplay.kind = Kind::Freeplay;
        s.records.push_back(freeplay);
        s.records.push_back(attempt("zero", c.entries[0].binding, Rational{}));
        auto uncommitted = attempt("uncommitted", c.entries[0].binding);
        uncommitted.status = "unresolved";
        s.records.push_back(uncommitted);
        auto source = attempt("source", c.entries[0].binding);
        source.kind = Kind::Source;
        s.records.push_back(source);

        const auto projected = projectDomainCoverage(s, c, profile, digest('c'));
        check(projected.profile == profile && projected.evidenceSha256 == digest('a')
              && projected.snapshotSha256 == digest('b') && projected.evidenceMarker == 4,
              "retains original profile and snapshot identity");
        check(projected.catalogVersion == c.version && projected.catalogSha256.size() == 64,
              "catalog version and exact digest retained");
        check(projected.mappedAttempts == 2 && projected.ignoredFreeplay == 1,
              "only two committed, positive mapped Attempts count");
        check(projected.byDomain.size() == 2 && projected.overlappingDomainActivity,
              "explicit overlapping domain rows only");
        check(projected.byDomain.at("Technique/fretboard").attempts == 2
              && projected.byDomain.at("Technique/fretboard").activeSeconds == Rational(11, 2),
              "exact rational activity across two mapped Attempts");
        check(projected.byDomain.at("Rhythm/groove").attempts == 1
              && projected.byDomain.at("Rhythm/groove").activeSeconds == Rational(5, 2),
              "multi-domain Attempt remains visibly overlapping");
        check(projected.unmapped.size() == 6, "six source-identity mismatches reported");
        check(projected.unmapped[0].originalOwner == "old"
              && projected.unmapped[0].reason == "content_revision_mismatch", "old revision not remapped");
        check(projected.unmapped[1].reason == "unknown_item"
              && projected.unmapped[2].reason == "unknown_variant"
              && projected.unmapped[3].reason == "content_version_mismatch"
              && projected.unmapped[4].reason == "source_manifest_mismatch"
              && projected.unmapped[5].reason == "source_refs_mismatch",
              "each unmatched historical reason explicit");
        check(s.records[0].originalBytes == original.originalBytes && s.records[0].active == original.active,
              "read-only projection leaves original evidence unchanged");

        refuses([&] { projectDomainCoverage(s, c, "another-profile", digest('c')); }, "foreign profile refused");
        refuses([&] { projectDomainCoverage(s, c, profile, digest('f')); }, "wrong expected manifest refused");
        auto bad = c;
        bad.entries[0].domains.push_back("Technique/fretboard");
        refuses([&] { projectDomainCoverage(s, bad, profile, digest('c')); }, "duplicate domain refused");
        bad = c;
        bad.entries.push_back(bad.entries[0]);
        refuses([&] { projectDomainCoverage(s, bad, profile, digest('c')); }, "duplicate source binding refused");
        bad = c;
        bad.entries[0].provenanceSha256.clear();
        refuses([&] { projectDomainCoverage(s, bad, profile, digest('c')); }, "missing authority provenance refused");
        bad = c;
        bad.entries[0].binding.sourceManifestSha256 = digest('f');
        refuses([&] { projectDomainCoverage(s, bad, profile, digest('c')); }, "catalog source manifest mismatch refused");
        auto malformed = s;
        malformed.records[0].sourceScope.object().erase("source_refs");
        refuses([&] { projectDomainCoverage(malformed, c, profile, digest('c')); }, "malformed saved scope refused");
        malformed = s;
        malformed.records.push_back(malformed.records[0]);
        refuses([&] { projectDomainCoverage(malformed, c, profile, digest('c')); }, "duplicate original owner refused");
        storage::Reply unconfirmed;
        unconfirmed.status = storage::Status::DefiniteFailure;
        bool adapterRefused = false;
        try { projectDomainCoverage(unconfirmed, c, profile, digest('c')); }
        catch (const HistoryError&) { adapterRefused = true; }
        check(adapterRefused, "unconfirmed store Reply refused by the authoritative adapter");
        std::cout << "PASS " << checks << " explicit Progress domain coverage checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n';
        return 1;
    }
}
