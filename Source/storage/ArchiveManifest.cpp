#include "storage/ArchiveManifest.hpp"
#include "storage/ProfileNaming.hpp"
#include "platform/ProfileAccessMac.hpp"
#include <regex>
#include <set>

namespace fathom::storage {
namespace {
using O=Value::Object;
using A=Value::Array;
void require(bool ok,const std::string& message){
    if(!ok)throw EnvelopeError("ARCHIVE_MANIFEST_INVALID",message);
}
void capacity(bool ok){
    if(!ok)throw EnvelopeError("ARCHIVE_MANIFEST_CAPACITY","The complete archive manifest exceeds64KiB; no references or history were discarded. Snapshot stage remains incomplete.");
}
const Value& field(const Value& v,const std::string& key){
    auto p=v.find(key);require(p!=nullptr,"Missing archive projection field: "+key);return *p;
}
std::string text(const Value& v){require(v.isString(),"Archive projection text required");return v.string();}
std::int64_t integer(const Value& v){std::int64_t n;require(v.integer(n)&&n>=0,"Archive projection nonnegative integer required");return n;}
Value num(std::int64_t n){return Value::fromInteger(n);}
void digest(const std::string& s){require(std::regex_match(s,std::regex("[0-9a-f]{64}")),"Archive projection SHA256 required");}
void item(const std::string& s){require(std::regex_match(s,std::regex("fg:item:[0-9]{6}")),"Canonical item identity required");}
bool earlier(const std::string& a,const std::string& b){
    if(utcBefore(a,b))return true;
    if(utcBefore(b,a))return false;
    return a<b;
}
}
ArchiveManifestBuilder::ArchiveManifestBuilder(const std::string& profile,std::int64_t marker,
        const std::string& schemaSha,const std::string& authoritySha,const Value& counts,std::int64_t dataSchema){
    require(dataSchema==1||dataSchema==2,"Unsupported archive data schema");dataSchema_=dataSchema;
    validateUuid(profile);require(marker>=0,"Archive marker must be nonnegative");digest(schemaSha);digest(authoritySha);
    require(counts.isObject(),"Verified row counts required");
    for(const auto& pair:counts.object())integer(pair.second);
    summary_=O{{"profile_id",profile},{"marker",num(marker)},{"schema_sha256",schemaSha},
        {"authority_sha256",authoritySha},{"authoritative_row_counts",counts},
        {"results",num(integer(field(counts,"finalized")))},{"sessions",num(integer(field(counts,"session")))},
        {"attestations",num(integer(field(counts,"source_attestation")))},
        {"rule_observations",num(integer(field(counts,"rule_observation")))},
        {"count_meaning","Record counts; source attestations are facts, not distinct performances"},
        {"recorded_range_meaning","Recorded result/source-work timestamps, including zero-active results; not proven active-practice coverage"},
        {"content_compatibility","NOT ASSESSED: preserve missing identities; compare available accepted content before applying"}};
}
void ArchiveManifestBuilder::setProfileName(const std::string& name){summary_["profile_name"]=profile_names::normalize(name);}
void ArchiveManifestBuilder::addReference(Value value){
    auto bytes=canonical(value);
    if(references_.count(bytes))return;
    capacity(bytes.size()<=maxBytes-referenceBytes_);
    referenceBytes_+=bytes.size();references_.emplace(std::move(bytes),std::move(value));
}
void ArchiveManifestBuilder::addContext(const Value& context){
    require(context.isObject(),"Verified historical context required");
    O reference{{"reference_kind","versioned_content"}};
    for(const char* key:{"item_id","variant_id","content_revision","content_version","source_manifest_sha256","source_refs"})
        reference.emplace(key,field(context,key));
    item(text(reference.at("item_id")));
    require(std::regex_match(text(reference.at("variant_id")),std::regex("fg:variant:[0-9]{6}")),"Canonical variant identity required");
    require(integer(reference.at("content_revision"))>0&&!text(reference.at("content_version")).empty(),"Historical version required");
    digest(text(reference.at("source_manifest_sha256")));
    auto& sources=reference.at("source_refs");require(sources.isArray()&&!sources.array().empty(),"Source provenance required");
    std::set<std::string> seen;
    for(const auto& source:sources.array()){auto s=text(source);require(!s.empty()&&seen.insert(s).second,"Unique source references required");}
    addReference(std::move(reference));
}
void ArchiveManifestBuilder::addAcknowledgment(const std::string& id,std::int64_t revision){
    item(id);require(revision>0,"Acknowledgment revision required");
    addReference(O{{"reference_kind","item_revision_only"},{"item_id",id},{"content_revision",num(revision)},
        {"metadata_status","variant/version/provenance unavailable in original acknowledgment; never filled from current content"}});
}
void ArchiveManifestBuilder::addRecordedTime(const std::string& utc){
    validateUtc(utc);
    if(!first_||earlier(utc,*first_))first_=utc;
    if(!last_||earlier(*last_,utc))last_=utc;
}
Value ArchiveManifestBuilder::manifest(std::int64_t bytes,const std::string& sha) const{
    require(bytes>0&&bytes<=16LL*1024*1024*1024,"Archive profile size outside accepted capacity");digest(sha);
    auto summary=summary_;A refs;for(const auto& pair:references_)refs.push_back(pair.second);
    summary.emplace("content_references",std::move(refs));
    summary.emplace("practice_range_utc",O{{"first",first_?Value(*first_):Value(nullptr)},{"last",last_?Value(*last_):Value(nullptr)}});
    Value out=O{{"format","Fathom.ProfileArchive"},{"archive_version",num(1)},{"data_schema_version",num(dataSchema_)},
                {"snapshot",std::move(summary)},{"profile_bytes",num(bytes)},{"profile_sha256",sha}};
    capacity(canonical(out).size()<=maxBytes);return out;
}
} // namespace fathom::storage
