#include "desktop/RecipeTaskView.hpp"
#include <iostream>
#include <stdexcept>

using namespace fathom;
using namespace fathom::tasks::recipes;
using V = json::Value;
using O = V::Object;
namespace {
std::size_t checks{}, paths{}, refusals{}, menuOrigins{};
void check(bool value,const char* message){++checks;if(!value)throw std::runtime_error(message);}
juce::Component* find(juce::Component& parent,const juce::String& id){if(parent.getComponentID()==id)return &parent;for(int n=0;n<parent.getNumChildComponents();++n)if(auto* p=find(*parent.getChildComponent(n),id))return p;return nullptr;}
template<class T>T& control(desktop::RecipeTaskView& view,const juce::String& id){auto* p=dynamic_cast<T*>(find(view,id));check(p!=nullptr,("Missing control "+id).toRawUTF8());return *p;}
desktop::RecipeTaskButton& button(desktop::RecipeTaskView& view,const char* id){return control<desktop::RecipeTaskButton>(view,id);}
void deliver(desktop::RecipeTaskView& view,const char* id){auto& b=button(view,id);check(b.isVisible()&&b.isEnabled(),"delivery control unavailable");b.deliver(b.capture());}
void bounds(juce::Component& parent){for(int n=0;n<parent.getNumChildComponents();++n){auto& c=*parent.getChildComponent(n);if(c.isVisible()){if(c.getComponentID().startsWith("recipe-")){check(c.getWidth()>0&&c.getHeight()>0,"visible control has empty bounds");check(parent.getLocalBounds().contains(c.getBounds()),"visible control outside its layout parent");}bounds(c);}}}
juce::String words(const V& value){juce::String out;for(const auto& v:value.array()){if(out.isNotEmpty())out+="; ";out+=juce::String::fromUTF8(v.string().c_str());}return out;}
void fill(desktop::RecipeTaskView& view,const V& report,bool positives=true){
 for(const auto& item:report.object()){if(item.first=="step"||item.first=="response")continue;const auto id="recipe-report-"+juce::String::fromUTF8(item.first.c_str());
  if(item.second.isBool()){auto& c=control<juce::ToggleButton>(view,id);check(!c.getToggleState(),"new step physical reports must be unchecked");c.setToggleState(positives,juce::dontSendNotification);}
  else if(!item.second.isNumber()){auto& c=control<juce::TextEditor>(view,id);check(c.getText().isEmpty(),"new step naming reports must be blank");c.setText(item.second.isArray()?words(item.second):juce::String::fromUTF8(item.second.string().c_str()),false);}
  else check(find(view,id)==nullptr,"fixed source count must not become a prefilled learner report field");
 }
}
void select(desktop::RecipeTaskView& view,int stroke=1,const juce::String& plan="I will sustain the selected secure target, then release; this is my own test-only choice."){
 control<juce::ComboBox>(view,"recipe-start-stroke").setSelectedId(stroke,juce::dontSendNotification);
 if(view.task()->retainedDefinition().recipe()==Recipe::RecoveryPair){auto& origin=control<juce::ComboBox>(view,"recipe-origin");origin.setSelectedId(1,juce::dontSendNotification);origin.onChange();auto& target=control<juce::ComboBox>(view,"recipe-target");check(target.getSelectedId()==0,"nearest target must remain an explicit blank choice");target.setSelectedId(1,juce::dontSendNotification);control<juce::TextEditor>(view,"recipe-remainder-plan").setText(plan,false);}
 deliver(view,"recipe-choose");check(view.task()->view().phase==Phase::Steps,"valid explicit choice failed");
}
void release(desktop::RecipeTaskView& view){auto& c=control<juce::ToggleButton>(view,"recipe-release-report");check(!c.getToggleState(),"release report starts unchecked");c.setToggleState(true,juce::dontSendNotification);deliver(view,"recipe-release");check(view.task()->view().phase==Phase::Closed,"explicit physical release failed");}
void unchanged(desktop::RecipeTaskView& view,const std::function<void()>& run){const auto revision=view.task()->revision();const auto count=view.task()->history().size();const auto phase=view.task()->view().phase;run();check(view.task()->revision()==revision&&view.task()->history().size()==count&&view.task()->view().phase==phase,"invalid UI delivery mutated owned state");++refusals;}
void initialise(desktop::RecipeTaskView& view,const std::string& key){view.setSize(920,680);view.setVisible(true);check(view.open(key),"trusted recipe open failed");check(control<juce::ComboBox>(view,"recipe-start-stroke").getSelectedId()==0,"first pick starts blank");check(control<juce::TextEditor>(view,"recipe-remainder-plan").getText().isEmpty(),"remainder plan starts blank");}
void screenshot(desktop::RecipeTaskView& view,const juce::File& directory,const char* name){auto image=view.createComponentSnapshot(view.getLocalBounds());check(image.getWidth()==920&&image.getHeight()==680,"snapshot supported size");auto stream=directory.getChildFile(name).createOutputStream();check(bool(stream),"snapshot output");juce::PNGImageFormat format;check(format.writeImageToStream(image,*stream),"snapshot encoding");}
void sourceFacts(desktop::RecipeTaskView& view){
 const auto& d=view.task()->retainedDefinition();const auto& c=d.retainedContract();const auto source=control<juce::TextEditor>(view,"recipe-source").getText();
 for(const auto& instruction:d.retainedSourceContext().find("context_tasks")->array())check(source.contains(juce::String::fromUTF8(instruction.find("instruction")->string().c_str())),"full shared source context missing");
 check(!source.contains("contract_sha256")&&!source.contains("schema")&&source.contains("No source")==false,"implementation names leaked into instructions");
 if(d.recipe()==Recipe::CallAnswer){const auto& rules=*c.find("source_rules");check(source.contains(juce::String::fromUTF8(rules.find("exact_variation")->string().c_str()))&&source.contains("gap has no attack"),"call variation/gap missing");
  for(const auto& note:c.find("ordered_contacts")->array()){std::int64_t s{},f{};check(note.find("string")->integer(s)&&note.find("fret")->integer(f),"source contact integer");const auto literal=juce::String::fromUTF8(note.find("printed_note")->string().c_str())+" ("+juce::String::fromUTF8(note.find("degree")->string().c_str())+juce::String::fromUTF8(") — printed string ")+juce::String(s)+", fret "+juce::String(f);check(source.contains(literal),"printed contact/degrees omitted");}}
 else{check(source.contains(juce::String::fromUTF8(c.find("printed_label")->string().c_str()))&&source.contains(juce::String::fromUTF8(c.find("printed_roles")->string().c_str())),"printed recovery pair/roles missing");check(source.contains("Your menus and remainder plan are explicit choices")&&source.contains("provisional minimum pitch-distance"),"chosen vs printed or nearest limitation missing");if(!c.find("borrowed_G_natural_scope")->null())check(source.contains(juce::String::fromUTF8(c.find("borrowed_G_natural_scope")->string().c_str())),"borrowed G scope missing");}
}
void menus(desktop::RecipeTaskView& view){if(view.task()->retainedDefinition().recipe()!=Recipe::RecoveryPair)return;
 const auto& d=view.task()->retainedDefinition();auto& origin=control<juce::ComboBox>(view,"recipe-origin");auto& target=control<juce::ComboBox>(view,"recipe-target");const auto origins=allowedChoices(d).find("source_contacts")->array();check(origin.getNumItems()==static_cast<int>(origins.size()),"origin menu incomplete");
 for(std::size_t n=0;n<origins.size();++n){origin.setSelectedId(static_cast<int>(n+1),juce::dontSendNotification);origin.onChange();const auto targets=allowedChoices(d,origins[n]).find("nearest_target_contacts")->array();check(target.getNumItems()==static_cast<int>(targets.size())&&target.getSelectedId()==0,"nearest target menu or blank selection changed");for(std::size_t t=0;t<targets.size();++t){std::int64_t s{},f{};check(targets[t].find("string")->integer(s)&&targets[t].find("fret")->integer(f),"target integer");check(target.getItemText(static_cast<int>(t))=="chosen string "+juce::String(s)+", fret "+juce::String(f),"menu differs from allowed choice policy");}++menuOrigins;}
 origin.setSelectedId(0,juce::dontSendNotification);origin.onChange();check(target.getNumItems()==0&&target.getSelectedId()==0,"cleared origin must clear target");
}
void navigationCases(const std::string& key){
 for(const auto initial:{Phase::Select,Phase::Steps,Phase::Release,Phase::Closed}){
  desktop::RecipeTaskView view;initialise(view,key);if(initial!=Phase::Select)select(view);if(initial==Phase::Release||initial==Phase::Closed){deliver(view,"recipe-stop");if(initial==Phase::Closed)release(view);}check(view.task()->view().phase==initial,"navigation fixture phase");
  int exits=0,settings=0;view.onBack=[&]{++exits;return true;};view.onSettings=[&]{++settings;return true;};
  auto& oldButton=button(view,initial==Phase::Select?"recipe-choose":initial==Phase::Closed?"recipe-again":"recipe-report");const auto stale=oldButton.capture();
  const auto count=view.task()->history().size();const auto pass=view.task()->pass();const auto instance=view.task()->capture(Intent::Report).instance;
  if(initial==Phase::Steps||initial==Phase::Release){unchanged(view,[&]{check(!view.open(key),"active open should refuse");});check(view.task()->capture(Intent::Report).instance==instance,"refused open lost owner");deliver(view,"recipe-settings");check(settings==0&&view.task()->view().phase==Phase::Release,"settings escaped active physical release");const auto h=view.task()->history().size();check(!view.prepareForNavigation()&&view.task()->history().size()==h,"repeated pending navigation changed release owner/history");unchanged(view,[&]{oldButton.deliver(stale);});release(view);deliver(view,"recipe-back");check(exits==1&&view.task()->view().phase==Phase::Closed,"released back failed");}
  else{deliver(view,"recipe-settings");check(settings==1&&view.task()->view().phase==initial&&view.task()->history().size()==count+1&&view.task()->pass()==pass+1,"idle settings must retain phase/history and native fence");const auto h=view.task()->history().size();check(view.prepareForNavigation()&&view.task()->history().size()==h,"idle navigation must be idempotent");unchanged(view,[&]{oldButton.deliver(stale);});view.resumeAfterNavigation();unchanged(view,[&]{oldButton.deliver(stale);});if(initial==Phase::Select)select(view);else deliver(view,"recipe-again");}
  bounds(view);
 }
}
void delayedMenus(const std::string& key){
 desktop::RecipeTaskView view;initialise(view,key);auto old=control<juce::ComboBox>(view,"recipe-origin").onChange;
 check(view.open(key),"idle source replacement failed");auto& origin=control<juce::ComboBox>(view,"recipe-origin");auto& target=control<juce::ComboBox>(view,"recipe-target");origin.setSelectedId(1,juce::dontSendNotification);
 const auto revision=view.task()->revision();old();check(target.getNumItems()==0&&view.task()->revision()==revision,"delayed foreign origin callback changed new selection");++refusals;
 origin.onChange();check(target.getNumItems()>0&&target.getSelectedId()==0,"fresh origin callback failed");
}
void invalidCases(const std::string& key){
 desktop::RecipeTaskView view;initialise(view,key);auto& choose=button(view,"recipe-choose");unchanged(view,[&]{choose.deliver(choose.capture());});
 control<juce::ComboBox>(view,"recipe-start-stroke").setSelectedId(3,juce::dontSendNotification);unchanged(view,[&]{choose.deliver(choose.capture());});
 if(view.task()->retainedDefinition().recipe()==Recipe::RecoveryPair){control<juce::ComboBox>(view,"recipe-start-stroke").setSelectedId(1,juce::dontSendNotification);unchanged(view,[&]{choose.deliver(choose.capture());});auto& origin=control<juce::ComboBox>(view,"recipe-origin");origin.setSelectedId(1,juce::dontSendNotification);origin.onChange();unchanged(view,[&]{choose.deliver(choose.capture());});control<juce::ComboBox>(view,"recipe-target").setSelectedId(1,juce::dontSendNotification);auto& plan=control<juce::TextEditor>(view,"recipe-remainder-plan");for(const auto& bad:{juce::String(" "),juce::String::repeatedString("x",501)}){plan.setText(bad,false);unchanged(view,[&]{choose.deliver(choose.capture());});}}
 select(view);auto expected=view.task()->expectedReport();unchanged(view,[&]{deliver(view,"recipe-report");});fill(view,expected,false);deliver(view,"recipe-report");check(view.task()->view().phase==Phase::Release&&view.task()->view().pendingOutcome==Outcome::RetryRequested&&view.task()->diagnosis(),"false physical report should require manual retry/release");check(control<juce::TextEditor>(view,"recipe-history").getText().contains("was reported false")&&!view.task()->view().observedPerformance,"human diagnosis missing or observed failure invented");unchanged(view,[&]{deliver(view,"recipe-release");});release(view);const auto history=view.retainedHistory().size();deliver(view,"recipe-again");check(view.retainedHistory().size()==history+1&&control<juce::ComboBox>(view,"recipe-start-stroke").getSelectedId()==0&&control<juce::TextEditor>(view,"recipe-remainder-plan").getText().isEmpty(),"fresh pass retained live report/default or lost history");
 select(view);deliver(view,"recipe-unknown");check(view.task()->view().phase==Phase::Release&&view.task()->view().pendingOutcome==Outcome::RetryRequested&&control<juce::TextEditor>(view,"recipe-history").getText().contains("reported uncertainty"),"uncertainty must be manual retry, not fabricated success");release(view);
 desktop::RecipeTaskView foreign;initialise(foreign,key);const auto foreignGesture=button(foreign,"recipe-choose").capture();unchanged(view,[&]{button(view,"recipe-choose").deliver(foreignGesture);});const auto count=view.retainedHistory().size();check(view.open(key)&&view.retainedHistory().size()==count,"opening a released task lost previous native history");unchanged(view,[&]{check(!view.open("foreign"),"untrusted key opened");});
 select(view);const auto stale=button(view,"recipe-report").capture();fill(view,view.task()->expectedReport());deliver(view,"recipe-report");unchanged(view,[&]{button(view,"recipe-report").deliver(stale);});deliver(view,"recipe-retry");release(view);check(view.task()->view().outcome==Outcome::RetryRequested,"retry outcome lost after release");
}
}
int main(int argc,char** argv){try{
 check(argc==2,"usage: recipe-view-check <snapshot-output-directory>");juce::ScopedJuceInitialiser_GUI gui;const juce::File output=juce::File::getCurrentWorkingDirectory().getChildFile(argv[1]);output.createDirectory();std::string call,recovery;
 for(const auto& key:keys()){
  const auto& d=definition(key);if(d.recipe()==Recipe::CallAnswer&&call.empty())call=key;if(d.recipe()==Recipe::RecoveryPair&&recovery.empty())recovery=key;
  for(int stroke:{1,2}){desktop::RecipeTaskView view;initialise(view,key);sourceFacts(view);menus(view);bounds(view);select(view,stroke);check(view.task()->selectedRequest()->find("start_stroke")->string()==(stroke==1?"D":"U"),"explicit pick mismatch");
   while(view.task()->view().phase==Phase::Steps){const auto before=view.task()->expectedReport();fill(view,before);bounds(view);deliver(view,"recipe-report");check(view.task()->history().back().reported==before,"UI report did not come from actual input");}
   check(view.task()->view().phase==Phase::Release&&view.task()->view().pendingOutcome==Outcome::UserReportedStepsFinished&&!view.task()->view().grantsCredit&&!view.task()->view().observedPerformance,"manual completed path claims performance or bypasses release");bounds(view);release(view);++paths;
  }
 }
 navigationCases(call);navigationCases(recovery);invalidCases(call);invalidCases(recovery);delayedMenus(recovery);
 desktop::RecipeTaskView a,b;initialise(a,call);select(a);initialise(b,recovery);screenshot(a,output,"call-answer-920x680.png");screenshot(b,output,"recovery-choice-920x680.png");
 std::cout<<"{\"result\":\"PASS\",\"rows\":17,\"ui_paths\":"<<paths<<",\"origin_menu_cases\":"<<menuOrigins<<",\"assertions\":"<<checks<<",\"refusal_checks\":"<<refusals<<",\"size\":[920,680],\"performance_observed\":false,\"runtime_admitted\":false,\"official_accepted\":false}\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
