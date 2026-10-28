#pragma once
#include "platform/AudioOutputMac.mm"
#include <array>
#include <vector>
#include <string>
#include <stdexcept>
using namespace fathom;
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
 static void cleanupFailure(AudioOutputMac& o,bool value){o.p_->cleanupFailed=value;o.p_->view.cleanupFailed=value;}
 static void faulted(AudioOutputMac& o){o.p_->life.invalidate(o.p_->epoch,output::Fault::Backend,10,0);o.p_->view.lifecycle=o.p_->life.snapshot();}
};
}
namespace fathom::desktop {
platform::OutputCapability settingsOutputCapability(){return capability;}
bool connectSettingsOutput(platform::AudioOutputMac& output,const platform::OutputCapability& cap,output::Format format,void* context,platform::OutputObserver observer,platform::ScheduledRender render){return platform::OutputTestAccess::attach(output,cap,format,context,observer,render);}
}
