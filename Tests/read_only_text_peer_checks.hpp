#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include <string>

namespace fathom::test {
// Test-only peer input. Public focus and viewport observations are independent
// of AX metadata; these checks make no physical keyboard-delivery claim.
class ReadingPeerScope final {
public:
    explicit ReadingPeerScope(juce::Component& root):root_(root) {
        root_.addToDesktop(juce::ComponentPeer::windowHasTitleBar);
        root_.setVisible(true);
    }
    ~ReadingPeerScope() { root_.removeFromDesktop(); }
    ReadingPeerScope(const ReadingPeerScope&)=delete;
    ReadingPeerScope& operator=(const ReadingPeerScope&)=delete;
private:
    juce::Component& root_;
};
template<class Check>
void readingKeys(juce::Component& root,juce::TextEditor& editor,const std::string& expected,Check check) {
    using Key=juce::KeyPress;
    juce::Viewport* viewport=nullptr;
    for(auto* child:editor.getChildren())if(auto* value=dynamic_cast<juce::Viewport*>(child)){viewport=value;break;}
    check(root.getPeer()!=nullptr&&root.isShowing()&&viewport!=nullptr,"Reading fixture has a real visible peer and instruction viewport");
    check(editor.isReadOnly()&&editor.getText().toStdString()==expected,"Reading fixture contains complete original permitted text");
    check(editor.getTextHeight()>viewport->getViewHeight(),"Populated original text is actually clipped in its viewport");
    const auto press=[&](int code) {
        check(juce::Component::getCurrentlyFocusedComponent()==&editor,"Reading key starts with actual instruction focus");
        const bool handled=root.getPeer()->handleKeyPress(Key(code));
        viewport->getVerticalScrollBar().handleUpdateNowIfNeeded();
        check(handled&&juce::Component::getCurrentlyFocusedComponent()==&editor,"Peer reading key is handled without changing focus");
        check(editor.isReadOnly()&&editor.getText().toStdString()==expected,"Reading key preserves original text bytes and read-only state");
    };
    const auto edgeVisible=[&](int index) {
        const auto caret=editor.getCaretRectangleForCharIndex(index);
        const auto area=editor.getLocalArea(viewport,viewport->getLocalBounds());
        return caret.getY()>=area.getY()&&caret.getBottom()<=area.getBottom();
    };
    press(Key::endKey);const auto end=viewport->getViewPositionY();
    check(end>0&&edgeVisible(editor.getTotalNumChars()),"End reaches the populated original final line");
    press(Key::pageUpKey);check(viewport->getViewPositionY()<end,"Page Up moves the populated viewport toward the beginning");
    press(Key::homeKey);const auto top=viewport->getViewPositionY();
    check(editor.getCaretPosition()==0&&edgeVisible(0),"Home reaches the populated original first line");
    press(Key::pageDownKey);check(viewport->getViewPositionY()>top,"Page Down moves the populated viewport toward the end");
    press(Key::homeKey);const auto beforeDown=viewport->getViewPositionY();
    press(Key::downKey);const auto down=viewport->getViewPositionY();
    check(down>beforeDown,"Down moves the populated viewport toward the end");
    press(Key::upKey);check(viewport->getViewPositionY()<down,"Up moves the populated viewport toward the beginning");
    press(Key::endKey);check(edgeVisible(editor.getTotalNumChars()),"End restores visibility of the complete original ending");
}
} // namespace fathom::test
