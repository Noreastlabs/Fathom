#pragma once
#include "desktop/PresentationSelector.hpp"
#include "desktop/ReadOnlyTextView.hpp"
#include "content/LessonCatalog.hpp"
#include "content/LearnSourceIndex.hpp"
#include "content/LearnSourceAdmission.hpp"
#include "content/SelectedCatalogStore.hpp"
#include "desktop/ActionButton.hpp"
#include "desktop/FretboardView.hpp"
#include "desktop/TabView.hpp"
#include "desktop/LessonSetupNotice.hpp"

namespace fathom::desktop {
class LessonPaneButton final : public juce::TextButton {
public:
    using juce::TextButton::TextButton;
    bool keyPressed(const juce::KeyPress& key) override {
        if (isShowing() && isEnabled() &&
            (key.getKeyCode() == juce::KeyPress::spaceKey ||
             key.getKeyCode() == juce::KeyPress::returnKey)) {
            triggerClick();
            return true;
        }
        return juce::TextButton::keyPressed(key);
    }
};
class LessonView final : public juce::Component {
public:
    LessonView();
    std::function<void(std::optional<presentation::Level>)> onPresentationChoice;
    void setPresentation(presentation::Level global,std::optional<presentation::Level> pageOverride){const auto level=pageOverride.value_or(global);presentation::validateLevel(level);presentationSelector_.display(global,pageOverride);presentationLevel_=level;presentSummary();renderSourceStage();}

    ~LessonView() override;
    bool load(const std::filesystem::path&,const std::filesystem::path& extension={},const std::filesystem::path& rung03={},const std::filesystem::path& rung04={},const std::filesystem::path& level006={});
    bool load(const std::filesystem::path&,const std::vector<std::filesystem::path>& installedExtensions);
    bool selectFirstAdmitted();
    bool loadSourceIndex(const std::filesystem::path&);
    bool installPreparedCatalog(std::shared_ptr<const lesson::Catalog>,const std::filesystem::path&,bool preserveSourceStage=false,bool selectedScope=false);
    bool installPreparedSourceIndex(std::shared_ptr<const learn::SourceIndex>);
    std::shared_ptr<const learn::SourceIndex> preparedSourceIndex()const{return sourceIndex_;}
    const std::filesystem::path& sourceResourceDirectory()const{return sourceResourceDirectory_;}
    void loadingStatus(const std::string&);
    void catalogPreparing(bool preparing);
    void catalogRefused(const std::string& message){catalogPreparing_=false;catalogReady_=false;catalogRefusal_=message;populateExercises();if(learnStage_==LearnStage::Case)refresh();renderSourceStage();}
    std::uint64_t sourceSelectionRevision()const{return sourceSelectionRevision_;}
    std::uint64_t sourceGroupRevision()const{return sourceGroupRevision_;}
    bool hasRetainedSourcePlan()const{return !previewRows_.empty()||exerciseQueue_!=nullptr;}
    std::function<void(const std::vector<lesson::SelectedCatalogStore::Request>&,std::uint64_t)> onPrepareSourceGroup;
    std::function<void()> onSourceGroupSelectionChanged;
    void resumeSourcePreparation(){if(learnStage_==LearnStage::Exercises&&!hasRetainedSourcePlan())prepareSourceGroup();}
    // Generic Learn resumes its source stage; explicit Browse levels opens Levels.
    void showSourceHierarchy(bool prepareIndex=true,bool browseLevels=false);
    bool sourceQueueActive() const;
    void setQueueOwnership(bool owned){queueOwned_=owned;}
    std::function<void()> onClearQueue;
    bool clearQueueSelection(){
        if(sourceQueueActive())return false;
        ++sourceSelectionRevision_;++sourceGroupRevision_;if(onSourceGroupSelectionChanged)onSourceGroupSelectionChanged();
        previewRows_.clear();previewEntries_.clear();previewVariants_.clear();exerciseQueue_.reset();sourceBpm_.setText(juce::String(defaultBpm_),false);
        sourceSublevel_.clear();sourceFirst_.setSelectedId(0,juce::dontSendNotification);sourceLast_.setSelectedId(0,juce::dontSendNotification);
        previewItems_.clear(juce::dontSendNotification);sourceVariants_.clear(juce::dontSendNotification);
        explicitSelection_=false;sourceMessage_="Queue cleared. Saved results and history are retained. Choose a level and exercises for a fresh queue.";
        sourceReturnStage_=LearnStage::Levels;sourceStage(LearnStage::Levels);return true;
    }
    void clearQueuePending(){queuePending_=false;}
    void queueStatus(const std::string& message,bool pending=false);
    void refreshQueueControls();
    std::function<bool(navigation::ExerciseQueue&,std::uint16_t,std::string&)> onQueueOpen;
    std::function<bool(std::string&)> onQueueNext, onQueueRetry;
    std::function<bool()> onQueueCanNext;
    std::function<std::string()> onQueueNextLabel,onQueueRetryLabel;
    std::function<void()> onQueueReturn;

