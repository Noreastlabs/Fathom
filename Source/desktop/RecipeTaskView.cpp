#include "desktop/Appearance.hpp"
#include "desktop/RecipeTaskView.hpp"
#include "desktop/TypedManualForm.hpp"
#include <algorithm>
#include <map>
#include <sstream>

namespace fathom::desktop {
namespace {
using namespace tasks::recipes;
using V = json::Value;
using O = V::Object;
juce::String ju(const std::string& text) { return juce::String::fromUTF8(text.c_str()); }
const V& f(const V& value, const char* key) { const auto* p=value.find(key); if(!p)throw Error("VIEW_CONTRACT_FIELD"); return *p; }
std::string text(const V& value, const char* key) { return f(value,key).string(); }
std::string integer(const V& value) { std::int64_t n{}; if(!value.integer(n))throw Error("VIEW_INTEGER"); return std::to_string(n); }
std::string humanValue(const V& value) {
    if(value.isString())return value.string();
    if(value.isBool())return value.boolean()?"I report yes":"I report no";
    if(value.isNumber())return integer(value);
    if(value.isArray()){std::string out;for(const auto& item:value.array()){if(!out.empty())out+="; ";out+=humanValue(item);}return out;}
    return "Not supplied";
}
std::string phaseName(const View& view) {
    switch(view.phase){case Phase::Select:return "Choose explicitly";case Phase::Steps:return "Manual step "+std::to_string(view.step.value_or(0));
    case Phase::Release:return "Physical release required";case Phase::Closed:return "Pass closed";}return {};
}
std::string label(const std::string& key) {
    static const std::map<std::string,std::string> names{
      {"ordered_names","Names in call / answer order (separate with semicolon)"},
      {"prepared_safely_reported","I prepared safely"},
      {"complete_printed_pair_played_reported","I played the complete printed call and answer"},
      {"eight_contact_call_played_reported","I played the eight-note variation call"},
      {"silent_source_beats","Source literal: silent beats"},
      {"internal_bar_count_continued_reported","I continued the internal bar count through the silence"},
      {"eight_contact_answer_ended_on_existing_A_reported","I played the eight-note answer ending on its existing A"},
      {"minor_call_dominant_answer_distinguished_reported","I distinguished the minor call and dominant answer"},
      {"rhythmic_identity_preserved_reported","I preserved the rhythmic identity"},
      {"two_silent_beats_counted_with_internal_bar_count_reported","I counted two silent beats while continuing the internal bar count"},
      {"final_A_completed_answer_without_extra_attack_reported","The existing final A completed my answer; I added no extra attack"},
      {"final_A_released_reported","I released the final A"},
      {"source_safety_followed_reported","I followed the source safety instructions"},
      {"printed_label","Name the printed recovery pair"},{"printed_roles","Name its printed harmonic roles"},
      {"chord","Name the chord context"},{"origin","Name the tension pitch"},{"target","Name the destination pitch"},
      {"target_named_before_origin_reported","I named the target before playing the tension"},
      {"existing_bar_and_pulse_prepared_reported","I prepared the existing bar and pulse"},
      {"chosen_contacts_safe_and_secure_reported","My chosen contacts are safe and secure"},
      {"chosen_origin_played_reported","I played my chosen tension contact"},
      {"chosen_named_target_reached_preserving_pulse_reported","I reached my chosen named target while preserving the pulse"},
      {"rest_of_bar_plan","Restate the remainder plan you actually used"},
      {"rest_of_existing_bar_simplified_reported","I simplified the rest of the existing bar"},
      {"chosen_target_secure_reported","My chosen target was secure"},
      {"pulse_preserved_reported","I preserved the pulse"},
      {"named_destination_heard_reported","I heard the named destination"},
      {"two_selected_pair_contacts_played_reported","I played both selected pair contacts"},
      {"final_target_released_reported","I released the final target"},
      {"released_completely_reported","I physically released completely"}};
    const auto found=names.find(key);if(found==names.end())throw Error("VIEW_REPORT_LABEL");return found->second;
}
std::string contact(const V& value, bool chosen) {
    std::string note;
    if(const auto* p=value.find("printed_note"))note=p->string();
    else if(const auto* p=value.find("required_source_pitch"))note=p->string();
    std::string out=note;
    if(const auto* p=value.find("degree"))out+=" ("+p->string()+")";
    if(!out.empty())out+=" — ";
    out+=(chosen?"chosen ":"printed ");out+="string "+integer(f(value,"string"))+", fret "+integer(f(value,"fret"));
    if(const auto* p=value.find("role"))out+="; role "+p->string();
    if(const auto* p=value.find("selected_pick"))out+="; chosen pick "+p->string();
    return out;
}
std::string outcome(Outcome value) {
    switch(value){case Outcome::None:return "No final outcome";case Outcome::UserReportedStepsFinished:return "You reported the displayed steps finished";
    case Outcome::RetryRequested:return "Manual retry requested";case Outcome::Cancelled:return "Pass stopped";}return {};
}
void readOnly(juce::TextEditor& field, const char* id, const char* title) {
    manual_text::configureReadOnly(field,id,title);
}
}
RecipeTaskButton::RecipeTaskButton() {
    onClick=[this]{if(!capture||!deliver)return;const auto now=juce::Time::getMillisecondCounter();
        const auto gesture=pending_.value_or(capture());pending_.reset();
        if(delivered_&&now-lastDeliveryMs_<350)return;
        delivered_=true;lastDeliveryMs_=now;deliver(gesture);};
}
void RecipeTaskButton::mouseDown(const juce::MouseEvent& event){if(capture)pending_=capture();juce::TextButton::mouseDown(event);}
bool RecipeTaskButton::keyPressed(const juce::KeyPress& key){
    if(key.getKeyCode()==juce::KeyPress::spaceKey||key.getKeyCode()==juce::KeyPress::returnKey){if(capture)pending_=capture();triggerClick();return true;}
    return juce::TextButton::keyPressed(key);
}
RecipeTaskView::RecipeTaskView() {
    setComponentID("recipe-task-view");heading_.setComponentID("recipe-heading");phase_.setComponentID("recipe-phase");status_.setComponentID("recipe-status");
    readOnly(source_,"recipe-source","Complete retained source instructions and printed facts; scroll to read all.");
    readOnly(action_,"recipe-action","Current manual action and chosen contacts.");
    readOnly(history_,"recipe-history","Retained manual interaction history and diagnosis; scroll to read all.");
    inputViewport_.setComponentID("recipe-input-viewport");inputViewport_.setViewedComponent(&inputBody_,false);
    inputViewport_.setScrollBarsShown(true,false);
    for(auto* c:std::initializer_list<juce::Component*>{&heading_,&phase_,&status_,&source_,&action_,&history_,&inputViewport_})addAndMakeVisible(*c);
    strokeLabel_.setText("First pick: choose Down or Up",juce::dontSendNotification);stroke_.setComponentID("recipe-start-stroke");stroke_.setTextWhenNothingSelected("Choose D or U");stroke_.setTitle("Explicit first pick; no default or printed picking claim.");stroke_.addItem(ju("D — downstroke"),1);stroke_.addItem(ju("U — upstroke"),2);
    originLabel_.setText("Choose a tension contact",juce::dontSendNotification);origin_.setComponentID("recipe-origin");origin_.setTextWhenNothingSelected("Choose a contact");origin_.setTitle("Explicit performer choice; the source prints pitches, not positions.");
    targetLabel_.setText("Choose a nearest target contact",juce::dontSendNotification);target_.setComponentID("recipe-target");target_.setTextWhenNothingSelected("Choose a target");target_.setTitle("Provisional minimum pitch-distance menu; physical security must be reported manually.");
    planLabel_.setText(ju("Your explicit remainder plan (1–500 characters)"),juce::dontSendNotification);plan_.setComponentID("recipe-remainder-plan");plan_.setTitle("Your chosen plan for simplifying the existing bar; no default or generated attacks.");plan_.setMultiLine(true);plan_.setScrollbarsShown(true);
    releaseReport_.setButtonText("I physically released completely");releaseReport_.setComponentID("recipe-release-report");releaseReport_.setTitle("Report physical release explicitly before another pass or navigation.");
    for(auto* c:std::initializer_list<juce::Component*>{&strokeLabel_,&stroke_,&originLabel_,&origin_,&targetLabel_,&target_,&planLabel_,&plan_,&releaseReport_})inputBody_.addAndMakeVisible(*c);
    wire(choose_,Intent::Choose,"recipe-choose","Use my explicit choices");wire(report_,Intent::Report,"recipe-report","Submit my report");
    wire(retry_,Intent::Retry,"recipe-retry","Request retry");wire(stop_,Intent::Stop,"recipe-stop","Stop this pass");wire(unknown_,Intent::Retry,"recipe-unknown","I'm not sure",true);
    wire(release_,Intent::Release,"recipe-release","Confirm physical release");wire(again_,Intent::Again,"recipe-again","Begin another pass");
    wire(back_,Intent::Navigate,"recipe-back","Back to Learn");wire(settings_,Intent::Navigate,"recipe-settings","Settings");
    juce::Component::SafePointer<RecipeTaskView> safe(this);
    back_.deliver=[safe](const RecipeGesture& gesture){if(safe)safe->navigation(gesture,false);};
    settings_.deliver=[safe](const RecipeGesture& gesture){if(safe)safe->navigation(gesture,true);};
    worksheet_.setComponentID("recipe-copy-worksheet");worksheet_.onClick=[this]{copyLearnerHistory();};addAndMakeVisible(worksheet_);
    addAndMakeVisible(draftPanel_);draftPanel_.hooks.key=[this]{return task_?task_->retainedDefinition().sourceKey():std::string{};};draftPanel_.hooks.stamp=[this]{return workspaceStamp();};draftPanel_.hooks.freeze=[this](bool b){setDraftBusy(b);};draftPanel_.hooks.gate=[this]{return onDraftSaveGate&&onDraftSaveGate();};draftPanel_.hooks.prepareNavigation=[this]{return prepareForNavigation();};draftPanel_.hooks.reopenStore=[this]{return onDraftStoreReopen&&onDraftStoreReopen();};draftPanel_.hooks.loadRefused=[this]{resumeAfterNavigation();};
    draftPanel_.hooks.capture=[this]{if(!task_)throw std::runtime_error("No current recipe");SourceDraftPanel::Capture c;c.key=task_->retainedDefinition().sourceKey();c.contract=task_->retainedDefinition().contractSha256();c.stamp=workspaceStamp();c.watermark=static_cast<std::int64_t>(task_->revision());c.bytes=captureWorkspace();return c;};
    draftPanel_.hooks.decoder=[](){return std::function<std::shared_ptr<void>(const SourceDraftPanel::Loaded&)>([](const auto&l){return std::make_shared<Workspace>(decodeWorkspace(l));});};draftPanel_.hooks.install=[this](std::shared_ptr<void>w,const std::string&stamp){return installWorkspace(std::move(*std::static_pointer_cast<Workspace>(w)),stamp);};
    render();
}
void RecipeTaskView::wire(RecipeTaskButton& button, Intent intent, const char* id, const char* name, bool unknown) {
    button.setComponentID(id);button.setButtonText(ju(name));button.setTitle(ju(name));button.setWantsKeyboardFocus(true);
    juce::Component::SafePointer<RecipeTaskView> safe(this);
    button.capture=[safe,intent]{return safe?safe->capture(intent):RecipeGesture{};};
    button.deliver=[safe,intent,unknown](const RecipeGesture& gesture){if(safe)safe->command(intent,gesture,unknown);};addAndMakeVisible(button);
}
RecipeGesture RecipeTaskView::capture(Intent intent) const {return {task_?std::optional<Token>(task_->capture(intent)):std::nullopt,generation_};}
bool RecipeTaskView::current(const RecipeGesture& gesture, Intent intent) const {
    if(draftBusy_||!isEnabled()||!task_||!gesture.owner||gesture.generation!=generation_||gesture.owner->intent!=intent)return false;
    try{requireCurrentToken(*gesture.owner,task_->capture(intent));return true;}catch(const Error&){return false;}
}
bool RecipeTaskView::open(const std::string& key) {
    if(draftBusy_)return false;
    if(task_&&task_->view().phase!=Phase::Select&&task_->view().phase!=Phase::Closed){message_="Finish and physically release the current pass before opening another task.";render();return false;}
    try{
        auto next=std::make_shared<RecipeTask>(definition(key));
        if(task_){retainFields();auto old=task_->history();archived_.insert(archived_.end(),old.begin(),old.end());archivedOwners_.push_back(task_);}
        task_=std::move(next);++generation_;navigationPrepared_=false;renderedInputs_.clear();message_.clear();clearChoices();populateOrigins();render();return true;
    }catch(const Error&){message_="This task is outside the verified compiled family. The current task remains open.";render();return false;}
}
void RecipeTaskView::clearChoices(){stroke_.setSelectedId(0,juce::dontSendNotification);origin_.setSelectedId(0,juce::dontSendNotification);target_.clear(juce::dontSendNotification);targets_.clear();plan_.setText({},false);releaseReport_.setToggleState(false,juce::dontSendNotification);}
void RecipeTaskView::populateOrigins(){
    origin_.clear(juce::dontSendNotification);origins_.clear();if(!task_||task_->retainedDefinition().recipe()!=Recipe::RecoveryPair)return;
    origins_=f(allowedChoices(task_->retainedDefinition()),"source_contacts").array();
    for(std::size_t n=0;n<origins_.size();++n)origin_.addItem(ju(contact(origins_[n],true)),static_cast<int>(n+1));
}
void RecipeTaskView::updateTargets(const RecipeGesture& gesture){
    if(navigationPrepared_||!current(gesture,Intent::Choose)||task_->view().phase!=Phase::Select)return;
    target_.clear(juce::dontSendNotification);targets_.clear();const int id=origin_.getSelectedId();
    if(id<1||static_cast<std::size_t>(id)>origins_.size())return;
    try{targets_=f(allowedChoices(task_->retainedDefinition(),origins_[static_cast<std::size_t>(id-1)]),"nearest_target_contacts").array();
        for(std::size_t n=0;n<targets_.size();++n)target_.addItem(ju(contact(targets_[n],true)),static_cast<int>(n+1));
    }catch(const Error&){message_="Choose a valid tension contact first.";render();}
}
V RecipeTaskView::choiceReport() const {
    if(stroke_.getSelectedId()!=1&&stroke_.getSelectedId()!=2)throw Error("EXPLICIT_START_REQUIRED");
    const auto& def=task_->retainedDefinition();O request{{"package_key",def.sourceKey()},{"contract_sha256",def.contractSha256()},{"start_stroke",stroke_.getSelectedId()==1?"D":"U"}};
    if(def.recipe()==Recipe::RecoveryPair){const int a=origin_.getSelectedId(),b=target_.getSelectedId();
        if(a<1||b<1||static_cast<std::size_t>(a)>origins_.size()||static_cast<std::size_t>(b)>targets_.size())throw Error("EXPLICIT_CONTACT_REQUIRED");
        request.emplace("source_contact",origins_[static_cast<std::size_t>(a-1)]);request.emplace("target_contact",targets_[static_cast<std::size_t>(b-1)]);request.emplace("rest_of_bar_plan",plan_.getText().toStdString());}
    return request;
}
V RecipeTaskView::stepReport() const {
    const auto expected=task_->expectedReport();O report{{"step",f(expected,"step")},{"response","acknowledged"}};
    for(const auto& field:reports_){
        if(field.toggle)report.emplace(field.key,field.toggle->getToggleState());
        else if(field.text){if(field.expected.isArray()){V::Array values;for(const auto& word:juce::StringArray::fromTokens(field.text->getText(),";",""))values.emplace_back(word.trim().toStdString());report.emplace(field.key,std::move(values));}
            else report.emplace(field.key,field.text->getText().toStdString());}
        else report.emplace(field.key,field.expected); // Labeled fixed source count; never a learner boolean/name.
    }return report;
}
void RecipeTaskView::command(Intent intent, const RecipeGesture& gesture, bool unknown) {
    if(draftBusy_||navigationPrepared_||!current(gesture,intent))return;
    try{
        V payload=O{};
        if(intent==Intent::Choose)payload=choiceReport();
        else if(intent==Intent::Report)payload=stepReport();
        else if(intent==Intent::Retry||intent==Intent::Stop)payload=O{{"step",V::fromInteger(static_cast<std::int64_t>(task_->view().step.value_or(0)))},{"response",intent==Intent::Stop?"stopped":"needs_retry"}};
        else if(intent==Intent::Release)payload=O{{"released_completely_reported",releaseReport_.getToggleState()}};
        retainFields();task_->apply(*gesture.owner,payload);
        if(unknown)notes_.push_back("You reported uncertainty at "+phaseName(task_->history().back().before)+"; this requested a manual retry. It is not an observed failure.");
        if(intent==Intent::Again){clearChoices();populateOrigins();}
        message_=unknown?"You reported uncertainty. Physically release before deciding on another pass.":"Your manual report was recorded. No performance was measured.";
        render();
    }catch(const Error& error){
        if(error.code=="EXPLICIT_START_REQUIRED")message_="Choose D or U explicitly first.";
        else if(error.code=="EXPLICIT_CONTACT_REQUIRED")message_="Choose the tension contact and a nearest target explicitly.";
        else if(error.code=="EXPLICIT_REMAINDER_PLAN")message_="Enter your own nonblank remainder plan, 1–500 characters.";
        else if(error.code=="EXPLICIT_RELEASE_REQUIRED")message_="Check the physical release report only after releasing completely.";
        else message_="Your report does not match the displayed source names or required fields. Review it, or request a manual retry.";
        render();
    }
}
bool RecipeTaskView::prepareForNavigation(){
    if(draftBusy_)return false;
    if(navigationPrepared_)return true;
    const auto savedFields=rawFields();retainFields();
    if(task_){const auto state=task_->view();
        if(state.phase==Phase::Steps){task_->apply(task_->capture(Intent::Navigate),O{});message_="Physically release completely and confirm release before leaving.";render();return false;}
        if(state.phase==Phase::Release){message_="Physically release completely and confirm release before leaving.";render();return false;}
        if(!task_->fenceInactiveForNavigation())return false;
    }
    ++generation_;navigationPrepared_=true;message_.clear();render();if(task_)restoreFields(savedFields);return true;
}
void RecipeTaskView::resumeAfterNavigation(){if(!navigationPrepared_)return;++generation_;navigationPrepared_=false;message_="Returned to the retained manual task. Earlier reports remain in history.";render();}
void RecipeTaskView::navigation(const RecipeGesture& gesture, bool settings){
    if(task_&&!current(gesture,Intent::Navigate))return;
    if(!prepareForNavigation())return;
    auto& callback=settings?onSettings:onBack;
    if(callback&&!callback()){message_="The requested navigation is still pending. Try the navigation button again, or return to this retained task.";render();}
}
std::vector<HistoryEvent> RecipeTaskView::retainedHistory() const {auto out=archived_;if(task_){auto now=task_->history();out.insert(out.end(),now.begin(),now.end());}return out;}
std::string RecipeTaskView::sourceText() const {
    if(!task_)return "Open a verified manual task to see its source instructions.";
    const auto& def=task_->retainedDefinition();const auto& c=def.retainedContract();std::ostringstream out;
    out<<"Level 68 • "<<(def.recipe()==Recipe::CallAnswer?"Module I, ":"Module K, ")<<def.sourceIdentity().substr(def.sourceIdentity().rfind('/')+1)<<"\n";
    for(const auto& item:f(def.retainedSourceContext(),"context_tasks").array())out<<text(item,"instruction")<<"\n";
    if(def.recipe()==Recipe::CallAnswer){const auto& rules=f(c,"source_rules");out<<text(rules,"exact_variation")<<"\n"<<text(f(rules,"safety"),"exact_text")<<"\n\nPrinted contacts in order (source positions and harmonic degrees):\n";
        for(const auto& item:f(c,"ordered_contacts").array())out<<integer(f(item,"order"))<<". "<<contact(item,false)<<"\n";
        out<<"CAL is the minor call; ANS is the dominant answer; >A is the existing final A.\nChosen alternating D/U picking is an implementation choice. The gap has no attack.\n";
    }else{out<<"Printed pair: "<<text(c,"printed_label")<<"\nPrinted roles: "<<text(c,"printed_roles")<<"\nChord context: "<<text(c,"chord_context")<<"; destination context: "<<text(c,"destination_harmonic_context")<<"\n";
        out<<text(c,"source_target_naming_rule")<<"\n"<<text(f(c,"source_safety"),"exact_text")<<"\n";
        if(const auto* borrowed=c.find("borrowed_G_natural_scope");borrowed&&!borrowed->null())out<<borrowed->string()<<"\n";
        out<<"The source prints two pitches. Their octave, string and fret are not printed. Your menus and remainder plan are explicit choices.\nThe nearest menu uses a provisional minimum pitch-distance interpretation in standard tuning, frets 0–24; it cannot certify physical security.\nAlternating D/U picking is chosen, not printed. No remainder notes or attacks are generated.\n";
    }
    out<<"Source timing, tempo and fixed fingers are not supplied. Count manually; there is no scheduled pulse or audio.\nThese are manual reports, not observed playing, hearing, safety certification or credit.";return out.str();
}
std::string RecipeTaskView::actionText() const {
    if(!task_)return "No current manual action.";
    const auto state=task_->view();if(state.phase==Phase::Select)return task_->retainedDefinition().recipe()==Recipe::CallAnswer?
      "Read the complete source context. Choose your first D/U pick explicitly. All naming fields start blank and physical reports unchecked.":
      "Read the complete source context. Choose D/U, an origin, a nearest target and your own remainder plan. Contacts and the remainder are your choices, not printed facts.";
    if(state.phase==Phase::Release)return "Release the current notes or shape completely. Check the physical release report only when it is true, then confirm. Back, settings and a fresh pass remain gated by release.";
    if(state.phase==Phase::Closed)return outcome(state.outcome)+". No performance or credit claim was made. A fresh pass clears choices and live reports while preserving history.";
    const auto currentStep=task_->currentStep();const auto& step=*currentStep;const auto n=state.step.value_or(0);std::ostringstream out;
    static const char* call[]={"Name the A-minor call and E-dominant answer resolving to A; prepare safely.","Play the complete printed call, then answer.","Play the eight-contact variation call.","Leave two source beats of silence. Keep the internal bar count running; make no attack. The source beat has no supplied numeric duration.","Play the eight-contact variation answer, ending on the existing final A. Add no final A attack.","Release and report the phrase distinction, rhythmic identity, counted gap, final A and safety."};
    static const char* recovery[]={"Name the chord, tension, target and roles before the tension. Prepare the existing bar/pulse and safe chosen contacts.","Play your chosen origin pitch.","Move to your chosen nearest named target while preserving the pulse.","Simplify the rest of the existing bar using your own explicit plan.","Release and report pulse, secure target, heard destination, simplification and safety."};
    out<<"Step "<<n<<" of "<<task_->retainedDefinition().reports().size()<<": "<<(task_->retainedDefinition().recipe()==Recipe::CallAnswer?call[n-1]:recovery[n-1])<<"\n";
    if(const auto* contacts=step.find("selected_contacts"))for(const auto& item:contacts->array())out<<contact(item,false)<<"\n";
    if(const auto* chosen=step.find("chosen_contact"))out<<contact(*chosen,true)<<"\n";
    if(const auto* plan=step.find("rest_of_bar_plan"))out<<"Your chosen remainder plan: "<<plan->string()<<"\nNo source notes, attacks or timing are inferred from this text.\n";
    return out.str();
}
std::string RecipeTaskView::historyText() const {
    std::ostringstream out;const auto history=retainedHistory();out<<"Manual history: "<<history.size()<<" owned interactions.\n";
    for(const auto& event:history){
        const auto& def=definition(event.token.sourceKey);
        out<<(def.recipe()==Recipe::CallAnswer?"Module I "+def.sourceIdentity().substr(def.sourceIdentity().rfind('/')+1):"Module K "+text(def.retainedContract(),"printed_label"))<<", pass "<<event.token.pass<<": ";
        out<<phaseName(event.before)<<" → "<<phaseName(event.after)<<"; ";
        if(event.token.intent==Intent::Choose){
            out<<"Explicit first pick: "<<text(event.reported,"start_stroke")<<" (chosen alternation)";
            if(const auto* origin=event.reported.find("source_contact"))out<<"; origin "<<contact(*origin,true)<<"; target "<<contact(f(event.reported,"target_contact"),true)<<"; chosen remainder plan: "<<text(event.reported,"rest_of_bar_plan");
        }
        else if(event.token.intent==Intent::Navigate)out<<"Navigation boundary recorded";
        else if(event.token.intent==Intent::Again||event.token.intent==Intent::Reopen)out<<"Fresh pass requested";
        else for(const auto& item:event.reported.object()){if(item.first=="step"||item.first=="response")continue;out<<label(item.first)<<": "<<humanValue(item.second)<<"; ";}
        if(const auto* response=event.reported.find("response");response&&response->string()!="acknowledged")out<<(response->string()=="stopped"?"Manual stop":"Manual retry");
        if(event.diagnosis){out<<". Manual diagnosis: ";if(const auto* negative=event.diagnosis->find("false_boolean_fields")){for(const auto& name:negative->array())out<<label(name.string())<<" was reported false; ";}else out<<"release before continuing";out<<"not an observed failure";}out<<"\n";
    }
    for(const auto& note:notes_)out<<note<<"\n";return out.str();
}
void RecipeTaskView::rebuildInputs(){
    const auto state=task_?task_->view():View{};std::string key=task_?std::to_string(task_->capture(Intent::Report).instance)+"/"+std::to_string(task_->pass())+"/"+std::to_string(static_cast<int>(state.phase))+"/"+std::to_string(state.step.value_or(0)):"empty";
    if(key==renderedInputs_)return;renderedInputs_=key;reports_.clear();releaseReport_.setToggleState(false,juce::dontSendNotification);inputViewport_.setViewPosition(0,0);
    if(task_&&state.phase==Phase::Steps){const auto expected=task_->expectedReport();for(const auto& item:expected.object()){
        if(item.first=="step"||item.first=="response")continue;ReportField field;field.key=item.first;field.expected=item.second;
        if(item.second.isBool()){field.toggle=std::make_unique<juce::ToggleButton>(ju(label(item.first)));field.toggle->setToggleState(false,juce::dontSendNotification);field.toggle->setComponentID("recipe-report-"+ju(item.first));field.toggle->setTitle(ju(label(item.first)));inputBody_.addAndMakeVisible(*field.toggle);}
        else{field.label=std::make_unique<juce::Label>();field.label->setText(ju(label(item.first)+(item.second.isNumber()?": "+integer(item.second):"")),juce::dontSendNotification);inputBody_.addAndMakeVisible(*field.label);
            if(!item.second.isNumber()){field.text=std::make_unique<juce::TextEditor>();field.text->setComponentID("recipe-report-"+ju(item.first));field.text->setTitle(ju(label(item.first)));field.text->setText({},false);field.text->setMultiLine(false);inputBody_.addAndMakeVisible(*field.text);}}
        reports_.push_back(std::move(field));}}
}
void RecipeTaskView::render(){
    const bool has=bool(task_);const auto state=has?task_->view():View{};rebuildInputs();
    const bool choose=has&&state.phase==Phase::Select,recovery=has&&task_->retainedDefinition().recipe()==Recipe::RecoveryPair;
    heading_.setText(has?(recovery?"Manual recovery pair":"Manual minor call / dominant answer"):"Manual exercises",juce::dontSendNotification);phase_.setText(ju(has?phaseName(state):"No task open"),juce::dontSendNotification);
    const auto source=sourceText();if(source_.getText()!=ju(source))manual_text::setReadOnlyText(source_,ju(source));const auto action=actionText();if(action_.getText()!=ju(action))manual_text::setReadOnlyText(action_,ju(action));manual_text::setReadOnlyText(history_,ju(historyText()));
    status_.setText(ju(message_+" No recording, Attempt, mastery or curriculum credit."),juce::dontSendNotification);status_.setTitle(status_.getText());
    for(auto* c:std::initializer_list<juce::Component*>{&strokeLabel_,&stroke_})c->setVisible(choose);
    for(auto* c:std::initializer_list<juce::Component*>{&originLabel_,&origin_,&targetLabel_,&target_,&planLabel_,&plan_})c->setVisible(choose&&recovery);
    releaseReport_.setVisible(has&&state.phase==Phase::Release);releaseReport_.setEnabled(!navigationPrepared_);
    choose_.setVisible(choose);report_.setVisible(has&&state.phase==Phase::Steps);retry_.setVisible(report_.isVisible());stop_.setVisible(report_.isVisible());unknown_.setVisible(report_.isVisible());
    release_.setVisible(has&&state.phase==Phase::Release);again_.setVisible(has&&state.phase==Phase::Closed);
    for(auto* c:std::initializer_list<juce::Component*>{&choose_,&report_,&retry_,&stop_,&unknown_,&release_,&again_,&stroke_,&origin_,&target_,&plan_})c->setEnabled(!navigationPrepared_);
    juce::Component::SafePointer<RecipeTaskView> safe(this);const auto gesture=capture(Intent::Choose);origin_.onChange=[safe,gesture]{if(safe)safe->updateTargets(gesture);};
    resized();
}
void RecipeTaskView::paint(juce::Graphics& graphics){graphics.fillAll(appearance::colour(0xff10212c));}
void RecipeTaskView::resized(){
    auto area=getLocalBounds().reduced(12);draftPanel_.setBounds(area.removeFromBottom(90));heading_.setBounds(area.removeFromTop(30));phase_.setBounds(area.removeFromTop(24));
    auto bottom=area.removeFromBottom(68);auto first=bottom.removeFromTop(32);int x=first.getX();
    for(auto* button:std::initializer_list<RecipeTaskButton*>{&choose_,&report_,&retry_,&stop_,&unknown_,&release_,&again_})if(button->isVisible()){const int w=button==&choose_||button==&release_?220:button==&again_?190:button==&report_?165:135;button->setBounds(x,first.getY(),w,30);x+=w+6;}
    auto navigation=bottom.removeFromTop(32);back_.setBounds(navigation.removeFromLeft(160));settings_.setBounds(navigation.removeFromLeft(130));worksheet_.setBounds(navigation.removeFromLeft(210));
    status_.setBounds(area.removeFromBottom(manual_text::labelHeight(status_,area.getWidth(),46)));history_.setBounds(area.removeFromBottom(74));source_.setBounds(area.removeFromTop(140));area.removeFromTop(4);action_.setBounds(area.removeFromTop(84));area.removeFromTop(4);inputViewport_.setBounds(area);
    const int width=std::max(1,inputViewport_.getWidth()-16);int y=0;const auto state=task_?task_->view():View{};
    auto pair=[&](juce::Label& l,juce::Component& c,int height=30){const int labelWidth=std::min(340,std::max(1,width/2));height=manual_text::labelHeight(l,labelWidth,height);l.setBounds(0,y,labelWidth,height);c.setTitle(l.getText());c.setBounds(labelWidth+4,y,std::max(1,width-labelWidth-4),height);y+=height+4;};
    if(task_&&state.phase==Phase::Select){pair(strokeLabel_,stroke_);if(task_->retainedDefinition().recipe()==Recipe::RecoveryPair){pair(originLabel_,origin_);pair(targetLabel_,target_);planLabel_.setBounds(0,y,width,24);y+=24;plan_.setBounds(0,y,width,56);y+=60;}}
    for(auto& field:reports_){if(field.toggle){field.toggle->setBounds(0,y,width,30);y+=34;}else if(field.text)pair(*field.label,*field.text);else{field.label->setBounds(0,y,width,28);y+=32;}}
    if(releaseReport_.isVisible()){releaseReport_.setBounds(0,y,width,32);y+=36;}inputBody_.setSize(width,std::max(y,inputViewport_.getHeight()));
}

json::Value RecipeTaskView::rawFields()const{
    V::Array fields;for(const auto&f:reports_)fields.emplace_back(O{{"key",f.key},{"schema",content::sha256(json::stringify(f.expected))},{"text",f.text?V(f.text->getText().toStdString()):V()},{"toggle",f.toggle?V(f.toggle->getToggleState()):V()}});
    return O{{"format","recipe-raw-fields-v1"},{"key",task_?task_->retainedDefinition().sourceKey():std::string{}},{"phase",V::fromInteger(task_?static_cast<int>(task_->view().phase):0)},{"step",task_&&task_->view().step?V::fromInteger(static_cast<std::int64_t>(*task_->view().step)):V()},{"stroke",V::fromInteger(stroke_.getSelectedId())},{"origin",V::fromInteger(origin_.getSelectedId())},{"target",V::fromInteger(target_.getSelectedId())},{"plan",plan_.getText().toStdString()},{"release",releaseReport_.getToggleState()},{"reports",fields}};
}
void RecipeTaskView::restoreFields(const V&v){
    const auto&d=v.object();if(d.size()!=10||f(v,"format")!=V("recipe-raw-fields-v1")||!task_||f(v,"key")!=V(task_->retainedDefinition().sourceKey())||f(v,"phase")!=V::fromInteger(static_cast<int>(task_->view().phase))||f(v,"step")!=(task_->view().step?V::fromInteger(static_cast<std::int64_t>(*task_->view().step)):V()))throw std::runtime_error("Saved recipe fields differ from current source/state");
    auto id=[](const V&v,int maximum){std::int64_t n{};if(!v.integer(n)||n<0||n>maximum)throw std::runtime_error("Saved recipe menu differs");return static_cast<int>(n);};const auto stroke=id(f(v,"stroke"),2),origin=id(f(v,"origin"),static_cast<int>(origins_.size()));
    std::vector<V> targets;if(origin)targets=f(allowedChoices(task_->retainedDefinition(),origins_.at(static_cast<std::size_t>(origin-1))),"nearest_target_contacts").array();const auto target=id(f(v,"target"),static_cast<int>(targets.size()));const auto plan=f(v,"plan").string();const auto released=f(v,"release").boolean();const auto&fields=f(v,"reports").array();if(fields.size()!=reports_.size())throw std::runtime_error("Saved recipe report shape differs");
    for(std::size_t n=0;n<fields.size();++n){const auto&r=fields[n];const auto&field=reports_[n];if(r.object().size()!=4||f(r,"key")!=V(field.key)||f(r,"schema")!=V(content::sha256(json::stringify(field.expected)))||(!field.text&&!f(r,"text").null())||(!field.toggle&&!f(r,"toggle").null()))throw std::runtime_error("Saved recipe report schema differs");if(field.text)(void)f(r,"text").string();if(field.toggle)(void)f(r,"toggle").boolean();}
    stroke_.setSelectedId(stroke,juce::dontSendNotification);origin_.setSelectedId(origin,juce::dontSendNotification);targets_=std::move(targets);target_.clear(juce::dontSendNotification);for(std::size_t n=0;n<targets_.size();++n)target_.addItem(ju(contact(targets_[n],true)),static_cast<int>(n+1));target_.setSelectedId(target,juce::dontSendNotification);plan_.setText(ju(plan),false);releaseReport_.setToggleState(released,juce::dontSendNotification);
    for(std::size_t n=0;n<fields.size();++n){auto&field=reports_[n];if(field.text)field.text->setText(ju(f(fields[n],"text").string()),false);if(field.toggle)field.toggle->setToggleState(f(fields[n],"toggle").boolean(),juce::dontSendNotification);}
}
void RecipeTaskView::retainFields(){if(!task_)return;const V record=O{{"key",task_->retainedDefinition().sourceKey()},{"revision",V::fromInteger(static_cast<std::int64_t>(task_->revision()))},{"fields",rawFields()}};if(earlierFields_.empty()||earlierFields_.back()!=record){if(earlierFields_.size()>=100000)throw std::runtime_error("Retained recipe field capacity");earlierFields_.push_back(record);}}
std::string RecipeTaskView::workspaceStamp()const{V::Array owners;for(const auto&o:archivedOwners_)owners.emplace_back(O{{"key",o->retainedDefinition().sourceKey()},{"revision",V::fromInteger(static_cast<std::int64_t>(o->revision()))}});return content::sha256(json::stringify(O{{"fields",rawFields()},{"revision",V::fromInteger(task_?static_cast<std::int64_t>(task_->revision()):0)},{"archives",owners},{"earlier",earlierFields_}}));}
std::function<std::string()> RecipeTaskView::captureWorkspace(){if(!task_)throw std::runtime_error("No recipe owner");auto owner=task_;auto archives=archivedOwners_;auto fields=rawFields();auto earlier=earlierFields_;auto notes=notes_;return [owner,archives,fields,earlier,notes]{V::Array old,messages;for(const auto&o:archives)old.emplace_back(o->continuation());for(const auto&s:notes)messages.emplace_back(s);return storage::canonical(O{{"format","recipe-workspace-private-v1"},{"owner",owner->continuation()},{"archives",old},{"fields",fields},{"earlier",earlier},{"notes",messages}});};}
RecipeTaskView::Workspace RecipeTaskView::decodeWorkspace(const SourceDraftPanel::Loaded&l){
    namespace D=storage::manual_drafts;D::require(l.receipt.status==storage::Status::Confirmed,"Recipe draft not confirmed");json::Limits limits;limits.bytes=D::maxBytes;limits.stringBytes=D::maxBytes;limits.depth=96;limits.values=2000000;const auto v=json::parse(l.payload,limits);D::require(v.object().size()==6&&f(v,"format")==V("recipe-workspace-private-v1")&&storage::canonical(v)==l.payload,"Recipe workspace shape/version");Workspace w;const auto&def=definition(l.sourceKey);D::require(l.sourceContract==def.contractSha256(),"Recipe source contract differs");w.task=RecipeTask::restoreContinuation(def,f(v,"owner").string());D::require(w.task->revision()==static_cast<std::uint64_t>(l.watermark),"Recipe owner watermark differs");
    D::require(f(v,"archives").isArray()&&f(v,"archives").array().size()<=100000,"Recipe archive bounds");for(const auto&saved:f(v,"archives").array()){const auto root=json::parse(saved.string(),limits);const auto key=f(f(root,"body"),"source_key").string();w.archives.push_back(RecipeTask::restoreContinuation(definition(key),saved.string()));}w.fields=f(v,"fields");w.earlier=f(v,"earlier");D::require(w.archives.size()<=100000&&w.earlier.isArray()&&w.earlier.array().size()<=100000,"Recipe archive bounds");for(const auto&message:f(v,"notes").array())w.notes.push_back(message.string());return w;
}
bool RecipeTaskView::installWorkspace(Workspace w,const std::string&expected){
    if(!w.task||workspaceStamp()!=expected)return false;
    // Probe every live field against a separate current-source component before
    // replacing the retained owner. No native command is delivered by probing.
    try{RecipeTaskView probe;probe.task_=w.task;probe.populateOrigins();probe.render();probe.restoreFields(w.fields);}catch(const std::exception&){return false;}
    auto previous=task_;auto archives=archivedOwners_;auto earlier=earlierFields_;auto notes=notes_;auto raw=rawFields();const auto prepared=navigationPrepared_;
    try{task_=std::move(w.task);archivedOwners_=std::move(w.archives);earlierFields_=w.earlier.array();notes_=std::move(w.notes);archived_.clear();for(const auto&o:archivedOwners_){const auto h=o->history();archived_.insert(archived_.end(),h.begin(),h.end());}++generation_;navigationPrepared_=false;renderedInputs_.clear();populateOrigins();render();restoreFields(w.fields);return true;}
    catch(...){task_=std::move(previous);archivedOwners_=std::move(archives);earlierFields_=std::move(earlier);notes_=std::move(notes);archived_.clear();for(const auto&o:archivedOwners_){const auto h=o->history();archived_.insert(archived_.end(),h.begin(),h.end());}navigationPrepared_=prepared;renderedInputs_.clear();populateOrigins();render();if(task_)restoreFields(raw);return false;}
}
void RecipeTaskView::setDraftBusy(bool b){draftBusy_=b;++generation_;for(auto*c:getChildren())if(c!=&draftPanel_)c->setEnabled(!b);if(!b)render();}

std::string RecipeTaskView::learnerHistoryExport(){
    if(draftBusy_||!task_)throw std::runtime_error("Learner worksheet unavailable during a draft job or without an owner");retainFields();V::Array rows;
    auto append=[&](const std::shared_ptr<RecipeTask>&owner){V::Array events;for(const auto&e:owner->history())events.emplace_back(O{{"intent",V::fromInteger(static_cast<int>(e.token.intent))},{"pass",V::fromInteger(static_cast<std::int64_t>(e.token.pass))},{"revision",V::fromInteger(static_cast<std::int64_t>(e.token.revision))},{"report",e.reported},{"before_phase",V::fromInteger(static_cast<int>(e.before.phase))},{"after_phase",V::fromInteger(static_cast<int>(e.after.phase))},{"diagnosis",e.diagnosis?*e.diagnosis:V()},{"observed_performance",false},{"grants_credit",false}});const auto&d=owner->retainedDefinition();const auto state=owner->view();rows.emplace_back(O{{"source_key",d.sourceKey()},{"source_identity",d.sourceIdentity()},{"contract_sha256",d.contractSha256()},{"phase",V::fromInteger(static_cast<int>(state.phase))},{"manual_release_due",state.needsManualRelease},{"history",events}});};for(const auto&o:archivedOwners_)append(o);append(task_);
    const auto a=origin_.getSelectedId(),b=target_.getSelectedId();const V choices=O{{"first_pick",stroke_.getSelectedId()==1?V("D"):stroke_.getSelectedId()==2?V("U"):V()},{"chosen_origin",a>0&&static_cast<std::size_t>(a)<=origins_.size()?origins_[static_cast<std::size_t>(a-1)]:V()},{"chosen_target",b>0&&static_cast<std::size_t>(b)<=targets_.size()?targets_[static_cast<std::size_t>(b-1)]:V()},{"remainder_plan",plan_.getText().toStdString()}};
    return storage::canonical(O{{"format","fathom-recipe-learner-worksheet-v1"},{"owners",rows},{"unsubmitted_current_fields",rawFields()},{"unsubmitted_current_choices",choices},{"earlier_unsubmitted_field_references",earlierFields_},{"observed_performance",false},{"grants_credit",false},{"notice","Manual declarations only. Unsubmitted fields are separate from native report history. Earlier drafts are references, not current reports, measured playing, mastery or user acceptance. Private replay bytes and source-player records are excluded."}});
}
bool RecipeTaskView::copyLearnerHistory(){if(draftBusy_)return false;try{const auto bytes=learnerHistoryExport();if(onCopyLearnerHistory)onCopyLearnerHistory(bytes);else{juce::SystemClipboard::copyTextToClipboard(ju(bytes));if(juce::SystemClipboard::getTextFromClipboard().toStdString()!=bytes)throw std::runtime_error("Clipboard readback differs");}message_="Learner worksheet copied. Unsubmitted fields remain separate from recorded reports.";render();return true;}catch(const std::exception&){message_="Learner worksheet was not copied. Current work and original reports are unchanged.";render();return false;}}
} // namespace fathom::desktop
