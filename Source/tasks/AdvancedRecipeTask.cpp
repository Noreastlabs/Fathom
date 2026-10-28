#include "tasks/AdvancedRecipeTask.hpp"
#include "content/Canonical.hpp"
#include <chrono>
#include "GeneratedAdvancedTransferFamily.hpp"
#include "GeneratedAdvancedTransferContext.hpp"
#include "GeneratedAdvancedRemainingFamily.hpp"
#include <algorithm>
#include <atomic>
#include <limits>
#include <functional>
#include <map>
#include <regex>
#include <set>
#include <type_traits>

namespace fathom::tasks::advanced {
namespace {
using V = json::Value; using O = V::Object; using A = V::Array;
void need(bool ok, const char* code) { if (!ok) throw recipes::Error(code); }
const V& field(const V& v, const char* name) { const auto* p=v.find(name); need(p!=nullptr,"FIELDS"); return *p; }
void fields(const V& v, std::initializer_list<const char*> names) {
    need(v.isObject() && v.object().size()==names.size(),"EXACT_FIELDS");
    for (auto name:names) need(v.find(name)!=nullptr,"EXACT_FIELDS");
}
std::string text(const V& v, const char* name) { const auto& p=field(v,name); need(p.isString(),"STRING_TYPE"); return p.string(); }
std::int64_t integer(const V& v) { std::int64_t n{}; need(v.integer(n),"INTEGER_TYPE"); return n; }
void validJson(const V& v) { (void)json::parse(json::stringify(v)); }
bool whitespace(unsigned p) {
    return (p>=9 && p<=13) || (p>=0x1c && p<=0x20) || p==0x85 || p==0xa0 || p==0x1680 ||
        (p>=0x2000 && p<=0x200a) || p==0x2028 || p==0x2029 || p==0x202f || p==0x205f || p==0x3000;
}
bool nonblank(const std::string& s) {
    for (std::size_t i=0;i<s.size();) {
        unsigned p=static_cast<unsigned char>(s[i++]); int n=0;
        if (p>=0xc0 && p<0xe0) { p&=31; n=1; }
        else if (p>=0xe0 && p<0xf0) { p&=15; n=2; }
        else if (p>=0xf0) { p&=7; n=3; }
        while (n--) { need(i<s.size(),"TEXT_UTF8"); p=(p<<6)|(static_cast<unsigned char>(s[i++])&63); }
        if (!whitespace(p)) return true;
    }
    return false;
}
bool hash(const std::string& s) { return s.size()==64 && std::all_of(s.begin(),s.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}); }
const O& pitchClasses() { static const auto v=json::parse(advanced_generated::pitchClassesJson); return v.object(); }
int pc(const std::string& n) { const auto i=pitchClasses().find(n); need(i!=pitchClasses().end(),"PITCH_SPELLING"); return static_cast<int>(integer(i->second)); }
int base(const std::string& s) {
    static const std::map<std::string,int> tuning{{"E",40},{"A",45},{"D",50},{"G",55},{"B",59},{"e",64}};
    const auto i=tuning.find(s); need(i!=tuning.end(),"STRING_NAME"); return i->second;
}
V contact(const std::string& s, int f) { return O{{"string",s},{"fret",V::fromInteger(f)},{"midi",V::fromInteger(base(s)+f)}}; }
int contactMidi(const V& c) {
    fields(c,{"string","fret","midi"}); const auto s=text(c,"string"); const auto f=integer(field(c,"fret")),m=integer(field(c,"midi"));
    need(f>=0 && f<=24 && m==base(s)+f,"CONTACT_RANGE_OR_TUNING"); return static_cast<int>(m);
}
void noFields(const V& p) { need(p.isObject() && p.object().empty(),"NO_PAYLOAD_FIELDS"); }
void yes(const V& v) { need(v.isBool() && v.boolean(),"MANUAL_ATTEMPT_REQUIRED"); }
bool enums(const V& object, const A& names) {
    need(object.isObject() && object.object().size()==names.size(),"DUTY_FIELDS"); O actual,expected;
    for (const auto& name:names) {
        const auto& value=field(object,name.string().c_str()); need(value.isString(),"DUTY_TYPE");
        need(value.string()=="yes" || value.string()=="no" || value.string()=="uncertain","DUTY_ENUM");
        actual.emplace(name.string(),value.string()=="yes"); expected.emplace(name.string(),true);
    }
    return recipes::validateManualReport(actual,expected).empty();
}
const A& common() { static const auto v=json::parse(advanced_generated::commonDutiesJson); return v.array(); }
const A& transfer() { static const auto v=json::parse(advanced_generated::transferDutiesJson); return v.array(); }
std::uint64_t nextInstance() {
    static std::atomic<std::uint64_t> next{1}; auto n=next.load();
    do { need(n!=std::numeric_limits<std::uint64_t>::max(),"INSTANCE_EXHAUSTED"); } while (!next.compare_exchange_weak(n,n+1));
    return n;
}
recipes::Intent intent(Action a) {
    switch(a) {
        case Action::SetPlan:return recipes::Intent::Choose;
        case Action::Release:return recipes::Intent::Release;
        case Action::Retry:case Action::CannotRespond:return recipes::Intent::Retry;
        case Action::Cancel:return recipes::Intent::Stop;
        case Action::Navigate:return recipes::Intent::Navigate;
        case Action::Reopen:return recipes::Intent::Reopen;
        case Action::Begin:case Action::Heard:case Action::SungName:case Action::ChooseArrangements:
        case Action::SetupTarget:case Action::Attack:case Action::Reveal:case Action::Report:
        case Action::NextSet:case Action::Finish:return recipes::Intent::Report;
    }
    throw recipes::Error("ACTION_KIND");
}
const char* stateName(State s) {
    switch(s) {
        case State::Setup:return "setup"; case State::Ready:return "ready"; case State::Hearing:return "hearing";
        case State::Singing:return "singing"; case State::ChooseArrangements:return "choose_arrangements";
        case State::SilentSetup:return "silent_setup"; case State::Attack:return "attack";
        case State::AwaitRelease:return "await_release"; case State::Reveal:return "reveal";
        case State::Reporting:return "reporting"; case State::Reported:return "reported";
        case State::NeedsRetry:return "needs_retry"; case State::Completed:return "completed";
        case State::Cancelled:return "cancelled"; case State::ReopenRelease:return "reopen_release";
    }
    throw recipes::Error("STATE_KIND");
}
std::string setName(std::size_t stage) { need(stage<2,"EXACT_TWO_STRING_SETS"); return stage==0?"string_set_1":"string_set_2"; }
bool stable(State s) { return s==State::Setup || s==State::Ready || s==State::Reporting || s==State::Reported || s==State::NeedsRetry || s==State::Completed; }
} // namespace

