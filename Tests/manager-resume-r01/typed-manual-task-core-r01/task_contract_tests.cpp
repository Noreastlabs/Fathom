#include "TaskContract.hpp"
#include <cstdlib>
#include <iostream>
#include <string>
#include <type_traits>
#include <utility>

using namespace fathom;
using namespace fathom::tasks;
namespace {
int checks = 0;
void check(bool value, const char* label) {
    ++checks;
    if (!value) { std::cerr << "FAIL: " << label << '\n'; std::exit(1); }
}
template<class F> void refuses(const char* code, F&& f) {
    bool caught = false;
    try { f(); } catch (const Error& e) { caught = e.code == code; }
    check(caught, code);
}
bool same(View a, View b) {
    return a.mode==b.mode && a.phase==b.phase && a.outcome==b.outcome
        && a.selectedBpm==b.selectedBpm && a.actionIndex==b.actionIndex
        && a.needsManualRelease==b.needsManualRelease && a.requiresSetup==b.requiresSetup;
}
template<class F> void unchanged(Task& task, const char* code, F&& f) {
    const auto before = task.view();
    refuses(code, std::forward<F>(f));
    check(same(before, task.view()), "refusal preserves state");
}
template<class T, class = void> struct acceptsTempo : std::false_type {};
template<class T> struct acceptsTempo<T, std::void_t<decltype(std::declval<Task&>().chooseEvenPulse(std::declval<T>(), TempoRange{1,2}))>> : std::true_type {};
constexpr TempoRange host{20, 300}; // explicit synthetic host, no product/default BPM claim
const std::string key = "exercise-completeness-r01/level053/moduleb/p003-t1-r1-c2/cmajrp";
Task started(bool paced) {
    Task task{representativeDefinition(key)};
    if (paced) task.chooseEvenPulse(80, host); else task.chooseSourceOrder();
    task.ready(host);
    return task;
}
void releaseAndReset(Task& task, Outcome expected) {
    check(task.view().phase==Phase::Release && task.view().needsManualRelease, "release required");
    check(task.view().outcome==Outcome::None && !task.view().actionIndex, "release is not completion");
    unchanged(task, "REPEAT_STATE", [&]{task.beginAnotherPass();});
    unchanged(task, "READY_STATE", [&]{task.ready(host);});
    unchanged(task, "SELECTION_STATE", [&]{task.chooseSourceOrder();});
    unchanged(task, "SELECTION_STATE", [&]{task.chooseEvenPulse(80,host);});
    unchanged(task, "CUE_STATE", [&]{task.followCuePosition(QuarterTime{Rational{1,1}});});
    unchanged(task, "MANUAL_RESPONSE_STATE", [&]{task.respond(Response::Acknowledged);});
    task.acknowledgeRelease();
    check(task.view().phase==Phase::Closed && task.view().outcome==expected, "explicit close outcome");
    unchanged(task, "RELEASE_STATE", [&]{task.acknowledgeRelease();});
    unchanged(task, "CANCEL_STATE", [&]{task.cancel();});
    task.beginAnotherPass();
    check(task.view().phase==Phase::Choose && task.view().mode==Mode::Unselected, "fresh mode required");
    check(!task.view().selectedBpm && !task.view().actionIndex && task.view().requiresSetup, "no tempo/cue resume");
    check(task.view().outcome==Outcome::None, "no carried completion");
}
}
static_assert(!std::is_default_constructible_v<Definition>);
static_assert(!std::is_aggregate_v<Definition>);
static_assert(!std::is_constructible_v<Definition, std::string>);
static_assert(!acceptsTempo<bool>::value && !acceptsTempo<double>::value && !acceptsTempo<unsigned>::value);
static_assert(acceptsTempo<int>::value);
static_assert(std::is_same_v<decltype(std::declval<const Definition&>().actions()), const std::vector<Action>&>);

