#pragma once
#include "ProfileStore.hpp"
#include "storage/ProfileNaming.hpp"
#include "content/Canonical.hpp"
#include "platform/ProfileAccessMac.hpp"
#include <limits>

namespace fathom::storage::manual_drafts {
// PRIVATE continuation storage, not a learner export or performance receipt.
// All methods block on the Store writer: run on a retained background worker,
// never the UI thread or the Store writer itself. Keep the Store/lease alive
// until the operation returns.
// Chunks are immutable; the revision-checked manifest is published last. A
// partial publication leaves the prior manifest intact. No schema migration,
// automatic deletion, original replacement, or task action occurs here.
constexpr std::size_t chunkBytes=256*1024, maxBytes=64*1024*1024;
inline const std::string chunkPrefix="manual-continuation-chunk-v1/";
inline const std::string draftPrefix="manual-continuation-draft-v1/";
inline bool ownsKey(const std::string& k){return k.rfind(chunkPrefix,0)==0||k.rfind(draftPrefix,0)==0;}
inline void require(bool b,const char* m){if(!b)throw std::invalid_argument(m);}
inline bool digest(const std::string& s){return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;}
inline std::int64_t integer(const Value& v){std::int64_t n;require(v.integer(n),"draft integer");return n;}
inline std::string hex(const std::string& s){constexpr char d[]="0123456789abcdef";std::string r;r.reserve(s.size()*2);for(unsigned char c:s){r+=d[c>>4];r+=d[c&15];}return r;}
inline std::string unhex(const std::string& s){require(s.size()%2==0&&s.find_first_not_of("0123456789abcdef")==std::string::npos,"draft chunk encoding");std::string r;r.reserve(s.size()/2);auto n=[](char c){return c<='9'?c-'0':c-'a'+10;};for(std::size_t i=0;i<s.size();i+=2)r+=static_cast<char>((n(s[i])<<4)|n(s[i+1]));return r;}
inline bool preferenceValidator(const std::string& key,std::int64_t version,const Value& v) noexcept {
 try{
  require(version==1&&v.isObject(),"draft namespace/version");const auto& o=v.object();
  if(key.rfind(chunkPrefix,0)==0){
   require(o.size()==3&&o.at("format").string()=="manual-continuation-chunk-v1","chunk shape");
   const auto h=o.at("sha256").string(),encoded=o.at("hex").string();
   require(digest(h)&&key==chunkPrefix+h&&encoded.size()<=2*chunkBytes&&!encoded.empty(),"chunk bounds/key");
   require(content::sha256(unhex(encoded))==h,"chunk digest");return true;
  }
  require(key.rfind(draftPrefix,0)==0&&(o.size()==9||(o.size()==10&&o.count("profile_name")&&profile_names::normalize(o.at("profile_name").string())==o.at("profile_name").string()))&&o.at("format").string()=="manual-continuation-draft-v1","manifest shape");
  validateUuid(o.at("profile_id").string());validateUuid(o.at("draft_id").string());
  require(key==draftPrefix+o.at("draft_id").string(),"draft key identity");
  const auto source=o.at("source_key").string();require(!source.empty()&&source.size()<=2048,"draft source key");
  require(digest(o.at("source_contract_sha256").string())&&digest(o.at("payload_sha256").string()),"draft digests");
  const auto size=integer(o.at("payload_bytes")),mark=integer(o.at("watermark"));
  require(size>0&&size<=static_cast<std::int64_t>(maxBytes)&&mark>=0,"draft size/watermark");
  const auto& chunks=o.at("chunks").array();require(chunks.size()==(static_cast<std::size_t>(size)+chunkBytes-1)/chunkBytes,"draft chunk count");
  for(const auto& c:chunks)require(c.isString()&&digest(c.string()),"draft chunk reference");return true;
 }catch(...){return false;}
}
struct Loaded {
 Reply receipt;
 std::string payload,sourceKey,sourceContract;
 std::int64_t revision=0,watermark=0;
};
class Publication final {
 friend class Repository;
 std::string profile_,draft_,manifest_,operation_;
 std::vector<std::pair<std::string,std::string>> chunks_; // digest, canonical chunk
 std::vector<std::string> operations_;
 std::int64_t expected_=0;
 bool unknown_=false;
 public:
 const std::string& operationId()const{return operation_;}
 const std::string& manifestBytes()const{return manifest_;}
 bool unresolved()const{return unknown_;}
};
class Repository final {
 static Reply reply(Status s,const Publication& p,const char* code){return {s,p.operation_,draftPrefix+p.draft_,code,"",nullptr};}
 static Reply binding(ProfileStore& store,const std::string& profile){auto r=store.readProfileIdentity(newUuid()).get();if(r.status!=Status::Confirmed)return r;if(r.data.object().at("profile_id").string()!=profile)return {Status::Conflict,r.operation,profile,"DRAFT_PROFILE_MISMATCH","Private draft belongs to another profile",nullptr};return r;}
 static std::int64_t revision(const Reply& r){return integer(r.data.object().at("revision"));}
 static bool exact(const Reply& r,const std::string& bytes){return r.status==Status::Confirmed&&r.data.object().at("applicable").boolean()&&r.data.object().at("bytes").string()==bytes;}
 public:
 // Callers must first validate the actual continuation with its source-specific
 // codec. This repository proves private byte custody, not task truth/acceptance.
 static Publication prepare(std::string profile,std::string draft,std::string source,std::string sourceContract,const std::string& payload,std::int64_t watermark,std::int64_t expectedRevision){
  validateUuid(profile);validateUuid(draft);require(!payload.empty()&&payload.size()<=maxBytes,"draft payload bounds");
  require(expectedRevision>=0&&expectedRevision<std::numeric_limits<std::int64_t>::max(),"draft revision bounds");
  Publication p;p.profile_=std::move(profile);p.draft_=std::move(draft);p.expected_=expectedRevision;p.operation_=newUuid();Value::Array references;
  for(std::size_t i=0;i<payload.size();i+=chunkBytes){const auto bytes=payload.substr(i,chunkBytes),h=content::sha256(bytes);references.emplace_back(h);p.chunks_.emplace_back(h,canonical(Value::Object{{"format","manual-continuation-chunk-v1"},{"sha256",h},{"hex",hex(bytes)}}));p.operations_.push_back(newUuid());}
  const Value manifest=Value::Object{{"format","manual-continuation-draft-v1"},{"profile_id",p.profile_},{"draft_id",p.draft_},{"source_key",std::move(source)},{"source_contract_sha256",std::move(sourceContract)},{"payload_sha256",content::sha256(payload)},{"payload_bytes",Value::fromInteger(payload.size())},{"watermark",Value::fromInteger(watermark)},{"chunks",std::move(references)}};
  require(preferenceValidator(draftPrefix+p.draft_,1,manifest),"invalid private draft manifest");p.manifest_=canonical(manifest);return p;
 }
 // No automatic retry after unknown COMMIT/acknowledgment. Reconcile using the
 // SAME Publication and a safely reopened original Store before another write.
 static Reply publish(ProfileStore& store,Publication& p,bool stoppedAndResolved){
  if(p.unknown_)return reply(Status::Unresolved,p,"DRAFT_RECONCILE_REQUIRED");
  if(!stoppedAndResolved)return reply(Status::Busy,p,"DRAFT_STOP_REQUIRED");
  auto b=binding(store,p.profile_);if(b.status!=Status::Confirmed)return b;
  if(const auto* name=b.data.find("profile_name")){auto manifest=parseCanonical(p.manifest_);if(const auto* old=manifest.find("profile_name")){if(*old!=*name)return reply(Status::Conflict,p,"DRAFT_PROFILE_NAME_CONFLICT");}else{manifest.object()["profile_name"]=*name;require(preferenceValidator(draftPrefix+p.draft_,1,manifest),"invalid named draft manifest");p.manifest_=canonical(manifest);}}
  auto old=store.readPreferences(newUuid(),draftPrefix+p.draft_).get();
  if(exact(old,p.manifest_)&&revision(old)==p.expected_+1)return reply(Status::Confirmed,p,"DRAFT_VALUE_CONFIRMED");
  if(old.status!=Status::Confirmed&&old.status!=Status::DefinitelyAbsent)return old;
  if(old.status==Status::Confirmed&&!old.data.object().at("applicable").boolean())return reply(Status::Unsupported,p,"DRAFT_PRESERVED_UNAVAILABLE");
  if((old.status==Status::DefinitelyAbsent&&p.expected_!=0)||(old.status==Status::Confirmed&&revision(old)!=p.expected_))return reply(Status::Conflict,p,"DRAFT_STALE_REVISION");
  for(std::size_t i=0;i<p.chunks_.size();++i){const auto& chunk=p.chunks_[i];const auto key=chunkPrefix+chunk.first;auto r=store.readPreferences(newUuid(),key).get();
   if(exact(r,chunk.second)&&revision(r)==1)continue;
   if(r.status!=Status::DefinitelyAbsent)return r.status==Status::Confirmed?reply(Status::Conflict,p,"DRAFT_IMMUTABLE_CHUNK_CONFLICT"):r;
   r=store.compareExchangePreferences(p.operations_[i],key,1,0,chunk.second,true).get();
   if(r.status!=Status::Confirmed){if(r.status==Status::Unresolved)p.unknown_=true;return r;}
  }
  auto r=store.compareExchangePreferences(p.operation_,draftPrefix+p.draft_,1,p.expected_,p.manifest_,true).get();if(r.status==Status::Unresolved)p.unknown_=true;return r;
 }
 // Confirmation means the exact desired value is durably present at the
 // expected next revision, not proof of which original operation installed it.
 static Reply reconcile(ProfileStore& store,Publication& p){
  auto b=binding(store,p.profile_);if(b.status!=Status::Confirmed)return b;
  auto r=store.readPreferences(newUuid(),draftPrefix+p.draft_).get();
  if(exact(r,p.manifest_)&&revision(r)==p.expected_+1){p.unknown_=false;return reply(Status::Confirmed,p,"DRAFT_VALUE_CONFIRMED");}
  if((r.status==Status::DefinitelyAbsent&&p.expected_==0)||(r.status==Status::Confirmed&&revision(r)==p.expected_)){p.unknown_=false;return reply(Status::DefinitelyAbsent,p,"DRAFT_MANIFEST_NOT_PUBLISHED");}
  if(r.status!=Status::Confirmed&&r.status!=Status::DefinitelyAbsent)return r;
  return reply(Status::Conflict,p,"DRAFT_RECONCILIATION_CONFLICT");
 }
 // Key-only discovery retains unsupported drafts in the list; opening each
 // still requires its exact original binding and source-specific replay.
 static Reply list(ProfileStore& store,const std::string& profile,const std::string& afterDraft={},std::int64_t limit=64){
  validateUuid(profile);if(!afterDraft.empty())validateUuid(afterDraft);auto b=binding(store,profile);if(b.status!=Status::Confirmed)return b;
  return store.readPreferenceKeys(newUuid(),draftPrefix,afterDraft.empty()?"":draftPrefix+afterDraft,limit).get();
 }
 static Loaded load(ProfileStore& store,const std::string& profile,const std::string& draft){
  validateUuid(profile);validateUuid(draft);Loaded out;out.receipt=binding(store,profile);if(out.receipt.status!=Status::Confirmed)return out;
  out.receipt=store.readPreferences(newUuid(),draftPrefix+draft).get();if(out.receipt.status!=Status::Confirmed)return out;
  try{
   require(out.receipt.data.object().at("applicable").boolean(),"unsupported private draft");
   const auto v=parseCanonical(out.receipt.data.object().at("bytes").string());require(preferenceValidator(draftPrefix+draft,1,v),"invalid private draft");const auto& m=v.object();
   require(m.at("profile_id").string()==profile,"private draft profile mismatch");
   out.revision=revision(out.receipt);out.watermark=integer(m.at("watermark"));out.sourceKey=m.at("source_key").string();out.sourceContract=m.at("source_contract_sha256").string();const auto count=m.at("chunks").array().size();
   for(std::size_t i=0;i<count;++i){const auto h=m.at("chunks").array()[i].string();auto c=store.readPreferences(newUuid(),chunkPrefix+h).get();require(c.status==Status::Confirmed&&revision(c)==1&&c.data.object().at("applicable").boolean(),"missing/unsupported immutable draft chunk");auto chunk=parseCanonical(c.data.object().at("bytes").string());require(preferenceValidator(chunkPrefix+h,1,chunk),"invalid draft chunk");auto raw=unhex(chunk.object().at("hex").string());require(i+1==count||raw.size()==chunkBytes,"short nonfinal chunk");out.payload+=raw;}
   require(out.payload.size()==static_cast<std::size_t>(integer(m.at("payload_bytes")))&&content::sha256(out.payload)==m.at("payload_sha256").string(),"private draft payload digest");
   out.receipt.code="DRAFT_BYTES_LOADED_REPLAY_REQUIRED";return out;
  }catch(const std::exception& e){out.payload.clear();out.receipt.status=Status::Unsupported;out.receipt.code="DRAFT_PRESERVED_UNAVAILABLE";out.receipt.message=e.what();return out;}
 }
};
} // namespace fathom::storage::manual_drafts