Definition::Definition(const char* row,const char* learner,const char* player)
    : exported_(json::parse(row)),initialLearner_(json::parse(learner)),player_(json::parse(player)) {
    key_=text(exported_,"source_key"); contractSha_=text(exported_,"contract_sha256"); closureSha_=advanced_generated::closureSha256;
    recipe_=text(exported_,"recipe");
    contract_=field(exported_,"contract");
    const auto contextRef=text(exported_,"context_ref");
    bool found=false;
    auto findContext=[&](const auto& contexts) { for (const auto& context:contexts) if (contextRef==context.reference) {
        need(!found,"DUPLICATE_SOURCE_CONTEXT"); context_=json::parse(context.value); found=true;
    }};
    findContext(advanced_generated::contexts); findContext(advanced_generated::remainingContexts);
    need(found && text(context_,"recipe")==recipe_ &&
         field(field(context_,"timing_authority"),"fixed_bpm").null(),"EXACT_RETAINED_SOURCE_CONTEXT");
    if (recipe_=="fixed_top_reduction") {
        const auto& behavior=field(field(context_,"source_task"),"fixed_top_behavior");const auto& card=field(contract_,"source_card");
        need(text(behavior,"contracts_resolved_from_exact_model_key")==key_ && field(behavior,"literal_top")==field(card,"literal_top") &&
             field(behavior,"source_harmonies")==field(card,"source_harmonies") && field(behavior,"four_stage_order")==field(contract_,"stages"),"EXACT_FIXED_TOP_CONTEXT_BINDING");
    } else need(field(field(context_,"source_task"),"contract")==contract_,"EXACT_RETAINED_CURRENT_CONTRACT");
    need(text(exported_,"schema")=="fathom.compiled-advanced-manual-definition.1" &&
         (recipe_=="chord_tone_transfer" || recipe_=="full_reconstruction" || recipe_=="fixed_top_reduction") &&
         key_=="exercise-completeness-r01/"+text(exported_,"source_identity") &&
         hash(contractSha_) && hash(closureSha_) && hash(text(exported_,"record_sha256")),"TRUSTED_DEFINITION");
    need(text(initialLearner_,"key")==key_ && (player_.null() || text(player_,"key")==key_) && !initialLearner_.find("reference_pitch"),"TRUSTED_VISIBILITY_SPLIT");
    if (recipe_=="chord_tone_transfer") {
    need(text(contract_,"key")==key_ && field(contract_,"source_absolute_contact_voicing_timing").null() &&
         field(contract_,"audio_supplied")==V(false) && field(contract_,"performance_observed")==V(false) &&
         field(contract_,"credit_awarded")==V(false) && field(contract_,"mastery_awarded")==V(false),"SOURCE_BOUNDARY");
    const auto pitch=text(field(contract_,"source_fields"),"Pitch"); const auto split=pitch.find(" / ");
    const int first=pc(pitch.substr(0,split)); if (split!=std::string::npos) need(first==pc(pitch.substr(split+3)),"SOURCE_EQUIVALENT_SPELLINGS");
    } else if (recipe_=="full_reconstruction") {
        need(text(contract_,"key")==key_ && field(contract_,"complete_manual_contract")==V(true) &&
             field(contract_,"source_fixed_bpm_meter_onset_duration_register_contacts").null() && !initialLearner_.find("source_reference"),"FULL_RECONSTRUCTION_BOUNDARY");
    } else {
        need(text(field(contract_,"source_card"),"package_key")==key_ && field(contract_,"complete_manual_contract")==V(true) && player_.null(),"FIXED_TOP_SOURCE_BOUNDARY");
    }
}
const Definition& definition(const std::string& key) {
    static const std::map<std::string,Definition> definitions=[] {
        std::map<std::string,Definition> out;
        auto insert=[&](const auto& rows) { for (const auto& row:rows) {
            Definition d(row.definition,row.learner,row.player);
            need(d.sourceKey()==row.key && out.emplace(row.key,std::move(d)).second,"CLOSED_COMPILED_KEY");
        }};
        insert(advanced_generated::rows); insert(advanced_generated::remainingRows);
        need(out.size()==56,"CLOSED_FIFTY_SIX"); return out;
    }();
    const auto i=definitions.find(key); need(i!=definitions.end(),"EXACT_ADVANCED_FAMILY_SCOPE"); return i->second;
}
const std::vector<std::string>& keys() {
    static const auto out=[] { std::vector<std::string> keys; for (const auto& row:advanced_generated::rows) { (void)definition(row.key); keys.emplace_back(row.key); } return keys; }();
    return out;
}
const std::vector<std::string>& allKeys() {
    static const auto out=[] { auto result=keys(); for (const auto& row:advanced_generated::remainingRows) { (void)definition(row.key); result.emplace_back(row.key); } return result; }();
    return out;
}
V allowedChoices(const Definition& d,std::optional<std::string> pitch) {
    if (pitch) (void)pc(*pitch); A contacts,names;
    for (const auto& n:pitchClasses()) names.emplace_back(n.first);
    for (auto s:{"E","A","D","G","B","e"}) for (int f=0;f<=24;++f) if (!pitch || (base(s)+f)%12==pc(*pitch)) contacts.push_back(contact(s,f));
    if (d.recipe()=="chord_tone_transfer") return O{{"package_key",d.sourceKey()},{"contract_sha256",d.contractSha256()},{"pitch_names",names},{"pitch_names_nullable",true},
             {"contacts",contacts},{"string_sets",A{"string_set_1","string_set_2"}},{"distinct_string_sets_required",true},
             {"voicing_membership_required",true},{"answer_filter_applied",false},{"default_choice",nullptr},{"source_clock",nullptr},{"source_contacts_fixed",false},{"cue_provider","chosen external_human"}};
    O result{{"package_key",d.sourceKey()},{"contract_sha256",d.contractSha256()},{"default_choice",nullptr},{"source_clock",nullptr},{"source_contacts_fixed",false}};
    if (d.recipe()=="full_reconstruction") {
        O scoreFields; for (const auto& b:field(d.retainedContract(),"worksheet_blocks").array()) scoreFields.emplace(b.string(),A{"hearing_accuracy","first_attack_fretboard_accuracy"});
        result.insert({{"pitch_names",names},{"written_passes",field(d.retainedContract(),"written_passes")},{"contacts",contacts},
          {"target_count",V::fromInteger(64)},{"minimum_fret_range",A{V::fromInteger(0),V::fromInteger(24)}},{"maximum_fret_range",A{V::fromInteger(0),V::fromInteger(24)}},
          {"octave_shift","explicit uniform nonzero multiple of12, within chosen contact range"},{"score_fields",scoreFields},
          {"score_domain",A{V::fromInteger(0),V::fromInteger(1),V::fromInteger(2),nullptr}},{"hidden_source_filter_applied",false},{"recording","actual external reference or declared hash unknown"}});
    } else {
        need(!pitch,"FIXED_TOP_LITERAL_PITCH");const auto& card=field(d.retainedContract(),"source_card");const auto top=text(card,"literal_top");A topContacts,siblings;
        for (auto s:{"E","A","D","G","B","e"}) for (int f=0;f<=24;++f) if ((base(s)+f)%12==pc(top)) topContacts.push_back(contact(s,f));
        const auto& source=field(card,"source_harmonies").array();
        if (text(card,"module")=="C") for (const auto& c:field(d.retainedContract(),"source_sibling_candidates").array()) if (std::find(source.begin(),source.end(),c)==source.end()) siblings.push_back(c);
        result.insert({{"top_contacts",topContacts},{"literal_top",top},{"stages",field(d.retainedContract(),"stages")},{"source_harmonies",source},{"additional_siblings",siblings},
          {"audit_fields",field(d.retainedContract(),"audit_questions")},{"voicing_api","voicings(key,chosen_top,harmony,stage,limit); no auto-selection"}});
    }
    return result;
}
void validatePlan(const V& p) {
    validJson(p); fields(p,{"prerequisites","cue_provider"}); const auto& pre=field(p,"prerequisites"); fields(pre,{"original_workbook","own_instrument"});
    yes(field(pre,"original_workbook")); yes(field(pre,"own_instrument")); const auto& cue=field(p,"cue_provider"); fields(cue,{"kind","reference","ready"});
    need(text(cue,"kind")=="external_human" && nonblank(text(cue,"reference")),"EXTERNAL_CUE_PROVIDER"); yes(field(cue,"ready"));
}
void validateArrangements(const V& p) {
    validJson(p); fields(p,{"string_set_1","string_set_2"}); std::set<std::string> sets[2]; int pitches[2]{};
    for (std::size_t i=0;i<2;++i) {
        const auto& v=field(p,setName(i).c_str()); fields(v,{"strings","target","voicing"});
        const auto& strings=field(v,"strings"),voices=field(v,"voicing");
        need(strings.isArray() && strings.array().size()>=1 && strings.array().size()<=6 && voices.isArray() && voices.array().size()==strings.array().size(),"CHOSEN_STRING_SET_SHAPE");
        for (const auto& s:strings.array()) { need(s.isString(),"STRING_TYPE"); (void)base(s.string()); need(sets[i].insert(s.string()).second,"DUPLICATE_STRING"); }
        std::set<std::string> played; bool inside=false;
        for (const auto& c:voices.array()) { (void)contactMidi(c); need(played.insert(text(c,"string")).second,"DUPLICATE_VOICING_STRING"); if (c==field(v,"target")) inside=true; }
        pitches[i]=contactMidi(field(v,"target"))%12; need(played==sets[i] && inside,"TARGET_IN_CHOSEN_VOICING");
    }
    need(sets[0]!=sets[1] && pitches[0]==pitches[1],"TWO_DISTINCT_SETS_SAME_CHOSEN_PC");
}

