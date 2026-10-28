#include "desktop/Appearance.hpp"
#include "desktop/MetronomeView.hpp"
#include "desktop/MetronomeFaultGuidance.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "content/Canonical.hpp"
#include <charconv>
#include <algorithm>

namespace fathom::desktop {
namespace {
int integer(const juce::TextEditor& editor,const char* label){
 const auto text=editor.getText().trim().toStdString();int n{};
 const auto parsed=std::from_chars(text.data(),text.data()+text.size(),n);
 if(text.empty()||parsed.ec!=std::errc{}||parsed.ptr!=text.data()+text.size())throw std::runtime_error(std::string(label)+": enter a whole number, without units or trailing text.");return n;
}
void supported(const metronome::Settings& s){metronome::validate(s);if(s.polyrhythmEnabled){if(s.countIn!=metronome::CountIn::Off||s.ramp)throw std::runtime_error("Polyrhythm preview requires count-in Off and ramp Off in this bounded desktop slice.");}else if(s.countIn==metronome::CountIn::AuthoredBar)throw std::runtime_error("Authored count-in requires a source task. Choose configured bar or Off for this sound check.");}
scheduler::Owner newOwner(std::uint64_t epoch){scheduler::Owner o;o.epoch=epoch;o.generation=1;const auto id=storage::newUuid();std::size_t at=0;int nibble=-1;for(char c:id){if(c=='-')continue;const auto v=c>='a'?c-'a'+10:c-'0';if(nibble<0)nibble=v;else{o.id[at++]=static_cast<std::uint8_t>(nibble*16+v);nibble=-1;}}return o;}
std::int64_t number(const json::Value& v,const char* key){std::int64_t n{};if(!v.find(key)||!v.find(key)->integer(n))throw std::runtime_error("Malformed preference receipt");return n;}
std::string patternLabel(const metronome::Settings& s){return s.polyrhythmEnabled?"Polyrhythm "+std::to_string(s.x)+":"+std::to_string(s.y):"Standard metronome";}
}
double MetronomeView::GainSlider::getValueFromText(const juce::String& source){invalidText_=false;auto value=source.trim().toStdString();if(!value.empty()&&value.back()=='%')value.pop_back();int n{};const auto r=std::from_chars(value.data(),value.data()+value.size(),n);if(value.empty()||r.ec!=std::errc{}||r.ptr!=value.data()+value.size()||n<0||n>100){invalidText_=true;if(onInvalidText)onInvalidText();return getValue();}return n;}
MetronomeView::MetronomeView():playback_(std::make_unique<platform::MetronomePlayback>()){
 title_.setText(juce::String::fromUTF8("METRONOME — TIMED SOUND-CHECK PREVIEW"),juce::dontSendNotification);title_.setFont(juce::FontOptions{26.0f,juce::Font::bold});
 description_.setText("Audio settings are shared across Learn, Practice, Freeplay and Rhythm; Start begins sound.\nSettings only; no practice result. Stop retains the check; Finish releases it. Space: transport; Esc: stop.",juce::dontSendNotification);
 profileState_.setComponentID("metronome-profile-state");profileState_.setTitle("Metronome profile-boundary marker.");profileState_.setFont(juce::FontOptions{15.0f,juce::Font::bold});profileState_.setColour(juce::Label::textColourId,appearance::colour(0xffffd479));profileState_.setText("No test profile attached; preset settings remain unsaved.",juce::dontSendNotification);
 status_.setTitle("Output state and next action");prefStatus_.setTitle("Saved settings state and recovery action");
 for(auto* l:{&title_,&description_,&status_,&facts_,&tempoStatus_,&prefStatus_,&profileState_}){addAndMakeVisible(*l);l->setMinimumHorizontalScale(1.0f);}
 for(auto* e:{&tempo_,&numerator_,&step_,&every_,&target_,&polyX_,&polyY_,&manual_,&presetName_}){addAndMakeVisible(*e);e->setSelectAllWhenFocused(true);e->onEscapeKey=[this]{stopSound();};}
 for(auto* c:{&meter_,&denominator_,&subdivision_,&unit_,&countIn_,&ramp_,&presetChoice_})addAndMakeVisible(*c);
 int id=1;for(const auto& m:metronome::commonMeters())meter_.addItem(juce::String(m.first)+"/"+juce::String(m.second),id++);meter_.addItem("Custom",9);
 for(int n:{2,4,8,16})denominator_.addItem(juce::String(n),n);
 for(int n=1;n<=7;++n)subdivision_.addItem(juce::String(n),n);
 unit_.addItem("Eighth",1);unit_.addItem("Quarter",2);unit_.addItem("Dotted quarter",3);unit_.addItem("Half",4);
 countIn_.addItem("One configured bar",1);countIn_.addItem("Off",2);
 ramp_.addItem("Ramp off",1);ramp_.addItem("Step up",2);ramp_.addItem("Step down",3);
 for(auto& s:styles_){addAndMakeVisible(s);s.addItem("Accent",1);s.addItem("Normal",2);s.addItem("Silent",3);}
 meter_.onChange=[this]{const auto i=meter_.getSelectedId();if(i>0&&i<=8){const auto m=metronome::commonMeters()[static_cast<std::size_t>(i-1)];numerator_.setText(juce::String(m.first));denominator_.setSelectedId(m.second,juce::dontSendNotification);}};
 for(auto* b:{&apply_,&connect_,&enable_,&start_,&pause_,&resume_,&stop_,&finish_,&reset_,&back_,&tapButton_,&applyTap_,&applyManual_,&saveLast_,&restoreLast_,&savePreset_,&replacePreset_,&restorePreset_,&reconcile_,&retry_,&keepStored_,&reopen_}){addAndMakeVisible(*b);b->addKeyListener(this);}
 for(auto* b:{&audioSettings_,&apply_,&connect_,&enable_,&start_,&pause_,&resume_,&stop_,&finish_,&reset_,&back_,&tapButton_,&applyTap_,&applyManual_,&saveLast_,&restoreLast_,&savePreset_,&replacePreset_,&restorePreset_,&reconcile_,&retry_,&keepStored_,&reopen_}){b->setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));b->setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));b->setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));}
 reopen_.setTitle("Reopen test profile");reopen_.setTooltip("Reopen the same test profile after a saved-settings failure.");
 addAndMakeVisible(enabled_);addAndMakeVisible(polyrhythm_);polyrhythm_.setTitle("Polyrhythm layers (X:Y)");addAndMakeVisible(mute_);
 addAndMakeVisible(reducedMotion_);reducedMotion_.setComponentID("metronome-reduce-motion");reducedMotion_.setTitle("Reduce motion in Metronome progress");reducedMotion_.setTooltip("Space toggles this option while focused. Keep the progress bar still; callback-confirmed time and completed bars continue below.");reducedMotion_.setColour(juce::ToggleButton::textColourId,appearance::colour(0xffffffff));reducedMotion_.addKeyListener(this);reducedMotion_.onClick=[this]{repaint();};
 for(auto* slider:{&masterGain_,&clickGain_}){addAndMakeVisible(*slider);slider->setRange(0,100,1);slider->setSliderStyle(juce::Slider::LinearHorizontal);slider->setTextBoxStyle(juce::Slider::TextBoxRight,false,40,24);slider->setTextValueSuffix("%");slider->onInvalidText=[this]{error_="Gain: enter a whole percentage from 0 to 100. Prior gain retained.";};}
 masterGain_.onValueChange=[this]{setMix(static_cast<int>(masterGain_.getValue()),static_cast<int>(clickGain_.getValue()),mute_.getToggleState());};clickGain_.onValueChange=masterGain_.onValueChange;mute_.onClick=masterGain_.onValueChange;
 apply_.onClick=[this]{applyEditors();};connect_.onClick=[this]{connectOutput();};enable_.onClick=[this]{enableOutput();};start_.onClick=[this]{startSound();};pause_.onClick=[this]{pauseSound();};resume_.onClick=[this]{resumeSound();};stop_.onClick=[this]{stopSound();};finish_.onClick=[this]{finishSound();};reset_.onClick=[this]{resetSound();};back_.onClick=[this]{if(!onBack){error_="Back is unavailable from Metronome until the existing Home navigation is connected. Return to Home to continue; no sound check, preference write or curriculum activity was changed.";refresh();return;}if(requestClose())onBack();};
 tapButton_.onClick=[this]{tap(platform::monotonicNs());};applyTap_.onClick=[this]{applyTap();};applyManual_.onClick=[this]{try{manualTempo(integer(manual_,"Manual BPM"));}catch(const std::exception& e){error_=e.what();}};
 saveLast_.onClick=[this]{saveLastUsed();};restoreLast_.onClick=[this]{restoreLastUsed();};savePreset_.onClick=[this]{savePreset(presetName_.getText().toStdString());};
 auto selected=[this]()->std::string{const auto i=presetChoice_.getSelectedId();return i>0&&static_cast<std::size_t>(i)<=presetIds_.size()?presetIds_[static_cast<std::size_t>(i-1)]:"";};
 replacePreset_.onClick=[this,selected]{const auto id=selected();if(!id.empty())savePreset(presetName_.getText().toStdString(),id);};restorePreset_.onClick=[this,selected]{restorePreset(selected());};
 reconcile_.onClick=[this]{reconcilePreferences();};retry_.onClick=[this]{retryOriginalPreferences();};keepStored_.onClick=[this]{keepStoredPreferences();};reopen_.onClick=[this]{if(onReopenStore&&!onReopenStore())preferenceMessage_="Profile reopen was not completed. Original proposal retained; finish any practice outcome, then retry Reopen test profile.";};
 auto caption=[this](juce::Component& c,const char* name){c.setTitle(name);auto label=std::make_unique<juce::Label>();label->setText(name,juce::dontSendNotification);label->setFont(juce::FontOptions{12.0f});label->attachToComponent(&c,false);addAndMakeVisible(*label);captions_.push_back(std::move(label));};
 caption(tempo_,"Selected BPM");caption(unit_,"BPM beat unit");caption(meter_,"Common meter");caption(numerator_,"Beats / bar");caption(denominator_,"Beat value");caption(subdivision_,"Parts / beat");caption(countIn_,"Count-in");
 caption(ramp_,"Stepped tempo");caption(step_,"BPM step");caption(every_,"Every bars");caption(target_,"Target BPM");caption(polyX_,"Layer A count");caption(polyY_,"Layer B count");caption(manual_,"Live BPM");caption(presetName_,"Preset name");caption(presetChoice_,"Saved presets");
 for(std::size_t i=0;i<styles_.size();++i){const auto name="Beat "+std::to_string(i+1);caption(styles_[i],name.c_str());}
 connect_.setVisible(false);enable_.setVisible(false);masterGain_.setVisible(false);clickGain_.setVisible(false);mute_.setVisible(false);
 addAndMakeVisible(audioSettings_);audioSettings_.onClick=[this]{
  if(onAudioSettings){onAudioSettings();return;}
  error_="Audio settings are unavailable from Metronome until the existing shared Audio destination is connected. Return to Home and choose Audio settings; no Metronome sound was started.";
  refresh();
 };
 int focusOrder=1;auto focus=[&](juce::Component& component){component.setExplicitFocusOrder(focusOrder++);};
 focus(back_);for(auto* component:std::initializer_list<juce::Component*>{&tempo_,&unit_,&meter_,&numerator_,&denominator_,&subdivision_,&countIn_})focus(*component);
 for(auto& style:styles_)focus(style);
 for(auto* component:std::initializer_list<juce::Component*>{&ramp_,&step_,&every_,&target_,&enabled_,&apply_,&polyrhythm_,&polyX_,&polyY_})focus(*component);
 for(auto* component:std::initializer_list<juce::Component*>{&audioSettings_,&connect_,&enable_,&masterGain_,&clickGain_,&mute_,&start_,&pause_,&resume_,&stop_,&finish_,&reset_,&reducedMotion_})focus(*component);
 for(auto* component:std::initializer_list<juce::Component*>{&manual_,&applyManual_,&tapButton_,&applyTap_,&presetName_,&savePreset_,&presetChoice_,&replacePreset_,&restorePreset_,&saveLast_,&restoreLast_,&reconcile_,&retry_,&keepStored_,&reopen_})focus(*component);
 // Optional controls share a named scrolling region. Transport and save recovery
 // remain direct page children, so collapsing it cannot hide an owned outcome.
 advancedViewport_.setComponentID("metronome-advanced-controls");
 advancedViewport_.setName("Advanced musical controls");
 advancedViewport_.setTitle("Advanced musical controls; scroll vertically for all settings");
 advancedViewport_.setDescription("Beat unit, custom meter, subdivisions, beat styles, tempo steps, polyrhythm, live tempo and saved presets. Scroll vertically; changes require their existing explicit actions.");
 advancedViewport_.setViewedComponent(&advancedContent_,false);
 advancedViewport_.setScrollBarsShown(true,false);advancedViewport_.setScrollBarThickness(14);
 addChildComponent(advancedViewport_);
 auto optional=[this](juce::Component& component){advancedContent_.addAndMakeVisible(component);};
 for(auto* component:std::initializer_list<juce::Component*>{&unit_,&numerator_,&denominator_,&subdivision_,&countIn_,&ramp_,&step_,&every_,&target_,&enabled_,&polyrhythm_,&polyX_,&polyY_,&manual_,&applyManual_,&tapButton_,&applyTap_,&tempoStatus_,&presetName_,&savePreset_,&presetChoice_,&replacePreset_,&restorePreset_,&saveLast_,&restoreLast_})optional(*component);
 for(auto& style:styles_)optional(style);
 for(std::size_t i=0;i<captions_.size();++i)if(i!=0&&i!=2)optional(*captions_[i]);
 for(auto* label:{&description_,&status_,&facts_,&prefStatus_,&presentationBadge_,&patternSummary_,&advancedHeading_}){label->setFont(juce::FontOptions{16.0f});label->setJustificationType(juce::Justification::topLeft);label->setMinimumHorizontalScale(1.0f);}
 presentationBadge_.setComponentID("metronome-presentation-level");presentationBadge_.setTitle("Inherited Metronome presentation level");addAndMakeVisible(presentationBadge_);
 patternSummary_.setComponentID("metronome-current-pattern");patternSummary_.setTitle("Applied metronome pattern; editor values change only when Apply pattern succeeds");addAndMakeVisible(patternSummary_);
 advancedHeading_.setText("Advanced musical controls",juce::dontSendNotification);advancedHeading_.setFont(juce::FontOptions{18.0f,juce::Font::bold});optional(advancedHeading_);
 advancedControls_.setComponentID("metronome-advanced-disclosure");advancedControls_.setTitle("Advanced controls");advancedControls_.setTooltip("Show or hide musical controls. This does not apply settings, start sound or write a profile.");advancedControls_.setColour(juce::ToggleButton::textColourId,appearance::colour(0xffffffff));advancedControls_.addKeyListener(this);addAndMakeVisible(advancedControls_);
 advancedControls_.onClick=[this]{showingDetails_=false;refreshDisclosure();resized();};
 detailsButton_.setComponentID("metronome-instructions-disclosure");detailsButton_.setTitle("Instructions and current Metronome details");detailsButton_.setTooltip("Read the complete instructions and current permitted sound-check and saved-settings messages. No action is taken.");detailsButton_.addKeyListener(this);addAndMakeVisible(detailsButton_);
 detailsButton_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));detailsButton_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));detailsButton_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
 detailsButton_.onClick=[this]{showingDetails_=!showingDetails_;refreshDetails();refreshDisclosure();resized();};
 for(auto* editor:{&instructions_,&details_}){editor->setMultiLine(true,true);editor->setReadOnly(true);editor->setScrollbarsShown(true);editor->setFont(juce::FontOptions{16.0f});editor->setColour(juce::TextEditor::backgroundColourId,appearance::colour(0xff172f3c));editor->setColour(juce::TextEditor::textColourId,appearance::colour(0xffffffff));}
 instructions_.setComponentID("metronome-complete-instructions");instructions_.setName("Complete Metronome instructions");instructions_.setTitle("Complete Metronome instructions; read-only, scroll vertically");
 instructions_.setText("Instructions\nAudio settings are shared across Learn, Practice, Freeplay and Rhythm; Start begins sound.\nSettings only; no practice result. Stop retains the check; Finish releases it. Space: transport; Esc: stop.\n\nSet BPM and time signature, then choose Apply pattern while stopped and resolved. Custom time signatures, beat unit, subdivisions, count-in, beat styles, tempo steps and polyrhythm are in Advanced controls. Opening or closing these controls never applies their values.\n\nA live tempo request uses Queue BPM. Tap at least four steady beats from 20 to 300 BPM, then choose Apply tap explicitly while running. A queued request waits for its callback decision.\n\nSaved timing settings require an open local profile. Save and Restore are separate explicit actions; Restore keeps sound stopped. Pending saves retain the original proposal until supported recovery resolves it.\n\nReduce motion keeps the progress bar still. Confirmed running time and completed bars remain in text. Neither sound-check time nor playback verifies guitar performance or accuracy.",false);optional(instructions_);
 details_.setComponentID("metronome-current-details");details_.setName("Metronome instructions and current details");details_.setTitle("Metronome instructions and current details; read-only, scroll vertically");addChildComponent(details_);
 title_.setWantsKeyboardFocus(true);title_.setTitle("Metronome page heading");
 // Explicit order follows the new visible primary rows, then optional settings.
 focusOrder=1;focus(back_);focus(advancedControls_);focus(detailsButton_);focus(tempo_);focus(meter_);focus(apply_);
 for(auto* component:std::initializer_list<juce::Component*>{&audioSettings_,&start_,&pause_,&resume_,&stop_,&finish_,&reset_,&reducedMotion_,&reconcile_,&retry_,&keepStored_,&reopen_})focus(*component);
 for(auto* component:std::initializer_list<juce::Component*>{&unit_,&numerator_,&denominator_,&subdivision_,&countIn_})focus(*component);
 for(auto& style:styles_)focus(style);
 for(auto* component:std::initializer_list<juce::Component*>{&ramp_,&step_,&every_,&target_,&enabled_,&polyrhythm_,&polyX_,&polyY_,&manual_,&applyManual_,&tapButton_,&applyTap_,&presetName_,&savePreset_,&presetChoice_,&replacePreset_,&restorePreset_,&saveLast_,&restoreLast_,&instructions_,&details_})focus(*component);
 loadEditors();setWantsKeyboardFocus(true);startTimer(20);refresh();refreshDisclosure();
}
MetronomeView::~MetronomeView(){quiesceAndRetain();}
void MetronomeView::setPresentationLevel(presentation::Level level){
 presentation::validateLevel(level);if(level==presentationLevel_)return;
 auto* focused=juce::Component::getCurrentlyFocusedComponent();
 const bool hidesFocused=level==presentation::Level::Beginner&&focused&&advancedContent_.isParentOf(focused);
 presentationLevel_=level;advancedControls_.setToggleState(level!=presentation::Level::Beginner,juce::dontSendNotification);showingDetails_=false;
 refreshDetails();refreshDisclosure();resized();
 if(hidesFocused&&isShowing())title_.grabKeyboardFocus();
}
juce::String MetronomeView::preferencePrimaryText()const{
 switch(prefState_){
  case PrefState::Detached:return "No local profile is open. Saved timing settings are unavailable.";
  case PrefState::Reading:return "Reading saved timing settings. Audio remains stopped.";
  case PrefState::Writing:return "Saving timing settings. Keep this profile open until the save is confirmed.";
  case PrefState::Reconciling:return "Checking the original settings save. Keep this profile open.";
  case PrefState::Conflict:return retryProven_?"The original save is not stored at the checked revision. Retry original or Keep stored explicitly.":"A different saved revision was found. Keep stored or check the original save again; no automatic overwrite.";
  case PrefState::Unsupported:return "Saved timing settings are not supported. Stored bytes are unchanged; no settings were applied. Use the available recovery action below.";
  case PrefState::Failed:
   if(reopenPending_)return "Reopening the same local profile. The original settings proposal is retained.";
   if(!pendingOperation_.empty())return store_?"Settings save is not confirmed. Keep this profile open and use the available recovery action below. Details retain the reason.":"Settings save is not confirmed. The original proposal is retained; use the available recovery action below. Details retain the reason.";
   return "Saved settings could not be read. Use the available recovery action below. Details retain the reason.";
  case PrefState::Ready:{
   const auto applied=storage::canonical(metronome::encodeSettings(settings()));
   std::string lifetime="Applied pattern is session-only. Save last used or a preset to retain it.";
   if(revision_>0){
    if(applied==storage::canonical(metronome::encodeSettings(preferences_.lastUsed)))lifetime="Applied pattern matches saved last used.";
    else for(const auto& preset:preferences_.presets)if(applied==storage::canonical(metronome::encodeSettings(preset.settings))){lifetime="Applied pattern matches a saved preset; last used is unchanged.";break;}
   }
   return juce::String(lifetime+"\n"+preferenceMessage_);
  }
 }
 return juce::String(preferenceMessage_);
}
void MetronomeView::refreshDetails(){
 const auto heading=presentationLevel_==presentation::Level::Developer?"\n\nCurrent permitted diagnostics\n":"\n\nCurrent sound-check and saved-settings details\n";
 const juce::String value=instructions_.getText()+heading+fullFacts_+"\n"+fullTempoStatus_+"\n"+status_.getText()+"\n"+juce::String(preferenceMessage_)+(error_.empty()?juce::String{}:"\nExisting output/settings message: "+juce::String(error_));
 if(details_.getText()!=value){
  // Live counters may change while instructions are being read. Retain the
  // reader's selection and scroll position rather than jumping to the caret.
  juce::Viewport* textViewport=nullptr;for(auto* child:details_.getChildren())if(auto* viewport=dynamic_cast<juce::Viewport*>(child)){textViewport=viewport;break;}
  const auto position=textViewport?textViewport->getViewPosition():juce::Point<int>{};
  const auto selection=details_.getHighlightedRegion();details_.setText(value,false);
  details_.setHighlightedRegion({std::min(selection.getStart(),value.length()),std::min(selection.getEnd(),value.length())});
  if(textViewport)textViewport->setViewPosition(position);
 }
}
void MetronomeView::refreshDisclosure(){
 const bool advanced=advancedControls_.getToggleState()&&!showingDetails_;
 const bool recovery=preferencesPending()||prefState_==PrefState::Failed||prefState_==PrefState::Conflict||prefState_==PrefState::Unsupported;
 const bool changed=advancedViewport_.isVisible()!=advanced||details_.isVisible()!=showingDetails_||reconcile_.isVisible()!=recovery;
 auto* focused=juce::Component::getCurrentlyFocusedComponent();
 const bool hidesAdvanced=focused&&advancedContent_.isParentOf(focused)&&!advanced;
 const bool hidesDetails=focused==&details_&&!showingDetails_;
 advancedViewport_.setVisible(advanced);details_.setVisible(showingDetails_);
 for(auto* button:{&reconcile_,&retry_,&keepStored_,&reopen_})button->setVisible(recovery);
 presentationBadge_.setText("Presentation: "+juce::String(presentation::levelLabel(presentationLevel_))+" (global)",juce::dontSendNotification);
 detailsButton_.setButtonText(showingDetails_?"Close Instructions / Details":presentationLevel_==presentation::Level::Developer?"Instructions / Diagnostics":"Instructions and Details");
 detailsButton_.setTitle(showingDetails_?"Close Metronome instructions and details":"Open Metronome instructions and current permitted details");
 if((hidesAdvanced||hidesDetails)&&isShowing())title_.grabKeyboardFocus();
 if(changed)resized();
}
bool MetronomeView::stoppedResolved()const{const auto s=output_.status().lifecycle;return !started_&&!s.ownsOutcome&&!s.pendingOutcome&&s.state!=output::State::Running&&s.state!=output::State::Paused&&!preferencesPending();}
bool MetronomeView::applySettings(const metronome::Settings& value){try{if(!stoppedResolved())throw std::runtime_error("Stop and Finish the check; resolve any preference write before changing the pattern.");supported(value);auto mix=commonMix_;mix.master=value.masterVolume;mix.bus=value.volumes;mix.masterMute=value.masterMute;mix.muteMask=static_cast<std::uint8_t>((mix.muteMask&3)|(value.mute[0]?4:0)|(value.mute[1]?8:0));mix.soloAB=static_cast<std::uint8_t>((value.solo[0]?1:0)|(value.solo[1]?2:0));if(!queueAudioMix(output_,mix))throw std::runtime_error("Audio settings could not be queued; prior pattern retained.");settings_=value;commonMix_=mix;loadEditors();error_.clear();if(onMixSelected)onMixSelected(mix);return true;}catch(const std::exception& e){error_=e.what();return false;}}
metronome::Settings MetronomeView::editorSettings()const{auto value=settings_;value.tempo=integer(tempo_,"Selected BPM");value.numerator=integer(numerator_,"Beats per bar");value.denominator=denominator_.getSelectedId();value.subdivision=subdivision_.getSelectedId();value.unit=static_cast<scheduler::BeatUnit>(unit_.getSelectedId()-1);if(countIn_.getSelectedId()!=1&&countIn_.getSelectedId()!=2)throw std::runtime_error("Select one configured bar or Off explicitly.");if(ramp_.getSelectedId()<1||ramp_.getSelectedId()>3)throw std::runtime_error("Select Ramp off, Step up or Step down explicitly.");value.countIn=countIn_.getSelectedId()==1?metronome::CountIn::ConfiguredBar:metronome::CountIn::Off;value.metronomeEnabled=enabled_.getToggleState();value.polyrhythmEnabled=polyrhythm_.getToggleState();if(value.polyrhythmEnabled){value.x=integer(polyX_,"Layer A count");value.y=integer(polyY_,"Layer B count");}if(value.numerator<1||value.numerator>16)throw std::runtime_error("Beats per bar must be 1–16.");value.styles.clear();for(int i=0;i<value.numerator;++i)value.styles.push_back(static_cast<metronome::Style>(styles_[static_cast<std::size_t>(i)].getSelectedId()-1));if(ramp_.getSelectedId()==1)value.ramp.reset();else value.ramp=metronome::Ramp{ramp_.getSelectedId()==2,integer(step_,"BPM step"),integer(every_,"Every bars"),integer(target_,"Target BPM")};return value;}
bool MetronomeView::hasPendingPatternEdits()const{try{return storage::canonical(metronome::encodeSettings(editorSettings()))!=storage::canonical(metronome::encodeSettings(settings_));}catch(const std::exception&){return true;}}
bool MetronomeView::applyEditors(){try{return applySettings(editorSettings());}catch(const std::exception& e){error_=e.what();return false;}}
void MetronomeView::loadEditors(){tempo_.setText(juce::String(settings_.tempo));numerator_.setText(juce::String(settings_.numerator));denominator_.setSelectedId(settings_.denominator,juce::dontSendNotification);subdivision_.setSelectedId(settings_.subdivision,juce::dontSendNotification);unit_.setSelectedId(static_cast<int>(settings_.unit)+1,juce::dontSendNotification);countIn_.setSelectedId(settings_.countIn==metronome::CountIn::Off?2:1,juce::dontSendNotification);int meter=9;for(std::size_t i=0;i<metronome::commonMeters().size();++i)if(metronome::commonMeters()[i]==std::make_pair(settings_.numerator,settings_.denominator))meter=static_cast<int>(i)+1;meter_.setSelectedId(meter,juce::dontSendNotification);for(std::size_t i=0;i<styles_.size();++i)styles_[i].setSelectedId(i<settings_.styles.size()?static_cast<int>(settings_.styles[i])+1:2,juce::dontSendNotification);enabled_.setToggleState(settings_.metronomeEnabled,juce::dontSendNotification);polyrhythm_.setToggleState(settings_.polyrhythmEnabled,juce::dontSendNotification);polyX_.setText(juce::String(settings_.x));polyY_.setText(juce::String(settings_.y));ramp_.setSelectedId(settings_.ramp?(settings_.ramp->up?2:3):1,juce::dontSendNotification);step_.setText(juce::String(settings_.ramp?settings_.ramp->step:1));every_.setText(juce::String(settings_.ramp?settings_.ramp->every:1));target_.setText(juce::String(settings_.ramp?settings_.ramp->target:120));masterGain_.setValue(settings_.masterVolume,juce::dontSendNotification);clickGain_.setValue(settings_.volumes[1],juce::dontSendNotification);mute_.setToggleState(settings_.masterMute,juce::dontSendNotification);manual_.setText(juce::String(settings_.tempo));}
bool MetronomeView::send(platform::OutputCommand command,const scheduler::Owner& owner,scheduler::Owner next){const auto s=output_.status().lifecycle;platform::Control c;c.op=command;c.owner=owner;c.nextOwner=next;c.epoch=s.request.epoch;c.token=s.observationToken;c.requestedNs=command==platform::OutputCommand::Stop&&requestedStopNs_?requestedStopNs_:platform::monotonicNs();if(output_.send(c))return true;error_="Output command queue refused; the original check remains retained.";return false;}
bool MetronomeView::connectOutput(const platform::OutputCapability* expected){if(!stoppedResolved())return false;if(output_.status().lifecycle.state==output::State::Fault&&!output_.disconnect())return false;if(output_.status().lifecycle.state!=output::State::Closed)return false;const auto cap=settingsOutputCapability();if(expected&&(!cap.valid||cap.uid!=expected->uid||cap.object!=expected->object||cap.rate!=expected->rate||cap.physicalFrames!=expected->physicalFrames||cap.outputChannels!=expected->outputChannels||cap.minFrames!=expected->minFrames||cap.maxFrames!=expected->maxFrames)){error_="Output capability changed before Connect. No output opened; inspect the selected device.";return false;}const bool okay=connectSettingsOutput(output_,cap,{cap.rate,cap.valid?std::clamp(256U,cap.minFrames,cap.maxFrames):0U},playback_.get(),platform::MetronomePlayback::observe,platform::MetronomePlayback::render);error_=okay?"":output_.error();return okay;}
bool MetronomeView::enableOutput(){return output_.status().lifecycle.state==output::State::Observed&&send(platform::OutputCommand::Acknowledge,{});}
bool MetronomeView::startSound(){
 if(!stoppedResolved()||output_.status().lifecycle.state!=output::State::Ready)return false;
 try{if(retained_.size()>=256)throw std::runtime_error("This sound-check preview has retained 256 generations. Close it after finishing; further checks need a fresh view.");supported(settings_);owner_=newOwner(output_.status().lifecycle.request.epoch);if(!playback_->prepare(settings_,owner_,owner_.generation,content::sha256(storage::canonical(metronome::encodeSettings(settings_))),output_.status().lifecycle.request.format.rate))throw std::runtime_error("Previous provider generation remains retained.");started_=true;terminalJoined_=false;resolveRequested_=false;stopRequested_=false;stopQueued_=false;requestedStopNs_=0;pendingStart_=true;cancelledCommand_=false;pendingResume_={};shown_={};manualCount_=0;tap_.reset();tapResult_={};error_.clear();
  if(!setMix(settings_.masterVolume,settings_.volumes[1],settings_.masterMute)||!send(platform::OutputCommand::Start,owner_)){output_.injectFault(output::Fault::QueueOverflow);return false;}return true;
 }catch(const std::exception& e){error_=e.what();return false;}
}
std::optional<MetronomeView::ManualPulseStart> MetronomeView::startManualPulse(int bpm){
 if(bpm<20||bpm>300){error_="Select an explicit quarter BPM20–300.";return std::nullopt;}
 metronome::Settings pulse{};
 pulse.tempo=bpm;
 pulse.numerator=1; pulse.denominator=4; pulse.subdivision=1;
 pulse.unit=scheduler::BeatUnit::Quarter;
 pulse.styles={metronome::Style::Normal};
 pulse.countIn=metronome::CountIn::Off;
 pulse.ramp.reset();pulse.polyrhythmEnabled=false;
 pulse.masterMute=false;pulse.metronomeEnabled=true;
 if(!applySettings(pulse)||!startSound())return std::nullopt;
 const auto rate=output_.status().lifecycle.request.format.rate;
 if(!rate){stopSound();error_="Shared output has no sample rate.";return std::nullopt;}
 return ManualPulseStart{owner_,owner_.generation,rate};
}
bool MetronomeView::resolveManualPulse(){
 if(started_&&!stoppedResolved()){
   if(!stopRequested_)stopSound();
   service();
   if(terminalJoined_&&!resolveRequested_)finishSound();
   service();
 }
 return requestClose();
}
bool MetronomeView::pauseSound(){if(!started_||stopRequested_||output_.status().lifecycle.state!=output::State::Running)return false;return send(platform::OutputCommand::Pause,owner_);}
bool MetronomeView::resumeSound(){if(!started_||stopRequested_||pendingResume_.valid()||!terminalJoined_||shown_.phase!=metronome::Phase::Paused||output_.status().lifecycle.state!=output::State::Paused)return false;try{if(retained_.size()>=256)throw std::runtime_error("Generation limit reached. Stop and Finish this check.");auto next=owner_;++next.generation;if(!playback_->prepareResume(owner_,next))return false;if(!send(platform::OutputCommand::PauseRetained,owner_)||!send(platform::OutputCommand::Resume,owner_,next)){output_.injectFault(output::Fault::QueueOverflow);return false;}pendingResume_=next;terminalJoined_=false;return true;}catch(const std::exception& e){error_=e.what();return false;}}
bool MetronomeView::stopSound(){if(!started_||resolveRequested_)return false;if(!stopRequested_)requestedStopNs_=platform::monotonicNs();stopRequested_=true;const auto state=output_.status().lifecycle.state;if(state==output::State::Unresolved||state==output::State::Fault)return true;if(stopQueued_)return true;const auto actual=output_.status().lifecycle.owner;const auto target=pendingResume_.valid()?pendingResume_:actual.valid()&&actual.id==owner_.id&&actual.generation>=owner_.generation?actual:owner_;stopQueued_=send(platform::OutputCommand::Stop,target);return stopQueued_;}
bool MetronomeView::finishSound(){const auto s=output_.status().lifecycle;if(!started_||!terminalJoined_||resolveRequested_||s.state==output::State::Running||s.state==output::State::Paused||preferencesPending())return false;if(s.ownsOutcome){if(!send(platform::OutputCommand::ResolveOutcome,s.owner))return false;}resolveRequested_=true;return true;}
bool MetronomeView::resetSound(){if(!stoppedResolved())return false;shown_={};tap_.reset();tapResult_={};tempoMessage_.clear();error_.clear();return true;}
bool MetronomeView::requestClose(){if(!stoppedResolved()){stopSound();error_="Finish the sound check and resolve the preference operation before leaving.";return false;}return output_.disconnect();}
bool MetronomeView::manualTempo(int bpm){if(bpm<20||bpm>300){error_="Live BPM must be an integer from 20 to 300.";return false;}if(!started_||stopRequested_||shown_.phase!=metronome::Phase::Running||output_.status().lifecycle.state!=output::State::Running)return false;if(manualCount_>=4096){error_="This check has reached its manual-command limit. Stop and Finish it.";return false;}if(!playback_->manual(owner_,shown_.binding,++sequence_,bpm))return false;++manualCount_;tempoMessage_="Tempo request queued; awaiting callback decision.";return true;}
metronome::TapResult MetronomeView::tap(std::uint64_t ns){tapResult_=tap_.add(++sequence_,ns);tempoMessage_=tapResult_.status==metronome::TapStatus::Candidate?"Tap candidate: "+std::to_string(tapResult_.bpm)+" BPM. Apply explicitly while running.":"Tap at least four steady beats (20–300 BPM).";return tapResult_;}
bool MetronomeView::applyTap(){return tapResult_.status==metronome::TapStatus::Candidate&&manualTempo(tapResult_.bpm);}
bool MetronomeView::applyCommonMix(const output::MixSettings& value){
 if(preferencesPending()||!queueAudioMix(output_,value))return false;
 commonMix_=value;settings_.masterVolume=value.master;settings_.volumes=value.bus;settings_.masterMute=value.masterMute;
 settings_.mute={bool(value.muteMask&4),bool(value.muteMask&8)};settings_.solo={bool(value.soloAB&1),bool(value.soloAB&2)};
 masterGain_.setValue(value.master,juce::dontSendNotification);clickGain_.setValue(value.bus[1],juce::dontSendNotification);mute_.setToggleState(value.masterMute,juce::dontSendNotification);return true;
}
bool MetronomeView::setMix(int master,int click,bool mute){
 auto value=commonMix_;value.bus=settings_.volumes;value.master=master;value.bus[1]=click;value.masterMute=mute;
 if(!applyCommonMix(value)){error_="Gain request refused; prior gain remains selected.";return false;}
 if(onMixSelected)onMixSelected(value);return true;
}
bool MetronomeView::audioCanRelease()const{return stoppedResolved();}
bool MetronomeView::audioRelease(){if(!audioCanRelease()||!output_.disconnect())return false;drain();return audioCanRelease();}

