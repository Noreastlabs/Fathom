#pragma once
#include "reference_audio_fixtures.hpp"

// Independent synthetic witness: low open E, high fret24 E, and two
// enharmonic spellings with identical MIDI but different letter classes.
// Never labels unspecified fingers or these fixtures as learner performance.
namespace playback_fretboard_fixtures {
inline std::shared_ptr<const fathom::music::ValidatedModel> checked(const fathom::music::Model& model){
    auto result=fathom::music::validate(model);
    if(!result.validReference()){
        std::string detail="Invalid synthetic renderer fixture "+model.itemId;
        for(const auto& issue:result.issues)detail+=" | "+issue.event+":"+issue.field+":"+issue.code+":"+issue.explanation;
        throw std::runtime_error(detail);
    }
    return result.model;
}
inline fathom::music::Model source() {
    using namespace fathom;
    auto m=reference_fixtures::synthetic("playback-fretboard-contract");
    auto chord=reference_fixtures::note("simultaneous-open-and-24",Rational{},Rational{1},1,0,40);
    chord.kind=music::Kind::Chord;
    chord.tones[0].finger="O";chord.tones[0].spelling="E";
    auto high=chord.tones[0];high.string=6;high.fret=24;high.midi=88;high.finger="4";high.spelling="E";
    chord.tones.push_back(high);
    auto flat=reference_fixtures::note("flat-A-letter",Rational{1},Rational{1},1,4,44);
    flat.tones[0].spelling="Ab"; // finger intentionally unspecified
    auto sharp=flat;sharp.id="sharp-G-letter";sharp.span.onset=Rational{2};sharp.tones[0].spelling="G#";
    m.events={chord,flat,sharp,reference_fixtures::rest("rest",Rational{3},Rational{1})};
    return m;
}
inline fathom::music::Model contacts() {
    using namespace fathom;
    auto m=reference_fixtures::synthetic("pitched-contact-independent-gates");
    auto e=reference_fixtures::note("pitched-contact",Rational{},Rational{1,4},1,0,40);
    e.kind=music::Kind::Contact;e.contact=music::Contact::Pitched;e.handDirection="D";
    e.tones[0].finger="O";e.tones[0].spelling="E";e.tones[0].soundingSpan=music::Span{Rational{},Rational{1}};
    auto second=e.tones[0];second.string=2;second.midi=45;second.spelling="A";second.soundingSpan=music::Span{Rational{},Rational{2}};e.tones.push_back(second);
    music::Event air;air.id="air-hand-slot";air.kind=music::Kind::Contact;air.contact=music::Contact::Air;air.handDirection="U";air.span={Rational{1,4},Rational{7,4}};
    m.events={e,air,reference_fixtures::rest("after-gates-rest",Rational{2},Rational{1})};
    return m;
}
inline std::array<int,6> openE(){return {{40,47,52,56,59,64}};}
}
