#include "desktop/Appearance.hpp"
#include "desktop/PracticeView.hpp"
#include "desktop/NotationLayout.hpp"
#include "desktop/LessonSelectionLabel.hpp"
#include "content/LessonTempo.hpp"
#include <algorithm>
#include "content/Canonical.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "storage/StorageEnvelope.hpp"
#include <initializer_list>
#include <utility>
namespace fathom::desktop {
namespace {
// One read-only state projection supplies both detailed and compact prerequisite text.
std::pair<std::string,std::string> startPrerequisite(output::State state,bool canStart){
 if(state==output::State::Closed)return {"Open Audio settings, choose Connect then Enable, and return here before Start.","Connect then Enable in Audio settings."};
 else if(state==output::State::Observed)return {"Open Audio settings, choose Enable, then return here before Start.","Enable in Audio settings."};
 else if(state==output::State::Ready&&canStart)return {"Choose Start selected case.","Start selected case."};
 else if(state==output::State::Ready)return {"Wait for the original Practice or Session operation to resolve before Start.","Resolve original Practice / Session before Start."};
 else if(state==output::State::Awaiting)return {"Wait for audio preparation to finish; inspect Audio settings before Start.","Wait for audio preparation before Start."};
 return {"Inspect Audio settings and resolve its retained state before Start.","Resolve Audio settings before Start."};
}

std::shared_ptr<const music::ValidatedModel> sampleModel(){
 music::Model m;m.itemId="synthetic:practice-transport";m.schemaVersion="qa1";m.contentVersion="qa1";m.syntheticFixture=true;m.proposalExample=false;m.instrument={{40,45,50,55,59,64},0};
 music::Event a;a.id="picked-E";a.span={Rational{},Rational{1}};music::Tone t;t.string=1;t.midi=40;t.fret=0;a.tones={t};
 auto b=a;b.id="held-E";b.span={Rational{1},Rational{1}};b.tones[0].attack=music::Attack::Held;b.tones[0].tieFrom=a.id;
 music::Event rest;rest.id="full-rest";rest.kind=music::Kind::Rest;rest.span={Rational{2},Rational{2}};rest.scopeStrings={1,2,3,4,5,6};
 m.events={a,b,rest};m.measures={{"synthetic:bar",Rational{},4,4,{a.id,b.id,rest.id},true}};
 auto v=music::validate(m);if(!v.model)throw std::runtime_error("Technical sample invalid");return v.model;
}
reference::Configuration programConfig(const practice::Configuration& c,const scheduler::Owner& o){reference::Configuration p;p.owner=o;p.binding=o.generation;p.sourceBinding="synthetic:practice-transport:qa1";p.rate=c.rate;p.bpm=c.bpm;p.unit=c.unit;p.cycle=c.span;p.intro=practice::countInSpan(c);return p;}
std::string practiceSourceIdentity(const lesson::Admission& admission){
 const auto& identity=admission.identity().object();const auto item=identity.at("item_id").string();const auto variant=identity.at("variant_id").string();
 std::string text=item+" / "+variant+" | Source: ";
 const auto& refs=admission.model()->source().sourceRefs;if(refs.empty())throw std::runtime_error("Admitted source has no source references.");
 for(std::size_t i=0;i<refs.size();++i){if(i)text+=", ";text+=refs[i];}
 return text + " | Content: " + identity.at("content_version").string()
     + " | Revision: " + storage::canonical(identity.at("content_revision"));
}
}
PracticeView::PracticeView(){
 presentationSelector_.setComponentID("practice-presentation");
 presentationSelector_.onChoice=[this](std::optional<presentation::Level> level){if(onPresentationChoice)onPresentationChoice(level);};
 addAndMakeVisible(presentationSelector_);

 addChildComponent(tempoButton_);tempoButton_.setComponentID("lesson-tempo");
 tempoButton_.onClick=[this]{showTempoControls(!tempoPanelOpen_);};
 addChildComponent(tempoPanel_);tempoPanel_.setComponentID("tempo-panel");
 for(auto* c:std::initializer_list<juce::Component*>{&rampDirection_,&rampStep_,&rampEvery_,&rampTarget_,&applyRamp_,&manualTempo_,&applyTempo_,&tempoHelp_})tempoPanel_.addAndMakeVisible(*c);
 rampDirection_.setComponentID("ramp-direction");rampStep_.setComponentID("ramp-step");rampEvery_.setComponentID("ramp-every");rampTarget_.setComponentID("ramp-target");manualTempo_.setComponentID("manual-tempo");
 rampDirection_.setTitle("Initial ramp direction");rampStep_.setTitle("Ramp step in BPM");rampEvery_.setTitle("Completed selected spans per step");rampTarget_.setTitle("Ramp target BPM");manualTempo_.setTitle("Manual tempo in quarter beats per minute");
 rampDirection_.addItem("Ramp Off",1);rampDirection_.addItem("Ramp Up",2);rampDirection_.addItem("Ramp Down",3);
 for(int n=1;n<=20;++n)rampStep_.addItem("Step "+juce::String(n)+" BPM",n);
 for(int n=1;n<=32;++n)rampEvery_.addItem("Every "+juce::String(n)+(n==1?" pass":" passes"),n);
 for(int n=20;n<=300;++n){rampTarget_.addItem("Target "+juce::String(n),n);manualTempo_.addItem(juce::String(n)+" BPM",n);}
 applyRamp_.onClick=[this]{const auto direction=rampDirection_.getSelectedId();
  if(direction==1)setLessonRamp({});
  else if(direction==2||direction==3)setLessonRamp(metronome::Ramp{direction==2,rampStep_.getSelectedId(),rampEvery_.getSelectedId(),rampTarget_.getSelectedId()});
 };
 applyTempo_.onClick=[this]{requestLessonTempo(manualTempo_.getSelectedId());};
 tempoHelp_.setFont(juce::FontOptions{14.0f});tempoHelp_.setJustificationType(juce::Justification::topLeft);
 tempoHelp_.setText("Optional playback aid at selected-span boundaries; source clean-loop guidance still applies. Manual changes turn ramp Off. Arrows edit selectors.",juce::dontSendNotification);
 resetTempoEditors();
 addChildComponent(setupSummary_);addChildComponent(setupButton_);addChildComponent(setupDetails_);
 setupSummary_.setFont(juce::FontOptions{14.0f});setupSummary_.setJustificationType(juce::Justification::topLeft);setupSummary_.setComponentID("setup-summary");setupDetails_.setComponentID("setup-details");
 setupDetails_.setMultiLine(true,true);setupDetails_.setReadOnly(true);setupDetails_.setScrollbarsShown(true);setupDetails_.setCaretVisible(false);
 setupButton_.onClick=[this]{showSetupDetails(!setupDetailsVisible_);};
 addChildComponent(scheduledPasses_);scheduledPasses_.setComponentID("scheduled-passes");scheduledPasses_.setTitle("Scheduled full-span passes");
 scheduledPasses_.setTooltip(juce::String::fromUTF8("Repeat the full selected span 1–32 times. Scheduled playback does not prove performed repetitions or source-task completion. Change after Again while stopped."));
 for(int passes=1;passes<=static_cast<int>(lesson::Admission::maximumScheduledPasses);++passes)scheduledPasses_.addItem(juce::String(passes)+(passes==1?" scheduled pass":" scheduled passes"),passes);
 scheduledPasses_.onChange=[this]{setLessonScheduledPasses(static_cast<std::uint64_t>(scheduledPasses_.getSelectedId()));};
 addChildComponent(beatClickButton_);beatClickButton_.setTooltip("Optional unaccented quarter-note beat at the selected BPM. Change after resolving this attempt. Click volume is in Audio settings.");
 beatClickButton_.onClick=[this]{setLessonBeatClick(!beatClick_);};
 title_.setText(juce::String::fromUTF8("PRACTICE — EXPLICIT START & SAVE"),juce::dontSendNotification);title_.setFont(juce::FontOptions{28.0f,juce::Font::bold});
 emptySourceState_.setComponentID("practice-empty-source-state");emptySourceState_.setTitle("Practice empty source-state marker.");emptySourceState_.setFont(juce::FontOptions{16.0f,juce::Font::bold});emptySourceState_.setColour(juce::Label::textColourId,appearance::colour(0xffa9bbc5));emptySourceState_.setText("No source-backed case selected yet",juce::dontSendNotification);
 status_.setComponentID("practice-status");status_.setTitle("Read-only Practice status: current lifecycle, next action, save boundary and local handoff.");
 description_.setComponentID("practice-authored-source");description_.setTitle("Authored source instructions and Practice next actions for the selected admitted case.");
 description_.setText("Choose an admitted source-backed case in Learn before Practice.\nNo authored lesson instructions or TAB are loaded in this empty Practice view.\nNo Attempt or curriculum credit exists yet.",juce::dontSendNotification);
 for(auto* component:std::initializer_list<juce::Component*>{&title_,&description_,&emptySourceState_,&status_,&facts_})addAndMakeVisible(*component);
 for(auto* b:{&connect_,&enable_,&start_,&pause_,&resume_,&stop_,&back_})addAndMakeVisible(*b);
 addAndMakeVisible(guidedSummary_);guidedSummary_.setComponentID("guided-summary");guidedSummary_.onClick=[this]{if(onGuidedSummary)onGuidedSummary();};
 addAndMakeVisible(openProgress_);openProgress_.setComponentID("open-progress");openProgress_.onClick=[this]{requestProgressPage();};
 addAndMakeVisible(metronomeButton_);
 connect_.onClick=[this]{performCommand(PracticeCommand::Connect);};enable_.onClick=[this]{performCommand(PracticeCommand::Enable);};start_.onClick=[this]{performCommand(PracticeCommand::Start);};pause_.onClick=[this]{performCommand(PracticeCommand::Pause);};resume_.onClick=[this]{performCommand(PracticeCommand::Resume);};stop_.onClick=[this]{performCommand(PracticeCommand::Stop);};
 metronomeButton_.onClick=[this]{requestMetronome();};
 back_.onClick=[this]{requestBack();};
 for(auto* component:std::initializer_list<juce::Component*>{&returnStatus_,&saveBack_,&retryBack_,&stay_})addChildComponent(*component);
 addAndMakeVisible(audioHelp_);audioHelp_.setFont(juce::FontOptions{14.0f});audioHelp_.setTitle("Speakers and headphones setup");
 audioHelp_.setText("Audio uses your macOS speakers or headphones. Connect audio, then Enable audio. Start begins sound. Audio settings are shared with Learn, Freeplay and rhythm tools; use Audio settings for output and mix, then Back to return to Practice without duplicating controls.",juce::dontSendNotification);
 returnStatus_.setFont(juce::FontOptions{16.0f});returnStatus_.setComponentID("practice-return-status");returnStatus_.setTitle("Read-only Practice return/recovery state, save barrier and next action.");
 saveBack_.setComponentID("practice-save-and-back");saveBack_.setTitle("Save the stopped Practice result, confirm cleanup, then return to Learn.");
 retryBack_.setComponentID("practice-retry-and-back");retryBack_.setTitle("Retry the original Practice save, confirm cleanup, then return to Learn.");
 stay_.setComponentID("practice-stay");stay_.setTitle("Keep the Practice result open without discarding or duplicating it.");
 saveBack_.onClick=[this]{saveAndBack();};retryBack_.onClick=[this]{retryAndBack();};stay_.onClick=[this]{stayHere();};
 for(auto* b:{&save_,&retry_,&again_})addAndMakeVisible(*b);
 addAndMakeVisible(assessment_);addAndMakeVisible(captureStatus_);addChildComponent(captureStatus_.detailsView());
 captureStatus_.onDetailsChanged=[this]{showSaveDetails();};
 assessment_.addItem("No self-assessment",1);assessment_.addItem("Struggling",2);assessment_.addItem("Developing",3);assessment_.addItem("Clean",4);assessment_.addItem("Easy",5);
 assessment_.setSelectedId(1,juce::dontSendNotification);assessment_.setTitle("Explicit self-assessment");
 save_.onClick=[this]{performCommand(PracticeCommand::Save);};
 retry_.onClick=[this]{performCommand(PracticeCommand::Retry);};again_.onClick=[this]{performCommand(PracticeCommand::Again);};
 connect_.setVisible(false);enable_.setVisible(false);audioHelp_.setVisible(false);
 addAndMakeVisible(audioSettings_);audioSettings_.onClick=[this]{if(!onAudioSettings){commandFeedback_.setText("Audio settings are unavailable from Practice until the existing shared Audio page is connected. Return to Home and choose Audio settings; no Practice activity or sound was started.",juce::dontSendNotification);refreshDisplay();return;}visitAudioSettings();onAudioSettings();};
 for(auto* c:std::initializer_list<juce::Component*>{&boardToggle_,&boardMode_,&boardSpelling_,&boardDisplayStatus_,&playbackBoard_})addChildComponent(*c);
 boardToggle_.setComponentID("practice-board-toggle");boardMode_.setComponentID("practice-board-mode");boardSpelling_.setComponentID("practice-board-spelling");
 boardMode_.setTitle("Playback fretboard mode");boardSpelling_.setTitle("Displayed note spelling only");
 boardMode_.addItem("Basic",1);boardMode_.addItem("Finger",2);boardMode_.addItem("Note",3);
 boardSpelling_.addItem("Sharp",1);boardSpelling_.addItem("Flat",2);
 boardDisplayStatus_.setFont(juce::FontOptions{12.0f});boardDisplayStatus_.setTitle("Fretboard display preference save status");
 auto boardChoice=[this]{auto value=boardDisplay_;value.mode=static_cast<setup::BoardMode>(boardMode_.getSelectedId()-1);value.spelling=static_cast<setup::NoteSpelling>(boardSpelling_.getSelectedId()-1);setBoardDisplay(value);if(onBoardDisplayChanged)onBoardDisplayChanged(value);};
 boardMode_.onChange=boardChoice;boardSpelling_.onChange=boardChoice;
 boardToggle_.onClick=[this]{auto value=boardDisplay_;value.visible=!value.visible;setBoardDisplay(value);if(onBoardDisplayChanged)onBoardDisplayChanged(value);};
 setBoardDisplay(boardDisplay_);
 model_=sampleModel();playbackBoard_.setModel(model_);tabView_.setDocument(std::make_shared<const tab::Document>(model_));tabView_.setCompact(true);addChildComponent(tabView_);addAndMakeVisible(tabModeButton_);tabModeButton_.onClick=[this]{showTab(!tabMode_);};
 for(auto* child:tabView_.getChildren())if(auto* button=dynamic_cast<juce::TextButton*>(child);button&&(button->getButtonText()=="Zoom -"||button->getButtonText()=="Zoom +"||button->getButtonText()=="Reset 100%")){
  auto original=button->onClick;button->onClick=[this,original]{original();if(focusMode_){refreshDisplay();resized();repaint();}};
 }
 addAndMakeVisible(focus_);addAndMakeVisible(commandFeedback_);addChildComponent(clean_);addChildComponent(focusFacts_);addChildComponent(shortcutHelp_);
 focus_.onClick=[this]{performCommand(PracticeCommand::ToggleFocus);};clean_.onClick=[this]{performCommand(PracticeCommand::Clean);};
 focusFacts_.setFont(juce::FontOptions{20.0f});shortcutHelp_.setFont(juce::FontOptions{16.0f});commandFeedback_.setFont(juce::FontOptions{16.0f});
 focusFacts_.setTitle("Practice tempo, loop and confirmed session facts");facts_.setComponentID("practice-saved-attempt-facts");facts_.setTitle("Read-only saved Practice Attempt ownership and activity facts.");commandFeedback_.setTitle("Practice command feedback");shortcutHelp_.setTitle("Practice keyboard shortcuts");
 auto configureControl=[&](juce::Component& component,const char* id,const char* title,int order){component.setComponentID(id);component.setTitle(title);component.setWantsKeyboardFocus(true);component.setExplicitFocusOrder(order);};
 configureControl(back_,"practice-back","Return to Learn without changing the current Practice result.",1);back_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));back_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));back_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(audioSettings_,"practice-audio-settings","Open shared Audio settings without changing the current Practice result.",2);audioSettings_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));audioSettings_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));audioSettings_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(tabModeButton_,"practice-tab-toggle","Show or hide the authored TAB view.",3);tabModeButton_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));tabModeButton_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));tabModeButton_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(focus_,"practice-focus","Enter or leave Practice Focus mode.",4);focus_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));focus_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));focus_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(start_,"practice-start","Start the selected Practice sample.",5);start_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));start_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));start_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(pause_,"practice-pause","Pause the active Practice sample.",6);pause_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));pause_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));pause_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(resume_,"practice-resume","Resume the paused Practice sample.",7);resume_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));resume_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));resume_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(stop_,"practice-stop","Stop Practice and review the result.",8);stop_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));stop_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));stop_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(save_,"practice-save","Save the reviewed Practice result as one local Attempt.",9);save_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));save_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));save_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(retry_,"practice-retry","Retry saving the reviewed Practice result.",10);retry_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));retry_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));retry_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(again_,"practice-again","Prepare another Practice sample without saving a curriculum result.",11);again_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));again_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));again_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(guidedSummary_,"practice-guided-summary","Open the owning Guided summary.",12);guidedSummary_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));guidedSummary_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));guidedSummary_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(openProgress_,"practice-open-progress","Open saved local Progress after a finalized Practice result.",13);openProgress_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));openProgress_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));openProgress_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(clean_,"practice-clean","Choose Clean for the explicit Practice self-assessment.",14);clean_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));clean_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));clean_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(metronomeButton_,"practice-metronome","Open the shared Metronome without changing the current Practice result.",15);metronomeButton_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));metronomeButton_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));metronomeButton_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 configureControl(tempoButton_,"lesson-tempo","Show or hide lesson tempo controls without changing the current Practice result.",16);tempoButton_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));tempoButton_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));tempoButton_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 shortcutHelp_.setText("Space: start / pause / resume    Esc: stop    F: leave Focus\nC: select Clean    S: save    R: retry original    A: Again (then explicit Start)",juce::dontSendNotification);
 focus_.setTooltip(shortcutHelp_.getText());focus_.setHelpText(shortcutHelp_.getText());
 setWantsKeyboardFocus(true);keyboard_=std::make_unique<PracticeKeyboardMac>(*this,[this](PracticeCommand c){performCommand(c);});
 keyboard_->onObservation=[this](const PracticeKeyObservation& o){if(onKeyObservation)onKeyObservation(o);};refreshDisplay();startTimer(20);
}
PracticeView::~PracticeView(){keyboard_.reset();quiesceAndRetain();} // flush before coupled provider destruction
bool PracticeView::send(platform::OutputCommand op,const scheduler::Owner& owner,scheduler::Owner next){platform::Control c;c.op=op;c.owner=owner;c.nextOwner=next;const auto s=output_.status().lifecycle;c.epoch=s.request.epoch;c.token=s.observationToken;c.requestedNs=platform::monotonicNs();if(op==platform::OutputCommand::Stop){stopRequested_=true;lastStopRequestNs_=c.requestedNs;}if(!output_.send(c)){error_="Output command queue refused. Original outcome remains pending.";return false;}if(op==platform::OutputCommand::Stop)clearBoardHighlight();return true;}
bool PracticeView::connectOutput(const platform::OutputCapability* expected){if(exitDiscard_||started_ || output_.status().lifecycle.state!=output::State::Closed)return false;const auto cap=settingsOutputCapability();if(expected&&!sameAudioCapability(cap,*expected)){error_="Output changed before Connect; inspect Audio settings.";return false;}audioDeviceName_=cap.valid?cap.name:std::string{};audioHelp_.setText(cap.valid?"Audio: "+juce::String(cap.name)+". Enable audio to prepare; Start begins sound.":"Audio unavailable. Choose speakers or headphones in macOS Sound settings, then Connect audio.",juce::dontSendNotification);const bool ok=connectSettingsOutput(output_,cap,{cap.rate,cap.valid?std::clamp(256U,cap.minFrames,cap.maxFrames):0U},&playback_,platform::PracticePlayback::observe,platform::PracticePlayback::render);if(!ok){error_=output_.error();audioHelp_.setText("Audio could not connect. See details; choose speakers or headphones in macOS Sound settings before retrying.",juce::dontSendNotification);}return ok;}
bool PracticeView::applyCommonMix(const output::MixSettings& value){if(!queueAudioMix(output_,value))return false;commonMix_=value;return true;}
bool PracticeView::audioCanRelease()const{return canReturn()&&outputCleared();}
bool PracticeView::audioRelease(){if(!audioCanRelease())return false;if(!output_.disconnect())return false;drain();serviceCapture();return audioCanRelease();}
bool PracticeView::requestMetronome(){
 if(!audioCanPrepare()){commandFeedback_.setText("Finish or resolve this Practice result before opening the shared Metronome.",juce::dontSendNotification);refreshDisplay();return false;}
 if(!onMetronome){commandFeedback_.setText("Metronome is unavailable from Practice until the existing Metronome page is connected. Return to Home and choose Metronome; no sound or Practice activity was started.",juce::dontSendNotification);refreshDisplay();return false;}
 if(onMetronome)onMetronome();
 return true;
}
bool PracticeView::requestProgressPage(){
 if(!capture_||capture_->phase()!=capture::SessionPhase::Saved){
  commandFeedback_.setText("Save the Practice result before opening Progress; no finalized local record is available yet.",juce::dontSendNotification);
  refreshDisplay();return false;
 }
 if(!audioCanRelease()){
  commandFeedback_.setText("Finish or resolve this Practice result before opening Progress; the local record remains here.",juce::dontSendNotification);
  refreshDisplay();return false;
 }
 if(!onProgressPage){
  commandFeedback_.setText("Progress is unavailable from Practice until the existing Progress page is connected. Return to Home and choose Progress to review the saved local Attempt; no new Attempt or curriculum credit was created. Next action: reconnect the existing Progress page, then choose Progress to review the saved local Attempt.",juce::dontSendNotification);
  refreshDisplay();return false;
 }
 if(!audioRelease()){
  commandFeedback_.setText("Practice output could not be released before opening Progress; the saved result remains here. Resolve the output state, then choose Open Progress again.",juce::dontSendNotification);
  refreshDisplay();return false;
 }
 onProgressPage();
 return true;
}
void PracticeView::visitAudioSettings(){playbackBoard_.setActiveEvents({});++returnGeneration_;returnAfterSave_=false;returnPosted_=false;requestedReturn_={};presentReturn();}
bool PracticeView::enableOutput(){return !exitDiscard_&&output_.status().lifecycle.state==output::State::Observed && send(platform::OutputCommand::Acknowledge,{});}
bool PracticeView::configureCapture(storage::ProfileStore& store,std::string session,std::function<std::string()> utc,std::string zone){
 if(started_||capture_||!utc)return false;storage::validateUuid(session);storage::localDay(utc(),zone);
 sessionId_=std::move(session);utcNow_=std::move(utc);timezone_=std::move(zone);capture_=std::make_unique<capture::PracticeSession>(store,coordinator_);return true;
}
bool PracticeView::rebindCaptureSession(std::string session){
 // Idle after a confirmed Again retains historical startTaken; only the current
 // phase/transport and unresolved-result guards determine whether rebinding is safe.
 if(!capture_||started_||capture_->phase()!=capture::SessionPhase::Idle||
    returnPanel_||returnAfterSave_||returnPosted_||returnFailed_||!canReturn()||!outputCleared()||!utcNow_||timezone_.empty())return false;
 try{storage::validateUuid(session);const auto now=utcNow_();storage::validateUtc(now);storage::localDay(now,timezone_);sessionId_=std::move(session);return true;}
 catch(const std::exception&){return false;}
}
bool PracticeView::configureLesson(std::shared_ptr<const lesson::Admission> selected,std::uint16_t bpm,const guitar::Setup& declared){
 if(!selected||!capture_||!canReturn()||!outputCleared())return false;
 try {
  const auto config=selected->practiceConfiguration(44100,bpm);
  const auto setupValue=declaredSetupValue(declared);const auto notice=lessonSetupNotice(*selected->model(),declared);
  auto document=std::make_shared<const tab::Document>(selected->model());
  const auto record=json::parse(selected->model()->source().preservedRecordJson);
  const auto id=selected->identity().object().at("variant_id").string();const json::Value* variant=nullptr;
  for(const auto& v:record.object().at("variants").array())if(v.object().at("id").string()==id)variant=&v;
  if(!variant)throw std::runtime_error("Selected variant label is absent from its own accepted source.");
  const auto& pickStart=variant->object().at("pick_start");
  auto label="Level "+json::stringify(record.object().at("legacy_level"))+" | "+
      (variant->object().at("route").string()=="selected"?"connected cell":variant->object().at("route").string())+
      (pickStart.null()?" | picking direction unspecified":" | "+pickStart.string()+" start");
  const auto sectionLabel=lessonSelectionLabel(*selected);if(!sectionLabel.empty())label+="\n"+sectionLabel;
  const auto caption="Level "+json::stringify(record.object().at("legacy_level"))+" | "+
      (sectionLabel.empty()?std::string{"Whole case"}:sectionLabel.substr(0,sectionLabel.find(':'))+" (partial)");
  label+="\nWorkbook identity: "+record.object().at("workbook_id").string()+" | Level: "+json::stringify(record.object().at("legacy_level"));
  label+="\n"+practiceSourceIdentity(*selected);
  // Disconnect flushes callbacks; drain/audit must still allow leaving the original.
  if(!audioRelease())return false;
  if(capture_->phase()==capture::SessionPhase::Saved){if(!capture_->again(true))return false;}
  else if(capture_->phase()!=capture::SessionPhase::Idle)return false;
  // No asynchronous preparation on the old selection, and no stale posted Back.
  ++returnGeneration_;returnPanel_=returnAfterSave_=returnPosted_=returnFailed_=false;requestedReturn_={};
  lesson_=std::move(selected);lessonLabel_=label;lessonCaption_=caption;model_=lesson_->model();config_=config;declaredSetup_=setupValue;beatClick_=false;initialRamp_.reset();tempoEvidence_.reset();requestedTempo_.reset();tempoAwaitingReply_=false;tempoPanelOpen_=false;resetTempoEditors();
  setupPrimaryNotice_=notice.warning?"Guitar setup differs. Open Setup details.\n":notice.summary.find("unavailable")!=std::string::npos?"Guitar setup unavailable. Open Setup details.\n":notice.summary.find("unspecified")!=std::string::npos?"Authored setup unspecified. Open Setup details.\n":"";setupSummary_.setText(juce::String::fromUTF8(notice.summary.c_str()),juce::dontSendNotification);setupSummary_.setColour(juce::Label::textColourId,juce::Colour{notice.warning?0xffffcb77U:0xffb7c9d2U});setupDetails_.setText(juce::String::fromUTF8(notice.details.c_str()),false);setupDetailsVisible_=false;
  clearBoardHighlight();playbackBoard_.setSetup(declared);playbackBoard_.setModel(model_);
  tabPlayback_=tab::Playback{};tabView_.setDocument(std::move(document));tabView_.setPlayback({},"Count-in Off. Explicit Start is required; no accepted output yet.");
  started_=stopRequested_=resolveRequested_=false;shown_={};terminalOutcome_.reset();error_.clear();assessment_.setSelectedId(1,juce::dontSendNotification);
  commandFeedback_.setText({},juce::dontSendNotification);
  start_.setButtonText("Start selected case");
  const auto ownerLine=sessionId_.empty()?std::string{}:"\nPractice owner Session: "+sessionId_;
  const auto& identity=lesson_->identity().object();std::string sourceRefs;
  for(std::size_t index=0;index<lesson_->model()->source().sourceRefs.size();++index){if(index)sourceRefs+=", ";sourceRefs+=lesson_->model()->source().sourceRefs[index];}
  const auto provenance="\n\nSOURCE PROVENANCE\nLesson title: "+record.object().at("title").string()+"\nVariant label: "+variant->object().at("label").string()+"\nWorkbook identity: "+record.object().at("workbook_id").string()+" | Level: "+json::stringify(record.object().at("legacy_level"))+"\nSource case: "+identity.at("item_id").string()+" / "+identity.at("variant_id").string()+"\nSource references: "+sourceRefs+"\nContent version: "+identity.at("content_version").string()+"\nContent revision: "+storage::canonical(identity.at("content_revision"));
  description_.setText(juce::String::fromUTF8((std::string{"AUTHORED SOURCE INSTRUCTIONS\n"}+lesson_->description()+ownerLine+provenance+"\nCount-in Off. Resume replays this selected span from its start.\nRead the authored instructions and TAB here; Back returns to Learn to change the source case.\nExplicit Start begins one local Practice Attempt; Save result is required before a local record is finalized.").c_str()),juce::dontSendNotification);
  showTab(true);refreshDisplay();return true;
 }catch(const std::exception& e){error_=e.what();return false;}
}
bool PracticeView::updateDeclaredSetup(const guitar::Setup& declared){
 if(!lesson_||!audioCanRelease())return false;
 try {auto value=declaredSetupValue(declared);const auto notice=lessonSetupNotice(*model_,declared);
 playbackBoard_.setSetup(declared);declaredSetup_=std::move(value);setupPrimaryNotice_=notice.warning?"Guitar setup differs. Open Setup details.\n":notice.summary.find("unavailable")!=std::string::npos?"Guitar setup unavailable. Open Setup details.\n":notice.summary.find("unspecified")!=std::string::npos?"Authored setup unspecified. Open Setup details.\n":"";setupSummary_.setText(juce::String::fromUTF8(notice.summary.c_str()),juce::dontSendNotification);setupSummary_.setColour(juce::Label::textColourId,juce::Colour{notice.warning?0xffffcb77U:0xffb7c9d2U});setupDetails_.setText(juce::String::fromUTF8(notice.details.c_str()),false);return true;
 }catch(const std::exception&){return false;}
}
void PracticeView::showSetupDetails(bool value){if(value&&captureStatus_.detailsVisible())captureStatus_.showDetails(false);setupDetailsVisible_=value;setupButton_.setButtonText(value?"Hide setup details":"Show setup details");showSaveDetails();}
bool PracticeView::setLessonBeatClick(bool value){
 if(!lesson_||started_||!canReturn()||!outputCleared()){
  commandFeedback_.setText("Resolve the current result and choose Again before changing the beat click.",juce::dontSendNotification);return false;
 }
 beatClick_=value;commandFeedback_.setText(value?"Quarter-note beat click selected. Click volume is in Audio settings; Start begins sound.":"Beat click Off. Reference notes and source instructions are unchanged.",juce::dontSendNotification);refreshDisplay();return true;
}
bool PracticeView::setLessonScheduledPasses(std::uint64_t passes){
 if(!lesson_||started_||returnPanel_||returnAfterSave_||returnPosted_||!canReturn()||!outputCleared()){
  commandFeedback_.setText("Resolve this result and choose Again before changing scheduled passes.",juce::dontSendNotification);refreshDisplay();return false;
 }
 try {auto next=config_;next.targetCycles=passes;lesson_->validatePractice(next);config_=next;
  commandFeedback_.setText("Scheduled passes selected. Playback does not prove performed repetitions or source-task completion.",juce::dontSendNotification);refreshDisplay();return true;
 }catch(const std::exception& e){commandFeedback_.setText(juce::String::fromUTF8(e.what()),juce::dontSendNotification);refreshDisplay();return false;}
}
bool PracticeView::canSelectTempo() const {
 return lesson_&&!started_&&!returnPanel_&&!returnAfterSave_&&!returnPosted_&&canReturn()&&outputCleared();
}
bool PracticeView::canRequestTempo() const {
 return lesson_&&hasCurrentAttempt()&&!returnPanel_&&!returnAfterSave_&&!returnPosted_&&!stopRequested_&&!terminalOutcome_
  &&capture_&&!capture_->stopRequired()&&coordinator_.state()==practice::State::Running
  &&output_.status().lifecycle.state==output::State::Running;
}
void PracticeView::resetTempoEditors(){
 rampDirection_.setSelectedId(initialRamp_?(initialRamp_->up?2:3):1,juce::dontSendNotification);
 rampStep_.setSelectedId(initialRamp_?initialRamp_->step:1,juce::dontSendNotification);
 rampEvery_.setSelectedId(initialRamp_?initialRamp_->every:1,juce::dontSendNotification);
 rampTarget_.setSelectedId(initialRamp_?initialRamp_->target:config_.bpm,juce::dontSendNotification);
 manualTempo_.setSelectedId(config_.bpm,juce::dontSendNotification);
}
bool PracticeView::setLessonRamp(std::optional<metronome::Ramp> value){
 if(!canSelectTempo()){
  commandFeedback_.setText("Resolve this result and choose Again before changing the initial ramp.",juce::dontSendNotification);resetTempoEditors();refreshDisplay();return false;
 }
 try {(void)lesson::tempoSettings(config_.bpm,value);initialRamp_=std::move(value);resetTempoEditors();
  commandFeedback_.setText("Initial ramp selected for the next attempt. Source clean-loop and next-time guidance remains separate.",juce::dontSendNotification);refreshDisplay();return true;
 }catch(const std::exception&){commandFeedback_.setText("Choose ramp step 1-20 BPM, every 1-32 completed selected spans, and target 20-300 BPM above the selected tempo for Up or below it for Down; or choose Off.",juce::dontSendNotification);resetTempoEditors();refreshDisplay();return false;}
}
bool PracticeView::requestLessonTempo(int bpm){
 if(!canRequestTempo()||bpm<20||bpm>300){
  commandFeedback_.setText("Choose 20-300 BPM while running. Finish any stop, pause or unresolved save first.",juce::dontSendNotification);return false;
 }
 const auto owner=coordinator_.owner();const auto seq=++sequence_;
 if(!playback_.manualTempo(owner,lessonTempoBinding,seq,bpm)){
  commandFeedback_.setText("Tempo request could not be queued. The current tempo is unchanged; try again while running.",juce::dontSendNotification);return false;
 }
 tempoRequestOwner_=owner;tempoRequestSequence_=seq;requestedTempo_=bpm;tempoAwaitingReply_=true;
 commandFeedback_.setText("Tempo request queued; waiting for audio acknowledgment. Applied tempo is shown above.",juce::dontSendNotification);refreshDisplay();return true;
}
std::string PracticeView::tempoFacts() const {
 const bool active=hasCurrentAttempt();
 std::string text="Selected: "+std::to_string(config_.bpm)+" BPM | Current: "+std::to_string(active?coordinator_.currentTempo():config_.bpm)+" BPM (quarter-note beat)";
 std::optional<int> pending;bool awaiting=false;
 if(active&&requestedTempo_&&tempoRequestOwner_==coordinator_.owner()){pending=requestedTempo_;awaiting=tempoAwaitingReply_;}
 else if(active&&tempoEvidence_&&tempoEvidence_->progress.owner==coordinator_.owner())pending=tempoEvidence_->tempo.pendingManual;
 if(pending)text+=(awaiting?" | Queued: ":coordinator_.state()==practice::State::Ended||coordinator_.state()==practice::State::Error?" | Unapplied: ":" | Pending: ")+std::to_string(*pending)+(awaiting?" (awaiting acknowledgment)":" at next loop");
 else text+=" | Pending: none";
 return text;
}
void PracticeView::showTempoControls(bool value){
 tempoPanelOpen_=value&&bool(lesson_)&&!returnPanel_;
 if(tempoPanelOpen_){captureStatus_.showDetails(false);setupDetailsVisible_=false;}
 showSaveDetails();refreshDisplay();
}
void PracticeView::refreshTempoControls(){
 const bool visible=bool(lesson_)&&!returnPanel_;
 tempoButton_.setVisible(visible);tempoButton_.setButtonText(tempoPanelOpen_?"Hide tempo controls":"Show tempo controls");
 tempoPanel_.setVisible(visible&&tempoPanelOpen_&&!captureStatus_.detailsVisible()&&!setupDetailsVisible_);
 for(auto* c:std::initializer_list<juce::Component*>{&rampDirection_,&rampStep_,&rampEvery_,&rampTarget_,&applyRamp_})c->setEnabled(canSelectTempo());
 manualTempo_.setEnabled(canRequestTempo());applyTempo_.setEnabled(canRequestTempo());
}
void PracticeView::layoutTempoControls(){
 const auto area=tabMode_?tabView_.getBounds():juce::Rectangle<int>{40,335,getWidth()-80,92};tempoPanel_.setBounds(area);
 rampDirection_.setBounds(0,0,116,34);rampStep_.setBounds(124,0,126,34);rampEvery_.setBounds(258,0,148,34);rampTarget_.setBounds(414,0,130,34);applyRamp_.setBounds(552,0,160,34);
 manualTempo_.setBounds(0,42,148,34);applyTempo_.setBounds(156,42,184,34);tempoHelp_.setBounds(352,40,std::max(1,area.getWidth()-352),52);
}
bool PracticeView::preparePlayback(const practice::Coordinator& original,std::uint64_t remaining){
 const auto& config=original.configuration();
 if(lesson_)return playback_.prepareLessonTempo(*lesson_,lesson_->referenceConfiguration(original.owner(),lessonTempoBinding,config.rate,original.currentTempo()),original,remaining);
 return playback_.prepare(model_,programConfig(config,original.owner()),config,remaining);
}
bool PracticeView::startSample(){
 if(exitDiscard_)return false;
 if(canStartNewCapture&&!canStartNewCapture())return false;
 if(started_ || !capture_ || output_.status().lifecycle.state!=output::State::Ready)return false;
 try {capture::StartRequest request;
  if(lesson_){config_.rate=output_.status().lifecycle.request.format.rate;lesson_->validatePractice(config_);
   request=capture::lessonStart(*lesson_,config_,sessionId_,utcNow_(),timezone_,output_.status().lifecycle.request.epoch,beatClick_,initialRamp_);
   request.binding.context.object().at("configuration").object()["declared_instrument_setup"]=declaredSetup_;
  }else{config_=practice::Configuration{};config_.span=Rational{4};config_.rate=output_.status().lifecycle.request.format.rate;config_.bpm=120;config_.meter={{4,4}};config_.faithfulWholeSpan=true;config_.targetCycles=2;
  using V=json::Value;using O=V::Object;using A=V::Array;auto n=[](int x){return V::fromInteger(x);};
  const auto identity=content::sha256("synthetic:practice-transport:qa1;standard-E2-held-quarter-plus-quarter;rest-two-quarters;source-not-curriculum");
  const V hashes=O{{"synthetic:practice-transport:qa1",identity}};
  V configuration=O{{"values",capture::configurationValues(config_)},{"synthetic_fixture",true},{"canonical_variant_id","fg:variant:000001"},{"authored_tempo_ref",nullptr},{"beat_reference_q",A{n(1),n(1)}},{"source_hashes",hashes}};
  V context=O{{"session_id",sessionId_},{"item_id","fg:item:000001"},{"variant_id","fg:variant:000001"},{"content_revision",n(1)},
   {"content_version","synthetic-practice-transport.1"},{"source_manifest_sha256",identity},{"source_refs",A{"synthetic:practice-transport:qa1"}},
   {"configuration_version",n(1)},{"configuration",configuration},{"span",O{{"start",A{n(0),n(1)}},{"end",A{n(4),n(1)}}}},{"target",O{{"cycles",n(2)}}}};
  request={{"","Attempt",context,hashes,utcNow_(),timezone_},config_,output_.status().lifecycle.request.epoch};}
  if(!capture_->start(std::move(request),++sequence_,static_cast<std::int64_t>(platform::monotonicNs()/1000000)))return false;
  clearBoardHighlight();boardAcceptOutput_=true;started_=true;stopRequested_=false;resolveRequested_=false;terminalOutcome_.reset();tempoEvidence_.reset();requestedTempo_.reset();tempoAwaitingReply_=false;error_.clear();shown_={};return true;
 }catch(const std::exception& e){error_=e.what();return false;}
}
bool PracticeView::pauseSample(){const auto s=output_.status().lifecycle;if(s.state!=output::State::Running || !coordinator_.command(++sequence_,coordinator_.owner()))return false;const bool accepted=send(platform::OutputCommand::Pause,coordinator_.owner());if(accepted)clearBoardHighlight();return accepted;}
bool PracticeView::resumeSample(){
 if(exitDiscard_)return false;
 if(coordinator_.state()!=practice::State::Paused || output_.status().lifecycle.state!=output::State::Paused||!capture_||capture_->stopRequired())return false;
 try {const auto previous=coordinator_.owner();const auto next=coordinator_.nextResumeOwner();const auto remaining=config_.targetCycles-coordinator_.completedCycles();
  auto staged=coordinator_;staged.resume();tab::Playback preparedTab;preparedTab.bind(tabView_.document(),model_,staged);
  if(!preparePlayback(staged,remaining))throw std::runtime_error("Prepared generation slots full; end this outcome.");
  if(!send(platform::OutputCommand::PauseRetained,previous) || !send(platform::OutputCommand::Resume,previous,next))return false;
  clearBoardHighlight();boardAcceptOutput_=true;coordinator_.resume();requestedTempo_=tempoEvidence_&&tempoEvidence_->progress.owner==previous?tempoEvidence_->tempo.pendingManual:std::optional<int>{};tempoRequestOwner_=next;tempoAwaitingReply_=false;tabPlayback_=std::move(preparedTab);tabView_.setPlayback({},lesson_?"Count-in Off; replay from selected-span start. No accepted output yet.":"Fresh count-in; no accepted musical output yet.");return true;
 }catch(const std::exception& e){error_=e.what();return false;}
}
bool PracticeView::stopSample(){if(!started_)return false;
 if(capture_&&!capture_->startTaken()){stopRequested_=true;capture_->cancelBeforeSound(platform::monotonicNs());clearBoardHighlight();return true;}
 const auto state=output_.status().lifecycle.state;
 if(state==output::State::Unresolved||state==output::State::Fault||terminalOutcome_)return false;
 if(!coordinator_.command(++sequence_,coordinator_.owner()))return false;const auto actual=output_.status().lifecycle.owner;const bool requested=send(platform::OutputCommand::Stop,coordinator_.owner());
 if(actual.valid() && !(actual==coordinator_.owner()))return send(platform::OutputCommand::Stop,actual)&&requested;
 return requested;}
