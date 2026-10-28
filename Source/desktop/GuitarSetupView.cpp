#include "desktop/GuitarSetupView.hpp"
#include "desktop/Appearance.hpp"
#include <iostream>

namespace fathom::desktop {
namespace {
constexpr auto ink = 0xffdce8ed;
constexpr auto muted = 0xffa9bbc5;
constexpr auto aqua = 0xff6bd5cb;
void label(juce::Label& control, const juce::String& text, float size = 15.0f) {
    control.setText(text,juce::dontSendNotification);
    control.setFont(juce::FontOptions{size});
    control.setColour(juce::Label::textColourId,appearance::colour(ink));
}
}
GuitarSetupView::GuitarSetupView() {
    label(heading,"Guitar setup",32.0f);
    label(explanation,"Describe your guitar. This does not detect its physical tuning. Applying setup changes local configuration only; authored lesson tuning remains unchanged.");
    label(tuningLabel,"Open tuning - low to high");
    label(capoLabel,"Capo (physical fret)"); label(fretsLabel,"Physical fret count"); label(handLabel,"Fretboard orientation");
    label(summary,""); label(status,"No setup changes applied in this app session. Choose a preset or edit fields, then Apply setup.");
    status.setTitle("Guitar setup session state and next action.");
    label(footer,"Changes are kept for this app session. Lesson notes keep their authored tuning.",14.0f);
    footer.setColour(juce::Label::textColourId,appearance::colour(muted));
    summary.setJustificationType(juce::Justification::topLeft);
    status.setJustificationType(juce::Justification::topLeft);
    for (auto* control : {&heading,&explanation,&tuningLabel,&capoLabel,&fretsLabel,&handLabel,&summary,&status,&footer})
        addAndMakeVisible(*control);
    preset.addItem("Standard",1); preset.addItem("E-flat Standard",2); preset.addItem("Drop D",3); preset.addItem("Custom",4); preset.addItem("Open E",5);
    preset.setTitle("Tuning preset"); preset.setSelectedId(1,juce::dontSendNotification);
    preset.onChange = [this] { selectPreset(); };
    boardMode.addItem("Basic",1); boardMode.addItem("Finger",2); boardMode.addItem("Note",3);
    boardMode.setTitle("Playback fretboard mode"); boardMode.setSelectedId(1,juce::dontSendNotification);
    noteSpelling.addItem("Sharp names",1); noteSpelling.addItem("Flat names",2);
    noteSpelling.setTitle("Playback fretboard note spelling"); noteSpelling.setSelectedId(1,juce::dontSendNotification);
    boardVisible.setTitle("Show playback fretboard");
    auto displayChanged=[this] { if(onBoardDisplayChanged)onBoardDisplayChanged(draftBoardDisplay()); };
    boardVisible.onClick=displayChanged; boardMode.onChange=displayChanged; noteSpelling.onChange=displayChanged;
    addAndMakeVisible(boardVisible); addAndMakeVisible(boardMode); addAndMakeVisible(noteSpelling);
    hand.addItem("Right-handed",1); hand.addItem("Left-handed",2);
    hand.setTitle("Fretboard orientation"); hand.setSelectedId(1,juce::dontSendNotification);
    for (std::size_t i = 0; i < notes.size(); ++i) {
        const auto name = "String " + juce::String(6-static_cast<int>(i));
        label(stringLabels[i], name + (i == 0 ? " - low" : i == 5 ? " - high" : ""));
        notes[i].setTitle(name + " open note");
        notes[i].setText(guitar::noteName(active.current().openMidi[i]),false);
        notes[i].onTextChange = [this] { preset.setSelectedId(4,juce::dontSendNotification); };
        notes[i].setSelectAllWhenFocused(true);
        addAndMakeVisible(stringLabels[i]); addAndMakeVisible(notes[i]);
    }
    capo.setTitle("Capo physical fret"); capo.setText("0",false); capo.setSelectAllWhenFocused(true);
    frets.setTitle("Physical fret count"); frets.setText("22",false); frets.setSelectAllWhenFocused(true);
    apply.onClick = [this] { applyDraft(); };
    back.onClick = [this] {
        if (onBack) { onBack(); return; }
        status.setText("Back is unavailable from Guitar setup until the existing Home navigation is connected. The current setup draft remains here; no setup change or curriculum activity was applied.",juce::dontSendNotification);
    };
    addAndMakeVisible(preset); addAndMakeVisible(hand); addAndMakeVisible(capo); addAndMakeVisible(frets);
    addAndMakeVisible(apply); addAndMakeVisible(back); addAndMakeVisible(board);
    for (auto* button : {static_cast<juce::TextButton*>(&apply), static_cast<juce::TextButton*>(&back)}) {
        button->setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));
        button->setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));
        button->setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    }
    back.setExplicitFocusOrder(1); preset.setExplicitFocusOrder(2);
    for (std::size_t i = 0; i < notes.size(); ++i) notes[i].setExplicitFocusOrder(static_cast<int>(i)+3);
    capo.setExplicitFocusOrder(9); frets.setExplicitFocusOrder(10); hand.setExplicitFocusOrder(11); apply.setExplicitFocusOrder(12);
    boardVisible.setExplicitFocusOrder(13); boardMode.setExplicitFocusOrder(14); noteSpelling.setExplicitFocusOrder(15);
    refreshSummary();
}
void GuitarSetupView::selectPreset() {
    const int selected = preset.getSelectedId();
    if (selected != 1 && selected != 2 && selected != 3 && selected != 5) return;
    const auto values = guitar::tuning(selected == 1 ? guitar::Preset::Standard : selected == 2 ? guitar::Preset::EFlat : selected == 3 ? guitar::Preset::DropD : guitar::Preset::OpenE);
    for (std::size_t i = 0; i < notes.size(); ++i) notes[i].setText(guitar::noteName(values[i]),false);
    status.setText("Draft changed. Choose Apply setup to use it.",juce::dontSendNotification);
}
void GuitarSetupView::setBoardDisplayStatus(const std::string& text) {
    footer.setText(juce::String{text}+" Authored lesson tuning remains unchanged.",juce::dontSendNotification);
}
void GuitarSetupView::setBoardDisplay(const setup::BoardDisplay& value) {
    setup::validateBoardDisplay(value);
    boardVisible.setToggleState(value.visible,juce::dontSendNotification);
    boardMode.setSelectedId(static_cast<int>(value.mode)+1,juce::dontSendNotification);
    noteSpelling.setSelectedId(static_cast<int>(value.spelling)+1,juce::dontSendNotification);
}
setup::BoardDisplay GuitarSetupView::draftBoardDisplay() const {
    setup::BoardDisplay value;
    value.visible=boardVisible.getToggleState();
    value.mode=static_cast<setup::BoardMode>(boardMode.getSelectedId()-1);
    value.spelling=static_cast<setup::NoteSpelling>(noteSpelling.getSelectedId()-1);
    setup::validateBoardDisplay(value);
    return value;
}
void GuitarSetupView::applyDraft() {
    try {
        if(canApply&&!canApply())throw std::invalid_argument("Finish the current activity and any pending result or settings save before applying a setup");
        std::string error;
        const auto draft = draftSetup(&error);
        if(!draft)throw std::invalid_argument(error);
        acceptSetup(*draft,false);
        if(onUserApplied)onUserApplied();
    } catch (const std::exception& error) {
        showError(error.what());
    }
}
std::optional<guitar::Setup> GuitarSetupView::draftSetup(std::string* error) const {
    try {
        auto draft=active.current();
        for(std::size_t i=0;i<notes.size();++i)draft.openMidi[i]=guitar::parseNote(notes[i].getText().toStdString());
        draft.capo=guitar::parseCount(capo.getText().toStdString());
        draft.fretCount=guitar::parseCount(frets.getText().toStdString());
        if(hand.getSelectedId()!=1&&hand.getSelectedId()!=2)throw std::invalid_argument("Choose a supported fretboard orientation");
        draft.handedness=hand.getSelectedId()==1?guitar::Handedness::Right:guitar::Handedness::Left;
        const auto issues=guitar::validate(draft);
        if(!issues.empty())throw std::invalid_argument(issues.front().message);
        if(error)error->clear();
        return draft;
    }catch(const std::exception& failure){if(error)*error=failure.what();return std::nullopt;}
}
bool GuitarSetupView::setDraft(const guitar::Setup& draft) {
    const auto issues=guitar::validate(draft);
    if(!issues.empty()){showError(issues.front().message);return false;}
    for(std::size_t i=0;i<notes.size();++i)notes[i].setText(guitar::noteName(draft.openMidi[i]),false);
    capo.setText(juce::String(draft.capo),false);frets.setText(juce::String(draft.fretCount),false);
    hand.setSelectedId(draft.handedness==guitar::Handedness::Right?1:2,juce::dontSendNotification);
    int presetId=4;
    if(draft.openMidi==guitar::tuning(guitar::Preset::Standard))presetId=1;
    else if(draft.openMidi==guitar::tuning(guitar::Preset::EFlat))presetId=2;
    else if(draft.openMidi==guitar::tuning(guitar::Preset::DropD))presetId=3;
    else if(draft.openMidi==guitar::tuning(guitar::Preset::OpenE))presetId=5;
    preset.setSelectedId(presetId,juce::dontSendNotification);
    status.setText("Draft changed. Choose Apply setup to use it.",juce::dontSendNotification);
    return true;
}
bool GuitarSetupView::applySetup(const guitar::Setup& value) {
    try{
        if(canApply&&!canApply())throw std::invalid_argument("Finish the current activity and any pending result or settings save before applying a setup");
        acceptSetup(value,true);return true;
    }catch(const std::exception& error){showError(error.what());return false;}
}
void GuitarSetupView::acceptSetup(const guitar::Setup& draft,bool syncDraft) {
    const auto issues=active.apply(draft,{true,true}); // host guard supplies current stopped/resolved admission
    if(!issues.empty())throw std::invalid_argument(issues.front().message);
    if(syncDraft)setDraft(draft);
    refreshSummary();
    if(onApplied)onApplied();
    status.setColour(juce::Label::textColourId,appearance::colour(aqua));
    status.setText("Setup applied. Open fret0 is at the capo; numbered frets are relative to it.",juce::dontSendNotification);
    std::cout<<"setup applied revision="<<active.revision()<<" capo="<<draft.capo<<" frets="<<draft.fretCount<<" hand="<<(draft.handedness==guitar::Handedness::Right?"right":"left")<<" tuning=";
    for(int midi:draft.openMidi)std::cout<<midi<<',';
    std::cout<<std::endl;
}
void GuitarSetupView::showError(const std::string& error) {
    status.setColour(juce::Label::textColourId,appearance::colour(0xffffc17d));
    status.setText(juce::String(error)+" Current setup unchanged.",juce::dontSendNotification);
    std::cout<<"setup refused: "<<error<<"; revision="<<active.revision()<<std::endl;
}
void GuitarSetupView::refreshSummary() {
    board.setup = active.current(); board.repaint();
    const bool left = active.current().handedness == guitar::Handedness::Left;
    summary.setText(juce::String(left ? "Left-handed: capo/open at right; frets increase left." : "Right-handed: capo/open at left; frets increase right.") +
        "\nString1 is high/top; string6 low/bottom. Preview: relative frets 0-12. Sharp note names; -- means unavailable.",juce::dontSendNotification);
}
void GuitarSetupView::paint(juce::Graphics& g) {
    g.fillAll(appearance::colour(0xff10212c));
    if (getWidth() >= 800) {
        g.setColour(appearance::colour(aqua)); g.fillRect(28,104,getWidth()-56,2);
    }
}
void GuitarSetupView::resized() {
    if (getWidth() < 800) {
        const int width = std::max(1,getWidth()-48);
        heading.setText(juce::String::fromUTF8("Guitar setup — Instrument configuration"),juce::dontSendNotification);
        heading.setBounds(24,10,width-84,34); back.setBounds(getWidth()-96,12,72,28);
        explanation.setBounds(24,48,width,48);
        tuningLabel.setBounds(24,100,120,24); preset.setBounds(150,98,width-174,30);
        const int cell = width/6;
        for (int i = 0; i < 6; ++i) {
            stringLabels[static_cast<std::size_t>(i)].setBounds(24+i*cell,134,cell-8,25);
            notes[static_cast<std::size_t>(i)].setBounds(24+i*cell,162,cell-8,30);
        }
        capoLabel.setBounds(24,206,130,24); capo.setBounds(24,234,120,30);
        fretsLabel.setBounds(166,206,130,24); frets.setBounds(166,234,120,30);
        handLabel.setBounds(308,206,170,24); hand.setBounds(308,234,width-332,30);
        apply.setBounds(24,278,162,36);
        const int displayCell=std::max(1,(width-186)/3);
        boardVisible.setBounds(210,278,displayCell,36);
        boardMode.setBounds(210+displayCell,278,displayCell-4,36);
        noteSpelling.setBounds(210+displayCell*2,278,displayCell-4,36);
        status.setBounds(24,322,width,44); summary.setBounds(24,374,width,50);
        board.setBounds(24,434,width,std::min(174,std::max(1,getHeight()-49-8-434))); footer.setBounds(24,getHeight()-49,width,35);
        return;
    }
    const int width = getWidth()-56;
    heading.setText("Guitar setup",juce::dontSendNotification);
    heading.setBounds(28,24,width-110,45); back.setBounds(getWidth()-118,28,90,34);
    explanation.setBounds(28,72,width,26);
    tuningLabel.setBounds(28,119,260,25); preset.setBounds(getWidth()-270,116,242,30);
    const int cell = width/6;
    for (int i = 0; i < 6; ++i) {
        stringLabels[static_cast<std::size_t>(i)].setBounds(28+i*cell,152,cell-10,25);
        notes[static_cast<std::size_t>(i)].setBounds(28+i*cell,179,cell-10,30);
    }
    capoLabel.setBounds(28,223,170,24); capo.setBounds(28,251,130,30);
    fretsLabel.setBounds(210,223,170,24); frets.setBounds(210,251,130,30);
    handLabel.setBounds(392,223,200,24); hand.setBounds(392,251,210,30);
    apply.setBounds(getWidth()-190,247,162,36);
    boardVisible.setBounds(28,293,240,30); boardMode.setBounds(280,293,150,30); noteSpelling.setBounds(442,293,150,30);
    status.setBounds(28,333,width,44); summary.setBounds(28,383,width,49);
    board.setBounds(28,440,width,std::min(174,std::max(1,getHeight()-49-8-440)));
    footer.setBounds(28,getHeight()-49,width,35);
}
void GuitarSetupView::Board::paint(juce::Graphics& g) {
    g.fillAll(appearance::colour(0xff172e3b));
    constexpr int columns = 13;
    const int rowHeight=std::max(1,(getHeight()-29)/6);
    const float margin = 42.0f;
    const float cell = (static_cast<float>(getWidth())-margin-6.0f)/columns;
    g.setFont(juce::FontOptions{12.0f});
    for (int fret = 0; fret < columns; ++fret) {
        const int column = guitar::fretColumn(fret,columns,setup.handedness);
        const float x = margin + static_cast<float>(column)*cell;
        g.setColour(appearance::colour(aqua));
        g.drawText(fret == 0 ? "0" : juce::String(fret),static_cast<int>(x),3,static_cast<int>(cell),19,juce::Justification::centred);
        g.setColour(appearance::colour(0xff38505e));g.drawVerticalLine(static_cast<int>(x),24.0f,static_cast<float>(getHeight()-3));
        for (int row = 0; row < 6; ++row) {
            const auto p = guitar::position(setup,6-row,fret);
            const auto text = p.available() ? juce::String(guitar::noteName(*p.midi)) : juce::String::fromUTF8("—");
            g.setColour(appearance::colour(p.available()?ink:muted));
            g.drawText(text,static_cast<int>(x),26+row*rowHeight,static_cast<int>(cell),rowHeight,juce::Justification::centred);
        }
    }
    for (int row = 0; row < 6; ++row) {
        g.setColour(appearance::colour(aqua));g.drawText(juce::String(row+1),3,26+row*rowHeight,32,rowHeight,juce::Justification::centred);
    }
}
} // namespace fathom::desktop