bool MetronomeView::preferencesReady()const noexcept{return prefState_==PrefState::Ready&&!future_&&pendingOperation_.empty();}
bool MetronomeView::preferencesPending()const noexcept{return reopenPending_||future_.has_value()||!pendingOperation_.empty();}
bool MetronomeView::configureStore(storage::ProfileStore& store){if(store_||!stoppedResolved())return false;store_=&store;prefState_=PrefState::Reading;future_.emplace(store_->readPreferences(storage::newUuid(),"freeplay_timing"));preferenceMessage_="Reading saved timing settings; audio remains stopped.";refresh();return true;}
bool MetronomeView::prepareStoreReopen(){const auto s=output_.status().lifecycle;if(reopenPending_||future_||started_||s.ownsOutcome||s.pendingOutcome||!output_.disconnect())return false;store_=nullptr;reopenPending_=true;prefState_=PrefState::Failed;retryProven_=false;preferenceMessage_="Reopening the same explicit test profile; original preference proposal retained.";return true;}
bool MetronomeView::rebindStore(storage::ProfileStore& store){if(store_||future_||started_||output_.status().lifecycle.ownsOutcome)return false;store_=&store;reopenPending_=false;const auto rebound=reconcilePreferences();refresh();return rebound;}
void MetronomeView::storeReopenFailed(const std::string& reason){reopenPending_=false;prefState_=PrefState::Failed;preferenceMessage_="Same-profile reopen failed: "+reason+". Original proposal retained; retry Reopen test profile.";}
bool MetronomeView::writePreferences(metronome::Preferences proposed){if(!store_||!preferencesReady()||!stoppedResolved())return false;try{pendingBytes_=storage::canonical(metronome::encodePreferences(proposed));pendingOperation_=storage::newUuid();expectedRevision_=revision_;proposed_=std::move(proposed);retryProven_=false;future_.emplace(store_->compareExchangePreferences(pendingOperation_,"freeplay_timing",1,expectedRevision_,pendingBytes_,true));prefState_=PrefState::Writing;preferenceMessage_="Saving settings; awaiting storage acknowledgment.";return true;}catch(const std::exception& e){preferenceMessage_=e.what();prefState_=PrefState::Failed;return false;}}
bool MetronomeView::saveLastUsed(){auto proposed=preferences_;proposed.lastUsed=settings_;return writePreferences(std::move(proposed));}
bool MetronomeView::savePreset(std::string name,std::string replaceId){if(!preferencesReady()||!stoppedResolved())return false;try{auto proposed=preferences_;metronome::putPreset(proposed,replaceId.empty()?storage::newUuid():replaceId,std::move(name),settings_,!replaceId.empty());proposed.lastUsed=settings_;return writePreferences(std::move(proposed));}catch(const std::exception& e){preferenceMessage_=e.what();return false;}}
bool MetronomeView::restoreLastUsed(){if(!preferencesReady())return false;try{return applySettings(metronome::restoreLastUsed(preferences_,stoppedResolved()));}catch(const std::exception& e){error_=e.what();return false;}}
bool MetronomeView::restorePreset(const std::string& id){if(!preferencesReady())return false;try{return applySettings(metronome::restorePreset(preferences_,id,stoppedResolved()));}catch(const std::exception& e){error_=e.what();return false;}}
bool MetronomeView::reconcilePreferences(){if(!store_||future_||started_)return false;future_.emplace(store_->readPreferences(storage::newUuid(),"freeplay_timing"));prefState_=pendingOperation_.empty()?PrefState::Reading:PrefState::Reconciling;preferenceMessage_="Inspecting the stored revision and exact value; original proposal retained.";return true;}
bool MetronomeView::retryOriginalPreferences(){if(!store_||future_||started_||!retryProven_||pendingOperation_.empty())return false;future_.emplace(store_->compareExchangePreferences(pendingOperation_,"freeplay_timing",1,expectedRevision_,pendingBytes_,true));prefState_=PrefState::Writing;retryProven_=false;preferenceMessage_="Retrying the unchanged original proposal at its inspected revision.";return true;}
bool MetronomeView::keepStoredPreferences(){if(future_||(prefState_!=PrefState::Conflict&&prefState_!=PrefState::Unsupported)||pendingOperation_.empty())return false;pendingOperation_.clear();pendingBytes_.clear();retryProven_=false;if(prefState_!=PrefState::Unsupported)prefState_=PrefState::Ready;preferenceMessage_="Kept the inspected stored value. The proposal is not the current stored value; no earlier commit history inferred.";return true;}
void MetronomeView::pollPreferences(){
 if(!future_||future_->wait_for(std::chrono::milliseconds(0))!=std::future_status::ready)return;
 try{const auto reply=future_->get();future_.reset();const bool writing=prefState_==PrefState::Writing;
  if(writing){if(reply.status==storage::Status::Confirmed&&number(reply.data,"revision")==expectedRevision_+1&&number(reply.data,"namespace_version")==1){revision_=expectedRevision_+1;preferences_=proposed_;pendingOperation_.clear();pendingBytes_.clear();prefState_=PrefState::Ready;preferenceMessage_="Settings saved. Restoring them requires a separate action.";}
   else {prefState_=PrefState::Failed;preferenceMessage_="Save not confirmed ("+std::string(storage::statusName(reply.status))+"). Inspecting original proposal against storage.";reconcilePreferences();}return;}
  if(reply.status!=storage::Status::Confirmed&&reply.status!=storage::Status::DefinitelyAbsent){prefState_=PrefState::Failed;preferenceMessage_="Storage inspection unavailable: "+reply.code+". Original proposal retained; Inspect save to retry reading.";return;}
  const bool absent=reply.status==storage::Status::DefinitelyAbsent;
  const auto actualRevision=absent?0:number(reply.data,"revision");const auto version=absent?1:number(reply.data,"namespace_version");const auto bytes=absent?"":reply.data.object().at("bytes").string();
  const bool applicable=absent||(version==1&&reply.data.object().at("applicable").boolean());
  if(!pendingOperation_.empty()&&version==1&&actualRevision==expectedRevision_+1&&bytes==pendingBytes_){revision_=actualRevision;preferences_=proposed_;pendingOperation_.clear();pendingBytes_.clear();prefState_=PrefState::Ready;preferenceMessage_="Exact proposed value confirmed stored at the expected next revision. No claim of which operation committed it.";return;}
  if(!applicable){prefState_=PrefState::Unsupported;preferenceMessage_="Unsupported saved timing namespace/version. Original bytes preserved; no settings applied or overwritten.";return;}
  preferences_=absent?metronome::Preferences{}:metronome::decodePreferences(storage::parseCanonical(bytes));revision_=actualRevision;
  if(!pendingOperation_.empty()){retryProven_=actualRevision==expectedRevision_;prefState_=PrefState::Conflict;preferenceMessage_=retryProven_?"Original proposal is not stored at this inspected revision. Retry original or Keep stored explicitly.":"A different stored revision/value was found. Original proposal retained; Keep stored or inspect again. No automatic overwrite.";}
  else{prefState_=PrefState::Ready;preferenceMessage_=absent?"No saved presets yet. Save settings explicitly.":"Saved settings available. Select Restore; audio will stay stopped.";}
 }catch(const std::exception& e){future_.reset();prefState_=PrefState::Failed;preferenceMessage_=std::string("Preference response could not be applied: ")+e.what()+". Original proposal retained.";}
}
void MetronomeView::drain(){
 platform::NativeEvent e;while(audioPolling_&&output_.nextEvent(e)){if(started_&&e.kind==71&&e.epoch==owner_.epoch&&(pendingStart_||pendingResume_.valid()))cancelledCommand_=true;if(onNativeEvent)onNativeEvent(e);}
 platform::MetronomeSegment segment;while(playback_->nextSegment(segment)){if(onSegment)onSegment(segment);if(!segments_.empty()){auto& last=segments_.back();if(last.owner==segment.owner&&last.binding==segment.binding&&last.through==segment.from&&last.tempo==segment.tempo&&last.countIn==segment.countIn){last.through=segment.through;continue;}}segments_.push_back(segment);if(segments_.size()>=65000&&!stopRequested_){error_="Diagnostic segment limit reached. Stopping with all received facts retained.";stopSound();}}
 auto show=[this](const platform::MetronomeProgress& p){if(pendingResume_.valid()&&p.owner==pendingResume_&&(p.clientAcceptedThrough>0||!p.terminal||output_.status().lifecycle.owner==pendingResume_)){owner_=pendingResume_;pendingResume_={};shown_={};terminalJoined_=false;}if(p.owner==owner_&&(!(shown_.owner==p.owner)||p.sequence>=shown_.sequence)){shown_=p;if(p.clientAcceptedThrough>0)pendingStart_=false;}};
 platform::MetronomeProgress p;while(playback_->nextProgress(p)){show(p);if(onProgress)onProgress(p);}while(playback_->reclaim(p)){pendingTerminal_.push_back(p);show(p);}
 scheduler::Fact fact;while(playback_->nextFact(fact))if(onFact)onFact(fact);
 platform::MetronomeReply reply;while(playback_->nextReply(reply)){if(reply.owner==owner_)tempoMessage_=reply.accepted?"Manual tempo accepted for the next bar; ramp disarmed.":"Manual tempo refused in the actual callback phase.";if(onReply)onReply(reply);}
 const auto s=output_.status().lifecycle;
 for(auto it=pendingTerminal_.begin();it!=pendingTerminal_.end();){
  const bool laterStop=s.state==output::State::Unresolved||s.state==output::State::Fault;
  const bool phase=it->phase==metronome::Phase::Paused?(s.state==output::State::Paused||laterStop):laterStop;
  const bool same=it->owner==s.owner&&it->owner.epoch==s.request.epoch&&it->clientAcceptedThrough==s.submittedFrames;
  const bool emptyFault=s.state==output::State::Fault&&it->fault&&it->owner.epoch<=s.request.epoch;
  const bool cancelledResume=cancelledCommand_&&pendingResume_.valid()&&it->owner==pendingResume_&&it->clientAcceptedThrough==0&&s.owner==owner_&&laterStop;
  if(phase&&(same||emptyFault||cancelledResume)){retained_.push_back({*it,s,false,cancelledResume});if(it->owner==owner_){terminalJoined_=true;shown_=*it;}if(cancelledResume){pendingResume_={};cancelledCommand_=false;}it=pendingTerminal_.erase(it);}else ++it;
 }
 if(shown_.owner==owner_&&shown_.terminal&&shown_.phase==metronome::Phase::Paused&&(s.state==output::State::Unresolved||s.state==output::State::Fault)&&s.owner==shown_.owner&&s.submittedFrames==shown_.clientAcceptedThrough){auto stopped=shown_;stopped.phase=metronome::Phase::Terminal;stopped.tempo.resumable=false;stopped.tempo.ramp.reset();stopped.requestedStopNs=s.requestedStopNs;stopped.uncertainThrough=s.uncertainThrough;stopped.fault=s.state==output::State::Fault;retained_.push_back({stopped,s,true,false});shown_=stopped;terminalJoined_=true;}
 if(pendingStart_&&cancelledCommand_&&s.state==output::State::Ready&&!s.ownsOutcome&&!s.pendingOutcome&&s.request.epoch==owner_.epoch){
  // Kind71 proves cancellation of the sole pending Start. Close/flush before
  // replacing the provider whose prepared Ready slot never became active.
  platform::MetronomeProgress cancelled;cancelled.owner=owner_;cancelled.binding=owner_.generation;cancelled.phase=metronome::Phase::Terminal;cancelled.terminal=true;cancelled.requestedStopNs=requestedStopNs_;cancelled.tempo.tempo=settings_.tempo;
  if(output_.disconnect()){retained_.push_back({cancelled,s,true,true});shown_=cancelled;playback_=std::make_unique<platform::MetronomePlayback>();pendingStart_=false;cancelledCommand_=false;terminalJoined_=true;}
 }
}
void MetronomeView::service(){if(audioPolling_)output_.service();drain();pollPreferences();const auto s=output_.status().lifecycle;
 if(started_&&stopRequested_&&!stopQueued_&&!resolveRequested_&&(s.state==output::State::Ready||s.state==output::State::Running||s.state==output::State::Paused))stopQueued_=send(platform::OutputCommand::Stop,owner_);
 if(resolveRequested_&&!s.ownsOutcome&&!s.pendingOutcome&&s.state!=output::State::Running&&s.state!=output::State::Paused){started_=false;resolveRequested_=false;stopRequested_=false;terminalJoined_=false;pendingStart_=false;pendingResume_={};}
 if(s.state==output::State::Fault)error_="Output unavailable: "+std::string(output::faultText(s.fault))+".";
 refresh();
}
void MetronomeView::quiesceAndRetain(){stopTimer();output_.shutdown();drain();}
bool MetronomeView::keyPressed(const juce::KeyPress& key){if(!isShowing())return false;if(key.getKeyCode()==juce::KeyPress::escapeKey)return stopSound();if(key.getKeyCode()!=juce::KeyPress::spaceKey)return false;if(dynamic_cast<juce::TextEditor*>(juce::Component::getCurrentlyFocusedComponent()))return false;if(spaceHeld_)return true;spaceHeld_=juce::KeyPress::isKeyCurrentlyDown(juce::KeyPress::spaceKey);if(output_.status().lifecycle.state==output::State::Paused)return resumeSound();if(output_.status().lifecycle.state==output::State::Running)return pauseSound();return startSound();}
bool MetronomeView::keyStateChanged(bool){if(!juce::KeyPress::isKeyCurrentlyDown(juce::KeyPress::spaceKey))spaceHeld_=false;return false;}
bool MetronomeView::keyStateChanged(bool down,juce::Component*){return keyStateChanged(down);}
bool MetronomeView::keyPressed(const juce::KeyPress& key,juce::Component* source){
 if(!isShowing())return false;
 if(source==&reducedMotion_&&key.getKeyCode()==juce::KeyPress::spaceKey){reducedMotion_.setToggleState(!reducedMotion_.getToggleState(),juce::sendNotificationSync);return true;}
 if(key.getKeyCode()==juce::KeyPress::returnKey){if(auto* b=dynamic_cast<juce::Button*>(source)){b->triggerClick();return true;}}
 if(key.getKeyCode()==juce::KeyPress::spaceKey){
  if(auto* b=dynamic_cast<juce::Button*>(source)){
   if(b->isShowing()&&b->isEnabled()&&!spaceHeld_){spaceHeld_=true;b->triggerClick();}
   return true;
  }
  keyPressed(key);return true;
 }
 if(key.getKeyCode()==juce::KeyPress::escapeKey){keyPressed(key);return true;}
 return false;
}
void MetronomeView::refresh(){const auto s=output_.status().lifecycle;const bool stopped=stoppedResolved();profileState_.setVisible(store_==nullptr&&!preferencesReady());
 connect_.setEnabled(stopped&&(s.state==output::State::Closed||s.state==output::State::Fault));enable_.setEnabled(s.state==output::State::Observed);start_.setEnabled(stopped&&s.state==output::State::Ready);pause_.setEnabled(started_&&!stopRequested_&&s.state==output::State::Running);resume_.setEnabled(started_&&!stopRequested_&&terminalJoined_&&s.state==output::State::Paused);stop_.setEnabled(started_&&!resolveRequested_);finish_.setEnabled(started_&&terminalJoined_&&!resolveRequested_&&s.state!=output::State::Paused&&s.state!=output::State::Running);reset_.setEnabled(stopped);back_.setEnabled(stopped);
 for(auto* c:std::initializer_list<juce::Component*>{&tempo_,&numerator_,&step_,&every_,&target_,&polyX_,&polyY_,&meter_,&denominator_,&subdivision_,&unit_,&countIn_,&ramp_,&enabled_,&polyrhythm_,&apply_})c->setEnabled(stopped);
 int draftBeats=0;try{draftBeats=integer(numerator_,"Beats per bar");}catch(...){}for(std::size_t i=0;i<styles_.size();++i)styles_[i].setEnabled(stopped&&static_cast<int>(i)<draftBeats);
 const bool running=started_&&!stopRequested_&&s.state==output::State::Running&&shown_.phase==metronome::Phase::Running;applyManual_.setEnabled(running);applyTap_.setEnabled(running&&tapResult_.status==metronome::TapStatus::Candidate);
 const bool prefs=stopped&&preferencesReady();for(auto* b:{&saveLast_,&restoreLast_,&savePreset_,&replacePreset_,&restorePreset_})b->setEnabled(prefs);reconcile_.setEnabled(store_&&!future_&&!started_);retry_.setEnabled(retryProven_&&!future_&&!started_);keepStored_.setEnabled((prefState_==PrefState::Conflict||prefState_==PrefState::Unsupported)&&!pendingOperation_.empty()&&!future_&&!started_);
 reopen_.setEnabled(bool(onReopenStore)&&!reopenPending_&&!future_&&!started_&&(prefState_==PrefState::Failed||prefState_==PrefState::Unsupported));
 masterGain_.setEnabled(!preferencesPending());clickGain_.setEnabled(!preferencesPending());mute_.setEnabled(!preferencesPending());
 if(s.state==output::State::Fault){
  const MetronomeFaultInput fault{started_,terminalJoined_,resolveRequested_,s.ownsOutcome,s.pendingOutcome,preferencesPending(),finish_.isEnabled()&&!preferencesPending(),connect_.isEnabled(),back_.isEnabled()};
  status_.setText(metronomeFaultGuidance(fault),juce::dontSendNotification);
 }else if(error_.empty()&&!started_&&s.state==output::State::Closed&&!preferencesPending())
  status_.setText(juce::String::fromUTF8("Closed · no unresolved check. Open Audio settings, choose Connect audio and Enable audio, then Start this sound check."),juce::dontSendNotification);
 else if(!error_.empty())status_.setText(error_,juce::dontSendNotification);
 else{
  std::string next;
  switch(s.state){
   case output::State::Observed:next=". Next action: Enable audio in Audio settings.";break;
   case output::State::Ready:next=". Start is available.";break;
   case output::State::Running:next=". Pause or Stop is available.";break;
   case output::State::Paused:next=". Resume or Stop is available.";break;
   case output::State::Unresolved:next=finish_.isEnabled()?". Finish check is available.":". Wait for callback confirmation before Finish check.";break;
   default:break;
  }
  status_.setText(std::string(output::stateText(s.state))+(started_?" · sound check retained":" · no unresolved check")+next,juce::dontSendNotification);
 }
 status_.setTooltip(status_.getText());
 start_.setTitle(start_.isEnabled()?"Start sound-check preview":"Start unavailable until audio is enabled");start_.setTooltip(start_.isEnabled()?"Start the prepared sound-check preview.":"Start unavailable: choose Audio settings, then Connect audio and Enable audio.");
 pause_.setTitle(pause_.isEnabled()?"Pause running sound check":"Pause unavailable until sound is running");pause_.setTooltip(pause_.isEnabled()?"Pause the running sound check.":"Pause unavailable until this sound check is running.");
 resume_.setTitle(resume_.isEnabled()?"Resume paused sound check":"Resume unavailable until sound is paused");resume_.setTooltip(resume_.isEnabled()?"Resume the paused sound check.":"Resume unavailable until Pause is confirmed.");
 stop_.setTitle(stop_.isEnabled()?"Stop retained sound check":"Stop unavailable until a sound check starts");stop_.setTooltip(stop_.isEnabled()?"Stop sound while retaining the check for Finish.":"Stop unavailable until a sound check starts.");
 finish_.setTitle(finish_.isEnabled()?"Finish stopped sound check":"Finish unavailable until stopped outcome is confirmed");finish_.setTooltip(finish_.isEnabled()?"Finish the stopped sound check and release its outcome.":"Finish unavailable until Stop and callback confirmation.");
 const auto rate=s.request.format.rate;fullFacts_=("Callback-confirmed running: "+juce::String(rate?static_cast<double>(shown_.totalActiveFrames)/rate:0,2)+" s · Complete scheduled bars: "+juce::String(static_cast<juce::int64>(shown_.completedCycles))+" · "+(shown_.phase==metronome::Phase::CountIn?"count-in":shown_.partial?"partial bar":"bar boundary")+"\n"+patternLabel(settings_)+" · Selected "+juce::String(settings_.tempo)+" BPM · Actual "+juce::String(shown_.owner.valid()?shown_.tempo.tempo:settings_.tempo)+" · "+metronome::beatUnitLabel(settings_.unit)+". No physical output or performed accuracy inferred.");
 const auto& actual=shown_.tempo;const auto rampText=shown_.owner.valid()?(actual.ramp?(actual.ramp->up?"up":"down"):"off"):"not running";fullTempoStatus_=("Actual ramp: "+std::string(rampText)+" · Bars toward step: "+std::to_string(actual.count)+(actual.pendingManual?" · Pending BPM: "+std::to_string(*actual.pendingManual):"")+" · "+tempoMessage_);tempoStatus_.setText(fullTempoStatus_,juce::dontSendNotification);
 facts_.setText("Sound-check time: "+juce::String(rate?static_cast<double>(shown_.totalActiveFrames)/rate:0,2)+" s · Complete scheduled bars: "+juce::String(static_cast<juce::int64>(shown_.completedCycles))+" · "+(shown_.phase==metronome::Phase::CountIn?"count-in":shown_.partial?"partial bar":"bar boundary")+"\nActual tempo: "+juce::String(shown_.owner.valid()?shown_.tempo.tempo:settings_.tempo)+" BPM ("+metronome::beatUnitLabel(settings_.unit)+"). No playing accuracy verified.",juce::dontSendNotification);
 patternSummary_.setText((hasPendingPatternEdits()?"Unapplied edits - choose Apply pattern.\n":"Applied pattern - no unapplied edits.\n")+juce::String(settings_.tempo)+" BPM · "+juce::String(settings_.numerator)+"/"+juce::String(settings_.denominator)+" · "+metronome::beatUnitLabel(settings_.unit)+"\n"+juce::String(patternLabel(settings_))+" · "+juce::String(settings_.subdivision)+" parts per beat",juce::dontSendNotification);
 patternSummary_.setTooltip("Applied pattern; editor values are pending until Apply pattern succeeds. "+fullFacts_);
 prefStatus_.setText(preferencePrimaryText(),juce::dontSendNotification);prefStatus_.setTooltip(preferenceMessage_);
 profileState_.setText(reopenPending_?"Reopening the same local profile; original settings proposal retained.":"No local profile is open; preset settings remain unsaved.",juce::dontSendNotification);
 const auto selectedIndex=presetChoice_.getSelectedId();const auto selectedId=selectedIndex>0&&static_cast<std::size_t>(selectedIndex)<=presetIds_.size()?presetIds_[static_cast<std::size_t>(selectedIndex-1)]:"";
 std::vector<std::string> ids;for(const auto& p:preferences_.presets)ids.push_back(p.id);
 if(ids!=presetIds_){presetChoice_.clear(juce::dontSendNotification);presetIds_=ids;int selected=0;for(std::size_t i=0;i<preferences_.presets.size();++i){presetChoice_.addItem(preferences_.presets[i].name,static_cast<int>(i)+1);if(preferences_.presets[i].id==selectedId)selected=static_cast<int>(i)+1;}presetChoice_.setSelectedId(selected,juce::dontSendNotification);}else for(std::size_t i=0;i<preferences_.presets.size();++i)presetChoice_.changeItemText(static_cast<int>(i)+1,preferences_.presets[i].name);
 const bool selectedPreset=presetChoice_.getSelectedId()>0&&static_cast<std::size_t>(presetChoice_.getSelectedId())<=presetIds_.size();replacePreset_.setEnabled(prefs&&selectedPreset);restorePreset_.setEnabled(prefs&&selectedPreset);
 const juce::String presetReason=!store_?"Unavailable: attach an explicit test profile to use saved settings.":preferencesPending()?"Unavailable: wait for the saved-settings operation to finish.":!stopped?"Unavailable: Stop and Finish the sound check before changing saved settings.":"Unavailable: inspect or recover saved settings first.";
 saveLast_.setTitle("Save applied timing pattern as last used");saveLast_.setTooltip(prefs?"Save the applied pattern to this local profile. Unapplied editor changes are excluded; choose Apply pattern first to save them.":presetReason);
 restoreLast_.setTitle("Restore last used timing settings");restoreLast_.setTooltip(prefs?"Restore last used timing settings without starting sound.":presetReason);
 savePreset_.setTitle("Create saved timing preset and update last used from applied pattern");savePreset_.setTooltip(prefs?"Save a new preset and last used from the applied pattern. Unapplied editor changes are excluded.":presetReason);
 replacePreset_.setTitle("Replace selected preset and last used with applied pattern");replacePreset_.setTooltip(!prefs?presetReason:selectedPreset?"Replace the selected preset using the same saved ID and update last used from the applied pattern.":"Select a saved preset before Replace selected.");
 restorePreset_.setTitle("Restore selected saved timing preset");restorePreset_.setTooltip(!prefs?presetReason:selectedPreset?"Restore the selected preset without starting sound.":"Select a saved preset before Restore selected.");
 reconcile_.setTitle("Inspect saved settings");reconcile_.setTooltip(reconcile_.isEnabled()?"Inspect the stored revision and exact value before deciding recovery.":presetReason);
 retry_.setTitle("Retry original saved-settings proposal");retry_.setTooltip(retry_.isEnabled()?"Retry the unchanged original proposal after inspection proves the revision.":"Retry unavailable until Inspect save proves the original proposal can be retried.");
 keepStored_.setTitle("Keep inspected stored settings");keepStored_.setTooltip(keepStored_.isEnabled()?"Keep the inspected stored value and discard the pending proposal.":"Keep stored unavailable until a saved-settings conflict is inspected.");
 reopen_.setTooltip(reopen_.isEnabled()?"Reopen the same test profile after a saved-settings failure.":"Reopen the same test profile is unavailable until a saved-settings failure requires recovery.");
 refreshDetails();refreshDisclosure();repaint();
}
void MetronomeView::paint(juce::Graphics& g){
 g.fillAll(appearance::colour(0xff10212c));
 const auto bar=progressBarBounds_;if(bar.isEmpty())return;
 g.setColour(appearance::colour(0xff29404d));g.fillRect(bar);
 if(reducedMotion_.getToggleState()){
  g.setColour(appearance::colour(0xffffffff));g.setFont(juce::FontOptions{12.0f});
  g.drawFittedText("Progress in text above",bar,juce::Justification::centred,1);return;
 }
 g.setColour(appearance::colour(0xff6bd5cb));
 const auto fraction=shown_.barFrames?std::clamp(static_cast<double>(shown_.cursorFrames)/shown_.barFrames,0.0,1.0):0.0;
 g.fillRect(bar.withWidth(static_cast<int>(bar.getWidth()*fraction)));
}
void MetronomeView::resized(){
 const int inset=getWidth()<800?16:24;
 const int width=std::max(1,getWidth()-2*inset);
 title_.setText("Metronome",juce::dontSendNotification);title_.setFont(juce::FontOptions{26.0f,juce::Font::bold});
 title_.setBounds(inset,8,std::max(1,width-100),34);back_.setBounds(getWidth()-inset-84,10,84,32);
 description_.setText("Set the tempo and time signature, then Start when audio is ready.\nStop keeps this sound check here; Finish releases it. No practice result.",juce::dontSendNotification);
 description_.setBounds(inset,48,width,48);
 const bool narrow=getWidth()<800;
 const int badgeWidth=narrow?208:240;
 presentationBadge_.setBounds(inset,100,badgeWidth,26);
 advancedControls_.setBounds(inset+badgeWidth+8,98,narrow?164:174,30);
 detailsButton_.setBounds(inset+badgeWidth+(narrow?180:190),98,std::max(1,width-badgeWidth-(narrow?180:190)),30);
 captions_[0]->setText("Tempo (BPM)",juce::dontSendNotification);captions_[2]->setText("Time signature",juce::dontSendNotification);
 for(auto& caption:captions_){caption->setFont(juce::FontOptions{14.0f});caption->setMinimumHorizontalScale(1.0f);}
 tempo_.setComponentID("metronome-tempo-bpm");tempo_.setTitle("Tempo in BPM");meter_.setComponentID("metronome-time-signature");meter_.setTitle("Time signature");
 // Keep the complete 14px BPM caption on one line without font compression.
 // The adjacent meter, Apply and current-pattern region move by the same 18px.
 tempo_.setBounds(inset,156,100,32);meter_.setBounds(inset+112,156,118,32);apply_.setBounds(inset+242,154,140,34);
 patternSummary_.setBounds(inset+394,138,std::max(1,width-394),54);
 auto row=[&](int y,std::initializer_list<std::pair<juce::Component*,int>> controls){
  int total=0;for(const auto& control:controls)total+=control.second;
  const int gaps=8*(static_cast<int>(controls.size())-1);const int available=std::max(1,width-gaps);int x=inset;
  for(const auto& control:controls){const int w=std::max(1,control.second*available/total);control.first->setBounds(x,y,w,34);x+=w+8;}
 };
 row(200,{{&audioSettings_,150},{&start_,68},{&pause_,68},{&resume_,76},{&stop_,68},{&finish_,112},{&reset_,84}});
 status_.setBounds(inset,242,width,52);facts_.setBounds(inset,298,width,60);
 progressBarBounds_={inset,366,std::max(1,width-158),18};reducedMotion_.setBounds(getWidth()-inset-150,364,150,24);
 profileState_.setBounds(inset,390,width,28);
 prefStatus_.setBounds(inset,422,width,60);
 const bool recovery=reconcile_.isVisible();
 row(488,{{&reconcile_,128},{&retry_,132},{&keepStored_,124},{&reopen_,184}});
 reopen_.setButtonText("Reopen profile");reopen_.setTitle("Reopen the same local profile");
 const int panelTop=recovery?532:492;
 const juce::Rectangle<int> panel{inset,panelTop,width,std::max(1,getHeight()-panelTop-16)};
 advancedViewport_.setBounds(panel);details_.setBounds(panel);
 // Flow complete advanced controls in authored UI order. The viewport, rather
 // than shortened captions or tiny fonts, handles a smaller available height.
 const int contentWidth=std::max(1,width-advancedViewport_.getScrollBarThickness());
 const int inner=16,available=std::max(1,contentWidth-2*inner);
 advancedHeading_.setBounds(inner,8,available,30);
 auto flow=[&](int y,std::initializer_list<std::pair<juce::Component*,int>> controls){
  int x=inner;for(const auto& control:controls){const int w=std::min(available,control.second);if(x>inner&&x+w>inner+available){x=inner;y+=58;}control.first->setBounds(x,y+22,w,32);x+=w+12;}return y+66;
 };
 int y=flow(44,{{&unit_,144},{&numerator_,104},{&denominator_,96},{&subdivision_,112},{&countIn_,170}});
 const int columns=available<700?4:8;const int cell=available/columns;
 for(std::size_t i=0;i<styles_.size();++i){styles_[i].setBounds(inner+static_cast<int>(i%columns)*cell,y+22+static_cast<int>(i/columns)*58,std::max(1,cell-8),32);}
 y+=static_cast<int>((styles_.size()+columns-1)/columns)*58+8;
 y=flow(y,{{&ramp_,142},{&step_,90},{&every_,108},{&target_,108},{&enabled_,220}});
 y=flow(y,{{&polyrhythm_,228},{&polyX_,116},{&polyY_,116}});
 y=flow(y,{{&manual_,100},{&applyManual_,120},{&tapButton_,84},{&applyTap_,114}});
 tempoStatus_.setBounds(inner,y,available,64);y+=76;
 y=flow(y,{{&presetName_,172},{&savePreset_,118},{&presetChoice_,172},{&replacePreset_,144},{&restorePreset_,144}});
 y=flow(y,{{&saveLast_,152},{&restoreLast_,144}});
 instructions_.setBounds(inner,y,available,200);y+=216;
 advancedContent_.setSize(contentWidth,y);
}
}
