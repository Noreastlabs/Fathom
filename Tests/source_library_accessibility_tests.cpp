#include "desktop/SourceLibraryView.hpp"
#include "desktop/ReadOnlyTextEditor.hpp"
#include "read_only_text_peer_checks.hpp"
#include <CoreFoundation/CoreFoundation.h>
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>

// Exercise the real closed browser projection and JUCE AX handlers. There is no
// store, audio owner or replacement source catalog in this target.
namespace fathom::desktop {
struct SourceBrowseTestAccess {
    static std::string selectedOriginal(const SourceLibraryView& view) {
        const auto* workbook=view.selectedWorkbook();
        if(!view.library_||!workbook)throw std::runtime_error("Selected verified Original workbook missing");
        return view.library_->instructions(*workbook);
    }
    static std::string selectedIdentity(const SourceLibraryView& view) {
        const auto* task=view.selectedSourceTask();
        const auto* workbook=view.selectedWorkbook();
        return task&&workbook&&view.context_
            ?view.context_->sourceIdentity(view.context_->book(workbook->level),*task):std::string{};
    }
    static juce::String expectedRow(const SourceLibraryView& view,int row) {
        const auto& ref=view.taskRows_.at(static_cast<std::size_t>(row));
        const auto& book=view.context_->book(ref.level);
        return "Level "+juce::String(ref.level)+juce::String::fromUTF8(" · ")
            +juce::String::fromUTF8(view.context_->sourceTaskLabel(book,book.sourceTasks.at(ref.task)).c_str())
            +juce::String::fromUTF8(" · ")+juce::String::fromUTF8(book.title.c_str());
    }
};
}

namespace {
template<class T>T& control(juce::Component& root,const char* id) {
    auto* value=dynamic_cast<T*>(root.findChildWithID(id));
    if(!value)throw std::runtime_error(std::string{"Missing control: "}+id);
    return *value;
}
void pump() {CFRunLoopRunInMode(kCFRunLoopDefaultMode,0.005,true);}
bool settle(const std::function<bool()>& state) {
    // TextEditor text-change callbacks are asynchronous. Observe a queued
    // message boundary and the resulting public view state, not one timer tick.
    auto marker=std::make_shared<bool>(false);
    if(!juce::MessageManager::callAsync([marker]{*marker=true;}))return false;
    const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(2);
    while(std::chrono::steady_clock::now()<deadline){
        pump();
        if(*marker&&state())return true;
    }
    return false;
}
bool accessibleTitle(juce::AccessibilityHandler& root,const juce::String& title,int depth=0) {
    if(root.getTitle()==title)return true;
    if(depth>=12)return false;
    for(auto* child:root.getChildren())if(child&&accessibleTitle(*child,title,depth+1))return true;
    return false;
}
}

