#pragma once
#include "core/MusicModel.hpp"
#include <memory>
#include <string>
#include <vector>

namespace fathom::tab {
struct ToneIdentity { std::string event; int string{}; };
struct Position {
    std::vector<std::string> events, instants;
    std::vector<ToneIdentity> sounding;
};
// Immutable source view. This is neither admission nor a playback clock.
class Document final {
public:
    explicit Document(std::shared_ptr<const music::ValidatedModel>);
    const music::Model& source() const noexcept { return model_->source(); }
    const music::Event* event(const std::string&) const noexcept;
    bool allTimed() const noexcept;
    Position at(const Rational&) const;
    std::string detail(const std::string&) const;
    std::string overview() const;
    int displayString(int internal) const;
private:
    std::shared_ptr<const music::ValidatedModel> model_;
};
std::string fraction(const Rational&);
std::string span(const music::Span&);
std::string attack(const music::Tone&);
std::string contact(music::Contact);
std::string degrees(const music::Tone&);
std::string pitch(const music::Tone&);
std::string noteName(const music::Tone&); // Derived sharp spelling labelled separately.
} // namespace fathom::tab
