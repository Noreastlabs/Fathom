#include "desktop/PortableRestoreWorkflow.hpp"

#include "content/Canonical.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "storage/ArchiveReader.hpp"

#include <CommonCrypto/CommonDigest.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <fcntl.h>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

namespace fathom::desktop {
namespace {
namespace fs = std::filesystem;
using Value = storage::Value;
using Object = Value::Object;

void require(bool condition, const std::string& message) {
    if (!condition)
        throw std::runtime_error(message);
}

void requireAbsolute(const fs::path& path, const std::string& label) {
    require(path.is_absolute() && path == path.lexically_normal(),
            label + " must be an absolute normalized path");
    struct stat info{};
    require(lstat(path.c_str(), &info) != 0 || !S_ISLNK(info.st_mode),
            label + " must not be a symlink");
}

void requireRegular(const fs::path& path, const std::string& label) {
    requireAbsolute(path, label);
    struct stat info{};
    require(lstat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode),
            label + " must be an existing regular file");
    require((info.st_mode & 077) == 0 && info.st_uid == getuid(),
            label + " must be private and user-owned");
}

void requireDirectory(const fs::path& path, const std::string& label) {
    requireAbsolute(path, label);
    struct stat info{};
    require(lstat(path.c_str(), &info) == 0 && S_ISDIR(info.st_mode),
            label + " must be an existing directory");
    require((info.st_mode & 077) == 0 && info.st_uid == getuid(),
            label + " must be private and user-owned");
}

void requireNewStage(const fs::path& path) {
    requireAbsolute(path, "Restore stage");
    struct stat info{};
    require(lstat(path.c_str(), &info) != 0,
            "Restore stage must not already exist");
    requireDirectory(path.parent_path(), "Restore stage parent");
}

std::string readFile(const fs::path& path, const std::string& label) {
    std::ifstream input(path, std::ios::binary);
    require(static_cast<bool>(input), "Cannot read " + label);
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

Value readCanonicalFile(const fs::path& path, const std::string& label) {
    const auto bytes = readFile(path, label);
    try {
        return storage::parseCanonical(bytes);
    } catch (const std::exception& error) {
        throw std::runtime_error(label + " is not canonical storage JSON: " + error.what());
    }
}

Value fileIdentity(const fs::path& path) {
    requireRegular(path, "Restore preview");
    struct stat info{};
    require(lstat(path.c_str(), &info) == 0, "Cannot inspect restore preview");
    return Object{{"device", std::to_string(info.st_dev)},
                  {"inode", std::to_string(info.st_ino)},
                  {"bytes", Value::fromInteger(info.st_size)},
                  {"sha256", content::sha256(readFile(path, "restore preview"))}};
}

void validateAvailable(const Value& available) {
    require(available.isArray(), "Available metadata must be an explicit array");
    // ProfileStore performs the authoritative schema/content-reference
    // validation. This boundary only prevents an ambiguous non-array input.
}

storage::StoreOptions optionsFor(const fs::path& profile) {
    storage::StoreOptions options;
    options.path = profile;
    return options;
}

void validateRequest(const PortableRestoreRequest& request, bool preparing) {
    requireRegular(request.profile, "Profile");
    requireRegular(request.archive, "Candidate archive");
    requireRegular(request.availableMetadata, "Available metadata");
    if (preparing)
        requireNewStage(request.stage);
    else
        requireDirectory(request.stage, "Restore preview parent");
}

class DisposableCandidate {
public:
    explicit DisposableCandidate(fs::path path) : path_(std::move(path)) {
        require(mkdir(path_.c_str(), 0700) == 0,
                "Cannot create private restore preflight directory");
        if (lstat(path_.c_str(), &created_) != 0 || !S_ISDIR(created_.st_mode)) {
            std::error_code ignored;
            fs::remove(path_, ignored);
            throw std::runtime_error("Cannot bind private restore preflight directory");
        }
    }
    ~DisposableCandidate() {
        if (retained_)
            return;
        struct stat info{};
        if (lstat(path_.c_str(), &info) == 0 && S_ISDIR(info.st_mode) &&
            info.st_dev == created_.st_dev && info.st_ino == created_.st_ino &&
            info.st_uid == getuid() && (info.st_mode & 077) == 0) {
            std::error_code ignored;
            fs::remove_all(path_, ignored);
        }
    }
    DisposableCandidate(const DisposableCandidate&) = delete;
    DisposableCandidate& operator=(const DisposableCandidate&) = delete;
    void retain() { retained_ = true; }

private:
    fs::path path_;
    struct stat created_{};
    bool retained_ = false;
};

struct Descriptor {
    int fd = -1;
    explicit Descriptor(int value) : fd(value) {
        require(fd >= 0, "Cannot open selected archive snapshot input or output");
    }
    ~Descriptor() { if (fd >= 0) close(fd); }
    Descriptor(const Descriptor&) = delete;
    Descriptor& operator=(const Descriptor&) = delete;
};

bool sameFile(const struct stat& a, const struct stat& b) {
    return a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_size == b.st_size &&
           a.st_mode == b.st_mode && a.st_uid == b.st_uid && a.st_nlink == b.st_nlink &&
           a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec &&
           a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
           a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec &&
           a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec;
}

std::string hashFile(int fd, off_t bytes) {
    CC_SHA256_CTX hash;
    require(CC_SHA256_Init(&hash) == 1, "Cannot start archive snapshot hash");
    std::vector<unsigned char> buffer(1048576);
    for (off_t at = 0; at < bytes;) {
        const auto wanted = static_cast<std::size_t>(std::min<off_t>(bytes - at, buffer.size()));
        auto count = pread(fd, buffer.data(), wanted, at);
        if (count < 0 && errno == EINTR) continue;
        require(count > 0 && CC_SHA256_Update(&hash, buffer.data(),
                static_cast<CC_LONG>(count)) == 1, "Cannot hash selected archive");
        at += count;
    }
    std::array<unsigned char, CC_SHA256_DIGEST_LENGTH> digest{};
    require(CC_SHA256_Final(digest.data(), &hash) == 1, "Cannot finish archive snapshot hash");
    const char* digits = "0123456789abcdef";
    std::string result;
    for (auto byte : digest) { result += digits[byte >> 4]; result += digits[byte & 15]; }
    return result;
}

Value copyValidatedArchive(const fs::path& source, const fs::path& destination,
                           const Value& originalIdentity) {
    const int sourceFd = open(source.c_str(), O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    require(sourceFd >= 0,
            "Restore preparation did not complete: ARCHIVE_CHANGED Selected archive unavailable before snapshot copy");
    Descriptor input(sourceFd);
    struct stat initial{}, named{};
    require(fstat(input.fd, &initial) == 0 && lstat(source.c_str(), &named) == 0 &&
            S_ISREG(initial.st_mode) && sameFile(initial, named) &&
            originalIdentity.object().at("device") == Value(std::to_string(initial.st_dev)) &&
            originalIdentity.object().at("inode") == Value(std::to_string(initial.st_ino)) &&
            originalIdentity.object().at("bytes") == Value::fromInteger(initial.st_size),
            "Restore preparation did not complete: ARCHIVE_CHANGED Selected archive changed before snapshot copy");
    Descriptor output(open(destination.c_str(), O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));
    std::vector<char> buffer(1048576);
    for (off_t at = 0; at < initial.st_size;) {
        const auto wanted = static_cast<std::size_t>(std::min<off_t>(initial.st_size - at, buffer.size()));
        auto count = pread(input.fd, buffer.data(), wanted, at);
        if (count < 0 && errno == EINTR) continue;
        require(count > 0, "Restore preparation did not complete: ARCHIVE_CHANGED Selected archive read failed");
        std::size_t written = 0;
        while (written < static_cast<std::size_t>(count)) {
            auto n = write(output.fd, buffer.data() + written, static_cast<std::size_t>(count) - written);
            if (n < 0 && errno == EINTR) continue;
            require(n > 0, "Cannot write private selected archive snapshot");
            written += static_cast<std::size_t>(n);
        }
        at += count;
        require(fstat(input.fd, &named) == 0 && sameFile(initial, named),
                "Restore preparation did not complete: ARCHIVE_CHANGED Selected archive changed during snapshot copy");
    }
    require(fchmod(output.fd, 0400) == 0 && fsync(output.fd) == 0,
            "Cannot sync and protect private selected archive snapshot");
    const auto sourceHash = hashFile(input.fd, initial.st_size);
    require(lstat(source.c_str(), &named) == 0 && sameFile(initial, named) &&
            fstat(input.fd, &named) == 0 && sameFile(initial, named) &&
            sourceHash == originalIdentity.object().at("sha256").string(),
            "Restore preparation did not complete: ARCHIVE_CHANGED Selected archive changed after preflight");
    struct stat copied{};
    require(fstat(output.fd, &copied) == 0 && copied.st_size == initial.st_size &&
            hashFile(output.fd, copied.st_size) == originalIdentity.object().at("sha256").string(),
            "Private selected archive snapshot differs from validated source");
    return Object{{"device", std::to_string(copied.st_dev)},
                  {"inode", std::to_string(copied.st_ino)},
                  {"bytes", Value::fromInteger(copied.st_size)},
                  {"sha256", originalIdentity.object().at("sha256")}};
}

Value preflightArchive(const PortableRestoreRequest& request, const fs::path& temporary) {
    storage::ArchiveReaderOptions options;
    options.archive = request.archive;
    options.candidateDirectory = temporary / "validated";
    try {
        return storage::previewProfileArchive(options);
    } catch (const storage::EnvelopeError& error) {
        throw std::runtime_error("Restore preparation did not complete: " +
                                 error.code + " " + error.what());
    }
}

PreparedPortableRestore preparedFromReply(const PortableRestoreRequest& request,
                                          storage::Reply reply,
                                          const std::string& profileId) {
    require(reply.status == storage::Status::Confirmed && reply.code == "RESTORE_PREPARED",
            "Restore preparation did not complete: " + reply.code + " " + reply.message);
    const auto& prepared = reply.data.object().at("restore_preparation");
    const auto& record = prepared.object().at("record");
    const auto& confirmation = record.object().at("confirmation_sha256");
    const auto& previewPath = prepared.object().at("path");
    require(previewPath.isString() && confirmation.isString(),
            "Restore preparation omitted exact preview identity or confirmation");
    PreparedPortableRestore result;
    result.request = request;
    result.preparation = std::move(reply);
    result.preview = previewPath.string();
    result.previewFile = prepared.object().at("file");
    result.availableReferences = request.availableMetadata.empty()
        ? Value::Array{}
        : readCanonicalFile(request.availableMetadata, "available metadata");
    result.confirmationSha256 = confirmation.string();
    result.profileId = profileId;
    return result;
}

} // namespace

PreparedPortableRestore PortableRestoreWorkflow::prepare(
    const PortableRestoreRequest& request, const std::function<void()>& afterPreflight) {
    validateRequest(request, true);
    const auto available = readCanonicalFile(request.availableMetadata, "available metadata");
    validateAvailable(available);

    const auto snapshotRoot = request.stage.parent_path() /
        (".restore-selected-" + storage::newUuid());
    DisposableCandidate snapshot(snapshotRoot);
    const auto validated = preflightArchive(request, snapshotRoot);
    const auto sourceIdentity = validated.object().at("archive");
    if (afterPreflight)
        afterPreflight();
    const auto selected = snapshotRoot / "selected.zip";
    const auto selectedIdentity = copyValidatedArchive(request.archive, selected, sourceIdentity);
    Value origin = Object{{"format", "Fathom.SealedArchiveSource"},
                          {"version", Value::fromInteger(1)},
                          {"source_archive_path", request.archive.string()},
                          {"source_archive_file", sourceIdentity},
                          {"snapshot_archive_path", selected.string()},
                          {"snapshot_archive_file", selectedIdentity},
                          {"copied_snapshot_semantics", true}};
    const auto originBytes = storage::canonical(origin);
    const auto originPath = snapshotRoot / "origin.json";
    Descriptor originOutput(open(originPath.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));
    for (std::size_t at = 0; at < originBytes.size();) {
        auto count = write(originOutput.fd, originBytes.data() + at, originBytes.size() - at);
        if (count < 0 && errno == EINTR) continue;
        require(count > 0, "Cannot retain selected archive origin record");
        at += static_cast<std::size_t>(count);
    }
    require(fchmod(originOutput.fd, 0400) == 0 && fsync(originOutput.fd) == 0,
            "Cannot sync and protect selected archive origin record");
    std::error_code cleanupError;
    fs::remove_all(snapshotRoot / "validated", cleanupError);
    require(!cleanupError, "Cannot clean validated archive extraction before opening profile");

    auto store = std::make_unique<storage::ProfileStore>(optionsFor(request.profile));
    const auto before = store->snapshot(storage::newUuid()).get();
    require(before.status == storage::Status::Confirmed,
            "Explicit profile snapshot could not be confirmed before restore preparation");
    const auto profileId = before.data.object().at("profile_id").string();

    storage::BackupSnapshotOptions backup;
    backup.destinationDirectory = request.stage;
    backup.stopped = true;
    backup.unresolvedWrites = false;
    storage::RestorePreparationRequest restore;
    restore.archive = selected;
    restore.availableReferences = available;
    auto reply = store->prepareRestore(storage::newUuid(), backup, restore).get();
    auto prepared = preparedFromReply(request, std::move(reply), profileId);
    prepared.request.archive = selected;
    snapshot.retain();
    return prepared;
}

PreparedPortableRestore PortableRestoreWorkflow::loadPrepared(const fs::path& profile,
                                                              const fs::path& preview,
                                                              const fs::path& availableMetadata,
                                                              std::string confirmationSha256) {
    PortableRestoreRequest request{profile, preview.parent_path() / "candidate.zip",
                                   preview.parent_path(), availableMetadata};
    validateRequest(request, false);
    require(preview.filename() == "restore-preview.json", "Preview must be restore-preview.json");
    require(!confirmationSha256.empty(), "Exact confirmation SHA256 is required");
    const auto available = readCanonicalFile(availableMetadata, "available metadata");
    validateAvailable(available);
    const auto record = readCanonicalFile(preview, "restore preview");
    require(record.isObject() && record.object().size() == 2,
            "Restore preview must be the exact prepared record");
    require(record.object().at("confirmation_sha256") == Value(confirmationSha256),
            "Restore apply did not complete: RESTORE_CONFIRMATION Supplied confirmation does not match the prepared preview");

    auto store = std::make_unique<storage::ProfileStore>(optionsFor(profile));
    const auto before = store->snapshot(storage::newUuid()).get();
    require(before.status == storage::Status::Confirmed,
            "Explicit profile snapshot could not be confirmed before restore apply");
    PreparedPortableRestore result;
    result.request = request;
    result.preparation = {storage::Status::Confirmed, "", before.owner, "RESTORE_PREPARED",
                          "Loaded explicit prepared preview", record};
    result.preview = preview;
    result.previewFile = fileIdentity(preview);
    result.availableReferences = available;
    result.confirmationSha256 = std::move(confirmationSha256);
    result.profileId = before.data.object().at("profile_id").string();
    return result;
}

AppliedPortableRestore PortableRestoreWorkflow::apply(const PreparedPortableRestore& prepared) {
    validateRequest(prepared.request, false);
    requireRegular(prepared.preview, "Restore preview");
    require(prepared.previewFile.isObject(), "Exact prepared preview file identity is required");
    validateAvailable(prepared.availableReferences);

    storage::Reply application;
    {
        auto store = std::make_unique<storage::ProfileStore>(optionsFor(prepared.request.profile));
        storage::RestoreApplyRequest applyRequest;
        applyRequest.preview = prepared.preview;
        applyRequest.previewFile = prepared.previewFile;
        applyRequest.confirmationSha256 = prepared.confirmationSha256;
        applyRequest.availableReferences = prepared.availableReferences;
        applyRequest.explicitConfirmation = true;
        applyRequest.stopped = true;
        applyRequest.unresolvedWrites = false;
        application = store->applyRestore(storage::newUuid(), std::move(applyRequest)).get();
    }

    storage::Reply reopened;
    if (application.status == storage::Status::Confirmed &&
        application.code == "RESTORE_APPLIED") {
        auto store = std::make_unique<storage::ProfileStore>(optionsFor(prepared.request.profile));
        reopened = store->snapshot(storage::newUuid()).get();
        require(reopened.status == storage::Status::Confirmed,
                "Applied profile did not normal-reopen: " + reopened.code);
        require(reopened.data.object().at("profile_id") ==
                    application.data.object().at("snapshot").object().at("profile_id"),
                "Normal reopen profile identity differs from applied restore");
    }
    return {std::move(application), std::move(reopened)};
}

} // namespace fathom::desktop
