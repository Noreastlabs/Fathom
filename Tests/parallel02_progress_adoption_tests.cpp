#include "desktop/ProgressPresentation.hpp"
#include "progression/InstalledDomainCatalog.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <array>

using namespace fathom;
namespace {
using V = json::Value;
int checks{};
void check(bool good, const char* name) {
    ++checks;
    if (!good) throw std::runtime_error(name);
}
V read(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("Missing fixture: " + path.string());
    return json::parse(std::string(std::istreambuf_iterator<char>(input), {}));
}
storage::Reply confirmed(storage::ProfileStore::Future future) {
    auto reply = future.get();
    if (reply.status != storage::Status::Confirmed)
        throw std::runtime_error("Disposable Store refused: " + reply.code + " " + reply.message);
    return reply;
}
V strings(const std::vector<std::string>& values) {
    V::Array out;
    for (const auto& value : values) out.emplace_back(value);
    return out;
}
V attempt(V value, const progression::DomainBinding& binding, const lesson::Catalog& installed) {
    const auto identity = installed.admit(binding.item, binding.variant)->identity();
    auto& context = value.object().at("context").object();
    context["item_id"] = binding.item;
    context["variant_id"] = binding.variant;
    context["content_revision"] = V::fromInteger(binding.contentRevision);
    context["content_version"] = binding.contentVersion;
    context["source_manifest_sha256"] = binding.sourceManifestSha256;
    context["source_refs"] = strings(binding.sourceRefs);
    context.at("configuration").object()["canonical_variant_id"] = binding.variant;
    auto& content = value.object().at("result").object().at("content").object();
    content["id"] = binding.item;
    content["content_revision"] = V::fromInteger(binding.contentRevision);
    content["content_version"] = binding.contentVersion;
    content["source_manifest_sha256"] = binding.sourceManifestSha256;
    content["source_refs"] = strings(binding.sourceRefs);
    content["source_hashes"] = identity.object().at("source_hashes");
    content["legacy_level"] = installed.lesson(binding.item).level;
    return value;
}
void save(storage::ProfileStore& store, V value, const std::string& kind,
          const std::string& stamp) {
    auto& context = value.object().at("context");
    if (kind == "Attempt") {
        const auto session = confirmed(store.createSession("session/" + stamp, stamp, "UTC", {},
            V::Object{{"synthetic_fixture", true}, {"purpose", "disposable Progress adoption proof"}}));
        context.object()["session_id"] = session.data.object().at("session_id");
    }
    auto& practice = value.object().at("practice");
    practice.object()["practice_utc"] = stamp;
    practice.object()["local_day"] = stamp.substr(0, 10);
    practice.object()["timezone"] = "UTC";
    value.object().at("result").object()["configuration"] = context.object().at("configuration");
    const auto allocation = confirmed(store.allocate("allocate/" + stamp, kind, context, stamp));
    const auto owner = allocation.data.object().at("owner").string();
    value.object()["owner"] = owner;
    value.object().at("result").object()["key"] = owner;
    const auto bytes = storage::canonical(value);
    confirmed(store.seal("seal/" + stamp, owner, bytes));
    confirmed(store.commit("commit/" + stamp, owner, bytes));
}
const V& field(const V& value, const char* name) { return value.object().at(name); }
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 4) throw std::runtime_error("Expected installed Resources, fixture directory and fresh Store directory");
        const std::filesystem::path resources = argv[1], fixtures = argv[2], scratch = argv[3];
        check(scratch.is_absolute() && !std::filesystem::exists(scratch), "fresh disposable Store path");
        std::filesystem::create_directories(scratch);
        std::filesystem::permissions(scratch, std::filesystem::perms::owner_all,
            std::filesystem::perm_options::replace);
        const auto installed = lesson::Catalog::loadInstalled(resources / "representative-controls",
            {resources / "rung02-extension", resources / "rung03-extension",
             resources / "rung04-extension", resources / "level006-extension",
             resources / "rung05-extension", resources / "level008-extension", resources / "level010-extension",
             resources / "level007-extension", resources / "level009-extension", resources / "level011-extension",
             resources / "level013-extension", resources / "level014-extension", resources / "level015-extension", resources / "level016-extension", resources / "level017-extension", resources / "level018-extension", resources / "level019-extension", resources / "level020-extension", resources / "level021-extension", resources / "level022-extension", resources / "level023-extension", resources / "level024-extension", resources / "level030-extension", resources / "level029-extension", resources / "level025-extension", resources / "level026-extension"});
        const auto bindings = progression::installedDomainCatalog(*installed);
        storage::StoreOptions options;
        options.path = scratch / "profile.sqlite";
        options.create = true;
        options.createdUtc = "2026-09-01T00:00:00Z";
        options.sourceValidator = [](const V&) { return true; }; // Disposable synthetic fixture only.
        auto store = std::make_unique<storage::ProfileStore>(options);
        const auto empty = confirmed(store->snapshot("progress-adoption-empty"));
        const auto emptyView = desktop::presentProgress(empty, "2026-09-24T00:00:00Z", installed);
        check(field(field(emptyView.projection, "domain_coverage"), "status") == V("mapped_recorded_activity")
            && emptyView.text.find("Mapped Attempts: 0") != std::string::npos,
            "empty confirmed profile shows zero mapped activity without inventing credit");
        const auto fixture = read(fixtures / "attempt.json");
        const std::array<std::string, 8> stamps{{"2026-09-14T10:00:00Z", "2026-09-14T11:00:00Z",
            "2026-09-15T12:00:00Z", "2026-09-22T10:00:00Z",
            "2026-09-23T11:00:00Z", "2026-09-23T12:00:00Z",
            "2026-09-23T14:00:00Z", "2026-09-23T15:00:00Z"}};
        const std::array<const progression::DomainBinding*, 8> selected{{
            &bindings.catalogs[0].entries[0].binding, &bindings.catalogs[0].entries[4].binding,
            &bindings.catalogs[1].entries[0].binding, &bindings.catalogs[2].entries[0].binding,
            &bindings.catalogs[3].entries[0].binding, &bindings.catalogs[4].entries[0].binding,
            &bindings.catalogs[5].entries[0].binding, &bindings.catalogs[5].entries[1].binding}};
        for (std::size_t i = 0; i < selected.size(); ++i)
            save(*store, attempt(fixture, *selected[i], *installed), "Attempt", stamps[i]);
        save(*store, read(fixtures / "freeplay.json"), "FreeplayActivity", "2026-09-23T13:00:00Z");
        const auto before = confirmed(store->snapshot("progress-adoption-before"));
        const auto shown = desktop::presentProgress(before, "2026-09-24T00:00:00Z", installed);
        const auto& domain = field(shown.projection, "domain_coverage");
        check(field(domain, "status") == V("mapped_recorded_activity")
            && field(domain, "mapped_attempts") == V::fromInteger(8)
            && field(domain, "separate_freeplay") == V::fromInteger(1),
            "seven exact installed case Attempts, including Rung05 D/U, map; Freeplay stays separate");
        check(field(domain, "profile_id") == field(before.data, "profile_id")
            && field(domain, "snapshot_sha256") == field(before.data, "snapshot_sha256")
            && field(domain, "evidence_sha256") == field(before.data, "evidence_sha256"),
            "domain coverage is bound to the confirmed Store snapshot");
        check(field(domain, "domains").array().size() == 1
            && field(field(domain, "domains").array()[0], "label") == V("Technique/fretboard")
            && field(field(domain, "domains").array()[0], "recorded_attempts") == V::fromInteger(8),
            "only reviewed Technique/fretboard label is visible");
        check(shown.text.find("Mapped Attempts: 8 | Freeplay kept separate: 1 | Unmapped Attempts: 0") != std::string::npos
            && shown.text.find("Technique/fretboard | recorded Attempts: 8 | active time: 32.000 s") != std::string::npos
            && shown.text.find("Weekly recorded activity") != std::string::npos
            && shown.text.find("Clean PB:") != std::string::npos
            && shown.text.find("Review due:") != std::string::npos
            && shown.text.find("Self-assessment:") != std::string::npos,
            "domain, weekly, PB, review and self-report presentation retains distinct meaning");
        const auto after = confirmed(store->snapshot("progress-adoption-after"));
        check(field(before.data, "authoritative") == field(after.data, "authoritative"),
            "Progress presentation changes no authoritative Store record");
        const auto missing = desktop::presentProgress(before, "2026-09-24T00:00:00Z");
        check(field(field(missing.projection, "domain_coverage"), "status") == V("mapping_unavailable")
            && missing.text.find("Domain coverage: not computed") != std::string::npos,
            "missing installed catalog retains history and refuses inferred mapping");
        const auto partial = lesson::Catalog::load(resources / "representative-controls");
        const auto changed = desktop::presentProgress(before, "2026-09-24T00:00:00Z", partial);
        check(field(field(changed.projection, "domain_coverage"), "status") == V("mapping_unavailable")
            && changed.text.find("Attempts: 8") != std::string::npos,
            "partial installed catalog retains history but cannot claim seven-case mapping");
        const auto withoutRung05 = lesson::Catalog::load(resources / "representative-controls",
            resources / "rung02-extension", resources / "rung03-extension",
            resources / "rung04-extension", resources / "level006-extension");
        const auto prior = desktop::presentProgress(before, "2026-09-24T00:00:00Z", withoutRung05);
        check(field(field(prior.projection, "domain_coverage"), "status") == V("mapping_unavailable")
            && prior.text.find("Attempts: 8") != std::string::npos,
            "missing current Rung05 admission retains all saved history without stale six-case claim");
        store.reset(); options.create = false;
        store = std::make_unique<storage::ProfileStore>(options);
        const auto reopened = desktop::presentProgress(confirmed(store->snapshot("progress-adoption-reopened")),
            "2026-09-24T00:00:00Z", installed);
        check(reopened.text == shown.text && reopened.details == shown.details,
            "same-profile reopen retains exact visible Progress facts");
        std::ofstream(scratch / "presentation.txt") << shown.text;
        std::ofstream(scratch / "projection.json") << shown.details;
        check(bindings.catalogs.size() == 27
            && bindings.catalogs[25].entries[0].binding.variant == "fg:variant:007474"
            && bindings.catalogs[25].entries[1].binding.variant == "fg:variant:007475",
            "exact Level25 D/U domain bindings follow all prior installed cases");
        save(*store, attempt(fixture, bindings.catalogs[25].entries[0].binding, *installed),
             "Attempt", "2026-09-23T16:00:00Z");
        save(*store, attempt(fixture, bindings.catalogs[25].entries[1].binding, *installed),
             "Attempt", "2026-09-23T17:00:00Z");
        const auto level25Shown = desktop::presentProgress(
            confirmed(store->snapshot("level25-progress-adoption")), "2026-09-24T00:00:00Z", installed);
        const auto& level25Coverage = field(level25Shown.projection, "domain_coverage");
        check(field(level25Coverage, "mapped_attempts") == V::fromInteger(10)
            && field(level25Coverage, "separate_freeplay") == V::fromInteger(1)
            && field(level25Coverage, "unmapped").array().empty()
            && field(level25Coverage, "domains").array().size() == 1
            && field(field(level25Coverage, "domains").array()[0], "label") == V("Technique/fretboard")
            && level25Shown.text.find("Mapped Attempts: 10 | Freeplay kept separate: 1 | Unmapped Attempts: 0") != std::string::npos,
            "Level25 D/U adds recorded Technique/fretboard activity without other domain credit");
        check(bindings.catalogs.size() == 27
            && bindings.catalogs[26].entries[0].binding.variant == "fg:variant:007476"
            && bindings.catalogs[26].entries[1].binding.variant == "fg:variant:007477",
            "exact Level26 D/U domain bindings follow all prior installed cases");
        save(*store, attempt(fixture, bindings.catalogs[26].entries[0].binding, *installed),
             "Attempt", "2026-09-23T18:00:00Z");
        save(*store, attempt(fixture, bindings.catalogs[26].entries[1].binding, *installed),
             "Attempt", "2026-09-23T19:00:00Z");
        const auto level26Shown = desktop::presentProgress(
            confirmed(store->snapshot("level26-progress-adoption")), "2026-09-24T00:00:00Z", installed);
        const auto& level26Coverage = field(level26Shown.projection, "domain_coverage");
        check(field(level26Coverage, "mapped_attempts") == V::fromInteger(12)
            && field(level26Coverage, "separate_freeplay") == V::fromInteger(1)
            && field(level26Coverage, "unmapped").array().empty()
            && field(level26Coverage, "domains").array().size() == 1
            && field(field(level26Coverage, "domains").array()[0], "label") == V("Technique/fretboard")
            && level26Shown.text.find("Mapped Attempts: 12 | Freeplay kept separate: 1 | Unmapped Attempts: 0") != std::string::npos,
            "Level26 D/U adds recorded Technique/fretboard activity without other domain credit");
        std::cout << "PASS " << checks << " visible Progress adoption checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n';
        return 1;
    }
}
