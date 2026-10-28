#include "progression/ProgressionRepository.hpp"

namespace fathom::progression {
namespace {
const Value& f(const Value& v,const std::string& key){auto p=v.find(key);if(!p)throw HistoryError("Missing "+key);return *p;}
std::string text(const Value& v){if(!v.isString())throw HistoryError("Expected text");return v.string();}
}
ProgressionRepository::ProgressionRepository(storage::ProfileStore& store,std::vector<Query> queries,std::string at,std::string operation,std::string key)
    :store_(store),queries_(std::move(queries)),asOf_(std::move(at)),operation_(std::move(operation)),cacheKey_(std::move(key)){
    if(operation_.empty()||cacheKey_.empty())throw HistoryError("Projection operation/cache key required");
    utcMicros(asOf_);future_.emplace(store_.snapshot(operation_+"/snapshot"));
    reply_={storage::Status::Unresolved,operation_,cacheKey_,"IN_PROGRESS","Original projection operation pending",nullptr};
}
void ProgressionRepository::finish(storage::Status status,const std::string& code,const std::string& message){reply_={status,operation_,cacheKey_,code,message,view_};phase_=Phase::Finished;future_.reset();}
void ProgressionRepository::poll(){
    if(finished()||!future_||future_->wait_for(std::chrono::seconds(0))!=std::future_status::ready)return;
    try{auto result=future_->get();future_.reset();
        if(phase_==Phase::Snapshot){if(result.status!=storage::Status::Confirmed){finish(result.status,result.code,result.message);return;}auto snapshot=adaptSnapshot(result);view_=projectSnapshot(snapshot,queries_,asOf_);bytes_=storage::canonical(view_);contentHash_=text(f(view_,"selection_sha256"));future_.emplace(store_.readCache(operation_+"/cache-read",cacheKey_,contentHash_,text(*initialRules().find("version")),asOf_));phase_=Phase::CacheRead;return;}
        if(phase_==Phase::CacheRead){
            if(result.status==storage::Status::Confirmed&&text(f(result.data,"bytes"))==bytes_){finish(storage::Status::Confirmed,"CACHE_VERIFIED","Cache equals clean recomputation for this original snapshot");return;}
            if(result.status!=storage::Status::Confirmed&&result.status!=storage::Status::DefinitelyAbsent){finish(result.status,result.code,result.message);return;}
            std::int64_t marker;if(!f(view_,"evidence_marker").integer(marker))throw HistoryError("Invalid original snapshot marker");future_.emplace(store_.writeCache(operation_+"/cache-write",cacheKey_,marker,text(f(view_,"evidence_sha256")),contentHash_,text(*initialRules().find("version")),asOf_,bytes_));phase_=Phase::CacheWrite;return;
        }
        if(result.status==storage::Status::Confirmed)finish(storage::Status::Confirmed,"CACHE_RECOMPUTED","Disposable cache replaced with this clean snapshot projection");
        else if(result.status==storage::Status::Conflict)finish(storage::Status::Confirmed,"SNAPSHOT_UNCACHED","History changed before cache write; original coherent snapshot retained, explicit refresh available");
        else finish(result.status,result.code,result.message);
    }catch(const std::exception& e){finish(storage::Status::DefiniteFailure,"PROJECTION_ERROR",e.what());}
}
} // namespace fathom::progression
