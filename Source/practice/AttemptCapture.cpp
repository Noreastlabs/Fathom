#include "practice/AttemptCapture.hpp"
#include "content/Canonical.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "progression/Progression.hpp"
#include "storage/Recovery.hpp"
#include <algorithm>
#include <limits>
#include <numeric>

namespace fathom::capture {
namespace {
using A=Value::Array; using O=Value::Object;
void need(bool b,const char* why) { if(!b) throw storage::EnvelopeError("CAPTURE_BINDING",why); }
const Value& at(const Value& v,const char* k) { auto p=v.find(k);need(p,"Missing original capture field");return *p; }
std::int64_t narrow(std::uint64_t n) { need(n<=INT64_MAX,"Transport value exceeds supported storage integer; retain original facts");return static_cast<std::int64_t>(n); }
Value num(std::uint64_t n) { return Value::fromInteger(narrow(n)); }
Value q(const Rational& n,bool strings=false) {
    if(strings)return A{std::to_string(n.numerator()),std::to_string(n.denominator())};
    return A{Value::fromInteger(n.numerator()),Value::fromInteger(n.denominator())};
}
Rational seconds(std::uint64_t frames,std::uint32_t rate) { return Rational{narrow(frames),static_cast<std::int64_t>(rate)}; }
std::string uuid(const scheduler::Owner& owner) {
    const char* h="0123456789abcdef";std::string s;
    for(std::size_t i=0;i<16;++i){if(i==4||i==6||i==8||i==10)s+='-';s+=h[owner.id[i]>>4];s+=h[owner.id[i]&15];}return s;
}
const char* unit(scheduler::BeatUnit u) {
    switch(u){case scheduler::BeatUnit::Eighth:return "eighth";case scheduler::BeatUnit::Quarter:return "quarter";
    case scheduler::BeatUnit::DottedQuarter:return "dotted_quarter";case scheduler::BeatUnit::Half:return "half";}
    throw storage::EnvelopeError("CAPTURE_UNIT","Unsupported beat unit");
}
const char* state(practice::State s) {
    switch(s){case practice::State::Stopped:return "STOPPED";case practice::State::CountIn:return "COUNT_IN";case practice::State::Running:return "RUNNING";
    case practice::State::Paused:return "PAUSED";case practice::State::Ended:return "ENDED";case practice::State::Error:return "ERROR";}
    throw storage::EnvelopeError("CAPTURE_STATE","Unsupported state");
}
const char* outcome(Outcome o) {
    switch(o){case Outcome::Stop:return "stop";case Outcome::Natural:return "natural";case Outcome::InterruptedError:return "interrupted_error";}
    throw storage::EnvelopeError("CAPTURE_OUTCOME","Unsupported outcome");
}
void assessment(const practice::Coordinator& c,const Value& a) {
    if(a.null())return;
    need(c.state()==practice::State::Ended||c.state()==practice::State::Error,"Stop or finish before explicit self-assessment");
    need(a.isString()&&(a.string()=="Struggling"||a.string()=="Developing"||a.string()=="Clean"||a.string()=="Easy"),"Choose an explicit supported self-assessment or leave it absent");
}
void finalState(const practice::Coordinator& c,Outcome o) {
    need(c.state()==practice::State::Ended||c.state()==practice::State::Error,"Stop or finish before finalizing actual facts");
    bool establishedEnded=false;
    for(const auto& p:c.generations())if(p.owner==c.owner()&&p.state==practice::State::Ended&&p.terminal&&!p.fault)establishedEnded=true;
    for(const auto& p:c.lateEvidence())if(p.owner.id==c.owner().id&&p.dispositionSequence&&p.state==practice::State::Ended)establishedEnded=true;
    if(c.state()==practice::State::Error&&!establishedEnded)
        need(o==Outcome::InterruptedError,"An active interruption must retain its interrupted-error outcome");
    else need(o!=Outcome::InterruptedError,"Retain the established Stop/Natural outcome independently of the later error stage");
    if(o==Outcome::Natural)need(c.completedCycles()==c.configuration().targetCycles,"Natural target has not completed");
}
Value contentBinding(const Binding& b) {
    if(b.kind=="FreeplayActivity"){need(b.sourceHashes.null(),"Freeplay cannot carry curriculum source hashes");return nullptr;}
    O o{{"id",at(b.context,"item_id")},{"source_hashes",b.sourceHashes}};
    for(auto k:{"content_revision","content_version","source_manifest_sha256","source_refs"})o.emplace(k,at(b.context,k));
    return o;
}
void validateBinding(const practice::Coordinator& c,const Binding& b) {
    storage::validateUuid(b.owner);validateContext(b,c.configuration());
    need(c.originalKey()==b.owner&&c.context()==storage::canonical(b.context),"Capture differs from original allocated owner/context");
    need(b.kind==(c.kind()==practice::Kind::Attempt?"Attempt":"FreeplayActivity"),"Attempt and Freeplay cannot exchange ownership");
}
void contextRules(const Binding& b,const practice::Configuration& cfg) {
    storage::validateContext(b.context,b.kind);
    need(at(b.context,"configuration_version")==num(1),"Unsupported capture configuration version");
    need(at(at(b.context,"configuration"),"values")==configurationValues(cfg),"Pinned runtime configuration differs from transport");
    at(at(b.context,"configuration"),"authored_tempo_ref"); // null is explicit; missing is not an inference
    const auto& conf=at(b.context,"configuration");
    Rational beat{1};switch(cfg.unit){case scheduler::BeatUnit::Eighth:beat=Rational{1,2};break;
        case scheduler::BeatUnit::DottedQuarter:beat=Rational{3,2};break;case scheduler::BeatUnit::Half:beat=Rational{2};break;case scheduler::BeatUnit::Quarter:break;}
    need(at(conf,"beat_reference_q")==q(beat),"Pinned beat reference differs from actual transport unit");
    if(b.kind=="Attempt"){
        need(at(conf,"source_hashes")==b.sourceHashes,"Capture source hashes differ from original allocated configuration");
        const auto& refs=at(b.context,"source_refs").array();
        need(b.sourceHashes.isObject()&&b.sourceHashes.object().size()==refs.size(),"Source hash coverage differs from original references");
        for(const auto& ref:refs){const auto* hash=b.sourceHashes.find(ref.string());
            need(hash&&hash->isString()&&hash->string().size()==64&&std::all_of(hash->string().begin(),hash->string().end(),[](char ch){return (ch>='0'&&ch<='9')||(ch>='a'&&ch<='f');}),"Original source reference requires its exact SHA-256");}
        if(const auto* condition=conf.find("progression_condition")){
            progression::validateCondition(*condition);
            for(auto pair:{std::pair{"variant","variant_id"},std::pair{"revision","content_revision"},
                           std::pair{"content_version","content_version"},std::pair{"span","span"},std::pair{"target","target"}})
                need(at(*condition,pair.first)==at(b.context,pair.second),"Progression condition differs from original allocated content/span/target");
            need(at(*condition,"beat_unit")==Value(unit(cfg.unit)),"Progression beat unit differs from actual transport");
        }
        const auto origin=progression::quantity(at(at(b.context,"span"),"start"));
        need(at(at(b.context,"span"),"end")==q(origin+cfg.span),"Original source interval differs from the pinned local transport length");
        need(at(at(b.context,"target"),"cycles")==num(cfg.targetCycles),"Original target differs from transport");
    }else need(b.sourceHashes.null(),"Freeplay cannot carry curriculum source hashes");
    storage::validateUtc(b.practiceUtc);storage::localDay(b.practiceUtc,b.timezone);
}
// Inverse sample mapping is a quantized cursor, never a new authored boundary.
// Its raw frames are retained separately. Complete traversals use source extent.
Rational cursor(const practice::Configuration& c,std::uint64_t frames,std::uint16_t bpm) {
    if(!frames)return Rational{};
    std::int64_t beatN=1,beatD=1;
    switch(c.unit){case scheduler::BeatUnit::Eighth:beatD=2;break;
        case scheduler::BeatUnit::DottedQuarter:beatN=3;beatD=2;break;
        case scheduler::BeatUnit::Half:beatN=2;break;case scheduler::BeatUnit::Quarter:break;}
    // frames is64-bit, BPM<=300 and the beat numerator<=3; this bounded
    // product fits128 bits without multiplying arbitrary structural rationals.
    __int128 n=static_cast<__int128>(frames)*bpm*beatN;
    __int128 d=static_cast<__int128>(c.rate)*60*beatD;
    auto gcd=[](__int128 a,__int128 b){while(b){auto r=a%b;a=b;b=r;}return a;};const auto g=gcd(n,d);n/=g;d/=g;
    need(n<=INT64_MAX&&d<=INT64_MAX,"Cursor mapping exceeds supported rational");
    const Rational position{static_cast<std::int64_t>(n),static_cast<std::int64_t>(d)};
    return c.span<position?c.span:position;
}
struct Ledger { A intervals,completed,traversals,interruptions,segments;Value live=nullptr;Rational active,cursor; };
Ledger ledger(const practice::Coordinator& c,const Binding& b) {
    Ledger l;std::uint64_t ordinal=0;const auto& cfg=c.configuration();
    const auto origin=b.kind=="Attempt"?progression::quantity(at(at(b.context,"span"),"start")):Rational{};
    l.cursor=origin;
    for(const auto& p:c.generations()) {
        need(p.owner.id==c.owner().id,"Generation changed original owner");
        const auto& map=c.timeline(p.owner);
        const auto active=seconds(p.activeFrames,cfg.rate);
        if(p.activeFrames){
            need(p.clientAcceptedThrough>=p.activeFrames,"Invalid accepted interval");
            l.intervals.emplace_back(O{{"id","confirmed-prefix"},{"generation",num(p.owner.generation)},
                {"start",q(seconds(p.clientAcceptedThrough-p.activeFrames,cfg.rate))},{"end",q(seconds(p.clientAcceptedThrough,cfg.rate))}});
            Rational consumed;
            for(const auto& part:map.slices(p.clientAcceptedThrough)){
                const auto duration=seconds(part.end-part.begin,cfg.rate);
                l.segments.emplace_back(O{{"tempo",q(Rational{static_cast<std::int64_t>(part.bpm)})},{"start_at",q(l.active+consumed)},
                    {"end_at",q(l.active+consumed+duration)},{"confirmed_duration",q(duration)}});
                consumed=consumed+duration;
            }
            need(consumed==active,"Tempo segments differ from the accepted active prefix");
            l.active=l.active+active;
        }
        for(std::uint64_t i=0;i<p.completedCycles;++i){need(ordinal<INT64_MAX,"Cycle ordinal overflow");++ordinal;l.completed.push_back(num(ordinal));
            l.traversals.emplace_back(O{{"cycle",num(ordinal)},{"start",q(origin)},{"end",q(origin+cfg.span)},{"status","complete"}});}
        const auto position=origin+cursor(cfg,p.cursorFrames,map.acceptedTempo(p.clientAcceptedThrough));
        if(p.cursorFrames){
            const bool live=p.owner==c.owner()&&!p.terminal&&c.state()!=practice::State::Ended&&c.state()!=practice::State::Error;
            Value t=O{{"cycle",num(ordinal+1)},{"start",q(origin)},{"end",q(position)},
                {"status",live?"running":p.state==practice::State::Paused?"partial_interrupted":"partial_ended"}};
            if(live)l.live=t;else l.traversals.push_back(t);
        }
        if(p.owner==c.owner())l.cursor=position;
        // Every generation retains its exact output facts, including pre-roll
        // cancellation and natural stop. This is not a performed-take assertion.
        auto raw=lateEvidence(p);raw.object()["kind"]="transport_generation";
        raw.object()["quantized_cursor_quarters"]=q(position);raw.object()["resume_boundary_quarters"]=q(origin);
        if(map.points().size()>1 || map.spec().initialBpm!=cfg.bpm){
            A points;
            for(const auto& point:map.points()){const auto exact=point.anchor.exact();points.push_back(O{{"cycle",num(point.cycle)},{"bpm",num(point.bpm)},
                {"anchor_samples",A{exact[0],exact[1]}}});}
            raw.object()["tempo_timeline"]=O{{"version","practice-tempo.1"},{"points",points}};
        }
        l.interruptions.push_back(std::move(raw));
    }
    for(const auto& p:c.lateEvidence())if(p.owner.id==c.owner().id&&p.dispositionSequence){
        auto marker=lateEvidence(p);marker.object()["kind"]="transport_disposition";l.interruptions.push_back(std::move(marker));
    }
    need(l.active==seconds(c.activeFrames(),cfg.rate)&&ordinal==c.completedCycles(),"Capture totals differ from authoritative transport");
    return l;
}
Value practiceMetadata(const Binding& b,const Rational& active){return O{{"practice_utc",b.practiceUtc},{"timezone",b.timezone},
    {"local_day",storage::localDay(b.practiceUtc,b.timezone)},{"active_seconds",q(active,true)}};}
std::string hex(const std::string& s){const char* h="0123456789abcdef";std::string out;out.reserve(s.size()*2);for(unsigned char c:s){out+=h[c>>4];out+=h[c&15];}return out;}
bool finalReceipt(const storage::Reply& r,const storage::Envelope& e) {
    if(r.status!=storage::Status::Confirmed||r.owner!=e.owner||!r.data.isObject())return false;
    auto p=r.data.find("payload"),d=r.data.find("digest"),s=r.data.find("committed_seq");std::int64_t seq{};
    return p&&d&&s&&*p==Value(e.bytes)&&*d==Value(e.digest)&&s->integer(seq)&&seq>0;
}
}
void validateContext(const Binding& b,const practice::Configuration& cfg){contextRules(b,cfg);}
Value configurationValues(const practice::Configuration& c) {
    practice::countInSpan(c);
    Value meter=nullptr;if(c.meter)meter=A{Value::fromInteger(c.meter->first),Value::fromInteger(c.meter->second)};
    return O{{"span",q(c.span)},{"rate",num(c.rate)},{"selected_bpm",num(c.bpm)},{"beat_unit",unit(c.unit)},
        {"count_in",c.countIn==practice::CountIn::Off?"off":"authored_bar"},{"meter",meter},
        {"target_cycles",num(c.targetCycles)},{"faithful_whole_span",c.faithfulWholeSpan},{"source_requires_count_in",c.sourceRequiresCountIn}};
}
Value lateEvidence(const practice::Progress& p) {
    need(p.owner.valid(),"Late evidence requires its original owner");storage::validateUuid(uuid(p.owner));
    return O{{"original_owner",uuid(p.owner)},{"generation",num(p.owner.generation)},{"epoch",std::to_string(p.owner.epoch)},
        {"kind","transport_late"},{"sequence",std::to_string(p.sequence)},{"disposition_sequence",std::to_string(p.dispositionSequence)},
        {"state",state(p.state)},{"client_accepted_frames",std::to_string(p.clientAcceptedThrough)},
        {"scheduled_frames",std::to_string(p.scheduledThrough)},{"active_frames",std::to_string(p.activeFrames)},
        {"completed_cycles_local",std::to_string(p.completedCycles)},{"cursor_frames",std::to_string(p.cursorFrames)},
        {"requested_stop_ns",std::to_string(p.requestedStopNs)},{"uncertain_through",std::to_string(p.uncertainThrough)},
        {"has_physical_confirmation",p.hasPhysicalConfirmation},{"physical_confirmed_frames",std::to_string(p.physicalConfirmedThrough)},
        {"terminal",p.terminal},{"partial",p.partial},{"fault",p.fault}};
}
Value lateEvidence(const practice::Progress& p,const practice::Timeline& map) {
    need(p.owner==map.spec().owner,"Late tempo map belongs to another original generation");
    (void)map.completed(p.clientAcceptedThrough);
    auto raw=lateEvidence(p);const auto& spec=map.spec();A points;
    for(const auto& point:map.points()){const auto exact=point.anchor.exact();points.push_back(O{{"cycle",num(point.cycle)},{"bpm",num(point.bpm)},{"anchor_samples",A{exact[0],exact[1]}}});}
    raw.object()["tempo_timeline"]=O{{"version","practice-tempo.1"},{"initial_bpm",num(spec.initialBpm)},
        {"rate",num(spec.rate)},{"beat_unit",unit(spec.unit)},{"span_quarters",q(spec.span)},
        {"intro_quarters",q(spec.intro)},{"target_cycles",num(spec.cycles)},{"points",points}};
    return raw;
}
storage::Envelope makeEnvelope(const practice::Coordinator& c,const Binding& b,Value a,Outcome o) {
    need(!c.sealed(),"Original outcome is sealed; reconcile its exact bytes without rebuilding");
    validateBinding(c,b);assessment(c,a);finalState(c,o);const auto l=ledger(c,b);
    const auto& config=at(b.context,"configuration");
    Value result=O{{"key",b.owner},{"kind",b.kind},{"content",contentBinding(b)},{"configuration",config},{"active",q(l.active)},
        {"completed_cycles",l.completed},{"traversals",l.traversals},{"interruptions",l.interruptions},{"intervals",l.intervals},
        {"selected_tempo",q(Rational{static_cast<std::int64_t>(c.configuration().bpm)})},{"authored_tempo_ref",at(config,"authored_tempo_ref")},
        {"tempo_segments",l.segments},{"assessment",a},{"outcome",outcome(o)}};
    return storage::validateEnvelope(storage::canonical(O{{"storage_envelope_version",num(1)},{"owner",b.owner},
        {"kind",b.kind},{"context",b.context},{"practice",practiceMetadata(b,l.active)},{"result",result}}));
}
storage::CheckpointSnapshot makeCheckpoint(const practice::Coordinator& c,const Binding& b,std::int64_t sequence,Value a,
                                          std::optional<Outcome> o,const storage::Envelope* sealed,bool saveUncertain) {
    validateBinding(c,b);assessment(c,a);need(sequence>=0,"Checkpoint sequence must be nonnegative");
    need(c.sealed()==(sealed!=nullptr),"Checkpoint must retain the original sealed envelope when present");
    need(!saveUncertain||sealed,"Save uncertainty requires its original immutable envelope");
    if(o&&!sealed)finalState(c,*o);
    auto l=ledger(c,b);const auto& config=at(b.context,"configuration");const auto& latest=c.generations().back();
    Value pending=nullptr,sealedBytes=nullptr;
    if(sealed){need(o.has_value()&&c.sealed(),"Sealed checkpoint requires the original sealed outcome");
        const auto original=storage::validateEnvelope(sealed->bytes);const auto& r=at(original.value,"result");
        need(original.owner==b.owner&&original.kind==b.kind&&original.contextBytes==storage::canonical(b.context)&&original.digest==sealed->digest,
             "Sealed checkpoint differs from original owner/context");
        need(at(r,"assessment")==a&&at(r,"outcome")==Value(outcome(*o))&&original.active==l.active,
             "Sealed checkpoint differs from original assessment/outcome/active facts");
        auto immutableCheck=c;immutableCheck.seal(original.owner,original.bytes);
        // The Coordinator's immutable-byte check is performed when SaveOperation
        // seals. This checkpoint carries the supplied original bytes verbatim;
        // late audit facts are appended separately and cannot rewrite its ledgers.
        l.intervals=at(r,"intervals").array();l.completed=at(r,"completed_cycles").array();l.traversals=at(r,"traversals").array();
        l.interruptions=at(r,"interruptions").array();l.segments=at(r,"tempo_segments").array();l.live=nullptr;
        const auto raw=storage::canonical(r);pending=O{{"key",b.owner},{"payload",raw},{"digest",content::sha256(raw)}};
        sealedBytes=O{{"bytes_hex",hex(sealed->bytes)},{"sha256",sealed->digest}};}
    Value snap=O{{"binding",contentBinding(b)},{"config",configurationValues(c.configuration())},{"context",b.kind=="Attempt"?"lesson":"freeplay"},
        {"attempt",b.owner},{"generation",num(c.owner().generation)},{"serial",Value::fromInteger(sequence)},{"cursor",q(l.cursor)},
        {"attempt_config",at(config,"values")},{"active",q(l.active)},{"intervals",l.intervals},{"completed",l.completed},
        {"cycle",num(c.completedCycles()+1)},{"traversals",l.traversals},{"traversal",l.live},{"interruptions",l.interruptions},
        {"segments",l.segments},{"segment",nullptr},{"tempo",q(Rational{static_cast<std::int64_t>(c.currentTempo())})},
        {"selected_tempo",q(Rational{static_cast<std::int64_t>(c.configuration().bpm)})},{"assessment",a},{"state",state(c.state())},
        {"confirmed_at",q(seconds(latest.clientAcceptedThrough,c.configuration().rate))},{"pending",pending},
        {"outcome",o?Value(outcome(*o)):Value(nullptr)},{"uncertain",saveUncertain}};
    Value cp=O{{"owner",b.owner},{"context",b.context},{"sequence",Value::fromInteger(sequence)},{"stopped_on_reopen",true},
        {"practice_snapshot",snap},{"snapshot_practice",practiceMetadata(b,l.active)},{"sealed_envelope",sealedBytes}};
    auto bytes=storage::canonical(cp);const auto gen=narrow(c.owner().generation);
    storage::validateCheckpoint(b.owner,gen,sequence,bytes,b.kind,b.context);storage::validateUnsealedRecoverySnapshot(snap);
    return {gen,sequence,std::move(bytes)};
}
SaveOperation::SaveOperation(storage::ProfileStore& s,practice::Coordinator& c,Binding b,Value a,Outcome o,std::string prefix,std::int64_t now)
    :store_(s),envelope_(makeEnvelope(c,b,std::move(a),o)),prefix_(std::move(prefix)),lastMs_(now) {
    need(!prefix_.empty()&&now>=0,"Explicit operation prefix and monotonic time required");
    c.seal(envelope_.owner,envelope_.bytes);submit(Stage::Reconcile,now);
}
SaveOperation::SaveOperation(storage::ProfileStore& s,practice::Coordinator& c,const storage::Envelope& original,std::string prefix,std::int64_t now)
    :store_(s),envelope_(storage::validateEnvelope(original.bytes)),prefix_(std::move(prefix)),lastMs_(now) {
    need(!prefix_.empty()&&now>=0,"Explicit operation prefix and monotonic time required");
    need(c.sealed()&&c.originalKey()==envelope_.owner&&c.context()==envelope_.contextBytes&&original.digest==envelope_.digest,
         "Reconciliation requires the exact original sealed owner/context");
    const auto& raw=at(envelope_.value,"result");
    Binding originalBinding{envelope_.owner,envelope_.kind,at(envelope_.value,"context"),
        envelope_.kind=="Attempt"?at(at(raw,"content"),"source_hashes"):Value(nullptr),envelope_.practiceUtc,envelope_.timezone};
    validateBinding(c,originalBinding);
    c.seal(envelope_.owner,envelope_.bytes);submit(Stage::Reconcile,now);
}
void SaveOperation::submit(Stage stage,std::int64_t now) {
    stage_=stage;submittedMs_=now;
    const auto op=prefix_+(stage==Stage::Reconcile?".reconcile":stage==Stage::Seal?".seal":".commit");
    if(stage==Stage::Reconcile)future_.emplace(store_.reconcile(op,envelope_.owner,envelope_.bytes));
    else if(stage==Stage::Seal)future_.emplace(store_.seal(op,envelope_.owner,envelope_.bytes));
    else future_.emplace(store_.commit(op,envelope_.owner,envelope_.bytes));
    feedback_={storage::Status::Unresolved,op,envelope_.owner,"SAVE_IN_PROGRESS","Original result pending; remain stopped",nullptr};
}
void SaveOperation::finish(storage::Reply r,bool saved){feedback_=std::move(r);finished_=true;saved_=saved;future_.reset();}
bool SaveOperation::poll(std::int64_t now) {
    need(now>=lastMs_,"Save observation clock moved backwards");lastMs_=now;if(finished_)return true;
    if(future_->wait_for(std::chrono::milliseconds(0))!=std::future_status::ready){
        if(now-submittedMs_>=1000)feedback_={storage::Status::Unresolved,future_->operationId(),envelope_.owner,"ACK_TIMEOUT","Original operation continues; retain key and bytes",nullptr};
        return false;
    }
    const auto expected=future_->operationId();auto r=future_->get();future_.reset();
    if(r.operation!=expected||r.owner!=envelope_.owner){finish({storage::Status::Conflict,expected,envelope_.owner,"SAVE_REPLY_OWNER","Reply does not match original operation; retain both",r.data});return true;}
    if((stage_==Stage::Reconcile||stage_==Stage::Commit)&&r.status==storage::Status::Confirmed){
        if(finalReceipt(r,envelope_))finish(std::move(r),true);
        else finish({storage::Status::Conflict,expected,envelope_.owner,"SAVE_RECEIPT","Final receipt lacks exact original payload/digest/sequence",r.data});return true;
    }
    if(stage_==Stage::Reconcile&&r.status==storage::Status::DefinitelyAbsent){submit(Stage::Seal,now);return false;}
    if(stage_==Stage::Reconcile&&r.status==storage::Status::Unresolved&&r.code=="PENDING"){
        if(at(r.data,"payload")!=Value(envelope_.bytes)||at(r.data,"digest")!=Value(envelope_.digest)){
            finish({storage::Status::Conflict,expected,envelope_.owner,"SAVE_PENDING_CONFLICT","Pending bytes differ; preserve original",r.data});return true;}
        submit(Stage::Commit,now);return false;
    }
    if(stage_==Stage::Seal&&r.status==storage::Status::Confirmed){
        const auto d=r.data.find("digest");if(!d||*d!=Value(envelope_.digest)){
            finish({storage::Status::Conflict,expected,envelope_.owner,"SAVE_SEAL_CONFLICT","Seal acknowledgment differs from original",r.data});return true;}
        submit(Stage::Commit,now);return false; // pending ACK alone never releases
    }
    finish(std::move(r));return true; // failures need explicit original reconciliation
}
bool SaveOperation::release(practice::Coordinator& c) const {
    return saved_&&c.originalKey()==envelope_.owner&&c.reconcile(envelope_.owner,envelope_.bytes,practice::Coordinator::Save::Matching);
}
} // namespace fathom::capture
