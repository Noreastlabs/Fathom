#pragma once
#include <cstdint>
#include <type_traits>

namespace fathom {
// Nonnegative, reduced structural value. Invalid/overflowing arithmetic rejects;
// it never wraps or changes unit. Not a content parser or a clock.
class Rational final {
public:
    explicit Rational(std::int64_t numerator = 0, std::int64_t denominator = 1);
    // Prevent direct-call narrowing before the checked constructor sees input.
    // Unsigned inputs also require an explicit checked conversion by the caller.
    template<class N, class D = std::int64_t,
             std::enable_if_t<!(std::is_integral_v<N> && std::is_signed_v<N>
                               && std::is_integral_v<D> && std::is_signed_v<D>), int> = 0>
    Rational(N, D = 1) = delete;
    std::int64_t numerator() const noexcept { return numerator_; }
    std::int64_t denominator() const noexcept { return denominator_; }
    Rational operator+(const Rational& rhs) const;
    bool operator==(const Rational& rhs) const noexcept;
    bool operator<(const Rational& rhs) const noexcept;
    double displayValue() const noexcept;
private:
    std::int64_t numerator_;
    std::int64_t denominator_;
};

struct QuarterUnit {};
struct SecondsUnit {};
template<class Unit> struct Quantity final {
    explicit Quantity(Rational input = Rational{}) : value(input) {}
    Rational value;
    Quantity operator+(const Quantity& other) const { return Quantity{value + other.value}; }
};
using QuarterTime = Quantity<QuarterUnit>;
using SecondsTime = Quantity<SecondsUnit>;
} // namespace fathom
