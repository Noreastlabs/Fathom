// Application composition root: owns the JUCE window and process-level profile
// open/create/recovery and quit workflows. Views emit intent; this owner retains
// the original pending operation until storage confirms its outcome. Ordinary
// startup is profileless and must not start audio or practice implicitly.
#include "desktop/PresentationPreferences.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include "core/Quantity.hpp"
#include "desktop/GuitarSetupView.hpp"
#include "desktop/HomeView.hpp"
#include "desktop/AudioOutputView.hpp"
#include "desktop/SchedulerView.hpp"
#include "desktop/ReferenceView.hpp"
#include "desktop/PracticeView.hpp"
#include "desktop/MetronomeView.hpp"
#include "desktop/LessonView.hpp"
#include "desktop/LocalProfile.hpp"
#include "desktop/NamedLocalProfile.hpp"
#include "desktop/PreviewResume.hpp"
#include "desktop/PortableRestoreWorkflow.hpp"
#include "desktop/PortableRestoreGuidance.hpp"
#include "content/CurriculumShardCatalog.hpp"
#include "content/SourceLibraryCatalog.hpp"
#include <iostream>
#include "platform/ProfileAccessMac.hpp"
#include <ctime>
#include <sys/stat.h>
#include <unistd.h>

namespace {
std::string utcNow(){const auto now=std::time(nullptr);std::tm utc{};gmtime_r(&now,&utc);char text[32]{};std::strftime(text,sizeof(text),"%Y-%m-%dT%H:%M:%SZ",&utc);return text;}
using Home=fathom::desktop::HomeView;
#if defined(FATHOM_MAIN_OWNER_TEST)
struct MainOwnerTestAccess;
#endif

class ClosingPanel final : public juce::Component {
public:
    ClosingPanel(){
        addAndMakeVisible(message);addAndMakeVisible(cancel);addChildComponent(save);addChildComponent(discard);save.setButtonText("Save and Quit");discard.setButtonText("Discard and Quit");save.setComponentID("shutdown-save");discard.setComponentID("shutdown-discard");
        message.setColour(juce::Label::textColourId,juce::Colours::white);
        message.setJustificationType(juce::Justification::centredLeft);
        cancel.setButtonText("Cancel Quit");cancel.setComponentID("shutdown-cancel");
        message.setComponentID("shutdown-status");
    }
    void paint(juce::Graphics& g)override{g.fillAll(fathom::desktop::appearance::colour(0xff203f50));}
    void resized()override{auto bounds=getLocalBounds().reduced(12,6);cancel.setBounds(bounds.removeFromRight(130));if(discard.isVisible())discard.setBounds(bounds.removeFromRight(210));if(save.isVisible())save.setBounds(bounds.removeFromRight(150));bounds.removeFromRight(12);message.setBounds(bounds);}
    juce::Label message;juce::TextButton cancel,save,discard;
};
class Window final : public juce::DocumentWindow {
public:
    Home& home(){return *static_cast<Home*>(getContentComponent());}
    void resetHome(){setContentOwned(new Home, true);bindAppearance();}
    void showClosing(const std::string& message,bool cancellable,bool held=false){
        closing.cancel.setVisible(true);closing.save.setVisible(false);closing.discard.setVisible(false);home().setEnabled(held);
        closing.message.setText(juce::String::fromUTF8(message.c_str()),juce::dontSendNotification);
        closing.cancel.setButtonText(held?"Keep app open":"Cancel Quit");
        closing.cancel.setEnabled(cancellable);closing.setVisible(true);closing.toFront(false);resized();
    }
    void showQuitChoice(const std::string& status="Save current changes, or discard unsaved changes. Saved history and recovery records stay."){showClosing(status,true);closing.save.setVisible(true);closing.discard.setVisible(true);closing.discard.setButtonText("Discard and Quit");resized();closing.resized();}
    void showDiscardRecovery(const std::string& status){showClosing(status,false);closing.cancel.setVisible(true);closing.cancel.setEnabled(true);closing.cancel.setButtonText("Keep App Open");closing.discard.setVisible(true);closing.discard.setButtonText("Continue Discard and Quit");resized();closing.resized();}
    std::function<void(bool)> onQuitChoice;
    void clearClosing(bool enableHome=true){closing.setVisible(false);home().setEnabled(enableHome);}
    std::function<void()> onCancelQuit;
#if defined(FATHOM_MAIN_OWNER_TEST)
    Window(bool native=true) : DocumentWindow("Fathom - Offline Guitar Training", juce::Colour{0xff10212c}, allButtons,native) {
#else
    Window() : DocumentWindow("Fathom - Offline Guitar Training", juce::Colour{0xff10212c}, allButtons) {
#endif
        setUsingNativeTitleBar(true);setContentOwned(new Home, true);bindAppearance();
        addChildComponent(closing);closing.save.onClick=[this]{if(onQuitChoice)onQuitChoice(false);};closing.discard.onClick=[this]{if(onQuitChoice)onQuitChoice(true);};closing.cancel.onClick=[this]{if(onCancelQuit)onCancelQuit();};
        setResizable(true, false);setResizeLimits(920, 680, 1400, 1000);
#if defined(FATHOM_MAIN_OWNER_TEST)
        if(native){centreWithSize(getWidth(), getHeight());setVisible(true);}else setSize(920,680);
#else
        centreWithSize(getWidth(), getHeight());setVisible(true);
#endif
    }
    void resized()override{DocumentWindow::resized();if(auto* content=getContentComponent())closing.setBounds(content->getBounds().withHeight(64));}
    bool keyPressed(const juce::KeyPress& key) override {
#if JUCE_MAC
        const auto fullscreenModifiers = juce::ModifierKeys::ctrlModifier | juce::ModifierKeys::commandModifier;
        if ((key.getKeyCode() == 'f' || key.getKeyCode() == 'F') &&
            key.getModifiers().getRawFlags() == fullscreenModifiers &&
            juce::Component::getCurrentlyModalComponent() == nullptr) {
            setFullScreen(!isFullScreen());
            return true;
        }
#endif
        return DocumentWindow::keyPressed(key);
    }
    void closeButtonPressed() override { juce::JUCEApplication::getInstance()->systemRequestedQuit(); }
private:
#if defined(FATHOM_MAIN_OWNER_TEST)
    friend struct MainOwnerTestAccess;
#endif
    void bindAppearance(){
        home().onAppearanceChanged=[this](fathom::desktop::setup::Appearance mode){
            fathom::desktop::appearance::set(mode);fathom::desktop::appearance::apply(*this);
            setBackgroundColour(fathom::desktop::appearance::colour(0xff10212c));repaint();
        };
        // Install the shared owner before any profile/setup choice. Profileless
        // startup otherwise retains JUCE's default LookAndFeel and popup peers.
        fathom::desktop::appearance::apply(*this);
    }
    ClosingPanel closing;
};

class Application final : public juce::JUCEApplication, private juce::Timer {
public:
    const juce::String getApplicationName() override { return "Fathom"; }
    const juce::String getApplicationVersion() override { return "0.0.1"; }
    bool moreThanOneInstanceAllowed() override {
        // Explicit preview commands are handled by this process, including invalid
        // arguments; never forward them into another owner preview.
        const auto args=juce::StringArray::fromTokens(getCommandLineParameters(),true);
        return args.size()>0 && (args[0]=="--capture-preview" || args[0]=="--resume-preview" ||
            args[0]=="--prepare-restore-preview" || args[0]=="--apply-restore-preview" ||
            args[0]=="--local-profile-self-test" || args[0]=="--local-profile-preview" || args[0]=="--check-curriculum-shards" ||
            args[0]=="--check-source-library" || args[0]=="--browse-source-library-smoke");
    }
    void initialise(const juce::String& commandLine) override {
        window = std::make_unique<Window>();
        window->onCancelQuit=[this]{cancelQuit();};window->onQuitChoice=[this](bool discard){chooseQuit(discard);};
        wireLocalProfile();
        const auto args=juce::StringArray::fromTokens(commandLine,true);
        if(args.size()>0 && args[0]=="--check-curriculum-shards"){
            try{
                if(args.size()!=1)throw std::runtime_error("Use --check-curriculum-shards with no other arguments");
                const auto application=juce::File::getSpecialLocation(juce::File::currentApplicationFile);
                const auto direct=application.getChildFile("Contents/Resources/curriculum-shards");
                const auto adjacent=application.getParentDirectory().getParentDirectory().getChildFile("Resources/curriculum-shards");
                const auto resources=(direct.isDirectory()?direct:adjacent).getFullPathName().toStdString();
                const auto found=fathom::curriculum::discoverShards(std::filesystem::path(resources));
                std::cout<<"CURRICULUM_SHARD_DISCOVERY shards="<<found.shardCount<<" source_records="<<found.sourceRecords
                         <<" admitted=false practice=false attempts=false\n";
                setApplicationReturnValue(0);quit();
            }catch(const std::exception& error){
                std::cerr<<"CURRICULUM_SHARD_REFUSED "<<error.what()<<std::endl;
                setApplicationReturnValue(2);quit();
            }
            return;
        }
        if(args.size()>0 && args[0]=="--check-source-library"){
            try{
                if(args.size()!=1)throw std::runtime_error("Use --check-source-library with no other arguments");
                const auto application=juce::File::getSpecialLocation(juce::File::currentApplicationFile);
                const auto direct=application.getChildFile("Contents/Resources/source-library");
                const auto adjacent=application.getParentDirectory().getParentDirectory().getChildFile("Resources/source-library");
                const auto resources=(direct.isDirectory()?direct:adjacent).getFullPathName().toStdString();
                const auto library=fathom::curriculum::SourceLibrary::load(std::filesystem::path(resources));
                std::cout<<"SOURCE_LIBRARY workbooks="<<library.workbooks().size()
                         <<" originals="<<library.workbooks().size()*2<<" admitted=false practice=false attempts=false\n";
                setApplicationReturnValue(library.workbooks().size()==105?0:2);quit();
            }catch(const std::exception& error){
                std::cerr<<"SOURCE_LIBRARY_REFUSED "<<error.what()<<std::endl;
                setApplicationReturnValue(2);quit();
            }
            return;
        }
        if(args.size()>0 && args[0]=="--browse-source-library-smoke"){
            if(args.size()!=1){setApplicationReturnValue(2);quit();return;}
            juce::Timer::callAfterDelay(250,[this]{
                auto* browse=dynamic_cast<juce::Button*>(window->home().findChildWithID("home-source-library"));
                if(!browse){std::cerr<<"Source library Home action missing\n";setApplicationReturnValue(2);quit();return;}
                browse->triggerClick();
                waitForSourceLibrary([this]{
                    auto* pane=window->home().findChildWithID("source-library-view");
                    auto* list=dynamic_cast<juce::ComboBox*>(pane?pane->findChildWithID("source-library-workbooks"):nullptr);
                    auto* text=dynamic_cast<juce::TextEditor*>(pane?pane->findChildWithID("source-library-original-text"):nullptr);
                    auto* search=dynamic_cast<juce::TextEditor*>(pane?pane->findChildWithID("source-library-search"):nullptr);
                    auto* back=dynamic_cast<juce::Button*>(pane?pane->findChildWithID("source-library-back"):nullptr);
                    if(!list||list->getNumItems()!=11||list->getSelectedId()!=1||!text||text->getText().isEmpty()||!search||!back||!back->isShowing()){
                        std::cerr<<"Source library browse flow unavailable\n";setApplicationReturnValue(2);quit();return;
                    }
                    search->setText("SCALE EXERCISES - SECTION III, LEVEL 29",true);
                    juce::Timer::callAfterDelay(250,[this]{
                        auto* paneAfterTextSearch=window->home().findChildWithID("source-library-view");
                        auto* listAfterTextSearch=dynamic_cast<juce::ComboBox*>(paneAfterTextSearch?paneAfterTextSearch->findChildWithID("source-library-workbooks"):nullptr);
                        auto* textAfterTextSearch=dynamic_cast<juce::TextEditor*>(paneAfterTextSearch?paneAfterTextSearch->findChildWithID("source-library-original-text"):nullptr);
                        auto* searchAfterTextSearch=dynamic_cast<juce::TextEditor*>(paneAfterTextSearch?paneAfterTextSearch->findChildWithID("source-library-search"):nullptr);
                        if(!listAfterTextSearch||listAfterTextSearch->getNumItems()!=1||listAfterTextSearch->getSelectedId()!=29
                           ||!textAfterTextSearch||!textAfterTextSearch->getText().containsIgnoreCase("Natural minor across the neck")||!searchAfterTextSearch){
                            std::cerr<<"Source library instruction search failed\n";setApplicationReturnValue(2);quit();return;
                        }
                        auto* openLearn=dynamic_cast<juce::Button*>(paneAfterTextSearch->findChildWithID("source-library-open-learn"));
                        if(!openLearn){std::cerr<<"Source library Learn link missing\n";setApplicationReturnValue(2);quit();return;}
                        openLearn->triggerClick();
                        waitForLearnWorkbook(29,[this]{
                            auto* learnPane=dynamic_cast<fathom::desktop::LessonView*>(window->home().findChildWithID("learn-view"));
                            auto* learnBack=dynamic_cast<juce::Button*>(learnPane?learnPane->findChildWithID("back"):nullptr);
                            if(!learnPane||!learnPane->sourceHierarchyReadyForLevel(29)||!learnBack){
                                std::cerr<<"Supported workbook did not open in Learn: pane="<<(learnPane?learnPane->isShowing():false)
                                         <<" selected="<<(learnPane?learnPane->sourceLevelSelection():0)
                                         <<" back="<<(learnBack!=nullptr)<<"\n";
                                setApplicationReturnValue(2);quit();return;
                            }
                            learnBack->triggerClick();
                            juce::Timer::callAfterDelay(250,[this]{
                                auto* returnedPane=window->home().findChildWithID("source-library-view");
                                auto* returnedSearch=dynamic_cast<juce::TextEditor*>(returnedPane?returnedPane->findChildWithID("source-library-search"):nullptr);
                                if(!returnedPane||!returnedPane->isShowing()||!returnedSearch){
                                    std::cerr<<"Learn did not return to the workbook library\n";setApplicationReturnValue(2);quit();return;
                                }
                                returnedSearch->setText("Level 104",true);
                                juce::Timer::callAfterDelay(250,[this]{
                                    auto* unsupportedPane=window->home().findChildWithID("source-library-view");
                                    auto* unsupportedList=dynamic_cast<juce::ComboBox*>(unsupportedPane?unsupportedPane->findChildWithID("source-library-workbooks"):nullptr);
                                    auto* unsupportedLearn=dynamic_cast<juce::Button*>(unsupportedPane?unsupportedPane->findChildWithID("source-library-open-learn"):nullptr);
                                    if(!unsupportedList||unsupportedList->getSelectedId()!=104||!unsupportedLearn){
                                        std::cerr<<"Level 104 workbook selection failed\n";setApplicationReturnValue(2);quit();return;
                                    }
                                    unsupportedLearn->triggerClick();
                                    waitForLearnWorkbook(104,[this]{
                                        auto* level104Pane=dynamic_cast<fathom::desktop::LessonView*>(window->home().findChildWithID("learn-view"));
                                        auto* level104Back=dynamic_cast<juce::Button*>(level104Pane?level104Pane->findChildWithID("back"):nullptr);
                                        if(!level104Pane||!level104Pane->sourceHierarchyReadyForLevel(104)||!level104Back
                                           ||store||localOpening.valid()||level104Pane->sourceQueueActive()
                                           ||level104Pane->hasRetainedSourcePlan()||level104Pane->hasExplicitSelection()){
                                            std::cerr<<"Level 104 hierarchy browse failed or allocated an activity selection\n";setApplicationReturnValue(2);quit();return;
                                        }
                                        // Hierarchy access is not Practice admission. No profile/activity is opened.
                                        level104Back->triggerClick();
                                        waitForSourceLibrary([this]{
                                        auto* returned104Pane=window->home().findChildWithID("source-library-view");
                                        auto* searchAfter104=dynamic_cast<juce::TextEditor*>(returned104Pane?returned104Pane->findChildWithID("source-library-search"):nullptr);
                                        if(!returned104Pane||!returned104Pane->isShowing()||!searchAfter104){
                                            std::cerr<<"Level 104 hierarchy did not return to the workbook library\n";setApplicationReturnValue(2);quit();return;
                                        }
                                        searchAfter104->setText("Level 105",true);
                                        juce::Timer::callAfterDelay(250,[this]{
                                            auto* paneAfterLevelSearch=window->home().findChildWithID("source-library-view");
                                            auto* listAfterLevelSearch=dynamic_cast<juce::ComboBox*>(paneAfterLevelSearch?paneAfterLevelSearch->findChildWithID("source-library-workbooks"):nullptr);
                                            auto* textAfterLevelSearch=dynamic_cast<juce::TextEditor*>(paneAfterLevelSearch?paneAfterLevelSearch->findChildWithID("source-library-original-text"):nullptr);
                                            auto* backAfterLevelSearch=dynamic_cast<juce::Button*>(paneAfterLevelSearch?paneAfterLevelSearch->findChildWithID("source-library-back"):nullptr);
                                            if(!listAfterLevelSearch||listAfterLevelSearch->getNumItems()!=1||listAfterLevelSearch->getSelectedId()!=105
                                               ||!textAfterLevelSearch||textAfterLevelSearch->getText().isEmpty()||!backAfterLevelSearch){
                                                std::cerr<<"Source library Level 105 selection failed\n";setApplicationReturnValue(2);quit();return;
                                            }
                                            backAfterLevelSearch->triggerClick();
                                            juce::Timer::callAfterDelay(250,[this]{
                                                auto* paneAfterBack=window->home().findChildWithID("source-library-view");
                                                auto* backAfter=dynamic_cast<juce::Button*>(paneAfterBack?paneAfterBack->findChildWithID("source-library-back"):nullptr);
                                                if(!backAfter||backAfter->isShowing()){std::cerr<<"Source library Back failed\n";setApplicationReturnValue(2);quit();return;}
                                                std::cout<<"SOURCE_LIBRARY_BROWSE_OK workbooks=105 instruction_search=29 learn=29 hierarchy=104 activity=false level_search=105 back=home\n";
                                                setApplicationReturnValue(0);quit();
                                            });
                                        });
                                        });
                                    });
                                });
                            });
                        });
                    });
                });
            });
            return;
        }
        if(args.size()>0 && args[0]=="--local-profile-preview"){
            try{
                if(args.size()!=2)throw std::runtime_error("Use --local-profile-preview <owned canonical private/tmp directory>");
                const std::filesystem::path directory(args[1].unquoted().toStdString());
                struct stat identity{};
                if(!directory.is_absolute()||directory.parent_path()!=std::filesystem::path("/private/tmp")||
                   std::filesystem::canonical(directory)!=directory||::lstat(directory.c_str(),&identity)!=0||
                   !S_ISDIR(identity.st_mode)||identity.st_uid!=::geteuid()||(identity.st_mode&077)!=0)
                    throw std::runtime_error("Diagnostic local profile requires existing canonical owner-only private/tmp directory");
                localProfileSelfTestPath=directory/"profile.sqlite";
                window->home().beginInitialSetup();
                // No automatic click/open/quit. The visible ordinary Home action
                // uses the same wireLocalProfile/openLocalProfile path explicitly.
            }catch(const std::exception& error){std::cerr<<error.what()<<std::endl;setApplicationReturnValue(2);quit();}
            return;
        }
        if(args.size()>0 && args[0]=="--local-profile-self-test"){
            localProfileSelfTestCreates_=true;
            try{
                if(args.size()!=2)throw std::runtime_error("Use --local-profile-self-test <new absolute profile.sqlite>");
                localProfileSelfTestPath=std::filesystem::path(args[1].unquoted().toStdString());
                if(!localProfileSelfTestPath.is_absolute()||localProfileSelfTestPath.filename()!="profile.sqlite"||
                   std::filesystem::exists(localProfileSelfTestPath))
                    throw std::runtime_error("Self-test requires a new absolute profile.sqlite path");
                juce::Timer::callAfterDelay(20,[this]{
                    if(!window)return;
                    auto* action=dynamic_cast<juce::Button*>(window->home().findChildWithID("home-local-profile"));
                    if(!action){std::cerr<<"Local profile Home action missing"<<std::endl;setApplicationReturnValue(2);quit();return;}
                    action->triggerClick();
                    juce::Timer::callAfterDelay(100,[this]{pollLocalProfileSelfTest();});
                });
            }catch(const std::exception& error){std::cerr<<error.what()<<std::endl;setApplicationReturnValue(2);quit();}
            return;
        }
        const bool captureSmoke=args.size()==4 && args[0]=="--capture-preview" && args[3]=="--smoke-test";
        if(args.size()>0 && args[0]=="--prepare-restore-preview"){
        try{
            if(args.size()!=5 && !(args.size()==6 && args[5]=="--smoke-test"))
                throw std::runtime_error("Use --prepare-restore-preview <profile.sqlite> <candidate.zip> <stage-dir> <available-metadata.json> [--smoke-test]");
            const fathom::desktop::PortableRestoreRequest request{
                std::filesystem::path(args[1].unquoted().toStdString()),
                std::filesystem::path(args[2].unquoted().toStdString()),
                std::filesystem::path(args[3].unquoted().toStdString()),
                std::filesystem::path(args[4].unquoted().toStdString())};
            const auto prepared=fathom::desktop::PortableRestoreWorkflow::prepare(request);
            std::cout<<"PORTABLE_RESTORE_PREPARED\n"
                     <<"profile="<<request.profile<<"\n"
                     <<"preview="<<prepared.preview<<"\n"
                     <<"preview_file="<<fathom::storage::canonical(prepared.previewFile)<<"\n"
                     <<"confirmation_sha256="<<prepared.confirmationSha256<<"\n";
            setApplicationReturnValue(0);quit();
        }catch(const std::exception& error){std::cerr<<fathom::desktop::portableRestoreFailureOutput(error.what())<<std::endl;setApplicationReturnValue(2);quit();}
            return;
        }
        if(args.size()>0 && args[0]=="--apply-restore-preview"){
        try{
            if(args.size()!=5 && !(args.size()==6 && args[5]=="--smoke-test"))
                throw std::runtime_error("Use --apply-restore-preview <profile.sqlite> <restore-preview.json> <available-metadata.json> <confirmation-sha256> [--smoke-test]");
            const auto profile=std::filesystem::path(args[1].unquoted().toStdString());
            const auto preview=std::filesystem::path(args[2].unquoted().toStdString());
            const auto available=std::filesystem::path(args[3].unquoted().toStdString());
            const auto confirmation=args[4].unquoted().toStdString();
            const auto prepared=fathom::desktop::PortableRestoreWorkflow::loadPrepared(profile,preview,available,confirmation);
            const auto result=fathom::desktop::PortableRestoreWorkflow::apply(prepared);
            std::cout<<"PORTABLE_RESTORE_APPLY status="<<fathom::storage::statusName(result.application.status)
                     <<" code="<<result.application.code<<"\n";
            if(result.reopened.status==fathom::storage::Status::Confirmed)
                std::cout<<"PORTABLE_RESTORE_REOPEN status=Confirmed profile="
                         <<result.reopened.data.object().at("profile_id").string()<<"\n";
            setApplicationReturnValue(result.application.status==fathom::storage::Status::Confirmed ? 0 : 3);quit();
        }catch(const std::exception& error){std::cerr<<fathom::desktop::portableRestoreFailureOutput(error.what())<<std::endl;setApplicationReturnValue(2);quit();}
            return;
        }
        if(args.size()>0 && args[0]=="--resume-preview") {
            try {
                if(args.size()!=5 && !(args.size()==6 && args[5]=="--smoke-test"))
                    throw std::runtime_error("Use --resume-preview <existing absolute private directory> <profile UUID> <original Session UUID> <IANA timezone> [--smoke-test]");
                fathom::desktop::PreviewResumeRequest request{std::filesystem::path(args[1].unquoted().toStdString()),
                    args[2].toStdString(),args[3].toStdString(),args[4].toStdString()};
                profilePath=request.directory/"profile.sqlite";profileId=request.profile;sessionId=request.session;profileZone=request.timezone;
                startupSmoke=args.size()==6;window->home().setEnabled(false);window->setName("Fathom - Opening saved preview");
                startup=std::async(std::launch::async,[request]{return fathom::desktop::openPreviewResume(request);});
                juce::Timer::callAfterDelay(20,[this]{pollStartup();});
            } catch(const std::exception& error) {std::cerr<<error.what()<<std::endl;setApplicationReturnValue(2);quit();}
            return;
        }
        if(args.size()>0&&args[0]=="--capture-preview")try{
            if(args.size()!=3 && !captureSmoke)throw std::runtime_error("Use --capture-preview <new absolute private directory> <IANA timezone> [--smoke-test]");
            const auto path=std::filesystem::path(args[1].unquoted().toStdString());const auto zone=args[2].unquoted().toStdString();
            if(!path.is_absolute()||std::filesystem::exists(path))throw std::runtime_error("Capture preview requires a new explicit directory; existing profiles are never modified");
            fathom::storage::localDay(utcNow(),zone);if(!std::filesystem::create_directories(path))throw std::runtime_error("Capture preview directory was not created by this invocation; existing paths are refused");std::filesystem::permissions(path,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
            fathom::storage::StoreOptions options;options.path=path/"profile.sqlite";options.create=true;options.createdUtc=utcNow();options.preferenceValidator=fathom::desktop::presentation::composedPreferenceValidator;
            store=std::make_unique<fathom::storage::ProfileStore>(options);
            auto reply=store->createSession(fathom::storage::newUuid(),utcNow(),zone,{},fathom::json::Value::Object{{"synthetic_fixture",true}}).get();
            if(reply.status!=fathom::storage::Status::Confirmed||!window->home().configureCapture(*store,reply.owner,zone))throw std::runtime_error("Synthetic Session creation is unresolved; profile retained at explicit path");
            const auto initialSnapshot=store->snapshot(fathom::storage::newUuid()).get();if(initialSnapshot.status!=fathom::storage::Status::Confirmed)throw std::runtime_error("Initial test profile identity could not be confirmed");
            profileId=initialSnapshot.data.object().at("profile_id").string();profilePath=options.path;sessionId=reply.owner;profileZone=zone;
            if(!window->home().attachPresentation(*store,profileId))throw std::runtime_error("Presentation profile attachment refused; original retained");
                wireStoreReopen();window->setName("Fathom - Guitar (Development Preview)");
            std::cout<<"Explicit synthetic capture profile: "<<options.path<<std::endl;
        }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;setApplicationReturnValue(2);quit();return;}
        if(args.size()==0||(args.size()==3&&args[0]=="--capture-preview"))window->home().beginInitialSetup();
        std::cout << "Fathom initialized; output remains closed until explicit Connect; "<<(store?"explicit synthetic profile attached":"no profile access") << std::endl;
        if (commandLine.trim() == "--smoke-test" || captureSmoke)
            juce::Timer::callAfterDelay(1000, [this] { systemRequestedQuit();chooseQuit(false); });
    }
    void shutdown() override {
        stopTimer();
        const auto before=std::chrono::steady_clock::now();window.reset();
        logQuitStage("views_released",before);const auto storeBefore=std::chrono::steady_clock::now();store.reset();
        logQuitStage("store_owner_released",storeBefore);
        std::cout << "Fathom shutdown" << std::endl;
    }
    void systemRequestedQuit() override {
        if(quitPhase==QuitPhase::Store||quitPhase==QuitPhase::StoreError||quitPhase==QuitPhase::Exiting||quitRequested)return;
        quitChoicePending=true;if(window){if(quitDiscardCommitted)window->showDiscardRecovery("Discarded changes cannot be restored. Saved history and original recovery records stay. Continue cleanup or keep the app open for recovery.");else window->showQuitChoice();}
    }
    void anotherInstanceStarted(const juce::String&) override { if (window) window->toFront(true); }
private:
#if defined(FATHOM_MAIN_OWNER_TEST)
    friend struct MainOwnerTestAccess;
    std::function<fathom::desktop::LocalProfileOpen(const std::filesystem::path&,const std::string&)> fixtureOpener;
    std::function<void(const char*)> fixtureCheckpoint;
    std::function<void()> fixtureExitReady;
#endif
    enum class QuitPhase { None, Consumers, Store, StoreError, Exiting };
    void logQuitStage(const char* stage,std::chrono::steady_clock::time_point before){
        const auto now=std::chrono::steady_clock::now();
        std::cout<<"SHUTDOWN stage="<<stage<<" stage_ms="<<std::chrono::duration<double,std::milli>(now-before).count();
        if(quitRequested)std::cout<<" request_ms="<<std::chrono::duration<double,std::milli>(now-quitStarted).count();
        std::cout<<std::endl;
    }
    void chooseQuit(bool discard){
        if(!quitChoicePending||quitRequested||(quitDiscardCommitted&&!discard))return;
        if(discard){if(quitDiscardCommitted&&window)window->home().retryExitDiscard();quitDiscardCommitted=true;}
        quitDiscard=discard;quitChoicePending=false;quitStarted=std::chrono::steady_clock::now();quitRequested=true;quitPhase=QuitPhase::Consumers;serviceQuit();
    }
    void cancelQuit(){
        if(quitPhase==QuitPhase::Store||quitPhase==QuitPhase::StoreError||quitPhase==QuitPhase::Exiting)return;
        if(quitDiscardCommitted){stopTimer();quitChoicePending=false;quitPhase=QuitPhase::None;quitRequested=false;quitAfterLoad=false;
            if(window)window->clearClosing();std::cout<<"SHUTDOWN paused after Discard; changes remain discarded and original recovery remains owned"<<std::endl;return;}
        if(window)window->home().cancelExit();
        stopTimer();quitChoicePending=false;quitPhase=QuitPhase::None;quitRequested=false;quitAfterLoad=false;
        if(window)window->clearClosing(!startup.valid()&&!localOpening.valid()&&!localRecoveryHeld&&!reopenFuture);
        std::cout<<"SHUTDOWN cancelled; original operations remain owned"<<std::endl;
    }
    void timerCallback()override{serviceQuit();}
    void serviceQuit(){
        if(!quitRequested)return;
        if(startup.valid()||localOpening.valid()||reopenFuture){
            quitAfterLoad=true;if(window)window->showClosing("Waiting for the original profile opening operation…",true);
            startTimer(20);return;
        }
        if(quitPhase==QuitPhase::Store){
            if(!store||store->shutdownComplete()){
                logQuitStage("storage_closed",storeDrainStarted);stopTimer();quitPhase=QuitPhase::Exiting;
#if defined(FATHOM_MAIN_OWNER_TEST)
                if(fixtureExitReady)fixtureExitReady();else quit();
#else
                quit();
#endif
                return;
            }
            const auto error=store->shutdownError();
            if(!error.empty()){
                stopTimer();quitPhase=QuitPhase::StoreError;
                if(window)window->showClosing("Profile close failed; accepted results remain retained. "+error,false);
                std::cerr<<"SHUTDOWN storage_close_held "<<error<<std::endl;
            }
            return;
        }
        if(std::chrono::steady_clock::now()-quitStarted>std::chrono::seconds(15)){
            stopTimer();quitRequested=false;quitChoicePending=true;if(window){if(quitDiscardCommitted)window->showDiscardRecovery("Discard is committed; saved history stays. Accepted operations remain unresolved. Continue retries only original recovery/cleanup; Save and Cancel cannot restore discarded changes.");else{window->home().cancelExit();window->showQuitChoice("Quit paused: the original result or cleanup is unresolved. Save and Quit retries; Cancel keeps the app open. Saved history stays.");}}return;
        }
        const auto before=std::chrono::steady_clock::now();
        if(window&&!window->home().requestExit(quitDiscard)){
            if(window->home().closeState()==Home::CloseState::Waiting){
                window->showClosing(window->home().closeStatus(),!quitDiscard);startTimer(20);
            }else{
                stopTimer();quitPhase=QuitPhase::None;quitRequested=false;quitAfterLoad=false;
                quitChoicePending=true;if(quitDiscardCommitted)window->showDiscardRecovery(window->home().closeStatus()+" Discard is committed; only original recovery/cleanup may continue.");else{window->home().cancelExit();window->showQuitChoice(window->home().closeStatus());}
                std::cout<<"SHUTDOWN held "<<window->home().closeStatus()<<std::endl;
            }
            return;
        }
        logQuitStage("consumer_gates_ready",before);storeDrainStarted=std::chrono::steady_clock::now();
        quitPhase=QuitPhase::Store;
        if(window)window->showClosing("Closing the local profile after all accepted operations…",false);
        if(store)store->beginShutdown();startTimer(20);
    }
    void waitForSourceLibrary(std::function<void()> ready,int polls=0){
        auto* pane=window?dynamic_cast<fathom::desktop::SourceLibraryView*>(window->home().findChildWithID("source-library-view")):nullptr;
        // triggerClick posts its onClick: an unopened pane is not a completed load.
        if(pane&&pane->isShowing()&&!pane->isLoading()){
            ready();return;
        }
        if(polls>=1200){
            std::cerr<<"Source library browse readiness timed out before a visible completed load\n";
            setApplicationReturnValue(2);quit();return;
        }
        juce::Timer::callAfterDelay(100,[this,ready=std::move(ready),polls]{waitForSourceLibrary(ready,polls+1);});
    }
    void waitForLearnWorkbook(int level,std::function<void()> ready,int polls=0){
        auto* pane=window?dynamic_cast<fathom::desktop::LessonView*>(window->home().findChildWithID("learn-view")):nullptr;
        // Workbook links publish the source hierarchy, not a selected Catalog case.
        if(pane&&pane->sourceHierarchyReadyForLevel(level)){ready();return;}
        if(polls>=1200){
            std::cerr<<"Source library Learn workbook readiness timed out: expected level="<<level
                     <<" selected="<<(pane?pane->sourceLevelSelection():0)<<"\n";
            setApplicationReturnValue(2);quit();return;
        }
        juce::Timer::callAfterDelay(100,[this,level,ready=std::move(ready),polls]{waitForLearnWorkbook(level,ready,polls+1);});
    }
    void wireLocalProfile(){
        window->home().onOpenLocalProfile=[this]{return beginLocalProfile(localProfileSelfTestCreates_?fathom::desktop::LocalProfileIntent::CreateOrOpen:fathom::desktop::LocalProfileIntent::ExistingOnly);};
        window->home().onOpenExistingLocalProfile=[this]{return beginLocalProfile(fathom::desktop::LocalProfileIntent::ExistingOnly);};
        window->home().onCreateLocalProfile=[this](const std::string& name){return beginLocalProfile(fathom::desktop::LocalProfileIntent::CreateOnly,name);};
    }
    bool beginLocalProfile(fathom::desktop::LocalProfileIntent intent,std::string name={}){
            if(store||localOpening.valid()||!window->home().canOpenLocalProfile()){
                window->home().localProfileFailed("Stop and resolve the current activity before opening a profile; retained activity is unchanged.");return false;
            }
            try{
                const auto path=localProfileSelfTestPath.empty()?fathom::storage::defaultProfilePath():localProfileSelfTestPath;
                const auto zone=fathom::storage::systemIanaTimezone();
#if defined(FATHOM_MAIN_OWNER_TEST)
                const auto opener=fixtureOpener;
                localOpening=std::async(std::launch::async,[path,zone,opener,intent,name]{if(opener)return opener(path,zone);return intent==fathom::desktop::LocalProfileIntent::CreateOnly?fathom::desktop::createNamedLocalProfile(path.parent_path(),name,zone):intent==fathom::desktop::LocalProfileIntent::ExistingOnly?fathom::desktop::openExistingLocalProfile(path.parent_path(),zone):fathom::desktop::openLocalProfile(path,zone,intent);});
#else
                localOpening=std::async(std::launch::async,[path,zone,intent,name]{return intent==fathom::desktop::LocalProfileIntent::CreateOnly?fathom::desktop::createNamedLocalProfile(path.parent_path(),name,zone):intent==fathom::desktop::LocalProfileIntent::ExistingOnly?fathom::desktop::openExistingLocalProfile(path.parent_path(),zone):fathom::desktop::openLocalProfile(path,zone,intent);});
#endif
                window->home().localProfileOpening(true);window->home().setEnabled(false);
                juce::Timer::callAfterDelay(20,[this]{pollLocalOpening();});return true;
            }catch(const std::exception& error){window->home().localProfileFailed(error.what());return false;}
    }
    void pollLocalOpening(){
        if(!localOpening.valid()||!window)return;
        if(localOpening.wait_for(std::chrono::milliseconds(0))!=std::future_status::ready){juce::Timer::callAfterDelay(20,[this]{pollLocalOpening();});return;}
        try{
            auto opened=localOpening.get();profilePath=opened.path;profileId=opened.profileId;
            sessionId=opened.sessionId;profileZone=opened.timezone;store=std::move(opened.store);
            profileDisplayName_=opened.displayName;window->home().setLocalProfileLabel(profileId,profileDisplayName_,profilePath);
            window->home().localProfileOpening(false);
            if(quitRequested){serviceQuit();return;}
            if(!window->home().configureCapture(*store,sessionId,profileZone))throw std::runtime_error("Local profile consumers could not attach; original profile retained");
#if defined(FATHOM_MAIN_OWNER_TEST)
            if(fixtureCheckpoint)fixtureCheckpoint("after_configure");
#endif
            if(!window->home().attachPresentation(*store,profileId))throw std::runtime_error("Presentation/setup attachment refused; original retained");
#if defined(FATHOM_MAIN_OWNER_TEST)
            if(fixtureCheckpoint)fixtureCheckpoint("after_presentation");
#endif
            wireStoreReopen();window->setName(juce::String("Fathom - ")+juce::String::fromUTF8(profileDisplayName_.c_str()));window->home().setEnabled(true);
            std::cout<<"Local offline profile "<<(opened.created?"created":"reopened")<<"; output remains Closed and activity has not started"<<std::endl;
        }catch(const std::exception& error){
            window->home().localProfileOpening(false);
            const std::string reason=error.what();
            if(store){
                // Partial attachment is retained in place. Existing consumers,
                // accepted reads, setup choices and Store lease keep their owners;
                // only the ordinary close coordinator may drain/destroy them.
                localRecoveryHeld=true;window->home().localProfileFailed(reason);
                window->showClosing("Profile attachment failed. Your profile and current choices are retained. Close this window normally before reopening the profile.",false);
                std::cerr<<"LOCAL_PROFILE attachment_held "<<reason<<std::endl;
                if(quitRequested)serviceQuit();
            }else{window->home().setEnabled(true);window->home().localProfileFailed(reason);if(quitRequested)serviceQuit();}
        }
    }
    void pollLocalProfileSelfTest(){
        if(!window)return;
        if(store&&window->home().onReopenStore&&
           window->home().audioSettings().snapshot().state==fathom::output::State::Closed){
            std::cout<<"LOCAL_PROFILE_SELF_TEST PASS profile="<<profileId<<" session="<<sessionId
                     <<" timezone="<<profileZone<<" output=Closed"<<std::endl;
            setApplicationReturnValue(0);quit();return;
        }
        if(++localProfileSelfTestPolls<30){juce::Timer::callAfterDelay(100,[this]{pollLocalProfileSelfTest();});return;}
        std::cerr<<"LOCAL_PROFILE_SELF_TEST FAIL: Home profile action did not attach a Closed local profile"<<std::endl;
        setApplicationReturnValue(2);quit();
    }
    void wireStoreReopen(){
            window->home().onReopenStore=[this]{
                if(reopenFuture||profilePath.empty()||!window->home().detachForStoreReopen())return false;
                store.reset();
                try{fathom::storage::StoreOptions reopen;reopen.path=profilePath;reopen.preferenceValidator=fathom::desktop::presentation::composedPreferenceValidator;store=std::make_unique<fathom::storage::ProfileStore>(reopen);reopenFuture.emplace(store->snapshot(fathom::storage::newUuid()));juce::Timer::callAfterDelay(20,[this]{pollStoreReopen();});return true;}
                catch(const std::exception& e){window->home().storeReopenFailed(e.what());return false;}
            };
    }
    void pollStartup(){
        if(!startup.valid())return;
        if(startup.wait_for(std::chrono::milliseconds(0))!=std::future_status::ready){juce::Timer::callAfterDelay(20,[this]{pollStartup();});return;}
        try {
            auto loaded=startup.get();store=std::move(loaded.store);
            if(quitAfterLoad){serviceQuit();return;}
            if(!window->home().configureCapture(*store,sessionId,profileZone))
                throw std::runtime_error("Original preview consumers could not attach; profile retained");
            if(!window->home().attachPresentation(*store,profileId))throw std::runtime_error("Presentation profile attachment refused; original retained");
                wireStoreReopen();window->setName(juce::String("Fathom - ")+juce::String::fromUTF8(profileDisplayName_.c_str()));window->home().setEnabled(true);
            std::cout<<"Resumed explicit synthetic preview profile "<<profileId<<"; original Session "<<sessionId
                <<"; output remains Closed; no new Session or activity"<<std::endl;
            if(startupSmoke)juce::Timer::callAfterDelay(1000,[this]{systemRequestedQuit();chooseQuit(false);});
        } catch(const std::exception& error){std::cerr<<error.what()<<std::endl;setApplicationReturnValue(2);quit();}
    }
    void pollStoreReopen(){
        if(!reopenFuture||!window)return;
        if(reopenFuture->wait_for(std::chrono::milliseconds(0))!=std::future_status::ready){juce::Timer::callAfterDelay(20,[this]{pollStoreReopen();});return;}
        try{const auto reply=reopenFuture->get();reopenFuture.reset();
            if(reply.status!=fathom::storage::Status::Confirmed||reply.data.object().at("profile_id").string()!=profileId)throw std::runtime_error("The reopened database is not the confirmed original profile");
            bool sessionPresent=false;for(const auto& row:reply.data.object().at("authoritative").object().at("session").array())if(!row.array().empty()&&row.array()[0]==fathom::json::Value(sessionId))sessionPresent=true;
            if(!sessionPresent)throw std::runtime_error("The original synthetic Session is missing; reattachment refused");
            if(!window->home().configureCapture(*store,sessionId,profileZone))throw std::runtime_error("Consumer reattachment refused; original proposal remains retained");
            if(!window->home().attachPresentation(*store,profileId))throw std::runtime_error("Presentation profile attachment refused; original retained");
        }catch(const std::exception& e){reopenFuture.reset();window->home().storeReopenFailed(e.what());std::cerr<<e.what()<<std::endl;}
        if(!quitRequested&&window)window->home().setEnabled(true);
        if(quitAfterLoad){quitAfterLoad=false;serviceQuit();}
    }
    std::future<fathom::desktop::ResumedPreview> startup;
    std::future<fathom::desktop::LocalProfileOpen> localOpening;
    bool quitChoicePending{},quitDiscard{};
    bool startupSmoke{},quitAfterLoad{},quitRequested{},localRecoveryHeld{},quitDiscardCommitted{};
    QuitPhase quitPhase{QuitPhase::None};
    std::chrono::steady_clock::time_point quitStarted{},storeDrainStarted{};
    std::optional<fathom::storage::ProfileStore::Future> reopenFuture;
    std::string profileDisplayName_="Unnamed local profile";
    std::filesystem::path profilePath;
    bool localProfileSelfTestCreates_{};
    std::filesystem::path localProfileSelfTestPath;
    int localProfileSelfTestPolls{};
    std::string sessionId,profileZone,profileId;
    std::unique_ptr<fathom::storage::ProfileStore> store;
    std::unique_ptr<Window> window;
};
}
#if !defined(FATHOM_MAIN_OWNER_TEST)
START_JUCE_APPLICATION(Application)
#endif
