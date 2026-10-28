#pragma once
#include "reference_audio_fixtures.hpp"
#include "core/TabPresentation.hpp"

namespace music_references {
using namespace fathom;
struct PositionCase {
    const char* id;
    std::array<int,6> tuning;
    int capo, string, fret, physical, midi;
    const char* name;
    bool left;
};
// Explicit independent expected values; not derived from the APIs under test.
inline const std::array<PositionCase,10> positions{{
 {"standard-low-open",{40,45,50,55,59,64},0,1,0,0,40,"E2",false},
 {"standard-high-octave",{40,45,50,55,59,64},0,6,12,12,76,"E5",false},
 {"standard-capo-relative",{40,45,50,55,59,64},2,1,3,5,45,"A2",false},
 {"eflat-low-open",{39,44,49,54,58,63},0,1,0,0,39,"D#2",false},
 {"eflat-capo-middle",{39,44,49,54,58,63},1,5,2,3,61,"C#4",false},
 {"dropd-capo-open",{38,45,50,55,59,64},2,1,0,2,40,"E2",false},
 {"dropd-third-string",{38,45,50,55,59,64},0,3,7,7,57,"A3",false},
 {"dadgad-capo",{38,45,50,55,57,62},3,6,2,5,67,"G4",false},
 {"custom-reentrant",{40,45,50,55,69,64},0,5,0,0,69,"A4",false},
 {"left-capo-relative",{40,45,50,55,59,64},4,2,1,5,50,"D3",true}
}};
inline guitar::Setup setup(const PositionCase& c) {
    guitar::Setup s;s.openMidi=c.tuning;s.capo=c.capo;s.handedness=c.left?guitar::Handedness::Left:guitar::Handedness::Right;return s;
}
inline music::Model model(const PositionCase& c) {
    auto m=reference_fixtures::synthetic(std::string("11.2:")+c.id);
    m.instrument.openMidi.assign(c.tuning.begin(),c.tuning.end());m.instrument.capo=c.capo;
    auto n=reference_fixtures::note("position",Rational{},Rational{1},c.string,c.fret,c.midi);
    n.sourceRef=std::string("synthetic:11.2-position-matrix#")+c.id;n.tones[0].finger=c.fret?"2":"O";
    m.events={n,reference_fixtures::rest("rest",Rational{1},Rational{1})};m.events[1].sourceRef=n.sourceRef;
    m.sourceRefs={n.sourceRef};m.measures={{"synthetic:2-4",Rational{},2,4,{"position","rest"},true}};
    m.preservedRecordJson="Synthetic known-position case, not authored course or runtime admission.";return m;
}
inline music::Model held(bool repicked=false) {
    auto m=reference_fixtures::synthetic(repicked?"11.2:repicked":"11.2:held");
    auto a=reference_fixtures::note("picked",Rational{},Rational{1},2,0,45);
    auto b=reference_fixtures::note("continued",Rational{1},Rational{1},2,0,45);
    if(!repicked){b.tones[0].attack=music::Attack::Held;b.tones[0].tieFrom="picked";}
    m.events={a,b,reference_fixtures::rest("rest",Rational{2},Rational{1})};
    m.measures={{"synthetic:3-4",Rational{},3,4,{"picked","continued","rest"},true}};return m;
}
}
