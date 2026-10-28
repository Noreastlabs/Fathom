#pragma once
#include "desktop/ReadOnlyTextView.hpp"
#include "content/ExerciseQueue.hpp"
#include <array>
namespace fathom::desktop {
class PracticeQueueHeader final : public juce::Component,private juce::Timer {
public:
    PracticeQueueHeader() {
        setComponentID("practice-suite-queue");setTitle("Current exercise followed by upcoming exercises in selected source order.");
        for(std::size_t i=0;i<rows_.size();++i){auto& row=rows_[i];addAndMakeVisible(row);row.setComponentID("practice-suite-queue-row-"+juce::String(static_cast<int>(i)));row.setFont(juce::FontOptions{i==0?16.0f:14.0f});row.setAlpha(i==0?1.0f:0.30f);row.setWantsKeyboardFocus(true);row.setExplicitFocusOrder(static_cast<int>(i)+1);}startTimer(100);
    }
    ~PracticeQueueHeader()override{stopTimer();}
    void display(const navigation::ExerciseQueue* queue,const std::vector<std::string>& labels) {
        for(std::size_t i=0;i<rows_.size();++i){auto& row=rows_[i];const auto entry=queue?queue->entryAt(queue->position()+i):nullptr;
            const std::string text=entry&&i<labels.size()?(i==0?"Current: ":"Upcoming: ")+labels[i]:std::string{};
            row.setText(juce::String::fromUTF8(text.c_str()),juce::dontSendNotification);row.setTitle(juce::String::fromUTF8(text.c_str()));
            row.setTooltip(entry?juce::String::fromUTF8((text+"\nSource: "+entry->sourceExerciseKey+" | "+entry->admission->itemId+" / "+entry->admission->variantId).c_str()):juce::String{});row.setVisible(entry!=nullptr&&i<labels.size());
        }
    }
    void resized() override {for(std::size_t i=0;i<rows_.size();++i)rows_[i].setBounds(16,static_cast<int>(i)*44,std::max(1,getWidth()-32),44);}
private:
    void timerCallback()override{for(std::size_t i=1;i<rows_.size();++i)rows_[i].setAlpha(rows_[i].hasKeyboardFocus(true)||rows_[i].isMouseOver(true)?1.0f:0.30f);}
    std::array<ReadOnlyTextView,3> rows_;
};
}
