#include "tasks/AdvancedRecipeTask.hpp"
#include <fstream>
#include <functional>
#include <iostream>
#include <iterator>
#include <map>
#include <set>
#include <type_traits>

using namespace fathom;
using namespace fathom::tasks::advanced;
using V=json::Value; using O=V::Object; using A=V::Array;
static_assert(!std::is_copy_constructible_v<AdvancedRecipeTask> && !std::is_move_constructible_v<AdvancedRecipeTask>);
static_assert(!std::is_constructible_v<Definition,const char*,const char*,const char*>);
namespace {
std::size_t checks{},refusals{},rows{},actions{};
void need(bool b,const char* msg="TEST") { ++checks; if (!b) throw std::runtime_error(msg); }
const V& field(const V& v,const char* n) { const auto* p=v.find(n); need(p!=nullptr,"FIXTURE_FIELD"); return *p; }
Action action(const std::string& name) {
    static const std::map<std::string,Action> values{{"set_plan",Action::SetPlan},{"begin",Action::Begin},{"heard",Action::Heard},
      {"sung_name",Action::SungName},{"choose_arrangements",Action::ChooseArrangements},{"cannot_respond",Action::CannotRespond},
      {"setup_target",Action::SetupTarget},{"attack",Action::Attack},{"release",Action::Release},{"reveal",Action::Reveal},
      {"report",Action::Report},{"next_set",Action::NextSet},{"retry",Action::Retry},{"finish",Action::Finish},
      {"cancel",Action::Cancel},{"navigate",Action::Navigate},{"reopen",Action::Reopen}};
    const auto i=values.find(name); need(i!=values.end(),"ACTION_FIXTURE"); return i->second;
}
void act(AdvancedRecipeTask& t,Action a,const V& p=O{}) { t.apply(t.capture(a),p); }
void unchanged(AdvancedRecipeTask& t,const std::function<void()>& f) {
    const auto before=t.learnerView();const auto token=t.capture(Action::Cancel);const auto size=t.history().size();
    try { f(); } catch (const std::exception&) {
        ++refusals;const auto after=t.capture(Action::Cancel);
        need(t.learnerView()==before && t.history().size()==size && after.owner.pass==token.owner.pass &&
             after.owner.revision==token.owner.revision && after.state==token.state && after.cycle==token.cycle && after.stringSet==token.stringSet,"REFUSAL_MUTATED_STATE"); return;
    }
    throw std::runtime_error("EXPECTED_REFUSAL");
}
void applyTrace(AdvancedRecipeTask& t,const V& step,bool compare=true) {
    act(t,action(field(step,"action").string()),field(step,"payload"));
    if (compare) need(t.learnerView()==field(step,"learner_view_after"),"PINNED_MODEL_LEARNER_VIEW_PARITY");
}
} // namespace

