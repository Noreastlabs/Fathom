#include "practice/AttemptCapture.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "progression/ProgressionAdapter.hpp"
#include "storage/Recovery.hpp"
#include "content/Canonical.hpp"
#include <atomic>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <thread>

using namespace fathom;
using V=json::Value;using O=V::Object;using A=V::Array;
namespace fs=std::filesystem;
namespace {
int checks=0,failures=0;
void check(bool b,const char* name){++checks;if(!b){++failures;std::cerr<<"FAIL "<<name<<'\n';}}
template<class F>void refuses(F f,const char* name){try{f();check(false,name);}catch(const std::exception&){check(true,name);}}
V n(std::int64_t x){return V::fromInteger(x);}V q(std::int64_t x,std::int64_t y=1){Rational r{x,y};return A{n(r.numerator()),n(r.denominator())};}
const V& at(const V& v,const char* k){return v.object().at(k);}V& at(V& v,const char* k){return v.object().at(k);}
void write(const fs::path& p,const std::string& s){std::ofstream out(p,std::ios::binary);out<<s;out.flush();if(!out)throw std::runtime_error("Evidence write failed");}
storage::Reply get(storage::ProfileStore::Future f){auto r=f.get();if(r.status!=storage::Status::Confirmed)throw std::runtime_error(r.code+": "+r.message);return r;}
practice::Configuration config(){practice::Configuration c;c.rate=8000;c.bpm=120;c.span=Rational{4};c.meter={{4,4}};c.faithfulWholeSpan=true;c.targetCycles=2;return c;}
scheduler::Owner owner(const std::string& id){scheduler::Owner o;std::string compact;for(auto c:id)if(c!='-')compact+=c;for(std::size_t i=0;i<16;++i)o.id[i]=static_cast<std::uint8_t>(std::stoul(compact.substr(i*2,2),nullptr,16));o.generation=1;o.epoch=1;return o;}
capture::Binding allocate(storage::ProfileStore& s,const practice::Configuration& cfg,bool freeplay=false){
    capture::Binding b;b.kind=freeplay?"FreeplayActivity":"Attempt";b.practiceUtc="2026-09-08T03:00:00Z";b.timezone="America/New_York";
    V configuration=O{{"values",capture::configurationValues(cfg)},{"synthetic_fixture",true},{"authored_tempo_ref",nullptr},{"beat_reference_q",q(1)}};
    b.context=O{{"configuration_version",n(1)},{"configuration",configuration}};
    if(!freeplay){
        auto session=get(s.createSession(storage::newUuid(),b.practiceUtc,b.timezone));
        const V span=O{{"start",q(0)},{"end",q(4)}};const V target=O{{"cycles",n(2)}};
        V condition=O{{"variant","fg:variant:000001"},{"revision",n(1)},{"content_version","synthetic-capture.1"},
            {"setup","synthetic-standard"},{"span",span},{"beat_unit","quarter"},{"grouping","one-per-quarter"},{"technique","test-only"},{"target",target}};
        at(configuration,"values")=capture::configurationValues(cfg);configuration.object()["canonical_variant_id"]="fg:variant:000001";
        configuration.object()["progression_condition"]=condition;
        configuration.object()["source_hashes"]=O{{"synthetic-source",std::string(64,'b')}};
        b.context=O{{"session_id",session.owner},{"item_id","fg:item:000001"},{"variant_id","fg:variant:000001"},
            {"content_revision",n(1)},{"content_version","synthetic-capture.1"},{"source_manifest_sha256",std::string(64,'a')},
            {"source_refs",A{"synthetic-source"}},{"configuration_version",n(1)},{"configuration",configuration},{"span",span},{"target",target}};
        b.sourceHashes=O{{"synthetic-source",std::string(64,'b')}};
    }
    b.owner=get(s.allocate(storage::newUuid(),b.kind,b.context,b.practiceUtc)).owner;return b;
}
void begin(practice::Coordinator& c,const capture::Binding& b,const practice::Configuration& cfg){c.begin(owner(b.owner),b.kind=="Attempt"?practice::Kind::Attempt:practice::Kind::Freeplay,storage::canonical(b.context),cfg);}
practice::Progress progress(const practice::Coordinator& c,std::uint64_t accepted,practice::State state){
    practice::Progress p;p.owner=c.owner();p.sequence=1;p.clientAcceptedThrough=p.scheduledThrough=p.uncertainThrough=accepted;
    const std::uint64_t intro=c.configuration().countIn==practice::CountIn::Off?0:16000;
    p.activeFrames=accepted>intro?accepted-intro:0;p.completedCycles=p.activeFrames/16000;p.cursorFrames=p.activeFrames%16000;
    p.partial=p.cursorFrames!=0;p.state=state;p.terminal=state==practice::State::Paused||state==practice::State::Ended||state==practice::State::Error;
    p.fault=state==practice::State::Error;p.requestedStopNs=p.terminal?123456789:0;return p;
}
void done(capture::SaveOperation& op,std::int64_t start=0){for(int i=0;i<5000&&!op.poll(start+i);++i)std::this_thread::sleep_for(std::chrono::milliseconds(1));if(!op.finished())throw std::runtime_error("Save exceeded declared5s");}
void save(storage::ProfileStore& s,practice::Coordinator& c,const capture::Binding& b,const fs::path& out,const char* name,V a=nullptr,capture::Outcome o=capture::Outcome::Stop){
    capture::SaveOperation op(s,c,b,a,o,storage::newUuid(),0);check(c.sealed()&&!op.saved()&&!op.release(c),"firstseal retains pending");done(op);
    check(op.saved()&&op.feedback().owner==b.owner,"exact final receipt saved");write(out/(std::string(name)+".json"),op.original().bytes);
    auto cp=capture::makeCheckpoint(c,b,100,a,o,&op.original());check(!cp.bytes.empty(),"sealed checkpoint exact original");
    check(op.release(c)&&c.state()==practice::State::Stopped,"confirmed release stopped");
    check(s.checkpoint(storage::newUuid(),b.owner,cp.generation,cp.sequence,cp.bytes).get().status!=storage::Status::Confirmed,"no checkpoint after final");
}
}
int main(int argc,char** argv){try{
    if(argc!=2)throw std::runtime_error("Explicit new test-data directory required");
    fs::path out=fs::absolute(argv[1]).lexically_normal();
    if(out.string().find("/Results/20260908T031111Z-3.4.1.1.1-r01-evidence/test-data/")==std::string::npos||fs::exists(out))throw std::runtime_error("Require a new directory inside this lane test-data");
    fs::create_directories(out);fs::permissions(out,fs::perms::owner_all,fs::perm_options::replace);
    storage::StoreOptions options;options.path=out/"profile.sqlite";options.create=true;options.createdUtc="2026-09-08T03:00:00Z";
    std::atomic<int> fault{0};
    options.diagnosticHook=[&](const std::string& phase,const std::string& op){
        if(op.find("lost.commit")!=std::string::npos&&phase=="after_commit"&&fault.exchange(0)==1)throw std::runtime_error("Controlled lost ACK after committed original");
        if(op.find("failed.commit")!=std::string::npos&&phase=="before_commit"&&fault.exchange(0)==2)throw std::runtime_error("Controlled failure before COMMIT");
        if(op.find("slow.reconcile")!=std::string::npos&&phase=="before_operation")std::this_thread::sleep_for(std::chrono::milliseconds(1100));
    };
    {
    storage::ProfileStore store(options);const auto cfg=config();
    { auto b=allocate(store,cfg);practice::Coordinator c;begin(c,b,cfg);c.progress(progress(c,8000,practice::State::Paused));c.stoppedAcknowledged(c.owner(),practice::State::Ended,555);
      auto e=capture::makeEnvelope(c,b,nullptr,capture::Outcome::Stop);auto& r=at(e.value,"result");
      check(e.active==Rational{}&&at(r,"completed_cycles").array().empty()&&at(r,"traversals").array().empty(),"countin cancellation zero facts");
      check(at(r,"interruptions").array().size()==2&&at(at(r,"interruptions").array().back(),"requested_stop_ns")==V("555"),"controlStop retained separately");
      save(store,c,b,out,"zero"); }
    { auto b=allocate(store,cfg);practice::Coordinator c;begin(c,b,cfg);
      auto initial=capture::makeCheckpoint(c,b,0);check(at(at(storage::parseCanonical(initial.bytes),"practice_snapshot"),"uncertain")==V(false),"physical unavailable is not save uncertainty");get(store.checkpoint(storage::newUuid(),b.owner,initial.generation,0,initial.bytes));
      c.progress(progress(c,24000,practice::State::Paused));auto cp=capture::makeCheckpoint(c,b,1);get(store.checkpoint(storage::newUuid(),b.owner,cp.generation,1,cp.bytes));
      storage::RecoveryBinding rb{b.owner,b.kind,b.context,nullptr,{},1,1};auto recovery=storage::planRecovery(get(store.recoveryState(storage::newUuid(),b.owner)),rb);
      auto recovered=storage::validateEnvelope(recovery.bytes);check(recovered.active==Rational{1}&&at(at(recovered.value,"result"),"outcome")==V("interrupted_reopen"),"unsealed recovery retains last1s");
      c.resume();c.progress(progress(c,48000,practice::State::Ended));auto e=capture::makeEnvelope(c,b,"Clean",capture::Outcome::Natural);const auto& r=at(e.value,"result");
      check(e.active==Rational{5}&&at(r,"completed_cycles").array()==A{n(1),n(2)},"replay5s with2cycles");
      check(at(r,"traversals").array().size()==3&&at(at(r,"traversals").array()[0],"cycle")==n(1)&&at(at(r,"traversals").array()[1],"cycle")==n(1),"partial cycle1 remains before fullcycle1");
      check(c.stoppedAcknowledged(c.owner(),practice::State::Error,999),"latebackenderrorafterestablishedNatural");
      auto later=capture::makeEnvelope(c,b,"Clean",capture::Outcome::Natural);check(at(at(later.value,"result"),"outcome")==V("natural"),"unsealed establishedNatural surviveslaterError");
      refuses([&]{capture::makeEnvelope(c,b,"Clean",capture::Outcome::InterruptedError);},"cannotrewrite establishedNatural asinterrupted");
      refuses([&]{auto bad=b;bad.owner=storage::newUuid();capture::makeEnvelope(c,bad,nullptr,capture::Outcome::Natural);},"wrongowner");
      refuses([&]{auto bad=b;at(at(bad.context,"configuration"),"values").object()["rate"]=n(48000);capture::makeEnvelope(c,bad,nullptr,capture::Outcome::Natural);},"changed pinned configuration");
      refuses([&]{auto bad=b;bad.sourceHashes=O{{"wrong-source",std::string(64,'b')}};capture::makeEnvelope(c,bad,nullptr,capture::Outcome::Natural);},"wrong source hash coverage");
      refuses([&]{auto bad=b;bad.sourceHashes=O{{"synthetic-source",std::string(64,'c')}};capture::makeEnvelope(c,bad,nullptr,capture::Outcome::Natural);},"valid changed source hash cannotreplaceoriginal");
      for(const char* field:{"variant","revision","content_version","span","target","technique"}){
          auto bad=b;auto& condition=at(at(bad.context,"configuration"),"progression_condition");
          if(std::string(field)=="technique")condition.object().erase(field);
          else if(std::string(field)=="revision")at(condition,field)=n(2);
          else if(std::string(field)=="span")at(condition,field)=O{{"start",q(0)},{"end",q(2)}};
          else if(std::string(field)=="target")at(condition,field)=O{{"cycles",n(1)}};
          else at(condition,field)="different";
          practice::Coordinator invalid;begin(invalid,bad,cfg);invalid.progress(progress(invalid,48000,practice::State::Ended));
          refuses([&]{capture::makeEnvelope(invalid,bad,nullptr,capture::Outcome::Natural);},"malformed/mismatchedcondition refused beforeStore");
      }
      refuses([&]{capture::makeEnvelope(c,b,"AutomaticClean",capture::Outcome::Natural);},"no inferred assessment");
      save(store,c,b,out,"replay","Clean",capture::Outcome::Natural); }
    { auto b=allocate(store,cfg);practice::Coordinator c;begin(c,b,cfg);
      refuses([&]{capture::makeEnvelope(c,b,"Clean",capture::Outcome::Stop);},"midrun assessment rejected");
      c.progress(progress(c,27000,practice::State::Ended));auto e=capture::makeEnvelope(c,b,"Clean",capture::Outcome::Stop);
      check(e.active==Rational{11,8}&&at(at(e.value,"result"),"completed_cycles").array().empty()&&e.outcome=="partial","restStop explicitClean remains partial");
      refuses([&]{capture::makeEnvelope(c,b,"Clean",capture::Outcome::Natural);},"natural target cannot be invented");save(store,c,b,out,"partial","Clean"); }
    { auto b=allocate(store,cfg);practice::Coordinator c;begin(c,b,cfg);c.progress(progress(c,32000,practice::State::Paused));c.stoppedAcknowledged(c.owner(),practice::State::Ended,777);
      auto e=capture::makeEnvelope(c,b,nullptr,capture::Outcome::Stop);check(at(at(e.value,"result"),"completed_cycles").array()==A{n(1)},"Stop exact boundary preceding cycleonce");
      save(store,c,b,out,"boundary"); }
    { auto b=allocate(store,cfg);practice::Coordinator c;begin(c,b,cfg);c.progress(progress(c,24000,practice::State::Error));
      refuses([&]{capture::makeEnvelope(c,b,nullptr,capture::Outcome::Stop);},"error disposition preserved");
      save(store,c,b,out,"error",nullptr,capture::Outcome::InterruptedError); }
    { auto b=allocate(store,cfg,true);practice::Coordinator c;begin(c,b,cfg);c.progress(progress(c,48000,practice::State::Ended));auto e=capture::makeEnvelope(c,b,nullptr,capture::Outcome::Natural);
      check(at(at(e.value,"result"),"content").null()&&!e.value.object().at("context").find("session_id"),"Freeplay no content orSession");
      save(store,c,b,out,"freeplay",nullptr,capture::Outcome::Natural); }
    { auto b=allocate(store,cfg);practice::Coordinator c;begin(c,b,cfg);c.progress(progress(c,48000,practice::State::Ended));fault=1;
      capture::SaveOperation op(store,c,b,"Easy",capture::Outcome::Natural,"lost",0);done(op);check(!op.saved()&&op.feedback().code=="ACKNOWLEDGMENT_LOST"&&c.pending(),"lostACK remains originalpending");
      const auto original=op.original();auto cp=capture::makeCheckpoint(c,b,2,"Easy",capture::Outcome::Natural,&original);
      refuses([&]{capture::SaveOperation conflict(store,c,b,"Clean",capture::Outcome::Natural,"conflict",0);},"sealed assessment conflict refused");
      auto late=c.generations().back();++late.sequence;late.scheduledThrough+=256;c.progress(late);
      auto sealedCp=capture::makeCheckpoint(c,b,3,"Easy",capture::Outcome::Natural,&original);check(storage::parseCanonical(cp.bytes).object().at("sealed_envelope")==storage::parseCanonical(sealedCp.bytes).object().at("sealed_envelope"),"late facts cannot rewrite sealedcheckpoint");
      get(store.appendLate(storage::newUuid(),b.owner,storage::newUuid(),b.practiceUtc,storage::canonical(capture::lateEvidence(late))));
      check(!c.reconcile(original.owner,original.bytes,practice::Coordinator::Save::Conflict)&&c.state()==practice::State::Error,"later saveerror retains establishedNatural");
      auto errorCp=capture::makeCheckpoint(c,b,4,"Easy",capture::Outcome::Natural,&original,true);check(at(at(storage::parseCanonical(errorCp.bytes),"practice_snapshot"),"uncertain")==V(true),"explicit save uncertainty retainedwithoriginal");
      capture::SaveOperation retry(store,c,original,"retry",0);done(retry);check(retry.saved()&&retry.original().bytes==original.bytes&&retry.release(c),"original reconciliation once afterlostACK");
      write(out/"lost-original.json",original.bytes); }
    { auto b=allocate(store,cfg);practice::Coordinator c;begin(c,b,cfg);c.progress(progress(c,8000,practice::State::Ended));fault=2;
      capture::SaveOperation op(store,c,b,nullptr,capture::Outcome::Stop,"failed",0);done(op);check(!op.saved()&&c.pending(),"failedcommit blocksAgain");
      auto original=op.original().bytes;capture::SaveOperation retry(store,c,op.original(),"retryfailed",0);done(retry);check(retry.saved()&&retry.original().bytes==original&&retry.release(c),"failedsave retry exactoriginal"); }
    { auto b=allocate(store,cfg);practice::Coordinator c;begin(c,b,cfg);c.progress(progress(c,8000,practice::State::Ended));
      capture::SaveOperation op(store,c,b,nullptr,capture::Outcome::Stop,"slow",0);check(!op.poll(1001)&&op.feedback().code=="ACK_TIMEOUT"&&!op.finished()&&!op.release(c),"timeout retainslivefuture");
      done(op,1001);check(op.saved()&&op.release(c)&&c.state()==practice::State::Stopped,"lateACK completesstopped noautoplay"); }
    auto snapshot=get(store.snapshot(storage::newUuid()));write(out/"snapshot.json",storage::canonical(snapshot.data));auto adapted=progression::adaptSnapshot(snapshot);
    check(adapted.records.size()==9,"nine unique final records");
    std::size_t complete=0,partialClean=0,freeplay=0;for(auto& e:adapted.records){if(e.kind==progression::Kind::Freeplay)++freeplay;else{if(e.complete)++complete;if(!e.complete&&e.assessment==V("Clean"))++partialClean;}}
    check(complete==2&&partialClean==1&&freeplay==1,"consumer distinguishes actualtargets partialClean Freeplay");
    check(at(at(snapshot.data,"authoritative"),"source_attestation").array().empty(),"capture producesno sourceattestation");
    }
    // Normal close/reopen in this process; separate executable adds distinct-process evidence.
    options.create=false;options.diagnosticHook={};{storage::ProfileStore reopened(options);auto r=get(reopened.snapshot(storage::newUuid()));write(out/"reopened-snapshot.json",storage::canonical(r.data));check(at(at(r.data,"authoritative"),"finalized").array().size()==9,"normalreopen nineoriginals");}
    write(out/"result.json",storage::canonical(O{{"checks",n(checks)},{"failures",n(failures)},{"synthetic_fixture",true}}));
    std::cout<<checks<<" checks; "<<failures<<" failures\n";return failures?1:0;
}catch(const std::exception& e){std::cerr<<"ERROR "<<e.what()<<'\n';return 2;}}
