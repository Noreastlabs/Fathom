#pragma once
#include "tasks/OrderedContactTask.hpp"
#include <type_traits>
namespace fathom::tasks::ordered_contacts::manual::contact_snapshot {
using J=json::Value;using O=J::Object;using A=J::Array;
inline J encode(const J& x){return x;}
inline J encode(const std::string& x){return x;}
inline J encode(bool x){return x;}
template<class T,std::enable_if_t<std::is_enum_v<T>||std::is_integral_v<T>,int> =0>J encode(T x){if constexpr(std::is_enum_v<T>)return std::to_string(static_cast<std::underlying_type_t<T>>(x));else return std::to_string(x);}
inline J encode(const Rational& x){return A{std::to_string(x.numerator()),std::to_string(x.denominator())};}
template<class T>J encode(const std::optional<T>&);
template<class T>J encode(const std::vector<T>&);
inline J encode(const std::vector<bool>&);
template<class T>J encode(const std::map<std::string,T>&);
inline J encode(const SessionReport&);inline J encode(const HistoryEntry&);inline J encode(const Policy&);inline J encode(const SourceLine&);inline J encode(const PassOption&);inline J encode(const SourceDutyOption&);inline J encode(const source_contacts::Atom&);inline J encode(const source_contacts::Cue&);inline J encode(const manual_contacts::Contact&);inline J encode(const manual_contacts::RelativeHandSlot&);inline J encode(const std::shared_ptr<const manual_contacts::Projection>&);
template<class T>J encode(const std::optional<T>& x){return x?encode(*x):J{};}
template<class T>J encode(const std::vector<T>& x){A out;out.reserve(x.size());for(const auto& e:x)out.push_back(encode(e));return out;}
inline J encode(const std::vector<bool>& x){A out;out.reserve(x.size());for(bool b:x)out.emplace_back(b);return out;}
template<class T>J encode(const std::map<std::string,T>& x){O out;for(const auto& p:x)out.emplace(p.first,encode(p.second));return out;}
inline J encode(const SessionReport& x){return O{{"priorPrintedPassesReported",encode(x.priorPrintedPassesReported)},{"fullPrintedSetClean",encode(x.fullPrintedSetClean)},{"bothRoutesClean",encode(x.bothRoutesClean)},{"bothStartsClean",encode(x.bothStartsClean)},{"bothModesClean",encode(x.bothModesClean)},{"separateDayLabels",encode(x.separateDayLabels)},{"nextSessionRhythm",encode(x.nextSessionRhythm)}};}
inline J encode(const HistoryEntry& x){return O{{"revision",encode(x.revision)},{"action",encode(x.action)},{"sourceKey",x.sourceKey},{"detail",x.detail},{"passIndex",encode(x.passIndex)},{"start",encode(x.start)},{"observation",encode(x.observation)},{"manualReportJson",x.manualReportJson}};}
inline J encode(const SourceLine& x){return O{{"line",encode(x.line)},{"text",x.text}};}
inline J encode(const PassOption& x){return O{{"pass",encode(x.pass)},{"rhythms",encode(x.rhythms)},{"sourceLines",encode(x.sourceLines)},{"needsReportedStableLandings",encode(x.needsReportedStableLandings)}};}
inline J encode(const SourceDutyOption& x){return O{{"duty",encode(x.duty)},{"label",x.label},{"sourceLines",encode(x.sourceLines)},{"needsRelease",encode(x.needsRelease)}};}
inline J encode(const Policy& x){
#define C(field) {#field,encode(x.field)}
 return O{C(level),C(contextPath),C(contextSha256),C(sourceTextPath),C(sourceTextSha256),C(sourceLines),C(passes),C(previousLevel),C(belowCleanMinimum),C(belowCleanMaximum),C(slowerOfTwoPreviousModes),C(oneModePerSession),C(downStartFirst),C(rotationAcrossSessions),C(restoreAfterStable),C(restoreAfterAdvancement),C(advancementNeedsTwoDays),C(advancementNeedsBothModes),C(advancementNeedsBothStarts),C(advancementNeedsBothRoutes),C(extensions),C(family),C(safeInstructionLines),C(sourceDuties),C(sourceTempoRule),C(approximateThreeQuarters),C(groupedBeforeDisplacement),C(minorGeometryRelease),C(upperGeometryRebuild),C(sourceGeometryObservation),C(sourceInstructionBlocks)};
#undef C
}
inline J encode(const source_contacts::Atom& x){
#define C(field) {#field,encode(x.field)}
 return O{C(sourceOrdinal),C(stringLabel),C(kind),C(spelling),C(attack),C(technique),C(annotationsJson),C(stringLowToHigh),C(physicalFret),C(soundingFret),C(referenceFret),C(midi),C(finger),C(picked),C(audible),C(onset),C(handSlotDuration),C(pick),C(sourceFactsJson)};
#undef C
}
inline J encode(const source_contacts::Cue& x){
#define C(field) {#field,encode(x.field)}
 return O{C(sourceKey),C(sourceIdentity),C(sourceRecordSha256),C(routeIndex),C(ordinal),C(atoms),C(simultaneous)};
#undef C
}
inline J encode(const manual_contacts::RelativeHandSlot& x){return O{{"onset",encode(x.onset)},{"duration",encode(x.duration)}};}
inline J encode(const manual_contacts::Contact& x){
#define C(field) {#field,encode(x.field)}
 return O{C(ordinal),C(stringLowToHigh),C(fret),C(finger),C(stringLabel),C(pick),C(midi),C(spelling),C(selectedRelativeHandSlot),C(acousticSoundingSpan),C(sourceRef),C(annotationsJson),C(attackAuthority),C(blockIndex),C(gridColumn),C(sourceLine),C(sourceColumn1Based),C(degree)};
#undef C
}
inline J encode(const std::shared_ptr<const manual_contacts::Projection>& p){if(!p)return nullptr;const auto& x=*p;
#define C(field) {#field,encode(x.field)}
 return O{C(family),C(start),C(sourceKey),C(sourceIdentity),C(sourceRecordSha256),C(level),C(selectedMetricEnd),C(contacts),C(legacyMusicModelUsed)};
#undef C
}
} // namespace fathom::tasks::ordered_contacts::manual::contact_snapshot
