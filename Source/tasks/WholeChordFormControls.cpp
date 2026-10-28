#include "tasks/WholeChordFormControls.hpp"
#include "tasks/DeclaredManualText.hpp"
#include "GeneratedWholeChordFormPrograms.hpp"
#include <algorithm>
#include <map>
#include <set>
#include <stdexcept>
namespace fathom::tasks::whole_chord_form_controls {
namespace {
using V=json::Value;using O=V::Object;using A=V::Array;
void need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
const V& f(const V& v,const std::string& k){const auto* p=v.find(k);need(p,"WHOLE_FORM_FIELD");return *p;}
std::int64_t n(const V& v){std::int64_t x{};need(v.integer(x),"WHOLE_FORM_INTEGER");return x;}
bool known(const V& v){if(v.null())return false;if(v.isString())return declared_manual_text::visibleUtf8(v.string());if(v.isObject())for(const auto& x:v.object())if(!known(x.second))return false;if(v.isArray())for(const auto& x:v.array())if(!known(x))return false;return true;}
bool includes(const V& a,const V& e){if(e.isObject()){if(!a.isObject())return false;for(const auto& p:e.object()){const auto* v=a.find(p.first);if(!v||!includes(*v,p.second))return false;}return true;}if(e.isArray()){if(!a.isArray()||a.array().size()!=e.array().size())return false;for(std::size_t i=0;i<e.array().size();++i)if(!includes(a.array()[i],e.array()[i]))return false;return true;}return a==e;}
const O& table(){static const O result=[] {O out;const auto& input=whole_chord_form_data::programs();need(f(input,"version")==V("B1145-source-whole-chord-forms-r15")&&f(input,"source_clock").null(),"WHOLE_FORM_VERSION");for(const auto& r:f(input,"rows").array())need(out.emplace(f(r,"source_key").string(),r).second,"WHOLE_FORM_UNIQUE_KEY");need(out.size()==24,"WHOLE_FORM_EXACT24");return out;}();return result;}
struct Row{V original,program,flags,cells;};std::map<std::string,Row> rows;
bool flag(const Row& r,const char* name){return f(r.flags,name)==V(true);}
V& policy(O& ps,const std::string& key){auto& base=ps[key];if(base.null())base=O{{"reduction_required",false},{"trigger_unresolved",false},{"reported_bpm_ceiling",nullptr}};auto& p=base.object()["whole_chord_form"];if(p.null())p=O{{"major_V_isolation_debt",false},{"pending_isolation_release",false},{"retained_known_negative_witness",nullptr},{"retained_choices",nullptr},{"barre_count_initialized",false},{"full_barre_cells_since_rest",V::fromInteger(0)},{"completed_capstone_passes",V::fromInteger(0)}};return p;}
const V* retained(const O& ps,const std::string& key){const auto i=ps.find(key);return i==ps.end()?nullptr:i->second.find("whole_chord_form");}
V shapeForExtent(const Row& r,const V& source,const V& choice){if(!flag(r,"partial")||f(choice,"chosen_F_extent")==V("full"))return source;A out;const auto& fingers=f(choice,"chosen_F_upper_four_fingers").array();for(const auto& c:source.array())if(n(f(c,"string"))<=4){auto chosen=c;chosen.object()["finger"]=fingers.at(out.size());out.push_back(chosen);}need(out.size()==4,"WHOLE_FORM_FOUR_SOURCE_CONTACTS");return out;}
V actualExpected(const Row& r,const V& choice){auto out=f(r.program,"source_expected_ordered_contacts");std::size_t total{};const auto& dynamic=f(r.program,"source_dynamic_contact_bindings");
 for(auto& entry:out.object()){
  auto& contact=entry.second;
  if(const auto* d=dynamic.find(entry.first)){
   const auto kind=f(*d,"kind");
   if(kind==V("selected_stable_string")){
    const auto string=f(choice,"chosen_stable_four_string_order").array().at(n(f(*d,"choice_index")));const auto stroke=f(choice,"chosen_pass4_strokes").array().at(n(f(*d,"stroke_index")));contact.object()["reported_actual_selected_string"]=string;contact.object()["reported_actual_selected_stroke"]=stroke;V selected;for(const auto& c:f(*d,"source_shape").array())if(f(c,"string")==string)selected=c;need(!selected.null(),"WHOLE_FORM_ACTIVE_STRING");contact.object()["reported_actual_selected_contact"]=A{selected};
   }else if(kind==V("optional_F_upper_four")){
    const auto shape=shapeForExtent(r,f(*d,"source_shape"),choice);contact.object()["reported_actual_contact_geometry"]=shape;A strings;for(const auto& c:shape.array())if(f(c,"muted")==V(false))strings.push_back(f(c,"string"));contact.object()["reported_actual_attack_zone"]=strings;
   }else if(kind==V("chosen_stroke"))contact.object()["reported_actual_stroke"]=f(f(choice,"chosen_unprinted_strokes"),entry.first);
   else if(kind==V("qualified_confirmation_or_hold")){
    const auto& mode=f(f(choice,"chosen_anticipation_confirmation_or_hold"),"destination_"+std::to_string(n(f(*d,"destination_bar"))));const bool hold=mode==V("hold_no_new_attack");contact.object()["reported_actual_stroke"]=hold?V("no_new_attack"):V("D");contact.object()["reported_actual_attack_count"]=V::fromInteger(hold?0:1);contact.object()["reported_sustain_without_new_attack"]=hold;
   }else{need(kind==V("qualified_final_Am_sustain"),"WHOLE_FORM_CLOSED_DYNAMIC_KIND");contact.object()["reported_actual_stroke"]="no_new_attack";contact.object()["reported_actual_attack_count"]=V::fromInteger(0);contact.object()["reported_sustain_without_new_attack"]=true;}
  }
  total+=n(f(contact,"reported_actual_attack_count"));if(contact.find("reported_additional_anticipated_contact"))++total;
 }
 return O{{"contacts",out},{"derived_actual_attack_count",V::fromInteger(total)}};
}
bool loss(const Row& row,const V& payload){if(!flag(row,"minor_V_repair"))return false;const auto* reports=payload.find("actual_ordered_contacts");if(!reports)return false;for(int i=9;i<=12;++i){const auto& p=f(*reports,"contact_"+std::to_string(i));if(f(p,"reported_named_quality")==V("minor")||f(p,"major_V_quality_personally_heard_reported")==V(false)||f(p,"reported_actual_chord")==V(f(f(f(row.program,"source_expected_ordered_contacts"),"contact_9"),"reported_actual_chord").string()+"m"))return true;}return false;}
bool choicesKnown(const Row& r,const V& payload,const V* ps){auto required=payload;
 if(flag(r,"partial")){required.object().erase("declared_actual_partial_need_reported");required.object().erase("chosen_F_upper_four_fingers");const auto mode=f(payload,"chosen_F_extent");if(mode==V("upper_four_if_needed")){if(f(payload,"declared_actual_partial_need_reported")!=V(true)||!known(f(payload,"chosen_F_upper_four_fingers")))return false;}else if(mode!=V("full"))return false;}
 if(flag(r,"capstone_rest")){required.object().erase("actual_rest_since_prior_capstone_seconds_reported");const auto prior=f(payload,"actual_prior_capstone_pass_reported");if(prior.null())return false;const bool owed=prior==V(true)||(ps&&n(f(*ps,"completed_capstone_passes"))>0);if(owed){const auto& rest=f(payload,"actual_rest_since_prior_capstone_seconds_reported");if(prior!=V(true)||!known(rest)||n(rest)<60)return false;}}
 if(!known(required))return false;
 if(flag(r,"selected_string_pass")){std::set<std::int64_t> source,chosen;for(const auto& s:f(f(r.program,"choice_domains"),"stable_four_strings").array())source.insert(n(s));const auto& a=f(payload,"chosen_stable_four_string_order").array();for(const auto& s:a){const auto v=n(s);if(!source.count(v))return false;chosen.insert(v);}if(a.size()!=4||chosen.size()!=4)return false;}
 if(flag(r,"barre")){const auto count=n(f(payload,"prior_full_barre_cells_since_rest_reported"));const auto rest=f(payload,"prior_full_rest_taken_reported");if(count>=4&&rest!=V(true))return false;if(ps&&f(*ps,"barre_count_initialized")==V(true)&&count<n(f(*ps,"full_barre_cells_since_rest"))&&rest!=V(true))return false;}
 return true;
}
}
bool supports(const V& original){const auto* k=original.find("package_key");return k&&k->isString()&&table().count(k->string());}
void qualificationGuard(const std::string& key,const V& program){const auto i=table().find(key);need(i!=table().end(),"WHOLE_FORM_QUALIFIED_EXACT_KEY");const auto* expected=f(i->second,"program").find("source_qualification");if(!expected){need(!program.find("source_qualification"),"WHOLE_FORM_UNQUALIFIED_SOURCE");return;}need(f(program,"name")==V("qualified_l050_whole_form_anticipation_controls")&&f(program,"source_qualification")==*expected,"WHOLE_FORM_EXACT_SOURCE_QUALIFICATION");}
V construct(const std::string& key,const V& original,const V& context,const V& contextRef,const V& family){const auto it=table().find(key);need(it!=table().end()&&!rows.count(key)&&f(original,"package_key")==V(key),"WHOLE_FORM_EXACT_FACTORY");const auto& r=it->second;const auto& im=f(original,"implementation");need(f(im,"events")==f(r,"source_events")&&f(im,"instructions")==f(r,"source_instructions")&&contextRef==f(r,"source_context_ref")&&context.isObject(),"WHOLE_FORM_ORIGINAL_JOIN");for(const auto& binding:f(f(r,"program"),"source_family_manifest").array()){const V* matched=nullptr;for(const auto& sibling:family.array())if(f(sibling,"package_key")==f(binding,"source_key")){need(!matched,"WHOLE_FORM_FAMILY_DUPLICATE");matched=&sibling;}need(matched&&f(f(*matched,"implementation"),"events")==f(binding,"source_events")&&f(f(*matched,"implementation"),"instructions")==f(binding,"source_instructions"),"WHOLE_FORM_COMPLETE_FAMILY_JOIN");}auto pg=f(r,"program");qualificationGuard(key,pg);pg.object()["source_facts"]=im;rows.emplace(key,Row{original,pg,f(r,"flags"),f(r,"full_barre_cells_per_pass")});return pg;}
bool guard(const V& op,const V& payload,const O& saved,const O& policies){need(op.isObject()&&op.object().size()==3&&f(op,"kind")==V("b_whole_chord_form_controls"),"WHOLE_FORM_CLOSED_OPERATOR");const auto& key=f(op,"source_key").string();const auto i=rows.find(key);need(i!=rows.end(),"WHOLE_FORM_OWNED_KEY");const auto& r=i->second;const auto stage=f(op,"stage").string();const auto& nd=f(f(f(r.program,"graph"),"nodes"),stage);if(!includes(payload,f(nd,"expected")))return false;const auto* ps=retained(policies,key);
 if(stage=="form_choices")return choicesKnown(r,payload,ps);
 auto required=payload;if(stage=="repeat_or_finish")required.object().erase("actual_rest_between_capstone_passes_seconds_reported");if(!known(required))return false;
 const auto found=saved.find("form_choices");const V* choice=found==saved.end()?nullptr:&found->second;
 if(stage=="major_V_isolation_repair"){if(!ps||f(*ps,"major_V_isolation_debt")!=V(true)||f(*ps,"retained_known_negative_witness").null())return false;choice=&f(*ps,"retained_choices");}
 if(stage=="post_form_rest")return ps&&f(payload,"reported_retained_full_barre_cells_since_rest")==f(*ps,"full_barre_cells_since_rest")&&(n(f(*ps,"full_barre_cells_since_rest"))<4||f(payload,"actual_full_rest_taken_reported")==V(true));
 if(stage=="repeat_or_finish"){const auto* whole=saved.count("whole_source_form")?&saved.at("whole_source_form"):nullptr;if(!whole||!policyComplete(key,policies))return false;const auto mode=f(payload,"repeat_or_finish");if(mode==V("finish"))return true;const auto& seconds=f(payload,"actual_rest_between_capstone_passes_seconds_reported");return mode==V("repeat")&&known(seconds)&&n(seconds)>=60;}
 if(!choice||choice->null()||f(payload,"reported_chosen_muting_method")!=f(*choice,"chosen_muting_method"))return false;
 if(stage=="silent_form_preparation"&&flag(r,"partial")){O actualShapes;const auto& reported=f(payload,"reported_actual_source_shapes");const auto& source=f(f(table().at(key),"program"),"preparation_source_shapes");for(const auto& entry:source.object())actualShapes.emplace(entry.first,entry.first=="F"?shapeForExtent(r,entry.second,*choice):entry.second);if(reported!=V(actualShapes)||f(payload,"reported_chosen_F_extent")!=f(*choice,"chosen_F_extent"))return false;}
 if(stage=="whole_source_form"){
  if(ps&&f(*ps,"major_V_isolation_debt")==V(true))return false;
  if((flag(r,"four_pass")||flag(r,"qualified_anticipation"))&&f(payload,"reported_actual_pass_bpm")!=f(*choice,"chosen_manual_pass_bpm"))return false;
  if(flag(r,"partial")&&f(payload,"reported_chosen_F_extent")!=f(*choice,"chosen_F_extent"))return false;
  const auto exp=actualExpected(r,*choice);if(!includes(f(payload,"actual_ordered_contacts"),f(exp,"contacts")))return false;if(flag(r,"qualified_anticipation")&&f(payload,"reported_derived_actual_attack_count")!=f(exp,"derived_actual_attack_count"))return false;
 }
 if(stage=="actual_form_audit"&&!policyComplete(key,policies))return false;return true;
}
bool bodilyStop(const std::string& key,const V& payload){if(!rows.count(key)||!payload.isObject())return false;for(const char* s:{"pain_or_persistent_tension","numbness_reported","forearm_fatigue_reported","pressure_increasing_reported","burning_or_tingling_reported","hand_cannot_relax_after_release_reported"})if(const auto* p=payload.find(s))if(*p==V(true))return true;return false;}
void policyBefore(const std::string& key,const std::string& stage,const V& payload,O& ps){const auto i=rows.find(key);if(i==rows.end()||stage!="whole_source_form"||!loss(i->second,payload))return;auto& p=policy(ps,key);p.object()["major_V_isolation_debt"]=true;p.object()["pending_isolation_release"]=false;if(f(p,"retained_known_negative_witness").null())p.object()["retained_known_negative_witness"]=O{{"source_key",key},{"source_stage",stage},{"reported_failed_major_V_contacts",f(payload,"actual_ordered_contacts")}};}
void policyAfter(const std::string& key,const std::string& stage,const V& payload,O& ps){const auto i=rows.find(key);if(i==rows.end())return;const auto& r=i->second;auto& p=policy(ps,key);if(stage=="form_choices"){if(f(p,"major_V_isolation_debt")==V(false))p.object()["retained_choices"]=payload;if(flag(r,"barre")){p.object()["barre_count_initialized"]=true;p.object()["full_barre_cells_since_rest"]=f(payload,"prior_full_rest_taken_reported")==V(true)?V::fromInteger(0):f(payload,"prior_full_barre_cells_since_rest_reported");}}if(stage=="whole_source_form"&&flag(r,"barre")){p.object()["full_barre_cells_since_rest"]=V::fromInteger(n(f(p,"full_barre_cells_since_rest"))+n(r.cells));if(flag(r,"capstone_rest"))p.object()["completed_capstone_passes"]=V::fromInteger(n(f(p,"completed_capstone_passes"))+1);}if(stage=="post_form_rest"&&f(payload,"actual_full_rest_taken_reported")==V(true))p.object()["full_barre_cells_since_rest"]=V::fromInteger(0);if(stage=="major_V_isolation_repair")p.object()["pending_isolation_release"]=true;}
void policyReleased(O& ps){for(auto& base:ps)if(const auto* found=base.second.find("whole_chord_form"))if(f(*found,"pending_isolation_release")==V(true)){auto& p=base.second.object()["whole_chord_form"];p.object()["major_V_isolation_debt"]=false;p.object()["pending_isolation_release"]=false;p.object()["retained_known_negative_witness"]=nullptr;}}
bool policyComplete(const std::string& key,const O& ps){const auto* p=retained(ps,key);return !p||(f(*p,"major_V_isolation_debt")==V(false)&&n(f(*p,"full_barre_cells_since_rest"))<4);}
std::string policyRetryEntry(const std::string& key,const O& ps){const auto* p=retained(ps,key);return p&&f(*p,"major_V_isolation_debt")==V(true)?"major_V_isolation_repair":"";}
V policyView(const std::string& key,const O& ps){const auto* p=retained(ps,key);return p?*p:V(nullptr);}
std::size_t rowCount(){return rows.size();}
}
