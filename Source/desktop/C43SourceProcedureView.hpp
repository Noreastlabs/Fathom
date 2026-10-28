#pragma once
#include "desktop/ReadOnlyTextEditor.hpp"
#include "desktop/SourceDraftPanel.hpp"
#include "tasks/c43/C43.hpp"
#include "tasks/c43/ClosedPackage.hpp"
#include "desktop/EarSourceProcedureView.hpp"
#include <map>
#include <optional>

namespace fathom::storage::manual_drafts {struct Loaded;}
namespace fathom::desktop {
class C43SourceProcedureView;
class C43ProcedureGesture final {
public: C43ProcedureGesture(const C43ProcedureGesture&)=default;
private:
    C43ProcedureGesture()=default;
    std::optional<tasks::c43::Token> token_;
    std::optional<tasks::ear234::Token> contextToken_;
    std::shared_ptr<const tasks::ear234::Owner> contextOwner_;
    std::string key_,action_,contextKey_;
    std::uint64_t generation_{},formGeneration_{},roleEpoch_{};
    int role_{};
    friend class C43SourceProcedureView;
};
// Type-specific capture adapter; the native C43 token never becomes editable.
class C43ProcedureButton final : public juce::TextButton {
public:
    using Capture=std::function<C43ProcedureGesture()>;
    using Deliver=std::function<void(const C43ProcedureGesture&)>;
    void bind(Capture,Deliver);
    C43ProcedureGesture capture()const;
    void deliver(const C43ProcedureGesture&);
    void mouseDown(const juce::MouseEvent&) override;
    bool keyPressed(const juce::KeyPress&) override;
private:
    Capture capture_;Deliver deliver_;
    std::optional<C43ProcedureGesture> pending_;
};

// Manual presentation only. Both closed packages and exact identities are host
// authorities. Source facts, availability, timings and completion stay native.
class C43SourceProcedureView final : public juce::Component {
public:
    C43SourceProcedureView();
    ~C43SourceProcedureView() override;
    bool open(const tasks::c43::package::ClosedPackage&,
              const tasks::ear234::package::ClosedPackage&,
              const std::string& exactKey,const std::string& exactIdentity);
    bool prepareForNavigation();
    void resumeAfterNavigation();
    std::function<void()> onBack;
    std::function<bool()> onSettings;
    json::Value learnerView()const;
    json::Value learnerActions()const;
    const json::Value& selectedSchema()const noexcept{return selectedSchema_;}
    std::size_t retainedOwnerCount()const noexcept{return entries_.size();}
    std::size_t retainedHistoryCount()const;
    bool providerSheetVisible()const noexcept;
    bool navigationPending()const noexcept{return navigationPending_;}
    const tasks::c43::Owner* retainedOwner(const std::string&)const;
    // Actual concurrent UI, not a completion snapshot. Host/test access does
    // not supply an attachment conclusion or forge a native capability.
    EarSourceProcedureView* contextView(const std::string&)const;
    struct Workspace {private:json::Value metadata;std::map<std::string,std::shared_ptr<tasks::c43::Owner>> owners;std::map<std::string,EarSourceProcedureView::Workspace> contexts;friend class C43SourceProcedureView;};
    std::function<std::string()> captureWorkspace();
    static Workspace decodeWorkspace(const tasks::c43::package::ClosedPackage&,const tasks::ear234::package::ClosedPackage&,const std::string&);
    static Workspace decodeWorkspace(const tasks::c43::package::ClosedPackage&,const tasks::ear234::package::ClosedPackage&,const storage::manual_drafts::Loaded&);
    bool installWorkspace(const tasks::c43::package::ClosedPackage&,const tasks::ear234::package::ClosedPackage&,Workspace&&);
    bool canAttachDraftStore(const std::string&profile)const{return draftPanel_.canAttach(profile);}
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
    enum Role{Learner=1,Provider=2,ProviderSetup=3,OpenProvider=4,
              ReturnLearner=5,Back=6,Settings=7,RefreshContext=8};
    enum class Mode{Learner,ProviderSetup,Provider};
    struct Entry{
        explicit Entry(const tasks::c43::Definition& d):owner(std::make_shared<tasks::c43::Owner>(d)){}
        std::shared_ptr<tasks::c43::Owner> owner;
        std::map<std::string,json::Value> fields;
        std::string learnerAction;
        std::shared_ptr<EarSourceProcedureView> context;
        std::string identity,contextKey;
        bool navigationFenced{};
    };
    bool installWorkspaceImpl(const tasks::c43::package::ClosedPackage&,const tasks::ear234::package::ClosedPackage&,Workspace&&,bool);
    Entry* entry();const Entry* entry()const;
    C43ProcedureGesture capture(int,const std::string&)const;
    bool current(const C43ProcedureGesture&)const;
    void deliver(const C43ProcedureGesture&);
    void selectAction(int,std::uint64_t,const tasks::c43::Token&);
    void configureForm(const json::Value&,int,const std::string&);
    void resetProvider();void invalidateContextControls();
    void contextChanged();
    void cacheFields();void clearFieldBinding();std::string fieldSlot()const;
    void render();void fail(const std::string&);
    std::vector<std::string> instructionText()const;
    std::map<std::string,std::unique_ptr<Entry>> entries_;
    std::optional<tasks::c43::package::ClosedPackage> package_;
    std::optional<tasks::ear234::package::ClosedPackage> contextPackage_;
    std::string key_,selectedAction_,lastError_;
    json::Value selectedSchema_,nativeSchema_;
    std::vector<std::string> actions_;
    std::uint64_t generation_{1},roleEpoch_{1};
    bool navigationPending_{},providerAuthorized_{};
    Mode mode_{Mode::Learner};
    SourceDraftPanel draftPanel_;
    bool draftBusy_{};std::string providerDraftId_;
    std::string fieldKey_,fieldRole_,fieldAction_;std::uint64_t fieldRevision_{},fieldEpoch_{};
    TypedManualForm form_;
    juce::TextButton worksheet_{"Copy learner worksheet"};
    juce::Label heading_,phase_,actionLabel_,contextLabel_;
    ReadOnlyTextEditor status_,presentation_;
    juce::ComboBox actionMenu_;
    juce::Viewport contextViewport_;
    C43ProcedureButton submit_,provider_,learner_,back_,settings_,refreshContext_;
};
}
