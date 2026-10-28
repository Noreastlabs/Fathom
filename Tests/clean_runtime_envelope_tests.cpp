#include "content/Canonical.hpp"
#include "content/CleanRuntimeEnvelope.hpp"
#include "content/SelectedCatalogStore.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace fathom;
namespace {
namespace fs = std::filesystem;
int checks = 0;
void check(bool value, const char *why) {
    ++checks;
    if (!value)
        throw std::runtime_error(why);
}
template <class F> void refuses(F action, const char *why) {
    bool failed = false;
    try {
        action();
    } catch (const std::exception &) {
        failed = true;
    }
    check(failed, why);
}
void write(const fs::path &path, const std::string &bytes) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    out.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    if (!out)
        throw std::runtime_error("Fixture write failed");
}
struct Scratch {
    fs::path parent, root;
    Scratch(const fs::path &source) {
        parent = fs::canonical(fs::temp_directory_path()) /
                 ("fathom-clean-envelope-" +
                  std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
        if (!fs::create_directory(parent))
            throw std::runtime_error("Fresh fixture required");
        root = parent / "runtime";
        fs::copy(source, root, fs::copy_options::recursive);
    }
    ~Scratch() {
        std::error_code ec;
        fs::remove_all(parent, ec);
    }
};
} // namespace
int main(int argc, char **argv) {
    try {
        if (argc != 2)
            throw std::runtime_error("Exact clean runtime root required");
        Scratch scratch(fs::canonical(argv[1]));
        const auto root = scratch.root, package = root / "level001-extension";
        const auto logical =
            content::sha256(content::readBounded(package / "manifest.json", 1024 * 1024));
        const auto metadataPath = root / "clean-runtime-manifest.json";
        const auto metadataBytes = content::readBounded(metadataPath, 2 * 1024 * 1024);
        const auto metadata = json::parse(metadataBytes);
        const auto cap = content::CleanRuntimeEnvelope::open(package, logical);
        check(static_cast<bool>(cap), "Pinned clean package refused");
        std::string predecessor, predecessorSha, proof, proofSha, retained;
        for (const auto &item : metadata.object().at("archived_evidence").object())
            if (item.first.rfind("level001-extension/", 0) == 0) {
                const auto local = item.first.substr(std::string("level001-extension/").size());
                if (item.second.object().at("role").string() == "predecessor_validation") {
                    predecessor = local;
                    predecessorSha = item.second.object().at("sha256").string();
                } else if (proof.empty()) {
                    proof = local;
                    proofSha = item.second.object().at("sha256").string();
                }
            }
        for (const auto &item : metadata.object().at("retained_files").object())
            if (item.first.rfind("level001-extension/", 0) == 0 &&
                fs::path(item.first).extension() == ".txt") {
                retained = item.first.substr(std::string("level001-extension/").size());
                break;
            }
        check(!predecessor.empty() && !proof.empty() && !retained.empty(),
              "Fixture proof coverage missing");
        const auto dto = cap->readSemanticProjection(predecessor, predecessorSha);
        check(dto.validReference && !dto.records.array().empty(), "Typed predecessor unavailable");
        cap->verifyArchivedEvidence(proof, proofSha);
        check(true, "Archived integrity reference refused");
        refuses([&] { cap->readSemanticProjection(proof, proofSha); },
                "Authority prose promoted to semantic report");
        refuses([&] { cap->readSemanticProjection(retained, proofSha); },
                "Raw source promoted to semantic report");
        refuses([&] { cap->verifyArchivedEvidence("../escape", proofSha); },
                "Archive traversal accepted");
        refuses([&] { cap->verifyArchivedEvidence(proof, std::string(64, '0')); },
                "Wrong archived identity accepted");
        refuses([&] { cap->verifyArchivedEvidence(proof, proofSha, 0); },
                "Wrong archived byte identity accepted");
        refuses([&] { content::readBounded(package / proof, 32 * 1024 * 1024); },
                "Archived original bytes fabricated");
        const auto outside = scratch.parent / "outside.txt";
        write(outside, "outside");
        refuses([&] { cap->verifyPayload(outside, "outside"); },
                "Outside physical payload accepted");
        const auto oldKey = std::string("level001-extension/") + predecessor;
        const auto projectionPath = root / metadata.object()
                                               .at("semantic_projections")
                                               .object()
                                               .at(oldKey)
                                               .object()
                                               .at("path")
                                               .string();
        const auto projectionBytes = content::readBounded(projectionPath, 32 * 1024 * 1024);
        write(projectionPath, projectionBytes + " ");
        refuses([&] { cap->readSemanticProjection(predecessor, predecessorSha); },
                "Changed-after-open projection accepted");
        write(projectionPath, projectionBytes);
        write(metadataPath, metadataBytes + " ");
        refuses([&] { cap->verifyState(); }, "Changed-after-open manifest accepted");
        refuses([&] { cap->verifyArchivedEvidence(proof, proofSha); },
                "Changed manifest retained archive authority");
        refuses([&] { cap->readSemanticProjection(predecessor, predecessorSha); },
                "Changed manifest retained semantic authority");
        write(metadataPath, metadataBytes);
        const auto moved = scratch.parent / "moved";
        fs::rename(root, moved);
        fs::create_directory_symlink(moved, root);
        refuses([&] { cap->verifyState(); }, "Post-open root symlink accepted");
        refuses([&] { cap->readSemanticProjection(predecessor, predecessorSha); },
                "Projection traversed post-open root symlink");
        fs::remove(root);
        fs::rename(moved, root);
        const auto extra = root / "unlisted.txt";
        write(extra, "extra");
        refuses([&] { cap->verifyState(); }, "Unlisted physical file accepted");
        fs::remove(extra);
        const auto archived = package / proof;
        fs::create_directories(archived.parent_path());
        fs::create_symlink(scratch.parent / "does-not-exist", archived);
        refuses([&] { cap->verifyArchivedEvidence(proof, proofSha); },
                "Dangling archived symlink accepted");
        fs::remove(archived);
        const auto ancestor = archived.parent_path(),
                   savedAncestor = scratch.parent / "saved-archive-parent",
                   outsideDirectory = scratch.parent / "outside-directory";
        fs::create_directory(outsideDirectory);
        fs::rename(ancestor, savedAncestor);
        fs::create_directory_symlink(outsideDirectory, ancestor);
        refuses([&] { cap->verifyArchivedEvidence(proof, proofSha); },
                "Post-open archived ancestor symlink accepted");
        fs::remove(ancestor);
        fs::rename(savedAncestor, ancestor);
        // Raw authoring validation never acquires installed-runtime archival authority.
        const auto baseRoot = root / "representative-controls";
        const auto baseManifest =
            json::parse(content::readBounded(baseRoot / "manifest.json", 1024 * 1024));
        const auto &entries = baseManifest.object().at("entries");
        const auto packet = content::readBounded(baseRoot / entries.object().at("package").string(),
                                                 32 * 1024 * 1024);
        const auto registry = content::readBounded(
            baseRoot / entries.object().at("registry").string(), 32 * 1024 * 1024);
        const auto profile = content::readBounded(
            baseRoot / entries.object().at("profile").string(), 32 * 1024 * 1024);
        const auto raw =
            content::validate({packet, registry, profile, content::sha256(profile), baseRoot});
        check(!raw.validReference && raw.exitCode == 1,
              "Raw validator fabricated absent archival proof");
        // Reusing models still requires current transport and physical byte checks.
        std::vector<fs::path> extensions;
        for (const auto &name : lesson::Catalog::installedExtensionDirectoryNames())
            extensions.push_back(root / name);
        lesson::SelectedCatalogStore store(root / "representative-controls", extensions);
        const std::vector<lesson::SelectedCatalogStore::Request> request{{"fg:item:000002", {}}};
        check(static_cast<bool>(store.prepare(request)), "Initial selected catalog failed");
        check(static_cast<bool>(store.prepare(request)) &&
                  store.lastPreparation().memoryCacheHits > 0,
              "Warm selected catalog not verified");
        write(projectionPath, projectionBytes + " ");
        refuses([&] { store.prepare(request); }, "Cached model survived projection tamper");
        write(projectionPath, projectionBytes);
        fs::rename(metadataPath, root / "missing-manifest");
        refuses([&] { content::CleanRuntimeEnvelope::open(package, logical); },
                "Missing transport manifest accepted");
        fs::rename(root / "missing-manifest", metadataPath);
        const auto payload = package / retained;
        const auto payloadBytes = content::readBounded(payload, 32 * 1024 * 1024);
        write(payload, payloadBytes + " ");
        refuses([&] { cap->verifyPayload(payload, payloadBytes + " "); },
                "Changed physical source bytes accepted");
        refuses([&] { content::CleanRuntimeEnvelope::open(package, logical); },
                "Tampered package opened");
        write(payload, payloadBytes);
        check(static_cast<bool>(content::CleanRuntimeEnvelope::open(package, logical)),
              "Restored fixture failed");
        std::cout << "PASS clean runtime envelope checks=" << checks
                  << "; no original/profile/native/audio access\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL after " << checks << ": " << e.what() << '\n';
        return 1;
    }
}
