#include "platform/MetronomePlayback.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace fathom::platform {
namespace {
void need(bool b,const char* m){if(!b)throw std::invalid_argument(m);}
constexpr double pi=3.14159265358979323846;
template<class Position> std::uint64_t rounded(Position v) noexcept {std::uint64_t n{};return scheduler::round(v,n)?n:UINT64_MAX;}
}
struct MetronomePlayback::Generation {
    Generation(const metronome::Settings& s,const scheduler::Owner& o,std::uint64_t key,std::string source,std::uint32_t rate)
        :settings(s),policy(o,key,s),candidate(policy){
        if (s.polyrhythmEnabled) {
            if (s.countIn != metronome::CountIn::Off || s.ramp)
                throw std::invalid_argument("Polyrhythm playback currently requires count-in Off and no tempo ramp");
            polyBank=std::make_unique<polyrhythm::PlanBank>(polyrhythm::Ratio{s.x,s.y},o,key,std::move(source),rate,s.unit,static_cast<std::uint16_t>(s.tempo));
        } else {
            bank=std::make_unique<metronome::PlanBank>(s,o,key,std::move(source),rate);
        }
    }
    const scheduler::Plan& initialPlan() const noexcept { return bank?bank->initial():polyBank->initial(); }
    const scheduler::Plan* tempoPlan(int bpm) const noexcept { return bank?bank->tempo(bpm):polyBank->tempo(bpm); }
    bool polyrhythm() const noexcept { return static_cast<bool>(polyBank); }
    metronome::Settings settings;
    std::unique_ptr<metronome::PlanBank> bank;
    std::unique_ptr<polyrhythm::PlanBank> polyBank;
    polyrhythm::Renderer polyRenderer;
    metronome::TempoPolicy policy,candidate;
    scheduler::Cursor cursor;
    MetronomeProgress progress;
    scheduler::FramePosition anchor{},draftAnchor{};
    std::uint64_t baseCycles{},baseActive{},intro{},scheduled{},sequence{},layerSequence{};
    struct Tagged {scheduler::Fact fact;int tempo{};};
    std::array<Tagged,scheduler::maxCallbackEvents> block{};std::size_t count{};
    std::array<MetronomeSegment,128> blockSegments{};std::size_t segmentCount{},unpublishedSegment{};
    std::array<std::uint32_t,281> lengths{};
    std::uint64_t clickStart{};std::uint32_t clickLength{};double frequency{},amplitude{};
    int renderedTempo{};
    bool clickActive{},failed{},pending{};
    MetronomePlayback* parent{};
};
MetronomePlayback::MetronomePlayback()=default;
MetronomePlayback::~MetronomePlayback()=default;
bool MetronomePlayback::prepare(const metronome::Settings& s,const scheduler::Owner& o,std::uint64_t binding,std::string key,std::uint32_t rate){
    need(std::none_of(history_.begin(),history_.end(),[&](const auto& h){return h.owner.id==o.id;}),"Original already prepared; resolve its retained outcome before a new original, or explicitly resume its paused generation");
    return install(s,o,binding,std::move(key),rate,nullptr);
}
bool MetronomePlayback::prepareResume(const scheduler::Owner& previous,const scheduler::Owner& next){
    const auto it=std::find_if(history_.begin(),history_.end(),[&](const auto& h){return h.owner==previous;});
    need(it!=history_.end() && it->reclaimed && it->retained.terminal && !it->retained.fault && it->retained.phase==metronome::Phase::Paused,"Resume requires this provider's exact retained paused generation");
    auto s=it->settings;s.tempo=it->retained.tempo.tempo;s.ramp=it->retained.tempo.ramp;
    return install(s,next,it->retained.binding,it->key,it->rate,&*it);
}
bool MetronomePlayback::install(const metronome::Settings& s,const scheduler::Owner& o,std::uint64_t binding,std::string key,std::uint32_t rate,const History* previous){
    need(o.epoch>invalidatedThrough_.load(std::memory_order_acquire),"Invalidated output epoch; explicitly stop, reconfigure and acknowledge");
    for(auto& slot:slots_)if(slot.state.load(std::memory_order_acquire)==Free){
        auto g=std::make_unique<Generation>(s,o,binding,key,rate);g->parent=this;
        if(previous){g->policy=metronome::TempoPolicy(previous->owner,o,binding,previous->retained.tempo);g->candidate=g->policy;g->baseCycles=previous->retained.completedCycles;g->baseActive=previous->retained.totalActiveFrames;}
        g->intro=rounded(g->initialPlan().introDuration());need(scheduler::position(g->initialPlan().introDuration(),g->anchor),"Initial sample position invalid");g->draftAnchor=g->anchor;
        need(g->intro!=UINT64_MAX,"Count-in frame overflow");
        for(int bpm=20;bpm<=300;++bpm){scheduler::FrameRatio interval;need(scheduler::samples(Rational{4,s.denominator*s.subdivision},rate,static_cast<std::uint16_t>(bpm),s.unit,interval),"Click interval overflow");
            const auto length=std::min<std::uint64_t>(rate/40,interval.n/interval.d);need(length>=3,"Selected click span has fewer than three output samples");g->lengths[static_cast<std::size_t>(bpm-20)]=static_cast<std::uint32_t>(length);}
        auto& p=g->progress;p.owner=o;p.binding=binding;p.tempo=g->policy.handoff();p.completedCycles=g->baseCycles;p.totalActiveFrames=g->baseActive;p.phase=g->intro?metronome::Phase::CountIn:metronome::Phase::Running;
        History h{o,s,std::move(key),rate,p,false};
        if(previous){const auto index=static_cast<std::size_t>(previous-history_.data());history_[index]=std::move(h);}else history_.push_back(std::move(h));
        slot.value=std::move(g);slot.state.store(Ready,std::memory_order_release);return true;
    }
    return false;
}
bool MetronomePlayback::manual(const scheduler::Owner& o,std::uint64_t binding,std::uint64_t sequence,int bpm) noexcept {
    if(!o.valid()||!binding||!sequence||bpm<20||bpm>300)return false;
    return commands_.push({o,binding,sequence,static_cast<std::uint64_t>(bpm),1});
}
bool MetronomePlayback::layerGains(const scheduler::Owner& o,std::uint64_t binding,std::uint64_t sequence,polyrhythm::LayerGains gains) noexcept {
    if(!o.valid()||!binding||!sequence||gains.a<0||gains.a>100||gains.b<0||gains.b>100)return false;
    return layerCommands_.push({o,binding,sequence,gains});
}
bool MetronomePlayback::nextProgress(MetronomeProgress& p) noexcept{return progress_.pop(p);}
bool MetronomePlayback::nextFact(scheduler::Fact& f) noexcept{return facts_.pop(f);}
bool MetronomePlayback::nextSegment(MetronomeSegment& s) noexcept{
    if(segments_.pop(s))return true;
    for(auto& slot:slots_)if(slot.state.load(std::memory_order_acquire)==Retired){auto& g=*slot.value;
        if(g.unpublishedSegment<g.segmentCount){s=g.blockSegments[g.unpublishedSegment++];return true;}}
    return false;
}
bool MetronomePlayback::nextReply(MetronomeReply& r) noexcept{if(!replies_.pop(r))return false;replyCapacity_.fetch_add(1,std::memory_order_release);return true;}
bool MetronomePlayback::nextLayerReply(PolyrhythmLayerReply& r) noexcept{if(!layerReplies_.pop(r))return false;layerReplyCapacity_.fetch_add(1,std::memory_order_release);return true;}
bool MetronomePlayback::reclaim(MetronomeProgress& p){
    for(auto& slot:slots_)if(slot.state.load(std::memory_order_acquire)==Retired){
        if(slot.value->unpublishedSegment<slot.value->segmentCount)continue;
        p=slot.value->progress;
        const auto it=std::find_if(history_.begin(),history_.end(),[&](const auto& h){return h.owner==p.owner;});
        if(it!=history_.end()){it->retained=p;it->reclaimed=true;}
        slot.value.reset();slot.state.store(Free,std::memory_order_release);return true;}
    return false;
}
bool MetronomePlayback::collect(void* context,const scheduler::Fact& f) noexcept {
    auto& g=*static_cast<Generation*>(context);
    if(g.count==g.block.size() || !g.parent->facts_.push(f))return false;
    g.block[g.count++]={f,g.candidate.handoff().tempo};return true;
}
scheduler::BoundaryDecision MetronomePlayback::boundary(void* context,const scheduler::Fact& f) noexcept {
    auto& g=*static_cast<Generation*>(context);const auto old=g.candidate.handoff().tempo;
    const auto* oldPlan=g.tempoPlan(old);
    if(!oldPlan || f.cycle>UINT64_MAX-g.baseCycles || !scheduler::add(g.draftAnchor,oldPlan->duration(),g.draftAnchor)){g.failed=true;return {scheduler::BoundaryAction::Stop,nullptr};}
    // This is a schedule proposal. The policy is committed only after the output
    // adapter accepts this whole client prefix; rejected PCM earns no ramp credit.
    const auto d=g.candidate.boundary(f.owner,f.binding,g.baseCycles+f.cycle,true,true,metronome::Intent::Continue);
    if(!d.accepted || !d.nextAttack){g.failed=true;return {scheduler::BoundaryAction::Stop,nullptr};}
    g.block[g.count-1].tempo=d.tempo;
    return d.tempo==old?scheduler::BoundaryDecision{}:scheduler::BoundaryDecision{scheduler::BoundaryAction::Tempo,g.tempoPlan(d.tempo)};
}
scheduler::BlockOutcome MetronomePlayback::render(void* context,const output::Owner& owner,std::uint32_t rate,std::uint32_t frames,Buses& buses) noexcept {
    if(!context)return {};auto& self=*static_cast<MetronomePlayback*>(context);auto* g=self.active_;
    if(!g || g->failed || g->pending || !(g->progress.owner==owner) || rate!=g->initialPlan().sampleRate() || !frames || frames>output::maxOutputFrames)return {};
    g->candidate=g->policy;g->draftAnchor=g->anchor;g->count=0;g->segmentCount=0;g->unpublishedSegment=0;
    const auto begin=g->cursor.snapshot().processedThrough;
    // Commands are drained by observe before this callback's render. Output's
    // urgent transport commands therefore beat tempo without another clock.
    if(!g->cursor.process(frames,owner,collect,g,boundary,g)||g->failed){g->failed=true;g->scheduled=g->cursor.snapshot().processedThrough;return {};}
    g->scheduled=g->cursor.snapshot().processedThrough;
    auto segmentFrom=begin;int segmentTempo=g->policy.handoff().tempo;bool segmentIntro=begin<g->intro;
    auto segment=[&](std::uint64_t through) noexcept {
        if(through==segmentFrom)return true;
        if(g->segmentCount==g->blockSegments.size())return false;
        g->blockSegments[g->segmentCount++]={owner,g->progress.binding,segmentFrom,through,segmentTempo,segmentIntro};g->unpublishedSegment=g->segmentCount;segmentFrom=through;return true;
    };
    std::size_t event{};
    for(std::uint32_t i=0;i<frames;++i){const auto frame=begin+i;
        while(event<g->count && g->block[event].fact.frame==frame){const auto tagged=g->block[event++];const auto& f=tagged.fact;
            if(f.kind==scheduler::FactKind::CountInEnded){if(!segment(frame)){g->failed=true;return {};}segmentIntro=false;}
            if(f.kind==scheduler::FactKind::CycleCompleted){if(!segment(frame)){g->failed=true;return {};}
                segmentTempo=tagged.tempo;
            }
            if(g->polyrhythm()){
                if(!g->polyRenderer.accept(f)){g->failed=true;return {};}
                if(f.kind==scheduler::FactKind::CycleCompleted && tagged.tempo!=g->renderedTempo){
                    const auto* next=g->tempoPlan(tagged.tempo);
                    if(!next || !g->polyRenderer.selectTempo(*next)){g->failed=true;return {};}
                    g->renderedTempo=tagged.tempo;
                }
                continue;
            }
            if(f.kind==scheduler::FactKind::Event){
                const auto& cues=f.role==scheduler::Role::CountIn?g->bank->countInCues():g->bank->cues();
                const auto cue=std::find_if(cues.begin(),cues.end(),[&](const auto& c){return c.id==f.sourceEvent;});
                if(cue==cues.end() || (f.role!=scheduler::Role::CountIn && f.role!=scheduler::Role::Metronome)){g->failed=true;return {};}
                g->frequency=cue->part?600:cue->style==metronome::Style::Accent?1200:800;
                g->amplitude=cue->part?0.35:cue->style==metronome::Style::Accent?0.8:0.55;
                g->clickStart=frame;g->clickLength=g->lengths[static_cast<std::size_t>(tagged.tempo-20)];g->clickActive=true;
            }
        }
        if(g->polyrhythm()){
            polyrhythm::LayerFrame output;
            if(!g->polyRenderer.sampleFrame(frame,output)){g->failed=true;return {};}
            const auto a=g->settings.metronomeEnabled?output.a:0.0f;
            const auto b=g->settings.metronomeEnabled?output.b:0.0f;
            buses[1][0][i]=buses[1][1][i]=0.0f;
            buses[2][0][i]=buses[2][1][i]=a;
            buses[3][0][i]=buses[3][1][i]=b;
            continue;
        }
        float mono{};
        if(g->clickActive){const auto age=frame-g->clickStart;
            if(age>=g->clickLength)g->clickActive=false;
            else if(age && age+1<g->clickLength){const auto envelope=std::sin(pi*static_cast<double>(age)/(g->clickLength-1));mono=static_cast<float>(g->amplitude*envelope*envelope*std::sin(2*pi*g->frequency*static_cast<double>(age)/rate));}}
        buses[1][0][i]=buses[1][1][i]=g->settings.metronomeEnabled?mono:0;
    }
    if(event!=g->count || !segment(begin+frames)){g->failed=true;return {};}
    g->pending=true;return {true,frames,false};
}
void MetronomePlayback::update(const output::Snapshot& s) noexcept {
    auto& g=*active_;auto& p=g.progress;if(!(s.owner==p.owner))return;
    if(g.pending){
        if(s.submittedFrames!=g.scheduled){g.failed=true;g.unpublishedSegment=g.segmentCount;}
        else {g.policy=g.candidate;g.anchor=g.draftAnchor;p.clientAcceptedThrough=s.submittedFrames;
            g.unpublishedSegment=g.segmentCount;
            for(std::size_t i=0;i<g.segmentCount;++i)if(!segments_.push(g.blockSegments[i])){g.unpublishedSegment=i;g.failed=true;break;}}
        g.pending=false;
    }else if(s.submittedFrames!=p.clientAcceptedThrough)g.failed=true;
    p.scheduledThrough=g.scheduled;p.activeFrames=p.clientAcceptedThrough>g.intro?p.clientAcceptedThrough-g.intro:0;
    if(p.activeFrames>UINT64_MAX-g.baseActive)g.failed=true;else p.totalActiveFrames=g.baseActive+p.activeFrames;
    p.tempo=g.policy.handoff();p.completedCycles=p.tempo.completedThrough;
    scheduler::FramePosition end;const auto* plan=g.tempoPlan(p.tempo.tempo);
    if(!plan || !scheduler::add(g.anchor,plan->duration(),end))g.failed=true;
    const auto start=rounded(g.anchor),endFrame=rounded(end);
    p.barFrames=endFrame>=start?endFrame-start:0;p.cursorFrames=p.clientAcceptedThrough>start?p.clientAcceptedThrough-start:0;
    const bool endpoint=p.clientAcceptedThrough>=g.intro && p.clientAcceptedThrough==endFrame;
    if(endpoint){if(p.completedCycles==UINT64_MAX)g.failed=true;else ++p.completedCycles;p.cursorFrames=0;}
    p.partial=p.cursorFrames!=0;p.requestedStopNs=s.requestedStopNs;p.uncertainThrough=std::max(s.uncertainThrough,s.submittedFrames);
    p.hasPhysicalConfirmation=s.hasConfirmation;p.physicalConfirmedThrough=s.confirmedFrames;
    p.fault=g.failed || s.state==output::State::Fault;p.terminal=p.fault || s.state!=output::State::Running;
    p.phase=p.terminal?(s.state==output::State::Paused&&!p.fault?metronome::Phase::Paused:metronome::Phase::Terminal):(p.clientAcceptedThrough<g.intro?metronome::Phase::CountIn:metronome::Phase::Running);
    if(p.terminal){const auto h=g.policy.handoff();if(h.completedThrough==UINT64_MAX)g.failed=true;
        else {const auto intent=p.fault?metronome::Intent::Error:p.phase==metronome::Phase::Paused?metronome::Intent::Pause:metronome::Intent::Stop;
            if(!g.policy.boundary(p.owner,p.binding,h.completedThrough+1,endpoint,endpoint,intent).accepted)g.failed=true;}
        p.tempo=g.policy.handoff();g.cursor.stop(p.owner,p.binding);g.clickActive=false;if(g.polyrhythm())g.polyRenderer.stop();}
    if(g.sequence==UINT64_MAX)g.failed=true;else p.sequence=++g.sequence;
    p.fault|=g.failed;
    if(!progress_.push(p)){g.failed=true;p.fault=true;p.terminal=true;p.phase=metronome::Phase::Terminal;}
    if(p.terminal){active_=nullptr;slots_[activeSlot_].state.store(Retired,std::memory_order_release);}
}
void MetronomePlayback::observe(void* context,const output::Snapshot& s) noexcept {
    if(!context)return;auto& self=*static_cast<MetronomePlayback*>(context);
    if(s.state==output::State::Fault){const auto epoch=s.request.epoch;if(epoch>self.invalidatedThrough_.load(std::memory_order_relaxed))self.invalidatedThrough_.store(epoch,std::memory_order_release);}
    if(!self.active_ && s.state==output::State::Running && s.owner.epoch>self.invalidatedThrough_.load(std::memory_order_acquire))for(std::size_t i=0;i<self.slots_.size();++i){auto& slot=self.slots_[i];
        if(slot.state.load(std::memory_order_acquire)!=Ready || !(slot.value->progress.owner==s.owner))continue;
        int expected=Ready;if(!slot.state.compare_exchange_strong(expected,Active,std::memory_order_acq_rel))continue;
        self.active_=slot.value.get();self.activeSlot_=i;
        if (self.active_->polyrhythm()) {
            self.active_->renderedTempo=self.active_->settings.tempo;
            if(!self.active_->polyRenderer.bind(self.active_->initialPlan(), polyrhythm::resolveLayerGains({self.active_->settings.volumes[2], self.active_->settings.volumes[3], self.active_->settings.mute[0], self.active_->settings.mute[1], self.active_->settings.solo[0], self.active_->settings.solo[1]})))
                self.active_->failed=true;
        }
        if(!self.active_->cursor.start(self.active_->initialPlan(),s.owner,self.active_->progress.binding))self.active_->failed=true;break;}
    if(self.active_){
        if(s.state==output::State::Fault && s.request.epoch>=self.active_->progress.owner.epoch && !(s.owner==self.active_->progress.owner)){
            // A device epoch invalidates the original even if delayed lifecycle
            // context names another owner. Never adopt that owner's frame counts.
            auto retained=s;const auto& p=self.active_->progress;
            retained.owner=p.owner;retained.submittedFrames=p.clientAcceptedThrough;
            retained.uncertainThrough=std::max(p.uncertainThrough,self.active_->scheduled);
            retained.hasConfirmation=p.hasPhysicalConfirmation;retained.confirmedFrames=p.physicalConfirmedThrough;
            self.update(retained);
        }else self.update(s);
    }
    scheduler::Command command;for(std::size_t drained=0;drained<64 && self.replyCapacity_.load(std::memory_order_acquire)>0 && self.commands_.pop(command);++drained){
        self.replyCapacity_.fetch_sub(1,std::memory_order_acquire);
        auto* g=self.active_;const bool accepted=g && s.state==output::State::Running && g->policy.manual(command.owner,command.binding,command.sequence,static_cast<int>(command.value),g->progress.phase);
        if(!self.replies_.push({command.owner,command.binding,command.sequence,static_cast<int>(command.value),accepted}) && g)g->failed=true;
    }
    LayerCommand layer;for(std::size_t drained=0;drained<64 && self.layerReplyCapacity_.load(std::memory_order_acquire)>0 && self.layerCommands_.pop(layer);++drained){
        self.layerReplyCapacity_.fetch_sub(1,std::memory_order_acquire);
        auto* g=self.active_;const bool accepted=g && s.state==output::State::Running && g->polyrhythm() &&
            g->progress.owner==layer.owner && g->progress.binding==layer.binding && layer.sequence>g->layerSequence &&
            g->polyRenderer.setGains(layer.gains);
        if(accepted)g->layerSequence=layer.sequence;
        if(!self.layerReplies_.push({layer.owner,layer.binding,layer.sequence,layer.gains,accepted}) && g)g->failed=true;
    }
    if(s.state==output::State::Fault || s.state==output::State::Unresolved)for(auto& slot:self.slots_){
        if(slot.state.load(std::memory_order_acquire)!=Ready || slot.value->progress.owner.epoch!=s.request.epoch)continue;
        int expected=Ready;if(!slot.state.compare_exchange_strong(expected,Active,std::memory_order_acq_rel))continue;
        auto& p=slot.value->progress;p.terminal=true;p.phase=metronome::Phase::Terminal;p.fault=s.state==output::State::Fault;p.requestedStopNs=s.requestedStopNs;p.sequence=1;
        self.progress_.push(p);slot.state.store(Retired,std::memory_order_release);}
}
}
