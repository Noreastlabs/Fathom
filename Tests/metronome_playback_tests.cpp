#include "platform/MetronomePlayback.hpp"
#include <fstream>
#include <iostream>
#include <iomanip>
#include <cmath>
using namespace fathom;
namespace {
struct Test {int pass{},fail{};std::ofstream out;explicit Test(const char* p):out(p){out<<"{\"classification\":\"software output-observer simulation; no native/physical/human execution\",\"checks\":[";}
 void check(const char* name,bool ok){if(pass+fail)out<<',';out<<"{\"name\":"<<std::quoted(name)<<",\"pass\":"<<(ok?"true":"false")<<'}';if(ok)++pass;else{++fail;std::cerr<<"FAIL "<<name<<'\n';}}
 ~Test(){out<<"],\"passed\":"<<pass<<",\"failed\":"<<fail<<"}\n";}
};
scheduler::Owner owner(){scheduler::Owner o;o.id[6]=0x40;o.id[8]=0x80;o.generation=o.epoch=1;return o;}
struct Harness {
 platform::MetronomePlayback player;platform::Buses buses{};output::Snapshot s;platform::MetronomeProgress p;
 std::vector<scheduler::Fact> facts;std::vector<platform::MetronomeSegment> segments;std::vector<platform::MetronomeReply> replies;std::vector<platform::PolyrhythmLayerReply> layerReplies;
 Harness(metronome::Settings c,std::uint32_t rate=44100){s.owner=owner();s.request.epoch=1;s.request.format={rate,256};s.state=output::State::Running;player.prepare(c,s.owner,1,"explicit-technical-settings",rate);platform::MetronomePlayback::observe(&player,s);drain();}
 void drain(){platform::MetronomeProgress v;while(player.nextProgress(v))p=v;scheduler::Fact f;while(player.nextFact(f))facts.push_back(f);platform::MetronomeSegment z;while(player.nextSegment(z))segments.push_back(z);platform::MetronomeReply r;while(player.nextReply(r))replies.push_back(r);platform::PolyrhythmLayerReply layer;while(player.nextLayerReply(layer))layerReplies.push_back(layer);}
 bool block(std::uint32_t n,bool accept=true){platform::MetronomePlayback::observe(&player,s);drain();buses={};const auto r=platform::MetronomePlayback::render(&player,s.owner,s.request.format.rate,n,buses);if(r.valid&&accept)s.submittedFrames+=r.submittedFrames;if(!r.valid||!accept)s.state=output::State::Fault;platform::MetronomePlayback::observe(&player,s);drain();return r.valid;}
 bool through(std::uint64_t n){while(s.submittedFrames<n){if(!block(static_cast<std::uint32_t>(std::min<std::uint64_t>(256,n-s.submittedFrames))))return false;}return true;}
 void stop(bool pause){s.state=pause?output::State::Paused:output::State::Unresolved;s.requestedStopNs=123;s.uncertainThrough=s.submittedFrames+256;platform::MetronomePlayback::observe(&player,s);drain();player.reclaim(p);}
 bool resume(){auto prior=s.owner;auto next=prior;++next.generation;const bool b=player.prepareResume(prior,next);s.owner=next;s.state=output::State::Running;s.submittedFrames=0;s.requestedStopNs=0;s.uncertainThrough=0;platform::MetronomePlayback::observe(&player,s);drain();return b;}
};
metronome::Settings ramp(){metronome::Settings c;c.tempo=120;c.ramp=metronome::Ramp{true,6,1,132};return c;}
}
int main(int argc,char** argv){if(argc!=2)return 2;Test t(argv[1]);
 {Harness h(ramp());t.check("ramp first endpoint",h.through(176400)&&h.p.completedCycles==1&&h.p.tempo.tempo==120&&h.p.cursorFrames==0);
 t.check("ramp boundary next attack",h.block(1)&&h.p.tempo.tempo==126&&h.p.completedCycles==1);
 t.check("second repeated ramp",h.through(260401)&&h.p.tempo.tempo==132&&h.p.completedCycles==2&&!h.p.tempo.ramp);
 t.check("target continues and exact endpoint",h.through(420764)&&h.p.completedCycles==4&&!h.p.terminal);
 h.stop(false);t.check("stop retains exact endpoint once",h.p.completedCycles==4&&h.p.activeFrames==332564&&h.p.terminal&&!h.p.fault&&!h.p.partial&&h.p.requestedStopNs==123&&h.p.uncertainThrough==421020);
 bool refused=false;try{h.resume();}catch(...){refused=true;}t.check("terminal cannot resume",refused);}
 {Harness h(ramp());h.through(206400);h.stop(true);t.check("partial ramp pause",h.p.completedCycles==1&&h.p.activeFrames==118200&&h.p.partial&&h.p.tempo.tempo==126&&h.p.tempo.resumable);
 t.check("same original resume",h.resume()&&h.p.owner.generation==2&&h.p.phase==metronome::Phase::CountIn);
 t.check("fresh countin excluded",h.through(84000)&&h.p.activeFrames==0&&h.p.completedCycles==1);
 t.check("replayed traversal completes once",h.through(248182)&&h.p.completedCycles==3&&h.p.totalActiveFrames==282382);h.stop(false);}
 {Harness h(ramp());h.through(176400);h.stop(true);t.check("endpoint Pause preserves due ramp",h.p.completedCycles==1&&h.p.tempo.count==1&&h.p.tempo.tempo==120&&h.p.tempo.resumable);
 h.resume();h.through(176401);t.check("resume due ramp applies after next complete bar",h.p.completedCycles==2&&h.p.tempo.tempo==126);h.stop(false);}
 {Harness h(ramp());h.through(500);h.stop(true);t.check("countin pause zero active",h.p.activeFrames==0&&h.p.completedCycles==0&&!h.p.partial);
 h.resume();h.through(88200);t.check("countin resume fresh entire bar",h.p.activeFrames==0&&h.p.totalActiveFrames==0);h.stop(false);}
 {Harness h(ramp());h.through(200000);t.check("manual enqueued",h.player.manual(h.s.owner,1,10,137));h.block(1);
 t.check("manual accepted and disarms",h.replies.back().accepted&&!h.p.tempo.ramp&&h.p.tempo.pendingManual==137);
 h.player.manual(h.s.owner,1,10,140);h.block(1);t.check("duplicate manual refused",!h.replies.back().accepted);
 auto stale=h.s.owner;++stale.generation;h.player.manual(stale,1,11,140);h.block(1);t.check("foreign generation refused",!h.replies.back().accepted);
 h.through(260401);t.check("manual wins boundary",h.p.tempo.tempo==137&&!h.p.tempo.ramp&&!h.p.tempo.pendingManual);
 h.through(414911);t.check("piecewise manual exact end",h.p.completedCycles==4);h.stop(false);}
 {Harness h(ramp());h.through(176300);h.player.manual(h.s.owner,1,1,137);h.block(256,false);
 t.check("rejected boundary block gives no credit",h.p.fault&&h.p.clientAcceptedThrough==176300&&h.p.completedCycles==0&&h.p.tempo.tempo==120&&h.p.tempo.pendingManual==137);
 t.check("scheduled facts remain distinct",h.p.scheduledThrough==176556&&h.facts.back().frame>=176400);
 bool noAccepted=true;for(const auto& x:h.segments)noAccepted&=x.through<=176300;t.check("rejected segments absent",noAccepted);}
 {auto c=ramp();Harness h(c);h.player.manual(h.s.owner,1,1,137);h.block(1);t.check("countin manual refused",!h.replies.back().accepted);h.stop(false);}
 {auto c=ramp();c.styles={metronome::Style::Silent,metronome::Style::Normal,metronome::Style::Silent,metronome::Style::Accent};c.subdivision=2;Harness h(c);h.through(176401);
 bool seenSparse=false,noSilent=true,ciFirst=false;for(const auto& f:h.facts)if(f.kind==scheduler::FactKind::Event){if(f.role==scheduler::Role::Metronome){seenSparse|=f.sourceEvent==6;noSilent&=f.sourceEvent==2||f.sourceEvent==3||f.sourceEvent==6||f.sourceEvent==7;}else ciFirst|=f.sourceEvent==0;}
 t.check("sparse cue IDs and countin role",seenSparse&&noSilent&&ciFirst);
 h.through(180000);t.check("silent new downbeat still new tempo segment",h.segments.back().tempo==126&&h.segments.back().through==180000);h.stop(false);}
 {metronome::Settings c;c.tempo=300;c.numerator=1;c.denominator=16;c.unit=scheduler::BeatUnit::Half;c.subdivision=7;c.styles={metronome::Style::Accent};c.countIn=metronome::CountIn::Off;Harness h(c,8000);
 t.check("maximum density full output block",h.block(8192)&&!h.p.fault&&h.p.completedCycles==40);
 bool finite=true,endpoints=true;for(auto x:h.buses[1][0])finite&=std::isfinite(x)&&std::abs(x)<=0.8f;
 for(const auto& f:h.facts)if(f.kind==scheduler::FactKind::Event&&f.frame<8192)endpoints&=h.buses[1][0][static_cast<std::size_t>(f.frame)]==0;
 t.check("dense finite zero attack endpoints",finite&&endpoints);h.stop(false);}
 {metronome::Settings c;c.tempo=120;c.countIn=metronome::CountIn::Off;c.metronomeEnabled=false;Harness h(c);h.block(256);bool zero=true;for(float x:h.buses[1][0])zero&=x==0;t.check("disabled bus clock continues",zero&&h.p.activeFrames==256&&!h.facts.empty());h.stop(false);}
 {metronome::Settings c;c.countIn=metronome::CountIn::Off;Harness h(c);auto foreign=h.s.owner;++foreign.epoch;t.check("foreign render refused",!platform::MetronomePlayback::render(&h.player,foreign,44100,256,h.buses).valid);h.stop(false);}
 {metronome::Settings c;c.tempo=60;c.countIn=metronome::CountIn::Off;c.polyrhythmEnabled=true;c.ramp.reset();c.x=3;c.y=2;c.volumes[2]=100;c.volumes[3]=0;Harness h(c,8000);
  t.check("polyrhythm playback starts without count-in",h.block(256)&&h.p.activeFrames==256);
  bool roles=false;for(const auto& f:h.facts)if(f.kind==scheduler::FactKind::Event)roles|=f.role==scheduler::Role::LayerA||f.role==scheduler::Role::LayerB;
  bool layerA=false,layerBZero=true;for(float x:h.buses[2][0])layerA|=std::abs(x)>0.000001f;for(float x:h.buses[3][0])layerBZero&=x==0;
  t.check("polyrhythm facts and separate buses preserve role/gain contract",roles&&layerA&&layerBZero);
  t.check("polyrhythm playback completes one shared cycle",h.through(8000)&&h.p.completedCycles==1&&!h.p.fault);h.stop(false);}
 {metronome::Settings c;c.tempo=60;c.countIn=metronome::CountIn::Off;c.polyrhythmEnabled=true;c.x=3;c.y=2;c.volumes[2]=c.volumes[3]=100;Harness h(c,8000);
  t.check("polyrhythm manual tempo queued",h.player.manual(h.s.owner,1,1,75)&&h.block(1)&&h.replies.back().accepted);
  t.check("polyrhythm old cycle closes before new tempo",h.through(8001)&&h.p.completedCycles==1&&h.p.tempo.tempo==75&&!h.p.fault);
  bool oldBoundary=false;for(const auto& f:h.facts)oldBoundary|=f.kind==scheduler::FactKind::CycleCompleted&&f.frame==8000&&f.cycle==1;
  t.check("polyrhythm first common-cycle boundary remains at old duration",oldBoundary);
  t.check("polyrhythm next common cycle uses selected tempo",h.through(14401)&&h.p.completedCycles==2&&!h.p.fault);
  bool newBoundary=false;for(const auto& f:h.facts)newBoundary|=f.kind==scheduler::FactKind::CycleCompleted&&f.frame==14400&&f.cycle==2;
  t.check("polyrhythm second boundary follows new 6400-frame duration",newBoundary);h.stop(false);}
 {metronome::Settings c;c.tempo=60;c.countIn=metronome::CountIn::Off;c.polyrhythmEnabled=true;c.x=3;c.y=2;c.volumes[2]=c.volumes[3]=100;Harness h(c,8000);
  t.check("polyrhythm active voices begin before live gain request",h.block(20)&&!h.p.fault);
  t.check("polyrhythm exact-owner layer request accepted",h.player.layerGains(h.s.owner,1,1,{0,100})&&h.block(20)&&!h.layerReplies.empty()&&h.layerReplies.back().accepted);
  bool aZero=true,bSounds=false;for(std::size_t i=0;i<20;++i){aZero&=h.buses[2][0][i]==0;bSounds|=std::abs(h.buses[3][0][i])>0.000001f;}
  t.check("polyrhythm gain change preserves active LayerB and mutes LayerA",aZero&&bSounds&&h.p.completedCycles==0);
  h.player.layerGains(h.s.owner,1,1,{100,0});h.block(20);
  t.check("polyrhythm duplicate layer sequence refuses",!h.layerReplies.back().accepted&&h.buses[2][0][0]==0);
  auto foreign=h.s.owner;++foreign.generation;h.player.layerGains(foreign,1,2,{100,0});h.block(20);
  t.check("polyrhythm foreign layer owner refuses",!h.layerReplies.back().accepted&&h.buses[2][0][0]==0&&h.p.owner==h.s.owner);h.stop(false);}
 {auto c=metronome::Settings{};c.polyrhythmEnabled=true;c.countIn=metronome::CountIn::ConfiguredBar;bool refused=false;try{Harness h(c,8000);}catch(const std::invalid_argument&){refused=true;}t.check("polyrhythm configured count-in refuses explicitly",refused);}
 {auto c=metronome::Settings{};c.polyrhythmEnabled=true;c.countIn=metronome::CountIn::Off;c.ramp=metronome::Ramp{true,1,1,61};bool refused=false;try{Harness h(c,8000);}catch(const std::invalid_argument&){refused=true;}t.check("polyrhythm ramp refuses explicitly in bounded seam",refused);}
 std::cout<<"checks="<<t.pass+t.fail<<" passed="<<t.pass<<" failed="<<t.fail<<'\n';return t.fail?1:0;
}
