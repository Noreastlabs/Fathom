#pragma once
#include "core/PracticeTransport.hpp"
#include "core/ReferenceAudio.hpp"
#include <stdexcept>
namespace practice_fixtures {
using namespace fathom;
inline scheduler::Owner owner(){scheduler::Owner o;o.id[0]=32;o.id[6]=0x40;o.id[8]=0x80;o.generation=1;o.epoch=1;return o;}
inline practice::Configuration config(std::uint32_t rate=8000){practice::Configuration c;c.rate=rate;c.bpm=120;c.span=Rational{4};c.meter={{4,4}};c.faithfulWholeSpan=true;c.targetCycles=2;return c;}
inline std::shared_ptr<const music::ValidatedModel> model(){
 music::Model m;m.itemId="synthetic:practice-transport";m.schemaVersion="qa1";m.contentVersion="qa1";m.syntheticFixture=true;m.proposalExample=false;m.instrument={{40,45,50,55,59,64},0};
 music::Event a;a.id="picked-E";a.span={Rational{},Rational{1}};music::Tone t;t.string=1;t.midi=40;t.fret=0;a.tones={t};
 auto b=a;b.id="held-E";b.span={Rational{1},Rational{1}};b.tones[0].attack=music::Attack::Held;b.tones[0].tieFrom=a.id;
 music::Event rest;rest.id="full-rest";rest.kind=music::Kind::Rest;rest.span={Rational{2},Rational{2}};rest.scopeStrings={1,2,3,4,5,6};
 m.events={a,b,rest};m.measures={{"synthetic:bar",Rational{},4,4,{a.id,b.id,rest.id},true}};
 auto v=music::validate(m);if(!v.model)throw std::runtime_error("Synthetic practice fixture invalid");return v.model;
}
inline reference::Configuration referenceConfig(const practice::Configuration& c,scheduler::Owner o=owner()){
 reference::Configuration r;r.owner=o;r.binding=o.generation;r.sourceBinding="synthetic:practice-transport:qa1";r.rate=c.rate;r.bpm=c.bpm;r.unit=c.unit;r.cycle=c.span;r.intro=practice::countInSpan(c);return r;
}
}
