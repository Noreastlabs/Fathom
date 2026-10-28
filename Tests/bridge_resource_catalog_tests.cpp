#include "content/BridgeResourceCatalog.hpp"
#include "content/Canonical.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <iterator>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using fathom::content::BridgeResourceCatalog;
using fathom::json::Value;

int checks = 0;
int fixtureNumber = 0;

void check(bool condition, const std::string& name) {
    if (!condition) throw std::runtime_error("CHECK_FAILED " + name);
    ++checks;
}

template <typename Action>
void refuses(Action action, const std::string& code, const std::string& name) {
    try {
        action();
    } catch (const std::exception& error) {
        check(std::string(error.what()).find(code) != std::string::npos, name + " refusal code");
        return;
    }
    throw std::runtime_error("EXPECTED_REFUSAL " + name + " code=" + code);
}

std::string readText(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("Cannot read fixture source: " + path.string());
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

void writeText(const std::filesystem::path& path, const std::string& bytes) {
    std::filesystem::create_directories(path.parent_path());
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!output) throw std::runtime_error("Cannot write fixture: " + path.string());
    output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    if (!output) throw std::runtime_error("Cannot finish fixture: " + path.string());
}

struct TempTree final {
    explicit TempTree(const std::filesystem::path& scratch) {
        path = scratch / ("fixture-" + std::to_string(++fixtureNumber));
        std::filesystem::remove_all(path);
        std::filesystem::create_directories(path);
    }
    ~TempTree() {
        std::error_code error;
        std::filesystem::remove_all(path, error);
    }
    std::filesystem::path path;
};

void copyBundle(const std::filesystem::path& from, const std::filesystem::path& to,
                const std::string& omit = {}) {
    std::filesystem::create_directories(to);
    for (const auto* name : {"manifest.json", "cards.json", "source-passages.json"}) {
        if (name == omit) continue;
        std::filesystem::copy_file(from / name, to / name);
    }
}

void mutateJsonFile(const std::filesystem::path& path,
                    const std::function<void(Value&)>& mutate) {
    auto value = fathom::json::parse(readText(path));
    mutate(value);
    writeText(path, fathom::json::stringify(value));
}

Value& objectMember(Value& value, const std::string& key) {
    if (!value.isObject()) throw std::runtime_error("Expected fixture JSON object: " + key);
    auto found = value.object().find(key);
    if (found == value.object().end()) throw std::runtime_error("Missing fixture JSON key: " + key);
    return found->second;
}

Value& cardById(Value& root, const std::string& id) {
    auto& cards = objectMember(root, "cards");
    if (!cards.isArray()) throw std::runtime_error("Expected cards array");
    for (auto& card : cards.array()) {
        const auto* cardId = card.find("id");
        if (cardId && cardId->isString() && cardId->string() == id) return card;
    }
    throw std::runtime_error("Missing fixture card: " + id);
}

void copySourceTree(const std::filesystem::path& repositoryRoot,
                    const std::filesystem::path& bundleRoot,
                    const std::filesystem::path& destination) {
    std::set<std::string> paths;
    auto manifest = fathom::json::parse(readText(bundleRoot / "manifest.json"));
    const auto& bindings = objectMember(manifest, "source_bindings");
    for (const auto& [path, unused] : bindings.object()) {
        (void)unused;
        paths.insert(path);
    }
    auto passages = fathom::json::parse(readText(bundleRoot / "source-passages.json"));
    const auto& passageMap = objectMember(passages, "passages");
    for (const auto& [id, passage] : passageMap.object()) {
        (void)id;
        const auto* path = passage.find("path");
        if (!path || !path->isString()) throw std::runtime_error("Missing source path in fixture passage");
        paths.insert(path->string());
    }
    for (const auto& relative : paths) {
        const auto source = repositoryRoot / relative;
        const auto target = destination / relative;
        std::filesystem::create_directories(target.parent_path());
        std::filesystem::copy_file(source, target);
    }
}

