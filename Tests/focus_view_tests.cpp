#include "desktop/PracticeView.hpp"
#include "content/LessonCatalog.hpp"
#include "storage/ProfileStore.hpp"
#include "platform/ProfileAccessMac.hpp"
#import <AppKit/AppKit.h>
#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
using namespace fathom;
namespace {
bool visibleControlsContainedAndDisjoint(juce::Component& root){
 std::vector<juce::Component*> controls;
 const auto collect=[&](auto&& self,juce::Component& node)->void{if(&node!=&root&&!node.isShowing())return;if(dynamic_cast<juce::Button*>(&node)||dynamic_cast<juce::ComboBox*>(&node))controls.push_back(&node);for(auto* child:node.getChildren())self(self,*child);};collect(collect,root);
 if(controls.empty())return false;
 for(auto* control:controls){const auto bounds=root.getLocalArea(control,control->getLocalBounds());if(bounds.isEmpty()||!root.getLocalBounds().contains(bounds))return false;}
 for(std::size_t i=0;i<controls.size();++i)for(std::size_t j=i+1;j<controls.size();++j)if(root.getLocalArea(controls[i],controls[i]->getLocalBounds()).intersects(root.getLocalArea(controls[j],controls[j]->getLocalBounds())))return false;
 return true;
}
bool scrollableReadOnlyLabel(const juce::Label* label){
 if(!label||!label->isShowing())return false;
 for(auto* child:label->getChildren())if(auto* editor=dynamic_cast<juce::TextEditor*>(child))return editor->isShowing()&&editor->isReadOnly()&&editor->isMultiLine()&&editor->getText()==label->getText()&&label->getLocalBounds().contains(editor->getBounds());
 return false;
}
bool supportedFocusRegions(desktop::PracticeView& view,const juce::Label* heading,const juce::Label* facts,const juce::Label* feedback){
 auto* presentation=view.findChildWithID("practice-presentation");auto& save=view.saveStatusView();auto& tab=view.tabView();
 const std::vector<const juce::Component*> regions{presentation,heading,facts,&save,&tab,feedback};
 for(const auto* region:regions)if(!region||!region->isShowing()||region->getBounds().isEmpty()||!view.getLocalBounds().contains(region->getBounds()))return false;
 for(std::size_t i=0;i<regions.size();++i)for(std::size_t j=i+1;j<regions.size();++j)if(regions[i]->getBounds().intersects(regions[j]->getBounds()))return false;
 for(const auto* id:{"practice-audio-settings","practice-start","practice-pause","practice-resume","practice-stop","lesson-tempo","scheduled-passes"})if(auto* control=view.findChildWithID(id);control&&control->isShowing())if(control->getY()<heading->getBottom()||control->getBottom()>facts->getY()||control->getBottom()>save.getY())return false;
 auto* clean=view.findChildWithID("practice-clean");auto* back=view.findChildWithID("practice-back");auto* focus=view.findChildWithID("practice-focus");
 // Facts and Save use scrollable read-only editors. Bottom command feedback is
 // a Label whose complete current text is retained in its tooltip and AX help.
 return clean&&back&&focus&&tab.getY()==144&&facts->getBottom()<=tab.getY()&&save.getBottom()<=tab.getY()&&tab.getBottom()<=clean->getY()&&clean->getBottom()<=feedback->getY()&&back->getY()==feedback->getY()&&focus->getY()==feedback->getY()&&scrollableReadOnlyLabel(facts)&&scrollableReadOnlyLabel(dynamic_cast<const juce::Label*>(save.findChildWithID("practice-save-status")))&&feedback->getText().toStdString()==view.commandFeedback()&&const_cast<juce::Label*>(feedback)->getTooltip()==feedback->getText()&&feedback->getMinimumHorizontalScale()==1.0f&&visibleControlsContainedAndDisjoint(view);
}
}
int main(int argc,char**argv){int n=0;try{
 if(argc==4&&(std::string(argv[3])=="--admitted-focus-integration"||std::string(argv[3])=="--native-focus-navigation"||std::string(argv[3])=="--focus-text-scaling"||std::string(argv[3])=="--compact-tab-integration")){
  const bool nativeNavigation=std::string(argv[3])=="--native-focus-navigation";
  const bool textScaling=std::string(argv[3])=="--focus-text-scaling";
  const bool compactTab=std::string(argv[3])=="--compact-tab-integration";
  const std::filesystem::path bundle=argv[1],root=argv[2];
  if(!bundle.is_absolute()||!root.is_absolute()||std::filesystem::exists(root))throw std::runtime_error("Absolute retained bundle and new absolute evidence directory required");
  std::filesystem::create_directories(root);
  std::ofstream checks(root/"admitted-focus-checks.tsv"),observations(root/"admitted-focus-keys.tsv"),nativeDiagnostics(root/"admitted-focus-native-context.tsv");
  const auto ck=[&](bool okay,const std::string& name){++n;checks<<name<<'\t'<<(okay?"PASS":"FAIL")<<'\n';if(!okay)throw std::runtime_error(name);};
  [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];juce::ScopedJuceInitialiser_GUI gui;
  auto catalog=lesson::Catalog::load(bundle);
  ck(catalog&&catalog->lessons().size()==13,"retained representative catalog loads without a new admission");
  const auto admitted=catalog->admit("fg:item:000002","fg:variant:000006");
  const auto& identity=admitted->identity().object();
  ck(admitted->practiceAllowed()&&identity.at("item_id").string()=="fg:item:000002"&&identity.at("variant_id").string()=="fg:variant:000006"&&identity.at("content_version").string()=="representative-controls.1"&&storage::canonical(identity.at("content_revision"))=="2","exact retained admitted source and content identity");
  const auto& refs=admitted->model()->source().sourceRefs;
  ck(refs==std::vector<std::string>{"L3-TXT5-21","L3-TXT28-46"},"source references remain the accepted L3 pair");
  const auto profileDir=root/"private-profile";std::filesystem::create_directories(profileDir);std::filesystem::permissions(profileDir,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
  storage::StoreOptions options;options.path=profileDir/"profile.sqlite";options.create=true;options.createdUtc="2026-09-23T10:00:00Z";
  storage::ProfileStore store(options);const auto session=store.createSession(storage::newUuid(),"2026-09-23T10:00:00Z","America/New_York",{},json::Value::Object{{"synthetic_fixture",true}}).get();
  ck(session.status==storage::Status::Confirmed&&!session.owner.empty(),"disposable authoritative Session created before Practice browsing");
  const auto before=store.snapshot(storage::newUuid()).get();ck(before.status==storage::Status::Confirmed,"before-browse Store snapshot confirmed");
  desktop::PracticeView practice;practice.setSize(920,680);practice.addToDesktop(juce::ComponentPeer::windowHasTitleBar);practice.setVisible(true);
  ck(practice.configureCapture(store,session.owner,[]{return std::string{"2026-09-23T10:00:00Z"};},"America/New_York")&&practice.configureLesson(admitted,60),"retained admitted source binds one stopped Practice owner");
  ck(practice.lessonAdmission()==admitted&&practice.captureSessionId()==session.owner&&practice.captureSession()&&practice.captureSession()->phase()==capture::SessionPhase::Idle&&practice.outputStatus().lifecycle.state==output::State::Closed,"Practice retains source Session identity with no Attempt or output on entry");
  ck(practice.tabVisible()&&practice.tabView().document()&&!practice.tabView().document()->source().events.empty(),"authored TAB is visible for the admitted source");
  const auto retainedDocument=practice.tabView().document();const auto retainedSelection=practice.tabView().selectedEvent();const auto retainedDetail=practice.tabView().visibleDetail();const auto retainedPlayback=practice.tabView().playingEvents();const auto retainedZoom=practice.tabView().zoom();const auto retainedScroll=practice.tabView().scrollPosition();const auto retainedCapture=practice.captureSession();const auto retainedAudio=practice.outputStatus();const auto retainedTempo=practice.tempoFacts();const auto retainedPasses=practice.lessonScheduledPasses();const auto retainedBeat=practice.lessonBeatClick();const auto retainedIdentity=storage::canonical(admitted->identity());
  const auto presentationUnchanged=[&]{const auto audio=practice.outputStatus();return practice.lessonAdmission()==admitted&&storage::canonical(admitted->identity())==retainedIdentity&&practice.captureSession()==retainedCapture&&practice.captureSessionId()==session.owner&&practice.captureSession()->phase()==capture::SessionPhase::Idle&&!practice.captureSession()->startTaken()&&!practice.coordinator().pending()&&practice.coordinator().activeFrames()==0&&practice.coordinator().completedCycles()==0&&practice.tempoFacts()==retainedTempo&&practice.lessonScheduledPasses()==retainedPasses&&practice.lessonBeatClick()==retainedBeat&&practice.tabView().document()==retainedDocument&&practice.tabView().selectedEvent()==retainedSelection&&practice.tabView().visibleDetail()==retainedDetail&&practice.tabView().playingEvents()==retainedPlayback&&practice.tabView().zoom()==retainedZoom&&practice.tabView().scrollPosition()==retainedScroll&&audio.lifecycle.state==retainedAudio.lifecycle.state&&audio.lifecycle.owner==retainedAudio.lifecycle.owner&&audio.lifecycle.pendingOutcome==retainedAudio.lifecycle.pendingOutcome&&audio.lifecycle.stopRequested==retainedAudio.lifecycle.stopRequested&&audio.lifecycle.submittedFrames==retainedAudio.lifecycle.submittedFrames&&audio.lifecycle.confirmedFrames==retainedAudio.lifecycle.confirmedFrames&&audio.callbacks==retainedAudio.callbacks&&audio.renderedBlocks==retainedAudio.renderedBlocks&&audio.commandAccepted==retainedAudio.commandAccepted&&audio.commandRejected==retainedAudio.commandRejected&&audio.mix.bus==retainedAudio.mix.bus&&audio.mix.master==retainedAudio.mix.master&&audio.mix.masterMute==retainedAudio.mix.masterMute&&audio.mix.muteMask==retainedAudio.mix.muteMask&&audio.mix.soloAB==retainedAudio.mix.soloAB;};
  practice.setPresentation(desktop::presentation::Level::Beginner,std::nullopt);const auto beginnerFacts=practice.focusFacts();
  ck(beginnerFacts.find("Tempo 60 BPM")!=std::string::npos&&beginnerFacts.find("Passes 0/")!=std::string::npos&&beginnerFacts.find("Practice owner Session:")==std::string::npos&&presentationUnchanged(),"Beginner primary facts change disclosure while preserving exact source, owner, stopped transport, audio, mix and TAB state");
  practice.setPresentation(desktop::presentation::Level::Beginner,desktop::presentation::Level::Advanced);const auto advancedFacts=practice.focusFacts();
  ck(advancedFacts!=beginnerFacts&&advancedFacts.find("Selected: 60 BPM")!=std::string::npos&&advancedFacts.find("Current: 60 BPM")!=std::string::npos&&advancedFacts.find("Count-in Off | Scheduled passes")!=std::string::npos&&advancedFacts.find("Practice owner Session:")==std::string::npos&&presentationUnchanged(),"Advanced session override exposes musical facts without changing source, Session, audio or transport");
  practice.setPresentation(desktop::presentation::Level::Beginner,desktop::presentation::Level::Developer);const auto developerFacts=practice.focusFacts();
  auto* presentationSelector=dynamic_cast<juce::ComboBox*>(practice.findChildWithID("practice-presentation"));
  ck(developerFacts!=advancedFacts&&developerFacts.find("Practice owner Session: "+session.owner)!=std::string::npos&&presentationSelector&&presentationSelector->getSelectedId()==4&&presentationSelector->getTitle().contains("this page, session only")&&presentationUnchanged(),"Developer session override retains existing exact owner diagnostics with unchanged authority and state");
  practice.setPresentation(desktop::presentation::Level::Beginner,std::nullopt);
  ck(practice.focusFacts()==beginnerFacts&&presentationSelector->getSelectedId()==1&&presentationSelector->getTitle().contains("Beginner (global)")&&presentationUnchanged(),"Use global restores Beginner disclosure and clears only the page override");
  const auto afterDisclosure=store.snapshot(storage::newUuid()).get();ck(afterDisclosure.status==storage::Status::Confirmed&&storage::canonical(afterDisclosure.data)==storage::canonical(before.data),"all presentation Level changes leave authoritative Store byte-identical");
  practice.setPresentation(desktop::presentation::Level::Developer,std::nullopt);ck(practice.focusFacts()==developerFacts&&presentationUnchanged(),"Developer global presentation restores complete facts for retained diagnostic checks without a Practice command");
  practice.grabKeyboardFocus();NSView* native=(__bridge NSView*)practice.getPeer()->getNativeHandle();[native.window makeKeyAndOrderFront:nil];
  NSEvent* fixtureEvent=nil;
  const char* contextHeader="fixture_event_hw\tfixture_event_down\tfixture_event_window\tcurrent_peer_window\toriginal_view_window\tapp_key_window\tevent_matches_current_peer\tcurrent_view_matches_original\tpeer_present\tpractice_showing\tfocused_type\tfocused_id\tfocused_title\tfocused_is_practice\tfocused_in_practice\tinput_descendant_focus";
  const auto nativeContext=[&](std::ostream& stream,NSEvent* event){
   auto* peer=practice.getPeer();NSView* currentNative=peer?(__bridge NSView*)peer->getNativeHandle():nil;NSWindow* currentWindow=currentNative.window;NSWindow* eventWindow=event?event.window:nil;
   auto* focused=juce::Component::getCurrentlyFocusedComponent();bool inputFocus=false;for(auto* ancestor=focused;ancestor&&ancestor!=&practice;ancestor=ancestor->getParentComponent())if(practice.isParentOf(ancestor)&&(dynamic_cast<juce::ComboBox*>(ancestor)||dynamic_cast<juce::TextEditor*>(ancestor))){inputFocus=true;break;}
   const char* type=!focused?"none":focused==&practice?"Practice":dynamic_cast<juce::TextEditor*>(focused)?"TextEditor":dynamic_cast<juce::ComboBox*>(focused)?"ComboBox":dynamic_cast<juce::Button*>(focused)?"Button":"Other";
   const auto clean=[](juce::String value){return value.replaceCharacter('\n',' ').replaceCharacter('\r',' ').replaceCharacter('\t',' ').toStdString();};
   stream<<(event?static_cast<int>(event.keyCode):-1)<<'\t'<<(event&&event.type==NSEventTypeKeyDown)<<'\t'<<(eventWindow?eventWindow.windowNumber:-1)<<'\t'<<(currentWindow?currentWindow.windowNumber:-1)<<'\t'<<(native.window?native.window.windowNumber:-1)<<'\t'<<(NSApp.keyWindow?NSApp.keyWindow.windowNumber:-1)<<'\t'<<(event&&currentWindow&&eventWindow==currentWindow)<<'\t'<<(currentNative==native)<<'\t'<<(peer!=nullptr)<<'\t'<<practice.isShowing()<<'\t'<<type<<'\t'<<(focused?clean(focused->getComponentID()):"<none>")<<'\t'<<(focused?clean(focused->getTitle()):"<none>")<<'\t'<<(focused==&practice)<<'\t'<<(focused&&practice.isParentOf(focused))<<'\t'<<inputFocus;
  };
  observations<<"key\thardware\tdown\tconsumed\tinvoked\trepeat\tmodified\tmatched_window\tvisible\t"<<contextHeader<<'\n';
  nativeDiagnostics<<"phase\t"<<contextHeader<<'\n';
  int observed=0,invoked=0;practice.onKeyObservation=[&](const desktop::PracticeKeyObservation& event){++observed;invoked+=event.invoked;observations<<event.key<<'\t'<<event.hardwareKey<<'\t'<<event.down<<'\t'<<event.consumed<<'\t'<<event.invoked<<'\t'<<event.repeat<<'\t'<<event.modified<<'\t'<<event.matchedWindow<<'\t'<<event.visible<<'\t';nativeContext(observations,fixtureEvent);observations<<'\n';observations.flush();};
  const auto key=[&](NSString* text,unsigned short code,bool down){auto* event=[NSEvent keyEventWithType:down?NSEventTypeKeyDown:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:text charactersIgnoringModifiers:text isARepeat:NO keyCode:code];fixtureEvent=event;nativeDiagnostics<<"before-send\t";nativeContext(nativeDiagnostics,event);nativeDiagnostics<<'\n';nativeDiagnostics.flush();auto* currentPeer=practice.getPeer();NSView* currentNative=currentPeer?(__bridge NSView*)currentPeer->getNativeHandle():nil;ck(event&&currentNative.window&&event.window==currentNative.window,"constructed native event window equals current Practice peer window before delivery");[NSApp sendEvent:event];fixtureEvent=nil;};
  const auto tap=[&](NSString* text,unsigned short code){key(text,code,true);key(text,code,false);};
  const auto visibleFocusOrder=[&]{std::vector<const juce::Component*> controls;for(auto* child:practice.getChildren())if(child->isVisible()&&(dynamic_cast<const juce::Button*>(child)||dynamic_cast<const juce::ComboBox*>(child)))controls.push_back(child);std::sort(controls.begin(),controls.end(),[](const auto* left,const auto* right){return left->getY()==right->getY()?left->getX()<right->getX():left->getY()<right->getY();});int prior=0;for(const auto* control:controls){const auto order=control->getExplicitFocusOrder();if(order<=prior)return false;prior=order;}return !controls.empty();};
  practice.setSize(640,680);
  // Native window activation and layout may focus a read-only text descendant.
  // Page shortcuts deliberately refuse input focus; establish their real target
  // after both operations rather than relying on the earlier focus request.
  practice.grabKeyboardFocus();ck(practice.hasKeyboardFocus(false)&&juce::Component::getCurrentlyFocusedComponent()==&practice,"native Practice command focus established after window activation and compact layout");
  tap(@"f",3);ck(practice.focusMode()&&observed==2&&invoked==1,"synthetic F keyboard route enters Focus once");
  const auto facts=practice.focusFacts();ck(facts.find("Selected: 60 BPM")!=std::string::npos&&facts.find("Current: 60 BPM")!=std::string::npos&&facts.find("Target:")!=std::string::npos&&facts.find("Scheduled:")!=std::string::npos&&facts.find("Practice owner Session: "+session.owner)!=std::string::npos,"Focus shows admitted BPM, loop, progress and exact Session owner");
  ck(practice.tabVisible()&&practice.tabView().document()&&practice.tabView().document()->source().events.size()==admitted->model()->source().events.size(),"Focus retains the authored TAB event projection");
  std::vector<const juce::Component*> narrowControls;bool beatClick=false,scheduled=false,contained=true,nonoverlap=true;
  for(auto* child:practice.getChildren())if(child->isVisible()&&(dynamic_cast<const juce::Button*>(child)||dynamic_cast<const juce::ComboBox*>(child))){
   narrowControls.push_back(child);contained=contained&&child->getWidth()>0&&child->getHeight()>0&&practice.getLocalBounds().contains(child->getBounds());
   if(auto* button=dynamic_cast<const juce::Button*>(child))beatClick=beatClick||button->getButtonText().contains("quarter-note beat click");
   if(child->getComponentID()=="scheduled-passes")scheduled=true;
  }
  for(std::size_t i=0;i<narrowControls.size();++i)for(std::size_t j=i+1;j<narrowControls.size();++j)
   nonoverlap=nonoverlap&&!narrowControls[i]->getBounds().intersects(narrowControls[j]->getBounds());
  ck(beatClick&&scheduled&&contained&&nonoverlap,"640px backward-compatible Focus below the current minimum contains separate visible transport, beat-click and scheduled-pass controls");
  ck(visibleFocusOrder()&&practice.findChildWithID("practice-clean")->getExplicitFocusOrder()<practice.findChildWithID("practice-save")->getExplicitFocusOrder(),"640px keyboard focus order follows visible rows, with Clean before Save");
  auto* narrowStatus=dynamic_cast<juce::Label*>(practice.findChildWithID("practice-status"));
  ck(narrowStatus&&narrowStatus->getText().contains("Source refs: L3-TXT5-21, L3-TXT28-46")&&narrowStatus->getText().contains("Save remains separate")&&narrowStatus->getTooltip().contains("Selected workbook identity"),"640px compatibility retains concise non-color state text and full source detail in its tooltip");
  auto* start=practice.findChildWithID("practice-start");auto* again=practice.findChildWithID("practice-again");
  ck(start&&again&&practice.getLocalBounds().contains(practice.tabView().getBounds())&&practice.tabView().getBounds().getBottom()<=start->getY()&&again->getBounds().getRight()<=practice.getWidth(),"640px authored TAB stays above contained Focus command rows");
  juce::Viewport* canvasViewport=nullptr;juce::TextButton* tabLarger=nullptr;
  for(auto* child:practice.tabView().getChildren()){if(auto* viewport=dynamic_cast<juce::Viewport*>(child))canvasViewport=viewport;if(auto* button=dynamic_cast<juce::TextButton*>(child);button&&button->getButtonText()=="Zoom +")tabLarger=button;}
  if(compactTab){
   auto* focusControl=dynamic_cast<juce::TextButton*>(practice.findChildWithID("practice-focus"));auto* saveControl=practice.findChildWithID("practice-save");juce::ComboBox* assessmentControl=nullptr;
   for(auto* child:practice.getChildren())if(auto* combo=dynamic_cast<juce::ComboBox*>(child);combo&&combo->getTitle()=="Explicit self-assessment")assessmentControl=combo;
   const juce::Label* shortcuts=nullptr;for(auto* child:practice.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getTitle()=="Practice keyboard shortcuts")shortcuts=label;
   ck(canvasViewport&&tabLarger&&canvasViewport->isVisible()&&canvasViewport->getHeight()>=70&&canvasViewport->getViewedComponent()&&canvasViewport->getViewedComponent()->getHeight()>canvasViewport->getHeight()&&canvasViewport->getY()>=tabLarger->getBottom(),"640px compatibility exposes a scrollable authored TAB canvas below Zoom controls (prior viewport: 2px)");
   ck(focusControl&&shortcuts&&!shortcuts->isVisible()&&focusControl->getTooltip()==shortcuts->getText()&&focusControl->getHelpText()==shortcuts->getText()&&focusControl->getAccessibilityHandler()->getHelp()==shortcuts->getText(),"compact Focus keeps full shortcut help in exit control tooltip and accessibility help");
   ck(assessmentControl&&saveControl&&assessmentControl->getY()==start->getY()&&saveControl->getY()>assessmentControl->getY()&&practice.findChildWithID("practice-clean")->getX()<saveControl->getX(),"640px transport/assessment and result commands occupy distinct visual rows with Clean before Save");
  }
  bool correctedTabHeading=false;for(auto* child:practice.tabView().getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->isVisible()&&label->getText().toStdString()=="TAB — Authored source view")correctedTabHeading=true;
  ck(correctedTabHeading,"Pinned P03 TabView renders the exact UTF-8 authored TAB heading inside 640px Focus");
  {auto snapshot=practice.createComponentSnapshot(practice.getLocalBounds());juce::FileOutputStream file(juce::File((root/"focus-640.png").string()));juce::PNGImageFormat png;ck(file.openedOk()&&png.writeImageToStream(snapshot,file),"640px admitted Focus snapshot written");file.flush();ck(!file.getStatus().failed(),"640px admitted Focus snapshot flushed");}
  tap(@" ",49);ck(invoked==2&&practice.commandFeedback()=="Wait for the current transition or finish the original result; Start also needs enabled audio and a test profile."&&practice.outputStatus().lifecycle.state==output::State::Closed,"synthetic Space transport refuses Start without enabled output");
  tap(@"c",8);ck(invoked==3&&practice.commandFeedback()=="Clean requires an ended result in review. Sealed assessments cannot change; finish saving, then use Again.","synthetic Clean refuses before Review");
  tap(@"a",0);ck(invoked==4&&practice.commandFeedback()=="Again requires confirmed persistence and cleared output. Save or reconcile the original first.","synthetic Again refuses before a saved Attempt");
  juce::Label* feedback=nullptr;for(auto* child:practice.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getTitle()=="Practice command feedback")feedback=label;
  ck(feedback&&feedback->isVisible()&&feedback->getHeight()>=42&&feedback->getText().toStdString()==practice.commandFeedback()&&feedback->getTooltip().toStdString()==practice.commandFeedback(),"640px refusal remains full textual feedback with a two-line region and complete tooltip");
  {auto snapshot=practice.createComponentSnapshot(practice.getLocalBounds());juce::FileOutputStream file(juce::File((root/"feedback-640.png").string()));juce::PNGImageFormat png;ck(file.openedOk()&&png.writeImageToStream(snapshot,file),"640px refusal feedback snapshot written");file.flush();ck(!file.getStatus().failed(),"640px refusal feedback snapshot flushed");}
  practice.setSize(920,680);
  int wideOrder=0;bool wideKeyboardOrder=true;for(const auto* id:{"practice-audio-settings","practice-back","practice-focus","scheduled-passes","lesson-tempo","practice-start","practice-pause","practice-resume","practice-stop","practice-clean","practice-save","practice-again"}){auto* control=practice.findChildWithID(id);wideKeyboardOrder=wideKeyboardOrder&&control&&control->getExplicitFocusOrder()==++wideOrder;}
  ck(wideKeyboardOrder&&practice.findChildWithID("practice-clean")->getExplicitFocusOrder()<practice.findChildWithID("practice-save")->getExplicitFocusOrder(),"920px Focus retains the explicit critical-control keyboard sequence with Clean before Save independently of visual rows");
  juce::Label* wideTitle=nullptr;juce::Label* wideFacts=nullptr;
  for(auto* child:practice.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child)){
   if(label->isVisible()&&label->getText().startsWith("Focus |"))wideTitle=label;
   if(label->getTitle()=="Practice tempo, loop and confirmed session facts")wideFacts=label;
  }
  auto* wideSetup=practice.findChildWithID("setup-summary");
  ck(wideTitle&&wideFacts&&wideSetup&&!wideSetup->isVisible()&&wideTitle->getText()=="Focus | Level 3 | Whole case"&&wideTitle->getTooltip().contains("fg:item:000002 / fg:variant:000006")&&supportedFocusRegions(practice,wideTitle,wideFacts,feedback),"920px admitted Focus has a readable primary caption, complete exact identity tooltip, disjoint header/transport, scrollable facts and Save, primary TAB at y144, and bottom feedback");
  ck(narrowStatus->getText().contains("Source refs: L3-TXT5-21, L3-TXT28-46")&&narrowStatus->getTooltip().contains("Selected workbook identity"),"920px admitted Focus retains concise source state and full authoritative tooltip");
  ck(feedback&&feedback->isVisible()&&feedback->getHeight()>=30&&feedback->getText().toStdString()==practice.commandFeedback()&&feedback->getTooltip().toStdString()==practice.commandFeedback(),"920px refusal retains explicit full-text and tooltip feedback");
  auto& retainedDetails=practice.saveStatusView().detailsView();
  ck(retainedDetails.isReadOnly()&&retainedDetails.getText().contains("Practice owner Session: "+juce::String(session.owner))&&retainedDetails.getText().contains("Source refs: L3-TXT5-21, L3-TXT28-46")&&retainedDetails.getText().contains("Guitar setup")&&retainedDetails.getText().contains("Keyboard help")&&wideFacts->getTooltip().contains("Practice owner Session: "+juce::String(session.owner)),"Developer complete source, owner, setup and shortcut context remains in read-only Save details and full facts tooltip");
  practice.saveStatusView().showDetails(true);ck(retainedDetails.isShowing()&&!practice.tabView().isVisible()&&practice.getLocalBounds().contains(retainedDetails.getBounds())&&retainedDetails.getBounds()==practice.tabView().getBounds(),"explicit Save details disclosure presents the retained full context in the contained notation workspace");practice.saveStatusView().showDetails(false);ck(practice.tabView().isShowing()&&!retainedDetails.isVisible(),"closing Save details restores authored TAB without changing source or owner");
  if(compactTab)ck(canvasViewport&&canvasViewport->getHeight()>=70&&supportedFocusRegions(practice,wideTitle,wideFacts,feedback),"920px supported Focus exposes scrollable TAB below transport and facts, above separate result and feedback rows");
  {auto snapshot=practice.createComponentSnapshot(practice.getLocalBounds());juce::FileOutputStream file(juce::File((root/"focus-920.png").string()));juce::PNGImageFormat png;ck(file.openedOk()&&png.writeImageToStream(snapshot,file),"920px admitted Focus top-text snapshot written");file.flush();ck(!file.getStatus().failed(),"920px admitted Focus top-text snapshot flushed");}
  {auto snapshot=practice.createComponentSnapshot(practice.getLocalBounds());juce::FileOutputStream file(juce::File((root/"feedback-920.png").string()));juce::PNGImageFormat png;ck(file.openedOk()&&png.writeImageToStream(snapshot,file),"920px refusal feedback snapshot written");file.flush();ck(!file.getStatus().failed(),"920px refusal feedback snapshot flushed");}
  if(nativeNavigation){
   std::ofstream trace(root/"focus-navigation.tsv");trace<<"width\tdirection\tfocused_id\tenabled\tvisible\n";
   const auto navigate=[&](int width,bool reverse){const auto chars=reverse?@"\u0019":@"\t";const auto flags=reverse?NSEventModifierFlagShift:static_cast<NSEventModifierFlags>(0);
    for(bool down:{true,false}){auto* event=[NSEvent keyEventWithType:down?NSEventTypeKeyDown:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:flags timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:chars charactersIgnoringModifiers:chars isARepeat:NO keyCode:48];[NSApp sendEvent:event];}
    auto* focused=juce::Component::getCurrentlyFocusedComponent();trace<<width<<'\t'<<(reverse?"Shift-Tab":"Tab")<<'\t'<<(focused?focused->getComponentID().toStdString():"<none>")<<'\t'<<(focused&&focused->isEnabled())<<'\t'<<(focused&&focused->isShowing())<<'\n';return focused;};
   for(int width:{640,920}){
    practice.setSize(width,680);[native.window makeKeyAndOrderFront:nil];
    auto* first=practice.findChildWithID(width==640?"practice-focus":"practice-audio-settings");
    auto* second=practice.findChildWithID(width==640?"practice-audio-settings":"practice-back");
    ck(first&&second&&first->isEnabled()&&second->isEnabled(),"native Tab route begins with visible enabled Focus controls");
    first->grabKeyboardFocus();ck(juce::Component::getCurrentlyFocusedComponent()==first,"native Tab route established JUCE keyboard focus in active AppKit window");
    ck(navigate(width,false)==second,"constructed AppKit Tab reaches next visible Focus control");
    ck(navigate(width,true)==first,"constructed AppKit Shift-Tab returns to prior visible Focus control");
    auto* scheduled=practice.findChildWithID("scheduled-passes");auto* tempo=practice.findChildWithID("lesson-tempo");
    ck(scheduled&&tempo&&scheduled->isEnabled()&&tempo->isEnabled(),"scheduled passes and tempo control remain enabled Focus navigation targets");
    tempo->grabKeyboardFocus();ck(juce::Component::getCurrentlyFocusedComponent()==tempo&&navigate(width,true)==scheduled,"constructed AppKit Shift-Tab traverses backward from tempo to scheduled passes");
    auto* startControl=practice.findChildWithID("practice-start");auto* saveControl=practice.findChildWithID("practice-save");
    ck(startControl&&saveControl&&!startControl->isEnabled()&&!saveControl->isEnabled(),"Start and Save remain disabled without enabled audio or a reviewed result");
    bool skippedDisabled=true,sawTempo=false,sawDetails=false;for(int step=0;step<24;++step){auto* focused=navigate(width,false);skippedDisabled=skippedDisabled&&focused&&focused->isEnabled()&&focused->isShowing()&&focused!=startControl&&focused!=saveControl;sawTempo=sawTempo||focused==tempo;sawDetails=sawDetails||(focused&&focused->getComponentID()=="practice-save-details");}
    ck(sawTempo&&sawDetails&&skippedDisabled,"constructed AppKit Tab traverses tempo and Save details while skipping disabled Start and Save");
   }
   auto* accessibleFeedback=feedback?feedback->getAccessibilityHandler():nullptr;
   ck(feedback&&accessibleFeedback&&feedback->getText().toStdString()==practice.commandFeedback()&&feedback->getTooltip().toStdString()==practice.commandFeedback()&&accessibleFeedback->getTitle()==feedback->getText()&&accessibleFeedback->getHelp()==feedback->getText()&&feedback->getText().contains("Again requires confirmed persistence"),"full refusal remains available from visible label, tooltip and accessibility title/help after native traversal");
   trace.flush();ck(trace.good(),"native focus trace flushed");
  }
  if(textScaling){
   juce::TextButton* smaller=nullptr;juce::TextButton* larger=nullptr;juce::TextButton* reset=nullptr;juce::Label* playbackLabel=nullptr;juce::TextEditor* sourceEditor=nullptr;
   for(auto* child:practice.tabView().getChildren()){
    if(auto* button=dynamic_cast<juce::TextButton*>(child)){if(button->getButtonText()=="Zoom -")smaller=button;if(button->getButtonText()=="Zoom +")larger=button;if(button->getButtonText()=="Reset 100%")reset=button;}
    if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText().contains("Count-in Off"))playbackLabel=label;
    if(auto* editor=dynamic_cast<juce::TextEditor*>(child);editor&&editor->getTitle()=="Selected event or complete source instructions")sourceEditor=editor;
   }
   auto* captureLabel=dynamic_cast<juce::Label*>(practice.saveStatusView().findChildWithID("practice-save-status"));
   ck(smaller&&larger&&reset&&captureLabel&&playbackLabel&&sourceEditor&&smaller->getWantsKeyboardFocus()&&larger->getWantsKeyboardFocus()&&reset->isShowing()&&!reset->isEnabled()&&practice.tabView().zoom()==1.0,"TAB Zoom controls are keyboard reachable, Reset 100% is disabled at baseline, and capture/playback/source text identified");
   const auto pump=[](){CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);if(auto* event=[NSApp nextEventMatchingMask:NSEventMaskAny untilDate:[NSDate dateWithTimeIntervalSinceNow:0.001] inMode:NSDefaultRunLoopMode dequeue:YES])[NSApp sendEvent:event];};
   const auto click=[&](juce::TextButton& button){struct Listener final:juce::Button::Listener{bool delivered{};void buttonClicked(juce::Button*)override{delivered=true;}} listener;button.addListener(&listener);button.triggerClick();const auto until=std::chrono::steady_clock::now()+std::chrono::seconds(2);while(!listener.delivered&&std::chrono::steady_clock::now()<until)pump();button.removeListener(&listener);if(!listener.delivered)throw std::runtime_error("Zoom button delivery watchdog");};
   auto* heading=const_cast<juce::Label*>(wideTitle);auto* factLabel=const_cast<juce::Label*>(wideFacts);
   const auto picture=[&](int width,const char* phase){auto snapshot=practice.createComponentSnapshot(practice.getLocalBounds());juce::FileOutputStream file(juce::File((root/("scale-"+std::to_string(width)+"-"+phase+".png")).string()));juce::PNGImageFormat png;ck(file.openedOk()&&png.writeImageToStream(snapshot,file),"Focus text-scale snapshot written");file.flush();ck(!file.getStatus().failed(),"Focus text-scale snapshot flushed");};
   for(int width:{640,920}){
    practice.setSize(width,680);ck(practice.tabView().zoom()==1.0&&smaller->isEnabled()&&larger->isEnabled()&&!reset->isEnabled(),"Focus scaling starts at 100% TAB zoom with both Zoom controls available and Reset disabled");
    const auto baseHeading=heading->getFont().getHeight(),baseFacts=factLabel->getFont().getHeight(),baseState=narrowStatus->getFont().getHeight(),baseCapture=captureLabel->getFont().getHeight(),baseFeedback=feedback->getFont().getHeight(),basePlayback=playbackLabel->getFont().getHeight(),baseSource=sourceEditor->getFont().getHeight();
    picture(width,"baseline");click(*larger);
    ck(practice.tabView().zoom()==1.25&&heading->getFont().getHeight()>baseHeading&&factLabel->getFont().getHeight()>baseFacts&&narrowStatus->getFont().getHeight()>baseState&&captureLabel->getFont().getHeight()>baseCapture&&feedback->getFont().getHeight()>baseFeedback&&playbackLabel->getFont().getHeight()>basePlayback&&sourceEditor->getFont().getHeight()>baseSource,"Zoom + immediately scales heading, tempo/state, capture, feedback and TAB playback/source text");
    larger->grabKeyboardFocus();key(@"\t",48,true);key(@"\t",48,false);ck(reset->isEnabled()&&reset->getWantsKeyboardFocus()&&juce::Component::getCurrentlyFocusedComponent()==reset,"constructed AppKit Tab reaches keyboard-enabled Reset 100% from Zoom +");click(*reset);
    ck(practice.tabView().zoom()==1.0&&!reset->isEnabled()&&heading->getFont().getHeight()==baseHeading&&factLabel->getFont().getHeight()==baseFacts&&narrowStatus->getFont().getHeight()==baseState&&captureLabel->getFont().getHeight()==baseCapture&&feedback->getFont().getHeight()==baseFeedback&&playbackLabel->getFont().getHeight()==basePlayback&&sourceEditor->getFont().getHeight()==baseSource&&practice.lessonAdmission()==admitted&&practice.captureSessionId()==session.owner&&practice.tabView().document()==retainedDocument&&practice.tabView().selectedEvent()==retainedSelection&&practice.captureSession()->phase()==capture::SessionPhase::Idle&&!practice.captureSession()->startTaken()&&practice.outputStatus().lifecycle.state==output::State::Closed&&practice.outputStatus().callbacks==0&&!practice.coordinator().pending(),"Reset 100% restores every Focus and TAB font while preserving exact source/selection, Session and stopped audio without an Attempt");
    const auto afterReset=store.snapshot(storage::newUuid()).get();ck(afterReset.status==storage::Status::Confirmed&&storage::canonical(afterReset.data)==storage::canonical(before.data),"actual Zoom Reset leaves authoritative Store byte-identical");click(*larger);
    for(int i=0;i<3;++i)click(*larger);
    ck(practice.tabView().zoom()==2.0&&!larger->isEnabled()&&smaller->isEnabled()&&practice.lessonAdmission()==admitted&&practice.captureSessionId()==session.owner,"Zoom + reaches bounded TAB maximum without changing source or Session owner");
    ck(heading->getTooltip().contains("fg:item:000002 / fg:variant:000006")&&factLabel->getTooltip().contains("Practice owner Session: "+juce::String(session.owner))&&narrowStatus->getTooltip().contains("Selected workbook identity")&&captureLabel->getTooltip().contains("Open Audio settings")&&feedback->getTooltip()==feedback->getText()&&feedback->getMinimumHorizontalScale()==1.0f,"enlarged concise Focus text retains exact source, owner, status, capture and refusal without horizontal font shrink");
    if(width<900)ck(heading->getBottom()<=factLabel->getY()&&factLabel->getBottom()<=narrowStatus->getY()&&narrowStatus->getBottom()<=captureLabel->getParentComponent()->getY()&&captureLabel->getParentComponent()->getBottom()<=feedback->getY()&&feedback->getBottom()<=practice.tabView().getY()&&practice.tabView().getBottom()<=start->getY(),"640px below-minimum compatibility retains enlarged text-region bounds and TAB separation from transport rows");else ck(supportedFocusRegions(practice,heading,factLabel,feedback),"supported 920px enlarged Focus retains contained disjoint header/transport, scrollable facts and Save, TAB and bottom feedback");
    ck(smaller->isShowing()&&reset->isShowing()&&practice.tabView().getLocalBounds().contains(smaller->getBounds())&&practice.tabView().getLocalBounds().contains(larger->getBounds())&&practice.tabView().getLocalBounds().contains(reset->getBounds()),"Zoom and Reset controls remain visible and contained at maximum zoom");picture(width,"max");
    for(int i=0;i<5;++i)click(*smaller);
    ck(practice.tabView().zoom()==0.75&&!smaller->isEnabled()&&larger->isEnabled()&&heading->getFont().getHeight()<baseHeading&&factLabel->getFont().getHeight()<baseFacts,"Zoom - reaches bounded minimum and shrinks essential Focus text");picture(width,"min");click(*larger);
    ck(practice.tabView().zoom()==1.0&&heading->getFont().getHeight()==baseHeading&&factLabel->getFont().getHeight()==baseFacts,"Zoom + reverses minimum scale to original fonts");
    smaller->grabKeyboardFocus();key(@"\t",48,true);key(@"\t",48,false);ck(juce::Component::getCurrentlyFocusedComponent()==larger,"constructed AppKit Tab reaches Zoom + from Zoom - in the existing TAB control row");
   }
   click(*larger);practice.setFocusMode(false);practice.setFocusMode(true);
   ck(practice.tabView().zoom()==1.25&&heading->getFont().getHeight()>18.0f&&practice.lessonAdmission()==admitted&&practice.captureSessionId()==session.owner,"Focus exit/reentry retains enlarged text scale and exact source/Session");
   click(*smaller);ck(practice.tabView().zoom()==1.0,"Zoom - returns to baseline after Focus reentry");
  }
  ck(practice.captureSession()->phase()==capture::SessionPhase::Idle&&!practice.captureSession()->startTaken()&&practice.coordinator().completedCycles()==0,"keyboard browsing and refused controls create no active Attempt");
  practice.grabKeyboardFocus();ck(practice.hasKeyboardFocus(false),"Practice command focus restored after read-only/native navigation checks");tap(@"f",3);ck(!practice.focusMode()&&invoked==5&&practice.findChildWithID("practice-back")->getExplicitFocusOrder()==1&&practice.findChildWithID("practice-focus")->getExplicitFocusOrder()==4&&practice.findChildWithID("practice-clean")->getExplicitFocusOrder()==14,"Exiting Focus restores the original non-Focus keyboard order");
  const auto after=store.snapshot(storage::newUuid()).get();ck(after.status==storage::Status::Confirmed&&storage::canonical(after.data)==storage::canonical(before.data),"authoritative Store remains byte-identical after Focus browsing");
  ck(practice.requestClose()&&practice.outputStatus().lifecycle.state==output::State::Closed,"Focus route closes without native output");
  observations.flush();checks.flush();ck(observations.good()&&checks.good(),"focused evidence files flushed");
  std::ofstream(root/"admitted-focus-summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<n<<",\"source\":\"fg:item:000002/fg:variant:000006\",\"session\":\""<<session.owner<<"\",\"attemptCreated\":false,\"syntheticKeyEvents\":true,\"appWiredHomeLesson\":false,\"foregroundUserKeyDelivery\":\"NOT RUN\"}\n";
  std::cout<<"PASS "<<n<<(nativeNavigation?" native Focus navigation":textScaling?" Focus text-scaling":compactTab?" compact Focus TAB":" admitted-source Focus component")<<" checks; Home/Lesson app wiring and hardware key NOT RUN\n";return 0;
 }
 if(argc!=2||std::filesystem::exists(argv[1]))throw std::runtime_error("New evidence directory required");std::filesystem::create_directories(argv[1]);const std::filesystem::path root=argv[1];std::ofstream log(root/"checks.tsv"),events(root/"keys.csv");
 const auto ck=[&](bool b,const std::string& s){++n;log<<s<<'\t'<<(b?"PASS":"FAIL")<<'\n';if(!b)throw std::runtime_error(s);};
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];juce::ScopedJuceInitialiser_GUI gui;
 desktop::PracticeView v;v.setSize(920,680);v.addToDesktop(juce::ComponentPeer::windowHasTitleBar);v.setVisible(true);v.grabKeyboardFocus();
 NSView* native=(__bridge NSView*)v.getPeer()->getNativeHandle();[native.window makeKeyAndOrderFront:nil];
 int observations=0,invocations=0;events<<"timestamp,key,hardware,down,repeat,modified,matched,visible,consumed,invoked\n";
 v.onKeyObservation=[&](const desktop::PracticeKeyObservation& o){++observations;invocations+=o.invoked;events<<o.timestamp<<','<<o.key<<','<<o.hardwareKey<<','<<o.down<<','<<o.repeat<<','<<o.modified<<','<<o.matchedWindow<<','<<o.visible<<','<<o.consumed<<','<<o.invoked<<'\n';};
 const auto key=[&](NSString* text,unsigned short code,bool down,bool repeat=false,NSEventModifierFlags flags=0){
  auto* e=[NSEvent keyEventWithType:down?NSEventTypeKeyDown:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:flags timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:text charactersIgnoringModifiers:text isARepeat:repeat keyCode:code];[NSApp sendEvent:e];
 };
 const auto tap=[&](NSString* text,unsigned short code){key(text,code,true);key(text,code,false);};
 auto& tab=v.tabView();const auto source=tab.document();tab.selectEvent("held-E");tab.setPlayback({"full-rest"},"Synthetic component pose; no audio executed.");tab.setZoom(2.0);v.showTab(true);tab.restoreScrollPosition({999,999});const auto before=tab.scrollPosition();
 const auto selected=tab.selectedEvent(),detail=tab.visibleDetail();
 const auto picture=[&](const std::string& name){auto image=v.createComponentSnapshot(v.getLocalBounds());juce::FileOutputStream out(juce::File((root/(name+".png")).string()));juce::PNGImageFormat png;ck(out.openedOk()&&png.writeImageToStream(image,out),"PNG "+name);out.flush();ck(!out.getStatus().failed(),"PNG flush "+name);};
 tap(@"f",3);ck(observations==2&&invocations==1&&v.focusMode(),"AppKit local monitor actual Focus route");
 ck(tab.document()==source&&tab.selectedEvent()==selected&&tab.visibleDetail()==detail&&tab.playingEvents()==std::vector<std::string>{"full-rest"},"Focus preserves source/selection/live distinction");
 ck(tab.zoom()==2.0,"Focus preserves zoom");
 key(@" ",49,true);ck(invocations==2&&!v.coordinator().pending(),"Space refuses absent profile without history");const auto feedback=v.commandFeedback();
 key(@" ",49,true,true);ck(invocations==2&&v.commandFeedback()==feedback,"native held repeat not invoked");
 auto* flags=[NSEvent keyEventWithType:NSEventTypeFlagsChanged location:NSZeroPoint modifierFlags:NSEventModifierFlagShift timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:@"" charactersIgnoringModifiers:@"" isARepeat:NO keyCode:56];[NSApp sendEvent:flags];ck(juce::ModifierKeys::getCurrentModifiers().isShiftDown(),"constructed flags update actual JUCE modifier state");
 tab.showDetail(true);juce::TextEditor* intended=nullptr;for(auto* c:tab.getChildren())if(auto* editor=dynamic_cast<juce::TextEditor*>(c)){intended=editor;editor->grabKeyboardFocus();}
 ck(intended&&intended->isShowing()&&intended->hasKeyboardFocus(false),"actual readonly descendant keyboard focus");
 key(@" ",49,true,true);ck(invocations==2,"modifier and descendant focus change cannot rearm repeat");
 key(@" ",49,false);key(@" ",49,true);ck(invocations==2,"TextEditor focus blocks a fresh Practice command");key(@" ",49,false);
 v.grabKeyboardFocus();ck(v.hasKeyboardFocus(false),"Practice focus restored after TextEditor input focus");
 key(@" ",49,true);ck(invocations==3,"exact up/fresh down rearms with Practice focus");key(@" ",49,false);
 const auto prior=invocations;key(@"c",8,true,false,NSEventModifierFlagCommand);key(@"c",8,false,false,NSEventModifierFlagCommand);ck(invocations==prior,"Command+C not captured");
 for(auto entry:{std::pair{ @"c",(unsigned short)8},std::pair{@"s",(unsigned short)1},std::pair{@"a",(unsigned short)0},std::pair{@"r",(unsigned short)15}}){tap(entry.first,entry.second);ck(!v.coordinator().pending()&&!v.commandFeedback().empty(),"invalid result command visible refusal/no owner");}
 tab.showDetail(false);tap(@"f",3);ck(!v.focusMode()&&v.tabVisible()&&tab.scrollPosition()==before,"exit restores prior TAB scroll and mode");
 v.showTab(false);tap(@"f",3);tap(@"f",3);ck(!v.focusMode()&&!v.tabVisible(),"return restores prior results mode");
 for(auto size:{std::pair{920,680},std::pair{1280,800}}){v.setSize(size.first,size.second);v.setFocusMode(true);tab.setZoom(1.0);tab.showDetail(false);picture("focus-"+std::to_string(size.first));tab.showSource();tab.showDetail(true);picture("source-"+std::to_string(size.first));tab.showDetail(false);v.performCommand(desktop::PracticeCommand::Again);picture("again-refused-"+std::to_string(size.first));
  {const juce::Label* heading=nullptr;const juce::Label* tempoFacts=nullptr;for(auto* child:v.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child)){if(label->isVisible()&&label->getText().startsWith("Focus |"))heading=label;if(label->getTitle()=="Practice tempo, loop and confirmed session facts")tempoFacts=label;}
   auto* state=dynamic_cast<juce::Label*>(v.findChildWithID("practice-status"));
   auto* emptyMarker=v.findChildWithID("practice-empty-source-state");
   const juce::Label* feedback=nullptr;for(auto* child:v.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getTitle()=="Practice command feedback")feedback=label;
   ck(heading&&tempoFacts&&state&&emptyMarker&&!emptyMarker->isVisible()&&heading->getText()=="Focus | Synthetic practice sample"&&supportedFocusRegions(v,heading,tempoFacts,feedback)&&state->getText().contains("No admitted case selected")&&state->getTooltip().contains("Practice opens from Learn")&&v.saveStatusView().detailsView().isReadOnly()&&v.saveStatusView().detailsView().getText().contains("No admitted case selected"),std::to_string(size.first)+"px synthetic Focus hides the empty-state overlay, contains disjoint supported regions and retains complete source state in read-only Save details/tooltip");}
  v.performCommand(desktop::PracticeCommand::Clean);ck(v.commandFeedback()=="Clean requires an ended result in review. Sealed assessments cannot change; finish saving, then use Again.","Clean refusal explains review and sealed-result boundary");picture("Clean-refused-"+std::to_string(size.first));
  ck(v.focusFacts().find("120 BPM (quarter-note beat)")!=std::string::npos&&v.focusFacts().find("4/4")!=std::string::npos&&v.focusFacts().find("Target: 2")!=std::string::npos,"exact beat/meter/loop target facts");
  ck(v.focusFacts().find("Confirmed active: 0.000 s")!=std::string::npos&&!v.coordinator().pending(),"browsing or key repeats no practice time");v.setFocusMode(false);
 }
 ck(v.requestClose()&&v.outputStatus().lifecycle.state==output::State::Closed,"no audio connect/profile accessed");events.flush();log.flush();ck(events.good()&&log.good(),"retained files flush");
 std::cout<<"PASS "<<n<<" Focus/AppKit component checks; native input events constructed, audio NOT RUN\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<n<<": "<<e.what()<<'\n';return 1;}}
