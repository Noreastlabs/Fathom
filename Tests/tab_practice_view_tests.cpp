#include "desktop/PracticeView.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
using namespace fathom;
int main(int argc,char**argv){int count=0;try{
 if(argc!=2||std::filesystem::exists(argv[1]))throw std::invalid_argument("new evidence directory required");std::filesystem::create_directories(argv[1]);std::ofstream log(std::filesystem::path(argv[1])/"checks.tsv");
 const auto ck=[&](bool b,const std::string& label){++count;log<<label<<'\t'<<(b?"PASS":"FAIL")<<'\n';if(!b)throw std::runtime_error(label);};
 juce::ScopedJuceInitialiser_GUI gui;desktop::PracticeView v;v.showTab(true);auto& tab=v.tabView();
 ck(v.tabVisible()&&!v.coordinator().pending(),"browse TAB no practice outcome");ck(!v.startSample(),"no profile or output start refusal");ck(tab.document()->source().itemId=="synthetic:practice-transport","literal source identity");ck(tab.document()->source().syntheticFixture,"not admitted curriculum");
 const auto picture=[&](const std::string& name){auto image=v.createComponentSnapshot(v.getLocalBounds());juce::FileOutputStream out(juce::File((std::filesystem::path(argv[1])/(name+".png")).string()));juce::PNGImageFormat png;ck(out.openedOk()&&png.writeImageToStream(image,out),"PNG "+name);out.flush();ck(!out.getStatus().failed(),"PNG flush "+name);};
 for(auto size:{std::pair{920,680},std::pair{1280,800}}){v.setSize(size.first,size.second);tab.showDetail(false);tab.setOverlays({true,true,true,true});
  ck(tab.selectEvent("picked-E"),"explicit selected source");const auto detail=tab.visibleDetail();
  for(const auto* id:{"picked-E","held-E","full-rest"}){ck(tab.setPlayback({id},std::string("Synthetic component fixture / accepted mapping tested separately: ")+id),"known playing source ID");ck(tab.selectedEvent()=="picked-E"&&tab.visibleDetail()==detail,"live highlight does not replace selected detail");picture(std::string(id)+"-"+std::to_string(size.first));}
  ck(!tab.setPlayback({"invalid"},"bad")&&tab.playingEvents()==std::vector<std::string>{"full-rest"},"unknown event rejected without mutation");
  tab.showDetail(true);ck(tab.detailVisible(),"full detail reachable compact");picture("detail-"+std::to_string(size.first));tab.showSource();ck(tab.visibleDetail().find("synthetic:practice-transport")!=std::string::npos,"full source preserved");picture("source-"+std::to_string(size.first));tab.showDetail(false);
 }
 const auto selected=tab.selectedEvent();v.showTab(false);ck(!v.tabVisible()&&!v.coordinator().pending(),"mode results creates no practice");v.showTab(true);ck(tab.selectedEvent()==selected,"mode retains selection");ck(!v.keyPressed(juce::KeyPress(juce::KeyPress::spaceKey))&&!v.coordinator().pending(),"keyboard Start respects absent profile");ck(v.requestClose(),"no original safe close");std::cout<<"PASS "<<count<<" TAB practice component checks; no native audio run\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<count<<": "<<e.what()<<'\n';return 1;}}
