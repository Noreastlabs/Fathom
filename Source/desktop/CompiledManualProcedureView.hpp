#pragma once
#include "desktop/ReadOnlyTextEditor.hpp"
#include "desktop/TypedManualForm.hpp"
#include "storage/ProfileStore.hpp"
#include "tasks/ManualProcedureGraph.hpp"
#include "tasks/InstalledExtraSource17Registry.hpp"
#include "tasks/ManualContactSourceHandle.hpp"
#include "tasks/OrderedContactTaskFormAdapter.hpp"
#include <map>
#include <variant>

namespace fathom::desktop {
enum class ManualProcedureFamily { None, Curriculum, OrderedContact };
class CompiledManualProcedureView;
// The outer capability is opaque, as are contact native/form tokens. A gesture
// retains the owner, exact action, native revision and view/form generation
// captured before delivery. A caller cannot retarget it to another task.
class ManualProcedureGesture final {
public:
    ManualProcedureGesture() = default;
    ManualProcedureGesture(const ManualProcedureGesture&) = default;
    ManualProcedureGesture& operator=(const ManualProcedureGesture&) = delete;
private:
    std::variant<std::monostate,tasks::manual_procedure_graph::Token,
        tasks::manual_procedure_graph::SourceRoleAction,
        tasks::ordered_contacts::manual::Token,
        tasks::ordered_contacts::manual::FormToken> token_;
    ManualProcedureFamily family_{ManualProcedureFamily::None};
    std::string key_, role_, action_;
    bool sourceRole_{};
    std::uint64_t generation_{}, nativeRevision_{}, formGeneration_{};
    friend class CompiledManualProcedureView;
};
class ManualProcedureButton final : public juce::TextButton {
public:
    ManualProcedureButton();
    std::function<ManualProcedureGesture()> capture;
    std::function<void(const ManualProcedureGesture&)> deliver;
    void mouseDown(const juce::MouseEvent&) override;
    bool keyPressed(const juce::KeyPress&) override;
private:
    std::optional<ManualProcedureGesture> pending_;
    bool delivered_{};
    juce::uint32 lastDeliveryMs_{};
};
// The host gates exact source keys through its installed closed registries.
// This renderer uses only native learner descriptors/instructions and retains
// one owner per exact key. The closed seven-only intentional Source role renders
// its exact script; the normal learner projection never renders trusted context.
class CompiledManualProcedureView final : public juce::Component {
public:
    CompiledManualProcedureView();
    ~CompiledManualProcedureView() override;
    bool open(const std::string& exactSourceKey);
    // Trusted closed extraSource package admission, never caller definitions.
    bool openExtraSource(const tasks::extra_source17::InstalledExtraSource17Registry&,
                         const std::string& exactSourceIdentity);
    bool attachDraftStore(storage::ProfileStore&,const std::string& profileIdentity);
    bool prepareDraftStoreReopen();
    bool detachDraftStore(); // no pending job; original unresolved publication retained
    void serviceDrafts();
    bool draftBusy() const noexcept;
    bool draftPending() const noexcept;
    bool saveDraftsForClose(bool stoppedAndResolved);
    void cancelDraftClose();
    bool saveCurrentDraft();
    bool refreshSavedDrafts(bool nextPage=false);
    bool reopenSelectedDraft();
    bool reconcileDraft();
    std::string learnerHistoryExport();
    bool copyLearnerHistory();
    std::function<void(const std::string&)> onCopyLearnerHistory;
    std::function<bool()> onDraftSaveGate;
    std::function<bool()> onDraftStoreReopen;
    bool prepareForNavigation();
    void resumeAfterNavigation();
    ManualProcedureFamily family() const noexcept { return family_; }
    const std::string& exactSourceKey() const noexcept { return key_; }
    std::size_t retainedOwnerCount() const noexcept { return owners_.size(); }
    std::size_t retainedHistoryCount() const;
    json::Value learnerView() const;
    json::Value learnerActions() const;
    // Presentation-only groups; every original report remains separately committed.
    json::Value committedReportGroups() const;
    json::Value selectedSchema() const { return selectedSchema_; }
    bool sourceRolePresentation() const noexcept {return sourceRole_;}
    const tasks::manual_procedure_graph::ManualProcedureGraph* curriculumTask() const noexcept;
    const tasks::ordered_contacts::manual::Task* contactTask() const noexcept;
    std::function<bool()> onBack;
    std::function<bool()> onSettings;
    void resized() override;
    void paint(juce::Graphics&) override;
private:
    struct Owner {
        std::unique_ptr<tasks::manual_procedure_graph::ManualProcedureGraph> curriculum;
        bool intentionalSourcePresentationSeen{};
        std::string draftId;
        std::int64_t draftRevision{};
        std::uint64_t draftSerial{1},savedDraftSerial{};
        std::map<std::string,json::Value> fieldDrafts;
        std::optional<tasks::ordered_contacts::manual::Extension> restoredFormExtension;
        std::unique_ptr<tasks::ordered_contacts::manual::Task> contact;
        std::unique_ptr<tasks::ordered_contacts::manual::OrderedContactTaskFormAdapter> adapter;
    };
    using OwnerKey=std::pair<ManualProcedureFamily,std::string>;
    Owner* owner() noexcept;
    const Owner* owner() const noexcept;
    bool hiddenSevenOwner() const;
    json::Value presentationActions() const;
    json::Value presentationView() const;
    void switchSourceRole(const ManualProcedureGesture&,bool);
    bool inactive() const;
    void fenceInactive();
    ManualProcedureGesture capture(const std::string& role) const;
    bool current(const ManualProcedureGesture&) const;
    void selectAction(const ManualProcedureGesture&);
    void configureSelected();
    void edited(const std::string& path);
    void command(const ManualProcedureGesture&);
    void navigation(const ManualProcedureGesture&,bool settings);
    void render(bool fresh=false);
    std::vector<std::string> instructions() const;
    std::vector<std::string> summaries() const;
    std::string phase() const;
    void requestCancellation();
    std::size_t ownerDraftWatermark()const;
    std::string currentFormDraftKey()const;
    bool cacheFormDraft();
    void restoreCurrentFormDraft();
    bool startDraftSave(const OwnerKey&,bool gate);
    void draftControls();
    std::map<OwnerKey,Owner> owners_;
    struct Drafts;
    std::unique_ptr<Drafts> drafts_;
    ManualProcedureFamily family_{ManualProcedureFamily::None};
    std::string key_, selectedAction_, message_;
    std::vector<std::string> actionNames_;
    json::Value selectedSchema_;
    std::optional<tasks::ordered_contacts::manual::OpenForm> contactForm_;
    std::optional<ManualProcedureGesture> formFence_;
    std::uint64_t generation_{1};
    bool navigationPrepared_{}, pendingNavigation_{};
    bool sourceRole_{};
    juce::Label heading_,phase_,status_,actionLabel_;
    ReadOnlyTextEditor retainedState_;
    juce::ComboBox actions_,savedDrafts_;
    juce::TextButton copyHistory_{"Copy full learner history"};
    juce::TextButton saveDraft_{"Save manual draft"},listDrafts_{"Find saved drafts"},moreDrafts_{"More drafts"},reopenDraft_{"Reopen selected draft"},checkDraft_{"Check original save"};
    TypedManualForm form_;
    ManualProcedureButton submit_,back_,settings_,sourceRoleButton_,listenerRoleButton_;
};
} // namespace fathom::desktop
