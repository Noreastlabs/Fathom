#include "Ear234.hpp"
#include "ClosedKernel.hpp"
#include "GeneratedEar234.hpp"
#include "NativeIndexBindings.hpp"
#include "NativeFormAmendment.hpp"
#include "tasks/ManualProcedureDomainReports.hpp"
#include <algorithm>
#include <atomic>
#include <mutex>
#include <numeric>
#include <set>
#include <chrono>
#include <type_traits>
#include "content/Canonical.hpp"

namespace fathom::tasks::ear234 {
using V=closed::Value;
using J=json::Value;
namespace {
[[noreturn]] void refuse(std::string why){throw std::runtime_error("ear234:"+why);}
const J& f(const J& j,const std::string& k){auto p=j.find(k);if(!p)refuse("missing exact field:"+k);return *p;}
std::string s(const J& j,const std::string& k){return f(j,k).string();}
const J& formAmendment(){static const J t=json::parse(nativeFormAmendment);return t;}
const J& indexBinding(){static const J t=json::parse(nativeIndexBindings);return t;}
const J& table(){static const J t=json::parse(generatedTable);return t;}
const std::string& continuationCatalogueSha(){static const auto hash=content::sha256(json::stringify(J::Object{{"catalogue",content::sha256(generatedTable)},{"form_amendment",content::sha256(nativeFormAmendment)},{"index_binding",content::sha256(nativeIndexBindings)}}));return hash;}
static_assert(std::is_nothrow_move_constructible<J>::value,"accepted command append must not throw after native mutation");
std::size_t unicodeLength(const std::string& s){return manual_procedure_graph_support::utf8TextLength(s);}
bool nonempty(const J& j){return j.isString()&&!closed::unicodeStrip(j.string()).empty();}
std::int64_t integer(const J& j){std::int64_t n;if(!j.integer(n))refuse("strict integer");return n;}
J textSchema(bool empty=false){return J::Object{{"type","string"},{"minLength",J::fromInteger(empty?0:1)}};}
J menu(J::Array values){return J::Object{{"type","string"},{"enum",values}};}
J object(J::Object props){J::Array r;for(auto& p:props)r.emplace_back(p.first);return J::Object{{"type","object"},{"properties",props},{"required",r},{"additionalProperties",false}};}
J yesNo(){return menu({"yes","no","uncertain"});}
J availabilitySchema(){return object({{"provider_kind",menu({"external_human","external_recording","public_workbook","own_instrument"})},{"provider_reference",textSchema()},{"material_available",J::Object{{"type",J::Array{"boolean","null"}}}},{"current_source_ready",J::Object{{"type",J::Array{"boolean","null"}}}},{"prior_source_exposure",J::Object{{"type",J::Array{"boolean","null"}}}},{"notes",textSchema()}});}
J releaseSchema(){return object({{"learner_released",J::Object{{"type","boolean"}}},{"source_stopped",J::Object{{"type",J::Array{"boolean","null"}}}},{"notes",textSchema()}});}
J stopSchema(){return object({{"reason",textSchema()}});}
J emptySchema(){return object({});}
std::atomic<std::uint64_t> instances{1};
bool isTrue(const J& j){return j.isBool()&&j.boolean();}
bool vtrue(V v){return v.kind()=="boolean"&&v.truth();}
V attr(V v,const std::string& name){auto p=v.p->attributes.find(name);return p==v.p->attributes.end()?V::none():p->second;}
bool hasAll(V d,std::initializer_list<const char*> keys){if(d.kind()!="dict")return false;for(auto k:keys)if(!d.has(V::string(k)))return false;return true;}
J project(const J& schema,bool source){
    auto role=schema.find("input_role");bool privateRole=role&&role->isString()&&role->string()=="explicit_source_player_only_choice";
    if(privateRole)return source?schema:J();
    if(schema.find("properties")){J::Object props;for(auto& p:f(schema,"properties").object()){auto child=project(p.second,source);if(!child.null())props[p.first]=child;}if(props.empty())return !source&&f(schema,"properties").object().empty()?schema:J();auto result=object(props);result.object()["type"]=f(schema,"type");return result;}
    return source?J():schema;
}
void merge(J& publicInput,const J& privateInput){if(publicInput.isObject()&&privateInput.isObject()){for(auto& p:privateInput.object()){auto i=publicInput.object().find(p.first);if(i==publicInput.object().end())publicInput.object()[p.first]=p.second;else merge(i->second,p.second);}return;}refuse("source/player merge collision");}
}
void validateTypedInput(const J& schema,const J& input){
    auto& kinds=f(schema,"type");auto kind=input.null()?"null":input.isBool()?"boolean":input.isString()?"string":input.isArray()?"array":input.isObject()?"object":"integer";
    bool allowed=false;if(kinds.isString())allowed=kinds.string()==kind;else for(auto& k:kinds.array())allowed|=k.string()==kind;if(!allowed)refuse("typed kind");
    if(auto e=schema.find("enum")){bool hit=false;for(auto& x:e->array())hit|=input==x;if(!hit)refuse("exact enum");}
    if(input.null())return;
    if(input.isNumber()){auto n=integer(input);if(auto p=schema.find("minimum"))if(n<integer(*p))refuse("integer below bound");if(auto p=schema.find("maximum"))if(n>integer(*p))refuse("integer above bound");}
    if(input.isString()){auto n=unicodeLength(input.string());if(auto p=schema.find("minLength"))if(n<static_cast<std::size_t>(integer(*p)))refuse("short text");if(auto p=schema.find("maxLength"))if(n>static_cast<std::size_t>(integer(*p)))refuse("long text");}
    if(input.isArray()){if(input.array().size()<static_cast<std::size_t>(integer(f(schema,"minItems")))||input.array().size()>static_cast<std::size_t>(integer(f(schema,"maxItems"))))refuse("array source extent");for(auto& x:input.array())validateTypedInput(f(schema,"items"),x);}
    if(input.isObject()){auto& props=f(schema,"properties").object();if(!f(schema,"additionalProperties").isBool()||f(schema,"additionalProperties").boolean()||input.object().size()!=props.size())refuse("closed object");std::set<std::string> required;for(auto& x:f(schema,"required").array())required.insert(x.string());if(required.size()!=props.size())refuse("schema fieldset");for(auto& p:props){if(!required.count(p.first)||!input.find(p.first))refuse("required field");validateTypedInput(p.second,f(input,p.first));}}
}
void validateTypedGuards(const J& guards,const J& value){
    if(!guards.isArray())refuse("closed typed guard list");
    for(auto& g:guards.array()){
        auto op=s(g,"operator");std::size_t fields=op=="canonical_rational_pair"?3:2;
        if(!g.isObject()||g.object().size()!=fields||!g.find("path")||!f(g,"path").isArray()||(op!="canonical_rational_pair"&&op!="strictly_increasing_unique_integer_array"&&op!="nonempty_trimmed_text"))refuse("unadmitted typed guard");
        if(op=="canonical_rational_pair"&&(!g.find("allow_zero_numerator")||!f(g,"allow_zero_numerator").isBool()))refuse("typed rational descriptor");
        std::vector<const J*> current{&value};for(auto& component:f(g,"path").array()){if(!component.isString()||component.string().empty())refuse("guard path");std::vector<const J*> next;for(auto p:current){if(p->null())continue;if(component.string()=="*"){if(!p->isArray())refuse("guard wildcard");for(auto& x:p->array())next.push_back(&x);}else next.push_back(&f(*p,component.string()));}current=std::move(next);}
        for(auto p:current){if(p->null())continue;if(op=="nonempty_trimmed_text"){if(!nonempty(*p))refuse("blank manual text");}else if(op=="canonical_rational_pair"){if(!p->isArray()||p->array().size()!=2)refuse("rational pair");auto n=integer(p->array()[0]),d=integer(p->array()[1]);if(d<=0||n<0||(!f(g,"allow_zero_numerator").boolean()&&!n)||std::gcd(n,d)!=1)refuse("noncanonical rational");}else {if(!p->isArray())refuse("source positions");std::int64_t prior=-1;bool first=true;for(auto& x:p->array()){auto n=integer(x);if(!first&&n<=prior)refuse("positions order/duplicate");prior=n;first=false;}}}
    }
}
Definition::Definition(const J& row):key_(s(row,"source_key")),family_(s(row,"family")),sha_(s(row,"contract_sha256")),binding_(row){auto& current=f(f(indexBinding(),"rows"),key_);binding_.object()["native_index_binding"]=f(current,"current_native_index_binding");binding_.object()["native_index_whole_ref"]=f(indexBinding(),"whole_index_ref");binding_.object()["native_metadata_adoption_ref"]=f(indexBinding(),"reviewed_metadata_adoption_ref");}
const std::vector<std::string>& keys(){static const auto k=[](){std::vector<std::string> v;for(auto& x:f(table(),"rows").array())v.push_back(s(x,"source_key"));return v;}();return k;}
const Definition& definition(const std::string& k){static const auto d=[](){std::map<std::string,Definition> v;for(auto& x:f(table(),"rows").array())v.emplace(s(x,"source_key"),Definition(x));return v;}();auto i=d.find(k);if(i==d.end())refuse("foreign exact source key");return i->second;}
Token::Token(std::uint64_t i,std::uint64_t r,std::string k,std::string a,bool role):instance_(i),revision_(r),key_(std::move(k)),action_(std::move(a)),sourceRole_(role){}
struct Owner::Impl {
    Definition definition;
    mutable std::mutex mutex;
    std::uint64_t instance{instances++},revision{1};
    closed::Kernel kernel;
    V self;
    J family,contract;
    J availability;
    std::map<std::string,J> sourceChoices;
    bool releaseDebt{},sourceDebt{},everRevealed{},currentRevealed{},completed{},cancelled{};
    std::string pendingExit;
    J revealedReference,fullReview,diagnosis;
    J::Object verificationMethods;
    J convergence;
    std::vector<J> events;
    J::Array journal;
    J pendingCommand;
    void prepare(J command){if(journal.size()>=100000)refuse("private continuation command limit");journal.reserve(journal.size()+1);pendingCommand=std::move(command);}
    J state()const {J::Object choices;for(const auto& x:sourceChoices)choices.emplace(x.first,x.second);return J::Object{
        {"revision",J::fromInteger(revision)},{"kernel",kernel.continuationState(self)},
        {"availability",availability},{"source_choices",choices},{"release_debt",releaseDebt},{"source_debt",sourceDebt},
        {"ever_revealed",everRevealed},{"current_revealed",currentRevealed},{"completed",completed},{"cancelled",cancelled},
        {"pending_exit",pendingExit},{"revealed_reference",revealedReference},{"full_review",fullReview},{"diagnosis",diagnosis},
        {"verification_methods",verificationMethods},{"convergence",convergence},{"events",J::Array(events.begin(),events.end())}};}
    J bundle()const {return J::Object{{"format","fathom-ear234-private-continuation-v1"},{"source_key",definition.sourceKey()},
        {"binding_sha256",content::sha256(json::stringify(definition.binding()))},{"catalogue_sha256",continuationCatalogueSha()},{"journal",journal},{"state_sha256",content::sha256(json::stringify(state()))}};}

