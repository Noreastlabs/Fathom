#pragma once
#include "desktop/Appearance.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include "desktop/PracticeGuidance.hpp"
#include "desktop/ReadOnlyTextView.hpp"
namespace fathom::desktop {
// Primary status and the separately placed, read-only details component share
// presentation only. Neither owns a practice command or Store operation.
class PracticeStatusView final : public juce::Component {
public:
    PracticeStatusView(){
        addAndMakeVisible(primary_);addAndMakeVisible(toggle_);
        primary_.setFont(juce::FontOptions{16.0f});primary_.setComponentID("practice-save-status");primary_.setTitle("Read-only Practice save state and next action.");
        primary_.setJustificationType(juce::Justification::centredLeft);
        toggle_.setComponentID("practice-save-details");toggle_.setTitle("Show or hide read-only saved Attempt details.");toggle_.setWantsKeyboardFocus(true);toggle_.setExplicitFocusOrder(15);
        toggle_.onClick=[this]{showDetails(!expanded_);};
        details_.setMultiLine(true,true);details_.setReadOnly(true);details_.setScrollbarsShown(true);
        details_.setFont(juce::FontOptions{16.0f});details_.setComponentID("practice-save-diagnostics");details_.setTitle("Read-only saved Attempt diagnostics.");
        details_.setColour(juce::TextEditor::backgroundColourId,appearance::colour(0xff10212c));
        details_.setColour(juce::TextEditor::textColourId,appearance::colour(0xffe4edf1));
    }
    void present(const PracticeGuidanceInput& input,const storage::Reply& reply,std::string_view localError={}){
        const auto next=practiceGuidance(input).primary();
        if(primary_.getText().toStdString()!=next)primary_.setText(juce::String::fromUTF8(next.data(),static_cast<int>(next.size())),juce::dontSendNotification);
        const auto text=practiceDiagnostics(input,reply,localError)+additionalDetails_;
        if(details_.getText().toStdString()!=text)details_.setText(juce::String::fromUTF8(text.data(),static_cast<int>(text.size())),false);
    }
    void setAdditionalDetails(std::string text){additionalDetails_=std::move(text);}
    void setFont(juce::Font font){primary_.setFont(font);}
    void showDetails(bool value){
        expanded_=value;details_.setVisible(value);toggle_.setButtonText(value?"Hide save details":"Save details");
        if(onDetailsChanged)onDetailsChanged();
    }
    bool detailsVisible() const noexcept{return expanded_;}
    juce::TextEditor& detailsView() noexcept{return details_;}
    juce::TextButton& detailsButton() noexcept{return toggle_;}
    std::string primaryText() const{return primary_.getText().toStdString();}
    std::function<void()> onDetailsChanged;
    void resized() override{const auto bw=150;toggle_.setBounds(getWidth()-bw,4,bw,std::max(1,getHeight()-8));primary_.setBounds(0,0,std::max(1,getWidth()-bw-10),getHeight());}
private:
    bool expanded_{};
    ReadOnlyTextView primary_;
    std::string additionalDetails_;
    juce::TextButton toggle_{"Save details"};
    juce::TextEditor details_; // owner places this separately, outside status row
};
}