int main() {
    const auto& d = representativeDefinition(key);
    refuses("REPRESENTATIVE_SCOPE", []{representativeDefinition("unknown");});
    refuses("REPRESENTATIVE_SCOPE", []{representativeDefinition("exercise-completeness-r01/level053/moduleb/p003-t1-r1-c3/cmaj1");});
    check(d.sourceKey()==key && d.actions().size()==4 && d.cueEnd()==Rational{4,1}, "exact representative");
    check(d.policySha256()=="5ca30eef84e88134336e01ec7ee6b23d81b531125c76a62023c0b2f8005af63b", "reviewed policy");
    check(d.setupInstructions().size()==5 && d.setupInstructions()[0].find("one progression")!=std::string::npos
        && d.setupInstructions()[0].find("relax the hand fully")!=std::string::npos, "full broader setup context");
    check(d.setupInstructions()[4].find("f2-3-1")!=std::string::npos, "suggested fingering");
    check(d.pacedChoiceExplanation().find("Fathom supplies")!=std::string::npos, "authored pacing visible");
    check(d.releaseInstruction()=="Release completely before the next shape.", "source release");
    const int strings[]{3,2,1}, frets[]{5,5,3}, pitches[]{60,64,67};
    for (std::size_t i=0;i<4;++i) {
        const auto& a=d.actions()[i];
        check(a.authoredCueOnset==Rational{static_cast<std::int64_t>(i),1}, "cue coordinates");
        check(a.contacts.size()==(i==0?3u:1u), "blocked versus sequential grouping");
        for(std::size_t j=0;j<a.contacts.size();++j) {
            const auto index=i==0?j:i-1;
            const auto& c=a.contacts[j];
            check(c.sourceString==strings[index] && c.fret==frets[index] && c.writtenStandardTuningMidi==pitches[index], "written contact order");
        }
    }
    Task fresh{d};
    check(fresh.view().mode==Mode::Unselected && fresh.view().phase==Phase::Choose && !fresh.view().selectedBpm, "initially unselected");
    unchanged(fresh,"READY_STATE",[&]{fresh.ready(host);});
    unchanged(fresh,"CUE_STATE",[&]{fresh.followCuePosition(QuarterTime{Rational{0,1}});});
    unchanged(fresh,"MANUAL_RESPONSE_STATE",[&]{fresh.respond(Response::Acknowledged);});
    unchanged(fresh,"RELEASE_STATE",[&]{fresh.acknowledgeRelease();});
    unchanged(fresh,"RETRY_STATE",[&]{fresh.requestRetry();});
    for (int tempo : {-1,0,19,301}) unchanged(fresh,"UNSUPPORTED_TEMPO",[&]{fresh.chooseEvenPulse(tempo,host);});
    for (auto range : {TempoRange{0,300},TempoRange{300,20}})
        unchanged(fresh,"HOST_TEMPO_CAPABILITY",[&]{fresh.chooseEvenPulse(80,range);});
    for (int edge : {20,300}) {fresh.chooseEvenPulse(edge,host);check(fresh.view().selectedBpm==edge,"inclusive host bound");}
    fresh.chooseEvenPulse(80,host);
    unchanged(fresh,"UNSUPPORTED_TEMPO",[&]{fresh.ready(TempoRange{90,300});});
    check(fresh.view().phase==Phase::Setup && fresh.view().selectedBpm==80, "current capability rechecked");
    fresh.chooseSourceOrder();
    check(!fresh.view().selectedBpm, "manual mode removes numeric tempo");
    fresh.ready(TempoRange{0,0}); // no clock is consumed by source-order mode
    unchanged(fresh,"READY_STATE",[&]{fresh.ready(host);});
    unchanged(fresh,"SELECTION_STATE",[&]{fresh.chooseEvenPulse(80,host);});
    unchanged(fresh,"MANUAL_RESPONSE",[&]{fresh.respond(static_cast<Response>(99));});
    for(std::size_t i=0;i<4;++i) {
        check(fresh.view().actionIndex==i && fresh.view().outcome==Outcome::None, "only current manual action");
        fresh.respond(Response::Acknowledged);
    }
    releaseAndReset(fresh,Outcome::UserReportedStepsFinished);

    auto paced=started(true);
    unchanged(paced,"MANUAL_RESPONSE_STATE",[&]{paced.respond(Response::Acknowledged);});
    paced.followCuePosition(QuarterTime{Rational{3,4}});
    check(paced.view().actionIndex==0,"fractional cue holds first action");
    paced.followCuePosition(QuarterTime{Rational{1,1}});
    check(paced.view().actionIndex==1,"cue boundary");
    paced.followCuePosition(QuarterTime{Rational{1,1}});
    check(paced.view().actionIndex==1,"repeated clock tick stable");
    unchanged(paced,"CUE_REGRESSION",[&]{paced.followCuePosition(QuarterTime{Rational{0,1}});});
    paced.followCuePosition(QuarterTime{Rational{7,2}});
    check(paced.view().actionIndex==3 && paced.view().outcome==Outcome::None,"skipped ticks update visual cue without completion");
    paced.followCuePosition(QuarterTime{Rational{4,1}});
    releaseAndReset(paced,Outcome::None);
    auto jumped=started(true);
    jumped.followCuePosition(QuarterTime{Rational{100,1}});
    releaseAndReset(jumped,Outcome::None);

    // Cancellation, retries and reopen must not bypass release or synthesize progress.
    for(bool mode : {false,true}) {
        for(int action=0;action<4;++action) {
            auto task=started(mode);
            if(mode) task.followCuePosition(QuarterTime{Rational{action,1}});
            else for(int j=0;j<action;++j) task.respond(Response::Acknowledged);
            task.cancel(); releaseAndReset(task,Outcome::Cancelled);
            task=started(mode);task.requestRetry();releaseAndReset(task,Outcome::RetryRequested);
        }
    }
    for(auto response : {Response::Stopped,Response::NeedsRetry}) {
        auto task=started(false);task.respond(response);
        releaseAndReset(task,response==Response::Stopped?Outcome::Cancelled:Outcome::RetryRequested);
    }
    for(int phase=0;phase<6;++phase) {
        Task task{d};
        if(phase==1) task.chooseEvenPulse(80,host);
        if(phase==2) task=started(false);
        if(phase>=3) task=started(true);
        if(phase>=4) task.cancel();
        if(phase==5) task.acknowledgeRelease();
        task.reopen();
        check(task.view().mode==Mode::Unselected && !task.view().selectedBpm,"reopen clears mode and tempo");
        releaseAndReset(task,Outcome::Interrupted);
    }
    Task beforeStart{d};beforeStart.cancel();releaseAndReset(beforeStart,Outcome::Cancelled);
    Task setup{d};setup.chooseSourceOrder();setup.cancel();releaseAndReset(setup,Outcome::Cancelled);
    // A copied definition outlives its local source wrapper; Task owns its data.
    Task owned=[] {Definition copied{representativeDefinition(key)};return Task{copied};}();
    check(owned.definition().actions()[0].contacts.size()==3,"owned definition lifetime");
    std::cout << "PASS " << checks << " causal typed-task checks; no UI/audio/history/admission claim\n";
}
