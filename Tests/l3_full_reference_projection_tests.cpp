#include "content/LessonCatalog.hpp"
#include "core/TabPresentation.hpp"
#include "desktop/FretboardView.hpp"
#include "desktop/TabView.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <vector>

using namespace fathom;
namespace {
struct Known { int string, fret, midi; const char* finger; };
// Source-record L3 ascending D-even direction, in the variant's authored order.
constexpr std::array<Known,20> known{{
    {1,5,45,"1"},{1,6,46,"2"},{1,5,45,"1"},{2,6,51,"2"},
    {2,5,50,"1"},{2,6,51,"2"},{2,5,50,"1"},{3,6,56,"2"},
    {3,5,55,"1"},{3,6,56,"2"},{3,5,55,"1"},{4,6,61,"2"},
    {4,5,60,"1"},{4,6,61,"2"},{4,5,60,"1"},{5,6,65,"2"},
    {5,5,64,"1"},{5,6,65,"2"},{5,5,64,"1"},{6,6,70,"2"}
}};
// Independently transcribed Level12 Rung05 Db-major cell: original TXT lines
// 14-39 and 98-109, checked against PDF pages 1, 2 and 4. The chosen 120 BPM
// below is a test configuration, not an authored fixed tempo.
constexpr std::array<Known,16> rung05Known{{
    {1,9,49,"2"},{1,11,51,"4"},{2,8,53,"1"},{2,9,54,"2"},
    {2,11,56,"4"},{3,8,58,"1"},{3,10,60,"3"},{3,11,61,"4"},
    {3,11,61,"4"},{3,10,60,"3"},{3,8,58,"1"},{2,11,56,"4"},
    {2,9,54,"2"},{2,8,53,"1"},{1,11,51,"4"},{1,9,49,"2"}
}};
constexpr std::array<const char*,16> rung05Spelling{{
    "Db","Eb","F","Gb","Ab","Bb","C","Db",
    "Db","C","Bb","Ab","Gb","F","Eb","Db"
}};
constexpr std::array<int,16> rung05Degree{{1,2,3,4,5,6,7,8,8,7,6,5,4,3,2,1}};
struct Level20Contact { std::size_t index; int string, fret, midi; const char* finger; const char* spelling; int degree; };
// Fixed from original Level20 Rung01 TXT lines 75-177 (PDF Rung01 pages 3-4):
// the last two contacts and first two contacts of each module transition.
// q is a learning-mode quarter slot from the original one-note-per-click rule,
// not an authored BPM or performed sustain. Module sizes: 30/78/96/52/66.
constexpr std::array<Level20Contact,16> level20Contacts{{
    {0,1,5,45,"2","A",1},{1,1,7,47,"4","B",2},
    {28,1,7,47,"4","B",2},{29,1,5,45,"2","A",1},
    {30,1,5,45,"2","A",1},{31,1,7,47,"4","B",2},
    {106,1,7,47,"4","B",2},{107,1,5,45,"2","A",1},
    {108,1,5,45,"2","A",1},{109,1,7,47,"4","B",2},
    {202,1,7,47,"4","B",2},{203,1,5,45,"2","A",1},
    {204,1,5,45,"2","A",1},{205,2,4,49,"1","C#",3},
    {255,1,5,45,"2","A",1},{256,1,5,45,"2","A",1}
}};
constexpr std::array<Level20Contact,3> level20Terminal{{
    {257,2,4,49,"1","C#",3},{320,2,4,49,"1","C#",3},
    {321,1,5,45,"2","A",1}
}};
const char* level20Ref(std::size_t index) {
    return index<30?"L20-TXT-A-MODULE1":index<108?"L20-TXT-A-MODULE2":
        index<204?"L20-TXT-A-MODULE3":index<256?"L20-TXT-A-MODULE4":
        "L20-TXT-A-MODULE5";
}
struct Facts { std::array<scheduler::Fact,scheduler::maxCallbackEvents> values{}; std::size_t count{}; };
bool collect(void* context,const scheduler::Fact& fact) noexcept {
    auto& buffer=*static_cast<Facts*>(context);
    if(buffer.count==buffer.values.size())return false;
    buffer.values[buffer.count++]=fact;return true;
}
scheduler::BoundaryDecision stopAtCycle(void*,const scheduler::Fact& fact) noexcept {
    return fact.kind==scheduler::FactKind::CycleCompleted
        ?scheduler::BoundaryDecision{scheduler::BoundaryAction::Stop,nullptr}
        :scheduler::BoundaryDecision{};
}
std::string idFor(std::size_t index) {
    auto digits=std::to_string(index+1);
    return "fg:item:000002:event:"+std::string(4-digits.size(),'0')+digits;
}
std::string rung05IdFor(std::size_t index) {
    auto digits=std::to_string(index+1);
    return "fg:item:001145:event:"+std::string(4-digits.size(),'0')+digits;
}
std::string level20IdFor(std::size_t index) {
    auto digits=std::to_string(index+1);
    return "fg:item:001167:event:"+std::string(4-digits.size(),'0')+digits;
}
}
int main(int argc,char** argv) {
    std::size_t checks{};
    try {
        if(argc!=3&&argc!=8&&argc!=21)throw std::invalid_argument(
            "Expected representative bundle and new absolute output directory; optionally the first five installed extensions through Rung05, or the first eighteen through Level20");
        const std::filesystem::path bundle(argv[1]),out(argv[2]);
        if(!out.is_absolute()||std::filesystem::exists(out))throw std::invalid_argument("Output directory must be new and absolute");
        std::filesystem::create_directories(out);
        std::ofstream log(out/"checks.tsv");
        const auto ck=[&](bool pass,const std::string& label){++checks;log<<label<<'\t'<<(pass?"PASS":"FAIL")<<'\n';log.flush();if(!pass)throw std::runtime_error(label);};
        juce::ScopedJuceInitialiser_GUI gui;
        constexpr const char* item="fg:item:000002",*variantId="fg:variant:000006",*eventRef="L3-TXT28-46";
        const auto catalog=lesson::Catalog::load(bundle);
        const auto admission=catalog->admit(item,variantId);
        const auto& variant=catalog->variant(item,variantId);
        const auto model=admission->model();
        const auto& source=model->source();
        const auto& selected=variant.authored.object().at("event_ids").array();
        ck(admission->practiceAllowed()&&variant.model==model&&!source.syntheticFixture&&source.itemId==item&&
           source.sourceRefs==std::vector<std::string>{"L3-TXT5-21",eventRef}&&admission->span()==Rational{5},
           "admitted non-synthetic L3 direction and full five-quarter span");
        ck(selected.size()==known.size()&&source.events.size()==known.size(),"selected authored event inventory has exactly twenty events");

        auto document=std::make_shared<const tab::Document>(model);
        desktop::TabView tabView;tabView.setSize(920,680);tabView.setDocument(document);
        desktop::FretboardView board;board.setSize(550,350);
        scheduler::Owner owner;owner.id[0]=42;owner.id[6]=0x40;owner.id[8]=0x80;owner.generation=owner.epoch=1;
        constexpr std::uint64_t binding=1;constexpr std::uint32_t rate=44100;constexpr std::uint16_t bpm=120;
        const auto config=admission->referenceConfiguration(owner,binding,rate,bpm);
        admission->validateReference(config);
        const auto program=reference::compile(model,config);
        ck(&program.source()==model.get()&&program.schedule().sourceBinding()==admission->sourceBinding()&&
           program.voices().size()==known.size(),"ReferenceAudio uses identical admitted source binding and twenty voices");

        std::array<std::uint64_t,known.size()+1> boundaries{};
        for(std::size_t i=0;i<known.size();++i) {
            const auto label=std::to_string(i+1);
            const auto id=idFor(i);
            const auto& expected=known[i];
            ck(selected[i].string()==id&&source.events[i].id==id&&source.events[i].sourceRef==eventRef&&
               source.events[i].kind==music::Kind::Note&&source.events[i].tones.size()==1&&
               source.events[i].span==music::Span{Rational{static_cast<std::int64_t>(i),4},Rational{1,4}},
               "selected event "+label+" has exact source ID, reference and rational span");
            const auto& tone=source.events[i].tones[0];
            ck(tone.string==expected.string&&tone.fret==expected.fret&&tone.midi==expected.midi&&
               tone.finger==expected.finger&&tone.attack==music::Attack::Picked,
               "selected event "+label+" has known string/fret/MIDI/finger/attack");
            const auto* tabEvent=document->event(id);
            const auto detail=document->detail(id);
            ck(tabView.selectEvent(id)&&tabView.selectedEvent()==id&&tabEvent==&source.events[i]&&
               detail.find(id+"\nSource: "+eventRef)!=std::string::npos&&
               detail.find("String "+std::to_string(7-expected.string)+" (internal "+std::to_string(expected.string)+
                           "), fret "+std::to_string(expected.fret))!=std::string::npos&&
               detail.find("MIDI "+std::to_string(expected.midi))!=std::string::npos&&
               detail.find("Fng: "+std::string(expected.finger))!=std::string::npos&&
               detail.find("onset "+tab::fraction(Rational{static_cast<std::int64_t>(i),4})+
                           "; duration 1/4 quarter units")!=std::string::npos,
               "selected event "+label+" TAB detail keeps exact source, position, pitch, finger and span");
            ck(board.setEvent(model,id)&&board.selectedEventId()==id&&board.markers().size()==1,
               "selected event "+label+" has one fretboard marker");
            const auto& marker=board.markers().front();
            ck(marker.sourceId==item&&marker.sourceRef==eventRef&&marker.eventId==id&&
               marker.internalString==expected.string&&marker.displayString==7-expected.string&&
               marker.relativeFret==expected.fret&&marker.physicalFret==expected.fret&&
               marker.midi==expected.midi&&marker.finger==expected.finger,
               "selected event "+label+" fretboard marker agrees with known source tone");
            const auto& voice=program.voices()[i];
            ck(voice.sourceEvents==std::vector<std::string>{id}&&voice.string==expected.string&&
               voice.midi==expected.midi&&voice.hz==reference::frequency(expected.midi)&&
               voice.onset==Rational{static_cast<std::int64_t>(i),4}&&
               voice.end==Rational{static_cast<std::int64_t>(i+1),4},
               "selected event "+label+" owns one exact ReferenceAudio pitch and gate");
            scheduler::FrameRatio start{},end{};
            ck(scheduler::samples(voice.onset,rate,bpm,scheduler::BeatUnit::Quarter,start)&&
               scheduler::samples(voice.end,rate,bpm,scheduler::BeatUnit::Quarter,end)&&
               voice.startFrames.n==start.n&&voice.startFrames.d==start.d&&
               voice.endFrames.n==end.n&&voice.endFrames.d==end.d&&
               scheduler::round(start,boundaries[i])&&scheduler::round(end,boundaries[i+1]),
               "selected event "+label+" has exact rational frame plan");
            const auto& events=program.schedule().events();
            const auto attack=std::find_if(events.begin(),events.end(),[&](const auto& e){return e.sourceEvent==i+1&&e.role==scheduler::Role::Reference&&e.action==scheduler::Action::Attack;});
            const auto release=std::find_if(events.begin(),events.end(),[&](const auto& e){return e.sourceEvent==i+1&&e.role==scheduler::Role::Reference&&e.action==scheduler::Action::Release;});
            ck(attack!=events.end()&&release!=events.end()&&attack->structural==voice.onset&&
               release->structural==voice.end&&attack->offset.n==start.n&&attack->offset.d==start.d&&
               release->offset.n==end.n&&release->offset.d==end.d,
               "selected event "+label+" has exact scheduled Attack and Release");
        }
        ck(boundaries.front()==0&&boundaries.back()==110250,
           "five-quarter cycle has the exact 110250-frame 44.1 kHz/120 BPM boundary");

        auto wrong=source;wrong.events[7].tones[0].midi++;
        const auto wrongValidation=music::validate(wrong);
        ck(!wrongValidation.validReference(),"wrong pitch for event eight is refused before ReferenceAudio Program");
        const auto alternate=catalog->admit(item,"fg:variant:000008");
        const auto foreign=alternate->referenceConfiguration(owner,binding+1,rate,bpm);
        bool foreignRefused=false;
        try{admission->validateReference(foreign);}catch(const std::exception&){foreignRefused=true;}
        ck(foreignRefused,"foreign variant event/source binding is refused before selected Program");

        scheduler::Cursor cursor;reference::Renderer renderer;
        ck(cursor.start(program.schedule(),owner,binding)&&renderer.bind(program),
           "shared software Cursor and Renderer bind exact selected Program");
        std::vector<float> pcm;pcm.reserve(boundaries.back());
        std::size_t factCount{};bool requestedStop=false;
        for(std::size_t iteration=0;iteration<100000&&pcm.size()<boundaries.back();++iteration) {
            const auto begin=cursor.snapshot().processedThrough;Facts buffer;
            const bool running=cursor.process(256,owner,collect,&buffer,stopAtCycle,nullptr);
            const auto end=cursor.snapshot().processedThrough;
            if(end<begin||end>boundaries.back()||(end==begin&&running))throw std::runtime_error("cursor made invalid progress");
            std::size_t index{};
            for(auto frame=begin;frame<end;++frame) {
                while(index<buffer.count&&buffer.values[index].frame==frame){
                    if(!renderer.accept(buffer.values[index++]))throw std::runtime_error("renderer rejected scheduled fact");
                    ++factCount;
                }
                float sample{};
                if(!renderer.sampleFrame(frame,sample))throw std::runtime_error("renderer rejected frame");
                pcm.push_back(sample);
            }
            while(index<buffer.count&&buffer.values[index].frame==end){
                if(!renderer.accept(buffer.values[index++]))throw std::runtime_error("renderer rejected boundary fact");
                ++factCount;
            }
            if(index!=buffer.count)throw std::runtime_error("fact outside processed frame range");
            if(!running){requestedStop=cursor.snapshot().reason==scheduler::StopReason::Requested;break;}
        }
        ck(requestedStop&&pcm.size()==boundaries.back()&&factCount==program.schedule().events().size()+1,
           "one complete cycle reaches exact requested stop with all schedule facts");
        bool finite=true,exact=true,eachNonzero=true,transitionExact=true;
        for(std::size_t i=0;i<known.size();++i){
            bool nonzero=false;const auto& voice=program.voices()[i];
            for(auto frame=boundaries[i];frame<boundaries[i+1];++frame){
                const auto expected=static_cast<float>(reference::sample(program.method(),voice.hz,
                    frame-boundaries[i],boundaries[i+1]-boundaries[i],rate)/6.0);
                finite=finite&&std::isfinite(pcm[frame]);exact=exact&&pcm[frame]==expected;
                nonzero=nonzero||pcm[frame]!=0.0f;
            }
            eachNonzero=eachNonzero&&nonzero;
            if(i>0){
                const auto frame=boundaries[i];
                const auto& old=program.voices()[i-1];
                const auto stale=static_cast<float>(reference::sample(program.method(),old.hz,
                    frame-boundaries[i-1],boundaries[i]-boundaries[i-1],rate)/6.0);
                transitionExact=transitionExact&&stale==0.0f&&
                    pcm[frame]==static_cast<float>(reference::sample(program.method(),voice.hz,0,
                        boundaries[i+1]-boundaries[i],rate)/6.0);
            }
        }
        ck(finite&&exact&&eachNonzero&&transitionExact,
           "all twenty note gates render finite exact PCM, with no stale sound across release/attack boundaries");
        float afterStop=1.0f;
        ck(!renderer.sampleFrame(boundaries.back(),afterStop)&&afterStop==0.0f,
           "completed cycle is silent beyond the final release/stop boundary");
        const auto l3Checks=checks;
        std::size_t rung05Frames{};
        std::size_t rung05Checks{},level20Checks{},level20Frames{};
        if(argc>=8) {
            std::vector<std::filesystem::path> extensionPaths;
            for(int argument=3;argument<argc;++argument)extensionPaths.emplace_back(argv[argument]);
            const auto installed=lesson::Catalog::loadInstalled(bundle,extensionPaths);
            constexpr const char* rungItem="fg:item:001145";
            constexpr const char* eventRef05="L12-TXT1-98-109";
            const std::array<const char*,2> rungVariants{{"fg:variant:007412","fg:variant:007413"}};
            const std::array<const char*,2> starts{{"D","U"}};
            for(std::size_t variantIndex=0;variantIndex<rungVariants.size();++variantIndex) {
                const auto* selectedVariant=rungVariants[variantIndex];
                const auto admission05=installed->admit(rungItem,selectedVariant);
                const auto& variant05=installed->variant(rungItem,selectedVariant);
                const auto model05=admission05->model();
                const auto& source05=model05->source();
                const auto& selected05=variant05.authored.object().at("event_ids").array();
                const auto prefix=std::string("Rung05 ")+starts[variantIndex]+"-start ";
                const std::vector<std::string> originalRefs05{
                    "L12-TXT1-98-109","L12-PDF1-p4","L12-PDF1-p2","L12-TXT1-1-40",
                    "L12-TXT1-224-227","L12-TXT1-229-231","L12-PDF1-p1"};
                ck(admission05->practiceAllowed()&&variant05.model==model05&&
                   admission05->span()==Rational{8}&&
                   source05.itemId==rungItem&&!source05.syntheticFixture&&
                   source05.sourceRefs==originalRefs05&&
                   source05.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&
                   source05.instrument.capo==0&&source05.measures.empty()&&
                   variant05.authored.object().at("pick_start").string()==starts[variantIndex],
                   prefix+"is the admitted full eight-quarter cell with exact setup and pick start");
                const auto& hashes05=admission05->identity().object().at("source_hashes").object();
                ck(hashes05.at("L12-TXT1-98-109").string()==
                       "64e65f5293012f9af3c84a885cbdd54c82275f6c6e282c8f8a28cca579631be9"&&
                   hashes05.at("L12-PDF1-p4").string()==
                       "ae31f029a3df324baa8822b913deb499eccc1438f1986967f96889e6eb45bd3b"&&
                   admission05->identity().object().at("content_version").string()==
                       "curriculum-v1-level012-rung05-local-build-only.1",
                   prefix+"runtime identity binds exact original TXT/PDF and admitted content version");
                ck(selected05.size()==rung05Known.size()&&source05.events.size()==rung05Known.size(),
                   prefix+"has all sixteen source-selected events");
                const auto document05=std::make_shared<const tab::Document>(model05);
                desktop::TabView tab05;tab05.setSize(920,680);tab05.setDocument(document05);
                desktop::FretboardView board05;board05.setSize(550,350);
                scheduler::Owner owner05;owner05.id[0]=43;owner05.id[6]=0x40;
                owner05.id[8]=0x80;owner05.generation=owner05.epoch=1;
                constexpr std::uint64_t binding05=2;
                const auto configuration05=admission05->referenceConfiguration(owner05,binding05,rate,bpm);
                admission05->validateReference(configuration05);
                const auto program05=reference::compile(model05,configuration05);
                ck(&program05.source()==model05.get()&&
                   program05.schedule().sourceBinding()==admission05->sourceBinding()&&
                   program05.voices().size()==rung05Known.size(),
                   prefix+"ReferenceAudio uses admitted source binding and sixteen voices");
                std::array<std::uint64_t,rung05Known.size()+1> edges{};
                const auto& scheduled=program05.schedule().events();
                for(std::size_t i=0;i<rung05Known.size();++i) {
                    const auto id=rung05IdFor(i), label=prefix+"event "+std::to_string(i+1)+" ";
                    const auto& expected=rung05Known[i];
                    const auto& event=source05.events[i];
                    ck(selected05[i].string()==id&&event.id==id&&event.sourceRef==eventRef05&&
                       event.kind==music::Kind::Note&&event.tones.size()==1&&
                       event.span==music::Span{Rational{static_cast<std::int64_t>(i),2},Rational{1,2}},
                       label+"retains original order, identity, source and even-eighth span");
                    const auto& tone=event.tones.front();
                    ck(tone.string==expected.string&&tone.fret==expected.fret&&
                       tone.midi==expected.midi&&tone.finger==expected.finger&&
                       tone.spelling==rung05Spelling[i]&&tone.attack==music::Attack::Picked&&
                       tone.tieFrom.empty()&&tone.degrees.size()==1&&
                       tone.degrees.front().ordinal==rung05Degree[i],
                       label+"matches source string/fret/pitch/spelling/finger/degree");
                    const auto* tabEvent=document05->event(id);
                    const auto detail=document05->detail(id);
                    ck(tab05.selectEvent(id)&&tab05.selectedEvent()==id&&tabEvent==&event&&
                       detail.find(id+"\nSource: "+eventRef05)!=std::string::npos&&
                       detail.find("String "+std::to_string(7-expected.string)+" (internal "+
                           std::to_string(expected.string)+"), fret "+std::to_string(expected.fret))!=std::string::npos&&
                       detail.find(std::string(rung05Spelling[i])+" (authored)")!=std::string::npos&&
                       detail.find("MIDI "+std::to_string(expected.midi))!=std::string::npos&&
                       detail.find("Fng: "+std::string(expected.finger))!=std::string::npos&&
                       detail.find("Deg: "+std::to_string(rung05Degree[i])+" [Db-major]")!=std::string::npos&&
                       detail.find("onset "+tab::fraction(Rational{static_cast<std::int64_t>(i),2})+
                           "; duration 1/2 quarter units")!=std::string::npos,
                       label+"TAB detail agrees with selected original event");
                    ck(board05.setEvent(model05,id)&&board05.selectedEventId()==id&&
                       board05.markers().size()==1,
                       label+"projects exactly one fretboard marker");
                    const auto& marker=board05.markers().front();
                    ck(marker.sourceId==rungItem&&marker.sourceRef==eventRef05&&
                       marker.eventId==id&&marker.internalString==expected.string&&
                       marker.displayString==7-expected.string&&
                       marker.relativeFret==expected.fret&&marker.physicalFret==expected.fret&&
                       marker.midi==expected.midi&&marker.finger==expected.finger,
                       label+"fretboard marker matches source tone");
                    const auto& voice=program05.voices()[i];
                    ck(voice.sourceEvents==std::vector<std::string>{id}&&
                       voice.string==expected.string&&voice.midi==expected.midi&&
                       voice.hz==reference::frequency(expected.midi)&&
                       voice.onset==Rational{static_cast<std::int64_t>(i),2}&&
                       voice.end==Rational{static_cast<std::int64_t>(i+1),2},
                       label+"owns exact ReferenceAudio pitch and gate");
                    scheduler::FrameRatio start05{},end05{};
                    ck(scheduler::samples(voice.onset,rate,bpm,scheduler::BeatUnit::Quarter,start05)&&
                       scheduler::samples(voice.end,rate,bpm,scheduler::BeatUnit::Quarter,end05)&&
                       voice.startFrames.n==start05.n&&voice.startFrames.d==start05.d&&
                       voice.endFrames.n==end05.n&&voice.endFrames.d==end05.d&&
                       scheduler::round(start05,edges[i])&&scheduler::round(end05,edges[i+1]),
                       label+"has exact rational frame plan");
                    const auto attack05=std::find_if(scheduled.begin(),scheduled.end(),[&](const auto& e){
                        return e.sourceEvent==i+1&&e.role==scheduler::Role::Reference&&
                            e.action==scheduler::Action::Attack;});
                    const auto release05=std::find_if(scheduled.begin(),scheduled.end(),[&](const auto& e){
                        return e.sourceEvent==i+1&&e.role==scheduler::Role::Reference&&
                            e.action==scheduler::Action::Release;});
                    ck(attack05!=scheduled.end()&&release05!=scheduled.end()&&
                       attack05->structural==voice.onset&&release05->structural==voice.end&&
                       attack05->offset.n==start05.n&&attack05->offset.d==start05.d&&
                       release05->offset.n==end05.n&&release05->offset.d==end05.d,
                       label+"scheduled Attack/Release agree with source time");
                }
                ck(edges.front()==0&&edges.back()==176400,
                   prefix+"eight-quarter cycle has 176400 software frames at selected 44.1 kHz/120 BPM");
                const auto foreign=installed->admit(rungItem,rungVariants[1-variantIndex]);
                bool refused=false;
                try { admission05->validateReference(foreign->referenceConfiguration(
                    owner05,binding05,rate,bpm)); } catch(const std::invalid_argument&) { refused=true; }
                ck(refused,prefix+"refuses a foreign D/U variant source binding");
                if(variantIndex==0) {
                    auto wrong=source05;wrong.events[7].tones.front().midi++;
                    ck(!music::validate(wrong).validReference(),
                       "Rung05 wrong octave-root pitch is refused before ReferenceAudio");
                    scheduler::Cursor cursor05;reference::Renderer renderer05;
                    ck(cursor05.start(program05.schedule(),owner05,binding05)&&renderer05.bind(program05),
                       "Rung05 software Cursor/Renderer bind selected D-start Program");
                    std::vector<float> pcm05;pcm05.reserve(edges.back());
                    std::size_t facts05{};bool stopped05=false;
                    for(std::size_t iteration=0;iteration<100000&&pcm05.size()<edges.back();++iteration) {
                        const auto begin=cursor05.snapshot().processedThrough;Facts buffer;
                        const bool running=cursor05.process(256,owner05,collect,&buffer,stopAtCycle,nullptr);
                        const auto end=cursor05.snapshot().processedThrough;
                        if(end<begin||end>edges.back()||(end==begin&&running))
                            throw std::runtime_error("Rung05 cursor made invalid progress");
                        std::size_t index{};
                        for(auto frame=begin;frame<end;++frame) {
                            while(index<buffer.count&&buffer.values[index].frame==frame) {
                                if(!renderer05.accept(buffer.values[index++]))
                                    throw std::runtime_error("Rung05 renderer rejected scheduled fact");
                                ++facts05;
                            }
                            float sample{};
                            if(!renderer05.sampleFrame(frame,sample))
                                throw std::runtime_error("Rung05 renderer rejected frame");
                            pcm05.push_back(sample);
                        }
                        while(index<buffer.count&&buffer.values[index].frame==end) {
                            if(!renderer05.accept(buffer.values[index++]))
                                throw std::runtime_error("Rung05 renderer rejected boundary fact");
                            ++facts05;
                        }
                        if(index!=buffer.count)throw std::runtime_error("Rung05 fact outside frame range");
                        if(!running) { stopped05=cursor05.snapshot().reason==scheduler::StopReason::Requested;break; }
                    }
                    ck(stopped05&&pcm05.size()==edges.back()&&
                       facts05==program05.schedule().events().size()+1,
                       "Rung05 complete software cycle stops with all scheduled facts");
                    bool finite05=true,exact05=true,nonzero05=true,transition05=true;
                    for(std::size_t i=0;i<rung05Known.size();++i) {
                        bool gateNonzero=false;const auto& voice=program05.voices()[i];
                        for(auto frame=edges[i];frame<edges[i+1];++frame) {
                            const auto expected=static_cast<float>(reference::sample(program05.method(),voice.hz,
                                frame-edges[i],edges[i+1]-edges[i],rate)/6.0);
                            finite05=finite05&&std::isfinite(pcm05[frame]);
                            exact05=exact05&&pcm05[frame]==expected;
                            gateNonzero=gateNonzero||pcm05[frame]!=0.0f;
                        }
                        nonzero05=nonzero05&&gateNonzero;
                        if(i>0) {
                            const auto frame=edges[i];const auto& old=program05.voices()[i-1];
                            const auto stale=static_cast<float>(reference::sample(program05.method(),old.hz,
                                frame-edges[i-1],edges[i]-edges[i-1],rate)/6.0);
                            transition05=transition05&&stale==0.0f&&
                                pcm05[frame]==static_cast<float>(reference::sample(program05.method(),voice.hz,0,
                                    edges[i+1]-edges[i],rate)/6.0);
                        }
                    }
                    ck(finite05&&exact05&&nonzero05&&transition05,
                       "Rung05 all sixteen picked gates render finite exact PCM without stale boundary sound");
                    float after05=1.0f;
                    ck(!renderer05.sampleFrame(edges.back(),after05)&&after05==0.0f,
                       "Rung05 software cycle is silent after final release/stop");
                    rung05Frames=pcm05.size();
                }
            }
            rung05Checks=checks-l3Checks;
            if(argc==21) {
                constexpr const char* level20Item="fg:item:001167";
                const std::array<const char*,2> level20Variants{{"fg:variant:007456","fg:variant:007457"}};
                const std::array<const char*,2> level20Starts{{"D","U"}};
                constexpr std::uint16_t level20Bpm=120; // deterministic user test choice, not authored tempo
                for(std::size_t variantIndex=0;variantIndex<level20Variants.size();++variantIndex) {
                    const auto* selectedVariant=level20Variants[variantIndex];
                    const auto admission20=installed->admit(level20Item,selectedVariant);
                    const auto& variant20=installed->variant(level20Item,selectedVariant);
                    const auto model20=admission20->model();
                    const auto& source20=model20->source();
                    const auto& selected20=variant20.authored.object().at("event_ids").array();
                    const auto prefix=std::string("Level20 ")+level20Starts[variantIndex]+"-start ";
                    ck(admission20->practiceAllowed()&&variant20.model==model20&&
                       source20.itemId==level20Item&&!source20.syntheticFixture&&
                       admission20->span()==Rational{322}&&source20.events.size()==322&&
                       selected20.size()==322&&source20.instrument.openMidi==std::vector<int>{40,45,50,55,59,64}&&
                       source20.instrument.capo==0&&source20.measures.empty()&&
                       variant20.authored.object().at("pick_start").string()==level20Starts[variantIndex],
                       prefix+"is exact admitted 322-quarter A-major learning circuit and source setup");
                    ck(admission20->identity().object().at("content_version").string()==
                           "curriculum-v1-level020-a-full-circuit-build-only.1"&&
                       std::find(source20.sourceRefs.begin(),source20.sourceRefs.end(),
                           "L20-TXT-A-MODULE1")!=source20.sourceRefs.end()&&
                       std::find(source20.sourceRefs.begin(),source20.sourceRefs.end(),
                           "L20-TXT-A-MODULE5")!=source20.sourceRefs.end(),
                       prefix+"binds admitted version and original first/final module references");
                    const auto document20=std::make_shared<const tab::Document>(model20);
                    desktop::TabView tab20;tab20.setSize(920,680);tab20.setDocument(document20);
                    desktop::FretboardView board20;board20.setSize(550,560);
                    scheduler::Owner owner20;owner20.id[0]=44;owner20.id[6]=0x40;
                    owner20.id[8]=0x80;owner20.generation=owner20.epoch=1;
                    constexpr std::uint64_t binding20=3;
                    const auto config20=admission20->referenceConfiguration(owner20,binding20,rate,level20Bpm);
                    admission20->validateReference(config20);
                    const auto program20=reference::compile(model20,config20);
                    ck(&program20.source()==model20.get()&&
                       program20.schedule().sourceBinding()==admission20->sourceBinding()&&
                       program20.voices().size()==322,
                       prefix+"ReferenceAudio uses identical admitted binding and 322 source voices");
                    const auto& scheduled20=program20.schedule().events();
                    const auto verifyContact=[&](const Level20Contact& expected) {
                        const auto i=expected.index;
                        const auto id=level20IdFor(i);
                        const auto label=prefix+"q"+std::to_string(i)+" ";
                        const auto& event=source20.events[i];
                        const auto ref=level20Ref(i);
                        ck(selected20[i].string()==id&&event.id==id&&event.sourceRef==ref&&
                           event.kind==music::Kind::Note&&event.tones.size()==1&&
                           event.span==music::Span{Rational{static_cast<std::int64_t>(i)},Rational{1}},
                           label+"keeps source identity, module and one-click quarter slot");
                        const auto& tone=event.tones.front();
                        ck(tone.string==expected.string&&tone.fret==expected.fret&&
                           tone.midi==expected.midi&&tone.finger==expected.finger&&
                           tone.spelling==expected.spelling&&tone.attack==music::Attack::Picked&&
                           tone.tieFrom.empty()&&tone.degrees.size()==1&&
                           tone.degrees.front().ordinal==expected.degree,
                           label+"agrees with original TAB string/fret/MIDI/finger/spelling/degree");
                        const auto* tabEvent=document20->event(id);
                        const auto detail=document20->detail(id);
                        ck(tab20.selectEvent(id)&&tab20.selectedEvent()==id&&tabEvent==&event&&
                           detail.find(id+"\nSource: "+ref)!=std::string::npos&&
                           detail.find("String "+std::to_string(7-expected.string)+" (internal "+
                               std::to_string(expected.string)+"), fret "+std::to_string(expected.fret))!=std::string::npos&&
                           detail.find(std::string(expected.spelling)+" (authored)")!=std::string::npos&&
                           detail.find("MIDI "+std::to_string(expected.midi))!=std::string::npos&&
                           detail.find("Fng: "+std::string(expected.finger))!=std::string::npos&&
                           detail.find("Deg: "+std::to_string(expected.degree)+" [A-major]")!=std::string::npos&&
                           detail.find("onset "+tab::fraction(Rational{static_cast<std::int64_t>(i)})+
                               "; duration 1 quarter units")!=std::string::npos,
                           label+"actual TAB detail agrees with selected source contact");
                        ck(board20.setEvent(model20,id)&&board20.selectedEventId()==id&&
                           board20.markers().size()==1,
                           label+"projects one visible fretboard contact");
                        const auto& marker=board20.markers().front();
                        ck(marker.sourceId==level20Item&&marker.sourceRef==ref&&marker.eventId==id&&
                           marker.internalString==expected.string&&marker.displayString==7-expected.string&&
                           marker.relativeFret==expected.fret&&marker.physicalFret==expected.fret&&
                           marker.midi==expected.midi&&marker.finger==expected.finger,
                           label+"actual fretboard marker agrees with original contact");
                        const auto& voice=program20.voices()[i];
                        ck(voice.sourceEvents==std::vector<std::string>{id}&&
                           voice.string==expected.string&&voice.midi==expected.midi&&
                           voice.hz==reference::frequency(expected.midi)&&
                           voice.onset==Rational{static_cast<std::int64_t>(i)}&&
                           voice.end==Rational{static_cast<std::int64_t>(i+1)},
                           label+"ReferenceAudio voice has exact source pitch and gate");
                        scheduler::FrameRatio start20{},end20{};
                        std::uint64_t startFrame{},endFrame{};
                        ck(scheduler::samples(voice.onset,rate,level20Bpm,scheduler::BeatUnit::Quarter,start20)&&
                           scheduler::samples(voice.end,rate,level20Bpm,scheduler::BeatUnit::Quarter,end20)&&
                           voice.startFrames.n==start20.n&&voice.startFrames.d==start20.d&&
                           voice.endFrames.n==end20.n&&voice.endFrames.d==end20.d&&
                           scheduler::round(start20,startFrame)&&scheduler::round(end20,endFrame)&&
                           startFrame==i*22050&&endFrame==(i+1)*22050,
                           label+"has exact 44.1 kHz/120 BPM software frame bounds");
                        const auto attack20=std::find_if(scheduled20.begin(),scheduled20.end(),[&](const auto& e){
                            return e.sourceEvent==i+1&&e.role==scheduler::Role::Reference&&
                                e.action==scheduler::Action::Attack;});
                        const auto release20=std::find_if(scheduled20.begin(),scheduled20.end(),[&](const auto& e){
                            return e.sourceEvent==i+1&&e.role==scheduler::Role::Reference&&
                                e.action==scheduler::Action::Release;});
                        ck(attack20!=scheduled20.end()&&release20!=scheduled20.end()&&
                           attack20->structural==voice.onset&&release20->structural==voice.end&&
                           attack20->offset.n==start20.n&&attack20->offset.d==start20.d&&
                           release20->offset.n==end20.n&&release20->offset.d==end20.d,
                           label+"scheduler Attack/Release preserves the exact source slot");
                    };
                    for(const auto& contact:level20Contacts)verifyContact(contact);
                    for(const auto& contact:level20Terminal)verifyContact(contact);
                    const auto foreign20=installed->admit(level20Item,level20Variants[1-variantIndex]);
                    bool refused20=false;
                    try { admission20->validateReference(foreign20->referenceConfiguration(
                        owner20,binding20,rate,level20Bpm)); } catch(const std::invalid_argument&) { refused20=true; }
                    ck(refused20,prefix+"refuses foreign D/U source binding before rendering");
                    if(variantIndex==0) {
                        auto wrongPitch=source20;wrongPitch.events[205].tones.front().midi++;
                        ck(!music::validate(wrongPitch).validReference(),
                           "Level20 wrong module4 third pitch is refused before ReferenceAudio");
                        auto wrongTime=source20;wrongTime.events[204].span.duration=Rational{};
                        ck(!music::validate(wrongTime).validReference(),
                           "Level20 zero-duration module4 root is refused before ReferenceAudio");
                        const auto picture=[&](const std::string& name,const juce::Image& image) {
                            juce::FileOutputStream stream{juce::File((out/(name+".png")).string())};
                            juce::PNGImageFormat png;
                            ck(stream.openedOk()&&png.writeImageToStream(image,stream),
                               "Level20 "+name+" actual component image written");
                            stream.flush();ck(!stream.getStatus().failed(),
                               "Level20 "+name+" actual image flushed");
                        };
                        const auto imagesDiffer=[](const juce::Image& a,const juce::Image& b) {
                            if(a.getWidth()!=b.getWidth()||a.getHeight()!=b.getHeight())return true;
                            for(int y=0;y<a.getHeight();++y)for(int x=0;x<a.getWidth();++x)
                                if(a.getPixelAt(x,y)!=b.getPixelAt(x,y))return true;
                            return false;
                        };
                        const auto rootId=level20IdFor(204),thirdId=level20IdFor(205);
                        ck(tab20.selectEvent(rootId)&&board20.setEvent(model20,rootId)&&
                           board20.getLocalBounds().contains(board20.markerBounds()),
                           "Level20 module4 root selected for actual rendering comparison");
                        const auto rootTab=tab20.createComponentSnapshot(tab20.getLocalBounds());
                        const auto rootBoard=board20.createComponentSnapshot(board20.getLocalBounds());
                        ck(tab20.selectEvent(thirdId)&&board20.setEvent(model20,thirdId)&&
                           board20.getLocalBounds().contains(board20.markerBounds()),
                           "Level20 module4 third selected for actual rendering comparison");
                        const auto thirdTab=tab20.createComponentSnapshot(tab20.getLocalBounds());
                        const auto thirdBoard=board20.createComponentSnapshot(board20.getLocalBounds());
                        ck(rootTab.isValid()&&thirdTab.isValid()&&rootBoard.isValid()&&thirdBoard.isValid()&&
                           imagesDiffer(rootTab,thirdTab)&&imagesDiffer(rootBoard,thirdBoard),
                           "Level20 actual TAB and fretboard pixels change with root-to-third selection");
                        picture("level20-q204-tab",rootTab);picture("level20-q204-fretboard",rootBoard);
                        picture("level20-q205-tab",thirdTab);picture("level20-q205-fretboard",thirdBoard);
                        scheduler::Cursor cursor20;reference::Renderer renderer20;
                        ck(cursor20.start(program20.schedule(),owner20,binding20)&&renderer20.bind(program20),
                           "Level20 software Cursor/Renderer bind selected D-start Program");
                        constexpr std::uint64_t terminalFrame=322*22050;
                        std::size_t facts20{};bool stopped20=false,finite20=true,exact20=true;
                        std::array<bool,322> nonzero20{};
                        for(std::size_t iteration=0;iteration<100000&&level20Frames<terminalFrame;++iteration) {
                            const auto begin=cursor20.snapshot().processedThrough;Facts buffer;
                            const bool running=cursor20.process(256,owner20,collect,&buffer,stopAtCycle,nullptr);
                            const auto end=cursor20.snapshot().processedThrough;
                            if(end<begin||end>terminalFrame||(end==begin&&running))
                                throw std::runtime_error("Level20 cursor made invalid progress");
                            std::size_t index{};
                            for(auto frame=begin;frame<end;++frame) {
                                while(index<buffer.count&&buffer.values[index].frame==frame) {
                                    if(!renderer20.accept(buffer.values[index++]))
                                        throw std::runtime_error("Level20 renderer rejected scheduled fact");
                                    ++facts20;
                                }
                                float sample{};
                                if(!renderer20.sampleFrame(frame,sample))
                                    throw std::runtime_error("Level20 renderer rejected frame");
                                const auto eventIndex=static_cast<std::size_t>(frame/22050);
                                const auto& voice=program20.voices()[eventIndex];
                                const auto expected=static_cast<float>(reference::sample(program20.method(),voice.hz,
                                    frame-eventIndex*22050,22050,rate)/6.0);
                                finite20=finite20&&std::isfinite(sample);
                                exact20=exact20&&sample==expected;
                                nonzero20[eventIndex]=nonzero20[eventIndex]||sample!=0.0f;
                                ++level20Frames;
                            }
                            while(index<buffer.count&&buffer.values[index].frame==end) {
                                if(!renderer20.accept(buffer.values[index++]))
                                    throw std::runtime_error("Level20 renderer rejected boundary fact");
                                ++facts20;
                            }
                            if(index!=buffer.count)throw std::runtime_error("Level20 fact outside frame range");
                            if(!running) { stopped20=cursor20.snapshot().reason==scheduler::StopReason::Requested;break; }
                        }
                        ck(stopped20&&level20Frames==terminalFrame&&
                           facts20==program20.schedule().events().size()+1,
                           "Level20 complete 322-quarter software cycle stops at q322 with all facts");
                        ck(finite20&&exact20&&
                           std::all_of(nonzero20.begin(),nonzero20.end(),[](bool value){return value;}),
                           "Level20 all 322 one-click gates render finite exact nonzero software PCM");
                        float after20=1.0f;
                        ck(!renderer20.sampleFrame(terminalFrame,after20)&&after20==0.0f,
                           "Level20 software cycle is silent after q322 final release/stop");
                    }
                }
                level20Checks=checks-l3Checks-rung05Checks;
            }
        }
        if(argc==3) {
            std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"events\":"<<known.size()
                <<",\"frames\":"<<pcm.size()<<",\"nativeOutput\":false,\"curriculumCredit\":false}\n";
            std::cout<<"PASS "<<l3Checks<<" L3 full-event projection checks; software PCM only\n";
        } else if(argc==8) {
            std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"events\":"<<known.size()
                <<",\"frames\":"<<pcm.size()<<",\"l3Checks\":"<<l3Checks
                <<",\"rung05Checks\":"<<rung05Checks<<",\"rung05Events\":"
                <<rung05Known.size()<<",\"rung05Frames\":"<<rung05Frames
                <<",\"nativeOutput\":false,\"curriculumCredit\":false}\n";
            std::cout<<"PASS "<<l3Checks<<" L3 checks, "<<rung05Checks
                      <<" Rung05 checks; software PCM only\n";
        } else {
            std::ofstream(out/"summary.json")<<"{\"checks\":"<<checks<<",\"events\":"<<known.size()
                <<",\"frames\":"<<pcm.size()<<",\"l3Checks\":"<<l3Checks
                <<",\"rung05Checks\":"<<rung05Checks<<",\"rung05Events\":"
                <<rung05Known.size()<<",\"rung05Frames\":"<<rung05Frames
                <<",\"level20Checks\":"<<level20Checks<<",\"level20Contacts\":"
                <<level20Contacts.size()+level20Terminal.size()<<",\"level20Frames\":"<<level20Frames
                <<",\"nativeOutput\":false,\"curriculumCredit\":false}\n";
            std::cout<<"PASS "<<l3Checks<<" L3 checks, "<<rung05Checks
                      <<" Rung05 checks, "<<level20Checks<<" Level20 checks; software PCM only\n";
        }
        return 0;
    }catch(const std::exception& ex){std::cerr<<"FAIL after "<<checks<<" checks: "<<ex.what()<<'\n';return 1;}
}