int main(int argc,char** argv) {
    int checks=0;
    std::ofstream trace;
    try {
        const bool retainedSearch=argc==4&&std::string(argv[3])=="--retained-search";
        if(argc!=3&&!retainedSearch)throw std::invalid_argument("Expected verified source-library resource path and a new absolute output directory");
        const std::filesystem::path resources{argv[1]},output{argv[2]};
        if(!resources.is_absolute()||!output.is_absolute()||std::filesystem::exists(output))
            throw std::invalid_argument("Resource and output paths must be absolute; output must not exist");
        std::filesystem::create_directories(output);
        trace.open(output/"checks.tsv");
        auto check=[&](bool result,const std::string& description){
            ++checks;trace<<(result?"PASS":"FAIL")<<'\t'<<description<<'\n';trace.flush();
            if(!result)throw std::runtime_error(description);
        };
        juce::ScopedJuceInitialiser_GUI gui;
        fathom::desktop::SourceLibraryView view;
        view.setSize(921,680);
        check(view.load(resources)&&view.bookContextAvailable(),"existing verified Original library and closed public context load");
        auto& search=control<juce::TextEditor>(view,"source-library-search");
        auto& books=control<juce::ComboBox>(view,"source-library-workbooks");
        auto& activities=control<juce::ListBox>(view,"source-library-source-tasks");
        auto& instructions=control<juce::TextEditor>(view,"source-library-original-text");
        auto& reveal=control<juce::TextButton>(view,"source-library-read-original-text");
        auto& open=control<juce::TextButton>(view,"source-library-open-source-task");
        if(retainedSearch){
            auto& clear=control<juce::TextButton>(view,"source-library-search-clear");
            auto& learn=control<juce::TextButton>(view,"source-library-open-learn");
            int calls=0;std::string called;
            view.onOpenInLearn=[&](const std::string& id){++calls;called=id;return true;};
            const int retained=books.getSelectedId();check(retained>0,"actual initial workbook selected");
            auto query=[&](const juce::String& value){search.setText(value,true);check(settle([&]{return search.getText()==value;}),"search callback settled");};
            query("not-a-retained-workbook");
            check(books.getNumItems()==0&&!learn.isEnabled()&&clear.isEnabled(),"no-match search has no launch target and explicit recovery");
            learn.onClick();check(calls==0,"direct Open callback cannot launch invisible workbook");
            auto image=view.createComponentSnapshot(view.getLocalBounds());auto stream=juce::File(juce::String::fromUTF8((output/"browser-no-match.png").c_str())).createOutputStream();juce::PNGImageFormat png;check(stream&&png.writeImageToStream(image,*stream),"no-match component image saved");stream.reset();
            clear.onClick();check(books.getSelectedId()==retained&&search.getText().isEmpty()&&learn.isEnabled(),"Clear search restores exact retained workbook and launch eligibility");
            query("Level 105");check(books.getSelectedId()==105,"cross-section query shows its actual visible workbook");
            clear.onClick();check(books.getSelectedId()==retained,"Clear search restores retained workbook and section after cross-section query without explicit choice");
            const int other=books.getItemId(books.getNumItems()-1);check(other>0&&other!=retained,"second actual workbook available");
            query("Level "+juce::String(other));check(books.getNumItems()>0,"matching public workbook query has visible results");
            books.setSelectedId(other,juce::sendNotificationSync);
            check(learn.getTitle().contains("Level "+juce::String(other)),"Open title identifies actual visible workbook");
            learn.onClick();check(calls==1&&!called.empty(),"explicit Open receives visible workbook identity once");
            query("not-a-retained-workbook");clear.onClick();check(books.getSelectedId()==other,"explicit changed selection becomes retained through a later no-match and clear");
            auto& volumes=control<juce::ComboBox>(view,"source-library-volume");auto& sections=control<juce::ComboBox>(view,"source-library-section");
            query("Level 105");volumes.setSelectedId(1,juce::sendNotificationSync);
            check(volumes.getSelectedId()==1&&search.getText().isEmpty()&&books.getSelectedId()>0,"explicit volume navigation during search is honored instead of restoring prior search section");
            const int nextSection=sections.getItemId(sections.getNumItems()-1);
            query("Level 105");volumes.setSelectedId(1,juce::sendNotificationSync);query("Level 7");
            sections.setSelectedId(nextSection,juce::sendNotificationSync);
            check(sections.getSelectedId()==nextSection&&search.getText().isEmpty()&&books.getSelectedId()>0,"explicit section navigation during search is honored instead of Clear Search restoration");
            image=view.createComponentSnapshot(view.getLocalBounds());stream=juce::File(juce::String::fromUTF8((output/"browser-restored.png").c_str())).createOutputStream();check(stream&&png.writeImageToStream(image,*stream),"restored component image saved");
            const auto future=output/"future-library-revision";std::filesystem::create_directory(future);std::ofstream(future/"handoff.json")<<"{\"schema\":\"unsupported-library-revision.fixture\"}";
            const auto callsBeforeRefusal=calls;check(!view.load(future)&&!learn.isEnabled()&&books.getNumItems()==0,"unaccepted source-library revision clears visible target and disables Open");
            learn.onClick();check(calls==callsBeforeRefusal,"failed source revision cannot silently reuse old workbook identity");
            std::ofstream(output/"summary.json")<<"{\"checks\":"<<checks<<",\"nativePeer\":false,\"databaseAccess\":false}\n";
            std::cout<<"PASS "<<checks<<" retained workbook search checks\n";return 0;
        }
        // JUCE publishes native handlers only for components with a window
        // handle. Attach the existing test peer before querying native AX.
        view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);
        view.setVisible(true);view.toFront(true);pump();
        check(view.getPeer()!=nullptr&&view.isShowing(),"native browser peer is visible before keyboard and AX queries");
        auto* searchAX=search.getAccessibilityHandler();
        auto* booksAX=books.getAccessibilityHandler();
        auto* textAX=instructions.getAccessibilityHandler();
        check(searchAX&&searchAX->getTitle()=="Search workbooks", "search has an explicit native AX name independent of placeholder");
        check(searchAX->getDescription().contains("Original text and answers are not searched"),"native search description preserves public-only search scope");
        check(searchAX->getHelp()==search.getTooltip()&&searchAX->getHelp().contains("Original text and answers are not searched"),
              "native search help retains the complete public-only scope separately from its title");
        check(booksAX&&booksAX->getTitle()=="Selected workbook"&&booksAX->getValueInterface()
              &&booksAX->getValueInterface()->getCurrentValueAsString()==books.getText(),"workbook AX names field and retains actual selected level/title value");
        check(textAX&&textAX->getTextInterface()&&textAX->getTextInterface()->isReadOnly()
              &&textAX->getTitle()=="Workbook context instructions", "permitted instructions expose a named read-only native AX text region");
        check(reveal.getTooltip().contains("no-chart")&&control<juce::TextButton>(view,"source-library-open-pdf").getTooltip().contains("no-chart"),"explicit Original text/PDF actions retain disclosure warning in help");
        auto* model=activities.getListBoxModel();
        check(model&&model->getNumRows()>1,"representative authored section has source rows");
        const auto first=fathom::desktop::SourceBrowseTestAccess::expectedRow(view,0);
        const auto second=fathom::desktop::SourceBrowseTestAccess::expectedRow(view,1);
        check(model->getNameForRow(0)==first&&model->getNameForRow(1)==second&&first!=second,
              "representative rows expose distinct exact public workbook/source-unit labels rather than Row N");
        check(model->getNameForRow(-1).isEmpty()&&model->getNameForRow(model->getNumRows()).isEmpty(),"invalid virtual rows expose no fabricated identity");
        check(model->getTooltipForRow(0)==first,"elided painted row retains complete same label in tooltip");
        int availabilityChecks=0,activityCalls=0;
        view.onManualTaskAvailable=[&](const std::string&){++availabilityChecks;return false;};
        view.onManualTaskOpen=[&](const std::string&){++activityCalls;return false;};
        activities.selectRow(0);
        const auto firstIdentity=fathom::desktop::SourceBrowseTestAccess::selectedIdentity(view);
        const auto publicText=instructions.getText();
        check(!firstIdentity.empty()&&!open.isEnabled(),"representative selected row retains real owned source identity and closed runtime action");
        search.grabKeyboardFocus();
        check(juce::Component::getCurrentlyFocusedComponent()==&search,"search is keyboard reachable");
        auto traverser=view.createKeyboardFocusTraverser();
        const auto order=traverser->getAllComponents(&view);
        const auto searchAt=std::find(order.begin(),order.end(),&search);
        const auto rowsAt=std::find(order.begin(),order.end(),&activities);
        const auto textAt=std::find(order.begin(),order.end(),&instructions);
        check(searchAt!=order.end()&&rowsAt!=order.end()&&textAt!=order.end()&&searchAt<rowsAt&&rowsAt<textAt,
              "focus traversal reaches search, source rows and read-only instructions in the explicit browse order");
        activities.grabKeyboardFocus();
        check(juce::Component::getCurrentlyFocusedComponent()==&activities,"source rows receive keyboard focus");
        check(view.getPeer()->handleKeyPress(juce::KeyPress{juce::KeyPress::downKey}),"native focused list handles Down selection");
        const auto secondIdentity=fathom::desktop::SourceBrowseTestAccess::selectedIdentity(view);
        check(activities.getSelectedRow()==1&&!secondIdentity.empty()&&secondIdentity!=firstIdentity,
              "keyboard selection resolves the next existing exact source identity");
        check(activityCalls==0&&!open.isEnabled()&&instructions.getText()==publicText&&availabilityChecks>0,
              "keyboard selection neither opens a source activity, reveals Original text nor bypasses availability");
        auto* listAX=activities.getAccessibilityHandler();
        check(listAX&&listAX->getTitle()=="Workbook source activities"&&accessibleTitle(*listAX,second),
              "native ListBox row accessibility publishes the actual selected public label");
        search.setText("zzzz-no-public-workbook-match",true);
        check(settle([&]{return books.getNumItems()==0&&model->getNumRows()==0&&!open.isEnabled();}),"empty search clears source row projection and leaves runtime action closed");
        search.setText("Level 1",true);
        check(settle([&]{return books.getSelectedId()==1&&model->getNumRows()>1&&model->getNameForRow(0)==first;}),
              "search result restoration reuses exact existing public row names");
        // Reuse the fixed Level77 original-reader case from the frozen prose matrix.
        search.setText("Level 77",true);
        check(settle([&]{return books.getSelectedId()==77&&model->getNumRows()>1;}),
              "exact public Level77 search selects the fixed populated original-reader workbook");
        const auto original=fathom::desktop::SourceBrowseTestAccess::selectedOriginal(view);
        const auto selectedIdentity=fathom::desktop::SourceBrowseTestAccess::selectedIdentity(view);
        const auto selectedRow=activities.getSelectedRow();const auto selectedBook=books.getSelectedId();
        const auto searchText=search.getText();const auto availableBeforeReading=availabilityChecks;
        check(reveal.isEnabled()&&bool(reveal.onClick),"selected verified workbook retains its explicit Original-text action");
        reveal.onClick();
        check(instructions.getText().toStdString()==original&&instructions.getTitle()=="Original workbook text",
              "explicit Original-text action displays the selected verified original bytes");
        reveal.grabKeyboardFocus();
        check(juce::Component::getCurrentlyFocusedComponent()==&reveal&&view.getPeer()->handleKeyPress(juce::KeyPress{juce::KeyPress::tabKey})
              &&juce::Component::getCurrentlyFocusedComponent()==&instructions,"peer Tab reaches the original reader from its explicit reveal control");
        fathom::test::readingKeys(view,instructions,original,check);
        check(fathom::desktop::SourceBrowseTestAccess::selectedIdentity(view)==selectedIdentity
              &&activities.getSelectedRow()==selectedRow&&books.getSelectedId()==selectedBook&&search.getText()==searchText
              &&activityCalls==0&&availabilityChecks==availableBeforeReading&&!open.isEnabled(),
              "original-reader keys preserve workbook/source selection, editable search and closed activity availability");
        check(dynamic_cast<fathom::desktop::ReadOnlyTextEditor*>(&search)==nullptr&&!search.isReadOnly(),
              "Source search retains its editable JUCE editor type");
        view.removeFromDesktop();
        check(trace.good(),"bounded software check log is writable");
        std::ofstream summary(output/"summary.json");
        summary<<"{\"status\":\"PASS\",\"checks\":"<<checks
               <<",\"representativeRowNames\":2,\"profileConfigured\":false,\"audioConfigured\":false,\"originalRevealed\":true,\"originalWorkbookLevel\":77,\"peerReadingKeys\":true,\"physicalKeyboardOrSpokenOutputClaimed\":false}\n";
        summary.flush();
        if(!summary.good())throw std::runtime_error("Could not save bounded software summary");
        std::cout<<"PASS "<<checks<<" SourceLibrary native AX/keyboard checks; no profile, audio or learner credit\n";
        return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL "<<error.what()<<'\n';return 1;}
}
