#include "core/AudioOutputLifecycle.hpp"
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
using namespace fathom::output;
namespace {
int checks{};
void check(bool ok,const char* message){++checks;if(!ok){std::cerr<<"FAIL "<<message<<'\n';std::exit(1);}}
Owner owner(std::uint64_t epoch=1){Owner o;o.id[6]=0x40;o.id[8]=0x80;o.id[15]=9;o.generation=1;o.epoch=epoch;return o;}
Request request(std::uint64_t epoch=1){return {epoch,10,{44100,256},1};}
Observation observation(std::uint64_t epoch=1){Observation o;o.epoch=epoch;o.callbackSequence=1;o.callbackStampNs=30;o.queryStampNs=21;o.queriedIO={44100,256};o.callbackFrames=256;o.nativeIOObject=2;o.queriedIOObject=2;o.physicalObject=1;o.physicalRate=44100;o.physicalFrames=512;o.physicalKnown=o.ioKnown=o.routeKnown=o.selectedInFullRoute=o.selectedInActiveRoute=true;return o;}
void ready(Lifecycle& l,std::uint64_t epoch=1){check(l.configure(request(epoch)),"configure");check(l.announce({epoch,20,{44100,256}}),"cached announcement");check(l.observe(observation(epoch)),"native observation physical512/IO256");check(l.acknowledge(epoch,1),"matching explicit acknowledgement");}
void startup(){
 Lifecycle l;check(!l.renderAllowed()&&l.snapshot().state==State::Closed,"initial no output");check(!l.start(owner()),"no unconfigured start");
 auto r=request();r.epoch=0;check(!l.configure(r),"zero epoch refusal");r=request();r.format.frames=0;check(!l.configure(r),"zero buffer refusal");r=request();r.selectedPhysical=0;check(!l.configure(r),"missing selected physical");
 check(l.configure(request()),"explicit request");check(!l.start(owner())&&!l.acknowledge(1,1),"no request-only ack/start");
 check(l.announce({1,20,{44100,256}})&&!l.renderAllowed(),"cached response remains silent");
 auto o=observation();o.physicalKnown=false;check(!l.observe(o)&&l.snapshot().state==State::Awaiting,"incomplete first observation awaits silently");
 check(l.observe(observation())&&l.snapshot().state==State::Observed,"silent observed token");
 o=observation();o.callbackSequence=2;o.callbackStampNs=40;check(l.observe(o)&&l.snapshot().observationToken==1,"stable token through later callbacks");
 check(!l.acknowledge(1,2)&&!l.acknowledge(2,1)&&!l.start(owner()),"wrong ack/epoch no start");
 check(l.acknowledge(1,1)&&!l.renderAllowed()&&!l.acknowledge(1,1),"ack ready not playing and duplicate refused");
 check(l.start(owner())&&l.renderAllowed()&&!l.start(owner()),"one explicit start");
 check(!l.submitted(owner(),1,256)&&!l.submitted(owner(),2,512)&&l.submitted(owner(),2,256)&&!l.submitted(owner(),2,256)&&!l.snapshot().hasConfirmation,"submitted output not confirmed");
 check(l.confirm(owner(),128)&&!l.confirm(owner(),257)&&!l.confirm(owner(),127),"separate bounded monotonic confirmation");
 auto wrong=owner();wrong.generation++;check(!l.pause(wrong,50,512)&&!l.stop(wrong,50,512)&&!l.confirm(wrong,256),"stale generation refuses");
 check(l.pause(owner(),50,512)&&!l.renderAllowed()&&!l.snapshot().pendingOutcome,"pause retains owned unfinished traversal");
 check(!l.submitted(owner(),2,256)&&!l.configure(request(2))&&!l.close(),"pause cannot fabricate frames/configure/loseowner");
 auto resumed=owner();resumed.generation=2;
 check(!l.resume(owner(),resumed)&&!l.acknowledgePause(wrong),"resume waits for retained original paused segment");
 check(l.acknowledgePause(owner())&&l.confirm(owner(),256)&&!l.resume(owner(),resumed),"changed paused confirmation invalidates retained snapshot ack");
 check(l.acknowledgePause(owner())&&l.confirm(owner(),256)&&!l.resume(owner(),owner())&&l.resume(owner(),resumed),"duplicate confirmation stays idempotent; fresh generation preserves UUID");
 o=observation();o.callbackSequence=3;o.callbackStampNs=55;check(l.observe(o),"new resumed callback observation");
 check(!l.submitted(owner(),3,256)&&l.submitted(resumed,3,256)&&!l.submitted(resumed,3,256)&&!l.submitted(resumed,4,256),"current generation exact unique observed submission");
 check(!l.invalidateOwner(owner(),Fault::Render,59,999)&&l.renderAllowed(),"delayed owner-specific fault cannot stop resumed generation");
 check(l.stop(resumed,60,512)&&!l.renderAllowed()&&l.snapshot().pendingOutcome,"final stop retains unresolved owner");
 auto s=l.snapshot();check(s.submittedFrames==256&&!s.hasConfirmation&&s.uncertainThrough==512&&s.requestedStopNs==60,"requested confirmed uncertain facts distinct");
 check(l.stop(resumed,90,900)&&l.snapshot().uncertainThrough==512,"duplicate stop leaves sealed terminal facts");
 check(!l.resume(owner(),owner())&&!l.configure(request(2))&&!l.start(owner())&&!l.close(),"unresolved cannot reopen again or resume");
 check(!l.resolveOutcome(owner())&&l.resolveOutcome(resumed)&&!l.renderAllowed(),"explicit coordinator original-owner resolution not autoplay");
 check(l.close()&&!l.configure(request())&&l.configure(request(2))&&!l.renderAllowed(),"reopen fresh epoch remains stopped");
}
void faults(){
 for(int f=1;f<=static_cast<int>(Fault::InvalidObservation);++f){
  Lifecycle l;ready(l);l.start(owner());l.submitted(owner(),1,256);
  check(l.invalidate(1,static_cast<Fault>(f),50,512)&&l.snapshot().state==State::Fault&&!l.renderAllowed(),"fault stops output");
  auto o=observation();o.callbackSequence=2;o.callbackStampNs=60;check(!l.observe(o)&&!l.acknowledge(1,1)&&!l.resume(owner(),owner()),"matching later callback cannot heal fault");
  check(l.snapshot().pendingOutcome&&l.snapshot().owner==owner()&&!l.configure(request(2)),"fault retains outcome and blocks replacement");
  check(l.resolveOutcome(owner())&&l.snapshot().state==State::Fault&&!l.renderAllowed(),"resolution keeps explicit recovery required");
  ready(l,2);check(l.start(owner(2)),"explicit newepoch recovery Start");
  check(!l.invalidate(1,Fault::DeviceLost,100,999)&&!l.announce({1,100,{48000,256}})&&!l.observe(observation()),"old epoch evidence cannot affect new owner");
  check(l.renderAllowed()&&l.snapshot().owner==owner(2),"current owner survives stale events");
 }
 Lifecycle l;ready(l);check(!l.invalidate(1,Fault::None,40,0)&&!l.invalidate(1,static_cast<Fault>(99),40,0),"unknown/no fault refuses");
 check(l.announce({1,40,{44100,256}})==false&&l.snapshot().fault==Fault::Restart,"duplicate registration invalidates");
 for(int i=0;i<11;++i){Lifecycle x;check(x.configure(request())&&x.announce({1,20,{44100,256}}),"format fixture setup");auto o=observation();
  if(i==0)o.callbackFrames=512;if(i==1)o.queriedIO.rate=48000;if(i==2)o.physicalRate=48000;if(i==3)o.physicalFrames=0;
  if(i==4)o.nativeIOObject=3;if(i==5)o.physicalObject=3;if(i==6)o.selectedInFullRoute=false;if(i==7)o.selectedInActiveRoute=false;
  if(i==8)o.callbackSequence=0;if(i==9)o.queryStampNs=31;if(i==10)o.callbackStampNs=19;
  check(!x.observe(o)&&x.snapshot().state==State::Fault&&!x.renderAllowed(),"known mismatch refuses and latches");
 }
 Lifecycle zero;ready(zero);zero.start(owner());zero.pause(owner(),0,0);zero.acknowledgePause(owner());auto next=owner();next.generation=2;check(zero.confirm(owner(),0)&&!zero.resume(owner(),next),"first zero confirmation is a new retained fact");check(zero.acknowledgePause(owner())&&zero.confirm(owner(),0)&&zero.resume(owner(),next),"duplicate zero confirmation permits acknowledged handoff");
 Lifecycle paused;ready(paused);paused.start(owner());paused.pause(owner(),500,0);paused.stop(owner(),900,0);check(paused.snapshot().firstSilenceNs==500&&paused.snapshot().requestedStopNs==900,"first silence and final stop requests retained separately");
 Lifecycle lost;ready(lost);lost.start(owner());auto o=observation();o.callbackSequence=2;o.callbackStampNs=40;o.routeKnown=false;
 check(!lost.observe(o)&&!lost.renderAllowed()&&lost.snapshot().state==State::Fault,"missing route proof after readiness stops output");
}
void mixer(){
 Mixer m;float out{};check(m.sample({1,1,1,1},out)&&std::abs(out-0.25f)<1e-6f,"initial fourbus quarterheadroom and50percent gains");
 for(int mute=0;mute<16;++mute)for(int solo=0;solo<4;++solo){MixSettings s;s.muteMask=static_cast<std::uint8_t>(mute);s.soloAB=static_cast<std::uint8_t>(solo);s.bus={100,100,100,100};s.master=100;check(m.apply(s),"all mask combinations valid");auto g=m.gains();
  for(int bus=0;bus<4;++bus){bool audible=!(mute&(1<<bus))&&(bus<2||solo==0||(solo&(1<<(bus-2))));check(g[static_cast<std::size_t>(bus)]==(audible?0.25f:0.0f),"own mute wins; ABsolo independent reference/metronome");}
 }
 for(int bus=0;bus<4;++bus)for(int gain=0;gain<=100;++gain)for(int master: {0,50,100}){MixSettings s;s.bus={0,0,0,0};s.bus[static_cast<std::size_t>(bus)]=gain;s.master=master;check(m.apply(s),"finite gain range");std::array<float,4> input{};input[static_cast<std::size_t>(bus)]=1;check(m.sample(input,out)&&std::abs(out-static_cast<float>(gain*master)/40000.0f)<1e-6f,"gain/reference independent oracle");}
 MixSettings retained;retained.bus={12,34,56,78};retained.master=63;retained.muteMask=4;retained.soloAB=1;m.apply(retained);const auto before=m.gains();retained.masterMute=true;check(m.apply(retained)&&m.gains()==std::array<float,4>{},"master mute allbuses without erasing settings");retained.masterMute=false;check(m.apply(retained)&&m.gains()==before,"master unmute restores selection and gates");
 MixSettings full;full.bus={100,100,100,100};full.master=100;m.apply(full);check(m.sample({1,1,1,1},out)&&out==1.0f,"full-scale sum bounded");check(m.sample({-1,-1,-1,-1},out)&&out==-1.0f,"negative fullscale bounded");
 for(int which=0;which<8;++which){auto s=full;if(which<4)s.bus[static_cast<std::size_t>(which)]=101;if(which==4)s.master=-1;if(which==5)s.master=101;if(which==6)s.muteMask=16;if(which==7)s.soloAB=4;check(!m.apply(s)&&m.settings().master==100&&m.settings().bus==full.bus,"invalid controls do not partially mutate");}
 for(auto bad: {std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity(),1.01f,-1.01f})check(!m.sample({0,bad,0,0},out)&&out==0,"nonfinite/outofrange bus refuses silence");
 check(std::string(stateText(State::Fault)).find("recovery")!=std::string::npos,"understandable fault recovery state");
}
}
int main(){startup();mixer();faults();std::cout<<"PASS "<<checks<<" output lifecycle/mixer checks; synthetic core only\n";}
