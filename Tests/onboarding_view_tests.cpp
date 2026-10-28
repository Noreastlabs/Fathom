#include "desktop/OnboardingView.hpp"
#include "desktop/GuitarSetupView.hpp"
#include "desktop/Appearance.hpp"
#include <iostream>
#include <stdexcept>
#include <vector>
#include <chrono>
#if JUCE_MAC
#include <CoreFoundation/CoreFoundation.h>
#endif

using namespace fathom;
namespace {
int checks{};
void check(bool condition,const std::string& description) {
    ++checks;
    if(!condition)throw std::runtime_error(description);
}
juce::Button& button(juce::Component& view,const char* id) {
    auto* result=dynamic_cast<juce::Button*>(view.findChildWithID(id));
    if(!result)throw std::runtime_error(std::string("Missing button: ")+id);
    return *result;
}
juce::Label& label(juce::Component& view,const char* id) {
    auto* result=dynamic_cast<juce::Label*>(view.findChildWithID(id));
    if(!result)throw std::runtime_error(std::string("Missing label: ")+id);
    return *result;
}
void click(juce::Component& view,const char* id) {
    auto& value=button(view,id);
    if(!value.isVisible()||!value.isEnabled()||!value.onClick)throw std::runtime_error(std::string("Button unavailable: ")+id);
    value.onClick();
}
bool sameSetup(const guitar::Setup& a,const guitar::Setup& b) {
    return a.valueVersion==b.valueVersion&&a.openMidi==b.openMidi&&a.capo==b.capo&&a.fretCount==b.fretCount&&a.handedness==b.handedness;
}
void dispatchButtons() {
#if JUCE_MAC
    // Dispatch asynchronous JUCE button callbacks without a window or peer.
    const auto until=std::chrono::steady_clock::now()+std::chrono::milliseconds(250);
    while(std::chrono::steady_clock::now()<until)CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);
#elif JUCE_MODAL_LOOPS_PERMITTED
    juce::MessageManager::getInstance()->runDispatchLoopUntil(40);
#else
    throw std::runtime_error("Button dispatch requires the macOS test environment");
#endif
}
void layout(desktop::OnboardingView& view,int width,int height) {
    view.setSize(width,height);
    const auto bounds=view.getLocalBounds();
    std::vector<juce::Component*> visible;
    for(auto* child:view.getChildren())if(child->isVisible()) {
        check(child->getWidth()>0&&child->getHeight()>0&&bounds.contains(child->getBounds()),"Visible onboarding child is contained: "+child->getComponentID().toStdString());
        visible.push_back(child);
        if(auto* control=dynamic_cast<juce::Button*>(child)) {
            const auto id=control->getComponentID().toStdString();
            check(control->getExplicitFocusOrder()>0&&!control->getTitle().isEmpty(),"Onboarding action retains focus order and accessible title: "+id);
            // JUCE's getter excludes disabled controls even when their configured
            // wants-focus flag is true. Disabled recovery/Back must stay skipped.
            check(control->getWantsKeyboardFocus()==control->isEnabled(),"Onboarding focus eligibility follows enabled state: "+id);
        }
    }
    for(std::size_t i=0;i<visible.size();++i)for(std::size_t j=i+1;j<visible.size();++j)
        check(!visible[i]->getBounds().intersects(visible[j]->getBounds()),"Visible onboarding controls do not overlap");
}
}
int main() {
    try {
        juce::ScopedJuceInitialiser_GUI gui;
        using S=desktop::setup::Step;
        using L=desktop::presentation::Level;
        using A=desktop::setup::Appearance;
        desktop::setup::Model model;
        desktop::OnboardingView view;
        view.setVisible(true);view.setSize(920,680);
        int changes{},next{},back{},skip{},finish{},guitarPages{},audioPages{},profiles{},reloads{};
        view.onModelChanged=[&](desktop::setup::Model changed){++changes;model=std::move(changed);view.setModel(model);};
        view.onNext=[&]{++next;};view.onBack=[&]{++back;};view.onSkip=[&]{++skip;};view.onFinish=[&]{++finish;};
        view.onOpenGuitar=[&]{++guitarPages;};view.onOpenAudio=[&]{++audioPages;};view.onOpenLocalProfile=[&]{++profiles;};
        view.onReload=[&]{++reloads;};
        view.setModel(model);
        dynamic_cast<juce::TextEditor*>(view.findChildWithID("onboarding-profile-name"))->setText("Component test");dispatchButtons();
        check(view.currentStep()==S::Welcome&&changes==0&&next==0&&audioPages==0,"Opening the view emits no choice, transition or audio-page action");
        check(!button(view,"onboarding-back").isEnabled()&&!button(view,"onboarding-finish").isVisible(),"Welcome exposes Next and keeps Back/Finish guarded");
        click(view,"onboarding-next");
        check(next==1&&view.currentStep()==S::Welcome,"Next requests a host transition without changing the model itself");
        button(view,"onboarding-open-audio").onClick();button(view,"onboarding-finish").onClick();
        check(audioPages==0&&finish==0,"Hidden audio/finish actions cannot bypass the current step");

        model.step=S::Experience;view.setModel(model);
        check(button(view,"onboarding-experience-beginner").getToggleState(),"Beginner is the initial experience choice");
        const auto beforeExperience=model;
        click(view,"onboarding-experience-advanced");
        auto expected=beforeExperience;expected.experience=L::Advanced;
        check(model==expected&&changes==1,"Experience emits only the selected disclosure choice");
        check(button(view,"onboarding-experience-advanced").getToggleState()&&!button(view,"onboarding-experience-beginner").getToggleState(),"Experience is an exclusive accessible choice");
        click(view,"onboarding-experience-advanced");
        check(changes==1,"Repeated current choice creates no replacement model event");
        check(label(view,"onboarding-intro").getText().contains("does not change your access")&&label(view,"onboarding-intro").getText().contains("award progress"),"Experience copy keeps exercise access and progress boundaries clear");

        model.step=S::Appearance;view.setModel(model);
        const auto beforeAppearance=model;
        click(view,"onboarding-appearance-light");
        expected=beforeAppearance;expected.appearance=A::Light;
        check(model==expected&&changes==2,"Appearance emits only the display choice");
        check(button(view,"onboarding-appearance-light").getToggleState()&&!button(view,"onboarding-appearance-default").getToggleState(),"Light remains an exclusive choice");
        click(view,"onboarding-appearance-dark");click(view,"onboarding-appearance-default");
        check(model.appearance==A::Default&&changes==4,"All three appearance choices are available");

        model.guitar.openMidi=guitar::tuning(guitar::Preset::DropD);model.guitar.capo=2;model.guitar.handedness=guitar::Handedness::Left;
        model.audio.master=37;model.audio.bus={13,27,41,89};model.audio.masterMute=true;model.audio.muteMask=3;model.audio.soloAB=2;
        model.step=S::Guitar;view.setModel(model);
        const auto retained=model;
        click(view,"onboarding-open-guitar");
        check(guitarPages==1&&model==retained&&view.currentStep()==S::Guitar,"Guitar link borrows the host page without applying or navigating locally");
        check(label(view,"onboarding-detail").getText().contains("D2")&&label(view,"onboarding-detail").getText().contains("Capo: 2")&&label(view,"onboarding-detail").getText().contains("Left-handed"),"Guitar step displays the actual retained setup");
        click(view,"onboarding-back");check(back==1&&model==retained,"Back retains the draft and asks the host to return");

        model.step=S::Audio;view.setModel(model);
        click(view,"onboarding-open-audio");
        check(audioPages==1&&view.currentStep()==S::Audio,"Audio link only asks the host to open existing settings");
        check(label(view,"onboarding-intro").getText().contains("macOS default")&&label(view,"onboarding-detail").getText().contains("Connect audio and Enable audio are explicit")&&label(view,"onboarding-detail").getText().contains("output stays disconnected"),"Audio copy preserves default-output, explicit preparation and restart boundaries");
        check(label(view,"onboarding-detail").getText().contains("Master 37%")&&label(view,"onboarding-detail").getText().contains("Rhythm B 89%"),"Audio step summarizes the selected mix without changing it");

        model.step=S::Summary;view.setModel(model);
        check(button(view,"onboarding-finish").isVisible()&&!button(view,"onboarding-next").isVisible(),"Summary exposes Finish as the final action");
        check(label(view,"onboarding-detail").getText().contains("Advanced")&&label(view,"onboarding-detail").getText().contains("Default (current Fathom appearance)")&&label(view,"onboarding-detail").getText().contains("Capo: 2"),"Summary retains experience, appearance and instrument choices");
        const auto beforeFinish=model;
        view.setPersistenceState(false,false,"The original save is not confirmed. Check it before finishing.");
        button(view,"onboarding-finish").onClick();
        check(finish==0&&!button(view,"onboarding-finish").isEnabled()&&model==beforeFinish,"Unconfirmed persistence holds Finish without clearing choices");
        view.setStatus("Original save retained.");
        view.setPersistenceState(true,true,"Saving the original choices.");
        for(const auto* id:{"onboarding-back","onboarding-skip","onboarding-next","onboarding-finish","onboarding-open-local-profile","onboarding-open-guitar","onboarding-open-audio","onboarding-reload"})button(view,id).onClick();
        check(next==1&&back==1&&skip==0&&finish==0&&profiles==0&&guitarPages==1&&audioPages==1&&model==beforeFinish,"Busy state refuses every action, including direct stale callback dispatch");
        check(label(view,"onboarding-status").getText()=="Original save retained.","Persistence refresh does not erase original failure guidance");
        check(reloads==0&&!button(view,"onboarding-reload").isEnabled(),"Executing future keeps original-save inspection disabled");
        view.setPersistenceState(true,false,"Original save held; inspect it explicitly.",true);
        click(view,"onboarding-reload");
        check(reloads==1&&model==beforeFinish&&!button(view,"onboarding-finish").isEnabled(),"Held debt permits explicit original-save inspection without replacing choices or enabling Finish");
        view.setPersistenceState(false,true,"Local profile is already attached.",false,false);
        button(view,"onboarding-open-local-profile").onClick();
        check(profiles==0&&!button(view,"onboarding-open-local-profile").isEnabled()&&model==beforeFinish,"Unavailable profile action rejects stale direct callback and preserves current choices");
        view.setPersistenceState(false,true,"Choices are for this session.");
        check(button(view,"onboarding-open-local-profile").isEnabled(),"Existing three/four-argument persistence calls keep profile action available by default");
        click(view,"onboarding-finish");click(view,"onboarding-skip");click(view,"onboarding-open-local-profile");
        check(finish==1&&skip==1&&profiles==1&&model==beforeFinish&&!model.completed&&!model.skipped,"Finish/Skip/profile remain host decisions and preserve current choices");
        button(view,"onboarding-next").onClick();check(next==1,"Hidden Next cannot leave Summary");

        for(const auto step:{S::Welcome,S::Experience,S::Appearance,S::Guitar,S::Audio,S::Summary}) {
            model.step=step;view.setModel(model);
            for(const auto size:{juce::Point<int>{920,680},juce::Point<int>{1400,680},juce::Point<int>{1280,800},juce::Point<int>{920,1000}})layout(view,size.x,size.y);
        }
        model.step=S::Experience;view.setModel(model);view.setPersistenceState(true,true);
        check(static_cast<juce::Component&>(button(view,"onboarding-experience-developer")).keyPressed(juce::KeyPress(juce::KeyPress::spaceKey)),"Disabled choice consumes Space without dispatching an action");
        check(changes==4,"Disabled keyboard choice leaves the model unchanged");
        check(static_cast<juce::Component&>(button(view,"onboarding-next")).keyPressed(juce::KeyPress(juce::KeyPress::returnKey)),"Disabled Next consumes Return safely");
        check(next==1,"Disabled keyboard action leaves navigation unchanged");
        auto invalid=model;invalid.guitar.capo=99;
        bool rejected=false;try{view.setModel(invalid);}catch(const std::invalid_argument&){rejected=true;}
        check(rejected&&view.currentStep()==model.step,"Invalid input model is rejected before replacing the current step");

        desktop::GuitarSetupView setup;
        int applied{};setup.onApplied=[&]{++applied;};
        const auto initial=setup.currentSetup();
        auto custom=initial;custom.openMidi={38,45,50,55,57,62};custom.capo=2;custom.fretCount=24;custom.handedness=guitar::Handedness::Left;
        check(setup.setDraft(custom)&&sameSetup(setup.currentSetup(),initial)&&applied==0,"Setting a valid guitar draft does not apply or claim a saved setting");
        std::string draftError;
        const auto draft=setup.draftSetup(&draftError);
        check(draft&&sameSetup(*draft,custom)&&draftError.empty(),"Validated guitar draft reads exact pitches, frets, capo and handedness");
        auto invalidSetup=custom;invalidSetup.capo=25;
        check(!setup.setDraft(invalidSetup)&&setup.draftSetup()&&sameSetup(*setup.draftSetup(),custom)&&sameSetup(setup.currentSetup(),initial),"Invalid external draft preserves editor values and active setup");
        setup.canApply=[] {return false;};
        check(!setup.applySetup(custom)&&sameSetup(setup.currentSetup(),initial)&&applied==0,"Confirmed restore still respects the current stopped/resolved host guard");
        setup.canApply=[] {return true;};
        check(!setup.applySetup(invalidSetup)&&sameSetup(setup.currentSetup(),initial)&&applied==0,"Invalid restore cannot apply or invoke onApplied");
        check(setup.applySetup(custom)&&sameSetup(setup.currentSetup(),custom)&&applied==1,"Allowed restore applies exact values through the existing callback once");
        check(setup.draftSetup()&&sameSetup(*setup.draftSetup(),custom),"Allowed restore also refreshes the existing draft editors");
        juce::TextEditor* capo=nullptr;juce::ComboBox* preset=nullptr;
        for(auto* child:setup.getChildren()) {
            if(auto* editor=dynamic_cast<juce::TextEditor*>(child);editor&&editor->getTitle()=="Capo physical fret")capo=editor;
            if(auto* combo=dynamic_cast<juce::ComboBox*>(child);combo&&combo->getTitle()=="Tuning preset")preset=combo;
        }
        check(capo&&preset&&preset->getSelectedId()==4,"External custom setup remains the existing Custom draft");
        capo->setText("-1",false);
        check(!setup.draftSetup(&draftError)&&!draftError.empty()&&sameSetup(setup.currentSetup(),custom),"Malformed editor read retains exact active setup and returns actionable error");
        juce::Button* apply=nullptr;
        for(auto* child:setup.getChildren())if(auto* candidate=dynamic_cast<juce::Button*>(child);candidate&&candidate->getButtonText()=="Apply setup")apply=candidate;
        check(apply&&bool(apply->onClick),"Original Apply setup action is retained");
        apply->onClick();
        check(applied==1&&capo->getText()=="-1"&&preset->getSelectedId()==4&&sameSetup(setup.currentSetup(),custom),"Original invalid Apply keeps custom draft/error state and active values");
        capo->setText("0",false);apply->onClick();
        check(applied==2&&setup.currentSetup().capo==0&&preset->getSelectedId()==4,"Original corrected Apply still applies once and retains Custom selection");
        bool sessionWorded=false;
        for(auto* child:setup.getChildren())if(auto* text=dynamic_cast<juce::Label*>(child);text&&text->getText().contains("Changes are kept for this app session"))sessionWorded=true;
        check(sessionWorded,"Guitar bridge retains session-only wording until the host confirms persistence");

        desktop::OnboardingView keyboard;
        keyboard.setVisible(true);keyboard.setSize(920,680);
        int keyboardNext{};
        dynamic_cast<juce::TextEditor*>(keyboard.findChildWithID("onboarding-profile-name"))->setText("Keyboard test");dispatchButtons();
        keyboard.onNext=[&]{++keyboardNext;};
        auto& keyNext=static_cast<juce::Component&>(button(keyboard,"onboarding-next"));
        keyNext.keyPressed(juce::KeyPress(juce::KeyPress::returnKey));
        keyNext.keyPressed(juce::KeyPress(juce::KeyPress::returnKey));dispatchButtons();
        check(keyboardNext==1,"Enabled Return activates Next once while held");
        keyNext.keyStateChanged(false);
        keyNext.keyPressed(juce::KeyPress(juce::KeyPress::spaceKey));
        keyNext.keyPressed(juce::KeyPress(juce::KeyPress::spaceKey));dispatchButtons();
        check(keyboardNext==2,"Enabled Space activates Next once while held");
        keyNext.keyStateChanged(false);
        keyNext.keyPressed(juce::KeyPress(juce::KeyPress::spaceKey));dispatchButtons();
        check(keyboardNext==3,"Key release rearms the Next action");
        desktop::setup::Model keyModel;keyModel.step=S::Experience;
        int keyboardChoices{};
        keyboard.onModelChanged=[&](desktop::setup::Model changed){++keyboardChoices;keyModel=std::move(changed);keyboard.setModel(keyModel);};
        keyboard.setModel(keyModel);
        auto& keyChoice=static_cast<juce::Component&>(button(keyboard,"onboarding-experience-advanced"));
        keyChoice.keyPressed(juce::KeyPress(juce::KeyPress::spaceKey));
        keyChoice.keyPressed(juce::KeyPress(juce::KeyPress::spaceKey));dispatchButtons();
        check(keyboardChoices==1&&keyModel.experience==L::Advanced,"Enabled Space dispatches one exact experience choice while held");
        desktop::appearance::set(A::Default);
        std::cout<<"PASS "<<checks<<" onboarding component/guitar bridge checks; no peer, audio device, recording or Store\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<'\n';return 1;}
}
