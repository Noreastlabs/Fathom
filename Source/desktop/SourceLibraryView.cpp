#include "desktop/Appearance.hpp"
#include "desktop/SourceLibraryView.hpp"
#include "desktop/CurriculumBrowseHierarchy.hpp"
#include "desktop/SourceDataWorker.hpp"
#include <algorithm>
#include <cctype>
#include <stdexcept>
#include <sstream>

namespace fathom::desktop {
namespace {
juce::ThreadPool& browsePool() { return sourceDataPool(); }
struct BrowsePayload {
    std::optional<curriculum::SourceLibrary> library;
    std::optional<curriculum::BookContextSourceCatalog> context;
    juce::String status;
};
}
SourceLibraryView::SourceLibraryView() {
    setComponentID("source-library-view");
    setWantsKeyboardFocus(true);
    title_.setText("Original workbook library",juce::dontSendNotification);
    title_.setFont(juce::FontOptions{30.0f,juce::Font::bold});
    scope_.setText("Choose a curriculum volume and authored section. Browse installed source context and workbooks; browsing grants no progress credit. Optional curriculum content may be absent. Required external resources remain unsupplied.",juce::dontSendNotification);
    scope_.setColour(juce::Label::textColourId,appearance::colour(0xffa9bbc5));
    search_.setTextToShowWhenEmpty("Search level, title, or public topics",
        appearance::current()==setup::Appearance::Light?appearance::colour(0xffa9bbc5):juce::Colours::grey);
    search_.setComponentID("source-library-search");
    search_.setTitle("Search workbooks");
    search_.setDescription("Search by level, workbook title, or approved public topics across all curriculum volumes. Original text and answers are not searched.");
    search_.setTooltip(search_.getDescription());
    search_.onTextChange=[this]{refreshList();};
    clearSearch_.setComponentID("source-library-search-clear");
    clearSearch_.setTitle("Clear workbook search and restore the retained workbook selection.");
    clearSearch_.onClick=[this]{search_.setText({},false);refreshList();};
    volumes_.setComponentID("source-library-volume");
    volumes_.setTitle("Curriculum volume");
    volumes_.setDescription("Choose a curriculum volume. Changing volume clears the search and shows its authored sections.");
    volumes_.addItem(juce::String::fromUTF8("Volume 1 · Foundation and scales"),1);
    volumes_.addItem(juce::String::fromUTF8("Volume 2 · Harmony and advanced scales"),2);
    volumes_.addItem(juce::String::fromUTF8("Volume 3 · Applied musicianship"),3);
    volumes_.setSelectedId(1,juce::dontSendNotification);
    volumes_.onChange=[this]{search_.setText({},false);lastSearchEmpty_=true;refreshSections();refreshList();};
    sections_.setComponentID("source-library-section");
    sections_.setTitle("Authored curriculum section");
    sections_.onChange=[this]{search_.setText({},false);lastSearchEmpty_=true;refreshList();};
    refreshSections();
    workbooks_.setComponentID("source-library-workbooks");
    workbooks_.setTitle("Selected workbook");
    workbooks_.setDescription("Choose a workbook from the current section or search results. The selected value includes its level and title.");
    workbooks_.onChange=[this]{selectWorkbook();};
    selection_.setColour(juce::Label::textColourId,appearance::colour(0xff6bd5cb));
    text_.setMultiLine(true);
    text_.setReadOnly(true);
    text_.setScrollbarsShown(true);
    text_.setFont(juce::FontOptions{13.0f});
    text_.setComponentID("source-library-original-text");
    text_.setTitle("Workbook context instructions");
    text_.setDescription("Read-only instructions. Use the arrow keys, Page Up and Page Down to move through the text. Original text is opened only with Read original text.");
    text_.setText("Source context will appear here. Original text and PDF browsing are explicit choices.",false);
    status_.setColour(juce::Label::textColourId,appearance::colour(0xffa9bbc5));
    status_.setComponentID("source-library-status");
    back_.setButtonText("Back to Home");
    back_.setComponentID("source-library-back");
    back_.onClick=[this]{cancelLoading();if(onBack)onBack();};
    openPdf_.setButtonText("Open original PDF");
    openPdf_.setComponentID("source-library-open-pdf");
    openPdf_.setTooltip("Open the selected workbook's original PDF in your default viewer. It can reveal worked examples or answers; keep it closed during a no-chart or unfamiliar listening task.");
    openPdf_.setEnabled(false);
    openPdf_.onClick=[this]{
        const auto* workbook=selectedWorkbook();
        if(!library_||!workbook)return;
        try {
            const juce::File file{juce::String::fromUTF8(library_->originalPdf(*workbook).string().c_str())};
            if(!file.startAsProcess())throw std::runtime_error("The PDF viewer could not open this file.");
            status_.setText("Opened original PDF in your default viewer.",juce::dontSendNotification);
        } catch(const std::exception& error) {
            status_.setText(juce::String::fromUTF8(error.what()),juce::dontSendNotification);
        }
    };
    openLearn_.setButtonText("Open in Learn");
    openLearn_.setComponentID("source-library-open-learn");
    openLearn_.setEnabled(false);
    openLearn_.onClick=[this]{
        const auto* workbook=selectedWorkbook();
        if(!workbook)return;
        retainedWorkbookLevel_=workbook->level;
        if(!onOpenInLearn||!onOpenInLearn(workbook->id))
            status_.setText("No Learn case is available for this workbook yet. Its original instructions remain browseable here.",juce::dontSendNotification);
    };
    sourceTasks_.setComponentID("source-library-source-tasks");
    sourceTasks_.setTitle("Workbook source activities");
    sourceTasks_.setDescription("Each row names its workbook and source unit. Use Up and Down to select a row, then Tab to the separate Open source activity or Verify and open source activity button. Selection alone does not open an activity or grant credit.");
    sourceTasks_.setWantsKeyboardFocus(true);
    sourceTasks_.setModel(this);sourceTasks_.setRowHeight(28);
    sourceTasks_.setColour(juce::ListBox::backgroundColourId,appearance::colour(0xff142833));
    openSourceTask_.setComponentID("source-library-open-source-task");
    openSourceTask_.setButtonText("Open source activity");openSourceTask_.setEnabled(false);
    openSourceTask_.onClick=[this]{
        const auto* task=selectedSourceTask();const auto* workbook=selectedWorkbook();
        if(!context_||!task||!workbook)return;
        const auto source=context_->sourceIdentity(context_->book(workbook->level),*task);
        if(onManualTaskAvailable&&onManualTaskAvailable(source)){
            if(!onManualTaskOpen||!onManualTaskOpen(source))status_.setText("This source activity cannot open yet. Finish or release the current activity first.",juce::dontSendNotification);
        }else if(onManualTaskCanPrepare&&onManualTaskCanPrepare(source)&&onManualTaskPrepare)onManualTaskPrepare(source);
        else
            status_.setText("This source activity is unavailable, or the current activity still needs to be finished or released.",juce::dontSendNotification);
    };
    showOriginal_.setButtonText("Read original text");
    showOriginal_.setComponentID("source-library-read-original-text");
    showOriginal_.setTooltip("Explicitly reveal the selected workbook's original text. It can disclose answers or preparation; keep it hidden during a no-chart or unfamiliar listening task.");
    showOriginal_.setEnabled(false);
    showOriginal_.onClick=[this]{showOriginalText();};
    showContext_.setButtonText("Context instructions");
    showContext_.setComponentID("source-library-context-instructions");
    showContext_.setEnabled(false);
    showContext_.onClick=[this]{selectWorkbook();};
    for(auto* component:std::initializer_list<juce::Component*>{&volumes_,&sections_,&sourceTasks_,&openSourceTask_,&showOriginal_,&showContext_,&title_,&scope_,&search_,&clearSearch_,&workbooks_,&selection_,&text_,&status_,&back_,&openPdf_,&openLearn_})
        addAndMakeVisible(*component);
    // Keep navigation predictable without adding a keyboard activation route to
    // source rows: the existing, independently gated action button remains required.
    int focusOrder=1;
    for(auto* component:std::initializer_list<juce::Component*>{&volumes_,&sections_,&search_,&clearSearch_,&workbooks_,&sourceTasks_,&openSourceTask_,&showContext_,&showOriginal_,&text_,&back_,&openPdf_,&openLearn_}) {
        component->setWantsKeyboardFocus(true);
        component->setExplicitFocusOrder(focusOrder++);
    }
}

SourceLibraryView::~SourceLibraryView() {cancelLoading();sourceTasks_.setModel(nullptr);}
void SourceLibraryView::lookAndFeelChanged() {
    search_.setTextToShowWhenEmpty(search_.getTextToShowWhenEmpty(),
        appearance::current()==setup::Appearance::Light?appearance::colour(0xffa9bbc5):juce::Colours::grey);
}
bool SourceLibraryView::hasBackgroundWork(){return browsePool().getNumJobs()!=0;}
void SourceLibraryView::cancelLoading() {
    if(loadTicket_){loadTicket_->store(true);loadTicket_.reset();}
    if(activityTicket_){activityTicket_->store(true);activityTicket_.reset();}
    if(!library_)theoryInitializationAttempted_=false;
}
void SourceLibraryView::prepareActivity(const std::string& source,ActivityPreparation prepare,std::function<bool()> open){
    if(activityTicket_||!prepare||!context_)return;
    auto ticket=std::make_shared<std::atomic<bool>>(false);activityTicket_=ticket;
    openSourceTask_.setEnabled(false);
    status_.setText("Verifying this source activity. You can browse other exercises or return to Home.",juce::dontSendNotification);
    const juce::Component::SafePointer<SourceLibraryView> owner{this};
    browsePool().addJob([owner,ticket,source,prepare=std::move(prepare),open=std::move(open)]{
        std::function<void()> commit;juce::String error;
        if(ticket->load())return;
        try{commit=prepare(ticket);}catch(const std::exception& e){error=juce::String::fromUTF8(e.what());}
        if(ticket->load())return;
        juce::MessageManager::callAsync([owner,ticket,source,commit=std::move(commit),open,error]{
            if(!owner||ticket->load()||owner->activityTicket_!=ticket)return;
            owner->activityTicket_.reset();
            const auto* task=owner->selectedSourceTask();const auto* workbook=owner->selectedWorkbook();
            const auto current=owner->context_&&task&&workbook?owner->context_->sourceIdentity(owner->context_->book(workbook->level),*task):std::string{};
            if(current!=source){owner->status_.setText("Selection changed; the earlier activity preparation was discarded.",juce::dontSendNotification);owner->refreshSourceTaskAvailability();return;}
            if(!error.isEmpty()){owner->status_.setText("Source activity verification failed: "+error,juce::dontSendNotification);owner->refreshSourceTaskAvailability();return;}
            if(commit)commit();
            owner->refreshSourceTaskAvailability();
            if(!owner->onManualTaskAvailable||!owner->onManualTaskAvailable(source)||!open||!open())
                owner->status_.setText("This source activity is unavailable or still needs to be released. Original instructions remain available.",juce::dontSendNotification);
        });
    });
}
void SourceLibraryView::beginBrowse(const std::filesystem::path& resources) {
    if(loadTicket_&&theoryResources_==resources)return; // repeated click owns one job
    if(library_&&loadedBrowseResources_==resources){refreshList();return;}
    cancelLoading();theoryResources_=resources;theoryInitializationAttempted_=true;
    library_.reset();context_.reset();loadedBrowseResources_.clear();taskRows_.clear();sourceTasks_.updateContent();
    workbooks_.clear(juce::dontSendNotification);
    for(auto* control:std::initializer_list<juce::Component*>{&volumes_,&sections_,&search_,&clearSearch_,&workbooks_,&sourceTasks_,&openSourceTask_,&showOriginal_,&showContext_,&openPdf_,&openLearn_})control->setEnabled(false);
    text_.setText("Loading verified offline source context. You can return to Home while this loads.",false);
    status_.setText("Loading and verifying original sources and context...",juce::dontSendNotification);
    auto ticket=std::make_shared<std::atomic<bool>>(false);loadTicket_=ticket;
    const juce::Component::SafePointer<SourceLibraryView> owner{this};
    browsePool().addJob([resources,ticket,owner]{
        if(ticket->load())return;
        auto result=std::make_shared<BrowsePayload>();
        try {
            if(!std::filesystem::is_directory(resources))
                throw std::runtime_error("Optional workbook content is not installed. Return to Learn, then Home, to use Free play, User profile or Settings.");
            result->library=curriculum::SourceLibrary::load(resources,[ticket]{return ticket->load();});
            if(ticket->load())return;
            result->status="Original sources verified. Context unavailable; explicit source browsing remains available.";
            const auto root=resources.parent_path()/"book-context105";
            if(std::filesystem::exists(root)){
                try {result->context=curriculum::BookContextSourceCatalog::load(root,*result->library,[ticket]{return ticket->load();});
                    result->status="Original sources and closed context verified. External resources remain unsupplied; browsing grants no credit.";
                }catch(const std::exception& error){result->status="Source context unavailable: "+juce::String::fromUTF8(error.what());}
            }
            if(ticket->load())return;
        }catch(const std::exception& error){result->status="Library unavailable: "+juce::String::fromUTF8(error.what());}
        if(ticket->load())return;
        juce::MessageManager::callAsync([owner,ticket,result,resources]{
            if(!owner||ticket->load()||owner->loadTicket_!=ticket)return;
            owner->loadTicket_.reset();
            owner->library_=std::move(result->library);owner->context_=std::move(result->context);
            owner->contextStatus_=result->status;
            if(owner->library_)owner->loadedBrowseResources_=resources;
            owner->showLoadResult();
        });
    });
}
void SourceLibraryView::showLoadResult() {
    for(auto* control:std::initializer_list<juce::Component*>{&volumes_,&sections_,&search_,&clearSearch_,&workbooks_,&sourceTasks_})control->setEnabled(library_.has_value());
    if(library_)refreshList();
    else {
        taskRows_.clear();sourceTasks_.updateContent();workbooks_.clear(juce::dontSendNotification);
        for(auto* control:std::initializer_list<juce::Component*>{&openSourceTask_,&showOriginal_,&showContext_,&openPdf_,&openLearn_})control->setEnabled(false);
        text_.setText("Original workbooks are unavailable. Back returns to Learn; Home remains available for the other activities.",false);
    }
    status_.setText(contextStatus_,juce::dontSendNotification);
}
void SourceLibraryView::refreshSections() {
    sections_.clear(juce::dontSendNotification);int first=0;
    for(std::size_t i=0;i<browseSections.size();++i){const auto& s=browseSections[i];if(s.volume!=volumes_.getSelectedId())continue;
        const auto id=static_cast<int>(i)+1;sections_.addItem("Section "+juce::String{s.name},id);if(!first)first=id;}
    sections_.setSelectedId(first,juce::dontSendNotification);
}

bool SourceLibraryView::initializeVerifiedContext(const std::filesystem::path& installedResources) {
    theoryResources_=installedResources;theoryInitializationAttempted_=true;
    try {
        auto candidate=curriculum::SourceLibrary::load(installedResources); // full exact Original/hash validation
        library_=std::move(candidate);context_.reset();
        contextStatus_="Source context is unavailable. Use explicit original-source browsing; Learn remains separate.";
        const auto contextRoot=installedResources.parent_path()/"book-context105";
        if(std::filesystem::exists(contextRoot)) {
            try {context_=curriculum::BookContextSourceCatalog::load(contextRoot,*library_);
                contextStatus_="Closed source context and public instructions verified. This view supplies no recording, partner or progress credit.";
            } catch(const std::exception& error) {contextStatus_="Source context unavailable: "+juce::String::fromUTF8(error.what());}
        }
        return true;
    } catch(const std::exception& error) {
        library_.reset();context_.reset();contextStatus_="Library unavailable: "+juce::String::fromUTF8(error.what());return false;
    }
}

bool SourceLibraryView::ensureTheoryContext(const std::filesystem::path& installedResources) {
    if(theoryInitializationAttempted_)return installedResources==theoryResources_&&library_&&context_;
    return initializeVerifiedContext(installedResources)&&context_.has_value();
}

std::string SourceLibraryView::publicTheoryContext(const std::string& workbookId) const {
    if(!library_||!context_)return "Approved workbook explanation unavailable: verified original library/context is required.";
    const auto found=std::find_if(library_->workbooks().begin(),library_->workbooks().end(),[&](const auto& book){return book.id==workbookId;});
    if(found==library_->workbooks().end())return "Approved workbook explanation unavailable: original workbook identity is not owned by this library.";
    const auto& book=context_->book(found->level);
    if(book.workbookId!=found->id)return "Approved workbook explanation unavailable: context workbook identity differs.";
    std::ostringstream out;out << "Original workbook " << found->id << " / Level " << found->level << ".\n";
    bool any=false;
    for(const auto* card:context_->publicCards(book)) {
        if(card->externalResource)continue;
        any=true;out << card->id << " — " << card->title << "\n" << card->summary << "\n";
        for(const auto& paragraph:card->paragraphs)out << paragraph << "\n";
        for(const auto& excerpt:card->authoredPublicExcerpts)out << excerpt.text << "\n";
        out << "Public source references:";for(const auto& ref:card->publicSourceRefs)out << " " << ref;
        out << "\n" << card->attribution << "\n\n";
    }
    if(!any)out << "No approved bridge explanation is mapped to this original workbook.\n";
    out << "Book-approved context only; not selected tone root-register inference or task admission. Required external resources remain unsupplied; no Attempt, completion or credit.";
    return out.str();
}

bool SourceLibraryView::load(const std::filesystem::path& installedResources) {
    cancelLoading();
    // Explicit browser load retains full verification and menu/task availability checks.
    if(initializeVerifiedContext(installedResources)) {
        refreshList();
        status_.setText(context_?"105 original text/PDF pairs and closed source context verified. Required external resources are not supplied.":"105 original text and PDF pairs verified. Choose context or explicit original-source browsing.",juce::dontSendNotification);
        return true;
    }
    taskRows_.clear();sourceTasks_.updateContent();openSourceTask_.setEnabled(false);showOriginal_.setEnabled(false);showContext_.setEnabled(false);workbooks_.clear(juce::dontSendNotification);openPdf_.setEnabled(false);openLearn_.setEnabled(false);
    text_.setText("Original workbooks are unavailable. Learn and the existing Practice cases remain available.",false);
    status_.setText(contextStatus_,juce::dontSendNotification);return false;
}

bool SourceLibraryView::loadBookContext(const std::filesystem::path& closedPackage) {
    context_.reset();
    try {
        if(!library_)throw std::runtime_error("Verified original library is required.");
        auto candidate=curriculum::BookContextSourceCatalog::load(closedPackage,*library_);
        context_=std::move(candidate);
        contextStatus_="Closed source context and public instructions verified. This view supplies no recording, partner or progress credit.";
        selectWorkbook();
        return true;
    } catch(const std::exception& error) {
        contextStatus_="Source context unavailable: "+juce::String::fromUTF8(error.what());
        selectWorkbook();
        return false;
    }
}

std::size_t SourceLibraryView::workbookCount() const noexcept {return library_?library_->workbooks().size():0;}

const curriculum::SourceWorkbook* SourceLibraryView::selectedWorkbook() const {
    if(!library_)return nullptr;
    const int level=workbooks_.getSelectedId();
    if(level<1||level>static_cast<int>(library_->workbooks().size())||workbooks_.indexOfItemId(level)<0)return nullptr;
    return &library_->workbooks()[static_cast<std::size_t>(level-1)];
}

void SourceLibraryView::refreshList() {
    const int previous=workbooks_.getSelectedId();
    workbooks_.clear(juce::dontSendNotification);
    if(!library_)return;
    const auto query=search_.getText().trim().toLowerCase();
    if(!query.isEmpty()&&lastSearchEmpty_&&previous>0)retainedWorkbookLevel_=previous;
    const bool restoring=query.isEmpty()&&!lastSearchEmpty_;
    lastSearchEmpty_=query.isEmpty();
    clearSearch_.setEnabled(!query.isEmpty());
    auto levelText=query.toStdString();
    if(levelText.rfind("level ",0)==0)levelText.erase(0,6);
    int exactLevel=0;
    if(!levelText.empty()&&std::all_of(levelText.begin(),levelText.end(),[](unsigned char c){return std::isdigit(c)!=0;})){
        int parsed=0;
        for(const auto digit:levelText){parsed=parsed*10+(digit-'0');if(parsed>105)break;}
        if(parsed>=1&&parsed<=105)exactLevel=parsed;
    }
    const auto metadataMatches=context_?context_->searchBooks(query.toStdString()):std::vector<int>{};
    int first=0;
    if(restoring&&retainedWorkbookLevel_>0){
        const int retainedSection=browseSectionForLevel(retainedWorkbookLevel_);
        volumes_.setSelectedId(browseSections[static_cast<std::size_t>(retainedSection-1)].volume,juce::dontSendNotification);
        refreshSections();sections_.setSelectedId(retainedSection,juce::dontSendNotification);
    }
    const int section=sections_.getSelectedId();
    for(const auto& workbook:library_->workbooks()) {
        if(query.isEmpty()&&browseSectionForLevel(workbook.level)!=section)continue;
        const auto label=juce::String::fromUTF8(workbook.label.c_str());
        const auto item="Level "+juce::String(workbook.level)+" — "+label;
        if(exactLevel>0&&workbook.level!=exactLevel)continue;
        if(exactLevel==0&&!query.isEmpty()&&!item.toLowerCase().contains(query)
           &&std::find(metadataMatches.begin(),metadataMatches.end(),workbook.level)==metadataMatches.end())continue;
        workbooks_.addItem(item,workbook.level);
        if(first==0)first=workbook.level;
    }
    const int wanted=restoring?retainedWorkbookLevel_:previous;
    const int selected=wanted>0&&workbooks_.indexOfItemId(wanted)>=0?wanted:first;
    if(query.isEmpty())retainedWorkbookLevel_=selected;
    workbooks_.setSelectedId(selected,juce::dontSendNotification);
    if(selected>0){
        if(!query.isEmpty()){
            const int found=browseSectionForLevel(selected);volumes_.setSelectedId(browseSections[static_cast<std::size_t>(found-1)].volume,juce::dontSendNotification);
            refreshSections();sections_.setSelectedId(found,juce::dontSendNotification);
        }
        selectWorkbook(false);
    }else {selection_.setText(retainedWorkbookLevel_>0?"No matching workbook. Level "+juce::String(retainedWorkbookLevel_)+" is retained; Clear search restores it.":"No matching workbook",juce::dontSendNotification);text_.clear();taskRows_.clear();sourceTasks_.updateContent();openSourceTask_.setEnabled(false);openPdf_.setEnabled(false);openLearn_.setEnabled(false);showOriginal_.setEnabled(false);showContext_.setEnabled(false);}
}

void SourceLibraryView::selectWorkbook(bool explicitSelection) {
    const auto* workbook=selectedWorkbook();
    openPdf_.setEnabled(workbook!=nullptr);openLearn_.setEnabled(workbook!=nullptr);
    showOriginal_.setEnabled(workbook!=nullptr);showContext_.setEnabled(workbook!=nullptr);
    if(!library_||!workbook)return;
    if(explicitSelection)retainedWorkbookLevel_=workbook->level;
    openLearn_.setTitle("Open the currently visible Level "+juce::String(workbook->level)+" - "+juce::String::fromUTF8(workbook->label.c_str())+" ["+juce::String::fromUTF8(workbook->id.c_str())+"] in Learn. This does not start Practice.");
    refreshSourceTasks();
    selection_.setText("Level "+juce::String(workbook->level)+" · "+juce::String(workbook->lines)+" text lines · "+juce::String(workbook->pages)+" PDF pages",juce::dontSendNotification);
    try {
        text_.setTitle("Workbook context instructions");
        if(context_)text_.setText(juce::String::fromUTF8(context_->publicInstructions(context_->book(workbook->level)).c_str()),false);
        else text_.setText("Original sources remain available through Read original text or Open original PDF. They can disclose worked examples or preparation details; keep them hidden during a no-chart or unfamiliar listening task. Learn uses each task's own instructions and availability checks.",false);
        text_.setCaretPosition(0);
        status_.setText(contextStatus_,juce::dontSendNotification);
    } catch(const std::exception&) {
        text_.clear();context_.reset();
        status_.setText("Source context is unavailable. Explicit original-source browsing remains available.",juce::dontSendNotification);
    }
}

void SourceLibraryView::showOriginalText() {
    const auto* workbook=selectedWorkbook();
    if(!library_||!workbook)return;
    try {
        const auto original=library_->instructions(*workbook);
        text_.setTitle("Original workbook text");
        text_.setText(juce::String::fromUTF8(original.c_str()),false);text_.setCaretPosition(0);
        status_.setText("Original text opened explicitly. It can disclose answers or preparation; use the PDF for complete notation and diagrams.",juce::dontSendNotification);
    } catch(const std::exception& error) {
        text_.clear();status_.setText("Original text unavailable: "+juce::String::fromUTF8(error.what()),juce::dontSendNotification);
    }
}

const curriculum::BookSourceTask* SourceLibraryView::selectedSourceTask() const {
    const int selected=sourceTasks_.getSelectedRow();
    if(!context_||selected<0||static_cast<std::size_t>(selected)>=taskRows_.size())return nullptr;
    const auto& row=taskRows_[static_cast<std::size_t>(selected)];const auto& book=context_->book(row.level);
    if(row.task>=book.sourceTasks.size())return nullptr;
    return &book.sourceTasks[row.task];
}
void SourceLibraryView::refreshSourceTaskAvailability() {
    const auto* task=selectedSourceTask();const auto* workbook=selectedWorkbook();bool available=false,canPrepare=false;
    if(context_&&task&&workbook&&onManualTaskAvailable){
        try{available=onManualTaskAvailable(context_->sourceIdentity(context_->book(workbook->level),*task));}catch(const std::exception&){available=false;}
    }
    if(context_&&task&&workbook&&onManualTaskCanPrepare)canPrepare=onManualTaskCanPrepare(context_->sourceIdentity(context_->book(workbook->level),*task));
    openSourceTask_.setButtonText(available?"Open source activity":"Verify and open source activity");
    openSourceTask_.setEnabled(!activityTicket_&&((available&&static_cast<bool>(onManualTaskOpen))||(canPrepare&&static_cast<bool>(onManualTaskPrepare))));
}
void SourceLibraryView::refreshSourceTasks() {
    std::optional<TaskRow> previous;
    const auto selection=sourceTasks_.getSelectedRow();
    if(selection>=0&&static_cast<std::size_t>(selection)<taskRows_.size())previous=taskRows_[static_cast<std::size_t>(selection)];
    taskRows_.clear();openSourceTask_.setEnabled(false);
    const auto* workbook=selectedWorkbook();if(!context_||!workbook){sourceTasks_.updateContent();return;}
    int selected=-1,firstWorkbook=-1;
    for(const auto& book:context_->books()){
        if(workbooks_.indexOfItemId(book.level)<0)continue;
        for(std::size_t i=0;i<book.sourceTasks.size();++i){
            const int index=static_cast<int>(taskRows_.size());
            if(book.level==workbook->level&&firstWorkbook<0)firstWorkbook=index;
            if(previous&&previous->level==workbook->level&&previous->level==book.level&&previous->task==i)selected=index;
            taskRows_.push_back({book.level,i});
        }
    }
    sourceTasks_.updateContent();
    if(selected<0)selected=firstWorkbook;
    sourceTasks_.selectRow(selected,false,false);
    refreshSourceTaskAvailability();
}
int SourceLibraryView::getNumRows(){return static_cast<int>(taskRows_.size());}
juce::String SourceLibraryView::getNameForRow(int row) {
    if(!context_||row<0||static_cast<std::size_t>(row)>=taskRows_.size())return {};
    const auto& ref=taskRows_[static_cast<std::size_t>(row)];
    const auto& book=context_->book(ref.level);
    if(ref.task>=book.sourceTasks.size())return {};
    // This is the same closed public label used in the painted row, not raw
    // owner JSON, original instructions, answers or a new exercise identity.
    return "Level "+juce::String(ref.level)+juce::String::fromUTF8(" · ")
        +juce::String::fromUTF8(context_->sourceTaskLabel(book,book.sourceTasks[ref.task]).c_str())
        +juce::String::fromUTF8(" · ")+juce::String::fromUTF8(book.title.c_str());
}
juce::String SourceLibraryView::getTooltipForRow(int row) {return getNameForRow(row);}
void SourceLibraryView::paintListBoxItem(int row,juce::Graphics& g,int width,int height,bool selected){
    if(!context_||row<0||static_cast<std::size_t>(row)>=taskRows_.size())return;
    if(selected)g.fillAll(appearance::colour(0xff254a59));
    g.setColour(appearance::colour(0xffffffff));g.setFont(juce::FontOptions{13.0f});
    const auto label=getNameForRow(row);
    g.drawText(label,8,0,std::max(0,width-16),height,juce::Justification::centredLeft,true);
}
void SourceLibraryView::selectedRowsChanged(int row){
    if(activityTicket_){activityTicket_->store(true);activityTicket_.reset();}
    if(row<0||static_cast<std::size_t>(row)>=taskRows_.size()){refreshSourceTaskAvailability();return;}
    const auto level=taskRows_[static_cast<std::size_t>(row)].level;
    if(workbooks_.getSelectedId()!=level){workbooks_.setSelectedId(level,juce::dontSendNotification);selectWorkbook();}
    refreshSourceTaskAvailability();
}

void SourceLibraryView::resized() {
    const int x=40,w=getWidth()-80;
    title_.setBounds(x,30,w,44);
    scope_.setBounds(x,80,w,38);
    volumes_.setBounds(x,132,w/2-8,34);sections_.setBounds(x+w/2+8,132,w/2-8,34);
    search_.setBounds(x,178,std::max(100,w/3-116),34);clearSearch_.setBounds(x+std::max(100,w/3-116)+8,178,108,34);
    workbooks_.setBounds(x+w/3+16,178,w-w/3-16,34);
    selection_.setBounds(x,218,w,28);
    const int column=(w-16)/2;
    openSourceTask_.setBounds(x,252,column,30);
    showContext_.setBounds(x+column+16,252,column/2-4,30);
    showOriginal_.setBounds(x+column+16+column/2+4,252,column/2-4,30);
    sourceTasks_.setBounds(x,294,column,std::max(50,getHeight()-420));
    text_.setBounds(x+column+16,294,column,std::max(50,getHeight()-420));
    status_.setBounds(x,getHeight()-116,w,42);
    back_.setBounds(x,getHeight()-64,170,36);
    openPdf_.setBounds(x+184,getHeight()-64,190,36);
    openLearn_.setBounds(x+388,getHeight()-64,240,36);
}
} // namespace fathom::desktop