AdvancedRecipeTask::AdvancedRecipeTask(const Definition& d):definition_(d),instance_(nextInstance()) { need(d.recipe()=="chord_tone_transfer","TRANSFER_OWNER_SCOPE"); }
AdvancedToken AdvancedRecipeTask::captureImpl(Action action) const {
    recipes::Phase phase=recipes::Phase::Steps;
    if (data_.state==State::Setup || data_.state==State::Ready) phase=recipes::Phase::Select;
    else if (data_.state==State::AwaitRelease || data_.state==State::ReopenRelease) phase=recipes::Phase::Release;
    else if (data_.state==State::Completed || data_.state==State::Cancelled) phase=recipes::Phase::Closed;
    return {{instance_,data_.pass,data_.revision,definition_.sourceKey(),definition_.contractSha256(),definition_.sourceClosureSha256(),phase,static_cast<std::size_t>(action)+1,intent(action)},action,data_.state,data_.stage,data_.cycle};
}
AdvancedToken AdvancedRecipeTask::capture(Action a) const { std::lock_guard<std::mutex> lock(mutex_); return captureImpl(a); }
V AdvancedRecipeTask::learnerViewImpl() const {
    auto v=definition_.initialLearner_; v.object().at("state")=stateName(data_.state); v.object().at("stage")=setName(data_.stage);
    v.object().at("sung_name")=data_.namedPitch; v.object().at("arrangements")=data_.arrangements?*data_.arrangements:V(nullptr);
    v.object().at("previously_revealed")=data_.everRevealed;
    if (data_.currentRevealed) v.object().emplace("reference_pitch",field(definition_.player_,"reference_pitch"));
    return v;
}
V AdvancedRecipeTask::learnerView() const { std::lock_guard<std::mutex> lock(mutex_); return learnerViewImpl(); }
V AdvancedRecipeTask::sourcePlayerView() const { return definition_.sourcePlayerView(); }
std::optional<std::string> AdvancedRecipeTask::priorityGuidance() const {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto i=history_.rbegin();i!=history_.rend();++i) if (i->token.action==Action::Report) {
        if (text(i->reported,"response_speed")!="immediate") return text(definition_.contract_,"printed_priority");
        return std::nullopt;
    }
    return std::nullopt;
}
std::vector<HistoryEvent> AdvancedRecipeTask::history() const { std::lock_guard<std::mutex> lock(mutex_); return history_; }
void AdvancedRecipeTask::clearInitial(Data& s) { s.namedPitch=nullptr; s.cueReport.reset(); s.arrangements.reset(); s.firstReported=s.currentRevealed=false; }
void AdvancedRecipeTask::apply(const AdvancedToken& token,const V& payload) {
    std::lock_guard<std::mutex> lock(mutex_); const auto current=captureImpl(token.action);
    recipes::requireCurrentToken(token.owner,current.owner);
    need(token.action==current.action && token.state==current.state && token.stringSet==current.stringSet && token.cycle==current.cycle,"CURRENT_ADVANCED_ACTION_STATE");
    validJson(payload); need(data_.revision!=std::numeric_limits<std::uint64_t>::max(),"REVISION_EXHAUSTED"); Data next=data_;
    if (token.action==Action::Navigate && (next.state==State::Setup || next.state==State::Completed)) {
        noFields(payload); need(next.pass!=std::numeric_limits<std::uint64_t>::max(),"PASS_EXHAUSTED");
        ++next.pass; ++next.revision;
        // Idle host navigation invalidates pending input without adding a
        // source response, changing phase, or erasing/replaying its history.
        journal_.emplace_back(O{{"kind","apply"},{"action",V::fromInteger(static_cast<int>(token.action))},{"input",payload}});
        data_=std::move(next); return;
    }
    const auto& source=field(definition_.contract_,"source_fields"); const auto chord=text(source,"Chord"),role=text(source,"Role");
    switch(token.action) {
        case Action::SetPlan:
            need(next.state==State::Setup || next.state==State::Completed,"PLAN_STATE"); validatePlan(payload);
            need(next.pass!=std::numeric_limits<std::uint64_t>::max(),"PASS_EXHAUSTED"); ++next.pass; next.stage=next.cycle=0; clearInitial(next); next.plan=payload; next.state=State::Ready; break;
        case Action::Begin:
            need(next.state==State::Ready,"BEGIN_STATE"); need(next.cycle!=std::numeric_limits<std::size_t>::max(),"CYCLE_EXHAUSTED");
            if (next.stage==0) { fields(payload,{"key","chord","role","ready"});
                need(text(payload,"key")==definition_.sourceKey() && text(payload,"chord")==chord && text(payload,"role")==role,"CURRENT_CUE_CONFIRMATION");
                yes(field(payload,"ready")); clearInitial(next); next.state=State::Hearing;
            } else { noFields(payload); need(next.firstReported,"FIRST_STRING_SET_REPORT_REQUIRED"); next.state=State::SilentSetup; }
            ++next.cycle; break;
        case Action::Heard:
            need(next.state==State::Hearing,"HEARING_STATE"); fields(payload,{"heard_chord_and_role"}); (void)enums(payload,A{"heard_chord_and_role"}); next.cueReport=payload; next.state=State::Singing; break;
        case Action::SungName: {
            need(next.state==State::Singing,"SINGING_STATE"); fields(payload,{"pitch_name","singing_attempted"}); const auto& name=field(payload,"pitch_name");
            need(name.null() || name.isString(),"NULLABLE_PITCH_NAME"); if (name.isString()) (void)pc(name.string()); yes(field(payload,"singing_attempted"));
            next.namedPitch=name; next.state=State::ChooseArrangements; break;
        }
        case Action::ChooseArrangements:
            need(next.state==State::ChooseArrangements,"ARRANGEMENT_STATE"); validateArrangements(payload); next.arrangements=payload; next.state=State::SilentSetup; break;
        case Action::CannotRespond:
            need(next.state==State::Singing || next.state==State::ChooseArrangements,"UNABLE_STATE"); fields(payload,{"diagnosis","released"});
            need(nonblank(text(payload,"diagnosis")),"DIAGNOSIS_REQUIRED"); yes(field(payload,"released")); next.state=State::NeedsRetry; break;
        case Action::SetupTarget:
            need(next.state==State::SilentSetup && next.arrangements.has_value(),"SILENT_SETUP_STATE"); yes(payload); next.state=State::Attack; break;
        case Action::Attack:
            need(next.state==State::Attack,"ATTACK_STATE"); yes(payload); next.state=State::AwaitRelease; break;
        case Action::Release:
            need(next.state==State::AwaitRelease || next.state==State::ReopenRelease,"RELEASE_STATE"); yes(payload);
            if (next.state==State::ReopenRelease) { need(next.resume.has_value(),"SAVED_RESUME"); next.state=*next.resume; next.resume.reset(); if (next.state==State::Ready && next.stage==0) clearInitial(next); }
            else next.state=next.stage==0?State::Reveal:State::Reporting;
            break;
        case Action::Reveal:
            need(next.state==State::Reveal,"POST_PLAY_RELEASE_REVEAL_STATE"); noFields(payload); next.currentRevealed=next.everRevealed=true; next.state=State::Reporting; break;
        case Action::Report: {
            need(next.state==State::Reporting && next.arrangements && next.cueReport,"REPORT_STATE");
            fields(payload,{"key","chord","role","string_set","target","named_pitch","attack_count","common","stage_duties","response_speed","diagnosis","notes"});
            const auto& target=field(field(*next.arrangements,setName(next.stage).c_str()),"target");
            const int targetPc=contactMidi(field(payload,"target"))%12;
            need(text(payload,"key")==definition_.sourceKey() && text(payload,"chord")==chord && text(payload,"role")==role &&
                 text(payload,"string_set")==setName(next.stage) && field(payload,"target")==target && field(payload,"named_pitch")==next.namedPitch,"EXACT_SOURCE_RESPONSE_BINDING");
            const auto count=integer(field(payload,"attack_count")); need(count>=0 && nonblank(text(payload,"notes")),"MANUAL_COUNT_NOTES");
            const auto speed=text(payload,"response_speed"); need(speed=="immediate" || speed=="slow" || speed=="uncertain","RESPONSE_SPEED_ENUM");
            const auto diagnosis=text(payload,"diagnosis");
            const bool duties=enums(field(payload,"common"),common()); const bool stageDuties=enums(field(payload,"stage_duties"),next.stage==0?A{"sung_pitch_correct"}:transfer());
            const auto literal=text(source,"Pitch"); const int answer=pc(literal.substr(0,literal.find(" / ")));
            const bool ok=!next.namedPitch.null() && pc(next.namedPitch.string())==answer && targetPc==answer &&
                text(*next.cueReport,"heard_chord_and_role")=="yes" && count==1 && duties && stageDuties;
            need(ok || nonblank(diagnosis),"FAILED_UNKNOWN_REPORT_NEEDS_DIAGNOSIS");
            if (ok && next.stage==0) next.firstReported=true; next.state=ok?State::Reported:State::NeedsRetry; break;
        }
        case Action::NextSet:
            need(next.state==State::Reported && next.stage==0 && next.firstReported,"EXACT_TWO_SETS_ORDER"); noFields(payload); next.stage=1; next.state=State::Ready; break;
        case Action::Retry:
            need(next.state==State::Reported || next.state==State::NeedsRetry,"RETRY_STATE"); need(payload.isString() && nonblank(payload.string()),"RETRY_DIAGNOSIS");
            if (next.stage==0) clearInitial(next); next.state=State::Ready; break;
        case Action::Finish:
            need(next.state==State::Reported && next.stage==1 && next.firstReported,"BOTH_STRING_SETS_REPORT_REQUIRED"); noFields(payload); next.state=State::Completed; break;
        case Action::Cancel:case Action::Navigate:
            need(next.state!=State::Cancelled,"CANCEL_STATE"); noFields(payload); need(next.pass!=std::numeric_limits<std::uint64_t>::max(),"PASS_EXHAUSTED");
            if (next.state!=State::ReopenRelease) next.resume=stable(next.state)?next.state:State::Ready;
            ++next.pass; next.state=State::Cancelled; break;
        case Action::Reopen:
            need(next.state==State::Cancelled,"REOPEN_STATE"); noFields(payload); need(next.pass!=std::numeric_limits<std::uint64_t>::max(),"PASS_EXHAUSTED"); ++next.pass; next.state=State::ReopenRelease; break;
    }
    ++next.revision; HistoryEvent event{token,payload,data_.state,next.state,false,false};
    V command=O{{"kind","apply"},{"action",V::fromInteger(static_cast<int>(token.action))},{"input",payload}};
    history_.push_back(std::move(event));try{journal_.push_back(std::move(command));}catch(...){history_.pop_back();throw;}
    static_assert(std::is_nothrow_move_assignable_v<Data>); data_=std::move(next);
}
namespace {
const A& writtenPasses() { static const A values{"contour","degrees","exact_notes","chord_function"};return values; }
const A& textures() { static const A values{"melody","root_melody","shell_melody","full_voicing"};return values; }
const A& reconstructionCommon() { static const auto v=json::parse(advanced_generated::reconstructionCommonJson);return v.array(); }
bool contains(const A& a,const V& value) { return std::find(a.begin(),a.end(),value)!=a.end(); }
void exactNames(const V& value,const A& names) {
    need(value.isObject() && value.object().size()==names.size(),"EXACT_NAMED_FIELDS");
    for (const auto& n:names) need(value.find(n.string())!=nullptr,"EXACT_NAMED_FIELDS");
}
void state(const std::string& current,std::initializer_list<const char*> states) {
    need(std::any_of(states.begin(),states.end(),[&](auto s){return current==s;}),"FAMILY_ACTION_STATE");
}
void nullableText(const V& v) { need(v.null() || (v.isString() && nonblank(v.string())),"NULLABLE_MANUAL_TEXT"); }
std::pair<std::vector<int>,std::vector<std::string>> chord(const std::string& symbol) {
    static const std::regex syntax("([A-G][#b]?)(maj7|m7b5|m7|7)");std::smatch m;
    need(std::regex_match(symbol,m,syntax),"SOURCE_CHORD_VOCABULARY");const int root=pc(m[1]);
    static const std::map<std::string,std::pair<std::vector<int>,std::vector<std::string>>> q{
      {"maj7",{{0,4,7,11},{"root","3","5","7"}}},{"m7",{{0,3,7,10},{"root","b3","5","b7"}}},
      {"7",{{0,4,7,10},{"root","3","5","b7"}}},{"m7b5",{{0,3,6,10},{"root","b3","b5","b7"}}}};
    auto result=q.at(m[2]);for (auto& n:result.first) n=(n+root)%12;return result;
}
std::string role(const Definition& d,const std::string& harmony) {
    const auto c=chord(harmony);const int pitch=pc(text(field(d.retainedContract(),"source_card"),"literal_top"));
    const auto i=std::find(c.first.begin(),c.first.end(),pitch);need(i!=c.first.end(),"FIXED_TOP_CHORD_MEMBERSHIP");return c.second[static_cast<std::size_t>(i-c.first.begin())];
}
void position(const V& plan,const A& names,bool second=false) {
    if (second) fields(plan,{"position","contacts","source_scope_ack","octave_shift_semitones"});
    else fields(plan,{"position","contacts","source_scope_ack"});
    const auto& p=field(plan,"position");fields(p,{"minimum_fret","maximum_fret","rationale"});
    const auto minimum=integer(field(p,"minimum_fret")),maximum=integer(field(p,"maximum_fret"));
    need(minimum>=0 && minimum<=maximum && maximum<=24 && nonblank(text(p,"rationale")),"CHOSEN_POSITION_RANGE");yes(field(plan,"source_scope_ack"));
    const auto& contacts=field(plan,"contacts");need(contacts.isArray() && contacts.array().size()==64 && names.size()==64,"WHOLE_SIXTY_FOUR_TARGETS");
    for (std::size_t i=0;i<64;++i) {
        const auto& c=contacts.array()[i];const int midi=contactMidi(c);need(names[i].isString() && midi%12==pc(names[i].string()),"WRITTEN_RESPONSE_CONTACT_BINDING");
        const auto fret=integer(field(c,"fret"));need(fret>=minimum && fret<=maximum,"ONE_CHOSEN_POSITION");
    }
}
A writtenNames(const V& responses) {
    A names;for (const auto& bar:field(field(responses,"exact_notes"),"bars").array()) for (const auto& n:bar.array()) names.push_back(n);return names;
}
const std::set<std::string>& familyActions(const std::string& recipe) {
    static const std::set<std::string> reconstruction{"set_source","begin_written","heard","request_stop","release","commit_written","next_written","choose_first_position","diagnose_unable","sung_bar","play_bar","report_bar","next_bar","retry_bar","reveal_source","restart_written","begin_second_register","declare_scores","finish","cancel","navigate","reopen"};
    static const std::set<std::string> fixed{"set_top","restart_top","sing_top","choose_voicing","cannot_realize","name_role","play","release","report","advance","choose_additional","audit","diagnose","finish","cancel","navigate","reopen"};
    need(recipe=="full_reconstruction" || recipe=="fixed_top_reduction","REMAINING_FAMILY_SCOPE");return recipe=="full_reconstruction"?reconstruction:fixed;
}
recipes::Intent familyIntent(const std::string& action) {
    if (action=="release") return recipes::Intent::Release;
    if (action=="cancel") return recipes::Intent::Stop;
    if (action=="navigate") return recipes::Intent::Navigate;
    if (action=="reopen") return recipes::Intent::Reopen;
    if (action=="retry_bar" || action=="restart_written" || action=="diagnose" || action=="diagnose_unable" || action=="cannot_realize") return recipes::Intent::Retry;
    if (action=="set_source" || action=="set_top" || action=="restart_top" || action=="choose_first_position" || action=="begin_second_register" || action=="choose_voicing" || action=="choose_additional") return recipes::Intent::Choose;
    return recipes::Intent::Report;
}
void increment(std::uint64_t& v) { need(v!=std::numeric_limits<std::uint64_t>::max(),"OWNER_COUNTER_EXHAUSTED");++v; }
} // namespace

