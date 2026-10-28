#pragma once
#include "metronome/Metronome.hpp"
#include "content/StrictJson.hpp"

namespace fathom::metronome {
Settings decodeSettings(const json::Value&);
json::Value encodeSettings(const Settings&);
struct Preset { std::string id,name; Settings settings; };
struct Preferences { Settings lastUsed; std::vector<Preset> presets; };
Preferences decodePreferences(const json::Value&);
json::Value encodePreferences(const Preferences&);
// Existing Store semantic hook. Unknown data stays in storage but cannot apply.
bool preferenceValidator(const std::string& key,std::int64_t namespaceVersion,
                         const json::Value&) noexcept;
void putPreset(Preferences&,std::string storageOwnedUuid,std::string name,
               Settings,bool replaceExisting);
// No transport field and no Start side effect. Caller must enforce actual stopped
// and resolved ownership, and source constraints for lesson preferences.
Settings restoreLastUsed(const Preferences&,bool stoppedAndResolved);
Settings restorePreset(const Preferences&,const std::string& id,bool stoppedAndResolved);
}
