#include "tasks/RecipeTask.hpp"
#include <algorithm>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <set>
#include <type_traits>

using namespace fathom;
using namespace fathom::tasks::recipes;
using V = json::Value;
using O = V::Object;
using A = V::Array;
static_assert(!std::is_copy_constructible_v<RecipeTask> && !std::is_copy_assignable_v<RecipeTask>);
static_assert(!std::is_move_constructible_v<RecipeTask> && !std::is_move_assignable_v<RecipeTask>);
static_assert(!std::is_constructible_v<Definition,const char*,const char*,const char*,const char*>);
namespace {
std::size_t checks{}, refusals{}, cases{}, rows{};
void need(bool value, const char* code="TEST") { ++checks; if (!value) throw std::runtime_error(code); }
const V& field(const V& object, const char* name) { const auto* value=object.find(name); need(value!=nullptr,"FIXTURE_FIELD"); return *value; }
bool same(const View& a, const View& b) {
    return a.phase==b.phase && a.outcome==b.outcome && a.pendingOutcome==b.pendingOutcome && a.step==b.step &&
           a.needsManualRelease==b.needsManualRelease && a.observedPerformance==b.observedPerformance && a.grantsCredit==b.grantsCredit;
}
void act(RecipeTask& task, Intent kind, const V& payload=O{}) { task.apply(task.capture(kind),payload); }
void reject(const std::function<void()>& run) {
    try { run(); } catch (const std::exception&) { ++refusals; return; }
    throw std::runtime_error("EXPECTED_REFUSAL");
}
void unchanged(RecipeTask& task, const std::function<void()>& run) {
    const auto before=task.view(); const auto revision=task.revision(), pass=task.pass(); const auto size=task.history().size();
    const auto request=task.selectedRequest(), plan=task.selectedPlan(), diagnosis=task.diagnosis();
    reject(run);
    need(same(task.view(),before) && task.revision()==revision && task.pass()==pass && task.history().size()==size &&
         task.selectedRequest()==request && task.selectedPlan()==plan && task.diagnosis()==diagnosis,"REFUSAL_MUTATED_STATE");
}
const V release = O{{"released_completely_reported",true}};
void complete(RecipeTask& task, const A& reports) {
    for (const auto& report:reports) { need(task.expectedReport()==report,"REPORT_PARITY"); act(task,Intent::Report,report); }
    need(task.view().phase==Phase::Release && task.view().pendingOutcome==Outcome::UserReportedStepsFinished &&
         task.view().outcome==Outcome::None,"SUCCESS_RELEASE_BOUNDARY");
    unchanged(task,[&]{act(task,Intent::Again);});
    act(task,Intent::Release,release);
    need(task.view().phase==Phase::Closed && task.view().outcome==Outcome::UserReportedStepsFinished,"MANUAL_FINISH");
}
}
int main(int argc, char** argv) { try {
    need(argc==3,"ARGS: definitions.jsonl native-choice-oracle.jsonl");
    need(keys().size()==17); std::ifstream definitions(argv[1]); need(definitions.good()); std::string line;
    std::set<std::string> exact;
    while (std::getline(definitions,line)) {
        const auto row=json::parse(line); const auto key=field(row,"source_key").string(); const auto& d=definition(key);
        need(d.exportedDefinition()==row,"FULL_FROZEN_DEFINITION_PARITY");
        need(d.retainedContract()==field(row,"contract") && d.contractSha256()==field(row,"contract_sha256").string());
        need(d.sourceIdentity()==field(row,"source_identity").string());
        need(d.sourceClosureSha256()=="e1ec9a40e149cb58c60af53b9f5bf63e0e23ecb9a6359046bdf93a2798dfb511");
        need(allowedChoices(d).find("default_choice")->null()); need(exact.insert(key).second); ++rows;
    }
    need(rows==17); for (const auto& key:keys()) need(exact.count(key)==1);
    reject([]{(void)definition("foreign");});
    reject([]{(void)definition("exercise-completeness-r01/level068/modulea/p002-card01/p1");});
    std::ifstream input(argv[2]); need(input.good()); std::map<std::string,V> samples;
    while (std::getline(input,line)) {
        const auto golden=json::parse(line); const auto key=field(golden,"source_key").string(); const auto& d=definition(key);
        const auto& request=field(golden,"request"); const auto expected=field(golden,"selection");
        need(select(d,request)==expected,"FROZEN_SELECTION_PARITY"); ++cases;
        if (golden.find("responses")) need(samples.emplace(key,golden).second);
    }
    need(samples.size()==17 && cases>=34);
    for (const auto& item:samples) {
        const auto& golden=item.second; const auto& d=definition(item.first); const auto request=field(golden,"request");
        const auto responses=field(golden,"responses").array(), next=field(golden,"next_steps").array();
        need(field(d.retainedSourceContext(),"context_tasks").isArray() && !field(d.retainedSourceContext(),"context_tasks").array().empty(), "RETAINED_CONTEXT");
        RecipeTask idle(d); const auto lateChoose=idle.capture(Intent::Choose);
        need(idle.fenceInactiveForNavigation() && idle.view().phase==Phase::Select && idle.history().size()==1 &&
             idle.pass()==2 && !idle.selectedRequest() && !idle.selectedPlan(), "IDLE_FENCE_HISTORY");
        unchanged(idle,[&]{idle.apply(lateChoose,request);});
        act(idle,Intent::Choose,request); const auto activeRevision=idle.revision(); const auto activeHistory=idle.history().size();
        need(!idle.fenceInactiveForNavigation() && idle.revision()==activeRevision && idle.history().size()==activeHistory,"ACTIVE_FENCE_REFUSED");
        act(idle,Intent::Stop,O{{"step",V::fromInteger(1)},{"response","stopped"}});
        need(!idle.fenceInactiveForNavigation() && idle.view().phase==Phase::Release,"RELEASE_FENCE_REFUSED");
        act(idle,Intent::Release,release); const auto lateAgain=idle.capture(Intent::Again);
        const auto closedHistory=idle.history().size(); const auto closedPass=idle.pass(); const auto closedDiagnosis=idle.diagnosis();
        need(idle.fenceInactiveForNavigation() && idle.view().phase==Phase::Closed &&
             idle.view().outcome==Outcome::Cancelled && idle.history().size()==closedHistory+1 &&
             idle.pass()==closedPass+1 && idle.diagnosis()==closedDiagnosis && idle.selectedRequest()==request,"CLOSED_FENCE_HISTORY");
        unchanged(idle,[&]{idle.apply(lateAgain,O{});});
        RecipeTask task(d), other(d);
        need(task.view().phase==Phase::Select && !task.selectedRequest() && !task.selectedPlan());
        unchanged(task,[&]{(void)task.expectedReport();});
        unchanged(task,[&]{act(task,Intent::Report,responses.front());});
        unchanged(task,[&]{act(task,Intent::Release,release);});
        const auto sourceToken=task.capture(Intent::Choose);
        unchanged(other,[&]{other.apply(sourceToken,request);});
        for (int fieldIndex=0;fieldIndex<9;++fieldIndex) {
            auto token=sourceToken;
            switch(fieldIndex) {
                case 0: ++token.instance; break; case 1: ++token.pass; break; case 2: ++token.revision; break;
                case 3: token.sourceKey="foreign"; break; case 4: token.contractSha256=std::string(64,'0'); break;
                case 5: token.sourceClosureSha256=std::string(64,'0'); break; case 6: token.phase=Phase::Steps; break;
                case 7: token.step=1; break; case 8: token.intent=static_cast<Intent>(999); break;
            }
            unchanged(task,[&]{task.apply(token,request);});
        }
        for (const auto& change: {O{{"start_stroke",""}}, O{{"package_key","foreign"}}, O{{"contract_sha256",std::string(64,'0')}}}) {
            auto wrong=request; for (const auto& e:change) wrong.object().at(e.first)=e.second;
            unchanged(task,[&]{act(task,Intent::Choose,wrong);});
        }
        auto extra=request; extra.object().emplace("bpm",V::fromInteger(90)); unchanged(task,[&]{act(task,Intent::Choose,extra);});
        act(task,Intent::Choose,request); need(task.selectedPlan()==field(golden,"selection"));
        unchanged(task,[&]{act(task,Intent::Choose,request);});
        for (std::size_t i=0;i<responses.size();++i) {
            need(task.currentStep()==next[i],"NEXT_STEP_PARITY"); need(task.expectedReport()==responses[i]);
            auto wrong=responses[i]; wrong.object().at("step")=V::fromInteger(99);
            unchanged(task,[&]{act(task,Intent::Report,wrong);});
            wrong=responses[i]; wrong.object().at("step")=true;
            unchanged(task,[&]{act(task,Intent::Report,wrong);});
            wrong=responses[i]; wrong.object().emplace("extra",true);
            unchanged(task,[&]{act(task,Intent::Report,wrong);});
            const auto stale=task.capture(Intent::Report); act(task,Intent::Report,responses[i]);
            unchanged(task,[&]{task.apply(stale,responses[i]);});
        }
        need(task.view().phase==Phase::Release && task.view().pendingOutcome==Outcome::UserReportedStepsFinished);
        unchanged(task,[&]{act(task,Intent::Reopen);});
        unchanged(task,[&]{act(task,Intent::Release,O{{"released_completely_reported",false}});});
        unchanged(task,[&]{act(task,Intent::Release,O{{"released_completely_reported",V::fromInteger(1)}});});
        act(task,Intent::Release,release); need(task.view().outcome==Outcome::UserReportedStepsFinished);
        const auto oldPass=task.capture(Intent::Reopen); const auto history=task.history(); act(task,Intent::Again);
        need(task.pass()==2 && task.history().size()==history.size()+1 && task.history().front().reported==request);
        need(task.view().phase==Phase::Select && !task.selectedPlan() && !task.diagnosis());
        unchanged(task,[&]{task.apply(oldPass,O{});});
        for (const auto& event:task.history()) need(!event.observedPerformance && !event.grantsCredit && !event.before.observedPerformance && !event.after.grantsCredit);

        RecipeTask recovery(d); act(recovery,Intent::Choose,request);
        auto wrong=recovery.expectedReport(); auto boolean=std::find_if(wrong.object().begin(),wrong.object().end(),[](const auto& e){return e.second.isBool();});
        need(boolean!=wrong.object().end()); const auto booleanName=boolean->first;
        boolean->second="true"; unchanged(recovery,[&]{act(recovery,Intent::Report,wrong);});
        wrong=recovery.expectedReport(); wrong.object().at("response")="unknown";
        unchanged(recovery,[&]{act(recovery,Intent::Report,wrong);});
        wrong=recovery.expectedReport(); wrong.object().at(booleanName)=false; act(recovery,Intent::Report,wrong);
        need(recovery.view().phase==Phase::Release && recovery.view().pendingOutcome==Outcome::RetryRequested && recovery.diagnosis());
        need(!field(*recovery.diagnosis(),"observed_failure").boolean() && field(*recovery.diagnosis(),"reported")==wrong);
        unchanged(recovery,[&]{act(recovery,Intent::Again);}); act(recovery,Intent::Release,release);
        need(recovery.view().outcome==Outcome::RetryRequested); act(recovery,Intent::Again);
        act(recovery,Intent::Choose,request); complete(recovery,responses); need(recovery.history().front().reported==request);

        for (const auto kind:{Intent::Stop,Intent::Retry}) {
            RecipeTask stop(d); act(stop,Intent::Choose,request);
            V report=O{{"step",V::fromInteger(1)},{"response",kind==Intent::Stop?"stopped":"needs_retry"}};
            auto malformed=report; malformed.object().emplace("extra",true); unchanged(stop,[&]{act(stop,kind,malformed);});
            act(stop,kind,report); need(stop.view().phase==Phase::Release && stop.diagnosis());
            unchanged(stop,[&]{act(stop,Intent::Report,responses.front());}); act(stop,Intent::Release,release);
            need(stop.view().outcome==(kind==Intent::Stop?Outcome::Cancelled:Outcome::RetryRequested));
        }
        RecipeTask navigation(d); act(navigation,Intent::Choose,request); const auto stale=navigation.capture(Intent::Report);
        act(navigation,Intent::Navigate); need(navigation.view().phase==Phase::Release && navigation.diagnosis());
        unchanged(navigation,[&]{navigation.apply(stale,responses.front());});
        unchanged(navigation,[&]{act(navigation,Intent::Reopen);}); act(navigation,Intent::Release,release); act(navigation,Intent::Reopen);
        need(navigation.pass()==2 && navigation.history().size()==4 && !navigation.selectedPlan());

        if (d.recipe()==Recipe::CallAnswer) {
            reject([&]{(void)allowedChoices(d,V(O{{"string",V::fromInteger(1)},{"fret",V::fromInteger(0)}}));});
            need(field(field(golden,"selection"),"paired").array().size()==16 && field(field(golden,"selection"),"variation_answer").array().size()==8);
        } else {
            auto bad=request; bad.object().at("source_contact")=O{{"string",true},{"fret",V::fromInteger(0)}};
            reject([&]{(void)select(d,bad);});
            bad=request; bad.object().at("target_contact")=O{{"string",V::fromInteger(1)},{"fret",V::fromInteger(99)}}; reject([&]{(void)select(d,bad);});
            for (const std::string& plan:{std::string(" "),std::string(501,'x'),std::string("\xc2\xa0\xe3\x80\x80")}) {
                bad=request; bad.object().at("rest_of_bar_plan")=plan; reject([&]{(void)select(d,bad);});
            }
            bad=request; std::string unicode; for(int n=0;n<500;++n) unicode+="\xc3\xa9";
            bad.object().at("rest_of_bar_plan")=std::string("\xc2\xa0")+unicode+"\xe3\x80\x80";
            need(field(select(d,bad),"rest_of_bar_plan").string()==field(bad,"rest_of_bar_plan").string(),"UNICODE_PLAN_PARITY");
            need(field(d.retainedContract(),"printed_contact_positions").null());
            need(!field(field(golden,"selection"),"remainder_notes_or_attacks_generated").boolean());
        }
    }
    std::cout<<"{\"result\":\"PASS\",\"rows\":"<<rows<<",\"finite_choices\":"<<cases
             <<",\"assertions\":"<<checks<<",\"refusals\":"<<refusals
             <<",\"performance_observed\":false,\"runtime_admitted\":false,\"official_accepted\":false}\n";
    return 0;
} catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;} }
