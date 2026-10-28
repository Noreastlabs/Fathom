#pragma once
// Test-only retained real desktop/Store/output callbacks; no campaign entry points.
// Actual desktop/Store/adapter paths; only capability and device-open leaves are synthetic.
#include "platform/AudioOutputMac.mm"
#include "desktop/HomeView.hpp"
#include <fstream>
namespace fathom::desktop {
struct PracticeViewTestAccess {
 static bool canLeave(const PracticeView& v){return v.canReturn();}
 static void tick(PracticeView& v){v.timerCallback();}
 static void halt(PracticeView& v){v.stopTimer();}
 static platform::AudioOutputMac& output(PracticeView& v){return v.output_;}
 static bool posted(const PracticeView& v){return v.returnPosted_;}
 static bool intent(const PracticeView& v){return v.returnAfterSave_;}
 static bool panel(const PracticeView& v){return v.returnPanel_;}
 static void queueReturn(PracticeView& v){v.requestBack();}
 static std::uint64_t stopStamp(const PracticeView& v){return v.lastStopRequestNs_;}
 static std::string assessment(const PracticeView& v){return v.assessment_.getText().toStdString();}
};
struct MetronomeViewTestAccess {
 static std::string pending(const MetronomeView&v){return v.pendingOperation_;}
 static std::string pendingBytes(const MetronomeView&v){return v.pendingBytes_;}
 static std::string status(const MetronomeView&v){return v.preferencePrimaryText().toStdString();}
 static void edit(MetronomeView&v,const char*value){v.tempo_.setText(value,false);}
 static auto&last(MetronomeView&v){return v.saveLast_;}
 static void halt(MetronomeView& v){v.stopTimer();}
 static platform::AudioOutputMac& output(MetronomeView& v){return v.output_;}
 static std::string statusText(const MetronomeView& v){return v.status_.getText().toStdString();}
};
struct SharedAudioViewTestAccess {
 static void finishSetup(HomeView&h){h.finishSetup();}
 static OriginalActivityRecovery& originalRecovery(HomeView& h){return h.originalRecovery_;}

 static std::string homeRouteStatus(const HomeView& h){return h.homeRouteStatus_.getText().toStdString();}
 static bool setupRestoreGatesReady(const HomeView& h){return !h.setupPreferences_.inFlight()&&!h.presentation_.inFlight()&&h.setupPreferences_.ready()&&h.presentationReadyForSetup()&&h.presentationStoppedAndResolved();}
 static bool setupRestorePending(const HomeView& h){return h.setupRestorePending_;}
 static bool setupReadersSettled(const HomeView& h){return !h.setupPreferences_.pending()&&!h.presentation_.pending()&&!h.metronomeView.preferenceInFlight()&&!h.learnFuture_&&h.learnMutation_==HomeView::LearnMutation::None&&!h.progressView.busy();}
 static bool originalPreferencesSettled(const HomeView& h){return !h.setupRestorePending_&&!h.setupPreferences_.pending()&&!h.presentation_.pending()&&!h.metronomeView.preferenceInFlight();}
 static bool originalAcceptedReadersSettled(const HomeView& h){return originalPreferencesSettled(h)&&!h.learnFuture_&&h.learnMutation_==HomeView::LearnMutation::None&&!h.progressView.busy();}

 static bool startupReadSettled(const HomeView& h){return !h.learnFuture_&&h.learnMutation_==HomeView::LearnMutation::None;}

