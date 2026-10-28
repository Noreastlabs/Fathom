#include "desktop/Appearance.hpp"
#include "desktop/SchedulerView.hpp"
#include <cmath>
#include <charconv>
#include <iostream>
#include <sstream>
namespace fathom::desktop {
namespace {
constexpr std::int64_t previewCycleQuarterBeats=4;
scheduler::Owner previewLayoutOwner(){
    scheduler::Owner owner{};owner.id[6]=0x40;owner.id[8]=0x80;owner.generation=1;owner.epoch=1;return owner;
}
constexpr std::array<polyrhythm::Ratio,8> commonRatios{{{2,3},{3,2},{3,4},{4,3},{4,5},{5,4},{5,7},{7,5}}};
std::string ratioText(polyrhythm::Ratio ratio){return std::to_string(ratio.x)+":"+std::to_string(ratio.y);}
bool parseCount(const juce::String& text,int& value){
    const auto input=text.trim().toStdString();if(input.empty())return false;
    const auto parsed=std::from_chars(input.data(),input.data()+input.size(),value);
    return parsed.ec==std::errc{}&&parsed.ptr==input.data()+input.size();
}
struct LayerDisplay final {std::vector<double> phases;std::string phaseText;};
LayerDisplay layerDisplay(const scheduler::Plan& plan,scheduler::Role role){
    LayerDisplay result;std::ostringstream text;
    for(const auto& event:plan.events())if(event.role==role&&event.action==scheduler::Action::Attack){
        const auto n=event.structural.numerator(),d=event.structural.denominator();
        result.phases.push_back(static_cast<double>(n)/static_cast<double>(d*previewCycleQuarterBeats));
        if(result.phases.size()>1)text<<", ";
        text<<n;if(d!=1)text<<'/'<<d;
    }
    result.phaseText=text.str();return result;
}
}
std::vector<scheduler::Plan> previewPlans(scheduler::Owner owner,std::uint32_t rate,polyrhythm::Ratio ratio) {
    polyrhythm::validate(ratio);
    using namespace scheduler;
    PlanSpec spec;spec.owner=owner;spec.binding=1;spec.sourceBinding="synthetic:scheduler-preview-v1";
    spec.sampleRate=rate;spec.bpm=120;spec.cycle=Rational{previewCycleQuarterBeats};spec.intro=Rational{previewCycleQuarterBeats};
    for(int i=0;i<4;++i)spec.countIn.push_back({Rational{i},static_cast<std::uint32_t>(i+1),Role::CountIn,Action::Attack});
    auto add=[&](Rational at,std::uint32_t id,Role role){spec.events.push_back({at,id,role,Action::Attack});};
    for(int i=0;i<4;++i)add(Rational{i},static_cast<std::uint32_t>(100+i),Role::Reference);
    for(int i=0;i<8;++i)add(Rational{i,2},static_cast<std::uint32_t>(200+i),Role::Metronome);
    for(int i=0;i<ratio.x;++i)add(Rational{previewCycleQuarterBeats*i,ratio.x},static_cast<std::uint32_t>(300+i),Role::LayerA);
    for(int i=0;i<ratio.y;++i)add(Rational{previewCycleQuarterBeats*i,ratio.y},static_cast<std::uint32_t>(400+i),Role::LayerB);
    std::vector<Plan> plans;plans.push_back(compile(spec));spec.intro=Rational{};spec.countIn.clear();
    spec.bpm=126;plans.push_back(compile(spec));spec.bpm=132;plans.push_back(compile(spec));return plans;
}
void SchedulerView::updateRatioDisplay(){
    const auto plans=previewPlans(previewLayoutOwner(),44100,selectedRatio_);
    const auto layerA=layerDisplay(plans.front(),scheduler::Role::LayerA);
    const auto layerB=layerDisplay(plans.front(),scheduler::Role::LayerB);
    layerAPhases=layerA.phases;layerBPhases=layerB.phases;
    const auto ratio=ratioText(selectedRatio_);
    cycleHeading.setText("Shared cycle · 4 quarter beats · "+ratio+" · both layers align at phase 0",juce::dontSendNotification);
    cycleHeading.setTitle("Shared cycle: four quarter beats. "+ratio+" means "+std::to_string(selectedRatio_.x)+" Layer A attacks and "+std::to_string(selectedRatio_.y)+" Layer B attacks; both begin together at phase 0. The playhead follows the shared scheduler cursor.");
    layerALabel.setText(juce::String::fromUTF8("Layer A  ▲  ")+juce::String(layerAPhases.size())+" hits",juce::dontSendNotification);
    layerALabel.setTitle("Layer A: "+juce::String(layerAPhases.size())+" hits at quarter-beat phases "+layerA.phaseText+" in the four-quarter shared cycle. Teal triangle markers; first hit aligns with Layer B.");
    layerBLabel.setText(juce::String::fromUTF8("Layer B  ●  ")+juce::String(layerBPhases.size())+" hits",juce::dontSendNotification);
    layerBLabel.setTitle("Layer B: "+juce::String(layerBPhases.size())+" hits at quarter-beat phases "+layerB.phaseText+" in the same four-quarter shared cycle. Amber circle markers; first hit aligns with Layer A.");
    updateReturnDescription();
    ratioX_.setText(juce::String(selectedRatio_.x),juce::dontSendNotification);ratioY_.setText(juce::String(selectedRatio_.y),juce::dontSendNotification);
}
void SchedulerView::updateReturnDescription(){const auto ratio=ratioText(selectedRatio_);
    description.setText("Audio settings are shared across activities. Start begins sound.\nOne count-in bar, then four 4/4 cycles at quarter-note 120 BPM.\n"+ratio+" means "+std::to_string(selectedRatio_.x)+" Layer A hits and "+std::to_string(selectedRatio_.y)+" Layer B hits per cycle.\nNo practice recording; "+back.getButtonText().toStdString()+" after Stop and Finish check acknowledge this preview. Back disconnects; another preview needs Start.",juce::dontSendNotification);
}
scheduler::BlockOutcome PreviewSound::render(void* p,const output::Owner& owner,std::uint32_t rate,std::uint32_t frames,platform::Buses& buses) noexcept {
    auto& s=*static_cast<PreviewSound*>(p);s.buses=&buses;s.rate=rate;
    return s.stream.process(owner,rate,frames,consume,&s);
}
void PreviewSound::observe(void* p,const output::Snapshot& snapshot) noexcept {
    auto& s=*static_cast<PreviewSound*>(p);s.stream.observe(snapshot);
    if(snapshot.state!=output::State::Running)for(auto& v:s.voices)v.active=false;
}
bool PreviewSound::consume(void* p,std::uint64_t begin,std::uint32_t prefix,const scheduler::Fact* facts,std::size_t count) noexcept {
    auto& s=*static_cast<PreviewSound*>(p);std::size_t event=0;
    constexpr std::array<double,4> frequency{220,880,440,660};
    for(std::uint32_t frame=0;frame<prefix;++frame) {
        const auto absolute=begin+frame;
        while(event<count && facts[event].frame<=absolute) {
            const auto& f=facts[event++];if(f.kind!=scheduler::FactKind::Event)continue;
            const auto bus=f.role==scheduler::Role::CountIn?1U:static_cast<unsigned>(f.role);
            if(bus>=4)return false;
            auto& v=s.voices[bus];v.attack=f.frame;v.active=f.action==scheduler::Action::Attack;
        }
        for(std::size_t bus=0;bus<4;++bus) {
            auto& v=s.voices[bus];float value=0;
            if(v.active) {
                const double t=static_cast<double>(absolute-v.attack)/s.rate;
                if(t>=0.025)v.active=false;
                else {const double envelope=std::sin(3.14159265358979323846*t/0.025);value=static_cast<float>(0.3*envelope*envelope*std::sin(6.28318530717958647692*frequency[bus]*t));}
            }
            (*s.buses)[bus][0][frame]=value;(*s.buses)[bus][1][frame]=value;
        }
    }
    return true;
}
SchedulerView::SchedulerView() {
    title.setText(juce::String::fromUTF8("RHYTHM — SYNTHETIC SOUND-CHECK PREVIEW"),juce::dontSendNotification);title.setFont(juce::FontOptions{28.0f,juce::Font::bold});
    title.setComponentID("rhythm-title");title.setTitle("Read-only Rhythm preview: synthetic sound-check only; no practice recording or curriculum credit.");
    description.setComponentID("rhythm-description");description.setTitle("Read-only Rhythm preview: shared Audio settings, explicit Start and no practice recording.");
    description.setText("Use Audio settings for speakers, headphones and volume. These shared settings apply across the other activities; Start begins sound.\nOne count-in bar, then four cycles: 4/4, quarter beat, 120 BPM.\nThis preview does not record practice.\n"+back.getButtonText().toStdString()+" after Stop and Finish check acknowledge this preview. Back disconnects; another preview needs Start.",juce::dontSendNotification);
    status.setComponentID("rhythm-status");status.setTitle("Read-only Rhythm preview lifecycle, output state, next action and safe release boundary.");
    cycleHeading.setComponentID("rhythm-shared-cycle");
    layerALabel.setComponentID("rhythm-layer-a");
    layerALabel.setColour(juce::Label::textColourId,appearance::colour(0xff6bd5cb));
    layerBLabel.setComponentID("rhythm-layer-b");
    layerBLabel.setColour(juce::Label::textColourId,appearance::colour(0xffffc857));
    ratioPreset_.setComponentID("rhythm-ratio-preset");ratioPreset_.setTitle("Choose a common X:Y ratio or Custom; X is Layer A hits and Y is Layer B hits.");
    for(std::size_t i=0;i<commonRatios.size();++i)ratioPreset_.addItem(ratioText(commonRatios[i]),static_cast<int>(i)+1);
    ratioPreset_.addItem("Custom X:Y",9);ratioPreset_.setSelectedId(selectedRatioChoice_,juce::dontSendNotification);
    ratioXLabel_.setComponentID("rhythm-ratio-x-label");ratioXLabel_.setText("A count",juce::dontSendNotification);ratioXLabel_.setTitle("X is the number of Layer A attacks per shared cycle.");
    ratioYLabel_.setComponentID("rhythm-ratio-y-label");ratioYLabel_.setText("B count",juce::dontSendNotification);ratioYLabel_.setTitle("Y is the number of Layer B attacks per shared cycle.");
    ratioX_.setComponentID("rhythm-ratio-x");ratioX_.setTitle("Layer A literal hit count X, from 1 through 16.");ratioX_.setInputRestrictions(2,"0123456789");
    ratioY_.setComponentID("rhythm-ratio-y");ratioY_.setTitle("Layer B literal hit count Y, from 1 through 16.");ratioY_.setInputRestrictions(2,"0123456789");
    ratioApply_.setComponentID("rhythm-ratio-apply");ratioApply_.setTitle("Apply the custom Layer A:Layer B ratio after existing validation.");
    ratioMessage_.setComponentID("rhythm-ratio-message");ratioMessage_.setTitle("Ratio selection validation result; invalid input is refused without changing the selected ratio.");
    for(auto* l:{&title,&description,&status,&progress,&cycleHeading,&layerALabel,&layerBLabel,&ratioXLabel_,&ratioYLabel_,&ratioMessage_})addAndMakeVisible(*l);
    for(auto* b:{&connect,&enable,&start,&stop,&tempo,&back,&ratioApply_})addAndMakeVisible(*b);
    addAndMakeVisible(ratioPreset_);addAndMakeVisible(ratioX_);addAndMakeVisible(ratioY_);
    updateRatioDisplay();
    connect.setVisible(false);enable.setVisible(false);addAndMakeVisible(audioSettings_);addAndMakeVisible(done);
    audioSettings_.setComponentID("rhythm-audio-settings");audioSettings_.setTitle("Open shared Audio settings before starting the Rhythm preview.");
    start.setComponentID("rhythm-start");start.setTitle("Start Rhythm preview synthetic sound; no practice recording is created.");
    stop.setComponentID("rhythm-stop");stop.setTitle("Stop Rhythm preview and retain the sound-check outcome until Finish check.");
    tempo.setComponentID("rhythm-tempo");tempo.setTitle("Change the Rhythm preview tempo for its next cycle.");
    done.setComponentID("rhythm-finish");done.setTitle("Finish the Rhythm preview check and release its retained output safely.");
    back.setComponentID("rhythm-back");back.setTitle("Return Home after the Rhythm preview is safely stopped.");
    for (auto* b : {&audioSettings_, &connect, &enable, &start, &stop, &tempo, &done, &back,&ratioApply_}) { b->setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb)); b->setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c)); b->setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c)); }
    ratioPreset_.onChange=[this]{
        if(started){ratioPreset_.setSelectedId(selectedRatioChoice_,juce::dontSendNotification);return;}
        const auto selected=ratioPreset_.getSelectedId();
        if(selected>=1&&selected<=static_cast<int>(commonRatios.size())){selectedRatioChoice_=selected;selectedRatio_=commonRatios[static_cast<std::size_t>(selected-1)];ratioX_.setText(juce::String(selectedRatio_.x),juce::dontSendNotification);ratioY_.setText(juce::String(selectedRatio_.y),juce::dontSendNotification);ratioMessage_.setText(juce::String{},juce::dontSendNotification);updateRatioDisplay();}
        else if(selected==9){selectedRatioChoice_=9;ratioX_.setText(juce::String(selectedRatio_.x),juce::dontSendNotification);ratioY_.setText(juce::String(selectedRatio_.y),juce::dontSendNotification);ratioMessage_.setText("Enter distinct literal counts, then apply. Current ratio remains "+juce::String(ratioText(selectedRatio_)),juce::dontSendNotification);}
        else ratioPreset_.setSelectedId(selectedRatioChoice_,juce::dontSendNotification);
        timerCallback();
    };
    ratioApply_.onClick=[this]{int x{},y{};if(started){ratioMessage_.setText("Stop and finish the preview before changing its ratio.",juce::dontSendNotification);return;}if(!parseCount(ratioX_.getText(),x)||!parseCount(ratioY_.getText(),y)){ratioMessage_.setText("Enter whole-number X and Y counts.",juce::dontSendNotification);return;}try{polyrhythm::validate({x,y});}catch(const std::exception& e){ratioMessage_.setText(juce::String(e.what()),juce::dontSendNotification);return;}selectedRatio_={x,y};selectedRatioChoice_=9;ratioPreset_.setSelectedId(9,juce::dontSendNotification);ratioMessage_.setText(juce::String{},juce::dontSendNotification);updateRatioDisplay();timerCallback();};
    audioSettings_.onClick=[this]{if(onAudioSettings)onAudioSettings();};
    connect.onClick=[this]{connectOutput();};enable.onClick=[this]{enableOutput();};
    done.onClick=[this]{finishCheck();};
    start.onClick=[this] {
        if(started || resolving || !sound||output.status().lifecycle.state!=output::State::Ready)return;
        if(!sameAudioCapability(settingsOutputCapability(),preparedCapability_)){localError_="Output changed. Open Audio settings and reconnect explicitly; no preview started.";audioRelease();return;}
        const auto uuid=juce::Uuid();std::copy_n(uuid.getRawData(),16,owner.id.begin());owner.id[6]=static_cast<std::uint8_t>((owner.id[6]&15)|0x40);owner.id[8]=static_cast<std::uint8_t>((owner.id[8]&63)|0x80);
        owner.generation=1;owner.epoch=output.status().lifecycle.request.epoch;
        try {auto next=std::make_unique<PreviewSound>();next->stream.prepare(previewPlans(owner,output.status().lifecycle.request.format.rate,selectedRatio_),4,2,1);sound->publish(std::move(next));view={};localError_.clear();retained=false;started=true;stopRequested=false;cancelledStart=false;if(!send(platform::OutputCommand::Start)){retainedOutput=output.shutdown();retainedTimeline=sound->current()->stream.quiescentView();retained=true;if(!retainedOutput.ownsOutcome&&output.disconnect()){sound.reset();started=false;}}}
        catch(const std::exception& e){localError_=e.what();status.setText(localError_,juce::dontSendNotification);}
    };
    stop.onClick=[this]{send(platform::OutputCommand::Stop);};
    tempo.onClick=[this]{if(sound&&sound->current() && sound->current()->stream.tempo({owner,1,1,2}))tempo.setEnabled(false);};
    back.onClick=[this]{if(audioCanRelease()&&audioRelease()){if(onBack)onBack();}else{send(platform::OutputCommand::Stop);status.setText("Stop and Finish check before leaving. No practice is recorded.",juce::dontSendNotification);}};
    startTimer(30);timerCallback();
}
SchedulerView::~SchedulerView(){stopTimer();stopAndRetain();}
bool SchedulerView::connectOutput(const platform::OutputCapability* expected){
    if(started||resolving||output.status().lifecycle.state!=output::State::Closed)return false;
    if(output.status().cleanupFailed)return false;
    const auto cap=settingsOutputCapability();if(expected&&!sameAudioCapability(cap,*expected))return false;
    sound=std::make_unique<PreparedToolSound<PreviewSound>>();preparedCapability_=cap;localError_.clear();
    return connectSettingsOutput(output,cap,{cap.rate,cap.valid?std::clamp(256U,cap.minFrames,cap.maxFrames):0},sound.get(),PreparedToolSound<PreviewSound>::observe,PreparedToolSound<PreviewSound>::render);
}
bool SchedulerView::enableOutput(){const auto s=output.status().lifecycle;if(s.state!=output::State::Observed)return false;platform::Control c;c.op=platform::OutputCommand::Acknowledge;c.epoch=s.request.epoch;c.token=s.observationToken;return output.send(c);}
bool SchedulerView::applyCommonMix(const output::MixSettings& value){if(!queueAudioMix(output,value))return false;commonMix_=value;return true;}
bool SchedulerView::audioCanRelease()const{const auto s=output.status().lifecycle;return !started&&!resolving&&!s.ownsOutcome&&!s.pendingOutcome&&s.state!=output::State::Running&&s.state!=output::State::Paused;}
bool SchedulerView::audioRelease(){if(!audioCanRelease()||!output.disconnect())return false;if(audioPolling_){platform::NativeEvent e;while(output.nextEvent(e)){}}sound.reset();return true;}
bool SchedulerView::requestClose(){
    if(audioCanRelease())return audioRelease();
    const auto s=output.status().lifecycle;
    if(started&&!resolving&&!s.pendingOutcome&&!stopRequested)send(platform::OutputCommand::Stop);
    return false;
}
bool SchedulerView::finishCheck(){const auto s=output.status().lifecycle;if(resolving||!s.pendingOutcome||!(s.owner==owner))return false;retainedOutput=s;retainedTimeline=view;retained=true;platform::Control c;c.op=platform::OutputCommand::ResolveOutcome;c.owner=owner;c.epoch=s.request.epoch;resolving=output.send(c);return resolving;}
bool SchedulerView::send(platform::OutputCommand op){if(op==platform::OutputCommand::Stop)stopRequested=true;platform::Control c;c.op=op;c.owner=owner;c.epoch=output.status().lifecycle.request.epoch;c.requestedNs=platform::monotonicNs();return output.send(c);}
void SchedulerView::stopAndRetain(){
    retainedOutput=output.shutdown();if(sound&&sound->current())retainedTimeline=sound->current()->stream.quiescentView();retained=true;
    if(!retainedOutput.ownsOutcome)output.disconnect();
    // Synthetic sound check only. Keep terminal facts in this view through destruction;
    // no learner Attempt is created or silently acknowledged as a persistence commit.
}
void SchedulerView::timerCallback(){
    if(audioPolling_)output.service();platform::NativeEvent e;while(audioPolling_&&output.nextEvent(e)){if(started&&stopRequested&&e.kind==71&&e.epoch==owner.epoch)cancelledStart=true;if(onNativeEvent)onNativeEvent(e);}
    if(sound&&sound->current()){scheduler::Fact f;while(sound->current()->stream.nextFact(f)){}while(sound->current()->stream.nextView(view)){}
        progress.setText("Cycle "+juce::String(view.cursor.completedCycles)+" of 4 · "+juce::String(view.tempoIndex==0?120:view.tempoIndex==1?126:132)+" BPM",juce::dontSendNotification);}
    auto s=output.status().lifecycle;
    if(cancelledStart&&!s.ownsOutcome&&s.state==output::State::Ready){
        retainedOutput=output.shutdown();if(sound&&sound->current())retainedTimeline=sound->current()->stream.quiescentView();retained=true;
        if(output.disconnect()){sound.reset();started=false;cancelledStart=false;stopRequested=false;s=output.status().lifecycle;}
    }
    if(resolving&&!s.ownsOutcome&&!s.pendingOutcome){
        if(sound&&sound->current())retainedTimeline=sound->current()->stream.quiescentView();
        if(s.state==output::State::Ready&&s.fault==output::Fault::None&&s.owner==owner){started=false;resolving=false;stopRequested=false;}
        else if(output.disconnect()){sound.reset();started=false;resolving=false;s=output.status().lifecycle;}
    }
    done.setEnabled(!resolving&&s.pendingOutcome&&s.owner==owner);
    const auto displayedState=s.state==output::State::Closed?std::string{"Closed · "+std::string(output::stateText(s.state))}:std::string(output::stateText(s.state));
    status.setText(!localError_.empty()?localError_:retained&&started&&output.error().empty()?"Preview stopped. Finish check acknowledges its original outcome; no practice recorded.":output.error().empty()?(s.state==output::State::Ready&&!started?"Output ready and stopped. Start preview is explicit; Back disconnects.":displayedState):output.error(),juce::dontSendNotification);
    connect.setEnabled(!started && s.state==output::State::Closed);enable.setEnabled(s.state==output::State::Observed);
    start.setEnabled(!started && s.state==output::State::Ready);stop.setEnabled(s.state==output::State::Running);tempo.setVisible(started && s.state==output::State::Running);
    const bool ratioEditable=!started&&s.state!=output::State::Running&&s.state!=output::State::Paused;
    ratioPreset_.setEnabled(ratioEditable);const bool customChoice=ratioPreset_.getSelectedId()==9;
    ratioX_.setEnabled(ratioEditable&&customChoice);ratioY_.setEnabled(ratioEditable&&customChoice);ratioApply_.setEnabled(ratioEditable&&customChoice);
    if((s.state==output::State::Unresolved || s.state==output::State::Fault) && !retained){retainedOutput=s;retainedTimeline=view;retained=true;status.setText(s.state==output::State::Fault?output.error():"Preview stopped. Finish check releases audio; no practice recorded.",juce::dontSendNotification);}
    repaint();
}
void SchedulerView::paint(juce::Graphics& g){
    g.fillAll(appearance::colour(0xff10212c));const auto compact=getWidth()<800;
    const int cycleLeft=compact?144:190,cycleRight=getWidth()-24,cycleWidth=std::max(1,cycleRight-cycleLeft);
    const int layerAY=compact?327:396,layerBY=compact?349:420;
    g.setColour(appearance::colour(0xff29404d));g.fillRect(cycleLeft,layerAY-1,cycleWidth,2);g.fillRect(cycleLeft,layerBY-1,cycleWidth,2);
    // No timer interpolation: the scheduler's copied absolute callback cursor drives one shared playhead.
    const double span=static_cast<double>(view.phaseSpan.n)/static_cast<double>(view.phaseSpan.d);
    const double phase=span>0?std::clamp(static_cast<double>(view.cursor.processedThrough-view.phaseOrigin)/span,0.0,1.0):0.0;
    const int playheadX=cycleLeft+static_cast<int>(cycleWidth*phase);
    g.setColour(appearance::colour(0xffeaf4f4));g.drawLine(static_cast<float>(playheadX),static_cast<float>(layerAY-7),static_cast<float>(playheadX),static_cast<float>(layerBY+7),2.0f);
    for(const auto hit:layerAPhases){const auto x=cycleLeft+static_cast<int>(cycleWidth*hit);juce::Path triangle;triangle.startNewSubPath(static_cast<float>(x),static_cast<float>(layerAY-6));triangle.lineTo(static_cast<float>(x-6),static_cast<float>(layerAY+6));triangle.lineTo(static_cast<float>(x+6),static_cast<float>(layerAY+6));triangle.closeSubPath();g.setColour(appearance::colour(0xff6bd5cb));g.fillPath(triangle);}
    for(const auto hit:layerBPhases){const auto x=cycleLeft+static_cast<int>(cycleWidth*hit);g.setColour(appearance::colour(0xffffc857));g.fillEllipse(static_cast<float>(x-5),static_cast<float>(layerBY-5),10.0f,10.0f);}
}
void SchedulerView::resized(){
    if(getWidth()<800){
        const auto w=std::max(1,getWidth()-48);
        if(title.getText().startsWith("RHYTHM")&&title.getText().contains("SYNTHETIC SOUND-CHECK PREVIEW"))
            title.setText(juce::String::fromUTF8("Rhythm — Synthetic sound-check preview"),juce::dontSendNotification);
        title.setBounds(24,16,w,40);description.setBounds(24,64,w,78);status.setBounds(24,148,w,38);progress.setBounds(24,258,w,32);
        cycleHeading.setBounds(24,292,w,22);layerALabel.setBounds(24,316,112,22);layerBLabel.setBounds(24,338,112,22);
        ratioPreset_.setBounds(24,190,160,28);ratioXLabel_.setBounds(192,190,54,28);ratioX_.setBounds(247,190,46,28);ratioYLabel_.setBounds(300,190,54,28);ratioY_.setBounds(355,190,46,28);ratioApply_.setBounds(410,190,112,28);ratioMessage_.setBounds(24,220,w,20);
        audioSettings_.setBounds(24,372,180,34);start.setBounds(216,372,150,34);stop.setBounds(378,372,100,34);done.setBounds(486,372,std::max(1,getWidth()-510),34);
        tempo.setBounds(24,418,230,36);back.setBounds(24,getHeight()-48,100,36);
        return;
    }
    const auto w=getWidth()-80;
    if(title.getText().startsWith("Rhythm")&&title.getText().contains("Synthetic sound-check preview"))
        title.setText(juce::String::fromUTF8("RHYTHM — SYNTHETIC SOUND-CHECK PREVIEW"),juce::dontSendNotification);
    title.setBounds(40,30,w,45);description.setBounds(40,95,w,72);status.setBounds(40,174,w,44);ratioPreset_.setBounds(40,224,180,28);ratioXLabel_.setBounds(228,224,56,28);ratioX_.setBounds(285,224,54,28);ratioYLabel_.setBounds(346,224,56,28);ratioY_.setBounds(403,224,54,28);ratioApply_.setBounds(465,224,120,28);ratioMessage_.setBounds(40,252,w,20);
    audioSettings_.setBounds(40,282,180,36);done.setBounds(670,282,160,36);start.setBounds(385,282,150,36);stop.setBounds(550,282,100,36);progress.setBounds(40,330,w,24);cycleHeading.setBounds(40,356,w,24);layerALabel.setBounds(40,384,142,24);layerBLabel.setBounds(40,408,142,24);tempo.setBounds(40,447,230,36);back.setBounds(40,getHeight()-72,100,36);
}
}
