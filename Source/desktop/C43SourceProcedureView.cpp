#include "C43SourceProcedureView.hpp"
#include "desktop/ManualWorkspaceDraft.hpp"
#include <algorithm>
#include <cctype>

namespace fathom::desktop {
namespace {
using J=json::Value;using O=J::Object;namespace C=tasks::c43;
const J& f(const J& v,const std::string& k){auto p=v.find(k);if(!p)throw std::runtime_error("Missing retained presentation field");return *p;}
bool yes(const J& v,const char* k){auto p=v.find(k);return p&&*p==J(true);}
juce::String ju(const std::string& s){return juce::String::fromUTF8(s.c_str());}
std::string label(std::string s){std::replace(s.begin(),s.end(),'_',' ');if(!s.empty())s[0]=static_cast<char>(std::toupper(static_cast<unsigned char>(s[0])));return s;}
bool custody(const std::string& k){return k=="key"||k=="source_key"||k=="exact_keys"||k=="source_identity"||k=="revision"||k=="generation"||k=="jsonl_line"||k=="bytes"||k.find("sha")!=std::string::npos||k.find("binding")!=std::string::npos||k.find("_ref")!=std::string::npos||k.find("path")!=std::string::npos||k.find("provenance")!=std::string::npos||k.find("canonical")!=std::string::npos||k.find("contract")!=std::string::npos;}
std::string readable(const J& v,int depth=0){
 if(depth>12)return "Retained source detail";if(v.null())return "Unknown / not reported";
 if(v.isBool())return v.boolean()?"Yes (manually declared)":"No (manually declared)";
 if(v.isNumber())return std::get<json::Number>(v.data).token;
 if(v.isString()){const auto& s=v.string();for(auto bad:{"exercise-completeness-r01/","proposed-printed-","Build/","Prompts/","Content/","Results/","sha256"})if(s.find(bad)!=std::string::npos)return "Retained printed reference";return s;}
 std::string out;if(v.isArray()){for(const auto& x:v.array()){if(!out.empty())out+="; ";out+=readable(x,depth+1);}}
 else if(v.isObject()){for(const auto& x:v.object())if(!custody(x.first)){if(!out.empty())out+='\n';out+=label(x.first)+": "+readable(x.second,depth+1);}}return out;
}
bool debt(const J& v){return yes(v,"manual_release_debt")||yes(v,"external_source_stop_debt");}
bool inactive(const J& v){return f(v,"state")==J("completed")||f(v,"state")==J("cancelled");}
J editableSchema(const J& schema){
 auto out=schema;
 if(auto p=schema.find("properties")){
  for(const auto& x:p->object())out.object()["properties"].object()[x.first]=editableSchema(x.second);
  if(out.object()["properties"].object().erase("source_key")){auto& r=out.object()["required"].array();r.erase(std::remove(r.begin(),r.end(),J("source_key")),r.end());}
  int item=0;for(auto& x:out.object()["properties"].object()){
   if(x.first.find("exercise-completeness-r01/")==0)x.second.object()["label"]="Required printed source item "+std::to_string(++item);
   if(auto e=x.second.find("enum");e&&e->array()==J::Array{"yes","no","uncertain"})x.second.object()["enumLabels"]=J::Array{"Yes — manually reported","No — not satisfied","Unknown / uncertain"};
  }
 }
 if(auto x=schema.find("items"))out.object()["items"]=editableSchema(*x);return out;
}
J setupSchema(const J& av){J::Array modes{"human_source_player","compatible_learner_supplied_recording"};if(!av.null()&&f(av,"provider_kind")==J("actual_learner_evidence_ledger"))modes.emplace_back("actual_learner_evidence_ledger");return O{{"type","object"},{"properties",O{
 {"provider_kind",O{{"type","string"},{"enum",modes}}},{"reference",O{{"type","string"},{"minLength",J::fromInteger(1)}}},
 {"external_provider_role_confirmed",O{{"type",J::Array{"boolean","null"}}}}, {"actual_source_material_ready",O{{"type",J::Array{"boolean","null"}}}}}},
 {"required",J::Array{"provider_kind","reference","external_provider_role_confirmed","actual_source_material_ready"}},{"additionalProperties",false}};}
}
void C43ProcedureButton::bind(Capture c,Deliver d){capture_=std::move(c);deliver_=std::move(d);pending_.reset();onClick=[this]{if(!capture_||!deliver_)return;auto g=pending_?*pending_:capture_();pending_.reset();deliver_(g);};}
C43ProcedureGesture C43ProcedureButton::capture()const{return capture_();}
void C43ProcedureButton::deliver(const C43ProcedureGesture& g){if(deliver_)deliver_(g);}
void C43ProcedureButton::mouseDown(const juce::MouseEvent& e){if(capture_)pending_.emplace(capture_());juce::TextButton::mouseDown(e);}
bool C43ProcedureButton::keyPressed(const juce::KeyPress& k){if(k==juce::KeyPress::returnKey||k==juce::KeyPress::spaceKey){if(capture_)pending_.emplace(capture_());triggerClick();return true;}return juce::TextButton::keyPressed(k);}
C43SourceProcedureView::C43SourceProcedureView(){
 worksheet_.setComponentID("c43-copy-worksheet");worksheet_.onClick=[this]{copyLearnerHistory();};addAndMakeVisible(worksheet_);
 addAndMakeVisible(draftPanel_);
 draftPanel_.hooks.key=[this]{return key_;};draftPanel_.hooks.stamp=[this]{return workspaceStamp();};draftPanel_.hooks.freeze=[this](bool busy){setDraftBusy(busy);};draftPanel_.hooks.gate=[this]{return onDraftSaveGate&&onDraftSaveGate();};draftPanel_.hooks.prepareNavigation=[this]{return prepareForNavigation();};draftPanel_.hooks.reopenStore=[this]{return onDraftStoreReopen&&onDraftStoreReopen();};
 draftPanel_.hooks.capture=[this]{if(!entry())throw std::runtime_error("No current C43 source");SourceDraftPanel::Capture c;c.key=key_;c.contract=content::sha256(json::stringify(entry()->owner->retainedDefinition().binding()));c.stamp=workspaceStamp();std::int64_t revision=0;f(learnerView(),"revision").integer(revision);c.watermark=revision;c.bytes=captureWorkspace();return c;};
 draftPanel_.hooks.decoder=[this]()->std::function<std::shared_ptr<void>(const SourceDraftPanel::Loaded&)>{if(!package_||!contextPackage_)return {};const auto package=*package_;const auto context=*contextPackage_;return [package,context](const auto&loaded){return std::make_shared<Workspace>(decodeWorkspace(package,context,loaded));};};
 draftPanel_.hooks.install=[this](std::shared_ptr<void>prepared,const std::string&expected){if(!package_||!contextPackage_||workspaceStamp()!=expected)return false;return installWorkspaceImpl(*package_,*contextPackage_,std::move(*std::static_pointer_cast<Workspace>(prepared)),true);};

 heading_.setText("Listening exercise",juce::dontSendNotification);actionLabel_.setText("Choose a manual action",juce::dontSendNotification);contextLabel_.setText(ju("Required listening context"),juce::dontSendNotification);
 for(auto* p:std::vector<juce::Component*>{&heading_,&phase_,&actionLabel_,&contextLabel_,&status_,&presentation_,&actionMenu_,&form_,&submit_,&provider_,&learner_,&back_,&settings_,&refreshContext_})addAndMakeVisible(p);
 manual_text::configureReadOnly(status_,"c43-status","Required actions and listening status");
 manual_text::configureReadOnly(presentation_,"c43-presentation","Current permitted listening information");
 contextViewport_.setComponentID("c43-context-viewport");contextViewport_.setTitle("Required listening context; scroll to reach all instructions and controls");contextViewport_.setScrollBarsShown(true,false);addChildComponent(contextViewport_);
 actionMenu_.setComponentID("c43-actions");submit_.setComponentID("c43-submit");provider_.setComponentID("c43-provider");learner_.setComponentID("c43-learner");back_.setComponentID("c43-back");settings_.setComponentID("c43-settings");refreshContext_.setComponentID("c43-context-refresh");status_.setComponentID("c43-status");presentation_.setComponentID("c43-presentation");
 submit_.setButtonText("Submit manual report");provider_.setButtonText("External source setup");learner_.setButtonText("Return to learner");back_.setButtonText("Back");settings_.setButtonText("Audio / settings");refreshContext_.setButtonText("Refresh context attachment");render();
}
C43SourceProcedureView::~C43SourceProcedureView(){form_.invalidate();}
C43SourceProcedureView::Entry* C43SourceProcedureView::entry(){auto p=entries_.find(key_);return p==entries_.end()?nullptr:p->second.get();}
const C43SourceProcedureView::Entry* C43SourceProcedureView::entry()const{auto p=entries_.find(key_);return p==entries_.end()?nullptr:p->second.get();}
const C::Owner* C43SourceProcedureView::retainedOwner(const std::string& k)const{auto p=entries_.find(k);return p==entries_.end()?nullptr:p->second->owner.get();}
EarSourceProcedureView* C43SourceProcedureView::contextView(const std::string& k)const{auto p=entries_.find(k);return p==entries_.end()?nullptr:p->second->context.get();}
J C43SourceProcedureView::learnerView()const{return entry()?entry()->owner->learnerView():J();}
J C43SourceProcedureView::learnerActions()const{return entry()?entry()->owner->learnerActions():J(O{});}
std::size_t C43SourceProcedureView::retainedHistoryCount()const{std::size_t n=0;for(const auto& p:entries_)n+=p.second->owner->history().size();return n;}
bool C43SourceProcedureView::providerSheetVisible()const noexcept{return mode_!=Mode::Learner;}
void C43SourceProcedureView::invalidateContextControls(){for(auto& p:entries_)if(p.second->context)p.second->context->resumeAfterNavigation();}
void C43SourceProcedureView::resetProvider(){cacheFields();providerDraftId_.clear();providerAuthorized_=false;++roleEpoch_;mode_=Mode::Learner;invalidateContextControls();}
bool C43SourceProcedureView::open(const C::package::ClosedPackage& p,const tasks::ear234::package::ClosedPackage& contexts,const std::string& key,const std::string& id){try{
 const auto& d=p.lookup(key,id);if(navigationPending_||draftBusy_)return false;
 for(const auto& old:entries_){auto v=old.second->owner->learnerView();if(!old.second->navigationFenced&&(debt(v)||(!inactive(v)&&!old.second->owner->history().empty())))return false;if(old.second->context&&!old.second->context->canOpenAnotherSource())return false;}
 auto it=entries_.find(key);if(it==entries_.end()){
  auto next=std::make_unique<Entry>(d);next->identity=id;
  if(auto expected=d.binding().find("required_complete_context_owner")){
   next->contextKey=f(*expected,"source_key").string();const auto& cd=tasks::ear234::definition(next->contextKey);const auto cid=f(cd.binding(),"source_identity").string();contexts.lookup(next->contextKey,cid);
   next->context=std::make_shared<EarSourceProcedureView>();next->context->embeddedDraftScope();if(!next->context->open(contexts,next->contextKey,cid))throw std::runtime_error("Exact contextual source unavailable");
   juce::Component::SafePointer<C43SourceProcedureView> safe(this);next->context->onOwnerChanged=[safe]{if(safe)safe->contextChanged();};next->context->onBack=[safe]{if(safe&&safe->prepareForNavigation()&&safe->onBack)safe->onBack();};next->context->onSettings=[safe]{return safe&&safe->prepareForNavigation()&&safe->onSettings&&safe->onSettings();};addChildComponent(*next->context);
  }
  entries_.emplace(key,std::move(next));
 }
 cacheFields();package_=p;contextPackage_=contexts;key_=key;resetProvider();lastError_.clear();render();return true;
 }catch(const std::exception&){fail("The exact closed source or required context is unavailable.");return false;}}
C43ProcedureGesture C43SourceProcedureView::capture(int role,const std::string& action)const{
 C43ProcedureGesture g;g.key_=key_;g.role_=role;g.action_=action;g.generation_=generation_;g.formGeneration_=form_.formGeneration();g.roleEpoch_=roleEpoch_;
 if(entry()){
  g.token_.emplace(role==Provider?entry()->owner->captureSourceChoices(action):entry()->owner->capture(role==Learner?action:role==ProviderSetup?"availability":"stop"));
  if(role==Learner&&action=="attach_complete_context"&&entry()->context){
   auto* owner=entry()->context->retainedOwner(entry()->contextKey);if(owner){g.contextKey_=entry()->contextKey;g.contextOwner_=entry()->context->sharedOwner(entry()->contextKey);g.contextToken_.emplace(owner->capture("view_control"));}
  }
 }return g;
}
bool C43SourceProcedureView::current(const C43ProcedureGesture& g)const{
 if(draftBusy_||!isEnabled()||!entry()||!g.token_||g.key_!=key_||g.generation_!=generation_||g.roleEpoch_!=roleEpoch_||!entry()->owner->current(*g.token_))return false;
 if(g.role_==Learner||g.role_==Provider||g.role_==ProviderSetup){if(g.formGeneration_!=form_.formGeneration()||g.action_!=selectedAction_)return false;if(g.role_==Learner&&mode_!=Mode::Learner)return false;if(g.role_==Provider&&(!providerAuthorized_||mode_!=Mode::Provider))return false;if(g.role_==ProviderSetup&&mode_!=Mode::ProviderSetup)return false;}
 if(g.action_=="attach_complete_context")return entry()->context&&g.contextOwner_&&g.contextToken_&&g.contextKey_==entry()->contextKey&&entry()->context->retainedOwner(g.contextKey_)==g.contextOwner_.get()&&g.contextOwner_->current(*g.contextToken_);
 return true;
}
void C43SourceProcedureView::fail(const std::string& why){lastError_=why;std::string s;if(entry()){auto v=learnerView();s=manual_text::releaseGuidance(yes(v,"manual_release_debt"),yes(v,"external_source_stop_debt"));if(entry()->context)s+=yes(v,"context_complete_and_current")?"Required context is complete and current.\n":"Required context is not complete and current.\n";}s+="The app supplies no source audio or curriculum credit. ";manual_text::setReadOnlyText(status_,ju(s+"\n"+why));}
void C43SourceProcedureView::deliver(const C43ProcedureGesture& g){if(!current(g)){fail("This control belongs to an earlier owner, role, action or context. Choose the current action.");return;}try{
 if(g.role_==Back||g.role_==Settings){if(!prepareForNavigation())return;if(g.role_==Back){if(onBack)onBack();}else if(onSettings)onSettings();return;}
 if(g.role_==OpenProvider){if(navigationPending_||debt(learnerView())||inactive(learnerView()))throw std::runtime_error("Provider role unavailable");resetProvider();mode_=Mode::ProviderSetup;render();return;}
 if(g.role_==ReturnLearner){resetProvider();render();return;}
 if(g.role_==RefreshContext){render();return;}
 auto input=earReportNativeInput(selectedSchema_,form_.read());
 if(g.role_==ProviderSetup){tasks::ear234::validateTypedInput(selectedSchema_,input);const auto currentView=learnerView();const auto& av=f(currentView,"availability_report");if(!yes(input,"external_provider_role_confirmed")||!yes(input,"actual_source_material_ready")||av.null()||f(av,"material_available")!=J("yes")||f(av,"compatible_exact_unit")!=J("yes")||f(av,"provider_kind")!=f(input,"provider_kind")||f(av,"reference")!=f(input,"reference"))throw std::runtime_error("Actual matching external provider setup required");cacheFields();entry()->fields.erase(fieldSlot());clearFieldBinding();providerAuthorized_=true;++roleEpoch_;mode_=Mode::Provider;invalidateContextControls();render();return;}
 cacheFields();const auto submitted=fieldSlot();
 if(g.action_=="attach_complete_context")entry()->owner->attachContextCompletion(*g.token_,g.contextOwner_);
 else{
  if(f(nativeSchema_,"properties").find("source_key"))input.object()["source_key"]=key_;
  tasks::ear234::validateTypedInput(nativeSchema_,input);entry()->owner->apply(*g.token_,input);
 }
 entry()->fields.erase(submitted);if(g.role_==Learner)entry()->learnerAction.clear();clearFieldBinding();entry()->navigationFenced=false;
 if(g.role_==Learner&&(g.action_=="availability"||g.action_=="stop"||g.action_=="navigate"||g.action_=="restart_owned_trial"||g.action_=="reopen"||g.action_=="retry_complete_unit"))resetProvider();
 lastError_.clear();render();
 }catch(const std::exception&){fail("The current source guard refused this report. Review the required fields, actual context and explicit release; retained work remains owned.");}}
std::vector<std::string> C43SourceProcedureView::instructionText()const{
 std::vector<std::string> out{"The app supplies no audio, hearing observation, attack clock or credit. Every report is your explicit manual declaration."};if(!entry())return out;auto v=learnerView();if(auto cue=v.find("instruction"))out.push_back(readable(*cue));
 if(mode_==Mode::ProviderSetup)out.push_back("External provider only: explicitly confirm the actual role and ready material, matching the learner's availability report. This setup supplies no source material and creates no native performance report.");
 else if(mode_==Mode::Provider)out.push_back("External provider only. Use actual compatible material outside the app. These source choices are private from the learner; seeing this sheet is prior exposure, not a blind trial.");
 else out.push_back("Commit the complete response before the offered explicit reveal. STOP, release and full owned retry retain your history and source exposure.");
 if(entry()->context)out.push_back("Complete the exact contextual source in the adjacent retained panel, including its release. Refresh attachment, then attach the actual current completed owner; a pasted conclusion cannot substitute.");
 return out;
}
void C43SourceProcedureView::configureForm(const J& schema,int role,const std::string& action){
 cacheFields();nativeSchema_=schema;selectedSchema_=editableSchema(schema);selectedAction_=action;const auto token=role==Provider?entry()->owner->captureSourceChoices(action):entry()->owner->capture(role==ProviderSetup?"availability":action);auto gen=generation_,epoch=roleEpoch_;auto key=key_;juce::Component::SafePointer<C43SourceProcedureView> safe(this);
 form_.configure(earReportPresentationSchema(selectedSchema_),instructionText(),[safe,token,gen,epoch,key]{return safe&&safe->generation_==gen&&safe->roleEpoch_==epoch&&safe->key_==key&&safe->entry()&&safe->entry()->owner->current(token);});
 submit_.bind([safe,role,action]{return safe->capture(role,action);},[safe](const auto& g){if(safe)safe->deliver(g);});fieldKey_=key_;fieldRole_=role==Learner?"learner":"source";if(role==ProviderSetup&&providerDraftId_.empty())providerDraftId_=storage::newUuid();fieldAction_=action+(role==ProviderSetup?"~"+providerDraftId_:std::string{})+"@"+content::sha256(json::stringify(schema));std::int64_t revision=0;f(learnerView(),"revision").integer(revision);fieldRevision_=static_cast<std::uint64_t>(revision);fieldEpoch_=roleEpoch_;if(role==Learner)entry()->learnerAction=action;auto saved=entry()->fields.find(fieldSlot());if(role!=ProviderSetup&&saved!=entry()->fields.end()&&!form_.restoreDraft(f(saved->second,"form")))throw std::runtime_error("Retained C43 fields unsupported; original preserved");submit_.setEnabled(!draftBusy_);
 if(action=="attach_complete_context"){auto* other=entry()->context?entry()->context->retainedOwner(entry()->contextKey):nullptr;submit_.setEnabled(other&&f(other->learnerView(),"state")==J("completed")&&!debt(other->learnerView()));}resized();
}
void C43SourceProcedureView::selectAction(int id,std::uint64_t gen,const C::Token& token){if(!entry()||gen!=generation_||!entry()->owner->current(token)){fail("This action menu is stale.");return;}if(id<=0||static_cast<std::size_t>(id)>actions_.size()){cacheFields();if(entry())entry()->learnerAction.clear();clearFieldBinding();form_.invalidate();selectedSchema_=J();selectedAction_.clear();submit_.setEnabled(false);return;}auto action=actions_[id-1];auto forms=mode_==Mode::Provider?f(entry()->owner->sourcePlayerView(),"source_choice_forms"):learnerActions();if(mode_==Mode::Provider&&!providerAuthorized_){fail("External provider setup is required.");return;}configureForm(f(forms,action),mode_==Mode::Provider?Provider:Learner,action);}
void C43SourceProcedureView::render(){
 cacheFields();clearFieldBinding();++generation_;form_.invalidate();selectedSchema_=J();nativeSchema_=J();selectedAction_.clear();actions_.clear();actionMenu_.clear(juce::dontSendNotification);submit_.setEnabled(false);juce::Component::SafePointer<C43SourceProcedureView> safe(this);
 for(auto p:std::vector<std::pair<C43ProcedureButton*,int>>{{&provider_,OpenProvider},{&learner_,ReturnLearner},{&back_,Back},{&settings_,Settings},{&refreshContext_,RefreshContext}})p.first->bind([safe,role=p.second]{return safe->capture(role,"view_control");},[safe](const auto& g){if(safe)safe->deliver(g);});
 for(auto& p:entries_)if(p.second->context){const bool visible=p.first==key_&&mode_==Mode::Learner;p.second->context->setVisible(visible);p.second->context->setEnabled(visible);}
 auto* context=entry()&&mode_==Mode::Learner?entry()->context.get():nullptr;
 if(contextViewport_.getViewedComponent()!=context)contextViewport_.setViewedComponent(context,false);
 contextViewport_.setVisible(context!=nullptr);
 contextLabel_.setVisible(entry()&&entry()->context&&mode_==Mode::Learner);refreshContext_.setVisible(contextLabel_.isVisible());
 if(!entry()){phase_.setText("Select an exact closed printed source",juce::dontSendNotification);provider_.setEnabled(false);learner_.setVisible(false);back_.setEnabled(false);settings_.setEnabled(false);form_.setInstructions(instructionText());resized();return;}
 back_.setEnabled(true);settings_.setEnabled(true);auto v=learnerView();const auto idle=entry()->owner->capture("stop");auto gen=generation_,epoch=roleEpoch_;auto key=key_;
 form_.configure(O{{"type","object"},{"properties",O{}},{"required",J::Array{}},{"additionalProperties",false}},instructionText(),[safe,idle,gen,epoch,key]{return safe&&safe->generation_==gen&&safe->roleEpoch_==epoch&&safe->key_==key&&safe->entry()&&safe->entry()->owner->current(idle);});
 phase_.setText(ju((mode_==Mode::Learner?"Learner — ":"External provider only — ")+label(f(v,"state").string())),juce::dontSendNotification);
 std::string shown;if(mode_==Mode::Provider){const auto source=entry()->owner->sourcePlayerView();shown="Provider-only exact source material and qualified interpretation:\n"+readable(f(source,"original_parameters"))+"\n"+readable(f(source,"original_source"))+"\n"+readable(f(source,"Root_selected_interpretation"));}
 else if(mode_==Mode::Learner){for(auto k:{"public_study_row","current_command_prompt","source_stage_cue","current_complete_command","learner_worksheet","diagnosis"})if(auto x=v.find(k);x&&!x->null())shown+=label(k)+": "+readable(*x)+"\n";if(yes(v,"explicit_current_reference_disclosure"))shown+="Explicitly revealed current source and qualified interpretation:\n"+readable(f(v,"current_reference"));}
 manual_text::setReadOnlyText(presentation_,ju(shown));std::string status=manual_text::releaseGuidance(yes(v,"manual_release_debt"),yes(v,"external_source_stop_debt"));if(entry()->context)status+=yes(v,"context_complete_and_current")?"Required context is complete and current.\n":"Required context is not complete and current.\n";status+="The app supplies no source audio, inferred timing or curriculum credit.";if(!lastError_.empty())status+='\n'+lastError_;manual_text::setReadOnlyText(status_,ju(status));
 std::vector<std::string> history;auto events=entry()->owner->history();for(std::size_t n=events.size()>8?events.size()-8:0;n<events.size();++n){const auto& e=events[n];std::string h=label(f(e,"action").string());if(auto role=e.find("role");role&&*role==J("trusted_source_player"))h+=" — provider choices retained privately";else if(auto report=e.find("report"))h+=" — my manual report: "+readable(*report);history.push_back(h);}form_.setHistorySummary(history);
 provider_.setVisible(mode_==Mode::Learner);provider_.setEnabled(!navigationPending_&&!debt(v)&&!inactive(v));learner_.setVisible(mode_!=Mode::Learner);actionMenu_.setVisible(mode_!=Mode::ProviderSetup);
 if(mode_==Mode::ProviderSetup)configureForm(setupSchema(f(v,"availability_report")),ProviderSetup,"provider_setup");
 else{auto forms=mode_==Mode::Provider?f(entry()->owner->sourcePlayerView(),"source_choice_forms"):learnerActions();for(const auto& a:forms.object()){if(a.first=="navigate")continue;if(navigationPending_&&a.first!="release"&&a.first!="stop")continue;actions_.push_back(a.first);actionMenu_.addItem(ju(label(a.first)),static_cast<int>(actions_.size()));}auto token=entry()->owner->capture("stop");actionMenu_.onChange=[safe,gen,token]{if(safe)safe->selectAction(safe->actionMenu_.getSelectedId(),gen,token);};}resized();
}
bool C43SourceProcedureView::prepareForNavigation(){if(draftBusy_)return false;cacheFields();if(!entry())return true;resetProvider();navigationPending_=true;bool settled=true;
 for(auto& p:entries_){auto& e=*p.second;if(e.context&&!e.context->prepareForNavigation())settled=false;if(e.navigationFenced)continue;auto v=e.owner->learnerView();if(debt(v)){if(f(v,"state")!=J("awaiting_exit_release"))e.owner->apply(e.owner->capture("navigate"),O{{"reason","Explicit navigation requires actual learner/source release"}});settled=false;continue;}if(!inactive(v)&&!e.owner->history().empty())e.owner->apply(e.owner->capture("navigate"),O{{"reason","Explicit navigation requested"}});if(e.owner->fenceInactiveForNavigation())e.navigationFenced=true;else settled=false;}
 render();if(!settled)return false;navigationPending_=false;return true;
}
void C43SourceProcedureView::resumeAfterNavigation(){resetProvider();render();}
namespace {
json::Limits c43WorkspaceLimits(){json::Limits l;l.bytes=64*1024*1024;l.stringBytes=64*1024*1024;l.depth=96;l.values=2000000;return l;}
std::uint64_t c43OwnerRevision(const tasks::c43::Owner&owner){std::int64_t n=0;manual_draft::D::require(f(owner.learnerView(),"revision").integer(n)&&n>=1,"Private C43 revision");return static_cast<std::uint64_t>(n);}
}
bool C43SourceProcedureView::attachDraftStore(storage::ProfileStore&store,const std::string&profile){if(!draftPanel_.canAttach(profile))return false;try{resumeAfterNavigation();return draftPanel_.attach(store,profile);}catch(const std::exception&){return false;}}
bool C43SourceProcedureView::detachDraftStore(){return draftPanel_.detach();}
bool C43SourceProcedureView::prepareDraftStoreReopen(){return !draftJobBusy()&&prepareForNavigation();}
std::string C43SourceProcedureView::workspaceStamp(){cacheFields();J::Array rows;for(const auto&p:entries_){J::Array forms;for(const auto&item:p.second->fields)forms.push_back(item.second);rows.emplace_back(O{{"key",p.first},{"revision",J::fromInteger(c43OwnerRevision(*p.second->owner))},{"forms",forms},{"action",p.second->learnerAction},{"context",p.second->context?J(p.second->context->workspaceStamp()):J()}});}return content::sha256(json::stringify(O{{"selected",key_},{"owners",rows}}));}
std::string C43SourceProcedureView::fieldSlot()const{return json::stringify(J::Array{fieldRole_,fieldAction_,J::fromInteger(fieldRevision_)});}
void C43SourceProcedureView::clearFieldBinding(){fieldKey_.clear();fieldRole_.clear();fieldAction_.clear();fieldRevision_=fieldEpoch_=0;}
void C43SourceProcedureView::cacheFields(){if(fieldKey_.empty()||fieldEpoch_!=roleEpoch_)return;auto i=entries_.find(fieldKey_);if(i==entries_.end()||c43OwnerRevision(*i->second->owner)!=fieldRevision_)return;auto draft=form_.captureDraft();i->second->fields[fieldSlot()]=O{{"role",fieldRole_},{"action",fieldAction_},{"watermark",J::fromInteger(fieldRevision_)},{"form",std::move(draft)}};}
void C43SourceProcedureView::setDraftBusy(bool busy){draftBusy_=busy;for(auto&p:entries_)if(p.second->context){p.second->context->setDraftBusy(busy);if(!busy)p.second->context->setEnabled(p.first==key_&&mode_==Mode::Learner);}setEnabled(!busy);}
std::function<std::string()> C43SourceProcedureView::captureWorkspace(){
 if(!draftBusy_)throw std::runtime_error("Freeze C43 workspace and context before capture");cacheFields();J::Array rows;std::map<std::string,std::shared_ptr<C::Owner>>owners;std::map<std::string,std::function<std::string()>>contexts;
 for(const auto&p:entries_){J::Array forms;for(const auto&item:p.second->fields)forms.push_back(item.second);rows.emplace_back(O{{"key",p.first},{"identity",p.second->identity},{"forms",forms},{"learner_action",p.second->owner->learnerActions().find(p.second->learnerAction)?p.second->learnerAction:std::string{}}});owners.emplace(p.first,p.second->owner);if(p.second->context)contexts.emplace(p.first,p.second->context->captureWorkspace());}
 const auto selected=key_;return [rows=std::move(rows),owners=std::move(owners),contexts=std::move(contexts),selected]()mutable{
  for(auto&row:rows){const auto key=f(row,"key").string();auto&owner=*owners.at(key);row.object()["owner"]=owner.continuation();auto context=contexts.find(key);row.object()["context"]=context==contexts.end()?J():J(context->second());manual_draft::validateForms(f(row,"forms"),c43OwnerRevision(owner));}
  const J body=O{{"format","c43-source-workspace-v1"},{"selected_key",selected},{"owners",rows}};auto bytes=json::stringify(O{{"body",body},{"sha256",content::sha256(json::stringify(body))}});json::parse(bytes,c43WorkspaceLimits());return bytes;
 };
}
C43SourceProcedureView::Workspace C43SourceProcedureView::decodeWorkspace(const C::package::ClosedPackage&package,const tasks::ear234::package::ClosedPackage&contextPackage,const std::string&bytes){
 auto envelope=json::parse(bytes,c43WorkspaceLimits());const auto&body=f(envelope,"body");manual_draft::D::require(envelope.object().size()==2&&f(envelope,"sha256")==J(content::sha256(json::stringify(body)))&&body.object().size()==3&&f(body,"format")==J("c43-source-workspace-v1"),"Private C43 workspace format/checksum");Workspace out;out.metadata=body;const auto&rows=f(body,"owners").array();manual_draft::D::require(rows.size()<=43,"Private C43 owner roster extent");
 const auto resolve=[&](const std::string&key)->const tasks::ear234::Definition&{const auto&d=tasks::ear234::definition(key);return contextPackage.lookup(key,f(d.binding(),"source_identity").string());};
 for(const auto&row:rows){manual_draft::D::require(row.object().size()==6,"Private C43 owner record shape");const auto key=f(row,"key").string();const auto&d=package.lookup(key,f(row,"identity").string());auto restored=C::Owner::restoreContinuation(d,f(row,"owner").string(),resolve);manual_draft::validateForms(f(row,"forms"),c43OwnerRevision(*restored.owner));const auto action=f(row,"learner_action").string();manual_draft::D::require(action.size()<=256,"Private C43 action bound");if(!action.empty())manual_draft::D::require(restored.owner->learnerActions().find(action),"Private C43 selected action unavailable");
  if(auto expected=d.binding().find("required_complete_context_owner")){manual_draft::D::require(f(row,"context").isString(),"Required Ear workspace missing");auto context=EarSourceProcedureView::decodeWorkspace(contextPackage,f(row,"context").string());const auto contextKey=f(*expected,"source_key").string();manual_draft::D::require(context.owners.count(contextKey),"Required Ear owner absent");if(restored.context){manual_draft::D::require(context.owners.at(contextKey)->continuation()==restored.context->continuation(),"C43 dependency and actual Ear panel snapshot differ");context.owners[contextKey]=std::move(restored.context);}out.contexts.emplace(key,std::move(context));}
  else manual_draft::D::require(f(row,"context").null()&&!restored.context,"Unexpected Ear dependency");
  manual_draft::D::require(out.owners.emplace(key,std::shared_ptr<C::Owner>(std::move(restored.owner))).second,"Duplicate C43 owner");
 }
 manual_draft::D::require(f(body,"selected_key").string().empty()?rows.empty():out.owners.count(f(body,"selected_key").string())==1,"Selected C43 owner absent");return out;
}
C43SourceProcedureView::Workspace C43SourceProcedureView::decodeWorkspace(const C::package::ClosedPackage&package,const tasks::ear234::package::ClosedPackage&contexts,const storage::manual_drafts::Loaded&loaded){
 manual_draft::D::require(loaded.receipt.status==storage::Status::Confirmed,"Original C43 profile read unconfirmed");auto out=decodeWorkspace(package,contexts,loaded.payload);const auto key=f(out.metadata,"selected_key").string();manual_draft::D::require(key==loaded.sourceKey&&out.owners.count(key),"C43 profile root source differs");const auto&owner=*out.owners.at(key);manual_draft::D::require(content::sha256(json::stringify(owner.retainedDefinition().binding()))==loaded.sourceContract&&loaded.watermark>=0&&c43OwnerRevision(owner)==static_cast<std::uint64_t>(loaded.watermark),"C43 profile contract or revision differs");return out;
}
bool C43SourceProcedureView::installWorkspace(const C::package::ClosedPackage&package,const tasks::ear234::package::ClosedPackage&contextPackage,Workspace&&workspace){return installWorkspaceImpl(package,contextPackage,std::move(workspace),false);}
bool C43SourceProcedureView::installWorkspaceImpl(const C::package::ClosedPackage&package,const tasks::ear234::package::ClosedPackage&contextPackage,Workspace&&workspace,bool confirmed){try{
 if(draftBusy_||(!confirmed&&!entries_.empty()))return false;std::map<std::string,std::unique_ptr<Entry>>candidate;auto selected=f(workspace.metadata,"selected_key").string();std::string action;
 for(const auto&row:f(workspace.metadata,"owners").array()){const auto key=f(row,"key").string();const auto&d=package.lookup(key,f(row,"identity").string());auto e=std::make_unique<Entry>(d);e->owner=workspace.owners.at(key);e->identity=f(row,"identity").string();e->learnerAction=f(row,"learner_action").string();for(const auto&record:f(row,"forms").array())e->fields.emplace(manual_draft::slot(record),record);
  if(auto expected=d.binding().find("required_complete_context_owner")){e->contextKey=f(*expected,"source_key").string();e->context=std::make_shared<EarSourceProcedureView>();e->context->embeddedDraftScope();manual_draft::D::require(e->context->installWorkspace(contextPackage,std::move(workspace.contexts.at(key))),"Private Ear panel unsupported");juce::Component::SafePointer<C43SourceProcedureView>safe(this);e->context->onOwnerChanged=[safe]{if(safe)safe->contextChanged();};e->context->onBack=[safe]{if(safe&&safe->prepareForNavigation()&&safe->onBack)safe->onBack();};e->context->onSettings=[safe]{return safe&&safe->prepareForNavigation()&&safe->onSettings&&safe->onSettings();};}
  if(key==selected){action=e->learnerAction;if(!action.empty()){auto schema=f(e->owner->learnerActions(),action);const auto slot=json::stringify(J::Array{"learner",action+"@"+content::sha256(json::stringify(schema)),J::fromInteger(c43OwnerRevision(*e->owner))});auto saved=e->fields.find(slot);if(saved!=e->fields.end()){TypedManualForm probe;probe.configure(earReportPresentationSchema(editableSchema(schema)),{},[]{return true;});manual_draft::D::require(probe.restoreDraft(f(saved->second,"form")),"Private C43 form unsupported");}}}
  candidate.emplace(key,std::move(e));
 }
 auto retainedPackage=package;auto retainedContexts=contextPackage;auto oldPackage=package_;auto oldContexts=contextPackage_;const auto oldNavigation=navigationPending_;clearFieldBinding();form_.invalidate();entries_.swap(candidate);package_=std::move(retainedPackage);contextPackage_=std::move(retainedContexts);key_.swap(selected);navigationPending_=false;
 try{resetProvider();lastError_.clear();render();if(!action.empty()){auto i=std::find(actions_.begin(),actions_.end(),action);if(i!=actions_.end()){const int id=static_cast<int>(std::distance(actions_.begin(),i))+1;actionMenu_.setSelectedId(id,juce::dontSendNotification);selectAction(id,generation_,entry()->owner->capture("stop"));}}return true;}
 catch(...){contextViewport_.setViewedComponent(nullptr,false);clearFieldBinding();form_.invalidate();entries_.swap(candidate);package_=std::move(oldPackage);contextPackage_=std::move(oldContexts);key_.swap(selected);navigationPending_=oldNavigation;resetProvider();render();throw;}
 }catch(const std::exception&){fail("Saved manual workspace unsupported; retain original bytes and current work.");return false;}}
void C43SourceProcedureView::contextChanged(){if(draftBusy_)return;const auto action=entry()?entry()->learnerAction:std::string{};render();if(entry()&&!action.empty()){auto i=std::find(actions_.begin(),actions_.end(),action);if(i!=actions_.end()){const int id=static_cast<int>(std::distance(actions_.begin(),i))+1;actionMenu_.setSelectedId(id,juce::dontSendNotification);selectAction(id,generation_,entry()->owner->capture("stop"));}}}
void C43SourceProcedureView::resized(){
 auto r=getLocalBounds().reduced(12);draftPanel_.setBounds(r.removeFromBottom(90));
 heading_.setBounds(r.removeFromTop(manual_text::labelHeight(heading_,r.getWidth(),28)));
 phase_.setBounds(r.removeFromTop(manual_text::labelHeight(phase_,r.getWidth(),24)));
 auto nav=r.removeFromTop(34);back_.setBounds(nav.removeFromLeft(70));settings_.setBounds(nav.removeFromLeft(110));
 provider_.setBounds(provider_.isVisible()?nav.removeFromLeft(std::min(220,nav.getWidth())):juce::Rectangle<int>{});
 learner_.setBounds(learner_.isVisible()?nav.removeFromLeft(std::min(155,nav.getWidth())):juce::Rectangle<int>{});
 refreshContext_.setBounds(nav);
 worksheet_.setBounds(r.removeFromTop(30));
 const auto statusHeight=std::clamp(manual_text::textHeight(status_,r.getWidth(),64),64,std::max(64,r.getHeight()/3));
 status_.setBounds(r.removeFromBottom(statusHeight));
 if(contextViewport_.isVisible()){
  const auto width=std::min(std::max(420,r.getWidth()/2),std::max(1,r.getWidth()-320));
  auto context=r.removeFromRight(width);contextLabel_.setBounds(context.removeFromTop(manual_text::labelHeight(contextLabel_,width,28)));
  contextViewport_.setBounds(context);
  if(auto* view=contextViewport_.getViewedComponent())view->setSize(std::max(1,context.getWidth()-18),std::max(680,context.getHeight()));
  r.removeFromRight(8);
 }
 presentation_.setBounds(r.removeFromBottom(std::min(110,std::max(48,r.getHeight()/4))));
 actionLabel_.setBounds(r.removeFromTop(manual_text::labelHeight(actionLabel_,r.getWidth(),24)));
 if(actionMenu_.isVisible())actionMenu_.setBounds(r.removeFromTop(30));
 submit_.setBounds(r.removeFromBottom(32));form_.setBounds(r);
}
std::string C43SourceProcedureView::learnerHistoryExport(){
 if(draftBusy_||mode_!=Mode::Learner||!entry())throw std::runtime_error("Return to learner role and finish the original draft job before exporting");cacheFields();J::Array owners;
 for(const auto&p:entries_){J::Array history,fields;for(const auto&e:p.second->owner->history())history.push_back(e);for(const auto&record:p.second->fields)if(f(record.second,"role")==J("learner"))fields.push_back(record.second);const auto&d=p.second->owner->retainedDefinition();J context;if(p.second->context)context=storage::parseCanonical(p.second->context->learnerHistoryExport());owners.emplace_back(O{{"source_key",p.first},{"source_identity",p.second->identity},{"contract_sha256",content::sha256(json::stringify(d.binding()))},{"learner_state",p.second->owner->learnerView()},{"history",history},{"learner_editor_references",fields},{"actual_context_worksheet",context}});}
 return storage::canonical(O{{"format","fathom-c43-learner-worksheet-v1"},{"selected_source",key_},{"owners",owners},{"observed_performance",false},{"grants_credit",false},{"notice","Manual declarations and separate learner editor references only. Context is the actual linked learner projection; stale context is not promoted. Source-role reports are redacted natively; private source forms, provider setup and replay bytes are excluded. No measured hearing, playing, safety, mastery or user acceptance is implied."}});
}
bool C43SourceProcedureView::copyLearnerHistory(){if(draftBusy_)return false;if(mode_!=Mode::Learner||!entry()||std::any_of(entries_.begin(),entries_.end(),[](const auto&p){return p.second->context&&p.second->context->providerSheetVisible();})){fail("Return all open panels to learner role before copying the worksheet.");return false;}try{const auto bytes=learnerHistoryExport();if(onCopyLearnerHistory)onCopyLearnerHistory(bytes);else{juce::SystemClipboard::copyTextToClipboard(ju(bytes));if(juce::SystemClipboard::getTextFromClipboard().toStdString()!=bytes)throw std::runtime_error("Clipboard readback differs");}fail("Learner worksheet copied. Source setup remains private; editor references are not submitted reports.");return true;}catch(const std::exception&){fail("Worksheet delivery failed. Current work and original reports remain unchanged.");return false;}}

}
