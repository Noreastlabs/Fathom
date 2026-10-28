#include "storage/ProfileStore.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "content/Canonical.hpp"
#include "sqlite3.h"
#include "fixtures/profile_store/SyntheticL105Handler.hpp"
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <fstream>
#include <fcntl.h>
#include <iostream>
#include <mutex>
#include <spawn.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <thread>
#include <unistd.h>
extern char** environ;
namespace {
using namespace fathom::storage;
using Object=Value::Object;using Array=Value::Array;
namespace fs=std::filesystem;
fs::path evidence,runRoot,practice,source,process;
Array checks,commands;
int failures=0;
std::string read(const fs::path& path){std::ifstream in(path,std::ios::binary);if(!in)throw std::runtime_error("Cannot read "+path.string());return {std::istreambuf_iterator<char>(in),{}};}
void write(const fs::path& path,const std::string& bytes){std::ofstream out(path,std::ios::binary);out<<bytes;if(!out)throw std::runtime_error("Cannot write test evidence");}
const Value& at(const Value& v,const std::string& k){return v.object().at(k);}
Value& at(Value& v,const std::string& k){return v.object().at(k);}
std::string str(const Value& v,const std::string& k){return at(v,k).string();}
std::int64_t n(const Value& v){std::int64_t value;if(!v.integer(value))throw std::runtime_error("Expected test integer");return value;}
Value num(std::int64_t v){return Value::fromInteger(v);}
Value fixture(const std::string& name){return parseCanonical(read(practice/name));}
void check(const std::string& name,bool pass,const std::string& detail=""){
    checks.push_back(Object{{"case",name},{"passed",pass},{"detail",detail}});
    std::cout<<(pass?"PASS ":"FAIL ")<<name<<(detail.empty()?"":" : "+detail)<<'\n';
    if(!pass)++failures;
}
template<class F> void rejects(const std::string& name,F f){bool rejected=false;std::string why;try{f();}catch(const std::exception& e){rejected=true;why=e.what();}check(name,rejected,why);}
Reply result(const std::string& name,ProfileStore::Future future,Status expected=Status::Confirmed){auto r=future.get();check(name,r.status==expected,std::string(statusName(r.status))+" "+r.code+" "+r.message);return r;}
Reply must(const std::string& name,ProfileStore::Future f){auto r=result(name,std::move(f));if(r.status!=Status::Confirmed)throw std::runtime_error("Prerequisite failed: "+name);return r;}
StoreOptions options(const std::string& name){StoreOptions o;o.path=runRoot/name/"profile.sqlite";o.create=true;o.createdUtc="2026-09-07T21:00:00Z";o.preferenceValidator=[](const std::string& key,std::int64_t version,const Value& value){return key=="synthetic.settings"&&version==1&&value.isObject();};return o;}
Value withOwner(Value v,const std::string& owner,const Value& context){at(v,"owner")=owner;at(v,"context")=context;at(at(v,"result"),"key")=owner;return v;}
Value checkpointWith(Value v,const std::string& owner,const Value& context){at(v,"owner")=owner;at(v,"context")=context;at(at(v,"practice_snapshot"),"attempt")=owner;return v;}
std::string session(ProfileStore& store){return must("create Session",store.createSession(newUuid(),"2026-09-07T21:00:00Z","UTC",900,Object{{"rule","synthetic"}})).owner;}
std::pair<std::string,Value> allocate(ProfileStore& store,const std::string& s,bool freeplay=false){auto c=fixture(freeplay?"freeplay-context.json":"attempt-context.json");if(!freeplay)at(c,"session_id")=s;auto r=must("allocate original activity",store.allocate(newUuid(),freeplay?"FreeplayActivity":"Attempt",c,"2026-09-07T21:00:00Z"));return {r.owner,c};}
std::string envelope(const std::pair<std::string,Value>& a,bool freeplay=false){return canonical(withOwner(fixture(freeplay?"freeplay-valid.json":"attempt-valid.json"),a.first,a.second));}
int child(const std::string& mode,const fs::path& db,const std::string& label){
    auto output=runRoot/(label+".log");std::vector<std::string> args={process.string(),evidence.string(),mode,db.string()};Array command;for(const auto& a:args)command.push_back(a);commands.push_back(Object{{"argv",command},{"output",output.string()}});
    std::vector<char*> argv;for(auto& a:args)argv.push_back(a.data());argv.push_back(nullptr);
    posix_spawn_file_actions_t actions;posix_spawn_file_actions_init(&actions);
    posix_spawn_file_actions_addopen(&actions,STDOUT_FILENO,output.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);
    posix_spawn_file_actions_adddup2(&actions,STDOUT_FILENO,STDERR_FILENO);
    pid_t pid=0;int error=posix_spawn(&pid,process.c_str(),&actions,nullptr,argv.data(),environ);posix_spawn_file_actions_destroy(&actions);if(error)throw std::runtime_error("spawn failed "+std::to_string(error));
    int status=0;for(int i=0;i<1000;++i){auto waited=waitpid(pid,&status,WNOHANG);if(waited==pid)return WIFEXITED(status)?WEXITSTATUS(status):128+WTERMSIG(status);if(waited<0)throw std::runtime_error("waitpid failed");std::this_thread::sleep_for(std::chrono::milliseconds(10));}
    kill(pid,SIGKILL);waitpid(pid,&status,0);throw std::runtime_error("Separate-process case exceeded declared10s bound; terminated helper, no crash claim");
}
struct Sql {
    sqlite3* db=nullptr;
    explicit Sql(const fs::path& path){if(sqlite3_open_v2(path.c_str(),&db,SQLITE_OPEN_READWRITE|SQLITE_OPEN_NOMUTEX,nullptr)!=SQLITE_OK)throw std::runtime_error("fixture SQLite open");}
    ~Sql(){sqlite3_close(db);}
    void exec(const std::string& sql){char* e=nullptr;auto rc=sqlite3_exec(db,sql.c_str(),nullptr,nullptr,&e);auto message=e?std::string(e):"";sqlite3_free(e);if(rc!=SQLITE_OK)throw std::runtime_error(message);}
    std::string text(const std::string& sql){sqlite3_stmt* s=nullptr;if(sqlite3_prepare_v2(db,sql.c_str(),-1,&s,nullptr)!=SQLITE_OK)throw std::runtime_error("fixture query");std::string value;if(sqlite3_step(s)==SQLITE_ROW){auto p=sqlite3_column_text(s,0);if(p)value=reinterpret_cast<const char*>(p);}sqlite3_finalize(s);return value;}
};
Value fileHashes(const fs::path& db){Object out;for(const auto& suffix:{"","-wal","-shm","-journal"}){fs::path p=db.string()+suffix;out[suffix]=fs::exists(p)?Value(fathom::content::sha256(read(p))):Value(nullptr);}return out;}
void codecCases(){
    auto manifest=fathom::json::parse(read(practice/"manifest.json"));
    for(const auto& entry:at(manifest,"fixtures").array()){
        auto name=str(entry,"name"),kind=str(entry,"kind"),bytes=read(practice/str(entry,"path"));
        check("fixture identity "+name,fathom::content::sha256(bytes)==str(entry,"sha256"));bool accepted=true;std::string error;
        try{if(kind=="Envelope")validateEnvelope(bytes);else if(kind=="Checkpoint")validateCheckpoint(str(entry,"owner"),n(at(entry,"generation")),n(at(entry,"sequence")),bytes,str(entry,"kind_argument"),parseCanonical(read(practice/str(entry,"allocated_context"))));else if(kind=="AttemptContext")validateContext(parseCanonical(bytes),"Attempt");else if(kind=="FreeplayContext")validateContext(parseCanonical(bytes),"FreeplayActivity");else parseCanonical(bytes);}catch(const std::exception& e){accepted=false;error=e.what();}
        check("requirement fixture "+name,accepted==(str(entry,"expected")=="accept_structure"),error);
    }
    auto e=validateEnvelope(read(practice/"attempt-valid.json"));check("Stop at exact target retains completed outcome",e.outcome=="complete"&&e.active==fathom::Rational(4));
    auto free=validateEnvelope(read(practice/"freeplay-valid.json"));check("Freeplay retains partial independent activity",free.outcome=="partial"&&free.active==fathom::Rational(3));
    for(const auto& zone:{"UTC","Etc/UTC","US/Eastern","America/New_York"}){check(std::string("IANA alias ")+zone,localDay("2026-09-07T21:00:00Z",zone)=="2026-09-07");}
    for(const auto& zone:{"PST","GMT+0300","../UTC","/UTC","Etc//UTC","Etc/UTC/"})rejects(std::string("invalid zone ")+zone,[&]{localDay("2026-09-07T21:00:00Z",zone);});
    check("fractional UTC ordering",utcBefore("2026-09-07T21:00:00Z","2026-09-07T21:00:00.1Z"));
    auto bad=fixture("attempt-context.json");at(bad,"configuration").object()["bad"]=fathom::json::Number{"NaN"};rejects("mutable Value nonfinite cannot enter allocation",[&]{validateContext(bad,"Attempt");});
    bad=fixture("attempt-context.json");at(bad,"configuration").object()["bad"]=std::string(1024*1024+1,'x');rejects("mutable Value string limit",[&]{validateContext(bad,"Attempt");});
}
void normalCases(){
    auto o=options("normal");std::string before,profile,owner;Value finalState;
    {
        ProfileStore store(o);auto initial=must("initial snapshot",store.snapshot(newUuid()));profile=initial.owner;check("initial receipt zero",n(at(initial.data,"committed_seq"))==0);
        check("SQLite exact runtime",std::string(sqlite3_libversion())=="3.53.4");
        struct stat st{};lstat(o.path.c_str(),&st);check("profile permissions user-only",(st.st_mode&077)==0&&st.st_uid==getuid());
        check("native default path query only",defaultProfilePath().is_absolute()&&defaultProfilePath().filename()=="profile.sqlite");
        rejects("same-process profile excluded",[&]{ProfileLease duplicate(o.path,false);});
        check("separate-process lease excluded",child("lease",o.path,"lease-held")==2);
        auto s=session(store);auto a=allocate(store,s);owner=a.first;auto bytes=envelope(a);
        result("unsealed commit refused",store.commit(newUuid(),owner,bytes),Status::DefiniteFailure);
        result("original absent reconciliation",store.reconcile(newUuid(),owner,bytes),Status::DefinitelyAbsent);
        auto checkpoint=checkpointWith(fixture("checkpoint-normal.json"),owner,a.second);auto cp=canonical(checkpoint);
        must("complete checkpoint saved",store.checkpoint(newUuid(),owner,1,7,cp));
        must("same checkpoint idempotent",store.checkpoint(newUuid(),owner,1,7,cp));
        auto lower=checkpoint;at(lower,"sequence")=num(6);result("stale checkpoint refused",store.checkpoint(newUuid(),owner,1,6,canonical(lower)),Status::DefiniteFailure);
        auto conflict=checkpoint;at(at(conflict,"practice_snapshot"),"uncertain")=true;result("same-position conflicting checkpoint refused",store.checkpoint(newUuid(),owner,1,7,canonical(conflict)),Status::DefiniteFailure);
        auto recovery=must("checkpoint recovery view",store.recoveryState(newUuid(),owner));check("recovery reports stopped only",str(recovery.data,"state")=="checkpoint"&&at(recovery.data,"stopped_on_reopen")==Value(true));
        result("unresolved Session close refused",store.closeSession(newUuid(),s,"2026-09-07T21:01:00Z","complete"),Status::DefiniteFailure);
        must("seal exact original bytes",store.seal(newUuid(),owner,bytes));must("duplicate seal",store.seal(newUuid(),owner,bytes));
        result("pending reconciliation stays unresolved",store.reconcile(newUuid(),owner,bytes),Status::Unresolved);
        auto changed=parseCanonical(bytes);at(at(changed,"result"),"assessment")="Clean";auto changedBytes=canonical(changed);
        result("conflicting pending seal",store.seal(newUuid(),owner,changedBytes),Status::Conflict);
        auto saved=must("atomic final receipt",store.commit(newUuid(),owner,bytes));check("first global receipt",n(at(saved.data,"committed_seq"))==1);
        auto duplicate=must("duplicate final exact receipt",store.commit(newUuid(),owner,bytes));check("no duplicate receipt",duplicate.data==saved.data);
        result("conflicting final visible",store.commit(newUuid(),owner,changedBytes),Status::Conflict);
        result("final supersedes new checkpoint",store.checkpoint(newUuid(),owner,1,7,cp),Status::DefiniteFailure);
        auto resolved=must("final recovery view",store.recoveryState(newUuid(),owner));check("final stopped view",str(resolved.data,"state")=="final");
        must("close settled Session",store.closeSession(newUuid(),s,"2026-09-07T21:01:00Z","complete"));
        result("closed Session rejects new Attempt",store.allocate(newUuid(),"Attempt",a.second,"2026-09-07T21:02:00Z"),Status::DefiniteFailure);
        auto f=allocate(store,"",true);auto fb=envelope(f,true);must("seal Freeplay",store.seal(newUuid(),f.first,fb));must("commit Freeplay",store.commit(newUuid(),f.first,fb));
        auto fact=newUuid();must("explicit Introduced acknowledgment",store.acknowledge(newUuid(),fact,"fg:item:000003",1,"2026-09-07T21:02:00Z"));
        must("duplicate acknowledgment returns receipt",store.acknowledge(newUuid(),fact,"fg:item:000003",1,"2026-09-07T21:02:00Z"));
        result("global UUID collision refuses fact",store.acknowledge(newUuid(),owner,"fg:item:000003",1,"2026-09-07T21:02:00Z"),Status::Conflict);
        auto lateId=newUuid();auto late=canonical(Object{{"original_owner",owner},{"generation",num(1)},{"observation","synthetic delayed confirmation"}});
        must("late evidence original owner",store.appendLate(newUuid(),owner,lateId,"2026-09-07T21:03:00Z",late));
        must("late exact duplicate",store.appendLate(newUuid(),owner,lateId,"2026-09-07T21:03:00Z",late));
        result("late cannot change owner",store.appendLate(newUuid(),f.first,newUuid(),"2026-09-07T21:03:00Z",late),Status::DefiniteFailure);
        auto setting=canonical(Object{{"volume",num(50)}});must("stopped preference initial CAS",store.compareExchangePreferences(newUuid(),"synthetic.settings",1,0,setting,true));
        result("stale preference CAS",store.compareExchangePreferences(newUuid(),"synthetic.settings",1,0,setting,true),Status::Conflict);
        result("running preference refused",store.compareExchangePreferences(newUuid(),"synthetic.settings",1,1,setting,false),Status::DefiniteFailure);
        result("unknown preference namespace",store.compareExchangePreferences(newUuid(),"unknown",1,0,setting,true),Status::Unsupported);
        auto prefs=must("read supported settings",store.readPreferences(newUuid(),"synthetic.settings"));check("preference applicable with registered handler",at(prefs.data,"applicable")==Value(true));
        auto snap=must("snapshot before cache",store.snapshot(newUuid()));auto eh=str(snap.data,"evidence_sha256"),hash=fathom::content::sha256("synthetic content selection");
        must("cache pinned to evidence",store.writeCache(newUuid(),"projection",n(at(snap.data,"committed_seq")),eh,hash,"synthetic.1","2026-09-07T21:03:00Z","{}"));
        must("current cache available",store.readCache(newUuid(),"projection",hash,"synthetic.1","2026-09-07T21:03:00Z"));
        auto observed=must("append rule observation",store.observeRule(newUuid(),newUuid(),Object{{"version","synthetic.1"}},Object{{"content","synthetic"}},Object{{"state","not-learning-proof"}},"2026-09-07T21:03:00Z"));
        (void)observed;auto afterRule=must("snapshot after rule",store.snapshot(newUuid()));check("rule observation excluded from progression hash",str(afterRule.data,"evidence_sha256")==eh);check("rule observation included in full hash",str(afterRule.data,"snapshot_sha256")!=str(snap.data,"snapshot_sha256"));
        must("rule-only history does not invalidate evidence cache",store.readCache(newUuid(),"projection",hash,"synthetic.1","2026-09-07T21:03:00Z"));
        must("change settings without rebinding activity",store.compareExchangePreferences(newUuid(),"synthetic.settings",1,1,canonical(Object{{"volume",num(60)}}),true));
        result("same receipt marker but changed evidence invalidates cache",store.readCache(newUuid(),"projection",hash,"synthetic.1","2026-09-07T21:03:00Z"),Status::DefinitelyAbsent);
        must("old context still reconciles",store.reconcile(newUuid(),owner,bytes));
        finalState=must("final normal snapshot",store.snapshot(newUuid())).data;before=str(finalState,"snapshot_sha256");
        check("three factual global receipts",n(at(finalState,"committed_seq"))==3);
        write(runRoot/"normal-before-reopen.json",canonical(finalState));
    }
    o.create=false;o.preferenceValidator={};
    {ProfileStore reopened(o);auto after=must("normal reopen snapshot",reopened.snapshot(newUuid()));check("normal reopen exact authoritative hash",str(after.data,"snapshot_sha256")==before&&after.owner==profile);auto preference=must("unknown settings retained on reopen",reopened.readPreferences(newUuid(),"synthetic.settings"));check("unknown setting not applicable",at(preference.data,"applicable")==Value(false));}
    check("separate-process normal reopen",child("snapshot",o.path,"normal-process-reopen")==0);
    auto raw=read(runRoot/"normal-process-reopen.log");auto start=raw.find('{');auto finish=raw.rfind('}');if(start!=std::string::npos&&finish!=std::string::npos){auto record=fathom::json::parse(raw.substr(start,finish-start+1));check("separate-process exact history",str(at(record,"data"),"snapshot_sha256")==before);}else check("separate-process snapshot record",false,raw);
    check("lease released after store join",child("lease",o.path,"lease-released")==0);
}
void failureCases(){
    std::atomic<int> commitCount{0};auto o=options("transaction-faults");
    o.diagnosticHook=[&](const std::string& phase,const std::string& op){if(phase=="before_commit"&&op=="precommit-failure")throw std::runtime_error("controlled precommit exception");if(phase=="after_commit"&&op=="lost-ack"){++commitCount;throw std::runtime_error("controlled lost acknowledgment after commit");}if(phase=="after_commit"&&op=="nonstd-lost-ack")throw 7;if(phase=="before_commit"&&op=="delayed-original")std::this_thread::sleep_for(std::chrono::milliseconds(1150));};
    ProfileStore store(o);auto lostSession=result("nonstd acknowledgment remains unresolved",store.createSession("nonstd-lost-ack","2026-09-07T21:00:00Z","UTC"),Status::Unresolved);check("allocated owner survives unknown acknowledgment exception",!lostSession.owner.empty()&&lostSession.operation=="nonstd-lost-ack");auto s=session(store);auto a=allocate(store,s);auto bytes=envelope(a);
    result("precommit rollback visible",store.seal("precommit-failure",a.first,bytes),Status::DefiniteFailure);
    result("rolled back seal absent",store.reconcile(newUuid(),a.first,bytes),Status::DefinitelyAbsent);
    must("seal after confirmed rollback",store.seal(newUuid(),a.first,bytes));
    result("commit acknowledgment lost",store.commit("lost-ack",a.first,bytes),Status::Unresolved);
    auto reconciled=must("original key reconciles lost acknowledgment",store.reconcile(newUuid(),a.first,bytes));
    check("lost acknowledgment never auto-retried",commitCount==1&&n(at(reconciled.data,"committed_seq"))==1);
    auto next=allocate(store,s);auto nextBytes=envelope(next);auto future=store.seal("delayed-original",next.first,nextBytes);
    auto timeout=ProfileStore::waitForAcknowledgment(future);check("timeout keeps immutable operation/owner",timeout.status==Status::Unresolved&&timeout.operation=="delayed-original"&&timeout.owner==next.first&&future.valid());
    auto delayed=future.get();check("late result remains original owner",delayed.status==Status::Confirmed&&delayed.operation==timeout.operation&&delayed.owner==timeout.owner);
    result("late seal pending remains unresolved",store.reconcile(newUuid(),next.first,nextBytes),Status::Unresolved);
    must("confirmed persistence before another attempt path",store.commit(newUuid(),next.first,nextBytes));
    must("fault profile still validates",store.snapshot(newUuid()));
}
void queueCases(){
    std::mutex mutex;std::condition_variable cv;bool entered=false,released=false;
    auto o=options("queue");o.diagnosticHook=[&](const std::string& phase,const std::string& op){if(phase=="before_operation"&&op=="hold"){std::unique_lock<std::mutex> lock(mutex);entered=true;cv.notify_all();cv.wait(lock,[&]{return released;});}};
    ProfileStore store(o);auto s=session(store);auto a=allocate(store,s);auto hold=store.snapshot("hold");{std::unique_lock<std::mutex> lock(mutex);if(!cv.wait_for(lock,std::chrono::seconds(2),[&]{return entered;}))throw std::runtime_error("queue hook not entered");}
    auto cp=canonical(checkpointWith(fixture("checkpoint-normal.json"),a.first,a.second));
    auto first=store.checkpoint("checkpoint-first",a.first,1,7,cp);
    auto second=store.checkpoint("checkpoint-deferred",a.first,1,7,cp);auto deferred=second.get();check("one queued checkpoint per owner explicit Busy",deferred.status==Status::Busy&&deferred.operation=="checkpoint-deferred");
    auto bytes=envelope(a);auto seal=store.seal("queued-seal",a.first,bytes);auto commit=store.commit("queued-commit",a.first,bytes);
    std::vector<ProfileStore::Future> futures;for(int i=0;i<61;++i)futures.push_back(store.readPreferences("queued-read-"+std::to_string(i),"missing"));
    auto over=store.snapshot("queue-overflow").get();check("queue64 admission refuses excess",over.status==Status::Busy);
    {std::lock_guard<std::mutex> lock(mutex);released=true;}cv.notify_all();
    check("held operation completes",hold.get().status==Status::Confirmed);check("checkpoint before seal preserved",first.get().status==Status::Confirmed);check("queued seal not dropped",seal.get().status==Status::Confirmed);check("queued commit not reordered",commit.get().status==Status::Confirmed);
    bool all=true;for(auto& f:futures)all=all&&f.get().status==Status::DefinitelyAbsent;check("all61 accepted reads completed",all);
}
void sourceCases(){
    const auto manifest=fathom::json::parse(read(source/"manifest.json"));
    const auto standalone=parseCanonical(read(source/"standalone-context.json"));
    reviewer::synthetic::L105SourceHandler handler(read(source/"historical-l105-authority.json"),standalone);
    for(const auto& entry:at(manifest,"fixtures").array()){
        auto bytes=read(source/str(entry,"path"));check("source fixture identity "+str(entry,"path"),fathom::content::sha256(bytes)==str(entry,"sha256"));
        auto v=parseCanonical(bytes);std::optional<Value> linked;if(!at(entry,"linked_context").null())linked=parseCanonical(read(source/at(entry,"linked_context").string()));bool okay=true;try{validateAttestation(v,str(manifest,"profile_id"),linked);}catch(...){okay=false;}
        check("source structure "+str(entry,"path"),okay==(str(entry,"structural_expected")=="accept"));
        if(okay)check("source semantics "+str(entry,"path"),handler(v)==(str(entry,"semantic_expected")=="accept"));
    }
    auto o=options("source-facts");o.sourceValidator=handler;std::string profile,before;
    {
        ProfileStore store(o);profile=must("source profile identity",store.snapshot(newUuid())).owner;
        auto adapt=[&](const std::string& file){auto v=parseCanonical(read(source/file));at(v,"performer_ref")=profile;at(at(v,"attestation"),"performer_ref")=profile;if(str(at(v,"attestation"),"role")=="learner")at(at(v,"attestation"),"who")=profile;return v;};
        auto learner=adapt("standalone-learner.json");auto bytes=canonical(learner);
        auto first=must("store actual-work synthetic attestation",store.attest(newUuid(),bytes));
        auto repeated=must("exact source fact duplicate",store.attest(newUuid(),bytes));check("source duplicate receipt",repeated.data==first.data);
        auto conflict=learner;at(at(conflict,"attestation"),"actual_work")=false;
        result("malformed same-fact cannot overwrite",store.attest(newUuid(),canonical(conflict)),Status::DefiniteFailure);
        conflict=adapt("conflict-same-fact-changed-bytes.json");result("valid conflicting same-fact refused",store.attest(newUuid(),canonical(conflict)),Status::Conflict);
        must("same-take independent review appends",store.attest(newUuid(),canonical(adapt("standalone-same-take-review.json"))));
        must("incomplete actual work retained",store.attest(newUuid(),canonical(adapt("standalone-incomplete-work.json"))));
        must("protected-zero valid work retained without completion verdict",store.attest(newUuid(),canonical(adapt("standalone-protected-zero.json"))));
        auto bad=adapt("reject-score-boolean.json");at(bad,"fact_id")=newUuid();result("new malformed source score refused by registered handler",store.attest(newUuid(),canonical(bad)),Status::Unsupported);
        auto s=session(store);auto c=parseCanonical(read(source/"linked-attempt-context.json"));at(c,"session_id")=s;auto allocated=must("allocate linked context",store.allocate(newUuid(),"Attempt",c,"2026-09-07T21:05:00Z"));
        auto linked=adapt("linked-same-take-review.json");at(linked,"owner")=allocated.owner;at(linked,"fact_id")=newUuid();must("linked exact historical context stores",store.attest(newUuid(),canonical(linked)));
        auto wrong=linked;at(wrong,"fact_id")=newUuid();at(at(at(wrong,"context"),"configuration"),"values").object()["tempo"]=num(61);result("linked changed context refused",store.attest(newUuid(),canonical(wrong)),Status::DefiniteFailure);
        auto snapshot=must("source store complete inspection",store.snapshot(newUuid()));check("five source facts share receipt sequence",n(at(snapshot.data,"committed_seq"))==5);before=str(snapshot.data,"snapshot_sha256");
        write(runRoot/"source-before-reopen.json",canonical(snapshot.data));
    }
    o.create=false;o.sourceValidator={};
    {ProfileStore reopened(o);auto r=must("historical source readable without present authority handler",reopened.snapshot(newUuid()));check("missing current content never rekeys source history",str(r.data,"snapshot_sha256")==before);auto v=parseCanonical(read(source/"standalone-learner.json"));at(v,"fact_id")=newUuid();at(v,"performer_ref")=profile;at(at(v,"attestation"),"performer_ref")=profile;at(at(v,"attestation"),"who")=profile;result("missing handler cannot admit new source claim",reopened.attest(newUuid(),canonical(v)),Status::Unsupported);}
}
void busyCases(){
    auto o=options("busy");ProfileStore store(o);auto s=session(store);auto a=allocate(store,s);auto bytes=envelope(a);
    {Sql blocker(o.path);blocker.exec("BEGIN IMMEDIATE");auto started=std::chrono::steady_clock::now();auto r=result("confirmed SQLite BUSY bounded",store.seal("held-sqlite-writer",a.first,bytes),Status::Busy);auto elapsed=std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count();check("BUSY wait finite and diagnostic retained",elapsed>=700&&elapsed<3000&&r.code=="SQL_BUSY",std::to_string(elapsed)+"ms available component observation, not power-loss qualification");blocker.exec("ROLLBACK");}
    result("failed seal remains absent",store.reconcile(newUuid(),a.first,bytes),Status::DefinitelyAbsent);
    result("Again cannot allocate over unresolved original",store.allocate(newUuid(),"Attempt",a.second,"2026-09-07T21:01:00Z"),Status::Unresolved);
    auto free=fixture("freeplay-context.json");result("mode switch cannot abandon original",store.allocate(newUuid(),"FreeplayActivity",free,"2026-09-07T21:01:00Z"),Status::Unresolved);
    must("seal after BUSY clears",store.seal(newUuid(),a.first,bytes));must("commit after BUSY clears",store.commit(newUuid(),a.first,bytes));
    auto snapshot=must("busy path retains only one result",store.snapshot(newUuid()));check("no duplicate from confirmed retries",n(at(snapshot.data,"committed_seq"))==1);
}

std::string hexBytes(const std::string& bytes){const char* h="0123456789abcdef";std::string out;for(unsigned char c:bytes){out+=h[c>>4];out+=h[c&15];}return out;}
void pendingCases(){
    auto o=options("pending-reopen");std::string owner,bytes;
    {
        ProfileStore store(o);auto s=session(store);auto a=allocate(store,s);owner=a.first;bytes=envelope(a);auto v=checkpointWith(fixture("checkpoint-pending.json"),owner,a.second);
        auto raw=canonical(at(parseCanonical(bytes),"result"));at(at(v,"practice_snapshot"),"pending")=Object{{"key",owner},{"payload",raw},{"digest",fathom::content::sha256(raw)}};
        at(v,"sealed_envelope")=Object{{"bytes_hex",hexBytes(bytes)},{"sha256",fathom::content::sha256(bytes)}};
        must("pending full original checkpoint",store.checkpoint(newUuid(),owner,2,8,canonical(v)));
        auto checkpoint=must("lone pending snapshot report",store.recoveryState(newUuid(),owner));check("lone snapshot stays checkpoint until sealed in store",str(checkpoint.data,"state")=="checkpoint");
        must("seal retained original after checkpoint",store.seal(newUuid(),owner,bytes));auto pending=must("pending outranks checkpoint",store.recoveryState(newUuid(),owner));check("pending bytes preserved",str(pending.data,"state")=="pending"&&str(pending.data,"payload")==bytes);
    }
    o.create=false;{
        ProfileStore reopened(o);auto state=must("pending survives normal reopen",reopened.recoveryState(newUuid(),owner));check("reopen retains original bytes stopped",str(state.data,"payload")==bytes&&at(state.data,"stopped_on_reopen")==Value(true));
        result("reopened pending reconciliation",reopened.reconcile(newUuid(),owner,bytes),Status::Unresolved);must("commit original reopened pending",reopened.commit(newUuid(),owner,bytes));auto snap=must("reopened final inspection",reopened.snapshot(newUuid()));check("one final receipt after pending reopen",n(at(snap.data,"committed_seq"))==1);
        const auto& policy=at(snap.data,"connection_policy");check("accepted live connection policies",str(policy,"journal_mode")=="wal"&&n(at(policy,"synchronous"))==2&&n(at(policy,"fullfsync"))==1&&n(at(policy,"checkpoint_fullfsync"))==1&&n(at(policy,"foreign_keys"))==1&&n(at(policy,"busy_timeout"))==250&&n(at(policy,"wal_autocheckpoint"))==1000&&n(at(policy,"journal_size_limit"))==8388608&&n(at(policy,"cache_size"))==-8192);
    }
}
void sidecarCases(){
    for(const auto& suffix:{"-wal","-shm","-journal"}){
        auto o=options(std::string("orphan")+suffix);{ProfileStore store(o);must(std::string("seed orphan")+suffix,store.snapshot(newUuid()));}write(o.path.string()+suffix,"");chmod((o.path.string()+suffix).c_str(),0600);auto before=fileHashes(o.path);o.create=false;rejects(std::string("orphan present even zero")+suffix,[&]{ProfileStore rejected(o);});check(std::string("orphan preserved")+suffix,fileHashes(o.path)==before);
    }
    auto seed=options("wal-seed");{ProfileStore store(seed);must("seed paired WAL test",store.snapshot(newUuid()));}
    auto pair=options("wal-pair"),bad=options("wal-pair-rejected");fs::create_directories(pair.path.parent_path());fs::create_directories(bad.path.parent_path());chmod(pair.path.parent_path().c_str(),0700);chmod(bad.path.parent_path().c_str(),0700);
    {
        Sql sql(seed.path);sql.exec("PRAGMA wal_autocheckpoint=0; INSERT INTO preferences VALUES('synthetic.settings',1,1,CAST('{\"from\":\"WAL\"}' AS BLOB))");
        for(const auto& suffix:{"","-wal","-shm"}){auto from=fs::path(seed.path.string()+suffix);check(std::string("actual WAL fixture exists")+suffix,fs::exists(from));fs::copy_file(from,pair.path.string()+suffix);fs::copy_file(from,bad.path.string()+suffix);chmod((pair.path.string()+suffix).c_str(),0600);chmod((bad.path.string()+suffix).c_str(),0600);}
    }
    pair.create=false;{ProfileStore store(pair);auto preference=must("production inspection consumes committed WAL",store.readPreferences(newUuid(),"synthetic.settings"));check("WAL-only preference visible",str(preference.data,"bytes")=="{\"from\":\"WAL\"}");}
    // Controlled malformed main-header identity with actual retained sidecars; no ignored WAL.
    {std::fstream db(bad.path,std::ios::in|std::ios::out|std::ios::binary);db.seekp(0);db.write("X",1);}
    auto before=fileHashes(bad.path);bad.create=false;rejects("paired WAL malformed main refused",[&]{ProfileStore rejected(bad);});check("paired WAL SHM DB rejected bytes intact",fileHashes(bad.path)==before);
}
void corruptRelations(){
    for(const auto& change:std::vector<std::pair<std::string,std::string>>{{"summary","UPDATE finalized SET active_num='999'"},{"digest","UPDATE finalized SET digest='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'"},{"receipt-gap","UPDATE finalized SET committed_seq=2;UPDATE metadata SET value='2' WHERE key='committed_seq'"}}){
        auto o=options("relation-"+change.first);{ProfileStore store(o);auto s=session(store);auto a=allocate(store,s);auto bytes=envelope(a);must("relation seal",store.seal(newUuid(),a.first,bytes));must("relation commit",store.commit(newUuid(),a.first,bytes));}
        {Sql sql(o.path);auto trigger=sql.text("SELECT sql FROM sqlite_schema WHERE name='final_no_update'");sql.exec("DROP TRIGGER final_no_update;"+change.second+";"+trigger);}
        auto before=fileHashes(o.path);o.create=false;rejects("typed authoritative corruption "+change.first,[&]{ProfileStore rejected(o);});check("authoritative original retained "+change.first,fileHashes(o.path)==before);
    }
    auto o=options("cache-corruption");ProfileStore store(o);auto snap=must("cache baseline",store.snapshot(newUuid()));auto hash=fathom::content::sha256("synthetic");must("cache baseline insert",store.writeCache(newUuid(),"cached",0,str(snap.data,"evidence_sha256"),hash,"synthetic.1","2026-09-07T21:00:00Z","{}"));
    {Sql sql(o.path);sql.exec("UPDATE projection_cache SET value_bytes=CAST('{invalid' AS BLOB)");}
    result("malformed cache is disposable",store.readCache(newUuid(),"cached",hash,"synthetic.1","2026-09-07T21:00:00Z"),Status::DefinitelyAbsent);
    {Sql sql(o.path);sql.exec("UPDATE metadata SET value='abc' WHERE key='committed_seq'");}
    result("authoritative corruption never a cache miss",store.readCache(newUuid(),"cached",hash,"synthetic.1","2026-09-07T21:00:00Z"),Status::DefiniteFailure);
}
void backpressureCases(){
    auto o=options("wal-pressure");ProfileStore store(o);std::uintmax_t size=0;int writes=0;
    {
        Sql reader(o.path);reader.exec("BEGIN");reader.text("SELECT value FROM metadata WHERE key='committed_seq'");
        // Finite predeclared workload: at most80 settings writes, each900000-character
        // synthetic value below the1MiB string bound, with a reader pinning WAL.
        for(int i=0;i<80&&size<64u*1024u*1024u;++i){auto bytes=canonical(Object{{"padding",std::string(900000,static_cast<char>('a'+i%26))},{"serial",num(i)}});auto r=store.compareExchangePreferences("pressure-"+std::to_string(i),"synthetic.settings",1,i,bytes,true).get();if(r.status!=Status::Confirmed)throw std::runtime_error("pressure fixture write failed "+r.message);++writes;size=fs::file_size(o.path.string()+"-wal");}
        check("finite workload reaches accepted64MiB WAL bound",size>=64u*1024u*1024u,"writes="+std::to_string(writes)+" bytes="+std::to_string(size));
        result("WAL pressure refuses new Session admission",store.createSession(newUuid(),"2026-09-07T21:00:00Z","UTC"),Status::Busy);
        auto c=fixture("freeplay-context.json");result("WAL pressure refuses new activity admission",store.allocate(newUuid(),"FreeplayActivity",c,"2026-09-07T21:00:00Z"),Status::Busy);
        reader.exec("ROLLBACK");
    }
    auto snap=must("pressure never deletes authoritative state",store.snapshot(newUuid()));check("pressure creates no practice receipt",n(at(snap.data,"committed_seq"))==0);
}

void rejectionCases(){
    for(const auto& change:std::vector<std::pair<std::string,std::string>>{{"newer","PRAGMA user_version=2"},{"wrong","PRAGMA application_id=1"},{"marker","UPDATE metadata SET value='9223372036854775807' WHERE key='committed_seq'"},{"trigger","DROP TRIGGER final_no_delete"},{"profile-date","DROP TRIGGER profile_no_update; UPDATE profile SET created_utc='not-a-date'"}}){
        auto o=options("reject-"+change.first);{ProfileStore store(o);must("seed rejection "+change.first,store.snapshot(newUuid()));}{Sql sql(o.path);sql.exec(change.second);}auto before=fileHashes(o.path);o.create=false;rejects("intact refusal "+change.first,[&]{ProfileStore rejected(o);});check("rejected file bytes preserved "+change.first,fileHashes(o.path)==before);
    }
    auto o=options("unsafe-lock");fs::create_directories(o.path.parent_path());chmod(o.path.parent_path().c_str(),0700);auto lock=o.path.parent_path()/".profile.lock";mkfifo(lock.c_str(),0600);auto start=std::chrono::steady_clock::now();rejects("special lock refused before open",[&]{ProfileLease lease(o.path,false);});check("special lock refusal bounded",std::chrono::steady_clock::now()-start<std::chrono::seconds(1));
}
}
int main(int argc,char** argv){
    if(argc!=6&&argc!=7){std::cerr<<"Usage: tests E run-name practice-fixtures source-fixtures process-helper [group]\n";return 64;}
    try{
        evidence=fs::canonical(argv[1]);std::string name=argv[2];if(name.empty()||name.find('/')!=std::string::npos||name=="."||name=="..")throw std::runtime_error("Invalid run directory");runRoot=evidence/"test-data"/name;if(fs::exists(runRoot))throw std::runtime_error("Never overwrite previous test run");fs::create_directories(runRoot);practice=fs::canonical(argv[3]);source=fs::canonical(argv[4]);process=fs::canonical(argv[5]);
        for(const auto& group:std::vector<std::pair<std::string,std::function<void()>>>{{"codec",codecCases},{"normal",normalCases},{"faults",failureCases},{"queue",queueCases},{"source",sourceCases},{"busy",busyCases},{"rejection",rejectionCases},{"pending",pendingCases},{"sidecars",sidecarCases},{"corrupt",corruptRelations},{"pressure",backpressureCases}}){if(argc==7&&std::string(argv[6]).find(group.first)==std::string::npos)continue;try{group.second();}catch(const std::exception& e){check("group "+group.first+" completed",false,e.what());}}
        write(runRoot/"checks.json",canonical(Object{{"synthetic",true},{"production_store",true},{"actual_human_work",false},{"checks",checks},{"failures",num(failures)},{"commands",commands}}));
        std::cout<<"Checks "<<checks.size()<<", failures "<<failures<<'\n';return failures?1:0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
