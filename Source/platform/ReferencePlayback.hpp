#pragma once
#include "core/ReferenceAudio.hpp"
#include "platform/AudioOutputMac.hpp"

namespace fathom::platform {
// Shared reference consumer. Prepare while stopped; retain this entire object and
// its Program until AudioOutputMac disconnect/shutdown has flushed the callback.
class ReferencePlayback final {
public:
    void prepare(reference::Program); // exactly once, control thread
    const reference::Program* program() const noexcept { return program_.get(); } // control, before start/after flush
    scheduler::ScheduledStream& stream() noexcept { return stream_; }
    static scheduler::BlockOutcome render(void*,const output::Owner&,std::uint32_t,std::uint32_t,Buses&) noexcept;
    static void observe(void*,const output::Snapshot&) noexcept;
private:
    static bool consume(void*,std::uint64_t,std::uint32_t,const scheduler::Fact*,std::size_t) noexcept;
    std::unique_ptr<const reference::Program> program_;
    reference::Renderer renderer_;
    scheduler::ScheduledStream stream_;
    std::atomic<bool> prepared_{false};
    bool rendered_{}, blockedBeforeRender_{};
    Buses* buses_{};
};
}
