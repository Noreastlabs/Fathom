// Actual selected-model/provider/TAB/Store consumers with synthetic callback acknowledgments.
#define main retained_pulse_campaign_main
#include "m1_lesson_pulse_tests.cpp"
#undef main
#include "core/TabPlayback.hpp"
#include <tuple>

int main(int argc,char** argv){try{
    if(argc!=4)throw std::invalid_argument("Expected accepted bundle, new evidence directory and retained full-span original");
    const std::filesystem::path out(argv[2]);
    if(!out.is_absolute()||std::filesystem::exists(out))throw std::invalid_argument("Use new absolute evidence directory");
    std::filesystem::create_directories(out);
    std::filesystem::permissions(out,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
    checkTrace.open(out/"checks.tsv");
    const auto catalog=lesson::Catalog::load(argv[1]);
    const auto full=catalog->admit("fg:item:000002","fg:variant:000006");
    const auto prior=json::parse(content::readBounded(argv[3],1024*1024));
    check(full->identity()==at(at(at(prior,"context"),"configuration"),"runtime_admission"),"full-span identity byte value unchanged from retained native original");
    check(V(full->sourceBinding())==at(at(at(prior,"context"),"configuration"),"source_binding"),"full-span binding unchanged");
    A cases;
    for(const auto* variant:{"fg:variant:000006","fg:variant:000008","fg:variant:000010","fg:variant:000012"}){
        const auto parent=catalog->admit("fg:item:000002",variant);
        for(std::uint32_t ordinal=1;ordinal<=5;++ordinal){
            const auto a=catalog->admitCell("fg:item:000002",variant,ordinal);
            const auto& source=parent->model()->source();const auto& selected=a->model()->source();
            check(a->sourceStart()==Rational{static_cast<std::int64_t>(ordinal-1)}&&a->span()==Rational{1},"selected length and original variant origin");
            check(selected.preservedRecordJson==source.preservedRecordJson&&selected.sourceRefs==source.sourceRefs&&selected.itemId==source.itemId&&selected.contentRevision==source.contentRevision&&selected.contentVersion==source.contentVersion,"complete original record/version/provenance preserved");
            check(selected.events.size()==4&&a->sourceBinding()!=parent->sourceBinding(),"four-note projection has distinct selection binding");
            check(at(at(a->identity(),"selection"),"parent_source_binding")==V(parent->sourceBinding()),"section binds immutable parent");
            A events;
            for(std::size_t i=0;i<4;++i){
                const auto& e=selected.events[i];const auto& originalEvent=source.events[static_cast<std::size_t>(ordinal-1)*4+i];
                const auto& t=e.tones.front();const auto& originalTone=originalEvent.tones.front();
                check(e.id==originalEvent.id&&e.sourceRef==originalEvent.sourceRef&&e.handDirection==originalEvent.handDirection&&e.kind==originalEvent.kind,"original source event identity and pick direction preserved");
                check(t.string==originalTone.string&&t.fret==originalTone.fret&&t.midi==originalTone.midi&&t.finger==originalTone.finger&&t.attack==originalTone.attack&&t.tieFrom==originalTone.tieFrom,"original tone/string/fret/finger/attack preserved");
                check(e.span.onset==Rational{static_cast<std::int64_t>(i),4}&&e.span.duration==Rational{1,4},"exact local quarter fractions preserve durations");
                events.push_back(O{{"id",e.id},{"source_ref",e.sourceRef},{"hand",e.handDirection},{"string",n(t.string)},{"fret",n(t.fret)},{"midi",n(t.midi)},
                    {"finger",t.finger},{"attack",n(static_cast<std::int64_t>(t.attack))},{"tie_from",t.tieFrom},
                    {"onset",q(static_cast<std::int64_t>(i),4)},{"duration",q(e.span.duration->numerator(),e.span.duration->denominator())}});
            }
            auto cfg=a->practiceConfiguration(44100,137);cfg.targetCycles=2;auto co=original(*a,cfg,true);
            const auto ctx=json::parse(co.context());check(at(ctx,"span")==V(O{{"start",q(ordinal-1)},{"end",q(ordinal)}}),"immutable context uses original interval");
            platform::PracticePlayback provider;
            check(provider.prepareLesson(*a,a->referenceConfiguration(co.owner(),1,cfg.rate,cfg.bpm),co,2),"exact selected model prepares actual provider");
            const auto terminal=frames(Rational{2},cfg);const auto rendered=drive(provider,co,terminal,false);
            using Fact=std::tuple<int,std::uint64_t,std::uint64_t,std::uint32_t,int,int>;
            std::vector<Fact> expected,actual;
            for(std::uint64_t cycle=0;cycle<2;++cycle){
                for(std::uint32_t note=0;note<4;++note){
                    expected.emplace_back(0,frames(Rational{static_cast<std::int64_t>(cycle*4+note),4},cfg),cycle,note+1,0,0);
                    expected.emplace_back(0,frames(Rational{static_cast<std::int64_t>(cycle*4+note+1),4},cfg),cycle,note+1,0,1);
                }
                expected.emplace_back(1,frames(Rational{static_cast<std::int64_t>(cycle+1)},cfg),cycle+1,0,0,0);
            }
            for(const auto& f:rendered.reference)actual.emplace_back(static_cast<int>(f.kind),f.frame,f.cycle,f.sourceEvent,static_cast<int>(f.role),static_cast<int>(f.action));
            std::sort(expected.begin(),expected.end());std::sort(actual.begin(),actual.end());
            check(actual==expected,"every attack/release/cycle matches source-derived global rational frame oracle");
            check(rendered.pulseFrames==std::vector<std::uint64_t>{0,frames(Rational{1},cfg)}&&co.completedCycles()==2&&co.activeFrames()==terminal,"two exact local passes and pulses stop before third attack");
            if(ordinal==1||ordinal==3||ordinal==5){
                auto tabOwner=original(*a,cfg,true);auto doc=std::make_shared<const tab::Document>(a->model());tab::Playback tab;tab.bind(doc,a->model(),tabOwner);std::uint64_t sequence{};
                for(std::int64_t note=0;note<8;++note){
                    const auto through=frames(Rational{note,4},cfg)+1;const auto completed=note>=4?1U:0U;
                    practice::Progress p;p.owner=tabOwner.owner();p.sequence=++sequence;p.clientAcceptedThrough=p.scheduledThrough=p.activeFrames=through;
                    p.completedCycles=completed;p.cursorFrames=through-frames(Rational{static_cast<std::int64_t>(completed)},cfg);p.partial=true;p.state=practice::State::Running;
                    check(tabOwner.progress(p)&&tab.update(tabOwner),"TAB accepts authoritative section prefix");
                    check(tab.position().events==std::vector<std::string>{selected.events[static_cast<std::size_t>(note%4)].id},"TAB uses exact original selected event IDs across repeat");
                }
                auto mismatch=original(*a,cfg,true);auto otherDoc=std::make_shared<const tab::Document>(parent->model());tab::Playback wrongTab;
                refuses([&]{wrongTab.bind(otherDoc,a->model(),mismatch);},"full-document and selected render pointer mismatch refused");
            }
            cases.push_back(O{{"identity",a->identity()},{"events",events},{"frames",n(static_cast<std::int64_t>(terminal))},{"notes_sha256",digest(rendered.notes)}});
        }
    }
    for(std::uint32_t invalid:{0U,6U,UINT32_MAX})refuses([&]{catalog->admitCell("fg:item:000002","fg:variant:000006",invalid);},"unsupported cell ordinal refused");
    for(const auto& selection:std::vector<std::pair<std::string,std::string>>{{"fg:item:000003","fg:variant:000029"},{"fg:item:000004","fg:variant:000033"},{"fg:item:000002","fg:variant:000007"}})
        refuses([&]{catalog->admitCell(selection.first,selection.second,1);},"unsupported connected cell, illustration or variant refused");
    const auto a=catalog->admitCell("fg:item:000002","fg:variant:000006",3);
    auto cfg=a->practiceConfiguration(44100,60);cfg.targetCycles=2;
    for(int corruption=0;corruption<7;++corruption){
        auto req=capture::lessonStart(*a,cfg,"00000000-0000-4000-8000-000000000001","2026-09-12T13:40:00Z","America/New_York",1,true);
        auto& ctx=req.binding.context;
        switch(corruption){
        case 0:ctx.object()["span"]=O{{"start",q(0)},{"end",q(1)}};break;
        case 1:ctx.object().at("span").object()["end"]=q(4);break;
        case 2:ctx.object().at("configuration").object()["runtime_admission"]=catalog->admitCell("fg:item:000002","fg:variant:000006",4)->identity();break;
        case 3:ctx.object().at("configuration").object()["source_binding"]=full->sourceBinding();break;
        case 4:ctx.object().at("target").object()["cycles"]=n(1);break;
        case 5:ctx.object().at("configuration").object().at("runtime_admission").object().at("selection").object().at("source_span").object()["start"]=q(1);break;
        case 6:{auto& ids=ctx.object().at("configuration").object().at("runtime_admission").object().at("selection").object().at("event_ids").array();std::swap(ids[0],ids[1]);break;}
        }
        practice::Coordinator co;co.begin(owner(),practice::Kind::Attempt,storage::canonical(ctx),cfg);
        refuses([&]{a->validateOriginal(co);},"original section identity/span/target alteration refused");
        if(corruption==1)refuses([&]{capture::validateContext(req.binding,cfg);},"Capture refuses original length mismatch independently");
    }
    for(auto cut:{Rational{1,2},Rational{2}}){auto bad=cfg;bad.span=cut;refuses([&]{a->validatePractice(bad);},"interior or expanded cell cut refused");}
    write(out/"cases.json",storage::canonical(cases));
    // Actual immutable Store result, partial second traversal then one full replay.
    storage::StoreOptions options;options.path=out/"profile.sqlite";options.create=true;options.createdUtc="2026-09-12T13:40:00Z";V before;
    {storage::ProfileStore store(options);const auto session=confirmed(store.createSession(storage::newUuid(),options.createdUtc,"America/New_York",{},O{{"synthetic_fixture",true}})).owner;
        auto req=capture::lessonStart(*a,cfg,session,options.createdUtc,"America/New_York",1,true);practice::Coordinator co;capture::PracticeSession capture(store,co);
        check(capture.start(req,1,now()),"Store-backed section original allocation");pulseUntil(capture,[&]{return capture.phase()==capture::SessionPhase::Ready;});auto first=capture.takeStart(now());check(first.has_value(),"initial checkpoint before provider");
        const auto initial=capture::makeCheckpoint(co,capture.binding(),1);const auto initialSnap=at(json::parse(initial.bytes),"practice_snapshot");
        check(at(initialSnap,"cursor")==q(2)&&at(initialSnap,"active")==q(0),"zero-output checkpoint has source origin2 and active0");
        platform::PracticePlayback provider;check(provider.prepareLesson(*a,a->referenceConfiguration(*first,1,cfg.rate,cfg.bpm),co,2),"Store original cell prepared");
        const std::uint64_t span=44100,cut=span+11025;drive(provider,co,cut,true);capture.poll(now(),options.createdUtc);
        const auto interrupted=capture::makeCheckpoint(co,capture.binding(),2);write(out/"interrupted-checkpoint.json",interrupted.bytes);
        const auto partial=at(json::parse(interrupted.bytes),"practice_snapshot");
        check(at(partial,"cursor")==q(9,4)&&at(partial,"active")==q(5,4)&&at(partial,"completed")==V(A{n(1)}),"canonical cursor9/4, actual5/4 seconds and only one complete traversal");
        co.resume();check(provider.prepareLesson(*a,a->referenceConfiguration(co.owner(),2,cfg.rate,cfg.bpm),co,1),"resume only remaining source cell from declared boundary");drive(provider,co,span,false);
        capture.poll(now(),options.createdUtc);check(capture.phase()==capture::SessionPhase::Review&&capture.save(nullptr,capture::Outcome::Natural,now()),"Save actual replay facts with absent self assessment");
        pulseUntil(capture,[&]{return capture.phase()==capture::SessionPhase::Saved&&capture.canLeave(true);});const auto& envelope=*capture.original();write(out/"original.json",envelope.bytes);
        const auto& result=at(envelope.value,"result");const auto& traversals=at(result,"traversals").array();
        check(envelope.active==Rational{9,4}&&at(result,"completed_cycles")==V(A{n(1),n(2)})&&traversals.size()==3,"replay actual9/4 seconds with completed1,2 and retained partial");
        check(traversals[0]==V(O{{"cycle",n(1)},{"start",q(2)},{"end",q(3)},{"status","complete"}})&&traversals[1]==V(O{{"cycle",n(2)},{"start",q(2)},{"end",q(9,4)},{"status","partial_interrupted"}})&&traversals[2]==V(O{{"cycle",n(2)},{"start",q(2)},{"end",q(3)},{"status","complete"}}),"canonical complete/partial/replayed traversal ledger exact");
        for(const auto& interruption:at(result,"interruptions").array())if(at(interruption,"kind")==V("transport_generation"))check(at(interruption,"resume_boundary_quarters")==q(2),"every generation retains canonical safe resume boundary");
        const auto snapshot=confirmed(store.snapshot(storage::newUuid()));before=snapshot.data;write(out/"before.json",storage::canonical(before));const auto adapted=progression::adaptSnapshot(snapshot);
        check(adapted.records.size()==1&&!adapted.records[0].complete&&adapted.records[0].condition.null()&&adapted.records[0].assessment.null(),"cell playback is no source completion or PB/mastery evidence");
        storage::RecoveryBinding binding{envelope.owner,"Attempt",at(envelope.value,"context"),{},envelope.bytes,0,0};
        const auto recovered=storage::planRecovery(confirmed(store.recoveryState(storage::newUuid(),envelope.owner)),binding);
        check(recovered.bytes==envelope.bytes,"final recovery preserves original bytes with no second offset");
    }
    options.create=false;{storage::ProfileStore reopened(options);const auto after=confirmed(reopened.snapshot(storage::newUuid()));check(after.data==before,"ordinary Store reopen preserves exact section original");write(out/"after.json",storage::canonical(after.data));}
    // Actual unsealed running checkpoint recovery; no device, crash or power-loss claim.
    options.path=out/"recovery"/"profile.sqlite";options.create=true;storage::RecoveryBinding recoveryBinding;
    {storage::ProfileStore store(options);const auto session=confirmed(store.createSession(storage::newUuid(),options.createdUtc,"America/New_York")).owner;
        auto req=capture::lessonStart(*a,cfg,session,options.createdUtc,"America/New_York",1,false);practice::Coordinator co;capture::PracticeSession capture(store,co);
        check(capture.start(req,1,now()),"recovery original allocation");pulseUntil(capture,[&]{return capture.phase()==capture::SessionPhase::Ready;});check(capture.takeStart(now()).has_value(),"recovery initial checkpoint acknowledged");
        check(co.progress(progress(co,11025,practice::State::Running)),"synthetic quarter-second running fact");
        const auto cp=capture::makeCheckpoint(co,capture.binding(),100);write(out/"running-checkpoint.json",cp.bytes);confirmed(store.checkpoint(storage::newUuid(),capture.binding().owner,cp.generation,cp.sequence,cp.bytes));
        recoveryBinding={capture.binding().owner,"Attempt",capture.binding().context,{},{},1,100};
    }
    options.create=false;{storage::ProfileStore reopened(options);storage::RecoveryOperation operation(reopened,recoveryBinding,"selected-running-recovery");
        const auto end=now()+6000;while(!operation.poll()){if(now()>end)throw std::runtime_error("Six-second recovery watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}
        check(operation.confirmed()&&operation.plan().has_value(),"actual stopped recovery commits original interrupted facts");const auto envelope=storage::validateEnvelope(operation.plan()->bytes);write(out/"recovered-original.json",envelope.bytes);
        const auto& result=at(envelope.value,"result");
        check(envelope.active==Rational{1,4}&&at(result,"completed_cycles").array().empty()&&at(result,"outcome")==V("interrupted_reopen"),"recovery earns only confirmed quarter-second, no complete cycle");
        check(at(result,"traversals")==V(A{O{{"cycle",n(1)},{"start",q(2)},{"end",q(9,4)},{"status","partial_recovered"}}}),"running recovery closes exact source-origin partial");
    }
    options.path=out/"sealed-recovery"/"profile.sqlite";options.create=true;std::string sealedBytes;
    {storage::ProfileStore store(options);const auto session=confirmed(store.createSession(storage::newUuid(),options.createdUtc,"America/New_York")).owner;
        auto req=capture::lessonStart(*a,cfg,session,options.createdUtc,"America/New_York",1,false);practice::Coordinator co;capture::PracticeSession capture(store,co);
        check(capture.start(req,1,now()),"sealed recovery original allocation");pulseUntil(capture,[&]{return capture.phase()==capture::SessionPhase::Ready;});check(capture.takeStart(now()).has_value(),"sealed recovery initial checkpoint acknowledged");
        check(co.progress(progress(co,11025,practice::State::Ended)),"synthetic stopped partial before original seal");
        const auto envelope=capture::makeEnvelope(co,capture.binding(),nullptr,capture::Outcome::Stop);sealedBytes=envelope.bytes;co.seal(envelope.owner,envelope.bytes);
        const auto cp=capture::makeCheckpoint(co,capture.binding(),100,nullptr,capture::Outcome::Stop,&envelope,true);write(out/"sealed-checkpoint.json",cp.bytes);
        confirmed(store.checkpoint(storage::newUuid(),capture.binding().owner,cp.generation,cp.sequence,cp.bytes));
        recoveryBinding={capture.binding().owner,"Attempt",capture.binding().context,{},envelope.bytes,1,100};
    }
    options.create=false;{storage::ProfileStore reopened(options);storage::RecoveryOperation operation(reopened,recoveryBinding,"selected-sealed-recovery");
        const auto end=now()+6000;while(!operation.poll()){if(now()>end)throw std::runtime_error("Six-second sealed recovery watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}
        check(operation.confirmed()&&operation.plan().has_value()&&operation.plan()->bytes==sealedBytes,"save-uncertain checkpoint recovery uses exact original bytes without second source offset");
        write(out/"sealed-recovered-original.json",operation.plan()->bytes);
    }
    auto stop=original(*a,cfg,true);platform::PracticePlayback stopped;check(stopped.prepareLesson(*a,a->referenceConfiguration(stop.owner(),1,cfg.rate,cfg.bpm),stop,2),"section boundary Stop preparation");
    const auto data=drive(stopped,stop,44100,true);stop.stoppedAcknowledged(stop.owner(),practice::State::Ended,1000);
    check(stop.completedCycles()==1&&stop.activeFrames()==44100&&data.pulseFrames==std::vector<std::uint64_t>{0},"boundary Stop excludes following attack and retains exactly one cycle");
    write(out/"cases.json",storage::canonical(cases));write(out/"summary.json",storage::canonical(O{{"status","PASS"},{"checks",n(checks)},{"projection_cases",n(20)},{"native",false},{"human_review",false},{"classification","actual provider/TAB/Store and synthetic acknowledgments"}}));
    std::cout<<"PASS "<<checks<<" section checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
