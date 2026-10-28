#include "core/FramePosition.hpp"
#include "core/Scheduler.hpp"
#include <algorithm>
#include <limits>
#include <numeric>
#include <stdexcept>

namespace fathom::scheduler {
namespace {
template<std::size_t N> using Wide = std::array<std::uint32_t, N>;
constexpr auto maximum = std::numeric_limits<std::uint64_t>::max();
template<std::size_t N> Wide<N> wide(std::uint64_t n) noexcept {
    Wide<N> v{}; v[0] = static_cast<std::uint32_t>(n); v[1] = static_cast<std::uint32_t>(n >> 32); return v;
}
template<std::size_t N> int compare(const Wide<N>& a, const Wide<N>& b) noexcept {
    for (std::size_t i = N; i--;) if (a[i] != b[i]) return a[i] < b[i] ? -1 : 1;
    return 0;
}
template<std::size_t N> bool sum(const Wide<N>& a, const Wide<N>& b, Wide<N>& out) noexcept {
    Wide<N> v{}; std::uint64_t carry{};
    for (std::size_t i = 0; i < N; ++i) {
        const auto s = static_cast<std::uint64_t>(a[i]) + b[i] + carry;
        v[i] = static_cast<std::uint32_t>(s); carry = s >> 32;
    }
    if (carry) return false;
    out = v; return true;
}
template<std::size_t N> Wide<N> difference(const Wide<N>& a, const Wide<N>& b) noexcept {
    Wide<N> v{}; std::uint64_t borrow{};
    for (std::size_t i = 0; i < N; ++i) {
        const auto sub = static_cast<std::uint64_t>(b[i]) + borrow;
        v[i] = static_cast<std::uint32_t>(static_cast<std::uint64_t>(a[i]) - sub);
        borrow = static_cast<std::uint64_t>(a[i]) < sub;
    }
    return v; // internal callers establish a >= b
}
template<std::size_t N> bool times(const Wide<N>& a, std::uint64_t m, Wide<N>& out) noexcept {
    Wide<N> v{};
    for (std::size_t j = 0; j < 2; ++j) {
        const auto digit = static_cast<std::uint32_t>(m >> (32 * j));
        if (!digit) continue;
        std::uint64_t carry{};
        for (std::size_t i = 0; i < N - j; ++i) {
            const auto product = static_cast<std::uint64_t>(a[i]) * digit + v[i+j] + carry;
            v[i+j] = static_cast<std::uint32_t>(product); carry = product >> 32;
        }
        if (carry || (j && a[N-1])) return false;
    }
    out = v; return true;
}
// Portable word division. The common small divisor route uses 64-bit partial
// words. Full uint64 divisors use bounded bit division with an explicit high
// carry; unsigned wrapping in the subtraction reconstructs the exact remainder.
template<std::size_t N> std::uint64_t divide(const Wide<N>& a, std::uint64_t d, Wide<N>& out) noexcept {
    Wide<N> q{}; std::uint64_t remainder{};
    if (d <= UINT32_MAX) {
        for (std::size_t i = N; i--;) {
            const auto n = (remainder << 32) | a[i];
            q[i] = static_cast<std::uint32_t>(n / d); remainder = n % d;
        }
    } else {
        for (std::size_t i = N; i--;) for (int bit = 31; bit >= 0; --bit) {
            const bool high = (remainder >> 63) != 0;
            remainder = (remainder << 1) | ((a[i] >> bit) & 1u);
            if (high || remainder >= d) { remainder -= d; q[i] |= std::uint32_t{1} << bit; }
        }
    }
    out = q; return remainder;
}
template<std::size_t N> std::uint64_t modulo(const Wide<N>& a, std::uint64_t d) noexcept {
    Wide<N> unused{}; return divide(a, d, unused);
}
template<std::size_t N> std::string decimal(Wide<N> a) {
    std::string value;
    do { const auto r = divide(a, 10, a); value.push_back(static_cast<char>('0' + r)); } while (a != Wide<N>{});
    std::reverse(value.begin(), value.end()); return value;
}
}
bool addRepeated(const FramePosition& a, FrameRatio b, std::uint64_t count, FramePosition& out) noexcept {
    if (!b.d) return false;
    const auto reduction = std::gcd(b.n, b.d); b.n /= reduction; b.d /= reduction;
    const auto integral = b.n / b.d;
    if (integral && count > maximum / integral) return false;
    std::uint64_t whole = integral * count;
    // Two uint64 factors fit this fixed 128-bit scratch; division yields a
    // quotient below count because the multiplied remainder is < denominator.
    Wide<4> multiplied{}, quotient{};
    if (!times(wide<4>(b.n % b.d), count, multiplied)) return false;
    auto remainder = divide(multiplied, b.d, quotient);
    if (quotient[2] || quotient[3]) return false;
    const auto extra = (static_cast<std::uint64_t>(quotient[1]) << 32) | quotient[0];
    if (whole > maximum - extra) return false;
    whole += extra;
    if (a.whole_ > maximum - whole) return false;
    FramePosition result = a; result.whole_ += whole;
    if (remainder) {
        const auto reducedBy = std::gcd(remainder, b.d); remainder /= reducedBy; b.d /= reducedBy;
        const auto g = std::gcd(modulo(a.denominator_, b.d), b.d);
        Wide<20> left{}, right{}, reducedDenominator{}, numerator{}, denominator{};
        divide(a.denominator_, g, reducedDenominator);
        if (!times(a.numerator_, b.d / g, left) || !times(reducedDenominator, remainder, right)
            || !sum(left, right, numerator) || !times(a.denominator_, b.d / g, denominator)) return false;
        const auto h = std::gcd(modulo(numerator, g), g);
        divide(numerator, h, numerator); divide(denominator, h, denominator);
        if (compare(numerator, denominator) >= 0) {
            if (result.whole_ == maximum) return false;
            ++result.whole_; numerator = difference(numerator, denominator);
        }
        result.numerator_ = numerator; result.denominator_ = denominator;
    }
    out = result; return true;
}
bool position(FrameRatio a, FramePosition& out) noexcept { return addRepeated(FramePosition{}, a, 1, out); }
bool add(const FramePosition& a, FrameRatio b, FramePosition& out) noexcept { return addRepeated(a, b, 1, out); }
bool round(const FramePosition& a, std::uint64_t& out) noexcept {
    const bool up = compare(a.numerator_, difference(a.denominator_, a.numerator_)) >= 0;
    if (up && a.whole_ == maximum) return false;
    out = a.whole_ + (up ? 1 : 0); return true;
}
std::array<std::string, 2> FramePosition::exact() const {
    Wide<24> denominator{}, fraction{}, numerator{};
    std::copy(denominator_.begin(), denominator_.end(), denominator.begin());
    std::copy(numerator_.begin(), numerator_.end(), fraction.begin());
    if (!times(denominator, whole_, numerator) || !sum(numerator, fraction, numerator))
        throw std::overflow_error("Exact sample position serialization overflow");
    return {decimal(numerator), decimal(denominator)};
}
}
