#include "tasks/ManualTaskAdapter.hpp"
#include "content/Canonical.hpp"
#include <charconv>
#include <chrono>
#include <atomic>
#include <limits>

namespace fathom::tasks {
std::uint64_t ManualTaskAdapter::nextInstance() noexcept {static std::atomic<std::uint64_t> next{1};return next.fetch_add(1);}
ManualTaskAdapter::ManualTaskAdapter(const Definition& definition):task_(definition),instance_(nextInstance()){}
IntentToken ManualTaskAdapter::capture(IntentKind kind) const {
    const auto state=task_.view();
    return {instance_,pass_,revision_,task_.definition().sourceKey(),task_.definition().policySha256(),state.phase,state.actionIndex,kind};
}
bool ManualTaskAdapter::same(const IntentToken& token) const noexcept {
    const auto state=task_.view();
    return token.instance==instance_&&token.pass==pass_&&token.revision==revision_&&
        token.sourceKey==task_.definition().sourceKey()&&token.policySha256==task_.definition().policySha256()&&
        token.phase==state.phase&&token.actionIndex==state.actionIndex;
}
void ManualTaskAdapter::invalidateClock() noexcept {clockArmed_=false;originSet_=false;clockOwner_={};clockBinding_=lastSequence_=originFrames_=0;sampleRate_=0;}
bool ManualTaskAdapter::applyImpl(const IntentToken& token,std::optional<int> bpm,TempoRange range,std::optional<json::Value> report){
    if(!same(token)){error_="Stale task intent refused";return false;}
    try {
        const auto before=task_.view();
        json::Value eventReport=report.value_or(json::Value::Object{});
        const bool typed=bool(task_.definition().reportContract());
        const bool reportIntent=token.kind==IntentKind::Ready||token.kind==IntentKind::Acknowledge||
            token.kind==IntentKind::Release||token.kind==IntentKind::Unknown;
        if(typed&&reportIntent&&!report)throw Error("TYPED_REPORT_REQUIRED","Explicit source report required");
        if(report&&(!typed||!reportIntent))throw Error("REPORT_INTENT","Report does not belong to this intent");
        switch(token.kind){
        case IntentKind::SourceOrder: task_.chooseSourceOrder();eventReport=json::Value::Object{{"mode","source_order_only"}};break;
        case IntentKind::EvenPulse:
            if(!bpm)throw Error("EXPLICIT_TEMPO","Choose a fresh integer quarter BPM before paced mode");
            task_.chooseEvenPulse(*bpm,range);eventReport=json::Value::Object{{"mode","fathom_even_pulse"},{"bpm",json::Value::fromInteger(*bpm)}};break;
        case IntentKind::Ready:
            if(before.mode==Mode::FathomEvenPulse){
                if(!bpm||*bpm<range.minimumBpm||*bpm>range.maximumBpm||bpm!=before.selectedBpm)
                    throw Error("CURRENT_TEMPO","Current BPM differs from the selected paced guide; reselect paced mode at the visible BPM before Ready");
            }
            if(typed)task_.readyReported(*report,range);else task_.ready(range);break;
        case IntentKind::Acknowledge: if(typed)task_.respondReported(*report);else task_.respond(Response::Acknowledged);break;
        case IntentKind::Unknown:
            if(!typed||*report!=json::Value(json::Value::Object{{"response","unknown"}}))
                throw Error("UNKNOWN_REPORT","Explicit unknown source report required");
            task_.respondReported(*report);break;
        case IntentKind::Retry:
            if(typed)eventReport=json::Value::Object{{"response","needs_retry"}};
            if(typed&&before.phase==Phase::ManualSteps){eventReport=json::Value::Object{{"response","needs_retry"}};task_.respondReported(eventReport);}
            else task_.requestRetry();break;
        case IntentKind::Cancel:
            if(typed&&before.phase==Phase::Cues)eventReport=json::Value::Object{{"response","stopped"}};
            if(typed&&before.phase==Phase::ManualSteps){eventReport=json::Value::Object{{"response","stopped"}};task_.respondReported(eventReport);}
            else task_.cancel();break;
        case IntentKind::Release: if(typed)task_.acknowledgeReleaseReported(*report);else task_.acknowledgeRelease();break;
        case IntentKind::Again: task_.beginAnotherPass();break;
        case IntentKind::Reopen: task_.reopen();break;
        default: throw Error("INTENT_KIND","Unsupported task intent");
        }
        const auto after=task_.view();
        if(token.kind==IntentKind::Retry||token.kind==IntentKind::Cancel||token.kind==IntentKind::Reopen||
           token.kind==IntentKind::Again||token.kind==IntentKind::Release||
           (before.phase==Phase::Cues&&after.phase!=Phase::Cues)) {
            invalidateClock();++pass_;
        }
        ++revision_;
        history_.push_back({token,std::move(eventReport),before,after,task_.diagnosis(),false,false});
        error_.clear();return true;
    }catch(const std::exception& e){error_=e.what();return false;}
}
bool ManualTaskAdapter::armClockImpl(const scheduler::Owner& owner,std::uint64_t binding,std::uint32_t rate){
    if(task_.view().phase!=Phase::Cues||!owner.valid()||!binding||!rate||clockArmed_){error_="Current cue pass cannot bind this clock";return false;}
    clockOwner_=owner;clockBinding_=binding;sampleRate_=rate;lastSequence_=originFrames_=0;originSet_=false;clockArmed_=true;error_.clear();return true;
}
bool ManualTaskAdapter::progressImpl(const platform::MetronomeProgress& value){
    if(!clockArmed_||task_.view().phase!=Phase::Cues){error_="Late clock progress refused";return false;}
    if(!(value.owner==clockOwner_)||value.binding!=clockBinding_||value.sequence<=lastSequence_||
       value.phase!=metronome::Phase::Running||value.terminal||value.fault||
       value.tempo.tempo!=task_.view().selectedBpm.value_or(0)||!value.clientAcceptedThrough){
        error_="Foreign, stale, interrupted or changed-tempo clock progress refused";return false;
    }
    if(originSet_&&value.totalActiveFrames<originFrames_){error_="Clock frame regression refused";return false;}
    lastSequence_=value.sequence;
    if(!originSet_){originFrames_=value.totalActiveFrames;originSet_=true;error_.clear();return true;}
    const auto frames=value.totalActiveFrames-originFrames_;
    const auto bpm=static_cast<std::uint64_t>(*task_.view().selectedBpm);
    if(frames>static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max())/bpm){error_="Clock coordinate overflow refused";return false;}
    try {
        const auto before=task_.view();
        task_.followCuePosition(QuarterTime{Rational{static_cast<std::int64_t>(frames*bpm),static_cast<std::int64_t>(sampleRate_)*60}});
        const auto after=task_.view();
        if(after.phase!=before.phase||after.actionIndex!=before.actionIndex)++revision_;
        if(after.phase!=Phase::Cues){invalidateClock();++pass_;}
        error_.clear();return true;
    }catch(const std::exception& e){error_=e.what();return false;}
}
void ManualTaskAdapter::invalidateForNavigationImpl(){
    const auto token=capture(IntentKind::Reopen);const auto before=task_.view();
    invalidateClock();++pass_;++revision_;
    if(task_.view().phase!=Phase::Closed&&task_.view().phase!=Phase::Release){
        try{task_.reopen();}catch(...){}
    }
    history_.push_back({token,json::Value::Object{},before,task_.view(),task_.diagnosis(),false,false});
}
bool ManualTaskAdapter::fenceInactiveForNavigationImpl(){
    const auto before=task_.view();
    if(before.phase!=Phase::Choose&&before.phase!=Phase::Closed)return false;
    const auto token=capture(IntentKind::Reopen);
    invalidateClock();++pass_;++revision_;
    history_.push_back({token,json::Value::Object{},before,task_.view(),task_.diagnosis(),false,false});
    return true;
}
namespace {
using J=json::Value;using O=J::Object;using A=J::Array;
void draftNeed(bool b,const char*m){if(!b)throw Error("PRIVATE_MANUAL_DRAFT",m);}
J u(std::uint64_t n){return std::to_string(n);}
std::uint64_t un(const J&v){draftNeed(v.isString(),"unsigned coordinate type");std::uint64_t n{};const auto&s=v.string();const auto r=std::from_chars(s.data(),s.data()+s.size(),n);draftNeed(r.ec==std::errc{}&&r.ptr==s.data()+s.size()&&std::to_string(n)==s,"unsigned coordinate value");return n;}
J i(std::int64_t n){return J::fromInteger(n);}
std::int64_t in(const J&v){std::int64_t n{};draftNeed(v.integer(n),"integer required");return n;}
void shape(const J&v,std::initializer_list<const char*>keys){draftNeed(v.isObject()&&v.object().size()==keys.size(),"exact object shape");for(auto k:keys)draftNeed(v.find(k),"missing field");}
J rat(const Rational&r){return O{{"n",i(r.numerator())},{"d",i(r.denominator())}};}
J own(const scheduler::Owner&o){A id;for(auto b:o.id)id.emplace_back(i(b));return O{{"id",id},{"generation",u(o.generation)},{"epoch",u(o.epoch)}};}
scheduler::Owner readOwner(const J&v){shape(v,{"id","generation","epoch"});scheduler::Owner o;const auto&a=v.object().at("id");draftNeed(a.isArray()&&a.array().size()==16,"owner bytes");for(std::size_t n=0;n<16;++n){const auto b=in(a.array()[n]);draftNeed(b>=0&&b<=255,"owner byte range");o.id[n]=static_cast<std::uint8_t>(b);}o.generation=un(v.object().at("generation"));o.epoch=un(v.object().at("epoch"));return o;}
J draftView(const View&v){return O{{"mode",i(static_cast<int>(v.mode))},{"phase",i(static_cast<int>(v.phase))},{"outcome",i(static_cast<int>(v.outcome))},{"bpm",v.selectedBpm?i(*v.selectedBpm):J()},{"action",v.actionIndex?u(*v.actionIndex):J()},{"release",v.needsManualRelease},{"setup",v.requiresSetup}};}
J source(const Definition&d){A setup,context,actions;for(auto&s:d.setupInstructions())setup.emplace_back(s);for(auto&s:d.retainedSourceContext())context.emplace_back(s);for(auto&a:d.actions()){A cs;for(auto&c:a.contacts)cs.emplace_back(O{{"string",i(c.sourceString)},{"fret",i(c.fret)},{"midi",i(c.writtenStandardTuningMidi)}});actions.emplace_back(O{{"label",a.label},{"contacts",cs},{"onset",rat(a.authoredCueOnset)}});}J reports;if(d.reportContract()){const auto&r=*d.reportContract();reports=O{{"setup",r.setup},{"actions",A(r.actions.begin(),r.actions.end())},{"release",r.release}};}return O{{"key",d.sourceKey()},{"label",d.label()},{"policy",d.policySha256()},{"provenance",d.provenanceJson()},{"setup",setup},{"context",context},{"actions",actions},{"release",d.releaseInstruction()},{"pace",d.pacedChoiceExplanation()},{"cue_end",rat(d.cueEnd())},{"reports",reports}};}
json::Limits limits(){json::Limits l;l.bytes=64*1024*1024;l.depth=96;l.stringBytes=8*1024*1024;l.values=2000000;return l;}
}
bool ManualTaskAdapter::record(J command,const std::function<bool()>& action){
    try{
        draftNeed(journal_.size()<100000,"command capacity reached; current work retained");
        draftNeed(pass_!=std::numeric_limits<std::uint64_t>::max()&&revision_!=std::numeric_limits<std::uint64_t>::max(),"gesture counter exhausted");
        auto previous=task_;const auto pass=pass_,revision=revision_;const bool armed=clockArmed_,origin=originSet_;const auto owner=clockOwner_;const auto binding=clockBinding_,sequence=lastSequence_,frames=originFrames_;const auto rate=sampleRate_;const auto historySize=history_.size();journal_.reserve(journal_.size()+1);history_.reserve(historySize+1);
        auto rollback=[&]{task_=std::move(previous);pass_=pass;revision_=revision;clockArmed_=armed;originSet_=origin;clockOwner_=owner;clockBinding_=binding;lastSequence_=sequence;originFrames_=frames;sampleRate_=rate;history_.resize(historySize);};
        try{if(!action()){rollback();return false;}journal_.push_back(std::move(command));return true;}catch(...){rollback();throw;}
    }catch(const std::exception&e){error_=e.what();return false;}
}
bool ManualTaskAdapter::apply(const IntentToken&t,std::optional<int>bpm,TempoRange range,std::optional<J>report){return record(O{{"kind","apply"},{"intent",i(static_cast<int>(t.kind))},{"bpm",bpm?i(*bpm):J()},{"minimum",i(range.minimumBpm)},{"maximum",i(range.maximumBpm)},{"report",report?*report:J()}},[&]{return applyImpl(t,bpm,range,report);});}
bool ManualTaskAdapter::armClock(const scheduler::Owner&o,std::uint64_t binding,std::uint32_t rate){return record(O{{"kind","arm"},{"owner",own(o)},{"binding",u(binding)},{"rate",u(rate)}},[&]{return armClockImpl(o,binding,rate);});}
bool ManualTaskAdapter::progress(const platform::MetronomeProgress&p){
    // Only the actual fields consumed by this adapter are retained. This is not
    // a full audio receipt or physical-presentation claim.
    return record(O{{"kind","progress"},{"owner",own(p.owner)},{"binding",u(p.binding)},{"sequence",u(p.sequence)},{"phase",i(static_cast<int>(p.phase))},{"terminal",p.terminal},{"fault",p.fault},{"tempo",i(p.tempo.tempo)},{"accepted",u(p.clientAcceptedThrough)},{"total_frames",u(p.totalActiveFrames)}},[&]{return progressImpl(p);});
}
void ManualTaskAdapter::invalidateForNavigation(){(void)record(O{{"kind","navigate"}},[&]{invalidateForNavigationImpl();return true;});}
bool ManualTaskAdapter::fenceInactiveForNavigation(){return record(O{{"kind","fence"}},[&]{return fenceInactiveForNavigationImpl();});}
J ManualTaskAdapter::continuationBody()const{
    draftNeed(!clockArmed_,"resolve the actual bound clock before saving; no automatic restart");
    A history;for(const auto&e:history_)history.emplace_back(O{{"intent",i(static_cast<int>(e.token.kind))},{"pass",u(e.token.pass)},{"revision",u(e.token.revision)},{"reported",e.reported},{"before",draftView(e.before)},{"after",draftView(e.after)},{"diagnosis",e.diagnosis?*e.diagnosis:J()},{"observed",false},{"credit",false}});
    return O{{"format","fathom-manual-pulse-private-v1"},{"source",content::sha256(json::stringify(source(definition())))},{"journal",journal_},{"history",history},{"state",O{{"view",draftView(task_.view())},{"pass",u(pass_)},{"revision",u(revision_)},{"pending_outcome",i(static_cast<int>(task_.pendingOutcome_))},{"last_cue",task_.lastCuePosition_?rat(*task_.lastCuePosition_):J()},{"acknowledged_all",task_.manuallyAcknowledgedAll_},{"diagnosis",task_.diagnosis_?*task_.diagnosis_:J()}}}};
}
std::string ManualTaskAdapter::continuation()const{const auto b=continuationBody();auto bytes=json::stringify(O{{"body",b},{"sha256",content::sha256(json::stringify(b))}});(void)json::parse(bytes,limits());return bytes;}
std::unique_ptr<ManualTaskAdapter> ManualTaskAdapter::restoreContinuation(const Definition&d,const std::string&bytes){
    const auto e=json::parse(bytes,limits());shape(e,{"body","sha256"});const auto&b=e.object().at("body");draftNeed(e.object().at("sha256")==J(content::sha256(json::stringify(b))),"checksum differs");shape(b,{"format","source","journal","history","state"});draftNeed(b.object().at("format")==J("fathom-manual-pulse-private-v1")&&b.object().at("source")==J(content::sha256(json::stringify(source(d)))),"source or format differs; original retained");const auto&j=b.object().at("journal");draftNeed(j.isArray()&&j.array().size()<=100000,"command limit");auto out=std::make_unique<ManualTaskAdapter>(d);const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(10);
    for(const auto&c:j.array()){
        draftNeed(std::chrono::steady_clock::now()<end,"replay deadline");const auto&o=c.object();const auto kind=o.at("kind").string();bool ok=false;
        if(kind=="apply"){shape(c,{"kind","intent","bpm","minimum","maximum","report"});const auto n=in(o.at("intent"));draftNeed(n>=0&&n<=static_cast<int>(IntentKind::Unknown),"intent range");auto asInt=[](const J&v){const auto n=in(v);draftNeed(n>=std::numeric_limits<int>::min()&&n<=std::numeric_limits<int>::max(),"integer range");return static_cast<int>(n);};std::optional<int>bpm;if(!o.at("bpm").null())bpm=asInt(o.at("bpm"));std::optional<J>report;if(!o.at("report").null())report=o.at("report");ok=out->apply(out->capture(static_cast<IntentKind>(n)),bpm,{asInt(o.at("minimum")),asInt(o.at("maximum"))},report);}
        else if(kind=="arm"){shape(c,{"kind","owner","binding","rate"});const auto rate=un(o.at("rate"));draftNeed(rate<=std::numeric_limits<std::uint32_t>::max(),"sample rate range");ok=out->armClock(readOwner(o.at("owner")),un(o.at("binding")),static_cast<std::uint32_t>(rate));}
        else if(kind=="progress"){shape(c,{"kind","owner","binding","sequence","phase","terminal","fault","tempo","accepted","total_frames"});platform::MetronomeProgress p;p.owner=readOwner(o.at("owner"));p.binding=un(o.at("binding"));p.sequence=un(o.at("sequence"));const auto phase=in(o.at("phase"));draftNeed(phase>=0&&phase<=static_cast<int>(metronome::Phase::Terminal),"clock phase range");p.phase=static_cast<metronome::Phase>(phase);p.terminal=o.at("terminal").boolean();p.fault=o.at("fault").boolean();const auto tempo=in(o.at("tempo"));draftNeed(tempo>=std::numeric_limits<int>::min()&&tempo<=std::numeric_limits<int>::max(),"tempo range");p.tempo.tempo=static_cast<int>(tempo);p.clientAcceptedThrough=un(o.at("accepted"));p.totalActiveFrames=un(o.at("total_frames"));ok=out->progress(p);}
        else if(kind=="fence"){shape(c,{"kind"});ok=out->fenceInactiveForNavigation();}
        else if(kind=="navigate"){shape(c,{"kind"});const auto before=out->journal_.size();out->invalidateForNavigation();ok=out->journal_.size()==before+1;}
        draftNeed(ok,"legal native replay refused");
    }
    draftNeed(!out->clockArmed_&&out->continuationBody()==b,"native replay differs or clock still bound");return out;
}

}
