#include "desktop/LessonView.hpp"
#include "core/ReferenceAudio.hpp"
#include "core/Scheduler.hpp"
#include <CoreFoundation/CoreFoundation.h>
#ifdef __OBJC__
#import <Cocoa/Cocoa.h>
#endif
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <iostream>
#include <vector>
using namespace fathom;
namespace {
struct L3Facts { std::array<scheduler::Fact, scheduler::maxCallbackEvents> values{}; std::size_t count{}; };
bool retainL3Fact(void* context,const scheduler::Fact& fact) noexcept {
    auto& buffer=*static_cast<L3Facts*>(context);
    if(buffer.count==buffer.values.size())return false;
    buffer.values[buffer.count++]=fact;return true;
}
scheduler::BoundaryDecision stopL3Reference(void*,const scheduler::Fact& fact) noexcept {
    return fact.kind==scheduler::FactKind::CycleCompleted
        ?scheduler::BoundaryDecision{scheduler::BoundaryAction::Stop,nullptr}
        :scheduler::BoundaryDecision{};
}
}
int main(int argc,char** argv){int checks=0;std::ofstream trace;
    auto check=[&](bool ok,const std::string& s){++checks;trace<<s<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(s);};
    try{
        const bool searchSmoke=argc==4&&std::string(argv[3])=="--search-smoke";const bool selectionSurface=argc==4&&std::string(argv[3])=="--selection-surface";const bool practiceHandoffContract=argc==4&&std::string(argv[3])=="--practice-handoff-contract";const bool catalogSurface=argc==4&&std::string(argv[3])=="--catalog-surface";const bool firstAdmitted=argc==4&&std::string(argv[3])=="--first-admitted";const bool fretboardSelection=argc==4&&std::string(argv[3])=="--fretboard-selection";const bool fretboardKnownCase=argc==4&&std::string(argv[3])=="--fretboard-known-case";const bool l3ReferenceCrossprojection=argc==4&&std::string(argv[3])=="--l3-reference-crossprojection";const bool leftHandedFretboard=argc==4&&std::string(argv[3])=="--left-handed-fretboard";const bool learnCompact=argc==4&&std::string(argv[3])=="--learn-compact";const bool learnKeyboardNative=argc==4&&std::string(argv[3])=="--learn-keyboard-native";const bool lessonActionKeys=argc==4&&std::string(argv[3])=="--lesson-action-keys";if(argc!=3&&!searchSmoke&&!selectionSurface&&!practiceHandoffContract&&!catalogSurface&&!firstAdmitted&&!fretboardSelection&&!fretboardKnownCase&&!l3ReferenceCrossprojection&&!leftHandedFretboard&&!learnCompact&&!learnKeyboardNative&&!lessonActionKeys)throw std::invalid_argument("Expected bundle, new absolute output, and a supported focused mode");const std::filesystem::path bundle(argv[1]),out(argv[2]);if(!out.is_absolute()||std::filesystem::exists(out))throw std::invalid_argument("Output must be new absolute directory");std::filesystem::create_directories(out);trace.open(out/"checks.tsv");
#ifdef __OBJC__
        if(learnKeyboardNative){[NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];}
#else
        if(learnKeyboardNative)throw std::invalid_argument("Native Learn keyboard mode requires Objective-C++ test compilation");
#endif
        juce::ScopedJuceInitialiser_GUI gui;
        if(lessonActionKeys){
            std::ofstream keys(out/"action-keys.tsv");keys<<"width\taction\tkey\tpractice_calls\taudio_calls\tback_calls\titem\tvariant\n";
            constexpr const char* itemId="fg:item:000002";constexpr const char* variantId="fg:variant:000006";
            for(const int width:{640,920}){
                desktop::LessonView learn;learn.setSize(width,680);
                int practiceCalls=0,audioCalls=0,backCalls=0;
                learn.onPractice=[&](std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&){++practiceCalls;return false;};
                learn.onAudioSettings=[&]{++audioCalls;};learn.onBack=[&]{++backCalls;};
                check(learn.load(bundle),"Learn action view loads retained source bundle at "+std::to_string(width));
                check(learn.selectLesson(itemId)&&learn.selectVariant(variantId),"Learn action view selects exact admitted L3 case at "+std::to_string(width));
                learn.addToDesktop(juce::ComponentPeer::windowHasTitleBar);learn.setVisible(true);auto* peer=learn.getPeer();
                auto* practice=dynamic_cast<juce::TextButton*>(learn.findChildWithID("practice-selection"));
                auto* audio=dynamic_cast<juce::TextButton*>(learn.findChildWithID("audio-settings"));
                auto* back=dynamic_cast<juce::TextButton*>(learn.findChildWithID("back"));
                check(peer&&learn.isShowing()&&practice&&audio&&back,"Learn visible peer and action controls at "+std::to_string(width));
                check(practice->isShowing()&&practice->isEnabled()&&audio->isShowing()&&audio->isEnabled()&&back->isShowing()&&back->isEnabled(),"Learn admitted Practice, Audio and Back are visible enabled at "+std::to_string(width));
                practice->grabKeyboardFocus();check(juce::Component::getCurrentlyFocusedComponent()==practice,"Learn Practice selected case receives focus at "+std::to_string(width));
                check(peer->handleKeyPress(juce::KeyPress{juce::KeyPress::spaceKey}),"Learn focused Practice selected case consumes Space at "+std::to_string(width));
                check(practiceCalls==1&&learn.selectedLesson()==itemId&&learn.selectedVariant()==variantId,"Learn Practice Space invokes one source-backed handoff without changing selection at "+std::to_string(width));
                keys<<width<<"\tPractice\tSpace\t"<<practiceCalls<<'\t'<<audioCalls<<'\t'<<backCalls<<'\t'<<itemId<<'\t'<<variantId<<'\n';
                audio->grabKeyboardFocus();check(juce::Component::getCurrentlyFocusedComponent()==audio,"Learn Audio settings receives focus at "+std::to_string(width));
                check(peer->handleKeyPress(juce::KeyPress{juce::KeyPress::spaceKey}),"Learn focused Audio settings consumes Space at "+std::to_string(width));
                check(audioCalls==1&&practiceCalls==1,"Learn Audio Space invokes one handoff without repeating Practice at "+std::to_string(width));
                keys<<width<<"\tAudio\tSpace\t"<<practiceCalls<<'\t'<<audioCalls<<'\t'<<backCalls<<'\t'<<itemId<<'\t'<<variantId<<'\n';
                back->grabKeyboardFocus();check(juce::Component::getCurrentlyFocusedComponent()==back,"Learn Back receives focus at "+std::to_string(width));
                check(peer->handleKeyPress(juce::KeyPress{juce::KeyPress::returnKey}),"Learn focused Back consumes Return at "+std::to_string(width));
                check(backCalls==1&&learn.selectedLesson()==itemId&&learn.selectedVariant()==variantId,"Learn Back Return invokes one navigation without changing source at "+std::to_string(width));
                keys<<width<<"\tBack\tReturn\t"<<practiceCalls<<'\t'<<audioCalls<<'\t'<<backCalls<<'\t'<<itemId<<'\t'<<variantId<<'\n';
                auto image=learn.createComponentSnapshot(learn.getLocalBounds());auto stream=juce::File(juce::String::fromUTF8((out/("learn-action-"+std::to_string(width)+".png")).c_str())).createOutputStream();juce::PNGImageFormat png;
                check(stream&&png.writeImageToStream(image,*stream),"Learn action screenshot at "+std::to_string(width));
                learn.removeFromDesktop();
            }
            keys.flush();trace.flush();check(keys.good()&&trace.good(),"Learn action evidence flushed");
            std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"status\":\"PASS\",\"practiceCallsPerWidth\":1,\"storeConfigured\":false,\"attemptCreated\":false,\"physicalKeyboard\":false}\n";
            std::cout<<"PASS "<<checks<<" Learn action keyboard checks\n";return 0;
        }
        desktop::LessonView view;view.setSize((fretboardSelection||fretboardKnownCase||l3ReferenceCrossprojection||leftHandedFretboard)?1320:920,(fretboardSelection||fretboardKnownCase||l3ReferenceCrossprojection||leftHandedFretboard)?1100:680);auto* emptyCatalogState=dynamic_cast<juce::Label*>(view.findChildWithID("learn-empty-catalog-state"));check(emptyCatalogState&&emptyCatalogState->isVisible()&&emptyCatalogState->getText().toStdString()=="No source-backed Learn catalog loaded yet"&&emptyCatalogState->getTitle().toStdString()=="Learn empty catalog state marker.","Learn identifies the missing source-backed catalog before load");check(view.load(bundle),"actual component loads local bundle");check(emptyCatalogState&&!emptyCatalogState->isVisible(),"Learn hides the empty catalog marker after the representative source bundle loads");
        auto combo=[&](const char* id){auto* c=dynamic_cast<juce::ComboBox*>(view.findChildWithID(id));if(!c)throw std::runtime_error("missing combo");return c;};
        auto button=[&](const char* id){auto* c=dynamic_cast<juce::TextButton*>(view.findChildWithID(id));if(!c)throw std::runtime_error("missing button");return c;};
        auto editor=dynamic_cast<juce::TextEditor*>(view.findChildWithID("instructions"));auto tab=dynamic_cast<desktop::TabView*>(view.findChildWithID("tab"));check(editor&&tab,"real read-only text and existing TAB component");
        auto click=[&](const char* id){button(id)->triggerClick();auto delivered=std::make_shared<bool>(false);juce::MessageManager::callAsync([delivered]{*delivered=true;});auto end=std::chrono::steady_clock::now()+std::chrono::seconds(2);while(!*delivered&&std::chrono::steady_clock::now()<end)CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);check(*delivered,"actual JUCE button delivery "+std::string(id));};
        auto textButton=[&](const char* label)->juce::TextButton*{for(auto* child:view.getChildren())if(auto* candidate=dynamic_cast<juce::TextButton*>(child))if(candidate->getButtonText().toStdString()==label)return candidate;throw std::runtime_error("missing text button "+std::string(label));};
        auto picture=[&](const std::string& name){auto img=view.createComponentSnapshot(view.getLocalBounds());auto stream=juce::File(juce::String::fromUTF8((out/(name+".png")).c_str())).createOutputStream();juce::PNGImageFormat png;check(stream&&png.writeImageToStream(img,*stream),"picture "+name);};
        auto catalog=view.catalog();check(combo("lessons")->getNumItems()==13,"all13cases accessible");
#ifdef __OBJC__
        if(learnKeyboardNative){
            constexpr const char* itemId="fg:item:000002";constexpr const char* variantId="fg:variant:000006";constexpr const char* eventId="fg:item:000002:event:0001";
            guitar::Setup active;view.currentSetup=[&]()->std::optional<guitar::Setup>{return active;};
            int practiceCalls{};view.onPractice=[&](std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&){++practiceCalls;return false;};
            check(view.selectLesson(itemId)&&view.selectVariant(variantId),"native Learn keyboard test selects exact source case");
            view.setSize(640,680);view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);view.setVisible(true);
            NSView* native=(__bridge NSView*)view.getPeer()->getNativeHandle();
            [native.window makeKeyAndOrderFront:nil];
            auto pump=[&]{CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);if(auto* event=[NSApp nextEventMatchingMask:NSEventMaskAny untilDate:[NSDate dateWithTimeIntervalSinceNow:0.001] inMode:NSDefaultRunLoopMode dequeue:YES])[NSApp sendEvent:event];};
            auto key=[&](NSString* chars,unsigned short code,NSEventModifierFlags flags=static_cast<NSEventModifierFlags>(0)){
                for(bool down:{true,false}){auto* event=[NSEvent keyEventWithType:down?NSEventTypeKeyDown:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:flags timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:chars charactersIgnoringModifiers:(code==48?@"\t":chars) isARepeat:NO keyCode:code];[NSApp sendEvent:event];}
                for(int step=0;step<30;++step)pump();
            };
            std::ofstream focusTrace(out/"native-focus.tsv");focusTrace<<"phase\twidth\tfocused_id\tvisible\tenabled\n";
            auto focused=[&](const char* phase){auto* c=juce::Component::getCurrentlyFocusedComponent();focusTrace<<phase<<'\t'<<view.getWidth()<<'\t'<<(c?c->getComponentID().toStdString():"<none>")<<'\t'<<(c&&c->isShowing())<<'\t'<<(c&&c->isEnabled())<<'\n';return c;};
            auto* mode=button("mode");auto* toggle=button("compact-fretboard-toggle");
            click("mode");check(tab->isVisible()&&tab->selectEvent(eventId)&&toggle->isShowing()&&toggle->isEnabled(),"compact native window exposes selected TAB event and enabled pane switch");
            auto findDeep=[&](auto&& self,juce::Component& parent,const juce::String& id)->juce::Component*{if(parent.getComponentID()==id)return &parent;for(int i=0;i<parent.getNumChildComponents();++i)if(auto* found=self(self,*parent.getChildComponent(i),id))return found;return nullptr;};
            auto* projection=dynamic_cast<desktop::FretboardView*>(findDeep(findDeep,view,"lesson-fretboard"));
            auto* viewport=dynamic_cast<juce::Viewport*>(findDeep(findDeep,view,"lesson-fretboard-viewport"));
            auto* cue=dynamic_cast<juce::Label*>(view.findChildWithID("compact-fretboard-status"));
            check(projection&&viewport&&cue&&projection->selectedEventId()==eventId,"native window retains source-backed event projection");
            mode->grabKeyboardFocus();check(focused("mode-initial")==mode,"mode button receives actual JUCE/AppKit keyboard focus");
            key(@"\t",48);check(focused("tab-to-switch")==toggle,"AppKit Tab reaches compact fretboard switch from Show instructions");
            key(@"\u0019",48,NSEventModifierFlagShift);check(focused("shift-tab-to-mode")==mode,"AppKit Shift-Tab returns from switch to Show instructions");
            key(@"\t",48);check(focused("tab-to-switch-again")==toggle,"AppKit Tab reenters compact switch without a focus trap");
            key(@" ",49);check(focused("space-shows-fretboard")==toggle&&viewport->isShowing()&&!tab->isShowing()&&toggle->getButtonText()=="Show TAB"&&projection->selectedEventId()==eventId,"native Space activates switch once and preserves source event");
            check(cue->isShowing()&&cue->getText().contains("Right-handed fretboard")&&cue->getText().contains(eventId)&&cue->getText().contains("string 6 fret 5 A2")&&cue->getAccessibilityHandler()->getTitle().contains(eventId),"non-color selected-event cue states orientation, source ID, string/fret/pitch accessibly");
            picture("keyboard-compact-board-right");
            key(@"\r",36);check(focused("return-shows-tab")==toggle&&tab->isShowing()&&!viewport->isShowing()&&toggle->getButtonText()=="Show fretboard"&&tab->selectedEvent()==eventId,"native Return returns to TAB exactly once without losing selection");
            key(@"\t",48);auto* compactNext=focused("compact-tab-after-switch");check(compactNext&&compactNext!=toggle&&compactNext->isShowing()&&compactNext->isEnabled(),"native Tab leaves compact switch for another visible enabled control");
            key(@"\u0019",48,NSEventModifierFlagShift);check(focused("compact-shift-tab-back")==toggle,"native Shift-Tab returns to compact switch after TAB is restored");
            active.handedness=guitar::Handedness::Left;active.openMidi[0]=38;active.capo=2;view.refreshSetup();
            key(@"\r",36);check(focused("return-shows-left-board")==toggle&&viewport->isShowing()&&!tab->isShowing()&&cue->getText().contains("Left-handed fretboard")&&cue->getText().contains(eventId)&&cue->getAccessibilityHandler()->getTitle().contains("Left-handed fretboard")&&projection->markers().front().midi==45,"native Return reopens left-handed board with unchanged source pitch, ID and non-color cue");
            picture("keyboard-compact-board-left");
            view.setSize(920,680);[native.window makeKeyAndOrderFront:nil];
            auto* wideSummary=dynamic_cast<juce::Label*>(view.findChildWithID("summary"));
            check(wideSummary&&wideSummary->isShowing(),"920-pixel selected-case summary remains visible beside source projection");
            juce::AttributedString summaryMeasure;summaryMeasure.setWordWrap(juce::AttributedString::byWord);summaryMeasure.append(wideSummary->getText(),wideSummary->getFont());
            juce::TextLayout summaryLayout;summaryLayout.createLayout(summaryMeasure,static_cast<float>(wideSummary->getWidth()-8));
            std::ofstream(out/"wide-summary-fit.tsv")<<"width\tlabel_height\tmeasured_text_height\tcontrols_y\n"<<view.getWidth()<<'\t'<<wideSummary->getHeight()<<'\t'<<summaryLayout.getHeight()<<'\t'<<mode->getY()<<'\n';
            check(static_cast<float>(wideSummary->getHeight())>=summaryLayout.getHeight()&&wideSummary->getBottom()+4<=mode->getY(),"920-pixel selected-case text fits before the source controls without clipping");
            check(!toggle->isShowing()&&tab->isShowing()&&viewport->isShowing()&&viewport->getViewPositionY()==0&&projection->selectedEventId()==eventId,"920-pixel native window restores side-by-side source projection and its visible heading after compact scroll");
            auto* wideFocus=focused("wide-after-resize");check(wideFocus&&wideFocus!=toggle&&wideFocus->isShowing()&&wideFocus->isEnabled(),"hiding focused compact switch transfers focus to a visible enabled control");
            key(@"\t",48);auto* wideNext=focused("wide-tab");check(wideNext&&wideNext!=toggle&&wideNext->isShowing()&&wideNext->isEnabled()&&wideNext!=wideFocus,"920-pixel native Tab continues through visible controls without compact focus trap");
            key(@"\u0019",48,NSEventModifierFlagShift);check(focused("wide-shift-tab")==wideFocus,"920-pixel native Shift-Tab returns to the prior visible control");
            picture("keyboard-wide-side-by-side");
            check(practiceCalls==0&&view.selectedLesson()==itemId&&view.selectedVariant()==variantId&&projection->markers().front().midi==45&&catalog->variant(itemId,variantId).model->source().instrument.openMidi.front()==40&&catalog->variant(itemId,variantId).model->source().instrument.capo==0,"native keyboard browsing creates no Practice handoff and retains source tuning/capo/pitch");
            focusTrace.flush();check(focusTrace.good(),"native focus trace flushed");
            view.removeFromDesktop();
            std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"practiceCalls\":"<<practiceCalls<<",\"nativeAppKit\":true,\"curriculumCredit\":false}\n";
            std::cout<<"PASS "<<checks<<" native Learn keyboard checks\n";return 0;
        }
