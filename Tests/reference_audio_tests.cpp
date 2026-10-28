#include "reference_audio_fixtures.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

using namespace fathom;
using namespace reference_fixtures;
namespace {
int checks=0;
void expect(bool ok,const std::string& label) {++checks;if(!ok)throw std::runtime_error(label);std::cout<<"PASS "<<label<<'\n';}
template<class F>void rejects(F f,const std::string& label){bool threw=false;try{f();}catch(const std::exception&){threw=true;}expect(threw,label);}
struct Trace {std::vector<scheduler::Fact> facts;std::vector<float> pcm;};
struct Collector {std::array<scheduler::Fact,scheduler::maxCallbackEvents> facts{};std::size_t count{};std::uint64_t stopAfter{1};const reference::Program* next{};};
bool collect(void* p,const scheduler::Fact& f) noexcept {auto& c=*static_cast<Collector*>(p);if(c.count==c.facts.size())return false;c.facts[c.count++]=f;return true;}
scheduler::BoundaryDecision boundary(void* p,const scheduler::Fact& f) noexcept {auto& c=*static_cast<Collector*>(p);if(f.cycle>=c.stopAfter)return {scheduler::BoundaryAction::Stop,nullptr};if(f.cycle==1 && c.next)return {scheduler::BoundaryAction::Tempo,&c.next->schedule()};return {};}
Trace render(const reference::Program& p,std::uint32_t block=256,std::uint64_t cycles=1,const reference::Program* next=nullptr) {
    scheduler::Cursor cursor;reference::Renderer renderer;Collector c;c.stopAfter=cycles;c.next=next;
    if(!renderer.bind(p) || !cursor.start(p.schedule(),p.schedule().owner(),p.schedule().binding()))throw std::runtime_error("fixture start");
    Trace out;
    for(std::size_t iteration=0;iteration<1000000;++iteration) {
        const auto begin=cursor.snapshot().processedThrough;c.count=0;
        const bool running=cursor.process(block,p.schedule().owner(),collect,&c,boundary,&c);
        const auto end=cursor.snapshot().processedThrough;std::size_t event=0;
        for(auto frame=begin;frame<end;++frame) {
            while(event<c.count && c.facts[event].frame==frame) {
                const auto& f=c.facts[event++];if(!renderer.accept(f))throw std::runtime_error("renderer fact");
                if(next && f.kind==scheduler::FactKind::CycleCompleted && f.cycle==1 && !renderer.selectTempo(*next))throw std::runtime_error("renderer tempo");
            }
            float sample{};if(!renderer.sampleFrame(frame,sample))throw std::runtime_error("renderer sample");out.pcm.push_back(sample);
        }
        while(event<c.count) {const auto& f=c.facts[event++];if(f.frame!=end || !renderer.accept(f))throw std::runtime_error("terminal fact");}
        out.facts.insert(out.facts.end(),c.facts.begin(),c.facts.begin()+static_cast<std::ptrdiff_t>(c.count));
        if(!running){if(cursor.snapshot().reason!=scheduler::StopReason::Requested || renderer.failed())throw std::runtime_error("unexpected terminal");renderer.stop();return out;}
    }
    throw std::runtime_error("fixture watchdog");
}
void dump(const std::filesystem::path& dir,const std::string& name,const reference::Program& p,const Trace& t) {
    std::filesystem::create_directories(dir);
    std::ofstream raw(dir/(name+".f32"),std::ios::binary);raw.write(reinterpret_cast<const char*>(t.pcm.data()),static_cast<std::streamsize>(t.pcm.size()*sizeof(float)));
    std::ofstream facts(dir/(name+"-facts.csv"));facts<<"kind,frame,cycle,sourceEvent,role,action\n";for(auto& f:t.facts)facts<<int(f.kind)<<','<<f.frame<<','<<f.cycle<<','<<f.sourceEvent<<','<<int(f.role)<<','<<int(f.action)<<'\n';
    std::ofstream voices(dir/(name+"-voices.csv"));voices<<"index,string,midi,hz,startN,startD,endN,endD,sourceEvents\n";std::size_t i=0;
    for(auto& v:p.voices()){voices<<++i<<','<<v.string<<','<<v.midi<<','<<std::setprecision(17)<<v.hz<<','<<v.startFrames.n<<','<<v.startFrames.d<<','<<v.endFrames.n<<','<<v.endFrames.d<<',';for(auto& id:v.sourceEvents)voices<<id<<';';voices<<'\n';}
    std::ofstream meta(dir/(name+".txt"));meta<<"Technical projection only; no runtime curriculum admission or human listening.\nitem="<<p.source().source().itemId<<"\nschema="<<p.source().source().schemaVersion<<"\ncontent="<<p.source().source().contentVersion<<"\nrevision="<<p.source().source().contentRevision<<"\nsynthetic="<<p.source().source().syntheticFixture<<"\nproposalExample="<<p.source().source().proposalExample<<"\nrate="<<p.schedule().sampleRate()<<"\nframes="<<t.pcm.size()<<"\nmethod="<<int(p.method())<<"\n";
}
}
int main(int argc,char**argv) {
 try {
    auto controls=controlExamples();const std::filesystem::path output=argc==2?argv[1]:"";
    auto run=[&](const std::string& name,const music::Model& m,reference::Configuration c){auto p=reference::compile(checked(m),c);auto t=render(p);expect(!t.pcm.empty(),name+" runs exact shared cursor");if(!output.empty())dump(output,name,p,t);return p;};
    const auto& level48=controls[6];
    auto level48Validation=music::validate(level48);
    expect(level48.itemId=="fg:item:000007" && !level48.syntheticFixture && level48.proposalExample &&
           level48.preservedRecordJson.find("\"runtime_eligible\":false")!=std::string::npos,
           "Level48 source candidate retains explicit non-runtime classification");
    expect(level48Validation.validReference() && level48Validation.model->source().sourceRefs==level48.sourceRefs &&
           std::find(level48.sourceRefs.begin(),level48.sourceRefs.end(),"L48-TXT49-76")!=level48.sourceRefs.end() &&
           level48.preservedRecordJson.find("\"basis\":\"Cnt1&2&3&4& source grid\"")!=std::string::npos &&
           level48.preservedRecordJson.find("\"status\":\"source_defined\"")!=std::string::npos,
           "Level48 keeps its source-defined quarter-grid provenance without admission");
    struct ExpectedRest { const char* id; Rational onset, duration; };
    const std::array<ExpectedRest,4> expectedRests{{
        {"fg:item:000007:event:0003",Rational{1},Rational{1,2}},
        {"fg:item:000007:event:0008",Rational{7,2},Rational{1,2}},
        {"fg:item:000007:event:0011",Rational{5},Rational{1,2}},
        {"fg:item:000007:event:0016",Rational{15,2},Rational{1,2}}
    }};
    bool restsPreserved=true;
    for(const auto& expected:expectedRests) {
        const auto sourceEvent=std::find_if(level48Validation.model->source().events.begin(),level48Validation.model->source().events.end(),[&](const auto& e){return e.id==expected.id;});
        const auto projection=std::find_if(level48Validation.model->projections().begin(),level48Validation.model->projections().end(),[&](const auto& e){return e.eventId==expected.id;});
        restsPreserved=restsPreserved && sourceEvent!=level48Validation.model->source().events.end() &&
            projection!=level48Validation.model->projections().end() && sourceEvent->kind==music::Kind::Rest &&
            sourceEvent->sourceRef=="L48-TXT49-76" && sourceEvent->span.onset && *sourceEvent->span.onset==expected.onset &&
            sourceEvent->span.duration && *sourceEvent->span.duration==expected.duration && sourceEvent->scopeStrings.empty() &&
            projection->kind==music::Kind::Rest && projection->span==sourceEvent->span;
    }
    expect(restsPreserved,"four Level48 Rest identities/source refs/rational spans survive validation without invented scope");
    const auto level48Readiness=music::assessReadiness(*level48Validation.model,{{music::Attack::Picked,music::Attack::Held},false,true,true});
    auto hasIssue=[&](const std::string& event,const std::string& code){return std::any_of(level48Readiness.issues.begin(),level48Readiness.issues.end(),[&](const auto& issue){return issue.event==event && issue.code==code;});};
    bool techniquesRefused=!level48Readiness.technicallyRenderable && !level48Readiness.curriculumPlaybackAuthorized;
    for(const auto* id:{"fg:item:000007:event:0002","fg:item:000007:event:0005","fg:item:000007:event:0006","fg:item:000007:event:0010","fg:item:000007:event:0014"})
        techniquesRefused=techniquesRefused && hasIssue(id,"unsupported_technique");
    bool restScopesUnresolved=true;
    for(const auto& expected:expectedRests)restScopesUnresolved=restScopesUnresolved && hasIssue(expected.id,"unresolved_scope");
    expect(techniquesRefused && restScopesUnresolved,"Level48 readiness reports unsupported techniques and unresolved authored Rest scope");
    std::string level48Refusal;
    try { (void)reference::compile(level48Validation.model,config(Rational{8})); }
    catch(const std::exception& error) { level48Refusal=error.what(); }
    expect(level48Refusal.find("fg:item:000007:event:0003")!=std::string::npos &&
           level48Refusal.find("unresolved_scope")!=std::string::npos,
           "ReferenceAudio refuses the unchanged Level48 source before any Program or PCM exists");
    auto l12=run("l12",controls[2],config(Rational{8}));expect(l12.voices().size()==16 && l12.voices()[7].midi==57 && l12.voices()[8].midi==57,"L12 two picked octave roots preserved");expect(l12.source().source().preservedRecordJson==controls[2].preservedRecordJson,"entire source/non-TAB metadata retained");
    auto l15=run("l15",controls[3],config(Rational{1}));expect(l15.voices()[1].startFrames.n==7350,"L15 exact triplet onset");
    auto e=run("chord-E",chord(false),config(Rational{5,2}));auto em=run("chord-Em",chord(true),config(Rational{5,2}));expect(e.voices().size()==6 && e.voices()[3].midi==56 && em.voices()[3].midi==55,"L49 simultaneous E/Em exact source voicings and synthetic timing");
    auto h=run("held",held(),config(Rational{3,2}));auto picked=run("repicked",held(true),config(Rational{3,2}));expect(h.voices().size()==1 && h.voices()[0].sourceEvents.size()==2 && picked.voices().size()==2,"held chain coalesces, repeated pick does not");
    auto contact=run("contact-air",air(),config(Rational{2}));auto ct=render(contact);expect(ct.pcm[6000]!=0 && std::all_of(ct.pcm.begin()+22050,ct.pcm.end(),[](float v){return v==0;}),"air keeps explicit gate then exact rest silence");
    auto bound=run("contacts",contacts(),config(Rational{9,2}));expect(bound.voices().size()==24 && bound.source().source().events.size()==17,"L58 four bound contacts and twelve air slots retain24 voices");
    for(const auto& rateTempo:std::array<std::pair<std::uint32_t,std::uint16_t>,2>{{{48000,120},{44100,137}}}) {
        const auto suffix="-"+std::to_string(rateTempo.first)+"-"+std::to_string(rateTempo.second);
        run("l12"+suffix,controls[2],config(Rational{8},rateTempo.first,rateTempo.second));
        run("l15"+suffix,controls[3],config(Rational{1},rateTempo.first,rateTempo.second));
        run("chord-E"+suffix,chord(false),config(Rational{5,2},rateTempo.first,rateTempo.second));
        run("chord-Em"+suffix,chord(true),config(Rational{5,2},rateTempo.first,rateTempo.second));
        run("held"+suffix,held(),config(Rational{3,2},rateTempo.first,rateTempo.second));
        run("repicked"+suffix,held(true),config(Rational{3,2},rateTempo.first,rateTempo.second));
        run("contacts"+suffix,contacts(),config(Rational{9,2},rateTempo.first,rateTempo.second));
    }
    auto sustain=air();sustain.events[1].contact=music::Contact::Sustain;sustain.events[1].scopeStrings={6};
    auto sustained=reference::compile(checked(sustain),config(Rational{2}));expect(render(sustained).pcm==ct.pcm,"explicit covering Sustain changes no attack or gate");
    auto scoped=synthetic("scoped-release");scoped.events={note("s1",Rational{},Rational{1},1,0,40),note("s2",Rational{},Rational{2},2,0,45)};
    music::Event release;release.id="release-s1";release.kind=music::Kind::Contact;release.contact=music::Contact::Release;release.span={Rational{1},Rational{}};release.scopeStrings={1};scoped.events.push_back(release);
    auto scopep=reference::compile(checked(scoped),config(Rational{2}));auto scopeTrace=render(scopep);expect(scopeTrace.pcm[25000]!=0,"scoped release leaves other explicit string gate sounding");
    auto ht=render(h);expect(std::all_of(ht.pcm.begin()+22050,ht.pcm.end(),[](float v){return v==0;}),"held endpoint leaves full authored rest");
    for(auto idx:{0,5,6,7,8})rejects([&]{reference::compile(checked(controls[static_cast<std::size_t>(idx)]),config(Rational{16}));},"unresolved/unsupported original control refuses "+std::to_string(idx));
    for(auto attack:{music::Attack::HammerOn,music::Attack::PullOff,music::Attack::SlideArrival,music::Attack::Bend,music::Attack::BlueThirdShade,music::Attack::Harmonic,music::Attack::Vibrato}) {
        auto m=synthetic("unsupported");m.events={note("n",Rational{},Rational{1})};m.events[0].tones[0].attack=attack;
        rejects([&]{reference::compile(checked(m),config());},"unsupported technique refused "+std::to_string(int(attack)));
    }
    auto ch=chord(false);ch.events.pop_back();auto heldChord=ch.events[0];heldChord.id="held-chord";heldChord.span={Rational{2},Rational{1}};for(auto& t:heldChord.tones){t.attack=music::Attack::Held;t.tieFrom=ch.events[0].id;t.memberSpan=heldChord.span;}ch.events.push_back(heldChord);rejects([&]{reference::compile(checked(ch),config());},"held chord refused even valid model");
    auto shortGate=synthetic("short");shortGate.events={note("n",Rational{1,44100},Rational{1,44100})};rejects([&]{reference::compile(checked(shortGate),config());},"subsample gate refuses before later anchor collapse");
    rejects([&]{reference::compile(checked(held()),config(Rational{1}));},"rest/phrase cutpoint cannot truncate original span");
    auto invalid=config();invalid.method=static_cast<reference::Method>(99);rejects([&]{reference::compile(checked(held()),invalid);},"invalid method refuses");
    auto model=checked(controls[2]);auto initial=config(Rational{8},44100,132);initial.intro=Rational{1,3};auto p=reference::compile(model,initial);auto variant=initial;variant.intro=Rational{};variant.bpm=137;auto q=reference::compile(model,variant);
    auto a=render(p,127,7,&q),b=render(p,512,7,&q);expect(a.pcm==b.pcm,"fractional intro/cycle/tempo partitions bit-identical");expect(p.compatibleTempo(q),"same immutable source tempo replacement allowed");
    auto changedSource=reference::compile(checked(controls[2]),variant);expect(!p.compatibleTempo(changedSource),"same IDs/equivalent but different source snapshot cannot hotreplace");variant.method=reference::Method::Sine;auto changedMethod=reference::compile(model,variant);expect(!p.compatibleTempo(changedMethod),"same schedule different method cannot hotreplace");
    auto bad=config();bad.owner={};rejects([&]{reference::compile(model,bad);},"invalid owner refuses");bad=config();bad.rate=0;rejects([&]{reference::compile(model,bad);},"invalid sample rate refuses");
    for(auto rate:{8000U,44100U,48000U,96000U,192000U}) {
        auto cp=reference::compile(checked(held()),config(Rational{3,2},rate));auto t=render(cp,257);
        expect(t.pcm.size()==static_cast<std::size_t>(rate*3/4),"observed-rate parameterization "+std::to_string(rate));
    }
    guitar::Setup setup;
    for(auto preset:{guitar::Preset::Standard,guitar::Preset::EFlat,guitar::Preset::DropD}) {
        setup.openMidi=guitar::tuning(preset);setup.capo=2;
        for(int string=1;string<=6;++string) {
            auto op=reference::tuningTone(setup,string,reference::ToneTarget::OpenString,owner(),62,44100);
            auto cap=reference::tuningTone(setup,string,reference::ToneTarget::CapoPosition,owner(),62,44100);
            expect(op.voices()[0].midi==setup.openMidi[static_cast<std::size_t>(string-1)] && cap.voices()[0].midi==op.voices()[0].midi+2,"open/capo tone distinction "+std::to_string(int(preset))+":"+std::to_string(string));
        }
    }
    guitar::Setup identity;identity.capo=2;
    const auto tone=[&](const guitar::Setup& selected,int string,reference::ToneTarget target,reference::Method method=reference::Method::Sine) {
        return reference::tuningTone(selected,string,target,owner(),62,44100,method);
    };
    const auto baseTone=tone(identity,1,reference::ToneTarget::OpenString);
    const auto sameTone=tone(identity,1,reference::ToneTarget::OpenString);
    expect(baseTone.schedule().sourceBinding()==sameTone.schedule().sourceBinding() &&
           baseTone.schedule().compatibleTempo(sameTone.schedule()),"identical tuning selection has stable scheduler source identity");
    expect(baseTone.schedule().sourceBinding().size()<1024,"tuning source identity fits scheduler bound");
    const auto different=[&](const reference::Program& candidate,const std::string& label) {
        expect(baseTone.schedule().sourceBinding()!=candidate.schedule().sourceBinding() &&
               !baseTone.schedule().compatibleTempo(candidate.schedule()),label);
    };
    different(tone(identity,2,reference::ToneTarget::OpenString),"selected string changes scheduler source identity");
    different(tone(identity,1,reference::ToneTarget::CapoPosition),"selected target changes scheduler source identity");
    auto changed=identity;++changed.openMidi[0];
    different(tone(changed,1,reference::ToneTarget::OpenString),"tuning changes scheduler source identity");
    changed=identity;++changed.capo;
    different(tone(changed,1,reference::ToneTarget::OpenString),"capo changes scheduler source identity even for open pitch");
    changed=identity;++changed.fretCount;
    different(tone(changed,1,reference::ToneTarget::OpenString),"neck extent changes scheduler source identity");
    changed=identity;changed.handedness=guitar::Handedness::Left;
    different(tone(changed,1,reference::ToneTarget::OpenString),"orientation changes scheduler source identity");
    different(tone(identity,1,reference::ToneTarget::OpenString,reference::Method::Pluck),"synthesis method changes scheduler source identity");
    setup.openMidi={0,25,50,75,100,127};setup.capo=0;setup.fretCount=0;
    auto high=reference::tuningTone(setup,6,reference::ToneTarget::OpenString,owner(),62,44100,reference::Method::Sine);expect(high.voices()[0].midi==127,"explicit high custom sine supported below Nyquist");rejects([&]{reference::tuningTone(setup,6,reference::ToneTarget::OpenString,owner(),62,44100,reference::Method::Pluck);},"no silent aliased pluck fallback");
    auto left=setup;left.handedness=guitar::Handedness::Left;auto lp=reference::tuningTone(left,6,reference::ToneTarget::OpenString,owner(),62,44100);expect(render(high).pcm==render(lp).pcm,"handedness changes no reference pitch");
    if(!output.empty()){dump(output,"custom-high-sine",high,render(high));setup={};auto standard=reference::tuningTone(setup,1,reference::ToneTarget::OpenString,owner(),62,44100);dump(output,"standard-open-E",standard,render(standard));}
    // Requirement-derived malformed stream cases use genuine scheduled first facts.
    auto trace=render(l12);const auto first=trace.facts.front();
    {reference::Renderer rr;expect(rr.bind(l12),"renderer binds once");expect(!rr.bind(l12),"renderer refuses rebind");expect(rr.accept(first),"genuine first event accepted");expect(!rr.accept(first) && rr.failed(),"duplicate event latches failure");float value=9;expect(!rr.sampleFrame(0,value)&&value==0,"failed renderer stays silent");}
    for(int mutation=0;mutation<5;++mutation){reference::Renderer rr;rr.bind(l12);auto f=first;if(mutation==0)++f.owner.generation;if(mutation==1)++f.binding;if(mutation==2)++f.frame;if(mutation==3)++f.sourceEvent;if(mutation==4)++f.cycle;expect(!rr.accept(f)&&rr.failed(),"stale/malformed event refuses "+std::to_string(mutation));}
    {reference::Renderer rr;rr.bind(l12);float value=4;expect(!rr.sampleFrame(0,value)&&value==0,"omitted due attack cannot silently render");}
    {reference::Renderer rr;rr.bind(l12);expect(!rr.selectTempo(q),"tempo cannot change outside boundary");}
    {reference::Renderer rr;rr.bind(l12);rr.accept(first);float value{};expect(rr.sampleFrame(0,value),"first sample accepted");expect(!rr.sampleFrame(0,value)&&value==0,"duplicate sample refuses");}
    {reference::Renderer rr;rr.bind(l12);rr.accept(first);rr.stop();float value=5;expect(!rr.sampleFrame(0,value)&&value==0 && !rr.bind(l12),"immediate stop cannot implicitly resume or rebind");}
    expect(reference::frequency(69)==440 && reference::sample(reference::Method::Pluck,440,44100,44100,44100)==0,"formula pitch/gate boundary");
    std::cout<<"CHECKS "<<checks<<" PASS\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<" after "<<checks<<" checks\n";return 1;}
}
