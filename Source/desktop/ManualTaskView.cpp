#include "desktop/Appearance.hpp"
#include "desktop/ManualTaskView.hpp"
#include "desktop/TypedManualForm.hpp"
#include <sstream>

namespace fathom::desktop {
namespace {
juce::String ju(const std::string& s){return juce::String::fromUTF8(s.c_str());}
std::string lines(const std::vector<std::string>& v){std::ostringstream out;for(const auto& x:v)out<<x<<'\n';return out.str();}
}
ManualTaskView::ManualTaskView(){
    setComponentID("manual-task-view");
    heading_.setText("Manual exercise",juce::dontSendNotification);heading_.setComponentID("manual-task-heading");
    source_.setComponentID("manual-task-source");phase_.setComponentID("manual-task-phase");
    action_.setComponentID("manual-task-action");release_.setComponentID("manual-task-release");
    status_.setComponentID("manual-task-status");
    bpmLabel_.setText(ju("Optional guide tempo: 20–300 BPM"),juce::dontSendNotification);
    bpmLabel_.setComponentID("manual-task-bpm-label");
    bpm_.setComponentID("manual-task-bpm");bpm_.setTitle("Enter an explicit quarter-note tempo20 to300; no source tempo is supplied.");
    bpm_.setMultiLine(false);bpm_.setText({},false);
    manual_text::configureReadOnly(setup_,"manual-task-setup","Instructions: read before Ready");
    setupAx_.setComponentID("manual-task-setup-accessible");
    for(auto* c:std::initializer_list<juce::Component*>{&heading_,&source_,&phase_,&action_,&release_,&status_,&bpmLabel_,&bpm_,&setup_,&setupAx_})addAndMakeVisible(*c);
    // The complete instruction text is now exposed by its scrolling native
    // text editor. Keep the old mirror for clients holding its identity, but
    // do not paint a second clipped copy or duplicate it in accessibility.
    setupAx_.setVisible(false);setupAx_.setAccessible(false);
    wire(sourceOrder_,tasks::IntentKind::SourceOrder,"Source order — manual reports");
    wire(evenPulse_,tasks::IntentKind::EvenPulse,"Fathom even-pulse guide");
    wire(ready_,tasks::IntentKind::Ready,"Ready after setup");
    wire(ack_,tasks::IntentKind::Acknowledge,"I did the displayed step");
    wire(retry_,tasks::IntentKind::Retry,"Request retry");
    wire(cancel_,tasks::IntentKind::Cancel,"Cancel current pass");
    wire(releaseAck_,tasks::IntentKind::Release,"I physically released the shape");
    wire(again_,tasks::IntentKind::Again,"Begin another pass");
    wire(unknown_,tasks::IntentKind::Unknown,"I'm not sure");
    const char* labels[]={"Root","Quality (major/minor)","Inversion","Bass degree","Notes, low to high","Degrees, low to high"};
    for(std::size_t n=0;n<reportFields_.size();++n){
        reportLabels_[n].setText(labels[n],juce::dontSendNotification);
        reportFields_[n].setComponentID("manual-task-report-"+juce::String(static_cast<int>(n)));
        reportFields_[n].setTitle(labels[n]);reportFields_[n].setMultiLine(false);
        addAndMakeVisible(reportLabels_[n]);addAndMakeVisible(reportFields_[n]);
    }
    const char* reports[]={"I looked, named, formed and released silently","I used minimum pressure","I muted outside strings","I followed the source setup"};
    for(std::size_t n=0;n<setupReports_.size();++n){setupReports_[n].setButtonText(reports[n]);setupReports_[n].setTitle(reports[n]);addAndMakeVisible(setupReports_[n]);}
    back_.setComponentID("manual-task-back");back_.setTitle("Leave this task; invalidate pending input, stop the shared clock and return to Learn without saving an Attempt.");
    back_.onClick=[this]{if(!prepareForNavigation())return;if(onBack&&!onBack()){message_="The return to Learn is still pending. Try Back again after it resolves.";render();}};
    audio_.setComponentID("manual-task-audio-settings");audio_.setTitle("Prepare the shared metronome output for an optional even-pulse guide.");
    audio_.onClick=[this]{if(draftBusy_||navigationPrepared_)return;if(onAudioSettings)onAudioSettings();};
    addAndMakeVisible(back_);addAndMakeVisible(audio_);
    addAndMakeVisible(draftPanel_);worksheet_.setComponentID("manual-copy-worksheet");worksheet_.onClick=[this]{copyLearnerHistory();};addAndMakeVisible(worksheet_);
    draftPanel_.hooks.key=[this]{return adapter_?adapter_->definition().sourceKey():std::string{};};draftPanel_.hooks.stamp=[this]{return workspaceStamp();};draftPanel_.hooks.freeze=[this](bool b){setDraftBusy(b);};draftPanel_.hooks.gate=[this]{return !pulsePending_&&!startPending_&&(!adapter_||!adapter_->clockArmed())&&onDraftSaveGate&&onDraftSaveGate();};draftPanel_.hooks.prepareNavigation=[this]{return prepareForNavigation();};draftPanel_.hooks.reopenStore=[this]{return onDraftStoreReopen&&onDraftStoreReopen();};draftPanel_.hooks.loadRefused=[this]{resumeAfterNavigation();};
    draftPanel_.hooks.capture=[this]{if(!adapter_||pulsePending_||startPending_||adapter_->clockArmed())throw std::runtime_error("Resolve actual pulse before capture");SourceDraftPanel::Capture c;c.key=adapter_->definition().sourceKey();c.contract=adapter_->definition().policySha256();c.stamp=workspaceStamp();c.watermark=static_cast<std::int64_t>(adapter_->revision());c.bytes=captureWorkspace();return c;};draftPanel_.hooks.decoder=[](){return std::function<std::shared_ptr<void>(const SourceDraftPanel::Loaded&)>([](const auto&l){return std::make_shared<Workspace>(decodeWorkspace(l));});};draftPanel_.hooks.install=[this](std::shared_ptr<void>w,const std::string&stamp){return installWorkspace(std::move(*std::static_pointer_cast<Workspace>(w)),stamp);};
    render();
}
void ManualTaskView::setPresentationLevel(presentation::Level level){
    presentation::validateLevel(level);if(level==presentationLevel_)return;
    presentationLevel_=level;render(); // display only; no action/input/clock mutation
}
void ManualTaskView::wire(ManualTaskButton& button,tasks::IntentKind kind,const char* label){
    button.setButtonText(ju(label));button.setComponentID("manual-task-"+ju(label).toLowerCase().replaceCharacter(' ','-'));
    button.setTitle(ju(label));button.setWantsKeyboardFocus(true);
    button.capture=[this,kind]{return ManualTaskGesture{adapter_?adapter_->capture(kind):tasks::IntentToken{},generation_};};
    button.deliver=[this,kind](const ManualTaskGesture& token){command(kind,token);};
    addAndMakeVisible(button);
}
bool ManualTaskView::open(const tasks::Definition& definition){
    if(draftBusy_)return false;
    if(adapter_&&adapter_->view().phase!=tasks::Phase::Choose&&adapter_->view().phase!=tasks::Phase::Closed){
        message_="Finish the current pass and physically release it before opening another task.";render();return false;
    }
    if(pulsePending_&&(!onResolvePulse||!onResolvePulse())){
        message_="Finish stopping the shared pulse before opening another task.";render();return false;
    }
    if(adapter_){retainFields();archivedOwners_.push_back(adapter_);}
    adapter_=std::make_shared<tasks::ManualTaskAdapter>(definition);++generation_;
    pulsePending_=false;startPending_=false;navigationPrepared_=false;
    for(auto& field:reportFields_)field.setText({},false);
    for(auto& control:setupReports_)control.setToggleState(false,juce::dontSendNotification);
    bpm_.setText({},false);message_.clear();render();return true;
}
void ManualTaskView::command(tasks::IntentKind kind,const ManualTaskGesture& gesture){
    if(draftBusy_||navigationPrepared_||!isEnabled()||!adapter_||gesture.generation!=generation_)return;const auto&token=gesture.owner;
    const auto previous=adapter_->view();
    std::optional<int> bpm;
    if(kind==tasks::IntentKind::EvenPulse||(kind==tasks::IntentKind::Ready&&previous.mode==tasks::Mode::FathomEvenPulse)){
        const auto value=bpm_.getText().trim();
        if(value.isEmpty()||value.length()>3||!value.containsOnly("0123456789")){
            message_=kind==tasks::IntentKind::Ready?"Current BPM is invalid; enter BPM20–300 and reselect paced mode before Ready.":"Enter an explicit integer BPM20–300 first.";
            render();return;
        }
        bpm=value.getIntValue();
    }
    std::optional<json::Value> report;
    if(adapter_->definition().reportContract()){
        const auto& contract=*adapter_->definition().reportContract();
        if(kind==tasks::IntentKind::Ready){
            auto words=[](const juce::String& text){json::Value::Array a;
                for(const auto& word:juce::StringArray::fromTokens(text.replaceCharacter(',',' ')," ","")){
                    if(!word.isEmpty())a.emplace_back(word.toStdString());
                }
                return json::Value(std::move(a));};
            report=json::Value::Object{{"root",reportFields_[0].getText().trim().toStdString()},
                {"quality",reportFields_[1].getText().trim().toStdString()},
                {"inversion",reportFields_[2].getText().trim().toStdString()},
                {"bass_degree",reportFields_[3].getText().trim().toStdString()},
                {"named_notes_low_to_high",words(reportFields_[4].getText())},
                {"named_degrees_low_to_high",words(reportFields_[5].getText())},
                {"silent_look_name_form_release_reported",setupReports_[0].getToggleState()},
                {"minimum_pressure_reported",setupReports_[1].getToggleState()},
                {"outside_strings_muted_reported",setupReports_[2].getToggleState()},
                {"source_setup_acknowledged",setupReports_[3].getToggleState()}};
        }else if(kind==tasks::IntentKind::Acknowledge&&previous.actionIndex){report=contract.actions.at(*previous.actionIndex);}
        else if(kind==tasks::IntentKind::Release){report=contract.release;}
        else if(kind==tasks::IntentKind::Unknown){report=json::Value::Object{{"response","unknown"}};}
    }
    retainFields();
    if(!adapter_->apply(token,bpm,{20,300},std::move(report))){message_=adapter_->error();render();return;}
    navigationPrepared_=false;
    if(kind==tasks::IntentKind::Again||kind==tasks::IntentKind::Reopen){
        for(auto& field:reportFields_)field.setText({},false);
        for(auto& control:setupReports_)control.setToggleState(false,juce::dontSendNotification);
    }
    message_.clear();
    if(kind==tasks::IntentKind::Ready&&previous.mode==tasks::Mode::FathomEvenPulse&&adapter_->view().phase==tasks::Phase::Cues){
        pendingBpm_=previous.selectedBpm.value_or(0);startRequestedMs_=juce::Time::getMillisecondCounter();lastStartTryMs_=startRequestedMs_-100;
        startPending_=true;message_="Preparing the observed shared audio output; no cue or credit begins until the clock starts.";
    }
    if(kind==tasks::IntentKind::Retry||kind==tasks::IntentKind::Cancel||kind==tasks::IntentKind::Reopen){startPending_=false;if(onStopPulse)onStopPulse();}
    if(message_.empty())message_="Current task state updated. This is guidance, not acoustic verification or credit.";
    render();
}
void ManualTaskView::onClock(const platform::MetronomeProgress& value){
    if(draftBusy_||!adapter_||!adapter_->clockArmed())return;
    const auto before=adapter_->view();
    if(!adapter_->progress(value))return;
    if(before.phase==tasks::Phase::Cues&&adapter_->view().phase!=tasks::Phase::Cues&&onStopPulse)onStopPulse();
    render();
}
void ManualTaskView::service(){
    draftPanel_.service();if(draftBusy_)return;
    if(startPending_&&adapter_){
        const auto now=juce::Time::getMillisecondCounter();
        if(now-startRequestedMs_>=5000){
            startPending_=false;const auto cancel=adapter_->capture(tasks::IntentKind::Cancel);adapter_->apply(cancel,std::nullopt,{20,300});
            if(onStopPulse)onStopPulse();message_="Shared audio did not become ready; release this pass, then reconnect in Audio settings.";render();
        }else if(now-lastStartTryMs_>=100){
            lastStartTryMs_=now;
            auto started=onStartPulse?onStartPulse(pendingBpm_):std::nullopt;
            if(started){
                startPending_=false;pulsePending_=true;
                if(!adapter_->armClock(started->owner,started->binding,started->sampleRate)){
                    const auto cancel=adapter_->capture(tasks::IntentKind::Cancel);adapter_->apply(cancel,std::nullopt,{20,300});
                    if(onStopPulse)onStopPulse();message_="Shared pulse binding failed; release this pass before retrying.";
                }else message_="Shared even-pulse guide running; these are Fathom-authored cues, not an acoustic or credit check.";
                render();
            }
        }
    }
    if(pulsePending_&&adapter_&&!adapter_->clockArmed()&&onResolvePulse&&onResolvePulse())pulsePending_=false;
}
void ManualTaskView::invalidateForNavigation(){if(draftBusy_)return;retainFields();++generation_;navigationPrepared_=false;startPending_=false;if(adapter_){adapter_->invalidateForNavigation();message_="The previous pass was interrupted. Complete the release boundary before another pass.";}if(onStopPulse)onStopPulse();render();}
bool ManualTaskView::prepareForNavigation(){
    if(draftBusy_)return false;
    if(navigationPrepared_)return true;
    if(adapter_&&adapter_->view().phase!=tasks::Phase::Choose&&adapter_->view().phase!=tasks::Phase::Closed){
        if(adapter_->view().phase!=tasks::Phase::Release)invalidateForNavigation();
        else{startPending_=false;if(onStopPulse)onStopPulse();}
        message_="Physically release the current shape and acknowledge release before leaving this task.";
        render();return false;
    }
    startPending_=false;if(onStopPulse)onStopPulse();
    if(pulsePending_&&(!onResolvePulse||!onResolvePulse())){
        message_="Finish stopping the shared pulse, then try leaving this task again.";render();return false;
    }
    pulsePending_=false;
    if(adapter_&&!adapter_->fenceInactiveForNavigation())return false;
    navigationPrepared_=true;++generation_;message_.clear();render();return true;
}
std::string ManualTaskView::modeName(tasks::Mode mode){switch(mode){case tasks::Mode::SourceOrder:return "Source order";case tasks::Mode::FathomEvenPulse:return "Optional Fathom even-pulse guide";default:return "Choose mode";}}
void ManualTaskView::render(){
    const bool has=bool(adapter_);
    const auto state=has?adapter_->view():tasks::View{};
    const bool typed=has&&bool(adapter_->definition().reportContract());
    for(auto& label:reportLabels_)label.setVisible(typed&&state.phase==tasks::Phase::Setup);
    for(auto& field:reportFields_)field.setVisible(typed&&state.phase==tasks::Phase::Setup);
    for(auto& control:setupReports_)control.setVisible(typed&&state.phase==tasks::Phase::Setup);
    unknown_.setVisible(typed);unknown_.setEnabled(typed&&state.phase==tasks::Phase::ManualSteps);
    source_.setText(has?ju(adapter_->definition().label()+(presentationLevel_==presentation::Level::Developer?" | "+adapter_->definition().sourceKey():std::string{})):"No manual exercise selected",juce::dontSendNotification);
    if(has){const auto& def=adapter_->definition();const auto authored=ju(lines(def.setupInstructions())+"\n"+lines(def.retainedSourceContext())+"\n"+def.pacedChoiceExplanation());manual_text::setReadOnlyText(setup_,authored);setupAx_.setText(authored,juce::dontSendNotification);setupAx_.setTitle(authored);release_.setText(ju(def.releaseInstruction()),juce::dontSendNotification);release_.setTitle(ju(def.releaseInstruction()+" User-reported release only; no acoustic verification, Attempt, mastery or credit."));}
    const auto name=modeName(state.mode);std::string phaseText=name+" | ";
    switch(state.phase){case tasks::Phase::Choose:phaseText+="Choose an explicit mode";break;case tasks::Phase::Setup:phaseText+="Read setup, then Ready";break;case tasks::Phase::ManualSteps:phaseText+="Report each printed step manually";break;case tasks::Phase::Cues:phaseText+="Follow the shared-clock visual cues";break;case tasks::Phase::Release:phaseText+="Release the shape physically, then acknowledge";break;case tasks::Phase::Closed:phaseText+="Pass closed; another pass is optional";break;}
    phase_.setText(ju(phaseText),juce::dontSendNotification);phase_.setTitle(ju(phaseText));
    if(has&&state.actionIndex&&*state.actionIndex<adapter_->definition().actions().size()){
        const auto& action=adapter_->definition().actions()[*state.actionIndex];
        action_.setText(ju("Step "+std::to_string(*state.actionIndex+1)+" of "+std::to_string(adapter_->definition().actions().size())+": "+action.label),juce::dontSendNotification);
    }else action_.setText("No current step",juce::dontSendNotification);
    action_.setTitle(action_.getText());
    std::string reportStatus;
    if(typed){reportStatus=" Report history: "+std::to_string(adapter_->history().size())+" accepted interactions in this open task.";
        if(adapter_->diagnosis())reportStatus+=" Your report differs from the source or requests retry; release before another pass.";}
    status_.setText(ju(message_+reportStatus+" No recording, Session, Attempt, mastery or curriculum credit is made by this task."),juce::dontSendNotification);
    sourceOrder_.setEnabled(has&&(state.phase==tasks::Phase::Choose||state.phase==tasks::Phase::Setup));
    evenPulse_.setEnabled(sourceOrder_.isEnabled());
    ready_.setEnabled(has&&state.phase==tasks::Phase::Setup);
    ack_.setEnabled(has&&state.phase==tasks::Phase::ManualSteps);
    retry_.setEnabled(has&&(state.phase==tasks::Phase::ManualSteps||state.phase==tasks::Phase::Cues));
    cancel_.setEnabled(has&&(state.phase==tasks::Phase::Setup||state.phase==tasks::Phase::ManualSteps||state.phase==tasks::Phase::Cues));
    releaseAck_.setEnabled(has&&state.phase==tasks::Phase::Release);
    again_.setEnabled(has&&state.phase==tasks::Phase::Closed);
    bpm_.setEnabled(has&&(state.phase==tasks::Phase::Choose||state.phase==tasks::Phase::Setup));
    release_.setVisible(has&&state.phase==tasks::Phase::Release);
    if(navigationPrepared_)for(auto*b:{&sourceOrder_,&evenPulse_,&ready_,&ack_,&retry_,&cancel_,&releaseAck_,&again_,&unknown_})b->setEnabled(false);
    if(draftBusy_)for(auto*c:getChildren())if(c!=&draftPanel_)c->setEnabled(false);
    resized();
}
void ManualTaskView::paint(juce::Graphics& g){g.fillAll(appearance::colour(0xff10212c));}
void ManualTaskView::resized(){
    auto area=getLocalBounds().reduced(16);draftPanel_.setBounds(area.removeFromBottom(90));heading_.setBounds(area.removeFromTop(30));
    source_.setBounds(area.removeFromTop(manual_text::labelHeight(source_,area.getWidth(),28)));
    phase_.setBounds(area.removeFromTop(manual_text::labelHeight(phase_,area.getWidth(),28)));
    action_.setBounds(area.removeFromTop(manual_text::labelHeight(action_,area.getWidth(),32)));
    auto top=area.removeFromTop(32);bpmLabel_.setBounds(top.removeFromLeft(std::min(300,top.getWidth()-100)));bpm_.setBounds(top.removeFromLeft(95));
    setupAx_.setBounds({});
    auto controls=area.removeFromBottom(128);
    auto row1=controls.removeFromTop(32);sourceOrder_.setBounds(row1.removeFromLeft(190));evenPulse_.setBounds(row1.removeFromLeft(190));ready_.setBounds(row1.removeFromLeft(170));
    auto row2=controls.removeFromTop(32);ack_.setBounds(row2.removeFromLeft(190));retry_.setBounds(row2.removeFromLeft(160));cancel_.setBounds(row2.removeFromLeft(160));unknown_.setBounds(row2.removeFromLeft(140));
    auto row3=controls.removeFromTop(32);releaseAck_.setBounds(row3.removeFromLeft(230));again_.setBounds(row3.removeFromLeft(180));
    auto row4=controls.removeFromTop(32);audio_.setBounds(row4.removeFromLeft(180));back_.setBounds(row4.removeFromLeft(180));worksheet_.setBounds(row4.removeFromLeft(220));
    status_.setBounds(area.removeFromBottom(manual_text::labelHeight(status_,area.getWidth(),48)));
    release_.setBounds(area.removeFromBottom(release_.isVisible()?manual_text::labelHeight(release_,area.getWidth(),42):0));
    const bool typed=adapter_&&adapter_->definition().reportContract();
    if(typed&&adapter_->view().phase==tasks::Phase::Setup){
        auto reports=area.removeFromBottom(132);
        for(std::size_t row=0;row<3;++row){auto line=reports.removeFromTop(28);auto left=line.removeFromLeft(line.getWidth()/2);
            for(std::size_t col=0;col<2;++col){const auto n=row*2+col;auto cell=col?line:left;
                reportLabels_[n].setBounds(cell.removeFromLeft(std::min(145,cell.getWidth()/2)));reportFields_[n].setBounds(cell);}}
        for(std::size_t row=0;row<2;++row){auto line=reports.removeFromTop(24);auto left=line.removeFromLeft(line.getWidth()/2);
            setupReports_[row*2].setBounds(left);setupReports_[row*2+1].setBounds(line);}
    }
    setup_.setBounds(area.reduced(0,4)); // all original instructions remain scrollable
}
namespace {
using J=json::Value;using O=J::Object;using A=J::Array;
const J& mf(const J&v,const char*k){auto*p=v.find(k);if(!p)throw std::runtime_error("Manual workspace field missing");return*p;}
std::shared_ptr<tasks::ManualTaskAdapter> restoreManual(const std::string&key,const std::string&bytes){
    try{return tasks::ManualTaskAdapter::restoreContinuation(tasks::compiledFamilyDefinition(key),bytes);}catch(const std::exception&){}
    return tasks::ManualTaskAdapter::restoreContinuation(tasks::representativeDefinition(key),bytes);
}
J manualState(const tasks::View&v){return O{{"mode",J::fromInteger(static_cast<int>(v.mode))},{"phase",J::fromInteger(static_cast<int>(v.phase))},{"outcome",J::fromInteger(static_cast<int>(v.outcome))},{"manual_release_due",v.needsManualRelease}};}
}
json::Value ManualTaskView::rawFields()const{A fields,toggles;for(const auto&f:reportFields_)fields.emplace_back(f.getText().toStdString());for(const auto&t:setupReports_)toggles.emplace_back(t.getToggleState());return O{{"format","manual-raw-fields-v1"},{"source_key",adapter_?adapter_->definition().sourceKey():std::string{}},{"policy",adapter_?adapter_->definition().policySha256():std::string{}},{"bpm_text",bpm_.getText().toStdString()},{"fields",fields},{"setup_reports",toggles}};}
void ManualTaskView::restoreFields(const J&v){if(!adapter_||v.object().size()!=6||mf(v,"format")!=J("manual-raw-fields-v1")||mf(v,"source_key")!=J(adapter_->definition().sourceKey())||mf(v,"policy")!=J(adapter_->definition().policySha256()))throw std::runtime_error("Manual source/field format differs");const auto text=mf(v,"bpm_text").string();const auto&fields=mf(v,"fields").array();const auto&t=mf(v,"setup_reports").array();if(fields.size()!=6||t.size()!=4)throw std::runtime_error("Manual field extent differs");for(const auto&f:fields)(void)f.string();for(const auto&b:t)(void)b.boolean();bpm_.setText(ju(text),false);for(std::size_t n=0;n<fields.size();++n)reportFields_[n].setText(ju(fields[n].string()),false);for(std::size_t n=0;n<t.size();++n)setupReports_[n].setToggleState(t[n].boolean(),juce::dontSendNotification);}
void ManualTaskView::retainFields(){if(!adapter_)return;const J v=O{{"source_key",adapter_->definition().sourceKey()},{"revision",J::fromInteger(static_cast<std::int64_t>(adapter_->revision()))},{"fields",rawFields()}};if(earlierFields_.empty()||earlierFields_.back()!=v){if(earlierFields_.size()>=100000)throw std::runtime_error("Manual field reference capacity");earlierFields_.push_back(v);}}
std::string ManualTaskView::workspaceStamp()const{A owners;for(const auto&o:archivedOwners_)owners.emplace_back(O{{"key",o->definition().sourceKey()},{"revision",J::fromInteger(static_cast<std::int64_t>(o->revision()))}});return content::sha256(json::stringify(O{{"fields",rawFields()},{"revision",J::fromInteger(adapter_?static_cast<std::int64_t>(adapter_->revision()):0)},{"archives",owners},{"earlier",earlierFields_}}));}
std::function<std::string()> ManualTaskView::captureWorkspace(){if(!adapter_||startPending_||pulsePending_||adapter_->clockArmed())throw std::runtime_error("Actual pulse must resolve before draft capture");auto owner=adapter_;auto archives=archivedOwners_;auto fields=rawFields();auto earlier=earlierFields_;return[owner,archives,fields,earlier]{A old;for(const auto&o:archives)old.emplace_back(O{{"key",o->definition().sourceKey()},{"owner",o->continuation()}});return storage::canonical(O{{"format","manual-workspace-private-v1"},{"source_key",owner->definition().sourceKey()},{"owner",owner->continuation()},{"archives",old},{"fields",fields},{"earlier",earlier}});};}
ManualTaskView::Workspace ManualTaskView::decodeWorkspace(const SourceDraftPanel::Loaded&l){namespace D=storage::manual_drafts;D::require(l.receipt.status==storage::Status::Confirmed,"Manual draft unconfirmed");json::Limits limits;limits.bytes=D::maxBytes;limits.stringBytes=D::maxBytes;limits.depth=96;limits.values=2000000;const auto v=json::parse(l.payload,limits);D::require(v.object().size()==6&&mf(v,"format")==J("manual-workspace-private-v1")&&storage::canonical(v)==l.payload&&mf(v,"source_key")==J(l.sourceKey),"Manual workspace binding/format");Workspace w;w.owner=restoreManual(l.sourceKey,mf(v,"owner").string());D::require(w.owner->definition().policySha256()==l.sourceContract&&l.watermark>=0&&w.owner->revision()==static_cast<std::uint64_t>(l.watermark)&&!w.owner->clockArmed(),"Manual source/watermark or bound clock differs");const auto&old=mf(v,"archives").array();D::require(old.size()<=100000,"Manual archive bounds");for(const auto&snapshot:old){D::require(snapshot.object().size()==2,"Manual archived owner shape");w.archives.push_back(restoreManual(mf(snapshot,"key").string(),mf(snapshot,"owner").string()));}w.fields=mf(v,"fields");w.earlier=mf(v,"earlier");D::require(w.earlier.isArray()&&w.earlier.array().size()<=100000,"Manual earlier-field bounds");return w;}
bool ManualTaskView::installWorkspace(Workspace w,const std::string&expected){if(!w.owner||startPending_||pulsePending_||(adapter_&&adapter_->clockArmed())||workspaceStamp()!=expected)return false;try{ManualTaskView probe;probe.adapter_=w.owner;probe.restoreFields(w.fields);}catch(const std::exception&){return false;}auto old=adapter_;auto archives=archivedOwners_;auto earlier=earlierFields_;auto fields=rawFields();const auto prepared=navigationPrepared_;try{adapter_=std::move(w.owner);archivedOwners_=std::move(w.archives);earlierFields_=w.earlier.array();navigationPrepared_=false;++generation_;render();restoreFields(w.fields);return true;}catch(...){adapter_=std::move(old);archivedOwners_=std::move(archives);earlierFields_=std::move(earlier);navigationPrepared_=prepared;render();if(adapter_)restoreFields(fields);return false;}}
void ManualTaskView::setDraftBusy(bool b){draftBusy_=b;++generation_;for(auto*c:getChildren())if(c!=&draftPanel_)c->setEnabled(!b);if(!b)render();}
std::string ManualTaskView::learnerHistoryExport(){if(draftBusy_||!adapter_)throw std::runtime_error("Manual learner worksheet unavailable");retainFields();A owners;auto append=[&](const std::shared_ptr<tasks::ManualTaskAdapter>&a){A events;for(const auto&e:a->history())events.emplace_back(O{{"intent",J::fromInteger(static_cast<int>(e.token.kind))},{"pass",J::fromInteger(static_cast<std::int64_t>(e.token.pass))},{"revision",J::fromInteger(static_cast<std::int64_t>(e.token.revision))},{"report",e.reported},{"before",manualState(e.before)},{"after",manualState(e.after)},{"diagnosis",e.diagnosis?*e.diagnosis:J()},{"observed_performance",false},{"grants_credit",false}});owners.emplace_back(O{{"source_key",a->definition().sourceKey()},{"policy_sha256",a->definition().policySha256()},{"current_state",manualState(a->view())},{"history",events}});};for(const auto&o:archivedOwners_)append(o);append(adapter_);return storage::canonical(O{{"format","fathom-manual-learner-worksheet-v1"},{"owners",owners},{"raw_editor_contents",rawFields()},{"earlier_editor_field_references",earlierFields_},{"observed_performance",false},{"grants_credit",false},{"notice","Raw editor contents may be hidden or retained from an earlier setup; they are not additional submissions. Only native history records submitted reports. Historical shared-clock guidance is not physical-audio or performance verification. Private replay/clock-binding records are excluded."}});}
bool ManualTaskView::copyLearnerHistory(){if(draftBusy_)return false;try{const auto bytes=learnerHistoryExport();if(onCopyLearnerHistory)onCopyLearnerHistory(bytes);else{juce::SystemClipboard::copyTextToClipboard(ju(bytes));if(juce::SystemClipboard::getTextFromClipboard().toStdString()!=bytes)throw std::runtime_error("Clipboard readback differs");}message_="Learner worksheet copied; partial fields remain separate from native reports.";render();return true;}catch(const std::exception&){message_="Worksheet not copied. Current work and original reports are unchanged.";render();return false;}}

}
