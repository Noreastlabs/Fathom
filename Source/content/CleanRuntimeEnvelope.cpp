#include "content/CleanRuntimeEnvelope.hpp"
#include "content/Canonical.hpp"
#include <algorithm>
#include <set>
#include <stdexcept>
#ifndef FATHOM_CLEAN_RUNTIME_MANIFEST_SHA
#error Clean runtime transport must have a compiled manifest pin
#endif
namespace fathom::content {
namespace {
// Parsing helpers reject unknown fields and ambiguous paths before any filesystem access.
using V = json::Value;
namespace fs = std::filesystem;
void need(bool value, const char *why) {
    if (!value)
        throw std::runtime_error(why);
}
const V &at(const V &value, const std::string &key) {
    need(value.isObject(), "Clean transport object required");
    const auto *found = value.find(key);
    need(found, "Clean transport field missing");
    return *found;
}
void shape(const V &value, std::initializer_list<const char *> names) {
    need(value.isObject(), "Clean transport object required");
    std::set<std::string> expected;
    for (const auto *n : names)
        expected.insert(n);
    std::set<std::string> actual;
    for (const auto &item : value.object())
        actual.insert(item.first);
    need(actual == expected, "Clean transport shape differs");
}
std::string text(const V &value) {
    need(value.isString(), "Clean transport string required");
    return value.string();
}
std::size_t size(const V &value) {
    std::int64_t n{};
    need(value.integer(n) && n >= 0 && n <= 512LL * 1024 * 1024, "Clean transport size invalid");
    return static_cast<std::size_t>(n);
}
void hash(const std::string &value) {
    need(value.size() == 64 &&
             std::all_of(value.begin(), value.end(),
                         [](char c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'); }),
         "Clean transport SHA256 invalid");
}
void relative(const std::string &value) {
    need(!value.empty() && value.find('\\') == std::string::npos &&
             value.find('\0') == std::string::npos,
         "Clean transport path invalid");
    fs::path path(value);
    need(!path.is_absolute() && !path.has_root_name(), "Clean transport path must be relative");
    for (const auto &part : path)
        need(part != "." && part != ".." && !part.empty(), "Clean transport traversal refused");
    need(path.generic_string() == value, "Clean transport path spelling differs");
}
void unlinked(const fs::path &path) {
    need(path.is_absolute(), "Clean runtime absolute path required");
    fs::path part;
    for (const auto &p : path) {
        need(p != "." && p != "..", "Clean runtime dot path refused");
        part /= p;
        need(!fs::is_symlink(fs::symlink_status(part)), "Clean runtime symlink refused");
    }
}
void descriptor(const V &value) {
    shape(value, {"bytes", "sha256"});
    (void)size(at(value, "bytes"));
    hash(text(at(value, "sha256")));
}
constexpr const char *manifestName = "clean-runtime-manifest.json";
constexpr const char *nibName = "RecentFilesMenuTemplate.nib";
constexpr const char *nibSha = "718eb4c5a3a5564dd832ae9a36cf649f3ef257ce896dd921693eeb6101bd008a";
} // namespace
CleanRuntimeEnvelope::CleanRuntimeEnvelope(fs::path root, fs::path package, V manifest,
                                           std::string sha, CancellationCheck canceled)
    : root_(std::move(root)), package_(std::move(package)),
      prefix_(package_.filename().generic_string() + "/"), transportSha_(std::move(sha)),
      manifest_(std::move(manifest)), canceled_(std::move(canceled)) {}
// Mint a scope only from the compiled transport pin. The old package manifest
// digest remains its logical admission identity; the transport digest is separate.
std::shared_ptr<const CleanRuntimeEnvelope>
CleanRuntimeEnvelope::open(const fs::path &package, const std::string &logicalSha,
                           const std::string &logicalName, const CancellationCheck &canceled) {
    checkLoadCanceled(canceled);
    unlinked(package);
    need(fs::is_directory(package), "Clean runtime package missing");
    relative(logicalName);
    hash(logicalSha);
    const auto actualPackage = fs::canonical(package), root = actualPackage.parent_path();
    unlinked(root);
    const auto path = root / manifestName;
    need(!fs::is_symlink(fs::symlink_status(path)), "Clean transport manifest symlink refused");
    const auto bytes = readBounded(path, 2 * 1024 * 1024, canceled);
    need(sha256(bytes) == FATHOM_CLEAN_RUNTIME_MANIFEST_SHA, "Clean runtime transport pin differs");
    auto manifest = json::parse(bytes);
    shape(manifest, {"schema", "retained_files", "archived_evidence", "semantic_projections"});
    need(text(at(manifest, "schema")) == "fathom-clean-runtime-transport.1",
         "Clean runtime transport version differs");
    need(at(manifest, "retained_files").isObject() &&
             at(manifest, "archived_evidence").isObject() &&
             at(manifest, "semantic_projections").isObject(),
         "Clean runtime inventories required");
    auto result = std::shared_ptr<CleanRuntimeEnvelope>(new CleanRuntimeEnvelope(
        root, actualPackage, std::move(manifest), sha256(bytes), canceled));
    const std::set<std::string> roles{
        "predecessor_validation",        "authority-attestation",
        "historical-agent-instructions", "engineering-contract-attestation",
        "validation-attestation",        "development-verifier-attestation"};
    const auto &retained = at(result->manifest_, "retained_files").object();
    const auto &archived = at(result->manifest_, "archived_evidence").object();
    need(!retained.empty() && retained.size() <= 10000 && archived.size() <= 10000,
         "Clean runtime inventory bounds differ");
    for (const auto &item : retained) {
        relative(item.first);
        descriptor(item.second);
        need(item.first != manifestName, "Clean manifest cannot self-authorize");
    }
    for (const auto &item : archived) {
        relative(item.first);
        shape(item.second, {"bytes", "sha256", "role"});
        (void)size(at(item.second, "bytes"));
        hash(text(at(item.second, "sha256")));
        need(roles.count(text(at(item.second, "role"))) == 1 && !retained.count(item.first),
             "Clean archive role/path differs");
    }
    for (const auto &item : at(result->manifest_, "semantic_projections").object()) {
        relative(item.first);
        shape(item.second, {"path", "bytes", "sha256", "original_sha256"});
        const auto target = text(at(item.second, "path"));
        relative(target);
        hash(text(at(item.second, "original_sha256")));
        hash(text(at(item.second, "sha256")));
        const auto old = archived.find(item.first);
        need(old != archived.end() && text(at(old->second, "role")) == "predecessor_validation" &&
                 at(old->second, "sha256") == at(item.second, "original_sha256"),
             "Semantic projection original role/identity differs");
        const auto current = retained.find(target);
        need(current != retained.end() &&
                 at(current->second, "bytes") == at(item.second, "bytes") &&
                 at(current->second, "sha256") == at(item.second, "sha256") &&
                 target.rfind("_semantic/", 0) == 0,
             "Semantic projection physical binding differs");
    }
    const auto key = result->localKey(logicalName);
    const auto logical = retained.find(key);
    need(logical != retained.end() && text(at(logical->second, "sha256")) == logicalSha,
         "Clean package logical identity differs");
    result->verifyState();
    // Validate every physical member in this package scope, plus all new DTOs.
    for (const auto &item : retained)
        if (item.first.rfind(result->prefix_, 0) == 0)
            (void)result->retainedBytes(item.first);
    std::set<std::string> checked;
    for (const auto &item : at(result->manifest_, "semantic_projections").object()) {
        const auto target = text(at(item.second, "path"));
        if (checked.insert(target).second)
            (void)result->retainedBytes(target);
    }
    return result;
}
std::string CleanRuntimeEnvelope::localKey(const std::string &path) const {
    relative(path);
    return prefix_ + path;
}
std::string CleanRuntimeEnvelope::archiveKey(const std::string &path) const {
    const auto key = localKey(path);
    const auto &archived = at(manifest_, "archived_evidence").object();
    if (archived.count(key))
        return key;
    // Preserve only the existing Results/primary logical alias, and only when
    // the exact archived record is present in the compiled-pinned manifest.
    if (path.rfind("Results/", 0) == 0 && path.rfind("Results/primary/", 0) != 0) {
        const auto alias = prefix_ + "Results/primary/" + path.substr(8);
        if (archived.count(alias))
            return alias;
    }
    return key;
}
bool CleanRuntimeEnvelope::hasArchivedEvidence(const std::string &path) const {
    return at(manifest_, "archived_evidence").object().count(archiveKey(path)) != 0;
}
// Attest only the original identity and physical absence. This API cannot
// supply archived bytes to an ordinary source or lesson reader.
void CleanRuntimeEnvelope::verifyArchivedEvidence(const std::string &path,
                                                  const std::string &oldSha,
                                                  std::optional<std::size_t> oldBytes) const {
    verifyTransportPin();
    checkLoadCanceled(canceled_);
    hash(oldSha);
    const auto key = archiveKey(path);
    const auto &archived = at(manifest_, "archived_evidence").object();
    const auto found = archived.find(key);
    need(found != archived.end() && text(at(found->second, "sha256")) == oldSha,
         "Archived evidence identity differs");
    if (oldBytes)
        need(size(at(found->second, "bytes")) == *oldBytes,
             "Archived evidence byte identity differs");
    auto ancestor = root_;
    for (const auto &part : fs::path(key)) {
        ancestor /= part;
        std::error_code error;
        const auto state = fs::symlink_status(ancestor, error);
        need(!error || error == std::make_error_code(std::errc::no_such_file_or_directory),
             "Archived path cannot be inspected");
        need(state.type() != fs::file_type::symlink, "Archived path ancestor symlink refused");
        if (state.type() == fs::file_type::not_found)
            break;
    }
    std::error_code ec;
    const auto state = fs::symlink_status(root_ / key, ec);
    need(!ec || ec == std::make_error_code(std::errc::no_such_file_or_directory),
         "Archived evidence path cannot be inspected");
    need(state.type() == fs::file_type::not_found,
         "Archived evidence body or symlink unexpectedly present");
}
fs::path CleanRuntimeEnvelope::safePhysical(const std::string &path) const {
    unlinked(root_);
    relative(path);
    auto file = root_;
    for (const auto &part : fs::path(path)) {
        file /= part;
        need(!fs::is_symlink(fs::symlink_status(file)), "Clean payload symlink refused");
    }
    need(fs::is_regular_file(file), "Clean payload missing");
    return file;
}
std::string CleanRuntimeEnvelope::retainedBytes(const std::string &key) const {
    verifyTransportPin();
    checkLoadCanceled(canceled_);
    const auto &files = at(manifest_, "retained_files").object();
    const auto found = files.find(key);
    need(found != files.end(), "Unlisted clean payload");
    const auto bytes = readBounded(safePhysical(key), size(at(found->second, "bytes")), canceled_);
    need(bytes.size() == size(at(found->second, "bytes")) &&
             sha256(bytes) == text(at(found->second, "sha256")),
         "Clean payload hash/bytes differ");
    return bytes;
}
void CleanRuntimeEnvelope::verifyPayload(const fs::path &resolved, const std::string &bytes) const {
    verifyTransportPin();
    checkLoadCanceled(canceled_);
    unlinked(resolved);
    const auto path = fs::canonical(resolved);
    const auto rel = path.lexically_relative(root_).generic_string();
    relative(rel);
    const auto &files = at(manifest_, "retained_files").object();
    const auto found = files.find(rel);
    need(found != files.end() && bytes.size() == size(at(found->second, "bytes")) &&
             sha256(bytes) == text(at(found->second, "sha256")),
         "Unbound or changed physical payload");
}
// Recheck the trust root on every consumed read, including cached catalog use.
void CleanRuntimeEnvelope::verifyTransportPin() const {
    checkLoadCanceled(canceled_);
    unlinked(root_);
    const auto file = root_ / manifestName;
    need(!fs::is_symlink(fs::symlink_status(file)), "Clean transport manifest symlink refused");
    const auto bytes = readBounded(file, 2 * 1024 * 1024, canceled_);
    need(sha256(bytes) == transportSha_ && transportSha_ == FATHOM_CLEAN_RUNTIME_MANIFEST_SHA,
         "Clean transport changed after opening");
}
void CleanRuntimeEnvelope::verifyState() const {
    verifyTransportPin();
    std::set<std::string> expected{manifestName};
    for (const auto &item : at(manifest_, "retained_files").object())
        expected.insert(item.first);
    const auto nib = root_ / nibName;
    if (fs::exists(nib)) {
        need(!fs::is_symlink(fs::symlink_status(nib)), "Generated nib symlink refused");
        const auto data = readBounded(nib, 2842, canceled_);
        need(data.size() == 2842 && sha256(data) == nibSha, "Generated nib identity differs");
        expected.insert(nibName);
    }
    std::set<std::string> actual;
    for (const auto &entry : fs::recursive_directory_iterator(root_)) {
        checkLoadCanceled(canceled_);
        need(!entry.is_symlink(), "Clean runtime symlink refused");
        if (entry.is_regular_file())
            actual.insert(entry.path().lexically_relative(root_).generic_string());
        else
            need(entry.is_directory(), "Clean runtime non-file entry refused");
    }
    need(actual == expected, "Clean runtime physical file set differs");
}
// The sole semantic exception is a typed predecessor projection. Its role,
// physical digest, exact fields and preserved record digests must all agree.
SemanticPredecessorProjection
CleanRuntimeEnvelope::readSemanticProjection(const std::string &path,
                                             const std::string &originalSha) const {
    verifyArchivedEvidence(path, originalSha);
    const auto key = archiveKey(path);
    need(text(at(at(manifest_, "archived_evidence").object().at(key), "role")) ==
             "predecessor_validation",
         "Only predecessor-validation projections are supported");
    const auto &projections = at(manifest_, "semantic_projections").object();
    const auto found = projections.find(key);
    need(found != projections.end() && text(at(found->second, "original_sha256")) == originalSha,
         "Semantic original binding differs");
    const auto value = json::parse(retainedBytes(text(at(found->second, "path"))));
    shape(value, {"validator_version", "valid_reference", "records"});
    need(text(at(value, "validator_version")) == "canonical-validator.1" &&
             at(value, "valid_reference").isBool() && at(value, "valid_reference").boolean() &&
             at(value, "records").isArray(),
         "Semantic predecessor validation scope differs");
    std::set<std::string> ids;
    for (const auto &row : at(value, "records").array()) {
        shape(row, {"id", "content_revision", "record_sha256", "preserved_record"});
        const auto id = text(at(row, "id"));
        need(ids.insert(id).second && at(row, "id") == at(at(row, "preserved_record"), "id") &&
                 at(row, "content_revision") == at(at(row, "preserved_record"), "content_revision"),
             "Semantic predecessor record identity differs");
        hash(text(at(row, "record_sha256")));
        need(sha256(json::stringify(at(row, "preserved_record"))) == text(at(row, "record_sha256")),
             "Semantic predecessor record digest differs");
    }
    return {text(at(value, "validator_version")), true, at(value, "records")};
}
} // namespace fathom::content
