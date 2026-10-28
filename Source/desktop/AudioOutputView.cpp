#include "desktop/Appearance.hpp"
#include "desktop/AudioOutputView.hpp"
#include <algorithm>
#include <charconv>
namespace fathom::desktop {
double AudioOutputView::GainSlider::getValueFromText(const juce::String& input){
    auto text=input.trim().toStdString();if(!text.empty()&&text.back()=='%')text.pop_back();int value{};
    const auto parsed=std::from_chars(text.data(),text.data()+text.size(),value);
    invalid_=text.empty()||parsed.ec!=std::errc{}||parsed.ptr!=text.data()+text.size()||value<0||value>100;
    if(invalid_){if(onInvalidText)onInvalidText();return getValue();}
    if(onValidText)onValidText();return value;
}
AudioOutputView::AudioOutputView() {
    title.setText(juce::String::fromUTF8("AUDIO — SHARED OUTPUT SETTINGS"),juce::dontSendNotification);title.setFont(juce::FontOptions{28.0f,juce::Font::bold});
    description.setComponentID("shared-audio-description");
    status.setComponentID("shared-audio-status");
    status.setTitle("Read-only shared Audio lifecycle, output state, next action and safe release boundary.");
    description.setText("Mix changes apply now for this session. Home > Setup / resume setup > Finish saves this mix.\nConnect macOS output, then Enable. Only Start or Play in the calling activity begins sound.\nLocal tools share this mix. Back preserves it; Disconnect requires safe release. Playback and output permission are never restored from settings.",juce::dontSendNotification);
    description.setTitle("Read-only shared Audio: Connect/Enable is explicit; activity controls begin sound across local tools.");
    unboundState_.setComponentID("audio-unbound-state");
    unboundState_.setTitle("Shared Audio unbound state marker.");
    unboundState_.setFont(juce::FontOptions{14.0f,juce::Font::bold});
    unboundState_.setColour(juce::Label::textColourId,appearance::colour(0xffa9bbc5));
    unboundState_.setText("Shared Audio settings are waiting for the calling activity.",juce::dontSendNotification);
    for(auto* c:{&title,&status,&description,&unboundState_}) addAndMakeVisible(*c);
    for(auto* b:{&connect,&enable,&disconnect,&back}) addAndMakeVisible(*b);
    connect.setComponentID("audio-connect");connect.setTitle("Connect shared macOS audio output.");
    connect.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));connect.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));connect.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    enable.setComponentID("audio-enable");enable.setTitle("Enable observed shared macOS audio output.");
    enable.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));enable.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));enable.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    disconnect.setComponentID("audio-disconnect");disconnect.setTitle("Disconnect shared audio when current activity is safely releasable.");
    disconnect.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));disconnect.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));disconnect.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    back.setComponentID("audio-back");back.setTitle("Return to the calling activity without changing shared Audio settings.");
    back.addKeyListener(this);
    back.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));back.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));back.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    connect.onClick=[this] {if(session_)session_->connect();timerCallback();};
    enable.onClick=[this] {if(session_)session_->enable();timerCallback();};
    disconnect.onClick=[this] {if(session_)session_->disconnect();timerCallback();};
    back.onClick=[this] {
        if(onBack){onBack();return;}
        status.setText("Back is unavailable from Audio settings until the existing caller navigation is connected. The shared Audio state remains here; no output, activity or curriculum credit was changed.",juce::dontSendNotification);
    };
    const char* names[]{"Master","Reference","Metronome","Rhythm A","Rhythm B"};
    const char* gainIds[]{"audio-master-volume","audio-reference-volume","audio-metronome-volume","audio-rhythm-a-volume","audio-rhythm-b-volume"};
    const char* muteIds[]{"audio-master-mute","audio-reference-mute","audio-metronome-mute","audio-rhythm-a-mute","audio-rhythm-b-mute"};
    for(std::size_t i=0;i<gains.size();++i) {
        labels[i].setText(names[i],juce::dontSendNotification);addAndMakeVisible(labels[i]);
        gains[i].setComponentID(gainIds[i]);gains[i].setColour(juce::Slider::thumbColourId,appearance::colour(0xff6bd5cb));gains[i].setColour(juce::Slider::trackColourId,appearance::colour(0xff6bd5cb));gains[i].setColour(juce::Slider::backgroundColourId,appearance::colour(0xff10212c));gains[i].onInvalidText=[this]{validationMessage_="Volume: enter a whole percentage from 0 to 100. Prior value retained.";};gains[i].onValidText=[this]{validationMessage_.clear();};gains[i].setRange(0,100,1);gains[i].setValue(50,juce::dontSendNotification);gains[i].setTextBoxStyle(juce::Slider::TextBoxRight,false,64,26);gains[i].setTitle(juce::String(names[i])+" volume");gains[i].onValueChange=[this,i] {validationMessage_.clear();if(i==0)settings.master=static_cast<int>(gains[i].getValue());else settings.bus[i-1]=static_cast<int>(gains[i].getValue());applyMix();};addAndMakeVisible(gains[i]);
        mutes[i].setComponentID(muteIds[i]);mutes[i].setButtonText("Mute");mutes[i].setTitle(juce::String(names[i])+" mute");mutes[i].setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));mutes[i].setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));mutes[i].setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));mutes[i].onClick=[this,i] {if(i==0)settings.masterMute=mutes[i].getToggleState();else {const auto bit=static_cast<std::uint8_t>(1U<<(i-1));settings.muteMask=mutes[i].getToggleState()?static_cast<std::uint8_t>(settings.muteMask|bit):static_cast<std::uint8_t>(settings.muteMask&~bit);}applyMix();};addAndMakeVisible(mutes[i]);
    }
    const char* soloIds[]{"audio-rhythm-a-solo","audio-rhythm-b-solo"};
    for(std::size_t i=0;i<2;++i) {solos[i].setComponentID(soloIds[i]);solos[i].setButtonText("Solo");solos[i].setTitle(i==0?"Rhythm A solo":"Rhythm B solo");solos[i].setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));solos[i].setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));solos[i].setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));solos[i].onClick=[this] {settings.soloAB=static_cast<std::uint8_t>((solos[0].getToggleState()?1:0)|(solos[1].getToggleState()?2:0));applyMix();};addAndMakeVisible(solos[i]);}
    auto configureControl=[&](juce::Component& component,int order){component.setWantsKeyboardFocus(true);component.setExplicitFocusOrder(order);};
    configureControl(connect,1);configureControl(enable,2);configureControl(disconnect,3);
    int order=4;for(std::size_t i=0;i<gains.size();++i){configureControl(gains[i],order++);configureControl(mutes[i],order++);if(i>=3)configureControl(solos[i-3],order++);}configureControl(back,16);
    setWantsKeyboardFocus(true);startTimer(30);timerCallback();
}
AudioOutputView::~AudioOutputView(){stopTimer();}
bool AudioOutputView::keyPressed(const juce::KeyPress& key,juce::Component* origin){
    if(origin!=&back||key.getKeyCode()!=juce::KeyPress::spaceKey||!back.isShowing()||!back.isEnabled())return false;
    if(backSpaceHeld_)return true;
    backSpaceHeld_=true;back.triggerClick();return true;
}
bool AudioOutputView::keyStateChanged(bool,juce::Component*){
    if(!juce::KeyPress::isKeyCurrentlyDown(juce::KeyPress::spaceKey))backSpaceHeld_=false;
    return false;
}
void AudioOutputView::applyMix(){if(session_)session_->selectMix(settings);timerCallback();}
void AudioOutputView::timerCallback(){
    unboundState_.setVisible(session_==nullptr);
    if(!session_){status.setText("Audio settings awaits its playback view.",juce::dontSendNotification);return;}
    const auto s=session_->snapshot();settings=session_->selected();
    const auto notice=!validationMessage_.empty()?validationMessage_:!session_->message().empty()?session_->message():s.state==output::State::Observed?std::string{"Output is connected and observed. Choose Enable audio to prepare; Start or Play in the current activity begins sound."}:s.state==output::State::Closed&&session_->canConnect()?std::string{"Next action: choose Connect audio, then choose Enable audio; Start or Play in the current activity begins sound."}:(!session_->canRelease()||!session_->canConnect())?session_->recoveryMessage():std::string{};
    status.setText(session_->name()+" | "+session_->deviceName()+" | "+output::stateText(s.state)+(notice.empty()?"":"\n"+notice),juce::dontSendNotification);
    enable.setEnabled(s.state==output::State::Observed);connect.setEnabled(session_->canConnect());
    disconnect.setEnabled(session_->canRelease()&&s.state!=output::State::Closed);
    for(std::size_t i=0;i<gains.size();++i){gains[i].setValue(i==0?settings.master:settings.bus[i-1],juce::dontSendNotification);mutes[i].setToggleState(i==0?settings.masterMute:bool(settings.muteMask&(1U<<(i-1))),juce::dontSendNotification);}
    for(std::size_t i=0;i<solos.size();++i)solos[i].setToggleState(bool(settings.soloAB&(1U<<i)),juce::dontSendNotification);
}
void AudioOutputView::paint(juce::Graphics& g){g.fillAll(appearance::colour(0xff10212c));}
void AudioOutputView::resized(){
    if(getWidth()<800){
        const auto w=std::max(1,getWidth()-48);
        if(title.getText().startsWith("AUDIO")&&title.getText().contains("SHARED OUTPUT SETTINGS"))
            title.setText(juce::String::fromUTF8("Audio — Shared output settings"),juce::dontSendNotification);
        title.setBounds(24,16,w,40);description.setBounds(24,64,w,88);unboundState_.setBounds(24,154,w,22);status.setBounds(24,180,w,82);
        connect.setBounds(24,276,168,34);enable.setBounds(204,276,160,34);disconnect.setBounds(376,276,std::max(1,getWidth()-400),34);
        for(int i=0;i<5;++i){const auto y=324+i*40;labels[static_cast<std::size_t>(i)].setBounds(24,y,96,36);gains[static_cast<std::size_t>(i)].setBounds(128,y,std::max(1,getWidth()-320),36);mutes[static_cast<std::size_t>(i)].setBounds(getWidth()-184,y,80,36);if(i>=3)solos[static_cast<std::size_t>(i-3)].setBounds(getWidth()-96,y,72,36);}
        back.setBounds(24,getHeight()-48,280,36);
        return;
    }
    const auto w=getWidth()-80;title.setBounds(40,30,w,45);description.setBounds(40,88,w,88);unboundState_.setBounds(40,178,w,22);status.setBounds(40,206,w,72);
    if(title.getText().startsWith("Audio")&&title.getText().contains("Shared output settings"))
        title.setText(juce::String::fromUTF8("AUDIO — SHARED OUTPUT SETTINGS"),juce::dontSendNotification);
    connect.setBounds(40,278,180,36);enable.setBounds(240,278,160,36);disconnect.setBounds(420,278,160,36);
    for(int i=0;i<5;++i){const auto y=320+i*40;labels[static_cast<std::size_t>(i)].setBounds(40,y,110,36);gains[static_cast<std::size_t>(i)].setBounds(160,y,w-370,36);mutes[static_cast<std::size_t>(i)].setBounds(getWidth()-240,y,90,36);if(i>=3)solos[static_cast<std::size_t>(i-3)].setBounds(getWidth()-140,y,90,36);}
    back.setBounds(40,getHeight()-48,280,36);
}
}
