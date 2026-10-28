#include "core/TabPlayback.hpp"
#include "reference_audio_fixtures.hpp"
#include <iostream>
#include <fstream>
#include <filesystem>
using namespace fathom;
int main(int argc,char** argv){int checks=0;try{
 if(argc!=2||std::filesystem::exists(argv[1]))throw std::invalid_argument("new output directory required");std::filesystem::create_directories(argv[1]);std::ofstream log(std::filesystem::path(argv[1])/"checks.tsv");
 auto ck=[&](bool b,const std::string& n){++checks;log<<n<<'\t'<<(b?"PASS":"FAIL")<<'\n';if(!b)throw std::runtime_error(n);};
 auto model=reference_fixtures::synthetic("tab-live");auto picked=reference_fixtures::note("picked",Rational{},Rational{1},1,0,40);auto held=picked;held.id="held";held.span.onset=Rational{1};held.tones[0].attack=music::Attack::Held;held.tones[0].tieFrom="picked";
 music::Event rest;rest.id="rest";rest.kind=music::Kind::Rest;rest.span={Rational{2},Rational{2}};rest.scopeStrings={1,2,3,4,5,6};model.events={picked,held,rest};
 auto prepared=reference_fixtures::checked(model);auto document=std::make_shared<const tab::Document>(prepared);practice::Configuration cfg;cfg.faithfulWholeSpan=true;cfg.meter={{4,4}};scheduler::Owner owner;owner.id[0]=1;owner.id[6]=0x40;owner.id[8]=0x80;owner.generation=1;owner.epoch=7;
 practice::Coordinator c;c.begin(owner,practice::Kind::Attempt,"synthetic-pinned",cfg);tab::Playback view;view.bind(document,prepared,c);ck(!view.position().hasMusicalSample&&view.position().events.empty(),"fresh no credit");
 std::uint64_t seq=0;
 auto accepted=[&](std::uint64_t through,practice::State state){practice::Progress p;p.owner=c.owner();p.sequence=++seq;p.clientAcceptedThrough=through;p.scheduledThrough=through+256;p.activeFrames=through>88200?through-88200:0;p.completedCycles=p.activeFrames/88200;p.cursorFrames=p.activeFrames%88200;p.partial=p.cursorFrames!=0;p.state=state;p.terminal=state==practice::State::Paused||state==practice::State::Ended;p.uncertainThrough=through+256;p.requestedStopNs=p.terminal?123456:0;ck(c.progress(p),"coordinator accepts exact fact");ck(view.update(c),"mapped current fact");return p;};
 accepted(256,practice::State::CountIn);ck(view.position().events.empty(),"countin no source");accepted(88200,practice::State::Running);ck(view.position().events.empty(),"exclusive intro endpoint still no musical sample");
 accepted(88201,practice::State::Running);ck(view.position().events==std::vector<std::string>{"picked"},"first accepted musical sample");
 accepted(110250,practice::State::Running);ck(view.position().events==std::vector<std::string>{"picked"},"through held onset retains picked");
 accepted(110251,practice::State::Running);ck(view.position().events==std::vector<std::string>{"held"},"held source differs coalesced voice");
 accepted(132300,practice::State::Running);ck(view.position().events==std::vector<std::string>{"held"},"exclusive rest boundary holds previous");
 auto p=accepted(132301,practice::State::Paused);ck(view.position().events==std::vector<std::string>{"rest"},"accepted rest and pause retained");ck(view.position().progress.requestedStopNs==123456&&view.position().progress.uncertainThrough==132557,"requested and uncertain remain separate");
 ck(!c.progress(p)&&!view.update(c),"duplicate no visual advance");p.sequence++;p.owner.epoch++;ck(!c.progress(p)&&!view.update(c),"stale epoch no visual advance");
 const auto old=c.owner();c.resume();ck(!view.update(c),"resume requires explicit binding");view.bind(document,prepared,c);ck(view.position().events.empty(),"resume clears live events");seq=0;accepted(256,practice::State::CountIn);ck(view.position().events.empty(),"resume countin silent visual");
 p.owner=old;p.sequence=100;p.clientAcceptedThrough=176400;p.activeFrames=88200;p.completedCycles=1;p.cursorFrames=0;p.partial=false;p.state=practice::State::Paused;ck(!c.progress(p)&&!view.update(c),"delayed prior owner retained not current view");
 accepted(176400,practice::State::Ended);ck(view.position().events==std::vector<std::string>{"rest"}&&view.position().cycle==0&&view.position().sample==176399,"stop exact cycle endpoint never lights upcoming picked");
 bool refused=false;try{view.bind(document,prepared,c);}catch(const std::exception&){refused=true;}ck(refused,"terminal generation cannot silently rebind");
 // Independent finite expected event positions; quarter frames = rate*60/bpm.
 for(const auto rate:{44100U,48000U})for(const auto bpm:{73,137,239}){
  auto m=reference_fixtures::synthetic("fractional");for(int i=0;i<7;++i)m.events.push_back(reference_fixtures::note("event-"+std::to_string(i),Rational{i,3},Rational{1,3},1,0,40));
  auto preparedFractional=reference_fixtures::checked(m);auto d=std::make_shared<const tab::Document>(preparedFractional);practice::Configuration f;f.span=Rational{7,3};f.countIn=practice::CountIn::Off;f.faithfulWholeSpan=true;f.rate=rate;f.bpm=static_cast<std::uint16_t>(bpm);f.targetCycles=3;
  scheduler::Owner o=owner;o.id[0]=static_cast<std::uint8_t>(bpm);practice::Coordinator control;control.begin(o,practice::Kind::Attempt,"fractional",f);tab::Playback tv;tv.bind(d,preparedFractional,control);std::uint64_t sequence=0;
  auto boundary=[&](std::uint64_t thirds){auto n=thirds*rate*60ULL;auto den=static_cast<std::uint64_t>(bpm)*3;return (n+den/2)/den;};
  for(std::uint64_t k=0;k<3;++k)for(std::uint64_t event=0;event<7;++event)for(auto through:{boundary(k*7+event)+1,boundary(k*7+event+1)}){
   practice::Progress q;q.owner=o;q.sequence=++sequence;q.clientAcceptedThrough=q.scheduledThrough=q.activeFrames=through;while(q.completedCycles<3&&boundary((q.completedCycles+1)*7)<=through)++q.completedCycles;q.cursorFrames=through-boundary(q.completedCycles*7);q.partial=q.cursorFrames!=0;q.state=through==boundary(21)?practice::State::Ended:practice::State::Running;q.terminal=q.state==practice::State::Ended;
   ck(control.progress(q)&&tv.update(control),"fractional actual accepted prefix");ck(tv.position().events==std::vector<std::string>{"event-"+std::to_string(event)}&&tv.position().cycle==k,"absolute rounded boundary event, no cycle drift");
  }
 }
 std::cout<<"PASS "<<checks<<" accepted-progress TAB checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
