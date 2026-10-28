#include "desktop/CompiledManualProcedureView.hpp"
#include "desktop/ManualWorkspaceDraft.hpp"
#include "tasks/ContactSnapshotValues.hpp"
#include <future>
#include <chrono>
#include "tasks/C1661HiddenSourceSeven.hpp"
#include "desktop/ManualSourceChoiceLabels.hpp"
#include "desktop/ManualReportWorkspace.hpp"
#include <algorithm>
#include <sstream>

namespace fathom::desktop {
namespace {
using V=json::Value;using O=V::Object;using A=V::Array;
namespace C=tasks::manual_procedure_graph;namespace M=tasks::ordered_contacts::manual;
const V& f(const V& v,const char* k){const auto* p=v.find(k);if(!p)throw tasks::recipes::Error("VIEW_FIELD");return *p;}
void clearDraftChoices(juce::ComboBox& menu){
    menu.clear(juce::dontSendNotification);auto& properties=menu.getProperties();
    for(int i=properties.size();i-->0;){const auto name=properties.getName(i);if(name.toString().startsWith("draft-"))properties.remove(name);}
}
juce::String ju(const std::string& s){return juce::String::fromUTF8(s.c_str());}
V number(std::size_t n){return V::fromInteger(static_cast<std::int64_t>(n));}
// The native schema distinguishes immutable printed bindings from reports.
// Supply only the presentation label required by the form; values and native
// validation stay unchanged. Unmarked or incorrectly marked constants retain
// the form's refusal behavior.
V labeledCurriculumSchema(V schema){
    if(!schema.isObject())return schema;
    schema=manual_source_choice_labels::projectEnumLabels(std::move(schema));
    const auto* source=schema.find("source_constant");const auto* role=schema.find("input_role");
    if(schema.find("const")&&!schema.find("literal_binding_label")&&source&&*source==V(true)&&role&&*role==V("source_binding"))schema.object().emplace("literal_binding_label","source_protocol_binding");
    if(const auto* properties=schema.find("properties");properties&&properties->isObject())for(auto& item:schema.object().at("properties").object())item.second=labeledCurriculumSchema(item.second);
    if(const auto* items=schema.find("items"))schema.object().at("items")=labeledCurriculumSchema(*items);
    return schema;
}
std::string human(std::string s){std::replace(s.begin(),s.end(),'_',' ');if(!s.empty()&&s[0]>='a'&&s[0]<='z')s[0]=static_cast<char>(s[0]-'a'+'A');return s;}
const char* stateName(M::State s){switch(s){case M::State::Setup:return "setup";case M::State::Traversal:return "traversal";case M::State::Boundary:return "boundary";case M::State::Release:return "release";case M::State::Review:return "review";case M::State::Finished:return "finished";case M::State::Cancelled:return "cancelled";case M::State::SourcePhase:return "source_phase";}return "";}
const char* actionName(M::Action a){switch(a){case M::Action::Begin:return "begin";case M::Action::Contact:return "contact";case M::Action::BoundaryReport:return "boundary_report";case M::Action::Release:return "release";case M::Action::LoopReport:return "loop_report";case M::Action::OppositeStart:return "opposite_start";case M::Action::Repeat:return "repeat";case M::Action::AdvancePass:return "advance_pass";case M::Action::Finish:return "finish";case M::Action::Retry:return "retry";case M::Action::Cancel:return "cancel";case M::Action::Restart:return "restart";case M::Action::SessionReport:return "session_report";case M::Action::ReduceTempo:return "reduce_tempo";case M::Action::PlanIncrease:return "plan_increase";case M::Action::ExtensionReport:return "extension_report";case M::Action::SourcePracticeReport:return "source_practice_report";case M::Action::SourceIssueReport:return "source_issue_report";case M::Action::SourcePhaseReport:return "source_phase_report";case M::Action::SourceRepairReport:return "source_repair_report";}return "";}
std::string readable(const V& v){
    if(v.null())return "Unknown / not supplied";if(v.isString()){auto s=v.string();if(s.rfind("exercise-completeness-r01/",0)==0||s.rfind("proposed-printed-",0)==0)return "Your selected printed case";if(s.size()>240){std::size_t end=240;while(end&&(static_cast<unsigned char>(s[end])&0xc0)==0x80)--end;s.resize(end);s+=" … Full response retained.";}return s;}
    if(v.isBool())return v.boolean()?"Yes":"No";if(v.isNumber())return std::get<json::Number>(v.data).token;
    std::ostringstream out;bool first=true;if(v.isObject()){for(const auto& p:v.object()){if(!first)out<<"; ";first=false;out<<human(p.first)<<": "<<readable(p.second);}}else if(v.isArray()){for(const auto& x:v.array()){if(!first)out<<" | ";first=false;out<<readable(x);}}return out.str();
}
std::string completeReportText(const V&v){
    if(v.null())return "Unknown / not supplied";if(v.isString())return v.string();if(v.isBool())return v.boolean()?"Yes":"No";if(v.isNumber())return std::get<json::Number>(v.data).token;
    std::ostringstream out;bool first=true;if(v.isObject())for(const auto&p:v.object()){if(!first)out<<"; ";first=false;out<<human(p.first)<<": "<<completeReportText(p.second);}else if(v.isArray())for(std::size_t i=0;i<v.array().size();++i){if(!first)out<<" | ";first=false;out<<"Entry "<<i+1<<": "<<completeReportText(v.array()[i]);}return out.str();
}
std::string stateSummary(const V& v){
    std::ostringstream out;if(const auto* check=v.find("printed_self_check"))out<<"Printed self-check you explicitly revealed\n"<<readable(*check)<<"\n\n";
    out<<"Your retained manual state\n";
    if(const auto* extra=v.find("extra_source_identity");extra&&extra->isBool()&&extra->boolean()){const auto* reference=v.find("reference_only");if(reference&&reference->isBool()&&reference->boolean())out<<"Reference and source-defect explanation only. A faithful full rendition of the original task is unavailable. Closing this reference does not complete that musical task.\n";else out<<"Qualified manual source version. Its exact source interpretation and original limitations remain explicit; no official-child or credit claim.\n";}
    if(v.find("node")){out<<"Follow the current printed procedure above. Your earlier choices and reports stay retained.\n";if(const auto* depth=v.find("call_depth")){std::int64_t n{};depth->integer(n);if(n>1)out<<"An additional printed procedure is open.\n";}}
    else if(const auto* cursor=v.find("cursor")){std::int64_t n{},total{};cursor->integer(n);f(v,"step_count").integer(total);out<<"Source step "<<std::min(n+1,total)<<" of "<<total<<".\n";}
    if(const auto* pass=v.find("pass_number"))out<<"Current printed pass: "<<readable(*pass)<<".\n";
    if(const auto* next=v.find("next_contact"))out<<"Next contact: "<<readable(*next)<<".\n";
    if(f(v,"needs_manual_release").boolean())out<<"Explicit manual release is still required.\n";
    if(const auto* debt=v.find("tempo_reduction_due");debt&&debt->boolean())out<<"Your pending source tempo reduction stays required.\n";
    const auto* sourceDebt=v.find("retained_source_debt_kind");
    if(const auto* debt=v.find("required_reported_tempo_reduction");debt&&debt->boolean()){if(sourceDebt&&sourceDebt->isString()&&sourceDebt->string()!="tempo_reduction")out<<"Your printed source duty and its required repair remain due.\n";else out<<"Your reported tempo reduction remains required.\n";}
    if(const auto* report=v.find("source_report_unresolved");report&&report->boolean())out<<"The current source phase remains unresolved by your reports.\n";
    if(const auto* repair=v.find("source_repair_due");repair&&repair->boolean()&&!sourceDebt)out<<"The printed source repair and its explicit report are still required.\n";
    if(const auto* ceiling=v.find("retained_reported_bpm_ceiling");ceiling&&!ceiling->null())out<<"Retained limit from your tempo reports: "<<readable(*ceiling)<<" BPM.\n";
    for(const auto& binding:std::initializer_list<std::pair<const char*,const char*>>{{"manual_clean_loops","Clean loops you reported"},{"manual_reported_errors","Errors you reported"},{"reported_bpm","Your reported BPM"},{"planned_next_session_bpm","Your planned next-session BPM"}})if(const auto* value=v.find(binding.first)){if(!value->null())out<<binding.second<<": "<<readable(*value)<<".\n";}
    if(const auto* reports=v.find("learner_responses"))for(const auto& p:reports->object())out<<human(p.first)<<": "<<readable(p.second)<<"\n";
    if(const auto* exposed=v.find("self_check_exposed_in_history");exposed&&exposed->boolean())out<<"Your history retains the earlier printed self-check exposure.\n";
    if(const auto* audit=v.find("family_audit_unperformed_or_unresolved");audit&&audit->boolean())out<<"The recording family audit is still unperformed or unresolved.\n";
    if(const auto* obligations=v.find("remaining_manual_obligations"))for(const auto& line:obligations->array())out<<line.string()<<"\n";
    auto text=out.str();if(text.size()>3000){std::size_t end=3000;while(end&&(static_cast<unsigned char>(text[end])&0xc0)==0x80)--end;text.resize(end);text+="\n… Full typed reports remain retained by the native owner.";}return text;
}
}
ManualProcedureButton::ManualProcedureButton(){onClick=[this]{if(!capture||!deliver)return;const auto now=juce::Time::getMillisecondCounter();const auto g=pending_?*pending_:capture();pending_.reset();if(delivered_&&now-lastDeliveryMs_<350)return;delivered_=true;lastDeliveryMs_=now;deliver(g);};}
void ManualProcedureButton::mouseDown(const juce::MouseEvent& e){if(capture)pending_.emplace(capture());juce::TextButton::mouseDown(e);}
bool ManualProcedureButton::keyPressed(const juce::KeyPress& k){if(k.getKeyCode()==juce::KeyPress::spaceKey||k.getKeyCode()==juce::KeyPress::returnKey){if(capture)pending_.emplace(capture());triggerClick();return true;}return juce::TextButton::keyPressed(k);}
struct CompiledManualProcedureView::Drafts {
    struct Work {ManualProcedureFamily family{ManualProcedureFamily::Curriculum};std::string kind,key,id;storage::Reply receipt;std::uint64_t serial{};std::int64_t revision{};std::shared_ptr<storage::manual_drafts::Publication> publication;std::optional<manual_draft::Restored> restored;std::optional<manual_draft::RestoredContact> restoredContact;json::Value rows;bool more{};std::string cursor;};
    storage::ProfileStore* store{};std::string profile,cursor;bool more{},resumeAfterJob{};std::optional<std::future<Work>> job;
    std::shared_ptr<storage::manual_drafts::Publication> pending;std::string pendingKey,pendingId;ManualProcedureFamily pendingFamily{ManualProcedureFamily::Curriculum};std::uint64_t pendingSerial{};std::int64_t pendingRevision{};std::string pendingCode;bool workerUncertain{};storage::Status pendingStatus=storage::Status::Confirmed;
    std::vector<std::shared_ptr<storage::manual_drafts::Publication>> retired;
};
CompiledManualProcedureView::CompiledManualProcedureView(){
    drafts_=std::make_unique<Drafts>();
    setComponentID("shared-procedure-view");heading_.setComponentID("shared-procedure-heading");phase_.setComponentID("shared-procedure-phase");status_.setComponentID("shared-procedure-status");
    for(auto* l:{&heading_,&phase_,&status_,&actionLabel_})l->setColour(juce::Label::textColourId,juce::Colour(0xff182b33));
    actionLabel_.setText("Choose your next action",juce::dontSendNotification);actions_.setComponentID("shared-procedure-actions");actions_.setTitle("Next manual action");actions_.setTextWhenNothingSelected("Choose explicitly");
    manual_text::configureReadOnly(retainedState_,"shared-procedure-retained-state","Your reported actions and remaining duties");retainedState_.setColour(juce::TextEditor::textColourId,juce::Colour(0xff182b33));retainedState_.setColour(juce::TextEditor::backgroundColourId,juce::Colours::white);
    for(auto* c:std::initializer_list<juce::Component*>{&heading_,&phase_,&status_,&actionLabel_,&actions_,&retainedState_,&form_,&submit_,&back_,&settings_})addAndMakeVisible(*c);
    submit_.setComponentID("shared-procedure-submit");submit_.setButtonText("Submit my report");back_.setComponentID("shared-procedure-back");back_.setButtonText("Back to Learn");settings_.setComponentID("shared-procedure-settings");settings_.setButtonText("Settings");
    juce::Component::SafePointer<CompiledManualProcedureView> safe(this);
    submit_.capture=[safe]{return safe?safe->capture("submit"):ManualProcedureGesture{};};submit_.deliver=[safe](const ManualProcedureGesture& g){if(safe)safe->command(g);};
    back_.capture=[safe]{return safe?safe->capture("navigation"):ManualProcedureGesture{};};settings_.capture=back_.capture;
    back_.deliver=[safe](const ManualProcedureGesture& g){if(safe)safe->navigation(g,false);};settings_.deliver=[safe](const ManualProcedureGesture& g){if(safe)safe->navigation(g,true);};
    form_.onEdited=[safe](const std::string& path){if(safe)safe->edited(path);};
    sourceRoleButton_.setComponentID("hidden-seven-source-role");sourceRoleButton_.setButtonText("Enter trusted Source player role");
    listenerRoleButton_.setComponentID("hidden-seven-listener-role");listenerRoleButton_.setButtonText("Return to listener role");
    addChildComponent(sourceRoleButton_);addChildComponent(listenerRoleButton_);
    for(auto* c:std::initializer_list<juce::Component*>{&saveDraft_,&listDrafts_,&moreDrafts_,&savedDrafts_,&reopenDraft_,&checkDraft_,&copyHistory_})addAndMakeVisible(*c);
    copyHistory_.setComponentID("manual-history-copy");copyHistory_.onClick=[safe]{if(safe)safe->copyLearnerHistory();};
    saveDraft_.setComponentID("manual-draft-save");listDrafts_.setComponentID("manual-draft-list");moreDrafts_.setComponentID("manual-draft-more");savedDrafts_.setComponentID("manual-draft-selection");reopenDraft_.setComponentID("manual-draft-reopen");checkDraft_.setComponentID("manual-draft-check");savedDrafts_.setTextWhenNothingSelected("Select a saved draft for this task");
    saveDraft_.onClick=[safe]{if(safe)safe->saveCurrentDraft();};listDrafts_.onClick=[safe]{if(safe)safe->refreshSavedDrafts();};moreDrafts_.onClick=[safe]{if(safe)safe->refreshSavedDrafts(true);};reopenDraft_.onClick=[safe]{if(safe)safe->reopenSelectedDraft();};checkDraft_.onClick=[safe]{if(safe)safe->reconcileDraft();};
    sourceRoleButton_.capture=[safe]{return safe?safe->capture("source_role"):ManualProcedureGesture{};};
    listenerRoleButton_.capture=sourceRoleButton_.capture;
    sourceRoleButton_.deliver=[safe](const ManualProcedureGesture& g){if(safe)safe->switchSourceRole(g,true);};
    listenerRoleButton_.deliver=[safe](const ManualProcedureGesture& g){if(safe)safe->switchSourceRole(g,false);};render(true);
}
CompiledManualProcedureView::~CompiledManualProcedureView()=default;
CompiledManualProcedureView::Owner* CompiledManualProcedureView::owner() noexcept{auto it=owners_.find({family_,key_});return it==owners_.end()?nullptr:&it->second;}
const CompiledManualProcedureView::Owner* CompiledManualProcedureView::owner()const noexcept{auto it=owners_.find({family_,key_});return it==owners_.end()?nullptr:&it->second;}
const C::ManualProcedureGraph* CompiledManualProcedureView::curriculumTask()const noexcept{const auto* p=owner();return p?p->curriculum.get():nullptr;}
const M::Task* CompiledManualProcedureView::contactTask()const noexcept{const auto* p=owner();return p?p->contact.get():nullptr;}
std::size_t CompiledManualProcedureView::retainedHistoryCount()const{std::size_t n{};for(const auto& it:owners_)n+=it.second.curriculum?it.second.curriculum->historyCount():it.second.contact->history().size();return n;}
V CompiledManualProcedureView::learnerView()const{
    const auto* p=owner();if(!p)return nullptr;if(p->curriculum){auto v=p->curriculum->learnerView();v.object().erase("source_key");v.object().erase("diagnosis");if(hiddenSevenOwner()){v.object()["intentional_source_role_presentation_seen"]=(p->intentionalSourcePresentationSeen||p->curriculum->sourcePresentationSeen());v.object()["fresh_unseen_listening_claim"]=false;}return v;}
    const auto v=p->contact->view();A obligations;for(const auto& s:v.coverage.remainingManualObligations)obligations.emplace_back(s);
    V result=O{{"state",stateName(v.state)},{"pass_number",number(v.passIndex+1)},{"next_contact",number(v.nextOrdinal)},{"needs_manual_release",v.needsManualRelease},{"needs_boundary_report",v.needsBoundaryReport},{"tempo_reduction_due",v.tempoReductionDue},{"manual_clean_loops",number(v.reportedCleanLoops)},{"manual_reported_errors",number(v.reportedErrors)},{"reported_bpm",v.reportedBpm?V::fromInteger(*v.reportedBpm):V(nullptr)},{"planned_next_session_bpm",v.plannedNextSessionBpm?V::fromInteger(*v.plannedNextSessionBpm):V(nullptr)},{"remaining_manual_obligations",obligations},{"observed_performance",false},{"grants_credit",false},{"automatic_mastery",false},{"source_clock",nullptr}};
    const auto sourceFamily=p->contact->sourceHandle().family();
    if(sourceFamily==tasks::manual_contacts::Family::HarmonicContact||sourceFamily==tasks::manual_contacts::Family::SourceContact){result.object().emplace("source_phase_number",number(v.sourcePhaseIndex+1));result.object().emplace("source_report_unresolved",v.sourcePhaseUnresolved);result.object().emplace("source_repair_due",v.sourceRepairDue.has_value());}
    return result;
}
V CompiledManualProcedureView::learnerActions()const{const auto* p=owner();if(!p)return A{};if(p->curriculum)return p->curriculum->learnerActions();A actions;for(const auto& d:p->contact->actionDescriptors())actions.emplace_back(O{{"action",actionName(d.action)},{"label",d.label}});return actions;}
bool CompiledManualProcedureView::hiddenSevenOwner()const{const auto* p=owner();return p&&p->curriculum&&C::hidden_seven::owns(key_);}
V CompiledManualProcedureView::committedReportGroups()const{
    const auto*p=owner();if(!p||!p->curriculum||hiddenSevenOwner()||sourceRole_)return A{};
    const auto&d=p->curriculum->retainedDefinition();
    return manual_workspace::reportGroups(p->curriculum->history(),O{{"source_key",d.sourceKey()},{"contract_sha256",d.contractSha256()},{"own_closure_sha256",d.sourceClosureSha256()}},false);
}
V CompiledManualProcedureView::presentationActions()const{if(hiddenSevenOwner()&&sourceRole_)return owner()->curriculum->sourcePlayerActions();return learnerActions();}
V CompiledManualProcedureView::presentationView()const{if(hiddenSevenOwner()&&sourceRole_){const auto trusted=owner()->curriculum->sourcePlayerView();return f(trusted,"current_trusted_source_reports");}return learnerView();}
void CompiledManualProcedureView::switchSourceRole(const ManualProcedureGesture& g,bool source){if(g.role_!="source_role"||!current(g)||!hiddenSevenOwner()||navigationPrepared_)return;if(!cacheFormDraft())return;++owner()->draftSerial;if(source){owner()->curriculum->recordSourcePresentation();owner()->intentionalSourcePresentationSeen=true;}sourceRole_=source;++generation_;message_=source?"Intentional trusted Source presentation. This caller role is not authentication; original scripts may disclose the reference. No fresh unseen listening or verified hearing is claimed.":"Listener projection restored. Earlier intentional Source access stays retained; no fresh unseen listening is claimed.";render(true);}
std::string CompiledManualProcedureView::phase()const{const auto v=learnerView();return v.null()?"":f(v,"state").string();}
bool CompiledManualProcedureView::inactive()const{const auto* p=owner();if(!p)return true;if(p->curriculum){const auto v=p->curriculum->learnerView();const auto s=f(v,"state").string();return !f(v,"needs_manual_release").boolean()&&(s=="select"||s=="completed"||s=="cancelled");}const auto v=p->contact->view();return !v.needsManualRelease&&(v.state==M::State::Setup||v.state==M::State::Finished||v.state==M::State::Cancelled);}
void CompiledManualProcedureView::fenceInactive(){
    auto* p=owner();if(!p)return;
    A fields;for(const auto& entry:p->fieldDrafts)fields.push_back(entry.second);
    const auto before=ownerDraftWatermark();
    const auto carried=manual_draft::carryInactiveLearnerForms(fields,before,before+1);
    std::map<std::string,V> next;for(const auto& record:carried.array())next.emplace(manual_draft::slot(record),record);
    if(p->curriculum){if(!p->curriculum->fenceInactiveForNavigation())throw tasks::recipes::Error("ACTIVE_NAVIGATION");}else{p->adapter->deactivateForNavigation();}
    p->fieldDrafts.swap(next);++p->draftSerial;
}
bool CompiledManualProcedureView::open(const std::string& key){
    if(draftBusy()||draftPending())return false;if(!cacheFormDraft())return false;
    const C::Definition* cd=nullptr;std::optional<tasks::manual_contacts::SourceHandle> source;
    try{cd=&C::definition(key);}catch(const std::exception&){}
    if(!cd)try{source.emplace(tasks::manual_contacts::SourceHandle::orderedKey(key));}catch(const std::exception&){}
    if(!cd&&!source)try{source.emplace(tasks::manual_contacts::SourceHandle::physicalKey(key));}catch(const std::exception&){}
    if(!cd&&!source)try{source.emplace(tasks::manual_contacts::SourceHandle::piecewiseKey(key));}catch(const std::exception&){}
    if(!cd&&!source)try{source.emplace(tasks::manual_contacts::SourceHandle::harmonicKey(key));}catch(const std::exception&){}
    if(!cd&&!source)try{source.emplace(tasks::manual_contacts::SourceHandle::sourceContactKey(key));}catch(const std::exception&){}
    if(!cd&&!source){message_="This task is outside the verified manual families. The current task remains retained.";render();return false;}
    if(owner()&&!inactive()){message_="Finish the current release and cancellation before opening a task.";render();return false;}
    try{
        const auto family=cd?ManualProcedureFamily::Curriculum:ManualProcedureFamily::OrderedContact;
        const OwnerKey id{family,key};auto it=owners_.find(id);
        // Prepare a new definition/owner before touching the outgoing owner.
        if(it==owners_.end()){Owner next;if(cd)next.curriculum=std::make_unique<C::ManualProcedureGraph>(*cd);else{next.contact=std::make_unique<M::Task>(*source);next.adapter=std::make_unique<M::OrderedContactTaskFormAdapter>(*next.contact);}it=owners_.emplace(id,std::move(next)).first;}
        const bool changed=family_!=family||key_!=key;fenceInactive();family_=family;key_=key;if(changed){clearDraftChoices(savedDrafts_);drafts_->cursor.clear();drafts_->more=false;}sourceRole_=false;++generation_;navigationPrepared_=pendingNavigation_=false;message_.clear();render(true);return true;
    }catch(const std::exception&){message_="Opening this task was refused. Retained work is preserved.";render();return false;}
}
bool CompiledManualProcedureView::openExtraSource(const tasks::extra_source17::InstalledExtraSource17Registry& registry,const std::string& identity){
    if(draftBusy()||draftPending())return false;if(!cacheFormDraft())return false;
    try{
        const auto candidate=registry.definitionForSourceIdentity(identity);
        if(!candidate){message_="This source version is outside the verified extra-source package. Retained work is preserved.";render();return false;}
        if(owner()&&!inactive()){message_="Finish the current release and cancellation before opening a source version.";render();return false;}
        const OwnerKey id{ManualProcedureFamily::Curriculum,candidate->sourceKey()};auto it=owners_.find(id);
        if(it==owners_.end()){Owner next;next.curriculum=std::make_unique<C::ManualProcedureGraph>(*candidate);it=owners_.emplace(id,std::move(next)).first;}
        const bool changed=family_!=ManualProcedureFamily::Curriculum||key_!=candidate->sourceKey();fenceInactive();family_=ManualProcedureFamily::Curriculum;key_=candidate->sourceKey();if(changed){clearDraftChoices(savedDrafts_);drafts_->cursor.clear();drafts_->more=false;}sourceRole_=false;++generation_;navigationPrepared_=pendingNavigation_=false;message_.clear();render(true);return true;
    }catch(const std::exception&){message_="Opening this qualified source version was refused. Retained work is preserved.";render();return false;}
}
ManualProcedureGesture CompiledManualProcedureView::capture(const std::string& role)const{
    ManualProcedureGesture g;g.generation_=generation_;g.family_=family_;g.key_=key_;g.role_=role;g.sourceRole_=sourceRole_;g.formGeneration_=form_.formGeneration();const auto* p=owner();if(!p)return g;
    try{
        if(p->curriculum){
            if(hiddenSevenOwner()&&role=="source_role"){const auto source=p->curriculum->sourcePlayerActions();if(!source.array().empty()){const auto a=f(source.array().front(),"action").string();g.action_=a;g.token_.emplace<C::SourceRoleAction>(p->curriculum->captureSourceAction(a));return g;}const auto listener=p->curriculum->learnerActions();if(!listener.array().empty()){const auto a=f(listener.array().front(),"action").string();g.action_=a;g.token_.emplace<C::Token>(p->curriculum->capture(a));return g;}}
            const auto available=presentationActions();std::string a=role=="submit"?selectedAction_:"";if(a.empty()&&!available.array().empty())a=f(available.array().front(),"action").string();if(a.empty())return g;g.action_=a;if(hiddenSevenOwner()&&sourceRole_)g.token_.emplace<C::SourceRoleAction>(p->curriculum->captureSourceAction(a));else g.token_.emplace<C::Token>(p->curriculum->capture(a));}
        else{g.nativeRevision_=p->contact->view().revision;if(role=="submit"&&contactForm_){g.action_=selectedAction_;g.token_.emplace<M::FormToken>(contactForm_->token);}
          else{const auto available=p->contact->actionDescriptors();if(available.empty())return g;const auto it=std::find_if(available.begin(),available.end(),[](const M::ActionDescriptor& a){return a.action==M::Action::Cancel;});const auto a=it==available.end()?available.front().action:it->action;g.action_=actionName(a);g.token_.emplace<M::Token>(p->contact->capture(a));}}
    }catch(const std::exception&){}return g;
}
bool CompiledManualProcedureView::current(const ManualProcedureGesture& g)const{
    if(draftBusy()||g.generation_!=generation_||g.family_!=family_||g.key_!=key_||navigationPrepared_||(hiddenSevenOwner()&&g.sourceRole_!=sourceRole_))return false;const auto* p=owner();if(!p)return g.family_==ManualProcedureFamily::None;
    try{if(const auto* t=std::get_if<C::SourceRoleAction>(&g.token_))return hiddenSevenOwner()&&p->curriculum&&p->curriculum->current(*t);if(const auto* t=std::get_if<C::Token>(&g.token_))return p->curriculum&&p->curriculum->current(*t);
      if(p->contact&&g.nativeRevision_==p->contact->view().revision){if(const auto* t=std::get_if<M::FormToken>(&g.token_))return p->adapter->current(*t)&&g.formGeneration_==form_.formGeneration();return std::holds_alternative<M::Token>(g.token_);}
      // A completed curriculum has no action, but its inactive navigation
      // gesture still binds the opaque outer view ownership generation.
      return p->curriculum&&std::holds_alternative<std::monostate>(g.token_)&&inactive()&&g.role_!="submit";
    }catch(const std::exception&){}return false;
}
void CompiledManualProcedureView::selectAction(const ManualProcedureGesture& g){
    if(!current(g)||g.role_!="select")return;const int id=actions_.getSelectedId();if(id<1||static_cast<std::size_t>(id)>actionNames_.size())return;
    if(!cacheFormDraft())return;
    const auto name=actionNames_[static_cast<std::size_t>(id-1)];try{auto* p=owner();if(p->curriculum){const auto available=presentationActions();for(const auto& a:available.array())if(f(a,"action").string()==name)selectedSchema_=labeledCurriculumSchema(f(a,"schema"));}else{const auto available=p->contact->actionDescriptors();const auto it=std::find_if(available.begin(),available.end(),[&](const M::ActionDescriptor& a){return name==actionName(a.action);});if(it==available.end())return;contactForm_.emplace(p->adapter->open(it->action));if(it->action==M::Action::ExtensionReport&&p->restoredFormExtension){contactForm_.emplace(p->adapter->selectExtension(contactForm_->token,*p->restoredFormExtension));p->restoredFormExtension.reset();}selectedSchema_=contactForm_->schema;}
      selectedAction_=name;++generation_;configureSelected();const auto fence=capture("select");juce::Component::SafePointer<CompiledManualProcedureView> safe(this);actions_.onChange=[safe,fence]{if(safe)safe->selectAction(fence);};render();
    }catch(const std::exception&){message_="The selected operation is no longer available.";render();}
}
void CompiledManualProcedureView::configureSelected(){
    // Capture native ownership before configuring. The contact form-generation
    // fence is filled after configure returns; the closure checks the stored
    // capability rather than a report/default constructed by the renderer.
    formFence_.emplace(capture("submit"));juce::Component::SafePointer<CompiledManualProcedureView> safe(this);const auto gen=generation_;
    form_.configure(selectedSchema_,instructions(),[safe,gen]{if(!safe||gen!=safe->generation_||!safe->formFence_)return false;auto token=*safe->formFence_;token.formGeneration_=safe->form_.formGeneration();return safe->current(token);});
    formFence_->formGeneration_=form_.formGeneration();restoreCurrentFormDraft();
    if(family_==ManualProcedureFamily::OrderedContact&&selectedAction_=="extension_report"&&contactForm_){const auto* properties=selectedSchema_.find("properties");const auto* extension=properties?properties->find("extension"):nullptr;if(extension&&!extension->find("const")){const auto chosen=form_.valueAt("input/extension");std::int64_t n{};if(chosen&&chosen->integer(n)&&n>=0&&n<=static_cast<int>(M::Extension::OtherPositionDistance)){contactForm_.emplace(owner()->adapter->selectExtension(contactForm_->token,static_cast<M::Extension>(n)));selectedSchema_=contactForm_->schema;++generation_;configureSelected();return;}}}
    form_.setHistorySummary(summaries());submit_.setEnabled(true);
}
void CompiledManualProcedureView::edited(const std::string& path){
    if(auto* p=owner())++p->draftSerial;
    if(path!="input/extension"||family_!=ManualProcedureFamily::OrderedContact||selectedAction_!="extension_report"||!contactForm_||!formFence_||!current(*formFence_))return;
    const auto value=form_.valueAt(path);std::int64_t n{};if(!value||!value->integer(n)||n<0||n>3)return;
    if(!cacheFormDraft())return;
    try{contactForm_.emplace(owner()->adapter->selectExtension(contactForm_->token,static_cast<M::Extension>(n)));selectedSchema_=contactForm_->schema;++generation_;configureSelected();const auto fence=capture("select");juce::Component::SafePointer<CompiledManualProcedureView> safe(this);actions_.onChange=[safe,fence]{if(safe)safe->selectAction(fence);};render();}catch(const std::exception&){message_="Choose an available source extension explicitly.";render();}
}
void CompiledManualProcedureView::requestCancellation(){auto* p=owner();++p->draftSerial;if(p->curriculum){if(!f(p->curriculum->learnerView(),"needs_manual_release").boolean()){if(hiddenSevenOwner()&&sourceRole_)p->curriculum->applySourceAction(p->curriculum->captureSourceAction("navigate"),O{});else p->curriculum->apply(p->curriculum->capture("navigate"),O{});}}else if(p->contact->view().state!=M::State::Cancelled)p->adapter->cancelForNavigation();}
bool CompiledManualProcedureView::prepareForNavigation(){
    if(draftBusy()||draftPending())return false;if(!cacheFormDraft())return false;
    if(navigationPrepared_)return true;
    try{if(inactive()){fenceInactive();navigationPrepared_=true;pendingNavigation_=false;++generation_;message_.clear();render(true);return true;}
      if(!pendingNavigation_){pendingNavigation_=true;requestCancellation();++generation_;render(true);}message_="Leaving requires explicit manual release. Complete Release, then choose Back or Settings again. Your work and remaining obligations stay retained.";render();return false;
    }catch(const std::exception&){message_="Navigation is blocked until the current manual release is reported.";render();return false;}
}
void CompiledManualProcedureView::resumeAfterNavigation(){navigationPrepared_=pendingNavigation_=false;if(hiddenSevenOwner())sourceRole_=false;++generation_;message_.clear();render(true);}
void CompiledManualProcedureView::navigation(const ManualProcedureGesture& g,bool settings){if(g.role_!="navigation"||!current(g)||!prepareForNavigation())return;const auto cb=settings?onSettings:onBack;juce::Component::SafePointer<CompiledManualProcedureView> safe(this);if(cb){const bool routed=cb();if(safe&&!routed)safe->resumeAfterNavigation();}}
void CompiledManualProcedureView::command(const ManualProcedureGesture& g){
    if(g.role_!="submit")return;
    if(g.action_!=selectedAction_||!current(g)||selectedAction_.empty()){message_="This report belongs to an earlier action or owner. Nothing was submitted. Review the current action and enter its required fields.";render();return;}
    try{const auto input=form_.read();cacheFormDraft();auto* p=owner();const auto submittedDraft=manual_draft::slot(O{{"role",sourceRole_?"source":"learner"},{"action",currentFormDraftKey()},{"watermark",number(ownerDraftWatermark())}});if(p->curriculum){if(hiddenSevenOwner()&&sourceRole_)p->curriculum->applySourceAction(std::get<C::SourceRoleAction>(g.token_),input);else p->curriculum->apply(std::get<C::Token>(g.token_),input);}else p->adapter->apply(std::get<M::FormToken>(g.token_),input);
      p->fieldDrafts.erase(submittedDraft);
      // A pre-existing curriculum physical-step release is not an exit release.
      // Discharge that source step, then preserve the already-requested native
      // cancellation obligation and collect a separate explicit exit release.
      if(pendingNavigation_&&p->curriculum&&!inactive()&&!f(p->curriculum->learnerView(),"needs_manual_release").boolean())requestCancellation();
      ++p->draftSerial;++generation_;message_="Your explicit manual input is retained. It supplies no observed performance or credit.";render(true);
    }catch(const std::exception&){message_="Input refused. Choose or enter every required manual field; release reports must be explicitly positive. The current work remains retained.";render();}
}
std::vector<std::string> CompiledManualProcedureView::instructions()const{
    const auto* p=owner();if(!p)return {"Open a verified manual procedure to begin."};std::vector<std::string> text;
    if(p->curriculum){if(hiddenSevenOwner()&&sourceRole_){const auto& c=p->curriculum->retainedDefinition().retainedOriginalContract();text.push_back("Trusted Source player role: intentional manual caller boundary, not authentication. No source clock, app audio, measured playing or credit.");
        if(C::hidden_seven::motif(key_)){text.push_back(f(c,"source_instruction").string());const auto& script=f(c,"source_script");text.push_back(f(script,"route_label").string());for(const auto* part:{"source_motif","destination_motif"}){text.push_back(human(part)+" — eight ordered source contacts");for(const auto& atom:f(script,part).array())text.push_back("String "+f(atom,"string_name").string()+", fret "+readable(f(atom,"fret"))+", printed note "+f(atom,"printed_note").string()+", degree "+f(atom,"printed_role").string()+". Finger, onset, duration and fixed BPM remain unspecified.");}text.push_back("Keep your declared rhythm, articulation and phrase length through the whole uninterrupted pair. Report source and destination separately in one whole-pair form, then release once. The external listener commits recognition and a key before explicit reveal.");}
        else text.push_back(f(c,"joined_source_instruction").string());
    }else {const auto native=p->curriculum->learnerInstructions();for(const auto& line:f(native,"text").array())text.push_back(line.string());}}
    else{if(contactForm_){text=contactForm_->instructions;if(contactForm_->contact){const auto& c=*contactForm_->contact;const auto finger=c.finger?", finger "+std::to_string(*c.finger):", finger not specified";const auto pick=c.pick.empty()?", pick not specified":", pick "+c.pick;std::string facts;if(c.sourceAtomDescriptor){const auto optionalNumber=[](const char* name,const std::optional<int>& v){return std::string(", ")+name+(v?" "+std::to_string(*v):" not specified");};const auto optionalFlag=[](const char* name,const std::optional<bool>& v){return std::string(", ")+name+(v?(*v?" yes":" no"):" not specified");};facts=", source atom "+c.sourceAtomKind+optionalNumber("physical fret",c.sourcePhysicalFret)+optionalNumber("sounding fret",c.sourceSoundingFret)+optionalNumber("reference fret",c.sourceReferenceFret)+optionalNumber("MIDI pitch",c.sourceMidi)+optionalFlag("audible",c.sourceAudible)+optionalFlag("pick attack",c.sourcePickAttack);}else facts=", fret "+std::to_string(c.fret);text.push_back("Current contact "+std::to_string(c.ordinal)+": string "+c.stringLabel+facts+finger+pick+", route "+c.route+". "+c.timingInstruction+(c.lightlyAccent?" Lightly accent this landing.":""));}}else text={"Choose an operation to read its complete printed guidance and report fields."};
      text.push_back("Reports are your own manual declarations. This procedure supplies no measured playing, source clock, mastery or credit.");}
    return text;
}
std::vector<std::string> CompiledManualProcedureView::summaries()const{
    std::vector<std::string> out{std::to_string(retainedHistoryCount())+" full manual events retained across "+std::to_string(owners_.size())+" tasks. Typed reports stay in their native owners."};const auto* p=owner();if(!p)return out;
    if(p->curriculum){const auto h=hiddenSevenOwner()&&sourceRole_?p->curriculum->sourcePlayerHistory():p->curriculum->history();const auto groups=committedReportGroups();
      if(!groups.array().empty()&&f(groups.array().back(),"reports").array().size()>1&&f(f(groups.array().back(),"reports").array().back(),"original_event_number")==number(h.size())){const auto& reports=f(groups.array().back(),"reports").array();out.push_back("Reports together — each was committed separately; original facts and retry boundaries stay retained.");for(std::size_t i=0;i<reports.size();++i){const auto&e=f(reports[i],"event");out.push_back(readable(f(reports[i],"original_event_number"))+". "+human(f(e,"action").string())+" — my committed report: "+completeReportText(f(e,"reported")));}}
      else {const auto begin=h.size()>8?h.size()-8:0;for(std::size_t i=begin;i<h.size();++i)out.push_back(std::to_string(i+1)+". "+human(f(h[i],"action").string())+" — explicit manual input retained.");}}

    else{const auto& h=p->contact->history();const auto begin=h.size()>8?h.size()-8:0;for(std::size_t i=begin;i<h.size();++i)out.push_back(std::to_string(i+1)+". "+human(actionName(h[i].action))+" — explicit manual input retained.");}return out;
}
void CompiledManualProcedureView::render(bool fresh){
    if(fresh){form_.invalidate();formFence_.reset();contactForm_.reset();selectedSchema_=nullptr;selectedAction_.clear();actions_.clear(juce::dontSendNotification);actionNames_.clear();
      if(!navigationPrepared_){const auto available=presentationActions();for(const auto& a:available.array()){const auto name=f(a,"action").string();if(name=="navigate")continue;actionNames_.push_back(name);const auto* label=a.find("label");actions_.addItem(ju(label?label->string():human(name)),static_cast<int>(actionNames_.size()));}}
      const auto fence=capture("select");juce::Component::SafePointer<CompiledManualProcedureView> safe(this);actions_.onChange=[safe,fence]{if(safe)safe->selectAction(fence);};
      // Selecting the sole current descriptor configures an empty form only.
      // It never submits, fills a learner report, or advances the native owner.
      std::vector<std::size_t> work;for(std::size_t i=0;i<actionNames_.size();++i)if(actionNames_[i]!="cancel"&&actionNames_[i]!="stop")work.push_back(i);
      if(work.size()==1){actions_.setSelectedId(static_cast<int>(work.front()+1),juce::dontSendNotification);selectAction(capture("select"));}
    }
    sourceRoleButton_.setVisible(hiddenSevenOwner());listenerRoleButton_.setVisible(hiddenSevenOwner());sourceRoleButton_.setEnabled(hiddenSevenOwner()&&!navigationPrepared_&&!sourceRole_);listenerRoleButton_.setEnabled(hiddenSevenOwner()&&!navigationPrepared_&&sourceRole_);
    const auto state=learnerView();const auto* extra=state.isObject()?state.find("extra_source_identity"):nullptr;const auto* reference=state.isObject()?state.find("reference_only"):nullptr;
    heading_.setText(ju(hiddenSevenOwner()&&sourceRole_?"Trusted Source player — intentional role":extra&&extra->isBool()&&extra->boolean()?(reference&&reference->isBool()&&reference->boolean()?"Source reference and limitation":"Qualified manual source version"):family_==ManualProcedureFamily::Curriculum?"Manual exercise":family_==ManualProcedureFamily::OrderedContact?"Contact exercise":"Manual procedure"),juce::dontSendNotification);
    phase_.setText(ju("Current phase: "+human(phase())),juce::dontSendNotification);status_.setText(ju(message_),juce::dontSendNotification);
    std::string stateText;if(owner()){const auto v=presentationView();stateText=stateSummary(v);}manual_text::setReadOnlyText(retainedState_,ju(stateText));form_.setInstructions(instructions());const auto groups=committedReportGroups();if(!groups.array().empty()&&f(groups.array().back(),"reports").array().size()>1&&f(f(groups.array().back(),"reports").array().back(),"original_event_number")==number(owner()->curriculum->historyCount()))form_.setCommittedReportSummary(summaries());else form_.setHistorySummary(summaries());
    if(!selectedAction_.empty()){const auto selected=std::find(actionNames_.begin(),actionNames_.end(),selectedAction_);if(selected!=actionNames_.end())actions_.setSelectedId(static_cast<int>(selected-actionNames_.begin()+1),juce::dontSendNotification);}
    const bool sole=actionNames_.size()==1;actions_.setVisible(!sole);actionLabel_.setText(!selectedAction_.empty()?"Current action: "+actions_.getText()+(sole?"":". Other current actions remain available below."):"Choose your next action",juce::dontSendNotification);
    const auto button=selectedAction_.find("reveal")!=std::string::npos?"Reveal reference":selectedAction_=="begin"?"Begin current task":selectedAction_=="release"?"Report release":selectedAction_=="finish"?"Finish manual task":"Submit current report";submit_.setButtonText(selectedAction_.empty()?"Submit my report":button);submit_.setTitle(selectedAction_.empty()?"Select a current manual action first":"Submit current manual action: "+ju(human(selectedAction_)));
    actions_.setEnabled(owner()&&!navigationPrepared_&&!actionNames_.empty());submit_.setEnabled(owner()&&!navigationPrepared_&&!selectedAction_.empty());back_.setEnabled(!navigationPrepared_);settings_.setEnabled(!navigationPrepared_);draftControls();resized();
}
void CompiledManualProcedureView::resized(){auto r=getLocalBounds().reduced(12);if(hiddenSevenOwner()){auto roles=r.removeFromTop(34);sourceRoleButton_.setBounds(roles.removeFromLeft(290).reduced(2));listenerRoleButton_.setBounds(roles.removeFromLeft(250).reduced(2));}auto storageRow=r.removeFromTop(32);saveDraft_.setBounds(storageRow.removeFromLeft(150).reduced(2));listDrafts_.setBounds(storageRow.removeFromLeft(145).reduced(2));moreDrafts_.setBounds(storageRow.removeFromLeft(100).reduced(2));checkDraft_.setBounds(storageRow.removeFromLeft(155).reduced(2));auto savedRow=r.removeFromTop(32);reopenDraft_.setBounds(savedRow.removeFromRight(185).reduced(2));savedDrafts_.setBounds(savedRow.reduced(2));copyHistory_.setBounds(r.removeFromTop(30).removeFromLeft(230).reduced(2));heading_.setBounds(r.removeFromTop(28));phase_.setBounds(r.removeFromTop(24));auto nav=r.removeFromTop(34);back_.setBounds(nav.removeFromLeft(150).reduced(2));settings_.setBounds(nav.removeFromLeft(110).reduced(2));submit_.setBounds(nav.removeFromRight(230).reduced(2));status_.setBounds(r.removeFromBottom(manual_text::labelHeight(status_,r.getWidth(),54)));actionLabel_.setBounds(r.removeFromTop(manual_text::labelHeight(actionLabel_,r.getWidth(),24)));actions_.setBounds(r.removeFromTop(30));r.removeFromTop(8);retainedState_.setBounds(r.removeFromBottom(std::min(116,r.getHeight()/3)));r.removeFromBottom(6);form_.setBounds(r);}
void CompiledManualProcedureView::paint(juce::Graphics& g){g.fillAll(juce::Colour(0xfff3f6f7));}
bool CompiledManualProcedureView::draftBusy()const noexcept{return drafts_&&drafts_->job.has_value();}
bool CompiledManualProcedureView::draftPending()const noexcept{return drafts_&&(bool(drafts_->pending)||drafts_->workerUncertain);}
bool CompiledManualProcedureView::attachDraftStore(storage::ProfileStore& store,const std::string& profile){
    if(drafts_->workerUncertain||draftBusy()||profile.empty()||(!drafts_->profile.empty()&&drafts_->profile!=profile))return false;
    drafts_->store=&store;drafts_->profile=profile;draftControls();return true;
}
bool CompiledManualProcedureView::prepareDraftStoreReopen(){return !draftBusy()&&(draftPending()?inactive():prepareForNavigation());}
bool CompiledManualProcedureView::detachDraftStore(){if(draftBusy())return false;drafts_->store=nullptr;draftControls();return true;}
std::size_t CompiledManualProcedureView::ownerDraftWatermark()const{const auto* p=owner();return !p?0:p->curriculum?p->curriculum->continuationWatermark():p->adapter->continuationWatermark();}
std::string CompiledManualProcedureView::currentFormDraftKey()const{const auto* p=owner();return p&&p->contact?manual_draft::contactFormKey(selectedAction_,selectedSchema_):selectedAction_;}
bool CompiledManualProcedureView::cacheFormDraft(){
    auto* p=owner();if(!p||(!p->curriculum&&!p->contact)||selectedAction_.empty()||!form_.current())return true;
    try{V record=O{{"role",sourceRole_?"source":"learner"},{"action",currentFormDraftKey()},{"watermark",number(ownerDraftWatermark())},{"form",form_.captureDraft()}};const auto slot=manual_draft::slot(record);const auto it=p->fieldDrafts.find(slot);if(it==p->fieldDrafts.end()||it->second!=record){p->fieldDrafts[slot]=std::move(record);++p->draftSerial;}return true;}
    catch(const std::exception&){message_="These unsubmitted fields could not be captured. Keep this task open; no saved-draft claim was made.";return false;}
}
void CompiledManualProcedureView::restoreCurrentFormDraft(){
    auto* p=owner();if(!p||(!p->curriculum&&!p->contact)||selectedAction_.empty())return;
    const V id=O{{"role",sourceRole_?"source":"learner"},{"action",currentFormDraftKey()},{"watermark",number(ownerDraftWatermark())}};
    const auto it=p->fieldDrafts.find(manual_draft::slot(id));if(it!=p->fieldDrafts.end()&&!form_.restoreDraft(f(it->second,"form")))message_="Saved unsubmitted fields are retained but do not match the current form. Nothing was submitted or replaced.";
    if(formFence_)formFence_->formGeneration_=form_.formGeneration();
}
void CompiledManualProcedureView::draftControls(){
    if(!drafts_)return;checkDraft_.setButtonText(drafts_->pendingCode=="STORE_UNCERTAIN"?"Reopen original profile":"Check original save");const bool bound=drafts_->store&&!drafts_->profile.empty();const bool supported=owner()&&(owner()->curriculum||owner()->contact);const bool busy=draftBusy(),pending=draftPending();
    saveDraft_.setButtonText(pending&&(drafts_->pendingStatus==storage::Status::Conflict||drafts_->pendingStatus==storage::Status::Unsupported)?"Save as new draft":"Save manual draft");
    if(pending&&drafts_->pendingStatus==storage::Status::DefinitelyAbsent)saveDraft_.setButtonText("Retry original save");
    saveDraft_.setEnabled(bound&&supported&&!busy&&(!pending||drafts_->pendingStatus==storage::Status::Conflict||drafts_->pendingStatus==storage::Status::Unsupported||drafts_->pendingStatus==storage::Status::DefinitelyAbsent));
    listDrafts_.setEnabled(bound&&supported&&!busy&&!pending);moreDrafts_.setEnabled(bound&&supported&&!busy&&!pending&&drafts_->more);savedDrafts_.setEnabled(bound&&supported&&!busy&&!pending);reopenDraft_.setEnabled(bound&&supported&&!busy&&!pending);checkDraft_.setEnabled(bound&&!busy&&pending);
    copyHistory_.setEnabled(supported&&!busy&&!sourceRole_);
    if(busy){actions_.setEnabled(false);submit_.setEnabled(false);back_.setEnabled(false);settings_.setEnabled(false);sourceRoleButton_.setEnabled(false);listenerRoleButton_.setEnabled(false);}form_.setEnabled(!busy&&!navigationPrepared_&&!selectedAction_.empty());
}
bool CompiledManualProcedureView::startDraftSave(const OwnerKey& key,bool gate){
    namespace D=storage::manual_drafts;
    if(!drafts_->store||draftBusy()||drafts_->workerUncertain||!gate)return false;auto it=owners_.find(key);if(it==owners_.end()||(!it->second.curriculum&&!it->second.contact))return false;auto& p=it->second;
    if(draftPending()&&drafts_->pendingStatus==storage::Status::DefinitelyAbsent){
        auto* store=drafts_->store;const auto pending=drafts_->pending;const auto source=drafts_->pendingKey,id=drafts_->pendingId;const auto serial=drafts_->pendingSerial;const auto revision=drafts_->pendingRevision;const auto family=drafts_->pendingFamily;
        drafts_->job.emplace(std::async(std::launch::async,[store,pending,source,id,serial,revision,family]{Drafts::Work w;w.family=family;w.kind="save";w.key=source;w.id=id;w.serial=serial;w.revision=revision;w.publication=pending;try{w.receipt=D::Repository::publish(*store,*pending,true);}catch(const std::exception& e){w.receipt={storage::Status::Unresolved,"",id,"DRAFT_RETRY_UNRESOLVED",e.what(),nullptr};}return w;}));message_="Retrying the original captured draft, without replacing its identity or bytes.";render();return true;
    }
    if(draftPending()){
        if(drafts_->pendingStatus!=storage::Status::Conflict&&drafts_->pendingStatus!=storage::Status::Unsupported)return false;
        // Explicit Save-as-new leaves the conflicting original untouched.
        drafts_->retired.push_back(drafts_->pending);drafts_->pending.reset();p.draftId.clear();p.draftRevision=0;
    }
    if(p.draftId.empty())p.draftId=storage::newUuid();A records;for(const auto& item:p.fieldDrafts)records.push_back(item.second);
    auto* store=drafts_->store;auto* graph=p.curriculum.get();auto* contact=p.contact.get();auto* adapter=p.adapter.get();const auto family=key.first;const auto profile=drafts_->profile,id=p.draftId,source=key.second;const auto expected=p.draftRevision;const auto serial=p.draftSerial;
    const std::string selected=key==OwnerKey{family_,key_}&&!sourceRole_?selectedAction_:"";
    drafts_->job.emplace(std::async(std::launch::async,[store,graph,contact,adapter,family,profile,id,source,expected,serial,records=V(std::move(records)),selected]()mutable{
        Drafts::Work w;w.kind="save";w.family=family;w.key=source;w.id=id;w.serial=serial;w.revision=expected+1;
        try{std::string payload,contract;std::size_t watermark{};if(graph){const auto frozen=graph->captureContinuation();payload=manual_draft::encode(frozen,records,selected);contract=graph->retainedDefinition().contractSha256();watermark=frozen.watermark();}else{const auto chosen=selected.empty()?std::optional<M::Action>{}:adapter->openAction();payload=manual_draft::encodeContact(*adapter,records,chosen);contract=contact->continuationSourceSha256();watermark=adapter->continuationWatermark();}w.publication=std::make_shared<D::Publication>(D::Repository::prepare(profile,id,source,contract,payload,watermark,expected));w.receipt=D::Repository::publish(*store,*w.publication,true);}
        catch(const std::exception& e){w.receipt={w.publication?storage::Status::Unresolved:storage::Status::DefiniteFailure,"",id,"DRAFT_SAVE_REFUSED",e.what(),nullptr};}return w;
    }));message_="Saving this manual task and its unsubmitted fields. No report is submitted and no activity starts.";render();return true;
}
bool CompiledManualProcedureView::saveCurrentDraft(){
    if(draftBusy())return false;if(!cacheFormDraft()){render();return false;}bool gate=false;try{gate=onDraftSaveGate&&onDraftSaveGate();}catch(...){}
    if(!gate){message_="Stop and resolve app audio/output before saving a manual draft. The current task stays open.";render();return false;}
    if(!startDraftSave({family_,key_},gate)){message_="Manual draft saving is unavailable here. Open a local profile and resolve any original save first. The current task and unsubmitted fields remain retained.";render();return false;}return true;
}
void CompiledManualProcedureView::cancelDraftClose(){if(draftBusy()){drafts_->resumeAfterJob=true;return;}if(navigationPrepared_)resumeAfterNavigation();}
bool CompiledManualProcedureView::saveDraftsForClose(bool gate){
    if(draftBusy()||draftPending())return false;if(!drafts_->store)return true;if(!cacheFormDraft())return false;
    for(const auto& entry:owners_)if((entry.second.curriculum||entry.second.contact)&&entry.second.draftSerial!=entry.second.savedDraftSerial){startDraftSave(entry.first,gate);return false;}return true;
}
bool CompiledManualProcedureView::refreshSavedDrafts(bool next){
    namespace D=storage::manual_drafts;if(!drafts_->store||draftBusy()||draftPending()||!owner()||(!owner()->curriculum&&!owner()->contact))return false;
    auto* store=drafts_->store;const auto family=family_;const auto profile=drafts_->profile,source=key_,after=next?drafts_->cursor:"";
    drafts_->job.emplace(std::async(std::launch::async,[store,profile,source,after,family]{Drafts::Work w;w.family=family;w.kind="list";w.key=source;A rows;
        try{w.receipt=D::Repository::list(*store,profile,after,64);if(w.receipt.status==storage::Status::Confirmed){w.more=f(w.receipt.data,"has_more").boolean();for(const auto& key:f(w.receipt.data,"keys").array()){
            const auto id=key.string().substr(D::draftPrefix.size());w.cursor=id;auto r=store->readPreferences(storage::newUuid(),key.string()).get();if(r.status!=storage::Status::Confirmed){w.receipt=r;return w;}
            if(!f(r.data,"applicable").boolean()){rows.emplace_back(O{{"id",id},{"label","Unavailable saved draft "+id.substr(0,8)}});continue;}
            const auto m=storage::parseCanonical(f(r.data,"bytes").string());if(f(m,"source_key")==V(source))rows.emplace_back(O{{"id",id},{"label","Manual draft "+id.substr(0,8)+" · revision "+std::to_string(D::integer(f(r.data,"revision")))}});
        }}w.rows=std::move(rows);}catch(const std::exception& e){w.receipt={storage::Status::DefiniteFailure,"","","DRAFT_LIST_REFUSED",e.what(),nullptr};}return w;
    }));message_="Reading saved draft names for this task; original drafts are unchanged.";render();return true;
}
bool CompiledManualProcedureView::reopenSelectedDraft(){
    namespace D=storage::manual_drafts;auto* p=owner();if(!drafts_->store||draftBusy()||draftPending()||!p||(!p->curriculum&&!p->contact)||!inactive())return false;if(!cacheFormDraft())return false;
    if(p->draftSerial!=p->savedDraftSerial&&!(p->draftRevision==0&&(p->curriculum?p->curriculum->historyCount():p->contact->history().size())==0&&p->draftSerial<=2)){message_="Save the current manual draft before reopening another. Unsaved work remains open.";render();return false;}
    const auto id=savedDrafts_.getText().toStdString();const auto selected=savedDrafts_.getSelectedId();if(selected<1||id.empty())return false;
    // IDs are retained as item properties, not parsed from the readable label.
    const auto draft=savedDrafts_.getProperties()[juce::Identifier("draft-"+juce::String(selected))].toString().toStdString();if(draft.empty())return false;
    auto* store=drafts_->store;const auto family=family_;const auto originalSerial=p->draftSerial;const auto profile=drafts_->profile,source=key_;std::optional<C::Definition> definition;if(p->curriculum)definition.emplace(p->curriculum->retainedDefinition());std::optional<tasks::manual_contacts::SourceHandle> contactSource;if(p->contact)contactSource.emplace(p->contact->sourceHandle());
    drafts_->job.emplace(std::async(std::launch::async,[store,profile,source,draft,definition,contactSource,family,originalSerial]{Drafts::Work w;w.serial=originalSerial;w.family=family;w.kind="open";w.key=source;w.id=draft;
        try{const auto loaded=D::Repository::load(*store,profile,draft);w.receipt=loaded.receipt;if(w.receipt.status==storage::Status::Confirmed){if(definition)w.restored.emplace(manual_draft::decode(*definition,loaded));else w.restoredContact.emplace(manual_draft::decodeContact(*contactSource,loaded));w.revision=loaded.revision;}}
        catch(const std::exception& e){w.receipt={storage::Status::Unsupported,"",draft,"DRAFT_PRESERVED_UNAVAILABLE",e.what(),nullptr};}return w;
    }));message_="Checking the saved source binding, original reports and remaining duties before reopening.";render();return true;
}
bool CompiledManualProcedureView::reconcileDraft(){
    namespace D=storage::manual_drafts;if(!drafts_->store||draftBusy()||!drafts_->pending||drafts_->workerUncertain)return false;
    if(drafts_->pendingCode=="STORE_UNCERTAIN"){
        if(!onDraftStoreReopen||!onDraftStoreReopen()){message_="Keep the original save retained. Complete manual release, then reopen the original profile before checking it again.";render();return false;}
        drafts_->pendingCode.clear();message_="Original profile reopened. Check the original save; no replacement was started.";render();return true;
    }
    auto* store=drafts_->store;const auto pending=drafts_->pending;const auto key=drafts_->pendingKey,id=drafts_->pendingId;const auto serial=drafts_->pendingSerial;const auto revision=drafts_->pendingRevision;const auto family=drafts_->pendingFamily;
    drafts_->job.emplace(std::async(std::launch::async,[store,pending,key,id,serial,revision,family]{Drafts::Work w;w.family=family;w.kind="check";w.key=key;w.id=id;w.serial=serial;w.revision=revision;w.publication=pending;try{w.receipt=D::Repository::reconcile(*store,*pending);}catch(const std::exception& e){w.receipt={storage::Status::Unresolved,"",id,"DRAFT_CHECK_UNRESOLVED",e.what(),nullptr};}return w;}));message_="Checking the original save identity; no replacement save is started.";render();return true;
}
void CompiledManualProcedureView::serviceDrafts(){
    if(!draftBusy()||drafts_->job->wait_for(std::chrono::seconds(0))!=std::future_status::ready)return;
    Drafts::Work w;try{w=drafts_->job->get();}catch(const std::exception& e){drafts_->job.reset();drafts_->workerUncertain=true;message_="The original manual draft worker failed unexpectedly. Keep open; execution outcome is uncertain. "+std::string(e.what());render();return;}drafts_->job.reset();auto it=owners_.find({w.family,w.key});
    if(it!=owners_.end()&&w.family==family_&&w.key==key_&&(w.kind=="save"||w.kind=="check"||w.kind=="open")){if(!cacheFormDraft())++it->second.draftSerial;}
    if(w.kind=="open"&&it!=owners_.end()&&it->second.draftSerial!=w.serial){message_="The current fields changed while the saved draft was being checked. Current work and the original saved draft are both retained; nothing was reopened.";render();return;}
    if(w.kind=="save"||w.kind=="check"){
        if(w.receipt.status==storage::Status::Confirmed&&it!=owners_.end()){
            it->second.draftId=w.id;it->second.draftRevision=w.revision;it->second.savedDraftSerial=w.serial;drafts_->pending.reset();message_=it->second.draftSerial==w.serial?"Manual draft saved, including unsubmitted fields. It supplies no observed performance or credit.":"Earlier manual draft saved. Newer changes remain unsaved.";
        }else if(w.kind=="check"&&w.receipt.status==storage::Status::DefinitelyAbsent){
            // The manifest is proven absent at the original expected revision.
            // Keep its original operation/captured bytes for explicit retry.
            drafts_->pending=w.publication;drafts_->pendingStatus=storage::Status::DefinitelyAbsent;message_="The original draft was not published. Choose Retry original save; the captured bytes and identity remain retained.";
        }else{drafts_->pending=w.publication;drafts_->pendingFamily=w.family;drafts_->pendingKey=w.key;drafts_->pendingId=w.id;drafts_->pendingSerial=w.serial;drafts_->pendingRevision=w.revision;drafts_->pendingStatus=w.receipt.status;drafts_->pendingCode=w.receipt.code;message_="Manual draft save is not confirmed. "+w.receipt.message+" Check the original save before closing or replacing it.";}
    }else if(w.kind=="list"){
        if(w.receipt.status==storage::Status::Confirmed){savedDrafts_.clear(juce::dontSendNotification);int n=0;for(const auto& row:w.rows.array()){++n;savedDrafts_.addItem(ju(f(row,"label").string()),n);savedDrafts_.getProperties().set(juce::Identifier("draft-"+juce::String(n)),ju(f(row,"id").string()));}drafts_->cursor=w.cursor;drafts_->more=w.more;message_=n?"Select a saved draft for this task. Unavailable originals remain preserved.":w.more?"No matching draft on this page. Choose More drafts.":"No matching saved draft on this page.";}
        else message_="Saved draft names could not be read. Originals remain unchanged. "+w.receipt.message;
    }else if(w.kind=="open"){
        bool installed=false;
        if(w.receipt.status==storage::Status::Confirmed&&w.restored&&it!=owners_.end())try{
            // Validate the currently applicable unsubmitted learner form on a
            // separate component before replacing any retained owner.
            auto& restored=*w.restored;const auto mark=restored.owner->continuationWatermark();
            for(const auto& record:restored.forms.array())if(f(record,"role")==V("learner")&&f(record,"action")==V(restored.action)&&storage::manual_drafts::integer(f(record,"watermark"))==static_cast<std::int64_t>(mark)){
                const auto available=restored.owner->learnerActions();for(const auto& action:available.array())if(f(action,"action")==V(restored.action)){TypedManualForm probe;probe.configure(labeledCurriculumSchema(f(action,"schema")),{},[]{return true;});if(!probe.restoreDraft(f(record,"form")))throw std::runtime_error("Saved fields do not match the current action schema");}
            }
            std::map<std::string,V> fields;for(const auto& record:restored.forms.array())fields.emplace(manual_draft::slot(record),record);std::string savedId=w.id;auto& p=it->second;p.curriculum=std::move(restored.owner);installed=true;p.fieldDrafts.swap(fields);p.draftId.swap(savedId);p.draftRevision=w.revision;++p.draftSerial;p.savedDraftSerial=p.draftSerial;sourceRole_=false;++generation_;navigationPrepared_=pendingNavigation_=false;message_="Saved manual draft reopened. Reports and remaining duties are unchanged; no report was submitted and Source role was not granted.";render(true);
            if(!restored.action.empty()){const auto a=std::find(actionNames_.begin(),actionNames_.end(),restored.action);if(a!=actionNames_.end()){actions_.setSelectedId(static_cast<int>(a-actionNames_.begin()+1),juce::dontSendNotification);selectAction(capture("select"));}}p.savedDraftSerial=p.draftSerial;
        }catch(const std::exception& e){message_=(installed?"The saved task loaded, but its form could not be presented. Original saved bytes remain intact. ":"Saved draft remains unavailable; current work was retained. ")+std::string(e.what());}
        else if(w.receipt.status==storage::Status::Confirmed&&w.restoredContact&&it!=owners_.end())try{
            auto& restored=*w.restoredContact;const auto mark=restored.owner.adapter->continuationWatermark();const auto extension=restored.owner.adapter->selectedExtension();
            std::string desired;if(restored.action){desired=actionName(*restored.action);auto opened=restored.owner.adapter->open(*restored.action);if(extension)opened=restored.owner.adapter->selectExtension(opened.token,*extension);const auto recordKey=manual_draft::contactFormKey(desired,opened.schema);
                for(const auto& record:restored.forms.array())if(f(record,"role")==V("learner")&&f(record,"action")==V(recordKey)&&storage::manual_drafts::integer(f(record,"watermark"))==static_cast<std::int64_t>(mark)){TypedManualForm probe;probe.configure(opened.schema,{},[]{return true;});if(!probe.restoreDraft(f(record,"form")))throw std::runtime_error("Saved contact fields differ from the current source form");}
            }
            std::map<std::string,V> fields;for(const auto& record:restored.forms.array())fields.emplace(manual_draft::slot(record),record);std::string savedId=w.id;auto& p=it->second;p.adapter.reset();p.contact=std::move(restored.owner.task);p.adapter=std::move(restored.owner.adapter);installed=true;p.fieldDrafts.swap(fields);p.restoredFormExtension=extension;p.draftId.swap(savedId);p.draftRevision=w.revision;++p.draftSerial;p.savedDraftSerial=p.draftSerial;sourceRole_=false;++generation_;navigationPrepared_=pendingNavigation_=false;message_="Saved contact draft reopened. Original reports, remaining source duties and unsubmitted fields are retained; no report or physical completion was inferred.";render(true);
            if(!desired.empty()&&selectedAction_!=desired){const auto action=std::find(actionNames_.begin(),actionNames_.end(),desired);if(action==actionNames_.end())throw std::runtime_error("Saved contact action is no longer available");p.restoredFormExtension=extension;actions_.setSelectedId(static_cast<int>(action-actionNames_.begin()+1),juce::dontSendNotification);selectAction(capture("select"));}p.savedDraftSerial=p.draftSerial;
        }catch(const std::exception& e){message_=(installed?"The saved contact task loaded, but its form could not be presented. Original saved bytes remain intact. ":"Saved contact draft remains unavailable; current work was retained. ")+std::string(e.what());}
        else message_="Saved draft was not reopened. Original and current work remain retained. "+w.receipt.message;
    }
    if(drafts_->resumeAfterJob){drafts_->resumeAfterJob=false;if(navigationPrepared_)resumeAfterNavigation();}
    render();
}

std::string CompiledManualProcedureView::learnerHistoryExport(){
    const auto* p=owner();if(draftBusy()||!p||(!p->curriculum&&!p->contact)||sourceRole_)throw std::runtime_error("Full learner history is unavailable in this role or during a draft operation");
    if(!cacheFormDraft())throw std::runtime_error("Current unsubmitted fields could not be captured");
    A history;if(p->curriculum){for(const auto& event:p->curriculum->history())history.push_back(event);}else history=M::contact_snapshot::encode(p->contact->history()).array();A fields,earlierFields;
    for(const auto& item:p->fieldDrafts)if(f(item.second,"role")==V("learner")){if(f(item.second,"watermark")==number(ownerDraftWatermark()))fields.push_back(item.second);else earlierFields.push_back(item.second);}
    // Use only the native learner projection. Private continuation bytes,
    // Source-player history and trusted source context are never exported.
    const auto sourceKey=p->curriculum?p->curriculum->retainedDefinition().sourceKey():std::string(p->contact->sourceKey());const auto identity=p->curriculum?p->curriculum->retainedDefinition().sourceIdentity():std::string(p->contact->sourceHandle().sourceIdentity());const auto contract=p->curriculum?p->curriculum->retainedDefinition().contractSha256():p->contact->continuationSourceSha256();
    return storage::canonical(O{{"format","fathom-learner-manual-history-v1"},{"source_key",sourceKey},{"source_identity",identity},{"contract_sha256",contract},{"current_state",learnerView()},{"history",std::move(history)},{"unsubmitted_learner_fields",std::move(fields)},{"retained_earlier_field_drafts",std::move(earlierFields)},{"observed_performance",false},{"grants_credit",false},{"notice","Manual declarations and field drafts only; history alone records submissions. Earlier drafts are references, not current reports, measured playing, mastery or user acceptance."}});
}
bool CompiledManualProcedureView::copyLearnerHistory(){
    if(!cacheFormDraft())return false;try{const auto bytes=learnerHistoryExport();if(onCopyLearnerHistory)onCopyLearnerHistory(bytes);else{juce::SystemClipboard::copyTextToClipboard(ju(bytes));if(juce::SystemClipboard::getTextFromClipboard().toStdString()!=bytes)throw std::runtime_error("Clipboard readback did not match");}message_="Full learner history copied, with original report order and remaining duties. Unsubmitted fields are labeled separately; no private Source-player records were copied.";render();return true;}catch(const std::exception&){message_="Learner history was not copied. Return to learner role and finish any draft operation first. Current work is unchanged.";render();return false;}
}
} // namespace fathom::desktop
