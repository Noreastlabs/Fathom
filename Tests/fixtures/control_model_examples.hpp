// Generated test-only reference fixtures; all13 examples remain non-runtime.
#pragma once
#include "core/MusicModel.hpp"
inline std::vector<fathom::music::Model> controlExamples() {
using namespace fathom;
using namespace fathom::music;
std::vector<Model> result;
{ Model m;
m.itemId="fg:item:000001";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L1-TXT2-15"};
m.instrument.openMidi={40,45,50,55,59,64};
m.instrument.capo=0;
m.preservedRecordJson=R"FATHOM({"ambiguities":["Only first four of24 ascending notes shown; no duration authored in selected passage. Full route/reverse remains instruction, not inferred complete playback."],"authored_text_refs":["L1-TXT2-15"],"content_revision":1,"context":{"capo":0,"local_code":"001","pick_start":"explicit learner variant D or U; no chosen default","position":"fifth","route":"ascending-low-to-high","tuning_open_midi":[40,45,50,55,59,64]},"events":[{"attack":"picked","degree_contexts":{},"duration_q":null,"event_id":"fg:item:000001:event:0001","finger":1,"fret":5,"kind":"note","midi":45,"onset_q":null,"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"event_id":"fg:item:000001:event:0002","finger":2,"fret":6,"kind":"note","midi":46,"onset_q":null,"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"event_id":"fg:item:000001:event:0003","finger":1,"fret":5,"kind":"note","midi":45,"onset_q":null,"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"event_id":"fg:item:000001:event:0004","finger":2,"fret":6,"kind":"note","midi":46,"onset_q":null,"spelling":null,"string":1,"tie_from":null}],"id":"fg:item:000001","kind":"notation","legacy_level":1,"module_id":"fg:module:000001","normalization":[{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[],"rubric":null,"runtime_eligible":false,"source_refs":["L1-TXT2-15"],"status":"proposal_example","timing":{"basis":"No timing inferred from ASCII spacing","status":"unresolved","unit":"quarter"},"title":"Exercise0011212 ascending opening","workbook_id":"fg:workbook:000001"})FATHOM";
{ Event e;
e.id="fg:item:000001:event:0001";
e.sourceRef="L1-TXT2-15";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=1; t.fret=5; t.midi=45;
t.finger="1";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000001:event:0002";
e.sourceRef="L1-TXT2-15";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=1; t.fret=6; t.midi=46;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000001:event:0003";
e.sourceRef="L1-TXT2-15";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=1; t.fret=5; t.midi=45;
t.finger="1";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000001:event:0004";
e.sourceRef="L1-TXT2-15";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=1; t.fret=6; t.midi=46;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000002";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L3-TXT5-21","L3-TXT28-46"};
m.instrument.openMidi={40,45,50,55,59,64};
m.instrument.capo=0;
m.preservedRecordJson=R"FATHOM({"ambiguities":["Straight16th/triplet/quintuplet are separate authored practice variants; no universal duration/default selected. ModeB and descending require distinct variant identity, not deduplication by local code."],"authored_text_refs":["L3-TXT5-21","L3-TXT28-46"],"content_revision":1,"context":{"authored_progression_ref":"L3-TXT5-21","capo":0,"local_code":"001","mode":"A","pick_start_variants":["D","U"],"route":"ascending-E-to-A-first-pair","tuning_open_midi":[40,45,50,55,59,64]},"events":[{"attack":"picked","degree_contexts":{},"duration_q":null,"event_id":"fg:item:000002:event:0001","finger":1,"fret":5,"kind":"note","midi":45,"onset_q":null,"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"event_id":"fg:item:000002:event:0002","finger":2,"fret":6,"kind":"note","midi":46,"onset_q":null,"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"event_id":"fg:item:000002:event:0003","finger":1,"fret":5,"kind":"note","midi":45,"onset_q":null,"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"event_id":"fg:item:000002:event:0004","finger":2,"fret":6,"kind":"note","midi":51,"onset_q":null,"spelling":null,"string":2,"tie_from":null}],"id":"fg:item:000002","kind":"notation","legacy_level":3,"module_id":"fg:module:000002","normalization":[{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[],"rubric":null,"runtime_eligible":false,"source_refs":["L3-TXT5-21","L3-TXT28-46"],"status":"proposal_example","timing":{"basis":"No timing inferred from ASCII spacing","status":"unresolved","unit":"quarter"},"title":"ModeA Exercise001 first transfer","workbook_id":"fg:workbook:000003"})FATHOM";
{ Event e;
e.id="fg:item:000002:event:0001";
e.sourceRef="L3-TXT28-46";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=1; t.fret=5; t.midi=45;
t.finger="1";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000002:event:0002";
e.sourceRef="L3-TXT28-46";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=1; t.fret=6; t.midi=46;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000002:event:0003";
e.sourceRef="L3-TXT28-46";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=1; t.fret=5; t.midi=45;
t.finger="1";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000002:event:0004";
e.sourceRef="L3-TXT28-46";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=2; t.fret=6; t.midi=51;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000003";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L12-TXT14-28","L12-TXT34-52"};
m.instrument.openMidi={40,45,50,55,59,64};
m.instrument.capo=0;
m.preservedRecordJson=R"FATHOM({"ambiguities":["Only A cell;13-rung route not converted. One-beat pause uses quarter beat as explicitly labelled contract example; beat-unit confirmation remains conversion comparison, no universal product default."],"authored_text_refs":["L12-TXT14-28","L12-TXT34-52"],"content_revision":1,"context":{"capo":0,"pick_continues_at_turn":true,"pick_start_variants":["D","U"],"source_tempo_rules_ref":"L12-TXT34-52","tuning_open_midi":[40,45,50,55,59,64]},"events":[{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":1,"source_label":"1"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0001","finger":2,"fret":5,"kind":"note","midi":45,"onset_q":[0,1],"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":2,"source_label":"2"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0002","finger":4,"fret":7,"kind":"note","midi":47,"onset_q":[1,2],"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":3,"source_label":"3"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0003","finger":1,"fret":4,"kind":"note","midi":49,"onset_q":[1,1],"spelling":null,"string":2,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":4,"source_label":"4"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0004","finger":2,"fret":5,"kind":"note","midi":50,"onset_q":[3,2],"spelling":null,"string":2,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":5,"source_label":"5"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0005","finger":4,"fret":7,"kind":"note","midi":52,"onset_q":[2,1],"spelling":null,"string":2,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":6,"source_label":"6"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0006","finger":1,"fret":4,"kind":"note","midi":54,"onset_q":[5,2],"spelling":null,"string":3,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":7,"source_label":"7"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0007","finger":3,"fret":6,"kind":"note","midi":56,"onset_q":[3,1],"spelling":null,"string":3,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":8,"source_label":"8"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0008","finger":4,"fret":7,"kind":"note","midi":57,"onset_q":[7,2],"spelling":null,"string":3,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":8,"source_label":"8"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0009","finger":4,"fret":7,"kind":"note","midi":57,"onset_q":[4,1],"spelling":null,"string":3,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":7,"source_label":"7"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0010","finger":3,"fret":6,"kind":"note","midi":56,"onset_q":[9,2],"spelling":null,"string":3,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":6,"source_label":"6"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0011","finger":1,"fret":4,"kind":"note","midi":54,"onset_q":[5,1],"spelling":null,"string":3,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":5,"source_label":"5"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0012","finger":4,"fret":7,"kind":"note","midi":52,"onset_q":[11,2],"spelling":null,"string":2,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":4,"source_label":"4"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0013","finger":2,"fret":5,"kind":"note","midi":50,"onset_q":[6,1],"spelling":null,"string":2,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":3,"source_label":"3"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0014","finger":1,"fret":4,"kind":"note","midi":49,"onset_q":[13,2],"spelling":null,"string":2,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":2,"source_label":"2"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0015","finger":4,"fret":7,"kind":"note","midi":47,"onset_q":[7,1],"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":1,"source_label":"1"}},"duration_q":[1,2],"event_id":"fg:item:000003:event:0016","finger":2,"fret":5,"kind":"note","midi":45,"onset_q":[15,2],"spelling":null,"string":1,"tie_from":null}],"id":"fg:item:000003","kind":"notation","legacy_level":12,"module_id":"fg:module:000003","normalization":[{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[],"rubric":null,"runtime_eligible":false,"source_refs":["L12-TXT14-28","L12-TXT34-52"],"status":"proposal_example","timing":{"basis":"TXT35 even eighths","meter":null,"status":"source_defined","unit":"quarter","variants":[{"id":"with-pause","post_cell_rest_q":[1,1]},{"id":"connected","post_cell_rest_q":[0,1]}]},"title":"Rung01 A major16-note cell","workbook_id":"fg:workbook:000012"})FATHOM";
{ Event e;
e.id="fg:item:000003:event:0001";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{0,1},Rational{1,2}};
{ Tone t;
t.string=1; t.fret=5; t.midi=45;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","1",9,1,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0002";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{1,2},Rational{1,2}};
{ Tone t;
t.string=1; t.fret=7; t.midi=47;
t.finger="4";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","2",9,2,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0003";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{1,1},Rational{1,2}};
{ Tone t;
t.string=2; t.fret=4; t.midi=49;
t.finger="1";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","3",9,3,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0004";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{3,2},Rational{1,2}};
{ Tone t;
t.string=2; t.fret=5; t.midi=50;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","4",9,4,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0005";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{2,1},Rational{1,2}};
{ Tone t;
t.string=2; t.fret=7; t.midi=52;
t.finger="4";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","5",9,5,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0006";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{5,2},Rational{1,2}};
{ Tone t;
t.string=3; t.fret=4; t.midi=54;
t.finger="1";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","6",9,6,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0007";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{3,1},Rational{1,2}};
{ Tone t;
t.string=3; t.fret=6; t.midi=56;
t.finger="3";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","7",9,7,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0008";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{7,2},Rational{1,2}};
{ Tone t;
t.string=3; t.fret=7; t.midi=57;
t.finger="4";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","8",9,8,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0009";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{4,1},Rational{1,2}};
{ Tone t;
t.string=3; t.fret=7; t.midi=57;
t.finger="4";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","8",9,8,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0010";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{9,2},Rational{1,2}};
{ Tone t;
t.string=3; t.fret=6; t.midi=56;
t.finger="3";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","7",9,7,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0011";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{5,1},Rational{1,2}};
{ Tone t;
t.string=3; t.fret=4; t.midi=54;
t.finger="1";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","6",9,6,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0012";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{11,2},Rational{1,2}};
{ Tone t;
t.string=2; t.fret=7; t.midi=52;
t.finger="4";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","5",9,5,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0013";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{6,1},Rational{1,2}};
{ Tone t;
t.string=2; t.fret=5; t.midi=50;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","4",9,4,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0014";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{13,2},Rational{1,2}};
{ Tone t;
t.string=2; t.fret=4; t.midi=49;
t.finger="1";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","3",9,3,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0015";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{7,1},Rational{1,2}};
{ Tone t;
t.string=1; t.fret=7; t.midi=47;
t.finger="4";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","2",9,2,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000003:event:0016";
e.sourceRef="L12-TXT34-52";
e.kind=Kind::Note;
e.span=Span{Rational{15,2},Rational{1,2}};
{ Tone t;
t.string=1; t.fret=5; t.midi=45;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","1",9,1,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000004";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L15-TXT21-32","L15-TXT59-81","L15-TXT392-398"};
m.instrument.openMidi={40,45,50,55,59,64};
m.instrument.capo=0;
m.preservedRecordJson=R"FATHOM({"ambiguities":["Only first triplet of78-note cell; upper-octave explanation is metadata, not additional sounded events."],"authored_text_refs":["L15-TXT21-32","L15-TXT59-81","L15-TXT392-398"],"content_revision":1,"context":{"capo":0,"degree_encoding_examples":[{"octaves_above":1,"simple":1,"source":"8"},{"octaves_above":1,"simple":2,"source":"9"},{"octaves_above":2,"simple":1,"source":"15"}],"tuning_open_midi":[40,45,50,55,59,64]},"events":[{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":1,"source_label":"1"}},"duration_q":[1,3],"event_id":"fg:item:000004:event:0001","finger":2,"fret":5,"kind":"note","midi":45,"onset_q":[0,1],"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":2,"source_label":"2"}},"duration_q":[1,3],"event_id":"fg:item:000004:event:0002","finger":4,"fret":7,"kind":"note","midi":47,"onset_q":[1,3],"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":3,"source_label":"3"}},"duration_q":[1,3],"event_id":"fg:item:000004:event:0003","finger":1,"fret":4,"kind":"note","midi":49,"onset_q":[2,3],"spelling":null,"string":2,"tie_from":null}],"id":"fg:item:000004","kind":"notation","legacy_level":15,"module_id":"fg:module:000004","normalization":[{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[],"rubric":null,"runtime_eligible":false,"source_refs":["L15-TXT21-32","L15-TXT59-81","L15-TXT392-398"],"status":"proposal_example","timing":{"basis":"TXT60 eighth-note triplets","status":"source_defined","unit":"quarter","variants":[{"id":"triplets","marking_factor":[1,1],"notes_per_beat":3},{"id":"two-triplet-groups","marking_factor":[1,2],"notes_per_beat":6}]},"title":"First rolling triplet / upper-octave context","workbook_id":"fg:workbook:000015"})FATHOM";
{ Event e;
e.id="fg:item:000004:event:0001";
e.sourceRef="L15-TXT59-81";
e.kind=Kind::Note;
e.span=Span{Rational{0,1},Rational{1,3}};
{ Tone t;
t.string=1; t.fret=5; t.midi=45;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","1",9,1,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000004:event:0002";
e.sourceRef="L15-TXT59-81";
e.kind=Kind::Note;
e.span=Span{Rational{1,3},Rational{1,3}};
{ Tone t;
t.string=1; t.fret=7; t.midi=47;
t.finger="4";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","2",9,2,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000004:event:0003";
e.sourceRef="L15-TXT59-81";
e.kind=Kind::Note;
e.span=Span{Rational{2,3},Rational{1,3}};
{ Tone t;
t.string=2; t.fret=4; t.midi=49;
t.finger="1";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","3",9,3,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000005";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L29-TXT1512-1513","compiled-PDF2"};
m.preservedRecordJson=R"FATHOM({"ambiguities":[],"authored_text_refs":["L29-TXT1512-1513","compiled-PDF2"],"content_revision":1,"context":{},"events":[],"id":"fg:item:000005","kind":"instruction","legacy_level":29,"module_id":"fg:module:000005","normalization":[{"basis":"C2","kind":"accepted_navigation","source_authority":"compiled physicalp2; frozen selected-extracts.md line3803; original obsolete text retained","value":{"30":"major pentatonic","49":"chords/rhythm","65":"harmonic minor"}},{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[],"rubric":null,"runtime_eligible":false,"source_refs":["L29-TXT1512-1513","compiled-PDF2"],"status":"proposal_example","timing":{"basis":"Navigation instruction","status":"not_applicable","unit":"quarter"},"title":"Source-authored continuation correction","workbook_id":"fg:workbook:000029"})FATHOM";
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000006";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L39-TXT30-40","L39-TXT94-106"};
m.instrument.openMidi={40,45,50,55,59,64};
m.instrument.capo=0;
m.preservedRecordJson=R"FATHOM({"ambiguities":["No duration inferred from row spacing; contexts do not transpose pitches or change finger values."],"authored_text_refs":["L39-TXT30-40","L39-TXT94-106"],"content_revision":1,"context":{"capo":0,"local_code":"P1","reference_tonal_centers":["A-major","F#-minor"],"tuning_open_midi":[40,45,50,55,59,64]},"events":[{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":2,"source_label":"2"},"F#-minor":{"alteration":0,"ordinal":4,"source_label":"4"}},"duration_q":null,"event_id":"fg:item:000006:event:0001","finger":1,"fret":4,"kind":"note","midi":59,"onset_q":null,"spelling":null,"string":4,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":3,"source_label":"3"},"F#-minor":{"alteration":0,"ordinal":5,"source_label":"5"}},"duration_q":null,"event_id":"fg:item:000006:event:0002","finger":3,"fret":6,"kind":"note","midi":61,"onset_q":null,"spelling":null,"string":4,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":5,"source_label":"5"},"F#-minor":{"alteration":-1,"ordinal":7,"source_label":"b7"}},"duration_q":null,"event_id":"fg:item:000006:event:0003","finger":2,"fret":5,"kind":"note","midi":64,"onset_q":null,"spelling":null,"string":5,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":6,"source_label":"6"},"F#-minor":{"alteration":0,"ordinal":1,"source_label":"1"}},"duration_q":null,"event_id":"fg:item:000006:event:0004","finger":4,"fret":7,"kind":"note","midi":66,"onset_q":null,"spelling":null,"string":5,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":1,"source_label":"1"},"F#-minor":{"alteration":-1,"ordinal":3,"source_label":"b3"}},"duration_q":null,"event_id":"fg:item:000006:event:0005","finger":2,"fret":5,"kind":"note","midi":69,"onset_q":null,"spelling":null,"string":6,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":6,"source_label":"6"},"F#-minor":{"alteration":0,"ordinal":1,"source_label":"1"}},"duration_q":null,"event_id":"fg:item:000006:event:0006","finger":4,"fret":7,"kind":"note","midi":66,"onset_q":null,"spelling":null,"string":5,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":5,"source_label":"5"},"F#-minor":{"alteration":-1,"ordinal":7,"source_label":"b7"}},"duration_q":null,"event_id":"fg:item:000006:event:0007","finger":2,"fret":5,"kind":"note","midi":64,"onset_q":null,"spelling":null,"string":5,"tie_from":null},{"attack":"picked","degree_contexts":{"A-major":{"alteration":0,"ordinal":3,"source_label":"3"},"F#-minor":{"alteration":0,"ordinal":5,"source_label":"5"}},"duration_q":null,"event_id":"fg:item:000006:event:0008","finger":3,"fret":6,"kind":"note","midi":61,"onset_q":null,"spelling":null,"string":4,"tie_from":null}],"id":"fg:item:000006","kind":"notation","legacy_level":39,"module_id":"fg:module:000006","normalization":[{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[],"rubric":null,"runtime_eligible":false,"source_refs":["L39-TXT30-40","L39-TXT94-106"],"status":"proposal_example","timing":{"basis":"No timing inferred from ASCII spacing","status":"unresolved","unit":"quarter"},"title":"P1 drone comparison / dual degree contexts","workbook_id":"fg:workbook:000039"})FATHOM";
{ Event e;
e.id="fg:item:000006:event:0001";
e.sourceRef="L39-TXT30-40";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=4; t.fret=4; t.midi=59;
t.finger="1";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","2",9,2,0,std::nullopt});
t.degrees.push_back(Degree{"F#-minor","4",6,4,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000006:event:0002";
e.sourceRef="L39-TXT30-40";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=4; t.fret=6; t.midi=61;
t.finger="3";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","3",9,3,0,std::nullopt});
t.degrees.push_back(Degree{"F#-minor","5",6,5,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000006:event:0003";
e.sourceRef="L39-TXT30-40";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=5; t.fret=5; t.midi=64;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","5",9,5,0,std::nullopt});
t.degrees.push_back(Degree{"F#-minor","b7",6,7,-1,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000006:event:0004";
e.sourceRef="L39-TXT30-40";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=5; t.fret=7; t.midi=66;
t.finger="4";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","6",9,6,0,std::nullopt});
t.degrees.push_back(Degree{"F#-minor","1",6,1,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000006:event:0005";
e.sourceRef="L39-TXT30-40";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=6; t.fret=5; t.midi=69;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","1",9,1,0,std::nullopt});
t.degrees.push_back(Degree{"F#-minor","b3",6,3,-1,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000006:event:0006";
e.sourceRef="L39-TXT30-40";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=5; t.fret=7; t.midi=66;
t.finger="4";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","6",9,6,0,std::nullopt});
t.degrees.push_back(Degree{"F#-minor","1",6,1,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000006:event:0007";
e.sourceRef="L39-TXT30-40";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=5; t.fret=5; t.midi=64;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","5",9,5,0,std::nullopt});
t.degrees.push_back(Degree{"F#-minor","b7",6,7,-1,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000006:event:0008";
e.sourceRef="L39-TXT30-40";
e.kind=Kind::Note;
e.span=Span{std::nullopt,std::nullopt};
{ Tone t;
t.string=4; t.fret=6; t.midi=61;
t.finger="3";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.degrees.push_back(Degree{"A-major","3",9,3,0,std::nullopt});
t.degrees.push_back(Degree{"F#-minor","5",6,5,0,std::nullopt});
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000007";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L48-TXT28-43","L48-TXT49-76","L48-TXT1214-1246"};
m.instrument.openMidi={40,45,50,55,59,64};
m.instrument.capo=0;
m.preservedRecordJson=R"FATHOM({"ambiguities":["Only P1call/response excerpt of authored614tones shown; held response has a backward tie_from link. Bends remain contract mappings, not a complete articulation engine."],"authored_text_refs":["L48-TXT28-43","L48-TXT49-76","L48-TXT1214-1246"],"content_revision":1,"context":{"bend_contract":{"base_pitch":"string/fret pitch","contour":"not fabricated from b< shade symbol","target_interval":"must be source-specified or unresolved"},"capo":0,"color_context":"separate from pitch, degree and finger","held_response_example":{"duration_q":[1,1],"rule":"One A tone sustained over two eighth slots; no second attack","source_ref":"L48-TXT49-76","source_slots":["A","="]},"source_count_classes":{"full_written_pick_attacks":517,"full_written_sounding_tones":614},"technique_legend":{"=":"held_tone","P":"picked","b":"bend","b<":"blue_third_shade","h":"hammer_on","p":"pull_off","r":"rest","s":"slide_arrival"},"tuning_open_midi":[40,45,50,55,59,64]},"events":[{"attack":"picked","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0001","finger":null,"fret":5,"kind":"note","midi":45,"onset_q":[0,1],"spelling":null,"string":1,"tie_from":null},{"attack":"hammer_on","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0002","finger":null,"fret":8,"kind":"note","midi":48,"onset_q":[1,2],"spelling":null,"string":1,"tie_from":null},{"duration_q":[1,2],"event_id":"fg:item:000007:event:0003","kind":"rest","onset_q":[1,1]},{"attack":"picked","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0004","finger":null,"fret":5,"kind":"note","midi":50,"onset_q":[3,2],"spelling":null,"string":2,"tie_from":null},{"attack":"slide_arrival","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0005","finger":null,"fret":6,"kind":"note","midi":51,"onset_q":[2,1],"spelling":null,"string":2,"tie_from":null},{"attack":"slide_arrival","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0006","finger":null,"fret":7,"kind":"note","midi":52,"onset_q":[5,2],"spelling":null,"string":2,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0007","finger":null,"fret":8,"kind":"note","midi":67,"onset_q":[3,1],"spelling":null,"string":5,"tie_from":null},{"duration_q":[1,2],"event_id":"fg:item:000007:event:0008","kind":"rest","onset_q":[7,2]},{"attack":"picked","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0009","finger":null,"fret":5,"kind":"note","midi":60,"onset_q":[4,1],"spelling":null,"string":4,"tie_from":null},{"attack":"slide_arrival","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0010","finger":null,"fret":6,"kind":"note","midi":61,"onset_q":[9,2],"spelling":null,"string":4,"tie_from":null},{"duration_q":[1,2],"event_id":"fg:item:000007:event:0011","kind":"rest","onset_q":[5,1]},{"attack":"picked","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0012","finger":null,"fret":5,"kind":"note","midi":64,"onset_q":[11,2],"spelling":null,"string":5,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0013","finger":null,"fret":5,"kind":"note","midi":55,"onset_q":[6,1],"spelling":null,"string":3,"tie_from":null},{"attack":"slide_arrival","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0014","finger":null,"fret":7,"kind":"note","midi":57,"onset_q":[13,2],"spelling":null,"string":3,"tie_from":null},{"attack":"held","degree_contexts":{},"duration_q":[1,2],"event_id":"fg:item:000007:event:0015","finger":null,"fret":7,"kind":"note","midi":57,"onset_q":[7,1],"spelling":null,"string":3,"tie_from":"fg:item:000007:event:0014"},{"duration_q":[1,2],"event_id":"fg:item:000007:event:0016","kind":"rest","onset_q":[15,2]}],"id":"fg:item:000007","kind":"mixed","legacy_level":48,"module_id":"fg:module:000007","normalization":[{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[{"disposition":"instructions in2.4plan; source obligation remains","in_app_import":false,"in_app_recorder":false,"kind":"learner_teacher_offline","purpose":"source-requested recording/review","supplied":false}],"rubric":{"dimensions":[{"anchors":["absent","inconsistent","controlled"],"name":"Form awareness"},{"anchors":["absent","inconsistent","controlled"],"name":"Rhythmic space"},{"anchors":["absent","inconsistent","controlled"],"name":"Chord targeting"},{"anchors":["absent","inconsistent","controlled"],"name":"Bend and slide intonation"},{"anchors":["absent","inconsistent","controlled"],"name":"Motif continuity"},{"anchors":["absent","inconsistent","controlled"],"name":"Position movement"},{"anchors":["absent","inconsistent","controlled"],"name":"Dynamic shape"},{"anchors":["absent","inconsistent","controlled"],"name":"Recovery after an error"}],"evidence_kind":"explicit_learner_or_reviewer_attestation","maximum_total":16,"minimum_total":13,"protected_nonzero":["Form awareness","Chord targeting","Recovery after an error"],"repeatability":{"kind":"two_separate_days"},"required_obligations":["all five local pairs and four seam conversations","transform one motif in seven ways","sparse/medium/dense target preservation","all three model choruses","tonic ending and functional turnaround","deliberate wrong-note recovery without stopping","record three connected choruses on two separate days","audible A7-D7-E7 form without accompaniment"],"required_obligations_refs":["L48-TXT1214-1246"]},"runtime_eligible":false,"source_refs":["L48-TXT28-43","L48-TXT49-76","L48-TXT1214-1246"],"status":"proposal_example","timing":{"basis":"Cnt1&2&3&4& source grid","meter":[4,4],"status":"source_defined","unit":"quarter"},"title":"P1 call/response excerpt and full assessment","workbook_id":"fg:workbook:000048"})FATHOM";
{ Event e;
e.id="fg:item:000007:event:0001";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{0,1},Rational{1,2}};
{ Tone t;
t.string=1; t.fret=5; t.midi=45;
t.finger="";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0002";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{1,2},Rational{1,2}};
{ Tone t;
t.string=1; t.fret=8; t.midi=48;
t.finger="";
t.spelling="";
t.attack=Attack::HammerOn;
t.authoredTechnique="hammer_on";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0003";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Rest;
e.span=Span{Rational{1,1},Rational{1,2}};
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0004";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{3,2},Rational{1,2}};
{ Tone t;
t.string=2; t.fret=5; t.midi=50;
t.finger="";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0005";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{2,1},Rational{1,2}};
{ Tone t;
t.string=2; t.fret=6; t.midi=51;
t.finger="";
t.spelling="";
t.attack=Attack::SlideArrival;
t.authoredTechnique="slide_arrival";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0006";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{5,2},Rational{1,2}};
{ Tone t;
t.string=2; t.fret=7; t.midi=52;
t.finger="";
t.spelling="";
t.attack=Attack::SlideArrival;
t.authoredTechnique="slide_arrival";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0007";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{3,1},Rational{1,2}};
{ Tone t;
t.string=5; t.fret=8; t.midi=67;
t.finger="";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0008";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Rest;
e.span=Span{Rational{7,2},Rational{1,2}};
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0009";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{4,1},Rational{1,2}};
{ Tone t;
t.string=4; t.fret=5; t.midi=60;
t.finger="";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0010";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{9,2},Rational{1,2}};
{ Tone t;
t.string=4; t.fret=6; t.midi=61;
t.finger="";
t.spelling="";
t.attack=Attack::SlideArrival;
t.authoredTechnique="slide_arrival";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0011";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Rest;
e.span=Span{Rational{5,1},Rational{1,2}};
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0012";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{11,2},Rational{1,2}};
{ Tone t;
t.string=5; t.fret=5; t.midi=64;
t.finger="";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0013";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{6,1},Rational{1,2}};
{ Tone t;
t.string=3; t.fret=5; t.midi=55;
t.finger="";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0014";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{13,2},Rational{1,2}};
{ Tone t;
t.string=3; t.fret=7; t.midi=57;
t.finger="";
t.spelling="";
t.attack=Attack::SlideArrival;
t.authoredTechnique="slide_arrival";
t.tieFrom="";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0015";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Note;
e.span=Span{Rational{7,1},Rational{1,2}};
{ Tone t;
t.string=3; t.fret=7; t.midi=57;
t.finger="";
t.spelling="";
t.attack=Attack::Held;
t.authoredTechnique="held";
t.tieFrom="fg:item:000007:event:0014";
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000007:event:0016";
e.sourceRef="L48-TXT49-76";
e.kind=Kind::Rest;
e.span=Span{Rational{15,2},Rational{1,2}};
m.events.push_back(std::move(e)); }
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000008";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L49-TXT49-61"};
m.instrument.openMidi={40,45,50,55,59,64};
m.instrument.capo=0;
m.preservedRecordJson=R"FATHOM({"ambiguities":["No authored chord duration/onset in these voicing definitions; do not serialize as two timed strums. One chord attack can contain six tones."],"authored_text_refs":["L49-TXT49-61"],"content_revision":1,"context":{"capo":0,"chord_voicings_are_alternatives":true,"muted_string_token":"x means no pitched member","open_finger_token":"O","tuning_open_midi":[40,45,50,55,59,64]},"events":[{"attack":"simultaneous_example","duration_q":null,"event_id":"fg:item:000008:event:0001","kind":"chord","members":[{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":"O","fret":0,"kind":"note","midi":40,"onset_q":null,"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":2,"fret":2,"kind":"note","midi":47,"onset_q":null,"spelling":null,"string":2,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":3,"fret":2,"kind":"note","midi":52,"onset_q":null,"spelling":null,"string":3,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":1,"fret":1,"kind":"note","midi":56,"onset_q":null,"spelling":null,"string":4,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":"O","fret":0,"kind":"note","midi":59,"onset_q":null,"spelling":null,"string":5,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":"O","fret":0,"kind":"note","midi":64,"onset_q":null,"spelling":null,"string":6,"tie_from":null}],"onset_q":null,"symbol":"E"},{"attack":"simultaneous_example","duration_q":null,"event_id":"fg:item:000008:event:0002","kind":"chord","members":[{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":"O","fret":0,"kind":"note","midi":40,"onset_q":null,"spelling":null,"string":1,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":2,"fret":2,"kind":"note","midi":47,"onset_q":null,"spelling":null,"string":2,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":3,"fret":2,"kind":"note","midi":52,"onset_q":null,"spelling":null,"string":3,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":"O","fret":0,"kind":"note","midi":55,"onset_q":null,"spelling":null,"string":4,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":"O","fret":0,"kind":"note","midi":59,"onset_q":null,"spelling":null,"string":5,"tie_from":null},{"attack":"picked","degree_contexts":{},"duration_q":null,"finger":"O","fret":0,"kind":"note","midi":64,"onset_q":null,"spelling":null,"string":6,"tie_from":null}],"onset_q":null,"symbol":"Em"}],"id":"fg:item:000008","kind":"harmony","legacy_level":49,"module_id":"fg:module:000008","normalization":[{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[],"rubric":null,"runtime_eligible":false,"source_refs":["L49-TXT49-61"],"status":"proposal_example","timing":{"basis":"No timing inferred from ASCII spacing","status":"unresolved","unit":"quarter"},"title":"E and Em simultaneous six-string voicings","workbook_id":"fg:workbook:000049"})FATHOM";
{ Event e;
e.id="fg:item:000008:event:0001";
e.sourceRef="L49-TXT49-61";
e.kind=Kind::Chord;
e.span=Span{std::nullopt,std::nullopt};
e.chordSymbol="E";
{ Tone t;
t.string=1; t.fret=0; t.midi=40;
t.finger="O";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
{ Tone t;
t.string=2; t.fret=2; t.midi=47;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
{ Tone t;
t.string=3; t.fret=2; t.midi=52;
t.finger="3";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
{ Tone t;
t.string=4; t.fret=1; t.midi=56;
t.finger="1";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
{ Tone t;
t.string=5; t.fret=0; t.midi=59;
t.finger="O";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
{ Tone t;
t.string=6; t.fret=0; t.midi=64;
t.finger="O";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000008:event:0002";
e.sourceRef="L49-TXT49-61";
e.kind=Kind::Chord;
e.span=Span{std::nullopt,std::nullopt};
e.chordSymbol="Em";
{ Tone t;
t.string=1; t.fret=0; t.midi=40;
t.finger="O";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
{ Tone t;
t.string=2; t.fret=2; t.midi=47;
t.finger="2";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
{ Tone t;
t.string=3; t.fret=2; t.midi=52;
t.finger="3";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
{ Tone t;
t.string=4; t.fret=0; t.midi=55;
t.finger="O";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
{ Tone t;
t.string=5; t.fret=0; t.midi=59;
t.finger="O";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
{ Tone t;
t.string=6; t.fret=0; t.midi=64;
t.finger="O";
t.spelling="";
t.attack=Attack::Picked;
t.authoredTechnique="picked";
t.tieFrom="";
t.memberSpan=Span{std::nullopt,std::nullopt};
e.tones.push_back(std::move(t)); }
m.events.push_back(std::move(e)); }
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000009";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L58-TXT7-17","L58-TXT43-48"};
m.preservedRecordJson=R"FATHOM({"ambiguities":["Pitch/chord binding unspecified in mask; cannot play pitched content from this record alone. Do not equate contacts with sounding tones."],"authored_text_refs":["L58-TXT7-17","L58-TXT43-48"],"content_revision":1,"context":{"authored_contacts":4,"symbol_semantics":{"-":"air, no contact",">":"accent next contact","P":"pitched contact requiring chord binding","R":"pressure release, not an attack","x":"muted contact, no pitch","~":"sustain, no new attack"}},"events":[{"contact":"pitched","duration_q":[1,4],"event_id":"fg:item:000009:event:0001","kind":"contact","onset_q":[0,1],"pick":"D","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0002","kind":"contact","onset_q":[1,4],"pick":"U","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0003","kind":"contact","onset_q":[1,2],"pick":"D","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0004","kind":"contact","onset_q":[3,4],"pick":"U","pitch_binding":null},{"contact":"pitched","duration_q":[1,4],"event_id":"fg:item:000009:event:0005","kind":"contact","onset_q":[1,1],"pick":"D","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0006","kind":"contact","onset_q":[5,4],"pick":"U","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0007","kind":"contact","onset_q":[3,2],"pick":"D","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0008","kind":"contact","onset_q":[7,4],"pick":"U","pitch_binding":null},{"contact":"pitched","duration_q":[1,4],"event_id":"fg:item:000009:event:0009","kind":"contact","onset_q":[2,1],"pick":"D","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0010","kind":"contact","onset_q":[9,4],"pick":"U","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0011","kind":"contact","onset_q":[5,2],"pick":"D","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0012","kind":"contact","onset_q":[11,4],"pick":"U","pitch_binding":null},{"contact":"pitched","duration_q":[1,4],"event_id":"fg:item:000009:event:0013","kind":"contact","onset_q":[3,1],"pick":"D","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0014","kind":"contact","onset_q":[13,4],"pick":"U","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0015","kind":"contact","onset_q":[7,2],"pick":"D","pitch_binding":null},{"contact":"air","duration_q":[1,4],"event_id":"fg:item:000009:event:0016","kind":"contact","onset_q":[15,4],"pick":"U","pitch_binding":null}],"id":"fg:item:000009","kind":"rhythm","legacy_level":58,"module_id":"fg:module:000009","normalization":[{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[],"rubric":null,"runtime_eligible":false,"source_refs":["L58-TXT7-17","L58-TXT43-48"],"status":"proposal_example","timing":{"basis":"sixteenth hand-grid1e&a through4e&a","meter":[4,4],"status":"source_defined","unit":"quarter"},"title":"A1 beat-only contact mask","workbook_id":"fg:workbook:000058"})FATHOM";
{ Event e;
e.id="fg:item:000009:event:0001";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{0,1},Rational{1,4}};
e.contact=Contact::Pitched;
e.handDirection="D";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0002";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{1,4},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="U";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0003";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{1,2},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="D";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0004";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{3,4},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="U";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0005";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{1,1},Rational{1,4}};
e.contact=Contact::Pitched;
e.handDirection="D";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0006";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{5,4},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="U";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0007";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{3,2},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="D";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0008";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{7,4},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="U";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0009";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{2,1},Rational{1,4}};
e.contact=Contact::Pitched;
e.handDirection="D";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0010";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{9,4},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="U";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0011";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{5,2},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="D";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0012";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{11,4},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="U";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0013";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{3,1},Rational{1,4}};
e.contact=Contact::Pitched;
e.handDirection="D";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0014";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{13,4},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="U";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0015";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{7,2},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="D";
m.events.push_back(std::move(e)); }
{ Event e;
e.id="fg:item:000009:event:0016";
e.sourceRef="L58-TXT43-48";
e.kind=Kind::Contact;
e.span=Span{Rational{15,4},Rational{1,4}};
e.contact=Contact::Air;
e.handDirection="U";
m.events.push_back(std::move(e)); }
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000010";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L74-TXT5-11","L74-TXT181-249"};
m.preservedRecordJson=R"FATHOM({"ambiguities":["Mathematical phrase descriptors, not converted allModuleD events. 4:3 resolution on beat4 is distinct from a repeated three-beat standalone cycle."],"authored_text_refs":["L74-TXT5-11","L74-TXT181-249"],"content_revision":1,"context":{"freeplay_default_selected":false},"events":[],"id":"fg:item:000010","kind":"rhythm","legacy_level":74,"module_id":"fg:module:000010","normalization":[{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[],"rubric":null,"runtime_eligible":false,"source_refs":["L74-TXT5-11","L74-TXT181-249"],"status":"proposal_example","timing":{"basis":"explicit sourceModuleD phrases","other_source_requirements":["5/4","7/8","quintuplets","septuplets"],"phrases":[{"common_cycle_q":[2,1],"cycles":2,"phrase_q":[4,1],"ratio":[3,2],"resolution_q":null},{"common_cycle_q":[3,1],"cycles":1,"phrase_q":[4,1],"ratio":[4,3],"resolution_q":[3,1]}],"status":"source_defined","unit":"quarter"},"title":"Source3:2 and4:3 phrases","workbook_id":"fg:workbook:000074"})FATHOM";
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000011";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L83-TXT52-56","L83-PDF19","L83-PDF20"};
m.preservedRecordJson=R"FATHOM({"ambiguities":["Chord symbol/top pitch class is not a voiced timed event. No octave, bass inversion, duration or voicing fabricated."],"authored_text_refs":["L83-TXT52-56","L83-PDF19","L83-PDF20"],"content_revision":1,"context":{"fixed_melody":true,"table":[{"bar":1,"bass_inversion":null,"chord_symbol":"Cmaj7","top_pitch_class":"E"},{"bar":2,"bass_inversion":null,"chord_symbol":"Am7","top_pitch_class":"E"},{"bar":3,"bass_inversion":null,"chord_symbol":"Dm7","top_pitch_class":"F"},{"bar":4,"bass_inversion":null,"chord_symbol":"G7","top_pitch_class":"B"},{"bar":5,"bass_inversion":null,"chord_symbol":"Cmaj7","top_pitch_class":"G"},{"bar":6,"bass_inversion":null,"chord_symbol":"A7","top_pitch_class":"C#"},{"bar":7,"bass_inversion":null,"chord_symbol":"Dm7","top_pitch_class":"F"},{"bar":8,"bass_inversion":null,"chord_symbol":"G7","top_pitch_class":"B"},{"bar":9,"bass_inversion":null,"chord_symbol":"Em7","top_pitch_class":"G"},{"bar":10,"bass_inversion":null,"chord_symbol":"A7","top_pitch_class":"C#"},{"bar":11,"bass_inversion":null,"chord_symbol":"Dm7","top_pitch_class":"F"},{"bar":12,"bass_inversion":null,"chord_symbol":"G7","top_pitch_class":"B"},{"bar":13,"bass_inversion":null,"chord_symbol":"Cmaj7","top_pitch_class":"E"},{"bar":14,"bass_inversion":null,"chord_symbol":"C#dim7","top_pitch_class":"E"},{"bar":15,"bass_inversion":null,"chord_symbol":"Dm7","top_pitch_class":"F"},{"bar":16,"bass_inversion":null,"chord_symbol":"G7","top_pitch_class":"B"},{"bar":17,"bass_inversion":null,"chord_symbol":"Am7","top_pitch_class":"C"},{"bar":18,"bass_inversion":null,"chord_symbol":"D7","top_pitch_class":"F#"},{"bar":19,"bass_inversion":null,"chord_symbol":"Gmaj7","top_pitch_class":"B"},{"bar":20,"bass_inversion":null,"chord_symbol":"B7","top_pitch_class":"D#"},{"bar":21,"bass_inversion":null,"chord_symbol":"Em7","top_pitch_class":"G"},{"bar":22,"bass_inversion":null,"chord_symbol":"A7","top_pitch_class":"C#"},{"bar":23,"bass_inversion":null,"chord_symbol":"Dm7","top_pitch_class":"F"},{"bar":24,"bass_inversion":null,"chord_symbol":"G7","top_pitch_class":"G"}],"task_obligations":["bars1–8 baseline wording preserved","bars9–16secondary dominants and one passing diminished chord","bars17–24reharmonize at least four measures without changing written melody"]},"events":[],"id":"fg:item:000011","kind":"task","legacy_level":83,"module_id":"fg:module:000011","normalization":[{"basis":"C3","kind":"accepted_explanation","text":"Baseline includes an already-authored applied-dominant exception: bar6 Chord A7 and Top C#, followed by Dm7. Approved normalization interpretation, not verified authorial intent. C# is melody/top, not bass inversion."},{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[],"rubric":{"dimensions":[{"anchors":["lost","functional","dominant/clear"],"name":"Melody clarity"},{"anchors":["unclear","functional","directed"],"name":"Bass logic"},{"anchors":["wrong","mostly clear","clear"],"name":"Chord quality"},{"anchors":["lost","functional","smooth"],"name":"Guide-tone motion"},{"anchors":["random","plausible","purposeful"],"name":"Substitution function"},{"anchors":["noisy","usable","clean"],"name":"Voicing cleanliness"},{"anchors":["lost","recovers","stable"],"name":"Form/pulse"},{"anchors":["restart","simplifies","seamless"],"name":"Recovery"}],"evidence_kind":"explicit_learner_or_reviewer_attestation","maximum_total":16,"minimum_total":14,"protected_nonzero":["Melody clarity","Bass logic","Form/pulse","Recovery"],"repeatability":{"kind":"two_separate_days"},"required_obligations":["retain fixed24bar melody","reharmonize at least four measures in17–24","source recovery hierarchy"],"required_obligations_refs":["L83-PDF19","L83-PDF20"]},"runtime_eligible":false,"source_refs":["L83-TXT52-56","L83-PDF19","L83-PDF20"],"status":"proposal_example","timing":{"basis":"Task table without authored note octaves/durations/voicings","status":"not_applicable","unit":"quarter"},"title":"ModulesI–J fixed melody/table and rubric","workbook_id":"fg:workbook:000083"})FATHOM";
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000012";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L97-TXT35-40","L97-PDF19"};
m.preservedRecordJson=R"FATHOM({"ambiguities":[],"authored_text_refs":["L97-TXT35-40","L97-PDF19"],"content_revision":1,"context":{},"events":[],"id":"fg:item:000012","kind":"task","legacy_level":97,"module_id":"fg:module:000012","normalization":[{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[{"disposition":"C4accepted source resource boundary;2.4.1.1.1 defines selection/availability/instructions; no license supplied","in_app_import":false,"in_app_recorder":false,"kind":"learner_teacher_offline","purpose":"unfamiliar48bar recording without chart","supplied":false}],"rubric":{"dimensions":[{"anchors":["wrong","mostly","secure"],"name":"Form"},{"anchors":["wrong","plausible","confirmed"],"name":"Bass/function"},{"anchors":["wrong","functional","clear"],"name":"Harmony"},{"anchors":["lost","approximate","source-like"],"name":"Groove"},{"anchors":["missing","partial","clear"],"name":"Signature material"},{"anchors":["poor","mixed","disciplined"],"name":"Structural judgment"},{"anchors":["stops","functional","convincing"],"name":"Performance"},{"anchors":["restart","simplifies","seamless"],"name":"Recovery"}],"evidence_kind":"explicit_learner_or_reviewer_attestation","maximum_total":16,"minimum_total":14,"protected_nonzero":["Form","Bass/function","Groove","Recovery"],"repeatability":{"kind":"two_unfamiliar_excerpts","same_excerpt_twice_counts":false},"required_obligations":["unfamiliar48bar recording","no chord chart","one-page map","functional arrangement","reduced fallback","uninterrupted performance"],"required_obligations_refs":["L97-TXT35-40"]},"runtime_eligible":false,"source_refs":["L97-TXT35-40","L97-PDF19"],"status":"proposal_example","timing":{"basis":"Task/attestation, not fabricated score","status":"not_applicable","unit":"quarter"},"title":"Unfamiliar recording capstone / full rubric","workbook_id":"fg:workbook:000097"})FATHOM";
result.push_back(std::move(m)); }
{ Model m;
m.itemId="fg:item:000013";
m.schemaVersion="0.1.0-proposal";
m.contentVersion="control-examples.1";
m.contentRevision=1;
m.proposalExample=true; m.syntheticFixture=false;
m.sourceRefs={"L105-TXT26-61","L105-PDF29","L105-PDF30","L105-PDF31"};
m.preservedRecordJson=R"FATHOM({"ambiguities":[],"authored_text_refs":["L105-TXT26-61","L105-PDF29","L105-PDF30","L105-PDF31"],"content_revision":1,"context":{"failed_domain_return_refs":"L105-PDF31","maximum_legacy_level":105,"no_automatic_mastery":true},"events":[],"id":"fg:item:000013","kind":"task","legacy_level":105,"module_id":"fg:module:000013","normalization":[{"basis":"delegated Technical proposal","kind":"representation_metadata","text":"Record is a bounded example; human converted-curriculum acceptance and runtime validation occur in later packages."}],"resource_requirements":[],"rubric":{"dimensions":[{"anchors":["breaks/unknown","basic","controlled","immediate + musical"],"name":"Technique/fretboard"},{"anchors":["wrong","basic","functional","voice-led + adaptive"],"name":"Harmony/voicing"},{"anchors":["unstable","keeps time","stylistic","deep pocket + switching"],"name":"Rhythm/groove"},{"anchors":["cannot reconstruct","partial","functional","fast + selective"],"name":"Ear/transcription"},{"anchors":["random","phrases","develops motif","coherent arc"],"name":"Improvisation"},{"anchors":["fragile","memorized","adaptable","resilient + transferable"],"name":"Repertoire"},{"anchors":["cluttered","basic","role-aware","orchestrated"],"name":"Arrangement"},{"anchors":["fragment","complete","coherent","distinct + revisable"],"name":"Composition"},{"anchors":["stops","recovers late","simplifies","seamless"],"name":"Recovery"},{"anchors":["fragmented","complete","convincing","commanding + musical"],"name":"Performance"}],"evidence_kind":"explicit_learner_or_reviewer_attestation","maximum_total":30,"minimum_total":24,"protected_nonzero":["Rhythm/groove","Ear/transcription","Recovery","Performance"],"repeatability":{"alternative_affects":"repeatability_only","alternatives":[{"kind":"two_separate_days"},{"kind":"one_passing_performance_independent_reviewer","minimum_reviewer_total":24}],"kind":"any_of"},"required_obligations":["complete final session without abandoning exam","one finished original presented","one complete adapted piece presented"],"required_obligations_refs":["L105-PDF30"]},"runtime_eligible":false,"source_refs":["L105-TXT26-61","L105-PDF29","L105-PDF30","L105-PDF31"],"status":"proposal_example","timing":{"basis":"60minute exam schedule is instruction, not musical event milliseconds","status":"not_applicable","unit":"quarter"},"title":"Final examination / graduation rubric","workbook_id":"fg:workbook:000105"})FATHOM";
result.push_back(std::move(m)); }
return result;
}
