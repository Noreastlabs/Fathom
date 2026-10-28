#include "tasks/RecipeTask.hpp"
#include "content/Canonical.hpp"
#include <chrono>
#include "GeneratedLevel068Family.hpp"
#include "GeneratedLevel068Context.hpp"
#include <algorithm>
#include <atomic>
#include <cstdlib>
#include <limits>
#include <map>
#include <type_traits>
#include <utility>

namespace fathom::tasks::recipes {
Error::Error(std::string value) : std::runtime_error(value), code(std::move(value)) {}
namespace {
using V = json::Value;
using O = V::Object;
using A = V::Array;
void need(bool condition, const char* code) { if (!condition) throw Error(code); }
const V& field(const V& object, const char* name) {
    const auto* value = object.find(name); need(value != nullptr, "FIELDS"); return *value;
}
std::string text(const V& object, const char* name) {
    const auto& value = field(object, name); need(value.isString(), "STRING_TYPE"); return value.string();
}
std::int64_t integer(const V& value) {
    std::int64_t out{}; need(value.integer(out), "INTEGER_TYPE"); return out;
}
void fields(const V& object, std::initializer_list<const char*> names) {
    need(object.isObject() && object.object().size() == names.size(), "EXACT_FIELDS");
    for (const auto* name : names) need(object.find(name) != nullptr, "EXACT_FIELDS");
}
void validJson(const V& value) { (void)json::parse(json::stringify(value)); }
bool hash(const std::string& s) {
    return s.size() == 64 && std::all_of(s.begin(), s.end(), [](char c) {
        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
    });
}
bool noFields(const V& value) { return value.isObject() && value.object().empty(); }
V contact(int string, int fret) { return O{{"string", V::fromInteger(string)}, {"fret", V::fromInteger(fret)}}; }
struct Position { int string, fret, midi; };
Position position(const V& value) {
    fields(value, {"string", "fret"});
    const auto s = integer(field(value, "string")), f = integer(field(value, "fret"));
    need(s >= 1 && s <= 6 && f >= 0 && f <= 24, "CONTACT_RANGE");
    static constexpr int tuning[] = {0, 64, 59, 55, 50, 45, 40};
    return {static_cast<int>(s), static_cast<int>(f), tuning[s] + static_cast<int>(f)};
}
int pc(const std::string& note) {
    static const std::map<std::string, int> values{{"A",9},{"B",11},{"C",0},{"D",2},{"E",4},{"F",5},{"G",7},{"G#",8}};
    const auto i = values.find(note); need(i != values.end(), "PITCH_SPELLING"); return i->second;
}
A menu(const std::string& note) {
    A out; const int pitch = pc(note);
    for (int s = 1; s <= 6; ++s) for (int f = 0; f <= 24; ++f)
        if (position(contact(s, f)).midi % 12 == pitch) out.push_back(contact(s, f));
    return out;
}
A nearest(const V& origin, const std::string& note) {
    const auto source = position(origin); const auto options = menu(note); A out;
    int minimum = 1000;
    for (const auto& value : options) minimum = std::min(minimum, std::abs(position(value).midi - source.midi));
    for (const auto& value : options) if (std::abs(position(value).midi - source.midi) == minimum) out.push_back(value);
    return out;
}
// Python str.strip/len semantics used by the frozen remainder-plan validator.
bool whitespace(unsigned cp) {
    return (cp >= 9 && cp <= 13) || (cp >= 0x1c && cp <= 0x20) || cp == 0x85 || cp == 0xa0 ||
           cp == 0x1680 || (cp >= 0x2000 && cp <= 0x200a) || cp == 0x2028 || cp == 0x2029 ||
           cp == 0x202f || cp == 0x205f || cp == 0x3000;
}
void remainder(const std::string& value) {
    std::vector<unsigned> points;
    for (std::size_t i = 0; i < value.size();) {
        const auto c = static_cast<unsigned char>(value[i++]); unsigned cp = c; int n = 0;
        if (c >= 0xc0 && c < 0xe0) { cp = c & 31; n = 1; }
        else if (c >= 0xe0 && c < 0xf0) { cp = c & 15; n = 2; }
        else if (c >= 0xf0) { cp = c & 7; n = 3; }
        while (n--) { need(i < value.size(), "PLAN_UTF8"); cp = (cp << 6) | (static_cast<unsigned char>(value[i++]) & 63); }
        points.push_back(cp);
    }
    std::size_t first = 0, last = points.size();
    while (first < last && whitespace(points[first])) ++first;
    while (last > first && whitespace(points[last - 1])) --last;
    need(last > first && last - first <= 500, "EXPLICIT_REMAINDER_PLAN");
}
std::uint64_t nextInstance() {
    static std::atomic<std::uint64_t> next{1}; auto value = next.load();
    do { need(value != std::numeric_limits<std::uint64_t>::max(), "INSTANCE_EXHAUSTED"); }
    while (!next.compare_exchange_weak(value, value + 1));
    return value;
}
void intentValid(Intent kind) {
    switch (kind) {
        case Intent::Choose: case Intent::Report: case Intent::Retry: case Intent::Stop:
        case Intent::Navigate: case Intent::Release: case Intent::Again: case Intent::Reopen: return;
    }
    throw Error("INTENT_KIND");
}
V diagnostic(const char* code, const V& reported, const std::optional<V>& expected = std::nullopt) {
    O out{{"code", code}, {"reported", reported}, {"observed_failure", false}};
    if (expected) out.emplace("expected", *expected);
    return out;
}
} // namespace

Definition::Definition(const char* row, const char* reports, const char* bindings, const char* closure)
    : closureSha256_(closure), exported_(json::parse(row)), reportBindings_(json::parse(bindings)) {
    sourceKey_ = text(exported_, "source_key"); sourceIdentity_ = text(exported_, "source_identity");
    contractSha256_ = text(exported_, "contract_sha256"); contract_ = field(exported_, "contract");
    need(text(exported_, "schema") == "fathom.compiled-level068-definition.1" &&
         sourceKey_ == "exercise-completeness-r01/" + sourceIdentity_ &&
         text(contract_, "package_key") == sourceKey_ && text(contract_, "source_identity") == sourceIdentity_ &&
         hash(contractSha256_) && hash(closureSha256_) && hash(text(exported_, "record_sha256")), "TRUSTED_DEFINITION");
    need(closureSha256_ == recipe_generated::contextClosureSha256, "CONTEXT_CLOSURE");
    const auto contexts = json::parse(recipe_generated::contexts);
    const auto* context = contexts.find(text(exported_, "context_ref"));
    need(context != nullptr, "CONTEXT_REFERENCE"); context_ = *context;
    const auto kind = text(exported_, "recipe");
    need(text(context_, "recipe") == kind && field(context_, "context_tasks").isArray(), "CONTEXT_RECIPE");
    if (kind == "call_answer") need(field(context_, "source_rules") == field(contract_, "source_rules"), "CONTEXT_RULES");
    else for (const char* rule : {"source_rule", "source_safety", "source_target_naming_rule"})
        need(field(context_, rule) == field(contract_, rule), "CONTEXT_RULES");
    need(kind == "call_answer" || kind == "recovery_pair", "RECIPE_SCOPE");
    recipe_ = kind == "call_answer" ? Recipe::CallAnswer : Recipe::RecoveryPair;
    need(field(contract_, "numeric_clock").null() && field(contract_, "fixed_bpm").null() &&
         field(contract_, "grants_credit") == V(false) && field(contract_, "performance_observed") == V(false) &&
         field(contract_, "runtime_admitted") == V(false), "SOURCE_BOUNDARY");
    const auto parsed = json::parse(reports); need(parsed.isArray(), "REPORT_TABLE"); reports_ = parsed.array();
    const auto& steps = field(contract_, "steps");
    need(steps.isArray() && steps.array().size() == reports_.size() &&
         reports_.size() == (recipe_ == Recipe::CallAnswer ? 6u : 5u) && reportBindings_.isArray(), "REPORT_STEPS");
    for (std::size_t i = 0; i < reports_.size(); ++i) {
        need(reports_[i].isObject() && integer(field(reports_[i], "step")) == static_cast<std::int64_t>(i + 1) &&
             text(reports_[i], "response") == "acknowledged", "REPORT_STEP_SCHEMA");
    }
}

const Definition& definition(const std::string& key) {
    static const std::map<std::string, Definition> definitions = [] {
        std::map<std::string, Definition> out;
        for (const auto& raw : recipe_generated::rows) {
            Definition d(raw.definition, raw.reports, raw.reportBindings, raw.sourceClosureSha256);
            need(d.sourceKey() == raw.key && out.emplace(raw.key, std::move(d)).second, "COMPILED_KEY_CLOSURE");
        }
        need(out.size() == 17, "COMPILED_FAMILY_SIZE"); return out;
    }();
    const auto found = definitions.find(key); need(found != definitions.end(), "COMPILED_RECIPE_SCOPE"); return found->second;
}
const std::vector<std::string>& keys() {
    static const std::vector<std::string> out = [] {
        std::vector<std::string> values;
        for (const auto& raw : recipe_generated::rows) { (void)definition(raw.key); values.emplace_back(raw.key); }
        return values;
    }();
    return out;
}

json::Value allowedChoices(const Definition& d, std::optional<V> origin) {
    O out{{"package_key", d.sourceKey()}, {"contract_sha256", d.contractSha256()},
          {"start_strokes", A{"D", "U"}}, {"default_choice", nullptr}};
    if (d.recipe() == Recipe::CallAnswer) need(!origin, "CALL_ANSWER_HAS_PRINTED_CONTACTS");
    else {
        out.emplace("source_contacts", field(d.retainedContract(), "source_contact_menu"));
        out.emplace("rest_of_bar_plan", O{{"type","string"},{"nonblank",true},{"max_characters",V::fromInteger(500)},{"generated_notes",false}});
        if (origin) {
            validJson(*origin); const auto pos = position(*origin);
            const auto canonical = contact(pos.string, pos.fret);
            const auto& origins = field(d.retainedContract(), "source_contact_menu").array();
            need(std::find(origins.begin(), origins.end(), canonical) != origins.end(), "ORIGIN_PITCH_MENU");
            const auto& events = field(d.retainedContract(), "source_pitch_events").array();
            out.emplace("nearest_target_contacts", nearest(canonical, text(events.at(1), "printed_note")));
        }
    }
    return out;
}

json::Value select(const Definition& d, const V& request) {
    validJson(request);
    if (d.recipe() == Recipe::CallAnswer) fields(request, {"package_key", "contract_sha256", "start_stroke"});
    else fields(request, {"package_key", "contract_sha256", "start_stroke", "source_contact", "target_contact", "rest_of_bar_plan"});
    need(text(request, "package_key") == d.sourceKey() && text(request, "contract_sha256") == d.contractSha256(), "SELECTION_IDENTITY_HASH");
    const auto start = text(request, "start_stroke"); need(start == "D" || start == "U", "START_STROKE");
    if (d.recipe() == Recipe::CallAnswer) {
        A contacts = field(d.retainedContract(), "ordered_contacts").array(); need(contacts.size() == 16, "PRINTED_CONTACTS");
        for (std::size_t i = 0; i < contacts.size(); ++i) {
            contacts[i].object().emplace("selected_pick", ((i % 2 == 0) == (start == "D")) ? "D" : "U");
            contacts[i].object().emplace("selected_pass_order", V::fromInteger(static_cast<std::int64_t>(i + 1)));
        }
        const auto& steps = field(d.retainedContract(), "steps").array();
        return O{{"paired",contacts},{"variation_call",A(contacts.begin(),contacts.begin()+8)},
                 {"silent_gap",field(steps.at(3),"gap")},{"variation_answer",A(contacts.begin()+8,contacts.end())},
                 {"printed_contacts",V::fromInteger(16)},{"replay_contacts",V::fromInteger(16)},
                 {"performance_observed",false},{"grants_credit",false}};
    }
    const auto source = position(field(request, "source_contact")), target = position(field(request, "target_contact"));
    const auto origin = contact(source.string, source.fret), destination = contact(target.string, target.fret);
    const auto choices = allowedChoices(d, origin);
    const auto& targets = field(choices, "nearest_target_contacts").array();
    need(std::find(targets.begin(), targets.end(), destination) != targets.end(), "NEAREST_NAMED_TARGET");
    const auto plan = text(request, "rest_of_bar_plan"); remainder(plan);
    const auto& events = field(d.retainedContract(), "source_pitch_events").array(); A selected;
    for (std::size_t i = 0; i < 2; ++i) {
        const auto p = i == 0 ? source : target;
        selected.emplace_back(O{{"source_event_order",V::fromInteger(static_cast<std::int64_t>(i+1))},
            {"required_source_pitch",field(events.at(i),"printed_note")},{"kind","chosen_contact_realization"},
            {"string",V::fromInteger(p.string)},{"fret",V::fromInteger(p.fret)},{"midi",V::fromInteger(p.midi)},
            {"selected_pick",((i%2==0)==(start=="D"))?"D":"U"},{"onset_q",nullptr},{"duration_q",nullptr},
            {"provenance","explicit performer choice; not printed TAB position or observed playing"}});
    }
    return O{{"origin",selected.at(0)},{"target",selected.at(1)},{"chosen_pair",selected},
             {"target_pitch_distance_semitones",V::fromInteger(std::abs(target.midi-source.midi))},
             {"rest_of_bar_plan",plan},{"remainder_notes_or_attacks_generated",false},
             {"performance_observed",false},{"grants_credit",false}};
}

void requireCurrentToken(const Token& a, const Token& b) {
    intentValid(a.intent);
    need(a.instance==b.instance && a.pass==b.pass && a.revision==b.revision && a.sourceKey==b.sourceKey &&
         a.contractSha256==b.contractSha256 && a.sourceClosureSha256==b.sourceClosureSha256 &&
         a.phase==b.phase && a.step==b.step && a.intent==b.intent, "FOREIGN_OR_STALE_INTENT");
}
std::vector<std::string> validateManualReport(const V& actual, const V& expected) {
    validJson(actual);
    need(actual.isObject() && expected.isObject() && actual.object().size()==expected.object().size(), "RESPONSE_FIELDS");
    std::vector<std::string> negative;
    for (const auto& entry : expected.object()) {
        const auto* value = actual.find(entry.first);
        need(value && value->data.index()==entry.second.data.index(), "RESPONSE_VALUE_TYPE");
        if (entry.second.isBool()) {
            need(entry.second.boolean(), "POSITIVE_REPORT_CONTRACT");
            if (!value->boolean()) negative.push_back(entry.first);
        } else {
            if (entry.second.isNumber()) (void)integer(*value);
            need(*value==entry.second, "EXACT_RESPONSE_VALUE");
        }
    }
    return negative;
}

RecipeTask::RecipeTask(const Definition& value) : definition_(value), instance_(nextInstance()) {}
View RecipeTask::viewImpl(const State& s) { return {s.phase,s.outcome,s.pending,s.step,s.phase==Phase::Release,false,false}; }
View RecipeTask::view() const { std::lock_guard<std::mutex> lock(mutex_); return viewImpl(state_); }
std::uint64_t RecipeTask::pass() const { std::lock_guard<std::mutex> lock(mutex_); return state_.pass; }
std::uint64_t RecipeTask::revision() const { std::lock_guard<std::mutex> lock(mutex_); return state_.revision; }
Token RecipeTask::captureImpl(Intent kind) const {
    intentValid(kind); return {instance_,state_.pass,state_.revision,definition_.sourceKey(),definition_.contractSha256(),
                             definition_.sourceClosureSha256(),state_.phase,state_.step,kind};
}
Token RecipeTask::capture(Intent kind) const { std::lock_guard<std::mutex> lock(mutex_); return captureImpl(kind); }
V RecipeTask::expectedReportImpl() const {
    need(state_.phase==Phase::Steps && state_.step && state_.request, "NO_CURRENT_REPORT");
    auto report = definition_.reports().at(*state_.step-1);
    for (const auto& binding : definition_.reportBindings().array()) {
        if (integer(field(binding,"step"))==static_cast<std::int64_t>(*state_.step))
            report.object().at(text(binding,"report_field")) = field(*state_.request, text(binding,"request_field").c_str());
    }
    return report;
}
V RecipeTask::expectedReport() const { std::lock_guard<std::mutex> lock(mutex_); return expectedReportImpl(); }
std::optional<V> RecipeTask::selectedPlan() const { std::lock_guard<std::mutex> lock(mutex_); return state_.plan; }
std::optional<V> RecipeTask::selectedRequest() const { std::lock_guard<std::mutex> lock(mutex_); return state_.request; }
std::optional<V> RecipeTask::diagnosis() const { std::lock_guard<std::mutex> lock(mutex_); return state_.diagnosis; }
std::vector<HistoryEvent> RecipeTask::history() const { std::lock_guard<std::mutex> lock(mutex_); return history_; }
std::optional<V> RecipeTask::currentStep() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (state_.phase!=Phase::Steps || !state_.step || !state_.plan) return std::nullopt;
    auto step=field(definition_.retainedContract(),"steps").array().at(*state_.step-1);
    if (const auto* source=step.find("contacts_from_selection"))
        step.object().emplace("selected_contacts",field(*state_.plan,source->string().c_str()));
    if (const auto* source=step.find("contact_from_selection"))
        step.object().emplace("chosen_contact",field(*state_.plan,source->string().c_str()));
    if (definition_.recipe()==Recipe::RecoveryPair && *state_.step==4)
        step.object().emplace("rest_of_bar_plan",field(*state_.plan,"rest_of_bar_plan"));
    return step;
}
bool RecipeTask::fenceInactiveForNavigation() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (state_.phase != Phase::Select && state_.phase != Phase::Closed) return false;
    need(state_.pass != std::numeric_limits<std::uint64_t>::max() &&
         state_.revision != std::numeric_limits<std::uint64_t>::max(), "NAVIGATION_FENCE_EXHAUSTED");
    State next = state_; ++next.pass; ++next.revision;
    HistoryEvent event{captureImpl(Intent::Navigate), O{}, viewImpl(state_), viewImpl(next), next.diagnosis, false, false};
    history_.push_back(std::move(event));
    state_ = std::move(next); return true;
}
void RecipeTask::enterRelease(State& s, Outcome outcome, std::optional<V> diagnosis) {
    s.phase=Phase::Release; s.pending=outcome; s.outcome=Outcome::None; s.step.reset(); s.diagnosis=std::move(diagnosis);
}
void RecipeTask::apply(const Token& token, const V& payload) {
    std::lock_guard<std::mutex> lock(mutex_);
    requireCurrentToken(token,captureImpl(token.intent)); validJson(payload);
    need(state_.revision!=std::numeric_limits<std::uint64_t>::max(),"REVISION_EXHAUSTED");
    State next=state_;
    switch (token.intent) {
        case Intent::Choose:
            need(next.phase==Phase::Select,"CHOICE_PHASE");
            next.plan=select(definition_,payload); next.request=payload; next.phase=Phase::Steps; next.step=1; break;
        case Intent::Report: case Intent::Retry: case Intent::Stop: {
            need(next.phase==Phase::Steps && next.step,"RESPONSE_PHASE");
            const auto response=text(payload,"response");
            need(response=="acknowledged" || response=="needs_retry" || response=="stopped","RESPONSE_VALUE");
            need(token.intent==Intent::Report || (token.intent==Intent::Retry && response=="needs_retry") ||
                 (token.intent==Intent::Stop && response=="stopped"),"RESPONSE_INTENT");
            need(integer(field(payload,"step"))==static_cast<std::int64_t>(*next.step),"RESPONSE_ORDER");
            if (response!="acknowledged") {
                fields(payload,{"step","response"});
                enterRelease(next,response=="stopped"?Outcome::Cancelled:Outcome::RetryRequested,
                             diagnostic(response=="stopped"?"MANUAL_STOPPED":"MANUAL_NEEDS_RETRY",payload));
            } else {
                const auto expected=expectedReportImpl(); const auto negative=validateManualReport(payload,expected);
                if (!negative.empty()) {
                    auto d=diagnostic("FALSE_MANUAL_REPORT",payload,expected); A names;
                    for (const auto& name:negative) names.emplace_back(name);
                    d.object().emplace("false_boolean_fields",names); enterRelease(next,Outcome::RetryRequested,d);
                } else if (*next.step==definition_.reports().size()) enterRelease(next,Outcome::UserReportedStepsFinished,std::nullopt);
                else ++*next.step;
            }
            break;
        }
        case Intent::Navigate:
            need((next.phase==Phase::Select || next.phase==Phase::Steps) && noFields(payload),"NAVIGATION_PHASE_FIELDS");
            enterRelease(next,Outcome::Cancelled,diagnostic("NAVIGATION",payload)); break;
        case Intent::Release:
            need(next.phase==Phase::Release && payload==V(O{{"released_completely_reported",true}}),"EXPLICIT_RELEASE_REQUIRED");
            next.phase=Phase::Closed; next.outcome=next.pending; next.pending=Outcome::None; break;
        case Intent::Again: case Intent::Reopen:
            need(next.phase==Phase::Closed && noFields(payload),"FRESH_PASS_REQUIRES_RELEASE");
            need(next.pass!=std::numeric_limits<std::uint64_t>::max(),"PASS_EXHAUSTED");
            ++next.pass; next.phase=Phase::Select; next.outcome=next.pending=Outcome::None;
            next.step.reset(); next.request.reset(); next.plan.reset(); next.diagnosis.reset(); break;
    }
    ++next.revision;
    HistoryEvent event{token,payload,viewImpl(state_),viewImpl(next),next.diagnosis,false,false};
    history_.push_back(std::move(event)); // allocation happens before committing state
    static_assert(std::is_nothrow_move_assignable_v<State>);
    state_=std::move(next);
}

