#pragma once
#include "practice/PracticeSession.hpp"
#include "platform/ProfileAccessMac.hpp"
#include <filesystem>
#include <fstream>
#include <thread>
namespace capture_fixture {
using namespace fathom;using V=json::Value;using O=V::Object;using A=V::Array;
inline V n(std::int64_t x){return V::fromInteger(x);}inline V q(std::int64_t a,std::int64_t b=1){Rational r{a,b};return A{n(r.numerator()),n(r.denominator())};}
inline const V& at(const V& v,const char* k){return v.object().at(k);}
inline void write(const std::filesystem::path& p,const std::string& s){std::ofstream out(p,std::ios::binary);out<<s;out.close();if(!out)throw std::runtime_error("Evidence write failed");}
inline storage::Reply confirmed(storage::ProfileStore::Future f){auto r=f.get();if(r.status!=storage::Status::Confirmed)throw std::runtime_error(r.code+": "+r.message);return r;}
inline practice::Configuration config(){practice::Configuration c;c.rate=8000;c.bpm=120;c.span=Rational{4};c.meter={{4,4}};c.faithfulWholeSpan=true;c.targetCycles=2;return c;}
inline capture::StartRequest request(const std::string& session,bool freeplay=false){
    auto cfg=config();V configuration=O{{"values",capture::configurationValues(cfg)},{"synthetic_fixture",true},{"authored_tempo_ref",nullptr},{"beat_reference_q",q(1)}};
    V context=O{{"configuration_version",n(1)},{"configuration",configuration}};V hashes;
    if(!freeplay){
        hashes=O{{"synthetic-source",std::string(64,'b')}};const V span=O{{"start",q(0)},{"end",q(4)}};const V target=O{{"cycles",n(2)}};
        configuration.object()["source_hashes"]=hashes;
        configuration.object()["canonical_variant_id"]="fg:variant:000001";
        configuration.object()["progression_condition"]=O{{"variant","fg:variant:000001"},{"revision",n(1)},{"content_version","synthetic-capture.2"},
            {"setup","synthetic-standard"},{"span",span},{"beat_unit","quarter"},{"grouping","one-per-quarter"},{"technique","test-only"},{"target",target}};
        context=O{{"session_id",session},{"item_id","fg:item:000001"},{"variant_id","fg:variant:000001"},{"content_revision",n(1)},
            {"content_version","synthetic-capture.2"},{"source_manifest_sha256",std::string(64,'a')},{"source_refs",A{"synthetic-source"}},
            {"configuration_version",n(1)},{"configuration",configuration},{"span",span},{"target",target}};
    }
    return {{"",freeplay?"FreeplayActivity":"Attempt",context,hashes,"2026-09-08T04:00:00Z","America/New_York"},cfg,1};
}
inline practice::Progress progress(const practice::Coordinator& c,std::uint64_t frames,practice::State s,std::uint64_t seq=1){
    practice::Progress p;p.owner=c.owner();p.sequence=seq;p.clientAcceptedThrough=p.scheduledThrough=p.uncertainThrough=frames;
    scheduler::FrameRatio intro,cycle;std::uint64_t start{},cycleFrames{};
    scheduler::samples(practice::countInSpan(c.configuration()),c.configuration().rate,c.configuration().bpm,c.configuration().unit,intro);scheduler::round(intro,start);
    scheduler::samples(c.configuration().span,c.configuration().rate,c.configuration().bpm,c.configuration().unit,cycle);scheduler::round(cycle,cycleFrames);
    p.activeFrames=frames>start?frames-start:0;p.completedCycles=p.activeFrames/cycleFrames;p.cursorFrames=p.activeFrames%cycleFrames;
    p.state=s;p.terminal=s==practice::State::Paused||s==practice::State::Ended||s==practice::State::Error;p.fault=s==practice::State::Error;p.partial=p.cursorFrames!=0;p.requestedStopNs=p.terminal?987654321:0;return p;
}
inline std::int64_t now(){return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
template<class F>inline void until(capture::PracticeSession& s,F predicate){const auto end=now()+6000;while(!predicate()){if(now()>end)throw std::runtime_error("Declared six-second controller watchdog");s.poll(now(),"2026-09-08T04:00:30Z");std::this_thread::sleep_for(std::chrono::milliseconds(1));}}
}
