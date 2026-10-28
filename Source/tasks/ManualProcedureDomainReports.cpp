#include "tasks/ManualProcedureDomainReports.hpp"
#include <set>
#include <stdexcept>
#include <vector>
namespace fathom::tasks::manual_procedure_graph_support {
namespace {using V=json::Value;
void need(bool b,const char* why){if(!b)throw std::runtime_error(why);}
const V& f(const V& v,const char* name){need(v.isObject(),"OBJECT_REQUIRED");const auto* p=v.find(name);need(p!=nullptr,"REFERENCE_FIELD");return *p;}
std::int64_t number(const V& v){std::int64_t n{};need(v.integer(n),"STRICT_INTEGER_REQUIRED");return n;}
void fields(const V& v,std::initializer_list<const char*> names){need(v.isObject()&&v.object().size()==names.size(),"EXACT_FIELDS");for(const auto* name:names)(void)f(v,name);}
}
Projection projectClosedDomainReports(const V& op,const V& selection,const V& domain) {
 fields(op,{"kind","domain","selection","fields"});need(f(op,"kind")==V("selected_domain_reports")&&f(op,"domain").isString(),"DOMAIN_OPERATOR");need(selection.isObject()&&f(op,"selection").isObject()&&selection.object().size()==f(op,"selection").object().size(),"SELECTION_FIELDS");bool known=true;
 for(const auto& item:f(op,"selection").object()){const auto& x=f(selection,item.first.c_str());known=known&&!x.null();}
 need(domain.isArray()&&!domain.array().empty()&&domain.array().size()<=4096,"FINITE_DOMAIN");const V* match=nullptr;std::set<std::string> selections;const auto& projection=f(op,"fields");need(projection.isObject()&&!projection.object().empty(),"DOMAIN_PROJECTIONS");const std::set<std::string> allowed{"printed_note","role","string","fret","pick","chosen_pick"};for(const auto& field:projection.object())need(!field.first.empty()&&field.second.isString()&&allowed.count(field.second.string()),"CLOSED_CONTACT_PROPERTY");
 for(const auto& record:domain.array()){
  if(record.isObject()&&record.object().size()==6){fields(record,{"selection","contacts","chosen_geometry","absolute_delta_semitones","source_geometry","source_clock"});const auto distance=number(f(record,"absolute_delta_semitones"));need(f(op,"domain")==V("chosen_pair")&&f(record,"chosen_geometry")==V(true)&&(distance==-1||distance==1||distance==2)&&f(record,"source_geometry").null()&&f(record,"source_clock").null()&&f(record,"contacts").isArray()&&f(record,"contacts").array().size()==2,"CLOSED_AUTHORED_TABLE_PAIR");
   const int tuning[]{0,64,59,55,50,45,40};std::int64_t pitches[2]{};for(std::size_t i=0;i<2;++i){const auto& contact=f(record,"contacts").array()[i];const auto string=number(f(contact,"string")),fret=number(f(contact,"fret"));need(string>=1&&string<=6&&fret>=0&&fret<=24,"AUTHORED_TABLE_CONTACT_RANGE");pitches[i]=tuning[string]+fret;}need(pitches[1]-pitches[0]==distance,"SOURCE_SIGNED_TABLE_MOVEMENT");}
  else fields(record,{"selection","contacts"});
  const auto& pick=f(record,"selection");need(pick.isObject()&&pick.object().size()==selection.object().size(),"DOMAIN_SELECTION_FIELDS");for(const auto& item:selection.object())(void)f(pick,item.first.c_str());need(selections.insert(json::stringify(pick)).second,"DUPLICATE_DOMAIN");const auto& contacts=f(record,"contacts");need(contacts.isArray()&&!contacts.array().empty()&&contacts.array().size()<=64,"FINITE_CONTACT_SEQUENCE");for(const auto& contact:contacts.array())for(const auto& field:projection.object())(void)f(contact,field.second.string().c_str());if(pick==selection){need(!match,"DUPLICATE_DOMAIN");match=&record;}}
 if(!known)return {false,V::Object{}};need(match!=nullptr,"CLOSED_DOMAIN_SELECTION");const auto& contacts=f(*match,"contacts");need(contacts.isArray()&&!contacts.array().empty()&&contacts.array().size()<=64,"FINITE_CONTACT_SEQUENCE");V::Object result;
 for(const auto& field:projection.object()){need(!field.first.empty()&&field.second.isString()&&allowed.count(field.second.string()),"CLOSED_CONTACT_PROPERTY");V::Array values;for(const auto& contact:contacts.array())values.push_back(f(contact,field.second.string().c_str()));result.emplace(field.first,values);}return {true,result};
}
const V& boundSourceAction(const V& contract,const V& reference) {
 fields(reference,{"original_contract_path"});const auto& path=f(reference,"original_contract_path");need(path.isArray()&&path.array().size()==2&&path.array()[0]==V("steps"),"BOUNDED_SOURCE_STEP_REFERENCE");const auto index=number(path.array()[1]);const auto& steps=f(contract,"steps");need(steps.isArray()&&index>=0&&static_cast<std::size_t>(index)<steps.array().size(),"SOURCE_STEP_RANGE");return steps.array()[static_cast<std::size_t>(index)];
}

namespace {
std::vector<std::uint32_t> codepoints(const std::string& text) {
 std::vector<std::uint32_t> out;
 for(std::size_t i=0;i<text.size();) {
  const auto first=static_cast<unsigned char>(text[i++]);std::uint32_t point{};std::size_t count{};
  if(first<0x80){point=first;count=0;}
  else if(first>=0xc2&&first<=0xdf){point=first&0x1f;count=1;}
  else if(first>=0xe0&&first<=0xef){point=first&0x0f;count=2;}
  else if(first>=0xf0&&first<=0xf4){point=first&0x07;count=3;}
  else throw std::runtime_error("INVALID_UTF8");
  need(i+count<=text.size(),"TRUNCATED_UTF8");
  for(std::size_t n=0;n<count;++n){const auto byte=static_cast<unsigned char>(text[i++]);need((byte&0xc0)==0x80,"INVALID_UTF8");point=(point<<6)|(byte&0x3f);}
  need((count!=1||point>=0x80)&&(count!=2||point>=0x800)&&(count!=3||point>=0x10000)&&point<=0x10ffff&&(point<0xd800||point>0xdfff),"INVALID_UTF8");out.push_back(point);
 }
 return out;
}
bool whitespace(std::uint32_t c) {return (c>=0x09&&c<=0x0d)||(c>=0x1c&&c<=0x20)||c==0x85||c==0xa0||c==0x1680||(c>=0x2000&&c<=0x200a)||c==0x2028||c==0x2029||c==0x202f||c==0x205f||c==0x3000;}
}
std::size_t utf8TextLength(const std::string& text){return codepoints(text).size();}
std::string utf8TextSlice(const std::string& text,std::size_t first,std::size_t last){const auto count=codepoints(text).size();need(first<=last&&last<=count,"UNICODE_SPAN_RANGE");std::vector<std::size_t> offsets;for(std::size_t i=0;i<text.size();++i)if((static_cast<unsigned char>(text[i])&0xc0)!=0x80)offsets.push_back(i);offsets.push_back(text.size());return text.substr(offsets[first],offsets[last]-offsets[first]);}
bool nonemptyTrimmedText(const V& report,std::size_t minimum,std::size_t maximum) {
 need(report.isString(),"TRIMMED_TEXT_TYPE");need(minimum>=1&&minimum<=maximum&&maximum<=8192,"TRIMMED_TEXT_BOUNDS");const auto points=codepoints(report.string());std::size_t first=0,last=points.size();while(first<last&&whitespace(points[first]))++first;while(last>first&&whitespace(points[last-1]))--last;return last-first>=minimum&&last-first<=maximum;
}
V boundSourceUnit(const V& contract,const V& node) {
 need(node.isObject()&&!(node.find("source_action_ref")&&node.find("source_action_refs")),"SOURCE_BINDING_FORM");V::Array actions;
 if(const auto* refs=node.find("source_action_refs")) {
  need(refs->isArray()&&!refs->array().empty()&&refs->array().size()<=2,"FINITE_SOURCE_UNIT");std::int64_t previous=-1;
  for(const auto& ref:refs->array()){const auto& action=boundSourceAction(contract,ref);const auto& path=f(ref,"original_contract_path");const auto index=number(path.array()[1]);need(previous<0||index==previous+1,"ORDERED_UNINTERRUPTED_SOURCE_UNIT");previous=index;actions.push_back(action);}
  if(actions.size()>1)need(f(node,"physical")==V(true),"PHYSICAL_SOURCE_UNIT");
 } else if(const auto* ref=node.find("source_action_ref"))actions.push_back(boundSourceAction(contract,*ref));
 V release=nullptr;if(const auto* ref=node.find("release_source_action_ref"))release=boundSourceAction(contract,*ref);
 return V::Object{{"source_actions",actions},{"separate_release_witness",release},{"inserts_release_between_actions",false},{"execution_observed",false},{"clock_synthesized",false}};
}
} // namespace fathom::tasks::manual_procedure_graph_support
