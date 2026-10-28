#pragma once
#include "desktop/ReadOnlyTextEditor.hpp"
#include "desktop/SourceDraftPanel.hpp"
#include "tasks/AdvancedRecipeTask.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include <map>
#include <memory>
#include <variant>

namespace fathom::desktop {
struct AdvancedRecipeGesture final {
    std::variant<std::monostate,tasks::advanced::AdvancedToken,tasks::advanced::FamilyToken> token;
    std::uint64_t generation{};
};
class AdvancedRecipeButton final : public juce::TextButton {
public:
    AdvancedRecipeButton();
    std::function<AdvancedRecipeGesture()> capture;
    std::function<void(const AdvancedRecipeGesture&)> deliver;
    void mouseDown(const juce::MouseEvent&) override;
    bool keyPressed(const juce::KeyPress&) override;
private:
    std::optional<AdvancedRecipeGesture> pending_;
    bool delivered_{};
    juce::uint32 lastDeliveryMs_{};
};
// One typed form renderer for the closed56 family. Only learner-safe APIs supply
// action forms/instructions; trusted reference/player metadata is never rendered.
class AdvancedRecipeTaskView final : public juce::Component {
public:
    AdvancedRecipeTaskView();
    bool open(const std::string& exactSourceKey);
    bool prepareForNavigation();
    void resumeAfterNavigation();
    json::Value learnerView() const;
    json::Value learnerActions() const;
    json::Value selectedSchema() const { return selectedSchema_; }
    json::Value retainedHistory() const;
    std::size_t learnerTextLayoutCount() const noexcept { return learnerTextLayouts_; }
    std::size_t historyTextLayoutCount() const noexcept { return historyTextLayouts_; }
    const tasks::advanced::AdvancedRecipeTask* transferTask() const noexcept;
    const tasks::advanced::AdvancedRecipeWorkflow* workflow() const noexcept;
    std::function<bool()> onBack;
    std::function<bool()> onSettings;
    bool canAttachDraftStore(const std::string&p)const{return draftPanel_.canAttach(p);}
    bool attachDraftStore(storage::ProfileStore&s,const std::string&p){if(!draftPanel_.canAttach(p))return false;resumeAfterNavigation();return draftPanel_.attach(s,p);}
    bool detachDraftStore(){return draftPanel_.detach();}
    void serviceDrafts(){draftPanel_.service();}
    bool draftJobBusy()const{return draftPanel_.busy();}bool draftPending()const{return draftPanel_.pending();}
    bool saveDraftsForClose(bool gate){return draftPanel_.saveForClose(gate);}
    std::function<bool()> onDraftSaveGate,onDraftStoreReopen;
    std::function<void(const std::string&)> onCopyLearnerHistory;
    std::string learnerHistoryExport();bool copyLearnerHistory();
    void resized() override;
    void paint(juce::Graphics&) override;
private:
    struct Owner {
        std::shared_ptr<tasks::advanced::AdvancedRecipeTask> transfer;
        std::shared_ptr<tasks::advanced::AdvancedRecipeWorkflow> workflow;
    };
    struct Field {
        json::Value schema;
        std::string path, name, kind;
        std::vector<std::unique_ptr<Field>> children;
        std::vector<json::Value> choices;
        std::unique_ptr<juce::Label> label;
        std::unique_ptr<juce::TextEditor> text;
        std::unique_ptr<juce::ComboBox> choice, count;
        std::unique_ptr<juce::ToggleButton> flag, unknown;
    };
    struct Workspace {std::map<std::string,Owner> owners;std::map<std::string,json::Value> forms;std::map<std::string,std::string> remembered;std::string selected;};
    static std::uint64_t revision(const Owner&);
    static json::Value rawField(const Field&,std::size_t=0);
    void restoreRaw(Field&,const json::Value&,std::size_t=0);
    void cacheForm();void restoreRemembered();void carryForms(std::uint64_t,std::uint64_t);
    std::string workspaceStamp();std::function<std::string()> captureWorkspace();
    static Workspace decodeWorkspace(const SourceDraftPanel::Loaded&);
    bool installWorkspace(Workspace,const std::string&);void setDraftBusy(bool);
    std::map<std::string,json::Value> formDrafts_;
    std::map<std::string,std::string> remembered_;
    SourceDraftPanel draftPanel_;bool draftBusy_{};
    juce::TextButton worksheet_{"Copy learner worksheet"};
    Owner* owner() noexcept;
    const Owner* owner() const noexcept;
    AdvancedRecipeGesture capture(const std::string& action) const;
    bool current(const AdvancedRecipeGesture&) const;
    void apply(const AdvancedRecipeGesture&,const json::Value&);
    json::Value instructions() const;
    std::string state() const;
    void command(const AdvancedRecipeGesture&);
    void navigation(const AdvancedRecipeGesture&,bool settings);
    void selectAction(const AdvancedRecipeGesture&);
    void wire(AdvancedRecipeButton&,const char* id,const char* title,const std::string& action);
    std::unique_ptr<Field> buildField(const json::Value&,const std::string& path,const std::string& name);
    json::Value readField(const Field&) const;
    void buildArray(Field&,std::size_t count);
    int layoutField(Field&,int y,int width,int indent=0);
    void render(bool newState=false);
    std::string phaseText() const;
    std::string learnerText() const;
    std::string historyText() const;
    std::map<std::string,Owner> owners_;
    std::string key_, selectedAction_, message_;
    json::Value selectedSchema_;
    std::unique_ptr<Field> form_;
    std::uint64_t generation_{1};
    std::string cachedLearnerText_, cachedHistoryText_;
    std::size_t learnerTextLayouts_{}, historyTextLayouts_{};
    bool navigationPrepared_{}, pendingNavigation_{}, navigationReleased_{};
    std::vector<std::string> actionNames_;
    juce::Label heading_,phase_,actionLabel_,status_;
    ReadOnlyTextEditor learner_,history_;
    juce::ComboBox actions_;
    juce::Viewport inputs_;
    juce::Component inputBody_;
    AdvancedRecipeButton submit_,back_,settings_;
};
} // namespace fathom::desktop
