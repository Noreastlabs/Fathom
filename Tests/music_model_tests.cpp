#include "core/MusicModel.hpp"
#include "fixtures/control_model_examples.hpp"
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <limits>

using namespace fathom;
using namespace fathom::music;
namespace {
int checks = 0;
void expect(bool condition, const std::string& label) {
    ++checks;
    if (!condition) throw std::runtime_error(label);
    std::cout << "PASS " << label << '\n';
}
bool has(const std::vector<Issue>& issues, const std::string& code) {
    return std::any_of(issues.begin(), issues.end(), [&](const Issue& i) { return i.code == code; });
}
void invalid(const Model& model, const std::string& code, const std::string& label) {
    auto v = validate(model);
    expect(!v.validReference() && has(v.issues,code), label);
}
Model synthetic() {
    Model model;
    model.itemId="synthetic:test"; model.schemaVersion="test-model1"; model.contentVersion="synthetic1";
    model.proposalExample=false; model.syntheticFixture=true;
    model.instrument={{40,45,50,55,59,64},0};
    return model;
}
Event note(const std::string& id, Rational onset, Rational duration, int string=1, int fret=5, int midi=45) {
    Event e; e.id=id; e.span={onset,duration}; Tone t; t.string=string; t.fret=fret; t.midi=midi; e.tones={t}; return e;
}
RendererCapabilities pluck() { return {{Attack::Picked,Attack::Held},false,false,false}; }
}
int main() {
    try {
        auto controls=controlExamples();
        expect(controls.size()==13,"thirteen exact accepted proposal controls");
        std::size_t count=0;
        for (const auto& model:controls) {
            auto v=validate(model);
            if (!v.validReference()) for (const auto& i:v.issues) std::cerr<<model.itemId<<' '<<i.event<<' '<<i.code<<'\n';
            expect(v.validReference(),"valid reference "+model.itemId);
            expect(v.model->source().proposalExample && !v.model->source().syntheticFixture,"source status retained "+model.itemId);
            expect(v.model->source().preservedRecordJson==model.preservedRecordJson,"entire source record preserved "+model.itemId);
            expect(!assessReadiness(*v.model,pluck()).curriculumPlaybackAuthorized,"no proposal becomes runtime curriculum "+model.itemId);
            count+=model.events.size();
            expect(v.model->projections().size()==model.events.size(),"one projection per original event "+model.itemId);
        }
        expect(count==69,"all69 mapped events retained");
        expect(controls[1].events[0].sourceRef=="L3-TXT28-46" && controls[2].events[0].sourceRef=="L12-TXT34-52" && controls[3].events[0].sourceRef=="L15-TXT59-81" && controls[6].events[0].sourceRef=="L48-TXT49-76" && controls[8].events[0].sourceRef=="L58-TXT43-48","event locators point to actual musical passages instead of legends");
        expect(controls[0].events.back().tones[0].midi==46 && controls[1].events.back().tones[0].midi==51 && controls[0].itemId!=controls[1].itemId,"L1/L3 local001 preserves distinct route identity and last string pitch");
        expect(!assessReadiness(*validate(controls[0]).model,pluck()).technicallyRenderable,"L1 untimed cannot acquire playback duration");

        const int expectedL12[]={45,47,49,50,52,54,56,57,57,56,54,52,50,49,47,45};
        auto l12=validate(controls[2]);
        for (std::size_t n=0;n<16;++n) {
            const auto& projection=l12.model->projections()[n];
            expect(projection.tones[0].soundingMidi==expectedL12[n] && projection.span.onset==std::optional<Rational>{Rational{static_cast<std::int64_t>(n),2}} && projection.span.duration==std::optional<Rational>{Rational{1,2}},"L12 source pitch and structural slot "+std::to_string(n+1));
        }
        expect(controls[2].events[7].tones[0].degrees[0].ordinal==8 && controls[2].events[7].tones[0].finger=="4","L12 octave degree8 is finger4");
        expect(controls[2].events[7].tones[0].attack==Attack::Picked && controls[2].events[8].tones[0].attack==Attack::Picked,"L12 repeated root is two picked events not a held tie");
        auto changed=controls[2]; changed.events[7].tones[0].finger="8"; invalid(changed,"finger","finger8 rejected");
        changed=controls[2]; changed.events[0].tones[0].midi=46; invalid(changed,"pitch_position","contradictory pitch/position rejected");
        changed=controls[2]; changed.events[0].tones[0].degrees[0].sourceLabel="9"; invalid(changed,"degree_label","wrong degree label rejected separately from pitch");
        changed=controls[2]; changed.events[0].tones[0].degrees[0].rootMidi=57; invalid(changed,"degree_register","explicit wrong root register rejected");
        auto immutable=validate(controls[2]); auto originalPitch=immutable.model->projections()[0].tones[0].soundingMidi;
        auto mutableInput=controls[2]; auto frozen=validate(mutableInput); mutableInput.events[0].tones[0].midi=90;
        expect(frozen.model->source().events[0].tones[0].midi==originalPitch && frozen.model->projections()[0].tones[0].soundingMidi==originalPitch,"immutable snapshot isolates later caller mutation across views");

        const auto& triplets=controls[3].events;
        expect(triplets[1].span.onset==std::optional<Rational>{Rational{1,3}} && triplets[2].span.onset==std::optional<Rational>{Rational{2,3}} && *triplets[2].span.onset+*triplets[2].span.duration==Rational{1},"L15 triplets preserve exact one-quarter total");
        auto degreeModel=synthetic(); degreeModel.events={note("upper",Rational{},Rational{1},1,19,59)};
        degreeModel.events[0].tones[0].degrees={{"A-major","9",9,9,0,45}};
        expect(validate(degreeModel).validReference(),"synthetic degree9 is upper2 fourteen semitones above explicit root");
        degreeModel.events[0].tones[0].midi=69; degreeModel.events[0].tones[0].fret=29; degreeModel.events[0].tones[0].degrees[0]={"A-major","15",9,15,0,45};
        expect(validate(degreeModel).validReference(),"synthetic degree15 retains two octaves");
        const auto& relative=controls[5].events[4].tones[0];
        expect(relative.midi==69 && relative.degrees[0].sourceLabel=="1" && relative.degrees[1].sourceLabel=="b3" && relative.finger=="2","L39 A-major1 and F-sharp-minor b3 share A69/finger2");
        changed=controls[5]; changed.events[4].tones[0].degrees[1].alteration=-2; changed.events[4].tones[0].degrees[1].sourceLabel="bb3"; invalid(changed,"degree_pitch","L39 double-flattening minor degree rejected");

        const auto& held=controls[6].events[14];
        expect(held.tones[0].attack==Attack::Held && held.tones[0].tieFrom==controls[6].events[13].id && controls[6].events[13].tones[0].attack==Attack::SlideArrival,"L48 original slide arrival and held continuation preserved");
        expect(has(assessReadiness(*validate(controls[6]).model,pluck()).issues,"unsupported_technique"),"L48 pluck renderer cannot silently substitute hammer/slide");
        for (const auto& id:{std::string("missing"),controls[6].events[15].id}) {
            changed=controls[6];changed.events[14].tones[0].tieFrom=id;invalid(changed,"tie_identity","dangling/forward held target "+id);
        }
        changed=controls[6];changed.events[14].tones[0].attack=Attack::Picked;invalid(changed,"tie_identity","re-picked held continuation rejected");
        changed=controls[6];changed.events[14].span.onset=Rational{29,4};invalid(changed,"tie_continuity","gap in held chain rejected");
        changed=controls[6];changed.events[14].tones[0].midi=58;changed.events[14].tones[0].fret=8;invalid(changed,"tie_identity","held different pitch/position rejected");
        changed=controls[6];changed.events[1].tones[0].fret=4;changed.events[1].tones[0].midi=44;invalid(changed,"legato_direction","hammer descending fret rejected");
        changed=controls[6];changed.events[1].span.onset=Rational{3,4};invalid(changed,"legato_gap","legato gap not silently articulated");

        const int expectedE[]={40,47,52,56,59,64}, expectedEm[]={40,47,52,55,59,64};
        auto chords=validate(controls[7]);
        for (std::size_t n=0;n<6;++n) expect(chords.model->projections()[0].tones[n].soundingMidi==expectedE[n] && chords.model->projections()[1].tones[n].soundingMidi==expectedEm[n],"L49 E/Em source voicing string "+std::to_string(n+1));
        expect(!assessReadiness(*chords.model,pluck()).technicallyRenderable,"L49 alternative voicings remain untimed reference");
        auto timed=controls[7];timed.syntheticFixture=true;timed.proposalExample=false;
        for(std::size_t n=0;n<timed.events.size();++n) {timed.events[n].span={Rational{static_cast<std::int64_t>(n)},Rational{1}};for(auto& tone:timed.events[n].tones)tone.memberSpan=timed.events[n].span;}
        expect(validate(timed).validReference() && assessReadiness(*validate(timed).model,pluck()).technicallyRenderable,"explicit synthetic simultaneous chord timing supported");
        changed=timed;changed.events[0].tones[1].memberSpan=Span{Rational{1,2},Rational{1}};invalid(changed,"chord_time","asynchronous chord member rejected");
        changed=timed;changed.events[0].tones[1]=changed.events[0].tones[0];invalid(changed,"duplicate_string","duplicate chord string rejected");
        changed=timed;changed.events[0].tones[1].finger="O";invalid(changed,"open_finger","fretted O finger rejected");

        auto mask=validate(controls[8]);
        auto air=std::count_if(mask.model->projections().begin(),mask.model->projections().end(),[](const EventProjection& e){return e.contact==Contact::Air;});
        expect(air==12 && mask.model->projections().size()==16,"L58 four contacts and twelve air strokes retained");
        expect(has(assessReadiness(*mask.model,pluck()).issues,"unresolved_binding"),"L58 no invented pitch binding");
        changed=controls[8];changed.events[1].tones={Tone{}};invalid(changed,"nonpitched_contact","air cannot acquire muted/pitched tone payload");
        for (std::size_t index:{4u,9u,10u,11u,12u}) expect(controls[index].events.empty() && !assessReadiness(*validate(controls[index]).model,pluck()).technicallyRenderable,"eventless task/reference retained "+controls[index].itemId);
        expect(controls[10].preservedRecordJson.find("A7")!=std::string::npos && controls[10].preservedRecordJson.find("C#")!=std::string::npos && controls[10].events.empty(),"L83 A7/topC-sharp table preserves no invented bass/octave/voicing");

        auto model=synthetic();model.instrument={{28,33,38,43},1};model.events={note("four-string",Rational{},Rational{1},1,2,31)};
        expect(validate(model).validReference(),"synthetic four-string vector and capo1 pitch31");
        changed=model;changed.events[0].tones[0].string=5;invalid(changed,"position","missing string rejected without fixed-six primitive");
        changed=model;changed.instrument.capo=-1;invalid(changed,"capo","negative capo rejected");
        changed=model;changed.events[0].tones[0].fret=-1;invalid(changed,"position","negative fret rejected");
        model=synthetic();model.instrument.openMidi[0]=38;model.events={note("drop",Rational{},Rational{1},1,5,43)};
        expect(validate(model).validReference(),"synthetic altered tuning computes explicit pitch43");
        changed=model;changed.events[0].tones[0].midi=45;invalid(changed,"pitch_position","setup change does not silently transpose authored pitch");
        model=synthetic();model.events={note("b-string",Rational{},Rational{1},5,1,60)};model.events[0].tones[0].spelling="B#";
        expect(validate(model).validReference() && pitchClass("B#")==pitchClass("C") && pitchClass("Db")==pitchClass("C#") && pitchClass("Fbb")==3,"B-string and enharmonic pitch-class relationships");
        changed=model;changed.events[0].tones[0].spelling="D";invalid(changed,"spelling_pitch","wrong authored spelling rejected");
        changed=model;changed.events[0].tones[0].spelling="C4";invalid(changed,"spelling","spelling token cannot silently supply an octave");
        expect(intervalSemitones(59,64)==5 && intervalSemitones(64,59)==-5,"directed intervals preserve tuning relation");
        expect(scalePitchClasses(9,{0,2,4,5,7,9,11})==std::vector<int>({9,11,1,2,4,6,8}),"explicit A-major scale intervals");
        expect(scalePitchClasses(6,{0,2,3,5,7,8,10})==std::vector<int>({6,8,9,11,1,2,4}),"explicit F-sharp natural minor shares A-major classes without double flattening");
        bool scaleRejected=false;try{(void)scalePitchClasses(0,{0,2,2,5});}catch(const std::invalid_argument&){scaleRejected=true;}expect(scaleRejected,"contradictory scale interval order rejected");

        model=synthetic();model.events={note("a",Rational{},Rational{1})};Event rest;rest.id="rest";rest.kind=Kind::Rest;rest.span={Rational{1},Rational{1}};rest.scopeStrings={1};model.events.push_back(rest);
        Measure measure;measure.id="two-four";measure.numerator=2;measure.denominator=4;measure.eventIds={"a","rest"};measure.requireCompleteCoverage=true;model.measures={measure};
        expect(validate(model).validReference(),"declared2/4 measure includes exact last rest");
        changed=model;changed.events[1].span.duration=Rational{1,2};invalid(changed,"measure_total","shortened final rest fails measure total");
        changed=model;changed.events[1].span.onset=Rational{3,2};invalid(changed,"measure_bounds","measure overrun rejected");
        changed=model;changed.events[1].tones={Tone{}};invalid(changed,"pitched_rest","rest cannot contain pitch");
        changed=model;changed.events[0].span.duration=Rational{};invalid(changed,"zero_duration","zero note duration rejected");
        changed=model;changed.events[0].span={std::nullopt,std::nullopt};auto unknown=validate(changed);expect(unknown.validReference()&&has(unknown.issues,"measure_time"),"unresolved measure time remains unknown not false contradiction");
        model=synthetic();model.events={note("s1",Rational{},Rational{2}),note("s1-overlap",Rational{1},Rational{1})};invalid(model,"string_overlap","same-string overlap rejected");
        model.events[1]=note("s2",Rational{1},Rational{1},2,0,45);expect(validate(model).validReference(),"different-string polyphonic overlap remains valid");
        rest.id="scoped";rest.span={Rational{1},Rational{1}};rest.scopeStrings={3};model.events.push_back(rest);expect(validate(model).validReference(),"rest on string3 does not erase sounding strings1/2");
        changed=model;changed.events.back().scopeStrings={1};invalid(changed,"rest_overlap","rest contradicting explicit sounding scope rejected");
        model.events.pop_back();Event gesture;gesture.id="air";gesture.kind=Kind::Contact;gesture.contact=Contact::Air;gesture.span={Rational{1},Rational{1}};model.events.push_back(gesture);expect(validate(model).validReference(),"air during sustain does not silence tone");
        for (const auto contact:{Contact::Muted,Contact::Release,Contact::Sustain}) {
            changed=model;changed.events.back().contact=contact;changed.events.back().scopeStrings={1};
            if(contact!=Contact::Sustain)changed.events.back().span.onset=Rational{2};
            auto v=validate(changed);expect(v.validReference()&&has(assessReadiness(*v.model,pluck()).issues,"unsupported_contact"),"contact capability refusal "+std::to_string(static_cast<int>(contact)));
        }
        changed=model;changed.events[1].id=changed.events[0].id;invalid(changed,"duplicate_identity","duplicate event identity rejected");
        changed=model;changed.events[1].span.onset=Rational{};changed.events[0].span.onset=Rational{1};invalid(changed,"event_order","out-of-order structural events rejected");
        changed=model;changed.events[0].kind=static_cast<Kind>(99);invalid(changed,"event_kind","unknown event kind rejected");
        changed=model;changed.events[0].tones[0].attack=static_cast<Attack>(99);invalid(changed,"attack_kind","unknown required technique rejected");
        model=synthetic();model.events={note("bend",Rational{},Rational{1})};model.events[0].tones[0].attack=Attack::Bend;auto bend=validate(model);expect(bend.validReference()&&has(assessReadiness(*bend.model,pluck()).issues,"bend_binding"),"bend token preserves unresolved amount and rejects playback");
        model.events[0].tones[0].attack=Attack::Harmonic;model.events[0].tones[0].midi=69;auto harmonic=validate(model);expect(harmonic.validReference()&&has(assessReadiness(*harmonic.model,pluck()).issues,"harmonic_binding"),"harmonic cannot pretend ordinary fretted-pitch proof");
        model=synthetic();model.events={note("huge",Rational{std::numeric_limits<std::int64_t>::max()},Rational{1})};invalid(model,"arithmetic_range","singleton structural end overflow rejected without another event");

        model=synthetic();auto pitched=note("bound-contact",Rational{},Rational{1,4});pitched.kind=Kind::Contact;pitched.contact=Contact::Pitched;pitched.tones[0].soundingSpan=Span{Rational{},Rational{2}};model.events={pitched};
        auto bound=validate(model);expect(bound.validReference() && assessReadiness(*bound.model,pluck()).technicallyRenderable,"explicit contact sounding gate may outlast hand slot");
        expect(bound.model->projections()[0].span.duration==std::optional<Rational>{Rational{1,4}} && bound.model->projections()[0].tones[0].soundingSpan.duration==std::optional<Rational>{Rational{2}},"projection separates quarter hand slot from two-quarter tone gate");
        changed=model;changed.events[0].tones[0].soundingSpan.reset();auto missingGate=validate(changed);expect(missingGate.validReference() && has(assessReadiness(*missingGate.model,pluck()).issues,"unresolved_gate"),"bound pitches alone cannot invent a contact sounding gate");
        changed=model;changed.events[0].tones[0].soundingSpan->onset=Rational{1,4};invalid(changed,"contact_gate_onset","contact gate must begin at contact onset");
        changed=model;changed.events[0].tones[0].soundingSpan->duration=Rational{};invalid(changed,"zero_gate","contact sounding gate must be positive");
        changed=model;changed.events.push_back(note("collision",Rational{1},Rational{1}));invalid(changed,"string_overlap","contact sounding gate catches overlap after hand slot ended");
        changed=model;rest.id="gate-rest";rest.span={Rational{1},Rational{1}};rest.scopeStrings={1};changed.events.push_back(rest);invalid(changed,"rest_overlap","rest checks contact sounding gate instead of hand slot");
        Event release;release.id="release";release.kind=Kind::Contact;release.contact=Contact::Release;release.scopeStrings={1};release.span={Rational{1},Rational{0}};
        changed=model;changed.events.push_back(release);invalid(changed,"release_gate","source release cannot silently truncate a longer declared gate");
        auto continuation=note("held",Rational{2},Rational{1});continuation.tones[0].attack=Attack::Held;continuation.tones[0].tieFrom="bound-contact";
        changed=model;changed.events.push_back(continuation);expect(validate(changed).validReference(),"held continuation uses contact sounding end rather than hand slot end");
        release.span.onset=Rational{2};changed=model;changed.events.push_back(release);changed.events.push_back(continuation);invalid(changed,"tie_cancelled","release at boundary breaks held continuation");
        changed=model;changed.events.push_back(continuation);changed.events.push_back(release);invalid(changed,"tie_cancelled","same-boundary cancellation does not depend on source vector ordering");
        changed=model;release.span.onset=Rational{1};changed.events.push_back(release);changed.events.push_back(continuation);invalid(changed,"tie_cancelled","mid-gate release cannot resume old held chain");
        auto unsupported=synthetic();Event sustain;sustain.id="sustain-alone";sustain.kind=Kind::Contact;sustain.contact=Contact::Sustain;sustain.scopeStrings={1};sustain.span={Rational{},Rational{1}};unsupported.events={sustain};auto noOrigin=validate(unsupported);RendererCapabilities sustainCap=pluck();sustainCap.sustainContact=true;
        expect(noOrigin.validReference() && has(assessReadiness(*noOrigin.model,sustainCap).issues,"sustain_binding") && !assessReadiness(*noOrigin.model,sustainCap).technicallyRenderable,"sustain cannot invent sounding origin even with renderer capability");
        changed=model;pitched.tones[0].soundingSpan=Span{Rational{},Rational{std::numeric_limits<std::int64_t>::max()}};pitched.span.onset=Rational{1};pitched.tones[0].soundingSpan->onset=Rational{1};changed.events={pitched};invalid(changed,"arithmetic_range","singleton contact gate overflow rejected eagerly");
        for (const auto operation : {Contact::Release,Contact::Muted}) {
            auto sameTime=synthetic(); release.contact=operation; release.span={Rational{},Rational{1,4}};
            sameTime.events={release,note("same-onset",Rational{},Rational{1})};
            invalid(sameTime,"release_gate","same-onset cancellation before attack rejected "+std::to_string(static_cast<int>(operation)));
            std::reverse(sameTime.events.begin(),sameTime.events.end());
            invalid(sameTime,"release_gate","same-onset cancellation after attack rejected "+std::to_string(static_cast<int>(operation)));
        }
        std::cout<<"PASS "<<checks<<" musical model checks; reference/synthetic only, no runtime admission\n";
        return 0;
    } catch(const std::exception& error) {std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<'\n';return 1;}
}