void validateSourcePlan(const V& plan) {
    validJson(plan);fields(plan,{"prerequisites","recording","source_declarations"});const auto& pre=field(plan,"prerequisites");fields(pre,{"original_workbook","own_instrument"});yes(field(pre,"original_workbook"));yes(field(pre,"own_instrument"));
    const auto& recording=field(plan,"recording");fields(recording,{"kind","reference","declared_sha256","ready"});
    need(text(recording,"kind")=="external_recording" && nonblank(text(recording,"reference")),"EXTERNAL_RECORDING_REFERENCE");yes(field(recording,"ready"));
    const auto& digest=field(recording,"declared_sha256");need(digest.null() || (digest.isString() && hash(digest.string())),"DECLARED_RECORDING_HASH_OR_UNKNOWN");
    (void)enums(field(plan,"source_declarations"),A{"recorded_once","transcriber_did_not_study_source_card"});
}
void validateWritten(const std::string& pass,const V& response) {
    validJson(response);need(contains(writtenPasses(),pass),"EXACT_WRITTEN_PASS");fields(response,{"bars","notes"});const auto& bars=field(response,"bars");
    need(bars.isArray() && bars.array().size()==16 && nonblank(text(response,"notes")),"SIXTEEN_WRITTEN_BARS");
    for (const auto& b:bars.array()) {
        if (pass=="contour" || pass=="degrees") nullableText(b);
        else if (pass=="exact_notes") { need(b.isArray() && b.array().size()==4,"FOUR_WRITTEN_PITCH_SLOTS");for (const auto& n:b.array()) { need(n.null() || n.isString(),"NULLABLE_WRITTEN_PITCH");if (n.isString()) (void)pc(n.string()); } }
        else { fields(b,{"chord","function"});nullableText(field(b,"chord"));nullableText(field(b,"function")); }
    }
}
void validateFixedTopChoice(const Definition& d,const V& choice) {
    validJson(choice);need(d.recipe()=="fixed_top_reduction","FIXED_TOP_CHOICE_SCOPE");fields(choice,{"key","literal_top","contact","original_workbook","own_instrument"});
    const auto top=text(field(d.retainedContract(),"source_card"),"literal_top");need(text(choice,"key")==d.sourceKey() && text(choice,"literal_top")==top && contactMidi(field(choice,"contact"))%12==pc(top),"EXACT_FIXED_TOP_CHOICE");yes(field(choice,"original_workbook"));yes(field(choice,"own_instrument"));
}
void validateFixedVoicing(const Definition& d,const V& top,const V& plan) {
    validJson(plan);need(d.recipe()=="fixed_top_reduction","FIXED_TOP_VOICING_SCOPE");(void)contactMidi(top);fields(plan,{"key","harmony","stage","contacts","rationale"});
    const auto& contract=d.retainedContract();const auto harmony=text(plan,"harmony"),texture=text(plan,"stage");
    need(text(plan,"key")==d.sourceKey() && contains(field(contract,"source_sibling_candidates").array(),harmony) && (contains(textures(),texture) || texture=="bass_melody_reduction") && nonblank(text(plan,"rationale")),"SOURCE_TEXTURE_VOCABULARY");
    const auto& voices=field(plan,"contacts");need(voices.isArray() && !voices.array().empty() && voices.array().size()<=4,"FINITE_TEXTURE_CONTACTS");
    std::set<std::string> strings;std::vector<int> pitches;int high=-1,low=999,highCount=0;
    for (const auto& c:voices.array()) { const int m=contactMidi(c);need(strings.insert(text(c,"string")).second,"DISTINCT_VOICING_STRINGS");pitches.push_back(m%12);low=std::min(low,m);if (m>high) {high=m;highCount=1;} else if (m==high) ++highCount; }
    const int literal=pc(text(field(contract,"source_card"),"literal_top"));need(contactMidi(top)%12==literal && high==contactMidi(top) && highCount==1,"FIXED_HIGHEST_SOUNDING_TOP");
    const auto pcs=chord(harmony).first;std::vector<int> target=texture=="melody"?std::vector<int>{literal}:
      (texture=="root_melody" || texture=="bass_melody_reduction"?std::vector<int>{pcs[0],literal}:texture=="shell_melody"?std::vector<int>{pcs[1],pcs[3],literal}:pcs);
    std::sort(pitches.begin(),pitches.end());std::sort(target.begin(),target.end());need(pitches==target,"EXACT_TEXTURE_PITCH_CLASSES");
    if (texture=="root_melody" || texture=="bass_melody_reduction") need(low%12==pcs[0],"ROOT_BELOW_UNCHANGED_TOP");
}
std::vector<V> voicings(const Definition& d,const V& choice,const std::string& harmony,const std::string& texture,std::size_t limit) {
    need(limit>=1 && limit<=128,"FINITE_ENUMERATION_LIMIT");validateFixedTopChoice(d,choice);need(contains(field(d.retainedContract(),"source_sibling_candidates").array(),harmony) && (contains(textures(),texture) || texture=="bass_melody_reduction"),"EXACT_ENUMERATED_VOCABULARY");
    const auto top=field(choice,"contact");const int literal=contactMidi(top)%12;const auto pcs=chord(harmony).first;
    std::vector<int> target=texture=="melody"?std::vector<int>{literal}:(texture=="root_melody" || texture=="bass_melody_reduction"?std::vector<int>{pcs[0],literal}:texture=="shell_melody"?std::vector<int>{pcs[1],pcs[3],literal}:pcs);
    const auto topPitch=std::find(target.begin(),target.end(),literal);need(topPitch!=target.end(),"TOP_IN_ENUMERATED_TEXTURE");target.erase(topPitch);std::vector<A> menus;
    for (int pitch:target) { A menu;for (auto s:{"E","A","D","G","B","e"}) for (int f=0;f<=24;++f) if (s!=text(top,"string") && base(s)+f<contactMidi(top) && (base(s)+f)%12==pitch) menu.push_back(contact(s,f));menus.push_back(std::move(menu)); }
    std::vector<V> result;A chosen;
    std::function<void(std::size_t)> visit=[&](std::size_t i) { if (result.size()==limit) return;if (i<menus.size()) { for (const auto& c:menus[i]) { chosen.push_back(c);visit(i+1);chosen.pop_back();if (result.size()==limit) return; }return; }
        auto contacts=chosen;contacts.push_back(top);V plan=O{{"key",d.sourceKey()},{"harmony",harmony},{"stage",texture},{"contacts",contacts},{"rationale","Explicit finite authored choice; no source fingering or observed performance."}};
        try { validateFixedVoicing(d,top,plan);result.push_back(std::move(plan)); } catch (const recipes::Error&) {} };
    visit(0);return result;
}

