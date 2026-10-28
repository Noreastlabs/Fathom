#include "tasks/ManualTaskAdapter.hpp"
#include "ExpectedRows.hpp"
#include <iostream>
#include <set>
#include <stdexcept>

using namespace fathom;
using namespace fathom::tasks;
static std::size_t checks=0,refusals=0;
static void check(bool value,const char* why){++checks;if(!value)throw std::runtime_error(why);}
template<class F> static void refuses(F run){bool caught=false;try{run();}catch(const Error&){caught=true;}check(caught,"Expected precise task refusal");++refusals;}
static void same(const View& a,const View& b){
    check(a.mode==b.mode&&a.phase==b.phase&&a.outcome==b.outcome&&a.selectedBpm==b.selectedBpm&&
          a.actionIndex==b.actionIndex&&a.needsManualRelease==b.needsManualRelease&&a.requiresSetup==b.requiresSetup,
          "Existing representative behavior parity");
}
static constexpr TempoRange host{40,200}; // synthetic host capability, not source/app tempo authority
static bool apply(ManualTaskAdapter& a,IntentKind kind,std::optional<int> bpm=std::nullopt){return a.apply(a.capture(kind),bpm,host);}
static void finish(Task& task){
    task.chooseSourceOrder();task.ready(host);
    for(std::size_t i=0;i<4;++i){check(task.view().actionIndex==i,"All-row four-action order");task.respond(Response::Acknowledged);}
    check(task.view().phase==Phase::Release&&task.view().outcome==Outcome::None,"No completion before release");
    task.acknowledgeRelease();
    check(task.view().outcome==Outcome::UserReportedStepsFinished,"Manual report only");
}

static void behavior(const Definition& d,const Definition& rep){
    Task t(d), baseline(rep);
    refuses([&]{t.ready(host);});refuses([&]{t.respond(Response::Acknowledged);});
    refuses([&]{t.acknowledgeRelease();});
    t.chooseSourceOrder();baseline.chooseSourceOrder();same(t.view(),baseline.view());
    t.ready(host);baseline.ready(host);same(t.view(),baseline.view());
    refuses([&]{t.chooseSourceOrder();});refuses([&]{t.ready(host);});
    refuses([&]{t.beginAnotherPass();});refuses([&]{t.respond(static_cast<Response>(99));});
    for(int i=0;i<4;++i){t.respond(Response::Acknowledged);baseline.respond(Response::Acknowledged);same(t.view(),baseline.view());}
    refuses([&]{t.respond(Response::Acknowledged);});refuses([&]{t.beginAnotherPass();});
    t.acknowledgeRelease();baseline.acknowledgeRelease();same(t.view(),baseline.view());
    refuses([&]{t.acknowledgeRelease();});refuses([&]{t.cancel();});
    t.beginAnotherPass();baseline.beginAnotherPass();same(t.view(),baseline.view());
    for(auto response:{Response::NeedsRetry,Response::Stopped}){
        t.chooseSourceOrder();baseline.chooseSourceOrder();t.ready(host);baseline.ready(host);
        t.respond(response);baseline.respond(response);same(t.view(),baseline.view());
        check(t.view().needsManualRelease,"Retry/stop requires release");
        refuses([&]{t.beginAnotherPass();});
        t.acknowledgeRelease();baseline.acknowledgeRelease();same(t.view(),baseline.view());
        t.beginAnotherPass();baseline.beginAnotherPass();same(t.view(),baseline.view());
    }
    t.cancel();baseline.cancel();same(t.view(),baseline.view());
    t.acknowledgeRelease();baseline.acknowledgeRelease();same(t.view(),baseline.view());
    t.beginAnotherPass();baseline.beginAnotherPass();same(t.view(),baseline.view());
    refuses([&]{t.chooseEvenPulse(0,host);});
    refuses([&]{t.chooseEvenPulse(90,{100,80});});
    t.chooseEvenPulse(90,host);baseline.chooseEvenPulse(90,host);same(t.view(),baseline.view());
    refuses([&]{t.ready({100,200});});
    t.ready(host);baseline.ready(host);same(t.view(),baseline.view());
    for(int q=0;q<4;++q){
        t.followCuePosition(QuarterTime{Rational{q,1}});baseline.followCuePosition(QuarterTime{Rational{q,1}});same(t.view(),baseline.view());
        check(t.view().actionIndex==static_cast<std::size_t>(q),"Authored display cue order");
    }
    refuses([&]{t.followCuePosition(QuarterTime{Rational{1,1}});});
    t.followCuePosition(QuarterTime{Rational{4,1}});baseline.followCuePosition(QuarterTime{Rational{4,1}});same(t.view(),baseline.view());
    t.acknowledgeRelease();baseline.acknowledgeRelease();same(t.view(),baseline.view());
    check(t.view().outcome==Outcome::None,"Cue elapsed time is not performed completion");

    ManualTaskAdapter a(d), other(d);
    auto foreign=other.capture(IntentKind::SourceOrder);
    check(!a.apply(foreign,std::nullopt,host),"Foreign instance refused");++refusals;
    auto stale=a.capture(IntentKind::SourceOrder);
    check(apply(a,IntentKind::SourceOrder),"Source order selected");
    check(!a.apply(stale,std::nullopt,host),"Stale revision refused");++refusals;
    check(apply(a,IntentKind::Ready),"Source Ready");
    auto modified=a.capture(IntentKind::Acknowledge);modified.sourceKey="foreign";
    check(!a.apply(modified,std::nullopt,host),"Foreign key refused");++refusals;
    modified=a.capture(IntentKind::Acknowledge);modified.policySha256="foreign";
    check(!a.apply(modified,std::nullopt,host),"Foreign policy refused");++refusals;
    check(!apply(a,IntentKind::Release),"Premature release refused");++refusals;
    auto previousPass=a.capture(IntentKind::Acknowledge);
    check(apply(a,IntentKind::Retry),"Retry enters release");
    check(!apply(a,IntentKind::Again),"Retry cannot bypass release");++refusals;
    check(apply(a,IntentKind::Release),"Manual release acknowledged");
    check(apply(a,IntentKind::Again),"Fresh pass available");
    check(!a.apply(previousPass,std::nullopt,host),"Previous pass token refused");++refusals;
    check(apply(a,IntentKind::SourceOrder)&&apply(a,IntentKind::Ready),"Restart with setup");
    auto beforeNavigation=a.capture(IntentKind::Acknowledge);a.invalidateForNavigation();
    check(a.view().phase==Phase::Release&&!a.clockArmed(),"Navigation release fence");
    check(!a.apply(beforeNavigation,std::nullopt,host),"Navigation stale token refused");++refusals;
    check(apply(a,IntentKind::Release)&&apply(a,IntentKind::Again),"Navigation recovery");
    check(!apply(a,IntentKind::EvenPulse),"No implicit BPM");++refusals;
    check(apply(a,IntentKind::EvenPulse,90),"Explicit authored cue choice");
    check(!apply(a,IntentKind::Ready,100),"Changed Ready BPM refused");++refusals;
    check(apply(a,IntentKind::Ready,90),"Current host BPM Ready");
    scheduler::Owner owner;owner.id[6]=0x40;owner.id[8]=0x80;owner.generation=1;owner.epoch=1;
    check(a.armClock(owner,1,48000),"Shared owner clock binding");
    platform::MetronomeProgress progress;progress.owner=owner;progress.binding=1;progress.sequence=1;
    progress.phase=metronome::Phase::Running;progress.tempo.tempo=90;progress.clientAcceptedThrough=1;
    check(a.progress(progress),"Shared clock origin");
    check(!a.progress(progress),"Repeated progress refused");++refusals;
    progress.sequence=2;progress.owner.epoch=2;
    check(!a.progress(progress),"Foreign clock owner refused");++refusals;
    progress.owner=owner;progress.totalActiveFrames=128000;
    check(a.progress(progress)&&a.view().phase==Phase::Release&&!a.clockArmed(),"Four cue units return to manual release");
    check(apply(a,IntentKind::Release)&&a.view().outcome==Outcome::None,"Cues do not report source playing");
    check(!a.progress(progress),"Late progress refused");++refusals;
}

