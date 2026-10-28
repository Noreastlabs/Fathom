#include "tasks/ManualProcedureProtocolSupport.hpp"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <set>
#include <stdexcept>

namespace fathom::tasks::manual_procedure_graph_support {
namespace {
using V=json::Value;
void need(bool yes,const char* reason){if(!yes)throw std::runtime_error(reason);}
const V& f(const V& v,const char* name){need(v.isObject(),"OBJECT_REQUIRED");const auto* x=v.find(name);need(x!=nullptr,"REFERENCE_FIELD");return *x;}
void fields(const V& v,std::initializer_list<const char*> names){need(v.isObject()&&v.object().size()==names.size(),"EXACT_OPERATOR_FIELDS");for(const auto* n:names)(void)f(v,n);}
std::int64_t integer(const V& v){std::int64_t x{};need(v.integer(x),"STRICT_INTEGER_REQUIRED");return x;}
struct Decimal {std::string digits;std::int64_t magnitude{};};
Decimal decimal(const V& value){
 need(value.isNumber(),"REPORTED_FINITE_NUMBER_TYPE");const auto& token=std::get<json::Number>(value.data).token;need(!token.empty()&&token.size()<=128&&json::parse(token).isNumber(),"DECIMAL_TOKEN");
 char* end=nullptr;const auto approximate=std::strtod(token.c_str(),&end);need(end==token.c_str()+token.size()&&std::isfinite(approximate)&&approximate>=0,"REPORTED_FINITE_NONNEGATIVE_NUMBER");
 std::size_t i=token[0]=='-'?1:0;std::string digits;std::size_t fractional{};bool dot=false;
 while(i<token.size()&&token[i]!='e'&&token[i]!='E'){const auto c=token[i++];if(c=='.'){dot=true;continue;}need(c>='0'&&c<='9',"DECIMAL_TOKEN");digits+=c;if(dot)++fractional;}
 std::int64_t exponent{};if(i<token.size()){++i;bool negative=false;if(token[i]=='+'||token[i]=='-'){negative=token[i]=='-';++i;}for(;i<token.size();++i){need(token[i]>='0'&&token[i]<='9'&&exponent<=10000,"DECIMAL_EXPONENT");exponent=exponent*10+token[i]-'0';}if(negative)exponent=-exponent;}
 const auto first=digits.find_first_not_of('0');if(first==std::string::npos)return {"",0};need(token[0]!='-',"REPORTED_NONNEGATIVE_NUMBER");digits.erase(0,first);
 const auto magnitude=exponent-static_cast<std::int64_t>(fractional)+static_cast<std::int64_t>(digits.size());while(digits.size()>1&&digits.back()=='0')digits.pop_back();return {digits,magnitude};
}
bool atLeast(const Decimal& a,const Decimal& b){if(b.digits.empty())return true;if(a.digits.empty())return false;if(a.magnitude!=b.magnitude)return a.magnitude>b.magnitude;auto x=a.digits,y=b.digits;const auto width=std::max(x.size(),y.size());x.append(width-x.size(),'0');y.append(width-y.size(),'0');return x>=y;}
}
Projection projectSourceOrderedPDirections(const V& op,const V& reports){
 fields(op,{"kind","source_contacts","directions_ref","protocol_start","include_first","first_P_order","source_P_orders","report_field","directions_value_kind"});
 const auto& reference=f(op,"directions_ref");fields(reference,{"scope","path"});need(f(reference,"scope")==V("saved")&&f(reference,"path").isArray()&&f(reference,"path").array().size()==2&&f(reference,"path").array()[0]==V("choice")&&f(reference,"path").array()[1].isString()&&!f(reference,"path").array()[1].string().empty(),"CLOSED_SAVED_P_CHOICE");
 need(f(op,"kind")==V("source_order_P_directions")&&f(op,"report_field")==V("P_directions"),"CLOSED_P_OPERATOR");const auto& start=f(op,"protocol_start");need(start==V("D")||start==V("U"),"P_PROTOCOL_START");need(f(op,"include_first").isBool(),"P_FIRST_MODE");const auto include=f(op,"include_first").boolean();
 const auto& contacts=f(op,"source_contacts");need(contacts.isArray()&&!contacts.array().empty()&&contacts.array().size()<=256,"CLOSED_SOURCE_CONTACTS");V::Array actual;std::int64_t prior=-1;
 for(const auto& contact:contacts.array()){const auto order=integer(f(contact,"order"));need(order>0&&order>prior,"SOURCE_CONTACT_ORDER");prior=order;need(f(contact,"pick").isString(),"SOURCE_PICK_TYPE");if(f(contact,"pick")==V("P"))actual.push_back(f(contact,"order"));}
 need(!actual.empty()&&V(actual)==f(op,"source_P_orders")&&actual.front()==f(op,"first_P_order"),"EXACT_SOURCE_P_ORDERS");const auto& kind=f(op,"directions_value_kind");need(kind==V("array")||kind==V("one_scalar"),"P_DIRECTION_VALUE_KIND");V::Array chosen;
 if(reports.null())return {false,V::Object{}};
 if(kind==V("one_scalar")){need(!include&&actual.size()==2,"ONE_LATER_P_SOURCE");chosen.push_back(reports);}else{need(reports.isArray(),"P_DIRECTION_ARRAY");chosen=reports.array();}
 need(chosen.size()==actual.size()-(include?0:1),"EXACT_P_DIRECTION_COUNT");bool known=true;for(const auto& x:chosen){need(x.null()||x==V("D")||x==V("U"),"P_DIRECTION_ENUM");known=known&&!x.null();}if(!known)return {false,V::Object{}};
 if(include)need(chosen.front()==start,"SOURCE_FIRST_P_BINDING");else chosen.insert(chosen.begin(),start);
 return {true,V::Object{{"P_directions",chosen}}};
}
bool reportedSecondsAtLeast(const V& report,const V& lower){
 // Validate known inputs even when the other side is an unknown report.
 Decimal a,b;if(!report.null())a=decimal(report);if(!lower.null())b=decimal(lower);if(report.null()||lower.null())return false;return atLeast(a,b);
}
bool trimmedTextExact(const V& report){need(report.isString(),"TRIMMED_TEXT_TYPE");return utf8TextLength(report.string())>0&&nonemptyTrimmedText(report,utf8TextLength(report.string()),utf8TextLength(report.string()));}
const V& boundProtocolSourceAction(const V& contract,const V& ref){
 fields(ref,{"original_contract_path"});const auto& path=f(ref,"original_contract_path");need(path.isArray()&&path.array().size()==2,"BOUNDED_PROTOCOL_REFERENCE");
 if(path.array()[0]==V("steps"))return boundSourceAction(contract,ref);
 const std::set<std::string> names{"setup","mirror","full_hand_release","one_breath","compare"};need(path.array()[0]==V("actions")&&path.array()[1].isString()&&names.count(path.array()[1].string()),"CLOSED_SOURCE_ACTION_ALIAS");return f(f(contract,"actions"),path.array()[1].string().c_str());
}
V boundTableSourceRecords(const V& original,const V& node){
 const auto& refs=f(node,"source_record_refs");need(refs.isArray()&&!refs.array().empty()&&refs.array().size()<=3,"FINITE_SOURCE_RECORD_REFS");const std::set<std::string> allowed{"table_task","task","context_tasks"};std::set<std::string> seen;V::Array result;
 for(const auto& path:refs.array()){need(path.isArray()&&path.array().size()==2&&path.array()[0]==V("implementation")&&path.array()[1].isString()&&allowed.count(path.array()[1].string())&&seen.insert(path.array()[1].string()).second,"CLOSED_SOURCE_RECORD_REF");result.push_back(f(f(original,"implementation"),path.array()[1].string().c_str()));}return result;
}
V boundAssessmentSourceInstructions(const V& contract,const V& node){
 const auto& refs=f(node,"source_action_refs");need(refs.isArray()&&!refs.array().empty()&&refs.array().size()<=256,"FINITE_ORDERED_SOURCE_REFS");const auto& lines=f(contract,"ordered_source_instructions");need(lines.isArray()&&!lines.array().empty(),"ORIGINAL_SOURCE_INSTRUCTIONS");std::int64_t prior=-1;V::Array result;
 for(const auto& ref:refs.array()){fields(ref,{"original_contract_path"});const auto& path=f(ref,"original_contract_path");need(path.isArray()&&path.array().size()==2&&path.array()[0]==V("ordered_source_instructions"),"CLOSED_ORDERED_SOURCE_REF");const auto index=integer(path.array()[1]);need(index>=0&&static_cast<std::size_t>(index)<lines.array().size()&&(prior<0||index==prior+1),"SOURCE_INSTRUCTION_ORDER_RANGE");const auto& line=lines.array()[static_cast<std::size_t>(index)];fields(line,{"line","text"});need(integer(f(line,"line"))>0&&f(line,"text").isString(),"SOURCE_INSTRUCTION_TEXT");result.push_back(line);prior=index;}return result;
}
} // namespace fathom::tasks::manual_procedure_graph_support
