#include "core/Scheduler.hpp"
#include <algorithm>
#include <limits>
#include <numeric>
#include <set>
#include <tuple>
#include <stdexcept>

namespace fathom::scheduler {
namespace {
constexpr auto limit = std::numeric_limits<std::uint64_t>::max();
bool product(std::uint64_t a, std::uint64_t b, std::uint64_t& out) noexcept {
    if (b && a > limit / b) return false;
    out = a * b; return true;
}
FrameRatio reduced(std::uint64_t n, std::uint64_t d) noexcept {
    const auto g = std::gcd(n, d); return {n / g, d / g};
}
}
bool Owner::valid() const noexcept { return generation && epoch && (id[6] & 0xf0) == 0x40 && (id[8] & 0xc0) == 0x80; }
bool Owner::operator==(const Owner& o) const noexcept { return id == o.id && generation == o.generation && epoch == o.epoch; }
bool add(FrameRatio a, FrameRatio b, FrameRatio& out) noexcept {
    if (!a.d || !b.d) return false;
    const auto g = std::gcd(a.d, b.d);
    std::uint64_t x{}, y{}, d{};
    if (!product(a.n, b.d / g, x) || !product(b.n, a.d / g, y) || x > limit - y || !product(a.d, b.d / g, d)) return false;
    out = reduced(x + y, d); return true;
}
bool multiply(FrameRatio a, std::uint64_t b, FrameRatio& out) noexcept {
    if (!a.d) return false;
    const auto g = std::gcd(b, a.d); std::uint64_t n{};
    if (!product(a.n, b / g, n)) return false;
    out = reduced(n, a.d / g); return true;
}
bool round(FrameRatio a, std::uint64_t& out) noexcept {
    if (!a.d) return false;
    const auto q = a.n / a.d, r = a.n % a.d;
    const bool up = r >= a.d / 2 + a.d % 2;
    if (up && q == limit) return false;
    out = q + (up ? 1 : 0); return true;
}
bool samples(const Rational& q, std::uint32_t rate, std::uint16_t bpm, BeatUnit unit, FrameRatio& out) noexcept {
    if (rate < 8000 || rate > 192000 || bpm < 20 || bpm > 300) return false;
    std::uint64_t un{}, ud{1};
    switch (unit) {
        case BeatUnit::Eighth: un = 1; ud = 2; break;
        case BeatUnit::Quarter: un = 1; break;
        case BeatUnit::DottedQuarter: un = 3; ud = 2; break;
        case BeatUnit::Half: un = 2; break;
        default: return false;
    }
    std::array<std::uint64_t, 4> ns{static_cast<std::uint64_t>(q.numerator()), 60, rate, ud};
    std::array<std::uint64_t, 3> ds{static_cast<std::uint64_t>(q.denominator()), bpm, un};
    for (auto& n : ns) for (auto& d : ds) { const auto g = std::gcd(n, d); n /= g; d /= g; }
    std::uint64_t n{1}, d{1};
    for (auto v : ns) if (!product(n, v, n)) return false;
    for (auto v : ds) if (!product(d, v, d)) return false;
    out = reduced(n, d); return true;
}
Plan::Plan(Plan&& p) noexcept { *this = std::move(p); }
Plan& Plan::operator=(Plan&& p) noexcept {
    if (this != &p) {
        valid_ = p.valid_; owner_ = p.owner_; binding_ = p.binding_; source_ = std::move(p.source_);
        rate_ = p.rate_; unit_ = p.unit_; cycle_ = p.cycle_; duration_ = p.duration_; introDuration_ = p.introDuration_;
        events_ = std::move(p.events_); countIn_ = std::move(p.countIn_); p.valid_ = false;
    }
    return *this;
}
Plan compile(const PlanSpec& s) {
    if (!s.owner.valid() || !s.binding || s.sourceBinding.empty() || s.sourceBinding.size() > 1024
        || !(Rational{0} < s.cycle) || Rational{4096} < s.cycle || Rational{4096} < s.intro
        || s.events.size() > maxPlanEvents || s.countIn.size() > maxPlanEvents - s.events.size())
        throw std::invalid_argument("scheduler owner/source/span/event capacity");
    Plan p;
    p.owner_ = s.owner; p.binding_ = s.binding; p.source_ = s.sourceBinding; p.rate_ = s.sampleRate; p.unit_ = s.unit; p.cycle_ = s.cycle;
    std::uint64_t rounded{};
    if (!samples(s.cycle, s.sampleRate, s.bpm, s.unit, p.duration_) || !round(p.duration_, rounded) || !rounded
        || !samples(s.intro, s.sampleRate, s.bpm, s.unit, p.introDuration_))
        throw std::invalid_argument("scheduler tempo/sample range or sub-sample cycle");
    auto make = [&](const std::vector<EventSpec>& input, const Rational& span, bool intro) {
        std::vector<TimedEvent> out; out.reserve(input.size());
        std::set<std::tuple<std::uint32_t, Role, Action>> identities;
        for (const auto& e : input) {
            if (!identities.emplace(e.sourceEvent, e.role, e.action).second) throw std::invalid_argument("duplicate scheduled event identity");
            if (span < e.at || (intro && !(e.at < span)) || (!intro && e.at == span && e.action == Action::Attack)
                || static_cast<unsigned>(e.role) > static_cast<unsigned>(Role::CountIn)
                || static_cast<unsigned>(e.action) > static_cast<unsigned>(Action::Silence)
                || (intro != (e.role == Role::CountIn))) throw std::invalid_argument("scheduler event phase/span/role");
            FrameRatio offset;
            if (!samples(e.at, s.sampleRate, s.bpm, s.unit, offset)) throw std::overflow_error("scheduler event arithmetic");
            out.push_back({e.at, offset, e.sourceEvent, e.role, e.action});
        }
        std::stable_sort(out.begin(), out.end(), [](const auto& a, const auto& b) {
            if (!(a.structural == b.structural)) return a.structural < b.structural;
            return a.action != Action::Attack && b.action == Action::Attack;
        });
        return out;
    };
    p.events_ = make(s.events, s.cycle, false); p.countIn_ = make(s.countIn, s.intro, true); p.valid_ = true; return p;
}
bool Plan::compatibleTempo(const Plan& p) const noexcept {
    if (!valid_ || !p.valid_ || !(owner_ == p.owner_) || binding_ != p.binding_ || source_ != p.source_
        || rate_ != p.rate_ || unit_ != p.unit_ || !(cycle_ == p.cycle_) || p.introDuration_.n || events_.size() != p.events_.size()) return false;
    for (std::size_t i = 0; i < events_.size(); ++i) {
        const auto& a = events_[i]; const auto& b = p.events_[i];
        if (!(a.structural == b.structural) || a.sourceEvent != b.sourceEvent || a.role != b.role || a.action != b.action) return false;
    }
    return true;
}
bool UrgentStop::request(const Owner& owner, std::uint64_t binding) noexcept {
    if (!owner_.valid() || !binding_ || !(owner_ == owner) || binding_ != binding) return false;
    requested_.store(true, std::memory_order_release); return true;
}
bool UrgentStop::consume(const Owner& owner, std::uint64_t binding) noexcept {
    if (!(owner_ == owner) || binding_ != binding) return false;
    return requested_.exchange(false, std::memory_order_acq_rel);
}
bool PlanPool::prepare(Plan&& plan, PlanToken& token) {
    if (!plan.valid() || next_ > limit / 4) return false;
    for (std::size_t i = 0; i < slots_.size(); ++i) {
        auto& s = slots_[i];
        if (s.word.load(std::memory_order_acquire) != Free) continue;
        s.plan = std::move(plan); token = {static_cast<std::uint8_t>(i), next_++};
        s.word.store(word(token, Ready), std::memory_order_release); return true;
    }
    return false;
}
const Plan* PlanPool::acquire(PlanToken t) noexcept {
    if (t.slot >= slots_.size() || !t.incarnation || t.incarnation > limit / 4) return nullptr;
    auto expected = word(t, Ready); auto& s = slots_[t.slot];
    return s.word.compare_exchange_strong(expected, word(t, Active), std::memory_order_acq_rel) ? &s.plan : nullptr;
}
bool PlanPool::retire(PlanToken t) noexcept {
    if (t.slot >= slots_.size() || !t.incarnation || t.incarnation > limit / 4) return false;
    auto expected = word(t, Active);
    return slots_[t.slot].word.compare_exchange_strong(expected, word(t, Retired), std::memory_order_release, std::memory_order_relaxed);
}
bool PlanPool::reclaim(PlanToken t) {
    if (t.slot >= slots_.size() || !t.incarnation || t.incarnation > limit / 4) return false;
    auto& s = slots_[t.slot];
    if (s.word.load(std::memory_order_acquire) != word(t, Retired)) return false;
    s.plan = Plan{}; s.word.store(Free, std::memory_order_release); return true;
}
bool Cursor::start(const Plan& p, const Owner& o, std::uint64_t binding) noexcept {
    if (status_.state != State::Idle || !p.valid() || !(p.owner() == o) || p.binding() != binding) return false;
    plan_ = &p; status_ = {}; status_.owner = o; status_.binding = binding;
    status_.state = p.introDuration().n ? State::CountIn : State::Running; anchor_ = {}; event_ = 0; consumedBoundary_ = false; return true;
}
void Cursor::retainEndpointCompletion() noexcept {
    if (status_.state != State::Running || !plan_ || consumedBoundary_) return;
    FramePosition end; std::uint64_t frame{};
    if (add(anchor_, plan_->duration(), end) && round(end, frame) && frame == status_.processedThrough
        && status_.completedCycles != limit) {
        ++status_.completedCycles; status_.boundaryFactPending = true;
    }
}
bool Cursor::fail(StopReason reason, std::uint64_t uncertain) noexcept {
    retainEndpointCompletion();
    status_.state = State::Terminal; status_.reason = reason;
    status_.uncertainThrough = std::max(status_.uncertainThrough, uncertain); return false;
}
bool Cursor::stop(const Owner& o, std::uint64_t key) noexcept {
    if (!(status_.owner == o) || status_.binding != key || status_.state == State::Idle) return false;
    if (status_.state != State::Terminal) fail(StopReason::Requested, status_.processedThrough);
    return true;
}
bool Cursor::confirm(const Owner& o, std::uint64_t through) noexcept {
    if (!(status_.owner == o) || status_.state == State::Idle || through > status_.processedThrough
        || (status_.hasConfirmation && through < status_.confirmedThrough)) return false;
    status_.confirmedThrough = through; status_.hasConfirmation = true; return true;
}
bool Cursor::acknowledge(const Owner& o, std::uint64_t key) noexcept {
    if (status_.state != State::Terminal || !(status_.owner == o) || status_.binding != key) return false;
    status_ = {}; plan_ = nullptr; return true;
}
bool Cursor::process(std::uint32_t frames, const Owner& observed, Sink sink, void* context,
                     BoundaryReducer reducer, void* reducerContext, UrgentStop* urgent) noexcept {
    if (status_.state == State::Idle || status_.state == State::Terminal) return false;
    if (!(observed == status_.owner)) return fail(StopReason::InvalidFormat, status_.processedThrough);
    if (!frames || frames > maxCallbackFrames || !sink || status_.processedThrough > limit - frames)
        return fail(StopReason::InvalidBlock, status_.processedThrough);
    const auto end = status_.processedThrough + frames;
    if (urgent && urgent->consume(status_.owner, status_.binding)) return fail(StopReason::Requested, end);
    std::size_t work{};
    while (true) {
        const bool intro = status_.state == State::CountIn;
        const auto& events = intro ? plan_->countIn() : plan_->events();
        const bool boundary = event_ == events.size();
        FramePosition position;
        if (!add(anchor_, boundary ? (intro ? plan_->introDuration() : plan_->duration()) : events[event_].offset, position))
            return fail(StopReason::Arithmetic, end);
        std::uint64_t at{};
        if (!round(position, at) || at < status_.processedThrough) return fail(StopReason::Arithmetic, end);
        if (at >= end) { status_.processedThrough = end; return true; }
        if (++work > maxCallbackEvents) return fail(StopReason::WorkLimit, end);
        status_.processedThrough = at;
        Fact f; f.owner = status_.owner; f.binding = status_.binding; f.frame = at; f.cycle = status_.completedCycles;
        if (!boundary) {
            const auto& e = events[event_++]; f.kind = FactKind::Event; f.sourceEvent = e.sourceEvent; f.role = e.role; f.action = e.action;
            if (!sink(context, f)) return fail(StopReason::FactOverflow, end);
            continue;
        }
        anchor_ = position; event_ = 0;
        if (intro) {
            status_.state = State::Running; f.kind = FactKind::CountInEnded;
            if (!sink(context, f)) return fail(StopReason::FactOverflow, end);
            continue;
        }
        if (status_.completedCycles == limit) return fail(StopReason::Arithmetic, end);
        consumedBoundary_ = true;
        f.kind = FactKind::CycleCompleted; f.cycle = ++status_.completedCycles;
        if (!sink(context, f)) {
            status_.boundaryFactPending = true;
            return fail(StopReason::FactOverflow, end);
        }
        const auto decision = reducer ? reducer(reducerContext, f) : BoundaryDecision{};
        if (decision.action == BoundaryAction::Stop) return fail(StopReason::Requested, end);
        if (decision.action != BoundaryAction::Continue && decision.action != BoundaryAction::Tempo)
            return fail(StopReason::InvalidDecision, end);
        if (decision.action == BoundaryAction::Tempo) {
            if (!decision.tempo || !plan_->compatibleTempo(*decision.tempo)) return fail(StopReason::InvalidTempo, end);
            plan_ = decision.tempo;
        }
        consumedBoundary_ = false;
    }
}
} // namespace fathom::scheduler