bool PracticeView::canPerformCommand(PracticeCommand command)const{
 if(suiteMode_&&command==PracticeCommand::Clean)return false;
 if(suiteMode_&&command==PracticeCommand::Again&&terminalOutcome_==capture::Outcome::Natural&&capture_&&capture_->phase()==capture::SessionPhase::Saved)return false;
 if((command==PracticeCommand::Start||command==PracticeCommand::Again)&&canStartNewCapture&&!canStartNewCapture())return false;
 const auto out=output_.status().lifecycle.state;
 const auto phase=capture_?capture_->phase():capture::SessionPhase::Idle;
 if(exitDiscard_&&command!=PracticeCommand::Stop&&command!=PracticeCommand::Retry&&command!=PracticeCommand::ToggleFocus)return false;
 if(exitDiscard_&&command==PracticeCommand::Retry)return bool(capture_);
 if((returnPanel_||returnAfterSave_)&&(command==PracticeCommand::Start||command==PracticeCommand::Again))return false;
 switch(command){
  case PracticeCommand::Connect:return !started_&&out==output::State::Closed;
  case PracticeCommand::Enable:return out==output::State::Observed;
  case PracticeCommand::Start:return !started_&&capture_&&out==output::State::Ready;
  case PracticeCommand::Pause:return !stopRequested_&&out==output::State::Running;
  case PracticeCommand::Resume:return !stopRequested_&&coordinator_.state()==practice::State::Paused&&out==output::State::Paused&&capture_&&!capture_->stopRequired()&&coordinator_.completedCycles()<config_.targetCycles;
  case PracticeCommand::ToggleTransport:return !started_?canPerformCommand(PracticeCommand::Start):coordinator_.state()==practice::State::Paused?canPerformCommand(PracticeCommand::Resume):canPerformCommand(PracticeCommand::Pause);
  case PracticeCommand::Stop:return !stopRequested_&&started_&&capture_&&!terminalOutcome_&&(!capture_->startTaken()||out==output::State::Running||out==output::State::Paused);
  case PracticeCommand::Clean:return capture_&&phase==capture::SessionPhase::Review;
  case PracticeCommand::Save:return capture_&&phase==capture::SessionPhase::Review&&terminalOutcome_.has_value();
  case PracticeCommand::Retry:return capture_&&(phase==capture::SessionPhase::Failed||phase==capture::SessionPhase::AllocationUnknown||phase==capture::SessionPhase::SealedCheckpoint||(phase==capture::SessionPhase::Review&&capture_->stopRequired())||(phase==capture::SessionPhase::Saved&&!capture_->canLeave(outputCleared())));
  case PracticeCommand::Again:return capture_&&phase==capture::SessionPhase::Saved&&capture_->canLeave(outputCleared());
  case PracticeCommand::ToggleFocus:return true;
 }
 return false;
}
bool PracticeView::performCommand(PracticeCommand command){
 const bool allowed=canPerformCommand(command);bool okay=false;const char* accepted="Command accepted.";const char* refused="Command is unavailable in the current state.";
 switch(command){
  case PracticeCommand::Connect:okay=allowed&&connectOutput();refused="Finish the original result before reconnecting audio.";break;
  case PracticeCommand::Enable:okay=allowed&&enableOutput();refused="Open Audio settings and wait for the observed configuration before enabling.";break;
  case PracticeCommand::Start:okay=allowed&&startSample();refused="Start needs an attached test profile, enabled audio and no unresolved result.";break;
  case PracticeCommand::Pause:okay=allowed&&pauseSample();refused="Pause requires running output; a requested Stop must finish first.";break;
  case PracticeCommand::Resume:okay=allowed&&resumeSample();refused=lesson_?"Resume requires a confirmed pause; replay starts at the selected span's beginning.":"Resume requires a confirmed pause and an available whole-bar continuation.";break;
  case PracticeCommand::ToggleTransport:
   if(!started_)okay=allowed&&startSample();
   else if(!stopRequested_&&coordinator_.state()==practice::State::Paused)okay=allowed&&resumeSample();
   else if(!stopRequested_&&output_.status().lifecycle.state==output::State::Running)okay=allowed&&pauseSample();
   refused="Wait for the current transition or finish the original result; Start also needs enabled audio and a test profile.";break;
  case PracticeCommand::Stop:okay=allowed&&stopSample();accepted="Stop requested; confirmed and uncertain output remain separate.";refused="No running attempt can be stopped; retain or save any original result.";break;
  case PracticeCommand::Clean:okay=allowed&&chooseAssessment("Clean");accepted="Clean selected as self-report. Press S to save this result; partial facts stay partial.";refused="Clean requires an ended result in review. Sealed assessments cannot change; finish saving, then use Again.";break;
  case PracticeCommand::Save:okay=allowed&&saveSelectedAssessment();accepted="Save requested for the original result. Check its current status above.";refused="Save requires an ended result awaiting review. Retry an uncertain original with R.";break;
  case PracticeCommand::Retry:okay=allowed&&retrySave();accepted="Retry requested for the original result. Check its current status above.";refused="No original retry is available. Wait for the current save or follow its error.";break;
  case PracticeCommand::Again:okay=allowed&&againSample();accepted=output_.status().lifecycle.state==output::State::Closed?"Ready for another attempt. Open Audio settings, then Start.":"Ready for another attempt. Press Space to Start; sound remains stopped.";refused="Again requires confirmed persistence and cleared output. Save or reconcile the original first.";break;
  case PracticeCommand::ToggleFocus:setFocusMode(!focusMode_);okay=true;accepted=focusMode_?"Focus on. Audio settings returns here; F leaves Focus.":"Focus off. The same practice result and source remain selected.";break;
 }
 commandFeedback_.setText(okay?accepted:refused,juce::dontSendNotification);refreshDisplay();
 if(onPracticeCommand)onPracticeCommand(command,okay,commandFeedback());return okay;
}
// Direct programmatic entry reports acceptance; actual native keys use the AppKit adapter.
bool PracticeView::keyPressed(const juce::KeyPress& key){
 for(auto* focused=juce::Component::getCurrentlyFocusedComponent();focused&&focused!=this;focused=focused->getParentComponent())
  if((dynamic_cast<juce::ComboBox*>(focused)||dynamic_cast<juce::TextEditor*>(focused))&&isParentOf(focused))return false;
 const auto c=PracticeShortcutGate::command(key.getKeyCode(),key.getModifiers().withoutMouseButtons().getRawFlags()!=0);return c&&performCommand(*c);}