void run(const std::filesystem::path& root, const std::filesystem::path& bundle,
         const std::filesystem::path& scratch) {
    const auto catalog = BridgeResourceCatalog::load(bundle, root);
    check(catalog.offline(), "sealed catalog is offline");
    check(!catalog.runtimeAdmitted(), "catalog is not runtime-admitted");
    check(catalog.cards().size() == 21, "exact card count");
    check(catalog.sourceBindings().size() == 5, "all five source bindings verified");
    check(catalog.verifiedPassageCount() == 43, "all 43 sealed passages verified");
    check(catalog.passages().size() == 41, "only 41 card-linked passages are exposed");
    check(catalog.findPassage("P-TXT1149-1171") == nullptr,
          "unlinked supporting review passage is not exposed");
    std::size_t linkCount = 0;
    for (const auto& card : catalog.cards()) linkCount += card.sourceLinks.size();
    check(linkCount == 49, "all 49 source links are preserved");

    const std::vector<std::string> bridgeIds{"G01", "G02", "G03", "G04", "G05"};
    const std::vector<std::string> resourceIds{
        "R39", "R48", "R73", "R74", "R75", "R76", "R77", "R78",
        "R79", "R95", "R96", "R97A", "R97B", "R97C", "R99", "R105"
    };
    for (std::size_t i = 0; i < bridgeIds.size(); ++i) {
        const auto& card = catalog.cards()[i];
        check(card.id == bridgeIds[i] && card.kind == "bridge", "bridge identity " + bridgeIds[i]);
        check(card.availability == "source_context_only" && !card.newWordingCurriculumAccepted,
              "bridge remains pending/non-runtime " + bridgeIds[i]);
    }
    check(catalog.find("G04")->hasProposedPreview && !catalog.find("G04")->proposedPreviewJson.empty(),
          "G04 proposed preview retained without acceptance");
    check(catalog.find("G05")->hasProposedPreview && !catalog.find("G05")->proposedPreviewJson.empty(),
          "G05 proposed preview retained without acceptance");
    for (std::size_t i = 0; i < resourceIds.size(); ++i) {
        const auto& card = catalog.cards()[i + bridgeIds.size()];
        check(card.id == resourceIds[i] && card.kind == "resource", "resource identity " + resourceIds[i]);
        check(card.availability == "required_unsupplied" && !card.hasSuppliedAsset,
              "resource remains unsupplied " + resourceIds[i]);
        check(!card.runtimeAdmitted && !card.runtimeNetwork && !card.inAppImport && !card.inAppRecorder,
              "resource runtime/network/import/recorder flags false " + resourceIds[i]);
        check(!card.sourceRefs.empty() && !card.tags.empty(), "resource source identity and tags " + resourceIds[i]);
    }
    for (const auto& card : catalog.cards()) {
        check(catalog.find(card.id) != nullptr, "card lookup " + card.id);
        check(!card.hasSuppliedAsset && !card.runtimeAdmitted, "no supply/admission " + card.id);
        for (const auto& link : card.sourceLinks)
            check(catalog.findPassage(link.passageId) != nullptr, "linked source passage " + card.id + "/" + link.passageId);
    }

    const auto sourceSearch = catalog.search("L12-TXT9-39");
    check(std::find(sourceSearch.begin(), sourceSearch.end(), "G01") != sourceSearch.end(),
          "search by approved source identity");
    const auto tagSearch = catalog.search("Fretboard");
    check(std::find(tagSearch.begin(), tagSearch.end(), "G01") != tagSearch.end(), "search by authored tag");
    check(catalog.search("fReTbOaRd") == tagSearch, "case-insensitive deterministic tag search");
    check(tagSearch == catalog.search("Fretboard"), "repeated search is deterministic");
    check(!catalog.search("Maximum: 30 points").size(), "answer-bearing passage text is not indexed");
    check(catalog.search("").empty(), "empty search is safe and deterministic");

    {
        TempTree fixture(scratch);
        const auto altered = fixture.path / "bundle";
        copyBundle(bundle, altered, "source-passages.json");
        refuses([&] { (void)BridgeResourceCatalog::load(altered, root); }, "BUNDLE_FILE_SET", "missing bundle file");
    }
    {
        TempTree fixture(scratch);
        const auto altered = fixture.path / "bundle";
        copyBundle(bundle, altered);
        auto cards = readText(altered / "cards.json");
        cards.push_back('\n');
        writeText(altered / "cards.json", cards);
        refuses([&] { (void)BridgeResourceCatalog::load(altered, root); }, "BUNDLE_FILE_SIZE", "changed bundle asset");
    }
    {
        TempTree fixture(scratch);
        const auto altered = fixture.path / "bundle";
        copyBundle(bundle, altered);
        mutateJsonFile(altered / "manifest.json", [](Value& manifest) {
            objectMember(manifest, "runtime_admitted") = Value(true);
        });
        refuses([&] { (void)BridgeResourceCatalog::load(altered, root); }, "RUNTIME_ADMISSION_TRUE", "runtime-admitted manifest");
    }
    {
        TempTree fixture(scratch);
        const auto altered = fixture.path / "bundle";
        copyBundle(bundle, altered);
        mutateJsonFile(altered / "manifest.json", [](Value& manifest) {
            objectMember(manifest, "supplied_assets") = Value(Value::Array{Value("R39")});
        });
        refuses([&] { (void)BridgeResourceCatalog::load(altered, root); }, "MANIFEST_SUPPLIED_ASSETS", "false supplied-assets list");
    }
    {
        TempTree fixture(scratch);
        const auto altered = fixture.path / "bundle";
        copyBundle(bundle, altered);
        mutateJsonFile(altered / "cards.json", [](Value& cards) {
            objectMember(cardById(cards, "G01"), "runtime_admitted") = Value(true);
        });
        refuses([&] { (void)BridgeResourceCatalog::load(altered, root); }, "CARD_RUNTIME_ADMITTED", "runtime-admitted card");
    }
    {
        TempTree fixture(scratch);
        const auto altered = fixture.path / "bundle";
        copyBundle(bundle, altered);
        mutateJsonFile(altered / "cards.json", [](Value& cards) {
            objectMember(cardById(cards, "R39"), "supplied_asset") = Value("fake-audio.wav");
        });
        refuses([&] { (void)BridgeResourceCatalog::load(altered, root); }, "CARD_SUPPLIED_ASSET", "supplied resource asset");
    }
    {
        TempTree fixture(scratch);
        const auto altered = fixture.path / "bundle";
        copyBundle(bundle, altered);
        mutateJsonFile(altered / "cards.json", [](Value& cards) {
            auto& requirement = objectMember(cardById(cards, "R39"), "approved_requirement");
            objectMember(requirement, "runtime_network") = Value(true);
        });
        refuses([&] { (void)BridgeResourceCatalog::load(altered, root); }, "RESOURCE_NETWORK_ENABLED", "network-enabled resource");
    }
    {
        TempTree fixture(scratch);
        const auto missingSources = fixture.path / "empty-source-root";
        std::filesystem::create_directories(missingSources);
        refuses([&] { (void)BridgeResourceCatalog::load(bundle, missingSources); }, "FILE_MISSING", "missing original source");
    }
    {
        TempTree fixture(scratch);
        const auto alteredSources = fixture.path / "source-root";
        copySourceTree(root, bundle, alteredSources);
        const auto plan = alteredSources / "Results/primary/20260906T184530Z-2.4.1.1.1-r01-evidence/plan.json";
        auto bytes = readText(plan);
        bytes.push_back(' ');
        writeText(plan, bytes);
        refuses([&] { (void)BridgeResourceCatalog::load(bundle, alteredSources); }, "BOUND_SOURCE_HASH", "changed bound plan source");
    }
    {
        TempTree fixture(scratch);
        const auto altered = fixture.path / "bundle";
        copyBundle(bundle, altered);
        std::filesystem::remove(altered / "source-passages.json");
        std::filesystem::create_symlink(bundle / "source-passages.json", altered / "source-passages.json");
        refuses([&] { (void)BridgeResourceCatalog::load(altered, root); }, "SYMLINK_REFUSED", "symlinked bundle passage");
    }

    std::cout << "PASS " << checks << " bridge resource catalog checks; bridge_ids=5; resource_ids=16; "
              << "verified_passages=43; linked_passages_exposed=41; runtime_admitted=false; offline=true\n";
}
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 4) throw std::runtime_error("Usage: bridge_resource_catalog_tests <repo-root> <bundle-root> <scratch-root>");
        const auto root = std::filesystem::canonical(argv[1]);
        const auto bundle = std::filesystem::canonical(argv[2]);
        const auto scratch = std::filesystem::absolute(argv[3]);
        std::filesystem::create_directories(scratch);
        run(root, bundle, scratch);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << " after " << checks << " checks\n";
        return 1;
    }
}
