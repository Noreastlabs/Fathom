#include "desktop/Appearance.hpp"
#include "desktop/TabView.hpp"
#include <algorithm>
#include <array>
#include <cmath>

namespace fathom::desktop {
namespace {
juce::Colour background(){return appearance::colour(0xff10212c);}
juce::Colour ink(){return appearance::colour(0xfff0f4f6);}
juce::Colour muted(){return appearance::colour(0xffb7c9d2);}
juce::Colour accent(){return appearance::colour(0xff6bd5cb);}
constexpr std::array zoomStops{0.10,0.25,0.50,0.75,1.0,1.25,1.50,1.75,2.0};
juce::String utf(const std::string& s){
    // JUCE strings cannot retain embedded NUL. Make the control byte visible;
    // the immutable source/Document detail still retain the original bytes.
    std::string display;display.reserve(s.size());
    for(const char c:s){if(c=='\0')display+="[U+0000]";else display+=c;}
    return juce::String::fromUTF8(display.data(),static_cast<int>(display.size()));
}
std::string shortAttack(music::Attack a){switch(a){case music::Attack::Picked:return "";case music::Attack::HammerOn:return "hammer-on";case music::Attack::PullOff:return "pull-off";case music::Attack::SlideArrival:return "slide arrival";case music::Attack::Bend:return "bend";case music::Attack::BlueThirdShade:return "blue-third shade";case music::Attack::Held:return "held / tie";case music::Attack::Harmonic:return "harmonic";case music::Attack::Vibrato:return "vibrato";}return "unknown technique";}
std::string technique(const music::Tone& t){auto text=shortAttack(t.attack);if(!t.authoredTechnique.empty()){if(!text.empty())text+="; ";text+=t.authoredTechnique;}return text;}
std::string measureLabel(const music::Measure& m){const auto end=m.start+Rational{static_cast<std::int64_t>(m.numerator)*4,static_cast<std::int64_t>(m.denominator)};return "Measure "+m.id+": "+std::to_string(m.numerator)+"/"+std::to_string(m.denominator)+"; q="+tab::fraction(m.start)+" to "+tab::fraction(end)+". Event columns are not proportional.";}
}
class TabView::Canvas final : public juce::Component {
    struct Panel {std::shared_ptr<const tab::Document> document;double y;int label,top;double height;bool chords,picking,active;};
public:
    explicit Canvas(TabView& parent):view(parent){setTitle("Canonical TAB, source event columns");setWantsKeyboardFocus(true);}
    int cellWidth() const { return static_cast<int>(std::ceil(logicalWidth*view.zoom_)); }
    int rowHeight() const { return (46+(view.overlays_.notes?24:0)+(view.overlays_.degrees?24:0)); }
    int columnStart(std::size_t index) const { return static_cast<int>(std::floor((65.0+index*logicalWidth)*view.zoom_)); }
    bool chordHeader() const { return chordRow_; }
    bool pickingHeader() const { return pickingRow_; }
    int notationTop() const { return panels.empty()?52:panels.front().top; }
    void reveal(std::size_t index) {
        if(!error.empty())return;
        const int left=columnStart(index),right=columnStart(index+1),current=view.viewport_.getViewPositionX();
        if(left<current || right>current+view.viewport_.getMaximumVisibleWidth())view.viewport_.setViewPosition(std::max(0,left-10),view.viewport_.getViewPositionY());
    }
    void follow(std::size_t index) {
        reveal(index);if(!error.empty()||!view.document_)return;
        const auto& event=view.document_->source().events.at(index);
        if(event.tones.empty()){view.viewport_.setViewPosition(view.viewport_.getViewPositionX(),0);return;}
        int first=100,last=0;
        for(const auto& tone:event.tones){const int row=view.document_->displayString(tone.string)-1;first=std::min(first,row);last=std::max(last,row);}
        const int above=static_cast<int>(std::floor((notationTop()+first*rowHeight()-20)*view.zoom_));
        const int annotation=34+(view.overlays_.notes?24:0)+(view.overlays_.degrees?24:0);
        const int below=static_cast<int>(std::ceil((notationTop()+last*rowHeight()+annotation)*view.zoom_));
        const int current=view.viewport_.getViewPositionY(),visible=view.viewport_.getMaximumVisibleHeight();
        if(above<current)view.viewport_.setViewPosition(view.viewport_.getViewPositionX(),std::max(0,above-4));
        else if(below>current+visible)view.viewport_.setViewPosition(view.viewport_.getViewPositionX(),std::max(0,below-visible+4));
    }
    void layout(){
        panels.clear();error.clear();futureNotice.clear();
        const auto build=[&](bool future){
            panels.clear();double width=120.0,measureWidth=0.0;fretWidth=48;
            const juce::Font font{juce::FontOptions{16.0f}},fretFont{juce::FontOptions{26.0f,juce::Font::bold}},chordFont{juce::FontOptions{20.0f,juce::Font::bold}};
            bool measurementRefused=false;std::size_t columns=0;double y=0;
            const auto measure=[&](const juce::Font& f,const std::string& t){if(t.size()>16384){measurementRefused=true;return 0.0;}return static_cast<double>(juce::GlyphArrangement::getStringWidth(f,utf(t)));};
            const auto fit=[&](const std::string& t,double extra){width=std::max(width,measure(font,t)+extra);};
            // Determine the shared fret mask before measuring any panel's technique labels.
            const auto measureFrets=[&](const std::shared_ptr<const tab::Document>& document){if(document)for(const auto& event:document->source().events)for(const auto& tone:event.tones)fretWidth=std::max(fretWidth,static_cast<int>(std::ceil(measure(fretFont,std::to_string(tone.fret))))+8);};
            measureFrets(view.document_);if(future)for(const auto& document:view.upcoming_)measureFrets(document);
            const auto append=[&](const std::shared_ptr<const tab::Document>& document,bool active){
                if(!document)return;
                const auto& source=document->source();
                const bool chords=std::any_of(source.events.begin(),source.events.end(),[](const auto& e){return !e.chordSymbol.empty()||e.kind==music::Kind::Rest||e.kind==music::Kind::Contact;});
                const bool picking=view.overlays_.picking&&std::any_of(source.events.begin(),source.events.end(),[](const auto& e){return !e.handDirection.empty();});
                const int label=future?28:0;
                const int top=52+(chords?28:0)+(picking?26:0)+28*static_cast<int>(source.measures.size());
                const double height=label+top+source.instrument.openMidi.size()*static_cast<double>(rowHeight())+64;
                panels.push_back({document,y,label,top+label,height,chords,picking,active});
                y+=height+ (future?24:0);columns=std::max(columns,source.events.size());
            for(const auto& m:document->source().measures)measureWidth=std::max(measureWidth,measure(font,measureLabel(m))+40.0);
            for(const auto& e:document->source().events)for(const auto& t:e.tones)fretWidth=std::max(fretWidth,static_cast<int>(std::ceil(measure(fretFont,std::to_string(t.fret))))+8);
            for(const auto& e:document->source().events){
                width=std::max(width,measure(chordFont,e.chordSymbol)+82);fit("Pick / hand: "+e.handDirection,26);
                fit("#"+std::to_string(document->source().events.size())+"  q="+(e.span.onset?tab::fraction(*e.span.onset):"?")+"  dur="+(e.span.duration?tab::fraction(*e.span.duration):"?"),26);
                for(const auto& t:e.tones){if(view.overlays_.degrees)fit("Deg: "+tab::degrees(t),26);if(view.overlays_.notes)fit(tab::noteName(t),26);fit(technique(t),fretWidth+34);}
                std::string scope="Scope: ";for(int n:e.scopeStrings)scope+=std::to_string(document->displayString(n))+" ";fit(scope,26);
            }
            };
            append(view.document_,true);
            if(future)for(const auto& document:view.upcoming_)append(document,false);
            const double totalWidth=std::max(measureWidth,80.0+columns*std::ceil(width))*view.zoom_;
            const double totalHeight=(y+(futureNotice.empty()?0:32))*view.zoom_;
            if(measurementRefused||!std::isfinite(totalWidth)||!std::isfinite(totalHeight)||totalWidth>1000000.0||totalHeight>100000.0)return false;
            logicalWidth=static_cast<int>(std::ceil(width));
            chordRow_=!panels.empty()&&panels.front().chords;pickingRow_=!panels.empty()&&panels.front().picking;
            setSize(std::max(view.viewport_.getMaximumVisibleWidth(),static_cast<int>(std::ceil(totalWidth))),std::max(view.viewport_.getMaximumVisibleHeight(),static_cast<int>(std::ceil(totalHeight))));return true;
        };
        // Refuse oversized future presentation without hiding or changing the active source.
        const bool future=view.document_&&!view.upcoming_.empty();
        if(future&&(view.upcoming_.size()>TabView::upcomingPanelLimit||!build(true))){futureNotice="Upcoming TAB display exceeds the view budget; active TAB remains available.";if(build(false))return;}
        else if(future||build(false))return;
        error="TAB extent exceeds the view budget. Complete source remains available through Source / instructions.";logicalWidth=220;panels.clear();setSize(std::max(1,view.viewport_.getMaximumVisibleWidth()),std::max(1,view.viewport_.getMaximumVisibleHeight()));
    }
    void paint(juce::Graphics& g) override {
        g.fillAll(background());if(!error.empty()){g.setColour(ink());g.setFont(juce::FontOptions{16.0f});g.drawFittedText(utf(error),20,20,std::max(1,getWidth()-40),100,juce::Justification::topLeft,4,1.0f);return;}if(!view.document_)return;
        g.addTransform(juce::AffineTransform::scale(static_cast<float>(view.zoom_)));
        for(const auto& panel:panels){
            juce::Graphics::ScopedSaveState saved(g);
            g.addTransform(juce::AffineTransform::translation(0,static_cast<float>(panel.y)));
            if(!panel.active)g.beginTransparencyLayer(0.30f);
            if(panel.label){g.setColour(ink());g.setFont(juce::FontOptions{16.0f});g.drawText(panel.active?"Current TAB":"Upcoming TAB",20,0,static_cast<int>(getWidth()/view.zoom_)-40,24,juce::Justification::centredLeft);}
            g.addTransform(juce::AffineTransform::translation(0,static_cast<float>(panel.label)));
            paintPanel(g,panel);if(!panel.active)g.endTransparencyLayer();
        }
        if(!futureNotice.empty()){g.setColour(muted());g.setFont(juce::FontOptions{16.0f});const auto bottom=panels.empty()?0:panels.back().y+panels.back().height;g.drawText(utf(futureNotice),20,static_cast<int>(bottom),static_cast<int>(getWidth()/view.zoom_)-40,28,juce::Justification::centredLeft);}
    }
    void paintPanel(juce::Graphics& g,const Panel& panel){
        const auto& d=*panel.document;const auto& m=d.source();const auto z=1.0f;const int cw=logicalWidth,rh=rowHeight(),topY=panel.top-panel.label,width=static_cast<int>(getWidth()/view.zoom_),height=panels.size()==1&&futureNotice.empty()?static_cast<int>(getHeight()/view.zoom_):static_cast<int>(panel.height)-panel.label;const int count=static_cast<int>(m.instrument.openMidi.size());
        g.setColour(muted());g.setFont(juce::FontOptions{16.0f});
        for(std::size_t n=0;n<m.measures.size();++n)g.drawText(utf(measureLabel(m.measures[n])),20,topY-42-28*static_cast<int>(m.measures.size()-1-n),width-40,24,juce::Justification::centredLeft);
        if(m.events.empty()){g.drawText("Instructions / reference material. No authored TAB events.",20,20,width-40,28,juce::Justification::centredLeft);return;}
        for(int display=1;display<=count;++display){const int y=topY+(display-1)*rh;g.setColour(appearance::colour(0xff617782));g.drawHorizontalLine(y,64.0f,static_cast<float>(width-12));g.setColour(muted());g.drawText(juce::String(display),16,y-12,36,24,juce::Justification::centred);}
        for(std::size_t i=0;i<m.events.size();++i){
            const auto& e=m.events[i];const int x=72+static_cast<int>(i)*cw;const auto box=juce::Rectangle<int>{x-7,4,cw-4,height-12};
            if(panel.active && std::find(view.playing_.begin(),view.playing_.end(),e.id)!=view.playing_.end()){g.setColour(appearance::colour(0xffffcb77).withAlpha(0.18f));g.fillRoundedRectangle(box.toFloat(),5);g.setColour(appearance::colour(0xffffcb77));g.fillRect(x-7,4,cw-4,4);}
            if(panel.active && e.id==view.selected_){g.setColour(accent().withAlpha(0.11f));g.fillRoundedRectangle(box.toFloat(),5);g.setColour(accent());g.drawRoundedRectangle(box.toFloat(),5,2);}
            g.setColour(muted());g.setFont(juce::FontOptions{16.0f});
            const std::string at=e.span.onset?tab::fraction(*e.span.onset):"?";const std::string dur=e.span.duration?tab::fraction(*e.span.duration):"?";
            g.drawText(utf("#"+std::to_string(i+1)+"  q="+at+"  dur="+dur),x,8,cw-18,24,juce::Justification::centredLeft);
            if(!e.chordSymbol.empty()){g.setColour(ink());g.setFont(juce::FontOptions{std::max(16.0f,20*z),juce::Font::bold});g.drawText(utf(e.chordSymbol),x,34,cw-18,26,juce::Justification::centredLeft);}
            else if(e.kind==music::Kind::Rest || e.kind==music::Kind::Contact){g.setColour(ink());g.setFont(juce::FontOptions{16.0f});g.drawText(utf(e.kind==music::Kind::Rest?"REST (scope in detail)":tab::contact(e.contact)),x,34,cw-18,26,juce::Justification::centredLeft);}
            if(view.overlays_.picking && !e.handDirection.empty()){g.setColour(ink());g.setFont(juce::FontOptions{16.0f});g.drawText(utf("Pick / hand: "+e.handDirection),x,panel.chords?64:36,cw-18,24,juce::Justification::centredLeft);}
            for(const auto& t:e.tones){const int y=topY+(d.displayString(t.string)-1)*rh;
                const auto annotation=technique(t);const auto annotationWidth=juce::GlyphArrangement::getStringWidth(juce::Font{juce::FontOptions{16.0f}},utf(annotation));
                const int maskWidth=annotation.empty()?fretWidth+4:fretWidth+14+static_cast<int>(std::ceil(annotationWidth));
                g.setColour(background());g.fillRect(x-2,y-17,maskWidth,31);g.setColour(ink());g.setFont(juce::FontOptions{std::max(20.0f,26*z),juce::Font::bold});g.drawText(juce::String(t.fret),x,y-17,fretWidth,30,juce::Justification::centredLeft);
                g.setColour(accent());g.setFont(juce::FontOptions{16.0f});g.drawText(utf(technique(t)),x+fretWidth+8,y-13,cw-fretWidth-26,24,juce::Justification::centredLeft);
                int a=y+13;g.setColour(muted());if(view.overlays_.fingers){g.drawText(utf("Fng: "+(t.finger.empty()?std::string("?"):t.finger)),x,a,cw-18,20,juce::Justification::centredLeft);}a+=24;
                if(view.overlays_.notes){g.drawText(utf(tab::noteName(t)),x,a,cw-18,20,juce::Justification::centredLeft);a+=24;}
                if(view.overlays_.degrees){g.drawText(utf("Deg: "+tab::degrees(t)),x,a,cw-18,20,juce::Justification::centredLeft);}
            }
            const int footer=topY+count*rh;g.setColour(ink());g.setFont(juce::FontOptions{16.0f});
            std::string label=e.kind==music::Kind::Rest?"REST":e.kind==music::Kind::Contact?tab::contact(e.contact):"";
            if(!label.empty())g.drawText(utf(label),x,footer,cw-18,24,juce::Justification::centredLeft);
            if(e.kind==music::Kind::Rest || e.kind==music::Kind::Contact){std::string sc="Scope: ";for(int s:e.scopeStrings)sc+=std::to_string(d.displayString(s))+" ";if(e.scopeStrings.empty())sc+="unspecified";g.drawText(utf(sc),x,footer+24,cw-18,24,juce::Justification::centredLeft);}
            bool measure=false;for(const auto& bar:m.measures)if(e.span.onset && *e.span.onset==bar.start){measure=true;g.setColour(accent());g.drawText(utf(std::to_string(bar.numerator)+"/"+std::to_string(bar.denominator)),x+cw-58,36,44,24,juce::Justification::centredLeft);}
            if(measure){g.setColour(accent());g.drawLine(static_cast<float>(x-10),static_cast<float>(topY-22),static_cast<float>(x-10),static_cast<float>(topY+(count-1)*rh+12),2);}
        }
    }
    void mouseDown(const juce::MouseEvent& e) override {
        if(!view.document_ || !error.empty() || e.position.x/view.zoom_<65)return;
        if(!panels.empty()&&(panels.size()>1||!futureNotice.empty())&&(e.position.y/view.zoom_<panels.front().label||e.position.y/view.zoom_>=panels.front().height))return;const auto index=static_cast<std::size_t>((e.position.x/view.zoom_-65)/logicalWidth);const auto& events=view.document_->source().events;
        if(index<events.size())view.selectEvent(events[index].id);
    }
    bool keyPressed(const juce::KeyPress& k) override{return view.keyPressed(k);}
private:TabView& view;int logicalWidth=220,fretWidth=48;bool chordRow_{},pickingRow_{};std::string error,futureNotice;std::vector<Panel> panels;
};
TabView::TabView():canvas_(std::make_unique<Canvas>(*this)) {
    setWantsKeyboardFocus(true);title_.setText("Interactive TAB",juce::dontSendNotification);title_.setFont(juce::FontOptions{24.0f,juce::Font::bold});title_.setColour(juce::Label::textColourId,ink());
    summary_.setColour(juce::Label::textColourId,muted());summary_.setFont(juce::FontOptions{14.0f});
    playbackStatus_.setColour(juce::Label::textColourId,appearance::colour(0xffffcb77));playbackStatus_.setFont(juce::FontOptions{14.0f});addAndMakeVisible(playbackStatus_);
    addChildComponent(detailButton_);detailButton_.onClick=[this]{showDetail(!showDetail_);};
    for(auto* l:{&title_,&summary_})addAndMakeVisible(*l);
    for(auto* b:{&fingers_,&picking_,&notes_,&degrees_}){addAndMakeVisible(*b);b->setColour(juce::ToggleButton::textColourId,ink());b->onClick=[this]{setOverlays({fingers_.getToggleState(),picking_.getToggleState(),notes_.getToggleState(),degrees_.getToggleState()});};}
    for(auto* b:{&smaller_,&larger_,&resetZoom_,&source_})addAndMakeVisible(*b);
    zoomValue_.setTitle("Notation zoom percentage");zoomValue_.setColour(juce::Label::textColourId,ink());addAndMakeVisible(zoomValue_);
    for(auto* b:{&detailButton_,&smaller_,&larger_,&resetZoom_,&source_}){b->setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));b->setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));b->setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));}
    smaller_.onClick=[this]{const auto next=std::lower_bound(zoomStops.begin(),zoomStops.end(),zoom_);if(next!=zoomStops.begin())setZoom(*(next-1));};
    larger_.onClick=[this]{const auto next=std::upper_bound(zoomStops.begin(),zoomStops.end(),zoom_);if(next!=zoomStops.end())setZoom(*next);};
    resetZoom_.onClick=[this]{setZoom(1.0);};source_.onClick=[this]{showSource();showDetail(true);};
    viewport_.setViewedComponent(canvas_.get(),false);viewport_.setScrollBarsShown(true,true);addAndMakeVisible(viewport_);
    detail_.setMultiLine(true,true);detail_.setReadOnly(true);detail_.setScrollbarsShown(true);detail_.setCaretVisible(false);detail_.setFont(juce::FontOptions{14.0f});detail_.setColour(juce::TextEditor::backgroundColourId,appearance::colour(0xff162d39));detail_.setColour(juce::TextEditor::textColourId,ink());detail_.setTitle("Selected event or complete source instructions");addAndMakeVisible(detail_);setSize(920,680);refresh();
}
TabView::~TabView(){viewport_.setViewedComponent(nullptr,false);}
void TabView::setDocument(std::shared_ptr<const tab::Document> d){document_=std::move(d);upcoming_.clear();selected_.clear();playing_.clear();playbackStatus_.setText("No accepted playback yet.",juce::dontSendNotification);showSource();viewport_.setViewPosition(0,0);refresh();}
void TabView::setUpcomingDocuments(std::vector<std::shared_ptr<const tab::Document>> documents){
    const auto position=viewport_.getViewPosition();upcoming_=std::move(documents);canvas_->layout();viewport_.setViewPosition(position);canvas_->repaint();
}
bool TabView::selectEvent(const std::string& id){if(!document_ || !document_->event(id))return false;selected_=id;detail_.setText(utf(document_->detail(id)),false);canvas_->repaint();const auto& events=document_->source().events;const auto it=std::find_if(events.begin(),events.end(),[&](const auto& e){return e.id==id;});canvas_->follow(static_cast<std::size_t>(it-events.begin()));if(onSelection)onSelection(id);return true;}
void TabView::showSource(){selected_.clear();detail_.setText(document_?utf(document_->overview()):"No validated musical document selected.",false);canvas_->repaint();}
bool TabView::setZoom(double value){if(!std::isfinite(value)||value<zoomStops.front()||value>zoomStops.back())return false;zoom_=value;refresh();return true;}
void TabView::setOverlays(TabOverlays o){overlays_=o;refresh();}
void TabView::refresh(){fingers_.setToggleState(overlays_.fingers,juce::dontSendNotification);picking_.setToggleState(overlays_.picking,juce::dontSendNotification);notes_.setToggleState(overlays_.notes,juce::dontSendNotification);degrees_.setToggleState(overlays_.degrees,juce::dontSendNotification);smaller_.setEnabled(zoom_>zoomStops.front());larger_.setEnabled(zoom_<zoomStops.back());zoomValue_.setText(juce::String(static_cast<int>(std::lround(zoom_*100)))+"%",juce::dontSendNotification);resetZoom_.setEnabled(zoom_!=1.0);
    summary_.setText(document_?(document_->allTimed()?"Exact q / duration labels; select an event for detail or Source / instructions for the authored record.":"No rhythm inferred; select an event for detail or Source / instructions for the authored record."):"No validated musical document selected.",juce::dontSendNotification);canvas_->layout();if(!selected_.empty() && document_){const auto& events=document_->source().events;const auto it=std::find_if(events.begin(),events.end(),[this](const auto& e){return e.id==selected_;});if(it!=events.end())canvas_->follow(static_cast<std::size_t>(it-events.begin()));}canvas_->repaint();}
