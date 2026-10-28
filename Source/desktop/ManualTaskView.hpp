#pragma once
#include "desktop/ReadOnlyTextEditor.hpp"
#include "desktop/SourceDraftPanel.hpp"
#include "tasks/ManualTaskAdapter.hpp"
#include "desktop/MetronomeView.hpp"
#include "desktop/PresentationPolicy.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include <memory>
#include <array>

namespace fathom::desktop {
struct ManualTaskGesture {tasks::IntentToken owner;std::uint64_t generation{};};
class ManualTaskButton final : public juce::TextButton {
public:
    using juce::TextButton::TextButton;
    std::function<ManualTaskGesture()> capture;
    std::function<void(const ManualTaskGesture&)> deliver;
    ManualTaskButton(){onClick=[this]{
        if(!capture||!deliver)return;
        const auto now=juce::Time::getMillisecondCounter();
        auto token=pending_.value_or(capture());pending_.reset();
        if(delivered_&&now-lastDeliveryMs_<350)return;
        delivered_=true;lastDeliveryMs_=now;deliver(token);
    };}
    void mouseDown(const juce::MouseEvent& event) override {if(capture)pending_=capture();juce::TextButton::mouseDown(event);}
    bool keyPressed(const juce::KeyPress& key) override {
        if(key.getKeyCode()==juce::KeyPress::spaceKey||key.getKeyCode()==juce::KeyPress::returnKey){
            if(capture)pending_=capture();triggerClick();return true;
        }
        return juce::TextButton::keyPressed(key);
    }
private:
    std::optional<ManualTaskGesture> pending_;
    bool delivered_{};
    juce::uint32 lastDeliveryMs_{};
};
class ManualTaskView final : public juce::Component {
public:
    ManualTaskView();
    void setPresentationLevel(presentation::Level);
    bool open(const tasks::Definition&);
    // Active manual duties stay visible until the explicit physical release.
    // Safe navigation invalidates pending input and waits for shared-clock cleanup.
    bool prepareForNavigation();
    void invalidateForNavigation();
    void onClock(const platform::MetronomeProgress&);
    void service();
    bool clockActive() const noexcept {return adapter_&&adapter_->clockArmed();}
    bool pulsePreparing() const noexcept {return startPending_;}
    const tasks::ManualTaskAdapter* adapter() const noexcept {return adapter_.get();}
    std::function<std::optional<MetronomeView::ManualPulseStart>(int)> onStartPulse;
    std::function<bool()> onResolvePulse;
    std::function<void()> onStopPulse;
    std::function<bool()> onBack;
    std::function<void()> onAudioSettings;
    bool canAttachDraftStore(const std::string&p)const{return draftPanel_.canAttach(p);}
    bool attachDraftStore(storage::ProfileStore&s,const std::string&p){if(!draftPanel_.canAttach(p))return false;resumeAfterNavigation();return draftPanel_.attach(s,p);}
    bool detachDraftStore(){return draftPanel_.detach();}
    bool draftJobBusy()const{return draftPanel_.busy();}
    bool draftPending()const{return draftPanel_.pending();}
    bool saveDraftsForClose(bool gate){return draftPanel_.saveForClose(gate);}
    void resumeAfterNavigation(){if(navigationPrepared_){navigationPrepared_=false;++generation_;render();}}
    std::function<bool()> onDraftSaveGate,onDraftStoreReopen;
    std::function<void(const std::string&)> onCopyLearnerHistory;
    std::string learnerHistoryExport();bool copyLearnerHistory();
    void resized() override;
    void paint(juce::Graphics&) override;
private:
    void render();
    void command(tasks::IntentKind,const ManualTaskGesture&);
    void wire(ManualTaskButton&,tasks::IntentKind,const char*);
    static std::string modeName(tasks::Mode);
    struct Workspace {std::shared_ptr<tasks::ManualTaskAdapter> owner;std::vector<std::shared_ptr<tasks::ManualTaskAdapter>> archives;json::Value fields,earlier;};
    json::Value rawFields()const;void restoreFields(const json::Value&);void retainFields();
    std::string workspaceStamp()const;std::function<std::string()> captureWorkspace();
    static Workspace decodeWorkspace(const SourceDraftPanel::Loaded&);
    bool installWorkspace(Workspace,const std::string&);void setDraftBusy(bool);
    std::shared_ptr<tasks::ManualTaskAdapter> adapter_;
    std::vector<std::shared_ptr<tasks::ManualTaskAdapter>> archivedOwners_;
    json::Value::Array earlierFields_;
    SourceDraftPanel draftPanel_;bool draftBusy_{};std::uint64_t generation_{1};
    juce::TextButton worksheet_{"Copy learner worksheet"};
    bool pulsePending_{};
    bool startPending_{};
    bool navigationPrepared_{};
    int pendingBpm_{};
    juce::uint32 startRequestedMs_{},lastStartTryMs_{};
    std::string message_;
    presentation::Level presentationLevel_{presentation::Level::Beginner};
    juce::Label heading_,source_,phase_,action_,release_,bpmLabel_,status_,setupAx_;
    ReadOnlyTextEditor setup_;
    juce::TextEditor bpm_;
    std::array<juce::Label,6> reportLabels_;
    std::array<juce::TextEditor,6> reportFields_;
    std::array<juce::ToggleButton,4> setupReports_;
    ManualTaskButton sourceOrder_,evenPulse_,ready_,ack_,retry_,cancel_,releaseAck_,again_,unknown_;
    juce::TextButton back_{"Back to Learn"},audio_{"Audio settings"};
};
}
