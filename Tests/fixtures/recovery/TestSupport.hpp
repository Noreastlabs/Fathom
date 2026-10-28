#pragma once
#include "storage/Recovery.hpp"
#include "storage/CheckpointCoordinator.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "content/Canonical.hpp"
#include <fstream>
#include <thread>
#include <chrono>
namespace recovery_test {
using namespace fathom::storage;
namespace fs=std::filesystem;
using Object=Value::Object;using Array=Value::Array;
inline const Value& at(const Value& v,const std::string& k){return v.object().at(k);}
inline Value& at(Value& v,const std::string& k){return v.object().at(k);}
inline std::string str(const Value& v,const std::string& k){return at(v,k).string();}
inline std::int64_t n(const Value& v){std::int64_t x;if(!v.integer(x))throw std::runtime_error("integer fixture required");return x;}
inline Value num(std::int64_t x){return Value::fromInteger(x);}
inline std::string read(const fs::path& p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Cannot read "+p.string());return {std::istreambuf_iterator<char>(f),{}};}
inline void write(const fs::path& p,const std::string& s){std::ofstream f(p,std::ios::binary);f<<s;if(!f)throw std::runtime_error("Cannot write "+p.string());}
inline Value load(const fs::path& p){return parseCanonical(read(p));}
inline std::string hex(const std::string& s){std::string out;for(unsigned char c:s){out.push_back("0123456789abcdef"[c>>4]);out.push_back("0123456789abcdef"[c&15]);}return out;}
inline std::string unhex(const std::string& s){std::string out;for(std::size_t i=0;i<s.size();i+=2)out.push_back(static_cast<char>(std::stoi(s.substr(i,2),nullptr,16)));return out;}
inline std::int64_t steadyNs(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
inline fs::path oracle(const fs::path& e,const std::string& name){return e/"reviewer/resource_plan_inputs/recovery-fixtures-02"/name;}
inline Reply required(ProfileStore::Future f){auto r=f.get();if(r.status!=Status::Confirmed)throw std::runtime_error(r.code+": "+r.message);return r;}
inline Value rebindEnvelope(Value v,const std::string& owner,const Value& context){at(v,"owner")=owner;at(v,"context")=context;at(at(v,"result"),"key")=owner;return v;}
inline Value rebindCheckpoint(Value v,const std::string& owner,const Value& context){at(v,"owner")=owner;at(v,"context")=context;auto& q=at(v,"practice_snapshot");at(q,"attempt")=owner;
 if(!at(v,"sealed_envelope").null()){auto env=rebindEnvelope(parseCanonical(unhex(str(at(v,"sealed_envelope"),"bytes_hex"))),owner,context);auto bytes=canonical(env);at(v,"sealed_envelope")=Object{{"bytes_hex",hex(bytes)},{"sha256",fathom::content::sha256(bytes)}};at(q,"pending")=Object{{"key",owner},{"payload",canonical(at(env,"result"))},{"digest",fathom::content::sha256(canonical(at(env,"result")))}};}return v;}
inline StoreOptions options(const fs::path& p,bool create=true){StoreOptions o;o.path=p;o.create=create;o.createdUtc="2026-09-07T22:00:00Z";return o;}
inline RecoveryBinding allocate(ProfileStore& s,Value context,const std::string& kind){if(kind=="Attempt"){auto session=required(s.createSession(newUuid(),"2026-09-07T00:30:00Z","America/New_York"));at(context,"session_id")=session.owner;}auto r=required(s.allocate(newUuid(),kind,context,"2026-09-07T00:30:00Z"));RecoveryBinding b;b.owner=r.owner;b.kind=kind;b.context=std::move(context);return b;}
inline Reply checkpointReply(const Value& cp){return {Status::Confirmed,"synthetic-read",str(cp,"owner"),"","",Object{{"state","checkpoint"},{"payload",canonical(cp)},{"generation",at(at(cp,"practice_snapshot"),"generation")},{"sequence",at(cp,"sequence")},{"stopped_on_reopen",true}}};}
inline CheckpointSnapshot snap(const Value& cp){return {n(at(at(cp,"practice_snapshot"),"generation")),n(at(cp,"sequence")),canonical(cp)};}
inline void await(RecoveryOperation& op){for(int i=0;i<5000&&!op.poll();++i)std::this_thread::sleep_for(std::chrono::milliseconds(1));if(!op.finished())throw std::runtime_error("Recovery exceeded5s bound");}
inline void gate(CheckpointCoordinator& c,std::int64_t time=0){for(int i=0;i<2000;++i){c.poll(time);if(!c.state(time).inFlight)return;std::this_thread::sleep_for(std::chrono::milliseconds(1));}throw std::runtime_error("Checkpoint wait exceeded2s");}
inline void boundedPath(const fs::path& e,const fs::path& p){auto rel=fs::absolute(p).lexically_normal().lexically_relative(fs::canonical(e)/"test-data");if(rel.empty()||rel.is_absolute()||*rel.begin()=="..")throw std::runtime_error("Test path must be under explicit evidence/test-data");}
}
