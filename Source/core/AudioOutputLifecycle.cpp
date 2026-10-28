#include "core/AudioOutputLifecycle.hpp"
#include <algorithm>
#include <cmath>
#include <limits>

namespace fathom::output {
bool Format::valid() const noexcept { return rate >= 8000 && rate <= 192000 && frames > 0 && frames <= maxOutputFrames; }
bool Lifecycle::configure(Request r) noexcept {
    if (!r.epoch || r.epoch <= lastEpoch_ || !r.format.valid() || !r.selectedPhysical
        || s_.ownsOutcome || s_.state == State::Running || s_.state == State::Paused) return false;
    s_ = {}; s_.request = r; s_.state = State::Awaiting; lastEpoch_ = r.epoch; lastSubmittedSequence_ = 0; pauseRetained_ = false; return true;
}
bool Lifecycle::announce(CachedAnnouncement c) noexcept {
    if (!current(c.epoch) || s_.state == State::Fault) return false;
    if (s_.announcements || c.stampNs < s_.request.stampNs) return invalidate(c.epoch, Fault::Restart, c.stampNs, s_.submittedFrames), false;
    s_.cached = c; ++s_.announcements;
    if (!(c.format == s_.request.format)) return invalidate(c.epoch, Fault::FormatMismatch, c.stampNs, s_.submittedFrames), false;
    return true;
}
bool Lifecycle::observe(Observation o) noexcept {
    if (!current(o.epoch) || s_.state == State::Fault) return false;
    if (!s_.announcements || !o.physicalKnown || !o.ioKnown || !o.routeKnown) {
        if (s_.state != State::Awaiting) invalidate(o.epoch, Fault::InvalidObservation, o.callbackStampNs, s_.submittedFrames);
        return false; // incomplete initial evidence is silent; lost established evidence latches
    }
    if (!o.callbackSequence || o.callbackSequence <= s_.observation.callbackSequence
        || o.callbackStampNs < s_.cached.stampNs || o.callbackStampNs < s_.observation.callbackStampNs
        || o.queryStampNs < s_.request.stampNs || o.queryStampNs < s_.observation.queryStampNs || o.queryStampNs > o.callbackStampNs)
        return invalidate(o.epoch, Fault::InvalidObservation, o.callbackStampNs, s_.submittedFrames), false;
    if (!(o.queriedIO == s_.request.format) || o.callbackFrames != s_.request.format.frames
        || !o.nativeIOObject || o.nativeIOObject != o.queriedIOObject || o.physicalObject != s_.request.selectedPhysical
        || o.physicalRate != s_.request.format.rate || !o.physicalFrames
        || !o.selectedInFullRoute || !o.selectedInActiveRoute)
        return invalidate(o.epoch, Fault::FormatMismatch, o.callbackStampNs, s_.submittedFrames), false;
    s_.observation = o;
    if (s_.state == State::Awaiting) { s_.state = State::Observed; s_.observationToken = o.callbackSequence; }
    return true;
}
bool Lifecycle::acknowledge(std::uint64_t epoch, std::uint64_t token) noexcept {
    if (!current(epoch) || s_.state != State::Observed || !token || token != s_.observationToken) return false;
    s_.state = State::Ready; return true;
}
bool Lifecycle::start(const Owner& owner) noexcept {
    if (s_.state != State::Ready || s_.ownsOutcome || !owner.valid() || owner.epoch != s_.request.epoch) return false;
    s_.owner = owner; s_.ownsOutcome = true; s_.submittedFrames = s_.confirmedFrames = s_.uncertainThrough = s_.requestedStopNs = s_.firstSilenceNs = 0;
    s_.hasConfirmation = false; s_.pendingOutcome = false; s_.stopRequested = false; s_.state = State::Running; return true;
}
void Lifecycle::retainStop(std::uint64_t stamp, std::uint64_t uncertain) noexcept {
    if (!s_.stopRequested) { s_.firstSilenceNs = stamp; s_.stopRequested = true; }
    s_.requestedStopNs = stamp;
    s_.uncertainThrough = std::max({s_.uncertainThrough, s_.submittedFrames, uncertain});
}
bool Lifecycle::pause(const Owner& owner, std::uint64_t stamp, std::uint64_t uncertain) noexcept {
    if (!matches(owner) || (s_.state != State::Running && s_.state != State::Paused)) return false;
    if (s_.state == State::Paused) return true;
    pauseRetained_ = false;
    retainStop(stamp, uncertain); s_.state = State::Paused; return true;
}
bool Lifecycle::acknowledgePause(const Owner& owner) noexcept {
    if (!matches(owner) || s_.state != State::Paused) return false;
    pauseRetained_ = true; return true;
}
bool Lifecycle::resume(const Owner& previous, const Owner& next) noexcept {
    if (!matches(previous) || s_.state != State::Paused || s_.pendingOutcome || !pauseRetained_
        || !next.valid() || next.id != previous.id || next.epoch != previous.epoch || next.generation <= previous.generation) return false;
    s_.owner = next; s_.submittedFrames = s_.confirmedFrames = s_.uncertainThrough = s_.requestedStopNs = s_.firstSilenceNs = 0;
    s_.hasConfirmation = false; s_.stopRequested = false; pauseRetained_ = false; s_.state = State::Running; return true;
}
bool Lifecycle::stop(const Owner& owner, std::uint64_t stamp, std::uint64_t uncertain) noexcept {
    if (!matches(owner)) return false;
    if (s_.state == State::Unresolved || s_.state == State::Fault) return true;
    if (s_.state != State::Running && s_.state != State::Paused) return false;
    retainStop(stamp, uncertain); s_.pendingOutcome = true; s_.state = State::Unresolved; return true;
}
bool Lifecycle::invalidate(std::uint64_t epoch, Fault f, std::uint64_t stamp, std::uint64_t uncertain) noexcept {
    if (!current(epoch) || f == Fault::None || static_cast<unsigned>(f) > static_cast<unsigned>(Fault::InvalidObservation)) return false;
    if (s_.state == State::Fault) return true;
    retainStop(stamp, uncertain); s_.fault = f; s_.pendingOutcome = s_.ownsOutcome; s_.state = State::Fault; return true;
}
bool Lifecycle::invalidateOwner(const Owner& owner, Fault f, std::uint64_t stamp, std::uint64_t uncertain) noexcept {
    if (!matches(owner)) return false;
    return invalidate(owner.epoch, f, stamp, uncertain);
}
bool Lifecycle::submitted(const Owner& owner, std::uint64_t sequence, std::uint32_t frames) noexcept {
    if (!matches(owner) || s_.state != State::Running || sequence != s_.observation.callbackSequence || sequence <= lastSubmittedSequence_
        || !frames || frames > s_.observation.callbackFrames) return false;
    if (s_.submittedFrames > std::numeric_limits<std::uint64_t>::max() - frames)
        return invalidate(s_.request.epoch, Fault::Clock, s_.observation.callbackStampNs, s_.submittedFrames), false;
    s_.submittedFrames += frames; lastSubmittedSequence_ = sequence; return true;
}
bool Lifecycle::confirm(const Owner& owner, std::uint64_t through) noexcept {
    if (!matches(owner) || through > s_.submittedFrames || (s_.hasConfirmation && through < s_.confirmedFrames)) return false;
    if (s_.state == State::Paused && (!s_.hasConfirmation || through != s_.confirmedFrames)) pauseRetained_ = false;
    s_.confirmedFrames = through; s_.hasConfirmation = true; return true;
}
bool Lifecycle::resolveOutcome(const Owner& owner) noexcept {
    if (!matches(owner) || !s_.pendingOutcome || (s_.state != State::Unresolved && s_.state != State::Fault)) return false;
    s_.pendingOutcome = false; s_.ownsOutcome = false; // snapshot facts remain available until explicit new start/configure
    if (s_.state == State::Unresolved) s_.state = State::Ready;
    return true;
}
bool Lifecycle::close() noexcept {
    if (s_.ownsOutcome || s_.state == State::Running || s_.state == State::Paused) return false;
    s_.state = State::Closed; return true;
}
bool MixSettings::valid() const noexcept {
    if (master < 0 || master > 100 || muteMask > 15 || soloAB > 3) return false;
    for (auto v : bus) if (v < 0 || v > 100) return false;
    return true;
}
bool Mixer::apply(MixSettings s) noexcept { if (!s.valid()) return false; settings_ = s; return true; }
std::array<float,4> Mixer::gains() const noexcept {
    std::array<float,4> g{};
    if (settings_.masterMute) return g;
    for (std::size_t i = 0; i < g.size(); ++i) {
        const bool soloSuppressed = i >= 2 && settings_.soloAB && !(settings_.soloAB & (1U << (i - 2)));
        if (!(settings_.muteMask & (1U << i)) && !soloSuppressed)
            g[i] = 0.25f * (static_cast<float>(settings_.bus[i]) / 100.0f) * (static_cast<float>(settings_.master) / 100.0f);
    }
    return g;
}
bool Mixer::sample(const std::array<float,4>& buses, float& result) const noexcept {
    result = 0.0f;
    for (auto v : buses) if (!std::isfinite(v) || v < -1.0f || v > 1.0f) return false;
    const auto g = gains();
    for (std::size_t i = 0; i < g.size(); ++i) result += buses[i] * g[i];
    return true;
}
const char* stateText(State state) noexcept {
    switch (state) {
        case State::Closed: return "Output closed";
        case State::Awaiting: return "Waiting for silent output observation";
        case State::Observed: return "Output observed; acknowledge to enable Start";
        case State::Ready: return "Output ready and stopped";
        case State::Running: return "Output running";
        case State::Paused: return "Output paused; explicit resume required";
        case State::Unresolved: return "Output stopped; prior outcome must be resolved";
        case State::Fault: return "Output stopped by an error; explicit recovery required";
    }
    return "Unknown output state";
}
const char* faultText(Fault f) noexcept {
    switch (f) {
        case Fault::None: return "No output error";
        case Fault::FormatMismatch: return "Output format or route changed; stop and reconfigure";
        case Fault::Restart: return "Unexpected output restart; stop and reconfigure";
        case Fault::DeviceLost: return "Output device unavailable; select an available output";
        case Fault::Sleep: return "Computer slept; recover output explicitly before playing";
        case Fault::Clock: return "Output clock discontinuity; playback stopped";
        case Fault::QueueOverflow: return "Output message capacity exceeded; playback stopped";
        case Fault::Backend: return "Audio device reported an error; playback stopped";
        case Fault::Render: return "Reference output could not be rendered safely";
        case Fault::InvalidObservation: return "Output observation is stale or invalid; reconfigure";
    }
    return "Unknown output error";
}
} // namespace fathom::output
