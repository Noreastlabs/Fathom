#include "tasks/ManualContactSourceHandle.hpp"
#include <algorithm>
#include <future>
#include <iostream>
#include <map>
#include <set>
#include <type_traits>

namespace {
namespace O=fathom::tasks::ordered_contacts;
namespace P=fathom::tasks::physical_contacts;
namespace S=fathom::tasks::manual_contacts;
std::size_t checks=0,refusals=0,physicalRows=0,legacyRows=0,physicalVariants=0,physicalContacts=0,legacyVariants=0,legacyContacts=0;
void check(bool good,const char* why) {++checks;if(!good)throw std::runtime_error(why);}
template<class F>void refuses(F&& f) {bool rejected=false;try{f();}catch(const std::invalid_argument&){rejected=true;}check(rejected,"EXPECTED_SOURCE_HANDLE_REFUSAL");++refusals;}
void tag(const S::SourceHandle& h) {
    if(h.family()==S::Family::OrderedContact)check(std::holds_alternative<S::OrderedPolicyTag>(h.policyTag())&&std::get<S::OrderedPolicyTag>(h.policyTag()).level==h.level(),"EXACT_SEPARATE_LEGACY_POLICY_TAG");
    else check(std::holds_alternative<S::PhysicalPolicyTag>(h.policyTag())&&std::get<S::PhysicalPolicyTag>(h.policyTag()).level==h.level(),"EXACT_SEPARATE_PHYSICAL_POLICY_TAG");
}
template<class D>void binding(const S::SourceHandle& h,const D& d) {
    check(std::string(h.sourceKey())==d.sourceKey()&&std::string(h.sourceIdentity())==d.sourceIdentity()
        &&std::string(h.sourceRecordSha256())==d.sourceRecordSha256()&&std::string(h.packetPath())==d.packetPath()
        &&std::string(h.packetSha256())==d.packetSha256()&&h.packetLine()==d.packetLine()
        &&h.level()==d.level()&&h.contactCount()==d.contactCount(),"EXACT_NEUTRAL_CLOSED_SOURCE_BINDING");tag(h);
}
void negatives(const S::SourceHandle& h) {
    const auto clean=h.projection(S::Start::Down);h.requireSourceParity(*clean,S::Start::Down);
    refuses([&]{(void)h.contact(0,S::Start::Down);});refuses([&]{(void)h.contact(h.contactCount()+1,S::Start::Down);});
    refuses([&]{(void)h.projection(static_cast<S::Start>(70));});
    auto bad=*clean;bad.sourceKey="other";refuses([&]{h.requireSourceParity(bad,S::Start::Down);});
    bad=*clean;bad.contacts.pop_back();refuses([&]{h.requireSourceParity(bad,S::Start::Down);});
    bad=*clean;bad.contacts[0].midi=bad.contacts[0].midi?*bad.contacts[0].midi+1:0;refuses([&]{h.requireSourceParity(bad,S::Start::Down);});
    bad=*clean;bad.contacts[0].acousticSoundingSpan=S::RelativeHandSlot{fathom::Rational(0),fathom::Rational(1,4)};refuses([&]{h.requireSourceParity(bad,S::Start::Down);});
    bad=*clean;++bad.contacts[0].finger;refuses([&]{h.requireSourceParity(bad,S::Start::Down);});
    bad=*clean;bad.contacts[0].pick="U";refuses([&]{h.requireSourceParity(bad,S::Start::Down);});
    bad=*clean;std::swap(bad.contacts[0],bad.contacts[1]);refuses([&]{h.requireSourceParity(bad,S::Start::Down);});
    bad=*clean;bad.contacts[0].selectedRelativeHandSlot.duration=fathom::Rational(9);refuses([&]{h.requireSourceParity(bad,S::Start::Down);});
    bad=*clean;bad.legacyMusicModelUsed=!bad.legacyMusicModelUsed;refuses([&]{h.requireSourceParity(bad,S::Start::Down);});
    h.requireSourceParity(*clean,S::Start::Down);
}
void physical() {
    check(S::legacyProjectionBuildCount()==0,"PHYSICAL_CAMPAIGN_STARTS_WITH_ZERO_LEGACY_MODELS");
    const auto& replacement=P::definition(P::keys().back());std::map<int,const P::Definition*> reps;
    for(const auto& key:P::keys()) {
        const auto& d=P::definition(key);auto caller=d;auto h=S::SourceHandle::physical(caller);
        caller=key==replacement.sourceKey()?P::definition(P::keys().front()):replacement;binding(h,d);binding(S::SourceHandle(h),d);
        check(h.selectedMetricEnd()==d.selectedMetricEnd()&&h.trustedMetadataJson()==d.trustedMetadataJson(),"EXACT_PHYSICAL_METADATA_ENDPOINT");
        for(const auto start:{S::Start::Down,S::Start::Up}) {
            const auto nativeStart=start==S::Start::Down?P::Start::Down:P::Start::Up;
            const auto p=h.projection(start);check(p==h.projection(start)&&!p->legacyMusicModelUsed&&p->contacts.size()==d.contactCount(),"PHYSICAL_IMMUTABLE_CACHE_NO_MODEL");h.requireSourceParity(*p,start);
            for(std::size_t n=1;n<=d.contactCount();++n) {
                const auto native=d.contact(n,nativeStart);const auto c=h.contact(n,start);
                check(c.ordinal==native.ordinal&&c.stringLowToHigh==native.stringLowToHigh&&c.fret==native.fret&&c.finger==native.finger
                    &&c.stringLabel==native.stringLabel&&c.pick==native.pick&&!c.midi&&c.spelling.empty()&&!c.acousticSoundingSpan,
                    "ALL_PHYSICAL_NEUTRAL_CONTACTS_OPTIONAL_UNKNOWN_PITCH_GATE");
                check(c.selectedRelativeHandSlot.onset==native.selectedRelativeHandSlot.onset&&c.selectedRelativeHandSlot.duration==native.selectedRelativeHandSlot.duration
                    &&c.annotationsJson==native.annotationsJson&&c.attackAuthority==native.attackAuthority&&c.blockIndex==native.blockIndex
                    &&c.gridColumn==native.gridColumn&&c.sourceLine==native.sourceLine&&c.sourceColumn1Based==native.sourceColumn1Based&&c.sourceRef.empty(),
                    "ALL_PHYSICAL_SLOT_SOURCE_ANNOTATION_LOCATOR_PARITY");++physicalContacts;
            }
            ++physicalVariants;
        }
        reps.emplace(d.level(),&d);++physicalRows;
    }
    for(const auto& x:reps) {
        std::shared_ptr<const S::Projection> retainedProjection;
        std::unique_ptr<S::SourceHandle> retained;
        {
            auto caller=*x.second;auto h=S::SourceHandle::physical(caller);
            retained=std::make_unique<S::SourceHandle>(h);retainedProjection=h.projection(S::Start::Down);
            caller=replacement;
        }
        binding(*retained,*x.second);check(retainedProjection->sourceKey==x.second->sourceKey(),"PHYSICAL_PROJECTION_OUTLIVES_CALLER_SCOPE");
        retained->requireSourceParity(*retainedProjection,S::Start::Down);negatives(*retained);
    }
    check(S::legacyProjectionBuildCount()==0,"ALL_339_PHYSICAL_ROWS_NEVER_CONSTRUCT_MUSICMODEL");
}
void legacy() {
    const auto& replacement=O::definition(O::keys().back());std::map<int,const O::Definition*> reps;
    for(const auto& key:O::keys()) {
        const auto& d=O::definition(key);auto caller=d;auto h=S::SourceHandle::ordered(caller);
        caller=key==replacement.sourceKey()?O::definition(O::keys().front()):replacement;
        binding(h,d);binding(S::SourceHandle(h),d);check(h.selectedMetricEnd()==d.metricEnd(),"LEGACY_HANDLE_ENDPOINT_ROUNDTRIP");
        reps.emplace(d.level(),&d);++legacyRows;
    }
    for(const auto& x:reps) {
        std::unique_ptr<S::SourceHandle> retained;
        {auto caller=*x.second;auto h=S::SourceHandle::ordered(caller);retained=std::make_unique<S::SourceHandle>(h);caller=replacement;}
        binding(*retained,*x.second);check(retained->trustedMetadataJson()==x.second->retainedMetadataJson(),"LEGACY_METADATA_CALLER_LIFETIME");
        for(const auto start:{S::Start::Down,S::Start::Up}) {
            const auto p=retained->projection(start);const auto native=x.second->reference(start==S::Start::Down?O::Start::Down:O::Start::Up);
            check(p==retained->projection(start)&&p->legacyMusicModelUsed&&p->contacts.size()==native.events.size(),"LEGACY_CACHED_REFERENCE_CONVERSION");retained->requireSourceParity(*p,start);
            for(std::size_t n=0;n<native.events.size();++n) {
                const auto& e=native.events[n];const auto& t=e.tones.front();const auto c=retained->contact(n+1,start);
                check(c.ordinal==n+1&&c.stringLowToHigh==t.string&&c.fret==t.fret&&c.finger==std::stoi(t.finger)&&c.pick==e.handDirection
                    &&c.midi==t.midi&&c.spelling==t.spelling&&!c.acousticSoundingSpan&&c.sourceRef==e.sourceRef
                    &&c.selectedRelativeHandSlot.onset==*e.span.onset&&c.selectedRelativeHandSlot.duration==*e.span.duration,
                    "REPRESENTATIVE_LEGACY_CONTACT_SOURCE_PARITY");++legacyContacts;
            }
            ++legacyVariants;
        }
        negatives(*retained);
    }
    auto h=S::SourceHandle::ordered(*reps.begin()->second);const auto before=S::legacyProjectionBuildCount();
    std::vector<std::future<std::shared_ptr<const S::Projection>>> work;
    for(int n=0;n<8;++n)work.push_back(std::async(std::launch::async,[h]{return h.projection(S::Start::Down);}));
    const auto p=work[0].get();for(std::size_t n=1;n<work.size();++n)check(p==work[n].get(),"SHARED_COPIED_HANDLE_THREAD_CACHE_SINGLE_PROJECTION");
    check(S::legacyProjectionBuildCount()==before+1,"ONLY_ONE_ACTUAL_LEGACY_MODEL_BUILD_FOR_SHARED_CACHE");
    auto bad=*p;bad.family=S::Family::PhysicalContact;refuses([&]{h.requireSourceParity(bad,S::Start::Down);});
    refuses([]{(void)S::SourceHandle::orderedKey("unknown");});refuses([]{(void)S::SourceHandle::physicalKey(O::keys().front());});
    refuses([]{(void)S::SourceHandle::orderedKey(P::keys().front());});
}
}
int main() {
    try {
        static_assert(std::is_copy_constructible_v<S::SourceHandle>&&!std::is_copy_assignable_v<S::SourceHandle>);
        physical();legacy();check(physicalRows==339&&physicalVariants==678&&physicalContacts==37812&&legacyRows==1401&&legacyVariants==20,"COMPLETE_NEW_ADAPTER_DENOMINATORS");
        std::cout<<"{\"result\":\"PASS\",\"physical_rows\":"<<physicalRows<<",\"physical_variants\":"<<physicalVariants
            <<",\"physical_contact_roundtrips\":"<<physicalContacts<<",\"physical_MusicModels_created\":0,\"legacy_handle_rows\":"<<legacyRows
            <<",\"legacy_representative_variants\":"<<legacyVariants<<",\"legacy_contact_roundtrips\":"<<legacyContacts
            <<",\"source_policy_tags\":28,\"caller_scope_policies\":28,\"legacy_projection_builds\":"<<S::legacyProjectionBuildCount()
            <<",\"assertions\":"<<checks<<",\"refusals\":"<<refusals<<",\"old_owner_or_music_validation_QA_replayed\":false,\"official_runtime_acceptance_increments\":0}\n";return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