    Impl(const Definition& d):definition(d),kernel(closed::Kernel::fromPinnedSha(s(d.binding(),"kernel_sha256"))),family(f(f(table(),"families"),d.family())),contract(f(f(table(),"contracts"),s(d.binding(),"retained_contract_sha256"))){
        std::vector<V> args;auto ctor=s(d.binding(),"constructor");if(ctor=="key")args.push_back(V::string(d.sourceKey()));else{args.push_back(closed::fromJson(contract));if(ctor=="contract_catalogue")args.push_back(closed::fromJson(f(f(table(),"catalogues"),s(f(contract,"source_catalogue_ref"),"sha256"))));}self=kernel.construct(s(d.binding(),"class"),args);if(d.family()=="rhythm_vocabulary")everRevealed=true;
    }
    bool tokenKernel()const{return kernel.hasMethod(self,"token");}
    std::int64_t cursor(const std::string& name)const{auto v=attr(self,name);return v.kind()=="integer"?v.number():0;}
    std::string modelState()const{auto v=attr(self,"state");return v.kind()=="string"?v.text():attr(self,"phase").kind()=="string"?attr(self,"phase").text():"retained_manual_sequence";}
    std::string stage(const std::string& action)const{
        auto fam=definition.family();
        if(fam=="interval_atlas"&&action=="report")return cursor("phase")==0?"upward":"downward";
        if(fam=="register_transfer"&&(action=="begin"||action=="report"))return cursor("stage")==0?"initial":"transfer";
        if(fam=="function_hearing"&&action=="answer"){auto state=modelState();return state=="answer_family"?"family":state=="answer_roman"?"roman":"chord";}
        if(fam=="progression_dictation"&&action=="answer")return modelState()=="answer_function"?"function":"roman";
        if(fam=="major_voiceleading"&&action=="report")return cursor("phase")==2?"combined":"solo";
        if(fam=="minor_voiceleading_dominant"&&action=="report")return cursor("stage")<3?"vocal":"dominant";
        if(fam=="three_layer_melody"&&action=="commit"){static const char* a[]={"contour","degrees","notes"};auto i=cursor("layer");if(i<0||i>2)refuse("owned layer");return a[i];}
        if((fam=="rhythm_pitch_dictation"||fam=="qqee_motif")&&action=="commit")return cursor("layer")==0?"pitch":"rhythm";
        if((fam=="rhythm_pitch_dictation"||fam=="qqee_motif")&&action=="report_verification"){static const char* a[]={"clap_rhythm","sing_without_rhythm","recombine"};auto i=cursor("stage");if(i<0||i>2)refuse("owned verification stage");return a[i];}
        if(fam=="four_pass_call_response"&&(action=="choose_response"||action=="report")){static const char* a[]={"exact","new_pitches","octave","next_chord"};auto i=cursor("phase");if(i<0||i>3)refuse("owned response phase");return a[i];}
        if(fam=="spoken_degree"&&(action=="begin"||action=="report"))return cursor("stage")==0?"initial":"transfer";
        if(fam=="transcription_workflow"&&action=="submit"){auto i=cursor("stage");auto& a=f(contract,"source_stages").array();if(i<0||static_cast<std::size_t>(i)>=a.size())refuse("owned source stage");return s(a[i],"name");}
        return "";
    }
    const J& action(const std::string& name)const{return f(f(family,"actions"),name);}
    std::pair<J,J> argument(const std::string& name,const std::string& arg)const{
        auto& before=f(f(action(name),"schema"),"properties");auto schema=f(before,arg);if(!schema.find("unresolved_native_form_schema"))return {schema,J::Array{}};
        auto st=stage(name);for(auto& b:f(table(),"bindings").array())if(s(b,"source_key")==definition.sourceKey()&&s(b,"action")==name&&s(b,"argument")==arg&&(st.empty()?f(b,"stage").null():!f(b,"stage").null()&&f(b,"stage").string()==st)){if(s(b,"profile_sha256")==s(formAmendment(),"old_profile_sha256")){bool exact=false;for(auto& key:f(formAmendment(),"exact_source_keys").array())exact|=key.string()==definition.sourceKey();if(!exact||name!="report"||arg!="r")refuse("foreign exact schema amendment");return {f(formAmendment(),"new_typed_schema"),f(formAmendment(),"guards_after")};}auto& p=f(f(table(),"profiles"),s(b,"profile_sha256"));return {f(f(table(),"typed_shapes"),s(p,"schema_sha256")),f(p,"typed_value_guards")};}refuse("unresolved exact owned schema/stage");
    }
    J actionSchema(const std::string& name,bool source)const{J::Object fields;for(auto& arg:f(action(name),"argument_order").array()){auto a=argument(name,arg.string());auto p=project(a.first,source);if(!p.null())fields[arg.string()]=p;}return object(fields);}
    bool externalNow()const{
        auto fam=definition.family();if(fam=="sung_guide_shell"||fam=="major_voiceleading")return false;
        if(fam=="register_transfer"||fam=="spoken_degree")return cursor("stage")==0;
        if(fam=="minor_voiceleading_dominant")return cursor("stage")>=3;
        if(fam=="rhythm_vocabulary")return attr(self,"pair").truth();
        if((fam=="rhythm_pitch_dictation"||fam=="qqee_motif")&&(modelState().find("verif")!=std::string::npos))return false;
        return true;
    }
    bool ready()const{if(availability.null())return false;if(!isTrue(f(availability,"material_available"))||!isTrue(f(availability,"current_source_ready")))return false;auto kind=s(availability,"provider_kind");return !externalNow()||kind=="external_human"||kind=="external_recording";}
    bool enabled(const std::string& name){if(completed||cancelled||!ready())return false;if(name=="finish"||name=="cancel"||name=="reopen"||name=="release")return false;if(name=="sing_guide"&&definition.family()=="sung_guide_shell"&&modelState()!="sing_guide1"&&modelState()!="sing_guide2")return false;if(name=="answer"&&(definition.family()=="function_hearing"||definition.family()=="progression_dictation")&&modelState().find("answer_")!=0)return false;return kernel.enabled(self,name,f(action(name),"argument_order").array().size(),tokenKernel());}
    V call(V target,const std::string& name,const J& input){std::vector<V> args;if(tokenKernel())args.push_back(kernel.invoke(target,"token"));for(auto& a:f(action(name),"argument_order").array())args.push_back(closed::fromJson(f(input,a.string())));return kernel.invoke(target,name,args);}
    std::string boundary()const{return std::to_string(cursor("phase"))+":"+std::to_string(cursor("stage"))+":"+std::to_string(cursor("layer"))+":"+std::to_string(cursor("target"))+":"+std::to_string(cursor("pass_number"))+":"+std::to_string(cursor("generation"));}
    bool revealAction(const std::string& name)const{return name.find("reveal")!=std::string::npos||name=="resolve_tonic"||name=="request_complete_voicing"||name=="request_reduced_rendition"||name=="compare_count_reference"||name=="request_guitar_confirmation";}
    bool bridgeCanReveal()const{
        auto fam=definition.family();if(fam=="progression")return vtrue(attr(self,"answer_committed"));if(fam=="arrangement_comparison")return attr(self,"response").kind()!="none";if(fam=="chord_quality")return attr(self,"responses").has(V::string("quality_response"));if(fam=="form_map")return attr(self,"data").has(V::string("section_labels"));return false;
    }
    bool legacyComplete(){
        auto fam=definition.family();auto d=attr(self,"data"),r=attr(self,"responses");
        if(tokenKernel())return kernel.hasMethod(self,"finish")&&kernel.enabled(self,"finish",0,true);
        if(fam=="tonic_card")return cursor("pass_number")==2&&d.has(V::integer(1))&&d.has(V::integer(2))&&hasAll(d.get(V::integer(1)),{"source_performed_report","singing_attempt_report","answer_committed","one_string_confirmation"})&&hasAll(d.get(V::integer(2)),{"source_performed_report","singing_attempt_report","answer_committed","one_string_confirmation"});
        if(fam=="bass_route")return hasAll(d,{"scale_degrees","pitch_names","chord_families","bass_confirmed_self_report","inversion_roles","upper_voice_evidence_self_report","chord_root_certainty_self_report"})&&vtrue(d.get("bass_confirmed_self_report"));
        if(fam=="chord_quality")return hasAll(r,{"reduced_listening_self_report","quality_response","clue_singing_self_report","comparison_self_report"})&&vtrue(attr(self,"full_voicing_ever_requested"));
        if(fam=="progression")return hasAll(r,{"root_motion","quality","roots_second_listen_confirmed_self_report","written_answer","cadence_note"})&&vtrue(attr(self,"answer_committed"))&&cursor("listen_requests")>=2;
        if(fam=="rhythm_vocabulary")return attr(self,"basic_reports").items().size()==3&&attr(self,"memory_answer").kind()!="none"&&attr(self,"repeat_reports").items().size()==4&&attr(self,"variation_answers").items().size()==3&&vtrue(attr(self,"memory_disclosed"))&&vtrue(attr(self,"variation_disclosed"));
        if(fam=="rhythm_dictation")return kernel.invoke(closed::clone(self),"manual_responses_complete").truth();
        if(fam=="melodic_contour")return hasAll(r,{"listening_self_report","contour_singing_self_report","contour_response","contour_correct_self_report","pitch_response"})&&vtrue(r.get("contour_correct_self_report"))&&vtrue(attr(self,"guitar_ever_requested"));
        if(fam=="structural_target")return hasAll(d,{"external_source_listening_self_report","target_response","current_reduction_requested","verification"})&&vtrue(d.get("verification").get("communicates_harmony_self_report"));
        if(fam=="form_map")return hasAll(d,{"external_basis_self_report","counts","counts_confirmed_self_report","repetition_groups","landmark_notes_self_report","section_labels"})&&vtrue(d.get("counts_confirmed_self_report"));
        if(fam=="layered_lab"){auto scores=attr(self,"scores"),verifications=attr(self,"verifications");return kernel.invoke(closed::clone(self),"complete").truth()&&currentRevealed&&kernel.invoke(closed::clone(self),"relisten_priority").items().empty()&&scores.items().size()==f(contract,"manual_score_layers").array().size()&&verifications.items().size()>=f(contract,"verification_passes").array().size()&&attr(self,"repair").kind()=="none";}
        if(fam=="arrangement_comparison")return attr(self,"harmony").kind()!="none"&&attr(self,"variant").kind()!="none"&&attr(self,"response").kind()!="none"&&attr(self,"renditions").get("baseline").truth()&&attr(self,"renditions").get("variation").truth();
        if(fam=="verification_method")return hasAll(d,{"candidate_reference","observations","conclusion"})&&verificationMethods.size()>=2&&!convergence.null()&&isTrue(f(convergence,"independent_clues"))&&isTrue(f(convergence,"agreement"));
        refuse("unadmitted full-unit family predicate");
    }
    J reviewSchema()const{J::Object duties;for(auto& p:f(family,"subordinate_action_protocols").array())duties[p.string()]=yesNo();return object({{"source_specific_duties",object(duties)},{"comparison_or_verification_basis",textSchema()},{"remaining_debt",yesNo()},{"diagnosis",textSchema(true)},{"notes",textSchema()}});}
    J safePresentation(){
        if(cancelled)return J();
        std::string method=kernel.hasMethod(self,"view")?"view":kernel.hasMethod(self,"learner_view")?"learner_view":"";if(method.empty()){auto fam=definition.family();if(fam=="minor_voiceleading_dominant")return closed::toJson(kernel.invoke(closed::clone(self),"cue"));J::Object publicCue;if(fam=="interval_atlas"||fam=="register_transfer"||fam=="spoken_degree")for(auto key:{"source_fields","source_reference","source_practice","source_no_search_rule","printed_degree"})if(auto value=contract.find(key))publicCue[key]=*value;if(fam=="transcription_workflow")for(auto key:{"source_stages","notation","source_notation","authored_policies"})if(auto value=contract.find(key))publicCue[key]=*value;if(fam=="verification_method")for(auto key:{"source_method","source_question","observation_fields"})if(auto value=contract.find(key))publicCue[key]=*value;return publicCue;}
        kernel.permitExplicitLearnerReference(true);V shown;try{shown=kernel.invoke(closed::clone(self),method);}catch(...){kernel.permitExplicitLearnerReference(false);throw;}kernel.permitExplicitLearnerReference(false);auto value=closed::toJson(shown);
        static const std::set<std::string> referenceFields{"expected_tonic","quality_reference","singing_clue","source_roman_answer","source_pitch_answer","rhythm_reference","source_pitch_reference","source_degree_reference","source_target_reference","source_role_reference","matching_reference_positions","one_plausible_source_label_sequence","reference","source_bars","variation_reference_segments","declared_changed_column","declared_source_variation","source_answer","reference_answer","question_reference","reference_question"};
        if(!currentRevealed)for(auto& field:referenceFields)value.object().erase(field);for(auto iter=value.object().begin();iter!=value.object().end();){if(iter->first.find("disclosure")!=std::string::npos||iter->first=="previously_revealed")iter=value.object().erase(iter);else++iter;}
        // The three public worksheet/study/sung-guide families are already public
        // source cues. Legacy auto-disclosure runs only on a clone and is filtered.
        return value;
    }
    J view(){J::Object out{{"source_key",definition.sourceKey()},{"family",definition.family()},{"revision",J::fromInteger(revision)},{"state",completed?"completed":cancelled?"cancelled":!pendingExit.empty()?"awaiting_exit_release":!ready()?"awaiting_actual_source":"retained_source_action"},{"retained_state",modelState()},{"availability_report",availability},{"manual_release_debt",releaseDebt},{"external_source_stop_debt",sourceDebt},{"prior_reference_disclosure",everRevealed},{"prior_exposure_unknown",availability.null()||f(availability,"prior_source_exposure").null()},{"blind_trial_claim",false},{"explicit_current_reference_disclosure",currentRevealed},{"current_reference",currentRevealed?revealedReference:J()},{"diagnosis",diagnosis},{"full_unit_review",fullReview},{"performance_observed",false},{"source_audio_supplied",false},{"source_clock",nullptr},{"credit_awarded",false},{"runtime_admitted",false},{"SourceIndex_rebind_pending",false},{"native_source_index_authority",f(indexBinding(),"whole_index_ref")},{"instructions",f(family,"learner_safe_instruction")}};out["source_action_presentation"]=safePresentation();out["owned_verification_methods"]=verificationMethods;out["convergence_report"]=convergence;out["verification_established_by_app"]=false;return out;}
    void event(std::string action,const J& input,bool source=false){events.emplace_back(J::Object{{"action",action},{"revision",J::fromInteger(revision)},{"input",source?J():input},{"source_role_input_retained_privately",source},{"retained_state",modelState()},{"manual_release_debt",releaseDebt},{"source_stop_debt",sourceDebt},{"observed_performance",false},{"credit",false}});journal.push_back(std::move(pendingCommand));pendingCommand=J();}
};
Owner::Owner(const Definition& d):impl_(std::make_unique<Impl>(d)){}
Owner::~Owner()=default;
const Definition& Owner::retainedDefinition()const noexcept{return impl_->definition;}
Token Owner::capture(const std::string& action)const{std::lock_guard<std::mutex> l(impl_->mutex);return Token(impl_->instance,impl_->revision,impl_->definition.sourceKey(),action,false);}
Token Owner::captureSourceChoices(const std::string& action)const{std::lock_guard<std::mutex> l(impl_->mutex);return Token(impl_->instance,impl_->revision,impl_->definition.sourceKey(),action,true);}
bool Owner::current(const Token& t)const{std::lock_guard<std::mutex> l(impl_->mutex);return t.instance_==impl_->instance&&t.revision_==impl_->revision&&t.key_==impl_->definition.sourceKey();}
void Owner::apply(const Token& t,const J& input){
    std::lock_guard<std::mutex> l(impl_->mutex);auto& i=*impl_;if(t.instance_!=i.instance||t.revision_!=i.revision||t.key_!=i.definition.sourceKey())refuse("stale/foreign owned gesture");auto name=t.action_;
    i.prepare(J::Object{{"kind","apply"},{"action",name},{"source_role",t.sourceRole_},{"input",input}});
    if(t.sourceRole_){if(i.completed||i.cancelled||!i.pendingExit.empty())refuse("inactive source choice");auto schema=i.actionSchema(name,true);if(f(schema,"properties").object().empty())refuse("no private source choice for action");validateTypedInput(schema,input);i.sourceChoices[name]=input;++i.revision;i.event(name,input,true);return;}
    if(name=="availability"){validateTypedInput(availabilitySchema(),input);if(i.releaseDebt||i.completed||i.cancelled)refuse("availability stage");i.availability=input;if(isTrue(f(input,"prior_source_exposure")))i.everRevealed=true;i.diagnosis=i.ready()?J():J::Object{{"source_or_material_not_ready",true},{"unknown_stays_awaiting",true}};++i.revision;i.event(name,input);return;}
    if(name=="stop"||name=="restart_owned_trial"||name=="navigate"){validateTypedInput(stopSchema(),input);if(i.cancelled)refuse("cancelled owner");i.pendingExit=name;i.completed=false;if(!i.releaseDebt){if(i.kernel.hasMethod(i.self,"cancel")){J p=J::Object{};i.call(i.self,"cancel",p);}i.cancelled=true;i.pendingExit.clear();}++i.revision;i.event(name,input);return;}
    if(name=="reopen"){validateTypedInput(emptySchema(),input);if(!i.cancelled)refuse("not cancelled");i.call(i.self,"reopen",J::Object{});i.cancelled=false;i.completed=false;i.currentRevealed=false;i.releaseDebt=true;i.sourceDebt=false;++i.revision;i.event(name,input);return;}
    if(name=="release"){
        validateTypedInput(releaseSchema(),input);if(!i.releaseDebt&&!i.sourceDebt)refuse("no owned release debt");if(!isTrue(f(input,"learner_released"))||(i.sourceDebt&&!isTrue(f(input,"source_stopped"))))refuse("positive owned role release required");
        auto next=closed::clone(i.self);
        if(!i.pendingExit.empty()){if(i.kernel.hasMethod(next,"cancel"))i.call(next,"cancel",J::Object{});if(attr(next,"source_release_required").kind()=="boolean")next.attribute("source_release_required",V::boolean(false));if(attr(next,"source_stop_requested").kind()=="boolean")next.attribute("source_stop_requested",V::boolean(false));if(attr(next,"partner_release_required").kind()=="boolean")next.attribute("partner_release_required",V::boolean(false));if(attr(next,"partner_stop_requested").kind()=="boolean")next.attribute("partner_stop_requested",V::boolean(false));i.cancelled=true;i.completed=false;i.pendingExit.clear();}
        else if(i.kernel.hasMethod(next,"release")){
            if(!i.kernel.enabled(next,"release",1,i.tokenKernel()))refuse("complete uninterrupted source unit before release; active STOP requires explicit exit request");
            const auto& order=f(i.action("release"),"argument_order").array();if(order.size()!=1)refuse("exact release adapter");auto a=i.argument("release",order[0].string()).first;J payload;
            if(f(a,"type").isString()&&f(a,"type").string()=="boolean")payload=J::Object{{order[0].string(),true}};
            else{auto& props=f(a,"properties").object();J::Object r;for(auto& p:props){if(p.first=="learner_released")r[p.first]=true;else if(p.first=="source_stopped"||p.first=="partner_stopped")r[p.first]=f(input,"source_stopped");else refuse("unknown release role");}payload=J::Object{{order[0].string(),r}};}
            i.call(next,"release",payload);
        }
        i.self=next;i.releaseDebt=i.sourceDebt=false;++i.revision;i.event(name,input);return;
    }
    if(i.completed||i.cancelled||!i.pendingExit.empty()||!i.ready())refuse("source/current owner not ready");
    if(name=="record_convergence"){
        if(i.definition.family()!="verification_method"||i.verificationMethods.size()<2)refuse("two distinct owned methods required");
        validateTypedInput(object({{"independent_clues",J::Object{{"type","boolean"}}},{"agreement",J::Object{{"type","boolean"}}},{"explanation",textSchema()}}),input);
        i.convergence=input;if(!isTrue(f(input,"independent_clues"))||!isTrue(f(input,"agreement")))i.diagnosis=J::Object{{"convergence_debt",true},{"verification_established_by_app",false}};
        ++i.revision;i.event(name,input);return;
    }
    if(name=="explicit_reveal"){
        validateTypedInput(emptySchema(),input);if(i.releaseDebt||i.sourceDebt||!i.bridgeCanReveal())refuse("commit/role release before explicit reveal");auto next=closed::clone(i.self);i.kernel.permitExplicitLearnerReference(true);V shown;try{shown=i.kernel.invoke(next,"learner_view");}catch(...){i.kernel.permitExplicitLearnerReference(false);throw;}i.kernel.permitExplicitLearnerReference(false);i.self=next;i.revealedReference=closed::toJson(shown);i.currentRevealed=i.everRevealed=true;++i.revision;i.event(name,input);return;
    }
    if(name=="complete"){
        validateTypedInput(i.reviewSchema(),input);if(i.releaseDebt||i.sourceDebt||!i.legacyComplete())refuse("complete source procedure before full-unit review");bool yes=s(input,"remaining_debt")=="no";for(auto& d:f(input,"source_specific_duties").object())yes&=d.second.string()=="yes";
        if(!yes){if(!nonempty(f(input,"diagnosis")))refuse("uncertain/negative full-unit diagnosis");i.fullReview=input;i.diagnosis=J::Object{{"full_unit_debt",true}};++i.revision;i.event(name,input);return;}
        auto next=closed::clone(i.self);if(i.tokenKernel())i.call(next,"finish",J::Object{});i.self=next;i.fullReview=input;i.completed=true;i.diagnosis=J();++i.revision;i.event(name,input);return;
    }
    static const std::set<std::string> advances{"begin_second_pass","next_pass","next_direction","next_register","next_stage","next_presentation","next_subpass","next_target"};if(advances.count(name)&&(i.releaseDebt||i.sourceDebt))refuse("owned physical/source release before advancing the full unit");
    if(!i.enabled(name))refuse("retained source guard disables action");
    if(i.revealAction(name)&&(i.releaseDebt||i.sourceDebt))refuse("owned physical/source release before reveal");
    auto schema=i.actionSchema(name,false);validateTypedInput(schema,input);J combined=input;auto priv=i.sourceChoices.find(name);auto srcSchema=i.actionSchema(name,true);if(!f(srcSchema,"properties").object().empty()){if(priv==i.sourceChoices.end())refuse("actual separate source-player choices required");merge(combined,priv->second);}
    for(auto& a:f(i.action(name),"argument_order").array()){auto resolved=i.argument(name,a.string());validateTypedInput(resolved.first,f(combined,a.string()));validateTypedGuards(resolved.second,f(combined,a.string()));}
    auto next=closed::clone(i.self);auto before=i.boundary();V returned;i.kernel.permitExplicitLearnerReference(i.revealAction(name));try{returned=i.call(next,name,combined);}catch(...){i.kernel.permitExplicitLearnerReference(false);throw;}i.kernel.permitExplicitLearnerReference(false);i.self=next;
    if(before!=i.boundary()||name=="submit_pitches"||name=="name_sections"||name=="commit_answer"||name=="commit_written_answer"||name=="commit_quality")i.currentRevealed=false;
    if(i.revealAction(name)){i.currentRevealed=i.everRevealed=true;if(returned.kind()!="none")i.revealedReference=closed::toJson(returned);else if(i.kernel.hasMethod(i.self,"learner_view")){i.kernel.permitExplicitLearnerReference(true);try{i.revealedReference=closed::toJson(i.kernel.invoke(closed::clone(i.self),"learner_view"));}catch(...){i.kernel.permitExplicitLearnerReference(false);throw;}i.kernel.permitExplicitLearnerReference(false);}}
    static const std::set<std::string> physical{"begin","begin_listening","begin_question","begin_dominant","begin_vocal","begin_verification","begin_target","begin_response","setup_target","setup_targets","attempt_attack","attack","play","play_response","add_third","perform_station","report_source_performed","resolve_tonic","request_complete_voicing","request_reduced_rendition","request_guitar_confirmation","report_relisten","report_complete_block_replay","report_singing_attempt","report_one_string_confirmation","record_clue_singing","report_contour_singing","report_reduced_listening","request_listen","report_hearing","report_listening","report_source_listening","report_rendition","report_variation_repeat"};
    if(physical.count(name)){i.releaseDebt=true;if(i.externalNow()&&(name.find("begin")!=std::string::npos||name.find("listen")!=std::string::npos||name.find("hearing")!=std::string::npos||name.find("rendition")!=std::string::npos||name=="report_source_performed"||name=="report_variation_repeat"||name=="resolve_tonic"||name=="request_complete_voicing"||name=="request_reduced_rendition"||name=="request_guitar_confirmation"||name=="report_relisten"))i.sourceDebt=true;}
    if(attr(i.self,"source_release_required").kind()=="boolean")i.sourceDebt=vtrue(attr(i.self,"source_release_required"));
    if(attr(i.self,"partner_release_required").kind()=="boolean")i.sourceDebt=vtrue(attr(i.self,"partner_release_required"));
    if(i.kernel.hasMethod(i.self,"release")&&i.kernel.enabled(i.self,"release",1,i.tokenKernel()))i.releaseDebt=true;
    if(name.find("revise")!=std::string::npos||name.find("restart")!=std::string::npos||name.find("repeat")!=std::string::npos){i.currentRevealed=false;i.fullReview=J();if(i.definition.family()=="verification_method"){i.verificationMethods.clear();i.convergence=J();}}
    ++i.revision;i.event(name,input);
}
void Owner::addVerificationClue(const Token& t,const Owner& other){
    if(this==&other)refuse("same method cannot supply second independent clue");
    std::scoped_lock l(impl_->mutex,other.impl_->mutex);auto&i=*impl_;auto&o=*other.impl_;
    if(t.instance_!=i.instance||t.revision_!=i.revision||t.key_!=i.definition.sourceKey()||t.action_!="add_verification_clue"||t.sourceRole_)refuse("current owned convergence gesture required");
    if(i.definition.family()!="verification_method"||o.definition.family()!="verification_method"||i.cancelled||o.cancelled||i.completed||i.releaseDebt||o.releaseDebt||i.sourceDebt||o.sourceDebt||!i.ready()||!o.ready())refuse("two current released method owners required");
    auto a=attr(i.self,"data"),b=attr(o.self,"data");if(!hasAll(a,{"candidate_reference","observations","conclusion"})||!hasAll(b,{"candidate_reference","observations","conclusion"})||a.get("candidate_reference")!=b.get("candidate_reference"))refuse("completed manual method conclusions for same candidate required");
    auto first=s(i.contract,"method_key"),second=s(o.contract,"method_key");if(first==second||i.verificationMethods.count(second))refuse("duplicate source method");
    i.prepare(J::Object{{"kind","clue"},{"other",o.bundle()}});
    auto pin=[&](Impl& owner,V data){return J::Object{{"source_key",owner.definition.sourceKey()},{"contract_sha256",owner.definition.contractSha256()},{"owner_revision",J::fromInteger(owner.revision)},{"manual_method_data",closed::toJson(data)},{"verification_established_by_app",false}};};
    i.verificationMethods[first]=pin(i,a);i.verificationMethods[second]=pin(o,b);i.convergence=J();++i.revision;i.event("add_verification_clue",J::Object{{"source_key",o.definition.sourceKey()},{"same_candidate",true},{"independence_not_inferred",true}});
}
J Owner::learnerView()const{std::lock_guard<std::mutex> l(impl_->mutex);return impl_->view();}
J Owner::learnerActions()const{std::lock_guard<std::mutex> l(impl_->mutex);auto& i=*impl_;J::Object out{{"availability",availabilitySchema()},{"stop",stopSchema()},{"restart_owned_trial",stopSchema()},{"navigate",stopSchema()}};if(i.releaseDebt||i.sourceDebt)out["release"]=releaseSchema();if(i.cancelled)out["reopen"]=emptySchema();if(!i.cancelled&&!i.completed&&i.pendingExit.empty()&&i.ready()){for(auto& a:f(i.family,"actions").object())if(i.enabled(a.first))out[a.first]=i.actionSchema(a.first,false);if(!i.releaseDebt&&!i.sourceDebt&&i.bridgeCanReveal())out["explicit_reveal"]=emptySchema();if(i.definition.family()=="verification_method"&&i.verificationMethods.size()>=2)out["record_convergence"]=object({{"independent_clues",J::Object{{"type","boolean"}}},{"agreement",J::Object{{"type","boolean"}}},{"explanation",textSchema()}});if(!i.releaseDebt&&!i.sourceDebt&&i.legacyComplete())out["complete"]=i.reviewSchema();}return out;}
J Owner::sourcePlayerView()const{std::lock_guard<std::mutex> l(impl_->mutex);auto& i=*impl_;J::Object forms;for(auto& a:f(i.family,"actions").object()){auto shape=i.actionSchema(a.first,true);if(!f(shape,"properties").object().empty())forms[a.first]=shape;}J::Object choices;for(auto& p:i.sourceChoices)choices[p.first]=p.second;return J::Object{{"role","trusted_source_player"},{"retained_source_contract",i.contract},{"source_choice_forms",forms},{"saved_source_choices",choices},{"actual_source_supplied_by_application",false}};}
std::vector<J> Owner::history()const{std::lock_guard<std::mutex> l(impl_->mutex);return impl_->events;}
bool Owner::fenceInactiveForNavigation(){std::lock_guard<std::mutex> l(impl_->mutex);auto& i=*impl_;if(i.releaseDebt||i.sourceDebt||(!i.cancelled&&!i.completed&&i.events.size()>0))return false;i.prepare(J::Object{{"kind","inactive_fence"}});++i.revision;i.event("inactive_navigation_fence",J::Object{});return true;}
namespace {
json::Limits continuationLimits(){json::Limits l;l.bytes=64*1024*1024;l.stringBytes=4*1024*1024;l.depth=96;l.values=2000000;return l;}
}
std::string Owner::continuation()const {
    J body;{std::lock_guard<std::mutex> l(impl_->mutex);body=impl_->bundle();}
    const auto bytes=json::stringify(J::Object{{"body",body},{"sha256",content::sha256(json::stringify(body))}});
    json::parse(bytes,continuationLimits());
    auto verified=restoreContinuation(impl_->definition,bytes);
    {std::lock_guard<std::mutex> l(verified->impl_->mutex);if(verified->impl_->bundle()!=body)refuse("private replay differs");}
    return bytes;
}
std::unique_ptr<Owner> Owner::restoreContinuation(const Definition& expected,const std::string& bytes,const ContinuationResolver& supplied){
    const auto envelope=json::parse(bytes,continuationLimits());
    if(!envelope.isObject()||envelope.object().size()!=2||s(envelope,"sha256")!=content::sha256(json::stringify(f(envelope,"body"))))refuse("private continuation envelope/checksum");
    const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(10);
    std::size_t commands=0;
    const auto resolve=[&](const std::string& key)->const Definition&{return supplied?supplied(key):definition(key);};
    std::function<std::unique_ptr<Owner>(const Definition&,const J&,std::size_t)> replay;
    replay=[&](const Definition& def,const J& b,std::size_t depth)->std::unique_ptr<Owner>{
        if(depth>32||std::chrono::steady_clock::now()>deadline)refuse("private replay budget");
        if(!b.isObject()||b.object().size()!=6||s(b,"format")!="fathom-ear234-private-continuation-v1"||s(b,"catalogue_sha256")!=continuationCatalogueSha()||s(b,"source_key")!=def.sourceKey()||s(b,"binding_sha256")!=content::sha256(json::stringify(def.binding())))refuse("private source/format differs; original preserved");
        auto out=std::make_unique<Owner>(def);
        for(const auto& command:f(b,"journal").array()){
            if(++commands>100000||std::chrono::steady_clock::now()>deadline)refuse("private replay command/time limit");
            const auto kind=s(command,"kind");
            if(kind=="apply"&&command.object().size()==4){auto role=f(command,"source_role").boolean();auto token=role?out->captureSourceChoices(s(command,"action")):out->capture(s(command,"action"));out->apply(token,f(command,"input"));}
            else if(kind=="inactive_fence"&&command.object().size()==1){if(!out->fenceInactiveForNavigation())refuse("private inactive fence differs");}
            else if(kind=="clue"&&command.object().size()==2){const auto& peer=f(command,"other");auto other=replay(resolve(s(peer,"source_key")),peer,depth+1);out->addVerificationClue(out->capture("add_verification_clue"),*other);}
            else refuse("private command shape/kind");
        }
        if(out->impl_->journal!=f(b,"journal").array()||content::sha256(json::stringify(out->impl_->state()))!=s(b,"state_sha256"))refuse("private native replay state differs");
        return out;
    };
    return replay(expected,f(envelope,"body"),0);
}
} // namespace fathom::tasks::ear234