int main(){
    try {
        check(compiledFamilyKeys().size()==167,"Exact family size");
        const auto& rep=representativeDefinition(expected::representative);
        refuses([&]{compiledFamilyDefinition(expected::representative);});
        refuses([&]{compiledFamilyDefinition("foreign");});
        std::set<std::string> unique;
        for(const auto& row:expected::rows){
            check(unique.insert(row.key).second,"Unique source keys");
            const auto& d=compiledFamilyDefinition(row.key);
            check(&d==&compiledFamilyDefinition(row.key),"One immutable shared definition");
            check(d.sourceKey()==row.key&&d.policySha256()==rep.policySha256(),"Source/policy binding");
            check(d.actions().size()==4&&d.cueEnd()==Rational{4,1},"Reviewed four-action cue policy");
            const auto& blocked=d.actions()[0].contacts;check(blocked.size()==3,"Written blocked triad");
            for(std::size_t i=0;i<3;++i){
                const auto& contact=blocked[i];const auto& o=row.voices[i];
                check(contact.sourceString==o.sourceString&&contact.fret==o.fret&&contact.writtenStandardTuningMidi==o.writtenStandardTuningMidi,"Original source contact parity");
                check(d.actions()[i+1].contacts.size()==1,"Individual low/middle/high action");
                const auto& v=d.actions()[i+1].contacts[0];
                check(v.sourceString==o.sourceString&&v.fret==o.fret&&v.writtenStandardTuningMidi==o.writtenStandardTuningMidi,"Original arpeggio order parity");
                check(d.actions()[i+1].authoredCueOnset==Rational{static_cast<std::int64_t>(i+1),1},"Authored cue not source clock");
            }
            refuses([&]{representativeDefinition(row.key);});
            Task task(d);finish(task);
        }
        for(const auto* key:expected::classes)behavior(compiledFamilyDefinition(key),rep);
        std::cout<<"{\"result\":\"PASS\",\"rows\":167,\"behavior_classes\":24,\"assertions\":"<<checks
                 <<",\"refusals\":"<<refusals<<",\"runtime_admitted\":false,\"official_accepted\":false}\n";
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