int main(int argc,char** argv) { try {
    need(argc==4,"ARGS: definitions.jsonl native-model-traces.jsonl family-closure.json");need(keys().size()==14);
    std::ifstream closureInput(argv[3]);need(closureInput.good());
    const auto closure=json::parse(std::string(std::istreambuf_iterator<char>(closureInput),{}));
    std::ifstream definitions(argv[1]);need(definitions.good());std::string line;std::set<std::string> seen;
    while (std::getline(definitions,line)) {
        const auto row=json::parse(line);if (field(row,"recipe").string()!="chord_tone_transfer") continue;
        const auto key=field(row,"source_key").string();const auto& d=definition(key);need(seen.insert(key).second);
        need(d.exportedDefinition()==row && d.retainedContract()==field(row,"contract"),"FULL_FROZEN_DEFINITION_CONTRACT_PARITY");
        need(d.retainedSourceContext()==field(field(closure,"contexts"),field(row,"context_ref").string().c_str()),"FULL_FROZEN_SOURCE_CONTEXT_PARITY");
        need(d.contractSha256()==field(row,"contract_sha256").string() && d.sourceClosureSha256()=="377abfe77580ecb3d7a60ea2cede09253989eb651a9d341bab4bf58ad581154d","CLOSED_SOURCE_HASH");
        const auto choices=allowedChoices(d);need(field(choices,"contacts").array().size()==150 && field(choices,"default_choice").null() && field(choices,"source_clock").null());
        for (const auto& pitch:field(choices,"pitch_names").array()) need(!field(allowedChoices(d,pitch.string()),"contacts").array().empty(),"ALL_KNOWN_SPELLINGS_HAVE_CONTACTS");
        ++rows;
    }
    need(rows==14);for (const auto& key:keys()) need(seen.count(key)==1);
    try { (void)definition("foreign/new/key");throw std::logic_error("FACTORY_WIDENED"); } catch (const tasks::recipes::Error&) { ++refusals; }
    std::ifstream traces(argv[2]);need(traces.good());std::vector<V> goldens;
    while (std::getline(traces,line)) goldens.push_back(json::parse(line));need(goldens.size()==14);
    std::set<std::string> classes;
    for (const auto& golden:goldens) {
        const auto key=field(golden,"source_key").string();const auto& d=definition(key);AdvancedRecipeTask t(d),other(d);
        need(t.learnerView()==field(golden,"initial_learner_view") && t.sourcePlayerView()==field(golden,"source_player_view"),"INITIAL_VISIBILITY_PARITY");
        classes.insert(field(t.learnerView(),"source_visibility").string());need(!t.learnerView().find("reference_pitch"));
        validatePlan(field(golden,"plan"));validateArrangements(field(golden,"arrangements"));
        auto capture=t.capture(Action::SetPlan);
        unchanged(other,[&]{other.apply(capture,field(golden,"plan"));});
        for (int i=0;i<13;++i) {
            auto bad=capture;
            switch(i) {
                case 0:++bad.owner.instance;break;case 1:++bad.owner.pass;break;case 2:++bad.owner.revision;break;
                case 3:bad.owner.sourceKey="foreign";break;case 4:bad.owner.contractSha256=std::string(64,'0');break;
                case 5:bad.owner.sourceClosureSha256=std::string(64,'0');break;case 6:bad.owner.phase=tasks::recipes::Phase::Steps;break;
                case 7:bad.owner.step=99;break;case 8:bad.owner.intent=static_cast<tasks::recipes::Intent>(999);break;
                case 9:bad.action=static_cast<Action>(999);break;case 10:bad.state=State::Ready;break;
                case 11:bad.stringSet=1;break;case 12:bad.cycle=1;break;
            }
            unchanged(t,[&]{t.apply(bad,field(golden,"plan"));});
        }
        unchanged(t,[&]{act(t,Action::Finish);});unchanged(t,[&]{act(t,Action::Reveal);});
        for (const auto& step:field(golden,"trace").array()) {
            const auto a=action(field(step,"action").string());const auto owner=t.capture(a);applyTrace(t,step);++actions;
            unchanged(t,[&]{t.apply(owner,field(step,"payload"));});
            need(!field(t.learnerView(),"blind_assessment_claim").boolean());
        }
        need(field(t.learnerView(),"state").string()=="completed" && t.priorityGuidance().has_value());
        for (const auto& e:t.history()) need(!e.performanceObserved && !e.grantsCredit,"NO_OBSERVED_PERFORMANCE_CREDIT");
        const auto before=t.learnerView();const auto history=t.history().size();const auto idle=t.capture(Action::SetPlan);
        act(t,Action::Navigate);need(t.learnerView()==before && t.history().size()==history,"IDLE_NAVIGATION_PRESERVES_PHASE_HISTORY");
        unchanged(t,[&]{t.apply(idle,field(golden,"plan"));});
    }
    need(classes.size()==2 && actions==238,"VISIBLE_AND_SOURCE_REVIEWED_OCCLUDED_STRATA");
    const auto& golden=goldens.front();const auto& d=definition(field(golden,"source_key").string());const auto trace=field(golden,"trace").array();
    // Every source phase at the first key: stop/reopen/release never skips or
    // silently exposes a reference; repeated refused release leaves owner intact.
    for (std::size_t prefix=0;prefix<=trace.size();++prefix) {
        AdvancedRecipeTask t(d);for (std::size_t i=0;i<prefix;++i) applyTrace(t,trace[i]);
        const auto size=t.history().size();const auto revealed=field(t.learnerView(),"previously_revealed");
        act(t,Action::Cancel);need(field(t.learnerView(),"state").string()=="cancelled");
        unchanged(t,[&]{act(t,Action::Release,true);});act(t,Action::Reopen);
        unchanged(t,[&]{act(t,Action::Release,false);});unchanged(t,[&]{act(t,Action::Release,O{});});
        unchanged(t,[&]{act(t,Action::Finish);});act(t,Action::Release,true);
        need(t.history().size()==size+3 && field(t.learnerView(),"previously_revealed")==revealed,"CANCEL_RECOVERY_HISTORY_EXPOSURE_RETAINED");
    }
    for (const auto& failure:std::vector<std::string>{"unknown_name","wrong_name","unknown_hearing","uncertain_duty","multiple_attacks"}) {
        AdvancedRecipeTask t(d);
        for (const auto& original:trace) {
            auto step=original;const auto name=field(step,"action").string();
            if (name=="heard" && failure=="unknown_hearing") step.object().at("payload").object().at("heard_chord_and_role")="uncertain";
            if (name=="sung_name" && failure=="unknown_name") step.object().at("payload").object().at("pitch_name")=nullptr;
            if (name=="sung_name" && failure=="wrong_name") step.object().at("payload").object().at("pitch_name")="F";
            if (name=="report") {
                auto payload=field(step,"payload");
                if (failure=="unknown_name") payload.object().at("named_pitch")=nullptr;
                if (failure=="wrong_name") payload.object().at("named_pitch")="F";
                if (failure=="uncertain_duty") payload.object().at("common").object().at("no_searching")="uncertain";
                if (failure=="multiple_attacks") payload.object().at("attack_count")=V::fromInteger(2);
                unchanged(t,[&]{act(t,Action::Report,payload);});
                payload.object().at("diagnosis")="Explicit synthetic failed/unknown response diagnosis.";act(t,Action::Report,payload);
                need(field(t.learnerView(),"state").string()=="needs_retry");unchanged(t,[&]{act(t,Action::NextSet);});unchanged(t,[&]{act(t,Action::Finish);});
                unchanged(t,[&]{act(t,Action::Retry,"");});const auto size=t.history().size();act(t,Action::Retry,"Diagnosed same-key retry.");
                need(field(t.learnerView(),"state").string()=="ready" && !t.learnerView().find("reference_pitch") &&
                     field(t.learnerView(),"previously_revealed").boolean() && t.history().size()==size+1,"FAILED_RETRY_HISTORY_NO_FRESH_BLIND_CLAIM");break;
            }
            applyTrace(t,step,false);
        }
    }
    AdvancedRecipeTask malformed(d);
    auto plan=field(golden,"plan");plan.object().at("cue_provider").object().at("reference")="\xc2\xa0";
    unchanged(malformed,[&]{act(malformed,Action::SetPlan,plan);});
    act(malformed,Action::SetPlan,field(golden,"plan"));
    auto begin=field(trace[1],"payload");begin.object().at("role")="foreign degree";unchanged(malformed,[&]{act(malformed,Action::Begin,begin);});
    for (std::size_t i=1;i<4;++i) applyTrace(malformed,trace[i]);
    auto arrangements=field(golden,"arrangements");arrangements.object().at("string_set_2")=field(arrangements,"string_set_1");
    unchanged(malformed,[&]{act(malformed,Action::ChooseArrangements,arrangements);});
    arrangements=field(golden,"arrangements");arrangements.object().at("string_set_1").object().at("target").object().at("fret")=true;
    unchanged(malformed,[&]{act(malformed,Action::ChooseArrangements,arrangements);});
    act(malformed,Action::Navigate);unchanged(malformed,[&]{act(malformed,Action::Release,true);});act(malformed,Action::Reopen);
    unchanged(malformed,[&]{act(malformed,Action::Begin);});act(malformed,Action::Release,true);need(field(malformed.learnerView(),"state").string()=="ready");
    std::cout<<"{\"outcome\":\"PASS\",\"rows\":"<<rows<<",\"pinned_model_actions\":"<<actions<<",\"assertions\":"<<checks
      <<",\"refusals\":"<<refusals<<",\"source_visibility_strata\":2,\"observed_performance\":false,\"runtime_admitted\":false,\"official_accepted\":false}\n";
    return 0;
} catch(const std::exception& error) { std::cerr<<error.what()<<"\n";return 1; } }
