#pragma once

// Test-only, single-child SQLite forwarding VFS. This simulates a software
// failure before ONE underlying WAL write/sync. It is not a disk-full,
// power-loss, OS-crash, durability, or physical-storage qualification.
//
// Construct/register before creating any SQLite connection or Store worker.
// Construct one instance per isolated test child. Close all connections and
// join all workers before destroying it. Registration is NOT concurrent.
// armOnce() may be called by a controller thread; injection is atomic and
// happens on the SQLite IO thread. TriggerCallback must be noexcept, bounded,
// and must not reenter SQLite/ProfileStore or destroy this VFS.

#include <sqlite3.h>

#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <exception>
#include <limits>
#include <new>
#include <stdexcept>
#include <string>
#include <utility>

namespace fathom::storage::test {

class RecoveryFaultVfs final {
public:
    enum class Fault : int { None = 0, WriteFull = 1, SyncIoerr = 2 };

    struct Trigger {
        Fault fault;
        const char* operation; // xWrite or xSync
        const char* actualPath; // exact path observed at xOpen, equal to filter
        int openFlags;
        int resultCode;
        std::uint64_t triggerCount;
        std::int64_t steadyNanoseconds; // arbitrary steady-clock epoch
        int byteCount; // xWrite only; zero for xSync
        sqlite3_int64 offset; // xWrite only; zero for xSync
        int syncFlags; // xSync only; zero for xWrite
    };

    using TriggerCallback = void (*)(const Trigger&, void*) noexcept;

    explicit RecoveryFaultVfs(std::string exactAbsoluteWalPath,
                              TriggerCallback callback,
                              void* callbackContext,
                              std::string uniqueVfsName = "fathom-recovery-fault-v1")
        : targetWal_(std::move(exactAbsoluteWalPath)),
          name_(std::move(uniqueVfsName)), callback_(callback),
          callbackContext_(callbackContext) {
        if (targetWal_.empty() || targetWal_.front() != '/' ||
            targetWal_.find('\0') != std::string::npos ||
            targetWal_.size() < 4 ||
            targetWal_.compare(targetWal_.size() - 4, 4, "-wal") != 0) {
            throw std::invalid_argument("Fault VFS needs the exact absolute test WAL path");
        }
        if (name_.empty() || name_.find('\0') != std::string::npos || callback_ == nullptr) {
            throw std::invalid_argument("Fault VFS needs a unique name and trigger logger");
        }
        if (sqlite3_vfs_find(name_.c_str()) != nullptr) {
            throw std::invalid_argument("Fault VFS name already registered");
        }
        underlying_ = sqlite3_vfs_find(nullptr);
        if (underlying_ == nullptr || underlying_->iVersion < 1 || underlying_->iVersion > 3 ||
            underlying_->szOsFile < static_cast<int>(sizeof(sqlite3_file)) ||
            underlying_->xOpen == nullptr) {
            throw std::runtime_error("Unsupported default SQLite VFS");
        }
        if (fileOffset() > static_cast<std::size_t>(std::numeric_limits<int>::max()) -
                               static_cast<std::size_t>(underlying_->szOsFile)) {
            throw std::overflow_error("Fault VFS file allocation overflow");
        }
        vfs_.iVersion = underlying_->iVersion;
        vfs_.szOsFile = static_cast<int>(fileOffset()) + underlying_->szOsFile;
        vfs_.mxPathname = underlying_->mxPathname;
        vfs_.zName = name_.c_str();
        vfs_.pAppData = this;
        vfs_.xOpen = &open;
        vfs_.xDelete = underlying_->xDelete ? &remove : nullptr;
        vfs_.xAccess = underlying_->xAccess ? &access : nullptr;
        vfs_.xFullPathname = underlying_->xFullPathname ? &fullPathname : nullptr;
        vfs_.xDlOpen = underlying_->xDlOpen ? &dlOpen : nullptr;
        vfs_.xDlError = underlying_->xDlError ? &dlError : nullptr;
        vfs_.xDlSym = underlying_->xDlSym ? &dlSym : nullptr;
        vfs_.xDlClose = underlying_->xDlClose ? &dlClose : nullptr;
        vfs_.xRandomness = underlying_->xRandomness ? &randomness : nullptr;
        vfs_.xSleep = underlying_->xSleep ? &sleep : nullptr;
        vfs_.xCurrentTime = underlying_->xCurrentTime ? &currentTime : nullptr;
        vfs_.xGetLastError = underlying_->xGetLastError ? &lastError : nullptr;
        if (vfs_.iVersion >= 2) {
            vfs_.xCurrentTimeInt64 = underlying_->xCurrentTimeInt64 ? &currentTimeInt64 : nullptr;
        }
        if (vfs_.iVersion >= 3) {
            vfs_.xSetSystemCall = underlying_->xSetSystemCall ? &setSystemCall : nullptr;
            vfs_.xGetSystemCall = underlying_->xGetSystemCall ? &getSystemCall : nullptr;
            vfs_.xNextSystemCall = underlying_->xNextSystemCall ? &nextSystemCall : nullptr;
        }
        const int rc = sqlite3_vfs_register(&vfs_, 1);
        if (rc != SQLITE_OK) {
            throw std::runtime_error("Cannot register fault VFS: " + std::to_string(rc));
        }
        registered_ = true;
    }

