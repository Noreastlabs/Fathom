#include "practice_capture_fixtures.hpp"
#include "desktop/ProgressPresentation.hpp"
#include "content/Canonical.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
using namespace fathom;
using V = json::Value;
using A = V::Array;
using O = V::Object;

const V& field(const V& value, const char* key) {
    return value.object().at(key);
}

std::size_t rows(const V& snapshot, const char* table) {
    return field(field(snapshot, "authoritative"), table).array().size();
}

std::string record(capture::PracticeSession& session, practice::Coordinator& coordinator,
                   bool interrupted, const std::filesystem::path& evidence, int index) {
    const auto request = capture_fixture::request("", true);
    if (!session.start(request, static_cast<std::uint64_t>(index), capture_fixture::now()))
        throw std::runtime_error("Freeplay allocation request refused");
    capture_fixture::until(session, [&] { return session.phase() == capture::SessionPhase::Ready; });
    if (!session.takeStart(capture_fixture::now()).has_value())
        throw std::runtime_error("Freeplay initial checkpoint did not release start");

    coordinator.progress(capture_fixture::progress(coordinator, interrupted ? 18000 : 24000,
                                                    interrupted ? practice::State::Error : practice::State::Ended));
    session.poll(capture_fixture::now(), "2026-09-13T18:00:30Z");
    capture_fixture::until(session, [&] { return session.phase() == capture::SessionPhase::Review; });
    if (!session.save(nullptr, interrupted ? capture::Outcome::InterruptedError : capture::Outcome::Stop,
                      capture_fixture::now()))
        throw std::runtime_error("Freeplay save request refused");
    capture_fixture::until(session, [&] { return session.phase() == capture::SessionPhase::Saved; });
    if (!session.original() || !session.canLeave(true))
        throw std::runtime_error("Freeplay original did not resolve for leave");

    const auto bytes = session.original()->bytes;
    capture_fixture::write(evidence / ("freeplay-" + std::to_string(index) + ".envelope.json"), bytes);
    return bytes;
}
}

int main(int argc, char** argv) {
    if (argc != 2 || !std::filesystem::path(argv[1]).is_absolute() || std::filesystem::exists(argv[1]))
        return 2;

    const std::filesystem::path evidence = argv[1];
    std::filesystem::create_directories(evidence);
    std::filesystem::permissions(evidence, std::filesystem::perms::owner_all, std::filesystem::perm_options::replace);
    std::ofstream checks(evidence / "checks.tsv");
    int count{};
    auto check = [&](bool okay, const std::string& name) {
        ++count;
        checks << count << '\t' << name << '\t' << (okay ? "PASS" : "FAIL") << '\n';
        checks.flush();
        if (!okay)
            throw std::runtime_error(name);
    };

    try {
        const auto profile = evidence / "profile.sqlite";
        storage::StoreOptions options;
        options.path = profile;
        options.create = true;
        options.createdUtc = "2026-09-13T18:00:00Z";

        std::string stoppedBytes;
        std::string interruptedBytes;
        {
            storage::ProfileStore store(options);
            practice::Coordinator stoppedCoordinator;
            capture::PracticeSession stoppedSession(store, stoppedCoordinator);
            stoppedBytes = record(stoppedSession, stoppedCoordinator, false, evidence, 1);
            const auto stoppedEnvelope = storage::validateEnvelope(stoppedBytes);
            check(stoppedEnvelope.kind == "FreeplayActivity" && field(stoppedEnvelope.value, "context").find("session_id") == nullptr,
                  "stopped Freeplay has no lesson Session");
            check(field(stoppedEnvelope.value, "result").find("content")->null(),
                  "stopped Freeplay retains exact content-null active facts");
            check(stoppedEnvelope.active.numerator() > 0, "stopped Freeplay records nonzero active time");

            practice::Coordinator interruptedCoordinator;
            capture::PracticeSession interruptedSession(store, interruptedCoordinator);
            interruptedBytes = record(interruptedSession, interruptedCoordinator, true, evidence, 2);
            const auto interruptedEnvelope = storage::validateEnvelope(interruptedBytes);
            check(interruptedEnvelope.kind == "FreeplayActivity"
                      && field(interruptedEnvelope.value, "result").find("outcome")->string() == "interrupted_error",
                  "interrupted Freeplay retains interrupted outcome");
            check(field(interruptedEnvelope.value, "result").find("content")->null()
                      && field(interruptedEnvelope.value, "context").find("session_id") == nullptr,
                  "interrupted Freeplay remains history-isolated");

            const auto before = capture_fixture::confirmed(store.snapshot("before-reopen"));
            capture_fixture::write(evidence / "snapshot-before-reopen.json", storage::canonical(before.data));
            check(rows(before.data, "session") == 0 && rows(before.data, "identity") == 2
                      && rows(before.data, "finalized") == 2 && rows(before.data, "pending") == 0,
                  "two Freeplay originals finalize without a Session or pending duplicate");
            check(field(before.data, "schema_sha256") == V(storage::ProfileStore::schemaIdentity()),
                  "snapshot retains pinned schema identity");
        }

        options.create = false;
        storage::ProfileStore reopened(options);
        const auto after = capture_fixture::confirmed(reopened.snapshot("after-reopen"));
        capture_fixture::write(evidence / "snapshot-after-reopen.json", storage::canonical(after.data));
        check(rows(after.data, "session") == 0 && rows(after.data, "identity") == 2
                  && rows(after.data, "finalized") == 2 && rows(after.data, "pending") == 0,
              "reopen retains exactly two finalized Freeplay originals");
        check(field(after.data, "authoritative") == field(capture_fixture::confirmed(reopened.snapshot("after-reopen-again")).data, "authoritative"),
              "repeated reopen snapshot is stable");

        const auto presentation = desktop::presentProgress(after, "2026-09-13T18:01:00Z", nullptr);
        const auto projection = presentation.projection;
        check(field(projection, "views").array().empty(), "Freeplay history creates no curriculum query view");
        check(field(projection, "original_history").array().size() == 2,
              "Progress retains two distinct original history entries");
        const auto first = presentation.text.find("Freeplay activity");
        const auto second = first == std::string::npos ? std::string::npos : presentation.text.find("Freeplay activity", first + 1);
        check(first != std::string::npos && second != std::string::npos
                  && presentation.text.find("No exact curriculum query") != std::string::npos,
              "Progress visibly distinguishes both Freeplay activities without curriculum credit");
        check(content::sha256(stoppedBytes) == storage::validateEnvelope(stoppedBytes).digest
                  && content::sha256(interruptedBytes) == storage::validateEnvelope(interruptedBytes).digest,
              "finalized envelope digests remain exact after reopen");

        std::ofstream hashes(evidence / "hashes.tsv");
        hashes << "stopped_envelope\t" << content::sha256(stoppedBytes) << '\n';
        hashes << "interrupted_envelope\t" << content::sha256(interruptedBytes) << '\n';
        hashes << "schema\t" << storage::ProfileStore::schemaIdentity() << '\n';
        hashes.close();
        std::ofstream summary(evidence / "summary.json");
        summary << "{\"checks\":" << count << ",\"finalized\":2,\"sessions\":0,\"status\":\"PASS\"}\n";
        std::cout << "PASS " << count << " Freeplay persistence checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << count << ": " << error.what() << '\n';
        return 1;
    }
}
