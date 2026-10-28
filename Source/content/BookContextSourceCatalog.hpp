#pragma once
#include "content/SourceLibraryCatalog.hpp"
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace fathom::curriculum {
struct BookPublicExcerpt { std::string passageId, text; };
struct BookContextLink {
    std::string relation, itemId, workbookId, moduleId, title, packageSha256, scope;
    std::size_t contentRevision=0;
};
struct BookPublicCard {
    std::string id, title, summary, attribution;
    bool externalResource = false;
    std::vector<int> levels;
    std::vector<std::string> paragraphs;
    std::vector<BookPublicExcerpt> authoredPublicExcerpts;
    std::vector<std::string> domains, topicTags, searchTerms, prerequisiteRefs, publicSourceRefs;
    std::vector<BookContextLink> contextLinks;
    std::string difficultyValue, difficultyBasis;
    std::size_t sourceOrder=0;
    std::optional<int> legacyLevel;
};
struct BookContextLocation {
    std::string kind;
    std::optional<int> firstLine, lastLine;
    std::vector<int> physicalPages;
};
struct BookContinuation { int physicalPage=0; std::size_t completeSourceUnits=0; };
struct BookSourceQualification {
    std::size_t sourceUnitOrdinal=0;
    bool qualifiedFullWorkflow=false;
    std::vector<int> physicalPages;
    std::string notice;
};
enum class BookSourceTaskQualification { OrdinaryTaskSource, QualifiedWorkflow, LimitedReference, SourceOnlyContext };
struct BookSourceTask {
    std::size_t sourceUnitOrdinal=0;
    std::optional<int> firstTxtLine,lastTxtLine;
    std::vector<int> physicalPages;
    BookSourceTaskQualification qualification=BookSourceTaskQualification::OrdinaryTaskSource;
private:
    friend class BookContextSourceCatalog;
    std::string sourceIdentity_;
};
struct BookPublicContext {
    std::string workbookId,title;
    int level=0;
    std::size_t txtLines=0,pdfPages=0,sourceUnits=0;
    std::size_t snapshotAcceptedChildren=0,snapshotPendingChildren=0,sourceOnlyUnits=0;
    std::vector<BookSourceTask> sourceTasks;
    std::vector<BookContextLocation> contextLocations;
    std::vector<BookContinuation> compositeContinuations;
    std::vector<std::string> publicCardIds;
    std::vector<BookSourceQualification> sourceQualifications;
};
enum class BookSnapshotCompatibility { ExactFrozenBindings, RequiresReviewedAdditiveRebind };

// Closed existing105 context; no raw JSON, source identity, program, source-player,
// Practice, performance, completion, credit or book-admission API.
class BookContextSourceCatalog final {
public:
    static BookContextSourceCatalog load(const std::filesystem::path& closedPackage,
        const SourceLibrary& verifiedOriginals, const content::CancellationCheck& canceled = {});
    const std::vector<BookPublicContext>& books() const noexcept { return books_; }
    const BookPublicContext& book(int existingLevel) const;
    std::vector<const BookPublicCard*> publicCards(const BookPublicContext&) const;
    std::string publicInstructions(const BookPublicContext&) const;
    // Public reviewed metadata only; Original/provider text and source answers
    // are never searched by these APIs. Domain is advisory, never an access lock.
    std::vector<const BookPublicCard*> searchCards(const std::string& query,
                                                  const std::string& domain={}) const;
    std::vector<int> searchBooks(const std::string& query,
                                 const std::string& domain={}) const;
    std::string sourceIdentity(const BookPublicContext&, const BookSourceTask&) const;
    std::string sourceTaskLabel(const BookPublicContext&, const BookSourceTask&) const;
    BookSnapshotCompatibility snapshotCompatibility(const std::string& descriptorSha,
                                                     const std::string& sourceIndexSha) const noexcept;
    static const char* snapshotDescriptorSha() noexcept;
    static const char* sourceIndexSha() noexcept;
private:
    BookContextSourceCatalog()=default;
    void requireOwned(const BookPublicContext&) const;
    std::vector<BookPublicContext> books_;
    std::vector<BookPublicCard> cards_;
};
} // namespace fathom::curriculum