AdvancedRecipeWorkflow::AdvancedRecipeWorkflow(const Definition& d):definition_(d),instance_(nextInstance()) {
    (void)familyActions(d.recipe());if (d.recipe()=="fixed_top_reduction") data_.harmonies=field(field(d.retainedContract(),"source_card"),"source_harmonies");
}
FamilyToken AdvancedRecipeWorkflow::captureImpl(const std::string& action) const {
    need(familyActions(definition_.recipe()).count(action)==1,"EXACT_FAMILY_ACTION");recipes::Phase phase=recipes::Phase::Steps;
    if (data_.state=="setup" || data_.state=="ready_written") phase=recipes::Phase::Select;
    else if (data_.state=="await_release" || data_.state=="played_bar" || data_.state=="reopen_release") phase=recipes::Phase::Release;
    else if (data_.state=="completed" || data_.state=="cancelled") phase=recipes::Phase::Closed;
    const auto& actions=familyActions(definition_.recipe());const auto opcode=static_cast<std::size_t>(std::distance(actions.begin(),actions.find(action)))+1;
    return {{instance_,data_.pass,data_.revision,definition_.sourceKey(),definition_.contractSha256(),definition_.sourceClosureSha256(),phase,opcode,familyIntent(action)},action,data_.state,data_.writtenPass,data_.bar,data_.registerIndex,data_.harmony,data_.texture,data_.recovery};
}
FamilyToken AdvancedRecipeWorkflow::capture(const std::string& action) const { std::lock_guard<std::mutex> lock(mutex_);return captureImpl(action); }
V AdvancedRecipeWorkflow::currentFixed(const Data& d) const {
    need(d.harmonies.isArray() && d.harmony<d.harmonies.array().size() && d.texture<4,"CURRENT_FIXED_TOP_RANGE");
    return O{{"key",definition_.sourceKey()},{"literal_top",field(field(definition_.contract_,"source_card"),"literal_top")},{"harmony",d.harmonies.array()[d.harmony]},{"stage",d.recovery?V("bass_melody_reduction"):textures()[d.texture]}};
}
V AdvancedRecipeWorkflow::target(const Data& d) const {
    need(definition_.recipe()=="full_reconstruction" && d.contacts.isArray() && d.contacts.array().size()==64 && d.bar<16,"CURRENT_WHOLE_RECONSTRUCTION_TARGET");
    A contacts(d.contacts.array().begin()+static_cast<std::ptrdiff_t>(4*d.bar),d.contacts.array().begin()+static_cast<std::ptrdiff_t>(4*d.bar+4));
    return O{{"bar",V::fromInteger(static_cast<std::int64_t>(d.bar+1))},{"contacts",contacts},{"chosen_position",d.position},{"register",V::fromInteger(static_cast<std::int64_t>(d.registerIndex+1))}};
}
V AdvancedRecipeWorkflow::learnerViewImpl() const {
    if (definition_.recipe()=="full_reconstruction") {
        auto view=definition_.initialLearner_;view.object().at("state")=data_.state;view.object().at("written_pass")=writtenPasses()[data_.writtenPass];view.object().at("bar")=V::fromInteger(static_cast<std::int64_t>(data_.bar+1));
        view.object().at("responses")=data_.responses;view.object().at("chosen_position")=data_.position;view.object().at("chosen_contacts")=data_.contacts;view.object().at("register")=V::fromInteger(static_cast<std::int64_t>(data_.registerIndex+1));
        if (data_.revealed) view.object().insert_or_assign("source_reference",field(definition_.player_,"bars"));return view;
    }
    auto view=currentFixed(data_);const auto& card=field(definition_.contract_,"source_card");const auto count=field(card,"source_harmonies").array().size();A extra(data_.harmonies.array().begin()+static_cast<std::ptrdiff_t>(count),data_.harmonies.array().end());
    view.object().insert({{"state",data_.state},{"chosen_top",data_.top},{"chosen_plan",data_.plan},{"literal_source_roles",field(card,"literal_roles")},{"source_harmonies",field(card,"source_harmonies")},{"authored_harmonies",extra},{"source_sibling_candidates",field(definition_.contract_,"source_sibling_candidates")},{"source_clocks",nullptr},{"actual_performance_verified",false},{"mastery_awarded",false}});return view;
}
V AdvancedRecipeWorkflow::learnerView() const { std::lock_guard<std::mutex> lock(mutex_);return learnerViewImpl(); }
V AdvancedRecipeWorkflow::sourcePlayerView() const { return definition_.sourcePlayerView(); }
V AdvancedRecipeWorkflow::currentTarget() const { std::lock_guard<std::mutex> lock(mutex_);return definition_.recipe()=="full_reconstruction"?target(data_):currentFixed(data_); }
V AdvancedRecipeWorkflow::snapshot() const {
    std::lock_guard<std::mutex> lock(mutex_);return O{{"state",data_.state},{"reduction_required",data_.reductionRequired},{"recovery",data_.recovery},{"restart_after_reduction",data_.restartAfterReduction},
      {"source_reference_revealed",data_.revealed},{"symbolic_pitch_matches",data_.hasPitchMatches?V(data_.pitchMatches):V(nullptr)},{"scores",data_.scores},{"hearing_reports",data_.hearingReports},
      {"history_count",V::fromInteger(static_cast<std::int64_t>(history_.size()))},{"release_or_hearing_observed",false},{"runtime_admitted",false},{"credit_awarded",false}};
}
std::vector<FamilyHistoryEvent> AdvancedRecipeWorkflow::history() const { std::lock_guard<std::mutex> lock(mutex_);return history_; }
void AdvancedRecipeWorkflow::apply(const FamilyToken& token,const V& payload) {
    std::lock_guard<std::mutex> lock(mutex_);const auto current=captureImpl(token.action);recipes::requireCurrentToken(token.owner,current.owner);
    need(token.action==current.action && token.state==current.state && token.writtenPass==current.writtenPass && token.bar==current.bar && token.registerIndex==current.registerIndex && token.harmony==current.harmony && token.texture==current.texture && token.recovery==current.recovery,"CURRENT_FAMILY_ACTION_COUNTERS");
    validJson(payload);need(data_.revision!=std::numeric_limits<std::uint64_t>::max(),"REVISION_EXHAUSTED");Data next=data_;
    if (token.action=="navigate" && (next.state=="setup" || next.state=="completed")) { noFields(payload);increment(next.pass);increment(next.revision);journal_.emplace_back(O{{"kind","apply"},{"action",token.action},{"input",payload}});data_=std::move(next);return; }
    if (definition_.recipe()=="full_reconstruction") applyReconstruction(next,token.action,payload);else applyFixedTop(next,token.action,payload);
    ++next.revision;FamilyHistoryEvent event{token,payload,data_.state,next.state,false,false};V command=O{{"kind","apply"},{"action",token.action},{"input",payload}};history_.push_back(std::move(event));try{journal_.push_back(std::move(command));}catch(...){history_.pop_back();throw;}static_assert(std::is_nothrow_move_assignable_v<Data>);data_=std::move(next);
}
void AdvancedRecipeWorkflow::applyReconstruction(Data& d,const std::string& action,const V& p) {
    if (action=="set_source") { state(d.state,{"setup"});validateSourcePlan(p);d.sourcePlan=p;increment(d.pass);d.state="ready_written"; }
    else if (action=="begin_written") {
        state(d.state,{"ready_written"});fields(p,{"key","pass","recording_reference","ready"});
        need(text(p,"key")==definition_.sourceKey() && field(p,"pass")==writtenPasses()[d.writtenPass] && field(p,"recording_reference")==field(field(d.sourcePlan,"recording"),"reference"),"CURRENT_WRITTEN_RECORDING_PASS");yes(field(p,"ready"));d.state="hearing";
    } else if (action=="heard") { state(d.state,{"hearing"});(void)enums(p,A{"heard_source"});d.hearingReports.object().insert_or_assign(writtenPasses()[d.writtenPass].string(),p);d.state="need_source_stop"; }
    else if (action=="request_stop") { state(d.state,{"need_source_stop"});noFields(p);d.state="await_release"; }
    else if (action=="release") {
        state(d.state,{"await_release","played_bar","reopen_release"});fields(p,{"learner_released","external_source_stopped"});yes(field(p,"learner_released"));yes(field(p,"external_source_stopped"));
        if (d.state=="reopen_release") { need(!d.resume.empty(),"SAVED_RECONSTRUCTION_RESUME");d.state=d.resume;d.resume.clear(); } else d.state=d.state=="await_release"?"writing":"reporting_bar";
    } else if (action=="commit_written") { state(d.state,{"writing"});const auto name=writtenPasses()[d.writtenPass].string();validateWritten(name,p);d.responses.object().insert_or_assign(name,p);d.state="written_committed"; }
    else if (action=="next_written") { state(d.state,{"written_committed"});noFields(p);if (d.writtenPass<3) { ++d.writtenPass;d.state="ready_written"; } else d.state="choose_first_position"; }
    else if (action=="choose_first_position") { state(d.state,{"choose_first_position"});position(p,writtenNames(d.responses));d.position=field(p,"position");d.contacts=d.firstContacts=field(p,"contacts");d.state="sing_bar"; }
    else if (action=="diagnose_unable") { state(d.state,{"choose_first_position"});need(p.isString() && nonblank(p.string()),"RECONSTRUCTION_UNABLE_DIAGNOSIS");d.state="needs_written_retry"; }
    else if (action=="sung_bar") { state(d.state,{"sing_bar"});yes(p);d.state="ready_play_bar"; }
    else if (action=="play_bar") { state(d.state,{"ready_play_bar"});yes(p);(void)target(d);d.state="played_bar"; }
    else if (action=="report_bar") {
        state(d.state,{"reporting_bar"});fields(p,{"key","bar","contacts","sing_count","attack_counts","common","diagnosis","notes"});const auto current=target(d);
        need(text(p,"key")==definition_.sourceKey() && integer(field(p,"bar"))==static_cast<std::int64_t>(d.bar+1) && field(p,"contacts")==field(current,"contacts"),"CURRENT_RECONSTRUCTION_BAR_CONTACTS");
        const auto& counts=field(p,"attack_counts");need(counts.isArray() && counts.array().size()==4,"FOUR_MANUAL_ATTACK_COUNTS");bool once=true;
        for (const auto& c:counts.array()) { const auto n=integer(c);need(n>=0,"MANUAL_COUNT_RANGE");once=once && n==1; }
        const auto sing=integer(field(p,"sing_count"));need(sing>=0 && nonblank(text(p,"notes")),"MANUAL_BAR_SING_NOTES");const auto diagnosis=text(p,"diagnosis");const bool duties=enums(field(p,"common"),reconstructionCommon());
        const bool ok=once && sing==1 && duties;need(ok || nonblank(diagnosis),"FAILED_BAR_DIAGNOSIS_REQUIRED");d.state=ok?"bar_reported":"needs_bar_retry";
    } else if (action=="next_bar") { state(d.state,{"bar_reported"});noFields(p);need(d.bar<16,"WHOLE_BAR_RANGE");++d.bar;d.state=d.bar<16?"sing_bar":(d.registerIndex==0?"first_register_reported":"both_registers_reported"); }
    else if (action=="retry_bar") { state(d.state,{"needs_bar_retry","bar_reported"});need(p.isString() && nonblank(p.string()),"BAR_RETRY_DIAGNOSIS");d.state="sing_bar"; }
    else if (action=="reveal_source") {
        state(d.state,{"first_register_reported"});noFields(p);const auto names=writtenNames(d.responses);const auto& bars=field(definition_.player_,"bars").array();bool match=true;std::size_t i=0;
        for (const auto& bar:bars) for (const auto& expected:field(bar,"pitches").array()) { match=match && names[i].isString() && pc(names[i].string())==pc(expected.string());++i; }
        need(i==64,"WHOLE_REVEAL_SOURCE");d.hasPitchMatches=true;d.pitchMatches=match;d.revealed=true;d.state="verification";
    } else if (action=="restart_written") {
        state(d.state,{"needs_written_retry","verification","both_registers_reported"});need(p.isString() && nonblank(p.string()),"WRITTEN_RESTART_DIAGNOSIS");d.writtenPass=d.bar=d.registerIndex=0;d.responses=O{};d.position=d.contacts=d.firstContacts=d.scores=nullptr;d.hearingReports=O{};d.hasPitchMatches=d.pitchMatches=false;increment(d.pass);d.state="ready_written";
    } else if (action=="begin_second_register") {
        state(d.state,{"verification"});need(d.hasPitchMatches && d.pitchMatches,"WRONG_UNKNOWN_SOURCE_NEEDS_RESTART");need(enums(field(d.sourcePlan,"source_declarations"),A{"recorded_once","transcriber_did_not_study_source_card"}) && d.hearingReports.object().size()==4,"RECORDING_HEARING_COMPLETE");
        for (const auto& name:writtenPasses()) need(text(field(d.hearingReports,name.string().c_str()),"heard_source")=="yes","UNKNOWN_HEARING_NEEDS_RESTART");
        position(p,writtenNames(d.responses),true);const auto shift=integer(field(p,"octave_shift_semitones"));need(shift!=0 && shift%12==0,"NONZERO_UNIFORM_OCTAVE");const auto& next=field(p,"contacts").array();
        for (std::size_t i=0;i<64;++i) need(integer(field(next[i],"midi"))-integer(field(d.firstContacts.array()[i],"midi"))==shift,"ALL_SIXTY_FOUR_UNIFORM_TRANSFER");
        d.registerIndex=1;d.bar=0;d.position=field(p,"position");d.contacts=field(p,"contacts");d.state="sing_bar";
    } else if (action=="declare_scores") {
        state(d.state,{"both_registers_reported"});exactNames(p,field(definition_.contract_,"worksheet_blocks").array());for (const auto& block:p.object()) { fields(block.second,{"hearing_accuracy","first_attack_fretboard_accuracy"});for (const auto& value:block.second.object()) if (!value.second.null()) { const auto n=integer(value.second);need(n>=0 && n<=2,"MANUAL_ZERO_TO_TWO_SCORE"); } }d.scores=p;
    } else if (action=="finish") {
        state(d.state,{"both_registers_reported"});noFields(p);for (auto name:{"contour","degrees"}) for (const auto& value:field(field(d.responses,name),"bars").array()) need(!value.null(),"UNKNOWN_WRITTEN_NEEDS_RESTART");
        for (const auto& bar:field(field(d.responses,"chord_function"),"bars").array()) for (const auto& value:bar.object()) need(!value.second.null(),"UNKNOWN_WRITTEN_NEEDS_RESTART");
        need(d.scores.isObject(),"EIGHT_MANUAL_SCORES_REQUIRED");for (const auto& block:d.scores.object()) for (const auto& value:block.second.object()) need(!value.second.null(),"UNKNOWN_SCORE_REMAINS_INCOMPLETE");d.state="completed";
    } else if (action=="cancel" || action=="navigate") {
        state(d.state,{"setup","ready_written","writing","written_committed","choose_first_position","needs_written_retry","reporting_bar","bar_reported","needs_bar_retry","first_register_reported","verification","both_registers_reported","completed","hearing","need_source_stop","await_release","sing_bar","ready_play_bar","played_bar","reopen_release"});noFields(p);
        if (d.state!="reopen_release") { const std::set<std::string> stable{"setup","ready_written","writing","written_committed","choose_first_position","needs_written_retry","reporting_bar","bar_reported","needs_bar_retry","first_register_reported","verification","both_registers_reported","completed"};d.resume=stable.count(d.state)?d.state:(d.contacts.null()?"ready_written":"sing_bar"); }increment(d.pass);d.state="cancelled";
    } else if (action=="reopen") { state(d.state,{"cancelled"});noFields(p);increment(d.pass);d.state="reopen_release"; }
    else throw recipes::Error("RECONSTRUCTION_ACTION_SCOPE");
}
void AdvancedRecipeWorkflow::applyFixedTop(Data& d,const std::string& action,const V& p) {
    const auto& card=field(definition_.contract_,"source_card");const auto current=currentFixed(d);
    if (action=="set_top") { state(d.state,{"setup"});validateFixedTopChoice(definition_,p);d.top=field(p,"contact");d.state="need_sing"; }
    else if (action=="restart_top") {
        state(d.state,{"needs_retry","needs_reduction","audit","ready_finish"});fields(p,{"key","literal_top","contact","original_workbook","own_instrument","diagnosis"});need(nonblank(text(p,"diagnosis")),"TOP_RESTART_DIAGNOSIS");auto choice=p;choice.object().erase("diagnosis");validateFixedTopChoice(definition_,choice);d.top=field(p,"contact");
        if (d.reductionRequired) { d.recovery=d.restartAfterReduction=true; } else { d.harmonies=field(card,"source_harmonies");d.harmony=d.texture=0;d.recovery=d.restartAfterReduction=false; }
        d.plan=d.roleResponse=d.auditAnswers=nullptr;increment(d.pass);d.state="need_sing";
    } else if (action=="sing_top") { state(d.state,{"need_sing"});fields(p,{"sung_before_voicing","notes"});(void)enums(O{{"sung_before_voicing",field(p,"sung_before_voicing")}},A{"sung_before_voicing"});need(nonblank(text(p,"notes")),"SING_BEFORE_VOICING_NOTES");d.retryTarget="need_sing";d.state=text(p,"sung_before_voicing")=="yes"?"choose_voicing":"needs_retry"; }
    else if (action=="choose_voicing") {
        state(d.state,{"choose_voicing"});for (auto name:{"key","harmony","stage"}) need(field(p,name)==field(current,name),"CURRENT_TEXTURE_REALIZATION_BINDING");validateFixedVoicing(definition_,d.top,p);d.plan=p;d.state="need_role";
    } else if (action=="cannot_realize") { state(d.state,{"choose_voicing"});need(p.isString() && nonblank(p.string()),"UNREALIZABLE_TEXTURE_DIAGNOSIS");d.retryTarget="need_sing";d.state="needs_retry"; }
    else if (action=="name_role") { state(d.state,{"need_role"});fields(p,{"role","notes"});nullableText(field(p,"role"));need(nonblank(text(p,"notes")),"MANUAL_ROLE_NOTES");d.roleResponse=p;d.state="ready_play"; }
    else if (action=="play") { state(d.state,{"ready_play"});yes(p);d.state="await_release"; }
    else if (action=="release") { state(d.state,{"await_release","reopen_release"});fields(p,{"learner_released"});yes(field(p,"learner_released"));if (d.state=="reopen_release") { need(!d.resume.empty(),"SAVED_FIXED_TOP_RESUME");d.state=d.resume; } else d.state="report"; }
    else if (action=="report") {
        state(d.state,{"report"});fields(p,{"key","harmony","stage","contacts","attack_counts","duties","diagnosis","notes"});for (auto name:{"key","harmony","stage"}) need(field(p,name)==field(current,name),"CURRENT_FIXED_TOP_REPORT_BINDING");need(field(p,"contacts")==field(d.plan,"contacts") && nonblank(text(p,"notes")),"CURRENT_FIXED_TOP_CONTACT_REPORT");
        const auto& counts=field(p,"attack_counts");need(counts.isArray() && counts.array().size()==field(d.plan,"contacts").array().size(),"MANUAL_HOLD_REPEAT_COUNTS");bool allPositive=true;
        for (const auto& n:counts.array()) { if (n.null()) allPositive=false;else { const auto number=integer(n);need(number>=0,"MANUAL_COUNT_RANGE");allPositive=allPositive && number>0; } }
        A duties{"fixed_top_preserved","melody_clear","no_melody_change_for_easier_grip","role_named_before_chord"};if (text(card,"module")=="C") duties.emplace_back("smallest_available_bass_inner_motion");
        const bool goodDuties=enums(field(p,"duties"),duties);const auto diagnosis=text(p,"diagnosis");const bool good=allPositive && goodDuties && field(d.roleResponse,"role")==V(role(definition_,text(current,"harmony")));
        need(good || nonblank(diagnosis),"FAILED_UNKNOWN_ROLE_DUTY_DIAGNOSIS");d.retryTarget="need_sing";const bool loss=text(field(p,"duties"),"melody_clear")=="no";if (loss) d.reductionRequired=true;
        d.state=good?"stage_reported":(loss && !d.recovery?"needs_reduction":"needs_retry");
    } else if (action=="advance") {
        state(d.state,{"stage_reported"});noFields(p);
        if (d.recovery) { d.reductionRequired=d.recovery=false;if (d.restartAfterReduction) { d.harmonies=field(card,"source_harmonies");d.harmony=d.texture=0;d.restartAfterReduction=false; }d.state="need_sing"; }
        else if (d.texture<3) { ++d.texture;d.state="need_sing"; }
        else if (d.harmony+1<d.harmonies.array().size()) { ++d.harmony;d.texture=0;d.state="need_sing"; }
        else d.state=text(card,"module")=="C" && d.harmonies.array().size()==3?"need_additional":"audit";
        d.plan=d.roleResponse=nullptr;
    } else if (action=="choose_additional") {
        state(d.state,{"need_additional"});fields(p,{"key","harmony","rationale"});const auto harmony=text(p,"harmony");need(text(p,"key")==definition_.sourceKey() && contains(field(definition_.contract_,"source_sibling_candidates").array(),harmony) && !contains(field(card,"source_harmonies").array(),harmony) && nonblank(text(p,"rationale")),"EXACT_ADDITIONAL_SOURCE_SIBLING");d.harmonies.array().emplace_back(harmony);++d.harmony;d.texture=0;d.state="need_sing";
    } else if (action=="audit") {
        state(d.state,{"audit"});fields(p,{"answers","notes","diagnosis"});const auto& answers=field(p,"answers");exactNames(answers,field(definition_.contract_,"audit_questions").array());bool complete=true;for (const auto& answer:answers.object()) { nullableText(answer.second);complete=complete && !answer.second.null(); }
        need(nonblank(text(p,"notes")),"AUDIT_NOTES");const auto diagnosis=text(p,"diagnosis");need(complete || nonblank(diagnosis),"UNKNOWN_AUDIT_DIAGNOSIS");d.auditAnswers=p;d.retryTarget="audit";d.state=complete?"ready_finish":"needs_retry";
    } else if (action=="diagnose") { state(d.state,{"needs_retry","needs_reduction"});need(p.isString() && nonblank(p.string()),"SAME_STEP_DIAGNOSIS");if (d.reductionRequired) d.recovery=true;d.plan=d.roleResponse=nullptr;need(!d.retryTarget.empty(),"REACHABLE_RETRY_TARGET");increment(d.pass);d.state=d.retryTarget; }
    else if (action=="finish") { state(d.state,{"ready_finish"});noFields(p);need(!d.reductionRequired,"MANDATORY_REDUCTION_DEBT");d.state="completed"; }
    else if (action=="cancel" || action=="navigate") {
        state(d.state,{"setup","need_sing","choose_voicing","need_role","ready_play","await_release","report","stage_reported","needs_retry","needs_reduction","need_additional","audit","ready_finish","completed","reopen_release"});noFields(p);
        if (d.state!="reopen_release") d.resume=(d.state=="need_role" || d.state=="ready_play" || d.state=="await_release")?"need_sing":d.state;increment(d.pass);d.state="cancelled";
    } else if (action=="reopen") { state(d.state,{"cancelled"});noFields(p);increment(d.pass);d.state="reopen_release"; }
    else throw recipes::Error("FIXED_TOP_ACTION_SCOPE");
}
namespace {
V objectSchema(O properties) {
    A required;for (const auto& p:properties) required.emplace_back(p.first);
    return O{{"type","object"},{"properties",properties},{"required",required},{"additionalProperties",false}};
}
V arraySchema(V items,std::size_t minimum,std::size_t maximum) {
    return O{{"type","array"},{"items",std::move(items)},{"minItems",V::fromInteger(static_cast<std::int64_t>(minimum))},{"maxItems",V::fromInteger(static_cast<std::int64_t>(maximum))},{"input_role","manual_choice_or_report"}};
}
V textSchema(bool nullable=false,bool nonempty=true) {
    return O{{"type",nullable?V(A{"string","null"}):V("string")},{"minLength",V::fromInteger(nonempty?1:0)},{"nonblank",nonempty},{"input_role","manual_report"}};
}
V numberSchema(std::int64_t minimum,std::int64_t maximum,bool nullable=false) {
    return O{{"type",nullable?V(A{"integer","null"}):V("integer")},{"minimum",V::fromInteger(minimum)},{"maximum",V::fromInteger(maximum)},{"input_role","manual_choice_or_report"}};
}
V ackSchema() { return O{{"type","boolean"},{"input_role","manual_acknowledgement"},{"must_be",true}}; }
V enumSchema(A choices,bool nullable=false) {
    if (nullable) choices.emplace_back(nullptr);return O{{"type",nullable?V(A{"string","null"}):V("string")},{"enum",choices},{"input_role","manual_choice_or_report"}};
}
V binding(const V& value,const char* origin="source_protocol_binding") { return O{{"const",value},{"input_role",origin},{"literal_binding_label",origin}}; }
V ynSchema() { return enumSchema(A{"yes","no","uncertain"}); }
V dutySchema(const A& names) { O fields;for (const auto& name:names) fields.emplace(name.string(),ynSchema());return objectSchema(std::move(fields)); }
V contactSchema(std::optional<std::string> pitch=std::nullopt) {
    A values;for (auto s:{"E","A","D","G","B","e"}) for (int f=0;f<=24;++f) if (!pitch || (base(s)+f)%12==pc(*pitch)) values.push_back(contact(s,f));
    return O{{"type","object"},{"enum",values},{"input_role","explicit_chosen_contact"},{"answer_filter_applied",false}};
}
V pitchSchema() { A names;for (const auto& p:pitchClasses()) names.emplace_back(p.first);return enumSchema(std::move(names),true); }
V positionSchema() { return objectSchema({{"minimum_fret",numberSchema(0,24)},{"maximum_fret",numberSchema(0,24)},{"rationale",textSchema()}}); }
V realizationSchema(bool second) {
    O properties{{"position",positionSchema()},{"contacts",arraySchema(contactSchema(),64,64)},{"source_scope_ack",ackSchema()}};
    if (second) properties.emplace("octave_shift_semitones",O{{"type","integer"},{"input_role","explicit_chosen_register_shift"},{"nonzero_multiple_of",V::fromInteger(12)}});
    return objectSchema(std::move(properties));
}
void addAction(A& actions,const std::string& name,V schema) { actions.emplace_back(O{{"action",name},{"schema",std::move(schema)},{"fresh_native_token_required",true}}); }
} // namespace
Action transferAction(const std::string& name) {
    static const std::map<std::string,Action> actions{{"set_plan",Action::SetPlan},{"begin",Action::Begin},{"heard",Action::Heard},{"sung_name",Action::SungName},{"choose_arrangements",Action::ChooseArrangements},{"cannot_respond",Action::CannotRespond},{"setup_target",Action::SetupTarget},{"attack",Action::Attack},{"release",Action::Release},{"reveal",Action::Reveal},{"report",Action::Report},{"next_set",Action::NextSet},{"retry",Action::Retry},{"finish",Action::Finish},{"cancel",Action::Cancel},{"navigate",Action::Navigate},{"reopen",Action::Reopen}};
    const auto i=actions.find(name);need(i!=actions.end(),"EXACT_TRANSFER_ACTION_NAME");return i->second;
}
bool AdvancedRecipeTask::fenceInactiveForNavigation() {
    std::lock_guard<std::mutex> lock(mutex_);if (data_.state!=State::Setup && data_.state!=State::Completed) return false;
    need(data_.pass!=std::numeric_limits<std::uint64_t>::max() && data_.revision!=std::numeric_limits<std::uint64_t>::max(),"IDLE_FENCE_EXHAUSTED");journal_.emplace_back(O{{"kind","fence"}});++data_.pass;++data_.revision;return true;
}
bool AdvancedRecipeWorkflow::fenceInactiveForNavigation() {
    std::lock_guard<std::mutex> lock(mutex_);if (data_.state!="setup" && data_.state!="completed") return false;
    need(data_.pass!=std::numeric_limits<std::uint64_t>::max() && data_.revision!=std::numeric_limits<std::uint64_t>::max(),"IDLE_FENCE_EXHAUSTED");journal_.emplace_back(O{{"kind","fence"}});++data_.pass;++data_.revision;return true;
}
V AdvancedRecipeTask::learnerInstructions() const {
    return O{{"schema","fathom.learner-safe-advanced-instructions.1"},{"recipe","chord_tone_transfer"},{"text",A{
      "Use the original workbook and your own instrument. Choose an external human cue provider.",
      "Hear the stated chord and role, sing once, and enter your pitch-name response before choosing contacts.",
      "Choose two different string sets and a target inside each voicing. Set up silently, make one first attack, and confirm physical release.",
      "Reveal the printed reference only after the first chosen set has been played and released. Report your actual response; transfer to the second set without a new answer choice.",
      "Wrong or unknown responses require your diagnosis and retry. Earlier reference exposure and response history remain retained.",
      "Cancel or active navigation requires external stop and manual release before resuming. Reports supply no observed hearing/play or credit."}},{"source_clock",nullptr},{"fixed_bpm",nullptr},{"actual_performance_verified",false}};
}
V AdvancedRecipeWorkflow::learnerInstructions() const {
    A instructions;
    if (definition_.recipe()=="full_reconstruction") instructions={
      "Use one chosen externally recorded source. Record once; the transcriber should not study the source card before the test.",
      "Replay that reference for the four written passes: contour, degrees, exact notes, then chord/function. Stop and manually release the external source before writing.",
      "Keep all16 bars and all64 targets. Unknown written fields remain unknown; contact choices follow your written responses before source comparison.",
      field(definition_.contract_,"printed_pulse"),field(definition_.contract_,"printed_realization"),field(definition_.contract_,"printed_scoring"),
      "Complete the first16-bar chosen register before revealing the reference; choose a second complete register with one uniform nonzero octave shift.",
      "Report all eight0–2 scores manually. Unknown scores block finish; zero scores carry no automatic acceptance or mastery threshold.",
      "Diagnosed written/bar retries retain response and source-reveal histories. Cancellation requires learner and external-source release."};
    else instructions={field(definition_.contract_,"instruction"),
      "Choose a sounding contact for the printed fixed top. Sing before choosing each texture; name the top's role before playing.",
      "Practice melody, root+melody, shell+melody, and full voicing for each current source harmony. Physical release precedes each report.",
      "ModuleC requires all three source harmonies in order and one explicitly chosen additional sibling outside those three, followed by the source-choice audit.",
      "If the melody disappears, preserve the mandatory bass+melody reduction. A changed register or cancellation keeps that debt; a positive reduction report and advance must precede the full rerender.",
      "Manual role, hold/repeat counts, audible choice audits and smallest available motion are declarations. Unknowns need diagnosis; no clocks or observed performance are supplied."};
    return O{{"schema","fathom.learner-safe-advanced-instructions.1"},{"recipe",definition_.recipe()},{"text",instructions},{"source_clock",nullptr},{"fixed_bpm",nullptr},{"actual_performance_verified",false}};
}
V AdvancedRecipeTask::learnerActions() const {
    std::lock_guard<std::mutex> lock(mutex_);A actions;auto add=[&](const char* action,V schema){addAction(actions,action,std::move(schema));};const auto empty=objectSchema({});
    const auto& source=field(definition_.contract_,"source_fields");const auto sourceBindings=O{{"key",binding(definition_.sourceKey())},{"chord",binding(field(source,"Chord"))},{"role",binding(field(source,"Role"))}};
    switch(data_.state) {
      case State::Setup:case State::Completed:
        add("set_plan",objectSchema({{"prerequisites",objectSchema({{"original_workbook",ackSchema()},{"own_instrument",ackSchema()}})},
          {"cue_provider",objectSchema({{"kind",binding("external_human")},{"reference",textSchema()},{"ready",ackSchema()}})}}));break;
      case State::Ready: { auto p=sourceBindings;if (data_.stage==0) {p.emplace("ready",ackSchema());add("begin",objectSchema(std::move(p)));} else add("begin",empty);break; }
      case State::Hearing:add("heard",objectSchema({{"heard_chord_and_role",ynSchema()}}));break;
      case State::Singing:add("sung_name",objectSchema({{"pitch_name",pitchSchema()},{"singing_attempted",ackSchema()}}));break;
      case State::ChooseArrangements: {
        const auto target=contactSchema(data_.namedPitch.isString()?std::optional<std::string>(data_.namedPitch.string()):std::nullopt);
        auto set=objectSchema({{"strings",arraySchema(enumSchema(A{"E","A","D","G","B","e"}),1,6)},{"target",target},{"voicing",arraySchema(contactSchema(),1,6)}});
        add("choose_arrangements",objectSchema({{"string_set_1",set},{"string_set_2",set}}));break;
      }
      case State::SilentSetup:add("setup_target",ackSchema());break;
      case State::Attack:add("attack",ackSchema());break;
      case State::AwaitRelease:case State::ReopenRelease:add("release",ackSchema());break;
      case State::Reveal:add("reveal",empty);break;
      case State::Reporting: {
        auto p=sourceBindings;p.insert({{"string_set",binding(setName(data_.stage))},{"target",binding(field(field(*data_.arrangements,setName(data_.stage).c_str()),"target"),"prior_learner_choice_binding")},
          {"attack_count",numberSchema(0,std::numeric_limits<std::int64_t>::max())},{"common",dutySchema(common())},{"stage_duties",dutySchema(data_.stage==0?A{"sung_pitch_correct"}:transfer())},
          {"response_speed",enumSchema(A{"immediate","slow","uncertain"})},{"diagnosis",textSchema(false,false)},{"notes",textSchema()}});
        auto name=pitchSchema();name.object().insert({{"must_equal_prior",data_.namedPitch},{"prior_learner_response_binding",true},{"reentry_required",true}});p.emplace("named_pitch",std::move(name));add("report",objectSchema(std::move(p)));break;
      }
      case State::Reported:add(data_.stage==0?"next_set":"finish",empty);add("retry",textSchema());break;
      case State::NeedsRetry:add("retry",textSchema());break;
      case State::Cancelled:add("reopen",empty);break;
    }
    if (data_.state==State::Singing || data_.state==State::ChooseArrangements) add("cannot_respond",objectSchema({{"diagnosis",textSchema()},{"released",ackSchema()}}));
    if (data_.state!=State::Cancelled) {add("cancel",empty);add("navigate",empty);}return actions;
}
V AdvancedRecipeWorkflow::learnerActions() const {
    std::lock_guard<std::mutex> lock(mutex_);A actions;auto add=[&](const char* name,V schema){addAction(actions,name,std::move(schema));};const auto empty=objectSchema({});const auto& s=data_.state;
    if (definition_.recipe()=="full_reconstruction") {
        if (s=="setup") add("set_source",objectSchema({{"prerequisites",objectSchema({{"original_workbook",ackSchema()},{"own_instrument",ackSchema()}})},
          {"recording",objectSchema({{"kind",binding("external_recording")},{"reference",textSchema()},{"declared_sha256",O{{"type",A{"string","null"}},{"pattern","^[0-9a-f]{64}$"},{"input_role","optional_declared_recording_identity"}}},{"ready",ackSchema()}})},
          {"source_declarations",dutySchema(A{"recorded_once","transcriber_did_not_study_source_card"})}}));
        else if (s=="ready_written") add("begin_written",objectSchema({{"key",binding(definition_.sourceKey())},{"pass",binding(writtenPasses()[data_.writtenPass])},{"recording_reference",binding(field(field(data_.sourcePlan,"recording"),"reference"),"prior_learner_recording_binding")},{"ready",ackSchema()}}));
        else if (s=="hearing") add("heard",objectSchema({{"heard_source",ynSchema()}}));
        else if (s=="need_source_stop") add("request_stop",empty);
        else if (s=="await_release" || s=="played_bar" || s=="reopen_release") add("release",objectSchema({{"learner_released",ackSchema()},{"external_source_stopped",ackSchema()}}));
        else if (s=="writing") {
            const auto pass=writtenPasses()[data_.writtenPass].string();V bar=pass=="exact_notes"?arraySchema(pitchSchema(),4,4):(pass=="chord_function"?objectSchema({{"chord",textSchema(true)},{"function",textSchema(true)}}):textSchema(true));
            add("commit_written",objectSchema({{"bars",arraySchema(std::move(bar),16,16)},{"notes",textSchema()}}));
        } else if (s=="written_committed") add("next_written",empty);
        else if (s=="choose_first_position") {add("choose_first_position",realizationSchema(false));add("diagnose_unable",textSchema());}
        else if (s=="sing_bar") add("sung_bar",ackSchema());
        else if (s=="ready_play_bar") add("play_bar",ackSchema());
        else if (s=="reporting_bar") add("report_bar",objectSchema({{"key",binding(definition_.sourceKey())},{"bar",binding(V::fromInteger(static_cast<std::int64_t>(data_.bar+1)))},{"contacts",binding(field(target(data_),"contacts"),"prior_learner_choice_binding")},
          {"sing_count",numberSchema(0,std::numeric_limits<std::int64_t>::max())},{"attack_counts",arraySchema(numberSchema(0,std::numeric_limits<std::int64_t>::max()),4,4)},{"common",dutySchema(reconstructionCommon())},{"diagnosis",textSchema(false,false)},{"notes",textSchema()}}));
        else if (s=="bar_reported") {add("next_bar",empty);add("retry_bar",textSchema());}
        else if (s=="needs_bar_retry") add("retry_bar",textSchema());
        else if (s=="first_register_reported") add("reveal_source",empty);
        else if (s=="verification") add("begin_second_register",realizationSchema(true));
        else if (s=="both_registers_reported") {
            O scores;for (const auto& b:field(definition_.contract_,"worksheet_blocks").array()) scores.emplace(b.string(),objectSchema({{"hearing_accuracy",numberSchema(0,2,true)},{"first_attack_fretboard_accuracy",numberSchema(0,2,true)}}));
            add("declare_scores",objectSchema(std::move(scores)));add("finish",empty);
        }
        if (s=="needs_written_retry" || s=="verification" || s=="both_registers_reported") add("restart_written",textSchema());
    } else {
        const auto& card=field(definition_.contract_,"source_card");const auto current=currentFixed(data_);
        auto top=objectSchema({{"key",binding(definition_.sourceKey())},{"literal_top",binding(field(card,"literal_top"))},{"contact",contactSchema(text(card,"literal_top"))},{"original_workbook",ackSchema()},{"own_instrument",ackSchema()}});
        if (s=="setup") add("set_top",top);
        else if (s=="need_sing") add("sing_top",objectSchema({{"sung_before_voicing",ynSchema()},{"notes",textSchema()}}));
        else if (s=="choose_voicing") {
            auto plan=objectSchema({{"key",binding(definition_.sourceKey())},{"harmony",binding(field(current,"harmony"))},{"stage",binding(field(current,"stage"))},{"contacts",arraySchema(contactSchema(),1,4)},{"rationale",textSchema()}});
            plan.object().emplace("explicit_choice_api","voicings(definition,topChoice,currentHarmony,currentStage,limit); no default selection");add("choose_voicing",std::move(plan));add("cannot_realize",textSchema());
        } else if (s=="need_role") add("name_role",objectSchema({{"role",textSchema(true)},{"notes",textSchema()}}));
        else if (s=="ready_play") add("play",ackSchema());
        else if (s=="await_release" || s=="reopen_release") add("release",objectSchema({{"learner_released",ackSchema()}}));
        else if (s=="report") {
            A duties{"fixed_top_preserved","melody_clear","no_melody_change_for_easier_grip","role_named_before_chord"};if (text(card,"module")=="C") duties.emplace_back("smallest_available_bass_inner_motion");const auto count=field(data_.plan,"contacts").array().size();
            add("report",objectSchema({{"key",binding(definition_.sourceKey())},{"harmony",binding(field(current,"harmony"))},{"stage",binding(field(current,"stage"))},{"contacts",binding(field(data_.plan,"contacts"),"prior_learner_choice_binding")},
              {"attack_counts",arraySchema(numberSchema(0,std::numeric_limits<std::int64_t>::max(),true),count,count)},{"duties",dutySchema(duties)},{"diagnosis",textSchema(false,false)},{"notes",textSchema()}}));
        } else if (s=="stage_reported") add("advance",empty);
        else if (s=="need_additional") add("choose_additional",objectSchema({{"key",binding(definition_.sourceKey())},{"harmony",enumSchema(field(allowedChoices(definition_),"additional_siblings").array())},{"rationale",textSchema()}}));
        else if (s=="audit") { O answers;for (const auto& n:field(definition_.contract_,"audit_questions").array()) answers.emplace(n.string(),textSchema(true));add("audit",objectSchema({{"answers",objectSchema(std::move(answers))},{"notes",textSchema()},{"diagnosis",textSchema(false,false)}})); }
        else if (s=="ready_finish") add("finish",empty);
        if (s=="needs_retry" || s=="needs_reduction") add("diagnose",textSchema());
        if (s=="needs_retry" || s=="needs_reduction" || s=="audit" || s=="ready_finish") {top.object().at("properties").object().emplace("diagnosis",textSchema());top.object().at("required").array().emplace_back("diagnosis");add("restart_top",std::move(top));}
    }
    if (s=="cancelled") add("reopen",empty);else {add("cancel",empty);add("navigate",empty);}return actions;
}