bool PracticeView::hasCurrentAttempt()const{
 return started_&&capture_&&capture_->startTaken()&&coordinator_.owner().valid()&&capture_->binding().owner==coordinator_.originalKey();
}
void PracticeView::refreshFocusFacts(){
 const auto active=hasCurrentAttempt()?coordinator_.activeFrames():0;
 const auto cycles=hasCurrentAttempt()?coordinator_.completedCycles():0;
 const auto seconds=config_.rate?static_cast<double>(active)/config_.rate:0.0;
 if(lesson_){const auto ownerLine=sessionId_.empty()?std::string{}:"\nPractice owner Session: "+sessionId_;const auto facts=juce::String::fromUTF8(tempoFacts().c_str())+"\nCount-in Off | Target: "+juce::String(static_cast<juce::int64>(config_.targetCycles))+" scheduled passes | Scheduled: "+juce::String(static_cast<juce::int64>(cycles))+" / "+juce::String(static_cast<juce::int64>(config_.targetCycles))+" | Active: "+juce::String(seconds,3)+" s"+juce::String::fromUTF8(ownerLine.c_str());focusFacts_.setTooltip(facts);
  if(focusMode_&&tabView_.zoom()>1.0){const auto tempo=tempoFacts();const auto pendingStart=tempo.find(" | ",tempo.find("Current:"));const auto pending=pendingStart==std::string::npos?std::string{"Pending: unknown"}:tempo.substr(pendingStart+3);
   const auto visible="Selected "+std::to_string(config_.bpm)+" | Current "+std::to_string(hasCurrentAttempt()?coordinator_.currentTempo():config_.bpm)+" BPM | "+pending+"\n"+std::to_string(cycles)+"/"+std::to_string(config_.targetCycles)+" passes | "+juce::String(seconds,3).toStdString()+" s | Session "+sessionId_.substr(0,8)+"…";
   focusFacts_.setText(juce::String::fromUTF8(setupPrimaryNotice_.c_str())+juce::String::fromUTF8(visible.c_str()),juce::dontSendNotification);
  }else focusFacts_.setText(juce::String::fromUTF8(setupPrimaryNotice_.c_str())+facts,juce::dontSendNotification);
  if(presentationLevel_!=presentation::Level::Developer){
    const auto tempo=tempoFacts();const auto split=tempo.find(" | ",tempo.find("Current:"));
    const auto pending=split==std::string::npos?std::string{}:tempo.substr(split+3);
    const auto basic="Tempo "+std::to_string(hasCurrentAttempt()?coordinator_.currentTempo():config_.bpm)+" BPM | "+pending+"\nPasses "+std::to_string(cycles)+"/"+std::to_string(config_.targetCycles)+" | Active "+juce::String(seconds,3).toStdString()+" s";
    const auto advanced=tempo+"\nCount-in Off | Scheduled passes "+std::to_string(cycles)+"/"+std::to_string(config_.targetCycles)+" | Active "+juce::String(seconds,3).toStdString()+" s";
    focusFacts_.setText(juce::String::fromUTF8((setupPrimaryNotice_+(presentationLevel_==presentation::Level::Beginner?basic:advanced)).c_str()),juce::dontSendNotification);
  }
  return;}

 const auto synthetic="120 BPM (quarter-note beat) | 4/4 | Loop: whole bar | Target: 2 cycles\nSynthetic session | Scheduled: "+juce::String(static_cast<juce::int64>(cycles))+" / 2 | Confirmed active: "+juce::String(seconds,3)+" s";
 focusFacts_.setTooltip(synthetic);
 focusFacts_.setText(juce::String::fromUTF8(setupPrimaryNotice_.c_str())+(focusMode_&&tabView_.zoom()>1.0?"120 BPM | 4/4 | whole-bar loop | "+juce::String(static_cast<juce::int64>(cycles))+"/2 cycles\nSynthetic session | Active "+juce::String(seconds,3)+" s":synthetic),juce::dontSendNotification);
}
void PracticeView::applyFocusTextScale(){
 const auto scale=focusMode_?std::clamp(1.0+0.4*(tabView_.zoom()-1.0),0.9,1.4):1.0;
 if(focusMode_){
  title_.setFont(juce::FontOptions{static_cast<float>(18.0*scale),juce::Font::bold});focusFacts_.setFont(juce::FontOptions{static_cast<float>(16.0*scale)});
  status_.setFont(juce::FontOptions{static_cast<float>(14.0*scale)});captureStatus_.setFont(juce::FontOptions{static_cast<float>(std::min(16.5,14.0*scale))});
  commandFeedback_.setFont(juce::FontOptions{static_cast<float>(std::min(19.5,16.0*scale))});setupSummary_.setFont(juce::FontOptions{static_cast<float>(std::min(16.0,14.0*scale))});
 }else{focusFacts_.setFont(juce::FontOptions{lesson_?16.0f:20.0f});setupSummary_.setFont(juce::FontOptions{14.0f});commandFeedback_.setFont(juce::FontOptions{16.0f});}
 for(auto* label:std::initializer_list<juce::Label*>{&title_,&focusFacts_,&status_,&commandFeedback_,&setupSummary_})label->setMinimumHorizontalScale(focusMode_?1.0f:0.7f);
 if(auto* primary=dynamic_cast<juce::Label*>(captureStatus_.findChildWithID("practice-save-status")))primary->setMinimumHorizontalScale(focusMode_?1.0f:0.7f);
 for(auto* child:tabView_.getChildren()){
  if(auto* label=dynamic_cast<juce::Label*>(child)){const bool heading=label->getText().startsWith("TAB")||label->getText()=="Interactive TAB";label->setFont(juce::FontOptions{static_cast<float>(heading?std::min(28.0,24.0*scale):std::min(16.0,14.0*scale)),heading?juce::Font::bold:juce::Font::plain});label->setMinimumHorizontalScale(focusMode_?1.0f:0.7f);}
  if(auto* editor=dynamic_cast<juce::TextEditor*>(child))editor->setFont(juce::FontOptions{static_cast<float>(14.0*scale)});
 }
}
void PracticeView::setFocusMode(bool value){
 if(value==focusMode_)return;
 if(value){beforeFocusTab_=tabMode_;beforeFocusScroll_=tabView_.scrollPosition();}
 focusMode_=value;showTab(value?true:beforeFocusTab_);
 focus_.setButtonText(value?"Exit Focus [F]":"Focus [F]");
 commandFeedback_.setText(value?"Focus on. Audio settings returns here; F leaves Focus.":"Focus off. The same practice result and source remain selected.",juce::dontSendNotification);
 title_.setFont(juce::FontOptions{lesson_&&lesson_->identity().find("selection")?16.0f:value?18.0f:28.0f,juce::Font::bold});status_.setFont(juce::FontOptions{value?26.0f:15.0f});captureStatus_.setFont(juce::FontOptions{value?17.0f:15.0f});
 refreshFocusFacts();resized();refreshDisplay();applyFocusTextScale();if(!value)tabView_.restoreScrollPosition(beforeFocusScroll_);repaint();
}
void PracticeView::quiesceAndRetain(){clearBoardHighlight();stopTimer();output_.shutdown();drain();clearBoardHighlight();}
void PracticeView::drain(){platform::NativeEvent ev;while(audioPolling_&&output_.nextEvent(ev)){
 if(started_ && stopRequested_ && ev.kind==71 && ev.epoch==coordinator_.owner().epoch && !output_.status().lifecycle.ownsOutcome)
  coordinator_.stoppedAcknowledged(coordinator_.owner(),practice::State::Ended,lastStopRequestNs_);
 if(onNativeEvent)onNativeEvent(ev);
}
 practice::Progress p;
 auto present=[&](const practice::Progress& fact,bool applied){if(applied){
   shown_=fact;
   if(tabView_.document()!=tabPlayback_.document())throw std::runtime_error("TAB document changed during a pinned outcome; stop and retain the original.");
   if(tabPlayback_.update(coordinator_)){const auto& position=tabPlayback_.position();
    std::string text=std::string(fact.state==practice::State::Ended?"Stopped output":fact.state==practice::State::Error?"Error output":practice::stateText(fact.state));
    if(!position.events.empty()){for(const auto& id:position.events){const auto* event=tabPlayback_.document()->event(id);text+=" | "+id+" q="+tab::fraction(*event->span.onset)+" dur="+tab::fraction(*event->span.duration);}}
    text+=" | last accepted client sample: "+(position.hasMusicalSample?std::to_string(position.sample):"none / count-in");
    const auto live=output_.status().lifecycle;
    const bool sounding=boardAcceptOutput_ && !stopRequested_ && position.hasMusicalSample &&
        fact.state==practice::State::Running && live.state==output::State::Running &&
        fact.owner==coordinator_.owner() && live.owner==fact.owner && isShowing() && tabMode_ && playbackBoard_.isVisible();
    if(sounding)playbackBoard_.setActiveTones(soundingTonesAt(*model_,coordinator_.timeline(fact.owner),position.cycle,position.sample));
    else playbackBoard_.setActiveEvents({});
    tabView_.setPlayback(position.events,text);if(onTabProgress)onTabProgress(position);
   }
   if(!terminalOutcome_&&(fact.state==practice::State::Ended||fact.state==practice::State::Error))
    terminalOutcome_=fact.state==practice::State::Error?capture::Outcome::InterruptedError:
        stopRequested_?capture::Outcome::Stop:coordinator_.completedCycles()==config_.targetCycles?capture::Outcome::Natural:capture::Outcome::Stop;
  }if(onProgress)onProgress(fact);};
 auto retain=[&](const practice::Progress& fact){try{present(fact,coordinator_.progress(fact));}catch(const std::exception& e){error_=e.what();send(platform::OutputCommand::Stop,coordinator_.owner());}};
 while(playback_.nextProgress(p))retain(p);while(playback_.reclaim(p))retain(p);
 platform::PracticeTempoEvidence packet;
 auto retainTempo=[&](const platform::PracticeTempoEvidence& fact){try{
  const bool applied=playback_.applyTempoEvidence(fact,coordinator_);
  if(applied){tempoEvidence_=fact;
   if(fact.progress.owner==tempoRequestOwner_&&fact.tempo.lastCommand>=tempoRequestSequence_){
    tempoAwaitingReply_=false;requestedTempo_=fact.tempo.pendingManual;
   }
  }
  present(fact.progress,applied);if(onTempoProgress)onTempoProgress(fact);
 }catch(const std::exception& e){error_=e.what();send(platform::OutputCommand::Stop,coordinator_.owner());}};
 while(playback_.nextTempoEvidence(packet))retainTempo(packet);
 while(playback_.reclaimTempoEvidence(packet))retainTempo(packet);
 platform::PracticeTempoReply reply;
 while(playback_.nextTempoReply(reply)){
  if(reply.owner==coordinator_.owner()&&reply.owner==tempoRequestOwner_&&reply.binding==lessonTempoBinding&&reply.sequence==tempoRequestSequence_){
   tempoAwaitingReply_=false;
   // A complete packet may already show this command applied; an older ACK must not restore a pending intent.
   const bool reflected=tempoEvidence_&&tempoEvidence_->progress.owner==reply.owner&&tempoEvidence_->tempo.lastCommand>=reply.sequence;
   if(!reply.accepted)requestedTempo_.reset();
   else if(!reflected)requestedTempo_=reply.bpm;
   commandFeedback_.setText(reply.accepted?"Tempo request acknowledged. Current and pending values above show the accepted state.":"No change was accepted for that request. Check Current above; try while running.",juce::dontSendNotification);
  }
  if(onTempoReply)onTempoReply(reply);
 }
 scheduler::Fact f;while(playback_.nextFact(f))if(onScheduledFact)onScheduledFact(f);
 const auto s=output_.status().lifecycle;
 if(s.state!=output::State::Running || coordinator_.state()!=practice::State::Running || terminalOutcome_)playbackBoard_.setActiveEvents({});
 if(started_ && (s.state==output::State::Unresolved || s.state==output::State::Fault))
  coordinator_.stoppedAcknowledged(s.owner.valid()?s.owner:coordinator_.owner(),s.state==output::State::Fault?practice::State::Error:practice::State::Ended,s.requestedStopNs);
 if(!terminalOutcome_&&(coordinator_.state()==practice::State::Ended||coordinator_.state()==practice::State::Error))
  terminalOutcome_=coordinator_.state()==practice::State::Error?capture::Outcome::InterruptedError:
      stopRequested_?capture::Outcome::Stop:coordinator_.completedCycles()==config_.targetCycles?capture::Outcome::Natural:capture::Outcome::Stop;
}
void PracticeView::timerCallback(){
 if(audioPolling_)output_.service();drain();serviceCapture();serviceReturn();refreshDisplay();
}
void PracticeView::refreshDisplay(){refreshBoardVisibility();const auto stopCaptionBefore=stop_.getButtonText();const auto s=output_.status().lifecycle;
 const bool progressWasVisible=openProgress_.isVisible(),guidedWasVisible=guidedSummary_.isVisible(),metronomeWasVisible=metronomeButton_.isVisible();
 refreshTempoControls();
 emptySourceState_.setVisible(!lesson_&&!focusMode_&&!tabMode_&&!returnPanel_);
 emptySourceState_.setText("No source-backed case selected yet",juce::dontSendNotification);
 scheduledPasses_.setVisible(bool(lesson_)&&!returnPanel_);
 scheduledPasses_.setEnabled(bool(lesson_)&&!started_&&!returnPanel_&&!returnAfterSave_&&!returnPosted_&&canReturn()&&outputCleared());
 scheduledPasses_.setSelectedId(static_cast<int>(config_.targetCycles),juce::dontSendNotification);
 beatClickButton_.setVisible(bool(lesson_)&&!returnPanel_);beatClickButton_.setEnabled(bool(lesson_)&&!started_&&canReturn()&&outputCleared());
 beatClickButton_.setButtonText(beatClick_?"Disable quarter-note beat click":"Enable quarter-note beat click");
 metronomeButton_.setVisible(!returnPanel_&&!focusMode_);metronomeButton_.setEnabled(audioCanPrepare());
 const bool guidedSummaryReady=static_cast<bool>(onGuidedSummary)&&capture_&&capture_->phase()==capture::SessionPhase::Saved&&!returnPanel_&&!returnAfterSave_&&!returnPosted_&&!returnFailed_&&audioCanRelease();
 guidedSummary_.setTitle(guidedSummaryReady?"Open the owning Guided Session summary for this saved Attempt.":"Open the owning Guided summary.");
 guidedSummary_.setVisible(guidedSummaryReady);guidedSummary_.setEnabled(guidedSummaryReady);
 const bool progressReady=static_cast<bool>(capture_)&&capture_->phase()==capture::SessionPhase::Saved&&!returnPanel_&&!returnAfterSave_&&!returnPosted_&&!returnFailed_;
 openProgress_.setTitle(progressReady?"Open read-only Progress for this saved Practice Attempt.":"Open saved local Progress after a finalized Practice result.");
 openProgress_.setVisible(progressReady);openProgress_.setEnabled(progressReady&&audioCanRelease());
 const bool reviewAwaitingSave=error_.empty()&&capture_&&capture_->phase()==capture::SessionPhase::Review&&terminalOutcome_.has_value();
 const bool savedReturnReady=static_cast<bool>(capture_)&&capture_->phase()==capture::SessionPhase::Saved&&!returnPanel_&&!returnAfterSave_&&!returnPosted_&&!returnFailed_&&audioCanRelease();
 const bool guidedOwner=lesson_&&static_cast<bool>(onGuidedSummary);
 const bool guidedPreSave=guidedOwner&&capture_&&capture_->phase()==capture::SessionPhase::Idle&&!started_&&!returnPanel_&&!returnAfterSave_;
 std::string sourceIdentity;
 if(lesson_){const auto& identity=lesson_->identity().object();sourceIdentity=identity.at("item_id").string()+" / "+identity.at("variant_id").string();}
 const bool savedPhase=capture_&&capture_->phase()==capture::SessionPhase::Saved;
 // Communicate the existing admission state; this text never issues audio/capture commands.
 const auto nextStartAction=startPrerequisite(s.state,canPerformCommand(PracticeCommand::Start)).first;
 std::string startTitle="Start the selected Practice sample.";
 if(savedPhase)startTitle="This Practice result is already saved; choose Again to prepare another sample before explicit Start.";
 else if(!sourceIdentity.empty())startTitle="Start the selected Practice sample for "+sourceIdentity+"; explicit Start creates one local Attempt and no curriculum credit.";
 if(guidedPreSave)startTitle="Start the selected Practice sample for "+sourceIdentity+"; it will remain owned by the active Guided Session and creates no curriculum credit.";
 start_.setTitle(juce::String::fromUTF8(startTitle.c_str()));
 std::string pauseTitle=sourceIdentity.empty()?"Pause the active Practice sample.":"Pause the active Practice sample for "+sourceIdentity+"; active time remains retained without finalizing.";
 std::string resumeTitle=sourceIdentity.empty()?"Resume the paused Practice sample.":"Resume the paused Practice sample for "+sourceIdentity+"; active time remains retained without finalizing.";
 std::string stopTitle=sourceIdentity.empty()?"Stop Practice and review the result.":"Stop Practice for "+sourceIdentity+" and review the result; Save result is a separate explicit action.";
 std::string saveTitle;
 if(savedPhase)saveTitle="This Practice result is already saved; Save will not create another Attempt.";
 else if(sourceIdentity.empty())saveTitle="Save the reviewed Practice result as one local Attempt.";
 else saveTitle="Save the reviewed Practice result for "+sourceIdentity+" as one local Attempt; no curriculum credit is inferred.";
 std::string retryTitle;
 if(savedPhase)retryTitle="This Practice result is already saved; Retry will not create another Attempt.";
 else if(sourceIdentity.empty())retryTitle="Retry saving the reviewed Practice result.";
 else retryTitle="Retry saving the original reviewed Practice result for "+sourceIdentity+"; no duplicate Attempt is created.";
 std::string againTitle=sourceIdentity.empty()?"Prepare another Practice sample without saving a curriculum result.":"Prepare another Practice sample for "+sourceIdentity+" without saving a curriculum result.";
 pause_.setTitle(juce::String::fromUTF8(pauseTitle.c_str()));resume_.setTitle(juce::String::fromUTF8(resumeTitle.c_str()));stop_.setTitle(juce::String::fromUTF8(stopTitle.c_str()));save_.setTitle(juce::String::fromUTF8(saveTitle.c_str()));retry_.setTitle(juce::String::fromUTF8(retryTitle.c_str()));again_.setTitle(juce::String::fromUTF8(againTitle.c_str()));
 std::string audioTitle="Open shared Audio settings without changing the current Practice result.";
 if(guidedOwner){const auto& identity=lesson_->identity().object();audioTitle="Open shared Audio settings for "+identity.at("item_id").string()+" / "+identity.at("variant_id").string()+" without changing the active Guided Session or Practice result.";}
 audioSettings_.setTitle(juce::String::fromUTF8(audioTitle.c_str()));
 std::string metronomeTitle="Open the shared Metronome without changing the current Practice result.";
 if(guidedOwner){const auto& identity=lesson_->identity().object();metronomeTitle="Open the shared Metronome for "+identity.at("item_id").string()+" / "+identity.at("variant_id").string()+" without changing the active Guided Session or Practice result.";}
 metronomeButton_.setTitle(juce::String::fromUTF8(metronomeTitle.c_str()));
 std::string tempoTitle="Show or hide lesson tempo controls without changing the current Practice result.";
 if(guidedOwner){const auto& identity=lesson_->identity().object();tempoTitle="Show or hide lesson tempo controls for "+identity.at("item_id").string()+" / "+identity.at("variant_id").string()+" without changing the active Guided Session or Practice result.";}
 tempoButton_.setTitle(juce::String::fromUTF8(tempoTitle.c_str()));
 std::string tabTitle="Show or hide the authored TAB view.";
 if(guidedOwner){const auto& identity=lesson_->identity().object();tabTitle="Show or hide the authored TAB view for "+identity.at("item_id").string()+" / "+identity.at("variant_id").string()+" without changing the active Guided Session or selected source.";}
 tabModeButton_.setTitle(juce::String::fromUTF8(tabTitle.c_str()));
 std::string focusTitle="Enter or leave Practice Focus mode.";
 if(guidedOwner){const auto& identity=lesson_->identity().object();focusTitle="Enter or leave Practice Focus mode for "+identity.at("item_id").string()+" / "+identity.at("variant_id").string()+" without changing the active Guided Session or selected source.";}
 focus_.setTitle(juce::String::fromUTF8(focusTitle.c_str()));
 const auto destination=back_.getButtonText().startsWith("Back to ")?back_.getButtonText().substring(8).toStdString():std::string{"Learn"};
 std::string backTitle="Return to "+destination+" without changing the current Practice result.";
 if(savedReturnReady) backTitle="Return to "+destination+" after the Practice result is saved and audio cleanup is confirmed.";
 else if(reviewAwaitingSave) backTitle="Review and save the stopped Practice result before returning to "+destination+"; Back never saves automatically.";
 else if(guidedOwner){const auto& identity=lesson_->identity().object();backTitle="Return to "+destination+" from "+identity.at("item_id").string()+" / "+identity.at("variant_id").string()+" without changing the active Guided Session or Practice result.";}
 back_.setTitle(juce::String::fromUTF8(backTitle.c_str()));
 connect_.setEnabled(canPerformCommand(PracticeCommand::Connect));enable_.setEnabled(canPerformCommand(PracticeCommand::Enable));start_.setEnabled(canPerformCommand(PracticeCommand::Start));
 pause_.setEnabled(canPerformCommand(PracticeCommand::Pause));const bool resumeReady=canPerformCommand(PracticeCommand::Resume);resume_.setEnabled(resumeReady);resume_.setButtonText(resumeReady?"Resume selected span":"Resume");const bool stopReady=canPerformCommand(PracticeCommand::Stop);stop_.setEnabled(stopReady);stop_.setButtonText(stopReady?"Stop & review result":"Stop");back_.setEnabled(true);
 if(!tabMode_&&!captureStatus_.detailsVisible()&&!setupDetailsVisible_&&!tempoPanelOpen_)facts_.setVisible(true);
 std::string savedAttemptSourceFacts;
 if(capture_ && capture_->phase() == capture::SessionPhase::Saved && lesson_){
  const auto& savedIdentity=lesson_->identity().object();std::string sourceRefs;
  for(std::size_t index=0;index<lesson_->model()->source().sourceRefs.size();++index){if(index)sourceRefs+=", ";sourceRefs+=lesson_->model()->source().sourceRefs[index];}
  savedAttemptSourceFacts="\nSaved Attempt source: "+savedIdentity.at("item_id").string()+" / "+savedIdentity.at("variant_id").string()+"\nSaved Attempt source references: "+sourceRefs+"\nSaved Attempt content version: "+savedIdentity.at("content_version").string()+"\nSaved Attempt content revision: "+storage::canonical(savedIdentity.at("content_revision"));
  const auto savedRecord=json::parse(lesson_->model()->source().preservedRecordJson);const auto& savedRecordObject=savedRecord.object();
  savedAttemptSourceFacts+="\nSaved Attempt lesson title: "+savedRecordObject.at("title").string();
  for(const auto& candidate:savedRecordObject.at("variants").array())if(candidate.object().at("id").string()==savedIdentity.at("variant_id").string()){savedAttemptSourceFacts+="\nSaved Attempt variant label: "+candidate.object().at("label").string();break;}
  const auto workbook=savedIdentity.find("workbook_id");const auto level=savedIdentity.find("legacy_level");
  if(workbook!=savedIdentity.end()&&level!=savedIdentity.end()&&workbook->second.isString()&&!workbook->second.string().empty())
   savedAttemptSourceFacts+="\nSaved Attempt workbook identity: "+workbook->second.string()+" | Level: "+storage::canonical(level->second);
 }
 std::string displayedStatus;
 if(!error_.empty())displayedStatus="Practice needs attention — see Save details.";
 else if(reviewAwaitingSave)displayedStatus="Practice stopped. Review the result; Save result finalizes one local Practice Attempt. Back waits until the result is saved or explicitly resolved. Next action: review the stopped result, then choose Save result to finalize one local Practice Attempt; Back waits until the result is saved or explicitly resolved.";
 else if(!lesson_)displayedStatus="Practice opens from Learn. Opening Practice without a selected case does not start sound or create an Attempt. Choose an admitted source-backed case before Start; no Attempt or curriculum credit exists yet. Open Audio settings to connect and enable the shared output before Start.";
 else if(started_&&coordinator_.state()==practice::State::Running)displayedStatus="Practice is running. Pause preserves active time; Stop ends the original result, then Save result finalizes one local Practice Attempt. Next action: choose Pause to preserve active time, or choose Stop to review and then Save result.";
 else if(started_&&coordinator_.state()==practice::State::Paused)displayedStatus="Practice is paused. Resume continues this selected span; Stop ends the original result, then Save result finalizes one local Practice Attempt. Next action: choose Resume to continue this selected span, or choose Stop to review and then Save result.";
 else if(capture_&&capture_->phase()==capture::SessionPhase::Saved)displayedStatus=std::string{"Practice result saved locally. Open Progress reviews it read-only; Guided summary returns to the owning Session when this Attempt is Guided-owned."}+savedAttemptSourceFacts+"\nNext action: choose Open Progress for a read-only review; choose Guided summary to return to the owning Session when this Attempt is Guided-owned.";
 else if(started_)displayedStatus=practice::stateText(coordinator_.state());
 else if(capture_&&capture_->phase()==capture::SessionPhase::Idle)
  {
   std::string selectedSourceFacts;
   if(lesson_){
    const auto& selectedIdentity=lesson_->identity().object();std::string sourceRefs;
    for(std::size_t index=0;index<lesson_->model()->source().sourceRefs.size();++index){if(index)sourceRefs+=", ";sourceRefs+=lesson_->model()->source().sourceRefs[index];}
    const auto selectedRecord=json::parse(lesson_->model()->source().preservedRecordJson);const auto& selectedRecordObject=selectedRecord.object();std::string selectedVariantLabel;
    for(const auto& candidate:selectedRecordObject.at("variants").array())if(candidate.object().at("id").string()==selectedIdentity.at("variant_id").string()){selectedVariantLabel=candidate.object().at("label").string();break;}
    selectedSourceFacts="\nSelected lesson: "+selectedRecordObject.at("title").string()+"\nSelected variant: "+selectedVariantLabel+"\nSelected workbook identity: "+selectedRecordObject.at("workbook_id").string()+" | Level: "+json::stringify(selectedRecordObject.at("legacy_level"))+"\nSelected source: "+selectedIdentity.at("item_id").string()+" / "+selectedIdentity.at("variant_id").string()+"\nSelected source references: "+sourceRefs+"\nSelected content version: "+selectedIdentity.at("content_version").string()+"\nSelected content revision: "+storage::canonical(selectedIdentity.at("content_revision"));
   }
   displayedStatus=std::string(output::stateText(s.state))+selectedSourceFacts+"\nOpening the selected Practice case does not start sound or create an Attempt.\nNext action: "+nextStartAction+"\nExplicit Start begins one local Practice Attempt; Save result is required before a local record is finalized.";
  }
 else displayedStatus=output::stateText(s.state);
 status_.setTooltip({});
 if(focusMode_){
  status_.setTooltip(juce::String::fromUTF8(displayedStatus.c_str()));
  if(error_.empty()&&capture_&&capture_->phase()==capture::SessionPhase::Idle&&!started_&&lesson_){
   std::string refs;for(const auto& ref:lesson_->model()->source().sourceRefs){if(!refs.empty())refs+=", ";refs+=ref;}
   displayedStatus=tabView_.zoom()>1.0?std::string(output::stateText(s.state))+". No Attempt started.\n"+nextStartAction+" Save remains separate.":std::string(output::stateText(s.state))+". No Attempt started.\nSource refs: "+refs+"\n"+nextStartAction+" Save remains separate.";
  }else if(reviewAwaitingSave)displayedStatus="Practice stopped. Review the original result, then Save before Back.";
  else if(started_&&coordinator_.state()==practice::State::Running)displayedStatus="Practice running. Pause or Stop; Save follows Review.";
  else if(started_&&coordinator_.state()==practice::State::Paused)displayedStatus="Practice paused. Resume or Stop; Save follows Review.";
  else if(capture_&&capture_->phase()==capture::SessionPhase::Saved)displayedStatus="Practice result saved locally. Open Progress to review it read-only.";
  else if(!lesson_)displayedStatus="No admitted case selected. Choose one in Learn before Start.";
 }
 status_.setText(juce::String::fromUTF8(displayedStatus.c_str()),juce::dontSendNotification);
 commandFeedback_.setTooltip(commandFeedback_.getText());
 const auto savedPracticeFact = capture_ && capture_->phase() == capture::SessionPhase::Saved
     ? std::string{"A local Practice Attempt is saved. Clean and performed repetitions are not inferred. Open Progress to review this finalized Practice record read-only; no curriculum credit or source-task completion is inferred. If this Attempt belongs to a Guided Session, Guided summary returns to that Session after save."} + savedAttemptSourceFacts + (guidedSummaryReady ? "\nGuided-owned Practice Attempt: Guided summary returns to the owning Session after save." : "")
     : std::string{"No Clean, performed repetitions or saved practice is inferred."};
 facts_.setText("Software-confirmed active time: "+juce::String(config_.rate&&hasCurrentAttempt()?static_cast<double>(coordinator_.activeFrames())/config_.rate:0,3)+" s  |  Scheduled cycles: "+juce::String(static_cast<juce::int64>(hasCurrentAttempt()?coordinator_.completedCycles():0))+"\n"+savedPracticeFact+" Space: pause/resume; Esc: stop.",juce::dontSendNotification);repaint();
 showCaptureStatus();refreshFocusFacts();presentReturn();
 if(getWidth()>0&&getHeight()>0&&(progressWasVisible!=openProgress_.isVisible()||guidedWasVisible!=guidedSummary_.isVisible()||metronomeWasVisible!=metronomeButton_.isVisible()||stopCaptionBefore!=stop_.getButtonText()))resized();
}
bool PracticeView::outputCleared()const{const auto s=output_.status().lifecycle;return !s.ownsOutcome&&!s.pendingOutcome&&s.state!=output::State::Running&&s.state!=output::State::Paused;}
void PracticeView::serviceCapture(){
 if(!capture_)return;
 try{const auto now=static_cast<std::int64_t>(platform::monotonicNs()/1000000);capture_->poll(now,utcNow_());
  if(capture_->stopRequired()&&capture_->startTaken()&&(output_.status().lifecycle.state==output::State::Running||output_.status().lifecycle.state==output::State::Paused)&&!stopRequested_)stopSample();
  if(capture_->phase()==capture::SessionPhase::Ready){
   const auto s=output_.status().lifecycle;
   if(s.state!=output::State::Ready||s.request.epoch!=coordinator_.owner().epoch)capture_->cancelBeforeSound(platform::monotonicNs());
   else if(auto owner=capture_->takeStart(now)){
    bool prepared=false;try{prepared=preparePlayback(coordinator_,config_.targetCycles);}catch(const std::exception& e){error_=e.what();}
    if(prepared)try{tabPlayback_.bind(tabView_.document(),model_,coordinator_);tabView_.setPlayback({},lesson_?"Count-in Off; no accepted musical output yet.":"Fresh count-in; no accepted musical output yet.");}catch(const std::exception& e){prepared=false;error_=e.what();}
    if(!prepared||!send(platform::OutputCommand::Start,*owner)){
     coordinator_.stoppedAcknowledged(*owner,practice::State::Error,platform::monotonicNs());error_="Output start refused; original zero/partial facts retained.";
    }
   }
  }
  // A suite records truthful capture facts without an intermediate assessment.
  // Only natural target completion auto-saves; Stop/error remains explicit.
  if(!exitRequested_&&suiteMode_&&capture_->phase()==capture::SessionPhase::Review&&terminalOutcome_==capture::Outcome::Natural&&
     coordinator_.completedCycles()==config_.targetCycles&&config_.targetCycles>0)saveSample(nullptr);
  if(capture_->phase()==capture::SessionPhase::Saved&&!resolveRequested_){
   const auto s=output_.status().lifecycle;
   if(s.ownsOutcome){if(send(platform::OutputCommand::ResolveOutcome,s.owner))resolveRequested_=true;}
   else resolveRequested_=outputCleared();
  }
 }catch(const std::exception& e){error_=e.what();if(started_)stopSample();}
}
bool PracticeView::suiteNaturalCompleted()const {
 return suiteMode_&&capture_&&capture_->phase()==capture::SessionPhase::Saved&&terminalOutcome_==capture::Outcome::Natural&&
        coordinator_.completedCycles()==config_.targetCycles&&config_.targetCycles>0&&capture_->original()&&
        capture_->original()->owner==capture_->binding().owner&&capture_->original()->kind=="Attempt"&&audioCanRelease();
}
bool PracticeView::saveSample(json::Value assessment){
 if(exitDiscard_)return false;
 if(suiteMode_&&!assessment.null())return false;
 if(!capture_)return false;try{
  if(!terminalOutcome_)return false;
  const auto selected=assessment;const bool okay=capture_->save(std::move(assessment),*terminalOutcome_,static_cast<std::int64_t>(platform::monotonicNs()/1000000));
  if(okay){int id=1;if(selected==json::Value("Struggling"))id=2;else if(selected==json::Value("Developing"))id=3;else if(selected==json::Value("Clean"))id=4;else if(selected==json::Value("Easy"))id=5;assessment_.setSelectedId(id,juce::dontSendNotification);}return okay;
 }catch(const std::exception& e){error_=e.what();return false;}
}
bool PracticeView::chooseAssessment(json::Value a){
 if(exitDiscard_)return false;
 if(suiteMode_&&!a.null())return false;
 if(!capture_||capture_->phase()!=capture::SessionPhase::Review)return false;
 int id=1;if(a==json::Value("Struggling"))id=2;else if(a==json::Value("Developing"))id=3;else if(a==json::Value("Clean"))id=4;else if(a==json::Value("Easy"))id=5;else if(!a.null())return false;
 assessment_.setSelectedId(id,juce::dontSendNotification);return true;
}
bool PracticeView::saveSelectedAssessment(){if(suiteMode_)return saveSample(nullptr);return saveSample(assessment_.getSelectedId()==1?json::Value(nullptr):json::Value(assessment_.getText().toStdString()));}
bool PracticeView::retrySave(){
 if(exitDiscard_){retryExitDiscard();return true;}
 if(!capture_)return false;
 if(capture_->phase()==capture::SessionPhase::Saved&&!outputCleared())return send(platform::OutputCommand::ResolveOutcome,output_.status().lifecycle.owner);
 const auto now=static_cast<std::int64_t>(platform::monotonicNs()/1000000);const bool okay=capture_->inspectAllocation(now)||capture_->retry(now);
 if(okay&&capture_->phase()==capture::SessionPhase::Idle){started_=false;stopRequested_=false;resolveRequested_=false;error_.clear();}return okay;
}
bool PracticeView::againSample(){
 if(exitDiscard_)return false;
 if(!capture_||!capture_->again(outputCleared()))return false;
 clearBoardHighlight();
 tabView_.setPlayback({},"Result saved. Explicit Start is required.");
 started_=false;stopRequested_=false;resolveRequested_=false;assessment_.setSelectedId(1,juce::dontSendNotification);error_.clear();tempoEvidence_.reset();requestedTempo_.reset();tempoAwaitingReply_=false;resetTempoEditors();refreshDisplay();if(onAudioPreparation)onAudioPreparation();return true;
}
bool PracticeView::requestExit(bool discard){
 const bool firstRequest=!exitRequested_;exitRequested_=true;exitDiscard_=discard;
 if(!discard&&firstRequest&&canPerformCommand(PracticeCommand::Retry))retrySave();
 if(capture_&&discard){capture_->requestExitDiscard();if(firstRequest)commandFeedback_.setText("Unsaved changes discarded. Saved history and recovery records stay. This owner is stopped for recovery only; Retry continues original accepted operations.",juce::dontSendNotification);}
 if(canPerformCommand(PracticeCommand::Stop))stopSample();
 drain();serviceCapture();
 // Explicit Discard resolves only this stopped output debt after admitted capture
 // operations have settled; it never changes the navigation/Saved contract.
 if(discard&&capture_&&!resolveRequested_){
  const auto stopped=output_.status().lifecycle;
  const bool stoppedOwned=stopped.owner==coordinator_.owner()&&stopped.ownsOutcome&&stopped.pendingOutcome&&
      (stopped.state==output::State::Unresolved||stopped.state==output::State::Fault);
  if(stoppedOwned&&capture_->canLeaveForExit(true,static_cast<std::int64_t>(platform::monotonicNs()/1000000)))
   if(send(platform::OutputCommand::ResolveOutcome,stopped.owner))resolveRequested_=true;
 }
 // Exit requires acknowledged device cleanup and a closed lifecycle, not only released outcome.
 if(outputCleared()){if(!output_.disconnect())return false;drain();serviceCapture();}
 if(!capture_)return !started_&&outputCleared();
 if(discard)return capture_->canLeaveForExit(outputCleared(),static_cast<std::int64_t>(platform::monotonicNs()/1000000));
 if(canPerformCommand(PracticeCommand::Save))saveSelectedAssessment();
 return capture_->canLeave(outputCleared());
}
bool PracticeView::requestClose(){
 if(!capture_)return !started_;
 if(capture_->canLeave(outputCleared())){output_.shutdown();drain();serviceCapture();if(capture_->phase()==capture::SessionPhase::Failed&&capture_->binding().owner.empty())retrySave();if(capture_->canLeave(outputCleared()))return true;}
 if(canPerformCommand(PracticeCommand::Stop))stopSample();
 returnPanel_=true;showTab(tabMode_);presentReturn();showCaptureStatus();return false;
}
bool PracticeView::canReturn()const{return !capture_?!started_:capture_->canLeave(outputCleared());}
bool PracticeView::retainReturnRequest(){
 if(!requestedReturn_)requestedReturn_=onBack;
 if(!requestedReturn_)return false;
 returnAfterSave_=true;return true;
}
void PracticeView::requestBack(){
 if(!onBack&&!requestedReturn_){
  commandFeedback_.setText("Back is unavailable from Practice until the existing Learn navigation is connected. Return to Learn to continue the existing Practice flow; no Practice result, Attempt or curriculum credit was changed. Next action: reconnect the existing Learn navigation, then choose Back.",juce::dontSendNotification);
  refreshDisplay();return;
 }
 returnFailed_=false;
 if(!retainReturnRequest())return;
 if(canReturn()){clearBoardHighlight();queueReturn();return;}
 playbackBoard_.setActiveEvents({});returnPanel_=true;
 if(canPerformCommand(PracticeCommand::Stop))performCommand(PracticeCommand::Stop);
 showTab(tabMode_);refreshDisplay();
}
void PracticeView::saveAndBack(){
 if(canReturn()){if(retainReturnRequest())queueReturn();return;}
 if(!canPerformCommand(PracticeCommand::Save))return;
 // This explicit action uses the current optional assessment. Back alone never saves.
 if(performCommand(PracticeCommand::Save)&&retainReturnRequest())serviceReturn();
 refreshDisplay();
}
void PracticeView::retryAndBack(){
 if(returnFailed_&&canReturn()){requestBack();return;}
 if(!canPerformCommand(PracticeCommand::Retry))return;
 if(performCommand(PracticeCommand::Retry)&&retainReturnRequest())serviceReturn();
 refreshDisplay();
}
void PracticeView::stayHere(){
 ++returnGeneration_;returnAfterSave_=false;returnPosted_=false;returnPanel_=false;returnFailed_=false;requestedReturn_={};
 showTab(tabMode_);refreshDisplay();
}
void PracticeView::serviceReturn(){if(returnAfterSave_&&canReturn())queueReturn();}
void PracticeView::haltReturn(){
 ++returnGeneration_;returnAfterSave_=false;returnPosted_=false;returnPanel_=true;returnFailed_=true;
 showTab(tabMode_);refreshDisplay();
}
void PracticeView::queueReturn(){
 if(returnPosted_||!returnAfterSave_||!canReturn())return;
 returnPosted_=true;const auto generation=returnGeneration_;
 juce::Component::SafePointer<PracticeView> safe(this);
 juce::MessageManager::callAsync([safe,generation]{
  if(!safe||safe->returnGeneration_!=generation||!safe->returnAfterSave_)return;
  safe->returnPosted_=false;
  // Quiescing may expose late facts: recheck the full guard after draining and polling.
  if(!safe->canReturn()||!safe->requestClose()){safe->haltReturn();return;}
  if(!safe->output_.disconnect()){safe->error_=safe->output_.error();safe->haltReturn();return;}
  safe->drain();safe->serviceCapture();if(!safe->canReturn()){safe->haltReturn();return;}
  safe->returnAfterSave_=false;safe->returnPanel_=false;++safe->returnGeneration_;
  safe->audioHelp_.setText("Audio is disconnected. Connect audio, then Enable audio for your macOS speakers or headphones. Start begins sound. Audio settings are shared with Learn, Freeplay and rhythm tools; use Audio settings for output and mix, then Back to return to Practice without duplicating controls.",juce::dontSendNotification);
  safe->showTab(safe->tabMode_);safe->refreshDisplay();
  const auto callback=std::move(safe->requestedReturn_);safe->requestedReturn_={};
  if(callback)callback(); // The consumer may destroy this view; no access follows.
 });
}
void PracticeView::presentReturn(){
 const bool panel=returnPanel_;
 for(auto* component:std::initializer_list<juce::Component*>{&returnStatus_,&saveBack_,&retryBack_,&stay_})component->setVisible(panel);
 if(!panel)return;
 saveBack_.setButtonText(canReturn()?"Go back":"Save & go back");
 saveBack_.setEnabled(!returnPosted_&&!returnFailed_&&(canReturn()||canPerformCommand(PracticeCommand::Save)));
 retryBack_.setEnabled(!returnPosted_&&((returnFailed_&&canReturn())||canPerformCommand(PracticeCommand::Retry)));
 returnStatus_.setText(returnFailed_?"Return paused: cleanup or the original result needs attention. Stay keeps this view open; Retry is explicit.":canReturn()?"Result resolved. Completing your requested return.":canPerformCommand(PracticeCommand::Save)?"Return requested. Choose Save & go back explicitly to keep this result, or Stay to cancel the return. Self-assessment is optional.":returnAfterSave_?"Return requested. Waiting for the original result and audio cleanup to be confirmed. Stay cancels only the return.":"Waiting for the original result. Use Retry if needed; nothing is discarded.",juce::dontSendNotification);
}
void PracticeView::showCaptureStatus(){
 const auto p=capture_?capture_->phase():capture::SessionPhase::Idle;
 const bool review=capture_&&p==capture::SessionPhase::Review;
 assessment_.setVisible(!suiteMode_);clean_.setVisible(!suiteMode_);
 assessment_.setEnabled(review&&!suiteMode_);clean_.setEnabled(!suiteMode_&&canPerformCommand(PracticeCommand::Clean));save_.setEnabled(canPerformCommand(PracticeCommand::Save));retry_.setEnabled(canPerformCommand(PracticeCommand::Retry));again_.setEnabled(canPerformCommand(PracticeCommand::Again));
 PracticeGuidanceInput context;context.attached=static_cast<bool>(capture_);context.phase=p;context.outputCleared=outputCleared();
 context.canStart=canPerformCommand(PracticeCommand::Start);context.canSave=canPerformCommand(PracticeCommand::Save);
 if(lesson_&&p==capture::SessionPhase::Idle&&!started_)context.startPrerequisite=startPrerequisite(output_.status().lifecycle.state,context.canStart).second;
 context.canRetry=canPerformCommand(PracticeCommand::Retry);context.canAgain=canPerformCommand(PracticeCommand::Again);
 context.canStop=canPerformCommand(PracticeCommand::Stop);context.canConnect=canPerformCommand(PracticeCommand::Connect);context.canEnable=canPerformCommand(PracticeCommand::Enable);
 context.priorActivityBlocked=capture_&&(capture_->feedback().code=="ALLOCATION_REFUSED_PRIOR_ACTIVITY"||capture_->feedback().code=="ALLOCATION_REFUSED_STORE_UNCERTAIN");
 if(capture_){context.receipt=capture_->feedback().status;context.stopRequired=capture_->stopRequired();context.hasOwner=!capture_->binding().owner.empty();context.hasOriginal=capture_->original().has_value();context.canLeave=capture_->canLeave(true);}
 captureStatus_.setAdditionalDetails("\n\nPractice facts\n"+focusFacts_.getTooltip().toStdString()+(lesson_?"\n\nSelected lesson and source\n"+lessonLabel_:std::string{})+"\n\nSource and current state\n"+status_.getText().toStdString()+"\n\nGuitar setup\n"+setupSummary_.getText().toStdString()+"\n\nKeyboard help\n"+shortcutHelp_.getText().toStdString());
 captureStatus_.present(context,capture_?capture_->feedback():storage::Reply{},error_);
 if(auto* primary=dynamic_cast<juce::Label*>(captureStatus_.findChildWithID("practice-save-status"))){
  primary->setTooltip(primary->getText());

 }
}
void PracticeView::paint(juce::Graphics& g){g.fillAll(appearance::colour(0xff10212c));if(tabMode_||captureStatus_.detailsVisible()||tempoPanel_.isVisible())return;g.setColour(appearance::colour(0xff29404d));g.fillRect(40,lesson_?344:320,getWidth()-80,18);scheduler::FrameRatio duration;const bool known=scheduler::samples(config_.span,config_.rate,hasCurrentAttempt()?coordinator_.currentTempo():config_.bpm,config_.unit,duration);auto span=known?static_cast<double>(duration.n)/static_cast<double>(duration.d):0;
 if(hasCurrentAttempt()&&shown_.owner==coordinator_.owner()){const auto& map=coordinator_.timeline(shown_.owner);span=shown_.completedCycles<map.spec().cycles?static_cast<double>(map.frame(shown_.completedCycles+1)-map.frame(shown_.completedCycles)):0;}const auto phase=span>0?std::clamp(static_cast<double>(shown_.cursorFrames)/span,0.0,1.0):0;g.setColour(appearance::colour(0xff6bd5cb));g.fillRect(40,lesson_?344:320,static_cast<int>((getWidth()-80)*phase),18);}
