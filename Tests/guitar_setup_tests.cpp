#include "core/GuitarSetup.hpp"
#include "fixtures/control_model_examples.hpp"
#include <algorithm>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace fathom;
using namespace fathom::guitar;
namespace {
int checks = 0;
void expect(bool condition, const char* description) {
    ++checks;
    if (!condition) throw std::runtime_error(description);
    std::cout << "PASS " << description << '\n';
}
bool warning(const Compatibility& c, const std::string& code) {
    return std::any_of(c.warnings.begin(),c.warnings.end(),[&](const auto& i){ return i.code == code; });
}
template<class F> bool rejects(F fn) { try { fn(); } catch (const std::invalid_argument&) { return true; } return false; }
}
int main() {
    try {
        Setup standard;
        expect(validate(standard).empty() && standard.fretCount == 22 && standard.capo == 0,"explicit initial Standard22/no-capo setup");
        expect(tuning(Preset::Standard) == std::array<int,6>{{40,45,50,55,59,64}},"known Standard pitches");
        expect(tuning(Preset::EFlat) == std::array<int,6>{{39,44,49,54,58,63}},"known E-flat pitches");
        expect(tuning(Preset::DropD) == std::array<int,6>{{38,45,50,55,59,64}},"known DropD only lowers low string");
        expect(rejects([]{(void)tuning(static_cast<Preset>(99));}),"unknown preset rejected");
        for (const auto preset : {Preset::Standard,Preset::EFlat,Preset::DropD}) {
            Setup setup; setup.openMidi = tuning(preset);
            for (int string=1;string<=6;++string) {
                const auto p = position(setup,string,5);
                expect(p.available() && *p.midi == setup.openMidi[static_cast<std::size_t>(string-1)]+5 && p.physicalFret == 5,"preset exact fifth-fret relation");
            }
        }
        Setup custom;custom.openMidi={{38,45,50,55,57,62}};
        expect(position(custom,5,2).midi==59 && position(custom,6,3).midi==65,"customDADGAD independent string pitches");
        standard.capo=2;
        expect(position(standard,1,0).midi==42 && position(standard,1,0).physicalFret==2,"capo2 open lowF-sharp2 at physical2");
        expect(position(standard,1,20).available() && position(standard,1,20).physicalFret==22,"last physical fret included");
        expect(!position(standard,1,21).withinFrets,"beyond physical fret unavailable");
        expect(!position(standard,1,std::numeric_limits<int>::max()).midi,"large relative fret no integer wrap");
        expect(rejects([&]{(void)position(standard,0,0);}) && rejects([&]{(void)position(standard,1,-1);}),"invalid string/negative relative fret rejected");
        custom.fretCount=0;custom.capo=0;expect(position(custom,1,0).available() && !position(custom,1,1).available(),"open-only configuration explicit");
        custom.fretCount=36;custom.capo=36;expect(position(custom,1,0).available(),"declared maximum fret/capo supported");
        custom.openMidi[0]=127;expect(!position(custom,1,0).midi,"high custom pluscapo not clamped");
        for (int midi=0;midi<=127;++midi) expect(parseNote(noteName(midi))==midi,"all128 displayed pitches parse exactly");
        expect(parseNote("Eb2")==39 && parseNote("b#3")==60 && parseNote("Cb4")==59 && parseNote("Fx3")==55,"enharmonic spellings preserve octave crossing");
        expect(parseNote("C-1")==0 && parseNote("G9")==127,"pitch representation endpoints");
        for (const auto* text : {"","E","E2.0"," E2","E2 ","E2x","E+2","H2","G#9","Cb-1","C-0","C10","E##","true","60","F♯2"})
            expect(rejects([&]{(void)parseNote(text);}),"malformed/unsupported note refused");
        expect(parseCount("0")==0 && parseCount("036")==36 && parseCount("999")==999,"strict decimal counts parsed before semantic range");
        for (const auto* text : {"-1","1.0","1x"," 2","2 ","","true","1000"}) expect(rejects([&]{(void)parseCount(text);}),"count coercion refused");
        for (int internal=1;internal<=6;++internal) expect(displayString(internal)==7-internal,"canonical versus guitar string label mapping");
        expect(rejects([]{(void)displayString(7);}),"seventh product string refused");
        for(int fret=0;fret<=12;++fret) expect(fretColumn(fret,13,Handedness::Right)==fret && fretColumn(fret,13,Handedness::Left)==12-fret,"horizontal handedness mirror preserves relative fret");
        expect(rejects([]{(void)fretColumn(13,13,Handedness::Right);}),"out-of-preview fret refused");
        auto controls=controlExamples();
        auto authored=music::validate(controls[7]);expect(authored.validReference(),"retained L49 E/Em reference valid");
        Setup current;
        auto same=compare(*authored.model,current);
        expect(same.accessAllowed && same.referenceUsesAuthoredSetup && same.positionsAssessed && same.requirementStatus==RequirementStatus::Specified && same.warnings.empty(),"matching authored setup has positive assessed positions");
        const auto source=authored.model->source().preservedRecordJson;
        current.openMidi=tuning(Preset::EFlat);auto mismatch=compare(*authored.model,current);
        expect(mismatch.accessAllowed && mismatch.referenceUsesAuthoredSetup && warning(mismatch,"tuning") && warning(mismatch,"pitch_mismatch"),"mismatch warns and retains authored reference/access");
        expect(authored.model->source().preservedRecordJson==source && authored.model->projections()[0].tones[0].soundingMidi==40,"declared tuning cannot mutate authored E pitch/source");
        current=Setup{};current.fretCount=1;expect(warning(compare(*authored.model,current),"unavailable_fret"),"source fret2 unavailable on fret1 neck but source retained");
        auto required=controls[0];required.syntheticFixture=true;required.proposalExample=false;required.instrument.capo=2;
        required.events.resize(1);required.events[0].tones[0].fret=20;required.events[0].tones[0].midi=62;required.events[0].tones[0].degrees.clear();
        auto withCapo=music::validate(required);expect(withCapo.validReference(),"synthetic requiredcapo2/fret20 reference valid");
        current=Setup{};current.fretCount=21;
        expect(position(current,1,20).withinFrets && warning(compare(*withCapo.model,current),"unavailable_fret") && warning(compare(*withCapo.model,current),"capo"),"required physical22 remains unavailable despite current physical20");
        for (std::size_t i : {8u,10u,11u,12u}) {
            auto task=music::validate(controls[i]);auto comparison=compare(*task.model,Setup{});
            expect(comparison.accessAllowed && comparison.requirementStatus==RequirementStatus::Unspecified && !comparison.positionsAssessed,"unbound/task requirements not invented or called compatible");
        }
        current=Setup{};current.openMidi[1]=127;
        expect(warning(compare(*authored.model,current),"pitch_range"),"comparison reports unrepresentable high custom position");
        ActiveSetup active;const auto snapshot=active.current();
        auto change=snapshot;change.openMidi=tuning(Preset::DropD);change.handedness=Handedness::Left;
        expect(!active.apply(change,{false,true}).empty() && active.revision()==0,"running context cannot apply preferences");
        expect(!active.apply(change,{true,false}).empty() && active.revision()==0,"unresolved outcome cannot apply preferences");
        expect(active.apply(change,{true,true}).empty() && active.revision()==1 && active.current().handedness==Handedness::Left,"explicit stopped/resolved apply advances once");
        expect(snapshot.openMidi[0]==40 && snapshot.handedness==Handedness::Right,"allocated snapshot retains original tuning/hand");
        const auto saved=active.current();
        for(int type=0;type<7;++type) {
            auto invalid=saved;
            if(type==0)invalid.valueVersion="future";
            if(type==1)invalid.fretCount=37;
            if(type==2)invalid.fretCount=-1;
            if(type==3)invalid.capo=-1;
            if(type==4)invalid.capo=23;
            if(type==5)invalid.openMidi[1]=128;
            if(type==6)invalid.handedness=static_cast<Handedness>(99);
            expect(!active.apply(invalid,{true,true}).empty() && active.revision()==1 && active.current().openMidi==saved.openMidi,"invalid/unknown config preserves active and revision");
        }
        std::cout << "PASS " << checks << " guitar setup checks; no audio/profile/physical tuning claim\n";
        return 0;
    } catch (const std::exception& e) { std::cerr << "FAIL after " << checks << " checks: " << e.what() << '\n';return 1; }
}
