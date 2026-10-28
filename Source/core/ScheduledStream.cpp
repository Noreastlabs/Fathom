#include "core/ScheduledStream.hpp"
#include <stdexcept>

namespace fathom::scheduler {
void ScheduledStream::prepare(std::vector<Plan> plans, std::uint64_t stopAfter,
                              std::uint32_t every, std::uint32_t rampIndex) {
    if(prepared_.load(std::memory_order_acquire) || plans.empty() || plans.size()>8 || !plans[0].valid()
        || every>32 || (every && (rampIndex==0 || rampIndex>=plans.size())))
        throw std::invalid_argument("Invalid or already prepared schedule");
    for(std::size_t i=1;i<plans.size();++i)
        if(!plans[0].compatibleTempo(plans[i])) throw std::invalid_argument("Incompatible tempo schedule");
    plans_=std::move(plans);stopAfter_=stopAfter;rampEvery_=every;rampIndex_=rampIndex;rampArmed_=every!=0;
    prepared_.store(true,std::memory_order_release);
}
bool ScheduledStream::tempo(TempoCommand c) noexcept {return commands_.push(c);}
bool ScheduledStream::collect(void* p,const Fact& f) noexcept {
    auto& s=*static_cast<ScheduledStream*>(p);
    if(s.count_==s.blockFacts_.size() || !s.facts_.push(f)) return false;
    if(f.kind!=FactKind::Event)s.view_.phaseOrigin=f.frame;
    s.blockFacts_[s.count_++]=f;return true;
}
BoundaryDecision ScheduledStream::boundary(void* p,const Fact& f) noexcept {
    auto& s=*static_cast<ScheduledStream*>(p);
    if(s.stopAfter_ && f.cycle>=s.stopAfter_)return {BoundaryAction::Stop,nullptr};
    if(s.manualPending_) {
        s.manualPending_=false;s.rampArmed_=false;s.tempoIndex_=s.pendingIndex_;
        return {BoundaryAction::Tempo,&s.plans_[s.tempoIndex_]};
    }
    if(s.rampArmed_ && f.cycle%s.rampEvery_==0) {
        s.rampArmed_=false;s.tempoIndex_=s.rampIndex_;
        return {BoundaryAction::Tempo,&s.plans_[s.tempoIndex_]};
    }
    return {};
}
void ScheduledStream::publish() noexcept {
    view_.cursor=cursor_.snapshot();view_.tempoIndex=tempoIndex_;view_.failed=failed_;
    if(!plans_.empty())view_.phaseSpan=view_.cursor.state==State::CountIn?plans_[0].introDuration():plans_[tempoIndex_].duration();
    if(!views_.push(view_))++view_.displayDrops; // Old display copies never drive the clock.
}
BlockOutcome ScheduledStream::process(const Owner& owner,std::uint32_t rate,std::uint32_t frames,
                                     BlockConsumer consumer,void* context) noexcept {
    if(!prepared_.load(std::memory_order_acquire))return {};
    if(failed_)return {false,0,true};
    const auto& first=plans_[0];
    if(!(owner==first.owner()) || rate!=first.sampleRate() || !consumer || !frames || frames>output::maxOutputFrames) {
        failed_=true;cursor_.stop(first.owner(),first.binding());publish();return {};
    }
    if(cursor_.snapshot().state==State::Idle && !cursor_.start(first,owner,first.binding()))return {};
    if(cursor_.snapshot().state==State::Terminal)return {!failed_,0,true};
    TempoCommand c;
    for(int i=0;i<32 && commands_.pop(c);++i) {
        if(!(c.owner==owner) || c.binding!=first.binding() || !c.sequence || c.sequence<=lastSequence_
            || c.index==0 || c.index>=plans_.size()) {++view_.rejectedCommands;continue;}
        lastSequence_=c.sequence;pendingIndex_=c.index;manualPending_=true;++view_.acceptedCommands;
    }
    count_=0;const auto begin=cursor_.snapshot().processedThrough;
    const bool ok=cursor_.process(frames,owner,collect,this,boundary,this);
    const auto s=cursor_.snapshot();const bool terminal=s.state==State::Terminal;
    const bool normal=terminal && s.reason==StopReason::Requested;
    std::uint32_t prefix=ok?frames:normal?static_cast<std::uint32_t>(s.processedThrough-begin):0;
    bool valid=(ok || normal) && prefix<=frames;
    if(valid)valid=consumer(context,begin,prefix,blockFacts_.data(),count_);
    if(!valid){failed_=true;prefix=0;cursor_.stop(owner,first.binding());}
    ++view_.block;view_.blockBegin=begin;view_.prefix=prefix;publish();
    return {valid,prefix,terminal || !valid};
}
void ScheduledStream::observe(const output::Snapshot& s) noexcept {
    if(!prepared_.load(std::memory_order_acquire))return;
    const auto current=cursor_.snapshot();
    if(current.state!=State::Idle && current.state!=State::Terminal && s.state!=output::State::Running
        && s.request.epoch==current.owner.epoch) {
        if((s.owner.valid() && !(s.owner==current.owner)) || s.state==output::State::Fault)failed_=true;
        cursor_.stop(current.owner,current.binding);view_.prefix=0;publish();
    }
}
bool ScheduledStream::nextView(StreamView& v) noexcept {return views_.pop(v);}
bool ScheduledStream::nextFact(Fact& f) noexcept {return facts_.pop(f);}
}
