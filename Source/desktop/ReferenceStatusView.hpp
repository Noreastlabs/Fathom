#pragma once
#include "desktop/Appearance.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include "desktop/ReferenceGuidance.hpp"
namespace fathom::desktop {
class ReferenceStatusView final:public juce::Component {
public:
    ReferenceStatusView(){
        addAndMakeVisible(primary_);addAndMakeVisible(toggle_);
        primary_.setFont(juce::FontOptions{17.0f});primary_.setTitle("Reference tone state and next action");primary_.setJustificationType(juce::Justification::centredLeft);
        toggle_.setComponentID("reference-tone-details");toggle_.setTitle("Show or hide read-only tone details");toggle_.setWantsKeyboardFocus(true);toggle_.setExplicitFocusOrder(11);toggle_.onClick=[this]{showDetails(!expanded_);};
        details_.setMultiLine(true,true);details_.setReadOnly(true);details_.setScrollbarsShown(true);details_.setFont(juce::FontOptions{16.0f});details_.setTitle("Read-only reference tone diagnostics");
        details_.setColour(juce::TextEditor::backgroundColourId,appearance::colour(0xff10212c));details_.setColour(juce::TextEditor::textColourId,appearance::colour(0xffe4edf1));
    }
    void present(const ReferenceGuidanceInput& input,std::string_view localError,std::string_view backendError){
        const auto primary=referenceGuidance(input).primary();if(primary_.getText().toStdString()!=primary)primary_.setText(primary,juce::dontSendNotification);
        const auto d=referenceDiagnostics(input,localError,backendError);if(details_.getText().toStdString()!=d)details_.setText(juce::String::fromUTF8(d.data(),static_cast<int>(d.size())),false);
    }
    void showDetails(bool value){expanded_=value;details_.setVisible(value);toggle_.setButtonText(value?"Hide tone details":"Tone details");if(onDetailsChanged)onDetailsChanged();}
    bool detailsVisible()const noexcept{return expanded_;}
    std::string primaryText()const{return primary_.getText().toStdString();}
    juce::TextEditor& detailsView()noexcept{return details_;}
    juce::TextButton& detailsButton()noexcept{return toggle_;}
    std::function<void()> onDetailsChanged;
    void resized()override{toggle_.setBounds(getWidth()-155,10,155,std::max(1,getHeight()-20));primary_.setBounds(0,0,std::max(1,getWidth()-165),getHeight());}
private:
    bool expanded_{};juce::Label primary_;juce::TextButton toggle_{"Tone details"};juce::TextEditor details_;
};
}
