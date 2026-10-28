#include "tasks/C1661HiddenSourceSeven.hpp"
#include "tasks/RecipeTask.hpp"
#include "tasks/DeclaredManualText.hpp"
#include "content/Canonical.hpp"
#include <GeneratedHiddenSevenBindings.hpp>
#include <algorithm>

namespace fathom::tasks::manual_procedure_graph::hidden_seven {
namespace {
using V=json::Value;using O=V::Object;using A=V::Array;
void need(bool b,const char* c){if(!b)throw recipes::Error(c);}
const V& f(const V& v,const std::string& k){const auto* p=v.find(k);need(p!=nullptr,"HIDDEN_SEVEN_FIELD");return *p;}
const Binding& binding(const std::string& key){for(const auto& b:bindings)if(key==b.key)return b;throw recipes::Error("CLOSED_HIDDEN_SEVEN_KEY");}
bool text(const V& v){return v.isString()&&declared_manual_text::visibleUtf8(v.string());}
bool contacts(const V& actual,const V& printed){if(!actual.isArray()||!printed.isArray()||actual.array().size()!=8||printed.array().size()!=8)return false;for(std::size_t i=0;i<8;++i){const auto& a=actual.array()[i];const auto& p=printed.array()[i];if(f(a,"string")!=f(p,"string_name")||f(a,"fret")!=f(p,"fret")||f(a,"named_pitch")!=f(p,"printed_note"))return false;}return true;}
bool sourceNode(const std::string& n){return n=="setup"||n=="whole_pair";}
bool control(const std::string& a){return a=="cancel"||a=="navigate"||a=="stop"||a=="reopen";}
}
bool owns(const std::string& key) noexcept {return std::any_of(bindings.begin(),bindings.end(),[&](const Binding& b){return key==b.key;});}
bool motif(const std::string& key){return binding(key).motif;}
bool requiredTextVisible(const V& value){if(value.isString())return text(value);if(value.isArray())for(const auto& v:value.array())if(!requiredTextVisible(v))return false;if(value.isObject())for(const auto& v:value.object())if(!requiredTextVisible(v.second))return false;return true;}
void validate(const std::string& key,const V& original,const V& contract,const V& program){const auto& b=binding(key);need(content::sha256(json::stringify(original))==b.original&&content::sha256(json::stringify(contract))==b.contract&&content::sha256(json::stringify(program))==b.program,"EXACT_HIDDEN_SEVEN_SOURCE_PROGRAM");}
bool reportedUnit(const std::string& unit,const V& p,const O& saved,const V& contract){
    if(unit=="setup")return text(f(p,"rhythm"))&&text(f(p,"articulation"))&&text(f(p,"phrase_length"));
    if(unit=="whole_pair"){
        const auto found=saved.find("setup");if(found==saved.end())return false;const auto& setup=found->second;const auto& script=f(contract,"source_script");
        if(!contacts(f(p,"source_contacts"),f(script,"source_motif"))||!contacts(f(p,"destination_contacts"),f(script,"destination_motif")))return false;
        for(const auto* field:{"rhythm","articulation","phrase_length"})if(f(p,field)!=f(setup,field)||!text(f(p,field)))return false;
        return true;
    }
    if(unit=="assignment_setup")return text(f(p,"musical_excerpt"))&&text(f(p,"score_reference"));
    if(unit=="assignment_record"){
        for(const auto* name:{"retained_tone","pivot_function_source_key","pivot_function_destination_key","stable_destination_tonic_bar","recording_evidence"})if(!text(f(p,name)))return false;
        return f(p,"recording_kind")==V("local_or_external_reference")||f(p,"recording_kind")==V("self_report");
    }
    throw recipes::Error("CLOSED_HIDDEN_SEVEN_UNIT");
}
V actions(const std::string& key,const V& view,const V& raw,bool sourceRole){
    const bool pair=motif(key);A out;for(const auto& action:raw.array()){
        const auto& a=f(action,"action").string();bool allowed=!pair&&!sourceRole;
        if(pair){const auto* node=view.find("node");const auto n=node&&node->isString()?node->string():"";const auto state=f(view,"state").string();
            if(control(a))allowed=true;
            else if(a=="release"||a=="begin")allowed=sourceRole;
            else if(a=="retry")allowed=!sourceRole;
            else allowed=sourceRole?state=="active"&&sourceNode(n):state=="active"&&!sourceNode(n);
        }
        if(allowed)out.push_back(action);
    }return out;
}
V learnerView(const std::string& key,const V& raw){
    O out{{"title",motif(key)?"Motif listening comparison":"Record before score access"},{"source_clock",nullptr},{"fixed_bpm",nullptr},{"actual_source_supplied",false},{"app_audio_supplied",false},{"observed_performance",false},{"grants_credit",false},{"automatic_mastery",false},{"fresh_unseen_listening_claim",false},{"source_role_is_authentication",false}};
    for(const auto* name:{"state","node","needs_manual_release","release_reason","self_check_exposed_in_history","user_reported_procedure_finished","whole_session_unverified"})if(const auto* v=raw.find(name))out[name]=*v;
    out["source_role_needed"]=motif(key);const auto* node=raw.find("node");out["awaiting_source_player"]=motif(key)&&((f(raw,"state")==V("select"))||(node&&node->isString()&&sourceNode(node->string())&&f(raw,"state")==V("active"))||f(raw,"needs_manual_release")==V(true));
    O own;
    if(const auto* reports=raw.find("learner_responses")) {
        for(const auto& row:reports->object()) {
            if(!motif(key)||row.first=="recognition"||row.first=="key_commit"||row.first=="comparison")own[row.first]=row.second;
        }
    }
    out["learner_responses"]=own;
    // Diagnostics never serialize trusted source reports, IDs, contacts, schema
    // literals or exception text. The full trusted history retains those duties.
    out["manual_report_retry_required"]=f(raw,"state")==V("needs_retry");
    if(const auto* answer=raw.find("printed_self_check")) {
        out["explicitly_disclosed_reference"]=*answer;
        out["printed_self_check"]=*answer; // Existing safe desktop renderer ABI.
    }
    return out;
}
std::vector<V> learnerHistory(const std::string& key,const std::vector<V>& raw){
    std::vector<V> out;for(const auto& e:raw){O projected{{"before",learnerView(key,f(e,"before"))},{"after",learnerView(key,f(e,"after"))},{"observed_performance",false},{"grants_credit",false}};
        for(const auto* k:{"action","pass","revision"})if(const auto* v=e.find(k))projected[k]=*v;
        const auto* node=e.find("node");const auto n=node&&node->isString()?node->string():"";
        if(!motif(key)||n=="recognition"||n=="key_commit"||n=="comparison"||f(e,"action")==V("retry"))projected["reported"]=f(e,"reported");
        else projected["trusted_source_report_retained"]=true;
        out.emplace_back(projected);
    }return out;
}
V reveal(const std::string& key,const V& contract,const O& saved){
    if(motif(key))return O{{"destination_key",f(contract,"destination_key")},{"origin","exact retained printed destination; explicitly revealed after independent response"},{"correctness_automatically_scored",false}};
    const auto found=saved.find("setup");need(found!=saved.end(),"ACTUAL_SCORE_DECLARATION_REQUIRED");need(f(found->second,"actual_source_available")==V(true)&&text(f(found->second,"score_reference")),"ACTUAL_SCORE_REFERENCE_UNAVAILABLE");
    return O{{"learner_declared_score_reference",f(found->second,"score_reference")},{"learner_declared_musical_excerpt",f(found->second,"musical_excerpt")},{"correct_answer_supplied",false},{"actual_recording_inspected",false},{"reference_supplied_by_app",false}};
}
} // namespace
