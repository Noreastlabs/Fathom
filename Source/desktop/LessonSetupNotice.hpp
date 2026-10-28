#pragma once
#include "core/GuitarSetup.hpp"
#include "content/StrictJson.hpp"
#include <set>
#include <stdexcept>
namespace fathom::desktop {
struct LessonSetupNotice {std::string summary,details;bool warning{};};
inline json::Value declaredSetupValue(const guitar::Setup& setup){
 if(!guitar::validate(setup).empty())throw std::invalid_argument("Current declared guitar setup is invalid.");
 using V=json::Value;V::Array tuning;for(auto pitch:setup.openMidi)tuning.push_back(V::fromInteger(pitch));
 return V::Object{{"value_version",setup.valueVersion},{"open_midi",tuning},{"capo",V::fromInteger(setup.capo)},{"fret_count",V::fromInteger(setup.fretCount)},{"handedness",setup.handedness==guitar::Handedness::Left?"left":"right"},{"physical_tuning_verified",false}};
}
inline LessonSetupNotice lessonSetupNotice(const music::ValidatedModel& model,const std::optional<guitar::Setup>& current){
 LessonSetupNotice notice;const auto& authored=model.source().instrument;
 std::string required="Authored tuning (low to high): ";
 if(authored.openMidi.empty())required="Authored instrument requirements are unspecified.";
 else {for(auto pitch:authored.openMidi)required+=guitar::noteName(pitch)+" ";required+="| capo "+std::to_string(authored.capo)+".";}
 notice.details=required+"\nReference uses authored pitches and positions; no automatic transposition.\n";
 if(!current){notice.summary="Current guitar setup is unavailable. Read the authored requirements in Setup details.";notice.details+="No declared setup is available for comparison. No physical tuning is verified.";return notice;}
 declaredSetupValue(*current);const auto comparison=guitar::compare(model,*current);
 notice.details+="\nDeclared tuning (low to high): ";for(auto pitch:current->openMidi)notice.details+=guitar::noteName(pitch)+" ";
 notice.details+="| capo "+std::to_string(current->capo)+" | physical frets "+std::to_string(current->fretCount)+" | "+(current->handedness==guitar::Handedness::Left?"left":"right")+" handed.\nDeclaration applies to the next Start. Saved and pending results retain their own snapshot. No physical tuning is verified.\n";
 if(comparison.requirementStatus==guitar::RequirementStatus::Unspecified){notice.summary="Authored setup unspecified; no position compatibility is inferred. Read Setup details.";notice.details+="\nThe source supplies no instrument requirement. Positioned compatibility was not assessed.";return notice;}
 notice.warning=!comparison.warnings.empty();
 if(!notice.warning)notice.summary=required+" Declared tuning/capo match; no physical tuning is verified.";
 else {std::set<std::string> codes;for(const auto& w:comparison.warnings)codes.insert(w.code);std::string kinds;for(const auto& code:codes){if(!kinds.empty())kinds+=", ";kinds+=code;}
  notice.summary=required+" Declared setup differs: continue authored reference or update Guitar setup. See Setup details.";
  notice.details+="\nWarnings ("+kinds+"):\n";for(const auto& w:comparison.warnings){if(!w.eventId.empty())notice.details+=w.eventId+": ";notice.details+=w.message+"\n";}}
 if(!comparison.positionsAssessed)notice.details+="\nPosition compatibility was not assessed for this selected case.";
 notice.details+="\nLesson access remains available. Source notes and frets are unchanged.";
 return notice;
}
}
