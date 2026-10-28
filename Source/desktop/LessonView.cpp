#include "desktop/Appearance.hpp"
#include "desktop/LessonView.hpp"
#include "desktop/LessonSelectionLabel.hpp"
#include "desktop/HiddenSevenLearnerSourceLabel.hpp"
#include "storage/StorageEnvelope.hpp"
#include <algorithm>
#include <cctype>
#include <set>
namespace fathom::desktop {
namespace {juce::String utf8(const std::string& s){return juce::String::fromUTF8(s.c_str());}}
namespace {
std::string folded(std::string value){
    for(auto& c:value)c=static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return value;
}
std::string previewInventory(const lesson::Catalog& catalog,presentation::Level level,bool compact=false,bool selectedScope=false){
    if(level==presentation::Level::Beginner)
        return "Case inspector. Reading does not start Practice.";
    if(level==presentation::Level::Advanced)
        return std::string(selectedScope?"Prepared selection and control cases":"Retained Practice cases")+"; the selected variant decides availability.\nReading does not start Practice or award credit.";
    const auto& records=catalog.lessons();
    std::size_t variants=0;
    std::set<std::string> workbooks;
    for(const auto& record:records){variants+=record.variants.size();workbooks.insert(record.record.object().at("workbook_id").string());}
    const auto sources=catalog.sourceEntryCount();
    if(compact)return std::string(selectedScope?"Prepared selection catalog: ":"Retained preview catalog: ")+std::to_string(records.size())+" cases / "+
        std::to_string(variants)+" variants / "+std::to_string(sources)+" sources\n"+
        std::to_string(workbooks.size())+" / 105 workbook identities represented; counts are not completion or credit.";
    return std::string(selectedScope?"Prepared selection and control catalog: ":"Retained Practice preview catalog: ")+std::to_string(records.size())+
        " cases | "+std::to_string(variants)+" variants | "+std::to_string(sources)+" retained source entries\n"+
        std::to_string(workbooks.size())+" of 105 approved workbook identities represented by these cases.\n"+
        "These catalog counts do not measure exercise engineering acceptance, whole-workbook completion or learner credit. Search and inspection are read-only until explicit Practice.";
}
}
LessonView::LessonView(){
 presentationSelector_.setComponentID("learn-presentation");
 presentationSelector_.onChoice=[this](std::optional<presentation::Level> level){if(onPresentationChoice)onPresentationChoice(level);};
 addAndMakeVisible(presentationSelector_);

    configureSourceControls();
    addAndMakeVisible(setupSummary_);addAndMakeVisible(setupButton_);addChildComponent(setupDetails_);
    setupSummary_.setFont(juce::FontOptions{14.0f});setupSummary_.setJustificationType(juce::Justification::topLeft);setupSummary_.setComponentID("setup-summary");setupDetails_.setComponentID("setup-details");
    setupDetails_.setMultiLine(true,true);setupDetails_.setReadOnly(true);setupDetails_.setScrollbarsShown(true);setupDetails_.setCaretVisible(false);
    setupButton_.setComponentID("setup-button");setupButton_.setTitle("Show or hide Guitar setup compatibility details without changing the selected source or Practice state.");
    setupButton_.onClick=[this]{setupDetailsVisible_=!setupDetailsVisible_;refresh();};
    title_.setText(utf8("Learn — Source-backed Development Preview catalog"),juce::dontSendNotification);title_.setComponentID("learn-heading");title_.setFont(juce::FontOptions{24.0f,juce::Font::bold});
    summary_.setJustificationType(juce::Justification::topLeft);
    selectedCaseHeading_.setText("SELECTED CASE",juce::dontSendNotification);selectedCaseHeading_.setFont(juce::FontOptions{16.0f,juce::Font::bold});selectedCaseHeading_.setComponentID("learn-selected-case-heading");selectedCaseHeading_.setTitle("Read-only selected Learn case heading");
    emptyCatalogState_.setComponentID("learn-empty-catalog-state");emptyCatalogState_.setTitle("Learn empty catalog state marker.");emptyCatalogState_.setFont(juce::FontOptions{16.0f,juce::Font::bold});emptyCatalogState_.setColour(juce::Label::textColourId,appearance::colour(0xffa9bbc5));emptyCatalogState_.setText("No source-backed Learn catalog loaded yet",juce::dontSendNotification);
    summary_.setTitle("Read-only selected Learn case: source identity, runtime admission, next action and no-credit boundary.");
    searchLabel_.setText("Find in catalog",juce::dontSendNotification);searchLabel_.setComponentID("lesson-search-label");searchLabel_.setTitle("Find retained source-backed Learn cases by title, stable ID, workbook, level, variant label or source reference; Clear Search restores all retained cases.");
    search_.setComponentID("lesson-search");search_.setTitle("Search retained lesson catalog by title, stable ID, workbook, level, variant label or source reference");
    search_.setTextToShowWhenEmpty("Title, ID, workbook, level, variant label or source reference",appearance::colour(0xff8aa0ad));
    search_.setMultiLine(false);search_.setReturnKeyStartsNewLine(false);search_.setScrollbarsShown(false);search_.setCaretVisible(true);
    searchLabel_.setJustificationType(juce::Justification::centredLeft);searchStatus_.setComponentID("lesson-search-status");searchStatus_.setTitle("Read-only Learn catalog search results, retained-case recovery and next action.");searchStatus_.setJustificationType(juce::Justification::centredLeft);searchStatus_.setFont(juce::FontOptions{12.0f});
    clearSearch_.setComponentID("lesson-search-clear");clearSearch_.setTitle("Clear Learn catalog search");clearSearch_.onClick=[this]{search_.setText({},true);refreshLessonChoices();refresh();};
    for(auto* c:std::initializer_list<juce::Component*>{&tempoLabel_,&tempo_,&practice_,&metronome_,&rhythm_,&audio_})addAndMakeVisible(c);
    tempoLabel_.setText("Selected quarter BPM",juce::dontSendNotification);tempo_.setText("60",false);tempo_.setTitle("Selected quarter-note tempo, 20 to 300 BPM");tempo_.setComponentID("selected-tempo");practice_.setComponentID("practice-selection");practice_.setTitle("Open the selected admitted source-backed case in Practice; explicit Practice Start creates the Attempt; no curriculum credit is inferred.");practice_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));practice_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));practice_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));practice_.setExplicitFocusOrder(6);
    for(auto* button:{&clearSearch_,&setupButton_,&metronome_,&rhythm_,&audio_,&back_,&mode_,&details_}){button->setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));button->setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));button->setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));}
    rhythm_.setComponentID("rhythm-preview");rhythm_.setTitle("Open the existing shared Rhythm preview; no Practice Attempt, curriculum credit, or sound starts from Learn.");rhythm_.setWantsKeyboardFocus(true);rhythm_.setExplicitFocusOrder(8);
    practice_.onClick=[this]{practiceSelected();};
    metronome_.onClick=[this]{requestMetronome();};rhythm_.onClick=[this]{requestRhythmPreview();};audio_.onClick=[this]{requestAudioSettings();};
    addAndMakeVisible(spanLabel_);addAndMakeVisible(spans_);
    spanLabel_.setText("Practice span",juce::dontSendNotification);spans_.setComponentID("practice-span");spans_.setTitle("Choose the whole admitted case or one authored source transfer cell; Practice Start remains explicit.");
    spans_.onChange=[this]{const auto id=spans_.getSelectedId();if(id<1||!selectPracticeCell(static_cast<std::uint32_t>(id-1)))spans_.setSelectedId(static_cast<int>(practiceCell_)+1,juce::dontSendNotification);};
    inventory_.setFont(juce::FontOptions{13.0f});inventory_.setJustificationType(juce::Justification::topLeft);inventory_.setComponentID("inventory");inventory_.setTitle("Read-only Development Preview catalog inventory and migration boundary.");
    for(auto* c:std::initializer_list<juce::Component*>{&title_,&inventory_,&summary_,&selectedCaseHeading_,&emptyCatalogState_,&searchLabel_,&search_,&clearSearch_,&searchStatus_,&lessons_,&variants_,&sections_,&back_,&mode_,&details_,&compactFretboard_,&text_,&diagnostics_,&tab_})addAndMakeVisible(c);
    lessons_.setComponentID("lessons");variants_.setComponentID("variants");sections_.setComponentID("sections");back_.setComponentID("back");mode_.setComponentID("mode");compactFretboard_.setComponentID("compact-fretboard-toggle");text_.setComponentID("instructions");tab_.setComponentID("tab");summary_.setComponentID("summary");diagnostics_.setComponentID("diagnostics");details_.setComponentID("details");metronome_.setComponentID("metronome");audio_.setComponentID("audio-settings");
    compactFretboard_.setTitle("Show the selected source event on the fretboard; return to TAB to select another event.");
    compactFretboard_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));
    compactFretboard_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));
    compactFretboard_.onClick=[this]{compactFretboardVisible_=!compactFretboardVisible_;refresh();centerSelectedFretboardMarkers();};
    lessons_.setTextWhenNothingSelected("Choose a control case");variants_.setTextWhenNothingSelected("Choose a source variant");setBackLabel("Back");
    lessons_.setTitle("Control case");variants_.setTitle("Source variant");sections_.setTitle("Instruction section");
    int id=1;for(const auto* label:{"Source instructions","Context & normalization","Assessment requirements","Offline resources","Variant details"})sections_.addItem(label,id++);sections_.setSelectedId(1,juce::dontSendNotification);
    for(auto* editor:{&text_,&diagnostics_}){editor->setMultiLine(true);editor->setReadOnly(true);editor->setScrollbarsShown(true);editor->setCaretVisible(false);}
    tab_.setCompact(true);tab_.showDetail(false);
    fretboard_.setComponentID("lesson-fretboard");
    fretboard_.onRequestBookContext=[this]{requestBookTheoryContext();};
    fretboardViewport_.setComponentID("lesson-fretboard-viewport");
    fretboardViewport_.setViewedComponent(&fretboard_, false);
    fretboardViewport_.setScrollBarsShown(true, false);
    fretboardHint_.setComponentID("lesson-fretboard-selection-hint");
    fretboardHint_.setTitle("Select a source note or chord in TAB to display its fretboard positions.");
    fretboardHint_.setText("Select a source note or chord in TAB to display its fretboard positions. Rests and unsupported events clear the board.",juce::dontSendNotification);
    fretboardHint_.setFont(juce::FontOptions{15.0f});
    fretboardHint_.setJustificationType(juce::Justification::centred);
    fretboardHint_.setColour(juce::Label::textColourId,appearance::colour(0xffb7c9d2));
    compactFretboardStatus_.setComponentID("compact-fretboard-status");
    compactFretboardStatus_.setFont(juce::FontOptions{13.0f,juce::Font::bold});
    compactFretboardStatus_.setColour(juce::Label::textColourId,appearance::colour(0xff6bd5cb));
    addAndMakeVisible(fretboardViewport_);addAndMakeVisible(fretboardHint_);addAndMakeVisible(compactFretboardStatus_);
    tab_.onSelection=[this](const std::string& eventId){projectSelectedSourceEvent(eventId);};
    text_.setFont(juce::FontOptions{juce::Font::getDefaultMonospacedFontName(),14.0f,juce::Font::plain});
    diagnostics_.setVisible(false);
    search_.onTextChange=[this]{refreshLessonChoices();refresh();};
    lessons_.onChange=[this]{const auto i=lessons_.getSelectedItemIndex();if(i>=0&&static_cast<std::size_t>(i)<visibleLessonIds_.size())selectLesson(visibleLessonIds_[static_cast<std::size_t>(i)]);};
    variants_.onChange=[this]{if(catalog_&&!item_.empty()){const auto& vs=catalog_->lesson(item_).variants;const auto i=variants_.getSelectedItemIndex();if(i>=0&&static_cast<std::size_t>(i)<vs.size())selectVariant(vs[static_cast<std::size_t>(i)].id);}};
    sections_.onChange=[this]{tabVisible_=false;compactFretboardVisible_=false;setupDetailsVisible_=false;refresh();};mode_.onClick=[this]{setupDetailsVisible_=false;tabVisible_=!tabVisible_;compactFretboardVisible_=false;refresh();};
    details_.onClick=[this]{diagnosticsVisible_=!diagnosticsVisible_;diagnostics_.setVisible(diagnosticsVisible_);resized();};
    back_.onClick=[this]{if(sourceDetail_){sourceDetail_=false;sourceStage(sourceReturnStage_);}else if(onBack)onBack();};refresh();
}
void LessonView::setBackLabel(const std::string& label){
    callerBackLabel_=label=="Back"?"Home":label;
    updateBackLabel();
}
void LessonView::updateBackLabel(){
    std::string label=callerBackLabel_;
    std::string title="Return to Home without changing the selected Learn case.";
    if(sourceDetail_){
        switch(sourceReturnStage_){
            case LearnStage::Levels:label="Levels";break;
            case LearnStage::Sublevels:label="Sublevels";break;
            case LearnStage::Exercises:label="Exercises";break;
            case LearnStage::Preview:label="Preview";break;
            case LearnStage::Queue:label="Queue";break;
            case LearnStage::Case:label="Case";break;
        }
        title="Return to "+label+" with the original source selection retained.";
    }else if(label=="Back to workbooks")title="Return to the original workbook library without changing the selected Learn case.";
    else if(label=="Back to Guided"&&!item_.empty()&&!variant_.empty())title="Return to the active Guided Session for "+item_+" / "+variant_+" without changing the selected Learn case.";
    back_.setButtonText(utf8(label));back_.setTitle(utf8(title));
}
void LessonView::presentInventory(){
    if(!catalog_)return;
    inventory_.setText(utf8(previewInventory(*catalog_,presentationLevel_,getWidth()<800,selectedCatalogScope_)),juce::dontSendNotification);
    inventory_.setDescription(utf8(previewInventory(*catalog_,presentationLevel_,false,selectedCatalogScope_)));
}
LessonView::~LessonView(){fretboardViewport_.setViewedComponent(nullptr,false);}
void LessonView::centerSelectedFretboardMarkers(){
    if(!compactFretboardVisible_)return;
    const auto markers=fretboard_.markerBounds();
    if(markers.isEmpty())return;
    const int height=fretboardViewport_.getMaximumVisibleHeight();
    fretboardViewport_.setViewPosition(0,std::max(0,markers.getCentreY()-height/2));
}
void LessonView::projectSelectedSourceEvent(const std::string& eventId){
    const auto setup=currentSetup?currentSetup():std::nullopt;
    presentationHandedness_=setup?setup->handedness:guitar::Handedness::Right;
    fretboard_.setHandedness(presentationHandedness_);
    bool consistent=false;
    if(catalog_&&!item_.empty()&&!variant_.empty()&&tab_.document()){
        const auto& model=catalog_->variant(item_,variant_).model;
        const auto* tabEvent=tab_.document()->event(eventId);
        const auto& tabSource=tab_.document()->source();
        const auto& modelSource=model->source();
        const auto modelEvent=std::find_if(modelSource.events.begin(),modelSource.events.end(),[&](const auto& event){return event.id==eventId;});
        consistent=tabEvent&&modelEvent!=modelSource.events.end()&&tabSource.itemId==modelSource.itemId&&tabEvent->id==modelEvent->id&&tabEvent->sourceRef==modelEvent->sourceRef;
        if(consistent)fretboard_.setEvent(model,eventId);
    }
    if(!consistent)fretboard_.setEvent(nullptr,eventId);
    if(consistent&&!fretboard_.markers().empty()){
        const auto& workbook=catalog_->lesson(item_).record.object().at("workbook_id").string();
        fretboard_.setApprovedBookContext(workbook==approvedTheoryWorkbook_?approvedTheoryText_:std::string{});
    }
    fretboardViewport_.setViewPosition(0,0);
    refresh();
    centerSelectedFretboardMarkers();
}
bool LessonView::requestBookTheoryContext(){
    if(!catalog_||item_.empty()||variant_.empty()||fretboard_.markers().empty())return false;
    const auto& workbook=catalog_->lesson(item_).record.object().at("workbook_id").string();
    approvedTheoryText_="Approved workbook explanation unavailable: verified context provider is unavailable.";
    try{if(onBookTheoryContext)approvedTheoryText_=onBookTheoryContext(workbook);}
    catch(const std::exception&){approvedTheoryText_="Approved workbook explanation unavailable: verified context could not be read.";}
    approvedTheoryWorkbook_=workbook;
    fretboard_.setApprovedBookContext(approvedTheoryText_);return true;
}

