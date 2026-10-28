#include "desktop/PlaybackFretboardView.hpp"
#include "core/TabPlayback.hpp"
#include "playback_fretboard_fixtures.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <algorithm>
using namespace fathom;
using View=desktop::PlaybackFretboardView;
int main(int argc,char**argv){int checks=0;try{
 if(argc!=2||std::filesystem::exists(argv[1]))throw std::runtime_error("fresh output directory required");
 std::filesystem::create_directory(argv[1]);std::ofstream log(std::filesystem::path(argv[1])/"checks.tsv");
 auto ck=[&](bool b,const char*n){++checks;log<<n<<'\t'<<(b?"PASS":"FAIL")<<'\n';if(!b)throw std::runtime_error(n);};
 juce::ScopedJuceInitialiser_GUI gui;View v;auto authored=playback_fretboard_fixtures::checked(playback_fretboard_fixtures::source());
 v.setModel(authored);guitar::Setup setup;setup.fretCount=24;v.setSetup(setup);
 auto cell=[&](int s,int f)->const View::Cell&{for(const auto&c:v.projection())if(c.internalString==s&&c.relativeFret==f)return c;throw std::runtime_error("missing cell");};
 auto active=[&]{return std::count_if(v.projection().begin(),v.projection().end(),[](const auto&c){return c.active;});};
 ck(v.projection().size()==150&&active()==0,"six strings and25 positions, no initial activity");
 // Paint/projection contract: passive Note map is not an active playback fact.
 v.setBounds(0,0,1400,300);v.setMode(View::Mode::Note);v.setSpelling(View::Spelling::Flat);
 auto paintNote=[&]{juce::Image image(juce::Image::ARGB,1400,300,true);juce::Graphics graphics(image);v.paint(graphics);return image;};
 const auto passive=paintNote();const auto passiveNote=cell(1,0).note;const auto passiveMidi=cell(1,0).midi;
 ck(active()==0&&!passiveNote.empty(),"passive Note labels exist with zero active playback markers");
 v.setActiveEvents({"simultaneous-open-and-24"});const auto sounding=paintNote();auto bounds=v.cellBounds(1,0).toNearestInt();int changed=0;
 for(int y=bounds.getY();y<bounds.getBottom();++y)for(int x=bounds.getX();x<bounds.getRight();++x)if(passive.getPixelAt(x,y)!=sounding.getPixelAt(x,y))++changed;
 ck(active()==2&&changed>20&&cell(1,0).note==passiveNote&&cell(1,0).midi==passiveMidi,"accepted authored tones change emphasis without changing passive Note pitch labels");
 v.setActiveEvents({});const auto cleared=paintNote();int mismatches=0;
 for(int y=0;y<300;++y)for(int x=0;x<1400;++x)if(passive.getPixelAt(x,y)!=cleared.getPixelAt(x,y))++mismatches;
 ck(active()==0&&mismatches==0&&cell(1,0).note==passiveNote,"clear returns exact passive map instead of erasing notes or inventing active color");
 v.setMode(View::Mode::Basic);v.setSpelling(View::Spelling::Sharp);

 v.setActiveEvents({"simultaneous-open-and-24"});ck(active()==2&&cell(1,0).active&&cell(6,24).active,"simultaneous open0 andfret24 projected");
 ck(cell(1,0).finger=="O"&&!cell(1,0).fingerUnknown&&cell(6,24).finger=="4","authored open/finger4 retained");
 ck(cell(6,24).midi==88&&cell(6,24).eventIds==std::vector<std::string>{"simultaneous-open-and-24"},"exact source event andpitch");
 v.setActiveEvents({"flat-A-letter"});ck(active()==1&&cell(1,4).fingerUnknown&&cell(1,4).finger=="?","unknown finger never invented");
 v.setMode(View::Mode::Note);v.setSpelling(View::Spelling::Flat);ck(cell(1,4).midi==44&&cell(1,4).note=="Ab","flat letterA samepitch");
 v.setSpelling(View::Spelling::Sharp);ck(cell(1,4).midi==44&&cell(1,4).note=="G#","sharp letterG samepitch");
 v.setActiveEvents({"rest"});ck(active()==0,"rest no sounding highlight");v.setActiveEvents({"not-an-authored-event"});ck(active()==0,"unknown event no guessed highlight");
 v.setActiveEvents({"simultaneous-open-and-24"});v.setModel(authored);ck(active()==0,"model rebind clears prior owner highlight");
 for(auto tuning:{guitar::tuning(guitar::Preset::Standard),guitar::tuning(guitar::Preset::DropD),playback_fretboard_fixtures::openE()}){setup.openMidi=tuning;v.setSetup(setup);for(int s=1;s<=6;++s)ck(cell(s,0).midi==tuning[std::size_t(s-1)]&&cell(s,24).midi==tuning[std::size_t(s-1)]+24,"declared tuning independently changes displayed neck pitches");}
 ck(authored->source().events[0].tones[0].midi==40&&authored->source().events[1].tones[0].spelling=="Ab"&&authored->source().events[1].tones[0].finger.empty(),"declared display leaves authoredpitch/spelling/finger unchanged");
 setup=guitar::Setup{};setup.fretCount=24;v.setSetup(setup);v.setActiveEvents({"simultaneous-open-and-24"});
 for(auto bounds:{juce::Rectangle<int>{0,0,640,120},juce::Rectangle<int>{0,0,1400,240},juce::Rectangle<int>{0,0,3840,300}}){v.setBounds(bounds);for(const auto&c:v.projection()){auto b=v.cellBounds(c.internalString,c.relativeFret);ck(b.getWidth()>0&&b.getHeight()>0&&v.getLocalBounds().toFloat().contains(b),"all projection cells inside component afterresize");}ck(active()==2,"resize does not alter musical projection");}
 auto right0=v.cellBounds(1,0),right24=v.cellBounds(1,24);setup.handedness=guitar::Handedness::Left;v.setSetup(setup);ck(v.cellBounds(1,0).getX()>v.cellBounds(1,24).getX()&&right0.getX()<right24.getX(),"handedness reverses geometry without source mutation");


 v.setBounds(0,0,1400,300);v.setMode(View::Mode::Note);v.setSpelling(View::Spelling::Sharp);
 auto paletteModel=reference_fixtures::synthetic("seven-letter-palette");std::vector<std::string> ids;
 for(int f=0;f<12;++f){auto e=reference_fixtures::note("palette-"+std::to_string(f),Rational{f},Rational{1},1,f,40+f);ids.push_back(e.id);paletteModel.events.push_back(e);}
 v.setModel(playback_fretboard_fixtures::checked(paletteModel));v.setActiveEvents(ids);
 juce::Image image(juce::Image::ARGB,1400,300,true);juce::Graphics graphics(image);v.paint(graphics);
 const std::vector<std::pair<int,juce::uint32>> colours{{5,0xfff4be72},{7,0xffb6c6ff},{8,0xff89d8c8},{10,0xfff49ba5},{0,0xffddd084},{1,0xffc8a7eb},{3,0xff8fc7ee}};
 for(auto [f,argb]:colours){auto b=v.cellBounds(1,f).toNearestInt();int pixels=0;for(int y=b.getY();y<b.getBottom();++y)for(int x=b.getX();x<b.getRight();++x)if(image.getPixelAt(x,y).getARGB()==argb)++pixels;ck(pixels>20,"paint contains specified distinct letterclass colour");}
 v.setModel(authored);v.setActiveEvents({"flat-A-letter"});v.setSpelling(View::Spelling::Flat);image.clear(image.getBounds(),juce::Colours::transparentBlack);v.paint(graphics);
 auto countColour=[&](juce::uint32 argb){auto b=v.cellBounds(1,4).toNearestInt();int n=0;for(int y=b.getY();y<b.getBottom();++y)for(int x=b.getX();x<b.getRight();++x)if(image.getPixelAt(x,y).getARGB()==argb)++n;return n;};
 ck(countColour(0xfff4be72)>20,"Ab rendered Acolour");v.setSpelling(View::Spelling::Sharp);image.clear(image.getBounds(),juce::Colours::transparentBlack);v.paint(graphics);ck(countColour(0xff8fc7ee)>20&&cell(1,4).midi==44,"Gsharp rendered Gcolour withoutpitchchange");
 // Independent accepted-frame oracle; 120 BPM at44100 gives22050 frames/quarter.
 practice::Configuration cfg;cfg.countIn=practice::CountIn::Off;cfg.faithfulWholeSpan=true;cfg.span=Rational{4};cfg.targetCycles=1;
 auto owner=reference_fixtures::owner();practice::Coordinator c;c.begin(owner,practice::Kind::Attempt,"synthetic:presentation-only",cfg);
 tab::Playback clock;auto doc=std::make_shared<const tab::Document>(authored);clock.bind(doc,authored,c);v.setModel(authored);
 std::uint64_t seq=0;
 auto advance=[&](std::uint64_t through,practice::State state){practice::Progress q;q.owner=c.owner();q.sequence=++seq;q.clientAcceptedThrough=q.scheduledThrough=q.activeFrames=through;q.completedCycles=through/88200;q.cursorFrames=through%88200;q.partial=q.cursorFrames!=0;q.state=state;q.terminal=state==practice::State::Paused||state==practice::State::Ended;if(q.terminal){q.requestedStopNs=1;q.uncertainThrough=through;}ck(c.progress(q)&&clock.update(c),"accepted timing fact only");v.setActiveEvents(clock.position().events);return q;};
 advance(1,practice::State::Running);ck(active()==2,"first accepted chord illuminates simultaneously");
 advance(22050,practice::State::Running);ck(active()==2,"exclusive event boundary retains priorchord");
 auto paused=advance(22051,practice::State::Paused);ck(active()==1&&cell(1,4).fingerUnknown,"pause freezes accepted flat note");
 ck(!c.progress(paused)&&!clock.update(c)&&active()==1,"duplicate doesnot advance display");
 auto stale=paused;stale.sequence++;stale.owner.epoch++;ck(!c.progress(stale)&&!clock.update(c)&&active()==1,"foreignowner no displayadvance");
 const auto previous=c.owner();c.resume();ck(!clock.update(c),"resume cannot inherit old binding");v.clear();clock.bind(doc,authored,c);v.setModel(authored);seq=0;ck(active()==0&&clock.position().events.empty(),"resume rebind clears highlights until acceptedfact");
 stale.owner=previous;stale.sequence=100;ck(!c.progress(stale)&&!clock.update(c)&&active()==0,"oldpausedowner remains stale afterresume");
 v.clear();ck(active()==0,"stop/navigation clear no retained highlight");
 std::cout<<"PASS "<<checks<<" renderer contract checks\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
