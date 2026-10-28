#include "tasks/SourceContactChoiceOperators.hpp"
#include <algorithm>
#include <stdexcept>
namespace fathom::tasks::source_contacts::private_operators {
namespace {
using J=json::Value;
void need(bool b,const char* e){if(!b)throw std::invalid_argument(e);}
const J& at(const J& v,const char* k){need(v.find(k),"PRIVATE_SOURCE_GUARD_FIELD");return *v.find(k);}
int integer(const J& v){std::int64_t n{};need(v.integer(n)&&n>=0&&n<=100000,"PRIVATE_SOURCE_GUARD_INTEGER");return static_cast<int>(n);}
}
std::optional<bool> reportGuard(const J& g,const J& p){
 const auto& k=at(g,"kind").string();
 if(k=="source_tempo_offset"){
  const auto& previous=at(p,at(g,"previous_field").string().c_str());const auto& current=at(p,at(g,"field").string().c_str());
  if(previous.null()||current.null())return false;const int old=integer(previous),now=integer(current),delta=old-now;
  return now>0&&delta>=integer(at(g,"minimum_drop"))&&delta<=integer(at(g,"maximum_drop"));
 }
 if(k=="saved_equal_report"||k=="next_landmark")return true;
 if(k=="conditional_report"){
  const auto& v=at(p,at(g,"field").string().c_str());const auto& r=at(p,at(g,"report_field").string().c_str());
  if(v.null()||v==J("unknown"))return false;
  return v==at(g,"omit")?r.null():r==J("reported_met");
 }
 if(k=="authored_phrase_domain"){
  const auto& choices=at(p,at(g,"field").string().c_str());need(choices.isArray()&&choices.array().size()==6,"PRIVATE_SOURCE_SIX_CHOSEN_CONTACTS");
  for(std::size_t i=0;i<choices.array().size();++i){const auto& c=choices.array()[i];if(at(c,"string").null()||at(c,"fret").null()||at(c,"note").null()||at(c,"string")==J("unknown")||at(c,"note")==J("unknown"))return false;
   const auto& domain=at(g,"domain").array();const auto f=std::find_if(domain.begin(),domain.end(),[&](const J& d){return at(d,"string")==at(c,"string")&&at(d,"fret")==at(c,"fret")&&at(d,"note")==at(c,"note");});need(f!=domain.end(),"PRIVATE_SOURCE_CHOSEN_TUPLE_OUTSIDE_POSITION");
   for(const auto& endpoint:at(g,"endpoints").array())if(integer(at(endpoint,"phrase_slot"))==static_cast<int>(i+1))need(at(endpoint,"string")==at(c,"string")&&at(endpoint,"fret")==at(c,"fret")&&at(endpoint,"note")==at(c,"note"),"PRIVATE_SOURCE_EXACT_REQUIRED_ENDPOINT");
  }return true;
 }
 return {};
}
bool ownedGuard(const J& g,const J& p,const std::map<std::string,J>& saved){
 const auto& k=at(g,"kind").string();
 if(k=="saved_equal_report"){
  const auto prior=saved.find(at(g,"phase").string());if(prior==saved.end())return false;
  const auto& current=at(p,at(g,"field").string().c_str());const auto& old=at(prior->second,at(g,"saved_field").string().c_str());return !current.null()&&!old.null()&&current==old;
 }
 if(k=="next_landmark"){
  const auto f=saved.find(at(g,"choice_phase").string());if(f==saved.end())return false;const auto& chosen=f->second;const auto& status=at(chosen,"form_status");
  if(status==J("secure"))return at(p,"reentry_bar").null()&&at(p,"stopped_playing_when_lost").null();
  if(status!=J("lost")||at(chosen,"current_bar").null()||at(p,"reentry_bar").null())return false;
  const int current=integer(at(chosen,"current_bar"));if(current<1||current>12)return false;int next=1;
  for(const auto& b:at(g,"landmark_bars").array())if(integer(b)>current){next=integer(b);break;}
  return at(p,"stopped_playing_when_lost")==J("reported_met")&&integer(at(p,"reentry_bar"))==next;
 }
 return true;
}
}