    ~RecoveryFaultVfs() noexcept {
        // An open handle would retain pointers into this object. Fail explicitly
        // rather than unregistering/freeing live callback state.
        if (openFiles_.load(std::memory_order_acquire) != 0) std::terminate();
        if (registered_) {
            const bool stillDefault = sqlite3_vfs_find(nullptr) == &vfs_;
            (void) sqlite3_vfs_unregister(&vfs_);
            if (stillDefault && sqlite3_vfs_register(underlying_, 1) != SQLITE_OK) std::terminate();
        }
    }

    RecoveryFaultVfs(const RecoveryFaultVfs&) = delete;
    RecoveryFaultVfs& operator=(const RecoveryFaultVfs&) = delete;
    RecoveryFaultVfs(RecoveryFaultVfs&&) = delete;
    RecoveryFaultVfs& operator=(RecoveryFaultVfs&&) = delete;

    // One arming for the entire object's lifetime, even if it never triggers.
    // Arm only after the durable baseline/seal and the declared phase barrier.
    // No automatic rearming, retries, or operation-name inference occur here.
    bool armOnce(Fault fault) noexcept {
        if (fault != Fault::WriteFull && fault != Fault::SyncIoerr) return false;
        bool expected = false;
        if (!everArmed_.compare_exchange_strong(expected, true, std::memory_order_acq_rel)) return false;
        armed_.store(fault, std::memory_order_release);
        return true;
    }

    bool isArmed() const noexcept { return armed_.load(std::memory_order_acquire) != Fault::None; }
    std::uint64_t triggerCount() const noexcept { return triggerCount_.load(std::memory_order_acquire); }
    std::uint64_t openFileCount() const noexcept { return openFiles_.load(std::memory_order_acquire); }
    const std::string& exactWalPath() const noexcept { return targetWal_; }
    const char* underlyingName() const noexcept { return underlying_->zName; }
    const char* registeredName() const noexcept { return name_.c_str(); }

private:
    struct File {
        sqlite3_file publicFile{}; // first member: SQLite owns this allocation
        RecoveryFaultVfs* owner = nullptr;
        sqlite3_file* real = nullptr;
        sqlite3_io_methods methods{}; // mirror real version/null capabilities
        bool targetWal = false;
        int openFlags = 0;
    };

    static constexpr std::size_t fileOffset() noexcept {
        // Preserve the allocation's alignment for the underlying VFS tail.
        constexpr auto alignment = alignof(std::max_align_t);
        return (sizeof(File) + alignment - 1) / alignment * alignment;
    }

