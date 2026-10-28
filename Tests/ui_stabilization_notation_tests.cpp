#include "desktop/PracticeView.hpp"
#include "content/LessonCatalog.hpp"
#include "installed_catalog_fixture_access.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "read_only_text_peer_checks.hpp"
#include "storage/ProfileStore.hpp"
#include <CoreFoundation/CoreFoundation.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>

using namespace fathom;
namespace {
constexpr const char* item="fg:item:000001";
constexpr const char* variant="fg:variant:007478";
constexpr const char* extensionManifestSha="4626ab601fceb4c2727e866e7fd083c674994941d5853f13a812033f58121d65";
constexpr const char* packageSha="64c155482b5c3886de5a0669c661d3b38e4d0c9ce5dfa713bad362ffe4511082";
void pump(){CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);}
bool settle(const std::function<bool()>& state){
    auto marker=std::make_shared<bool>(false);
    if(!juce::MessageManager::callAsync([marker]{*marker=true;}))return false;
    const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(2);
    while(std::chrono::steady_clock::now()<deadline){pump();if(*marker&&state())return true;}
    return false;
}
storage::Reply confirmed(storage::ProfileStore::Future reply){
    if(reply.wait_for(std::chrono::seconds(6))!=std::future_status::ready)
        throw std::runtime_error("Synthetic Store response exceeded six-second watchdog");
    auto value=reply.get();
    if(value.status!=storage::Status::Confirmed)throw std::runtime_error(value.code+": "+value.message);
    return value;
}
juce::Viewport& viewport(desktop::TabView& tab){
    for(auto* child:tab.getChildren())if(auto* value=dynamic_cast<juce::Viewport*>(child))return *value;
    throw std::runtime_error("TAB viewport is absent");
}
juce::TextButton& resetButton(desktop::TabView& tab){
    for(auto* child:tab.getChildren())if(auto* button=dynamic_cast<juce::TextButton*>(child))
        if(button->getButtonText()=="Reset 100%")return *button;
    throw std::runtime_error("Notation Reset 100% is absent");
}
bool visibleWithin(const juce::Component& component,const juce::Component& root){
    for(auto* current=&component;current;current=current->getParentComponent()){
        if(!current->isVisible())return false;
        if(current==&root)return true;
    }
    return false;
}
void collectControls(juce::Component& root,juce::Component& node,std::vector<juce::Component*>& controls){
    if(&node!=&root&&!visibleWithin(node,root))return;
    if(dynamic_cast<juce::Button*>(&node)||dynamic_cast<juce::ComboBox*>(&node))controls.push_back(&node);
    for(auto* child:node.getChildren())collectControls(root,*child,controls);
}
std::string componentName(const juce::Component& component){
    if(auto* button=dynamic_cast<const juce::Button*>(&component))return button->getButtonText().toStdString();
    return component.getComponentID().toStdString();
}
enum class Ink{FretOrPicking,FingerOrString,Selection,StringLabel};
bool stringLabelInk(juce::Colour colour){
    // Read actual antialiased muted glyph coverage over the opaque background,
    // rather than requiring every connecting pixel to be nearly full ink.
    const double red=colour.getRed()-16.0,green=colour.getGreen()-33.0,blue=colour.getBlue()-44.0;
    const double coverage=(red*167.0+green*168.0+blue*166.0)/(167.0*167.0+168.0*168.0+166.0*166.0);
    // Exclude background/noise and other paint colours. Two channel steps allow
    // bounded 8-bit blend quantization; no row spacing or expected count is used.
    return coverage>=1.0/16.0&&coverage<=1.0&&std::abs(red-coverage*167.0)<=2.0
        &&std::abs(green-coverage*168.0)<=2.0&&std::abs(blue-coverage*166.0)<=2.0;
}
bool ink(juce::Colour colour,Ink kind){
    if(kind==Ink::StringLabel)return stringLabelInk(colour);
    const auto near=[](int a,int b){return std::abs(a-b)<=10;};
    if(kind==Ink::FretOrPicking)return colour.getRed()>=225&&colour.getGreen()>=225&&colour.getBlue()>=225;
    if(kind==Ink::FingerOrString)return near(colour.getRed(),183)&&near(colour.getGreen(),201)&&near(colour.getBlue(),210);
    return near(colour.getRed(),107)&&near(colour.getGreen(),213)&&near(colour.getBlue(),203);
}
// Discover the bounds of actual rasterized glyph bands; do not copy a string
// row stride, notation origin or font-height formula from production layout.
std::vector<juce::Rectangle<int>> bands(const juce::Image& image,int left,int right,Ink kind){
    std::vector<juce::Rectangle<int>> result;
    left=std::clamp(left,0,image.getWidth());right=std::clamp(right,0,image.getWidth());
    juce::Rectangle<int> active;
    for(int y=0;y<image.getHeight();++y){
        int first=right,last=-1;
        for(int x=left;x<right;++x)if(ink(image.getPixelAt(x,y),kind)){first=std::min(first,x);last=x;}
        if(last>=first){
            const juce::Rectangle<int> line{first,y,last-first+1,1};
            active=active.isEmpty()?line:active.getUnion(line);
        }else if(!active.isEmpty()){result.push_back(active);active={};}
    }
    if(!active.isEmpty())result.push_back(active);
    return result;
}
struct AccentRails {
    juce::Rectangle<int> allInk,border;
    std::vector<juce::Rectangle<int>> rails;
};
AccentRails selectedBorder(const juce::Image& image){
    AccentRails result;
    if(image.isNull())return result;
    const juce::Image::BitmapData pixels{image,juce::Image::BitmapData::readOnly};
    for(int x=0;x<image.getWidth();++x){
        int first=image.getHeight(),last=-1,start=-1,bestStart=0,bestLength=0;
        const auto finishRun=[&](int end){
            if(start>=0&&end-start>bestLength){bestStart=start;bestLength=end-start;}
            start=-1;
        };
        for(int y=0;y<image.getHeight();++y){
            if(ink(pixels.getPixelColour(x,y),Ink::Selection)){
                first=std::min(first,y);last=y;if(start<0)start=y;
            }else finishRun(y);
        }
        finishRun(image.getHeight());
        if(last>=first){const juce::Rectangle<int> column{x,first,1,last-first+1};
            result.allInk=result.allInk.isEmpty()?column:result.allInk.getUnion(column);
        }
        // The selected outline has two tall vertical rails; accent technique
        // glyphs are separate short runs. Measure rails rather than copying any
        // source origin, stride or font, or depending on rounded-corner joins.
        if(bestLength>image.getHeight()/2){
            const juce::Rectangle<int> rail{x,bestStart,1,bestLength};
            if(result.rails.empty()||result.rails.back().getRight()!=x)result.rails.push_back(rail);
            else result.rails.back()=result.rails.back().getUnion(rail);
        }
    }
    for(const auto& rail:result.rails)result.border=result.border.isEmpty()?rail:result.border.getUnion(rail);
    return result;
}
std::string fingerprint(const tab::Document& document){
    std::string bytes=document.overview();
    const auto rational=[](const std::optional<Rational>& value)->json::Value{
        if(!value)return nullptr;
        return json::Value::Array{json::Value::fromInteger(value->numerator()),json::Value::fromInteger(value->denominator())};
    };
    for(const auto& event:document.source().events){
        bytes+=document.detail(event.id);
        // Note details do not currently include handDirection. Preserve its
        // exact value and explicit span rather than relying on display prose.
        bytes+=storage::canonical(json::Value::Object{{"event_id",event.id},{"hand_direction",event.handDirection},
            {"onset_q",rational(event.span.onset)},{"duration_q",rational(event.span.duration)}});
    }
    return content::sha256(bytes);
}
std::string rectangle(const juce::Rectangle<int>& value){
    return std::to_string(value.getX())+","+std::to_string(value.getY())+","+
        std::to_string(value.getWidth())+","+std::to_string(value.getHeight());
}
}

