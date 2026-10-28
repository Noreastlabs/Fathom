#include "desktop/ReferenceView.hpp"
#import <AppKit/AppKit.h>
#include <filesystem>
#include <fstream>
#include <iostream>
using namespace fathom;
int main(int argc,char**argv){int n=0;try{
 const bool controlOnly=argc==3&&std::string(argv[2])=="--control-contract";const bool statusSurfaceOnly=argc==3&&std::string(argv[2])=="--status-surface";const bool actionKeysOnly=argc==3&&std::string(argv[2])=="--action-keys";
 if((argc!=2&&!controlOnly&&!statusSurfaceOnly&&!actionKeysOnly)||std::filesystem::exists(argv[1]))throw std::runtime_error("New evidence directory required");std::filesystem::create_directories(argv[1]);const std::filesystem::path dir=argv[1];std::ofstream log(dir/"checks.tsv"),poses(dir/"poses.tsv");
 const auto ck=[&](bool b,const std::string& s){++n;log<<s<<'\t'<<(b?"PASS":"FAIL")<<'\n';if(!b)throw std::runtime_error(s);};
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];juce::ScopedJuceInitialiser_GUI gui;
 if(actionKeysOnly){
  std::ofstream trace(dir/"action-keys.tsv");trace<<"width\taction\tkey\taudio_handoffs\tdetails_visible\toutput_state\n";
  for(const int width:{640,920}){
   desktop::ReferenceView reference;reference.setSize(width,680);reference.addToDesktop(juce::ComponentPeer::windowHasTitleBar);reference.setVisible(true);
   auto* peer=reference.getPeer();auto* audio=dynamic_cast<juce::TextButton*>(reference.findChildWithID("reference-audio-settings"));
   auto& tone=reference.toneStatusView();auto* details=dynamic_cast<juce::TextButton*>(tone.findChildWithID("reference-tone-details"));
   ck(peer&&reference.isShowing()&&audio&&details,"Reference visible peer and action controls at "+std::to_string(width));
   ck(audio->isShowing()&&audio->isEnabled()&&details->isShowing()&&details->isEnabled(),"Reference Audio and Tone details are visible enabled controls at "+std::to_string(width));
   const auto pitch=reference.displayedPitch();int handoffs=0;reference.onAudioSettings=[&]{++handoffs;};
   audio->grabKeyboardFocus();ck(juce::Component::getCurrentlyFocusedComponent()==audio,"Reference Audio settings receives focus at "+std::to_string(width));
   ck(peer->handleKeyPress(juce::KeyPress{juce::KeyPress::spaceKey}),"Reference focused Audio settings consumes Space at "+std::to_string(width));
   ck(handoffs==1&&reference.outputSnapshot().state==output::State::Closed,"Reference Audio handoff occurs once with output Closed at "+std::to_string(width));
   trace<<width<<"\tAudio settings\tSpace\t"<<handoffs<<"\t0\tClosed\n";
   details->grabKeyboardFocus();ck(juce::Component::getCurrentlyFocusedComponent()==details,"Reference Tone details receives focus at "+std::to_string(width));
   ck(peer->handleKeyPress(juce::KeyPress{juce::KeyPress::returnKey}),"Reference focused Tone details consumes Return at "+std::to_string(width));
   const auto settled=[NSDate dateWithTimeIntervalSinceNow:0.2];while([settled timeIntervalSinceNow]>0){CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);if(auto* event=[NSApp nextEventMatchingMask:NSEventMaskAny untilDate:[NSDate dateWithTimeIntervalSinceNow:0.001] inMode:NSDefaultRunLoopMode dequeue:YES])[NSApp sendEvent:event];}
   ck(tone.detailsVisible()&&tone.detailsView().isVisible()&&tone.detailsView().isReadOnly(),"Reference Tone details Return opens read-only disclosure at "+std::to_string(width));
   ck(reference.displayedPitch()==pitch&&reference.outputSnapshot().state==output::State::Closed&&handoffs==1,"Reference action keys preserve pitch and closed output at "+std::to_string(width));
   trace<<width<<"\tTone details\tReturn\t"<<handoffs<<"\t1\tClosed\n";
   auto image=reference.createComponentSnapshot(reference.getLocalBounds());juce::FileOutputStream file{juce::File((dir/("reference-action-"+std::to_string(width)+".png")).string())};juce::PNGImageFormat png;
   ck(file.openedOk()&&png.writeImageToStream(image,file),"Reference action screenshot at "+std::to_string(width));
   reference.removeFromDesktop();
  }
  trace.flush();log.flush();ck(trace.good()&&log.good(),"Reference action evidence flushed");
  std::ofstream(dir/"summary.json")<<"{\"checks\":"<<n<<",\"status\":\"PASS\",\"nativeAudioRun\":false,\"physicalKeyboard\":false}\n";
  std::cout<<"PASS "<<n<<" Reference action keyboard checks\n";return 0;
 }
 desktop::ReferenceView v;v.setSize(920,680);v.addToDesktop(juce::ComponentPeer::windowHasTitleBar);v.setVisible(true);auto& status=v.toneStatusView();
 if(statusSurfaceOnly){
  auto* idle=dynamic_cast<juce::Label*>(v.findChildWithID("reference-idle-state"));
  ck(idle&&idle->isVisible()&&idle->getText().toStdString()=="Reference output is closed; no tone is playing."&&idle->getTitle().toStdString()=="Reference idle-state marker.","Reference exposes the exact closed-output idle marker");
  desktop::ReferenceView compact;compact.setSize(640,680);compact.setVisible(true);compact.resized();auto* compactIdle=compact.findChildWithID("reference-idle-state");auto* compactAudio=compact.findChildWithID("reference-audio-settings");
  ck(compactIdle&&compactIdle->isVisible()&&compact.getLocalBounds().contains(compactIdle->getBounds())&&compactAudio&&compactIdle->getBottom()<=compactAudio->getY(),"compact Reference keeps the idle marker contained above the lower action row");
  juce::Label* description=nullptr;for(auto* child:v.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))if(label->getText().toStdString().find("Use Audio settings for speakers")!=std::string::npos)description=label;
  ck(description&&description->getTitle().toStdString()=="Read-only Reference: shared Audio settings, three-second tones and no practice recording.","Reference explanation exposes the stable shared-Audio and no-recording title");
  ck(description&&description->getText().toStdString().find("These shared settings apply across the other activities;")!=std::string::npos&&description->getText().toStdString().find("Back returns to Home after the reference output is idle.")!=std::string::npos&&description->getText().toStdString().find("Each tone lasts three seconds; open-string and capo-note references stay separate.")!=std::string::npos&&description->getText().toStdString().find("does not listen, score or record practice.")!=std::string::npos,"Reference explanation retains authored tone/no-practice text and adds shared-Audio idle-return guidance");
  ck(status.getComponentID()=="reference-status"&&status.getTitle().toStdString()=="Read-only Reference tone lifecycle, output state and next action.","Reference status exposes a stable truthful lifecycle title");
  ck(status.isVisible()&&status.primaryText().find("Output is closed.")!=std::string::npos,"Reference status preserves the existing Closed-output state");
  ck(status.primaryText().find("Open Audio settings, then Connect audio and Enable audio before Play tone.")!=std::string::npos,"Reference status preserves the exact Connect and Play next action");
  ck(v.getLocalBounds().contains(status.getBounds())&&status.getHeight()>=88,"Reference status remains readable and contained in the 920x680 layout");
  ck(idle&&v.getLocalBounds().contains(idle->getBounds())&&idle->getY()>=status.detailsView().getBottom()&&idle->getBottom()<=v.findChildWithID("reference-audio-settings")->getY(),"Reference idle marker remains contained between details and the lower action row");
  ck(status.detailsView().getY()>=status.getBottom(),"Reference read-only details remain below the enlarged status");
  auto* audioSettings=v.findChildWithID("reference-audio-settings");auto* play=v.findChildWithID("reference-play");auto* stop=v.findChildWithID("reference-stop");auto* done=v.findChildWithID("reference-done");
  ck(audioSettings&&play&&stop&&done,"Reference lower controls remain discoverable after status reflow");
  if(audioSettings&&play&&stop&&done)ck(audioSettings->getY()>=status.detailsView().getBottom()&&audioSettings->getY()==play->getY()&&play->getY()==stop->getY()&&stop->getY()==done->getY()&&audioSettings->getX()<play->getX()&&play->getX()<stop->getX()&&stop->getX()<done->getX(),"Reference Audio and tone controls remain below details and ordered");
  ck(v.outputSnapshot().state==output::State::Closed&&!v.outputSnapshot().ownsOutcome&&!v.outputSnapshot().owner.valid(),"Reference status inspection creates no output owner or native playback");
  log<<"summary\tPASS\tchecks="<<n<<"\n";std::cout<<"PASS "<<n<<" Reference status surface checks; no sound/Store\n";return 0;
 }
 if(controlOnly){
  struct ControlContract{const char* id;const char* label;const char* title;int order;};
  const ControlContract controls[]={
   {"reference-string","String 6 (low)","Choose the guitar string for the reference tone.",1},
   {"reference-target","Open string (uncapoed)","Choose an open-string or capo-position reference.",2},
   {"reference-sound","Pure sine","Choose the reference sound method.",3},
   {"reference-audio-settings","Audio settings","Open shared Audio settings before playing a reference tone.",4},
   {"reference-connect","Connect audio","Connect the shared Audio output without starting a reference tone.",5},
   {"reference-enable","Enable audio","Enable the observed shared Audio output.",6},
   {"reference-play","Play tone","Play the selected reference tone.",7},
   {"reference-stop","Stop","Stop the reference tone and review the output state.",8},
   {"reference-done","Finish tone","Acknowledge this stopped tone; keep healthy prepared output for another explicit Play.",9},
   {"reference-back","Back","Return to Home after the reference output is idle.",10}
  };
  for(const auto& contract:controls){auto* component=v.findChildWithID(contract.id);ck(component!=nullptr,std::string("Reference control exists: ")+contract.id);if(!component)continue;ck(component->getTitle().toStdString()==contract.title,std::string("Reference control title: ")+contract.id);ck(component->getExplicitFocusOrder()==contract.order,std::string("Reference control focus order: ")+contract.id);ck(component->getWantsKeyboardFocus()==component->isEnabled(),std::string("Reference control focusability preserves enabled-state boundary: ")+contract.id);if(auto* combo=dynamic_cast<juce::ComboBox*>(component))ck(combo->getText().toStdString()==contract.label,std::string("Reference selector label: ")+contract.id);else if(auto* button=dynamic_cast<juce::Button*>(component))ck(button->getButtonText().toStdString()==contract.label,std::string("Reference control label: ")+contract.id);}
  const char* actionIds[]={"reference-audio-settings","reference-connect","reference-enable","reference-play","reference-stop","reference-done","reference-back"};bool actionPresentation=true;for(const auto* id:actionIds){auto* button=dynamic_cast<juce::TextButton*>(v.findChildWithID(id));actionPresentation=actionPresentation&&button&&button->findColour(juce::TextButton::buttonColourId)==juce::Colour{0xff6bd5cb}&&button->findColour(juce::TextButton::textColourOffId)==juce::Colour{0xff10212c}&&button->findColour(juce::TextButton::textColourOnId)==juce::Colour{0xff10212c};}ck(actionPresentation,"Reference action buttons use the primary presentation while preserving the existing control contract");
  ck(v.outputSnapshot().state==output::State::Closed&&!v.outputSnapshot().ownsOutcome&&!v.outputSnapshot().owner.valid(),"Reference control inspection leaves native output closed and unowned");
  log.flush();poses.flush();ck(log.good()&&poses.good(),"Reference control evidence flush");std::cout<<"PASS "<<n<<" Reference control checks; no sound/Store\n";return 0;
 }
 const auto picture=[&](const std::string& name){auto image=v.createComponentSnapshot(v.getLocalBounds());juce::FileOutputStream out(juce::File((dir/(name+".png")).string()));juce::PNGImageFormat png;ck(out.openedOk()&&png.writeImageToStream(image,out),"PNG "+name);out.flush();ck(!out.getStatus().failed(),"PNG flush "+name);};
 ck(!status.detailsVisible()&&!status.detailsView().isVisible(),"details hidden by default");ck(status.primaryText().find("Open Audio settings, then Connect audio and Enable audio before Play tone.")!=std::string::npos,"actual constructed Closed next-action guidance");auto* detailsButton=status.findChildWithID("reference-tone-details");ck(detailsButton==&status.detailsButton()&&detailsButton->getTitle().toStdString()=="Show or hide read-only tone details"&&detailsButton->getExplicitFocusOrder()==11&&detailsButton->getWantsKeyboardFocus(),"Reference Tone details is the stable, keyboard-focusable final action after Back");status.detailsButton().grabKeyboardFocus();ck(status.detailsButton().getWantsKeyboardFocus(),"standard button keyboard focus");
 ck(static_cast<juce::Component&>(status.detailsButton()).keyPressed(juce::KeyPress(juce::KeyPress::returnKey)),"standard JUCE Return handled");
 const auto end=[NSDate dateWithTimeIntervalSinceNow:0.2];while([end timeIntervalSinceNow]>0){CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);if(auto* event=[NSApp nextEventMatchingMask:NSEventMaskAny untilDate:[NSDate dateWithTimeIntervalSinceNow:0.001] inMode:NSDefaultRunLoopMode dequeue:YES])[NSApp sendEvent:event];}
 ck(status.detailsVisible()&&status.detailsView().isVisible()&&status.detailsView().isReadOnly(),"posted keyboard action opens readonly details");
 ck(status.detailsButton().isRegisteredForShortcut(juce::KeyPress(juce::KeyPress::spaceKey)),"standard JUCE Space shortcut is registered for the disclosure");status.detailsButton().triggerClick();const auto closeEnd=[NSDate dateWithTimeIntervalSinceNow:0.2];while([closeEnd timeIntervalSinceNow]>0){CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);if(auto* event=[NSApp nextEventMatchingMask:NSEventMaskAny untilDate:[NSDate dateWithTimeIntervalSinceNow:0.001] inMode:NSDefaultRunLoopMode dequeue:YES])[NSApp sendEvent:event];}ck(!status.detailsVisible()&&!status.detailsView().isVisible(),"details toggle closes readonly disclosure without changing the Reference output");
 guitar::Setup setup;setup.openMidi=guitar::tuning(guitar::Preset::DropD);setup.capo=2;v.setSetup(setup);const auto open=v.displayedPitch();ck(open=="D2 | 73.42 Hz | Capo 2 | Open-string tuning","actual applied DropD open pitch");
 auto* target=dynamic_cast<juce::ComboBox*>(v.findChildWithID("reference-target"));auto* method=dynamic_cast<juce::ComboBox*>(v.findChildWithID("reference-sound"));
 ck(target&&method,"actual target and sound selectors present");target->setSelectedId(2,juce::sendNotificationSync);ck(v.displayedPitch()=="E2 | 82.41 Hz | Capo 2 | At capo","actual capo reference separate from open");method->setSelectedId(2,juce::sendNotificationSync);ck(method->getText()=="Clean pluck"&&v.displayedPitch().find("E2")==0,"pluck preserves same pitch");method->setSelectedId(1,juce::sendNotificationSync);ck(method->getText()=="Pure sine","sine remains available");
 const auto pitch=v.displayedPitch();status.showDetails(false);ck(!status.detailsVisible()&&v.displayedPitch()==pitch,"close details preserves pitch and target");
 using S=output::State;
 for(auto size:{std::pair{920,680},std::pair{1280,800}}){v.setSize(size.first,size.second);const auto suffix=std::to_string(size.first);status.showDetails(false);desktop::ReferenceGuidanceInput i;i.output.state=S::Unresolved;i.output.pendingOutcome=true;i.output.ownsOutcome=true;i.started=true;i.ownerMatches=true;i.canDone=true;i.output.owner.id[0]=42;i.output.owner.epoch=12;i.output.owner.generation=3;
  const std::string error="Synthetic original Done queue refusal. Stop and reconnect is obsolete feedback, not current guidance.";
  const auto pose=[&](const char* id){status.present(i,error,"Synthetic backend context; no actual failure injected.");poses<<id<<'-'<<suffix<<'\t'<<status.primaryText()<<'\n';picture(std::string(id)+"-"+suffix);ck(status.primaryText().find(error)==std::string::npos,"raw error absent primary "+std::string(id));};
  pose("pending-done");i.output.state=S::Fault;pose("pending-fault");i.resolving=true;i.canDone=false;pose("resolving");i={};i.output.state=S::Fault;i.canBack=true;pose("unowned-fault");i={};i.output.state=S::Ready;i.canPlay=true;pose("ready");
  status.present(i,"é ♯ original\n"+std::string(2000,'x'),"backend raw context");status.showDetails(true);picture("details-"+suffix);ck(status.detailsView().getText().contains("[display truncated]")&&status.detailsView().getText().contains("é ♯"),"actual bounded Unicode details");
  ck(v.displayedPitch()==pitch&&target->getSelectedId()==2&&method->getSelectedId()==1,"poses preserve applied pitch and selectors");status.showDetails(false);
 }
 ck(v.outputSnapshot().state==S::Closed&&!v.outputSnapshot().ownsOutcome&&!v.outputSnapshot().owner.valid(),"all poses leave actual output Closed and owner absent; no practice");log.flush();poses.flush();ck(log.good()&&poses.good(),"component evidence flush");std::cout<<"PASS "<<n<<" reference component checks; injected presentation poses only, no sound/Store\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<n<<": "<<e.what()<<'\n';return 1;}}