 static std::string navigationFacts(const HomeView& h){return "page="+std::to_string(static_cast<int>(h.page_))+" learnFuture="+std::to_string(bool(h.learnFuture_))+" learnMutation="+std::to_string(static_cast<int>(h.learnMutation_))+" queue="+std::to_string(bool(h.learnQueue_))+" suite="+std::to_string(bool(h.learnSuite_))+" suiteReviewed="+std::to_string(h.suiteReviewSaved_)+" practiceRelease="+std::to_string(h.practiceView->audioCanRelease())+" metronomeRelease="+std::to_string(h.metronomeView.audioCanRelease())+" referenceRelease="+std::to_string(h.referenceView.audioCanRelease())+" rhythmRelease="+std::to_string(h.scheduleView.audioCanRelease())+" metroPrefsInFlight="+std::to_string(h.metronomeView.preferenceInFlight())+" metroPrefsPending="+std::to_string(h.metronomeView.preferencesPending());}

 static LessonView& lessons(HomeView& h){return h.lessonView;}
 static ProgressView& progress(HomeView& h){return h.progressView;}
 static GuitarSetupView& setup(HomeView& h){return h.setup;}
 static PracticeView& practice(HomeView& h){return *h.practiceView;}
 static GuidedSessionView& guided(HomeView& h){return h.guidedView;}
 static MetronomeView& metronome(HomeView& h){return h.metronomeView;}
 static FreeplayView& freeplay(HomeView& h){return h.freeplayView;}
 static ReferenceView& reference(HomeView& h){return h.referenceView;}
 static SchedulerView& rhythm(HomeView& h){return h.scheduleView;}
 static AudioOutputView& settings(HomeView& h){return h.outputView;}
 static void halt(HomeView& h){h.stopTimer();h.progressView.stopTimer();h.outputView.stopTimer();PracticeViewTestAccess::halt(*h.practiceView);MetronomeViewTestAccess::halt(h.metronomeView);h.referenceView.stopTimer();h.scheduleView.stopTimer();h.freeplayView.stopTimer();}
 static void tick(HomeView& h){h.progressView.service();h.metronomeView.service();h.referenceView.timerCallback();h.scheduleView.timerCallback();PracticeViewTestAccess::tick(*h.practiceView);h.freeplayView.timerCallback();h.timerCallback();h.outputView.timerCallback();}
 static void inactiveFirst(HomeView& h){h.metronomeView.service();h.referenceView.timerCallback();PracticeViewTestAccess::tick(*h.practiceView);}
 static platform::AudioOutputMac& output(HomeView& h){switch(h.audio_.active()){case SharedAudioSettings::Consumer::Practice:return PracticeViewTestAccess::output(*h.practiceView);case SharedAudioSettings::Consumer::Metronome:return MetronomeViewTestAccess::output(h.metronomeView);case SharedAudioSettings::Consumer::Reference:return h.referenceView.output_;case SharedAudioSettings::Consumer::Rhythm:return h.scheduleView.output;case SharedAudioSettings::Consumer::Count:break;}throw std::runtime_error("Invalid consumer");}
 static std::size_t visiblePages(HomeView& h){std::size_t n{};for(auto* c:std::initializer_list<juce::Component*>{&h.setup,&h.outputView,&h.scheduleView,&h.referenceView,h.practiceView.get(),&h.metronomeView,&h.lessonView,&h.progressView,&h.freeplayView})n+=c->isVisible();return n;}
 static bool pollers(HomeView& h){int n=0;n+=h.practiceView->audioPolling_;n+=h.metronomeView.audioPolling_;n+=h.referenceView.audioPolling_;n+=h.scheduleView.audioPolling_;return n==1;}
 static const scheduler::StreamView& rhythmFinal(HomeView& h){return h.scheduleView.retainedTimeline;}
 static const output::Snapshot& rhythmOutput(HomeView& h){return h.scheduleView.retainedOutput;}
 static AudioEndpoint practiceEndpoint(HomeView& h){return audioEndpoint(*h.practiceView,"Old Practice");}
};
}

