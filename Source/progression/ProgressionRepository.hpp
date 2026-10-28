#pragma once
#include "progression/ProgressionAdapter.hpp"
#include <optional>

namespace fathom::progression {
// One off-audio, caller-polled operation. Returned data is explicitly bound to
// its original snapshot, not relabelled as the latest history after later writes.
class ProgressionRepository final {
public:
    ProgressionRepository(storage::ProfileStore&,std::vector<Query>,std::string asOf,
                          std::string operation,std::string cacheKey="progress-current");
    void poll();
    bool finished()const noexcept{return phase_==Phase::Finished;}
    const storage::Reply& reply()const noexcept{return reply_;}
    const Value& snapshotView()const noexcept{return view_;}
private:
    enum class Phase { Snapshot, CacheRead, CacheWrite, Finished };
    storage::ProfileStore& store_;
    std::vector<Query> queries_;
    std::string asOf_,operation_,cacheKey_,bytes_,contentHash_;
    Phase phase_=Phase::Snapshot;
    std::optional<storage::ProfileStore::Future> future_;
    storage::Reply reply_;
    Value view_;
    void finish(storage::Status,const std::string& code,const std::string& message);
};
} // namespace fathom::progression
