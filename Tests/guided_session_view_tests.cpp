#include "desktop/GuidedSessionView.hpp"
#include "practice/AttemptCapture.hpp"
#include "practice/LessonAttempt.hpp"
#include "practice_capture_fixtures.hpp"

#include <CoreFoundation/CoreFoundation.h>
#include <atomic>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <thread>

using namespace fathom;

namespace fathom::desktop {
struct GuidedSessionViewTestAccess {
    static void stopTimer(GuidedSessionView& view) { view.stopTimer(); }
    static void pose(GuidedSessionView& view, const std::string& state) {
        view.running_=state=="running" || state=="unresolved";
        view.closed_=state=="stopped";
        view.unresolved_=state=="unresolved";
        view.closeUnresolved_=state=="unresolved";
        view.sessionId_=view.running_||view.closed_?"synthetic-guided-focus-pose":std::string{};
        view.refreshControls();
        view.status_.setText(juce::String("Synthetic ")+state+" keyboard pose; no profile, Session or Attempt was written.",juce::dontSendNotification);
        view.sessionSummary_.setText("Synthetic keyboard pose only; retained source plan unchanged and no saved outcome claimed.",juce::dontSendNotification);
    }
    static bool detached(const GuidedSessionView& view) { return view.store_==nullptr&&!view.future_; }
    static json::Value originalStart(const GuidedSessionView& view) {
        if(!view.originalCreate_)return nullptr;
        const auto& original=*view.originalCreate_;
        return json::Value::Object{{"operation",original.operation},{"utc",original.utc},{"timezone",original.timezone},
            {"seconds",json::Value::fromInteger(original.seconds)},{"plan",original.plan},{"owner",original.owner},
            {"status",json::Value::fromInteger(static_cast<int>(original.status))},{"code",original.errorCode},{"detail",original.errorDetail}};
    }
    static std::string source(const GuidedSessionView& view) { return view.firstItemId_+"/"+view.firstVariantId_; }
    static void linkSyntheticSummary(GuidedSessionView& view) {
        view.savedAttemptLinked_=true;
        view.refreshControls();
        view.resized();
        view.status_.setText("Synthetic linked-summary keyboard pose; no profile, Session or Attempt was written.",juce::dontSendNotification);
        view.sessionSummary_.setText("Synthetic linked-summary pose only; no saved outcome is claimed.",juce::dontSendNotification);
    }
    static void poseCatalogCritical(GuidedSessionView& view,const std::string& state) {
        view.stopTimer();
        if(state=="running"||state=="unresolved")pose(view,state);
        else if(state=="closed")pose(view,"stopped");
        else if(state=="busy")view.future_.emplace(std::future<storage::Reply>{},"synthetic-catalog-feedback-pending","");
        else if(state=="summary-unavailable")view.summaryUnavailable_=true;
        view.status_.setText(juce::String::fromUTF8(("Synthetic critical "+state+" status; no profile activity was created.").c_str()),juce::dontSendNotification);
    }
    static std::string lifecycle(const GuidedSessionView& view) {
        return storage::canonical(json::Value::Object{{"busy",view.busy()},{"running",view.running_},
            {"closed",view.closed_},{"unresolved",view.unresolved_},{"close_unresolved",view.closeUnresolved_},
            {"summary_unavailable",view.summaryUnavailable_},{"session",view.sessionId_},{"plan",view.planValue_},
            {"selected_minutes",json::Value::fromInteger(view.selectedMinutes_)}});
    }
    static bool noStore(const GuidedSessionView& view) { return view.store_==nullptr; }
    static void deliverSyntheticSummary(GuidedSessionView& view,storage::Status status,json::Value data) {
        std::promise<storage::Reply> promise;
        auto future=promise.get_future();
        storage::Reply reply;reply.status=status;reply.code="synthetic-summary-reply";reply.data=std::move(data);
        promise.set_value(std::move(reply));
        view.mutation_=GuidedSessionView::Mutation::LoadSummary;
        view.future_.emplace(std::move(future),"synthetic-summary-reply","");
        view.service();
    }
};
}

namespace {
const json::Value& field(const json::Value& value, const std::string& key) { return value.object().at(key); }
std::size_t rows(const json::Value& snapshot, const char* table) { return field(field(snapshot, "authoritative"), table).array().size(); }
void pump() {
    CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.005, true);
    std::this_thread::sleep_for(std::chrono::milliseconds(2));
}
scheduler::Owner ownerFor(const std::string& id) {
    storage::validateUuid(id);
    scheduler::Owner owner;
    std::string compact;
    for (const auto c : id) if (c != '-') compact += c;
    for (std::size_t i = 0; i < owner.id.size(); ++i)
        owner.id[i] = static_cast<std::uint8_t>(std::stoul(compact.substr(i * 2, 2), nullptr, 16));
    owner.generation = 1;
    owner.epoch = 1;
    return owner;
}
void beginAttempt(practice::Coordinator& coordinator, const capture::Binding& binding,
                  const practice::Configuration& configuration) {
    coordinator.begin(ownerFor(binding.owner), practice::Kind::Attempt,
                      storage::canonical(binding.context), configuration);
}
std::string admissionDisclosure(const lesson::Catalog& catalog, const lesson::Lesson& lesson) {
    std::vector<std::string> admitted;
    for (const auto& variant : lesson.variants) {
        try {
            const auto admission = catalog.admit(lesson.id, variant.id);
            if (admission && admission->practiceAllowed()) admitted.push_back(variant.id);
        } catch (const std::exception&) {}
    }
    if (admitted.empty()) return "Practice admission: refused by the existing runtime gate.";
    std::string text = "Practice-ready variants: ";
    for (std::size_t index = 0; index < admitted.size(); ++index) {
        if (index != 0) text += ", ";
        text += admitted[index];
    }
    return text;
}
}

