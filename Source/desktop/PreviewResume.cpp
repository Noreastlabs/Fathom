#include "desktop/PresentationPreferences.hpp"
#include "desktop/PreviewResume.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "metronome/MetronomePreferences.hpp"
#include "progression/ProgressionAdapter.hpp"
#include <cstdint>
#include <set>
#include <stdexcept>

namespace fathom::desktop {
namespace {
using V=json::Value;
const V& field(const V& value,const std::string& name){return value.object().at(name);}
void require(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
std::string blob(const V& value){
    const auto& hex=field(value,"blob_hex").string();
    require(hex.size()%2==0,"Malformed original Session plan bytes");
    auto nibble=[](char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;throw std::runtime_error("Malformed original Session plan hex");};
    std::string bytes;for(std::size_t i=0;i<hex.size();i+=2)bytes.push_back(static_cast<char>((nibble(hex[i])<<4)|nibble(hex[i+1])));return bytes;
}
}
void validatePreviewResumeSnapshot(const storage::Reply& reply,const PreviewResumeRequest& request){
    storage::validateUuid(request.profile);storage::validateUuid(request.session);
    storage::localDay("2026-09-01T00:00:00Z",request.timezone);
    const auto snapshot=progression::adaptSnapshot(reply);
    require(snapshot.profile==request.profile,"Resume refused: profile identity differs from the explicit original");
    const auto& authority=field(reply.data,"authoritative");bool found=false;
    for(const auto& row:field(authority,"session").array()){
        const auto& cells=row.array();require(cells.size()==5,"Malformed original Session row");
        if(cells[0]!=V(request.session))continue;
        require(!found,"Duplicate original Session");found=true;
        require(cells[2]==V(request.timezone),"Resume refused: timezone differs from the original Session");
        require(!cells[4].null(),"Resume preview requires an explicitly marked synthetic Session");
        const auto plan=storage::parseCanonical(blob(cells[4]));
        const auto* synthetic=plan.find("synthetic_fixture");
        if(synthetic){
            require(*synthetic==V(true),"Resume preview refuses a Session with an invalid synthetic-fixture marker");
        }else{
            const auto* version=plan.find("version");
            require(version&&*version==V("guided-session-plan.1"),"Resume preview refuses an unsupported Session plan");
            std::int64_t planned{};
            require(cells[3].integer(planned)&&planned>0&&planned<=14400,
                    "Resume preview refuses a Guided Session without a bounded planned duration");
            const auto* plannedSeconds=plan.find("planned_seconds");
            require(plannedSeconds&&plannedSeconds->integer(planned)&&planned>0&&planned<=14400,
                    "Resume preview refuses a Guided plan without a bounded planned duration");
            std::int64_t sessionPlanned{};
            require(cells[3].integer(sessionPlanned)&&sessionPlanned==planned,
                    "Resume preview refuses a Guided plan whose duration differs from its Session");
            const auto* durationMinutes=plan.find("duration_minutes");
            std::int64_t minutes{};
            require(durationMinutes&&durationMinutes->integer(minutes)&&minutes>=1&&minutes<=240&&minutes*60==planned,
                    "Resume preview refuses a Guided plan with an unsupported duration");
        }
    }
    require(found,"Resume refused: the specified original Session is missing");
    for(const auto& row:field(authority,"session_close").array())
        require(row.array().at(0)!=V(request.session),"Resume refused: original Session is closed; use a new explicit session workflow");
    std::set<std::string> finalized;
    for(const auto& row:field(authority,"finalized").array())finalized.insert(row.array().at(0).string());
    for(const auto& row:field(authority,"identity").array())
        require(finalized.count(row.array().at(0).string())==1,"Resume refused: unresolved original activity requires recovery before a new attempt; profile retained");
    require(field(authority,"pending").array().empty()&&field(authority,"checkpoint").array().empty(),
            "Resume refused: pending original outcome requires recovery; profile retained");
}
ResumedPreview openPreviewResume(const PreviewResumeRequest& request){
    require(request.directory.is_absolute(),"Resume requires an existing absolute private profile directory");
    require(std::filesystem::is_directory(std::filesystem::symlink_status(request.directory)),"Resume requires an existing nonsymlink profile directory");
    const auto path=request.directory/"profile.sqlite";
    require(std::filesystem::is_regular_file(std::filesystem::symlink_status(path)),"Resume requires an existing nonsymlink profile.sqlite; no replacement will be created");
    storage::validateUuid(request.profile);storage::validateUuid(request.session);
    storage::localDay("2026-09-01T00:00:00Z",request.timezone);
    storage::StoreOptions options;options.path=path;options.preferenceValidator=presentation::composedPreferenceValidator;
    ResumedPreview loaded;loaded.store=std::make_unique<storage::ProfileStore>(options);
    loaded.snapshot=loaded.store->snapshot("preview-resume/"+request.profile).get();
    validatePreviewResumeSnapshot(loaded.snapshot,request);return loaded;
}
}
