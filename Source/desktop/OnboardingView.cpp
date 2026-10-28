#include "desktop/OnboardingView.hpp"
#include "desktop/Appearance.hpp"
#include <algorithm>
#include <sstream>
#if defined(FATHOM_ONBOARDING_RECEIVER_TRACE)
#include <cstdio>
#endif

namespace fathom::desktop {
namespace {
#if defined(FATHOM_ONBOARDING_RECEIVER_TRACE)
// Private receiver fixture only. Observation must not consume or transform keys.
struct SetupReceiverTrace final : juce::KeyListener {
    bool keyPressed(const juce::KeyPress& key, juce::Component* component) override {
        const auto code=key.getKeyCode();
        if(code!=juce::KeyPress::spaceKey&&code!=juce::KeyPress::returnKey&&code!=juce::KeyPress::tabKey)return false;
        const auto* focused=juce::Component::getCurrentlyFocusedComponent();
        std::fprintf(stderr,"SETUP_RECEIVER key=%d text=%u target=%s focused=%s exact_focus=%d enabled=%d showing=%d\n",
            code,static_cast<unsigned>(key.getTextCharacter()),component->getComponentID().toRawUTF8(),
            focused?focused->getComponentID().toRawUTF8():"none",focused==component,component->isEnabled(),component->isShowing());
        std::fflush(stderr);
        return false;
    }
    bool keyStateChanged(bool down,juce::Component* component) override {
        std::fprintf(stderr,"SETUP_RECEIVER state=%d target=%s space_down=%d return_down=%d\n",down,
            component->getComponentID().toRawUTF8(),juce::KeyPress::isKeyCurrentlyDown(juce::KeyPress::spaceKey),
            juce::KeyPress::isKeyCurrentlyDown(juce::KeyPress::returnKey));
        std::fflush(stderr);
        return false;
    }
};
SetupReceiverTrace setupReceiverTrace;
int setupReceiverModelEvents{};
#endif
constexpr std::uint32_t background = 0xff10212c, panel = 0xff172e3b;
constexpr std::uint32_t ink = 0xffdce8ed, accent = 0xff6bd5cb;
const char* appearanceLabel(setup::Appearance value) {
    switch(value) {
        case setup::Appearance::Default: return "Default (current Fathom appearance)";
        case setup::Appearance::Light: return "Light";
        case setup::Appearance::Dark: return "Dark";
    }
    return "Unknown";
}
int stepNumber(setup::Step step) {
    switch(step) {
        case setup::Step::Welcome: return 1;
        case setup::Step::Experience: return 2;
        case setup::Step::Appearance: return 3;
        case setup::Step::Guitar: return 4;
        case setup::Step::Audio: return 5;
        case setup::Step::Summary: return 6;
    }
    return 1;
}
void label(juce::Label& value, const char* id, float size) {
    value.setComponentID(id);
    value.setFont(juce::FontOptions{size});
    value.setJustificationType(juce::Justification::topLeft);
    value.setColour(juce::Label::textColourId, appearance::colour(ink));
}
}
bool OnboardingView::ActionButton::keyPressed(const juce::KeyPress& key) {
    if(key.getKeyCode()==juce::KeyPress::spaceKey||key.getKeyCode()==juce::KeyPress::returnKey) {
        auto& held=key.getKeyCode()==juce::KeyPress::spaceKey?spaceHeld_:returnHeld_;
        if(held)return true;
        held=true;
        if(isEnabled())triggerClick();
        return true;
    }
    return juce::TextButton::keyPressed(key);
}
bool OnboardingView::ActionButton::keyStateChanged(bool) {
    if(!juce::KeyPress::isKeyCurrentlyDown(juce::KeyPress::spaceKey))spaceHeld_=false;
    if(!juce::KeyPress::isKeyCurrentlyDown(juce::KeyPress::returnKey))returnHeld_=false;
    return false;
}
bool OnboardingView::ChoiceButton::keyPressed(const juce::KeyPress& key) {
#if defined(FATHOM_ONBOARDING_RECEIVER_TRACE)
    if(key.getKeyCode()==juce::KeyPress::spaceKey||key.getKeyCode()==juce::KeyPress::returnKey) {
        std::fprintf(stderr,"SETUP_HANDLER key=%d target=%s space_held=%d return_held=%d enabled=%d\n",key.getKeyCode(),
            getComponentID().toRawUTF8(),spaceHeld_,returnHeld_,isEnabled());
        std::fflush(stderr);
    }
#endif
    if(key.getKeyCode()==juce::KeyPress::spaceKey||key.getKeyCode()==juce::KeyPress::returnKey) {
        auto& held=key.getKeyCode()==juce::KeyPress::spaceKey?spaceHeld_:returnHeld_;
        if(held)return true;
        held=true;
        if(isEnabled())triggerClick();
        return true;
    }
    return juce::ToggleButton::keyPressed(key);
}
bool OnboardingView::ChoiceButton::keyStateChanged(bool) {
    if(!juce::KeyPress::isKeyCurrentlyDown(juce::KeyPress::spaceKey))spaceHeld_=false;
    if(!juce::KeyPress::isKeyCurrentlyDown(juce::KeyPress::returnKey))returnHeld_=false;
    return false;
}
OnboardingView::OnboardingView() {
    label(progress_,"onboarding-progress",14.0f);
    label(title_,"onboarding-title",32.0f);
    label(intro_,"onboarding-intro",17.0f);
    label(detail_,"onboarding-detail",16.0f);
    label(status_,"onboarding-status",15.0f);
    label(persistence_,"onboarding-persistence",14.0f);
    for(auto* value:{&progress_,&title_,&intro_,&detail_,&status_,&persistence_})addAndMakeVisible(*value);
    title_.setTitle("Fathom first-run setup step.");
    detail_.setTitle("Current setup choices and next action.");
    status_.setTitle("Setup status and recovery guidance.");
    persistence_.setTitle("Whether setup choices are kept for this session or saved locally.");
    for(std::size_t i=0;i<choices_.size();++i) {
        auto& choice=choices_[i];
        choice.setClickingTogglesState(true);
        choice.setRadioGroupId(8301);
        choice.setWantsKeyboardFocus(true);
        choice.setExplicitFocusOrder(static_cast<int>(i)+1);
#if defined(FATHOM_ONBOARDING_RECEIVER_TRACE)
        choice.addKeyListener(&setupReceiverTrace);
#endif
        addChildComponent(choice);
        label(choiceDescriptions_[i],"onboarding-choice-description",15.0f);
        addChildComponent(choiceDescriptions_[i]);
    }
    auto control=[this](ActionButton& button,const char* id,const char* title,int order) {
        button.setComponentID(id);button.setTitle(title);
        button.setWantsKeyboardFocus(true);button.setExplicitFocusOrder(order);
#if defined(FATHOM_ONBOARDING_RECEIVER_TRACE)
        button.addKeyListener(&setupReceiverTrace);
#endif
        button.setColour(juce::TextButton::buttonColourId,appearance::colour(accent));
        button.setColour(juce::TextButton::textColourOffId,appearance::colour(background));
        button.setColour(juce::TextButton::textColourOnId,appearance::colour(background));
        addAndMakeVisible(button);
    };
    boardVisible_.setButtonText("Show playback fretboard"); boardVisible_.setTitle("Show playback fretboard");
    boardVisible_.setExplicitFocusOrder(1); boardVisible_.onClick=[this]{chooseBoardDisplay();}; addChildComponent(boardVisible_);
    boardMode_.addItem("Basic",1); boardMode_.addItem("Finger",2); boardMode_.addItem("Note",3);
    boardMode_.setTitle("Playback fretboard mode"); boardMode_.setExplicitFocusOrder(2);
    boardMode_.onChange=[this]{chooseBoardDisplay();}; addChildComponent(boardMode_);
    noteSpelling_.addItem("Sharp names",1); noteSpelling_.addItem("Flat names",2);
    noteSpelling_.setTitle("Playback fretboard note spelling"); noteSpelling_.setExplicitFocusOrder(3);
    noteSpelling_.onChange=[this]{chooseBoardDisplay();}; addChildComponent(noteSpelling_);
    control(guitar_,"onboarding-open-guitar","Edit the current guitar draft in Guitar setup.",4);
    control(audio_,"onboarding-open-audio","Open existing shared output settings; Connect and Enable remain explicit.",4);
    label(profileNameLabel_,"onboarding-profile-name-label",16.0f);profileNameLabel_.setText("Profile name",juce::dontSendNotification);addChildComponent(profileNameLabel_);
    label(profileNameHelp_,"onboarding-profile-name-help",14.0f);addChildComponent(profileNameHelp_);
    profileName_.setComponentID("onboarding-profile-name");profileName_.setTitle("Name for your new local profile and recovery file");profileName_.setMultiLine(false);profileName_.setTextToShowWhenEmpty("e.g. Joe's guitar",appearance::colour(ink));profileName_.setWantsKeyboardFocus(true);profileName_.setExplicitFocusOrder(1);profileName_.onTextChange=[this]{if(!busy_&&onProfileNameChanged)onProfileNameChanged(profileName());refresh();};addChildComponent(profileName_);
    control(profile_,"onboarding-open-local-profile","Open your existing local profile and review any retained original activity; this action never creates a new profile.",5);
    control(reload_,"onboarding-reload","Inspect the retained original setup save without a replacement write.",6);
    control(back_,"onboarding-back","Return to the previous setup step, retaining current choices.",7);
    control(skip_,"onboarding-skip","Skip setup for now, retaining the current defaults or choices.",8);
    control(next_,"onboarding-next","Continue to the next setup step, retaining current choices.",9);
    control(finish_,"onboarding-finish","Finish with the displayed choices; the setup status explains whether they are saved.",9);
    back_.onClick=[this]{if(model_.step!=setup::Step::Welcome)invoke(onBack,"Back");};
    skip_.onClick=[this]{invoke(onSkip,"Skip for now");};
    next_.onClick=[this]{if(next_.isEnabled()&&model_.step!=setup::Step::Summary)invoke(onNext,"Next");};
    finish_.onClick=[this]{if(model_.step==setup::Step::Summary&&canFinish_)invoke(onFinish,"Finish setup");};
    guitar_.onClick=[this]{if(model_.step==setup::Step::Guitar)invoke(onOpenGuitar,"Guitar setup");};
    audio_.onClick=[this]{if(model_.step==setup::Step::Audio)invoke(onOpenAudio,"Audio settings");};
    profile_.onClick=[this]{if(recoveryPending_){if(onResumeRecovery)onResumeRecovery();return;}if(canOpenProfile_)invoke(onOpenLocalProfile,"Open existing profile");};
    reload_.onClick=[this]{
        if(!canReload_)return;
        if(onReload)onReload();
        else setStatus("Checking the original save is unavailable until setup recovery is connected. Your current choices and original save are retained.");
    };
    setWantsKeyboardFocus(true);
    refresh();
}
void OnboardingView::setModel(const setup::Model& value) {
    setup::validate(value);
    model_=value;
    refresh();
}
void OnboardingView::setStatus(std::string text) {
    status_.setText(juce::String::fromUTF8(text.c_str()),juce::dontSendNotification);
    status_.setTooltip(status_.getText());
}
void OnboardingView::setPersistenceState(bool busy,bool canFinish,std::string flags,bool canReload,bool canOpenProfile,bool profileOpen,bool recoveryPending) {
    profileOpen_=profileOpen;recoveryPending_=recoveryPending;
    busy_=busy;canFinish_=canFinish;canReload_=canReload;canOpenProfile_=canOpenProfile;
    persistence_.setText(juce::String::fromUTF8(flags.c_str()),juce::dontSendNotification);
    persistence_.setTooltip(persistence_.getText());
    refresh();
}
void OnboardingView::invoke(const std::function<void()>& callback,const char* action) {
    if(busy_)return;
    if(callback)callback();
    else setStatus(std::string(action)+" is unavailable until setup navigation is connected. Your current choices are retained.");
}
void OnboardingView::chooseExperience(presentation::Level value) {
#if defined(FATHOM_ONBOARDING_RECEIVER_TRACE)
    std::fprintf(stderr,"SETUP_MODEL enter=%s busy=%d step=%d original=%s callback=%d\n",presentation::levelName(value),
        busy_,static_cast<int>(model_.step),presentation::levelName(model_.experience),static_cast<bool>(onModelChanged));
    std::fflush(stderr);
#endif
    if(busy_||model_.step!=setup::Step::Experience)return;
    auto changed=model_;changed.experience=value;
    if(changed==model_){refresh();return;}
    if(onModelChanged) {
#if defined(FATHOM_ONBOARDING_RECEIVER_TRACE)
        std::fprintf(stderr,"SETUP_MODEL dispatch=%s count=%d\n",presentation::levelName(value),++setupReceiverModelEvents);
        std::fflush(stderr);
#endif
        onModelChanged(changed);
    }
    else setStatus("The experience choice is waiting for setup navigation. Your current choices are retained.");
    refresh();
}
void OnboardingView::chooseAppearance(setup::Appearance value) {
    if(busy_||model_.step!=setup::Step::Appearance)return;
    auto changed=model_;changed.appearance=value;
    if(changed==model_){refresh();return;}
    if(onModelChanged)onModelChanged(changed);
    else setStatus("The appearance choice is waiting for setup navigation. Your current choices are retained.");
    refresh();
}
void OnboardingView::chooseBoardDisplay() {
    if(busy_ || model_.step!=setup::Step::Guitar)return;
    auto changed=model_;
    changed.boardDisplay.visible=boardVisible_.getToggleState();
    changed.boardDisplay.mode=static_cast<setup::BoardMode>(boardMode_.getSelectedId()-1);
    changed.boardDisplay.spelling=static_cast<setup::NoteSpelling>(noteSpelling_.getSelectedId()-1);
    setup::validateBoardDisplay(changed.boardDisplay);
    model_=changed;
    if(onModelChanged)onModelChanged(changed);
    refresh();
}
std::string OnboardingView::guitarSummary() const {
    std::ostringstream text;
    text<<"Open notes, low to high: ";
    for(std::size_t i=0;i<model_.guitar.openMidi.size();++i) {
        if(i)text<<"  ";
        text<<guitar::noteName(model_.guitar.openMidi[i]);
    }
    text<<"\nCapo: "<<model_.guitar.capo<<"  |  Physical frets: "<<model_.guitar.fretCount
        <<"  |  "<<(model_.guitar.handedness==guitar::Handedness::Right?"Right-handed":"Left-handed");
    text<<"\nPlayback fretboard: "<<(model_.boardDisplay.visible?"On":"Off")
        <<" | "<<setup::boardModeName(model_.boardDisplay.mode)<<" | "<<setup::noteSpellingName(model_.boardDisplay.spelling)<<" names";
    return text.str();
}
std::string OnboardingView::audioSummary() const {
    const auto& mix=model_.audio;
    std::ostringstream text;
    text<<"Volume: Master "<<mix.master<<"%, Reference "<<mix.bus[0]<<"%, Metronome "<<mix.bus[1]
        <<"%, Rhythm A "<<mix.bus[2]<<"%, Rhythm B "<<mix.bus[3]<<"%.";
    text<<"\nMute: ";
    bool any=false;
    if(mix.masterMute){text<<"Master";any=true;}
    const char* names[]{"Reference","Metronome","Rhythm A","Rhythm B"};
    for(std::size_t i=0;i<4;++i)if(mix.muteMask&(1U<<i)){if(any)text<<", ";text<<names[i];any=true;}
    if(!any)text<<"none";
    text<<". Solo: "<<(mix.soloAB==0?"none":mix.soloAB==1?"Rhythm A":mix.soloAB==2?"Rhythm B":"Rhythm A and B")<<'.';
    return text.str();
}
void OnboardingView::refresh() {
    const auto step=model_.step;
    const bool naming=step==setup::Step::Welcome&&!profileOpen_;profileName_.setVisible(naming);profileNameLabel_.setVisible(naming);profileNameHelp_.setVisible(naming);profileName_.setEnabled(!busy_);std::string nameError;try{(void)storage::profile_names::normalize(profileName());}catch(const std::exception& e){nameError=e.what();}profileNameHelp_.setText(nameError.empty()?"Used in the recovery filename. Duplicate display names keep separate profile IDs.":juce::String(nameError),juce::dontSendNotification);
    progress_.setText("SETUP  "+juce::String(stepNumber(step))+" OF 6",juce::dontSendNotification);
    const bool experience=step==setup::Step::Experience;
    const bool appearanceStep=step==setup::Step::Appearance;
    for(std::size_t i=0;i<choices_.size();++i) {
        choices_[i].setVisible(experience||appearanceStep);
        choiceDescriptions_[i].setVisible(experience||appearanceStep);
        choices_[i].setEnabled(!busy_);
    }
    detail_.setVisible(!experience&&!appearanceStep);
    const bool guitarStep=step==setup::Step::Guitar;
    boardVisible_.setVisible(guitarStep); boardMode_.setVisible(guitarStep); noteSpelling_.setVisible(guitarStep);
    boardVisible_.setEnabled(!busy_); boardMode_.setEnabled(!busy_); noteSpelling_.setEnabled(!busy_);
    boardVisible_.setToggleState(model_.boardDisplay.visible,juce::dontSendNotification);
    boardMode_.setSelectedId(static_cast<int>(model_.boardDisplay.mode)+1,juce::dontSendNotification);
    noteSpelling_.setSelectedId(static_cast<int>(model_.boardDisplay.spelling)+1,juce::dontSendNotification);
    guitar_.setVisible(guitarStep);
    audio_.setVisible(step==setup::Step::Audio);
    next_.setVisible(step!=setup::Step::Summary);
    finish_.setVisible(step==setup::Step::Summary);
    for(auto* button:{&skip_,&next_,&guitar_,&audio_})button->setEnabled(!busy_);
    profile_.setButtonText(recoveryPending_?"Resume profile recovery":"Open existing profile");
    profile_.setTitle(recoveryPending_?"Return to the same retained original. No profile is reopened and no activity is saved.":"Open an existing local profile; does not create or replace a profile.");
    profile_.setEnabled(recoveryPending_||(!busy_&&canOpenProfile_));
    if(naming&&!nameError.empty())next_.setEnabled(false);
    next_.setButtonText(step==setup::Step::Welcome&&!profileOpen_?"Create Profile":"Next");
    next_.setTitle(step==setup::Step::Welcome&&!profileOpen_?"Begin new-profile setup. The profile is created only when you choose Finish setup.":"Continue to the next setup step.");
    back_.setEnabled(!busy_&&step!=setup::Step::Welcome);
    finish_.setEnabled(!busy_&&canFinish_);
    reload_.setEnabled(canReload_);
    switch(step) {
        case setup::Step::Welcome:
            title_.setText("Welcome to Fathom",juce::dontSendNotification);
            intro_.setText("Make a few choices for your practice space. You can go back, skip for now, or edit these settings later from Home.",juce::dontSendNotification);
            detail_.setText(profileOpen_?"Your existing local profile is open. Next continues setup when retained activity has been resolved. Resume profile recovery to review an unfinished original; no new profile is created here.":"Choose a name, then Create Profile to choose settings. Finish setup creates your named local recovery file.\n\nOpen existing profile loads saved choices and unfinished activity. It never replaces that profile.",juce::dontSendNotification);
            break;
        case setup::Step::Experience: {
            title_.setText("Choose your starting experience",juce::dontSendNotification);
            intro_.setText("This controls how much detail you see. It does not change your access to exercises, save activity, or award progress. You can change it later.",juce::dontSendNotification);
            const char* names[]{"Beginner","Advanced","Developer"};
            const char* descriptions[]{"Clear guidance and the essential practice controls.","More musical detail and practice options.","Additional technical details for inspecting the Development Preview."};
            const char* ids[]{"onboarding-experience-beginner","onboarding-experience-advanced","onboarding-experience-developer"};
            const presentation::Level values[]{presentation::Level::Beginner,presentation::Level::Advanced,presentation::Level::Developer};
            for(std::size_t i=0;i<choices_.size();++i) {
                choices_[i].setButtonText(names[i]);choices_[i].setComponentID(ids[i]);
                choices_[i].setTitle(juce::String(names[i])+". "+descriptions[i]);
                choices_[i].setToggleState(model_.experience==values[i],juce::dontSendNotification);
                choiceDescriptions_[i].setText(descriptions[i],juce::dontSendNotification);
                choices_[i].onClick=[this,value=values[i]]{chooseExperience(value);};
            }
            break;
        }
        case setup::Step::Appearance: {
            title_.setText("Choose an appearance",juce::dontSendNotification);
            intro_.setText("Use the current Fathom appearance, or choose Light or Dark. This changes the display only, and you can edit it later.",juce::dontSendNotification);
            const char* names[]{"Default","Light","Dark"};
            const char* descriptions[]{"Keep the current Fathom appearance.","Pale surfaces with dark text.","Dark surfaces with light text."};
            const char* ids[]{"onboarding-appearance-default","onboarding-appearance-light","onboarding-appearance-dark"};
            const setup::Appearance values[]{setup::Appearance::Default,setup::Appearance::Light,setup::Appearance::Dark};
            for(std::size_t i=0;i<choices_.size();++i) {
                choices_[i].setButtonText(names[i]);choices_[i].setComponentID(ids[i]);
                choices_[i].setTitle(juce::String(names[i])+". "+descriptions[i]);
                choices_[i].setToggleState(model_.appearance==values[i],juce::dontSendNotification);
                choiceDescriptions_[i].setText(descriptions[i],juce::dontSendNotification);
                choices_[i].onClick=[this,value=values[i]]{chooseAppearance(value);};
            }
            break;
        }
        case setup::Step::Guitar:
            title_.setText("Describe your guitar",juce::dontSendNotification);
            intro_.setText("Open Guitar setup to choose tuning, capo, fret count, and orientation. This describes your instrument; it does not detect physical tuning.",juce::dontSendNotification);
            detail_.setText(juce::String::fromUTF8((guitarSummary()+"\n\nUse the existing Guitar setup controls, then return here. Authored lesson tuning stays unchanged. Next or Skip keeps the choices shown here.").c_str()),juce::dontSendNotification);
            break;
        case setup::Step::Audio:
            title_.setText("Prepare your audio output",juce::dontSendNotification);
            intro_.setText("Fathom uses the current macOS default speakers or headphones. Choose the output in macOS Sound settings, then open Audio settings here.",juce::dontSendNotification);
            detail_.setText(juce::String::fromUTF8((std::string{"Connect audio and Enable audio are explicit choices. Enable prepares output; Play or Start in an activity begins sound.\n\n"}+audioSummary()+"\n\nOpening this step starts no sound. This setup uses output only. On restart, output stays disconnected until you Connect and Enable explicitly.").c_str()),juce::dontSendNotification);
            break;
        case setup::Step::Summary:
            title_.setText("Your setup choices",juce::dontSendNotification);
            intro_.setText("Review these choices, go Back to edit them, or Finish setup. You can reopen setup and the individual settings pages from Home later.",juce::dontSendNotification);
            detail_.setText(juce::String::fromUTF8((std::string{"Experience: "}+presentation::levelLabel(model_.experience)+"\nAppearance: "+appearanceLabel(model_.appearance)+"\n\n"+guitarSummary()+"\n\n"+audioSummary()+"\n\nAudio connection is not restored after restart. Connect and Enable explicitly when you want output.").c_str()),juce::dontSendNotification);
            break;
    }
    appearance::apply(*this);
    resized();
    repaint();
}
void OnboardingView::paint(juce::Graphics& g) {
    g.fillAll(appearance::colour(background));
    const auto margin=getWidth()<800?24:28;
    g.setColour(appearance::colour(panel));
    g.fillRoundedRectangle(juce::Rectangle<float>{static_cast<float>(margin),178.0f,static_cast<float>(std::max(1,getWidth()-margin*2)),static_cast<float>(std::max(1,getHeight()-368))},10.0f);
}
void OnboardingView::resized() {
    const auto margin=getWidth()<800?24:28;
    const auto width=std::max(1,getWidth()-margin*2);
    progress_.setBounds(margin,20,width,22);
    title_.setBounds(margin,50,width,44);
    intro_.setBounds(margin,106,width,62);
    const auto contentHeight=std::max(1,getHeight()-368);
    const auto inset=18;
    const bool linked=model_.step==setup::Step::Guitar||model_.step==setup::Step::Audio;
    const bool naming=model_.step==setup::Step::Welcome&&!profileOpen_;
    profileNameLabel_.setBounds(margin+inset,190,140,26);profileName_.setBounds(margin+inset+145,188,std::max(1,width-inset*2-145),30);profileNameHelp_.setBounds(margin+inset,222,width-inset*2,38);
    detail_.setBounds(margin+inset,naming?268:194,width-inset*2,std::max(1,contentHeight-32-(naming?74:0)-(linked?56:0)-(model_.step==setup::Step::Guitar?40:0)));
    guitar_.setBounds(margin+inset,178+contentHeight-52,std::min(300,width-inset*2),36);
    audio_.setBounds(guitar_.getBounds());
    const int displayWidth=std::max(1,(width-inset*2)/3);
    const int displayY=178+contentHeight-92;
    boardVisible_.setBounds(margin+inset,displayY,displayWidth,30);
    boardMode_.setBounds(margin+inset+displayWidth,displayY,displayWidth-4,30);
    noteSpelling_.setBounds(margin+inset+displayWidth*2,displayY,displayWidth-4,30);
    if(getWidth()>=800) {
        const auto gap=20;
        const auto cell=(width-inset*2-gap*2)/3;
        for(std::size_t i=0;i<choices_.size();++i) {
            const auto x=margin+inset+static_cast<int>(i)*(cell+gap);
            choices_[i].setBounds(x,204,cell,36);
            choiceDescriptions_[i].setBounds(x,254,cell,std::max(1,contentHeight-94));
        }
    }else{
        const auto cell=std::max(1,(contentHeight-24)/3);
        for(std::size_t i=0;i<choices_.size();++i) {
            const auto y=190+static_cast<int>(i)*cell;
            choices_[i].setBounds(margin+inset,y,148,32);
            choiceDescriptions_[i].setBounds(margin+inset+160,y,std::max(1,width-inset*2-160),std::max(1,cell-10));
        }
    }
    persistence_.setBounds(margin,getHeight()-180,width,30);
    profile_.setBounds(margin,getHeight()-142,std::min(270,width),34);
    reload_.setBounds(margin+282,getHeight()-142,std::max(1,std::min(228,width-282)),34);
    status_.setBounds(margin,getHeight()-100,width,40);
    back_.setBounds(margin,getHeight()-48,90,34);
    skip_.setBounds(margin+102,getHeight()-48,148,34);
    next_.setBounds(getWidth()-margin-132,getHeight()-48,132,34);
    finish_.setBounds(next_.getBounds());
}
} // namespace fathom::desktop