    bool selectLesson(const std::string&,bool preserveSourceStage=false,bool explicitSelection=true);
    bool selectVariant(const std::string&,bool explicitSelection=true);
    bool hasExplicitSelection()const{return explicitSelection_;}
    bool selectPracticeCell(std::uint32_t ordinal);
    std::uint32_t selectedPracticeCell() const noexcept { return practiceCell_; }
    const std::string& selectedLesson() const noexcept { return item_; }
    const std::string& selectedVariant() const noexcept { return variant_; }
    std::shared_ptr<const lesson::Catalog> catalog() const { return catalog_; }
    bool catalogReady() const { return catalog_&&catalogReady_&&!catalogPreparing_&&catalogRefusal_.empty(); }
    bool showSourceLevel(int level);
    int sourceLevelSelection()const{return sourceLevels_.getSelectedId();}
    bool sourceHierarchyReadyForLevel(int level)const{
        return isShowing()&&sourcePanel_.isShowing()&&sourceIndex_
            &&learnStage_==LearnStage::Sublevels&&sourceLevel_==level
            &&sourceLevels_.getSelectedId()==level&&sourceSublevels_.getNumItems()>0;
    }
    void resized() override;
    void paint(juce::Graphics&) override;
    void setBackLabel(const std::string& label);
    std::function<void()> onBack;
    std::function<void()> onMetronome;
    std::function<void()> onRhythmPreview;
    std::function<void()> onAudioSettings;
    std::function<bool(std::shared_ptr<const lesson::Admission>,std::uint16_t,std::string&)> onPractice;
    std::function<bool(const std::string&)> onManualTaskAvailable;
    std::function<bool(const std::string&)> onManualTaskOpen;
    std::function<bool(const std::string&)> onManualTaskCanPrepare;
    std::function<void(const std::string&)> onManualTaskPrepare;
    std::function<std::string(const std::string& originalWorkbookId)> onBookTheoryContext;
    bool requestBookTheoryContext();
    bool requestMetronome();
    bool requestRhythmPreview();
    bool requestAudioSettings();
    std::function<bool()> localProfileAvailable;
    void setDefaultTempoValue(std::uint16_t bpm){if(bpm>=20&&bpm<=300)defaultBpm_=bpm;}
    void seedNewTempo(std::uint16_t bpm){setDefaultTempoValue(bpm);if(!hasRetainedSourcePlan()&&!sourceQueueActive()){setSelectedTempo(defaultBpm_);sourceBpm_.setText(juce::String(defaultBpm_),false);}}
    void setSelectedTempo(std::uint16_t bpm){if(bpm>=20&&bpm<=300)tempo_.setText(juce::String(bpm),false);}
    bool practiceSelected();
    bool practiceExplicitSelection(const std::string& item,const std::string& variant);
    bool selectedCaseVisibleInSearch()const noexcept;
    std::function<std::optional<guitar::Setup>()> currentSetup;
    void refreshSetup(){refresh();}
private:
    friend struct LearnNavigationTestAccess; // Observe retained queue identity in scoped navigation tests.
    ActionButton sourceClear_{"Clear queue & start fresh"};
    std::uint16_t defaultBpm_{60};
    PresentationSelector presentationSelector_;
    enum class LearnStage { Levels, Sublevels, Exercises, Preview, Queue, Case };
    LearnStage learnStage_{LearnStage::Case}, sourceReturnStage_{LearnStage::Levels};
    bool sourceDetail_{}, queuePending_{}, queueOwned_{};
    int sourceLevel_{1};
    std::string sourceSublevel_, sourceMessage_;
    std::string loadingStatus_;
    bool catalogPreparing_{};
    bool catalogReady_=true;
    std::string catalogRefusal_;
    std::uint64_t sourceSelectionRevision_{};
    std::uint64_t sourceGroupRevision_{};
    bool selectedCatalogScope_{};
    std::filesystem::path sourceResourceDirectory_;
    std::shared_ptr<const learn::SourceIndex> sourceIndex_;
    std::vector<const learn::Exercise*> previewRows_;
    std::vector<navigation::ExerciseEntry> previewEntries_;
    std::vector<navigation::AdmissionIdentity> previewVariants_;
    std::unique_ptr<navigation::ExerciseQueue> exerciseQueue_;
    juce::Component sourcePanel_;
    juce::Label sourceHeading_,sourceBreadcrumb_,sourceFirstLabel_,sourceLastLabel_,sourceTempoLabel_;
    juce::TextEditor sourceInfo_, sourceBpm_;
    juce::ComboBox sourceLevels_,sourceSublevels_,sourceMode_,sourceFirst_,sourceLast_,previewItems_,sourceVariants_;
    ActionButton sourceBack_{"Back"},sourceContinue_{"Open level"},sourcePreview_{"Preview selection"},sourceConfirm_{"Confirm queue"},sourceOpen_{"Open exercise in Practice"},sourceNext_{"Next after result resolution"},sourceRetry_{"Retry Session operation"},sourceCase_{"Exercise details"},sourceManual_{"Open exercise activity"},sourceBrowse_{"Browse levels"};
    const learn::Exercise* selectedSourceRow() const;
    void configureSourceControls();
    void sourceStage(LearnStage);
    void populateSublevels();
    void populateExercises();
    void prepareSourceGroup();
    std::string sourceAvailability(const learn::Exercise&)const;
    void buildSourcePreview();
    void refreshPreviewVariants();
    void renderSourceStage();
    std::string playerSourceMessage(std::string)const;
    void layoutSourceStage();
    std::shared_ptr<const lesson::Catalog> catalog_;
    std::string item_,variant_,diagnostic_,fullSummary_,compactSummary_,beginnerSummary_,inspectionQualifier_;
    bool explicitSelection_{};
    presentation::Level presentationLevel_{presentation::Level::Beginner};
    std::string callerBackLabel_{"Home"};
    void updateBackLabel();
    void presentInventory();
    void presentSummary(){const auto& text=presentationLevel_==presentation::Level::Beginner?beginnerSummary_:presentationLevel_==presentation::Level::Advanced?compactSummary_:fullSummary_;summary_.setText(juce::String::fromUTF8(text.c_str()),juce::dontSendNotification);updateBackLabel();presentInventory();}
    std::string approvedTheoryWorkbook_,approvedTheoryText_;
    std::vector<std::string> visibleLessonIds_;
    std::uint32_t practiceCell_{};
    bool tabVisible_=false;
    bool diagnosticsVisible_=false;
    bool compactFretboardVisible_=false;
    bool layoutWasCompact_=false;
    guitar::Handedness presentationHandedness_=guitar::Handedness::Right;
    ReadOnlyTextView summary_;
    std::string setupPrimaryNotice_;
    juce::Label title_,inventory_,selectedCaseHeading_,emptyCatalogState_,setupSummary_,searchLabel_,searchStatus_;
    juce::TextEditor setupDetails_;
    juce::TextEditor search_;
    ActionButton clearSearch_{"Clear search"};
    ActionButton setupButton_{"Setup details"};
    bool setupDetailsVisible_{};
    juce::Label tempoLabel_;
    juce::TextEditor tempo_;
    ActionButton practice_{"Practice selected case"};
    ActionButton metronome_{"Open metronome"};
    ActionButton rhythm_{"Rhythm preview"};
    ActionButton audio_{"Audio settings"};
    juce::ComboBox lessons_,variants_,sections_;
    juce::Label spanLabel_;
    juce::ComboBox spans_;
    ActionButton back_{"Back"},mode_{"View TAB"},details_{"Details"};
    LessonPaneButton compactFretboard_{"Show fretboard"};
    juce::TextEditor text_,diagnostics_;
    TabView tab_;
    FretboardView fretboard_;
    juce::Viewport fretboardViewport_;
    juce::Label fretboardHint_;
    juce::Label compactFretboardStatus_;
    void refreshLessonChoices();
    void refresh();
    void projectSelectedSourceEvent(const std::string&);
    void centerSelectedFretboardMarkers();
    std::shared_ptr<const lesson::Admission> selectedAdmission() const;
    void resetPracticeSpans();
};
}
