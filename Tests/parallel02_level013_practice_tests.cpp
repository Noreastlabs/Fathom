// Real desktop/Store/Practice paths, with only device I/O substituted.
#define main retained_shared_audio_campaign_main
#include "shared_audio_settings_tests.cpp"
#undef main
#include "progression/ProgressionAdapter.hpp"
#include "desktop/ProgressPresentation.hpp"
#include <array>
int main(int argc,char** argv){int checks=0;try{
    if(argc!=14)throw std::runtime_error("Expected original bundle, extension, new evidence directory");
    const std::filesystem::path out=argv[13];if(!out.is_absolute()||std::filesystem::exists(out))throw std::runtime_error("Fresh evidence required");
    std::filesystem::create_directories(out);std::ofstream trace(out/"checks.tsv");juce::ScopedJuceInitialiser_GUI gui;
    auto ck=[&](bool ok,const std::string& text){++checks;trace<<text<<'\t'<<(ok?"PASS":"FAIL")<<std::endl;if(!ok)throw std::runtime_error(text);};
    auto clickId=[&](juce::Component& view,const char* id){auto* b=dynamic_cast<juce::Button*>(view.findChildWithID(id));if(!b||!b->isVisible()||!b->isEnabled())throw std::runtime_error(std::string("Unusable button ")+id);activate(*b);};
    Harness h(out,"private-profile");auto& learn=A::lessons(*h.home);
    ck(learn.load(argv[1],std::vector<std::filesystem::path>{argv[2],argv[3],argv[4],argv[5],argv[6],argv[7],argv[8],argv[9],argv[10],argv[11],argv[12]}),"load actual eleven-extension catalog");
    auto snapshot=[&](const std::string& name){auto reply=capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));capture_fixture::write(out/(name+".json"),storage::canonical(reply.data));return reply;};
    auto counts=[&](const storage::Reply& reply,std::size_t expected){const auto& a=reply.data.object().at("authoritative");ck(a.object().at("identity").array().size()==expected&&a.object().at("source_attestation").array().empty(),"exact Attempt count and no curriculum source credit");};
    counts(snapshot("initial"),0);
    click(*h.home,"Learn");counts(snapshot("learn-entry"),0);
    click(learn,"Back");counts(snapshot("learn-back"),0);click(*h.home,"Learn");
    ck(learn.catalog()->lessons().size()==27,"twenty-seven source-backed cases visible");
    for(int index=0;index<4;++index){
        const std::string item=index<2?"fg:item:001153":"fg:item:001154";
        const std::array<std::string,4> variants{"fg:variant:007428","fg:variant:007429",
            "fg:variant:007430","fg:variant:007431"};
        const std::string variant=variants[static_cast<std::size_t>(index)];
        const std::string prefix=std::string(index<2?"A-":"A-Bb-")+(index%2==0?"D":"U");
        ck(learn.selectLesson(item)&&learn.selectVariant(variant),"select exact new D/U source variant");
        if(index<2)ck(learn.catalog()->lesson(item).title.find("excerpt of neighbor-stage")!=std::string::npos,
            "Learn retains first-cell neighboring-stage excerpt qualifier");
        click(learn,"Back");click(*h.home,"Guided sessions");h.tick();
        auto& guided=A::guided(*h.home);h.wait([&]{return !guided.busy();},"plan ready");
        ck(guided.planText().find(variant)!=std::string::npos,"Guided plan selects exact D/U identity");
        counts(snapshot(prefix+"-plan-entry"),index);
        click(guided,"Start Guided session");h.wait([&]{return guided.running()&&!guided.busy();},"explicit Guided Session");
        const auto selectedSession=guided.sessionId();
        ck(!selectedSession.empty()&&selectedSession!=h.sessionId,"new explicit source-bound Session");
        auto planned=snapshot(prefix+"-session-plan");bool exactPlan=false;
        for(const auto& row:planned.data.object().at("authoritative").object().at("session").array())if(row.array()[0].string()==selectedSession){
            const auto hex=row.array()[4].object().at("blob_hex").string();std::string bytes;
            for(std::size_t i=0;i<hex.size();i+=2)bytes+=static_cast<char>(std::stoul(hex.substr(i,2),nullptr,16));
            const auto plan=json::parse(bytes);exactPlan=plan.object().at("selected_case")==learn.catalog()->admit(item,variant)->identity()&&plan.object().at("content_version")==json::Value(learn.catalog()->contentVersion(item));
            capture_fixture::write(out/(prefix+"-decoded-plan.json"),storage::canonical(plan));
        }
        ck(exactPlan,"persisted Session plan exactly equals full admission identity and owning version");
        clickId(guided,"open-first");h.tick();
        click(learn,"Practice selected case");h.tick();ck(h.home->page()==H::Page::Practice,"actual Learn to Practice handoff");
        const auto token=h.practice().lessonAdmission();ck(token&&token->model()->source().events.size()==(index<2?30:60)&&h.practice().captureSessionId()==selectedSession,"30/60 notes and exact selected local Session");
        auto* instructions=dynamic_cast<juce::Label*>(h.practice().findChildWithID("practice-authored-source"));
        ck(instructions&&instructions->getText().toStdString().find(learn.catalog()->variant(item,variant).label)!=std::string::npos,"visible exact authored D/U label");
        if(index<2)ck(token->description().find("first-cell excerpt of the neighboring-rung even-eighth stage")!=std::string::npos&&
            instructions->getText().toStdString().find("first-cell excerpt of the neighboring-rung even-eighth stage")!=std::string::npos,
            "Practice retains source-supported excerpt qualifier");
        counts(snapshot(prefix+"-practice-entry"),index);
        click(h.practice(),"Back");
        h.wait([&]{return h.home->page()==H::Page::Learn;},"queued Back navigation");
        counts(snapshot(prefix+"-practice-back"),index);
        ck(h.home->page()==H::Page::Learn&&learn.selectedVariant()==variant,
            "Back keeps exact variant; expected "+variant+", observed "+learn.selectedVariant()+
            ", page "+std::to_string(static_cast<int>(h.home->page())));
        click(learn,"Practice selected case");h.tick();
        ck(h.practice().lessonAdmission()->identity()==token->identity(),"entry preserves immutable source admission");
        click(h.practice(),"Audio settings");h.tick();
        if(h.home->audioSettings().snapshot().state==output::State::Closed){click(A::settings(*h.home),"Connect audio");h.tick();click(A::settings(*h.home),"Enable audio");h.blocks(1);}
        click(A::settings(*h.home),"Back to Practice");h.tick();counts(snapshot(prefix+"-audio-ready"),index);
        click(h.practice(),"Start selected case");h.wait([&]{return h.practice().captureSession()->startTaken();},"explicit Start");
        ck(!h.practice().rebindCaptureSession(h.sessionId)&&h.practice().captureSessionId()==selectedSession,"active Attempt cannot rebind its Session");
        const auto context=h.practice().captureSession()->binding().context;
        for(const auto* key:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs"})ck(context.object().at(key)==token->identity().object().at(key),std::string("allocated exact ")+key);
        ck(context.object().at("session_id").string()==selectedSession,"Attempt links source-bound Session");
        ck(context.object().at("configuration").object().at("source_hashes")==token->identity().object().at("source_hashes"),"source hashes preserved");
        ck(!context.object().at("configuration").object().at("source_task_completion").boolean()&&!context.object().at("configuration").find("progression_condition"),"no whole-source completion or comparable credit");
        capture_fixture::write(out/(prefix+"-context.json"),storage::canonical(context));capture_fixture::write(out/(prefix+"-admission.json"),storage::canonical(token->identity()));
        const auto& cfg=h.practice().coordinator().configuration();
        const auto program=reference::compile(token->model(),token->referenceConfiguration(h.practice().coordinator().owner(),1,cfg.rate,cfg.bpm));
        ck(program.voices().size()==static_cast<std::size_t>(index<2?30:60),"actual reference program has exact 30/60 ordered voices");
        counts(snapshot(prefix+"-explicit-start"),index+1);
        float peak=0;
        // The two-cell source span is 31 quarter beats; the old four-note
        // fixture's 3,000 software blocks stopped before this span ended.
        for(int block=0;block<10000&&h.practice().captureSession()->phase()!=capture::SessionPhase::Review;++block){peak=std::max(peak,platform::OutputTestAccess::block(A::output(*h.home)));h.tick();}
        ck(peak>0,"software callback produces nonzero reference PCM");
        h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Review;},"natural exact selected span");
        ck(h.practice().coordinator().completedCycles()==1,"one selected span completed by software callback");
        click(h.practice(),"Save result");h.wait([&]{return h.practice().captureSession()->phase()==capture::SessionPhase::Saved;},"saved original");h.blocks(2);h.wait([&]{return h.practice().audioCanRelease();},"audio cleanup");
        ck(!h.practice().captureSession()->original()->assessment,"no inferred Clean assessment");
        capture_fixture::write(out/(prefix+"-original.json"),h.practice().captureSession()->original()->bytes);
        counts(snapshot(prefix+"-saved"),index+1);click(h.practice(),"Guided summary");h.tick();
        h.wait([&]{return !guided.busy();},"Guided summary");
        clickId(guided,"stop");h.wait([&]{return !guided.running()&&!guided.busy();},"explicit Session close");
        click(guided,"Back");click(*h.home,"Learn");h.tick();
    }
    ck(learn.selectLesson("fg:item:000001")&&learn.selectVariant("fg:variant:000001"),"unadmitted case remains selectable");
    ck(!button(learn,"Practice selected case").isEnabled(),"unadmitted Practice remains disabled");counts(snapshot("unadmitted-selection"),4);
    const auto before=snapshot("before-reopen");const auto adapted=progression::adaptSnapshot(before);
    ck(adapted.records.size()==4,"exactly four explicit Attempts");for(const auto& r:adapted.records)ck(!r.complete&&r.condition.null()&&r.assessment.null(),"no automatic credit or mastery");
    const auto shown=desktop::presentProgress(before,"2026-09-24T01:45:00Z",learn.catalog());
    const auto& coverage=shown.projection.object().at("domain_coverage").object();
    ck(coverage.at("status").string()=="mapped_recorded_activity"&&coverage.at("mapped_attempts")==json::Value::fromInteger(4)
       &&coverage.at("unmapped").array().empty()&&shown.text.find("Mapped Attempts: 4 | Freeplay kept separate: 0 | Unmapped Attempts: 0")!=std::string::npos
       &&shown.text.find("Technique/fretboard | recorded Attempts: 4")!=std::string::npos,
       "source-reviewed Level13 A/A-Bb D/U Attempts map once to Technique/fretboard without inferred credit");
    ck(h.home->detachForStoreReopen(),"safe Home detach");h.store.reset();storage::StoreOptions options;options.path=h.dir/"profile.sqlite";options.create=false;options.preferenceValidator=metronome::preferenceValidator;h.store=std::make_unique<storage::ProfileStore>(options);
    const auto after=snapshot("after-reopen");ck(after.data.object().at("authoritative")==before.data.object().at("authoritative"),"restart preserves exact authoritative Session and Attempts");
    ck(h.home->configureCapture(*h.store,h.sessionId,"America/New_York"),"reattach original local Session");
    std::ofstream(out/"summary.json")<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"actual_store\":true,\"software_device\":true,\"installed_app\":false,\"physical_listening\":false,\"attempts\":4,\"credit\":false}\n";
    std::cout<<"PASS "<<checks<<" Level13 two-case source-backed desktop/history checks; software device only\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