bool LessonView::load(const std::filesystem::path& path,const std::filesystem::path& extension,const std::filesystem::path& rung03,const std::filesystem::path& rung04,const std::filesystem::path& level006){
    std::vector<std::filesystem::path> installed;
    for(const auto& candidate:{extension,rung03,rung04,level006}){
        if(candidate.empty())break;
        installed.push_back(candidate);
    }
    return load(path,installed);
}
bool LessonView::load(const std::filesystem::path& path,const std::vector<std::filesystem::path>& installed){
    try{return installPreparedCatalog(lesson::Catalog::loadInstalled(path,installed),path.parent_path());}
    catch(const std::exception& e){practiceCell_=0;spans_.clear(juce::dontSendNotification);catalog_.reset();approvedTheoryWorkbook_.clear();approvedTheoryText_.clear();item_.clear();variant_.clear();visibleLessonIds_.clear();search_.clear();lessons_.clear(juce::dontSendNotification);variants_.clear(juce::dontSendNotification);tab_.setDocument(nullptr);fretboard_.setEvent(nullptr,{});inventory_.setText({},juce::dontSendNotification);diagnostic_=e.what();refresh();return false;}
}
bool LessonView::installPreparedCatalog(std::shared_ptr<const lesson::Catalog> candidate,const std::filesystem::path& resources,bool preserveSourceStage,bool selectedScope){
    if(!candidate||sourceQueueActive())return false;
    // Preview and a confirmed Ready queue already own exact admission snapshots.
    // Background publication cannot replace that owner before explicit selection reset.
    if(candidate!=catalog_&&hasRetainedSourcePlan())return false;
    if(candidate==catalog_){catalogReady_=true;catalogRefusal_.clear();selectedCatalogScope_=selectedScope;if(sourceIndex_&&!sourceSublevel_.empty())populateExercises();presentInventory();refresh();renderSourceStage();return true;}
    sourceResourceDirectory_=resources/"learn-source-index";catalog_=std::move(candidate);
    selectedCatalogScope_=selectedScope;
    catalogReady_=true;catalogRefusal_.clear();
    approvedTheoryWorkbook_.clear();approvedTheoryText_.clear();item_.clear();variant_.clear();search_.clear();
    refreshLessonChoices();presentInventory();diagnostic_.clear();
    const bool selected=selectLesson(catalog_->lessons().front().id,preserveSourceStage,false);
    if(sourceIndex_&&!sourceSublevel_.empty()){
        const auto first=sourceFirst_.getSelectedId(),last=sourceLast_.getSelectedId();populateExercises();
        sourceFirst_.setSelectedId(first,juce::dontSendNotification);sourceLast_.setSelectedId(last,juce::dontSendNotification);
    }
    renderSourceStage();return selected;
}
void LessonView::loadingStatus(const std::string& text){loadingStatus_=text;renderSourceStage();}
void LessonView::catalogPreparing(bool preparing){
    catalogPreparing_=preparing;
    if(preparing){catalogReady_=false;catalogRefusal_.clear();}
    if(sourceIndex_&&!sourceSublevel_.empty())populateExercises();
    renderSourceStage();
}
bool LessonView::selectFirstAdmitted(){
    if(!catalog_)return false;
    for(const auto& lesson:catalog_->lessons())for(const auto& variant:lesson.variants){
        try{
            const auto admission=catalog_->admit(lesson.id,variant.id);
            if(admission&&admission->practiceAllowed())return selectLesson(lesson.id,false,false)&&selectVariant(variant.id,false);
        }catch(const std::exception&){
            // Unsupported or incomplete records remain available for explicit inspection.
        }
    }
    return false;
}
void LessonView::refreshLessonChoices(){
    if(!catalog_)return;
    const auto query=folded(search_.getText().trim().toStdString());const auto current=item_;
    visibleLessonIds_.clear();lessons_.clear(juce::dontSendNotification);int row=1;
    for(const auto& l:catalog_->lessons()){
        std::string searchable=folded(l.title+" "+l.id+" "+l.record.object().at("workbook_id").string()+" "+storage::canonical(l.record.object().at("legacy_level")));
        for(const auto& ref:l.record.object().at("source_refs").array())searchable+=" "+folded(ref.string());
        for(const auto& v:l.variants){searchable+=" "+folded(v.label);for(const auto& ref:v.model->source().sourceRefs)searchable+=" "+folded(ref);}
        if(!query.empty()&&searchable.find(query)==std::string::npos)continue;
        std::string admissionStatus="none available";
        for(const auto& variant:l.variants){
            try{
                const auto admitted=catalog_->admit(l.id,variant.id);
                if(admitted&&admitted->practiceAllowed()){admissionStatus="some available";break;}
            }catch(const std::exception&){
                // Unsupported or incomplete variants remain visibly unavailable.
            }
        }
        lessons_.addItem(utf8("Level "+std::to_string(l.level)+" — "+l.title+" ["+l.id+"] | Workbook: "+l.record.object().at("workbook_id").string()+" | Revision: "+storage::canonical(l.record.object().at("content_revision"))+" | Case variants: "+admissionStatus),row++);
        visibleLessonIds_.push_back(l.id);
    }
    lessons_.setTextWhenNothingSelected(visibleLessonIds_.empty()?"No matching source-backed cases":"Choose a control case");
    if(const auto it=std::find(visibleLessonIds_.begin(),visibleLessonIds_.end(),current);it!=visibleLessonIds_.end())lessons_.setSelectedItemIndex(static_cast<int>(std::distance(visibleLessonIds_.begin(),it)),juce::dontSendNotification);
    else lessons_.setSelectedId(0,juce::dontSendNotification);
    if(query.empty())searchStatus_.setText(utf8(selectedCatalogScope_
        ? "Search the "+std::to_string(catalog_->lessons().size())+" currently prepared cases by title, ID, workbook, level, variant or source. Browse levels opens the complete exercise list. Reading does not start Practice."
        : "Search the retained "+std::to_string(catalog_->lessons().size())+"-case catalog by title, stable ID, workbook, level, variant label or source reference. Selection is read-only until explicit Practice."),juce::dontSendNotification);
    else if(visibleLessonIds_.empty())searchStatus_.setText(utf8("No source-backed lesson cases match \""+search_.getText().trim().toStdString()+"\". Clear Search to restore all retained cases. The prior selection "+current+" / "+variant_+" is retained, not a match. Practice is disabled until Clear Search restores it or you choose a matching case."),juce::dontSendNotification);
    else if(std::find(visibleLessonIds_.begin(),visibleLessonIds_.end(),current)==visibleLessonIds_.end()&&!current.empty())searchStatus_.setText(utf8(std::to_string(visibleLessonIds_.size())+" matching retained cases. Current selection "+current+" is outside this filter; no replacement was loaded. Practice is disabled for this retained target. Choose a matching retained case or Clear Search to restore the current selection."),juce::dontSendNotification);
    else searchStatus_.setText(utf8(std::to_string(visibleLessonIds_.size())+" matching retained source-backed case"+(visibleLessonIds_.size()==1?"":"s")+". Choose a retained case to inspect its source/TAB; Clear Search restores all retained cases. Search never changes the selected variant automatically."),juce::dontSendNotification);
}
bool LessonView::selectLesson(const std::string& id,bool preserveSourceStage,bool explicitSelection){
    inspectionQualifier_.clear();
    if(sourceQueueActive())return false;
    if(!catalog_)return false;
    if(!preserveSourceStage){sourceDetail_=false;sourceStage(LearnStage::Case);}
    const auto& all=catalog_->lessons();auto it=std::find_if(all.begin(),all.end(),[&](const auto& l){return l.id==id;});
    if(it==all.end()){diagnostic_="That lesson is not in the loaded content version; the current selection is retained.";refresh();return false;}
    item_=id;if(const auto visible=std::find(visibleLessonIds_.begin(),visibleLessonIds_.end(),id);visible!=visibleLessonIds_.end())lessons_.setSelectedItemIndex(static_cast<int>(std::distance(visibleLessonIds_.begin(),visible)),juce::dontSendNotification);else lessons_.setSelectedId(0,juce::dontSendNotification);
    variants_.clear(juce::dontSendNotification);int i=1;for(const auto& v:it->variants){
        auto label=v.label+" ["+v.id+"]";
        if(!v.model->source().sourceRefs.empty()){
            label+=" | Source: ";
            for(std::size_t ref=0;ref<v.model->source().sourceRefs.size();++ref){
                if(ref!=0)label+=" ";
                label+=v.model->source().sourceRefs[ref];
            }
        }
        label+=" | Content: "+catalog_->contentVersion(item_)+" | Revision: "+storage::canonical(it->record.object().at("content_revision"));
        label+=" | Workbook: "+it->record.object().at("workbook_id").string()+" | Level: "+storage::canonical(it->record.object().at("legacy_level"));
        variants_.addItem(utf8(label),i++);
    }
    tabVisible_=false;return selectVariant(it->variants.front().id,explicitSelection);
}
bool LessonView::selectVariant(const std::string& id,bool explicitSelection){
    if(!catalog_||item_.empty())return false;
    const auto& all=catalog_->lesson(item_).variants;auto it=std::find_if(all.begin(),all.end(),[&](const auto& v){return v.id==id;});
    if(it==all.end()){diagnostic_="That variant does not belong to the selected lesson; the current selection is retained.";refresh();return false;}
    variant_=id;explicitSelection_=explicitSelection;variants_.setSelectedItemIndex(static_cast<int>(std::distance(all.begin(),it)),juce::dontSendNotification);diagnostic_.clear();
    resetPracticeSpans();tab_.setDocument(std::make_shared<const tab::Document>(it->model));fretboard_.setEvent(it->model,{});refresh();return true;
}
std::shared_ptr<const lesson::Admission> LessonView::selectedAdmission() const {
    return practiceCell_ ? catalog_->admitCell(item_,variant_,practiceCell_) : catalog_->admit(item_,variant_);
}
void LessonView::resetPracticeSpans(){
    practiceCell_=0;spans_.clear(juce::dontSendNotification);
    spans_.addItem("Whole selected case",1);
    try {
        auto first=catalog_->admitCell(item_,variant_,1);
        spans_.clear(juce::dontSendNotification);spans_.addItem("Whole selected direction",1);
        for(std::uint32_t i=1;i<=5;++i)spans_.addItem(utf8(lessonSelectionLabel(i==1?*first:*catalog_->admitCell(item_,variant_,i))),static_cast<int>(i)+1);
    } catch(const std::exception&) { /* Unsupported cases expose no cutpoints. */ }
    spans_.setSelectedId(1,juce::dontSendNotification);
}
bool LessonView::selectPracticeCell(std::uint32_t ordinal){
    if(!catalog_||item_.empty()||variant_.empty())return false;
    try {
        if(ordinal>5)throw std::runtime_error("Choose Whole selected case or a listed source transfer cell; arbitrary cutpoints are unsupported.");
        auto selected=ordinal?catalog_->admitCell(item_,variant_,ordinal):catalog_->admit(item_,variant_);
        auto document=std::make_shared<const tab::Document>(selected->model());
        practiceCell_=ordinal;spans_.setSelectedId(static_cast<int>(ordinal)+1,juce::dontSendNotification);
        tab_.setDocument(std::move(document));fretboard_.setEvent(selected->model(),{});diagnostic_.clear();refresh();return true;
    }catch(const std::exception& e){diagnostic_=e.what();refresh();summary_.setText(utf8("Practice span unchanged. "+diagnostic_),juce::dontSendNotification);return false;}
}
bool LessonView::selectedCaseVisibleInSearch()const noexcept{
    return std::find(visibleLessonIds_.begin(),visibleLessonIds_.end(),item_)!=visibleLessonIds_.end();
}
bool LessonView::practiceExplicitSelection(const std::string& item,const std::string& variant){
    if(!catalogReady()||!catalog_)return false;
    try{const auto admission=catalog_->admit(item,variant);if(!admission||!admission->practiceAllowed())return false;}
    catch(const std::exception&){return false;}
    // A new explicit source choice may clear a prior filter; search alone never does.
    search_.setText({},false);refreshLessonChoices();
    return selectLesson(item)&&selectVariant(variant)&&practiceSelected();
}
bool LessonView::practiceSelected(){
    if(!selectedCaseVisibleInSearch()){summary_.setText("The retained case is outside the current search. Clear Search to restore it, or select a matching case before Practice. No activity was opened.",juce::dontSendNotification);return false;}
    if(!catalogReady()||!onPractice)return false;
    const auto text=tempo_.getText().trim();const int bpm=text.getIntValue();
    if(text.isEmpty()||text.length()>3||!text.containsOnly("0123456789")||bpm<20||bpm>300){summary_.setText("Choose a whole quarter-note tempo from 20 to 300 BPM. The current Practice selection is unchanged.",juce::dontSendNotification);return false;}
    try{auto selected=selectedAdmission();if(!selected->practiceAllowed()){summary_.setText(utf8(selected->description()),juce::dontSendNotification);return false;}
        std::string reason;if(!onPractice(std::move(selected),static_cast<std::uint16_t>(bpm),reason)){summary_.setText(utf8(reason.empty()?"Practice is unavailable. The original selection is retained; inspect Audio settings for the current activity.":reason+" The original Practice selection is retained."),juce::dontSendNotification);return false;}return true;
    }catch(const std::exception& e){diagnostic_=e.what();summary_.setText("Practice is unavailable for this selection. Read its source instructions and Variant details; no replacement has been loaded.",juce::dontSendNotification);diagnostics_.setText(utf8(diagnostic_),false);return false;}
}
bool LessonView::requestMetronome(){
    if(!onMetronome){
        summary_.setText("Metronome is unavailable from Learn until the existing Metronome page is connected. Return to Home and choose Metronome; no sound or practice activity was started.",juce::dontSendNotification);
        return false;
    }
    onMetronome();
    return true;
}
bool LessonView::requestRhythmPreview(){
    if(!onRhythmPreview){
        summary_.setText("Rhythm preview is unavailable from Learn until the existing shared Rhythm page is connected. Return to Home and choose Rhythm preview; no sound or practice activity was started.",juce::dontSendNotification);
        return false;
    }
    onRhythmPreview();
    return true;
}
bool LessonView::requestAudioSettings(){
    if(!onAudioSettings){
        summary_.setText("Audio settings are unavailable from Learn until the existing shared Audio page is connected. Return to Home and choose Audio settings; no sound or practice activity was started.",juce::dontSendNotification);
        return false;
    }
    onAudioSettings();
    return true;
}
void LessonView::refresh(){
    const bool ready=catalog_&&!item_.empty()&&!variant_.empty();
    for(auto* c:std::initializer_list<juce::Component*>{&lessons_,&variants_,&sections_,&mode_})c->setEnabled(ready);
    practice_.setButtonText(localProfileAvailable&&!localProfileAvailable()?"Create/open local profile":"Practice selected case");
    practice_.setEnabled(false);practice_.setWantsKeyboardFocus(false);practice_.setTitle("Open the selected admitted source-backed case in Practice; explicit Practice Start creates the Attempt; no curriculum credit is inferred.");tempo_.setEnabled(false);
    metronome_.setEnabled(true);rhythm_.setEnabled(true);audio_.setEnabled(true);
    spans_.setEnabled(ready&&spans_.getNumItems()>1);
    if(ready){
        const auto& variant=catalog_->variant(item_,variant_);
        const auto setup=currentSetup?currentSetup():std::nullopt;
        presentationHandedness_=setup?setup->handedness:guitar::Handedness::Right;
        fretboard_.setHandedness(presentationHandedness_);
        const auto setupNotice=lessonSetupNotice(*variant.model,setup);
        setupPrimaryNotice_=setupNotice.warning?"Guitar setup differs. Open Details for the authored requirements.\n":setupNotice.summary.find("unavailable")!=std::string::npos?"Guitar setup unavailable. Open Details.\n":setupNotice.summary.find("unspecified")!=std::string::npos?"Authored setup unspecified. Open Details.\n":"";setupSummary_.setText(utf8(setupNotice.summary),juce::dontSendNotification);setupSummary_.setColour(juce::Label::textColourId,juce::Colour{setupNotice.warning?0xffffcb77U:0xffb7c9d2U});setupDetails_.setText(utf8(setupNotice.details),false);
        std::string notice=variant.model->source().events.empty()?"Task instructions only. Reading creates no practice or completion credit.":"Selected case, not a complete workbook. Read the source and Variant details for playback limits.";
        if(variant.technicallyRenderable){const auto selected=selectedAdmission();if(selected->practiceAllowed()){
            practice_.setEnabled(catalogReady()&&selectedCaseVisibleInSearch()&&static_cast<bool>(onPractice));practice_.setWantsKeyboardFocus(practice_.isEnabled());tempo_.setEnabled(catalogReady());
            if(onPractice){
                const auto& lesson=catalog_->lesson(item_);
                std::string practiceTitle="Open admitted "+item_+" / "+variant_+" in Practice: "+lesson.title+" | Variant: "+variant.label;
                const auto& sourceRefs=lesson.record.object().at("source_refs").array();
                if(!sourceRefs.empty()){
                    practiceTitle+=" | Source refs:";
                    for(const auto& ref:sourceRefs)practiceTitle+=" "+ref.string();
                }
                practiceTitle+=(localProfileAvailable&&!localProfileAvailable()?"; create or open the ordinary private local profile, then return to this exact stopped case. No sound or Attempt starts.":"; explicit Practice Start creates the Attempt; no curriculum credit is inferred.");
                practice_.setTitle(juce::String::fromUTF8(practiceTitle.c_str()));
            }
            notice="Selected variant available for Practice. Runtime admission: admitted for Practice. One selected pass, count-in Off. The visible tempo is your selection, not an authored or prior clean tempo. Follow the source guidance below.\nSelected case only; this does not complete a workbook or award curriculum credit.\nNext action: read the authored instructions and TAB, then choose Practice selected case to enter Practice; selecting this case creates no Attempt or curriculum credit.";
            if(localProfileAvailable&&!localProfileAvailable())notice+="\nA local profile is required for saving. Create/open local profile retains this exact source and variant and returns to stopped preparation. No activity or audio starts.";
            if(practiceCell_)notice=lessonSelectionLabel(*selected)+". This cell is not a full direction or source task. Practice Start is explicit; selecting it creates no Attempt or curriculum credit. Follow the unchanged source guidance below.";
        }else {practice_.setTitle(juce::String::fromUTF8((std::string("Selected variant unavailable for Practice: runtime admission refused ")+item_+" / "+variant_+"; no Practice, Attempt or curriculum credit is created. Choose another variant or case in Learn.").c_str()));notice="Selected variant unavailable for Practice. Runtime admission refused this selection; no Practice or curriculum progress will be created.\n"+selected->description()+"\nNext action: choose another variant or case in Learn; this selection cannot enter Practice.";}}
        else if(!variant.model->source().events.empty()) {
        practice_.setTitle(juce::String::fromUTF8((std::string("Selected variant unavailable for Practice: runtime admission refused ")+item_+" / "+variant_+"; no Practice, Attempt or curriculum credit is created. Choose another variant or case in Learn.").c_str()));
        notice="Selected variant unavailable for Practice. Runtime admission refused this selection; no Practice or curriculum progress will be created.\nNext action: choose another variant or case in Learn; this selection cannot enter Practice.";
        }
        notice += "\nSource case: " + item_ + " / " + variant_ + "\nSource references:";
        for (const auto& ref : catalog_->lesson(item_).record.object().at("source_refs").array()) notice += " " + ref.string();
        notice += "\nWorkbook identity: " + catalog_->lesson(item_).record.object().at("workbook_id").string();
        notice += " | Level: " + storage::canonical(catalog_->lesson(item_).record.object().at("legacy_level"));
        notice += "\nContent version: " + catalog_->contentVersion(item_);
        notice += "\nContent revision: " + storage::canonical(catalog_->lesson(item_).record.object().at("content_revision"));
        notice += "\nAuthored instructions and TAB are read-only source content; reading them does not create Practice, progress or curriculum credit.";
        fullSummary_=notice;
        const bool admitted=variant.technicallyRenderable&&selectedAdmission()->practiceAllowed();
        compactSummary_=admitted?"Selected variant available for Practice; explicit Start creates the Attempt.":
            "Selected variant unavailable for Practice; choose another variant or case.";
        compactSummary_+="\nSource: "+item_+" / "+variant_+"\nRefs:";
        for(const auto& ref:catalog_->lesson(item_).record.object().at("source_refs").array())compactSummary_+=" "+ref.string();
        beginnerSummary_=compactSummary_.substr(0,compactSummary_.find("\n"))+"\nRead the instructions; no playing is verified. Reading creates no completion or curriculum credit.";
        compactSummary_+=admitted?"\nRead instructions/TAB; no completion or credit.":
            "\nReading creates no Attempt or curriculum credit.";
        if(admitted&&localProfileAvailable&&!localProfileAvailable()){
            const auto prerequisite=std::string{"Create/open a local profile to save results.\nYour exact case returns stopped; no sound or Attempt starts."};
            compactSummary_=prerequisite+"\n"+compactSummary_;beginnerSummary_=prerequisite;
        }
        if(practiceCell_){
            const auto partial=lessonSelectionLabel(*selectedAdmission())+". This cell is not a full direction or source task.\n";
            compactSummary_=partial+compactSummary_;beginnerSummary_=partial+beginnerSummary_;
        }
        summary_.setDescription(utf8(fullSummary_));
        presentSummary();
        const auto section=sections_.getSelectedId();
        text_.setMultiLine(true,section!=1); // Preserve aligned source TAB with horizontal scrolling.
        text_.setText(utf8(catalog_->text(item_,variant_,static_cast<lesson::Section>(section>=1&&section<=5?section-1:0))),false);
        mode_.setEnabled(!variant.model->source().events.empty());if(variant.model->source().events.empty())tabVisible_=false;
    }else{beginnerSummary_="Exercise list unavailable. Return Home, then choose Start learning to retry. No replacement was loaded.";fullSummary_="Lessons are unavailable. Rebuild or reinstall this preview with its bundled representative lesson resources. No replacement exercise has been loaded. Return to Home with Back, then choose Start learning to retry the retained preview load; other preview activities remain available through Back.";compactSummary_="Lesson resources unavailable. Return Home, then choose Start learning to retry. No replacement case loaded.";summary_.setDescription(utf8(fullSummary_));presentSummary();text_.setText("The local lesson bundle could not be loaded. Details identifies the missing or unsupported file. Return to Home with Back, then choose Start learning to retry the retained preview load. Other preview activities remain available through Back.",false);tabVisible_=false;}
    const bool hasCatalog=static_cast<bool>(catalog_);const bool projectionMode=tabVisible_&&!setupDetailsVisible_;const bool noEvent=tab_.selectedEvent().empty();const bool compactBoard=projectionMode&&compactFretboardVisible_;
    emptyCatalogState_.setVisible(!hasCatalog);emptyCatalogState_.setText("No source-backed Learn catalog loaded yet",juce::dontSendNotification);
    if(ready&&!selectedCaseVisibleInSearch()){
        practice_.setEnabled(false);practice_.setWantsKeyboardFocus(false);
        practice_.setTitle(utf8("Practice disabled: retained target "+item_+" / "+variant_+" is outside the current search. Clear Search restores this exact target; selecting a matching case changes it explicitly."));
    }
    searchLabel_.setVisible(hasCatalog&&!projectionMode);search_.setVisible(hasCatalog&&!projectionMode);clearSearch_.setVisible(hasCatalog&&!projectionMode);clearSearch_.setEnabled(hasCatalog&&!projectionMode&&!search_.getText().trim().isEmpty());searchStatus_.setVisible(hasCatalog&&!projectionMode);inventory_.setVisible(ready&&!projectionMode);
    selectedCaseHeading_.setVisible(ready);setupSummary_.setVisible(ready&&!projectionMode);setupButton_.setEnabled(ready&&!projectionMode);setupButton_.setVisible(!projectionMode);setupButton_.setButtonText(setupDetailsVisible_?"Hide setup details":"Show setup details");setupDetails_.setVisible(ready&&setupDetailsVisible_);
    tempoLabel_.setVisible(!projectionMode);tempo_.setVisible(!projectionMode);practice_.setVisible(!projectionMode);metronome_.setVisible(!projectionMode);rhythm_.setVisible(!projectionMode);audio_.setVisible(!projectionMode);spanLabel_.setVisible(!projectionMode);spans_.setVisible(!projectionMode);
    sections_.setVisible(ready);details_.setVisible(!projectionMode);text_.setVisible(!tabVisible_&&!setupDetailsVisible_);tab_.setVisible(projectionMode&&!compactBoard);
    compactFretboard_.setVisible(projectionMode);compactFretboard_.setEnabled(!noEvent);compactFretboard_.setButtonText(compactBoard?"Show TAB":"Show fretboard");
    fretboardViewport_.setVisible(projectionMode&&!noEvent&&compactBoard);fretboardHint_.setVisible(projectionMode&&noEvent&&compactBoard);mode_.setButtonText(tabVisible_?"Show instructions":"Show TAB");
    std::string boardStatus=presentationHandedness_==guitar::Handedness::Left?"Left-handed fretboard":"Right-handed fretboard";
    if(!fretboard_.markers().empty()){
        const auto& marker=fretboard_.markers().front();
        boardStatus+=" | "+marker.eventId+" | string "+std::to_string(marker.displayString)+
            " fret "+std::to_string(marker.relativeFret)+" "+marker.pitchName;
        if(fretboard_.markers().size()>1)boardStatus+=" | "+std::to_string(fretboard_.markers().size())+" tones";
    }else boardStatus+=" | no pitched source marker; return to TAB";
    compactFretboardStatus_.setText(utf8(boardStatus),juce::dontSendNotification);
    compactFretboardStatus_.setTitle(utf8(boardStatus+". "+fretboard_.statusSummary()));
    compactFretboardStatus_.setVisible(compactBoard);
    fullSummary_+="\n\nGuitar setup\n"+setupDetails_.getText().toStdString();compactSummary_=setupPrimaryNotice_+compactSummary_;beginnerSummary_=setupPrimaryNotice_+beginnerSummary_;
    if(!inspectionQualifier_.empty()){fullSummary_=inspectionQualifier_+"\n"+fullSummary_;compactSummary_=inspectionQualifier_+"\n"+compactSummary_;beginnerSummary_=inspectionQualifier_+"\n"+beginnerSummary_;summary_.setDescription(utf8(fullSummary_));}
    presentSummary();
    diagnostics_.setText(utf8(fullSummary_+"\n\n"+(diagnostic_.empty()?"Loaded selected source-backed record; source files and the local runtime-admission decision are available for inspection. Only the bounded supported selections can enter Practice. No source-task completion, Curriculum acceptance or progress is inferred.":diagnostic_)),false);
    if(learnStage_!=LearnStage::Case)renderSourceStage();
    resized();
}
void LessonView::paint(juce::Graphics& g){g.fillAll(appearance::colour(0xff10212c));}
void LessonView::resized(){
    if(learnStage_!=LearnStage::Case){layoutSourceStage();return;}
    const bool compact=getWidth()<800;
    const bool crossedFromCompact=layoutWasCompact_&&!compact;
    const bool crossedToCompact=!layoutWasCompact_&&compact;
    layoutWasCompact_=compact;
    const bool projectionMode=tabVisible_&&!setupDetailsVisible_;
    const bool compactBoard=projectionMode&&compactFretboardVisible_;
    presentInventory();
    presentSummary();
    tab_.setVisible(projectionMode&&!compactBoard);
    compactFretboard_.setVisible(projectionMode);
    compactFretboard_.setButtonText(compactBoard?"Show TAB":"Show fretboard");
    fretboardViewport_.setVisible(projectionMode&&!tab_.selectedEvent().empty()&&compactBoard);
    fretboardHint_.setVisible(projectionMode&&tab_.selectedEvent().empty()&&compactBoard);
    compactFretboardStatus_.setVisible(compactBoard);
    title_.setText(utf8(compact?"Learn — Development Preview catalog":"Learn — Source-backed Development Preview catalog"),juce::dontSendNotification);
    selectedCaseHeading_.setText(!item_.empty()&&!selectedCaseVisibleInSearch()?"RETAINED CASE - OUTSIDE SEARCH":compact?"SELECTED SOURCE CASE":"SELECTED CASE",juce::dontSendNotification);
    auto area=getLocalBounds().reduced(24);auto top=area.removeFromTop(36);back_.setBounds(top.removeFromRight(90));top.removeFromRight(8);sourceBrowse_.setBounds(top.removeFromRight(155));top.removeFromRight(8);presentationSelector_.setBounds(top.removeFromRight(200));top.removeFromRight(8);title_.setBounds(top);area.removeFromTop(compact?6:12);
    if(tabVisible_&&!setupDetailsVisible_){
        if(diagnostics_.isVisible()){
            diagnostics_.setBounds(area.removeFromBottom(58).reduced(0,4));
            area.removeFromBottom(8);
        }
        auto cases=area.removeFromTop(compact?54:34);
        if(compact){lessons_.setBounds(cases.removeFromTop(25));cases.removeFromTop(4);variants_.setBounds(cases.removeFromTop(25));}
        else{lessons_.setBounds(cases.removeFromLeft(cases.getWidth()/2));cases.removeFromLeft(12);variants_.setBounds(cases);}
        area.removeFromTop(compact?6:8);
        selectedCaseHeading_.setVisible(false);
        summary_.setTooltip(utf8(fullSummary_));presentSummary();
        summary_.setBounds(area.removeFromTop(36));area.removeFromTop(4);
        auto controls=area.removeFromTop(32);
        compactFretboard_.setBounds(controls.removeFromRight(150));controls.removeFromRight(8);
        details_.setVisible(true);details_.setBounds(controls.removeFromRight(82));controls.removeFromRight(8);
        mode_.setBounds(controls.removeFromRight(150));controls.removeFromRight(8);sections_.setBounds(controls);
        area.removeFromTop(8);
        tab_.setBounds(area);
        auto boardArea=area;compactFretboardStatus_.setBounds(boardArea.removeFromTop(compactBoard?26:0));
        fretboardViewport_.setBounds(boardArea);
        fretboard_.setSize(std::max(1,fretboardViewport_.getMaximumVisibleWidth()),std::max(480,fretboardViewport_.getMaximumVisibleHeight()));
        if(crossedFromCompact)fretboardViewport_.setViewPosition(0,0);
        if(crossedToCompact&&compactBoard)centerSelectedFretboardMarkers();
        fretboardHint_.setBounds(fretboardViewport_.getBounds().reduced(12).withHeight(92));
        setupDetails_.setBounds(area);
        return;
    }
    inventory_.setBounds(area.removeFromTop(compact?30:88));emptyCatalogState_.setBounds(inventory_.getBounds());area.removeFromTop(compact?4:8);
    auto searchRow=area.removeFromTop(compact?48:48);
    if(compact){
        auto statusRow=searchRow.removeFromTop(20);searchLabel_.setBounds(statusRow.removeFromLeft(100));statusRow.removeFromLeft(10);searchStatus_.setBounds(statusRow);
        searchRow.removeFromTop(4);auto inputRow=searchRow.removeFromTop(24);clearSearch_.setBounds(inputRow.removeFromRight(112));inputRow.removeFromRight(8);search_.setBounds(inputRow);
    }else{
        searchLabel_.setBounds(searchRow.removeFromLeft(100));searchRow.removeFromLeft(10);search_.setBounds(searchRow.removeFromLeft(280));searchRow.removeFromLeft(12);clearSearch_.setBounds(searchRow.removeFromLeft(120));searchRow.removeFromLeft(12);searchStatus_.setBounds(searchRow);
    }
    area.removeFromTop(compact?4:10);
    auto row=area.removeFromTop(compact?54:34);
    if(compact){lessons_.setBounds(row.removeFromTop(25));row.removeFromTop(4);variants_.setBounds(row.removeFromTop(25));}
    else{lessons_.setBounds(row.removeFromLeft(row.getWidth()/2));row.removeFromLeft(12);variants_.setBounds(row);}
    area.removeFromTop(compact?4:10);
    if(compact){
        auto tempoRow=area.removeFromTop(28);tempoLabel_.setBounds(tempoRow.removeFromLeft(174));tempo_.setBounds(tempoRow.removeFromLeft(76));area.removeFromTop(4);
        practice_.setBounds(area.removeFromTop(28));area.removeFromTop(4);
        auto toolRow=area.removeFromTop(28);const int toolWidth=(toolRow.getWidth()-16)/3;metronome_.setBounds(toolRow.removeFromLeft(toolWidth));toolRow.removeFromLeft(8);rhythm_.setBounds(toolRow.removeFromLeft(toolWidth));toolRow.removeFromLeft(8);audio_.setBounds(toolRow);
    }else{
        auto practiceRow=area.removeFromTop(32);tempoLabel_.setBounds(practiceRow.removeFromLeft(174));tempo_.setBounds(practiceRow.removeFromLeft(76));practiceRow.removeFromLeft(16);practice_.setBounds(practiceRow.removeFromLeft(210));practiceRow.removeFromLeft(8);metronome_.setBounds(practiceRow.removeFromLeft(118));practiceRow.removeFromLeft(8);rhythm_.setBounds(practiceRow.removeFromLeft(120));practiceRow.removeFromLeft(8);audio_.setBounds(practiceRow);
    }
    area.removeFromTop(compact?4:10);
    auto spanRow=area.removeFromTop(compact?28:32);spanLabel_.setBounds(spanRow.removeFromLeft(120));spans_.setBounds(spanRow);area.removeFromTop(compact?4:10);
    auto section=area.removeFromTop(compact?28:32);details_.setBounds(section.removeFromRight(90));section.removeFromRight(10);mode_.setBounds(section.removeFromRight(150));section.removeFromRight(10);sections_.setBounds(section);area.removeFromTop(compact?4:10);
    selectedCaseHeading_.setBounds(area.removeFromTop(compact?20:22));area.removeFromTop(compact?2:4);summary_.setBounds(area.removeFromTop(compact?72:170));area.removeFromTop(compact?4:8);
    if(diagnostics_.isVisible()){diagnostics_.setBounds(area.removeFromBottom(compact?60:80));area.removeFromBottom(compact?6:8);}
    auto setupRow=area.removeFromTop(compact?30:48);setupButton_.setBounds(setupRow.removeFromRight(compact?132:150).withHeight(compact?30:34));setupRow.removeFromRight(compact?8:10);setupSummary_.setBounds(setupRow);area.removeFromTop(compact?4:8);
    text_.setBounds(area);tab_.setBounds(area);setupDetails_.setBounds(area);fretboardViewport_.setBounds(area);fretboardHint_.setBounds(area);
}
void LessonView::configureSourceControls(){
    addChildComponent(sourcePanel_);addAndMakeVisible(sourceBrowse_);
    for(auto* c:std::initializer_list<juce::Component*>{&sourceHeading_,&sourceBreadcrumb_,&sourceFirstLabel_,&sourceLastLabel_,&sourceTempoLabel_,&sourceInfo_,&sourceBpm_,&sourceLevels_,&sourceSublevels_,&sourceMode_,&sourceFirst_,&sourceLast_,&previewItems_,&sourceVariants_,&sourceBack_,&sourceContinue_,&sourcePreview_,&sourceConfirm_,&sourceOpen_,&sourceNext_,&sourceRetry_,&sourceClear_,&sourceCase_,&sourceManual_})sourcePanel_.addChildComponent(c);
    sourceHeading_.setFont(juce::FontOptions{24.0f,juce::Font::bold});sourceFirstLabel_.setText("Start exercise",juce::dontSendNotification);sourceLastLabel_.setText("Stop exercise",juce::dontSendNotification);sourceTempoLabel_.setText("Quarter-note BPM",juce::dontSendNotification);sourceBpm_.setText("60",false);sourceBpm_.setComponentID("learn-source-bpm");sourceBpm_.setTitle(utf8("Selected quarter-note BPM20–300; opening Practice does not start sound"));
    sourceInfo_.setMultiLine(true,true);sourceInfo_.setReadOnly(true);sourceInfo_.setScrollbarsShown(true);sourceInfo_.setCaretVisible(false);sourceInfo_.setComponentID("learn-source-details");
    int focus=1;
    for(auto* c:std::initializer_list<juce::Component*>{&sourceBack_,&sourceLevels_,&sourceSublevels_,&sourceMode_,&sourceFirst_,&sourceLast_,&previewItems_,&sourceVariants_,&sourceContinue_,&sourcePreview_,&sourceConfirm_,&sourceOpen_,&sourceNext_,&sourceRetry_,&sourceClear_,&sourceCase_,&sourceManual_}){c->setWantsKeyboardFocus(true);c->setExplicitFocusOrder(focus++);}
    sourceLevels_.setComponentID("learn-source-level");sourceLevels_.setTitle("Choose one of 105 levels");
    sourceSublevels_.setComponentID("learn-source-sublevel");sourceSublevels_.setTitle("Choose a sublevel");
    sourceFirst_.setComponentID("learn-source-start");sourceFirst_.setTitle("First exercise, inclusive");
    sourceLast_.setComponentID("learn-source-stop");sourceLast_.setTitle("Last exercise, inclusive, in this sublevel");
    sourceMode_.setComponentID("learn-source-selection-mode");sourceMode_.addItem("One exercise",1);sourceMode_.addItem("Exercise range",2);sourceMode_.setSelectedId(1,juce::dontSendNotification);
    previewItems_.setComponentID("learn-preview-item");previewItems_.setTitle("Choose each queued exercise to review its exact admitted variant");sourceVariants_.setComponentID("learn-preview-variant");sourceVariants_.setTitle("Explicit variant choice for this source exercise");
    for(auto* button:{&sourceBack_,&sourceContinue_,&sourcePreview_,&sourceConfirm_,&sourceOpen_,&sourceNext_,&sourceRetry_,&sourceClear_,&sourceCase_,&sourceManual_,&sourceBrowse_}){button->setTitle(button->getButtonText());button->setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb));button->setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c));}
    sourceManual_.setComponentID("learn-source-manual-task");sourceManual_.setTitle("Open a reviewed source-bound manual guidance task; no Practice Session, Attempt or credit.");sourceOpen_.setComponentID("learn-queue-open");sourceNext_.setComponentID("learn-queue-next");sourceConfirm_.setComponentID("learn-queue-confirm");sourcePreview_.setComponentID("learn-source-preview");
    sourceBrowse_.onClick=[this]{showSourceHierarchy(true,true);};
    sourceLevels_.onChange=[this]{++sourceSelectionRevision_;++sourceGroupRevision_;if(onSourceGroupSelectionChanged)onSourceGroupSelectionChanged();const auto level=sourceLevels_.getSelectedId();if(sourceLevel_!=level){sourceSublevel_.clear();sourceFirst_.setSelectedId(0,juce::dontSendNotification);sourceLast_.setSelectedId(0,juce::dontSendNotification);}sourceLevel_=level;};
    sourceSublevels_.onChange=[this]{++sourceSelectionRevision_;++sourceGroupRevision_;if(onSourceGroupSelectionChanged)onSourceGroupSelectionChanged();if(sourceIndex_){const auto& subs=sourceIndex_->level(sourceLevel_).sublevels;const auto i=sourceSublevels_.getSelectedItemIndex();if(i>=0&&static_cast<std::size_t>(i)<subs.size()){const auto& key=subs[static_cast<std::size_t>(i)].key;if(sourceSublevel_!=key){sourceFirst_.setSelectedId(0,juce::dontSendNotification);sourceLast_.setSelectedId(0,juce::dontSendNotification);}sourceSublevel_=key;}}};
    sourceContinue_.onClick=[this]{++sourceSelectionRevision_;if(!sourceIndex_)return;if(learnStage_==LearnStage::Levels){populateSublevels();sourceStage(LearnStage::Sublevels);}else{prepareSourceGroup();populateExercises();sourceStage(LearnStage::Exercises);}};
    sourceMode_.onChange=[this]{++sourceSelectionRevision_;if(sourceMode_.getSelectedId()==1)sourceLast_.setSelectedId(sourceFirst_.getSelectedId(),juce::dontSendNotification);renderSourceStage();};
    sourceFirst_.onChange=[this]{++sourceSelectionRevision_;if(sourceMode_.getSelectedId()==1)sourceLast_.setSelectedId(sourceFirst_.getSelectedId(),juce::dontSendNotification);renderSourceStage();};sourceLast_.onChange=[this]{++sourceSelectionRevision_;renderSourceStage();};
    sourcePreview_.onClick=[this]{++sourceSelectionRevision_;buildSourcePreview();};
    previewItems_.onChange=[this]{refreshPreviewVariants();renderSourceStage();};
    sourceVariants_.onChange=[this]{const auto i=previewItems_.getSelectedItemIndex(),v=sourceVariants_.getSelectedItemIndex();if(i>=0&&v>=0&&static_cast<std::size_t>(i)<previewEntries_.size()&&static_cast<std::size_t>(v)<previewVariants_.size()){previewEntries_[static_cast<std::size_t>(i)].admission=previewVariants_[static_cast<std::size_t>(v)];renderSourceStage();}};
    sourceConfirm_.onClick=[this]{if(!isEnabled()||sourceQueueActive()||previewEntries_.empty())return;const auto& first=previewEntries_.front();const auto& last=previewEntries_.back();auto plan=navigation::planExercises(previewEntries_,{first.levelKey,first.sublevelKey,first.sourceExerciseKey,last.sourceExerciseKey});if(!plan.valid()){sourceMessage_=playerSourceMessage(plan.error());renderSourceStage();return;}exerciseQueue_=std::make_unique<navigation::ExerciseQueue>(std::move(plan));sourceMessage_=exerciseQueue_->size()>1?"Suite confirmed. Open Practice and choose Start for the first exercise. Each naturally completed exercise saves and the next starts automatically. Review only completed exercises together once at the end.":"Queue confirmed. Open each exercise explicitly; Practice Start and Save remain separate.";sourceStage(LearnStage::Queue);};
    sourceOpen_.onClick=[this]{if(!exerciseQueue_||queuePending_)return;if(queueOwned_||exerciseQueue_->phase()==navigation::ExerciseQueuePhase::Open){if(onQueueReturn)onQueueReturn();return;}const auto value=sourceBpm_.getText().trim();const int bpm=value.getIntValue();if(value.isEmpty()||!value.containsOnly("0123456789")||bpm<20||bpm>300){queueStatus("Choose a quarter-note tempo20–300 before opening.");return;}std::string reason;if(!onQueueOpen||!onQueueOpen(*exerciseQueue_,static_cast<std::uint16_t>(bpm),reason))queueStatus(reason.empty()?"Practice queue is unavailable.":reason);};
    sourcePanel_.addAndMakeVisible(sourceClear_);sourceClear_.setComponentID("learn-queue-clear");sourceClear_.setWantsKeyboardFocus(true);
    sourceClear_.onClick=[this]{if(onClearQueue)onClearQueue();};
    sourceNext_.onClick=[this]{std::string reason;if(!onQueueNext||!onQueueNext(reason))queueStatus(reason.empty()?"Save the current result before Next.":reason);};
    sourceRetry_.onClick=[this]{std::string reason;if(!onQueueRetry||!onQueueRetry(reason))queueStatus(reason.empty()?"No Session operation can be retried.":reason);};
    sourceBack_.onClick=[this]{if(sourceQueueActive()){queueStatus("Resolve the current exercise and Session before changing the source selection.");return;}if(learnStage_==LearnStage::Levels){if(onBack)onBack();}else if(learnStage_==LearnStage::Sublevels||learnStage_==LearnStage::Exercises){++sourceGroupRevision_;if(onSourceGroupSelectionChanged)onSourceGroupSelectionChanged();sourceStage(learnStage_==LearnStage::Sublevels?LearnStage::Levels:LearnStage::Sublevels);}else sourceStage(LearnStage::Exercises);};
    sourceManual_.onClick=[this]{
        if(sourceQueueActive())return;
        const auto* row=selectedSourceRow();if(!row)return;
        const auto& source=row->source.sourceExerciseKey;
        if(onManualTaskAvailable&&onManualTaskAvailable(source)){
            if(onManualTaskOpen&&onManualTaskOpen(source))return;
        }else if(onManualTaskCanPrepare&&onManualTaskCanPrepare(source)&&onManualTaskPrepare){
            onManualTaskPrepare(source);return;
        }
        sourceMessage_="No reviewed manual task is available for this source row.";renderSourceStage();
    };
    sourceCase_.onClick=[this]{
        if(sourceQueueActive())return;
        if(!catalog_){sourceMessage_="Practice catalog is still preparing. Please wait or return Home; no exercise was replaced.";renderSourceStage();return;}
        const auto* row=selectedSourceRow();if(!row){sourceMessage_="Choose an exercise before inspecting its Practice selection.";renderSourceStage();return;}
        auto choices=learn::choices(*row,*catalog_);
        if(!choices.empty()){
            auto choice=choices.front();
            if(learnStage_==LearnStage::Preview){const auto i=previewItems_.getSelectedItemIndex();if(i>=0&&static_cast<std::size_t>(i)<previewEntries_.size()&&previewEntries_[i].admission){const auto& previous=*previewEntries_[i].admission;const auto exact=std::find_if(choices.begin(),choices.end(),[&](const auto& c){return c==previous;});if(exact!=choices.end())choice=*exact;}}
            const auto from=learnStage_;
            if(selectLesson(choice.itemId)&&selectVariant(choice.variantId)){sourceDetail_=true;sourceReturnStage_=from;updateBackLabel();return;}
        }
        for(const auto& binding:row->bindings)if(!binding.exact){
            for(const auto& variant:binding.variants){
                try{const auto admitted=catalog_->admit(binding.itemId,variant);
                    if(!admitted||admitted->identity().object().at("package_sha256").string()!=binding.packageHash)continue;
                    const auto from=learnStage_;
                    if(selectLesson(binding.itemId)&&selectVariant(variant)){
                        sourceDetail_=true;sourceReturnStage_=from;
                        inspectionQualifier_="Supplemental / larger case inspection. Original exercise remains unavailable for exact Practice.";refresh();return;
                    }
                }catch(const std::exception&){} // Retain unavailable source row and prior selection.
            }
        }
        sourceMessage_="This exact exercise cannot enter Practice. Read its original instructions or choose another available exercise; no replacement or admission was created.";renderSourceStage();
    };

}
const learn::Exercise* LessonView::selectedSourceRow() const {
    if(learnStage_==LearnStage::Preview&&!previewRows_.empty()){
        const auto i=previewItems_.getSelectedItemIndex();
        if(i>=0&&static_cast<std::size_t>(i)<previewRows_.size())return previewRows_[static_cast<std::size_t>(i)];
    }
    if(learnStage_==LearnStage::Exercises&&sourceIndex_&&!sourceSublevel_.empty()){
        const auto& sub=sourceIndex_->sublevel(sourceLevel_,sourceSublevel_);
        const auto i=sourceFirst_.getSelectedItemIndex();
        if(i>=0&&static_cast<std::size_t>(i)<sub.exercises.size())return &sourceIndex_->exercises()[sub.exercises[static_cast<std::size_t>(i)]];
    }
    return nullptr;
}
bool LessonView::loadSourceIndex(const std::filesystem::path& directory){
    if(sourceQueueActive())return false;
    previewRows_.clear();previewEntries_.clear();previewVariants_.clear();exerciseQueue_.reset();sourceBpm_.setText(juce::String(defaultBpm_),false);sourceSublevel_.clear();sourceReturnStage_=LearnStage::Levels;
    if(learnStage_!=LearnStage::Case)learnStage_=LearnStage::Levels;
    sourceLevels_.clear(juce::dontSendNotification);
    try{return installPreparedSourceIndex(learn::SourceIndex::load(directory));}
    catch(const std::exception& error){sourceIndex_.reset();sourceMessage_=std::string{"Source index unavailable: "}+error.what();return false;}
}
bool LessonView::installPreparedSourceIndex(std::shared_ptr<const learn::SourceIndex> candidate){
    if(!candidate||sourceQueueActive())return false;
    if(candidate==sourceIndex_)return true;
    // Preview and Ready queues retain pointers into their verified source index.
    // Replacement must go through explicit selection reset, never publication.
    if(!previewRows_.empty()||exerciseQueue_)return false;
    sourceIndex_=std::move(candidate);sourceLevels_.clear(juce::dontSendNotification);
    for(const auto& level:sourceIndex_->levels())sourceLevels_.addItem(utf8("Level "+std::to_string(level.number)+" — "+level.title),level.number);
    sourceLevels_.setSelectedId(sourceLevel_,juce::dontSendNotification);sourceMessage_.clear();renderSourceStage();return true;
}
bool LessonView::sourceQueueActive()const{return queueOwned_||queuePending_||(exerciseQueue_&&exerciseQueue_->phase()==navigation::ExerciseQueuePhase::Open);}
bool LessonView::showSourceLevel(int level){
    if(!sourceIndex_||sourceQueueActive())return false;
    sourceIndex_->level(level); // Exact reviewed hierarchy, no invented groups.
    previewRows_.clear();previewEntries_.clear();previewVariants_.clear();exerciseQueue_.reset();sourceBpm_.setText(juce::String(defaultBpm_),false);
    sourceLevel_=level;sourceSublevel_.clear();sourceFirst_.setSelectedId(0,juce::dontSendNotification);sourceLast_.setSelectedId(0,juce::dontSendNotification);
    sourceLevels_.setSelectedId(level,juce::dontSendNotification);++sourceSelectionRevision_;++sourceGroupRevision_;
    if(onSourceGroupSelectionChanged)onSourceGroupSelectionChanged();
    populateSublevels();sourceMessage_.clear();sourceStage(LearnStage::Sublevels);return true;
}
void LessonView::showSourceHierarchy(bool prepareIndex,bool browseLevels){if(prepareIndex&&!sourceIndex_&&!sourceResourceDirectory_.empty())loadSourceIndex(sourceResourceDirectory_);if(sourceQueueActive()){sourceStage(LearnStage::Queue);return;}sourceStage(browseLevels||sourceReturnStage_==LearnStage::Case?LearnStage::Levels:sourceReturnStage_);}
void LessonView::sourceStage(LearnStage stage){
    learnStage_=stage;
    if(stage!=LearnStage::Case)sourceReturnStage_=stage;
    for(int i=0;i<getNumChildComponents();++i){
        auto* c=getChildComponent(i);
        if(c!=&sourcePanel_)c->setVisible(stage==LearnStage::Case);
    }
    // The optional footer follows the user's explicit choice, not the generic
    // Case visibility loop. Returning through the hierarchy retains that choice.
    diagnostics_.setVisible(stage==LearnStage::Case&&diagnosticsVisible_);
    sourcePanel_.setVisible(stage!=LearnStage::Case);
    presentationSelector_.setVisible(true);
    if(stage==LearnStage::Case)refresh();else renderSourceStage();
    resized();
}
void LessonView::populateSublevels(){
    const auto previous=sourceSublevel_;
    sourceSublevels_.clear(juce::dontSendNotification);
    if(!sourceIndex_)return;
    const auto& level=sourceIndex_->level(sourceLevel_);
    int id=1,selected=0;
    for(const auto& sub:level.sublevels){
        sourceSublevels_.addItem(utf8(sub.label+" ("+std::to_string(sub.exercises.size())+" exercises)"),id);
        if(sub.key==previous)selected=id;
        ++id;
    }
    if(selected==0&&!level.sublevels.empty())selected=1;
    sourceSublevels_.setSelectedId(selected,juce::dontSendNotification);
    sourceSublevel_=selected==0?std::string{}:level.sublevels[static_cast<std::size_t>(selected-1)].key;
}
std::string LessonView::sourceAvailability(const learn::Exercise& row)const{
    if(catalogPreparing_&&!row.bindings.empty())return "Preparing selected exercise Practice…";
    if(!row.bindings.empty()&&!catalogRefusal_.empty())return "Practice verification refused";
    if(!row.bindings.empty()&&!catalogReady_)return "Choose this sublevel to verify Practice";
    if(catalog_)return learn::availability(row,*catalog_);
    return row.bindings.empty()?"No exact Practice mapping; see exercise activity":"Choose this sublevel to verify Practice";
}
void LessonView::prepareSourceGroup(){
    if(!onPrepareSourceGroup||!sourceIndex_||sourceSublevel_.empty()||sourceQueueActive())return;
    // Open sublevel is an explicit new selection. Publication alone never resets
    // a Preview or a confirmed Ready queue owned by the previous selection.
    previewRows_.clear();previewEntries_.clear();previewVariants_.clear();exerciseQueue_.reset();sourceBpm_.setText(juce::String(defaultBpm_),false);
    previewItems_.clear(juce::dontSendNotification);sourceVariants_.clear(juce::dontSendNotification);
    sourceMessage_.clear();
    std::vector<lesson::SelectedCatalogStore::Request> requests;
    std::set<std::pair<std::string,std::string>> seen;
    for(const auto i:sourceIndex_->sublevel(sourceLevel_,sourceSublevel_).exercises)
        for(const auto& binding:sourceIndex_->exercises()[i].bindings)
            if(seen.emplace(binding.itemId,binding.packageHash).second)
                requests.push_back({binding.itemId,binding.packageHash});
    onPrepareSourceGroup(requests,++sourceGroupRevision_);
}
void LessonView::populateExercises(){
    const auto first=sourceFirst_.getSelectedId(),last=sourceLast_.getSelectedId();
    sourceFirst_.clear(juce::dontSendNotification);sourceLast_.clear(juce::dontSendNotification);
    if(!sourceIndex_||sourceSublevel_.empty())return;
    int id=1;
    for(auto i:sourceIndex_->sublevel(sourceLevel_,sourceSublevel_).exercises){
        const auto& row=sourceIndex_->exercises()[i];
        const auto label=std::to_string(row.source.sourceOrder)+". "+hiddenSevenLearnerLabel(row.source.sourceExerciseKey,row.label)+" — "+sourceAvailability(row);
        sourceFirst_.addItem(utf8(label),id);sourceLast_.addItem(utf8(label),id++);
    }
    const auto retained=[id](int old){return old>0&&old<id?old:(id>1?1:0);};
    sourceFirst_.setSelectedId(retained(first),juce::dontSendNotification);
    sourceLast_.setSelectedId(sourceMode_.getSelectedId()==1?sourceFirst_.getSelectedId():retained(last),juce::dontSendNotification);
}
void LessonView::buildSourcePreview(){
    if(!sourceIndex_||!catalog_)return;
    try{const auto& sub=sourceIndex_->sublevel(sourceLevel_,sourceSublevel_);const auto a=sourceFirst_.getSelectedItemIndex(),b=sourceMode_.getSelectedId()==1?a:sourceLast_.getSelectedItemIndex();if(a<0||b<0)throw std::runtime_error("Choose source exercise endpoints.");previewRows_=sourceIndex_->range(sourceLevel_,sourceSublevel_,sourceIndex_->exercises()[sub.exercises.at(static_cast<std::size_t>(a))].source.sourceExerciseKey,sourceIndex_->exercises()[sub.exercises.at(static_cast<std::size_t>(b))].source.sourceExerciseKey);previewEntries_.clear();previewItems_.clear(juce::dontSendNotification);int id=1;for(const auto* row:previewRows_){auto entry=row->source;const auto variants=learn::choices(*row,*catalog_);if(!variants.empty()){entry.mappingExtent=navigation::ExerciseMappingExtent::ExactSourceUnit;entry.admission=variants.front();}else if(std::any_of(row->bindings.begin(),row->bindings.end(),[](const auto& bound){return !bound.exact;}))entry.mappingExtent=navigation::ExerciseMappingExtent::LargerSourceCase;previewEntries_.push_back(std::move(entry));previewItems_.addItem(utf8(hiddenSevenLearnerLabel(row->source.sourceExerciseKey,row->label)),id++);}previewItems_.setSelectedId(1,juce::dontSendNotification);sourceMessage_="Review the displayed initial variant for every item. You may change each item here before confirming. No Practice Session or Attempt exists yet.";refreshPreviewVariants();sourceStage(LearnStage::Preview);}
    catch(const std::exception& e){sourceMessage_=e.what();renderSourceStage();}
}
void LessonView::refreshPreviewVariants(){sourceVariants_.clear(juce::dontSendNotification);previewVariants_.clear();const auto i=previewItems_.getSelectedItemIndex();if(!catalog_||i<0||static_cast<std::size_t>(i)>=previewRows_.size())return;previewVariants_=learn::choices(*previewRows_[static_cast<std::size_t>(i)],*catalog_);int id=1;for(const auto& v:previewVariants_)sourceVariants_.addItem(utf8(catalog_->variant(v.itemId,v.variantId).label),id++);const auto& selected=previewEntries_[static_cast<std::size_t>(i)].admission;if(selected){for(std::size_t j=0;j<previewVariants_.size();++j)if(previewVariants_[j]==*selected)sourceVariants_.setSelectedId(static_cast<int>(j+1),juce::dontSendNotification);}sourceVariants_.setTextWhenNothingSelected("No exact admitted variant for this source exercise");}
void LessonView::queueStatus(const std::string& message,bool pending){sourceMessage_=playerSourceMessage(message);queuePending_=pending;sourceStage(LearnStage::Queue);}
std::string LessonView::playerSourceMessage(std::string message)const{
    for(const auto* row:previewRows_){const auto& key=row->source.sourceExerciseKey;std::size_t offset=0;while(!key.empty()&&(offset=message.find(key,offset))!=std::string::npos){const auto safe=hiddenSevenLearnerLabel(row->source.sourceExerciseKey,row->label);message.replace(offset,key.size(),safe);offset+=safe.size();}}
    return message;
}
void LessonView::refreshQueueControls(){if(learnStage_==LearnStage::Queue)renderSourceStage();}
void LessonView::renderSourceStage(){
    if(learnStage_==LearnStage::Case)return;
    for(int i=0;i<getNumChildComponents();++i)if(getChildComponent(i)!=&sourcePanel_&&getChildComponent(i)!=&presentationSelector_)getChildComponent(i)->setVisible(false);
    sourcePanel_.setVisible(true);
    // Apply only final visibility. Hiding a still-visible control gives away its focus.
    std::vector<juce::Component*> visible;
    const auto show=[&](juce::Component& component){visible.push_back(&component);};
    if(exerciseQueue_&&learnStage_==LearnStage::Queue)show(sourceClear_);
    show(sourceHeading_);show(sourceBreadcrumb_);show(sourceInfo_);show(sourceBack_);
    sourceHeading_.setText(utf8("Learn — exercises"),juce::dontSendNotification);
    sourceBreadcrumb_.setText(utf8("105 levels"+(learnStage_==LearnStage::Levels?std::string{}:" / Level "+std::to_string(sourceLevel_))+(learnStage_==LearnStage::Levels||sourceSublevel_.empty()||!sourceIndex_?std::string{}:" / "+sourceIndex_->sublevel(sourceLevel_,sourceSublevel_).label)),juce::dontSendNotification);
    // A retained Preview or queue does not describe the Levels screen. Keep
    // its message for resume, and retain index failures and loading diagnostics.
    std::string information=(learnStage_==LearnStage::Levels&&sourceIndex_?std::string{}:sourceMessage_)
        +(loadingStatus_.empty()?std::string{}:"\n\n"+loadingStatus_);
    std::string sessionDescription;
    if(!sourceIndex_)information+=catalogPreparing_?"\nPreparing the exercise list. No exercise has been selected.":"\nThe exercise list is not ready. No substitute exercise was selected.";
    if(learnStage_==LearnStage::Levels){show(sourceLevels_);show(sourceContinue_);sourceContinue_.setButtonText("Open level");information+="\nChoose a level, sublevel and exercise. Preparation does not start Practice. Exercises that cannot enter Practice remain visible.";}
    if(learnStage_==LearnStage::Sublevels){show(sourceSublevels_);show(sourceContinue_);sourceContinue_.setButtonText("Open sublevel");}
    if(learnStage_==LearnStage::Exercises){show(sourceFirstLabel_);show(sourceLastLabel_);for(auto* c:std::initializer_list<juce::Component*>{&sourceMode_,&sourceFirst_,&sourceLast_,&sourcePreview_,&sourceCase_,&sourceManual_})show(*c);sourceLast_.setEnabled(sourceMode_.getSelectedId()==2);if(sourceIndex_&&!sourceSublevel_.empty()){const auto& sub=sourceIndex_->sublevel(sourceLevel_,sourceSublevel_);const auto i=sourceFirst_.getSelectedItemIndex();if(i>=0){const auto& row=sourceIndex_->exercises()[sub.exercises.at(static_cast<std::size_t>(i))];information+="\n\n"+hiddenSevenLearnerLabel(row.source.sourceExerciseKey,row.label)+"\n"+sourceAvailability(row);if(presentationLevel_==presentation::Level::Developer)information+="\n"+hiddenSevenLearnerLocator(row.source.sourceExerciseKey,row.locator);}}}
    if(learnStage_==LearnStage::Preview){for(auto* c:std::initializer_list<juce::Component*>{&previewItems_,&sourceVariants_,&sourceConfirm_,&sourceCase_,&sourceManual_})show(*c);information+="\n\nInclusive selection (separate Session and Attempt per item):";for(std::size_t i=0;i<previewRows_.size();++i){const auto& entry=previewEntries_[i];information+="\n"+std::to_string(i+1)+". "+hiddenSevenLearnerLabel(previewRows_[i]->source.sourceExerciseKey,previewRows_[i]->label)+" — "+(entry.admission?catalog_->variant(entry.admission->itemId,entry.admission->variantId).label:"UNAVAILABLE");}if(!previewEntries_.empty()){const auto& a=previewEntries_.front();const auto& b=previewEntries_.back();const auto planned=navigation::planExercises(previewEntries_,{a.levelKey,a.sublevelKey,a.sourceExerciseKey,b.sourceExerciseKey});sourceConfirm_.setEnabled(planned.valid());if(!planned.valid())information+="\n\nCannot confirm: "+playerSourceMessage(planned.error());}}
    if(learnStage_==LearnStage::Queue&&exerciseQueue_){show(sourceTempoLabel_);show(sourceBpm_);sourceBpm_.setEnabled(!sourceQueueActive());show(sourceOpen_);show(sourceNext_);show(sourceRetry_);const auto phase=exerciseQueue_->phase();sourceOpen_.setButtonText(queueOwned_||phase==navigation::ExerciseQueuePhase::Open?"Return to current Practice":"Open exercise in Practice");sourceOpen_.setEnabled(!queuePending_&&(queueOwned_||phase==navigation::ExerciseQueuePhase::Ready||phase==navigation::ExerciseQueuePhase::Open));sourceNext_.setEnabled(!queuePending_&&onQueueCanNext&&onQueueCanNext());sourceNext_.setButtonText(onQueueNextLabel?utf8(onQueueNextLabel()):"Next after Save and cleanup");sourceRetry_.setEnabled(!queuePending_);sourceRetry_.setButtonText(onQueueRetryLabel?utf8(onQueueRetryLabel()):"Check original Session operation");sourceRetry_.setTitle(sourceRetry_.getButtonText()+"; retained request identity and payload are unchanged. No replacement operation is created.");information+="\n\nQueue "+std::to_string(std::min(exerciseQueue_->position()+1,exerciseQueue_->size()))+" / "+std::to_string(exerciseQueue_->size());if(const auto* entry=exerciseQueue_->current())information+="\n"+hiddenSevenLearnerLabel(previewRows_.at(exerciseQueue_->position())->source.sourceExerciseKey,previewRows_.at(exerciseQueue_->position())->label)+"\nVariant: "+catalog_->variant(entry->admission->itemId,entry->admission->variantId).label;else information+="\nQueue finished. Saved history remains unchanged; no curriculum credit was inferred.";if(exerciseQueue_->activeLaunch())sessionDescription="Session "+exerciseQueue_->activeLaunch()->sessionId+"; source "+(hiddenSevenMotifOrdinal(exerciseQueue_->activeLaunch()->exercise.sourceExerciseKey)?std::string("selected motif listening task"):exerciseQueue_->activeLaunch()->exercise.sourceExerciseKey);information+=exerciseQueue_->size()>1?"\nChoose Start explicitly for the first exercise. Each naturally completed exercise saves and the next starts automatically. One final review covers only completed exercises. Stop is not discard.":"\nNext is enabled only after Save and cleanup, or cancellation of a never-started preparation. Stop is not discard. Practice Start remains explicit.";}
    // Derive the annotation from the retained launch, including an empty value
    // after confirmed close/Next. Do not publish unchanged accessibility values.
    const auto description=utf8(sessionDescription);
    if(sourceInfo_.getDescription()!=description)sourceInfo_.setDescription(description);
    const auto* selectedManual=selectedSourceRow();
    sourceManual_.setEnabled(!sourceQueueActive()&&selectedManual&&
        ((onManualTaskAvailable&&onManualTaskAvailable(selectedManual->source.sourceExerciseKey))||
         (onManualTaskCanPrepare&&onManualTaskCanPrepare(selectedManual->source.sourceExerciseKey))));
    for(auto* button:{&sourceContinue_,&sourceOpen_,&sourceNext_})button->setTitle(button->getButtonText());
    sourceContinue_.setEnabled(sourceIndex_&&sourceLevels_.getSelectedId()>0);sourcePreview_.setEnabled(sourceIndex_&&catalog_&&catalogReady_&&!catalogPreparing_&&!sourceQueueActive());sourceCase_.setEnabled(catalog_&&catalogReady_&&!catalogPreparing_&&selectedSourceRow()&&!sourceQueueActive());sourceBack_.setEnabled(!sourceQueueActive());if(sourceInfo_.getText()!=utf8(information))sourceInfo_.setText(utf8(information),false);for(int i=0;i<sourcePanel_.getNumChildComponents();++i){auto* c=sourcePanel_.getChildComponent(i);c->setVisible(std::find(visible.begin(),visible.end(),c)!=visible.end());}
    layoutSourceStage();
}
void LessonView::layoutSourceStage(){
    sourcePanel_.setBounds(getLocalBounds());auto area=sourcePanel_.getLocalBounds().reduced(getWidth()<800?16:24);auto head=area.removeFromTop(38);sourceBack_.setBounds(head.removeFromRight(90));head.removeFromRight(8);presentationSelector_.setBounds(head.removeFromRight(200));head.removeFromRight(8);sourceHeading_.setBounds(head);sourceBreadcrumb_.setBounds(area.removeFromTop(30));
    const auto row=[&](juce::Component& c){if(c.isVisible()){area.removeFromTop(8);c.setBounds(area.removeFromTop(34));}};
    for(auto* c:std::initializer_list<juce::Component*>{&sourceLevels_,&sourceSublevels_,&sourceMode_})row(*c);
    const auto labelled=[&](juce::Label& label,juce::Component& control){if(control.isVisible()){area.removeFromTop(8);auto line=area.removeFromTop(34);label.setBounds(line.removeFromLeft(150));control.setBounds(line);}};
    labelled(sourceFirstLabel_,sourceFirst_);labelled(sourceLastLabel_,sourceLast_);row(previewItems_);row(sourceVariants_);labelled(sourceTempoLabel_,sourceBpm_);
    auto bottom=area.removeFromBottom(learnStage_==LearnStage::Queue?162:124);
    for(auto* c:std::initializer_list<juce::Component*>{&sourceContinue_,&sourcePreview_,&sourceConfirm_,&sourceOpen_,&sourceNext_,&sourceRetry_,&sourceClear_,&sourceCase_,&sourceManual_})if(c->isVisible()){c->setBounds(bottom.removeFromTop(34));bottom.removeFromTop(6);}
    area.removeFromTop(10);sourceInfo_.setBounds(area);
}

}
