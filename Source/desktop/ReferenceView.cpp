#include "desktop/Appearance.hpp"
#include "desktop/ReferenceView.hpp"
#include <algorithm>

namespace fathom::desktop {
ReferenceView::ReferenceView() {
    title_.setText(juce::String::fromUTF8("REFERENCE — LOCAL TONE COMPARISON"),juce::dontSendNotification);title_.setFont(juce::FontOptions{28.0f,juce::Font::bold});
    description_.setText("Use Audio settings for speakers, headphones and volume. These shared settings apply across the other activities; Play tone begins sound.\nEach tone lasts three seconds; open-string and capo-note references stay separate.\nCompare by ear. This tool does not listen, score or record practice.\nBack returns to Home after the reference output is idle.",juce::dontSendNotification);
    description_.setTitle("Read-only Reference: shared Audio settings, three-second tones and no practice recording.");
    for(auto* l:{&title_,&description_,&pitch_,&facts_})addAndMakeVisible(*l);
    status_.setComponentID("reference-status");
    status_.setTitle("Read-only Reference tone lifecycle, output state and next action.");
    addAndMakeVisible(status_);addChildComponent(status_.detailsView());
    status_.detailsButton().addShortcut(juce::KeyPress(juce::KeyPress::spaceKey));
    idleState_.setComponentID("reference-idle-state");
    idleState_.setTitle("Reference idle-state marker.");
    idleState_.setFont(juce::FontOptions{15.0f, juce::Font::bold});
    idleState_.setColour(juce::Label::textColourId, appearance::colour(0xffffd479));
    idleState_.setText("Reference output is closed; no tone is playing.", juce::dontSendNotification);
    addAndMakeVisible(idleState_);
    status_.onDetailsChanged=[this]{facts_.setVisible(!status_.detailsVisible());resized();repaint();};
    for(int i=1;i<=6;++i)string_.addItem("String "+juce::String(7-i)+(i==1?" (low)":i==6?" (high)":""),i);
    string_.setComponentID("reference-string");string_.setTitle("Reference string");string_.setSelectedId(1,juce::dontSendNotification);
    target_.setComponentID("reference-target");target_.addItem("Open string (uncapoed)",1);target_.addItem("At capo / fret 0",2);target_.setTitle("Reference target");target_.setSelectedId(1,juce::dontSendNotification);
    method_.setComponentID("reference-sound");method_.addItem("Pure sine",1);method_.addItem("Clean pluck",2);method_.setTitle("Reference sound");method_.setSelectedId(1,juce::dontSendNotification);
    for(auto* c:{&string_,&target_,&method_}){addAndMakeVisible(*c);c->onChange=[this]{updatePitch();};}
    for(auto* b:{&connect_,&enable_,&play_,&stop_,&done_,&back_})addAndMakeVisible(*b);
    connect_.setVisible(false);enable_.setVisible(false);
    audioSettings_.setComponentID("reference-audio-settings");audioSettings_.setTitle("Open shared Audio settings before playing a reference tone.");
    connect_.setComponentID("reference-connect");enable_.setComponentID("reference-enable");play_.setComponentID("reference-play");stop_.setComponentID("reference-stop");done_.setComponentID("reference-done");back_.setComponentID("reference-back");
    auto configureControl=[&](juce::Component& component,const char* title,int order){component.setTitle(title);component.setWantsKeyboardFocus(true);component.setExplicitFocusOrder(order);};
    configureControl(string_,"Choose the guitar string for the reference tone.",1);
    configureControl(target_,"Choose an open-string or capo-position reference.",2);
    configureControl(method_,"Choose the reference sound method.",3);
    configureControl(audioSettings_,"Open shared Audio settings before playing a reference tone.",4);
    configureControl(connect_,"Connect the shared Audio output without starting a reference tone.",5);
    configureControl(enable_,"Enable the observed shared Audio output.",6);
    configureControl(play_,"Play the selected reference tone.",7);
    configureControl(stop_,"Stop the reference tone and review the output state.",8);
    configureControl(done_,"Acknowledge this stopped tone; keep healthy prepared output for another explicit Play.",9);
    configureControl(back_,"Return to Home after the reference output is idle.",10);
    for (auto* b : {static_cast<juce::TextButton*>(&audioSettings_), static_cast<juce::TextButton*>(&connect_), static_cast<juce::TextButton*>(&enable_), static_cast<juce::TextButton*>(&play_), static_cast<juce::TextButton*>(&stop_), static_cast<juce::TextButton*>(&done_), static_cast<juce::TextButton*>(&back_)}) { b->setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb)); b->setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c)); b->setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c)); }
    addAndMakeVisible(audioSettings_);audioSettings_.onClick=[this]{if(onAudioSettings)onAudioSettings();};
    connect_.onClick=[this]{connectOutput();};enable_.onClick=[this]{enableOutput();};
    play_.onClick=[this]{
        if(started_ || resolving_ || !playback_ || output_.status().lifecycle.state!=output::State::Ready)return;
        if(!sameAudioCapability(settingsOutputCapability(),preparedCapability_)){localError_="Output changed. Open Audio settings and reconnect explicitly; no tone started.";closeUnowned();return;}
        try {
            const juce::Uuid id;std::copy_n(id.getRawData(),16,owner_.id.begin());owner_.id[6]=static_cast<std::uint8_t>((owner_.id[6]&15)|0x40);owner_.id[8]=static_cast<std::uint8_t>((owner_.id[8]&63)|0x80);
            owner_.generation=++generation_;owner_.epoch=output_.status().lifecycle.request.epoch;
            auto program=reference::tuningTone(setup_,string_.getSelectedId(),target_.getSelectedId()==1?reference::ToneTarget::OpenString:reference::ToneTarget::CapoPosition,owner_,generation_,output_.status().lifecycle.request.format.rate,method_.getSelectedId()==1?reference::Method::Sine:reference::Method::Pluck);
            auto next=std::make_unique<platform::ReferencePlayback>();next->prepare(std::move(program));playback_->publish(std::move(next));
            view_={};started_=true;closeStopRequested_=false;
            if(!command(platform::OutputCommand::Start)){cancelledStart_=true;closeUnowned();}
        }catch(const std::exception& e){localError_=e.what();refreshGuidance(output_.status().lifecycle);}
    };
    stop_.onClick=[this]{command(platform::OutputCommand::Stop);};
    done_.onClick=[this]{finishTool();};
    back_.onClick=[this]{
        const auto s=output_.status().lifecycle;
        if(s.state==output::State::Fault && !s.ownsOutcome){leaveIdle();return;}
        if(started_ && !s.pendingOutcome){stopWhenRunning_=true;command(platform::OutputCommand::Stop);refreshGuidance(s);return;}
        if(s.ownsOutcome){refreshGuidance(s);return;}
        leaveIdle();
    };
    updatePitch();startTimer(30);timerCallback();
}
ReferenceView::~ReferenceView(){stopTimer();retained_=output_.shutdown();}
void ReferenceView::setSetup(const guitar::Setup& setup){if(output_.status().lifecycle.ownsOutcome || started_)return;setup_=setup;updatePitch();}
void ReferenceView::updatePitch(){
    localError_.clear();
    const auto i=string_.getSelectedId();
    try {
        if(!guitar::validate(setup_).empty() || i<1 || i>6)throw std::invalid_argument("Choose a valid applied guitar setup.");
        const auto position=guitar::position(setup_,i,0);if(target_.getSelectedId()==2 && !position.available())throw std::invalid_argument("Capo reference position is unavailable.");
        const auto midi=target_.getSelectedId()==1?setup_.openMidi[static_cast<std::size_t>(i-1)]:*position.midi;
        pitch_.setText(juce::String(guitar::noteName(midi))+" | "+juce::String(reference::frequency(midi),2)+" Hz | Capo "+juce::String(setup_.capo)+(target_.getSelectedId()==1?" | Open-string tuning":" | At capo"),juce::dontSendNotification);
    }catch(const std::exception& e){pitch_.setText(e.what(),juce::dontSendNotification);}
}
bool ReferenceView::connectOutput(const platform::OutputCapability* expected){
    if(started_||resolving_||output_.status().lifecycle.state!=output::State::Closed)return false;
    if(output_.status().cleanupFailed)return false;
    const auto cap=settingsOutputCapability();if(expected&&!sameAudioCapability(cap,*expected)){localError_="Output changed before Connect; inspect Audio settings.";return false;}
    localError_.clear();view_={};playback_=std::make_unique<PreparedToolSound<platform::ReferencePlayback>>();preparedCapability_=cap;
    return connectSettingsOutput(output_,cap,{cap.rate,cap.valid?std::clamp(256U,cap.minFrames,cap.maxFrames):0},playback_.get(),PreparedToolSound<platform::ReferencePlayback>::observe,PreparedToolSound<platform::ReferencePlayback>::render);
}
bool ReferenceView::enableOutput(){return output_.status().lifecycle.state==output::State::Observed&&command(platform::OutputCommand::Acknowledge);}
bool ReferenceView::applyCommonMix(const output::MixSettings& value){if(!queueAudioMix(output_,value))return false;commonMix_=value;return true;}
bool ReferenceView::audioCanRelease()const{const auto s=outputSnapshot();return !started_&&!resolving_&&!s.ownsOutcome&&!s.pendingOutcome&&s.state!=output::State::Running&&s.state!=output::State::Paused;}
bool ReferenceView::audioRelease(){if(!audioCanRelease())return false;const bool closed=closeUnowned();if(audioPolling_){platform::NativeEvent e;while(output_.nextEvent(e)){}}return closed;}
bool ReferenceView::requestClose(){
    if(audioCanRelease())return audioRelease();
    const auto s=outputSnapshot();
    if(started_&&!resolving_&&!s.pendingOutcome&&!closeStopRequested_)
        closeStopRequested_=command(platform::OutputCommand::Stop);
    return false;
}
bool ReferenceView::command(platform::OutputCommand op){
    if(op==platform::OutputCommand::Stop&&closeStopRequested_)return true;
    platform::Control c;c.op=op;c.owner=owner_;const auto s=output_.status().lifecycle;
    c.epoch=s.request.epoch;c.token=s.observationToken;c.requestedNs=platform::monotonicNs();
    if(!output_.send(c)){localError_="Output command could not be queued.";refreshGuidance(output_.status().lifecycle);return false;}
    if(op==platform::OutputCommand::Stop)closeStopRequested_=true;
    return true;
}
void ReferenceView::finishTool(){
    const auto s=output_.status().lifecycle;if(resolving_ || !s.pendingOutcome || !(s.owner==owner_))return;
    // Only this explicitly unrecorded reference tool. No Practice Attempt or SaveReceipt
    // exists. Preserve its actual output facts before the user's Done acknowledgment.
    retained_=s;resolving_=command(platform::OutputCommand::ResolveOutcome);
}
bool ReferenceView::closeUnowned(){
    if(output_.status().lifecycle.ownsOutcome)return false;
    if(!output_.disconnect()){localError_=output_.error();return false;}
    playback_.reset();started_=false;resolving_=false;stopWhenRunning_=false;cancelledStart_=false;closeStopRequested_=false;view_={};return true;
}
void ReferenceView::leaveIdle(){if(closeUnowned() && onBack)onBack();}
void ReferenceView::timerCallback(){
    if(audioPolling_)output_.service();platform::NativeEvent ev;while(audioPolling_&&output_.nextEvent(ev)){
        // One pending Start belongs to this private tool/epoch. Kind71 is the
        // actual adapter acknowledgement that urgent Stop cancelled that Start.
        if(ev.kind==71 && ev.epoch==owner_.epoch && (stopWhenRunning_||closeStopRequested_))cancelledStart_=true;
        if(onNativeEvent)onNativeEvent(ev);
    }
    if(playback_&&playback_->current()){scheduler::Fact f;while(playback_->current()->stream().nextFact(f)){}while(playback_->current()->stream().nextView(view_)){};}
    auto s=output_.status().lifecycle;
    if(cancelledStart_ && !s.ownsOutcome && s.state==output::State::Ready){if(closeUnowned())s=output_.status().lifecycle;}
    if(stopWhenRunning_ && s.state==output::State::Running){if(!closeStopRequested_)command(platform::OutputCommand::Stop);stopWhenRunning_=false;}
    if(resolving_ && !s.ownsOutcome&&!s.pendingOutcome){
        if(s.state==output::State::Ready&&s.fault==output::Fault::None&&s.owner==owner_){
            // ResolveOutcome was consumed by the original callback. Keep its
            // provider alive and the device prepared; never enqueue another Start.
            started_=false;resolving_=false;stopWhenRunning_=false;closeStopRequested_=false;
        }else if(closeUnowned())s=output_.status().lifecycle;
    }
    connect_.setEnabled(!started_ && !resolving_ && s.state==output::State::Closed);enable_.setEnabled(s.state==output::State::Observed);
    play_.setEnabled(!started_ && !resolving_ && s.state==output::State::Ready);stop_.setEnabled(s.state==output::State::Running);
    done_.setEnabled(!resolving_ && s.pendingOutcome && (s.state==output::State::Unresolved || s.state==output::State::Fault));
    for(auto* c:{&string_,&target_,&method_})c->setEnabled(!started_ && !resolving_);
    refreshGuidance(s);
    const auto& shown=s.ownsOutcome?s:retained_;
    facts_.setText(shown.owner.valid()?"No practice has been recorded. Your applied guitar setup is unchanged.":"Use Guitar setup to change your applied tuning or capo.",juce::dontSendNotification);
    idleState_.setVisible(s.state==output::State::Closed&&!s.ownsOutcome&&!s.pendingOutcome&&!started_&&!resolving_&&!retained_.owner.valid());
    repaint();
}
void ReferenceView::refreshGuidance(const output::Snapshot& s){
    ReferenceGuidanceInput i;i.output=s;i.started=started_;i.resolving=resolving_;i.stopWhenRunning=stopWhenRunning_;
    i.ownerMatches=s.owner==owner_&&owner_.valid();
    i.canConnect=!started_&&!resolving_&&s.state==output::State::Closed;
    i.canEnable=s.state==output::State::Observed;
    i.canPlay=!started_&&!resolving_&&s.state==output::State::Ready;
    i.canStop=s.state==output::State::Running;
    i.canDone=!resolving_&&s.pendingOutcome&&(s.state==output::State::Unresolved||s.state==output::State::Fault);
    i.canBack=back_.isEnabled();status_.present(i,localError_,output_.error());
}
void ReferenceView::paint(juce::Graphics& g){g.fillAll(appearance::colour(0xff10212c));if(status_.detailsVisible())return;const auto compact=getWidth()<800||getHeight()<680;const auto bar=juce::Rectangle<int>{compact?24:40,compact?436:478,getWidth()-(compact?48:80),compact?8:12};g.setColour(appearance::colour(0xff29404d));g.fillRect(bar);const auto total=output_.status().lifecycle.request.format.rate*3ULL;const double phase=total?std::clamp(static_cast<double>(view_.cursor.processedThrough)/static_cast<double>(total),0.0,1.0):0.0;g.setColour(appearance::colour(0xff6bd5cb));g.fillRect(bar.withWidth(static_cast<int>(bar.getWidth()*phase)));}
void ReferenceView::resized(){
    if(getWidth()<800 || getHeight()<680){
        const auto w=std::max(1,getWidth()-48);
        if(title_.getText().startsWith("REFERENCE")&&title_.getText().contains("LOCAL TONE COMPARISON"))
            title_.setText(juce::String::fromUTF8("Reference — Local tone comparison"),juce::dontSendNotification);
        title_.setBounds(24,16,w,40);description_.setBounds(24,64,w,112);string_.setBounds(24,184,180,32);target_.setBounds(216,184,200,32);method_.setBounds(432,184,std::max(1,getWidth()-456),32);pitch_.setBounds(24,228,w,35);status_.setBounds(24,272,w,82);status_.detailsView().setBounds(24,364,w,40);facts_.setBounds(24,364,w,40);idleState_.setBounds(24,408,w,24);audioSettings_.setBounds(24,448,160,36);play_.setBounds(200,448,130,36);stop_.setBounds(346,448,90,36);done_.setBounds(452,448,140,36);back_.setBounds(24,getHeight()-48,100,36);
        return;
    }
    const auto w=getWidth()-80;
    if(title_.getText().startsWith("Reference")&&title_.getText().contains("Local tone comparison"))
        title_.setText(juce::String::fromUTF8("REFERENCE — LOCAL TONE COMPARISON"),juce::dontSendNotification);
    title_.setBounds(40,30,w,45);description_.setBounds(40,90,w,112);string_.setBounds(40,220,180,32);target_.setBounds(235,220,230,32);method_.setBounds(480,220,180,32);pitch_.setBounds(40,265,w,35);status_.setBounds(40,310,w,96);status_.detailsView().setBounds(40,415,w,96);facts_.setBounds(40,420,w,45);idleState_.setBounds(40,516,w,24);audioSettings_.setBounds(40,550,160,36);play_.setBounds(380,550,130,36);stop_.setBounds(525,550,90,36);done_.setBounds(630,550,140,36);back_.setBounds(40,getHeight()-72,100,36);
}
}
