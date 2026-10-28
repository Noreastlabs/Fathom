#include "reference_audio_fixtures.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace fathom;
using namespace reference_fixtures;
namespace {
int checks{};
void ck(bool good,const char* name){++checks;if(!good)throw std::runtime_error(name);std::cout<<"PASS "<<name<<'\n';}
template<class F> void refuses(F&& f,const char* name){bool thrown{};try{f();}catch(const std::exception&){thrown=true;}ck(thrown,name);}
struct Run {std::vector<float> pcm;std::size_t attacks{}, releases{};};
struct Facts {std::array<scheduler::Fact,scheduler::maxCallbackEvents> facts{};std::size_t count{};};
bool collect(void* p,const scheduler::Fact& fact) noexcept {auto& f=*static_cast<Facts*>(p);if(f.count==f.facts.size())return false;f.facts[f.count++]=fact;return true;}
scheduler::BoundaryDecision stop(void*,const scheduler::Fact&) noexcept {return {scheduler::BoundaryAction::Stop,nullptr};}
Run render(const reference::Program& p,std::uint32_t block) {
 scheduler::Cursor cursor;reference::Renderer renderer;Facts got;Run out;
 if(!renderer.bind(p)||!cursor.start(p.schedule(),p.schedule().owner(),p.schedule().binding()))throw std::runtime_error("start");
 for(int watchdog=0;watchdog<100000;++watchdog){const auto begin=cursor.snapshot().processedThrough;got.count=0;
  const bool running=cursor.process(block,p.schedule().owner(),collect,&got,stop,nullptr);
  const auto end=cursor.snapshot().processedThrough;std::size_t i{};
  for(auto frame=begin;frame<end;++frame){while(i<got.count&&got.facts[i].frame==frame){const auto& f=got.facts[i++];if(!renderer.accept(f))throw std::runtime_error("accept");if(f.kind==scheduler::FactKind::Event){out.attacks+=f.action==scheduler::Action::Attack;out.releases+=f.action==scheduler::Action::Release;}}
   float sample{};if(!renderer.sampleFrame(frame,sample))throw std::runtime_error("sample");out.pcm.push_back(sample);}
  while(i<got.count){const auto& f=got.facts[i++];if(f.frame!=end||!renderer.accept(f))throw std::runtime_error("terminal");if(f.kind==scheduler::FactKind::Event){out.attacks+=f.action==scheduler::Action::Attack;out.releases+=f.action==scheduler::Action::Release;}}
  if(!running){if(renderer.failed()||cursor.snapshot().reason!=scheduler::StopReason::Requested)throw std::runtime_error("stop");return out;}
 }
 throw std::runtime_error("watchdog");
}
music::Model pair(music::Attack attack){auto m=synthetic("legato-pair");
 auto first=note("picked",Rational{},Rational{1},3,4,54);auto second=note("arrival",Rational{1},Rational{1},3,attack==music::Attack::HammerOn?7:2,attack==music::Attack::HammerOn?57:52);
 if(attack==music::Attack::PullOff){first.tones[0].fret=7;first.tones[0].midi=57;second.tones[0].fret=4;second.tones[0].midi=54;}
 second.tones[0].attack=attack;m.events={first,second};return m;}
double rms(const std::vector<float>& pcm,std::size_t start,std::size_t length){double sum{};for(std::size_t i=start;i<start+length;++i)sum+=double(pcm[i])*pcm[i];return std::sqrt(sum/length);}
int crossingCount(const std::vector<float>& pcm,std::size_t start,std::size_t length){int n{};for(std::size_t i=start+1;i<start+length;++i)n+=pcm[i-1]<=0&&pcm[i]>0;return n;}
}
int main(){try {
 for(auto attack:{music::Attack::HammerOn,music::Attack::PullOff}){
  auto m=pair(attack);auto c=config(Rational{2});c.method=reference::Method::Sine;auto p=reference::compile(checked(m),c);
  ck(p.voices().size()==1&&p.voices()[0].sourceEvents==std::vector<std::string>({"picked","arrival"})&&p.voices()[0].segments.size()==2,"one voice retains two source IDs and pitch segments");
  auto a=render(p,127),b=render(p,512);ck(a.pcm==b.pcm&&a.attacks==1&&a.releases==1,"one attack/release and block partition equality");
  ck(a.pcm.size()==44100&&std::all_of(a.pcm.begin(),a.pcm.end(),[](float x){return std::isfinite(x);}),"finite two-quarter digital gate");
  const auto firstCycles=crossingCount(a.pcm,8000,8000),secondCycles=crossingCount(a.pcm,28000,8000);
  const double firstHz=firstCycles*44100.0/8000,secondHz=secondCycles*44100.0/8000;
  ck(std::abs(firstHz-p.voices()[0].segments[0].hz)<7&&std::abs(secondHz-p.voices()[0].segments[1].hz)<7,"frequency follows authored target after q1 sample boundary");
  double phase{};constexpr double twoPi=6.283185307179586476925286766559;
  for(int i=0;i<22050;++i)phase=std::remainder(phase+twoPi*p.voices()[0].segments[0].hz/44100,twoPi);
  ck(std::abs(a.pcm[22050]-std::sin(phase)/6.0)<1e-6,"oscillator phase and envelope continue at q1 seam");
  ck(rms(a.pcm,21900,100)>0.08&&rms(a.pcm,22050,100)>0.08,"nonpicked arrival has no new 3ms attack fade");
  phase=std::remainder(phase+twoPi*p.voices()[0].segments[1].hz/44100,twoPi);
  ck(std::abs(a.pcm[22051]-std::sin(phase)/6.0)<1e-6,"first post-boundary phase step uses arrival pitch");
 }
 for(auto attack:{music::Attack::HammerOn,music::Attack::PullOff}){
  auto m=pair(attack);auto held=m.events[1];held.id="held";held.span={Rational{2},Rational{1}};
  held.tones[0].attack=music::Attack::Held;held.tones[0].tieFrom="arrival";m.events.push_back(held);
  auto validated=music::validate(m);ck(validated.validReference()&&validated.issues.empty(),"three-event legato then Held is source-valid");
  auto ready=music::assessReadiness(*validated.model,{{music::Attack::Picked,music::Attack::Held,music::Attack::HammerOn,music::Attack::PullOff},false,true,true});
  ck(ready.technicallyRenderable,"three-event legato then Held advertises technical readiness");
  auto program=reference::compile(validated.model,config(Rational{3}));
  ck(program.voices().size()==1&&program.voices()[0].segments.size()==2&&
     program.voices()[0].sourceEvents==std::vector<std::string>({"picked","arrival","held"})&&
     program.voices()[0].segments.back().midi==m.events[2].tones[0].midi,
     "held extends final pitch segment and retains all three event IDs");
  auto pcm=render(program,127),partition=render(program,512);
  ck(pcm.attacks==1&&pcm.releases==1&&pcm.pcm==partition.pcm,"three-event chain schedules one excitation and is partition identical");
  const auto finalHz=crossingCount(pcm.pcm,50000,8000)*44100.0/8000;
  ck(std::abs(finalHz-program.voices()[0].segments.back().hz)<7,"held span stays at legato arrival pitch");
  for(auto contact:{music::Contact::Release,music::Contact::Muted}){
   auto atSeam=pair(attack);music::Event cancel;cancel.id="cancel";cancel.kind=music::Kind::Contact;cancel.contact=contact;
   cancel.span={Rational{1},contact==music::Contact::Release?Rational{}:Rational{1,4}};cancel.scopeStrings={3};
   atSeam.events.push_back(cancel);const auto invalid=music::validate(atSeam);
   ck(!invalid.validReference()&&std::any_of(invalid.issues.begin(),invalid.issues.end(),[](const auto& issue){return issue.code=="legato_cancelled";}),
      "release/mute at pitch seam refuses legato continuity");
   refuses([&]{reference::compile(checked(atSeam),config(Rational{2}));},"cancelled legato cannot compile");
   auto atHeld=m;cancel.span={Rational{2},contact==music::Contact::Release?Rational{}:Rational{1,4}};atHeld.events.push_back(cancel);
   const auto invalidHeld=music::validate(atHeld);
   ck(!invalidHeld.validReference()&&std::any_of(invalidHeld.issues.begin(),invalidHeld.issues.end(),[](const auto& issue){return issue.code=="tie_cancelled";}),
      "release/mute at held seam refuses tie continuity");
  }
 }
 auto pluckConfig=config(Rational{2});auto pluckProgram=reference::compile(checked(pair(music::Attack::HammerOn)),pluckConfig);
 auto pluckPCM=render(pluckProgram,127);
 ck(pluckPCM.attacks==1&&rms(pluckPCM.pcm,22050,128)>0.06,"Pluck method has one excitation and no second attack fade");
 auto fractional=config(Rational{2},44100,137);auto fractionalProgram=reference::compile(checked(pair(music::Attack::PullOff)),fractional);
 ck(render(fractionalProgram,127).pcm==render(fractionalProgram,512).pcm,"fractional-tempo legato block partitions bit-identical");
 auto picked=pair(music::Attack::HammerOn);picked.events[1].tones[0].attack=music::Attack::Picked;
 auto repick=reference::compile(checked(picked),config(Rational{2}));ck(repick.voices().size()==2&&render(repick,256).attacks==2,"new picked event remains reattack");
 auto bad=pair(music::Attack::HammerOn);bad.events[1].tones[0].string=4;bad.events[1].tones[0].fret=2;bad.events[1].tones[0].midi=57;refuses([&]{reference::compile(checked(bad),config(Rational{2}));},"wrong-string antecedent refuses");
 bad=pair(music::Attack::HammerOn);bad.events[1].tones[0].fret=2;bad.events[1].tones[0].midi=52;refuses([&]{reference::compile(checked(bad),config(Rational{2}));},"wrong hammer direction refuses");
 bad=pair(music::Attack::PullOff);bad.events[1].tones[0].fret=9;bad.events[1].tones[0].midi=59;refuses([&]{reference::compile(checked(bad),config(Rational{2}));},"wrong pull direction refuses");
 bad=pair(music::Attack::HammerOn);bad.events[1].span={Rational{5,4},Rational{3,4}};refuses([&]{reference::compile(checked(bad),config(Rational{2}));},"rational gap refuses");
 bad=pair(music::Attack::HammerOn);bad.events[0].span={Rational{},Rational{5,4}};refuses([&]{reference::compile(checked(bad),config(Rational{2}));},"overlapping gates refuse");
 bad=pair(music::Attack::HammerOn);bad.events[0].tones[0].midi=55;refuses([&]{reference::compile(checked(bad),config(Rational{2}));},"invalid source pitch-position refuses");
 bad=pair(music::Attack::HammerOn);bad.events[0].span={Rational{},Rational{1,100000}};bad.events[1].span={Rational{1,100000},Rational{2}};refuses([&]{reference::compile(checked(bad),config(Rational{3}));},"subsample antecedent refuses");
 // Slide support shares legato ownership but preserves its distinct arrival technique.
 bad=pair(music::Attack::HammerOn);bad.events[1].tones[0].attack=music::Attack::SlideArrival;
 auto slide=reference::compile(checked(bad),config(Rational{2}));
 ck(slide.voices().size()==1 && slide.voices()[0].sourceEvents.size()==2
    && slide.voices()[0].segments.size()==2
    && slide.voices()[0].segments[1].attack==music::Attack::SlideArrival,
    "supported slide retains one voice and distinct arrival technique");
 bad=pair(music::Attack::HammerOn);music::Event release;release.id="release";release.kind=music::Kind::Contact;release.contact=music::Contact::Release;release.span={Rational{1},Rational{}};release.scopeStrings={3};bad.events.push_back(release);refuses([&]{reference::compile(checked(bad),config(Rational{2}));},"boundary release cancels legato");

 // Pinned Level36 Position 1 source oracle, q1-per-click producer model choice.
 struct Contact {int string,fret,midi,finger;const char* spelling;const char* degree;music::Attack attack;};
 const std::array<Contact,24> contacts{{
   {1,5,45,2,"A","1",music::Attack::Picked},
   {1,7,47,4,"B","2",music::Attack::HammerOn},
   {2,4,49,1,"C#","3",music::Attack::Picked},
   {2,7,52,4,"E","5",music::Attack::HammerOn},
   {3,4,54,1,"F#","6",music::Attack::Picked},
   {3,7,57,4,"A","1",music::Attack::HammerOn},
   {4,4,59,1,"B","2",music::Attack::Picked},
   {4,6,61,3,"C#","3",music::Attack::HammerOn},
   {5,5,64,2,"E","5",music::Attack::Picked},
   {5,7,66,4,"F#","6",music::Attack::HammerOn},
   {6,5,69,2,"A","1",music::Attack::Picked},
   {6,7,71,4,"B","2",music::Attack::HammerOn},
   {6,7,71,4,"B","2",music::Attack::Picked},
   {6,5,69,2,"A","1",music::Attack::PullOff},
   {5,7,66,4,"F#","6",music::Attack::Picked},
   {5,5,64,2,"E","5",music::Attack::PullOff},
   {4,6,61,3,"C#","3",music::Attack::Picked},
   {4,4,59,1,"B","2",music::Attack::PullOff},
   {3,7,57,4,"A","1",music::Attack::Picked},
   {3,4,54,1,"F#","6",music::Attack::PullOff},
   {2,7,52,4,"E","5",music::Attack::Picked},
   {2,4,49,1,"C#","3",music::Attack::PullOff},
   {1,7,47,4,"B","2",music::Attack::Picked},
   {1,5,45,2,"A","1",music::Attack::PullOff},
 }};
 auto l36=synthetic("l36-p1-private-projection");l36.syntheticFixture=false;
 l36.itemId="fg:item:036901";l36.sourceRefs={"L36-TXT-P1-35-59"};
 l36.events.clear();
 for(std::size_t i=0;i<contacts.size();++i){const auto& source=contacts[i];
  auto event=note("fg:item:036901:event:"+std::to_string(10000+i+1).substr(1),Rational{static_cast<std::int64_t>(i)},Rational{1},source.string,source.fret,source.midi);
  event.sourceRef="L36-TXT-P1-35-59";auto& t=event.tones[0];t.finger=std::to_string(source.finger);t.spelling=source.spelling;t.attack=source.attack;
  t.degrees={{"A-major-pentatonic",source.degree,9,std::stoi(source.degree),0,{}}};l36.events.push_back(event);
 }
 auto l36v=music::validate(l36);ck(l36v.validReference()&&l36v.issues.empty(),"Level36 24 source contacts retain valid note/degree/technique projection");
 auto l36p=reference::compile(l36v.model,config(Rational{24}));
 bool parity=l36p.voices().size()==12;
 for(std::size_t i=0;i<l36p.voices().size();++i){const auto& voice=l36p.voices()[i];
  parity=parity&&voice.segments.size()==2&&voice.sourceEvents.size()==2&&voice.sourceEvents[0]==l36.events[2*i].id&&voice.sourceEvents[1]==l36.events[2*i+1].id&&voice.segments[0].midi==contacts[2*i].midi&&voice.segments[1].midi==contacts[2*i+1].midi;
 }
 ck(parity,"Level36 12 two-tone voices preserve all 24 event IDs and pitch pairs");
 auto l36run=render(l36p,512);ck(l36run.attacks==12&&l36run.releases==12,"Level36 source projects 12 picked attacks, not 24");
 ck(contacts[10].midi==69&&contacts[11].midi==71&&contacts[12].midi==71&&contacts[12].attack==music::Attack::Picked&&l36p.voices()[6].segments[0].midi==71,"high-e B turn is re-picked source event");
 std::cout<<"CHECKS "<<checks<<" PASS\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<" after "<<checks<<" checks\n";return 1;}}
