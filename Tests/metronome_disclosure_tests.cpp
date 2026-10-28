#include "desktop/MetronomeView.hpp"
#include "content/Canonical.hpp"
#include "read_only_text_peer_checks.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <algorithm>

using namespace fathom;
namespace fathom::desktop {
struct MetronomeViewTestAccess {
 static void halt(MetronomeView& view){view.stopTimer();}
 static void advanced(MetronomeView& view,bool value){view.advancedControls_.setToggleState(value,juce::dontSendNotification);view.advancedControls_.onClick();}
 static void details(MetronomeView& view){view.detailsButton_.onClick();}
 static juce::Viewport& viewport(MetronomeView& view){return view.advancedViewport_;}
 static juce::Component& optional(MetronomeView& view){return view.advancedContent_;}
 static juce::TextEditor& instructions(MetronomeView& view){return view.instructions_;}
 static juce::TextEditor& detailText(MetronomeView& view){return view.details_;}
 static juce::Label& heading(MetronomeView& view){return view.title_;}
 static juce::TextEditor& bpm(MetronomeView& view){return view.tempo_;}
 static juce::TextEditor& draftStep(MetronomeView& view){return view.step_;}
 static juce::ComboBox& beatUnit(MetronomeView& view){return view.unit_;}
 static juce::Rectangle<int> bar(MetronomeView& view){return view.progressBarBounds_;}
 static void progress(MetronomeView& view,std::uint64_t cursor){view.shown_.cursorFrames=cursor;view.shown_.barFrames=100;view.shown_.completedCycles=2;view.refresh();}
 static void counter(MetronomeView& view,std::uint64_t bars){view.shown_.completedCycles=bars;view.refresh();}
 static void recovery(MetronomeView& view){
  view.owner_.id[0]=42;view.owner_.epoch=8;view.owner_.generation=3;
  view.pendingOperation_="synthetic-original-settings";view.pendingBytes_="synthetic-immutable-bytes";
  view.expectedRevision_=7;view.revision_=6;view.prefState_=MetronomeView::PrefState::Failed;
  view.preferenceMessage_="Synthetic failed save; exact original proposal retained. This pose does not create a Store or native owner.";
  view.onReopenStore=[]{return false;};view.refresh();
 }
 static std::string identity(const MetronomeView& view){return std::to_string(view.owner_.id[0])+":"+std::to_string(view.owner_.epoch)+":"+std::to_string(view.owner_.generation)+":"+view.pendingOperation_+":"+view.pendingBytes_+":"+std::to_string(view.expectedRevision_)+":"+std::to_string(view.revision_)+":"+std::to_string(view.started_)+":"+std::to_string(view.stopRequested_)+":"+std::to_string(view.resolveRequested_);}
 static void clearSynthetic(MetronomeView& view){view.owner_={};view.pendingOperation_.clear();view.pendingBytes_.clear();view.expectedRevision_=0;view.revision_=0;view.prefState_=MetronomeView::PrefState::Detached;view.preferenceMessage_="No local profile is open.";view.onReopenStore={};view.shown_={};view.refresh();}
};
}
namespace {
int checks{},failures{};
std::ofstream trace;
void check(bool value,const std::string& message){++checks;if(!value)++failures;trace<<(value?"PASS\t":"FAIL\t")<<message<<'\n';}
juce::Component* find(juce::Component& root,const juce::String& id){
 for(auto* child:root.getChildren()){if(child->getComponentID()==id||child->getTitle()==id)return child;if(auto* button=dynamic_cast<juce::Button*>(child);button&&button->getButtonText()==id)return child;if(auto* result=find(*child,id))return result;}return nullptr;
}
bool mainBounds(desktop::MetronomeView& view,std::initializer_list<const char*> ids){
 for(const auto* id:ids){auto* child=find(view,id);if(!child||!child->isVisible()||child->getParentComponent()!=&view||child->getBounds().isEmpty()||!view.getLocalBounds().contains(child->getBounds()))return false;}return true;
}
bool disjoint(desktop::MetronomeView& view,std::initializer_list<const char*> ids){
 for(auto left=ids.begin();left!=ids.end();++left)for(auto right=std::next(left);right!=ids.end();++right){auto* a=find(view,*left);auto* b=find(view,*right);if(!a||!b||a->getBounds().intersects(b->getBounds()))return false;}return true;
}
float measuredTextHeight(juce::Label& label){juce::AttributedString text(label.getText());text.setFont(label.getFont());juce::TextLayout layout;layout.createLayout(text,std::max(1,label.getWidth()-8));return layout.getHeight();}
bool textFits(juce::Label& label){return measuredTextHeight(label)<=label.getHeight()-4;}
bool pixelsEqual(const juce::Image& a,const juce::Image& b,juce::Rectangle<int> area){for(int y=area.getY();y<area.getBottom();++y)for(int x=area.getX();x<area.getRight();++x)if(a.getPixelAt(x,y)!=b.getPixelAt(x,y))return false;return true;}
void snapshot(juce::Component& component,const std::filesystem::path& path){juce::FileOutputStream output(juce::File(path.string()));juce::PNGImageFormat png;check(output.openedOk()&&png.writeImageToStream(component.createComponentSnapshot(component.getLocalBounds()),output),"component screenshot written; synthetic pose only");output.flush();}
}
int main(int argc,char** argv){
 if(argc!=2||!std::filesystem::path(argv[1]).is_absolute()||std::filesystem::exists(argv[1])){std::cerr<<"New absolute generated output directory required\n";return 2;}
 const std::filesystem::path directory{argv[1]};std::filesystem::create_directories(directory);trace.open(directory/"checks.tsv");
 juce::ScopedJuceInitialiser_GUI gui;
 using A=desktop::MetronomeViewTestAccess;using Level=desktop::presentation::Level;
 try{
  desktop::MetronomeView view;A::halt(view);view.setSize(921,680);view.setVisible(true);
  check(view.presentationLevel()==Level::Beginner&&!A::viewport(view).isVisible(),"Beginner initially keeps Advanced controls closed");
  check(view.outputStatus().lifecycle.state==output::State::Closed&&!view.soundPending()&&view.audioCanRelease(),"fresh view has Closed output, no activity, and no unresolved sound check");
  A::bpm(view).setText("84");A::draftStep(view).setText("not a number");
  const auto settings=storage::canonical(metronome::encodeSettings(view.settings()));const auto identity=A::identity(view);
  for(auto level:{Level::Beginner,Level::Advanced,Level::Developer}){
   view.setPresentationLevel(level);
   check(storage::canonical(metronome::encodeSettings(view.settings()))==settings&&A::identity(view)==identity&&A::bpm(view).getText()=="84"&&A::draftStep(view).getText()=="not a number","changing presentation preserves applied music, unsubmitted inputs, original owner and save state");
   check(view.outputStatus().lifecycle.state==output::State::Closed&&!view.soundPending()&&!view.preferencesPending(),"changing presentation opens no output, starts no check and submits no preference operation");
   for(const auto size:{std::pair{921,680},std::pair{1400,928},std::pair{1400,680}}){
    view.setSize(size.first,size.second);
    check(mainBounds(view,{"metronome-presentation-level","metronome-advanced-disclosure","metronome-instructions-disclosure","metronome-tempo-bpm","metronome-time-signature","Apply pattern","Audio settings","Start","Pause","Resume","Stop","Finish check","Reset","Output state and next action","Saved settings state and recovery action","metronome-current-pattern","metronome-profile-state"}),"all primary pattern, transport and saved-status controls stay inside supported bounds");
    check(disjoint(view,{"Audio settings","Start","Pause","Resume","Stop","Finish check","Reset"})&&disjoint(view,{"metronome-presentation-level","metronome-advanced-disclosure","metronome-instructions-disclosure"}),"primary controls and disclosure controls do not overlap");
    for(auto* child:view.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->isVisible())check(textFits(*label),"visible primary label has measured wrapping height: "+std::string(desktop::presentation::levelName(level))+" "+std::to_string(size.first)+"x"+std::to_string(size.second)+" ["+label->getText().replaceCharacter('\n',' ').toStdString()+"] measured="+std::to_string(measuredTextHeight(*label))+" available="+std::to_string(label->getHeight()-4)+" width="+std::to_string(label->getWidth()-8));
    A::advanced(view,true);auto& viewport=A::viewport(view);auto& optional=A::optional(view);
    check(viewport.isVisible()&&viewport.getViewedComponent()==&optional&&optional.getHeight()>viewport.getHeight()&&viewport.getTitle().contains("scroll vertically"),"complete advanced settings use named vertical scrolling at supported heights");
    bool reach=true;for(auto* child:optional.getChildren()){
     if(child->getBounds().isEmpty()||!optional.getLocalBounds().contains(child->getBounds()))reach=false;
     if(child->getHeight()<=viewport.getViewHeight()){
      viewport.setViewPosition(0,std::max(0,child->getBottom()-viewport.getViewHeight()));
      if(!viewport.getViewArea().contains(child->getBounds()))reach=false;
     }
    }
    check(reach,"every advanced control and caption is retained within scroll content and can be revealed");
    check(A::instructions(view).isReadOnly()&&A::instructions(view).getText().contains("Space: transport; Esc: stop.")&&A::instructions(view).getText().contains("Stop retains the check; Finish releases it."),"complete original transport instructions remain reachable as read-only text");
    viewport.setViewPosition(0,0);
    snapshot(view,directory/(std::string(desktop::presentation::levelName(level))+"-advanced-"+std::to_string(size.first)+"x"+std::to_string(size.second)+".png"));
    A::advanced(view,false);A::details(view);
    check(!viewport.isVisible()&&A::detailText(view).isVisible()&&A::detailText(view).isReadOnly()&&A::detailText(view).getText().contains("No physical output or performed accuracy inferred."),"all levels retain complete permitted instructions and original no-performance qualification in Details");
    check(mainBounds(view,{"Stop","Finish check","Saved settings state and recovery action"}),"Instructions and Details cannot hide stop, finish or saved-status ownership");
    A::details(view);
   }
  }
  view.setSize(920,680);view.setPresentationLevel(Level::Developer);A::advanced(view,false);A::details(view);
  auto& readingDetails=A::detailText(view);const auto readingText=readingDetails.getText().toStdString();
  check(readingText.find("Current permitted diagnostics")!=std::string::npos,
        "Developer Details retains the complete current permitted diagnostics ending");
  {
   test::ReadingPeerScope peer{view};readingDetails.grabKeyboardFocus();
   test::readingKeys(view,readingDetails,readingText,check);
  }
  check(view.outputStatus().lifecycle.state==output::State::Closed&&!view.soundPending()&&!view.preferencesPending(),
        "Developer Details reading keys preserve closed audio and create no sound check or preference operation");
  A::details(view);
  bool refused=false;try{view.setPresentationLevel(static_cast<Level>(99));}catch(const std::invalid_argument&){refused=true;}
  check(refused&&view.presentationLevel()==Level::Developer&&A::identity(view)==identity,"unsupported presentation level is refused without changing current state");
  view.setSize(921,680);view.setPresentationLevel(Level::Beginner);A::recovery(view);const auto recoveryIdentity=A::identity(view);
  for(auto level:{Level::Beginner,Level::Advanced,Level::Developer}){
   view.setPresentationLevel(level);A::advanced(view,false);
   check(mainBounds(view,{"Inspect saved settings","Retry original saved-settings proposal","Keep inspected stored settings","Reopen the same local profile","Saved settings state and recovery action"}),"recovery remains visible and bounded even when Advanced controls are closed");
   check(disjoint(view,{"Inspect saved settings","Retry original saved-settings proposal","Keep inspected stored settings","Reopen the same local profile"}),"recovery actions occupy separate bounds");
   check(view.preferencesPending()&&!view.audioCanRelease()&&A::identity(view)==recoveryIdentity,"disclosure preserves pending original proposal and blocked release in synthetic recovery pose");
   A::details(view);check(A::detailText(view).getText().contains("synthetic-original-settings")==false&&A::detailText(view).getText().contains("Synthetic failed save"),"Details preserves existing message without adding raw hidden operation identity");A::details(view);
   snapshot(view,directory/(std::string(desktop::presentation::levelName(level))+"-recovery-921x680.png"));
  }
  A::clearSynthetic(view);view.setPresentationLevel(Level::Beginner);
  auto* motion=dynamic_cast<juce::ToggleButton*>(find(view,"metronome-reduce-motion"));check(motion!=nullptr,"Reduce motion remains in primary controls");
  if(motion){
   A::progress(view,25);auto low=view.createComponentSnapshot(view.getLocalBounds());A::progress(view,75);auto high=view.createComponentSnapshot(view.getLocalBounds());
   check(!pixelsEqual(low,high,A::bar(view)),"default bar reflects synthetic callback cursor");motion->setToggleState(true,juce::sendNotificationSync);
   A::progress(view,25);low=view.createComponentSnapshot(view.getLocalBounds());A::progress(view,75);high=view.createComponentSnapshot(view.getLocalBounds());
   check(pixelsEqual(low,high,A::bar(view)),"Reduce motion keeps progress bar still while text is retained");
  }
  A::details(view);auto& details=A::detailText(view);juce::Viewport* detailViewport=nullptr;
  for(auto* child:details.getChildren())if(auto* viewport=dynamic_cast<juce::Viewport*>(child)){detailViewport=viewport;break;}
  check(detailViewport!=nullptr,"read-only Details exposes a vertical text viewport");
  if(detailViewport){details.setHighlightedRegion({4,20});detailViewport->setViewPosition(0,100);const auto position=detailViewport->getViewPosition();const auto selection=details.getHighlightedRegion();A::counter(view,3);check(detailViewport->getViewPosition()==position&&details.getHighlightedRegion()==selection,"a changing synthetic counter preserves instruction reading position and selected text");}
  A::details(view);
  check(view.outputStatus().lifecycle.state==output::State::Closed&&!view.soundPending(),"all disclosure and synthetic copy poses leave actual output Closed without performance or credit");
  // Root owns this finite native component test's foreground. This verifies
  // focus transfer, not listening, physical input or an application campaign.
  view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);view.setVisible(true);
  view.setPresentationLevel(Level::Advanced);A::beatUnit(view).grabKeyboardFocus();
  check(view.getPeer()&&view.isShowing()&&A::beatUnit(view).hasKeyboardFocus(true),"optional beat unit receives native component focus while disclosed");
  view.setPresentationLevel(Level::Beginner);
  check(A::heading(view).hasKeyboardFocus(false)&&!A::viewport(view).isVisible(),"global Beginner moves focus from a hidden optional control to the page heading");
  check(view.outputStatus().lifecycle.state==output::State::Closed&&!view.soundPending()&&!view.preferencesPending(),"native component focus transfer opens no audio and submits no save");
  view.removeFromDesktop();
 }catch(const std::exception& error){++failures;trace<<"EXCEPTION\t"<<error.what()<<'\n';}
 trace.flush();std::ofstream(directory/"checks.json")<<"{\"checks\":"<<checks<<",\"failures\":"<<failures<<",\"native_audio_run\":false,\"store_attached\":false,\"actual_gui_audit\":false,\"physical_listening\":false}\n";
 std::cout<<(failures?"FAIL ":"PASS ")<<checks<<" metronome disclosure component checks\n";return failures?1:0;
}
