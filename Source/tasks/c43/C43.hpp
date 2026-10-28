#pragma once
#include "Ear234.hpp"
#include <cstdint>
#include <memory>
#include <string>
#include <vector>
namespace fathom::tasks::c43 {
class Definition final {
public:
 const std::string& sourceKey()const noexcept{return key_;}
 const std::string& group()const noexcept{return group_;}
 const json::Value& binding()const noexcept{return binding_;}
private:
 explicit Definition(json::Value);
 std::string key_,group_;json::Value binding_;
 friend const Definition& definition(const std::string&);
};
const Definition& definition(const std::string& exactKey);
const std::vector<std::string>& keys();
class Token final {
public:Token(const Token&)=default;
private:
 Token(std::uint64_t,std::uint64_t,std::string,std::string,bool);
 std::uint64_t instance_,revision_;std::string key_,action_;bool sourceRole_;
 friend class Owner;
};
struct RestoredOwner;
class Owner final {
public:
 explicit Owner(const Definition&);~Owner();
 Owner(const Owner&)=delete;Owner&operator=(const Owner&)=delete;
 Token capture(const std::string&)const;
 // Trusted actual source-player role only; never a learner form.
 Token captureSourceChoices(const std::string&)const;
 bool current(const Token&)const;
 void apply(const Token&,const json::Value& actualTypedReport);
 void attachContextCompletion(const Token&,std::shared_ptr<const ear234::Owner> actualContextOwner);
 json::Value learnerView()const;
 json::Value learnerActions()const;
 json::Value sourcePlayerView()const;
 std::vector<json::Value> history()const;
 bool fenceInactiveForNavigation();
 // Private profile data. Restore returns the same mutable dependency held by C43.
 std::string continuation()const;
 static RestoredOwner restoreContinuation(const Definition&,const std::string&,
     const ear234::Owner::ContinuationResolver& = {});
 const Definition& retainedDefinition()const noexcept;
private:struct Impl;std::unique_ptr<Impl>impl_;
};
struct RestoredOwner {std::unique_ptr<Owner> owner;std::shared_ptr<ear234::Owner> context;};
}
