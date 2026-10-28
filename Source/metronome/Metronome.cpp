#include "metronome/Metronome.hpp"
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace fathom::metronome {
namespace {
void need(bool yes,const char* message){if(!yes)throw std::invalid_argument(message);}
bool in(int n,int a,int b){return n>=a && n<=b;}
bool validRamp(const Ramp& r,int bpm){return in(r.step,1,20)&&in(r.every,1,32)&&in(r.target,20,300)&&(r.up?r.target>bpm:r.target<bpm);}
std::uint64_t medianTwice(std::uint64_t* values,std::size_t n) noexcept {
    std::sort(values,values+n);
    return n%2?2*values[n/2]:values[n/2-1]+values[n/2];
}
}
void validate(const Settings& s){
    need(in(s.tempo,20,300),"Select integer tempo from 20 to 300 BPM");
    need(in(static_cast<int>(s.unit),0,3),"Select eighth, quarter, dotted-quarter or half-note BPM unit");
    need(in(s.numerator,1,16)&&(s.denominator==2||s.denominator==4||s.denominator==8||s.denominator==16),"Select meter numerator 1–16 and denominator 2, 4, 8 or 16");
    need(in(s.subdivision,1,7),"Select 1–7 subdivisions per meter denominator beat");
    need(s.styles.size()==static_cast<std::size_t>(s.numerator),"Set one accent, normal or silent style per meter beat");
    for(auto style:s.styles)need(in(static_cast<int>(style),0,2),"Unsupported beat style");
    need(in(s.x,1,16)&&in(s.y,1,16)&&in(static_cast<int>(s.reference),0,2),"Select literal layer counts 1–16 and reference A, B or Cycle");
    need(in(static_cast<int>(s.countIn),0,2),"Select an explicit supported count-in");
    need(in(s.masterVolume,0,100),"Master volume requires integer 0–100 percent");
    for(int volume:s.volumes)need(in(volume,0,100),"Bus volume requires integer 0–100 percent");
    if(s.ramp)need(validRamp(*s.ramp,s.tempo),"Ramp needs step 1–20, every 1–32 bars, and target 20–300 in its direction");
}
Rational barSpan(const Settings& s){validate(s);return Rational{s.numerator*4,s.denominator};}
const std::array<std::pair<int,int>,8>& commonMeters() noexcept {
    static const std::array<std::pair<int,int>,8> meters{{{2,4},{3,4},{4,4},{5,4},{6,8},{7,8},{9,8},{12,8}}};return meters;
}
const char* beatUnitLabel(scheduler::BeatUnit u) noexcept {
    switch(u){case scheduler::BeatUnit::Eighth:return "eighth note";case scheduler::BeatUnit::Quarter:return "quarter note";case scheduler::BeatUnit::DottedQuarter:return "dotted quarter note";case scheduler::BeatUnit::Half:return "half note";}return "unsupported BPM unit";
}
std::vector<Cue> events(const Settings& s){
    validate(s);std::vector<Cue> out;out.reserve(static_cast<std::size_t>(s.numerator*s.subdivision));
    for(int beat=0;beat<s.numerator;++beat)for(int part=0;part<s.subdivision;++part){
        if(s.styles[static_cast<std::size_t>(beat)]==Style::Silent)continue;
        const auto id=static_cast<std::uint32_t>(beat*s.subdivision+part);
        out.push_back({Rational{4*(beat*s.subdivision+part),s.denominator*s.subdivision},id,
            part==0 && s.styles[static_cast<std::size_t>(beat)]==Style::Accent?Style::Accent:Style::Normal,beat,part});
    }
    return out;
}
PlanBank::PlanBank(const Settings& s,const scheduler::Owner& owner,std::uint64_t binding,std::string source,std::uint32_t rate){
    validate(s);need(!s.polyrhythmEnabled,"Use the Polyrhythmic Generator adapter for an enabled two-layer configuration");
    need(s.countIn!=CountIn::AuthoredBar,"An authored count-in requires the lesson's admitted source context; use configured bar or Off here");
    cues_=events(s);scheduler::PlanSpec spec;spec.owner=owner;spec.binding=binding;spec.sourceBinding=std::move(source);spec.sampleRate=rate;spec.bpm=static_cast<std::uint16_t>(s.tempo);spec.unit=s.unit;spec.cycle=barSpan(s);
    // Logical events remain available through mute/disable for phase and traces;
    // metronomeEnabled/gains gate the output bus in its renderer, never the clock.
    for(const auto& cue:cues_)spec.events.push_back({cue.at,cue.id,scheduler::Role::Metronome,scheduler::Action::Attack});
    for(int bpm=20;bpm<=300;++bpm){spec.bpm=static_cast<std::uint16_t>(bpm);tempos_[static_cast<std::size_t>(bpm-20)]=scheduler::compile(spec);}
    spec.bpm=static_cast<std::uint16_t>(s.tempo);
    if(s.countIn==CountIn::ConfiguredBar){
        spec.intro=spec.cycle;
        // One primary denominator click per count-in beat. Silent practice beats
        // do not erase the explicitly selected preparation bar. Master gain applies.
        for(int i=0;i<s.numerator;++i){Cue c{Rational{4*i,s.denominator},static_cast<std::uint32_t>(i),i==0?Style::Accent:Style::Normal,i,0};countIn_.push_back(c);spec.countIn.push_back({c.at,c.id,scheduler::Role::CountIn,scheduler::Action::Attack});}
    }
    initial_=scheduler::compile(spec);
}
const scheduler::Plan* PlanBank::tempo(int bpm) const noexcept {return in(bpm,20,300)?&tempos_[static_cast<std::size_t>(bpm-20)]:nullptr;}
std::size_t PlanBank::retainedEventCount() const noexcept {
    std::size_t n=initial_.events().size()+initial_.countIn().size();for(const auto& p:tempos_)n+=p.events().size()+p.countIn().size();return n;
}
TapResult Tap::add(std::uint64_t seq,std::uint64_t ns) noexcept {
    if(!seq||seq<=sequence_||(sequence_&&ns<=lastNs_))return {TapStatus::Rejected,0};
    if(sequence_&&ns-lastNs_>4000000000ULL)count_=0;
    sequence_=seq;lastNs_=ns;
    if(count_==points_.size()){std::move(points_.begin()+1,points_.end(),points_.begin());--count_;}points_[count_++]=ns;
    std::array<std::uint64_t,5> intervals{},inliers{};std::size_t count=0,accepted=0;
    for(std::size_t i=1;i<count_;++i){auto d=points_[i]-points_[i-1];if(d>=200000000ULL&&d<=3000000000ULL)intervals[count++]=d;}
    if(count<3)return {TapStatus::Insufficient,0};
    const auto med=medianTwice(intervals.data(),count);
    for(std::size_t i=0;i<count;++i){auto twice=intervals[i]*2;auto difference=twice>med?twice-med:med-twice;if(difference*5<=med)inliers[accepted++]=intervals[i];}
    if(accepted<3)return {TapStatus::Unstable,0};
    const auto d=medianTwice(inliers.data(),accepted);constexpr std::uint64_t n=120000000000ULL;
    const auto bpm=n/d+((n%d)*2>=d?1:0);return {TapStatus::Candidate,static_cast<int>(bpm)};
}
TempoPolicy::TempoPolicy(const scheduler::Owner& owner,std::uint64_t binding,const Settings& s):owner_(owner),binding_(binding){
    validate(s);need(owner.valid()&&binding,"Existing valid owner and binding required");state_.tempo=s.tempo;state_.ramp=s.ramp;
}
TempoPolicy::TempoPolicy(const scheduler::Owner& previous,const scheduler::Owner& resumed,std::uint64_t binding,TempoState handoff):owner_(resumed),binding_(binding),state_(std::move(handoff)){
    need(previous.valid()&&resumed.valid()&&previous.id==resumed.id&&resumed.generation>previous.generation&&resumed.epoch>=previous.epoch&&binding,"Resume must retain the original ID with a later accepted generation and nonregressing format epoch");
    need(in(state_.tempo,20,300)&&(!state_.ramp||validRamp(*state_.ramp,state_.tempo))&&in(state_.count,0,state_.ramp?state_.ramp->every:0)&&(!state_.pendingManual||in(*state_.pendingManual,20,300)),"Invalid retained tempo/ramp handoff");
    need(state_.resumable,"Only an accepted Pause handoff may resume this original");state_.resumable=false;
    need(!(state_.ramp&&state_.pendingManual),"Manual choice must already have disarmed ramp");
}
bool TempoPolicy::manual(const scheduler::Owner& o,std::uint64_t key,std::uint64_t command,int bpm,Phase phase) noexcept {
    if(halted_||!(o==owner_)||key!=binding_||!command||command<=state_.lastCommand||!in(bpm,20,300)||phase!=Phase::Running)return false;
    state_.lastCommand=command;state_.pendingManual=bpm;state_.ramp.reset();state_.count=0;return true;
}
Decision TempoPolicy::boundary(const scheduler::Owner& o,std::uint64_t key,std::uint64_t bar,bool confirmed,bool complete,Intent intent) noexcept {
    Decision out{false,false,state_.tempo,intent};
    if(halted_||!(o==owner_)||key!=binding_||!bar||static_cast<unsigned>(intent)>static_cast<unsigned>(Intent::Error))return out;
    if(state_.completedThrough==std::numeric_limits<std::uint64_t>::max()||bar!=state_.completedThrough+1)return out;
    // Only the next unique, fully accepted bar advances the retained high water.
    if(confirmed&&complete){state_.completedThrough=bar;if(state_.ramp)state_.count=std::min(state_.ramp->every,state_.count+1);}
    out.accepted=true;
    if(intent!=Intent::Continue){halted_=true;state_.resumable=intent==Intent::Pause;if(intent!=Intent::Pause){state_.ramp.reset();state_.count=0;}return out;}
    if(!confirmed||!complete)return out;
    if(state_.pendingManual){state_.tempo=*state_.pendingManual;state_.pendingManual.reset();}
    else if(state_.ramp&&state_.count>=state_.ramp->every){auto r=*state_.ramp;const int n=state_.tempo+(r.up?r.step:-r.step);state_.tempo=r.up?std::min(n,r.target):std::max(n,r.target);state_.count=0;if(state_.tempo==r.target)state_.ramp.reset();}
    out.nextAttack=true;out.tempo=state_.tempo;return out;
}
}
