#define main retained_home_route_shared_audio_fixture_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include <stdexcept>
#include <iostream>
namespace fathom::desktop {
struct HomeRouteTestAccess {
    static void page(HomeView& h,HomeView::Page p){h.page_=p;h.update();}
    static ReferenceView& reference(HomeView& h){return h.referenceView;}
    static PracticeView& practice(HomeView& h){return *h.practiceView;}
    static GuidedSessionView& guided(HomeView& h){return h.guidedView;}
    static FreeplayView& freeplay(HomeView& h){return h.freeplayView;}
    static bool detour(const HomeView& h){return h.homeLearnDetour_;}
};
struct GuidedSessionViewTestAccess { static void running(GuidedSessionView& v,bool value){v.running_=value;} static void linkedLayout(GuidedSessionView& v,bool value){v.savedAttemptLinked_=value;v.resized();} };

}
namespace {
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
}
int main(){
 juce::ScopedJuceInitialiser_GUI gui;
 using namespace fathom::desktop;
 HomeView h;std::string reason;
 for(const auto size:{juce::Point<int>{620,680},juce::Point<int>{920,680},juce::Point<int>{1400,1000}}){
  h.setSize(size.x,size.y);
  for(auto page:{HomeView::Page::Learn,HomeView::Page::Practice,HomeView::Page::Reference,HomeView::Page::Progress}){
   HomeRouteTestAccess::page(h,page);
   require(h.getLocalBounds().contains(h.homeRouteBounds()),"Home control outside window");
   require(h.childPageBounds().getY()==64 && h.childPageBounds().getHeight()==size.y-64,"Reserved header missing");
   require(!h.homeRouteBounds().intersects(h.childPageBounds()),"Home control overlaps child page");
  }
 }

 // Exercise Guitar at the actual reserved-header child sizes, including narrow branch.
 for(const auto size:{juce::Point<int>{620,616},juce::Point<int>{920,616},juce::Point<int>{1400,936}}){
  GuitarSetupView guitar;guitar.setSize(size.x,size.y);
  juce::Component* board=nullptr;juce::Component* footer=nullptr;
  for(auto* child:guitar.getChildren()){
   if(child->getY()==434||child->getY()==440)board=child;
   if(child->getY()==size.y-49&&child->getHeight()==35)footer=child;
  }
  require(board&&footer,"Actual Guitar board/footer not found");
  require(guitar.getLocalBounds().contains(board->getBounds())&&guitar.getLocalBounds().contains(footer->getBounds()),"Guitar board/footer clipped by child bounds");
  require(board->getBottom()+8<=footer->getY(),"Guitar board overlaps reserved footer gap");
 }
 // Exercise the nested Practice layout, not just the outer child rectangle.
 for(const auto size:{juce::Point<int>{920,680},juce::Point<int>{1400,1000}}){
  h.setSize(size.x,size.y);HomeRouteTestAccess::page(h,HomeView::Page::Practice);
  auto& practice=HomeRouteTestAccess::practice(h);practice.showTab(true);
  for(bool focus:{false,true})for(bool board:{false,true}){
   practice.setFocusMode(focus);setup::BoardDisplay display;display.visible=board;
   practice.setBoardDisplay(display);practice.resized();
   for(double zoom:{0.1,2.0}){
    require(practice.tabView().setZoom(zoom),"TAB zoom refused");
    const auto tabBounds=practice.tabView().getBounds();
    require(practice.getLocalBounds().contains(tabBounds),"Nested TAB outside Practice");
    bool viewportSeen=false;
    for(auto* child:practice.tabView().getChildren())if(auto* viewport=dynamic_cast<juce::Viewport*>(child)){
     viewportSeen=true;require(viewport->getWidth()>0&&viewport->getHeight()>0,"Nested TAB viewport collapsed");
     require(practice.tabView().getLocalBounds().contains(viewport->getBounds()),"TAB viewport clipped");
    }
    require(viewportSeen,"TAB viewport missing");
    if(board){
     require(practice.getLocalBounds().contains(practice.boardBounds()),"Board outside nested Practice");
     require(!practice.boardBounds().intersects(tabBounds),"Board overlaps TAB");
    }
   }
  }
 }

 // The reserved Home header must leave usable nested Reference/Guided controls.
 for(const auto size:{juce::Point<int>{920,680},juce::Point<int>{1400,1000}}){
  h.setSize(size.x,size.y);
  auto control=[](juce::Component& view,const char* id)->juce::Component&{
   for(auto* child:view.getChildren())if(child->getComponentID()==id)return *child;
   throw std::runtime_error("Essential control missing");
  };
  HomeRouteTestAccess::page(h,HomeView::Page::Reference);
  auto& reference=HomeRouteTestAccess::reference(h);
  auto& referenceBack=control(reference,"reference-back");
  auto& referenceAudio=control(reference,"reference-audio-settings");
  require(reference.getLocalBounds().contains(referenceBack.getBounds()),"Nested Reference Back clipped");
  require(reference.getLocalBounds().contains(referenceAudio.getBounds()),"Nested Reference Audio clipped");
  require(!referenceBack.getBounds().intersects(referenceAudio.getBounds()),"Reference Back overlaps Audio");
  HomeRouteTestAccess::page(h,HomeView::Page::Guided);
  auto& guided=HomeRouteTestAccess::guided(h);
  for(bool linked:{false,true}){
   GuidedSessionViewTestAccess::linkedLayout(guided,linked);
   std::vector<juce::Rectangle<int>> bounds;
   for(const auto* id:{"guided-audio-settings","start","open-first","stop","interrupt","open-progress","back"}){
    const auto rect=control(guided,id).getBounds();
    require(rect.getWidth()>0&&rect.getHeight()>0&&guided.getLocalBounds().contains(rect),"Nested Guided essential control clipped");
    for(const auto& prior:bounds)require(!prior.intersects(rect),"Guided essential controls overlap");
    bounds.push_back(rect);
   }
  }
  GuidedSessionViewTestAccess::linkedLayout(guided,false);
 }
 HomeRouteTestAccess::page(h,HomeView::Page::Reference);
 require(h.requestHome(reason)&&h.page()==HomeView::Page::Home,"Stopped ordinary page cannot reach Home");
 HomeRouteTestAccess::page(h,HomeView::Page::Guided);
 GuidedSessionViewTestAccess::running(HomeRouteTestAccess::guided(h),true);
 require(!h.requestHome(reason)&&h.page()==HomeView::Page::Guided,"Active Guided escaped");
 GuidedSessionViewTestAccess::running(HomeRouteTestAccess::guided(h),false);
 HomeRouteTestAccess::page(h,HomeView::Page::Setup);
 require(!h.requestHome(reason)&&h.page()==HomeView::Page::Setup,"Unapplied setup silently discarded");
 std::cout<<"Home route guards/layout PASS (software only; no profile/audio/native proof)\n";
}
