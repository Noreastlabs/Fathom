#include "core/TabPresentation.hpp"
#include <algorithm>
#include <sstream>
#include <stdexcept>

namespace fathom::tab {
namespace {
bool contains(const music::Span& s,const Rational& p) {
    return s.onset && s.duration && !(*s.duration==Rational{}) && !(p<*s.onset) && p<(*s.onset+*s.duration);
}
std::string scope(const std::vector<int>& strings,int count) {
    if(strings.empty())return "unspecified";
    std::string s;
    for(int v:strings){if(!s.empty())s+=", ";s+=std::to_string(count+1-v);}
    return s;
}
}
Document::Document(std::shared_ptr<const music::ValidatedModel> m):model_(std::move(m)) {
    if(!model_)throw std::invalid_argument("TAB requires a validated immutable musical model");
}
const music::Event* Document::event(const std::string& id) const noexcept {
    const auto& events=source().events;
    const auto it=std::find_if(events.begin(),events.end(),[&](const auto& e){return e.id==id;});
    return it==events.end()?nullptr:&*it;
}
bool Document::allTimed() const noexcept {
    return !source().events.empty() && std::all_of(source().events.begin(),source().events.end(),[](const auto& e){return e.span.onset && e.span.duration;});
}
int Document::displayString(int internal) const {
    if(internal<1 || static_cast<std::size_t>(internal)>source().instrument.openMidi.size())throw std::out_of_range("Unknown TAB string");
    return static_cast<int>(source().instrument.openMidi.size())+1-internal;
}
Position Document::at(const Rational& p) const {
    Position out;
    for(const auto& e:source().events) {
        if(contains(e.span,p))out.events.push_back(e.id);
        if(e.span.onset && e.span.duration && *e.span.duration==Rational{} && *e.span.onset==p)out.instants.push_back(e.id);
        for(const auto& t:e.tones) {
            const auto& gate=e.kind==music::Kind::Contact?t.soundingSpan:std::optional<music::Span>{e.span};
            if(gate && contains(*gate,p))out.sounding.push_back({e.id,t.string});
        }
    }
    return out;
}
std::string fraction(const Rational& r){return std::to_string(r.numerator())+(r.denominator()==1?"":"/"+std::to_string(r.denominator()));}
std::string span(const music::Span& s){return "onset "+(s.onset?fraction(*s.onset):"unspecified")+"; duration "+(s.duration?fraction(*s.duration):"unspecified")+" quarter units";}
std::string contact(music::Contact c){switch(c){case music::Contact::Pitched:return "pitched contact";case music::Contact::Muted:return "muted contact";case music::Contact::Air:return "air stroke";case music::Contact::Release:return "release";case music::Contact::Sustain:return "sustain contact";}throw std::invalid_argument("Unknown contact");}
std::string attack(const music::Tone& t){
    std::string s;
    switch(t.attack){case music::Attack::Picked:s="picked";break;case music::Attack::HammerOn:s="hammer-on";break;case music::Attack::PullOff:s="pull-off";break;case music::Attack::SlideArrival:s="slide arrival";break;case music::Attack::Bend:s="bend";break;case music::Attack::BlueThirdShade:s="blue-third shade";break;case music::Attack::Held:s="held (no new pick)";break;case music::Attack::Harmonic:s="harmonic";break;case music::Attack::Vibrato:s="vibrato";break;}
    if(t.bendSemitones)s+=" "+fraction(*t.bendSemitones)+" semitones";
    if(!t.authoredTechnique.empty())s+="; source: "+t.authoredTechnique;
    if(!t.tieFrom.empty())s+="; from "+t.tieFrom;
    return s;
}
std::string degrees(const music::Tone& t) {
    if(t.degrees.empty())return "unspecified";
    std::string s;
    for(const auto& d:t.degrees){if(!s.empty())s+=" | ";s+=d.sourceLabel+" ["+d.context+"]";}
    return s;
}
std::string noteName(const music::Tone& t){
    if(!t.spelling.empty())return t.spelling+" (authored)";
    static constexpr const char* names[]={"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};
    if(t.midi<0||t.midi>127)throw std::invalid_argument("Invalid MIDI for TAB label");
    return std::string(names[t.midi%12])+std::to_string(t.midi/12-1)+" (derived)";
}
std::string pitch(const music::Tone& t){return noteName(t)+"; MIDI "+std::to_string(t.midi)+(t.spelling.empty()?"; authored spelling unspecified":"");}
std::string Document::overview() const {
    std::ostringstream o;o<<source().itemId<<"\nSchema "<<source().schemaVersion<<"; content "<<source().contentVersion<<"; revision "<<source().contentRevision<<"\n";
    if(source().syntheticFixture)o<<"Synthetic fixture. ";
    if(source().proposalExample)o<<"Proposal/reference example. ";
    o<<"Display is not runtime curriculum admission.\nCapo "<<source().instrument.capo<<"; open MIDI low to high:";
    for(int m:source().instrument.openMidi)o<<' '<<m;
    o<<"\nSource references:\n";for(const auto& ref:source().sourceRefs)o<<ref<<'\n';
    o<<"Measures / sections:\n";
    for(const auto& m:source().measures){o<<m.id<<": start "<<fraction(m.start)<<"; "<<m.numerator<<'/'<<m.denominator<<"; complete coverage "<<(m.requireCompleteCoverage?"required":"not declared")<<"; events:";for(const auto& id:m.eventIds)o<<' '<<id;o<<'\n';}
    o<<"Preserved authored record (read only, not interpreted as notes):\n"<<source().preservedRecordJson;
    return o.str();
}
std::string Document::detail(const std::string& id) const {
    const auto* e=event(id);if(!e)throw std::invalid_argument("Unknown source event: "+id);
    std::ostringstream o;o<<e->id<<"\nSource: "<<e->sourceRef<<"\n"<<span(e->span)<<'\n';
    for(const auto& measure:source().measures)if(std::find(measure.eventIds.begin(),measure.eventIds.end(),id)!=measure.eventIds.end()) {
        const auto end=measure.start+Rational{static_cast<std::int64_t>(measure.numerator)*4,static_cast<std::int64_t>(measure.denominator)};
        o<<"Declared measure "<<measure.id<<": "<<measure.numerator<<'/'<<measure.denominator<<"; start "<<fraction(measure.start)<<"; end "<<fraction(end)<<" quarter units. Event membership is authored; event onset remains separate.\n";
    }
    if(e->kind==music::Kind::Rest)o<<"REST; scope (display strings): "<<scope(e->scopeStrings,static_cast<int>(source().instrument.openMidi.size()))<<'\n';
    if(e->kind==music::Kind::Contact)o<<contact(e->contact)<<"; hand direction "<<(e->handDirection.empty()?"unspecified":e->handDirection)<<"; scope "<<scope(e->scopeStrings,static_cast<int>(source().instrument.openMidi.size()))<<'\n';
    if(!e->chordSymbol.empty())o<<"Chord: "<<e->chordSymbol<<'\n';
    for(const auto& t:e->tones){
        o<<"String "<<displayString(t.string)<<" (internal "<<t.string<<"), fret "<<t.fret<<"; "<<pitch(t)<<"\nFng: "<<(t.finger.empty()?"unspecified":t.finger)<<"; Deg: "<<degrees(t)<<"\nTechnique: "<<attack(t)<<'\n';
        for(const auto& d:t.degrees)o<<"Degree context "<<d.context<<": root pitch class "<<d.rootPitchClass<<"; ordinal "<<d.ordinal<<"; alteration "<<d.alteration<<"; root MIDI "<<(d.rootMidi?std::to_string(*d.rootMidi):"unspecified")<<'\n';
        if(t.memberSpan)o<<"Authored member "<<span(*t.memberSpan)<<'\n';
        if(e->kind==music::Kind::Contact)o<<"Sounding gate: "<<(t.soundingSpan?span(*t.soundingSpan):"unspecified; hand slot is not the sounding gate")<<'\n';
    }
    return o.str();
}
} // namespace fathom::tab