    static File& file(sqlite3_file* p) noexcept { return *reinterpret_cast<File*>(p); }
    static RecoveryFaultVfs& self(sqlite3_vfs* p) noexcept {
        return *static_cast<RecoveryFaultVfs*>(p->pAppData);
    }

    bool inject(File& f, Fault kind, int bytes, sqlite3_int64 offset, int flags) noexcept {
        if (!f.targetWal) return false;
        Fault expected = kind;
        if (!armed_.compare_exchange_strong(expected, Fault::None, std::memory_order_acq_rel)) return false;
        const auto count = triggerCount_.fetch_add(1, std::memory_order_acq_rel) + 1;
        const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        const Trigger trigger{kind, kind == Fault::WriteFull ? "xWrite" : "xSync",
                              targetWal_.c_str(), f.openFlags,
                              kind == Fault::WriteFull ? SQLITE_FULL : SQLITE_IOERR_FSYNC,
                              count, ns, bytes, offset, flags};
        callback_(trigger, callbackContext_);
        return true;
    }

    static int open(sqlite3_vfs* p, sqlite3_filename name, sqlite3_file* output,
                    int flags, int* outFlags) noexcept {
        auto& s = self(p);
        auto* f = ::new (static_cast<void*>(output)) File{};
        f->owner = &s;
        f->real = reinterpret_cast<sqlite3_file*>(reinterpret_cast<unsigned char*>(output) + fileOffset());
        std::memset(f->real, 0, static_cast<std::size_t>(s.underlying_->szOsFile));
        f->openFlags = flags;
        f->targetWal = name != nullptr && (flags & SQLITE_OPEN_WAL) != 0 &&
                       std::strcmp(name, s.targetWal_.c_str()) == 0;
        const int rc = s.underlying_->xOpen(s.underlying_, name, f->real, flags, outFlags);
        const auto* m = f->real->pMethods;
        if (m == nullptr) return rc == SQLITE_OK ? SQLITE_IOERR : rc;
        if (m->iVersion < 1 || m->iVersion > 3 || m->xClose == nullptr) {
            if (m->xClose != nullptr) (void) m->xClose(f->real);
            f->real->pMethods = nullptr;
            return SQLITE_CANTOPEN;
        }
        f->methods.iVersion = m->iVersion;
        f->methods.xClose = &close;
        f->methods.xRead = m->xRead ? &read : nullptr;
        f->methods.xWrite = m->xWrite ? &write : nullptr;
        f->methods.xTruncate = m->xTruncate ? &truncate : nullptr;
        f->methods.xSync = m->xSync ? &sync : nullptr;
        f->methods.xFileSize = m->xFileSize ? &fileSize : nullptr;
        f->methods.xLock = m->xLock ? &lock : nullptr;
        f->methods.xUnlock = m->xUnlock ? &unlock : nullptr;
        f->methods.xCheckReservedLock = m->xCheckReservedLock ? &reserved : nullptr;
        f->methods.xFileControl = &control;
        f->methods.xSectorSize = m->xSectorSize ? &sectorSize : nullptr;
        f->methods.xDeviceCharacteristics = m->xDeviceCharacteristics ? &characteristics : nullptr;
        if (m->iVersion >= 2) {
            f->methods.xShmMap = m->xShmMap ? &shmMap : nullptr;
            f->methods.xShmLock = m->xShmLock ? &shmLock : nullptr;
            f->methods.xShmBarrier = m->xShmBarrier ? &shmBarrier : nullptr;
            f->methods.xShmUnmap = m->xShmUnmap ? &shmUnmap : nullptr;
        }
        if (m->iVersion >= 3) {
            f->methods.xFetch = m->xFetch ? &fetch : nullptr;
            f->methods.xUnfetch = m->xUnfetch ? &unfetch : nullptr;
        }
        f->publicFile.pMethods = &f->methods;
        s.openFiles_.fetch_add(1, std::memory_order_release);
        // Even a failed underlying open can supply pMethods requiring xClose.
        return rc;
    }

