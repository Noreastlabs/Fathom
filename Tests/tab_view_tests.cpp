#include "desktop/TabView.hpp"
#include "reference_audio_fixtures.hpp"
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <chrono>

int main(int argc,char** argv){
    using namespace fathom;int checks=0;
    const auto check=[&](bool pass,const std::string& what){++checks;if(!pass)throw std::runtime_error(what);};
    try{
        const bool stackedQueue=argc==3&&std::string(argv[2])=="--stacked-queue";const bool headingUtf8=argc==3&&std::string(argv[2])=="--heading-utf8";const bool keyboardFocus=argc==3&&std::string(argv[2])=="--keyboard-focus";const bool actionKeys=argc==3&&std::string(argv[2])=="--action-keys";const bool zoomRange=argc==3&&std::string(argv[2])=="--zoom-range";if(argc!=2&&!headingUtf8&&!keyboardFocus&&!actionKeys&&!zoomRange&&!stackedQueue)throw std::invalid_argument("Expected new output directory and optional focused mode");auto out=std::filesystem::path(argv[1]);if(std::filesystem::exists(out))throw std::invalid_argument("Output already exists");std::filesystem::create_directories(out);
        juce::ScopedJuceInitialiser_GUI gui;desktop::TabView view;auto models=controlExamples();
        bool actionPresentation=true;int styledActions=0;for(const auto* label:{"Detail","Zoom -","Zoom +","Reset 100%","Source / instructions"}){bool found=false;for(auto* child:view.getChildren())if(auto* button=dynamic_cast<juce::TextButton*>(child);button&&button->getButtonText().toStdString()==label){found=true;actionPresentation=actionPresentation&&button->findColour(juce::TextButton::buttonColourId)==juce::Colour{0xff6bd5cb}&&button->findColour(juce::TextButton::textColourOffId)==juce::Colour{0xff10212c}&&button->findColour(juce::TextButton::textColourOnId)==juce::Colour{0xff10212c};++styledActions;break;}actionPresentation=actionPresentation&&found;}
        check(actionPresentation&&styledActions==5,"TAB action buttons use the primary presentation while preserving the existing authored contract");
        const auto picture=[&](const std::string& name){auto image=view.createComponentSnapshot(view.getLocalBounds());juce::File file(juce::String::fromUTF8((out/(name+".png")).c_str()));auto stream=file.createOutputStream();juce::PNGImageFormat png;check(stream && png.writeImageToStream(image,*stream),"snapshot "+name);};
        if(stackedQueue){
            const auto active=std::make_shared<const tab::Document>(reference_fixtures::checked(models[2]));
            const auto future=std::make_shared<const tab::Document>(reference_fixtures::checked(models[5]));
            const auto originalActive=active->overview(),originalFuture=future->overview();
            desktop::TabView stacked;stacked.setSize(640,420);stacked.setDocument(active);
            juce::Viewport* port=nullptr;for(auto* child:stacked.getChildren())if(auto* candidate=dynamic_cast<juce::Viewport*>(child))port=candidate;
            check(port&&port->getViewedComponent(),"shared viewport exists");auto* canvas=port->getViewedComponent();
            
            const auto singleHeight=canvas->getHeight();
            const auto event=active->source().events.back().id;check(stacked.selectEvent(event)&&stacked.setPlayback({event},"Synthetic component playback position"),"active position initialized");
            const auto position=stacked.scrollPosition();const auto detail=stacked.visibleDetail();
            stacked.setUpcomingDocuments({future,active});
            check(stacked.upcomingDocuments()==std::vector<std::shared_ptr<const tab::Document>>{future,active}&&stacked.document()==active,"all immutable future documents retained in order");
            check(stacked.selectedEvent()==event&&stacked.playingEvents()==std::vector<std::string>{event}&&stacked.visibleDetail()==detail&&stacked.scrollPosition()==position,"future append preserves active selection, detail, playback and scroll");
            check(canvas->getHeight()>singleHeight*2,"complete future notation adds vertical extent, not title-only rows");
            const auto before=canvas->createComponentSnapshot(canvas->getLocalBounds());
            check(stacked.selectEvent(active->source().events.front().id)&&stacked.setPlayback({active->source().events.front().id},"Changed synthetic position"),"active position changes");
            const auto after=canvas->createComponentSnapshot(canvas->getLocalBounds());
            int futureChanges=0;for(int y=singleHeight+60;y<before.getHeight();++y)for(int x=0;x<before.getWidth();++x)if(before.getPixelAt(x,y)!=after.getPixelAt(x,y))++futureChanges;
            check(futureChanges==0,"future panels with colliding active event IDs never receive selection or playback highlights");
            check(stacked.selectEvent(event)&&stacked.setPlayback({event},"Retained active last event"),"active last event retained before future hit test");
            const auto selected=stacked.selectedEvent();const juce::Point<float> point{80.0f,static_cast<float>(canvas->getHeight()-100)};const auto now=juce::Time::getCurrentTime();
            canvas->mouseDown(juce::MouseEvent{juce::Desktop::getInstance().getMainMouseSource(),point,juce::ModifierKeys{},1,0,0,0,0,canvas,canvas,now,point,now,1,false});
            check(stacked.selectedEvent()==selected,"future vertical hit cannot select an active event");
            check(stacked.setZoom(0.5)&&stacked.selectedEvent()==selected&&stacked.playingEvents()==std::vector<std::string>{selected},"shared zoom retains active state");stacked.setZoom(1);
            stacked.restoreScrollPosition({canvas->getWidth(),canvas->getHeight()});check(stacked.scrollPosition().y>0,"tiny viewport reaches final upcoming panel through shared scroll");
            const auto save=[&](const std::string& name){auto image=canvas->createComponentSnapshot(canvas->getLocalBounds());auto stream=juce::File{juce::String::fromUTF8((out/name).c_str())}.createOutputStream();juce::PNGImageFormat png;check(stream&&png.writeImageToStream(image,*stream),"saved complete stacked render");};save("stacked-shared-columns-alpha.png");
            for(const auto size:{juce::Point<int>{920,680},juce::Point<int>{1400,1000}}){stacked.setSize(size.x,size.y);stacked.restoreScrollPosition({0,0});auto image=stacked.createComponentSnapshot(stacked.getLocalBounds());auto stream=juce::File{juce::String::fromUTF8((out/(std::to_string(size.x)+"x"+std::to_string(size.y)+"-stacked-viewport.png")).c_str())}.createOutputStream();juce::PNGImageFormat png;check(stream&&png.writeImageToStream(image,*stream),"saved ordinary min/max viewport stack");}
            stacked.setSize(640,420);
            stacked.setUpcomingDocuments(std::vector<std::shared_ptr<const tab::Document>>(33,future));check(stacked.document()==active&&stacked.selectedEvent()==selected&&canvas->getHeight()<singleHeight+100,"oversized future stack preserves visible active TAB with bounded notice");
            const juce::Point<float> noticePoint{80.0f,static_cast<float>(canvas->getHeight()-10)};
            canvas->mouseDown(juce::MouseEvent{juce::Desktop::getInstance().getMainMouseSource(),noticePoint,juce::ModifierKeys{},1,0,0,0,0,canvas,canvas,now,noticePoint,now,1,false});
            check(stacked.selectedEvent()==selected,"future budget notice cannot select an active event");
            stacked.setDocument(future);check(stacked.document()==future&&stacked.upcomingDocuments().empty()&&stacked.playingEvents().empty()&&stacked.selectedEvent().empty(),"advancement clears future presentation and prior active state");
            check(active->overview()==originalActive&&future->overview()==originalFuture,"all original source records remain unchanged");
            std::cout<<"PASS "<<checks<<" stacked TAB component checks (not native or physical legibility)\n";return 0;
        }
        if(zoomRange){
            // This six-string/48-event fixture tests the zoom component contract;
            // the existing actual-source notation regression retains its own gate.
            auto model=reference_fixtures::synthetic("zoom-range-six-strings-48-events");
            model.preservedRecordJson=R"({"fixture":"Synthetic six-string zoom regression; no learner credit"})";
            for(int index=0;index<48;++index){const int string=index/8+1,fret=index%4+5;auto event=reference_fixtures::note("synthetic:zoom:event:"+std::to_string(index+1),Rational{index},Rational{1},string,fret,model.instrument.openMidi.at(static_cast<std::size_t>(string-1))+fret);event.handDirection=index%2==0?"D":"U";event.tones.front().finger=std::to_string(index%4+1);model.events.push_back(std::move(event));}
            const auto source=std::make_shared<const tab::Document>(reference_fixtures::checked(model));
            const auto last=source->source().events.back().id,first=source->source().events.front().id;
            const auto sourceBytes=[&]{auto bytes=source->overview();for(const auto& event:source->source().events)bytes+=source->detail(event.id);return bytes;};
            const auto originalSource=sourceBytes();
            std::ofstream trace(out/"zoom-range.tsv");trace<<"width\tphase\tzoom\tselected_event\tscroll_x\tscroll_y\n";
            for(const int width:{640,920}){
                desktop::TabView zoomView;zoomView.setCompact(width==640);zoomView.setSize(width,680);zoomView.setDocument(source);
                juce::Viewport* port=nullptr;juce::Label* percentage=nullptr;juce::TextButton *smaller=nullptr,*larger=nullptr,*reset=nullptr;
                for(auto* child:zoomView.getChildren()){
                    if(auto* candidate=dynamic_cast<juce::Viewport*>(child))port=candidate;
                    if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->getTitle()=="Notation zoom percentage")percentage=label;
                    if(auto* button=dynamic_cast<juce::TextButton*>(child)){if(button->getButtonText()=="Zoom -")smaller=button;else if(button->getButtonText()=="Zoom +")larger=button;else if(button->getButtonText()=="Reset 100%")reset=button;}
                }
                const auto prefix=std::to_string(width)+"px ";
                check(port&&port->getViewedComponent()&&percentage&&smaller&&larger&&reset,prefix+"zoom controls and authored canvas are present");
                auto* canvas=port->getViewedComponent();
                const auto record=[&](const std::string& phase){trace<<width<<'\t'<<phase<<'\t'<<zoomView.zoom()<<'\t'<<zoomView.selectedEvent()<<'\t'<<port->getViewPositionX()<<'\t'<<port->getViewPositionY()<<'\n';};
                const auto preserved=[&](const std::string& phase){check(zoomView.document()==source&&zoomView.selectedEvent()==last&&zoomView.visibleDetail()==source->detail(last),prefix+phase+" retains exact final event, immutable source and complete detail");check(port->getViewPositionX()>=0&&port->getViewPositionY()>=0&&port->getViewArea().getRight()<=canvas->getWidth()&&port->getViewArea().getBottom()<=canvas->getHeight(),prefix+phase+" keeps a valid scrollable canvas extent");record(phase);};
                check(zoomView.zoom()==1.0&&percentage->getText()=="100%"&&!reset->isEnabled(),prefix+"default remains100% with Reset disabled");
                check(zoomView.selectEvent(last),prefix+"final six-string event selected");
                const auto detail=zoomView.visibleDetail();const auto position=zoomView.scrollPosition();
                for(const auto invalid:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity(),0.0,-1.0,std::nextafter(0.10,0.0),std::nextafter(2.0,3.0)}){
                    check(!zoomView.setZoom(invalid)&&zoomView.zoom()==1.0&&zoomView.selectedEvent()==last&&zoomView.visibleDetail()==detail&&zoomView.scrollPosition()==position,prefix+"invalid zoom refuses without changing presentation or source selection");
                }
                for(const auto expected:{0.75,0.50,0.25,0.10}){check(smaller->isEnabled(),prefix+"decrease remains reachable above10%");smaller->onClick();check(zoomView.zoom()==expected&&percentage->getText()==juce::String(static_cast<int>(std::lround(expected*100)))+"%",prefix+"decrease visits the intended stop");preserved("decrease");}
                check(!smaller->isEnabled()&&larger->isEnabled()&&reset->isEnabled(),prefix+"10% boundary disables only decrease");
                for(const auto expected:{0.25,0.50,0.75,1.0,1.25,1.50,1.75,2.0}){check(larger->isEnabled(),prefix+"increase remains reachable below200%");larger->onClick();check(zoomView.zoom()==expected,prefix+"increase visits the intended stop");preserved("increase");}
                check(smaller->isEnabled()&&!larger->isEnabled()&&reset->isEnabled(),prefix+"200% remains the upper boundary");
                for(const auto value:{0.11,0.249,0.62,1.13,1.99}){check(zoomView.setZoom(value)&&zoomView.zoom()==value,prefix+"direct set accepts an in-range scale without quantizing it");preserved("direct-scale");}
                check(zoomView.setZoom(0.11),prefix+"off-stop low scale accepted");smaller->onClick();check(zoomView.zoom()==0.10,prefix+"decrease from an off-stop low scale reaches10%");
                check(zoomView.setZoom(0.62),prefix+"off-stop middle scale accepted");larger->onClick();check(zoomView.zoom()==0.75,prefix+"increase from an off-stop scale selects next larger stop");smaller->onClick();check(zoomView.zoom()==0.50,prefix+"decrease from75% reaches50%");
                for(const auto value:{0.10,1.0,2.0}){
                    check(zoomView.setZoom(value),prefix+"edge/default scale accepted");preserved("edge-render");
                    const auto visible=port->getViewArea();const auto selectedImage=canvas->createComponentSnapshot(visible);
                    zoomView.showSource();check(zoomView.selectedEvent().empty()&&zoomView.visibleDetail().find(model.preservedRecordJson)!=std::string::npos,prefix+"complete synthetic source remains reachable at edge zoom");
                    const auto sourceImage=canvas->createComponentSnapshot(visible);int changedPixels=0;
                    for(int y=0;y<selectedImage.getHeight();++y)for(int x=0;x<selectedImage.getWidth();++x)if(selectedImage.getPixelAt(x,y)!=sourceImage.getPixelAt(x,y))++changedPixels;
                    check(changedPixels>0,prefix+"final selected-column highlight is actually visible at edge/default zoom");
                    check(zoomView.selectEvent(last),prefix+"source route can reselect final event");
                    check(reset->isEnabled()==(value!=1.0),prefix+"Reset availability tracks default scale");if(reset->isEnabled())reset->onClick();
                    check(zoomView.zoom()==1.0&&percentage->getText()=="100%"&&!reset->isEnabled(),prefix+"Reset action returns exactly100%");preserved("reset");
                }
                check(zoomView.setZoom(0.10)&&zoomView.selectEvent(first)&&zoomView.keyPressed(juce::KeyPress{juce::KeyPress::rightKey})&&zoomView.selectedEvent()==source->source().events.at(1).id,prefix+"reduced scale preserves source-order Right navigation");
                check(zoomView.selectEvent(last)&&zoomView.keyPressed(juce::KeyPress{juce::KeyPress::rightKey})&&zoomView.selectedEvent()==last,prefix+"reduced scale Right boundary retains final event");
                check(zoomView.keyPressed(juce::KeyPress{juce::KeyPress::leftKey})&&zoomView.selectedEvent()==source->source().events.at(46).id,prefix+"reduced scale Left navigation remains reachable");
                check(sourceBytes()==originalSource,prefix+"zoom/navigation never changes source identity, wording, tones or event order");
            }
            trace.flush();check(trace.good(),"zoom-range trace flushed");
            juce::DynamicObject::Ptr report=new juce::DynamicObject;report->setProperty("checks",checks);report->setProperty("failures",0);report->setProperty("status","PASS");report->setProperty("minimumPercent",10);report->setProperty("maximumPercent",200);report->setProperty("sourceEventCount",48);report->setProperty("sourceFixture","synthetic six-string component regression");report->setProperty("nativeKeyEvent",false);report->setProperty("physicalReadability",false);report->setProperty("audioRun",false);juce::File(juce::String::fromUTF8((out/"checks.json").c_str())).replaceWithText(juce::JSON::toString(juce::var(report.get())));std::cout<<"PASS "<<checks<<" TAB zoom-range component checks\n";return 0;
        }
        if(actionKeys){
            const auto source=std::make_shared<const tab::Document>(reference_fixtures::checked(models[5]));
            std::ofstream trace(out/"action-keys.tsv");trace<<"width\tcontrol\tkey\tzoom\tdetail_visible\tselected_event\n";
            for(const int width:{640,920}){
                desktop::TabView focusedView;focusedView.setCompact(width==640);focusedView.setSize(width,680);focusedView.setDocument(source);focusedView.addToDesktop(juce::ComponentPeer::windowHasTitleBar);focusedView.setVisible(true);
                auto* peer=focusedView.getPeer();check(peer&&focusedView.isShowing(),std::to_string(width)+"px visible TAB peer");
                const auto button=[&](const std::string& label){for(auto* child:focusedView.getChildren())if(auto* b=dynamic_cast<juce::TextButton*>(child);b&&b->getButtonText().toStdString()==label)return b;return static_cast<juce::TextButton*>(nullptr);};
                const auto press=[&](const std::string& label,int key){auto* b=button(label);check(b&&b->isShowing()&&b->isEnabled(),std::to_string(width)+"px visible enabled "+label);b->grabKeyboardFocus();check(juce::Component::getCurrentlyFocusedComponent()==b,std::to_string(width)+"px focused "+label);check(peer->handleKeyPress(juce::KeyPress{key}),std::to_string(width)+"px "+label+" key consumed");trace<<width<<'\t'<<label<<'\t'<<(key==juce::KeyPress::spaceKey?"Space":"Return")<<'\t'<<focusedView.zoom()<<'\t'<<focusedView.detailVisible()<<'\t'<<focusedView.selectedEvent()<<'\n';};
                press("Zoom +",juce::KeyPress::spaceKey);check(focusedView.zoom()==1.25,std::to_string(width)+"px Zoom + Space increases zoom once");
                press("Zoom -",juce::KeyPress::returnKey);check(focusedView.zoom()==1.0,std::to_string(width)+"px Zoom - Return decreases zoom once");
                check(focusedView.selectEvent(source->source().events.front().id),std::to_string(width)+"px event selected before Source");
                press("Source / instructions",juce::KeyPress::spaceKey);check(focusedView.selectedEvent().empty()&&focusedView.visibleDetail().find("Preserved authored")!=std::string::npos,std::to_string(width)+"px Source Space reveals preserved authored record");
                if(width==640){check(focusedView.detailVisible(),"640px Source opens compact detail");press("TAB",juce::KeyPress::returnKey);check(!focusedView.detailVisible(),"640px TAB Return restores authored canvas");}
                auto image=focusedView.createComponentSnapshot(focusedView.getLocalBounds());juce::File file(juce::String::fromUTF8((out/(width==640?"action-keys-compact-640.png":"action-keys-standard-920.png")).c_str()));auto stream=file.createOutputStream();juce::PNGImageFormat png;check(stream&&png.writeImageToStream(image,*stream),std::to_string(width)+"px TAB action render");
                focusedView.removeFromDesktop();
            }
            trace.flush();check(trace.good(),"TAB action trace flushed");
            juce::DynamicObject::Ptr report=new juce::DynamicObject;report->setProperty("checks",checks);report->setProperty("status","PASS");report->setProperty("nativeKeyEvent",false);report->setProperty("physicalKeyboard",false);report->setProperty("audioRun",false);juce::File(juce::String::fromUTF8((out/"checks.json").c_str())).replaceWithText(juce::JSON::toString(juce::var(report.get())));std::cout<<"PASS "<<checks<<" TAB action keyboard checks\n";return 0;
        }
        if(keyboardFocus){
            const auto source=std::make_shared<const tab::Document>(reference_fixtures::checked(models[5]));const auto& events=source->source().events;
            check(events.size()>=3,"selected source fixture has enough events for keyboard traversal");
            std::ofstream trace(out/"keyboard-focus.tsv");trace<<"width\tfocus\tkey\tselected_event\tscroll_x\tviewport_width\tcanvas_width\n";
            const auto eventAt=[&](std::size_t index)->const std::string&{return events.at(index).id;};
            for(const int width:{640,920}){
                desktop::TabView focusedView;focusedView.setCompact(width==640);focusedView.setSize(width,680);focusedView.setDocument(source);focusedView.addToDesktop(juce::ComponentPeer::windowHasTitleBar);focusedView.setVisible(true);
                auto* peer=focusedView.getPeer();juce::Viewport* viewport=nullptr;for(auto* child:focusedView.getChildren())if(auto* candidate=dynamic_cast<juce::Viewport*>(child))viewport=candidate;
                check(peer&&focusedView.isShowing()&&viewport&&viewport->isShowing()&&viewport->getViewedComponent(),std::to_string(width)+"px visible peer and source canvas");
                auto* canvas=viewport->getViewedComponent();
                const auto route=[&](int key,const juce::Component* expectedFocus,std::size_t expectedIndex,const std::string& phase){
                    check(juce::Component::getCurrentlyFocusedComponent()==expectedFocus&&expectedFocus->isShowing(),std::to_string(width)+"px "+phase+" focused component is visible");
                    check(peer->handleKeyPress(juce::KeyPress{key}),std::to_string(width)+"px "+phase+" key dispatch consumed");
                    const auto selected=focusedView.selectedEvent();check(selected==eventAt(expectedIndex),std::to_string(width)+"px "+phase+" preserves source-order event identity");
                    check(focusedView.visibleDetail().find(selected)!=std::string::npos,std::to_string(width)+"px "+phase+" detail identifies selected event");
                    trace<<width<<'\t'<<phase<<'\t'<<(key==juce::KeyPress::rightKey?"Right":"Left")<<'\t'<<selected<<'\t'<<viewport->getViewPositionX()<<'\t'<<viewport->getMaximumVisibleWidth()<<'\t'<<canvas->getWidth()<<'\n';
                };
                focusedView.grabKeyboardFocus();check(juce::Component::getCurrentlyFocusedComponent()==&focusedView,std::to_string(width)+"px root accepts actual JUCE keyboard focus");
                route(juce::KeyPress::rightKey,&focusedView,0,"root-focus-first-right");
                canvas->grabKeyboardFocus();check(juce::Component::getCurrentlyFocusedComponent()==canvas,std::to_string(width)+"px visible Canvas receives actual JUCE keyboard focus");
                route(juce::KeyPress::rightKey,canvas,1,"canvas-focus-second-right");
                for(std::size_t index=2;index<events.size();++index)route(juce::KeyPress::rightKey,canvas,index,"canvas-focus-next-right");
                check(viewport->getViewPositionX()>0||canvas->getWidth()<=viewport->getMaximumVisibleWidth(),std::to_string(width)+"px selected final source column is revealed or fully visible");
                auto focusedImage=focusedView.createComponentSnapshot(focusedView.getLocalBounds());juce::File focusedFile(juce::String::fromUTF8((out/(width==640?"keyboard-focus-compact-640.png":"keyboard-focus-standard-920.png")).c_str()));auto focusedStream=focusedFile.createOutputStream();juce::PNGImageFormat focusedPng;check(focusedStream&&focusedPng.writeImageToStream(focusedImage,*focusedStream),std::to_string(width)+"px selected-source render");
                const auto last=focusedView.selectedEvent();route(juce::KeyPress::rightKey,canvas,events.size()-1,"canvas-focus-right-boundary");check(focusedView.selectedEvent()==last,std::to_string(width)+"px Right boundary retains final source event");
                route(juce::KeyPress::leftKey,canvas,events.size()-2,"canvas-focus-left-from-final");
                for(std::size_t index=events.size()-2;index>0;--index)route(juce::KeyPress::leftKey,canvas,index-1,"canvas-focus-previous-left");
                const auto first=focusedView.selectedEvent();route(juce::KeyPress::leftKey,canvas,0,"canvas-focus-left-boundary");check(focusedView.selectedEvent()==first,std::to_string(width)+"px Left boundary retains first source event");
                focusedView.removeFromDesktop();
            }
            trace.flush();check(trace.good(),"focused keyboard trace flushed");
            juce::DynamicObject::Ptr report=new juce::DynamicObject;report->setProperty("checks",checks);report->setProperty("failures",0);report->setProperty("compactWidth",640);report->setProperty("standardWidth",920);report->setProperty("sourceItem",juce::String::fromUTF8(source->source().itemId.c_str()));report->setProperty("eventCount",static_cast<int>(events.size()));report->setProperty("dispatch","JUCE ComponentPeer::handleKeyPress through current focused component");report->setProperty("nativeKeyEvent",false);report->setProperty("physicalKeyboard",false);report->setProperty("audioRun",false);juce::File(juce::String::fromUTF8((out/"checks.json").c_str())).replaceWithText(juce::JSON::toString(juce::var(report.get())));std::cout<<"PASS "<<checks<<" focused TAB keyboard checks\n";return 0;
        }
        if(headingUtf8){
            view.setCompact(true);view.setSize(720,680);const auto expectedHeading=juce::String::fromUTF8("TAB — Authored source view");juce::Label* heading=nullptr;
            for(auto* child:view.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child);label&&label->isVisible()&&label->getText()==expectedHeading)heading=label;
            check(heading!=nullptr,"compact TAB heading preserves the exact UTF-8 em dash");picture("compact-heading-utf8");
            juce::DynamicObject::Ptr report=new juce::DynamicObject;report->setProperty("checks",checks);report->setProperty("failures",0);report->setProperty("heading",expectedHeading);report->setProperty("nativeAudioRun",false);report->setProperty("clockIntegration",false);juce::File(juce::String::fromUTF8((out/"checks.json").c_str())).replaceWithText(juce::JSON::toString(juce::var(report.get())));std::cout<<"PASS "<<checks<<" compact TAB heading checks\n";return 0;
        }
        for(std::size_t i=0;i<models.size();++i){auto d=std::make_shared<const tab::Document>(reference_fixtures::checked(models[i]));view.setDocument(d);juce::Label* summary=nullptr;for(auto* child:view.getChildren())if(auto* label=dynamic_cast<juce::Label*>(child))if(label->getText().toStdString().find("Source / instructions for the authored record")!=std::string::npos)summary=label;check(summary&&summary->getText().toStdString().find("select an event for detail")!=std::string::npos,"summary exposes event detail and complete authored-record route");check(view.document()==d && view.selectedEvent().empty(),"explicit document no inferred event");check(view.visibleDetail().find(models[i].preservedRecordJson)!=std::string::npos,"full source reachable");check(!view.selectEvent("not-an-id"),"invalid ID refuses");if(!models[i].events.empty()){check(view.selectEvent(models[i].events.back().id),"last source event reachable");check(view.visibleDetail().find(models[i].events.back().id)!=std::string::npos,"last event detail");}}
        for(const auto index:{2u,3u,5u,6u,7u,8u,10u}){
            view.setDocument(std::make_shared<const tab::Document>(reference_fixtures::checked(models[index])));view.setSize(920,680);view.setZoom(1);view.setOverlays({true,true,false,false});picture("control-"+std::to_string(index)+"-920");
            view.setSize(1280,800);view.setOverlays({true,true,true,true});picture("control-"+std::to_string(index)+"-overlays-1280");
        }
        view.setDocument(std::make_shared<const tab::Document>(reference_fixtures::checked(models[5])));for(int n=0;n<5;++n)check(view.keyPressed(juce::KeyPress{juce::KeyPress::rightKey}),"production key handler");check(view.selectedEvent()==models[5].events[4].id,"keyboard follows stable source order");picture("L39-dual-context");
        const auto selected=view.selectedEvent();check(!view.selectEvent("missing")&&view.selectedEvent()==selected,"invalid selection retains prior source");
        check(!view.setZoom(std::numeric_limits<double>::quiet_NaN())&&!view.setZoom(0.09)&&!view.setZoom(2.01),"nonfinite unsupported zoom refused");check(view.setZoom(0.10),"minimum zoom");picture("minimum-zoom");check(view.setZoom(2),"maximum zoom");picture("maximum-zoom");view.setOverlays({false,false,false,false});picture("required-techniques-no-overlays");
        check(!view.overlays().fingers&&!view.overlays().degrees&&!view.overlays().picking&&!view.overlays().notes,"independent overlay state");view.showSource();check(view.selectedEvent().empty()&&view.visibleDetail().find("Preserved authored")!=std::string::npos,"source view clears selection honestly");
        view.setZoom(1);view.setSize(1280,800);view.setDocument(std::make_shared<const tab::Document>(reference_fixtures::checked(models[6])));view.setOverlays({false,false,false,false});check(view.selectEvent(models[6].events[14].id),"actual L48 held selected");picture("L48-held-overlays-off");check(view.selectEvent(models[6].events[15].id),"L48 rest selected");picture("L48-rest-overlays-off");
        view.setDocument(std::make_shared<const tab::Document>(reference_fixtures::checked(models[2])));check(view.selectEvent(models[2].events[7].id),"L12 turn eighth event");picture("L12-turn-eight");check(view.selectEvent(models[2].events[8].id),"L12 distinct ninth event");picture("L12-turn-nine");
        auto synthetic=reference_fixtures::air();synthetic.events[0].tones[0].fret=12;synthetic.events[0].tones[0].midi=76;synthetic.events[0].tones[0].authoredTechnique="display-only palm-mute instruction";
        view.setDocument(std::make_shared<const tab::Document>(reference_fixtures::checked(synthetic)));view.setOverlays({true,true,true,true});for(double zoom:{0.75,1.0,2.0}){view.setZoom(zoom);picture("synthetic-contact-"+std::to_string(zoom));}view.setOverlays({false,false,false,false});picture("synthetic-required-technique-overlays-off");
        auto wide=reference_fixtures::synthetic("large-fret-display");auto n=reference_fixtures::note("harmonic-unbound",Rational{},Rational{1},6,123456789,64);n.tones[0].attack=music::Attack::Harmonic;wide.events={n};view.setDocument(std::make_shared<const tab::Document>(reference_fixtures::checked(wide)));view.setZoom(1);picture("unresolved-large-fret");check(view.visibleDetail().find("Synthetic fixture")!=std::string::npos,"large fret remains labelled synthetic reference");
        wide.events[0].tones[0].authoredTechnique=std::string(200000,'x');
        const auto extentBegin=std::chrono::steady_clock::now();view.setDocument(std::make_shared<const tab::Document>(reference_fixtures::checked(wide)));
        check(std::chrono::steady_clock::now()-extentBegin<std::chrono::seconds(5),"oversized primary annotation refuses within the bounded display budget");
        check(view.document()->source().events[0].tones[0].authoredTechnique==wide.events[0].tones[0].authoredTechnique&&view.document()->detail(wide.events[0].id).find(wide.events[0].tones[0].authoredTechnique)!=std::string::npos,"display refusal preserves complete source annotation and reachable Document detail");
        picture("extent-refusal");check(view.visibleDetail().find(wide.itemId)!=std::string::npos,"extent refusal preserves source identity");
        juce::DynamicObject::Ptr report=new juce::DynamicObject;report->setProperty("checks",checks);report->setProperty("failures",0);report->setProperty("nativeAudioRun",false);report->setProperty("clockIntegration",false);juce::File(juce::String::fromUTF8((out/"checks.json").c_str())).replaceWithText(juce::JSON::toString(juce::var(report.get())));std::cout<<"PASS "<<checks<<" TAB component checks\n";return 0;
    }catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}
}