#include "practice_capture_fixtures.hpp"
#include <atomic>
#include <mutex>
#include <iostream>
#include <sstream>
#include <array>
#include <iomanip>
using namespace fathom;
using H=desktop::HomeView;
using A=desktop::SharedAudioViewTestAccess;
using P=desktop::PracticeViewTestAccess;
namespace {
int nativeOpens{},connections{},maxClaims{};std::vector<std::string> ioLog;
platform::OutputCapability capability{true,87,44100,512,2,32,2048,"synthetic:direct","Software fixture; not hardware","",{{44100,44100}}};
struct SoftwareDevice final:juce::AudioIODevice {
 SoftwareDevice():AudioIODevice("Software fixture","test"){}
 juce::StringArray getOutputChannelNames()override{return {"L","R"};}juce::StringArray getInputChannelNames()override{return {};}
 juce::Array<double> getAvailableSampleRates()override{return {44100};}juce::Array<int> getAvailableBufferSizes()override{return {256};}
 int getDefaultBufferSize()override{return 256;}juce::String open(const juce::BigInteger&,const juce::BigInteger&,double,int)override{++nativeOpens;return "Forbidden";}
 void close()override{ioLog.push_back("close");}bool isOpen()override{return true;}void start(juce::AudioIODeviceCallback*)override{++nativeOpens;}void stop()override{ioLog.push_back("stop");}bool isPlaying()override{return false;}juce::String getLastError()override{return {};}
 int getCurrentBufferSizeSamples()override{return 256;}double getCurrentSampleRate()override{return 44100;}int getCurrentBitDepth()override{return 32;}
 juce::BigInteger getActiveOutputChannels()const override{juce::BigInteger b;b.setRange(0,2,true);return b;}juce::BigInteger getActiveInputChannels()const override{return {};}
 int getOutputLatencyInSamples()override{return 0;}int getInputLatencyInSamples()override{return 0;}
 };
void pump(){@autoreleasepool {CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.001,true);if(auto* e=[NSApp nextEventMatchingMask:NSEventMaskAny untilDate:[NSDate dateWithTimeIntervalSinceNow:0.001] inMode:NSDefaultRunLoopMode dequeue:YES])[NSApp sendEvent:e];}}
void activate(juce::Button& button){struct Listener final:juce::Button::Listener{bool delivered{};void buttonClicked(juce::Button*)override{delivered=true;}} listener;button.addListener(&listener);button.triggerClick();const auto until=capture_fixture::now()+2000;while(!listener.delivered&&capture_fixture::now()<until)pump();button.removeListener(&listener);if(!listener.delivered)throw std::runtime_error("button dispatch watchdog");}
[[maybe_unused]] void marker(){bool reached=false;juce::MessageManager::callAsync([&]{reached=true;});const auto until=capture_fixture::now()+2000;while(!reached&&capture_fixture::now()<until)pump();if(!reached)throw std::runtime_error("marker watchdog");}
[[maybe_unused]] juce::Button& button(juce::Component& c,const std::string& name){for(auto* child:c.getChildren()){if(auto* b=dynamic_cast<juce::Button*>(child);b&&b->getButtonText().toStdString()==name)return *b;}throw std::runtime_error("Missing button "+name);}
// Historical campaigns request these route names; assertions below test the
// current visible controls. A removed duplicate is never dispatched directly.
void click(juce::Component& c,const std::string& name){
 auto actual=name;
 if(dynamic_cast<desktop::HomeView*>(&c)){
  if(name=="Start learning"||name=="Continue selected case"||name=="Practice (choose in Learn)")actual="Learn";
  else if(name=="Review selected case")actual="Exercise details";
 }
 if(name=="Back"&&dynamic_cast<desktop::LessonView*>(&c)){
  // The retained case Back now names its destination; hidden case controls
  // must never substitute for the visible source-hierarchy Back.
  if(auto* back=dynamic_cast<juce::Button*>(c.findChildWithID("back"));back&&back->isVisible())actual=back->getButtonText().toStdString();
 }
 const auto visibleButton=[&](auto&& self,juce::Component& root)->juce::Button*{
  if(auto* candidate=dynamic_cast<juce::Button*>(&root);candidate&&candidate->isVisible()&&candidate->getButtonText().toStdString()==actual)return candidate;
  for(auto* child:root.getChildren())if(child->isVisible())if(auto* found=self(self,*child))return found;
  return nullptr;
 };
 auto* b=visibleButton(visibleButton,c);if(!b||!b->isEnabled()||!c.getLocalBounds().contains(b->getBounds()))throw std::runtime_error("Button not usable "+actual);activate(*b);
}

