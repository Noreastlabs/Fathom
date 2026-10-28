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
        if (argc != 21) throw std::runtime_error("Expected base, seventeen prior extensions, Level20 and fresh output");
        const std::filesystem::path base = argv[1], out = argv[20];
        if (!out.is_absolute() || std::filesystem::exists(out)) throw std::runtime_error("Fresh absolute output required");
        std::filesystem::create_directories(out);
        std::ofstream trace(out / "checks.tsv");
        auto ck = [&](bool good, const std::string& label) {
            ++checks; trace << label << '\t' << (good ? "PASS" : "FAIL") << '\n';
            if (!good) throw std::runtime_error(label);
        };
        auto refuses = [&](auto action, const std::string& label) {
            bool denied = false; try { action(); } catch (const std::exception&) { denied = true; }
            ck(denied, label);
        };
        std::vector<std::filesystem::path> prior;
        for (int i = 2; i <= 18; ++i) prior.emplace_back(argv[i]);
        auto withNew = prior; withNew.emplace_back(argv[19]);
        const auto old = lesson::Catalog::loadInstalled(base, prior);
        const auto current = lesson::Catalog::loadInstalled(base, withNew);
        ck(old->lessons().size() == 39 && current->lessons().size() == 40 &&
           old->sourceEntryCount() == 140 && current->sourceEntryCount() == 150,
           "one exact case and ten source keys added once");
        const auto installedOrder = lesson::Catalog::installedExtensionDirectoryNames();
        ck(installedOrder.size() >= 18 &&
           std::vector<std::string>(installedOrder.begin(), installedOrder.begin() + 18) == std::vector<std::string>{
            "rung02-extension", "rung03-extension", "rung04-extension", "level006-extension",
            "rung05-extension", "level008-extension", "level010-extension", "level007-extension",
            "level009-extension", "level011-extension", "level013-extension", "level014-extension",
            "level015-extension", "level016-extension", "level017-extension", "level018-extension",
            "level019-extension", "level020-extension"}, "exact historical Level20 extension prefix");
        std::size_t priorVariants = 0;
        for (const auto& item : old->lessons()) {
            ck(item.record == current->lesson(item.id).record &&
               old->contentVersion(item.id) == current->contentVersion(item.id),
               "prior authored case/version preserved " + item.id);
            for (const auto& variant : item.variants) {
                ++priorVariants;
                ck(variant.authored == current->variant(item.id, variant.id).authored,
                   "prior authored variant preserved " + variant.id);
                try {
                    const auto a = old->admit(item.id, variant.id);
                    const auto b = current->admit(item.id, variant.id);
                    ck(a->identity() == b->identity() && a->sourceBinding() == b->sourceBinding() &&
                       a->span() == b->span(), "prior runtime admission preserved " + variant.id);
                } catch (const std::exception&) {
                    refuses([&] { current->admit(item.id, variant.id); },
                            "prior nonadmission preserved " + variant.id);
                }
            }
        }
        ck(priorVariants == 101, "all 101 prior variants accounted for");
        const auto manifest = json::parse(content::readBounded(withNew.back() / "manifest.json", 1024 * 1024));
        const auto& entries = manifest.object().at("entries").object();
        const auto packet = json::parse(content::readBounded(withNew.back() / entries.at("package").string(), 32 * 1024 * 1024));
        ck(packet.object().at("records").array().size() == 1 && packet.object().at("sources").object().size() == 10,
           "exact native-validated one-case ten-source packet");
        const auto& source = packet.object().at("records").array().front().object();
        const std::string item = "fg:item:001167";
        const std::array<std::string, 2> variants{"fg:variant:007456", "fg:variant:007457"};
        const auto& selected = current->lesson(item);
        ck(selected.title.find("322-contact") != std::string::npos,
           "Learn identifies complete first A-major circuit only");
        for (std::size_t v = 0; v < variants.size(); ++v) {
            const auto token = current->admit(item, variants[v]);
            ck(token->practiceAllowed() && token->span() == Rational{322} &&
               !token->identity().object().at("whole_task_completion").boolean(),
               "exact q322 Practice admission without whole-workbook credit");
            const auto& identity = token->identity().object();
            ck(identity.at("bundle_sha256") == json::Value("fbdcafadb070ef66e5acea75ff48da0d6b65b5ea5a835a60db9ae5d6ad01fb87") &&
               identity.at("content_version") == json::Value("curriculum-v1-level020-a-full-circuit-build-only.1") &&
               identity.at("item_id") == json::Value(item) && identity.at("variant_id") == json::Value(variants[v]) &&
               identity.at("source_refs") == source.at("source_refs"),
               "exact installed source, version, bundle and variant identity");
            const auto& events = token->model()->source().events;
            ck(events.size() == 322, "all 322 ordered contacts loaded");
            for (std::size_t i = 0; i < events.size(); ++i) {
                const auto& event = events[i];
                const auto& authored = source.at("events").array()[i].object();
                ck(event.kind == music::Kind::Note && event.span.onset == Rational{static_cast<std::int64_t>(i)} &&
                   event.span.duration == Rational{1} && event.tones.size() == 1 &&
                   json::Value::fromInteger(event.tones[0].string) == authored.at("string") &&
                   json::Value::fromInteger(event.tones[0].fret) == authored.at("fret") &&
                   json::Value::fromInteger(event.tones[0].midi) == authored.at("midi") &&
                   event.handDirection == (((i % 2 == 0) == (v == 0)) ? "D" : "U"),
                   "exact picked q1 contact, pitch, stroke " + std::to_string(i + 1));
            }
            for (std::size_t seam : {30u, 108u, 204u, 256u})
                ck(events[seam - 1].span.onset.value() + events[seam - 1].span.duration.value() ==
                       events[seam].span.onset.value() &&
                   events[seam].tones[0].string == 1 && events[seam].tones[0].fret == 5,
                   "immediate low-root re-articulation after contact " + std::to_string(seam));
        }
        refuses([&] { current->admit(item, "fg:variant:007455"); }, "foreign Level19 variant refused");
        refuses([&] { current->admit("fg:item:001166", variants[0]); }, "Level20 variant on old case refused");
        refuses([&] { lesson::Catalog::loadInstalled(base, {withNew.back()}); }, "missing prior extension sequence refused");
        auto missing = prior; missing.push_back(out / "missing-level020");
        refuses([&] { lesson::Catalog::loadInstalled(base, missing); }, "missing atomic Level20 bundle refused");
        const auto altered = out / "mutable-level020";
        std::filesystem::copy(withNew.back(), altered, std::filesystem::copy_options::recursive);
        auto changed = prior; changed.push_back(altered);
        const auto packagePath = altered / entries.at("package").string();
        const auto originalBytes = content::readBounded(packagePath, 32 * 1024 * 1024);
        for (const auto* fault : {"onset", "duration", "pitch", "degree", "event-count"}) {
            auto candidate = json::parse(originalBytes);
            auto& eventArray = candidate.object().at("records").array()[0].object().at("events").array();
            if (std::string(fault) == "onset") eventArray[30].object()["onset_q"] = json::parse("[29,1]");
            else if (std::string(fault) == "duration") eventArray[108].object()["duration_q"] = json::parse("[2,1]");
            else if (std::string(fault) == "pitch") eventArray[204].object()["fret"] = json::Value::fromInteger(6);
            else if (std::string(fault) == "degree") eventArray[256].object()["degree_contexts"].object()["A-major"].object()["ordinal"] = json::Value::fromInteger(2);
            else eventArray.pop_back();
            { std::ofstream write(packagePath, std::ios::binary); write << json::stringify(candidate); }
            refuses([&] { lesson::Catalog::loadInstalled(base, changed); },
                    std::string("changed ") + fault + " refused by frozen manifest");
            { std::ofstream write(packagePath, std::ios::binary); write << originalBytes; }
        }
        std::ofstream(out / "summary.json") << "{\"status\":\"PASS\",\"checks\":" << checks
            << ",\"cases\":1,\"attempts\":0,\"physical_listening\":false}\n";
        std::cout << "PASS " << checks << " Level20 source-backed q322 Catalog checks\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FAIL after " << checks << ": " << e.what() << '\n';
        return 1;
    }
}
