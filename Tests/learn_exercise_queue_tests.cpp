#include "content/ExerciseQueue.hpp"
#include "content/ExerciseSuiteReview.hpp"
#include "content/LearnSourceAdmission.hpp"
#include <iostream>

using namespace fathom::navigation;
namespace {
int checks = 0;
void check(bool okay, const char* detail) {
    ++checks;
    if (!okay) throw std::runtime_error(detail);
}
ExerciseEntry fixture(std::uint32_t order) {
    const auto id = std::to_string(order);
    return {"fixture:level", "fixture:sublevel", "fixture:source:" + id, order, order,
            "fixture:index:1", "fixture:original:1", ExerciseMappingExtent::ExactSourceUnit,
            AdmissionIdentity{"fixture:item:" + id, "fixture:variant:" + id,
                              "fixture:content:" + id, "fixture:binding:" + id}};
}
ExerciseSelection selection(std::uint32_t first, std::uint32_t last) {
    return {"fixture:level", "fixture:sublevel", "fixture:source:" + std::to_string(first),
            "fixture:source:" + std::to_string(last)};
}
std::vector<ExerciseEntry> entries() { return {fixture(3), fixture(1), fixture(2)}; }
ExercisePlan plan() { return planExercises(entries(), selection(1, 3)); }
void refused(std::vector<ExerciseEntry> rows, const ExerciseSelection& selected, const char* reason) {
    const auto result = planExercises(rows, selected);
    check(!result.valid(), reason);
    check(!result.error().empty() && result.items().empty(), "Refusal must return reason and zero partial queue items");
}
ExerciseResolution saved(const ExerciseLaunch& launch) {
    return {launch.ticket, *launch.exercise.admission, ResultDisposition::Saved,
            true, true, launch.sessionId, "fixture:attempt"};
}
void selectionTests() {
    auto result = plan();
    check(result.valid(), "An inclusive source range must plan");
    check(result.items().size() == 3, "Inclusive range count");
    check(result.items()[0].sourceOrder == 1 && result.items()[2].sourceOrder == 3, "Source order independent of input order");
    check(result.items()[0].admission->contentVersion != result.items()[1].admission->contentVersion,
          "Separate legitimate per-item content versions are retained");
    check(planExercises(entries(), selection(2, 2)).items().size() == 1, "Single exercise uses identical endpoints");
    refused(entries(), selection(3, 1), "Reversed selection");
    refused(entries(), selection(1, 4), "Missing endpoint");
    auto rows = entries(); rows.erase(rows.begin() + 2);
    refused(rows, selection(1, 3), "Missing interior ordinal");
    rows = entries(); rows.push_back(rows[1]);
    refused(rows, selection(1, 3), "Duplicate endpoint key");
    rows = entries(); rows.push_back(rows[2]); rows.back().sublevelKey = "fixture:other";
    refused(rows, selection(1, 3), "Duplicate key outside selected sublevel");
    rows = entries(); rows.push_back(fixture(2)); rows.back().sourceExerciseKey = "fixture:different-key";
    refused(rows, selection(1, 3), "Duplicate interior ordinal");
    rows = entries(); rows[2].sourceExerciseKey.clear();
    refused(rows, selection(1, 3), "Empty interior stable key");
    rows = entries(); rows[2].admission.reset();
    refused(rows, selection(1, 3), "Unavailable source stays unlaunchable");
    rows = entries(); rows[2].mappingExtent = ExerciseMappingExtent::LargerSourceCase;
    refused(rows, selection(1, 3), "Composite admitted case cannot substitute for one source exercise");
    check(planExercises(rows, selection(1, 3)).error().find("larger admitted case") != std::string::npos,
          "Larger-case refusal explains extent mismatch");
    rows = entries(); rows[2].mappingExtent = ExerciseMappingExtent::Ambiguous;
    refused(rows, selection(1, 3), "Ambiguous source mapping refuses even with admitted identity");
    rows = entries(); rows[2].mappingExtent = ExerciseMappingExtent::Unavailable;
    refused(rows, selection(1, 3), "Default unavailable mapping never grants single-unit launch");
    rows = entries(); rows[2].admission->variantId.clear();
    refused(rows, selection(1, 3), "Variant must be selected per item");
    rows = entries(); rows[2].admission->itemId = rows[1].admission->itemId;
    refused(rows, selection(1, 3), "Different variants of same item cannot stand in for two exercises");
    rows = entries(); rows[2].indexRevision += ":changed";
    refused(rows, selection(1, 3), "Mixed index revision");
    rows = entries(); rows[2].sourceRevision += ":changed";
    refused(rows, selection(1, 3), "Mixed original source revision");
    rows = entries(); rows[1].sourceRevision.clear();
    refused(rows, selection(1, 3), "Absent original pin");
    rows = entries(); rows[0].sublevelKey = "fixture:another";
    refused(rows, selection(1, 3), "Cross-sublevel endpoints");
    rows = entries(); rows[0].levelKey = "fixture:another-level";
    refused(rows, selection(1, 3), "Cross-level endpoints");
    rows = entries(); rows[0].sourceOrder = 0;
    refused(rows, selection(1, 3), "Zero source ordinal");
    rows = entries(); rows[2].levelOrder = 0;
    refused(rows, selection(1, 3), "Zero level ordinal");
    rows = entries(); rows[0].levelOrder = 7;
    refused(rows, selection(1, 3), "Recurring parent path crosses source segment");
    auto blank = selection(1, 3); blank.sublevelKey.clear();
    refused(entries(), blank, "Explicit sublevel is required");
    rows = {fixture(5), fixture(14)}; rows[1].sublevelKey = "fixture:set2";
    refused(rows, selection(5, 14), "Level2 SET1 5 to SET2 14 must refuse, regardless of title shorthand");
    rows = {fixture(1), fixture(std::numeric_limits<std::uint32_t>::max())};
    refused(rows, selection(1, std::numeric_limits<std::uint32_t>::max()), "Huge bounds refuse without range iteration or overflow");
}
void queueTests() {
    ExerciseQueue queue(plan());
    std::string error;
    std::optional<ExerciseLaunch> opened;
    int resolveCalls = 0, prepareCalls = 0;
    const auto resolve = [&](const ExerciseEntry& entry) { ++resolveCalls; return entry.admission; };
    const auto prepare = [&](const ExerciseLaunch& launch) { ++prepareCalls; opened = launch; return true; };
    check(queue.phase() == ExerciseQueuePhase::Ready && queue.position() == 0, "Planning creates no active launch");
    check(!queue.activeLaunch() && !queue.resolution() && resolveCalls == 0 && prepareCalls == 0, "Construction has no side effects");
    check(!queue.nextExplicitly(error), "Next before first open refuses");
    check(!queue.openExplicitly("", resolve, prepare, error), "Empty Session cannot open Practice");
    check(!queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), {}, prepare, error), "Missing resolver refuses");
    check(!queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), [](const auto&) { return std::optional<AdmissionIdentity>{}; }, prepare, error), "Current unadmitted item refuses");
    check(!queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), [](const auto& entry) { auto pin = *entry.admission; pin.sourceBinding += ":changed"; return pin; }, prepare, error), "Changed runtime binding refuses");
    check(!queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), [](const auto& entry) { auto pin = *entry.admission; pin.variantId += ":changed"; return pin; }, prepare, error), "Changed variant refuses");
    check(!queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), [](const auto& entry) { auto pin = *entry.admission; pin.contentVersion += ":changed"; return pin; }, prepare, error), "Changed content version refuses");
    check(prepareCalls == 0, "Refused admission never prepares Practice");
    check(!queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), resolve, [](const auto&) { return false; }, error), "Failed prepare retains Ready");
    check(queue.phase() == ExerciseQueuePhase::Ready && !queue.activeLaunch(), "Failed prepare never moves queue");
    check(!queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), resolve, [](const auto&) -> bool { throw std::runtime_error("fixture refusal"); }, error), "Thrown preparation refuses");
    check(queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), resolve, prepare, error), "Explicit preparation succeeds");
    check(queue.phase() == ExerciseQueuePhase::Open && queue.position() == 0 && opened.has_value(), "Open waits for current result");
    const auto firstLaunch = *opened;
    check(!queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), resolve, prepare, error), "Duplicate open cannot replace unresolved result");
    check(!queue.nextExplicitly(error), "Unresolved result cannot advance");
    auto receipt = saved(firstLaunch); receipt.outputCleared = false;
    check(!queue.noteResolved(receipt, error), "Saved result still needs audio cleanup");
    receipt = saved(firstLaunch); receipt.canLeave = false;
    check(!queue.noteResolved(receipt, error), "Saved result still needs canLeave");
    receipt = saved(firstLaunch); receipt.ticket += 1;
    check(!queue.noteResolved(receipt, error), "Stale/unrelated launch ticket refuses");
    receipt = saved(firstLaunch); receipt.admission.itemId += ":other";
    check(!queue.noteResolved(receipt, error), "Unrelated result identity refuses");
    receipt = saved(firstLaunch); receipt.sessionId += ":wrong";
    check(!queue.noteResolved(receipt, error), "Result cannot use another Session");
    receipt = saved(firstLaunch); receipt.attemptId.clear();
    check(!queue.noteResolved(receipt, error), "Saved result cannot omit Attempt identity");
    check(queue.noteResolved(saved(firstLaunch), error), "Saved and cleared result resolves");
    check(queue.phase() == ExerciseQueuePhase::Resolved && queue.position() == 0 && prepareCalls == 1,
          "Resolution alone never advances or launches");
    check(!queue.noteResolved(saved(firstLaunch), error), "Duplicate result notification refuses");
    check(queue.nextExplicitly(error), "Explicit Next advances after saved result");
    check(queue.phase() == ExerciseQueuePhase::Ready && queue.position() == 1 && prepareCalls == 1,
          "Next does not auto launch or allocate anything");
    check(queue.current()->admission->itemId == "fixture:item:2", "Second exercise keeps own item");
    check(!queue.openExplicitly(firstLaunch.sessionId, resolve, prepare, error), "Second item cannot reuse first Session");
    check(queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), resolve, prepare, error), "Second explicit open resolves fresh admission");
    check(opened->ticket != firstLaunch.ticket, "Launch tickets differ for separate items");
    check(opened->sessionId != firstLaunch.sessionId, "Each item keeps separate Session ownership");
    check(!queue.noteResolved(saved(firstLaunch), error), "Prior saved receipt cannot resolve next item");
    receipt = saved(*opened); receipt.disposition = ResultDisposition::SafelyDiscarded;
    receipt.attemptId.clear(); receipt.canLeave = false;
    check(!queue.noteResolved(receipt, error), "Discard label alone cannot bypass unresolved guard");
    receipt.canLeave = true;
    check(queue.noteResolved(receipt, error), "Trusted safe discard permits resolution without inventing Attempt");
    check(queue.nextExplicitly(error), "Explicit Next after safe discard");
    check(queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), resolve, prepare, error), "Last item explicitly opens");
    check(queue.noteResolved(saved(*opened), error) && queue.nextExplicitly(error), "Last saved item ends queue only on Next");
    check(queue.phase() == ExerciseQueuePhase::Complete && !queue.current() && !queue.activeLaunch(), "Completed queue has no current launch");
    check(!queue.openExplicitly("fixture:session:" + std::to_string(queue.position()), resolve, prepare, error) && !queue.nextExplicitly(error), "Complete queue cannot automatically restart");
    ExerciseQueue restarted(plan());
    check(restarted.openExplicitly("fixture:restart-session", resolve, prepare, error), "New explicitly chosen queue can replay selection");
    check(opened->ticket != firstLaunch.ticket, "New queue does not reuse old launch correlation");
    check(!restarted.noteResolved(saved(firstLaunch), error), "Old receipt cannot resolve restarted queue");
    ExerciseQueue reentrant(plan());
    check(reentrant.openExplicitly("fixture:reentrant-session", resolve, [&](const auto&) {
        std::string nestedError;
        check(!reentrant.openExplicitly("fixture:reentrant-session", resolve, prepare, nestedError), "Reentrant prepare refuses");
        check(!reentrant.nextExplicitly(nestedError), "Reentrant Next refuses");
        return true;
    }, error), "Outer preparation survives rejected reentry");
    bool invalidRejected = false;
    try { ExerciseQueue invalid(ExercisePlan{}); } catch (const std::invalid_argument&) { invalidRejected = true; }
    check(invalidRejected, "No fabricated empty plan can create a queue");
}
}
void suiteMembershipTests() {
    ExerciseSuiteReview suite("fixture:suite:1");
    auto item = fixture(1);
    ExerciseLaunch first{101,item,"fixture:session:1"};
    auto receipt = saved(first);receipt.attemptId="fixture:attempt:1";
    std::string reason;
    check(suite.record(first,receipt,false,reason) && suite.completed().empty(),"Saved Stop/abort never becomes completed suite membership");
    auto wrong=receipt;wrong.ticket=102;
    check(!suite.record(first,wrong,true,reason),"Foreign launch ticket refuses final review membership");
    wrong=receipt;wrong.admission.sourceBinding="different";
    check(!suite.record(first,wrong,true,reason),"Source provenance mismatch refuses final review membership");
    wrong=receipt;wrong.outputCleared=false;
    check(!suite.record(first,wrong,true,reason),"Unresolved output prevents completed membership");
    wrong=receipt;wrong.disposition=ResultDisposition::SafelyDiscarded;
    check(!suite.record(first,wrong,true,reason),"Skipped/unplayed receipt never enters completed membership");
    check(suite.record(first,receipt,true,reason),"Actual natural completed saved Attempt enters membership");
    check(suite.record(first,receipt,true,reason) && suite.completed().size()==1,"Identical completed replay has one member");
    auto changed=first;changed.exercise.sourceExerciseKey="changed";
    check(!suite.record(changed,receipt,true,reason),"Original Attempt cannot be rebound to changed source key");
    ExerciseLaunch second{102,fixture(2),"fixture:session:2"};auto secondReceipt=saved(second);secondReceipt.attemptId="fixture:attempt:2";
    check(suite.record(second,secondReceipt,true,reason) && suite.completed().size()==2,"Separate completed Attempts preserve individual Session and source identities");
    check(suite.completed()[0].attemptId=="fixture:attempt:1" && suite.completed()[1].admission.itemId=="fixture:item:2","Final members retain original Attempt and admitted source identities");
    suite.freeze();
    check(suite.frozen() && suite.record(second,secondReceipt,true,reason) && suite.completed().size()==2,"Identical completed callback remains idempotent after final membership freeze");
    ExerciseLaunch third{103,fixture(3),"fixture:session:3"};auto thirdReceipt=saved(third);thirdReceipt.attemptId="fixture:attempt:3";
    check(!suite.record(third,thirdReceipt,true,reason),"New membership cannot be inserted after final review freeze");
    check(suite.suiteId()=="fixture:suite:1","Durable suite identity retained independently of launch ticket");
}
void realCatalogTests(const std::filesystem::path& resources) {
    std::vector<std::filesystem::path> extensions;
    for(const auto& name:fathom::lesson::Catalog::installedExtensionDirectoryNames())extensions.push_back(resources/name);
    const auto catalog=fathom::lesson::Catalog::loadInstalled(resources/"representative-controls",extensions);
    const auto index=fathom::learn::SourceIndex::load(resources/"learn-source-index");
    const auto& sub=index->level(12).sublevels.front();
    const auto source=index->range(12,sub.key,index->exercises()[sub.exercises[1]].source.sourceExerciseKey,index->exercises()[sub.exercises[4]].source.sourceExerciseKey);
    std::vector<ExerciseEntry> real;
    for(std::size_t i=0;i<source.size();++i){auto e=source[i]->source;const auto choices=fathom::learn::choices(*source[i],*catalog);check(choices.size()==2,"Each real Level12 source rung has two independently admitted variants");e.mappingExtent=ExerciseMappingExtent::ExactSourceUnit;e.admission=choices[i%2];real.push_back(e);}
    const std::vector<std::string> expected{"fg:item:001141","fg:item:001142","fg:item:001143","fg:item:001145"};
    auto selected=planExercises(real,{real.front().levelKey,sub.key,real.front().sourceExerciseKey,real.back().sourceExerciseKey});
    check(selected.valid()&&selected.items().size()==4,"Real source range resolves four separate admitted items");
    ExerciseQueue queue(std::move(selected));std::string reason;
    for(std::size_t i=0;i<4;++i){check(queue.current()->admission->itemId==expected[i],"Real source order matches individually admitted rungs");int preparations=0;const auto resolve=[&](const auto& e){return fathom::navigation::snapshotAdmission(*fathom::navigation::resolveExerciseAdmission(*catalog,e));};check(queue.openExplicitly("test-real-session-"+std::to_string(i),resolve,[&](const ExerciseLaunch& launch){++preparations;return launch.exercise.admission->itemId==expected[i];},reason),"Actual Catalog admission re-resolves before each preparation");check(preparations==1&&queue.phase()==ExerciseQueuePhase::Open,"Only explicit Open prepares one item");const auto launch=*queue.activeLaunch();check(queue.noteResolved({launch.ticket,*launch.exercise.admission,ResultDisposition::Saved,true,true,launch.sessionId,"test-real-attempt-"+std::to_string(i)},reason),"Exact separate receipt resolves current real admitted identity");check(queue.nextExplicitly(reason)&&preparations==1,"Explicit Next never prepares following item");}
    check(queue.phase()==ExerciseQueuePhase::Complete,"Real four-item queue completes only after four explicit resolutions");
    const auto& composite=index->exercises()[index->level(13).sublevels.front().exercises[1]];
    check(fathom::learn::choices(composite,*catalog).empty(),"Real Level13 composite source coverage cannot launch exact single rung");
    const auto& missing=index->exercises()[index->level(2).sublevels.front().exercises[4]];
    check(fathom::learn::choices(missing,*catalog).empty(),"Real unavailable Level2 source row remains unlaunchable");
    const auto& admitted26=index->exercises()[index->level(26).sublevels.front().exercises.front()];
    check(fathom::learn::choices(admitted26,*catalog).size()==2,"Independently accepted Level26 exact source overlay has two admitted variants");
    auto changed=*source.front();changed.bindings.front().packageHash=std::string(64,'0');
    check(fathom::learn::choices(changed,*catalog).empty(),"Exact-unit candidate with mismatched Catalog package refuses");
}
int main(int argc,char** argv) {
    try {
        suiteMembershipTests();
        if(argc!=2)throw std::runtime_error("Expected installed Resources path");
        selectionTests(); queueTests(); realCatalogTests(argv[1]);
        std::cout << "PASS " << checks << " focused queue checks with real Catalog/source-index linkage plus synthetic counterexamples\n";
        return 0;
    } catch (const std::exception& exception) {
        std::cerr << "FAIL after " << checks << " checks: " << exception.what() << '\n';
        return 1;
    }
}
