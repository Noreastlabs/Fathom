#include "core/Quantity.hpp"
#include <iostream>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <utility>

using fathom::Rational;
template<class A, class B, class = void> struct CanAdd : std::false_type {};
template<class A, class B> struct CanAdd<A, B, std::void_t<decltype(std::declval<A>() + std::declval<B>())>> : std::true_type {};
static_assert(!CanAdd<fathom::QuarterTime, fathom::SecondsTime>::value, "Units must not silently mix");
static_assert(!std::is_convertible_v<double, Rational>, "Floating time must not implicitly become exact time");
static_assert(!std::is_constructible_v<Rational, double>, "Direct floating construction must reject");
static_assert(!std::is_constructible_v<Rational, double, int>, "Floating numerator must reject");
static_assert(!std::is_constructible_v<Rational, int, double>, "Floating denominator must reject");
static_assert(!std::is_constructible_v<Rational, bool>, "Boolean numerator must reject");
static_assert(!std::is_constructible_v<Rational, int, bool>, "Boolean denominator must reject");
static_assert(!std::is_constructible_v<Rational, std::uint64_t>, "Unsigned conversion must be checked explicitly");
static_assert(std::is_constructible_v<Rational, std::int64_t, std::int64_t>, "Signed integer construction supported");

int main() {
    int checks = 0;
    auto require = [&](bool condition, const char* label) {
        ++checks;
        if (!condition) throw std::runtime_error(label);
    };
    auto invalid = [&](auto operation) {
        try { operation(); } catch (const std::invalid_argument&) { return true; }
        return false;
    };
    auto overflow = [&](auto operation) {
        try { operation(); } catch (const std::overflow_error&) { return true; }
        return false;
    };
    try {
        require(Rational{0, 7} == Rational{}, "zero normalization");
        require(Rational{6, 8} == Rational{3, 4}, "reduction");
        require(invalid([] { (void) Rational{1, 0}; }), "zero denominator rejected");
        require(invalid([] { (void) Rational{-1, 2}; }), "negative structural time rejected");
        require(invalid([] { (void) Rational{1, -2}; }), "negative denominator rejected");
        for (std::int64_t denominator = 1; denominator <= 32; ++denominator) {
            Rational total;
            for (std::int64_t n = 0; n < denominator; ++n) total = total + Rational{1, denominator};
            require(total == Rational{1}, "exact cycle from repeated fractional subdivisions");
        }
        require(Rational{1, 3} + Rational{1, 6} == Rational{1, 2}, "different denominators");
        constexpr auto maximum = std::numeric_limits<std::int64_t>::max();
        require(Rational{maximum, maximum} == Rational{1}, "reduce before range arithmetic");
        require(overflow([&] { (void) (Rational{maximum} + Rational{1}); }), "sum overflow rejected");
        require(overflow([&] { (void) (Rational{1, maximum} + Rational{1, maximum - 1}); }), "denominator overflow rejected");
        require(overflow([&] { (void) (Rational{maximum, 2} + Rational{maximum, 2}); }), "documented conservative intermediate bound rejects");
        require((fathom::QuarterTime{Rational{1, 3}} + fathom::QuarterTime{Rational{2, 3}}).value == Rational{1}, "typed quarter sum");
        require(Rational{1, maximum} < Rational{1, maximum - 1}, "extreme reciprocal comparison without cross-product overflow");
        require(Rational{maximum - 2, maximum - 1} < Rational{maximum - 1, maximum}, "extreme near-one comparison");
        require(!(Rational{2, 3} < Rational{4, 6}), "equal reduced values are not less");
        bool ordered = true;
        for (std::int64_t a = 0; a < 16; ++a)
            for (std::int64_t b = 1; b <= 16; ++b)
                for (std::int64_t c = 0; c < 16; ++c)
                    for (std::int64_t d = 1; d <= 16; ++d)
                        ordered = ordered && ((Rational{a,b} < Rational{c,d}) == (a*d < c*b));
        require(ordered, "65536 exact bounded comparison counterexamples");
        std::cout << "PASS " << checks << " core checks; 9 compile-time unit/input checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n';
        return 1;
    }
}