namespace {
json::Limits advancedDraftLimits(){json::Limits l;l.bytes=64*1024*1024;l.depth=96;l.stringBytes=8*1024*1024;l.values=2000000;return l;}
V draftN(std::uint64_t n){need(n<=static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()),"DRAFT_COUNTER_RANGE");return V::fromInteger(static_cast<std::int64_t>(n));}
V sourceDraft(const Definition&d,const A&journal,const V&state,const char*format){need(journal.size()<=100000,"DRAFT_COMMAND_LIMIT");return O{{"format",format},{"source_key",d.sourceKey()},{"contract",d.contractSha256()},{"closure",d.sourceClosureSha256()},{"definition",content::sha256(json::stringify(d.exportedDefinition()))},{"context",content::sha256(json::stringify(d.retainedSourceContext()))},{"player",content::sha256(json::stringify(d.sourcePlayerView()))},{"journal",journal},{"state",state}};}
std::string advancedEnvelope(const V&b){return json::stringify(O{{"body",b},{"sha256",content::sha256(json::stringify(b))}});}
V openAdvancedDraft(const Definition&d,const std::string&bytes,const char*format){auto e=json::parse(bytes,advancedDraftLimits());fields(e,{"body","sha256"});auto b=field(e,"body");need(field(e,"sha256")==V(content::sha256(json::stringify(b))),"DRAFT_CHECKSUM");fields(b,{"format","source_key","contract","closure","definition","context","player","journal","state"});need(field(b,"format")==V(format)&&field(b,"source_key")==V(d.sourceKey())&&field(b,"contract")==V(d.contractSha256())&&field(b,"closure")==V(d.sourceClosureSha256())&&field(b,"definition")==V(content::sha256(json::stringify(d.exportedDefinition())))&&field(b,"context")==V(content::sha256(json::stringify(d.retainedSourceContext())))&&field(b,"player")==V(content::sha256(json::stringify(d.sourcePlayerView()))),"DRAFT_SOURCE_BINDING");need(field(b,"journal").isArray()&&field(b,"journal").array().size()<=100000,"DRAFT_COMMAND_LIMIT");return b;}
}

