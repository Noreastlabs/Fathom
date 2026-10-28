#include "tasks/InstalledOrderedContactTaskRegistry.hpp"
#include "content/Canonical.hpp"
#include "GeneratedOrderedContactPackageBinding.hpp"
#include <fstream>
#include <set>
#include <sstream>

namespace fathom::tasks::ordered_contacts {
namespace {
using J = json::Value;
namespace fs = std::filesystem;
void need(bool good, const char* message) { if (!good) throw std::runtime_error(message); }
const J& at(const J& obj, const char* name) {
    need(obj.isObject() && obj.find(name), "Ordered contact package field required"); return *obj.find(name);
}
std::string text(const J& obj, const char* name) {
    const auto& v = at(obj, name); need(v.isString(), "Ordered contact package string required"); return v.string();
}
std::int64_t integer(const J& v) {
    std::int64_t n = 0; need(v.integer(n) && n >= 0, "Ordered contact package unsigned integer required"); return n;
}
void shape(const J& obj, std::initializer_list<const char*> fields) {
    need(obj.isObject() && obj.object().size() == fields.size(), "Ordered contact package exact schema required");
    for (const auto* field : fields) (void)at(obj, field);
}
fs::path realDirectory(const fs::path& input) {
    const auto path = fs::absolute(input).lexically_normal();
    need(fs::is_directory(path) && !fs::is_symlink(fs::symlink_status(path)) && fs::canonical(path) == path,
         "Ordered contact package root must be an exact real directory");
    return path;
}
fs::path safeFile(const fs::path& root, const std::string& relative) {
    const fs::path path(relative);
    need(!relative.empty() && !path.is_absolute() && path.generic_string() == relative, "Ordered contact relative file required");
    fs::path cursor = root;
    for (const auto& component : path) {
        need(component != "." && component != ".." && !component.empty(), "Ordered contact unsafe path component");
        cursor /= component;
        need(!fs::is_symlink(fs::symlink_status(cursor)), "Ordered contact source/package symlink refused");
    }
    need(fs::is_regular_file(cursor), "Ordered contact regular file required"); return cursor;
}
std::string read(const fs::path& root, const std::string& path, std::size_t limit) {
    return content::readBounded(safeFile(root, path), limit);
}
void pin(const J& p, const std::string& raw) {
    shape(p, {"path", "bytes", "sha256"});
    need(static_cast<std::size_t>(integer(at(p, "bytes"))) == raw.size() && text(p, "sha256") == content::sha256(raw),
         "Ordered contact file bytes/hash differ");
}
J rational(Rational q) { return J::Array{J::fromInteger(q.numerator()), J::fromInteger(q.denominator())}; }
}

InstalledOrderedContactTaskRegistry InstalledOrderedContactTaskRegistry::load(const fs::path& input, const fs::path& assetsInput) {
    InstalledOrderedContactTaskRegistry result;
    try {
        const auto directory = realDirectory(input), assets = realDirectory(assetsInput);
        const auto manifestBytes = read(directory, "manifest.json", 65536);
        need(content::sha256(manifestBytes) == package_binding::manifestSha, "Ordered contact installed manifest version differs");
        const auto manifest = json::parse(manifestBytes);
        shape(manifest, {"schema", "family", "scope", "rows", "native_contexts", "source_policy_groups", "runtime_candidate",
            "runtime_admitted", "practice_admitted", "official_accepted", "grants_credit", "fixed_bpm", "source_acoustic_gates",
            "package_files", "definitions", "contexts", "source_assets", "version_bindings", "resource_layout"});
        need(text(manifest, "schema") == "fathom.ordered-contact-manual-package.1" && text(manifest, "family") == "ordered-contact"
            && text(manifest, "scope") == "manual-guidance-candidate" && integer(at(manifest, "rows")) == 1401
            && integer(at(manifest, "native_contexts")) == 11 && integer(at(manifest, "source_policy_groups")) == 10,
            "Ordered contact package schema/scope/denominator differs");
        need(at(manifest, "runtime_candidate") == J(true) && at(manifest, "runtime_admitted") == J(false)
            && at(manifest, "practice_admitted") == J(false) && at(manifest, "official_accepted") == J(false)
            && at(manifest, "grants_credit") == J(false) && at(manifest, "fixed_bpm").null()
            && at(manifest, "source_acoustic_gates").null(), "Ordered contact manual/noncredit boundary differs");
        need(at(manifest, "version_bindings") == json::parse(package_binding::versionsJson), "Ordered contact native/generated/code/source versions differ");
        need(text(at(manifest, "version_bindings"), "native_row_closure_sha256") == closureSha256()
            && text(at(manifest, "version_bindings"), "manual_policy_closure_sha256") == manual::policyClosureSha256()
            && text(at(manifest, "version_bindings"), "cohort_sha256") == cohortSha256(), "Ordered contact compiled source closure differs");
        const auto& definitionsPin = at(manifest, "definitions"); const auto& contextsPin = at(manifest, "contexts");
        need(text(definitionsPin, "path") == "definitions.jsonl" && text(contextsPin, "path") == "contexts.json",
             "Ordered contact fixed package paths differ");
        const auto bulk = read(directory, "definitions.jsonl", 2 * 1024 * 1024);
        const auto contextsBytes = read(directory, "contexts.json", 256 * 1024);
        pin(definitionsPin, bulk); pin(contextsPin, contextsBytes);
        const auto contexts = json::parse(contextsBytes);
        shape(contexts, {"schema", "native_contexts", "source_policies", "source_packets"});
        need(text(contexts, "schema") == "fathom.ordered-contact-shared-contexts.1"
            && at(contexts, "native_contexts").isArray() && at(contexts, "native_contexts").array().size() == 11
            && at(contexts, "source_policies").isArray() && at(contexts, "source_policies").array().size() == 10
            && at(contexts, "source_packets").isArray() && at(contexts, "source_packets").array().size() == 10,
             "Ordered contact shared context schema differs");
        need(content::sha256(json::stringify(at(contexts, "source_policies"))) == manual::policyClosureSha256(),
             "Ordered contact complete shared policies differ from compiled policies");
        std::map<std::string, std::size_t> contextIndices, packetIndices;
        for (std::size_t i = 0; i < 11; ++i)
            need(contextIndices.emplace(content::sha256(json::stringify(at(contexts, "native_contexts").array()[i])), i).second,
                 "Ordered contact duplicate native context");
        for (std::size_t i = 0; i < 10; ++i) {
            const auto& packet = at(contexts, "source_packets").array()[i]; shape(packet, {"path", "bytes", "sha256"});
            need(packetIndices.emplace(text(packet, "path"), i).second, "Ordered contact duplicate packet provenance");
            const auto& item = at(contexts, "source_policies").array()[i];
            const auto& p = manual::policy(static_cast<int>(i) + 2);
            need(text(at(at(item, "policy"), "context_ref"), "sha256") == p.contextSha256,
                 "Ordered contact saved source context differs");
        }
        const auto& sourceAssets = at(manifest, "source_assets");
        need(sourceAssets.isArray() && sourceAssets.array().size() == 20, "Ordered contact twenty original source assets required");
        std::map<std::string, J> expectedAssets;
        for (const auto& item : at(contexts, "source_policies").array()) {
            const auto& originals = at(at(item, "source_context"), "originals");
            for (const auto* type : {"txt", "pdf"}) {
                const auto& asset = at(originals, type); shape(asset, {"path", "bytes", "sha256"});
                need(expectedAssets.emplace(text(asset, "path"), asset).second, "Ordered contact duplicate original asset");
            }
        }
        std::set<std::string> seenAssets;
        for (const auto& asset : sourceAssets.array()) {
            const auto path = text(asset, "path");
            need(expectedAssets.count(path) && expectedAssets.at(path) == asset && seenAssets.insert(path).second,
                 "Ordered contact original/source-book binding differs");
            const auto bytes = read(assets, path, 256 * 1024); ++result.sourceFilesHashed_;
            pin(asset, bytes);
        }
        std::map<std::string, std::string> identities, keysByIdentity;
        std::istringstream lines(bulk); std::string line; std::size_t index = 0, offset = 0;
        while (std::getline(lines, line)) {
            need(!line.empty() && index < keys().size(), "Ordered contact bulk row count differs");
            const auto row = json::parse(line);
            shape(row, {"source_key", "source_identity", "record_canonical_sha256", "source_packet", "packet_line", "level",
                "native_contact_offset", "contact_count", "metric_end_q", "native_context", "source_policy", "contract_sha256"});
            const auto& d = definition(keys()[index]); const auto meta = json::parse(d.retainedMetadataJson());
            const auto contextSha = text(meta, "shared_context_sha256");
            need(contextIndices.count(contextSha) && packetIndices.count(d.packetPath()), "Ordered contact row provenance/context join differs");
            const auto contextIndex = contextIndices.at(contextSha), packetIndex = packetIndices.at(d.packetPath());
            need(at(contexts, "native_contexts").array()[contextIndex] == at(meta, "source_context")
                && text(at(contexts, "source_packets").array()[packetIndex], "sha256") == d.packetSha256(),
                 "Ordered contact native context/packet differs");
            J expected(J::Object{{"source_key", d.sourceKey()}, {"source_identity", d.sourceIdentity()},
                {"record_canonical_sha256", d.sourceRecordSha256()}, {"source_packet", J::fromInteger(static_cast<std::int64_t>(packetIndex))},
                {"packet_line", J::fromInteger(d.packetLine())}, {"level", J::fromInteger(d.level())},
                {"native_contact_offset", J::fromInteger(static_cast<std::int64_t>(offset))},
                {"contact_count", J::fromInteger(static_cast<std::int64_t>(d.contactCount()))}, {"metric_end_q", rational(d.metricEnd())},
                {"native_context", J::fromInteger(static_cast<std::int64_t>(contextIndex))}, {"source_policy", J::fromInteger(d.level() - 2)}});
            expected.object().emplace("contract_sha256", content::sha256(json::stringify(J::Object{
                {"row", expected}, {"context", at(at(manifest, "version_bindings"), "contract_context")}})));
            need(row == expected, "Ordered contact complete bulk row/native contract differs");
            need(identities.emplace(d.sourceKey(), d.sourceIdentity()).second && keysByIdentity.emplace(d.sourceIdentity(), d.sourceKey()).second,
                 "Ordered contact duplicate installed key/identity");
            offset += d.contactCount(); ++index;
        }
        need(index == 1401 && identities.size() == 1401 && keysByIdentity.size() == 1401 && offset == 59528,
             "Ordered contact complete family required before any query");
        std::set<std::string> actualFiles;
        for (const auto& entry : fs::directory_iterator(directory)) {
            need(!entry.is_symlink() && entry.is_regular_file(), "Ordered contact flat package special/extra directory refused");
            actualFiles.insert(entry.path().filename().generic_string());
        }
        need(actualFiles == std::set<std::string>{"manifest.json", "definitions.jsonl", "contexts.json"}
            && at(manifest, "package_files") == J(J::Array{J("manifest.json"), J("definitions.jsonl"), J("contexts.json")}),
             "Ordered contact package has missing or unexpected files");
        result.identities_ = std::move(identities); result.keysByIdentity_ = std::move(keysByIdentity); result.ready_ = true;
    } catch (const std::exception& error) {
        result.ready_ = false; result.identities_.clear(); result.keysByIdentity_.clear(); result.error_ = error.what();
    }
    return result;
}
bool InstalledOrderedContactTaskRegistry::containsSourceKey(const std::string& key) const noexcept {
    return ready_ && identities_.count(key) == 1;
}
bool InstalledOrderedContactTaskRegistry::containsSourceIdentity(const std::string& identity) const noexcept {
    return ready_ && keysByIdentity_.count(identity) == 1;
}
std::optional<Definition> InstalledOrderedContactTaskRegistry::definitionForSourceKey(const std::string& key) const {
    if (!containsSourceKey(key)) return std::nullopt;
    return definition(key);
}
std::optional<Definition> InstalledOrderedContactTaskRegistry::definitionForSourceIdentity(const std::string& identity) const {
    if (!containsSourceIdentity(identity)) return std::nullopt;
    return definition(keysByIdentity_.at(identity));
}
std::unique_ptr<manual::Task> InstalledOrderedContactTaskRegistry::taskForSourceKey(const std::string& key) const {
    if (!containsSourceKey(key)) return {};
    return std::make_unique<manual::Task>(definition(key));
}
} // namespace fathom::tasks::ordered_contacts
