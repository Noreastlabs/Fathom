#pragma once
#include <array>
#include <cstdint>
#include <string>

namespace fathom::scheduler {
struct FrameRatio;
// Accumulated sample position, distinct from small immutable plan intervals.
// Canonical whole + proper fraction; the callback path never allocates.
// 640 fractional bits cover a compatible cycle/intro and supported 20..300
// tempos, plus one independently evaluated event offset. Arbitrary unrelated
// denominators remain checked rather than promising unbounded rational math.
class FramePosition final {
public:
    FramePosition() = default;
    bool operator==(const FramePosition& p) const noexcept {
        return whole_ == p.whole_ && numerator_ == p.numerator_ && denominator_ == p.denominator_;
    }
    // Control thread only: exact improper numerator/denominator decimal strings.
    std::array<std::string, 2> exact() const;
private:
    friend bool addRepeated(const FramePosition&, FrameRatio, std::uint64_t, FramePosition&) noexcept;
    friend bool round(const FramePosition&, std::uint64_t&) noexcept;
    std::uint64_t whole_{};
    std::array<std::uint32_t, 20> numerator_{}, denominator_{{1}};
};
bool position(FrameRatio, FramePosition&) noexcept;
bool add(const FramePosition&, FrameRatio, FramePosition&) noexcept;
bool addRepeated(const FramePosition&, FrameRatio, std::uint64_t, FramePosition&) noexcept;
bool round(const FramePosition&, std::uint64_t&) noexcept;
}
