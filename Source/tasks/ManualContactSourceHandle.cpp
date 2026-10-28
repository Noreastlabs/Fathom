#include "tasks/ManualContactSourceHandle.hpp"
#include <array>
#include <atomic>
#include <mutex>
#include <stdexcept>
#include <type_traits>

namespace fathom::tasks::manual_contacts {
namespace {
std::atomic<std::size_t> legacyBuilds{0};
void need(bool good,const char* reason) {if(!good)throw std::invalid_argument(reason);}
void startValid(Start start) {need(start==Start::Down||start==Start::Up,"MANUAL_SOURCE_EXPLICIT_START");}
std::string label(int lowToHigh) {
    static const std::array<const char*,6> labels{{"E","A","D","G","B","e"}};
    need(lowToHigh>=1&&lowToHigh<=6,"MANUAL_SOURCE_PRINTED_STRING");return labels[static_cast<std::size_t>(lowToHigh-1)];
}
bool slotEqual(const RelativeHandSlot& a,const RelativeHandSlot& b) {
    return a.onset==b.onset&&a.duration==b.duration;
}
bool contactEqual(const Contact& a,const Contact& b) {
    return a.ordinal==b.ordinal&&a.stringLowToHigh==b.stringLowToHigh&&a.fret==b.fret&&a.finger==b.finger
        &&a.stringLabel==b.stringLabel&&a.pick==b.pick&&a.midi==b.midi&&a.spelling==b.spelling
        &&slotEqual(a.selectedRelativeHandSlot,b.selectedRelativeHandSlot)&&!a.acousticSoundingSpan&&!b.acousticSoundingSpan
        &&a.sourceRef==b.sourceRef&&a.annotationsJson==b.annotationsJson&&a.attackAuthority==b.attackAuthority
        &&a.blockIndex==b.blockIndex&&a.gridColumn==b.gridColumn&&a.sourceLine==b.sourceLine&&a.sourceColumn1Based==b.sourceColumn1Based&&a.degree==b.degree;
}
}
struct SourceHandle::Cache final {
    std::mutex mutex;
    std::array<std::shared_ptr<const Projection>,2> projections;
};
SourceHandle::SourceHandle(ClosedDefinition d):definition_(std::move(d)),cache_(std::make_shared<Cache>()) {}
SourceHandle SourceHandle::ordered(const ordered_contacts::Definition& d) {return SourceHandle(d);}
SourceHandle SourceHandle::physical(const physical_contacts::Definition& d) {return SourceHandle(d);}
SourceHandle SourceHandle::piecewise(const piecewise_contacts::Definition& d) {return SourceHandle(d);}
SourceHandle SourceHandle::harmonic(const harmonic_contacts::Definition& d) {return SourceHandle(d);}
SourceHandle SourceHandle::sourceContact(const source_contacts::Definition& d) {return SourceHandle(d);}
SourceHandle SourceHandle::orderedKey(const std::string& key) {return ordered(ordered_contacts::definition(key));}
SourceHandle SourceHandle::physicalKey(const std::string& key) {return physical(physical_contacts::definition(key));}
SourceHandle SourceHandle::piecewiseKey(const std::string& key) {return piecewise(piecewise_contacts::definition(key));}
SourceHandle SourceHandle::harmonicKey(const std::string& key) {return harmonic(harmonic_contacts::definition(key));}
SourceHandle SourceHandle::sourceContactKey(const std::string& key) {return sourceContact(source_contacts::definition(key));}
Family SourceHandle::family() const noexcept {
    if(std::holds_alternative<ordered_contacts::Definition>(definition_))return Family::OrderedContact;
    if(std::holds_alternative<harmonic_contacts::Definition>(definition_))return Family::HarmonicContact;
    if(std::holds_alternative<source_contacts::Definition>(definition_))return Family::SourceContact;
    return std::holds_alternative<physical_contacts::Definition>(definition_)?Family::PhysicalContact:Family::PiecewiseContact;
}
const char* SourceHandle::sourceKey() const {return std::visit([](const auto& d){return d.sourceKey();},definition_);}
const char* SourceHandle::sourceIdentity() const {return std::visit([](const auto& d){return d.sourceIdentity();},definition_);}
const char* SourceHandle::sourceRecordSha256() const {return std::visit([](const auto& d){return d.sourceRecordSha256();},definition_);}
const char* SourceHandle::packetPath() const {return std::visit([](const auto& d){return d.packetPath();},definition_);}
const char* SourceHandle::packetSha256() const {return std::visit([](const auto& d){return d.packetSha256();},definition_);}
int SourceHandle::packetLine() const {return std::visit([](const auto& d){return d.packetLine();},definition_);}
int SourceHandle::level() const {return std::visit([](const auto& d){return d.level();},definition_);}
std::size_t SourceHandle::contactCount() const {return std::visit([](const auto& d){return d.contactCount();},definition_);}
Rational SourceHandle::selectedMetricEnd() const {
    return std::visit([](const auto& d){
        if constexpr(std::is_same_v<std::decay_t<decltype(d)>,ordered_contacts::Definition>)return d.metricEnd();
        else if constexpr(std::is_same_v<std::decay_t<decltype(d)>,harmonic_contacts::Definition>||std::is_same_v<std::decay_t<decltype(d)>,source_contacts::Definition>){const auto metric=d.selectedMetricEnd();need(metric.has_value(),"HARMONIC_SOURCE_METRIC_END_UNKNOWN");return *metric;}
        else return d.selectedMetricEnd();
    },definition_);
}
PolicyTag SourceHandle::policyTag() const {
    if(family()==Family::OrderedContact)return OrderedPolicyTag{level()};
    if(family()==Family::PhysicalContact)return PhysicalPolicyTag{level()};
    if(family()==Family::HarmonicContact)return HarmonicPolicyTag{level()};
    if(family()==Family::SourceContact)return SourceContactPolicyTag{level()};return PiecewisePolicyTag{level()};
}
std::string SourceHandle::trustedMetadataJson() const {
    return std::visit([](const auto& d){
        if constexpr(std::is_same_v<std::decay_t<decltype(d)>,ordered_contacts::Definition>)return d.retainedMetadataJson();
        else return d.trustedMetadataJson();
    },definition_);
}
std::shared_ptr<const Projection> SourceHandle::projection(Start start) const {
    need(family()!=Family::HarmonicContact&&family()!=Family::SourceContact,"HARMONIC_USE_OPTIONAL_SOURCE_ATOM_API");
    startValid(start);const auto index=start==Start::Down?0U:1U;
    std::lock_guard<std::mutex> lock(cache_->mutex);
    if(cache_->projections[index])return cache_->projections[index];
    auto result=std::make_shared<Projection>(Projection{family(),start,sourceKey(),sourceIdentity(),sourceRecordSha256(),level(),selectedMetricEnd(),{},false});
    result->contacts.reserve(contactCount());
    std::visit([&](const auto& d){
        if constexpr(std::is_same_v<std::decay_t<decltype(d)>,ordered_contacts::Definition>) {
            const auto nativeStart=start==Start::Down?ordered_contacts::Start::Down:ordered_contacts::Start::Up;
            const auto native=d.reference(nativeStart);
            // Exact legacy source parity was sealed independently. Conversion
            // retains each source field; this is not a second validate/admission.
            need(native.events.size()==d.contactCount(),"MANUAL_SOURCE_LEGACY_COUNT");
            ++legacyBuilds;result->legacyMusicModelUsed=true;
            for(std::size_t n=0;n<native.events.size();++n) {
                const auto& event=native.events[n];need(event.tones.size()==1&&event.span.onset&&event.span.duration,"MANUAL_SOURCE_LEGACY_SINGLE_CONTACT");
                const auto& tone=event.tones.front();need(tone.midi>=0&&tone.midi<=127&&!tone.soundingSpan,"MANUAL_SOURCE_LEGACY_FROZEN_PITCH_UNKNOWN_GATE");
                need(tone.finger.size()==1&&tone.finger[0]>='1'&&tone.finger[0]<='4',"MANUAL_SOURCE_LEGACY_PRINTED_FINGER");
                result->contacts.push_back({n+1,tone.string,tone.fret,tone.finger[0]-'0',label(tone.string),event.handDirection,tone.midi,tone.spelling,
                    {*event.span.onset,*event.span.duration},std::nullopt,event.sourceRef,{},"",std::nullopt,std::nullopt,std::nullopt,std::nullopt});
            }
        } else if constexpr(std::is_same_v<std::decay_t<decltype(d)>,physical_contacts::Definition>) {
            const auto nativeStart=start==Start::Down?physical_contacts::Start::Down:physical_contacts::Start::Up;
            for(std::size_t n=1;n<=d.contactCount();++n) {
                const auto c=d.contact(n,nativeStart);
                need(!c.midi&&!c.acousticSoundingSpan,"MANUAL_SOURCE_PHYSICAL_PITCH_GATE_MUST_REMAIN_UNKNOWN");
                result->contacts.push_back({c.ordinal,c.stringLowToHigh,c.fret,c.finger,c.stringLabel,c.pick,std::nullopt,{},
                    {c.selectedRelativeHandSlot.onset,c.selectedRelativeHandSlot.duration},std::nullopt,{},c.annotationsJson,c.attackAuthority,
                    c.blockIndex,c.gridColumn,c.sourceLine,c.sourceColumn1Based});
            }
        } else if constexpr(std::is_same_v<std::decay_t<decltype(d)>,piecewise_contacts::Definition>) {
            const auto nativeStart=start==Start::Down?piecewise_contacts::Start::Down:piecewise_contacts::Start::Up;
            for(std::size_t n=1;n<=d.contactCount();++n) {
                const auto cue=d.contact(n,nativeStart);const auto& c=cue.source;
                need(c.midi&&!c.acousticSoundingSpan,"MANUAL_SOURCE_PIECEWISE_RETAINED_PITCH_UNKNOWN_GATE");
                result->contacts.push_back({c.ordinal,c.stringLowToHigh,c.fret,c.finger,c.stringLabel,c.pick,c.midi,cue.spelling,
                    {c.selectedRelativeHandSlot.onset,c.selectedRelativeHandSlot.duration},std::nullopt,{},c.annotationsJson,c.attackAuthority,
                    c.blockIndex,c.gridColumn,c.sourceLine,c.sourceColumn1Based,cue.degree});
            }
        } else need(false,"HARMONIC_NO_LEGACY_PROJECTION_OR_MUSIC_MODEL");
    },definition_);
    cache_->projections[index]=result;return result;
}
Contact SourceHandle::contact(std::size_t ordinal,Start start) const {
    need(ordinal>0&&ordinal<=contactCount(),"MANUAL_SOURCE_EXACT_ORDINAL");return projection(start)->contacts[ordinal-1];
}
void SourceHandle::requireSourceParity(const Projection& actual,Start start) const {
    const auto expected=projection(start);
    need(actual.family==expected->family&&actual.start==expected->start&&actual.sourceKey==expected->sourceKey
        &&actual.sourceIdentity==expected->sourceIdentity&&actual.sourceRecordSha256==expected->sourceRecordSha256
        &&actual.level==expected->level&&actual.selectedMetricEnd==expected->selectedMetricEnd
        &&actual.legacyMusicModelUsed==expected->legacyMusicModelUsed&&actual.contacts.size()==expected->contacts.size(),
        "MANUAL_SOURCE_PROJECTION_IDENTITY_SCOPE");
    for(std::size_t n=0;n<actual.contacts.size();++n)
        need(contactEqual(actual.contacts[n],expected->contacts[n]),"MANUAL_SOURCE_PROJECTION_CONTACT_PARITY");
}
std::size_t legacyProjectionBuildCount() noexcept {return legacyBuilds.load();}
harmonic_contacts::Cue SourceHandle::harmonicContact(std::size_t ordinal,Start start)const{
    need(family()==Family::HarmonicContact,"HARMONIC_SOURCE_FAMILY_REQUIRED");
    need(start==Start::Down||start==Start::Up||start==Start::Unspecified,"HARMONIC_SOURCE_START_ENUM");
    const auto native=start==Start::Down?harmonic_contacts::PickVariant::Down:start==Start::Up?harmonic_contacts::PickVariant::Up:harmonic_contacts::PickVariant::Unspecified;
    return std::get<harmonic_contacts::Definition>(definition_).contact(ordinal,native);
}
std::optional<Rational> SourceHandle::harmonicMetricEnd()const{need(family()==Family::HarmonicContact,"HARMONIC_SOURCE_FAMILY_REQUIRED");return std::get<harmonic_contacts::Definition>(definition_).selectedMetricEnd();}
std::string SourceHandle::harmonicProgramJson()const{need(family()==Family::HarmonicContact,"HARMONIC_SOURCE_FAMILY_REQUIRED");return std::get<harmonic_contacts::Definition>(definition_).sourceProgramJson();}
std::string SourceHandle::harmonicContextJson()const{need(family()==Family::HarmonicContact,"HARMONIC_SOURCE_FAMILY_REQUIRED");return std::get<harmonic_contacts::Definition>(definition_).trustedContextJson();}
source_contacts::Cue SourceHandle::sourceAtomContact(std::size_t ordinal,Start start,std::size_t route)const{
    need(family()==Family::SourceContact,"SOURCE_ATOM_FAMILY_REQUIRED");
    need(start==Start::Down||start==Start::Up||start==Start::Unspecified,"SOURCE_ATOM_START_ENUM");
    const auto native=start==Start::Down?source_contacts::PickVariant::Down:start==Start::Up?source_contacts::PickVariant::Up:source_contacts::PickVariant::Unspecified;
    return std::get<source_contacts::Definition>(definition_).contact(ordinal,native,route);
}
std::string SourceHandle::phaseProgramJson(std::size_t route)const{
    if(family()==Family::HarmonicContact){need(route==0,"HARMONIC_EXACT_SINGLE_ROUTE");return harmonicProgramJson();}
    need(family()==Family::SourceContact,"SOURCE_PHASE_FAMILY_REQUIRED");return std::get<source_contacts::Definition>(definition_).sourceProgramJson(route);
}
std::string SourceHandle::phaseContextJson()const{if(family()==Family::HarmonicContact)return harmonicContextJson();need(family()==Family::SourceContact,"SOURCE_PHASE_FAMILY_REQUIRED");return std::get<source_contacts::Definition>(definition_).trustedContextJson();}
std::string SourceHandle::phaseAtomsJson(std::size_t route)const{if(family()==Family::HarmonicContact){need(route==0,"HARMONIC_EXACT_SINGLE_ROUTE");return std::get<harmonic_contacts::Definition>(definition_).sourceAtomsJson();}need(family()==Family::SourceContact,"SOURCE_PHASE_FAMILY_REQUIRED");return std::get<source_contacts::Definition>(definition_).sourceAtomsJson(route);}
std::optional<Rational> SourceHandle::phaseMetricEnd(std::size_t route)const{if(family()==Family::HarmonicContact){need(route==0,"HARMONIC_EXACT_SINGLE_ROUTE");return harmonicMetricEnd();}need(family()==Family::SourceContact,"SOURCE_PHASE_FAMILY_REQUIRED");return std::get<source_contacts::Definition>(definition_).selectedMetricEnd(route);}
std::size_t SourceHandle::sourceRouteCount()const{need(family()==Family::SourceContact,"SOURCE_PHASE_FAMILY_REQUIRED");return std::get<source_contacts::Definition>(definition_).routeCount();}
std::size_t SourceHandle::sourceRouteContactCount(std::size_t route)const{need(family()==Family::SourceContact,"SOURCE_PHASE_FAMILY_REQUIRED");return std::get<source_contacts::Definition>(definition_).contactCount(route);}
} // namespace fathom::tasks::manual_contacts
