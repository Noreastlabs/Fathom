// Real Home/setup/lesson/Store controls; only device I/O leaves are synthetic.
#import <AppKit/AppKit.h>
#define main retained_settings_campaign_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include "desktop/GuidedSessionView.cpp"
namespace {
juce::TextEditor& edit(juce::Component& v,const std::string& title){for(auto* child:v.getChildren())if(auto* e=dynamic_cast<juce::TextEditor*>(child);e&&e->getTitle().toStdString()==title)return *e;throw std::runtime_error("Missing editor "+title);}
juce::ComboBox& select(juce::Component& v,const std::string& id){auto* c=dynamic_cast<juce::ComboBox*>(v.findChildWithID(id));if(!c)throw std::runtime_error("Missing combo "+id);return *c;}
void choose(desktop::LessonView& view,const std::string& item,const std::string& variant){const auto& lessons=view.catalog()->lessons();auto l=std::find_if(lessons.begin(),lessons.end(),[&](const auto& x){return x.id==item;});if(l==lessons.end())throw std::runtime_error("Missing fixture item");select(view,"lessons").setSelectedItemIndex(static_cast<int>(l-lessons.begin()),juce::sendNotificationSync);auto v=std::find_if(l->variants.begin(),l->variants.end(),[&](const auto& x){return x.id==variant;});if(v==l->variants.end())throw std::runtime_error("Missing fixture variant");select(view,"variants").setSelectedItemIndex(static_cast<int>(v-l->variants.begin()),juce::sendNotificationSync);}
std::string text(juce::Component& c,const char* id){if(auto* label=dynamic_cast<juce::Label*>(c.findChildWithID(id)))return label->getText().toStdString();if(auto* editor=dynamic_cast<juce::TextEditor*>(c.findChildWithID(id)))return editor->getText().toStdString();throw std::runtime_error("Missing text component");}
void load(Harness& h,const std::filesystem::path& bundle){if(!A::lessons(*h.home).load(bundle))throw std::runtime_error("Bundle load");click(*h.home,"Learn");}
void apply(Harness& h,const guitar::Setup& value){h.home->navigate(H::Page::Setup);auto& setup=A::setup(*h.home);for(int i=0;i<6;++i)edit(setup,"String "+std::to_string(6-i)+" open note").setText(guitar::noteName(value.openMidi[static_cast<std::size_t>(i)]),false);edit(setup,"Capo physical fret").setText(std::to_string(value.capo),false);edit(setup,"Physical fret count").setText(std::to_string(value.fretCount),false);click(setup,"Apply setup");h.tick();}
void setupClick(juce::Component& component,const std::string& name){click(component,name=="Setup details"?"Show setup details":name=="Close setup details"?"Hide setup details":name=="Stop"?"Stop & review result":name=="View TAB"?"Show TAB":name=="Read instructions"?"Show instructions":name);}
#define click setupClick
}
int main(int argc,char** argv){int checks{};std::ofstream out;try{
 const bool setupResponsiveOnly=argc==4&&std::string(argv[3])=="--setup-responsive-layout";
 const bool setupAccessibilityCapture=argc==4&&std::string(argv[3])=="--setup-accessibility-capture";
 if((argc!=3&&!setupResponsiveOnly&&!setupAccessibilityCapture)||!std::filesystem::path(argv[1]).is_absolute()||!std::filesystem::path(argv[2]).is_absolute()||std::filesystem::exists(argv[2]))throw std::runtime_error("Absolute bundle/new output required");const std::filesystem::path bundle=argv[1],dir=argv[2];std::filesystem::create_directories(dir);out.open(dir/"checks.tsv");juce::ScopedJuceInitialiser_GUI gui;
 auto ck=[&](bool okay,const std::string& reason){++checks;out<<reason<<'\t'<<(okay?"PASS":"FAIL")<<std::endl;if(!okay)throw std::runtime_error(reason);};
 if(setupAccessibilityCapture){
  [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
  std::ofstream trace(dir/"focus.tsv");
  const auto focusName=[](const juce::Component* item){
   if(!item)return std::string{"<none>"};
   if(const auto* button=dynamic_cast<const juce::Button*>(item))return button->getButtonText().toStdString();
   return item->getTitle().toStdString();
  };
  for(const int width:{640,920}){
   desktop::GuitarSetupView view;view.setSize(width,680);view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);view.setVisible(true);
   auto* native=(__bridge NSView*)view.getPeer()->getNativeHandle();[native.window makeKeyAndOrderFront:nil];
   ck(native&&native.window&&view.isShowing(),"Guitar Setup native peer showing at "+std::to_string(width));
   const auto picture=[&](const std::string& name){
    const auto shot=view.createComponentSnapshot(view.getLocalBounds());
    juce::FileOutputStream file{juce::File((dir/name).string())};juce::PNGImageFormat png;
    ck(file.openedOk()&&png.writeImageToStream(shot,file),"Guitar Setup native snapshot written: "+name);
    file.flush();ck(!file.getStatus().failed(),"Guitar Setup native snapshot flushed: "+name);
   };
   picture("setup-"+std::to_string(width)+"-right.png");
   juce::Label* heading=nullptr;juce::Label* tuning=nullptr;
   for(auto* child:view.getChildren())if(auto* item=dynamic_cast<juce::Label*>(child)){
    if(item->getText().startsWith("Guitar setup"))heading=item;
    if(item->getText().startsWith("Open tuning"))tuning=item;
   }
   ck(heading&&tuning&&view.getLocalBounds().contains(heading->getBounds())&&view.getLocalBounds().contains(tuning->getBounds()),
      "Guitar Setup identity and tuning row contained at "+std::to_string(width));
   if(width==640){
    ck(heading->getText().contains(juce::String::fromUTF8("—")),"Compact Guitar Setup heading renders its UTF-8 separator");
    juce::Image background(juce::Image::RGB,width,680,true);juce::Graphics graphics(background);view.paint(graphics);
    ck(background.getPixelAt(tuning->getX()+4,tuning->getY()+4)!=juce::Colour{0xff6bd5cb},
       "Compact Guitar Setup separator clears the tuning row");
   }
   juce::KeyboardFocusTraverser traverser;const auto order=traverser.getAllComponents(&view);
   trace<<width<<"\tconstructed";for(const auto* item:order)trace<<'\t'<<focusName(item);trace<<'\n';
   ck(!order.empty(),"Guitar Setup constructed focus path exists at "+std::to_string(width));
   ck(order.size()==12&&dynamic_cast<juce::Button*>(order.front())
      &&dynamic_cast<juce::Button*>(order.front())->getButtonText()=="Back"
      &&dynamic_cast<juce::ComboBox*>(order[1])
      &&order[1]->getTitle()=="Tuning preset"
      &&dynamic_cast<juce::Button*>(order.back())
      &&dynamic_cast<juce::Button*>(order.back())->getButtonText()=="Apply setup",
      "Guitar Setup peer focus path spans Back, tuning fields and Apply at "+std::to_string(width));
   if(order.size()>1){
    order.front()->grabKeyboardFocus();const auto* before=juce::Component::getCurrentlyFocusedComponent();
    auto* down=[NSEvent keyEventWithType:NSEventTypeKeyDown location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:@"\t" charactersIgnoringModifiers:@"\t" isARepeat:NO keyCode:48];
    auto* up=[NSEvent keyEventWithType:NSEventTypeKeyUp location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:native.window.windowNumber context:nil characters:@"\t" charactersIgnoringModifiers:@"\t" isARepeat:NO keyCode:48];
    [NSApp sendEvent:down];[NSApp sendEvent:up];const auto* after=juce::Component::getCurrentlyFocusedComponent();
    trace<<width<<"\tAppKit Tab\t"<<focusName(before)<<'\t'<<focusName(after)<<'\n';
    ck(before==order.front()&&after==order[1],"Injected AppKit Tab advances Back to tuning preset at "+std::to_string(width));
   }
   for(auto* child:view.getChildren())if(auto* combo=dynamic_cast<juce::ComboBox*>(child);combo&&combo->getTitle()=="Fretboard orientation")combo->setSelectedId(2,juce::sendNotificationSync);
   for(auto* child:view.getChildren())if(auto* button=dynamic_cast<juce::TextButton*>(child);button&&button->getButtonText()=="Apply setup")button->onClick();
   ck(view.currentSetup().handedness==guitar::Handedness::Left,"Guitar Setup applies left-handed orientation at "+std::to_string(width));
   picture("setup-"+std::to_string(width)+"-left.png");
   view.removeFromDesktop();
  }
  trace.flush();ck(trace.good(),"Guitar Setup native focus trace flushed");
  std::ofstream(dir/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"injectedAppKitEvents\":true,\"nativeAudioRun\":false}\n";
  out.close();std::cout<<"PASS "<<checks<<" Guitar Setup accessibility capture checks\n";return 0;
 }
 if(setupResponsiveOnly){
  desktop::GuitarSetupView compact;compact.setSize(640,680);compact.setVisible(true);compact.resized();const auto bounds=compact.getLocalBounds();
  for(auto* child:compact.getChildren())if(child->isVisible())ck(child->getWidth()>0&&child->getHeight()>0&&bounds.contains(child->getBounds()),"compact Guitar Setup child is positive and contained");
  juce::Label* compactHeading=nullptr;for(auto* child:compact.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText().startsWith("Guitar setup")&&label->getText().contains("Instrument configuration"))compactHeading=label;ck(compactHeading&&compactHeading->isVisible(),"compact Guitar Setup exposes an instrument-configuration heading");
  juce::Button* applyButton=nullptr;juce::Button* backButton=nullptr;for(auto* child:compact.getChildren())if(auto* button=dynamic_cast<juce::Button*>(child)){if(button->getButtonText()=="Apply setup")applyButton=button;if(button->getButtonText()=="Back")backButton=button;}
  ck(applyButton&&backButton,"compact Guitar Setup Apply and Back controls are present");ck(applyButton&&backButton&&!applyButton->getBounds().intersects(backButton->getBounds()),"compact Guitar Setup Apply and Back do not overlap");
  const std::string exact="Back is unavailable from Guitar setup until the existing Home navigation is connected. The current setup draft remains here; no setup change or curriculum activity was applied.";if(backButton)backButton->onClick();bool exactStatus=false;for(auto* child:compact.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))exactStatus=exactStatus||label->getText().toStdString()==exact;ck(exactStatus,"compact Guitar Setup Back preserves exact disconnected recovery");
  desktop::GuitarSetupView standard;standard.setSize(920,680);standard.setVisible(true);standard.resized();juce::Label* standardHeading=nullptr;juce::Button* standardBack=nullptr;for(auto* child:standard.getChildren()){if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText()=="Guitar setup")standardHeading=label;if(auto* button=dynamic_cast<juce::Button*>(child);button&&button->getButtonText()=="Back")standardBack=button;}ck(standardHeading&&standardHeading->isVisible()&&standardBack&&standardBack->getBounds().getX()==802&&standardBack->getBounds().getY()==28,"standard Guitar Setup heading and geometry remain unchanged at 920x680");
  out.close();std::cout<<"PASS "<<checks<<" compact Guitar Setup surface checks\n";return 0;
 }
 {
  desktop::GuitarSetupView detached;detached.setSize(920,680);detached.setVisible(true);
  auto* entryStatus=dynamic_cast<juce::Label*>(detached.getChildren().size()>0?detached.findChildWithID("setup-status"):nullptr);
  if(!entryStatus)for(auto* child:detached.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText().toStdString().find("No setup changes applied in this app session.")!=std::string::npos){entryStatus=label;break;}
  ck(entryStatus&&entryStatus->getText().toStdString()=="No setup changes applied in this app session. Choose a preset or edit fields, then Apply setup."&&entryStatus->getTitle().toStdString()=="Guitar setup session state and next action.","fresh Guitar Setup exposes the exact entry-state next action without changing setup");
  juce::Button* back=nullptr;for(auto* child:detached.getChildren())if(auto* candidate=dynamic_cast<juce::Button*>(child);candidate&&candidate->getButtonText()=="Back")back=candidate;
  const std::string exact="Back is unavailable from Guitar setup until the existing Home navigation is connected. The current setup draft remains here; no setup change or curriculum activity was applied.";
  ck(back!=nullptr,"disconnected Guitar Setup Back control is present and actionable");back->onClick();
  bool actionPresentation=true;int styledActions=0;for(auto* child:detached.getChildren())if(auto* button=dynamic_cast<juce::TextButton*>(child)){const auto label=button->getButtonText().toStdString();if(label=="Apply setup"||label=="Back"){actionPresentation=actionPresentation&&button->findColour(juce::TextButton::buttonColourId)==juce::Colour{0xff6bd5cb}&&button->findColour(juce::TextButton::textColourOffId)==juce::Colour{0xff10212c}&&button->findColour(juce::TextButton::textColourOnId)==juce::Colour{0xff10212c};++styledActions;}}
  ck(actionPresentation&&styledActions==2,"Guitar Setup action buttons use the primary presentation while preserving the existing contract");
  bool exactStatus=false;for(auto* child:detached.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))exactStatus=exactStatus||label->getText().toStdString()==exact;
  ck(exactStatus,"disconnected Guitar Setup Back exposes exact recovery guidance without callback");
  int backCalls{};detached.onBack=[&]{++backCalls;};back->onClick();ck(backCalls==1,"connected Guitar Setup Back callback is delivered exactly once");
 }
 {Harness h(dir,"source-guidance");load(h,bundle);auto& v=A::lessons(*h.home);for(int level:{3,12}){const auto item=level==3?"fg:item:000002":"fg:item:000003",variant=level==3?"fg:variant:000006":"fg:variant:000029";choose(v,item,variant);const auto model=v.catalog()->variant(item,variant).model;const auto source=model->source().preservedRecordJson;
  const std::array<int,5> expected=level==3?std::array<int,5>{0,4,21,20,4}:std::array<int,5>{0,5,17,12,5};
  for(int kind=0;kind<5;++kind){guitar::Setup current;if(kind==1)current.openMidi=guitar::tuning(guitar::Preset::DropD);if(kind==2)current.capo=2;if(kind==3)current.fretCount=4;if(kind==4)current.openMidi[0]=127;apply(h,current);ck(desktop::declaredSetupValue(A::setup(*h.home).currentSetup())==desktop::declaredSetupValue(current),"actual setup Apply "+std::to_string(level)+"/"+std::to_string(kind));h.home->navigate(H::Page::Learn);const auto comparison=guitar::compare(*model,current);ck(comparison.warnings.size()==static_cast<std::size_t>(expected[static_cast<std::size_t>(kind)])&&comparison.accessAllowed&&comparison.referenceUsesAuthoredSetup,"source-derived warning count/access "+std::to_string(level)+"/"+std::to_string(kind));const auto notice=text(v,"setup-summary");ck(notice.find(kind==0?"Declared tuning/capo match":"Declared setup differs")!=std::string::npos&&notice.find("capo 0")!=std::string::npos,"visible authored/declared distinction "+std::to_string(level)+"/"+std::to_string(kind));click(v,"Setup details");const auto detail=text(v,"setup-details");for(const auto& w:comparison.warnings)ck(detail.find(w.message)!=std::string::npos&&(w.eventId.empty()||detail.find(w.eventId)!=std::string::npos),"exact warning detail "+std::to_string(level)+"/"+w.code+"/"+w.eventId);ck(model->source().preservedRecordJson==source&&button(v,"Practice selected case").isEnabled(),"source unchanged and no hard lock");if(kind==1||kind==2)h.image("L"+std::to_string(level)+"-setup"+std::to_string(kind));click(v,"Close setup details");}
 }
  for(const auto& l:v.catalog()->lessons())if(l.variants.front().model->source().instrument.openMidi.empty()){choose(v,l.id,l.variants.front().id);ck(text(v,"setup-summary").find("Authored setup unspecified")!=std::string::npos,"missing requirements not Standard match "+l.id);click(v,"Setup details");ck(text(v,"setup-details").find("not assessed")!=std::string::npos,"unspecified position claim "+l.id);click(v,"Close setup details");}
  choose(v,"fg:item:000002","fg:variant:000006");
  auto unusual=v.catalog()->variant("fg:item:000002","fg:variant:000006").model->source();unusual.syntheticFixture=true;unusual.proposalExample=false;unusual.itemId="synthetic:setup:seven-string";unusual.instrument.openMidi.push_back(67);const auto validated=music::validate(unusual);
  ck(bool(validated.model),"synthetic positioned seven-string model validates");const auto unsupported=desktop::lessonSetupNotice(*validated.model,guitar::Setup{});
  ck(unsupported.details.find("Position compatibility was not assessed")!=std::string::npos&&unsupported.details.find("no positioned notes")==std::string::npos,"unsupported instrument does not erase positioned notes");
  click(v,"Setup details");click(v,"View TAB");ck(!v.findChildWithID("setup-details")->isVisible()&&button(v,"Show instructions").isEnabled(),"Show TAB closes setup overlay");
  ck(button(v,"Details").isEnabled()&&!v.findChildWithID("setup-button")->isVisible()&&dynamic_cast<juce::Label*>(v.findChildWithID("summary"))->getTooltip().contains(juce::String::fromUTF8(text(v,"setup-details").c_str())),"TAB exposes complete authored setup through Details while secondary setup controls are hidden");
  click(v,"Read instructions");click(v,"Setup details");click(v,"View TAB");click(v,"Read instructions");ck(!v.findChildWithID("setup-details")->isVisible()&&button(v,"Show TAB").isEnabled(),"Show instructions closes setup overlay");
  h.home->navigate(H::Page::Setup);const auto old=desktop::declaredSetupValue(A::setup(*h.home).currentSetup());edit(A::setup(*h.home),"String 6 open note").setText("E2junk",false);click(A::setup(*h.home),"Apply setup");ck(desktop::declaredSetupValue(A::setup(*h.home).currentSetup())==old,"invalid draft retains actual declaration");ck(h.finals()==0,"setup/reading creates no practice");
 }
 {Harness h(dir,"pending-preference");guitar::Setup other;other.capo=2;h.mode=4;ck(A::metronome(*h.home).savePreset("Held preference"),"inactive pending Metronome save queued");h.wait([&]{return h.entered.load();},"preference barrier");apply(h,other);ck(A::setup(*h.home).currentSetup().capo==0,"inactive preference blocks actual Apply callback");h.release=true;h.wait([&]{return A::metronome(*h.home).preferencesReady();},"preference settles");apply(h,other);ck(A::setup(*h.home).currentSetup().capo==2,"resolved preference releases Apply");}
 {Harness h(dir,"original-snapshot");load(h,bundle);auto& v=A::lessons(*h.home);choose(v,"fg:item:000002","fg:variant:000006");click(v,"Practice selected case");const auto source=h.practice().lessonAdmission()->sourceBinding();guitar::Setup current;current.openMidi=guitar::tuning(guitar::Preset::DropD);apply(h,current);h.home->navigate(H::Page::Practice);ck(text(h.practice(),"setup-summary").find("Declared setup differs")!=std::string::npos,"setup changed after selection refreshes before Start");activate(h.practice().saveStatusView().detailsButton());ck(h.practice().saveStatusView().detailsVisible(),"actual Save details opens");click(h.practice(),"Setup details");ck(!h.practice().saveStatusView().detailsVisible()&&h.practice().findChildWithID("setup-details")->isVisible(),"Setup details replaces Save details");activate(h.practice().saveStatusView().detailsButton());ck(h.practice().saveStatusView().detailsVisible()&&!h.practice().findChildWithID("setup-details")->isVisible(),"Save details replaces Setup details");click(h.practice(),"Setup details");h.image("practice-details");click(h.practice(),"Close setup details");h.practice().setFocusMode(true);h.image("focus-warning");
  click(h.practice(),"Audio settings");h.tick();click(A::settings(*h.home),"Connect audio");h.tick();click(A::settings(*h.home),"Enable audio");h.blocks(1);click(A::settings(*h.home),"Back to Practice");
  h.mode=4;click(h.practice(),"Start selected case");h.wait([&]{return h.entered.load();},"allocation barrier");guitar::Setup next=current;next.capo=2;apply(h,next);ck(A::setup(*h.home).currentSetup().capo==0,"allocation-pending actual Apply refuses");h.release=true;h.home->navigate(H::Page::Practice);h.wait([&]{return h.practice().captureSession()->startTaken();},"original allocated");h.blocks(40);const auto context=h.practice().captureSession()->binding().context;const auto& config=context.find("configuration")->object();ck(config.at("declared_instrument_setup")==desktop::declaredSetupValue(current)&&config.at("source_binding").string()==source,"Start snapshots actual post-selection declaration outside source binding");ck(h.practice().lessonAdmission()->model()->source().instrument.openMidi[0]==40,"Drop D declaration never retunes authored low E");
  click(h.practice(),"Stop");h.blocks(2);h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"Review");apply(h,next);ck(A::setup(*h.home).currentSetup().capo==0&&h.practice().captureSession()->binding().context==context,"Review Apply retains original context");h.home->navigate(H::Page::Practice);h.mode=2;click(h.practice(),"Save result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Failed;},"lost receipt");const auto bytes=h.practice().captureSession()->original()->bytes;apply(h,next);ck(A::setup(*h.home).currentSetup().capo==0&&h.practice().captureSession()->original()->bytes==bytes,"uncertain Save Apply retains immutable original");h.home->navigate(H::Page::Practice);click(h.practice(),"Retry original");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"reconcile");h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"resolved original");apply(h,next);ck(A::setup(*h.home).currentSetup().capo==2&&h.practice().captureSession()->original()->bytes==bytes,"post-save Apply affects next Start only");h.home->navigate(H::Page::Practice);click(h.practice(),"Again");h.blocks(1);ck(h.practice().captureSession()->phase()==capture::SessionPhase::Idle&&h.finals()==1,"Again no new history from setup");capture_fixture::write(h.dir/"original.json",bytes);h.image("again-new-declaration");
 }
 ck(nativeOpens==0&&maxClaims<=1,"software device only; one active owner");std::ofstream(dir/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"nativeOpens\":0}\n";std::cout<<"PASS "<<checks<<" setup integration checks\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}
}