void PracticeView::showTab(bool value){
 if(!value)playbackBoard_.setActiveEvents({});
 status_.setVisible(!value);
 if(focusMode_&&!value){setFocusMode(false);return;}
 setupSummary_.setVisible(static_cast<bool>(lesson_));setupButton_.setVisible(static_cast<bool>(lesson_));metronomeButton_.setVisible(!returnPanel_&&!focusMode_);
 title_.setText(lesson_?juce::String::fromUTF8(((focusMode_?"Focus | ":"")+lessonLabel_).c_str()):focusMode_?"Focus | Synthetic practice sample":value?"TAB: synthetic practice sample":"Practice capture preview",juce::dontSendNotification);
 refreshLessonHeading();
 title_.setFont(juce::FontOptions{lesson_&&lesson_->identity().find("selection")?16.0f:focusMode_?18.0f:28.0f,juce::Font::bold});
 tabMode_=value;tabView_.setCompact(value);tabView_.setVisible(value);tabModeButton_.setButtonText(value?"Show Results / transport":"Show TAB");tabModeButton_.setVisible(!focusMode_);
 description_.setVisible(!value);facts_.setVisible(!value);assessment_.setVisible(true);save_.setVisible(!returnPanel_);retry_.setVisible(!returnPanel_);again_.setVisible(!returnPanel_);
 clean_.setVisible(focusMode_&&!returnPanel_);focusFacts_.setVisible(focusMode_||static_cast<bool>(lesson_));shortcutHelp_.setVisible(focusMode_);connect_.setVisible(false);enable_.setVisible(false);audioHelp_.setVisible(!value);audioSettings_.setVisible(true);back_.setVisible(true);
 for(auto* button:{&start_,&pause_,&resume_,&stop_})button->setVisible(!returnPanel_||!focusMode_);presentReturn();
 showSaveDetails();
}
void PracticeView::refreshLessonHeading(){
 if(!lesson_)return;
 const auto full=(focusMode_?"Focus | ":"")+lessonLabel_;
 const auto caption=getWidth()>=900?(focusMode_?"Focus | ":"Practice | ")+lessonCaption_:full;
 title_.setText(juce::String::fromUTF8(caption.c_str()),juce::dontSendNotification);
 title_.setTooltip(juce::String::fromUTF8(full.c_str()));
}
void PracticeView::showSaveDetails(){
 const bool details=captureStatus_.detailsVisible();
 if(returnPanel_)tempoPanelOpen_=false;
 if(details)setupDetailsVisible_=false;
 if(details||setupDetailsVisible_)tempoPanelOpen_=false;
 setupButton_.setButtonText(setupDetailsVisible_?"Hide setup details":"Show setup details");setupDetails_.setVisible(setupDetailsVisible_&&static_cast<bool>(lesson_));
 tabView_.setVisible(tabMode_&&!details&&!setupDetailsVisible_&&!tempoPanelOpen_);facts_.setVisible(!tabMode_&&!details&&!setupDetailsVisible_&&!tempoPanelOpen_);
 refreshTempoControls();
 resized();repaint();
}

