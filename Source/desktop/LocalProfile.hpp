#pragma once
#include "desktop/PresentationPreferences.hpp"

#include "metronome/MetronomePreferences.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "storage/ProfileStore.hpp"
#include "storage/ProfileNaming.hpp"
#include <ctime>
#include <stdexcept>

namespace fathom::desktop {

enum class LocalProfileIntent { CreateOrOpen, ExistingOnly, CreateOnly };

struct LocalProfileOpen {
    std::unique_ptr<storage::ProfileStore> store;
    std::filesystem::path path;
    std::string profileId, sessionId, timezone, displayName="Unnamed local profile";
    bool created{};
};

inline std::string localProfileUtcNow(){
    const auto now=std::time(nullptr);
    std::tm utc{};
    gmtime_r(&now,&utc);
    char value[32]{};
    std::strftime(value,sizeof(value),"%Y-%m-%dT%H:%M:%SZ",&utc);
    return value;
}

inline std::string localProfilePlanHex(){
    const auto bytes=storage::canonical(json::Value::Object{{"version","local-practice-session.1"}});
    constexpr char digits[]="0123456789abcdef";
    std::string hex;
    hex.reserve(bytes.size()*2);
    for(const unsigned char byte:bytes){hex.push_back(digits[byte>>4]);hex.push_back(digits[byte&15]);}
    return hex;
}

// The caller must invoke this only after an explicit user action. Existing state is
// opened in place; an unknown or damaged profile is never replaced.
inline LocalProfileOpen openLocalProfile(const std::filesystem::path& path,const std::string& newSessionZone,LocalProfileIntent intent=LocalProfileIntent::CreateOrOpen){
    if(!path.is_absolute()||!storage::profile_names::databaseName(path.filename().string()))
        throw std::runtime_error("A private absolute Fathom profile database path is required");
    std::error_code error;
    const auto kind=std::filesystem::symlink_status(path,error).type();
    if(error&&error!=std::errc::no_such_file_or_directory)
        throw std::runtime_error("Cannot inspect the local profile path: "+error.message());
    const bool exists=kind!=std::filesystem::file_type::not_found;
    if(exists&&kind!=std::filesystem::file_type::regular)
        throw std::runtime_error("Local profile path is not a regular file; original retained");
    if(intent==LocalProfileIntent::ExistingOnly&&!exists)throw std::runtime_error("No existing local profile was found. Use Create Profile to begin setup.");
    if(intent==LocalProfileIntent::CreateOnly&&exists)throw std::runtime_error("A local profile already exists. It is unchanged. Return to Welcome and choose Open existing profile.");
    storage::localDay(localProfileUtcNow(),newSessionZone);
    storage::StoreOptions options;
    options.path=path;
    options.create=!exists;
    if(options.create)options.createdUtc=localProfileUtcNow();
    options.preferenceValidator=presentation::composedPreferenceValidator;
    LocalProfileOpen result;
    result.path=path;
    result.created=!exists;
    result.store=std::make_unique<storage::ProfileStore>(options);
    const auto snapshot=result.store->snapshot(storage::newUuid()).get();
    if(snapshot.status!=storage::Status::Confirmed)
        throw std::runtime_error("Local profile could not be read; original retained: "+snapshot.message);
    result.profileId=snapshot.data.object().at("profile_id").string();
    const auto& sessions=snapshot.data.object().at("authoritative").object().at("session").array();
    const auto planHex=localProfilePlanHex();
    for(const auto& row:sessions){
        const auto& cells=row.array();
        if(cells.size()!=5||cells[4].null()||cells[4].object().at("blob_hex").string()!=planHex)continue;
        if(!result.sessionId.empty())throw std::runtime_error("Multiple local practice Sessions require recovery; original retained");
        result.sessionId=cells[0].string();
        result.timezone=cells[2].string();
    }
    if(result.sessionId.empty()){
        if(intent==LocalProfileIntent::ExistingOnly)throw std::runtime_error("Existing profile has no ordinary local Practice Session. Original retained unchanged; no new Session was created.");
        if(!sessions.empty())throw std::runtime_error("Existing profile has no local practice Session; original retained");
        const auto reply=result.store->createSession(storage::newUuid(),localProfileUtcNow(),newSessionZone,{},
            json::Value::Object{{"version","local-practice-session.1"}}).get();
        if(reply.status!=storage::Status::Confirmed)
            throw std::runtime_error("Local practice Session was not confirmed; profile retained: "+reply.message);
        result.sessionId=reply.owner;
        result.timezone=newSessionZone;
    }
    return result;
}

} // namespace fathom::desktop
