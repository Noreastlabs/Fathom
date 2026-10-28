#pragma once

#include "desktop/DiagnosticText.hpp"

#include <string>
#include <string_view>

namespace fathom::desktop {

struct PortableRestoreGuidance {
    std::string primary;
    std::string nextAction;
    std::string code;
};

inline bool startsWith(std::string_view text, std::string_view prefix) {
    return text.size() >= prefix.size() && text.substr(0, prefix.size()) == prefix;
}

inline bool codeStartsWith(std::string_view code, std::string_view prefix) {
    return code == prefix || (code.size() > prefix.size() &&
                              code.substr(0, prefix.size()) == prefix &&
                              code[prefix.size()] == '_');
}

inline std::string portableRestoreCode(std::string_view detail) {
    for (const auto prefix : {std::string_view{"Restore preparation did not complete: "},
                              std::string_view{"Restore apply did not complete: "}}) {
        if (!startsWith(detail, prefix))
            continue;
        const auto rest = detail.substr(prefix.size());
        const auto end = rest.find_first_of(" \t\r\n");
        return std::string(rest.substr(0, end == std::string_view::npos ? rest.size() : end));
    }
    return {};
}

inline PortableRestoreGuidance portableRestoreGuidance(std::string_view detail) {
    const auto code = portableRestoreCode(detail);
    if (detail == "Candidate archive must be an existing regular file")
        return {"The selected backup archive is missing, so the restore was not applied.",
                "Choose an existing Fathom backup archive and select Prepare again.", code};
    if (codeStartsWith(code, "ARCHIVE"))
        return {"This backup could not be read, so the restore was not applied.",
                "Choose a verified Fathom backup archive and try Prepare again.", code};
    if (code == "RESTORE_CONTENT")
        return {"This backup is not ready for restore, so the restore was not applied.",
                "Check the backup and its private staging location, then prepare a new preview.", code};
    if (code == "RESTORE_CONTENT_STALE" || codeStartsWith(code, "RESTORE_PREVIEW") ||
        codeStartsWith(code, "RESTORE_PATH") || codeStartsWith(code, "RESTORE_CAPACITY") ||
        codeStartsWith(code, "RESTORE_OPTIONS") || codeStartsWith(code, "RESTORE_COPY") ||
        codeStartsWith(code, "RESTORE_SPACE"))
        return {"This backup is not ready for restore, so the restore was not applied.",
                "Check the backup, available space and its private staging location, then prepare a new preview.", code};
    if (code == "RESTORE_CONFIRMATION")
        return {"The restore was not applied because the prepared preview could not be confirmed.",
                "Keep the current profile unchanged; use the exact confirmation SHA-256 shown by the prepared preview. If the preview no longer verifies, prepare a new preview.", code};
    if (codeStartsWith(code, "RESTORE_CONFLICT") ||
        codeStartsWith(code, "RESTORE_PENDING") || code == "RESTORE_RECOVERY_REQUIRED" ||
        codeStartsWith(code, "RESTORE_SOURCE") || codeStartsWith(code, "RESTORE_CHANGED") ||
        codeStartsWith(code, "RESTORE_CHECKPOINT") || codeStartsWith(code, "RESTORE_SYNC") ||
        codeStartsWith(code, "RESTORE_SWAP_UNCERTAIN") || codeStartsWith(code, "RESTORE_OPERATION") ||
        code == "RESTORE_CANCELLED" || code == "RESTORE_DEADLINE" ||
        codeStartsWith(code, "RESTORE_SIDECARS") || codeStartsWith(code, "RESTORE_HANDLE") ||
        codeStartsWith(code, "RESTORE_RECORD") || codeStartsWith(code, "RESTORE_REOPEN") ||
        code == "RESTORE_EXCEPTION")
        return {"The restore needs attention, and no new restore was applied.",
                "Keep the original profile, review the restore details, and reconcile the original operation before retrying.", code};
    return {"The restore could not be completed, so no restore was applied.",
            "Keep the original profile, review the diagnostic details, and try again only after the cause is understood.", code};
}

inline std::string portableRestoreFailureOutput(std::string_view detail) {
    const auto guidance = portableRestoreGuidance(detail);
    return "PORTABLE_RESTORE_GUIDANCE primary=" + guidance.primary +
           "\nPORTABLE_RESTORE_NEXT_ACTION " + guidance.nextAction +
           "\nPORTABLE_RESTORE_DIAGNOSTIC code=" + diagnosticField(guidance.code, 256) +
           " detail=" + diagnosticField(detail, 1024);
}

} // namespace fathom::desktop