std::vector<PlaybackFretboardView::ActiveTone> PracticeView::soundingTonesAt(
 const music::ValidatedModel& model,const practice::Timeline& timeline,std::uint64_t cycle,std::uint64_t sample){
 std::vector<PlaybackFretboardView::ActiveTone> result;
 for(const auto& event:model.projections()){
  const bool pitched=event.kind==music::Kind::Note || event.kind==music::Kind::Chord ||
      (event.kind==music::Kind::Contact && event.contact==music::Contact::Pitched);
  if(!pitched)continue;
  for(const auto& tone:event.tones){
   if(!tone.soundingSpan.onset || !tone.soundingSpan.duration)continue;
   const auto begin=timeline.frame(cycle,*tone.soundingSpan.onset);
   const auto end=timeline.frame(cycle,*tone.soundingSpan.onset+*tone.soundingSpan.duration);
   if(begin<=sample && sample<end){
    PlaybackFretboardView::ActiveTone key{event.eventId,tone.string,tone.fret};
    if(std::find(result.begin(),result.end(),key)==result.end())result.push_back(std::move(key));
   }
  }
 }
 return result;
}
void PracticeView::clearBoardHighlight(){boardAcceptOutput_=false;playbackBoard_.setActiveEvents({});}
void PracticeView::visibilityChanged(){if(!isShowing())playbackBoard_.setActiveEvents({});}
void PracticeView::setBoardDisplay(const setup::BoardDisplay& value){
 setup::validateBoardDisplay(value);boardDisplay_=value;
 playbackBoard_.setMode(static_cast<PlaybackFretboardView::Mode>(value.mode));
 playbackBoard_.setSpelling(static_cast<PlaybackFretboardView::Spelling>(value.spelling));
 boardToggle_.setButtonText(value.visible?"Fretboard: On":"Fretboard: Off");
 boardMode_.setSelectedId(static_cast<int>(value.mode)+1,juce::dontSendNotification);
 boardSpelling_.setSelectedId(static_cast<int>(value.spelling)+1,juce::dontSendNotification);
 refreshBoardVisibility();resized();repaint();
}
void PracticeView::setBoardDisplayStatus(const std::string& text){
 boardDisplayStatus_.setText(juce::String::fromUTF8(text.c_str()),juce::dontSendNotification);
 boardDisplayStatus_.setTooltip(boardDisplayStatus_.getText()+"\nFretboard On and Show TAB display the board. Basic shows active fills; Finger shows authored fingers or ?; Note keeps a dim note map and emphasizes active positions. Active markers require accepted current playback and clear when paused or stopped. Declared tuning is not physical tuning detection.");
}
void PracticeView::refreshBoardVisibility(){
 const bool controls=tabMode_&&!returnPanel_&&!captureStatus_.detailsVisible()&&!setupDetailsVisible_&&!tempoPanelOpen_;
 for(auto* c:std::initializer_list<juce::Component*>{&boardToggle_,&boardMode_,&boardSpelling_,&boardDisplayStatus_})c->setVisible(controls);
 playbackBoard_.setVisible(controls&&boardDisplay_.visible);
 if(!playbackBoard_.isVisible())playbackBoard_.setActiveEvents({});
}
void PracticeView::layoutBoardOffControls(){
 if(!boardToggle_.isVisible())return;
 auto area=tabView_.getBounds();const int top=area.getY();
 notation_layout::row({area.getX(),top,area.getWidth(),28},{{&boardToggle_,140},{&boardMode_,110},{&boardSpelling_,100},{&boardDisplayStatus_,230}});
 area.removeFromTop(32);tabView_.setBounds(area);
}
bool PracticeView::layoutBoardOn(){
 if(!playbackBoard_.isVisible())return false;
 boardLayoutActive_=true;
 const int inset=12,inner=std::max(1,getWidth()-2*inset);const bool narrow=getWidth()<800;
 refreshLessonHeading();title_.setFont(juce::FontOptions{16.0f,juce::Font::bold});
 title_.setBounds(inset,4,inner-180,28);tabModeButton_.setBounds(getWidth()-180,4,168,28);
 presentationSelector_.setVisible(false);status_.setVisible(false);setupSummary_.setVisible(false);shortcutHelp_.setVisible(false);
 notation_layout::row({inset,36,inner,30},{{&audioSettings_,130},{&start_,120},{&pause_,80},{&resume_,85},{&stop_,110}});
 notation_layout::row({inset,70,inner,28},{{&setupButton_,130},{&tempoButton_,120},{&scheduledPasses_,140},{&beatClickButton_,140}});
 const int factsHeight=narrow?64:42;
 focusFacts_.setVisible(true);focusFacts_.setFont(juce::FontOptions{12.0f});focusFacts_.setBounds(inset,102,inner/2-4,factsHeight);
 captureStatus_.setBounds(inset+inner/2,102,inner/2,factsHeight);refreshFocusFacts();
 const int barTop=106+factsHeight;
 notation_layout::row({inset,barTop,inner,28},{{&boardToggle_,140},{&boardMode_,110},{&boardSpelling_,100},{&boardDisplayStatus_,230}});
 const int boardTop=barTop+32,boardHeight=narrow?142:154;
 playbackBoard_.setBounds(inset,boardTop,inner,boardHeight);
 const int tabTop=boardTop+boardHeight+4,bottom=88;
 tabView_.setBounds(8,tabTop,std::max(1,getWidth()-16),std::max(1,getHeight()-bottom-tabTop));
 const int saveTop=getHeight()-84;
 notation_layout::row({inset,saveTop,inner,30},{{&assessment_,160},{&clean_,80},{&save_,100},{&retry_,100},{&again_,80},{&guidedSummary_,130}});
 notation_layout::row({inset,getHeight()-46,inner,32},{{&back_,90},{&focus_,120},{&metronomeButton_,140},{&openProgress_,140},{&commandFeedback_,200}});
 captureStatus_.detailsView().setBounds(tabView_.getBounds());setupDetails_.setBounds(tabView_.getBounds());
 return true;
}
void PracticeView::resized(){
 refreshBoardVisibility();
 if(layoutBoardOn())return;
 if(boardLayoutActive_){
  title_.setFont(juce::FontOptions{lesson_&&lesson_->identity().find("selection")?16.0f:focusMode_?18.0f:28.0f,juce::Font::bold});
  applyFocusTextScale();boardLayoutActive_=false;
 }
 struct FinishBoardBar { PracticeView& view; ~FinishBoardBar(){view.layoutBoardOffControls();} } finishBoardBar{*this};
 presentationSelector_.setVisible(getWidth()>=900);presentationSelector_.setBounds(24,10,200,28);auto w=getWidth()-80;
 // TabView uses four compact header rows below 800px; its bounds inset is 16px.
 const bool compactTabFocus=focusMode_&&getWidth()>=620&&getWidth()<816&&!returnPanel_;
 auto order=[&](std::initializer_list<juce::Component*> controls){int index=1;for(auto* control:controls)control->setExplicitFocusOrder(index++);};
 if(focusMode_){
  if(compactTabFocus)order({&focus_,&audioSettings_,&back_,&beatClickButton_,&scheduledPasses_,&tempoButton_,&start_,&pause_,&resume_,&stop_,&assessment_,&clean_,&save_,&again_,&retry_,&setupButton_,&guidedSummary_,&openProgress_});
  else if(getWidth()<900)order({&focus_,&audioSettings_,&back_,&beatClickButton_,&scheduledPasses_,&tempoButton_,&start_,&pause_,&resume_,&stop_,&clean_,&save_,&again_,&assessment_,&retry_,&setupButton_,&guidedSummary_,&openProgress_});
  else order({&audioSettings_,&back_,&focus_,&scheduledPasses_,&tempoButton_,&start_,&pause_,&resume_,&stop_,&clean_,&save_,&again_,&assessment_,&retry_,&setupButton_,&beatClickButton_,&guidedSummary_,&openProgress_});
  tabModeButton_.setExplicitFocusOrder(0);metronomeButton_.setExplicitFocusOrder(0);
 }else{
  order({&back_,&audioSettings_,&tabModeButton_,&focus_,&start_,&pause_,&resume_,&stop_,&save_,&retry_,&again_,&guidedSummary_,&openProgress_,&clean_,&metronomeButton_,&tempoButton_});
  for(auto* control:{static_cast<juce::Component*>(&scheduledPasses_),static_cast<juce::Component*>(&beatClickButton_),static_cast<juce::Component*>(&assessment_),static_cast<juce::Component*>(&setupButton_)})control->setExplicitFocusOrder(0);
 }
 scheduledPasses_.setBounds(204,440,140,36);
 beatClickButton_.setBounds(654,498,226,36);
 if(getWidth()<800&&!focusMode_&&!tabMode_&&!returnPanel_){
  const int x=24;const int width=std::max(1,getWidth()-48);
  if(!lesson_&&title_.getText()==juce::String::fromUTF8("PRACTICE — EXPLICIT START & SAVE"))title_.setText(juce::String::fromUTF8("Practice — Explicit start & save"),juce::dontSendNotification);
  title_.setComponentID("practice-heading");title_.setBounds(x,12,250,34);tabModeButton_.setBounds(284,12,150,34);back_.setBounds(444,12,172,34);
  emptySourceState_.setBounds(x,50,width,24);description_.setBounds(x,78,width,50);audioHelp_.setBounds(x,132,width,44);status_.setBounds(x,180,width,64);facts_.setBounds(x,248,width,46);captureStatus_.setBounds(x,300,width,44);captureStatus_.detailsView().setBounds(x,300,width,44);commandFeedback_.setBounds(x,350,width,30);
  audioSettings_.setBounds(x,390,140,34);start_.setBounds(174,390,120,34);pause_.setBounds(302,390,88,34);resume_.setBounds(398,390,98,34);stop_.setBounds(504,390,112,34);
  assessment_.setBounds(x,434,140,34);save_.setBounds(174,434,110,34);retry_.setBounds(294,434,110,34);again_.setBounds(414,434,100,34);
  focus_.setBounds(x,478,150,34);metronomeButton_.setBounds(184,478,150,34);openProgress_.setBounds(344,478,140,34);guidedSummary_.setBounds(494,478,122,34);
  setupSummary_.setBounds(x,520,width-182,40);setupButton_.setBounds(getWidth()-206,520,182,34);tempoButton_.setBounds(x,564,120,30);scheduledPasses_.setBounds(152,564,140,30);beatClickButton_.setBounds(304,564,180,30);tabView_.setBounds(x,600,width,60);setupDetails_.setBounds(tabView_.getBounds());
  returnStatus_.setBounds(x,520,width,44);saveBack_.setBounds(x,570,176,34);retryBack_.setBounds(212,570,176,34);stay_.setBounds(400,570,100,34);
  return;
 }
 if((focusMode_||tabMode_)&&getWidth()>=900){
  const int inset=16,inner=getWidth()-2*inset;
  refreshLessonHeading();if(!lesson_)title_.setTooltip(title_.getText());presentationSelector_.setBounds(inset,8,200,28);title_.setBounds(inset+208,8,inner-426,28);tabModeButton_.setBounds(getWidth()-218,8,202,28);
  std::vector<std::pair<juce::Component*,int>> transport{{&audioSettings_,142},{&start_,94},{&pause_,68},{&resume_,82},{&stop_,68},{&setupButton_,130},{&tempoButton_,138},{&scheduledPasses_,150}};
  // The shared row scales weights. Reserve the current Stop caption's measured
  // width before distributing the rest, including while Practice is paused.
  int count=0,otherWeight=0;
  for(const auto& [control,weight]:transport)if(control->isVisible()){++count;if(control!=&stop_)otherWeight+=weight;}
  if(stop_.isVisible()&&otherWeight>0){
   const int available=std::max(1,inner-notation_layout::gap*(count-1));
   const int fitted=std::clamp(stop_.getLookAndFeel().getTextButtonWidthToFitText(stop_,34),1,std::max(1,available-count+1));
   const int remainder=std::max(1,available-fitted);
   for(auto& [control,weight]:transport)if(control==&stop_)weight=std::max(weight,(fitted*otherWeight+remainder-1)/remainder);
  }
  notation_layout::row({inset,42,inner,34},transport);
  // Independent state/Save areas and a dedicated bottom feedback row avoid
  // overlaying actionable controls; complete owner diagnostics stay in Details.
  status_.setVisible(false);captureStatus_.setBounds(inset+inner/2,78,inner/2,64);
  focusFacts_.setVisible(true);focusFacts_.setFont(juce::FontOptions{14.0f});focusFacts_.setBounds(inset,78,inner/2-8,64);
  refreshFocusFacts();
  setupSummary_.setVisible(false);shortcutHelp_.setVisible(false);
  const int extra=returnPanel_?46:0;
  const auto primary=notation_layout::workspace(getLocalBounds(),144,88+extra);
  tabView_.setBounds(primary);captureStatus_.detailsView().setBounds(primary);setupDetails_.setBounds(primary);
  const int y=getHeight()-84;
  if(returnPanel_){
   returnStatus_.setBounds(inset,y-44,inner,38);
   notation_layout::row({inset,y,inner,34},{{&assessment_,200},{&saveBack_,180},{&retryBack_,180},{&stay_,100}});
  }else notation_layout::row({inset,y,inner,34},{{&assessment_,174},{&clean_,84},{&save_,94},{&retry_,112},{&again_,88},{&guidedSummary_,150},{&beatClickButton_,184}});
  auto nav=juce::Rectangle<int>{inset,getHeight()-42,inner,34};
  back_.setBounds(nav.removeFromLeft(92));nav.removeFromLeft(8);focus_.setBounds(nav.removeFromLeft(132));nav.removeFromLeft(8);
  if(metronomeButton_.isVisible()){metronomeButton_.setBounds(nav.removeFromLeft(180));nav.removeFromLeft(8);}
  if(openProgress_.isVisible()){openProgress_.setBounds(nav.removeFromLeft(150));nav.removeFromLeft(8);}
  commandFeedback_.setBounds(nav);commandFeedback_.setTooltip(commandFeedback_.getText());
  layoutTempoControls();applyFocusTextScale();return;
 }
 if(!lesson_&&!focusMode_&&!tabMode_&&!returnPanel_&&title_.getText().startsWith("Practice")&&title_.getText().contains("Explicit start & save"))title_.setText(juce::String::fromUTF8("PRACTICE — EXPLICIT START & SAVE"),juce::dontSendNotification);
 if(focusMode_&&getWidth()<900){
  const int inner=getWidth()-40, gap=8;
  const int four=(inner-3*gap)/4, three=(inner-2*gap)/3;
  const int controlsTop=getHeight()-(compactTabFocus?88:164);
  if(lesson_){const auto& identity=lesson_->identity().object();const auto item=identity.at("item_id").string(),variant=identity.at("variant_id").string();const auto full="Focus | "+item+" / "+variant;title_.setTooltip(juce::String::fromUTF8(full.c_str()));title_.setText(juce::String::fromUTF8((tabView_.zoom()>1.0?"Focus | "+item.substr(item.rfind(':')+1)+" / "+variant.substr(variant.rfind(':')+1):full).c_str()),juce::dontSendNotification);}
  else title_.setText("Focus | Synthetic practice sample",juce::dontSendNotification);
  setupSummary_.setVisible(false);
  title_.setBounds(20,10,getWidth()-230,32);focus_.setBounds(getWidth()-190,10,170,32);
  audioSettings_.setBounds(20,50,158,32);back_.setBounds(190,50,104,32);beatClickButton_.setBounds(310,50,getWidth()-330,32);
  focusFacts_.setBounds(20,88,inner,60);
  scheduledPasses_.setBounds(20,154,190,34);tempoButton_.setBounds(getWidth()-144,154,124,28);
  status_.setBounds(20,194,inner,56);captureStatus_.setBounds(20,252,inner,38);commandFeedback_.setBounds(20,292,inner,46);
  const int tabBottom=returnPanel_?controlsTop-56:controlsTop-12;
  tabView_.setBounds(8,340,getWidth()-16,std::max(1,tabBottom-340));captureStatus_.detailsView().setBounds(tabView_.getBounds());setupDetails_.setBounds(tabView_.getBounds());
  shortcutHelp_.setVisible(!compactTabFocus);
  if(compactTabFocus){
   const int span=inner-4*gap;
   const int a=span*120/568,b=span*90/568,c=span*100/568,d=span*90/568,e=span-a-b-c-d;
   int x=20;for(const auto pair:{std::pair<juce::Component*,int>{&start_,a},{&pause_,b},{&resume_,c},{&stop_,d},{&assessment_,e}}){pair.first->setBounds(x,controlsTop,pair.second,36);x+=pair.second+gap;}
   const int q=span*105/568,r=span-4*q;
   x=20;for(const auto pair:{std::pair<juce::Component*,int>{&clean_,q},{&save_,q},{&again_,q},{&retry_,q},{&setupButton_,r}}){pair.first->setBounds(x,controlsTop+44,pair.second,36);x+=pair.second+gap;}
   layoutTempoControls();applyFocusTextScale();return;
  }
  int x=20;for(auto* b:{&start_,&pause_,&resume_,&stop_}){b->setBounds(x,controlsTop,four,36);x+=four+gap;}
  x=20;for(auto* b:{&clean_,&save_,&again_}){b->setBounds(x,controlsTop+42,three,36);x+=three+gap;}
  assessment_.setBounds(20,controlsTop+84,three,34);retry_.setBounds(20+three+gap,controlsTop+84,three,34);setupButton_.setBounds(20+2*(three+gap),controlsTop+84,three,34);
  shortcutHelp_.setBounds(20,controlsTop+122,inner,38);
  if(returnPanel_){
   returnStatus_.setBounds(20,controlsTop-48,inner,40);
   assessment_.setBounds(20,controlsTop,three,36);saveBack_.setBounds(20+three+gap,controlsTop,three,36);retryBack_.setBounds(20+2*(three+gap),controlsTop,three,36);stay_.setBounds(20,controlsTop+42,three,36);
  }
  layoutTempoControls();applyFocusTextScale();return;
 }
 if(focusMode_){
  shortcutHelp_.setVisible(true);
  if(lesson_){const auto& identity=lesson_->identity().object();const auto item=identity.at("item_id").string(),variant=identity.at("variant_id").string();const auto full="Focus | "+item+" / "+variant;title_.setTooltip(juce::String::fromUTF8(full.c_str()));title_.setText(juce::String::fromUTF8((tabView_.zoom()>1.0?"Focus | "+item.substr(item.rfind(':')+1)+" / "+variant.substr(variant.rfind(':')+1):full).c_str()),juce::dontSendNotification);}
  else title_.setText("Focus | Synthetic practice sample",juce::dontSendNotification);
  refreshFocusFacts();setupSummary_.setVisible(static_cast<bool>(lesson_));
  scheduledPasses_.setBounds(getWidth()-210,114,190,34);
  beatClickButton_.setBounds(604,getHeight()-84,270,34);
  title_.setBounds(20,10,getWidth()-500,32);audioSettings_.setBounds(getWidth()-480,10,158,32);back_.setBounds(getWidth()-310,10,104,32);focus_.setBounds(getWidth()-190,10,170,32);
  focusFacts_.setBounds(20,50,getWidth()-40,60);setupSummary_.setBounds(20,114,getWidth()-240,38);status_.setBounds(20,158,getWidth()-184,52);captureStatus_.setBounds(20,214,getWidth()-40,42);commandFeedback_.setBounds(20,262,getWidth()-40,42);
  const int tabTop=310,controlsTop=getHeight()-128;
  tabView_.setBounds(8,tabTop,getWidth()-16,std::max(1,controlsTop-(returnPanel_?56:12)-tabTop));captureStatus_.detailsView().setBounds(tabView_.getBounds());setupDetails_.setBounds(tabView_.getBounds());
  const int y=getHeight()-128;int x=20;
  for(auto* b:{&start_,&pause_,&resume_,&stop_,&clean_,&save_,&again_}){b->setBounds(x,y,116,36);x+=124;}
  assessment_.setBounds(20,y+44,220,34);retry_.setBounds(248,y+44,155,34);setupButton_.setBounds(416,y+44,174,34);shortcutHelp_.setBounds(20,y+82,getWidth()-40,42);
  tempoButton_.setBounds(getWidth()-144,166,124,28);layoutTempoControls();applyFocusTextScale();
  if(returnPanel_){returnStatus_.setBounds(20,getHeight()-174,getWidth()-40,42);assessment_.setBounds(20,y,220,36);saveBack_.setBounds(252,y,176,36);retryBack_.setBounds(440,y,176,36);stay_.setBounds(628,y,100,36);}return;
 }
 focus_.setBounds(24,getHeight()-50,170,34);commandFeedback_.setBounds(204,getHeight()-50,getWidth()-228,34);
 if(tabMode_){
 scheduledPasses_.setBounds(getWidth()-214,lesson_?250:222,190,34);
 beatClickButton_.setBounds(670,getHeight()-96,226,34);
 title_.setBounds(24,10,w-160,34);tabModeButton_.setBounds(getWidth()-210,12,186,32);
 status_.setBounds(24,46,getWidth()-48,lesson_?72:44);captureStatus_.setBounds(24,lesson_?124:96,getWidth()-48,52);
 const int controlsY=lesson_?236:148;const int factsTop=lesson_?184:148;focusFacts_.setBounds(24,factsTop,getWidth()-48,44);
 audioSettings_.setBounds(24,controlsY,158,34);start_.setBounds(194,controlsY,125,34);pause_.setBounds(331,controlsY,85,34);resume_.setBounds(428,controlsY,88,34);stop_.setBounds(528,controlsY,80,34);
 setupButton_.setBounds(620,controlsY,174,34);setupSummary_.setBounds(24,lesson_?278:238,getWidth()-252,38);
 const int y=getHeight()-96;const int tabTop=lesson_?326:188;tabView_.setBounds(8,tabTop,getWidth()-16,std::max(1,y-tabTop-10-(returnPanel_?44:0)));captureStatus_.detailsView().setBounds(tabView_.getBounds());setupDetails_.setBounds(tabView_.getBounds());
  assessment_.setBounds(24,y,218,34);save_.setBounds(254,y,126,34);retry_.setBounds(392,y,144,34);again_.setBounds(548,y,110,34);guidedSummary_.setBounds(666,y,170,34);openProgress_.setBounds(340,getHeight()-50,180,34);
 returnStatus_.setBounds(24,y-42,getWidth()-48,38);saveBack_.setBounds(254,y,176,34);retryBack_.setBounds(442,y,176,34);stay_.setBounds(630,y,100,34);
 back_.setBounds(24,getHeight()-50,100,34);focus_.setBounds(136,getHeight()-50,170,34);commandFeedback_.setBounds(318,getHeight()-50,getWidth()-342,34);metronomeButton_.setBounds(590,getHeight()-50,190,34);tempoButton_.setBounds(806,controlsY,90,34);layoutTempoControls();return;}

 const bool savedLesson=capture_&&capture_->phase()==capture::SessionPhase::Saved&&static_cast<bool>(lesson_);const int statusTop=lesson_?242:180;const int statusHeight=savedLesson?112:lesson_?72:50;const int captureTop=savedLesson?360:lesson_?320:235;const int detailTop=savedLesson?419:lesson_?379:315;status_.setFont(juce::FontOptions{savedLesson?14.0f:15.0f});tabModeButton_.setBounds(getWidth()-210,30,170,34);title_.setBounds(40,25,w,45);emptySourceState_.setBounds(40,74,w,24);description_.setBounds(40,lesson_?78:104,w,lesson_?65:36);audioHelp_.setBounds(40,144,w,42);focusFacts_.setBounds(40,145,w,44);setupSummary_.setBounds(40,196,w-180,42);setupButton_.setBounds(getWidth()-214,196,174,34);status_.setBounds(40,statusTop,w,statusHeight);facts_.setBounds(40,savedLesson?419:lesson_?382:365,w,lesson_?45:55);captureStatus_.setBounds(40,captureTop,w,lesson_?52:70);captureStatus_.detailsView().setBounds(40,detailTop,w,lesson_?82:112);setupDetails_.setBounds(40,savedLesson?419:lesson_?351:335,w,lesson_?82:92);audioSettings_.setBounds(40,440,158,36);start_.setBounds(355,440,130,36);pause_.setBounds(495,440,90,36);resume_.setBounds(595,440,95,36);stop_.setBounds(700,440,80,36);assessment_.setBounds(40,498,205,36);save_.setBounds(255,498,125,36);retry_.setBounds(390,498,140,36);again_.setBounds(540,498,100,36);guidedSummary_.setBounds(650,498,170,36);openProgress_.setBounds(340,getHeight()-100,180,36);back_.setBounds(40,getHeight()-100,100,36);metronomeButton_.setBounds(160,getHeight()-100,170,36);
 if(getWidth()>=900){refreshLessonHeading();title_.setBounds(232,10,getWidth()-450,34);tabModeButton_.setBounds(getWidth()-210,10,186,32);}
 tempoButton_.setBounds(790,440,90,36);layoutTempoControls();
 if(!lesson_){status_.setBounds(40,180,w,62);captureStatus_.setBounds(40,247,w,70);captureStatus_.detailsView().setBounds(40,327,w,112);}
 if(returnPanel_){audioSettings_.setBounds(getWidth()-220,getHeight()-100,180,36);returnStatus_.setBounds(40,427,w,62);saveBack_.setBounds(255,498,176,36);retryBack_.setBounds(443,498,176,36);stay_.setBounds(631,498,100,36);for(auto* button:{&connect_,&enable_,&start_,&pause_,&resume_,&stop_})button->setVisible(false);}
}
}
