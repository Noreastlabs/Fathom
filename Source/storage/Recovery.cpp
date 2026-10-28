#include "storage/Recovery.hpp"
#include "content/Canonical.hpp"
#include <algorithm>
#include <charconv>
#include <limits>
#include <numeric>
#include <set>

namespace fathom::storage {
namespace {
const Value& at(const Value& v,const std::string& k){return v.object().at(k);}
Value& at(Value& v,const std::string& k){return v.object().at(k);}
std::int64_t integer(const Value& v){std::int64_t n;if(!v.integer(n)||n<0||canonical(v)!=std::to_string(n))throw EnvelopeError("RECOVERY_INTEGER","Nonnegative integer required");return n;}
std::int64_t next(std::int64_t n){if(n<0||n==std::numeric_limits<std::int64_t>::max())throw EnvelopeError("RECOVERY_GENERATION","Generation cannot advance safely");return n+1;}
std::string unhex(const std::string& h){if(h.size()%2)throw EnvelopeError("RECOVERY_HEX","Odd sealed bytes");std::string out;out.reserve(h.size()/2);auto digit=[](char c)->unsigned {if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;throw EnvelopeError("RECOVERY_HEX","Noncanonical hex");};for(std::size_t i=0;i<h.size();i+=2)out.push_back(static_cast<char>((digit(h[i])<<4)|digit(h[i+1])));return out;}
void requireLedger(bool okay,const std::string& why){if(!okay)throw EnvelopeError("RECOVERY_LEDGER",why);}
std::int64_t component(const Value& v){if(!v.isString())return integer(v);const auto& s=v.string();requireLedger(!s.empty()&&(s.size()==1||s[0]!='0')&&s.find_first_not_of("0123456789")==std::string::npos,"Noncanonical ledger rational component");std::int64_t value=0;auto parsed=std::from_chars(s.data(),s.data()+s.size(),value);requireLedger(parsed.ec==std::errc{}&&parsed.ptr==s.data()+s.size(),"Ledger rational component outside int64");return value;}
Rational quantity(const Value& v){requireLedger(v.isArray()&&v.array().size()==2,"Expected ledger rational pair");auto a=component(v.array()[0]),b=component(v.array()[1]);requireLedger(b>0&&std::gcd(a,b)==1,"Expected reduced ledger rational");return Rational(a,b);}
void fields(const Value& v,std::initializer_list<const char*> keys){requireLedger(v.isObject(),"Expected ledger object");std::set<std::string> want,got;for(auto key:keys)want.insert(key);for(const auto& item:v.object())got.insert(item.first);requireLedger(want==got,"Unexpected or missing ledger fields");}
Rational segmentDuration(const Value& v){fields(v,{"tempo","start_at","end_at","confirmed_duration"});auto tempo=quantity(at(v,"tempo")),start=quantity(at(v,"start_at")),end=quantity(at(v,"end_at")),duration=quantity(at(v,"confirmed_duration"));requireLedger(tempo.numerator()>0&&start+duration==end,"Invalid confirmed tempo segment extent");return duration;}
void traversal(const Value& v,bool live){fields(v,{"cycle","start","end","status"});requireLedger(integer(at(v,"cycle"))>0,"Invalid traversal cycle");auto start=quantity(at(v,"start")),end=quantity(at(v,"end"));requireLedger(!(end<start),"Negative traversal extent");requireLedger(at(v,"status").isString(),"Invalid traversal status");const auto& status=at(v,"status").string();const std::set<std::string> closed={"complete","partial_suffix","partial_interrupted","partial_ended","partial_recovered"};requireLedger(live?status=="running":closed.count(status)==1,"Unsupported traversal status");}
void bindEnvelope(const std::string& bytes,const RecoveryBinding& b){const auto e=validateEnvelope(bytes);if(e.owner!=b.owner||e.kind!=b.kind||e.contextBytes!=canonical(b.context))throw EnvelopeError("RECOVERY_BINDING","Recovered bytes differ from original owner/context");if(b.originalSealedBytes&&bytes!=*b.originalSealedBytes)throw EnvelopeError("RECOVERY_CONFLICT","Durable outcome conflicts with retained original sealed bytes; preserve both");}
}
Rational confirmedRecoveryQuantity(const Value& value){return quantity(value);}
void validateUnsealedRecoverySnapshot(const Value& q){
    if(!at(q,"pending").null())return; // Established sealed result is never rebuilt.
    Rational total;for(const auto& value:at(q,"segments").array())total=total+segmentDuration(value);
    if(!at(q,"segment").null())total=total+segmentDuration(at(q,"segment"));
    requireLedger(total==quantity(at(q,"active")),"Tempo durations differ from confirmed active practice");
    for(const auto& value:at(q,"traversals").array())traversal(value,false);
    if(!at(q,"traversal").null()){traversal(at(q,"traversal"),true);requireLedger(!(quantity(at(q,"cursor"))<quantity(at(at(q,"traversal"),"start"))),"Confirmed cursor precedes live traversal");}
}
RecoveryPlan planRecovery(const Reply& r,const RecoveryBinding& b){
    validateUuid(b.owner);validateContext(b.context,b.kind);
    if(r.status!=Status::Confirmed||r.owner!=b.owner)throw EnvelopeError("RECOVERY_REPLY","A confirmed original-owner recovery reply is required");
    if(at(r.data,"stopped_on_reopen")!=Value(true))throw EnvelopeError("RECOVERY_STOPPED","Recovery must be stopped");
    RecoveryPlan p;p.owner=b.owner;if(b.currentGeneration<0)throw EnvelopeError("RECOVERY_GENERATION","Invalid generation");if(b.currentGeneration<std::numeric_limits<std::int64_t>::max())p.nextGeneration=next(b.currentGeneration);if(b.currentSerial<0)throw EnvelopeError("RECOVERY_SERIAL","Invalid serial high-water");p.serial=b.currentSerial;
    const auto state=at(r.data,"state").string();
    if(state=="final"||state=="pending"){
        p.bytes=at(r.data,"payload").string();bindEnvelope(p.bytes,b);p.digest=content::sha256(p.bytes);
        if(p.digest!=at(r.data,"digest").string())throw EnvelopeError("RECOVERY_DIGEST","Durable outcome digest mismatch");
        p.kind=state=="final"?RecoveryKind::Final:RecoveryKind::Original;return p;
    }
    if(state=="allocated"){
        if(at(r.data,"kind")!=Value(b.kind)||at(r.data,"context")!=b.context)throw EnvelopeError("RECOVERY_BINDING","Allocation context mismatch");
        if(b.originalSealedBytes){bindEnvelope(*b.originalSealedBytes,b);p.kind=RecoveryKind::Original;p.bytes=*b.originalSealedBytes;p.digest=content::sha256(p.bytes);}return p;
    }
    if(state!="checkpoint")throw EnvelopeError("RECOVERY_STATE","Unsupported recovery state");
    auto bytes=at(r.data,"payload").string();auto generation=integer(at(r.data,"generation")),sequence=integer(at(r.data,"sequence"));
    validateCheckpoint(b.owner,generation,sequence,bytes,b.kind,b.context);
    auto cp=parseCanonical(bytes), q=at(cp,"practice_snapshot");
    const auto highGeneration=std::max(b.currentGeneration,integer(at(q,"generation")));p.nextGeneration.reset();if(highGeneration<std::numeric_limits<std::int64_t>::max())p.nextGeneration=next(highGeneration);p.serial=std::max(b.currentSerial,integer(at(q,"serial")));
    if(!at(cp,"sealed_envelope").null()){
        const auto& sealed=at(cp,"sealed_envelope");p.bytes=unhex(at(sealed,"bytes_hex").string());bindEnvelope(p.bytes,b);p.digest=content::sha256(p.bytes);if(p.digest!=at(sealed,"sha256").string())throw EnvelopeError("RECOVERY_DIGEST","Sealed checkpoint digest mismatch");p.kind=RecoveryKind::Original;
    }else if(b.originalSealedBytes){bindEnvelope(*b.originalSealedBytes,b);p.bytes=*b.originalSealedBytes;p.digest=content::sha256(p.bytes);p.kind=RecoveryKind::Original;
    }else{
        validateUnsealedRecoverySnapshot(q);
        if(!p.nextGeneration)throw EnvelopeError("RECOVERY_GENERATION","Unsealed reconstruction cannot advance generation safely; preserve checkpoint and remain stopped");
        const auto& configuration=at(b.context,"configuration");const Value* authored=configuration.find("authored_tempo_ref");
        if(authored&&b.originalAuthoredTempoRef&&*authored!=*b.originalAuthoredTempoRef)throw EnvelopeError("RECOVERY_BINDING","Original authored tempo metadata conflicts");
        if(!authored&&b.originalAuthoredTempoRef)authored=&*b.originalAuthoredTempoRef;
        if(!authored)throw EnvelopeError("RECOVERY_METADATA_REQUIRED","Retain original authored_tempo_ref in initial configuration, or supply exact original bound metadata; no current-content inference");
        if(!at(q,"segment").null()){at(q,"segments").array().push_back(at(q,"segment"));at(q,"segment")=nullptr;}
        if(!at(q,"traversal").null()){auto traversal=at(q,"traversal");at(traversal,"end")=at(q,"cursor");at(traversal,"status")="partial_recovered";at(q,"traversals").array().push_back(traversal);at(q,"traversal")=nullptr;}
        if(at(q,"outcome").null())at(q,"outcome")="interrupted_reopen";
        Value raw=Value::Object{{"key",b.owner},{"kind",b.kind},{"content",b.kind=="Attempt"?at(q,"binding"):Value(nullptr)},{"configuration",configuration},{"active",at(q,"active")},{"completed_cycles",at(q,"completed")},{"traversals",at(q,"traversals")},{"interruptions",at(q,"interruptions")},{"intervals",at(q,"intervals")},{"selected_tempo",at(q,"selected_tempo")},{"authored_tempo_ref",*authored},{"tempo_segments",at(q,"segments")},{"assessment",at(q,"assessment")},{"outcome",at(q,"outcome")}};
        const auto& practice=at(cp,"snapshot_practice");
        p.bytes=canonical(Value::Object{{"storage_envelope_version",Value::fromInteger(1)},{"owner",b.owner},{"kind",b.kind},{"context",b.context},{"practice",practice},{"result",raw}});bindEnvelope(p.bytes,b);p.digest=content::sha256(p.bytes);p.kind=RecoveryKind::Interrupted;
    }
    if(p.nextGeneration)at(q,"generation")=Value::fromInteger(*p.nextGeneration);at(q,"serial")=Value::fromInteger(p.serial);at(q,"state")="STOPPED";p.stoppedSnapshot=std::move(q);return p;
}
RecoveryOperation::RecoveryOperation(ProfileStore& s,RecoveryBinding b,std::string prefix):store_(s),binding_(std::move(b)),prefix_(std::move(prefix)){
    future_.emplace(store_.recoveryState(prefix_+".read",binding_.owner));reply_={Status::Unresolved,prefix_,binding_.owner,"RECOVERY_IN_PROGRESS","Remain stopped until original outcome is confirmed",nullptr};
}
void RecoveryOperation::finish(Reply r){reply_=std::move(r);finished_=true;future_.reset();}
bool RecoveryOperation::canRetry()const noexcept{
    return finished_&&reply_.code!="INITIAL_CHECKPOINT_REQUIRED"&&
        (reply_.status==Status::Unresolved||reply_.status==Status::Busy||
         (reply_.status==Status::DefiniteFailure&&plan_.has_value()));
}
bool RecoveryOperation::retry(){
    if(!canRetry())return false;
    // Never generate a replacement operation or rebuild a retained outcome.
    // Reconcile first: final is adopted, pending is committed, and only a
    // definite absence permits sealing these exact original bytes again.
    try{
        if(plan_){stage_=Stage::Reconcile;future_.emplace(store_.reconcile(prefix_+".reconcile",binding_.owner,plan_->bytes));}
        else{stage_=Stage::Read;future_.emplace(store_.recoveryState(prefix_+".read",binding_.owner));}
    }catch(const std::exception& e){finish({Status::Unresolved,prefix_,binding_.owner,"RECOVERY_SUBMISSION",e.what(),nullptr});return false;}
    finished_=false;reply_={Status::Unresolved,prefix_,binding_.owner,"RECOVERY_IN_PROGRESS","Checking the same original; no replacement outcome",nullptr};return true;
}
bool RecoveryOperation::poll(){
    if(finished_)return true;
    if(!future_){finish({Status::Unresolved,prefix_,binding_.owner,"RECOVERY_SUBMISSION","Original submission is not confirmed; retain identity and check explicitly",nullptr});return true;}
    try{
    if(future_->wait_for(std::chrono::milliseconds(0))!=std::future_status::ready)return false;
    Reply r;
    try{r=future_->get();future_.reset();}
    catch(const std::exception& e){finish({Status::Unresolved,prefix_,binding_.owner,"RECOVERY_FUTURE",e.what(),nullptr});return true;}
    if(stage_==Stage::Read){
        if(r.status!=Status::Confirmed){finish(std::move(r));return true;}
        try{plan_=planRecovery(r,binding_);}catch(const EnvelopeError& e){finish({e.code=="RECOVERY_CONFLICT"?Status::Conflict:Status::DefiniteFailure,prefix_,binding_.owner,e.code,e.what(),r.data});return true;}catch(const std::exception& e){finish({Status::DefiniteFailure,prefix_,binding_.owner,"RECOVERY_INVALID",e.what(),r.data});return true;}
        if(plan_->kind==RecoveryKind::NeedsInitialCheckpoint){finish({Status::Unresolved,prefix_,binding_.owner,"INITIAL_CHECKPOINT_REQUIRED","Original allocation has no complete checkpoint; remain stopped and recover original binding",r.data});return true;}
        binding_.originalSealedBytes=plan_->bytes;
        stage_=Stage::Reconcile;future_.emplace(store_.reconcile(prefix_+".reconcile",binding_.owner,plan_->bytes));return false;
    }
    if(stage_==Stage::Reconcile){
        if(r.status==Status::Confirmed){finish(std::move(r));return true;}
        if(r.status==Status::DefinitelyAbsent){stage_=Stage::Seal;future_.emplace(store_.seal(prefix_+".seal",binding_.owner,plan_->bytes));return false;}
        if(r.status==Status::Unresolved&&r.code=="PENDING"){stage_=Stage::Commit;future_.emplace(store_.commit(prefix_+".commit",binding_.owner,plan_->bytes));return false;}
        finish(std::move(r));return true;
    }
    if(stage_==Stage::Seal&&r.status==Status::Confirmed){stage_=Stage::Commit;future_.emplace(store_.commit(prefix_+".commit",binding_.owner,plan_->bytes));return false;}
    finish(std::move(r));return true;
    }catch(const std::exception& e){finish({Status::Unresolved,prefix_,binding_.owner,"RECOVERY_SUBMISSION",e.what(),nullptr});return true;}
}
} // namespace fathom::storage
