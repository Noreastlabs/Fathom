#pragma once
#include "storage/ProfileStore.hpp"

namespace fathom::desktop {
// Explicit development-preview admission; not ordinary profile discovery.
struct PreviewResumeRequest {
    std::filesystem::path directory;
    std::string profile, session, timezone;
};
struct ResumedPreview {
    std::unique_ptr<storage::ProfileStore> store;
    storage::Reply snapshot;
};
void validatePreviewResumeSnapshot(const storage::Reply&, const PreviewResumeRequest&);
// Caller runs on a tracked background worker and retains ownership through completion.
ResumedPreview openPreviewResume(const PreviewResumeRequest&);
}