void TabView::resized(){
    auto area=getLocalBounds().reduced(compact_?8:16);
    title_.setText(compact_?utf("TAB — Authored source view"):"Interactive TAB",juce::dontSendNotification);
    title_.setVisible(!compact_||getWidth()<800);summary_.setVisible(!compact_);
    if(!compact_){title_.setBounds(area.removeFromTop(32));summary_.setBounds(area.removeFromTop(40));}else if(getWidth()<800)title_.setBounds(area.removeFromTop(30));
    auto first=area.removeFromTop(30);
    detailButton_.setVisible(true);detailButton_.setBounds(first.removeFromRight(78));first.removeFromRight(6);
    source_.setBounds(first.removeFromRight(std::min(190,std::max(100,first.getWidth()/3))));first.removeFromRight(6);
    playbackStatus_.setBounds(first);
    auto buttons=area.removeFromTop(32);
    fingers_.setBounds(buttons.removeFromLeft(58));picking_.setBounds(buttons.removeFromLeft(76));notes_.setBounds(buttons.removeFromLeft(108));degrees_.setBounds(buttons.removeFromLeft(130));
    if(getWidth()<800)buttons=area.removeFromTop(32);
    smaller_.setBounds(buttons.removeFromLeft(68).reduced(2));zoomValue_.setBounds(buttons.removeFromLeft(54));larger_.setBounds(buttons.removeFromLeft(68).reduced(2));resetZoom_.setBounds(buttons.removeFromLeft(104).reduced(2));
    area.removeFromTop(4);
    detail_.setVisible(showDetail_);viewport_.setVisible(!showDetail_);detail_.setBounds(area);viewport_.setBounds(area);
    canvas_->layout();
    if(!selected_.empty()&&document_){const auto& events=document_->source().events;const auto it=std::find_if(events.begin(),events.end(),[this](const auto& e){return e.id==selected_;});if(it!=events.end())canvas_->follow(static_cast<std::size_t>(it-events.begin()));}
}
bool TabView::setPlayback(std::vector<std::string> ids,std::string status){
 if(!document_&&!ids.empty())return false;for(const auto& id:ids)if(!document_->event(id))return false;
 const bool changed=playing_!=ids;playing_=std::move(ids);playbackStatus_.setText(utf(status),juce::dontSendNotification);
 if(changed&&!playing_.empty()){const auto& events=document_->source().events;const auto it=std::find_if(events.begin(),events.end(),[this](const auto& e){return e.id==playing_.front();});canvas_->follow(static_cast<std::size_t>(it-events.begin()));}canvas_->repaint();return true;
}
void TabView::setCompact(bool value){compact_=value;resized();}
void TabView::showDetail(bool value){showDetail_=value;detailButton_.setButtonText(value?"TAB":"Detail");resized();}
void TabView::paint(juce::Graphics& g){g.fillAll(background());}
bool TabView::keyPressed(const juce::KeyPress& k){if(!document_ || document_->source().events.empty())return false;const auto& events=document_->source().events;const auto it=std::find_if(events.begin(),events.end(),[this](const auto& e){return e.id==selected_;});if(k.getKeyCode()!=juce::KeyPress::leftKey&&k.getKeyCode()!=juce::KeyPress::rightKey)return false;std::size_t index=it==events.end()?0:static_cast<std::size_t>(it-events.begin());if(it!=events.end()){if(k.getKeyCode()==juce::KeyPress::rightKey){if(index+1<events.size())++index;}else if(index>0)--index;}selectEvent(events[index].id);return true;}
} // namespace fathom::desktop