V AdvancedRecipeTask::continuationBody() const {return sourceDraft(definition_,journal_,O{{"pass",draftN(data_.pass)} ,{"revision",draftN(data_.revision)} ,{"stage",draftN(data_.stage)} ,{"cycle",draftN(data_.cycle)} ,{"state",V::fromInteger(static_cast<int>(data_.state))},{"resume",data_.resume?V::fromInteger(static_cast<int>(*data_.resume)):V()},{"plan",data_.plan?*data_.plan:V()},{"arrangements",data_.arrangements?*data_.arrangements:V()},{"cueReport",data_.cueReport?*data_.cueReport:V()},{"namedPitch",data_.namedPitch},{"firstReported",data_.firstReported},{"currentRevealed",data_.currentRevealed},{"everRevealed",data_.everRevealed},{"history_count",draftN(history_.size())},{"learner",learnerViewImpl()}},"fathom-advanced-transfer-private-v1");}
std::string AdvancedRecipeTask::continuation() const {V body;{std::lock_guard<std::mutex>lock(mutex_);body=continuationBody();}auto bytes=advancedEnvelope(body);(void)json::parse(bytes,advancedDraftLimits());return bytes;}
std::unique_ptr<AdvancedRecipeTask> AdvancedRecipeTask::restoreContinuation(const Definition&d,const std::string&bytes){auto b=openAdvancedDraft(d,bytes,"fathom-advanced-transfer-private-v1");auto out=std::make_unique<AdvancedRecipeTask>(d);const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(10);for(const auto&c:field(b,"journal").array()){need(std::chrono::steady_clock::now()<end,"DRAFT_REPLAY_DEADLINE");if(field(c,"kind")==V("fence")){fields(c,{"kind"});need(out->fenceInactiveForNavigation(),"DRAFT_FENCE");}else{fields(c,{"kind","action","input"});need(field(c,"kind")==V("apply"),"DRAFT_COMMAND");std::int64_t n{};need(field(c,"action").integer(n)&&n>=static_cast<int>(Action::SetPlan)&&n<=static_cast<int>(Action::Reopen),"DRAFT_ACTION");auto action=static_cast<Action>(n);out->apply(out->capture(action),field(c,"input"));}}need(out->continuationBody()==b,"DRAFT_NATIVE_REPLAY_DIFFERS");return out;}