[[maybe_unused]] bool equal(const output::MixSettings& a,const output::MixSettings& b){return a.master==b.master&&a.bus==b.bus&&a.masterMute==b.masterMute&&a.muteMask==b.muteMask&&a.soloAB==b.soloAB;}
// Measure the actual caption through its drawing font and text insets, independently
// of the production row's weights or target pixel widths.
[[maybe_unused]] bool stopCaptionFits(desktop::PracticeView& view){
 auto* stop=dynamic_cast<juce::TextButton*>(view.findChildWithID("practice-stop"));
 if(!stop||!stop->isVisible()||!stop->isEnabled()||stop->getButtonText()!="Stop & review result")return false;
 const auto font=stop->getLookAndFeel().getTextButtonFont(*stop,stop->getHeight());
 const int corner=std::min(stop->getHeight(),stop->getWidth())/2;
 const int fontInset=juce::roundToInt(font.getHeight()*0.6f);
 const int left=std::min(fontInset,2+corner/(stop->isConnectedOnLeft()?4:2));
 const int right=std::min(fontInset,2+corner/(stop->isConnectedOnRight()?4:2));
 return juce::GlyphArrangement::getStringWidth(font,stop->getButtonText())<=stop->getWidth()-left-right;
}
[[maybe_unused]] bool transportContainedAndSeparate(desktop::PracticeView& view){
 std::vector<juce::Component*> controls;
 for(const auto* id:{"practice-audio-settings","practice-start","practice-pause","practice-resume","practice-stop","lesson-tempo","scheduled-passes"}){
  auto* control=view.findChildWithID(id);if(!control)return false;
  if(control->isVisible())controls.push_back(control);
 }
 for(auto* child:view.getChildren())if(auto* setup=dynamic_cast<juce::TextButton*>(child);setup&&setup->isVisible()&&(setup->getButtonText()=="Show setup details"||setup->getButtonText()=="Hide setup details"))controls.push_back(setup);
 for(std::size_t i=0;i<controls.size();++i){
  const auto bounds=controls[i]->getBounds();if(bounds.isEmpty()||!view.getLocalBounds().contains(bounds))return false;
  for(std::size_t j=0;j<i;++j)if(bounds.intersects(controls[j]->getBounds()))return false;
 }
 return !controls.empty();
}
}
namespace fathom::platform {
struct OutputTestAccess {
 inline static bool deferObservation=false; // Exercise asynchronous native handoff timing with software I/O only.
 static bool attach(AudioOutputMac& o,const OutputCapability& c,output::Format format,void* context,OutputObserver observer,ScheduledRender render){
  auto& p=*o.p_;bool free=false;if(!hub.claimed.compare_exchange_strong(free,true))return false;
  output::Observation discard;while(p.queries.pop(discard)){} output::CachedAnnouncement old;while(p.announcements.pop(old)){} Control command;while(p.normal.pop(command)){}while(p.urgent.pop(command)){} p.latestQuery={};p.firstSilentCallbackNs=0;p.silenceOwner={};p.lastError.clear();p.expectedStop.store(false);hub.expectedIO.store(0);
  p.claimed=true;p.epoch=epochCounter.fetch_add(1)+1;p.requested=format;p.quiescent=true;p.device=std::make_unique<SoftwareDevice>();p.context=context;p.observer=observer;p.scheduled=render;p.capability=c;
  nativeSequence=1;hub.epoch.store(p.epoch);hub.faultWord.store(tagged(p.epoch,0));hub.ioWord.store(tagged(p.epoch,c.object));hub.armed.store(false);hub.frames.store(format.frames);
  if(!p.life.configure({static_cast<std::uint64_t>(p.epoch),1,format,c.object})||!p.life.announce({static_cast<std::uint64_t>(p.epoch),2,format}))throw std::runtime_error("Synthetic configure");
  p.latestQuery={static_cast<std::uint64_t>(p.epoch),1,4,3,format,format.frames,c.object,c.object,c.object,c.rate,c.physicalFrames,true,true,true,true,true};
  if(!deferObservation)p.life.observe(p.latestQuery);p.view.lifecycle=p.life.snapshot();++connections;maxClaims=std::max(maxClaims,int(hub.claimed));ioLog.push_back("connect:"+std::to_string(p.epoch)+":"+(context?"provider":"NULL"));return context&&observer&&render;
 }
 static float block(AudioOutputMac& o){auto& p=*o.p_;if(!p.device)return 0;nativeEpoch=p.epoch;nativeObject=p.capability.object;nativeFrames=p.requested.frames;++nativeSequence;std::array<float,256> l{},r{};float* channels[]{l.data(),r.data()};juce::AudioIODeviceCallbackContext context{};p.audioDeviceIOCallbackWithContext(nullptr,0,channels,2,256,context);float peak{};for(auto f:l)peak=std::max(peak,std::abs(f));return peak;}
 static void queued(AudioOutputMac& o,bool queued){o.p_->quiescent=!queued;}
 static void observedFrames(AudioOutputMac& o,std::uint32_t frames){o.p_->view.lifecycle.observation.physicalFrames=frames;}
 static void event(NativeEvent e){emit(e);}
 static bool consume(NativeEvent& e){return hub.events.pop(e);}
 static void faulted(AudioOutputMac& o){o.p_->life.invalidate(o.p_->epoch,output::Fault::Backend,10,0);o.p_->view.lifecycle=o.p_->life.snapshot();}
};
}
namespace fathom::desktop {
platform::OutputCapability settingsOutputCapability(){return capability;}
bool connectSettingsOutput(platform::AudioOutputMac& output,const platform::OutputCapability& cap,output::Format format,void* context,platform::OutputObserver observer,platform::ScheduledRender render){return platform::OutputTestAccess::attach(output,cap,format,context,observer,render);}
}

