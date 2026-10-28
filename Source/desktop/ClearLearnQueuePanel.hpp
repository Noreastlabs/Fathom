#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
namespace fathom::desktop {
class ClearLearnQueuePanel final : public juce::Component {
public:
    std::function<void()> onCancel,onConfirm,onReturn,onRetry;
    ClearLearnQueuePanel(){
        setComponentID("clear-learn-queue-confirmation");setInterceptsMouseClicks(true,true);
        addAndMakeVisible(title_);addAndMakeVisible(body_);addAndMakeVisible(cancel_);addAndMakeVisible(confirm_);addAndMakeVisible(return_);addAndMakeVisible(retry_);
        title_.setText("Clear this lesson queue?",juce::dontSendNotification);title_.setFont(juce::Font(juce::FontOptions(24.0f)));
        body_.setJustificationType(juce::Justification::topLeft);body_.setFont(juce::Font(juce::FontOptions(17.0f)));
        retry_.setComponentID("queue-clear-retry");retry_.setExplicitFocusOrder(4);retry_.onClick=[this]{if(retry_.isEnabled()&&onRetry)onRetry();};
        cancel_.setComponentID("queue-clear-cancel");confirm_.setComponentID("queue-clear-confirm");return_.setComponentID("queue-clear-return");
        cancel_.setExplicitFocusOrder(1);return_.setExplicitFocusOrder(2);confirm_.setExplicitFocusOrder(3);
        cancel_.onClick=[this]{if(cancel_.isEnabled()&&onCancel)onCancel();};confirm_.onClick=[this]{if(confirm_.isEnabled()&&onConfirm)onConfirm();};return_.onClick=[this]{if(return_.isEnabled()&&onReturn)onReturn();};
    }
    void present(bool ready,bool pending,const std::string& reason){
        body_.setText(juce::String::fromUTF8((std::string{"This ends the current queue and removes its remaining selection. You cannot resume this queue after confirming. Choose exercises again to start fresh.\n\nSaved results and history stay intact. Completed exercises receive no new score or credit. Nothing starts playing.\n\n"}+(pending?"Confirming the original Session and queue closure. Wait; use Check original reset if its reply is uncertain. ":ready?"Cancel keeps your current queue unchanged.":reason)).c_str()),juce::dontSendNotification);
        confirm_.setEnabled(ready);cancel_.setEnabled(!pending);retry_.setVisible(pending);return_.setEnabled(!pending&&!ready);
    }
    void allowRetry(bool enabled){retry_.setEnabled(enabled);}
    void resized()override{auto b=getLocalBounds().reduced(28);title_.setBounds(b.removeFromTop(45));b.removeFromTop(12);auto buttons=b.removeFromBottom(162);body_.setBounds(b);cancel_.setBounds(buttons.removeFromTop(34));buttons.removeFromTop(8);return_.setBounds(buttons.removeFromTop(34));buttons.removeFromTop(8);confirm_.setBounds(buttons.removeFromTop(34));buttons.removeFromTop(8);retry_.setBounds(buttons.removeFromTop(34));}
    void paint(juce::Graphics& g)override{g.fillAll(juce::Colour(0xff10212c));}
private:
    juce::Label title_,body_;
    juce::TextButton cancel_{"Cancel - keep queue"},confirm_{"Clear queue & start fresh"},return_{"Return to current Practice"},retry_{"Check original reset"};
};
}