    static int close(sqlite3_file* p) noexcept {
        auto& f = file(p);
        auto* owner = f.owner;
        const int rc = f.real->pMethods->xClose(f.real);
        f.publicFile.pMethods = nullptr;
        owner->openFiles_.fetch_sub(1, std::memory_order_acq_rel);
        return rc;
    }
    static int read(sqlite3_file* p, void* b, int n, sqlite3_int64 o) noexcept {
        auto& f = file(p); return f.real->pMethods->xRead(f.real, b, n, o);
    }
    static int write(sqlite3_file* p, const void* b, int n, sqlite3_int64 o) noexcept {
        auto& f = file(p);
        if (f.owner->inject(f, Fault::WriteFull, n, o, 0)) return SQLITE_FULL;
        return f.real->pMethods->xWrite(f.real, b, n, o);
    }
    static int truncate(sqlite3_file* p, sqlite3_int64 n) noexcept {
        auto& f = file(p); return f.real->pMethods->xTruncate(f.real, n);
    }
    static int sync(sqlite3_file* p, int flags) noexcept {
        auto& f = file(p);
        if (f.owner->inject(f, Fault::SyncIoerr, 0, 0, flags)) return SQLITE_IOERR_FSYNC;
        return f.real->pMethods->xSync(f.real, flags);
    }
    static int fileSize(sqlite3_file* p, sqlite3_int64* n) noexcept {
        auto& f = file(p); return f.real->pMethods->xFileSize(f.real, n);
    }
    static int lock(sqlite3_file* p, int n) noexcept { auto& f = file(p); return f.real->pMethods->xLock(f.real, n); }
    static int unlock(sqlite3_file* p, int n) noexcept { auto& f = file(p); return f.real->pMethods->xUnlock(f.real, n); }
    static int reserved(sqlite3_file* p, int* n) noexcept { auto& f = file(p); return f.real->pMethods->xCheckReservedLock(f.real, n); }
    static int control(sqlite3_file* p, int op, void* arg) noexcept {
        auto& f = file(p);
        // Report this actual shim for the two VFS-identity controls. All other
        // controls are forwarded without interpreting their pointer payload.
        if (op == SQLITE_FCNTL_VFS_POINTER) {
            *static_cast<sqlite3_vfs**>(arg) = &f.owner->vfs_;
            return SQLITE_OK;
        }
        const int rc = f.real->pMethods->xFileControl
            ? f.real->pMethods->xFileControl(f.real, op, arg) : SQLITE_NOTFOUND;
        if (op == SQLITE_FCNTL_VFSNAME && rc == SQLITE_OK) {
            auto** name = static_cast<char**>(arg);
            char* stacked = sqlite3_mprintf("%s/%s", f.owner->name_.c_str(), *name ? *name : "");
            sqlite3_free(*name);
            *name = stacked;
            return stacked ? SQLITE_OK : SQLITE_NOMEM;
        }
        return rc;
    }
    static int sectorSize(sqlite3_file* p) noexcept { auto& f = file(p); return f.real->pMethods->xSectorSize(f.real); }
    static int characteristics(sqlite3_file* p) noexcept { auto& f = file(p); return f.real->pMethods->xDeviceCharacteristics(f.real); }
    static int shmMap(sqlite3_file* p, int page, int size, int extend, void volatile** result) noexcept {
        auto& f = file(p); return f.real->pMethods->xShmMap(f.real, page, size, extend, result);
    }
    static int shmLock(sqlite3_file* p, int offset, int n, int flags) noexcept {
        auto& f = file(p); return f.real->pMethods->xShmLock(f.real, offset, n, flags);
    }
    static void shmBarrier(sqlite3_file* p) noexcept { auto& f = file(p); f.real->pMethods->xShmBarrier(f.real); }
    static int shmUnmap(sqlite3_file* p, int removeFlag) noexcept {
        auto& f = file(p); return f.real->pMethods->xShmUnmap(f.real, removeFlag);
    }
    static int fetch(sqlite3_file* p, sqlite3_int64 offset, int amount, void** result) noexcept {
        auto& f = file(p); return f.real->pMethods->xFetch(f.real, offset, amount, result);
    }
    static int unfetch(sqlite3_file* p, sqlite3_int64 offset, void* page) noexcept {
        auto& f = file(p); return f.real->pMethods->xUnfetch(f.real, offset, page);
    }

