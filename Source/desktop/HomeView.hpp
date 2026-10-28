#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

#include "desktop/GuitarSetupView.hpp"
#include "desktop/OriginalActivityRecovery.hpp"
#include "desktop/ReadOnlyTextView.hpp"
#include "desktop/PresentationPreferences.hpp"
#include "desktop/SetupPreferences.hpp"
#include "desktop/OnboardingView.hpp"
#include "desktop/Appearance.hpp"
#include "desktop/AudioOutputView.hpp"
#include "desktop/SchedulerView.hpp"
#include "desktop/ReferenceView.hpp"
#include "desktop/PracticeView.hpp"
#include "desktop/PracticeQueueHeader.hpp"
#include "desktop/ClearLearnQueuePanel.hpp"
#include "desktop/SuiteReviewView.hpp"
#include "content/ExerciseSuiteReview.hpp"
#include "desktop/MetronomeView.hpp"
#include "desktop/LessonView.hpp"
#include "content/LearnQueueCapture.hpp"
#include "desktop/ProgressView.hpp"
#include "desktop/FreeplayView.hpp"
#include "desktop/GuidedSessionView.hpp"
#include "desktop/SourceLibraryView.hpp"
#include "desktop/SourceTaskLibraries.hpp"
#include "desktop/SourceDataWorker.hpp"
#include "tasks/InstalledExtraSource17Registry.hpp"
#include "desktop/ManualTaskView.hpp"
#include "tasks/InstalledManualTaskRegistry.hpp"
#include "desktop/RecipeTaskView.hpp"
#include "tasks/InstalledRecipeTaskRegistry.hpp"
#include "desktop/AdvancedRecipeTaskView.hpp"
#include "tasks/InstalledAdvancedRecipeRegistry.hpp"
#include "desktop/CompiledManualProcedureView.hpp"
#include "desktop/EarSourceProcedureView.hpp"
#include "desktop/C43SourceProcedureView.hpp"
#include "content/Canonical.hpp"
#include <map>
#include "tasks/InstalledOrderedContactTaskRegistry.hpp"
#include "tasks/InstalledManualProcedureGraphRegistry.hpp"
#include "tasks/InstalledPhysicalContactTaskRegistry.hpp"
#include "tasks/InstalledPiecewiseContactTaskRegistry.hpp"
#include "tasks/InstalledHarmonicContactTaskRegistry.hpp"
#include "tasks/InstalledSourceContactTaskRegistry.hpp"
#include <iostream>
#include "platform/ProfileAccessMac.hpp"
#include <ctime>
#include <set>