#endif
        if(learnCompact){
            constexpr const char* itemId="fg:item:000002";constexpr const char* variantId="fg:variant:000006";constexpr const char* eventId="fg:item:000002:event:0001";
            guitar::Setup active;view.currentSetup=[&]()->std::optional<guitar::Setup>{return active;};
            int practiceCalls{};view.onPractice=[&](std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&){++practiceCalls;return false;};
            check(view.selectLesson(itemId)&&view.selectVariant(variantId),"compact Learn selects exact source case and variant");
            view.setSize(640,680);
            std::ofstream geometry(out/"geometry.tsv");geometry<<"state\tcomponent\tx\ty\twidth\theight\tvisible\n";
            auto record=[&](const char* state,const char* id){auto* c=view.findChildWithID(id);if(!c)throw std::runtime_error(std::string("missing compact component ")+id);const auto b=c->getBounds();geometry<<state<<'\t'<<id<<'\t'<<b.getX()<<'\t'<<b.getY()<<'\t'<<b.getWidth()<<'\t'<<b.getHeight()<<'\t'<<c->isVisible()<<'\n';};
            for(const auto* id:{"inventory","lesson-search","lessons","variants","practice-selection","practice-span","sections","summary","instructions","mode","details"})record("source",id);
            auto* summary=dynamic_cast<juce::Label*>(view.findChildWithID("summary"));auto* inventory=dynamic_cast<juce::Label*>(view.findChildWithID("inventory"));auto* setup=view.findChildWithID("setup-summary");
            check(editor->getHeight()>=150&&view.getLocalBounds().contains(editor->getBounds())&&editor->getText().toStdString()==catalog->text(itemId,variantId,lesson::Section::Instructions),"compact source editor has at least 150 px of contained scrollable authored text without substitution");
            check(summary&&inventory&&setup&&summary->getText().toStdString().find(itemId)!=std::string::npos&&summary->getText().toStdString().find("L3-TXT5-21 L3-TXT28-46")!=std::string::npos&&summary->getText().toStdString().find("no completion or credit")!=std::string::npos&&inventory->getText().toStdString().find("Curriculum review: Pending")!=std::string::npos,"compact visible summary retains source, refs, no-credit boundary and preview status");
            for(const auto* id:{"inventory","lesson-search","lessons","variants","practice-selection","practice-span","sections","summary","instructions","mode","details","setup-summary","setup-button"}){auto* c=view.findChildWithID(id);check(c&&view.getLocalBounds().contains(c->getBounds())&&c->getWidth()>0&&c->getHeight()>0,std::string("compact visible control is contained: ")+id);}
            check(inventory->getBottom()<=view.findChildWithID("lesson-search-label")->getY()&&view.findChildWithID("lesson-search")->getBottom()<=combo("lessons")->getY()&&combo("variants")->getBottom()<=view.findChildWithID("selected-tempo")->getY()&&summary->getBottom()<=setup->getY()&&setup->getBottom()<=editor->getY(),"compact source rows remain ordered without vertical overlap");
            picture("baseline-or-final-compact-source");
            combo("sections")->setSelectedId(2,juce::sendNotificationSync);
            check(editor->getText().toStdString()==catalog->text(itemId,variantId,lesson::Section::Context),"compact section selector reads the exact retained source section");
            combo("sections")->setSelectedId(1,juce::sendNotificationSync);
            click("mode");check(tab->selectEvent(eventId),"compact TAB selects exact L3 event");
            auto findDeep=[&](auto&& self,juce::Component& parent,const juce::String& id)->juce::Component*{if(parent.getComponentID()==id)return &parent;for(int i=0;i<parent.getNumChildComponents();++i)if(auto* found=self(self,*parent.getChildComponent(i),id))return found;return nullptr;};
            auto* projection=dynamic_cast<desktop::FretboardView*>(findDeep(findDeep,view,"lesson-fretboard"));
            auto* viewport=dynamic_cast<juce::Viewport*>(findDeep(findDeep,view,"lesson-fretboard-viewport"));
            check(projection&&viewport&&projection->selectedEventId()==eventId&&projection->markers().size()==1,"compact source projection retains exact L3 marker");
            auto* compactToggle=button("compact-fretboard-toggle");
            check(tab->isVisible()&&tab->getWidth()>=500&&view.getLocalBounds().contains(tab->getBounds())&&compactToggle->isVisible()&&compactToggle->isEnabled()&&compactToggle->getBounds().getIntersection(combo("sections")->getBounds()).isEmpty(),"compact full-width TAB and fretboard switch are visible, contained and nonoverlapping");
            for(const auto* id:{"lessons","variants","sections","summary","tab","lesson-fretboard-viewport","mode","compact-fretboard-toggle"})record("tab-right",id);
            picture("baseline-or-final-compact-tab-right");
            click("compact-fretboard-toggle");
            auto* boardStatus=dynamic_cast<juce::Label*>(view.findChildWithID("compact-fretboard-status"));
            check(!tab->isVisible()&&viewport->isVisible()&&viewport->getWidth()>=500&&view.getLocalBounds().contains(viewport->getBounds())&&projection->selectedEventId()==eventId,"compact switch presents the full-width selected source fretboard without losing TAB selection");
            check(boardStatus&&boardStatus->isVisible()&&boardStatus->getText().toStdString().find("Right-handed fretboard")!=std::string::npos&&boardStatus->getText().toStdString().find(eventId)!=std::string::npos&&boardStatus->getText().toStdString().find("string 6 fret 5 A2")!=std::string::npos&&boardStatus->getBottom()<=viewport->getY(),"compact fixed fretboard cue keeps source event, orientation and marker fact above the scrolled board");
            const auto rightX=projection->markerBounds().getCentreX();
            const auto markerY=projection->markerBounds().getCentreY();
            check(markerY>=viewport->getViewPositionY()&&markerY<viewport->getViewPositionY()+viewport->getMaximumVisibleHeight(),"compact fretboard scroll centers the selected string-six marker in view");
            picture("baseline-or-final-compact-fretboard-right");
            active.handedness=guitar::Handedness::Left;active.openMidi[0]=38;active.capo=2;view.refreshSetup();
            const auto& compactMarker=projection->markers().front();
            check(projection->markerBounds().getCentreX()>rightX&&projection->selectedEventId()==eventId&&compactMarker.midi==45&&compactMarker.pitchName=="A2"&&compactMarker.relativeFret==5&&compactMarker.physicalFret==5&&catalog->variant(itemId,variantId).model->source().instrument.openMidi.front()==40&&catalog->variant(itemId,variantId).model->source().instrument.capo==0&&practiceCalls==0&&boardStatus->getText().toStdString().find("Left-handed fretboard")!=std::string::npos,"compact left-handed refresh mirrors marker while retaining source tuning/capo, pitch/fret/event and no Practice handoff");
            picture("baseline-or-final-compact-fretboard-left");
            view.setSize(920,680);
            check(tab->isVisible()&&viewport->isVisible()&&viewport->getX()>=tab->getRight()&&!compactToggle->isVisible()&&projection->selectedEventId()==eventId,"920-pixel layout restores side-by-side TAB/fretboard with the same source event");
            view.setSize(640,680);
            check(!tab->isVisible()&&viewport->isVisible()&&boardStatus->isVisible()&&projection->selectedEventId()==eventId,"return to 640-pixel layout retains the compact selected fretboard pane");
            click("compact-fretboard-toggle");
            check(tab->isVisible()&&!viewport->isVisible()&&tab->selectedEvent()==eventId,"compact switch returns to the same selectable TAB event");
            std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"practiceCalls\":"<<practiceCalls<<",\"nativeAudio\":false,\"curriculumCredit\":false}\n";
            std::cout<<"PASS "<<checks<<" compact Learn observation checks\n";return 0;
        }
        if(leftHandedFretboard){
            auto findDeep=[&](auto&& self,juce::Component& parent,const juce::String& id)->juce::Component*{if(parent.getComponentID()==id)return &parent;for(int i=0;i<parent.getNumChildComponents();++i)if(auto* found=self(self,*parent.getChildComponent(i),id))return found;return nullptr;};
            auto* projection=dynamic_cast<desktop::FretboardView*>(findDeep(findDeep,view,"lesson-fretboard"));
            check(projection,"Learn contains the source-validated fretboard projection");
            int practiceCalls{};view.onPractice=[&](std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&){++practiceCalls;return false;};
            guitar::Setup active;view.currentSetup=[&]()->std::optional<guitar::Setup>{return active;};
            constexpr const char* itemId="fg:item:000002";constexpr const char* variantId="fg:variant:000006";constexpr const char* eventId="fg:item:000002:event:0001";
            check(view.selectLesson(itemId)&&view.selectVariant(variantId),"Learn selects the exact retained L3 source case");
            const auto& source=catalog->variant(itemId,variantId).model->source();
            check(source.instrument.openMidi.front()==40&&source.instrument.capo==0,"source keeps its authored tuning and capo");
            click("mode");check(tab->selectEvent(eventId),"TAB selects the exact source note event");
            juce::Component* board=nullptr;for(auto* child:projection->getChildren())if(child->getTitle()=="Fretboard: source event positions")board=child;
            check(board&&board->getNumChildComponents()==1,"right-handed source marker is visible");
            const auto marker=projection->markers().front();
            const auto sourceSummary=projection->sourceSummary(),timingSummary=projection->timingSummary(),statusSummary=projection->statusSummary();
            const int rightX=board->getChildComponent(0)->getBounds().getCentreX();
            picture("learn-source-right-handed");
            active.handedness=guitar::Handedness::Left;active.openMidi[0]=38;active.capo=2;
            view.refreshSetup();
            const int leftX=board->getChildComponent(0)->getBounds().getCentreX();
            const auto& mirrored=projection->markers().front();
            check(leftX>rightX&&mirrored.sourceId==marker.sourceId&&mirrored.sourceRef==marker.sourceRef&&mirrored.eventId==marker.eventId&&mirrored.internalString==marker.internalString&&mirrored.displayString==marker.displayString&&mirrored.relativeFret==marker.relativeFret&&mirrored.physicalFret==marker.physicalFret&&mirrored.midi==marker.midi&&mirrored.pitchName==marker.pitchName&&mirrored.finger==marker.finger,"active left-handed setup mirrors marker while source tuning/capo, pitch, fret and finger stay authoritative");
            check(projection->selectedEventId()==eventId&&projection->sourceSummary()==sourceSummary&&projection->timingSummary()==timingSummary&&projection->statusSummary()==statusSummary&&tab->selectedEvent()==eventId&&practiceCalls==0,"setup refresh retains selected TAB event, source/timing/status identity and no Practice handoff");
            picture("learn-source-left-handed");
            active.handedness=guitar::Handedness::Right;view.refreshSetup();
            check(board->getChildComponent(0)->getBounds().getCentreX()==rightX&&practiceCalls==0,"returning to right-handed setup restores the original board column without an Attempt");
            view.currentSetup={};view.refreshSetup();
            check(board->getChildComponent(0)->getBounds().getCentreX()==rightX,"missing active setup defaults to right-handed presentation");
            std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"practiceCalls\":"<<practiceCalls<<",\"nativeAudio\":false,\"curriculumCredit\":false}\n";
            std::cout<<"PASS "<<checks<<" Learn left-handed fretboard checks\n";return 0;
        }
        if(l3ReferenceCrossprojection){
            auto findDeep=[&](auto&& self,juce::Component& parent,const juce::String& id)->juce::Component*{if(parent.getComponentID()==id)return &parent;for(int i=0;i<parent.getNumChildComponents();++i)if(auto* found=self(self,*parent.getChildComponent(i),id))return found;return nullptr;};
            auto* projection=dynamic_cast<desktop::FretboardView*>(findDeep(findDeep,view,"lesson-fretboard"));auto* viewport=dynamic_cast<juce::Viewport*>(findDeep(findDeep,view,"lesson-fretboard-viewport"));auto* hint=dynamic_cast<juce::Label*>(view.findChildWithID("lesson-fretboard-selection-hint"));check(projection&&viewport&&hint,"Learn contains the integrated source-backed fretboard view");
            int practiceCalls{};view.onPractice=[&](std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&){++practiceCalls;return false;};
            constexpr const char* itemId="fg:item:000002";constexpr const char* variantId="fg:variant:000006";constexpr const char* eventId="fg:item:000002:event:0001";
            check(view.selectLesson(itemId)&&view.selectedLesson()==itemId&&view.selectVariant(variantId)&&view.selectedVariant()==variantId,"Learn selects the admitted L3 ascending D-even direction by exact IDs");
            const auto& variant=catalog->variant(itemId,variantId);const auto admission=catalog->admit(itemId,variantId);const auto selectedModel=variant.model;
            check(admission&&admission->practiceAllowed()&&admission->model()==selectedModel&&!selectedModel->source().syntheticFixture,"the reviewed L3 source model has an exact non-synthetic admitted reference capability");
            const auto& timing=catalog->lesson(itemId).record.object().at("timing");const auto& grouping=variant.authored.object().at("grouping");std::int64_t notesPerBeat{};check(timing.object().at("status").string()=="unresolved"&&grouping.object().at("kind").string()=="even_subdivision"&&grouping.object().at("notes_per_beat").integer(notesPerBeat)&&notesPerBeat==4,"literal source onset/duration remain unresolved; the selected direction supplies its explicit four-note quarter grouping");
            const auto& source=selectedModel->source();check(source.sourceRefs==std::vector<std::string>{"L3-TXT5-21","L3-TXT28-46"},"selected L3 variant retains both movement-rule and event-sequence source references");const auto sourceEvent=std::find_if(source.events.begin(),source.events.end(),[](const auto& event){return event.id==eventId;});
            check(sourceEvent!=source.events.end()&&sourceEvent->kind==music::Kind::Note&&sourceEvent->sourceRef=="L3-TXT28-46"&&sourceEvent->span==music::Span{Rational{0,1},Rational{1,4}}&&sourceEvent->tones.size()==1,"selected L3 event retains its profile-bound source, ID and grouping-projected quarter-unit span");
            const auto& tone=sourceEvent->tones.front();check(tone.string==1&&tone.fret==5&&tone.midi==45&&tone.finger=="1","selected L3 event retains its authored low-E string, fret, pitch and finger");
            click("mode");check(tab->isVisible()&&tab->document()&&&tab->document()->source()==&source,"Learn TAB uses the exact selected immutable L3 source model");
            const auto* tabEvent=tab->document()->event(eventId);check(tab->selectEvent(eventId)&&tab->selectedEvent()==eventId&&tabEvent&&tabEvent->id==sourceEvent->id&&tabEvent->sourceRef==sourceEvent->sourceRef&&tabEvent->span==sourceEvent->span&&tabEvent->tones.size()==1,"TAB selects the exact L3 authored event with the same source reference and span");
            bool markerMatches=projection->selectedEventId()==eventId&&projection->markers().size()==1&&viewport->isVisible()&&!hint->isVisible()&&projection->sourceSummary().find(source.itemId)!=std::string::npos&&projection->sourceSummary().find(eventId)!=std::string::npos&&projection->sourceSummary().find(sourceEvent->sourceRef)!=std::string::npos;
            if(markerMatches){const auto& marker=projection->markers().front();markerMatches=marker.sourceId==source.itemId&&marker.sourceRef==sourceEvent->sourceRef&&marker.eventId==eventId&&marker.internalString==tone.string&&marker.displayString==7-tone.string&&marker.relativeFret==tone.fret&&marker.midi==tone.midi&&marker.finger==tone.finger;}
            check(markerMatches&&viewport->getX()>=tab->getRight(),"Fretboard marker beside TAB preserves the exact selected L3 source event and tone");picture("l3-source-tab-fretboard");
            scheduler::Owner owner;owner.id[0]=42;owner.id[6]=0x40;owner.id[8]=0x80;owner.generation=owner.epoch=1;constexpr std::uint64_t binding=1;constexpr std::uint32_t rate=44100;constexpr std::uint16_t bpm=120;
            const auto config=admission->referenceConfiguration(owner,binding,rate,bpm);admission->validateReference(config);const auto program=reference::compile(admission->model(),config);
            check(&program.source()==selectedModel.get()&&&program.source().source()==&source&&program.source().source().itemId==itemId&&program.schedule().sourceBinding()==admission->sourceBinding(),"ReferenceAudio program uses the same immutable admitted L3 model and source binding");
            std::size_t selectedVoice=program.voices().size(),matches=0;
            for(std::size_t i=0;i<program.voices().size();++i)if(std::find(program.voices()[i].sourceEvents.begin(),program.voices()[i].sourceEvents.end(),eventId)!=program.voices()[i].sourceEvents.end()){selectedVoice=i;++matches;}
            check(matches==1,"reference PCM plan maps the selected L3 event to exactly one voice");const auto& voice=program.voices().at(selectedVoice);const auto voiceEnd=*sourceEvent->span.onset+*sourceEvent->span.duration;
            check(voice.sourceEvents==std::vector<std::string>{eventId}&&voice.string==tone.string&&voice.midi==tone.midi&&voice.onset==*sourceEvent->span.onset&&voice.end==voiceEnd,"reference voice keeps selected event ID, pitch, and authored gate boundaries");
            const auto plannedSourceEvent=static_cast<std::uint32_t>(selectedVoice+1);const auto& scheduled=program.schedule().events();const auto attack=std::find_if(scheduled.begin(),scheduled.end(),[&](const auto& event){return event.sourceEvent==plannedSourceEvent&&event.role==scheduler::Role::Reference&&event.action==scheduler::Action::Attack;});const auto release=std::find_if(scheduled.begin(),scheduled.end(),[&](const auto& event){return event.sourceEvent==plannedSourceEvent&&event.role==scheduler::Role::Reference&&event.action==scheduler::Action::Release;});
            std::uint64_t selectedStart{},selectedEnd{},expectedFrames{};check(attack!=scheduled.end()&&release!=scheduled.end()&&attack->structural==voice.onset&&release->structural==voice.end&&attack->offset.n==voice.startFrames.n&&attack->offset.d==voice.startFrames.d&&release->offset.n==voice.endFrames.n&&release->offset.d==voice.endFrames.d&&scheduler::round(voice.startFrames,selectedStart)&&scheduler::round(voice.endFrames,selectedEnd)&&scheduler::round(program.schedule().duration(),expectedFrames),"scheduler Reference Attack/Release facts preserve the selected source event's planned gate");
            auto alternate=catalog->admit(itemId,"fg:variant:000008");const auto alternateConfig=alternate->referenceConfiguration(owner,binding+1,rate,bpm);std::string refusal;
            try{admission->validateReference(alternateConfig);}catch(const std::exception& ex){refusal=ex.what();}
            check(!refusal.empty()&&refusal.find("no substitute source or cutpoint")!=std::string::npos,"selected L3 admission refuses a valid reference configuration bound to the alternate L3 direction");
            const auto alternateProgram=reference::compile(alternate->model(),alternateConfig);check(!program.compatibleTempo(alternateProgram),"ReferenceAudio refuses hot substitution to a different L3 source model");
            scheduler::Cursor cursor;reference::Renderer renderer;check(cursor.start(program.schedule(),owner,binding)&&renderer.bind(program),"software Scheduler Cursor and ReferenceAudio Renderer bind the exact L3 program");
            auto pcmPath=out/"reference-l3.pcm.f32";std::ofstream pcm(pcmPath,std::ios::binary);check(pcm.good(),"Build-only PCM trace opens");std::ofstream facts(out/"reference-l3-facts.tsv");facts<<"frame\tkind\tvoice_event\trole\taction\n";
            L3Facts buffer;std::uint64_t written{};std::size_t factCount{};bool finite=true,selectedMatches=true,selectedNonzero=false,requestedStop=false;
            while(written<expectedFrames){const auto begin=cursor.snapshot().processedThrough;buffer.count=0;const bool running=cursor.process(256,owner,retainL3Fact,&buffer,stopL3Reference,nullptr);const auto end=cursor.snapshot().processedThrough;if(end<begin||end>expectedFrames||(end==begin&&running))throw std::runtime_error("L3 cursor made invalid/no progress");std::size_t index{};
                for(auto frame=begin;frame<end;++frame){while(index<buffer.count&&buffer.values[index].frame==frame){const auto& fact=buffer.values[index++];if(!renderer.accept(fact))throw std::runtime_error("ReferenceAudio refused a scheduled L3 fact");facts<<fact.frame<<'\t'<<static_cast<int>(fact.kind)<<'\t'<<fact.sourceEvent<<'\t'<<static_cast<int>(fact.role)<<'\t'<<static_cast<int>(fact.action)<<'\n';++factCount;}float sample{};if(!renderer.sampleFrame(frame,sample))throw std::runtime_error("ReferenceAudio refused an L3 PCM frame");finite=finite&&std::isfinite(sample);if(frame>=selectedStart&&frame<selectedEnd){const auto expected=static_cast<float>(reference::sample(program.method(),voice.hz,frame-selectedStart,selectedEnd-selectedStart,rate)/6.0);selectedMatches=selectedMatches&&sample==expected;selectedNonzero=selectedNonzero||sample!=0.0f;}pcm.write(reinterpret_cast<const char*>(&sample),sizeof sample);if(!pcm.good())throw std::runtime_error("Could not write deterministic L3 PCM trace");++written;}
                while(index<buffer.count&&buffer.values[index].frame==end){const auto& fact=buffer.values[index++];if(!renderer.accept(fact))throw std::runtime_error("ReferenceAudio refused an L3 boundary fact");facts<<fact.frame<<'\t'<<static_cast<int>(fact.kind)<<'\t'<<fact.sourceEvent<<'\t'<<static_cast<int>(fact.role)<<'\t'<<static_cast<int>(fact.action)<<'\n';++factCount;}if(index!=buffer.count)throw std::runtime_error("L3 fact arrived outside the processed frame range");if(!running){requestedStop=cursor.snapshot().reason==scheduler::StopReason::Requested;break;}}
            pcm.close();facts.close();check(requestedStop&&written==expectedFrames&&factCount==scheduled.size()+1,"one complete exact-span software reference cycle closes on its requested boundary");check(finite&&selectedMatches&&selectedNonzero,"generated L3 PCM is finite, nonzero for the selected note, and matches its exact reference voice samples");
            check(practiceCalls==0&&view.selectedLesson()==itemId&&view.selectedVariant()==variantId,"cross-projection inspection starts no Practice handoff or activity");
            std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"item\":\""<<itemId<<"\",\"variant\":\""<<variantId<<"\",\"event\":\""<<eventId<<"\",\"sourceRef\":\""<<sourceEvent->sourceRef<<"\",\"referenceFrames\":"<<written<<",\"scheduledFacts\":"<<factCount<<",\"selectedPcmMatches\":"<<(selectedMatches?"true":"false")<<",\"foreignSourceRefused\":\""<<refusal<<"\",\"practiceCalls\":"<<practiceCalls<<",\"nativeOutput\":false,\"profileAccess\":false,\"attemptCreated\":false,\"curriculumCredit\":false}\n";
            std::cout<<"PASS "<<checks<<" L3 source/TAB/fretboard/reference PCM cross-projection checks\n";return 0;
        }
        if(fretboardKnownCase){
            auto findDeep=[&](auto&& self,juce::Component& parent,const juce::String& id)->juce::Component*{if(parent.getComponentID()==id)return &parent;for(int i=0;i<parent.getNumChildComponents();++i)if(auto* found=self(self,*parent.getChildComponent(i),id))return found;return nullptr;};
            auto* projection=dynamic_cast<desktop::FretboardView*>(findDeep(findDeep,view,"lesson-fretboard"));auto* viewport=dynamic_cast<juce::Viewport*>(findDeep(findDeep,view,"lesson-fretboard-viewport"));auto* hint=dynamic_cast<juce::Label*>(view.findChildWithID("lesson-fretboard-selection-hint"));
            check(projection&&viewport&&hint,"Learn embeds the reviewed fretboard component for the known source case");
            const auto& l15=catalog->lesson("fg:item:000004");check(l15.record.object().at("status").string()=="converted_candidate"&&!l15.record.object().at("runtime_eligible").boolean(),"L15 source record remains converted_candidate and explicitly not runtime eligible");
            check(view.selectLesson(l15.id)&&view.selectedLesson()=="fg:item:000004"&&view.selectedVariant()=="fg:variant:000033"&&view.selectVariant("fg:variant:000033"),"Learn selects the exact retained L15 triplet-D source case and variant");
            const auto& source= catalog->variant("fg:item:000004","fg:variant:000033").model->source();
            const std::vector<std::string> expectedRefs{"L15-TXT21-32","L15-TXT59-81","L15-TXT392-398","L15-TXT21-47","L15-TXT386-399"};
            check(source.itemId=="fg:item:000004"&&source.sourceRefs==expectedRefs&&catalog->lesson("fg:item:000004").record.object().at("title").string()=="First rolling triplet / upper-octave context","selected L15 model retains its exact item, authored source-reference set and case identity");
            auto* practice=dynamic_cast<juce::TextButton*>(view.findChildWithID("practice-selection"));auto* summary=dynamic_cast<juce::Label*>(view.findChildWithID("summary"));int practiceCalls{};view.onPractice=[&](std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&){++practiceCalls;return false;};
            check(practice&&summary&&!practice->isEnabled()&&practice->getTitle().toStdString().find("runtime admission refused fg:item:000004 / fg:variant:000033")!=std::string::npos&&summary->getText().toStdString().find("Runtime admission refused this selection")!=std::string::npos,"non-runtime candidate exposes the truthful Learn refusal and no Practice action");
            check(!view.practiceSelected()&&practiceCalls==0,"direct Practice request refuses L15 without invoking the Practice handoff callback");
            click("mode");check(tab->isVisible()&&tab->document()&&tab->document()->source().itemId==source.itemId&&hint->isVisible()&&!viewport->isVisible(),"L15 opens the same source TAB with no previous-event marker");
            struct ExpectedEvent{std::string id,sourceRef;int string,fret,midi;std::string finger;music::Span span;};
            const std::vector<ExpectedEvent> expected{
                {"fg:item:000004:event:0001","L15-TXT59-81",1,5,45,"2",{Rational{0,1},Rational{1,3}}},
                {"fg:item:000004:event:0002","L15-TXT59-81",1,7,47,"4",{Rational{1,3},Rational{1,3}}},
                {"fg:item:000004:event:0003","L15-TXT59-81",2,4,49,"1",{Rational{2,3},Rational{1,3}}}
            };
            check(source.events.size()==expected.size()&&std::all_of(source.events.begin(),source.events.end(),[](const auto& e){return e.kind==music::Kind::Note;}),"L15 triplet-D contains exactly three authored Notes and no Rest");
            std::size_t index{};
            for(const auto& expectedEvent:expected){
                const auto modelEvent=std::find_if(source.events.begin(),source.events.end(),[&](const auto& e){return e.id==expectedEvent.id;});
                check(modelEvent!=source.events.end()&&modelEvent->kind==music::Kind::Note&&modelEvent->sourceRef==expectedEvent.sourceRef&&modelEvent->span==expectedEvent.span&&modelEvent->tones.size()==1,"L15 model retains the exact authored event/source/span "+expectedEvent.id);
                const auto* tabEvent=tab->document()->event(expectedEvent.id);
                check(tabEvent&&tabEvent->id==modelEvent->id&&tabEvent->sourceRef==modelEvent->sourceRef&&tabEvent->kind==modelEvent->kind&&tabEvent->span==modelEvent->span&&tabEvent->span==expectedEvent.span&&tabEvent->tones.size()==1,"TAB event identity, source reference and rational span match the selected Learn model "+expectedEvent.id);
                const auto& tone=modelEvent->tones.front();check(tone.string==expectedEvent.string&&tone.fret==expectedEvent.fret&&tone.midi==expectedEvent.midi&&tone.finger==expectedEvent.finger,"L15 authored tone retains string/fret/MIDI/finger "+expectedEvent.id);
                check(tab->selectEvent(expectedEvent.id)&&tab->selectedEvent()==expectedEvent.id,"TAB selects the exact L15 source event "+expectedEvent.id);
                const auto markerCount=projection->markers().size();bool markerMatches=markerCount==1&&projection->selectedEventId()==expectedEvent.id&&viewport->isVisible()&&!hint->isVisible()&&projection->sourceSummary().find(source.itemId)!=std::string::npos&&projection->sourceSummary().find(expectedEvent.id)!=std::string::npos&&projection->sourceSummary().find(expectedEvent.sourceRef)!=std::string::npos;
                if(markerMatches){const auto& marker=projection->markers().front();markerMatches=marker.sourceId==source.itemId&&marker.sourceRef==expectedEvent.sourceRef&&marker.eventId==expectedEvent.id&&marker.internalString==expectedEvent.string&&marker.displayString==7-expectedEvent.string&&marker.relativeFret==expectedEvent.fret&&marker.midi==expectedEvent.midi&&marker.finger==expectedEvent.finger;}
                check(markerMatches,"fretboard marker exactly matches the same L15 TAB/model event and authored tone "+expectedEvent.id);
                if(index==0||index+1==expected.size())picture("L15-triplet-event-"+std::to_string(index+1));
                ++index;
            }
            check(practiceCalls==0,"read-only L15 rendering never invokes the Practice handoff");
            const auto& restLesson=catalog->lesson("fg:item:000007");const auto& restVariant=restLesson.variants.front();const auto restEvent=std::find_if(restVariant.model->source().events.begin(),restVariant.model->source().events.end(),[](const auto& event){return event.kind==music::Kind::Rest;});
            check(restEvent!=restVariant.model->source().events.end(),"retained L48 source supplies a Rest for the separate clearing check");check(view.selectLesson(restLesson.id)&&view.selectedVariant()==restVariant.id,"Learn switches to the retained L48 source case");click("mode");check(hint->isVisible()&&!viewport->isVisible(),"new L48 source selection hides prior L15 markers");check(tab->selectEvent(restEvent->id),"TAB accepts the exact L48 Rest event");check(projection->markers().empty()&&projection->selectedEventId().empty()&&projection->statusSummary().find("not a note or chord")!=std::string::npos&&viewport->isVisible(),"L48 Rest refusal clears every previous L15 marker");picture("L48-rest-cleared");
            std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"item\":\"fg:item:000004\",\"variant\":\"fg:variant:000033\",\"events\":3,\"runtimeEligible\":false,\"practiceCalls\":"<<practiceCalls<<",\"restClearItem\":\"fg:item:000007\",\"nativeAudio\":false,\"profileAccess\":false,\"curriculumCredit\":false}\n";
            std::cout<<"PASS "<<checks<<" Learn fretboard known-case checks\n";return 0;
        }
        if(fretboardSelection){
            auto findDeep=[&](auto&& self,juce::Component& parent,const juce::String& id)->juce::Component*{if(parent.getComponentID()==id)return &parent;for(int i=0;i<parent.getNumChildComponents();++i)if(auto* found=self(self,*parent.getChildComponent(i),id))return found;return nullptr;};
            auto* projection=dynamic_cast<desktop::FretboardView*>(findDeep(findDeep,view,"lesson-fretboard"));auto* viewport=dynamic_cast<juce::Viewport*>(findDeep(findDeep,view,"lesson-fretboard-viewport"));auto* hint=dynamic_cast<juce::Label*>(view.findChildWithID("lesson-fretboard-selection-hint"));
            check(projection&&viewport&&hint,"Learn embeds the reviewed fretboard component in a source-selection viewport");
            int practiceCalls{};view.onPractice=[&](std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&){++practiceCalls;return false;};
            check(view.selectFirstAdmitted()&&view.selectedLesson()=="fg:item:000002"&&view.selectedVariant()=="fg:variant:000006","focused projection uses the exact first admitted source case and selected variant");
            const auto selectedModel=catalog->variant(view.selectedLesson(),view.selectedVariant()).model;const auto& source=selectedModel->source();
            const auto sourceEvent=std::find_if(source.events.begin(),source.events.end(),[](const auto& event){return event.kind==music::Kind::Note||event.kind==music::Kind::Chord;});
            check(sourceEvent!=source.events.end()&&!sourceEvent->sourceRef.empty(),"selected admitted source contains a supported note/chord event with an authored source reference");
            click("mode");check(tab->isVisible()&&tab->document()&&tab->document()->source().itemId==source.itemId,"Learn opens the source TAB for the exact selected model");
            check(hint->isVisible()&&!viewport->isVisible()&&hint->getText().toStdString().find("Select a source note or chord in TAB")!=std::string::npos,"empty TAB selection has a plain learner next action without a stale projection");
            check(tab->selectEvent(sourceEvent->id),"TAB accepts the original source event selection");
            auto* tabEvent=tab->document()->event(sourceEvent->id);const auto markerCount=projection->markers().size();
            bool markersMatch=tabEvent&&tabEvent->id==sourceEvent->id&&tabEvent->sourceRef==sourceEvent->sourceRef&&tab->selectedEvent()==sourceEvent->id&&projection->selectedEventId()==tab->selectedEvent()&&projection->sourceSummary().find(source.itemId)!=std::string::npos&&projection->sourceSummary().find(sourceEvent->id)!=std::string::npos&&projection->sourceSummary().find(sourceEvent->sourceRef)!=std::string::npos&&markerCount==sourceEvent->tones.size();
            for(std::size_t i=0;markersMatch&&i<markerCount;++i){const auto& marker=projection->markers()[i];const auto& tone=sourceEvent->tones[i];markersMatch=marker.sourceId==source.itemId&&marker.sourceRef==sourceEvent->sourceRef&&marker.eventId==sourceEvent->id&&marker.internalString==tone.string&&marker.displayString==7-tone.string&&marker.relativeFret==tone.fret&&marker.midi==tone.midi&&marker.finger==tone.finger;}
            check(markersMatch&&viewport->isVisible()&&!hint->isVisible()&&viewport->getX()>=tab->getRight(),"same selected source event and exact tone identity project beside TAB without reordering or substitution");
            check(practiceCalls==0,"source event inspection creates no Practice handoff, Attempt, audio or curriculum credit");
            picture("learn-fretboard-selected-event");
            const auto& restLesson=catalog->lesson("fg:item:000007");const auto& restVariant=restLesson.variants.front();const auto restEvent=std::find_if(restVariant.model->source().events.begin(),restVariant.model->source().events.end(),[](const auto& event){return event.kind==music::Kind::Rest;});
            check(restEvent!=restVariant.model->source().events.end(),"retained representative bundle supplies a source-backed rest event for clearing verification");
            check(view.selectLesson(restLesson.id)&&view.selectedVariant()==restVariant.id,"switching the inspected source case retains its exact variant identity");
            click("mode");check(hint->isVisible()&&!viewport->isVisible(),"new source case starts with no selected event and hides prior markers");
            check(tab->selectEvent(restEvent->id),"TAB accepts the retained rest event identity");
            check(projection->markers().empty()&&projection->selectedEventId().empty()&&projection->statusSummary().find("not a note or chord")!=std::string::npos&&viewport->isVisible(),"rest selection explicitly refuses and clears the previous event markers");
            picture("learn-fretboard-rest-cleared");
            std::ofstream summaryFile(out/"summary.json");summaryFile<<"{\"checks\":"<<checks<<",\"item\":\""<<source.itemId<<"\",\"variant\":\"fg:variant:000006\",\"event\":\""<<sourceEvent->id<<"\",\"rest\":\""<<restEvent->id<<"\",\"markerCount\":"<<markerCount<<",\"practiceCalls\":"<<practiceCalls<<",\"nativeAudio\":false,\"profileAccess\":false,\"curriculumCredit\":false}\n";
            std::cout<<"PASS "<<checks<<" Learn fretboard selection checks\n";return 0;
        }
        if(firstAdmitted){
            view.setPresentation(desktop::presentation::Level::Developer,std::nullopt);
            int practiceCalls{};view.onPractice=[&](std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&){++practiceCalls;return false;};
            check(view.selectFirstAdmitted()&&view.selectedLesson()=="fg:item:000002"&&view.selectedVariant()=="fg:variant:000006","first-admitted helper selects the existing admitted source case without hard-coded fallback content");
            auto* practice=button("practice-selection");auto* summary=dynamic_cast<juce::Label*>(view.findChildWithID("summary"));
            check(practice&&practice->isEnabled()&&practice->getTitle().toStdString().find("Open admitted fg:item:000002 / fg:variant:000006 in Practice")!=std::string::npos&&summary&&summary->getText().toStdString().find("Runtime admission: admitted for Practice")!=std::string::npos,"first-admitted selection exposes the exact source-backed Practice action and admission status");
            const auto& source=view.catalog()->variant(view.selectedLesson(),view.selectedVariant()).model->source();
            check(source.sourceRefs==std::vector<std::string>{"L3-TXT5-21","L3-TXT28-46"}&&practiceCalls==0&&summary->getText().toStdString().find("no Attempt or curriculum credit")!=std::string::npos,"first-admitted selection preserves exact source refs and remains read-only without activity or credit");
            check(view.selectLesson("fg:item:000001")&&view.selectedVariant()=="fg:variant:000001"&&!practice->isEnabled()&&summary->getText().toStdString().find("Runtime admission refused")!=std::string::npos&&summary->getText().toStdString().find("no Practice or curriculum progress will be created")!=std::string::npos,"the retained refused source case remains explicitly selectable and refused");
            std::ofstream summaryFile(out/"summary.json");summaryFile<<"{\"checks\":"<<checks<<",\"selected\":\"fg:item:000002/fg:variant:000006\",\"refused\":\"fg:item:000001/fg:variant:000001\",\"practiceCalls\":"<<practiceCalls<<",\"nativeAudio\":false,\"curriculumCredit\":false}\n";std::cout<<"PASS "<<checks<<" Learn first-admitted checks\n";return 0;
        }
        auto search=dynamic_cast<juce::TextEditor*>(view.findChildWithID("lesson-search"));auto clearSearch=dynamic_cast<juce::TextButton*>(view.findChildWithID("lesson-search-clear"));auto searchStatus=dynamic_cast<juce::Label*>(view.findChildWithID("lesson-search-status"));check(search&&clearSearch&&searchStatus&&search->getTitle().toStdString().find("title")!=std::string::npos&&clearSearch->getButtonText().toStdString()=="Clear search"&&!clearSearch->isEnabled(),"Learn exposes source-backed search guidance and a disabled empty-query Clear search");
        check(searchStatus->getText().toStdString().find("Selection is read-only until explicit Practice.")!=std::string::npos,"Learn search status distinguishes browsing from explicit Practice entry");
        bool actionPresentation=true;int styledActions=0;for(const auto* id:{"lesson-search-clear","audio-settings","back","mode","details"}){auto* button=dynamic_cast<juce::TextButton*>(view.findChildWithID(id));actionPresentation=actionPresentation&&button&&button->findColour(juce::TextButton::buttonColourId)==juce::Colour{0xff6bd5cb}&&button->findColour(juce::TextButton::textColourOffId)==juce::Colour{0xff10212c}&&button->findColour(juce::TextButton::textColourOnId)==juce::Colour{0xff10212c};if(button)++styledActions;}
        for(const auto* label:{"Show setup details","Open metronome"}){auto* button=textButton(label);actionPresentation=actionPresentation&&button->findColour(juce::TextButton::buttonColourId)==juce::Colour{0xff6bd5cb}&&button->findColour(juce::TextButton::textColourOffId)==juce::Colour{0xff10212c}&&button->findColour(juce::TextButton::textColourOnId)==juce::Colour{0xff10212c};++styledActions;}
        check(actionPresentation&&styledActions==7,"Learn action buttons use the primary presentation while preserving the existing source-backed contract");
        auto setSearch=[&](const std::string& value){search->setText(juce::String::fromUTF8(value.c_str()),true);auto delivered=std::make_shared<bool>(false);juce::MessageManager::callAsync([delivered]{*delivered=true;});auto end=std::chrono::steady_clock::now()+std::chrono::seconds(2);while(!*delivered&&std::chrono::steady_clock::now()<end)CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);};
        if(practiceHandoffContract){
            auto* practice=button("practice-selection");auto* summary=dynamic_cast<juce::Label*>(view.findChildWithID("summary"));check(!practice->isEnabled()&&practice->getButtonText().toStdString()=="Practice selected case"&&summary&&summary->getText().toStdString().find("Runtime admission refused")!=std::string::npos&&summary->getText().toStdString().find("no Practice or curriculum progress will be created")!=std::string::npos,"refused initial case keeps Practice disabled and preserves the exact runtime/no-credit recovery");
            int practiceCalls{};view.onPractice=[&](std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&){++practiceCalls;return false;};combo("lessons")->setSelectedItemIndex(1,juce::sendNotificationSync);combo("variants")->setSelectedItemIndex(1,juce::sendNotificationSync);check(view.selectedLesson()=="fg:item:000002"&&view.selectedVariant()=="fg:variant:000006","handoff contract selects the retained admitted source case");check(practice->isEnabled()&&practice->getButtonText().toStdString()=="Practice selected case"&&practice->getTitle().toStdString()=="Open admitted fg:item:000002 / fg:variant:000006 in Practice: ModeA Exercise001 full selected directions | Variant: sixteenths-ascending-D-even | Source refs: L3-TXT5-21 L3-TXT28-46; explicit Practice Start creates the Attempt; no curriculum credit is inferred."&&practice->getExplicitFocusOrder()==6&&practice->getWantsKeyboardFocus(),"admitted Learn case exposes the source-backed Practice handoff title and stable control contract");const auto admittedSummary=summary->getText().toStdString();check(admittedSummary.find("Runtime admission: admitted for Practice")!=std::string::npos&&admittedSummary.find("Next action: read the authored instructions and TAB, then choose Practice selected case to enter Practice; selecting this case creates no Attempt or curriculum credit.")!=std::string::npos&&admittedSummary.find("Source case: fg:item:000002 / fg:variant:000006")!=std::string::npos,"admitted handoff retains the exact source-backed next action and no-credit boundary");check(practiceCalls==0,"handoff inspection does not invoke Practice before explicit user activation");std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"nativeAudio\":false,\"storeConfigured\":false,\"practiceStarted\":false,\"practiceCalls\":"<<practiceCalls<<"}\n";std::cout<<"PASS "<<checks<<" Learn Practice handoff contract checks\n";return 0;
        }
        const auto initialLesson=view.selectedLesson(),initialVariant=view.selectedVariant();const auto& searchableRecord=catalog->lesson("fg:item:000002").record.object();const auto workbook=searchableRecord.at("workbook_id").string();int workbookMatches{};for(const auto& lesson:catalog->lessons())if(lesson.record.object().at("workbook_id").string()==workbook)++workbookMatches;
        if(catalogSurface){
            bool learnHeading = false;
            for (auto* child : view.getChildren())
                if (auto* label = dynamic_cast<juce::Label*>(child); label && label->getText().toStdString() == "Learn — Source-backed Development Preview catalog") learnHeading = true;
            check(learnHeading,"Learn heading identifies the source-backed Development Preview catalog");
            auto inventory=dynamic_cast<juce::Label*>(view.findChildWithID("inventory"));
            check(searchStatus->getTitle().toStdString()=="Read-only Learn catalog search results, retained-case recovery and next action.","Learn search status exposes a stable truthful catalog title");
            check(inventory&&inventory->getTitle().toStdString()=="Read-only Development Preview catalog inventory and migration boundary.","Learn inventory exposes a stable truthful migration title");
            auto diagnostics=dynamic_cast<juce::TextEditor*>(view.findChildWithID("diagnostics"));
            check(diagnostics&&diagnostics->getText().toStdString().find("Loaded selected source-backed record")!=std::string::npos&&diagnostics->getText().toStdString().find("No source-task completion, Curriculum acceptance or progress is inferred.")!=std::string::npos,"Learn Details distinguishes loaded source-backed data from Curriculum acceptance and progress");
            check(inventory&&inventory->getText().toStdString()=="Case inspector. Reading does not start Practice.","Beginner inspector keeps catalog counts out of primary copy");
            view.setPresentation(desktop::presentation::Level::Advanced,std::nullopt);
            check(inventory->getText().contains("selected variant decides availability")&&!inventory->getDescription().contains("49 variants"),"Advanced inventory gives the variant boundary without technical counts");
            view.setPresentation(desktop::presentation::Level::Developer,std::nullopt);
            const auto inventoryText=inventory?inventory->getText().toStdString():std::string{};
            check(inventory&&inventory->isVisible()&&combo("lessons")->getNumItems()==13&&inventoryText.find("13 cases")!=std::string::npos&&inventoryText.find("49 variants")!=std::string::npos&&inventoryText.find("47 retained source entries")!=std::string::npos&&inventoryText.find("13 of 105 approved workbook identities represented")!=std::string::npos&&inventoryText.find("do not measure exercise engineering acceptance, whole-workbook completion or learner credit")!=std::string::npos,"Developer catalog counts name their retained preview denominator and exclude acceptance or credit");
            auto* searchLabel=dynamic_cast<juce::Label*>(view.findChildWithID("lesson-search-label"));
            check(inventory&&inventory->getHeight()>=68&&view.getLocalBounds().contains(inventory->getBounds())&&searchLabel&&inventory->getBottom()<=searchLabel->getY(),"Learn inventory reserves readable contained space above the search controls");
            check(searchStatus->getHeight()>=44&&view.getLocalBounds().contains(searchStatus->getBounds())&&searchStatus->getBottom()<=combo("lessons")->getY(),"Learn search recovery status reserves readable contained space above case selection");
            check(searchStatus->getText().toStdString().find("Search the retained 13-case catalog")!=std::string::npos,"Learn search status preserves exact empty-query guidance");
            setSearch("fg:item:000002");
            check(combo("lessons")->getNumItems()==1&&combo("lessons")->getItemText(0).toStdString().find("[fg:item:000002]")!=std::string::npos&&view.selectedLesson()==initialLesson&&view.selectedVariant()==initialVariant&&searchStatus->getText().toStdString().find("Current selection fg:item:000001 is outside this filter; no replacement was loaded.") != std::string::npos,"stable-ID filtering preserves the current source selection and exact recovery until explicit choice");
            int practiceCalls{},metronomeCalls{},audioCalls{};view.onPractice=[&](std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&){++practiceCalls;return false;};view.onMetronome=[&]{++metronomeCalls;};view.onAudioSettings=[&]{++audioCalls;};
            check(practiceCalls==0&&metronomeCalls==0&&audioCalls==0,"catalog status inspection creates no Practice, Audio or Metronome activity");
            std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"cases\":13,\"variants\":49,\"sourceEntries\":47,\"nativeAudio\":false,\"databaseAccess\":false,\"practiceCalls\":0}\n";std::cout<<"PASS "<<checks<<" Learn catalog status surface checks\n";return 0;
        }
        if(searchSmoke){
            int searchPracticeCalls=0;
            view.onPractice=[&](std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&){++searchPracticeCalls;return false;};
            view.refreshSetup();
            check(combo("lessons")->getNumItems()==13&&initialLesson=="fg:item:000001"&&initialVariant=="fg:variant:000001","search smoke starts with the retained refused source case and complete 13-case catalog");
            setSearch("fg:item:000002");check(combo("lessons")->getNumItems()==1&&combo("lessons")->getItemText(0).toStdString().find("[fg:item:000002]")!=std::string::npos&&view.selectedLesson()==initialLesson&&view.selectedVariant()==initialVariant,"stable-ID search filters actual case rows without replacing the current selection");
            combo("lessons")->setSelectedItemIndex(0,juce::sendNotificationSync);check(view.selectedLesson()=="fg:item:000002","filtered row selects the actual source-backed case");check(view.selectVariant("fg:variant:000006"),"explicitly select admitted variant for launch boundary check");const auto selectedSearchVariant=view.selectedVariant();const auto retainedAdmission=view.catalog()->admit(view.selectedLesson(),selectedSearchVariant);const auto retainedSourceBinding=retainedAdmission->sourceBinding();
            setSearch(workbook);check(combo("lessons")->getNumItems()==workbookMatches&&combo("lessons")->getItemText(0).toStdString().find(workbook)!=std::string::npos&&searchStatus->getText().toStdString().find("Choose a retained case to inspect its source/TAB; Clear Search restores all retained cases.")!=std::string::npos,"workbook search uses actual catalog provenance and matching-state next action");
            const auto sourceRef=searchableRecord.at("source_refs").array().front().string();setSearch(sourceRef);check(combo("lessons")->getItemText(0).toStdString().find("[fg:item:000002]")!=std::string::npos,"source-reference search uses retained source identity");
            setSearch("fg:item:000003");check(combo("lessons")->getNumItems()==1&&combo("lessons")->getItemText(0).toStdString().find("[fg:item:000003]")!=std::string::npos&&view.selectedLesson()=="fg:item:000002"&&view.selectedVariant()==selectedSearchVariant&&searchStatus->getText().toStdString().find("Current selection fg:item:000002 is outside this filter; no replacement was loaded.")!=std::string::npos,"filtered search preserves the hidden selection and gives matching-case or Clear Search recovery");
            check(!view.selectedCaseVisibleInSearch()&&!button("practice-selection")->isEnabled(),"hidden retained case cannot be launched from filtered results");
            view.practiceSelected();check(searchPracticeCalls==0,"direct Practice callback refuses hidden selection");
            picture("learn-outside-search");
            setSearch("not-a-retained-source-case");check(clearSearch->isEnabled()&&combo("lessons")->getNumItems()==0&&view.selectedLesson()=="fg:item:000002"&&view.selectedVariant()==selectedSearchVariant&&searchStatus->getText().toStdString().find("No source-backed lesson cases match")!=std::string::npos,"no-match search preserves the selected source case, enables Clear search and reports no fallback");
            view.practiceSelected();check(searchPracticeCalls==0&&!button("practice-selection")->isEnabled(),"no-match search refuses Practice without replacing source identity");
            click("lesson-search-clear");setSearch("");check(combo("lessons")->getNumItems()==13&&view.selectedLesson()=="fg:item:000002"&&view.selectedVariant()==selectedSearchVariant&&search->getText().isEmpty()&&!clearSearch->isEnabled()&&searchStatus->getText().toStdString().find("Search the retained 13-case catalog")!=std::string::npos,"Clear search restores the full retained catalog, exact selection and empty-query guidance");
            check(view.selectedCaseVisibleInSearch()&&button("practice-selection")->isEnabled(),"clearing search restores launch eligibility for the exact retained case");
            view.practiceSelected();check(searchPracticeCalls==1&&view.selectedLesson()=="fg:item:000002"&&view.selectedVariant()==selectedSearchVariant,"explicit Practice after restoration uses retained item and variant once");
            check(view.catalog()->admit(view.selectedLesson(),view.selectedVariant())->sourceBinding()==retainedSourceBinding,"filter and restore preserve exact source revision capability, not only display IDs");
            picture("learn-restored-search");
            const auto future=out/"future-source-revision";std::filesystem::create_directory(future);std::ofstream(future/"manifest.json")<<"{\"version\":\"unsupported-source-revision.fixture\"}";
            check(!view.load(future)&&!button("practice-selection")->isEnabled()&&!view.practiceSelected()&&searchPracticeCalls==1,"unaccepted source revision cannot silently reuse or launch the prior retained target");
            check(retainedAdmission->sourceBinding()==retainedSourceBinding,"previous immutable source capability survives refused publication unchanged");
            std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"nativeAudio\":false,\"humanReview\":false,\"databaseAccess\":false}\n";std::cout<<"PASS "<<checks<<" Learn search smoke checks\n";return 0;
        }
        if(selectionSurface){
            check(view.findChildWithID("summary")&&view.findChildWithID("summary")->getHeight()>=170,"Learn selected-case summary reserves readable space for the truthful source/admission and recovery facts");
            auto heading=dynamic_cast<juce::Label*>(view.findChildWithID("learn-selected-case-heading"));auto summary=dynamic_cast<juce::Label*>(view.findChildWithID("summary"));check(heading&&heading->isVisible()&&heading->getText().toStdString()=="SELECTED CASE"&&heading->getTitle().toStdString()=="Read-only selected Learn case heading","Learn exposes the visible SELECTED CASE heading");check(summary&&summary->isVisible()&&summary->getTitle().toStdString().find("source identity, runtime admission, next action and no-credit boundary")!=std::string::npos&&summary->getHeight()>=100,"selected-case summary exposes a truthful title and readable height");const auto summaryText=summary->getText().toStdString();check(heading->getBottom()<=summary->getY()&&summaryText.find("Source case: fg:item:000001 / fg:variant:000001")!=std::string::npos&&summaryText.find("Runtime admission refused")!=std::string::npos&&summaryText.find("no Practice or curriculum progress will be created")!=std::string::npos,"selected-case heading precedes the exact refused source-backed selection boundary");for(const char* id:{"lessons","variants","selected-tempo","practice-selection","audio-settings","practice-span","sections","mode","details","back"}){auto* child=view.findChildWithID(id);check(child&&child->getBoundsInParent().getBottom()<=view.getHeight(),"Learn selection surface keeps control in view "+std::string(id));}std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"nativeAudio\":false,\"humanReview\":false,\"databaseAccess\":false,\"storeConfigured\":false,\"practiceStarted\":false}\n";std::cout<<"PASS "<<checks<<" Learn selection surface checks\n";return 0;
        }
        setSearch("fg:item:000002");check(combo("lessons")->getNumItems()==1&&combo("lessons")->getItemText(0).toStdString().find("[fg:item:000002]")!=std::string::npos&&view.selectedLesson()==initialLesson&&view.selectedVariant()==initialVariant,"stable-ID search filters actual case rows without replacing the current selection");
        combo("lessons")->setSelectedItemIndex(0,juce::sendNotificationSync);check(view.selectedLesson()=="fg:item:000002","filtered row selects the actual source-backed case");const auto selectedSearchVariant=view.selectedVariant();
        setSearch(workbook);check(combo("lessons")->getNumItems()==workbookMatches&&combo("lessons")->getItemText(0).toStdString().find(workbook)!=std::string::npos&&searchStatus->getText().toStdString().find("Choose a retained case to inspect its source/TAB; Clear Search restores all retained cases.")!=std::string::npos,"workbook search uses actual catalog provenance and matching-state next action");
        const auto sourceRef=searchableRecord.at("source_refs").array().front().string();setSearch(sourceRef);check(combo("lessons")->getItemText(0).toStdString().find("[fg:item:000002]")!=std::string::npos,"source-reference search uses retained source identity");
        setSearch("fg:item:000003");check(combo("lessons")->getNumItems()==1&&combo("lessons")->getItemText(0).toStdString().find("[fg:item:000003]")!=std::string::npos&&view.selectedLesson()=="fg:item:000002"&&view.selectedVariant()==selectedSearchVariant&&searchStatus->getText().toStdString().find("Current selection fg:item:000002 is outside this filter; no replacement was loaded. Choose a matching retained case or Clear Search to restore the current selection.")!=std::string::npos,"filtered search preserves the hidden selection and gives matching-case or Clear Search recovery");
        setSearch("not-a-retained-source-case");check(clearSearch->isEnabled()&&combo("lessons")->getNumItems()==0&&view.selectedLesson()=="fg:item:000002"&&view.selectedVariant()==selectedSearchVariant&&searchStatus->getText().toStdString().find("No source-backed lesson cases match")!=std::string::npos,"no-match search preserves the selected source case, enables Clear search and reports no fallback");
        click("lesson-search-clear");setSearch("");check(combo("lessons")->getNumItems()==13&&view.selectedLesson()=="fg:item:000002"&&view.selectedVariant()==selectedSearchVariant&&search->getText().isEmpty()&&!clearSearch->isEnabled()&&searchStatus->getText().toStdString().find("Search the retained 13-case catalog")!=std::string::npos,"Clear search restores the full retained catalog, exact selection and empty-query guidance");combo("lessons")->setSelectedItemIndex(0,juce::sendNotificationSync);
        for(std::size_t i=0;i<catalog->lessons().size();++i){
            const auto label=combo("lessons")->getItemText(static_cast<int>(i)).toStdString();
            check(label.find("["+catalog->lessons()[i].id+"]")!=std::string::npos,
                  "catalog label retains exact stable item ID "+catalog->lessons()[i].id);
        }
        auto inventory=dynamic_cast<juce::Label*>(view.findChildWithID("inventory"));check(inventory&&inventory->isVisible(),"visible Development Preview inventory disclosure");
        view.setPresentation(desktop::presentation::Level::Developer,std::nullopt);
        const auto inventoryText=inventory->getText().toStdString();check(inventoryText.find("Retained Practice preview catalog: 13 cases")!=std::string::npos&&inventoryText.find("49 variants")!=std::string::npos&&inventoryText.find("47 retained source entries")!=std::string::npos,"Developer inventory reports the actual retained package counts");check(inventoryText.find("13 of 105 approved workbook identities represented")!=std::string::npos&&inventoryText.find("do not measure exercise engineering acceptance, whole-workbook completion or learner credit")!=std::string::npos,"Developer inventory distinguishes represented workbook identities from completion and credit");
        auto summary=dynamic_cast<juce::Label*>(view.findChildWithID("summary"));check(summary&&view.selectedLesson()=="fg:item:000001"&&!button("practice-selection")->isEnabled()&&summary->getText().toStdString().find("Selected variant unavailable for Practice. Runtime admission refused this selection; no Practice or curriculum progress will be created.")==0&&summary->getText().toStdString().find("Next action: choose another variant or case in Learn; this selection cannot enter Practice.")!=std::string::npos,"refused source case explains runtime admission, no-credit boundary and alternate-case recovery");
        const auto refusedSummary=summary->getText().toStdString();check(refusedSummary.find("Source case: fg:item:000001 / fg:variant:000001")!=std::string::npos&&refusedSummary.find("Source references: L1-TXT2-15")!=std::string::npos,"refused case shows exact stable source identity");
        auto metronome=textButton("Open metronome");auto audio=button("audio-settings");const auto handoffLesson=view.selectedLesson(),handoffVariant=view.selectedVariant();int metronomeCallbacks=0,audioCallbacks=0;check(metronome->isEnabled()&&audio->isEnabled(),"Learn keeps Metronome and shared Audio recovery controls actionable without host callbacks");check(!view.requestMetronome()&&metronomeCallbacks==0&&view.selectedLesson()==handoffLesson&&view.selectedVariant()==handoffVariant&&summary->getText().toStdString()=="Metronome is unavailable from Learn until the existing Metronome page is connected. Return to Home and choose Metronome; no sound or practice activity was started.","missing Learn Metronome callback gives exact recovery without mutation or sound");check(!view.requestAudioSettings()&&audioCallbacks==0&&view.selectedLesson()==handoffLesson&&view.selectedVariant()==handoffVariant&&summary->getText().toStdString()=="Audio settings are unavailable from Learn until the existing shared Audio page is connected. Return to Home and choose Audio settings; no sound or practice activity was started.","missing Learn Audio callback gives exact recovery without mutation or sound");view.onMetronome=[&]{++metronomeCallbacks;};view.onAudioSettings=[&]{++audioCallbacks;};view.refreshSetup();check(view.requestMetronome()&&metronomeCallbacks==1&&view.requestAudioSettings()&&audioCallbacks==1&&view.selectedLesson()==handoffLesson&&view.selectedVariant()==handoffVariant,"connected Learn Metronome and Audio callbacks route exactly once and retain selection");
        for(std::size_t i=0;i<catalog->lessons().size();++i){const auto& l=catalog->lessons()[i];combo("lessons")->setSelectedItemIndex(static_cast<int>(i),juce::sendNotificationSync);check(view.selectedLesson()==l.id,"actual case selection "+l.id);check(combo("variants")->getNumItems()==static_cast<int>(l.variants.size()),"variant coverage "+l.id);
            for(std::size_t variantIndex=0;variantIndex<l.variants.size();++variantIndex){
                const auto label=combo("variants")->getItemText(static_cast<int>(variantIndex)).toStdString();
                const auto& sourceRefs=l.variants[variantIndex].model->source().sourceRefs;
                std::string expected=l.variants[variantIndex].label+" ["+l.variants[variantIndex].id+"]";
                if(!sourceRefs.empty()){
                    expected+=" | Source: ";
                    for(std::size_t ref=0;ref<sourceRefs.size();++ref){if(ref!=0)expected+=" ";expected+=sourceRefs[ref];}
                }
                check(label.find(expected)!=std::string::npos,
                      "variant label retains authored label, stable ID and source refs "+l.variants[variantIndex].id);
            }
            combo("sections")->setSelectedId(1,juce::sendNotificationSync);check(editor->getText().toStdString()==catalog->text(l.id,view.selectedVariant(),lesson::Section::Instructions),"exact actual instruction text "+l.id);
            for(int width:{920,1280}){view.setSize(width,width==920?680:800);picture("L"+std::to_string(l.level)+"-source-"+std::to_string(width));}
            if(l.level==15){
                view.setSize(920,680);const auto staff=editor->getText().indexOf("Deg|1--2--3--|");const auto end=editor->getText().indexOf(staff,"\n");check(staff>=0&&end>staff,"wide authored TAB exists");
                const auto startRect=editor->getCaretRectangleForCharIndex(staff),endRect=editor->getCaretRectangleForCharIndex(end-1);
                check(startRect.getY()==endRect.getY()&&endRect.getX()>editor->getWidth(),"source staff remains one aligned unwrapped row");
                juce::Viewport* port=nullptr;for(auto* child:editor->getChildren())if(auto* found=dynamic_cast<juce::Viewport*>(child))port=found;
                check(port!=nullptr,"actual editor scroll viewport exists");port->setViewPosition(0,port->getViewPositionY()+startRect.getY()-60);picture("L15-wide-source-left");
                port->setViewPosition(editor->getTextWidth()-port->getViewWidth()+20,port->getViewPositionY());check(port->getViewPositionX()>0,"actual source horizontal scroll reaches right");picture("L15-wide-source-right");
            }
            for(int section:{2,3,4,5}){combo("sections")->setSelectedId(section,juce::sendNotificationSync);check(editor->getText().toStdString()==catalog->text(l.id,view.selectedVariant(),static_cast<lesson::Section>(section-1)),"actual section "+l.id+"/"+std::to_string(section));}
            if(l.level==48||l.level==83||l.level==97||l.level==105){for(int s:{2,3,4}){combo("sections")->setSelectedId(s,juce::sendNotificationSync);view.setSize(920,680);picture("L"+std::to_string(l.level)+"-section"+std::to_string(s));}}
            if(l.variants.front().model->source().events.empty())check(!button("mode")->isEnabled(),"non-TAB task refuses fabricated staff "+l.id);
            else{click("mode");check(tab->isVisible()&&tab->document()->source().itemId==l.id,"TAB same selected source "+l.id);view.setSize(920,680);picture("L"+std::to_string(l.level)+"-tab");click("mode");check(editor->isVisible(),"instruction return "+l.id);}
        }
        combo("lessons")->setSelectedItemIndex(1,juce::sendNotificationSync);combo("variants")->setSelectedItemIndex(1,juce::sendNotificationSync);
        const auto admittedPracticeSummary=summary->getText().toStdString();check(admittedPracticeSummary.find("Source case: fg:item:000002 / fg:variant:000006")!=std::string::npos&&admittedPracticeSummary.find("Next action: read the authored instructions and TAB, then choose Practice selected case to enter Practice; selecting this case creates no Attempt or curriculum credit.")!=std::string::npos,"admitted Learn case exposes the authored-instructions/TAB to Practice next action without creating an Attempt");
        auto spans=combo("practice-span");spans->setSelectedId(2,juce::sendNotificationSync);
        const auto admittedCellSummary=summary->getText().toStdString();check(admittedCellSummary.find("This cell is not a full direction or source task. Practice Start is explicit; selecting it creates no Attempt or curriculum credit. Follow the unchanged source guidance below.")!=std::string::npos,"selected Learn source cell states explicit Practice Start and no Attempt/no-credit boundary");
        const auto admittedSummary=summary->getText().toStdString();check(admittedSummary.find("Source case: fg:item:000002 / fg:variant:000006")!=std::string::npos&&admittedSummary.find("Source references: L3-TXT5-21 L3-TXT28-46")!=std::string::npos,"admitted case shows exact stable source identity");
        check(combo("variants")->getItemText(1).toStdString().find("| Source: L3-TXT5-21 L3-TXT28-46 | Content: representative-controls.1 | Revision: 2")!=std::string::npos,"selected Learn variant row shows exact loaded content provenance");
        const auto& selectedSource=tab->document()->source();const auto& catalogSource=catalog->variant(view.selectedLesson(),view.selectedVariant()).model->source();const bool sameIdentity=selectedSource.itemId==catalogSource.itemId&&selectedSource.sourceRefs==catalogSource.sourceRefs;check(view.selectedLesson()=="fg:item:000002"&&view.selectedVariant()=="fg:variant:000006"&&sameIdentity,"actual nonfirst ComboBox variant and exact shared source identity");auto doc=tab->document();check(!view.selectVariant("fg:variant:000049")&&view.selectedVariant()=="fg:variant:000006"&&tab->document()==doc,"cross-owner selection refuses without substitute");check(!view.selectLesson("missing")&&view.selectedLesson()=="fg:item:000002","missing lesson retains current selection");
        bool returned=false;view.onBack=[&]{returned=true;};click("back");check(returned,"actual Back dispatch");
        check(!view.load(out/"absent-bundle")&&!view.catalog()&&view.selectedLesson().empty()&&!tab->document(),"failed reload clears old catalog, no silent fallback");check(!inventory->isVisible()&&inventory->getText().isEmpty(),"load error makes no successful inventory claim");check(!combo("lessons")->isEnabled()&&button("back")->isEnabled(),"load error keeps Back with no selectable sample");check(summary->getText().toStdString().find("bundled representative lesson resources")!=std::string::npos&&summary->getText().toStdString().find("complete local lesson resources")==std::string::npos,"load error names the bounded representative bundle without claiming completeness");click("details");picture("missing-bundle-details");
        std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"nativeAudio\":false,\"humanReview\":false,\"databaseAccess\":false}\n";std::cout<<"PASS "<<checks<<" lesson component checks\n";return 0;
    }catch(const std::exception& ex){std::cerr<<"FAIL after "<<checks<<": "<<ex.what()<<'\n';return 1;}
}
