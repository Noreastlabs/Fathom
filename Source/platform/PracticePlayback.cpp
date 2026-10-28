#include "platform/PracticePlayback.hpp"
#include "content/LessonAdmission.hpp"
#include "content/LessonPulse.hpp"
#include "content/LessonTempo.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace fathom::platform {
namespace {
scheduler::Plan combinedPlan(const reference::Program& program,const reference::Configuration& c,
                             const practice::Configuration& cfg,bool beatClick) {
    scheduler::PlanSpec s;s.owner=c.owner;s.binding=c.binding;s.sourceBinding=c.sourceBinding;
    s.sampleRate=c.rate;s.bpm=c.bpm;s.unit=c.unit;s.cycle=c.cycle;s.intro=c.intro;
    for(const auto& ev:program.schedule().events())s.events.push_back({ev.structural,ev.sourceEvent,ev.role,ev.action});
    if(beatClick){
        if(cfg.unit!=scheduler::BeatUnit::Quarter)throw std::invalid_argument("Lesson beat clicks require the admitted quarter-note tempo.");
        for(std::int64_t beat=0;Rational{beat}<cfg.span;++beat){
            if(s.events.size()>=scheduler::maxPlanEvents)throw std::invalid_argument("The selected span exceeds the bounded combined reference/click event capacity.");
            s.events.push_back({Rational{beat},static_cast<std::uint32_t>(beat+1),scheduler::Role::Metronome,scheduler::Action::Attack});
        }
    }
    if(c.intro.numerator()){
        const auto [n,d]=*cfg.meter;
        for(int i=0;i<n;++i)s.countIn.push_back({Rational{static_cast<std::int64_t>(i)*4,static_cast<std::int64_t>(d)},static_cast<std::uint32_t>(i+1),scheduler::Role::CountIn,scheduler::Action::Attack});
    }
    return scheduler::compile(s);
}
bool sameRamp(const std::optional<metronome::Ramp>& a,const std::optional<metronome::Ramp>& b) noexcept {
    return a.has_value()==b.has_value()&&(!a||(a->up==b->up&&a->step==b->step&&a->every==b->every&&a->target==b->target));
}
template<class Position> bool rounded(const Position& p,std::uint64_t& n) noexcept {return scheduler::round(p,n);}
}
struct PracticePlayback::Generation {
    struct Dynamic {
        explicit Dynamic(metronome::TempoPolicy p):policy(p),candidate(p){}
        std::array<reference::Program,281> programs;
        std::array<scheduler::Plan,281> plans;
        metronome::TempoPolicy policy,candidate;
        PracticeTempoEvidence packet;
        std::array<PracticeTempoPoint,32> draftPoints{};
        std::uint32_t draftCount{};
        scheduler::FramePosition anchor{},draftAnchor{};
        std::uint64_t baseCycles{};
        std::array<std::uint16_t,scheduler::maxCallbackEvents> blockTempos{};
        std::uint16_t renderBpm{};std::uint32_t proposedFrames{};
        bool pending{};
    };
    std::unique_ptr<Dynamic> dynamic;
    reference::Program program;
    scheduler::Plan plan;
    reference::Renderer renderer;
    scheduler::Cursor cursor;
    practice::Progress progress;
    std::array<scheduler::Fact,scheduler::maxCallbackEvents> blockFacts{};
    std::size_t count{};
    std::uint64_t target{}, intro{}, confirmedCycleEnd{}, clickStart{}, sequence{};
    bool clickActive{}, failed{};
    PracticePlayback* parent{};
};
PracticePlayback::PracticePlayback()=default;
PracticePlayback::~PracticePlayback()=default;
bool PracticePlayback::prepare(std::shared_ptr<const music::ValidatedModel> model,const reference::Configuration& c,
                               const practice::Configuration& cfg,std::uint64_t remaining) {
    if(!model || !model->source().syntheticFixture)throw std::invalid_argument("Raw curriculum models require separate trusted lesson admission; synthetic technical fixtures only at this entry.");
    return prepareChecked(std::move(model),c,cfg,remaining);
}
bool PracticePlayback::prepareLesson(const lesson::Admission& admission,const reference::Configuration& c,
                                     const practice::Coordinator& original,std::uint64_t remaining) {
    admission.validateOriginal(original);admission.validateReference(c);const auto& cfg=original.configuration();
    if(!(original.owner()==c.owner)||original.completedCycles()>=cfg.targetCycles
        ||remaining!=cfg.targetCycles-original.completedCycles())
        throw std::invalid_argument("Playback owner or remaining span differs from the retained original Attempt.");
    const auto context=json::parse(original.context());
    if(context.object().at("configuration").find("lesson_tempo"))throw std::invalid_argument("This original selected a dynamic tempo policy; use its complete-evidence provider.");
    return prepareChecked(admission.model(),c,cfg,remaining,lesson::pulseEnabled(context.object().at("configuration")));
}
bool PracticePlayback::prepareLessonTempo(const lesson::Admission& admission,const reference::Configuration& c,
                                          const practice::Coordinator& original,std::uint64_t remaining) {
    admission.validateOriginal(original);admission.validateReference(c);auto cfg=original.configuration();
    if(!(original.owner()==c.owner)||original.completedCycles()>=cfg.targetCycles||remaining!=cfg.targetCycles-original.completedCycles())
        throw std::invalid_argument("Dynamic playback must retain its original owner and remaining unique source spans.");
    const auto& map=original.timeline(original.owner());
    if(map.spec().initialBpm!=original.currentTempo()||c.bpm!=original.currentTempo())
        throw std::invalid_argument("Prepare the current generation at its retained tempo, without changing original selected tempo.");
    const auto context=json::parse(original.context());const auto& configuration=context.object().at("configuration");
    const auto ramp=lesson::tempoRamp(configuration,cfg.bpm);cfg.bpm=c.bpm;
    return prepareChecked(admission.model(),c,cfg,remaining,lesson::pulseEnabled(configuration),true,ramp,original.context());
}
bool PracticePlayback::prepareTempo(std::shared_ptr<const music::ValidatedModel> model,const reference::Configuration& c,
                                   const practice::Configuration& cfg,std::uint64_t remaining,std::optional<metronome::Ramp> ramp) {
    if(!model||!model->source().syntheticFixture)throw std::invalid_argument("Raw dynamic models require explicit synthetic technical provenance; actual lessons require admission.");
    return prepareChecked(std::move(model),c,cfg,remaining,false,true,ramp);
}
bool PracticePlayback::prepareChecked(std::shared_ptr<const music::ValidatedModel> model,const reference::Configuration& c,
                                      const practice::Configuration& cfg,std::uint64_t remaining,bool beatClick,
                                      bool dynamic,std::optional<metronome::Ramp> initialRamp,std::string pinnedContext) {
    const auto prior=std::find_if(preparedOwners_.begin(),preparedOwners_.end(),[&](const auto& o){return o.id==c.owner.id;});
    if(prior!=preparedOwners_.end() && (c.owner.generation<=prior->generation || c.owner.epoch<prior->epoch))
        throw std::invalid_argument("This original generation was already prepared or is stale; retain its outcome and use an explicit new generation.");
    const TempoHistory* previous=nullptr;
    for(const auto& h:tempoHistory_)if(h.owner.id==c.owner.id&&(!previous||h.owner.generation>previous->owner.generation))previous=&h;
    if(!dynamic&&previous)throw std::invalid_argument("An original dynamic generation cannot resume through the fixed evidence API.");
    if(dynamic&&prior!=preparedOwners_.end()&&!previous)throw std::invalid_argument("A fixed original cannot switch to dynamic mode during resume.");
    if(dynamic&&(cfg.targetCycles>32||remaining>32))throw std::invalid_argument("Dynamic lesson tempo supports the selected1–32 whole source spans.");
    const auto intro=practice::countInSpan(cfg);
    if(previous&&(!previous->reclaimed||!previous->retained.progress.terminal||previous->retained.progress.fault
        ||previous->retained.progress.state!=practice::State::Paused||previous->sourceBinding!=c.sourceBinding
        ||previous->binding!=c.binding||previous->method!=c.method||previous->model!=model||!(previous->spec.intro==intro)
        ||previous->beatClick!=beatClick||previous->configuration.countIn!=cfg.countIn||previous->configuration.meter!=cfg.meter
        ||previous->configuration.sourceRequiresCountIn!=cfg.sourceRequiresCountIn||previous->configuration.faithfulWholeSpan!=cfg.faithfulWholeSpan
        ||previous->configuration.targetCycles!=cfg.targetCycles||!sameRamp(previous->initialRamp,initialRamp)||previous->pinnedContext!=pinnedContext
        ||previous->spec.rate!=c.rate||!(previous->spec.span==cfg.span)||previous->spec.unit!=cfg.unit
        ||previous->retained.tempo.tempo!=c.bpm||previous->spec.cycles-previous->retained.progress.completedCycles!=remaining))
        throw std::invalid_argument("Resume needs this provider's exact reclaimed Paused source generation, current tempo and remaining target.");
    if(c.owner.epoch<=invalidatedThrough_.load(std::memory_order_acquire))throw std::invalid_argument("This output epoch was invalidated; stop and explicitly reconfigure before preparing music.");
    if(!(c.intro==intro) || !(c.cycle==cfg.span) || c.rate!=cfg.rate || c.bpm!=cfg.bpm || c.unit!=cfg.unit
        || !remaining || remaining>cfg.targetCycles)throw std::invalid_argument("Practice and reference configurations must describe the same clock/span/count-in.");
    for(auto& slot:slots_)if(slot.state.load(std::memory_order_acquire)==Free) {
        auto g=std::make_unique<Generation>();g->parent=this;g->target=remaining;
        g->program=reference::compile(model,c);g->plan=combinedPlan(g->program,c,cfg,beatClick);
        if(!scheduler::round(g->plan.introDuration(),g->intro) || !g->renderer.bind(g->program))throw std::invalid_argument("Could not bind immutable practice generation.");
        g->progress.owner=c.owner;g->progress.state=intro.numerator()?practice::State::CountIn:practice::State::Running;
        auto owners=preparedOwners_;const auto index=static_cast<std::size_t>(std::distance(preparedOwners_.begin(),prior));
        if(prior==preparedOwners_.end())owners.push_back(c.owner);else owners[index]=c.owner;
        auto history=tempoHistory_;PracticeTempoPreparation stats{};
        if(dynamic){
            auto policy=previous?metronome::TempoPolicy(previous->owner,c.owner,c.binding,previous->retained.tempo)
                :metronome::TempoPolicy(c.owner,c.binding,lesson::tempoSettings(c.bpm,initialRamp));
            g->dynamic=std::make_unique<Generation::Dynamic>(policy);auto& d=*g->dynamic;
            d.baseCycles=previous?previous->retained.tempo.completedThrough:0;d.renderBpm=c.bpm;
            if(!scheduler::position(g->plan.introDuration(),d.anchor))throw std::invalid_argument("Initial tempo position cannot be represented.");
            d.draftAnchor=d.anchor;d.packet.progress=g->progress;d.packet.binding=c.binding;
            d.packet.points[0]={0,c.bpm};d.packet.pointCount=1;d.packet.tempo=d.policy.handoff();
            stats={1,1,g->program.voices().size(),g->plan.events().size()+g->program.schedule().events().size(),sizeof(Generation)+sizeof(Generation::Dynamic)};
            for(int bpm=20;bpm<=300;++bpm){auto variant=c;variant.bpm=static_cast<std::uint16_t>(bpm);variant.intro=Rational{};
                const auto at=static_cast<std::size_t>(bpm-20);d.programs[at]=reference::compile(model,variant);d.plans[at]=combinedPlan(d.programs[at],variant,cfg,beatClick);
                if(!g->program.compatibleTempo(d.programs[at])||!g->plan.compatibleTempo(d.plans[at]))throw std::invalid_argument("Tempo bank changed the original musical structure or source binding.");
                ++stats.programs;++stats.plans;stats.voices+=d.programs[at].voices().size();stats.events+=d.plans[at].events().size()+d.programs[at].schedule().events().size();
            }
            history.push_back({c.owner,c.binding,c.sourceBinding,{c.owner,cfg.span,intro,c.rate,c.bpm,c.unit,remaining},c.method,model,cfg,beatClick,initialRamp,std::move(pinnedContext),d.packet,false});
        }
        preparedOwners_.swap(owners);tempoHistory_.swap(history);if(dynamic)preparation_=stats;
        slot.value=std::move(g);slot.state.store(Ready,std::memory_order_release);return true;
    }
    return false;
}
bool PracticePlayback::nextProgress(practice::Progress& p){return progress_.pop(p);}
bool PracticePlayback::nextFact(scheduler::Fact& f){return facts_.pop(f);}
bool PracticePlayback::reclaim(practice::Progress& p) {
    for(auto& s:slots_)if(s.state.load(std::memory_order_acquire)==Retired&&!s.value->dynamic){p=s.value->progress;s.value.reset();s.state.store(Free,std::memory_order_release);return true;}return false;
}
bool PracticePlayback::nextTempoEvidence(PracticeTempoEvidence& p) noexcept {return tempoProgress_.pop(p);}
bool PracticePlayback::reclaimTempoEvidence(PracticeTempoEvidence& p) {
    for(auto& s:slots_)if(s.state.load(std::memory_order_acquire)==Retired&&s.value->dynamic){
        p=s.value->dynamic->packet;
        const auto h=std::find_if(tempoHistory_.begin(),tempoHistory_.end(),[&](const auto& x){return x.owner==p.progress.owner&&x.binding==p.binding;});
        if(h==tempoHistory_.end())throw std::logic_error("Original dynamic generation history is unavailable; retain its slot.");
        h->retained=p;h->reclaimed=true;s.value.reset();s.state.store(Free,std::memory_order_release);return true;
    }
    return false;
}
bool PracticePlayback::manualTempo(const scheduler::Owner& o,std::uint64_t binding,std::uint64_t seq,int bpm) noexcept {
    if(!o.valid()||!binding||!seq||bpm<20||bpm>300)return false;
    const auto h=std::find_if(tempoHistory_.begin(),tempoHistory_.end(),[&](const auto& x){return x.owner==o&&x.binding==binding;});
    if(h==tempoHistory_.end())return false; // fixed mode never upgrades in place
    return tempoCommands_.push({o,binding,seq,static_cast<std::uint64_t>(bpm),1});
}
bool PracticePlayback::nextTempoReply(PracticeTempoReply& r) noexcept {
    if(!tempoReplies_.pop(r))return false;replyCapacity_.fetch_add(1,std::memory_order_release);return true;
}
bool PracticePlayback::applyTempoEvidence(const PracticeTempoEvidence& e,practice::Coordinator& c) const {
    const auto h=std::find_if(tempoHistory_.begin(),tempoHistory_.end(),[&](const auto& x){return x.owner==e.progress.owner&&x.binding==e.binding;});
    if(h==tempoHistory_.end()||!e.pointCount||e.pointCount>e.points.size()||e.points[0].cycle||e.points[0].bpm!=h->spec.initialBpm)
        throw std::invalid_argument("Tempo packet has no matching original generation/binding or complete initial map.");
    practice::Timeline map(h->spec);
    for(std::size_t i=1;i<e.pointCount;++i)map=map.changed(e.points[i].cycle,e.points[i].bpm);
    if(map.acceptedTempo(e.progress.clientAcceptedThrough)!=e.tempo.tempo)
        throw std::invalid_argument("Reported current tempo disagrees with the packet's accepted output map.");
    return c.progress(e.progress,map);
}
bool PracticePlayback::collect(void* context,const scheduler::Fact& f) noexcept {
    auto& g=*static_cast<Generation*>(context);
    if(g.count==g.blockFacts.size() || !g.parent->facts_.push(f))return false;
    g.blockFacts[g.count++]=f;return true;
}
scheduler::BoundaryDecision PracticePlayback::boundary(void* context,const scheduler::Fact& f) noexcept {
    auto& g=*static_cast<Generation*>(context);
    if(f.cycle>=g.target)return {scheduler::BoundaryAction::Stop,nullptr};
    if(!g.dynamic)return {};
    auto& d=*g.dynamic;const auto old=d.candidate.handoff().tempo;
    if(f.cycle>UINT64_MAX-d.baseCycles||!scheduler::add(d.draftAnchor,d.plans[static_cast<std::size_t>(old-20)].duration(),d.draftAnchor)){g.failed=true;return {scheduler::BoundaryAction::Stop,nullptr};}
    const auto decision=d.candidate.boundary(f.owner,f.binding,d.baseCycles+f.cycle,true,true,metronome::Intent::Continue);
    if(!decision.accepted||!decision.nextAttack){g.failed=true;return {scheduler::BoundaryAction::Stop,nullptr};}
    d.blockTempos[g.count-1]=static_cast<std::uint16_t>(decision.tempo);
    if(decision.tempo==old)return {};
    if(d.draftCount==d.draftPoints.size()){g.failed=true;return {scheduler::BoundaryAction::Stop,nullptr};}
    d.draftPoints[d.draftCount++]={f.cycle,static_cast<std::uint16_t>(decision.tempo)};
    return {scheduler::BoundaryAction::Tempo,&d.plans[static_cast<std::size_t>(decision.tempo-20)]};
}
scheduler::BlockOutcome PracticePlayback::render(void* context,const output::Owner& owner,std::uint32_t rate,std::uint32_t frames,Buses& buses) noexcept {
    if(!context)return {};auto& self=*static_cast<PracticePlayback*>(context);auto* g=self.active_;
    if(!g || g->failed || (g->dynamic&&g->dynamic->pending) || !(g->plan.owner()==owner) || rate!=g->plan.sampleRate() || !frames || frames>output::maxOutputFrames)return {};
    const auto begin=g->cursor.snapshot().processedThrough;g->count=0;
    if(g->dynamic){auto& d=*g->dynamic;d.candidate=d.policy;d.draftAnchor=d.anchor;d.draftPoints=d.packet.points;d.draftCount=d.packet.pointCount;d.blockTempos.fill(0);}
    const bool ok=g->cursor.process(frames,owner,collect,g,boundary,g);
    const auto snapshot=g->cursor.snapshot();const bool terminal=snapshot.state==scheduler::State::Terminal;
    const bool normal=terminal && snapshot.reason==scheduler::StopReason::Requested;
    const auto prefix=ok?frames:normal?static_cast<std::uint32_t>(snapshot.processedThrough-begin):0U;
    g->progress.scheduledThrough=snapshot.processedThrough;
    if(g->failed || (!ok&&!normal) || prefix>frames){g->failed=true;return {};}
    std::size_t event=0;
    auto accept=[&](const scheduler::Fact& f,std::size_t index) {
        if(f.kind==scheduler::FactKind::Event && (f.role==scheduler::Role::CountIn||f.role==scheduler::Role::Metronome)){g->clickStart=f.frame;g->clickActive=true;return true;}
        if(!g->renderer.accept(f))return false;
        if(g->dynamic&&f.kind==scheduler::FactKind::CycleCompleted){auto& d=*g->dynamic;const auto bpm=d.blockTempos[index];
            if(bpm&&bpm!=d.renderBpm){if(!g->renderer.selectTempo(d.programs[static_cast<std::size_t>(bpm-20)]))return false;d.renderBpm=bpm;}}
        return true;
    };
    for(std::uint32_t i=0;i<prefix;++i){const auto frame=begin+i;
        while(event<g->count && g->blockFacts[event].frame<=frame){const auto index=event++;if(!accept(g->blockFacts[index],index)){g->failed=true;return {};}}
        float mono{};if(!g->renderer.sampleFrame(frame,mono)){g->failed=true;return {};}
        buses[0][0][i]=buses[0][1][i]=mono;
        if(g->clickActive && frame>=g->clickStart){const auto age=frame-g->clickStart;const auto length=std::max(1U,rate/40);
            if(age<length){const auto click=static_cast<float>(reference::sample(reference::Method::Sine,1000,age,length,rate));buses[1][0][i]=buses[1][1][i]=click;}else g->clickActive=false;}
    }
    while(event<g->count){const auto index=event++;const auto& f=g->blockFacts[index];if(f.frame!=begin+prefix || !accept(f,index)){g->failed=true;return {};}}
    if(g->dynamic){g->dynamic->pending=true;g->dynamic->proposedFrames=prefix;}
    return {true,prefix,terminal};
}
void PracticePlayback::update(const output::Snapshot& s) noexcept {
    if(active_->dynamic){updateTempo(s);return;}
    auto& g=*active_;auto& p=g.progress;
    if(!(s.owner==p.owner))return;
    // Post-validation successful client submission is software confirmation only.
    // Scheduled facts may precede it; rejected/zeroed blocks earn no credit.
    if(s.submittedFrames<p.clientAcceptedThrough || s.submittedFrames>p.scheduledThrough){g.failed=true;}
    else p.clientAcceptedThrough=s.submittedFrames;
    p.activeFrames=p.clientAcceptedThrough>g.intro?p.clientAcceptedThrough-g.intro:0;
    std::uint64_t count=p.completedCycles;
    while(count<g.target) {
        scheduler::FrameRatio offset,end;std::uint64_t frame{};
        if(!scheduler::multiply(g.plan.duration(),count+1,offset) || !scheduler::add(g.plan.introDuration(),offset,end) || !scheduler::round(end,frame)){g.failed=true;break;}
        if(frame>p.clientAcceptedThrough)break;
        ++count;g.confirmedCycleEnd=frame;
    }
    p.completedCycles=count;
    p.cursorFrames=p.clientAcceptedThrough>g.intro?p.clientAcceptedThrough-(g.confirmedCycleEnd?g.confirmedCycleEnd:g.intro):0;
    p.partial=p.cursorFrames!=0;
    p.requestedStopNs=s.requestedStopNs;p.uncertainThrough=std::max(s.uncertainThrough,s.submittedFrames);
    p.hasPhysicalConfirmation=s.hasConfirmation;p.physicalConfirmedThrough=s.confirmedFrames;
    const bool stopped=s.state!=output::State::Running;
    p.fault=g.failed || s.state==output::State::Fault;
    p.state=p.fault?practice::State::Error:stopped?(s.state==output::State::Paused?practice::State::Paused:practice::State::Ended)
        :(p.clientAcceptedThrough<g.intro?practice::State::CountIn:practice::State::Running);
    p.terminal=stopped || g.failed;
    if(g.sequence==UINT64_MAX){g.failed=true;p.fault=true;p.state=practice::State::Error;p.terminal=true;}
    else p.sequence=++g.sequence;
    if(!progress_.push(p)){g.failed=true;p.fault=true;p.state=practice::State::Error;p.terminal=true;}
    if(p.terminal){g.cursor.stop(p.owner,g.plan.binding());g.renderer.stop();const auto slot=activeSlot_;active_=nullptr;slots_[slot].state.store(Retired,std::memory_order_release);}
}
void PracticePlayback::updateTempo(const output::Snapshot& s) noexcept {
    auto& g=*active_;auto& d=*g.dynamic;auto& p=g.progress;
    if(!(s.owner==p.owner))return;d.packet.reportedSubmittedThrough=s.submittedFrames;
    if(d.pending){
        if(s.submittedFrames!=p.scheduledThrough)g.failed=true;
        else if(d.proposedFrames){d.policy=d.candidate;d.anchor=d.draftAnchor;d.packet.points=d.draftPoints;d.packet.pointCount=d.draftCount;p.clientAcceptedThrough=s.submittedFrames;}
        d.pending=false;
    }else if(s.submittedFrames!=p.clientAcceptedThrough)g.failed=true;
    p.activeFrames=p.clientAcceptedThrough>g.intro?p.clientAcceptedThrough-g.intro:0;
    const auto accepted=d.policy.handoff();std::uint64_t start{},end{};scheduler::FramePosition next;
    const auto at=static_cast<std::size_t>(accepted.tempo-20);
    if(accepted.completedThrough<d.baseCycles||!rounded(d.anchor,start)||!scheduler::add(d.anchor,d.plans[at].duration(),next)||!rounded(next,end))g.failed=true;
    p.completedCycles=accepted.completedThrough>=d.baseCycles?accepted.completedThrough-d.baseCycles:0;
    const bool endpoint=p.clientAcceptedThrough>=g.intro&&p.clientAcceptedThrough==end;
    if(endpoint)++p.completedCycles;
    if(p.completedCycles>g.target)g.failed=true;
    p.cursorFrames=p.clientAcceptedThrough>start?p.clientAcceptedThrough-start:0;if(endpoint)p.cursorFrames=0;
    p.partial=p.cursorFrames!=0;p.requestedStopNs=s.requestedStopNs;
    p.uncertainThrough=std::max({s.uncertainThrough,s.submittedFrames,p.scheduledThrough});
    p.hasPhysicalConfirmation=s.hasConfirmation;p.physicalConfirmedThrough=s.confirmedFrames;
    p.fault=g.failed||s.state==output::State::Fault;p.terminal=p.fault||s.state!=output::State::Running;
    p.state=p.fault?practice::State::Error:p.terminal?(s.state==output::State::Paused?practice::State::Paused:practice::State::Ended)
        :(p.clientAcceptedThrough<g.intro?practice::State::CountIn:practice::State::Running);
    if(p.terminal){
        const auto intent=p.fault?metronome::Intent::Error:p.state==practice::State::Paused?metronome::Intent::Pause:metronome::Intent::Stop;
        if(accepted.completedThrough==UINT64_MAX||!d.policy.boundary(p.owner,g.plan.binding(),accepted.completedThrough+1,endpoint,endpoint,intent).accepted)g.failed=true;
    }
    if(g.sequence==UINT64_MAX)g.failed=true;else p.sequence=++g.sequence;
    if(g.failed){p.fault=true;p.terminal=true;p.state=practice::State::Error;}
    d.packet.progress=p;d.packet.tempo=d.policy.handoff();
    if(!tempoProgress_.push(d.packet)){g.failed=true;p.fault=true;p.terminal=true;p.state=practice::State::Error;
        if(!d.policy.halted()){const auto state=d.policy.handoff();(void)d.policy.boundary(p.owner,g.plan.binding(),state.completedThrough+1,endpoint,endpoint,metronome::Intent::Error);}
        d.packet.progress=p;d.packet.tempo=d.policy.handoff();}
    if(p.terminal){g.cursor.stop(p.owner,g.plan.binding());g.renderer.stop();g.clickActive=false;active_=nullptr;slots_[activeSlot_].state.store(Retired,std::memory_order_release);}
}
void PracticePlayback::observe(void* context,const output::Snapshot& s) noexcept {
    if(!context)return;auto& self=*static_cast<PracticePlayback*>(context);
    if(s.state==output::State::Fault || s.state==output::State::Unresolved) {
        const auto epoch=s.request.epoch;
        if(s.state==output::State::Fault && epoch>self.invalidatedThrough_.load(std::memory_order_relaxed))self.invalidatedThrough_.store(epoch,std::memory_order_release);
        // A prepared generation that never acquired output still has a retained
        // zero-credit cancellation/fault. Its immutable slot is retired by callback.
        for(auto& slot:self.slots_)if(slot.state.load(std::memory_order_acquire)==Ready && slot.value->plan.owner().epoch==epoch) {
            int expected=Ready;if(!slot.state.compare_exchange_strong(expected,Active,std::memory_order_acq_rel))continue;
            auto& g=*slot.value;g.failed=s.state==output::State::Fault;g.progress.sequence=1;g.progress.fault=g.failed;
            g.progress.state=g.failed?practice::State::Error:practice::State::Ended;g.progress.terminal=true;g.progress.requestedStopNs=s.requestedStopNs;
            if(g.dynamic){auto& d=*g.dynamic;const auto h=d.policy.handoff();
                (void)d.policy.boundary(g.progress.owner,g.plan.binding(),h.completedThrough+1,false,false,g.failed?metronome::Intent::Error:metronome::Intent::Stop);
                d.packet.progress=g.progress;d.packet.tempo=d.policy.handoff();self.tempoProgress_.push(d.packet);
            }else self.progress_.push(g.progress);
            slot.state.store(Retired,std::memory_order_release);
        }
    }
    if(!self.active_ && s.state==output::State::Running && s.request.epoch>self.invalidatedThrough_.load(std::memory_order_acquire))for(std::size_t i=0;i<self.slots_.size();++i){auto& slot=self.slots_[i];
        if(slot.state.load(std::memory_order_acquire)!=Ready || !(slot.value->plan.owner()==s.owner))continue;
        int expected=Ready;if(!slot.state.compare_exchange_strong(expected,Active,std::memory_order_acq_rel))continue;
        self.active_=slot.value.get();self.activeSlot_=i;
        if(!self.active_->cursor.start(self.active_->plan,s.owner,self.active_->plan.binding()))self.active_->failed=true;
        break;
    }
    if(self.active_){
        if(self.active_->dynamic&&s.state==output::State::Fault&&s.request.epoch>=self.active_->progress.owner.epoch&&!(s.owner==self.active_->progress.owner)){
            auto original=s;const auto& p=self.active_->progress;original.owner=p.owner;original.submittedFrames=p.clientAcceptedThrough;
            original.uncertainThrough=std::max(p.uncertainThrough,p.scheduledThrough);original.hasConfirmation=p.hasPhysicalConfirmation;original.confirmedFrames=p.physicalConfirmedThrough;self.update(original);
        }else self.update(s);
    }
    scheduler::Command command;
    for(std::size_t count=0;count<64&&self.replyCapacity_.load(std::memory_order_acquire)>0&&self.tempoCommands_.pop(command);++count){
        self.replyCapacity_.fetch_sub(1,std::memory_order_acquire);auto* g=self.active_;
        const bool accepted=g&&g->dynamic&&s.state==output::State::Running&&g->dynamic->policy.manual(command.owner,command.binding,command.sequence,static_cast<int>(command.value),g->progress.state==practice::State::Running?metronome::Phase::Running:metronome::Phase::CountIn);
        if(!self.tempoReplies_.push({command.owner,command.binding,command.sequence,static_cast<int>(command.value),accepted})&&g)g->failed=true;
    }
}
}
