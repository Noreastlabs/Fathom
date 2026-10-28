#include "music_reference_cases.hpp"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
using namespace fathom;
namespace {
int checks=0;std::ofstream results;
void ck(bool b,const std::string& s){++checks;results<<s<<'\t'<<(b?"PASS":"FAIL")<<'\n';if(!b)throw std::runtime_error(s);}
bool issue(const music::Validation& v,const std::string& code,music::Severity severity){return std::any_of(v.issues.begin(),v.issues.end(),[&](const auto& i){return i.code==code&&i.severity==severity;});}
void bad(const music::Model& m,const std::string& code){const auto v=music::validate(m);ck(!v.validReference()&&issue(v,code,music::Severity::Contradiction),"contradiction "+code);}
void refuses(const music::Model& m,const std::string& id){bool refused=false;try{(void)reference::compile(reference_fixtures::checked(m),reference_fixtures::config(Rational{8}));}catch(const std::invalid_argument&){refused=true;}ck(refused,id);}
struct Collector {std::vector<scheduler::Fact> facts;};
bool collect(void* p,const scheduler::Fact& f) noexcept {try{static_cast<Collector*>(p)->facts.push_back(f);return true;}catch(...){return false;}}
scheduler::BoundaryDecision finish(void*,const scheduler::Fact&) noexcept{return {scheduler::BoundaryAction::Stop,nullptr};}
std::vector<float> render(const reference::Program& program){
 scheduler::Cursor cursor;reference::Renderer renderer;Collector got;
 if(!renderer.bind(program)||!cursor.start(program.schedule(),program.schedule().owner(),program.schedule().binding()))throw std::runtime_error("start reference");std::vector<float> out;
 for(int block=0;block<5000;++block){const auto begin=cursor.snapshot().processedThrough;got.facts.clear();const bool running=cursor.process(128,program.schedule().owner(),collect,&got,finish,nullptr);const auto end=cursor.snapshot().processedThrough;std::size_t index=0;
  for(auto frame=begin;frame<end;++frame){while(index<got.facts.size()&&got.facts[index].frame==frame)if(!renderer.accept(got.facts[index++]))throw std::runtime_error("accept fact");float sample{};if(!renderer.sampleFrame(frame,sample))throw std::runtime_error("sample frame");out.push_back(sample);}
  while(index<got.facts.size()){const auto& f=got.facts[index++];if(f.frame!=end||!renderer.accept(f))throw std::runtime_error("terminal fact");}
  if(!running){if(renderer.failed()||cursor.snapshot().reason!=scheduler::StopReason::Requested)throw std::runtime_error("unexpected terminal");renderer.stop();return out;}
 }throw std::runtime_error("bounded digital watchdog");
}
void dump(const std::filesystem::path& root,const std::string& id,const tab::Document& doc,const std::vector<float>& pcm){
 std::ofstream raw(root/(id+".f32"),std::ios::binary);raw.write(reinterpret_cast<const char*>(pcm.data()),static_cast<std::streamsize>(pcm.size()*sizeof(float)));raw.flush();ck(raw.good(),id+" retained digital mono");
 std::ofstream text(root/(id+".txt"));text<<doc.overview()<<'\n';for(const auto& event:doc.source().events)text<<doc.detail(event.id)<<'\n';text.flush();ck(text.good(),id+" retained source details");
}
struct ChordMemberExpected {int string,displayString,fret,physicalFret,midi;const char* finger;const char* note;};
void checkL49ChordProjections(const std::vector<music::Model>& controls,const std::filesystem::path& root){
 const std::array<ChordMemberExpected,6> eExpected{{
  {1,6,0,0,40,"O","E2"},{2,5,2,2,47,"2","B2"},{3,4,2,2,52,"3","E3"},
  {4,3,1,1,56,"1","G#3"},{5,2,0,0,59,"O","B3"},{6,1,0,0,64,"O","E4"}}};
 const std::array<ChordMemberExpected,6> emExpected{{
  {1,6,0,0,40,"O","E2"},{2,5,2,2,47,"2","B2"},{3,4,2,2,52,"3","E3"},
  {4,3,0,0,55,"O","G3"},{5,2,0,0,59,"O","B3"},{6,1,0,0,64,"O","E4"}}};
 const auto sourceIt=std::find_if(controls.begin(),controls.end(),[](const auto& m){return m.itemId=="fg:item:000008";});
 ck(sourceIt!=controls.end(),"L49 accepted E/Em source fixture exists");
 const auto& source=*sourceIt;
 ck(source.proposalExample&&!source.syntheticFixture&&source.sourceRefs==std::vector<std::string>{"L49-TXT49-61"}&&source.instrument.openMidi==std::vector<int>({40,45,50,55,59,64})&&source.instrument.capo==0,"L49 proposal identity, source and standard tuning retained");
 ck(source.events.size()==2,"L49 source retains two alternative chord events");
 std::ofstream rows(root/"l49-chord-projections.tsv");
 rows<<"chord\tevent\tinternalString\tdisplayString\trelativeFret\tphysicalFret\tfinger\tmidi\thz\tstartFrame\tendFrame\n";
 for(bool minor:{false,true}){
  const auto& expected=minor?emExpected:eExpected;
  const auto eventId=std::string("fg:item:000008:event:")+(minor?"0002":"0001");
  const auto symbol=minor?"Em":"E";
  const auto eventIt=std::find_if(source.events.begin(),source.events.end(),[&](const auto& event){return event.id==eventId;});
  ck(eventIt!=source.events.end(),std::string("L49 ")+symbol+" source event identity");
  const auto& event=*eventIt;
  ck(event.kind==music::Kind::Chord&&event.chordSymbol==symbol&&event.sourceRef=="L49-TXT49-61"&&event.tones.size()==expected.size(),std::string("L49 ")+symbol+" authored chord symbol, source and six tones");
  ck(!event.span.onset&&!event.span.duration&&std::all_of(event.tones.begin(),event.tones.end(),[](const auto& tone){return tone.memberSpan&&!tone.memberSpan->onset&&!tone.memberSpan->duration;}),std::string("L49 ")+symbol+" authored onset and duration remain unspecified");
  const auto validated=music::validate(source);
  ck(validated.validReference(),std::string("L49 ")+symbol+" valid source reference model");
  const auto projectionIt=std::find_if(validated.model->projections().begin(),validated.model->projections().end(),[&](const auto& projection){return projection.eventId==eventId;});
  ck(projectionIt!=validated.model->projections().end(),std::string("L49 ")+symbol+" validation retains chord projection identity");
  const auto& projection=*projectionIt;
  ck(projection.kind==music::Kind::Chord&&projection.tones.size()==expected.size(),std::string("L49 ")+symbol+" validation retains simultaneous six-tone chord");
  tab::Document sourceTab(validated.model);
  ck(!sourceTab.allTimed(),std::string("L49 ")+symbol+" TAB does not invent source timing");
  const auto sourceDetail=sourceTab.detail(eventId);
  ck(sourceDetail.find("Source: L49-TXT49-61")!=std::string::npos&&sourceDetail.find("onset unspecified; duration unspecified")!=std::string::npos,std::string("L49 ")+symbol+" TAB retains source and untimed boundary");
  guitar::Setup setup;
  std::copy(source.instrument.openMidi.begin(),source.instrument.openMidi.end(),setup.openMidi.begin());
  setup.capo=source.instrument.capo;
  for(std::size_t i=0;i<expected.size();++i){
   const auto& want=expected[i];const auto& tone=event.tones[i];const auto& projected=projection.tones[i];
   ck(tone.string==want.string&&tone.fret==want.fret&&tone.midi==want.midi&&tone.finger==want.finger&&tone.attack==music::Attack::Picked,std::string("L49 ")+symbol+" independent source member "+std::to_string(i+1));
   ck(projected.string==want.string&&projected.fret==want.fret&&projected.soundingMidi==want.midi&&projected.finger==want.finger,std::string("L49 ")+symbol+" validated member projection "+std::to_string(i+1));
   const auto position=guitar::position(setup,want.string,want.fret);
   ck(position.available()&&position.physicalFret==want.physicalFret&&position.midi==want.midi,std::string("L49 ")+symbol+" guitar position "+std::to_string(i+1));
   const auto memberText="String "+std::to_string(want.displayString)+" (internal "+std::to_string(want.string)+"), fret "+std::to_string(want.fret)+"; "+want.note+" (derived); MIDI "+std::to_string(want.midi)+"; authored spelling unspecified\nFng: "+want.finger+"; Deg: unspecified";
   ck(sourceTab.displayString(want.string)==want.displayString&&sourceDetail.find(memberText)!=std::string::npos,std::string("L49 ")+symbol+" TAB string/pitch/finger "+std::to_string(i+1));
  }
  refuses(source,std::string("L49 ")+symbol+" untimed source refuses reference playback");

  auto timed=reference_fixtures::chord(minor);
  ck(timed.itemId==source.itemId&&timed.proposalExample&&timed.syntheticFixture&&timed.sourceRefs==source.sourceRefs,std::string("L49 ")+symbol+" synthetic timing remains a non-runtime QA copy");
  ck(timed.events.size()==2&&timed.events[0].id==eventId&&timed.events[0].sourceRef==event.sourceRef&&timed.events[0].chordSymbol==symbol&&timed.events[0].span==music::Span{Rational{},Rational{2}},std::string("L49 ")+symbol+" synthetic event span explicit and source-linked");
  ck(std::all_of(timed.events[0].tones.begin(),timed.events[0].tones.end(),[](const auto& tone){return tone.memberSpan&&*tone.memberSpan==music::Span{Rational{},Rational{2}};}),std::string("L49 ")+symbol+" synthetic member spans explicit");
  const auto timedValidated=music::validate(timed);
  ck(timedValidated.validReference(),std::string("L49 ")+symbol+" synthetic method fixture validates");
  tab::Document timedTab(timedValidated.model);
  const auto atQuarter=timedTab.at(Rational{1});
  ck(atQuarter.events==std::vector<std::string>{eventId}&&atQuarter.sounding.size()==expected.size(),std::string("L49 ")+symbol+" TAB query reports one chord and six sounding members");
  for(std::size_t i=0;i<expected.size();++i)ck(atQuarter.sounding[i].event==eventId&&atQuarter.sounding[i].string==expected[i].string,std::string("L49 ")+symbol+" TAB simultaneous member "+std::to_string(i+1));
  const auto program=reference::compile(timedValidated.model,reference_fixtures::config(Rational{5,2}));
  ck(program.voices().size()==expected.size(),std::string("L49 ")+symbol+" reference program has six voices");
  for(std::size_t i=0;i<expected.size();++i){
   const auto& want=expected[i];const auto& voice=program.voices()[i];
   ck(voice.string==want.string&&voice.midi==want.midi&&voice.sourceEvents==std::vector<std::string>{eventId},std::string("L49 ")+symbol+" reference voice retains event/string/pitch "+std::to_string(i+1));
   ck(std::abs(voice.hz-440.0*std::pow(2.0,static_cast<double>(want.midi-69)/12))<1e-9&&voice.onset==Rational{}&&voice.end==Rational{2},std::string("L49 ")+symbol+" reference frequency and shared gate "+std::to_string(i+1));
   ck(voice.startFrames.n==0&&voice.startFrames.d==1&&voice.endFrames.n==44100&&voice.endFrames.d==1,std::string("L49 ")+symbol+" reference sample gate "+std::to_string(i+1));
   rows<<symbol<<'\t'<<eventId<<'\t'<<want.string<<'\t'<<want.displayString<<'\t'<<want.fret<<'\t'<<want.physicalFret<<'\t'<<want.finger<<'\t'<<voice.midi<<'\t'<<std::setprecision(17)<<voice.hz<<'\t'<<voice.startFrames.n<<'\t'<<voice.endFrames.n<<'\n';
  }
  const auto pcm=render(program);
  ck(pcm.size()==55125&&std::all_of(pcm.begin(),pcm.end(),[](float value){return std::isfinite(value);}),std::string("L49 ")+symbol+" finite synthetic chord render and half-quarter tail");
  ck(std::any_of(pcm.begin(),pcm.begin()+44100,[](float value){return value!=0;})&&std::all_of(pcm.begin()+44100,pcm.end(),[](float value){return value==0;}),std::string("L49 ")+symbol+" digital chord signal and exact synthetic silence");
  dump(root,std::string("L49-")+symbol,timedTab,pcm);
 }
 ck(std::equal(eExpected.begin(),eExpected.begin()+3,emExpected.begin(),[](const auto& a,const auto& b){return a.string==b.string&&a.fret==b.fret&&a.midi==b.midi&&a.finger==b.finger;})&&eExpected[3].string==emExpected[3].string&&eExpected[3].midi==56&&emExpected[3].midi==55&&eExpected[3].fret==1&&emExpected[3].fret==0&&std::equal(eExpected.begin()+4,eExpected.end(),emExpected.begin()+4,[](const auto& a,const auto& b){return a.string==b.string&&a.fret==b.fret&&a.midi==b.midi&&a.finger==b.finger;}),"L49 E and Em differ only at internal-string-4 major/minor-third member");
 auto wrong=source;auto wrongEvent=std::find_if(wrong.events.begin(),wrong.events.end(),[](const auto& event){return event.id=="fg:item:000008:event:0001";});wrongEvent->tones[3].midi=55;bad(wrong,"pitch_position");
 rows.flush();ck(rows.good(),"L49 retained projection rows valid");
}
}
int main(int argc,char** argv){try{
 if(argc!=2||std::filesystem::exists(argv[1]))throw std::runtime_error("New output directory required");const std::filesystem::path root=argv[1];std::filesystem::create_directories(root);results.open(root/"checks.tsv");std::ofstream rows(root/"positions.tsv");rows<<"id\tinternalString\tdisplayString\trelativeFret\tphysicalFret\tmidi\thz\tstartFrame\tendFrame\tframes\tname\n";
 for(const auto& c:music_references::positions){const auto m=music_references::model(c);const auto v=music::validate(m);ck(v.validReference(),std::string(c.id)+" valid synthetic music");const tab::Document tab(v.model);auto cfg=reference_fixtures::config(Rational{2});auto program=reference::compile(v.model,cfg);auto s=music_references::setup(c);const auto p=guitar::position(s,c.string,c.fret);
  ck(p.available()&&p.physicalFret==c.physical&&p.midi==c.midi,std::string(c.id)+" setup independent expected position");
  ck(v.model->projections()[0].tones[0].soundingMidi==c.midi&&v.model->projections()[0].tones[0].fret==c.fret,std::string(c.id)+" model exact expected pitch/fret");
  const auto detail=tab.detail("position");ck(tab.displayString(c.string)==7-c.string&&detail.find("fret "+std::to_string(c.fret))!=std::string::npos&&detail.find(std::string(c.name)+" (derived)")!=std::string::npos,std::string(c.id)+" TAB derived pitch/position");
  ck(program.voices().size()==1&&program.voices()[0].midi==c.midi&&program.voices()[0].string==c.string&&program.voices()[0].sourceEvents==std::vector<std::string>{"position"},std::string(c.id)+" voice identity same source");const auto& voice=program.voices()[0];
  ck(std::abs(voice.hz-440.0*std::pow(2.0,static_cast<double>(c.midi-69)/12))<1e-9,std::string(c.id)+" equal-temperament numerical only");
  ck(voice.startFrames.n==0&&voice.endFrames.n==22050&&voice.endFrames.d==1,std::string(c.id)+" exact quarter gate frames");
  ck(tab.at(Rational{1}).events==std::vector<std::string>{"rest"}&&tab.at(Rational{1}).sounding.empty()&&tab.at(Rational{2}).events.empty(),std::string(c.id)+" half-open full rest");
  const auto pcm=render(program);ck(pcm.size()==44100&&std::all_of(pcm.begin(),pcm.end(),[](float f){return std::isfinite(f);}),std::string(c.id)+" finite digital one cycle");ck(std::any_of(pcm.begin(),pcm.begin()+22050,[](float f){return f!=0;})&&std::all_of(pcm.begin()+22050,pcm.end(),[](float f){return f==0;}),std::string(c.id)+" note exists and whole rest silent");
  const auto mirrored= c.left?guitar::Handedness::Right:guitar::Handedness::Left;s.handedness=mirrored;ck(guitar::position(s,c.string,c.fret).midi==c.midi,std::string(c.id)+" handedness no retuning");
  auto declared=s;declared.openMidi[0]+=1;const auto comp=guitar::compare(*v.model,declared);ck(!comp.warnings.empty()&&comp.accessAllowed&&comp.referenceUsesAuthoredSetup&&program.voices()[0].midi==c.midi&&v.model->source().instrument.openMidi==m.instrument.openMidi,std::string(c.id)+" mismatch warns retains authored reference");
  rows<<c.id<<'\t'<<c.string<<'\t'<<tab.displayString(c.string)<<'\t'<<c.fret<<'\t'<<p.physicalFret<<'\t'<<voice.midi<<'\t'<<std::setprecision(17)<<voice.hz<<'\t'<<voice.startFrames.n<<'\t'<<voice.endFrames.n<<'\t'<<pcm.size()<<'\t'<<c.name<<'\n';dump(root,c.id,tab,pcm);
 }
 auto originals=controlExamples();checkL49ChordProjections(originals,root);const auto l12=reference_fixtures::checked(originals[2]);tab::Document d12(l12);const auto p12=reference::compile(l12,reference_fixtures::config(Rational{8}));
 for(auto i:{7u,8u}){const auto& e=originals[2].events[i];ck(e.tones[0].midi==57&&e.tones[0].degrees[0].sourceLabel=="8"&&p12.voices()[i].midi==57&&p12.voices()[i].sourceEvents==std::vector<std::string>{e.id},"L12 exact distinct octave-root source/program "+std::to_string(i));ck(d12.detail(e.id).find("8 [")!=std::string::npos,"L12 octave degree remains degree not finger");}
 ck(p12.voices()[7].sourceEvents!=p12.voices()[8].sourceEvents&&p12.voices()[7].end==p12.voices()[8].onset,"L12 repeated root is new pick at boundary");
 ck(music::scalePitchClasses(9,{0,2,4,5,7,9,11})==std::vector<int>({9,11,1,2,4,6,8})&&music::intervalSemitones(45,57)==12,"A major within-octave pitch classes plus explicit octave interval");
 const auto l15=reference_fixtures::checked(originals[3]);tab::Document d15(l15);const auto p15=reference::compile(l15,reference_fixtures::config(Rational{1}));ck(p15.voices().size()==3,"L15 three source attacks");
 for(std::size_t i=0;i<3;++i){const auto& e=originals[3].events[i];ck(p15.voices()[i].startFrames.n==7350*i&&p15.voices()[i].startFrames.d==1&&d15.at(Rational{static_cast<std::int64_t>(i),3}).events==std::vector<std::string>{e.id},"L15 cross-view exact triplet "+std::to_string(i));}
 const auto l39=reference_fixtures::checked(originals[5]);tab::Document d39(l39);const auto& dual=originals[5].events[4];const auto desc=d39.detail(dual.id);ck(dual.tones[0].midi==69&&dual.tones[0].finger=="2"&&desc.find("1 [A-major] | b3 [F#-minor]")!=std::string::npos&&desc.find("Fng: 2")!=std::string::npos,"L39 A4 distinct degree contexts and finger");ck(!d39.allTimed(),"L39 source time not invented");refuses(originals[5],"L39 source reference refuses playback");
 for(auto pair:{std::pair{"L12",&d12},std::pair{"L15",&d15},std::pair{"L39",&d39}}){std::ofstream file(root/(std::string(pair.first)+"-source.txt"));file<<pair.second->overview()<<'\n';for(const auto& e:pair.second->source().events)file<<pair.second->detail(e.id)<<'\n';file.flush();ck(file.good(),std::string(pair.first)+" exact source snapshot");}
 for(bool repick:{false,true}){auto m=music_references::held(repick);auto v=reference_fixtures::checked(m);tab::Document d(v);auto p=reference::compile(v,reference_fixtures::config(Rational{3}));ck(p.voices().size()==(repick?2u:1u),"held/repicked voice count");ck(d.at(Rational{1}).events==std::vector<std::string>{"continued"}&&d.at(Rational{1}).sounding[0].event=="continued","TAB continuation source identity regardless of attack");if(!repick)ck(p.voices()[0].sourceEvents==std::vector<std::string>({"picked","continued"}),"one held voice retains both source events");auto pcm=render(p);ck(pcm.size()==66150&&std::all_of(pcm.begin()+44100,pcm.end(),[](float f){return f==0;}),"whole final rest silent at exact gate");dump(root,repick?"repicked":"held",d,pcm);}
 auto base=music_references::model(music_references::positions[2]);auto m=base;m.events[0].tones[0].midi++;bad(m,"pitch_position");m=base;m.events[0].tones[0].fret++;bad(m,"pitch_position");m=base;m.events[0].tones[0].string=7;bad(m,"position");m=base;m.instrument.capo++;bad(m,"pitch_position");m=base;m.events[0].tones[0].finger="8";bad(m,"finger");
 m=base;m.events[0].tones[0].degrees={{"A-major","2",9,2,0,{}}};bad(m,"degree_pitch");m=music_references::held();m.events[1].tones[0].tieFrom="missing";bad(m,"tie_identity");m=base;m.measures[0].eventIds={"position"};bad(m,"measure_total");m=base;m.events[0].tones[0].spelling="C";bad(m,"spelling_pitch");
 m=music_references::model(music_references::positions[4]);m.events[0].tones[0].spelling="Db";auto enh=reference_fixtures::checked(m);auto ep=reference::compile(enh,reference_fixtures::config(Rational{2}));ck(tab::Document(enh).detail("position").find("Db (authored)")!=std::string::npos&&ep.voices()[0].midi==61,"authored Db preserved beside unchanged sounding MIDI61");
 m=base;m.events[0].tones[0].attack=music::Attack::Harmonic;auto unresolved=music::validate(m);ck(unresolved.validReference()&&issue(unresolved,"harmonic_binding",music::Severity::Unresolved),"harmonic unresolved not false contradiction");refuses(m,"unresolved harmonic playback refuses");
 m=base;m.events[0].tones[0].attack=music::Attack::Vibrato;auto unsupported=music::validate(m);ck(unsupported.validReference()&&unsupported.issues.empty(),"resolved unsupported technique is valid music");auto supported=music::assessReadiness(*unsupported.model,{{music::Attack::Picked,music::Attack::Held},false,true,true});ck(!supported.technicallyRenderable&&std::any_of(supported.issues.begin(),supported.issues.end(),[](const auto& i){return i.code=="unsupported_technique"&&i.severity==music::Severity::Unsupported;}),"resolved vibrato is unsupported by this renderer only");refuses(m,"resolved unsupported vibrato compile refusal");
 auto readiness=music::assessReadiness(*l15,{{music::Attack::Picked,music::Attack::Held},false,true,true});ck(readiness.technicallyRenderable&&!readiness.curriculumPlaybackAuthorized,"technical valid does not admit source curriculum");
 rows.flush();ck(rows.good()&&results.good(),"retained output streams valid");results.flush();std::cout<<"PASS "<<checks<<" cross-projection reference checks; digital only, no native/human/fretboard admission\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
