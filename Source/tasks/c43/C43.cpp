#include "C43.hpp"
#include "GeneratedC43.hpp"
#include "ClosedKernel.hpp"
#include <algorithm>
#include <atomic>
#include <filesystem>
#include <mutex>
#include <set>
#include <stdexcept>
#include <chrono>
#include <type_traits>
#include "content/Canonical.hpp"
namespace fathom::tasks::c43 {
using J=json::Value;
namespace {
[[noreturn]]void refuse(const std::string&s){throw std::runtime_error("C43:"+s);}
const J&f(const J&j,const std::string&k){auto p=j.find(k);if(!p)refuse("missing field:"+k);return*p;}
std::string s(const J&j,const std::string&k){return f(j,k).string();}
std::int64_t n(const J&j){std::int64_t v;if(!j.integer(v))refuse("strict integer");return v;}
J i(std::int64_t v){return J::fromInteger(v);}
const J&table(){static const J t=json::parse(generatedC43);return t;}
const std::string&catalogueSha(){static const auto hash=content::sha256(generatedC43);return hash;}
static_assert(std::is_nothrow_move_constructible<J>::value,"accepted command append");

J text(){return J::Object{{"type","string"},{"minLength",i(1)},{"maxLength",i(16000)}};}
J number(std::int64_t lo=0,std::int64_t hi=1000000,bool nullable=false){return J::Object{{"type",nullable?J(J::Array{"integer","null"}):J("integer")},{"minimum",i(lo)},{"maximum",i(hi)}};}
J menu(J::Array values){return J::Object{{"type","string"},{"enum",values}};}
J status(){return menu({"yes","no","uncertain"});}
J obj(J::Object p){J::Array req;for(auto&x:p)req.emplace_back(x.first);return J::Object{{"type","object"},{"properties",p},{"required",req},{"additionalProperties",false}};}
J array(J shape,int minimum,int maximum=-1){return J::Object{{"type","array"},{"items",shape},{"minItems",i(minimum)},{"maxItems",i(maximum<0?minimum:maximum)}};}
J contact(){return obj({{"string",number(1,6)},{"fret",number(0,24)},{"midi",number(0,127)}});}
J report(J::Object p){p["source_key"]=text();p["evidence_reference"]=text();p["notes"]=text();return obj(p);}
bool yes(const J&j){return j.isString()&&j.string()=="yes";}
bool allStatusesYes(const J&schema,const J&input){
 if(input.null())return f(schema,"type").isString()&&f(schema,"type").string()=="null";
 if(auto e=schema.find("enum")){auto&a=e->array();if(a==J::Array{"yes","no","uncertain"})return yes(input);}
 if(input.isObject())for(auto&p:f(schema,"properties").object())if(!allStatusesYes(p.second,f(input,p.first)))return false;
 if(input.isArray())for(auto&x:input.array())if(!allStatusesYes(f(schema,"items"),x))return false;
 return true;
}
void trimmed(const J&schema,const J&input){if(input.null())return;if(input.isString()){if(ear234::closed::unicodeStrip(input.string()).empty())refuse("blank manual text");}else if(input.isObject())for(auto&p:f(schema,"properties").object())trimmed(p.second,f(input,p.first));else if(input.isArray())for(auto&x:input.array())trimmed(f(schema,"items"),x);}
int pc(const std::string&note){
 if(note.empty())refuse("empty pitch spelling");int p;switch(note[0]){case'C':p=0;break;case'D':p=2;break;case'E':p=4;break;case'F':p=5;break;case'G':p=7;break;case'A':p=9;break;case'B':p=11;break;default:refuse("literal pitch spelling");}
 for(std::size_t k=1;k<note.size();){if(note[k]=='#'){++p;++k;}else if(note[k]=='b'){--p;++k;}else if(note.compare(k,3,"♯")==0){++p;k+=3;}else if(note.compare(k,3,"♭")==0){--p;k+=3;}else refuse("unadmitted pitch spelling");}return(p%12+12)%12;
}
std::vector<int>contacts(const J&a){static const int base[]={0,64,59,55,50,45,40};std::vector<int>m;for(auto&c:a.array()){auto string=n(f(c,"string")),fret=n(f(c,"fret")),midi=n(f(c,"midi"));if(midi!=base[string]+fret)refuse("declared contact/MIDI contradiction");m.push_back(static_cast<int>(midi));}return m;}
bool date(const std::string&d){if(d.size()!=10||d[4]!='-'||d[7]!='-')return false;for(auto k:{0,1,2,3,5,6,8,9})if(d[k]<'0'||d[k]>'9')return false;int y=std::stoi(d.substr(0,4)),m=std::stoi(d.substr(5,2)),v=std::stoi(d.substr(8,2));if(y<1||m<1||m>12)return false;int days[]={0,31,28,31,30,31,30,31,31,30,31,30,31};if(m==2&&y%4==0&&(y%100!=0||y%400==0))days[m]=29;return v>=1&&v<=days[m];}
bool zone(const std::string&z){if(z.empty()||z.front()=='/'||z.back()=='/'||z.find("..")!=std::string::npos||z.find("//")!=std::string::npos)return false;for(unsigned char c:z)if(!(c>='A'&&c<='Z')&&!(c>='a'&&c<='z')&&!(c>='0'&&c<='9')&&c!='/'&&c!='_'&&c!='-'&&c!='+')return false;std::error_code ec;return std::filesystem::is_regular_file(std::filesystem::path("/usr/share/zoneinfo")/z,ec)&&!ec;}
std::atomic<std::uint64_t>instances{1};
}
Definition::Definition(J row):key_(s(row,"source_key")),group_(s(row,"group")),binding_(std::move(row)){}
const std::vector<std::string>&keys(){static auto k=[](){std::vector<std::string>v;for(auto&r:f(table(),"rows").array())v.push_back(s(r,"source_key"));return v;}();return k;}
const Definition&definition(const std::string&k){static auto d=[](){std::map<std::string,Definition>v;for(auto&r:f(table(),"rows").array())v.emplace(s(r,"source_key"),Definition(r));return v;}();auto p=d.find(k);if(p==d.end())refuse("foreign exact key");return p->second;}
Token::Token(std::uint64_t a,std::uint64_t b,std::string k,std::string action,bool role):instance_(a),revision_(b),key_(std::move(k)),action_(std::move(action)),sourceRole_(role){}
struct Owner::Impl {
 Definition def;mutable std::mutex mutex;std::uint64_t instance{instances++};
 struct State {std::uint64_t revision{1};std::size_t cursor{};J availability,prepared,trialSource,trialAnswer,commits,worksheet;std::vector<int>zeroBlocks;int reactionStage{1},reactionTrial{},reactionCorrect{},reactionCompatible{};bool stageFailed{},releaseDebt{},sourceDebt{},revealed{},everRevealed{},failed{},done{},cancelled{};std::string pendingExit,diagnosis;std::vector<J>events;std::shared_ptr<const ear234::Owner>context;std::uint64_t contextRevision{};}st;
 J::Array journal;
 void reserveCommand(){if(journal.size()>=100000)refuse("private command limit");journal.reserve(journal.size()+1);}
 J privateState(const J&context)const {J::Array zeros;for(auto x:st.zeroBlocks)zeros.emplace_back(i(x));return J::Object{{"revision",i(st.revision)},{"cursor",i(st.cursor)},{"availability",st.availability},{"prepared",st.prepared},{"trialSource",st.trialSource},{"trialAnswer",st.trialAnswer},{"commits",st.commits},{"worksheet",st.worksheet},{"zeroBlocks",zeros},{"reactionStage",i(st.reactionStage)},{"reactionTrial",i(st.reactionTrial)},{"reactionCorrect",i(st.reactionCorrect)},{"reactionCompatible",i(st.reactionCompatible)},{"stageFailed",st.stageFailed},{"releaseDebt",st.releaseDebt},{"sourceDebt",st.sourceDebt},{"revealed",st.revealed},{"everRevealed",st.everRevealed},{"failed",st.failed},{"done",st.done},{"cancelled",st.cancelled},{"pendingExit",st.pendingExit},{"diagnosis",st.diagnosis},{"events",J::Array(st.events.begin(),st.events.end())},{"contextRevision",i(st.contextRevision)},{"current_context_sha256",context.null()?J():J(content::sha256(context.string()))}};}
 J bundle(const J&context)const{return J::Object{{"format","fathom-c43-private-continuation-v1"},{"source_key",def.sourceKey()},{"binding_sha256",content::sha256(json::stringify(def.binding()))},{"catalogue_sha256",catalogueSha()},{"journal",journal},{"current_context",context},{"state_sha256",content::sha256(json::stringify(privateState(context)))}};}
 explicit Impl(const Definition&d):def(d){if(def.group()=="legacy_Am7_guide_row")st.everRevealed=true;}
 const J&parameters()const{return f(def.binding(),"parameters");}
 const J&workflow()const{return f(f(table(),"workflows"),def.group());}
 const J&step()const{if(st.cursor>=workflow().array().size())refuse("full cursor extent");return workflow().array()[st.cursor];}
 bool ready()const{return !st.availability.null()&&!st.prepared.null()&&yes(f(st.availability,"material_available"))&&yes(f(st.availability,"compatible_exact_unit"))&&yes(f(st.prepared,"source_ready"))&&s(st.availability,"reference")==s(st.prepared,"reference");}
 J availabilitySchema()const{J::Array modes{"human_source_player","compatible_learner_supplied_recording"};if(def.group()=="mastery76"||def.group()=="mastery77")modes.emplace_back("actual_learner_evidence_ledger");return obj({{"reference",text()},{"provider_kind",menu(modes)},{"material_available",status()},{"compatible_exact_unit",status()},{"prior_source_exposure",J::Object{{"type",J::Array{"boolean","null"}}}},{"notes",text()}});}
 J prepareSchema()const{
  J::Object p{{"reference",text()},{"source_ready",status()},{"complete_compatible_source_declaration",text()},{"notes",text()}};
  if(def.group()=="literal_interval_pair"){p["start_midi"]=number(0,127);p["destination_midi"]=number(0,127);}
  if(def.group()=="auditory_delay_tonic"){p["context"]=menu({"A minor"});p["beats_per_bar"]=number(1,16);p["actual_pulse_reference"]=text();}
  if(def.group()=="mixed_command_deck"){p["selected_order"]=array(text(),18);p["order_reference"]=text();}
  return obj(p);
 }
 J coverageSchema(bool seventySeven)const{
  J::Object groups;auto&extent=f(table(),seventySeven?"coverage77":"coverage76");
  for(auto&g:extent.object()){J::Object entries;for(auto&key:g.second.array()){
   J::Object p{{"actual_evidence_kind",menu({"learner_audio_transcription_log","learner_performance_report"})},{"actual_source_reference",text()},{"full_source_duties",status()},{"complete_actual_unit",status()},{"evidence_reference",text()}};
   if(g.first=="eight_four_layer_melodies")for(auto field:{"contour","degree","rhythm","exact_pitch"})p[field]=status();
   if(g.first=="eight_delayed_questions"){p["actual_delay_bars"]=number(0,16);p["complete_question_echoed"]=status();p["no_fingering_during_delay"]=status();}
   if(g.first=="named_degree_realization"||g.first=="named_chord_tone_realization"){p["single_silent_setup"]=status();p["actual_attack_count"]=number(0,128);p["no_searching"]=status();p["heard_target_before_hand"]=status();}
   entries[key.string()]=obj(p);
  }groups[g.first]=obj(entries);}return report({{"coverage",obj(groups)}});
 }
 J daySchema(bool seventySeven)const{
  J::Object scores;for(auto field:seventySeven?std::vector<std::string>{"interval_degree_hearing","chord_function","guide_tone_singing","first_attack_accuracy","call_response_memory","complete_performance"}:std::vector<std::string>{"form","bass","harmony","rhythm","melody","arrangement"})scores[field]=number(0,2,true);
  J::Object p{{"personal_local_date",text()},{"personal_local_IANA_zone",text()},{"actual_source_reference",text()},{"bars",number(16,seventySeven?16:32,true)},{"unfamiliar_actual_source",status()},{"without_supplied_chart",status()},{"all_full_reconstruction_passes",status()},{"without_stopping_or_restart",status()},{"scores",obj(scores)},{"score_evidence_reference",text()},{"error_and_recovery",text()}};
  if(!seventySeven)p["transcription_log"]=obj({{"date",text()},{"source_length",text()},{"form",text()},{"bass",text()},{"harmony",text()},{"rhythm",text()},{"melody",text()},{"arrangement",text()},{"score",text()}});
  return report({{"days",array(obj(p),2)}});
 }
 J reactionSourceSchema()const{auto&r=f(table(),"reaction_stages").array()[st.reactionStage-1];return report({{"reference",text()},{"command_type",menu({f(r,"command_type")})},{"complete_command",text()},{"source_context",text()},{"expected_response",array(text(),1,2)},{"target_pitch_classes",array(text(),1,4)},{"actual_command_performed",status()},{"prior_source_exposure",J::Object{{"type",J::Array{"boolean","null"}}}}});}
 J reactionCommitSchema()const{
  J::Object duties;auto add=[&](const char*n){duties[n]=status();};add("complete_command_heard");add("source_order");
  int stage=st.reactionStage;if(stage<=4||stage>=11)add("sung_target_before_hand");if(stage==3||stage==7||stage==11)add("degree_or_function_named");if(stage==4||stage==8)add("chord_role_named");if(stage>=5&&stage<=7)add("two_registers_performed");if(stage==8)add("two_string_sets_performed");if(stage>=9)add("no_searching");if(stage>=9)add("single_silent_setup");if(stage==12)add("shell_after_singing");
  int min=stage>=5&&stage<=8?2:stage==12?2:1;int max=stage==12?4:min;
  return report({{"response",array(text(),1,2)},{"duties",obj(duties)},{"selected_contacts",array(contact(),min,max)},{"actual_attack_count",number(0,128)},{"first_correct_attack_ms",number(0,1000000,true)},{"timing_basis",menu({"declared_observer","actual_recording_annotation","unavailable"})},{"timing_reference",text()}});
 }
 J actionSchema()const{
  auto&sp=step();auto op=s(sp,"opcode");if(auto p=sp.find("schema")){auto result=*p;
   if(def.group()=="melodic_pitch_rhythm"&&s(sp,"action")=="commit_exact_pitches"){auto count=f(parameters(),"derived_pitch_class_sequence").array().size();auto&v=result.object()["properties"].object()["pitches"];v.object()["minItems"]=i(count);v.object()["maxItems"]=i(count);}
   if(def.group()=="melodic_pitch_rhythm"&&s(sp,"action")=="recombine_realize"){auto count=f(parameters(),"derived_pitch_class_sequence").array().size();result.object()["properties"].object()["selected_contacts"]=array(contact(),count);result.object()["required"].array().emplace_back("selected_contacts");}
   if(def.group()=="mixed_command_deck"&&s(sp,"action")=="commit_command_response"&&!f(parameters(),"complete_singing_pair_required").boolean())result.object()["properties"].object()["voice_report"]=J::Object{{"type","null"}};
   return result;
  }
  if(op=="reveal")return obj({});if(op=="context_owner")return obj({});
  if(op=="repair_blocks")return report({{"block",number(1,8)},{"complete_source_relistened",status()},{"repaired_full_block",obj({{"form",text()},{"bass",text()},{"harmony",text()},{"rhythm",text()},{"texture_dynamics",text()},{"landmarks",text()},{"confidence",number(1,2)}})}});
  if(op=="coverage76"||op=="coverage77")return coverageSchema(op=="coverage77");if(op=="days76"||op=="days77")return daySchema(op=="days77");
  if(op=="interval_ledger"){
   J::Object intervals;for(auto name:{"m2","M2","m3","M3","P4","TT","P5","m6","M6","m7","M7","P8"})intervals[name]=obj({{"ascending",obj({{"actual_reference",text()},{"correct",status()},{"evidence_reference",text()}})},{"descending",obj({{"actual_reference",text()},{"correct",status()},{"evidence_reference",text()}})}});
   return report({{"intervals",obj(intervals)}});
  }
  if(op=="progression_ledger"){
   J::Object phases,diagnoses;for(auto name:{"interval_atlas","interval_dictation","random_root_transfer","function_hearing","major_guide_tones","minor_guide_tones","melodic_dictation","call_response","timed_realization","capstone16"})phases[name]=obj({{"actual_evidence_reference",text()},{"complete",status()}});
   for(auto name:{"wrong_pitch_right_contour_interval_issue","right_pitch_after_search_neck_location","right_chord_wrong_function_context","voice_right_guitar_wrong_mapping","echo_degrades_delay_memory","fast_wrong_increase_response_window"})diagnoses[name]=obj({{"actual_diagnosis_or_not_applicable_evidence",text()},{"source_policy_retained",status()}});
   return report({{"ten_phases",obj(phases)},{"six_diagnoses",obj(diagnoses)}});
  }
  if(op=="reaction_source")return reactionSourceSchema();if(op=="reaction_commit")return reactionCommitSchema();if(op=="reaction_compare")return report({{"full_response_compared",status()},{"source_correct",status()},{"diagnosis",text()}});
  refuse("unknown closed operator");
 }
 J actions(bool source=false)const{
  J::Object out;if(source){if(!st.done&&!st.cancelled&&!st.releaseDebt&&!st.sourceDebt&&st.pendingExit.empty()){
   if(st.cursor==0&&st.commits.null()&&st.reactionStage==1&&st.reactionTrial==0)out["prepare_source"]=prepareSchema();if(ready()&&!st.stageFailed&&s(step(),"opcode")=="reaction_source")out[s(step(),"action")]=actionSchema();}return out;}
  if(!st.done)out["availability"]=availabilitySchema();out["stop"]=obj({{"reason",text()}});out["navigate"]=obj({{"reason",text()}});out["restart_owned_trial"]=obj({{"reason",text()}});
  if(st.releaseDebt||st.sourceDebt)out["release"]=obj({{"learner_released",status()},{"source_stopped",status()},{"notes",text()}});
  if(st.cancelled)out["reopen"]=obj({{"reason",text()}});
  if(st.done||st.cancelled||!st.pendingExit.empty()||!ready()||st.releaseDebt||st.sourceDebt)return out;
  if(st.stageFailed){out["repeat_reaction_stage"]=obj({{"reason",text()}});return out;}
  if(st.failed){out["retry_step"]=obj({{"reason",text()}});out["retry_complete_unit"]=obj({{"reason",text()}});if(def.group()=="twelve_stage_reaction")out["retry_reaction_trial"]=obj({{"reason",text()}});return out;}
  if(s(step(),"opcode")!="reaction_source")out[s(step(),"action")]=actionSchema();return out;
 }
 bool contextCurrent()const{if(!st.context)return false;auto v=st.context->learnerView();return static_cast<std::uint64_t>(n(f(v,"revision")))==st.contextRevision&&s(v,"state")=="completed"&&!f(v,"manual_release_debt").boolean()&&!f(v,"external_source_stop_debt").boolean();}
 J view()const{
  J::Object out{{"source_key",def.sourceKey()},{"group",def.group()},{"revision",i(st.revision)},{"state",st.done?"completed":st.cancelled?"cancelled":!st.pendingExit.empty()?"awaiting_exit_release":st.stageFailed?"reaction_stage_debt":st.failed?"source_duty_debt":!ready()?"awaiting_external_reference":"current_source_workflow"},{"workflow_position",i(st.cursor)},{"manual_release_debt",st.releaseDebt},{"external_source_stop_debt",st.sourceDebt},{"prior_reference_disclosure",st.everRevealed},{"explicit_current_reference_disclosure",st.revealed},{"availability_report",st.availability},{"source_assets_supplied",false},{"source_audio_supplied",false},{"performance_observed",false},{"automatic_credit",false},{"mastery_awarded",false},{"runtime_admitted",false},{"source_clock",nullptr},{"blind_trial_claim",false},{"source_index_authority",f(f(table(),"authority"),"SourceIndex")},{"diagnosis",st.diagnosis},{"context_complete_and_current",contextCurrent()}};
  if(!st.done&&!st.cancelled){out["instruction"]=f(step(),"cue");out["current_action"]=f(step(),"action");}
  out["current_reference"]=st.revealed?J(J::Object{{"original_parameters",parameters()},{"Root_selected_interpretation",f(f(table(),"groups"),def.group())},{"original_source",f(f(table(),"contexts"),s(def.binding(),"context_key"))}}):J();
  if(def.group()=="mixed_command_deck"&&ready())out["current_command_prompt"]=f(parameters(),"source_command");
  if(def.group()=="legacy_Am7_guide_row")out["public_study_row"]=J::Object{{"observed_original_row",f(parameters(),"resolved_original_row")},{"legacy_inventory_label",f(parameters(),"legacy_label")},{"separate_row6_key",f(parameters(),"separate_row6_key_preserved")},{"blind_exercise",false}};
  if(def.group()=="capstone32"){J::Array pending;for(auto b:st.zeroBlocks)pending.push_back(i(b));out["confidence_zero_blocks"]=pending;out["learner_worksheet"]=st.worksheet;}
  if(def.group()=="twelve_stage_reaction"){out["stage"]=i(st.reactionStage);out["trial_in_stage"]=i(st.reactionTrial+1);out["reported_correct_trials"]=i(st.reactionCorrect);out["reported_correct_with_compatible_timing"]=i(st.reactionCompatible);out["source_stage_cue"]=f(table(),"reaction_stages").array()[st.reactionStage-1];if(!st.trialSource.null())out["current_complete_command"]=f(st.trialSource,"complete_command");if(st.revealed)out["current_declared_target"]=st.trialSource;}
  return out;
 }
 bool physicalValid(const J&sp,const J&input)const{
  auto c=input.find("selected_contacts");if(!c)return true;auto midi=contacts(*c);auto rule=sp.find("contact_targets");if(!rule){if(def.group()=="melodic_pitch_rhythm"&&s(sp,"action")=="recombine_realize"){auto& pitches=f(f(st.commits,"commit_exact_pitches"),"pitches").array();for(std::size_t x=0;x<midi.size();++x)if(midi[x]%12!=pc(pitches[x].string()))return false;}return true;}auto r=rule->string();
  if(r=="literal_destination"){if(midi.size()!=1||midi[0]%12!=pc("D")||midi[0]!=n(f(st.prepared,"destination_midi")))return false;}
  if(r=="guides"){auto&g=f(parameters(),"guide_notes").array();for(std::size_t x=0;x<midi.size();++x)if(midi[x]%12!=pc(g[x].string()))return false;}
  // Before reveal, check only the learner's own declared pitch/contact relation.
  // The hidden original question is compared only after explicit owned reveal.
  if(r=="question"){auto&q=f(input,"pitches").array();for(std::size_t x=0;x<midi.size();++x)if(midi[x]%12!=pc(q[x].string()))return false;}
  if(r=="tonic_triad"){auto p=pc(s(f(parameters(),"derived_unplayed_terminal_target"),"key"));std::multiset<int>a;for(auto m:midi)a.insert(m%12);if(a!=std::multiset<int>{p,(p+4)%12,(p+7)%12})return false;}
  if(auto a=input.find("actual_attack_count"))if(r=="literal_destination"||r=="tonic_triad")if(n(*a)!=1)return false;
  return true;
 }
 bool coverageValid(const J&input)const{
  auto&c=f(input,"coverage");for(auto&g:c.object())for(auto&entry:g.second.object()){
   auto&p=entry.second;if(auto a=p.find("actual_delay_bars"))if(n(*a)!=1)return false;if(auto a=p.find("actual_attack_count"))if(n(*a)!=1)return false;
  }return true;
 }
 bool daysValid(const J&input,bool seventySeven)const{
  auto&days=f(input,"days").array();auto firstDate=s(days[0],"personal_local_date"),secondDate=s(days[1],"personal_local_date"),z=s(days[0],"personal_local_IANA_zone");
  if(!date(firstDate)||!date(secondDate)||firstDate==secondDate||!zone(z)||z!=s(days[1],"personal_local_IANA_zone"))return false;
  for(auto&d:days){if(f(d,"bars").null())return false;int total=0;for(auto&p:f(d,"scores").object()){if(p.second.null())return false;total+=static_cast<int>(n(p.second));if(!seventySeven&&(p.first=="form"||p.first=="bass"||p.first=="harmony"||p.first=="rhythm")&&n(p.second)==0)return false;}if(total<10)return false;if(!seventySeven&&s(f(d,"transcription_log"),"date")!=s(d,"personal_local_date"))return false;}
  return true;
 }
 bool symbolicMatches()const{
  auto find=[&](const char*action,const char*field)->const J*{auto a=st.commits.find(action);return a?a->find(field):nullptr;};auto eq=[&](const J*a,const J&b){return a&&*a==b;};auto g=def.group();
  if(g=="altered_fifth_quality")return eq(find("commit_quality","quality"),f(parameters(),"source_quality_answer"));
  if(g=="literal_interval_pair")return eq(find("commit_interval_quality","interval_quality"),f(parameters(),"derived_literal_pair_interval"))&&eq(find("commit_destination","destination"),f(f(parameters(),"source_fields"),"Destination"));
  if(g=="derived_terminal_tonic"){
   J::Array functions,romans;for(auto&r:f(parameters(),"original_four_slots").array()){functions.push_back(f(r,"function"));romans.push_back(f(r,"roman"));}
   return eq(find("commit_functions","functions"),functions)&&eq(find("commit_romans","romans"),romans)&&eq(find("sing_tonic","tonic"),f(f(parameters(),"derived_unplayed_terminal_target"),"key"));
  }
  if(g=="legacy_Am7_guide_row")return eq(find("commit_sung_guides","guide_notes"),f(parameters(),"guide_notes"))&&contextCurrent();
  if(g=="melodic_pitch_rhythm")return eq(find("commit_exact_pitches","pitches"),f(parameters(),"derived_pitch_class_sequence"));
  if(g=="auditory_delay_tonic")return eq(find("commit_sung_tonic","tonic"),f(parameters(),"derived_tonic"))&&eq(find("reproduce_complete_question","pitches"),f(parameters(),"source_question"));
  if(g=="mixed_command_deck"){auto*r=find("commit_command_response","response");auto expected=f(parameters(),"derived_comparison_key");if(expected.isString())expected=J::Array{expected};return eq(r,expected);}
  return true;
 }
 void process(const std::string&action,const J&input,bool sourceRole){
  if(action=="availability"){if(!st.prepared.null()&&(st.cursor>0||!st.commits.null()||st.reactionTrial>0||st.reactionStage>1)&&s(input,"reference")!=s(st.prepared,"reference"))refuse("source reference change requires owned whole-unit restart");st.availability=input;return;}
  if(action=="prepare_source"){
   if(def.group()=="literal_interval_pair"){auto a=n(f(input,"start_midi")),b=n(f(input,"destination_midi"));if(a%12!=pc("B")||b%12!=pc("D")||a-b!=9)refuse("literal B-to-lower-D derived within-octave pair");}
   if(def.group()=="mixed_command_deck"){std::set<std::string>expected,actual;for(auto&r:f(table(),"rows").array())if(s(r,"group")=="mixed_command_deck")expected.insert(s(r,"source_key"));for(auto&k:f(input,"selected_order").array())actual.insert(k.string());if(actual!=expected||actual.size()!=18)refuse("exact eighteen-card selected order");}
   st.prepared=input;return;
  }
  if(action=="stop"||action=="navigate"||action=="restart_owned_trial"){
   if(st.releaseDebt||st.sourceDebt)st.pendingExit=action;else exit(action);return;
  }
  if(action=="release"){
   if(!yes(f(input,"learner_released"))||!yes(f(input,"source_stopped"))){st.diagnosis="Actual learner/source release remains unresolved";return;}
   st.releaseDebt=false;st.sourceDebt=false;if(!st.pendingExit.empty()){auto action=st.pendingExit;st.pendingExit.clear();exit(action);}return;
  }
  if(action=="reopen"){st.cancelled=false;st.failed=false;return;}
  if(action=="retry_step"){st.failed=false;st.diagnosis.clear();return;}
  if(action=="retry_complete_unit"){auto events=st.events;auto ever=st.everRevealed;auto revision=st.revision;auto availability=st.availability,prepared=st.prepared;st=State{};st.events=std::move(events);st.everRevealed=ever;st.revision=revision;st.availability=std::move(availability);st.prepared=std::move(prepared);return;}
  if(action=="retry_reaction_trial"){st.failed=false;st.cursor=0;st.trialSource=J();st.trialAnswer=J();st.revealed=false;st.diagnosis.clear();return;}
  if(action=="repeat_reaction_stage"){st.stageFailed=false;st.reactionTrial=st.reactionCorrect=st.reactionCompatible=0;st.cursor=0;st.trialSource=J();st.trialAnswer=J();st.revealed=false;return;}
  auto&sp=step();auto op=s(sp,"opcode");
  if(op=="context_owner")refuse("use actual context-owner API");
  if(op=="reveal"){st.revealed=true;st.everRevealed=true;++st.cursor;return;}
  if(op=="reaction_source"){
   if(!sourceRole)refuse("trusted caller required");for(auto&p:f(input,"target_pitch_classes").array())pc(p.string());if(s(input,"reference")!=s(st.availability,"reference"))refuse("current reference mismatch");
   if(st.reactionStage<12&&f(input,"target_pitch_classes").array().size()!=1)refuse("single target pitch-class extent for this stage");
   if(st.reactionStage==12){
    const auto&declared=f(input,"target_pitch_classes").array();std::set<int>unique;
    for(const auto&p:declared)unique.insert(pc(p.string()));
    if(unique.size()<2||unique.size()!=declared.size())refuse("explicit unique full shell pitch-class extent");
   }
   if(!yes(f(input,"actual_command_performed"))){st.failed=true;st.diagnosis="Actual command performance unknown";return;}st.trialSource=input;st.revealed=false;++st.cursor;return;
  }
  if(op=="reaction_commit"){
   contacts(f(input,"selected_contacts"));st.trialAnswer=input;st.releaseDebt=true;st.sourceDebt=true;++st.cursor;return;
  }
  bool positive=allStatusesYes(actionSchema(),input);if(auto key=input.find("source_key"))if(key->string()!=def.sourceKey())refuse("foreign source-key report");
  if(op=="worksheet"){
   st.worksheet=f(input,"blocks");st.zeroBlocks.clear();for(std::size_t b=0;b<st.worksheet.array().size();++b)if(n(f(st.worksheet.array()[b],"confidence"))==0)st.zeroBlocks.push_back(static_cast<int>(b+1));++st.cursor;if(st.zeroBlocks.empty())++st.cursor;return;
  }
  if(op=="repair_blocks"){
   int b=static_cast<int>(n(f(input,"block")));auto it=std::find(st.zeroBlocks.begin(),st.zeroBlocks.end(),b);if(it==st.zeroBlocks.end())refuse("not a pending zero-confidence block");if(positive){st.worksheet.array()[b-1]=f(input,"repaired_full_block");st.zeroBlocks.erase(it);if(st.zeroBlocks.empty())++st.cursor;}else{st.failed=true;st.diagnosis="Confidence-zero repair remains debt";}return;
  }
  if(op=="physical"){positive&=physicalValid(sp,input);st.releaseDebt=true;st.sourceDebt=true;}
  if(op=="delay")positive&=n(f(input,"actual_delay_bars"))==1;
  if(op=="deck_commit"){
   auto count=f(parameters(),"derived_comparison_key").isArray()?f(parameters(),"derived_comparison_key").array().size():1;
   if(f(input,"response").array().size()!=count)refuse("complete command answer extent");if(f(parameters(),"complete_singing_pair_required").boolean())positive&=yes(f(input,"voice_report"));
   positive&=!f(input,"reaction_ms").null()&&n(f(input,"reaction_ms"))<=4000&&s(input,"timing_basis")!="unavailable";
  }
  if(op=="coverage76"||op=="coverage77")positive&=coverageValid(input);
  if(op=="days76"||op=="days77")positive&=daysValid(input,op=="days77");
  if(op=="interval_ledger"){
   int correct=0;positive=true;for(auto&p:f(input,"intervals").object())for(auto&dir:p.second.object()){auto&c=f(dir.second,"correct");if(c.string()=="uncertain")positive=false;if(yes(c))++correct;}positive&=correct>=22;
  }
  if(op=="rubric32"){int total=0;for(auto field:{"form","bass","harmony","rhythm","melodic_targets","arrangement"})total+=static_cast<int>(n(f(input,field)));positive&=total>=10;for(auto field:{"form","bass","harmony","rhythm"})positive&=n(f(input,field))>0;}
  if(op=="rubric16"){/* source capstone alone has no invented two-day threshold */}
  if(op=="compare")positive&=symbolicMatches();
  if(op=="complete")positive&=(!st.releaseDebt&&!st.sourceDebt)&&(def.group()!="legacy_Am7_guide_row"||contextCurrent());
  if(op=="reaction_compare"){
   if(st.trialAnswer.null()||st.trialSource.null())refuse("missing actual trial custody");auto&answer=st.trialAnswer;auto&sr=st.trialSource;
   if(!yes(f(input,"full_response_compared"))||s(input,"source_correct")=="uncertain"||(yes(f(input,"source_correct"))&&(f(answer,"first_correct_attack_ms").null()||s(answer,"timing_basis")=="unavailable"))){st.failed=true;st.diagnosis="Actual comparison/timing unknown";return;}
   bool correct=yes(f(input,"source_correct"))&&f(answer,"response")==f(sr,"expected_response");for(auto&d:f(answer,"duties").object())correct&=yes(d.second);
   auto midi=contacts(f(answer,"selected_contacts"));std::set<int>expected;for(auto&p:f(sr,"target_pitch_classes").array())expected.insert(pc(p.string()));
   std::set<int>actual;for(auto m:midi){correct&=expected.count(m%12)>0;actual.insert(m%12);}
   // A sung guide tone is retained separately in expected_response. The played
   // shell must realize every declared target exactly once; duplicate octave
   // contacts cannot substitute for missing shell members.
   if(st.reactionStage==12)correct&=actual==expected&&midi.size()==expected.size();
   if(st.reactionStage>=5&&st.reactionStage<=7)correct&=midi.size()==2&&midi[0]!=midi[1];
   if(st.reactionStage==8)correct&=n(f(f(answer,"selected_contacts").array()[0],"string"))!=n(f(f(answer,"selected_contacts").array()[1],"string"));
   if(st.reactionStage>=9&&st.reactionStage<=11)correct&=n(f(answer,"actual_attack_count"))==1;else correct&=n(f(answer,"actual_attack_count"))>0;
   if(correct)++st.reactionCorrect;auto limit=n(f(f(table(),"reaction_stages").array()[st.reactionStage-1],"limit_seconds"))*1000;
   if(correct&&!f(answer,"first_correct_attack_ms").null()&&n(f(answer,"first_correct_attack_ms"))<=limit)++st.reactionCompatible;
   ++st.reactionTrial;
   if(st.reactionTrial<10){st.cursor=0;st.trialSource=J();st.trialAnswer=J();st.revealed=false;return;}
   if(st.reactionCorrect<9||st.reactionCompatible<9){st.stageFailed=true;st.diagnosis="Stage needs at least nine of ten reported correct with compatible timing";return;}
   if(st.reactionStage<12){++st.reactionStage;st.reactionTrial=st.reactionCorrect=st.reactionCompatible=0;st.cursor=0;st.trialSource=J();st.trialAnswer=J();st.revealed=false;return;}
   ++st.cursor;return;
  }
  if(!positive){st.failed=true;st.diagnosis="Negative/unknown source duty or symbolic comparison remains explicit debt";return;}
  if(op=="commit"||op=="deck_commit"||op=="physical"){
   if(!st.commits.isObject())st.commits=J::Object{};st.commits.object()[action]=input;
  }
  if(op=="complete"){st.done=true;return;}++st.cursor;
  if(st.cursor<workflow().array().size()&&s(step(),"opcode")=="reveal"&&def.group()!="mastery76"&&def.group()!="mastery77")st.sourceDebt=true;
 }
 void exit(const std::string&action){
  if(action=="restart_owned_trial"){auto events=st.events;auto ever=st.everRevealed;auto revision=st.revision;st=State{};st.events=std::move(events);st.everRevealed=ever;st.revision=revision;}
  else st.cancelled=true;
 }
};
Owner::Owner(const Definition&d):impl_(std::make_unique<Impl>(d)){}Owner::~Owner()=default;
Token Owner::capture(const std::string&action)const{std::lock_guard<std::mutex>l(impl_->mutex);if(!impl_->actions().find(action))refuse("current learner action unavailable");return Token(impl_->instance,impl_->st.revision,impl_->def.sourceKey(),action,false);}
Token Owner::captureSourceChoices(const std::string&action)const{std::lock_guard<std::mutex>l(impl_->mutex);if(!impl_->actions(true).find(action))refuse("current trusted source action unavailable");return Token(impl_->instance,impl_->st.revision,impl_->def.sourceKey(),action,true);}
bool Owner::current(const Token&t)const{std::lock_guard<std::mutex>l(impl_->mutex);return t.instance_==impl_->instance&&t.revision_==impl_->st.revision&&t.key_==impl_->def.sourceKey()&&impl_->actions(t.sourceRole_).find(t.action_);}
void Owner::apply(const Token&t,const J&input){
 std::lock_guard<std::mutex>l(impl_->mutex);auto&i=*impl_;if(t.instance_!=i.instance||t.revision_!=i.st.revision||t.key_!=i.def.sourceKey())refuse("stale/foreign gesture");auto actions=i.actions(t.sourceRole_);auto schema=actions.find(t.action_);if(!schema)refuse("current action unavailable");ear234::validateTypedInput(*schema,input);trimmed(*schema,input);if(auto key=input.find("source_key"))if(key->string()!=i.def.sourceKey())refuse("foreign source-key report");
 i.reserveCommand();J contextAtCommand;if(i.st.context)contextAtCommand=i.st.context->continuation();J command=J::Object{{"kind","apply"},{"action",t.action_},{"source_role",t.sourceRole_},{"input",input},{"context",contextAtCommand}};
 auto previous=i.st;try{i.process(t.action_,input,t.sourceRole_);++i.st.revision;i.st.events.emplace_back(J::Object{{"source_key",i.def.sourceKey()},{"revision",::fathom::json::Value::fromInteger(i.st.revision)},{"action",t.action_},{"role",t.sourceRole_?"trusted_source_player":"learner"},{"report",t.sourceRole_?J("private source choice retained separately"):input},{"source_clock",nullptr},{"performance_observed",false}});i.journal.push_back(std::move(command));}catch(...){i.st=std::move(previous);throw;}
}
void Owner::attachContextCompletion(const Token&t,std::shared_ptr<const ear234::Owner>other){
 std::lock_guard<std::mutex>l(impl_->mutex);auto&i=*impl_;if(t.sourceRole_||t.instance_!=i.instance||t.revision_!=i.st.revision||t.key_!=i.def.sourceKey()||t.action_!="attach_complete_context"||!i.actions().find(t.action_))refuse("current context gesture");if(!other)refuse("missing actual context owner");auto&expected=f(i.def.binding(),"required_complete_context_owner");auto&d=other->retainedDefinition();auto v=other->learnerView();if(d.sourceKey()!=s(expected,"source_key")||d.contractSha256()!=s(expected,"contract_sha256")||s(v,"state")!="completed"||f(v,"manual_release_debt").boolean()||f(v,"external_source_stop_debt").boolean())refuse("complete exact released contextual source owner required");
 const auto peer=other->continuation();
 if(other->learnerView()!=v)refuse("context changed during attachment snapshot");
 i.reserveCommand();J command=J::Object{{"kind","context"},{"snapshot",peer}};auto previous=i.st;
 try{i.st.context=std::move(other);i.st.contextRevision=static_cast<std::uint64_t>(n(f(v,"revision")));++i.st.cursor;++i.st.revision;i.st.events.emplace_back(J::Object{{"action","attach_complete_context"},{"context_source_key",d.sourceKey()},{"context_contract_sha256",d.contractSha256()},{"context_revision",f(v,"revision")},{"observed_performance",false}});i.journal.push_back(std::move(command));}catch(...){i.st=std::move(previous);throw;}

}
J Owner::learnerView()const{std::lock_guard<std::mutex>l(impl_->mutex);return impl_->view();}
J Owner::learnerActions()const{std::lock_guard<std::mutex>l(impl_->mutex);return impl_->actions();}
J Owner::sourcePlayerView()const{std::lock_guard<std::mutex>l(impl_->mutex);auto&i=*impl_;return J::Object{{"role","trusted_source_player"},{"original_parameters",i.parameters()},{"original_source",f(f(table(),"contexts"),s(i.def.binding(),"context_key"))},{"Root_selected_interpretation",f(f(table(),"groups"),i.def.group())},{"source_choice_forms",i.actions(true)},{"saved_source_choices",i.st.prepared},{"current_trial_source",i.st.trialSource},{"actual_source_supplied_by_application",false}};}
std::vector<J>Owner::history()const{std::lock_guard<std::mutex>l(impl_->mutex);return impl_->st.events;}
bool Owner::fenceInactiveForNavigation(){std::lock_guard<std::mutex>l(impl_->mutex);auto&owner=*impl_;if(owner.st.releaseDebt||owner.st.sourceDebt)return false;owner.reserveCommand();J command=J::Object{{"kind","inactive_fence"}};auto previous=owner.st;try{owner.st.cancelled=true;++owner.st.revision;owner.st.events.emplace_back(J::Object{{"action","inactive_navigation_fence"},{"source_key",owner.def.sourceKey()},{"revision",i(owner.st.revision)},{"source_clock",nullptr},{"performance_observed",false}});owner.journal.push_back(std::move(command));return true;}catch(...){owner.st=std::move(previous);throw;}}

const Definition&Owner::retainedDefinition()const noexcept{return impl_->def;}
namespace {
json::Limits continuationLimits(){json::Limits l;l.bytes=64*1024*1024;l.stringBytes=64*1024*1024;l.depth=96;l.values=2000000;return l;}
std::string envelope(const J& b){return json::stringify(J::Object{{"body",b},{"sha256",content::sha256(json::stringify(b))}});}
}
std::string Owner::continuation()const {
 J body;{std::lock_guard<std::mutex>l(impl_->mutex);J context;if(impl_->st.context)context=impl_->st.context->continuation();body=impl_->bundle(context);}
 auto bytes=envelope(body);json::parse(bytes,continuationLimits());auto verified=restoreContinuation(impl_->def,bytes);
 return bytes;
}
RestoredOwner Owner::restoreContinuation(const Definition&def,const std::string&bytes,const ear234::Owner::ContinuationResolver& supplied){
 auto e=json::parse(bytes,continuationLimits());if(!e.isObject()||e.object().size()!=2||s(e,"sha256")!=content::sha256(json::stringify(f(e,"body"))))refuse("private envelope/checksum");const auto&b=f(e,"body");
 if(!b.isObject()||b.object().size()!=7||s(b,"format")!="fathom-c43-private-continuation-v1"||s(b,"source_key")!=def.sourceKey()||s(b,"binding_sha256")!=content::sha256(json::stringify(def.binding()))||s(b,"catalogue_sha256")!=catalogueSha())refuse("private source/format/catalogue differs; original preserved");
 auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(10);RestoredOwner result;result.owner=std::make_unique<Owner>(def);auto&out=*result.owner;
 const auto resolve=[&](const std::string& key)->const ear234::Definition&{return supplied?supplied(key):ear234::definition(key);};
 auto restorePeer=[&](const std::string& snapshot){const auto root=json::parse(snapshot,continuationLimits());const auto key=s(f(root,"body"),"source_key");return ear234::Owner::restoreContinuation(resolve(key),snapshot,supplied);};
 J attachment;
 const auto bindCurrent=[&](const J&current){
  if(current.null()){if(out.impl_->st.context)refuse("attached context absent at command boundary");result.context.reset();return;}
  if(attachment.null()||!out.impl_->st.context)refuse("current context without guarded attachment");
  auto peer=restorePeer(current.string());auto currentEnvelope=json::parse(current.string(),continuationLimits());const auto&oldBody=f(attachment,"body");const auto&nowBody=f(currentEnvelope,"body");
  if(f(oldBody,"source_key")!=f(nowBody,"source_key")||f(oldBody,"binding_sha256")!=f(nowBody,"binding_sha256"))refuse("current context foreign lineage");
  const auto&oldCommands=f(oldBody,"journal").array();const auto&nowCommands=f(nowBody,"journal").array();if(nowCommands.size()<oldCommands.size()||!std::equal(oldCommands.begin(),oldCommands.end(),nowCommands.begin()))refuse("current context is not a continuation of actual attachment");
  result.context=std::shared_ptr<ear234::Owner>(std::move(peer));out.impl_->st.context=result.context;
 };
 if(f(b,"journal").array().size()>100000)refuse("private replay command limit");
 for(const auto& command:f(b,"journal").array()){
  if(std::chrono::steady_clock::now()>deadline)refuse("private replay time limit");const auto kind=s(command,"kind");
  if(kind=="apply"&&command.object().size()==5){bindCurrent(f(command,"context"));auto token=f(command,"source_role").boolean()?out.captureSourceChoices(s(command,"action")):out.capture(s(command,"action"));out.apply(token,f(command,"input"));}
  else if(kind=="inactive_fence"&&command.object().size()==1){if(!out.fenceInactiveForNavigation())refuse("private inactive fence differs");}
  else if(kind=="context"&&command.object().size()==2){auto peer=restorePeer(s(command,"snapshot"));attachment=json::parse(s(command,"snapshot"),continuationLimits());result.context=std::shared_ptr<ear234::Owner>(std::move(peer));out.attachContextCompletion(out.capture("attach_complete_context"),result.context);}
  else refuse("private replay command shape/kind");
 }
 const auto&current=f(b,"current_context");
 // Rebind only the actual dependency; preserve C43's attachment revision.
 bindCurrent(current);
 if(out.impl_->journal!=f(b,"journal").array()||content::sha256(json::stringify(out.impl_->privateState(current)))!=s(b,"state_sha256"))refuse("private native replay differs");
 if(std::chrono::steady_clock::now()>deadline)refuse("private replay time limit");return result;
}

}
