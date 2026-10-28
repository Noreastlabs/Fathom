#include "core/Quantity.hpp"
#include <limits>
#include <numeric>
#include <stdexcept>

namespace fathom {
namespace {
std::int64_t multiply(std::int64_t a, std::int64_t b) {
    if (b != 0 && a > std::numeric_limits<std::int64_t>::max() / b)
        throw std::overflow_error("Rational product exceeds supported integer range");
    return a * b;
}
}
Rational::Rational(std::int64_t numerator, std::int64_t denominator) {
    if (numerator < 0 || denominator <= 0)
        throw std::invalid_argument("Rational requires a nonnegative numerator and positive denominator");
    const auto divisor = std::gcd(numerator, denominator);
    numerator_ = numerator / divisor;
    denominator_ = denominator / divisor;
}
Rational Rational::operator+(const Rational& rhs) const {
    const auto divisor = std::gcd(denominator_, rhs.denominator_);
    const auto left = multiply(numerator_, rhs.denominator_ / divisor);
    const auto right = multiply(rhs.numerator_, denominator_ / divisor);
    if (left > std::numeric_limits<std::int64_t>::max() - right)
        throw std::overflow_error("Rational sum exceeds supported integer range");
    return Rational{left + right, multiply(denominator_ / divisor, rhs.denominator_)};
}
bool Rational::operator==(const Rational& rhs) const noexcept {
    return numerator_ == rhs.numerator_ && denominator_ == rhs.denominator_;
}
bool Rational::operator<(const Rational& rhs) const noexcept {
    auto a = numerator_, b = denominator_, c = rhs.numerator_, d = rhs.denominator_;
    bool reversed = false;
    for (;;) {
        if (a / b != c / d) return reversed ? a / b > c / d : a / b < c / d;
        const auto left = a % b, right = c % d;
        if (left == 0 || right == 0) {
            if (left == right) return false;
            return reversed ? right == 0 : left == 0;
        }
        a = b; b = left; c = d; d = right; reversed = !reversed;
    }
}
double Rational::displayValue() const noexcept {
    return static_cast<double>(numerator_) / static_cast<double>(denominator_);
}
} // namespace fathom
