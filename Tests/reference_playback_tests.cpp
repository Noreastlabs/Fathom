#include "reference_audio_fixtures.hpp"
#include "platform/ReferencePlayback.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace fathom;using namespace reference_fixtures;
namespace {int checks=0;void expect(bool x,const char* name){++checks;if(!x)throw std::runtime_error(name);std::cout<<"PASS "<<name<<'\n';}}
int main(){try{
 auto buses=std::make_unique<platform::Buses>();
 for(int which=0;which<4;++which){
    auto model=which==0?chord(false):which==1?held():which==2?air():synthetic("terminal");
    auto cfg=config(which==0?Rational{5,2}:which==1?Rational{3,2}:Rational{2});
    if(which==3){model.events={note("tiny",Rational{},Rational{17,1000})};cfg=config(Rational{17,1000},8000,60);}
    auto program=reference::compile(checked(model),cfg);platform::ReferencePlayback playback;playback.prepare(program);
    output::Snapshot ready;ready.state=output::State::Ready;ready.request.epoch=cfg.owner.epoch;platform::ReferencePlayback::observe(&playback,ready);
    std::uint64_t pos=0;bool done=false;double error=0;std::uint32_t terminalPrefix=0;
    for(int block=0;block<1000 && !done;++block){*buses={};auto result=platform::ReferencePlayback::render(&playback,cfg.owner,cfg.rate,256,*buses);if(!result.valid)throw std::runtime_error("valid reference provider");
      for(std::uint32_t f=0;f<result.submittedFrames;++f){double expected=0;for(const auto& voice:program.voices()){std::uint64_t a{},b{};scheduler::round(voice.startFrames,a);scheduler::round(voice.endFrames,b);if(pos+f>=a&&pos+f<b)expected+=reference::sample(program.method(),voice.hz,pos+f-a,b-a,cfg.rate)/6.0;}
        error=std::max(error,std::abs(static_cast<double>((*buses)[0][0][f])-static_cast<float>(expected)));if((*buses)[0][0][f]!=(*buses)[0][1][f])throw std::runtime_error("stereo");}
      for(std::size_t b=1;b<4;++b)for(const auto& channel:(*buses)[b])for(auto value:channel)if(value!=0)throw std::runtime_error("foreign bus");
      scheduler::Fact f;while(playback.stream().nextFact(f)){}scheduler::StreamView v;while(playback.stream().nextView(v)){}
      pos+=result.submittedFrames;done=result.terminal;terminalPrefix=result.submittedFrames;
    }
    expect(done&&error==0,"provider matches accepted core PCM and zero foreign buses");std::uint64_t expectedEnd{};scheduler::round(program.schedule().duration(),expectedEnd);expect(pos==expectedEnd,"normal prefix preserves exact source endpoint");
    if(which==3)expect(terminalPrefix==136 && (*buses)[0][0][135]!=0,"positive136-frame terminal reference tail is preserved");
    auto stopped=ready;stopped.state=output::State::Unresolved;stopped.owner=cfg.owner;platform::ReferencePlayback::observe(&playback,stopped);auto again=platform::ReferencePlayback::render(&playback,cfg.owner,cfg.rate,256,*buses);expect(again.valid&&again.terminal&&again.submittedFrames==0,"terminal consumer cannot replay old events");
 }
 {platform::ReferencePlayback p;auto cfg=config();p.prepare(reference::compile(checked(held()),cfg));auto wrong=cfg.owner;++wrong.generation;expect(!platform::ReferencePlayback::render(&p,wrong,cfg.rate,256,*buses).valid,"stale output owner refuses provider");expect(!platform::ReferencePlayback::render(&p,cfg.owner,cfg.rate,256,*buses).valid,"stale failure latches without recovery replay");}
 {platform::ReferencePlayback p;auto cfg=config();p.prepare(reference::compile(checked(held()),cfg));expect(!platform::ReferencePlayback::render(&p,cfg.owner,48000,256,*buses).valid,"changed observed format refuses provider");}
 {platform::ReferencePlayback p;auto cfg=config();p.prepare(reference::compile(checked(held()),cfg));output::Snapshot fault;fault.state=output::State::Fault;fault.request.epoch=cfg.owner.epoch;fault.owner=cfg.owner;platform::ReferencePlayback::observe(&p,fault);expect(!platform::ReferencePlayback::render(&p,cfg.owner,cfg.rate,256,*buses).valid,"prestart fault cannot later render stale music");}
 std::cout<<"CHECKS "<<checks<<" PASS\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<" after "<<checks<<" checks\n";return 1;}}
