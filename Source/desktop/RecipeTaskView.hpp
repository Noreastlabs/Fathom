#pragma once
#include "desktop/ReadOnlyTextEditor.hpp"
#include "desktop/SourceDraftPanel.hpp"
#include "tasks/RecipeTask.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include <functional>
#include <memory>

namespace fathom::desktop {
struct RecipeGesture final {
    std::optional<tasks::recipes::Token> owner;
    std::uint64_t generation{};
};
class RecipeTaskButton final : public juce::TextButton {
public:
    RecipeTaskButton();
    std::function<RecipeGesture()> capture;
    std::function<void(const RecipeGesture&)> deliver;
    void mouseDown(const juce::MouseEvent&) override;
    bool keyPressed(const juce::KeyPress&) override;
private:
    std::optional<RecipeGesture> pending_;
    juce::uint32 lastDeliveryMs_{};
    bool delivered_{};
};

// Manual reports for the exact trusted Level68 family. No audio, tempo or credit.
class RecipeTaskView final : public juce::Component {
public:
    RecipeTaskView();
    bool open(const std::string& exactSourceKey);
    bool prepareForNavigation();
    // Explicit host return from a settings detour, retaining owned native history.
    void resumeAfterNavigation();
    const tasks::recipes::RecipeTask* task() const noexcept { return task_.get(); }
    std::vector<tasks::recipes::HistoryEvent> retainedHistory() const;
    std::function<bool()> onBack;
    std::function<bool()> onSettings;
    bool canAttachDraftStore(const std::string&p)const{return draftPanel_.canAttach(p);}
    bool attachDraftStore(storage::ProfileStore&s,const std::string&p){if(!draftPanel_.canAttach(p))return false;resumeAfterNavigation();return draftPanel_.attach(s,p);}
    bool detachDraftStore(){return draftPanel_.detach();}
    void serviceDrafts(){draftPanel_.service();}
    bool draftJobBusy()const{return draftPanel_.busy();}
    bool draftPending()const{return draftPanel_.pending();}
    bool saveDraftsForClose(bool gate){return draftPanel_.saveForClose(gate);}
    std::function<bool()> onDraftSaveGate,onDraftStoreReopen;
    std::string learnerHistoryExport();
    bool copyLearnerHistory();
    std::function<void(const std::string&)> onCopyLearnerHistory;
    void resized() override;
    void paint(juce::Graphics&) override;
private:
    using Intent = tasks::recipes::Intent;
    struct ReportField {
        std::string key;
        json::Value expected;
        std::unique_ptr<juce::Label> label;
        std::unique_ptr<juce::TextEditor> text;
        std::unique_ptr<juce::ToggleButton> toggle;
    };
    RecipeGesture capture(Intent) const;
    bool current(const RecipeGesture&, Intent) const;
    void command(Intent, const RecipeGesture&, bool unknown = false);
    void navigation(const RecipeGesture&, bool settings);
    void wire(RecipeTaskButton&, Intent, const char* id, const char* label, bool unknown = false);
    void clearChoices();
    void populateOrigins();
    void updateTargets(const RecipeGesture&);
    json::Value choiceReport() const;
    json::Value stepReport() const;
    void rebuildInputs();
    void render();
    std::string sourceText() const;
    std::string actionText() const;
    std::string historyText() const;
    struct Workspace {std::shared_ptr<tasks::recipes::RecipeTask> task;std::vector<std::shared_ptr<tasks::recipes::RecipeTask>> archives;json::Value fields,earlier;std::vector<std::string>notes;};
    json::Value rawFields()const;
    void restoreFields(const json::Value&);
    void retainFields();
    std::string workspaceStamp()const;
    std::function<std::string()> captureWorkspace();
    static Workspace decodeWorkspace(const SourceDraftPanel::Loaded&);
    bool installWorkspace(Workspace,const std::string&);
    void setDraftBusy(bool);
    SourceDraftPanel draftPanel_;
    bool draftBusy_{};
    json::Value::Array earlierFields_;
    std::vector<std::shared_ptr<tasks::recipes::RecipeTask>> archivedOwners_;
    std::shared_ptr<tasks::recipes::RecipeTask> task_;
    std::vector<tasks::recipes::HistoryEvent> archived_;
    std::vector<std::string> notes_;
    std::vector<json::Value> origins_, targets_;
    std::vector<ReportField> reports_;
    std::uint64_t generation_{1};
    bool navigationPrepared_{};
    std::string renderedInputs_, message_;
    juce::TextButton worksheet_{"Copy learner worksheet"};
    juce::Label heading_, phase_, status_, strokeLabel_, originLabel_, targetLabel_, planLabel_;
    ReadOnlyTextEditor source_, action_, history_;
    juce::TextEditor plan_;
    juce::ComboBox stroke_, origin_, target_;
    juce::ToggleButton releaseReport_;
    juce::Viewport inputViewport_;
    juce::Component inputBody_;
    RecipeTaskButton choose_, report_, retry_, stop_, unknown_, release_, again_, back_, settings_;
};
} // namespace fathom::desktop
