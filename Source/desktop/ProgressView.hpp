#pragma once
#include "desktop/ReadOnlyTextEditor.hpp"
#include "desktop/ProgressPresentation.hpp"
#include <juce_gui_basics/juce_gui_basics.h>

namespace fathom::desktop {
class ProgressActionButton final : public juce::TextButton {
public:
    using juce::TextButton::TextButton;
    bool keyPressed(const juce::KeyPress& key) override {
        if (key.getKeyCode() == juce::KeyPress::spaceKey || key.getKeyCode() == juce::KeyPress::returnKey) {
            triggerClick();
            return true;
        }
        return juce::TextButton::keyPressed(key);
    }
};

class ProgressView final : public juce::Component, private juce::Timer {
public:
    using Clock = std::function<std::string()>;
    ProgressView();
    ~ProgressView() override;
    bool bind(storage::ProfileStore&, Clock);
    bool detach();
    bool refresh();
    void service();
    bool busy() const noexcept { return future_.valid(); }
    void unavailable(const std::string&);
    void setCatalog(std::shared_ptr<const lesson::Catalog> value) { catalog_ = std::move(value); }
    const ProgressPresentation& presentation() const noexcept { return data_; }
    std::string statusText() const { return status_.getText().toStdString(); }
    std::function<void()> onBack, onLearn, onAudioSettings;
    std::function<bool()> onReopen;
    void resized() override;
    void paint(juce::Graphics&) override;
private:
    friend struct SharedAudioViewTestAccess;
    struct ReadResult { std::uint64_t generation{}; std::string operation, error; ProgressPresentation data; };
    storage::ProfileStore* store_{};
    Clock clock_;
    std::shared_ptr<const lesson::Catalog> catalog_;
    std::future<ReadResult> future_;
    std::uint64_t generation_{};
    std::string operation_, expectedProfile_;
    ProgressPresentation data_;
    bool detailsShown_{}, reopening_{};
    juce::Label title_, status_, emptyState_, emptyNextAction_;
    ReadOnlyTextEditor body_;
    ProgressActionButton back_{"Back"}, refresh_{"Refresh"}, reopen_{"Reopen profile"},
                         learn_{"Choose practice in Learn"}, audio_{"Audio settings"}, details_{"Details"};
    void timerCallback() override { service(); }
    void updateControls();
    void showBody();
    std::string olderSnapshot() const;
};
}
