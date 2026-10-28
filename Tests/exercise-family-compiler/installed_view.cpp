#include "desktop/ManualTaskView.hpp"
#include "tasks/InstalledManualTaskRegistry.hpp"
#include <iostream>
#include <stdexcept>
using namespace fathom;
namespace {
std::size_t assertions=0;
void check(bool value,const char* message){++assertions;if(!value)throw std::runtime_error(message);}
desktop::ManualTaskButton& button(desktop::ManualTaskView& view,const char* id){
 auto* result=dynamic_cast<desktop::ManualTaskButton*>(view.findChildWithID(juce::String::fromUTF8(id)));if(!result)throw std::runtime_error(std::string{"manual control missing: "}+id);++assertions;return *result;}
void deliver(desktop::ManualTaskButton& b){check(b.isEnabled(),"intended UI control must be enabled");b.deliver(b.capture());}
juce::String words(const json::Value& value){juce::String text;for(const auto& v:value.array()){if(text.isNotEmpty())text+=" ";text+=juce::String::fromUTF8(v.string().c_str());}return text;}
void fill(desktop::ManualTaskView& view,const json::Value& setup){
 const char* names[]={"root","quality","inversion","bass_degree","named_notes_low_to_high","named_degrees_low_to_high"};
 for(int n=0;n<6;++n){auto* field=dynamic_cast<juce::TextEditor*>(view.findChildWithID("manual-task-report-"+juce::String(n)));
  check(field&&field->getText().isEmpty(),"naming fields start blank");const auto& value=setup.object().at(names[n]);field->setText(n<4?juce::String(value.string()):words(value),false);}
 int toggles=0;for(int n=0;n<view.getNumChildComponents();++n)if(auto* t=dynamic_cast<juce::ToggleButton*>(view.getChildComponent(n))){check(!t->getToggleState(),"physical reports start unchecked");t->setToggleState(true,juce::dontSendNotification);++toggles;}
 check(toggles==4,"exact four explicit setup reports");
}
void visibleBounds(desktop::ManualTaskView& view){for(int n=0;n<view.getNumChildComponents();++n){auto* child=view.getChildComponent(n);if(child->isVisible())check(child->getHeight()>0&&child->getWidth()>0&&view.getLocalBounds().contains(child->getBounds()),"visible control clipped at supported window size");}}
void navigationBoundaries(const tasks::Definition& definition){
 for(const auto phase:{tasks::Phase::Setup,tasks::Phase::ManualSteps,tasks::Phase::Cues,tasks::Phase::Release}){
  desktop::ManualTaskView view;view.setSize(920,680);view.setVisible(true);check(view.open(definition),"navigation fixture open");
  int exits=0,stops=0,starts=0;view.onBack=[&]{++exits;return true;};view.onStopPulse=[&]{++stops;};
  view.onStartPulse=[&](int)->std::optional<desktop::MetronomeView::ManualPulseStart>{++starts;return std::nullopt;};
  if(phase==tasks::Phase::Cues){
   auto* bpm=dynamic_cast<juce::TextEditor*>(view.findChildWithID("manual-task-bpm"));check(bool(bpm),"paced BPM field");bpm->setText("90",false);
   deliver(button(view,"manual-task-fathom-even-pulse-guide"));
  }else deliver(button(view,"manual-task-source-order-—-manual-reports"));
  if(phase!=tasks::Phase::Setup){
   if(definition.reportContract())fill(view,definition.reportContract()->setup);
   deliver(button(view,"manual-task-ready-after-setup"));
   if(phase==tasks::Phase::Release)deliver(button(view,"manual-task-cancel-current-pass"));
  }
  check(view.adapter()->view().phase==phase,"navigation starts in requested duty phase");
  const auto original=view.adapter()->capture(tasks::IntentKind::Ready);const auto history=view.adapter()->history().size();
  check(!view.open(definition),"active task replacement must refuse");
  check(view.adapter()->capture(tasks::IntentKind::Ready).instance==original.instance&&view.adapter()->history().size()==history,"refused open retains owner and report history");
  auto* back=dynamic_cast<juce::Button*>(view.findChildWithID("manual-task-back"));check(bool(back),"Back control exists");const auto previousStops=stops;back->onClick();
  check(exits==0&&stops==previousStops+1&&view.adapter()->view().phase==tasks::Phase::Release&&!view.pulsePreparing(),"active Back retains visible release and stops preparation");
  const auto releaseOwner=view.adapter()->capture(tasks::IntentKind::Release);const auto releaseHistory=view.adapter()->history().size();
  check(!view.prepareForNavigation(),"host navigation must also retain release");
  check(view.adapter()->capture(tasks::IntentKind::Release).revision==releaseOwner.revision&&view.adapter()->history().size()==releaseHistory,"repeated refused leave retains release owner and history");
  const auto after=view.adapter()->history().size();button(view,"manual-task-ready-after-setup").deliver(original);
  check(view.adapter()->view().phase==tasks::Phase::Release&&view.adapter()->history().size()==after,"delayed Ready cannot escape release");
  view.service();check(starts==0,"interrupted preparation must not start a later clock");
  deliver(button(view,"manual-task-i-physically-released-the-shape"));check(view.adapter()->view().phase==tasks::Phase::Closed,"physical release closes interrupted pass");
  const auto staleAgain=button(view,"manual-task-begin-another-pass").capture();back->onClick();
  check(exits==1&&view.adapter()->view().phase==tasks::Phase::Closed,"released task may leave");
  const auto closedHistory=view.adapter()->history().size();button(view,"manual-task-begin-another-pass").deliver(staleAgain);
  check(view.adapter()->view().phase==tasks::Phase::Closed&&view.adapter()->history().size()==closedHistory,"navigation fences closed-pass input");
  check(view.open(definition)&&view.adapter()->view().phase==tasks::Phase::Choose,"released source may open a fresh pass");
 }
 desktop::ManualTaskView choose;check(choose.open(definition),"safe Choose open");
 const auto stale=button(choose,"manual-task-source-order-—-manual-reports").capture();int exits=0;choose.onBack=[&]{++exits;return true;};
 dynamic_cast<juce::Button*>(choose.findChildWithID("manual-task-back"))->onClick();
 check(exits==1&&choose.adapter()->view().phase==tasks::Phase::Choose,"unstarted Choose may leave");
 button(choose,"manual-task-source-order-—-manual-reports").deliver(stale);
 check(choose.adapter()->view().phase==tasks::Phase::Choose&&choose.adapter()->history().size()==1,"safe navigation fences old Choose input");
}
}
int main(int argc,char** argv){try{
 check(argc==2,"usage: view-check <installed-resource-directory>");juce::ScopedJuceInitialiser_GUI gui;
 auto registry=tasks::InstalledManualTaskRegistry::load(std::filesystem::path{argv[1]}/"typed-manual-tasks-v1");check(registry.error().empty(),"installed resource registry unavailable");
 auto typed=registry.definition(tasks::compiledFamilyKeys().front().substr(std::string{"exercise-completeness-r01/"}.size()));check(bool(typed),"navigation typed fixture");navigationBoundaries(*typed);
 auto legacy=registry.definition("level053/moduleb/p003-t1-r1-c2/cmajrp");check(bool(legacy),"navigation legacy fixture");navigationBoundaries(*legacy);
 for(const auto& key:tasks::compiledFamilyKeys()){
  auto definition=registry.definition(key.substr(std::string{"exercise-completeness-r01/"}.size()));check(bool(definition),"compiled source route missing");
  desktop::ManualTaskView view;view.setSize(920,680);view.setVisible(true);check(view.open(*definition),"source view open");
  auto& source=button(view,"manual-task-source-order-—-manual-reports");deliver(source);
  check(view.adapter()->view().phase==tasks::Phase::Setup,"source setup visible");visibleBounds(view);
  auto* setup=dynamic_cast<juce::TextEditor*>(view.findChildWithID("manual-task-setup"));check(setup&&setup->getText().contains("Source suggested fingers")&&setup->getText().contains("Written low/middle/high"),"source facts visible");
  const auto& reports=definition->reportContract()->setup.object();
  for(std::size_t n=0;n<3;++n){const auto literal=reports.at("named_notes_low_to_high").array()[n].string()+" ("+reports.at("named_degrees_low_to_high").array()[n].string()+")";
   check(setup->getText().contains(juce::String::fromUTF8(literal.c_str())),"exact printed note/degree visible");}
  fill(view,definition->reportContract()->setup);deliver(button(view,"manual-task-ready-after-setup"));
  check(view.adapter()->view().phase==tasks::Phase::ManualSteps&&!view.pulsePreparing()&&!view.clockActive(),"source path needs no shared clock");
  for(int n=0;n<4;++n)deliver(button(view,"manual-task-i-did-the-displayed-step"));
  check(view.adapter()->view().phase==tasks::Phase::Release,"release boundary visible");visibleBounds(view);
  deliver(button(view,"manual-task-i-physically-released-the-shape"));check(view.adapter()->view().phase==tasks::Phase::Closed,"explicit release closes UI path");
  auto history=view.adapter()->history().size();deliver(button(view,"manual-task-begin-another-pass"));
  check(view.adapter()->view().phase==tasks::Phase::Choose&&view.adapter()->history().size()==history+1,"another pass retains history");
  const auto chooseHistory=view.adapter()->history().size();
  check(view.prepareForNavigation()&&view.adapter()->view().phase==tasks::Phase::Choose&&view.adapter()->history().size()==chooseHistory+1,"safe settings detour retains prior pass history");
  check(view.prepareForNavigation()&&view.adapter()->history().size()==chooseHistory+1,"safe navigation preparation is idempotent");
  for(int n=0;n<6;++n){auto* field=dynamic_cast<juce::TextEditor*>(view.findChildWithID("manual-task-report-"+juce::String(n)));check(field&&field->getText().isEmpty(),"another pass clears actual naming report");}
 }
 std::cout<<"{\"result\":\"PASS\",\"rows\":167,\"assertions\":"<<assertions<<",\"ui_delivery_paths\":true,\"practice_admitted\":false,\"official_accepted\":false}\n";return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
