#include "desktop/PracticeKeyboardMac.hpp"
#import <AppKit/AppKit.h>
#include <array>
#include <cctype>
#include <typeinfo>

namespace fathom::desktop {
struct PracticeKeyboardMac::Impl {
    PracticeKeyboardMac& api;
    juce::Component& component;
    std::function<void(PracticeCommand)> dispatch;
    PracticeShortcutGate gate;
    std::array<int,128> hardware{};
    std::array<juce::Component::SafePointer<juce::TextButton>,128> pendingSpaceButtons{};
    id monitor=nil, inactive=nil;
    Impl(PracticeKeyboardMac& a,juce::Component& c,std::function<void(PracticeCommand)> d)
        :api(a),component(c),dispatch(std::move(d)) {
        monitor=[NSEvent addLocalMonitorForEventsMatchingMask:NSEventMaskKeyDown|NSEventMaskKeyUp handler:^NSEvent*(NSEvent* event){return handle(event);}];
        inactive=[[NSNotificationCenter defaultCenter] addObserverForName:NSApplicationDidResignActiveNotification object:nil queue:nil usingBlock:^(NSNotification*){
            gate.abandonInactiveGestures();hardware.fill(0);pendingSpaceButtons.fill(nullptr);
        }];
    }
    ~Impl(){if(monitor)[NSEvent removeMonitor:monitor];if(inactive)[[NSNotificationCenter defaultCenter] removeObserver:inactive];}
    NSEvent* handle(NSEvent* event){
        auto* peer=component.getPeer();NSView* native=peer?(__bridge NSView*)peer->getNativeHandle():nil;
        const bool matching=native && event.window==native.window;
        const bool visible=component.isShowing();
        const auto code=static_cast<unsigned>(event.keyCode);
        const auto text=event.charactersIgnoringModifiers;
        int key=text.length?static_cast<int>([text characterAtIndex:0]):0;
        if(key>='a'&&key<='z')key-=('a'-'A');
        const bool down=event.type==NSEventTypeKeyDown;
        const bool repeat=down&&event.isARepeat;
        const auto flags=event.modifierFlags;
        const bool modified=(flags&(NSEventModifierFlagShift|NSEventModifierFlagControl|NSEventModifierFlagOption|NSEventModifierFlagCommand|NSEventModifierFlagFunction))!=0;
        bool consumed=false,invoked=false;
        juce::Component::SafePointer<juce::TextButton> releasedSpaceButton;
        // Release bookkeeping follows the physical key even if its character or
        // modifiers changed. It never invokes a command or consumes another view.
        if(!down){
            const int original=code<hardware.size()?hardware[code]:0;
            if(original)gate.release(original);
            if(code<hardware.size())hardware[code]=0;
            if(code<pendingSpaceButtons.size()){
                releasedSpaceButton=pendingSpaceButtons[code];
                pendingSpaceButtons[code]=nullptr;
            }
        }
        bool inputFocus=false,buttonFocus=false;
        juce::Button* focusedButton=nullptr;
        for(auto* focused=juce::Component::getCurrentlyFocusedComponent();focused&&focused!=&component;focused=focused->getParentComponent())
            if(component.isParentOf(focused)){
                if(dynamic_cast<juce::ComboBox*>(focused)||dynamic_cast<juce::TextEditor*>(focused)){inputFocus=true;break;}
                if(auto* button=dynamic_cast<juce::Button*>(focused)){buttonFocus=true;if(!focusedButton)focusedButton=button;}
            }
        auto* releasedButton=releasedSpaceButton.getComponent();
        if(releasedButton&&matching&&visible&&!inputFocus&&buttonFocus&&focusedButton==releasedButton
           &&component.isParentOf(releasedButton)&&typeid(*releasedButton)==typeid(juce::TextButton)
           &&releasedButton->isShowing()&&releasedButton->isEnabled()
           &&!releasedButton->isRegisteredForShortcut(juce::KeyPress(juce::KeyPress::spaceKey)))
            releasedButton->triggerClick();
        if(matching&&visible&&down&&!inputFocus){
            if(key==' '&&buttonFocus){
                if(!modified&&!repeat&&code<pendingSpaceButtons.size())
                    if(auto* textButton=dynamic_cast<juce::TextButton*>(focusedButton);
                       textButton&&typeid(*textButton)==typeid(juce::TextButton)
                       &&!textButton->isRegisteredForShortcut(juce::KeyPress(juce::KeyPress::spaceKey)))
                        pendingSpaceButtons[code]=textButton;
            }else if(const auto command=PracticeShortcutGate::command(key,modified)){
                if(!(key==' '&&buttonFocus)){
                    consumed=true;
                    // AppKit repeat identity is retained even when JUCE has cleared
                    // its own key state after modifier or activation changes.
                    // A repeat/layout change must not retarget the key whose future
                    // keyUp releases the original gesture.
                    invoked=code<hardware.size()&&hardware[code]==0&&gate.press(key,repeat);
                    if(invoked){hardware[code]=key;dispatch(*command);}
                }
            }
        }
        if(api.onObservation)api.onObservation({event.timestamp,key,static_cast<int>(code),down,repeat,modified,matching,visible,consumed,invoked});
        return consumed?nil:event;
    }
};
PracticeKeyboardMac::PracticeKeyboardMac(juce::Component& c,std::function<void(PracticeCommand)> d):impl_(std::make_unique<Impl>(*this,c,std::move(d))){}
PracticeKeyboardMac::~PracticeKeyboardMac()=default;
}
