#include "content/LessonCatalog.hpp"
#include "practice/LessonAttempt.hpp"
#include "platform/PracticePlayback.hpp"
#include "progression/ProgressionAdapter.hpp"
#include "core/TabPresentation.hpp"
#include "practice_capture_fixtures.hpp"
#include <cmath>
#include <iostream>
#include <set>
#include <type_traits>

using namespace fathom;using namespace capture_fixture;
namespace {
int checks=0;std::ofstream trace;
void check(bool good,const std::string& name){++checks;trace<<checks<<'\t'<<name<<'\t'<<(good?"PASS":"FAIL")<<std::endl;if(!good)throw std::runtime_error(name);}
template<class F>void refuses(F f,const std::string& name){std::string error;try{f();}catch(const std::exception& e){error=e.what();}check(!error.empty(),name);trace<<"REFUSAL\t"<<name<<'\t'<<error<<std::endl;}
std::uint64_t length(const Rational& span,std::uint32_t rate=44100,std::uint16_t bpm=120){scheduler::FrameRatio f;std::uint64_t n{};if(!scheduler::samples(span,rate,bpm,scheduler::BeatUnit::Quarter,f)||!scheduler::round(f,n))throw std::runtime_error("Sample length refused");return n;}
scheduler::Owner testOwner(){scheduler::Owner o;o.id[0]=42;o.id[6]=0x40;o.id[8]=0x80;o.epoch=o.generation=1;return o;}
template<class F>void pollUntil(capture::PracticeSession& session,F predicate){const auto deadline=now()+6000;while(!predicate()){if(now()>deadline)throw std::runtime_error("Declared six-second Store/controller watchdog");session.poll(now(),"2026-09-08T17:20:30Z");std::this_thread::sleep_for(std::chrono::milliseconds(1));}}
struct Collected {std::vector<scheduler::Fact> facts;static bool receive(void* p,const scheduler::Fact& f)noexcept{static_cast<Collected*>(p)->facts.push_back(f);return true;}};
// Offline, whole finite projection; no output driver, physical claim or Practice credit.
practice::Coordinator posedOriginal(const lesson::Admission& a,const practice::Configuration& cfg){
    auto request=capture::lessonStart(a,a.practiceConfiguration(44100,120),"00000000-0000-4000-8000-000000000001","2026-09-08T17:20:00Z","America/New_York",1);
    practice::Coordinator coordinator;coordinator.begin(testOwner(),practice::Kind::Attempt,storage::canonical(request.binding.context),cfg);return coordinator;
}
void renderReference(const lesson::Admission& a,const std::filesystem::path& out){
    const auto c=a.referenceConfiguration(testOwner(),1,44100,120);const auto p=reference::compile(a.model(),c);
    tab::Document tab(a.model());check(&p.source()==a.model().get()&&&tab.source()==&a.model()->source(),"same immutable reference and TAB model");
    check(p.voices().size()==a.model()->source().events.size(),"every accepted source note has one reference voice");
    const auto end=length(a.span());scheduler::Cursor cursor;reference::Renderer renderer;Collected collected;
    check(cursor.start(p.schedule(),c.owner,c.binding)&&renderer.bind(p),"explicit one-pass technical reference bind");
    auto stop=[](void*,const scheduler::Fact&)noexcept{return scheduler::BoundaryDecision{scheduler::BoundaryAction::Stop,nullptr};};
    std::ofstream pcm(out/"reference.f32",std::ios::binary),facts(out/"reference-facts.tsv");bool finite=true;double peak=0;std::uint64_t count=0;
    for(std::uint64_t frame=0;frame<end;++frame){collected.facts.clear();const bool okay=cursor.process(1,c.owner,Collected::receive,&collected,stop);
        if(!okay&&cursor.snapshot().processedThrough!=end)throw std::runtime_error("Unexpected reference termination");
        for(const auto& f:collected.facts){if(f.frame==frame){if(!renderer.accept(f))throw std::runtime_error("Reference fact rejected");facts<<f.frame<<'\t'<<static_cast<int>(f.kind)<<'\t'<<f.sourceEvent<<'\t'<<static_cast<int>(f.action)<<'\n';}}
        float sample{};if(!renderer.sampleFrame(frame,sample))throw std::runtime_error("Reference sample rejected");finite=finite&&std::isfinite(sample);peak=std::max(peak,std::abs(static_cast<double>(sample)));pcm.write(reinterpret_cast<const char*>(&sample),sizeof sample);++count;
        for(const auto& f:collected.facts)if(f.frame==frame+1){if(!renderer.accept(f))throw std::runtime_error("Reference end fact rejected");facts<<f.frame<<'\t'<<static_cast<int>(f.kind)<<'\t'<<f.sourceEvent<<'\t'<<static_cast<int>(f.action)<<'\n';}
    }
    check(finite&&peak>0&&count==end,"finite nonzero PCM exactly selected one-pass duration");
    for(std::size_t i=0;i<p.voices().size();++i)check(p.voices()[i].sourceEvents==std::vector<std::string>{a.model()->source().events[i].id},"source event identity retained "+a.model()->source().events[i].id);
    write(out/"reference-summary.json",storage::canonical(O{{"frames",n(static_cast<std::int64_t>(count))},{"rate",n(44100)},{"bpm",n(120)},{"physical_output",false},{"native",false}}));
}
practice::Progress drive(platform::PracticePlayback& provider,practice::Coordinator& coordinator,
                         std::uint64_t stopAfter,bool pause,std::ofstream& log){
    const auto owner=coordinator.owner();auto buses=std::make_unique<platform::Buses>();output::Snapshot state;state.owner=owner;state.request.epoch=owner.epoch;state.state=output::State::Running;
    std::uint64_t through=0;practice::Progress last;std::size_t blocks=0;bool finite=true,postTargetAttack=false;double peak=0;
    auto drain=[&]{while(provider.nextProgress(last)){coordinator.progress(last);log<<owner.generation<<'\t'<<last.sequence<<'\t'<<last.clientAcceptedThrough<<'\t'<<last.completedCycles<<'\t'<<static_cast<int>(last.state)<<'\n';}scheduler::Fact f;while(provider.nextFact(f)){log<<"FACT\t"<<owner.generation<<'\t'<<f.frame<<'\t'<<static_cast<int>(f.kind)<<'\t'<<f.sourceEvent<<'\t'<<static_cast<int>(f.action)<<'\t'<<f.cycle<<'\n';if(!pause&&f.kind==scheduler::FactKind::Event&&f.action==scheduler::Action::Attack&&f.frame>=stopAfter)postTargetAttack=true;};};
    while(through<stopAfter||(!pause&&state.state==output::State::Running)){platform::PracticePlayback::observe(&provider,state);drain();*buses={};const auto frames=static_cast<std::uint32_t>(through<stopAfter?std::min<std::uint64_t>(256,stopAfter-through):256);const auto got=platform::PracticePlayback::render(&provider,owner,coordinator.configuration().rate,frames,*buses);
        if(!got.valid||(!got.submittedFrames&&!got.terminal)||got.submittedFrames>frames)throw std::runtime_error("Actual provider rejected expected prefix");
        for(std::uint32_t i=0;i<got.submittedFrames;++i){const auto sample=(*buses)[0][0][i];finite=finite&&std::isfinite(sample);peak=std::max(peak,std::abs(static_cast<double>(sample)));}
        through+=got.submittedFrames;++blocks;if(through>stopAfter)throw std::runtime_error("Provider exceeded declared selected target");state.submittedFrames=through;
        if(got.terminal){state.state=output::State::Unresolved;state.uncertainThrough=through;}
        platform::PracticePlayback::observe(&provider,state);drain();if(got.terminal)break;
    }
    if(pause){state.state=output::State::Paused;state.requestedStopNs=999;state.uncertainThrough=through;platform::PracticePlayback::observe(&provider,state);drain();}
    check(finite&&peak>0&&blocks>0&&through==stopAfter&&!postTargetAttack,"actual software provider exact finite selected prefix");practice::Progress retained;check(provider.reclaim(retained)&&retained.owner==owner,"original callback owner retired with terminal evidence");return last;
}
}
int main(int argc,char** argv){try{
    if(argc!=3&&argc!=4)throw std::invalid_argument("Expected absolute accepted bundle and new evidence directory, optionally --practice-only");const bool practiceOnly=argc==4&&std::string(argv[3])=="--practice-only";if(argc==4&&!practiceOnly)throw std::invalid_argument("Unknown bounded test selection");const std::filesystem::path out(argv[2]);
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::invalid_argument("Evidence path must be new and absolute");std::filesystem::create_directories(out);std::filesystem::permissions(out,std::filesystem::perms::owner_all);trace.open(out/"checks.tsv");
    static_assert(!std::is_default_constructible_v<lesson::Admission>);
    const auto catalog=lesson::Catalog::load(argv[1]);std::vector<std::shared_ptr<const lesson::Admission>> practices;std::size_t references=0,refused=0;
    for(const auto& l:catalog->lessons())for(const auto& v:l.variants){
        if(practiceOnly){if(v.technicallyRenderable){auto a=catalog->admit(l.id,v.id);if(a->practiceAllowed()){practices.push_back(a);std::filesystem::create_directory(out/v.id);}}continue;}
        if(!v.technicallyRenderable){refuses([&]{catalog->admit(l.id,v.id);},"unsupported variant "+v.id);++refused;continue;}
        const auto a=catalog->admit(l.id,v.id);++references;check(a->model()==v.model&&!a->model()->source().syntheticFixture,"trusted exact nonsynthetic selection "+v.id);
        check(at(a->identity(),"content_revision")==n(2)&&at(a->identity(),"whole_task_completion")==V(false),"canonical revision and bounded task disposition");
        const auto dir=out/v.id;std::filesystem::create_directory(dir);write(dir/"admission.json",storage::canonical(a->identity()));renderReference(*a,dir);
        platform::PracticePlayback raw;const auto rc=a->referenceConfiguration(testOwner(),1,44100,120);
        auto pretend=practice::Configuration{};pretend.span=a->span();pretend.countIn=practice::CountIn::Off;pretend.faithfulWholeSpan=true;pretend.targetCycles=1;
        refuses([&]{raw.prepare(a->model(),rc,pretend,1);},"raw actual curriculum cannot bypass token");
        if(a->practiceAllowed()){practices.push_back(a);check(a->span()==(l.level==3?Rational{5}:Rational{8}),"exact direction/cell span");}
        else {refuses([&]{a->practiceConfiguration(44100,120);},"L15 incomplete illustration cannot Practice");refuses([&]{practice::Coordinator posed;posed.begin(testOwner(),practice::Kind::Attempt,"{}",pretend);raw.prepareLesson(*a,rc,posed,1);},"typed L15 cannot forge faithful Practice flag");}
    }
    if(!practiceOnly){check(references==10&&practices.size()==6&&refused==39,"exact reviewed permission census");
    refuses([&]{catalog->admit("fg:item:000001","fg:variant:000006");},"foreign variant owner refusal");refuses([&]{catalog->admit("missing","missing");},"unknown identity refusal");
    auto independent=lesson::Catalog::load(argv[1]);auto survives=independent->admit("fg:item:000002","fg:variant:000006");independent.reset();check(survives->model()->source().events.size()==20,"admission lifetime survives catalog destruction");
    }
    const auto& a=*practices.front();auto cfg=a.practiceConfiguration(44100,120);const auto rc=a.referenceConfiguration(testOwner(),1,44100,120);
    if(!practiceOnly){for(int which=0;which<9;++which){auto bad=cfg;switch(which){case 0:bad.span=Rational{4};break;case 1:bad.targetCycles=33;break;case 2:bad.countIn=practice::CountIn::AuthoredBar;break;case 3:bad.meter={{4,4}};break;case 4:bad.sourceRequiresCountIn=true;break;case 5:bad.faithfulWholeSpan=false;break;case 6:bad.unit=scheduler::BeatUnit::Eighth;break;case 7:bad.bpm=19;break;case 8:bad.bpm=301;break;}
        platform::PracticePlayback p;refuses([&]{auto original=posedOriginal(a,bad);p.prepareLesson(a,rc,original,1);},"altered Practice configuration "+std::to_string(which));}
    for(int which=0;which<5;++which){auto bad=rc;switch(which){case 0:bad.sourceBinding=practices[1]->sourceBinding();break;case 1:bad.cycle=Rational{4};break;case 2:bad.intro=Rational{4};break;case 3:bad.unit=scheduler::BeatUnit::Half;break;case 4:bad.bpm=121;break;}
        platform::PracticePlayback p;refuses([&]{auto original=posedOriginal(a,cfg);p.prepareLesson(a,bad,original,1);},"foreign or mismatched reference configuration "+std::to_string(which));}
    {auto original=posedOriginal(a,cfg);platform::PracticePlayback p;refuses([&]{p.prepareLesson(*practices[1],practices[1]->referenceConfiguration(testOwner(),1,44100,120),original,1);},"same-duration foreign variant cannot replace allocated context");
     auto changed=cfg;changed.bpm=121;auto wrong=posedOriginal(a,changed);refuses([&]{p.prepareLesson(a,a.referenceConfiguration(testOwner(),1,44100,121),wrong,1);},"changed tempo cannot replace original context values");
     auto foreign=testOwner();foreign.id[1]=99;refuses([&]{p.prepareLesson(a,a.referenceConfiguration(foreign,1,44100,120),original,1);},"foreign allocated owner cannot claim original context");
     refuses([&]{p.prepareLesson(a,rc,original,0);},"remaining target must match original");}
    check(a.practiceConfiguration(44100,20).bpm==20&&a.practiceConfiguration(44100,300).bpm==300,"finite explicit tempo endpoints");
    }
    // Original mutable request counterexamples: refusal is before any publication.
    for(int which=0;which<7;++which){auto request=capture::lessonStart(a,cfg,"00000000-0000-4000-8000-000000000001","2026-09-08T17:20:00Z","America/New_York",1);auto& configuration=request.binding.context.object().at("configuration");
        switch(which){case 0:configuration.object()["source_hashes"]=O{{"wrong",std::string(64,'c')}};break;
        case 1:configuration.object()["progression_condition"]=nullptr;break;case 2:configuration.object()["source_task_completion"]=true;break;
        case 3:configuration.object()["synthetic_fixture"]=true;break;case 4:configuration.object()["beat_reference_q"]=q(2);break;
        case 5:configuration.object()["authored_tempo_ref"]=nullptr;break;case 6:configuration.object().at("values").object()["selected_bpm"]=n(121);break;}
        practice::Coordinator original;original.begin(testOwner(),practice::Kind::Attempt,storage::canonical(request.binding.context),cfg);platform::PracticePlayback provider;
        refuses([&]{provider.prepareLesson(a,rc,original,1);},"mutated original cannot alter source/non-credit/clock fields "+std::to_string(which));}
    storage::StoreOptions options;options.path=out/"profile.sqlite";options.create=true;options.createdUtc="2026-09-08T17:20:00Z";std::string session;V snapshot;
    {
        storage::ProfileStore store(options);session=confirmed(store.createSession(storage::newUuid(),options.createdUtc,"America/New_York")).owner;
        for(const auto& selected:practices){const auto& token=*selected;auto c=token.practiceConfiguration(44100,120);auto req=capture::lessonStart(token,c,session,options.createdUtc,"America/New_York",1);
            check(req.binding.owner.empty()&&!at(req.binding.context,"configuration").find("progression_condition"),"no invented result owner or source completion comparability");
            for(const auto* k:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs"})check(at(req.binding.context,k)==at(token.identity(),k),std::string("exact canonical allocation ")+k);
            check(req.binding.sourceHashes==at(token.identity(),"source_hashes"),"original exact source hash coverage");
            const auto variant=at(token.identity(),"variant_id").string();std::ofstream log(out/variant/"practice-progress.tsv");
            practice::Coordinator coordinator;capture::PracticeSession capture(store,coordinator);check(capture.start(req,1,now()),"actual Store allocation requested");check(!capture.takeStart(now()),"no start before initial checkpoint receipt");pollUntil(capture,[&]{return capture.phase()==capture::SessionPhase::Ready;});const auto owner=capture.takeStart(now());check(owner&&owner->id==coordinator.owner().id,"actual allocator identity released after checkpoint");
            platform::PracticePlayback provider;check(provider.prepareLesson(token,token.referenceConfiguration(*owner,1,c.rate,c.bpm),coordinator,1),"actual typed provider prepared");
            refuses([&]{provider.prepareLesson(token,token.referenceConfiguration(*owner,1,c.rate,c.bpm),coordinator,1);},"same original generation cannot prepare twice");
            const auto cut=length(token.span())/3;const auto interrupted=drive(provider,coordinator,cut,true,log);check(interrupted.completedCycles==0&&interrupted.partial&&!interrupted.hasPhysicalConfirmation&&interrupted.requestedStopNs==999,"partial request/client progress/unknown physical facts remain separate");
            capture.poll(now(),options.createdUtc);const auto next=coordinator.nextResumeOwner();check(next.id==owner->id&&next.generation==2,"resume retains original owner and increments generation");
            auto staged=coordinator;staged.resume();check(provider.prepareLesson(token,token.referenceConfiguration(next,2,c.rate,c.bpm),staged,1),"fresh full selected-span replay prepared");coordinator.resume();const auto final=drive(provider,coordinator,length(token.span()),false,log);
            check(final.completedCycles==1&&coordinator.completedCycles()==1&&coordinator.activeFrames()==cut+length(token.span()),"partial replay time retained without duplicate completed cycle");
            capture.poll(now(),options.createdUtc);check(capture.phase()==capture::SessionPhase::Review&&!capture.again(true),"unresolved original remains review before Again");check(capture.save(nullptr,capture::Outcome::Natural,now()),"explicit absent assessment saves original");pollUntil(capture,[&]{return capture.phase()==capture::SessionPhase::Saved;});pollUntil(capture,[&]{return capture.canLeave(true);});
            check(capture.original()&&at(at(capture.original()->value,"result"),"assessment").null(),"playback does not infer Clean");write(out/variant/"original.json",capture.original()->bytes);
        }
        const auto snap=confirmed(store.snapshot(storage::newUuid()));snapshot=snap.data;write(out/"snapshot.json",storage::canonical(snapshot));
        const auto evidence=progression::adaptSnapshot(snap);check(evidence.records.size()==6,"six actual unique stored Attempts");
        bool excluded=true;for(const auto& record:evidence.records){excluded=excluded&&!record.complete&&record.condition.null()&&record.assessment.null();for(const auto& s:record.segments)excluded=excluded&&!s.wholeTarget;}
        check(excluded,"selected-case playback cannot earn comparable PB or complete source-task credit");
        const auto& tables=at(snapshot,"authoritative");check(at(tables,"finalized").array().size()==6&&at(tables,"identity").array().size()==6&&at(tables,"pending").array().empty()&&at(tables,"source_attestation").array().empty(),"one original each no unresolved duplicate or fabricated source attestation");
    }
    options.create=false;{storage::ProfileStore reopened(options);const auto after=confirmed(reopened.snapshot(storage::newUuid()));check(after.data==snapshot,"ordinary Store reopen preserves exact authoritative originals");write(out/"reopened.json",storage::canonical(after.data));}
    write(out/"summary.json",storage::canonical(O{{"status","PASS"},{"checks",n(checks)},{"native_audio",false},{"physical_output",false},{"real_learner_data",false},{"curriculum_source_actual",true},{"runtime_scenario","synthetic software callback delivery and private Store"}}));std::cout<<"PASS "<<checks<<" lesson runtime checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
