// Real Coordinator/TAB/Capture/Store consumers; all submission inputs here are synthetic.
#define main retained_pulse_campaign_main
#include "m1_lesson_pulse_tests.cpp"
#undef main
#include "core/TabPlayback.hpp"

namespace {
std::int64_t integer(const V& v){std::int64_t x{};if(!v.integer(x))throw std::invalid_argument("Expected oracle integer");return x;}
std::uint64_t u(const V& v){const auto x=integer(v);if(x<0)throw std::invalid_argument("Negative oracle frame");return static_cast<std::uint64_t>(x);}
practice::Progress observed(const practice::Coordinator& c,std::uint64_t through,std::uint64_t intro,
        std::uint64_t complete,std::uint64_t anchor,practice::State state){
    practice::Progress p;p.owner=c.owner();p.sequence=c.generations().back().sequence+1;
    p.clientAcceptedThrough=p.scheduledThrough=p.uncertainThrough=through;
    p.activeFrames=through>intro?through-intro:0;p.completedCycles=complete;p.cursorFrames=through>anchor?through-anchor:0;
    p.partial=p.cursorFrames!=0;p.state=state;p.terminal=state==practice::State::Paused||state==practice::State::Ended||state==practice::State::Error;
    p.fault=state==practice::State::Error;p.requestedStopNs=p.terminal?1000:0;return p;
}
void finishSave(capture::SaveOperation& save,std::int64_t floor=0){
    const auto end=now()+6000;while(!save.poll(std::max(now(),floor))){if(now()>end)throw std::runtime_error("Six-second save watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}
}
}
int main(int argc,char** argv){try{
    if(argc!=4)throw std::invalid_argument("Expected accepted bundle, new absolute evidence directory, independent preflight oracle");
    const std::filesystem::path out(argv[2]);if(!out.is_absolute()||std::filesystem::exists(out))throw std::invalid_argument("Use new absolute evidence directory");
    std::filesystem::create_directories(out);std::filesystem::permissions(out,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);checkTrace.open(out/"checks.tsv");
    const auto oracleBytes=content::readBounded(argv[3],1024*1024);const auto oracle=json::parse(oracleBytes);write(out/"oracle-used.json",oracleBytes);
    const auto catalog=lesson::Catalog::load(argv[1]);const auto a=catalog->admitCell("fg:item:000002","fg:variant:000006",3);
    auto doc=std::make_shared<const tab::Document>(a->model());A traces;std::uint64_t caseNumber{};
    for(const auto& test:at(oracle,"cases").array()){
        ++caseNumber;auto cfg=a->practiceConfiguration(static_cast<std::uint32_t>(u(at(test,"rate"))),static_cast<std::uint16_t>(u(at(test,"tempos_per_cycle").array().front())));
        const auto& cycles=at(test,"cycles").array();cfg.targetCycles=cycles.size();const auto intro=u(at(test,"intro_frames"));
        if(intro){cfg.countIn=practice::CountIn::AuthoredBar;cfg.meter={{3,4}};}
        practice::Coordinator c;c.begin(owner(),practice::Kind::Attempt,"synthetic-tempo-consumer-case-"+std::to_string(caseNumber),cfg);
        practice::Timeline full=c.timeline(c.owner());for(std::size_t i=1;i<cycles.size();++i)if(at(cycles[i],"bpm")!=at(cycles[i-1],"bpm"))full=full.changed(i,static_cast<std::uint16_t>(u(at(cycles[i],"bpm"))));
        check(full.frame(0)==intro&&full.frame(cycles.size())==u(at(test,"target_end")),"exact independent rational intro and target");
        practice::Timeline accepted=c.timeline(c.owner());tab::Playback tab;tab.bind(doc,a->model(),c);A prefixes;
        if(intro){auto p=observed(c,intro-1,intro,0,intro,practice::State::CountIn);check(c.progress(p)&&tab.update(c)&&!tab.position().hasMusicalSample,"synthetic count-in has no active musical sample");}
        for(std::size_t cycle=0;cycle<cycles.size();++cycle){const auto& expected=cycles[cycle];
            const auto anchor=full.coordinate(cycle);const auto& exact=at(expected,"ideal_anchor_frames").array();
            check(anchor.exact()==std::array<std::string,2>{std::to_string(u(exact[0])),std::to_string(u(exact[1]))},"rational anchor accumulated before rounding");
            check(full.frame(cycle)==u(at(expected,"rounded_start"))&&full.frame(cycle+1)==u(at(expected,"rounded_end")),"independent rounded cycle endpoints");
            for(std::size_t note=0;note<4;++note){const auto start=u(at(expected,"event_onsets").array()[note]),end=u(at(expected,"event_ends").array()[note]);
                check(full.frame(cycle,Rational{static_cast<std::int64_t>(note),4})==start&&full.frame(cycle,Rational{static_cast<std::int64_t>(note+1),4})==end,"independent half-open source event frames");
                for(const auto through:{start+1,end}){
                    while(accepted.points().size()<full.points().size()){
                        const auto& point=full.points()[accepted.points().size()];if(full.frame(point.cycle)>=through)break;accepted=accepted.changed(point.cycle,point.bpm);
                    }
                    std::uint64_t complete{};for(const auto& candidate:cycles)if(u(at(candidate,"rounded_end"))<=through)++complete;
                    const auto cycleAnchor=complete?u(at(cycles[static_cast<std::size_t>(complete-1)],"rounded_end")):intro;
                    const auto state=through==u(at(test,"target_end"))?practice::State::Ended:practice::State::Running;
                    auto p=observed(c,through,intro,complete,cycleAnchor,state);
                    check(c.progress(p,accepted)&&tab.update(c),"actual Coordinator/TAB accept scripted confirmed prefix");
                    check(tab.position().cycle==cycle&&tab.position().sample==through-1&&tab.position().events==std::vector<std::string>{a->model()->source().events[note].id},"TAB original eventID follows acceptedThrough-minus-one");
                    check(c.currentTempo()==u(at(expected,"bpm"))&&c.configuration().bpm==cfg.bpm,"actual accepted tempo differs from immutable selected tempo only as evidenced");
                    prefixes.push_back(O{{"through",n(static_cast<std::int64_t>(through))},{"completed",n(static_cast<std::int64_t>(complete))},{"bpm",n(c.currentTempo())},{"event",a->model()->source().events[note].id}});
                }
            }
        }
        check(c.activeFrames()==u(at(test,"total_active_frames"))&&c.completedCycles()==cycles.size(),"no count-in time or duplicated completed cycles");
        traces.push_back(O{{"case",n(static_cast<std::int64_t>(caseNumber))},{"prefixes",prefixes}});
    }
    write(out/"oracle-traces.json",storage::canonical(traces));
    auto cfg=a->practiceConfiguration(44100,60);cfg.targetCycles=4;auto c=original(*a,cfg,false);const auto base=c.timeline(c.owner());
    auto p=observed(c,1000,0,0,0,practice::State::Running);check(c.progress(p),"initial fixed prefix accepted");
    auto future=base.changed(1,75);p=observed(c,2000,0,0,0,practice::State::Running);
    refuses([&]{c.progress(p,future);},"future tempo boundary cannot enter accepted history");
    check(c.activeFrames()==1000&&c.timeline(c.owner()).points().size()==1,"failed future validation leaves original map/progress unchanged");
    p=observed(c,44100,0,1,44100,practice::State::Running);refuses([&]{c.progress(p,future);},"boundary without following accepted sample remains old tempo");
    check(c.progress(p)&&c.currentTempo()==60,"scalar exact endpoint keeps old tempo");
    p=observed(c,44101,0,1,44100,practice::State::Running);check(c.progress(p,future)&&c.currentTempo()==75,"change exactly at previous accepted endpoint becomes real only with next sample");
    check(!c.progress(p,base)&&c.currentTempo()==75,"duplicate sequence cannot erase accepted map");
    p=observed(c,45000,0,1,44100,practice::State::Running);check(c.progress(p)&&c.currentTempo()==75,"legacy scalar overload reuses current accepted map");
    p=observed(c,46000,0,1,44100,practice::State::Running);refuses([&]{c.progress(p,base.changed(1,74));},"conflicting accepted tempo cannot rewrite prefix");
    auto wrong=base.spec();++wrong.owner.epoch;refuses([&]{c.progress(p,practice::Timeline(wrong));},"foreign map epoch refused");
    wrong=base.spec();wrong.rate=48000;refuses([&]{c.progress(p,practice::Timeline(wrong));},"changed map sample rate refused");
    auto foreign=p;++foreign.owner.generation;check(!c.progress(foreign,future)&&c.activeFrames()==45000,"foreign progress cannot change original");
    auto prior=original(*a,cfg,false);auto old=observed(prior,45000,0,1,44100,practice::State::Running);check(prior.progress(old),"constant prefix already includes following cycle");
    old=observed(prior,46000,0,1,44100,practice::State::Running);refuses([&]{prior.progress(old,future);},"late tempo cannot relabel already accepted next-cycle sample");
    for(auto invalid:{0U,4U,9U})refuses([&]{base.changed(invalid,75);},"unsupported initial/terminal/outside change boundary refused");
    for(auto invalid:{0U,19U,301U,65535U})refuses([&]{base.changed(1,static_cast<std::uint16_t>(invalid));},"unsupported tempo range refused");
    refuses([&]{base.changed(1,60);},"redundant map change refused; manual intent remains separate policy obligation");
    refuses([&]{future.changed(1,80);},"duplicate change cycle refused");
    auto huge=base.spec();huge.span=Rational{INT64_MAX};refuses([&]{practice::Timeline invalid(huge);},"arithmetic overflow rejects without wrap");
    auto rampSpec=base.spec();rampSpec.initialBpm=137;rampSpec.cycles=32;auto ramp=practice::Timeline(rampSpec);
    for(std::uint64_t cycle=1;cycle<32;++cycle)ramp=ramp.changed(cycle,static_cast<std::uint16_t>(137+cycle*2));
    check(ramp.points().size()==32&&ramp.frame(32)>ramp.frame(31),"full accepted137-to199 32pass map now exactly representable");
    write(out/"full-ramp-anchor.json",storage::canonical(A{ramp.coordinate(32).exact()[0],ramp.coordinate(32).exact()[1]}));
    // Synthetic authored3/4 count-in; this is not a source requirement for the admitted cell.
    auto counted=cfg;counted.targetCycles=3;counted.countIn=practice::CountIn::AuthoredBar;counted.meter={{3,4}};
    practice::Coordinator countedOwner;countedOwner.begin(owner(),practice::Kind::Attempt,"synthetic-counted-tempo-replay",counted);
    auto countedMap=countedOwner.timeline(countedOwner.owner()).changed(1,75);
    auto initialPartial=observed(countedOwner,185220,132300,1,176400,practice::State::Paused);
    check(countedOwner.progress(initialPartial,countedMap)&&countedOwner.activeFrames()==52920,"changed-tempo partial excludes actual synthetic3-quarter initial count-in");
    const auto oldCounted=countedOwner.owner();countedOwner.resume();
    check(countedOwner.currentTempo()==75&&countedOwner.configuration().bpm==60&&countedOwner.timeline(countedOwner.owner()).frame(0)==105840,"fresh resumed count-in uses current75 while selected60 stays immutable");
    auto delayed=initialPartial;++delayed.sequence;delayed.scheduledThrough+=256;
    check(!countedOwner.progress(delayed,countedMap)&&countedOwner.owner().generation==oldCounted.generation+1&&countedOwner.activeFrames()==52920&&countedOwner.timeline(countedOwner.owner()).points().size()==1,"late old-generation supplied map retains raw audit only and cannot change current tempo or totals");
    check(countedOwner.progress(observed(countedOwner,100,105840,0,105840,practice::State::Paused))&&countedOwner.activeFrames()==52920&&countedOwner.completedCycles()==1,"pause during fresh count-in adds no active time or completed pass");
    countedOwner.resume();check(countedOwner.timeline(countedOwner.owner()).frame(0)==105840&&countedOwner.currentTempo()==75,"another explicit resume repeats the full configured count-in");
    tab::Playback countedTab;countedTab.bind(doc,a->model(),countedOwner);
    check(countedOwner.progress(observed(countedOwner,105840,105840,0,105840,practice::State::Running))&&countedTab.update(countedOwner)&&!countedTab.position().hasMusicalSample,"entire fresh count-in still has no accepted musical sample");
    check(countedOwner.progress(observed(countedOwner,105841,105840,0,105840,practice::State::Running))&&countedTab.update(countedOwner)&&countedTab.position().events==std::vector<std::string>{a->model()->source().events[0].id},"first accepted post-count-in sample maps to original selected cell event");
    // A source-origin partial at75 BPM, then same-original replay at75 with immutable selected60.
    cfg.targetCycles=3;storage::StoreOptions options;options.path=out/"profile.sqlite";options.create=true;options.createdUtc="2026-09-12T15:05:00Z";
    std::atomic<bool> entered{false},lost{true};options.diagnosticHook=[&](const std::string& phase,const std::string& operation){
        if(operation.find("slow.reconcile")!=std::string::npos&&phase=="before_operation"){entered=true;std::this_thread::sleep_for(std::chrono::milliseconds(1100));}
        if(operation.find("slow.commit")!=std::string::npos&&phase=="after_commit"&&lost.exchange(false))throw std::runtime_error("Synthetic lost acknowledgment after actual original commit");
    };V before;
    {storage::ProfileStore store(options);const auto session=confirmed(store.createSession(storage::newUuid(),options.createdUtc,"America/New_York",{},O{{"synthetic_fixture",true}})).owner;
        auto req=capture::lessonStart(*a,cfg,session,options.createdUtc,"America/New_York",1,false);practice::Coordinator co;capture::PracticeSession capture(store,co);
        check(capture.start(req,1,now()),"actual Store original allocation");pulseUntil(capture,[&]{return capture.phase()==capture::SessionPhase::Ready;});check(capture.takeStart(now()).has_value(),"initial durable checkpoint acknowledged before scripted practice");
        const auto initialContext=co.context();auto map=co.timeline(co.owner()).changed(1,75);
        check(co.progress(observed(co,52920,0,1,44100,practice::State::Paused),map),"scripted accepted partial at changed tempo");
        const auto partial=capture::makeCheckpoint(co,capture.binding(),100);write(out/"partial-checkpoint.json",partial.bytes);
        const auto snap=at(json::parse(partial.bytes),"practice_snapshot");check(at(snap,"cursor")==q(9,4)&&at(snap,"active")==q(6,5)&&at(snap,"tempo")==q(75)&&at(snap,"selected_tempo")==q(60),"checkpoint source cursor and selected/current tempo stay distinct");
        const auto oldOwner=co.owner();co.resume();check(co.currentTempo()==75&&co.configuration().bpm==60&&co.context()==initialContext&&co.owner().id==oldOwner.id,"resume keeps original selected60, starts actual75");
        check(co.timeline(co.owner()).points().size()==1&&co.timeline(co.owner()).spec().cycles==2,"resumed map has two remaining unique passes and no fabricated transition");
        tab::Playback tab;tab.bind(doc,a->model(),co);
        check(co.progress(observed(co,1,0,0,0,practice::State::Running))&&tab.update(co)&&tab.position().events==std::vector<std::string>{a->model()->source().events[0].id},"resumed TAB starts first original cell event at current tempo");
        check(co.progress(observed(co,70560,0,2,70560,practice::State::Ended))&&tab.update(co),"two resumed75BPM cycles complete from accepted endpoints");
        auto expected=capture::makeEnvelope(co,capture.binding(),nullptr,capture::Outcome::Natural);const auto& result=at(expected.value,"result");
        const auto& traversals=at(result,"traversals").array();check(expected.active==Rational{14,5}&&at(result,"completed_cycles")==V(A{n(1),n(2),n(3)})&&traversals.size()==4,"actual2.8seconds with three unique completed passes plus retained partial");
        check(traversals[1]==V(O{{"cycle",n(2)},{"start",q(2)},{"end",q(9,4)},{"status","partial_interrupted"}}),"partial source cycle2 remains partial through replay");
        const V segments=A{O{{"tempo",q(60)},{"start_at",q(0)},{"end_at",q(1)},{"confirmed_duration",q(1)}},O{{"tempo",q(75)},{"start_at",q(1)},{"end_at",q(6,5)},{"confirmed_duration",q(1,5)}},O{{"tempo",q(75)},{"start_at",q(6,5)},{"end_at",q(14,5)},{"confirmed_duration",q(8,5)}}};
        check(at(result,"tempo_segments")==segments&&at(result,"selected_tempo")==q(60)&&at(result,"assessment").null(),"exact confirmed segments and immutable selected tempo; no inferred assessment");
        check(at(result,"interruptions").array().size()==2&&at(at(at(result,"interruptions").array()[1],"tempo_timeline"),"points").array().size()==1,"resumed initial75 map retained despite no new transition");
        const auto started=now();capture::SaveOperation save(store,co,capture.binding(),nullptr,capture::Outcome::Natural,"slow",started);
        const auto gate=now()+6000;while(!entered){if(now()>gate)throw std::runtime_error("Save hook entry watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}
        check(!save.poll(started+1001)&&save.feedback().code=="ACK_TIMEOUT"&&!save.release(co),"actual delayed reconciliation retains original timeout without release");
        finishSave(save,started+1001);check(!save.saved()&&save.feedback().code=="ACKNOWLEDGMENT_LOST"&&co.pending(),"lost commit receipt retains unresolved exact original");
        check(save.original().bytes==expected.bytes,"save sealed exactly the precomputed original without reinterpreting tempo");write(out/"original.json",save.original().bytes);
        refuses([&]{co.begin(owner(),practice::Kind::Attempt,"new",cfg);},"Again cannot replace an unresolved original");
        capture::SaveOperation retry(store,co,save.original(),"retry",now());finishSave(retry);check(retry.saved()&&retry.original().bytes==expected.bytes&&retry.release(co),"explicit original-key reconciliation confirms identical bytes once");
        const auto snapshot=confirmed(store.snapshot(storage::newUuid()));before=snapshot.data;write(out/"before.json",storage::canonical(before));const auto adapted=progression::adaptSnapshot(snapshot);
        check(adapted.records.size()==1&&!adapted.records[0].complete&&adapted.records[0].condition.null()&&adapted.records[0].assessment.null(),"mixed scheduled passes do not imply PB/mastery/source performance");
    }
    options.create=false;options.diagnosticHook={};{storage::ProfileStore reopened(options);auto after=confirmed(reopened.snapshot(storage::newUuid()));check(after.data==before,"ordinary reopen retains exact original and segments");write(out/"after.json",storage::canonical(after.data));}
    for(const bool sealed:{false,true}){
        options.path=out/(sealed?"sealed-recovery":"running-recovery")/"profile.sqlite";options.create=true;storage::RecoveryBinding binding;std::string sealedBytes;V originalSegments;
        {storage::ProfileStore store(options);const auto session=confirmed(store.createSession(storage::newUuid(),options.createdUtc,"America/New_York")).owner;
            auto req=capture::lessonStart(*a,cfg,session,options.createdUtc,"America/New_York",1,false);practice::Coordinator co;capture::PracticeSession capture(store,co);
            check(capture.start(req,1,now()),"recovery original allocation");pulseUntil(capture,[&]{return capture.phase()==capture::SessionPhase::Ready;});check(capture.takeStart(now()).has_value(),"recovery initial checkpoint acknowledged");
            auto map=co.timeline(co.owner()).changed(1,75);check(co.progress(observed(co,52920,0,1,44100,sealed?practice::State::Ended:practice::State::Running),map),"recovery retains actual scripted changed-tempo prefix");
            std::optional<storage::Envelope> envelope;if(sealed){envelope=capture::makeEnvelope(co,capture.binding(),nullptr,capture::Outcome::Stop);sealedBytes=envelope->bytes;co.seal(envelope->owner,envelope->bytes);}
            const auto checkpoint=capture::makeCheckpoint(co,capture.binding(),100,nullptr,sealed?std::optional<capture::Outcome>{capture::Outcome::Stop}:std::nullopt,envelope?&*envelope:nullptr,sealed);
            write(out/(sealed?"sealed-checkpoint.json":"running-checkpoint.json"),checkpoint.bytes);originalSegments=at(at(json::parse(checkpoint.bytes),"practice_snapshot"),"segments");
            confirmed(store.checkpoint(storage::newUuid(),capture.binding().owner,checkpoint.generation,checkpoint.sequence,checkpoint.bytes));binding={capture.binding().owner,"Attempt",capture.binding().context,{},sealed?std::optional<std::string>{sealedBytes}:std::nullopt,1,100};
        }
        options.create=false;{storage::ProfileStore reopened(options);storage::RecoveryOperation recovery(reopened,binding,sealed?"sealed":"running");const auto end=now()+6000;
            while(!recovery.poll()){if(now()>end)throw std::runtime_error("Six-second recovery watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}
            check(recovery.confirmed()&&recovery.plan().has_value(),"actual stopped recovery confirms original once");const auto envelope=storage::validateEnvelope(recovery.plan()->bytes);const auto& result=at(envelope.value,"result");
            check(envelope.active==Rational{6,5}&&at(result,"tempo_segments")==originalSegments&&at(result,"selected_tempo")==q(60),"recovery preserves exact changed segments and initial selected tempo");
            if(sealed)check(envelope.bytes==sealedBytes,"sealed recovery preserves bytes exactly");else check(at(at(result,"traversals").array().back(),"end")==q(9,4)&&at(result,"outcome")==V("interrupted_reopen"),"running recovery preserves source-origin partial and stopped outcome");
            write(out/(sealed?"sealed-recovered.json":"running-recovered.json"),envelope.bytes);
        }
    }
    // New exact large-denominator anchors enter the actual unchanged Store API.
    options.path=out/"wide-recovery"/"profile.sqlite";options.create=true;options.diagnosticHook={};
    V wideBefore;std::string wideBytes;
    {storage::ProfileStore store(options);const auto session=confirmed(store.createSession(storage::newUuid(),options.createdUtc,"America/New_York")).owner;
        auto wideCfg=a->practiceConfiguration(48000,137);wideCfg.targetCycles=32;
        auto req=capture::lessonStart(*a,wideCfg,session,options.createdUtc,"America/New_York",1,false);practice::Coordinator co;capture::PracticeSession capture(store,co);
        check(capture.start(req,1,now()),"wide-anchor actual Store original allocated");pulseUntil(capture,[&]{return capture.phase()==capture::SessionPhase::Ready;});check(capture.takeStart(now()).has_value(),"wide initial checkpoint durable");
        auto map=co.timeline(co.owner());for(std::uint64_t cycle=1;cycle<32;++cycle)map=map.changed(cycle,static_cast<std::uint16_t>(137+cycle*2));
        check(co.progress(observed(co,map.frame(32),0,32,map.frame(32),practice::State::Ended),map),"all32 synthetic confirmed cycles accepted with wide map");
        const auto envelope=capture::makeEnvelope(co,capture.binding(),nullptr,capture::Outcome::Stop);wideBytes=envelope.bytes;const auto& result=at(envelope.value,"result");
        const auto& pointRecords=at(at(at(result,"interruptions").array().front(),"tempo_timeline"),"points").array();check(pointRecords.size()==32,"wide Capture retains every applied tempo point");
        for(std::size_t j=0;j<pointRecords.size();++j){const auto exact=map.points()[j].anchor.exact();check(at(pointRecords[j],"anchor_samples")==V(A{exact[0],exact[1]}),"wide decimal anchors retain full exact value in original");}
        check(map.points().back().anchor.exact()[0].size()>20&&at(result,"tempo_segments").array().size()==32,"large anchor and positive segments are retained without small integer cast");
        write(out/"wide-original.json",wideBytes);co.seal(envelope.owner,envelope.bytes);capture::SaveOperation save(store,co,envelope,"wide.commit",now());finishSave(save);check(save.saved()&&save.original().bytes==wideBytes,"wide original committed unchanged");
        wideBefore=confirmed(store.snapshot(storage::newUuid())).data;write(out/"wide-before.json",storage::canonical(wideBefore));
    }
    options.create=false;{storage::ProfileStore reopened(options);const auto after=confirmed(reopened.snapshot(storage::newUuid()));check(after.data==wideBefore,"wide original and anchors survive actual ordinary reopen");write(out/"wide-after.json",storage::canonical(after.data));}
    write(out/"summary.json",storage::canonical(O{{"status","PASS"},{"checks",n(checks)},{"oracle_cases",n(static_cast<std::int64_t>(caseNumber))},{"native",false},{"human_review",false},{"classification","actual Coordinator/TAB/Capture/Store consumers with synthetic submission evidence; provider controls not integrated"}}));
    std::cout<<"PASS "<<checks<<" timeline checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
