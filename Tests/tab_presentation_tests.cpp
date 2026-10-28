#include "core/TabPresentation.hpp"
#include "reference_audio_fixtures.hpp"
#include <fstream>
#include <algorithm>
#include <iostream>
#include <filesystem>
#include <limits>

namespace {
int checks=0;
void check(bool good,const std::string& name){++checks;if(!good)throw std::runtime_error(name);}
bool has(const std::vector<std::string>& values,const std::string& s){return std::find(values.begin(),values.end(),s)!=values.end();}
}
int main(int argc,char** argv){
    using namespace fathom;using namespace reference_fixtures;
    try{
        if(argc!=2)throw std::invalid_argument("Expected new output directory");const auto dir=std::filesystem::path(argv[1]);if(std::filesystem::exists(dir))throw std::invalid_argument("Output already exists");std::filesystem::create_directories(dir);
        auto controls=controlExamples();std::size_t events=0,tones=0;
        for(auto& m:controls){auto v=checked(m);tab::Document d(v);check(d.source().itemId==m.itemId && d.source().preservedRecordJson==m.preservedRecordJson,"exact full record "+m.itemId);check(d.overview().find(m.preservedRecordJson)!=std::string::npos,"full authored record surfaced");check(d.event("missing")==nullptr,"unknown ID not substituted");
            for(const auto& e:m.events){++events;const auto detail=d.detail(e.id);check(d.event(e.id)->id==e.id && detail.find(e.sourceRef)!=std::string::npos,"source event locator");check(detail.find(tab::span(e.span))!=std::string::npos,"exact span label");for(const auto& t:e.tones){++tones;check(d.displayString(t.string)==7-t.string,"source low string displayed bottom");check(detail.find("Fng: "+(t.finger.empty()?std::string("unspecified"):t.finger))!=std::string::npos,"finger namespace");check(detail.find("Deg: "+tab::degrees(t))!=std::string::npos,"degree context namespace");check(!tab::noteName(t).empty(),"named pitch display");} }
            std::ofstream output(dir/(m.itemId.substr(8)+".txt"));output<<d.overview()<<'\n';for(const auto& e:m.events)output<<"\n--- EVENT ---\n"<<d.detail(e.id);check(output.good(),"retained details");
        }
        check(events==69 && tones==59,"retained control inventory only");
        tab::Document dual(checked(controls[5]));auto text=dual.detail(controls[5].events[4].id);check(text.find("1 [A-major]")!=std::string::npos && text.find("b3 [F#-minor]")!=std::string::npos,"L39 dual context exact");check(text.find("Fng: 2")!=std::string::npos,"L39 separate finger2");check(!dual.allTimed() && dual.at(Rational{}).events.empty(),"unknown timing cannot highlight");
        tab::Document triplet(checked(controls[3]));check(triplet.at(Rational{1,3}).events==std::vector<std::string>{controls[3].events[1].id},"exact triplet boundary not previous");
        auto m=held();tab::Document chain(checked(m));check(chain.at(Rational{1,2}).events==std::vector<std::string>{m.events[1].id},"held keeps next source event identity");check(chain.at(Rational{1}).events==std::vector<std::string>{m.events[2].id} && chain.at(Rational{1}).sounding.empty(),"final rest is current and silent");check(chain.at(Rational{3,2}).events.empty(),"half-open last end");check(chain.detail(m.events[1].id).find("held (no new pick)")!=std::string::npos,"held not repicked");
        auto airModel=air();tab::Document contactDoc(checked(airModel));auto at=contactDoc.at(Rational{1,2});check(at.events.empty() && at.sounding.size()==1 && at.sounding[0].event=="pitched-contact","hand gap preserves independent sounding gate");at=contactDoc.at(Rational{1,4});check(at.events==std::vector<std::string>{"air"} && at.sounding.size()==1,"air does not cancel gate");
        auto chordModel=chord(false);tab::Document chordDoc(checked(chordModel));check(chordDoc.at(Rational{}).events.size()==1 && chordDoc.at(Rational{}).sounding.size()==6,"chord one source event six simultaneous tones");
        m=synthetic("zero-release");music::Event release;release.id="zero";release.kind=music::Kind::Contact;release.contact=music::Contact::Release;release.span={Rational{1},Rational{}};release.scopeStrings={1};m.events={release};tab::Document zero(checked(m));check(zero.at(Rational{1}).events.empty()&&zero.at(Rational{1}).instants==std::vector<std::string>{"zero"},"instant release distinct from interval");
        m=synthetic("overlap");m.events={note("one",Rational{},Rational{2},1,0,40),note("two",Rational{1},Rational{1},2,0,45)};tab::Document overlap(checked(m));check(overlap.at(Rational{1}).events.size()==2 && overlap.at(Rational{1}).sounding.size()==2,"all overlapping strings selected");
        auto source=checked(m);tab::Document immutable(source);m.events[0].id="changed";check(immutable.event("one") && !immutable.event("changed"),"caller mutation cannot affect validated model");
        bool rejected=false;try{tab::Document invalid(nullptr);}catch(const std::invalid_argument&){rejected=true;}check(rejected,"null model refused");rejected=false;try{(void)immutable.detail("missing");}catch(const std::invalid_argument&){rejected=true;}check(rejected,"unknown selection detail refuses");
        tab::Document task(checked(controls[10]));check(task.source().events.empty() && task.overview().find("A7")!=std::string::npos && task.overview().find("C#")!=std::string::npos,"eventless L83 preserved without inferred voicing");
        music::Tone t;t.midi=45;check(tab::noteName(t)=="A2 (derived)","MIDI named pitch labelled derived");t.midi=61;check(tab::noteName(t)=="C#4 (derived)","sharp choice explicitly derived");t.spelling="Db";check(tab::noteName(t)=="Db (authored)","authored enharmonic preserved");
        check(!has(immutable.at(Rational{2}).events,"one"),"end is exclusive");std::cout<<"PASS "<<checks<<" TAB semantic checks; no clock or runtime admission\n";return 0;
    }catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}
}
