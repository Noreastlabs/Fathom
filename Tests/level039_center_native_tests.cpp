#include "core/MusicModel.hpp"
#include "core/ReferenceAudio.hpp"
#include "content/Canonical.hpp"
#include <cstdlib>
#include <filesystem>
#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace fathom;
namespace {
void require(bool yes,const char* why) {if(!yes)throw std::runtime_error(why);std::cout<<"PASS "<<why<<'\n';}
struct Pitch {int string,fret,midi;};
constexpr std::array<Pitch,32> printed{{
        {4,4,59},
        {4,6,61},
        {5,5,64},
        {4,6,61},
        {4,4,59},
        {3,7,57},
        {5,5,64},
        {3,7,57},
        {3,9,59},
        {4,6,61},
        {4,9,64},
        {4,6,61},
        {3,7,57},
        {2,9,54},
        {4,6,61},
        {2,9,54},
        {3,9,59},
        {3,11,61},
        {4,9,64},
        {3,11,61},
        {3,9,59},
        {2,12,57},
        {4,9,64},
        {2,12,57},
        {4,16,71},
        {5,14,73},
        {5,17,76},
        {5,14,73},
        {4,14,69},
        {3,16,66},
        {5,14,73},
        {3,16,66}
}};
music::Model model(bool backing) {
    music::Model m;m.itemId="fg:item:039901";m.schemaVersion="curriculum-v1";m.contentVersion="l39-v1-private";
    m.instrument.openMidi={40,45,50,55,59,64};m.sourceRefs={"L39-PDF-PIVOT-P10"};
    for(std::size_t i=0;i<printed.size();++i) {
        music::Event e;e.id="fg:item:039901:event:"+std::to_string(10000+i+1).substr(1);
        e.sourceRef="L39-PDF-PIVOT-P10";e.span={Rational{static_cast<std::int64_t>(i)},Rational{1}};
        music::Tone t;t.string=printed[i].string;t.fret=printed[i].fret;t.midi=printed[i].midi;
        e.tones.push_back(t);m.events.push_back(e);
    }
    if(backing) {
        music::BackingLane lane;lane.sourceRef="L39-PDF-PIVOT-P10";
        lane.sourceSha256="4f263085b49918b80702669c1a11949ecf3bb04708bf38019c2f3daa6c05b63b";
        lane.eventDigestSha256="3737b290fbeabc623cdfaa2a56cfcccc581150389fe472bad7209f7e6bbb8ad9";
        lane.modelChoice="agent:l39-v1-sine-a3-fsharp3-full-section-gate-80permille";
        for(const auto& e:m.events)lane.contacts.push_back({e.id,*e.span.onset,*e.span.duration,e.tones[0].string,e.tones[0].fret,e.tones[0].midi});
        for(int i=0;i<4;++i)lane.sections.push_back({Rational{i*8},Rational{8},i%2?6:9,i%2?54:57});
        m.backing=std::move(lane);
    }
    return m;
}
reference::Configuration config() {
    reference::Configuration c;c.owner.id[0]=1;c.owner.id[6]=0x40;c.owner.id[8]=0x80;c.owner.generation=1;c.owner.epoch=1;
    c.binding=39;c.sourceBinding="l39-v1-private";c.cycle=Rational{32};c.bpm=120;c.rate=8000;c.method=reference::Method::Sine;return c;
}
struct Collector {std::array<scheduler::Fact,scheduler::maxCallbackEvents> facts{};std::size_t count{};};
bool collect(void* p,const scheduler::Fact& f) noexcept {auto& c=*static_cast<Collector*>(p);if(c.count==c.facts.size())return false;c.facts[c.count++]=f;return true;}
scheduler::BoundaryDecision boundary(void*,const scheduler::Fact&) noexcept {return {scheduler::BoundaryAction::Stop,nullptr};}
std::vector<float> render(const reference::Program& p) {
    scheduler::Cursor cursor;reference::Renderer renderer;Collector c;
    if(!renderer.bind(p)||!cursor.start(p.schedule(),p.schedule().owner(),p.schedule().binding()))throw std::runtime_error("bind");
    std::vector<float> pcm;
    for(int block=0;block<100;++block) {
        const auto begin=cursor.snapshot().processedThrough;c.count=0;
        const bool running=cursor.process(4096,p.schedule().owner(),collect,&c,boundary,nullptr);
        const auto end=cursor.snapshot().processedThrough;std::size_t e=0;
        for(auto frame=begin;frame<end;++frame) {
            while(e<c.count && c.facts[e].frame==frame)if(!renderer.accept(c.facts[e++]))throw std::runtime_error("fact");
            float sample{};if(!renderer.sampleFrame(frame,sample))throw std::runtime_error("sample");pcm.push_back(sample);
        }
        while(e<c.count) {if(c.facts[e].frame!=end||!renderer.accept(c.facts[e]))throw std::runtime_error("end fact");++e;}
        if(!running) {if(renderer.failed())throw std::runtime_error("renderer failed");renderer.stop();return pcm;}
    }
    throw std::runtime_error("watchdog");
}
}
int main() {
 try {
    auto m=model(true);auto v=music::validate(m);require(v.validReference(),"source-bound 32-contact model validates");
    auto readiness=music::assessReadiness(*v.model,{{music::Attack::Picked},false,true,true});
    require(readiness.technicallyRenderable&&!readiness.curriculumPlaybackAuthorized,"technical readiness without runtime admission");
    const auto p=reference::compile(v.model,config());
    require(p.voices().size()==32&&p.backingVoices().size()==4,"32 melodic voices and four distinct backing voices");
    bool exact=true;for(int i=0;i<4;++i){const auto& b=p.backingVoices()[i];exact&=b.midi==(i%2?54:57)&&b.onset==Rational{i*8}&&b.end==Rational{(i+1)*8};}
    require(exact&&p.schedule().events().size()==72,"A/F#/A/F# section gates are scheduled and rendered");
    auto pcm=render(p);require(pcm.size()==128000,"synchronized renderer completed exact 32-quarter cycle");
    auto baseline=music::validate(model(false));require(baseline.validReference(),"baseline no-backing model validates");
    auto dry=render(reference::compile(baseline.model,config()));
    bool audibleDifference=false;for(auto frame:std::array<std::size_t,4>{{2000,34000,66000,98000}})
        audibleDifference|=std::abs(pcm[frame]-dry[frame])>0.0001f;
    require(audibleDifference,"backing contributes nonzero PCM, not a silent declaration");
    auto contactDrift=m;contactDrift.events[7].tones[0].midi++;
    require(!music::validate(contactDrift).validReference(),"contact drift refused");
    auto swapped=m;swapped.backing->sections[1].midi=57;swapped.backing->sections[1].centerPitchClass=9;
    require(!music::validate(swapped).validReference(),"swapped center refused");
    auto unsupported=m;unsupported.backing->levelMilli=90;
    require(!music::validate(unsupported).validReference(),"unsupported level default refused");
    auto unrendered=m;unrendered.backing->sections.clear();
    require(!music::validate(unrendered).validReference(),"unrendered declared backing refused");
    if(const auto* root=std::getenv("FATHOM_L039_PRIVATE_PACKET_ROOT")) {
        const auto base=std::filesystem::path(root);
        const auto original=std::filesystem::path(std::getenv("FATHOM_L039_ORIGINAL_ROOT"));
        const auto packet=original/"Build/level-oracle/levels/level039/expanded-r01/producer-r01/packet";
        const auto profile=content::readBounded(base/"private-expected-profile.json",2*1024*1024);
        content::Input input{content::readBounded(base/"positive.json",2*1024*1024),
            content::readBounded(packet/"identity-registry.json",2*1024*1024),profile,content::sha256(profile),original};
        auto parsed=content::validate(input);
        require(parsed.validReference&&parsed.variants.size()==1&&parsed.variants[0].readiness.technicallyRenderable,
            "frozen source packet plus private Version1 binding validates natively");
        require(parsed.variants[0].validation.model && parsed.variants[0].source.events.size()==32
            && parsed.variants[0].source.backing && parsed.variants[0].source.backing->sections.size()==4,
            "canonical projection retains 32 contacts plus separate typed backing");
        auto integrated=reference::compile(parsed.variants[0].validation.model,config());
        require(integrated.voices().size()==32&&integrated.backingVoices().size()==4,
            "canonical model reaches four-voice backing renderer");
        require(render(integrated).size()==128000,"canonical Version1 renders one exact cycle");
    }
    return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
}
