#include "desktop/TabView.hpp"
#include "music_reference_cases.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
using namespace fathom;
int main(int argc,char** argv){int count=0;try{
 const bool responsiveOnly=argc==3&&std::string(argv[2])=="--responsive-layout";if((argc!=2&&!responsiveOnly)||std::filesystem::exists(argv[1]))throw std::runtime_error("New output directory required");std::filesystem::path root=argv[1];std::filesystem::create_directories(root);std::ofstream log(root/"checks.tsv");
 const auto ck=[&](bool b,const std::string& what){++count;log<<what<<'\t'<<(b?"PASS":"FAIL")<<'\n';if(!b)throw std::runtime_error(what);};
 juce::ScopedJuceInitialiser_GUI gui;desktop::TabView view;view.setCompact(true);auto originals=controlExamples();
 if(responsiveOnly){
  view.setSize(640,680);const auto doc=std::make_shared<const tab::Document>(reference_fixtures::checked(originals[5]));view.setDocument(doc);view.showDetail(false);const auto bounds=view.getLocalBounds();
  for(auto* child:view.getChildren())if(child->isVisible())ck(bounds.contains(child->getBounds())&&child->getWidth()>0&&child->getHeight()>0,"compact TAB child is positive and contained");
  juce::Label* compactTitle=nullptr;for(auto* child:view.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText().startsWith("TAB")&&label->getText().contains("Authored source view"))compactTitle=label;ck(compactTitle&&compactTitle->isVisible(),"compact TAB exposes a truthful authored-source heading");ck(compactTitle&&compactTitle->getBounds().getY()==16&&compactTitle->getBounds().getHeight()==30,"compact TAB heading owns a dedicated top row");
  std::vector<juce::Button*> actions;for(auto* child:view.getChildren())if(auto* button=dynamic_cast<juce::Button*>(child);button&&button->isVisible())actions.push_back(button);for(std::size_t left=0;left<actions.size();++left)for(std::size_t right=left+1;right<actions.size();++right)ck(!actions[left]->getBounds().intersects(actions[right]->getBounds()),"compact TAB actions do not overlap");
  auto* detail=static_cast<juce::Button*>(nullptr);auto* source=static_cast<juce::Button*>(nullptr);for(auto* button:actions){if(button->getButtonText()=="Detail")detail=button;if(button->getButtonText()=="Source / instructions")source=button;}ck(detail&&source,"compact TAB Detail and Source actions remain reachable");ck(view.selectEvent(originals[5].events[4].id),"compact TAB selects retained authored event");view.showDetail(true);ck(view.detailVisible()&&view.visibleDetail()==doc->detail(originals[5].events[4].id),"compact TAB preserves exact authored event detail");view.showSource();ck(view.selectedEvent().empty()&&view.visibleDetail()==doc->overview(),"compact TAB Source restores exact authored overview");
  desktop::TabView standard;standard.setSize(920,680);standard.setVisible(true);bool standardTitle=false,standardSource=false;for(auto* child:standard.getChildren()){if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getText()=="Interactive TAB")standardTitle=label->isVisible();if(auto* button=dynamic_cast<juce::Button*>(child);button&&button->getButtonText()=="Source / instructions")standardSource=button->getWidth()>0&&button->getHeight()>0;}ck(standardTitle&&standardSource,"standard TAB geometry remains available at 920x680");log.flush();std::cout<<"PASS "<<count<<" compact TAB surface checks; no native audio or profile activity\n";return 0;
 }
 struct Pose{std::string id;music::Model model;std::string event;};
 std::vector<Pose> poses{{"capo",music_references::model(music_references::positions[2]),"position"},{"L39-dual",originals[5],originals[5].events[4].id},{"L15-triplet",originals[3],originals[3].events[1].id},{"held",music_references::held(),"continued"},{"rest",music_references::held(),"rest"}};
 for(const auto& pose:poses)for(int width:{920,1280}){view.setSize(width,width==920?680:800);const auto doc=std::make_shared<const tab::Document>(reference_fixtures::checked(pose.model));view.setDocument(doc);view.setZoom(1);view.setOverlays({true,true,true,true});ck(view.selectEvent(pose.event),pose.id+" real source selection");view.showDetail(true);ck(view.visibleDetail()==doc->detail(pose.event),pose.id+" exact source details retained");view.showDetail(false);
  // Display pose only: no playback clock, input gesture, native audio or profile.
  ck(view.setPlayback({pose.event},"Reference inspection pose; no sound executed."),pose.id+" explicit labelled pose");ck(view.document()==doc&&view.selectedEvent()==pose.event,pose.id+" source identity unchanged");
  const auto name=pose.id+"-"+std::to_string(width);auto image=view.createComponentSnapshot(view.getLocalBounds());juce::FileOutputStream out(juce::File((root/(name+".png")).string()));juce::PNGImageFormat png;ck(out.openedOk()&&png.writeImageToStream(image,out),name+" actual PNG");out.flush();ck(!out.getStatus().failed(),name+" PNG flushed");
  std::ofstream text(root/(name+".txt"));text<<doc->detail(pose.event);text.flush();ck(text.good(),name+" source detail exported");
 }
 log.flush();ck(log.good(),"checks flushed");std::cout<<"PASS "<<count<<" actual TAB component reference checks; no native audio or human review\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL after "<<count<<": "<<e.what()<<'\n';return 1;}}
