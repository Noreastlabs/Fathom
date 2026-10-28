#include "L97ListeningSixControls.hpp"
#include "DeclaredManualText.hpp"
#include <GeneratedL97ListeningSixAuthority.hpp>
#include <algorithm>
#include <charconv>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
namespace fathom::tasks::manual_procedure_graph_support {
namespace {
using V=json::Value;using O=V::Object;
void need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
const V& f(const V& v,const std::string& k){const auto* p=v.find(k);need(p!=nullptr,"L97_REQUIRED_CLOSED_FIELD");return *p;}
std::string text(const V& v){need(v.isString(),"L97_DECLARED_STRING_TYPE");return v.string();}
bool yes(const V& v){return v==V(true);}
bool visible(const V& v){return v.isString()&&declared_manual_text::visibleUtf8(v.string());}
bool known(const V& v){
 if(v.null())return false;
 if(v.isString())return visible(v);
 if(v.isObject()){for(const auto& x:v.object())if(!known(x.second))return false;return true;}
 if(v.isArray()){if(v.array().empty())return false;for(const auto& x:v.array())if(!known(x))return false;return true;}
 return v.isBool()||v.isNumber();
}
bool schema(const V& s,const V& v){
 const auto& t=f(s,"type");std::set<std::string> ts;
 if(t.isString())ts.insert(t.string());else for(const auto& x:t.array())ts.insert(text(x));
 if(v.null()){need(ts.count("null"),"L97_NULLABLE_REPORT_TYPE");return true;}
 if(v.isString())need(ts.count("string"),"L97_CLOSED_STRING_TYPE");
 else if(v.isBool())need(ts.count("boolean"),"L97_CLOSED_BOOLEAN_TYPE");
 else if(v.isNumber()){
  std::int64_t a{},lo{},hi{};need(ts.count("integer")&&v.integer(a),"L97_EXACT_INT64_REPORT");
  if(const auto* p=s.find("minimum")){need(p->integer(lo)&&a>=lo,"L97_REPORT_REPRESENTATION_MINIMUM");}
  if(const auto* p=s.find("maximum")){need(p->integer(hi)&&a<=hi,"L97_REPORT_REPRESENTATION_MAXIMUM");}
 }else if(v.isArray()){
  need(ts.count("array"),"L97_CLOSED_ARRAY_TYPE");std::int64_t lo{},hi{};need(f(s,"minItems").integer(lo)&&f(s,"maxItems").integer(hi),"L97_ARRAY_TRANSPORT_BOUNDS");
  need(v.array().size()>=static_cast<std::size_t>(lo)&&v.array().size()<=static_cast<std::size_t>(hi),"L97_ARRAY_REPORT_EXTENT");for(const auto& x:v.array())schema(f(s,"items"),x);
 }else if(v.isObject()){
  need(ts.count("object")&&!yes(f(s,"additionalProperties")),"L97_CLOSED_OBJECT_TYPE");
  const auto& props=f(s,"properties");need(v.object().size()==props.object().size(),"L97_CLOSED_REPORT_KEYS");for(const auto& x:props.object())schema(x.second,f(v,x.first));
 }else need(false,"L97_REPORT_TYPE");
 if(const auto* e=s.find("enum"))need(std::find(e->array().begin(),e->array().end(),v)!=e->array().end(),"L97_CLOSED_ENUM");return true;
}
bool fullForm(const V& spans,std::int64_t bars,bool study){
 if(spans.null())return false;need(spans.isArray(),"L97_FULL_FORM_REPORTS_ARRAY");
 std::int64_t previous=0;
 for(const auto& x:spans.array()){
  std::int64_t first{},last{};if(!f(x,"first_bar").integer(first)||!f(x,"last_bar").integer(last))return false;
  // Check before adding: an INT64_MAX final span never wraps to create extra bars.
  if(previous==std::numeric_limits<std::int64_t>::max()||first!=previous+1||last<first||last>bars)return false;
  if(study&&first!=last)return false;
  if(!known(x)||!yes(f(x,"reported_compared_to_actual_recording")))return false;previous=last;
 }
 return previous==bars&&(!study||spans.array().size()==16);
}
}
std::optional<bool> l97ListeningSixGuard(const V& d,const V& p,const V& c,const V& frame,const O& saved){
 const auto* kind=d.find("kind");if(!kind||*kind!=V("l97_closed_listening_material"))return std::nullopt;
 need(d.isObject()&&d.object().size()==3,"L97_CLOSED_GUARD_DESCRIPTOR");
 const auto key=text(f(d,"source_key")),stage=text(f(d,"stage"));
 const auto* a=l97_listening_six_authority::find(key);need(a!=nullptr,"L97_EXACT_SIX_KEYS");
 if(const auto* fk=frame.find("source_key"))need(*fk==V(key),"L97_EXACT_CURRENT_FRAME");
 need(c==json::parse(a->contract),"L97_EXACT_ORIGINAL_SOURCE_CONTRACT");
 static const auto rules=[](){std::map<std::string,V> result;for(const auto& x:l97_listening_six_authority::rows)result.emplace(x.key,json::parse(x.rules));return result;}();
 const V* rule=nullptr;for(const auto& x:f(rules.at(key),"rules").array())if(f(x,"stage")==V(stage)){need(!rule,"L97_UNIQUE_STAGE");rule=&x;}need(rule!=nullptr,"L97_EXACT_SOURCE_STAGE");
 schema(O{{"type","object"},{"properties",f(*rule,"properties")},{"additionalProperties",false}},p);
 const bool study=std::string(a->profile)=="study_groove"||std::string(a->profile)=="study_harmony";
 std::set<std::string> optional{"actual_backward_work_reference","actual_repair_plan","actual_repaired_recording_reference","actual_full_repaired_replay_reported","actual_repaired_comparison"};
 for(const auto& x:p.object())if(!optional.count(x.first)&&!known(x.second))return false;
 for(const auto& x:f(*rule,"expected").object())if(f(p,x.first)!=x.second)return false;
 if(stage=="resource_setup"){
  std::int64_t bars{};if(!f(p,"actual_bar_count").integer(bars)||bars<1||(study&&bars!=16))return false;
  return f(p,"actual_recording_availability")==V("available")&&yes(f(p,"actual_offline_audio_access_reported"))&&yes(f(p,"permission_to_use_reported"))&&yes(f(p,"own_instrument_available"));
 }
 const auto setup=saved.find("resource_setup");need(setup!=saved.end(),"L97_COMMITTED_RESOURCE_SETUP");
 std::int64_t bars{};need(f(setup->second,"actual_bar_count").integer(bars)&&bars>0,"L97_RETAINED_ACTUAL_FORM_COUNT");
 if(const auto* reference=p.find("actual_recording_reference"))if(*reference!=f(setup->second,"actual_recording_reference"))return false;
 if(const auto* spans=p.find("actual_full_form_reports"))if(!fullForm(*spans,bars,study))return false;
 if(stage=="one_string_bass"){
  const auto selected=text(f(p,"actual_selected_string"));if(selected!="E"&&selected!="A"&&selected!="D"&&selected!="G"&&selected!="B"&&selected!="e")return false;
  if(!yes(f(p,"all_actual_bass_changes_retained_reported")))return false;
  for(const auto& x:f(p,"actual_bass_contacts").array()){std::int64_t bar{};if(!f(x,"bar_number").integer(bar)||bar>bars||f(x,"string")!=V(selected))return false;}
 }
 if(stage=="sing_changes"){
  if(!yes(f(p,"all_actual_changes_retained_reported")))return false;
  std::int64_t previous=0;for(const auto& x:f(p,"actual_changes").array()){std::int64_t bar{};if(!f(x,"bar_number").integer(bar)||bar<previous||bar>bars||!yes(f(x,"actual_sung_at_change_reported")))return false;previous=bar;}
 }
 if(stage=="useful_fifths"&&f(p,"fifths_useful_reported")!=f(p,"actual_fifths_added_reported"))return false;
 if(stage=="minimal_harmony"&&f(p,"extensions_useful_reported")!=f(p,"actual_extensions_added_reported"))return false;
 if(stage=="cadence_audit"){
  if(yes(f(p,"bass_was_unclear_reported")))return visible(f(p,"actual_backward_work_reference"));
  if(!f(p,"actual_backward_work_reference").null()&&!visible(f(p,"actual_backward_work_reference")))return false;
 }
 if(stage=="muted_reproduction"&&!yes(f(p,"actual_source_resemblance_reported")))return false;
 if(stage=="primary_contacts"||stage=="ghosts_mutes"){
  if(!yes(f(p,"actual_primary_map_secure_reported")))return false;
  if(stage=="primary_contacts"){
   if(!yes(f(p,"all_actual_primary_attacks_retained_reported")))return false;
   std::int64_t previous=0;for(const auto& x:f(p,"actual_primary_attacks").array()){std::int64_t bar{};if(!f(x,"bar_number").integer(bar)||bar<previous||bar>bars||f(x,"attack_kind")!=V("P"))return false;previous=bar;}
  }
  if(stage=="ghosts_mutes"){const auto old=saved.find("primary_contacts");need(old!=saved.end(),"L97_P_MAP_BEFORE_GHOSTS");if(!yes(f(old->second,"actual_primary_map_secure_reported"))||f(p,"actual_primary_map_reference")!=f(old->second,"actual_primary_contact_map"))return false;}
 }
 if(stage=="blind_form"&&(!yes(f(p,"no_chart_used_reported"))||!yes(f(p,"brief_not_consulted_this_pass_reported"))))return false;
 if(stage=="signature_map"&&study){
  const bool groove=std::string(a->profile)=="study_groove";
  const auto& material=f(p,groove?"actual_signature_rhythm":"actual_repeated_answer");
  const auto& occurrences=f(p,groove?"actual_rhythm_repeat_occurrences":"actual_answer_repeat_occurrences");
  std::set<std::pair<std::int64_t,std::string>> positions;
  for(const auto& x:occurrences.array()){std::int64_t bar{};if(!f(x,"bar_number").integer(bar)||bar<1||bar>16||f(x,"actual_repeated_material")!=material||!positions.emplace(bar,text(f(x,"actual_within_bar_position"))).second)return false;}
  if(positions.size()<2)return false;
  if(groove){std::int64_t beats{};if(!f(p,"actual_signature_rhythm_length_beats").integer(beats)||beats!=2||f(p,"actual_section_change_bars")!=V(V::Array{V::fromInteger(9)}))return false;}
  else if(!yes(f(p,"actual_comping_lead_alternation_reported")))return false;
 }
 if(stage=="record_compare_repair"){
  if(f(p,"actual_original_recording_reference")!=f(setup->second,"actual_recording_reference"))return false;
  const auto result=f(p,"actual_comparison_result");if(result==V("unknown"))return false;
  if(result==V("differences"))return visible(f(p,"actual_repair_plan"))&&visible(f(p,"actual_repaired_recording_reference"))&&yes(f(p,"actual_full_repaired_replay_reported"))&&f(p,"actual_repaired_comparison")==V("matches");
  return result==V("matches")&&f(p,"actual_repair_plan").null()&&f(p,"actual_repaired_recording_reference").null()&&f(p,"actual_full_repaired_replay_reported").null()&&f(p,"actual_repaired_comparison").null();
 }
 return true;
}
namespace {
constexpr const char* ledgerKind="l97_closed_listening_comparison_debt";
bool owed(const V& d){return yes(f(d,"known_negative"))||yes(f(d,"unresolved"));}
std::uint64_t ordinal(const V& v){need(v.isString(),"L97_PRIVATE_ORDINAL");std::uint64_t out{};const auto& s=v.string();const auto r=std::from_chars(s.data(),s.data()+s.size(),out);need(r.ec==std::errc{}&&r.ptr==s.data()+s.size(),"L97_PRIVATE_ORDINAL_EXACT");return out;}
const V* protocol(const V& program,const std::string& key){
 const auto* all=program.find("source_state_protocols");bool mentioned=false;if(all&&all->isArray())for(const auto& p:all->array())if(p.find("kind")&&f(p,"kind")==V(ledgerKind))mentioned=true;
 if(!l97ListeningOwns(key)){need(!mentioned,"L97_NO_FOREIGN_COMPARISON_PROTOCOL");return nullptr;}
 need(all&&all->isArray()&&all->array().size()==1,"L97_CLOSED_COMPARISON_PROTOCOL_COUNT");const auto& p=all->array()[0];
 need(p.isObject()&&p.object().size()==6&&f(p,"kind")==V(ledgerKind)&&f(p,"source_key")==V(key)&&f(p,"failed_node")==V("record_compare_repair")&&f(p,"repair_node")==V("record_compare_repair")&&f(p,"collection_attribution")==V("derived_agent_manual_comparison_and_repair"),"L97_CLOSED_COMPARISON_PROTOCOL");
 const auto* a=l97_listening_six_authority::find(key);need(f(f(program,"source_facts"),"original_contract")==json::parse(a->contract),"L97_POLICY_EXACT_ORIGINAL_CONTRACT");
 const auto& nodes=f(f(program,"graph"),"nodes");std::set<std::string> reports,required;
 for(const auto& x:nodes.object()){if(f(x.second,"kind")==V("report"))reports.insert(x.first);need(!x.second.find("calls"),"L97_NO_CALLER_SOURCE_PATH");}
 for(const auto& x:f(p,"full_retry_nodes").array()){need(x.isString()&&required.insert(x.string()).second,"L97_UNIQUE_FULL_RETRY_DUTY");}
 need(required==reports&&required.count("resource_setup")&&required.count("record_compare_repair"),"L97_COMPLETE_SOURCE_RETRY_PROTOCOL");return &p;
}
V& ledger(O& policies,const std::string& key){
 auto& base=policies[key];if(base.null())base=O{{"reduction_required",false},{"trigger_unresolved",false},{"reported_bpm_ceiling",nullptr}};
 if(!base.find("future_debts"))base.object()["future_debts"]=O{};
 auto& d=base.object()["future_debts"].object()[ledgerKind];if(d.null())d=O{{"known_negative",false},{"unresolved",false},{"repair_completed",false},{"activation_pass","0"},{"clear_after_release",false},{"repair_pass","0"},{"pending_repair_pass","0"},{"candidate_repair",false},{"owned_known_failure",nullptr},{"current_source_reference",nullptr},{"resolved_by_pass",nullptr}};return d;
}
const V* existing(const O& policies,const std::string& key){auto it=policies.find(key);if(it==policies.end()||!it->second.find("future_debts"))return nullptr;return f(it->second,"future_debts").find(ledgerKind);}
}
bool l97ListeningOwns(const std::string& key){return l97_listening_six_authority::find(key)!=nullptr;}
bool l97ListeningRetryTextVisible(const V& value){return visible(value);}
std::optional<bool> l97ListeningPolicyBefore(const V& program,const V& payload,const std::string& key,const std::string& node,std::uint64_t pass,O& policies){
 if(!protocol(program,key))return std::nullopt;auto& d=ledger(policies,key);
 if(owed(d)&&yes(f(d,"known_negative"))&&node=="resource_setup"){
  const auto& reference=f(f(f(d,"owned_known_failure"),"payload"),"actual_original_recording_reference");
  if(f(payload,"actual_recording_reference")!=reference)return false;
 }
 if(node=="resource_setup"&&visible(f(payload,"actual_recording_reference")))d.object()["current_source_reference"]=f(payload,"actual_recording_reference");
 if(node!="record_compare_repair")return true;
 d.object()["candidate_repair"]=false;const auto& result=f(payload,"actual_comparison_result");
 if(result.null()||result==V("unknown")){
  if(!owed(d))d.object()["activation_pass"]=std::to_string(pass);d.object()["unresolved"]=true;return false;
 }
 if(result==V("differences")){
  if(!visible(f(payload,"actual_original_recording_reference"))||f(payload,"actual_original_recording_reference")!=f(d,"current_source_reference")){
   if(!owed(d))d.object()["activation_pass"]=std::to_string(pass);d.object()["unresolved"]=true;return false;
  }
  if(yes(f(d,"known_negative"))){const auto& old=f(f(f(d,"owned_known_failure"),"payload"),"actual_original_recording_reference");if(f(payload,"actual_original_recording_reference")!=old)return false;}
  if(!owed(d))d.object()["activation_pass"]=std::to_string(pass);
  if(!yes(f(d,"known_negative")))d.object()["owned_known_failure"]=O{{"source_key",key},{"node",node},{"pass",std::to_string(pass)},{"pass_tag",node},{"payload",payload}};
  d.object()["known_negative"]=true;
  // Every fresh known-negative report needs its own repair and owned release.
  // Retain the original source/failure witness rather than paying it with a later positive.
  d.object()["repair_completed"]=false;d.object()["clear_after_release"]=false;
  const bool repair=visible(f(payload,"actual_repair_plan"))&&visible(f(payload,"actual_repaired_recording_reference"))&&yes(f(payload,"actual_full_repaired_replay_reported"))&&f(payload,"actual_repaired_comparison")==V("matches")&&f(payload,"actual_repaired_recording_reference")!=f(payload,"actual_reconstruction_recording_reference");
  d.object()["candidate_repair"]=repair;d.object()["pending_repair_pass"]=std::to_string(pass);return repair;
 }
 need(result==V("matches"),"L97_CLOSED_KNOWN_COMPARISON");
 if(yes(f(d,"known_negative"))){
  if(!yes(f(d,"repair_completed")))return false;
  return f(payload,"actual_original_recording_reference")==f(f(f(d,"owned_known_failure"),"payload"),"actual_original_recording_reference");
 }
 return true;
}
bool l97ListeningPolicyAfter(const V& program,const std::string& key,const std::string& node,std::uint64_t pass,O& policies){
 if(!protocol(program,key))return false;auto& d=ledger(policies,key);
 if(node=="record_compare_repair"&&yes(f(d,"candidate_repair"))){need(ordinal(f(d,"pending_repair_pass"))==pass,"L97_REPAIR_CURRENT_PASS");d.object()["clear_after_release"]=true;}
 return true;
}
void l97ListeningPolicyReleased(O& policies){for(auto& base:policies){if(!l97ListeningOwns(base.first))continue;const auto* present=existing(policies,base.first);if(!present)continue;auto& d=ledger(policies,base.first);if(yes(f(d,"clear_after_release"))){d.object()["repair_completed"]=true;d.object()["repair_pass"]=f(d,"pending_repair_pass");d.object()["clear_after_release"]=false;d.object()["candidate_repair"]=false;}}}
V l97ListeningDebtView(const O& policies,const std::string& key){const auto* d=existing(policies,key);if(!d)return V::Array{};return V::Array{O{{"duty","Retained reported comparison differences require a concrete full repair, owned release, then a distinct fresh complete reconstruction and comparison. Unknown results require a complete known retry."},{"collection_attribution","derived_agent_manual_comparison_and_repair"},{"known_negative_report_retained",f(*d,"known_negative")},{"unknown_report_retained",f(*d,"unresolved")},{"repair_reported_after_owned_release",f(*d,"repair_completed")},{"remains_due",owed(*d)},{"observation_claim",false},{"actual_recording_supplied",false}}};}
std::optional<bool> l97ListeningPolicyComplete(const V& program,const std::string& key,std::uint64_t pass,const std::set<std::string>& committed,O& policies){
 const auto* p=protocol(program,key);if(!p)return std::nullopt;auto& d=ledger(policies,key);if(!owed(d))return true;
 bool full=pass>ordinal(f(d,"activation_pass"));for(const auto& x:f(*p,"full_retry_nodes").array())full=full&&committed.count(x.string());
 if(yes(f(d,"known_negative")))full=full&&yes(f(d,"repair_completed"))&&pass>ordinal(f(d,"repair_pass"));
 if(full){d.object()["known_negative"]=false;d.object()["unresolved"]=false;d.object()["repair_completed"]=false;d.object()["resolved_by_pass"]=std::to_string(pass);}return full;
}
}
