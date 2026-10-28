#include "content/BridgeResourceCatalog.hpp"

#include "content/Canonical.hpp"

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <set>
#include <stdexcept>
#include <unordered_map>

namespace fathom::content {
namespace {
using J = json::Value;

constexpr const char* kManifestSha256 = "8270787ed8c7a9511b9cf7c218b3c57ec289f354a0604ca2e31ea3c14ad0e343";
constexpr std::size_t kJsonLimit = 4U * 1024U * 1024U;
constexpr std::size_t kSourceLimit = 64U * 1024U * 1024U;
constexpr std::size_t kExpectedPassages = 43;
constexpr std::size_t kExpectedLinkedPassages = 41;
constexpr std::size_t kExpectedSourceLinks = 49;

const std::vector<std::string> kBridgeIds{"G01", "G02", "G03", "G04", "G05"};
const std::vector<std::string> kResourceIds{
    "R39", "R48", "R73", "R74", "R75", "R76", "R77", "R78",
    "R79", "R95", "R96", "R97A", "R97B", "R97C", "R99", "R105"
};

[[noreturn]] void refuse(const std::string& code, const std::string& detail = {}) {
    throw std::runtime_error("BRIDGE_RESOURCE_" + code + (detail.empty() ? "" : ": " + detail));
}

void require(bool condition, const std::string& code, const std::string& detail = {}) {
    if (!condition) refuse(code, detail);
}

const J& at(const J& value, const std::string& key, const std::string& context) {
    require(value.isObject(), "TYPE_OBJECT", context);
    const auto* child = value.find(key);
    require(child != nullptr, "REQUIRED_FIELD", context + "/" + key);
    return *child;
}

std::string stringValue(const J& value, const std::string& context, bool allowEmpty = false) {
    require(value.isString(), "TYPE_STRING", context);
    const auto& text = value.string();
    require(allowEmpty || !text.empty(), "EMPTY_STRING", context);
    return text;
}

bool boolValue(const J& value, const std::string& context) {
    require(value.isBool(), "TYPE_BOOLEAN", context);
    return value.boolean();
}

std::int64_t integerValue(const J& value, const std::string& context,
                          std::int64_t minimum = 0, std::int64_t maximum = 1000000) {
    std::int64_t result = 0;
    require(value.integer(result), "TYPE_INTEGER", context);
    require(result >= minimum && result <= maximum, "INTEGER_RANGE", context);
    return result;
}

std::vector<std::string> stringArray(const J& value, const std::string& context) {
    require(value.isArray(), "TYPE_ARRAY", context);
    std::vector<std::string> result;
    result.reserve(value.array().size());
    std::set<std::string> unique;
    for (std::size_t i = 0; i < value.array().size(); ++i) {
        auto item = stringValue(value.array()[i], context + "/" + std::to_string(i));
        require(unique.insert(item).second, "DUPLICATE_VALUE", context + "/" + item);
        result.push_back(std::move(item));
    }
    return result;
}

std::vector<int> integerArray(const J& value, const std::string& context) {
    require(value.isArray(), "TYPE_ARRAY", context);
    std::vector<int> result;
    result.reserve(value.array().size());
    for (std::size_t i = 0; i < value.array().size(); ++i)
        result.push_back(static_cast<int>(integerValue(value.array()[i], context + "/" + std::to_string(i))));
    return result;
}

std::filesystem::path checkedRoot(const std::filesystem::path& root, const std::string& label) {
    require(root.is_absolute(), "ROOT_NOT_ABSOLUTE", label);
    std::filesystem::path current;
    for (const auto& part : root) {
        current /= part;
        std::error_code error;
        const auto state = std::filesystem::symlink_status(current, error);
        require(!error || error == std::errc::no_such_file_or_directory, "ROOT_UNAVAILABLE", current.string());
        require(!std::filesystem::is_symlink(state), "ROOT_SYMLINK_REFUSED", current.string());
    }
    require(std::filesystem::is_directory(root), "ROOT_MISSING", root.string());
    return std::filesystem::canonical(root);
}

std::filesystem::path safeFile(const std::filesystem::path& root, const std::string& name) {
    require(!name.empty() && name.find('\\') == std::string::npos && name.find('\0') == std::string::npos,
            "UNSAFE_PATH", name);
    const std::filesystem::path relative{name};
    require(!relative.is_absolute() && !relative.has_root_name(), "UNSAFE_PATH", name);
    auto current = root;
    for (const auto& part : relative) {
        require(part != "" && part != "." && part != "..", "UNSAFE_PATH_COMPONENT", name);
        current /= part;
        std::error_code error;
        const auto state = std::filesystem::symlink_status(current, error);
        require(!error || error == std::errc::no_such_file_or_directory, "FILE_STATUS_FAILED", current.string());
        require(!std::filesystem::is_symlink(state), "SYMLINK_REFUSED", current.string());
    }
    require(std::filesystem::is_regular_file(current), "FILE_MISSING", name);
    return current;
}

std::string readFile(const std::filesystem::path& root, const std::string& name,
                     std::size_t limit, const std::string& code) {
    const auto path = safeFile(root, name);
    std::error_code error;
    const auto size = std::filesystem::file_size(path, error);
    require(!error && size <= limit, code, name);
    try {
        auto bytes = content::readBounded(path, limit);
        require(bytes.size() == size, code, name);
        return bytes;
    } catch (const std::exception& errorValue) {
        refuse(code, name + " (" + errorValue.what() + ")");
    }
}

J parseJson(const std::string& bytes, const std::string& name) {
    try {
        return json::parse(bytes, json::Limits{kJsonLimit, 64, 1024U * 1024U, 1000000, 128});
    } catch (const std::exception& error) {
        refuse("JSON_INVALID", name + " (" + error.what() + ")");
    }
}

std::set<std::string> actualFiles(const std::filesystem::path& root) {
    std::set<std::string> result;
    std::error_code error;
    for (std::filesystem::recursive_directory_iterator it(root, error), end; it != end; it.increment(error)) {
        require(!error, "DIRECTORY_READ_FAILED", root.string());
        require(!it->is_symlink(), "SYMLINK_REFUSED", it->path().string());
        if (it->is_regular_file()) result.insert(it->path().lexically_relative(root).generic_string());
        else require(it->is_directory(), "UNEXPECTED_ENTRY", it->path().string());
    }
    require(!error, "DIRECTORY_READ_FAILED", root.string());
    return result;
}

void requireExactStringArray(const J& value, const std::vector<std::string>& expected,
                             const std::string& code) {
    require(stringArray(value, code) == expected, code);
}

std::string lowerAscii(std::string text) {
    std::transform(text.begin(), text.end(), text.begin(), [](unsigned char value) {
        return static_cast<char>(std::tolower(value));
    });
    return text;
}

std::string joinForSearch(const BridgeCard& card) {
    std::string result;
    auto append = [&result](const std::string& part) {
        result.push_back('\n');
        result += part;
    };
    append(card.id);
    append(card.kind);
    append(card.title);
    append(card.summary);
    append(card.availability);
    for (const auto* fields : {&card.sourceRefs, &card.publicSourceRefs, &card.tags, &card.searchTerms,
                               &card.prerequisiteLinks, &card.requiredOutputs, &card.selectionConstraints})
        for (const auto& field : *fields) append(field);
    for (const auto& link : card.sourceLinks) {
        append(link.passageId);
        append(link.path);
        append(link.sourceSha256);
    }
    return lowerAscii(std::move(result));
}

BridgePassage parsePassage(const std::string& id, const J& value) {
    const auto context = "passages/" + id;
    BridgePassage passage;
    passage.id = id;
    passage.format = stringValue(at(value, "format", context), context + "/format");
    require(passage.format == "txt" || passage.format == "pdf", "PASSAGE_FORMAT", id);
    passage.path = stringValue(at(value, "path", context), context + "/path");
    passage.sourceSha256 = stringValue(at(value, "sha256", context), context + "/sha256");
    passage.text = stringValue(at(value, "text", context), context + "/text", true);
    passage.textSha256 = stringValue(at(value, "text_sha256", context), context + "/text_sha256");
    const auto& level = at(value, "level", context);
    passage.level = level.null() ? 0 : static_cast<int>(integerValue(level, context + "/level", 1, 105));
    if (passage.format == "pdf") {
        passage.page = static_cast<int>(integerValue(at(value, "page", context), context + "/page", 1, 1000));
    } else {
        passage.firstLine = static_cast<int>(integerValue(at(value, "first_line", context), context + "/first_line", 1));
        passage.lastLine = static_cast<int>(integerValue(at(value, "last_line", context), context + "/last_line", passage.firstLine));
        require(passage.firstLine <= passage.lastLine, "PASSAGE_LINE_RANGE", id);
    }
    require(content::sha256(passage.text) == passage.textSha256, "PASSAGE_TEXT_HASH", id);
    return passage;
}

BridgeSourceLink parseLink(const J& value, const std::string& context,
                           const std::unordered_map<std::string, BridgePassage>& passages) {
    BridgeSourceLink link;
    link.passageId = stringValue(at(value, "passage_id", context), context + "/passage_id");
    const auto& passage = [&]() -> const BridgePassage& {
        const auto found = passages.find(link.passageId);
        require(found != passages.end(), "PASSAGE_LINK_MISSING", context + "/" + link.passageId);
        return found->second;
    }();
    require(stringValue(at(value, "ref", context), context + "/ref") == link.passageId,
            "PASSAGE_REF_MISMATCH", context);
    link.path = stringValue(at(value, "path", context), context + "/path");
    link.sourceSha256 = stringValue(at(value, "source_sha256", context), context + "/source_sha256");
    link.passageSha256 = stringValue(at(value, "passage_sha256", context), context + "/passage_sha256");
    require(link.path == passage.path && link.sourceSha256 == passage.sourceSha256
                && link.passageSha256 == passage.textSha256,
            "PASSAGE_BINDING_MISMATCH", context);
    const auto& locator = at(value, "locator", context);
    if (passage.format == "txt") {
        link.lines = integerArray(at(locator, "lines", context + "/locator"), context + "/locator/lines");
        require(link.lines.size() == 2 && link.lines[0] == passage.firstLine && link.lines[1] == passage.lastLine,
                "PASSAGE_LOCATOR_MISMATCH", context);
    } else {
        link.page = static_cast<int>(integerValue(at(locator, "page", context + "/locator"), context + "/locator/page", 1, 1000));
        require(link.page == passage.page, "PASSAGE_LOCATOR_MISMATCH", context);
    }
    return link;
}

BridgeCard parseCard(const J& value, const std::string& expectedId, const std::string& expectedKind,
                     const std::unordered_map<std::string, BridgePassage>& passages) {
    const auto context = "cards/" + expectedId;
    BridgeCard card;
    card.id = stringValue(at(value, "id", context), context + "/id");
    require(card.id == expectedId, "CARD_ORDER_OR_ID", expectedId);
    card.kind = stringValue(at(value, "kind", context), context + "/kind");
    require(card.kind == expectedKind, "CARD_KIND", card.id);
    card.title = stringValue(at(value, "title", context), context + "/title");
    card.summary = stringValue(at(value, "summary", context), context + "/summary", true);
    card.availability = stringValue(at(value, "availability", context), context + "/availability");
    const auto& legacyLevel = at(value, "legacy_level", context);
    card.legacyLevel = legacyLevel.null() ? 0 : static_cast<int>(integerValue(legacyLevel, context + "/legacy_level", 1, 105));
    card.appliesToLevels = integerArray(at(value, "applies_to_levels", context), context + "/applies_to_levels");
    card.sourceRefs = stringArray(at(value, "source_refs", context), context + "/source_refs");
    card.publicSourceRefs = stringArray(at(value, "public_source_refs", context), context + "/public_source_refs");
    card.tags = stringArray(at(value, "tags", context), context + "/tags");
    card.searchTerms = stringArray(at(value, "search_terms", context), context + "/search_terms");
    card.prerequisiteLinks = stringArray(at(value, "prerequisite_links", context), context + "/prerequisite_links");
    card.requiredOutputs = stringArray(at(value, "required_outputs", context), context + "/required_outputs");
    card.selectionConstraints = stringArray(at(value, "selection_constraints", context), context + "/selection_constraints");
    card.approvedRequirementJson = json::stringify(at(value, "approved_requirement", context));
    card.runtimeAdmitted = boolValue(at(value, "runtime_admitted", context), context + "/runtime_admitted");
    card.hasSuppliedAsset = !at(value, "supplied_asset", context).null();
    const auto& preview = at(value, "preview_content", context);
    card.hasProposedPreview = !preview.null();
    if (card.hasProposedPreview) card.proposedPreviewJson = json::stringify(preview);
    card.newWordingCurriculumAccepted = boolValue(at(value, "new_wording_curriculum_accepted", context),
                                                  context + "/new_wording_curriculum_accepted");
    require(!card.runtimeAdmitted, "CARD_RUNTIME_ADMITTED", card.id);
    require(!card.hasSuppliedAsset, "CARD_SUPPLIED_ASSET", card.id);
    require(!card.newWordingCurriculumAccepted, "CARD_WORDING_ACCEPTED", card.id);
    require(at(value, "canonical_task_id", context).null(), "CARD_CANONICAL_TASK_ID", card.id);

    const auto& approved = at(value, "approved_requirement", context);
    require(stringValue(at(approved, "id", context + "/approved_requirement"), context + "/approved_requirement/id") == card.id,
            "APPROVED_ID_MISMATCH", card.id);
    require(stringValue(at(approved, "implementation_consumer", context + "/approved_requirement"),
                        context + "/approved_requirement/implementation_consumer") == "2.4.1.2.1",
            "APPROVED_CONSUMER_MISMATCH", card.id);
    require(stringArray(at(approved, "source_refs", context + "/approved_requirement"),
                        context + "/approved_requirement/source_refs") == card.sourceRefs,
            "APPROVED_SOURCE_IDENTITY_MISMATCH", card.id);
    std::vector<int> approvedLevels;
    if (const auto* levels = approved.find("levels")) {
        approvedLevels = integerArray(*levels, context + "/approved_requirement/levels");
    } else {
        approvedLevels.push_back(static_cast<int>(integerValue(
            at(approved, "level", context + "/approved_requirement"), context + "/approved_requirement/level", 1, 105)));
    }
    require(approvedLevels == card.appliesToLevels, "APPROVED_LEVELS_MISMATCH", card.id);
    card.runtimeNetwork = false;
    card.inAppImport = false;
    card.inAppRecorder = false;
    if (expectedKind == "bridge") {
        require(card.availability == "source_context_only", "BRIDGE_AVAILABILITY", card.id);
        require(!card.newWordingCurriculumAccepted, "BRIDGE_WORDING_ACCEPTED", card.id);
        require(card.hasProposedPreview == (card.id == "G04" || card.id == "G05"), "BRIDGE_PREVIEW_SET", card.id);
    } else {
        require(card.availability == "required_unsupplied", "RESOURCE_AVAILABILITY", card.id);
        require(stringValue(at(approved, "availability", context + "/approved_requirement"),
                            context + "/approved_requirement/availability") == "required_unsupplied",
                "RESOURCE_APPROVED_AVAILABILITY", card.id);
        require(!boolValue(at(approved, "runtime_network", context + "/approved_requirement"),
                           context + "/approved_requirement/runtime_network"), "RESOURCE_NETWORK_ENABLED", card.id);
        require(!boolValue(at(approved, "in_app_import", context + "/approved_requirement"),
                           context + "/approved_requirement/in_app_import"), "RESOURCE_IMPORT_ENABLED", card.id);
        require(!boolValue(at(approved, "in_app_recorder", context + "/approved_requirement"),
                           context + "/approved_requirement/in_app_recorder"), "RESOURCE_RECORDER_ENABLED", card.id);
        require(at(approved, "supplied_asset", context + "/approved_requirement").null(),
                "RESOURCE_APPROVED_SUPPLIED_ASSET", card.id);
        require(stringArray(at(approved, "required_outputs", context + "/approved_requirement"),
                            context + "/approved_requirement/required_outputs") == card.requiredOutputs,
                "RESOURCE_OUTPUTS_MISMATCH", card.id);
        require(stringArray(at(approved, "selection_constraints", context + "/approved_requirement"),
                            context + "/approved_requirement/selection_constraints") == card.selectionConstraints,
                "RESOURCE_CONSTRAINTS_MISMATCH", card.id);
        card.runtimeNetwork = boolValue(at(approved, "runtime_network", context + "/approved_requirement"),
                                        context + "/approved_requirement/runtime_network");
        card.inAppImport = boolValue(at(approved, "in_app_import", context + "/approved_requirement"),
                                     context + "/approved_requirement/in_app_import");
        card.inAppRecorder = boolValue(at(approved, "in_app_recorder", context + "/approved_requirement"),
                                       context + "/approved_requirement/in_app_recorder");
    }
    require(!card.runtimeNetwork && !card.inAppImport && !card.inAppRecorder, "CARD_CAPABILITY_ENABLED", card.id);

    const auto& links = at(value, "source_links", context);
    require(links.isArray() && !links.array().empty(), "CARD_SOURCE_LINKS", card.id);
    std::set<std::string> linkRefs;
    for (std::size_t i = 0; i < links.array().size(); ++i) {
        auto link = parseLink(links.array()[i], context + "/source_links/" + std::to_string(i), passages);
        require(linkRefs.insert(link.passageId).second, "DUPLICATE_SOURCE_LINK", card.id);
        card.sourceLinks.push_back(std::move(link));
    }
    const std::set<std::string> refs(card.sourceRefs.begin(), card.sourceRefs.end());
    for (const auto& ref : refs)
        require(linkRefs.count(ref) != 0, "CARD_SOURCE_IDENTITY_MISMATCH", card.id + "/" + ref);
    for (const auto& ref : card.publicSourceRefs)
        require(linkRefs.count(ref) != 0, "CARD_PUBLIC_SOURCE_IDENTITY_MISMATCH", card.id + "/" + ref);
    return card;
}

} // namespace

BridgeResourceCatalog BridgeResourceCatalog::load(const std::filesystem::path& bundleRoot,
                                                   const std::filesystem::path& sourceRoot) {
    const auto bundle = checkedRoot(bundleRoot, "bundle");
    const auto sources = checkedRoot(sourceRoot, "source");
    const std::set<std::string> expectedFiles{"manifest.json", "cards.json", "source-passages.json"};
    require(actualFiles(bundle) == expectedFiles, "BUNDLE_FILE_SET");

    const auto manifestBytes = readFile(bundle, "manifest.json", kJsonLimit, "MANIFEST_READ");
    const auto manifest = parseJson(manifestBytes, "manifest.json");
    require(stringValue(at(manifest, "version", "manifest"), "manifest/version") == "bridge-resource-bundle.1",
            "MANIFEST_VERSION");
    require(boolValue(at(manifest, "offline", "manifest"), "manifest/offline"), "OFFLINE_FLAG_FALSE");
    require(!boolValue(at(manifest, "runtime_admitted", "manifest"), "manifest/runtime_admitted"),
            "RUNTIME_ADMISSION_TRUE");
    require(boolValue(at(manifest, "future_reader_required", "manifest"), "manifest/future_reader_required"),
            "READER_REQUIREMENT_FLAG");
    require(stringValue(at(manifest, "lesson_bundle_schema", "manifest"), "manifest/lesson_bundle_schema") == "lesson-bundle.1",
            "LESSON_BUNDLE_SCHEMA");
    requireExactStringArray(at(manifest, "bridge_ids", "manifest"), kBridgeIds, "BRIDGE_ID_SET");
    requireExactStringArray(at(manifest, "resource_ids", "manifest"), kResourceIds, "RESOURCE_ID_SET");
    require(at(manifest, "supplied_assets", "manifest").isArray()
                && at(manifest, "supplied_assets", "manifest").array().empty(),
            "MANIFEST_SUPPLIED_ASSETS");
    const auto& fileRefs = at(manifest, "files", "manifest");
    require(fileRefs.isArray() && fileRefs.array().size() == 2, "MANIFEST_FILE_LIST");

    std::unordered_map<std::string, std::pair<std::size_t, std::string>> descriptors;
    for (const auto& fileRef : fileRefs.array()) {
        const auto name = stringValue(at(fileRef, "path", "manifest/files"), "manifest/files/path");
        require(name == "cards.json" || name == "source-passages.json", "MANIFEST_FILE_PATH", name);
        const auto size = static_cast<std::size_t>(integerValue(at(fileRef, "bytes", "manifest/files"), "manifest/files/bytes", 1, kJsonLimit));
        const auto hash = stringValue(at(fileRef, "sha256", "manifest/files"), "manifest/files/sha256");
        require(descriptors.emplace(name, std::make_pair(size, hash)).second, "MANIFEST_DUPLICATE_FILE", name);
    }
    require(descriptors.size() == 2, "MANIFEST_FILE_LIST");

    const auto cardBytes = readFile(bundle, "cards.json", kJsonLimit, "CARDS_READ");
    const auto passageBytes = readFile(bundle, "source-passages.json", kJsonLimit, "PASSAGES_READ");
    const auto cardsJson = parseJson(cardBytes, "cards.json");
    const auto passagesJson = parseJson(passageBytes, "source-passages.json");
    require(stringValue(at(cardsJson, "version", "cards"), "cards/version") == "bridge-resource-cards.1",
            "CARDS_VERSION");
    require(stringValue(at(passagesJson, "version", "passages"), "passages/version") == "bridge-source-passages.1",
            "PASSAGES_VERSION");
    require(!boolValue(at(passagesJson, "search_indexed", "passages"), "passages/search_indexed"),
            "PASSAGE_TEXT_SEARCH_ENABLED");

    std::unordered_map<std::string, BridgePassage> passageMap;
    const auto& passageObject = at(passagesJson, "passages", "passages");
    require(passageObject.isObject() && passageObject.object().size() == kExpectedPassages,
            "PASSAGE_COUNT", std::to_string(kExpectedPassages));
    for (const auto& [id, value] : passageObject.object()) {
        auto passage = parsePassage(id, value);
        require(passageMap.emplace(id, std::move(passage)).second, "DUPLICATE_PASSAGE", id);
    }

    const auto& cardArray = at(cardsJson, "cards", "cards");
    require(cardArray.isArray() && cardArray.array().size() == kBridgeIds.size() + kResourceIds.size(),
            "CARD_COUNT");
    BridgeResourceCatalog catalog;
    catalog.offline_ = true;
    catalog.runtimeAdmitted_ = false;
    std::set<std::string> linkedPassageIds;
    std::size_t sourceLinkCount = 0;
    std::size_t position = 0;
    for (const auto& id : kBridgeIds) {
        auto card = parseCard(cardArray.array()[position++], id, "bridge", passageMap);
        for (const auto& link : card.sourceLinks) {
            linkedPassageIds.insert(link.passageId);
            ++sourceLinkCount;
        }
        catalog.cards_.push_back(std::move(card));
    }
    for (const auto& id : kResourceIds) {
        auto card = parseCard(cardArray.array()[position++], id, "resource", passageMap);
        for (const auto& link : card.sourceLinks) {
            linkedPassageIds.insert(link.passageId);
            ++sourceLinkCount;
        }
        catalog.cards_.push_back(std::move(card));
    }
    require(sourceLinkCount == kExpectedSourceLinks, "SOURCE_LINK_COUNT");
    require(linkedPassageIds.size() == kExpectedLinkedPassages, "LINKED_PASSAGE_COUNT");

    // The sealed passage file contains 43 source excerpts, including passages
    // not selected for public card search. Verify every source path and digest.
    std::unordered_map<std::string, std::string> verifiedSources;
    for (const auto& [id, passage] : passageMap) {
        const auto source = verifiedSources.find(passage.path);
        if (source == verifiedSources.end()) {
            auto sourceBytes = readFile(sources, passage.path, kSourceLimit, "SOURCE_FILE_READ");
            const auto sourceHash = content::sha256(sourceBytes);
            require(sourceHash == passage.sourceSha256, "SOURCE_FILE_HASH", passage.path);
            verifiedSources.emplace(passage.path, std::move(sourceBytes));
        } else {
            require(content::sha256(source->second) == passage.sourceSha256, "SOURCE_FILE_HASH", passage.path);
        }
    }
    catalog.verifiedPassageCount_ = passageMap.size();
    require(catalog.verifiedPassageCount_ == kExpectedPassages, "PASSAGE_COUNT");
    for (const auto& id : linkedPassageIds) catalog.passages_.push_back(passageMap.at(id));

    const auto& bindingObject = at(manifest, "source_bindings", "manifest");
    require(bindingObject.isObject() && bindingObject.object().size() == 5, "SOURCE_BINDING_COUNT");
    for (const auto& [name, digestValue] : bindingObject.object()) {
        const auto expectedHash = stringValue(digestValue, "manifest/source_bindings/" + name);
        const auto bytes = readFile(sources, name, kSourceLimit, "BOUND_SOURCE_READ");
        require(content::sha256(bytes) == expectedHash, "BOUND_SOURCE_HASH", name);
        catalog.sourceBindings_.push_back({name, expectedHash});
    }

    for (const auto& [name, descriptor] : descriptors) {
        const auto& bytes = name == "cards.json" ? cardBytes : passageBytes;
        require(bytes.size() == descriptor.first, "BUNDLE_FILE_SIZE", name);
        require(content::sha256(bytes) == descriptor.second, "BUNDLE_FILE_HASH", name);
    }
    require(content::sha256(manifestBytes) == kManifestSha256, "MANIFEST_HASH");
    return catalog;
}

const BridgeCard* BridgeResourceCatalog::find(const std::string& id) const noexcept {
    const auto found = std::find_if(cards_.begin(), cards_.end(), [&id](const BridgeCard& card) { return card.id == id; });
    return found == cards_.end() ? nullptr : &*found;
}

const BridgePassage* BridgeResourceCatalog::findPassage(const std::string& id) const noexcept {
    const auto found = std::find_if(passages_.begin(), passages_.end(), [&id](const BridgePassage& passage) { return passage.id == id; });
    return found == passages_.end() ? nullptr : &*found;
}

std::vector<std::string> BridgeResourceCatalog::search(const std::string& query) const {
    const auto needle = lowerAscii(query);
    if (needle.empty()) return {};
    std::vector<std::string> result;
    for (const auto& card : cards_)
        if (joinForSearch(card).find(needle) != std::string::npos) result.push_back(card.id);
    std::sort(result.begin(), result.end());
    return result;
}

} // namespace fathom::content
