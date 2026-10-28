#include "core/PracticeTransport.hpp"
#include <algorithm>
#include <limits>
#include <stdexcept>
namespace fathom::practice {
namespace {
void validateProgress(const Progress& p,const Progress& before,const Timeline& map) {
    if(p.fault!=(p.state==State::Error))throw std::invalid_argument("Fault and state disagree; retain the original evidence.");
    if(p.state==State::Stopped || (p.state!=State::CountIn && p.state!=State::Running && p.state!=State::Paused && p.state!=State::Ended && p.state!=State::Error)
        || p.terminal!=(p.state==State::Paused || p.state==State::Ended || p.state==State::Error))
        throw std::invalid_argument("Callback progress cannot confirm persistence or fabricate a terminal state.");
    if(p.clientAcceptedThrough<p.activeFrames || p.scheduledThrough<p.clientAcceptedThrough || p.completedCycles>map.spec().cycles
        || p.clientAcceptedThrough<before.clientAcceptedThrough || p.activeFrames<before.activeFrames || p.completedCycles<before.completedCycles)
        throw std::invalid_argument("Conflicting authoritative transport progress; retain original evidence.");
    const auto introFrame=map.frame(0),lo=map.completed(p.clientAcceptedThrough),anchor=map.frame(lo);
    const auto active=p.clientAcceptedThrough>introFrame?p.clientAcceptedThrough-introFrame:0;
    const auto cursor=p.clientAcceptedThrough>anchor?p.clientAcceptedThrough-anchor:0;
    if(p.activeFrames!=active || p.completedCycles!=lo || p.cursorFrames!=cursor || p.partial!=(cursor!=0)
        || (p.state==State::CountIn && p.clientAcceptedThrough>=introFrame) || (p.state==State::Running && p.clientAcceptedThrough<introFrame))
        throw std::invalid_argument("Progress contradicts the pinned count-in/cycle/sample timeline.");
}
}
Rational countInSpan(const Configuration& c) {
    if(!c.faithfulWholeSpan || c.span.numerator()==0)throw std::invalid_argument("Select a validated whole span with faithful entry and exit; unsupported cutpoints cannot play.");
    if(!c.targetCycles || c.targetCycles>1000000)throw std::invalid_argument("Choose a finite target from 1 to 1000000 scheduled cycles.");
    scheduler::FrameRatio frames;
    if(!scheduler::samples(c.span,c.rate,c.bpm,c.unit,frames))throw std::invalid_argument("Choose a supported rate, tempo and explicit beat unit.");
    if(c.countIn==CountIn::Off) {
        if(c.sourceRequiresCountIn)throw std::invalid_argument("This source requires count-in; choose its authored bar.");
        return Rational{};
    }
    if(c.countIn!=CountIn::AuthoredBar || !c.meter)throw std::invalid_argument("No defined authored meter: explicitly choose Off or a supported authored bar.");
    const auto [n,d]=*c.meter;
    if(n<1 || n>32 || (d!=2 && d!=4 && d!=8 && d!=16))throw std::invalid_argument("Unsupported authored meter; preserve the source and select a supported configuration.");
    return Rational{static_cast<std::int64_t>(n)*4,static_cast<std::int64_t>(d)};
}
void Coordinator::begin(scheduler::Owner owner,Kind kind,std::string context,Configuration config) {
    if(pending())throw std::logic_error("Resolve and confirm the original outcome before a new attempt or context.");
    if(!owner.valid() || context.empty() || (kind!=Kind::Attempt && kind!=Kind::Freeplay))throw std::invalid_argument("An allocated original identity and pinned context are required.");
    const auto intro=countInSpan(config);
    if(owner_.valid() && owner.id==owner_.id)throw std::invalid_argument("A completed original identity cannot be allocated again.");
    for(const auto& prior:retained_)if(prior.owner.id==owner.id)throw std::invalid_argument("Previously allocated original identity cannot be reused.");
    Timeline initial({owner,config.span,intro,config.rate,config.bpm,config.unit,config.targetCycles});
    // Prepare all allocating copies before replacing the current original. A
    // refused allocation cannot leave progress and its map in different owners.
    auto retained=retained_;retained.insert(retained.end(),generations_.begin(),generations_.end());
    auto maps=retainedTimelines_;maps.insert(maps.end(),timelines_.begin(),timelines_.end());
    const auto state=intro.numerator()?State::CountIn:State::Running;
    Progress p;p.owner=owner;p.state=state;
    std::vector<Progress> generations{p};std::vector<Timeline> timelines;timelines.push_back(std::move(initial));
    owner_=owner;kind_=kind;context_=std::move(context);config_=config;lastCommand_=0;key_.clear();payload_.clear();
    retained_.swap(retained);retainedTimelines_.swap(maps);generations_.swap(generations);timelines_.swap(timelines);state_=state;
}
bool Coordinator::command(std::uint64_t seq,const scheduler::Owner& owner) {
    if(!pending() || !(owner==owner_) || !seq || seq<=lastCommand_)return false;
    lastCommand_=seq;return true;
}
scheduler::Owner Coordinator::nextResumeOwner() const {
    if(state_!=State::Paused || sealed())throw std::logic_error("Retain the stopped traversal before explicit Resume.");
    if(owner_.generation==std::numeric_limits<std::uint64_t>::max())throw std::overflow_error("Transport generation exhausted; finish the original outcome.");
    if(completedCycles()>=config_.targetCycles)throw std::logic_error("Scheduled target already reached; finish this outcome.");
    auto next=owner_;++next.generation;return next;
}
scheduler::Owner Coordinator::resume() {
    const auto next=nextResumeOwner();
    Timeline map({next,config_.span,countInSpan(config_),config_.rate,currentTempo(),config_.unit,config_.targetCycles-completedCycles()});
    Progress p;p.owner=next;p.state=countInSpan(config_).numerator()?State::CountIn:State::Running;
    timelines_.reserve(timelines_.size()+1);generations_.reserve(generations_.size()+1);
    timelines_.push_back(std::move(map));generations_.push_back(p);owner_=next;lastCommand_=0;state_=p.state;return owner_;
}
const Timeline& Coordinator::timeline(const scheduler::Owner& owner) const {
    const auto i=std::find_if(timelines_.begin(),timelines_.end(),[&](const auto& t){return t.spec().owner==owner;});
    if(i!=timelines_.end())return *i;
    const auto old=std::find_if(retainedTimelines_.begin(),retainedTimelines_.end(),[&](const auto& t){return t.spec().owner==owner;});
    if(old==retainedTimelines_.end())throw std::invalid_argument("No accepted tempo timeline for this original generation.");return *old;
}
const Timeline* Coordinator::lateTimeline(const Progress& p) const noexcept {
    const auto found=std::find_if(mappedLate_.begin(),mappedLate_.end(),[&](const auto& x){return x.fact.owner==p.owner && x.fact.sequence==p.sequence && x.fact.dispositionSequence==p.dispositionSequence;});
    return found==mappedLate_.end()?nullptr:&found->map;
}
void Coordinator::retainLate(const Progress& p,const Progress& acceptedBase,const Timeline* supplied) {
    if(!supplied){late_.push_back(p);return;}
    const Timeline* base=&timeline(p.owner);const Progress* before=&acceptedBase;
    // Legacy raw notifications did not validate a tempo map. Only accepted
    // progress or a previously validated full late map can establish its prefix.
    for(const auto& prior:mappedLate_)if(prior.fact.owner==p.owner && prior.fact.sequence>before->sequence){before=&prior.fact;base=&prior.map;}
    if(!supplied->extends(*base,before->clientAcceptedThrough,p.clientAcceptedThrough))
        throw std::invalid_argument("Late tempo evidence changed its original binding, validated prefix or unsubmitted boundary.");
    validateProgress(p,*before,*supplied);
    MappedLate staged{p,*supplied};mappedLate_.reserve(mappedLate_.size()+1);late_.reserve(late_.size()+1);
    mappedLate_.push_back(std::move(staged));late_.push_back(p);
}
std::uint16_t Coordinator::currentTempo() const {
    if(generations_.empty())return config_.bpm;
    const auto& p=generations_.back();return timeline(p.owner).acceptedTempo(p.clientAcceptedThrough);
}

bool Coordinator::stoppedAcknowledged(const scheduler::Owner& actual,State state,std::uint64_t requestedNs) {
    if(!pending() || sealed() || actual.id!=owner_.id || actual.epoch!=owner_.epoch || (state!=State::Ended && state!=State::Error))return false;
    auto i=std::find_if(generations_.begin(),generations_.end(),[&](const auto& x){return x.owner==actual;});
    if(i==generations_.end())return false;
    if(!(actual==owner_) && (generations_.back().sequence || generations_.back().clientAcceptedThrough))return false;
    if(state_==State::Error && state==State::Ended)return false;
    if(state_==state)return true;
    // Pause's interrupted snapshot remains immutable. This separate original
    // disposition adds no frames/cycles and records actual adapter cancellation.
    auto marker=*i;marker.state=state;marker.terminal=true;marker.fault=state==State::Error;marker.requestedStopNs=requestedNs;
    if(dispositionSequence_==UINT64_MAX)throw std::overflow_error("Disposition sequence exhausted; preserve original outcome.");
    marker.dispositionSequence=++dispositionSequence_;late_.push_back(marker);state_=state;return true;
}
bool Coordinator::progress(const Progress& p) { return progressChecked(p,nullptr); }
bool Coordinator::progress(const Progress& p,const Timeline& accepted) { return progressChecked(p,&accepted); }
bool Coordinator::progressChecked(const Progress& p,const Timeline* accepted) {
    if(p.dispositionSequence)throw std::invalid_argument("Callback progress cannot impersonate a control disposition.");
    auto i=std::find_if(generations_.begin(),generations_.end(),[&](const auto& x){return x.owner==p.owner;});
    if(i==generations_.end()) {
        const auto old=std::find_if(retained_.begin(),retained_.end(),[&](const auto& x){return x.owner==p.owner;});
        if(old==retained_.end() || !p.sequence || p.sequence<=old->sequence)return false;
        for(const auto& late:late_)if(!late.dispositionSequence && late.owner==p.owner && p.sequence<=late.sequence)return false;
        retainLate(p,*old,accepted);return false; // original owner outbox, never new-context credit
    }
    if(!p.sequence || p.sequence<=i->sequence)return false;
    for(const auto& old:late_)if(!old.dispositionSequence && old.owner==p.owner && p.sequence<=old.sequence)return false;
    if(sealed() || state_==State::Ended || state_==State::Error || !(p.owner==owner_) || i->terminal){retainLate(p,*i,accepted);return false;}
    const auto index=static_cast<std::size_t>(std::distance(generations_.begin(),i));
    auto map=accepted?*accepted:timelines_.at(index);
    if(!map.extends(timelines_.at(index),i->clientAcceptedThrough,p.clientAcceptedThrough))
        throw std::invalid_argument("Tempo evidence changed an accepted prefix, original binding or unsubmitted boundary.");
    validateProgress(p,*i,map);
    timelines_[index]=std::move(map);*i=p;state_=p.state;return true;
}
std::uint64_t Coordinator::activeFrames() const {std::uint64_t n=0;for(const auto& p:generations_){if(n>UINT64_MAX-p.activeFrames)throw std::overflow_error("Practice duration overflow");n+=p.activeFrames;}return n;}
std::uint64_t Coordinator::completedCycles() const {std::uint64_t n=0;for(const auto& p:generations_){if(n>UINT64_MAX-p.completedCycles)throw std::overflow_error("Cycle count overflow");n+=p.completedCycles;}return n;}
std::string Coordinator::originalKey() const {
    constexpr char hex[]="0123456789abcdef";std::string key;
    for(std::size_t i=0;i<owner_.id.size();++i){if(i==4 || i==6 || i==8 || i==10)key+='-';key+=hex[owner_.id[i]>>4];key+=hex[owner_.id[i]&15];}return key;
}
void Coordinator::seal(std::string key,std::string payload) {
    if(state_!=State::Ended && state_!=State::Error)throw std::logic_error("Stop or finish before finalizing actual facts.");
    if(key!=originalKey() || payload.empty())throw std::invalid_argument("Original finalization key and immutable bytes are required.");
    if(sealed() && (key!=key_ || payload!=payload_))throw std::logic_error("Conflicting sealed payload; original is preserved.");
    key_=std::move(key);payload_=std::move(payload);
}
bool Coordinator::reconcile(const std::string& key,const std::string& payload,Save result) {
    if(!sealed() || key!=key_)return false;
    if(payload!=payload_ || result==Save::Conflict){state_=State::Error;return false;}
    if(result==Save::Matching){state_=State::Stopped;return true;}
    if(result!=Save::Unknown && result!=Save::Absent)throw std::invalid_argument("Unknown persistence reply");
    return false;
}
const char* stateText(State s) noexcept {switch(s){case State::Stopped:return "Stopped";case State::CountIn:return "Count-in";case State::Running:return "Running";case State::Paused:return "Paused";case State::Ended:return "Ended — outcome pending";case State::Error:return "Error — original outcome retained";}return "Unknown";}
}
