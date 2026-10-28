// Contract-driven synthetic submissions through actual Coordinator and private Store.
#define main retained_pulse_campaign_main
#include "m1_lesson_pulse_tests.cpp"
#undef main
#include <mutex>

namespace {
practice::Progress fact(scheduler::Owner o,std::uint64_t seq,std::uint64_t through,
        std::uint64_t intro,std::uint64_t cycles,std::uint64_t anchor,
        practice::State state=practice::State::Ended){
    practice::Progress p;p.owner=o;p.sequence=seq;p.clientAcceptedThrough=through;
    p.scheduledThrough=through+256;p.uncertainThrough=through+128;
    p.activeFrames=through>intro?through-intro:0;p.completedCycles=cycles;
    p.cursorFrames=through>anchor?through-anchor:0;p.partial=p.cursorFrames!=0;
    p.state=state;p.terminal=state==practice::State::Ended||state==practice::State::Paused||state==practice::State::Error;
    p.fault=state==practice::State::Error;p.requestedStopNs=p.terminal?123456:0;return p;
}
std::string bytes(const V& v){const auto& hex=at(v,"blob_hex").string();std::string b;
    for(std::size_t i=0;i<hex.size();i+=2)b+=static_cast<char>(std::stoul(hex.substr(i,2),nullptr,16));return b;}
const V& authority(const V& snapshot,const char* table){return at(at(snapshot,"authoritative"),table);}
void saveStopped(capture::PracticeSession& s){s.poll(now(),"2026-09-12T16:15:00Z");
    check(s.phase()==capture::SessionPhase::Review&&s.save(nullptr,capture::Outcome::Stop,now()),"explicit stopped original Save");
    pulseUntil(s,[&]{return s.phase()==capture::SessionPhase::Saved&&s.canLeave(true);});}
void started(capture::PracticeSession& s,capture::StartRequest r,std::uint64_t seq){
    check(s.start(std::move(r),seq,now()),"private Store allocation starts");
    pulseUntil(s,[&]{return s.phase()==capture::SessionPhase::Ready;});check(s.takeStart(now()).has_value(),"durable initial checkpoint precedes synthetic submissions");}
}
int main(int argc,char** argv){try{
    if(argc!=3)throw std::invalid_argument("Require accepted bundle and new absolute evidence directory");
    const std::filesystem::path out(argv[2]);if(!out.is_absolute()||std::filesystem::exists(out))throw std::invalid_argument("New absolute evidence directory required");
    std::filesystem::create_directories(out);std::filesystem::permissions(out,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);checkTrace.open(out/"checks.tsv");
    const auto catalog=lesson::Catalog::load(argv[1]);const auto a=catalog->admitCell("fg:item:000002","fg:variant:000006",3);
    auto cfg=a->practiceConfiguration(44100,60);cfg.targetCycles=4;
    // Exact expected sample facts below derive from one quarter: 44100 at60,
    // then35280 at75, then29400 at90. They are not computed by the consumer.
    auto c=original(*a,cfg,false);const auto o=c.owner();const auto base=c.timeline(o);
    auto paused=fact(o,1,52920,0,1,44100,practice::State::Paused);auto changed=base.changed(1,75);
    check(c.progress(paused,changed),"partial75 accepted before explicit same-original resume");c.resume();
    const auto resumed=c.owner();auto resumedMap=c.timeline(resumed);
    check(resumedMap.spec().initialBpm==75&&resumedMap.spec().cycles==3&&c.configuration().bpm==60,"generation-local75 does not rewrite original selected60");
    check(c.progress(fact(resumed,1,1,0,0,0,practice::State::Ended)),"resumed generation stops at first confirmed frame");
    auto resumedLate=fact(resumed,2,35281,0,1,35280);auto resumedChanged=resumedMap.changed(1,90);
    const auto credit=c.activeFrames();check(!c.progress(resumedLate,resumedChanged)&&c.activeFrames()==credit,"late resumed map does not alter original credit");
    const auto serialized=capture::lateEvidence(resumedLate,*c.lateTimeline(resumedLate));
    check(at(at(serialized,"tempo_timeline"),"initial_bpm")==n(75)&&at(at(serialized,"tempo_timeline"),"target_cycles")==n(3),"late map serializes generation-local initial tempo and remaining target");
    write(out/"resumed-late.json",storage::canonical(serialized));
    auto raw=fact(resumed,3,999999,0,0,999999);check(!c.progress(raw)&&!c.lateTimeline(raw),"legacy raw notification remains explicitly mapless");
    auto more=fact(resumed,4,35282,0,1,35280);check(!c.progress(more,resumedChanged)&&c.lateTimeline(more),"raw scalar is not accepted map or prefix authority");
    auto scalar=capture::lateEvidence(raw);check(!scalar.find("tempo_timeline"),"scalar payload has no synthesized or null map field");write(out/"scalar-late.json",storage::canonical(scalar));
    auto bad=more;bad.sequence=5;const auto count=c.lateEvidence().size();
    auto reject=[&](const practice::Progress& p,const practice::Timeline& map,const char* why){refuses([&]{c.progress(p,map);},why);check(c.lateEvidence().size()==count&&c.activeFrames()==credit,"invalid late evidence changes neither audit nor credit");};
    reject(bad,resumedMap,"missing already validated late tempo point refused");
    reject(bad,resumedMap.changed(1,89),"changed prior late tempo point refused");
    for(int mode=0;mode<8;++mode){auto spec=resumedChanged.spec();switch(mode){
        case 0:++spec.owner.epoch;break;case 1:++spec.owner.generation;break;case 2:spec.owner.id[0]^=1;break;
        case 3:spec.rate=48000;break;case 4:spec.initialBpm=60;break;case 5:spec.span=Rational{2};break;
        case 6:spec.intro=Rational{3};break;case 7:spec.cycles=4;break;}
        reject(bad,practice::Timeline(spec),"foreign original spec refused");}
    reject(bad,resumedChanged.changed(2,100),"unsubmitted future point refused");
    auto regressed=bad;regressed.clientAcceptedThrough=35281;regressed.activeFrames=35281;regressed.cursorFrames=1;reject(regressed,resumedChanged,"late accepted prefix regression refused");
    for(int mode=0;mode<6;++mode){auto invalid=bad;switch(mode){case 0:++invalid.activeFrames;break;case 1:++invalid.completedCycles;break;
        case 2:++invalid.cursorFrames;break;case 3:invalid.partial=false;break;case 4:invalid.fault=true;break;case 5:invalid.terminal=false;break;}
        reject(invalid,resumedChanged,"malformed late sample or terminal accounting refused");}
    bad.dispositionSequence=1;reject(bad,resumedChanged,"callback cannot impersonate control disposition");
    check(!c.progress(more,resumedMap)&&c.lateEvidence().size()==count,"duplicate sequence cannot replace or add audit");
    auto stale=more;stale.sequence=1;check(!c.progress(stale,resumedMap)&&c.lateEvidence().size()==count,"stale sequence cannot add audit");
    auto unknown=more;unknown.owner.id[1]=99;check(!c.progress(unknown,resumedChanged)&&c.lateEvidence().size()==count,"unknown owner cannot create audit");
    // Disposition remains an old scalar control fact, never a fabricated map.
    auto disposition=original(*a,cfg,false);check(disposition.progress(fact(disposition.owner(),1,100,0,0,0,practice::State::Paused)),"pause before separate control disposition");
    check(disposition.stoppedAcknowledged(disposition.owner(),practice::State::Ended,777),"actual control disposition retained");
    const auto& marker=disposition.lateEvidence().back();check(marker.dispositionSequence&&!disposition.lateTimeline(marker)&&!capture::lateEvidence(marker).find("tempo_timeline"),"scalar disposition byte shape unchanged");
    write(out/"scalar-disposition.json",storage::canonical(capture::lateEvidence(marker)));
    // Real outbox, original-key lost acknowledgment/retry and ordinary reopen.
    storage::StoreOptions options;options.path=out/"profile.sqlite";options.create=true;options.createdUtc="2026-09-12T16:15:00Z";
    std::atomic<int> mode{0};std::atomic<bool> entered{false},releaseAudit{false};std::mutex logMutex;A hookLog;
    options.diagnosticHook=[&](const std::string& phase,const std::string& operation){
        if(operation.find(".late")==std::string::npos)return;
        {std::lock_guard<std::mutex> lock(logMutex);hookLog.push_back(O{{"phase",phase},{"operation",operation}});}
        if(phase=="before_operation"&&mode==1){mode=2;entered=true;const auto hookDeadline=now()+6000;
            while(!releaseAudit){if(now()>hookDeadline)throw std::runtime_error("Bounded late-audit hook gate watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}}
        if(phase=="after_commit"&&mode==2){mode=0;throw std::runtime_error("Synthetic lost late-audit ACK after actual commit");}
    };
    V before;A expectedAudits;std::string originalBytes,oldId;
    {storage::ProfileStore store(options);const auto session=confirmed(store.createSession(storage::newUuid(),options.createdUtc,"America/New_York",{},O{{"synthetic_fixture",true}})).owner;
        practice::Coordinator co;capture::PracticeSession s(store,co);started(s,capture::lessonStart(*a,cfg,session,options.createdUtc,"America/New_York",1,false),1);
        const auto old=co.owner();oldId=s.binding().owner;const auto accepted=co.timeline(old);
        check(co.progress(fact(old,1,44100,0,1,44100)),"one60BPM cycle stopped for original Save");saveStopped(s);originalBytes=s.original()->bytes;write(out/"original.json",originalBytes);
        const auto originalContext=co.context();const auto savedCredit=co.activeFrames();const auto savedCycles=co.completedCycles();
        auto first=fact(old,2,44101,0,1,44100);auto firstMap=accepted.changed(1,75);
        auto second=fact(old,3,79381,0,2,79380);auto secondMap=firstMap.changed(2,90);
        check(!co.progress(first,firstMap)&&!co.progress(second,secondMap),"two late packets queued before collector polls");
        check(co.lateTimeline(first)->points().size()==2&&co.lateTimeline(second)->points().size()==3,"each packet retains its own map snapshot");
        check(co.activeFrames()==savedCredit&&co.completedCycles()==savedCycles&&co.context()==originalContext&&s.original()->bytes==originalBytes,"sealed original and totals unchanged by later output facts");
        expectedAudits.push_back(capture::lateEvidence(first,firstMap));expectedAudits.push_back(capture::lateEvidence(second,secondMap));
        mode=1;s.poll(now(),options.createdUtc);
        const auto deadline=now()+6000;while(!entered){if(now()>deadline)throw std::runtime_error("Late hook entry watchdog");std::this_thread::sleep_for(std::chrono::milliseconds(1));}
        pulseUntil(s,[&]{return s.feedback().code=="AUDIT_ACK_TIMEOUT";});
        check(s.stopRequired()&&!s.canLeave(true)&&!s.again(true)&&!s.retry(now()),"pending late ACK blocks leave/Again and cannot create concurrent retry");
        releaseAudit=true;pulseUntil(s,[&]{return s.feedback().code=="ACKNOWLEDGMENT_LOST";});
        check(!s.canLeave(true)&&!s.again(true)&&s.original()->bytes==originalBytes,"lost actual late commit receipt preserves exact original and unresolved audit");
        check(s.retry(now()),"explicit retry retains same outbox event identity and payload");pulseUntil(s,[&]{return s.canLeave(true);});
        auto snapshot=confirmed(store.snapshot(storage::newUuid()));check(authority(snapshot.data,"late_evidence").array().size()==2,"lost receipt and retry produce exactly two distinct audit rows");
        check(authority(snapshot.data,"finalized").array().size()==1&&bytes(authority(snapshot.data,"finalized").array()[0].array()[1])==originalBytes,"actual finalized BLOB remains byte identical after audits");
        write(out/"after-audit.json",storage::canonical(snapshot.data));
        const auto b=catalog->admitCell("fg:item:000002","fg:variant:000006",4);auto other=b->practiceConfiguration(48000,120);other.targetCycles=2;
        check(s.again(true),"Again only after original and audit receipts");started(s,capture::lessonStart(*b,other,session,options.createdUtc,"America/New_York",2,false),2);
        const auto current=co.owner();const auto currentContext=co.context();
        check(current.id!=old.id&&currentContext!=originalContext&&co.configuration().rate==48000&&co.currentTempo()==120,"new context has distinct identity source-cell rate and tempo");
        auto third=fact(old,4,108781,0,3,108780);check(!co.progress(third,secondMap),"old44100 map validated after new48000 context begins");expectedAudits.push_back(capture::lateEvidence(third,secondMap));
        check(co.owner()==current&&co.activeFrames()==0&&co.completedCycles()==0&&co.currentTempo()==120&&co.context()==currentContext,"old owner map adds no new context credit or tempo");
        s.poll(now(),options.createdUtc);const auto auditDeadline=now()+6000;
        while(authority(confirmed(store.snapshot(storage::newUuid())).data,"late_evidence").array().size()!=3){if(now()>auditDeadline)throw std::runtime_error("Third audit watchdog");s.poll(now(),options.createdUtc);std::this_thread::sleep_for(std::chrono::milliseconds(1));}
        s.poll(now(),options.createdUtc);check(co.pending()&&s.phase()==capture::SessionPhase::Active&&!s.canLeave(true)&&!s.again(true),"old audit ACK cannot release current unresolved outcome");
        check(co.progress(fact(current,1,12000,0,0,0)),"new source cell ends partial with own120BPM configuration");saveStopped(s);write(out/"second-original.json",s.original()->bytes);
        // Large exact decimal anchors use this same production audit outbox.
        auto wideCfg=a->practiceConfiguration(48000,137);wideCfg.targetCycles=32;check(s.again(true),"rearm explicit wide original");
        started(s,capture::lessonStart(*a,wideCfg,session,options.createdUtc,"America/New_York",3,false),3);const auto wideOwner=co.owner();auto wide=co.timeline(wideOwner);
        check(co.progress(fact(wideOwner,1,21022,0,1,21022)),"wide selected137 original stopped at one rounded cycle");saveStopped(s);const auto wideBytes=s.original()->bytes;write(out/"wide-original.json",wideBytes);
        for(std::uint64_t cycle=1;cycle<32;++cycle)wide=wide.changed(cycle,static_cast<std::uint16_t>(137+2*cycle));
        check(wide.frame(32)==555347,"wide exact map matches retained independent32-cycle endpoint");
        auto wideLate=fact(wideOwner,2,555347,0,32,555347);check(!co.progress(wideLate,wide)&&co.activeFrames()==21022&&co.completedCycles()==1,"late32cycle map cannot retroactively complete original target");
        expectedAudits.push_back(capture::lateEvidence(wideLate,wide));s.poll(now(),options.createdUtc);pulseUntil(s,[&]{return s.canLeave(true);});
        check(s.original()->bytes==wideBytes,"wide original immutable after exact anchor audit");
        before=confirmed(store.snapshot(storage::newUuid())).data;
        const auto& rows=authority(before,"late_evidence").array();check(rows.size()==4,"four exact mapped audit identities retained");std::set<std::string> events;std::set<std::string> actual;
        for(const auto& row:rows){const auto& r=row.array();events.insert(r[0].string());const auto payload=bytes(r[3]);actual.insert(payload);check(content::sha256(payload)==r[4].string(),"each stored audit digest binds exact payload");}
        check(events.size()==4&&actual.size()==4,"no duplicate identity or overwritten packet");for(const auto& expected:expectedAudits)check(actual.count(storage::canonical(expected))==1,"stored audit equals its original packet-specific map and raw facts");
        const auto& row=rows.front().array();auto changedPayload=json::parse(bytes(row[3]));changedPayload.object()["sequence"]="9999";
        auto conflict=store.appendLate(storage::newUuid(),row[1].string(),row[0].string(),row[2].string(),storage::canonical(changedPayload)).get();
        check(conflict.status==storage::Status::Conflict,"same audit event key with conflicting payload fails visibly");
        check(confirmed(store.snapshot(storage::newUuid())).data==before,"conflicting late save changes no authoritative state");
        write(out/"conflict.json",storage::canonical(O{{"code",conflict.code},{"message",conflict.message},{"event_key",row[0]}}));
        check(authority(before,"finalized").array().size()==3&&authority(before,"source_attestation").array().empty(),"three originals and no fabricated source performance");
        auto derived=progression::adaptSnapshot(confirmed(store.snapshot(storage::newUuid())));check(derived.records.size()==3&&std::none_of(derived.records.begin(),derived.records.end(),[](const auto& r){return r.complete;}),"late audit never becomes progression completion credit");
        write(out/"before-reopen.json",storage::canonical(before));
    }
    options.create=false;options.diagnosticHook={};{storage::ProfileStore reopened(options);const auto after=confirmed(reopened.snapshot(storage::newUuid())).data;check(after==before,"ordinary reopen preserves all original and audit bytes");write(out/"after-reopen.json",storage::canonical(after));}
    write(out/"expected-audits.json",storage::canonical(expectedAudits));write(out/"hook-trace.json",storage::canonical(hookLog));
    write(out/"summary.json",storage::canonical(O{{"status","PASS"},{"checks",n(checks)},{"native",false},{"synthetic_submission_inputs",true},{"ordinary_reopen_not_crash",true},{"original_owner",oldId},{"audit_rows",n(4)}}));
    std::cout<<"PASS "<<checks<<" tempo audit checks\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
