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
void ck(bool value,const char* label){++checks;if(!value)throw std::runtime_error(label);std::cout<<"PASS "<<label<<'\n';}
template<class F>void refuse(F f,const char* label){bool threw{};try{f();}catch(const std::exception&){threw=true;}ck(threw,label);}
struct Run{std::vector<float> pcm;int attacks{},releases{};};
struct Facts{std::array<scheduler::Fact,scheduler::maxCallbackEvents> value{};std::size_t count{};};
bool collect(void* p,const scheduler::Fact& f)noexcept{auto& v=*static_cast<Facts*>(p);if(v.count==v.value.size())return false;v.value[v.count++]=f;return true;}
scheduler::BoundaryDecision stop(void*,const scheduler::Fact&)noexcept{return {scheduler::BoundaryAction::Stop,nullptr};}
Run render(const reference::Program& p,std::uint32_t block){scheduler::Cursor cursor;reference::Renderer renderer;Facts facts;Run out;
 if(!renderer.bind(p)||!cursor.start(p.schedule(),p.schedule().owner(),p.schedule().binding()))throw std::runtime_error("start");
 for(int watch=0;watch<100000;++watch){auto begin=cursor.snapshot().processedThrough;facts.count=0;bool running=cursor.process(block,p.schedule().owner(),collect,&facts,stop,nullptr);auto end=cursor.snapshot().processedThrough;std::size_t at{};
  auto accept=[&](const scheduler::Fact& f){if(!renderer.accept(f))throw std::runtime_error("fact");if(f.kind==scheduler::FactKind::Event){out.attacks+=f.action==scheduler::Action::Attack;out.releases+=f.action==scheduler::Action::Release;}};
  for(auto frame=begin;frame<end;++frame){while(at<facts.count&&facts.value[at].frame==frame)accept(facts.value[at++]);float sample{};if(!renderer.sampleFrame(frame,sample))throw std::runtime_error("sample");out.pcm.push_back(sample);}
  while(at<facts.count){if(facts.value[at].frame!=end)throw std::runtime_error("terminal frame");accept(facts.value[at++]);}
  if(!running){if(renderer.failed()||cursor.snapshot().reason!=scheduler::StopReason::Requested)throw std::runtime_error("stop");return out;}
 }throw std::runtime_error("watchdog");}
music::Model slidePair(){auto m=synthetic("slide-pair");auto a=note("picked",Rational{},Rational{1},2,5,50);auto b=note("slide",Rational{1},Rational{1},2,6,51);b.tones[0].attack=music::Attack::SlideArrival;m.events={a,b};return m;}
music::Model expansion(){auto m=synthetic("level48-expansion-reference");m.syntheticFixture=false;m.sourceRefs={"L48-TXT351-362/PDF9"};m.events={
 note("slot1",Rational{},Rational{1,2},1,5,45),note("slot2",Rational{1,2},Rational{1,2},1,8,48),
 note("slot3",Rational{1},Rational{1,2},2,5,50),note("slot4",Rational{3,2},Rational{1,2},2,6,51),
 note("slot5",Rational{2},Rational{1,2},2,7,52),note("slot6",Rational{5,2},Rational{1,2},5,8,67),
 note("slot7",Rational{3},Rational{1,2},3,7,57),note("slot8",Rational{7,2},Rational{1,2},6,8,72)};
 m.events[1].tones[0].attack=music::Attack::HammerOn;m.events[3].tones[0].attack=music::Attack::SlideArrival;m.events[4].tones[0].attack=music::Attack::SlideArrival;return m;}
