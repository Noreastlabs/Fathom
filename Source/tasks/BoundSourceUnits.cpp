#include "tasks/BoundSourceUnits.hpp"
#include "tasks/HarmonizedTriadControls.hpp"
#include "tasks/Level68SourceControls.hpp"
#include "tasks/BeginnerSourceControls.hpp"
#include "tasks/SeventhFamilyControls.hpp"
#include "tasks/RhythmGridControls.hpp"
#include "tasks/SourcePhraseControls.hpp"
#include "tasks/DiagonalRouteControls.hpp"
#include "tasks/AnticipationGridControls.hpp"
#include "tasks/ProgressionCircleControls.hpp"
#include "tasks/AnticipationLadderControls.hpp"
#include "tasks/TimedChordChangeControls.hpp"
#include "tasks/CompiledChordSessionControls.hpp"
#include "tasks/WholeChordFormControls.hpp"
#include "tasks/PracticalTriadControls.hpp"
#include "tasks/MelodicFunctionControls.hpp"
#include "tasks/SourceMapControls.hpp"
#include "tasks/PhraseApplicationControls.hpp"
#include "tasks/IntervalRecoveryControls.hpp"
#include "tasks/SourceTaskControls.hpp"
#include "tasks/QualifiedSourceControls.hpp"
#include "tasks/DimContextControls.hpp"
#include "tasks/RootlessSeventhControls.hpp"
#include "tasks/TimedAssessmentControls.hpp"
#include "tasks/SourceFormControls.hpp"
#include "content/Canonical.hpp"
#include <GeneratedRootlessSelectedCustody.hpp>
#include <SupportingBIntervalFamily.hpp>
#include <GeneratedB714Bindings.hpp>
#include <SupportingBFamilyContext.hpp>
#include <algorithm>
#include <functional>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
namespace fathom::tasks::bound_source_units {
namespace {
using V=json::Value;using O=V::Object;using A=V::Array;
void need(bool x,const char* reason){if(!x)throw std::runtime_error(reason);}
const V& f(const V& v,const std::string& key){const auto* p=v.find(key);need(p!=nullptr,"BOUND_SOURCE_FIELD");return *p;}
bool yes(const V& v){return v.isBool()&&v.boolean();}
std::string indexName(std::size_t i){std::ostringstream out;out<<"contact_";out.width(4);out.fill('0');out<<i+1;return out.str();}
V printedRepresentation(const V& value){
 if(value.isArray()){A a;for(const auto& x:value.array())a.push_back(printedRepresentation(x));return a;}
 if(value.isObject()){O o;for(const auto& x:value.object())o.emplace(x.first,printedRepresentation(x.second));if(value.find("fret")&&f(value,"fret").null()&&value.find("muted")&&yes(f(value,"muted")))o["fret"]="muted";return o;}
 return value;
}
V atomExpected(const V& atom){
 O value{{"reported_attack_count",V::fromInteger(f(atom,"kind")==V("hold")||f(atom,"kind")==V("air_stroke")||f(atom,"kind")==V("voicing_formation")?0:1)},
         {"source_order_followed",true},{"unwanted_strings_silent",true},{"pain_or_persistent_tension",false}};
 for(const auto* name:{"printed_note","chord","quality","degree","role"})if(const auto* literal=atom.find(name)){if(literal->isString()){value.emplace("reported_identity",*literal);break;}}
 const auto kind=f(atom,"kind").string();
 const bool selectedSingle=kind=="source_unspecified_arpeggio_contact"||kind=="selected_partial_string_contact"||kind=="learner_selected_string_contact";
 if(!selectedSingle)if(const auto* members=atom.find("members")){if(members->isArray()){A contacts;for(const auto& member:members->array()){O contact{{"string",f(member,"string")},{"fret",f(member,"fret")}};if(member.find("muted"))contact.emplace("muted",f(member,"muted"));contacts.push_back(printedRepresentation(V(contact)));}value.emplace("reported_contacts",contacts);}}
 if(kind=="muted_string_test")value["reported_contacts"]=A{O{{"string",f(atom,"string")},{"fret","muted"},{"muted",true}}};
 else if(!selectedSingle&&!value.count("reported_contacts")&&atom.find("string")&&atom.find("fret")&&!f(atom,"string").null()&&!f(atom,"fret").null())value.emplace("reported_contacts",A{O{{"string",f(atom,"string")},{"fret",f(atom,"fret")},{"muted",atom.find("muted")?f(atom,"muted"):V(false)}}});
 if(const auto* pick=atom.find("pick"))if(!pick->null()&&*pick!=V("P"))value.emplace("reported_stroke",*pick);
 if(kind=="muted_contact"||kind=="dead_stroke"||kind=="muted_string_test"||kind=="muted_strum")value.emplace("continued_contact_without_pressure",true);
 if(kind=="voicing_formation")value.emplace("no_strum",true);
 if(const auto* pressure=atom.find("pressure_instruction"))value.emplace("reported_pressure_action",*pressure);
 return value;
}
bool subset(const V& actual,const V& expected){
 if(actual.null())return false;
 if(expected.isObject()){if(!actual.isObject())return false;for(const auto& x:expected.object()){const auto* p=actual.find(x.first);if(!p||!subset(*p,x.second))return false;}return true;}
 if(expected.isArray()){if(!actual.isArray()||actual.array().size()!=expected.array().size())return false;for(std::size_t i=0;i<expected.array().size();++i)if(!subset(actual.array()[i],expected.array()[i]))return false;return true;}
 return actual==expected;
}
bool permittedContactChoice(const V& atom,const V& contacts){
 if(!contacts.isArray()||contacts.array().empty())return false;const auto kind=f(atom,"kind").string();
 const bool single=kind=="source_unspecified_arpeggio_contact"||kind=="selected_partial_string_contact"||kind=="learner_selected_string_contact";
 if(single&&contacts.array().size()!=1)return false;
 if(const auto* members=atom.find("members"))if(members->isArray()){
  if(single){bool matched=false;for(const auto& m:members->array())matched=matched||subset(contacts.array().front(),printedRepresentation(m));return matched;}
  if(contacts.array().size()!=members->array().size())return false;for(std::size_t i=0;i<members->array().size();++i)if(!subset(contacts.array()[i],printedRepresentation(members->array()[i])))return false;
 }
 if(const auto* string=atom.find("string"))if(!string->null())for(const auto& contact:contacts.array())if(f(contact,"string")!=*string)return false;
 if(const auto* fret=atom.find("fret"))if(!fret->null())for(const auto& contact:contacts.array())if(f(contact,"fret")!=*fret)return false;
 return true;
}
void verifyRootlessSelected(const std::string& key,const V& exported,const V& original){
 const auto found=std::find_if(rootless_selected_custody::rows.begin(),rootless_selected_custody::rows.end(),[&](const auto& row){return key==row.key;});
 if(found==rootless_selected_custody::rows.end()){need(!rootless_seventh_controls::supports(original),"ROOTLESS_UNBOUND_SELECTED_KEY");return;}
 need(f(exported,"source_key")==V(found->key)&&f(original,"package_key")==V(found->key)&&f(exported,"source_identity")==V(found->identity)&&f(original,"source_identity")==V(found->identity),"ROOTLESS_SELECTED_IDENTITY");
 need(f(exported,"payload_ref")==json::parse(found->payload)&&f(exported,"original_row_sha256")==V(found->rawSha)&&f(exported,"original_compact_sha256")==V(found->compactSha),"ROOTLESS_SELECTED_COMPLETE_BINDING");
 need(content::sha256(json::stringify(original))==found->nativeOriginalSha,"ROOTLESS_SELECTED_NATIVE_ORIGINAL");
 need(f(f(exported,"program"),"source_facts")==f(original,"implementation"),"ROOTLESS_SELECTED_SOURCE_FACTS");
}
struct Store{
 std::map<std::string,V> originals,operative,exported,contexts;
 std::set<std::string> caged,triad,coordinates,kinds;
 std::vector<Row> rows;std::vector<Context> contextRows;
};
Store& store(){static Store value=[](){Store s;
 for(const auto& row:b714_compiled_generated::rows){
  need(s.exported.emplace(row.key,json::parse(row.value)).second,"COMPILED_B714_DUPLICATE");
  const auto& exported=s.exported.at(row.key);auto original=json::parse(row.original),operative=f(f(exported,"program"),"source_facts");
  need(f(exported,"source_key")==V(row.key)&&f(original,"package_key")==V(row.key)&&f(exported,"source_identity")==f(original,"source_identity")&&f(operative,"kind")==f(f(original,"implementation"),"kind"),"COMPILED_B714_EXACT_BINDING");
  verifyRootlessSelected(row.key,exported,original);
  bool complete=false;const auto& p=f(exported,"program");for(const auto* k:{"retained_selected_contract_resolved","selected_source_cell_controls_resolved"})if(const auto* x=p.find(k))complete=complete||yes(*x);complete=complete||(b714_compiled_generated::generated::melodicKey(row.key)&&melodic_function_controls::supports(original))||(b714_compiled_generated::generated::sourceMapKey(row.key)&&source_map_controls::supports(original))||(b714_compiled_generated::generated::phraseApplicationKey(row.key)&&phrase_application_controls::supports(original))||(b714_compiled_generated::generated::intervalRecoveryKey(row.key)&&interval_recovery_controls::supports(original));complete=complete||source_task_controls::supports(original)||qualified_source_controls::supports(original)||dim_context_controls::supports(original)||rootless_seventh_controls::supports(original)||timed_assessment_controls::supports(original)||source_form_controls::supports(original);need(complete,"COMPILED_B714_FULL_DUTY_SCOPE");
  s.originals.emplace(row.key,std::move(original));s.operative.emplace(row.key,std::move(operative));s.kinds.insert(f(s.operative.at(row.key),"kind").string());
  if(row.caged)s.caged.insert(row.key);if(row.triad)s.triad.insert(row.key);if(row.coordinate)s.coordinates.insert(row.key);
  s.rows.push_back({row.key,row.value,row.closure,row.original});
 }
 for(const auto& row:s.exported){const auto& ref=f(row.second,"context_ref");const auto path=f(ref,"path").string();if(s.contexts.count(path))continue;bool found=false;for(const auto& c:b714_compiled_generated::generated::contexts)if(path==c.path){s.contexts.emplace(path,json::parse(c.value));found=true;break;}need(found,"CLOSED_COMPILED_B714_CONTEXT");}need(s.exported.size()==b714_compiled_generated::rowCount,"CLOSED_COMPILED_B714");
 // Immutable family inputs are shared only during this initialization. Every
 // selected row still reconstructs and checks its complete exported program.
 std::map<std::string,A> preparedFamilies;
 const auto cachedFamily=[&](const std::string& identity,const auto& prepare)->const A&{
  const auto found=preparedFamilies.find(identity);
  if(found!=preparedFamilies.end())return found->second;
  return preparedFamilies.emplace(identity,prepare()).first->second;
 };
 for(const auto& row:b714_compiled_generated::rows){const std::string key=row.key;const auto& im=s.operative.at(key);const auto& d=s.exported.at(key);const auto& contextRef=f(d,"context_ref");
  auto operativeOriginal=s.originals.at(key);operativeOriginal.object()["implementation"]=im;
  if(source_form_controls::supports(operativeOriginal)){
   need(source_form_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef)==f(d,"program"),"SOURCE_FORM_CONTROLS_PROGRAM_PARITY");
  }else if(timed_assessment_controls::supports(operativeOriginal)){
   need(timed_assessment_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef)==f(d,"program"),"TIMED_ASSESSMENT_CONTROLS_PROGRAM_PARITY");
  }else if(rootless_seventh_controls::supports(operativeOriginal)){
   verifyRootlessSelected(key,d,s.originals.at(key));
   need(rootless_seventh_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef)==f(d,"program"),"ROOTLESS_SEVENTH_CONTROLS_PROGRAM_PARITY");
  }else if(dim_context_controls::supports(operativeOriginal)){
   need(dim_context_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef)==f(d,"program"),"DIM_CONTEXT_CONTROLS_PROGRAM_PARITY");
  }else if(qualified_source_controls::supports(operativeOriginal)){
   need(qualified_source_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef)==f(d,"program"),"QUALIFIED_SOURCE_CONTROLS_PROGRAM_PARITY");
  }else if(source_task_controls::supports(operativeOriginal)){
   need(source_task_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef)==f(d,"program"),"SOURCE_TASK_CONTROLS_PROGRAM_PARITY");
  }else if(melodic_function_controls::supports(operativeOriginal)){
   const auto& family=cachedFamily("melodic", [&](){
   A family;for(const auto& candidate:s.originals)if(melodic_function_controls::familyKey(candidate.first)){auto member=candidate.second;member.object()["implementation"]=s.operative.at(candidate.first);family.push_back(std::move(member));}
   return family;});
   need(melodic_function_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"MELODICFUNCTIONCONTROLS_PROGRAM_PARITY");
  }else  if(source_map_controls::supports(operativeOriginal)){
   const auto& family=cachedFamily("source-map", [&](){
   A family;for(const auto& candidate:s.originals)if(source_map_controls::familyKey(candidate.first)){auto member=candidate.second;member.object()["implementation"]=s.operative.at(candidate.first);family.push_back(std::move(member));}
   return family;});
   need(source_map_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"SOURCEMAPCONTROLS_PROGRAM_PARITY");
  }else  if(phrase_application_controls::supports(operativeOriginal)){
   const auto& family=cachedFamily("phrase-application", [&](){
   auto familySources=s.originals;for(const auto& support:b714_compiled_generated::generated::rows)if(!familySources.count(support.key)&&phrase_application_controls::familyKey(support.key)){auto originalSupport=json::parse(support.original);const auto supportExport=json::parse(support.value);need(f(supportExport,"source_key")==V(support.key)&&f(supportExport,"source_identity")==f(originalSupport,"source_identity"),"EXACT_COMPILED_FAMILY_ORIGINAL_IDENTITY");need(f(originalSupport,"package_key")==V(support.key),"EXACT_COMPILED_PHRASE_FAMILY_ORIGINAL_KEY");need(familySources.emplace(support.key,std::move(originalSupport)).second,"UNIQUE_COMPILED_PHRASE_FAMILY_SOURCE");}A family;for(const auto& candidate:familySources)if(phrase_application_controls::familyKey(candidate.first)){auto member=candidate.second;member.object()["implementation"]=s.operative.count(candidate.first)?s.operative.at(candidate.first):f(candidate.second,"implementation");family.push_back(std::move(member));}
   return family;});
   need(phrase_application_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"PHRASEAPPLICATIONCONTROLS_PROGRAM_PARITY");
  }else  if(interval_recovery_controls::supports(operativeOriginal)){
   const auto& family=cachedFamily("interval-recovery", [&](){
   auto familySources=s.originals;for(const auto& support:b714_compiled_generated::generated::rows)if(!familySources.count(support.key)&&interval_recovery_controls::familyKey(support.key)){auto originalSupport=json::parse(support.original);const auto supportExport=json::parse(support.value);need(f(supportExport,"source_key")==V(support.key)&&f(supportExport,"source_identity")==f(originalSupport,"source_identity"),"EXACT_COMPILED_FAMILY_ORIGINAL_IDENTITY");need(f(originalSupport,"package_key")==V(support.key),"EXACT_COMPILED_INTERVAL_FAMILY_ORIGINAL_KEY");need(familySources.emplace(support.key,std::move(originalSupport)).second,"UNIQUE_COMPILED_INTERVAL_FAMILY_SOURCE");}for(const auto& support:b_final_interval_support::sourceFamilySupport){need(!s.exported.count(support.key),"NONEXECUTABLE_INTERVAL_FAMILY_SUPPORT_SCOPE");need(familySources.emplace(support.key,json::parse(support.original)).second,"UNIQUE_INTERVAL_FAMILY_SUPPORT");}
   A family;for(const auto& candidate:familySources)if(interval_recovery_controls::familyKey(candidate.first)){auto member=candidate.second;member.object()["implementation"]=s.operative.count(candidate.first)?s.operative.at(candidate.first):f(candidate.second,"implementation");family.push_back(std::move(member));}
   return family;});
   need(interval_recovery_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"INTERVALRECOVERYCONTROLS_PROGRAM_PARITY");
  }else if(practical_triad_controls::supports(operativeOriginal)){
   const auto& family=cachedFamily("practical-triad", [&](){
   A family;for(const auto& candidate:s.originals)if(practical_triad_controls::familyKey(candidate.first)){auto member=candidate.second;member.object()["implementation"]=s.operative.at(candidate.first);family.push_back(std::move(member));}
   return family;});
   need(practical_triad_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"PRACTICAL_TRIAD_PROGRAM_PARITY");
  }else if(whole_chord_form_controls::supports(operativeOriginal)){
   const auto& family=cachedFamily("whole-chord", [&](){
   A family;for(const auto& original:s.originals)if(whole_chord_form_controls::supports(original.second))family.push_back(original.second);
   return family;});
   need(whole_chord_form_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"WHOLE_CHORD_FORM_PROGRAM_PARITY");
  }else if(compiled_chord_session_controls::supports(operativeOriginal)){
   need(compiled_chord_session_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef)==f(d,"program"),"COMPILED_CHORD_SESSION_PROGRAM_PARITY");
  }else if(timed_chord_change_controls::supports(operativeOriginal)){
   need(timed_chord_change_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef)==f(d,"program"),"COMPILED_TIMED_PROGRAM_PARITY");
  }else if(anticipation_ladder_controls::supports(operativeOriginal)){
   const auto& family=cachedFamily("anticipation-ladder", [&](){
   A family;for(const auto& candidate:s.originals)if(anticipation_ladder_controls::supports(candidate.second)||candidate.first=="exercise-completeness-r01/level058/modulee/p009-card01/gd"||candidate.first=="exercise-completeness-r01/level058/moduleb/p005-card01/b1alternatingchordghost")family.push_back(candidate.second);
   return family;});
   need(anticipation_ladder_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"COMPILED_LADDER_PROGRAM_PARITY");
  }else if(progression_circle_controls::supports(operativeOriginal)){
   const auto& prepared=cachedFamily("progression:"+json::stringify(A{f(operativeOriginal,"level"),f(f(im,"context_tasks").array().front(),"instruction")}),[&](){
   A family,spellings;const auto& im=f(operativeOriginal,"implementation");const auto heading=f(f(im,"context_tasks").array().front(),"instruction");
   for(const auto& candidate:s.originals){if(f(candidate.second,"level")!=f(operativeOriginal,"level"))continue;auto member=candidate.second;member.object()["implementation"]=s.operative.at(candidate.first);if(harmonized_triad_controls::owns(candidate.first))spellings.push_back(member);if(progression_circle_controls::supports(member)&&f(f(f(member,"implementation"),"context_tasks").array().front(),"instruction")==heading)family.push_back(member);}
   return A{V(std::move(family)),V(std::move(spellings))};});
   const auto& family=prepared.at(0).array();const auto& spellings=prepared.at(1).array();
   need(progression_circle_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family,spellings)==f(d,"program"),"COMPILED_PROGRESSION_PROGRAM_PARITY");
  }else if(anticipation_grid_controls::supports(operativeOriginal)){
   const auto qualified=anticipation_grid_controls::qualificationBinding(key);const auto& join=f(qualified,"original_binding");
   need(f(join,"original_raw_sha256")==f(d,"original_row_sha256")&&f(join,"original_compact_sha256")==f(d,"original_compact_sha256")&&f(join,"payload_ref")==f(d,"payload_ref"),"EXACT_AGENT_SOURCE_QUALIFIED_ORIGINAL_JOIN");
   need(anticipation_grid_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef)==f(d,"program"),"COMPILED_ANTICIPATION_PROGRAM_PARITY");
  }else if(diagonal_route_controls::supports(operativeOriginal)){
   need(diagonal_route_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef)==f(d,"program"),"COMPILED_DIAGONAL_PROGRAM_PARITY");
  }else if(source_phrase_controls::supports(operativeOriginal)){
   const auto& family=cachedFamily("source-phrase", [&](){
   A family;for(const auto& candidate:s.originals){auto member=candidate.second;member.object()["implementation"]=s.operative.at(candidate.first);if(source_phrase_controls::supports(member))family.push_back(std::move(member));}
   return family;});
   need(source_phrase_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"COMPILED_SOURCE_PHRASE_PROGRAM_PARITY");
  }else if(rhythm_grid_controls::supports(operativeOriginal)){
   const auto& family=cachedFamily("rhythm-grid", [&](){
   A family;for(const auto& candidate:s.originals){auto member=candidate.second;member.object()["implementation"]=s.operative.at(candidate.first);if(rhythm_grid_controls::supports(member))family.push_back(std::move(member));}
   return family;});
   need(rhythm_grid_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"COMPILED_RHYTHM_PROGRAM_PARITY");
  }else if(seventh_family_controls::supports(operativeOriginal)){
   const auto& family=cachedFamily("seventh", [&](){
   A family;for(const auto& candidate:s.originals){auto member=candidate.second;member.object()["implementation"]=s.operative.at(candidate.first);if(seventh_family_controls::supports(member))family.push_back(std::move(member));}
   return family;});
   need(seventh_family_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"COMPILED_SEVENTH_PROGRAM_PARITY");
  }else if(beginner_source_controls::supports(operativeOriginal)){
   const auto& family=cachedFamily("beginner:"+json::stringify(A{f(operativeOriginal,"level"),f(f(im,"context_tasks").array().front(),"instruction")}), [&](){
   auto familySources=s.originals;for(const auto& support:b714_compiled_generated::sourceFamilySupport){if(s.exported.count(support.key)){need((std::string(support.key)=="proposed-printed-l049-module-a1-minimum-fretting-pressure-index-finger-g1-g-four-attacks-clean-reduce-to-buzz-threshold-restore-minimum-clean-pressure-release-without-lifting"||std::string(support.key)=="proposed-printed-l049-module-a1-minimum-fretting-pressure-middle-finger-e2-f-four-attacks-clean-reduce-to-buzz-threshold-restore-minimum-clean-pressure-release-without-lifting")&&source_form_controls::supports(s.originals.at(support.key))&&s.originals.at(support.key)==json::parse(support.original),"EXACT_TWO_MATURED_PRESSURE_SOURCE_ORIGINALS");continue;}need(!s.exported.count(support.key),"NONEXECUTABLE_SUPPORT_SCOPE");familySources.emplace(support.key,json::parse(support.original));}
   A family;const auto heading=f(f(im,"context_tasks").array().front(),"instruction");for(const auto& candidate:familySources){if(f(candidate.second,"level")!=f(operativeOriginal,"level"))continue;const auto& impl=s.operative.count(candidate.first)?s.operative.at(candidate.first):f(candidate.second,"implementation");if(!impl.find("context_tasks")||f(impl,"context_tasks").array().empty())continue;if(f(f(impl,"context_tasks").array().front(),"instruction")==heading){auto member=candidate.second;member.object()["implementation"]=impl;family.push_back(std::move(member));}}
   return family;});
   need(beginner_source_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"COMPILED_BEGINNER_PROGRAM_PARITY");
  }else if(harmonized_triad_controls::owns(key)){
   const auto& original=s.originals.at(key);const auto page=f(f(f(im,"source_scope"),"locator"),"physical_page");
   const auto& family=cachedFamily("harmonized:"+json::stringify(A{f(original,"level"),page}),[&](){
    A family;
   for(const auto& candidate:s.originals)if(harmonized_triad_controls::owns(candidate.first)&&f(candidate.second,"level")==f(original,"level")&&f(f(f(s.operative.at(candidate.first),"source_scope"),"locator"),"physical_page")==page){auto member=candidate.second;member.object()["implementation"]=s.operative.at(candidate.first);family.push_back(std::move(member));}
   return family;});
   auto operativeOriginal=original;operativeOriginal.object()["implementation"]=im;
   need(harmonized_triad_controls::construct(key,operativeOriginal,s.contexts.at(f(contextRef,"path").string()),contextRef,family)==f(d,"program"),"COMPILED_HARMONIZED_PROGRAM_PARITY");
  }else if(level068_source_controls::supports(im))need(level068_source_controls::construct(key,im)==f(d,"program"),"COMPILED_L068_PROGRAM_PARITY");
 }
 return s;}();return value;}
}
void configureRoot(const std::filesystem::path&){ /* No runtime source cache/root lookup. */ }
const std::vector<Row>& rows(){return store().rows;}
const std::vector<Context>& contexts(){return store().contextRows;}
bool exactKey(const std::string& key){return store().exported.count(key)==1;}
bool allowedKind(const std::string& kind){return store().kinds.count(kind)==1;}
bool cagedKey(const std::string& key){return store().caged.count(key)==1;}
bool triadControlsKey(const std::string& key){return store().triad.count(key)==1;}
bool coordinateOverrideKey(const std::string& key){return store().coordinates.count(key)==1;}
const V& operativeImplementation(const std::string& key){const auto& s=store();const auto found=s.operative.find(key);need(found!=s.operative.end(),"COMPILED_B714_OPERATIVE_KEY");verifyRootlessSelected(key,s.exported.at(key),s.originals.at(key));return found->second;}
std::size_t cachedFilesHashed(){return 0;}
bool bodilyStopReported(const V& value){
 if(value.isObject()){for(const auto& x:value.object())if((x.first=="pain_or_persistent_tension"&&yes(x.second))||bodilyStopReported(x.second))return true;}
 if(value.isArray())for(const auto& x:value.array())if(bodilyStopReported(x))return true;
 return false;
}
bool atomReportGuard(const V& op,const V& payload,const O& saved){
 need(op.isObject()&&(op.object().size()==2||(op.object().size()==3&&f(op,"kind")==V("b_source_atom_unit")&&f(op,"stage")==V("printed_first")))&&(f(op,"kind")==V("b_source_atom_unit")||f(op,"kind")==V("b_source_choices_known")||f(op,"kind")==V("b_triad_silent_landing")),"CLOSED_SOURCE_ATOM_OPCODE");const auto key=f(op,"source_key").string();need(exactKey(key),"SOURCE_ATOM_OPERATOR_KEY");
 if(f(op,"kind")==V("b_triad_silent_landing")){need(triadControlsKey(key),"CLOSED_TRIAD_CONTROL_KEY");return true;}
 if(f(op,"kind")==V("b_source_choices_known")){
  std::function<bool(const V&)> known=[&](const V& value){if(value.null())return false;if(value.isArray()){for(const auto& x:value.array())if(!known(x))return false;}if(value.isObject()){for(const auto& x:value.object())if(!known(x.second))return false;}return true;};if(!known(payload))return false;
  const auto& atoms=f(operativeImplementation(key),"events").array();for(std::size_t i=0;i<atoms.size();++i)if(const auto* choice=payload.find(indexName(i)))if(const auto* contacts=choice->find("chosen_contacts"))if(!permittedContactChoice(atoms[i],*contacts))return false;return true;
 }
 const auto& im=operativeImplementation(key);const auto& atoms=f(im,"events").array();const auto& reports=f(payload,"reports");need(reports.isObject()&&reports.object().size()==atoms.size(),"COMPLETE_ATOM_REPORT_COUNT");
 if(const auto* contract=im.find("manual_execution_contract"))if(f(*contract,"schema")==V("fathom.private-manual-keychange.v1")||f(*contract,"schema")==V("fathom.private-manual-bridge-template.v1")){
  const auto found=saved.find("source_choices");if(found==saved.end())return false;const auto& start=f(found->second,"chosen_start");if(start!=V("D")&&start!=V("U"))return false;const auto& entered=f(payload,"reported_strokes");if(entered.null())return false;const auto& strokes=entered.array();if(strokes.size()!=atoms.size())return false;for(std::size_t i=0;i<strokes.size();++i)if(strokes[i]!=(i%2==0?start:start==V("D")?V("U"):V("D")))return false;
 }
 if(const auto* contract=im.find("manual_execution_contract"))if(f(*contract,"schema")==V("fathom.private-manual-bridge-template.v1")){const auto found=saved.find("source_choices");if(found==saved.end())return false;for(const auto* name:{"larger_key_context","bridge_purpose"})if(f(payload,std::string("reported_")+name)!=f(found->second,std::string("declared_")+name))return false;}
 bool good=true;for(std::size_t i=0;i<atoms.size();++i){const auto& report=f(reports,indexName(i));auto expected=atomExpected(atoms[i]);
 for(auto it=expected.object().begin();it!=expected.object().end();)if(!report.find(it->first))it=expected.object().erase(it);else ++it;
  good=good&&subset(report,expected);
  for(const auto* field:{"chosen_pick_direction","chosen_contacts"})if(const auto* chosen=report.find(field)){
   const auto prior=saved.find("source_choices");good=good&&prior!=saved.end();
   if(prior!=saved.end()){const auto* atomChoice=prior->second.find(indexName(i));good=good&&atomChoice&&atomChoice->find(field)&&f(*atomChoice,field)==*chosen;}
   good=good&&!chosen->null()&&f(report,field==std::string("chosen_pick_direction")?"reported_stroke":"reported_contacts")==*chosen;
   if(std::string(field)=="chosen_contacts")good=good&&permittedContactChoice(atoms[i],*chosen);
  }
 }
 if(const auto* contract=im.find("manual_execution_contract"))if(f(*contract,"schema")==V("fathom.private-manual-system-compare.v1")){
  if(op.find("stage")){need(f(*contract,"steps").array().size()==6,"CLOSED_COMPARISON_FIRST_STAGE");return good;}
  if(f(*contract,"steps").array().size()==6){const auto prior=saved.find("printed_first_pass_reports");if(prior==saved.end()||f(prior->second,"reports")!=reports)return false;}
  const auto prior=saved.find("source_choices");if(prior==saved.end())return false;const auto& start=f(prior->second,"chosen_comparison_start");if(start!=V("D")&&start!=V("U"))return false;const auto& comparison=f(payload,"comparison_reports");need(comparison.isObject()&&comparison.object().size()==atoms.size(),"COMPLETE_COMPARISON_REPORTS");
  for(std::size_t i=0;i<atoms.size();++i){auto expected=atomExpected(atoms[i]);expected.object().erase("reported_stroke");const auto& report=f(comparison,indexName(i));for(auto it=expected.object().begin();it!=expected.object().end();)if(!report.find(it->first))it=expected.object().erase(it);else ++it;good=good&&subset(report,expected)&&f(report,"reported_stroke")== (i%2==0?start:start==V("D")?V("U"):V("D"));}
 }
 return good;
}
}
