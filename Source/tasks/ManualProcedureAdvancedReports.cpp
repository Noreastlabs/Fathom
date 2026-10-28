#include "tasks/ManualProcedureAdvancedReports.hpp"
#include "tasks/ManualProcedureDomainReports.hpp"
#include <algorithm>
#include <set>

namespace fathom::tasks::manual_procedure_graph_support {
namespace {
using V=json::Value;using O=V::Object;using A=V::Array;
void need(bool ok,const char* message){if(!ok)throw recipes::Error(message);}
const V& f(const V& value,const std::string& name){const auto* found=value.find(name);need(found!=nullptr,"ADVANCED_FIELDS");return *found;}
std::string s(const V& value,const char* name){const auto& result=f(value,name);need(result.isString(),"ADVANCED_STRING");return result.string();}
std::int64_t n(const V& value){std::int64_t result{};need(value.integer(result),"ADVANCED_INTEGER");return result;}
void shape(const V& value,std::initializer_list<const char*> fields){need(value.isObject()&&value.object().size()==fields.size(),"CLOSED_ADVANCED_GUARD");for(const auto* field:fields)(void)f(value,field);}
bool nonempty(const V& value){return !value.null()&&nonemptyTrimmedText(value,1,8192);}
V expand(const V& value,const V& parameters){
    if(value.isObject()){
        if(const auto* parameter=value.find("$parameter")){need(value.object().size()==1&&parameter->isString(),"CLOSED_PARAMETER_OPERATOR");return f(parameters,parameter->string());}
        O result;for(const auto& item:value.object())result.emplace(item.first,expand(item.second,parameters));return result;
    }
    if(value.isArray()){A result;for(const auto& item:value.array())result.push_back(expand(item,parameters));return result;}
    return value;
}
bool nonemptyLists(const V& descriptor,const V& payload){
    shape(descriptor,{"kind","fields","lengths"});const auto& fields=f(descriptor,"fields").array();const auto& lengths=f(descriptor,"lengths").array();need(!fields.empty()&&fields.size()<=128&&fields.size()==lengths.size(),"LIST_DESCRIPTOR_COUNT");bool good=true;
    for(std::size_t i=0;i<fields.size();++i){need(fields[i].isString(),"LIST_FIELD_NAME");const auto& list=f(payload,fields[i].string());need(list.isArray()&&list.array().size()==static_cast<std::size_t>(n(lengths[i])),"SOURCE_LIST_COUNT");for(const auto& value:list.array()){need(value.null()||value.isString(),"SOURCE_LIST_TEXT_TYPE");good=nonempty(value)&&good;}}
    return good;
}
bool permutation(const V& value,const V& domain){need(value.isArray()&&domain.isArray()&&value.array().size()==domain.array().size(),"SOURCE_PERMUTATION_COUNT");std::set<std::string> actual,expected;bool good=true;for(const auto& item:domain.array()){need(item.isString()&&expected.insert(item.string()).second,"SOURCE_PERMUTATION_DOMAIN");}for(const auto& item:value.array()){if(item.null()){good=false;continue;}need(item.isString(),"SOURCE_PERMUTATION_TYPE");if(!actual.insert(item.string()).second)good=false;}return good&&actual==expected;}
struct Date {int year{},month{},day{};};
std::optional<Date> date(const V& value){
    if(value.null())return std::nullopt;need(value.isString(),"DATE_REPORT_TYPE");const auto& text=value.string();if(text.size()!=10||text[4]!='-'||text[7]!='-')return std::nullopt;
    for(std::size_t i=0;i<text.size();++i)if(i!=4&&i!=7&&(text[i]<'0'||text[i]>'9'))return std::nullopt;
    const Date result{std::stoi(text.substr(0,4)),std::stoi(text.substr(5,2)),std::stoi(text.substr(8,2))};if(result.year<1||result.month<1||result.month>12)return std::nullopt;
    const int lengths[]{31,28,31,30,31,30,31,31,30,31,30,31};const bool leap=result.year%4==0&&(result.year%100!=0||result.year%400==0);if(result.day<1||result.day>lengths[result.month-1]+(result.month==2&&leap?1:0))return std::nullopt;return result;
}
bool nextDay(const V& before,const V& after){auto a=date(before),b=date(after);if(!a||!b)return false;const int lengths[]{31,28,31,30,31,30,31,31,30,31,30,31};const bool leap=a->year%4==0&&(a->year%100!=0||a->year%400==0);if(++a->day>lengths[a->month-1]+(a->month==2&&leap?1:0)){a->day=1;if(++a->month>12){a->month=1;++a->year;}}return a->year==b->year&&a->month==b->month&&a->day==b->day;}
V savedRef(const V& descriptor,const O& saved){shape(descriptor,{"scope","path"});need(s(descriptor,"scope")=="saved","SAVED_SOURCE_CHOICE_SCOPE");return boundedOriginalPath(V(saved),f(descriptor,"path"));}
}
const V& boundedOriginalPath(const V& original,const V& path){need(path.isArray()&&!path.array().empty()&&path.array().size()<=16,"BOUNDED_ORIGINAL_PATH");const V* result=&original;for(const auto& part:path.array()){if(part.isString())result=&f(*result,part.string());else{const auto index=n(part);need(result->isArray()&&index>=0&&static_cast<std::size_t>(index)<result->array().size(),"ORIGINAL_PATH_RANGE");result=&result->array()[static_cast<std::size_t>(index)];}}return *result;}
V expandSharedProgram(const V& catalog,const std::string& program,const V& parameters){shape(catalog,{"templates","closed_parameters"});need(parameters.isObject(),"PARAMETERS_OBJECT");const auto& names=f(f(catalog,"closed_parameters"),program).array();need(parameters.object().size()==names.size(),"CLOSED_PARAMETER_FIELDS");for(const auto& name:names){need(name.isString(),"PARAMETER_NAME");(void)f(parameters,name.string());}return expand(f(f(catalog,"templates"),program),parameters);}
std::optional<bool> advancedReportedGuard(const V& descriptor,const V& payload,const O& saved,const V& failed,const V& domains){
    const auto kind=s(descriptor,"kind");
    if(kind=="required_manual_fields_resolved"||kind=="source_resolved_fields"){
        shape(descriptor,{"kind","fields"});const auto& fields=f(descriptor,"fields").array();need(!fields.empty()&&fields.size()<=128,"RESOLVED_FIELDS_COUNT");bool good=true;for(const auto& field:fields){need(field.isString(),"RESOLVED_FIELD_NAME");good=!f(payload,field.string()).null()&&good;}return good;
    }
    if(kind=="seventh_nonempty_reports"||kind=="source_nonempty_lists")return nonemptyLists(descriptor,payload);
    if(kind=="readiness_named_reports"){
        shape(descriptor,{"kind","fields"});bool good=true;for(const auto& field:f(descriptor,"fields").array()){need(field.isString(),"NAMED_FIELD");const auto& list=f(payload,field.string());need(list.isArray()&&!list.array().empty()&&list.array().size()<=128,"NAMED_REPORT_COUNT");for(const auto& value:list.array()){need(value.null()||value.isString(),"NAMED_REPORT_TYPE");good=nonempty(value)&&good;}}return good;
    }
    if(kind=="readiness_next_day_reports"){
        shape(descriptor,{"kind","before_field","after_field","array_fields"});bool good=nextDay(f(payload,s(descriptor,"before_field")),f(payload,s(descriptor,"after_field")));const auto& fields=f(descriptor,"array_fields").array();need(fields.size()==2,"NEXT_DAY_ARRAY_FIELDS");for(const auto& field:fields){const auto& list=f(payload,field.string());need(list.isArray()&&list.array().size()==5,"NEXT_DAY_FIVE_ROLES");for(const auto& value:list.array()){need(value.null()||value.isString(),"NEXT_DAY_TEXT_TYPE");good=nonempty(value)&&good;}}return good;
    }
    if(kind=="seventh_quality_permutation"){shape(descriptor,{"kind","field"});return permutation(f(payload,s(descriptor,"field")),V(A{"maj7","7","m7","m7b5"}));}
    if(kind=="source_order_permutation"){shape(descriptor,{"kind","field","domain"});return permutation(f(payload,s(descriptor,"field")),f(descriptor,"domain"));}
    if(kind=="source_adjacent_sets"){
        shape(descriptor,{"kind","current_field","target_field"});const auto& first=f(payload,s(descriptor,"current_field"));const auto& second=f(payload,s(descriptor,"target_field"));if(first.null()||second.null())return false;need(first.isString()&&second.isString(),"STRING_SET_TYPE");const std::vector<std::string> sets{"E_A_D","A_D_G","D_G_B","G_B_e"};const auto a=std::find(sets.begin(),sets.end(),first.string()),b=std::find(sets.begin(),sets.end(),second.string());need(a!=sets.end()&&b!=sets.end(),"CLOSED_STRING_SET");return a-b==1||b-a==1;
    }
    if(kind=="selected_source_literal"){
        shape(descriptor,{"kind","choice_ref","domain","reports"});const auto choice=savedRef(f(descriptor,"choice_ref"),saved);if(choice.null())return false;need(choice.isString(),"SOURCE_DOMAIN_CHOICE_TYPE");const auto& domain=f(domains,s(descriptor,"domain"));need(domain.isObject(),"SOURCE_LITERAL_DOMAIN_OBJECT");const auto* match=domain.find(choice.string());need(match!=nullptr,"CLOSED_SOURCE_DOMAIN_CHOICE");bool good=true;for(const auto& report:f(descriptor,"reports").object()){const auto& value=f(payload,report.first);good=!value.null()&&value==f(*match,report.second.string())&&good;}return good;
    }
    if(kind=="failed_report_predicate"){
        shape(descriptor,{"kind","field","equals"});if(failed.null()||!failed.find("payload"))return false;const auto* value=f(failed,"payload").find(s(descriptor,"field"));return value&&!value->null()&&*value==f(descriptor,"equals");
    }
    if(kind=="source_assignment_coverage"){
        shape(descriptor,{"kind","field","positions","patterns"});const auto& actual=f(payload,s(descriptor,"field"));need(actual.isArray(),"COVERAGE_ARRAY");std::set<std::string> required,reported;for(const auto& position:f(descriptor,"positions").array())for(const auto& pattern:f(descriptor,"patterns").array())required.insert(position.string()+"/"+pattern.string());bool good=true;for(const auto& item:actual.array()){if(item.null()){good=false;continue;}shape(item,{"position","pattern"});if(f(item,"position").null()||f(item,"pattern").null()){good=false;continue;}need(f(item,"position").isString()&&f(item,"pattern").isString(),"COVERAGE_ITEM_TYPE");if(!reported.insert(s(item,"position")+"/"+s(item,"pattern")).second)good=false;}return good&&reported==required;
    }
    if(kind=="failed_boundary_selection"){
        shape(descriptor,{"kind","failed_node","field","choice_field","boundary_count"});if(failed.null()||!failed.find("payload")||f(failed,"node")!=f(descriptor,"failed_node"))return false;const auto& choice=f(payload,s(descriptor,"choice_field"));if(choice.null())return false;const auto index=n(choice);const auto& reports=f(f(failed,"payload"),s(descriptor,"field"));need(reports.isArray()&&reports.array().size()==static_cast<std::size_t>(n(f(descriptor,"boundary_count"))),"FAILED_BOUNDARY_REPORTS");need(index>=1&&index<=n(f(descriptor,"boundary_count")),"FAILED_BOUNDARY_RANGE");const auto& value=reports.array()[static_cast<std::size_t>(index-1)];return !value.null()&&value!=V("unknown")&&value!=V("no_issue");
    }
    return std::nullopt;
}
} // namespace fathom::tasks::manual_procedure_graph_support
