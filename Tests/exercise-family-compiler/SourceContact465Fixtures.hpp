#pragma once
// TEST ONLY: synthetic manual reports. Production reports must start blank.
#include "tasks/OrderedContactTaskFormAdapter.hpp"
#include <algorithm>
namespace fathom::tasks::source_contacts::test_fixtures {
using J=json::Value;namespace M=ordered_contacts::manual;
inline const J& at(const J& x,const char* k){if(!x.find(k))throw std::runtime_error("fixture missing field");return *x.find(k);}
inline J value(const J& schema){
 const auto* choices=schema.find("enum");if(choices){for(const auto& v:choices->array())if(v==J("reported_met"))return v;for(const auto& v:choices->array())if(v==J("clean"))return v;for(const auto& v:choices->array())if(!v.null()&&v!=J("unknown"))return v;}
 const auto& type=at(schema,"type");const std::string t=type.isString()?type.string():type.array()[0].string();
 if(t=="string")return J("Synthetic explicit manual source report");
 if(t=="integer"){const auto* lo=schema.find("minimum");std::int64_t n=1;if(lo)lo->integer(n);return J::fromInteger(n);}
 if(t=="boolean")return J(true);
 if(t=="array"){J::Array out;std::int64_t count=0;at(schema,"minItems").integer(count);for(std::int64_t n=0;n<count;++n){const auto& item=at(schema,"items");if(at(item,"type")==J("string")&&item.find("maxLength")&&at(item,"maxLength")==J::fromInteger(10))out.emplace_back(n?"2026-10-02":"2026-10-01");else out.push_back(value(item));}return J(out);}
 if(t=="object"){J::Object out;for(const auto& name:at(schema,"required").array())out.emplace(name.string(),value(*at(schema,"properties").find(name.string())));return J(out);}
 return J(nullptr);
}
inline J positiveFor(const M::Task& task,const M::OpenForm& form,M::Action action){
 J out=value(form.schema);
 if(action==M::Action::Begin){for(const auto& k:{"setup_read","one_set","printed_mode","stable_landings"})if(out.find(k))out.object()[k]=J::fromInteger(static_cast<int>(M::Claim::Yes));}
 if(action==M::Action::Contact&&out.find("contact_reported"))out.object()["contact_reported"]=J::fromInteger(static_cast<int>(M::Claim::Yes));
 if(action==M::Action::Release&&out.find("hand_release_reported"))out.object()["hand_release_reported"]=J::fromInteger(static_cast<int>(M::Claim::Yes));
 if(action==M::Action::AdvancePass){std::int64_t r{};at(out,"source_route").integer(r);const auto p=json::parse(task.sourceHandle().phaseProgramJson(static_cast<std::size_t>(r)));out.object()["first_start"]=J::fromInteger(static_cast<int>(at(p,"requires_both_saved_starts").boolean()?ordered_contacts::Start::Down:ordered_contacts::Start::Unspecified));}
 if(action==M::Action::SourcePhaseReport||action==M::Action::SourceRepairReport){
  const auto p=json::parse(task.sourceHandle().phaseProgramJson(task.view().passIndex));const J* phase=nullptr;
  if(action==M::Action::SourcePhaseReport)phase=&at(p,"report_phases").array().at(task.view().sourcePhaseIndex);
  else for(const auto& r:at(p,"repair_options").array())if(at(r,"id")==J(*task.view().sourceRepairDue))phase=&r;
  if(!phase)throw std::runtime_error("fixture exact phase");for(const auto& g:at(*phase,"guards").array()){
   if(at(g,"kind")==J("equal_literal"))out.object()[at(g,"field").string()]=at(g,"value");
   if(at(g,"kind")==J("minimum"))out.object()[at(g,"field").string()]=at(g,"value");
   if(at(g,"kind")==J("source_tempo_offset")){const int current=task.view().reportedBpm.value_or(100);out.object()[at(g,"previous_field").string()]=J::fromInteger(current+10);out.object()[at(g,"field").string()]=J::fromInteger(current);}
   if(at(g,"kind")==J("conditional_report"))out.object()[at(g,"report_field").string()]=nullptr;
   if(at(g,"kind")==J("next_landmark")){out.object()["reentry_bar"]=nullptr;out.object()["stopped_playing_when_lost"]=nullptr;}
   if(at(g,"kind")==J("authored_phrase_domain")){J::Array chosen;for(std::size_t i=0;i<6;++i){const J* d=&at(g,"domain").array()[0];for(const auto& e:at(g,"endpoints").array()){std::int64_t slot{};at(e,"phrase_slot").integer(slot);if(slot==static_cast<std::int64_t>(i+1))d=&e;}chosen.push_back(J::Object{{"string",at(*d,"string")},{"fret",at(*d,"fret")},{"note",at(*d,"note")},{"chosen_finger",nullptr}});}out.object()[at(g,"field").string()]=J(chosen);}

   if(at(g,"kind")==J("tempo_reduction")||at(g,"kind")==J("reduction_or_source_isolation")){const int prior=task.view().reportedBpm.value_or(100);out.object()[at(g,"previous_field").string()]=J::fromInteger(prior);out.object()[at(g,"new_field").string()]=J::fromInteger(prior-4);out.object()[at(g,"drop_field").string()]=J::fromInteger(4);if(at(g,"kind")==J("reduction_or_source_isolation"))out.object()[at(g,"field").string()]="reduce_4_6";}
   if(at(g,"kind")==J("source_tempo_progression")){const int prior=task.view().reportedBpm.value_or(100);out.object()[at(g,"field").string()]="hold";out.object()[at(g,"previous_field").string()]=J::fromInteger(prior);out.object()[at(g,"new_field").string()]=J::fromInteger(prior);out.object()[at(g,"clean_field").string()]=J::fromInteger(0);}
  }
  if(out.find("manual_bpm"))out.object()["manual_bpm"]=J::fromInteger(1);
  if(out.find("source_errors"))out.object()["source_errors"]=J::fromInteger(0);if(out.find("source_issue"))out.object()["source_issue"]="clean";
  if(out.find("reported_manual_bpm"))out.object()["reported_manual_bpm"]=J::fromInteger(task.view().reportedBpm.value_or(100));
  if(out.find("heard_center")){
   const auto& phases=at(p,"report_phases").array();for(const auto& next:phases)for(const auto& g:at(next,"guards").array())if(at(g,"kind")==J("saved_equal_literal")&&at(g,"field")==J("heard_center"))out.object()["heard_center"]=at(g,"value");
  }
 }
 return out;
}
inline J unresolvedFor(const M::Task& task,const M::OpenForm& form,M::Action action){auto p=positiveFor(task,form,action);if(p.find("evidence"))p.object()["evidence"]=" \t\n ";else throw std::runtime_error("fixture has no manual evidence");return p;}
}
