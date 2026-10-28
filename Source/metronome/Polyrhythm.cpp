#include "metronome/Polyrhythm.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>

namespace fathom::polyrhythm {
namespace {
void require(bool condition, const char* message) {
    if (!condition)
        throw std::invalid_argument(message);
}
}

void validate(const Ratio& ratio) {
    require(ratio.x >= 1 && ratio.x <= 16 && ratio.y >= 1 && ratio.y <= 16,
            "Polyrhythm layers must be integer counts from 1 through 16");
    require(ratio.x != ratio.y, "Polyrhythm layers must be distinct");
}

int commonCycleTicks(const Ratio& ratio) {
    validate(ratio);
    const auto divisor = std::gcd(ratio.x, ratio.y);
    const auto product = static_cast<std::int64_t>(ratio.x / divisor) * ratio.y;
    if (product > std::numeric_limits<int>::max())
        throw std::overflow_error("Polyrhythm common cycle exceeds supported integer range");
    return static_cast<int>(product);
}

Cycle makeCycle(const Ratio& ratio) {
    const auto ticks = commonCycleTicks(ratio);
    Cycle result;
    result.ticks = ticks;
    result.events.reserve(static_cast<std::size_t>(ratio.x + ratio.y));
    for (int index = 0; index < ratio.x; ++index)
        result.events.push_back({0, index, index * ticks / ratio.x, Rational{index, ratio.x}});
    for (int index = 0; index < ratio.y; ++index)
        result.events.push_back({1, index, index * ticks / ratio.y, Rational{index, ratio.y}});
    std::sort(result.events.begin(), result.events.end(), [](const Event& left, const Event& right) {
        if (left.tick != right.tick)
            return left.tick < right.tick;
        if (left.layer != right.layer)
            return left.layer < right.layer;
        return left.index < right.index;
    });
    return result;
}

scheduler::Plan compilePlan(const Ratio& ratio, const scheduler::Owner& owner,
                            std::uint64_t binding, std::string sourceBinding,
                            std::uint32_t sampleRate, std::uint16_t bpm,
                            scheduler::BeatUnit unit) {
    const auto cycle = makeCycle(ratio);
    scheduler::PlanSpec spec;
    spec.owner = owner;
    spec.binding = binding;
    spec.sourceBinding = std::move(sourceBinding);
    spec.sampleRate = sampleRate;
    spec.bpm = bpm;
    spec.unit = unit;
    spec.cycle = Rational{1};
    spec.intro = Rational{0};
    spec.events.reserve(cycle.events.size());
    for (const auto& event : cycle.events) {
        const auto sourceEvent = static_cast<std::uint32_t>(event.layer * 32 + event.index + 1);
        spec.events.push_back({event.position, sourceEvent,
                               event.layer == 0 ? scheduler::Role::LayerA : scheduler::Role::LayerB,
                               scheduler::Action::Attack});
    }
    return scheduler::compile(spec);
}

PlanBank::PlanBank(const Ratio& ratio, const scheduler::Owner& owner, std::uint64_t binding,
                   std::string sourceBinding, std::uint32_t sampleRate,
                   scheduler::BeatUnit unit, std::uint16_t initialBpm)
    : initialBpm_(initialBpm) {
    if (initialBpm < 20 || initialBpm > 300)
        throw std::invalid_argument("Polyrhythm initial tempo must be from 20 through 300 BPM");
    for (int bpm = 20; bpm <= 300; ++bpm)
        tempos_[static_cast<std::size_t>(bpm - 20)] =
            compilePlan(ratio, owner, binding, sourceBinding, sampleRate,
                        static_cast<std::uint16_t>(bpm), unit);
}

const scheduler::Plan* PlanBank::tempo(int bpm) const noexcept {
    return bpm >= 20 && bpm <= 300 ? &tempos_[static_cast<std::size_t>(bpm - 20)] : nullptr;
}

std::size_t PlanBank::retainedEventCount() const noexcept {
    std::size_t count = 0;
    for (const auto& plan : tempos_)
        count += plan.events().size() + plan.countIn().size();
    return count;
}

void validateLayerControls(const LayerControls& controls) {
    require(controls.volumeA >= 0 && controls.volumeA <= 100,
            "Polyrhythm LayerA volume must be from 0 through 100");
    require(controls.volumeB >= 0 && controls.volumeB <= 100,
            "Polyrhythm LayerB volume must be from 0 through 100");
}

LayerGains resolveLayerGains(const LayerControls& controls) {
    validateLayerControls(controls);
    const auto soloActive = controls.soloA || controls.soloB;
    return {
        controls.muteA || (soloActive && !controls.soloA) ? 0 : controls.volumeA,
        controls.muteB || (soloActive && !controls.soloB) ? 0 : controls.volumeB,
    };
}

bool Renderer::bind(const scheduler::Plan& plan, LayerGains gains) noexcept {
    if (plan_ || failed_ || stopped_ || !plan.valid() || plan.introDuration().n ||
        plan.events().empty() || gains.a < 0 || gains.a > 100 || gains.b < 0 || gains.b > 100)
        return false;
    plan_ = &plan;
    gains_ = gains;
    if (!scheduler::round(plan.events().front().offset, due_)) {
        plan_ = nullptr;
        return false;
    }
    return true;
}

bool Renderer::fail() noexcept {
    failed_ = true;
    stop();
    return false;
}

void Renderer::stop() noexcept {
    stopped_ = true;
    active_ = {};
}

bool Renderer::accept(const scheduler::Fact& fact) noexcept {
    if (!plan_ || failed_ || stopped_ || !(fact.owner == plan_->owner()) ||
        fact.binding != plan_->binding() || fact.frame != nextFrame_)
        return fail();
    if (fact.kind == scheduler::FactKind::CycleCompleted) {
        std::uint64_t expected{};
        scheduler::FramePosition end;
        if (fact.sourceEvent != 0 || fact.role != scheduler::Role::Reference ||
            fact.action != scheduler::Action::Attack ||
            event_ != plan_->events().size() ||
            cycle_ == std::numeric_limits<std::uint64_t>::max() ||
            fact.cycle != cycle_ + 1 ||
            !scheduler::add(anchor_, plan_->duration(), end) ||
            !scheduler::round(end, expected) || fact.frame != expected)
            return fail();
        anchor_ = end;
        ++cycle_;
        event_ = 0;
        scheduler::FramePosition next;
        if (!scheduler::add(anchor_, plan_->events().front().offset, next) ||
            !scheduler::round(next, due_))
            return fail();
        boundaryOpen_ = true;
        return true;
    }
    if (fact.kind != scheduler::FactKind::Event || fact.cycle != cycle_ ||
        event_ >= plan_->events().size())
        return fail();
    const auto& event = plan_->events()[event_];
    std::uint64_t expected{};
    scheduler::FramePosition position;
    if (!scheduler::add(anchor_, event.offset, position) ||
        !scheduler::round(position, expected) || fact.frame != expected ||
        fact.sourceEvent != event.sourceEvent || fact.role != event.role ||
        fact.action != event.action || fact.action != scheduler::Action::Attack ||
        (fact.role != scheduler::Role::LayerA && fact.role != scheduler::Role::LayerB))
        return fail();
    const auto layer = fact.role == scheduler::Role::LayerA ? 0u : 1u;
    boundaryOpen_ = false;
    starts_[layer] = fact.frame;
    active_[layer] = true;
    ++event_;
    if (event_ < plan_->events().size()) {
        scheduler::FramePosition next;
        if (!scheduler::add(anchor_, plan_->events()[event_].offset, next) ||
            !scheduler::round(next, due_))
            return fail();
    } else {
        scheduler::FramePosition boundary;
        if (!scheduler::add(anchor_, plan_->duration(), boundary) ||
            !scheduler::round(boundary, due_))
            return fail();
    }
    return true;
}

bool Renderer::selectTempo(const scheduler::Plan& plan) noexcept {
    if (!plan_ || failed_ || stopped_ || !boundaryOpen_ ||
        !plan_->compatibleTempo(plan))
        return fail();
    plan_ = &plan;
    boundaryOpen_ = false;
    scheduler::FramePosition next;
    if (!scheduler::add(anchor_, plan_->events().front().offset, next) ||
        !scheduler::round(next, due_))
        return fail();
    return true;
}

bool Renderer::setGains(LayerGains gains) noexcept {
    if (!plan_ || failed_ || stopped_ || gains.a < 0 || gains.a > 100 ||
        gains.b < 0 || gains.b > 100)
        return false;
    gains_ = gains;
    return true;
}

bool Renderer::sampleFrame(std::uint64_t frame, LayerFrame& output) noexcept {
    output = {};
    if (!plan_ || failed_ || stopped_ || frame != nextFrame_ || frame >= due_ ||
        nextFrame_ == std::numeric_limits<std::uint64_t>::max())
        return fail();
    boundaryOpen_ = false;
    const auto length = std::max<std::uint32_t>(1, plan_->sampleRate() / 40);
    constexpr double pi = 3.14159265358979323846;
    const auto render = [&](std::size_t layer, double hz, int gain) noexcept {
        if (!active_[layer] || frame < starts_[layer])
            return 0.0f;
        const auto age = frame - starts_[layer];
        if (age >= length) {
            active_[layer] = false;
            return 0.0f;
        }
        const auto envelope = length == 1 ? 1.0 : std::sin(pi * static_cast<double>(age) /
                                                               static_cast<double>(length));
        const auto value = envelope * envelope *
                           std::sin(2.0 * pi * hz * static_cast<double>(age) /
                                    static_cast<double>(plan_->sampleRate()));
        return static_cast<float>(value * static_cast<double>(gain) / 100.0);
    };
    output.a = render(0, 880.0, gains_.a);
    output.b = render(1, 660.0, gains_.b);
    ++nextFrame_;
    return true;
}

} // namespace fathom::polyrhythm