    static int remove(sqlite3_vfs* p, const char* n, int syncDirectory) noexcept {
        auto& s = self(p); return s.underlying_->xDelete(s.underlying_, n, syncDirectory);
    }
    static int access(sqlite3_vfs* p, const char* n, int flags, int* result) noexcept {
        auto& s = self(p); return s.underlying_->xAccess(s.underlying_, n, flags, result);
    }
    static int fullPathname(sqlite3_vfs* p, const char* n, int size, char* out) noexcept {
        auto& s = self(p); return s.underlying_->xFullPathname(s.underlying_, n, size, out);
    }
    static void* dlOpen(sqlite3_vfs* p, const char* n) noexcept {
        auto& s = self(p); return s.underlying_->xDlOpen(s.underlying_, n);
    }
    static void dlError(sqlite3_vfs* p, int n, char* out) noexcept {
        auto& s = self(p); s.underlying_->xDlError(s.underlying_, n, out);
    }
    static void (*dlSym(sqlite3_vfs* p, void* handle, const char* name) noexcept)(void) {
        auto& s = self(p); return s.underlying_->xDlSym(s.underlying_, handle, name);
    }
    static void dlClose(sqlite3_vfs* p, void* handle) noexcept {
        auto& s = self(p); s.underlying_->xDlClose(s.underlying_, handle);
    }
    static int randomness(sqlite3_vfs* p, int n, char* out) noexcept {
        auto& s = self(p); return s.underlying_->xRandomness(s.underlying_, n, out);
    }
    static int sleep(sqlite3_vfs* p, int us) noexcept {
        auto& s = self(p); return s.underlying_->xSleep(s.underlying_, us);
    }
    static int currentTime(sqlite3_vfs* p, double* value) noexcept {
        auto& s = self(p); return s.underlying_->xCurrentTime(s.underlying_, value);
    }
    static int lastError(sqlite3_vfs* p, int n, char* out) noexcept {
        auto& s = self(p); return s.underlying_->xGetLastError(s.underlying_, n, out);
    }
    static int currentTimeInt64(sqlite3_vfs* p, sqlite3_int64* value) noexcept {
        auto& s = self(p); return s.underlying_->xCurrentTimeInt64(s.underlying_, value);
    }
    static int setSystemCall(sqlite3_vfs* p, const char* n, sqlite3_syscall_ptr call) noexcept {
        auto& s = self(p); return s.underlying_->xSetSystemCall(s.underlying_, n, call);
    }
    static sqlite3_syscall_ptr getSystemCall(sqlite3_vfs* p, const char* n) noexcept {
        auto& s = self(p); return s.underlying_->xGetSystemCall(s.underlying_, n);
    }
    static const char* nextSystemCall(sqlite3_vfs* p, const char* n) noexcept {
        auto& s = self(p); return s.underlying_->xNextSystemCall(s.underlying_, n);
    }

    const std::string targetWal_;
    const std::string name_;
    TriggerCallback const callback_;
    void* const callbackContext_;
    sqlite3_vfs* underlying_ = nullptr;
    sqlite3_vfs vfs_{};
    bool registered_ = false;
    std::atomic<bool> everArmed_{false};
    std::atomic<Fault> armed_{Fault::None};
    std::atomic<std::uint64_t> triggerCount_{0};
    std::atomic<std::uint64_t> openFiles_{0};
};

} // namespace fathom::storage::test
