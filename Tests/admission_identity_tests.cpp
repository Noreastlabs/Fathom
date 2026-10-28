// Baseline captured from the immutable full-private source loader, not new metadata.
#include "content/LessonCatalog.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
int main(int argc, char **argv) {
    try {
        if (argc != 2)
            throw std::runtime_error("runtime root required");
        const auto root = std::filesystem::canonical(argv[1]);
        std::vector<std::filesystem::path> extensions;
        for (const auto &name : fathom::lesson::Catalog::installedExtensionDirectoryNames())
            extensions.push_back(root / name);
        const auto catalog =
            fathom::lesson::Catalog::loadInstalled(root / "representative-controls", extensions);
        using J = fathom::json::Value;
        J::Object admissions, cases;
        J::Array refused;
        for (const auto &lesson : catalog->lessons()) {
            J::Object variants;
            for (const auto &v : lesson.variants) {
                const auto key = lesson.id + "/" + v.id;
                variants.emplace(
                    v.id, J::Object{{"authored_sha256",
                                     fathom::content::sha256(fathom::json::stringify(v.authored))},
                                    {"technically_renderable", v.technicallyRenderable}});
                try {
                    const auto a = catalog->admit(lesson.id, v.id);
                    if (a && a->practiceAllowed())
                        admissions.emplace(key, a->identity());
                    else
                        refused.emplace_back(key);
                } catch (const std::exception &) {
                    refused.emplace_back(key);
                }
            }
            cases.emplace(lesson.id,
                          J::Object{{"record_sha256", fathom::content::sha256(
                                                          fathom::json::stringify(lesson.record))},
                                    {"content_version", catalog->contentVersion(lesson.id)},
                                    {"variants", variants}});
        }
        const auto snapshot =
            fathom::json::stringify(
                J::Object{{"cases", cases}, {"admissions", admissions}, {"refused", refused}}) +
            "\n";
        if (fathom::content::sha256(snapshot) !=
            "11d80e8eef1c95622e2fb5a87990b2827a816a795031946e85dbcb9efd4b754e")
            throw std::runtime_error("Legacy admission/model identity snapshot differs");
        std::cout << "cases=" << cases.size() << " admissions=" << admissions.size()
                  << " refused=" << refused.size() << '\n';
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
