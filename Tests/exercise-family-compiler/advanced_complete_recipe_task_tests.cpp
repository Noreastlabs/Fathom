#include "tasks/AdvancedRecipeTask.hpp"
#include <algorithm>
#include <fstream>
#include <functional>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <type_traits>

using namespace fathom;
using namespace fathom::tasks::advanced;
using V=json::Value;using O=V::Object;using A=V::Array;
static_assert(!std::is_copy_constructible_v<AdvancedRecipeWorkflow> && !std::is_move_constructible_v<AdvancedRecipeWorkflow>);
namespace {
std::size_t assertions{},refusals{},rows{},actions{},recoveries{},texturesChecked{};
void need(bool b,const char* message="TEST") { ++assertions;if (!b) throw std::runtime_error(message); }
const V& field(const V& v,const char* n) { const auto* p=v.find(n);need(p!=nullptr,"FIXTURE_FIELD");return *p; }
V read(const char* path) { std::ifstream f(path);need(f.good());return json::parse(std::string(std::istreambuf_iterator<char>(f),{})); }
std::vector<V> lines(const char* path) { std::ifstream f(path);need(f.good());std::vector<V> result;std::string line;while (std::getline(f,line)) result.push_back(json::parse(line));return result; }
void act(AdvancedRecipeWorkflow& t,const std::string& a,const V& p=O{}) { t.apply(t.capture(a),p); }
void unchanged(AdvancedRecipeWorkflow& t,const std::function<void()>& operation) {
    const auto view=t.learnerView(),snapshot=t.snapshot();const auto token=t.capture("cancel");
    try { operation(); } catch (const std::exception&) {
        ++refusals;const auto after=t.capture("cancel");need(t.learnerView()==view && t.snapshot()==snapshot && token.owner.pass==after.owner.pass && token.owner.revision==after.owner.revision && token.state==after.state,"REFUSAL_CHANGED_OWNER_HISTORY_STATE");return;
    }
    throw std::runtime_error("EXPECTED_REFUSAL");
}
void step(AdvancedRecipeWorkflow& task,const V& s) {
    const auto action=field(s,"action").string();const auto payload=field(s,"payload");const auto owner=task.capture(action);
    if (const auto* refusal=s.find("refuse");refusal && refusal->boolean()) unchanged(task,[&]{task.apply(owner,payload);});
    else { task.apply(owner,payload);unchanged(task,[&]{task.apply(owner,payload);}); }
    need(task.learnerView()==field(s,"learner_view_after"),"PINNED_MODEL_VIEW_PARITY");
    if (const auto* obligations=s.find("obligations_after")) for (const auto& item:obligations->object()) need(field(task.snapshot(),item.first.c_str())==item.second,"PINNED_REDUCTION_OBLIGATION_PARITY");
    need(!field(task.snapshot(),"release_or_hearing_observed").boolean() && !field(task.snapshot(),"credit_awarded").boolean());
    if (action=="report") ++texturesChecked;
}
}
int main(int argc,char** argv) { try {
    need(argc==5,"ARGS: definitions.jsonl family-closure.json remaining-traces.jsonl recovery-traces.jsonl");
    const auto definitions=lines(argv[1]);const auto closure=read(argv[2]);need(definitions.size()==56 && allKeys().size()==56 && keys().size()==14);
    std::set<std::string> seen;
    for (const auto& row:definitions) {
        const auto key=field(row,"source_key").string();const auto& d=definition(key);need(seen.insert(key).second && d.exportedDefinition()==row && d.retainedContract()==field(row,"contract"),"COMPLETE56_FROZEN_CONTRACT_ROUNDTRIP");
        need(d.retainedSourceContext()==field(field(closure,"contexts"),field(row,"context_ref").string().c_str()),"COMPLETE56_CACHED_CONTEXT_ROUNDTRIP");
        need(d.contractSha256()==field(row,"contract_sha256").string() && d.sourceClosureSha256()=="377abfe77580ecb3d7a60ea2cede09253989eb651a9d341bab4bf58ad581154d");
        const auto choices=allowedChoices(d);need(field(choices,"default_choice").null() && field(choices,"source_clock").null());
        if (d.recipe()=="full_reconstruction") need(field(choices,"contacts").array().size()==150 && field(choices,"written_passes").array().size()==4 && field(choices,"target_count")==V::fromInteger(64));
        if (d.recipe()=="fixed_top_reduction") { need(!field(choices,"top_contacts").array().empty() && field(choices,"stages").array().size()==4);try { (void)allowedChoices(d,"C");throw std::logic_error("FIXED_TOP_DOMAIN_WIDENED"); } catch (const tasks::recipes::Error&) { ++refusals; } }
    }
    for (const auto& key:allKeys()) need(seen.count(key)==1);
    try { (void)definition("foreign/new/key");throw std::logic_error("FOREIGN_FACTORY"); } catch (const tasks::recipes::Error&) { ++refusals; }
    try { AdvancedRecipeWorkflow bad(definition(keys().front()));throw std::logic_error("REMAINING_OWNER_WIDENED"); } catch (const tasks::recipes::Error&) { ++refusals; }
    const auto goldens=lines(argv[3]);need(goldens.size()==42);std::set<std::string> strata;
    for (const auto& golden:goldens) {
        const auto& d=definition(field(golden,"source_key").string());AdvancedRecipeWorkflow t(d),other(d);
        need(t.learnerView()==field(golden,"initial_learner_view") && t.sourcePlayerView()==field(golden,"source_player_view"),"INITIAL_SOURCE_PLAYER_LEARNER_SPLIT");
        const auto& trace=field(golden,"trace").array();const auto action=field(trace.front(),"action").string();const auto owner=t.capture(action);const auto payload=field(trace.front(),"payload");
        unchanged(other,[&]{other.apply(owner,payload);});unchanged(t,[&]{act(t,"foreign_action");});unchanged(t,[&]{act(t,"finish");});
        for (int i=0;i<17;++i) {
            auto bad=owner;switch(i) {
                case 0:++bad.owner.instance;break;case 1:++bad.owner.pass;break;case 2:++bad.owner.revision;break;
                case 3:bad.owner.sourceKey="foreign";break;case 4:bad.owner.contractSha256=std::string(64,'0');break;
                case 5:bad.owner.sourceClosureSha256=std::string(64,'0');break;case 6:bad.owner.phase=tasks::recipes::Phase::Steps;break;
                case 7:bad.owner.step=bad.owner.step.value_or(0)+1;break;case 8:bad.owner.intent=static_cast<tasks::recipes::Intent>(999);break;
                case 9:bad.action="finish";break;case 10:bad.state="foreign";break;case 11:++bad.writtenPass;break;
                case 12:++bad.bar;break;case 13:++bad.registerIndex;break;case 14:++bad.harmony;break;
                case 15:++bad.texture;break;case 16:bad.recovery=true;break;
            } unchanged(t,[&]{t.apply(bad,payload);});
        }
        if (d.recipe()=="full_reconstruction") strata.insert("whole16bar64tone_reconstruction");else strata.insert("fixedtop_"+field(field(d.retainedContract(),"source_card"),"module").string());
        V topChoice;
        for (const auto& s:trace) {
            const auto a=field(s,"action").string();
            if (a=="set_top") topChoice=field(s,"payload");
            if (a=="choose_voicing") { const auto& p=field(s,"payload");const auto choices=voicings(d,topChoice,field(p,"harmony").string(),field(p,"stage").string(),1);need(choices.size()==1 && choices.front()==p,"PINNED_FINITE_VOICING_ENUMERATION"); }
            if (a=="begin_second_register") {
                auto nonuniform=field(s,"payload");auto& first=nonuniform.object().at("contacts").array().front();first.object().at("fret")=V::fromInteger(0);first.object().at("midi")=V::fromInteger(64);
                unchanged(t,[&]{act(t,a,nonuniform);});
            }
            if (a=="choose_additional") { auto bad=field(s,"payload");bad.object().at("harmony")=field(field(d.retainedContract(),"source_card"),"source_harmonies").array().front();unchanged(t,[&]{act(t,a,bad);}); }
            step(t,s);++actions;
            if (d.recipe()=="full_reconstruction" && !field(t.snapshot(),"source_reference_revealed").boolean()) need(!t.learnerView().find("source_reference"),"EARLY_HIDDEN_SOURCE_LEAK");
        }
        need(field(t.learnerView(),"state").string()=="completed");for (const auto& h:t.history()) need(!h.performanceObserved && !h.grantsCredit);
        const auto view=t.learnerView(),snapshot=t.snapshot();const auto stale=t.capture("cancel");act(t,"navigate");need(t.learnerView()==view && t.snapshot()==snapshot,"IDLE_NATIVE_FENCE_PRESERVES_SOURCE_HISTORY");unchanged(t,[&]{t.apply(stale,O{});});++rows;
    }
    need(rows==42 && actions==1971 && strata.size()==3,"CLOSED42_POSITIVE_PATHS");
    for (const auto& fixture:lines(argv[4])) {
        AdvancedRecipeWorkflow t(definition(field(fixture,"source_key").string()));
        for (const auto& s:field(fixture,"trace").array()) { step(t,s);++recoveries; }
        const auto name=field(fixture,"name").string();
        if (name=="unknown_written") need(field(t.learnerView(),"state").string()=="ready_written" && field(t.snapshot(),"source_reference_revealed").boolean() && field(t.learnerView(),"responses").object().empty(),"REACHABLE_NULLABLE_WRITTEN_RESTART_EXPOSURE_RETAINED");
        else need(field(t.learnerView(),"state").string()=="completed");
        if (name.find("fixedtop_debt")==0) need(!field(t.snapshot(),"reduction_required").boolean() && !field(t.snapshot(),"restart_after_reduction").boolean(),"REDUCTION_DEBT_DISCHARGED_ONLY_BY_REDUCTION");
    }
    need(recoveries==434,"CACHED_RECOVERY_STRATA");
    // Small necessary malformed/manual-unknown and physical-release guards.
    const auto fixed=std::find_if(goldens.begin(),goldens.end(),[](const V& g){return field(g,"recipe").string()=="fixed_top_reduction";});need(fixed!=goldens.end());
    const auto& d=definition(field(*fixed,"source_key").string());const auto trace=field(*fixed,"trace").array();AdvancedRecipeWorkflow unknown(d);
    for (const auto& s:trace) {
        const auto a=field(s,"action").string();
        if (a=="name_role") { auto p=field(s,"payload");p.object().at("role")=nullptr;act(unknown,a,p); }
        else if (a=="report") { auto p=field(s,"payload");unchanged(unknown,[&]{act(unknown,a,p);});p.object().at("diagnosis")="Synthetic unknown role diagnosis.";act(unknown,a,p);unchanged(unknown,[&]{act(unknown,"finish");});act(unknown,"diagnose","Diagnosed same-step retry.");need(field(unknown.learnerView(),"state").string()=="need_sing");break; }
        else act(unknown,a,field(s,"payload"));
    }
    AdvancedRecipeWorkflow audit(d);
    for (const auto& s:trace) {
        const auto a=field(s,"action").string();if (a=="audit") {
            auto p=field(s,"payload");p.object().at("answers").object().begin()->second=nullptr;unchanged(audit,[&]{act(audit,a,p);});p.object().at("diagnosis")="Unknown manual audit diagnosis.";act(audit,a,p);unchanged(audit,[&]{act(audit,"finish");});act(audit,"diagnose","Explicit audit retry.");need(field(audit.learnerView(),"state").string()=="audit");act(audit,a,field(s,"payload"));act(audit,"finish");break;
        }act(audit,a,field(s,"payload"));
    }
    AdvancedRecipeWorkflow release(d);
    for (const auto& s:trace) { if (field(s,"action").string()=="release") break;act(release,field(s,"action").string(),field(s,"payload")); }
    act(release,"navigate");unchanged(release,[&]{act(release,"release",O{{"learner_released",true}});});act(release,"reopen");
    unchanged(release,[&]{act(release,"release",O{{"learner_released",false}});});unchanged(release,[&]{act(release,"release",O{});});act(release,"release",O{{"learner_released",true}});need(field(release.learnerView(),"state").string()=="need_sing");
    std::cout<<"{\"outcome\":\"PASS\",\"definitions_roundtripped\":56,\"implemented_remaining_rows\":"<<rows<<",\"positive_model_actions\":"<<actions<<",\"recovery_model_actions\":"<<recoveries<<",\"assertions\":"<<assertions<<",\"refusals\":"<<refusals<<",\"source_system_strata\":3,\"synthetic_reports_observed\":false,\"runtime_admitted\":false,\"official_accepted\":false}\n";return 0;
} catch (const std::exception& e) { std::cerr<<e.what()<<"\n";return 1; } }
