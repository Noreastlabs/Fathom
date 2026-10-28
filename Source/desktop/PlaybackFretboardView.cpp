#include "desktop/PlaybackFretboardView.hpp"
#include <algorithm>
#include <set>
#include <map>
#include <stdexcept>
namespace fathom::desktop {
namespace {
std::string name(int midi, PlaybackFretboardView::Spelling spelling) {
    static const char* sharp[]{"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};
    static const char* flat[]{"C","Db","D","Eb","E","F","Gb","G","Ab","A","Bb","B"};
    return (spelling == PlaybackFretboardView::Spelling::Sharp ? sharp : flat)[midi % 12];
}
juce::Colour letterColour(char letter) {
    // Letter identity is also printed; colour never carries the only meaning.
    switch(letter) {
        case 'A': return juce::Colour(0xfff4be72);
        case 'B': return juce::Colour(0xffb6c6ff);
        case 'C': return juce::Colour(0xff89d8c8);
        case 'D': return juce::Colour(0xfff49ba5);
        case 'E': return juce::Colour(0xffddd084);
        case 'F': return juce::Colour(0xffc8a7eb);
        default: return juce::Colour(0xff8fc7ee);
    }
}
juce::Colour fingerColour(const std::string& finger) {
    if(finger == "1") return juce::Colour(0xff89d8c8);
    if(finger == "2") return juce::Colour(0xfff4be72);
    if(finger == "3") return juce::Colour(0xffb6c6ff);
    if(finger == "4") return juce::Colour(0xfff49ba5);
    return juce::Colour(0xffc4cad4);
}
}
PlaybackFretboardView::PlaybackFretboardView() { setInterceptsMouseClicks(false, false); setTitle("Playback fretboard - declared tuning display only; audio and authored source unchanged"); rebuild(); }
void PlaybackFretboardView::setSetup(const guitar::Setup& value) {
    if(!guitar::validate(value).empty()) throw std::invalid_argument("Invalid declared guitar setup");
    setup_ = value; rebuild();
}
void PlaybackFretboardView::setMode(Mode value) {
    if(value!=Mode::Basic && value!=Mode::Finger && value!=Mode::Note) throw std::invalid_argument("Invalid fretboard mode");
    mode_ = value; repaint();
}
void PlaybackFretboardView::setSpelling(Spelling value) {
    if(value!=Spelling::Sharp && value!=Spelling::Flat) throw std::invalid_argument("Invalid note spelling");
    if(spelling_==value) return; spelling_ = value; rebuild();
}
void PlaybackFretboardView::setModel(std::shared_ptr<const music::ValidatedModel> value) {
    model_ = std::move(value); activeEvents_.clear();activeTones_.clear();exactTones_=false; rebuild();
}
void PlaybackFretboardView::setActiveEvents(const std::vector<std::string>& value) {
    if(!exactTones_ && activeEvents_==value) return; exactTones_=false;activeTones_.clear();activeEvents_ = value; rebuild();
}
void PlaybackFretboardView::setActiveTones(const std::vector<ActiveTone>& value) {
    if(exactTones_ && activeTones_==value)return;
    exactTones_=true;activeEvents_.clear();activeTones_=value;rebuild();
}
void PlaybackFretboardView::clear() { model_.reset(); activeEvents_.clear();activeTones_.clear();exactTones_=false; rebuild(); }
void PlaybackFretboardView::rebuild() {
    struct ActivePosition { std::set<std::string> fingers; bool unspecified{}; std::vector<std::string> ids; };
    std::map<std::pair<int,int>,ActivePosition> positions;
    const std::set<std::string> active(activeEvents_.begin(),activeEvents_.end());
    if(model_) for(const auto& event:model_->source().events) {
        const bool pitched=event.kind==music::Kind::Note || event.kind==music::Kind::Chord ||
            (event.kind==music::Kind::Contact && event.contact==music::Contact::Pitched);
        if(!pitched || (!exactTones_ && active.count(event.id)==0))continue;
        for(const auto& tone:event.tones) {
            if(exactTones_ && std::find(activeTones_.begin(),activeTones_.end(),ActiveTone{event.id,tone.string,tone.fret})==activeTones_.end())continue;
            auto& value=positions[{tone.string,tone.fret}];
            if(std::find(value.ids.begin(),value.ids.end(),event.id)==value.ids.end()) value.ids.push_back(event.id);
            if(tone.finger.empty()) value.unspecified=true; else value.fingers.insert(tone.finger);
        }
    }
    std::vector<Cell> next; next.reserve(150);
    for(int string=1; string<=6; ++string) for(int fret=0; fret<=24; ++fret) {
        const auto position = guitar::position(setup_,string,fret);
        Cell cell; cell.internalString=string;cell.relativeFret=fret;
        cell.physicalFret=static_cast<int>(position.physicalFret);
        cell.available=position.available();cell.midi=position.midi.value_or(-1);
        if(cell.midi>=0) cell.note=name(cell.midi,spelling_);
        const auto found=positions.find({string,fret});
        if(found!=positions.end()) {
            const auto& value=found->second;
            cell.active=true;cell.eventIds=value.ids;
            cell.fingerUnknown=value.unspecified || value.fingers.size()!=1;
            cell.finger=cell.fingerUnknown ? "?" : *value.fingers.begin();
        }
        next.push_back(std::move(cell));
    }
    cells_=std::move(next);repaint();
}
juce::Rectangle<float> PlaybackFretboardView::cellBounds(int string,int fret) const {
    if(string<1 || string>6 || fret<0 || fret>24) return {};
    const auto board=juce::Rectangle<float>(64.0f,30.0f,
        std::max(0.0f,static_cast<float>(getWidth())-72.0f),
        std::max(0.0f,static_cast<float>(getHeight())-38.0f));
    const float cw=board.getWidth()/25.0f, rh=board.getHeight()/6.0f;
    return {board.getX()+guitar::fretColumn(fret,25,setup_.handedness)*cw,
            board.getY()+(6-string)*rh,cw,rh};
}
void PlaybackFretboardView::paint(juce::Graphics& g) {
    g.fillAll(juce::Colour(0xff17202b));
    g.setColour(juce::Colours::white);g.setFont(12.0f);
    for(int fret=0;fret<=24;++fret) {
        const auto b=cellBounds(6,fret);
        g.drawText(juce::String(fret),juce::Rectangle<float>(b.getX(),5,b.getWidth(),18),juce::Justification::centred);
    }
    for(int string=1;string<=6;++string) {
        const auto b=cellBounds(string,0);
        const int openMidi=setup_.openMidi[static_cast<std::size_t>(string-1)];
        const auto tuning=name(openMidi,spelling_)+std::to_string(openMidi/12-1);
        g.setColour(juce::Colour(0xffdce2ea));g.setFont(12.0f);
        g.drawText(juce::String(guitar::displayString(string))+"  "+juce::String(tuning),
                   juce::Rectangle<float>(3,b.getY(),57,b.getHeight()),juce::Justification::centredLeft);
    }
    for(const auto& cell:cells_) {
        const auto b=cellBounds(cell.internalString,cell.relativeFret);
        g.setColour(juce::Colour(0xff657181));g.drawLine(b.getX(),b.getCentreY(),b.getRight(),b.getCentreY(),1.0f);
        g.setColour(juce::Colour(0xff374455));g.drawVerticalLine(static_cast<int>(b.getRight()),b.getY(),b.getBottom());
        if(!cell.available) { g.setColour(juce::Colour(0xff657181));g.drawText(juce::String::charToString(0x2013),b,juce::Justification::centred);continue; }
        if(!cell.active && mode_==Mode::Finger) continue;
        const auto diameter=std::max(0.0f,std::min(b.getWidth()-3,b.getHeight()-6));
        const auto circle=juce::Rectangle<float>(diameter,diameter).withCentre(b.getCentre());
        auto colour=juce::Colour(0xffdce2ea);
        std::string label;
        if(mode_==Mode::Finger) { colour=fingerColour(cell.finger);label=cell.finger; }
        if(mode_==Mode::Note) { colour=letterColour(cell.note.front());label=cell.note; }
        if(mode_==Mode::Note) {
            if(cell.active) { g.setColour(juce::Colour(0xff253342));g.fillEllipse(circle); }
            colour=cell.active ? colour : colour.withMultipliedAlpha(0.55f);
            g.setColour(colour);g.drawEllipse(circle,cell.active ? 2.0f : 1.2f);
        } else {
            g.setColour(colour);
            if(cell.active) g.fillEllipse(circle);else g.drawEllipse(circle,1.2f);
        }
        if(!label.empty()) {
            g.setColour(mode_==Mode::Note ? colour : (cell.active ? juce::Colour(0xff101722) : colour));
            g.setFont(std::min(14.0f,std::max(8.0f,diameter*0.53f)));
            auto painted=juce::String(label);
            if(mode_==Mode::Note) painted=painted.replace("#",juce::String::charToString(0x266f)).replace("b",juce::String::charToString(0x266d));
            g.drawText(painted,circle,juce::Justification::centred);
        }
    }
}
}
