#pragma once
#include "desktop/ReadOnlyTextEditor.hpp"

#include "content/SourceLibraryCatalog.hpp"
#include "content/BookContextSourceCatalog.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include <functional>
#include <optional>
#include <atomic>
#include <memory>

namespace fathom::desktop {
class SourceLibraryView final : public juce::Component, private juce::ListBoxModel {
public:
    SourceLibraryView();
    void setReturnLabel(const juce::String& label){back_.setButtonText(label);back_.setTitle(label);}
    ~SourceLibraryView() override;
    // Source verification runs off the UI thread. Activity verification is an
    // explicit separate action; canceled jobs never publish data or navigate.
    using LoadTicket=std::shared_ptr<std::atomic<bool>>;
    using ActivityPreparation=std::function<std::function<void()>(const LoadTicket&)>;
    void beginBrowse(const std::filesystem::path&);
    void prepareActivity(const std::string& source,ActivityPreparation,std::function<bool()> open);
    void cancelLoading();
    bool isLoading() const noexcept { return static_cast<bool>(loadTicket_); }
    bool isPreparingActivity() const noexcept { return static_cast<bool>(activityTicket_); }
    static bool hasBackgroundWork();
    bool load(const std::filesystem::path& installedResources);
    bool loadBookContext(const std::filesystem::path& closedPackage);
    bool ensureTheoryContext(const std::filesystem::path& installedResources);
    std::string publicTheoryContext(const std::string& originalWorkbookId) const;
    bool bookContextAvailable() const noexcept { return context_.has_value(); }
    std::function<void()> onBack;
    std::function<bool(const std::string& workbookId)> onOpenInLearn;
    std::function<bool(const std::string& sourceIdentity)> onManualTaskAvailable;
    std::function<bool(const std::string& sourceIdentity)> onManualTaskOpen;
    std::function<bool(const std::string&)> onManualTaskCanPrepare;
    std::function<void(const std::string&)> onManualTaskPrepare;
    std::size_t workbookCount() const noexcept;
    void resized() override;
    void lookAndFeelChanged() override;
private:
    friend struct SourceBrowseTestAccess;
    void showLoadResult();
    void refreshSections();
    int getNumRows() override;
    void paintListBoxItem(int,juce::Graphics&,int,int,bool) override;
    juce::String getNameForRow(int) override;
    juce::String getTooltipForRow(int) override;
    void selectedRowsChanged(int) override;
    struct TaskRow { int level; std::size_t task; };
    std::vector<TaskRow> taskRows_;
    std::shared_ptr<std::atomic<bool>> loadTicket_;
    LoadTicket activityTicket_;
    std::filesystem::path loadedBrowseResources_;
    bool initializeVerifiedContext(const std::filesystem::path& installedResources);
    std::filesystem::path theoryResources_;
    bool theoryInitializationAttempted_=false;
    void refreshList();
    void selectWorkbook(bool explicitSelection=true);
    void showOriginalText();
    void refreshSourceTasks();
    void refreshSourceTaskAvailability();
    const curriculum::BookSourceTask* selectedSourceTask() const;
    const curriculum::SourceWorkbook* selectedWorkbook() const;
    std::optional<curriculum::SourceLibrary> library_;
    std::optional<curriculum::BookContextSourceCatalog> context_;
    juce::String contextStatus_;
    juce::Label title_, scope_, selection_, status_;
    int retainedWorkbookLevel_{};bool lastSearchEmpty_=true;
    juce::TextEditor search_;
    juce::TextButton clearSearch_{"Clear search"};
    ReadOnlyTextEditor text_;
    juce::ComboBox volumes_,sections_,workbooks_;
    juce::ListBox sourceTasks_;
    juce::TextButton back_, openPdf_, openLearn_, showOriginal_, showContext_, openSourceTask_;
};
} // namespace fathom::desktop