V AdvancedRecipeWorkflow::continuationBody() const {return sourceDraft(definition_,journal_,O{{"pass",draftN(data_.pass)} ,{"revision",draftN(data_.revision)} ,{"writtenPass",draftN(data_.writtenPass)} ,{"bar",draftN(data_.bar)} ,{"registerIndex",draftN(data_.registerIndex)} ,{"harmony",draftN(data_.harmony)} ,{"texture",draftN(data_.texture)} ,{"state",data_.state},{"resume",data_.resume},{"retryTarget",data_.retryTarget},{"revealed",data_.revealed},{"hasPitchMatches",data_.hasPitchMatches},{"pitchMatches",data_.pitchMatches},{"recovery",data_.recovery},{"reductionRequired",data_.reductionRequired},{"restartAfterReduction",data_.restartAfterReduction},{"sourcePlan",data_.sourcePlan},{"position",data_.position},{"contacts",data_.contacts},{"firstContacts",data_.firstContacts},{"responses",data_.responses},{"hearingReports",data_.hearingReports},{"scores",data_.scores},{"top",data_.top},{"plan",data_.plan},{"roleResponse",data_.roleResponse},{"auditAnswers",data_.auditAnswers},{"harmonies",data_.harmonies},{"history_count",draftN(history_.size())},{"learner",learnerViewImpl()}},"fathom-advanced-workflow-private-v1");}
std::string AdvancedRecipeWorkflow::continuation() const {V body;{std::lock_guard<std::mutex>lock(mutex_);body=continuationBody();}auto bytes=advancedEnvelope(body);(void)json::parse(bytes,advancedDraftLimits());return bytes;}
std::unique_ptr<AdvancedRecipeWorkflow> AdvancedRecipeWorkflow::restoreContinuation(const Definition&d,const std::string&bytes){auto b=openAdvancedDraft(d,bytes,"fathom-advanced-workflow-private-v1");auto out=std::make_unique<AdvancedRecipeWorkflow>(d);const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(10);for(const auto&c:field(b,"journal").array()){need(std::chrono::steady_clock::now()<end,"DRAFT_REPLAY_DEADLINE");if(field(c,"kind")==V("fence")){fields(c,{"kind"});need(out->fenceInactiveForNavigation(),"DRAFT_FENCE");}else{fields(c,{"kind","action","input"});need(field(c,"kind")==V("apply"),"DRAFT_COMMAND");need(field(c,"action").isString(),"DRAFT_ACTION");const auto action=field(c,"action").string();out->apply(out->capture(action),field(c,"input"));}}need(out->continuationBody()==b,"DRAFT_NATIVE_REPLAY_DIFFERS");return out;}
} // namespace fathom::tasks::advanced
