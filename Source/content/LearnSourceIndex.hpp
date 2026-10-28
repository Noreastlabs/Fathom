#pragma once
#include "content/ExerciseQueue.hpp"
#include "content/StrictJson.hpp"
#include "content/LoadCancellation.hpp"
#include <filesystem>
#include <memory>

namespace fathom::learn {
struct Binding { std::string itemId, packageHash; std::vector<std::string> variants; bool exact{}; bool supplemental{}; };
struct Exercise {
    navigation::ExerciseEntry source;
    std::string label, auditStatus, locator;
    std::vector<Binding> bindings;
};
struct Sublevel { std::string key, label; std::vector<std::size_t> exercises; };
struct Level { int number{}; std::string title; std::vector<Sublevel> sublevels; };
struct Pins { std::string index, exercises, overlay; };
class SourceIndex final {
public:
    static std::shared_ptr<const SourceIndex> load(const std::filesystem::path& directory,
        const content::CancellationCheck& canceled = {});
    // Parsing remains bounded and hash checked; caller-supplied pins support focused fixtures.
    static SourceIndex parse(const std::string& index, const std::string& exercises,
                             const std::string& overlay, const Pins&,
                             const content::CancellationCheck& canceled = {});
    const std::vector<Level>& levels() const noexcept { return levels_; }
    const std::vector<Exercise>& exercises() const noexcept { return exercises_; }
    const Level& level(int number) const;
    const Sublevel& sublevel(int level, const std::string& key) const;
    std::vector<const Exercise*> range(int level, const std::string& sublevel,
                                     const std::string& first, const std::string& last) const;
private:
    std::vector<Level> levels_;
    std::vector<Exercise> exercises_;
};
}
