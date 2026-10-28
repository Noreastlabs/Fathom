#include "desktop/PortableRestoreGuidance.hpp"

#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

using namespace fathom::desktop;

int main() {
    int checks = 0;
    const auto check = [&](bool condition, std::string_view name) {
        ++checks;
        if (!condition)
            throw std::runtime_error(std::string(name));
    };
    const auto verify = [&](std::string_view detail, std::string_view expectedCode,
                            std::string_view expectedAction) {
        const auto guidance = portableRestoreGuidance(detail);
        check(guidance.code == expectedCode, "stable code extraction");
        check(guidance.primary.find("restore was not applied") != std::string::npos ||
                  guidance.primary.find("no new restore was applied") != std::string::npos,
              "no false success in primary");
        check(guidance.nextAction == expectedAction, "safe next action");
        check(guidance.primary.find('\n') == std::string::npos &&
                  guidance.nextAction.find('\n') == std::string::npos,
              "single-line guidance");
        check(guidance.primary.size() < 160 && guidance.nextAction.size() < 180,
              "finite guidance");
        check(guidance.primary.find(std::string(detail)) == std::string::npos,
              "raw detail excluded from primary");
        const auto output = portableRestoreFailureOutput(detail);
        check(output.find("PORTABLE_RESTORE_GUIDANCE primary=") == 0,
              "stable primary label");
        check(output.find("PORTABLE_RESTORE_NEXT_ACTION ") != std::string::npos,
              "stable action label");
        check(output.find("PORTABLE_RESTORE_DIAGNOSTIC code=") != std::string::npos,
              "stable diagnostic label");
        check(output.find(std::string(detail)) != std::string::npos,
              "raw detail retained separately");
    };

    verify("Restore preparation did not complete: ARCHIVE_FORMAT Local and central header mismatch",
            "ARCHIVE_FORMAT", "Choose a verified Fathom backup archive and try Prepare again.");
    verify("Restore preparation did not complete: ARCHIVE_CONTAINER_READ_FAILED input ended early",
            "ARCHIVE_CONTAINER_READ_FAILED", "Choose a verified Fathom backup archive and try Prepare again.");
    verify("Candidate archive must be an existing regular file", "",
           "Choose an existing Fathom backup archive and select Prepare again.");
    const auto missingArchive = portableRestoreGuidance(
        "Candidate archive must be an existing regular file");
    check(missingArchive.primary ==
              "The selected backup archive is missing, so the restore was not applied.",
          "missing archive refusal identifies no-restore outcome");
    check(missingArchive.nextAction ==
              "Choose an existing Fathom backup archive and select Prepare again.",
          "missing archive action names the next step");
    check(missingArchive.code.empty(), "raw missing-archive validation does not invent a code");
    verify("Restore preparation did not complete: RESTORE_CONTENT missing reference",
            "RESTORE_CONTENT", "Check the backup and its private staging location, then prepare a new preview.");
    verify("Restore apply did not complete: RESTORE_CONTENT_STALE source changed",
            "RESTORE_CONTENT_STALE", "Check the backup, available space and its private staging location, then prepare a new preview.");
    for (const auto code : {"RESTORE_COPY", "RESTORE_SPACE"})
        verify(std::string("Restore apply did not complete: ") + code + " bounded failure",
               code, "Check the backup, available space and its private staging location, then prepare a new preview.");
    for (const auto code : {"RESTORE_OPERATION", "RESTORE_OPERATION_EXISTS", "RESTORE_SIDECARS",
                            "RESTORE_HANDLE", "RESTORE_RECORD", "RESTORE_RECORD_WRITE", "RESTORE_REOPEN"})
        verify(std::string("Restore apply did not complete: ") + code + " bounded failure",
               code, "Keep the original profile, review the restore details, and reconcile the original operation before retrying.");
    for (const auto detail : {
             "Restore apply did not complete: RESTORE_CANCELLED Restore cancelled; preserve original operation and data",
             "Restore apply did not complete: RESTORE_DEADLINE Restore aggregate deadline reached; preserve original operation and data"})
        verify(detail, portableRestoreCode(detail),
               "Keep the original profile, review the restore details, and reconcile the original operation before retrying.");
    verify("Restore preparation did not complete: RESTORE_CONFIRMATION Exact SHA256 required",
            "RESTORE_CONFIRMATION", "Keep the current profile unchanged; use the exact confirmation SHA-256 shown by the prepared preview. If the preview no longer verifies, prepare a new preview.");
    verify("Restore apply did not complete: RESTORE_CONFIRMATION Supplied confirmation does not match the prepared preview",
            "RESTORE_CONFIRMATION", "Keep the current profile unchanged; use the exact confirmation SHA-256 shown by the prepared preview. If the preview no longer verifies, prepare a new preview.");
    for (const auto detail : {
             "Restore preparation did not complete: RESTORE_CONFIRMATION Exact SHA256 required",
             "Restore apply did not complete: RESTORE_CONFIRMATION Supplied confirmation does not match the prepared preview"}) {
        const auto guidance = portableRestoreGuidance(detail);
        check(guidance.primary.find("restore was not applied") != std::string::npos,
              "confirmation refusal is explicitly no-apply");
        check(guidance.nextAction.find("exact confirmation SHA-256") != std::string::npos &&
                  guidance.nextAction.find("reconcile") == std::string::npos,
              "confirmation recovery uses preview hash and does not require an operation");
    }
    const auto pending = portableRestoreGuidance("Restore apply did not complete: RESTORE_PENDING original operation is unresolved");
    check(pending.nextAction == "Keep the original profile, review the restore details, and reconcile the original operation before retrying.",
          "real pending restore retains reconcile guidance");

    const auto unknown = portableRestoreGuidance("profile preview failed unexpectedly");
    check(unknown.code.empty(), "unknown code remains empty");
    check(unknown.primary.find("no restore was applied") != std::string::npos,
          "unknown failure cannot imply success");
    check(unknown.nextAction.find("understood") != std::string::npos,
          "unknown failure asks for diagnosis");

    const std::string raw = "Restore preparation did not complete: ARCHIVE_FORMAT raw\n";
    const auto output = portableRestoreFailureOutput(raw);
    check(output.find("primary=This backup could not be read") != std::string::npos,
          "primary is learner-facing");
    check(output.find("detail=Restore preparation did not complete: ARCHIVE_FORMAT raw\\x0A") != std::string::npos,
          "diagnostic newline is escaped");
    check(output.find("ARCHIVE_FORMAT raw") > output.find("PORTABLE_RESTORE_DIAGNOSTIC"),
          "diagnostic follows guidance");
    const auto confirmation = portableRestoreFailureOutput(
        "Restore apply did not complete: RESTORE_CONFIRMATION Supplied confirmation does not match the prepared preview");
    check(confirmation.find("primary=The restore was not applied because the prepared preview could not be confirmed.") != std::string::npos,
          "confirmation refusal has no-restore primary");
    check(confirmation.find("RESTORE_CONFIRMATION") > confirmation.find("PORTABLE_RESTORE_DIAGNOSTIC"),
          "confirmation code remains diagnostic");
    const std::string longDetail(5000, 'x');
    const auto bounded = portableRestoreFailureOutput(longDetail);
    check(bounded.size() < 1500, "diagnostic display is bounded");
    check(bounded.find("[display truncated]") != std::string::npos,
          "long diagnostic is visibly bounded");

    std::cout << "PASS " << checks << " portable restore guidance checks; no restore execution\n";
    return 0;
}