bool issue(const music::Validation& v,const char* code){return std::any_of(v.issues.begin(),v.issues.end(),[&](const auto& x){return x.code==code;});}
}
int main(){try{
 auto m=slidePair();auto validated=music::validate(m);ck(validated.validReference()&&validated.issues.empty(),"same-string slide pair valid source model");
 auto c=config(Rational{2});c.method=reference::Method::Sine;auto p=reference::compile(validated.model,c);
 ck(p.voices().size()==1&&p.voices()[0].sourceEvents==std::vector<std::string>({"picked","slide"})&&p.voices()[0].segments.size()==2&&p.voices()[0].segments[1].midi==51,"one voice retains both IDs and target pitch");
 auto a=render(p,127),b=render(p,512);ck(a.attacks==1&&a.releases==1&&a.pcm==b.pcm,"one pick/release and partition equality");
 ck(a.pcm.size()==44100&&std::all_of(a.pcm.begin(),a.pcm.end(),[](float x){return std::isfinite(x);}),"finite deterministic PCM");
 constexpr double twoPi=6.283185307179586476925286766559;double phase{};const auto window=22050U/4U,glideStart=22050U-window;
 for(unsigned frame=0;frame<22050;++frame){double hz=p.voices()[0].segments[0].hz;if(frame>=glideStart)hz+=(p.voices()[0].segments[1].hz-hz)*double(frame-glideStart)/window;phase=std::remainder(phase+twoPi*hz/44100,twoPi);}
 ck(std::abs(a.pcm[22050]-std::sin(phase)/6.0)<1e-6,"phase/envelope continuous at exact q1 seam");
 ck(std::abs(a.pcm[22051]-std::sin(std::remainder(phase+twoPi*p.voices()[0].segments[1].hz/44100,twoPi))/6.0)<1e-6,"target pitch begins at authored seam");
 auto step=m;step.events[1].tones[0].attack=music::Attack::HammerOn;auto stepP=reference::compile(checked(step),c);auto stepRun=render(stepP,127);
 ck(std::equal(a.pcm.begin(),a.pcm.begin()+glideStart,stepRun.pcm.begin()),"pre-glide picked excitation is byte-identical to continuous step path");
 ck(std::all_of(a.pcm.begin()+glideStart,a.pcm.begin()+22050,[](float x){return std::isfinite(x);}),"glide region remains finite");
 ck(std::abs(a.pcm[glideStart+window/2]-stepRun.pcm[glideStart+window/2])>1e-5,"audible-reference trajectory differs from hammer-like pitch step before seam");
 auto pluckConfig=config(Rational{2});auto pluckProgram=reference::compile(checked(m),pluckConfig);
 auto pluckA=render(pluckProgram,113),pluckB=render(pluckProgram,512);
 ck(pluckA.attacks==1&&pluckA.releases==1&&pluckA.pcm==pluckB.pcm&&
    std::all_of(pluckA.pcm.begin(),pluckA.pcm.end(),[](float x){return std::isfinite(x);}),
    "Pluck slide has one excitation, finite PCM and partition equality");
 ck(std::abs(pluckA.pcm[22050])>1e-4,"Pluck arrival carries the decaying envelope without a new attack fade");
 auto e=expansion();auto ev=music::validate(e);ck(ev.validReference()&&ev.issues.empty(),"original Expansion eight-slot note/fret/attack projection source-valid");auto ec=config(Rational{4});auto ep=reference::compile(ev.model,ec);
 ck(ep.voices().size()==5&&ep.voices()[1].sourceEvents==std::vector<std::string>({"slot3","slot4","slot5"})&&ep.voices()[1].segments[2].midi==52,"Expansion preserves two upward A-string slide arrivals and eight IDs");
 auto er=render(ep,113),er2=render(ep,512);ck(er.attacks==5&&er.releases==5&&er.pcm==er2.pcm,"Expansion has five printed picks, no slide repicks, partition equality");
 auto down=slidePair();down.events[0].tones[0].fret=7;down.events[0].tones[0].midi=52;down.events[1].tones[0].fret=5;down.events[1].tones[0].midi=50;ck(reference::compile(checked(down),config(Rational{2})).voices().size()==1,"downward fretted slide supported");
 for(auto contact:{music::Contact::Release,music::Contact::Muted}){auto cancelled=slidePair();music::Event x;x.id="cancel";x.kind=music::Kind::Contact;x.contact=contact;x.span={Rational{1},contact==music::Contact::Release?Rational{}:Rational{1,4}};x.scopeStrings={2};cancelled.events.push_back(x);auto v=music::validate(cancelled);ck(!v.validReference()&&issue(v,"legato_cancelled"),"source validator refuses slide cancellation at seam");}
 auto bad=slidePair();bad.events[1].tones[0].string=3;bad.events[1].tones[0].fret=1;bad.events[1].tones[0].midi=51;refuse([&]{reference::compile(checked(bad),config(Rational{2}));},"wrong string refuses");
 bad=slidePair();bad.events[1].tones[0].fret=5;bad.events[1].tones[0].midi=50;ck(issue(music::validate(bad),"legato_direction"),"same-fret slide source-invalid");
 bad=slidePair();bad.events[0].tones[0].fret=0;bad.events[0].tones[0].midi=45;refuse([&]{reference::compile(checked(bad),config(Rational{2}));},"open-origin slide geometry refuses");
 bad=slidePair();bad.events[0].span={Rational{},Rational{1,10000}};bad.events[1].span={Rational{1,10000},Rational{2}};refuse([&]{reference::compile(checked(bad),config(Rational{3}));},"too-short slide origin refuses");
 for(auto attack:{music::Attack::Bend,music::Attack::BlueThirdShade,music::Attack::Harmonic,music::Attack::Vibrato}){bad=slidePair();bad.events[1].tones[0].attack=attack;refuse([&]{reference::compile(checked(bad),config(Rational{2}));},"other unsupported technique refuses");}
 std::cout<<"CHECKS "<<checks<<" PASS\n";return 0;
}catch(const std::exception& ex){std::cerr<<"FAIL "<<ex.what()<<" after "<<checks<<" checks\n";return 1;}}
