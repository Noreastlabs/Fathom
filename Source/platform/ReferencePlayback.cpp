#include "platform/ReferencePlayback.hpp"
#include <stdexcept>

namespace fathom::platform {
void ReferencePlayback::prepare(reference::Program p) {
    if(prepared_.load(std::memory_order_acquire) || !p.schedule().valid())throw std::invalid_argument("Reference playback is invalid or already prepared");
    program_=std::make_unique<const reference::Program>(std::move(p));
    if(!renderer_.bind(*program_))throw std::invalid_argument("Reference renderer could not bind this stopped program");
    std::vector<scheduler::Plan> plans;plans.push_back(program_->schedule());stream_.prepare(std::move(plans),1);
    prepared_.store(true,std::memory_order_release);
}
scheduler::BlockOutcome ReferencePlayback::render(void* context,const output::Owner& owner,std::uint32_t rate,std::uint32_t frames,Buses& buses) noexcept {
    if(!context)return {};
    auto& self=*static_cast<ReferencePlayback*>(context);
    if(!self.prepared_.load(std::memory_order_acquire))return {};
    if(self.blockedBeforeRender_)return {false,0,true};
    self.buses_=&buses;self.rendered_=true;
    return self.stream_.process(owner,rate,frames,consume,&self);
}
void ReferencePlayback::observe(void* context,const output::Snapshot& state) noexcept {
    if(!context)return;
    auto& self=*static_cast<ReferencePlayback*>(context);
    if(!self.prepared_.load(std::memory_order_acquire))return;
    const bool sameEpoch=state.request.epoch==self.program_->schedule().owner().epoch;
    if(!self.rendered_ && sameEpoch && (state.state==output::State::Fault || state.state==output::State::Unresolved)) {
        self.blockedBeforeRender_=true;self.renderer_.stop();
    }
    self.stream_.observe(state);
    if(self.rendered_ && state.state!=output::State::Running && state.request.epoch==self.program_->schedule().owner().epoch)
        self.renderer_.stop();
}
bool ReferencePlayback::consume(void* context,std::uint64_t begin,std::uint32_t prefix,const scheduler::Fact* facts,std::size_t count) noexcept {
    auto& self=*static_cast<ReferencePlayback*>(context);std::size_t event=0;
    for(std::uint32_t offset=0;offset<prefix;++offset) {
        const auto frame=begin+offset;
        while(event<count && facts[event].frame<=frame)if(!self.renderer_.accept(facts[event++]))return false;
        float mono{};if(!self.renderer_.sampleFrame(frame,mono))return false;
        (*self.buses_)[0][0][offset]=mono;(*self.buses_)[0][1][offset]=mono;
    }
    // A normal terminal prefix can end on Release/CycleCompleted, including zero
    // frames. Those facts still belong to this owner and must not disappear.
    while(event<count) {
        if(facts[event].frame!=begin+prefix || !self.renderer_.accept(facts[event++]))return false;
    }
    return true;
}
}