#include "desktop/LocalProfile.hpp"
namespace fathom::desktop {
struct LearnNavigationTestAccess { static bool originalDiscoverySettled(const HomeView& home){return !home.learnFuture_&&home.learnMutation_==HomeView::LearnMutation::None;} };
}
namespace {
juce::ComboBox& combo(desktop::LessonView& v,const char* id){auto* c=dynamic_cast<juce::ComboBox*>(v.findChildWithID(id));if(!c)throw std::runtime_error("Missing combo");return *c;}
[[maybe_unused]] juce::TextEditor& tempo(desktop::LessonView& v){auto* c=dynamic_cast<juce::TextEditor*>(v.findChildWithID("selected-tempo"));if(!c)throw std::runtime_error("Missing tempo");return *c;}
void choose(desktop::LessonView& v,const std::string& item,const std::string& variant){
 const auto& ls=v.catalog()->lessons();auto l=std::find_if(ls.begin(),ls.end(),[&](const auto& x){return x.id==item;});if(l==ls.end())throw std::runtime_error("Fixture item absent");
 combo(v,"lessons").setSelectedItemIndex(static_cast<int>(l-ls.begin()),juce::sendNotificationSync);
 auto it=std::find_if(l->variants.begin(),l->variants.end(),[&](const auto& x){return x.id==variant;});if(it==l->variants.end())throw std::runtime_error("Fixture variant absent");combo(v,"variants").setSelectedItemIndex(static_cast<int>(it-l->variants.begin()),juce::sendNotificationSync);
}
}