int main(int argc, char** argv) {
    int checks{};
    std::ofstream trace;
    auto check = [&](bool okay, const std::string& name) {
        ++checks;
        trace << name << '\t' << (okay ? "PASS" : "FAIL") << '\n';
        trace.flush();
        if (!okay) throw std::runtime_error(name);
    };
    try {
        const bool controlOnly=argc==4&&std::string(argv[3])=="--control-contract";
        const bool summarySurfaceOnly=argc==4&&std::string(argv[3])=="--summary-surface";
        const bool savedAttemptSummaryOnly=argc==4&&std::string(argv[3])=="--saved-attempt-summary";
        const bool statusSurfaceOnly=argc==4&&std::string(argv[3])=="--status-surface";
        const bool guidedProgressHandoffOnly=argc==4&&std::string(argv[3])=="--guided-progress-handoff";
        const bool guidedSelectedCaseHandoffOnly=argc==4&&std::string(argv[3])=="--guided-selected-case-handoff";
        const bool responsiveOnly=argc==4&&std::string(argv[3])=="--responsive-layout";
        const bool keyboardPeerOnly=argc==4&&std::string(argv[3])=="--keyboard-peer";
        const bool stopPresentationOnly=argc==4&&std::string(argv[3])=="--guided-stop-presentation";
        const bool catalogFeedbackOnly=argc==4&&std::string(argv[3])=="--catalog-load-feedback";
        const bool exitSaveFailureOnly=argc==4&&std::string(argv[3])=="--exit-save-failure-regression";
        const bool exitDiscardOnly=argc==4&&std::string(argv[3])=="--exit-discard-regression";
        const bool shutdownDebtOnly=argc==4&&std::string(argv[3])=="--shutdown-debt";
        if (argc != 3 && !controlOnly && !summarySurfaceOnly && !savedAttemptSummaryOnly && !statusSurfaceOnly && !guidedProgressHandoffOnly && !guidedSelectedCaseHandoffOnly && !responsiveOnly && !keyboardPeerOnly && !stopPresentationOnly && !catalogFeedbackOnly && !shutdownDebtOnly && !exitDiscardOnly && !exitSaveFailureOnly) throw std::invalid_argument("Expected absolute representative bundle and new evidence directory");
        const std::filesystem::path bundle(argv[1]), evidence(argv[2]);
        if (!bundle.is_absolute() || !evidence.is_absolute() || std::filesystem::exists(evidence))
            throw std::invalid_argument("Bundle must be absolute and evidence directory must be new");
        std::filesystem::create_directories(evidence);
        std::filesystem::permissions(evidence, std::filesystem::perms::owner_all, std::filesystem::perm_options::replace);
        trace.open(evidence / "checks.tsv");
        juce::ScopedJuceInitialiser_GUI gui;
        if(exitSaveFailureOnly){
            const auto catalog=lesson::Catalog::load(bundle);
            for(const bool lostAck:{false,true}){
                const auto profile=evidence/(lostAck?"close-lost-ack":"close-refusal");if(!std::filesystem::create_directory(profile))throw std::runtime_error("Fresh Guided close fixture required");std::filesystem::permissions(profile,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
                storage::StoreOptions options;options.path=profile/"profile.sqlite";options.create=true;options.createdUtc="2026-10-10T00:00:00Z";
                std::atomic<bool> fail{true};std::atomic<int> submitted{0};options.diagnosticHook=[&](const std::string& phase,const std::string& op){if(op.find("guided-session/close/")==std::string::npos)return;if(phase=="before_operation")++submitted;if(phase==(lostAck?"after_commit":"before_commit")&&fail.exchange(false))throw std::runtime_error("Controlled Guided close refusal");};
                storage::ProfileStore store(options);desktop::GuidedSessionView view;view.setCatalog(catalog);check(view.configureStore(store,[]{return std::string("2026-10-10T00:00:10Z");},"Etc/UTC"),"failed-close view binds actualStore");
                auto drain=[&]{const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(6);while(view.busy()){view.service();pump();if(std::chrono::steady_clock::now()>end)throw std::runtime_error("Guided close six-second future watchdog");}};
                drain();check(view.buildPlan()&&view.startSession(),"failed-close fixture starts actual plannedSession");drain();const auto owner=view.sessionId();check(view.running(),"original Guided create confirmed");
                check(!view.requestExit(false),"SaveQuit first waits accepted Guided close");drain();check(!view.presentationStoppedAndResolved(),"failed or unknown Guided close is not resolved presentation");
                check(!view.requestExit(false)&&!view.requestExit(false)&&view.sessionId()==owner,"repeated SaveQuit cannot bypass failed original close");
                check(submitted==1,"one explicit Save intent submits original close once");const auto snap=store.snapshot(storage::newUuid()).get();check(snap.status==storage::Status::Confirmed&&rows(snap.data,"session_close")==static_cast<std::size_t>(lostAck?1:0)&&rows(snap.data,"identity")==0,"Guided failure preserves actual close commit boundary and no Attempt credit");
            }
            return 0;
        }
        if(exitDiscardOnly){
            storage::StoreOptions options;options.path=evidence/"profile.sqlite";options.create=true;options.createdUtc="2026-10-10T00:00:00Z";storage::ProfileStore store(options);
            desktop::GuidedSessionView view;view.setCatalog(lesson::Catalog::load(bundle));check(view.configureStore(store,[]{return std::string("2026-10-10T00:00:10Z");},"Etc/UTC"),"Guided actual Store configured");
            auto drain=[&]{const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(6);while(view.busy()){view.service();pump();if(std::chrono::steady_clock::now()>end)throw std::runtime_error("Guided six-second future watchdog");}};
            drain();check(view.buildPlan()&&view.startSession(),"Guided actual immutable plan starts Session");drain();check(view.running(),"Guided actual create ACK owns running Session");const auto owner=view.sessionId();auto before=store.snapshot(storage::newUuid()).get();check(before.status==storage::Status::Confirmed,"Guided baseline contains acknowledged Session");
            check(view.requestExit(true)&&!view.running()&&view.sessionId()==owner,"Guided Discard stops volatile timer and retains original Session");check(view.requestExit(true),"repeated Guided Discard remains idempotent");check(!view.startSession()&&view.sessionId()==owner&&!view.presentationStoppedAndResolved(),"kept-open discarded Guided Session cannot start replacement or claim resolved close");auto after=store.snapshot(storage::newUuid()).get();check(after.status==storage::Status::Confirmed&&after.data==before.data,"Guided Discard adds no Session close or Attempt and changes no authority");return 0;
        }
        if(shutdownDebtOnly){
            const auto catalog=lesson::Catalog::load(bundle);
            for(const bool lostReceipt:{true,false}){
                const auto label=std::string(lostReceipt?"lost-receipt":"definite-failure");
                const auto profile=evidence/label;std::filesystem::create_directory(profile);
                std::filesystem::permissions(profile,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
                std::atomic<bool> failCreate{true};std::vector<std::string> operations;
                storage::StoreOptions options;options.path=profile/"profile.sqlite";options.create=true;options.createdUtc="2026-09-14T00:55:00Z";
                options.diagnosticHook=[&](const std::string& phase,const std::string& operation){
                    if(operation.find("guided-session/create/")!=0||operation.find(".inspect/")!=std::string::npos)return;
                    if(phase=="before_operation")operations.push_back(operation);
                    if(phase==(lostReceipt?"after_commit":"before_operation")&&failCreate.exchange(false))
                        throw std::runtime_error(lostReceipt?"Controlled original Guided Create receipt loss":"Controlled definite Guided Create failure");
                };
                storage::ProfileStore store(options);desktop::GuidedSessionView view;
                desktop::GuidedSessionViewTestAccess::stopTimer(view);view.setCatalog(catalog);
                std::string utc="2026-09-14T00:55:10Z";
                const auto settle=[&]{const auto until=capture_fixture::now()+7000;while(view.busy()){
                    if(capture_fixture::now()>until)throw std::runtime_error("Guided shutdown-debt fixture watchdog");
                    view.service();std::this_thread::sleep_for(std::chrono::milliseconds(1));
                }};
                check(view.configureStore(store,[&]{return utc;},"America/New_York"),label+" binds its existing Store");settle();
                check(view.buildPlan()&&view.canClose(),label+" idle plan creates no quit debt");
                check(view.startSession()&&view.busy()&&!view.canClose(),label+" original Create holds Quit while pending");settle();
                const auto original=desktop::GuidedSessionViewTestAccess::originalStart(view);
                check(view.createUnresolved()&&!view.running()&&!view.busy()&&!view.canClose()&&view.holdsSessionOperation()
                      &&view.sessionId().empty()&&original.object().at("utc")==json::Value("2026-09-14T00:55:10Z")
                      &&!original.object().at("operation").string().empty(),label+" unconfirmed original holds Quit and retains its exact request");
                const auto before=capture_fixture::confirmed(store.snapshot(storage::newUuid()));
                check(rows(before.data,"session")==static_cast<std::size_t>(lostReceipt?1:0)&&rows(before.data,"session_close")==0
                      &&rows(before.data,"identity")==0&&rows(before.data,"finalized")==0,
                      label+" actual durable Session boundary is truthful and creates no Practice or curriculum record");
                utc="2026-09-14T01:55:10Z";
                check(!view.startSession()&&!view.buildPlan()&&!view.configureStore(store,[&]{return utc;},"America/New_York")
                      &&!view.canClose()&&desktop::GuidedSessionViewTestAccess::originalStart(view)==original,
                      label+" replacement Start plan and Store rebinding cannot overwrite the original quit debt");
                if(lostReceipt){
                    const auto owner=original.object().at("owner").string();
                    check(!owner.empty()&&before.data.object().at("authoritative").object().at("session").array().front().array()[0]==json::Value(owner)
                          &&!view.retryOriginalStart(),"lost receipt retains its actual persisted owner and refuses raw Create retry");
                    check(view.inspectOriginalStart()&&!view.inspectOriginalStart()&&!view.canClose(),"explicit exact-owner inspection holds Quit without concurrent inspection");settle();
                    const auto after=capture_fixture::confirmed(store.snapshot(storage::newUuid()));
                    check(!view.createUnresolved()&&view.running()&&view.sessionId()==owner&&operations.size()==1
                          &&before.data.object().at("authoritative")==after.data.object().at("authoritative")
                          &&desktop::GuidedSessionViewTestAccess::originalStart(view)==original,
                          "explicit inspection adopts the exact original stored Session and plan without another Create or authority change");
                }else{
                    check(original.object().at("owner").string().empty()
                          &&view.retryOriginalStart()&&!view.retryOriginalStart()&&!view.startSession(),
                          "definitely absent Create permits only one explicit unchanged original retry");settle();
                    const auto retried=desktop::GuidedSessionViewTestAccess::originalStart(view);
                    const auto after=capture_fixture::confirmed(store.snapshot(storage::newUuid()));
                    const auto& row=after.data.object().at("authoritative").object().at("session").array().front().array();
                    check(view.running()&&!view.createUnresolved()&&operations.size()==2&&operations[0]==operations[1]
                          &&rows(after.data,"session")==1&&row[0]==json::Value(view.sessionId())&&row[1]==original.object().at("utc")
                          &&row[2]==original.object().at("timezone")&&row[3]==original.object().at("seconds")
                          &&retried.object().at("operation")==original.object().at("operation")&&retried.object().at("plan")==original.object().at("plan"),
                          "safe retry confirms one Session using the exact original operation time timezone duration and plan");
                }
                const auto beforeInterrupt=capture_fixture::confirmed(store.snapshot(storage::newUuid()));
                check(!view.canClose()&&view.interruptSession()&&view.canClose()&&!view.createUnresolved(),
                      label+" explicit confirmed interruption preserves its existing safe-exit contract");
                const auto afterInterrupt=capture_fixture::confirmed(store.snapshot(storage::newUuid()));
                check(beforeInterrupt.data.object().at("authoritative")==afterInterrupt.data.object().at("authoritative")
                      &&rows(afterInterrupt.data,"session_close")==0&&!view.startSession()&&!view.retryOriginalStart(),
                      label+" explicit interruption retains its durable original without inventing a close or replacement");
            }
            std::ofstream(evidence/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"nativeAudio\":false}\n";
            std::cout<<"PASS "<<checks<<" Guided shutdown-debt checks\n";return 0;
        }

        if(catalogFeedbackOnly){
            // Return before Catalog::load. These marked display poses have no
            // Store, device, real Session or source admission.
            const std::string pending="Synthetic installed catalog preparation is pending.";
            const std::string failure="Synthetic installed catalog preparation failed; return Home and inspect its original metadata.";
            const auto planState=[](desktop::GuidedSessionView& view){
                auto* label=dynamic_cast<juce::Label*>(view.findChildWithID("guided-plan-state"));
                if(!label)throw std::runtime_error("Missing Guided plan state");
                return label->getText().toStdString();
            };
            desktop::GuidedSessionView idle;
            desktop::GuidedSessionViewTestAccess::stopTimer(idle);
            idle.setCatalogLoading(true,pending);
            check(idle.statusText()==pending&&planState(idle)==pending,"idle Guided reports the actual pending message in lifecycle and plan state");
            idle.setCatalogLoading(true,failure);
            check(idle.statusText()==failure&&planState(idle)==failure,"catalog failure replaces stale preparing text verbatim");
            const auto idleState=desktop::GuidedSessionViewTestAccess::lifecycle(idle);
            check(!idle.buildPlan()&&!idle.startSession()&&idle.statusText()==failure&&planState(idle)==failure,"direct Build and Start remain refused with the actual catalog failure");
            check(desktop::GuidedSessionViewTestAccess::lifecycle(idle)==idleState&&desktop::GuidedSessionViewTestAccess::noStore(idle)&&idle.sessionId().empty(),"catalog feedback creates no plan, owner, Session or Store");
            auto* build=idle.findChildWithID("build");auto* start=idle.findChildWithID("start");
            check(build&&start&&!build->isEnabled()&&!start->isEnabled(),"pending catalog keeps existing Build and Start gates disabled");
            idle.setCatalogLoading(true,{});
            check(idle.statusText().find("Practice catalog is preparing.")==0&&idle.statusText().find("no new Guided plan")!=std::string::npos&&planState(idle)==idle.statusText(),"empty catalog message uses one truthful fallback in both surfaces");
            for(const auto& state:std::vector<std::string>{"running","unresolved","closed","busy","summary-unavailable"}){
                desktop::GuidedSessionView view;
                desktop::GuidedSessionViewTestAccess::poseCatalogCritical(view,state);
                const auto critical=view.statusText();
                const auto before=desktop::GuidedSessionViewTestAccess::lifecycle(view);
                view.setCatalogLoading(true,failure);
                check(view.statusText()==critical&&planState(view)==failure,"catalog failure preserves critical "+state+" lifecycle while updating its separate plan state");
                check(!view.buildPlan()&&!view.startSession()&&view.statusText()==critical,"direct catalog refusal preserves critical "+state+" status");
                view.setCatalogLoading(false);
                check(view.statusText()==critical&&desktop::GuidedSessionViewTestAccess::lifecycle(view)==before&&desktop::GuidedSessionViewTestAccess::noStore(view),"loading transition leaves "+state+" lifecycle, ownership and gates' inputs unchanged");
            }
            desktop::GuidedSessionView summaryFailure;
            desktop::GuidedSessionViewTestAccess::stopTimer(summaryFailure);
            summaryFailure.setCatalogLoading(true,pending);
            desktop::GuidedSessionViewTestAccess::deliverSyntheticSummary(summaryFailure,storage::Status::DefiniteFailure,nullptr);
            auto criticalSummary=summaryFailure.statusText();
            summaryFailure.setCatalogLoading(true,failure);
            check(criticalSummary.find("Saved Guided summary unavailable:")==0&&summaryFailure.statusText()==criticalSummary,"production summary-reply handling protects a marked synthetic failed summary from catalog feedback");
            desktop::GuidedSessionViewTestAccess::deliverSyntheticSummary(summaryFailure,storage::Status::Confirmed,nullptr);
            criticalSummary=summaryFailure.statusText();
            summaryFailure.setCatalogLoading(true,pending);
            check(criticalSummary.find("Snapshot has no authoritative object")!=std::string::npos&&summaryFailure.statusText()==criticalSummary,"confirmed malformed synthetic summary retains its parser error during catalog preparation");
            const json::Value emptySummary=json::Value::Object{
                {"authoritative",json::Value::Object{{"session",json::Value::Array{}},{"session_close",json::Value::Array{}}}}
            };
            desktop::GuidedSessionViewTestAccess::deliverSyntheticSummary(summaryFailure,storage::Status::Confirmed,emptySummary);
            summaryFailure.setCatalogLoading(true,failure);
            check(summaryFailure.statusText()==failure&&summaryFailure.sessionId().empty()&&desktop::GuidedSessionViewTestAccess::noStore(summaryFailure),"only a confirmed parsed summary clears the display protection; no Store or Session is created");
            trace.flush();
            std::ofstream(evidence/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"mode\":\"catalog-load-feedback\",\"catalogLoaded\":false,\"profileWrites\":false,\"syntheticLifecyclePoses\":true,\"physicalListening\":false}\n";
            std::cout<<"PASS "<<checks<<" finite Guided catalog feedback checks; no catalog, Store, device or Session\n";
            return 0;
        }

        if(keyboardPeerOnly){
            auto catalog=lesson::Catalog::load(bundle);
            std::ofstream keys(evidence/"focus-keys.tsv");keys<<"width\tstate\tfrom\tkey\texpected\tactual\tresult\n";
            int failures=0;
            auto peerCheck=[&](bool okay,const std::string& label){++checks;failures+=!okay;trace<<label<<'\t'<<(okay?"PASS":"FAIL")<<'\n';};
            const std::array<std::string,5> states{"detached","plan-ready","running","stopped","unresolved"};
            for(int width:{640,920})for(const auto& state:states){
                desktop::GuidedSessionView view;desktop::GuidedSessionViewTestAccess::stopTimer(view);view.setSize(width,680);
                if(state!="detached")view.setCatalog(catalog);
                const auto source=desktop::GuidedSessionViewTestAccess::source(view);
                if(state=="running"||state=="stopped"||state=="unresolved")desktop::GuidedSessionViewTestAccess::pose(view,state);
                view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);view.setVisible(true);
                auto* peer=view.getPeer();juce::KeyboardFocusTraverser traverser;const auto order=traverser.getAllComponents(&view);
                auto named=[](const juce::Component* c){return c?c->getComponentID().toStdString():std::string{"<none>"};};
                auto contains=[&](const char* id){auto* c=view.findChildWithID(id);return c&&std::find(order.begin(),order.end(),c)!=order.end();};
                peerCheck(peer&&view.isShowing()&&!order.empty()&&named(order.front())=="guided-audio-settings","visible Guided peer starts with Audio settings in "+state);
                peerCheck(desktop::GuidedSessionViewTestAccess::detached(view)&&view.sessionId().empty()==(state=="detached"||state=="plan-ready")&&(state=="detached"||!source.empty()),"synthetic Guided state keeps Store detached and source identity stable in "+state);
                peerCheck(!contains("custom")&&!contains("start")&&!contains("open-progress")&&contains("guided-audio-settings"),"disabled and hidden controls stay outside traversal in "+state);
                peerCheck(contains("stop")== (state=="running"||state=="unresolved") && contains("back")== (state=="detached"||state=="plan-ready"||state=="stopped") && contains("open-first")== (state!="detached"),"state-specific Stop Back and admitted-case focus eligibility in "+state);
                bool valid=true;for(auto* c:order)valid=valid&&c->isShowing()&&c->isEnabled()&&c->getWantsKeyboardFocus()&&c->getWidth()>0&&c->getHeight()>0&&view.getLocalBounds().contains(c->getBounds());peerCheck(valid,"all Guided traversal entries are visible enabled and contained in "+state);
                if(peer&&!order.empty()){
                    order.front()->grabKeyboardFocus();
                    peerCheck(juce::Component::getCurrentlyFocusedComponent()==order.front(),"Guided peer focus begins at first action in "+state);
                    for(std::size_t index=1;index<order.size();++index){auto* before=juce::Component::getCurrentlyFocusedComponent();peer->handleKeyPress(juce::KeyPress(juce::KeyPress::tabKey));auto* actual=juce::Component::getCurrentlyFocusedComponent();const bool okay=before==order[index-1]&&actual==order[index];keys<<width<<'\t'<<state<<'\t'<<named(order[index-1])<<"\tTab\t"<<named(order[index])<<'\t'<<named(actual)<<'\t'<<(okay?"PASS":"FAIL")<<'\n';peerCheck(okay,"Guided Tab follows constructed focus order in "+state);}
                    for(std::size_t index=order.size()-1;index>0;--index){auto* before=juce::Component::getCurrentlyFocusedComponent();peer->handleKeyPress(juce::KeyPress(juce::KeyPress::tabKey,juce::ModifierKeys::shiftModifier,'\t'));auto* actual=juce::Component::getCurrentlyFocusedComponent();const bool okay=before==order[index]&&actual==order[index-1];keys<<width<<'\t'<<state<<'\t'<<named(order[index])<<"\tShift-Tab\t"<<named(order[index-1])<<'\t'<<named(actual)<<'\t'<<(okay?"PASS":"FAIL")<<'\n';peerCheck(okay,"Guided Shift-Tab follows reverse focus order in "+state);}
                    const char* action=state=="detached"?"build":state=="plan-ready"?"open-first":state=="stopped"?"back":"stop";
                    auto* button=dynamic_cast<juce::TextButton*>(view.findChildWithID(action));int activated=0;
                    if(button){button->onClick=[&]{++activated;};button->grabKeyboardFocus();peer->handleKeyPress(juce::KeyPress(juce::KeyPress::returnKey));for(int i=0;i<20;++i)pump();peerCheck(activated==1,"focused Return activates Guided "+std::string(action)+" in "+state);peer->handleKeyPress(juce::KeyPress(juce::KeyPress::spaceKey));peer->handleKeyPress(juce::KeyPress(juce::KeyPress::spaceKey));for(int i=0;i<20;++i)pump();peerCheck(activated==2,"focused Space activates Guided once while held in "+state);peer->handleKeyUpOrDown(false);peer->handleKeyPress(juce::KeyPress(juce::KeyPress::spaceKey));for(int i=0;i<20;++i)pump();peerCheck(activated==3,"focused Space rearms after key release in "+state);}else peerCheck(false,"state action exists in "+state);
                }
                peerCheck(desktop::GuidedSessionViewTestAccess::detached(view)&&(state=="detached"||desktop::GuidedSessionViewTestAccess::source(view)==source),"peer keys create no profile activity or source change in "+state);
                if(state=="running"||state=="stopped"||state=="unresolved")peerCheck(view.statusText().find("Synthetic "+state)!=std::string::npos,"synthetic lifecycle pose is marked in visible status for "+state);
                auto image=view.createComponentSnapshot(view.getLocalBounds());const auto name="guided-keyboard-"+state+"-"+std::to_string(width)+".png";juce::FileOutputStream out(juce::File((evidence/name).string()));juce::PNGImageFormat png;const bool saved=out.openedOk()&&png.writeImageToStream(image,out);out.flush();peerCheck(saved&&!out.getStatus().failed(),"Guided peer screenshot saved for "+state);
                view.removeFromDesktop();
            }
            keys.flush();trace.flush();peerCheck(keys.good()&&trace.good(),"Guided peer evidence flushed");
            std::ofstream(evidence/"summary.json")<<"{\"checks\":"<<checks<<",\"failures\":"<<failures<<",\"peerInjectedKeys\":true,\"syntheticLifecyclePoses\":true,\"profileWrites\":false}\n";
            std::cout<<(failures?"FAIL ":"PASS ")<<checks<<" Guided peer keyboard checks; failures="<<failures<<'\n';return failures?1:0;
        }

        if(stopPresentationOnly){
            auto catalog=lesson::Catalog::load(bundle);
            for(const int width:{920,640})for(const bool linked:{false,true}){
                desktop::GuidedSessionView view;desktop::GuidedSessionViewTestAccess::stopTimer(view);view.setSize(width,680);view.setCatalog(catalog);
                desktop::GuidedSessionViewTestAccess::pose(view,"running");
                if(linked)desktop::GuidedSessionViewTestAccess::linkSyntheticSummary(view);
                view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);view.setVisible(true);
                auto* stop=dynamic_cast<juce::TextButton*>(view.findChildWithID("stop"));
                const std::string expected=linked?(width==640?"Stop & save summary":"Stop & save Guided summary"):"Stop Guided session";
                const std::string title=linked?"Stop Guided and save this Session with its linked Practice summary.":"Stop Guided and save its local Session outcome.";
                check(stop&&stop->isShowing()&&stop->isEnabled()&&stop->getButtonText().toStdString()==expected&&stop->getTitle().toStdString()==title,"active Stop label and full accessible title match state at "+std::to_string(width)+(linked?" linked":" running"));
                check(stop&&stop->getWidth()==150&&stop->getHeight()>0&&view.getLocalBounds().contains(stop->getBounds()),"active Stop has readable contained geometry at "+std::to_string(width)+(linked?" linked":" running"));
                auto image=view.createComponentSnapshot(view.getLocalBounds());const auto name="guided-stop-"+std::string(linked?"linked-":"running-")+std::to_string(width)+".png";juce::FileOutputStream out(juce::File((evidence/name).string()));juce::PNGImageFormat png;const bool saved=out.openedOk()&&png.writeImageToStream(image,out);out.flush();check(saved&&!out.getStatus().failed(),"active Stop peer screenshot saved at "+std::to_string(width)+(linked?" linked":" running"));
                if(!linked&&width==640){
                    const auto* explanation=dynamic_cast<const juce::Label*>(view.findChildWithID("guided-explanation"));
                    const auto* duration=view.findChildWithID("guided-duration-label");
                    const juce::String first="Build a source-backed Guided plan. Choose a duration before Start.";
                    const juce::String second="Start creates a local Session; Practice grants no curriculum credit.";
                    check(explanation&&explanation->getText()==first+"\n"+second
                              && explanation->getHelpText().contains("After Start: open a source-backed case in Learn")
                              && explanation->getHelpText().contains("an unresolved close stays retryable"),
                          "compact unlinked Guided introduction has complete visible lines and full accessible help");
                    check(explanation&&duration&&explanation->getBottom()<duration->getY()
                              && explanation->getHeight()>=2*explanation->getFont().getHeight()+8
                              && juce::GlyphArrangement::getStringWidth(explanation->getFont(),first)<=explanation->getWidth()-8
                              && juce::GlyphArrangement::getStringWidth(explanation->getFont(),second)<=explanation->getWidth()-8,
                          "compact unlinked Guided lines fit before Duration");
                }
                if(linked){
                    const auto* explanation=dynamic_cast<const juce::Label*>(view.findChildWithID("guided-explanation"));
                    const auto* duration=view.findChildWithID("guided-duration-label");
                    const juce::String first="Saved Practice Attempt belongs to this Guided Session; no curriculum credit.";
                    const juce::String second="Stop & save summary closes its local Session.";
                    check(explanation&&explanation->getText()==first+"\n"+second,
                          "linked Guided introduction contains two complete visible lines at "+std::to_string(width));
                    check(explanation&&duration&&explanation->getBottom()<duration->getY()
                              && explanation->getHeight()>=2*explanation->getFont().getHeight()+8
                              && juce::GlyphArrangement::getStringWidth(explanation->getFont(),first)<=explanation->getWidth()-8
                              && juce::GlyphArrangement::getStringWidth(explanation->getFont(),second)<=explanation->getWidth()-8,
                          "linked Guided lines fit their label and clear Duration at "+std::to_string(width));
                    check(explanation&&explanation->getHelpText().contains("Choose 10, 20, 30, 45 or 60 minutes")
                              && explanation->getHelpText().contains("After Start: open a source-backed case in Learn")
                              && explanation->getHelpText().contains("curriculum credit")
                              && explanation->getHelpText().contains("an unresolved close stays retryable"),
                          "linked Guided accessible help preserves complete path, credit and refusal guidance at "+std::to_string(width));
                }
                int activations=0;stop->onClick=[&]{++activations;};stop->grabKeyboardFocus();auto* peer=view.getPeer();
                check(peer&&juce::Component::getCurrentlyFocusedComponent()==stop,"active Stop receives actual peer focus at "+std::to_string(width)+(linked?" linked":" running"));
                if(peer)peer->handleKeyPress(juce::KeyPress(juce::KeyPress::returnKey));for(int i=0;i<20;++i)pump();check(activations==1,"focused Return activates active Stop once at "+std::to_string(width)+(linked?" linked":" running"));
                if(peer)peer->handleKeyPress(juce::KeyPress(juce::KeyPress::spaceKey));for(int i=0;i<20;++i)pump();check(activations==2,"focused Space activates active Stop once at "+std::to_string(width)+(linked?" linked":" running"));
                check(desktop::GuidedSessionViewTestAccess::detached(view)&&view.running()&&view.sessionId()=="synthetic-guided-focus-pose"&&view.statusText().find("Synthetic")!=std::string::npos,"synthetic Stop pose preserves no-Store lifecycle boundary at "+std::to_string(width)+(linked?" linked":" running"));
                const int resizedWidth=width==640?920:640;view.setSize(resizedWidth,680);
                const std::string resizedLabel=linked?(resizedWidth==640?"Stop & save summary":"Stop & save Guided summary"):"Stop Guided session";
                check(stop->getButtonText().toStdString()==resizedLabel&&stop->getWidth()==150&&view.getLocalBounds().contains(stop->getBounds()),"active Stop adapts label and bounds after live resize to "+std::to_string(resizedWidth)+(linked?" linked":" running"));
                view.removeFromDesktop();
            }
            std::ofstream(evidence/"summary.json")<<"{\"checks\":"<<checks<<",\"status\":\"PASS\",\"peerInjectedKeys\":true,\"syntheticLifecyclePoses\":true,\"profileWrites\":false}\n";
            std::cout<<"PASS "<<checks<<" Guided Stop presentation checks\n";return 0;
        }

        if(responsiveOnly){
            desktop::GuidedSessionView compact;compact.setSize(640,680);compact.setVisible(true);compact.resized();const auto bounds=compact.getLocalBounds();
            auto* compactHeading=dynamic_cast<juce::Label*>(compact.findChildWithID("guided-heading"));check(compactHeading&&compactHeading->getText()==juce::String::fromUTF8("Guided — Timed local session"),"compact Guided heading names the timed local Session concisely");
            for(auto* child:compact.getChildren())if(child->isVisible())check(child->getWidth()>0&&child->getHeight()>0&&bounds.contains(child->getBounds()),"compact Guided child is positive and contained");
            std::vector<juce::Button*> actions;for(auto* child:compact.getChildren())if(auto* button=dynamic_cast<juce::Button*>(child);button&&button->isVisible())actions.push_back(button);for(std::size_t left=0;left<actions.size();++left)for(std::size_t right=left+1;right<actions.size();++right)check(!actions[left]->getBounds().intersects(actions[right]->getBounds()),"compact Guided actions do not overlap");
            const char* ids[]={"guided-audio-settings","duration","custom","build","start","open-first","stop","interrupt","open-progress","back"};for(const auto* id:ids)check(compact.findChildWithID(id)&&bounds.contains(compact.findChildWithID(id)->getBounds()),std::string("compact Guided control remains reachable: ")+id);
            check(compact.sessionId().empty()&&!compact.running()&&!compact.busy()&&compact.canLeave(),"compact Guided inspection creates no Session, profile operation or activity");
            desktop::GuidedSessionView standard;standard.setSize(920,680);standard.setVisible(true);standard.resized();auto* standardHeading=dynamic_cast<juce::Label*>(standard.findChildWithID("guided-heading"));check(standardHeading&&standardHeading->getText().startsWith("GUIDED")&&standardHeading->getText().contains("TIMED LOCAL SESSION")&&standard.findChildWithID("back")&&standard.getLocalBounds().contains(standard.findChildWithID("back")->getBounds()),"standard Guided restores the existing timed local Session heading and geometry");for(auto* child:standard.getChildren())if(auto* button=dynamic_cast<juce::Button*>(child);button&&button->isVisible())check(button->getWidth()>0&&button->getHeight()>0&&standard.getLocalBounds().contains(button->getBounds()),"standard Guided visible action is contained at 920x680");
            std::ofstream(evidence/"summary.json")<<"{\"checks\":"<<checks<<",\"status\":\"PASS\",\"sessionLifecycle\":false,\"profileAccess\":false}\n";std::cout<<"PASS "<<checks<<" compact Guided surface checks\n";return 0;
        }

        if(controlOnly){
            desktop::GuidedSessionView view;view.setSize(920,680);
            struct ControlContract {const char* id;const char* label;const char* title;int order;};
            const ControlContract controls[]={
                {"guided-audio-settings","Audio settings","Open shared Audio settings without changing Guided Session state.",1},
                {"duration",nullptr,"Choose Guided duration: 10, 20, 30, 45 or 60 minutes, or Custom.",2},
                {"custom",nullptr,"Enter a whole custom Guided duration from 1 to 240 minutes.",3},
                {"build","Build Guided plan","Build a source-backed Guided plan from the retained records.",4},
                {"open-first","Open first practice-ready case in Learn","Open the admitted source-backed case in Learn.",5},
                {"start","Start Guided session","Start one local Guided Session; no Attempt or curriculum credit is created.",6},
                {"stop","Stop Guided session","Stop Guided and save its local Session outcome.",7},
                {"interrupt","Interrupt & leave unresolved","Interrupt Guided and leave the original Session unresolved.",8},
                {"open-progress","Open Progress","Review saved Guided activity in Progress read-only.",9},
                {"back","Back","Return to Home when the Guided Session is not active or unresolved.",10}
            };
            auto* audioColor=dynamic_cast<juce::TextButton*>(view.findChildWithID("guided-audio-settings"));
            check(audioColor&&audioColor->findColour(juce::TextButton::buttonColourId)==juce::Colour{0xff6bd5cb}&&audioColor->findColour(juce::TextButton::textColourOffId)==juce::Colour{0xff10212c}&&audioColor->findColour(juce::TextButton::textColourOnId)==juce::Colour{0xff10212c},"Guided Audio settings uses the primary teal presentation while preserving the existing control contract");
            auto* startColor=dynamic_cast<juce::TextButton*>(view.findChildWithID("start"));
            check(startColor&&startColor->findColour(juce::TextButton::buttonColourId)==juce::Colour{0xff6bd5cb}&&startColor->findColour(juce::TextButton::textColourOffId)==juce::Colour{0xff10212c}&&startColor->findColour(juce::TextButton::textColourOnId)==juce::Colour{0xff10212c},"Guided Start uses the primary teal presentation while preserving the existing control contract");
            for(const auto& contract:controls){auto* component=view.findChildWithID(contract.id);check(component!=nullptr,std::string("Guided control exists: ")+contract.id);if(!component)continue;check(component->getTitle().toStdString()==contract.title,std::string("Guided control title: ")+contract.id);check(component->getExplicitFocusOrder()==contract.order,std::string("Guided control focus order: ")+contract.id);check(component->getWantsKeyboardFocus()==component->isEnabled(),std::string("Guided control focusability preserves enabled-state boundary: ")+contract.id);if(contract.label){auto* button=dynamic_cast<juce::Button*>(component);check(button&&button->getButtonText().toStdString()==contract.label,std::string("Guided control label preserved: ")+contract.id);}}
            check(view.sessionId().empty()&&!view.running()&&!view.busy(),"Guided control inspection creates no Session or pending profile operation");
            std::ofstream(evidence/"summary.json")<<"{\"checks\":"<<checks<<",\"status\":\"PASS\",\"sessionLifecycle\":false,\"profileAccess\":false}\n";
            std::cout<<"PASS "<<checks<<" Guided control checks\n";return 0;
        }

        if(summarySurfaceOnly){
            desktop::GuidedSessionView view;view.setSize(1280,800);view.setVisible(true);
            auto* heading=dynamic_cast<juce::Label*>(view.findChildWithID("guided-session-summary-heading"));
            auto* state=dynamic_cast<juce::Label*>(view.findChildWithID("guided-summary-state"));
            auto* summary=dynamic_cast<juce::Label*>(view.findChildWithID("session-summary"));
            auto* planState=dynamic_cast<juce::Label*>(view.findChildWithID("guided-plan-state"));
            auto* plan=dynamic_cast<juce::TextEditor*>(view.findChildWithID("plan"));
            check(heading&&heading->getText().toStdString()=="SESSION SUMMARY"&&heading->getTitle().toStdString()=="Read-only Guided Session summary heading"&&heading->isVisible(),"Guided summary heading is visible and truthful");
            check(state&&state->isVisible()&&state->getText().toStdString()=="No saved Guided Session yet"&&state->getTitle().toStdString()=="Guided summary empty-state marker."&&view.getLocalBounds().contains(state->getBounds()),"Guided summary exposes a contained no-saved-session state marker");
            check(summary&&summary->getTitle().toStdString()=="Read-only Guided Session summary: Session identity, planned duration, elapsed time, outcome and linked Attempt facts."&&summary->isVisible()&&summary->getHeight()>=160,"Large Guided summary retains the original 160-point multi-line surface");
            view.setSize(920,680);
            juce::TextEditor* summaryEditor=nullptr;
            if(summary)for(auto* child:summary->getChildren())if(auto* editor=dynamic_cast<juce::TextEditor*>(child))summaryEditor=editor;
            check(summaryEditor&&summaryEditor->isReadOnly()&&summaryEditor->isMultiLine()&&summaryEditor->isVisible()&&summaryEditor->getFont().getHeight()>=15.0f&&summaryEditor->getText()==summary->getText()&&summary->getLocalBounds().contains(summaryEditor->getBounds())&&view.getLocalBounds().contains(summary->getBounds()),"Minimum Guided summary preserves complete exact text in the existing contained read-only scrolling surface");
            check(summary&&summary->getText().toStdString().find("Opening Guided summary does not create activity.")!=std::string::npos&&summary->getText().toStdString().find("no Guided Session has been saved")!=std::string::npos&&summary->getText().toStdString().find("no saved outcome exists yet")!=std::string::npos,"Guided summary preserves the read-only/no-activity boundary and honest initial no-saved state");
            check(planState&&planState->isVisible()&&planState->getText().toStdString()=="No source-backed Guided plan built yet"&&planState->getTitle().toStdString()=="Guided source-plan empty-state marker."&&view.getLocalBounds().contains(planState->getBounds()),"Guided plan exposes a contained no-plan state marker before Build plan");
            check(heading&&state&&summary&&planState&&plan&&heading->getBounds().getRight()<=state->getX()&&heading->getBottom()<=summary->getY()&&summary->getBottom()<=planState->getY()&&planState->getBottom()<=plan->getY(),"Guided summary, plan empty-state marker, facts and plan remain ordered without overlap");
            for(const auto* id:{"start","open-first","stop","interrupt","open-progress","back"}){auto* component=view.findChildWithID(id);check(component&&view.getLocalBounds().contains(component->getBounds()),std::string("Guided action remains inside the visible summary layout: ")+id);check(plan&&component&&plan->getBottom()<=component->getY(),std::string("Guided action remains below the source-backed plan without overlap: ")+id);}
            check(view.sessionId().empty()&&!view.running()&&!view.busy(),"summary surface inspection creates no Session or pending profile operation");
            const auto originalSummary=summary->getText();
            juce::String overflowingSummary="SYNTHETIC SUMMARY START\n";
            for(int n=0;n<40;++n)overflowingSummary+="Synthetic retained Session, source identity, elapsed outcome and no-credit facts line "+juce::String(n)+".\n";
            overflowingSummary+="SYNTHETIC SUMMARY END";
            summary->setText(overflowingSummary,juce::dontSendNotification);
            for(int n=0;n<4;++n)pump();
            check(summaryEditor->getText()==overflowingSummary&&summaryEditor->getTextHeight()>summaryEditor->getHeight(),"Long synthetic summary genuinely exceeds the viewport without truncating text");
            juce::Viewport* summaryViewport=nullptr;
            for(auto* child:summaryEditor->getChildren())if(auto* viewport=dynamic_cast<juce::Viewport*>(child))summaryViewport=viewport;
            check(summaryViewport&&summaryViewport->getViewedComponent()&&summaryViewport->getViewedComponent()->getHeight()>summaryViewport->getMaximumVisibleHeight(),"Long summary exposes its existing actual scrolling viewport");
            summaryEditor->moveCaretToEnd();
            summaryViewport->getVerticalScrollBar().setCurrentRangeStart(summaryViewport->getVerticalScrollBar().getMaximumRangeLimit(),juce::sendNotificationSync);
            for(int n=0;n<4;++n)pump();
            std::ofstream scrollMetrics(evidence/"summary-scroll-metrics.txt");
            scrollMetrics<<"viewport="<<summaryEditor->getLocalBounds().toString()<<" textHeight="<<summaryEditor->getTextHeight()<<" caret="<<summaryEditor->getCaretPosition()<<" length="<<overflowingSummary.length()<<" end="<<summaryEditor->getCaretRectangleForCharIndex(overflowingSummary.length()).toString()<<std::endl;
            scrollMetrics<<"visible="<<summaryViewport->getViewArea().toString()<<" content="<<summaryViewport->getViewedComponent()->getLocalBounds().toString()<<std::endl;
            check(summaryEditor->getCaretPosition()==overflowingSummary.length()&&summaryEditor->getLocalBounds().contains(summaryEditor->getCaretRectangleForCharIndex(overflowingSummary.length())),"Complete summary end is scroll-reachable in the minimum window");
            summaryEditor->moveCaretToTop(false);
            summaryViewport->getVerticalScrollBar().setCurrentRangeStart(0.0,juce::sendNotificationSync);
            for(int n=0;n<4;++n)pump();
            scrollMetrics<<"start="<<summaryEditor->getCaretRectangleForCharIndex(0).toString()<<std::endl;
            check(summaryEditor->getCaretPosition()==0&&summaryEditor->getLocalBounds().contains(summaryEditor->getCaretRectangleForCharIndex(0)),"Complete summary beginning remains scroll-reachable after end inspection");
            summary->setText(originalSummary,juce::dontSendNotification);
            check(summaryEditor->getText()==originalSummary&&view.sessionId().empty()&&!view.running()&&!view.busy(),"Summary scroll inspection restores exact initial content without creating activity");
            std::ofstream(evidence/"summary-surface.json")<<"{\"checks\":"<<checks<<",\"status\":\"PASS\",\"sessionLifecycle\":false,\"profileAccess\":false}\n";
            std::cout<<"PASS "<<checks<<" Guided summary surface checks\n";return 0;
        }

        if(statusSurfaceOnly){
            desktop::GuidedSessionView view; view.setSize(920,680); view.setVisible(true);
            auto* status=dynamic_cast<juce::Label*>(view.findChildWithID("guided-status"));
            check(status&&status->getTitle().toStdString()=="Read-only Guided Session lifecycle, next action and save boundary.","Guided status exposes a stable truthful lifecycle title");
            check(status&&status->isVisible()&&status->getText().toStdString().find("Opening Guided does not start sound or create a Session.")!=std::string::npos&&status->getText().toStdString().find("Choose a duration and build a source-backed plan.")!=std::string::npos,"Guided status preserves the no-sound/no-Session entry boundary and existing initial plan guidance");
            check(status&&status->getText().toStdString().find("Next action: choose a duration, then choose Build Guided plan.")!=std::string::npos,"Guided status preserves the exact initial Build plan next action");
            check(status&&status->getHeight()>=42&&view.getLocalBounds().contains(status->getBounds()),"Guided status remains readable and contained in the 920x680 layout");
            auto* explanation=dynamic_cast<juce::Label*>(view.findChildWithID("guided-explanation"));
            auto* plan=dynamic_cast<juce::TextEditor*>(view.findChildWithID("plan"));
            check(explanation&&explanation->getText().toStdString().find("Local Guided activity requires an explicit profile")!=std::string::npos
                      && explanation->getText().toStdString().find("--capture-preview <new private directory> <IANA timezone>")!=std::string::npos,
                  "Guided explanation identifies the profile-dependent Development Preview path");
            check(explanation&&explanation->getHeight()>=90&&view.getLocalBounds().contains(explanation->getBounds()),"Guided entry explanation reserves readable contained space");
            check(plan&&plan->getHeight()>=90&&view.getLocalBounds().contains(plan->getBounds()),"Guided source-backed plan remains readable and contained after the explanation reflow");
            check(view.sessionId().empty()&&!view.running()&&!view.busy(),"Guided status inspection creates no Session, profile operation or audio activity");
            std::ofstream(evidence/"summary.json")<<"{\"checks\":"<<checks<<",\"status\":\"PASS\",\"sessionLifecycle\":false,\"profileAccess\":false}\n";
            std::cout<<"PASS "<<checks<<" Guided status surface checks\n";return 0;
        }

        if(guidedSelectedCaseHandoffOnly){
            auto catalog=lesson::Catalog::load(bundle);
            for(const int width:{640,920}){
                desktop::GuidedSessionView view;view.setSize(width,680);view.setVisible(true);
                auto* open=dynamic_cast<juce::TextButton*>(view.findChildWithID("open-first"));
                check(open&&open->getTitle().toStdString()=="Open the admitted source-backed case in Learn."&&!open->isEnabled()&&open->getButtonText().toStdString()=="Open first practice-ready case in Learn","initial Guided handoff preserves the generic title and disabled no-plan boundary at "+std::to_string(width));
                view.setCatalog(catalog);
                check(view.buildPlan(),"selected-case handoff fixture builds the retained source-backed Guided plan at "+std::to_string(width));
                open=dynamic_cast<juce::TextButton*>(view.findChildWithID("open-first"));
                check(open&&open->isEnabled()&&open->getButtonText().toStdString()=="Open selected case in Learn"&&open->getTitle().toStdString()=="Open admitted fg:item:000002 / fg:variant:000006 in Learn: ModeA Exercise001 full selected directions. Practice Start remains explicit and no curriculum credit is inferred.","short visible action retains exact admitted identity in its semantic title at "+std::to_string(width));
                check(open&&open->getWidth()>=(width==640?200:190)&&open->getHeight()>0&&view.getLocalBounds().contains(open->getBounds()),"selected-case action has readable, contained bounds at "+std::to_string(width));
                check(view.planText().find("Practice handoff: first practice-ready case in Learn is fg:item:000002 / fg:variant:000006 | Variant label: sixteenths-ascending-D-even | Source refs: L3-TXT5-21, L3-TXT28-46")!=std::string::npos,"Guided plan preserves exact selected source identity and references at "+std::to_string(width));
                auto image=view.createComponentSnapshot(view.getLocalBounds());const auto name="guided-selected-case-"+std::to_string(width)+".png";juce::FileOutputStream out(juce::File((evidence/name).string()));juce::PNGImageFormat png;const bool saved=out.openedOk()&&png.writeImageToStream(image,out);out.flush();check(saved&&!out.getStatus().failed(),"selected-case screenshot saved at "+std::to_string(width));
                int calls=0;std::string openedItem,openedVariant;
                view.onOpenLesson=[&](const std::string& item,const std::string& variant){++calls;openedItem=item;openedVariant=variant;return true;};
                view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);view.setVisible(true);open->grabKeyboardFocus();
                auto* peer=view.getPeer();check(peer&&juce::Component::getCurrentlyFocusedComponent()==open,"selected-case action receives peer focus at "+std::to_string(width));
                if(peer)peer->handleKeyPress(juce::KeyPress(juce::KeyPress::spaceKey));for(int i=0;i<20;++i)pump();
                check(calls==1&&openedItem=="fg:item:000002"&&openedVariant=="fg:variant:000006","focused Space opens the exact admitted item and variant in Learn at "+std::to_string(width));
                check(view.statusText().find("Learn opened with admitted fg:item:000002 / fg:variant:000006 in Learn.")!=std::string::npos&&view.statusText().find("Source refs: L3-TXT5-21, L3-TXT28-46")!=std::string::npos,"successful handoff reports exact selected identity and source refs at "+std::to_string(width));
                check(desktop::GuidedSessionViewTestAccess::detached(view)&&view.sessionId().empty()&&!view.running()&&!view.busy(),"Guided handoff creates no Session, Attempt or profile operation at "+std::to_string(width));
                view.removeFromDesktop();
            }
            std::ofstream(evidence/"summary.json")<<"{\"checks\":"<<checks<<",\"status\":\"PASS\",\"peerInjectedSpace\":true,\"sessionLifecycle\":false,\"profileAccess\":false,\"attemptCreated\":false,\"case\":\"fg:item:000002/fg:variant:000006\",\"sourceRefs\":[\"L3-TXT5-21\",\"L3-TXT28-46\"]}\n";
            std::cout<<"PASS "<<checks<<" Guided selected-case handoff checks\n";return 0;
        }

        if(savedAttemptSummaryOnly){
            desktop::GuidedSessionView detached;detached.setSize(920,680);detached.setVisible(true);
            check(detached.sessionSummaryText().find("SAVED ATTEMPT")==std::string::npos,"initial Guided summary keeps the saved Attempt marker absent");
            storage::StoreOptions options;options.path=evidence/"profile.sqlite";options.create=true;options.createdUtc="2026-09-14T00:55:00Z";
            storage::ProfileStore store(options);auto catalog=lesson::Catalog::load(bundle);
            desktop::GuidedSessionView view;view.setSize(920,680);view.setVisible(true);view.setCatalog(catalog);check(view.buildPlan(),"saved summary fixture builds the retained source-backed Guided plan");
            const auto assertContained=[&](juce::Component& owner,const char* id,const std::string& label){auto* component=owner.findChildWithID(id);check(component&&component->isVisible()&&owner.getLocalBounds().contains(component->getBounds()),label);};
            check(view.configureStore(store,[]{return std::string("2026-09-14T00:55:10Z");},"America/New_York"),"saved summary fixture binds the existing local Store");while(view.busy()){view.service();pump();}
            check(view.startSession()&&view.busy(),"saved summary fixture starts one local Guided Session");while(view.busy()){view.service();pump();}const auto activeSessionId=view.sessionId();check(view.running()&&!activeSessionId.empty(),"saved summary fixture confirms the Session owner");
            const auto admitted=catalog->admit("fg:item:000002","fg:variant:000006");check(admitted&&admitted->practiceAllowed(),"saved summary fixture uses the retained admitted source case");const auto attemptConfiguration=admitted->practiceConfiguration(8000,120);auto attemptRequest=capture::lessonStart(*admitted,attemptConfiguration,activeSessionId,"2026-09-14T00:55:12Z","America/New_York",1,false);auto allocation=store.allocate("guided-saved-attempt-summary-allocate",attemptRequest.binding.kind,attemptRequest.binding.context,attemptRequest.binding.practiceUtc).get();check(allocation.status==storage::Status::Confirmed&&!allocation.owner.empty(),"saved summary fixture allocates the Attempt against the Session");attemptRequest.binding.owner=allocation.owner;practice::Coordinator coordinator;beginAttempt(coordinator,attemptRequest.binding,attemptConfiguration);check(coordinator.progress(capture_fixture::progress(coordinator,16000,practice::State::Ended)),"saved summary fixture reaches a stopped Attempt result");const auto envelope=capture::makeEnvelope(coordinator,attemptRequest.binding,nullptr,capture::Outcome::Stop);check(store.seal("guided-saved-attempt-summary-seal",envelope.owner,envelope.bytes).get().status==storage::Status::Confirmed&&store.commit("guided-saved-attempt-summary-commit",envelope.owner,envelope.bytes).get().status==storage::Status::Confirmed,"saved summary fixture finalizes the Attempt");
            view.noteSavedPracticeAttempt();check(view.busy(),"saved summary fixture begins the existing summary refresh");while(view.busy()){view.service();pump();}const auto linkedSummary=view.sessionSummaryText();check(linkedSummary.find("SAVED ATTEMPT\nSaved Practice Attempt: linked to this Guided Session")!=std::string::npos,"active linked summary exposes the exact Saved Attempt marker");check(linkedSummary.find(activeSessionId)!=std::string::npos&&linkedSummary.find("Source case: fg:item:000002 / fg:variant:000006")!=std::string::npos&&linkedSummary.find("Source refs: L3-TXT5-21, L3-TXT28-46")!=std::string::npos&&linkedSummary.find("Content version: representative-controls.1")!=std::string::npos&&linkedSummary.find("No curriculum progress")!=std::string::npos,"active linked summary preserves Session, source, content and no-credit facts");
            for(const auto* id:{"guided-heading","guided-status","session-summary","plan","guided-audio-settings","open-first","start","stop","interrupt","back"})assertContained(view,id,std::string("active linked Guided surface remains contained: ")+id);
            check(linkedSummary.find("Lesson title: ModeA Exercise001 full selected directions")!=std::string::npos&&linkedSummary.find("Variant label: sixteenths-ascending-D-even")!=std::string::npos,"active linked summary exposes Catalog lesson title and variant label");
            check(view.stopSession()&&view.busy(),"saved summary fixture submits the same Session close");while(view.busy()){view.service();pump();}check(!view.running()&&view.sessionSummaryText().find("SAVED ATTEMPT\nSaved Practice Attempt: linked to this Guided Session")!=std::string::npos&&view.sessionSummaryText().find("Outcome: partial")!=std::string::npos,"closed linked summary preserves the marker and existing outcome facts");
            for(const auto* id:{"guided-heading","guided-status","session-summary","plan","guided-audio-settings","open-first","start","open-progress","back"})assertContained(view,id,std::string("closed linked Guided surface remains contained: ")+id);
            auto snapshotFuture=store.snapshot("guided-saved-attempt-summary-final");auto snapshot=storage::ProfileStore::waitForAcknowledgment(snapshotFuture);check(snapshot.status==storage::Status::Confirmed&&rows(snapshot.data,"session")==1&&rows(snapshot.data,"session_close")==1&&rows(snapshot.data,"identity")==1&&rows(snapshot.data,"finalized")==1,"saved summary fixture preserves one Session, close and finalized Attempt lineage");
            desktop::GuidedSessionView reopened;reopened.setSize(920,680);reopened.setVisible(true);reopened.setCatalog(catalog);
            check(reopened.configureStore(store,[]{return std::string("2026-09-14T00:56:00Z");},"America/New_York"),"saved summary fixture reopens the same local Store");while(reopened.busy()){reopened.service();pump();}
            const auto assertReopenedContained=[&](const char* id){auto* component=reopened.findChildWithID(id);check(component&&component->isVisible()&&reopened.getLocalBounds().contains(component->getBounds()),std::string("reopened Guided surface remains contained: ")+id);};
            for(const auto* id:{"guided-heading","guided-status","session-summary","plan","guided-audio-settings","open-first","start","open-progress","back"})assertReopenedContained(id);
            check(reopened.sessionSummaryText().find("Lesson title: ModeA Exercise001 full selected directions")!=std::string::npos&&reopened.sessionSummaryText().find("Variant label: sixteenths-ascending-D-even")!=std::string::npos,"reopened Guided summary preserves Catalog lesson title and variant label");
            check(reopened.sessionSummaryText().find(activeSessionId)!=std::string::npos&&reopened.sessionSummaryText().find("Source case: fg:item:000002 / fg:variant:000006")!=std::string::npos&&reopened.sessionSummaryText().find("Outcome: partial")!=std::string::npos,"reopened contained surface preserves the exact Session, source and outcome facts");
            std::ofstream(evidence/"summary.json")<<"{\"checks\":"<<checks<<",\"status\":\"PASS\",\"sessionLifecycle\":true,\"savedAttemptMarker\":true,\"finalizedAttempts\":1}\n";std::cout<<"PASS "<<checks<<" Guided saved Attempt summary checks\n";return 0;
        }

        if(guidedProgressHandoffOnly){
            desktop::GuidedSessionView view;view.setSize(920,680);view.setVisible(true);
            auto* progress=dynamic_cast<juce::TextButton*>(view.findChildWithID("open-progress"));
            auto* stop=dynamic_cast<juce::TextButton*>(view.findChildWithID("stop"));
            check(progress&&!progress->isVisible()&&!progress->isEnabled(),"initial Guided view keeps the saved-summary Progress handoff hidden");
            storage::StoreOptions options;options.path=evidence/"profile.sqlite";options.create=true;options.createdUtc="2026-09-19T12:59:17Z";
            storage::ProfileStore store(options);auto catalog=lesson::Catalog::load(bundle);view.setCatalog(catalog);
            check(view.buildPlan(),"handoff fixture builds the retained source-backed Guided plan");
            check(view.configureStore(store,[]{return std::string("2026-09-19T12:59:18Z");},"America/New_York"),"handoff fixture binds the existing local Store");while(view.busy()){view.service();pump();}
            int progressCalls{};view.onProgressPage=[&]{++progressCalls;};
            check(view.startSession()&&view.busy(),"handoff fixture starts one local Guided Session");while(view.busy()){view.service();pump();}
            check(view.running()&&progress&&!progress->isVisible()&&!progress->isEnabled(),"active Guided view keeps the saved-summary Progress handoff hidden");
            const auto activeSessionId=view.sessionId();const auto admitted=catalog->admit("fg:item:000002","fg:variant:000006");
            check(admitted&&admitted->practiceAllowed(),"handoff fixture uses the retained admitted source case");const auto attemptConfiguration=admitted->practiceConfiguration(8000,120);auto attemptRequest=capture::lessonStart(*admitted,attemptConfiguration,activeSessionId,"2026-09-19T12:59:20Z","America/New_York",1,false);auto allocation=store.allocate("guided-progress-handoff-allocate",attemptRequest.binding.kind,attemptRequest.binding.context,attemptRequest.binding.practiceUtc).get();check(allocation.status==storage::Status::Confirmed&&!allocation.owner.empty(),"handoff fixture allocates the Attempt against the Guided Session");attemptRequest.binding.owner=allocation.owner;practice::Coordinator coordinator;beginAttempt(coordinator,attemptRequest.binding,attemptConfiguration);check(coordinator.progress(capture_fixture::progress(coordinator,16000,practice::State::Ended)),"handoff fixture reaches a stopped Attempt result");const auto envelope=capture::makeEnvelope(coordinator,attemptRequest.binding,nullptr,capture::Outcome::Stop);check(store.seal("guided-progress-handoff-seal",envelope.owner,envelope.bytes).get().status==storage::Status::Confirmed&&store.commit("guided-progress-handoff-commit",envelope.owner,envelope.bytes).get().status==storage::Status::Confirmed,"handoff fixture finalizes the Guided-owned Attempt");
            view.noteSavedPracticeAttempt();check(view.busy(),"saved Attempt begins the existing Guided summary refresh");while(view.busy()){view.service();pump();}
            auto* linkedStatus=dynamic_cast<juce::Label*>(view.findChildWithID("guided-status"));check(linkedStatus&&linkedStatus->getHeight()>=110,"linked Guided status reserves readable space for exact source provenance and Stop next action");
            check(view.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session")!=std::string::npos&&view.sessionSummaryText().find(activeSessionId)!=std::string::npos&&view.sessionSummaryText().find("Source case: fg:item:000002 / fg:variant:000006")!=std::string::npos&&view.sessionSummaryText().find("Content revision: 2")!=std::string::npos&&view.sessionSummaryText().find("No curriculum progress")!=std::string::npos,"saved summary preserves Session, source, exact content revision and no-credit facts before close");
            check(stop&&stop->getButtonText().toStdString()=="Stop & save Guided summary"&&stop->getTitle().toStdString()=="Stop Guided and save this Session with its linked Practice summary.","saved Guided-owned Stop exposes the exact linked-summary destination without changing its visible action");
            check(view.stopSession()&&view.busy(),"saved summary submits the existing Guided close");while(view.busy()){view.service();pump();}
            check(!view.running()&&progress&&progress->isVisible()&&progress->isEnabled()&&progress->getTitle().toStdString()=="Open read-only Progress for saved Guided Session " + activeSessionId + " with its linked Practice Attempt; no new Session or Attempt is created.","closed saved summary exposes the explicit read-only Progress destination");
            const auto closedSummary=view.sessionSummaryText();
            check(closedSummary.find(activeSessionId)!=std::string::npos&&closedSummary.find("Outcome: partial (stopped before planned duration)")!=std::string::npos&&closedSummary.find("Content revision: 2")!=std::string::npos&&closedSummary.find("No curriculum progress")!=std::string::npos,"closed Guided summary retains Session outcome, exact content revision and no-credit facts");
            auto* savedBack=dynamic_cast<juce::TextButton*>(view.findChildWithID("back"));
            check(savedBack&&savedBack->getTitle().toStdString()=="Return to Home after saved Guided Session " + activeSessionId + "; linked Practice Attempt remains read-only.","closed Guided summary Back exposes the settled Home destination without changing the Back label or behavior");
            check(view.requestProgressPage()&&progressCalls==1,"saved summary Progress handoff invokes the existing callback exactly once");
            desktop::GuidedSessionView reopened;reopened.setCatalog(catalog);
            check(reopened.configureStore(store,[]{return std::string("2026-09-19T13:00:00Z");},"America/New_York"),"reopened Guided summary binds the same local Store");while(reopened.busy()){reopened.service();pump();}
            const auto reopenedSummary=reopened.sessionSummaryText();
            check(!reopened.running()&&reopenedSummary.find(activeSessionId)!=std::string::npos&&reopenedSummary.find("Source case: fg:item:000002 / fg:variant:000006")!=std::string::npos&&reopenedSummary.find("Source refs: L3-TXT5-21, L3-TXT28-46")!=std::string::npos&&reopenedSummary.find("Content version: representative-controls.1")!=std::string::npos&&reopenedSummary.find("Content revision: 2")!=std::string::npos&&reopenedSummary.find("Outcome: partial (stopped before planned duration)")!=std::string::npos&&reopenedSummary.find("No curriculum progress")!=std::string::npos,"reopened Guided summary retains exact source provenance, outcome and no-credit facts");
            check(reopened.statusText().find("Linked saved Practice Attempt:")!=std::string::npos&&reopened.statusText().find("Source case: fg:item:000002 / fg:variant:000006")!=std::string::npos&&reopened.statusText().find("Workbook identity: fg:workbook:000003 | Level: 3")!=std::string::npos&&reopened.statusText().find("Lesson title: ModeA Exercise001 full selected directions")!=std::string::npos&&reopened.statusText().find("Variant label: sixteenths-ascending-D-even")!=std::string::npos&&reopened.statusText().find("Source refs: L3-TXT5-21, L3-TXT28-46")!=std::string::npos&&reopened.statusText().find("Content version: representative-controls.1")!=std::string::npos&&reopened.statusText().find("Content revision: 2")!=std::string::npos&&reopened.statusText().find("Next action: choose Review Progress (read-only) for a read-only activity review, or Start Guided session to begin a new local Session.")!=std::string::npos,"reopened Guided status preserves linked Attempt provenance and exact read-only next actions");
            auto reopenedFuture=store.snapshot("guided-progress-handoff-reopen");const auto reopenedSnapshot=storage::ProfileStore::waitForAcknowledgment(reopenedFuture);
            check(reopenedSnapshot.status==storage::Status::Confirmed&&rows(reopenedSnapshot.data,"session")==1&&rows(reopenedSnapshot.data,"session_close")==1&&rows(reopenedSnapshot.data,"finalized")==1,"reopened Guided summary read creates no duplicate Session, close or Attempt rows");
            capture_fixture::write(evidence/"summary.txt",view.sessionSummaryText());
            std::ofstream(evidence/"summary.json")<<"{\"checks\":"<<checks<<",\"status\":\"PASS\",\"sessionLifecycle\":true,\"savedSummaryProgressHandoff\":true,\"progressCalls\":1}\n";std::cout<<"PASS "<<checks<<" Guided Progress handoff checks\n";return 0;
        }

        desktop::GuidedSessionView unavailable;
        unavailable.setSize(920, 680);
        check(!unavailable.buildPlan()
                  && unavailable.planText().find("Open Learn to load the bundled source records, return here and choose Build plan") != std::string::npos
                  && unavailable.planText().find("rebuild this preview with its bundled source records") != std::string::npos
                  && unavailable.statusText().find("no guided plan was fabricated") != std::string::npos
                  && unavailable.statusText().find("then choose Build plan") != std::string::npos,
              "missing Guided catalog gives an exact Learn-return-Build recovery without fabricating a plan");
        desktop::GuidedSessionView disconnectedBack;
        disconnectedBack.setSize(920, 680);
        int disconnectedBackCalls{};
        check(!disconnectedBack.requestBack()
                  && disconnectedBack.statusText() == "Back is unavailable from Guided until the existing Home navigation is connected. No Guided Session or summary state was changed; use the existing Home navigation when connected. Next action: reconnect the existing Home navigation, then choose Back."
                  && disconnectedBack.sessionSummaryText().find("no Guided Session has been saved") != std::string::npos,
              "missing Guided Back callback gives exact recovery without changing the initial summary");
        disconnectedBack.onBack = [&] { ++disconnectedBackCalls; };
        check(disconnectedBack.requestBack() && disconnectedBackCalls == 1,
              "connected Guided Back callback is delivered exactly once");

        storage::StoreOptions options;
        options.path = evidence / "profile.sqlite";
        options.create = true;
        options.createdUtc = "2026-09-14T00:55:00Z";
        std::atomic<int> forcedCloseFailures{1};
        options.diagnosticHook = [&](const std::string& phase, const std::string& operation) {
            if (phase == "before_operation" && operation.find("guided-session/close/") == 0
                && forcedCloseFailures.exchange(0) == 1) throw std::runtime_error("TEST forced first Guided close failure");
        };
        storage::ProfileStore store(options);
        auto catalog = lesson::Catalog::load(bundle);
        desktop::GuidedSessionView disconnectedLearn;
        disconnectedLearn.setSize(920, 680);
        disconnectedLearn.setCatalog(catalog);
        check(disconnectedLearn.buildPlan(), "disconnected Learn handoff fixture builds retained plan");
        auto* openFirstLearn = dynamic_cast<juce::TextButton*>(disconnectedLearn.findChildWithID("open-first"));
        check(openFirstLearn && openFirstLearn->isEnabled(), "disconnected Learn handoff remains actionable for recovery");
        openFirstLearn->onClick();
        check(disconnectedLearn.statusText() == "Learn is unavailable from Guided until the existing Learn page is connected. Return to Home and choose Learn to open the retained admitted source-backed case; no Practice activity or source case was opened.",
              "missing Guided Learn callback gives exact Home-to-Learn recovery");
        check(disconnectedLearn.planText().find("fg:item:000002") != std::string::npos,
              "missing Guided Learn callback preserves the retained admitted source case in the plan");
        check(disconnectedLearn.sessionSummaryText().find("no Guided Session has been saved") != std::string::npos,
              "missing Guided Learn callback does not create a Session summary");
        std::string openedLearnItem, openedLearnVariant;
        disconnectedLearn.onOpenLesson = [&](const std::string& item, const std::string& variant) {
            openedLearnItem = item;
            openedLearnVariant = variant;
            return true;
        };
        openFirstLearn->onClick();
        check(openedLearnItem == "fg:item:000002" && openedLearnVariant == "fg:variant:000006"
                  && disconnectedLearn.statusText().find("Learn opened with admitted fg:item:000002 / fg:variant:000006 in Learn. No practice credit was created.") != std::string::npos,
              "connected Guided Learn callback opens the exact first admitted source case once");
        desktop::GuidedSessionView view;
        view.setSize(920, 680);
        int progressCalls{};
        view.onProgressPage = [&] { ++progressCalls; };
        check(view.statusText() == "Opening Guided does not start sound or create a Session. Choose a duration and build a source-backed plan. Next action: choose a duration, then choose Build Guided plan.",
              "initial Guided status names the exact duration and Build plan next actions");
        view.setCatalog(catalog);
        const auto* explanation = dynamic_cast<const juce::Label*>(view.findChildWithID("guided-explanation"));
        check(explanation
                  && explanation->getText().toStdString().find("Choose 10, 20, 30, 45 or 60 minutes, or enter a custom whole-minute duration from 1 to 240.") != std::string::npos
                  && explanation->getText().toStdString().find("After Start: open a source-backed case in Learn, save its Practice Attempt, then return here for the linked Guided summary.") != std::string::npos
                  && explanation->getText().toStdString().find("The active Guided Session owns that Attempt; it remains separate from curriculum credit.") != std::string::npos
                  && explanation->getText().toStdString().find("Refused cases remain out of Practice; an unresolved close stays retryable.") != std::string::npos,
              "Guided explanation states supported durations, the existing Learn/save/summary path and refusal/retry boundaries");
        check(view.sessionSummaryText().find("no Guided Session has been saved") != std::string::npos
                  && view.sessionSummaryText().find("Start creates one local Guided Session; no saved outcome exists yet.") != std::string::npos,
              "initial summary does not invent a saved Session");
        check(view.planText().find("GUIDED PLAN") != std::string::npos, "actual catalog creates initial deterministic plan");
        check(view.planText().find("Plan feasibility: one local Guided Session uses the selected whole-minute budget; this Development Preview does not allocate time per case.") != std::string::npos,
              "plan explains one Session budget without inventing per-case scheduling");
        check(view.planText().find(catalog->lessons().front().id) != std::string::npos
                  && view.planText().find(catalog->contentVersion()) != std::string::npos,
              "plan retains actual source identity and content version");
        check(view.planText().find("[" + catalog->lessons().front().id + "] | Variants available: "
                                      + std::to_string(catalog->lessons().front().variants.size()) + " | Revision: "
                                      + storage::canonical(field(catalog->lessons().front().record, "content_revision"))) != std::string::npos,
              "plan row discloses exact loaded content revision");
        for (std::size_t index = 0; index < std::min<std::size_t>(3, catalog->lessons().size()); ++index) {
            const auto& record = catalog->lessons()[index].record;
            const auto expected = " | Workbook: " + field(record, "workbook_id").string()
                + " | Level: " + storage::canonical(field(record, "legacy_level"));
            check(view.planText().find(expected) != std::string::npos,
                  "plan row discloses catalog-derived workbook and level " + catalog->lessons()[index].id);
        }
        check(view.planText().find("Plan preview: showing 3 of 13 retained source-backed cases.") != std::string::npos,
              "plan discloses the bounded rendered preview count");
        check(view.planText().find("Migration: 13 of 105 approved workbook identities packaged; 92 remain outside this Development Preview | Additional workbook identities represented by selected cases: 0 | Whole-workbook completion from these cases: 0 | Curriculum review: Pending") != std::string::npos,
              "plan discloses the exact packaged, imported/admitted, remaining and Curriculum disposition without acceptance");
        check(view.planText().find("Practice handoff: first practice-ready case in Learn is fg:item:000002 / fg:variant:000006 | Variant label: sixteenths-ascending-D-even | Source refs: L3-TXT5-21, L3-TXT28-46") != std::string::npos,
              "plan identifies the exact first catalog case and variant admitted for Practice handoff");
        check(view.planText().find("Source: L1-TXT2-15") != std::string::npos
                  && view.planText().find("Source: L3-TXT5-21, L3-TXT28-46") != std::string::npos,
              "plan rows retain exact package-order source references");
        auto* audio = dynamic_cast<juce::TextButton*>(view.findChildWithID("guided-audio-settings"));
        int audioCalls{};
        const auto planBeforeAudio = view.planText();
        check(audio && audio->isEnabled(), "Guided Audio settings remains actionable for callback recovery");
        audio->onClick();
        check(audioCalls == 0
                  && view.planText() == planBeforeAudio
                  && !view.running()
                  && view.statusText().find("Audio settings are unavailable from Guided until the existing shared Audio page is connected") != std::string::npos
                  && view.statusText().find("Return to Home and choose Audio settings") != std::string::npos
                  && view.statusText().find("no Guided Session or sound was started") != std::string::npos,
              "missing Guided Audio callback gives Home recovery without creating a Session or starting sound");
        view.onAudioSettings = [&] { ++audioCalls; };
        check(view.buildPlan() && audio->isEnabled(), "Guided Audio settings remains available for the existing plan");
        audio->onClick();
        check(audioCalls == 1, "Guided Audio settings invokes its safe callback without changing the plan");
        for (std::size_t index = 0; index < std::min<std::size_t>(3, catalog->lessons().size()); ++index)
            check(view.planText().find("[" + catalog->lessons()[index].id + "] | Variants available: "
                                      + std::to_string(catalog->lessons()[index].variants.size())) != std::string::npos,
                  "plan row discloses catalog-derived variant count " + catalog->lessons()[index].id);
        for (std::size_t index = 0; index < std::min<std::size_t>(3, catalog->lessons().size()); ++index)
            check(view.planText().find(admissionDisclosure(*catalog, catalog->lessons()[index])) != std::string::npos,
                  "plan row discloses catalog-derived admission " + catalog->lessons()[index].id);

        auto* open = dynamic_cast<juce::TextButton*>(view.findChildWithID("open-first"));
        check(open && open->isEnabled(), "Learn handoff remains actionable for callback recovery");
        std::string openedItem, openedVariant;
        view.onOpenLesson = [&](const std::string& id, const std::string& variant) { openedItem = id; openedVariant = variant; return true; };
        view.buildPlan();
        check(open && open->isEnabled() && open->getButtonText() == "Open selected case in Learn" && open->getTitle().contains("Open admitted fg:item:000002 / fg:variant:000006 in Learn") && open->getTitle().contains("Practice Start remains explicit"),
              "Learn handoff identifies and enables the exact first practice-ready case and variant");
        open->onClick();
        check(openedItem == "fg:item:000002" && openedVariant == "fg:variant:000006"
                  && openedItem != catalog->lessons().front().id,
              "Learn handoff skips the refused first catalog item and preserves the exact admitted item and variant");
        check(view.statusText().find("Learn opened with admitted fg:item:000002 / fg:variant:000006 in Learn. No practice credit was created.") != std::string::npos,
              "Learn handoff reports the admitted source-backed case");
        view.onOpenLesson = [](const std::string&, const std::string&) { return false; };
        open->onClick();
        check(view.statusText().find("first practice-ready source-backed case could not be opened in Learn") != std::string::npos
                  && view.statusText().find("Return to Learn to choose an admitted source-backed case manually") != std::string::npos
                  && view.statusText().find("no replacement case was loaded") != std::string::npos,
              "failed Learn handoff gives manual admitted-case recovery without loading a replacement");
        view.onOpenLesson = [&](const std::string& id, const std::string& variant) {
            openedItem = id;
            openedVariant = variant;
            return true;
        };

        auto* duration = dynamic_cast<juce::ComboBox*>(view.findChildWithID("duration"));
        auto* custom = dynamic_cast<juce::ComboBox*>(view.findChildWithID("custom"));
        auto* build = dynamic_cast<juce::TextButton*>(view.findChildWithID("build"));
        if (!duration || !custom || !build) throw std::runtime_error("Guided duration controls missing");
        const std::array<int, 5> expected{10, 20, 30, 45, 60};
        for (int id = 1; id <= 5; ++id) {
            duration->setSelectedId(id, juce::sendNotificationSync);
            check(view.selectedMinutes() == expected[static_cast<std::size_t>(id - 1)], "predefined duration " + std::to_string(id));
            check(view.buildPlan(), "predefined plan builds " + std::to_string(id));
            check(build->getButtonText() == "Build Guided plan" && build->isEnabled(),
                  "plan-ready Guided builder identifies plan construction " + std::to_string(id));
            check(view.statusText().find("Plan ready. Start creates one local Guided Session from the retained source records; no curriculum credit is created.") != std::string::npos,
                  "plan-ready status identifies the next local Session action");
            auto* start = dynamic_cast<juce::TextButton*>(view.findChildWithID("start"));
            check(start && start->getButtonText() == "Start Guided session",
                  "plan-ready Guided action identifies the new local Session; bound store controls enablement");
            check(view.planText().find("Plan feasibility: one local Guided Session uses the selected whole-minute budget; this Development Preview does not allocate time per case.") != std::string::npos
                      && view.planText().find("Duration: " + std::to_string(expected[static_cast<std::size_t>(id - 1)]) + " minutes") != std::string::npos
                      && view.planText().find(std::to_string(expected[static_cast<std::size_t>(id - 1)] * 60) + " seconds") != std::string::npos,
                  "predefined duration has exact feasibility and seconds disclosure " + std::to_string(expected[static_cast<std::size_t>(id - 1)]));
        }
        duration->setSelectedId(6, juce::sendNotificationSync);
        custom->setText("1", juce::dontSendNotification);
        check(view.buildPlan() && view.selectedMinutes() == 1
                  && view.planText().find("Plan feasibility: one local Guided Session uses the selected whole-minute budget; this Development Preview does not allocate time per case.") != std::string::npos
                  && view.planText().find("Duration: 1 minutes") != std::string::npos && view.planText().find("60 seconds") != std::string::npos,
              "custom lower bound has exact feasibility and seconds disclosure");
        custom->setText("240", juce::dontSendNotification);
        check(view.buildPlan() && view.selectedMinutes() == 240
                  && view.planText().find("Plan feasibility: one local Guided Session uses the selected whole-minute budget; this Development Preview does not allocate time per case.") != std::string::npos
                  && view.planText().find("Duration: 240 minutes") != std::string::npos && view.planText().find("14400 seconds") != std::string::npos,
              "custom upper bound has exact feasibility and seconds disclosure");
        for (const auto& invalid : {std::string(""), std::string("0"), std::string("241"), std::string("15.5")}) {
            custom->setText(invalid, juce::dontSendNotification);
            check(!view.buildPlan() && view.statusText().find("minute") != std::string::npos
                      && view.statusText().find("Next action: correct the duration, then choose Build Guided plan.") != std::string::npos,
                  "invalid custom duration rejected: " + (invalid.empty() ? std::string("blank") : invalid));
        }
        custom->setText("10", juce::dontSendNotification);
        check(view.buildPlan() && view.selectedMinutes() == 10, "10-minute plan restored");
        check(view.planText().find("Duration: 10 minutes") != std::string::npos
                  && view.planText().find("600 seconds") != std::string::npos,
              "plan visibly binds whole-minute duration to exact seconds");
        check(view.configureStore(store, [] { return std::string("2026-09-14T00:55:10Z"); }, "America/New_York"),
              "guided view binds existing local Store");
        while (view.busy()) { view.service(); pump(); }
        check(view.sessionSummaryText().find("no Guided Session has been saved") != std::string::npos,
              "initial profile read keeps the honest no-saved summary");
        auto* progress = dynamic_cast<juce::TextButton*>(view.findChildWithID("open-progress"));
        check(progress && !progress->isVisible() && !progress->isEnabled(),
              "Guided Progress handoff stays hidden before a confirmed Session close");

        int backCalls{};
        view.onBack = [&] { ++backCalls; };
        check(view.startSession() && view.busy() && !view.canLeave(), "Start submits one local Session");
        while (view.busy()) { view.service(); pump(); }
        check(view.running() && !view.sessionId().empty() && !view.canLeave(), "confirmed Session becomes the active identity");
        check(view.statusText().find("Guided Session running locally. Save a Practice result before Guided summary becomes available. Stop saves this Session; no curriculum progress is created.") != std::string::npos
                  && view.statusText().find("Open the admitted case in Learn, then use explicit Practice Start; no Attempt exists before that.") != std::string::npos
                  && view.statusText().find("Next action: open the admitted case in Learn, then choose explicit Practice Start and save the result before returning for Guided summary.") != std::string::npos,
              "active Guided status requires a saved Practice result before its summary and names the next action");
        check(progress && !progress->isVisible() && !view.requestProgressPage() && progressCalls == 0
                  && view.statusText().find("Next action: choose Stop Guided session to save this Session, then choose Review Progress.") != std::string::npos,
              "active Guided Session refuses the Progress handoff and names Stop-and-save recovery without creating activity");
        const auto activeSessionId = view.sessionId();
        auto* stop = dynamic_cast<juce::TextButton*>(view.findChildWithID("stop"));
        check(stop && stop->getButtonText() == "Stop Guided session", "active Guided Session exposes the normal Stop Guided session action");
        check(view.sessionSummaryText().find(activeSessionId) != std::string::npos
                  && view.sessionSummaryText().find("Duration: 10 minutes (600 seconds)") != std::string::npos
                  && view.sessionSummaryText().find("No curriculum progress") != std::string::npos
                  && view.sessionSummaryText().find("Stop saves this same Session; an unresolved close stays retryable.") != std::string::npos
                  && view.sessionSummaryText().find("This active Guided Session owns any Practice Attempt saved from it.") != std::string::npos,
              "active summary identifies the exact Session, planned duration, no-credit, close retry and Attempt-ownership contracts");
        check(open && open->isEnabled(), "Learn handoff remains available for the active Session");
        openedItem.clear();
        open->onClick();
        check(openedItem == "fg:item:000002" && view.running() && view.sessionId() == activeSessionId,
              "active handoff preserves the first admitted case, Session owner and running state");
        auto startedFuture = store.snapshot("guided-before-close");
        auto started = storage::ProfileStore::waitForAcknowledgment(startedFuture);
        check(started.status == storage::Status::Confirmed && rows(started.data, "session") == 1
                  && rows(started.data, "identity") == 0 && rows(started.data, "finalized") == 0,
              "start creates only the planned Session and no practice fact");
        const auto sessionRow = field(field(started.data, "authoritative"), "session").array().front();
        check(sessionRow.isArray() && sessionRow.array().size() == 5 && sessionRow.array()[3] == json::Value::fromInteger(600),
              "Session stores the selected ten-minute budget");
        check(!view.requestBack() && backCalls == 0
                  && view.statusText().find("Next action: choose Stop Guided session to save this Session, then choose Back.") != std::string::npos,
              "Back refusal while guided Session is running names the Stop-and-save recovery action");
        const auto admitted = catalog->admit("fg:item:000002", "fg:variant:000006");
        check(admitted && admitted->practiceAllowed(), "saved-Attempt fixture uses the retained admitted source case");
        const auto attemptConfiguration = admitted->practiceConfiguration(8000, 120);
        auto attemptRequest = capture::lessonStart(*admitted, attemptConfiguration, activeSessionId,
                                                   "2026-09-14T00:55:12Z", "America/New_York", 1, false);
        auto attemptAllocation = store.allocate("guided-saved-attempt-allocate", attemptRequest.binding.kind,
                                                attemptRequest.binding.context, attemptRequest.binding.practiceUtc).get();
        check(attemptAllocation.status == storage::Status::Confirmed && !attemptAllocation.owner.empty(),
              "source-backed Attempt allocates against the active Guided Session");
        attemptRequest.binding.owner = attemptAllocation.owner;
        practice::Coordinator attemptCoordinator;
        beginAttempt(attemptCoordinator, attemptRequest.binding, attemptConfiguration);
        check(attemptCoordinator.progress(capture_fixture::progress(attemptCoordinator, 16000, practice::State::Ended)),
              "source-backed Attempt reaches a stopped persisted result");
        const auto attemptEnvelope = capture::makeEnvelope(attemptCoordinator, attemptRequest.binding, nullptr, capture::Outcome::Stop);
        check(store.seal("guided-saved-attempt-seal", attemptEnvelope.owner, attemptEnvelope.bytes).get().status == storage::Status::Confirmed
                  && store.commit("guided-saved-attempt-commit", attemptEnvelope.owner, attemptEnvelope.bytes).get().status == storage::Status::Confirmed,
              "source-backed Attempt is finalized before Guided close");
        check(attemptRequest.binding.context.find("item_id")->string() == "fg:item:000002"
                  && attemptRequest.binding.context.find("variant_id")->string() == "fg:variant:000006"
                  && attemptRequest.binding.context.find("session_id")->string() == activeSessionId,
              "finalized Attempt preserves exact source and Guided Session identities");
        view.noteSavedPracticeAttempt();
        check(view.busy() && view.statusText().find("Stop is temporarily unavailable while the local summary refresh completes") != std::string::npos,
              "saved Attempt handoff explains the temporary Stop readiness boundary");
        while (view.busy()) { view.service(); pump(); }
        check(view.statusText().find("Next action: choose Stop & save Guided summary.") != std::string::npos
                  && view.statusText().find("Stop saves this Session") != std::string::npos
                  && view.statusText().find("separate from curriculum progress") != std::string::npos
                  && view.statusText().find("Linked saved Practice Attempt:") != std::string::npos
                  && view.statusText().find("Source case: fg:item:000002 / fg:variant:000006") != std::string::npos
                  && view.statusText().find("Source refs: L3-TXT5-21, L3-TXT28-46") != std::string::npos
                  && view.statusText().find("Content version: representative-controls.1") != std::string::npos
                  && view.statusText().find("Content revision: 2") != std::string::npos,
              "saved Attempt summary refresh announces safe Stop readiness with exact linked source provenance");
        check(stop->getButtonText() == "Stop & save Guided summary",
              "saved Attempt summary exposes the explicit Stop and Guided-summary action");
        check(view.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session") != std::string::npos
                  && view.sessionSummaryText().find("Source case: fg:item:000002 / fg:variant:000006") != std::string::npos
                  && view.sessionSummaryText().find("Source refs: L3-TXT5-21, L3-TXT28-46") != std::string::npos
                  && view.sessionSummaryText().find("Content version: representative-controls.1") != std::string::npos
                  && view.sessionSummaryText().find("Elapsed:") != std::string::npos,
              "active saved Attempt summary discloses source identity, content version and elapsed context before close");
        const auto savedAttemptSummaryBeforeProgressRefusal = view.sessionSummaryText();
        check(!view.requestProgressPage()
                  && view.statusText().find("Next action: choose Stop & save Guided summary, then choose Review Progress.") != std::string::npos
                  && view.sessionSummaryText() == savedAttemptSummaryBeforeProgressRefusal,
              "active saved Attempt refuses the Progress handoff and names the Guided-summary recovery without mutating the summary");
        check(view.stopSession() && view.busy(), "Stop submits close for the same Session");
        while (view.busy()) { view.service(); pump(); }
        check(view.running() && stop->getButtonText() == "Retry stop" && view.sessionId() == activeSessionId
                  && view.statusText().find("close unresolved") != std::string::npos
                  && view.statusText().find("Next action: choose Retry stop to resubmit the close for this same Session.") != std::string::npos
                  && view.sessionSummaryText().find("No saved outcome is claimed") != std::string::npos
                  && view.sessionSummaryText().find("Outcome:") == std::string::npos,
              "failed close keeps the same active Session and exposes an honest Retry stop action");
        check(!view.requestBack() && backCalls == 0
                  && view.statusText().find("Next action: choose Retry stop to resolve this Session, then choose Back.") != std::string::npos,
              "Back refusal after an unresolved close names the Retry stop recovery action");
        check(view.stopSession() && view.busy(), "Retry stop resubmits the original Session close");
        while (view.busy()) { view.service(); pump(); }
        check(!view.running() && view.canLeave() && view.statusText().find("saved locally") != std::string::npos
                  && view.statusText().find("Linked saved Practice Attempt:") != std::string::npos
                  && view.statusText().find("Source case: fg:item:000002 / fg:variant:000006") != std::string::npos
                  && view.statusText().find("Source refs: L3-TXT5-21, L3-TXT28-46") != std::string::npos
                  && view.statusText().find("Content version: representative-controls.1") != std::string::npos
                  && view.statusText().find("Content revision: 2") != std::string::npos,
              "confirmed close produces honest local summary");
        check(view.statusText().find("Back is safe now; Start creates a new local Session.") != std::string::npos
                  && view.statusText().find("separate from curriculum progress") != std::string::npos
                  && view.statusText().find("Next action: choose Review Progress (read-only) for a read-only activity review, or Start Guided session to begin a new local Session.") != std::string::npos,
              "confirmed close states safe Back, new Session boundary and the next read-only review action");
        check(stop->getButtonText() == "Stop Guided session", "confirmed close restores the normal Stop Guided session label");
        check(view.sessionSummaryText().find(activeSessionId) != std::string::npos
                  && view.sessionSummaryText().find("Duration: 10 minutes (600 seconds)") != std::string::npos
                  && view.sessionSummaryText().find("Outcome: partial") != std::string::npos
                  && view.sessionSummaryText().find("Outcome: partial (stopped before planned duration)") != std::string::npos
                  && view.sessionSummaryText().find("Elapsed:") != std::string::npos
                  && view.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session") != std::string::npos
                  && view.sessionSummaryText().find("Source case: fg:item:000002 / fg:variant:000006") != std::string::npos
                  && view.sessionSummaryText().find("Workbook identity: fg:workbook:000003 | Level: 3") != std::string::npos
                  && view.sessionSummaryText().find("Source refs: L3-TXT5-21, L3-TXT28-46") != std::string::npos
                  && view.sessionSummaryText().find("Content version: representative-controls.1") != std::string::npos
                  && view.sessionSummaryText().find("No curriculum progress") != std::string::npos,
              "saved summary preserves identity, source case, source refs, content version, elapsed outcome and no-credit boundary");
        check(progress && progress->isVisible() && progress->isEnabled()
                  && progress->getButtonText() == "Review Progress (read-only)",
              "confirmed Guided summary exposes an explicit read-only Progress handoff");
        const auto savedSummaryBeforeUnavailableProgress = view.sessionSummaryText();
        view.onProgressPage = {};
        check(!view.requestProgressPage()
                  && view.statusText().find("Progress is unavailable from Guided until the existing Progress page is connected") != std::string::npos
                  && view.statusText().find("Return to Home and choose Progress to review saved local activity") != std::string::npos
                  && view.sessionSummaryText() == savedSummaryBeforeUnavailableProgress,
              "missing Progress callback gives Home-to-Progress recovery without mutating the saved summary");
        view.onProgressPage = [&] { ++progressCalls; };
        const auto savedSummaryBeforeProgress = view.sessionSummaryText();
        check(view.requestProgressPage() && progressCalls == 1 && view.sessionSummaryText() == savedSummaryBeforeProgress,
              "confirmed Guided summary opens read-only Progress without mutating the saved summary");
        auto finishedFuture = store.snapshot("guided-after-close");
        auto finished = storage::ProfileStore::waitForAcknowledgment(finishedFuture);
        check(finished.status == storage::Status::Confirmed && rows(finished.data, "session") == 1
                  && rows(finished.data, "session_close") == 1 && rows(finished.data, "identity") == 1
                  && rows(finished.data, "pending") == 0 && rows(finished.data, "finalized") == 1,
              "close preserves one Session/close pair and one finalized Attempt");
        check(view.requestBack() && backCalls == 1, "Back succeeds only after confirmed close");

        desktop::GuidedSessionView reopened;
        reopened.setCatalog(catalog);
        check(reopened.configureStore(store, [] { return std::string("2026-09-14T00:55:20Z"); }, "America/New_York"),
              "reopened Guided view binds the same local Store");
        while (reopened.busy()) { reopened.service(); pump(); }
        check(!reopened.running() && !reopened.stopSession(), "restored summary does not reattach an active Session");
        check(reopened.sessionSummaryText().find(activeSessionId) != std::string::npos
                  && reopened.sessionSummaryText().find("Duration: 10 minutes (600 seconds)") != std::string::npos
                  && reopened.sessionSummaryText().find("Outcome: partial") != std::string::npos
                  && reopened.sessionSummaryText().find("Outcome: partial (stopped before planned duration)") != std::string::npos
                  && reopened.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session") != std::string::npos
                  && reopened.sessionSummaryText().find("Source case: fg:item:000002 / fg:variant:000006") != std::string::npos
                  && reopened.sessionSummaryText().find("Workbook identity: fg:workbook:000003 | Level: 3") != std::string::npos
                  && reopened.sessionSummaryText().find("Source refs: L3-TXT5-21, L3-TXT28-46") != std::string::npos
                  && reopened.sessionSummaryText().find("Content version: representative-controls.1") != std::string::npos
                  && reopened.sessionSummaryText().find("No curriculum progress") != std::string::npos,
              "reopen restores exact Guided identity, linked Attempt source, content version, outcome and no-credit boundary");
        check(reopened.sessionSummaryText().find("Saved Guided Session history is read-only; Start creates a new local Session.") != std::string::npos
                  && reopened.sessionSummaryText().find("Open Progress reviews this saved Guided Session read-only; Start creates a new local Session.") != std::string::npos
                  && reopened.sessionSummaryText().find("Next action: choose Review Progress (read-only) for a read-only activity review, or Start Guided session to begin a new local Session.") != std::string::npos,
              "reopen states saved Guided history is read-only, names Progress review and Start creates a new Session");
        check(reopened.statusText().find("The last saved Guided Session was restored for viewing.") != std::string::npos
                  && reopened.statusText().find("Linked saved Practice Attempt:") != std::string::npos
                  && reopened.statusText().find("Source case: fg:item:000002 / fg:variant:000006") != std::string::npos
                  && reopened.statusText().find("Workbook identity: fg:workbook:000003 | Level: 3") != std::string::npos
                  && reopened.statusText().find("Lesson title: ModeA Exercise001 full selected directions") != std::string::npos
                  && reopened.statusText().find("Variant label: sixteenths-ascending-D-even") != std::string::npos
                  && reopened.statusText().find("Source refs: L3-TXT5-21, L3-TXT28-46") != std::string::npos
                  && reopened.statusText().find("Content version: representative-controls.1") != std::string::npos
                  && reopened.statusText().find("Content revision: 2") != std::string::npos
                  && reopened.statusText().find("Next action: choose Review Progress (read-only) for a read-only activity review, or Start Guided session to begin a new local Session.") != std::string::npos,
              "reopened Guided status preserves linked Attempt provenance and the exact read-only Progress or new Session next action");
        check(reopened.sessionSummaryText().find("Elapsed 00:00:") != std::string::npos,
              "reopen restores persisted elapsed time");
        auto reopenedFuture = store.snapshot("guided-after-summary-reopen");
        auto reopenedSnapshot = storage::ProfileStore::waitForAcknowledgment(reopenedFuture);
        check(reopenedSnapshot.status == storage::Status::Confirmed && rows(reopenedSnapshot.data, "session") == 1
                  && rows(reopenedSnapshot.data, "session_close") == 1 && rows(reopenedSnapshot.data, "identity") == 1
                  && rows(reopenedSnapshot.data, "finalized") == 1,
              "summary read creates no additional authoritative rows");

        check(view.buildPlan(), "fresh source-backed plan can be built after confirmed close");
        check(view.startSession() && view.busy(), "same Guided view can start a second local Session");
        while (view.busy()) { view.service(); pump(); }
        const auto secondSessionId = view.sessionId();
        check(view.running() && !secondSessionId.empty() && secondSessionId != activeSessionId,
              "fresh Guided Session receives a distinct owner after the prior close");
        check(view.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session") == std::string::npos,
              "fresh Guided Session does not inherit the prior saved Attempt acknowledgement");
        check(view.stopSession() && view.busy(), "second Guided Session submits its own close");
        while (view.busy()) { view.service(); pump(); }
        check(!view.running() && view.sessionSummaryText().find(secondSessionId) != std::string::npos
                  && view.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session") == std::string::npos,
              "second close keeps its own identity without stale saved Attempt acknowledgement");
        auto repeatedFuture = store.snapshot("guided-after-same-view-restart");
        auto repeated = storage::ProfileStore::waitForAcknowledgment(repeatedFuture);
        check(repeated.status == storage::Status::Confirmed && rows(repeated.data, "session") == 2
                  && rows(repeated.data, "session_close") == 2 && rows(repeated.data, "identity") == 1
                  && rows(repeated.data, "finalized") == 1 && rows(repeated.data, "pending") == 0,
              "same-view restart adds only the second Session/close pair and preserves the Attempt");

        desktop::GuidedSessionView interrupted;
        interrupted.setSize(920, 680);
        interrupted.setCatalog(catalog);
        check(interrupted.configureStore(store, [] { return std::string("2026-09-14T00:55:30Z"); }, "America/New_York"),
              "interruption view binds the same local Store");
        while (interrupted.busy()) { interrupted.service(); pump(); }
        check(interrupted.buildPlan() && interrupted.startSession() && interrupted.busy(),
              "interruption fixture starts a second planned Guided Session");
        while (interrupted.busy()) { interrupted.service(); pump(); }
        const auto interruptedSessionId = interrupted.sessionId();
        auto interrupt = dynamic_cast<juce::TextButton*>(interrupted.findChildWithID("interrupt"));
        check(interrupted.running() && interrupt && interrupt->getButtonText() == "Interrupt & leave unresolved" && interrupt->isEnabled(),
              "active Guided Session exposes the explicit Interrupt / leave action");
        auto beforeInterruptFuture = store.snapshot("guided-before-interrupt");
        auto beforeInterrupt = storage::ProfileStore::waitForAcknowledgment(beforeInterruptFuture);
        check(beforeInterrupt.status == storage::Status::Confirmed && rows(beforeInterrupt.data, "session") == 3
                  && rows(beforeInterrupt.data, "session_close") == 2 && rows(beforeInterrupt.data, "identity") == 1
                  && rows(beforeInterrupt.data, "finalized") == 1 && rows(beforeInterrupt.data, "pending") == 0,
              "interruption starts from the expected persisted Session/close boundary");
        interrupted.noteSavedPracticeAttempt();
        while (interrupted.busy()) { interrupted.service(); pump(); }
        check(interrupted.interruptSession() && !interrupted.running() && interrupted.canLeave(),
              "Interrupt / leave releases the local running state without a storage future");
        check(interrupted.statusText().find("Guided Session left unresolved before Stop. Back is safe now; the original Session remains unresolved. No saved outcome or curriculum progress was created.") != std::string::npos,
              "interrupted Guided Session states safe Back without claiming a close");
        check(!interrupted.startSession() && !interrupted.stopSession() && !interrupt->isEnabled(),
              "interrupted Guided Session cannot start a phantom Session or submit Stop");
        check(interrupted.sessionId() == interruptedSessionId
                  && interrupted.sessionSummaryText().find("interrupted local Session " + interruptedSessionId) != std::string::npos
                  && interrupted.sessionSummaryText().find("Duration: 10 minutes (600 seconds)") != std::string::npos
                  && interrupted.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session.") != std::string::npos
                  && interrupted.sessionSummaryText().find("No saved outcome is claimed") != std::string::npos
                  && interrupted.sessionSummaryText().find("No curriculum progress") != std::string::npos
                  && interrupted.sessionSummaryText().find("Outcome:") == std::string::npos,
              "interruption preserves exact identity and explicit unresolved no-outcome summary");
        auto afterInterruptFuture = store.snapshot("guided-after-interrupt");
        auto afterInterrupt = storage::ProfileStore::waitForAcknowledgment(afterInterruptFuture);
        check(afterInterrupt.status == storage::Status::Confirmed && afterInterrupt.data == beforeInterrupt.data,
              "Interrupt / leave creates no close, identity, finalized, pending or other storage mutation");
        bool interruptedBack{};
        interrupted.onBack = [&] { interruptedBack = true; };
        check(interrupted.requestBack() && interruptedBack, "Back succeeds after explicit unresolved interruption");
        check(!interrupted.presentationStoppedAndResolved(), "Interrupted Guided permits Back but refuses stopped-and-resolved settings save without closing its original Session");

        const auto unresolvedDirectory = evidence / "unresolved-profile";
        std::filesystem::create_directories(unresolvedDirectory);
        std::filesystem::permissions(unresolvedDirectory, std::filesystem::perms::owner_all, std::filesystem::perm_options::replace);
        storage::StoreOptions unresolvedOptions;
        unresolvedOptions.path = unresolvedDirectory / "profile.sqlite";
        unresolvedOptions.create = true;
        unresolvedOptions.createdUtc = "2026-09-14T00:56:00Z";
        storage::ProfileStore unresolvedStore(unresolvedOptions);
        auto unresolvedCreateFuture = unresolvedStore.createSession("guided-unresolved-create", "2026-09-14T00:56:10Z", "America/New_York", 600,
                                                                    json::Value::Object{{"version", "guided-session-plan.1"}});
        const auto unresolvedStart = storage::ProfileStore::waitForAcknowledgment(unresolvedCreateFuture);
        check(unresolvedStart.status == storage::Status::Confirmed && !unresolvedStart.owner.empty(),
              "unresolved fixture creates one planned Session without a close");
        desktop::GuidedSessionView unresolved;
        unresolved.setCatalog(catalog);
        check(unresolved.configureStore(unresolvedStore, [] { return std::string("2026-09-14T00:56:20Z"); }, "America/New_York"),
              "unresolved profile binds through the same snapshot path");
        while (unresolved.busy()) { unresolved.service(); pump(); }
        check(!unresolved.running() && !unresolved.startSession() && !unresolved.stopSession(),
              "unresolved planned Session cannot start a phantom Session or Stop without an owner");
        check(unresolved.sessionSummaryText().find("unresolved local Session " + unresolvedStart.owner) != std::string::npos
                  && unresolved.sessionSummaryText().find("Duration: 10 minutes (600 seconds)") != std::string::npos
                  && unresolved.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session.") == std::string::npos
                  && unresolved.sessionSummaryText().find("Source case:") == std::string::npos
                  && unresolved.sessionSummaryText().find("Source refs:") == std::string::npos
                  && unresolved.sessionSummaryText().find("No saved outcome is claimed") != std::string::npos
                  && unresolved.sessionSummaryText().find("No curriculum progress") != std::string::npos
                  && unresolved.sessionSummaryText().find("Outcome:") == std::string::npos,
              "unresolved summary preserves exact identity and refuses an invented outcome");
        auto unresolvedSnapshotFuture = unresolvedStore.snapshot("guided-unresolved-after-read");
        auto unresolvedSnapshot = storage::ProfileStore::waitForAcknowledgment(unresolvedSnapshotFuture);
        check(unresolvedSnapshot.status == storage::Status::Confirmed && rows(unresolvedSnapshot.data, "session") == 1
                  && rows(unresolvedSnapshot.data, "session_close") == 0 && rows(unresolvedSnapshot.data, "identity") == 0
                  && rows(unresolvedSnapshot.data, "finalized") == 0,
              "unresolved read leaves the original planned Session and practice tables unchanged");

        const auto unresolvedAttemptDirectory = evidence / "unresolved-attempt-profile";
        std::filesystem::create_directories(unresolvedAttemptDirectory);
        std::filesystem::permissions(unresolvedAttemptDirectory, std::filesystem::perms::owner_all, std::filesystem::perm_options::replace);
        storage::StoreOptions unresolvedAttemptOptions;
        unresolvedAttemptOptions.path = unresolvedAttemptDirectory / "profile.sqlite";
        unresolvedAttemptOptions.create = true;
        unresolvedAttemptOptions.createdUtc = "2026-09-14T00:57:00Z";
        storage::ProfileStore unresolvedAttemptStore(unresolvedAttemptOptions);
        auto unresolvedAttemptCreateFuture = unresolvedAttemptStore.createSession(
            "guided-unresolved-attempt-create", "2026-09-14T00:57:10Z", "America/New_York", 600,
            json::Value::Object{{"version", "guided-session-plan.1"}});
        const auto unresolvedAttemptSession = storage::ProfileStore::waitForAcknowledgment(unresolvedAttemptCreateFuture);
        check(unresolvedAttemptSession.status == storage::Status::Confirmed && !unresolvedAttemptSession.owner.empty(),
              "unresolved linked-Attempt fixture creates one planned Session without a close");
        const auto unresolvedAttemptConfiguration = admitted->practiceConfiguration(8000, 120);
        auto unresolvedAttemptRequest = capture::lessonStart(*admitted, unresolvedAttemptConfiguration,
                                                             unresolvedAttemptSession.owner, "2026-09-14T00:57:12Z",
                                                             "America/New_York", 1, false);
        const auto unresolvedAttemptAllocation = unresolvedAttemptStore.allocate(
            "guided-unresolved-attempt-allocate", unresolvedAttemptRequest.binding.kind,
            unresolvedAttemptRequest.binding.context, unresolvedAttemptRequest.binding.practiceUtc).get();
        check(unresolvedAttemptAllocation.status == storage::Status::Confirmed && !unresolvedAttemptAllocation.owner.empty(),
              "unresolved linked-Attempt fixture allocates the retained admitted source case");
        unresolvedAttemptRequest.binding.owner = unresolvedAttemptAllocation.owner;
        practice::Coordinator unresolvedAttemptCoordinator;
        beginAttempt(unresolvedAttemptCoordinator, unresolvedAttemptRequest.binding, unresolvedAttemptConfiguration);
        check(unresolvedAttemptCoordinator.progress(capture_fixture::progress(unresolvedAttemptCoordinator, 16000, practice::State::Ended)),
              "unresolved linked-Attempt fixture reaches a stopped result");
        const auto unresolvedAttemptEnvelope = capture::makeEnvelope(
            unresolvedAttemptCoordinator, unresolvedAttemptRequest.binding, nullptr, capture::Outcome::Stop);
        check(unresolvedAttemptStore.seal("guided-unresolved-attempt-seal", unresolvedAttemptEnvelope.owner,
                                          unresolvedAttemptEnvelope.bytes).get().status == storage::Status::Confirmed
                  && unresolvedAttemptStore.commit("guided-unresolved-attempt-commit", unresolvedAttemptEnvelope.owner,
                                                   unresolvedAttemptEnvelope.bytes).get().status == storage::Status::Confirmed,
              "unresolved linked Attempt is finalized without closing its Guided Session");
        auto unresolvedAttemptBeforeFuture = unresolvedAttemptStore.snapshot("guided-unresolved-attempt-before-read");
        const auto unresolvedAttemptBefore = storage::ProfileStore::waitForAcknowledgment(unresolvedAttemptBeforeFuture);
        check(unresolvedAttemptBefore.status == storage::Status::Confirmed
                  && rows(unresolvedAttemptBefore.data, "session") == 1
                  && rows(unresolvedAttemptBefore.data, "session_close") == 0
                  && rows(unresolvedAttemptBefore.data, "identity") == 1
                  && rows(unresolvedAttemptBefore.data, "pending") == 0
                  && rows(unresolvedAttemptBefore.data, "finalized") == 1,
              "unresolved linked-Attempt profile has one Session, Attempt and final with no close");
        check(unresolvedAttemptRequest.binding.context.find("item_id")->string() == "fg:item:000002"
                  && unresolvedAttemptRequest.binding.context.find("variant_id")->string() == "fg:variant:000006"
                  && unresolvedAttemptRequest.binding.context.find("session_id")->string() == unresolvedAttemptSession.owner,
              "unresolved linked-Attempt profile preserves exact source and Session identities");
        desktop::GuidedSessionView unresolvedWithAttempt;
        unresolvedWithAttempt.setCatalog(catalog);
        check(unresolvedWithAttempt.configureStore(unresolvedAttemptStore,
                                                   [] { return std::string("2026-09-14T00:57:20Z"); }, "America/New_York"),
              "unresolved linked-Attempt view binds through the existing snapshot path");
        while (unresolvedWithAttempt.busy()) { unresolvedWithAttempt.service(); pump(); }
        check(!unresolvedWithAttempt.running()
                  && unresolvedWithAttempt.sessionSummaryText().find("unresolved local Session " + unresolvedAttemptSession.owner) != std::string::npos
                  && unresolvedWithAttempt.sessionSummaryText().find("Saved Practice Attempt: linked to this Guided Session.") != std::string::npos
                  && unresolvedWithAttempt.sessionSummaryText().find("Source case: fg:item:000002 / fg:variant:000006") != std::string::npos
                  && unresolvedWithAttempt.sessionSummaryText().find("Source refs: L3-TXT5-21, L3-TXT28-46") != std::string::npos
                  && unresolvedWithAttempt.sessionSummaryText().find("Content version: representative-controls.1") != std::string::npos
                  && unresolvedWithAttempt.sessionSummaryText().find("No saved outcome is claimed") != std::string::npos
                  && unresolvedWithAttempt.sessionSummaryText().find("No curriculum progress") != std::string::npos
                  && unresolvedWithAttempt.sessionSummaryText().find("Outcome:") == std::string::npos,
              "reopen restores linked Attempt ownership without inventing an unresolved Guided outcome");
        auto unresolvedAttemptAfterFuture = unresolvedAttemptStore.snapshot("guided-unresolved-attempt-after-read");
        const auto unresolvedAttemptAfter = storage::ProfileStore::waitForAcknowledgment(unresolvedAttemptAfterFuture);
        check(unresolvedAttemptAfter.status == storage::Status::Confirmed
                  && unresolvedAttemptAfter.data == unresolvedAttemptBefore.data,
              "unresolved linked-Attempt summary read creates no additional authoritative rows");

        const auto completeProfileDirectory = evidence / "complete-profile";
        std::filesystem::create_directories(completeProfileDirectory);
        std::filesystem::permissions(completeProfileDirectory, std::filesystem::perms::owner_all, std::filesystem::perm_options::replace);
        storage::StoreOptions completeOptions;
        completeOptions.path = completeProfileDirectory / "profile.sqlite";
        completeOptions.create = true;
        completeOptions.createdUtc = "2026-09-14T00:58:00Z";
        storage::ProfileStore completeStore(completeOptions);
        auto completeCreateFuture = completeStore.createSession(
            "guided-complete-fixture-create", "2026-09-14T00:58:10Z", "America/New_York", 600,
            json::Value::Object{{"version", "guided-session-plan.1"}});
        const auto completeCreate = storage::ProfileStore::waitForAcknowledgment(completeCreateFuture);
        check(completeCreate.status == storage::Status::Confirmed && !completeCreate.owner.empty(),
              "complete-outcome fixture creates one planned Guided Session");
        auto completeCloseFuture = completeStore.closeSession(
            "guided-complete-fixture-close", completeCreate.owner, "2026-09-14T00:58:20Z", "complete");
        const auto completeClose = storage::ProfileStore::waitForAcknowledgment(completeCloseFuture);
        check(completeClose.status == storage::Status::Confirmed,
              "complete-outcome fixture closes through the existing raw complete value");
        auto completeBeforeFuture = completeStore.snapshot("guided-complete-fixture-before-read");
        const auto completeBefore = storage::ProfileStore::waitForAcknowledgment(completeBeforeFuture);
        check(completeBefore.status == storage::Status::Confirmed
                  && rows(completeBefore.data, "session") == 1
                  && rows(completeBefore.data, "session_close") == 1
                  && rows(completeBefore.data, "identity") == 0
                  && rows(completeBefore.data, "finalized") == 0,
              "complete-outcome fixture retains one closed Session without an Attempt");
        desktop::GuidedSessionView completeView;
        completeView.setCatalog(catalog);
        check(completeView.configureStore(completeStore,
                                          [] { return std::string("2026-09-14T00:58:30Z"); }, "America/New_York"),
              "complete-outcome view binds through the existing summary snapshot path");
        while (completeView.busy()) { completeView.service(); pump(); }
        check(!completeView.running()
                  && completeView.sessionSummaryText().find(completeCreate.owner) != std::string::npos
                  && completeView.sessionSummaryText().find("Duration: 10 minutes (600 seconds)") != std::string::npos
                  && completeView.sessionSummaryText().find("Outcome: complete (planned duration reached)") != std::string::npos
                  && completeView.sessionSummaryText().find("No curriculum progress") != std::string::npos
                  && completeView.sessionSummaryText().find("Saved Practice Attempt:") == std::string::npos
                  && completeView.sessionSummaryText().find("Source case:") == std::string::npos,
              "reopened complete summary explains the raw outcome without fabricating Attempt or source facts");
        auto completeAfterFuture = completeStore.snapshot("guided-complete-fixture-after-read");
        const auto completeAfter = storage::ProfileStore::waitForAcknowledgment(completeAfterFuture);
        check(completeAfter.status == storage::Status::Confirmed && completeAfter.data == completeBefore.data,
              "complete summary read creates no additional authoritative rows");

        std::ofstream(evidence / "summary.json") << "{\"checks\":" << checks
            << ",\"sessionLifecycle\":true,\"practiceFactsCreated\":false,\"humanReview\":false}\n";
        std::cout << "PASS " << checks << " guided session checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << ": " << error.what() << '\n';
        return 1;
    }
}
