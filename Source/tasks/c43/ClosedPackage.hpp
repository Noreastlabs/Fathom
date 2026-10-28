#pragma once
#include "C43.hpp"
namespace fathom::tasks::c43::package {
class ClosedPackage final {
public:
 static ClosedPackage load(const std::string&exactPackageBytes,const std::string&exactIndexBytes);
 const Definition&lookup(const std::string&exactKey,const std::string&exactSourceIdentity)const;
 std::string learnerInstruction(const std::string&exactKey,const std::string&exactSourceIdentity)const;
 const json::Value&authority()const noexcept{return authority_;}
private:explicit ClosedPackage(json::Value);json::Value authority_;
};
}
