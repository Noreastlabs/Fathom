#include "tasks/AdvancedRecipeTask.hpp"
#include <algorithm>
#include <fstream>
#include <functional>
#include <iostream>
#include <iterator>
#include <set>
using namespace fathom;using namespace fathom::tasks::advanced;
using V=json::Value;using O=V::Object;using A=V::Array;
namespace {
std::size_t checks{},refusals{},paths{},actions{};
void need(bool v,const char* message="SCHEMA_TEST") { ++checks;if (!v) throw std::runtime_error(message); }
const V& f(const V& v,const char* name) { const auto* p=v.find(name);need(p!=nullptr,"FIELD");return *p; }
std::vector<V> lines(const char* path) { std::ifstream stream(path);need(stream.good());std::vector<V> result;std::string line;while(std::getline(stream,line)) result.push_back(json::parse(line));return result; }
bool type(const V& value,const std::string& kind) {
    if (kind=="null") return value.null();if (kind=="string") return value.isString();if (kind=="boolean") return value.isBool();
    if (kind=="array") return value.isArray();if (kind=="object") return value.isObject();std::int64_t n{};return kind=="integer" && value.integer(n);
}
void validate(const V& schema,const V& payload) {
    need(schema.isObject() && !schema.find("default"),"NO_AUTOMATIC_REPORT_DEFAULT");
    if (const auto* c=schema.find("const")) {need(*c==payload,"SOURCE_PROTOCOL_CHOICE_BINDING");return;}
    const auto& types=f(schema,"type");bool typed=false;if(types.isString()) typed=type(payload,types.string());else for(const auto& kind:types.array()) typed=typed || type(payload,kind.string());need(typed,"PAYLOAD_SCHEMA_TYPE");
    if (const auto* choices=schema.find("enum")) need(std::find(choices->array().begin(),choices->array().end(),payload)!=choices->array().end(),"CHOICE_DOMAIN");
    if (payload.isObject() && schema.find("properties")) {
        const auto& properties=f(schema,"properties");need(!f(schema,"additionalProperties").boolean() && payload.object().size()==properties.object().size(),"EXACT_FORM_FIELDS");
        for(const auto& entry:properties.object()) validate(entry.second,f(payload,entry.first.c_str()));
    }
    if (payload.isArray() && schema.find("items")) {
        std::int64_t lo{},hi{};need(f(schema,"minItems").integer(lo) && f(schema,"maxItems").integer(hi));need(payload.array().size()>=static_cast<std::size_t>(lo) && payload.array().size()<=static_cast<std::size_t>(hi));
        for(const auto& item:payload.array()) validate(f(schema,"items"),item);
    }
    if (payload.isString()) { if(const auto* minimum=schema.find("minLength")) {std::int64_t n{};need(minimum->integer(n) && payload.string().size()>=static_cast<std::size_t>(n));} }
    std::int64_t number{};if(payload.integer(number)) {if(const auto* minimum=schema.find("minimum")){std::int64_t n{};need(minimum->integer(n) && number>=n);}if(const auto* maximum=schema.find("maximum")){std::int64_t n{};need(maximum->integer(n) && number<=n);} }
    if(const auto* prior=schema.find("must_equal_prior")) need(payload==*prior && f(schema,"reentry_required").boolean() && !schema.find("const"),"EXPLICIT_PRIOR_NAMING_REENTRY");
}
const V& descriptor(const V& list,const std::string& name) { const V* found=nullptr;for(const auto& d:list.array()) if(f(d,"action").string()==name) {need(found==nullptr);found=&d;}need(found!=nullptr,"MISSING_CURRENT_SOURCE_ACTION");return *found; }
template<class T,class F> void unchanged(T& task,F operation) {
    const auto before=task.learnerView();const auto size=task.history().size();try {operation();}catch(const std::exception&){++refusals;need(task.learnerView()==before && task.history().size()==size);return;}throw std::runtime_error("EXPECTED_REFUSAL");
}
void safeInstructions(const V& instructions) {need(f(instructions,"source_clock").null() && !f(instructions,"actual_performance_verified").boolean());need(!instructions.find("source_reference") && !instructions.find("bars") && !instructions.find("source_task") && !instructions.find("contract"));}
}
int main(int argc,char** argv) {try {
    need(argc==4,"ARGS: transfer-traces remaining-traces recovery-traces");
    for(const auto& fixture:lines(argv[1])) {
        AdvancedRecipeTask task(definition(f(fixture,"source_key").string()));safeInstructions(task.learnerInstructions());
        auto owner=task.capture(Action::SetPlan);const auto before=task.learnerView();need(task.fenceInactiveForNavigation() && task.learnerView()==before && task.history().empty());unchanged(task,[&]{task.apply(owner,f(f(fixture,"trace").array().front(),"payload"));});
        for(const auto& step:f(fixture,"trace").array()) {
            const auto name=f(step,"action").string();validate(f(descriptor(task.learnerActions(),name),"schema"),f(step,"payload"));
            if(f(task.learnerView(),"state").string()!="setup" && f(task.learnerView(),"state").string()!="completed") {const auto beforeView=task.learnerView();const auto size=task.history().size();need(!task.fenceInactiveForNavigation() && task.learnerView()==beforeView && task.history().size()==size);}
            task.apply(task.capture(transferAction(name)),f(step,"payload"));++actions;
        }++paths;
    }
    for(int file=2;file<4;++file) for(const auto& fixture:lines(argv[file])) {
        AdvancedRecipeWorkflow task(definition(f(fixture,"source_key").string()));safeInstructions(task.learnerInstructions());
        for(const auto& step:f(fixture,"trace").array()) {
            const auto name=f(step,"action").string();validate(f(descriptor(task.learnerActions(),name),"schema"),f(step,"payload"));
            if(name=="finish" && task.retainedDefinition().recipe()=="full_reconstruction") {
                auto retarget=task.capture("declare_scores");retarget.action="finish";unchanged(task,[&]{task.apply(retarget,O{});});
            }
            if(const auto* refuse=step.find("refuse");refuse && refuse->boolean()) unchanged(task,[&]{task.apply(task.capture(name),f(step,"payload"));});else task.apply(task.capture(name),f(step,"payload"));++actions;
        }++paths;
    }
    need(paths==59 && actions==2643,"ALL56_PLUS3_RECOVERY_SCHEMA_PATHS");
    std::cout<<"{\"outcome\":\"PASS\",\"source_rows\":56,\"paths\":"<<paths<<",\"current_action_schema_payloads\":"<<actions<<",\"assertions\":"<<checks<<",\"refusals\":"<<refusals<<",\"exact_action_retarget_refused\":true,\"manual_defaults\":0,\"source_player_used_for_learner_schema\":false}\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;} }
