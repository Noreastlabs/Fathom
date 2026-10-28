#include "core/PracticeTimeline.hpp"
#include <algorithm>
#include <stdexcept>

namespace fathom::practice {
namespace {
void require(bool value, const char* why) { if(!value)throw std::invalid_argument(why); }
bool same(const TimelineSpec& a,const TimelineSpec& b) {
    return a.owner==b.owner && a.span==b.span && a.intro==b.intro && a.rate==b.rate
        && a.initialBpm==b.initialBpm && a.unit==b.unit && a.cycles==b.cycles;
}
}
Timeline::Timeline(TimelineSpec spec):spec_(spec) {
    require(spec.owner.valid() && spec.cycles && spec.cycles<=1000000 && spec.span.numerator(),
            "Tempo timeline needs an original generation and finite faithful span.");
    scheduler::FrameRatio intro,cycle;
    require(scheduler::samples(spec.intro,spec.rate,spec.initialBpm,spec.unit,intro)
            && scheduler::samples(spec.span,spec.rate,spec.initialBpm,spec.unit,cycle)
            && cycle.n>=cycle.d,"Unsupported tempo timeline rate, beat unit or sub-sample span.");
    scheduler::FramePosition initial;
    require(scheduler::position(intro,initial),"Invalid initial sample coordinate.");
    points_.push_back({0,spec.initialBpm,initial});
    frame(spec.cycles); // reject arithmetic overflow before publishing a map
}
scheduler::FramePosition Timeline::coordinate(std::uint64_t cycle,const Rational& offset) const {
    require(cycle<=spec_.cycles && !(spec_.span<offset) && (cycle<spec_.cycles || !offset.numerator()),
            "Tempo coordinate is outside the declared selected span/target.");
    const auto it=std::upper_bound(points_.begin(),points_.end(),cycle,[](auto n,const auto& p){return n<p.cycle;});
    const auto& point=*std::prev(it);
    scheduler::FrameRatio duration,part; scheduler::FramePosition result;
    require(scheduler::samples(spec_.span,spec_.rate,point.bpm,spec_.unit,duration)
            && scheduler::addRepeated(point.anchor,duration,cycle-point.cycle,result)
            && scheduler::samples(offset,spec_.rate,point.bpm,spec_.unit,part)
            && scheduler::add(result,part,result),"Tempo coordinate exceeds checked rational sample arithmetic; retain original evidence.");
    return result;
}
std::uint64_t Timeline::frame(std::uint64_t cycle,const Rational& offset) const {
    std::uint64_t value{};
    require(scheduler::round(coordinate(cycle,offset),value),"Tempo sample coordinate overflow.");return value;
}
Timeline Timeline::changed(std::uint64_t cycle,std::uint16_t bpm) const {
    require(spec_.cycles<=32 && points_.size()<32 && cycle>points_.back().cycle && cycle<spec_.cycles,
            "Tempo changes need an ordered continuing boundary within the selected 1–32 passes.");
    require(bpm>=20 && bpm<=300 && bpm!=points_.back().bpm,"Tempo change must name a different supported 20–300 BPM value.");
    Timeline next=*this;const auto anchor=coordinate(cycle);next.points_.push_back({cycle,bpm,anchor});
    require(next.frame(cycle)<next.frame(cycle+1),"Changed tempo has no distinct cycle sample extent.");
    next.frame(spec_.cycles);return next;
}
std::uint64_t Timeline::completed(std::uint64_t accepted) const {
    require(accepted<=frame(spec_.cycles),"Accepted output exceeds the retained tempo timeline.");
    std::uint64_t lo=0,hi=spec_.cycles;
    while(lo<hi){const auto mid=lo+(hi-lo+1)/2;if(frame(mid)<=accepted)lo=mid;else hi=mid-1;}return lo;
}
std::uint16_t Timeline::tempo(std::uint64_t cycle) const {
    require(cycle<spec_.cycles,"No continuing tempo after the selected target.");
    const auto it=std::upper_bound(points_.begin(),points_.end(),cycle,[](auto n,const auto& p){return n<p.cycle;});
    return std::prev(it)->bpm;
}
std::uint16_t Timeline::acceptedTempo(std::uint64_t accepted) const {
    if(accepted<=frame(0))return spec_.initialBpm;
    return tempo(completed(accepted-1)); // an endpoint alone submitted no new-tempo sample
}
std::vector<TempoSlice> Timeline::slices(std::uint64_t accepted) const {
    completed(accepted);std::vector<TempoSlice> result;
    for(std::size_t i=0;i<points_.size();++i){
        const auto begin=frame(points_[i].cycle);
        const auto end=std::min(accepted,i+1<points_.size()?frame(points_[i+1].cycle):accepted);
        if(begin<end)result.push_back({points_[i].bpm,begin,end});
    }return result;
}
bool Timeline::extends(const Timeline& previous,std::uint64_t oldThrough,std::uint64_t through) const {
    if(!same(spec_,previous.spec_) || through<oldThrough || points_.size()<previous.points_.size())return false;
    for(std::size_t i=0;i<points_.size();++i){
        const auto& point=points_[i];
        if(i<previous.points_.size()){
            const auto& old=previous.points_[i];
            if(point.cycle!=old.cycle || point.bpm!=old.bpm || !(point.anchor==old.anchor))return false;
        }else if(frame(point.cycle)<oldThrough)return false;
        if(i && frame(point.cycle)>=through)return false;
    }
    return true;
}
}
