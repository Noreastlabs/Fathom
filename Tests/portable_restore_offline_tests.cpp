#include "content/Canonical.hpp"
#include "desktop/PortableRestoreWorkflow.hpp"

#include <algorithm>
#include <arpa/inet.h>
#include <cerrno>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <netinet/in.h>
#include <stdexcept>
#include <string>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

namespace {
namespace fs = std::filesystem;
using fathom::desktop::PortableRestoreRequest;
using fathom::desktop::PortableRestoreWorkflow;
using fathom::storage::BackupPublicationRequest;
using fathom::storage::BackupSnapshotOptions;
using fathom::storage::ProfileStore;
using fathom::storage::Status;
using fathom::storage::StoreOptions;
using fathom::storage::Value;
using Object = Value::Object;
using Array = Value::Array;

int checks = 0;

void require(bool condition, const std::string& message) {
    if (!condition)
        throw std::runtime_error(message);
}

void check(const std::string& label, bool condition) {
    require(condition, label);
    ++checks;
    std::cout << "PASS " << label << '\n';
}

const Value& at(const Value& value, const std::string& key) {
    return value.object().at(key);
}

std::string readFile(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    require(static_cast<bool>(input), "Cannot read " + path.string());
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

std::string sha256(const std::string& bytes) {
    return fathom::content::sha256(bytes);
}

std::string sha256File(const fs::path& path) {
    return sha256(readFile(path));
}

void writeNew(const fs::path& path, const std::string& bytes) {
    require(!fs::exists(path), "Refuse to overwrite " + path.string());
    std::ofstream output(path, std::ios::binary);
    require(static_cast<bool>(output), "Cannot create " + path.string());
    output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    output.close();
    require(static_cast<bool>(output) && chmod(path.c_str(), 0600) == 0,
            "Cannot write/protect " + path.string());
}

void makePrivateDirectory(const fs::path& path) {
    require(fs::create_directory(path), "Directory already exists: " + path.string());
    require(chmod(path.c_str(), 0700) == 0, "Cannot protect directory: " + path.string());
}

void requirePrivateDirectory(const fs::path& path, const std::string& label) {
    struct stat info{};
    require(path.is_absolute() && path == path.lexically_normal() &&
                lstat(path.c_str(), &info) == 0 && S_ISDIR(info.st_mode) &&
                !S_ISLNK(info.st_mode) && info.st_uid == getuid() &&
                (info.st_mode & 077) == 0,
            label + " must be an absolute normalized owner-only directory");
}

void requireRegularFile(const fs::path& path, const std::string& label) {
    struct stat info{};
    require(path.is_absolute() && path == path.lexically_normal() &&
                lstat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode) &&
                !S_ISLNK(info.st_mode) && info.st_uid == getuid(),
            label + " must be an absolute owner-owned regular file");
}

void copyPrivate(const fs::path& source, const fs::path& destination,
                 const std::string& expectedSha, const std::string& label) {
    requireRegularFile(source, label + " fixture");
    require(sha256File(source) == expectedSha, label + " fixture hash changed");
    require(!fs::exists(destination), "Refuse existing copy: " + destination.string());
    require(fs::copy_file(source, destination), "Cannot copy " + label + " fixture");
    require(chmod(destination.c_str(), 0600) == 0, "Cannot protect copied fixture");
    check(label + " fixture hash verified before copy",
          sha256File(destination) == expectedSha);
}

Object sandboxDenialProbe() {
    int descriptor = ::socket(AF_INET, SOCK_STREAM, 0);
    if (descriptor < 0) {
        const int error = errno;
        check("network socket creation denied by process sandbox",
              error == EPERM || error == EACCES);
        return Object{{"operation", "socket(AF_INET, SOCK_STREAM)"},
                      {"denied", true}, {"errno", Value::fromInteger(error)},
                      {"expected_errno", "EPERM or EACCES"}, {"traffic_sent", false}};
    }

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_port = 0;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    const int bindResult = ::bind(descriptor, reinterpret_cast<const sockaddr*>(&address),
                                  static_cast<socklen_t>(sizeof(address)));
    const int error = bindResult == 0 ? 0 : errno;
    ::close(descriptor);
    check("network loopback bind denied by process sandbox",
          bindResult != 0 && (error == EPERM || error == EACCES));
    return Object{{"operation", "bind(AF_INET, 127.0.0.1:0)"},
                  {"denied", true}, {"errno", Value::fromInteger(error)},
                  {"expected_errno", "EPERM or EACCES"}, {"traffic_sent", false}};
}

Value snapshot(ProfileStore& store, const std::string& operation) {
    const auto reply = store.snapshot(operation).get();
    require(reply.status == Status::Confirmed,
            "Profile snapshot failed: " + reply.code + " " + reply.message);
    return reply.data;
}

std::vector<std::string> referenceIdentities(const Value& manifest) {
    std::vector<std::string> identities;
    const auto& references = at(at(manifest, "snapshot"), "content_references").array();
    for (const auto& reference : references)
        identities.push_back(fathom::storage::canonical(reference));
    std::sort(identities.begin(), identities.end());
    return identities;
}

Value availableMetadataFrom(const Value& manifest) {
    Array available;
    const auto& references = at(at(manifest, "snapshot"), "content_references").array();
    for (auto reference : references) {
        if (at(reference, "reference_kind") == Value("versioned_content")) {
            reference.object().erase("reference_kind");
            available.emplace_back(Object{
                {"reference", std::move(reference)},
                {"provenance", "Same-process disconnected-proof synthetic metadata; exact source identity only"}});
        }
    }
    require(!available.empty(), "Archive manifest has no exact versioned references for prepare");
    return available;
}

Value summary(const Object& fields) {
    return Value(fields);
}

void run(const fs::path& scratch, const fs::path& fixtureRoot) {
    requirePrivateDirectory(scratch, "Scratch root");
    require(scratch.string().find("/Build/parallel-01/10.5-offline-r01/") != std::string::npos,
            "Scratch root must remain under the P01 10.5 offline Build directory");
    require(fs::is_empty(scratch), "Scratch root must be new and empty");
    require(fixtureRoot.is_absolute() && fixtureRoot == fixtureRoot.lexically_normal(),
            "Fixture root must be an absolute normalized path");

    const auto networkProbe = sandboxDenialProbe();
    const auto richProfile = fixtureRoot / "rich/profile.sqlite";
    const auto emptyProfile = fixtureRoot / "empty/profile.sqlite";
    const auto richManifestPath = fixtureRoot / "rich/manifest.json";
    requireRegularFile(richManifestPath, "Rich fixture manifest");
    const auto richManifestBytes = readFile(richManifestPath);
    check("rich fixture manifest hash verified",
          sha256(richManifestBytes) ==
              "bc9a6f10222dc9434c23715c4dc808f9313f19d520e2ba99511b88e6364e507e");
    const auto fixtureManifest = fathom::storage::parseCanonical(richManifestBytes);
    const auto fixtureReferences = referenceIdentities(fixtureManifest);
    check("rich fixture manifest has three exact content references",
          fixtureReferences.size() == 3);

    makePrivateDirectory(scratch / "sender-live");
    makePrivateDirectory(scratch / "sender-stage-parent");
    copyPrivate(richProfile, scratch / "sender-live/profile.sqlite",
                "7344807f48176330849fd1efab15313ae8e6c10bbd1919e86ccc95d81b790ed4",
                "rich sender");
    makePrivateDirectory(scratch / "receiver-live");
    makePrivateDirectory(scratch / "receiver-stage-parent");
    copyPrivate(emptyProfile, scratch / "receiver-live/profile.sqlite",
                "489c04bc883d0e6cd2fa123c500ee82c4c7b6047d74edb3691c23024b07deb69",
                "empty receiver");

    StoreOptions senderOptions;
    senderOptions.path = scratch / "sender-live/profile.sqlite";
    ProfileStore sender(senderOptions);
    const auto before = snapshot(sender, "offline-proof-source-before");
    const auto& beforeAuthority = at(before, "authoritative");
    const auto& authorityObject = beforeAuthority.object();
    check("source has one committed Session",
          authorityObject.at("session").array().size() == 1);
    check("source preserves two finalized history records",
          authorityObject.at("finalized").array().size() == 2);
    check("source preserves two settings rows",
          authorityObject.at("preferences").array().size() == 2);
    const auto beforeAuthoritySha = sha256(fathom::storage::canonical(beforeAuthority));

    BackupSnapshotOptions backupOptions;
    backupOptions.destinationDirectory = scratch / "sender-stage-parent/stage";
    backupOptions.stopped = true;
    backupOptions.unresolvedWrites = false;
    backupOptions.includeArchiveManifest = true;
    backupOptions.includeArchiveContainer = true;
    BackupPublicationRequest publication;
    publication.destination = scratch / "portable-backup.zip";
    backupOptions.publication = publication;
    const auto backup = sender.prepareBackupSnapshot(
        "12121212-1212-4212-8212-121212121212", backupOptions).get();
    check("real source backup publishes while sandbox denies network",
          backup.status == Status::Confirmed && backup.code == "BACKUP_PUBLISHED");
    requireRegularFile(publication.destination, "Published archive");
    requireRegularFile(backupOptions.destinationDirectory / "manifest.json",
                       "Published source manifest");
    const auto sourceManifestBytes = readFile(backupOptions.destinationDirectory / "manifest.json");
    const auto sourceManifest = fathom::storage::parseCanonical(sourceManifestBytes);
    const auto sourceReferences = referenceIdentities(sourceManifest);
    check("published backup manifest preserves all three fixture references",
          sourceReferences == fixtureReferences);
    check("published archive hash matches verified receipt",
          sha256File(publication.destination) ==
              at(at(at(backup.data, "archive"), "file"), "sha256").string());
    check("backup receipt binds exact source authority boundary",
          at(at(backup.data, "authority"), "sha256") == at(before, "snapshot_sha256") &&
              at(backup.data, "profile_id") == at(before, "profile_id") &&
              at(backup.data, "committed_seq") == at(before, "committed_seq"));

    const auto afterBackup = snapshot(sender, "offline-proof-source-after-backup");
    check("backup leaves exact sender identity and authority unchanged",
          at(afterBackup, "profile_id") == at(before, "profile_id") &&
              at(afterBackup, "committed_seq") == at(before, "committed_seq") &&
              at(afterBackup, "authoritative") == beforeAuthority);

    const auto availablePath = scratch / "available-metadata.json";
    const auto available = availableMetadataFrom(sourceManifest);
    writeNew(availablePath, fathom::storage::canonical(available));
    check("available metadata contains exact versioned refs only",
          available.array().size() == 2);

    PortableRestoreRequest request;
    request.profile = scratch / "receiver-live/profile.sqlite";
    request.archive = publication.destination;
    request.stage = scratch / "receiver-stage-parent/stage";
    request.availableMetadata = availablePath;
    const auto prepared = PortableRestoreWorkflow::prepare(request);
    check("public restore prepare succeeds while sandbox denies network",
          prepared.preparation.status == Status::Confirmed &&
              prepared.preparation.code == "RESTORE_PREPARED");
    check("prepare produces an explicit confirmation and retained preview",
          !prepared.confirmationSha256.empty() && fs::is_regular_file(prepared.preview));
    const auto applied = PortableRestoreWorkflow::apply(prepared);
    check("public restore apply and normal reopen succeed",
          applied.application.status == Status::Confirmed &&
              applied.application.code == "RESTORE_APPLIED" &&
              applied.reopened.status == Status::Confirmed);
    check("restored receiver has exact sender profile identity and history/settings",
          at(applied.reopened.data, "profile_id") == at(before, "profile_id") &&
              at(applied.reopened.data, "committed_seq") == at(before, "committed_seq") &&
              at(applied.reopened.data, "authoritative") == beforeAuthority);
    check("restored receiver has exact source content-reference archive projection",
          sourceReferences == fixtureReferences && sourceReferences.size() == 3);

    const auto senderAfterRestore = snapshot(sender, "offline-proof-source-after-restore");
    check("restore leaves sender exact authority unchanged",
          at(senderAfterRestore, "profile_id") == at(before, "profile_id") &&
              at(senderAfterRestore, "committed_seq") == at(before, "committed_seq") &&
              at(senderAfterRestore, "authoritative") == beforeAuthority);

    const auto restoredAuthoritySha =
        sha256(fathom::storage::canonical(at(applied.reopened.data, "authoritative")));
    Object report{
        {"status", "PASS"}, {"checks", Value::fromInteger(checks)},
        {"network_denial_probe", networkProbe}, {"sandbox_policy", "deny network*"},
        {"fixture_rich_profile_sha256", "7344807f48176330849fd1efab15313ae8e6c10bbd1919e86ccc95d81b790ed4"},
        {"fixture_empty_profile_sha256", "489c04bc883d0e6cd2fa123c500ee82c4c7b6047d74edb3691c23024b07deb69"},
        {"source_profile_id", at(before, "profile_id")},
        {"source_committed_seq", at(before, "committed_seq")},
        {"source_authoritative_sha256_before", beforeAuthoritySha},
        {"source_authoritative_sha256_after_backup",
            sha256(fathom::storage::canonical(at(afterBackup, "authoritative")))},
        {"source_authoritative_sha256_after_restore",
            sha256(fathom::storage::canonical(at(senderAfterRestore, "authoritative")))},
        {"restored_authoritative_sha256", restoredAuthoritySha},
        {"source_authority_unchanged", at(afterBackup, "authoritative") == beforeAuthority &&
                                         at(senderAfterRestore, "authoritative") == beforeAuthority},
        {"restored_authority_exact", at(applied.reopened.data, "authoritative") == beforeAuthority},
        {"content_reference_count", Value::fromInteger(static_cast<std::int64_t>(sourceReferences.size()))},
        {"content_references_exact", sourceReferences == fixtureReferences},
        {"archive_sha256", sha256File(publication.destination)},
        {"archive_bytes", Value::fromInteger(static_cast<std::int64_t>(fs::file_size(publication.destination)))},
        {"backup_operation", backup.operation}, {"backup_code", backup.code},
        {"prepare_operation", prepared.preparation.operation},
        {"prepare_code", prepared.preparation.code},
        {"confirmation_sha256", prepared.confirmationSha256},
        {"apply_operation", applied.application.operation},
        {"apply_code", applied.application.code},
        {"reopened_profile_id", at(applied.reopened.data, "profile_id")},
        {"same_machine_disposable_roots", true},
        {"clean_mac_install_qualified", false}, {"human_acceptance", false}};
    writeNew(scratch / "offline-restore-summary.json",
             fathom::storage::canonical(summary(report)));
    std::cout << "PASS disconnected backup/restore reconciliation (" << checks << " checks)\n";
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "Usage: fathom_portable_restore_offline_tests <fresh-build-scratch-root> <r10-fixture-root>\n";
        return 2;
    }
    try {
        run(fs::absolute(argv[1]).lexically_normal(),
            fs::absolute(argv[2]).lexically_normal());
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL disconnected backup/restore proof: " << error.what() << '\n';
        return 1;
    }
}
