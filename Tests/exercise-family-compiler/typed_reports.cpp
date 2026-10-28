#include "tasks/ManualTaskAdapter.hpp"
#include "ExpectedReports.hpp"
#include <iostream>
#include <set>

using namespace fathom;
using namespace fathom::tasks;
static_assert(!std::is_copy_constructible_v<ManualTaskAdapter> && !std::is_copy_assignable_v<ManualTaskAdapter>);
static_assert(!std::is_move_constructible_v<ManualTaskAdapter> && !std::is_move_assignable_v<ManualTaskAdapter>);
namespace {
std::size_t checks=0,refusals=0;
void need(bool value){++checks;if(!value)throw std::runtime_error("Typed family check failed");}
bool apply(ManualTaskAdapter& a,IntentKind k,std::optional<json::Value> report=std::nullopt){
    return a.apply(a.capture(k),std::nullopt,{40,200},std::move(report));
}
void refuse(ManualTaskAdapter& a,IntentKind k,std::optional<json::Value> report=std::nullopt){
    const auto size=a.history().size();const auto revision=a.revision();const auto before=a.view();
    need(!apply(a,k,std::move(report)));++refusals;
    need(a.history().size()==size&&a.revision()==revision&&a.view().phase==before.phase);
}
}
int main(){try{
    need(compiledFamilyKeys().size()==167);std::set<std::string> classes;
    for(const auto& row:expected::rows){
        const auto& d=compiledFamilyDefinition(row.key);need(d.reportContract().has_value());
        const auto setup=json::parse(row.setup),actions=json::parse(row.actions),release=json::parse(row.release);
        need(d.reportContract()->setup==setup&&d.reportContract()->actions==actions.array()&&d.reportContract()->release==release);
        classes.insert(row.behaviorClass);ManualTaskAdapter a(d);
        need(apply(a,IntentKind::SourceOrder));refuse(a,IntentKind::Ready);
        need(apply(a,IntentKind::Ready,setup));need(a.view().phase==Phase::ManualSteps);
        for(std::size_t n=0;n<4;++n){
            const auto stale=a.capture(IntentKind::Acknowledge);
            auto wrong=actions.array()[n];wrong.object().at("action_order")=json::Value::fromInteger(99);
            refuse(a,IntentKind::Acknowledge,wrong);
            need(apply(a,IntentKind::Acknowledge,actions.array()[n]));
            const auto count=a.history().size();need(!a.apply(stale,std::nullopt,{40,200},actions.array()[n]));++refusals;
            need(a.history().size()==count);
        }
        need(a.view().phase==Phase::Release&&a.view().outcome==Outcome::None);
        refuse(a,IntentKind::Release,json::Value::Object{{"released_completely_reported",false}});
        need(apply(a,IntentKind::Release,release));need(a.view().outcome==Outcome::UserReportedStepsFinished);
        need(a.history().size()==7);for(const auto& event:a.history())need(!event.observedPerformance&&!event.grantsCredit);
        const auto old=a.history().front().reported;need(apply(a,IntentKind::Again));need(a.history().size()==8);
        need(a.history().front().reported==old&&a.view().phase==Phase::Choose&&!a.diagnosis());
        // Naming/manual-report mismatches are reports, not observed failures.
        ManualTaskAdapter b(d);need(apply(b,IntentKind::SourceOrder));auto bad=setup;bad.object().at("root")="wrong";
        need(apply(b,IntentKind::Ready,bad));need(b.view().phase==Phase::Release&&b.diagnosis());
        need(b.diagnosis()->object().at("reported")==bad&&!b.diagnosis()->object().at("observed_failure").boolean());
        need(apply(b,IntentKind::Release,release));need(b.view().outcome==Outcome::RetryRequested);
        need(apply(b,IntentKind::Again)&&!b.diagnosis());
        need(apply(b,IntentKind::SourceOrder)&&apply(b,IntentKind::Ready,setup));
        need(apply(b,IntentKind::Unknown,json::Value::Object{{"response","unknown"}}));
        need(b.view().phase==Phase::Release&&b.diagnosis()->object().at("code").string()=="MANUAL_UNKNOWN");
        need(apply(b,IntentKind::Release,release)&&b.view().outcome==Outcome::RetryRequested);
        ManualTaskAdapter c(d);need(apply(c,IntentKind::SourceOrder));auto malformed=setup;malformed.object().at("minimum_pressure_reported")="true";
        refuse(c,IntentKind::Ready,malformed);need(apply(c,IntentKind::Ready,setup));
        auto contact=actions.array().front();contact.object().at("written_action").object().at("voices").array().front().object().at("printed_degree")="wrong";
        need(apply(c,IntentKind::Acknowledge,contact));need(c.view().phase==Phase::Release&&c.diagnosis());
        need(c.history().back().reported==contact&&c.view().outcome==Outcome::None);
    }
    need(classes.size()==24);
    for(const auto& key:{std::string{"foreign"},std::string{expected::representative}}){
        try{(void)compiledFamilyDefinition(key);need(false);}catch(const Error& e){need(e.code=="COMPILED_FAMILY_SCOPE");++refusals;}
    }
    // Existing representative remains source-order compatible and noncredit.
    ManualTaskAdapter legacy(representativeDefinition(expected::representative));
    need(apply(legacy,IntentKind::SourceOrder)&&apply(legacy,IntentKind::Ready));
    for(int n=0;n<4;++n)need(apply(legacy,IntentKind::Acknowledge));
    need(apply(legacy,IntentKind::Release)&&legacy.view().outcome==Outcome::UserReportedStepsFinished);
    std::cout<<"{\"result\":\"PASS\",\"rows\":167,\"classes\":24,\"assertions\":"<<checks<<",\"refusals\":"<<refusals<<",\"runtime_admitted\":false,\"official_accepted\":false}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