namespace {
json::Limits draftLimits(){json::Limits l;l.bytes=64*1024*1024;l.depth=96;l.stringBytes=8*1024*1024;l.values=2000000;return l;}
V draftNumber(std::uint64_t n){need(n<=static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()),"DRAFT_COUNTER_RANGE");return V::fromInteger(static_cast<std::int64_t>(n));}
V draftView(const View& v){return O{{"phase",V::fromInteger(static_cast<int>(v.phase))},{"outcome",V::fromInteger(static_cast<int>(v.outcome))},{"pending",V::fromInteger(static_cast<int>(v.pendingOutcome))},{"step",v.step?draftNumber(*v.step):V()},{"release",v.needsManualRelease},{"observed",false},{"credit",false}};}
std::string draftEnvelope(const V& body){return json::stringify(O{{"body",body},{"sha256",content::sha256(json::stringify(body))}});}
}
V RecipeTask::continuationBody() const {
    need(history_.size()<=100000,"DRAFT_COMMAND_LIMIT"); A journal;
    for(const auto& e:history_){
        // Navigation from Select/Closed through the dedicated idle fence is
        // distinct from Navigate's real release transition.
        const bool fence=e.token.intent==Intent::Navigate&&(e.before.phase==Phase::Select||e.before.phase==Phase::Closed)&&e.after.phase==e.before.phase;
        journal.emplace_back(O{{"fence",fence},{"intent",V::fromInteger(static_cast<int>(e.token.intent))},{"input",e.reported},{"pass",draftNumber(e.token.pass)},{"revision",draftNumber(e.token.revision)},{"before",draftView(e.before)},{"after",draftView(e.after)},{"diagnosis",e.diagnosis?*e.diagnosis:V()}});
    }
    return O{{"format","fathom-recipe-private-continuation-v1"},{"source_key",definition_.sourceKey()},{"contract",definition_.contractSha256()},{"closure",definition_.sourceClosureSha256()},{"definition_sha256",content::sha256(json::stringify(definition_.exportedDefinition()))},{"context_sha256",content::sha256(json::stringify(definition_.retainedSourceContext()))},{"journal",journal},{"pass",draftNumber(state_.pass)},{"revision",draftNumber(state_.revision)},{"view",draftView(viewImpl(state_))},{"request",state_.request?*state_.request:V()},{"plan",state_.plan?*state_.plan:V()},{"diagnosis",state_.diagnosis?*state_.diagnosis:V()}};
}
std::string RecipeTask::continuation() const {
    V body;{std::lock_guard<std::mutex> lock(mutex_);body=continuationBody();}
    const auto bytes=draftEnvelope(body);(void)json::parse(bytes,draftLimits());return bytes;
}
std::unique_ptr<RecipeTask> RecipeTask::restoreContinuation(const Definition& d,const std::string& bytes){
    const auto envelope=json::parse(bytes,draftLimits());fields(envelope,{"body","sha256"});const auto& b=field(envelope,"body");
    need(text(envelope,"sha256")==content::sha256(json::stringify(b)),"DRAFT_CHECKSUM");
    fields(b,{"format","source_key","contract","closure","definition_sha256","context_sha256","journal","pass","revision","view","request","plan","diagnosis"});
    need(text(b,"format")=="fathom-recipe-private-continuation-v1"&&text(b,"source_key")==d.sourceKey()&&text(b,"contract")==d.contractSha256()&&text(b,"closure")==d.sourceClosureSha256()&&text(b,"definition_sha256")==content::sha256(json::stringify(d.exportedDefinition()))&&text(b,"context_sha256")==content::sha256(json::stringify(d.retainedSourceContext())),"DRAFT_SOURCE_BINDING");
    const auto& journal=field(b,"journal");need(journal.isArray()&&journal.array().size()<=100000,"DRAFT_COMMAND_LIMIT");auto out=std::make_unique<RecipeTask>(d);const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(10);
    for(const auto& e:journal.array()){
        need(std::chrono::steady_clock::now()<end,"DRAFT_REPLAY_DEADLINE");fields(e,{"fence","intent","input","pass","revision","before","after","diagnosis"});const auto kind=integer(field(e,"intent"));need(kind>=static_cast<int>(Intent::Choose)&&kind<=static_cast<int>(Intent::Reopen),"DRAFT_INTENT");const auto& fence=field(e,"fence");need(fence.isBool(),"DRAFT_FENCE_TYPE");
        if(fence.boolean()){need(kind==static_cast<int>(Intent::Navigate)&&field(e,"input")==V(O{})&&out->fenceInactiveForNavigation(),"DRAFT_FENCE");}
        else out->apply(out->capture(static_cast<Intent>(kind)),field(e,"input"));
    }
    // Compare regenerated native history and final state, not a raw setter.
    need(out->continuationBody()==b,"DRAFT_NATIVE_REPLAY_DIFFERS");return out;
}
} // namespace fathom::tasks::recipes
