#pragma once
#include "storage/StorageEnvelope.hpp"
#include <map>

namespace fathom::storage {
// A bounded projection of a verified completed candidate, never learner evidence.
class ArchiveManifestBuilder {
public:
    static constexpr std::size_t maxBytes=65536;
    ArchiveManifestBuilder(const std::string& profileId,std::int64_t marker,
                           const std::string& schemaSha,const std::string& authoritySha,
                           const Value& rowCounts,std::int64_t dataSchema=1);
    void addContext(const Value&);
    void addAcknowledgment(const std::string& itemId,std::int64_t revision);
    void setProfileName(const std::string&);
    void addRecordedTime(const std::string& utc);
    Value manifest(std::int64_t profileBytes,const std::string& profileSha) const;
private:
    std::int64_t dataSchema_=1;
    Value::Object summary_;
    std::map<std::string,Value> references_;
    std::size_t referenceBytes_=0;
    std::optional<std::string> first_,last_;
    void addReference(Value);
};
} // namespace fathom::storage
