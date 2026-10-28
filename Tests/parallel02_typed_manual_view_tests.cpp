#include "desktop/ManualTaskView.hpp"
#include "tasks/InstalledManualTaskRegistry.hpp"
#include <iostream>
#include <stdexcept>
#include <thread>
int main(int argc,char** argv){
 try{
  if(argc!=2)throw std::runtime_error("usage: view-test <typed-task-resource-directory>");
  juce::ScopedJuceInitialiser_GUI juce;
  auto registry=fathom::tasks::InstalledManualTaskRegistry::load(argv[1]);
  auto def=registry.definition("level053/moduleb/p003-t1-r1-c2/cmajrp");
  if(!def)throw std::runtime_error("reviewed definition unavailable");
  fathom::desktop::ManualTaskView view;view.setSize(920,680);view.setVisible(true);
  if(!view.open(*def)||!view.findChildWithID("manual-task-setup")||!view.findChildWithID("manual-task-setup-accessible")||!view.findChildWithID("manual-task-release")||
     !view.findChildWithID("manual-task-bpm")||!view.findChildWithID("manual-task-back"))
      throw std::runtime_error("AX controls missing");
  auto* setup=dynamic_cast<juce::TextEditor*>(view.findChildWithID("manual-task-setup"));
  auto* setupAx=dynamic_cast<juce::Label*>(view.findChildWithID("manual-task-setup-accessible"));
  auto* release=dynamic_cast<juce::Label*>(view.findChildWithID("manual-task-release"));
  if(!setup||!setup->getText().containsIgnoreCase("Mute")||!setupAx||!setupAx->getText().containsIgnoreCase("Mute")||!release||release->getTitle().isEmpty())
      throw std::runtime_error("authored setup/release inaccessible");
  auto* bpm=dynamic_cast<juce::TextEditor*>(view.findChildWithID("manual-task-bpm"));
  auto* paced=dynamic_cast<fathom::desktop::ManualTaskButton*>(view.findChildWithID("manual-task-fathom-even-pulse-guide"));
  auto* ready=dynamic_cast<fathom::desktop::ManualTaskButton*>(view.findChildWithID("manual-task-ready-after-setup"));
  auto* status=dynamic_cast<juce::Label*>(view.findChildWithID("manual-task-status"));
  if(!bpm||!paced||!ready||!status)throw std::runtime_error("paced controls missing");
  bpm->setText("60",false);paced->onClick();
  if(view.adapter()->view().phase!=fathom::tasks::Phase::Setup||view.adapter()->view().selectedBpm!=60)
      throw std::runtime_error("explicit paced selection missing");
  bpm->setText("120",false);ready->onClick();
  if(view.adapter()->view().phase!=fathom::tasks::Phase::Setup||view.pulsePreparing()||view.clockActive()||
     !status->getText().containsIgnoreCase("reselect"))
      throw std::runtime_error("visible 60-to-120 Ready must refuse in Setup without pulse");
  std::this_thread::sleep_for(std::chrono::milliseconds(400));paced->onClick();
  std::this_thread::sleep_for(std::chrono::milliseconds(400));ready->onClick();
  if(view.adapter()->view().phase!=fathom::tasks::Phase::Cues||!view.pulsePreparing()||view.adapter()->view().selectedBpm!=120)
      throw std::runtime_error("reselected visible 120 must enter paced cues");
  int requestedBpm=0;
  view.onStartPulse=[&](int value)->std::optional<fathom::desktop::MetronomeView::ManualPulseStart>{requestedBpm=value;return std::nullopt;};
  view.service();
  if(requestedBpm!=120)throw std::runtime_error("shared clock requested at stale BPM");
  std::cout<<"PASS typed manual view AX setup/release and Ready-time visible BPM controls\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}
