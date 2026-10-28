#include "practice/PracticeSession.hpp"
#include "platform/ProfileAccessMac.hpp"
#include <algorithm>

namespace fathom::capture {
namespace {
const Value& at(const Value& v,const char* key){return v.object().at(key);}
scheduler::Owner toOwner(const std::string& id,std::uint64_t epoch){
    storage::validateUuid(id);scheduler::Owner o;std::string hex;
    for(char c:id)if(c!='-')hex+=c;
    for(std::size_t i=0;i<16;++i)o.id[i]=static_cast<std::uint8_t>(std::stoul(hex.substr(i*2,2),nullptr,16));
    o.epoch=epoch;o.generation=1;return o;
}
bool stopped(const practice::Coordinator& c){return c.state()==practice::State::Ended||c.state()==practice::State::Error;}
practice::Configuration originalConfiguration(const Value& v){
    auto integer=[](const Value& x){std::int64_t n{};if(!x.integer(n)||n<0)throw std::invalid_argument("Invalid original configuration integer");return static_cast<std::uint64_t>(n);};
    practice::Configuration c;const auto& span=at(v,"span").array();c.span=Rational{static_cast<std::int64_t>(integer(span.at(0))),static_cast<std::int64_t>(integer(span.at(1)))};
    auto rate=integer(at(v,"rate")),bpm=integer(at(v,"selected_bpm"));if(rate>UINT32_MAX||bpm>UINT16_MAX)throw std::invalid_argument("Original configuration exceeds supported bounds");
    c.rate=static_cast<std::uint32_t>(rate);c.bpm=static_cast<std::uint16_t>(bpm);c.targetCycles=integer(at(v,"target_cycles"));
    const auto u=at(v,"beat_unit").string();
    if(u=="quarter")c.unit=scheduler::BeatUnit::Quarter;else if(u=="eighth")c.unit=scheduler::BeatUnit::Eighth;
    else if(u=="dotted_quarter")c.unit=scheduler::BeatUnit::DottedQuarter;else if(u=="half")c.unit=scheduler::BeatUnit::Half;else throw std::invalid_argument("Unsupported original beat unit");
    const auto count=at(v,"count_in").string();if(count=="off")c.countIn=practice::CountIn::Off;else if(count=="authored_bar")c.countIn=practice::CountIn::AuthoredBar;else throw std::invalid_argument("Unsupported original count-in");
    if(!at(v,"meter").null()){const auto& m=at(v,"meter").array();auto n=integer(m.at(0)),d=integer(m.at(1));if(n>32||d>16)throw std::invalid_argument("Unsupported original meter");c.meter={{static_cast<int>(n),static_cast<int>(d)}};}
    c.faithfulWholeSpan=at(v,"faithful_whole_span")==Value(true);c.sourceRequiresCountIn=at(v,"source_requires_count_in")==Value(true);
    if(configurationValues(c)!=v)throw std::invalid_argument("Original configuration must round-trip exactly");return c;
}
}
const char* phaseText(SessionPhase s)noexcept{
    switch(s){case SessionPhase::Idle:return "Ready for an explicit Start";case SessionPhase::Allocating:return "Pending — allocating original record";
    case SessionPhase::AllocationUnknown:return "Unknown allocation — original identity retained";case SessionPhase::InitialCheckpoint:return "Pending — initial durable checkpoint";
    case SessionPhase::Ready:return "Initial checkpoint acknowledged";case SessionPhase::Active:return "Practice in progress";
    case SessionPhase::Review:return "Stopped — choose self-assessment or leave it absent";case SessionPhase::SealedCheckpoint:return "Pending — retaining original result";
    case SessionPhase::Saving:return "Pending — confirming original result";case SessionPhase::Saved:return "Saved — sound remains stopped";
    case SessionPhase::Recovering:return "Pending — recovering original while stopped";case SessionPhase::Failed:return "Failed — original facts retained";}return "Unknown";
}
PracticeSession::PracticeSession(storage::ProfileStore& s,practice::Coordinator& c):store_(s),coordinator_(c){}
std::string PracticeSession::displayText()const{
    if(feedback_.status==storage::Status::Unresolved&&(phase_==SessionPhase::Failed||feedback_.code=="ACK_TIMEOUT"||feedback_.code=="CHECKPOINT_ACK_TIMEOUT"||feedback_.code=="AUDIT_ACK_TIMEOUT"))return "Unknown — original operation and facts retained";
    return phaseText(phase_);
}
void PracticeSession::clock(std::int64_t now){if(now<0||(clockSet_&&now<now_))throw std::invalid_argument("Capture control clock regressed");now_=now;clockSet_=true;}
void PracticeSession::setFeedback(storage::Status s,const char* code,const char* message){feedback_={s,prefix_,request_.binding.owner,code,message,nullptr};}
bool PracticeSession::start(StartRequest r,std::uint64_t seq,std::int64_t now){
    clock(now);if(exitDiscard_||phase_!=SessionPhase::Idle||coordinator_.pending()||!seq||seq<=commandSequence_||!audit_.empty())return false;
    if(!r.binding.owner.empty()||!r.epoch)throw std::invalid_argument("Start requires a new Store allocation and current output epoch");
    validateContext(r.binding,r.configuration);
    auto& configuration=r.binding.context.object().at("configuration");
    Value metadata=Value::Object{{"practice_utc",r.binding.practiceUtc},{"timezone",r.binding.timezone}};
    if(auto* old=configuration.find("capture_metadata");old&&*old!=metadata)throw std::invalid_argument("Original practice metadata conflicts");
    configuration.object()["capture_metadata"]=metadata;
    request_=std::move(r);prefix_=storage::newUuid();commandSequence_=seq;cancelled_=false;startTaken_=false;cancelNs_=0;stopRequired_=false;allocationAbsent_=false;allocationRecovery_=false;recoveryBinding_.reset();
    assessment_=nullptr;outcome_.reset();original_.reset();latest_.reset();sealedCheckpoint_.reset();checkpoint_.reset();save_.reset();recovery_.reset();
    checkpointSequence_=-1;observed_.clear();submitted_=now;
    endpointActive_=0;terminalObserved_=false;
    allocation_.emplace(store_.allocate(prefix_+".allocate",request_.binding.kind,request_.binding.context,request_.binding.practiceUtc));
    phase_=SessionPhase::Allocating;setFeedback(storage::Status::Unresolved,"ALLOCATING","Original allocation pending; sound stopped");return true;
}
void PracticeSession::cancelBeforeSound(std::uint64_t ns){
    if(startTaken_||phase_==SessionPhase::Idle||phase_==SessionPhase::Saved)return;
    cancelled_=true;cancelNs_=ns;stopRequired_=true;
    if(coordinator_.pending()&&!coordinator_.sealed())coordinator_.stoppedAcknowledged(coordinator_.owner(),practice::State::Ended,ns);
}
void PracticeSession::beginAllocated(std::int64_t now){
    const auto& b=request_.binding;
    coordinator_.begin(toOwner(b.owner,request_.epoch),b.kind=="Attempt"?practice::Kind::Attempt:practice::Kind::Freeplay,storage::canonical(b.context),request_.configuration);
    checkpoint_=std::make_unique<storage::CheckpointCoordinator>(store_,b.owner,b.kind,b.context,prefix_+".checkpoint");
    if(exitDiscard_)checkpoint_->quiesceForExit();
    if(cancelled_)coordinator_.stoppedAcknowledged(coordinator_.owner(),practice::State::Ended,cancelNs_);
    phase_=cancelled_?SessionPhase::Review:SessionPhase::InitialCheckpoint;offer(now,true);
}
void PracticeSession::offer(std::int64_t now,bool force,const std::string* utc){
    if(exitDiscard_||!checkpoint_||original_||!coordinator_.pending())return;
    auto probe=makeCheckpoint(coordinator_,request_.binding,0);
    // Serial is fixed in this comparison. A timer alone creates no new checkpoint facts.
    if(probe.bytes==observed_)return;
    // Calendar attribution follows the observed confirmed-practice endpoint,
    // not Start or eventual Save. The initial allocation timestamp remains in
    // immutable capture_metadata for allocation-only recovery. A timer, pause
    // waiting, later error or save receipt cannot move an unchanged endpoint.
    const auto active=coordinator_.activeFrames();const bool terminal=stopped(coordinator_);
    if(utc&&!allocationRecovery_&&(active>endpointActive_||(!active&&terminal&&!terminalObserved_))){
        storage::validateUtc(*utc);storage::localDay(*utc,request_.binding.timezone);request_.binding.practiceUtc=*utc;
    }
    endpointActive_=active;terminalObserved_=terminalObserved_||terminal;
    observed_=makeCheckpoint(coordinator_,request_.binding,0).bytes;
    if(checkpointSequence_==INT64_MAX)throw std::overflow_error("Checkpoint sequence exhausted; retain original");
    latest_=makeCheckpoint(coordinator_,request_.binding,++checkpointSequence_);
    checkpoint_->offer(*latest_,now,force);
}
std::optional<scheduler::Owner> PracticeSession::takeStart(std::int64_t now){
    clock(now);if(phase_!=SessionPhase::Ready||cancelled_||startTaken_||!checkpoint_||stopRequired_)return {};
    const auto state=checkpoint_->state(now);
    if(!state.initialAcknowledged||state.stopRequired){cancelBeforeSound(0);return {};}
    if(exitDiscard_)return {};
    startTaken_=true;phase_=SessionPhase::Active;return coordinator_.owner();
}
void PracticeSession::collectAudit(const std::string& utc){
    const auto& facts=coordinator_.lateEvidence();
    while(auditIndex_<facts.size()){
        const auto& fact=facts[auditIndex_];const auto* map=coordinator_.lateTimeline(fact);
        auto v=map?lateEvidence(fact,*map):lateEvidence(fact);storage::validateUtc(utc);
        audit_.push_back({at(v,"original_owner").string(),storage::newUuid(),utc,storage::canonical(v),{},false});++auditIndex_;
    }
    if(audit_.size()>=256){stopRequired_=true;if(!startTaken_)cancelBeforeSound(0);} // never drop original audit facts
}
void PracticeSession::serviceAudit(std::int64_t now,bool explicitRetry){
    if(audit_.empty())return;auto& a=audit_.front();if(a.failed)return;
    if(!a.future&&exitDiscard_&&!explicitRetry)return;
    if(!a.future){a.future.emplace(store_.appendLate(a.id+".late",a.owner,a.id,a.received,a.bytes));a.submitted=now;return;}
    if(a.future->wait_for(std::chrono::milliseconds(0))!=std::future_status::ready){if(now-a.submitted>=1000){stopRequired_=true;if(!startTaken_)cancelBeforeSound(0);setFeedback(storage::Status::Unresolved,"AUDIT_ACK_TIMEOUT","Original late-evidence operation continues; stop and retain its identity");}return;}
    auto r=a.future->get();a.future.reset();
    if(r.status==storage::Status::Confirmed&&r.owner==a.owner&&r.operation==a.id+".late"){
        audit_.pop_front();
        // This ACK resolves only its audit operation. A failed/pending result or
        // an active transport stop latch is never cleared by an audit receipt.
        if(audit_.empty()&&phase_==SessionPhase::Saved){stopRequired_=false;
            setFeedback(storage::Status::Confirmed,"SAVED","Original result confirmed; retained late evidence acknowledged");}
    }else{a.failed=true;feedback_=std::move(r);stopRequired_=true;if(!startTaken_)cancelBeforeSound(0);}
}
void PracticeSession::poll(std::int64_t now,const std::string& utc){
    clock(now);
    if(allocation_){
        if(now-submitted_>=1000){cancelBeforeSound(0);setFeedback(storage::Status::Unresolved,"ACK_TIMEOUT","Allocation continues; late acknowledgment cannot start sound");}
        if(allocation_->wait_for(std::chrono::milliseconds(0))==std::future_status::ready){
            auto r=allocation_->get();allocation_.reset();feedback_=r;
            if(r.operation!=prefix_+".allocate"){phase_=SessionPhase::Failed;return;}
            request_.binding.owner=r.owner;
            if(r.status==storage::Status::Confirmed&&at(r.data,"owner")==Value(r.owner)&&at(r.data,"kind")==Value(request_.binding.kind)&&at(r.data,"context")==request_.binding.context)beginAllocated(now);
            else {cancelled_=true;stopRequired_=true;
                allocationAbsent_=r.owner.empty()&&(r.status==storage::Status::DefiniteFailure||r.status==storage::Status::Busy||r.status==storage::Status::Unsupported);
                phase_=r.status==storage::Status::Unresolved||!r.owner.empty()?SessionPhase::AllocationUnknown:SessionPhase::Failed;}
        }
    }
    if(inspection_&&inspection_->wait_for(std::chrono::milliseconds(0))==std::future_status::ready){
        auto r=inspection_->get();inspection_.reset();feedback_=r;
        if(r.status==storage::Status::Confirmed&&r.owner==request_.binding.owner&&r.operation==prefix_+".inspect"&&at(r.data,"state")==Value("allocated")&&at(r.data,"context")==request_.binding.context&&at(r.data,"kind")==Value(request_.binding.kind))beginAllocated(now);
        else phase_=SessionPhase::AllocationUnknown;
    }
    if(checkpoint_&&phase_!=SessionPhase::Saved&&phase_!=SessionPhase::Recovering){
        checkpoint_->poll(now);const auto state=checkpoint_->state(now);
        if(state.stopRequired&&state.code!="INITIAL_CHECKPOINT_REQUIRED"){
            stopRequired_=true;if(!startTaken_)cancelBeforeSound(0);
            if(state.lastReply&&state.lastReply->status!=storage::Status::Confirmed)feedback_=*state.lastReply;
            else setFeedback(storage::Status::Unresolved,state.code.c_str(),"Remain stopped; retain the original checkpoint operation");
        }
        if(coordinator_.pending()&&!original_){
            const bool terminal=stopped(coordinator_);
            offer(now,terminal||coordinator_.state()==practice::State::Paused,&utc);
            if(terminal)phase_=SessionPhase::Review;
            else if(phase_==SessionPhase::InitialCheckpoint&&state.initialAcknowledged&&!state.stopRequired&&!cancelled_){phase_=SessionPhase::Ready;setFeedback(storage::Status::Confirmed,"INITIAL_CHECKPOINT_ACKNOWLEDGED","Original initial checkpoint is durable");}
        }
        if(!exitDiscard_&&phase_==SessionPhase::SealedCheckpoint&&sealedCheckpoint_&&state.acknowledged&&state.acknowledged->bytes==sealedCheckpoint_->bytes&&!state.inFlight&&!state.hasUnsaved){
            save_=std::make_unique<SaveOperation>(store_,coordinator_,*original_,prefix_+".save",now);phase_=SessionPhase::Saving;
        }
        if(allocationRecovery_&&latest_&&state.acknowledged&&state.acknowledged->bytes==latest_->bytes&&!state.inFlight&&!state.hasUnsaved){
            allocationRecovery_=false;recovery_=std::make_unique<storage::RecoveryOperation>(store_,*recoveryBinding_,prefix_+".recover-zero");phase_=SessionPhase::Recovering;
        }
    }
    if(save_&&phase_==SessionPhase::Saving){
        save_->poll(now);feedback_=save_->feedback();
        if(save_->finished()){
            if(save_->saved()&&save_->release(coordinator_)){phase_=SessionPhase::Saved;stopRequired_=false;}
            else phase_=SessionPhase::Failed;
        }
    }
    if(recovery_&&phase_==SessionPhase::Recovering){
        recovery_->poll();feedback_=recovery_->reply();
        if(recovery_->finished()){
            if(recovery_->confirmed()&&recovery_->plan()&&recovery_->plan()->kind!=storage::RecoveryKind::NeedsInitialCheckpoint){
                original_=storage::validateEnvelope(recovery_->plan()->bytes);
                if(coordinator_.pending()){coordinator_.seal(original_->owner,original_->bytes);if(!coordinator_.reconcile(original_->owner,original_->bytes,practice::Coordinator::Save::Matching))throw std::logic_error("Original recovery release refused");}
                phase_=SessionPhase::Saved;stopRequired_=false;
            }else if(!exitDiscard_&&recovery_->plan()&&recovery_->plan()->kind==storage::RecoveryKind::NeedsInitialCheckpoint){
                const auto& conf=at(request_.binding.context,"configuration");const auto& metadata=at(conf,"capture_metadata");
                request_.binding.practiceUtc=at(metadata,"practice_utc").string();request_.binding.timezone=at(metadata,"timezone").string();
                request_.binding.sourceHashes=request_.binding.kind=="Attempt"?at(conf,"source_hashes"):Value(nullptr);
                request_.configuration=originalConfiguration(at(conf,"values"));request_.epoch=1;
                validateContext(request_.binding,request_.configuration);cancelled_=true;allocationRecovery_=true;beginAllocated(now);
            }else phase_=SessionPhase::Failed;
        }
    }
    if(!exitDiscard_)collectAudit(utc);
    serviceAudit(now);
}
bool PracticeSession::save(Value a,Outcome o,std::int64_t now){
    if(exitDiscard_)return false;
    clock(now);if(phase_!=SessionPhase::Review||original_||!stopped(coordinator_)||!checkpoint_)return false;
    auto e=makeEnvelope(coordinator_,request_.binding,a,o);coordinator_.seal(e.owner,e.bytes);
    original_=std::move(e);assessment_=std::move(a);outcome_=o;
    sealedCheckpoint_=makeCheckpoint(coordinator_,request_.binding,++checkpointSequence_,assessment_,outcome_,&*original_);
    latest_=sealedCheckpoint_;checkpoint_->offer(*sealedCheckpoint_,now,true);phase_=SessionPhase::SealedCheckpoint;
    setFeedback(storage::Status::Unresolved,"SEALED_CHECKPOINT_PENDING","Original result immutable; awaiting its durable checkpoint");return true;
}
bool PracticeSession::retry(std::int64_t now){
    clock(now);
    if(phase_==SessionPhase::Failed&&allocationAbsent_){phase_=SessionPhase::Idle;return true;}
    if(!audit_.empty()&&audit_.front().failed){audit_.front().failed=false;return true;}
    if(phase_==SessionPhase::Failed&&recovery_&&recovery_->finished()&&recoveryBinding_){
        recovery_=std::make_unique<storage::RecoveryOperation>(store_,*recoveryBinding_,prefix_+".recovery-retry."+storage::newUuid());phase_=SessionPhase::Recovering;return true;
    }
    if(original_&&save_&&save_->finished()&&!save_->saved()&&phase_==SessionPhase::Failed){
        save_=std::make_unique<SaveOperation>(store_,coordinator_,*original_,prefix_+".retry."+storage::newUuid(),now);phase_=SessionPhase::Saving;return true;
    }
    if(checkpoint_&&latest_&&stopped(coordinator_)&&(phase_==SessionPhase::Review||phase_==SessionPhase::SealedCheckpoint)){
        const auto state=checkpoint_->state(now);if(state.inFlight)return false;
        checkpoint_=std::make_unique<storage::CheckpointCoordinator>(store_,request_.binding.owner,request_.binding.kind,request_.binding.context,prefix_+".checkpoint-retry."+storage::newUuid());
        checkpoint_->offer(*latest_,now,true);return true;
    }
    return false;
}
bool PracticeSession::inspectAllocation(std::int64_t now){
    clock(now);if(phase_!=SessionPhase::AllocationUnknown||allocation_||inspection_||request_.binding.owner.empty())return false;
    inspection_.emplace(store_.recoveryState(prefix_+".inspect",request_.binding.owner));return true;
}
bool PracticeSession::recover(storage::RecoveryBinding b){
    if(phase_!=SessionPhase::Idle||coordinator_.pending()||!audit_.empty())return false;
    request_.binding.owner=b.owner;request_.binding.kind=b.kind;request_.binding.context=b.context;
    prefix_=storage::newUuid();recoveryBinding_=b;recovery_=std::make_unique<storage::RecoveryOperation>(store_,std::move(b),prefix_+".reopen");phase_=SessionPhase::Recovering;return true;
}
void PracticeSession::requestExitDiscard() noexcept {
    exitDiscard_=true;cancelled_=true;stopRequired_=true;
    if(checkpoint_)checkpoint_->quiesceForExit();
    // Explicit Discard: drop only volatile audit entries never admitted to Store.
    for(auto i=audit_.begin();i!=audit_.end();)if(!i->future&&!i->failed)i=audit_.erase(i);else ++i;
}
void PracticeSession::retryExitDiscard(std::int64_t now){
    if(!exitDiscard_)return;
    if(phase_==SessionPhase::AllocationUnknown&&!allocation_&&!inspection_)inspectAllocation(now);
    if(checkpoint_)checkpoint_->retryPendingForExit(now);
    if(!audit_.empty()&&audit_.front().failed){audit_.front().failed=false;serviceAudit(now,true);}
}
bool PracticeSession::canLeaveForExit(bool cleared,std::int64_t now) {
    if(!exitDiscard_)return canLeave(cleared);
    if(!cleared||allocation_||inspection_||phase_==SessionPhase::AllocationUnknown)return false;
    if(save_&&!save_->finished())return false;
    if(save_&&!save_->saved()){
        if(!checkpoint_||!sealedCheckpoint_)return false;
        const auto state=checkpoint_->state(now);
        if(!state.acknowledged||state.acknowledged->bytes!=sealedCheckpoint_->bytes)return false;
    }
    if(recovery_&&!recovery_->finished())return false;
    for(const auto& a:audit_)if(a.future||a.failed)return false;
    if(checkpoint_){const auto state=checkpoint_->state(now);if(state.inFlight||state.inFlightSnapshot)return false;}
    // The user's exit-only Discard drops volatile unsent progress, not durable
    // records. Any accepted checkpoint receipt is settled and retained as-is;
    // no Saved/absence claim follows from this exit permission.

    // Exit only: no navigation release, reconciliation, finalization or deletion.
    // Persisted identity/checkpoint remains recoverable on the next open.
    return true;
}
bool PracticeSession::canLeave(bool cleared)const{
    return cleared&&!allocation_&&!inspection_&&audit_.empty()&&(phase_==SessionPhase::Idle||phase_==SessionPhase::Saved||(phase_==SessionPhase::Failed&&allocationAbsent_));
}
bool PracticeSession::again(bool cleared){if(exitDiscard_||phase_!=SessionPhase::Saved||!canLeave(cleared))return false;phase_=SessionPhase::Idle;return true;}
storage::CheckpointState PracticeSession::checkpointState(std::int64_t now){clock(now);return checkpoint_?checkpoint_->state(now):storage::CheckpointState{};}
} // namespace fathom::capture
