#include "storage/ProfileStore.hpp"
#include <chrono>
#include <condition_variable>
#include <filesystem>
#include <fstream>
#include <future>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <thread>

namespace {
using namespace fathom::storage;
namespace fs = std::filesystem;
using namespace std::chrono_literals;
std::ofstream checks;
int passed = 0, failed = 0;
void check(const char* name, bool okay) {
    checks << (okay ? "PASS" : "FAIL") << '\t' << name << '\n';
    if (!checks) throw std::runtime_error("Cannot persist fixture check");
    okay ? ++passed : ++failed;
}
struct Gate {
    std::mutex mutex;
    std::condition_variable cv;
    bool entered = false, released = false;
    void hold() {
        std::unique_lock<std::mutex> lock(mutex);
        entered = true; cv.notify_all();
        cv.wait(lock, [this] { return released; });
    }
    bool awaitEntry() {
        std::unique_lock<std::mutex> lock(mutex);
        return cv.wait_for(lock, 3s, [this] { return entered; });
    }
    void release() {
        { std::lock_guard<std::mutex> lock(mutex); released = true; }
        cv.notify_all();
    }
};
struct ReleaseOnExit {
    Gate& gate;
    ~ReleaseOnExit() { gate.release(); }
};
StoreOptions options(const fs::path& path) {
    StoreOptions result;
    result.path = path / "profile.sqlite";
    result.create = true;
    result.createdUtc = "2026-10-07T12:00:00Z";
    return result;
}
Reply ready(ProfileStore::Future& future) {
    if (future.wait_for(3s) != std::future_status::ready)
        throw std::runtime_error("Fixture reply did not settle within its bound");
    return future.get();
}
bool awaitShutdown(ProfileStore& store) {
    const auto until = std::chrono::steady_clock::now() + 3s;
    while (!store.shutdownComplete() && store.shutdownError().empty() &&
           std::chrono::steady_clock::now() < until)
        std::this_thread::sleep_for(1ms);
    return store.shutdownComplete();
}
void drainCase(const fs::path& root) {
    Gate gate;
    auto config = options(root / "drain");
    config.diagnosticHook = [&](const std::string& phase, const std::string& operation) {
        if (phase == "before_operation" && operation == "accepted-one") gate.hold();
    };
    auto store = std::make_unique<ProfileStore>(config);
    ReleaseOnExit releaseBeforeStore{gate};
    auto first = store->createSession("accepted-one", "2026-10-07T12:00:01Z", "UTC",
                                      {}, Value::Object{{"synthetic_fixture", true}});
    if (!gate.awaitEntry()) throw std::runtime_error("Accepted writer did not reach its gate");
    auto second = store->createSession("accepted-two", "2026-10-07T12:00:02Z", "UTC",
                                       {}, Value::Object{{"synthetic_fixture", true}});
    auto begin = std::async(std::launch::async, [&] { store->beginShutdown(); });
    // Release the fixture barrier before any async-future destructor can wait,
    // including the failure path of the nonblocking-return oracle itself.
    ReleaseOnExit releaseBeforeBegin{gate};
    const bool returned = begin.wait_for(500ms) == std::future_status::ready;
    check("beginShutdown returns while accepted writer remains gated", returned);
    if (!returned) { gate.release(); begin.wait(); }
    begin.get();
    check("shutdown incomplete while accepted work is gated", !store->shutdownComplete());
    check("accepted original future remains pending", first.wait_for(0ms) != std::future_status::ready);
    check("accepted queued future remains pending", second.wait_for(0ms) != std::future_status::ready);
    auto refused = store->createSession("refused-after-shutdown", "2026-10-07T12:00:03Z", "UTC");
    const auto rejected = ready(refused);
    check("new submission Busy retains exact operation", rejected.status == Status::Busy &&
          rejected.operation == "refused-after-shutdown" && rejected.code == "QUEUE_REFUSED");
    store->beginShutdown();
    check("repeated beginShutdown does not finish or cancel original work", !store->shutdownComplete());
    gate.release();
    const auto one = ready(first);
    const auto two = ready(second);
    check("first original accepted write confirmed", one.status == Status::Confirmed &&
          one.operation == "accepted-one" && !one.owner.empty());
    check("second original accepted write confirmed", two.status == Status::Confirmed &&
          two.operation == "accepted-two" && !two.owner.empty() && one.owner != two.owner);
    check("completion published after drain and native close", awaitShutdown(*store));
    check("successful close has no shutdown error", store->shutdownError().empty());
    bool excluded = false;
    auto reopen = config; reopen.create = false; reopen.diagnosticHook = {};
    try { ProfileStore duplicate(reopen); } catch (const std::exception&) { excluded = true; }
    check("profile lease retained until Store destruction", excluded);
    store.reset();
    ProfileStore reopened(reopen);
    auto read = reopened.snapshot("verify-drained-writes");
    const auto snapshot = ready(read);
    const auto& rows = snapshot.data.object().at("authoritative").object().at("session").array();
    bool hasOne = false, hasTwo = false;
    for (const auto& row : rows) {
        hasOne = hasOne || row.array()[0].string() == one.owner;
        hasTwo = hasTwo || row.array()[0].string() == two.owner;
    }
    check("both accepted writes durable exactly once and refused write absent",
          snapshot.status == Status::Confirmed && rows.size() == 2 && hasOne && hasTwo);
}
void closeFailureCase(const fs::path& root) {
    auto config = options(root / "close-failure");
    config.diagnosticHook = [](const std::string& phase, const std::string&) {
        if (phase == "before_shutdown_close")
            throw std::runtime_error("controlled writer-side close failure");
    };
    auto store = std::make_unique<ProfileStore>(config);
    auto write = store->createSession("accepted-before-close-error", "2026-10-07T12:00:01Z", "UTC");
    const auto original = ready(write);
    store->beginShutdown();
    check("close failure does not publish completion", !awaitShutdown(*store));
    check("close failure is exposed without false success",
          store->shutdownError() == "controlled writer-side close failure");
    auto read = store->snapshot("new-read-after-close-error");
    check("failed-close Store refuses fresh work", ready(read).status == Status::Busy);
    bool excluded = false;
    auto reopen = config; reopen.create = false; reopen.diagnosticHook = {};
    try { ProfileStore duplicate(reopen); } catch (const std::exception&) { excluded = true; }
    check("failed-close Store retains profile lease", excluded);
    // Explicit fixture teardown exercises the existing defensive destructor,
    // not permission for the production coordinator to destroy a failed owner.
    store.reset();
    ProfileStore reopened(reopen);
    auto snapshot = reopened.snapshot("verify-close-error-preservation");
    const auto result = ready(snapshot);
    const auto& rows = result.data.object().at("authoritative").object().at("session").array();
    check("close failure preserves original durable write",
          original.status == Status::Confirmed && result.status == Status::Confirmed &&
          rows.size() == 1 && rows[0].array()[0].string() == original.owner);
}
} // namespace
int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("Use profile_store_shutdown_tests <fresh absolute output directory>");
        const fs::path root(argv[1]);
        if (!root.is_absolute() || fs::exists(root) || !fs::create_directories(root))
            throw std::runtime_error("Output must be a newly created absolute fixture directory");
        fs::permissions(root, fs::perms::owner_all, fs::perm_options::replace);
        checks.open(root / "checks.tsv");
        if (!checks) throw std::runtime_error("Cannot create fixture checks");
        drainCase(root); closeFailureCase(root);
        std::ofstream summary(root / "summary.json");
        summary << "{\"passed\":" << passed << ",\"failed\":" << failed << "}\n";
        if (!summary) throw std::runtime_error("Cannot persist fixture summary");
        std::cout << "ProfileStore shutdown checks: " << passed << " passed, " << failed << " failed\n";
        return failed ? 1 : 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
