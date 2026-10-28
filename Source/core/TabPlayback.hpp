#pragma once
#include "core/TabPresentation.hpp"
#include "core/PracticeTransport.hpp"

namespace fathom::tab {
struct PlaybackPosition {
    practice::Progress progress;
    std::vector<std::string> events;
    std::uint64_t cycle{}, sample{};
    bool hasMusicalSample{};
};
// Control/UI executor only. Reads the Coordinator's already validated current
// snapshot, never provisional scheduler facts or a callback-owned pointer.
// Accepted tempo maps are refreshed from the same Coordinator generation.
class Playback final {
public:
    void bind(std::shared_ptr<const Document>, std::shared_ptr<const music::ValidatedModel> preparedModel, const practice::Coordinator&);
    bool update(const practice::Coordinator&);
    const PlaybackPosition& position() const noexcept { return position_; }
    std::shared_ptr<const Document> document() const { return document_; }
private:
    std::uint64_t frame(std::uint64_t cycle, const Rational& offset) const;
    std::shared_ptr<const Document> document_;
    scheduler::Owner owner_;
    practice::Configuration config_;
    std::string context_;
    std::optional<practice::Timeline> timeline_;
    std::uint64_t remaining_{};
    PlaybackPosition position_;
};
}