namespace fathom::desktop {
inline std::string desktopUtcNow(){const auto now=std::time(nullptr);std::tm utc{};gmtime_r(&now,&utc);char text[32]{};std::strftime(text,sizeof(text),"%Y-%m-%dT%H:%M:%SZ",&utc);return text;}
class KeyboardButton final : public juce::TextButton {
public:
    using juce::TextButton::TextButton;
    bool keyPressed(const juce::KeyPress& key) override {
        if (key.getKeyCode() == juce::KeyPress::spaceKey || key.getKeyCode() == juce::KeyPress::returnKey) {
            triggerClick();
            return true;
        }
        return juce::TextButton::keyPressed(key);
    }
};

class HomeView final : public juce::Component, private juce::Timer, private SourceTaskLibraries {
public:
    bool configureCapture(fathom::storage::ProfileStore& store,const std::string& session,const std::string& zone){
        if(learnQueue_||learnFuture_||learnMutation_!=LearnMutation::None||(learnSuite_&&!suiteReviewSaved_))return false;
        if(progressView.busy())return false;
        if(!practiceView->configureCapture(store,session,desktopUtcNow,zone)||!freeplayView.configureStore(store,desktopUtcNow,zone)||!guidedView.configureStore(store,desktopUtcNow,zone)||!(metronomeView.configureStore(store)||metronomeView.rebindStore(store)))return false;
        guidedView.setCatalog(lessonView.catalog());
        if(!progressView.bind(store,desktopUtcNow))return false;
        if(page_==Page::Progress)progressView.refresh();
        if(!originalRecovery_.attach(store))return false;
        learnStore_=&store;learnTimezone_=zone;learnPreviewSession_=session;
        learnOperation_="learn-suite/discover/"+storage::newUuid();learnMutation_=LearnMutation::ReadSuite;
        std::string suiteReason;submitLearnMutation(suiteReason);
        profileStatus_.clear();update();
        return true;
    }
    bool attachPresentation(storage::ProfileStore& store,const std::string& profileIdentity){
        if(!advancedRecipeTaskView.canAttachDraftStore(profileIdentity)||!manualTaskView.canAttachDraftStore(profileIdentity)||!recipeTaskView.canAttachDraftStore(profileIdentity)||!earSourceProcedureView.canAttachDraftStore(profileIdentity)||!c43SourceProcedureView.canAttachDraftStore(profileIdentity))return false;
        const bool preserveExplicitLevel=!presentation_.hasProfile()&&presentation_.dirty();
        const auto explicitLevel=presentation_.model().globalLevel();
        const bool presentationAttached=presentation_.attach(store,profileIdentity);
        if(preserveExplicitLevel)presentation_.chooseGlobal(explicitLevel);
        if(!presentationAttached)return false;
        if(!setupPreferences_.attach(store,profileIdentity))return false;
        if(!compiledManualProcedureView.attachDraftStore(store,profileIdentity))return false;
        if(!advancedRecipeTaskView.attachDraftStore(store,profileIdentity)||!manualTaskView.attachDraftStore(store,profileIdentity)||!recipeTaskView.attachDraftStore(store,profileIdentity)||!earSourceProcedureView.attachDraftStore(store,profileIdentity)||!c43SourceProcedureView.attachDraftStore(store,profileIdentity))return false;
        boardSaveRequested_=false;setupRestorePending_=true;
        applyPresentation();return true;
    }
    void setLocalProfileLabel(const std::string& id,const std::string& name,const std::filesystem::path& file){profileSummary_="Profile: "+name+"\nProfile ID: "+id+"\nRecovery file: "+file.string();originalRecovery_.setProfileIdentity(id,name,file);}
    const setup::Model& setupModel()const noexcept{return setupPreferences_.model();}
    std::function<void(setup::Appearance)> onAppearanceChanged;
    void beginInitialSetup(){
        if(!setupPreferences_.hasProfile()){
            auto model=setupPreferences_.model();model.experience=presentation_.model().globalLevel();
            model.guitar=setup.currentSetup();model.audio=audio_.selected();if(model!=setupPreferences_.model())setupPreferences_.choose(model);
        }
        page_=Page::Onboarding;refreshOnboarding();update();
    }
    void resumeInitialSetup(const setup::Model& model){
        setupPreferences_.choose(model);presentation_.chooseGlobal(model.experience);
        setupOwnerRestoreHeld_=!setup.applySetup(model.guitar)||!audio_.selectMix(model.audio);
        if(setupOwnerRestoreHeld_)setupNotice_="Retained guitar/audio draft is waiting for safe application. Review those settings before saving.";
        applyBoardDisplay();applyPresentation();applySetupAppearance();page_=Page::Onboarding;refreshOnboarding();update();
    }
    void localProfileOpening(bool opening){localProfileOpening_=opening;if(opening){setupNotice_="Opening your private local profile… Existing activity and setup choices remain owned.";profileStatus_=setupNotice_;}else if(setupNotice_.find("Opening your private local profile") == 0){setupNotice_.clear();profileStatus_.clear();}refreshOnboarding();update();}
    bool canOpenLocalProfile()const{return !localProfileOpening_&&!presentation_.hasProfile()&&!setupPreferences_.hasProfile()&&presentationStoppedAndResolved()&&presentation_.canDetach()&&setupPreferences_.canDetach();}
    bool openSetupWizard(){
        if(!presentationStoppedAndResolved())return false;
        auto model=setupPreferences_.model();model.experience=presentation_.model().globalLevel();
        model.guitar=setup.currentSetup();model.audio=audio_.selected();
        model.completed=false;model.skipped=false;
        if(model.step==setup::Step::Summary)model.step=setup::Step::Welcome;
        setupPreferences_.choose(model);page_=Page::Onboarding;refreshOnboarding();update();return true;
    }
    bool presentationStoppedAndResolved() const {
        // Home is reached through each manual renderer's native release gate.
        // This query never stops playback, acknowledges debt or writes a profile.
        return !originalRecovery_.held()&&!setupOwnerRestoreHeld_&&!localProfileOpening_&&(page_==Page::Home||page_==Page::About||page_==Page::Settings||page_==Page::UserProfile||page_==Page::Onboarding)&&!learnQueue_&&!learnFuture_&&
            learnMutation_==LearnMutation::None&&!progressView.busy()&&
            freeplayView.presentationStoppedAndResolved()&&guidedView.presentationStoppedAndResolved()&&
            practiceView->audioCanRelease()&&metronomeView.audioCanRelease()&&
            referenceView.audioCanRelease()&&scheduleView.audioCanRelease()&&
            !metronomeView.preferencesPending()&&!manualTaskView.clockActive()&&!manualTaskView.pulsePreparing();
    }
    bool manualDraftSaveGate()const{
        return !localProfileOpening_&&!originalRecovery_.busy()&&!learnQueue_&&!learnFuture_&&learnMutation_==LearnMutation::None&&
            !progressView.busy()&&freeplayView.presentationStoppedAndResolved()&&guidedView.presentationStoppedAndResolved()&&
            practiceView->audioCanRelease()&&metronomeView.audioCanRelease()&&referenceView.audioCanRelease()&&scheduleView.audioCanRelease()&&
            !metronomeView.preferencesPending()&&!presentation_.pending()&&!setupPreferences_.pending()&&!manualTaskView.clockActive()&&!manualTaskView.pulsePreparing();
    }
    const presentation::Model& presentationModel()const{return presentation_.model();}
    std::function<bool()> onReopenStore;
    std::function<bool()> onOpenLocalProfile, onOpenExistingLocalProfile;
    std::function<bool(const std::string&)> onCreateLocalProfile;
    void localProfileFailed(const std::string& reason){const bool selectedTask=profileCase_.has_value();profileCase_.reset();profileStatus_="Local profile unavailable: "+reason;setupFinish_=SetupFinish::Idle;setupNotice_=profileStatus_;if(selectedTask&&!practiceView->captureSession())page_=Page::Learn;refreshOnboarding();update();}
    void storeReopenFailed(const std::string& reason){metronomeView.storeReopenFailed(reason);progressView.unavailable(reason);}
    bool detachForStoreReopen(){
        if(originalRecovery_.busy())return false;
        if(!presentation_.canDetach()||!setupPreferences_.canDetach()||compiledManualProcedureView.draftBusy()||advancedRecipeTaskView.draftJobBusy()||manualTaskView.draftJobBusy()||recipeTaskView.draftJobBusy()||earSourceProcedureView.draftJobBusy()||c43SourceProcedureView.draftJobBusy())return false;
        if(!prepareManualNavigation(true))return false;
        if(learnQueue_||learnFuture_||learnMutation_!=LearnMutation::None)return false;
        if(progressView.busy())return false;
        if(freeplayView.closeState()!=FreeplayView::CloseState::Ready)return false;
        if(!guidedView.canLeave())return false;
        audio_.invalidatePreparation();
        if(!practiceView->requestClose()||!audio_.disconnect()||!metronomeView.prepareStoreReopen())return false;
        if(!progressView.detach())return false;
        if(!advancedRecipeTaskView.detachDraftStore()||!manualTaskView.detachDraftStore()||!recipeTaskView.detachDraftStore()||!compiledManualProcedureView.detachDraftStore()||!earSourceProcedureView.detachDraftStore()||!c43SourceProcedureView.detachDraftStore())return false;
        presentation_.detach();setupPreferences_.detach();boardSaveRequested_=false;setupRestorePending_=false;
        learnStore_=nullptr;learnTimezone_.clear();learnPreviewSession_.clear();learnSuite_.reset();suiteQueue_=nullptr;lessonView.setQueueOwnership(false);suiteContinuation_=SuiteContinuation::None;
        practiceView->visitAudioSettings();removeChildComponent(practiceView.get());practiceView=std::make_unique<PracticeView>();
        wirePractice();addChildComponent(*practiceView);resized();update();return true;
    }
    enum class CloseState { Ready, Waiting, Held };
    CloseState closeState() const noexcept { return closeState_; }
    const std::string& closeStatus() const noexcept { return closeStatus_; }
    void retryExitDiscard(){practiceView->retryExitDiscard();freeplayView.retryExitDiscard();if(learnMutation_!=LearnMutation::None&&!learnFuture_){std::string reason;retryLearnQueue(reason);}}
    void cancelExit(){if(page_==Page::CompiledManualProcedure)compiledManualProcedureView.cancelDraftClose();guidedView.cancelExit();practiceView->cancelExit();freeplayView.cancelExit();quitSetupSubmitted_=false;quitPresentationSubmitted_=false;quitLearnRetrySubmitted_=false;}
    bool requestExit(bool discard){
        if(originalRecovery_.busy()){closeState_=CloseState::Waiting;closeStatus_="Waiting for original recovery operation; no new activity.";return false;}
        // Never auto-advance or attach a new exercise during the selected quit.
        suiteContinuation_=SuiteContinuation::None;suiteAutoAdvanceAllowed_=false;
        closeState_=CloseState::Waiting;closeStatus_="Stopping and resolving the current result before Quit.";
        if(!practiceView->requestExit(discard))return false;
        if(discard){
            boardSaveRequested_=false;
            if(learnFuture_||presentation_.inFlight()||setupPreferences_.inFlight())return false;
            // Retain queue/Session/suite and persisted preferences for recovery.
        }
        if(!freeplayView.requestExit(discard)||!guidedView.requestExit(discard))return false;
        if(!discard){
            if(learnMutation_!=LearnMutation::None&&!learnFuture_&&!quitLearnRetrySubmitted_){quitLearnRetrySubmitted_=true;std::string reason;retryLearnQueue(reason);}
            // An accepted reader/operation is transient ownership, not a failed save receipt.
            if(learnFuture_||progressView.busy()||setupPreferences_.inFlight()||presentation_.inFlight()||metronomeView.preferenceInFlight()){
                closeState_=CloseState::Waiting;closeStatus_="Waiting for the original accepted operations before saving setup and presentation.";return false;
            }
            // Retained stopped Learn ownership is closed using the existing exact
            // resolution before preferences require a queue-free stopped gate.
            // No next exercise is opened: exit already disabled auto-continuation.
            if(learnQueue_&&!learnSuite_){
                if(!practiceView->requestClose()){closeState_=CloseState::Held;closeStatus_="Save or resolve the original Practice result before closing its Learn Session.";return false;}
                std::string reason;
                if(canAdvanceLearnQueue()&&advanceLearnQueue(reason)){closeStatus_="Closing the original Learn Session before saving preferences.";return false;}
                closeState_=CloseState::Held;closeStatus_=reason.empty()?"Resolve the original Learn Session before saving preferences.":reason;return false;
            }
            if(setupPreferences_.hasProfile()&&setupPreferences_.dirty()){
                if(!quitSetupSubmitted_&&setupPreferences_.canSave(presentationStoppedAndResolved())){quitSetupSubmitted_=true;setupPreferences_.save(true);}
                if(setupPreferences_.inFlight())return false;
                if(setupPreferences_.dirty()){closeState_=CloseState::Held;closeStatus_="Setup save was not confirmed. Keep the app open and retry the original save.";return false;}
            }
            if(presentation_.hasProfile()&&presentation_.dirty()){
                if(!quitPresentationSubmitted_&&presentation_.canSave(presentationStoppedAndResolved())){quitPresentationSubmitted_=true;presentation_.save(true);}
                if(presentation_.inFlight())return false;
                if(presentation_.dirty()){closeState_=CloseState::Held;closeStatus_="Presentation save was not confirmed.";return false;}
            }
        }
        if(!discard&&learnSuite_&&!learnQueue_&&!suiteReviewSaved_){
            if(!learnFuture_&&learnMutation_==LearnMutation::None)submitFinalSuiteReview(nullptr);
            if(!suiteReviewSaved_)return false;
        }
        return requestClose(discard);
    }
    bool requestClose(bool exitDiscard=false){
        if(originalRecovery_.busy())return false;
        suiteContinuation_=SuiteContinuation::None;suiteAutoAdvanceAllowed_=false;
        closeState_=CloseState::Held;closeStatus_.clear();
        const auto waiting=[this](const std::string& message){closeState_=CloseState::Waiting;closeStatus_=message;return false;};
        const auto held=[this](const std::string& message){closeStatus_=message;return false;};
        pendingLearnEntry_=false;
        cancelLearnLoading();sourceLibraryView.cancelLoading();sourceCloseStatus_.clear();
        if(setupFinish_!=SetupFinish::Idle){setupFinish_=SetupFinish::Idle;setupNotice_="Setup completion interrupted by Quit. Confirmed drafts remain saved; completion is not assumed.";}
        if(!presentation_.canDetach()){
            if(presentation_.inFlight())return waiting("Waiting for the original presentation operation…");
            return held("Check the original presentation save on Home. Its unresolved operation is retained.");
        }
        if(!setupPreferences_.canDetach()){
            if(setupPreferences_.inFlight())return waiting("Waiting for the original setup operation…");
            page_=Page::Onboarding;refreshOnboarding();update();
            return held("Check the original setup save. Its unresolved operation is retained.");
        }
        if(advancedRecipeTaskView.draftJobBusy()||manualTaskView.draftJobBusy()||recipeTaskView.draftJobBusy()||earSourceProcedureView.draftJobBusy()||c43SourceProcedureView.draftJobBusy())return waiting("Waiting for the original source draft operation.");
        if(advancedRecipeTaskView.draftPending()||manualTaskView.draftPending()||recipeTaskView.draftPending()||earSourceProcedureView.draftPending()||c43SourceProcedureView.draftPending())return held("Check the original source draft save before closing. Its operation remains retained.");
        if(compiledManualProcedureView.draftBusy())return waiting("Waiting for the original manual draft operation.");
        if(compiledManualProcedureView.draftPending())return held("Check the original manual draft save before closing. The original operation is retained.");
        if(!prepareManualNavigation())return held("Resolve the current source activity and sound-check release before quitting.");
        if(!exitDiscard&&!compiledManualProcedureView.saveDraftsForClose(manualDraftSaveGate()))return compiledManualProcedureView.draftBusy()?waiting("Saving retained manual drafts before closing."):held("Manual drafts are not confirmed saved. Keep open and resolve the original save.");
        if(!exitDiscard&&!earSourceProcedureView.saveDraftsForClose(manualDraftSaveGate()))return earSourceProcedureView.draftJobBusy()?waiting("Saving retained listening drafts before closing."):held("Listening drafts are not confirmed saved. Keep open and check the original save.");
        if(!exitDiscard&&!advancedRecipeTaskView.saveDraftsForClose(manualDraftSaveGate()))return advancedRecipeTaskView.draftJobBusy()?waiting("Saving retained advanced drafts before closing."):held("Advanced drafts are not confirmed saved. Keep open and check the original save.");
        if(!exitDiscard&&!manualTaskView.saveDraftsForClose(manualDraftSaveGate()))return manualTaskView.draftJobBusy()?waiting("Saving retained manual-guide drafts before closing."):held("Manual-guide drafts are not confirmed saved. Keep open and check the original save.");
        if(!exitDiscard&&!recipeTaskView.saveDraftsForClose(manualDraftSaveGate()))return recipeTaskView.draftJobBusy()?waiting("Saving retained recipe drafts before closing."):held("Recipe drafts are not confirmed saved. Keep open and check the original save.");
        if(!exitDiscard&&!c43SourceProcedureView.saveDraftsForClose(manualDraftSaveGate()))return c43SourceProcedureView.draftJobBusy()?waiting("Saving retained contextual drafts before closing."):held("Contextual drafts are not confirmed saved. Keep open and check the original save.");
        if(learnFuture_)return waiting("Waiting for the original Learn Session operation…");
        if(learnMutation_!=LearnMutation::None){
            lessonView.queueStatus("Retry the original Learn Session operation before quitting.");page_=Page::Learn;update();
            return held("The original Learn Session operation needs reconciliation.");
        }
        if(learnQueue_&&!exitDiscard){
            if(!exitDiscard&&!practiceView->requestClose()){page_=Page::Practice;update();return held("Save or resolve the retained Practice result before quitting.");}
            // The existing close contract records partial for a saved result, or
            // cancelled for a prepared exercise that never started. It never
            // fabricates task completion, an Attempt, or a new exercise launch.
            std::string reason;
            if(canAdvanceLearnQueue()&&advanceLearnQueue(reason))return waiting("Closing the original Learn Session…");
            lessonView.queueStatus(reason.empty()?"Resolve the original Learn Session before quitting.":reason);page_=Page::Learn;update();
            return held("The original Learn Session remains open; resolve it before quitting.");
        }
        if(!exitDiscard&&!practiceView->requestClose()){page_=Page::Practice;update();return held("Save or resolve the retained Practice result before quitting.");}
        if(!metronomeView.requestClose()){
            if(metronomeView.preferenceInFlight()&&!metronomeView.soundPending())return waiting("Waiting for the original timing preference operation…");
            page_=Page::Metronome;update();return held("Finish the sound check or reconcile its original preference operation.");
        }
        if(!referenceView.requestClose()){page_=Page::Reference;update();return held("Reference Stop was requested; finish its retained sound check before quitting.");}
        if(!scheduleView.requestClose()){page_=Page::Rhythm;update();return held("Rhythm Stop was requested; finish its retained sound check before quitting.");}
        if(progressView.busy())return waiting("Waiting for the current history read…");
        if(!exitDiscard&&!freeplayView.requestClose()){
            if(freeplayView.closeState()==FreeplayView::CloseState::Pending)return waiting("Saving the stopped Freeplay recording…");
            page_=Page::Freeplay;update();return held("Freeplay history is unresolved. Its duration and original save are retained.");
        }
        if(!exitDiscard&&guidedView.busy())return waiting("Waiting for the original Guided Session operation…");
        if(!exitDiscard&&!guidedView.canClose()){page_=Page::Guided;update();return held(guidedView.createUnresolved()?"Check the original Guided start before quitting; its Session identity is retained.":"Finish or explicitly interrupt the current Guided Session before quitting.");}
        if(SourceLibraryView::hasBackgroundWork())return waiting("Finishing cancelled source verification…");
        closeState_=CloseState::Ready;return true;
    }
    ~HomeView() override { cancelLearnLoading();stopTimer(); }
    enum class Page { Home,About,Onboarding,Setup,Audio,Rhythm,Reference,Practice,Metronome,Learn,ManualTask,Progress,Freeplay,Guided,SourceLibrary,RecipeTask,AdvancedRecipeTask,CompiledManualProcedure,EarSourceProcedure,C43SourceProcedure,SuiteReview,Settings,UserProfile,FreeplayMenu };
    Page page()const noexcept{return page_;}
    Page settingsCaller()const noexcept{return settingsCaller_;}
    SharedAudioSettings& audioSettings() noexcept{return audio_;}
    void openAudioSettings(){
        if(page_==Page::Audio)return;
        if(!prepareManualNavigation())return;
        pendingLearnEntry_=false;
        cancelLearnLoading();
        if(page_==Page::SourceLibrary)sourceLibraryView.cancelLoading();
        settingsCaller_=page_;settingsFocus_=juce::Component::getCurrentlyFocusedComponent();
        practiceView->visitAudioSettings();
        page_=Page::Audio;outputView.setReturnLabel("Back to "+pageName(settingsCaller_));update();
    }
    void returnFromAudioSettings(){
        if(page_!=Page::Audio)return;
        if(settingsCaller_==Page::Onboarding)captureSetupOwners();
        page_=settingsCaller_;if(page_==Page::ManualTask)manualTaskView.resumeAfterNavigation();if(page_==Page::RecipeTask)recipeTaskView.resumeAfterNavigation();if(page_==Page::AdvancedRecipeTask)advancedRecipeTaskView.resumeAfterNavigation();if(page_==Page::CompiledManualProcedure)compiledManualProcedureView.resumeAfterNavigation();if(page_==Page::EarSourceProcedure)earSourceProcedureView.resumeAfterNavigation();if(page_==Page::C43SourceProcedure)c43SourceProcedureView.resumeAfterNavigation();update();
        if(settingsFocus_&&settingsFocus_->isShowing()&&settingsFocus_->getWantsKeyboardFocus())settingsFocus_->grabKeyboardFocus();
        settingsFocus_=nullptr;
        if(page_==Page::Onboarding){saveSetupDraft();refreshOnboarding();}
    }
    bool navigate(Page target){
        if(clearQueuePanel_.isVisible()||clearQueueRequested_)return false;
        if(originalRecovery_.held()&&target!=Page::UserProfile&&target!=Page::Home&&target!=Page::About)return false;
        if(target==Page::Guided&&!canReviewGuidedOriginal())return false;
        if(canReviewGuidedOriginal()&&target!=Page::Guided&&target!=Page::Home&&target!=Page::UserProfile&&target!=Page::Settings&&target!=Page::About&&target!=Page::Progress&&target!=Page::Audio)return false;
        if(learnSuite_&&!suiteReviewSaved_&&target!=Page::Learn&&target!=Page::Practice&&target!=Page::Audio&&target!=Page::Progress&&target!=Page::SuiteReview&&target!=Page::Settings&&target!=Page::UserProfile&&target!=Page::About){lessonView.queueStatus("Finish the current suite or its final review before opening another activity.");return false;}
        if((target==Page::Settings||target==Page::UserProfile||target==Page::About)&&(!practiceView->audioCanRelease()||!audio_.canRelease()))return false;
        if(target!=page_&&!prepareManualNavigation())return false;
        if(learnFuture_&&target!=Page::Learn){lessonView.queueStatus("Wait for or retry the original Learn Session operation before leaving this screen.",learnFuture_.has_value());return false;}
        if((learnQueue_||learnFuture_||learnMutation_!=LearnMutation::None)&&target!=Page::Learn&&target!=Page::Practice&&target!=Page::Audio&&target!=Page::Progress&&target!=Page::Settings&&target!=Page::UserProfile&&target!=Page::About){lessonView.queueStatus("Resolve the current Learn Session before opening another activity.",learnFuture_.has_value());return false;}
        if(target==Page::Metronome&&page_!=Page::Metronome){metronomeReturnPage_=page_;metronomeView.setReturnLabel("Back to "+pageName(page_));}
        if(target==Page::Rhythm&&page_!=Page::Rhythm){rhythmReturnPage_=page_;scheduleView.setReturnLabel("Back to "+pageName(page_));}
        if(target==Page::Progress){
            if(!practiceView->audioCanRelease()||!metronomeView.audioCanRelease()||!referenceView.audioCanRelease()||!scheduleView.audioCanRelease())return false;
            progressView.setCatalog(lessonView.catalog());
            if(!progressView.busy())progressView.refresh();
        }
        if(target==Page::Audio){openAudioSettings();return true;}
        std::optional<SharedAudioSettings::Consumer> consumer;
        if(target==Page::Practice&&learnMutation_==LearnMutation::None)consumer=SharedAudioSettings::Consumer::Practice;
        if(target==Page::Metronome)consumer=SharedAudioSettings::Consumer::Metronome;
        if(target==Page::Reference)consumer=SharedAudioSettings::Consumer::Reference;
        if(target==Page::Rhythm)consumer=SharedAudioSettings::Consumer::Rhythm;
        if(consumer&&!audio_.activate(*consumer)){
            // Failure keeps the original owner reachable; settings is a reversible detour.
            openAudioSettings();return false;
        }
        if(target==Page::Learn)lessonView.refreshSetup();
        if(target==Page::Progress&&page_!=Page::Progress)progressReturnPage_=page_;
        if(target==Page::Reference&&page_!=Page::Reference)referenceReturnPage_=page_;
        if(target==Page::Guided&&guidedView.newSessionsEnabled()){
            guidedView.setCatalog(lessonView.catalog());
            const bool selectedCase=lessonView.catalogReady()&&lessonView.hasExplicitSelection();
            guidedView.selectCase(selectedCase?lessonView.selectedLesson():std::string{},selectedCase?lessonView.selectedVariant():std::string{});
        }
        if(target==Page::Practice)practiceView->updateDeclaredSetup(setup.currentSetup());
        if(page_==Page::SourceLibrary&&target!=Page::SourceLibrary)sourceLibraryView.cancelLoading();
        if(learnLoadTicket_&&target!=learnLoadingPage_)cancelLearnLoading();
        if(target!=Page::Home)pendingLearnEntry_=false;
        if(page_==Page::Practice&&target==Page::Home)practiceView->cancelReturnForNavigation();
        if(target!=Page::Home&&target!=Page::Onboarding)profileCase_.reset();
        page_=target;update();if(getPeer()!=nullptr){if(target==Page::Settings)presentationChoice_.grabKeyboardFocus();if(target==Page::UserProfile)progressButton.grabKeyboardFocus();if(target==Page::FreeplayMenu)freeplaySessionButton_.grabKeyboardFocus();}return true;
    }
    bool requestHome(std::string& reason){
        if(clearQueuePanel_.isVisible()||clearQueueRequested_){reason="Finish or cancel the queue reset confirmation first.";return false;}
        auto held=[&](const char* text){reason=text;homeRouteStatus_.setText(juce::String::fromUTF8(text),juce::dontSendNotification);return false;};
        if(page_==Page::Onboarding||page_==Page::Setup)return held("Use Back or the existing setup action to retain your draft before Home.");
        if(learnFuture_||learnMutation_!=LearnMutation::None)return held("Wait for or resolve the original Learn operation before Home.");
        if(!practiceView->audioCanRelease()||!audio_.canRelease())return held("Use Stop and the existing Save / return controls to resolve the current result before Home. Nothing was discarded.");
        if(!freeplayView.canLeave()||!guidedView.canClose())return held("Finish or resolve the current Freeplay / Guided session before Home. The original session is retained.");
        if(!prepareManualNavigation())return held("Resolve the current source activity using its existing controls before Home.");
        const bool retained=learnQueue_||learnSuite_;
        if(retained){
            // A stopped detour preserves all durable queue/Session facts.
            suiteContinuation_=SuiteContinuation::None;suiteAutoAdvanceAllowed_=false;
            homeLearnDetour_=true;pendingLearnEntry_=false;practiceView->cancelReturnForNavigation();page_=Page::Home;update();
        }else if(!navigate(Page::Home))return held("Resolve the current page using its existing controls before Home.");
        reason.clear();homeRouteStatus_.setText({},juce::dontSendNotification);return true;
    }
    juce::Rectangle<int> homeRouteBounds() const noexcept { return homeRoute_.getBounds(); }
    juce::Rectangle<int> childPageBounds() const noexcept { return getLocalBounds().withTrimmedTop(page_==Page::Home||page_==Page::About?0:64); }
    HomeView() {
        guidedView.setNewSessionsEnabled(false);
        originalRecovery_.onBack=[this]{refreshOnboarding();update();};
        addChildComponent(originalRecovery_);
        addChildComponent(practiceQueueHeader_);addChildComponent(suiteReviewView_);
        suiteReviewView_.onSubmit=[this](json::Value score){submitFinalSuiteReview(std::move(score));};
        suiteReviewView_.onRetry=[this]{std::string reason;retryLearnQueue(reason);};
        suiteReviewView_.onBack=[this]{if(suiteReviewSaved_){learnSuite_.reset();suiteQueue_=nullptr;lessonView.setQueueOwnership(false);suiteReviewSaved_=false;suiteCompletedCount_=0;practiceView->setSuiteMode(false);navigate(Page::Home);}};
        heading.setText("Fathom", juce::dontSendNotification);
        heading.setFont(juce::FontOptions{38.0f, juce::Font::bold});
        subtitle.setText("OFFLINE MACOS DEVELOPMENT PREVIEW", juce::dontSendNotification);
        subtitle.setColour(juce::Label::textColourId, juce::Colour{0xff6bd5cb});
        message.setFont(juce::FontOptions{18.0f});
        message.setComponentID("home-guidance");
        message.setTitle("Read-only Home navigation guidance and product boundary.");
        message.setJustificationType(juce::Justification::topLeft);
        detail.setFont(juce::FontOptions{14.0f});
        detail.setComponentID("home-preview-inventory");
        detail.setTitle("Read-only Development Preview inventory and shared Audio scope.");
        detail.setColour(juce::Label::textColourId, juce::Colour{0xffa9bbc5});
        detail.setJustificationType(juce::Justification::topLeft);
        for (auto* label : {&heading, &subtitle, &learnPracticeLabel, &activitiesLabel, &audioToolsLabel}) addAndMakeVisible(*label);
        addAndMakeVisible(message);addChildComponent(detail);
        presentationChoice_.addItem("Beginner",1);presentationChoice_.addItem("Advanced",2);presentationChoice_.addItem("Developer",3);
        presentationChoice_.setComponentID("presentation-global");presentationChoice_.setTitle("Global presentation level. Disclosure only; Developer adds no permissions.");
        presentationChoice_.onChange=[this]{if(consumePresentationChoice())applyPresentation();};
        presentationSave_.onClick=[this]{consumePresentationChoice();presentation_.save(presentationStoppedAndResolved());applyPresentation();};
        presentationReset_.onClick=[this]{presentation_.resetPresentation();syncPresentationChoice();applyPresentation();};
        presentationReload_.onClick=[this]{syncPresentationChoice();presentation_.reload();applyPresentation();};
        previewDetails_.setComponentID("home-preview-details");
        previewDetails_.onClick=[this]{if(page_!=Page::Settings)return;aboutReturnPage_=Page::Settings;navigate(Page::About);};
        for(auto* c:std::initializer_list<juce::Component*>{&presentationChoice_,&presentationSave_,&presentationReset_,&presentationReload_,&presentationStatus_,&previewDetails_})addAndMakeVisible(*c);
        presentationStatus_.setFont(juce::FontOptions{14.0f});presentationStatus_.setTitle("Presentation setting save status. Unresolved original saves remain owned.");
        presentationSave_.setTitle("Save global presentation to this profile only while activities are stopped and resolved.");
        presentationReset_.setTitle("Reset presentation to Beginner and clear session page overrides. Zoom reset is separate; Save explicitly to persist.");
        presentationReload_.setTitle("Reload saved presentation or inspect the original uncertain save without issuing a replacement write.");
        for (auto* label : {&learnPracticeLabel, &activitiesLabel, &audioToolsLabel}) {
            label->setFont(juce::FontOptions{13.0f, juce::Font::bold});
            label->setColour(juce::Label::textColourId, juce::Colour{0xff6bd5cb});
        }
        learnPracticeLabel.setText(juce::String::fromUTF8("LEARN & PRACTICE — SOURCE-BACKED PREVIEW"), juce::dontSendNotification);
        activitiesLabel.setText(juce::String::fromUTF8("ACTIVITIES — LOCAL SAVED ACTIVITY"), juce::dontSendNotification);
        audioToolsLabel.setText(juce::String::fromUTF8("AUDIO & TOOLS — SHARED AUDIO"), juce::dontSendNotification);
        about.setButtonText("About this preview");
        about.setTitle("About this preview");
        about.setExplicitFocusOrder(1);
        addChildComponent(homeRoute_);addChildComponent(homeRouteStatus_);
        homeRoute_.setComponentID("global-home-route");homeRoute_.setTitle("Return Home while retaining unresolved activity and Learn ownership.");
        homeRoute_.setExplicitFocusOrder(1);
        homeRouteStatus_.setFont(juce::FontOptions{13.0f});homeRouteStatus_.setJustificationType(juce::Justification::centredLeft);
        homeRoute_.onClick=[this]{std::string reason;requestHome(reason);};
        about.onClick = [this] {if(page_==Page::About){if(aboutReturnPage_==Page::Home){std::string reason;requestHome(reason);}else navigate(aboutReturnPage_);}else{aboutReturnPage_=Page::Home;navigate(Page::About);} };
        quit.setButtonText("Quit");
        quit.setExplicitFocusOrder(2);
        quit.onClick = [] { juce::JUCEApplication::getInstance()->systemRequestedQuit(); };
        addAndMakeVisible(about);
        addAndMakeVisible(quit);
        localProfileButton.setButtonText("Open existing profile");
        onboardingButton_.setButtonText("Setup / resume setup");
        onboardingButton_.setComponentID("home-onboarding");onboardingButton_.setTitle("Review or resume initial setup; no activity or audio starts.");onboardingButton_.setWantsKeyboardFocus(true);onboardingButton_.setExplicitFocusOrder(16);
        onboardingButton_.onClick=[this]{openSetupWizard();};addAndMakeVisible(onboardingButton_);
        addChildComponent(onboarding_);
        onboarding_.onModelChanged=[this](setup::Model model){
            if(originalRecovery_.held()||localProfileOpening_)return;
            const bool changedBoard=model.boardDisplay!=setupPreferences_.model().boardDisplay;
            const bool changedLevel=model.experience!=setupPreferences_.model().experience;
            setupPreferences_.choose(std::move(model));if(changedLevel)presentation_.chooseGlobal(setupPreferences_.model().experience);
            applyBoardDisplay();if(changedBoard)requestBoardSave();
            applyPresentation();applySetupAppearance();refreshOnboarding();
        };
        onboarding_.onProfileNameChanged=[this](std::string name){if(!originalRecovery_.held()&&!localProfileOpening_)newProfileName_=std::move(name);};
        onboarding_.onNext=[this]{if(originalRecovery_.held()||localProfileOpening_)return;if(setupPreferences_.model().step==setup::Step::Welcome&&!setupPreferences_.hasProfile()){try{newProfileName_=storage::profile_names::normalize(onboarding_.profileName());}catch(const std::exception& e){setupNotice_=e.what();refreshOnboarding();return;}setupCreatingProfile_=true;}moveSetupStep(1);};onboarding_.onBack=[this]{moveSetupStep(-1);};
        onboarding_.onSkip=[this]{skipSetup();};onboarding_.onFinish=[this]{finishSetup();};
        onboarding_.onOpenLocalProfile=[this]{if(originalRecovery_.held()||localProfileOpening_)return;setupCreatingProfile_=false;if(!setupPreferences_.hasProfile()&&onOpenExistingLocalProfile)onOpenExistingLocalProfile();};
        onboarding_.onResumeRecovery=[this]{if(originalRecovery_.resumePresentation()){refreshOnboarding();update();}};
        onboarding_.onReload=[this]{if(originalRecovery_.held())return;if(!setupPreferences_.inFlight()&&!presentation_.inFlight()){setupFinish_=SetupFinish::Idle;boardSaveRequested_=false;setupPreferences_.reload();presentation_.reload();setupRestorePending_=true;refreshOnboarding();}};
        onboarding_.onOpenGuitar=[this]{guitarSetupCaller_=Page::Onboarding;setup.setDraft(setupPreferences_.model().guitar);setup.setBoardDisplay(setupPreferences_.model().boardDisplay);navigate(Page::Setup);};
        onboarding_.onOpenAudio=[this]{openAudioSettings();};
        localProfileButton.onClick=[this]{
            if(originalRecovery_.held()){originalRecovery_.resumePresentation();return;}
            if(!canOpenLocalProfile()){localProfileFailed("Stop and resolve the current activity before opening a profile. Retained activity stays available.");return;}
            if(!onOpenLocalProfile){localProfileFailed("Profile service is unavailable.");return;}
            if(onOpenLocalProfile())update();
        };
        addAndMakeVisible(localProfileButton);
        setupButton.setButtonText("Guitar setup");
        setupButton.onClick = [this] {if(!presentationStoppedAndResolved())return;guitarSetupCaller_=Page::UserProfile;navigate(Page::Setup); };
        setup.onBack = [this] {if(guitarSetupCaller_==Page::Onboarding)captureSetupOwners();if(navigate(guitarSetupCaller_)&&guitarSetupCaller_==Page::Onboarding)saveSetupDraft(); };
        setup.canApply=[this]{return practiceView->audioCanRelease()&&metronomeView.audioCanRelease()&&referenceView.audioCanRelease()&&scheduleView.audioCanRelease();};
        setup.onApplied=[this]{lessonView.refreshSetup();practiceView->updateDeclaredSetup(setup.currentSetup());};
        setup.onUserApplied=[this]{
            auto model=setupPreferences_.model();model.guitar=setup.currentSetup();model.boardDisplay=setup.draftBoardDisplay();
            setupPreferences_.choose(model);applyBoardDisplay();requestBoardSave();
        };
        setup.onBoardDisplayChanged=[this](const setup::BoardDisplay& value){chooseBoardDisplay(value);};
        lessonView.currentSetup=[this]{return std::optional<guitar::Setup>{setup.currentSetup()};};
        addAndMakeVisible(setupButton); addChildComponent(setup);
        outputButton.setButtonText("Audio settings"); outputButton.onClick=[this] {openAudioSettings();};
        outputView.onBack=[this] {returnFromAudioSettings();};
        addAndMakeVisible(outputButton);addChildComponent(outputView);
        scheduleButton.setButtonText("Rhythm preview");scheduleButton.onClick=[this]{navigate(Page::Rhythm);};
        scheduleView.onBack=[this]{const auto target=rhythmReturnPage_;rhythmReturnPage_=Page::Home;navigate(target);};
        addAndMakeVisible(scheduleButton);addChildComponent(scheduleView);
        referenceButton.setButtonText("Reference tones");referenceButton.onClick=[this]{if(navigate(Page::Reference))referenceView.setSetup(setup.currentSetup());};
        referenceView.onBack=[this]{navigate(referenceReturnPage_);};addAndMakeVisible(referenceButton);addChildComponent(referenceView);
        practiceButton.setButtonText("Exercise details");practiceButton.onClick=[this]{
            if(learnQueue_||learnFuture_||learnMutation_!=LearnMutation::None||lessonView.sourceQueueActive()){
                if(navigate(Page::Learn))lessonView.showSourceHierarchy();
                return;
            }
            const auto item=lessonView.selectedLesson(),variant=lessonView.selectedVariant();
            if(!lessonView.catalog()||item.empty()||variant.empty()){learnButton.triggerClick();return;}
            if(!navigate(Page::Learn))return;
            if(!lessonView.selectLesson(item)||!lessonView.selectVariant(variant))return;
            learnReturnPage_=Page::Home;lessonView.setBackLabel("Back");
        };
        practiceView->onBack=[this]{navigate(learnQueue_||learnFuture_||learnMutation_!=LearnMutation::None?Page::Learn:Page::Home);};addAndMakeVisible(practiceButton);addChildComponent(*practiceView);
        metronomeButton.setButtonText("Metronome");metronomeButton.onClick=[this]{navigate(Page::Metronome);};
        metronomeView.onBack=[this]{const auto target=metronomeReturnPage_;metronomeReturnPage_=Page::Home;navigate(target);};metronomeView.onReopenStore=[this]{return onReopenStore&&onReopenStore();};addAndMakeVisible(metronomeButton);addChildComponent(metronomeView);
        metronomeView.onProgress=[this](const platform::MetronomeProgress& progress){manualTaskView.onClock(progress);};
        manualTaskView.onStartPulse=[this](int bpm)->std::optional<MetronomeView::ManualPulseStart>{
            if(!audio_.activate(SharedAudioSettings::Consumer::Metronome))return std::nullopt;
            return metronomeView.startManualPulse(bpm);
        };
        manualTaskView.onStopPulse=[this]{if(metronomeView.soundPending())metronomeView.stopSound();};
        manualTaskView.onResolvePulse=[this]{return metronomeView.resolveManualPulse();};
        manualTaskView.onBack=[this]{return navigate(Page::Learn);};
        manualTaskView.onAudioSettings=[this]{openAudioSettings();};
        manualTaskView.onDraftSaveGate=[this]{return manualDraftSaveGate();};manualTaskView.onDraftStoreReopen=[this]{return onReopenStore&&onReopenStore();};
        addChildComponent(manualTaskView);
        recipeTaskView.onBack=[this]{return navigate(Page::Learn);};
        recipeTaskView.onSettings=[this]{openAudioSettings();return page_==Page::Audio;};
        recipeTaskView.onDraftSaveGate=[this]{return manualDraftSaveGate();};recipeTaskView.onDraftStoreReopen=[this]{return onReopenStore&&onReopenStore();};
        addChildComponent(recipeTaskView);
        advancedRecipeTaskView.onBack=[this]{return navigate(Page::Learn);};
        advancedRecipeTaskView.onSettings=[this]{openAudioSettings();return page_==Page::Audio;};
        advancedRecipeTaskView.onDraftSaveGate=[this]{return manualDraftSaveGate();};advancedRecipeTaskView.onDraftStoreReopen=[this]{return onReopenStore&&onReopenStore();};
        addChildComponent(advancedRecipeTaskView);
        compiledManualProcedureView.onDraftStoreReopen=[this]{return onReopenStore&&onReopenStore();};
        compiledManualProcedureView.onDraftSaveGate=[this]{return manualDraftSaveGate();};
        earSourceProcedureView.onDraftSaveGate=[this]{return manualDraftSaveGate();};c43SourceProcedureView.onDraftSaveGate=[this]{return manualDraftSaveGate();};
        earSourceProcedureView.onDraftStoreReopen=[this]{return onReopenStore&&onReopenStore();};c43SourceProcedureView.onDraftStoreReopen=[this]{return onReopenStore&&onReopenStore();};
        compiledManualProcedureView.onBack=[this]{return navigate(Page::Learn);};
        compiledManualProcedureView.onSettings=[this]{openAudioSettings();return page_==Page::Audio;};
        addChildComponent(compiledManualProcedureView);
        earSourceProcedureView.onBack=[this]{navigate(Page::Learn);};
        earSourceProcedureView.onSettings=[this]{openAudioSettings();return page_==Page::Audio;};
        addChildComponent(earSourceProcedureView);
        c43SourceProcedureView.onBack=[this]{navigate(Page::Learn);};
        c43SourceProcedureView.onSettings=[this]{openAudioSettings();return page_==Page::Audio;};
        addChildComponent(c43SourceProcedureView);
        learnButton.setButtonText("Learn");
        lessonView.setComponentID("learn-view");
        learnButton.onClick=[this]{
            if(clearQueuePanel_.isVisible()||clearQueueRequested_)return;
            if(homeLearnDetour_){if(navigate(Page::Learn)){homeLearnDetour_=false;lessonView.queueStatus("Retained Learn session resumed. Open the current exercise explicitly; automatic continuation remains paused.");}return;}

            lessonView.seedNewTempo(static_cast<std::uint16_t>(setupPreferences_.model().defaultBpm));
            sourceLibraryView.cancelLoading();
            pendingLearnEntry_=false;
            lessonView.setBackLabel("Back");
            learnReturnPage_=Page::Home;
            const auto resources=std::filesystem::path{representativeResources().getParentDirectory().getFullPathName().toStdString()};
            beginLearnIndexLoading(resources,installedExtensionResources());
        };
        startLearningButton.setButtonText("Start learning");
        startLearningButton.setTitle("Start learning in Learn");
        startLearningButton.setColour(juce::TextButton::buttonColourId, juce::Colour{0xff6bd5cb});
        startLearningButton.setColour(juce::TextButton::textColourOffId, juce::Colour{0xff10212c});
        startLearningButton.setColour(juce::TextButton::textColourOnId, juce::Colour{0xff10212c});
        startLearningButton.setExplicitFocusOrder(3);
        startLearningButton.onClick=[this]{learnButton.triggerClick();};
        lessonView.onBack=[this]{navigate(learnReturnPage_);};lessonView.onMetronome=[this]{navigate(Page::Metronome);};lessonView.onRhythmPreview=[this]{navigate(Page::Rhythm);};lessonView.onAudioSettings=[this]{openAudioSettings();};
        lessonView.onPrepareSourceGroup=[this](const std::vector<lesson::SelectedCatalogStore::Request>& requests,std::uint64_t group){if(learnSelectiveLoading_)beginSelectedCatalogLoading(requests,group);};
        lessonView.onSourceGroupSelectionChanged=[this]{cancelLearnLoading();};
        lessonView.onManualTaskCanPrepare=[](const std::string& source){return source_routes::familyFor(source)!=source_routes::Family::None;};
        lessonView.onManualTaskPrepare=[this](const std::string& source){beginLearnActivityLoading(source);};
        lessonView.onManualTaskAvailable=[this](const std::string& source){return (manualTaskRegistry_&&manualTaskRegistry_->contains(source))||(recipeTaskRegistry_&&recipeTaskRegistry_->contains("exercise-completeness-r01/"+source))||(advancedRecipeTaskRegistry_&&advancedRecipeTaskRegistry_->contains("exercise-completeness-r01/"+source))||(orderedContactTaskRegistry_&&orderedContactTaskRegistry_->containsSourceIdentity(source))||(physicalContactTaskRegistry_&&physicalContactTaskRegistry_->containsSourceIdentity(source))||(piecewiseContactTaskRegistry_&&piecewiseContactTaskRegistry_->containsSourceIdentity(source))||(harmonicContactTaskRegistry_&&harmonicContactTaskRegistry_->containsSourceIdentity(source))||(sourceContactTaskRegistry_&&sourceContactTaskRegistry_->containsSourceIdentity(source))||(manualCurriculumRegistry_&&manualCurriculumRegistry_->containsSourceIdentity(source))||(extraSource17Registry_&&extraSource17Registry_->containsSourceIdentity(source))||(ear234Package_&&ear234SourceKeys_.count(source))||(c43Package_&&ear234Package_&&c43SourceKeys_.count(source));};
        lessonView.onManualTaskOpen=[this](const std::string& source){
            if(learnQueue_||learnFuture_||learnMutation_!=LearnMutation::None)return false;
            const auto key="exercise-completeness-r01/"+source;
            if(c43Package_&&ear234Package_){
                const auto found=c43SourceKeys_.find(source);
                if(found!=c43SourceKeys_.end()){
                    if(page_!=Page::C43SourceProcedure&&!prepareManualNavigation())return false;
                    if(!c43SourceProcedureView.open(*c43Package_,*ear234Package_,found->second,source))return false;
                    return navigate(Page::C43SourceProcedure);
                }
            }
            if(ear234Package_){
                const auto found=ear234SourceKeys_.find(source);
                if(found!=ear234SourceKeys_.end()){
                    if(page_!=Page::EarSourceProcedure&&!prepareManualNavigation())return false;
                    if(!earSourceProcedureView.open(*ear234Package_,found->second,source))return false;
                    return navigate(Page::EarSourceProcedure);
                }
            }
            if(orderedContactTaskRegistry_&&orderedContactTaskRegistry_->containsSourceIdentity(source)){
                const auto definition=orderedContactTaskRegistry_->definitionForSourceIdentity(source);
                if(!definition)return false;
                if(page_!=Page::CompiledManualProcedure&&!prepareManualNavigation())return false;
                if(!compiledManualProcedureView.open(definition->sourceKey()))return false;
                return navigate(Page::CompiledManualProcedure);
            }
            if(physicalContactTaskRegistry_&&physicalContactTaskRegistry_->containsSourceIdentity(source)){
                const auto definition=physicalContactTaskRegistry_->definitionForSourceIdentity(source);
                if(!definition)return false;
                if(page_!=Page::CompiledManualProcedure&&!prepareManualNavigation())return false;
                if(!compiledManualProcedureView.open(definition->sourceKey()))return false;
                return navigate(Page::CompiledManualProcedure);
            }
            if(piecewiseContactTaskRegistry_&&piecewiseContactTaskRegistry_->containsSourceIdentity(source)){
                const auto definition=piecewiseContactTaskRegistry_->definitionForSourceIdentity(source);
                if(!definition)return false;
                if(page_!=Page::CompiledManualProcedure&&!prepareManualNavigation())return false;
                if(!compiledManualProcedureView.open(definition->sourceKey()))return false;
                return navigate(Page::CompiledManualProcedure);
            }
            if(harmonicContactTaskRegistry_&&harmonicContactTaskRegistry_->containsSourceIdentity(source)){
                const auto definition=harmonicContactTaskRegistry_->definitionForSourceIdentity(source);
                if(!definition)return false;
                if(page_!=Page::CompiledManualProcedure&&!prepareManualNavigation())return false;
                if(!compiledManualProcedureView.open(definition->sourceKey()))return false;
                return navigate(Page::CompiledManualProcedure);
            }
            if(sourceContactTaskRegistry_&&sourceContactTaskRegistry_->containsSourceIdentity(source)){
                const auto definition=sourceContactTaskRegistry_->definitionForSourceIdentity(source);
                if(!definition)return false;
                if(page_!=Page::CompiledManualProcedure&&!prepareManualNavigation())return false;
                if(!compiledManualProcedureView.open(definition->sourceKey()))return false;
                return navigate(Page::CompiledManualProcedure);
            }
            if(manualCurriculumRegistry_&&manualCurriculumRegistry_->containsSourceIdentity(source)){
                const auto definition=manualCurriculumRegistry_->definitionForSourceIdentity(source);
                if(!definition)return false;
                if(page_!=Page::CompiledManualProcedure&&!prepareManualNavigation())return false;
                if(!compiledManualProcedureView.open(definition->sourceKey()))return false;
                return navigate(Page::CompiledManualProcedure);
            }
            if(extraSource17Registry_&&extraSource17Registry_->containsSourceIdentity(source)){
                if(page_!=Page::CompiledManualProcedure&&!prepareManualNavigation())return false;
                if(!compiledManualProcedureView.openExtraSource(*extraSource17Registry_,source))return false;
                return navigate(Page::CompiledManualProcedure);
            }
            if(advancedRecipeTaskRegistry_&&advancedRecipeTaskRegistry_->contains(key)){
                if(page_!=Page::AdvancedRecipeTask&&!prepareManualNavigation())return false;
                if(!advancedRecipeTaskView.open(key))return false;
                return navigate(Page::AdvancedRecipeTask);
            }
            if(recipeTaskRegistry_&&recipeTaskRegistry_->contains(key)){
                if(page_!=Page::RecipeTask&&!prepareManualNavigation())return false;
                if(!recipeTaskView.open(key))return false;
                return navigate(Page::RecipeTask);
            }
            if(!manualTaskRegistry_)return false;
            const auto definition=manualTaskRegistry_->definition(source);
            if(!definition||(page_!=Page::ManualTask&&!prepareManualNavigation())||!manualTaskView.open(*definition))return false;
            return navigate(Page::ManualTask);
        };
        addAndMakeVisible(learnButton);addChildComponent(lessonView);
        // Retain the legacy control ID for internal fixture migration only.
        // Learn is the sole visible hierarchy entry; this duplicate is never shown.
        addChildComponent(startLearningButton);
        sourceLibraryButton.setButtonText("Exercise library");
        sourceLibraryButton.onClick=[this]{
            if(!navigate(Page::SourceLibrary))return;
            const auto resources=installedSourceLibrary();
            sourceLibraryView.beginBrowse(resources);
        };
        lessonView.onBookTheoryContext=[this](const std::string& workbookId){
            if(!sourceLibraryView.ensureTheoryContext(installedSourceLibrary()))
                return std::string{"Approved workbook explanation unavailable: verified offline source context could not be loaded."};
            return sourceLibraryView.publicTheoryContext(workbookId);
        };
        sourceLibraryView.setReturnLabel("Back to Learn");sourceLibraryView.onBack=[this]{navigate(Page::Learn);};
        sourceLibraryView.onOpenInLearn=[this](const std::string& workbookId){return openWorkbookInLearn(workbookId);};
        sourceLibraryView.onManualTaskAvailable=[this](const std::string& source){return lessonView.onManualTaskAvailable&&lessonView.onManualTaskAvailable(source);};
        sourceLibraryView.onManualTaskOpen=[this](const std::string& source){return lessonView.onManualTaskOpen&&lessonView.onManualTaskOpen(source);};
        sourceLibraryView.onManualTaskCanPrepare=[](const std::string& source){return source_routes::familyFor(source)!=source_routes::Family::None;};
        sourceLibraryView.onManualTaskPrepare=[this](const std::string& source){
            const auto family=source_routes::familyFor(source);if(family==source_routes::Family::None)return;
            const auto resources=installedSourceLibrary().parent_path();
            const juce::Component::SafePointer<HomeView> owner{this};
            sourceLibraryView.prepareActivity(source,[resources,owner,source](const SourceLibraryView::LoadTicket& ticket){
                auto gates=std::make_shared<SourceTaskLibraries>();gates->loadSelected(resources,ticket,source);
                return [owner,gates]{if(owner)owner->SourceTaskLibraries::merge(std::move(*gates));};
            },[owner,source]{return owner&&owner->lessonView.onManualTaskOpen&&owner->lessonView.onManualTaskOpen(source);});
        };
        addAndMakeVisible(sourceLibraryButton);
        addChildComponent(sourceLibraryView);
        addChildComponent(clearQueuePanel_);
        clearQueuePanel_.onCancel=[this]{if(!clearQueueRequested_){closeClearLearnPanel();update();}};
        clearQueuePanel_.onReturn=[this]{if(!clearQueueRequested_){closeClearLearnPanel();if(learnQueue_)navigate(Page::Practice);else navigate(Page::Learn);}};
        clearQueuePanel_.onRetry=[this]{if(clearQueueRequested_&&!learnFuture_&&learnMutation_!=LearnMutation::None){std::string reason;retryLearnQueue(reason);}};
        clearQueuePanel_.onConfirm=[this]{confirmClearLearnQueue();};
        lessonView.onClearQueue=[this]{requestClearLearnQueue();};
        lessonView.onQueueOpen=[this](navigation::ExerciseQueue& queue,std::uint16_t bpm,std::string& reason){return openLearnQueue(queue,bpm,reason);};
        lessonView.onQueueCanNext=[this]{return canAdvanceLearnQueue();};
        lessonView.onQueueNextLabel=[this]{return canAdvanceLearnQueue()&&learnCaptureResult()==learn::QueueCaptureResult::UnusedPreparation?std::string{"Cancel unused preparation & Next"}:std::string{"Next after Save and cleanup"};};
        lessonView.onQueueNext=[this](std::string& reason){if(clearQueuePanel_.isVisible()||clearQueueRequested_){reason="Finish or cancel the queue reset first.";return false;}return advanceLearnQueue(reason);};
        lessonView.onQueueRetryLabel=[this]{return learnRetryLabel();};
        lessonView.onQueueRetry=[this](std::string& reason){if(clearQueuePanel_.isVisible()||clearQueueRequested_){reason="Use Check original reset in the confirmation.";return false;}return retryLearnQueue(reason);};
        lessonView.onQueueReturn=[this]{if(suiteQueue_&&!learnQueue_&&suiteQueue_->phase()==navigation::ExerciseQueuePhase::Ready){std::string reason;openLearnQueue(*suiteQueue_,learnBpm_,reason);}else navigate(Page::Practice);};
        lessonView.localProfileAvailable=[this]{return practiceView->captureSession()!=nullptr;};
        lessonView.onPractice=[this](std::shared_ptr<const lesson::Admission> selection,std::uint16_t bpm,std::string& reason){
            if(learnQueue_||learnFuture_||learnMutation_!=LearnMutation::None){reason="Resolve the current Learn queue Session before opening a direct case.";return false;}
            if(!lessonView.catalogReady()){reason="Reverify the selected exercise in Learn before opening a new Practice preparation.";return false;}
            if(!selection){reason="No supported lesson selection is available.";return false;}
            if(!practiceView->captureSession())return prepareProfileForCase(std::move(selection),bpm,reason);
            if(!practiceView->audioCanRelease()){reason="Finish or reconcile the current Practice result before choosing another case.";return false;}
            if(!audio_.canRelease()){reason="Return to "+audio_.name()+" and finish its current activity or pending settings save.";return false;}
            try{selection->practiceConfiguration(44100,bpm);}catch(const std::exception& e){reason=e.what();return false;}
            // Admit the audio handoff before replacing a lesson or its return origin.
            if(!audio_.activate(SharedAudioSettings::Consumer::Practice)){reason=audio_.message();return false;}
            const auto guidedOwner=guidedView.running()?guidedView.sessionId():std::string{};
            const auto previousOwner=practiceView->captureSessionId();
            const auto targetOwner=guidedOwner.empty()?learnPreviewSession_:guidedOwner;
            // A saved result is immutable; release its in-memory capture before
            // binding the explicitly selected Session. This never starts an Attempt.
            if(targetOwner!=previousOwner&&practiceView->captureSession()->phase()==capture::SessionPhase::Saved&&!practiceView->againSample()){
                reason="The saved Practice result cannot be released for the selected Session.";return false;
            }
            if(targetOwner.empty()||(targetOwner!=previousOwner&&!practiceView->rebindCaptureSession(targetOwner))){reason="The selected Session cannot own Practice until the current capture is idle and resolved.";return false;}
            if(!practiceView->configureLesson(std::move(selection),bpm,setup.currentSetup())){
                practiceView->rebindCaptureSession(previousOwner);
                reason="Audio cleanup or the original Practice result still needs attention. Return to Practice and inspect its details.";return false;
            }
            if(guidedOwner.empty())practiceView->setGuidedSummaryAction(std::function<void()>{});
            else practiceView->setGuidedSummaryAction([this]{guidedView.noteSavedPracticeAttempt();navigate(Page::Guided);});
            practiceView->setReturnDestination(guidedOwner.empty()?"Learn":"Guided");
            practiceView->onBack=[this,guidedOwner]{
                const auto* capture=practiceView->captureSession();
                if(!guidedOwner.empty()&&guidedView.running()&&guidedView.sessionId()==guidedOwner
                   &&practiceView->captureSessionId()==guidedOwner&&capture){
                    if(capture->phase()==capture::SessionPhase::Saved)guidedView.noteSavedPracticeAttempt();
                    navigate(Page::Guided);return;
                }
                navigate(Page::Learn);
            };
            practiceView->onProgressPage=[this]{navigate(Page::Progress);};
            // Same admitted consumer; preparation cannot start musical output.
            audio_.activate(SharedAudioSettings::Consumer::Practice);
            page_=Page::Practice;update();return true;
        };
        progressButton.setButtonText("Progress");progressButton.onClick=[this]{navigate(Page::Progress);};
        progressView.onBack=[this]{navigate(learnQueue_||learnFuture_||learnMutation_!=LearnMutation::None?Page::Learn:progressReturnPage_);};
        progressView.onLearn=[this]{learnButton.triggerClick();};
        progressView.onAudioSettings=[this]{openAudioSettings();};
        progressView.onReopen=[this]{return onReopenStore&&onReopenStore();};
        addAndMakeVisible(progressButton);addChildComponent(progressView);
        freeplayButton.setButtonText("Free play");
        freeplayButton.onClick=[this]{navigate(Page::FreeplayMenu);};
        freeplayView.setReturnDestination("Free play");freeplayView.onBack=[this]{navigate(Page::FreeplayMenu);};
        freeplayView.onRhythmTools=[this]{navigate(Page::Metronome);};
        freeplayView.onProgress=[this]{navigate(Page::Progress);};
        freeplayView.onAudioSettings=[this]{openAudioSettings();};
        addAndMakeVisible(freeplayButton);addChildComponent(freeplayView);
        guidedButton.setButtonText("Guided sessions");
        guidedButton.onClick=[this]{
            if(!guidedView.newSessionsEnabled())return;
            sourceLibraryView.cancelLoading();
            const auto resources=std::filesystem::path{representativeResources().getParentDirectory().getFullPathName().toStdString()};
            beginGuidedSelectionLoading(resources,installedExtensionResources());
        };
        guidedView.onBack=[this]{navigate(Page::Home);};
        guidedView.onProgressPage=[this]{navigate(Page::Progress);};
        guidedView.onAudioSettings=[this]{openAudioSettings();};
        guidedView.onOpenLesson=[this](const std::string& id,const std::string& variantId){
            if(!guidedView.newSessionsEnabled())return false;
            if(guidedView.running())return lessonView.practiceExplicitSelection(id,variantId);
            if(!lessonView.selectLesson(id)||!lessonView.selectVariant(variantId)) return false;
            learnReturnPage_=Page::Guided;
            lessonView.setBackLabel("Back to Guided");
            lessonView.onBack=[this]{navigate(learnReturnPage_);};
            return navigate(Page::Learn);
        };
        addAndMakeVisible(guidedButton);addChildComponent(guidedView);
        auto configureHomeControl=[&](juce::Component& component,const char* id,const char* title,int order){component.setComponentID(id);component.setTitle(title);component.setWantsKeyboardFocus(true);component.setExplicitFocusOrder(order);component.setColour(juce::TextButton::buttonColourId,juce::Colour{0xff6bd5cb});component.setColour(juce::TextButton::textColourOffId,juce::Colour{0xff10212c});component.setColour(juce::TextButton::textColourOnId,juce::Colour{0xff10212c});};
        configureHomeControl(about,"home-about-preview","Show the offline Development Preview scope and review status.",1);
        configureHomeControl(quit,"home-quit","Quit Fathom.",2);
        configureHomeControl(setupButton,"home-guitar-setup","Open Guitar setup without starting activity.",3);
        configureHomeControl(outputButton,"home-audio-output","Open shared Audio settings for local activities; opening settings does not start audio or practice activity.",4);
        configureHomeControl(scheduleButton,"home-rhythm-preview","Open Rhythm preview.",5);
        configureHomeControl(referenceButton,"home-reference-tones","Open Reference tones.",6);
        configureHomeControl(practiceButton,"home-practice","Review the current exercise in Learn. Choose an exercise in Learn first; opening details does not start Practice.",7);
        configureHomeControl(metronomeButton,"home-metronome","Open Metronome tools.",8);
        configureHomeControl(learnButton,"home-learn","Choose a level and exercise. Practice starts only when you choose Start in Practice.",9);
        configureHomeControl(startLearningButton,"home-start-learning","Start learning in the retained source-backed Learn catalog; select an admitted case before explicit Practice Start and no curriculum credit is inferred.",10);
        configureHomeControl(progressButton,"home-progress","Open read-only Progress for saved local activity; no curriculum credit is inferred.",11);
        configureHomeControl(freeplayButton,"home-freeplay","Open separate Freeplay; active time and history stay outside curriculum progress.",12);
        configureHomeControl(guidedButton,"home-guided","Open Guided sessions with a local timed plan; linked Practice stays explicit and no curriculum credit is inferred.",13);
        configureHomeControl(localProfileButton,"home-local-profile","Open an existing local profile without starting activity or audio. Use Setup / resume setup to create a named profile.",14);
        configureHomeControl(sourceLibraryButton,"home-source-library","Browse installed original workbook text and PDF sources without starting Practice or granting progress credit. Optional curriculum content may be absent.",15);
        configureHomeControl(settingsButton_,"home-settings","Open presentation, appearance and UI preferences. Personal learning and instrument preferences are in User profile.",16);addChildComponent(settingsButton_);
        settingsButton_.onClick=[this]{if(page_==Page::Home)navigate(Page::Settings);};
        presentationChoice_.setExplicitFocusOrder(1);presentationSave_.setExplicitFocusOrder(2);presentationReset_.setExplicitFocusOrder(3);presentationReload_.setExplicitFocusOrder(4);onboardingButton_.setExplicitFocusOrder(5);previewDetails_.setExplicitFocusOrder(6);settingsBack_.setExplicitFocusOrder(7);
        settingsBack_.setComponentID("settings-back");settingsBack_.onClick=[this]{std::string reason;requestHome(reason);};addChildComponent(settingsBack_);
        settingsHeading_.setText("Settings",juce::dontSendNotification);settingsHeading_.setFont(juce::FontOptions{28.0f});
        settingsHelp_.setText("Presentation changes disclosure only. Save explicitly to keep a change in this profile. Activities, results and audio stay under their existing controls.",juce::dontSendNotification);
        settingsPresentationLabel_.setText("PRESENTATION",juce::dontSendNotification);settingsSetupLabel_.setText("SETUP",juce::dontSendNotification);settingsInfoLabel_.setText("PREVIEW INFORMATION",juce::dontSendNotification);
        for(auto* c:{&settingsHeading_,&settingsHelp_,&settingsPresentationLabel_,&settingsSetupLabel_,&settingsInfoLabel_,&homeSettingsNotice_}){addChildComponent(c);c->setJustificationType(juce::Justification::topLeft);}
        homeSettingsNotice_.setFont(juce::FontOptions{14.0f});homeSettingsNotice_.setComponentID("home-settings-attention");
        for(auto* c:std::initializer_list<juce::Component*>{&userProfileButton_,&freeplaySessionButton_,&profileSave_,&profileReload_,&guidedRecoveryButton_,&uiSave_,&uiReload_,&sectionBack_,&profileBpm_,&appearanceChoice_,&sectionHeading_,&sectionHelp_,&profileIdentity_,&profileBpmLabel_,&profileStatusLabel_,&uiStatus_})addChildComponent(*c);
        userProfileButton_.setComponentID("home-user-profile");userProfileButton_.setTitle("User profile: identity, Progress and history, default BPM and guitar settings.");userProfileButton_.onClick=[this]{navigate(Page::UserProfile);};
        freeplaySessionButton_.setComponentID("freeplay-session");freeplaySessionButton_.onClick=[this]{navigate(Page::Freeplay);};
        sectionBack_.setComponentID("section-back");sectionBack_.onClick=[this]{std::string reason;requestHome(reason);};
        guidedRecoveryButton_.setComponentID("profile-guided-recovery");guidedRecoveryButton_.onClick=[this]{if(canReviewGuidedOriginal())navigate(Page::Guided);};
        profileBpm_.setComponentID("profile-default-bpm");profileBpm_.setTitle("Default quarter-note BPM for new Learn selections;20 to 300. Current queues and recorded tempos stay unchanged.");profileBpm_.setInputRestrictions(3,"0123456789");profileBpm_.onTextChange=[this]{profileBpmEdited_=profileBpm_.getText().toStdString()!=profileBpmDisplayed_;refreshNavigationSections();};
        profileBpmLabel_.setText("Default BPM (new Learn selections)",juce::dontSendNotification);
        profileSave_.setComponentID("profile-save-preferences");profileSave_.onClick=[this]{saveProfilePreferences();};profileReload_.setComponentID("profile-reload-preferences");profileReload_.onClick=[this]{if(!setupPreferences_.inFlight()){profileBpmEdited_=false;profileBpmDisplayed_=profileBpm_.getText().toStdString();if(setupPreferences_.reload())applyProfileReload_=true;}};
        appearanceChoice_.setComponentID("settings-appearance");appearanceChoice_.setTitle("Interface appearance: Default, Light or Dark. This never starts audio.");appearanceChoice_.addItem("Default appearance",1);appearanceChoice_.addItem("Light appearance",2);appearanceChoice_.addItem("Dark appearance",3);appearanceChoice_.onChange=[this]{consumeAppearanceChoice();};
        uiSave_.setComponentID("settings-save-ui");uiSave_.onClick=[this]{consumeAppearanceChoice();saveSetupDraft();};uiReload_.setComponentID("settings-reload-ui");uiReload_.onClick=[this]{if(!setupPreferences_.inFlight()&&setupPreferences_.reload())applyProfileReload_=true;};
        int navFocus=1;for(auto* c:std::initializer_list<juce::Component*>{&learnButton,&freeplayButton,&userProfileButton_,&settingsButton_,&quit,&freeplaySessionButton_,&profileBpm_,&profileSave_,&profileReload_,&appearanceChoice_,&uiSave_,&uiReload_,&sectionBack_,&guidedRecoveryButton_}){c->setWantsKeyboardFocus(true);c->setExplicitFocusOrder(navFocus++);if(auto* button=dynamic_cast<juce::Button*>(c);button&&button->getTitle().isEmpty())button->setTitle(button->getButtonText());}
        profileIdentity_.setMultiLine(true);profileIdentity_.setReadOnly(true);profileIdentity_.setScrollbarsShown(true);profileIdentity_.setFont(juce::FontOptions{14.0f});profileIdentity_.setComponentID("profile-identity");profileIdentity_.setTitle("Read-only profile name, stable identity and local recovery file; scroll for the complete path.");
        sectionHeading_.setFont(juce::FontOptions{28.0f});for(auto* label:{&sectionHeading_,&sectionHelp_,&profileBpmLabel_,&profileStatusLabel_,&uiStatus_})label->setJustificationType(juce::Justification::topLeft);
        startLearningButton.setWantsKeyboardFocus(false);
        startLearningButton.setEnabled(false);
        lessonView.onPresentationChoice=[this](std::optional<presentation::Level> level){presentation_.choosePage(presentation::Page::Learn,level);applyPresentation();};
        wirePractice();applyPresentation();
        audio_.bind(SharedAudioSettings::Consumer::Metronome,audioEndpoint(metronomeView,"Metronome"));
        audio_.bind(SharedAudioSettings::Consumer::Reference,audioEndpoint(referenceView,"Reference tones"));
        audio_.bind(SharedAudioSettings::Consumer::Rhythm,audioEndpoint(scheduleView,"Rhythm preview"));
        outputView.bind(audio_);
        metronomeView.onAudioSettings=[this]{openAudioSettings();};
        referenceView.onAudioSettings=[this]{openAudioSettings();};
        scheduleView.onAudioSettings=[this]{openAudioSettings();};
        metronomeView.onMixSelected=[this](const output::MixSettings& m){audio_.selectedByConsumer(SharedAudioSettings::Consumer::Metronome,m);};
        startTimer(20);
        setSize(920, 680);
        update();
    }
    void paint(juce::Graphics& graphics) override {
        graphics.fillAll(appearance::colour(0xff10212c));
        graphics.setColour(appearance::colour(0xff6bd5cb));
        if(page_==Page::Home||page_==Page::About)graphics.fillRect(40, 158, getWidth() - 80, 2);
    }
    void resized() override {
        originalRecovery_.setBounds(getLocalBounds());clearQueuePanel_.setBounds(getLocalBounds());
        const bool child=page_!=Page::Home&&page_!=Page::About;
        const auto childBounds=getLocalBounds().withTrimmedTop(child?64:0);
        homeRoute_.setBounds(12,12,96,36);homeRouteStatus_.setBounds(120,6,std::max(1,getWidth()-132-(page_==Page::Learn?210:0)),52);
        const int x=getWidth()<800?16:40,width=getWidth()-2*x;
        heading.setBounds(x,22,width,54);subtitle.setBounds(x,82,width,24);
        message.setBounds(x,146,width,142);detail.setBounds(x,300,width,std::max(40,getHeight()-490));
        heading.setBounds(x,64,width,56);subtitle.setBounds(x,126,width,24);message.setBounds(x,172,width,110);
        userProfileButton_.setBounds(getWidth()-x-190,20,190,38);
        learnButton.setBounds(x,316,std::min(380,width),56);freeplayButton.setBounds(x,392,std::min(380,width),56);
        settingsButton_.setBounds(x,getHeight()-64,180,36);quit.setBounds(getWidth()-x-150,getHeight()-64,150,36);
        sourceLibraryButton.setBounds(getWidth()-x-170,12,170,36);
        sectionHeading_.setBounds(x,82,width,38);sectionHelp_.setBounds(x,458,width,110);sectionBack_.setBounds(x,getHeight()-64,180,36);
        if(page_==Page::UserProfile){
            profileIdentity_.setBounds(x,132,width,66);progressButton.setBounds(x,214,320,36);localProfileButton.setBounds(x,258,320,36);onboardingButton_.setBounds(x,302,320,36);guidedRecoveryButton_.setBounds(x,346,320,36);setupButton.setBounds(x,402,320,36);
            const int right=x+std::max(360,width/2);profileBpmLabel_.setBounds(right,214,std::max(1,width-(right-x)),24);profileBpm_.setBounds(right,246,140,34);profileSave_.setBounds(right,294,250,36);profileReload_.setBounds(right,338,250,36);profileStatusLabel_.setBounds(right,390,std::max(1,width-(right-x)),62);
        }
        if(page_==Page::FreeplayMenu){
            freeplaySessionButton_.setBounds(x,164,320,44);metronomeButton.setBounds(x,228,320,36);scheduleButton.setBounds(x,276,320,36);referenceButton.setBounds(x,324,320,36);outputButton.setBounds(x,372,320,36);
        }
        if(page_==Page::Settings){
            settingsHeading_.setBounds(x,82,width,38);settingsHelp_.setBounds(x,130,width,52);
            settingsPresentationLabel_.setBounds(x,194,width,24);
            presentationChoice_.setBounds(x,224,std::min(320,width/2),36);presentationSave_.setBounds(x+std::min(320,width/2)+12,224,170,36);
            presentationReset_.setBounds(x,272,240,36);presentationReload_.setBounds(x+252,272,std::min(280,width-252),36);
            presentationStatus_.setBounds(x,320,width,70);settingsSetupLabel_.setBounds(x,406,width,24);appearanceChoice_.setBounds(x,436,280,36);uiSave_.setBounds(x+292,436,180,36);uiReload_.setBounds(x+484,436,220,36);uiStatus_.setBounds(x,482,width,32);
            settingsInfoLabel_.setBounds(x,524,width,24);previewDetails_.setBounds(x,554,240,36);settingsBack_.setBounds(x,getHeight()-64,180,36);
        }
        homeSettingsNotice_.setBounds(x,476,width,100);
        about.setBounds(x,getHeight()-64,180,36);
        for(auto* c:std::initializer_list<juce::Component*>{&onboarding_,&setup,&outputView,&scheduleView,&referenceView,practiceView.get(),&metronomeView,&lessonView,&manualTaskView,&progressView,&freeplayView,&guidedView,&sourceLibraryView,&recipeTaskView,&advancedRecipeTaskView,&compiledManualProcedureView,&earSourceProcedureView,&c43SourceProcedureView})c->setBounds(childBounds);
        suiteReviewView_.setBounds(childBounds);
        const auto* queuedCurrent=learnQueue_?learnQueue_->current():nullptr;
        const auto& activeAdmission=practiceView->lessonAdmission();
        // A queue may advance before asynchronous Practice preparation finishes.
        // Never label the old active TAB as the newly selected exercise.
        const bool queuedPractice=page_==Page::Practice&&learnQueue_&&learnQueue_->size()>1&&queuedCurrent&&queuedCurrent->admission&&activeAdmission&&navigation::snapshotAdmission(*activeAdmission)==*queuedCurrent->admission;
        std::vector<std::string> queueLabels;
        if(queuedPractice)for(std::size_t i=0;i<1;++i){const auto* entry=learnQueue_->entryAt(learnQueue_->position()+i);if(!entry)break;
            try{const auto admitted=navigation::resolveExerciseAdmission(*lessonView.catalog(),*entry);const auto record=json::parse(admitted->model()->source().preservedRecordJson);std::string label=record.object().at("title").string();
                for(const auto& variant:record.object().at("variants").array())if(variant.object().at("id").string()==entry->admission->variantId){label+=" — "+variant.object().at("label").string();break;}queueLabels.push_back(std::move(label));}
            catch(const std::exception&){queueLabels.push_back("Exercise "+std::to_string(entry->sourceOrder)+" — source details unavailable");}}
        // Future documents are read-only presentation. They never configure
        // Practice, allocate capture authority, or prepare/start output.
        const auto* shownQueue=queuedPractice?learnQueue_:nullptr;
        const auto shownPosition=shownQueue?shownQueue->position():0;
        const auto active=practiceView->tabView().document();
        // The source plan is immutable. Resize alone must not repeat admission
        // work or allocate future documents. Bound the preview before resolving.
        if(shownQueue!=upcomingTabQueue_||shownPosition!=upcomingTabPosition_||active!=upcomingTabActive_){
            std::vector<std::shared_ptr<const tab::Document>> documents;
            upcomingTabError_.clear();
            const auto remaining=shownQueue?shownQueue->size()-shownPosition-1:0;
            if(remaining>TabView::upcomingPanelLimit){
                practiceView->tabView().setUpcomingDocuments({});
                upcomingTabError_="Upcoming TAB preview exceeds the panel budget; current TAB is unchanged.";
            }else try{
                if(shownQueue)for(std::size_t i=shownPosition+1;i<shownQueue->size();++i){
                    const auto* entry=shownQueue->entryAt(i);
                    if(!entry)throw std::runtime_error("Upcoming source exercise is unavailable");
                    const auto admitted=navigation::resolveExerciseAdmission(*lessonView.catalog(),*entry);
                    documents.push_back(std::make_shared<const tab::Document>(admitted->model()));
                }
                practiceView->tabView().setUpcomingDocuments(std::move(documents));
            }catch(const std::exception&){
                practiceView->tabView().setUpcomingDocuments({});
                upcomingTabError_="Upcoming TAB unavailable; current exercise is unchanged.";
            }
            upcomingTabQueue_=shownQueue;upcomingTabPosition_=shownPosition;upcomingTabActive_=active;
        }
        if(queuedPractice&&!upcomingTabError_.empty()&&!queueLabels.empty())queueLabels.front()+=" — "+upcomingTabError_;
        practiceQueueHeader_.display(queuedPractice?learnQueue_:nullptr,queueLabels);practiceQueueHeader_.setVisible(queuedPractice);
        if(queuedPractice){practiceQueueHeader_.setBounds(0,childBounds.getY(),getWidth(),44);practiceView->setBounds(0,childBounds.getY()+44,getWidth(),std::max(1,childBounds.getHeight()-44));}
    }

private:
    friend struct HomeRouteTestAccess;
    friend struct OnboardingIntegrationTestAccess;
    friend struct SharedAudioViewTestAccess;
    friend struct LearnNavigationTestAccess;
    struct LearnPayload {
        std::shared_ptr<const learn::SourceIndex> index;
        std::shared_ptr<const lesson::Catalog> catalog;
        std::unique_ptr<SourceTaskLibraries> gates=std::make_unique<SourceTaskLibraries>();
    };
    void cancelLearnLoading(){learnActivitySource_.clear();if(learnLoadTicket_){learnLoadTicket_->store(true);learnLoadTicket_.reset();lessonView.catalogPreparing(false);guidedView.setCatalogLoading(false);}}
    bool beginLearnIndexLoading(const std::filesystem::path& resources,const std::vector<std::filesystem::path>& extensions,std::function<void(HomeView&)> onIndexReady={}){
        if(!learnResources_.empty()&&(learnResources_!=resources||learnExtensions_!=extensions))return false;
        if(!navigate(Page::Learn))return false;
        lessonView.showSourceHierarchy(false);
        if(learnLoadTicket_&&learnPreparingIndex_)return true;
        cancelLearnLoading();
        learnResources_=resources;learnExtensions_=extensions;learnSelectiveLoading_=true;
        if(!selectedCatalogStore_)selectedCatalogStore_=std::make_shared<lesson::SelectedCatalogStore>(resources/"representative-controls",extensions);
        if(learnIndexLoaded_&&lessonView.preparedSourceIndex()){
            lessonView.loadingStatus("");if(onIndexReady)onIndexReady(*this);else lessonView.resumeSourcePreparation();return true;
        }
        const auto previous=learnPayload_;auto data=std::make_shared<LearnPayload>();learnPayload_=data;
        auto ticket=std::make_shared<std::atomic<bool>>(false);learnLoadTicket_=ticket;learnLoadingPage_=Page::Learn;learnPreparingIndex_=true;
        lessonView.loadingStatus("Preparing the complete exercise list. Back remains available.");
        const juce::Component::SafePointer<HomeView> owner{this};
        sourceDataPool().addJob([owner,ticket,data,previous,resources,onIndexReady]{
            const SourceTaskLibraries::ActiveLoad active;
            try{
                if(ticket->load())return;
                // The single worker serializes canceled private preparation before
                // reuse. Only the current ticket may publish a source index.
                if(previous)data->index=previous->index;
                if(!data->index){
                    // A source-only build deliberately omits optional curriculum.
                    // Missing content is a held empty state, never a synthetic index
                    // or permission to admit a replacement exercise.
                    if(!std::filesystem::is_directory(resources/"learn-source-index"))
                        throw std::runtime_error("Optional curriculum content is not installed. Free play, User profile and Settings remain available. Back returns to Home.");
                    data->index=learn::SourceIndex::load(resources/"learn-source-index",[ticket]{return ticket->load();});
                }
                if(ticket->load())return;
                juce::MessageManager::callAsync([owner,ticket,index=data->index,onIndexReady]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    owner->learnLoadTicket_.reset();owner->learnPreparingIndex_=false;
                    owner->learnIndexLoaded_=owner->lessonView.installPreparedSourceIndex(index);
                    owner->lessonView.loadingStatus(owner->learnIndexLoaded_?"":"Finish the retained selection before changing its verified source index.");
                    if(owner->learnIndexLoaded_){if(onIndexReady)onIndexReady(*owner);else owner->lessonView.resumeSourcePreparation();}
                });
            }catch(const std::exception& error){
                const auto message=std::string{"Exercise list unavailable: "}+error.what();
                juce::MessageManager::callAsync([owner,ticket,message]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    owner->learnLoadTicket_.reset();owner->learnPreparingIndex_=false;owner->lessonView.loadingStatus(message);
                });
            }
        });
        return true;
    }
    bool beginSelectedCatalogLoading(const std::vector<lesson::SelectedCatalogStore::Request>& requests,std::uint64_t group){
        if(page_!=Page::Learn||learnResources_.empty()||lessonView.hasRetainedSourcePlan()||lessonView.sourceQueueActive())return false;
        cancelLearnLoading();learnPreparingIndex_=false;
        if(requests.empty()){
            learnSelectedRequests_.clear();lessonView.catalogPreparing(false);lessonView.loadingStatus("Choose Open exercise activity for source-guided exercises.");return true;
        }
        for(const auto& request:requests)if(request.expectedPackageHash.empty())return false;
        if(!selectedCatalogStore_)selectedCatalogStore_=std::make_shared<lesson::SelectedCatalogStore>(learnResources_/"representative-controls",learnExtensions_);
        auto ticket=std::make_shared<std::atomic<bool>>(false);learnLoadTicket_=ticket;learnLoadingPage_=Page::Learn;
        lessonView.catalogPreparing(true);lessonView.loadingStatus("Verifying this sublevel's Practice cases. Other exercises remain browseable; Back remains available.");
        const auto resources=learnResources_;const auto store=selectedCatalogStore_;
        const juce::Component::SafePointer<HomeView> owner{this};
        sourceDataPool().addJob([owner,ticket,store,requests,group,resources]{
            const SourceTaskLibraries::ActiveLoad active;
            try{
                const auto catalog=store->prepare(requests,[ticket]{return ticket->load();});
                if(!catalog||ticket->load())return;
                juce::MessageManager::callAsync([owner,ticket,catalog,group,resources,requests]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    owner->learnLoadTicket_.reset();owner->lessonView.catalogPreparing(false);
                    if(owner->page_!=Page::Learn||owner->lessonView.sourceGroupRevision()!=group)return;
                    const bool installed=owner->lessonView.installPreparedCatalog(catalog,resources,true,true);
                    if(installed)owner->learnSelectedRequests_=requests;
                    owner->lessonView.loadingStatus(installed?"":"The retained Preview or queue keeps its original verified catalog. Open a new sublevel explicitly to change selection.");
                });
            }catch(const std::exception& error){
                const auto message=std::string{"Selected Practice preparation refused: "}+error.what();
                juce::MessageManager::callAsync([owner,ticket,group,message]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    owner->learnLoadTicket_.reset();
                    // Retain the refusal and keep Preview disabled. An old catalog
                    // may never confer availability on an unverified new selection.
                    if(owner->page_==Page::Learn&&owner->lessonView.sourceGroupRevision()==group){owner->lessonView.catalogRefused(message);owner->lessonView.loadingStatus(message);}
                });
            }
        });
        return true;
    }
    bool beginLearnActivityLoading(const std::string& source){
        if(page_!=Page::Learn||learnResources_.empty()||lessonView.sourceQueueActive())return false;
        if(source_routes::familyFor(source)==source_routes::Family::None)return false;
        if(learnActivitySource_==source&&learnLoadTicket_)return true;
        cancelLearnLoading();learnPreparingIndex_=false;
        auto ticket=std::make_shared<std::atomic<bool>>(false);learnLoadTicket_=ticket;learnLoadingPage_=Page::Learn;
        learnActivitySource_=source;const auto revision=lessonView.sourceSelectionRevision();const auto resources=learnResources_;
        lessonView.loadingStatus("Verifying the selected exercise activity. Back remains available.");
        const juce::Component::SafePointer<HomeView> owner{this};
        sourceDataPool().addJob([owner,ticket,resources,source,revision]{
            try{
                auto gates=std::make_shared<SourceTaskLibraries>();gates->loadSelected(resources,ticket,source);
                if(ticket->load())return;
                juce::MessageManager::callAsync([owner,ticket,gates,source,revision]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    owner->learnLoadTicket_.reset();owner->learnActivitySource_.clear();owner->SourceTaskLibraries::merge(std::move(*gates));
                    owner->lessonView.loadingStatus("");owner->lessonView.refreshSetup();
                    if(owner->page_==Page::Learn&&owner->lessonView.sourceSelectionRevision()==revision&&owner->lessonView.onManualTaskOpen)
                        owner->lessonView.onManualTaskOpen(source);
                });
            }catch(const std::exception& error){
                const auto message=std::string{"Selected exercise activity refused: "}+error.what();
                juce::MessageManager::callAsync([owner,ticket,revision,message]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    owner->learnLoadTicket_.reset();owner->learnActivitySource_.clear();
                    if(owner->page_==Page::Learn&&owner->lessonView.sourceSelectionRevision()==revision)owner->lessonView.loadingStatus(message);
                });
            }
        });
        return true;
    }
    bool beginLearnLoading(const std::filesystem::path& resources,const std::vector<std::filesystem::path>& extensions,
                           const std::vector<source_routes::Family>& families,std::function<void()> beforeCatalog={},
                           Page entryPage=Page::Learn,std::function<void(HomeView&)> onCatalogReady={}){
        if(entryPage==Page::Guided&&!guidedView.newSessionsEnabled())return false;
        // The live GUI owns staged pointers and installed gates from one package.
        // A different resource root or extension extent requires a fresh owner.
        if(!learnResources_.empty()&&(learnResources_!=resources||learnExtensions_!=extensions))return false;
        learnSelectiveLoading_=false;
        if(!navigate(entryPage))return false;
        if(entryPage==Page::Learn)lessonView.showSourceHierarchy(false);
        if(learnLoadTicket_&&learnResources_==resources)return true;
        cancelLearnLoading();
        const auto previous=learnResources_==resources?learnPayload_:nullptr;
        const auto existingCatalog=learnResources_==resources&&learnExtensions_==extensions?lessonView.catalog():nullptr;
        const auto existingIndex=learnResources_==resources&&learnExtensions_==extensions&&learnIndexLoaded_?lessonView.preparedSourceIndex():nullptr;
        if(existingCatalog&&existingIndex&&families.empty()){lessonView.loadingStatus("");if(onCatalogReady)onCatalogReady(*this);return true;}
        learnResources_=resources;learnExtensions_=extensions;auto data=std::make_shared<LearnPayload>();learnPayload_=data;
        auto ticket=std::make_shared<std::atomic<bool>>(false);learnLoadTicket_=ticket;learnLoadingPage_=entryPage;
        lessonView.catalogPreparing(!existingCatalog);
        lessonView.loadingStatus("Preparing exercises and Practice. Back remains available.");
        if(entryPage==Page::Guided)guidedView.setCatalogLoading(true,"Preparing the verified Practice catalog. Back remains available.");
        const juce::Component::SafePointer<HomeView> owner{this};
        sourceDataPool().addJob([owner,ticket,data,previous,existingCatalog,existingIndex,resources,extensions,families,beforeCatalog,onCatalogReady]{
            const SourceTaskLibraries::ActiveLoad active;
            if(ticket->load())return;
            try{
                // Earlier canceled work is read only here, after its job in this
                // single pool has ended. Reuse verified private data, never old UI intent.
                if(previous){
                    data->index=previous->index;data->catalog=previous->catalog;
                    if(previous->gates)data->gates=std::move(previous->gates);
                }
                if(existingIndex)data->index=existingIndex;
                if(existingCatalog)data->catalog=existingCatalog;
                if(!data->index){
                    // A source-only build deliberately omits optional curriculum.
                    // Missing content is a held empty state, never a synthetic index
                    // or permission to admit a replacement exercise.
                    if(!std::filesystem::is_directory(resources/"learn-source-index"))
                        throw std::runtime_error("Optional curriculum content is not installed. Free play, User profile and Settings remain available. Back returns to Home.");
                    data->index=learn::SourceIndex::load(resources/"learn-source-index",[ticket]{return ticket->load();});
                }
                if(ticket->load())return;
                juce::MessageManager::callAsync([owner,ticket,index=data->index]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    if(!owner->learnIndexLoaded_){
                        owner->learnIndexLoaded_=owner->lessonView.installPreparedSourceIndex(index);
                        if(!owner->learnIndexLoaded_){owner->cancelLearnLoading();owner->lessonView.loadingStatus("Finish the current Learn queue before changing its verified source index.");return;}
                    }
                    owner->lessonView.loadingStatus(owner->lessonView.catalog()?"Exercise list ready. Preparing other exercise activities in the background.":"Exercise list ready. Preparing Practice and other activities in the background.");
                });
                if(beforeCatalog)beforeCatalog();
                if(ticket->load())return;
                if(!data->catalog)data->catalog=lesson::Catalog::loadInstalled(resources/"representative-controls",extensions,[ticket]{return ticket->load();});
                if(ticket->load())return;
                juce::MessageManager::callAsync([owner,ticket,catalog=data->catalog,resources,onCatalogReady]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    if(owner->lessonView.catalog()!=catalog){
                        if(!owner->lessonView.installPreparedCatalog(catalog,resources,true)){
                            owner->cancelLearnLoading();owner->lessonView.loadingStatus("Finish the current Learn queue before changing its verified catalog.");return;
                        }
                    }
                    owner->lessonView.catalogPreparing(false);
                    owner->lessonView.loadingStatus("Practice ready. Preparing other exercise activities in the background.");
                    if(onCatalogReady)onCatalogReady(*owner);
                });
                for(const auto family:families){if(ticket->load())return;data->gates->loadMissing(resources,ticket,family);}
                if(ticket->load())return;
                juce::MessageManager::callAsync([owner,ticket,data]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    // Consume the prepared gate owner exactly once. Immutable
                    // index/catalog caches remain reusable after publication.
                    auto gates=std::move(data->gates);
                    if(gates)owner->SourceTaskLibraries::merge(std::move(*gates));
                    owner->learnLoadTicket_.reset();owner->lessonView.catalogPreparing(false);owner->lessonView.loadingStatus("");owner->guidedView.setCatalogLoading(false);owner->lessonView.refreshSetup();
                });
            }catch(const std::exception& error){
                const auto message=std::string{"Could not prepare exercises: "}+error.what();
                juce::MessageManager::callAsync([owner,ticket,message]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    owner->learnLoadTicket_.reset();owner->lessonView.catalogPreparing(false);owner->lessonView.loadingStatus(message);
                    if(owner->page_==Page::Guided)owner->guidedView.setCatalogLoading(true,message+" Back remains available.");
                });
            }
        });
        return true;
    }
    bool openWorkbookInLearn(const std::string& workbookId){
        const auto resources=std::filesystem::path{representativeResources().getParentDirectory().getFullPathName().toStdString()};
        int selectedLevel=0;
        for(int level=1;level<=105;++level){char exact[32]{};std::snprintf(exact,sizeof(exact),"fg:workbook:%06d",level);if(workbookId==exact){selectedLevel=level;break;}}
        if(!selectedLevel||lessonView.sourceQueueActive())return false;
        learnReturnPage_=Page::SourceLibrary;lessonView.setBackLabel("Back to workbooks");
        const auto revision=lessonView.sourceSelectionRevision();
        return beginLearnIndexLoading(resources,installedExtensionResources(),[selectedLevel,revision](HomeView& owner){
            if(owner.lessonView.sourceSelectionRevision()==revision)owner.lessonView.showSourceLevel(selectedLevel);
        });
    }
    bool beginGuidedSelectionLoading(const std::filesystem::path& resources,const std::vector<std::filesystem::path>& extensions){
        if(!guidedView.newSessionsEnabled())return false;
        if(!learnResources_.empty()&&(learnResources_!=resources||learnExtensions_!=extensions))return false;
        if(guidedView.holdsSessionOperation())return navigate(Page::Guided);
        std::optional<navigation::AdmissionIdentity> selectedIdentity;
        if(lessonView.catalogReady()&&lessonView.hasExplicitSelection()&&lessonView.selectedPracticeCell()==0){
            try{const auto admitted=lessonView.catalog()->admit(lessonView.selectedLesson(),lessonView.selectedVariant());if(admitted->practiceAllowed())selectedIdentity=navigation::snapshotAdmission(*admitted);}catch(const std::exception&){}
        }
        if(!selectedIdentity||learnSelectedRequests_.empty()){
            if(!navigate(Page::Guided))return false;
            guidedView.setCatalog({});
            guidedView.setCatalogLoading(true,"Choose an admitted whole exercise explicitly in Learn before creating a Guided plan. Return Home, choose Learn, open its sublevel, Preview selection and Exercise details. This page does not prepare every exercise in the library.");
            return true;
        }
        const auto original=lessonView.catalog();const auto requests=learnSelectedRequests_;
        if(!navigate(Page::Guided))return false;
        cancelLearnLoading();learnPreparingIndex_=false;
        auto ticket=std::make_shared<std::atomic<bool>>(false);learnLoadTicket_=ticket;learnLoadingPage_=Page::Guided;
        guidedView.setCatalogLoading(true,"Rechecking the selected exercise's verified source before creating a new Guided plan. Back remains available.");
        const auto store=selectedCatalogStore_;const juce::Component::SafePointer<HomeView> owner{this};
        sourceDataPool().addJob([owner,ticket,store,requests,original,identity=*selectedIdentity]{
            const SourceTaskLibraries::ActiveLoad active;
            try{
                const auto verified=store->prepare(requests,[ticket]{return ticket->load();});
                if(!verified||ticket->load())return;
                juce::MessageManager::callAsync([owner,ticket,verified,original,identity]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    if(owner->page_!=Page::Guided||owner->lessonView.catalog()!=original||verified!=original||owner->lessonView.selectedLesson()!=identity.itemId||owner->lessonView.selectedVariant()!=identity.variantId){
                        owner->learnLoadTicket_.reset();
                        owner->guidedView.setCatalogLoading(true,"The original exercise selection is retained. Choose and verify its sublevel again in Learn before creating a new Guided plan.");return;
                    }
                    owner->finishSelectedGuided(ticket,verified,identity);
                });
            }catch(const std::exception& error){
                const auto message=std::string{"Guided source verification refused: "}+error.what();
                juce::MessageManager::callAsync([owner,ticket,message]{
                    if(!owner||ticket->load()||owner->learnLoadTicket_!=ticket)return;
                    owner->learnLoadTicket_.reset();owner->lessonView.catalogRefused(message);owner->guidedView.setCatalogLoading(true,message+" Reverify the exercise in Learn; Back remains available.");
                });
            }
        });
        return true;
    }
    void finishSelectedGuided(const std::shared_ptr<std::atomic<bool>>& ticket,const std::shared_ptr<const lesson::Catalog>& catalog,const navigation::AdmissionIdentity& identity,unsigned polls=0){
        if(ticket->load()||learnLoadTicket_!=ticket||page_!=Page::Guided)return;
        if(guidedView.busy()){
            if(polls>=100){learnLoadTicket_.reset();guidedView.setCatalogLoading(true,"The original Guided summary is still loading. Back remains available; reopen Guided after it finishes.");return;}
            const juce::Component::SafePointer<HomeView> owner{this};
            juce::Timer::callAfterDelay(50,[owner,ticket,catalog,identity,polls]{if(owner)owner->finishSelectedGuided(ticket,catalog,identity,polls+1);});return;
        }
        learnLoadTicket_.reset();
        if(lessonView.catalog()!=catalog||!lessonView.catalogReady()||lessonView.selectedLesson()!=identity.itemId||lessonView.selectedVariant()!=identity.variantId||guidedView.holdsSessionOperation()){
            guidedView.setCatalogLoading(true,"Retain the original Guided operation and exact exercise selection; return to Learn to reverify before a new plan.");return;
        }
        try{if(!(navigation::snapshotAdmission(*catalog->admit(identity.itemId,identity.variantId))==identity))throw std::runtime_error("Guided admission identity changed");}
        catch(const std::exception& error){lessonView.catalogRefused(error.what());guidedView.setCatalogLoading(true,"Selected Guided admission was refused. Return to Learn to verify the source again.");return;}
        guidedView.setCatalog(catalog);guidedView.selectCase(identity.itemId,identity.variantId);guidedView.setCatalogLoading(false);
        if(!guidedView.buildPlan())guidedView.setCatalogLoading(true,"The exact selected Guided plan could not be prepared. Return to Learn to verify its source; no replacement case was selected.");
    }
    bool beginGuidedLoading(const std::filesystem::path& resources,const std::vector<std::filesystem::path>& extensions,
                            std::function<void()> beforeCatalog={}){
        if(!guidedView.newSessionsEnabled())return false;
        if(!learnResources_.empty()&&(learnResources_!=resources||learnExtensions_!=extensions))return false;
        if(lessonView.catalog())return navigate(Page::Guided);
        return beginLearnLoading(resources,extensions,{},std::move(beforeCatalog),Page::Guided,[](HomeView& owner){
            owner.guidedView.setCatalogLoading(false);owner.lessonView.selectFirstAdmitted();
            owner.navigate(Page::Guided);
        });
    }
    bool beginWorkbookLoading(const std::filesystem::path& resources,const std::vector<std::filesystem::path>& extensions,
                              const std::string& workbookId,std::function<void()> beforeCatalog={}){
        if(!learnResources_.empty()&&(learnResources_!=resources||learnExtensions_!=extensions))return false;
        learnReturnPage_=Page::SourceLibrary;lessonView.setBackLabel("Back to workbooks");
        const auto revision=lessonView.sourceSelectionRevision();
        return beginLearnLoading(resources,extensions,{},std::move(beforeCatalog),Page::Learn,[workbookId,revision](HomeView& owner){
            // Verified catalog publication cannot replace a newer source selection.
            if(owner.lessonView.sourceSelectionRevision()!=revision)return;
            for(const auto& lesson:owner.lessonView.catalog()->lessons()){
                if(lesson.record.object().at("workbook_id").string()!=workbookId)continue;
                if(owner.lessonView.selectLesson(lesson.id))return;
                break;
            }
            owner.lessonView.queueStatus("No installed admitted case is available for this workbook. Its source metadata remains available.");
        });
    }
    static std::vector<std::filesystem::path> installedExtensionResources(){
        const auto root=std::filesystem::path{representativeResources().getParentDirectory().getFullPathName().toStdString()};
        std::vector<std::filesystem::path> paths;
        for(const auto& name:lesson::Catalog::installedExtensionDirectoryNames())paths.push_back(root/name);
        return paths;
    }
    static juce::File representativeResources(){
        const auto executable=juce::File::getSpecialLocation(juce::File::currentApplicationFile);
        const auto bundleResources=executable.getChildFile("Contents/Resources").getChildFile("representative-controls");
        if(bundleResources.isDirectory())return bundleResources;
        const auto adjacentResources=executable.getParentDirectory().getParentDirectory().getChildFile("Resources").getChildFile("representative-controls");
        if(adjacentResources.isDirectory())return adjacentResources;
        const auto workingTreeResources=juce::File::getCurrentWorkingDirectory()
            .getChildFile("Build/development/Fathom_artefacts/Release/Fathom.app/Contents/Resources/representative-controls");
        if(workingTreeResources.isDirectory())return workingTreeResources;
        return adjacentResources;
    }
    static std::filesystem::path installedSourceLibrary(){
        const auto executable=juce::File::getSpecialLocation(juce::File::currentApplicationFile);
        const auto direct=executable.getChildFile("Contents/Resources/source-library");
        if(direct.isDirectory())return std::filesystem::path{direct.getFullPathName().toStdString()};
        const auto adjacent=executable.getParentDirectory().getParentDirectory().getChildFile("Resources/source-library");
        return std::filesystem::path{adjacent.getFullPathName().toStdString()};
    }
    static juce::String pageName(Page page){
        switch(page){case Page::Home:return "Home";case Page::About:return "About";case Page::Onboarding:return "Initial setup";case Page::Setup:return "Guitar setup";case Page::Audio:return "Audio output";case Page::Rhythm:return "Rhythm preview";case Page::Reference:return "Reference tones";case Page::Practice:return "Practice";case Page::Metronome:return "Metronome";case Page::Learn:return "Learn";case Page::ManualTask:return "Manual task";case Page::Progress:return "Progress";case Page::Freeplay:return "Freeplay";case Page::Guided:return "Guided sessions";case Page::SourceLibrary:return "Original workbooks";case Page::RecipeTask:return "Manual exercise";case Page::AdvancedRecipeTask:return "Manual exercise";case Page::CompiledManualProcedure:return "Manual exercise";case Page::EarSourceProcedure:return "Manual exercise";case Page::C43SourceProcedure:return "Manual exercise";case Page::SuiteReview:return "Suite review";case Page::Settings:return "Settings";case Page::UserProfile:return "User profile";case Page::FreeplayMenu:return "Free play";}return "Home";
    }
    bool prepareManualNavigation(bool storeReopen=false){
        if(page_==Page::ManualTask&&!manualTaskView.prepareForNavigation())return false;
        if(page_==Page::RecipeTask&&!recipeTaskView.prepareForNavigation())return false;
        if(page_==Page::AdvancedRecipeTask&&!advancedRecipeTaskView.prepareForNavigation())return false;
        if(page_==Page::CompiledManualProcedure&&!(storeReopen?compiledManualProcedureView.prepareDraftStoreReopen():compiledManualProcedureView.prepareForNavigation()))return false;
        if(page_==Page::EarSourceProcedure&&!earSourceProcedureView.prepareForNavigation())return false;
        if(page_==Page::C43SourceProcedure&&!c43SourceProcedureView.prepareForNavigation())return false;
        return (page_!=Page::ManualTask&&page_!=Page::RecipeTask&&page_!=Page::AdvancedRecipeTask&&page_!=Page::CompiledManualProcedure&&page_!=Page::EarSourceProcedure&&page_!=Page::C43SourceProcedure)||metronomeView.resolveManualPulse();
    }
    void wirePractice(){
        practiceView->onBoardDisplayChanged=[this](const setup::BoardDisplay& value){chooseBoardDisplay(value);};
        // Replacement views receive current presentation without firing a choice or save.
        practiceView->setBoardDisplay(setupPreferences_.model().boardDisplay);
        practiceView->setBoardDisplayStatus(setupPreferences_.statusText());
        practiceView->onPresentationChoice=[this](std::optional<presentation::Level> level){presentation_.choosePage(presentation::Page::Practice,level);applyPresentation();};
        practiceView->canStartNewCapture=[this]{return !originalRecovery_.held()&&!learnFuture_&&learnMutation_==LearnMutation::None;};
        practiceView->onBack=[this]{navigate(learnQueue_||learnFuture_||learnMutation_!=LearnMutation::None?Page::Learn:Page::Home);};
        practiceView->onMetronome=[this]{navigate(Page::Metronome);};
        practiceView->onAudioSettings=[this]{openAudioSettings();};
        practiceView->onAudioPreparation=[this]{if(!learnFuture_&&learnMutation_==LearnMutation::None)audio_.activate(SharedAudioSettings::Consumer::Practice);};
        audio_.bind(SharedAudioSettings::Consumer::Practice,audioEndpoint(*practiceView,"Practice"));
    }
    void applySetupAppearance(){
        appearance::set(setupPreferences_.model().appearance);appearance::apply(*this);
        if(onAppearanceChanged)onAppearanceChanged(setupPreferences_.model().appearance);repaint();
    }
    void applyBoardDisplay(){
        const auto& value=setupPreferences_.model().boardDisplay;
        setup.setBoardDisplay(value);practiceView->setBoardDisplay(value);
    }
    void chooseBoardDisplay(const setup::BoardDisplay& value){
        setup::validateBoardDisplay(value);
        auto model=setupPreferences_.model();model.boardDisplay=value;
        setupPreferences_.choose(model);applyBoardDisplay();requestBoardSave();refreshOnboarding();
    }
    void requestBoardSave(){
        // Only an explicit user choice/Apply arms this save. Profile reads never do.
        boardSaveRequested_=setupPreferences_.hasProfile();
        serviceBoardSave();
    }
    void serviceBoardSave(){
        if(boardSaveRequested_&&!setupPreferences_.dirty())boardSaveRequested_=false;
        if(boardSaveRequested_&&!setupRestorePending_&&setupFinish_==SetupFinish::Idle&&
           setupPreferences_.canSave(presentationStoppedAndResolved())){
            // One proposal per explicit request; failure does not auto-retry.
            boardSaveRequested_=false;setupPreferences_.save(true);
        }
        auto text=setupPreferences_.statusText();
        if(boardSaveRequested_&&setupPreferences_.dirty()&&!setupPreferences_.pending()&&
           (setupPreferences_.state()==setup::PreferenceState::SessionOnly||setupPreferences_.state()==setup::PreferenceState::StopRequired))
            text="Display applies now; saves at Home when resolved.";
        setup.setBoardDisplayStatus(text);practiceView->setBoardDisplayStatus(text);
    }
    void captureSetupOwners(){
        if(setupOwnerRestoreHeld_){const auto retained=setupPreferences_.model();if(!setup.applySetup(retained.guitar)||!audio_.selectMix(retained.audio))return;setupOwnerRestoreHeld_=false;}
        auto model=setupPreferences_.model();model.guitar=setup.currentSetup();model.boardDisplay=setup.draftBoardDisplay();model.audio=audio_.selected();
        model.experience=presentation_.model().globalLevel();setupPreferences_.choose(model);
    }
    void saveSetupDraft(){
        if(setupPreferences_.canSave(presentationStoppedAndResolved()))setupPreferences_.save(true);
    }
    void moveSetupStep(int offset){
        if(originalRecovery_.held()||localProfileOpening_||setupPreferences_.pending()||presentation_.pending()||setupFinish_!=SetupFinish::Idle)return;
        captureSetupOwners();auto model=setupPreferences_.model();
        model.step=static_cast<setup::Step>(std::clamp(static_cast<int>(model.step)+offset,0,5));
        setupPreferences_.choose(model);setupNotice_.clear();saveSetupDraft();refreshOnboarding();
    }
    void skipSetup(){
        if(originalRecovery_.held()||localProfileOpening_||setupPreferences_.pending()||presentation_.pending()||setupFinish_!=SetupFinish::Idle)return;
        captureSetupOwners();auto model=setupPreferences_.model();model.completed=false;model.skipped=true;
        setupPreferences_.choose(model);saveSetupDraft();page_=Page::Home;update();
    }
    bool presentationReadyForSetup()const{
        return presentation_.hasProfile()&&presentation_.observedRevision().has_value()&&!presentation_.pending()&&
            presentation_.state()!=presentation::PreferenceState::Conflict&&
            presentation_.state()!=presentation::PreferenceState::Unsupported&&
            presentation_.state()!=presentation::PreferenceState::Failed;
    }
    void finishSetup(){
        if(originalRecovery_.held()||localProfileOpening_||setupFinish_!=SetupFinish::Idle||setupPreferences_.pending()||presentation_.pending()||!presentationStoppedAndResolved())return;
        captureSetupOwners();auto model=setupPreferences_.model();model.completed=false;model.skipped=false;model.step=setup::Step::Summary;
        setupPreferences_.choose(model);presentation_.chooseGlobal(model.experience);applyPresentation();setupDraftSubmitted_=setupPresentationSubmitted_=false;
        setupFinish_=SetupFinish::Preparing;setupNotice_="Confirming setup and experience before marking setup complete…";
        if(!setupPreferences_.hasProfile()){
            const bool opened=setupCreatingProfile_?(onCreateLocalProfile&&onCreateLocalProfile(newProfileName_)):(onOpenLocalProfile&&onOpenLocalProfile());
            if(!opened){setupFinish_=SetupFinish::Idle;setupNotice_=profileStatus_.empty()?"A local profile was not opened. Your choices remain for this session; retry explicitly or Skip for now.":profileStatus_;}
            // attachPresentation resets its own model; re-establish only this explicit choice.
            if(setupPreferences_.hasProfile())presentation_.chooseGlobal(model.experience);
        }
        refreshOnboarding();
    }
    void refreshOnboarding(){
        onboarding_.setModel(setupPreferences_.model());
        const bool pending=setupPreferences_.pending()||presentation_.pending()||localProfileOpening_;
        const bool future=setupPreferences_.inFlight()||presentation_.inFlight();
        const auto message=originalRecovery_.held()?std::string{"Your existing profile has an unfinished original. It is retained unchanged. Resume profile recovery to review it; new activity stays blocked."}:setupNotice_.empty()?setupPreferences_.statusText():setupNotice_;
        onboarding_.setStatus(message+(presentation_.hasProfile()?"\n"+presentation_.statusText():""));
        const bool gate=presentationStoppedAndResolved();
        onboarding_.setPersistenceState(pending||setupFinish_!=SetupFinish::Idle||originalRecovery_.held(),
            gate&&!pending&&setupFinish_==SetupFinish::Idle&&(!setupPreferences_.hasProfile()||(setupPreferences_.ready()&&presentationReadyForSetup())),
            setupPreferences_.hasProfile()?"Confirmed drafts can resume on this profile. Guitar and audio mix stay editable later; audio permission and playback are never restored.":"No local profile is open. Create Profile begins new-profile setup; Finish setup creates it. Open existing profile loads saved choices.",
            setupPreferences_.hasProfile()&&!future&&setupFinish_==SetupFinish::Idle&&!originalRecovery_.held(),canOpenLocalProfile(),setupPreferences_.hasProfile(),originalRecovery_.held()&&!originalRecovery_.busy());
    }
    void serviceSetup(bool setupPolled){
        if(setupRestorePending_&&!originalRecovery_.held()&&!setupPreferences_.inFlight()&&!presentation_.inFlight()){
            if(setupPreferences_.ready()&&presentationReadyForSetup()&&presentationStoppedAndResolved()){
                if(setupPreferences_.observedRevision()==0){
                    // Legacy profile: preserve canonical disclosure and current guitar/audio.
                    if(setupFinish_==SetupFinish::Idle)captureSetupOwners();
                }else if(!setupPreferences_.dirty()&&setupFinish_==SetupFinish::Idle){
                    const auto model=setupPreferences_.model();
                    if(!setup.applySetup(model.guitar)||!audio_.selectMix(model.audio)){setupNotice_="Saved setup is not fully applied. Guitar or audio mix may already be restored; no audio starts.";refreshOnboarding();return;}
                    applyBoardDisplay();applySetupAppearance();
                    if(presentation_.dirty()){auto newer=model;newer.experience=presentation_.model().globalLevel();setupPreferences_.choose(newer);}
                    // A saved global presentation is authoritative over an older setup draft.
                    // Only profiles without that namespace use the incomplete draft fallback.
                    else if(!model.completed&&presentation_.observedRevision()==0){presentation_.chooseGlobal(model.experience);applyPresentation();}
                    if(!model.completed&&!model.skipped){if(!navigate(Page::Onboarding))return;}
                    else if(page_==Page::Onboarding){if(!navigate(Page::Home))return;}
                }
                setupRestorePending_=false;
            }else if(!setupPreferences_.pending()&&!presentation_.pending()&&(!setupPreferences_.ready()||!presentationReadyForSetup()))setupRestorePending_=false;
        }
        if(setupFinish_!=SetupFinish::Idle){
            if(localProfileOpening_||originalRecovery_.busy()){refreshOnboarding();return;}
            if(originalRecovery_.held()){setupFinish_=SetupFinish::Idle;setupNotice_="Profile created or opened; setup is not complete because an original activity still needs recovery.";refreshOnboarding();return;}
            if(setupRestorePending_){refreshOnboarding();return;}
            if(!setupPreferences_.hasProfile()){refreshOnboarding();return;}
            if(setupPreferences_.inFlight()||presentation_.inFlight()){refreshOnboarding();return;}
            if(!setupPreferences_.ready()||!presentationReadyForSetup()||!presentationStoppedAndResolved()){
                setupFinish_=SetupFinish::Idle;setupNotice_="Setup completion is not confirmed. Inspect the original save or reload before retrying.";
            }else if(setupFinish_==SetupFinish::Preparing){
                if(presentation_.dirty()){
                    if(setupPresentationSubmitted_){setupFinish_=SetupFinish::Idle;setupNotice_="Experience save failed. Retry explicitly; setup is incomplete.";}
                    else{setupPresentationSubmitted_=true;presentation_.save(true);}
                }
                if(setupFinish_==SetupFinish::Preparing&&setupPreferences_.dirty()){
                    if(setupDraftSubmitted_){setupFinish_=SetupFinish::Idle;setupNotice_="Setup draft save failed. Retry explicitly; setup is incomplete.";}
                    else{setupDraftSubmitted_=true;setupPreferences_.save(true);}
                }
                if(setupFinish_==SetupFinish::Preparing&&!presentation_.dirty()&&!setupPreferences_.dirty()&&!presentation_.pending()&&!setupPreferences_.pending()){
                    auto model=setupPreferences_.model();model.completed=true;model.skipped=false;
                    setupPreferences_.choose(model);setupFinish_=SetupFinish::MarkingComplete;setupPreferences_.save(true);
                }
            }else if(!setupPreferences_.dirty()&&!setupPreferences_.pending()){
                setupFinish_=SetupFinish::Idle;setupNotice_="Setup complete and saved. Change it later from Setup / resume setup.";page_=Page::Home;update();
            }else{setupFinish_=SetupFinish::Idle;setupNotice_="Completion marker was not confirmed. The saved draft remains; retry explicitly.";}
        }
        serviceBoardSave();
        if(setupPolled||page_==Page::Onboarding)refreshOnboarding();
    }
    bool consumePresentationChoice(){
        const auto id=presentationChoice_.getSelectedId();
        if(presentationDisplayedChoice_==0||id<1||id>3||id==presentationDisplayedChoice_)return false;
        presentationDisplayedChoice_=id;
        presentation_.chooseGlobal(static_cast<presentation::Level>(id-1));
        return true;
    }
    void syncPresentationChoice(){
        presentationDisplayedChoice_=static_cast<int>(presentation_.model().globalLevel())+1;
        presentationChoice_.setSelectedId(presentationDisplayedChoice_,juce::dontSendNotification);
    }
    void refreshPresentationControls(){
        const auto state=presentation_.state();const bool attention=presentation_.pending()||state==presentation::PreferenceState::Conflict||state==presentation::PreferenceState::Unsupported||state==presentation::PreferenceState::Failed||state==presentation::PreferenceState::Unknown;
        const auto setupState=setupPreferences_.state();const bool setupAttention=setupOwnerRestoreHeld_||setupPreferences_.pending()||setupState==setup::PreferenceState::Conflict||setupState==setup::PreferenceState::Unsupported||setupState==setup::PreferenceState::Failed||setupState==setup::PreferenceState::Unknown;
        homeSettingsNotice_.setVisible(page_==Page::Home&&(attention||setupAttention));
        homeSettingsNotice_.setText((attention||setupAttention)?juce::String::fromUTF8((std::string{"Settings need attention: "}+(attention?presentation_.statusText():setupPreferences_.statusText())+" Open Settings to inspect the original save.").c_str()):juce::String{},juce::dontSendNotification);

        // Leave an explicit queued choice intact until its callback or the
        // timer consumes it. Reset/Reload explicitly discard older choices.
        if(presentationDisplayedChoice_==0||presentationChoice_.getSelectedId()==presentationDisplayedChoice_)syncPresentationChoice();
        presentationSave_.setEnabled(presentation_.canSave(presentationStoppedAndResolved()));
        presentationReload_.setEnabled(presentation_.hasProfile()&&presentation_.state()!=presentation::PreferenceState::Reading&&presentation_.state()!=presentation::PreferenceState::Saving);
        const auto& originalPresentationSave=presentation_.pendingOperationId();
        presentationReload_.setButtonText(originalPresentationSave.empty()?"Reload / check save":"Check original save");
        presentationReload_.setTitle(originalPresentationSave.empty()?"Reload saved presentation or inspect the original uncertain save without issuing a replacement write.":"Check original presentation save "+juce::String::fromUTF8(originalPresentationSave.c_str())+". This reads the same stored proposal and never issues a replacement write.");
        presentationStatus_.setText(juce::String::fromUTF8(presentation_.statusText().c_str()),juce::dontSendNotification);
        presentationStatus_.setTooltip(presentationStatus_.getText()+(originalPresentationSave.empty()?juce::String{}:" Original operation: "+juce::String::fromUTF8(originalPresentationSave.c_str())+". Keep the profile and original proposal; use Check original save."));
    }
    void applyPresentation(){
        consumePresentationChoice();
        const auto& model=presentation_.model();
        lessonView.setPresentation(model.globalLevel(),model.pageOverride(presentation::Page::Learn));
        practiceView->setPresentation(model.globalLevel(),model.pageOverride(presentation::Page::Practice));
        metronomeView.setPresentationLevel(model.globalLevel());
        manualTaskView.setPresentationLevel(model.globalLevel());
        refreshPresentationControls();
    }
    void timerCallback() override { advancedRecipeTaskView.serviceDrafts();recipeTaskView.serviceDrafts();compiledManualProcedureView.serviceDrafts();earSourceProcedureView.serviceDrafts();c43SourceProcedureView.serviceDrafts();originalRecovery_.poll(); const bool setupPolled=setupPreferences_.poll();serviceSetup(setupPolled);const bool chosen=consumePresentationChoice();const bool polled=presentation_.poll();if(chosen||polled)applyPresentation();if(polled)serviceSetup(false);else if(page_==Page::Home||page_==Page::About||page_==Page::Settings||page_==Page::UserProfile)refreshPresentationControls();consumeAppearanceChoice();audio_.observe();refreshNavigationSections();serviceLearnQueue();if(clearQueuePanel_.isVisible())refreshClearLearnQueue();serviceSuiteContinuation();lessonView.refreshQueueControls();if(page_==Page::ManualTask&&(manualTaskView.clockActive()||manualTaskView.pulsePreparing()))metronomeView.service();manualTaskView.service();
        if(pendingLearnEntry_&&page_==Page::Home&&SourceTaskLibraries::activeLoads.load()==0){pendingLearnEntry_=false;if(learnButton.onClick)learnButton.onClick();}
        serviceProfileCase();
        if(originalRecovery_.held()&&originalRecovery_.isVisible())originalRecovery_.toFront(false);
    }
    struct ProfileCase {std::shared_ptr<const lesson::Admission> admission;std::uint16_t bpm;};
    std::optional<ProfileCase> profileCase_;
    bool prepareProfileForCase(std::shared_ptr<const lesson::Admission> selection,std::uint16_t bpm,std::string& reason){
        if(page_!=Page::Learn||profileCase_||localProfileOpening_||!selection||!lessonView.catalogReady()){
            reason="The selected task cannot open a profile while another operation is pending.";return false;
        }
        if(!navigate(Page::Home)){reason="Resolve the original activity before opening a local profile. The selected case stays unchanged.";return false;}
        if(!canOpenLocalProfile()||!onOpenLocalProfile){
            reason="Local saving is unavailable or an original activity is unresolved. The selected case stays unchanged.";page_=Page::Learn;update();return false;
        }
        profileCase_=ProfileCase{std::move(selection),bpm};
        profileStatus_="Opening a local profile for the selected case. Its exact source and variant are retained; preparation will stay stopped.";
        try{if(onOpenLocalProfile()){update();return true;}}
        catch(const std::exception& error){localProfileFailed(error.what());}
        profileCase_.reset();page_=Page::Learn;update();
        reason=profileStatus_.empty()?"No profile was opened. Retry explicitly for this same selected case.":profileStatus_;return false;
    }
    void serviceProfileCase(){
        if(!profileCase_||localProfileOpening_||page_!=Page::Home||!practiceView->captureSession()||setupRestorePending_||
           !setupPreferences_.ready()||!presentationReadyForSetup()||!presentationStoppedAndResolved()||originalRecovery_.held())return;
        const auto selected=*profileCase_;profileCase_.reset();
        try{
            const auto& id=selected.admission->identity().object();
            const auto item=id.at("item_id").string(),variant=id.at("variant_id").string();
            const auto current=lessonView.catalogReady()?lessonView.catalog()->admit(item,variant):nullptr;
            if(!current||current->identity()!=selected.admission->identity())throw std::runtime_error("The retained source revision changed; reselect it explicitly in Learn.");
            lessonView.setSelectedTempo(selected.bpm);
            if(!lessonView.practiceExplicitSelection(item,variant))throw std::runtime_error("Stopped preparation was refused; inspect the retained case in Learn. No activity started.");
            profileStatus_.clear();
        }catch(const std::exception& error){profileStatus_=error.what();navigate(Page::Learn);update();}
    }
    OriginalActivityRecovery originalRecovery_;
    void update() {
        if(originalRecovery_.held()&&originalRecovery_.isVisible())originalRecovery_.toFront(false);
        const bool home=page_==Page::Home||page_==Page::About;
        if(homeRouteStatusPage_!=page_){homeRouteStatus_.setText({},juce::dontSendNotification);homeRouteStatusPage_=page_;}
        homeRoute_.setVisible(!home);homeRouteStatus_.setVisible(!home);
        learnButton.setButtonText("Learn");learnButton.setTitle(homeLearnDetour_?"Resume the retained Learn queue without starting sound or replacing its Session.":"Choose a level and exercise; Start remains explicit.");
        settingsButton_.setVisible(page_==Page::Home);
        if(!home&&homeRouteStatus_.getText().isEmpty())homeRouteStatus_.setText("Fathom / "+juce::String(pageName(page_)),juce::dontSendNotification);
        const bool details=previewDetailsOpen_||page_==Page::About;
        for(auto* c:std::initializer_list<juce::Component*>{&presentationChoice_,&presentationSave_,&presentationReset_,&presentationReload_,&presentationStatus_,&previewDetails_,&onboardingButton_,&settingsHeading_,&settingsHelp_,&settingsPresentationLabel_,&settingsSetupLabel_,&settingsInfoLabel_,&settingsBack_})c->setVisible(page_==Page::Settings);
        previewDetails_.setButtonText("Preview details");
        refreshPresentationControls();
        onboardingButton_.setEnabled(presentationStoppedAndResolved());
        for(auto* c:std::initializer_list<juce::Component*>{&heading,&subtitle,&message,&detail,&learnPracticeLabel,&activitiesLabel,&audioToolsLabel,&about,&quit,&setupButton,&outputButton,&scheduleButton,&referenceButton,&practiceButton,&metronomeButton,&learnButton,&startLearningButton,&localProfileButton,&sourceLibraryButton,&progressButton,&freeplayButton,&guidedButton})c->setVisible(home);
        detail.setVisible(home&&details);
        for(auto* c:std::initializer_list<juce::Component*>{&learnPracticeLabel,&activitiesLabel,&audioToolsLabel,&outputButton,&scheduleButton,&referenceButton,&practiceButton,&metronomeButton,&learnButton,&startLearningButton,&localProfileButton,&sourceLibraryButton,&progressButton,&freeplayButton,&guidedButton})c->setVisible(home&&!details);
        startLearningButton.setVisible(false);
        onboarding_.setVisible(page_==Page::Onboarding);
        setup.setVisible(page_==Page::Setup);outputView.setVisible(page_==Page::Audio);scheduleView.setVisible(page_==Page::Rhythm);
        referenceView.setVisible(page_==Page::Reference);practiceView->setVisible(page_==Page::Practice);metronomeView.setVisible(page_==Page::Metronome);lessonView.setVisible(page_==Page::Learn);manualTaskView.setVisible(page_==Page::ManualTask);progressView.setVisible(page_==Page::Progress);freeplayView.setVisible(page_==Page::Freeplay);guidedView.setVisible(page_==Page::Guided);
        recipeTaskView.setVisible(page_==Page::RecipeTask);
        advancedRecipeTaskView.setVisible(page_==Page::AdvancedRecipeTask);
        compiledManualProcedureView.setVisible(page_==Page::CompiledManualProcedure);
        earSourceProcedureView.setVisible(page_==Page::EarSourceProcedure);
        c43SourceProcedureView.setVisible(page_==Page::C43SourceProcedure);
        sourceLibraryView.setVisible(page_==Page::SourceLibrary);suiteReviewView_.setVisible(page_==Page::SuiteReview);
        if(page_==Page::Learn&&lessonView.getPeer()!=nullptr){
            const auto eligible=[this](juce::Component* c){return c&&lessonView.isParentOf(c)&&c->isShowing()&&c->isEnabled()&&c->getWantsKeyboardFocus();};
            // Hiding the previous page can leave no target from which Tab can traverse.
            // Preserve a valid Learn focus; seed only a newly visible eligible descendant.
            if(!eligible(juce::Component::getCurrentlyFocusedComponent()))
                if(auto traversal=lessonView.createKeyboardFocusTraverser())
                    if(auto* target=traversal->getDefaultComponent(&lessonView);eligible(target))target->grabKeyboardFocus();
        }
        applyNavigationSections();
        resized();
        if(page_==Page::Practice)practiceView->grabKeyboardFocus();
        if(page_==Page::Metronome)metronomeView.grabKeyboardFocus();
        if(page_==Page::ManualTask)manualTaskView.grabKeyboardFocus();
        if(page_==Page::RecipeTask)recipeTaskView.grabKeyboardFocus();
        if(page_==Page::AdvancedRecipeTask)advancedRecipeTaskView.grabKeyboardFocus();
        if(page_==Page::CompiledManualProcedure)compiledManualProcedureView.grabKeyboardFocus();
        if(page_==Page::EarSourceProcedure)earSourceProcedureView.grabKeyboardFocus();
        if(page_==Page::C43SourceProcedure)c43SourceProcedureView.grabKeyboardFocus();
        if(page_==Page::Audio)outputView.grabKeyboardFocus();
        if(page_==Page::Freeplay)freeplayView.grabKeyboardFocus();
        if(page_==Page::Guided)guidedView.grabKeyboardFocus();
        if(page_==Page::SourceLibrary)sourceLibraryView.grabKeyboardFocus();
        auto installedCatalogSummary=std::string{"Installed lesson catalog: not loaded yet; open Learn to inspect selected cases and their individual Practice admission."};
        if(const auto catalog=lessonView.catalog()){
            const auto selectedCaseCount=catalog->lessons().size();std::size_t variantCount=0;std::set<std::string> workbooks;
            for(const auto& record:catalog->lessons()){variantCount+=record.variants.size();workbooks.insert(record.record.object().at("workbook_id").string());}
            installedCatalogSummary="Installed lesson catalog: "+std::to_string(selectedCaseCount)+" selected source-backed cases | "+std::to_string(variantCount)+" variants | "+std::to_string(catalog->sourceEntryCount())+" retained source entries across "+std::to_string(workbooks.size())+" workbook identities. Practice admission is checked separately for each selected case.";
        }
        const auto aboutText=std::string{"A quiet place to build your guitar practice.\n\nLearn requires separately installed optional curriculum content. Choose an installed level and exercise in Learn. Free play is independent practice. Guided sessions are disabled; retained originals remain available for safe resolution in User profile. Progress shows saved local activity.\n\nOpening pages does not start Practice or create completion credit. This is an offline macOS Development Preview."};
        const bool hasLearnSelection=lessonView.catalog()&&lessonView.hasExplicitSelection()&&!lessonView.selectedLesson().empty()&&!lessonView.selectedVariant().empty();
        const bool profileAttached=practiceView->captureSession()!=nullptr;
        localProfileButton.setButtonText(originalRecovery_.held()?"Resume profile recovery":profileAttached?"Local profile ready":"Open existing profile");
        localProfileButton.setEnabled(originalRecovery_.held()?!originalRecovery_.busy():!profileAttached&&canOpenLocalProfile());
        localProfileButton.setTitle(profileStatus_.empty()?"Open an existing local profile; no activity or audio starts. Create a named profile through Setup / resume setup.":profileStatus_);
        const auto profileBoundary=profileAttached
            ? std::string{"Local profile ready. Start stays explicit; save your result before leaving an active exercise."}
            : std::string{"Open User profile to create or open a named local profile."};
        const auto homeGuidance=std::string{"Choose Learn for exercises or Free play for independent practice and audio tools.\nUser profile contains history and instrument preferences.\n"}+profileBoundary;
        heading.setText(page_==Page::About?"About Fathom":"Fathom",juce::dontSendNotification);
        const auto visibleGuidance=(sourceCloseStatus_.empty()?std::string{}:sourceCloseStatus_+"\n\n")+(pendingLearnEntry_?std::string{"Finishing earlier preparation before opening Learn. Home remains available.\n\n"}:std::string{})+(profileStatus_.empty()?homeGuidance:profileStatus_+"\n\n"+homeGuidance);
        message.setText(page_==Page::About?juce::String::fromUTF8(aboutText.c_str()):juce::String::fromUTF8(visibleGuidance.c_str()),juce::dontSendNotification);
        // Labels describe destinations, independently of background catalog defaults.
        practiceButton.setButtonText("Exercise details");
        practiceButton.setTitle(hasLearnSelection?"Review the current exercise in Learn. Opening details does not start Practice.":"Choose an exercise in Learn first. Opening details does not start Practice.");
        practiceButton.setEnabled(hasLearnSelection);
        const auto catalogState = lessonView.catalog()
            ? std::string{"Catalog state: retained source-backed catalog loaded from the Development Preview bundle; selection remains read-only until explicit Practice."}
            : std::string{"Catalog state: retained source-backed catalog not loaded yet; choose Learn to load it."};
        const bool learnContentPresent=representativeResources().getParentDirectory().getChildFile("learn-source-index").isDirectory();
        const bool workbookContentPresent=std::filesystem::is_directory(installedSourceLibrary());
        const auto optionalContentSummary=std::string{learnContentPresent
            ? "Optional Learn content is present; open Learn to verify its exact supported contents. "
            : "Optional Learn content is not installed. "}
            +(workbookContentPresent
                ? "Optional workbook library is present; open Exercise library to verify its exact supported contents. "
                : "Optional workbook library is not installed. ")
            +"Free play, User profile and Settings are available.";
        auto detailText=std::string{"Development Preview | "+optionalContentSummary+"\n"+installedCatalogSummary+"\nWhole-workbook completion: 0 | Curriculum review Pending\nVisible MVP paths: Home → Learn → admitted Practice → Save result → Progress; Home → Free play → explicit timer/audio tools; User profile → Progress/history. Guided new sessions are disabled.\nAudio settings are shared across activities. Configure speakers and headphones in Audio settings for Practice, Learn, Freeplay, Guided and rhythm tools.\nProfile boundary: "+profileBoundary+"\n"+catalogState};
        if(!lessonView.selectedLesson().empty()&&!lessonView.selectedVariant().empty()) {
            detailText += "\nCurrent Learn selection: "+lessonView.selectedLesson()+" / "+lessonView.selectedVariant()+". Practice remains explicit; selection creates no Attempt or curriculum credit.";
            try {
                if(const auto catalog=lessonView.catalog()) {
                    const auto& record=catalog->lesson(lessonView.selectedLesson()).record.object();
                    const auto& sourceRefs=catalog->variant(lessonView.selectedLesson(),lessonView.selectedVariant()).model->source().sourceRefs;
                    detailText += "\nSource refs: ";
                    for(std::size_t index=0;index<sourceRefs.size();++index) {
                        if(index!=0) detailText += ", ";
                        detailText += sourceRefs[index];
                    }
                    detailText += "\nContent version: "+catalog->contentVersion(lessonView.selectedLesson())+" | Content revision: "+storage::canonical(record.at("content_revision"))+" | Workbook identity: "+record.at("workbook_id").string()+" | Level: "+storage::canonical(record.at("legacy_level"));
                    detailText += "\nLesson title: "+catalog->lesson(lessonView.selectedLesson()).title;
                    detailText += "\nSelected variant: "+catalog->variant(lessonView.selectedLesson(),lessonView.selectedVariant()).label;
                }
            } catch(const std::exception&) {
                // Preserve the exact selected-ID context if a loaded preview lacks provenance.
            }
        }
        detail.setText(juce::String::fromUTF8(detailText.c_str()),juce::dontSendNotification);
        about.setButtonText(page_==Page::About?"Back":"About this preview");about.setTitle(page_==Page::About?"Return to Home from the preview details.":"Show the offline Development Preview scope and review status.");
        std::cout<<"view="<<pageName(page_)<<std::endl;
    }

    bool canReviewGuidedOriginal()const{return guidedView.holdsSessionOperation()||(!guidedView.sessionId().empty()&&!guidedView.presentationStoppedAndResolved());}
    void saveProfilePreferences(){
        if(!presentationStoppedAndResolved()||!setupPreferences_.supported()||setupPreferences_.pending())return;
        const auto text=profileBpm_.getText();const int bpm=text.getIntValue();
        if(text.isEmpty()||!text.containsOnly("0123456789")||bpm<20||bpm>300){profilePreferenceNotice_="Enter a whole default BPM from 20 to 300.";refreshNavigationSections();return;}
        captureSetupOwners();auto model=setupPreferences_.model();model.defaultBpm=bpm;setupPreferences_.choose(model);profileBpmEdited_=false;profileBpmDisplayed_=profileBpm_.getText().toStdString();profilePreferenceNotice_.clear();saveSetupDraft();refreshNavigationSections();
    }
    bool consumeAppearanceChoice(){const int id=appearanceChoice_.getSelectedId();if(appearanceDisplayedChoice_==0||id<1||id>3||id==appearanceDisplayedChoice_)return false;appearanceDisplayedChoice_=id;auto model=setupPreferences_.model();model.appearance=static_cast<setup::Appearance>(id-1);setupPreferences_.choose(model);applySetupAppearance();refreshNavigationSections();return true;}
    void refreshNavigationSections(){
        if(applyProfileReload_&&!setupPreferences_.inFlight()&&setupPreferences_.ready()&&presentationStoppedAndResolved()){
            const auto& restored=setupPreferences_.model();if(setup.applySetup(restored.guitar)&&audio_.selectMix(restored.audio)){applyBoardDisplay();applySetupAppearance();applyProfileReload_=false;}
        }
        lessonView.setDefaultTempoValue(static_cast<std::uint16_t>(setupPreferences_.model().defaultBpm));
        const bool newBinding=profileBpmIdentity_!=setupPreferences_.profileIdentity();
        if(newBinding){profileBpmIdentity_=setupPreferences_.profileIdentity();profileBpmEdited_=false;appearanceDisplayedChoice_=0;}
        else if(profileBpm_.getText().toStdString()!=profileBpmDisplayed_)profileBpmEdited_=true;
        if(!profileBpmEdited_){profileBpmDisplayed_=std::to_string(setupPreferences_.model().defaultBpm);profileBpm_.setText(juce::String::fromUTF8(profileBpmDisplayed_.c_str()),false);}
        if(appearanceDisplayedChoice_==0||appearanceChoice_.getSelectedId()==appearanceDisplayedChoice_){appearanceDisplayedChoice_=static_cast<int>(setupPreferences_.model().appearance)+1;appearanceChoice_.setSelectedId(appearanceDisplayedChoice_,juce::dontSendNotification);}
        const bool gate=presentationStoppedAndResolved();
        profileSave_.setEnabled(gate&&setupPreferences_.supported()&&!setupPreferences_.pending()&&(profileBpmEdited_||setupPreferences_.dirty()));
        profileReload_.setEnabled(setupPreferences_.hasProfile()&&!setupPreferences_.inFlight());uiSave_.setEnabled(setupPreferences_.canSave(gate));uiReload_.setEnabled(setupPreferences_.hasProfile()&&!setupPreferences_.inFlight());
        profileStatusLabel_.setText(juce::String::fromUTF8((profilePreferenceNotice_.empty()?setupPreferences_.statusText():profilePreferenceNotice_).c_str()),juce::dontSendNotification);uiStatus_.setText(juce::String::fromUTF8(setupPreferences_.statusText().c_str()),juce::dontSendNotification);
        profileIdentity_.setTooltip(juce::String::fromUTF8(profileSummary_.c_str()));
        profileIdentity_.setText(juce::String::fromUTF8((profileSummary_.empty()?"No named local profile is open. Create or open one below.":profileSummary_).c_str()),false);
        freeplaySessionButton_.setButtonText(freeplayView.presentationStoppedAndResolved()?"Free play session":"Resume Free play");
        if(page_==Page::UserProfile)guidedRecoveryButton_.setVisible(canReviewGuidedOriginal());
        if(page_==Page::Home&&canReviewGuidedOriginal())homeSettingsNotice_.setText("An unfinished Guided session is retained. Open User profile > Resolve retained Guided session. New Guided sessions are disabled; nothing was discarded.",juce::dontSendNotification);
        if(page_==Page::Home&&canReviewGuidedOriginal())homeSettingsNotice_.setVisible(true);
        if(page_==Page::Home&&originalRecovery_.held()){homeSettingsNotice_.setText("An unfinished original activity is retained. Open User profile and Resume profile recovery; new activity is blocked until the original is resolved.",juce::dontSendNotification);homeSettingsNotice_.setVisible(true);}
    }
    void applyNavigationSections(){
        const bool profile=page_==Page::UserProfile,free=page_==Page::FreeplayMenu,settings=page_==Page::Settings;
        for(auto* c:std::initializer_list<juce::Component*>{&learnPracticeLabel,&activitiesLabel,&audioToolsLabel,&practiceButton,&guidedButton,&progressButton,&setupButton,&localProfileButton,&sourceLibraryButton,&metronomeButton,&scheduleButton,&referenceButton,&outputButton,&about})c->setVisible(false);
        learnButton.setVisible(page_==Page::Home);freeplayButton.setVisible(page_==Page::Home);settingsButton_.setVisible(page_==Page::Home);quit.setVisible(page_==Page::Home);userProfileButton_.setVisible(page_==Page::Home);
        for(auto* c:std::initializer_list<juce::Component*>{&sectionHeading_,&sectionHelp_,&sectionBack_})c->setVisible(profile||free);
        for(auto* c:std::initializer_list<juce::Component*>{&progressButton,&localProfileButton,&setupButton,&onboardingButton_,&profileIdentity_,&profileBpmLabel_,&profileBpm_,&profileSave_,&profileReload_,&profileStatusLabel_})c->setVisible(profile);
        guidedRecoveryButton_.setVisible(profile&&canReviewGuidedOriginal());
        for(auto* c:std::initializer_list<juce::Component*>{&freeplaySessionButton_,&metronomeButton,&scheduleButton,&referenceButton,&outputButton})c->setVisible(free);
        sourceLibraryButton.setVisible(page_==Page::Learn);about.setVisible(page_==Page::About);
        for(auto* c:std::initializer_list<juce::Component*>{&appearanceChoice_,&uiSave_,&uiReload_,&uiStatus_})c->setVisible(settings);
        settingsSetupLabel_.setText("APPEARANCE",juce::dontSendNotification);settingsHelp_.setText("Presentation and appearance change the interface. Personal learning, profile and guitar preferences are in User profile. No setting starts audio or grants permissions.",juce::dontSendNotification);
        if(profile){sectionHeading_.setText("User profile",juce::dontSendNotification);sectionHelp_.setText("Default BPM applies only to new Learn selections. Existing queues, metronome presets and recorded tempos stay unchanged. Use Guitar setup for tuning, capo and frets. Stop and resolve current activity before saving preferences.",juce::dontSendNotification);setupButton.setEnabled(presentationStoppedAndResolved());onboardingButton_.setEnabled(presentationStoppedAndResolved());}
        if(free){sectionHeading_.setText("Free play",juce::dontSendNotification);sectionHelp_.setText("Choose the independent Free play timer or an audio tool. Opening a tool never starts sound. Stop or pause and resolve saved work before leaving; each Back returns to its original caller.",juce::dontSendNotification);}
        refreshNavigationSections();
    }
    bool canClearLearnQueue(std::string& reason)const{
        if(originalRecovery_.held()||localProfileOpening_){reason="Resolve the original profile recovery before clearing a queue.";return false;}
        if(learnFuture_||learnMutation_!=LearnMutation::None){reason="Wait for or retry the original Session operation. The queue and its request are retained.";return false;}
        if(!practiceView->audioCanRelease()||!audio_.canRelease()||!freeplayView.canLeave()||!guidedView.canClose()){
            reason="Unsaved work or audio cleanup remains. Return to current Practice and use its existing Stop / Save / return controls. Stop alone does not discard work.";return false;}
        if(learnQueue_&&!canAdvanceLearnQueue()){reason="Resolve the current original result in Practice before clearing. Nothing has been discarded.";return false;}
        reason.clear();return true;
    }
    void requestClearLearnQueue(){
        if(clearQueueRequested_||clearQueuePanel_.isVisible()||(page_!=Page::Home&&page_!=Page::Learn))return;
        if(!learnQueue_&&!learnSuite_&&!lessonView.hasRetainedSourcePlan())return;
        clearQueueDisabled_.clear();for(auto* c:getChildren())if(c!=&clearQueuePanel_){clearQueueDisabled_.push_back({c,c->isEnabled()});c->setEnabled(false);}
        clearQueuePanel_.setVisible(true);refreshClearLearnQueue();clearQueuePanel_.toFront(false);
    }
    void closeClearLearnPanel(){clearQueuePanel_.setVisible(false);for(auto& saved:clearQueueDisabled_)if(saved.first)saved.first->setEnabled(saved.second);clearQueueDisabled_.clear();}
    void refreshClearLearnQueue(){for(auto& saved:clearQueueDisabled_)if(saved.first)saved.first->setEnabled(false);std::string reason;const bool ready=canClearLearnQueue(reason);clearQueuePanel_.present(ready&&!clearQueueRequested_,clearQueueRequested_,reason);clearQueuePanel_.allowRetry(clearQueueRequested_&&!learnFuture_&&learnMutation_!=LearnMutation::None);}
    void confirmClearLearnQueue(){
        std::string reason;if(!clearQueuePanel_.isVisible()||clearQueueRequested_||!canClearLearnQueue(reason)){refreshClearLearnQueue();return;}
        clearQueueRequested_=true;suiteContinuation_=SuiteContinuation::None;suiteAutoAdvanceAllowed_=false;suiteAdvanceAfterClose_=false;
        serviceClearLearnQueue();refreshClearLearnQueue();
    }
    void serviceClearLearnQueue(){
        if(!clearQueueRequested_||learnFuture_||learnMutation_!=LearnMutation::None)return;
        std::string reason;
        if(learnQueue_){if(!advanceLearnQueue(reason))clearQueuePanel_.present(false,true,reason);return;}
        if(learnSuite_&&!suiteReviewSaved_){learnOperation_="learn-suite/clear/"+storage::newUuid();learnAt_=desktopUtcNow();learnMutation_=LearnMutation::ClearSuite;submitLearnMutation(reason);return;}
        finishClearLearnQueue();
    }
    void finishClearLearnQueue(){
        // All durable closes are confirmed before releasing in-memory owners.
        lessonView.setQueueOwnership(false);lessonView.clearQueuePending();
        learnQueue_=nullptr;suiteQueue_=nullptr;learnSuite_.reset();suiteReviewSaved_=false;suiteCompletedCount_=0;
        suiteContinuation_=SuiteContinuation::None;suiteAdvanceAfterClose_=false;suiteAutoAdvanceAllowed_=false;practiceView->setSuiteMode(false);
        homeLearnDetour_=false;pendingLearnEntry_=false;cancelLearnLoading();
        if(!lessonView.clearQueueSelection()){clearQueuePanel_.present(false,true,"Queue closure is confirmed; selection cleanup needs attention.");return;}
        clearQueueRequested_=false;closeClearLearnPanel();page_=Page::Learn;update();
    }
    void submitFinalSuiteReview(json::Value score){
        if(!learnSuite_||learnFuture_||suiteReviewSaved_)return;
        if(learnMutation_==LearnMutation::ReviewSuite)return; // Retry retains the original chosen score.
        if(learnMutation_!=LearnMutation::None)return;
        learnSuite_->freeze();suiteReviewView_.retainOriginalScore();suiteScore_=std::move(score);learnOperation_="learn-suite/review/"+storage::newUuid();learnAt_=desktopUtcNow();learnMutation_=LearnMutation::ReviewSuite;std::string reason;submitLearnMutation(reason);
    }
    void serviceSuiteContinuation(){
        if(clearQueuePanel_.isVisible()||clearQueueRequested_)return;
        if(!learnSuite_||learnFuture_||learnMutation_!=LearnMutation::None||!learnQueue_)return;
        if(suiteAutoAdvanceAllowed_&&practiceView->suiteNaturalCompleted()){
            suiteOutputCapability_=settingsOutputCapability();suiteAppendOwner_=practiceView->captureSession()->binding().owner;learnOperation_="learn-suite/member/"+storage::newUuid();learnAt_=desktopUtcNow();learnMutation_=LearnMutation::AppendSuiteMember;std::string reason;submitLearnMutation(reason);return;
        }
        if(suiteContinuation_==SuiteContinuation::None)return;
        const auto hold=[this](const char* why){suiteContinuation_=SuiteContinuation::None;lessonView.queueStatus(why);};
        if(page_!=Page::Practice||std::chrono::steady_clock::now()>suiteContinuationDeadline_){hold("Automatic continuation paused. Resolve the current exercise; nothing is skipped or scored.");return;}
        const auto cap=settingsOutputCapability();if(!sameAudioCapability(cap,suiteOutputCapability_)){hold("Audio output changed. Inspect Audio settings before continuing the suite.");return;}
        const auto state=practiceView->audioSnapshot().state;
        if(suiteContinuation_==SuiteContinuation::Connect){if(state==output::State::Ready){suiteContinuation_=SuiteContinuation::Ready;return;}if(state==output::State::Observed){suiteContinuation_=SuiteContinuation::Observed;return;}if(state==output::State::Awaiting)return;if(state!=output::State::Closed||!audio_.connect()){hold("Automatic suite output preparation needs attention.");return;}suiteContinuation_=SuiteContinuation::Observed;return;}
        if(suiteContinuation_==SuiteContinuation::Observed&&state==output::State::Ready){suiteContinuation_=SuiteContinuation::Ready;return;}
        if(suiteContinuation_==SuiteContinuation::Observed&&state==output::State::Observed){if(!audio_.enable()){hold("Automatic suite output enable was refused; retain the current exercise.");return;}suiteContinuation_=SuiteContinuation::Ready;return;}
        if(suiteContinuation_==SuiteContinuation::Ready&&state==output::State::Ready){suiteContinuation_=SuiteContinuation::None;if(!practiceView->startSample())hold("Automatic suite Start was refused; no exercise is skipped.");return;}
        if(state==output::State::Fault||state==output::State::Unresolved)hold("Automatic continuation paused for the original output fault.");
    }
    enum class LearnMutation { None, Create, Close, CloseFailedPreparation, BeginSuite, AppendSuiteMember, ReviewSuite, ReadSuite, ClearSuite };
    enum class SuiteContinuation { None, Connect, Observed, Ready };
    storage::ProfileStore* learnStore_{};
    PracticeQueueHeader practiceQueueHeader_;
    std::string upcomingTabError_;
    const navigation::ExerciseQueue* upcomingTabQueue_{};
    std::size_t upcomingTabPosition_{};
    std::shared_ptr<const tab::Document> upcomingTabActive_;
    SuiteReviewView suiteReviewView_;
    std::unique_ptr<navigation::ExerciseSuiteReview> learnSuite_;
    json::Value suitePlan_,suiteScore_;
    std::string suiteAppendOwner_;
    std::size_t suiteCompletedCount_{};
    bool suiteReviewSaved_{},suiteAdvanceAfterClose_{},suiteAutoAdvanceAllowed_{true};
    SuiteContinuation suiteContinuation_{SuiteContinuation::None};
    std::chrono::steady_clock::time_point suiteContinuationDeadline_;
    platform::OutputCapability suiteOutputCapability_;
    navigation::ExerciseQueue* suiteQueue_{};
    navigation::ExerciseQueue* learnQueue_{}; // LessonView cannot replace an open/pending queue.
    std::optional<storage::ProfileStore::Future> learnFuture_;
    LearnMutation learnMutation_{LearnMutation::None};
    std::string learnTimezone_,learnPreviewSession_,learnOperation_,learnAt_,learnSession_,learnOutcome_,learnFailure_,learnBaselineAttempt_;
    json::Value learnPlan_;
    std::uint16_t learnBpm_{60};
    std::optional<navigation::ExerciseResolution> learnReceipt_;
    bool learnIndexLoaded_{};
    bool learnFail(std::string& reason,const std::string& message){reason=message;lessonView.queueStatus(message,learnFuture_.has_value());return false;}
    bool openLearnQueue(navigation::ExerciseQueue& queue,std::uint16_t bpm,std::string& reason){
        if(clearQueuePanel_.isVisible()||clearQueueRequested_)return learnFail(reason,"Finish or cancel the queue reset first.");
        if(learnQueue_||learnFuture_||learnMutation_!=LearnMutation::None)return learnFail(reason,"A Learn Session operation is already pending; retain or retry it.");
        if(learnSuite_&&suiteQueue_!=&queue)return learnFail(reason,"Finish the retained suite review before choosing another suite.");
        if(!learnStore_||learnTimezone_.empty()||!practiceView->captureSession())return learnFail(reason,"Create or open a local profile on Home first.");
        if(guidedView.running())return learnFail(reason,"Finish the active Guided Session before starting an independent Learn queue.");
        if(queue.phase()!=navigation::ExerciseQueuePhase::Ready||!practiceView->audioCanRelease()||!audio_.canRelease())return learnFail(reason,"Finish and save the current activity before opening another exercise.");
        try{
            auto admission=navigation::resolveExerciseAdmission(*lessonView.catalog(),*queue.current());
            admission->practiceConfiguration(44100,bpm);
            learnPlan_=json::Value::Object{{"version","learn-exercise-session.1"},{"source_identity",queue.current()->sourceExerciseKey},{"index_revision",queue.current()->indexRevision},{"item_id",queue.current()->admission->itemId},{"variant_id",queue.current()->admission->variantId},{"source_binding",queue.current()->admission->sourceBinding},{"source_task_completion",false},{"synthetic_fixture",false}};
            if(learnSuite_)learnPlan_.object()["suite_id"]=learnSuite_->suiteId();
            learnQueue_=&queue;lessonView.setQueueOwnership(true);learnBpm_=bpm;learnSession_.clear();learnReceipt_.reset();learnFailure_.clear();
            if(queue.size()>1&&!learnSuite_){
                json::Value::Array items;
                for(std::size_t i=0;i<queue.size();++i){const auto& entry=*queue.entryAt(i);const auto exact=navigation::resolveExerciseAdmission(*lessonView.catalog(),entry);
                    json::Value::Object item;for(const auto* key:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs"})item.emplace(key,exact->identity().object().at(key));item["source_binding"]=exact->sourceBinding();item["source_exercise_key"]=entry.sourceExerciseKey;item["index_revision"]=entry.indexRevision;item["source_revision"]=entry.sourceRevision;item["level_key"]=entry.levelKey;item["sublevel_key"]=entry.sublevelKey;item["source_order"]=json::Value::fromInteger(entry.sourceOrder);item["level_order"]=json::Value::fromInteger(entry.levelOrder);items.emplace_back(std::move(item));}
                suitePlan_=json::Value::Object{{"version",json::Value::fromInteger(1)},{"items",std::move(items)}};
                learnSuite_=std::make_unique<navigation::ExerciseSuiteReview>(storage::newUuid());suiteQueue_=&queue;suiteCompletedCount_=0;suiteReviewSaved_=false;suiteAutoAdvanceAllowed_=true;
                learnOperation_="learn-suite/begin/"+storage::newUuid();learnAt_=desktopUtcNow();learnMutation_=LearnMutation::BeginSuite;
            }else{learnOperation_="learn-exercise/create/"+storage::newUuid();learnAt_=desktopUtcNow();learnMutation_=LearnMutation::Create;}
            practiceView->setSuiteMode(queue.size()>1);if(queue.size()>1)suiteAutoAdvanceAllowed_=true;
            return submitLearnMutation(reason);
        }catch(const std::exception& error){return learnFail(reason,error.what());}
    }
    bool submitLearnMutation(std::string& reason){
        if(!learnStore_||learnFuture_||learnMutation_==LearnMutation::None)return learnFail(reason,"The original Learn Session operation is unavailable or still pending.");
        try{
            if(learnMutation_==LearnMutation::ReadSuite)learnFuture_.emplace(learnStore_->readSuite(learnOperation_,""));
            else if(learnMutation_==LearnMutation::BeginSuite)learnFuture_.emplace(learnStore_->beginSuite(learnOperation_,learnSuite_->suiteId(),learnAt_,suitePlan_));
            else if(learnMutation_==LearnMutation::AppendSuiteMember)learnFuture_.emplace(learnStore_->appendSuiteMember(learnOperation_,learnSuite_->suiteId(),suiteAppendOwner_,learnAt_));
            else if(learnMutation_==LearnMutation::ClearSuite)learnFuture_.emplace(learnStore_->submitSuiteReview(learnOperation_,learnSuite_->suiteId(),learnAt_,json::Value{}));
            else if(learnMutation_==LearnMutation::ReviewSuite)learnFuture_.emplace(learnStore_->submitSuiteReview(learnOperation_,learnSuite_->suiteId(),learnAt_,suiteScore_));
            else if(learnMutation_==LearnMutation::Create){
                // Reserve once before submission; retry must recover this exact
                // Session after a lost receipt rather than allocate another one.
                if(learnSession_.empty()){learnSession_=storage::newUuid();learnPlan_.object()["original_start_operation"]=learnOperation_;learnPlan_.object()["original_session_id"]=learnSession_;}
                learnFuture_.emplace(learnStore_->createSessionWithIdentity(learnOperation_,learnSession_,learnAt_,learnTimezone_,std::optional<std::int64_t>{},learnPlan_));
            }
            else learnFuture_.emplace(learnStore_->closeSession(learnOperation_,learnSession_,learnAt_,learnOutcome_));
            if(learnMutation_==LearnMutation::ReviewSuite)suiteReviewView_.present(suiteCompletedCount_,"Saving the original final review…",true,false);
            if(learnMutation_!=LearnMutation::ReadSuite)
                lessonView.queueStatus(learnMutation_==LearnMutation::Create?"Creating this exercise's own Session; no Attempt has started.":"Closing the original exercise Session; saved Attempts remain unchanged.",true);
            return true;
        }catch(const std::exception& error){return learnFail(reason,std::string{"Session operation could not be submitted. Retry retains the same operation: "}+error.what());}
    }
    bool restoreLearnPreviewOwner(){
        if(!practiceView->captureSession()||!practiceView->audioRelease())return false;
        if(practiceView->captureSession()->phase()==capture::SessionPhase::Saved&&!practiceView->againSample())return false;
        return practiceView->captureSessionId()==learnPreviewSession_||practiceView->rebindCaptureSession(learnPreviewSession_);
    }
    learn::QueueCaptureResult learnCaptureResult()const{
        const auto* current=practiceView->captureSession();
        if(!current)return learn::QueueCaptureResult::Unresolved;
        learn::QueueCaptureEvidence evidence;
        evidence.phase=current->phase()==capture::SessionPhase::Saved?learn::QueueCapturePhase::Saved:current->phase()==capture::SessionPhase::Idle?learn::QueueCapturePhase::Idle:learn::QueueCapturePhase::Other;
        evidence.canLeave=practiceView->audioCanRelease();
        evidence.expectedSession=learnSession_;evidence.currentSession=practiceView->captureSessionId();
        evidence.owner=current->binding().owner;evidence.baselineOwner=learnBaselineAttempt_;
        if(const auto& original=current->original()){
            evidence.originalOwner=original->owner;evidence.originalKind=original->kind;
            if(const auto* context=original->value.find("context"))if(const auto* session=context->find("session_id"))if(session->isString())evidence.originalSession=session->string();
            try{evidence.originalContextMatches=original->contextBytes==storage::canonical(current->binding().context);}catch(const std::exception&){return learn::QueueCaptureResult::Unresolved;}
        }
        return learn::queueCaptureResult(evidence);
    }
    bool canAdvanceLearnQueue()const{
        if(!learnQueue_||learnFuture_||learnMutation_!=LearnMutation::None||learnSession_.empty()||learnQueue_->phase()!=navigation::ExerciseQueuePhase::Open)return false;
        return learnCaptureResult()!=learn::QueueCaptureResult::Unresolved;
    }
    bool advanceLearnQueue(std::string& reason){
        if(!canAdvanceLearnQueue())return learnFail(reason,"Save the original result and finish cleanup before Next; Stop is not discard.");
        const auto* capture=practiceView->captureSession();const auto& launch=*learnQueue_->activeLaunch();
        if(learnSuite_&&practiceView->suiteNaturalCompleted()){
            const auto& completed=learnSuite_->completed();const bool recorded=std::any_of(completed.begin(),completed.end(),[&](const auto& item){return item.attemptId==capture->binding().owner;});
            if(!recorded){suiteAppendOwner_=capture->binding().owner;suiteOutputCapability_=settingsOutputCapability();learnOperation_="learn-suite/member/"+storage::newUuid();learnAt_=desktopUtcNow();learnMutation_=LearnMutation::AppendSuiteMember;return submitLearnMutation(reason);}
        }
        try{
            const auto admission=practiceView->lessonAdmission();
            if(!admission||!(navigation::snapshotAdmission(*admission)==*launch.exercise.admission))return learnFail(reason,"Practice source differs from the queue item; preserve the original result.");
            if(!practiceView->audioRelease())return learnFail(reason,"Audio cleanup still needs attention.");
            const bool saved=learnCaptureResult()==learn::QueueCaptureResult::Saved;
            learnReceipt_=navigation::ExerciseResolution{launch.ticket,*launch.exercise.admission,saved?navigation::ResultDisposition::Saved:navigation::ResultDisposition::SafelyDiscarded,true,true,learnSession_,saved?capture->binding().owner:std::string{}};
            learnOutcome_=saved?"partial":"cancelled"; // Activity is not source task completion.
            learnOperation_="learn-exercise/close/"+storage::newUuid();learnAt_=desktopUtcNow();learnMutation_=LearnMutation::Close;
            return submitLearnMutation(reason);
        }catch(const std::exception& error){return learnFail(reason,error.what());}
    }
    std::string learnRetryLabel()const{
        switch(learnMutation_){
            case LearnMutation::Create:return "Check original exercise preparation";
            case LearnMutation::Close:return "Check original Session close";
            case LearnMutation::CloseFailedPreparation:return "Check original unused Session cancellation";
            case LearnMutation::BeginSuite:return "Check original queue creation";
            case LearnMutation::AppendSuiteMember:return "Check original queue member append";
            case LearnMutation::ReviewSuite:return "Check original final review save";
            case LearnMutation::ClearSuite:return "Check original queue reset";
            case LearnMutation::ReadSuite:return "Check original saved queue read";
            case LearnMutation::None:return "No original Session operation to check";
        }
        return "Check original Session operation";
    }
    bool retryLearnQueue(std::string& reason){
        if(learnFuture_)return learnFail(reason,"The original Session operation is still pending; wait for its result.");
        if(learnMutation_==LearnMutation::None)return learnFail(reason,"No Session operation needs retry. Resolve Practice through its original Save controls.");
        // A confirmed Session with failed preparation must be closed only after
        // the old Practice owner is safely restored; no Attempt was started here.
        if(learnMutation_==LearnMutation::CloseFailedPreparation&&!restoreLearnPreviewOwner())return learnFail(reason,"Resolve audio and the original Practice capture before cancelling the unused Session.");
        return submitLearnMutation(reason); // original operation/time/owner/payload, never a new retry identity
    }
    void serviceLearnQueue(){
        if(!learnFuture_||learnFuture_->wait_for(std::chrono::seconds(0))!=std::future_status::ready)return;
        storage::Reply reply;
        try{reply=learnFuture_->get();learnFuture_.reset();}
        catch(const std::exception& error){learnFuture_.reset();lessonView.queueStatus(std::string{"Session result needs retry: "}+error.what());return;}
        if(reply.operation!=learnOperation_){lessonView.queueStatus("Session reply does not match the retained operation. Preserve it for reconciliation.");return;}
        if(learnMutation_==LearnMutation::ReadSuite&&reply.status==storage::Status::DefinitelyAbsent){lessonView.clearQueuePending();learnMutation_=LearnMutation::None;learnOperation_.clear();return;}
        if(reply.status!=storage::Status::Confirmed){if(learnMutation_==LearnMutation::ReviewSuite)suiteReviewView_.present(suiteCompletedCount_,"Original final review unresolved; Retry preserves its exact score and operation.",false,false);lessonView.queueStatus("Session operation unresolved: "+reply.code+". Retry uses the original operation; no result is discarded.");return;}
        if(learnMutation_==LearnMutation::BeginSuite||learnMutation_==LearnMutation::AppendSuiteMember||learnMutation_==LearnMutation::ReviewSuite){
            const auto* returnedSuite=reply.data.find("suite");const auto* returnedId=returnedSuite?returnedSuite->find("suite_id"):nullptr;
            if(!learnSuite_||reply.owner!=learnSuite_->suiteId()||!returnedId||!returnedId->isString()||returnedId->string()!=learnSuite_->suiteId()){lessonView.queueStatus("Suite reply belongs to another owner; retain the original operation.");return;}
            if(const auto* members=returnedSuite->find("members"))suiteCompletedCount_=members->array().size();
        }
        if(learnMutation_==LearnMutation::ReadSuite){
            try{learnSuite_=std::make_unique<navigation::ExerciseSuiteReview>(reply.data.object().at("suite_id").string());suiteQueue_=nullptr;lessonView.setQueueOwnership(false);suitePlan_=reply.data.object().at("plan");suiteCompletedCount_=reply.data.object().at("members").array().size();if(const auto* pending=reply.data.find("pending_members"))suiteCompletedCount_+=pending->array().size();learnSuite_->freeze();learnMutation_=LearnMutation::None;learnOperation_.clear();page_=Page::SuiteReview;suiteReviewView_.begin(suiteCompletedCount_,"Review your completed exercises. Unplayed exercises will not receive this score.");update();}
            catch(const std::exception& e){lessonView.queueStatus(std::string{"Original suite recovery requires attention: "}+e.what());}return;
        }
        if(learnMutation_==LearnMutation::BeginSuite){learnPlan_.object()["suite_id"]=learnSuite_->suiteId();learnOperation_="learn-exercise/create/"+storage::newUuid();learnAt_=desktopUtcNow();learnMutation_=LearnMutation::Create;std::string reason;submitLearnMutation(reason);return;}
        if(learnMutation_==LearnMutation::AppendSuiteMember){
            const auto* capture=practiceView->captureSession();const auto launch=learnQueue_?learnQueue_->activeLaunch():std::optional<navigation::ExerciseLaunch>{};
            if(!capture||!launch||capture->binding().owner!=suiteAppendOwner_||!practiceView->suiteNaturalCompleted()){lessonView.queueStatus("Durable suite member is saved; original Practice ownership needs reconciliation.");return;}
            const navigation::ExerciseResolution receipt{launch->ticket,*launch->exercise.admission,navigation::ResultDisposition::Saved,true,true,learnSession_,suiteAppendOwner_};std::string reason;
            if(!learnSuite_->record(*launch,receipt,true,reason)){lessonView.queueStatus(reason);return;}learnMutation_=LearnMutation::None;suiteAdvanceAfterClose_=suiteAutoAdvanceAllowed_;advanceLearnQueue(reason);return;
        }
        if(learnMutation_==LearnMutation::ClearSuite){const auto* closedSuite=reply.data.find("suite");if(!learnSuite_||reply.owner!=learnSuite_->suiteId()||!closedSuite||!closedSuite->find("suite_id")||closedSuite->object().at("suite_id")!=json::Value(learnSuite_->suiteId())||!closedSuite->find("closed")||closedSuite->object().at("closed")!=json::Value(true)){lessonView.queueStatus("Queue reset reply belongs to another owner; check its original operation.");return;}learnMutation_=LearnMutation::None;finishClearLearnQueue();return;}
        if(learnMutation_==LearnMutation::ReviewSuite){suiteReviewSaved_=true;learnMutation_=LearnMutation::None;suiteReviewView_.present(suiteCompletedCount_,"Final review saved for "+std::to_string(suiteCompletedCount_)+" completed exercises.",false,true);return;}
        if(learnMutation_==LearnMutation::Create){
            try{
                // Idempotent create replay returns session_id in its saved data.
                const auto returnedSession=reply.data.object().at("session_id").string();storage::validateUuid(returnedSession);
                if(learnSession_.empty()||returnedSession!=learnSession_||reply.owner!=learnSession_){lessonView.queueStatus("Session preparation reply belongs to another owner. Retain the original operation.");return;}
                std::shared_ptr<const lesson::Admission> admission;std::string reason;
                const bool opened=learnQueue_->openExplicitly(learnSession_,[&](const navigation::ExerciseEntry& entry){admission=navigation::resolveExerciseAdmission(*lessonView.catalog(),entry);return navigation::snapshotAdmission(*admission);},[&](const navigation::ExerciseLaunch& launch){
                    if(!practiceView->audioCanRelease()||!audio_.canRelease()||!audio_.activate(SharedAudioSettings::Consumer::Practice))return false;
                    if(practiceView->captureSession()->phase()==capture::SessionPhase::Saved&&!practiceView->againSample())return false;
                    learnBaselineAttempt_=practiceView->captureSession()->binding().owner;
                    if(!practiceView->rebindCaptureSession(launch.sessionId))return false;
                    if(!practiceView->configureLesson(admission,learnBpm_,setup.currentSetup()))return false;
                    if(practiceView->captureSessionId()!=launch.sessionId)return false;
                    practiceView->setGuidedSummaryAction({});practiceView->setReturnDestination("Learn");practiceView->onBack=[this]{suiteContinuation_=SuiteContinuation::None;suiteAutoAdvanceAllowed_=false;lessonView.queueStatus("Review the current result. Save and cleanup are required before Next.");navigate(Page::Learn);};practiceView->onProgressPage=[this]{navigate(Page::Progress);};return true;
                },reason);
                if(opened){learnMutation_=LearnMutation::None;lessonView.queueStatus("Exercise prepared in its own Session. Choose Start in Practice; no Attempt or credit was created by navigation.");navigate(Page::Practice);return;}
                learnFailure_=reason;
                learnOperation_="learn-exercise/cancel-unused/"+storage::newUuid();learnAt_=desktopUtcNow();learnOutcome_="cancelled";learnMutation_=LearnMutation::CloseFailedPreparation;
                if(restoreLearnPreviewOwner())submitLearnMutation(reason);else lessonView.queueStatus("Preparation refused: "+learnFailure_+". Resolve cleanup, then retry cancelling its unused Session.");
            }catch(const std::exception& error){lessonView.queueStatus(std::string{"Retain the created Session and retry its original operation: "}+error.what());}
            return;
        }
        if(learnMutation_==LearnMutation::Close||learnMutation_==LearnMutation::CloseFailedPreparation){
            const auto* returnedSession=reply.data.find("session_id");if(!returnedSession||!returnedSession->isString()||returnedSession->string()!=learnSession_){lessonView.queueStatus("Session close reply belongs to another owner. Retain the original operation.");return;}
            // Keep the confirmed close request and original IDs until restoration
            // succeeds. Retry is idempotent, so no duplicate close is fabricated.
            if(!restoreLearnPreviewOwner()){lessonView.queueStatus("Session close is confirmed, but Practice ownership could not be restored. Resolve cleanup, then retry the same close.");return;}
            if(learnMutation_==LearnMutation::Close){std::string reason;if(!learnReceipt_||!learnQueue_->noteResolved(*learnReceipt_,reason)||!learnQueue_->nextExplicitly(reason)){lessonView.queueStatus("Session is closed; queue reconciliation needs attention: "+reason);return;}}
            const auto message=learnMutation_==LearnMutation::CloseFailedPreparation?"Preparation refused: "+learnFailure_+". The unused Session was cancelled without an Attempt. Choose Open to retry.":"Original Session closed. Next source item is selected; Open and Practice Start remain explicit.";
            auto* retainedQueue=learnQueue_;const bool autoNext=suiteAdvanceAfterClose_;suiteAdvanceAfterClose_=false;
            learnQueue_=nullptr;lessonView.setQueueOwnership(learnSuite_&&retainedQueue&&retainedQueue->phase()!=navigation::ExerciseQueuePhase::Complete);learnMutation_=LearnMutation::None;learnReceipt_.reset();learnSession_.clear();learnOperation_.clear();learnPlan_=nullptr;lessonView.queueStatus(message);
            if(clearQueueRequested_){serviceClearLearnQueue();return;}
            if(learnSuite_&&retainedQueue&&retainedQueue->phase()==navigation::ExerciseQueuePhase::Complete){learnSuite_->freeze();suiteContinuation_=SuiteContinuation::None;practiceView->setSuiteMode(false);page_=Page::SuiteReview;suiteReviewView_.begin(suiteCompletedCount_,"Choose one final report for the completed exercises.");update();return;}
            if(autoNext&&learnSuite_&&retainedQueue&&retainedQueue->phase()==navigation::ExerciseQueuePhase::Ready){std::string reason;if(openLearnQueue(*retainedQueue,learnBpm_,reason)){suiteContinuation_=SuiteContinuation::Connect;suiteContinuationDeadline_=std::chrono::steady_clock::now()+std::chrono::seconds(10);}return;}
            // Next disables its focused button while the close is pending. Once
            // the new item is ready, restore a keyboard entry exactly once.
            if(page_==Page::Learn)update();
            return;
        }
    }
    Page page_{Page::Home},settingsCaller_{Page::Home},learnReturnPage_{Page::Home};
    juce::TextButton homeRoute_{"Home"};
    juce::Label homeRouteStatus_;
    Page homeRouteStatusPage_{Page::Home};
    bool homeLearnDetour_{};
    Page progressReturnPage_{Page::UserProfile},referenceReturnPage_{Page::FreeplayMenu};
    KeyboardButton userProfileButton_{"User profile"},freeplaySessionButton_{"Free play session"},profileSave_{"Save profile preferences"},profileReload_{"Reload / check profile save"},guidedRecoveryButton_{"Resolve retained Guided session"},uiSave_{"Save appearance"},uiReload_{"Reload / check UI save"},sectionBack_{"Back to Home"};
    juce::Label sectionHeading_,sectionHelp_,profileBpmLabel_,profileStatusLabel_,uiStatus_;
    ReadOnlyTextEditor profileIdentity_;
    juce::TextEditor profileBpm_;
    juce::ComboBox appearanceChoice_;
    std::string profileSummary_,profileBpmIdentity_,profilePreferenceNotice_,profileBpmDisplayed_;
    bool profileBpmEdited_{},applyProfileReload_{};
    int appearanceDisplayedChoice_{};
    bool clearQueueRequested_{};
    ClearLearnQueuePanel clearQueuePanel_;
    std::vector<std::pair<juce::Component::SafePointer<juce::Component>,bool>> clearQueueDisabled_;
    KeyboardButton settingsButton_{"Settings"},settingsBack_{"Back to Home"};
    juce::Label settingsHeading_,settingsHelp_,settingsPresentationLabel_,settingsSetupLabel_,settingsInfoLabel_,homeSettingsNotice_;
    Page aboutReturnPage_{Page::Home};
    bool pendingLearnEntry_=false;
    bool learnPreparingIndex_=false;
    bool learnSelectiveLoading_=false;
    std::shared_ptr<lesson::SelectedCatalogStore> selectedCatalogStore_;
    std::vector<lesson::SelectedCatalogStore::Request> learnSelectedRequests_;
    std::string learnActivitySource_;
    std::filesystem::path learnResources_;
    std::vector<std::filesystem::path> learnExtensions_;
    Page learnLoadingPage_{Page::Learn};
    std::shared_ptr<LearnPayload> learnPayload_;
    std::shared_ptr<std::atomic<bool>> learnLoadTicket_;
    std::string sourceCloseStatus_;
    CloseState closeState_{CloseState::Ready};
    std::string closeStatus_;
    juce::Component::SafePointer<juce::Component> settingsFocus_;
    SharedAudioSettings audio_;
    fathom::desktop::LessonView lessonView;
    fathom::desktop::ManualTaskView manualTaskView;
    fathom::desktop::RecipeTaskView recipeTaskView;
    fathom::desktop::AdvancedRecipeTaskView advancedRecipeTaskView;
    fathom::desktop::CompiledManualProcedureView compiledManualProcedureView;
    fathom::desktop::EarSourceProcedureView earSourceProcedureView;
    fathom::desktop::C43SourceProcedureView c43SourceProcedureView;
    fathom::desktop::ProgressView progressView;
    fathom::desktop::MetronomeView metronomeView;
    fathom::desktop::FreeplayView freeplayView;
    fathom::desktop::GuidedSessionView guidedView;
    fathom::desktop::SourceLibraryView sourceLibraryView;
    std::unique_ptr<fathom::desktop::PracticeView> practiceView=std::make_unique<fathom::desktop::PracticeView>();
    fathom::desktop::ReferenceView referenceView;
    fathom::desktop::SchedulerView scheduleView;
    fathom::desktop::AudioOutputView outputView;
    fathom::desktop::GuitarSetupView setup;
    setup::PreferencesController setupPreferences_;
    OnboardingView onboarding_;KeyboardButton onboardingButton_;
    enum class SetupFinish { Idle, Preparing, MarkingComplete };
    SetupFinish setupFinish_{SetupFinish::Idle};
    bool boardSaveRequested_{};
    std::string newProfileName_;
    bool setupCreatingProfile_{};
    bool setupRestorePending_{},setupDraftSubmitted_{},setupPresentationSubmitted_{},setupOwnerRestoreHeld_{},localProfileOpening_{};
    std::string setupNotice_;
    Page guitarSetupCaller_{Page::Home};
    presentation::PreferencesController presentation_;
    juce::ComboBox presentationChoice_;
    int presentationDisplayedChoice_{};
    KeyboardButton presentationSave_{"Save setting"},presentationReset_{"Reset presentation"},presentationReload_{"Reload / check save"},previewDetails_{"Preview details"};
    juce::Label presentationStatus_;
    bool previewDetailsOpen_{};
    ReadOnlyTextView message,detail;
    juce::Label heading, subtitle, learnPracticeLabel, activitiesLabel, audioToolsLabel;
    bool quitSetupSubmitted_{},quitPresentationSubmitted_{},quitLearnRetrySubmitted_{};
    KeyboardButton about, quit, setupButton, outputButton, scheduleButton, referenceButton, practiceButton, metronomeButton, learnButton, startLearningButton, localProfileButton, sourceLibraryButton, progressButton, freeplayButton, guidedButton;
    std::string profileStatus_;
    Page metronomeReturnPage_{Page::Home};
    Page rhythmReturnPage_{Page::Home};
};

}
