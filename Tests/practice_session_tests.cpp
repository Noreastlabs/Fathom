#include "practice_capture_fixtures.hpp"
#include "progression/ProgressionAdapter.hpp"
#include <atomic>
#include <iostream>
using namespace capture_fixture;
namespace fs=std::filesystem;
namespace {
int checks=0,failures=0;V::Array results;
void check(bool b,const char* name){++checks;results.emplace_back(O{{"name",name},{"pass",b}});if(!b){++failures;std::cerr<<"FAIL "<<name<<'\n';}}
template<class F>void refuses(F f,const char* name){try{f();check(false,name);}catch(const std::exception&){check(true,name);}}
void ready(capture::PracticeSession& s){until(s,[&]{return s.phase()==capture::SessionPhase::Ready;});}
void saved(capture::PracticeSession& s){until(s,[&]{return s.phase()==capture::SessionPhase::Saved;});}
void stoppedReview(capture::PracticeSession& s,practice::Coordinator& c,std::uint64_t frames=24000){c.progress(progress(c,frames,practice::State::Ended));s.poll(now(),"2026-09-08T04:00:30Z");check(s.phase()==capture::SessionPhase::Review,"terminal facts enter explicit review");}
}
int main(int argc,char** argv){try{
    if(argc==3&&std::string(argv[2])=="--prior-owner-allocation-refusal-regression"){
        const fs::path out=fs::absolute(argv[1]).lexically_normal();if(out.parent_path()!=fs::path("/private/tmp")||fs::exists(out))throw std::runtime_error("Fresh private prior-owner fixture required");fs::create_directory(out);fs::permissions(out,fs::perms::owner_all);
        for(bool freeplay:{false,true}){
            const auto dir=out/(freeplay?"prior-freeplay":"prior-attempt");fs::create_directory(dir);fs::permissions(dir,fs::perms::owner_all);
            storage::StoreOptions opt;opt.path=dir/"profile.sqlite";opt.create=true;opt.createdUtc="2026-10-10T00:00:00Z";storage::ProfileStore store(opt);
            const auto group=confirmed(store.createSession(storage::newUuid(),opt.createdUtc,"Etc/UTC")).owner;
            practice::Coordinator oldCoordinator;capture::PracticeSession old(store,oldCoordinator);check(old.start(request(group,freeplay),1,now()),"original real owner allocated");ready(old);const auto owner=old.binding().owner;
            const auto before=at(confirmed(store.snapshot(storage::newUuid())).data,"authoritative");
            auto desired=request(group);const auto op=storage::newUuid();const auto refused=store.allocate(op,desired.binding.kind,desired.binding.context,desired.binding.practiceUtc).get();
            check(refused.status==storage::Status::DefiniteFailure&&refused.operation==op&&refused.owner.empty()&&refused.code=="ALLOCATION_REFUSED_PRIOR_ACTIVITY"&&at(refused.data,"version")==V("allocation-refusal.1")&&at(refused.data,"new_allocation")==V("not_admitted")&&at(refused.data,"rollback_confirmed")==V(true)&&at(refused.data,"blocking_owner")==V(owner),"typed refusal proves only new allocation absent and binds original blocking owner");
            practice::Coordinator nextCoordinator;capture::PracticeSession next(store,nextCoordinator);check(next.start(request(group),1,now()),"new explicit capture submits one actual refused allocation");until(next,[&]{return next.phase()==capture::SessionPhase::Failed;});
            check(next.binding().owner.empty()&&!next.takeStart(now())&&nextCoordinator.activeFrames()==0&&!next.original()&&next.canLeave(true)&&!next.canLeave(false),"definitely unallocated new capture can return only after output clear without sound or Saved");
            next.requestExitDiscard();check(next.canLeaveForExit(true,now()),"explicit exit releases only definitely refused new capture");
            check(at(confirmed(store.snapshot(storage::newUuid())).data,"authoritative")==before,"all fourteen original authority tables exactly unchanged by refused new allocation and exit");
            const auto recovery=confirmed(store.recoveryState(storage::newUuid(),owner));check(recovery.owner==owner&&at(recovery.data,"state")==V("checkpoint"),"prior original owner remains recoverable and unfinalized");
        }
        const auto dir=out/"lost-allocation-ack";fs::create_directory(dir);fs::permissions(dir,fs::perms::owner_all);storage::StoreOptions opt;opt.path=dir/"profile.sqlite";opt.create=true;opt.createdUtc="2026-10-10T00:00:00Z";
        opt.diagnosticHook=[](const std::string& phase,const std::string& op){if(phase=="after_commit"&&op.size()>=9&&op.compare(op.size()-9,9,".allocate")==0)throw std::runtime_error("Synthetic allocation ACK loss");};storage::ProfileStore store(opt);const auto group=confirmed(store.createSession(storage::newUuid(),opt.createdUtc,"Etc/UTC")).owner;practice::Coordinator c;capture::PracticeSession s(store,c);s.start(request(group),1,now());until(s,[&]{return s.phase()==capture::SessionPhase::AllocationUnknown;});
        check(!s.binding().owner.empty()&&!s.canLeave(true)&&!s.takeStart(now()),"ownerful lost allocation acknowledgment remains held and cannot start");s.requestExitDiscard();check(!s.canLeaveForExit(true,now()),"Discard cannot waive admitted unknown allocation ownership");
        write(out/"summary.json",storage::canonical(O{{"checks",n(checks)},{"failures",n(failures)}}));return failures?2:0;
    }
    if(argc==3&&std::string(argv[2])=="--exit-discard-regression"){
        const fs::path out=fs::absolute(argv[1]).lexically_normal();
        if(out.parent_path()!=fs::path("/private/tmp")||fs::exists(out))throw std::runtime_error("Fresh private synthetic exit fixture required");
        fs::create_directory(out);fs::permissions(out,fs::perms::owner_all,fs::perm_options::replace);
        auto privateProfile=[&](const char* label){const auto dir=out/label;if(!fs::create_directory(dir))throw std::runtime_error("Fresh fixture subdirectory required");fs::permissions(dir,fs::perms::owner_all,fs::perm_options::replace);return dir/"profile.sqlite";};
        storage::StoreOptions opt;opt.path=out/"profile.sqlite";opt.create=true;opt.createdUtc="2026-10-10T00:00:00Z";
        std::string owner;V context;V before;
        {
            storage::ProfileStore store(opt);const auto group=confirmed(store.createSession(storage::newUuid(),opt.createdUtc,"Etc/UTC")).owner;
            practice::Coordinator c;capture::PracticeSession session(store,c);
            check(session.start(request(group),1,now()),"exit fixture allocates actual original");ready(session);
            owner=session.binding().owner;context=session.binding().context;
            check(!session.canLeaveForExit(true,now()),"unresolved original cannot leave without explicit Discard");
            const auto baseline=confirmed(store.snapshot(storage::newUuid())).data;
            check(!session.canLeave(true),"Cancel/no choice retains navigation ownership");
            check(confirmed(store.snapshot(storage::newUuid())).data==baseline,"Cancel/no choice changes no authority");
            session.requestExitDiscard();session.requestExitDiscard();
            check(!session.canLeaveForExit(false,now()),"Discard waits output ownership clearance");
            until(session,[&]{return session.canLeaveForExit(true,now());});
            check(!session.canLeave(true)&&!session.again(true)&&!session.takeStart(now()),"exit-only Discard cannot navigate, rearm or Start");
            before=confirmed(store.snapshot(storage::newUuid())).data;
            check(before==baseline,"repeated Discard preserves exact acknowledged authority");
            check(!session.original(),"Discard never fabricates finalized assessment");
            write(out/"discard-authority.json",storage::canonical(before));
        }
        opt.create=false;
        {
            storage::ProfileStore store(opt);check(confirmed(store.snapshot(storage::newUuid())).data==before,"normal reopen preserves discarded pending original exactly");
            practice::Coordinator c;capture::PracticeSession session(store,c);
            storage::RecoveryBinding binding{owner,"Attempt",context,nullptr,{},0,0};
            check(session.recover(binding),"discarded original supports stopped same-owner recovery");saved(session);
            check(session.original()&&session.original()->owner==owner&&!session.takeStart(now()),"recovery finalizes original owner without autoplay");
            check(at(at(session.original()->value,"result"),"outcome")==V("interrupted_reopen"),"Discard reopen remains truthful interrupted recovery");
        }
        {
            storage::StoreOptions unknown;unknown.path=privateProfile("allocation-unknown");unknown.create=true;unknown.createdUtc="2026-10-10T00:00:00Z";
            std::atomic<bool> inject{true};unknown.diagnosticHook=[&](const std::string& phase,const std::string& op){if(op.find(".allocate")!=std::string::npos&&phase=="after_commit"&&inject.exchange(false))throw std::runtime_error("Controlled allocation lost ACK");};
            storage::ProfileStore store(unknown);const auto group=confirmed(store.createSession(storage::newUuid(),unknown.createdUtc,"Etc/UTC")).owner;practice::Coordinator c;capture::PracticeSession session(store,c);
            check(session.start(request(group),1,now()),"unknown allocation retains actual operation");until(session,[&]{return session.phase()==capture::SessionPhase::AllocationUnknown;});session.requestExitDiscard();
            check(!session.canLeaveForExit(true,now())&&!session.canLeave(true)&&!session.takeStart(now()),"Discard cannot bypass unknown allocation or autoplay");
            check(session.inspectAllocation(now()),"explicit same-owner allocation reconciliation remains available");until(session,[&]{return session.phase()==capture::SessionPhase::Review;});until(session,[&]{return session.canLeaveForExit(true,now());});
            const auto authority=at(confirmed(store.snapshot(storage::newUuid())).data,"authoritative");check(at(authority,"identity").array().size()==1&&at(authority,"finalized").array().empty(),"reconciled Discard retains one pending original without finalization");
        }
        {
            storage::StoreOptions audit; audit.path=privateProfile("audit-discard");audit.create=true;audit.createdUtc="2026-10-10T00:00:00Z";
            std::atomic<bool> inject{true};audit.diagnosticHook=[&](const std::string& phase,const std::string& op){if(op.find(".late")!=std::string::npos&&phase=="before_operation"&&inject.exchange(false))throw std::runtime_error("Controlled late audit refusal");};
            storage::ProfileStore store(audit);const auto group=confirmed(store.createSession(storage::newUuid(),audit.createdUtc,"Etc/UTC")).owner;practice::Coordinator c;capture::PracticeSession session(store,c);
            session.start(request(group),1,now());ready(session);session.takeStart(now());auto late=progress(c,48000,practice::State::Ended);c.progress(late);session.poll(now(),"2026-09-08T04:00:30Z");session.save(nullptr,capture::Outcome::Natural,now());saved(session);const auto bytes=session.original()->bytes;
            late.sequence=2;check(!c.progress(late),"post-seal progress is retained audit, not new performance");session.poll(now(),"2026-09-08T04:00:30Z");
            session.requestExitDiscard();check(!session.canLeaveForExit(true,now()),"admitted audit future must drain before Discard exit");
            until(session,[&]{return !inject.load()&&session.feedback().status!=storage::Status::Confirmed;});
            session.requestExitDiscard();
            check(!session.canLeaveForExit(true,now()),"failed accepted audit receipt retains Discard ownership");
            session.retryExitDiscard(now());check(!session.canLeaveForExit(true,now()),"explicit audit retry retains admitted future until actual receipt");until(session,[&]{return session.canLeaveForExit(true,now());});
            check(session.phase()==capture::SessionPhase::Saved,"audit retry preserves already Saved original phase");
            check(session.original()->bytes==bytes,"audit retry preserves immutable captured result");const auto authority=at(confirmed(store.snapshot(storage::newUuid())).data,"authoritative");
            check(at(authority,"finalized").array().size()==1&&at(authority,"late_evidence").array().size()==1,"late audit retry admits one audit fact without duplicate original");
        }
        {
            storage::StoreOptions opt;opt.path=privateProfile("volatile-discard");opt.create=true;opt.createdUtc="2026-10-10T00:00:00Z";
            storage::ProfileStore store(opt);const auto group=confirmed(store.createSession(storage::newUuid(),opt.createdUtc,"Etc/UTC")).owner;practice::Coordinator c;capture::PracticeSession session(store,c);session.start(request(group),1,now());ready(session);session.takeStart(now());
            const auto before=confirmed(store.snapshot(storage::newUuid())).data;
            const auto activeProgress=progress(c,24000,practice::State::Running);
            check(activeProgress.activeFrames==8000&&activeProgress.cursorFrames==8000&&activeProgress.completedCycles==0&&activeProgress.partial,"synthetic progress is one active second after authored count-in, partial first cycle");
            check(c.progress(activeProgress),"actual active progress creates new volatile facts");session.poll(now(),"2026-09-08T04:00:30Z");
            const auto state=session.checkpointState(now());check(session.latestCheckpoint()&&state.acknowledged&&session.latestCheckpoint()->bytes!=state.acknowledged->bytes&&!state.inFlight,"active latest differs from durable checkpoint and is not admitted");
            session.requestExitDiscard();check(!session.canLeaveForExit(false,now()),"volatile Discard still waits output clearance");until(session,[&]{return session.canLeaveForExit(true,now());});
            check(confirmed(store.snapshot(storage::newUuid())).data==before,"volatile active Discard preserves last durable authority exactly");
            check(!session.canLeave(true)&&!session.again(true)&&!session.original(),"volatile discard grants only exit without saved claim");
        }
        {
            storage::StoreOptions options;options.path=privateProfile("checkpoint-failure");options.create=true;options.createdUtc="2026-10-10T00:00:00Z";std::atomic<bool> fail{false};options.diagnosticHook=[&](const std::string& phase,const std::string& op){if(phase=="before_commit"&&op.find(".checkpoint.")!=std::string::npos&&fail.exchange(false))throw std::runtime_error("Controlled admitted checkpoint refusal");};
            storage::ProfileStore store(options);const auto group=confirmed(store.createSession(storage::newUuid(),options.createdUtc,"Etc/UTC")).owner;practice::Coordinator c;capture::PracticeSession session(store,c);session.start(request(group),1,now());ready(session);session.takeStart(now());fail=true;c.progress(progress(c,24000,practice::State::Ended));session.poll(now(),"2026-09-08T04:00:30Z");
            until(session,[&]{const auto state=session.checkpointState(now());return !fail.load()&&!state.inFlight&&state.lastReply&&state.lastReply->status!=storage::Status::Confirmed;});const auto bytes=session.latestCheckpoint()->bytes;session.requestExitDiscard();
            check(!session.canLeaveForExit(true,now()),"failed admitted checkpoint retains Discard ownership despite future settled");session.retryExitDiscard(now());const auto retryState=session.checkpointState(now());check(retryState.inFlight&&retryState.inFlightSnapshot&&retryState.inFlightSnapshot->bytes==bytes,"ContinueDiscard admits exact original checkpoint retry and retains its future");until(session,[&]{return session.canLeaveForExit(true,now());});
            const auto state=session.checkpointState(now());check(state.acknowledged&&state.acknowledged->bytes==bytes&&!session.original()&&!session.canLeave(true),"exact checkpoint retry grants exit only without finalized credit");
        }
        for(const bool lostAck:{false,true}){
            storage::StoreOptions failure;failure.path=privateProfile(lostAck?"lost-ack":"save-refusal");failure.create=true;failure.createdUtc="2026-10-10T00:00:00Z";
            std::atomic<bool> inject{true};failure.diagnosticHook=[&](const std::string& phase,const std::string& op){if(op.find(".save.commit")!=std::string::npos&&phase==(lostAck?"after_commit":"before_commit")&&inject.exchange(false))throw std::runtime_error("Controlled save boundary refusal");};
            storage::ProfileStore store(failure);const auto group=confirmed(store.createSession(storage::newUuid(),failure.createdUtc,"Etc/UTC")).owner;
            practice::Coordinator c;capture::PracticeSession session(store,c);check(session.start(request(group),1,now()),"failed-save fixture starts original");ready(session);session.takeStart(now());stoppedReview(session,c,48000);
            check(session.save("Developing",capture::Outcome::Natural,now()),"Save seals explicit original assessment");until(session,[&]{return session.phase()==capture::SessionPhase::Failed;});const auto bytes=session.original()->bytes;const auto originalOwner=session.binding().owner;
            session.requestExitDiscard();until(session,[&]{return session.canLeaveForExit(true,now());});
            check(session.phase()==capture::SessionPhase::Failed,"settled failed Save exit retains truthful failure, not Saved");
            check(!session.canLeave(true)&&!session.again(true),"failed Save retains navigation and original identity");
            check(session.original()->bytes==bytes&&session.binding().owner==originalOwner,"Discard retains exact sealed original without rescore");
            const auto authority=at(confirmed(store.snapshot(storage::newUuid())).data,"authoritative");check(at(authority,"finalized").array().size()==(lostAck?1u:0u)&&at(authority,"identity").array().size()==1,"settled Save refusal preserves actual commit boundary without fabrication");
        }
        {
            storage::StoreOptions opt;opt.path=privateProfile("freeplay-discard");opt.create=true;opt.createdUtc="2026-10-10T00:00:00Z";
            storage::ProfileStore store(opt);practice::Coordinator c;capture::PracticeSession session(store,c);check(session.start(request("",true),1,now()),"Freeplay allocates standalone owner");ready(session);const auto baseline=confirmed(store.snapshot(storage::newUuid())).data;session.requestExitDiscard();until(session,[&]{return session.canLeaveForExit(true,now());});
            check(confirmed(store.snapshot(storage::newUuid())).data==baseline&&!session.canLeave(true),"Freeplay exit Discard retains checkpoint without lesson Session or finalization");
        }
        write(out/"checks.json",storage::canonical(O{{"checks",n(checks)},{"failures",n(failures)},{"cases",results}}));return failures?1:0;
    }
    if(argc!=2)throw std::runtime_error("Require explicit new evidence directory");fs::path out=fs::absolute(argv[1]).lexically_normal();
    if(out.string().find("/Results/20260908T034923Z-3.4.1.1.1-r02-evidence/test-data/")==std::string::npos||fs::exists(out))throw std::runtime_error("New bounded evidence directory required");
    fs::create_directories(out);fs::permissions(out,fs::perms::owner_all,fs::perm_options::replace);
    storage::StoreOptions options;options.path=out/"profile.sqlite";options.create=true;options.createdUtc="2026-09-08T04:00:00Z";
    // Actual writer exception/ACK delay injection only; not crash or power-loss proof.
    std::atomic<int> fault{0};
    options.diagnosticHook=[&](const std::string& phase,const std::string& op){
        const int f=fault.load();
        if((f==1||f==2||f==3)&&op.find(".allocate")!=std::string::npos&&phase==(f==3?"after_commit":"before_operation")&&fault.exchange(0)==f){
            if(f==1)throw std::runtime_error("Controlled definite allocation refusal");if(f==2)std::this_thread::sleep_for(std::chrono::milliseconds(1100));if(f==3)throw std::runtime_error("Controlled lost allocation ACK");
        }
        if(f==4&&op.find(".checkpoint.")!=std::string::npos&&phase=="before_operation"&&fault.exchange(0)==4)std::this_thread::sleep_for(std::chrono::milliseconds(1100));
        if((f==5||f==6)&&op.find(".save.commit")!=std::string::npos&&phase==(f==5?"after_commit":"before_commit")&&fault.exchange(0)==f)throw std::runtime_error("Controlled final save failure/ACK loss");
        if(f==7&&op.find(".reopen")!=std::string::npos&&phase=="before_operation"&&fault.exchange(0)==7)throw std::runtime_error("Controlled recovery read failure");
    };
    std::string durableOwner;V durableContext;std::string group;
    {
    storage::ProfileStore store(options);group=confirmed(store.createSession(storage::newUuid(),options.createdUtc,"America/New_York")).owner;
    {
        practice::Coordinator c;capture::PracticeSession s(store,c);auto bad=request(group);bad.binding.context.object().at("configuration").object().at("progression_condition").object()["variant"]="fg:variant:000002";
        refuses([&]{s.start(bad,1,now());},"invalid condition refused before allocation");
        auto snap=confirmed(store.snapshot(storage::newUuid()));check(at(at(snap.data,"authoritative"),"identity").array().empty(),"invalid preflight creates no identity");
        fault=1;check(s.start(request(group),1,now()),"explicit allocation request accepted");until(s,[&]{return s.phase()==capture::SessionPhase::Failed;});
        check(s.binding().owner.empty()&&s.canLeave(true)&&!c.pending(),"proven allocation refusal permits leave without fake owner");
        check(s.retry(now())&&s.phase()==capture::SessionPhase::Idle,"explicit retry rearms proven absent allocation");
        check(!s.start(request(group),1,now()),"duplicate command cannot reallocate");
        check(s.start(request(group),2,now()),"new command starts corrected allocation");check(!s.takeStart(now()),"no sound before initial ACK");
        check(!s.start(request(group),3,now()),"live allocation rejects repeated Start");ready(s);const auto owner=s.takeStart(now());
        check(owner&&owner->id==c.owner().id&&!s.takeStart(now()),"initial ACK releases exactly one original Start");
        stoppedReview(s,c);check(!s.canLeave(true)&&!s.again(true),"unresolved outcome blocks leave and Again");
        check(s.save(nullptr,capture::Outcome::Stop,now()),"explicit absent assessment may save");
        check(s.phase()==capture::SessionPhase::SealedCheckpoint&&!s.again(true),"first Save waits sealed checkpoint not Saved");
        check(!s.save("Clean",capture::Outcome::Stop,now()),"repeated Save cannot change first payload");saved(s);
        check(s.original()&&s.original()->active==Rational{1}&&!c.pending()&&at(at(s.original()->value,"result"),"assessment").null(),"one-second original saved absent assessment stopped");
        check(!s.again(false)&&!s.canLeave(false),"final receipt alone cannot clear output owner");
        until(s,[&]{return s.canLeave(true);});check(s.again(true)&&!c.pending()&&!s.takeStart(now()),"Again rearms only no autoplay");
        write(out/"first-original.json",s.original()->bytes);
    }
    for(int mode:{2,3,4}){
        practice::Coordinator c;capture::PracticeSession s(store,c);fault=mode;check(s.start(request(group),1,now()),"timeout original allocation accepted");
        if(mode==2){s.cancelBeforeSound(111);check(!s.start(request(group),2,now()),"cancel during allocation cannot replace original");}
        until(s,[&]{return s.phase()==capture::SessionPhase::Review||s.phase()==capture::SessionPhase::AllocationUnknown;});
        if(mode==3){check(!s.binding().owner.empty()&&!s.takeStart(now())&&!s.canLeave(true),"lost allocation ACK retains UUID stopped");check(s.inspectAllocation(now()),"explicit inspect same allocation");until(s,[&]{return s.phase()==capture::SessionPhase::Review;});}
        check(!s.takeStart(now())&&c.activeFrames()==0&&c.completedCycles()==0,"cancel or late initial ACK never plays or credits");
        check(s.save(nullptr,capture::Outcome::Stop,now()),"cancelled original has explicit zero outcome");saved(s);until(s,[&]{return s.canLeave(true);});
        check(s.original()->active==Rational{},"zero cancellation saved without fabricated practice");
    }
    {
        practice::Coordinator c;capture::PracticeSession s(store,c);s.start(request(group),1,now());ready(s);s.takeStart(now());
        c.progress(progress(c,24000,practice::State::Paused));s.poll(now(),"2026-09-08T04:00:30Z");c.resume();c.progress(progress(c,32000,practice::State::Ended));
        s.poll(now(),"2026-09-08T04:00:30Z");check(s.save("Clean",capture::Outcome::Stop,now()),"explicit Clean remains self report on partial target");saved(s);
        const auto& r=at(s.original()->value,"result");check(s.original()->active==Rational{3}&&at(r,"completed_cycles").array()==A{n(1)}&&at(r,"traversals").array().size()==2,"interrupted replay3s andonecycle distinct");
        check(at(r,"outcome")==V("stop"),"Stop at boundary remains Stop with completed cycle");write(out/"partial-replay.json",s.original()->bytes);until(s,[&]{return s.canLeave(true);});
    }
    for(int mode:{5,6}){
        practice::Coordinator c;capture::PracticeSession s(store,c);s.start(request(group),1,now());ready(s);s.takeStart(now());stoppedReview(s,c,48000);
        fault=mode;check(s.save("Easy",capture::Outcome::Natural,now()),"first immutable natural save");until(s,[&]{return s.phase()==capture::SessionPhase::Failed;});const auto bytes=s.original()->bytes;
        check(!s.again(true)&&!s.canLeave(true)&&c.pending(),"failed or lost final ACK blocks replacement");
        check(s.retry(now()),"explicit retry original after final failure");saved(s);check(s.original()->bytes==bytes&&!c.pending(),"retry confirms exact original once");until(s,[&]{return s.canLeave(true);});
    }
    {
        practice::Coordinator c;capture::PracticeSession s(store,c);s.start(request(group,true),1,now());ready(s);s.takeStart(now());stoppedReview(s,c,48000);s.save(nullptr,capture::Outcome::Natural,now());saved(s);
        check(s.original()->kind=="FreeplayActivity"&&at(at(s.original()->value,"result"),"content").null()&&!s.binding().context.find("session_id"),"Freeplay never adopts lesson Session or content");until(s,[&]{return s.canLeave(true);});
    }
    // Retain a genuine allocated-only identity with exact durable metadata, then
    // normally close and reopen. No native playback or crash is implied.
    auto r=request(group);r.binding.context.object().at("configuration").object()["capture_metadata"]=O{{"practice_utc",r.binding.practiceUtc},{"timezone",r.binding.timezone}};
    auto allocation=confirmed(store.allocate(storage::newUuid(),r.binding.kind,r.binding.context,r.binding.practiceUtc));durableOwner=allocation.owner;durableContext=r.binding.context;
    write(out/"before-reopen.json",storage::canonical(confirmed(store.snapshot(storage::newUuid())).data));
    }
    options.create=false;
    {
    storage::ProfileStore store(options);practice::Coordinator c;capture::PracticeSession s(store,c);fault=7;
    storage::RecoveryBinding rb{durableOwner,"Attempt",durableContext,nullptr,{},0,0};check(s.recover(rb),"explicit same-owner stopped reopen");until(s,[&]{return s.phase()==capture::SessionPhase::Failed;});
    check(!s.takeStart(now())&&!s.canLeave(true)&&s.retry(now()),"failed recovery retries same binding while stopped");saved(s);
    check(s.original()->owner==durableOwner&&s.original()->active==Rational{}&&s.original()->practiceUtc=="2026-09-08T04:00:00Z"&&s.original()->timezone=="America/New_York", "allocated-only recovery exact owner UTC zone zero time");
    check(at(at(s.original()->value,"result"),"outcome")==V("interrupted_reopen")&&!s.takeStart(now())&&!c.pending(),"allocated-only recovered original no autoplay");until(s,[&]{return s.canLeave(true);});
    auto snap=confirmed(store.snapshot(storage::newUuid()));write(out/"snapshot.json",storage::canonical(snap.data));const auto& authorities=at(snap.data,"authoritative");
    check(at(authorities,"finalized").array().size()==9&&at(authorities,"identity").array().size()==9&&at(authorities,"pending").array().empty(),"nine originals final once no pending duplicates");
    check(at(authorities,"source_attestation").array().empty()&&at(authorities,"session").array().size()==1,"one Session group and no inferred source performance");
    auto adapted=progression::adaptSnapshot(snap);check(adapted.records.size()==9,"accepted progression consumer reads actual capture originals");
    }
    options.diagnosticHook={};{storage::ProfileStore store(options);write(out/"reopened-snapshot.json",storage::canonical(confirmed(store.snapshot(storage::newUuid())).data));}
    write(out/"checks.json",storage::canonical(O{{"checks",n(checks)},{"failures",n(failures)},{"synthetic_fixture",true},{"cases",results}}));
    std::cout<<checks<<" checks; "<<failures<<" failures\n";return failures?1:0;
}catch(const std::exception& e){std::cerr<<"ERROR "<<e.what()<<'\n';return 2;}}
