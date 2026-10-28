#include "desktop/ReadOnlyTextEditor.hpp"
#include "desktop/TypedManualForm.hpp"
#include "desktop/ManualTaskView.hpp"
#include "desktop/EarSourceProcedureView.hpp"
#include "desktop/C43SourceProcedureView.hpp"
#include "desktop/ReadOnlyTextView.hpp"
#include "content/Canonical.hpp"
#include "tasks/InstalledManualTaskRegistry.hpp"
#include <array>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <functional>
#include <iostream>
#include <stdexcept>
#if JUCE_MAC
#include <ApplicationServices/ApplicationServices.h>
#include <unistd.h>
#endif

using namespace fathom;
using V=json::Value;using O=V::Object;using A=V::Array;
namespace {
std::size_t checks{};
void check(bool condition,const char* reason){++checks;if(!condition)throw std::runtime_error(reason);}
juce::Component* find(juce::Component& parent,const juce::String& id){
    if(parent.getComponentID()==id)return &parent;
    for(int n=0;n<parent.getNumChildComponents();++n)if(auto* child=find(*parent.getChildComponent(n),id))return child;
    return nullptr;
}
template<class T>T& control(juce::Component& parent,const char* id){
    auto* result=dynamic_cast<T*>(find(parent,id));check(result!=nullptr,"Required visible control missing");return *result;
}
template<class T>T* descendant(juce::Component& parent){
    for(int n=0;n<parent.getNumChildComponents();++n){
        auto& child=*parent.getChildComponent(n);
        if(auto* result=dynamic_cast<T*>(&child))return result;
        if(auto* result=descendant<T>(child))return result;
    }
    return nullptr;
}
juce::Viewport& instructionViewport(juce::TextEditor& editor){
    auto* viewport=descendant<juce::Viewport>(editor);
    check(viewport!=nullptr,"Instruction editor must contain its real scrolling viewport");
    return *viewport;
}
bool peerKey(juce::Component& root,juce::TextEditor& editor,const juce::KeyPress& key){
    check(root.getPeer()!=nullptr&&juce::Component::getCurrentlyFocusedComponent()==&editor,
          "Peer key requires real editor focus, independent of AX focus reporting");
    const bool handled=root.getPeer()->handleKeyPress(key);
    // The pinned JUCE line-scroll methods notify their viewport asynchronously.
    // Deliver that existing notification; do not set a viewport position here.
    instructionViewport(editor).getVerticalScrollBar().handleUpdateNowIfNeeded();
    check(juce::Component::getCurrentlyFocusedComponent()==&editor,"Reading key changed actual keyboard focus");
    return handled;
}
void readingKeys(juce::Component& root,juce::TextEditor& editor,const juce::String& expected){
    using Key=juce::KeyPress;
    auto& viewport=instructionViewport(editor);
    check(editor.isReadOnly()&&editor.getText()==expected,"Keyboard fixture must retain original read-only text");
    check(editor.getTextHeight()>viewport.getViewHeight(),"Keyboard fixture must contain actually clipped prose");
    const auto originalBytes=editor.getText().toStdString();
    const auto press=[&](int code){
        check(peerKey(root,editor,Key(code)),"Read-only navigation key must be handled through the peer");
        check(editor.isReadOnly()&&editor.getText().toStdString()==originalBytes,"Navigation changed original instruction bytes or read-only state");
    };
    const auto edgeVisible=[&](int index){
        const auto caret=editor.getCaretRectangleForCharIndex(index);
        const auto area=editor.getLocalArea(&viewport,viewport.getLocalBounds());
        return caret.getY()>=area.getY()&&caret.getBottom()<=area.getBottom();
    };
    press(Key::endKey);const auto end=viewport.getViewPositionY();
    check(end>0&&editor.getCaretPosition()==editor.getTotalNumChars()&&edgeVisible(editor.getTotalNumChars()),"End must reveal the original final line");
    press(Key::upKey);const auto beforeRepeatedEnd=viewport.getViewPositionY();
    check(beforeRepeatedEnd<end,"Up must scroll clipped prose toward its beginning");
    press(Key::endKey);
    check(viewport.getViewPositionY()>beforeRepeatedEnd&&edgeVisible(editor.getTotalNumChars()),"Repeated End must reveal the final line even when the caret was already at the end");
    const auto beforePageUp=viewport.getViewPositionY();press(Key::pageUpKey);
    check(viewport.getViewPositionY()<beforePageUp,"Page Up must move the actual instruction viewport");
    press(Key::homeKey);const auto top=viewport.getViewPositionY();
    check(editor.getCaretPosition()==0&&edgeVisible(0),"Home must reveal the original first line");
    press(Key::downKey);
    check(viewport.getViewPositionY()>top,"Down must scroll clipped prose toward its end");
    press(Key::homeKey);
    check(viewport.getViewPositionY()<=top&&edgeVisible(0),"Repeated Home must reveal the first line even when the caret was already at the beginning");
    const auto beforePageDown=viewport.getViewPositionY();press(Key::pageDownKey);
    check(viewport.getViewPositionY()>beforePageDown,"Page Down must move the actual instruction viewport");
    check(peerKey(root,editor,Key('a',juce::ModifierKeys::commandModifier,0)),"JUCE Select All dispatch must remain available");
    check(editor.getHighlightedRegion()==juce::Range<int>{0,editor.getTotalNumChars()},"Select All must retain the full permitted text selection");
    for(const auto& key:std::array<Key,3>{{Key(Key::backspaceKey),Key(Key::deleteKey),Key('x',juce::ModifierKeys::noModifiers,'x')}}){
        (void)peerKey(root,editor,key);
        check(editor.isReadOnly()&&editor.getText().toStdString()==originalBytes,"Delete, Backspace or a character changed selected read-only instructions");
    }
    press(Key::homeKey);
}
void editableFallback(){
    desktop::ReadOnlyTextEditor editor;juce::TextEditor vanilla;
    for(auto* control:std::array<juce::TextEditor*,2>{{&editor,&vanilla}}){
        control->setMultiLine(true,true);control->setReadOnly(false);
        control->setText("first\nsecond",false);control->setCaretPosition(9);
    }
    const auto sameAsJuce=[&](const juce::KeyPress& key,const char* reason){
        const bool handled=editor.keyPressed(key);const bool referenceHandled=vanilla.keyPressed(key);
        check(handled==referenceHandled&&editor.getText()==vanilla.getText()
              &&editor.getCaretPosition()==vanilla.getCaretPosition()
              &&editor.getHighlightedRegion()==vanilla.getHighlightedRegion()
              &&editor.isReadOnly()==vanilla.isReadOnly(),reason);
    };
    sameAsJuce(juce::KeyPress(juce::KeyPress::homeKey),"Editable Home must match the pinned JUCE editor on this platform");
    sameAsJuce(juce::KeyPress('x',juce::ModifierKeys::noModifiers,'x'),"Editable character dispatch must match JUCE insertion");
    sameAsJuce(juce::KeyPress(juce::KeyPress::backspaceKey),"Editable Backspace must match JUCE deletion");
    sameAsJuce(juce::KeyPress(juce::KeyPress::deleteKey),"Editable Delete must match JUCE deletion");
}
// JUCE only exposes getAccessibilityHandler() while a component has a native
// window handle. Root serializes these finite component peers under its GUI
// lease; no audio, learner action or application campaign is started here.
class NativePeerScope final {
public:
    explicit NativePeerScope(juce::Component& component):component_(component){
        component_.addToDesktop(juce::ComponentPeer::windowHasTitleBar);
        component_.setVisible(true);
        check(component_.getPeer()!=nullptr&&component_.getWindowHandle()!=nullptr&&component_.isShowing(),"Native component peer is required before AX assertions");
    }
    ~NativePeerScope(){component_.setVisible(false);component_.removeFromDesktop();}
    NativePeerScope(const NativePeerScope&)=delete;
    NativePeerScope& operator=(const NativePeerScope&)=delete;
private:
    juce::Component& component_;
};
void accessibleText(juce::TextEditor& editor,const juce::String& expected,const juce::String& expectedTitle="Instructions"){
    check(editor.isReadOnly()&&editor.isVisible()&&editor.getWidth()>0&&editor.getHeight()>0,"Instructions must have a visible read-only region");
    check(editor.getText()==expected&&editor.getDescription()==expected,"Permitted instruction bytes must remain complete");
    check(editor.getTitle()==expectedTitle,"Instruction component title differs from the named contract");
    check(editor.getWindowHandle()!=nullptr&&editor.isAccessible(),"Instruction AX must have an accessible native peer");
    auto* handler=editor.getAccessibilityHandler();check(handler!=nullptr,"Native instruction accessibility handler missing despite its peer");
    check(handler->getTitle()==expectedTitle&&handler->getRole()==juce::AccessibilityRole::staticText,"Instruction AX name or static-text role differs from the named contract");
    check(handler->getDescription()==expected,"Full permitted instruction AX description missing");
    check(handler->getHelp()==expected,"Full permitted instruction help missing");
    auto* text=handler->getTextInterface();check(text!=nullptr,"Native instruction text interface missing");
    check(text->isReadOnly()&&text->getText({0,text->getTotalNumCharacters()})==expected,"Native AX text must retain the complete permitted instructions");
}
void formReadability(){
    desktop::TypedManualForm form;bool current=true;
    const auto longLabel=std::string(24,' ') + "A long source-bound prompt with an explicit unknown choice; preserve every word while wrapping into the report field viewport. " + std::string(160,'x');
    const V schema=O{{"type","object"},{"properties",O{
        {"report",O{{"type",A{"string","null"}},{"label",longLabel},{"minLength",V::fromInteger(1)}}},
        {"source",O{{"const",longLabel},{"literal_binding_label","source_protocol_binding"}}}
    }},{"required",A{"report","source"}},{"additionalProperties",false}};
    const std::vector<std::string> lines{
        "Permitted instructions only. Keep the full original order and report what you actually did.",
        std::string(1400,'a')+" Final permitted instruction; no source answer was invented."
    };
    std::string joined;for(const auto& line:lines)joined+=line+"\n\n";
    form.setSize(920,400);form.configure(schema,lines,[&]{return current;});
    NativePeerScope peer(form);
    auto& input=control<juce::TextEditor>(form,"typed-field-input/report");
    auto& unknown=control<juce::ToggleButton>(form,"typed-unknown-input/report");
    input.setText("My exact report",false);unknown.setToggleState(true,juce::dontSendNotification);
    const auto generation=form.formGeneration();const auto layouts=form.instructionLayoutCount();
    const std::array<juce::Point<int>,4> sizes{{{440,280},{920,400},{1400,600},{1100,320}}};
    for(const auto size:sizes){
        form.setSize(size.x,size.y);accessibleText(control<juce::TextEditor>(form,"typed-instructions"),joined);
        check(form.formGeneration()==generation&&form.instructionLayoutCount()==layouts,"Resize cannot reconfigure the native form or rewrite instructions");
        check(input.getText()=="My exact report"&&unknown.getToggleState(),"Resize changed an explicit report/Unknown choice");
        check(form.read().object().at("report").null(),"Unknown must retain null instead of a default response");
        auto& label=control<juce::Label>(form,"typed-label-input/source");
        check(label.getTooltip()==label.getText(),"Long source binding must retain its complete accessible text");
        if(size.x==440)check(label.getHeight()>42,"Long source binding must allocate more lines at narrow width");
        auto& fields=control<juce::Viewport>(form,"typed-viewport");
        check(fields.getHeight()>0&&fields.getViewedComponent()->getHeight()>=fields.getHeight(),"All report fields must remain scroll-reachable");
    }
    form.setSize(920,400);
    auto& instructions=control<juce::TextEditor>(form,"typed-instructions");instructions.grabKeyboardFocus();
    readingKeys(form,instructions,joined);accessibleText(instructions,joined);
    check(form.formGeneration()==generation&&form.instructionLayoutCount()==layouts,"Reading keys cannot regenerate a report form or rewrite its instructions");
    check(input.getText()=="My exact report"&&unknown.getToggleState()&&form.read().object().at("report").null(),"Reading keys changed an explicit report or Unknown choice");
    check(dynamic_cast<desktop::ReadOnlyTextEditor*>(&input)==nullptr&&!input.isReadOnly(),"Editable report fields must retain their original editor type");
    input.grabKeyboardFocus();input.moveCaretToEnd();
    check(peerKey(form,input,juce::KeyPress('x',juce::ModifierKeys::noModifiers,'x'))&&input.getText()=="My exact reportx","Editable report character dispatch must remain available");
    check(peerKey(form,input,juce::KeyPress(juce::KeyPress::backspaceKey))&&input.getText()=="My exact report","Editable report Backspace must remain available");
    current=false;bool refused=false;try{(void)form.read();}catch(const std::exception&){refused=true;}
    check(refused,"Readability cannot bypass a stale native owner");
    const auto debt=desktop::manual_text::releaseGuidance(true,true);
    check(debt.find("Release your instrument")!=std::string::npos&&debt.find("Stop the external sound source")!=std::string::npos,"Both required physical/source actions must remain explicit");
}
void manualDisclosure(const char* resource){
    auto registry=tasks::InstalledManualTaskRegistry::load(resource);
    auto definition=registry.definition("level053/moduleb/p003-t1-r1-c2/cmajrp");check(bool(definition),"Required retained manual fixture missing");
    desktop::ManualTaskView view;view.setSize(920,680);check(view.open(*definition),"Manual fixture must open through its normal registry");
    NativePeerScope peer(view);
    auto& instructions=control<juce::TextEditor>(view,"manual-task-setup");const auto original=instructions.getText();
    auto& bpm=control<juce::TextEditor>(view,"manual-task-bpm");bpm.setText("64",false);
    const auto phase=view.adapter()->view().phase;const auto history=view.adapter()->history().size();
    const std::array<desktop::presentation::Level,3> levels{{desktop::presentation::Level::Beginner,desktop::presentation::Level::Advanced,desktop::presentation::Level::Developer}};
    for(const auto level:levels){
        view.setPresentationLevel(level);view.setSize(1100,680);accessibleText(instructions,original,"Instructions: read before Ready");
        check(view.adapter()->view().phase==phase&&view.adapter()->history().size()==history,"Disclosure changed native phase/history");
        check(!view.clockActive()&&!view.pulsePreparing()&&bpm.getText()=="64","Disclosure changed pace/input or prepared sound");
        const auto shown=control<juce::Label>(view,"manual-task-source").getText();
        check(shown.contains(juce::String{definition->sourceKey()})==(level==desktop::presentation::Level::Developer),"Only Developer primary text should add the diagnostic source key");
    }
    check(!control<juce::Label>(view,"manual-task-setup-accessible").isAccessible(),"Clipped duplicate instruction mirror must not replace native accessible text");
}
void originalManualKeyboard(const char* resource){
    auto registry=tasks::InstalledManualTaskRegistry::load(resource);
    auto definition=registry.definition("level053/moduleb/p004-t1-r5-c7/gmin2nd");
    check(bool(definition),"Exact populated long original manual fixture missing");
    std::string original;
    for(const auto& line:definition->setupInstructions())original+=line+'\n';
    original+='\n';for(const auto& line:definition->retainedSourceContext())original+=line+'\n';
    original+='\n';original+=definition->pacedChoiceExplanation();
    const auto expected=juce::String::fromUTF8(original.c_str());
    check(expected.length()==1823,"Exact selected original manual body must retain its reviewed length");
    {
    desktop::ManualTaskView view;view.setSize(920,680);check(view.open(*definition),"Original manual fixture must open through its normal registry");
    NativePeerScope peer(view);
    auto& instructions=control<juce::TextEditor>(view,"manual-task-setup");
    auto& bpm=control<juce::TextEditor>(view,"manual-task-bpm");bpm.setText("64",false);
    const auto phase=view.adapter()->view().phase;const auto history=view.adapter()->history().size();
    bpm.grabKeyboardFocus();check(juce::Component::getCurrentlyFocusedComponent()==&bpm,"Manual focus must actually begin in editable BPM");
    check(view.getPeer()->handleKeyPress(juce::KeyPress(juce::KeyPress::tabKey)),"Native peer must deliver Tab from BPM");
    check(juce::Component::getCurrentlyFocusedComponent()==&instructions&&instructions.hasKeyboardFocus(false),
          "BPM Tab must reach the original instruction editor; AX focus metadata is not keyboard focus proof");
    readingKeys(view,instructions,expected);accessibleText(instructions,expected,"Instructions: read before Ready");
    check(view.adapter()->view().phase==phase&&view.adapter()->history().size()==history,"Reading keys changed native manual phase or history");
    check(!view.clockActive()&&!view.pulsePreparing()&&bpm.getText()=="64","Reading keys changed tempo or prepared a pulse");
    for(int n=0;n<6;++n)check(control<juce::TextEditor>(view,("manual-task-report-"+std::to_string(n)).c_str()).getText().isEmpty(),"Reading keys supplied a manual report");
    check(view.getPeer()->handleKeyPress(juce::KeyPress(juce::KeyPress::tabKey,juce::ModifierKeys::shiftModifier,0))
          &&juce::Component::getCurrentlyFocusedComponent()==&bpm,"Shift-Tab must return from the instruction body to editable BPM");
    check(dynamic_cast<desktop::ReadOnlyTextEditor*>(&bpm)==nullptr&&!bpm.isReadOnly(),"Editable BPM must retain its original editor type");
    bpm.moveCaretToEnd();
    check(peerKey(view,bpm,juce::KeyPress('7',juce::ModifierKeys::noModifiers,'7'))&&bpm.getText()=="647","Editable BPM character dispatch must remain available");
    check(peerKey(view,bpm,juce::KeyPress(juce::KeyPress::backspaceKey))&&bpm.getText()=="64","Editable BPM Backspace must remain available");
    check(view.adapter()->view().phase==phase&&view.adapter()->history().size()==history&&!view.clockActive()&&!view.pulsePreparing(),"Keyboard inspection must not apply a pace or perform a task step");
    }

    desktop::ReadOnlyTextView label;label.setSize(440,160);label.setText(expected,juce::dontSendNotification);
    NativePeerScope labelPeer(label);auto* body=descendant<juce::TextEditor>(label);
    check(body!=nullptr,"Shared read-only Label must expose its instruction editor");body->grabKeyboardFocus();
    readingKeys(label,*body,expected);
    // AppKit exposes the Label-compatible wrapper as the focused AX static
    // text. Prove that peer-delivered reading keys on that exact target reach
    // the embedded editor instead of merely returning API success.
    auto& viewport=instructionViewport(*body);body->moveCaretToTop(false);
    viewport.getVerticalScrollBar().handleUpdateNowIfNeeded();
    label.grabKeyboardFocus();
    check(juce::Component::getCurrentlyFocusedComponent()==&label,"Shared read-only wrapper must take native keyboard focus");
    check(label.getPeer()->handleKeyPress(juce::KeyPress(juce::KeyPress::endKey)),"Wrapper-focused End must be handled through the native peer");
    viewport.getVerticalScrollBar().handleUpdateNowIfNeeded();
    check(viewport.getViewPositionY()>0&&body->getCaretPosition()==body->getTotalNumChars(),"Wrapper-focused End must reveal the original final line");
    check(label.getText()==expected&&body->getText().toStdString()==original,"Shared read-only Label navigation changed its original text");
}
void populatedEarKeyboard(const char* resource){
    const auto root=std::filesystem::path{resource}.parent_path();
    const auto package=tasks::ear234::package::ClosedPackage::load(
        content::readBounded(root/"compiled-manual-families-v1/ear234/closed-package.json",512*1024),
        content::readBounded(root/"learn-source-index/exercises.jsonl",32*1024*1024));
    const std::string key="exercise-completeness-r01/level076/moduleg/p013-u001/moduleglayeredsixteenbartranscriptionlab";
    const std::string identity="level076/moduleg/p013-u001/moduleglayeredsixteenbartranscriptionlab";
    check(package.learnerInstruction(key,identity)==
          "External once-recorded/partner16-bar source; seven full16-bar worksheet layers in order, four confidence0-2 per layer. Zero-confidence blocks first for re-listen. Reference only after worksheet; scores and verification separate. Classify faulty layer/block, correct ONLY it, invalidate affected score, replay COMPLETE block before another repair.",
          "Exact populated Ear closed-package instruction differs");

    desktop::EarSourceProcedureView view;view.setSize(920,680);
    check(view.open(package,key,identity),"Exact populated Ear source owner did not open");
    check(view.retainedOwnerCount()==1&&view.retainedHistoryCount()==0,"Opening exact Ear source must not invent an action");
    const auto initialState=view.learnerView();
    NativePeerScope peer(view);
    auto& instructions=control<juce::TextEditor>(view,"typed-instructions");
    const auto original=instructions.getText().toStdString();
    check(original.size()==637&&content::sha256(original)=="2d17ff23d1df4e92bdad5fd08958c19d99852cfe45f750303ae7fc0418ebcb5f",
          "Exact populated Ear instruction body differs");
    accessibleText(instructions,instructions.getText());

    const auto unchanged=[&]{
        check(instructions.isReadOnly()&&instructions.getText().toStdString()==original,"Ear reading changed the exact instruction body");
        check(view.retainedOwnerCount()==1&&view.retainedHistoryCount()==0&&view.learnerView()==initialState,
              "Ear reading changed retained owner, history or learner state");
    };
    const auto sequence=[&]{
        using Key=juce::KeyPress;
        auto& viewport=instructionViewport(instructions);
        const auto beginningVisible=[&]{
            const auto caret=instructions.getCaretRectangleForCharIndex(0);
            const auto visible=instructions.getLocalArea(&viewport,viewport.getLocalBounds());
            const auto viewY=viewport.getViewPositionY();
            // Pinned JUCE includes the editor's configured top indent in the
            // first caret's content position. A Home from below aligns that
            // caret at the viewport top; an already-top Home preserves the
            // leading indent. Both positions expose the complete first line.
            const auto firstCaretInset=caret.getY()-visible.getY()+viewY;
            check(firstCaretInset==instructions.getTopIndent(),"Populated Ear first-caret inset differs from the configured JUCE top indent");
            return instructions.getCaretPosition()==0&&viewY>=0&&viewY<=firstCaretInset
                &&caret.getY()>=visible.getY()&&caret.getBottom()<=visible.getBottom();
        };
        const Key home(Key::homeKey,juce::ModifierKeys::noModifiers,0);
        instructions.grabKeyboardFocus();
        check(juce::Component::getCurrentlyFocusedComponent()==&instructions&&instructions.hasKeyboardFocus(false),
              "Populated Ear sequence requires actual JUCE instruction focus");
        check(peerKey(view,instructions,home),"Populated Ear Home was not handled through the peer");
        const auto top=viewport.getViewPositionY();
        check(beginningVisible(),"Populated Ear Home did not reveal the complete first line within the configured JUCE inset");
        unchanged();
        check(peerKey(view,instructions,Key(Key::endKey)),"Populated Ear End was not handled through the peer");
        const auto bottom=viewport.getViewPositionY();
        check(instructions.getCaretPosition()==instructions.getTotalNumChars()&&bottom>top,"Populated Ear End did not reveal the ending");
        unchanged();
        check(peerKey(view,instructions,home),"Populated Ear repeated Home was not handled through the peer");
        check(beginningVisible(),"Populated Ear repeated Home did not reveal the complete first line within the configured JUCE inset");
        unchanged();
        const auto beforePageDown=viewport.getViewPositionY();
        check(peerKey(view,instructions,Key(Key::pageDownKey)),"Populated Ear Page Down was not handled through the peer");
        check(viewport.getViewPositionY()>beforePageDown,"Populated Ear Page Down did not move the instruction viewport");
        unchanged();
    };
    sequence();
    view.resumeAfterNavigation();
    check(&control<juce::TextEditor>(view,"typed-instructions")==&instructions,"Ear re-entry replaced the retained instruction component");
    unchanged();
    sequence();
}
#if JUCE_MAC
void requireSelfPostInputBoundary(){
    check(CGPreflightPostEventAccess(),"SELF_POST_PERMISSION_UNAVAILABLE: existing native event-post access is required; this pilot never prompts or changes trust settings");
    const auto flags=CGEventSourceFlagsState(kCGEventSourceStateCombinedSessionState);
    const auto forbidden=kCGEventFlagMaskShift|kCGEventFlagMaskControl|kCGEventFlagMaskAlternate
                        |kCGEventFlagMaskCommand|kCGEventFlagMaskSecondaryFn;
    check((flags&forbidden)==0,"SELF_POST_INPUT_BUSY: a shortcut modifier is held; no key was posted");
    check(!CGEventSourceButtonState(kCGEventSourceStateCombinedSessionState,kCGMouseButtonLeft)
          &&!CGEventSourceButtonState(kCGEventSourceStateCombinedSessionState,kCGMouseButtonRight)
          &&!CGEventSourceButtonState(kCGEventSourceStateCombinedSessionState,kCGMouseButtonCenter),
          "SELF_POST_INPUT_BUSY: a pointer button is held; no key was posted");
}
void postNavigationKeyToSelf(CGKeyCode virtualKey,UniChar appKitCodepoint){
    requireSelfPostInputBoundary();
    auto* source=CGEventSourceCreate(kCGEventSourceStatePrivate);
    auto* down=source==nullptr?nullptr:CGEventCreateKeyboardEvent(source,virtualKey,true);
    auto* up=source==nullptr?nullptr:CGEventCreateKeyboardEvent(source,virtualKey,false);
    if(source==nullptr||down==nullptr||up==nullptr){
        if(down!=nullptr)CFRelease(down);
        if(up!=nullptr)CFRelease(up);
        if(source!=nullptr)CFRelease(source);
        throw std::runtime_error("SELF_POST_SETUP_FAILED: fixed native key events could not be created");
    }
    CGEventSetFlags(down,kCGEventFlagMaskSecondaryFn);
    CGEventSetFlags(up,kCGEventFlagMaskSecondaryFn);
    CGEventKeyboardSetUnicodeString(down,1,&appKitCodepoint);
    CGEventKeyboardSetUnicodeString(up,1,&appKitCodepoint);
    CGEventPostToPid(::getpid(),down);
    CGEventPostToPid(::getpid(),up);
    CFRelease(down);CFRelease(up);CFRelease(source);
}
void emitSelfPostState(const char* step,const char* outcome,juce::Component& root,juce::TextEditor& editor){
    auto& viewport=instructionViewport(editor);
    const auto* peer=root.getPeer();
    std::cout<<"EAR_SELF_POST step="<<step<<" outcome="<<outcome<<" pid="<<::getpid()
             <<" peer_id="<<(peer==nullptr?0:peer->getUniqueID())
             <<" native_window="<<reinterpret_cast<std::uintptr_t>(root.getWindowHandle())
             <<" caret="<<editor.getCaretPosition()<<" viewport_y="<<viewport.getViewPositionY()
             <<" foreground="<<(juce::Process::isForegroundProcess()?1:0)
             <<" juce_focus="<<(juce::Component::getCurrentlyFocusedComponent()==&editor&&editor.hasKeyboardFocus(false)?1:0)
             <<" showing="<<(root.isShowing()?1:0)<<std::endl;
}
class EarSelfPostSequence final : private juce::Timer {
public:
    EarSelfPostSequence(juce::Component& root,juce::TextEditor& editor,std::function<void()> integrity,
                        std::function<bool()> beginning,std::array<int,5>& positions)
        :root_(root),editor_(editor),integrity_(std::move(integrity)),beginning_(std::move(beginning)),positions_(positions){}
    void run(){
        startTimer(20);
        juce::MessageManager::getInstance()->runDispatchLoop();
        stopTimer();
        if(failure_)std::rethrow_exception(failure_);
        check(step_==4,"SELF_POST_LOOP_INCOMPLETE: native dispatch loop returned before the fixed sequence completed");
    }
private:
    static constexpr std::array<const char*,4> labels_{{"home","end","home_again","page_down"}};
    static constexpr std::array<CGKeyCode,4> keys_{{115,119,115,121}};
    static constexpr std::array<UniChar,4> codepoints_{{0xF729,0xF72B,0xF729,0xF72D}};
    static constexpr std::array<const char*,4> failures_{{
        "SELF_POST_HOME_UNDELIVERED: Home from the peer-established bottom did not reach the exact Ear beginning",
        "SELF_POST_END_UNDELIVERED: End did not reach the exact Ear ending",
        "SELF_POST_REPEATED_HOME_UNDELIVERED: Home posted after End did not reach the exact Ear beginning",
        "SELF_POST_PAGE_DOWN_UNDELIVERED: Page Down did not move the exact Ear viewport"
    }};
    void finish(){stopTimer();juce::MessageManager::getInstance()->stopDispatchLoop();}
    void fail(const char* step,const char* outcome,const char* message){
        emitSelfPostState(step,outcome,root_,editor_);
        failure_=std::make_exception_ptr(std::runtime_error(message));
        finish();
    }
    void postCurrent(){
        try{postNavigationKeyToSelf(keys_[static_cast<std::size_t>(step_)],codepoints_[static_cast<std::size_t>(step_)]);}
        catch(...){emitSelfPostState(labels_[static_cast<std::size_t>(step_)],"post_refused",root_,editor_);failure_=std::current_exception();finish();}
    }
    bool observed()const{
        auto& viewport=instructionViewport(editor_);
        if(step_==0||step_==2)return beginning_();
        if(step_==1)return editor_.getCaretPosition()==editor_.getTotalNumChars()&&viewport.getViewPositionY()>positions_[1];
        return viewport.getViewPositionY()>positions_[3];
    }
    void timerCallback()override{
        try{
            auto& viewport=instructionViewport(editor_);
            viewport.getVerticalScrollBar().handleUpdateNowIfNeeded();
            if(step_<0){
                if(juce::Process::isForegroundProcess()&&juce::Component::getCurrentlyFocusedComponent()==&editor_
                   &&editor_.hasKeyboardFocus(false)){
                    emitSelfPostState("owned","observed",root_,editor_);step_=0;polls_=0;postCurrent();return;
                }
                if(++polls_>=50)fail("owned","timeout","SELF_POST_FOCUS_FAILED: own test process/window/editor did not obtain foreground JUCE focus");
                return;
            }
            if(!observed()){
                if(++polls_>=50)fail(labels_[static_cast<std::size_t>(step_)],"timeout",failures_[static_cast<std::size_t>(step_)]);
                return;
            }
            emitSelfPostState(labels_[static_cast<std::size_t>(step_)],"observed",root_,editor_);
            integrity_();positions_[static_cast<std::size_t>(step_)+1]=viewport.getViewPositionY();
            ++step_;polls_=0;
            if(step_==4){finish();return;}
            postCurrent();
        }catch(...){failure_=std::current_exception();finish();}
    }
    juce::Component& root_;juce::TextEditor& editor_;
    std::function<void()> integrity_;std::function<bool()> beginning_;
    std::array<int,5>& positions_;std::exception_ptr failure_;
    int step_{-1},polls_{};
};
void populatedEarSelfPostPilot(const char* resource){
    const auto root=std::filesystem::path{resource}.parent_path();
    const auto package=tasks::ear234::package::ClosedPackage::load(
        content::readBounded(root/"compiled-manual-families-v1/ear234/closed-package.json",512*1024),
        content::readBounded(root/"learn-source-index/exercises.jsonl",32*1024*1024));
    const std::string key="exercise-completeness-r01/level076/moduleg/p013-u001/moduleglayeredsixteenbartranscriptionlab";
    const std::string identity="level076/moduleg/p013-u001/moduleglayeredsixteenbartranscriptionlab";

    desktop::EarSourceProcedureView view;view.setSize(920,680);
    check(view.open(package,key,identity),"Exact populated Ear source owner did not open for self-post pilot");
    check(view.retainedOwnerCount()==1&&view.retainedHistoryCount()==0,"Self-post pilot requires one untouched Ear owner");
    const auto initialState=view.learnerView();
    std::array<int,5> viewportSequence{};
    std::uintptr_t ownedWindow{};
    std::uint32_t ownedPeer{};
    std::exception_ptr pilotFailure;
    try{
        NativePeerScope peer(view);
        auto& instructions=control<juce::TextEditor>(view,"typed-instructions");
        auto& viewport=instructionViewport(instructions);
        const auto original=instructions.getText().toStdString();
        check(original.size()==637&&content::sha256(original)=="2d17ff23d1df4e92bdad5fd08958c19d99852cfe45f750303ae7fc0418ebcb5f",
              "Exact populated Ear body differs before self-post pilot");
        check(instructions.isReadOnly()&&instructions.getTextHeight()>viewport.getViewHeight(),
              "Self-post pilot requires clipped, read-only exact Ear prose");
        const auto unchanged=[&]{
            check(instructions.isReadOnly()&&instructions.getText().toStdString()==original,
                  "Self-post navigation changed the exact Ear instruction body");
            check(view.retainedOwnerCount()==1&&view.retainedHistoryCount()==0&&view.learnerView()==initialState,
                  "Self-post navigation changed Ear owner, history or learner state");
            check(juce::Component::getCurrentlyFocusedComponent()==&instructions&&instructions.hasKeyboardFocus(false),
                  "Self-post navigation changed actual JUCE instruction focus");
        };
        const auto beginningVisible=[&]{
            const auto caret=instructions.getCaretRectangleForCharIndex(0);
            const auto visible=instructions.getLocalArea(&viewport,viewport.getLocalBounds());
            return instructions.getCaretPosition()==0&&caret.getY()>=visible.getY()&&caret.getBottom()<=visible.getBottom();
        };

        juce::Process::makeForegroundProcess();
        view.getPeer()->grabFocus();
        instructions.grabKeyboardFocus();
        ownedWindow=reinterpret_cast<std::uintptr_t>(view.getWindowHandle());
        ownedPeer=view.getPeer()->getUniqueID();
        check(ownedWindow!=0&&ownedPeer!=0,"Self-post pilot requires one exact owned native window");

        // One existing peer-dispatch control establishes a discriminating bottom
        // state. The retained 532-check suite is not replayed by this selector.
        check(peerKey(view,instructions,juce::KeyPress(juce::KeyPress::endKey)),
              "Peer control End was not handled by the exact Ear editor");
        check(instructions.getCaretPosition()==instructions.getTotalNumChars()&&viewport.getViewPositionY()>0,
              "Peer control End did not establish the exact Ear bottom state");
        viewportSequence[0]=viewport.getViewPositionY();unchanged();
        emitSelfPostState("peer_control_end","observed",view,instructions);

        // This opt-in process exits immediately afterward, so one standard JUCE
        // native dispatch loop may be stopped after the fixed sequence. No modal
        // loop API, global build flag or second dispatch-loop invocation is used.
        EarSelfPostSequence sequence(view,instructions,unchanged,beginningVisible,viewportSequence);
        sequence.run();
    }catch(...){pilotFailure=std::current_exception();}
    const bool closed=view.getPeer()==nullptr&&view.getWindowHandle()==nullptr&&!view.isShowing();
    std::cout<<"EAR_SELF_POST step=closed outcome="<<(closed?"observed":"failed")<<" pid="<<::getpid()
             <<" peer_id="<<ownedPeer<<" native_window="<<ownedWindow
             <<" peer_absent="<<(view.getPeer()==nullptr?1:0)<<" showing="<<(view.isShowing()?1:0)<<std::endl;
    check(closed,"SELF_POST_CLOSE_FAILED: scoped native Ear window did not close through RAII");
    if(pilotFailure)std::rethrow_exception(pilotFailure);
    std::cout<<"PASS Ear self-post pilot pid="<<::getpid()<<" body_sha256=2d17ff23d1df4e92bdad5fd08958c19d99852cfe45f750303ae7fc0418ebcb5f"
             <<" viewport_sequence=peerEnd:"<<viewportSequence[0]<<",home:"<<viewportSequence[1]
             <<",end:"<<viewportSequence[2]<<",homeAgain:"<<viewportSequence[3]<<",pageDown:"<<viewportSequence[4]
             <<" exact_privateState_Fn_R25_mapping=1 actual_JUCE_focus=retained owner_history_state=unchanged"
             <<" native_window_RAII_closed=1 audio_device_profile=unused\n";
}
#endif
void emptyListeningPages(){
    desktop::EarSourceProcedureView ear;ear.setSize(440,680);
    desktop::C43SourceProcedureView c43;c43.setSize(920,680);
    for(auto* page:std::array<juce::Component*,2>{{&ear,&c43}}){
        NativePeerScope peer(*page);
        auto& instructions=control<juce::TextEditor>(*page,"typed-instructions");accessibleText(instructions,instructions.getText());
    }
    check(ear.retainedHistoryCount()==0&&c43.retainedHistoryCount()==0,"Inspection must not create listening history");
}
}
int main(int argc,char** argv){
    try{
        if(argc!=2&&argc!=3)throw std::runtime_error("usage: manual-readability-tests <typed-task-resource-directory> [--ear-self-post-pilot]");
        const bool selfPostPilot=argc==3&&std::string{argv[2]}=="--ear-self-post-pilot";
        if(argc==3&&!selfPostPilot)throw std::runtime_error("Only the fixed --ear-self-post-pilot selector is supported");
        juce::ScopedJuceInitialiser_GUI juce;
        if(selfPostPilot){
#if JUCE_MAC
            populatedEarSelfPostPilot(argv[1]);
            return 0;
#else
            throw std::runtime_error("SELF_POST_UNSUPPORTED_PLATFORM: the bounded native pilot requires macOS");
#endif
        }
        editableFallback();formReadability();manualDisclosure(argv[1]);originalManualKeyboard(argv[1]);populatedEarKeyboard(argv[1]);emptyListeningPages();
        std::cout<<"PASS manual readability "<<checks<<" checks; peer-dispatched reading keys, real focus, instructions/Unknown/owner and disclosure boundaries retained; no listening claim\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL "<<error.what()<<'\n';return 1;}
}
