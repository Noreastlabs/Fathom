#pragma once
#include "platform/AudioOutputMac.hpp"
#include <atomic>
#include <memory>
#include <stdexcept>
#include <vector>
namespace fathom::desktop {
// One UI publisher, one audio callback reader. Publish only while the owning
// lifecycle is Ready and its prior outcome has been explicitly acknowledged.
// Old providers are never mutated or freed while callbacks can still see them.
// The owning view destroys this slot ONLY after successful disconnect/flush.
// A generation limit bounds retention; closing the view starts a fresh slot.
template<class Provider> class PreparedToolSound final {
public:
    void publish(std::unique_ptr<Provider> next){
        if(!next||retained_.size()>=256)throw std::runtime_error("256 sound checks retained. Finish and leave this tool before preparing another.");
        auto* value=next.get();retained_.push_back(std::move(next));current_.store(value,std::memory_order_release);
    }
    Provider* current()const noexcept{return current_.load(std::memory_order_acquire);}
    static void observe(void* context,const output::Snapshot& state)noexcept{
        if(context)if(auto* p=static_cast<PreparedToolSound*>(context)->current())Provider::observe(p,state);
    }
    static scheduler::BlockOutcome render(void* context,const output::Owner& owner,std::uint32_t rate,std::uint32_t frames,platform::Buses& buses)noexcept{
        if(context)if(auto* p=static_cast<PreparedToolSound*>(context)->current())return Provider::render(p,owner,rate,frames,buses);
        return {};
    }
private:
    std::atomic<Provider*> current_{nullptr};
    std::vector<std::unique_ptr<Provider>> retained_;
};
}
