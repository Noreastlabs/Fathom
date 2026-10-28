#pragma once
#include "content/StrictJson.hpp"
#include <array>
#include <optional>

namespace fathom::desktop::presentation {
// Disclosure only. No action, identity, admission or permission is represented here.
enum class Level { Beginner, Advanced, Developer };
enum class Page { Learn, Practice };
inline constexpr const char* preferenceKey = "ui_presentation";
inline constexpr std::int64_t namespaceVersion = 1;

inline const char* levelName(Level level) noexcept {
    switch (level) {
        case Level::Beginner: return "beginner";
        case Level::Advanced: return "advanced";
        case Level::Developer: return "developer";
    }
    return "unknown";
}
inline const char* levelLabel(Level level) noexcept {
    switch (level) {
        case Level::Beginner: return "Beginner";
        case Level::Advanced: return "Advanced";
        case Level::Developer: return "Developer";
    }
    return "Unknown";
}
inline void validateLevel(Level level) {
    if (level != Level::Beginner && level != Level::Advanced && level != Level::Developer)
        throw std::invalid_argument("Unsupported presentation level");
}
inline json::Value encodePreferences(Level level) {
    validateLevel(level);
    return json::Value::Object{{"version", "presentation1"}, {"global_level", levelName(level)}};
}
inline Level decodePreferences(const json::Value& value) {
    if (!value.isObject() || value.object().size() != 2)
        throw std::invalid_argument("Exact presentation preference object required");
    const auto* version = value.find("version");
    const auto* level = value.find("global_level");
    if (!version || !version->isString() || version->string() != "presentation1" ||
        !level || !level->isString())
        throw std::invalid_argument("Unsupported presentation preference shape/version");
    if (level->string() == "beginner") return Level::Beginner;
    if (level->string() == "advanced") return Level::Advanced;
    if (level->string() == "developer") return Level::Developer;
    throw std::invalid_argument("Unsupported presentation preference level");
}
inline bool preferenceValidator(const std::string& key, std::int64_t version,
                                const json::Value& value) noexcept {
    if (key != preferenceKey || version != namespaceVersion) return false;
    try { (void)decodePreferences(value); return true; } catch (...) { return false; }
}

class Model final {
public:
    Level globalLevel() const noexcept { return global_; }
    std::optional<Level> pageOverride(Page page) const { return overrides_[index(page)]; }
    Level effectiveLevel(Page page) const { return pageOverride(page).value_or(global_); }
    void setGlobalLevel(Level level) { validateLevel(level); global_ = level; }
    void setPageOverride(Page page, std::optional<Level> level) {
        if (level) validateLevel(*level);
        overrides_[index(page)] = level;
    }
    void resetPage(Page page) { setPageOverride(page, std::nullopt); }
    void resetPresentation() noexcept { global_ = Level::Beginner; overrides_ = {}; }
    void resetForProfile() noexcept { resetPresentation(); }
    std::string effectiveLabel(Page page) const {
        return std::string("Presentation: ") + levelLabel(effectiveLevel(page)) +
               (pageOverride(page) ? " (this page, session only)" : " (global)");
    }
private:
    static std::size_t index(Page page) {
        switch (page) { case Page::Learn: return 0; case Page::Practice: return 1; }
        throw std::invalid_argument("Unsupported presentation page override");
    }
    Level global_ = Level::Beginner;
    std::array<std::optional<Level>, 2> overrides_{};
};
} // namespace fathom::desktop::presentation
