#include "core/ReferenceAudio.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <stdexcept>

namespace fathom::reference {
namespace {
bool methodValid(Method m) { return m==Method::Pluck || m==Method::Sine; }
scheduler::FrameRatio frames(const Rational& q,const Configuration& c) {
    scheduler::FrameRatio v;
    if(!scheduler::samples(q,c.rate,c.bpm,c.unit,v))throw std::invalid_argument("Reference time/rate/tempo outside supported arithmetic");
    return v;
}
std::string tuningSourceBinding(const guitar::Setup& setup,int string,ToneTarget target,Method method) {
    // Setup, string and target are validated before this is called; compile
    // refuses an unsupported method before publishing a Program. Decimal
    // values and the fixed version token cannot contain these delimiters.
    std::string key=target==ToneTarget::OpenString?"tool:open-string-tone":"tool:capo-position-tone";
    key+="|version="+setup.valueVersion+"|string="+std::to_string(string)+"|open=";
    for(std::size_t i=0;i<setup.openMidi.size();++i) {
        if(i)key+=',';
        key+=std::to_string(setup.openMidi[i]);
    }
    key+="|capo="+std::to_string(setup.capo)+"|frets="+std::to_string(setup.fretCount);
    key+="|hand=";
    key+=setup.handedness==guitar::Handedness::Right?"right":"left";
    key+="|method=";
    key+=method==Method::Pluck?"pluck":"sine";
    return key;
}
}
double frequency(int midi) {
    if(midi<0 || midi>127)throw std::invalid_argument("Reference pitch outside MIDI0..127");
    return 440.0*std::pow(2.0,(midi-69)/12.0);
}
Program compile(std::shared_ptr<const music::ValidatedModel> model,const Configuration& c) {
    if(!model || !methodValid(c.method))throw std::invalid_argument("Reference requires validated model and explicit supported method");
    const auto ready=music::assessReadiness(*model,{{music::Attack::Picked,music::Attack::Held,music::Attack::HammerOn,music::Attack::PullOff,music::Attack::SlideArrival,music::Attack::Bend},true,true,true});
    if(!ready.technicallyRenderable) {
        const auto& i=ready.issues.front();throw std::invalid_argument(i.event+": "+i.code+" — "+i.explanation);
    }
    if(model->source().instrument.openMidi.size()!=6)throw std::invalid_argument("Reference method supports six declared strings");
    if(model->source().terminal && !(c.cycle==*model->source().terminal))
        throw std::invalid_argument("Declared cycle must equal explicit terminal endpoint");
    Program p;p.source_=std::move(model);p.method_=c.method;
    std::map<std::pair<std::string,int>,std::size_t> members;
    std::map<int,const music::EventProjection*> lastOnString;
    std::size_t segmentCount{};
    for(const auto& e:p.source_->projections()) {
        if(!e.span.onset || !e.span.duration || c.cycle<*e.span.onset+*e.span.duration)
            throw std::invalid_argument(e.eventId+": explicit event span must fit whole declared cycle");
        for(const auto& t:e.tones) {
            if(!t.soundingSpan.onset || !t.soundingSpan.duration)throw std::invalid_argument(e.eventId+": explicit sounding gate required");
            const auto onset=*t.soundingSpan.onset,end=onset+*t.soundingSpan.duration;
            const auto gateLength=frames(*t.soundingSpan.duration,c);
            if(gateLength.n<gateLength.d)throw std::invalid_argument(e.eventId+": gate shorter than one sample cannot survive every cycle anchor");
            if(c.cycle<end)throw std::invalid_argument(e.eventId+": gate crosses unsupported loop cutpoint");
            const auto startFrames=frames(onset,c),endFrames=frames(end,c);
            std::uint64_t startSample{},endSample{};
            if(!scheduler::round(startFrames,startSample) || !scheduler::round(endFrames,endSample) || endSample<=startSample)
                throw std::invalid_argument(e.eventId+": pitch segment collapses to a sample boundary");
            const double hz=frequency(t.soundingMidi);
            if(hz*(c.method==Method::Pluck?3.0:1.0)>=c.rate/2.0)
                throw std::invalid_argument(e.eventId+": method harmonics reach Nyquist; choose an explicitly supported method/rate");
            if(t.attack==music::Attack::Held) {
                auto previous=members.find({t.tieFrom,t.string});
                if(e.tones.size()!=1 || previous==members.end())throw std::invalid_argument(e.eventId+": held chord or missing origin is not supported");
                const auto& origin=*std::find_if(p.source_->projections().begin(),p.source_->projections().end(),[&](const auto& x){return x.eventId==t.tieFrom;});
                if(origin.tones.size()!=1)throw std::invalid_argument(e.eventId+": held chord continuation is not supported");
                auto& v=p.voices_[previous->second];
                if(!(v.end==onset) || v.segments.empty() || v.segments.back().midi!=t.soundingMidi)throw std::invalid_argument(e.eventId+": noncontiguous held chain");
                v.end=end;v.endFrames=endFrames;v.sourceEvents.push_back(e.eventId);
                v.segments.back().end=end;v.segments.back().endFrames=endFrames;
                members[{e.eventId,t.string}]=previous->second;
            } else if(t.attack==music::Attack::HammerOn || t.attack==music::Attack::PullOff || t.attack==music::Attack::SlideArrival) {
                const auto last=lastOnString.find(t.string);
                if(last==lastOnString.end())throw std::invalid_argument(e.eventId+": missing same-string legato antecedent");
                const auto* origin=last->second;
                const auto prior=std::find_if(origin->tones.begin(),origin->tones.end(),[&](const auto& x){return x.string==t.string;});
                if(prior==origin->tones.end())throw std::invalid_argument(e.eventId+": missing same-string pitch");
                const auto member=members.find({origin->eventId,t.string});
                if(member==members.end())throw std::invalid_argument(e.eventId+": missing legato voice");
                auto& v=p.voices_[member->second];
                if(!(v.end==onset) || !(prior->soundingSpan.onset && prior->soundingSpan.duration)
                    || !(*prior->soundingSpan.onset+*prior->soundingSpan.duration==onset)
                    || (t.attack==music::Attack::HammerOn && t.fret<=prior->fret)
                    || (t.attack==music::Attack::PullOff && t.fret>=prior->fret)
                    || (t.attack==music::Attack::SlideArrival && (prior->fret<=0 || t.fret<=0 || t.fret==prior->fret
                        || frames(*prior->soundingSpan.duration,c).n / frames(*prior->soundingSpan.duration,c).d < 9)))
                    throw std::invalid_argument(e.eventId+": invalid legato/slide gate or direction (fretted endpoints and nine-sample origin required)");
                for(const auto& possible:p.source_->projections())
                    if(possible.kind==music::Kind::Contact &&
                       (possible.contact==music::Contact::Release || possible.contact==music::Contact::Muted) &&
                       possible.span.onset && !(*possible.span.onset<*prior->soundingSpan.onset) &&
                       ! (onset<*possible.span.onset) &&
                       std::find(possible.scopeStrings.begin(),possible.scopeStrings.end(),t.string)!=possible.scopeStrings.end())
                        throw std::invalid_argument(e.eventId+": legato transition cancelled");
                if(v.segments.size()>=scheduler::maxPlanEvents)throw std::invalid_argument(e.eventId+": legato segment capacity");
                v.segments.push_back({e.eventId,t.attack,t.soundingMidi,hz,onset,end,startFrames,endFrames,{}});
                if(t.attack==music::Attack::SlideArrival)v.hasSlide=true;
                ++segmentCount;
                v.end=end;v.endFrames=endFrames;v.sourceEvents.push_back(e.eventId);
                members[{e.eventId,t.string}]=member->second;
            } else {
                members[{e.eventId,t.string}]=p.voices_.size();
                p.voices_.push_back({t.string,t.soundingMidi,hz,onset,end,startFrames,endFrames,{e.eventId},
                                     {{e.eventId,t.attack,t.soundingMidi,hz,onset,end,startFrames,endFrames,{}}},false});
                ++segmentCount;
            }
            if(t.attack==music::Attack::Bend) {
                if(!t.bend || p.voices_.empty())throw std::invalid_argument(e.eventId+": missing bend contour");
                auto& segment=p.voices_.back().segments.back();
                for(const auto& knot:t.bend->knots) {
                    std::uint64_t sample{};
                    if(!scheduler::round(frames(knot.q,c),sample))throw std::invalid_argument(e.eventId+": bend knot frame overflow");
                    if(!segment.bendKnots.empty() && sample<=segment.bendKnots.back().frame)
                        throw std::invalid_argument(e.eventId+": bend knots collapse to the same sample");
                    const double knotHz=frequency(t.soundingMidi)*std::pow(2.0,knot.offsetSemitones.displayValue()/12.0);
                    if(knotHz*(c.method==Method::Pluck?3.0:1.0)>=c.rate/2.0)
                        throw std::invalid_argument(e.eventId+": bend reaches Nyquist");
                    segment.bendKnots.push_back({sample,knotHz});
                }
                if(segment.bendKnots.front().frame!=startSample || segment.bendKnots.back().frame!=endSample)
                    throw std::invalid_argument(e.eventId+": bend contour/gate sample mismatch");
            }
            if(segmentCount>scheduler::maxPlanEvents)throw std::invalid_argument(e.eventId+": pitch segment capacity");
            lastOnString[t.string]=&e;
        }
        if(e.kind==music::Kind::Contact && e.contact==music::Contact::Muted) {
            const auto attackEnd=*e.span.onset+std::min(*e.span.duration,Rational{1,32});
            const auto startFrames=frames(*e.span.onset,c),endFrames=frames(attackEnd,c);
            std::uint64_t start{},end{};
            if(!scheduler::round(startFrames,start) || !scheduler::round(endFrames,end) || end<=start)
                throw std::invalid_argument(e.eventId+": muted attack collapses to a sample boundary");
            for(int string:e.scopeStrings) p.muted_.push_back({e.eventId,string,*e.span.onset,attackEnd,endFrames});
        }
        if(e.kind==music::Kind::Rest || (e.kind==music::Kind::Contact && e.contact==music::Contact::Release))
            p.silences_.push_back({e.eventId,e.scopeStrings});
    }
    if (p.source_->source().backing) {
        for (const auto& section:p.source_->source().backing->sections) {
            const auto end=section.onset+section.duration;
            if (c.cycle<end)throw std::invalid_argument("Backing section crosses declared cycle");
            const auto startFrames=frames(section.onset,c),endFrames=frames(end,c);
            std::uint64_t startSample{},endSample{};
            if (!scheduler::round(startFrames,startSample) || !scheduler::round(endFrames,endSample) || endSample<=startSample)
                throw std::invalid_argument("Backing section has no renderable sample gate");
            const auto hz=frequency(section.midi);
            if (hz>=c.rate/2.0)throw std::invalid_argument("Backing sine reaches Nyquist");
            p.backing_.push_back({section.midi,p.source_->source().backing->levelMilli,hz,section.onset,end,startFrames,endFrames});
        }
        if (p.backing_.size()!=p.source_->source().backing->sections.size())
            throw std::invalid_argument("Declared backing is not rendered");
    }
    scheduler::PlanSpec s;s.owner=c.owner;s.binding=c.binding;s.sourceBinding=c.sourceBinding;s.sampleRate=c.rate;s.bpm=c.bpm;s.unit=c.unit;s.cycle=c.cycle;s.intro=c.intro;
    if(p.voices_.size()+p.backing_.size()+p.muted_.size()>scheduler::maxPlanEvents/2 ||
       p.silences_.size()>scheduler::maxPlanEvents-2*(p.voices_.size()+p.backing_.size()+p.muted_.size()))
        throw std::invalid_argument("Reference exceeds bounded scheduler event capacity; split only at an authored safe boundary");
    for(std::size_t i=0;i<p.voices_.size();++i) {
        const auto& v=p.voices_[i];std::uint64_t start{},end{};
        if(!scheduler::round(v.startFrames,start) || !scheduler::round(v.endFrames,end) || end<=start)
            throw std::invalid_argument("Reference gate is shorter than representable sample interval");
        const auto id=static_cast<std::uint32_t>(i+1);
        s.events.push_back({v.onset,id,scheduler::Role::Reference,scheduler::Action::Attack});
        s.events.push_back({v.end,id,scheduler::Role::Reference,scheduler::Action::Release});
    }
    for(std::size_t i=0;i<p.backing_.size();++i) {
        const auto& b=p.backing_[i];const auto id=static_cast<std::uint32_t>(p.voices_.size()+i+1);
        s.events.push_back({b.onset,id,scheduler::Role::Reference,scheduler::Action::Attack});
        s.events.push_back({b.end,id,scheduler::Role::Reference,scheduler::Action::Release});
    }
    for(std::size_t i=0;i<p.muted_.size();++i) {
        const auto& v=p.muted_[i]; const auto id=static_cast<std::uint32_t>(p.voices_.size()+p.backing_.size()+i+1);
        s.events.push_back({v.onset,id,scheduler::Role::Reference,scheduler::Action::Attack});
        s.events.push_back({v.end,id,scheduler::Role::Reference,scheduler::Action::Release});
    }
    for(std::size_t i=0;i<p.silences_.size();++i) {
        const auto& silence=p.silences_[i];const auto& e=*std::find_if(p.source_->projections().begin(),p.source_->projections().end(),[&](const auto& x){return x.eventId==silence.event;});
        s.events.push_back({*e.span.onset,static_cast<std::uint32_t>(p.voices_.size()+p.backing_.size()+p.muted_.size()+i+1),scheduler::Role::Reference,scheduler::Action::Silence});
    }
    p.schedule_=scheduler::compile(s);return p;
}
bool Program::compatibleTempo(const Program& p) const noexcept {
    // Pointer identity binds the SAME immutable validated content, not merely reused IDs.
    return source_ && source_==p.source_ && method_==p.method_ && schedule_.compatibleTempo(p.schedule_);
}
Program tuningTone(const guitar::Setup& setup,int string,ToneTarget target,const scheduler::Owner& owner,std::uint64_t binding,std::uint32_t rate,Method method) {
    if(!guitar::validate(setup).empty() || string<1 || string>6 || (target!=ToneTarget::OpenString && target!=ToneTarget::CapoPosition))
        throw std::invalid_argument("Invalid active setup/string/reference target");
    const auto position=guitar::position(setup,string,0);
    if(target==ToneTarget::CapoPosition && !position.available())throw std::invalid_argument("Capo reference position is unavailable");
    music::Model m;m.itemId="synthetic:reference-tone";m.schemaVersion="reference-tool1";m.contentVersion=setup.valueVersion;m.syntheticFixture=true;m.proposalExample=false;
    m.instrument.openMidi.assign(setup.openMidi.begin(),setup.openMidi.end());m.instrument.capo=target==ToneTarget::OpenString?0:setup.capo;
    music::Event e;e.id="tone";e.span={Rational{},Rational{3}};music::Tone t;t.string=string;t.fret=0;t.midi=target==ToneTarget::OpenString?setup.openMidi[static_cast<std::size_t>(string-1)]:*position.midi;e.tones={t};m.events={e};
    auto validated=music::validate(m);if(!validated.validReference())throw std::invalid_argument("Reference setup produced invalid pitch binding");
    Configuration c;c.owner=owner;c.binding=binding;c.sourceBinding=tuningSourceBinding(setup,string,target,method);c.rate=rate;c.bpm=60;c.cycle=Rational{3};c.method=method;
    return compile(validated.model,c);
}
double sample(Method method,double hz,std::uint64_t age,std::uint64_t length,std::uint32_t rate) noexcept {
    if(!methodValid(method) || !rate || age>=length || !std::isfinite(hz) || hz<=0)return 0;
    const double t=static_cast<double>(age)/rate,phase=6.283185307179586476925286766559*hz*t;
    double value=std::sin(phase);
    if(method==Method::Pluck)value=(value+.4*std::sin(2*phase)+.2*std::sin(3*phase))/1.6*std::exp(-6*t);
    return value*std::min(t/.003,1.0)*std::min((static_cast<double>(length)/rate-t)/.01,1.0);
}
bool Renderer::bind(const Program& p) noexcept {
    if(program_ || failed_ || stopped_ || !p.schedule().valid())return false;
    program_=&p;intro_=p.schedule().introDuration().n!=0;return refreshDue();
}
bool Renderer::fail() noexcept {failed_=true;stop();return false;}
void Renderer::stop() noexcept {stopped_=true;for(auto& v:active_)v={};for(auto& v:mutedActive_)v={};backingActive_={};}
bool Renderer::at(scheduler::FrameRatio offset,std::uint64_t& value) const noexcept {
    scheduler::FramePosition total;return scheduler::add(anchor_,offset,total) && scheduler::round(total,value);
}
bool Renderer::refreshDue() noexcept {
    const auto& plan=program_->schedule();
    if(intro_)return scheduler::round(plan.introDuration(),due_) || fail();
    const auto offset=event_<plan.events().size()?plan.events()[event_].offset:plan.duration();
    return at(offset,due_) || fail();
}
bool Renderer::accept(const scheduler::Fact& f) noexcept {
    if(!program_ || failed_ || stopped_ || !(f.owner==program_->schedule().owner()) || f.binding!=program_->schedule().binding() || f.frame!=nextFrame_)return fail();
    const auto& plan=program_->schedule();std::uint64_t expected{};
    if(f.kind!=scheduler::FactKind::Event && (f.sourceEvent!=0 || f.role!=scheduler::Role::Reference || f.action!=scheduler::Action::Attack))return fail();
    if(intro_) {
        if(f.kind!=scheduler::FactKind::CountInEnded || f.cycle!=0 || !scheduler::round(plan.introDuration(),expected) || expected!=f.frame)return fail();
        if(!scheduler::position(plan.introDuration(),anchor_))return fail();intro_=false;return refreshDue();
    }
    if(f.kind==scheduler::FactKind::CycleCompleted) {
        if(event_!=plan.events().size() || cycle_==std::numeric_limits<std::uint64_t>::max() || f.cycle!=cycle_+1 || !at(plan.duration(),expected) || f.frame!=expected)return fail();
        for(const auto& v:active_)if(v.voice)return fail();
        if(backingActive_.voice)return fail();
        for(const auto& v:mutedActive_)if(v.voice)return fail();
        if(!scheduler::add(anchor_,plan.duration(),anchor_))return fail();
        ++cycle_;event_=0;boundaryOpen_=true;return refreshDue();
    }
    if(f.kind!=scheduler::FactKind::Event || f.cycle!=cycle_ || event_>=plan.events().size())return fail();
    const auto& e=plan.events()[event_];
    if(f.sourceEvent!=e.sourceEvent || f.role!=e.role || f.action!=e.action || !at(e.offset,expected) || expected!=f.frame)return fail();
    boundaryOpen_=false;++event_;
    if(f.action==scheduler::Action::Silence) {
        if(f.sourceEvent<=program_->voices().size()+program_->backingVoices().size()+program_->mutedVoices().size())return fail();
        const auto index=f.sourceEvent-program_->voices().size()-program_->backingVoices().size()-program_->mutedVoices().size()-1;
        if(index>=program_->silences().size())return fail();
        for(int string:program_->silences()[index].strings)
            if(active_[static_cast<std::size_t>(string-1)].voice || mutedActive_[static_cast<std::size_t>(string-1)].voice)return fail();
        return refreshDue();
    }
    if(f.sourceEvent>program_->voices().size() && f.sourceEvent<=program_->voices().size()+program_->backingVoices().size()) {
        const auto& b=program_->backingVoices()[f.sourceEvent-program_->voices().size()-1];
        if(f.action==scheduler::Action::Attack) {
            std::uint64_t end{};
            if(backingActive_.voice || !at(b.endFrames,end) || end<=f.frame)return fail();
            backingActive_={&b,f.frame,end,f.sourceEvent};
        } else {
            if(!backingActive_.voice || backingActive_.id!=f.sourceEvent || backingActive_.end!=f.frame)return fail();
            backingActive_={};
        }
        return refreshDue();
    }
    if(f.sourceEvent>program_->voices().size()+program_->backingVoices().size() &&
       f.sourceEvent<=program_->voices().size()+program_->backingVoices().size()+program_->mutedVoices().size()) {
        const auto& mute=program_->mutedVoices()[f.sourceEvent-program_->voices().size()-program_->backingVoices().size()-1];
        auto& current=mutedActive_[static_cast<std::size_t>(mute.string-1)];
        if(f.action==scheduler::Action::Attack) {
            std::uint64_t end{};
            if(current.voice || active_[static_cast<std::size_t>(mute.string-1)].voice || !at(mute.endFrames,end) || end<=f.frame)return fail();
            current={&mute,f.frame,end,f.sourceEvent};
        } else {
            if(!current.voice || current.id!=f.sourceEvent || current.end!=f.frame)return fail();
            current={};
        }
        return refreshDue();
    }
    if(!f.sourceEvent || f.sourceEvent>program_->voices().size())return fail();
    const auto& voice=program_->voices()[f.sourceEvent-1];auto& current=active_[static_cast<std::size_t>(voice.string-1)];
    if(f.action==scheduler::Action::Attack) {
        std::uint64_t end{};if(current.voice || mutedActive_[static_cast<std::size_t>(voice.string-1)].voice || !at(voice.endFrames,end) || end<=f.frame)return fail();
        std::uint64_t segmentEnd{};
        if(voice.segments.empty() || !at(voice.segments.front().endFrames,segmentEnd) || segmentEnd<=f.frame)return fail();
        current={&voice,f.frame,end,f.sourceEvent,0,segmentEnd,0.0};
    } else {
        if(!current.voice || current.id!=f.sourceEvent || current.end!=f.frame)return fail();
        current={};
    }
    return refreshDue();
}
bool Renderer::selectTempo(const Program& p) noexcept {
    if(!program_ || failed_ || stopped_ || !boundaryOpen_ || !program_->compatibleTempo(p))return fail();
    program_=&p;boundaryOpen_=false;return refreshDue();
}
bool Renderer::sampleFrame(std::uint64_t frame,float& mono) noexcept {
    mono=0;if(!program_ || failed_ || stopped_ || frame!=nextFrame_ || nextFrame_==std::numeric_limits<std::uint64_t>::max())return fail();
    const auto& plan=program_->schedule();
    if(frame>=due_)return fail();
    double value=0;
    constexpr double twoPi=6.283185307179586476925286766559;
    for(auto& active:active_)if(active.voice) {
        if(frame<active.start || frame>=active.end)return fail();
        const auto& segments=active.voice->segments;
        if(active.segment>=segments.size())return fail();
        if(frame>=active.segmentEnd) {
            if(frame!=active.segmentEnd || active.segment+1>=segments.size())return fail();
            ++active.segment;
            if(!at(segments[active.segment].endFrames,active.segmentEnd) || active.segmentEnd<=frame)return fail();
        }
        if(segments.size()==1 && segments.front().bendKnots.empty()) {
            value+=sample(program_->method(),active.voice->hz,frame-active.start,active.end-active.start,plan.sampleRate())/6.0;
        } else {
            // One excitation at the first pick. A nonpicked arrival changes frequency
            // while phase and the chain envelope carry through the exact sample seam.
            const auto age=static_cast<double>(frame-active.start)/plan.sampleRate();
            const auto remaining=static_cast<double>(active.end-frame)/plan.sampleRate();
            const double envelope=std::min(age/.003,1.0)*std::min(remaining/.01,1.0);
            double wave=std::sin(active.phase);
            if(program_->method()==Method::Pluck)
                wave=(wave+.4*std::sin(2*active.phase)+.2*std::sin(3*active.phase))/1.6;
            // Reference slide convention: interpolate frequency linearly in Hz over
            // the final quarter of the preceding segment, ending at the exact authored
            // arrival seam. The source supplies no motion-start time or curve.
            double advanceHz=segments[active.segment].hz;
            const auto& bendKnots=segments[active.segment].bendKnots;
            if(!bendKnots.empty()) {
                while(active.bendIndex+2<bendKnots.size() && frame>=active.start+bendKnots[active.bendIndex+1].frame-bendKnots.front().frame)
                    ++active.bendIndex;
                const auto& from=bendKnots[active.bendIndex];
                const auto& to=bendKnots[active.bendIndex+1];
                const auto local=frame-active.start+bendKnots.front().frame;
                const double fraction=static_cast<double>(local-from.frame)/static_cast<double>(to.frame-from.frame);
                advanceHz=from.hz*std::pow(to.hz/from.hz,fraction);
            }
            if(active.segment+1<segments.size() && segments[active.segment+1].attack==music::Attack::SlideArrival) {
                std::uint64_t segmentStart{};
                if(!at(segments[active.segment].onsetFrames,segmentStart) || active.segmentEnd<=segmentStart+7)return fail();
                const auto window=(active.segmentEnd-segmentStart)/4;
                const auto glideStart=active.segmentEnd-window;
                if(frame>=glideStart) {
                    const double portion=static_cast<double>(frame-glideStart)/static_cast<double>(window);
                    advanceHz+=(segments[active.segment+1].hz-advanceHz)*portion;
                }
            }
            const bool hasSlide=active.voice->hasSlide;
            if((hasSlide || !bendKnots.empty()) && program_->method()==Method::Pluck)
                wave*=std::exp(-6*age);
            value+=wave*envelope/6.0;
            active.phase=std::remainder(active.phase+twoPi*advanceHz/plan.sampleRate(),twoPi);
        }
    }
    for(const auto& mute:mutedActive_)if(mute.voice) {
        if(frame<mute.start || frame>=mute.end)return fail();
        const auto age=frame-mute.start, length=mute.end-mute.start;
        // Fixed integer hash gives a repeatable broadband, pitch-free transient.
        std::uint32_t noise=static_cast<std::uint32_t>(age)^
            (0x9e3779b9u*static_cast<std::uint32_t>(mute.voice->string));
        noise^=noise<<13;noise^=noise>>17;noise^=noise<<5;
        const double unit=(static_cast<double>(noise&0xffffu)/32767.5)-1.0;
        const double envelope=std::exp(-8.0*static_cast<double>(age)/static_cast<double>(length));
        value+=0.12*unit*envelope;
    }
    if(backingActive_.voice) {
        if(frame<backingActive_.start || frame>=backingActive_.end)return fail();
        const double level=backingActive_.voice->levelMilli/1000.0;
        value=value*(1.0-level)+level*sample(Method::Sine,backingActive_.voice->hz,
            frame-backingActive_.start,backingActive_.end-backingActive_.start,plan.sampleRate());
    }
    if(!std::isfinite(value) || std::abs(value)>1.0000001)return fail();
    mono=static_cast<float>(value);++nextFrame_;boundaryOpen_=false;return true;
}
}
