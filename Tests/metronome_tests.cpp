#include "metronome/MetronomePreferences.hpp"
#include "storage/StorageEnvelope.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <set>

using namespace fathom;using namespace fathom::metronome;
namespace {
using V=json::Value;using A=V::Array;using O=V::Object;A checks;int failures=0;
std::string read(const std::string& p){std::ifstream f(p);if(!f)throw std::runtime_error("Input unavailable");return {std::istreambuf_iterator<char>(f),{}};}
void check(std::string name,bool pass){checks.push_back(O{{"case",name},{"passed",pass}});if(!pass)++failures;std::cout<<(pass?"PASS ":"FAIL ")<<name<<'\n';}
template<class F>void rejects(const std::string& name,F f){bool rejected=false;try{f();}catch(const std::exception&){rejected=true;}check(name,rejected);}
int integer(const V& v){std::int64_t i;if(!v.integer(i))throw std::runtime_error("Expected integer");return static_cast<int>(i);}
V num(std::int64_t n){return V::fromInteger(n);}
scheduler::Owner owner(){scheduler::Owner o;o.id[6]=0x40;o.id[8]=0x80;o.id[15]=1;o.generation=1;o.epoch=1;return o;}
struct Timeline {
    TempoPolicy* policy{};const PlanBank* bank{};std::vector<scheduler::Fact> facts;std::vector<int> tempos;
    static bool collect(void* p,const scheduler::Fact& f)noexcept {auto& t=*static_cast<Timeline*>(p);t.facts.push_back(f);return true;}
    static scheduler::BoundaryDecision boundary(void* p,const scheduler::Fact& f)noexcept {
        auto& t=*static_cast<Timeline*>(p);auto d=t.policy->boundary(f.owner,f.binding,f.cycle,true,true,Intent::Continue);t.tempos.push_back(d.tempo);
        if(f.cycle==4)return {scheduler::BoundaryAction::Stop,nullptr};
        return d.nextAttack?scheduler::BoundaryDecision{scheduler::BoundaryAction::Tempo,t.bank->tempo(d.tempo)}:scheduler::BoundaryDecision{scheduler::BoundaryAction::Stop,nullptr};
    }
};
}
int main(int argc,char** argv){
    try{
        if(argc!=4||std::filesystem::exists(argv[1]))throw std::runtime_error("New output JSON, accepted config and frozen oracle paths required");
        const auto config=json::parse(read(argv[2])),oracle=json::parse(read(argv[3]));Settings base;
        check("C++ defaults exactly equal accepted F3 configuration",encodeSettings(base)==*config.find("freeplay_default"));
        check("eight common meters exact",commonMeters()==std::array<std::pair<int,int>,8>{{{2,4},{3,4},{4,4},{5,4},{6,8},{7,8},{9,8},{12,8}}});
        std::size_t compared=0;bool correct=true;
        for(const auto& item:oracle.find("cases")->array()){
            auto settings=encodeSettings(base);for(auto key:{"meter","subdivision","styles"})settings.object()[key]=*item.find(key);auto decoded=decodeSettings(settings);const auto actual=events(decoded);const auto& expected=item.find("events")->array();correct &= actual.size()==expected.size();
            for(std::size_t i=0;i<actual.size()&&i<expected.size();++i){const auto& a=actual[i];const auto& b=expected[i].array();correct &= a.at==Rational{integer(b[0]),integer(b[1])} && (a.style==Style::Accent?"accent":"normal")==b[2].string();++compared;}
        }
        check("448 source-contract meter/subdivision oracles match exact events",correct&&oracle.find("cases")->array().size()==448);
        for(auto [key,value]:std::vector<std::pair<std::string,V>>{{"tempo",num(19)},{"tempo",num(301)},{"tempo",true},{"tempo",json::Number{"60.0"}},{"subdivision",num(8)},{"master_volume",num(-1)},{"x",num(0)},{"y",num(17)},{"beat_unit_q",A{num(2),num(2)}},{"meter",A{num(4),num(3)}},{"count_in","guess"},{"metronome_enabled",num(1)}}){auto v=encodeSettings(base);v.object()[key]=value;rejects("invalid field "+key+" "+json::stringify(value),[&]{decodeSettings(v);});}
        auto bad=encodeSettings(base);bad.object()["running"]=true;rejects("running state not a setting",[&]{decodeSettings(bad);});bad=encodeSettings(base);bad.object().erase("ramp");rejects("missing field is not defaulted",[&]{decodeSettings(bad);});
        auto silent=base;silent.styles.assign(4,Style::Silent);check("all-silent practice events empty, time remains one bar",events(silent).empty()&&barSpan(silent)==Rational{4});
        PlanBank silentBank(silent,owner(),1,"synthetic-silent",44100);check("explicit preparation count-in survives silent practice",silentBank.initial().countIn().size()==4&&silentBank.initial().events().empty());
        auto unsupported=base;unsupported.polyrhythmEnabled=true;rejects("poly config retained but not falsely compiled by standard tool",[&]{PlanBank bank(unsupported,owner(),1,"synthetic",44100);});check("full poly config roundtrip remains intact",encodeSettings(decodeSettings(encodeSettings(unsupported)))==encodeSettings(unsupported));unsupported=base;unsupported.countIn=CountIn::AuthoredBar;rejects("authored count-in requires actual source adapter",[&]{PlanBank bank(unsupported,owner(),1,"synthetic",44100);});
        auto worst=base;worst.numerator=16;worst.denominator=2;worst.subdivision=7;worst.styles.assign(16,Style::Accent);worst.tempo=20;worst.unit=scheduler::BeatUnit::Eighth;
        const auto started=std::chrono::steady_clock::now();PlanBank bank(worst,owner(),1,"synthetic-worst-bank",44100);const auto micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-started).count();
        bool compatible=true;for(int bpm=20;bpm<=300;++bpm){auto p=bank.tempo(bpm);scheduler::FrameRatio exact;compatible &= p&&bank.initial().compatibleTempo(*p)&&scheduler::samples(Rational{32},44100,static_cast<std::uint16_t>(bpm),scheduler::BeatUnit::Eighth,exact)&&p->duration().n==exact.n&&p->duration().d==exact.d;}
        check("all281 full-range stable intro-free tempo plans exact",compatible&&bank.retainedEventCount()==282*112+16&&bank.tempo(19)==nullptr&&bank.tempo(301)==nullptr);
        bool units=true;for(int i=0;i<4;++i){auto s=base;s.unit=static_cast<scheduler::BeatUnit>(i);s.countIn=CountIn::Off;PlanBank b(s,owner(),1,"synthetic-unit",48000);scheduler::FrameRatio duration;units &= scheduler::samples(Rational{4},48000,60,s.unit,duration)&&b.initial().duration().n==duration.n&&b.initial().duration().d==duration.d&&b.initial().countIn().empty();}check("all four BPM units and Off count-in preserve schedule",units);
        Tap tap;TapResult tr;for(std::uint64_t i=0;i<4;++i)tr=tap.add(i+1,i*500000000ULL);check("four taps propose120 without applying tempo",tr.status==TapStatus::Candidate&&tr.bpm==120);check("duplicate and nonincreasing taps refused",tap.add(4,2000000000).status==TapStatus::Rejected&&tap.add(5,1500000000).status==TapStatus::Rejected);tap.reset();check("Reset Tap retains sequence/time protection",tap.retained()==0&&tap.add(4,3000000000).status==TapStatus::Rejected);tr=tap.add(5,2000000000);check("reset requires new intervals",tr.status==TapStatus::Insufficient);
        Tap gaps;for(std::uint64_t i=0;i<4;++i)gaps.add(i+1,i*500000000ULL);gaps.add(5,5500000000ULL);check("exactly4s gap does not reset",gaps.retained()==5);gaps.add(6,9500000001ULL);check("greater than4s resets to one point",gaps.retained()==1);
        Tap outlier;std::uint64_t time=0;outlier.add(1,time);std::uint64_t seq=1;for(auto d:{500000000ULL,500000000ULL,1000000000ULL,500000000ULL,500000000ULL}){time+=d;tr=outlier.add(++seq,time);}check("supported outlier excluded with four inliers",tr.status==TapStatus::Candidate&&tr.bpm==120&&outlier.retained()==6);
        Tap unstable;time=0;unstable.add(1,time);seq=1;for(auto d:{200000000ULL,500000000ULL,3000000000ULL}){time+=d;tr=unstable.add(++seq,time);}check("unstable three intervals do not invent tempo",tr.status==TapStatus::Unstable);
        Tap half;for(std::uint64_t i=0;i<4;++i)tr=half.add(i+1,i*960000000ULL);check("62.5 BPM rounds half up to63",tr.status==TapStatus::Candidate&&tr.bpm==63);
        for(auto pair:{std::pair<std::uint64_t,int>{200000000,300},{3000000000,20}}){Tap edge;for(std::uint64_t i=0;i<4;++i)tr=edge.add(i+1,i*pair.first);check("tap supported endpoint "+std::to_string(pair.second),tr.status==TapStatus::Candidate&&tr.bpm==pair.second);}
        Settings ramp=base;ramp.ramp=Ramp{true,7,2,75};TempoPolicy policy(owner(),1,ramp);auto wrong=owner();wrong.generation=2;
        check("foreign generation and binding do not mutate",!policy.boundary(wrong,1,1,true,true,Intent::Continue).accepted&&!policy.boundary(owner(),2,1,true,true,Intent::Continue).accepted&&policy.handoff().completedThrough==0);
        check("partial boundary waits for same actual completed bar",!policy.boundary(owner(),1,1,true,false,Intent::Continue).nextAttack&&policy.handoff().count==0);
        check("first complete bar at60",policy.boundary(owner(),1,1,true,true,Intent::Continue).tempo==60);
        check("duplicate bar not credited",!policy.boundary(owner(),1,1,true,true,Intent::Continue).accepted);
        check("second bar steps67",policy.boundary(owner(),1,2,true,true,Intent::Continue).tempo==67);
        policy.boundary(owner(),1,3,true,true,Intent::Continue);check("repeat step74",policy.boundary(owner(),1,4,true,true,Intent::Continue).tempo==74);
        policy.boundary(owner(),1,5,true,true,Intent::Continue);auto atTarget=policy.boundary(owner(),1,6,true,true,Intent::Continue);check("target clamp75 remains running with rampOff",atTarget.nextAttack&&atTarget.tempo==75&&!policy.handoff().ramp);
        auto down=ramp;down.tempo=70;down.ramp=Ramp{false,7,1,60};TempoPolicy dp(owner(),1,down);check("down ramp63 then target60",dp.boundary(owner(),1,1,true,true,Intent::Continue).tempo==63&&dp.boundary(owner(),1,2,true,true,Intent::Continue).tempo==60&&!dp.handoff().ramp);
        TempoPolicy manual(owner(),1,ramp);check("manual rejected outsideRunning",!manual.manual(owner(),1,1,90,Phase::Paused)&&!manual.manual(owner(),1,1,90,Phase::CountIn));check("manual queues not immediate and disarms ramp",manual.manual(owner(),1,1,90,Phase::Running)&&manual.handoff().tempo==60&&!manual.handoff().ramp);check("stale manual cannot replace pending",!manual.manual(owner(),1,1,100,Phase::Running)&&manual.handoff().pendingManual==90);check("manual wins next continuing boundary",manual.boundary(owner(),1,1,true,true,Intent::Continue).tempo==90&&!manual.handoff().pendingManual);
        TempoPolicy paused(owner(),1,ramp);paused.boundary(owner(),1,1,true,true,Intent::Continue);auto stopped=paused.boundary(owner(),1,2,true,true,Intent::Pause);check("Pause suppresses due step preserving saturation",stopped.accepted&&!stopped.nextAttack&&paused.handoff().tempo==60&&paused.handoff().count==2&&paused.halted());TempoPolicy resume(owner(),wrong,1,paused.handoff());check("resumed partial does not trigger ramp",!resume.boundary(wrong,1,3,false,false,Intent::Continue).nextAttack&&resume.handoff().tempo==60);check("next confirmed resumed bar applies due step",resume.boundary(wrong,1,3,true,true,Intent::Continue).tempo==67);
        for(auto intent:{Intent::Stop,Intent::Context,Intent::Error}){TempoPolicy terminal(owner(),1,ramp);terminal.manual(owner(),1,1,100,Phase::Running);auto d=terminal.boundary(owner(),1,1,true,true,intent);check("terminal suppresses sound, retains original pending choice "+std::to_string(static_cast<int>(intent)),d.accepted&&!d.nextAttack&&terminal.handoff().pendingManual==100&&!terminal.handoff().ramp);rejects("terminal handoff cannot masquerade as Pause",[&]{TempoPolicy invalid(owner(),wrong,1,terminal.handoff());});}
        auto integrated=base;integrated.countIn=CountIn::Off;integrated.tempo=60;integrated.ramp=Ramp{true,10,1,80};PlanBank ib(integrated,owner(),1,"synthetic-integrated",8000);TempoPolicy ip(owner(),1,integrated);Timeline timeline{&ip,&ib,{},{}};timeline.facts.reserve(128);timeline.tempos.reserve(8);scheduler::Cursor cursor;check("shared cursor starts compiled initial plan",cursor.start(ib.initial(),owner(),1));for(int i=0;i<800 && cursor.snapshot().state!=scheduler::State::Terminal;++i)cursor.process(256,owner(),Timeline::collect,&timeline,Timeline::boundary,&timeline);
        check("four confirmed bars use repeated ramp on shared Cursor",cursor.snapshot().completedCycles==4&&timeline.tempos==std::vector<int>{70,80,80,80}&&cursor.snapshot().state==scheduler::State::Terminal);
        scheduler::FrameRatio position{},duration{};bool exact=true;std::size_t b=0;for(const auto& f:timeline.facts)if(f.kind==scheduler::FactKind::CycleCompleted){int bpm=b==0?60:b==1?70:80;scheduler::samples(Rational{4},8000,static_cast<std::uint16_t>(bpm),scheduler::BeatUnit::Quarter,duration);scheduler::add(position,duration,position);std::uint64_t expected;scheduler::round(position,expected);exact &= expected==f.frame;++b;}check("piecewise boundary frames use absolute exact arithmetic",exact&&b==4);
        A trace;for(const auto& f:timeline.facts)trace.push_back(O{{"kind",num(static_cast<int>(f.kind))},{"frame",num(static_cast<std::int64_t>(f.frame))},{"cycle",num(static_cast<std::int64_t>(f.cycle))},{"id",num(f.sourceEvent)}});
        std::ofstream out(argv[1]);out<<json::stringify(O{{"classification","synthetic software component; no native/audio/human claim"},{"checks",checks},{"failures",num(failures)},{"oracle_events_compared",num(static_cast<std::int64_t>(compared))},{"worst_case_bank",O{{"construction_microseconds",num(micros)},{"retained_events",num(static_cast<std::int64_t>(bank.retainedEventCount()))},{"timed_event_size_bytes",num(sizeof(scheduler::TimedEvent))},{"plan_bank_object_bytes",num(sizeof(PlanBank))},{"measurement_limit","single available-host construction observation; counts exclude allocator overhead; not qualification"}}},{"scheduler_trace",trace}})<<'\n';if(!out)throw std::runtime_error("Cannot retain results");return failures?1:0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
