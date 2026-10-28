#pragma once
#include "desktop/ReadOnlyTextEditor.hpp"
#include "desktop/SourceDraftPanel.hpp"
#include "Ear234.hpp"
#include "ClosedPackage.hpp"
#include "desktop/TypedManualForm.hpp"
#include <map>
#include <optional>

namespace fathom::storage::manual_drafts {struct Loaded;}
namespace fathom::desktop {
// Exact presentation adapter: unsupported pure-null fields require an explicit
// blank null choice; the original native schema validates every submission.
json::Value earReportPresentationSchema(const json::Value&);
json::Value earReportNativeInput(const json::Value& nativeSchema,const json::Value& collected);
class EarSourceProcedureView;
// Copyable captured gesture, with no caller-writable owner/action/role fields.
class EarProcedureGesture final {
public:
    EarProcedureGesture(const EarProcedureGesture&)=default;
private:
    EarProcedureGesture()=default;
    std::optional<tasks::ear234::Token> token_,otherToken_;
    std::string key_,otherKey_,action_;
    std::uint64_t generation_{},formGeneration_{},roleEpoch_{};
    int role_{};
    friend class EarSourceProcedureView;
};
class EarProcedureButton final : public juce::TextButton {
public:
    using Capture=std::function<EarProcedureGesture()>;
    using Deliver=std::function<void(const EarProcedureGesture&)>;
    void bind(Capture,Deliver);
    EarProcedureGesture capture()const;
    void deliver(const EarProcedureGesture&);
    void mouseDown(const juce::MouseEvent&) override;
    bool keyPressed(const juce::KeyPress&) override;
private:
    Capture capture_; Deliver deliver_;
    std::optional<EarProcedureGesture> pending_;
};
// Host passes a verified closed package and exact source identity. This view
// collects manual declarations; it supplies no source audio, answers or credit.
class EarSourceProcedureView final : public juce::Component {
public:
    EarSourceProcedureView();
    ~EarSourceProcedureView() override;
    bool open(const tasks::ear234::package::ClosedPackage&,const std::string& exactKey,
              const std::string& exactSourceIdentity);
    bool prepareForNavigation();
    // Read-only check of all retained owners and their current fences.
    bool canOpenAnotherSource()const;
    void resumeAfterNavigation();
    std::function<void()> onBack;
    std::function<void()> onOwnerChanged;
    std::function<bool()> onSettings;
    json::Value learnerView()const;
    json::Value learnerActions()const;
    const json::Value& selectedSchema()const noexcept{return selectedSchema_;}
    std::size_t retainedOwnerCount()const noexcept{return entries_.size();}
    std::size_t retainedHistoryCount()const;
    bool providerSheetVisible()const noexcept;
    bool navigationPending()const noexcept{return navigationPending_;}
    const tasks::ear234::Owner* retainedOwner(const std::string& exactKey)const;
    // UI gathers fields; returned capture runs only off the message thread while
    // draftBusy is held. No provider authorization is included in this format.
    struct Workspace {private:json::Value metadata;std::map<std::string,std::shared_ptr<tasks::ear234::Owner>> owners;friend class EarSourceProcedureView;friend class C43SourceProcedureView;};
    std::function<std::string()> captureWorkspace();
    static Workspace decodeWorkspace(const tasks::ear234::package::ClosedPackage&,const std::string&);
    static Workspace decodeWorkspace(const tasks::ear234::package::ClosedPackage&,const storage::manual_drafts::Loaded&);
    bool installWorkspace(const tasks::ear234::package::ClosedPackage&,Workspace&&);
    bool canAttachDraftStore(const std::string&profile)const{return !embeddedContext_&&draftPanel_.canAttach(profile);}
    bool attachDraftStore(storage::ProfileStore&,const std::string&);
    bool detachDraftStore();
    bool prepareDraftStoreReopen();
    void serviceDrafts(){draftPanel_.service();}
    bool draftPending()const{return draftPanel_.pending();}
    bool draftJobBusy()const{return draftPanel_.busy();}
    bool saveDraftsForClose(bool gate){return draftPanel_.saveForClose(gate);}
    std::function<bool()> onDraftSaveGate,onDraftStoreReopen;
    std::string workspaceStamp();
    void setDraftBusy(bool);
    bool draftBusy()const noexcept{return draftBusy_;}
    std::string learnerHistoryExport();bool copyLearnerHistory();
    std::function<void(const std::string&)> onCopyLearnerHistory;
    void resized() override;
private:
    enum Role { Learner=1,Provider=2,ProviderSetup=3,OpenProvider=4,ReturnLearner=5,
                Method=6,Clue=7,Back=8,Settings=9 };
    enum class Mode { Learner,ProviderSetup,Provider };
    struct Entry {
        explicit Entry(const tasks::ear234::Definition& d):owner(std::make_shared<tasks::ear234::Owner>(d)){}
        std::shared_ptr<tasks::ear234::Owner> owner;
        std::map<std::string,json::Value> fields;
        std::string learnerAction;
        std::string identity,label,candidate;
        bool navigationFenced{};
    };
    bool installWorkspaceImpl(const tasks::ear234::package::ClosedPackage&,Workspace&&,bool);
    Entry* entry(); const Entry* entry()const;
    EarProcedureGesture capture(int role,const std::string& action)const;
    bool current(const EarProcedureGesture&)const;
    void deliver(const EarProcedureGesture&);
    void render();
    void selectAction(int,std::uint64_t,const tasks::ear234::Token&);
    bool switchMethod(const std::string&);
    void configureForm(const json::Value&,int,const std::string&,
                       const std::vector<std::string>&);
    void resetProvider();
    void notifyOwnerChanged();
    void cacheFields();
    void carryFenceFields(Entry&,std::uint64_t);
    void clearFieldBinding();
    std::string fieldSlot()const;
    void embeddedDraftScope(){embeddedContext_=true;draftPanel_.setVisible(false);}
    std::shared_ptr<const tasks::ear234::Owner> sharedOwner(const std::string&key)const{auto i=entries_.find(key);return i==entries_.end()?nullptr:i->second->owner;}
    bool embeddedContext_{};
    friend class C43SourceProcedureView;
    void fail(const std::string&);
    std::vector<std::string> instructionText()const;
    std::optional<tasks::ear234::package::ClosedPackage> package_;
    std::map<std::string,std::unique_ptr<Entry>> entries_;
    std::string key_,selectedAction_,selectedOther_,lastError_;
    json::Value selectedSchema_;
    std::vector<std::string> actions_,methods_,clues_;
    std::uint64_t generation_{1},roleEpoch_{1};
    bool navigationPending_{},providerAuthorized_{};
    Mode mode_{Mode::Learner};
    SourceDraftPanel draftPanel_;
    bool draftBusy_{};
    std::string providerDraftId_;
    std::string fieldKey_,fieldAction_,fieldRole_;
    std::uint64_t fieldRevision_{},fieldEpoch_{};
    TypedManualForm form_;
    juce::TextButton worksheet_{"Copy learner worksheet"};
    juce::Label heading_,phase_,actionLabel_,methodLabel_,clueLabel_;
    ReadOnlyTextEditor status_,presentation_;
    juce::ComboBox actionMenu_,methodMenu_,clueMenu_;
    EarProcedureButton submit_,provider_,learner_,addClue_,back_,settings_;
};
}
