#pragma once
#include "fixtures/control_model_examples.hpp"
#include "core/ReferenceAudio.hpp"

namespace reference_fixtures {
using namespace fathom;
inline music::Model synthetic(const std::string& name) {
    music::Model m;m.itemId="synthetic:"+name;m.schemaVersion="qa1";m.contentVersion="qa1";m.syntheticFixture=true;m.proposalExample=false;m.instrument={{40,45,50,55,59,64},0};return m;
}
inline music::Event note(const std::string& id,Rational onset,Rational duration,int string=3,int fret=7,int midi=57) {
    music::Event e;e.id=id;e.span={onset,duration};music::Tone t;t.string=string;t.fret=fret;t.midi=midi;e.tones={t};return e;
}
inline music::Event rest(const std::string& id,Rational onset,Rational duration,std::vector<int> scope={1,2,3,4,5,6}) {
    music::Event e;e.id=id;e.kind=music::Kind::Rest;e.span={onset,duration};e.scopeStrings=std::move(scope);return e;
}
inline music::Model chord(bool minor) {
    const auto originals=controlExamples();auto m=originals[7];
    // Original L49 has no authored times. All timings here are synthetic method QA.
    m.syntheticFixture=true;m.proposalExample=true;m.events={m.events[minor?1:0]};m.measures.clear();
    m.events[0].span={Rational{},Rational{2}};
    for(auto& t:m.events[0].tones)t.memberSpan=m.events[0].span;
    m.events.push_back(rest("synthetic:post-chord-rest",Rational{2},Rational{1,2}));return m;
}
inline music::Model held(bool repicked=false) {
    const auto originals=controlExamples();auto m=originals[6];
    m.syntheticFixture=true;m.events={m.events[13],m.events[14],m.events[15]};m.measures.clear();
    // Isolated same retained QA departure: slide arrival replaced by a picked origin.
    m.events[0].span={Rational{},Rational{1,2}};m.events[0].tones[0].attack=music::Attack::Picked;
    m.events[1].span={Rational{1,2},Rational{1,2}};
    if(repicked){m.events[1].tones[0].attack=music::Attack::Picked;m.events[1].tones[0].tieFrom.clear();}
    m.events[2].span={Rational{1},Rational{1,2}};m.events[2].scopeStrings={1,2,3,4,5,6};return m;
}
inline music::Model air() {
    auto m=synthetic("bound-contact-air");auto n=note("pitched-contact",Rational{},Rational{1,4},6,0,64);n.kind=music::Kind::Contact;n.contact=music::Contact::Pitched;n.handDirection="D";n.tones[0].soundingSpan=music::Span{Rational{},Rational{1}};
    music::Event air;air.id="air";air.kind=music::Kind::Contact;air.contact=music::Contact::Air;air.span={Rational{1,4},Rational{1,4}};air.handDirection="U";
    m.events={n,air,rest("rest",Rational{1},Rational{1})};return m;
}
inline music::Model contacts() {
    auto originals=controlExamples();auto m=originals[8];m.syntheticFixture=true;m.measures.clear();m.instrument=originals[7].instrument;
    // Original hand slots and directions retained. Existing method QA explicitly binds
    // every pitched contact to source L49 E with a one-quarter sounding gate.
    const auto chordTones=originals[7].events[0].tones;
    for(auto& e:m.events)if(e.contact==music::Contact::Pitched) {
        e.tones=chordTones;
        for(auto& t:e.tones){t.memberSpan.reset();t.soundingSpan=music::Span{*e.span.onset,Rational{1}};}
    }
    m.events.push_back(rest("synthetic:contacts-final-rest",Rational{4},Rational{1,2}));return m;
}
inline scheduler::Owner owner() {scheduler::Owner o;o.id[6]=0x40;o.id[8]=0x80;o.id[0]=6;o.generation=1;o.epoch=1;return o;}
inline reference::Configuration config(Rational cycle=Rational{4},std::uint32_t rate=44100,std::uint16_t bpm=120) {
    reference::Configuration c;c.owner=owner();c.binding=62;c.sourceBinding="synthetic:reference-component-check";c.cycle=cycle;c.rate=rate;c.bpm=bpm;return c;
}
inline std::shared_ptr<const music::ValidatedModel> checked(const music::Model& m) {
    auto v=music::validate(m);if(!v.validReference())throw std::runtime_error("Invalid test fixture "+m.itemId);return v.model;
}
}
