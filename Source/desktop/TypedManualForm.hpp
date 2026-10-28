#pragma once
#include "desktop/ReadOnlyTextEditor.hpp"
#include "content/StrictJson.hpp"
#include <juce_gui_basics/juce_gui_basics.h>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace fathom::desktop {
// Shared presentation adapters. They never read a native owner or change a
// form value, action token, source instruction, or permission boundary.
namespace manual_text {
void configureReadOnly(juce::TextEditor&, const char* id, const char* title);
void setReadOnlyText(juce::TextEditor&, const juce::String&);
int labelHeight(juce::Label&, int width, int minimum = 24);
int toggleHeight(juce::ToggleButton&, int width, int minimum = 30);
int textHeight(const juce::TextEditor&, int width, int minimum = 32);
std::string releaseGuidance(bool physicalReleaseRequired, bool externalStopRequired);
}
// Presentation/collection only. The caller supplies a current learner-safe
// descriptor and a closure bound to its opaque native action token. Native
// owners retain source authority, transitions, release/debt/history and credit.
class TypedManualForm final : public juce::Component {
public:
    TypedManualForm();
    ~TypedManualForm() override;
    std::uint64_t configure(const json::Value& learnerSchema,
        const std::vector<std::string>& learnerInstructions,
        std::function<bool()> ownerIsCurrent);
    void invalidate();
    bool current() const noexcept;
    std::uint64_t formGeneration() const noexcept { return generation_; }
    // Number inputs retain their exact StrictJson decimal token; nullable
    // reports require an explicit Unknown choice. No clock or report default.
    json::Value read() const;
    // Private unsubmitted widget state, including blank/invalid text. This is
    // never a report and never invokes the owner or an edit callback.
    json::Value captureDraft() const;
    // Exact current schema + current owner fence required. Failed validation
    // preserves the current form; old widget callbacks are serial-fenced.
    bool restoreDraft(const json::Value&);

    std::optional<json::Value> valueAt(const std::string& exactPath) const;
    const json::Value& schema() const noexcept { return schema_; }
    void setInstructions(const std::vector<std::string>& learnerSafeText);
    void setHistorySummary(const std::vector<std::string>& learnerSafeSummaries);
    // Already-committed learner reports only; full text remains scrollable.
    void setCommittedReportSummary(const std::vector<std::string>& learnerSafeReports);
    std::size_t instructionLayoutCount() const noexcept { return instructionLayouts_; }
    std::size_t historyLayoutCount() const noexcept { return historyLayouts_; }
    // For explicit conditional choices only. A caller may normalize/reconfigure
    // the current descriptor; old field callbacks are generation/owner fenced.
    std::function<void(const std::string& exactPath)> onEdited;
    void resized() override;
    void paint(juce::Graphics&) override;
private:
    struct Field;
    std::unique_ptr<Field> build(const json::Value&,const std::string& path,
        const std::string& name,bool optional=false);
    void buildArray(Field&,std::size_t);
    json::Value readField(const Field&) const;
    json::Value draftField(const Field&) const;
    void restoreDraftField(Field&,const json::Value&);
    const Field* find(const Field&,const std::string&) const;
    int layout(Field&,int y,int width,int indent=0);
    bool sameField(std::uint64_t,const std::string&) const;
    void changed(std::uint64_t,const std::string&,std::uint64_t);
    void wire(Field&);
    json::Value schema_;
    std::unique_ptr<Field> form_;
    std::function<bool()> ownerIsCurrent_;
    std::uint64_t generation_{1}, fieldSerial_{1};
    std::string instructionText_,historyText_;
    std::size_t instructionLayouts_{},historyLayouts_{};
    ReadOnlyTextEditor instructions_,history_;
    juce::Viewport viewport_;
    juce::Component body_;
    struct ReportPanel;
    std::unique_ptr<ReportPanel> reports_;
};
} // namespace fathom::desktop
