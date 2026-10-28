#include "desktop/PracticeView.hpp"
#import <AppKit/AppKit.h>
#include <filesystem>
#include <fstream>
#include <iostream>
using namespace fathom;
int main(int argc,char**argv){int n=0;try{
 if(argc!=2||std::filesystem::exists(argv[1]))throw std::runtime_error("New evidence directory required");std::filesystem::create_directories(argv[1]);const std::filesystem::path dir=argv[1];std::ofstream log(dir/"checks.tsv"),poses(dir/"poses.tsv");
 const auto ck=[&](bool b,const std::string& s){++n;log<<s<<'\t'<<(b?"PASS":"FAIL")<<'\n';if(!b)throw std::runtime_error(s);};
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];juce::ScopedJuceInitialiser_GUI gui;
 desktop::PracticeView v;v.setSize(920,680);v.addToDesktop(juce::ComponentPeer::windowHasTitleBar);v.setVisible(true);
 auto& status=v.saveStatusView();auto* emptySource=dynamic_cast<juce::Label*>(v.findChildWithID("practice-empty-source-state"));
 ck(emptySource&&emptySource->isVisible()&&emptySource->getText()=="No source-backed case selected yet","visible empty-source marker before Focus");
 const auto emptyGuidance=status.primaryText();
 ck(emptyGuidance.find("Choose Create / open local profile on Home.")!=std::string::npos&&emptyGuidance.find("--capture-preview")==std::string::npos&&emptyGuidance.find("No Attempt")!=std::string::npos&&emptyGuidance.find("audio")!=std::string::npos&&emptyGuidance.find("curriculum credit")!=std::string::npos&&emptyGuidance.find("Result saved")==std::string::npos&&emptyGuidance.find("Attempt ended")==std::string::npos,"actual unattached guidance directs to Home without a launch command or fabricated result");
 v.setFocusMode(true);auto& tab=v.tabView();const auto document=tab.document();tab.selectEvent("picked-E");tab.setPlayback({"full-rest"},"Synthetic presentation pose; no sound.");tab.setZoom(2.0);tab.restoreScrollPosition({999,999});const auto scroll=tab.scrollPosition();const auto detail=tab.visibleDetail();
 const auto picture=[&](const std::string& name){auto image=v.createComponentSnapshot(v.getLocalBounds());juce::FileOutputStream out(juce::File((dir/(name+".png")).string()));juce::PNGImageFormat png;ck(out.openedOk()&&png.writeImageToStream(image,out),"PNG "+name);out.flush();ck(!out.getStatus().failed(),"PNG flush "+name);};
 ck(!status.detailsVisible()&&!status.detailsView().isVisible(),"details hidden by default");status.detailsButton().grabKeyboardFocus();ck(status.detailsButton().getWantsKeyboardFocus(),"details standard keyboard focus enabled");
 ck(static_cast<juce::Component&>(status.detailsButton()).keyPressed(juce::KeyPress(juce::KeyPress::returnKey)),"standard JUCE Return handled by details button");
 const auto end=[NSDate dateWithTimeIntervalSinceNow:0.2];
 while([end timeIntervalSinceNow]>0){CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);if(auto* event=[NSApp nextEventMatchingMask:NSEventMaskAny untilDate:[NSDate dateWithTimeIntervalSinceNow:0.001] inMode:NSDefaultRunLoopMode dequeue:YES])[NSApp sendEvent:event];}
 log<<"keyboard-open-state\t"<<status.detailsVisible()<<','<<status.detailsView().isVisible()<<','<<tab.isVisible()<<'\n';
 ck(status.detailsVisible()&&status.detailsView().isVisible()&&!tab.isVisible(),"actual posted button activation opens separate details");
 ck(status.detailsView().isReadOnly(),"diagnostics readonly");ck(tab.document()==document&&tab.selectedEvent()=="picked-E"&&tab.visibleDetail()==detail&&tab.zoom()==2&&tab.scrollPosition()==scroll,"details preserve source and selected/viewport state");
 ck(!v.coordinator().pending()&&!v.captureSession()&&v.outputStatus().lifecycle.state==output::State::Closed,"details keyboard action creates no owner/profile/audio");
 status.showDetails(false);ck(tab.isVisible()&&tab.scrollPosition()==scroll,"close restores exact TAB scroll");tab.showSource();tab.showDetail(true);const auto sourceDetail=tab.visibleDetail();const auto sourceSelected=tab.selectedEvent();status.showDetails(true);v.setFocusMode(false);v.setFocusMode(true);status.showDetails(false);
 ck(tab.document()==document&&tab.visibleDetail()==sourceDetail&&tab.selectedEvent()==sourceSelected&&tab.detailVisible(),"Source detail preserved through diagnostics and Focus changes");tab.showDetail(false);tab.setZoom(1.0);
 using P=capture::SessionPhase;using S=storage::Status;
 for(auto size:{std::pair{920,680},std::pair{1280,800}}){
  v.setSize(size.first,size.second);v.setFocusMode(true);const auto suffix=std::to_string(size.first);
  status.showDetails(false);desktop::PracticeGuidanceInput input;input.attached=true;input.hasOwner=true;input.hasOriginal=true;input.canRetry=true;
  storage::Reply reply;reply.operation="synthetic-original-save";reply.owner="synthetic-original-owner";reply.code="ACK_TIMEOUT";reply.message="Synthetic unknown receipt; actual persistence is NOT RUN in this component pose.";
  const auto pose=[&](const char* id){reply.status=input.receipt;status.present(input,reply);poses<<id<<'-'<<suffix<<'\t'<<status.primaryText()<<"\n";picture(std::string(id)+"-"+suffix);ck(status.primaryText().find(reply.code)==std::string::npos&&status.primaryText().find(reply.message)==std::string::npos,"raw receipt absent primary "+std::string(id));};
  input.phase=P::Review;input.canSave=true;pose("review");input.phase=P::Saving;input.receipt=S::Unresolved;pose("unknown-save");
  input.phase=P::Failed;input.receipt=S::Conflict;reply.code="CONFLICT";pose("conflict");
  input.phase=P::Saved;input.outputCleared=false;pose("saved-output-conflict");input.receipt=S::Confirmed;reply.code="SAVED";reply.message="Synthetic confirmed result; output cleanup pending.";pose("saved-output");input.outputCleared=true;input.receipt=S::Unresolved;reply.code="AUDIT_ACK_TIMEOUT";reply.message="Synthetic unknown late-evidence receipt; final result remains confirmed.";pose("saved-late");
  reply.message="é ♯ original details\n"+std::string(2000,'x');status.present(input,reply,"Synthetic local exception\nraw text stays in details.");status.showDetails(true);picture("details-"+suffix);
  ck(status.detailsView().getText().contains("[display truncated]")&&status.detailsView().getText().contains("é ♯"),"bounded actual Unicode details");
  status.showDetails(false);v.setFocusMode(false);v.showTab(false);status.present(input,reply);status.showDetails(true);picture("results-details-"+suffix);status.showDetails(false);
 }
 ck(v.requestClose()&&!v.coordinator().pending()&&v.outputStatus().lifecycle.state==output::State::Closed,"no introduced practice/sound/profile");log.flush();poses.flush();ck(log.good()&&poses.good(),"component evidence flush");std::cout<<"PASS "<<n<<" guidance component checks; state poses synthetic, no audio/Store\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<n<<": "<<e.what()<<'\n';return 1;}}
