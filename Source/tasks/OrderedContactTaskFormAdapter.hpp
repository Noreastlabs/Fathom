#pragma once
#include "tasks/OrderedContactTask.hpp"
#include "content/StrictJson.hpp"

namespace fathom::tasks::ordered_contacts::manual {
class OrderedContactTaskFormAdapter;
struct RestoredContactOwner;
class FormToken final {
public:
    FormToken(const FormToken&) = default;
    FormToken& operator=(const FormToken&) = default;
private:
    FormToken(std::uint64_t owner, std::uint64_t generation) : owner_(owner), generation_(generation) {}
    std::uint64_t owner_, generation_;
    friend class OrderedContactTaskFormAdapter;
struct RestoredContactOwner;
};
struct OpenForm final {
    FormToken token;
    json::Value schema;
    std::string label;
    std::vector<std::string> instructions;
    std::optional<ContactDescriptor> contact;
};
// A generic JSON-form bridge over the frozen native owner. It contains no
// source-row interpretation, player/clock, original answers or provenance UI.
class OrderedContactTaskFormAdapter final {
public:
    explicit OrderedContactTaskFormAdapter(Task&);
    OrderedContactTaskFormAdapter(const OrderedContactTaskFormAdapter&) = delete;
    OrderedContactTaskFormAdapter& operator=(const OrderedContactTaskFormAdapter&) = delete;
    OpenForm open(Action);
    OpenForm selectExtension(const FormToken&, Extension explicitLearnerChoice);
    bool current(const FormToken&) const noexcept;
    void apply(const FormToken&, const json::Value& exactTypedPayload);
    void invalidate() noexcept;
    // Host lifecycle calls use the same native guards and become replayable.
    void cancelForNavigation();
    void deactivateForNavigation();
    // Private bytes only, not learner export or observed performance. Requires
    // exclusive owner access; unsupported/untracked owners remain intact.
    std::string continuation() const;
    std::size_t continuationWatermark() const noexcept { return journal_.size(); }
    std::optional<Action> openAction() const { return nativeToken_&&task_.view().revision==openedRevision_?std::optional<Action>{descriptor_.action}:std::nullopt; }
    std::optional<Extension> selectedExtension() const { return openAction()?selectedExtension_:std::nullopt; }
    static RestoredContactOwner restoreContinuation(const manual_contacts::SourceHandle&,const std::string&);

    static const char* schemaVersion() noexcept { return "fathom.ordered-contact-manual-form.1"; }
private:
    void prepareJournalSlot();
    std::vector<json::Value> journal_;
    bool trackable_{};
    Task& task_;
    const std::uint64_t owner_;
    std::uint64_t generation_{0}, openedRevision_{0};
    std::size_t openedOrdinal_{0};
    std::optional<Token> nativeToken_;
    ActionDescriptor descriptor_{Action::Begin, {}, {}, {}, {}};
    std::optional<Extension> selectedExtension_;
    json::Value schema_;
    void fence(const FormToken&) const;
    OpenForm rebuild();
};
struct RestoredContactOwner final {
    std::unique_ptr<Task> task;
    std::unique_ptr<OrderedContactTaskFormAdapter> adapter;
};
} // namespace fathom::tasks::ordered_contacts::manual
