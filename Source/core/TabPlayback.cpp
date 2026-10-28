#include "core/TabPlayback.hpp"
#include <stdexcept>
namespace fathom::tab {
namespace {
bool same(const practice::Configuration& a,const practice::Configuration& b){
 return a.span==b.span&&a.countIn==b.countIn&&a.meter==b.meter&&a.sourceRequiresCountIn==b.sourceRequiresCountIn&&a.faithfulWholeSpan==b.faithfulWholeSpan&&a.rate==b.rate&&a.bpm==b.bpm&&a.unit==b.unit&&a.targetCycles==b.targetCycles;
}
}
std::uint64_t Playback::frame(std::uint64_t cycle,const Rational& offset)const{
 if(!timeline_)throw std::logic_error("TAB has no accepted timeline.");
 return timeline_->frame(cycle,offset);
}
void Playback::bind(std::shared_ptr<const Document> document,std::shared_ptr<const music::ValidatedModel> preparedModel,const practice::Coordinator& c){
 if(!document||!preparedModel||&document->source()!=&preparedModel->source()||!document->allTimed()||!c.owner().valid()||c.context().empty()||c.generations().empty()||!(c.generations().back().owner==c.owner())||c.generations().back().sequence||c.generations().back().clientAcceptedThrough||(c.state()!=practice::State::CountIn&&c.state()!=practice::State::Running))throw std::invalid_argument("TAB needs a timed document and an explicit fresh current practice generation.");
 Playback next;next.document_=std::move(document);next.config_=c.configuration();next.owner_=c.owner();next.context_=c.context();
 next.timeline_=c.timeline(c.owner());
 if(next.document_->source().events.size()>scheduler::maxPlanEvents)throw std::invalid_argument("TAB playback span exceeds the supported event budget; select a smaller validated span.");
 for(const auto& e:next.document_->source().events){if(next.config_.span<*e.span.onset+*e.span.duration)throw std::invalid_argument("TAB event crosses the pinned whole-span boundary; select the matching validated span.");}
 const auto done=c.completedCycles();if(done>=next.config_.targetCycles)throw std::invalid_argument("TAB target is already complete.");next.remaining_=next.config_.targetCycles-done;
 if(next.frame(0,Rational{})>=next.frame(1,Rational{}))throw std::invalid_argument("TAB cycle has no distinct sample extent.");
 next.frame(next.remaining_,Rational{});next.position_.progress=c.generations().back();*this=std::move(next);
}
bool Playback::update(const practice::Coordinator& c){
 if(!document_||!(c.owner()==owner_)||c.context()!=context_||!same(c.configuration(),config_)||c.generations().empty())return false;
 const auto& p=c.generations().back();
 if(!(p.owner==owner_)||!p.sequence||p.sequence<=position_.progress.sequence||p.clientAcceptedThrough<position_.progress.clientAcceptedThrough||p.clientAcceptedThrough>c.timeline(owner_).frame(remaining_,Rational{}))return false;
 timeline_=c.timeline(owner_);
 PlaybackPosition next;next.progress=p;
 const auto intro=frame(0,Rational{});
 if(p.clientAcceptedThrough>intro){
  next.hasMusicalSample=true;next.sample=p.clientAcceptedThrough-1;
  std::uint64_t lo=0,hi=remaining_-1;while(lo<hi){const auto mid=lo+(hi-lo+1)/2;if(frame(mid,Rational{})<=next.sample)lo=mid;else hi=mid-1;}next.cycle=lo;
  for(const auto& e:document_->source().events){const auto begin=frame(lo,*e.span.onset),end=frame(lo,*e.span.onset+*e.span.duration);
   if((begin<=next.sample&&next.sample<end)||(e.span.duration->numerator()==0&&e.kind==music::Kind::Contact&&begin==next.sample))next.events.push_back(e.id);
  }
 }
 position_=std::move(next);return true;
}
}
