#pragma once
#include "content/StrictJson.hpp"
#include "core/PracticeTransport.hpp"
#include "core/ReferenceAudio.hpp"

namespace fathom::lesson {
class Catalog;
// Only the validated, hash-pinned Catalog can create this immutable capability.
// It authorizes a bounded consumer, not source task completion or performance.
class Admission final {
public:
    static constexpr std::uint64_t maximumScheduledPasses = 32;
    const std::shared_ptr<const music::ValidatedModel>& model() const noexcept { return model_; }
    const json::Value& identity() const noexcept { return identity_; }
    const std::string& sourceBinding() const noexcept { return sourceBinding_; }
    const std::string& description() const noexcept { return description_; }
    Rational span() const noexcept { return span_; }
    // Scheduler/TAB positions are local; captured source positions retain this origin.
    Rational sourceStart() const noexcept { return sourceStart_; }
    bool practiceAllowed() const noexcept { return practice_; }
    practice::Configuration practiceConfiguration(std::uint32_t rate,std::uint16_t bpm) const;
    reference::Configuration referenceConfiguration(const scheduler::Owner&,std::uint64_t binding,
                                                   std::uint32_t rate,std::uint16_t bpm) const;
    void validatePractice(const practice::Configuration&) const;
    void validateOriginal(const practice::Coordinator&) const;
    void validateReference(const reference::Configuration&) const;
private:
    friend class Catalog;
    Admission(std::shared_ptr<const music::ValidatedModel>,json::Value,Rational,bool,std::string,Rational sourceStart=Rational{});
    std::shared_ptr<const music::ValidatedModel> model_;
    json::Value identity_;
    Rational span_;
    Rational sourceStart_;
    bool practice_{};
    std::string sourceBinding_,description_;
};
}
