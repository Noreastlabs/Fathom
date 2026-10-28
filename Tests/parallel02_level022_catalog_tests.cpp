#include "content/LessonCatalog.hpp"
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

using namespace fathom;

int main(int argc, char** argv) {
    int checks = 0;
    try {
        if (argc != 23) throw std::runtime_error("Expected base, nineteen prior extensions, Level22 and fresh output");
        const std::filesystem::path base = argv[1], out = argv[22];
        if (!out.is_absolute() || std::filesystem::exists(out))
            throw std::runtime_error("Fresh absolute output required");
        std::filesystem::create_directories(out);
        std::ofstream trace(out / "checks.tsv");
        auto ck = [&](bool ok, const std::string& name) {
            ++checks; trace << name << '\t' << (ok ? "PASS" : "FAIL") << std::endl;
            if (!ok) throw std::runtime_error(name);
        };
        auto refuses = [&](auto action, const std::string& name) {
            bool denied = false;
            try { action(); } catch (const std::exception&) { denied = true; }
            ck(denied, name);
        };
        std::vector<std::filesystem::path> prior;
        for (int i = 2; i <= 20; ++i) prior.emplace_back(argv[i]);
        auto currentPaths = prior;
        currentPaths.emplace_back(argv[21]);
        const auto old = lesson::Catalog::loadInstalled(base, prior);
        const auto current = lesson::Catalog::loadInstalled(base, currentPaths);
        ck(old->lessons().size() == 43 && current->lessons().size() == 44 &&
               old->sourceEntryCount() == 157 && current->sourceEntryCount() == 163,
               "one pair and six unique source keys added");
        const auto installedOrder = lesson::Catalog::installedExtensionDirectoryNames();
        ck(installedOrder.size() == 21 && installedOrder[19] == "level022-extension" &&
               installedOrder.back() == "level023-extension",
               "finite Level22 historical extension position preserved after Level23");
        std::size_t priorVariants = 0;
        for (const auto& selected : old->lessons()) {
            const auto& now = current->lesson(selected.id);
            ck(now.title == selected.title &&
                   now.variants.size() == selected.variants.size() &&
                   current->contentVersion(selected.id) == old->contentVersion(selected.id),
                   "prior case title, variants and version preserved " + selected.id);
            for (const auto& variant : selected.variants) {
                ++priorVariants;
                ck(variant.authored == current->variant(selected.id, variant.id).authored,
                   "prior authored variant preserved " + variant.id);
                try {
                    const auto a = old->admit(selected.id, variant.id);
                    const auto b = current->admit(selected.id, variant.id);
                    ck(a->identity() == b->identity() && a->sourceBinding() == b->sourceBinding() &&
                           a->span() == b->span(), "prior admission and gap preserved " + variant.id);
                } catch (const std::exception&) {
                    refuses([&] { current->admit(selected.id, variant.id); },
                            "prior refusal preserved " + variant.id);
                }
            }
        }
        ck(priorVariants == 109, "all prior variants accounted for");
        const std::string item = "fg:item:001171";
        const std::array<std::string, 2> variants{"fg:variant:007464", "fg:variant:007465"};
        const auto& selected = current->lesson(item);
        ck(selected.title.find("60-contact") != std::string::npos &&
               current->admit(item, variants.front())->description().find("one-beat") != std::string::npos,
               "Learn identifies the exact neighboring pair and pause");
        const auto manifest = json::parse(content::readBounded(currentPaths.back() / "manifest.json", 1024 * 1024));
        const auto package = json::parse(content::readBounded(
            currentPaths.back() / manifest.object().at("entries").object().at("package").string(),
            32 * 1024 * 1024));
        for (std::size_t pick = 0; pick < variants.size(); ++pick) {
            const auto token = current->admit(item, variants[pick]);
            ck(token->practiceAllowed() && token->span() == Rational{31} &&
                   !token->identity().object().at("whole_task_completion").boolean(),
                   "exact q31 pair span, runtime permission and no whole-task credit");
            const auto& identity = token->identity().object();
            ck(identity.at("bundle_sha256") == json::Value("ac8020af955cef93d8f2aa886edad93bd440e4b5c64b038a2e3f332b6f13df44") &&
                   identity.at("package_sha256") == json::Value("6d009fdbd4ac1e290ee121178a5d04648aa718822ba84a9c0ecad06bcd1f7be2") &&
                   identity.at("content_version") == json::Value("curriculum-v1-level022-first-neighbor-pair-build-only.1") &&
                   identity.at("source_refs") == json::parse(R"(["L22-TXT-GUIDANCE","L22-PDF-GUIDANCE","L22-PDF-ROUTE","L22-TXT-RUNG01","L22-TXT-RUNG02","L22-PDF-CARDS01-02"])") &&
                   identity.at("source_hashes").object().at("L22-TXT-GUIDANCE") ==
                       json::Value("0031bdd05834d1f1f381240a48a5fa193da561f7bdf51df580771f593c82b1dc") &&
                   identity.at("source_hashes").object().at("L22-PDF-ROUTE") ==
                       json::Value("f07518814be26b8290c6b9a688251eb77fd2b2aedb8efc03a0469167d8be7bde"),
                   "installed bundle, original sources and case version pinned");
            const auto& events = token->model()->source().events;
            ck(events.size() == 60, "sixty exact picked contacts");
            for (std::size_t i = 0; i < events.size(); ++i) {
                const auto& event = events[i];
                const auto& tone = event.tones.at(0);
                const auto& authored = package.object().at("records").array().front()
                                           .object().at("events").array()[i].object();
                const auto onset = lesson::installedCaseOnset(Rational{1, 2}, i, 30, Rational{1});
                ck(event.kind == music::Kind::Note && event.span.onset == onset &&
                       event.span.duration == Rational{1, 2} && event.tones.size() == 1 &&
                       json::Value::fromInteger(tone.string) == authored.at("string") &&
                       json::Value::fromInteger(tone.fret) == authored.at("fret") &&
                       json::Value::fromInteger(tone.midi) == authored.at("midi") &&
                       event.handDirection == (((i % 2 == 0) == (pick == 0)) ? "D" : "U"),
                   "exact original contact, gap onset and continuous pick " + std::to_string(i + 1));
            }
        }
        ck(lesson::installedCaseOnset(Rational{1, 2}, 29, 30, Rational{1}) == Rational{29, 2} &&
               lesson::installedCaseOnset(Rational{1, 2}, 30, 30, Rational{1}) == Rational{16} &&
               lesson::installedCaseOnset(Rational{1, 2}, 59, 30, Rational{1}) == Rational{61, 2},
               "source [15,16) rest precedes Bb contact31 and ends at q31");
        ck(lesson::validInstalledGaps(60, 30, 1, 1, 0, 0, 1) &&
               lesson::validInstalledGaps(60, 0, 0, 1, 0, 0, 1),
               "reviewed one-gap and old zero-gap structures remain valid");
        for (const auto& bad : std::array<std::array<std::int64_t, 3>, 7>{{
                 {{0, 1, 1}}, {{30, 0, 1}}, {{30, -1, 1}}, {{30, 1, 0}},
                 {{30, 1, -1}}, {{60, 1, 1}}, {{61, 1, 1}}}})
            ck(!lesson::validInstalledGaps(60, static_cast<std::size_t>(bad[0]), bad[1], bad[2], 0, 0, 1),
               "zero, negative or out-of-range gap refused");
        for (const auto wrong : std::array<Rational, 3>{Rational{0}, Rational{1, 2}, Rational{2}})
            ck(!(lesson::installedCaseOnset(Rational{1, 2}, 30, 30, wrong) == Rational{16}),
               "missing, short or long pause cannot match Bb source onset");
        refuses([&] { current->admit(item, "fg:variant:007463"); }, "foreign variant refused");
        refuses([&] { lesson::Catalog::loadInstalled(base, {currentPaths.back()}); },
                "partial extension set refused");
        auto missing = prior; missing.push_back(out / "missing-level022");
        refuses([&] { lesson::Catalog::loadInstalled(base, missing); }, "missing Level22 bundle refused");
        const auto altered = out / "altered-level022";
        std::filesystem::copy(currentPaths.back(), altered, std::filesystem::copy_options::recursive);
        auto changed = prior; changed.push_back(altered);
        const auto packagePath = altered / manifest.object().at("entries").object().at("package").string();
        const auto originalBytes = content::readBounded(packagePath, 32 * 1024 * 1024);
        for (const auto* fault : {"missing-gap", "wrong-onset", "wrong-identity", "missing-event"}) {
            auto candidate = json::parse(originalBytes);
            auto& record = candidate.object().at("records").array().front().object();
            auto& events = record.at("events").array();
            if (std::string(fault) == "missing-gap") events[30].object()["onset_q"] = json::parse("[15,1]");
            else if (std::string(fault) == "wrong-onset") events[30].object()["onset_q"] = json::parse("[33,2]");
            else if (std::string(fault) == "wrong-identity") record["id"] = "fg:item:001172";
            else events.pop_back();
            { std::ofstream write(packagePath, std::ios::binary); write << json::stringify(candidate); }
            refuses([&] { lesson::Catalog::loadInstalled(base, changed); },
                    std::string("changed ") + fault + " refused");
            { std::ofstream write(packagePath, std::ios::binary); write << originalBytes; }
        }
        std::ofstream(out / "summary.json") << "{\"status\":\"PASS\",\"checks\":" << checks
                                             << ",\"cases\":1,\"physical_listening\":false}\n";
        std::cout << "PASS " << checks << " Level22 source-backed one-pair Catalog/gap checks\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FAIL after " << checks << ": " << e.what() << '\n';
        return 1;
    }
}
