#include "metronome/Polyrhythm.hpp"

#include <filesystem>
#include <fstream>
#include <cmath>
#include <array>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

using namespace fathom;
using namespace fathom::polyrhythm;

namespace {
struct CursorTrace {
    std::vector<scheduler::Fact> facts;
    static bool sink(void* context, const scheduler::Fact& fact) noexcept {
        static_cast<CursorTrace*>(context)->facts.push_back(fact);
        return true;
    }
};

struct ReliabilityTrace {
    std::vector<scheduler::Fact> facts;
    const scheduler::Plan* changedTempo{};
    static bool sink(void* context, const scheduler::Fact& fact) noexcept {
        static_cast<ReliabilityTrace*>(context)->facts.push_back(fact);
        return true;
    }
    static scheduler::BoundaryDecision boundary(void* context,
                                                 const scheduler::Fact& fact) noexcept {
        const auto* state = static_cast<ReliabilityTrace*>(context);
        if (fact.cycle == 128)
            return {scheduler::BoundaryAction::Stop, nullptr};
        if (fact.cycle == 64)
            return {scheduler::BoundaryAction::Tempo, state->changedTempo};
        return {};
    }
};
}

int main(int argc, char** argv) {
    int checks = 0;
    try {
        if (argc != 2 || std::filesystem::exists(argv[1]))
            throw std::runtime_error("New evidence output path required");
        std::filesystem::create_directories(argv[1]);
        std::ofstream trace(std::filesystem::path(argv[1]) / "cycle-trace.tsv");
        const auto check = [&](bool condition, std::string_view name) {
            ++checks;
            trace << name << '\t' << (condition ? "PASS" : "FAIL") << '\n';
            if (!condition)
                throw std::runtime_error(std::string(name));
        };
        const auto rejects = [&](Ratio ratio, std::string_view name) {
            bool rejected = false;
            try {
                (void)makeCycle(ratio);
            } catch (const std::invalid_argument&) {
                rejected = true;
            }
            check(rejected, name);
        };
        const auto verify = [&](Ratio ratio, int expectedTicks, std::string_view name) {
            const auto first = makeCycle(ratio);
            const auto second = makeCycle(ratio);
            check(first.ticks == expectedTicks, std::string(name) + " exact common cycle");
            check(first.events.size() == static_cast<std::size_t>(ratio.x + ratio.y),
                  std::string(name) + " exact event count");
            check(first.events == second.events, std::string(name) + " deterministic repeat");
            check(first.events.front().tick == 0 && first.events.back().tick < first.ticks,
                  std::string(name) + " half-open endpoints");
            for (std::size_t i = 0; i < first.events.size(); ++i) {
                const auto& event = first.events[i];
                check(event.layer == 0 || event.layer == 1, std::string(name) + " layer identity");
                check(event.index >= 0 && event.tick >= 0 && event.tick < first.ticks,
                      std::string(name) + " bounded event fields");
                if (i > 0) {
                    const auto& previous = first.events[i - 1];
                    check(previous.tick < event.tick ||
                              (previous.tick == event.tick &&
                               (previous.layer < event.layer ||
                                (previous.layer == event.layer && previous.index <= event.index))),
                          std::string(name) + " deterministic ordering");
                }
                trace << name << '\t' << event.layer << '\t' << event.index << '\t'
                      << event.tick << '\t' << event.position.numerator() << '/'
                      << event.position.denominator() << '\n';
            }
            int layerCounts[2]{};
            for (const auto& event : first.events) {
                ++layerCounts[event.layer];
                const auto expected = event.layer == 0 ? Rational{event.index, ratio.x}
                                                       : Rational{event.index, ratio.y};
                check(event.position == expected, std::string(name) + " exact Rational position");
                const auto divisor = event.layer == 0 ? ratio.x : ratio.y;
                check(event.tick == event.index * first.ticks / divisor,
                      std::string(name) + " exact shared tick");
            }
            check(layerCounts[0] == ratio.x && layerCounts[1] == ratio.y,
                  std::string(name) + " separate layer counts");
            return first;
        };

        verify({3, 2}, 6, "3:2");
        verify({4, 3}, 12, "4:3");
        verify({5, 7}, 35, "5:7");
        verify({1, 16}, 16, "1:16");
        check(commonCycleTicks({8, 12}) == 24, "8:12 gcd-reduced cycle");
        rejects({0, 3}, "zero layer refused");
        rejects({17, 3}, "layer above bound refused");
        rejects({3, 0}, "zero second layer refused");
        rejects({3, 17}, "second layer above bound refused");
        rejects({4, 4}, "equal layers refused");
        check(!makeCycle({1, 2}).events.empty(), "smallest distinct pair emits events");
        scheduler::Owner owner;
        owner.id[6] = 0x40;
        owner.id[8] = 0x80;
        owner.id[15] = 7;
        owner.generation = 1;
        owner.epoch = 1;
        const auto plan = compilePlan({3, 2}, owner, 7, "synthetic-polyrhythm-v1", 8000, 60,
                                       scheduler::BeatUnit::Quarter);
        const auto repeat = compilePlan({3, 2}, owner, 7, "synthetic-polyrhythm-v1", 8000, 60,
                                         scheduler::BeatUnit::Quarter);
        check(plan.valid() && plan.duration().n == 8000 && plan.duration().d == 1,
              "scheduler adapter valid normalized plan");
        check(plan.compatibleTempo(repeat), "scheduler adapter repeat is compatible");
        check(plan.events().size() == 5 && plan.introDuration().n == 0,
              "scheduler adapter exact events and no intro");
        int layerCounts[2]{};
        for (const auto& event : plan.events()) {
            check(event.action == scheduler::Action::Attack && event.structural < Rational{1},
                  "scheduler adapter half-open attack");
            check(event.role == scheduler::Role::LayerA || event.role == scheduler::Role::LayerB,
                  "scheduler adapter layer role");
            ++layerCounts[event.role == scheduler::Role::LayerA ? 0 : 1];
        }
        check(layerCounts[0] == 3 && layerCounts[1] == 2,
              "scheduler adapter separate layer counts");
        PlanBank bank({3, 2}, owner, 7, "synthetic-polyrhythm-v1", 8000,
                      scheduler::BeatUnit::Quarter);
        const auto* bank60 = bank.tempo(60);
        check(bank.initial().valid() && bank60 &&
                  bank.initial().compatibleTempo(*bank60),
              "tempo plan bank initial plan and compatible 60 BPM plan");
        check(bank.tempo(19) == nullptr && bank.tempo(301) == nullptr &&
                  bank.retainedEventCount() == 281u * 5u,
              "tempo plan bank bounded lookup and retained event count");
        bool bankExact = true;
        bool bankRoles = true;
        for (const int bpm : {20, 60, 120, 300}) {
            const auto* candidate = bank.tempo(bpm);
            scheduler::FrameRatio expected{};
            bankExact = bankExact && candidate &&
                        scheduler::samples(Rational{1}, 8000, static_cast<std::uint16_t>(bpm),
                                           scheduler::BeatUnit::Quarter, expected) &&
                        candidate->duration().n == expected.n &&
                        candidate->duration().d == expected.d &&
                        candidate->owner() == owner && candidate->binding() == 7 &&
                        candidate->sampleRate() == 8000 &&
                        candidate->sourceBinding() == "synthetic-polyrhythm-v1" &&
                        candidate->introDuration().n == 0;
            int counts[2]{};
            if (candidate) {
                for (const auto& event : candidate->events()) {
                    if (event.role == scheduler::Role::LayerA)
                        ++counts[0];
                    else if (event.role == scheduler::Role::LayerB)
                        ++counts[1];
                    else
                        bankRoles = false;
                    bankRoles = bankRoles && event.action == scheduler::Action::Attack;
                }
            }
            bankRoles = bankRoles && counts[0] == 3 && counts[1] == 2;
        }
        check(bankExact, "tempo plan bank exact durations and identities");
        check(bankRoles, "tempo plan bank preserves LayerA and LayerB attacks");
        LayerControls controls{35, 72, false, false, false, false};
        auto gains = resolveLayerGains(controls);
        check(gains.a == 35 && gains.b == 72, "layer controls retain both requested volumes");
        controls.soloA = true;
        gains = resolveLayerGains(controls);
        check(gains.a == 35 && gains.b == 0, "LayerA solo silences LayerB");
        controls.muteA = true;
        gains = resolveLayerGains(controls);
        check(gains.a == 0 && gains.b == 0, "mute takes precedence over solo");
        controls = {35, 72, false, false, true, true};
        gains = resolveLayerGains(controls);
        check(gains.a == 35 && gains.b == 72, "dual solo retains both layers");
        controls = {0, 0, false, false, false, false};
        check(resolveLayerGains(controls).a == 0 && resolveLayerGains(controls).b == 0,
              "zero volume is an audible silence result");
        bool invalidA = false;
        bool invalidB = false;
        try {
            auto invalid = controls;
            invalid.volumeA = -1;
            validateLayerControls(invalid);
        } catch (const std::invalid_argument&) {
            invalidA = true;
        }
        try {
            auto invalid = controls;
            invalid.volumeB = 101;
            validateLayerControls(invalid);
        } catch (const std::invalid_argument&) {
            invalidB = true;
        }
        check(invalidA && invalidB, "layer control volume bounds refuse invalid values");
        const auto mapped = resolveLayerGains({41, 63, false, false, false, false});
        bool roleMapping = true;
        for (const auto& event : bank60->events()) {
            roleMapping = roleMapping &&
                          ((event.role == scheduler::Role::LayerA && mapped.a == 41) ||
                           (event.role == scheduler::Role::LayerB && mapped.b == 63));
        }
        check(roleMapping, "resolved gains map only accepted LayerA and LayerB roles");
        CursorTrace renderFacts;
        scheduler::Cursor renderCursor;
        Renderer renderer;
        check(renderCursor.start(*bank60, owner, 7), "renderer source cursor starts accepted plan");
        check(renderCursor.process(8000, owner, CursorTrace::sink, &renderFacts),
              "renderer source cursor emits one complete plan cycle");
        check(renderFacts.facts.size() == 5, "renderer source trace has exact first-cycle facts");
        check(renderer.bind(*bank60, resolveLayerGains({100, 100, false, false, false, false})),
              "software renderer binds immutable plan and gains");
        std::size_t renderIndex = 0;
        bool rendered = true;
        bool layerANonzero = false;
        bool layerBNonzero = false;
        for (std::uint64_t frame = 0; frame < 8000; ++frame) {
            while (renderIndex < renderFacts.facts.size() &&
                   renderFacts.facts[renderIndex].frame == frame) {
                rendered = rendered && renderer.accept(renderFacts.facts[renderIndex++]);
            }
            LayerFrame output;
            rendered = rendered && renderer.sampleFrame(frame, output);
            layerANonzero = layerANonzero || std::abs(output.a) > 0.000001f;
            layerBNonzero = layerBNonzero || std::abs(output.b) > 0.000001f;
        }
        check(rendered && renderIndex == 5 && layerANonzero && layerBNonzero,
              "software renderer produces separate nonzero LayerA and LayerB lanes");
        check(renderCursor.process(1, owner, CursorTrace::sink, &renderFacts),
              "renderer source cursor emits shared-cycle boundary");
        bool boundaryAccepted = true;
        while (renderIndex < renderFacts.facts.size())
            boundaryAccepted = boundaryAccepted && renderer.accept(renderFacts.facts[renderIndex++]);
        LayerFrame nextCycle;
        check(boundaryAccepted && renderer.sampleFrame(8000, nextCycle) && !renderer.failed(),
              "software renderer accepts one shared-cycle boundary and next attack");
        check(renderFacts.facts.size() >= 7 &&
                  renderFacts.facts[5].kind == scheduler::FactKind::CycleCompleted &&
                  renderFacts.facts[5].sourceEvent == 0 &&
                  renderFacts.facts[5].role == scheduler::Role::Reference &&
                  renderFacts.facts[5].action == scheduler::Action::Attack,
              "scheduler emits canonical non-event identity at the cycle boundary");
        for (int field = 0; field < 3; ++field) {
            Renderer invalid;
            check(invalid.bind(*bank60, {100, 100}),
                  "malformed boundary fixture binds the same immutable plan");
            std::size_t index = 0;
            bool validPrefix = true;
            for (std::uint64_t frame = 0; frame < 8000; ++frame) {
                while (index < 5 && renderFacts.facts[index].frame == frame)
                    validPrefix = invalid.accept(renderFacts.facts[index++]) && validPrefix;
                LayerFrame output;
                validPrefix = invalid.sampleFrame(frame, output) && validPrefix;
            }
            check(validPrefix && index == 5 && !invalid.failed(),
                  "malformed boundary fixture consumes the valid first cycle");
            auto malformed = renderFacts.facts[5];
            if (field == 0)
                malformed.sourceEvent = 1;
            else if (field == 1)
                malformed.role = scheduler::Role::LayerA;
            else
                malformed.action = scheduler::Action::Release;
            check(!invalid.accept(malformed) && invalid.failed() && invalid.stopped() &&
                      !invalid.selectTempo(*bank.tempo(75)),
                  std::string("malformed cycle identity field ") + std::to_string(field) +
                      " faults before tempo handoff");
        }
        Renderer muted;
        check(muted.bind(*bank60, resolveLayerGains({100, 0, false, false, false, false})) &&
                  muted.accept(renderFacts.facts[0]) && muted.accept(renderFacts.facts[1]),
              "muted software renderer accepts both role facts");
        LayerFrame mutedFrame;
        check(muted.sampleFrame(0, mutedFrame) && muted.sampleFrame(1, mutedFrame) &&
                  mutedFrame.b == 0 && std::abs(mutedFrame.a) > 0.000001f,
              "resolved zero LayerB gain is silent while LayerA remains audible");
        Renderer duplicate;
        check(duplicate.bind(*bank60, {100, 100}) && duplicate.accept(renderFacts.facts[0]) &&
                  !duplicate.accept(renderFacts.facts[0]) && duplicate.failed(),
              "duplicate software fact latches renderer failure");
        Renderer omitted;
        LayerFrame omittedFrame;
        check(omitted.bind(*bank60, {100, 100}) && !omitted.sampleFrame(0, omittedFrame) &&
                  omitted.failed(),
              "software renderer requires facts before the due sample");
        Renderer stopped;
        check(stopped.bind(*bank60, {100, 100}), "stoppable software renderer binds");
        stopped.stop();
        check(!stopped.sampleFrame(0, omittedFrame) && !stopped.bind(*bank60, {100, 100}) &&
                  stopped.stopped(),
              "stopped renderer cannot resume or rebind");
        CursorTrace cursorTrace;
        scheduler::Cursor cursor;
        check(cursor.start(plan, owner, 7), "scheduler adapter cursor start");
        for (int i = 0; i < 32; ++i)
            check(cursor.process(256, owner, CursorTrace::sink, &cursorTrace),
                  "scheduler adapter cursor block");
        check(cursor.snapshot().completedCycles == 1, "scheduler adapter completes shared cycle");
        int traced[2]{};
        for (const auto& fact : cursorTrace.facts) {
            if (fact.kind == scheduler::FactKind::Event && fact.cycle == 0 &&
                (fact.role == scheduler::Role::LayerA || fact.role == scheduler::Role::LayerB))
                ++traced[fact.role == scheduler::Role::LayerA ? 0 : 1];
        }
        check(traced[0] == 3 && traced[1] == 2, "scheduler trace preserves both layers");

        const auto reliability = [&](Ratio ratio, std::string_view label) {
            constexpr std::uint32_t rate = 8000;
            constexpr std::uint32_t block = 256;
            constexpr std::uint64_t cycles = 128;
            constexpr std::uint64_t switchCycle = 64;
            const std::string source = "synthetic-polyrhythm-reliability-v1-" +
                                       std::string(label);
            PlanBank longBank(ratio, owner, 7, source, rate,
                              scheduler::BeatUnit::Quarter, 60);
            const auto* initial = longBank.tempo(60);
            const auto* changed = longBank.tempo(75);
            check(initial && changed && initial->compatibleTempo(*changed),
                  std::string(label) + " accepted tempo-bank plans");
            const auto writePlan = [&](const scheduler::Plan& selected, int bpm) {
                std::ofstream out(std::filesystem::path(argv[1]) /
                                  ("plan-" + std::string(label) + "-" +
                                   std::to_string(bpm) + ".tsv"));
                out << "source\t" << selected.sourceBinding() << "\nownerGeneration\t"
                    << selected.owner().generation << "\nownerEpoch\t"
                    << selected.owner().epoch << "\nbinding\t" << selected.binding()
                    << "\nsampleRate\t" << selected.sampleRate() << "\nbpm\t" << bpm
                    << "\nduration\t" << selected.duration().n << '/'
                    << selected.duration().d << "\n";
                for (const auto& event : selected.events())
                    out << event.structural.numerator() << '/'
                        << event.structural.denominator() << '\t' << event.offset.n
                        << '/' << event.offset.d << '\t' << event.sourceEvent << '\t'
                        << static_cast<int>(event.role) << '\t'
                        << static_cast<int>(event.action) << '\n';
                check(out.good(), std::string(label) + " plan manifest written");
            };
            writePlan(*initial, 60);
            writePlan(*changed, 75);

            scheduler::Cursor longCursor;
            Renderer longRenderer;
            ReliabilityTrace state;
            state.changedTempo = changed;
            state.facts.reserve(32);
            check(longCursor.start(*initial, owner, 7) &&
                      longRenderer.bind(*initial, {100, 100}),
                  std::string(label) + " shared cursor and renderer start");
            const scheduler::Plan* active = initial;
            scheduler::FramePosition anchor{};
            std::uint64_t completed = 0, priorFrame = 0, totalEvents = 0;
            std::size_t nextEvent = 0;
            std::array<std::uint64_t, 2> layerTotals{}, cycleLayers{};
            bool ordered = true, exact = true, rendered = true, clean = true;
            std::uint64_t callbacks = 0;
            while (longCursor.snapshot().state != scheduler::State::Terminal &&
                   callbacks < 10000) {
                const auto begin = longCursor.snapshot().processedThrough;
                state.facts.clear();
                const bool running = longCursor.process(
                    block, owner, ReliabilityTrace::sink, &state,
                    ReliabilityTrace::boundary, &state);
                ++callbacks;
                const auto end = longCursor.snapshot().processedThrough;
                std::size_t consumed = 0;
                const auto accept = [&](const scheduler::Fact& fact) {
                    ordered = ordered && fact.frame >= priorFrame &&
                              fact.cycle >= completed && fact.cycle <= completed + 1 &&
                              fact.owner == owner && fact.binding == 7;
                    priorFrame = fact.frame;
                    if (fact.kind == scheduler::FactKind::Event) {
                        if (nextEvent >= active->events().size()) {
                            exact = false;
                        } else {
                            const auto& expected = active->events()[nextEvent];
                            scheduler::FramePosition position;
                            std::uint64_t frame{};
                            exact = exact &&
                                    scheduler::add(anchor, expected.offset, position) &&
                                    scheduler::round(position, frame) && fact.frame == frame &&
                                    fact.cycle == completed &&
                                    fact.sourceEvent == expected.sourceEvent &&
                                    fact.role == expected.role &&
                                    fact.action == expected.action;
                            if (fact.role == scheduler::Role::LayerA)
                                ++cycleLayers[0], ++layerTotals[0];
                            else if (fact.role == scheduler::Role::LayerB)
                                ++cycleLayers[1], ++layerTotals[1];
                            else
                                exact = false;
                            ++nextEvent;
                            ++totalEvents;
                        }
                    } else if (fact.kind == scheduler::FactKind::CycleCompleted) {
                        scheduler::FramePosition boundary;
                        std::uint64_t frame{};
                        exact = exact && nextEvent == active->events().size() &&
                                cycleLayers[0] == static_cast<std::uint64_t>(ratio.x) &&
                                cycleLayers[1] == static_cast<std::uint64_t>(ratio.y) &&
                                scheduler::add(anchor, active->duration(), boundary) &&
                                scheduler::round(boundary, frame) && fact.frame == frame &&
                                fact.cycle == completed + 1 && fact.sourceEvent == 0 &&
                                fact.role == scheduler::Role::Reference &&
                                fact.action == scheduler::Action::Attack;
                        anchor = boundary;
                        ++completed;
                        nextEvent = 0;
                        cycleLayers = {};
                    } else {
                        exact = false;
                    }
                    rendered = rendered && longRenderer.accept(fact);
                    if (fact.kind == scheduler::FactKind::CycleCompleted &&
                        fact.cycle == switchCycle) {
                        rendered = rendered && longRenderer.selectTempo(*changed);
                        active = changed;
                    }
                    trace << "reliability-" << label << '\t'
                          << static_cast<int>(fact.kind) << '\t' << fact.frame << '\t'
                          << fact.cycle << '\t' << fact.sourceEvent << '\t'
                          << static_cast<int>(fact.role) << '\n';
                };
                for (std::uint64_t frame = begin; frame < end; ++frame) {
                    while (consumed < state.facts.size() &&
                           state.facts[consumed].frame == frame)
                        accept(state.facts[consumed++]);
                    LayerFrame output;
                    rendered = rendered && longRenderer.sampleFrame(frame, output);
                }
                while (consumed < state.facts.size()) {
                    exact = exact && state.facts[consumed].frame == end;
                    accept(state.facts[consumed++]);
                }
                clean = clean && (running ||
                        (longCursor.snapshot().state == scheduler::State::Terminal &&
                         longCursor.snapshot().reason == scheduler::StopReason::Requested));
            }
            const auto snapshot = longCursor.snapshot();
            scheduler::FramePosition expectedEnd{};
            std::uint64_t expectedFrames{};
            const bool expectedDuration =
                scheduler::addRepeated({}, initial->duration(), switchCycle, expectedEnd) &&
                scheduler::addRepeated(expectedEnd, changed->duration(),
                                       cycles - switchCycle, expectedEnd) &&
                scheduler::round(expectedEnd, expectedFrames);
            check(ordered, std::string(label) + " monotone frame/cycle and owner identity");
            check(exact && completed == cycles && nextEvent == 0,
                  std::string(label) + " every cycle has exact scheduled facts");
            check(totalEvents == cycles * static_cast<std::uint64_t>(ratio.x + ratio.y) &&
                      layerTotals[0] == cycles * static_cast<std::uint64_t>(ratio.x) &&
                      layerTotals[1] == cycles * static_cast<std::uint64_t>(ratio.y),
                  std::string(label) + " no duplicate or lost layer events");
            check(expectedDuration && snapshot.processedThrough == expectedFrames &&
                      snapshot.completedCycles == cycles,
                  std::string(label) + " exact rational duration and cycle count");
            check(clean && snapshot.state == scheduler::State::Terminal &&
                      snapshot.reason == scheduler::StopReason::Requested &&
                      callbacks < 10000 && rendered && !longRenderer.failed(),
                  std::string(label) + " requested boundary stop without renderer fault");
            longRenderer.stop();
            check(longRenderer.stopped() && longCursor.acknowledge(owner, 7) &&
                      longCursor.snapshot().state == scheduler::State::Idle,
                  std::string(label) + " clean renderer stop and cursor acknowledgment");
            trace << "summary-" << label << "\trate=" << rate << "\tframes="
                  << expectedFrames << "\tseconds=" << expectedFrames / rate << '+'
                  << expectedFrames % rate << '/' << rate << "\tcycles=" << completed
                  << "\tA=" << layerTotals[0] << "\tB=" << layerTotals[1]
                  << "\tcallbacks=" << callbacks << "\ttransition=" << switchCycle
                  << ":60->75\n";
        };
        reliability({5, 7}, "5-7");
        reliability({3, 2}, "3-2");
        trace.flush();
        check(trace.good(), "evidence trace flushed");
        std::cout << "PASS " << checks << " polyrhythm component checks; no audio/UI/store execution\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << ": " << error.what() << '\n';
        return 1;
    }
}
