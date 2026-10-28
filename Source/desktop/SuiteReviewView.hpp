#pragma once
#include "desktop/ReadOnlyTextView.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include "content/StrictJson.hpp"
namespace fathom::desktop {
class SuiteReviewView final : public juce::Component {
public:
    std::function<void(json::Value)> onSubmit;
    std::function<void()> onRetry,onBack;
    SuiteReviewView(){
        setComponentID("suite-review");heading_.setText("Review your completed exercises",juce::dontSendNotification);heading_.setComponentID("suite-review-heading");heading_.setFont(juce::FontOptions{22.0f,juce::Font::bold});
        score_.setComponentID("suite-review-score");score_.setTitle("Choose one final self-assessment for the exercises actually completed in this suite.");score_.addItem("No self-assessment",1);score_.addItem("Struggling",2);score_.addItem("Developing",3);score_.addItem("Clean",4);score_.addItem("Easy",5);score_.setSelectedId(1,juce::dontSendNotification);
        submit_.setComponentID("suite-review-submit");submit_.setTitle("Save this explicit final self-assessment for the completed exercises; skipped and interrupted exercises are excluded.");retry_.setComponentID("suite-review-retry");retry_.setTitle("Retry the unchanged original suite review save.");back_.setComponentID("suite-review-back");back_.setTitle("Return after the original suite review is saved.");status_.setComponentID("suite-review-status");status_.setTitle("Suite review membership, original save status and provenance.");
        for(auto* c:std::initializer_list<juce::Component*>{&heading_,&status_,&score_,&submit_,&retry_,&back_})addAndMakeVisible(c);
        submit_.onClick=[this]{if(onSubmit)onSubmit(score_.getSelectedId()==1?json::Value(nullptr):json::Value(score_.getText().toStdString()));};retry_.onClick=[this]{if(onRetry)onRetry();};back_.onClick=[this]{if(onBack)onBack();};
        int order=1;for(auto* c:std::initializer_list<juce::Component*>{&score_,&submit_,&retry_,&back_}){c->setWantsKeyboardFocus(true);c->setExplicitFocusOrder(order++);}present(0,"",false,false);
    }
    void begin(std::size_t completed,const std::string& message){scoreLocked_=false;score_.setSelectedId(1,juce::dontSendNotification);present(completed,message,false,false);}
    void retainOriginalScore(){scoreLocked_=true;}
    void present(std::size_t completed,const std::string& message,bool pending,bool saved){
        status_.setText(juce::String(static_cast<juce::int64>(completed))+" completed exercises. Your final self-assessment applies to these completed exercises. Skipped or interrupted exercises receive no score. The app has not verified your playing.\n"+juce::String::fromUTF8(message.c_str()),juce::dontSendNotification);
        score_.setEnabled(!scoreLocked_&&!pending&&!saved);submit_.setEnabled(!scoreLocked_&&!pending&&!saved);retry_.setEnabled(scoreLocked_&&!pending&&!saved);back_.setEnabled(saved);
    }
    void resized() override {const int w=std::max(1,getWidth()-48);heading_.setBounds(24,24,w,40);status_.setBounds(24,76,w,140);score_.setBounds(24,236,220,36);submit_.setBounds(24,288,220,36);retry_.setBounds(256,288,200,36);back_.setBounds(24,344,180,36);}
private:bool scoreLocked_{};juce::Label heading_;ReadOnlyTextView status_;juce::ComboBox score_;juce::TextButton submit_{"Save final review"},retry_{"Retry original save"},back_{"Return to Home"};
};
}
