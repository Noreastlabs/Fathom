#include "storage/CheckpointCoordinator.hpp"
#include "storage/Recovery.hpp"

namespace fathom::storage {
CheckpointCoordinator::CheckpointCoordinator(ProfileStore& s,std::string owner,std::string kind,Value c,std::string prefix)
 :store_(s),owner_(std::move(owner)),kind_(std::move(kind)),prefix_(std::move(prefix)),context_(std::move(c)){
    validateUuid(owner_);validateContext(context_,kind_);
}
void CheckpointCoordinator::clock(std::int64_t now){
    if(now<0||(lastClock_&&now<*lastClock_))throw EnvelopeError("CHECKPOINT_CLOCK","Control clock must be nonnegative monotonic milliseconds");lastClock_=now;
}
void CheckpointCoordinator::offer(CheckpointSnapshot snapshot,std::int64_t now,bool force){
    clock(now);validateCheckpoint(owner_,snapshot.generation,snapshot.sequence,snapshot.bytes,kind_,context_);
    const auto cp=parseCanonical(snapshot.bytes);const auto& q=cp.object().at("practice_snapshot");validateUnsealedRecoverySnapshot(q);
    Captured incoming{std::move(snapshot),now,force,q.object().at("active"),!cp.object().at("sealed_envelope").null()};
    if(highWater_){const auto& old=highWater_->snapshot;const auto& fresh=incoming.snapshot;
        if(fresh.generation<old.generation||(fresh.generation==old.generation&&fresh.sequence<old.sequence))throw EnvelopeError("CHECKPOINT_STALE","Generation or sequence regressed");
        if(fresh.generation==old.generation&&fresh.sequence==old.sequence){if(fresh.bytes!=old.bytes)throw EnvelopeError("CHECKPOINT_CONFLICT","Same checkpoint position has different bytes");if(latest_)latest_->forced=latest_->forced||force;submitIfDue(now);return;}
        if(highWater_->sealed)throw EnvelopeError("CHECKPOINT_SEALED","A sealed outcome cannot be replaced by a new checkpoint");
    }
    highWater_=incoming;latest_=std::move(incoming);submitIfDue(now);
}
void CheckpointCoordinator::submitIfDue(std::int64_t now){
    if(halted_||future_||!latest_)return;
    if(lastSubmit_&&!latest_->forced&&now-*lastSubmit_<1000)return;
    pending_=std::move(latest_);latest_.reset();lastSubmit_=now;
    const auto& s=pending_->snapshot;
    future_.emplace(store_.checkpoint(prefix_+"."+std::to_string(s.generation)+"."+std::to_string(s.sequence),owner_,s.generation,s.sequence,s.bytes));
}
void CheckpointCoordinator::poll(std::int64_t now){
    clock(now);
    if(future_&&now-*lastSubmit_>=1000)timeout_=true;
    if(future_&&future_->wait_for(std::chrono::milliseconds(0))==std::future_status::ready){
        reply_=future_->get();future_.reset();
        if(reply_->status==Status::Confirmed){acknowledged_=pending_;pending_.reset();}
        else{halted_=true;} // Preserve failed original pending and newer latest, never retry implicitly.
    }
    submitIfDue(now);
}
CheckpointState CheckpointCoordinator::state(std::int64_t now){
    clock(now);if(future_&&now-*lastSubmit_>=1000)timeout_=true;CheckpointState s;s.initialAcknowledged=acknowledged_.has_value();s.inFlight=future_.has_value();s.hasUnsaved=pending_.has_value()||latest_.has_value();s.lastReply=reply_;
    if(acknowledged_)s.acknowledged=acknowledged_->snapshot;if(pending_)s.inFlightSnapshot=pending_->snapshot;if(latest_)s.unsaved=latest_->snapshot;
    s.stopRequired=true;
    if(halted_){s.code="CHECKPOINT_WRITE_UNRESOLVED";return s;}
    if(timeout_){s.code="CHECKPOINT_ACK_TIMEOUT";return s;}
    if(!acknowledged_){s.code="INITIAL_CHECKPOINT_REQUIRED";return s;}
    if(highWater_&&confirmedRecoveryQuantity(acknowledged_->active)+Rational(2)<confirmedRecoveryQuantity(highWater_->active)){s.code="CHECKPOINT_BACKLOG";return s;}
    s.stopRequired=false;s.code=s.hasUnsaved?"CHECKPOINT_UNSAVED":"CHECKPOINT_ACKNOWLEDGED";return s;
}
bool CheckpointCoordinator::retryPendingForExit(std::int64_t now){
    clock(now);if(future_||!pending_)return false;
    const auto& s=pending_->snapshot;lastSubmit_=now;
    future_.emplace(store_.checkpoint(prefix_+"."+std::to_string(s.generation)+"."+std::to_string(s.sequence),owner_,s.generation,s.sequence,s.bytes));
    return true; // exact originally admitted payload; never submit discarded latest
}
bool CheckpointCoordinator::resolveAcknowledgedWhileStopped(){
    if(halted_||future_||latest_||pending_||!acknowledged_)return false;
    timeout_=false;return true;
}
} // namespace fathom::storage
