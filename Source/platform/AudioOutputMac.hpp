#pragma once
#include "core/AudioOutputLifecycle.hpp"
#include "core/ScheduledStream.hpp"
#include <memory>
#include <string>
#include <vector>

namespace fathom::platform {
struct OutputCapability final {
    bool valid{};
    std::uint32_t object{}, rate{}, physicalFrames{}, outputChannels{}, minFrames{}, maxFrames{};
    std::string uid, name, error;
    std::vector<std::array<double,2>> rates;
};
// Raw CoreAudio getters only. Does not construct/open a JUCE audio device.
OutputCapability defaultOutputCapability();
std::uint64_t monotonicNs() noexcept;
struct NativeEvent final {
    std::uint64_t ns{}, epoch{}, serial{}, rawHost{};
    std::uint32_t kind{}, object{}, selector{}, scope{}, element{}, frames{}, flags{};
    std::int32_t status{};
    double sampleTime{}, rateScalar{}, peak{};
    std::array<char,160> text{};
};
struct OutputStatus final {
    output::Snapshot lifecycle;
    output::MixSettings mix;
    bool cleanupFailed{};
    std::uint64_t firstSilentCallbackNs{}; // actual zeroed client callback; 0 = not observed
    std::uint64_t callbacks{}, renderedBlocks{}, commandAccepted{}, commandRejected{}, nativeSkips{}, overloads{};
};
using Buses = std::array<std::array<std::array<float,output::maxOutputFrames>,2>,4>;
// Called only on the audio callback. The provider/context must outlive disconnect.
// No allocation/locks/files/UI, valid finite [-1,1] samples, no independent timer.
using RenderOutput = bool (*)(void*, const output::Owner&, std::uint32_t rate, std::uint32_t frames, Buses&) noexcept;
using ScheduledRender = scheduler::BlockOutcome (*)(void*, const output::Owner&, std::uint32_t rate, std::uint32_t frames, Buses&) noexcept;
// Invoked on the callback, and after device stop/flush on the control thread.
// Context must outlive disconnect; never mutate it concurrently from UI/service.
using OutputObserver = void (*)(void*, const output::Snapshot&) noexcept;
enum class OutputCommand { Acknowledge, Start, Pause, PauseRetained, Resume, Stop, ResolveOutcome, Mix };
struct Control final {
    OutputCommand op{};
    std::uint64_t epoch{}, token{}, requestedNs{};
    output::Owner owner, nextOwner;
    output::MixSettings mix;
};
// Sole message-thread owner, sole callback Lifecycle writer while open.
// service() must run regularly; all methods except the provider are message-thread only.
class AudioOutputMac final {
public:
    AudioOutputMac();
    ~AudioOutputMac();
    AudioOutputMac(const AudioOutputMac&) = delete;
    AudioOutputMac& operator=(const AudioOutputMac&) = delete;
    bool connect(const OutputCapability&, output::Format, RenderOutput = nullptr, void* context = nullptr,
                 OutputObserver = nullptr, ScheduledRender = nullptr);
    bool send(Control); // Pause/Stop have an independent urgent queue.
    void service();
    OutputStatus status() const;
    const std::string& error() const;
    bool nextEvent(NativeEvent&); // bounded diagnostics; no disk I/O inside adapter
    bool disconnect(); // refuses unresolved owner; close/reopen never starts music
    output::Snapshot shutdown(); // forced device stop; caller retains unresolved outcome before destruction
    void injectFault(output::Fault); // explicit same path for deterministic platform failure tests
private:
    friend struct OutputTestAccess;
    struct Impl;
    std::unique_ptr<Impl> p_;
};
} // namespace fathom::platform
