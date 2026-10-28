#pragma once
#include "content/StrictJson.hpp"
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace fathom::tasks::ear234 {
class Definition final {
public:
    Definition(const Definition&)=default;
    const std::string& sourceKey()const noexcept{return key_;}
    const std::string& family()const noexcept{return family_;}
    const std::string& contractSha256()const noexcept{return sha_;}
    const json::Value& binding()const noexcept{return binding_;}
private:
    explicit Definition(const json::Value&);
    std::string key_,family_,sha_;
    json::Value binding_;
    friend const Definition& definition(const std::string&);
};
const Definition& definition(const std::string& exactKey);
const std::vector<std::string>& keys();
class Token final {
public:
    Token(const Token&)=default;
private:
    Token(std::uint64_t,std::uint64_t,std::string,std::string,bool);
    std::uint64_t instance_,revision_;
    std::string key_,action_;
    bool sourceRole_;
    friend class Owner;
};
// The source role API is a trusted source-player surface, not a learner form.
// Source files remain inspectable; this enforces presentation/gesture custody.
class Owner final {
public:
    explicit Owner(const Definition&);
    ~Owner();
    Owner(const Owner&)=delete;
    Owner& operator=(const Owner&)=delete;
    Token capture(const std::string& action)const;
    Token captureSourceChoices(const std::string& action)const;
    bool current(const Token&)const;
    void apply(const Token&,const json::Value& actualTypedInput);
    // Adds a distinct, source-bound manual method from another current owner.
    // Arbitrary caller snapshots cannot establish convergence custody.
    void addVerificationClue(const Token&,const Owner& otherMethod);
    json::Value learnerView()const;
    json::Value learnerActions()const;
    json::Value sourcePlayerView()const;
    std::vector<json::Value> history()const;
    bool fenceInactiveForNavigation();
    using ContinuationResolver = std::function<const Definition&(const std::string&)>;
    // Private profile data, including source-role choices. Never learner export.
    std::string continuation() const;
    static std::unique_ptr<Owner> restoreContinuation(const Definition&,const std::string&,
                                                     const ContinuationResolver& = {});
    const Definition& retainedDefinition()const noexcept;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
void validateTypedInput(const json::Value& schema,const json::Value&);
void validateTypedGuards(const json::Value& guardArray,const json::Value&);
} // namespace fathom::tasks::ear234
