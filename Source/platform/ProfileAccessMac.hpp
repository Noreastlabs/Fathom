#pragma once
#include <filesystem>
#include <memory>
#include <string>

namespace fathom::storage {
// No default profile is created by resolving this location.
std::filesystem::path defaultProfilePath();
std::string systemIanaTimezone();
std::string localDay(const std::string& normalizedUtc, const std::string& ianaZone);
void validateUtc(const std::string& normalizedUtc);
bool utcBefore(const std::string& lhs,const std::string& rhs);
std::string newUuid();

// The native lock is directory-scoped (.profile.lock), so profiles sharing a
// directory cannot be open concurrently. Keep this lease alive through writer
// shutdown; releasing the UI view alone does not release the profile.
class ProfileLease final {
public:
    explicit ProfileLease(std::filesystem::path database, bool createDirectories);
    ~ProfileLease();
    ProfileLease(ProfileLease&&) noexcept;
    ProfileLease& operator=(ProfileLease&&) noexcept;
    ProfileLease(const ProfileLease&)=delete;
    ProfileLease& operator=(const ProfileLease&)=delete;
    const std::filesystem::path& path() const;
    void validateFiles(bool databaseRequired) const;
    // Readonly check that the native held lease still owns the named lock file.
    void validateLeaseIdentity() const;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
} // namespace fathom::storage