int main(int argc,char** argv){
    int checks=0;std::ofstream trace,geometry;
    try{
        if(argc!=3)throw std::invalid_argument("Expected exact frozen Resources directory and new absolute output directory");
        const std::filesystem::path resources{argv[1]},output{argv[2]};
        if(!resources.is_absolute()||!output.is_absolute()||std::filesystem::exists(output))
            throw std::invalid_argument("Absolute resource path and absent absolute output directory required");
        std::filesystem::create_directories(output);
        std::filesystem::permissions(output,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
        trace.open(output/"checks.tsv");geometry.open(output/"geometry.tsv");
        geometry<<"view\twidth\theight\tzoom\tevent\tvisible_canvas\tfret\tfinger\tpicking\tselection_column\n";
        auto check=[&](bool okay,const std::string& label){++checks;trace<<(okay?"PASS":"FAIL")<<'\t'<<label<<'\n';trace.flush();if(!okay)throw std::runtime_error(label);};
        const auto extension=resources/"level001-extension";
        const auto manifestBytes=content::readBounded(extension/"manifest.json",1024*1024);
        check(content::sha256(manifestBytes)==extensionManifestSha,"actual audit Level1 manifest matches immutable SHA256 before entry lookup");
        const auto manifest=json::parse(manifestBytes);
        const auto packagePath=extension/manifest.object().at("entries").object().at("package").string();
        const auto packageBytes=content::readBounded(packagePath,16*1024*1024);
        check(content::sha256(packageBytes)==packageSha,"actual audit Level1 full-exercise package matches immutable SHA256");
        auto catalog=lesson::InstalledCatalogFixtureAccess::levelOneWithControls(resources);
        const auto admission=catalog->admit(item,variant);
        check(admission&&admission->practiceAllowed()&&admission->identity().object().at("package_sha256").string()==packageSha,
              "exact existing full48 quarter-pulse admission is retained without new permission");
        auto document=std::make_shared<const tab::Document>(admission->model());
        const auto originalFingerprint=fingerprint(*document);
        const auto originalIdentity=storage::canonical(admission->identity());
        const auto originalBinding=admission->sourceBinding();
        const auto& events=document->source().events;
        check(!document->source().syntheticFixture&&events.size()==48&&document->source().measures.empty()
              &&document->source().instrument.openMidi.size()==6,"actual selected source has48 events and six strings, with no synthetic substitute");
        check(std::all_of(events.begin(),events.end(),[](const auto& event){return event.tones.size()==1&&!event.handDirection.empty()&&!event.tones.front().finger.empty();}),
              "actual selected full48 includes authored finger and configured picking projections");
        const auto& record=catalog->lesson(item).record.object();
        const auto& authored=catalog->variant(item,variant).authored.object();
        const auto& grouping=authored.at("grouping").object();
        const json::Value one=json::Value::Array{json::Value::fromInteger(1),json::Value::fromInteger(1)};
        check(catalog->isInstalledExtension(item)&&authored.at("route").string()=="ascending_then_descending_full_printed_unit"
              &&authored.at("pick_start").string()=="D"&&authored.at("pick_start_origin").string()=="learner_configuration"
              &&grouping.at("kind").string()=="even_subdivision"&&grouping.at("beat_unit_q")==one
              &&grouping.at("marking_factor")==one&&grouping.at("notes_per_beat")==json::Value::fromInteger(1)
              &&authored.at("source_refs")==json::Value(json::Value::Array{"L1-TXT2-15","L1-FATHOM-FULL48-QUARTER-PULSE"})
              &&record.at("timing").object().at("status").string()=="unresolved",
              "exact variant binds the full printed route and learner D-start to Fathom quarter pulse while source timing stays unresolved");
        const auto& sourceEvents=record.at("events").array();
        const auto& routeEvents=authored.at("event_ids").array();
        bool exactRoute=sourceEvents.size()==48&&routeEvents.size()==48;
        for(std::size_t index=0;exactRoute&&index<events.size();++index){
            const auto& event=events[index];const auto& source=sourceEvents[index].object();
            exactRoute=event.id==routeEvents[index].string()&&event.id==source.at("event_id").string()
                &&source.at("onset_q").null()&&source.at("duration_q").null()
                &&event.span.onset==Rational{static_cast<std::int64_t>(index)}&&event.span.duration==Rational{1}
                &&event.handDirection==(index%2==0?"D":"U");
        }
        const auto pulse=admission->practiceConfiguration(44100,60);
        check(exactRoute&&document->allTimed()&&admission->span()==Rational{48}&&admission->sourceStart()==Rational{0}
              &&pulse.span==Rational{48}&&pulse.unit==scheduler::BeatUnit::Quarter,
              "all48 exact source IDs retain order and unresolved authored spans; admitted normalization alone supplies q0..47 duration1 and alternating D/U");
        for(const auto index:{0u,44u,45u,46u,47u})
            check(document->displayString(events.at(index).tones.front().string)==6,"actual event "+std::to_string(index+1)+" is display string6");
        juce::ScopedJuceInitialiser_GUI gui;
        const auto profile=output/"synthetic-profile";std::filesystem::create_directory(profile);
        std::filesystem::permissions(profile,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
        storage::StoreOptions options;options.path=profile/"profile.sqlite";options.create=true;options.createdUtc="2026-10-04T00:00:00Z";
        storage::ProfileStore store(options);
        const auto session=confirmed(store.createSession(storage::newUuid(),options.createdUtc,"America/New_York",{},json::Value::Object{{"synthetic_fixture",true},{"purpose","notation-geometry-only"}}));
        const auto before=confirmed(store.snapshot(storage::newUuid()));
        desktop::PracticeView practice;
        practice.setVisible(true);
        check(practice.configureCapture(store,session.owner,[]{return std::string{"2026-10-04T00:00:01Z"};},"America/New_York")
              &&practice.configureLesson(admission,60),"actual Practice configures retained admission in a fresh isolated synthetic Session without Start");
        practice.showTab(false);
        auto* authoredSource=dynamic_cast<juce::Label*>(practice.findChildWithID("practice-authored-source"));
        juce::TextEditor* authoredReader=nullptr;
        if(authoredSource)for(auto* child:authoredSource->getChildren())
            if(auto* editor=dynamic_cast<juce::TextEditor*>(child)){authoredReader=editor;break;}
        check(authoredSource&&authoredReader,
              "Practice authored source exposes one focusable read-only scrolling reader rather than a clipped display label");
        const auto authoredText=authoredSource->getText().toStdString();
        const std::string finalBoundary="Explicit Start begins one local Practice Attempt; Save result is required before a local record is finalized.";
        check(authoredText.rfind("AUTHORED SOURCE INSTRUCTIONS\n",0)==0
              &&authoredText.find(admission->description())!=std::string::npos
              &&authoredText.find("Source case: fg:item:000001 / fg:variant:007478")!=std::string::npos
              &&authoredText.find("Source references: L1-TXT2-15, L1-FATHOM-FULL48-QUARTER-PULSE")!=std::string::npos
              &&authoredText.size()>=finalBoundary.size()
              &&authoredText.compare(authoredText.size()-finalBoundary.size(),finalBoundary.size(),finalBoundary)==0,
              "Practice reader preserves the complete authored beginning, exact admission prose, provenance and final Start/Save boundary");
        {
            test::ReadingPeerScope peer{practice};
            for(const auto size:{juce::Point<int>{920,680},juce::Point<int>{1400,785}}){
                practice.setSize(size.x,size.y);practice.showTab(false);pump();
                authoredReader->grabKeyboardFocus();pump();
                const auto sizedCheck=[&](bool okay,const std::string& label){
                    check(okay,"Practice source reader "+std::to_string(size.x)+"x"+std::to_string(size.y)+": "+label);
                };
                test::readingKeys(practice,*authoredReader,authoredText,sizedCheck);
            }
        }
        check(storage::canonical(admission->identity())==originalIdentity&&fingerprint(*document)==originalFingerprint
              &&practice.captureSession()->phase()==capture::SessionPhase::Idle&&!practice.captureSession()->startTaken()
              &&practice.outputStatus().lifecycle.state==fathom::output::State::Closed,
              "Practice source reading preserves exact admission/source identity, Idle no-Start state and closed audio");
        desktop::TabView standalone;standalone.setVisible(true);standalone.setCompact(true);standalone.setDocument(document);
        auto controls=[&](juce::Component& root,const std::string& label){
            std::vector<juce::Component*> values;collectControls(root,root,values);
            bool contained=!values.empty(),separate=true;std::string outside,collision;
            for(auto* control:values){
                const auto bounds=root.getLocalArea(control,control->getLocalBounds());
                if(bounds.isEmpty()||!root.getLocalBounds().contains(bounds)){contained=false;if(outside.empty())outside=componentName(*control);}
            }
            for(std::size_t i=0;i<values.size();++i)for(std::size_t j=i+1;j<values.size();++j){
                const auto first=root.getLocalArea(values[i],values[i]->getLocalBounds());
                const auto second=root.getLocalArea(values[j],values[j]->getLocalBounds());
                if(first.intersects(second)){separate=false;if(collision.empty())collision=componentName(*values[i])+" / "+componentName(*values[j]);}
            }
            check(contained,label+" contains all visible controls"+(outside.empty()?"":": "+outside));
            check(separate,label+" keeps visible controls disjoint"+(collision.empty()?"":": "+collision));
        };
        auto inspect=[&](desktop::TabView& tab,const std::string& name,int width,int height,double zoom,std::size_t index){
            check(tab.setZoom(zoom)&&tab.selectEvent(events.at(index).id),name+" selects exact event "+std::to_string(index+1)+" at zoom "+std::to_string(zoom));
            auto& port=viewport(tab);auto* canvas=port.getViewedComponent();
            check(canvas&&port.isVisible()&&!tab.detailVisible()&&port.getMaximumVisibleWidth()>0&&port.getMaximumVisibleHeight()>0,name+" has a usable actual canvas viewport");
            const auto visible=port.getViewArea();
            // Only the selected visible columns and the label stripe are rasterized;
            // full48 content stays in one immutable Document, not a huge image archive.
            const auto columns=canvas->createComponentSnapshot({visible.getX(),0,visible.getWidth(),canvas->getHeight()});
            const auto accent=selectedBorder(columns);
            const auto selection=accent.border;
            // Preserve actual measurement before an assertion can abort the
            // fixture, so absent ink and clipped column edges are distinguishable.
            trace<<"METRIC\t"<<name<<" "<<width<<"x"<<height<<" zoom="<<zoom<<" event="<<index+1
                 <<" selected_id="<<tab.selectedEvent()<<" viewport="<<rectangle(port.getBounds())
                 <<" visible_before="<<rectangle(visible)<<" visible_after="<<rectangle(port.getViewArea())
                 <<" canvas_bounds="<<rectangle(canvas->getBounds())<<" canvas_local="<<rectangle(canvas->getLocalBounds())
                 <<" image="<<columns.getWidth()<<","<<columns.getHeight()<<" selection_image="<<rectangle(selection)
                 <<" selection_canvas="<<rectangle(selection.translated(visible.getX(),0))
                 <<" accent_union_image="<<rectangle(accent.allInk)<<" selection_rail_bands="<<accent.rails.size()
                 <<" selection_empty="<<(selection.isEmpty()?"true":"false")<<'\n';
            trace.flush();
            check(accent.rails.size()==2,name+" raster independently identifies both selected-column border rails rather than accent technique glyphs");
            check(!selection.isEmpty()&&selection.getX()>0&&selection.getRight()<columns.getWidth(),name+" reveals both horizontal edges of selected event column");
            const auto white=bands(columns,selection.getX()+4,selection.getRight()-4,Ink::FretOrPicking);
            const auto grey=bands(columns,selection.getX()+4,selection.getRight()-4,Ink::FingerOrString);
            check(white.size()>=2&&grey.size()>=2,name+" raster retains separate picking, fret and finger glyph bands");
            const auto picking=white.front(),fret=white.back(),finger=grey.back();
            const juce::Rectangle<int> vertical{0,visible.getY(),columns.getWidth(),visible.getHeight()};
            check(vertical.contains(fret)&&vertical.contains(finger),name+" selected string6 fret and finger glyphs fit vertically without clipping");
            if(zoom<=1.0)check(vertical.contains(picking),name+" default/reduced zoom also exposes configured picking glyphs");
            else{
                tab.restoreScrollPosition({visible.getX(),0});
                check(port.getViewArea().getY()<=picking.getY()&&port.getViewArea().getBottom()>=picking.getBottom(),name+" high-zoom picking remains reachable by vertical scrolling");
                check(tab.selectedEvent()==events.at(index).id&&tab.selectEvent(events.at(index).id),name+" high-zoom scrolling retains exact selection and re-reveals lower-string glyphs");
                const auto revealed=port.getViewArea();
                check(revealed.contains(fret.translated(visible.getX(),0))&&revealed.contains(finger.translated(visible.getX(),0)),
                      name+" high-zoom reselect actually reveals measured string6 fret and finger glyph bands in both axes");
            }
            if(zoom==1.0&&index==0){
                check(port.getViewPositionX()==0,name+" initial default column keeps string-label margin reachable");
                const int gutterRight=visible.getX()+selection.getX();
                check(gutterRight>0,name+" default string-label gutter is measured from first selected-column edge");
                const auto stripe=canvas->createComponentSnapshot({0,0,gutterRight,canvas->getHeight()});
                const auto labels=bands(stripe,0,stripe.getWidth(),Ink::StringLabel);
                trace<<"METRIC\t"<<name<<" string_labels count="<<labels.size()<<" stripe="<<stripe.getWidth()<<","<<stripe.getHeight()
                     <<" visible="<<rectangle(port.getViewArea())<<" bands=";
                for(const auto& glyph:labels)trace<<"["<<rectangle(glyph)<<"]";
                trace<<'\n';trace.flush();
                if(labels.size()!=6){
                    bool saved=false;
                    // The fixture aborts on this unchanged count assertion, so
                    // at most one tiny failure image is kept, never every case.
                    if(stripe.getWidth()<=64&&stripe.getHeight()<=600){
                        const auto path=(output/"failure-label-stripe.png").string();
                        const juce::File file{juce::String::fromUTF8(path.c_str())};
                        auto stream=file.createOutputStream();juce::PNGImageFormat encoder;
                        saved=stream&&encoder.writeImageToStream(stripe,*stream);if(stream)stream->flush();
                    }
                    trace<<"METRIC\tlabel_failure_png_saved="<<(saved?"true":"false")
                         <<" max_dimensions=64,600 path=failure-label-stripe.png\n";trace.flush();
                }
                check(labels.size()==6,name+" raster contains all six distinct string-label glyph bands");
                for(const auto& glyph:labels)check(port.getViewArea().contains(glyph),name+" all six string labels fit simultaneously at default100%");
            }
            check(tab.visibleDetail().find(events.at(index).id)!=std::string::npos&&tab.document()->source().events.size()==48,name+" details and source event extent retain exact selected identity");
            geometry<<name<<'\t'<<width<<'\t'<<height<<'\t'<<zoom<<'\t'<<index+1<<'\t'<<rectangle(visible)
                    <<'\t'<<rectangle(fret)<<'\t'<<rectangle(finger)<<'\t'<<rectangle(picking)<<'\t'<<rectangle(selection)<<'\n';
            geometry.flush();
        };
        for(const auto size:{juce::Point<int>{921,680},juce::Point<int>{1400,680},juce::Point<int>{1400,928}}){
            standalone.setSize(size.x,size.y);practice.setSize(size.x,size.y);practice.showTab(true);
            for(auto pair:{std::pair<desktop::TabView*,std::string>{&standalone,"TAB"},{&practice.tabView(),"Practice"}}){
                auto& tab=*pair.first;
                const auto overlays=tab.overlays();
                check(overlays.fingers&&overlays.picking&&!overlays.notes&&!overlays.degrees,pair.second+" defaults preserve finger/picking on, optional names/degrees off");
                tab.showSource();tab.showDetail(false);tab.setZoom(1.0);tab.restoreScrollPosition({0,0});
                controls(pair.second=="TAB"?static_cast<juce::Component&>(standalone):static_cast<juce::Component&>(practice),pair.second+" "+std::to_string(size.x)+"x"+std::to_string(size.y));
                for(const auto zoom:{1.0,0.75,2.0})for(const auto index:{0u,44u,45u,46u,47u})inspect(tab,pair.second,size.x,size.y,zoom,index);
                const auto selected=tab.selectedEvent();resetButton(tab).triggerClick();
                check(settle([&]{return tab.zoom()==1.0;}),pair.second+" actual Reset100% action settles at default zoom");
                check(tab.selectedEvent()==selected&&tab.document()->source().events.size()==48,pair.second+" Reset100% preserves selected source and event count");
                if(pair.second=="Practice")check(fingerprint(*tab.document())==originalFingerprint,"Practice projected source/frets/fingers/timing/order remain identical after resizing/zoom/selection");
            }
        }
        check(fingerprint(*document)==originalFingerprint&&storage::canonical(admission->identity())==originalIdentity
              &&admission->sourceBinding()==originalBinding,"immutable source/admission/binding fingerprints including exact handDirection and spans remain identical before and after all display actions");
        const auto after=confirmed(store.snapshot(storage::newUuid()));
        check(before.data.find("authoritative")&&after.data.find("authoritative")&&*before.data.find("authoritative")==*after.data.find("authoritative"),"notation actions create no Attempt, performance report or learner credit");
        check(practice.outputStatus().lifecycle.state==fathom::output::State::Closed&&practice.outputStatus().callbacks==0
              &&practice.captureSession()->phase()==capture::SessionPhase::Idle,"audio stays Closed with zero callbacks and no started Practice capture");
        confirmed(store.closeSession(storage::newUuid(),session.owner,"2026-10-04T00:00:02Z","cancelled"));
        std::ofstream summary(output/"summary.json");
        summary<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"sourceEventCount\":48,\"selectedVariant\":\""<<variant
               <<"\",\"packageSha256\":\""<<packageSha<<"\",\"sourceFingerprint\":\""<<originalFingerprint
               <<"\",\"sizes\":[[921,680],[1400,680],[1400,928]],\"zooms\":[1,0.75,2],\"profile\":\"isolated synthetic only\",\"audioOpened\":false,\"practiceStarted\":false,\"actualListeningOrPerformanceClaimed\":false}\n";
        summary.flush();if(!summary.good()||!geometry.good()||!trace.good())throw std::runtime_error("Could not save bounded notation QA evidence");
        std::cout<<"PASS "<<checks<<" actual48 Level1 notation checks; audio Closed, no Practice start or learner credit\n";return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL "<<error.what()<<'\n';return 1;}
}
