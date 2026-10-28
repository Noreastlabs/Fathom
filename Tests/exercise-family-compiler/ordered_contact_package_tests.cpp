#include "tasks/InstalledOrderedContactTaskRegistry.hpp"
#include "tasks/OrderedContactTaskFormAdapter.hpp"
#include "content/Canonical.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <array>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <set>
#include <sstream>

// Standalone substitutes for the existing production content I/O/hash facade;
// production keeps its existing JUCE-backed implementation, unchanged.
namespace fathom::content {
std::string sha256(const std::string& raw) {
    if (raw.size() > std::numeric_limits<CC_LONG>::max()) throw std::runtime_error("Hash size");
    std::array<unsigned char,CC_SHA256_DIGEST_LENGTH> bytes{};
    CC_SHA256(raw.data(),static_cast<CC_LONG>(raw.size()),bytes.data());
    std::ostringstream out; for (const auto byte:bytes) out<<std::hex<<std::setw(2)<<std::setfill('0')<<static_cast<int>(byte);
    return out.str();
}
std::string readBounded(const std::filesystem::path& path,std::size_t limit) {
    if (!std::filesystem::is_regular_file(path)) throw std::runtime_error("Regular file required");
    std::ifstream input(path,std::ios::binary); if (!input) throw std::runtime_error("File unavailable");
    std::string out; char buffer[65536];
    while (input) {
        input.read(buffer,sizeof(buffer)); const auto n=static_cast<std::size_t>(input.gcount());
        if (n>limit-out.size()) throw std::runtime_error("File exceeds bound"); out.append(buffer,n);
    }
    if (!input.eof()) throw std::runtime_error("Read failed"); return out;
}
}
namespace {
namespace fs=std::filesystem;
namespace F=fathom::tasks::ordered_contacts;
namespace M=F::manual;
using J=fathom::json::Value;
using Registry=F::InstalledOrderedContactTaskRegistry;
std::size_t checks=0,packageRefusals=0,formRefusals=0,rowQueries=0;
void check(bool good,const char* label) { ++checks;if (!good) throw std::runtime_error(label); }
const J& at(const J& v,const std::string& key) {check(v.isObject()&&v.find(key),"TEST_OBJECT_FIELD");return *v.find(key);}
void write(const fs::path& p,const std::string& raw) {fs::create_directories(p.parent_path());std::ofstream o(p,std::ios::binary);o<<raw;check(o.good(),"TEST_WRITE");}
template<class Action>void refuses(Action&& action,M::Task& task) {
    const auto before=task.view();bool rejected=false;
    try {action();}catch(const std::invalid_argument& e){rejected=true;check(std::string(e.what()).find("ORDERED_TASK_")==std::string::npos,"NO_INTERNAL_ERROR_IN_LEARNER_MESSAGE");}
    check(rejected,"EXPECTED_FORM_REFUSAL");++formRefusals;
    check(task.view().revision==before.revision&&task.view().state==before.state,"FORM_REFUSAL_DOES_NOT_MUTATE_NATIVE_OWNER");
}
J beginPayload(M::Task& task) {
    J::Object fields{{"branch",J::fromInteger(static_cast<int>(M::Branch::PrintedPassProgression))},
        {"rhythm",J::fromInteger(static_cast<int>(task.sourcePolicy().passes.front().rhythms.front()))},
        {"first_start",J::fromInteger(static_cast<int>(F::Start::Down))},{"setup_read",J::fromInteger(2)},
        {"one_set",J::fromInteger(2)},{"stable_landings",J::fromInteger(2)}};
    if(task.sourcePolicy().oneModePerSession)fields.emplace("printed_mode",J::fromInteger(2));
    return fields;
}
void nativeRoute(M::Task& task) {
    while(task.view().state==M::State::Traversal||task.view().state==M::State::Boundary) {
        if(task.view().state==M::State::Boundary)task.reportBoundary(task.capture(M::Action::BoundaryReport),{M::Claim::Yes,M::Claim::Yes,M::Claim::Yes});
        task.confirmContact(task.capture(M::Action::Contact),task.view().nextOrdinal,M::Claim::Yes);
    }
    task.release(task.capture(M::Action::Release),M::Claim::Yes);
    task.reportLoop(task.capture(M::Action::LoopReport),{M::Observation::Clean,M::Claim::Yes});
}
void finishNative(M::Task& task) {
    M::SetupReport setup{M::Branch::PrintedPassProgression,task.sourcePolicy().passes.front().rhythms.front(),F::Start::Down};
    setup.sourceSetupRead=setup.onePrintedSetChosen=setup.printedModeChosen=setup.stableLandings=M::Claim::Yes;
    task.begin(task.capture(M::Action::Begin),setup);
    for(std::size_t p=0;p<task.sourcePolicy().passes.size();++p) {
        nativeRoute(task);task.oppositeStart(task.capture(M::Action::OppositeStart));nativeRoute(task);
        if(p+1==task.sourcePolicy().passes.size())task.finish(task.capture(M::Action::Finish));
        else {const auto& next=task.sourcePolicy().passes[p+1];task.advancePass(task.capture(M::Action::AdvancePass),next.pass,next.rhythms.front());}
    }
}
void allRows(const Registry& registry) {
    check(registry.size()==1401&&registry.error().empty()&&registry.sourceFilesHashed()==20,"COMPLETE_SOURCE_VERIFIED_REGISTRY");
    std::set<std::string> seen;
    for(const auto& key:F::keys()) {
        const auto& native=F::definition(key);
        check(registry.containsSourceKey(key)&&registry.containsSourceIdentity(native.sourceIdentity())&&seen.insert(key).second,"ALL_ROW_EXACT_UNIQUE_ROUTING");
        const auto keyed=registry.definitionForSourceKey(key),identified=registry.definitionForSourceIdentity(native.sourceIdentity());
        check(keyed&&identified&&std::string(keyed->sourceKey())==key&&std::string(identified->sourceKey())==key
            &&std::string(keyed->sourceRecordSha256())==native.sourceRecordSha256()&&keyed->contactCount()==native.contactCount(),"ALL_ROW_NATIVE_CONTRACT_PROVENANCE");
        auto task=registry.taskForSourceKey(key);check(task&&task->sourcePolicy().level==native.level(),"ALL_ROW_SHARED_OWNER_POLICY_BINDING");
        M::OrderedContactTaskFormAdapter adapter(*task);const auto form=adapter.open(M::Action::Begin);
        check(adapter.current(form.token)&&at(form.schema,"additionalProperties")==J(false)
            &&!at(form.schema,"properties").find("source_key")&&!at(form.schema,"properties").find("source_context"),"EVERY_ROW_CLOSED_LEARNER_SCHEMA");
        check(form.label.find("sha256")==std::string::npos&&!task->view().reportedBpm,"NO_SOURCE_METADATA_OR_DEFAULT_BPM");
        for(const auto& instruction:form.instructions)check(instruction.find(native.sourceRecordSha256())==std::string::npos,"NO_SOURCE_HASH_IN_LEARNER_INSTRUCTIONS");
        ++rowQueries;
    }
    for(const auto& key:{std::string("unknown"),std::string("proposed-printed-l002-set-1-of-9-exercises-001-012-exercise-002-1213"),
        std::string("proposed-printed-l004-set-1-of-9-exercises-001-012-exercise-006-1234")})
        check(!registry.containsSourceKey(key)&&!registry.definitionForSourceKey(key)&&!registry.taskForSourceKey(key),"UNKNOWN_ACCEPTED_AND_HELD_EXCLUSIONS_REMAIN");
}
void packageNegatives(const fs::path& root,const fs::path& original,const fs::path& assets) {
    const auto scratch=root/"Build/manager-resume-r03/ordered-contact-package-r01/test-package";
    const auto initial=fathom::json::parse(fathom::content::readBounded(original/"manifest.json",65536));
    const auto reset=[&] {
        fs::remove_all(scratch);fs::create_directories(scratch);
        for(const auto* name:{"manifest.json","definitions.jsonl","contexts.json"})fs::copy_file(original/name,scratch/name);
    };
    const auto reject=[&](const fs::path& candidate,const fs::path& source) {
        const auto r=Registry::load(candidate,source);
        check(r.size()==0&&!r.error().empty(),"BAD_PACKAGE_GRANTS_ZERO_PARTIAL_KEYS");
        for(const auto& key:F::keys())check(!r.containsSourceKey(key)&&!r.definitionForSourceKey(key)&&!r.taskForSourceKey(key),"EVERY_KEY_REFUSED_AFTER_FAILURE");
        ++packageRefusals;return r;
    };
    reset();auto manifest=initial;manifest.object()["runtime_admitted"]=J(true);write(scratch/"manifest.json",fathom::json::stringify(manifest));reject(scratch,assets);
    reset();manifest=initial;manifest.object()["definitions"].object()["path"]=J("../definitions.jsonl");write(scratch/"manifest.json",fathom::json::stringify(manifest));reject(scratch,assets);
    reset();manifest=initial;manifest.object()["version_bindings"].object()["manual_source_version"]=J("unknown");write(scratch/"manifest.json",fathom::json::stringify(manifest));reject(scratch,assets);
    reset();manifest=initial;manifest.object()["source_policy_groups"]=J::fromInteger(11);write(scratch/"manifest.json",fathom::json::stringify(manifest));reject(scratch,assets);
    reset();auto rows=fathom::content::readBounded(scratch/"definitions.jsonl",2*1024*1024);const auto first=rows.find('\n');write(scratch/"definitions.jsonl",rows+rows.substr(0,first+1));reject(scratch,assets);
    reset();write(scratch/"definitions.jsonl",rows.substr(0,rows.rfind('\n',rows.size()-2)+1));reject(scratch,assets);
    reset();auto changed=rows;changed[10]=changed[10]=='x'?'y':'x';write(scratch/"definitions.jsonl",changed);reject(scratch,assets);
    reset();write(scratch/"contexts.json","{}");reject(scratch,assets);
    reset();fs::remove(scratch/"contexts.json");reject(scratch,assets);
    reset();fs::remove(scratch/"definitions.jsonl");fs::create_symlink(original/"definitions.jsonl",scratch/"definitions.jsonl");reject(scratch,assets);
    reset();write(scratch/"extra.json","{}");reject(scratch,assets);
    reset();fs::create_directory(scratch/"extra");reject(scratch,assets);
    const auto link=root/"Build/manager-resume-r03/ordered-contact-package-r01/package-root-link";
    fs::remove(link);fs::create_directory_symlink(original,link);reject(link,assets);fs::remove(link);
    const auto sourceScratch=root/"Build/manager-resume-r03/ordered-contact-package-r01/test-source-assets";
    fs::remove_all(sourceScratch);fs::create_directories(sourceScratch);
    const auto asset=at(initial,"source_assets").array().front();const auto path=at(asset,"path").string();
    auto source=fathom::content::readBounded(assets/path,256*1024);source[0]=source[0]=='x'?'y':'x';write(sourceScratch/path,source);
    auto rejected=reject(original,sourceScratch);check(rejected.error().find("bytes/hash")!=std::string::npos&&rejected.sourceFilesHashed()==1,"ACTUAL_FIRST_SOURCE_BYTE_CORRUPTION_CAUSALITY");
    fs::remove(sourceScratch/path);fs::create_symlink(assets/path,sourceScratch/path);rejected=reject(original,sourceScratch);
    check(rejected.error().find("symlink")!=std::string::npos,"SOURCE_FILE_SYMLINK_CAUSALITY");
    fs::remove_all(sourceScratch);reject(original,sourceScratch);
    fs::remove_all(scratch);fs::remove_all(sourceScratch);
}
void forms(const Registry& registry,const fs::path& root) {
    std::string firstKey,shiftKey;
    for(const auto& key:F::keys()) {if(F::definition(key).level()==2&&firstKey.empty())firstKey=key;if(F::definition(key).level()==11&&shiftKey.empty())shiftKey=key;}
    auto task=registry.taskForSourceKey(firstKey),other=registry.taskForSourceKey(firstKey);
    M::OrderedContactTaskFormAdapter adapter(*task),second(*other);
    auto form=adapter.open(M::Action::Begin);auto valid=beginPayload(*task);
    write(root/"Build/manager-resume-r03/ordered-contact-package-r01/form-begin-fixture.json",fathom::json::stringify(form.schema)+"\n");
    check(!second.current(form.token),"FORM_OWNER_CROSS_TASK_FENCE");
    auto bad=valid;bad.object()["source_key"]=J("injected");refuses([&]{adapter.apply(form.token,bad);},*task);
    bad=valid;bad.object()["branch"]=J("0");refuses([&]{adapter.apply(form.token,bad);},*task);
    bad=valid;bad.object()["chosen_bpm"]=J(fathom::json::Number{"90.5"});refuses([&]{adapter.apply(form.token,bad);},*task);
    bad=valid;bad.object()["chosen_bpm"]=J::fromInteger(2147483648LL);refuses([&]{adapter.apply(form.token,bad);},*task);
    bad=valid;bad.object()["setup_read"]=J::fromInteger(0);refuses([&]{adapter.apply(form.token,bad);},*task);
    check(adapter.current(form.token),"UNKNOWN_SETUP_CAN_BE_CORRECTED_WITHOUT_TRAP");
    auto replacement=adapter.open(M::Action::Begin);refuses([&]{adapter.apply(form.token,valid);},*task);
    adapter.apply(replacement.token,valid);check(!adapter.current(replacement.token)&&task->view().state==M::State::Traversal,"SUCCESS_CONSUMES_FRESH_FORM_CAPABILITY");
    auto contact=adapter.open(M::Action::Contact);task->cancel(task->capture(M::Action::Cancel));
    refuses([&]{adapter.apply(contact.token,J::Object{{"contact_reported",J::fromInteger(2)}});},*task);
    auto release=adapter.open(M::Action::Release);refuses([&]{adapter.apply(release.token,J::Object{{"hand_release_reported",J::fromInteger(0)}});},*task);
    adapter.apply(release.token,J::Object{{"hand_release_reported",J::fromInteger(2)}});
    check(task->view().state==M::State::Cancelled,"FORM_RELEASE_OWNS_CANCEL_CLOSURE");
    auto restart=adapter.open(M::Action::Restart);adapter.apply(restart.token,J::Object{});
    auto shifted=registry.taskForSourceKey(shiftKey);finishNative(*shifted);
    M::SessionReport external;external.priorPrintedPassesReported=external.fullPrintedSetClean=external.bothRoutesClean=
        external.bothStartsClean=external.bothModesClean=M::Claim::Yes;external.separateDayLabels={"2026-09-29","2026-09-30"};
    shifted->reportSession(shifted->capture(M::Action::SessionReport),external);
    M::OrderedContactTaskFormAdapter extension(*shifted);auto initial=extension.open(M::Action::ExtensionReport);
    check(!at(initial.schema,"properties").find("position_one"),"CONDITIONAL_FRAMES_START_UNSELECTED");
    auto selected=extension.selectExtension(initial.token,M::Extension::OtherPositionDistance);
    check(!extension.current(initial.token)&&at(selected.schema,"properties").find("position_one"),"CONDITIONAL_REBUILD_FENCES_OLD_FORM");
    const auto& binding=at(at(selected.schema,"properties"),"extension");
    check(at(binding,"const")==J::fromInteger(3)&&at(binding,"literal_binding_label")==J("prior_learner_choice_binding")
        &&at(binding,"input_role")==J("prior_learner_choice_binding"),"CONSTANT_IS_ACTUAL_LABELED_PRIOR_CHOICE");
    write(root/"Build/manager-resume-r03/ordered-contact-package-r01/form-extension-fixture.json",fathom::json::stringify(selected.schema)+"\n");
    J payload(J::Object{{"extension",J::fromInteger(3)},{"mastery_reported",J::fromInteger(2)},
        {"position_one",J::fromInteger(5)},{"position_two",J::fromInteger(9)},{"position_three",J::fromInteger(13)}});
    refuses([&]{extension.apply(initial.token,payload);},*shifted);
    bad=payload;bad.object()["position_two"]=J::fromInteger(5);refuses([&]{extension.apply(selected.token,bad);},*shifted);
    bad=payload;bad.object()["extension"]=J::fromInteger(1);refuses([&]{extension.apply(selected.token,bad);},*shifted);
    extension.apply(selected.token,payload);
    check(shifted->view().state==M::State::Finished&&!shifted->view().coverage.runtimeAdmitted
        &&!shifted->view().coverage.wholeChildAccepted,"SEPARATE_EXTENSION_PLAN_CANNOT_PROMOTE_BASE_REFERENCE");
}
}
int main(int argc,char** argv) {
    try {
        check(argc==2,"ROOT_ARGUMENT");const fs::path root=fs::canonical(argv[1]);
        const auto package=root/"Content/runtime/compiled-manual-families-v1/ordered-contact";
        const auto assets=root/"Build/manager-resume-r03/native-integration-r01/Fathom_artefacts/Debug/Fathom.app/Contents/Resources/source-library/bundle/assets";
        const auto registry=Registry::load(package,assets);if(!registry.error().empty())throw std::runtime_error(registry.error());
        allRows(registry);packageNegatives(root,package,assets);forms(registry,root);
        std::cout<<"{\"result\":\"PASS\",\"all_row_queries\":"<<rowQueries<<",\"source_files_verified\":20,\"source_policy_groups\":10,\"native_contexts\":11,\"package_refusals\":"
            <<packageRefusals<<",\"form_refusals\":"<<formRefusals<<",\"assertions\":"<<checks
            <<",\"zero_partial_routing\":true,\"per_row_files_or_models\":0,\"official_runtime_acceptance_increments\":0}\n";return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
