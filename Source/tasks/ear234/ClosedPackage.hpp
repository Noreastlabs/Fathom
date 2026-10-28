#pragma once
#include "Ear234.hpp"
#include <string>
#include <vector>
namespace fathom::tasks::ear234::package {
// Host loads bytes. The package validates exact compiled byte authorities before
// constructing any Definition; it grants no learner/source-player permission.
class ClosedPackage final {
public:
    static ClosedPackage load(const std::string& exactPackageBytes,
                              const std::string& exactSourceIndexBytes);
    const Definition& lookup(const std::string& exactKey,
                             const std::string& exactSourceIdentity)const;
    std::string learnerInstruction(const std::string& exactKey,
                                   const std::string& exactSourceIdentity)const;
    const std::vector<std::string>& exactKeys()const noexcept{return keys_;}
    const json::Value& authority()const noexcept{return authority_;}
private:
    explicit ClosedPackage(json::Value);
    json::Value authority_;
    std::vector<std::string> keys_;
};
}
